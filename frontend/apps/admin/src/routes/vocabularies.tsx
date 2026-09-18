/**
 * Vocabularies (SPEC §23.3, §10.2).
 *
 * The value lists behind every dropdown in the product. An administrator adds a sample nature or
 * a payment method here and it appears in the forms without a release — that is the whole point
 * of the configuration tier.
 *
 * A code is an identity, not a label: once an entry is in use, records point at it and changing
 * it would silently re-file them. So the code is fixed after creation and only the labels,
 * colour, icon and ordering stay editable. Entries are deactivated rather than deleted, which
 * keeps historical records readable.
 */
import { useApi } from "@mizan/api-client";
import { useSession } from "@mizan/app-kit";
import { useTranslation } from "@mizan/i18n";
import { Badge, FormField, Input, LabelsInput, Select, Switch, useToast, type ColumnDef } from "@mizan/ui";
import { useNavigate, useParams } from "@tanstack/react-router";
import { useState } from "react";

import { ListPage, RecordDrawer, useList, useSave, textOf } from "../lib/resource";

type Entry = {
  id: string;
  kind: string;
  branch_id: string | null;
  code: string;
  labels: Record<string, string>;
  colour: string;
  icon: string;
  ord: number;
  active: boolean;
  extra: Record<string, unknown>;
};

const HUES = ["slate", "gray", "red", "orange", "amber", "green", "teal", "blue", "indigo", "violet", "pink", "brown"];

export function VocabulariesPage() {
  const { t } = useTranslation();
  const api = useApi();
  const session = useSession();
  const toast = useToast();
  const navigate = useNavigate();
  const params = useParams({ strict: false }) as { kind?: string };

  const kinds = useList<string>(["vocabularies", "kinds"], async () => (await api.client.GET("/vocabularies/kinds")).data as string[] | undefined, {
    enabled: session.can("vocabulary", "view"),
  });
  // The route carries the kind so a vocabulary can be linked to and reloaded straight into.
  const kind = params.kind ?? kinds.data?.[0] ?? "";

  const listKey = ["vocabularies", kind, "entries"];
  const entries = useList<Entry>(
    listKey,
    async () => (await api.client.GET("/vocabularies/{kind}/entries", { params: { path: { kind } } })).data as Entry[] | undefined,
    { enabled: !!kind },
  );

  const [editing, setEditing] = useState<Entry | null>(null);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ code: "", labels: { fr: "", en: "" }, colour: "", icon: "", ord: 0, active: true });

  const save = useSave(
    async () => {
      if (editing) {
        return (await api.client.PATCH("/vocabularies/{kind}/entries/{entry_id}", {
          params: { path: { kind, entry_id: editing.id } },
          body: { labels: form.labels, colour: form.colour, icon: form.icon, ord: form.ord } as never,
        })).data;
      }
      return (await api.client.POST("/vocabularies/{kind}/entries", {
        params: { path: { kind } },
        body: { code: form.code, labels: form.labels, colour: form.colour, icon: form.icon, ord: form.ord } as never,
      })).data;
    },
    [listKey],
    () => {
      setOpen(false);
      toast.success(t("common.saved"));
    },
  );

  const columns: ColumnDef<Entry, unknown>[] = [
    { id: "ord", header: t("org.order"), accessorKey: "ord", cell: (c) => <span className="tabular text-muted">{textOf(c.getValue())}</span> },
    { id: "code", header: t("common.code"), accessorKey: "code", cell: (c) => <span className="font-medium tabular">{textOf(c.getValue())}</span> },
    { id: "label_fr", header: t("common.language_fr"), accessorFn: (row) => row.labels?.["fr"] ?? "" },
    { id: "label_en", header: t("common.language_en"), accessorFn: (row) => row.labels?.["en"] ?? "" },
    {
      id: "colour",
      header: t("org.colour"),
      accessorKey: "colour",
      cell: (c) => (c.getValue() ? <Badge tone={textOf(c.getValue()) as never}>{textOf(c.getValue())}</Badge> : <span className="text-muted">—</span>),
    },
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
        title={t("nav.admin.vocabularies")}
        subtitle={t("vocab.hint")}
        columns={columns}
        rows={entries.data}
        loading={entries.isPending || kinds.isPending}
        error={entries.error ?? kinds.error}
        onRetry={() => void entries.refetch()}
        getRowId={(row) => row.id}
        searchable={(row, needle) => `${row.code} ${Object.values(row.labels ?? {}).join(" ")}`.toLowerCase().includes(needle)}
        onRowClick={(row) => {
          setEditing(row);
          setForm({
            code: row.code,
            labels: { fr: row.labels?.["fr"] ?? "", en: row.labels?.["en"] ?? "" },
            colour: row.colour,
            icon: row.icon,
            ord: row.ord,
            active: row.active,
          });
          setOpen(true);
        }}
        onCreate={() => {
          setEditing(null);
          // Append at the end: the next multiple of ten leaves room to reorder without a renumber.
          const next = Math.max(0, ...(entries.data ?? []).map((entry) => entry.ord)) + 10;
          setForm({ code: "", labels: { fr: "", en: "" }, colour: "", icon: "", ord: next, active: true });
          setOpen(true);
        }}
        canCreate={session.can("vocabulary", "configure") && !!kind}
        toolbar={
          <Select
            value={kind}
            onValueChange={(next) => void navigate({ to: "/vocabularies/$kind", params: { kind: next } })}
            placeholder={t("vocab.kind")}
            className="w-64"
            options={(kinds.data ?? []).map((value) => ({ value, label: value }))}
            aria-label={t("vocab.kind")}
          />
        }
      />

      <RecordDrawer
        open={open}
        onOpenChange={setOpen}
        title={editing ? `${editing.code} — ${t("common.edit")}` : `${kind} — ${t("common.new")}`}
        onSubmit={() => save.mutate(undefined as never)}
        saving={save.isPending}
      >
        <FormField
          label={t("common.code")}
          required
          error={save.fieldErrors["code"]}
          help={editing ? t("vocab.system_hint") : undefined}
        >
          <Input value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value.toUpperCase() })} disabled={!!editing} />
        </FormField>
        <FormField label={t("common.labels")} required error={save.fieldErrors["labels"]}>
          <LabelsInput value={form.labels} onChange={(labels) => setForm({ ...form, labels: { fr: labels.fr ?? "", en: labels.en ?? "" } })} />
        </FormField>
        <div className="grid grid-cols-2 gap-4">
          <FormField label={t("org.colour")} optionalLabel={t("common.optional")}>
            <Select
              value={form.colour}
              onValueChange={(value) => setForm({ ...form, colour: value })}
              allowEmpty
              emptyLabel={t("common.none")}
              options={HUES.map((hue) => ({ value: hue, label: <Badge tone={hue as never}>{hue}</Badge> }))}
            />
          </FormField>
          <FormField label={t("org.order")}>
            <Input type="number" value={String(form.ord)} onChange={(e) => setForm({ ...form, ord: Number(e.target.value) || 0 })} className="tabular" />
          </FormField>
        </div>
        {editing && (
          <FormField label={t("common.status")}>
            <Switch checked={form.active} onCheckedChange={(checked) => setForm({ ...form, active: checked })} label={form.active ? t("common.active") : t("common.inactive")} />
          </FormField>
        )}
      </RecordDrawer>
    </>
  );
}
