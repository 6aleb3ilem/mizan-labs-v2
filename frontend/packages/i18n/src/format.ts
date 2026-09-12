/** Number, money and date formatting by locale (SPEC §21.7). Amounts are strings from the API. */

export type Locale = "fr" | "en";

const NUMBER_LOCALE: Record<Locale, string> = { fr: "fr-FR", en: "en-GB" };

export function toLocale(value: string | undefined | null): Locale {
  return value?.toLowerCase().startsWith("en") ? "en" : "fr";
}

export function formatNumber(value: number | string | null | undefined, locale: Locale, digits = 2): string {
  if (value === null || value === undefined || value === "") return "";
  const n = typeof value === "string" ? Number(value) : value;
  if (Number.isNaN(n)) return String(value);
  return new Intl.NumberFormat(NUMBER_LOCALE[locale], {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(n);
}

/** Money is formatted with the code after the amount ("60 610,00 MRU"), never a symbol. */
export function formatMoney(value: number | string | null | undefined, currency: string, locale: Locale): string {
  const text = formatNumber(value, locale, 2);
  return text ? `${text}\u00a0${currency}`.trim() : "";
}

export function formatDate(value: string | Date | null | undefined, locale: Locale): string {
  if (!value) return "";
  const date = typeof value === "string" ? new Date(value.length === 10 ? `${value}T00:00:00` : value) : value;
  if (Number.isNaN(date.getTime())) return String(value);
  return new Intl.DateTimeFormat(NUMBER_LOCALE[locale], { day: "2-digit", month: "2-digit", year: "numeric" }).format(date);
}

export function formatDateTime(value: string | Date | null | undefined, locale: Locale): string {
  if (!value) return "";
  const date = typeof value === "string" ? new Date(value) : value;
  if (Number.isNaN(date.getTime())) return String(value);
  return new Intl.DateTimeFormat(NUMBER_LOCALE[locale], {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

export function formatRelative(value: string | Date, locale: Locale, now: Date = new Date()): string {
  const date = typeof value === "string" ? new Date(value) : value;
  const diff = (date.getTime() - now.getTime()) / 1000;
  const rtf = new Intl.RelativeTimeFormat(NUMBER_LOCALE[locale], { numeric: "auto" });
  const abs = Math.abs(diff);
  if (abs < 60) return rtf.format(Math.round(diff), "second");
  if (abs < 3600) return rtf.format(Math.round(diff / 60), "minute");
  if (abs < 86400) return rtf.format(Math.round(diff / 3600), "hour");
  return rtf.format(Math.round(diff / 86400), "day");
}

/** Pick the translation of a `{fr, en}` labels object with fallbacks. */
export function pickLabel(labels: Record<string, string | null | undefined> | null | undefined, locale: Locale): string {
  if (!labels) return "";
  return labels[locale] || labels["fr"] || labels["en"] || Object.values(labels).find((v) => !!v) || "";
}
