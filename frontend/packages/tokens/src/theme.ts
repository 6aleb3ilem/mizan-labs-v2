import { ensureAAOnWhiteText, onColor, shade, shiftLightness, tint } from "./color";

/** The default theme of SPEC §21.2. */
export const LIGHT = {
  "bg.canvas": "#F6F7F9",
  "bg.surface": "#FFFFFF",
  "bg.subtle": "#EEF1F5",
  "border.default": "#D9DEE7",
  "text.primary": "#111827",
  "text.secondary": "#5B6472",
  "text.inverse": "#FFFFFF",
  primary: "#1F5EFF",
  success: "#12805C",
  warning: "#B26B00",
  danger: "#C62828",
  info: "#0E7490",
} as const;

export const DARK = {
  "bg.canvas": "#0B1220",
  "bg.surface": "#111A2E",
  "bg.subtle": "#182238",
  "border.default": "#26324A",
  "text.primary": "#E5E9F0",
  "text.secondary": "#9AA5B5",
  "text.inverse": "#0B1220",
  primary: "#6D94FF",
  success: "#3CCB93",
  warning: "#F5B342",
  danger: "#FF6B6B",
  info: "#4FD1E5",
} as const;

export type ThemeName = "light" | "dark";
export type BaseTokens = typeof LIGHT;
export type TokenName = keyof BaseTokens;

export const RADIUS = { control: "6px", card: "10px", dialog: "14px" } as const;
export const SPACING = [4, 8, 12, 16, 24, 32, 48] as const;
export const SHADOW = {
  1: "0 1px 2px rgba(17, 24, 39, 0.06), 0 1px 1px rgba(17, 24, 39, 0.04)",
  2: "0 2px 6px rgba(17, 24, 39, 0.08), 0 1px 2px rgba(17, 24, 39, 0.05)",
  3: "0 8px 24px rgba(17, 24, 39, 0.12), 0 2px 6px rgba(17, 24, 39, 0.06)",
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
