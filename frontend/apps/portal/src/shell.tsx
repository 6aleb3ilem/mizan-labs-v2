/** Client portal shell (SPEC §24): lighter density, bottom navigation on phones, one-handed use. */
import { useInbox, useOnline, useSession } from "@mizan/app-kit";
import { useTranslation } from "@mizan/i18n";
import { AppShell, Button, DropdownMenu, Spinner, type NavItem, type NavSection } from "@mizan/ui";
import { Link, Outlet, useNavigate, useRouterState } from "@tanstack/react-router";
import { Bell, FileText, FolderKanban, History, Home, MessageSquare, Receipt, User, Wallet } from "lucide-react";

export function PortalShell() {
  const { t } = useTranslation();
  const session = useSession();
  const inbox = useInbox();
  const online = useOnline();
  const navigate = useNavigate();
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  if (session.status === "loading") {
    return (
      <div className="flex min-h-dvh items-center justify-center">
        <Spinner label={t("common.loading")} />
      </div>
    );
  }
  const active = (href: string) => pathname === href || pathname.startsWith(`${href}/`);
  const items: NavItem[] = [
    { key: "home", label: t("nav.portal.home"), href: "/home", icon: <Home className="size-4" />, active: active("/home") },
    { key: "projects", label: t("nav.portal.projects"), href: "/projects", icon: <FolderKanban className="size-4" />, active: active("/projects") },
    { key: "quotes", label: t("nav.portal.quotes"), href: "/quotes", icon: <FileText className="size-4" />, active: active("/quotes") },
    { key: "reports", label: t("nav.portal.reports"), href: "/reports", icon: <FileText className="size-4" />, active: active("/reports") },
    { key: "invoices", label: t("nav.portal.invoices"), href: "/invoices", icon: <Receipt className="size-4" />, active: active("/invoices") },
    { key: "payments", label: t("nav.portal.payments"), href: "/payments", icon: <Wallet className="size-4" />, active: active("/payments") },
    { key: "requests", label: t("nav.portal.requests"), href: "/requests", icon: <MessageSquare className="size-4" />, active: active("/requests") },
    { key: "account", label: t("nav.portal.account"), href: "/account", icon: <User className="size-4" />, active: active("/account") },
    { key: "history", label: t("nav.portal.history"), href: "/history", icon: <History className="size-4" />, active: active("/history") },
  ];
  const sections: NavSection[] = [{ key: "main", items }];
  return (
    <AppShell
      brand={
        <Link to="/home" className="text-md font-semibold">
          {t("common.app_name")}
        </Link>
      }
      sections={sections}
      renderLink={(item, className, children) => (
        <Link key={item.key} to={item.href as never} className={className} aria-current={item.active ? "page" : undefined}>
          {children}
        </Link>
      )}
      offline={!online}
      offlineMessage={t("common.offline")}
      bottomNav={[items[0]!, items[1]!, items[2]!, items[4]!, items[7]!]}
      topbar={
        <>
          <span className="flex-1" />
          <Button variant="ghost" size="icon-sm" aria-label={t("common.notifications")} onClick={() => void navigate({ to: "/home" })} className="relative">
            <Bell className="size-4" aria-hidden />
            {inbox.unread > 0 && <span className="absolute -right-0.5 -top-0.5 rounded-full bg-danger px-1 text-[10px] font-semibold text-white">{inbox.unread}</span>}
          </Button>
          <DropdownMenu
            trigger={
              <Button variant="ghost" size="sm" leftIcon={<User className="size-4" aria-hidden />}>
                <span className="max-w-32 truncate">{session.me?.display_name || session.me?.email}</span>
              </Button>
            }
            items={[
              { key: "account", label: t("nav.portal.account"), onSelect: () => void navigate({ to: "/account" }) },
              { key: "sep", label: "", separator: true },
              { key: "logout", label: t("common.sign_out"), destructive: true, onSelect: () => void session.logout().then(() => navigate({ to: "/login" })) },
            ]}
          />
        </>
      }
    >
      <div className="mx-auto w-full max-w-5xl">
        <Outlet />
      </div>
    </AppShell>
  );
}
