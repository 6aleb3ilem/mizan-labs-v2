import { describe, expect, it } from "vitest";

import { formatDate, formatMoney, formatNumber, pickLabel } from "./format";
import { initI18n, messageForKey, resources, setLocale } from "./index";

describe("formatters", () => {
  it("formats money by locale with the code after the amount", () => {
    expect(formatMoney("60610.00", "MRU", "fr")).toBe("60 610,00 MRU");
    expect(formatMoney("60610.00", "MRU", "en")).toBe("60,610.00 MRU");
    expect(formatNumber("22.5", "fr", 1)).toBe("22,5");
    expect(formatDate("2026-09-11", "fr")).toBe("11/09/2026");
    expect(formatDate("2026-09-11", "en")).toBe("11/09/2026");
  });

  it("picks labels with fallbacks", () => {
    expect(pickLabel({ fr: "Béton", en: "Concrete" }, "en")).toBe("Concrete");
    expect(pickLabel({ fr: "Béton" }, "en")).toBe("Béton");
    expect(pickLabel(null, "fr")).toBe("");
  });
});

describe("resources", () => {
  it("has the same keys in French and English", () => {
    const flatten = (obj: Record<string, unknown>, prefix = ""): string[] =>
      Object.entries(obj).flatMap(([k, v]) =>
        typeof v === "object" && v !== null ? flatten(v as Record<string, unknown>, `${prefix}${k}.`) : [`${prefix}${k}`],
      );
    const fr = flatten(resources.fr.translation).sort();
    const en = flatten(resources.en.translation).sort();
    expect(en).toEqual(fr);
  });

  it("translates problem details by message_key", async () => {
    initI18n({ locale: "fr" });
    expect(messageForKey("auth.invalid_credentials")).toBe("E-mail ou mot de passe incorrect.");
    await setLocale("en");
    expect(messageForKey("auth.invalid_credentials")).toBe("Incorrect e-mail or password.");
    expect(messageForKey("something.unknown")).toBe("Unexpected error. Retry; if it persists, contact support.");
  });
});
