import { useOnline } from "@mizan/app-kit";
import { useTranslation, setLocale, currentLocale } from "@mizan/i18n";
import { Button, cn } from "@mizan/ui";
import { Link, useRouterState } from "@tanstack/react-router";
import { ShieldCheck, WifiOff } from "lucide-react";
import type { ReactNode } from "react";

export function VerifyShell({ children }: { children: ReactNode }) {
  const { t } = useTranslation();
  const online = useOnline();
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const links = [
    { to: "/", label: t("verify.title") },
    { to: "/keys", label: t("verify.keys") },
    { to: "/transparency", label: t("verify.transparency") },
    { to: "/offline", label: t("verify.offline_mode") },
  ];
  return (
    <div className="flex min-h-dvh flex-col bg-canvas">
      <header className="border-b border-line bg-surface">
        <div className="mx-auto flex h-14 w-full max-w-3xl items-center gap-4 px-4">
          <Link to="/" className="flex items-center gap-2 text-md font-semibold">
            <ShieldCheck className="size-5 text-primary" aria-hidden />
            {t("common.app_name")}
          </Link>
          <nav aria-label="Main" className="ml-auto flex items-center gap-1 overflow-x-auto">
            {links.map((link) => (
              <Link key={link.to} to={link.to} className={cn("rounded-control px-2 py-1 text-sm text-muted hover:text-text", pathname === link.to && "bg-subtle text-text")} aria-current={pathname === link.to ? "page" : undefined}>
                {link.label}
              </Link>
            ))}
            <Button variant="ghost" size="sm" onClick={() => void setLocale(currentLocale() === "fr" ? "en" : "fr")} aria-label={t("common.locale")}>
              {currentLocale() === "fr" ? "EN" : "FR"}
            </Button>
          </nav>
        </div>
      </header>
      {!online && (
        <div role="status" className="flex items-center justify-center gap-2 bg-warning px-4 py-1.5 text-sm text-white">
          <WifiOff className="size-4" aria-hidden />
          {t("verify.offline_mode")}
        </div>
      )}
      <main className="mx-auto w-full max-w-3xl flex-1 px-4 py-6">{children}</main>
      <footer className="border-t border-line px-4 py-3 text-center text-xs text-muted">Mizan Labs · PDF/A · PAdES · Ed25519</footer>
    </div>
  );
}
