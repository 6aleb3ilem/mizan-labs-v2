import { SEMANTIC_HUE, WORKFLOW_PALETTE, isPaletteHue, type PaletteHue } from "@mizan/tokens";
import type { CSSProperties, ReactNode } from "react";

import { cn } from "../cn";

export type BadgeTone = PaletteHue | keyof typeof SEMANTIC_HUE | "primary";

export type BadgeProps = {
  children: ReactNode;
  /** A palette hue (workflow state colour) or a semantic tone. */
  tone?: BadgeTone | string;
  size?: "sm" | "md";
  dot?: boolean;
  className?: string;
  title?: string;
};

function hueOf(tone: string | undefined): PaletteHue | "primary" {
  if (!tone) return "slate";
  if (tone === "primary") return "primary";
  if (tone in SEMANTIC_HUE) return SEMANTIC_HUE[tone as keyof typeof SEMANTIC_HUE];
  return isPaletteHue(tone) ? tone : "slate";
}

/** State badge: colours come from the fixed accessible palette, never arbitrary hex (SPEC §21.2). */
export function Badge({ children, tone, size = "md", dot, className, title }: BadgeProps) {
  const hue = hueOf(tone);
  const style: CSSProperties =
    hue === "primary"
      ? { background: "var(--mz-primary-subtle)", color: "var(--mz-primary)", borderColor: "var(--mz-primary)" }
      : {
          background: `var(--mz-hue-${hue}-bg, ${WORKFLOW_PALETTE[hue].light.bg})`,
          color: `var(--mz-hue-${hue}-fg, ${WORKFLOW_PALETTE[hue].light.fg})`,
          borderColor: `var(--mz-hue-${hue}-border, ${WORKFLOW_PALETTE[hue].light.border})`,
        };
  return (
    <span
      title={title}
      style={style}
      className={cn("inline-flex items-center gap-1.5 whitespace-nowrap rounded-full border font-medium", size === "sm" ? "h-5 px-2 text-xs" : "h-6 px-2.5 text-sm", className)}
    >
      {dot && <span className="size-1.5 rounded-full bg-current" aria-hidden />}
      {children}
    </span>
  );
}

/** CSS variables of the workflow palette for the current theme; apply on the root element. */
export function paletteVariables(theme: "light" | "dark"): Record<string, string> {
  const vars: Record<string, string> = {};
  for (const [hue, tokens] of Object.entries(WORKFLOW_PALETTE)) {
    const variant = tokens[theme];
    vars[`--mz-hue-${hue}-bg`] = variant.bg;
    vars[`--mz-hue-${hue}-fg`] = variant.fg;
    vars[`--mz-hue-${hue}-border`] = variant.border;
  }
  return vars;
}
