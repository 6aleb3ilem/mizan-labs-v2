/** Back-office shell (SPEC §22.1): spaces from permissions, ⌘K, branch switcher, inbox, scan button on tablet. */
import { useApi } from "@mizan/api-client";
import { useInbox, useOnline, useSession } from "@mizan/app-kit";
import { useTranslation } from "@mizan/i18n";
import { AppShell, Button, CommandPalette, DropdownMenu, Select, Spinner, type CommandItem, type NavItem, type NavSection } from "@mizan/ui";
import { useQuery } from "@tanstack/react-query";
import { Link, Outlet, useNavigate, useRouterState } from "@tanstack/react-router";
import { Bell, Briefcase, FlaskConical, FolderKanban, Home, Inbox, Landmark, Search, Truck, User, Wrench } from "lucide-react";
import { useMemo, useState, type ReactNode } from "react";

export type SpaceEntry = { key: string; label: string; href: string; icon?: ReactNode; permission?: [string, string] };
export type Space = { key: string; label: string; icon: ReactNode; entries: SpaceEntry[]; permission?: [string, string] };

export function useSpaces(): Space[] {
  const { t } = useTranslation();
  return useMemo<Space[]>(
    () => [
      { key: "commercial", label: t("nav.commercial"), icon: <Briefcase className="size-4" />, permission: ["quote", "view"], entries: [
        { key: "dashboard", label: t("nav.dashboard"), href: "/commercial/dashboard", permission: ["dashboard", "view"] },
        { key: "accounts", label: t("nav.accounts"), href: "/commercial/accounts", permission: ["account", "view"] },
        { key: "contacts", label: t("nav.contacts"), href: "/commercial/contacts", permission: ["contact", "view"] },
        { key: "quotes", label: t("nav.quotes"), href: "/commercial/quotes", permission: ["quote", "view"] },
        { key: "contracts", label: t("nav.contracts"), href: "/commercial/contracts", permission: ["contract", "view"] },
        { key: "orders", label: t("nav.orders"), href: "/commercial/orders", permission: ["order", "view"] },
        { key: "requests", label: t("nav.requests"), href: "/commercial/requests", permission: ["project", "view"] },
      ] },
      { key: "lab", label: t("nav.laboratory"), icon: <FlaskConical className="size-4" />, permission: ["test_run", "view"], entries: [
        { key: "dashboard", label: t("nav.dashboard"), href: "/lab/dashboard", permission: ["dashboard", "view"] },
        { key: "intake", label: t("nav.new_intake"), href: "/lab/intake/new", permission: ["intake", "create"] },
        { key: "intakes", label: t("nav.intakes"), href: "/lab/intakes", permission: ["intake", "view"] },
        { key: "calendar", label: t("nav.calendar"), href: "/lab/calendar", permission: ["test_run", "view"] },
        { key: "runs", label: t("nav.runs"), href: "/lab/runs", permission: ["test_run", "view"] },
        { key: "stages", label: t("nav.stages"), href: "/lab/stages", permission: ["specimen", "view"] },
        { key: "review", label: t("nav.review"), href: "/lab/review", permission: ["test_run", "review_results"] },
        { key: "reports", label: t("nav.reports"), href: "/lab/reports", permission: ["report", "view"] },
        { key: "tests", label: t("nav.tests"), href: "/lab/tests", permission: ["test_run", "view"] },
        { key: "samples", label: t("nav.samples"), href: "/lab/samples", permission: ["sample", "view"] },
      ] },
      { key: "finance", label: t("nav.finance"), icon: <Landmark className="size-4" />, permission: ["invoice", "view"], entries: [
        { key: "dashboard", label: t("nav.dashboard"), href: "/finance/dashboard", permission: ["dashboard", "view"] },
        { key: "to-invoice", label: t("nav.to_invoice"), href: "/finance/to-invoice", permission: ["invoice", "create"] },
        { key: "invoices", label: t("nav.invoices"), href: "/finance/invoices", permission: ["invoice", "view"] },
        { key: "credit-notes", label: t("nav.credit_notes"), href: "/finance/credit-notes", permission: ["credit_note", "view"] },
        { key: "payments", label: t("nav.payments"), href: "/finance/payments", permission: ["payment", "view"] },
        { key: "treasury", label: t("nav.treasury"), href: "/finance/treasury", permission: ["treasury_entry", "view"] },
        { key: "statements", label: t("nav.statements"), href: "/finance/statements", permission: ["invoice", "view"] },
        { key: "dunning", label: t("nav.dunning"), href: "/finance/dunning", permission: ["invoice", "view"] },
        { key: "reconciliation", label: t("nav.reconciliation"), href: "/finance/reconciliation", permission: ["payment", "view"] },
      ] },
      { key: "assets", label: t("nav.assets"), icon: <Wrench className="size-4" />, permission: ["equipment", "view"], entries: [
        { key: "dashboard", label: t("nav.dashboard"), href: "/assets/dashboard" },
        { key: "equipment", label: t("nav.equipment"), href: "/assets/equipment", permission: ["equipment", "view"] },
        { key: "stock", label: t("nav.stock"), href: "/assets/stock", permission: ["stock", "view"] },
        { key: "consumables", label: t("nav.consumables"), href: "/assets/consumables", permission: ["consumable", "view"] },
        { key: "rentals", label: t("nav.rentals"), href: "/assets/rentals", permission: ["rental", "view"] },
        { key: "sales", label: t("nav.sales"), href: "/assets/sales", permission: ["sale", "view"] },
        { key: "outings", label: t("nav.outings"), href: "/assets/outings", permission: ["outing", "view"] },
        { key: "transfers", label: t("nav.transfers"), href: "/assets/transfers", permission: ["transfer", "view"] },
        { key: "maintenance", label: t("nav.maintenance"), href: "/assets/maintenance", permission: ["maintenance", "view"] },
        { key: "fleet", label: t("nav.fleet"), href: "/assets/fleet", permission: ["vehicle", "view"] },
        { key: "calendar", label: t("nav.calendar"), href: "/assets/calendar", permission: ["rental", "view"] },
        { key: "alerts", label: t("nav.alerts"), href: "/assets/alerts", permission: ["equipment", "view"] },
      ] },
      { key: "delivery", label: t("nav.delivery"), icon: <Truck className="size-4" />, permission: ["work_order", "view"], entries: [
        { key: "dashboard", label: t("nav.dashboard"), href: "/delivery/dashboard" },
        { key: "work-orders", label: t("nav.work_orders"), href: "/delivery/work-orders", permission: ["work_order", "view"] },
        { key: "responsibles", label: t("nav.responsibles"), href: "/delivery/responsibles", permission: ["work_order", "view"] },
      ] },
    ],
    [t],
  );
}

export function useBranchOptions() {
  const api = useApi();
  const session = useSession();
  const branches = useQuery({ queryKey: ["branches", "list", {}], queryFn: async () => (await api.client.GET("/branches")).data ?? [], enabled: session.status === "authenticated" && session.can("branch", "view") });
  const mine = new Set(session.branchIds);
  const all = mine.has(null);
  return (branches.data ?? []).filter((b) => all || mine.has(b.id)).map((b) => ({ value: b.id, label: b.code }));
}

export function BackOfficeShell() {
  const { t } = useTranslation();
  const session = useSession();
  const inbox = useInbox();
  const online = useOnline();
  const navigate = useNavigate();
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const [paletteOpen, setPaletteOpen] = useState(false);
  const spaces = useSpaces();
  const branchOptions = useBranchOptions();

  if (session.status === "loading") {
    return (
      <div className="flex min-h-dvh items-center justify-center">
        <Spinner label={t("common.loading")} />
      </div>
    );
  }
  const allowed = (p?: [string, string]) => !p || session.can(p[0], p[1]);
  const active = (href: string) => pathname === href || pathname.startsWith(`${href}/`);
  const sections: NavSection[] = [
    { key: "main", items: [
      { key: "home", label: t("nav.home"), href: "/home", icon: <Home className="size-4" />, active: active("/home") },
      { key: "inbox", label: t("nav.inbox"), href: "/inbox", icon: <Inbox className="size-4" />, active: active("/inbox"), badge: inbox.unread || undefined },
      { key: "projects", label: t("nav.projects"), href: "/projects", icon: <FolderKanban className="size-4" />, active: active("/projects") },
    ] },
    ...spaces
      .filter((space) => allowed(space.permission) && space.entries.some((e) => allowed(e.permission)))
      .map((space) => ({ key: space.key, label: space.label, items: space.entries.filter((e) => allowed(e.permission)).map<NavItem>((e) => ({ key: `${space.key}-${e.key}`, label: e.label, href: e.href, icon: e.icon, active: active(e.href) })) })),
  ];
  const commands: CommandItem[] = sections.flatMap((s) => s.items.map((i) => ({ id: i.key, group: String(s.label ?? t("nav.home")), label: String(i.label), onSelect: () => void navigate({ to: i.href as never }) })));
  const bottomNav: NavItem[] = [sections[0]!.items[0]!, ...sections.slice(1, 4).map((s) => ({ ...s.items[0]!, label: s.label, icon: spaces.find((sp) => sp.key === s.key)?.icon }))];

  return (
    <AppShell
      brand={
        <Link to="/home" className="flex items-center gap-2 text-md font-semibold">
          <FlaskConical className="size-5 text-primary" aria-hidden />
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
      onScan={() => void navigate({ to: "/lab/runs" })}
      scanLabel="Scan"
      bottomNav={bottomNav}
      topbar={
        <>
          <Button variant="outline" size="sm" leftIcon={<Search className="size-4" aria-hidden />} onClick={() => setPaletteOpen(true)} className="hidden sm:inline-flex">
            {t("common.search_placeholder")}
          </Button>
          {branchOptions.length > 1 && (
            <div className="w-32">
              <Select value={session.branchId} onValueChange={session.setBranchId} options={branchOptions} />
            </div>
          )}
          <span className="flex-1" />
          <Button variant="ghost" size="icon-sm" aria-label={t("common.notifications")} onClick={() => void navigate({ to: "/inbox" })} className="relative">
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
              { key: "profile", label: t("common.profile"), icon: <User className="size-4" />, onSelect: () => void navigate({ to: "/settings/profile" }) },
              { key: "sep", label: "", separator: true },
              { key: "logout", label: t("common.sign_out"), destructive: true, onSelect: () => void session.logout().then(() => navigate({ to: "/login" })) },
            ]}
          />
        </>
      }
    >
      <Outlet />
      <CommandPalette open={paletteOpen} onOpenChange={setPaletteOpen} items={commands} placeholder={t("common.search_placeholder")} emptyLabel={t("common.empty_title")} />
    </AppShell>
  );
}
