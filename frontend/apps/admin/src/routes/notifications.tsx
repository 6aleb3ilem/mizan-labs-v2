/**
 * Notifications (SPEC §23.6, §19): rules, message templates, channels and the delivery log.
 *
 * A rule says "when this event happens, tell these people, on these channels, with this
 * template". Two things make that safe to configure without a release:
 *
 * - **Simulate before saving.** A rule is a dry run away from showing exactly who it would
 *   reach and what each of them would read, per channel and per locale. Sending the wrong
 *   message to a client cannot be undone, so the console asks the server to resolve the
 *   audience first.
 * - **Render before saving.** The template editor previews a draft against sample data, so a
 *   broken placeholder is caught in the editor instead of in a client's inbox.
 *
 * The delivery log is the answer to "did they get it?" — a failed delivery is re-queued from
 * there rather than by re-firing the event.
 */
import { useApi } from "@mizan/api-client";
import { usePagedQuery, useSession } from "@mizan/app-kit";
import { currentLocale, formatDateTime, useTranslation } from "@mizan/i18n";
import {
  Alert,
  Badge,
  Button,
  Card,
  Checkbox,
  Drawer,
  EmptyState,
  ErrorState,
  FormField,
  Input,
  PageHeader,
  Select,
  SkeletonRows,
  Switch,
  Textarea,
  useToast,
  type ColumnDef,
} from "@mizan/ui";
import { RefreshCw, Send } from "lucide-react";
import { useMemo, useState } from "react";

import { ListPage, RecordDrawer, useList, useSave, textOf } from "../lib/resource";

type Rule = {
  id: string;
  branch_id: string | null;
  code: string;
  event_code: string;
  audience: Record<string, unknown>;
  channels: string[];
  template_code: string;
  throttle: Record<string, unknown>;
  digest: Record<string, unknown>;
  respect_quiet_hours: boolean;
  active: boolean;
  description: string;
  row_version: number;
};

type Template = {
  id: string;
  code: string;
  locale: string;
  channel: string;
  subject: string;
  body: string;
  html: string;
  variables: Record<string, unknown>;
  active: boolean;
  row_version: number;
};

type Delivery = {
  id: string;
  rule_id: string | null;
  event_code: string;
  recipient: Record<string, unknown>;
  recipient_key: string;
  channel: string;
  locale: string;
  template_code: string;
  status: string;
  attempts: number;
  last_error: string;
  scheduled_for: string | null;
  sent_at: string | null;
  created_at: string;
};

type SimulatedDelivery = {
  recipient: Record<string, unknown>;
  channel: string;
  locale: string;
  status: string;
  reason: string;
  scheduled_for: string | null;
  rendered: Record<string, string>;
};

const CHANNELS = ["email", "sms", "whatsapp", "in_app"];
const STATUSES = ["PENDING", "SCHEDULED", "SENT", "FAILED", "SKIPPED"];

const RULES_KEY = ["notification-rules", "list", {}];
const TEMPLATES_KEY = ["message-templates", "list", {}];

function statusTone(status: string): "success" | "danger" | "amber" | "slate" | "teal" {
  if (status === "SENT") return "success";
  if (status === "FAILED") return "danger";
  if (status === "SCHEDULED") return "teal";
  if (status === "PENDING") return "amber";
  return "slate";
}

/** `{"roles": ["LAB_SUPERVISOR"]}` ⇄ `roles = LAB_SUPERVISOR, …`, one group per line. */
function audienceToLines(audience: Record<string, unknown>): string {
  return Object.entries(audience ?? {})
    .map(([key, value]) => `${key} = ${Array.isArray(value) ? value.join(", ") : String(value)}`)
    .join("\n");
}

/** Sample payloads are typed by hand, so invalid JSON is expected rather than exceptional. */
function parseJson(text: string): Record<string, unknown> | null {
  try {
    const value: unknown = JSON.parse(text.trim() || "{}");
    return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : null;
  } catch {
    return null;
  }
}

function linesToAudience(text: string): Record<string, string[]> {
  const result: Record<string, string[]> = {};
  for (const line of text.split("\n")) {
    const at = line.indexOf("=");
    if (at === -1) continue;
    const key = line.slice(0, at).trim();
    const values = line
      .slice(at + 1)
      .split(",")
      .map((value) => value.trim())
      .filter(Boolean);
    if (key) result[key] = values;
  }
  return result;
}

/* ------------------------------------------------------------------ rules */

export function NotificationRulesPage() {
  const { t } = useTranslation();
  const api = useApi();
  const session = useSession();
  const toast = useToast();

  const rules = useList<Rule>(RULES_KEY, async () => (await api.client.GET("/notification-rules")).data as Rule[] | undefined, {
    enabled: session.can("notification_rule", "view"),
  });
  const templates = useList<Template>(TEMPLATES_KEY, async () => (await api.client.GET("/message-templates")).data as Template[] | undefined, {
    enabled: session.can("notification_rule", "view"),
  });

  const [editing, setEditing] = useState<Rule | null>(null);
  const [open, setOpen] = useState(false);
  const [simulating, setSimulating] = useState<Rule | null>(null);
  const [form, setForm] = useState({
    code: "",
    event_code: "",
    channels: ["email"] as string[],
    template_code: "",
    audience: "",
    respect_quiet_hours: true,
    active: true,
    description: "",
  });

  const save = useSave(
    async () => {
      const body = {
        event_code: form.event_code,
        channels: form.channels,
        template_code: form.template_code,
        audience: linesToAudience(form.audience),
        respect_quiet_hours: form.respect_quiet_hours,
        active: form.active,
        description: form.description,
      };
      if (editing) {
        return (await api.client.PATCH("/notification-rules/{rule_id}", {
          params: { path: { rule_id: editing.id } },
          body: body as never,
        })).data;
      }
      return (await api.client.POST("/notification-rules", { body: { ...body, code: form.code } as never })).data;
    },
    [RULES_KEY],
    () => {
      setOpen(false);
      toast.success(t("common.saved"));
    },
  );

  // Template codes are what a rule points at, so the picker offers the ones that exist.
  const templateCodes = useMemo(() => [...new Set((templates.data ?? []).map((template) => template.code))].sort(), [templates.data]);

  const columns: ColumnDef<Rule, unknown>[] = [
    { id: "code", header: t("common.code"), accessorKey: "code", cell: (c) => <span className="font-medium tabular">{textOf(c.getValue())}</span> },
    { id: "event_code", header: "event", accessorKey: "event_code", cell: (c) => <code className="text-sm">{textOf(c.getValue())}</code> },
    {
      id: "channels",
      header: t("nav.admin.providers"),
      accessorFn: (row) => (row.channels ?? []).join(" "),
      cell: (c) => (
        <span className="flex flex-wrap gap-1">
          {(c.row.original.channels ?? []).map((channel) => (
            <Badge key={channel} tone="blue">
              {channel}
            </Badge>
          ))}
        </span>
      ),
    },
    { id: "template_code", header: t("nav.admin.message_templates"), accessorKey: "template_code" },
    {
      id: "audience",
      header: "audience",
      accessorFn: (row) => Object.keys(row.audience ?? {}).join(", "),
      cell: (c) => <span className="text-sm text-muted">{textOf(c.getValue()) || "—"}</span>,
    },
    {
      id: "active",
      header: t("common.status"),
      accessorKey: "active",
      cell: (c) => <Badge tone={c.getValue() ? "success" : "neutral"}>{c.getValue() ? t("common.active") : t("common.inactive")}</Badge>,
    },
    {
      id: "actions",
      header: "",
      enableSorting: false,
      cell: (c) => (
        <Button
          variant="ghost"
          size="sm"
          leftIcon={<Send className="size-3.5" aria-hidden />}
          onClick={(e) => {
            e.stopPropagation();
            setSimulating(c.row.original);
          }}
        >
          {t("common.preview")}
        </Button>
      ),
    },
  ];

  return (
    <>
      <ListPage
        title={t("nav.admin.rules")}
        columns={columns}
        rows={rules.data}
        loading={rules.isPending}
        error={rules.error}
        onRetry={() => void rules.refetch()}
        getRowId={(row) => row.id}
        searchable={(row, needle) => `${row.code} ${row.event_code} ${row.template_code}`.toLowerCase().includes(needle)}
        onRowClick={(row) => {
          setEditing(row);
          setForm({
            code: row.code,
            event_code: row.event_code,
            channels: row.channels ?? [],
            template_code: row.template_code,
            audience: audienceToLines(row.audience),
            respect_quiet_hours: row.respect_quiet_hours,
            active: row.active,
            description: row.description,
          });
          setOpen(true);
        }}
        onCreate={() => {
          setEditing(null);
          setForm({ code: "", event_code: "", channels: ["email"], template_code: templateCodes[0] ?? "", audience: "roles = ", respect_quiet_hours: true, active: true, description: "" });
          setOpen(true);
        }}
        canCreate={session.can("notification_rule", "configure")}
      />

      <RecordDrawer
        open={open}
        onOpenChange={setOpen}
        title={editing ? `${editing.code} — ${t("common.edit")}` : t("common.new")}
        onSubmit={() => save.mutate(undefined as never)}
        saving={save.isPending}
        width="max-w-2xl"
      >
        <FormField label={t("common.code")} required error={save.fieldErrors["code"]}>
          <Input value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value.toUpperCase() })} disabled={!!editing} />
        </FormField>
        <FormField label="event_code" required error={save.fieldErrors["event_code"]} help="quote.issued, report.validated…">
          <Input value={form.event_code} onChange={(e) => setForm({ ...form, event_code: e.target.value })} className="tabular" />
        </FormField>
        <FormField label={t("nav.admin.providers")} required error={save.fieldErrors["channels"]}>
          <div className="flex flex-wrap gap-3">
            {CHANNELS.map((channel) => (
              <Checkbox
                key={channel}
                checked={form.channels.includes(channel)}
                onCheckedChange={(checked) =>
                  setForm({ ...form, channels: checked ? [...form.channels, channel] : form.channels.filter((c) => c !== channel) })
                }
                label={channel}
              />
            ))}
          </div>
        </FormField>
        <FormField label={t("nav.admin.message_templates")} required error={save.fieldErrors["template_code"]}>
          <Select
            value={form.template_code}
            onValueChange={(value) => setForm({ ...form, template_code: value })}
            placeholder={t("common.select_placeholder")}
            options={templateCodes.map((code) => ({ value: code, label: code }))}
          />
        </FormField>
        <FormField label="audience" help="roles = ..., contact_roles = ..., user_ids = ..." error={save.fieldErrors["audience"]}>
          <Textarea value={form.audience} onChange={(e) => setForm({ ...form, audience: e.target.value })} rows={4} className="tabular" />
        </FormField>
        <FormField label={t("common.description")}>
          <Textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} rows={2} />
        </FormField>
        <div className="grid grid-cols-2 gap-4">
          <FormField label="quiet hours">
            <Switch
              checked={form.respect_quiet_hours}
              onCheckedChange={(checked) => setForm({ ...form, respect_quiet_hours: checked })}
              label={form.respect_quiet_hours ? t("common.yes") : t("common.no")}
            />
          </FormField>
          <FormField label={t("common.status")}>
            <Switch checked={form.active} onCheckedChange={(checked) => setForm({ ...form, active: checked })} label={form.active ? t("common.active") : t("common.inactive")} />
          </FormField>
        </div>
      </RecordDrawer>

      <SimulateDrawer rule={simulating} onClose={() => setSimulating(null)} />
    </>
  );
}

/**
 * The dry run.
 *
 * It resolves the real audience against a sample payload and renders each message, without
 * queueing anything. Recipients that would be skipped are shown with the reason — an empty
 * result is the most valuable outcome this screen produces, because a rule that reaches nobody
 * looks identical to a working one until the day it matters.
 */
function SimulateDrawer({ rule, onClose }: { rule: Rule | null; onClose: () => void }) {
  const { t } = useTranslation();
  const api = useApi();
  const [payload, setPayload] = useState("{}");
  const [result, setResult] = useState<SimulatedDelivery[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const simulate = useSave(
    async () => {
      const parsed = parseJson(payload);
      if (!parsed) {
        setError("JSON");
        return undefined;
      }
      setError(null);
      const response = await api.client.POST("/notification-rules/{rule_id}:simulate", {
        params: { path: { rule_id: rule!.id } },
        body: { payload: parsed } as never,
      });
      setResult((response.data ?? []) as SimulatedDelivery[]);
      return response.data;
    },
    [],
  );

  return (
    <Drawer
      open={!!rule}
      onOpenChange={(next) => {
        if (!next) {
          setResult(null);
          onClose();
        }
      }}
      title={`${t("common.preview")} — ${rule?.code ?? ""}`}
      description={rule?.event_code}
      width="max-w-2xl"
      closeLabel={t("common.close")}
      footer={
        <Button onClick={() => simulate.mutate(undefined as never)} loading={simulate.isPending} leftIcon={<Send className="size-4" aria-hidden />}>
          {t("common.preview")}
        </Button>
      }
    >
      <div className="flex flex-col gap-4">
        <FormField label="payload" help="Sample event payload" error={error ? "JSON" : undefined}>
          <Textarea value={payload} onChange={(e) => setPayload(e.target.value)} rows={6} className="tabular" />
        </FormField>

        {result !== null && result.length === 0 && <Alert tone="warning">{t("common.empty_title")}</Alert>}

        {result?.map((delivery, index) => (
          <Card key={index} title={`${delivery.channel} · ${delivery.locale}`}>
            <div className="flex flex-col gap-2">
              <div className="flex flex-wrap items-center gap-2">
                <Badge tone={statusTone(delivery.status)}>{delivery.status}</Badge>
                {delivery.reason && <span className="text-sm text-muted">{delivery.reason}</span>}
                {delivery.scheduled_for && <span className="tabular text-sm text-muted">{formatDateTime(delivery.scheduled_for, currentLocale())}</span>}
              </div>
              <p className="text-sm text-muted">{JSON.stringify(delivery.recipient)}</p>
              {delivery.rendered?.["subject"] && <p className="font-medium">{delivery.rendered["subject"]}</p>}
              {delivery.rendered?.["body"] && <p className="whitespace-pre-wrap text-sm">{delivery.rendered["body"]}</p>}
            </div>
          </Card>
        ))}
      </div>
    </Drawer>
  );
}

/* -------------------------------------------------------------- templates */

export function MessageTemplatesPage() {
  const { t } = useTranslation();
  const api = useApi();
  const session = useSession();
  const toast = useToast();

  const templates = useList<Template>(TEMPLATES_KEY, async () => (await api.client.GET("/message-templates")).data as Template[] | undefined, {
    enabled: session.can("notification_rule", "view"),
  });

  const [editing, setEditing] = useState<Template | null>(null);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ code: "", locale: "fr", channel: "email", subject: "", body: "", html: "", sample: "{}", active: true });
  const [preview, setPreview] = useState<{ subject: string; body: string; html: string } | null>(null);

  const save = useSave(
    async () => {
      const sample = parseJson(form.sample) ?? {};
      if (editing) {
        return (await api.client.PATCH("/message-templates/{template_id}", {
          params: { path: { template_id: editing.id } },
          body: { subject: form.subject, body: form.body, html: form.html, active: form.active, sample } as never,
        })).data;
      }
      return (await api.client.POST("/message-templates", {
        body: { code: form.code, locale: form.locale, channel: form.channel, subject: form.subject, body: form.body, html: form.html, sample } as never,
      })).data;
    },
    [TEMPLATES_KEY],
    () => {
      setOpen(false);
      toast.success(t("common.saved"));
    },
  );

  const render = useSave(async () => {
    const sample = parseJson(form.sample) ?? {};
    const response = await api.client.POST("/message-templates:preview", {
      body: { subject: form.subject, body: form.body, html: form.html, channel: form.channel, sample } as never,
    });
    setPreview((response.data ?? null) as { subject: string; body: string; html: string } | null);
    return response.data;
  }, []);

  const columns: ColumnDef<Template, unknown>[] = [
    { id: "code", header: t("common.code"), accessorKey: "code", cell: (c) => <span className="font-medium tabular">{textOf(c.getValue())}</span> },
    { id: "channel", header: t("nav.admin.providers"), accessorKey: "channel", cell: (c) => <Badge tone="blue">{textOf(c.getValue())}</Badge> },
    { id: "locale", header: t("common.locale"), accessorKey: "locale" },
    { id: "subject", header: "subject", accessorKey: "subject" },
    {
      id: "active",
      header: t("common.status"),
      accessorKey: "active",
      cell: (c) => <Badge tone={c.getValue() ? "success" : "neutral"}>{c.getValue() ? t("common.active") : t("common.inactive")}</Badge>,
    },
  ];

  return (
    <>
      <ListPage
        title={t("nav.admin.message_templates")}
        columns={columns}
        rows={templates.data}
        loading={templates.isPending}
        error={templates.error}
        onRetry={() => void templates.refetch()}
        getRowId={(row) => row.id}
        searchable={(row, needle) => `${row.code} ${row.subject} ${row.channel}`.toLowerCase().includes(needle)}
        onRowClick={(row) => {
          setEditing(row);
          setPreview(null);
          setForm({ code: row.code, locale: row.locale, channel: row.channel, subject: row.subject, body: row.body, html: row.html, sample: "{}", active: row.active });
          setOpen(true);
        }}
        onCreate={() => {
          setEditing(null);
          setPreview(null);
          setForm({ code: "", locale: "fr", channel: "email", subject: "", body: "", html: "", sample: "{}", active: true });
          setOpen(true);
        }}
        canCreate={session.can("notification_rule", "configure")}
      />

      <RecordDrawer
        open={open}
        onOpenChange={setOpen}
        title={editing ? `${editing.code} · ${editing.locale}` : t("common.new")}
        onSubmit={() => save.mutate(undefined as never)}
        saving={save.isPending}
        width="max-w-3xl"
        extraActions={
          <Button variant="outline" onClick={() => render.mutate(undefined as never)} loading={render.isPending}>
            {t("common.preview")}
          </Button>
        }
      >
        <div className="grid grid-cols-3 gap-4">
          <FormField label={t("common.code")} required error={save.fieldErrors["code"]}>
            <Input value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value.toUpperCase() })} disabled={!!editing} />
          </FormField>
          <FormField label={t("nav.admin.providers")} required>
            <Select value={form.channel} onValueChange={(value) => setForm({ ...form, channel: value })} disabled={!!editing} options={CHANNELS.map((channel) => ({ value: channel, label: channel }))} />
          </FormField>
          <FormField label={t("common.locale")} required>
            <Select
              value={form.locale}
              onValueChange={(value) => setForm({ ...form, locale: value })}
              disabled={!!editing}
              options={[
                { value: "fr", label: t("common.language_fr") },
                { value: "en", label: t("common.language_en") },
              ]}
            />
          </FormField>
        </div>
        {/* SMS and WhatsApp have no subject line; offering one invites a message that loses it. */}
        {form.channel === "email" && (
          <FormField label="subject" error={save.fieldErrors["subject"]}>
            <Input value={form.subject} onChange={(e) => setForm({ ...form, subject: e.target.value })} />
          </FormField>
        )}
        <FormField label="body" required error={save.fieldErrors["body"]} help="{{ variable }}">
          <Textarea value={form.body} onChange={(e) => setForm({ ...form, body: e.target.value })} rows={8} className="tabular" />
        </FormField>
        {form.channel === "email" && (
          <FormField label="html" optionalLabel={t("common.optional")}>
            <Textarea value={form.html} onChange={(e) => setForm({ ...form, html: e.target.value })} rows={6} className="tabular" />
          </FormField>
        )}
        <FormField label="sample" help="JSON">
          <Textarea value={form.sample} onChange={(e) => setForm({ ...form, sample: e.target.value })} rows={4} className="tabular" />
        </FormField>

        {preview && (
          <Card title={t("common.preview")}>
            <div className="flex flex-col gap-2">
              {preview.subject && <p className="font-medium">{preview.subject}</p>}
              <p className="whitespace-pre-wrap text-sm">{preview.body}</p>
            </div>
          </Card>
        )}

        {editing && (
          <FormField label={t("common.status")}>
            <Switch checked={form.active} onCheckedChange={(checked) => setForm({ ...form, active: checked })} label={form.active ? t("common.active") : t("common.inactive")} />
          </FormField>
        )}
      </RecordDrawer>
    </>
  );
}

/* ----------------------------------------------------------- delivery log */

export function DeliveryLogPage() {
  const { t } = useTranslation();
  const api = useApi();
  const session = useSession();
  const toast = useToast();
  const locale = currentLocale();

  const [status, setStatus] = useState("");
  const [channel, setChannel] = useState("");
  const [selected, setSelected] = useState<Delivery | null>(null);

  const deliveries = usePagedQuery<Delivery>(
    ["notification-deliveries", { status, channel }],
    async (client, after) =>
      (await client.client.GET("/notification-deliveries", {
        params: { query: { ...(status ? { status } : {}), ...(channel ? { channel } : {}), ...(after ? { after } : {}), limit: 50 } as never },
      })).data as never,
    { enabled: session.can("notification_rule", "view") },
  );

  const retry = useSave(
    async (delivery: Delivery) => (await api.client.POST("/notification-deliveries/{delivery_id}:retry", { params: { path: { delivery_id: delivery.id } } })).data,
    [["notification-deliveries"]],
    () => {
      setSelected(null);
      toast.success(t("common.saved"));
    },
  );

  const failures = useMemo(() => deliveries.items.filter((delivery) => delivery.status === "FAILED").length, [deliveries.items]);

  return (
    <div className="flex flex-col gap-4">
      <PageHeader
        title={t("nav.admin.log")}
        badges={failures > 0 ? <Badge tone="danger">{t("common.results", { count: failures })}</Badge> : undefined}
      />

      <div className="flex flex-wrap items-center gap-3">
        <Select value={status} onValueChange={setStatus} allowEmpty emptyLabel={t("common.all")} placeholder={t("common.status")} className="w-44" options={STATUSES.map((value) => ({ value, label: value }))} aria-label={t("common.status")} />
        <Select value={channel} onValueChange={setChannel} allowEmpty emptyLabel={t("common.all")} placeholder={t("nav.admin.providers")} className="w-44" options={CHANNELS.map((value) => ({ value, label: value }))} aria-label={t("nav.admin.providers")} />
        <span className="ml-auto text-sm text-muted">{t("common.results", { count: deliveries.items.length })}</span>
      </div>

      {deliveries.error ? (
        <ErrorState title={t("common.error_title")} onRetry={deliveries.refetch} retryLabel={t("common.retry")} />
      ) : deliveries.loading && deliveries.items.length === 0 ? (
        <div className="rounded-card border border-line bg-surface">
          <SkeletonRows rows={8} columns={5} />
        </div>
      ) : deliveries.items.length === 0 ? (
        <EmptyState title={t("common.empty_title")} hint={t("common.empty_hint")} kind="search" />
      ) : (
        <div className="overflow-hidden rounded-card border border-line bg-surface">
          <ul className="divide-y divide-line">
            {deliveries.items.map((delivery) => (
              <li key={delivery.id}>
                <button type="button" onClick={() => setSelected(delivery)} className="flex w-full items-center gap-3 px-3 py-2.5 text-left hover-colors hover:bg-subtle">
                  <span className="tabular w-40 shrink-0 text-sm text-muted">{formatDateTime(delivery.sent_at ?? delivery.created_at, locale)}</span>
                  <Badge tone={statusTone(delivery.status)}>{delivery.status}</Badge>
                  <Badge tone="blue">{delivery.channel}</Badge>
                  <span className="truncate font-medium">{delivery.recipient_key}</span>
                  <span className="truncate text-sm text-muted">{delivery.event_code}</span>
                  {delivery.attempts > 1 && <span className="tabular ml-auto shrink-0 text-xs text-muted">×{delivery.attempts}</span>}
                </button>
              </li>
            ))}
          </ul>
          {deliveries.hasMore && (
            <div className="border-t border-line p-3 text-center">
              <Button variant="outline" onClick={deliveries.loadMore} loading={deliveries.loading}>
                {t("common.load_more")}
              </Button>
            </div>
          )}
        </div>
      )}

      <Drawer
        open={!!selected}
        onOpenChange={(next) => !next && setSelected(null)}
        title={selected ? `${selected.channel} · ${selected.recipient_key}` : ""}
        description={selected?.event_code}
        closeLabel={t("common.close")}
        footer={
          selected &&
          (selected.status === "FAILED" || selected.status === "SKIPPED") &&
          session.can("notification_rule", "configure") && (
            <Button onClick={() => retry.mutate(selected)} loading={retry.isPending} leftIcon={<RefreshCw className="size-4" aria-hidden />}>
              {t("common.retry")}
            </Button>
          )
        }
      >
        {selected && (
          <div className="flex flex-col gap-4">
            <div className="flex flex-wrap items-center gap-2">
              <Badge tone={statusTone(selected.status)}>{selected.status}</Badge>
              <span className="tabular text-sm text-muted">{selected.attempts} ×</span>
              <span className="text-sm text-muted">{selected.template_code}</span>
            </div>
            {selected.last_error && <Alert tone="danger">{selected.last_error}</Alert>}
            <div>
              <h4 className="mb-1 text-sm font-semibold">recipient</h4>
              <pre className="overflow-x-auto rounded-card border border-line bg-subtle p-3 text-xs">{JSON.stringify(selected.recipient, null, 2)}</pre>
            </div>
          </div>
        )}
      </Drawer>
    </div>
  );
}

/* --------------------------------------------------------------- channels */

/**
 * Channel configuration is deployment-level (SMTP host, SMS aggregator credentials, WhatsApp
 * sender), held in secrets rather than in tenant configuration, so this screen reports what the
 * server actually has available rather than pretending to edit it.
 */
export function ProvidersPage() {
  const { t } = useTranslation();
  const api = useApi();
  const session = useSession();

  const deliveries = useList<Delivery>(
    ["notification-deliveries", "recent"],
    async () => (await api.client.GET("/notification-deliveries", { params: { query: { limit: 200 } } })).data?.items as Delivery[] | undefined,
    { enabled: session.can("notification_rule", "view") },
  );

  /* Health per channel, read off the recent log: the only honest signal the console has about a
     channel it does not configure. */
  const health = useMemo(() => {
    const rows = CHANNELS.map((channel) => {
      const own = (deliveries.data ?? []).filter((delivery) => delivery.channel === channel);
      const failed = own.filter((delivery) => delivery.status === "FAILED").length;
      const sent = own.filter((delivery) => delivery.status === "SENT").length;
      return { channel, total: own.length, sent, failed, lastError: own.find((delivery) => delivery.last_error)?.last_error ?? "" };
    });
    return rows;
  }, [deliveries.data]);

  return (
    <div className="flex flex-col gap-4">
      <PageHeader title={t("nav.admin.providers")} subtitle={t("audit.hint")} />
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {health.map((row) => (
          <Card key={row.channel} title={row.channel}>
            <div className="flex flex-col gap-2">
              <div className="flex items-center gap-3">
                <Badge tone={row.failed > 0 ? "danger" : row.sent > 0 ? "success" : "neutral"}>
                  {row.failed > 0 ? "FAILED" : row.sent > 0 ? "SENT" : "—"}
                </Badge>
                <span className="tabular text-sm text-muted">
                  {row.sent} / {row.total}
                </span>
              </div>
              {row.lastError && <p className="text-sm text-danger">{row.lastError}</p>}
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
