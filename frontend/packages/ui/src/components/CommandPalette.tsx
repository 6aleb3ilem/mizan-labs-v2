import { Command } from "cmdk";
import { Search } from "lucide-react";
import { Dialog as RadixDialog } from "radix-ui";
import { useEffect, type ReactNode } from "react";

import { cn } from "../cn";

export type CommandItem = { id: string; group: string; label: string; hint?: string; icon?: ReactNode; keywords?: string[]; onSelect: () => void };

export type CommandPaletteProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  items: CommandItem[];
  placeholder?: string;
  emptyLabel?: string;
  title?: string;
  onSearchChange?: (value: string) => void;
  search?: string;
};

/** ⌘K / Ctrl+K palette for navigation and actions (SPEC §21.9). */
export function CommandPalette({ open, onOpenChange, items, placeholder = "Search…", emptyLabel = "No result", title = "Command palette", onSearchChange, search }: CommandPaletteProps) {
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        onOpenChange(!open);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onOpenChange]);

  const groups = new Map<string, CommandItem[]>();
  for (const item of items) groups.set(item.group, [...(groups.get(item.group) ?? []), item]);

  return (
    <RadixDialog.Root open={open} onOpenChange={onOpenChange}>
      <RadixDialog.Portal>
        <RadixDialog.Overlay className="fixed inset-0 z-40 bg-black/40" />
        <RadixDialog.Content className="fixed left-1/2 top-[15vh] z-50 w-[calc(100%-2rem)] max-w-xl -translate-x-1/2 overflow-hidden rounded-dialog border border-line bg-surface shadow-3">
          <RadixDialog.Title className="sr-only">{title}</RadixDialog.Title>
          <RadixDialog.Description className="sr-only">{placeholder}</RadixDialog.Description>
          <Command label={title} shouldFilter={!onSearchChange}>
            <div className="flex items-center gap-2 border-b border-line px-3">
              <Search className="size-4 text-muted" aria-hidden />
              <Command.Input value={search} onValueChange={onSearchChange} placeholder={placeholder} className="h-11 flex-1 bg-transparent text-base outline-none placeholder:text-muted" />
              <kbd className="rounded border border-line px-1.5 text-xs text-muted">Esc</kbd>
            </div>
            <Command.List className="max-h-80 overflow-y-auto p-2">
              <Command.Empty className="px-2 py-6 text-center text-sm text-muted">{emptyLabel}</Command.Empty>
              {Array.from(groups.entries()).map(([group, entries]) => (
                <Command.Group key={group} heading={group} className="[&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:py-1 [&_[cmdk-group-heading]]:text-xs [&_[cmdk-group-heading]]:font-semibold [&_[cmdk-group-heading]]:uppercase [&_[cmdk-group-heading]]:text-muted">
                  {entries.map((item) => (
                    <Command.Item
                      key={item.id}
                      value={`${item.label} ${item.keywords?.join(" ") ?? ""}`}
                      onSelect={() => {
                        onOpenChange(false);
                        item.onSelect();
                      }}
                      className={cn("flex cursor-default select-none items-center gap-2 rounded-control px-2 py-2 text-base data-[selected=true]:bg-subtle")}
                    >
                      {item.icon && <span className="text-muted">{item.icon}</span>}
                      <span className="flex-1">{item.label}</span>
                      {item.hint && <span className="text-xs text-muted">{item.hint}</span>}
                    </Command.Item>
                  ))}
                </Command.Group>
              ))}
            </Command.List>
          </Command>
        </RadixDialog.Content>
      </RadixDialog.Portal>
    </RadixDialog.Root>
  );
}
