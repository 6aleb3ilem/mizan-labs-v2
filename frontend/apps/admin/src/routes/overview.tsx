import { useApi } from "@mizan/api-client";
import { useSession } from "@mizan/app-kit";
import { useTranslation } from "@mizan/i18n";
import { KpiCard, PageHeader, Card } from "@mizan/ui";
import { useQuery } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";

import { useAdminSections } from "../shell";

export function OverviewPage() {
  const { t } = useTranslation();
  const api = useApi();
  const session = useSession();
  const sections = useAdminSections();
  const branches = useQuery({ queryKey: ["branches", "list", {}], queryFn: async () => (await api.client.GET("/branches")).data ?? [], enabled: session.can("branch", "view") });
  const users = useQuery({ queryKey: ["users", "list", { limit: 200 }], queryFn: async () => (await api.client.GET("/users", { params: { query: { limit: 200 } } })).data, enabled: session.can("user", "view") });
  const roles = useQuery({ queryKey: ["roles", "list", {}], queryFn: async () => (await api.client.GET("/roles")).data ?? [], enabled: session.can("role", "view") });
  const deliveries = useQuery({ queryKey: ["notification-deliveries", "list", { status: "FAILED" }], queryFn: async () => (await api.client.GET("/notification-deliveries", { params: { query: { status: "FAILED", limit: 50 } } })).data, enabled: session.can("notification_rule", "view") });

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title={t("auth.welcome_back", { name: session.me?.display_name || session.me?.email })} subtitle={t("nav.admin.organisation")} />
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <KpiCard label={t("common.branches")} value={branches.data?.length ?? "—"} />
        <KpiCard label={t("nav.admin.users")} value={users.data?.items.length ?? "—"} />
        <KpiCard label={t("nav.admin.roles")} value={roles.data?.length ?? "—"} />
        <KpiCard label={t("nav.admin.log")} value={deliveries.data?.items.length ?? "—"} tone={deliveries.data?.items.length ? "danger" : undefined} hint="FAILED" />
      </div>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
        {sections
          .filter((s) => s.key !== "platform" || session.me?.realm === "PLATFORM")
          .map((section) => (
            <Card key={section.key} title={section.label}>
              <ul className="flex flex-col gap-1">
                {section.entries
                  .filter((e) => !e.permission || session.can(e.permission[0], e.permission[1]) || session.me?.realm === "PLATFORM")
                  .map((entry) => (
                    <li key={entry.key}>
                      <Link to={entry.href as never} className="flex items-center gap-2 rounded-control px-2 py-1.5 text-base hover:bg-subtle">
                        <span className="text-muted">{entry.icon}</span>
                        {entry.label}
                      </Link>
                    </li>
                  ))}
              </ul>
            </Card>
          ))}
      </div>
    </div>
  );
}
