import { ChevronRight } from "lucide-react";
import { Tabs as RadixTabs } from "radix-ui";
import type { ReactNode } from "react";

import { cn } from "../cn";

export type Crumb = { label: ReactNode; href?: string; onClick?: () => void };

export function Breadcrumbs({ items, className, linkComponent: Link }: { items: Crumb[]; className?: string; linkComponent?: (props: { href: string; children: ReactNode; className?: string }) => ReactNode }) {
  return (
    <nav aria-label="Breadcrumb" className={cn("flex items-center gap-1 text-sm text-muted", className)}>
      {items.map((item, index) => {
        const last = index === items.length - 1;
        const content = last ? (
          <span aria-current="page" className="font-medium text-text">
            {item.label}
          </span>
        ) : item.href && Link ? (
          <Link href={item.href} className="hover:text-text">
            {item.label}
          </Link>
        ) : item.onClick ? (
          <button type="button" onClick={item.onClick} className="hover:text-text">
            {item.label}
          </button>
        ) : (
          <span>{item.label}</span>
        );
        return (
          <span key={index} className="flex items-center gap-1">
            {content}
            {!last && <ChevronRight className="size-3.5" aria-hidden />}
          </span>
        );
      })}
    </nav>
  );
}

export type TabItem = { value: string; label: ReactNode; badge?: ReactNode; disabled?: boolean };

export function Tabs({ value, onValueChange, items, children, className }: { value: string; onValueChange: (v: string) => void; items: TabItem[]; children?: ReactNode; className?: string }) {
  return (
    <RadixTabs.Root value={value} onValueChange={onValueChange} className={className}>
      <RadixTabs.List className="flex gap-1 overflow-x-auto border-b border-line" aria-label="Tabs">
        {items.map((item) => (
          <RadixTabs.Trigger
            key={item.value}
            value={item.value}
            disabled={item.disabled}
            className="-mb-px flex items-center gap-2 whitespace-nowrap border-b-2 border-transparent px-3 py-2 text-base text-muted hover:text-text data-[state=active]:border-primary data-[state=active]:text-text disabled:opacity-50"
          >
            {item.label}
            {item.badge !== undefined && <span className="rounded-full bg-subtle px-1.5 text-xs">{item.badge}</span>}
          </RadixTabs.Trigger>
        ))}
      </RadixTabs.List>
      {children}
    </RadixTabs.Root>
  );
}

export const TabPanel = RadixTabs.Content;

export type Step = { key: string; label: ReactNode; description?: ReactNode };

export function Stepper({ steps, current, onSelect, className }: { steps: Step[]; current: number; onSelect?: (index: number) => void; className?: string }) {
  return (
    <ol className={cn("flex flex-wrap gap-4", className)}>
      {steps.map((step, index) => {
        const state = index < current ? "done" : index === current ? "current" : "todo";
        return (
          <li key={step.key} className="flex items-center gap-2">
            <button
              type="button"
              disabled={!onSelect || index > current}
              onClick={() => onSelect?.(index)}
              aria-current={state === "current" ? "step" : undefined}
              className={cn(
                "flex size-7 items-center justify-center rounded-full border text-sm font-medium",
                state === "done" && "border-primary bg-primary text-primary-on",
                state === "current" && "border-primary text-primary",
                state === "todo" && "border-line text-muted",
              )}
            >
              {index + 1}
            </button>
            <span className={cn("text-base", state === "todo" ? "text-muted" : "text-text")}>{step.label}</span>
            {index < steps.length - 1 && <ChevronRight className="size-4 text-muted" aria-hidden />}
          </li>
        );
      })}
    </ol>
  );
}

export function PageHeader({ title, subtitle, badges, actions, breadcrumbs, className }: { title: ReactNode; subtitle?: ReactNode; badges?: ReactNode; actions?: ReactNode; breadcrumbs?: ReactNode; className?: string }) {
  return (
    <header className={cn("flex flex-col gap-2", className)}>
      {breadcrumbs}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="truncate text-xl font-semibold">{title}</h1>
            {badges}
          </div>
          {subtitle && <p className="text-sm text-muted">{subtitle}</p>}
        </div>
        {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
      </div>
    </header>
  );
}

export function Card({ title, actions, children, className, padded = true }: { title?: ReactNode; actions?: ReactNode; children: ReactNode; className?: string; padded?: boolean }) {
  return (
    <section className={cn("rounded-card border border-line bg-surface shadow-1", className)}>
      {(title || actions) && (
        <header className="flex items-center justify-between gap-2 border-b border-line px-4 py-3">
          <h2 className="text-base font-semibold">{title}</h2>
          {actions}
        </header>
      )}
      <div className={padded ? "p-4" : undefined}>{children}</div>
    </section>
  );
}

export function KpiCard({ label, value, hint, tone, onClick, className }: { label: ReactNode; value: ReactNode; hint?: ReactNode; tone?: "success" | "warning" | "danger" | "info"; onClick?: () => void; className?: string }) {
  const body = (
    <>
      <p className="text-xs font-medium uppercase tracking-wide text-muted">{label}</p>
      <p className={cn("tabular mt-1 text-2xl font-semibold", tone && `text-${tone}`)}>{value}</p>
      {hint && <p className="mt-1 text-xs text-muted">{hint}</p>}
    </>
  );
  if (onClick) {
    return (
      <button type="button" onClick={onClick} className={cn("rounded-card border border-line bg-surface p-4 text-left shadow-1 hover:bg-subtle", className)}>
        {body}
      </button>
    );
  }
  return <div className={cn("rounded-card border border-line bg-surface p-4 shadow-1", className)}>{body}</div>;
}

export type TimelineEntry = { key: string; at: ReactNode; title: ReactNode; detail?: ReactNode; tone?: "success" | "warning" | "danger" | "info" | "neutral" };

export function Timeline({ entries, className }: { entries: TimelineEntry[]; className?: string }) {
  return (
    <ol className={cn("relative flex flex-col gap-4 border-l border-line pl-4", className)}>
      {entries.map((entry) => (
        <li key={entry.key} className="relative">
          <span className={cn("absolute -left-[21px] top-1.5 size-2.5 rounded-full border-2 border-surface", entry.tone === "success" ? "bg-success" : entry.tone === "warning" ? "bg-warning" : entry.tone === "danger" ? "bg-danger" : entry.tone === "info" ? "bg-info" : "bg-muted")} aria-hidden />
          <p className="text-xs text-muted">{entry.at}</p>
          <p className="text-base font-medium">{entry.title}</p>
          {entry.detail && <div className="text-sm text-muted">{entry.detail}</div>}
        </li>
      ))}
    </ol>
  );
}
