/**
 * The audit log (SPEC §23.7, §20).
 *
 * Append-only: every write in the system lands here with who, what, when and the before/after of
 * the fields that moved. The screen's job is not to list events — it is to answer "what changed
 * on this record, and who did it", so the row expands into a field-level diff rather than a JSON
 * blob, and only the keys that actually differ are shown.
 *
 * The list is cursor-paginated on the timestamp, because an audit log is unbounded by design.
 */
import { useApi } from "@mizan/api-client";
import { usePagedQuery, useSession } from "@mizan/app-kit";
import { currentLocale, formatDateTime, useTranslation } from "@mizan/i18n";
import {
  Badge,
  Button,
  Drawer,
  ErrorState,
  Input,
  PageHeader,
  Select,
  SkeletonRows,
  EmptyState,
  useChangeHighlight,
} from "@mizan/ui";
import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";

type AuditEvent = {
  id: string;
  branch_id: string | null;
  aggregate_type: string;
  aggregate_id: string | null;
  action: string;
  actor_id: string | null;
  actor_type: string;
  at: string;
  before: Record<string, unknown> | null;
  after: Record<string, unknown> | null;
  context: Record<string, unknown>;
};

type User = { id: string; email: string; display_name: string };

/** Only the keys whose value actually moved: an event that touched one field shows one row. */
function diffOf(event: AuditEvent): { field: string; before: unknown; after: unknown }[] {
  const before = event.before ?? {};
  const after = event.after ?? {};
  const fields = [...new Set([...Object.keys(before), ...Object.keys(after)])].sort();
  return fields
    .map((field) => ({ field, before: before[field], after: after[field] }))
    .filter(({ before: a, after: b }) => JSON.stringify(a) !== JSON.stringify(b));
}

function display(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function actionTone(action: string): "success" | "danger" | "amber" | "slate" {
  if (/created|added|activated/.test(action)) return "success";
  if (/deleted|revoked|disabled|cancelled/.test(action)) return "danger";
  if (/issued|approved|signed/.test(action)) return "amber";
  return "slate";
}

export function AuditPage() {
  const { t } = useTranslation();
  const api = useApi();
  const session = useSession();
  const locale = currentLocale();

  const [resource, setResource] = useState("");
  const [action, setAction] = useState("");
  const [since, setSince] = useState("");
  const [selected, setSelected] = useState<AuditEvent | null>(null);

  const events = usePagedQuery<AuditEvent>(
    ["audit-events", { resource, action, since }],
    async (client, after) =>
      (await client.client.GET("/audit-events", {
        params: {
          query: {
            ...(resource ? { aggregate_type: resource } : {}),
            ...(action ? { action } : {}),
            ...(since ? { since: new Date(since).toISOString() } : {}),
            ...(after ? { after } : {}),
            limit: 50,
          } as never,
        },
      })).data as never,
    { enabled: session.can("audit_event", "view") },
  );

  /* Actors are stored as ids. Resolving them to names once, here, is what turns the log from a
     forensic dump into something a manager can read. */
  const userList = useQuery({
    queryKey: ["users", "list", { limit: 200 }],
    queryFn: async () => ((await api.client.GET("/users", { params: { query: { limit: 200 } } })).data?.items ?? []) as User[],
    enabled: session.can("user", "view"),
  });
  const users = useMemo(() => new Map((userList.data ?? []).map((u) => [u.id, u])), [userList.data]);
  const actorName = (event: AuditEvent) => {
    if (!event.actor_id) return t("audit.system_actor");
    const user = users.get(event.actor_id);
    return user ? user.display_name || user.email : event.actor_id.slice(0, 8);
  };

  // Newest event first; the list highlights when a fresh page changes what is on top.
  const newest = events.items[0]?.id;
  const listRef = useChangeHighlight<HTMLDivElement>(newest);

  const resourceOptions = useMemo(
    () => [...new Set(events.items.map((event) => event.aggregate_type))].sort().map((value) => ({ value, label: value })),
    [events.items],
  );
  const actionOptions = useMemo(
    () => [...new Set(events.items.map((event) => event.action))].sort().map((value) => ({ value, label: value })),
    [events.items],
  );

  return (
    <div className="flex flex-col gap-4">
      <PageHeader title={t("nav.admin.audit")} subtitle={t("audit.hint")} />

      <div className="flex flex-wrap items-end gap-3">
        <Select
          value={resource}
          onValueChange={setResource}
          allowEmpty
          emptyLabel={t("common.all")}
          placeholder={t("audit.resource")}
          className="w-52"
          options={resourceOptions}
          aria-label={t("audit.resource")}
        />
        <Select
          value={action}
          onValueChange={setAction}
          allowEmpty
          emptyLabel={t("common.all")}
          placeholder={t("audit.action")}
          className="w-52"
          options={actionOptions}
          aria-label={t("audit.action")}
        />
        <Input type="date" value={since} onChange={(e) => setSince(e.target.value)} className="w-44 tabular" aria-label={t("common.date")} />
        {(resource || action || since) && (
          <Button
            variant="ghost"
            onClick={() => {
              setResource("");
              setAction("");
              setSince("");
            }}
          >
            {t("common.cancel")}
          </Button>
        )}
        <span className="ml-auto text-sm text-muted">{t("common.results", { count: events.items.length })}</span>
      </div>

      {events.error ? (
        <ErrorState title={t("common.error_title")} onRetry={events.refetch} retryLabel={t("common.retry")} />
      ) : events.loading && events.items.length === 0 ? (
        <div className="rounded-card border border-line bg-surface">
          <SkeletonRows rows={8} columns={5} />
        </div>
      ) : events.items.length === 0 ? (
        <EmptyState title={t("common.empty_title")} hint={t("common.empty_hint")} kind="search" />
      ) : (
        <div ref={listRef} className="overflow-hidden rounded-card border border-line bg-surface">
          <ul className="divide-y divide-line">
            {events.items.map((event) => {
              const changes = diffOf(event);
              return (
                <li key={event.id}>
                  <button
                    type="button"
                    onClick={() => setSelected(event)}
                    className="flex w-full items-center gap-3 px-3 py-2.5 text-left hover-colors hover:bg-subtle"
                  >
                    <span className="tabular w-40 shrink-0 text-sm text-muted">{formatDateTime(event.at, locale)}</span>
                    <Badge tone={actionTone(event.action)}>{event.action}</Badge>
                    <span className="font-medium">{event.aggregate_type}</span>
                    <span className="truncate text-sm text-muted">{actorName(event)}</span>
                    {changes.length > 0 && (
                      <span className="ml-auto shrink-0 text-xs text-muted">
                        {t("common.results", { count: changes.length })}
                      </span>
                    )}
                  </button>
                </li>
              );
            })}
          </ul>
          {events.hasMore && (
            <div className="border-t border-line p-3 text-center">
              <Button variant="outline" onClick={events.loadMore} loading={events.loading}>
                {t("common.load_more")}
              </Button>
            </div>
          )}
        </div>
      )}

      <Drawer
        open={!!selected}
        onOpenChange={(next) => !next && setSelected(null)}
        title={selected ? `${selected.aggregate_type} · ${selected.action}` : ""}
        description={selected ? `${formatDateTime(selected.at, locale)} — ${actorName(selected)}` : undefined}
        closeLabel={t("common.close")}
      >
        {selected && <AuditDetail event={selected} />}
      </Drawer>
    </div>
  );
}

function AuditDetail({ event }: { event: AuditEvent }) {
  const { t } = useTranslation();
  const changes = diffOf(event);
  return (
    <div className="flex flex-col gap-4">
      <dl className="grid grid-cols-2 gap-3 text-sm">
        <div>
          <dt className="text-xs uppercase tracking-wide text-muted">{t("audit.resource")}</dt>
          <dd>{event.aggregate_type}</dd>
        </div>
        <div>
          <dt className="text-xs uppercase tracking-wide text-muted">{t("audit.action")}</dt>
          <dd>{event.action}</dd>
        </div>
        <div className="col-span-2">
          <dt className="text-xs uppercase tracking-wide text-muted">id</dt>
          <dd className="tabular truncate">{event.aggregate_id ?? "—"}</dd>
        </div>
      </dl>

      <section>
        <h4 className="mb-2 text-sm font-semibold">{t("audit.changes")}</h4>
        {changes.length === 0 ? (
          <p className="text-sm text-muted">{t("audit.no_changes")}</p>
        ) : (
          <div className="overflow-hidden rounded-card border border-line">
            <table className="w-full text-sm">
              <thead className="bg-subtle text-xs uppercase tracking-wide text-muted">
                <tr>
                  <th scope="col" className="px-3 py-1.5 text-left">
                    {t("common.label")}
                  </th>
                  <th scope="col" className="px-3 py-1.5 text-left">
                    {t("audit.before")}
                  </th>
                  <th scope="col" className="px-3 py-1.5 text-left">
                    {t("audit.after")}
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {changes.map((change) => (
                  <tr key={change.field}>
                    <th scope="row" className="px-3 py-1.5 text-left font-medium">
                      {change.field}
                    </th>
                    {/* Removed value struck through, new value in full: the shape of a diff. */}
                    <td className="px-3 py-1.5 text-muted line-through decoration-danger/50">{display(change.before)}</td>
                    <td className="px-3 py-1.5">{display(change.after)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {Object.keys(event.context ?? {}).length > 0 && (
        <section>
          <h4 className="mb-2 text-sm font-semibold">{t("common.details")}</h4>
          <pre className="overflow-x-auto rounded-card border border-line bg-subtle p-3 text-xs">{JSON.stringify(event.context, null, 2)}</pre>
        </section>
      )}
    </div>
  );
}
