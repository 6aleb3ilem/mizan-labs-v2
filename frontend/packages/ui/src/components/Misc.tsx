import { Search, X } from "lucide-react";
import { forwardRef, type ReactNode } from "react";

import { cn } from "../cn";
import { Input, type InputProps } from "./Input";

export type Labels = { fr?: string | null; en?: string | null };

/** FR/EN label pair: every configurable entity carries both languages (SPEC §8). */
export function LabelsInput({ value, onChange, invalid, disabled, id, placeholderFr = "Français", placeholderEn = "English" }: { value: Labels; onChange: (labels: Labels) => void; invalid?: boolean; disabled?: boolean; id?: string; placeholderFr?: string; placeholderEn?: string }) {
  return (
    <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
      <Input id={id} prefix="FR" value={value.fr ?? ""} onChange={(e) => onChange({ ...value, fr: e.target.value })} placeholder={placeholderFr} invalid={invalid} disabled={disabled} aria-label="Français" />
      <Input prefix="EN" value={value.en ?? ""} onChange={(e) => onChange({ ...value, en: e.target.value })} placeholder={placeholderEn} disabled={disabled} aria-label="English" />
    </div>
  );
}

export const SearchInput = forwardRef<HTMLInputElement, InputProps & { onClear?: () => void }>(function SearchInput({ className, onClear, value, ...props }, ref) {
  return (
    <div className={cn("relative", className)}>
      <Search className="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted" aria-hidden />
      <Input ref={ref} type="search" value={value} className="pl-8 pr-8" {...props} />
      {onClear && value && (
        <button type="button" onClick={onClear} aria-label="Clear" className="absolute right-2 top-1/2 -translate-y-1/2 text-muted hover:text-text">
          <X className="size-4" aria-hidden />
        </button>
      )}
    </div>
  );
});

export type MatrixCell<R, C> = (row: R, column: C) => ReactNode;

/** A resources × actions grid (permission matrix, SPEC §23); cells render scope chips or checkboxes. */
export function MatrixGrid<R, C>({ rows, columns, rowLabel, columnLabel, cell, rowKey, columnKey, stickyFirst = true, className }: { rows: R[]; columns: C[]; rowLabel: (row: R) => ReactNode; columnLabel: (column: C) => ReactNode; cell: MatrixCell<R, C>; rowKey: (row: R) => string; columnKey: (column: C) => string; stickyFirst?: boolean; className?: string }) {
  return (
    <div className={cn("overflow-auto rounded-card border border-line bg-surface", className)}>
      <table className="w-full border-collapse text-sm">
        <thead className="bg-subtle text-xs font-semibold uppercase tracking-wide text-muted">
          <tr>
            <th scope="col" className={cn("border-b border-line px-3 py-2 text-left", stickyFirst && "sticky left-0 z-10 bg-subtle")}>
              &nbsp;
            </th>
            {columns.map((column) => (
              <th key={columnKey(column)} scope="col" className="whitespace-nowrap border-b border-line px-2 py-2 text-center">
                {columnLabel(column)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={rowKey(row)} className="border-b border-line last:border-b-0 hover:bg-subtle/60">
              <th scope="row" className={cn("whitespace-nowrap px-3 py-1.5 text-left font-medium", stickyFirst && "sticky left-0 z-10 bg-surface")}>
                {rowLabel(row)}
              </th>
              {columns.map((column) => (
                <td key={columnKey(column)} className="px-2 py-1.5 text-center align-middle">
                  {cell(row, column)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function DescriptionList({ items, className, columns = 2 }: { items: { label: ReactNode; value: ReactNode }[]; className?: string; columns?: 1 | 2 | 3 }) {
  return (
    <dl className={cn("grid gap-x-6 gap-y-3", columns === 1 ? "grid-cols-1" : columns === 2 ? "grid-cols-1 sm:grid-cols-2" : "grid-cols-1 sm:grid-cols-3", className)}>
      {items.map((item, index) => (
        <div key={index} className="min-w-0">
          <dt className="text-xs font-medium uppercase tracking-wide text-muted">{item.label}</dt>
          <dd className="truncate text-base">{item.value ?? "—"}</dd>
        </div>
      ))}
    </dl>
  );
}

export function Kbd({ children }: { children: ReactNode }) {
  return <kbd className="rounded border border-line bg-subtle px-1.5 py-0.5 font-sans text-xs text-muted">{children}</kbd>;
}
