import { describe, expect, it } from "vitest";

import { contrastRatio, ensureAAOnWhiteText, meetsAA, parseHex, toHex } from "./color";
import { PALETTE_HUES, WORKFLOW_PALETTE } from "./palette";
import { BRAND } from "./brand";
import { DURATION, EASING, EXIT_RATIO, exitDuration, motionVariables } from "./motion";
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
    expect(vars["--mz-bg-canvas"]).toBe(DARK["bg.canvas"]);
    expect(vars["--mz-primary"]).toBe("#FF8A00");
    expect(Object.keys(cssVariables("light"))).toContain("--mz-focus-ring");
  });

  it("carries the brand, radii, shadows and motion into the variables", () => {
    const vars = cssVariables("light");
    expect(vars["--mz-brand-orange"]).toBe(BRAND.orange);
    expect(vars["--mz-radius-card"]).toBe("12px");
    expect(vars["--mz-shadow-3"]).toContain("rgba");
    expect(vars["--mz-ease-spring"]).toBe(EASING.spring);
    expect(vars["--mz-duration-base"]).toBe("200ms");
  });

  it("parses short and long hex", () => {
    expect(toHex(parseHex("#abc"))).toBe("#AABBCC");
    expect(() => parseHex("blue")).toThrow();
  });
});

describe("brand (SPEC §21.2)", () => {
  it("derives the interactive primary from the mark orange", () => {
    // The raw mark is 3.35:1 on white — fine for the logo and large accents, not for buttons.
    expect(meetsAA("#FFFFFF", BRAND.orange)).toBe(false);
    expect(meetsAA("#FFFFFF", BRAND.orange, true)).toBe(true);
    expect(ensureAAOnWhiteText(BRAND.orange)).toBe(LIGHT.primary);
  });

  it("keeps the mark readable on both canvases", () => {
    expect(contrastRatio(BRAND.orange, LIGHT["bg.canvas"])).toBeGreaterThanOrEqual(3);
    expect(contrastRatio(BRAND.aqua, DARK["bg.canvas"])).toBeGreaterThanOrEqual(3);
  });
});

describe("motion (SPEC §21.6)", () => {
  it("keeps every duration inside the perceptible-but-not-slow band", () => {
    for (const [name, ms] of Object.entries(DURATION)) {
      expect(ms, name).toBeGreaterThanOrEqual(100);
      expect(ms, name).toBeLessThanOrEqual(400);
    }
  });

  it("leaves faster than it arrives", () => {
    expect(EXIT_RATIO).toBeLessThan(1);
    for (const name of Object.keys(DURATION) as (keyof typeof DURATION)[]) {
      expect(exitDuration(name), name).toBeLessThan(DURATION[name]);
    }
  });

  it("emits a variable for every duration, easing and travel distance", () => {
    const vars = motionVariables();
    expect(vars["--mz-duration-base"]).toBe("200ms");
    expect(vars["--mz-duration-base-exit"]).toBe("140ms");
    expect(vars["--mz-ease-out"]).toBe(EASING.out);
    expect(vars["--mz-travel-lg"]).toBe("12px");
  });

  it("uses no linear easing: real objects accelerate and decelerate", () => {
    for (const [name, curve] of Object.entries(EASING)) {
      expect(curve, name).toMatch(/^cubic-bezier\(/);
      expect(curve, name).not.toBe("cubic-bezier(0, 0, 1, 1)");
    }
  });
});
