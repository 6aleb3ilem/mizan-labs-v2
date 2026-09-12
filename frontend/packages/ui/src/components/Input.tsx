import { forwardRef, type InputHTMLAttributes, type ReactNode, type TextareaHTMLAttributes } from "react";

import { cn } from "../cn";

export const inputClass =
  "h-9 w-full rounded-control border border-line bg-surface px-3 text-base text-text placeholder:text-muted disabled:bg-subtle disabled:opacity-70 aria-invalid:border-danger";

export type InputProps = InputHTMLAttributes<HTMLInputElement> & { invalid?: boolean; suffix?: ReactNode; prefix?: ReactNode };

export const Input = forwardRef<HTMLInputElement, InputProps>(function Input({ className, invalid, suffix, prefix, ...props }, ref) {
  if (!suffix && !prefix) {
    return <input ref={ref} className={cn(inputClass, className)} aria-invalid={invalid || undefined} {...props} />;
  }
  return (
    <div className={cn("flex h-9 items-stretch rounded-control border border-line bg-surface focus-within:outline-2 focus-within:outline-offset-2", invalid && "border-danger", className)}>
      {prefix && <span className="flex items-center border-r border-line px-2 text-sm text-muted">{prefix}</span>}
      <input
        ref={ref}
        className="min-w-0 flex-1 bg-transparent px-3 text-base text-text outline-none placeholder:text-muted disabled:opacity-70"
        aria-invalid={invalid || undefined}
        {...props}
      />
      {suffix && <span className="flex items-center border-l border-line px-2 text-sm text-muted">{suffix}</span>}
    </div>
  );
});

export type NumberInputProps = Omit<InputProps, "type" | "value" | "onChange"> & {
  value: number | string | null | undefined;
  onValueChange: (value: string) => void;
  unit?: string;
  decimals?: number;
};

/** Numeric input with a unit suffix and the numeric keypad on tablets (SPEC §21.4, §21.9). */
export const NumberInput = forwardRef<HTMLInputElement, NumberInputProps>(function NumberInput(
  { value, onValueChange, unit, decimals = 2, ...props },
  ref,
) {
  return (
    <Input
      ref={ref}
      type="text"
      inputMode={decimals > 0 ? "decimal" : "numeric"}
      value={value ?? ""}
      onChange={(e) => onValueChange(e.target.value.replace(",", "."))}
      suffix={unit}
      className="tabular"
      {...props}
    />
  );
});

export type MoneyInputProps = Omit<NumberInputProps, "unit"> & { currency: string };

export const MoneyInput = forwardRef<HTMLInputElement, MoneyInputProps>(function MoneyInput({ currency, ...props }, ref) {
  return <NumberInput ref={ref} unit={currency} decimals={2} {...props} />;
});

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaHTMLAttributes<HTMLTextAreaElement> & { invalid?: boolean }>(
  function Textarea({ className, invalid, ...props }, ref) {
    return (
      <textarea
        ref={ref}
        className={cn("min-h-24 w-full rounded-control border border-line bg-surface px-3 py-2 text-base text-text placeholder:text-muted disabled:bg-subtle", invalid && "border-danger", className)}
        aria-invalid={invalid || undefined}
        {...props}
      />
    );
  },
);
