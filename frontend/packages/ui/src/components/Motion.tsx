/**
 * Motion utilities and the small components built on them (SPEC §21.6).
 *
 * Everything here obeys the rules in `@mizan/tokens/motion`: transform and opacity only, fast
 * durations, ease-out on the way in, and nothing at all when the user has asked for reduced
 * motion.
 */
import { useCallback, useEffect, useLayoutEffect, useRef, useState, type HTMLAttributes, type ReactNode } from "react";

import { cn } from "../cn";

/** Tracks the user's reduced-motion preference, including changes made while the app is open. */
export function useReducedMotion(): boolean {
  const [reduced, setReduced] = useState(() => globalThis.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false);
  useEffect(() => {
    const query = globalThis.matchMedia?.("(prefers-reduced-motion: reduce)");
    if (!query) return;
    const update = (event: MediaQueryListEvent) => setReduced(event.matches);
    query.addEventListener("change", update);
    return () => query.removeEventListener("change", update);
  }, []);
  return reduced;
}

/**
 * Suspends every transition and animation on the document for a moment.
 *
 * Two cases need it. A theme flip would otherwise animate every colour on the page at once, a
 * wave of fades that reads as a glitch. A window resize turns responsive layout jumps into
 * visible slides. Both are cured by dropping transitions for the duration of the change.
 */
export function useTransitionSuppressor(): (during?: () => void) => void {
  const timer = useRef<ReturnType<typeof setTimeout>>(undefined);
  const suppress = useCallback((during?: () => void) => {
    const root = document.documentElement;
    root.classList.add("mz-no-transitions");
    during?.();
    clearTimeout(timer.current);
    // Two frames: one for the class to take effect, one for the change to paint under it.
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        timer.current = setTimeout(() => root.classList.remove("mz-no-transitions"), 0);
      });
    });
  }, []);
  useEffect(() => () => clearTimeout(timer.current), []);
  return suppress;
}

/** Suppresses transitions while the window is being resized. Mount once, in the app shell. */
export function useResizeTransitionGuard(): void {
  const suppress = useTransitionSuppressor();
  useEffect(() => {
    let frame = 0;
    const onResize = () => {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(() => suppress());
    };
    window.addEventListener("resize", onResize);
    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener("resize", onResize);
    };
  }, [suppress]);
}

export type SkeletonProps = HTMLAttributes<HTMLDivElement> & {
  /** Tailwind width class or a CSS width. Vary it across lines so a block does not look printed. */
  width?: string;
  /** `text` matches a line of body copy, `block` fills its container, `circle` is an avatar. */
  shape?: "text" | "block" | "circle";
};

/**
 * A loading placeholder shaped like the content it stands in for.
 *
 * A skeleton that matches the final layout keeps the page from jumping when data lands; a
 * generic grey box does not, and is worse than a spinner. Skeletons are for first loads only —
 * a refetch of data already on screen should leave the old value visible.
 */
export function Skeleton({ className, width, shape = "block", style, ...props }: SkeletonProps) {
  return (
    <div
      aria-hidden
      className={cn(
        "mz-skeleton",
        shape === "text" && "h-[1em] rounded-xs",
        shape === "block" && "h-full w-full rounded-control",
        shape === "circle" && "aspect-square rounded-full",
        className,
      )}
      style={{ width, ...style }}
      {...props}
    />
  );
}

/** A table-shaped skeleton: the same columns and row height the real table will have. */
export function SkeletonRows({ rows = 5, columns = 4, className }: { rows?: number; columns?: number; className?: string }) {
  // Deterministic, uneven widths: a column of identical bars reads as a pattern, not as data.
  const widths = ["68%", "42%", "85%", "55%", "73%", "38%"];
  return (
    <div className={cn("flex flex-col", className)} aria-hidden>
      {Array.from({ length: rows }, (_, row) => (
        <div key={row} className="flex items-center gap-4 border-b border-line px-3 py-3 last:border-0">
          {Array.from({ length: columns }, (_, column) => (
            <div key={column} className="flex-1">
              <Skeleton shape="text" width={widths[(row * columns + column) % widths.length]} />
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}

/**
 * An indeterminate spinner.
 *
 * `delay` holds it back: a request that resolves in 150 ms should show nothing at all, because
 * a spinner that flashes for two frames reads as a fault. Anything under ~400 ms feels instant
 * without one.
 */
export function Spinner({ size = 16, delay = 400, className, label }: { size?: number; delay?: number; className?: string; label?: string }) {
  const [visible, setVisible] = useState(delay === 0);
  useEffect(() => {
    if (delay === 0) return;
    const timer = setTimeout(() => setVisible(true), delay);
    return () => clearTimeout(timer);
  }, [delay]);
  if (!visible) return null;
  return (
    <span role="status" aria-live="polite" className={cn("inline-flex items-center gap-2", className)}>
      <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden style={{ animation: "mz-spin 700ms linear infinite" }}>
        <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="2.5" opacity="0.18" />
        <path d="M21 12a9 9 0 0 0-9-9" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
      </svg>
      {label && <span className="text-sm text-muted">{label}</span>}
    </span>
  );
}

/**
 * A number that animates to its new value instead of snapping.
 *
 * Used for counters and totals that change under the user — an unread badge, a queue length, a
 * running total. The eye follows the change and knows what moved. Values are formatted through
 * `Intl`, and the element is `tabular` so the width never shifts mid-count.
 */
export function AnimatedNumber({
  value,
  format,
  duration = 400,
  className,
}: {
  value: number;
  format?: (value: number) => string;
  duration?: number;
  className?: string;
}) {
  const reduced = useReducedMotion();
  const [display, setDisplay] = useState(value);
  const from = useRef(value);
  const frame = useRef(0);

  // When motion is off the value is rendered directly, so the effect only tracks the origin
  // for a later animation and never sets state.
  const animated = !reduced && duration > 0;

  useLayoutEffect(() => {
    if (!animated || from.current === value) {
      from.current = value;
      return;
    }
    const start = performance.now();
    const origin = from.current;
    const distance = value - origin;
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / duration);
      // Ease-out cubic: the count decelerates into its final value.
      const eased = 1 - Math.pow(1 - t, 3);
      setDisplay(origin + distance * eased);
      if (t < 1) frame.current = requestAnimationFrame(tick);
      else from.current = value;
    };
    frame.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame.current);
  }, [value, duration, animated]);

  const rounded = Math.round(animated ? display : value);
  return (
    <span className={cn("tabular", className)}>
      {format ? format(rounded) : rounded.toLocaleString()}
    </span>
  );
}

/** A keyboard key. Shows the platform's own modifier glyphs so the hint matches the keyboard. */
export function Kbd({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <kbd
      className={cn(
        "inline-flex h-5 min-w-5 items-center justify-center rounded-xs border border-line bg-subtle px-1.5",
        "font-sans text-xs font-medium text-muted shadow-[inset_0_-1px_0_rgba(23,20,15,0.06)]",
        className,
      )}
    >
      {children}
    </kbd>
  );
}

/**
 * `true` on Apple platforms, so shortcut hints can show ⌘ rather than Ctrl.
 *
 * Read once at mount rather than from an effect: the platform cannot change under a running
 * app, and a second render just to correct the glyph would flash the wrong key.
 */
export function useIsApple(): boolean {
  const [apple] = useState(() => {
    const agent = globalThis.navigator;
    return agent ? /mac|iphone|ipad/i.test(agent.platform || agent.userAgent) : false;
  });
  return apple;
}

/** The modifier glyph for this platform, for use in `<Kbd>`. */
export function useModifierKey(): string {
  return useIsApple() ? "⌘" : "Ctrl";
}

/**
 * Flashes a soft highlight when `trigger` changes.
 *
 * Applied to a row that changed under the user — someone else's edit arriving over SSE, or a
 * record that has just saved. It answers "what just moved?" without a toast.
 */
export function useChangeHighlight<T extends HTMLElement>(trigger: unknown) {
  const ref = useRef<T>(null);
  const first = useRef(true);
  useEffect(() => {
    if (first.current) {
      first.current = false;
      return;
    }
    const node = ref.current;
    if (!node) return;
    node.classList.remove("mz-highlight");
    // Force a reflow so the animation restarts even when it is already running.
    void node.offsetWidth;
    node.classList.add("mz-highlight");
  }, [trigger]);
  return ref;
}
