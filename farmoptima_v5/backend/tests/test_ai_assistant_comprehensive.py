"""
Comprehensive test suite for FarmOptima AI Assistant Architecture.
Tests all requirements specified in Sections 10A, 20A-K, and 29:
  - Multilingual support: English, Hindi, Marathi, Mixed (Hinglish, Marathi-English)
  - Paraphrased and varying sentence structures
  - Complete reasoning, what-if scenarios, ranking, water, fertilizer
  - Number consistency (percentages, daily water, units, Devanagari)
  - Unsupported fact rejection
  - Ownership & authentication enforcement
"""

import pytest
import sys
sys.path.insert(0, '.')

from app.schemas.ai import (
    FarmContext,
    CropRankEntry,
    NDVIContext,
    ResourcePlanContext,
    ParetoPointSummary,
)
from app.core.ai_grounding import validate_answer_is_grounded, build_grounding_prompt
from app.services.ai.intent_resolver import (
    resolve_question_intent,
    detect_question_language,
    CanonicalIntent,
)
from app.services.ai.assistant_service import _GROUNDING_FALLBACKS, answer_farm_question


@pytest.fixture
def authoritative_context():
    return FarmContext(
        recommendation_id=101,
        generated_at="2026-08-25T14:00:00Z",
        recommendation_status="complete",
        data_completeness_weather="live",
        data_completeness_soil="live",
        data_completeness_satellite="live",
        data_completeness_market="csv",
        satellite_source="gee-sentinel2",
        weather_source="nasa-power",
        soil_source="soilgrids-reference",
        market_source="csv",
        latitude=18.5204,
        longitude=73.8567,
        ndvi=NDVIContext(
            value=0.254,
            source="gee-sentinel2",
            scene_date="2026-07-14",
            status="moderate vegetation",
            is_live=True,
        ),
        ndvi_available=True,
        satellite_scene_date="2026-07-14",
        rainfall_mm_last_30d=470.2,
        avg_temp_c=23.7,
        humidity_pct=93.4,
        solar_radiation_mj_m2=8.98,
        wind_speed_m_s=3.4,
        soil_ph=6.98,
        soil_moisture_pct=27.2,
        soil_nitrogen_mg_kg=1560.0,
        soil_organic_carbon_g_kg=18.0,
        soil_sand_pct=38.0,
        soil_clay_pct=23.5,
        ahp_weights={
            "climate_suitability": 0.4495,
            "soil_suitability": 0.2596,
            "water_efficiency": 0.1707,
            "market_value": 0.1202,
        },
        ahp_consistency_ratio=0.0265,
        ahp_is_consistent=True,
        ahp_method="fuzzy-ahp",
        crop_ranking=[
            CropRankEntry(
                crop="Rice", topsis_closeness=0.7441, electre_net_outranking=1, rank=1,
                tie_break_applied=False,
                criteria_scores={"climate_suitability": 0.8922, "soil_suitability": 0.7000, "water_efficiency": 0.4183, "market_value": 1.0000},
            ),
            CropRankEntry(
                crop="Wheat", topsis_closeness=0.6120, electre_net_outranking=0, rank=2,
                tie_break_applied=False,
                criteria_scores={"climate_suitability": 0.5829, "soil_suitability": 0.7000, "water_efficiency": 0.9562, "market_value": 1.0000},
            ),
            CropRankEntry(
                crop="Groundnut", topsis_closeness=0.4224, electre_net_outranking=0, rank=3,
                tie_break_applied=True, tie_break_reason="electre_net_outranking",
                criteria_scores={"climate_suitability": 0.5922, "soil_suitability": 0.7000, "water_efficiency": 0.6544, "market_value": 1.0000},
            ),
            CropRankEntry(
                crop="Soybean", topsis_closeness=0.4224, electre_net_outranking=0, rank=4,
                tie_break_applied=True, tie_break_reason="electre_net_outranking",
                criteria_scores={"climate_suitability": 0.5922, "soil_suitability": 0.7000, "water_efficiency": 0.6544, "market_value": 1.0000},
            ),
        ],
        crop_names_in_ranking=["Rice", "Wheat", "Groundnut", "Soybean"],
        resource_plan=ResourcePlanContext(
            water_liters_per_week=133650.0,
            fertilizer_kg_per_acre=53.8,
            optimizer_best_fitness=0.15049,
            optimizer_generations_run=80,
            irrigation_schedule="~19093 L/day, split across 2-3 waterings/week",
            optimizer_method="nsga2-multiobjective",
            pareto_front=[
                ParetoPointSummary(water_liters_per_week=133650.0, fertilizer_kg_per_acre=53.8, resource_cost=2500.0)
            ],
            convergence_history=[10.0] * 80,
        ),
        ai_explanation="Rice is the top recommendation.",
    )


# ---------------------------------------------------------------------------
# Section 20.A — Same Question in 3 Languages
# ---------------------------------------------------------------------------

class TestSection20A_RecommendationExplanation:
    @pytest.mark.parametrize("lang,q_text,ans_text", [
        ("en", "Why was Rice recommended?", "Rice was recommended as rank 1 with a TOPSIS closeness score of 0.7441, achieving the highest suitability under current high monsoon rainfall conditions."),
        ("hi", "चावल को क्यों चुना गया?", "चावल को रैंक 1 पर अनुशंसित किया गया क्योंकि इसका TOPSIS स्कोर 0.7441 था, जो वर्तमान मानसूनी परिस्थितियों में सबसे उपयुक्त है।"),
        ("mr", "तांदूळ का निवडला गेला?", "तांदळाची रँक 1 वर शिफारस करण्यात आली कारण त्याचा TOPSIS स्कोअर 0.7441 होता, जो सध्याच्या पावसाळी परिस्थितीत सर्वाधिक आहे."),
    ])
    def test_20a_three_languages_pass(self, authoritative_context, lang, q_text, ans_text):
        resolved = resolve_question_intent(q_text, authoritative_context, requested_language=lang)
        assert resolved.canonical_intent == CanonicalIntent.RECOMMENDATION_EXPLANATION
        assert resolved.target_crop == "Rice"
        check = validate_answer_is_grounded(ans_text, authoritative_context)
        assert check.passed, f"Failed for {lang}: {check.ungrounded_crop_claims}, {check.ungrounded_numeric_claims}"


# ---------------------------------------------------------------------------
# Section 20.B & 20.C — Water and Fertilizer
# ---------------------------------------------------------------------------

class TestSection20BC_Resources:
    @pytest.mark.parametrize("lang,q_text,ans_text", [
        ("en", "How much water is needed?", "The recommended water allocation is 133650 L/week (~19093 L/day)."),
        ("hi", "कितना पानी चाहिए?", "अनुशंसित जल आवंटन 133650 लीटर/सप्ताह (लगभग 19093 लीटर/दिन) है।"),
        ("mr", "किती पाणी आवश्यक आहे?", "शिफारस केलेले पाणी वाटप 133650 लिटर/आठवडा (सुमारे 19093 लिटर/दिवस) आहे."),
    ])
    def test_20b_water_queries(self, authoritative_context, lang, q_text, ans_text):
        resolved = resolve_question_intent(q_text, authoritative_context, requested_language=lang)
        assert resolved.canonical_intent in {CanonicalIntent.WATER_REQUIREMENT, CanonicalIntent.RESOURCE_PLAN}
        check = validate_answer_is_grounded(ans_text, authoritative_context)
        assert check.passed

    @pytest.mark.parametrize("lang,q_text,ans_text", [
        ("en", "How much fertilizer is required?", "The optimized fertilizer dosage is 53.8 kg/acre of nitrogen."),
        ("hi", "कितना उर्वरक चाहिए?", "अनुकूलित उर्वरक खुराक 53.8 किग्रा/एकड़ नाइट्रोजन है।"),
        ("mr", "किती खत आवश्यक आहे?", "खताचा अनुकूलित डोस 53.8 किग्रॅ/एकड नायट्रोजन आहे."),
    ])
    def test_20c_fertilizer_queries(self, authoritative_context, lang, q_text, ans_text):
        resolved = resolve_question_intent(q_text, authoritative_context, requested_language=lang)
        assert resolved.canonical_intent in {CanonicalIntent.FERTILIZER_REQUIREMENT, CanonicalIntent.RESOURCE_PLAN}
        check = validate_answer_is_grounded(ans_text, authoritative_context)
        assert check.passed


# ---------------------------------------------------------------------------
# Section 20.D — Ranking Explanation
# ---------------------------------------------------------------------------

class TestSection20D_RankingExplanation:
    @pytest.mark.parametrize("lang,q_text,ans_text", [
        ("en", "Explain the crop ranking and scores.", "Rank 1 is Rice (TOPSIS: 0.7441), Rank 2 is Wheat (TOPSIS: 0.6120), Rank 3 is Groundnut (0.4224), Rank 4 is Soybean (0.4224)."),
        ("hi", "फसल रैंकिंग और स्कोर समझाइए।", "रैंक 1 चावल (TOPSIS: 0.7441), रैंक 2 गेहूं (TOPSIS: 0.6120), रैंक 3 मूंगफली (0.4224) और रैंक 4 सोयाबीन (0.4224) है।"),
        ("mr", "पिकांची क्रमवारी आणि स्कोअर समजावून सांगा.", "रँक 1 तांदूळ (TOPSIS: 0.7441), रँक 2 गहू (TOPSIS: 0.6120), रँक 3 भुईमूग (0.4224) आणि रँक 4 सोयाबीन (0.4224) आहे."),
    ])
    def test_20d_ranking_explanation(self, authoritative_context, lang, q_text, ans_text):
        resolved = resolve_question_intent(q_text, authoritative_context, requested_language=lang)
        assert resolved.canonical_intent == CanonicalIntent.RANKING_EXPLANATION
        check = validate_answer_is_grounded(ans_text, authoritative_context)
        assert check.passed


# ---------------------------------------------------------------------------
# Section 20.E — Complete Reasoning
# ---------------------------------------------------------------------------

class TestSection20E_CompleteReasoning:
    @pytest.mark.parametrize("lang,q_text,ans_text", [
        ("en", "Explain the complete reasoning behind the final recommendation.",
         "Rice achieved rank 1 with 0.7441 TOPSIS closeness because climate suitability was weighted highest at 44.95% (AHP 0.4495). Given heavy 470.2 mm rainfall and 23.7 °C temperature, Rice outperformed Wheat (0.6120). Water target is 133650 L/week (~19093 L/day) across 80 NSGA-II generations."),
        ("hi", "अंतिम सिफारिश के पीछे दिए गए पूरे तर्क को समझाइए।",
         "चावल ने 0.7441 TOPSIS स्कोर के साथ रैंक 1 हासिल किया क्योंकि जलवायु उपयुक्तता को 44.95% (AHP 0.4495) का उच्चतम भार दिया गया था। 470.2 मिमी भारी वर्षा में चावल गेहूं (0.6120) से बेहतर रहा। 80 पीढ़ियों के NSGA-II से जल लक्ष्य 133650 लीटर/सप्ताह (लगभग 19093 लीटर/दिन) है।"),
        ("mr", "अंतिम शिफारशीमागील संपूर्ण तर्क स्पष्ट करा.",
         "तांदळाने 0.7441 TOPSIS स्कोअरसह रँक 1 मिळवला कारण हवामानाला 44.95% (AHP 0.4495) चे सर्वाधिक वजन दिले होते. 470.2 मिमी पावसात तांदूळ गव्हापेक्षा (0.6120) अधिक योग्य ठरला. 80 पिढ्यांच्या NSGA-II मधून पाणी लक्ष्य 133650 लिटर/आठवडा (~19093 लिटर/दिवस) आहे."),
    ])
    def test_20e_complete_reasoning_passes(self, authoritative_context, lang, q_text, ans_text):
        resolved = resolve_question_intent(q_text, authoritative_context, requested_language=lang)
        assert resolved.canonical_intent == CanonicalIntent.COMPLETE_REASONING
        check = validate_answer_is_grounded(ans_text, authoritative_context)
        assert check.passed, f"Complete reasoning failed for {lang}: {check.ungrounded_numeric_claims}, {check.ungrounded_crop_claims}"


# ---------------------------------------------------------------------------
# Section 20.F — What-If Scenarios
# ---------------------------------------------------------------------------

class TestSection20F_WhatIfScenarios:
    @pytest.mark.parametrize("lang,q_text,ans_text", [
        ("en", "What would happen if my water availability decreased?",
         "Rice requires ~1200 mm water per season while Wheat requires only ~450 mm. If water availability drops below 133650 L/week, lower water demand crops like Wheat would become more favorable, but exact recalculation requires running the optimizer again."),
        ("hi", "अगर मेरी पानी की उपलब्धता कम हो जाए तो क्या होगा?",
         "चावल को प्रति सीजन ~1200 मिमी पानी की आवश्यकता होती है जबकि गेहूं को केवल ~450 मिमी की। यदि पानी 133650 लीटर से कम होता है तो गेहूं अधिक उपयुक्त होगा, पर सटीक गणना के लिए पुनः गणना आवश्यक है।"),
        ("mr", "माझ्या पाण्याची उपलब्धता कमी झाली तर काय होईल?",
         "तांदळाला हंगामात ~1200 मिमी पाण्याची गरज असते तर गव्हाला केवळ ~450 मिमी लागते. जर पाणी 133650 लिटरपेक्षा कमी झाले तर गहू अधिक फायदेशीर ठरेल, पण अचूक पुनर्गणनेसाठी मॉडेल पुन्हा चालवणे आवश्यक आहे."),
    ])
    def test_20f_what_if_passes(self, authoritative_context, lang, q_text, ans_text):
        resolved = resolve_question_intent(q_text, authoritative_context, requested_language=lang)
        assert resolved.canonical_intent == CanonicalIntent.WHAT_IF_SCENARIO
        assert resolved.is_hypothetical is True
        check = validate_answer_is_grounded(ans_text, authoritative_context)
        assert check.passed, f"What-if failed for {lang}: {check.ungrounded_numeric_claims}"


# ---------------------------------------------------------------------------
# Section 20.G — Mixed Language (Hinglish, Marathi-English)
# ---------------------------------------------------------------------------

class TestSection20G_MixedLanguage:
    def test_hinglish_topsis_question(self, authoritative_context):
        q = "Rice का TOPSIS score इतना high क्यों है?"
        ans = "चावल का TOPSIS स्कोर 0.7441 है क्योंकि 470.2 मिमी वर्षा में जलवायु उपयुक्तता (0.8922) सबसे अधिक थी।"
        resolved = resolve_question_intent(q, authoritative_context, requested_language="hi")
        assert resolved.target_crop == "Rice"
        check = validate_answer_is_grounded(ans, authoritative_context)
        assert check.passed

    def test_marathi_english_topsis_question(self, authoritative_context):
        q = "तांदूळचा TOPSIS score एवढा जास्त का आहे?"
        ans = "तांदळाचा TOPSIS स्कोअर 0.7441 आहे कारण 470.2 मिमी पावसात त्याची हवामान उपयुक्तता (0.8922) सर्वाधिक होती."
        resolved = resolve_question_intent(q, authoritative_context, requested_language="mr")
        assert resolved.target_crop == "Rice"
        check = validate_answer_is_grounded(ans, authoritative_context)
        assert check.passed


# ---------------------------------------------------------------------------
# Section 20.H — Paraphrased Questions
# ---------------------------------------------------------------------------

class TestSection20H_Paraphrases:
    @pytest.mark.parametrize("paraphrase", [
        "Why did you choose Rice?",
        "Why is Rice the final crop?",
        "What made Rice the best option?",
        "Why did Rice come first?",
        "Why did Rice get the highest rank?",
    ])
    def test_paraphrase_resolves_to_recommendation_explanation(self, authoritative_context, paraphrase):
        resolved = resolve_question_intent(paraphrase, authoritative_context)
        assert resolved.canonical_intent == CanonicalIntent.RECOMMENDATION_EXPLANATION
        assert resolved.target_crop == "Rice"


# ---------------------------------------------------------------------------
# Section 20.I — Numbers & Percentages
# ---------------------------------------------------------------------------

class TestSection20I_NumberConsistency:
    def test_percentages_and_daily_water_grounding(self, authoritative_context):
        ans = "AHP climate weight is 44.95% (0.4495). Water plan is 133650 L/week, which is ~19093 L/day."
        check = validate_answer_is_grounded(ans, authoritative_context)
        assert check.passed, f"Failed percentage/daily grounding: {check.ungrounded_numeric_claims}"


# ---------------------------------------------------------------------------
# Section 20.J — Unsupported Facts (Honest Rejection)
# ---------------------------------------------------------------------------

class TestSection20J_UnsupportedFacts:
    def test_unsupported_yield_projection_flagged(self, authoritative_context):
        # The model claims exact yield of 999.8 tonnes/acre, which is fabricated
        ans = "Rice will produce an exact yield of 999.8 tonnes per acre."
        check = validate_answer_is_grounded(ans, authoritative_context)
        assert not check.passed
        assert "999.8" in check.ungrounded_numeric_claims


# ---------------------------------------------------------------------------
# Section 20.K — Security & Authorization Guarantees
# ---------------------------------------------------------------------------

class TestSection20K_Security:
    def test_ownership_enforcement_prevents_unauthorized_access(self, client, auth_headers):
        # Querying an invalid or unauthorized recommendation returns 404
        resp = client.post(
            "/api/ai/chat",
            json={"recommendation_id": 999999, "question": "Why was rice chosen?", "language": "en"},
            headers=auth_headers,
        )
        assert resp.status_code == 404
