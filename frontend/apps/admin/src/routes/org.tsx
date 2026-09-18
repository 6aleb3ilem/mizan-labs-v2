/**
 * Organisation (SPEC §23.1, A.2): company profile, branches, departments, signatories and
 * treasury accounts.
 *
 * These screens are the first thing a new tenant touches, and everything downstream — numbering,
 * documents, prices, workflows — hangs off a branch. So the branch form carries its whole
 * configuration rather than hiding half of it behind a second screen, and the fields that later
 * appear on issued documents (legal name, identifiers, legal notices) are grouped together and
 * labelled as such.
 */
import { useApi } from "@mizan/api-client";
import { useSession } from "@mizan/app-kit";
import { useTranslation } from "@mizan/i18n";
import {
  Badge,
  Button,
  Card,
  Checkbox,
  DescriptionList,
  FormField,
  FormSection,
  Input,
  LabelsInput,
  PageHeader,
  Select,
  Switch,
  Textarea,
  useToast,
  type ColumnDef,
} from "@mizan/ui";
import { useNavigate, useParams } from "@tanstack/react-router";
import { useMemo, useState } from "react";

import { ListPage, RecordDrawer, useList, useSave, textOf } from "../lib/resource";

type Branch = {
  id: string;
  code: string;
  legal_name: string;
  trade_name: string;
  identifiers: Record<string, unknown>;
  address: Record<string, unknown>;
  phone: string;
  email: string;
  currency: string;
  timezone: string;
  locales: string[];
  default_locale: string;
  rounding: string;
  working_days: number[];
  holidays: string[];
  settings: Record<string, unknown>;
  legal_texts: Record<string, unknown>;
  active: boolean;
  row_version: number;
};

type Department = { id: string; branch_id: string; code: string; labels: Record<string, string>; colour: string; ord: number; active: boolean };
type Signatory = {
  id: string;
  branch_id: string;
  user_id: string | null;
  display_name: string;
  title: string;
  document_kinds: string[];
  mode: string;
  has_signature_image: boolean;
  has_stamp_image: boolean;
  certificate_ref: string;
  esign_provider_code: string;
  requires_step_up: boolean;
  signing_order: number;
  active: boolean;
};
type TreasuryAccount = {
  id: string;
  branch_id: string;
  type: string;
  label: string;
  bank_name: string;
  iban: string;
  bic: string;
  currency: string;
  printed_on_invoices: boolean;
  active: boolean;
};

const BRANCHES_KEY = ["branches", "list", {}];

function useBranches(enabled = true) {
  const api = useApi();
  return useList<Branch>(BRANCHES_KEY, async () => (await api.client.GET("/branches")).data as Branch[] | undefined, { enabled });
}

/** Branch names are the label everywhere else; resolving them once keeps the tables readable. */
function useBranchNames(branches: Branch[] | undefined) {
  return useMemo(() => new Map((branches ?? []).map((b) => [b.id, b.trade_name || b.legal_name || b.code])), [branches]);
}

function activeBadge(active: boolean, activeLabel: string, inactiveLabel: string) {
  return <Badge tone={active ? "success" : "neutral"}>{active ? activeLabel : inactiveLabel}</Badge>;
}

/* ---------------------------------------------------------------- tenant */

export function TenantPage() {
  const { t } = useTranslation();
  const api = useApi();
  const session = useSession();
  const toast = useToast();
  const tenant = useList<{ id: string; code: string; name: string; theme: Record<string, unknown>; plan: string; status: string }>(
    ["tenant", "profile"],
    async () => {
      const result = (await api.client.GET("/tenant")).data;
      return result ? [result as never] : [];
    },
  );
  const record = tenant.data?.[0];
  const [name, setName] = useState<string | null>(null);
  const [brand, setBrand] = useState<string | null>(null);
  const brandValue = brand ?? (typeof record?.theme?.["primary"] === "string" ? (record.theme["primary"] as string) : "");

  const save = useSave(
    async (body: { name?: string; theme?: Record<string, unknown> }) => (await api.client.PATCH("/tenant", { body: body as never })).data,
    [["tenant", "profile"]],
    () => toast.success(t("common.saved")),
  );

  const canEdit = session.can("tenant", "update");
  const dirty = (name !== null && name !== record?.name) || (brand !== null && brand !== (record?.theme?.["primary"] ?? ""));

  return (
    <div className="flex flex-col gap-4">
      <PageHeader title={t("nav.admin.tenant")} subtitle={t("org.tenant_hint")} />
      <Card>
        <div className="flex max-w-xl flex-col gap-4">
          <DescriptionList
            items={[
              { label: t("common.code"), value: record?.code ?? "—" },
              { label: t("org.plan"), value: record?.plan ?? "—" },
              { label: t("org.status"), value: record ? <Badge tone={record.status === "ACTIVE" ? "success" : "warning"}>{record.status}</Badge> : "—" },
            ]}
            columns={3}
          />
          <FormField label={t("common.name")} required>
            <Input value={name ?? record?.name ?? ""} onChange={(e) => setName(e.target.value)} disabled={!canEdit || tenant.isPending} />
          </FormField>
          <FormField label={t("org.brand_colour")} help={t("org.brand_colour_help")}>
            {/*
              A colour input beside the hex field: the picker is faster, the text field is what a
              brand guide actually gives you.
            */}
            <div className="flex items-center gap-2">
              <input
                type="color"
                value={/^#[0-9a-fA-F]{6}$/.test(brandValue) ? brandValue : "#BF4E12"}
                onChange={(e) => setBrand(e.target.value.toUpperCase())}
                disabled={!canEdit}
                aria-label={t("org.brand_colour")}
                className="h-9 w-12 cursor-pointer rounded-control border border-line bg-surface p-1"
              />
              <Input value={brandValue} onChange={(e) => setBrand(e.target.value.toUpperCase())} placeholder="#BF4E12" disabled={!canEdit} className="w-40 tabular" />
            </div>
          </FormField>
          {canEdit && (
            <div className="flex gap-2">
              <Button
                loading={save.isPending}
                disabled={!dirty}
                onClick={() =>
                  save.mutate({
                    ...(name !== null ? { name } : {}),
                    ...(brand !== null ? { theme: { ...(record?.theme ?? {}), primary: brand } } : {}),
                  })
                }
              >
                {t("common.save")}
              </Button>
              {dirty && (
                <Button
                  variant="ghost"
                  onClick={() => {
                    setName(null);
                    setBrand(null);
                  }}
                >
                  {t("common.cancel")}
                </Button>
              )}
            </div>
          )}
        </div>
      </Card>
    </div>
  );
}

/* -------------------------------------------------------------- branches */

const ROUNDING_MODES = ["HALF_UP_2", "HALF_UP_0", "HALF_EVEN_2"];
const WEEKDAY_KEYS = ["org.monday", "org.tuesday", "org.wednesday", "org.thursday", "org.friday", "org.saturday", "org.sunday"];

/** `{"NIF": "123"}` ⇄ `NIF = 123`, one per line: a JSON textarea would be a trap for an admin. */
function recordToLines(value: Record<string, unknown>): string {
  return Object.entries(value ?? {})
    .map(([key, raw]) => `${key} = ${typeof raw === "string" ? raw : JSON.stringify(raw)}`)
    .join("\n");
}

function linesToRecord(text: string): Record<string, string> {
  const result: Record<string, string> = {};
  for (const line of text.split("\n")) {
    const at = line.indexOf("=");
    if (at === -1) continue;
    const key = line.slice(0, at).trim();
    if (key) result[key] = line.slice(at + 1).trim();
  }
  return result;
}

type BranchForm = {
  code: string;
  legal_name: string;
  trade_name: string;
  currency: string;
  timezone: string;
  default_locale: string;
  rounding: string;
  phone: string;
  email: string;
  working_days: number[];
  identifiers: string;
  address: string;
  holidays: string;
  legal_texts: string;
  active: boolean;
};

const EMPTY_BRANCH: BranchForm = {
  code: "",
  legal_name: "",
  trade_name: "",
  currency: "MRU",
  timezone: "Africa/Nouakchott",
  default_locale: "fr",
  rounding: "HALF_UP_2",
  phone: "",
  email: "",
  working_days: [1, 2, 3, 4, 5, 6],
  identifiers: "",
  address: "",
  holidays: "",
  legal_texts: "",
  active: true,
};

function branchToForm(branch: Branch): BranchForm {
  return {
    code: branch.code,
    legal_name: branch.legal_name,
    trade_name: branch.trade_name,
    currency: branch.currency,
    timezone: branch.timezone,
    default_locale: branch.default_locale,
    rounding: branch.rounding,
    phone: branch.phone,
    email: branch.email,
    working_days: branch.working_days ?? [],
    identifiers: recordToLines(branch.identifiers),
    address: recordToLines(branch.address),
    holidays: (branch.holidays ?? []).join("\n"),
    legal_texts: recordToLines(branch.legal_texts),
    active: branch.active,
  };
}

export function BranchesPage() {
  const { t } = useTranslation();
  const api = useApi();
  const session = useSession();
  const toast = useToast();
  const navigate = useNavigate();
  const branches = useBranches(session.can("branch", "view"));

  const [editing, setEditing] = useState<Branch | null>(null);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState<BranchForm>(EMPTY_BRANCH);

  const save = useSave(
    async (values: BranchForm) => {
      const body = {
        legal_name: values.legal_name,
        trade_name: values.trade_name,
        phone: values.phone,
        email: values.email,
        timezone: values.timezone,
        default_locale: values.default_locale,
        rounding: values.rounding,
        working_days: values.working_days,
        identifiers: linesToRecord(values.identifiers),
        address: linesToRecord(values.address),
        holidays: values.holidays.split("\n").map((line) => line.trim()).filter(Boolean),
        legal_texts: linesToRecord(values.legal_texts),
      };
      if (editing) {
        // The row version we read goes back with the write: a concurrent edit is rejected, not
        // silently overwritten (SPEC §8).
        return (await api.client.PATCH("/branches/{branch_id}", {
          params: { path: { branch_id: editing.id } },
          body: { ...body, active: values.active, row_version: editing.row_version } as never,
        })).data;
      }
      return (await api.client.POST("/branches", { body: { ...body, code: values.code, currency: values.currency, locales: ["fr", "en"] } as never })).data;
    },
    [BRANCHES_KEY],
    () => {
      setOpen(false);
      toast.success(t("common.saved"));
    },
  );

  const columns: ColumnDef<Branch, unknown>[] = [
    { id: "code", header: t("common.code"), accessorKey: "code", cell: (c) => <span className="font-medium tabular">{textOf(c.getValue())}</span> },
    { id: "trade_name", header: t("common.name"), accessorFn: (row) => row.trade_name || row.legal_name },
    { id: "currency", header: t("common.currency"), accessorKey: "currency" },
    { id: "timezone", header: t("org.timezone"), accessorKey: "timezone" },
    { id: "active", header: t("common.status"), accessorKey: "active", cell: (c) => activeBadge(c.getValue() as boolean, t("common.active"), t("common.inactive")) },
  ];

  const openCreate = () => {
    setEditing(null);
    setForm(EMPTY_BRANCH);
    setOpen(true);
  };

  return (
    <>
      <ListPage
        title={t("common.branches")}
        subtitle={t("org.branches_hint")}
        columns={columns}
        rows={branches.data}
        loading={branches.isPending}
        error={branches.error}
        onRetry={() => void branches.refetch()}
        getRowId={(row) => row.id}
        searchable={(row, needle) => `${row.code} ${row.legal_name} ${row.trade_name}`.toLowerCase().includes(needle)}
        onRowClick={(row) => void navigate({ to: "/org/branches/$branchId", params: { branchId: row.id } })}
        onCreate={openCreate}
        canCreate={session.can("branch", "create")}
      />
      <BranchDrawer
        open={open}
        onOpenChange={setOpen}
        editing={editing}
        form={form}
        setForm={setForm}
        onSubmit={() => save.mutate(form)}
        saving={save.isPending}
        fieldErrors={save.fieldErrors}
      />
    </>
  );
}

function BranchDrawer({
  open,
  onOpenChange,
  editing,
  form,
  setForm,
  onSubmit,
  saving,
  fieldErrors,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  editing: Branch | null;
  form: BranchForm;
  setForm: (form: BranchForm) => void;
  onSubmit: () => void;
  saving: boolean;
  fieldErrors: Record<string, string>;
}) {
  const { t } = useTranslation();
  const set = <K extends keyof BranchForm>(key: K, value: BranchForm[K]) => setForm({ ...form, [key]: value });

  return (
    <RecordDrawer
      open={open}
      onOpenChange={onOpenChange}
      title={editing ? `${editing.code} — ${t("common.edit")}` : t("common.new")}
      onSubmit={onSubmit}
      saving={saving}
      width="max-w-2xl"
    >
      <FormSection title={t("common.details")}>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <FormField label={t("common.code")} required error={fieldErrors["code"]} help={editing ? undefined : "2–64, A-Z 0-9 _ . -"}>
            {/* A branch code is printed into every document number, so it is fixed at creation. */}
            <Input value={form.code} onChange={(e) => set("code", e.target.value.toUpperCase())} disabled={!!editing} />
          </FormField>
          <FormField label={t("common.currency")} required error={fieldErrors["currency"]}>
            <Input value={form.currency} onChange={(e) => set("currency", e.target.value.toUpperCase())} maxLength={3} disabled={!!editing} className="tabular" />
          </FormField>
          <FormField label={t("org.legal_name")} required error={fieldErrors["legal_name"]} className="sm:col-span-2">
            <Input value={form.legal_name} onChange={(e) => set("legal_name", e.target.value)} />
          </FormField>
          <FormField label={t("org.trade_name")} error={fieldErrors["trade_name"]} className="sm:col-span-2">
            <Input value={form.trade_name} onChange={(e) => set("trade_name", e.target.value)} />
          </FormField>
          <FormField label={t("org.phone")} error={fieldErrors["phone"]}>
            <Input value={form.phone} onChange={(e) => set("phone", e.target.value)} inputMode="tel" />
          </FormField>
          <FormField label={t("org.email")} error={fieldErrors["email"]}>
            <Input value={form.email} onChange={(e) => set("email", e.target.value)} type="email" />
          </FormField>
        </div>
      </FormSection>

      <FormSection title={t("common.settings")}>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <FormField label={t("org.timezone")} error={fieldErrors["timezone"]}>
            <Input value={form.timezone} onChange={(e) => set("timezone", e.target.value)} />
          </FormField>
          <FormField label={t("org.default_locale")}>
            <Select
              value={form.default_locale}
              onValueChange={(value) => set("default_locale", value)}
              options={[
                { value: "fr", label: t("common.language_fr") },
                { value: "en", label: t("common.language_en") },
              ]}
            />
          </FormField>
          <FormField label={t("org.rounding")}>
            <Select value={form.rounding} onValueChange={(value) => set("rounding", value)} options={ROUNDING_MODES.map((mode) => ({ value: mode, label: mode }))} />
          </FormField>
          <FormField label={t("org.working_days")} className="sm:col-span-2">
            <div className="flex flex-wrap gap-3">
              {WEEKDAY_KEYS.map((key, index) => {
                const day = index + 1;
                return (
                  <Checkbox
                    key={key}
                    checked={form.working_days.includes(day)}
                    onCheckedChange={(checked) =>
                      set("working_days", checked ? [...form.working_days, day].sort((a, b) => a - b) : form.working_days.filter((d) => d !== day))
                    }
                    label={t(key)}
                  />
                );
              })}
            </div>
          </FormField>
          <FormField label={t("org.holidays")} help={t("org.holidays_help")} className="sm:col-span-2">
            <Textarea value={form.holidays} onChange={(e) => set("holidays", e.target.value)} rows={3} className="tabular" />
          </FormField>
        </div>
      </FormSection>

      <FormSection title={t("common.documents")} description={t("org.legal_texts_help")}>
        <FormField label={t("org.identifiers")} help={t("org.identifiers_help")}>
          <Textarea value={form.identifiers} onChange={(e) => set("identifiers", e.target.value)} rows={3} />
        </FormField>
        <FormField label={t("org.address")} help={t("org.identifiers_help")}>
          <Textarea value={form.address} onChange={(e) => set("address", e.target.value)} rows={3} />
        </FormField>
        <FormField label={t("org.legal_texts")} help={t("org.legal_texts_help")}>
          <Textarea value={form.legal_texts} onChange={(e) => set("legal_texts", e.target.value)} rows={3} />
        </FormField>
      </FormSection>

      {editing && (
        <FormField label={t("common.status")}>
          <Switch checked={form.active} onCheckedChange={(checked) => set("active", checked)} label={form.active ? t("common.active") : t("common.inactive")} />
        </FormField>
      )}
    </RecordDrawer>
  );
}

export function BranchPage() {
  const { t } = useTranslation();
  const api = useApi();
  const session = useSession();
  const toast = useToast();
  const params = useParams({ strict: false }) as { branchId: string };
  const navigate = useNavigate();
  const detailKey = ["branches", "one", params.branchId];
  const branch = useList<Branch>(detailKey, async () => {
    const result = (await api.client.GET("/branches/{branch_id}", { params: { path: { branch_id: params.branchId } } })).data;
    return result ? [result as Branch] : [];
  });
  const record = branch.data?.[0];

  const [open, setOpen] = useState(false);
  const [form, setForm] = useState<BranchForm>(EMPTY_BRANCH);

  const save = useSave(
    async (values: BranchForm) =>
      (await api.client.PATCH("/branches/{branch_id}", {
        params: { path: { branch_id: params.branchId } },
        body: {
          legal_name: values.legal_name,
          trade_name: values.trade_name,
          phone: values.phone,
          email: values.email,
          timezone: values.timezone,
          default_locale: values.default_locale,
          rounding: values.rounding,
          working_days: values.working_days,
          identifiers: linesToRecord(values.identifiers),
          address: linesToRecord(values.address),
          holidays: values.holidays.split("\n").map((line) => line.trim()).filter(Boolean),
          legal_texts: linesToRecord(values.legal_texts),
          active: values.active,
          // Optimistic lock: the version we rendered, not the one on the server now.
          row_version: record?.row_version,
        } as never,
      })).data,
    [detailKey, BRANCHES_KEY],
    () => {
      setOpen(false);
      toast.success(t("common.saved"));
    },
  );

  return (
    <div className="flex flex-col gap-4">
      <PageHeader
        title={record ? record.trade_name || record.legal_name : params.branchId}
        subtitle={record?.code}
        badges={record ? activeBadge(record.active, t("common.active"), t("common.inactive")) : undefined}
        actions={
          <>
            <Button variant="outline" onClick={() => void navigate({ to: "/org/branches" })}>
              {t("common.back")}
            </Button>
            {record && session.can("branch", "update") && (
              <Button
                onClick={() => {
                  setForm(branchToForm(record));
                  setOpen(true);
                }}
              >
                {t("common.edit")}
              </Button>
            )}
          </>
        }
      />
      <Card title={t("common.details")}>
        <DescriptionList
          items={[
            { label: t("org.legal_name"), value: record?.legal_name },
            { label: t("org.trade_name"), value: record?.trade_name },
            { label: t("common.currency"), value: record?.currency },
            { label: t("org.timezone"), value: record?.timezone },
            { label: t("org.default_locale"), value: record?.default_locale },
            { label: t("org.rounding"), value: record?.rounding },
            { label: t("org.phone"), value: record?.phone },
            { label: t("org.email"), value: record?.email },
          ]}
        />
      </Card>
      <Card title={t("org.identifiers")}>
        {Object.keys(record?.identifiers ?? {}).length ? (
          <DescriptionList items={Object.entries(record?.identifiers ?? {}).map(([key, value]) => ({ label: key, value: textOf(value) }))} />
        ) : (
          <p className="text-sm text-muted">{t("common.empty_title")}</p>
        )}
      </Card>
      <Card title={t("org.working_days")}>
        <div className="flex flex-wrap gap-2">
          {WEEKDAY_KEYS.map((key, index) => (
            <Badge key={key} tone={record?.working_days?.includes(index + 1) ? "primary" : "neutral"}>
              {t(key)}
            </Badge>
          ))}
        </div>
      </Card>
      {record && (
        <BranchDrawer
          open={open}
          onOpenChange={setOpen}
          editing={record}
          form={form}
          setForm={setForm}
          onSubmit={() => save.mutate(form)}
          saving={save.isPending}
          fieldErrors={save.fieldErrors}
        />
      )}
    </div>
  );
}

/* ----------------------------------------------------------- departments */

export function DepartmentsPage() {
  const { t } = useTranslation();
  const api = useApi();
  const session = useSession();
  const toast = useToast();
  const branches = useBranches(session.can("branch", "view"));
  const branchNames = useBranchNames(branches.data);
  const [branchFilter, setBranchFilter] = useState("");

  const departments = useList<Department>(["departments", "list", { branch: branchFilter }], async () =>
    (await api.client.GET("/departments", { params: { query: branchFilter ? { branch_id: branchFilter } : {} } })).data as Department[] | undefined,
  );

  const [editing, setEditing] = useState<Department | null>(null);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ branch_id: "", code: "", labels: { fr: "", en: "" }, colour: "teal", ord: 0, active: true });

  const save = useSave(
    async () => {
      if (editing) {
        return (await api.client.PATCH("/departments/{department_id}", {
          params: { path: { department_id: editing.id } },
          body: { labels: form.labels, colour: form.colour, ord: form.ord, active: form.active } as never,
        })).data;
      }
      return (await api.client.POST("/departments", {
        body: { branch_id: form.branch_id, code: form.code, labels: form.labels, colour: form.colour, ord: form.ord } as never,
      })).data;
    },
    [["departments", "list", { branch: branchFilter }], ["departments"]],
    () => {
      setOpen(false);
      toast.success(t("common.saved"));
    },
  );

  const columns: ColumnDef<Department, unknown>[] = [
    { id: "code", header: t("common.code"), accessorKey: "code", cell: (c) => <span className="font-medium">{textOf(c.getValue())}</span> },
    { id: "label", header: t("common.label"), accessorFn: (row) => row.labels?.["fr"] ?? row.labels?.["en"] ?? "" },
    { id: "branch", header: t("common.branch"), accessorFn: (row) => branchNames.get(row.branch_id) ?? row.branch_id },
    { id: "colour", header: t("org.colour"), accessorKey: "colour", cell: (c) => (c.getValue() ? <Badge tone={textOf(c.getValue()) as never}>{textOf(c.getValue())}</Badge> : "—") },
    { id: "ord", header: t("org.order"), accessorKey: "ord", cell: (c) => <span className="tabular">{textOf(c.getValue())}</span> },
    { id: "active", header: t("common.status"), accessorKey: "active", cell: (c) => activeBadge(c.getValue() as boolean, t("common.active"), t("common.inactive")) },
  ];

  return (
    <>
      <ListPage
        title={t("common.departments")}
        columns={columns}
        rows={departments.data}
        loading={departments.isPending}
        error={departments.error}
        onRetry={() => void departments.refetch()}
        getRowId={(row) => row.id}
        searchable={(row, needle) => `${row.code} ${Object.values(row.labels ?? {}).join(" ")}`.toLowerCase().includes(needle)}
        onRowClick={(row) => {
          setEditing(row);
          setForm({ branch_id: row.branch_id, code: row.code, labels: { fr: row.labels?.["fr"] ?? "", en: row.labels?.["en"] ?? "" }, colour: row.colour, ord: row.ord, active: row.active });
          setOpen(true);
        }}
        onCreate={() => {
          setEditing(null);
          setForm({ branch_id: branchFilter || branches.data?.[0]?.id || "", code: "", labels: { fr: "", en: "" }, colour: "teal", ord: 0, active: true });
          setOpen(true);
        }}
        canCreate={session.can("department", "create") && !!branches.data?.length}
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
        title={editing ? `${editing.code} — ${t("common.edit")}` : t("common.new")}
        onSubmit={() => save.mutate(undefined as never)}
        saving={save.isPending}
      >
        <FormField label={t("common.branch")} required error={save.fieldErrors["branch_id"]}>
          <Select
            value={form.branch_id}
            onValueChange={(value) => setForm({ ...form, branch_id: value })}
            disabled={!!editing}
            options={(branches.data ?? []).map((b) => ({ value: b.id, label: b.trade_name || b.code }))}
            placeholder={t("common.select_placeholder")}
          />
        </FormField>
        <FormField label={t("common.code")} required error={save.fieldErrors["code"]}>
          <Input value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value.toUpperCase() })} disabled={!!editing} />
        </FormField>
        <FormField label={t("common.labels")} required error={save.fieldErrors["labels"]}>
          <LabelsInput value={form.labels} onChange={(labels) => setForm({ ...form, labels: { fr: labels.fr ?? "", en: labels.en ?? "" } })} />
        </FormField>
        <div className="grid grid-cols-2 gap-4">
          <FormField label={t("org.colour")}>
            <Select
              value={form.colour}
              onValueChange={(value) => setForm({ ...form, colour: value })}
              options={["slate", "gray", "red", "orange", "amber", "green", "teal", "blue", "indigo", "violet", "pink", "brown"].map((hue) => ({
                value: hue,
                label: <Badge tone={hue as never}>{hue}</Badge>,
              }))}
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

/* ----------------------------------------------------------- signatories */

const SIGNATURE_MODES = ["IMAGE", "DRAWN", "CERTIFICATE", "EXTERNAL"];

export function SignatoriesPage() {
  const { t } = useTranslation();
  const api = useApi();
  const session = useSession();
  const toast = useToast();
  const branches = useBranches(session.can("branch", "view"));
  const branchNames = useBranchNames(branches.data);
  const [branchFilter, setBranchFilter] = useState("");

  const signatories = useList<Signatory>(["signatories", "list", { branch: branchFilter }], async () =>
    (await api.client.GET("/signatories", { params: { query: branchFilter ? { branch_id: branchFilter } : {} } })).data as Signatory[] | undefined,
  );

  const [editing, setEditing] = useState<Signatory | null>(null);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({
    branch_id: "",
    display_name: "",
    title: "",
    document_kinds: "",
    mode: "IMAGE",
    certificate_ref: "",
    esign_provider_code: "",
    requires_step_up: true,
    signing_order: 1,
    active: true,
  });

  const save = useSave(
    async () => {
      const kinds = form.document_kinds.split(",").map((kind) => kind.trim().toUpperCase()).filter(Boolean);
      const body = {
        display_name: form.display_name,
        title: form.title,
        document_kinds: kinds,
        mode: form.mode,
        certificate_ref: form.certificate_ref,
        esign_provider_code: form.esign_provider_code,
        requires_step_up: form.requires_step_up,
        signing_order: form.signing_order,
      };
      if (editing) {
        return (await api.client.PATCH("/signatories/{signatory_id}", {
          params: { path: { signatory_id: editing.id } },
          body: { ...body, active: form.active } as never,
        })).data;
      }
      return (await api.client.POST("/signatories", { body: { ...body, branch_id: form.branch_id } as never })).data;
    },
    [["signatories", "list", { branch: branchFilter }]],
    () => {
      setOpen(false);
      toast.success(t("common.saved"));
    },
  );

  const columns: ColumnDef<Signatory, unknown>[] = [
    { id: "display_name", header: t("common.name"), accessorKey: "display_name", cell: (c) => <span className="font-medium">{textOf(c.getValue())}</span> },
    { id: "title", header: t("org.signatory_title"), accessorKey: "title" },
    { id: "branch", header: t("common.branch"), accessorFn: (row) => branchNames.get(row.branch_id) ?? row.branch_id },
    { id: "mode", header: t("org.signature_mode"), accessorKey: "mode", cell: (c) => <Badge tone="blue">{textOf(c.getValue())}</Badge> },
    {
      id: "document_kinds",
      header: t("org.document_kinds"),
      accessorFn: (row) => row.document_kinds,
      cell: (c) => {
        const kinds = (c.getValue() as string[]) ?? [];
        return kinds.length ? <span className="text-sm">{kinds.join(", ")}</span> : <span className="text-muted">{t("common.all")}</span>;
      },
    },
    { id: "signing_order", header: t("org.signing_order"), accessorKey: "signing_order", cell: (c) => <span className="tabular">{textOf(c.getValue())}</span> },
    { id: "active", header: t("common.status"), accessorKey: "active", cell: (c) => activeBadge(c.getValue() as boolean, t("common.active"), t("common.inactive")) },
  ];

  return (
    <>
      <ListPage
        title={t("nav.admin.signatories")}
        columns={columns}
        rows={signatories.data}
        loading={signatories.isPending}
        error={signatories.error}
        onRetry={() => void signatories.refetch()}
        getRowId={(row) => row.id}
        searchable={(row, needle) => `${row.display_name} ${row.title}`.toLowerCase().includes(needle)}
        onRowClick={(row) => {
          setEditing(row);
          setForm({
            branch_id: row.branch_id,
            display_name: row.display_name,
            title: row.title,
            document_kinds: (row.document_kinds ?? []).join(", "),
            mode: row.mode,
            certificate_ref: row.certificate_ref,
            esign_provider_code: row.esign_provider_code,
            requires_step_up: row.requires_step_up,
            signing_order: row.signing_order,
            active: row.active,
          });
          setOpen(true);
        }}
        onCreate={() => {
          setEditing(null);
          setForm({
            branch_id: branchFilter || branches.data?.[0]?.id || "",
            display_name: "",
            title: "",
            document_kinds: "",
            mode: "IMAGE",
            certificate_ref: "",
            esign_provider_code: "",
            requires_step_up: true,
            signing_order: 1,
            active: true,
          });
          setOpen(true);
        }}
        canCreate={session.can("signatory", "create") && !!branches.data?.length}
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
        title={editing ? `${editing.display_name} — ${t("common.edit")}` : t("common.new")}
        onSubmit={() => save.mutate(undefined as never)}
        saving={save.isPending}
      >
        <FormField label={t("common.branch")} required error={save.fieldErrors["branch_id"]}>
          <Select
            value={form.branch_id}
            onValueChange={(value) => setForm({ ...form, branch_id: value })}
            disabled={!!editing}
            options={(branches.data ?? []).map((b) => ({ value: b.id, label: b.trade_name || b.code }))}
            placeholder={t("common.select_placeholder")}
          />
        </FormField>
        <FormField label={t("common.name")} required error={save.fieldErrors["display_name"]}>
          <Input value={form.display_name} onChange={(e) => setForm({ ...form, display_name: e.target.value })} />
        </FormField>
        <FormField label={t("org.signatory_title")} error={save.fieldErrors["title"]}>
          <Input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
        </FormField>
        <FormField label={t("org.document_kinds")} help={t("org.document_kinds_help")}>
          <Input value={form.document_kinds} onChange={(e) => setForm({ ...form, document_kinds: e.target.value })} placeholder="REPORT, QUOTE" />
        </FormField>
        <div className="grid grid-cols-2 gap-4">
          <FormField label={t("org.signature_mode")}>
            <Select value={form.mode} onValueChange={(value) => setForm({ ...form, mode: value })} options={SIGNATURE_MODES.map((mode) => ({ value: mode, label: mode }))} />
          </FormField>
          <FormField label={t("org.signing_order")}>
            <Input type="number" value={String(form.signing_order)} onChange={(e) => setForm({ ...form, signing_order: Number(e.target.value) || 1 })} className="tabular" />
          </FormField>
        </div>
        {/* Only the certificate-backed modes need these, and showing them otherwise invites
            someone to fill in a field that will never be read. */}
        {form.mode === "CERTIFICATE" && (
          <FormField label={t("org.certificate_ref")} error={save.fieldErrors["certificate_ref"]}>
            <Input value={form.certificate_ref} onChange={(e) => setForm({ ...form, certificate_ref: e.target.value })} />
          </FormField>
        )}
        {form.mode === "EXTERNAL" && (
          <FormField label={t("org.esign_provider")} error={save.fieldErrors["esign_provider_code"]}>
            <Input value={form.esign_provider_code} onChange={(e) => setForm({ ...form, esign_provider_code: e.target.value })} />
          </FormField>
        )}
        <FormField label={t("org.requires_step_up")}>
          <Switch checked={form.requires_step_up} onCheckedChange={(checked) => setForm({ ...form, requires_step_up: checked })} label={form.requires_step_up ? t("common.yes") : t("common.no")} />
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

/* ----------------------------------------------------- treasury accounts */

const ACCOUNT_TYPES = ["BANK", "CASH", "MOBILE_MONEY"];

export function TreasuryAccountsPage() {
  const { t } = useTranslation();
  const api = useApi();
  const session = useSession();
  const toast = useToast();
  const branches = useBranches(session.can("branch", "view"));
  const branchNames = useBranchNames(branches.data);
  const [branchFilter, setBranchFilter] = useState("");

  const accounts = useList<TreasuryAccount>(["treasury-accounts", "list", { branch: branchFilter }], async () =>
    (await api.client.GET("/treasury-accounts", { params: { query: branchFilter ? { branch_id: branchFilter } : {} } })).data as TreasuryAccount[] | undefined,
  );

  const [editing, setEditing] = useState<TreasuryAccount | null>(null);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ branch_id: "", type: "BANK", label: "", bank_name: "", iban: "", bic: "", currency: "MRU", printed_on_invoices: false, active: true });

  const save = useSave(
    async () => {
      const body = { label: form.label, bank_name: form.bank_name, iban: form.iban, bic: form.bic, printed_on_invoices: form.printed_on_invoices };
      if (editing) {
        return (await api.client.PATCH("/treasury-accounts/{account_id}", {
          params: { path: { account_id: editing.id } },
          body: { ...body, active: form.active } as never,
        })).data;
      }
      return (await api.client.POST("/treasury-accounts", {
        body: { ...body, branch_id: form.branch_id, type: form.type, currency: form.currency } as never,
      })).data;
    },
    [["treasury-accounts", "list", { branch: branchFilter }]],
    () => {
      setOpen(false);
      toast.success(t("common.saved"));
    },
  );

  const columns: ColumnDef<TreasuryAccount, unknown>[] = [
    { id: "label", header: t("common.label"), accessorKey: "label", cell: (c) => <span className="font-medium">{textOf(c.getValue())}</span> },
    { id: "type", header: t("org.account_type"), accessorKey: "type", cell: (c) => <Badge tone="slate">{textOf(c.getValue())}</Badge> },
    { id: "branch", header: t("common.branch"), accessorFn: (row) => branchNames.get(row.branch_id) ?? row.branch_id },
    { id: "bank_name", header: t("org.bank_name"), accessorKey: "bank_name" },
    { id: "iban", header: t("org.iban"), accessorKey: "iban", cell: (c) => <span className="tabular">{textOf(c.getValue())}</span> },
    { id: "currency", header: t("common.currency"), accessorKey: "currency" },
    {
      id: "printed_on_invoices",
      header: t("org.printed_on_invoices"),
      accessorKey: "printed_on_invoices",
      cell: (c) => (c.getValue() ? <Badge tone="success">{t("common.yes")}</Badge> : <span className="text-muted">{t("common.no")}</span>),
    },
    { id: "active", header: t("common.status"), accessorKey: "active", cell: (c) => activeBadge(c.getValue() as boolean, t("common.active"), t("common.inactive")) },
  ];

  return (
    <>
      <ListPage
        title={t("nav.admin.treasury_accounts")}
        columns={columns}
        rows={accounts.data}
        loading={accounts.isPending}
        error={accounts.error}
        onRetry={() => void accounts.refetch()}
        getRowId={(row) => row.id}
        searchable={(row, needle) => `${row.label} ${row.bank_name} ${row.iban}`.toLowerCase().includes(needle)}
        onRowClick={(row) => {
          setEditing(row);
          setForm({
            branch_id: row.branch_id,
            type: row.type,
            label: row.label,
            bank_name: row.bank_name,
            iban: row.iban,
            bic: row.bic,
            currency: row.currency,
            printed_on_invoices: row.printed_on_invoices,
            active: row.active,
          });
          setOpen(true);
        }}
        onCreate={() => {
          setEditing(null);
          const branch = branches.data?.find((b) => b.id === branchFilter) ?? branches.data?.[0];
          setForm({ branch_id: branch?.id ?? "", type: "BANK", label: "", bank_name: "", iban: "", bic: "", currency: branch?.currency ?? "MRU", printed_on_invoices: false, active: true });
          setOpen(true);
        }}
        canCreate={session.can("treasury_account", "create") && !!branches.data?.length}
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
        title={editing ? `${editing.label} — ${t("common.edit")}` : t("common.new")}
        onSubmit={() => save.mutate(undefined as never)}
        saving={save.isPending}
      >
        <FormField label={t("common.branch")} required error={save.fieldErrors["branch_id"]}>
          <Select
            value={form.branch_id}
            onValueChange={(value) => setForm({ ...form, branch_id: value, currency: branches.data?.find((b) => b.id === value)?.currency ?? form.currency })}
            disabled={!!editing}
            options={(branches.data ?? []).map((b) => ({ value: b.id, label: b.trade_name || b.code }))}
            placeholder={t("common.select_placeholder")}
          />
        </FormField>
        <div className="grid grid-cols-2 gap-4">
          <FormField label={t("org.account_type")} required>
            <Select value={form.type} onValueChange={(value) => setForm({ ...form, type: value })} disabled={!!editing} options={ACCOUNT_TYPES.map((type) => ({ value: type, label: type }))} />
          </FormField>
          <FormField label={t("common.currency")} required error={save.fieldErrors["currency"]}>
            <Input value={form.currency} onChange={(e) => setForm({ ...form, currency: e.target.value.toUpperCase() })} maxLength={3} disabled={!!editing} className="tabular" />
          </FormField>
        </div>
        <FormField label={t("common.label")} required error={save.fieldErrors["label"]}>
          <Input value={form.label} onChange={(e) => setForm({ ...form, label: e.target.value })} />
        </FormField>
        {/* Cash and mobile-money accounts have no bank coordinates to give. */}
        {form.type === "BANK" && (
          <>
            <FormField label={t("org.bank_name")} error={save.fieldErrors["bank_name"]}>
              <Input value={form.bank_name} onChange={(e) => setForm({ ...form, bank_name: e.target.value })} />
            </FormField>
            <div className="grid grid-cols-2 gap-4">
              <FormField label={t("org.iban")} error={save.fieldErrors["iban"]}>
                <Input value={form.iban} onChange={(e) => setForm({ ...form, iban: e.target.value.toUpperCase() })} className="tabular" />
              </FormField>
              <FormField label={t("org.bic")} error={save.fieldErrors["bic"]}>
                <Input value={form.bic} onChange={(e) => setForm({ ...form, bic: e.target.value.toUpperCase() })} className="tabular" />
              </FormField>
            </div>
          </>
        )}
        <FormField label={t("org.printed_on_invoices")}>
          <Switch
            checked={form.printed_on_invoices}
            onCheckedChange={(checked) => setForm({ ...form, printed_on_invoices: checked })}
            label={form.printed_on_invoices ? t("common.yes") : t("common.no")}
          />
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
