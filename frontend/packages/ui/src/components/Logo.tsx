/**
 * The Mizan Labs mark (SPEC §21.2).
 *
 * Drawn as inline SVG rather than shipped as an image: it inherits the theme, stays crisp at
 * favicon size, costs no request, and the reticle can animate. `assets/mizan-logo.png` holds
 * the original artwork this is traced from, for print and for anything outside the apps.
 *
 * The geometry is a plumb-bob diamond — aqua above, orange below — crossed by a spirit-level
 * bar through a bubble reticle. The colours are fixed brand values and deliberately do not
 * follow the tenant's primary: a tenant may re-brand its documents, not the platform's mark.
 */
import { forwardRef, type SVGProps } from "react";

import { cn } from "../cn";

const ORANGE = "#E9631A";
const AQUA = "#B2F0EF";

export type LogoMarkProps = SVGProps<SVGSVGElement> & {
  /** Height in pixels; the width follows the aspect ratio. */
  size?: number;
  /** The bar colour. Defaults to the ink of the artwork, `currentColor` inverts cleanly. */
  barColor?: string;
};

export const LogoMark = forwardRef<SVGSVGElement, LogoMarkProps>(function LogoMark(
  { size = 28, barColor = "currentColor", className, ...props },
  ref,
) {
  return (
    <svg
      ref={ref}
      viewBox="0 0 128 128"
      width={size}
      height={size}
      fill="none"
      role="presentation"
      aria-hidden
      className={cn("shrink-0", className)}
      {...props}
    >
      {/* Diamond, aqua body. */}
      <path d="M64 5 L123 64 L64 123 L5 64 Z" fill={AQUA} />
      {/* Lower-left quadrant, orange — the weighted end of the plumb bob. */}
      <path d="M5 64 L64 123 L64 64 Z" fill={ORANGE} />
      {/* Measurement graduations along the loaded edge. */}
      <g stroke={ORANGE} strokeWidth="3.5" strokeLinecap="round">
        <line x1="14" y1="73" x2="33" y2="73" />
        <line x1="20" y1="81" x2="39" y2="81" />
        <line x1="26" y1="89" x2="45" y2="89" />
      </g>
      {/* The level bar, running out of the reticle to the right edge. */}
      <rect x="64" y="60.5" width="62" height="7" rx="1" fill={barColor} />
      {/* Bubble reticle. */}
      <circle cx="58" cy="64" r="21" fill="var(--mz-bg-surface, #FFFFFF)" stroke={barColor} strokeWidth="2.5" />
      <g stroke={barColor} strokeWidth="2.5" strokeLinecap="round">
        <line x1="58" y1="52" x2="58" y2="76" />
        <line x1="46" y1="64" x2="70" y2="64" />
      </g>
    </svg>
  );
});

export type LogoProps = {
  /** Mark height in pixels; the wordmark scales with it. */
  size?: number;
  /** `full` is mark + wordmark, `mark` is the diamond alone. */
  variant?: "full" | "mark";
  /** Accessible name. Set `""` when the logo sits beside a visible product name. */
  label?: string;
  className?: string;
};

/**
 * Mark plus wordmark. The wordmark is set in the UI font rather than traced as paths so it
 * stays legible at small sizes and follows the user's font settings; the artwork's own
 * lettering is kept in `assets/mizan-logo.png` for print.
 */
export function Logo({ size = 28, variant = "full", label = "Mizan Labs", className }: LogoProps) {
  const mark = <LogoMark size={size} barColor="var(--mz-brand-ink)" className="dark:[--mz-brand-ink:#EDEAE5]" />;
  if (variant === "mark") {
    return (
      <span className={cn("inline-flex", className)} role={label ? "img" : undefined} aria-label={label || undefined}>
        {mark}
        {label && <span className="sr-only">{label}</span>}
      </span>
    );
  }
  return (
    <span
      className={cn("inline-flex items-center gap-2 select-none", className)}
      role={label ? "img" : undefined}
      aria-label={label || undefined}
    >
      {mark}
      <span className="flex flex-col leading-none" aria-hidden>
        <span
          className="font-extrabold tracking-tight text-brand"
          style={{ fontSize: size * 0.68, letterSpacing: "-0.02em" }}
        >
          MIZAN
        </span>
        <span
          className="font-semibold text-info"
          style={{ fontSize: size * 0.34, letterSpacing: "0.08em", marginTop: size * 0.06 }}
        >
          labs
        </span>
      </span>
      {label && <span className="sr-only">{label}</span>}
    </span>
  );
}
