import { CheckCircle2, Info, X, XCircle } from "lucide-react";
import { Toast as RadixToast } from "radix-ui";
import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";

import { cn } from "../cn";

export type ToastTone = "info" | "success" | "danger";
export type ToastInput = { title: ReactNode; description?: ReactNode; tone?: ToastTone; duration?: number; action?: { label: string; onClick: () => void } };
type ToastRecord = ToastInput & { id: number };

const ToastContext = createContext<((toast: ToastInput) => void) | null>(null);

export function useToast() {
  const push = useContext(ToastContext);
  if (!push) throw new Error("useToast must be used inside <ToastProvider>");
  return useMemo(
    () => ({
      show: push,
      success: (title: ReactNode, description?: ReactNode) => push({ title, description, tone: "success" }),
      error: (title: ReactNode, description?: ReactNode) => push({ title, description, tone: "danger", duration: 8000 }),
      info: (title: ReactNode, description?: ReactNode) => push({ title, description, tone: "info" }),
    }),
    [push],
  );
}

const icons = { info: Info, success: CheckCircle2, danger: XCircle };

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastRecord[]>([]);
  const push = useCallback((toast: ToastInput) => {
    setToasts((current) => [...current.slice(-4), { ...toast, id: Date.now() + Math.random() }]);
  }, []);
  return (
    <ToastContext.Provider value={push}>
      <RadixToast.Provider swipeDirection="right" duration={5000}>
        {children}
        {toasts.map((toast) => {
          const Icon = icons[toast.tone ?? "info"];
          return (
            <RadixToast.Root
              key={toast.id}
              duration={toast.duration}
              onOpenChange={(open) => !open && setToasts((current) => current.filter((t) => t.id !== toast.id))}
              className={cn("flex items-start gap-3 rounded-card border border-line bg-surface p-3 shadow-3", toast.tone === "danger" && "border-danger/50")}
            >
              <Icon className={cn("mt-0.5 size-5 shrink-0", toast.tone === "success" && "text-success", toast.tone === "danger" && "text-danger", toast.tone === "info" && "text-info")} aria-hidden />
              <div className="flex-1">
                <RadixToast.Title className="text-base font-medium">{toast.title}</RadixToast.Title>
                {toast.description && <RadixToast.Description className="text-sm text-muted">{toast.description}</RadixToast.Description>}
                {toast.action && (
                  <RadixToast.Action altText={toast.action.label} asChild>
                    <button type="button" className="mt-1 text-sm font-medium text-primary" onClick={toast.action.onClick}>
                      {toast.action.label}
                    </button>
                  </RadixToast.Action>
                )}
              </div>
              <RadixToast.Close className="text-muted hover:text-text" aria-label="Close">
                <X className="size-4" aria-hidden />
              </RadixToast.Close>
            </RadixToast.Root>
          );
        })}
        <RadixToast.Viewport className="fixed bottom-4 right-4 z-50 flex w-96 max-w-[calc(100vw-2rem)] flex-col gap-2 outline-none" />
      </RadixToast.Provider>
    </ToastContext.Provider>
  );
}
