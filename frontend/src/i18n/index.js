import en from "./locales/en.json";
import hi from "./locales/hi.json";
import mr from "./locales/mr.json";

export const LANGUAGES = [
  { code: "en", label: "English" },
  { code: "hi", label: "हिन्दी" },
  { code: "mr", label: "मराठी" },
];

const LOCALES = { en, hi, mr };
const STORAGE_KEY = "farmoptima_language";

export function getCurrentLocale() {
  if (typeof window === "undefined") return "en";
  const saved = localStorage.getItem(STORAGE_KEY);
  return LANGUAGES.some((lang) => lang.code === saved) ? saved : "en";
}

export function setCurrentLocale(locale) {
  const next = LANGUAGES.some((lang) => lang.code === locale) ? locale : "en";
  if (typeof window !== "undefined") {
    localStorage.setItem(STORAGE_KEY, next);
  }
  return next;
}

export function t(key, locale = getCurrentLocale(), params = {}) {
  const target = LOCALES[locale] || LOCALES.en;
  const value = key.split(".").reduce((obj, segment) => obj?.[segment], target) || key;

  return Object.entries(params).reduce((text, [param, replacement]) => {
    return text.replace(new RegExp(`{{\\s*${param}\\s*}}`, "g"), String(replacement));
  }, value);
}

export function translateCropName(cropName, locale = getCurrentLocale()) {
  if (!cropName) return "";

  const normalized = String(cropName).trim();
  const canonical = normalized.charAt(0).toUpperCase() + normalized.slice(1).toLowerCase();
  const key = `crops.${canonical}`;
  const translated = t(key, locale);
  return translated === key ? normalized : translated;
}

