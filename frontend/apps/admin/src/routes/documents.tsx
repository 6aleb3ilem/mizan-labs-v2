/**
 * Document templates and print profiles (SPEC §23.5, §18).
 *
 * Every document this platform issues is sealed, hashed and published to a transparency log, so
 * a template is not a cosmetic choice: the version that rendered a document is recorded with it
 * and has to stay reproducible forever. That shapes the whole screen.
 *
 * - Templates are versioned and approved. An approved version is never edited; changing it means
 *   a new draft version, which is what the editor offers.
 * - A draft is previewed as the real thing — the server renders an actual PDF through WeasyPrint
 *   with sample data — because HTML that looks right in a browser routinely paginates wrongly.
 * - Print profiles hold the paper defaults per document kind, separately from the template, so a
 *   branch can change its paper size without touching an approved layout.
 */
import { useApi } from "@mizan/api-client";
import { useSession } from "@mizan/app-kit";
import { currentLocale, formatDateTime, useTranslation } from "@mizan/i18n";
import {
  Alert,
  Badge,
  Button,
  ConfirmDialog,
  FormField,
  Input,
  PageHeader,
  Select,
  Textarea,
  useToast,
  type ColumnDef,
} from "@mizan/ui";
import { useNavigate, useParams } from "@tanstack/react-router";
import { CheckCircle2, FileText, Lock } from "lucide-react";
import { useEffect, useState } from "react";

import { ListPage, RecordDrawer, useList, useSave, textOf } from "../lib/resource";

type TemplateSummary = {
  id: string;
  branch_id: string | null;
  kind: string;
  locale: string;
  version: number;
  status: string;
  name: string;
  approved_at: string | null;
};

type Template = TemplateSummary & {
  html: string;
  css: string;
  variables: Record<string, unknown>;
  sample_data: Record<string, unknown>;
};

type PrintProfile = { id: string; branch_id: string; kind: string; defaults: Record<string, unknown> };
type Branch = { id: string; code: string; trade_name: string; legal_name: string };

const TEMPLATES_KEY = ["document-templates", "list", {}];

const DOCUMENT_KINDS = ["QUOTE", "ORDER", "CONTRACT", "REPORT", "INVOICE", "CREDIT_NOTE", "RECEIPT", "DELIVERY_NOTE", "HANDOVER_NOTE"];

function statusTone(status: string): "success" | "amber" | "slate" {
  return status === "ACTIVE" ? "success" : status === "DRAFT" ? "amber" : "slate";
}

export function TemplatesPage() {
  const { t } = useTranslation();
  const api = useApi();
  const session = useSession();
  const navigate = useNavigate();
  const locale = currentLocale();

  const templates = useList<TemplateSummary>(TEMPLATES_KEY, async () => (await api.client.GET("/document-templates")).data as TemplateSummary[] | undefined, {
    enabled: session.can("document_template", "view"),
  });

  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ kind: "REPORT", locale: "fr", name: "", html: "<article>\n  <h1>{{ document.title }}</h1>\n</article>", css: "" });
  const toast = useToast();

  const save = useSave(
    async () =>
      (await api.client.POST("/document-templates", {
        body: { kind: form.kind, locale: form.locale, name: form.name, html: form.html, css: form.css } as never,
      })).data,
    [TEMPLATES_KEY],
    (created) => {
      setOpen(false);
      toast.success(t("common.saved"));
      const id = (created as { id?: string } | undefined)?.id;
      // Straight into the editor: a template with no content is not a finished act.
      if (id) void navigate({ to: "/documents/templates/$templateId", params: { templateId: id } });
    },
  );

  const columns: ColumnDef<TemplateSummary, unknown>[] = [
    { id: "kind", header: t("numbering.kind"), accessorKey: "kind", cell: (c) => <span className="font-medium">{textOf(c.getValue())}</span> },
    { id: "name", header: t("common.name"), accessorKey: "name" },
    { id: "locale", header: t("common.locale"), accessorKey: "locale" },
    { id: "version", header: t("common.version"), accessorKey: "version", cell: (c) => <span className="tabular">v{textOf(c.getValue())}</span> },
    {
      id: "status",
      header: t("common.status"),
      accessorKey: "status",
      cell: (c) => (
        <span className="flex items-center gap-1.5">
          <Badge tone={statusTone(textOf(c.getValue()))}>{textOf(c.getValue())}</Badge>
          {c.row.original.status === "ACTIVE" && <Lock className="size-3.5 text-muted" aria-label={t("common.version")} />}
        </span>
      ),
    },
    {
      id: "approved_at",
      header: t("common.date"),
      accessorKey: "approved_at",
      cell: (c) => (c.getValue() ? <span className="tabular text-sm">{formatDateTime(String(c.getValue()), locale)}</span> : <span className="text-muted">—</span>),
    },
  ];

  return (
    <>
      <ListPage
        title={t("nav.admin.templates")}
        columns={columns}
        rows={templates.data}
        loading={templates.isPending}
        error={templates.error}
        onRetry={() => void templates.refetch()}
        getRowId={(row) => row.id}
        searchable={(row, needle) => `${row.kind} ${row.name}`.toLowerCase().includes(needle)}
        onRowClick={(row) => void navigate({ to: "/documents/templates/$templateId", params: { templateId: row.id } })}
        onCreate={() => setOpen(true)}
        canCreate={session.can("document_template", "configure")}
      />

      <RecordDrawer open={open} onOpenChange={setOpen} title={t("common.new")} onSubmit={() => save.mutate(undefined as never)} saving={save.isPending} width="max-w-2xl">
        <div className="grid grid-cols-2 gap-4">
          <FormField label={t("numbering.kind")} required error={save.fieldErrors["kind"]}>
            <Select value={form.kind} onValueChange={(value) => setForm({ ...form, kind: value })} options={DOCUMENT_KINDS.map((kind) => ({ value: kind, label: kind }))} />
          </FormField>
          <FormField label={t("common.locale")} required>
            <Select
              value={form.locale}
              onValueChange={(value) => setForm({ ...form, locale: value })}
              options={[
                { value: "fr", label: t("common.language_fr") },
                { value: "en", label: t("common.language_en") },
              ]}
            />
          </FormField>
        </div>
        <FormField label={t("common.name")} error={save.fieldErrors["name"]}>
          <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
        </FormField>
        <FormField label="html" required error={save.fieldErrors["html"]}>
          <Textarea value={form.html} onChange={(e) => setForm({ ...form, html: e.target.value })} rows={10} className="tabular" />
        </FormField>
      </RecordDrawer>
    </>
  );
}

/**
 * The template editor.
 *
 * An active template is read-only and offers a new draft version instead. The preview asks the
 * server for a real PDF and shows it in an object frame — the point is to see the pagination,
 * which no HTML preview in the console could tell the truth about.
 */
export function TemplatePage() {
  const { t } = useTranslation();
  const api = useApi();
  const session = useSession();
  const toast = useToast();
  const navigate = useNavigate();
  const params = useParams({ strict: false }) as { templateId: string };

  const detailKey = ["document-templates", "one", params.templateId];
  const template = useList<Template>(detailKey, async () => {
    const result = (await api.client.GET("/document-templates/{template_id}", { params: { path: { template_id: params.templateId } } })).data;
    return result ? [result as Template] : [];
  });
  const record = template.data?.[0];

  const [draft, setDraft] = useState<{ id: string; html: string; css: string; name: string } | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [approving, setApproving] = useState(false);

  // Blob URLs are a resource, not a string: each new preview must release the previous one.
  useEffect(() => () => {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
  }, [previewUrl]);

  const editable = record?.status === "DRAFT" && session.can("document_template", "configure");
  const current = draft?.id === params.templateId ? draft : { id: params.templateId, html: record?.html ?? "", css: record?.css ?? "", name: record?.name ?? "" };

  const newVersion = useSave(
    async () =>
      (await api.client.POST("/document-templates/{template_id}/versions", {
        params: { path: { template_id: params.templateId } },
        body: { html: record?.html, css: record?.css, name: record?.name } as never,
      })).data,
    [TEMPLATES_KEY],
    (created) => {
      const id = (created as { id?: string } | undefined)?.id;
      toast.success(t("common.saved"));
      if (id) void navigate({ to: "/documents/templates/$templateId", params: { templateId: id } });
    },
  );

  const approve = useSave(
    async () => (await api.client.POST("/document-templates/{template_id}:approve", { params: { path: { template_id: params.templateId } } })).data,
    [detailKey, TEMPLATES_KEY],
    () => {
      setApproving(false);
      toast.success(t("common.saved"));
    },
  );

  const preview = useSave(async () => {
    // The endpoint returns a PDF, so it bypasses the JSON client and goes through fetchBlob.
    const blob = await api.fetchBlob(`/document-templates/${params.templateId}:preview`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setPreviewUrl(URL.createObjectURL(blob));
    return blob;
  }, []);

  return (
    <div className="flex flex-col gap-4">
      <PageHeader
        title={record ? `${record.kind} · ${record.locale}` : params.templateId}
        subtitle={record?.name}
        badges={
          record && (
            <>
              <Badge tone={statusTone(record.status)}>{record.status}</Badge>
              <Badge tone="slate">v{record.version}</Badge>
            </>
          )
        }
        actions={
          <>
            <Button variant="outline" onClick={() => void navigate({ to: "/documents/templates" })}>
              {t("common.back")}
            </Button>
            <Button variant="outline" onClick={() => preview.mutate(undefined as never)} loading={preview.isPending} leftIcon={<FileText className="size-4" aria-hidden />}>
              {t("common.preview")}
            </Button>
            {record?.status === "ACTIVE" && session.can("document_template", "configure") && (
              <Button onClick={() => newVersion.mutate(undefined as never)} loading={newVersion.isPending}>
                {t("common.version")} +1
              </Button>
            )}
            {editable && (
              <Button onClick={() => setApproving(true)} leftIcon={<CheckCircle2 className="size-4" aria-hidden />}>
                {t("common.confirm")}
              </Button>
            )}
          </>
        }
      />

      {record?.status === "ACTIVE" && (
        <Alert tone="info">
          {t("numbering.superseded")} — v{record.version}
        </Alert>
      )}

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <div className="flex flex-col gap-4">
          <FormField label={t("common.name")}>
            <Input value={current.name} onChange={(e) => setDraft({ ...current, name: e.target.value })} disabled={!editable} />
          </FormField>
          <FormField label="html">
            <Textarea value={current.html} onChange={(e) => setDraft({ ...current, html: e.target.value })} rows={20} disabled={!editable} className="tabular" />
          </FormField>
          <FormField label="css">
            <Textarea value={current.css} onChange={(e) => setDraft({ ...current, css: e.target.value })} rows={10} disabled={!editable} className="tabular" />
          </FormField>
        </div>

        <div className="flex flex-col gap-2">
          <h3 className="text-sm font-semibold">{t("common.preview")}</h3>
          {previewUrl ? (
            // An <object> renders the real PDF, so pagination and page breaks are visible.
            <object data={previewUrl} type="application/pdf" className="h-[80vh] w-full rounded-card border border-line bg-surface" aria-label={t("common.preview")}>
              <a href={previewUrl} download>
                {t("common.download")}
              </a>
            </object>
          ) : (
            <div className="grid h-[80vh] place-items-center rounded-card border border-dashed border-line bg-subtle text-sm text-muted">
              {t("common.preview")}
            </div>
          )}
        </div>
      </div>

      <ConfirmDialog
        open={approving}
        onOpenChange={setApproving}
        title={t("common.confirm")}
        consequences={t("numbering.activate_consequences")}
        confirmLabel={t("common.confirm")}
        cancelLabel={t("common.cancel")}
        loading={approve.isPending}
        onConfirm={() => approve.mutate(undefined as never)}
      />
    </div>
  );
}

/* ------------------------------------------------------- print profiles */

export function PrintProfilesPage() {
  const { t } = useTranslation();
  const api = useApi();
  const session = useSession();
  const toast = useToast();
  const [branchFilter, setBranchFilter] = useState("");

  const branches = useList<Branch>(["branches", "list", {}], async () => (await api.client.GET("/branches")).data as Branch[] | undefined, {
    enabled: session.can("branch", "view"),
  });
  const listKey = ["print-profiles", "list", { branch: branchFilter }];
  const profiles = useList<PrintProfile>(listKey, async () =>
    (await api.client.GET("/print-profiles", { params: { query: branchFilter ? { branch_id: branchFilter } : {} } })).data as PrintProfile[] | undefined,
  );

  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ branch_id: "", kind: "REPORT", paper: "A4", margins: "20mm", copies: 1, duplex: false });

  const save = useSave(
    async () =>
      (await api.client.POST("/print-profiles", {
        body: {
          branch_id: form.branch_id,
          kind: form.kind,
          defaults: { paper: form.paper, margins: form.margins, copies: form.copies, duplex: form.duplex },
        } as never,
      })).data,
    [listKey],
    () => {
      setOpen(false);
      toast.success(t("common.saved"));
    },
  );

  const columns: ColumnDef<PrintProfile, unknown>[] = [
    { id: "kind", header: t("numbering.kind"), accessorKey: "kind", cell: (c) => <span className="font-medium">{textOf(c.getValue())}</span> },
    {
      id: "branch",
      header: t("common.branch"),
      accessorFn: (row) => branches.data?.find((b) => b.id === row.branch_id)?.trade_name ?? row.branch_id,
    },
    {
      id: "defaults",
      header: t("common.settings"),
      accessorFn: (row) => JSON.stringify(row.defaults ?? {}),
      cell: (c) => (
        <span className="flex flex-wrap gap-1">
          {Object.entries(c.row.original.defaults ?? {}).map(([key, value]) => (
            <Badge key={key} tone="slate">
              {key}: {String(value)}
            </Badge>
          ))}
        </span>
      ),
    },
  ];

  return (
    <>
      <ListPage
        title={t("nav.admin.print_profiles")}
        columns={columns}
        rows={profiles.data}
        loading={profiles.isPending}
        error={profiles.error}
        onRetry={() => void profiles.refetch()}
        getRowId={(row) => row.id}
        searchable={(row, needle) => row.kind.toLowerCase().includes(needle)}
        onRowClick={(row) => {
          const defaults = row.defaults ?? {};
          setForm({
            branch_id: row.branch_id,
            kind: row.kind,
            paper: String(defaults["paper"] ?? "A4"),
            margins: String(defaults["margins"] ?? "20mm"),
            copies: Number(defaults["copies"] ?? 1),
            duplex: Boolean(defaults["duplex"]),
          });
          setOpen(true);
        }}
        onCreate={() => {
          setForm({ branch_id: branchFilter || branches.data?.[0]?.id || "", kind: "REPORT", paper: "A4", margins: "20mm", copies: 1, duplex: false });
          setOpen(true);
        }}
        canCreate={session.can("document_template", "configure") && !!branches.data?.length}
        toolbar={
          <Select
            value={branchFilter}
            onValueChange={setBranchFilter}
            allowEmpty
            emptyLabel={t("common.all")}
            placeholder={t("common.branch")}
            className="w-56"
            options={(branches.data ?? []).map((b) => ({ value: b.id, label: b.trade_name || b.code }))}
          />
        }
      />

      <RecordDrawer open={open} onOpenChange={setOpen} title={t("nav.admin.print_profiles")} onSubmit={() => save.mutate(undefined as never)} saving={save.isPending}>
        <FormField label={t("common.branch")} required error={save.fieldErrors["branch_id"]}>
          <Select
            value={form.branch_id}
            onValueChange={(value) => setForm({ ...form, branch_id: value })}
            placeholder={t("common.select_placeholder")}
            options={(branches.data ?? []).map((b) => ({ value: b.id, label: b.trade_name || b.code }))}
          />
        </FormField>
        <FormField label={t("numbering.kind")} required error={save.fieldErrors["kind"]}>
          <Select value={form.kind} onValueChange={(value) => setForm({ ...form, kind: value })} options={DOCUMENT_KINDS.map((kind) => ({ value: kind, label: kind }))} />
        </FormField>
        <div className="grid grid-cols-3 gap-4">
          <FormField label="paper">
            <Select value={form.paper} onValueChange={(value) => setForm({ ...form, paper: value })} options={["A4", "A5", "LETTER"].map((value) => ({ value, label: value }))} />
          </FormField>
          <FormField label="margins">
            <Input value={form.margins} onChange={(e) => setForm({ ...form, margins: e.target.value })} className="tabular" />
          </FormField>
          <FormField label="copies">
            <Input type="number" min={1} value={String(form.copies)} onChange={(e) => setForm({ ...form, copies: Number(e.target.value) || 1 })} className="tabular" />
          </FormField>
        </div>
      </RecordDrawer>
    </>
  );
}
