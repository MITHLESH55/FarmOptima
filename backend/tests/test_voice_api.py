"""
tests/test_voice_api.py — Phase 2.4 Voice Interaction Tests.

Comprehensive integration tests covering:
  - Owner voice interaction & end-to-end pipeline
  - Authentication enforcement
  - Authorization & cross-user isolation (authorization BEFORE STT / LLM / TTS)
  - Audio payload validations (empty audio, invalid MIME/extension, oversized file)
  - STT provider failure and empty transcript handling
  - AI Grounding integration (grounded vs hallucinated answers)
  - AIInteraction audit trail with real recommendation_id
  - TTS success and graceful degradation on failure
  - Recommendation context specificity (Rec A vs Rec B)
"""

from __future__ import annotations

import io
import pytest

from app.services.weather_service import WeatherResult
from app.services.soil_service import SoilResult
from app.services.satellite_service import SatelliteResult
import app.api.routes.recommend as recommend_route
import app.services.ai.llm_client as llm_module
import app.services.voice.stt_client as stt_module
import app.services.voice.tts_client as tts_module
from app.models import AIInteraction
from app.utils.exceptions import VoiceServiceUnavailableError

# ---------------------------------------------------------------------------
# Shared test data & helpers
# ---------------------------------------------------------------------------

FAKE_WEATHER_A = WeatherResult(
    rainfall_mm_last_30d=85.0, avg_temp_c=25.0, humidity_pct=60.0,
    solar_radiation_mj_m2=18.0, wind_speed_m_s=2.0, source="nasa-power",
)
FAKE_SOIL_A = SoilResult(
    ph=6.5, clay_pct=25.0, sand_pct=30.0, soil_moisture_pct=25.0,
    nitrogen_total_mg_kg=40.0, organic_carbon_g_kg=15.0, source="soilgrids",
)
FAKE_SAT_A = SatelliteResult(ndvi=0.55, source="gee-sentinel2", scene_date="2026-07-10")

FAKE_WEATHER_B = WeatherResult(
    rainfall_mm_last_30d=10.0, avg_temp_c=42.0, humidity_pct=12.0,
    solar_radiation_mj_m2=32.0, wind_speed_m_s=7.0, source="nasa-power",
)
FAKE_SOIL_B = SoilResult(
    ph=8.5, clay_pct=5.0, sand_pct=80.0, soil_moisture_pct=3.0,
    nitrogen_total_mg_kg=4.0, organic_carbon_g_kg=1.5, source="soilgrids",
)
FAKE_SAT_B = SatelliteResult(ndvi=0.12, source="gee-sentinel2", scene_date="2026-07-25")

# Synthetic valid audio sample (dummy webm header/bytes)
SAMPLE_AUDIO_BYTES = b"\x1a\x45\xdf\xa3\x9f\x42\x86\x81\x01\x42\xf7\x81\x01\x42\xf2\x81\x04" * 16


def _patch_services_a(monkeypatch):
    monkeypatch.setattr(recommend_route, "get_weather_for_location", lambda lat, lon: FAKE_WEATHER_A)
    monkeypatch.setattr(recommend_route, "get_soil_for_location", lambda lat, lon: FAKE_SOIL_A)
    monkeypatch.setattr(recommend_route, "get_ndvi_for_location", lambda lat, lon: FAKE_SAT_A)


def _patch_services_b(monkeypatch):
    monkeypatch.setattr(recommend_route, "get_weather_for_location", lambda lat, lon: FAKE_WEATHER_B)
    monkeypatch.setattr(recommend_route, "get_soil_for_location", lambda lat, lon: FAKE_SOIL_B)
    monkeypatch.setattr(recommend_route, "get_ndvi_for_location", lambda lat, lon: FAKE_SAT_B)


def _make_recommendation(client, auth_headers, monkeypatch, lat=18.5, lon=73.8, use_b=False):
    if use_b:
        _patch_services_b(monkeypatch)
    else:
        _patch_services_a(monkeypatch)
    resp = client.post("/api/recommend", json={"lat": lat, "lon": lon}, headers=auth_headers)
    assert resp.status_code == 200, f"Recommendation creation failed: {resp.text}"
    return resp.json()


def _register_and_login(client, username, password="password123"):
    client.post("/api/auth/register", json={"username": username, "password": password})
    resp = client.post("/api/auth/login", json={"username": username, "password": password})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


# ---------------------------------------------------------------------------
# TEST 1 — Owner Voice Question (Happy Path)
# ---------------------------------------------------------------------------

def test_owner_voice_question(client, auth_headers, monkeypatch):
    """User A asks a question via voice for their own recommendation."""
    rec = _make_recommendation(client, auth_headers, monkeypatch)
    rec_id = rec["id"]
    top_crop = rec["crop_ranking"][0]["crop"]

    monkeypatch.setattr(
        stt_module, "transcribe_audio",
        lambda audio_bytes, filename=None, content_type=None: f"Why was {top_crop} recommended?",
    )
    monkeypatch.setattr(
        llm_module, "call_llm",
        lambda *a, **kw: f"Based on your soil and climate data, {top_crop} is recommended.",
    )
    monkeypatch.setattr(
        tts_module, "synthesize_speech",
        lambda text, raise_on_failure=False: "bXAzLWF1ZGlvLWRhdGE=",
    )

    files = {"audio": ("question.webm", io.BytesIO(SAMPLE_AUDIO_BYTES), "audio/webm")}
    data = {"recommendation_id": rec_id, "enable_tts": "true"}

    resp = client.post("/api/ai/voice", data=data, files=files, headers=auth_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert body["transcript"] == f"Why was {top_crop} recommended?"
    assert top_crop.lower() in body["answer"].lower()
    assert body["context_snapshot_id"] == rec_id
    assert body["audio_base64"] == "bXAzLWF1ZGlvLWRhdGE="


# ---------------------------------------------------------------------------
# TEST 2 — Unauthenticated Request
# ---------------------------------------------------------------------------

def test_unauthenticated_voice_request(client, monkeypatch):
    """Voice request without token fails with 401; STT and LLM are never called."""
    stt_called = []
    llm_called = []
    monkeypatch.setattr(stt_module, "transcribe_audio", lambda *a, **kw: stt_called.append(1) or "q")
    monkeypatch.setattr(llm_module, "call_llm", lambda *a, **kw: llm_called.append(1) or "a")

    files = {"audio": ("question.webm", io.BytesIO(SAMPLE_AUDIO_BYTES), "audio/webm")}
    data = {"recommendation_id": 1}

    resp = client.post("/api/ai/voice", data=data, files=files)
    assert resp.status_code == 401
    assert len(stt_called) == 0, "STT must not be called when unauthenticated"
    assert len(llm_called) == 0, "LLM must not be called when unauthenticated"


# ---------------------------------------------------------------------------
# TEST 3 — Nonexistent Recommendation
# ---------------------------------------------------------------------------

def test_nonexistent_recommendation_returns_404(client, auth_headers, monkeypatch):
    """Voice request for nonexistent recommendation returns 404 recommendation_not_found."""
    stt_called = []
    llm_called = []
    monkeypatch.setattr(stt_module, "transcribe_audio", lambda *a, **kw: stt_called.append(1) or "q")
    monkeypatch.setattr(llm_module, "call_llm", lambda *a, **kw: llm_called.append(1) or "a")

    files = {"audio": ("question.webm", io.BytesIO(SAMPLE_AUDIO_BYTES), "audio/webm")}
    data = {"recommendation_id": 99999999}

    resp = client.post("/api/ai/voice", data=data, files=files, headers=auth_headers)
    assert resp.status_code == 404
    body = resp.json()
    assert body["error"]["code"] == "recommendation_not_found"
    assert len(stt_called) == 0, "STT must not be called on nonexistent recommendation"
    assert len(llm_called) == 0, "LLM must not be called on nonexistent recommendation"


# ---------------------------------------------------------------------------
# TEST 4 — Cross-User Access Denied (Crucial Security Invariant)
# ---------------------------------------------------------------------------

def test_cross_user_voice_access_denied(client, monkeypatch):
    """
    User B attempts to query User A's recommendation via voice.
    Authorization MUST reject with 404 BEFORE STT, context loader, LLM, or TTS run.
    """
    headers_a = _register_and_login(client, "voice_user_a_t4")
    headers_b = _register_and_login(client, "voice_user_b_t4")

    rec_a = _make_recommendation(client, headers_a, monkeypatch, lat=12.5, lon=75.5)
    rec_id_a = rec_a["id"]

    stt_called = []
    ctx_called = []
    llm_called = []
    tts_called = []

    import app.services.ai.context_loader as ctx_loader
    original_get_ctx = ctx_loader.get_context_for_recommendation

    monkeypatch.setattr(stt_module, "transcribe_audio", lambda *a, **kw: stt_called.append(1) or "q")
    monkeypatch.setattr(
        ctx_loader, "get_context_for_recommendation",
        lambda *a, **kw: ctx_called.append(1) or original_get_ctx(*a, **kw),
    )
    monkeypatch.setattr(llm_module, "call_llm", lambda *a, **kw: llm_called.append(1) or "a")
    monkeypatch.setattr(tts_module, "synthesize_speech", lambda *a, **kw: tts_called.append(1) or "audio")

    files = {"audio": ("question.webm", io.BytesIO(SAMPLE_AUDIO_BYTES), "audio/webm")}
    data = {"recommendation_id": rec_id_a}

    resp = client.post("/api/ai/voice", data=data, files=files, headers=headers_b)
    assert resp.status_code == 404
    body = resp.json()
    assert body["error"]["code"] == "recommendation_not_found"

    assert len(stt_called) == 0, "STT must NOT be invoked when user is unauthorized"
    assert len(ctx_called) == 0, "Context loader must NOT be invoked when user is unauthorized"
    assert len(llm_called) == 0, "LLM must NOT be invoked when user is unauthorized"
    assert len(tts_called) == 0, "TTS must NOT be invoked when user is unauthorized"


# ---------------------------------------------------------------------------
# TEST 5 — Empty Audio Upload
# ---------------------------------------------------------------------------

def test_empty_audio_upload_rejected(client, auth_headers, monkeypatch):
    """Uploading 0-byte audio fails with 400 invalid_audio; LLM is never called."""
    rec = _make_recommendation(client, auth_headers, monkeypatch)
    rec_id = rec["id"]

    llm_called = []
    monkeypatch.setattr(llm_module, "call_llm", lambda *a, **kw: llm_called.append(1) or "a")

    files = {"audio": ("empty.webm", io.BytesIO(b""), "audio/webm")}
    data = {"recommendation_id": rec_id}

    resp = client.post("/api/ai/voice", data=data, files=files, headers=auth_headers)
    assert resp.status_code == 400
    body = resp.json()
    assert body["error"]["code"] == "invalid_audio"
    assert len(llm_called) == 0


# ---------------------------------------------------------------------------
# TEST 6 — Invalid Content Type / Extension
# ---------------------------------------------------------------------------

def test_invalid_content_type_rejected(client, auth_headers, monkeypatch):
    """Uploading non-audio files (e.g. text/plain or image/png) fails with 400 invalid_audio."""
    rec = _make_recommendation(client, auth_headers, monkeypatch)
    rec_id = rec["id"]

    llm_called = []
    monkeypatch.setattr(llm_module, "call_llm", lambda *a, **kw: llm_called.append(1) or "a")

    files = {"audio": ("document.txt", io.BytesIO(b"Hello world text"), "text/plain")}
    data = {"recommendation_id": rec_id}

    resp = client.post("/api/ai/voice", data=data, files=files, headers=auth_headers)
    assert resp.status_code == 400
    body = resp.json()
    assert body["error"]["code"] == "invalid_audio"
    assert len(llm_called) == 0, "Invalid file format must not reach LLM"


# ---------------------------------------------------------------------------
# TEST 7 — Oversized Audio Upload
# ---------------------------------------------------------------------------

def test_oversized_audio_rejected(client, auth_headers, monkeypatch):
    """Uploading audio exceeding max size limit fails with 400 invalid_audio."""
    from app.config import settings

    rec = _make_recommendation(client, auth_headers, monkeypatch)
    rec_id = rec["id"]

    # Temporarily set limit to 100 bytes for fast test execution
    monkeypatch.setattr(settings, "voice_max_audio_size_bytes", 100)

    llm_called = []
    monkeypatch.setattr(llm_module, "call_llm", lambda *a, **kw: llm_called.append(1) or "a")

    oversized_data = b"X" * 200
    files = {"audio": ("big.webm", io.BytesIO(oversized_data), "audio/webm")}
    data = {"recommendation_id": rec_id}

    resp = client.post("/api/ai/voice", data=data, files=files, headers=auth_headers)
    assert resp.status_code == 400
    body = resp.json()
    assert body["error"]["code"] == "invalid_audio"
    assert len(llm_called) == 0, "Oversized audio must not reach LLM"


# ---------------------------------------------------------------------------
# TEST 8 — Empty Transcript
# ---------------------------------------------------------------------------

def test_empty_transcript_handling(client, auth_headers, monkeypatch):
    """STT returning empty/blank string results in controlled 400 empty_transcript."""
    rec = _make_recommendation(client, auth_headers, monkeypatch)
    rec_id = rec["id"]

    llm_called = []
    monkeypatch.setattr(llm_module, "call_llm", lambda *a, **kw: llm_called.append(1) or "a")

    from app.utils.exceptions import EmptyTranscriptError
    monkeypatch.setattr(
        stt_module, "transcribe_audio",
        lambda *a, **kw: (_ for _ in ()).throw(EmptyTranscriptError("Inaudible audio.")),
    )

    files = {"audio": ("silence.webm", io.BytesIO(SAMPLE_AUDIO_BYTES), "audio/webm")}
    data = {"recommendation_id": rec_id}

    resp = client.post("/api/ai/voice", data=data, files=files, headers=auth_headers)
    assert resp.status_code == 400
    body = resp.json()
    assert body["error"]["code"] == "empty_transcript"
    assert len(llm_called) == 0, "LLM must not be called when transcript is empty"


# ---------------------------------------------------------------------------
# TEST 9 — STT Failure
# ---------------------------------------------------------------------------

def test_stt_failure_returns_controlled_502(client, auth_headers, monkeypatch):
    """STT provider failure returns 502 voice_service_unavailable / ai_service_unavailable."""
    rec = _make_recommendation(client, auth_headers, monkeypatch)
    rec_id = rec["id"]

    llm_called = []
    monkeypatch.setattr(llm_module, "call_llm", lambda *a, **kw: llm_called.append(1) or "a")

    monkeypatch.setattr(
        stt_module, "transcribe_audio",
        lambda *a, **kw: (_ for _ in ()).throw(VoiceServiceUnavailableError("Whisper API connection error.")),
    )

    files = {"audio": ("question.webm", io.BytesIO(SAMPLE_AUDIO_BYTES), "audio/webm")}
    data = {"recommendation_id": rec_id}

    resp = client.post("/api/ai/voice", data=data, files=files, headers=auth_headers)
    assert resp.status_code == 502
    body = resp.json()
    assert "service_unavailable" in body["error"]["code"]
    assert "Traceback" not in resp.text
    assert len(llm_called) == 0, "LLM must not be called when STT fails"


# ---------------------------------------------------------------------------
# TEST 10 — Grounded Answer
# ---------------------------------------------------------------------------

def test_grounded_voice_answer(client, auth_headers, monkeypatch):
    """Valid question and grounded response passes grounding check."""
    rec = _make_recommendation(client, auth_headers, monkeypatch)
    rec_id = rec["id"]
    top_crop = rec["crop_ranking"][0]["crop"]

    monkeypatch.setattr(
        stt_module, "transcribe_audio",
        lambda *a, **kw: f"Tell me about {top_crop}.",
    )
    monkeypatch.setattr(
        llm_module, "call_llm",
        lambda *a, **kw: f"The top recommended crop is {top_crop}.",
    )

    files = {"audio": ("question.webm", io.BytesIO(SAMPLE_AUDIO_BYTES), "audio/webm")}
    data = {"recommendation_id": rec_id}

    resp = client.post("/api/ai/voice", data=data, files=files, headers=auth_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert top_crop.lower() in body["answer"].lower()


# ---------------------------------------------------------------------------
# TEST 11 — Hallucinated Answer Triggers Grounding Fallback
# ---------------------------------------------------------------------------

def test_hallucinated_voice_answer_triggers_fallback(client, auth_headers, monkeypatch):
    """Hallucinated crop/numbers in model answer trigger Phase 2.1 grounding fallback."""
    rec = _make_recommendation(client, auth_headers, monkeypatch)
    rec_id = rec["id"]

    monkeypatch.setattr(
        stt_module, "transcribe_audio",
        lambda *a, **kw: "What crop should I grow?",
    )
    # "sugarcane" is in _ALL_KNOWN_CROP_WORDS and 888.5 is an ungrounded number
    monkeypatch.setattr(
        llm_module, "call_llm",
        lambda *a, **kw: "You should grow sugarcane with 888.5 kg yield increase.",
    )

    files = {"audio": ("question.webm", io.BytesIO(SAMPLE_AUDIO_BYTES), "audio/webm")}
    data = {"recommendation_id": rec_id}

    resp = client.post("/api/ai/voice", data=data, files=files, headers=auth_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "888.5" not in body["answer"], "Hallucinated numeric claim must be filtered out"


# ---------------------------------------------------------------------------
# TEST 12 — AIInteraction Linkage
# ---------------------------------------------------------------------------

def test_voice_ai_interaction_persisted(client, auth_headers, monkeypatch, test_db_engine):
    """Voice question persists AIInteraction with exact recommendation_id and transcript."""
    from sqlalchemy.orm import Session

    rec = _make_recommendation(client, auth_headers, monkeypatch)
    rec_id = rec["id"]
    top_crop = rec["crop_ranking"][0]["crop"]

    monkeypatch.setattr(
        stt_module, "transcribe_audio",
        lambda *a, **kw: f"Is {top_crop} suitable?",
    )
    monkeypatch.setattr(
        llm_module, "call_llm",
        lambda *a, **kw: f"Yes, {top_crop} is suitable.",
    )

    files = {"audio": ("question.webm", io.BytesIO(SAMPLE_AUDIO_BYTES), "audio/webm")}
    data = {"recommendation_id": rec_id}

    resp = client.post("/api/ai/voice", data=data, files=files, headers=auth_headers)
    assert resp.status_code == 200

    with Session(test_db_engine) as db:
        interaction = (
            db.query(AIInteraction)
            .filter(AIInteraction.recommendation_id == rec_id)
            .order_by(AIInteraction.id.desc())
            .first()
        )
        assert interaction is not None, "AIInteraction must be persisted"
        assert interaction.recommendation_id == rec_id
        assert interaction.question == f"Is {top_crop} suitable?"


# ---------------------------------------------------------------------------
# TEST 13 — TTS Success
# ---------------------------------------------------------------------------

def test_tts_success(client, auth_headers, monkeypatch):
    """When TTS succeeds, base64 audio is returned alongside grounded text answer."""
    rec = _make_recommendation(client, auth_headers, monkeypatch)
    rec_id = rec["id"]
    top_crop = rec["crop_ranking"][0]["crop"]

    monkeypatch.setattr(stt_module, "transcribe_audio", lambda *a, **kw: "Give advice.")
    monkeypatch.setattr(llm_module, "call_llm", lambda *a, **kw: f"Based on data, {top_crop} is recommended.")
    monkeypatch.setattr(tts_module, "synthesize_speech", lambda text, raise_on_failure=False: "dGVzdC1hdWRpbw==")

    files = {"audio": ("question.webm", io.BytesIO(SAMPLE_AUDIO_BYTES), "audio/webm")}
    data = {"recommendation_id": rec_id, "enable_tts": "true"}

    resp = client.post("/api/ai/voice", data=data, files=files, headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert top_crop.lower() in body["answer"].lower()
    assert body["audio_base64"] == "dGVzdC1hdWRpbw=="


# ---------------------------------------------------------------------------
# TEST 14 — TTS Failure (Graceful Degradation)
# ---------------------------------------------------------------------------

def test_tts_failure_graceful_degradation(client, auth_headers, monkeypatch):
    """When TTS fails, the grounded text answer is preserved and audio_base64 is None."""
    rec = _make_recommendation(client, auth_headers, monkeypatch)
    rec_id = rec["id"]
    top_crop = rec["crop_ranking"][0]["crop"]

    monkeypatch.setattr(stt_module, "transcribe_audio", lambda *a, **kw: "Give advice.")
    monkeypatch.setattr(llm_module, "call_llm", lambda *a, **kw: f"Based on data, {top_crop} is recommended.")

    # Mock synthesize_speech returning None on error
    monkeypatch.setattr(tts_module, "synthesize_speech", lambda text, raise_on_failure=False: None)

    files = {"audio": ("question.webm", io.BytesIO(SAMPLE_AUDIO_BYTES), "audio/webm")}
    data = {"recommendation_id": rec_id, "enable_tts": "true"}

    resp = client.post("/api/ai/voice", data=data, files=files, headers=auth_headers)
    assert resp.status_code == 200, "Failure in TTS must not cause a 500/502 when text answer succeeded"
    body = resp.json()
    assert top_crop.lower() in body["answer"].lower()
    assert body["audio_base64"] is None


# ---------------------------------------------------------------------------
# TEST 15 — Context Specificity (Rec A vs Rec B)
# ---------------------------------------------------------------------------

def test_voice_context_specificity(client, auth_headers, monkeypatch):
    """Voice requests against Rec A and Rec B receive their respective independent contexts."""
    rec_a = _make_recommendation(client, auth_headers, monkeypatch, lat=15.0, lon=74.0, use_b=False)
    rec_id_a = rec_a["id"]
    top_crop_a = rec_a["crop_ranking"][0]["crop"]

    rec_b = _make_recommendation(client, auth_headers, monkeypatch, lat=28.0, lon=77.0, use_b=True)
    rec_id_b = rec_b["id"]
    top_crop_b = rec_b["crop_ranking"][0]["crop"]

    captured_contexts = {}

    import app.services.ai.assistant_service as svc
    original_answer = svc.answer_farm_question

    def capturing_answer(context, question, db):
        captured_contexts[context.recommendation_id] = context
        return original_answer(context=context, question=question, db=db)

    monkeypatch.setattr(svc, "answer_farm_question", capturing_answer)
    monkeypatch.setattr(stt_module, "transcribe_audio", lambda *a, **kw: "What is my top crop?")

    def dynamic_llm(*a, **kw):
        prompt = (kw.get("system_prompt") or (a[0] if a else ""))
        if top_crop_a in prompt:
            return f"Top crop is {top_crop_a}."
        return f"Top crop is {top_crop_b}."

    monkeypatch.setattr(llm_module, "call_llm", dynamic_llm)

    files_a = {"audio": ("q.webm", io.BytesIO(SAMPLE_AUDIO_BYTES), "audio/webm")}
    files_b = {"audio": ("q.webm", io.BytesIO(SAMPLE_AUDIO_BYTES), "audio/webm")}

    resp_a = client.post("/api/ai/voice", data={"recommendation_id": rec_id_a}, files=files_a, headers=auth_headers)
    resp_b = client.post("/api/ai/voice", data={"recommendation_id": rec_id_b}, files=files_b, headers=auth_headers)

    assert resp_a.status_code == 200
    assert resp_b.status_code == 200

    assert rec_id_a in captured_contexts
    assert rec_id_b in captured_contexts
    assert captured_contexts[rec_id_a].crop_ranking[0].crop == top_crop_a
    assert captured_contexts[rec_id_b].crop_ranking[0].crop == top_crop_b
