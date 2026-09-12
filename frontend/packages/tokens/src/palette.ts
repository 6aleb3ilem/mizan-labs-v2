/** The 12 accessible hues an administrator may choose for workflow states (SPEC §21.2). */

export type PaletteHue =
  | "slate" | "gray" | "red" | "orange" | "amber" | "green"
  | "teal" | "blue" | "indigo" | "violet" | "pink" | "brown";

export type HueVariant = { bg: string; fg: string; border: string };
export type HueTokens = { light: HueVariant; dark: HueVariant };

/** Each hue: a subtle background, a readable foreground (AA on that background) and a border. */
export const WORKFLOW_PALETTE: Record<PaletteHue, HueTokens> = {
  slate:  { light: { bg: "#E8ECF2", fg: "#334155", border: "#B8C2D1" }, dark: { bg: "#1F2A3D", fg: "#C7D2E3", border: "#3B4A63" } },
  gray:   { light: { bg: "#EDEEF0", fg: "#3F444C", border: "#C2C6CD" }, dark: { bg: "#262B33", fg: "#CBD0D8", border: "#444B56" } },
  red:    { light: { bg: "#FBE4E4", fg: "#9F1D1D", border: "#F0B4B4" }, dark: { bg: "#3D1B1B", fg: "#FFB3B3", border: "#6B2A2A" } },
  orange: { light: { bg: "#FCE8D8", fg: "#9A3F0B", border: "#F2C0A0" }, dark: { bg: "#3E2414", fg: "#FFC29A", border: "#6E3E1F" } },
  amber:  { light: { bg: "#FCEFCB", fg: "#7A4B00", border: "#F0D48A" }, dark: { bg: "#3D2E0F", fg: "#FFD57A", border: "#6E5420" } },
  green:  { light: { bg: "#DDF3E7", fg: "#0F5F43", border: "#A6DEC1" }, dark: { bg: "#123326", fg: "#8CE2B8", border: "#215A44" } },
  teal:   { light: { bg: "#D8F2F1", fg: "#0F5F5C", border: "#9EDBD8" }, dark: { bg: "#10312F", fg: "#8CE0DC", border: "#1F5754" } },
  blue:   { light: { bg: "#DFE9FF", fg: "#1D46B8", border: "#B1C6F6" }, dark: { bg: "#172A52", fg: "#A8C0FF", border: "#2B4585" } },
  indigo: { light: { bg: "#E4E4FB", fg: "#3730A3", border: "#BEBEF0" }, dark: { bg: "#232251", fg: "#BBB9FF", border: "#3D3B88" } },
  violet: { light: { bg: "#EFE3FA", fg: "#6B21A8", border: "#D3B9EE" }, dark: { bg: "#2F1B47", fg: "#D8B4FE", border: "#553280" } },
  pink:   { light: { bg: "#FBE2EE", fg: "#9D174D", border: "#F0B4D0" }, dark: { bg: "#421A2E", fg: "#FFB1D2", border: "#742B4F" } },
  brown:  { light: { bg: "#F0E6DE", fg: "#6B4423", border: "#D8C1AE" }, dark: { bg: "#3A2A1F", fg: "#E1BFA3", border: "#63472F" } },
};

export const PALETTE_HUES = Object.keys(WORKFLOW_PALETTE) as PaletteHue[];

export function isPaletteHue(value: string): value is PaletteHue {
  return value in WORKFLOW_PALETTE;
}

/** Semantic colours for states whose meaning is fixed (SPEC §21.2). */
export const SEMANTIC_HUE: Record<"success" | "warning" | "danger" | "info" | "neutral", PaletteHue> = {
  success: "green",
  warning: "amber",
  danger: "red",
  info: "teal",
  neutral: "slate",
};
