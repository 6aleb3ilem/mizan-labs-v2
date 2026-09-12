import { Check, ChevronDown } from "lucide-react";
import { Select as RadixSelect } from "radix-ui";
import type { ReactNode } from "react";

import { cn } from "../cn";

export type SelectOption = { value: string; label: ReactNode; disabled?: boolean };

export type SelectProps = {
  value: string | null | undefined;
  onValueChange: (value: string) => void;
  options: SelectOption[];
  placeholder?: string;
  disabled?: boolean;
  invalid?: boolean;
  id?: string;
  "aria-describedby"?: string;
  className?: string;
  allowEmpty?: boolean;
  emptyLabel?: string;
};

const EMPTY = "__empty__";

export function Select({ value, onValueChange, options, placeholder, disabled, invalid, id, className, allowEmpty, emptyLabel, ...aria }: SelectProps) {
  return (
    <RadixSelect.Root value={value || (allowEmpty ? EMPTY : undefined)} onValueChange={(v) => onValueChange(v === EMPTY ? "" : v)} disabled={disabled}>
      <RadixSelect.Trigger
        id={id}
        aria-describedby={aria["aria-describedby"]}
        aria-invalid={invalid || undefined}
        className={cn(
          "flex h-9 w-full items-center justify-between gap-2 rounded-control border border-line bg-surface px-3 text-base text-text data-[placeholder]:text-muted disabled:opacity-70",
          invalid && "border-danger",
          className,
        )}
      >
        <RadixSelect.Value placeholder={placeholder ?? "—"} />
        <RadixSelect.Icon>
          <ChevronDown className="size-4 text-muted" aria-hidden />
        </RadixSelect.Icon>
      </RadixSelect.Trigger>
      <RadixSelect.Portal>
        <RadixSelect.Content position="popper" sideOffset={4} className="z-50 max-h-72 min-w-[var(--radix-select-trigger-width)] overflow-hidden rounded-card border border-line bg-surface shadow-3">
          <RadixSelect.Viewport className="p-1">
            {allowEmpty && (
              <RadixSelect.Item value={EMPTY} className="relative flex cursor-default select-none items-center rounded-control py-1.5 pl-7 pr-2 text-base text-muted outline-none data-[highlighted]:bg-subtle">
                <RadixSelect.ItemText>{emptyLabel ?? "—"}</RadixSelect.ItemText>
              </RadixSelect.Item>
            )}
            {options.map((option) => (
              <RadixSelect.Item
                key={option.value}
                value={option.value}
                disabled={option.disabled}
                className="relative flex cursor-default select-none items-center rounded-control py-1.5 pl-7 pr-2 text-base outline-none data-[highlighted]:bg-subtle data-[disabled]:opacity-50"
              >
                <RadixSelect.ItemIndicator className="absolute left-2">
                  <Check className="size-4" aria-hidden />
                </RadixSelect.ItemIndicator>
                <RadixSelect.ItemText>{option.label}</RadixSelect.ItemText>
              </RadixSelect.Item>
            ))}
          </RadixSelect.Viewport>
        </RadixSelect.Content>
      </RadixSelect.Portal>
    </RadixSelect.Root>
  );
}
