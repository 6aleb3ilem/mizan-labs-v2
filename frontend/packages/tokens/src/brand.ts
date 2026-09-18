/**
 * The Mizan Labs brand, sampled from the logo mark (SPEC §21.2).
 *
 * The mark is a plumb-bob diamond — aqua on the upper half, orange on the lower — crossed by
 * a spirit-level bar through a bubble reticle: balance, measurement, calibration. Those three
 * colours are the whole brand; everything else in the theme is neutral so that state colours
 * (workflow hues) stay legible against it.
 *
 * `ORANGE` is the raw mark colour and must only be used for the mark, accents and large text:
 * white body text on it is 3.0:1, below AA. `derivePrimary` darkens it for interactive
 * surfaces; use `--mz-primary` for those.
 */

export const BRAND = {
  /** MIZAN wordmark and the lower diamond fill. */
  orange: "#E9631A",
  /** Diamond body and the "labs" wordmark. */
  aqua: "#B2F0EF",
  /** The level bar. */
  ink: "#0A0A0A",
} as const;

export type BrandColor = keyof typeof BRAND;

/** Aqua shades: the sampled tint is too light to carry text, so darker steps are derived. */
export const AQUA = {
  50: "#F0FCFB",
  100: "#DCF7F6",
  200: "#B2F0EF",
  300: "#7FE0DE",
  400: "#46C7C4",
  500: "#1FA8A5",
  600: "#128683",
  700: "#0E6B69",
  800: "#0F5553",
  900: "#0F3F3E",
} as const;

/** Orange shades derived from the mark for hover, subtle fills and dark-theme lifts. */
export const ORANGE = {
  50: "#FEF4ED",
  100: "#FCE5D4",
  200: "#F8C6A6",
  300: "#F3A272",
  400: "#EF8244",
  500: "#E9631A",
  600: "#C9500F",
  700: "#A33F0C",
  800: "#7D310B",
  900: "#5C250A",
} as const;
