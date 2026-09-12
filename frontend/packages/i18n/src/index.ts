import i18next, { type i18n as I18n } from "i18next";
import { initReactI18next } from "react-i18next";

import en from "./locales/en.json";
import fr from "./locales/fr.json";
import { toLocale, type Locale } from "./format";

export * from "./format";
export { useTranslation, Trans } from "react-i18next";

export const resources = { fr: { translation: fr }, en: { translation: en } } as const;
export const SUPPORTED_LOCALES: Locale[] = ["fr", "en"];
const STORAGE_KEY = "mizan.locale";

export type InitOptions = {
  /** Extra resources of the app (merged into the `translation` namespace). */
  extra?: Partial<Record<Locale, Record<string, unknown>>>;
  locale?: Locale;
};

function storedLocale(): Locale | undefined {
  try {
    const value = globalThis.localStorage?.getItem(STORAGE_KEY);
    return value ? toLocale(value) : undefined;
  } catch {
    return undefined;
  }
}

function browserLocale(): Locale {
  const lang = globalThis.navigator?.language;
  return toLocale(lang);
}

/** Initialise i18next once per app; returns the instance for providers and tests. */
export function initI18n(options: InitOptions = {}): I18n {
  const locale = options.locale ?? storedLocale() ?? browserLocale();
  if (!i18next.isInitialized) {
    void i18next.use(initReactI18next).init({
      resources,
      lng: locale,
      fallbackLng: "fr",
      supportedLngs: SUPPORTED_LOCALES,
      interpolation: { escapeValue: false },
      returnNull: false,
    });
  }
  for (const [lng, bundle] of Object.entries(options.extra ?? {})) {
    if (bundle) i18next.addResourceBundle(lng, "translation", bundle, true, true);
  }
  if (i18next.language !== locale) void i18next.changeLanguage(locale);
  return i18next;
}

export function currentLocale(): Locale {
  return toLocale(i18next.language);
}

export async function setLocale(locale: Locale): Promise<void> {
  try {
    globalThis.localStorage?.setItem(STORAGE_KEY, locale);
  } catch {
    /* storage unavailable */
  }
  if (i18next.isInitialized) await i18next.changeLanguage(locale);
  if (globalThis.document) globalThis.document.documentElement.lang = locale;
}

/**
 * Translate an API error (RFC 9457 problem details with a `message_key`) into a message.
 * Keys are dotted (`auth.invalid_credentials`) and looked up under `errors`.
 */
export function messageForKey(messageKey: string | undefined, params?: Record<string, unknown>): string {
  if (!messageKey) return i18next.t("errors.common.internal_error");
  const key = `errors.${messageKey}`;
  return i18next.exists(key) ? i18next.t(key, params) : i18next.t("errors.common.internal_error");
}

export { i18next };
