/**
 * Toasts (SPEC §21.4, §21.6).
 *
 * A stack, not a list. New toasts land in front; the ones behind fall back in scale and peek
 * out by a few pixels, so three notifications take the space of one and the newest is always
 * the readable one. Hovering (or focusing into) the stack fans it out to full height, which is
 * how the user reads the ones behind without any of them being dismissed underneath them.
 *
 * Details that make it feel finished:
 * - Timers pause while the stack is expanded or a toast is being dragged. A notification must
 *   never expire while it is being read.
 * - Toasts can be flicked to the right to dismiss, following the pointer as they go.
 * - Errors last longer than confirmations and are not auto-dismissed at all when they carry an
 *   action, because a dismissed error is an error the user never handled.
 * - Exits are animated out of the DOM rather than unmounted, so a dismissal is never abrupt.
 */
import { CheckCircle2, Info, TriangleAlert, X, XCircle } from "lucide-react";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
  type PointerEvent as ReactPointerEvent,
  type ReactNode,
} from "react";

import { cn } from "../cn";

export type ToastTone = "info" | "success" | "warning" | "danger";
export type ToastInput = {
  title: ReactNode;
  description?: ReactNode;
  tone?: ToastTone;
  duration?: number;
  action?: { label: string; onClick: () => void };
};
type ToastRecord = ToastInput & { id: number; leaving?: boolean };

/** How far a toast peeks out from behind the one in front of it, collapsed. */
const PEEK = 14;
/** Scale lost per position back in the stack. */
const SCALE_STEP = 0.05;
/** Beyond this many, toasts are held but not drawn — the stack stops being readable. */
const VISIBLE = 3;
/** Gap between toasts once the stack is expanded. */
const GAP = 12;
/** Drag distance, in px, past which a release dismisses. */
const SWIPE_THRESHOLD = 60;

const DEFAULT_DURATION: Record<ToastTone, number> = {
  info: 5000,
  success: 4000,
  warning: 7000,
  danger: 9000,
};

type ToastApi = { push: (toast: ToastInput) => number; dismiss: (id: number) => void };
const ToastContext = createContext<ToastApi | null>(null);

export function useToast() {
  const api = useContext(ToastContext);
  if (!api) throw new Error("useToast must be used inside <ToastProvider>");
  return useMemo(
    () => ({
      show: api.push,
      dismiss: api.dismiss,
      success: (title: ReactNode, description?: ReactNode) => api.push({ title, description, tone: "success" }),
      warning: (title: ReactNode, description?: ReactNode) => api.push({ title, description, tone: "warning" }),
      error: (title: ReactNode, description?: ReactNode) => api.push({ title, description, tone: "danger" }),
      info: (title: ReactNode, description?: ReactNode) => api.push({ title, description, tone: "info" }),
    }),
    [api],
  );
}

const icons = { info: Info, success: CheckCircle2, warning: TriangleAlert, danger: XCircle };
const toneClass: Record<ToastTone, string> = {
  info: "text-info",
  success: "text-success",
  warning: "text-warning",
  danger: "text-danger",
};

export function ToastProvider({ children, label = "Notifications" }: { children: ReactNode; label?: string }) {
  const [toasts, setToasts] = useState<ToastRecord[]>([]);
  const [pointerInside, setPointerInside] = useState(false);
  const [dragging, setDragging] = useState(false);
  const nextId = useRef(1);

  const remove = useCallback((id: number) => setToasts((current) => current.filter((t) => t.id !== id)), []);

  /** Mark leaving so the exit animation runs, then drop it once the animation is over. */
  const dismiss = useCallback(
    (id: number) => {
      setToasts((current) => current.map((t) => (t.id === id ? { ...t, leaving: true } : t)));
      setTimeout(() => remove(id), 200);
    },
    [remove],
  );

  const push = useCallback((toast: ToastInput) => {
    const id = nextId.current++;
    // Hold a few beyond what is drawn: dismissing the front one should reveal the next.
    setToasts((current) => [...current.slice(-(VISIBLE + 2)), { ...toast, id }]);
    return id;
  }, []);

  const api = useMemo(() => ({ push, dismiss }), [push, dismiss]);

  // Derived, not stored: an emptied stack cannot stay expanded, and there is no state to reset.
  const expanded = pointerInside && toasts.length > 0;

  return (
    <ToastContext.Provider value={api}>
      {children}
      <section
        aria-label={label}
        className="fixed bottom-4 right-4 z-[60] w-96 max-w-[calc(100vw-2rem)]"
        onMouseEnter={() => setPointerInside(true)}
        onMouseLeave={() => !dragging && setPointerInside(false)}
        onFocusCapture={() => setPointerInside(true)}
        onBlurCapture={(event) => {
          if (!event.currentTarget.contains(event.relatedTarget as Node)) setPointerInside(false);
        }}
      >
        {/* Live region: the text is announced whether or not the stack is looked at. */}
        <div aria-live="polite" aria-atomic="false" className="relative">
          <ToastStack toasts={toasts} expanded={expanded} onDismiss={dismiss} onDragChange={setDragging} paused={expanded || dragging} />
        </div>
      </section>
    </ToastContext.Provider>
  );
}

function ToastStack({
  toasts,
  expanded,
  onDismiss,
  onDragChange,
  paused,
}: {
  toasts: ToastRecord[];
  expanded: boolean;
  onDismiss: (id: number) => void;
  onDragChange: (dragging: boolean) => void;
  paused: boolean;
}) {
  const [heights, setHeights] = useState<Record<number, number>>({});
  // Newest first: index 0 is the toast in front.
  const ordered = useMemo(() => [...toasts].reverse(), [toasts]);

  const setHeight = useCallback((id: number, height: number) => {
    setHeights((current) => (current[id] === height ? current : { ...current, [id]: height }));
  }, []);

  /* The container has to reserve the height of whatever is currently drawn, or the page
     underneath receives pointer events where the stack visually is. */
  const stackHeight = expanded
    ? ordered.slice(0, VISIBLE).reduce((total, toast, index) => total + (heights[toast.id] ?? 64) + (index > 0 ? GAP : 0), 0)
    : (heights[ordered[0]?.id ?? -1] ?? 0) + Math.min(ordered.length - 1, VISIBLE - 1) * PEEK;

  return (
    <ol className="relative m-0 list-none p-0" style={{ height: ordered.length ? stackHeight : 0, transition: "height var(--mz-duration-slow) var(--mz-ease-spring)" }}>
      {ordered.map((toast, index) => (
        <ToastItem
          key={toast.id}
          toast={toast}
          index={index}
          expanded={expanded}
          paused={paused}
          offset={
            expanded
              ? ordered.slice(0, index).reduce((total, previous) => total + (heights[previous.id] ?? 64) + GAP, 0)
              : index * PEEK
          }
          onHeight={setHeight}
          onDismiss={onDismiss}
          onDragChange={onDragChange}
        />
      ))}
    </ol>
  );
}

function ToastItem({
  toast,
  index,
  offset,
  expanded,
  paused,
  onHeight,
  onDismiss,
  onDragChange,
}: {
  toast: ToastRecord;
  index: number;
  offset: number;
  expanded: boolean;
  paused: boolean;
  onHeight: (id: number, height: number) => void;
  onDismiss: (id: number) => void;
  onDragChange: (dragging: boolean) => void;
}) {
  const node = useRef<HTMLLIElement>(null);
  const [swipe, setSwipe] = useState(0);
  const [swiping, setSwiping] = useState(false);
  const dragStart = useRef<number | null>(null);
  const Icon = icons[toast.tone ?? "info"];

  // Measure once mounted, and again if the content reflows: the stack maths needs real heights.
  useLayoutEffect(() => {
    const element = node.current;
    if (!element) return;
    const report = () => onHeight(toast.id, element.getBoundingClientRect().height);
    report();
    const observer = new ResizeObserver(report);
    observer.observe(element);
    return () => observer.disconnect();
  }, [toast.id, onHeight]);

  /* Auto-dismiss. An error carrying an action never expires on its own — the action is the
     whole point of showing it. Hovering the stack pauses every timer in it. */
  const autoDismiss = toast.duration ?? (toast.tone === "danger" && toast.action ? 0 : DEFAULT_DURATION[toast.tone ?? "info"]);
  useEffect(() => {
    if (autoDismiss === 0 || paused || toast.leaving) return;
    const timer = setTimeout(() => onDismiss(toast.id), autoDismiss);
    return () => clearTimeout(timer);
  }, [autoDismiss, paused, toast.id, toast.leaving, onDismiss]);

  const onPointerDown = (event: ReactPointerEvent<HTMLLIElement>) => {
    if (event.button !== 0 || (event.target as HTMLElement).closest("button,a")) return;
    dragStart.current = event.clientX;
    setSwiping(true);
    onDragChange(true);
    event.currentTarget.setPointerCapture(event.pointerId);
  };
  const onPointerMove = (event: ReactPointerEvent<HTMLLIElement>) => {
    if (dragStart.current === null) return;
    const delta = event.clientX - dragStart.current;
    // Rightwards dismisses; leftwards is resisted so the gesture has a direction.
    setSwipe(delta > 0 ? delta : delta / 5);
  };
  const endDrag = () => {
    if (dragStart.current === null) return;
    dragStart.current = null;
    setSwiping(false);
    onDragChange(false);
    if (swipe > SWIPE_THRESHOLD) onDismiss(toast.id);
    setSwipe(0);
  };

  const behind = index >= 1;
  const hidden = index >= VISIBLE;

  return (
    <li
      ref={node}
      role="status"
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={endDrag}
      onPointerCancel={endDrag}
      data-leaving={toast.leaving || undefined}
      className={cn(
        "absolute bottom-0 right-0 flex w-full list-none items-start gap-3 rounded-card border border-line bg-surface p-3 shadow-3",
        "touch-none select-none",
        toast.tone === "danger" && "border-danger/40",
        toast.tone === "warning" && "border-warning/40",
      )}
      style={{
        // Only transform and opacity animate; the stack never reflows as toasts arrive.
        transform: `translate3d(${swipe}px, ${-offset}px, 0) scale(${expanded ? 1 : 1 - index * SCALE_STEP})`,
        transformOrigin: "bottom center",
        opacity: hidden ? 0 : toast.leaving ? 0 : 1,
        zIndex: 100 - index,
        pointerEvents: hidden ? "none" : undefined,
        transition: swiping ? "none" : "transform var(--mz-duration-slow) var(--mz-ease-spring), opacity var(--mz-duration-base) var(--mz-ease-out)",
        // Collapsed, only the front toast is readable; the ones behind are a hint of depth.
        ...(behind && !expanded ? { filter: "saturate(0.7)" } : null),
      }}
    >
      <Icon className={cn("mt-0.5 size-5 shrink-0", toneClass[toast.tone ?? "info"])} aria-hidden />
      <div className="min-w-0 flex-1">
        <p className="text-base font-medium">{toast.title}</p>
        {toast.description && <p className="mt-0.5 text-sm text-muted">{toast.description}</p>}
        {toast.action && (
          <button
            type="button"
            className="mt-1.5 rounded-xs text-sm font-medium text-primary hover-colors hover:underline"
            onClick={() => {
              toast.action?.onClick();
              onDismiss(toast.id);
            }}
          >
            {toast.action.label}
          </button>
        )}
      </div>
      <button
        type="button"
        aria-label="Close"
        onClick={() => onDismiss(toast.id)}
        className="rounded-xs p-0.5 text-muted hover-colors hover:bg-subtle hover:text-text"
      >
        <X className="size-4" aria-hidden />
      </button>
    </li>
  );
}
