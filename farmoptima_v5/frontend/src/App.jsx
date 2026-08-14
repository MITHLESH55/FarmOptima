import React, { useState, useEffect } from "react";
import "leaflet/dist/leaflet.css";
import LocationBar from "./components/dashboard/LocationBar";
import LocationMapModal from "./components/dashboard/LocationMapModal";
import HeroRecommendation from "./components/dashboard/HeroRecommendation";
import SectionTabs from "./components/dashboard/SectionTabs";
import LiveFieldDataPanel from "./components/dashboard/LiveFieldDataPanel";
import AHPRankingPanel from "./components/dashboard/AHPRankingPanel";
import ResourcePlanPanel from "./components/dashboard/ResourcePlanPanel";
import ExplainabilityPanel from "./components/dashboard/ExplainabilityPanel";
import { LANGUAGES, getCurrentLocale, setCurrentLocale, t } from "./i18n";
import { Sprout, LogOut, Globe, User, ShieldCheck } from "lucide-react";

const API_BASE = "http://localhost:8000";
const TOKEN_KEY = "farmoptima_token";

export default function App() {
  const [token, setToken] = useState(null);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [isRegisterMode, setIsRegisterMode] = useState(false);
  
  // Default position: Pune, Maharashtra (18.5204, 73.8567)
  const [position, setPosition] = useState({ lat: 18.5204, lon: 73.8567 });
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [authError, setAuthError] = useState(null);
  const [authLoading, setAuthLoading] = useState(false);
  const [locale, setLocale] = useState(getCurrentLocale());
  const [activeTab, setActiveTab] = useState("live");
  const [isMapModalOpen, setIsMapModalOpen] = useState(false);

  useEffect(() => {
    setCurrentLocale(locale);
  }, [locale]);

  // Load token from localStorage on mount
  useEffect(() => {
    const storedToken = localStorage.getItem(TOKEN_KEY);
    if (storedToken) {
      setToken(storedToken);
    }
  }, []);

  async function handleLogin(e) {
    e.preventDefault();
    if (!username.trim() || !password.trim()) {
      setAuthError(t("auth.invalidLogin", locale));
      return;
    }

    setAuthLoading(true);
    setAuthError(null);

    try {
      const res = await fetch(`${API_BASE}/api/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });

      if (!res.ok) {
        const resData = await res.json();
        throw new Error(resData.error?.detail || t("auth.loginFailed", locale));
      }

      const resData = await res.json();
      const newToken = resData.access_token;
      
      localStorage.setItem(TOKEN_KEY, newToken);
      setToken(newToken);
      setUsername("");
      setPassword("");
      setAuthError(null);
    } catch (e) {
      setAuthError(
        e.message === "Failed to fetch"
          ? t("auth.backendDown", locale)
          : e.message
      );
    } finally {
      setAuthLoading(false);
    }
  }

  async function handleRegister(e) {
    e.preventDefault();
    if (!username.trim() || !password.trim()) {
      setAuthError(t("auth.invalidLogin", locale));
      return;
    }

    if (password.length < 8) {
      setAuthError(t("auth.atLeast8", locale));
      return;
    }

    setAuthLoading(true);
    setAuthError(null);

    try {
      const res = await fetch(`${API_BASE}/api/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });

      if (!res.ok) {
        const resData = await res.json();
        throw new Error(resData.error?.detail || t("auth.registrationFailed", locale));
      }

      setAuthError(null);
      setIsRegisterMode(false);
      
      // Auto-login after registration
      const loginRes = await fetch(`${API_BASE}/api/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });

      if (loginRes.ok) {
        const loginData = await loginRes.json();
        const newToken = loginData.access_token;
        localStorage.setItem(TOKEN_KEY, newToken);
        setToken(newToken);
        setUsername("");
        setPassword("");
      }
    } catch (e) {
      setAuthError(
        e.message === "Failed to fetch"
          ? t("auth.backendDown", locale)
          : e.message
      );
    } finally {
      setAuthLoading(false);
    }
  }

  function handleLogout() {
    localStorage.removeItem(TOKEN_KEY);
    setToken(null);
    setUsername("");
    setPassword("");
    setData(null);
    setError(null);
  }

  async function getRecommendation() {
    if (!position) return;
    if (!token) {
      setError(t("auth.invalidLogin", locale));
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const res = await fetch(`${API_BASE}/api/recommend`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`,
        },
        body: JSON.stringify(position),
      });

      if (res.status === 401) {
        localStorage.removeItem(TOKEN_KEY);
        setToken(null);
        setError(t("auth.sessionExpired", locale));
        return;
      }

      if (!res.ok) {
        const responseData = await res.json();
        const detail = responseData.error?.detail || responseData.detail || "Request failed";
        throw new Error(detail);
      }

      const resultData = await res.json();
      setData(resultData);
    } catch (e) {
      setError(
        e.message === "Failed to fetch"
          ? t("auth.backendDown", locale)
          : e.message
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-base text-ink-primary font-body antialiased flex flex-col">
      {/* Header Bar */}
      <header className="bg-surface border-b border-ink-secondary/15 sticky top-0 z-30 shadow-xs">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-brand-primary text-surface flex items-center justify-center shadow-md">
              <Sprout className="w-6 h-6 text-brand-accent" />
            </div>
            <div>
              <h1 className="text-xl font-display font-extrabold text-brand-primary tracking-tight">
                {t("header.title", locale)}
              </h1>
              <p className="text-xs text-ink-secondary hidden sm:block">
                {t("header.summary", locale)}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-4">
            {/* Language Selector */}
            <div className="flex items-center gap-1.5 bg-base px-3 py-1.5 rounded-lg border border-ink-secondary/15 text-xs text-ink-secondary">
              <Globe className="w-3.5 h-3.5 text-brand-primary" />
              <select
                value={locale}
                onChange={(e) => setLocale(e.target.value)}
                className="bg-transparent font-medium text-ink-primary border-none focus:ring-0 cursor-pointer text-xs"
              >
                {LANGUAGES.map((lang) => (
                  <option key={lang.code} value={lang.code}>{lang.label}</option>
                ))}
              </select>
            </div>

            {token && (
              <button
                onClick={handleLogout}
                className="flex items-center gap-1.5 text-xs font-semibold px-3 py-2 rounded-lg bg-status-risk/10 text-status-risk hover:bg-status-risk/20 border border-status-risk/20 transition-colors"
              >
                <LogOut className="w-3.5 h-3.5" />
                <span>{t("header.logout", locale)}</span>
              </button>
            )}
          </div>
        </div>
      </header>

      {!token ? (
        /* Login / Register Card view */
        <main className="flex-1 flex items-center justify-center p-6">
          <div className="w-full max-w-md bg-surface rounded-card border border-ink-secondary/20 shadow-card p-8">
            <div className="text-center mb-6">
              <div className="w-12 h-12 rounded-2xl bg-brand-primary/10 text-brand-primary mx-auto flex items-center justify-center mb-3">
                <ShieldCheck className="w-7 h-7 text-brand-primary" />
              </div>
              <h2 className="text-2xl font-display font-bold text-ink-primary">
                {isRegisterMode ? t("auth.createAccount", locale) : t("auth.login", locale)}
              </h2>
              <p className="text-xs text-ink-secondary mt-1">
                Access satellite NDVI analytics and multi-criteria decision modeling.
              </p>
            </div>

            <form onSubmit={isRegisterMode ? handleRegister : handleLogin} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-ink-secondary mb-1.5">
                  {t("auth.username", locale)}
                </label>
                <div className="relative">
                  <User className="w-4 h-4 text-ink-secondary absolute left-3 top-3" />
                  <input
                    type="text"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    className="w-full pl-9 pr-4 py-2.5 bg-base border border-ink-secondary/20 rounded-lg text-sm focus:outline-none focus:border-brand-primary"
                    placeholder={t("auth.enterUsername", locale)}
                    disabled={authLoading}
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-ink-secondary mb-1.5">
                  {t("auth.password", locale)}
                </label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full px-4 py-2.5 bg-base border border-ink-secondary/20 rounded-lg text-sm focus:outline-none focus:border-brand-primary"
                  placeholder={t("auth.enterPassword", locale)}
                  disabled={authLoading}
                />
                {isRegisterMode && (
                  <p className="text-[11px] text-ink-secondary mt-1">{t("auth.atLeast8", locale)}</p>
                )}
              </div>

              {authError && (
                <div className="text-xs text-status-risk bg-status-risk/10 p-3 rounded-lg border border-status-risk/20 font-medium">
                  {authError}
                </div>
              )}

              <button
                type="submit"
                disabled={authLoading}
                className="w-full py-3 rounded-lg bg-brand-primary text-surface font-semibold text-sm hover:bg-brand-primary/90 disabled:opacity-50 transition-colors shadow-sm"
              >
                {authLoading
                  ? (isRegisterMode ? t("auth.creatingAccount", locale) : t("auth.loggingIn", locale))
                  : (isRegisterMode ? t("auth.register", locale) : t("auth.login", locale))}
              </button>
            </form>

            <div className="mt-6 text-center text-xs">
              <button
                onClick={() => {
                  setIsRegisterMode(!isRegisterMode);
                  setAuthError(null);
                }}
                className="text-brand-primary font-bold hover:underline"
              >
                {isRegisterMode ? t("auth.alreadyHaveAccount", locale) : t("auth.needAccount", locale)}
              </button>
            </div>
          </div>
        </main>
      ) : (
        /* Main Dashboard view */
        <>
          {/* LocationBar */}
          <LocationBar
            position={position}
            onOpenMap={() => setIsMapModalOpen(true)}
            onGetRecommendation={getRecommendation}
            loading={loading}
            locale={locale}
          />

          <main className="max-w-7xl mx-auto px-6 py-6 space-y-6 flex-1 w-full">
            {error && (
              <div className="bg-status-risk/10 border border-status-risk/30 text-status-risk p-4 rounded-xl text-sm font-semibold flex items-center justify-between">
                <span>{error}</span>
                <button
                  onClick={() => setError(null)}
                  className="text-xs text-status-risk underline font-bold"
                >
                  Dismiss
                </button>
              </div>
            )}

            {/* Hero Recommendation Component */}
            <HeroRecommendation data={data} loading={loading} locale={locale} />

            {/* Section Tabs Controller */}
            {data && (
              <SectionTabs activeTab={activeTab} onChange={setActiveTab} locale={locale}>
                {activeTab === "live" && <LiveFieldDataPanel data={data} locale={locale} />}
                {activeTab === "ahp" && <AHPRankingPanel data={data} locale={locale} />}
                {activeTab === "plan" && (
                  <div className="space-y-6">
                    <ResourcePlanPanel data={data} locale={locale} />
                    <ExplainabilityPanel data={data} locale={locale} />
                  </div>
                )}
              </SectionTabs>
            )}
          </main>

          {/* Location Map Modal (opens on demand) */}
          <LocationMapModal
            isOpen={isMapModalOpen}
            onClose={() => setIsMapModalOpen(false)}
            position={position}
            onSelect={setPosition}
            onConfirm={() => {
              if (position) {
                getRecommendation();
              }
            }}
            locale={locale}
          />
        </>
      )}
    </div>
  );
}
