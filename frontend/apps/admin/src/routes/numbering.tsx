/**
 * Numbering schemes (SPEC §23.3, §10.1).
 *
 * Document numbers are the reference clients and auditors quote back, so a scheme is versioned
 * and becomes immutable the moment it allocates its first number. The console has to make that
 * visible, because "why can't I edit this?" is otherwise the first support ticket: a scheme that
 * has issued numbers shows the lock and offers a new version instead of an edit.
 *
 * The pattern field previews live as it is typed. Getting `{SEQ:4}` wrong is cheap to fix before
 * activation and expensive afterwards.
 */
import { useApi } from "@mizan/api-client";
import { useSession } from "@mizan/app-kit";
import { useTranslation } from "@mizan/i18n";
import { Alert, Badge, Button, ConfirmDialog, FormField, Input, Select, Tooltip, useToast, type ColumnDef } from "@mizan/ui";
import { Lock, Play } from "lucide-react";
import { useMemo, useState } from "react";

import { ListPage, RecordDrawer, useList, useSave, textOf } from "../lib/resource";

type Scheme = {
  id: string;
  branch_id: string;
  department_id: string | null;
  applies_to: string;
  prefix: string;
  pattern: string;
  reset: string;
  gap_policy: string;
  allocation: string;
  version: number;
  status: string;
  effective_from: string | null;
  immutable: boolean;
  preview: string | null;
};
type Branch = { id: string; code: string; trade_name: string; legal_name: string; currency: string };

const KINDS = [
  "ACCOUNT", "PROJECT", "QUOTE", "ORDER", "CONTRACT", "INTAKE", "SAMPLE", "SPECIMEN", "TEST_RUN",
  "REPORT", "INVOICE", "CREDIT_NOTE", "PAYMENT", "RENTAL", "SALE", "OUTING", "TRANSFER",
  "WORK_ORDER", "EQUIPMENT", "MAINTENANCE",
];
const RESETS = ["NEVER", "YEARLY", "MONTHLY"];
const GAP_POLICIES = ["TOLERANT", "GAP_FREE"];
const ALLOCATIONS = ["ON_CREATE", "ON_ISSUE"];

/**
 * The same substitution the server performs, for the live preview only.
 *
 * It is deliberately approximate — the sequence shown is a placeholder, not a reservation — so
 * the real value still comes from `preview` on an activated scheme.
 */
function renderPattern(pattern: string, prefix: string, branchCode: string, departmentCode = ""): string {
  const now = new Date();
  return pattern.replace(/\{(PREFIX|BRANCH|DEPT|YYYY|YY|MM|SEQ(?::(\d+))?)\}/g, (_match, token: string, width?: string) => {
    if (token === "PREFIX") return prefix;
    if (token === "BRANCH") return branchCode;
    if (token === "DEPT") return departmentCode;
    if (token === "YYYY") return String(now.getFullYear());
    if (token === "YY") return String(now.getFullYear()).slice(-2);
    if (token === "MM") return String(now.getMonth() + 1).padStart(2, "0");
    return "1".padStart(Number(width ?? 1), "0");
  });
}

function statusTone(status: string): "success" | "slate" | "amber" {
  return status === "ACTIVE" ? "success" : status === "RETIRED" ? "slate" : "amber";
}

export function NumberingPage() {
  const { t } = useTranslation();
  const api = useApi();
  const session = useSession();
  const toast = useToast();
  const [branchFilter, setBranchFilter] = useState("");

  const branches = useList<Branch>(["branches", "list", {}], async () => (await api.client.GET("/branches")).data as Branch[] | undefined, {
    enabled: session.can("branch", "view"),
  });
  const listKey = ["numbering-schemes", "list", { branch: branchFilter }];
  const schemes = useList<Scheme>(listKey, async () =>
    (await api.client.GET("/numbering-schemes", { params: { query: branchFilter ? { branch_id: branchFilter } : {} } })).data as Scheme[] | undefined,
  );

  const branchByI = useMemo(() => new Map((branches.data ?? []).map((b) => [b.id, b])), [branches.data]);

  const [open, setOpen] = useState(false);
  /** A new version keeps the scheme's identity, so the drawer remembers which one it came from. */
  const [versionOf, setVersionOf] = useState<Scheme | null>(null);
  const [activating, setActivating] = useState<Scheme | null>(null);
  const [form, setForm] = useState({
    branch_id: "",
    applies_to: "QUOTE",
    prefix: "",
    pattern: "{PREFIX}-{BRANCH}-{YYYY}-{SEQ:4}",
    reset: "YEARLY",
    gap_policy: "TOLERANT",
    allocation: "ON_CREATE",
  });

  const save = useSave(
    async () => {
      const body = {
        prefix: form.prefix,
        pattern: form.pattern,
        reset: form.reset,
        gap_policy: form.gap_policy,
        allocation: form.allocation,
      };
      if (versionOf) {
        return (await api.client.POST("/numbering-schemes/{scheme_id}/versions", {
          params: { path: { scheme_id: versionOf.id } },
          body: body as never,
        })).data;
      }
      return (await api.client.POST("/numbering-schemes", {
        body: { ...body, branch_id: form.branch_id, applies_to: form.applies_to } as never,
      })).data;
    },
    [listKey],
    () => {
      setOpen(false);
      toast.success(t("common.saved"));
    },
  );

  const activate = useSave(
    async (scheme: Scheme) => (await api.client.POST("/numbering-schemes/{scheme_id}:activate", { params: { path: { scheme_id: scheme.id } } })).data,
    [listKey],
    () => {
      setActivating(null);
      toast.success(t("common.saved"));
    },
  );

  const canConfigure = session.can("numbering_scheme", "configure");

  const columns: ColumnDef<Scheme, unknown>[] = [
    { id: "applies_to", header: t("numbering.kind"), accessorKey: "applies_to", cell: (c) => <span className="font-medium">{textOf(c.getValue())}</span> },
    { id: "branch", header: t("common.branch"), accessorFn: (row) => branchByI.get(row.branch_id)?.trade_name ?? branchByI.get(row.branch_id)?.code ?? row.branch_id },
    { id: "pattern", header: t("numbering.pattern"), accessorKey: "pattern", cell: (c) => <code className="tabular text-sm">{textOf(c.getValue())}</code> },
    {
      id: "preview",
      header: t("numbering.next_value"),
      accessorFn: (row) => row.preview ?? renderPattern(row.pattern, row.prefix, branchByI.get(row.branch_id)?.code ?? "—"),
      cell: (c) => <span className="tabular font-medium">{textOf(c.getValue())}</span>,
    },
    { id: "reset", header: t("numbering.reset_policy"), accessorKey: "reset" },
    {
      id: "gap_policy",
      header: t("numbering.gapless"),
      accessorKey: "gap_policy",
      cell: (c) => (c.getValue() === "GAP_FREE" ? <Badge tone="teal">{t("numbering.gapless")}</Badge> : <span className="text-muted">—</span>),
    },
    { id: "version", header: t("common.version"), accessorKey: "version", cell: (c) => <span className="tabular">v{textOf(c.getValue())}</span> },
    {
      id: "status",
      header: t("common.status"),
      accessorKey: "status",
      cell: (c) => (
        <span className="flex items-center gap-1.5">
          <Badge tone={statusTone(textOf(c.getValue()))}>{textOf(c.getValue())}</Badge>
          {/* Immutability is the fact that explains every disabled control on this row. */}
          {c.row.original.immutable && (
            <Tooltip content={t("numbering.superseded")}>
              <Lock className="size-3.5 text-muted" aria-label={t("numbering.superseded")} />
            </Tooltip>
          )}
        </span>
      ),
    },
    {
      id: "actions",
      header: "",
      enableSorting: false,
      cell: (c) => {
        const scheme = c.row.original;
        if (!canConfigure) return null;
        return (
          <div className="flex justify-end gap-1">
            {scheme.status === "DRAFT" && (
              <Button
                variant="outline"
                size="sm"
                leftIcon={<Play className="size-3.5" aria-hidden />}
                onClick={(e) => {
                  e.stopPropagation();
                  setActivating(scheme);
                }}
              >
                {t("numbering.activate")}
              </Button>
            )}
            {scheme.immutable && (
              <Button
                variant="ghost"
                size="sm"
                onClick={(e) => {
                  e.stopPropagation();
                  setVersionOf(scheme);
                  setForm({
                    branch_id: scheme.branch_id,
                    applies_to: scheme.applies_to,
                    prefix: scheme.prefix,
                    pattern: scheme.pattern,
                    reset: scheme.reset,
                    gap_policy: scheme.gap_policy,
                    allocation: scheme.allocation,
                  });
                  setOpen(true);
                }}
              >
                {t("common.version")} +1
              </Button>
            )}
          </div>
        );
      },
    },
  ];

  const branchCode = branchByI.get(form.branch_id)?.code ?? "NKC";
  const preview = renderPattern(form.pattern, form.prefix, branchCode);
  // The server rejects this combination; saying so here costs one line and a round trip.
  const gaplessConflict = form.gap_policy === "GAP_FREE" && form.allocation !== "ON_ISSUE";

  return (
    <>
      <ListPage
        title={t("nav.admin.numbering")}
        columns={columns}
        rows={schemes.data}
        loading={schemes.isPending}
        error={schemes.error}
        onRetry={() => void schemes.refetch()}
        getRowId={(row) => row.id}
        searchable={(row, needle) => `${row.applies_to} ${row.pattern}`.toLowerCase().includes(needle)}
        onCreate={() => {
          setVersionOf(null);
          setForm({
            branch_id: branchFilter || branches.data?.[0]?.id || "",
            applies_to: "QUOTE",
            prefix: "",
            pattern: "{PREFIX}-{BRANCH}-{YYYY}-{SEQ:4}",
            reset: "YEARLY",
            gap_policy: "TOLERANT",
            allocation: "ON_CREATE",
          });
          setOpen(true);
        }}
        canCreate={canConfigure && !!branches.data?.length}
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

      <RecordDrawer
        open={open}
        onOpenChange={setOpen}
        title={versionOf ? `${versionOf.applies_to} — v${versionOf.version + 1}` : t("common.new")}
        description={versionOf ? t("numbering.superseded") : undefined}
        onSubmit={() => save.mutate(undefined as never)}
        saving={save.isPending}
      >
        <FormField label={t("common.branch")} required error={save.fieldErrors["branch_id"]}>
          <Select
            value={form.branch_id}
            onValueChange={(value) => setForm({ ...form, branch_id: value })}
            disabled={!!versionOf}
            placeholder={t("common.select_placeholder")}
            options={(branches.data ?? []).map((b) => ({ value: b.id, label: b.trade_name || b.code }))}
          />
        </FormField>
        <FormField label={t("numbering.kind")} required error={save.fieldErrors["applies_to"]}>
          <Select value={form.applies_to} onValueChange={(value) => setForm({ ...form, applies_to: value })} disabled={!!versionOf} options={KINDS.map((kind) => ({ value: kind, label: kind }))} />
        </FormField>
        <div className="grid grid-cols-3 gap-4">
          <FormField label="PREFIX" error={save.fieldErrors["prefix"]}>
            <Input value={form.prefix} onChange={(e) => setForm({ ...form, prefix: e.target.value.toUpperCase() })} maxLength={16} className="tabular" />
          </FormField>
          <FormField label={t("numbering.pattern")} required error={save.fieldErrors["pattern"]} className="col-span-2">
            <Input value={form.pattern} onChange={(e) => setForm({ ...form, pattern: e.target.value })} className="tabular" />
          </FormField>
        </div>
        <p className="-mt-2 text-xs text-muted">{t("numbering.pattern_help")}</p>

        {/* The preview updates as the pattern is typed: the point is to see the mistake now. */}
        <div className="rounded-card border border-line bg-subtle px-3 py-2">
          <p className="text-xs font-medium uppercase tracking-wide text-muted">{t("numbering.preview")}</p>
          <p className="tabular text-lg font-semibold">{preview || "—"}</p>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <FormField label={t("numbering.reset_policy")}>
            <Select
              value={form.reset}
              onValueChange={(value) => setForm({ ...form, reset: value })}
              options={RESETS.map((reset) => ({
                value: reset,
                label: reset === "NEVER" ? t("numbering.reset_never") : reset === "YEARLY" ? t("numbering.reset_yearly") : t("numbering.reset_monthly"),
              }))}
            />
          </FormField>
          <FormField label={t("numbering.gapless")} help={t("numbering.gapless_help")}>
            <Select value={form.gap_policy} onValueChange={(value) => setForm({ ...form, gap_policy: value })} options={GAP_POLICIES.map((policy) => ({ value: policy, label: policy }))} />
          </FormField>
        </div>
        <FormField label="allocation" error={save.fieldErrors["allocation"]}>
          <Select value={form.allocation} onValueChange={(value) => setForm({ ...form, allocation: value })} options={ALLOCATIONS.map((value) => ({ value, label: value }))} />
        </FormField>
        {gaplessConflict && <Alert tone="warning">GAP_FREE ⇒ ON_ISSUE</Alert>}
      </RecordDrawer>

      <ConfirmDialog
        open={!!activating}
        onOpenChange={(next) => !next && setActivating(null)}
        title={t("numbering.activate_confirm")}
        consequences={t("numbering.activate_consequences")}
        confirmLabel={t("numbering.activate")}
        cancelLabel={t("common.cancel")}
        loading={activate.isPending}
        onConfirm={() => activating && activate.mutate(activating)}
      >
        {activating && (
          <p className="tabular text-base">
            {renderPattern(activating.pattern, activating.prefix, branchByI.get(activating.branch_id)?.code ?? "")}
          </p>
        )}
      </ConfirmDialog>
    </>
  );
}
