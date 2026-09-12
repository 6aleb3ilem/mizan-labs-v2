/** The admin console shell: sections from SPEC §23, menus filtered by permissions. */
import { useInbox, useSession, useOnline } from "@mizan/app-kit";
import { useTranslation } from "@mizan/i18n";
import { AppShell, Button, CommandPalette, DropdownMenu, Select, Spinner, type CommandItem, type NavItem, type NavSection } from "@mizan/ui";
import { Link, Outlet, useNavigate, useRouterState } from "@tanstack/react-router";
import {
  Bell, BookText, Building2, ClipboardList, FileText, Hash, KeyRound, Landmark, LayoutDashboard, ListTree, Mail, Moon, Plug, Search, Server, Settings2, ShieldCheck, Tags, User, Users, Wand2, Workflow,
} from "lucide-react";
import { useMemo, useState } from "react";

type Entry = { key: string; label: string; href: string; icon: React.ReactNode; permission?: [string, string] };
type Section = { key: string; label: string; entries: Entry[] };

export function useAdminSections(): Section[] {
  const { t } = useTranslation();
  const icon = (node: React.ReactNode) => node;
  return useMemo<Section[]>(
    () => [
      { key: "platform", label: t("nav.admin.platform"), entries: [
        { key: "tenants", label: t("nav.admin.tenants"), href: "/platform/tenants", icon: icon(<Server className="size-4" />), permission: ["tenant", "create"] },
        { key: "keys", label: t("nav.admin.keys"), href: "/platform/keys", icon: icon(<KeyRound className="size-4" />), permission: ["tenant", "configure"] },
        { key: "health", label: t("nav.admin.health"), href: "/platform/health", icon: icon(<ShieldCheck className="size-4" />), permission: ["tenant", "configure"] },
      ] },
      { key: "org", label: t("nav.admin.organisation"), entries: [
        { key: "tenant", label: t("nav.admin.tenant"), href: "/org/tenant", icon: icon(<Building2 className="size-4" />), permission: ["tenant", "view"] },
        { key: "branches", label: t("common.branches"), href: "/org/branches", icon: icon(<Landmark className="size-4" />), permission: ["branch", "view"] },
        { key: "departments", label: t("common.departments"), href: "/org/departments", icon: icon(<ListTree className="size-4" />), permission: ["department", "view"] },
        { key: "signatories", label: t("nav.admin.signatories"), href: "/org/signatories", icon: icon(<User className="size-4" />), permission: ["signatory", "view"] },
        { key: "treasury", label: t("nav.admin.treasury_accounts"), href: "/org/treasury-accounts", icon: icon(<Landmark className="size-4" />), permission: ["treasury_account", "view"] },
      ] },
      { key: "access", label: t("nav.admin.access"), entries: [
        { key: "users", label: t("nav.admin.users"), href: "/access/users", icon: icon(<Users className="size-4" />), permission: ["user", "view"] },
        { key: "memberships", label: t("nav.admin.memberships"), href: "/access/memberships", icon: icon(<ClipboardList className="size-4" />), permission: ["user", "view"] },
        { key: "roles", label: t("nav.admin.roles"), href: "/access/roles", icon: icon(<ShieldCheck className="size-4" />), permission: ["role", "view"] },
        { key: "view-as", label: t("nav.admin.view_as"), href: "/access/view-as", icon: icon(<Search className="size-4" />), permission: ["user", "impersonate_view"] },
      ] },
      { key: "config", label: t("common.settings"), entries: [
        { key: "numbering", label: t("nav.admin.numbering"), href: "/numbering", icon: icon(<Hash className="size-4" />), permission: ["numbering_scheme", "view"] },
        { key: "vocabularies", label: t("nav.admin.vocabularies"), href: "/vocabularies", icon: icon(<Tags className="size-4" />), permission: ["vocabulary", "view"] },
        { key: "workflows", label: t("nav.admin.workflows"), href: "/workflows", icon: icon(<Workflow className="size-4" />), permission: ["workflow", "view"] },
        { key: "catalog", label: t("nav.admin.catalog"), href: "/catalog/services", icon: icon(<BookText className="size-4" />), permission: ["service", "view"] },
        { key: "pricing", label: t("nav.admin.pricing"), href: "/pricing/price-lists", icon: icon(<Landmark className="size-4" />), permission: ["price_list", "view"] },
        { key: "payment-terms", label: t("nav.admin.payment_terms"), href: "/payment-terms", icon: icon(<ClipboardList className="size-4" />), permission: ["payment_terms_template", "view"] },
        { key: "documents", label: t("nav.admin.documents"), href: "/documents/templates", icon: icon(<FileText className="size-4" />), permission: ["document_template", "view"] },
        { key: "notifications", label: t("nav.admin.notifications"), href: "/notifications/rules", icon: icon(<Mail className="size-4" />), permission: ["notification_rule", "view"] },
        { key: "portal", label: t("nav.admin.portal"), href: "/portal", icon: icon(<LayoutDashboard className="size-4" />), permission: ["tenant", "configure"] },
        { key: "integrations", label: t("nav.admin.integrations"), href: "/integrations", icon: icon(<Plug className="size-4" />), permission: ["integration", "view"] },
        { key: "audit", label: t("nav.admin.audit"), href: "/audit", icon: icon(<ShieldCheck className="size-4" />), permission: ["audit_event", "view"] },
        { key: "setup", label: t("nav.admin.setup"), href: "/setup", icon: icon(<Wand2 className="size-4" />), permission: ["tenant", "configure"] },
      ] },
    ],
    [t],
  );
}

export function AdminShell() {
  const { t } = useTranslation();
  const session = useSession();
  const inbox = useInbox();
  const online = useOnline();
  const navigate = useNavigate();
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const [paletteOpen, setPaletteOpen] = useState(false);
  const allSections = useAdminSections();

  if (session.status === "loading") {
    return (
      <div className="flex min-h-dvh items-center justify-center">
        <Spinner label={t("common.loading")} />
      </div>
    );
  }

  const sections: NavSection[] = allSections
    .map((section) => ({
      key: section.key,
      label: section.label,
      items: section.entries
        .filter((e) => !e.permission || session.can(e.permission[0], e.permission[1]) || (section.key === "platform" && session.me?.realm === "PLATFORM"))
        .map<NavItem>((e) => ({ key: e.key, label: e.label, href: e.href, icon: e.icon, active: pathname === e.href || pathname.startsWith(`${e.href}/`) })),
    }))
    .filter((s) => s.items.length > 0 && !(s.key === "platform" && session.me?.realm !== "PLATFORM"));

  const commands: CommandItem[] = sections.flatMap((s) => s.items.map((i) => ({ id: i.key, group: String(s.label ?? ""), label: String(i.label), onSelect: () => void navigate({ to: i.href as never }) })));
  const branches = session.me?.memberships ?? [];
  const branchOptions = Array.from(new Map(branches.filter((m) => (m as { branch_id?: string | null }).branch_id).map((m) => [(m as { branch_id?: string }).branch_id!, (m as { branch_code?: string; branch_id?: string }).branch_code ?? (m as { branch_id?: string }).branch_id!])).entries()).map(([value, label]) => ({ value, label }));

  return (
    <AppShell
      brand={
        <Link to="/" className="flex items-center gap-2 text-md font-semibold">
          <Settings2 className="size-5 text-primary" aria-hidden />
          {t("common.app_name")}
        </Link>
      }
      sections={sections}
      sidebarLabel={t("nav.admin.organisation")}
      renderLink={(item, className, children) => (
        <Link key={item.key} to={item.href as never} className={className} aria-current={item.active ? "page" : undefined}>
          {children}
        </Link>
      )}
      offline={!online}
      offlineMessage={t("common.offline")}
      topbar={
        <>
          <Button variant="outline" size="sm" leftIcon={<Search className="size-4" aria-hidden />} onClick={() => setPaletteOpen(true)} className="hidden sm:inline-flex">
            {t("common.search_placeholder")}
          </Button>
          {branchOptions.length > 1 && (
            <div className="w-40">
              <Select value={session.branchId} onValueChange={session.setBranchId} options={branchOptions} aria-describedby={undefined} />
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
              { key: "theme", label: t("common.theme"), icon: <Moon className="size-4" />, onSelect: () => void navigate({ to: "/settings/profile" }) },
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
