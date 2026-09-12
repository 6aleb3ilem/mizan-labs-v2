import { useApi, type Notification } from "@mizan/api-client";
import { usePagedQuery, useInbox } from "@mizan/app-kit";
import { formatRelative, currentLocale, useTranslation } from "@mizan/i18n";
import { Button, EmptyState, PageHeader, SkeletonRows, cn } from "@mizan/ui";
import { useNavigate } from "@tanstack/react-router";
import { CheckCheck } from "lucide-react";

export function InboxPage() {
  const { t } = useTranslation();
  const api = useApi();
  const inbox = useInbox();
  const navigate = useNavigate();
  const locale = currentLocale();
  const paged = usePagedQuery<Notification>(["me", "notifications", "page"], async (client, after) => (await client.client.GET("/me/notifications", { params: { query: { after: after ?? undefined, limit: 50 } } })).data);
  void api;

  return (
    <div className="flex flex-col gap-4">
      <PageHeader
        title={t("common.notifications")}
        actions={
          <Button variant="outline" size="sm" leftIcon={<CheckCheck className="size-4" aria-hidden />} onClick={() => void inbox.markAllRead().then(paged.refetch)} disabled={inbox.unread === 0}>
            {t("common.mark_all_read")}
          </Button>
        }
      />
      {paged.loading && paged.items.length === 0 ? (
        <SkeletonRows rows={6} />
      ) : paged.items.length === 0 ? (
        <EmptyState title={t("common.no_notifications")} />
      ) : (
        <ul className="flex flex-col divide-y divide-line rounded-card border border-line bg-surface">
          {paged.items.map((n) => (
            <li key={n.id}>
              <button
                type="button"
                className={cn("flex w-full flex-col gap-0.5 px-4 py-3 text-left hover:bg-subtle", !n.read_at && "bg-primary-subtle/40")}
                onClick={() => {
                  if (!n.read_at) void inbox.markRead([n.id]).then(paged.refetch);
                  if (n.link) void navigate({ to: n.link as never });
                }}
              >
                <span className="flex items-center justify-between gap-2">
                  <span className={cn("text-base", !n.read_at && "font-semibold")}>{n.title}</span>
                  <span className="shrink-0 text-xs text-muted">{formatRelative(n.created_at, locale)}</span>
                </span>
                {n.body && <span className="text-sm text-muted">{n.body}</span>}
              </button>
            </li>
          ))}
        </ul>
      )}
      {paged.hasMore && (
        <Button variant="outline" size="sm" onClick={paged.loadMore} loading={paged.loading}>
          {t("common.load_more")}
        </Button>
      )}
    </div>
  );
}
