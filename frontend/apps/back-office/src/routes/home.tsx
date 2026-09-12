/** Home (SPEC §22.2): cards for authorised spaces, "My day", recent items, quick create. */
import { useApi, type Notification } from "@mizan/api-client";
import { useSession } from "@mizan/app-kit";
import { formatRelative, currentLocale, useTranslation } from "@mizan/i18n";
import { Button, Card, EmptyState, KpiCard, PageHeader } from "@mizan/ui";
import { useQuery } from "@tanstack/react-query";
import { Link, useNavigate } from "@tanstack/react-router";
import { Plus } from "lucide-react";

import { useSpaces } from "../shell";

export function HomePage() {
  const { t } = useTranslation();
  const api = useApi();
  const session = useSession();
  const navigate = useNavigate();
  const spaces = useSpaces();
  const locale = currentLocale();
  const notifications = useQuery({
    queryKey: ["me", "notifications", "recent"],
    queryFn: async () => (await api.client.GET("/me/notifications", { params: { query: { limit: 8, unread: true } } })).data,
  });
  type Quick = { key: string; label: string; href: string; permission: [string, string] };
  const quickAll: Quick[] = [
    { key: "intake", label: t("nav.new_intake"), href: "/lab/intake/new", permission: ["intake", "create"] },
    { key: "quote", label: t("nav.quotes"), href: "/commercial/quotes", permission: ["quote", "create"] },
    { key: "payment", label: t("nav.payments"), href: "/finance/payments", permission: ["payment", "create"] },
    { key: "rental", label: t("nav.rentals"), href: "/assets/rentals", permission: ["rental", "create"] },
  ];
  const quick = quickAll.filter((q) => session.can(q.permission[0], q.permission[1]));
  const today = new Intl.DateTimeFormat(locale === "fr" ? "fr-FR" : "en-GB", { weekday: "long", day: "numeric", month: "long" }).format(new Date());

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title={t("auth.welcome_back", { name: session.me?.display_name || session.me?.email })}
        subtitle={today}
        actions={quick.map((q) => (
          <Button key={q.key} variant={q.key === quick[0]?.key ? "primary" : "outline"} leftIcon={<Plus className="size-4" aria-hidden />} onClick={() => void navigate({ to: q.href as never })}>
            {q.label}
          </Button>
        ))}
      />
      <section aria-labelledby="my-day">
        <h2 id="my-day" className="mb-2 text-md font-semibold">
          {t("nav.my_day")}
        </h2>
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          <KpiCard label={t("nav.runs")} value="—" hint={t("nav.laboratory")} onClick={() => void navigate({ to: "/lab/runs" })} />
          <KpiCard label={t("nav.quotes")} value="—" hint={t("nav.commercial")} onClick={() => void navigate({ to: "/commercial/quotes" })} />
          <KpiCard label={t("nav.to_invoice")} value="—" hint={t("nav.finance")} onClick={() => void navigate({ to: "/finance/to-invoice" })} />
          <KpiCard label={t("nav.alerts")} value={notifications.data?.items.length ?? "—"} tone={notifications.data?.items.length ? "warning" : undefined} onClick={() => void navigate({ to: "/inbox" })} />
        </div>
      </section>
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="flex flex-col gap-4 lg:col-span-2">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {spaces
              .filter((space) => !space.permission || session.can(space.permission[0], space.permission[1]))
              .map((space) => (
                <Card key={space.key} title={<span className="flex items-center gap-2">{space.icon}{space.label}</span>}>
                  <ul className="grid grid-cols-2 gap-1">
                    {space.entries
                      .filter((e) => !e.permission || session.can(e.permission[0], e.permission[1]))
                      .slice(0, 6)
                      .map((entry) => (
                        <li key={entry.key}>
                          <Link to={entry.href as never} className="block rounded-control px-2 py-1 text-base hover:bg-subtle">
                            {entry.label}
                          </Link>
                        </li>
                      ))}
                  </ul>
                </Card>
              ))}
          </div>
        </div>
        <Card title={t("common.notifications")} actions={<Link to="/inbox" className="text-sm text-primary">{t("nav.inbox")}</Link>}>
          {notifications.data?.items.length ? (
            <ul className="flex flex-col divide-y divide-line">
              {notifications.data.items.map((n: Notification) => (
                <li key={n.id} className="py-2">
                  <button type="button" className="w-full text-left" onClick={() => n.link && void navigate({ to: n.link as never })}>
                    <span className="block text-base font-medium">{n.title}</span>
                    <span className="block text-xs text-muted">{formatRelative(n.created_at, locale)}</span>
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <EmptyState title={t("common.no_notifications")} className="py-6" />
          )}
        </Card>
      </div>
    </div>
  );
}
