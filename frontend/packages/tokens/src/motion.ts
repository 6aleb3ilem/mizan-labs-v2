/**
 * Motion tokens (SPEC §21.6).
 *
 * Rules the whole design system obeys:
 *
 * 1. **Fast.** UI motion is 120–260 ms. Anything a user triggers and waits on is under 200 ms;
 *    only large surfaces (drawers, dialogs) reach 260 ms. Nothing in the product animates for
 *    longer than `slower` — a slow interface reads as a broken one after the tenth repetition.
 * 2. **Enter eases out, exit eases in, and exit is shorter.** An element arriving decelerates
 *    into place (`out`); an element leaving accelerates away (`in`) in ~70 % of the time,
 *    because nobody wants to watch a dismissal.
 * 3. **Transform and opacity only.** Never animate width, height, top or box-shadow — they
 *    force layout on every frame. Move with `translate`, size with `scale`, fade with `opacity`.
 * 4. **Movement is small.** 4–8 px for menus and tooltips, 12 px for toasts. Big travel
 *    distances feel sluggish however short the duration.
 * 5. **Origin matters.** A menu grows from its trigger, not from its own centre; Radix exposes
 *    `--radix-*-transform-origin` for exactly this.
 * 6. **Interruptible.** State-driven animations must be able to reverse mid-flight, so exits
 *    are animated rather than unmounted instantly.
 * 7. **Reduced motion is honoured** globally in `tokens.css`; never re-enable it locally.
 */

/** Durations in milliseconds. */
export const DURATION = {
  /** Colour and opacity changes on hover — perceived as instant. */
  instant: 100,
  /** Pressed states, checkbox and switch thumbs. */
  fast: 150,
  /** The default: menus, tooltips, popovers, tabs. */
  base: 200,
  /** Dialogs, toasts, anything covering content. */
  slow: 260,
  /** Drawers and full-height sheets only. */
  slower: 400,
} as const;

export type DurationName = keyof typeof DURATION;

/**
 * Easing curves.
 *
 * `spring` is the workhorse — a heavily weighted ease-out that settles like a critically
 * damped spring without the cost of a physics loop. It is what makes a drawer feel dragged
 * into place rather than tweened.
 */
export const EASING = {
  /** Entering: decelerate into rest. */
  out: "cubic-bezier(0.22, 1, 0.36, 1)",
  /** Leaving: accelerate away. */
  in: "cubic-bezier(0.4, 0, 1, 1)",
  /** Moves that both start and end on screen (reordering, repositioning). */
  inOut: "cubic-bezier(0.65, 0, 0.35, 1)",
  /** Large surfaces: drawers, sheets, toast stacks. */
  spring: "cubic-bezier(0.32, 0.72, 0, 1)",
  /** Emphasis for a single celebrated element — use sparingly. */
  emphasized: "cubic-bezier(0.16, 1, 0.3, 1)",
} as const;

export type EasingName = keyof typeof EASING;

/** Travel distances in pixels. Small on purpose — see rule 4. */
export const TRAVEL = {
  /** Menus, tooltips, popovers. */
  sm: "4px",
  /** Dialogs, dropdown content. */
  md: "8px",
  /** Toasts and anything entering from an edge. */
  lg: "12px",
} as const;

/** The scale a surface enters from. Below 0.95 reads as a zoom, not an arrival. */
export const ENTER_SCALE = 0.97;

/** Pressed feedback on buttons and rows: enough to feel, too little to notice. */
export const PRESS_SCALE = 0.985;

/** Exits run at this share of the enter duration (rule 2). */
export const EXIT_RATIO = 0.7;

export function exitDuration(name: DurationName): number {
  return Math.round(DURATION[name] * EXIT_RATIO);
}

/** `transition-property` groups — only compositor-friendly properties (rule 3). */
export const TRANSITION_PROPERTIES = {
  colors: "color, background-color, border-color, fill, stroke",
  transform: "transform",
  opacity: "opacity",
  /** The common pair for interactive surfaces. */
  motion: "transform, opacity",
} as const;

export type MotionVariables = Record<`--mz-${string}`, string>;

/** Motion custom properties, emitted into `:root` and consumed by the Tailwind theme. */
export function motionVariables(): MotionVariables {
  const vars: MotionVariables = {};
  for (const [name, value] of Object.entries(DURATION)) vars[`--mz-duration-${name}`] = `${value}ms`;
  for (const [name, value] of Object.entries(DURATION)) vars[`--mz-duration-${name}-exit`] = `${Math.round(value * EXIT_RATIO)}ms`;
  for (const [name, value] of Object.entries(EASING)) vars[`--mz-ease-${name.toLowerCase()}`] = value;
  for (const [name, value] of Object.entries(TRAVEL)) vars[`--mz-travel-${name}`] = value;
  vars["--mz-enter-scale"] = String(ENTER_SCALE);
  vars["--mz-press-scale"] = String(PRESS_SCALE);
  return vars;
}
