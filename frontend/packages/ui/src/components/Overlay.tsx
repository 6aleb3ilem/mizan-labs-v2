import { X } from "lucide-react";
import { Dialog as RadixDialog, DropdownMenu as RadixDropdown, Tooltip as RadixTooltip } from "radix-ui";
import { type ReactNode } from "react";

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
        <RadixDialog.Overlay className="fixed inset-0 z-40 bg-black/40 data-[state=open]:animate-in" />
        <RadixDialog.Content
          className={cn("fixed left-1/2 top-1/2 z-50 flex max-h-[90vh] w-[calc(100%-2rem)] -translate-x-1/2 -translate-y-1/2 flex-col rounded-dialog border border-line bg-surface shadow-3 focus:outline-none", sizes[size])}
        >
          <header className="flex items-start justify-between gap-4 border-b border-line px-5 py-4">
            <div>
              <RadixDialog.Title className="text-md font-semibold">{title}</RadixDialog.Title>
              {description ? <RadixDialog.Description className="mt-1 text-sm text-muted">{description}</RadixDialog.Description> : <RadixDialog.Description className="sr-only">{title}</RadixDialog.Description>}
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

export type DrawerProps = Omit<DialogProps, "size"> & { side?: "right" | "left" | "bottom"; width?: string };

export function Drawer({ open, onOpenChange, title, description, children, footer, side = "right", width = "max-w-xl", closeLabel = "Close" }: DrawerProps) {
  const position =
    side === "bottom"
      ? "inset-x-0 bottom-0 max-h-[85vh] w-full rounded-t-dialog"
      : side === "left"
        ? `inset-y-0 left-0 h-full w-full ${width}`
        : `inset-y-0 right-0 h-full w-full ${width}`;
  return (
    <RadixDialog.Root open={open} onOpenChange={onOpenChange}>
      <RadixDialog.Portal>
        <RadixDialog.Overlay className="fixed inset-0 z-40 bg-black/40" />
        <RadixDialog.Content className={cn("fixed z-50 flex flex-col border-line bg-surface shadow-3 focus:outline-none", position)}>
          <header className="flex items-start justify-between gap-4 border-b border-line px-5 py-4">
            <div>
              <RadixDialog.Title className="text-md font-semibold">{title}</RadixDialog.Title>
              {description ? <RadixDialog.Description className="mt-1 text-sm text-muted">{description}</RadixDialog.Description> : <RadixDialog.Description className="sr-only">{title}</RadixDialog.Description>}
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

export function Tooltip({ content, children, side = "top" }: { content: ReactNode; children: ReactNode; side?: "top" | "bottom" | "left" | "right" }) {
  return (
    <RadixTooltip.Provider delayDuration={300}>
      <RadixTooltip.Root>
        <RadixTooltip.Trigger asChild>{children}</RadixTooltip.Trigger>
        <RadixTooltip.Portal>
          <RadixTooltip.Content side={side} sideOffset={4} className="z-50 rounded-control bg-text px-2 py-1 text-xs text-inverse shadow-2">
            {content}
          </RadixTooltip.Content>
        </RadixTooltip.Portal>
      </RadixTooltip.Root>
    </RadixTooltip.Provider>
  );
}

export type MenuItem = { key: string; label: ReactNode; icon?: ReactNode; onSelect?: () => void; disabled?: boolean; destructive?: boolean; separator?: boolean };

export function DropdownMenu({ trigger, items, align = "end" }: { trigger: ReactNode; items: MenuItem[]; align?: "start" | "end" }) {
  return (
    <RadixDropdown.Root>
      <RadixDropdown.Trigger asChild>{trigger}</RadixDropdown.Trigger>
      <RadixDropdown.Portal>
        <RadixDropdown.Content align={align} sideOffset={4} className="z-50 min-w-44 rounded-card border border-line bg-surface p-1 shadow-3">
          {items.map((item) =>
            item.separator ? (
              <RadixDropdown.Separator key={item.key} className="my-1 h-px bg-line" />
            ) : (
              <RadixDropdown.Item
                key={item.key}
                disabled={item.disabled}
                onSelect={item.onSelect}
                className={cn("flex cursor-default select-none items-center gap-2 rounded-control px-2 py-1.5 text-base outline-none data-[highlighted]:bg-subtle data-[disabled]:opacity-50", item.destructive && "text-danger")}
              >
                {item.icon}
                {item.label}
              </RadixDropdown.Item>
            ),
          )}
        </RadixDropdown.Content>
      </RadixDropdown.Portal>
    </RadixDropdown.Root>
  );
}
