import { BRAND } from "./brand";
import { ensureAAOnWhiteText, onColor, shade, shiftLightness, tint } from "./color";
import { motionVariables } from "./motion";

/**
 * The default theme (SPEC §21.2), built on the Mizan mark.
 *
 * The neutrals are warm — they carry a trace of the mark's orange — so that the brand does not
 * sit on a cold grey that fights it. `primary` is the mark orange darkened until white text on
 * it reaches AA (the raw `BRAND.orange` stays available for the mark and large accents), and
 * `info` is the aqua half of the diamond taken down to a readable depth.
 */
export const LIGHT = {
  "bg.canvas": "#F7F6F4",
  "bg.surface": "#FFFFFF",
  "bg.subtle": "#F0EEEA",
  "border.default": "#E0DCD5",
  "text.primary": "#17140F",
  "text.secondary": "#6B6259",
  "text.inverse": "#FFFFFF",
  primary: "#BF4E12",
  success: "#12805C",
  warning: "#B26B00",
  danger: "#C62828",
  info: "#0E6B69",
} as const;

export const DARK = {
  "bg.canvas": "#0E0D0C",
  "bg.surface": "#171614",
  "bg.subtle": "#201E1B",
  "border.default": "#302D29",
  "text.primary": "#EDEAE5",
  "text.secondary": "#A29A90",
  "text.inverse": "#0E0D0C",
  primary: "#F3A272",
  success: "#3CCB93",
  warning: "#F5B342",
  danger: "#FF6B6B",
  info: "#46C7C4",
} as const;

export type ThemeName = "light" | "dark";
export type BaseTokens = typeof LIGHT;
export type TokenName = keyof BaseTokens;

/**
 * Radii nest: an inner radius equals its parent's radius minus the padding between them, so a
 * `control` inside a `card` with 4 px of padding looks concentric rather than pinched.
 */
export const RADIUS = { xs: "4px", control: "8px", card: "12px", dialog: "16px", pill: "999px" } as const;
export const SPACING = [4, 8, 12, 16, 24, 32, 48] as const;

/**
 * Layered shadows: several stacked shadows with growing blur and falling opacity read as light
 * falling on an object, where one wide blur reads as a grey smudge. Tinted with the warm ink of
 * the neutrals rather than pure black.
 */
export const SHADOW = {
  0: "0 0 0 1px rgba(23, 20, 15, 0.05)",
  1: "0 1px 1px rgba(23, 20, 15, 0.04), 0 2px 2px rgba(23, 20, 15, 0.03)",
  2: "0 1px 1px rgba(23, 20, 15, 0.04), 0 2px 4px rgba(23, 20, 15, 0.04), 0 4px 8px rgba(23, 20, 15, 0.04)",
  3: "0 1px 2px rgba(23, 20, 15, 0.04), 0 4px 8px rgba(23, 20, 15, 0.05), 0 12px 24px rgba(23, 20, 15, 0.07), 0 24px 48px rgba(23, 20, 15, 0.06)",
} as const;
export const FONT_SIZES = [12, 13, 14, 16, 20, 24, 30] as const;

export type PrimaryScale = {
  primary: string;
  hover: string;
  subtle: string;
  on: string;
  ring: string;
};

/** Derive the primary scale (hover = -8 % lightness, subtle = 92 % tint) with AA guaranteed. */
export function derivePrimary(brand: string, theme: ThemeName = "light"): PrimaryScale {
  const primary = theme === "light" ? ensureAAOnWhiteText(brand) : brand;
  const hover = theme === "light" ? shiftLightness(primary, -0.08) : shiftLightness(primary, 0.06);
  const subtle = theme === "light" ? tint(primary, 0.92) : shade(primary, 0.75);
  return { primary, hover, subtle, on: onColor(primary), ring: `${primary}66` };
}

export type CssVariables = Record<`--${string}`, string>;

/** CSS custom properties for a theme; `brand` overrides the primary (tenant setting). */
export function cssVariables(theme: ThemeName, brand?: string): CssVariables {
  const base = theme === "light" ? LIGHT : DARK;
  const scale = derivePrimary(brand ?? base.primary, theme);
  const vars: CssVariables = {};
  for (const [name, value] of Object.entries(base)) {
    vars[`--mz-${name.replace(".", "-")}`] = value;
  }
  vars["--mz-primary"] = scale.primary;
  vars["--mz-primary-hover"] = scale.hover;
  vars["--mz-primary-subtle"] = scale.subtle;
  vars["--mz-primary-on"] = scale.on;
  vars["--mz-focus-ring"] = scale.ring;
  for (const [name, value] of Object.entries(BRAND)) vars[`--mz-brand-${name}`] = value;
  for (const [name, value] of Object.entries(RADIUS)) vars[`--mz-radius-${name}`] = value;
  for (const [name, value] of Object.entries(SHADOW)) vars[`--mz-shadow-${name}`] = value;
  Object.assign(vars, motionVariables());
  return vars;
}

/** Apply a theme (and optional brand colour) to a root element. */
export function applyTheme(root: HTMLElement, theme: ThemeName, brand?: string): void {
  for (const [name, value] of Object.entries(cssVariables(theme, brand))) {
    root.style.setProperty(name, value);
  }
  root.dataset["theme"] = theme;
  root.style.colorScheme = theme;
}
