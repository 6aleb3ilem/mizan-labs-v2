/**
 * Payment terms templates (SPEC §23.3, §10.5).
 *
 * A template is a set of milestones — "40 % on acceptance, 60 % on report" — that a quote later
 * turns into dated instalments. Two invariants drive the editor:
 *
 * - **The percentages must reach 100.** A template that sums to 95 % quietly under-invoices
 *   every order that uses it, so the running total is shown as it is edited and the form refuses
 *   to save until it balances.
 * - **Every milestone needs a trigger.** "When is this due?" is what turns a percentage into a
 *   date, and a milestone without one can never fall due.
 *
 * Exactly one template per branch is the default. Setting a new one clears the old, so it is a
 * separate action rather than a checkbox that silently demotes another record.
 */
import { useApi } from "@mizan/api-client";
import { useSession } from "@mizan/app-kit";
import { useTranslation } from "@mizan/i18n";
import {
  Alert,
  Badge,
  Button,
  FormField,
  Input,
  LabelsInput,
  Select,
  Switch,
  useToast,
  type ColumnDef,
} from "@mizan/ui";
import { Plus, Star, Trash2 } from "lucide-react";
import { useState } from "react";

import { ListPage, RecordDrawer, useList, useSave, textOf } from "../lib/resource";

type Milestone = {
  order: number;
  label: Record<string, string>;
  percent: string | number | null;
  amount: string | number | null;
  trigger: string;
  trigger_params: Record<string, unknown>;
  due_days_after_trigger: number;
};

type Template = {
  id: string;
  branch_id: string;
  code: string;
  labels: Record<string, string>;
  is_default: boolean;
  active: boolean;
  milestones: Milestone[];
};

type Branch = { id: string; code: string; trade_name: string; legal_name: string };

const TRIGGERS = ["ON_ACCEPTANCE", "ON_DELIVERY", "ON_REPORT", "ON_DATE", "ON_PHASE", "MANUAL"];
const LIST_KEY = ["payment-terms-templates", "list", {}];

function emptyMilestone(order: number): Milestone {
  return { order, label: { fr: "", en: "" }, percent: 0, amount: null, trigger: "ON_ACCEPTANCE", trigger_params: {}, due_days_after_trigger: 0 };
}

function totalPercent(milestones: Milestone[]): number {
  return milestones.reduce((sum, milestone) => sum + Number(milestone.percent ?? 0), 0);
}

export function PaymentTermsPage() {
  const { t } = useTranslation();
  const api = useApi();
  const session = useSession();
  const toast = useToast();

  const branches = useList<Branch>(["branches", "list", {}], async () => (await api.client.GET("/branches")).data as Branch[] | undefined, {
    enabled: session.can("branch", "view"),
  });
  const templates = useList<Template>(LIST_KEY, async () => (await api.client.GET("/payment-terms-templates")).data as Template[] | undefined, {
    enabled: session.can("payment_terms_template", "view"),
  });

  const [editing, setEditing] = useState<Template | null>(null);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ branch_id: "", code: "", labels: { fr: "", en: "" }, active: true, milestones: [emptyMilestone(1)] });

  const save = useSave(
    async () => {
      const milestones = form.milestones.map((milestone, index) => ({
        ...milestone,
        order: index + 1,
        percent: Number(milestone.percent ?? 0),
        amount: null,
      }));
      if (editing) {
        return (await api.client.PATCH("/payment-terms-templates/{template_id}", {
          params: { path: { template_id: editing.id } },
          body: { labels: form.labels, active: form.active, milestones } as never,
        })).data;
      }
      return (await api.client.POST("/payment-terms-templates", {
        body: { branch_id: form.branch_id, code: form.code, labels: form.labels, milestones } as never,
      })).data;
    },
    [LIST_KEY],
    () => {
      setOpen(false);
      toast.success(t("common.saved"));
    },
  );

  const setDefault = useSave(
    async (template: Template) =>
      (await api.client.POST("/payment-terms-templates/{template_id}:set-default", { params: { path: { template_id: template.id } } })).data,
    [LIST_KEY],
    () => toast.success(t("common.saved")),
  );

  const columns: ColumnDef<Template, unknown>[] = [
    { id: "code", header: t("common.code"), accessorKey: "code", cell: (c) => <span className="font-medium tabular">{textOf(c.getValue())}</span> },
    { id: "label", header: t("common.label"), accessorFn: (row) => row.labels?.["fr"] ?? row.labels?.["en"] ?? "" },
    {
      id: "branch",
      header: t("common.branch"),
      accessorFn: (row) => branches.data?.find((b) => b.id === row.branch_id)?.trade_name ?? row.branch_id,
    },
    {
      id: "milestones",
      header: t("common.total"),
      accessorFn: (row) => totalPercent(row.milestones ?? []),
      cell: (c) => {
        const total = Number(c.getValue());
        return (
          <span className="flex items-center gap-2">
            <span className="tabular">{(c.row.original.milestones ?? []).length} ×</span>
            {/* 100 is the only correct total; anything else is a template that under-invoices. */}
            <Badge tone={total === 100 ? "success" : "danger"}>{total} %</Badge>
          </span>
        );
      },
    },
    {
      id: "is_default",
      header: "",
      enableSorting: false,
      cell: (c) =>
        c.row.original.is_default ? (
          <Badge tone="primary">{t("common.yes")}</Badge>
        ) : session.can("payment_terms_template", "configure") ? (
          <Button
            variant="ghost"
            size="sm"
            leftIcon={<Star className="size-3.5" aria-hidden />}
            loading={setDefault.isPending}
            onClick={(e) => {
              e.stopPropagation();
              setDefault.mutate(c.row.original);
            }}
          >
            {t("common.confirm")}
          </Button>
        ) : null,
    },
    {
      id: "active",
      header: t("common.status"),
      accessorKey: "active",
      cell: (c) => <Badge tone={c.getValue() ? "success" : "neutral"}>{c.getValue() ? t("common.active") : t("common.inactive")}</Badge>,
    },
  ];

  const total = totalPercent(form.milestones);
  const balanced = Math.abs(total - 100) < 0.001;

  const updateMilestone = (index: number, patch: Partial<Milestone>) =>
    setForm({ ...form, milestones: form.milestones.map((milestone, i) => (i === index ? { ...milestone, ...patch } : milestone)) });

  return (
    <>
      <ListPage
        title={t("nav.admin.payment_terms")}
        columns={columns}
        rows={templates.data}
        loading={templates.isPending}
        error={templates.error}
        onRetry={() => void templates.refetch()}
        getRowId={(row) => row.id}
        searchable={(row, needle) => `${row.code} ${Object.values(row.labels ?? {}).join(" ")}`.toLowerCase().includes(needle)}
        onRowClick={(row) => {
          setEditing(row);
          setForm({
            branch_id: row.branch_id,
            code: row.code,
            labels: { fr: row.labels?.["fr"] ?? "", en: row.labels?.["en"] ?? "" },
            active: row.active,
            milestones: (row.milestones ?? []).map((milestone, index) => ({ ...milestone, order: index + 1 })),
          });
          setOpen(true);
        }}
        onCreate={() => {
          setEditing(null);
          setForm({ branch_id: branches.data?.[0]?.id ?? "", code: "", labels: { fr: "", en: "" }, active: true, milestones: [{ ...emptyMilestone(1), percent: 100 }] });
          setOpen(true);
        }}
        canCreate={session.can("payment_terms_template", "configure") && !!branches.data?.length}
      />

      <RecordDrawer
        open={open}
        onOpenChange={setOpen}
        title={editing ? `${editing.code} — ${t("common.edit")}` : t("common.new")}
        onSubmit={() => balanced && save.mutate(undefined as never)}
        saving={save.isPending}
        width="max-w-3xl"
      >
        <div className="grid grid-cols-2 gap-4">
          <FormField label={t("common.branch")} required error={save.fieldErrors["branch_id"]}>
            <Select
              value={form.branch_id}
              onValueChange={(value) => setForm({ ...form, branch_id: value })}
              disabled={!!editing}
              placeholder={t("common.select_placeholder")}
              options={(branches.data ?? []).map((b) => ({ value: b.id, label: b.trade_name || b.code }))}
            />
          </FormField>
          <FormField label={t("common.code")} required error={save.fieldErrors["code"]}>
            <Input value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value.toUpperCase() })} disabled={!!editing} />
          </FormField>
        </div>
        <FormField label={t("common.labels")} required error={save.fieldErrors["labels"]}>
          <LabelsInput value={form.labels} onChange={(labels) => setForm({ ...form, labels: { fr: labels.fr ?? "", en: labels.en ?? "" } })} />
        </FormField>

        <section className="flex flex-col gap-3">
          <header className="flex items-center justify-between">
            <h3 className="text-md font-semibold">{t("common.total")}</h3>
            <span className={`tabular text-md font-semibold ${balanced ? "text-success" : "text-danger"}`}>{total} %</span>
          </header>

          {form.milestones.map((milestone, index) => (
            <div key={index} className="flex flex-col gap-3 rounded-card border border-line p-3">
              <div className="flex items-center justify-between">
                <span className="tabular text-sm font-medium text-muted">#{index + 1}</span>
                {form.milestones.length > 1 && (
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    aria-label={t("common.delete")}
                    className="text-danger"
                    onClick={() => setForm({ ...form, milestones: form.milestones.filter((_, i) => i !== index) })}
                  >
                    <Trash2 className="size-4" aria-hidden />
                  </Button>
                )}
              </div>
              <FormField label={t("common.label")}>
                <LabelsInput
                  value={{ fr: milestone.label?.["fr"] ?? "", en: milestone.label?.["en"] ?? "" }}
                  onChange={(label) => updateMilestone(index, { label: { fr: label.fr ?? "", en: label.en ?? "" } })}
                />
              </FormField>
              <div className="grid grid-cols-3 gap-3">
                <FormField label="%">
                  <Input
                    type="number"
                    min={0}
                    max={100}
                    step="0.01"
                    value={String(milestone.percent ?? 0)}
                    onChange={(e) => updateMilestone(index, { percent: e.target.value })}
                    className="tabular"
                  />
                </FormField>
                <FormField label="trigger" required>
                  <Select value={milestone.trigger} onValueChange={(trigger) => updateMilestone(index, { trigger })} options={TRIGGERS.map((value) => ({ value, label: value }))} />
                </FormField>
                <FormField label="+ days">
                  <Input
                    type="number"
                    min={0}
                    value={String(milestone.due_days_after_trigger ?? 0)}
                    onChange={(e) => updateMilestone(index, { due_days_after_trigger: Number(e.target.value) || 0 })}
                    className="tabular"
                  />
                </FormField>
              </div>
            </div>
          ))}

          <Button
            variant="outline"
            leftIcon={<Plus className="size-4" aria-hidden />}
            onClick={() => setForm({ ...form, milestones: [...form.milestones, emptyMilestone(form.milestones.length + 1)] })}
          >
            {t("common.new")}
          </Button>

          {!balanced && <Alert tone="danger">{`${total} % ≠ 100 %`}</Alert>}
        </section>

        {editing && (
          <FormField label={t("common.status")}>
            <Switch checked={form.active} onCheckedChange={(checked) => setForm({ ...form, active: checked })} label={form.active ? t("common.active") : t("common.inactive")} />
          </FormField>
        )}
      </RecordDrawer>
    </>
  );
}
