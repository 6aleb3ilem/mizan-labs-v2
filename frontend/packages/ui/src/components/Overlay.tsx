/**
 * Overlay surfaces (SPEC §21.3, §21.6): dialog, drawer, tooltip, menu.
 *
 * Every one of them covers content the user was reading, so each has to say clearly where it
 * came from and get out of the way quickly:
 *
 * - The backdrop fades and blurs by 2 px, which separates the layers without hiding context.
 * - The dialog rises 8 px and settles on the spring curve; it leaves straight down, faster.
 * - Menus and tooltips grow from their trigger, using the origin Radix reports.
 * - Drawers can be dragged shut, and follow the finger while they are.
 */
import { X } from "lucide-react";
import { Dialog as RadixDialog, DropdownMenu as RadixDropdown, Tooltip as RadixTooltip } from "radix-ui";
import { useCallback, useRef, useState, type PointerEvent as ReactPointerEvent, type ReactNode } from "react";

import { cn } from "../cn";
import { Button } from "./Button";

export type DialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: ReactNode;
  description?: ReactNode;
  children?: ReactNode;
  footer?: ReactNode;
  size?: "sm" | "md" | "lg" | "xl";
  closeLabel?: string;
};

const sizes = { sm: "max-w-sm", md: "max-w-lg", lg: "max-w-2xl", xl: "max-w-4xl" };

export function Dialog({ open, onOpenChange, title, description, children, footer, size = "md", closeLabel = "Close" }: DialogProps) {
  return (
    <RadixDialog.Root open={open} onOpenChange={onOpenChange}>
      <RadixDialog.Portal>
        <RadixDialog.Overlay className="mz-overlay fixed inset-0 z-40" />
        <RadixDialog.Content
          className={cn(
            "mz-dialog fixed left-1/2 top-1/2 z-50 flex max-h-[90vh] w-[calc(100%-2rem)] -translate-x-1/2 -translate-y-1/2",
            "flex-col rounded-dialog border border-line bg-surface shadow-3 focus:outline-none",
            sizes[size],
          )}
        >
          <header className="flex items-start justify-between gap-4 border-b border-line px-5 py-4">
            <div>
              <RadixDialog.Title className="text-md font-semibold">{title}</RadixDialog.Title>
              {description ? (
                <RadixDialog.Description className="mt-1 text-sm text-muted">{description}</RadixDialog.Description>
              ) : (
                <RadixDialog.Description className="sr-only">{title}</RadixDialog.Description>
              )}
            </div>
            <RadixDialog.Close asChild>
              <Button variant="ghost" size="icon-sm" aria-label={closeLabel}>
                <X className="size-4" aria-hidden />
              </Button>
            </RadixDialog.Close>
          </header>
          <div className="flex-1 overflow-y-auto px-5 py-4">{children}</div>
          {footer && <footer className="flex flex-wrap items-center justify-end gap-2 border-t border-line px-5 py-3">{footer}</footer>}
        </RadixDialog.Content>
      </RadixDialog.Portal>
    </RadixDialog.Root>
  );
}

export type ConfirmDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: ReactNode;
  /** State the consequences ("3 scheduled runs will be cancelled"). */
  consequences?: ReactNode;
  confirmLabel: string;
  cancelLabel: string;
  destructive?: boolean;
  loading?: boolean;
  onConfirm: () => void;
  children?: ReactNode;
};

export function ConfirmDialog({ open, onOpenChange, title, consequences, confirmLabel, cancelLabel, destructive, loading, onConfirm, children }: ConfirmDialogProps) {
  return (
    <Dialog
      open={open}
      onOpenChange={onOpenChange}
      title={title}
      description={consequences}
      size="sm"
      footer={
        <>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={loading}>
            {cancelLabel}
          </Button>
          <Button variant={destructive ? "danger" : "primary"} onClick={onConfirm} loading={loading}>
            {confirmLabel}
          </Button>
        </>
      }
    >
      {children}
    </Dialog>
  );
}

/** Below this share of the panel's own size, a release springs back instead of dismissing. */
const DISMISS_DISTANCE = 0.35;
/** A fast flick dismisses regardless of distance, in px/ms. */
const DISMISS_VELOCITY = 0.5;

type Axis = "x" | "y";

/**
 * Drag-to-dismiss for an edge panel.
 *
 * While the pointer is down the panel is positioned directly from the drag delta — no
 * animation, no transition, because anything interpolating here would lag behind the finger.
 * Dragging away from the closing direction is resisted rather than blocked: the panel still
 * moves, by a shrinking fraction, so it reads as elastic rather than stuck.
 *
 * On release the decision uses both distance and velocity. Distance alone punishes a quick
 * flick, which is how people actually dismiss things on a touchscreen.
 */
function useDragDismiss(axis: Axis, sign: 1 | -1, enabled: boolean, onDismiss: () => void) {
  const panel = useRef<HTMLDivElement>(null);
  const [dragging, setDragging] = useState(false);
  const [settling, setSettling] = useState(false);
  const start = useRef({ position: 0, time: 0 });
  const last = useRef({ position: 0, time: 0 });

  const positionOf = useCallback((event: { clientX: number; clientY: number }) => (axis === "x" ? event.clientX : event.clientY), [axis]);

  const onPointerDown = useCallback(
    (event: ReactPointerEvent<HTMLElement>) => {
      // Let controls inside the header keep their own clicks.
      if (!enabled || event.button !== 0 || (event.target as HTMLElement).closest("button,a,input,select,textarea")) return;
      const position = positionOf(event);
      start.current = { position, time: event.timeStamp };
      last.current = { position, time: event.timeStamp };
      setSettling(false);
      setDragging(true);
      event.currentTarget.setPointerCapture(event.pointerId);
    },
    [enabled, positionOf],
  );

  const onPointerMove = useCallback(
    (event: ReactPointerEvent<HTMLElement>) => {
      if (!dragging || !panel.current) return;
      const position = positionOf(event);
      last.current = { position, time: event.timeStamp };
      const delta = (position - start.current.position) * sign;
      // Past the open position: resistance, not a wall.
      const travel = delta >= 0 ? delta : delta / 4;
      panel.current.style.transform = axis === "x" ? `translate3d(${travel * sign}px, 0, 0)` : `translate3d(0, ${travel * sign}px, 0)`;
    },
    [dragging, axis, sign, positionOf],
  );

  const onPointerUp = useCallback(
    (event: ReactPointerEvent<HTMLElement>) => {
      if (!dragging || !panel.current) return;
      setDragging(false);
      const node = panel.current;
      const delta = (positionOf(event) - start.current.position) * sign;
      const elapsed = Math.max(1, event.timeStamp - last.current.time);
      const velocity = ((positionOf(event) - last.current.position) * sign) / elapsed;
      const extent = axis === "x" ? node.offsetWidth : node.offsetHeight;

      if (delta > extent * DISMISS_DISTANCE || velocity > DISMISS_VELOCITY) {
        onDismiss();
        // Leave the transform in place; the close animation takes over from where the finger was.
        return;
      }
      setSettling(true);
      node.style.transform = "";
      const done = () => {
        setSettling(false);
        node.removeEventListener("transitionend", done);
      };
      node.addEventListener("transitionend", done);
    },
    [dragging, axis, sign, positionOf, onDismiss],
  );

  return [
    panel,
    enabled ? { onPointerDown, onPointerMove, onPointerUp, onPointerCancel: onPointerUp } : {},
    { "data-dragging": dragging || undefined, "data-settling": settling || undefined },
  ] as const;
}

export type DrawerProps = Omit<DialogProps, "size"> & {
  side?: "right" | "left" | "bottom";
  width?: string;
  /**
   * Drag the header (or the grab handle on a bottom sheet) to dismiss. On by default for bottom
   * sheets, where it is the expected gesture; off for side drawers holding a form, where a
   * stray drag would lose work.
   */
  draggable?: boolean;
};

export function Drawer({
  open,
  onOpenChange,
  title,
  description,
  children,
  footer,
  side = "right",
  width = "max-w-xl",
  closeLabel = "Close",
  draggable,
}: DrawerProps) {
  const canDrag = draggable ?? side === "bottom";
  const axis: Axis = side === "bottom" ? "y" : "x";
  const sign: 1 | -1 = side === "left" ? -1 : 1;
  const [panelRef, dragHandlers, dragState] = useDragDismiss(axis, sign, canDrag, () => onOpenChange(false));

  const position =
    side === "bottom"
      ? "inset-x-0 bottom-0 max-h-[85vh] w-full rounded-t-dialog"
      : side === "left"
        ? `inset-y-0 left-0 h-full w-full ${width}`
        : `inset-y-0 right-0 h-full w-full ${width}`;

  return (
    <RadixDialog.Root open={open} onOpenChange={onOpenChange}>
      <RadixDialog.Portal>
        <RadixDialog.Overlay className="mz-overlay fixed inset-0 z-40" />
        <RadixDialog.Content
          ref={panelRef}
          data-side={side}
          {...dragState}
          className={cn("mz-panel fixed z-50 flex flex-col border-line bg-surface shadow-3 focus:outline-none", position)}
        >
          <header
            className={cn(
              "flex items-start justify-between gap-4 border-b border-line px-5 py-4",
              canDrag && "cursor-grab touch-none active:cursor-grabbing",
            )}
            {...dragHandlers}
          >
            <div className="min-w-0">
              {/* The grab handle is the affordance: without it nobody discovers the gesture. */}
              {canDrag && side === "bottom" && <div aria-hidden className="mx-auto mb-3 h-1 w-10 rounded-full bg-line" />}
              <RadixDialog.Title className="text-md font-semibold">{title}</RadixDialog.Title>
              {description ? (
                <RadixDialog.Description className="mt-1 text-sm text-muted">{description}</RadixDialog.Description>
              ) : (
                <RadixDialog.Description className="sr-only">{title}</RadixDialog.Description>
              )}
            </div>
            <RadixDialog.Close asChild>
              <Button variant="ghost" size="icon-sm" aria-label={closeLabel}>
                <X className="size-4" aria-hidden />
              </Button>
            </RadixDialog.Close>
          </header>
          <div className="flex-1 overflow-y-auto px-5 py-4">{children}</div>
          {footer && <footer className="flex flex-wrap items-center justify-end gap-2 border-t border-line px-5 py-3">{footer}</footer>}
        </RadixDialog.Content>
      </RadixDialog.Portal>
    </RadixDialog.Root>
  );
}

/**
 * Tooltips.
 *
 * The 300 ms open delay stops a row of icon buttons firing tooltips as the pointer crosses it;
 * `skipDelayDuration` then lets the next one open instantly, because once the user is reading
 * tooltips they want the next one now.
 */
export function Tooltip({
  content,
  children,
  side = "top",
  shortcut,
}: {
  content: ReactNode;
  children: ReactNode;
  side?: "top" | "bottom" | "left" | "right";
  /** Rendered as a key hint after the label — cheap keyboard discoverability. */
  shortcut?: ReactNode;
}) {
  return (
    <RadixTooltip.Provider delayDuration={300} skipDelayDuration={200}>
      <RadixTooltip.Root>
        <RadixTooltip.Trigger asChild>{children}</RadixTooltip.Trigger>
        <RadixTooltip.Portal>
          <RadixTooltip.Content
            side={side}
            sideOffset={6}
            className="mz-pop z-50 flex items-center gap-2 rounded-control bg-text px-2 py-1 text-xs text-inverse shadow-2"
          >
            {content}
            {shortcut && <span className="opacity-60">{shortcut}</span>}
          </RadixTooltip.Content>
        </RadixTooltip.Portal>
      </RadixTooltip.Root>
    </RadixTooltip.Provider>
  );
}

export type MenuItem = {
  key: string;
  label: ReactNode;
  icon?: ReactNode;
  onSelect?: () => void;
  disabled?: boolean;
  destructive?: boolean;
  separator?: boolean;
  shortcut?: ReactNode;
};

export function DropdownMenu({ trigger, items, align = "end" }: { trigger: ReactNode; items: MenuItem[]; align?: "start" | "end" }) {
  return (
    <RadixDropdown.Root>
      <RadixDropdown.Trigger asChild>{trigger}</RadixDropdown.Trigger>
      <RadixDropdown.Portal>
        <RadixDropdown.Content
          align={align}
          sideOffset={6}
          collisionPadding={8}
          className="mz-pop z-50 min-w-48 rounded-card border border-line bg-surface p-1 shadow-3"
        >
          {items.map((item) =>
            item.separator ? (
              <RadixDropdown.Separator key={item.key} className="my-1 h-px bg-line" />
            ) : (
              <RadixDropdown.Item
                key={item.key}
                disabled={item.disabled}
                onSelect={item.onSelect}
                className={cn(
                  "flex cursor-default select-none items-center gap-2 rounded-xs px-2 py-1.5 text-base outline-none",
                  "transition-colors duration-[var(--mz-duration-instant)]",
                  "data-[highlighted]:bg-subtle data-[disabled]:opacity-50",
                  item.destructive && "text-danger data-[highlighted]:bg-danger/10",
                )}
              >
                {item.icon}
                <span className="flex-1">{item.label}</span>
                {item.shortcut && <span className="text-xs text-muted">{item.shortcut}</span>}
              </RadixDropdown.Item>
            ),
          )}
        </RadixDropdown.Content>
      </RadixDropdown.Portal>
    </RadixDropdown.Root>
  );
}
