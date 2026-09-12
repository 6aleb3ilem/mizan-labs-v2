/** Portal home (SPEC §24): open projects, pending quotes, latest reports, unpaid invoices, notifications. */
import { useApi, type Notification } from "@mizan/api-client";
import { useSession } from "@mizan/app-kit";
import { formatRelative, currentLocale, useTranslation } from "@mizan/i18n";
import { Button, Card, EmptyState, PageHeader } from "@mizan/ui";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "@tanstack/react-router";
import { MessageSquare, Plus } from "lucide-react";

export function HomePage() {
  const { t } = useTranslation();
  const api = useApi();
  const session = useSession();
  const navigate = useNavigate();
  const locale = currentLocale();
  const notifications = useQuery({ queryKey: ["me", "notifications", "recent"], queryFn: async () => (await api.client.GET("/me/notifications", { params: { query: { limit: 10 } } })).data });
  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title={t("auth.welcome_back", { name: session.me?.display_name || session.me?.email })}
        actions={
          <>
            <Button leftIcon={<Plus className="size-4" aria-hidden />} onClick={() => void navigate({ to: "/requests/new" })}>
              {t("nav.portal.request_quote")}
            </Button>
            <Button variant="outline" leftIcon={<MessageSquare className="size-4" aria-hidden />} onClick={() => void navigate({ to: "/requests/new" })}>
              {t("nav.portal.ask_question")}
            </Button>
          </>
        }
      />
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {(["projects", "quotes", "reports", "invoices"] as const).map((key) => (
          <Card key={key} title={t(`nav.portal.${key}`)}>
            <EmptyState title={t("common.empty_title")} className="py-6" action={<Button variant="link" onClick={() => void navigate({ to: `/${key}` as never })}>{t(`nav.portal.${key}`)}</Button>} />
          </Card>
        ))}
      </div>
      <Card title={t("common.notifications")}>
        {notifications.data?.items.length ? (
          <ul className="flex flex-col divide-y divide-line">
            {notifications.data.items.map((n: Notification) => (
              <li key={n.id} className="py-2">
                <p className="text-base font-medium">{n.title}</p>
                {n.body && <p className="text-sm text-muted">{n.body}</p>}
                <p className="text-xs text-muted">{formatRelative(n.created_at, locale)}</p>
              </li>
            ))}
          </ul>
        ) : (
          <EmptyState title={t("common.no_notifications")} className="py-6" />
        )}
      </Card>
    </div>
  );
}
