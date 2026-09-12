import { useId, type ReactElement, type ReactNode, cloneElement, isValidElement } from "react";

import { cn } from "../cn";

export type FormFieldProps = {
  label: ReactNode;
  help?: ReactNode;
  error?: ReactNode;
  required?: boolean;
  optionalLabel?: string;
  className?: string;
  children: ReactElement<{ id?: string; "aria-describedby"?: string; "aria-invalid"?: boolean; invalid?: boolean }>;
};

/** Labelled control with help text and an announced error (SPEC §21.7). */
export function FormField({ label, help, error, required, optionalLabel, className, children }: FormFieldProps) {
  const id = useId();
  const helpId = `${id}-help`;
  const errorId = `${id}-error`;
  const described = [help ? helpId : null, error ? errorId : null].filter(Boolean).join(" ") || undefined;
  const control = isValidElement(children)
    ? cloneElement(children, { id, "aria-describedby": described, ...(error ? { invalid: true } : {}) })
    : children;
  return (
    <div className={cn("flex flex-col gap-1.5", className)}>
      <label htmlFor={id} className="text-sm font-medium text-text">
        {label}
        {required && <span className="ml-0.5 text-danger" aria-hidden>*</span>}
        {!required && optionalLabel && <span className="ml-1 text-xs font-normal text-muted">({optionalLabel})</span>}
      </label>
      {control}
      {help && !error && (
        <p id={helpId} className="text-xs text-muted">
          {help}
        </p>
      )}
      {error && (
        <p id={errorId} role="alert" className="text-xs text-danger">
          {error}
        </p>
      )}
    </div>
  );
}

export function FormSection({ title, description, children, className }: { title: ReactNode; description?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <section className={cn("flex flex-col gap-4", className)}>
      <header>
        <h3 className="text-md font-semibold">{title}</h3>
        {description && <p className="text-sm text-muted">{description}</p>}
      </header>
      {children}
    </section>
  );
}

export function FormActions({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cn("sticky bottom-0 -mx-4 flex flex-wrap items-center justify-end gap-2 border-t border-line bg-surface/95 px-4 py-3 backdrop-blur", className)}>{children}</div>;
}
