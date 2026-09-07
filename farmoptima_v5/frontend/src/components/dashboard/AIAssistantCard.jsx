import React, { useState, useRef, useEffect } from "react";
import {
  Sparkles,
  Mic,
  MicOff,
  Send,
  Volume2,
  VolumeX,
  Square,
  AlertCircle,
  CheckCircle2,
  Bot,
  User,
  Loader2,
} from "lucide-react";
import { t, translateCropName } from "../../i18n";

const API_BASE = "";

export default function AIAssistantCard({ data, token, locale }) {
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [loadingStatus, setLoadingStatus] = useState("");
  const [error, setError] = useState(null);

  // Interaction conversation history / current response
  const [transcript, setTranscript] = useState(null);
  const [answer, setAnswer] = useState(null);
  const [groundedFields, setGroundedFields] = useState([]);
  const [audioBase64, setAudioBase64] = useState(null);
  const [isPlayingAudio, setIsPlayingAudio] = useState(false);

  // Voice recording states
  const [isRecording, setIsRecording] = useState(false);
  const [recordingSeconds, setRecordingSeconds] = useState(0);

  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const recordingTimerRef = useRef(null);
  const audioPlayerRef = useRef(null);

  const recommendationId = data?.id;

  // Cleanup audio player and recording on unmount or recommendation change
  useEffect(() => {
    return () => {
      if (recordingTimerRef.current) clearInterval(recordingTimerRef.current);
      if (audioPlayerRef.current) {
        audioPlayerRef.current.pause();
        audioPlayerRef.current = null;
      }
      if (mediaRecorderRef.current && mediaRecorderRef.current.state === "recording") {
        mediaRecorderRef.current.stop();
      }
    };
  }, []);

  // When recommendation changes, clear old answer/transcript if it was for another recommendation
  useEffect(() => {
    setTranscript(null);
    setAnswer(null);
    setGroundedFields([]);
    setAudioBase64(null);
    setError(null);
    if (audioPlayerRef.current) {
      audioPlayerRef.current.pause();
      audioPlayerRef.current = null;
      setIsPlayingAudio(false);
    }
  }, [recommendationId]);

  // Suggested dynamic questions based on current recommendation
  const topCrop = translateCropName(data?.crop_ranking?.[0]?.crop, locale) || "this crop";
  const suggestedQuestions = [
    t("assistant.suggestedWhy", locale, { crop: topCrop }),
    t("assistant.suggestedWater", locale),
    t("assistant.suggestedRanking", locale),
    t("assistant.suggestedNdvi", locale),
  ];

  // Helper to map error response into friendly, farmer-facing message
  function mapErrorMessage(resStatus, errorObj) {
    if (resStatus === 401) {
      return t("assistant.errorSessionExpired", locale);
    }
    if (resStatus === 404) {
      return t("assistant.errorRecommendationUnavailable", locale);
    }
    if (resStatus === 429) {
      return t("assistant.errorTooManyRequests", locale);
    }
    if (resStatus === 400) {
      const code = errorObj?.error?.code || errorObj?.code;
      if (code === "empty_transcript") {
        return t("assistant.errorEmptyTranscript", locale);
      }
      if (code === "invalid_audio") {
        return t("assistant.errorInvalidAudio", locale);
      }
      return t("assistant.errorUnclearRequest", locale);
    }
    if (resStatus >= 500) {
      return t("assistant.errorServiceUnavailable", locale);
    }
    return t("assistant.errorConnect", locale);
  }

  // Handle typed text question (POST /api/ai/chat)
  async function handleSendText(textToSend) {
    const q = (textToSend || question).trim();
    if (!q) return;

    if (!recommendationId) {
      setError(t("assistant.generateFirst", locale));
      return;
    }

    setLoading(true);
    setLoadingStatus(t("assistant.loadingText", locale));
    setError(null);
    setTranscript(q);

    // Stop previous audio if playing
    if (audioPlayerRef.current) {
      audioPlayerRef.current.pause();
      setIsPlayingAudio(false);
    }

    try {
      const res = await fetch(`${API_BASE}/api/ai/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          recommendation_id: recommendationId,
          question: q,
          language: locale,
        }),
      });

      if (!res.ok) {
        let errData = {};
        try {
          errData = await res.json();
        } catch {
          // ignore parse error
        }
        throw new Error(mapErrorMessage(res.status, errData));
      }

      const result = await res.json();
      setAnswer(result.answer);
      setGroundedFields(result.grounded_fields_used || []);
      setAudioBase64(null); // Text endpoint doesn't synthesize TTS
      setQuestion("");
    } catch (err) {
      setError(
        err.message === "Failed to fetch"
          ? t("assistant.errorConnect", locale)
          : err.message
      );
    } finally {
      setLoading(false);
      setLoadingStatus("");
    }
  }

  // Handle voice question recording
  async function toggleRecording() {
    if (isRecording) {
      // Stop recording
      stopRecording();
    } else {
      // Start recording
      await startRecording();
    }
  }

  async function startRecording() {
    if (!recommendationId) {
      setError(t("assistant.generateFirst", locale));
      return;
    }

    if (!navigator.mediaDevices || !window.MediaRecorder) {
      setError(t("assistant.errorVoiceUnsupported", locale));
      return;
    }

    setError(null);
    audioChunksRef.current = [];

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

      // Determine supported MIME type
      let mimeType = "audio/webm";
      const candidates = [
        "audio/webm;codecs=opus",
        "audio/webm",
        "audio/mp4",
        "audio/ogg;codecs=opus",
        "audio/wav",
      ];
      for (const cand of candidates) {
        if (MediaRecorder.isTypeSupported(cand)) {
          mimeType = cand;
          break;
        }
      }

      const recorder = new MediaRecorder(stream, { mimeType });
      mediaRecorderRef.current = recorder;

      recorder.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) {
          audioChunksRef.current.push(e.data);
        }
      };

      recorder.onstop = async () => {
        // Stop all audio tracks to release microphone
        stream.getTracks().forEach((track) => track.stop());

        const audioBlob = new Blob(audioChunksRef.current, { type: mimeType });
        if (audioBlob.size > 0) {
          await submitVoiceQuestion(audioBlob, mimeType);
        } else {
          setError(t("assistant.errorNoAudio", locale));
        }
      };

      recorder.start(250); // Slice data every 250ms
      setIsRecording(true);
      setRecordingSeconds(0);

      // Start timer
      recordingTimerRef.current = setInterval(() => {
        setRecordingSeconds((prev) => prev + 1);
      }, 1000);
    } catch (err) {
      if (err.name === "NotAllowedError" || err.name === "PermissionDeniedError") {
        setError(t("assistant.errorMicPermission", locale));
      } else {
        setError(t("assistant.errorMicAccess", locale, { detail: err.message || t("assistant.unknownError", locale) }));
      }
    }
  }

  function stopRecording() {
    if (recordingTimerRef.current) {
      clearInterval(recordingTimerRef.current);
      recordingTimerRef.current = null;
    }
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === "recording") {
      mediaRecorderRef.current.stop();
    }
    setIsRecording(false);
  }

  // Submit audio blob to POST /api/ai/voice
  async function submitVoiceQuestion(audioBlob, mimeType) {
    setLoading(true);
    setLoadingStatus(t("assistant.loadingVoice", locale));
    setError(null);

    // Stop previous audio
    if (audioPlayerRef.current) {
      audioPlayerRef.current.pause();
      setIsPlayingAudio(false);
    }

    try {
      const formData = new FormData();
      formData.append("recommendation_id", String(recommendationId));

      const ext = mimeType.includes("mp4") ? "mp4" : mimeType.includes("wav") ? "wav" : "webm";
      formData.append("audio", audioBlob, `voice-question.${ext}`);
      formData.append("enable_tts", "true");

      const res = await fetch(`${API_BASE}/api/ai/voice`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      });

      if (!res.ok) {
        let errData = {};
        try {
          errData = await res.json();
        } catch {
          // ignore parse error
        }
        throw new Error(mapErrorMessage(res.status, errData));
      }

      const result = await res.json();
      setTranscript(result.transcript);
      setAnswer(result.answer);
      setGroundedFields(result.grounded_fields_used || []);
      setAudioBase64(result.audio_base64 || null);
    } catch (err) {
      setError(
        err.message === "Failed to fetch"
          ? t("assistant.errorConnect", locale)
          : err.message
      );
    } finally {
      setLoading(false);
      setLoadingStatus("");
    }
  }

  // Audio Playback handler (User-controlled, no autoplay)
  function handlePlayAudio() {
    if (!audioBase64) return;

    if (isPlayingAudio && audioPlayerRef.current) {
      audioPlayerRef.current.pause();
      setIsPlayingAudio(false);
      return;
    }

    try {
      const audioUrl = `data:audio/mp3;base64,${audioBase64}`;
      const audio = new Audio(audioUrl);
      audioPlayerRef.current = audio;

      audio.onended = () => {
        setIsPlayingAudio(false);
      };
      audio.onerror = () => {
        setIsPlayingAudio(false);
        setError(t("assistant.errorAudioPlayback", locale));
      };

      audio.play();
      setIsPlayingAudio(true);
    } catch {
      setIsPlayingAudio(false);
      setError(t("assistant.errorAudioPlayback", locale));
    }
  }

  // Format seconds as MM:SS
  function formatTime(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
  }

  // Helper to format grounded field names cleanly
  function formatGroundedField(field) {
    if (field.startsWith("crop_ranking[")) {
      return "Crop Ranking Order";
    }
    const map = {
      ndvi: "NDVI Satellite Data",
      rainfall_mm_last_30d: "Rainfall Window",
      avg_temp_c: "Average Temperature",
      humidity_pct: "Relative Humidity",
      solar_radiation_mj_m2: "Solar Radiation",
      wind_speed_m_s: "Wind Speed",
      soil_ph: "Soil pH",
      soil_moisture_pct: "Soil Moisture",
      soil_nitrogen_mg_kg: "Soil Nitrogen",
      soil_organic_carbon_g_kg: "Organic Carbon",
      soil_sand_pct: "Soil Sand %",
      soil_clay_pct: "Soil Clay %",
      "resource_plan.water_liters_per_week": "Water Requirement",
      "resource_plan.fertilizer_kg_per_acre": "Fertilizer Schedule",
      "resource_plan.irrigation_schedule": "Irrigation Plan",
      "crop_ranking.topsis_closeness": "TOPSIS Closeness",
      "crop_ranking.electre_net_outranking": "ELECTRE Rank",
      ahp_weights: "AHP Agronomic Weights",
      "resource_plan.pareto_front": "NSGA-II Pareto Optimization",
      crop_ranking: "Crop Ranking",
    };
    return map[field] || field;
  }

  const isAssistantDisabled = !recommendationId;

  return (
    <div className="bg-surface rounded-card border border-brand-primary/20 shadow-card overflow-hidden transition-all">
      {/* Header Bar */}
      <div className="p-5 sm:p-6 bg-brand-primary/5 border-b border-brand-primary/15 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-brand-primary text-surface flex items-center justify-center shadow-xs flex-shrink-0">
            <Sparkles className="w-5 h-5 text-brand-accent" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="font-display font-bold text-lg text-ink-primary">
                {t("assistant.title", locale)}
              </h3>
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-brand-primary/10 text-brand-primary border border-brand-primary/20">
                <Bot className="w-3 h-3" />
                <span>{t("assistant.tag", locale)}</span>
              </span>
            </div>
            <p className="text-xs text-ink-secondary mt-0.5">
              {t("assistant.subtitle", locale)}
            </p>
          </div>
        </div>

        {/* Status Indicator */}
        <div className="flex items-center gap-2 text-xs font-semibold text-ink-secondary">
          {isRecording ? (
            <span className="flex items-center gap-1.5 text-status-risk animate-pulse bg-status-risk/10 px-3 py-1.5 rounded-lg border border-status-risk/20">
              <span className="w-2 h-2 rounded-full bg-status-risk animate-ping" />
              {t("assistant.recording", locale, { time: formatTime(recordingSeconds) })}
            </span>
          ) : loading ? (
            <span className="flex items-center gap-1.5 text-brand-primary bg-brand-primary/10 px-3 py-1.5 rounded-lg border border-brand-primary/20">
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
              {t("assistant.processing", locale)}
            </span>
          ) : (
            <span className="flex items-center gap-1.5 text-status-good bg-status-good/10 px-3 py-1 rounded-md border border-status-good/20 text-[11px]">
              <CheckCircle2 className="w-3 h-3" />
              {t("assistant.ready", locale)}
            </span>
          )}
        </div>
      </div>

      {/* Main Body */}
      <div className="p-5 sm:p-6 space-y-5">
        {/* Disabled Warning if no recommendation loaded */}
        {isAssistantDisabled && (
          <div className="p-4 rounded-xl bg-base border border-ink-secondary/20 text-ink-secondary text-xs flex items-center gap-2.5 font-medium">
            <AlertCircle className="w-4 h-4 text-brand-accent flex-shrink-0" />
            <span>{t("assistant.generateFirst", locale)}</span>
          </div>
        )}

        {/* Error banner */}
        {error && (
          <div className="p-4 rounded-xl bg-status-risk/10 border border-status-risk/30 text-status-risk text-xs font-semibold flex items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              <span>{error}</span>
            </div>
            <button
              onClick={() => setError(null)}
              className="text-status-risk hover:underline font-bold text-xs"
            >
              {t("assistant.dismiss", locale)}
            </button>
          </div>
        )}

        {/* Question Input and Microphone Bar */}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSendText();
          }}
          className="space-y-3"
        >
          <div className="relative flex items-center gap-2">
            <div className="relative flex-1">
              <input
                type="text"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                placeholder={
                  isRecording
                    ? t("assistant.recordingVoice", locale)
                    : t("assistant.questionPlaceholder", locale)
                }
                disabled={isAssistantDisabled || loading || isRecording}
                maxLength={2000}
                className="w-full pl-4 pr-12 py-3 bg-base border border-ink-secondary/20 rounded-xl text-sm text-ink-primary focus:outline-none focus:border-brand-primary focus:ring-1 focus:ring-brand-primary transition-all disabled:opacity-60 placeholder:text-ink-secondary/60 shadow-inner"
              />
              <button
                type="submit"
                disabled={isAssistantDisabled || loading || isRecording || !question.trim()}
                title={t("assistant.sendQuestion", locale)}
                aria-label={t("assistant.sendQuestion", locale)}
                className="absolute right-2 top-2 p-2 rounded-lg bg-brand-primary text-surface hover:bg-brand-primary/90 disabled:opacity-30 transition-all cursor-pointer disabled:cursor-not-allowed shadow-xs"
              >
                <Send className="w-4 h-4" />
              </button>
            </div>

            {/* Voice Microphone Button */}
            <button
              type="button"
              onClick={toggleRecording}
              disabled={isAssistantDisabled || loading}
              title={isRecording ? t("assistant.stopRecording", locale) : t("assistant.startRecording", locale)}
              aria-label={isRecording ? t("assistant.stopRecording", locale) : t("assistant.startRecording", locale)}
              className={`p-3 rounded-xl font-semibold text-sm flex items-center gap-2 transition-all cursor-pointer disabled:cursor-not-allowed flex-shrink-0 shadow-sm ${
                isRecording
                  ? "bg-status-risk text-surface hover:bg-status-risk/90 ring-4 ring-status-risk/20 animate-pulse"
                  : "bg-brand-primary/10 text-brand-primary hover:bg-brand-primary/20 border border-brand-primary/30"
              } disabled:opacity-40`}
            >
              {isRecording ? (
                <>
                  <Square className="w-4 h-4 fill-current" />
                  <span className="text-xs font-mono font-bold hidden sm:inline">
                    {formatTime(recordingSeconds)}
                  </span>
                </>
              ) : (
                <>
                  <Mic className="w-4 h-4 text-brand-primary" />
                  <span className="text-xs font-bold hidden sm:inline">Ask by Voice</span>
                </>
              )}
            </button>
          </div>

          {/* Suggested Quick Question Chips */}
          {!isAssistantDisabled && !isRecording && (
            <div className="flex items-center gap-2 flex-wrap pt-1">
              <span className="text-[11px] font-bold text-ink-secondary uppercase tracking-wider">
                {t("assistant.suggested", locale)}
              </span>
              {suggestedQuestions.map((sq, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => handleSendText(sq)}
                  disabled={loading}
                  className="px-3 py-1 rounded-full text-xs font-medium bg-base hover:bg-brand-primary/10 text-ink-secondary hover:text-brand-primary border border-ink-secondary/15 hover:border-brand-primary/30 transition-colors text-left disabled:opacity-50 cursor-pointer"
                >
                  {sq}
                </button>
              ))}
            </div>
          )}
        </form>

        {/* Loading Spinner / State */}
        {loading && (
          <div className="p-6 rounded-xl bg-base border border-ink-secondary/15 flex flex-col items-center justify-center gap-3 text-center">
            <Loader2 className="w-7 h-7 text-brand-primary animate-spin" />
            <p className="text-xs font-semibold text-ink-secondary">
              {loadingStatus || t("assistant.loadingText", locale)}
            </p>
          </div>
        )}

        {/* Active Conversation / Answer Panel */}
        {!loading && (transcript || answer) && (
          <div className="rounded-xl border border-brand-primary/20 bg-base/50 p-5 space-y-4">
            {/* User Question */}
            {transcript && (
              <div className="flex items-start gap-3">
                <div className="w-7 h-7 rounded-lg bg-ink-primary/10 text-ink-primary flex items-center justify-center flex-shrink-0 mt-0.5">
                  <User className="w-4 h-4" />
                </div>
                <div className="flex-1">
                  <span className="text-[11px] font-bold uppercase tracking-wider text-ink-secondary block">
                    {t("assistant.youAsked", locale)}
                  </span>
                  <p className="text-sm font-semibold text-ink-primary mt-0.5">
                    "{transcript}"
                  </p>
                </div>
              </div>
            )}

            {/* AI Grounded Answer */}
            {answer && (
              <div className="pt-3 border-t border-ink-secondary/10 flex items-start gap-3">
                <div className="w-7 h-7 rounded-lg bg-brand-primary text-surface flex items-center justify-center flex-shrink-0 mt-0.5 shadow-xs">
                  <Bot className="w-4 h-4 text-brand-accent" />
                </div>
                <div className="flex-1 space-y-3">
                  <div>
                    <span className="text-[11px] font-bold uppercase tracking-wider text-brand-primary block">
                      {t("assistant.farmOptimaAi", locale)}
                    </span>
                    <p className="text-sm text-ink-primary font-normal leading-relaxed mt-1 whitespace-pre-wrap">
                      {answer}
                    </p>
                  </div>

                  {/* Audio Playback Controls (if TTS audio_base64 is available) */}
                  {audioBase64 && (
                    <div className="pt-2 flex items-center gap-3">
                      <button
                        type="button"
                        onClick={handlePlayAudio}
                        className={`inline-flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold border transition-all cursor-pointer shadow-xs ${
                          isPlayingAudio
                            ? "bg-brand-primary text-surface border-brand-primary"
                            : "bg-surface text-brand-primary border-brand-primary/30 hover:bg-brand-primary/10"
                        }`}
                      >
                        {isPlayingAudio ? (
                          <>
                            <Square className="w-3.5 h-3.5 fill-current" />
                            <span>{t("assistant.stopVoice", locale)}</span>
                          </>
                        ) : (
                          <>
                            <Volume2 className="w-3.5 h-3.5" />
                            <span>{t("assistant.playVoice", locale)}</span>
                          </>
                        )}
                      </button>
                    </div>
                  )}

                  {/* Grounding Attribution Chips */}
                  {groundedFields && groundedFields.length > 0 && (
                    <div className="pt-2 border-t border-ink-secondary/10">
                      <span className="text-[10px] font-bold uppercase tracking-wider text-ink-secondary block mb-1.5">
                        {t("assistant.groundedIn", locale)}
                      </span>
                      <div className="flex flex-wrap gap-1.5">
                        {Array.from(new Set(groundedFields.map(formatGroundedField))).map((gf, idx) => (
                          <span
                            key={idx}
                            className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-medium bg-surface text-ink-secondary border border-ink-secondary/15"
                          >
                            <span className="w-1.5 h-1.5 rounded-full bg-brand-primary" />
                            {gf}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
