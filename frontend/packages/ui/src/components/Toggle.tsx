import { Check } from "lucide-react";
import { Checkbox as RadixCheckbox, RadioGroup as RadixRadio, Switch as RadixSwitch } from "radix-ui";
import type { ReactNode } from "react";

import { cn } from "../cn";

export type CheckboxProps = {
  checked: boolean | "indeterminate";
  onCheckedChange: (checked: boolean) => void;
  label?: ReactNode;
  disabled?: boolean;
  id?: string;
  className?: string;
  "aria-label"?: string;
};

export function Checkbox({ checked, onCheckedChange, label, disabled, id, className, ...aria }: CheckboxProps) {
  const box = (
    <RadixCheckbox.Root
      id={id}
      checked={checked}
      onCheckedChange={(v) => onCheckedChange(v === true)}
      disabled={disabled}
      aria-label={aria["aria-label"]}
      className={cn("flex size-4 shrink-0 items-center justify-center rounded-[4px] border border-line bg-surface data-[state=checked]:border-primary data-[state=checked]:bg-primary data-[state=checked]:text-primary-on data-[state=indeterminate]:bg-primary disabled:opacity-50", className)}
    >
      <RadixCheckbox.Indicator>
        {checked === "indeterminate" ? <span className="block h-0.5 w-2 bg-primary-on" /> : <Check className="size-3" aria-hidden />}
      </RadixCheckbox.Indicator>
    </RadixCheckbox.Root>
  );
  if (!label) return box;
  return (
    <label className="inline-flex cursor-pointer items-center gap-2 text-base">
      {box}
      <span>{label}</span>
    </label>
  );
}

export type SwitchProps = { checked: boolean; onCheckedChange: (checked: boolean) => void; label?: ReactNode; disabled?: boolean; id?: string; "aria-label"?: string };

export function Switch({ checked, onCheckedChange, label, disabled, id, ...aria }: SwitchProps) {
  const control = (
    <RadixSwitch.Root
      id={id}
      checked={checked}
      onCheckedChange={onCheckedChange}
      disabled={disabled}
      aria-label={aria["aria-label"]}
      className="relative h-5 w-9 shrink-0 rounded-full bg-line transition-colors data-[state=checked]:bg-primary disabled:opacity-50"
    >
      <RadixSwitch.Thumb className="block size-4 translate-x-0.5 rounded-full bg-white shadow-1 transition-transform data-[state=checked]:translate-x-[18px]" />
    </RadixSwitch.Root>
  );
  if (!label) return control;
  return (
    <label className="inline-flex cursor-pointer items-center gap-2 text-base">
      {control}
      <span>{label}</span>
    </label>
  );
}

export type RadioOption = { value: string; label: ReactNode; description?: ReactNode; disabled?: boolean };

export function RadioGroup({ value, onValueChange, options, name, className }: { value: string; onValueChange: (v: string) => void; options: RadioOption[]; name?: string; className?: string }) {
  return (
    <RadixRadio.Root value={value} onValueChange={onValueChange} name={name} className={cn("flex flex-col gap-2", className)}>
      {options.map((option) => (
        <label key={option.value} className="flex cursor-pointer items-start gap-2 text-base">
          <RadixRadio.Item value={option.value} disabled={option.disabled} className="mt-0.5 flex size-4 shrink-0 items-center justify-center rounded-full border border-line bg-surface data-[state=checked]:border-primary disabled:opacity-50">
            <RadixRadio.Indicator className="size-2 rounded-full bg-primary" />
          </RadixRadio.Item>
          <span>
            <span className="block">{option.label}</span>
            {option.description && <span className="block text-xs text-muted">{option.description}</span>}
          </span>
        </label>
      ))}
    </RadixRadio.Root>
  );
}
