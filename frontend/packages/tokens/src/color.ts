/** Colour maths for token derivation and WCAG contrast validation (SPEC §21.2, §21.7). */

export type Rgb = { r: number; g: number; b: number };
export type Hsl = { h: number; s: number; l: number };

export function parseHex(hex: string): Rgb {
  const clean = hex.trim().replace(/^#/, "");
  const full = clean.length === 3 ? clean.split("").map((c) => c + c).join("") : clean;
  if (!/^[0-9a-fA-F]{6}$/.test(full)) throw new Error(`invalid colour ${hex}`);
  return {
    r: parseInt(full.slice(0, 2), 16),
    g: parseInt(full.slice(2, 4), 16),
    b: parseInt(full.slice(4, 6), 16),
  };
}

export function toHex({ r, g, b }: Rgb): string {
  const c = (v: number) => Math.round(Math.min(255, Math.max(0, v))).toString(16).padStart(2, "0");
  return `#${c(r)}${c(g)}${c(b)}`.toUpperCase();
}

export function rgbToHsl({ r, g, b }: Rgb): Hsl {
  const rn = r / 255, gn = g / 255, bn = b / 255;
  const max = Math.max(rn, gn, bn), min = Math.min(rn, gn, bn);
  const l = (max + min) / 2;
  if (max === min) return { h: 0, s: 0, l };
  const d = max - min;
  const s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
  let h: number;
  if (max === rn) h = ((gn - bn) / d + (gn < bn ? 6 : 0)) / 6;
  else if (max === gn) h = ((bn - rn) / d + 2) / 6;
  else h = ((rn - gn) / d + 4) / 6;
  return { h: h * 360, s, l };
}

export function hslToRgb({ h, s, l }: Hsl): Rgb {
  const hn = ((h % 360) + 360) % 360 / 360;
  if (s === 0) return { r: l * 255, g: l * 255, b: l * 255 };
  const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
  const p = 2 * l - q;
  const channel = (t: number) => {
    let tt = t;
    if (tt < 0) tt += 1;
    if (tt > 1) tt -= 1;
    if (tt < 1 / 6) return p + (q - p) * 6 * tt;
    if (tt < 1 / 2) return q;
    if (tt < 2 / 3) return p + (q - p) * (2 / 3 - tt) * 6;
    return p;
  };
  return { r: channel(hn + 1 / 3) * 255, g: channel(hn) * 255, b: channel(hn - 1 / 3) * 255 };
}

function linear(v: number): number {
  const c = v / 255;
  return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
}

/** Relative luminance per WCAG 2.x. */
export function luminance(rgb: Rgb): number {
  return 0.2126 * linear(rgb.r) + 0.7152 * linear(rgb.g) + 0.0722 * linear(rgb.b);
}

/** Contrast ratio between two colours (1..21). */
export function contrastRatio(a: string, b: string): number {
  const la = luminance(parseHex(a));
  const lb = luminance(parseHex(b));
  const [hi, lo] = la > lb ? [la, lb] : [lb, la];
  return (hi + 0.05) / (lo + 0.05);
}

export const AA_TEXT = 4.5;
export const AA_LARGE = 3;

export function meetsAA(foreground: string, background: string, large = false): boolean {
  return contrastRatio(foreground, background) >= (large ? AA_LARGE : AA_TEXT);
}

/** Lighten (positive) or darken (negative) by a lightness delta in [-1, 1]. */
export function shiftLightness(hex: string, delta: number): string {
  const hsl = rgbToHsl(parseHex(hex));
  return toHex(hslToRgb({ ...hsl, l: Math.min(1, Math.max(0, hsl.l + delta)) }));
}

/** Mix `hex` with white (`tint` in 0..1 is the share of white). */
export function tint(hex: string, share: number): string {
  const rgb = parseHex(hex);
  return toHex({
    r: rgb.r + (255 - rgb.r) * share,
    g: rgb.g + (255 - rgb.g) * share,
    b: rgb.b + (255 - rgb.b) * share,
  });
}

/** Mix `hex` with black. */
export function shade(hex: string, share: number): string {
  const rgb = parseHex(hex);
  return toHex({ r: rgb.r * (1 - share), g: rgb.g * (1 - share), b: rgb.b * (1 - share) });
}

/** The text colour (white or near-black) that reads best on `background`. */
export function onColor(background: string): string {
  return contrastRatio("#FFFFFF", background) >= contrastRatio("#111827", background) ? "#FFFFFF" : "#111827";
}

/**
 * Adjust a brand colour until white text on it reaches AA (4.5:1) by darkening in small
 * steps; the hue is preserved. Returns the original when it already complies.
 */
export function ensureAAOnWhiteText(hex: string, target = AA_TEXT): string {
  let current = toHex(parseHex(hex));
  for (let i = 0; i < 40 && contrastRatio("#FFFFFF", current) < target; i += 1) {
    current = shiftLightness(current, -0.02);
  }
  return current;
}
