import { describe, expect, it } from "vitest";

import { contrastRatio, ensureAAOnWhiteText, meetsAA, parseHex, toHex } from "./color";
import { PALETTE_HUES, WORKFLOW_PALETTE } from "./palette";
import { DARK, LIGHT, cssVariables, derivePrimary } from "./theme";

describe("default theme contrast (SPEC §21.7: validated at build)", () => {
  it("body text reads on every surface, light and dark", () => {
    for (const t of [LIGHT, DARK]) {
      for (const surface of [t["bg.canvas"], t["bg.surface"], t["bg.subtle"]]) {
        expect(contrastRatio(t["text.primary"], surface)).toBeGreaterThanOrEqual(4.5);
        expect(contrastRatio(t["text.secondary"], surface)).toBeGreaterThanOrEqual(4.5);
      }
    }
  });

  it("inverse text reads on the primary and the semantic colours", () => {
    for (const name of ["primary", "success", "danger", "info"] as const) {
      expect(meetsAA(LIGHT["text.inverse"], LIGHT[name]), name).toBe(true);
    }
    // warning is reserved for large text, icons and borders (3:1), never for body text
    expect(meetsAA(LIGHT["text.inverse"], LIGHT.warning, true)).toBe(true);
    expect(meetsAA(LIGHT.warning, LIGHT["bg.surface"], true)).toBe(true);
  });

  it("every workflow hue is readable in both variants", () => {
    for (const hue of PALETTE_HUES) {
      const { light, dark } = WORKFLOW_PALETTE[hue];
      expect(contrastRatio(light.fg, light.bg), `${hue} light`).toBeGreaterThanOrEqual(4.5);
      expect(contrastRatio(dark.fg, dark.bg), `${hue} dark`).toBeGreaterThanOrEqual(4.5);
    }
  });
});

describe("tenant primary derivation", () => {
  it("auto-adjusts a bright brand orange to AA for white text", () => {
    const scale = derivePrimary("#FF8A00");
    expect(scale.primary).not.toBe("#FF8A00");
    expect(contrastRatio("#FFFFFF", scale.primary)).toBeGreaterThanOrEqual(4.5);
    expect(scale.on).toBe("#FFFFFF");
    expect(contrastRatio(scale.hover, scale.primary)).toBeLessThan(2); // a nearby shade
    expect(contrastRatio(LIGHT["text.primary"], scale.subtle)).toBeGreaterThanOrEqual(4.5);
  });

  it("keeps a compliant brand colour untouched", () => {
    expect(ensureAAOnWhiteText("#1F5EFF")).toBe("#1F5EFF");
    expect(derivePrimary("#1F5EFF").primary).toBe("#1F5EFF");
  });

  it("emits CSS variables for both themes", () => {
    const vars = cssVariables("dark", "#FF8A00");
    expect(vars["--mz-bg-canvas"]).toBe("#0B1220");
    expect(vars["--mz-primary"]).toBe("#FF8A00");
    expect(Object.keys(cssVariables("light"))).toContain("--mz-focus-ring");
  });

  it("parses short and long hex", () => {
    expect(toHex(parseHex("#abc"))).toBe("#AABBCC");
    expect(() => parseHex("blue")).toThrow();
  });
});
