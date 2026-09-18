/**
 * Price lists and tax rules (SPEC §23.4, §10.6).
 *
 * A price list is scoped and dated: a branch, a currency, a validity window, optionally a client
 * tier or a single account. Resolution picks the most specific list that is valid on the day, so
 * the list screen shows the window and the scope on every row — an expired list looks identical
 * to an active one until you can see its dates.
 *
 * Prices themselves are a second level: a list opens into its rows, because a price list with
 * four hundred services does not belong in a drawer.
 */
import { useApi } from "@mizan/api-client";
import { useSession } from "@mizan/app-kit";
import { currentLocale, formatDate, formatNumber, useTranslation } from "@mizan/i18n";
import {
  Badge,
  Button,
  DataTable,
  Drawer,
  FormField,
  Input,
  LabelsInput,
  Select,
  Switch,
  useToast,
  type ColumnDef,
} from "@mizan/ui";
import { useMemo, useState } from "react";

import { ListPage, RecordDrawer, useList, useSave, textOf } from "../lib/resource";

type PriceList = {
  id: string;
  branch_id: string;
  code: string;
  labels: Record<string, string>;
  currency: string;
  valid_from: string;
  valid_to: string | null;
  client_tier_id: string | null;
  account_id: string | null;
  status: string;
  prices_count: number;
};

type Price = {
  id: string;
  price_list_id: string;
  service_id: string;
  specimen_type_id: string | null;
  unit_price: string | number;
  min_qty: string | number;
  currency: string;
};

type TaxRule = {
  id: string;
  branch_id: string;
  code: string;
  labels: Record<string, string>;
  rate: string | number;
  applies_to_kinds: string[];
  active: boolean;
};

type Branch = { id: string; code: string; trade_name: string; legal_name: string; currency: string };
type Service = { id: string; code: string; labels: Record<string, string>; kind: string };

const SERVICE_KINDS = ["LAB_TEST", "FIELD_SERVICE", "STUDY", "RENTAL", "SALE", "FEE"];
const LISTS_KEY = ["price-lists", "list", {}];
const TAX_KEY = ["tax-rules", "list", {}];

/** A list is only "the price" while today falls inside its window. */
function windowState(list: PriceList, today = new Date()): "active" | "future" | "expired" {
  const from = new Date(list.valid_from);
  const to = list.valid_to ? new Date(list.valid_to) : null;
  if (from > today) return "future";
  if (to && to < today) return "expired";
  return "active";
}

export function PriceListsPage() {
  const { t } = useTranslation();
  const api = useApi();
  const session = useSession();
  const toast = useToast();
  const locale = currentLocale();

  const branches = useList<Branch>(["branches", "list", {}], async () => (await api.client.GET("/branches")).data as Branch[] | undefined, {
    enabled: session.can("branch", "view"),
  });
  const lists = useList<PriceList>(LISTS_KEY, async () => (await api.client.GET("/price-lists")).data as PriceList[] | undefined, {
    enabled: session.can("price_list", "view"),
  });
  const services = useList<Service>(["services", "list", {}], async () => (await api.client.GET("/services")).data as Service[] | undefined, {
    enabled: session.can("service", "view"),
  });

  const [open, setOpen] = useState(false);
  const [viewing, setViewing] = useState<PriceList | null>(null);
  const [form, setForm] = useState({
    branch_id: "",
    code: "",
    labels: { fr: "", en: "" },
    currency: "MRU",
    valid_from: new Date().toISOString().slice(0, 10),
    valid_to: "",
  });

  const save = useSave(
    async () =>
      (await api.client.POST("/price-lists", {
        body: {
          branch_id: form.branch_id,
          code: form.code,
          labels: form.labels,
          currency: form.currency,
          valid_from: form.valid_from,
          valid_to: form.valid_to || null,
        } as never,
      })).data,
    [LISTS_KEY],
    () => {
      setOpen(false);
      toast.success(t("common.saved"));
    },
  );

  const columns: ColumnDef<PriceList, unknown>[] = [
    { id: "code", header: t("common.code"), accessorKey: "code", cell: (c) => <span className="font-medium tabular">{textOf(c.getValue())}</span> },
    { id: "label", header: t("common.label"), accessorFn: (row) => row.labels?.["fr"] ?? row.labels?.["en"] ?? "" },
    {
      id: "branch",
      header: t("common.branch"),
      accessorFn: (row) => branches.data?.find((b) => b.id === row.branch_id)?.trade_name ?? row.branch_id,
    },
    { id: "currency", header: t("common.currency"), accessorKey: "currency" },
    {
      id: "window",
      header: t("common.date"),
      accessorFn: (row) => row.valid_from,
      cell: (c) => {
        const list = c.row.original;
        const state = windowState(list);
        return (
          <span className="flex items-center gap-2">
            <span className="tabular text-sm">
              {formatDate(list.valid_from, locale)} → {list.valid_to ? formatDate(list.valid_to, locale) : "∞"}
            </span>
            <Badge tone={state === "active" ? "success" : state === "future" ? "teal" : "neutral"}>{state}</Badge>
          </span>
        );
      },
    },
    {
      id: "scope",
      header: t("access.scope"),
      accessorFn: (row) => (row.account_id ? "account" : row.client_tier_id ? "tier" : "branch"),
      cell: (c) => <Badge tone="slate">{textOf(c.getValue())}</Badge>,
    },
    { id: "prices_count", header: t("common.total"), accessorKey: "prices_count", cell: (c) => <span className="tabular">{textOf(c.getValue())}</span> },
  ];

  return (
    <>
      <ListPage
        title={t("nav.admin.price_lists")}
        columns={columns}
        rows={lists.data}
        loading={lists.isPending}
        error={lists.error}
        onRetry={() => void lists.refetch()}
        getRowId={(row) => row.id}
        searchable={(row, needle) => `${row.code} ${Object.values(row.labels ?? {}).join(" ")}`.toLowerCase().includes(needle)}
        onRowClick={setViewing}
        onCreate={() => {
          const branch = branches.data?.[0];
          setForm({
            branch_id: branch?.id ?? "",
            code: "",
            labels: { fr: "", en: "" },
            currency: branch?.currency ?? "MRU",
            valid_from: new Date().toISOString().slice(0, 10),
            valid_to: "",
          });
          setOpen(true);
        }}
        canCreate={session.can("price_list", "configure") && !!branches.data?.length}
      />

      <RecordDrawer open={open} onOpenChange={setOpen} title={t("common.new")} onSubmit={() => save.mutate(undefined as never)} saving={save.isPending}>
        <div className="grid grid-cols-2 gap-4">
          <FormField label={t("common.branch")} required error={save.fieldErrors["branch_id"]}>
            <Select
              value={form.branch_id}
              onValueChange={(value) => setForm({ ...form, branch_id: value, currency: branches.data?.find((b) => b.id === value)?.currency ?? form.currency })}
              placeholder={t("common.select_placeholder")}
              options={(branches.data ?? []).map((b) => ({ value: b.id, label: b.trade_name || b.code }))}
            />
          </FormField>
          <FormField label={t("common.code")} required error={save.fieldErrors["code"]}>
            <Input value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value.toUpperCase() })} />
          </FormField>
        </div>
        <FormField label={t("common.labels")} required error={save.fieldErrors["labels"]}>
          <LabelsInput value={form.labels} onChange={(labels) => setForm({ ...form, labels: { fr: labels.fr ?? "", en: labels.en ?? "" } })} />
        </FormField>
        <div className="grid grid-cols-3 gap-4">
          <FormField label={t("common.currency")} required error={save.fieldErrors["currency"]}>
            <Input value={form.currency} onChange={(e) => setForm({ ...form, currency: e.target.value.toUpperCase() })} maxLength={3} className="tabular" />
          </FormField>
          <FormField label="valid_from" required error={save.fieldErrors["valid_from"]}>
            <Input type="date" value={form.valid_from} onChange={(e) => setForm({ ...form, valid_from: e.target.value })} className="tabular" />
          </FormField>
          <FormField label="valid_to" optionalLabel={t("common.optional")}>
            <Input type="date" value={form.valid_to} onChange={(e) => setForm({ ...form, valid_to: e.target.value })} className="tabular" />
          </FormField>
        </div>
      </RecordDrawer>

      <PricesDrawer list={viewing} services={services.data ?? []} onClose={() => setViewing(null)} />
    </>
  );
}

/** The rows of one list. Opened as a drawer so the list behind stays as context. */
function PricesDrawer({ list, services, onClose }: { list: PriceList | null; services: Service[]; onClose: () => void }) {
  const { t } = useTranslation();
  const api = useApi();
  const locale = currentLocale();

  const prices = useList<Price>(
    ["price-lists", list?.id ?? "", "prices"],
    async () => (await api.client.GET("/price-lists/{price_list_id}/prices", { params: { path: { price_list_id: list!.id } } })).data as Price[] | undefined,
    { enabled: !!list },
  );

  const serviceNames = useMemo(() => new Map(services.map((service) => [service.id, service.labels?.["fr"] || service.code])), [services]);

  const columns: ColumnDef<Price, unknown>[] = [
    { id: "service", header: t("nav.admin.services"), accessorFn: (row) => serviceNames.get(row.service_id) ?? row.service_id },
    {
      id: "unit_price",
      header: t("common.amount"),
      accessorKey: "unit_price",
      cell: (c) => <span className="tabular font-medium">{formatNumber(c.getValue() as never, locale)}</span>,
    },
    { id: "min_qty", header: "min", accessorKey: "min_qty", cell: (c) => <span className="tabular">{formatNumber(c.getValue() as never, locale, 0)}</span> },
    { id: "currency", header: t("common.currency"), accessorKey: "currency" },
  ];

  return (
    <Drawer
      open={!!list}
      onOpenChange={(next) => !next && onClose()}
      title={list ? `${list.code} — ${list.currency}` : ""}
      description={list ? `${formatDate(list.valid_from, locale)} → ${list.valid_to ? formatDate(list.valid_to, locale) : "∞"}` : undefined}
      width="max-w-3xl"
      closeLabel={t("common.close")}
    >
      <DataTable
        columns={columns}
        data={prices.data ?? []}
        getRowId={(row) => row.id}
        loading={prices.isPending}
        emptyTitle={t("common.empty_title")}
        emptyHint={t("common.empty_hint")}
      />
    </Drawer>
  );
}

/* ------------------------------------------------------------- tax rules */

export function TaxRulesPage() {
  const { t } = useTranslation();
  const api = useApi();
  const session = useSession();
  const toast = useToast();
  const locale = currentLocale();

  const branches = useList<Branch>(["branches", "list", {}], async () => (await api.client.GET("/branches")).data as Branch[] | undefined, {
    enabled: session.can("branch", "view"),
  });
  const rules = useList<TaxRule>(TAX_KEY, async () => (await api.client.GET("/tax-rules")).data as TaxRule[] | undefined, {
    enabled: session.can("tax_rule", "view"),
  });

  const [editing, setEditing] = useState<TaxRule | null>(null);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ branch_id: "", code: "", labels: { fr: "", en: "" }, rate: "0", applies_to_kinds: [] as string[], active: true });

  const save = useSave(
    async () => {
      const body = { labels: form.labels, rate: Number(form.rate), applies_to_kinds: form.applies_to_kinds };
      if (editing) {
        return (await api.client.PATCH("/tax-rules/{rule_id}", { params: { path: { rule_id: editing.id } }, body: { ...body, active: form.active } as never })).data;
      }
      return (await api.client.POST("/tax-rules", { body: { ...body, branch_id: form.branch_id, code: form.code } as never })).data;
    },
    [TAX_KEY],
    () => {
      setOpen(false);
      toast.success(t("common.saved"));
    },
  );

  const columns: ColumnDef<TaxRule, unknown>[] = [
    { id: "code", header: t("common.code"), accessorKey: "code", cell: (c) => <span className="font-medium tabular">{textOf(c.getValue())}</span> },
    { id: "label", header: t("common.label"), accessorFn: (row) => row.labels?.["fr"] ?? row.labels?.["en"] ?? "" },
    {
      id: "rate",
      header: "%",
      accessorKey: "rate",
      cell: (c) => <span className="tabular font-medium">{formatNumber(c.getValue() as never, locale)} %</span>,
    },
    {
      id: "applies_to_kinds",
      header: t("nav.admin.services"),
      accessorFn: (row) => (row.applies_to_kinds ?? []).join(" "),
      cell: (c) => {
        const kinds = c.row.original.applies_to_kinds ?? [];
        return kinds.length ? (
          <span className="flex flex-wrap gap-1">
            {kinds.map((kind) => (
              <Badge key={kind} tone="slate">
                {kind}
              </Badge>
            ))}
          </span>
        ) : (
          <span className="text-muted">{t("common.all")}</span>
        );
      },
    },
    {
      id: "branch",
      header: t("common.branch"),
      accessorFn: (row) => branches.data?.find((b) => b.id === row.branch_id)?.trade_name ?? row.branch_id,
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
        title={t("nav.admin.tax_rules")}
        columns={columns}
        rows={rules.data}
        loading={rules.isPending}
        error={rules.error}
        onRetry={() => void rules.refetch()}
        getRowId={(row) => row.id}
        searchable={(row, needle) => `${row.code} ${Object.values(row.labels ?? {}).join(" ")}`.toLowerCase().includes(needle)}
        onRowClick={(row) => {
          setEditing(row);
          setForm({
            branch_id: row.branch_id,
            code: row.code,
            labels: { fr: row.labels?.["fr"] ?? "", en: row.labels?.["en"] ?? "" },
            rate: String(row.rate),
            applies_to_kinds: row.applies_to_kinds ?? [],
            active: row.active,
          });
          setOpen(true);
        }}
        onCreate={() => {
          setEditing(null);
          setForm({ branch_id: branches.data?.[0]?.id ?? "", code: "", labels: { fr: "", en: "" }, rate: "0", applies_to_kinds: [], active: true });
          setOpen(true);
        }}
        canCreate={session.can("tax_rule", "configure") && !!branches.data?.length}
      />

      <RecordDrawer
        open={open}
        onOpenChange={setOpen}
        title={editing ? `${editing.code} — ${t("common.edit")}` : t("common.new")}
        onSubmit={() => save.mutate(undefined as never)}
        saving={save.isPending}
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
        <FormField label="%" required error={save.fieldErrors["rate"]}>
          <Input type="number" min={0} max={100} step="0.01" value={form.rate} onChange={(e) => setForm({ ...form, rate: e.target.value })} className="tabular" />
        </FormField>
        <FormField label={t("nav.admin.services")} help={t("common.all")}>
          <div className="flex flex-wrap gap-2">
            {SERVICE_KINDS.map((kind) => {
              const on = form.applies_to_kinds.includes(kind);
              return (
                <Button
                  key={kind}
                  variant={on ? "primary" : "outline"}
                  size="sm"
                  onClick={() =>
                    setForm({ ...form, applies_to_kinds: on ? form.applies_to_kinds.filter((k) => k !== kind) : [...form.applies_to_kinds, kind] })
                  }
                >
                  {kind}
                </Button>
              );
            })}
          </div>
        </FormField>
        {editing && (
          <FormField label={t("common.status")}>
            <Switch checked={form.active} onCheckedChange={(checked) => setForm({ ...form, active: checked })} label={form.active ? t("common.active") : t("common.inactive")} />
          </FormField>
        )}
      </RecordDrawer>
    </>
  );
}
