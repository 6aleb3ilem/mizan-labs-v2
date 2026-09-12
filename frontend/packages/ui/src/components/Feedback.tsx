import { AlertTriangle, Inbox, Loader2, RefreshCw, SearchX } from "lucide-react";
import type { ReactNode } from "react";

import { cn } from "../cn";
import { Button } from "./Button";

export function Spinner({ className, label = "Loading" }: { className?: string; label?: string }) {
  return <Loader2 className={cn("size-5 animate-spin text-muted", className)} role="status" aria-label={label} />;
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn("animate-pulse rounded-control bg-subtle", className)} aria-hidden />;
}

export function SkeletonRows({ rows = 5, className }: { rows?: number; className?: string }) {
  return (
    <div className={cn("flex flex-col gap-2", className)} aria-busy>
      {Array.from({ length: rows }, (_, i) => (
        <Skeleton key={i} className="h-9 w-full" />
      ))}
    </div>
  );
}

export type EmptyStateProps = { title: ReactNode; hint?: ReactNode; action?: ReactNode; icon?: ReactNode; className?: string; kind?: "empty" | "search" };

/** Empty states always offer the next action (SPEC §21.9, zero dead ends). */
export function EmptyState({ title, hint, action, icon, className, kind = "empty" }: EmptyStateProps) {
  return (
    <div className={cn("flex flex-col items-center justify-center gap-2 rounded-card border border-dashed border-line px-6 py-12 text-center", className)}>
      <span className="text-muted">{icon ?? (kind === "search" ? <SearchX className="size-8" aria-hidden /> : <Inbox className="size-8" aria-hidden />)}</span>
      <p className="text-md font-medium">{title}</p>
      {hint && <p className="max-w-md text-sm text-muted">{hint}</p>}
      {action && <div className="mt-2">{action}</div>}
    </div>
  );
}

export type ErrorStateProps = { title: ReactNode; detail?: ReactNode; onRetry?: () => void; retryLabel?: string; className?: string };

export function ErrorState({ title, detail, onRetry, retryLabel = "Retry", className }: ErrorStateProps) {
  return (
    <div role="alert" className={cn("flex flex-col items-center justify-center gap-2 rounded-card border border-danger/40 bg-surface px-6 py-10 text-center", className)}>
      <AlertTriangle className="size-8 text-danger" aria-hidden />
      <p className="text-md font-medium">{title}</p>
      {detail && <p className="max-w-md text-sm text-muted">{detail}</p>}
      {onRetry && (
        <Button variant="outline" size="sm" onClick={onRetry} leftIcon={<RefreshCw className="size-4" aria-hidden />}>
          {retryLabel}
        </Button>
      )}
    </div>
  );
}

export function Alert({ tone = "info", title, children, className }: { tone?: "info" | "success" | "warning" | "danger"; title?: ReactNode; children?: ReactNode; className?: string }) {
  const colours = { info: "border-info/40 text-info", success: "border-success/40 text-success", warning: "border-warning/40 text-warning", danger: "border-danger/40 text-danger" }[tone];
  return (
    <div role={tone === "danger" ? "alert" : "status"} className={cn("rounded-card border bg-surface px-4 py-3 text-base", colours, className)}>
      {title && <p className="font-medium">{title}</p>}
      {children && <div className="text-text">{children}</div>}
    </div>
  );
}
