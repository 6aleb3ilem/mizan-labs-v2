/**
 * The catalogue (SPEC §23.4, §10.3–10.4): categories, services, test definitions, specimen
 * types and sieve sets.
 *
 * This is where the laboratory's own vocabulary lives. A service is what a client buys; a test
 * definition is what the laboratory performs, and the two are linked by code so that a sold
 * line item knows which worksheet to generate.
 *
 * Test definitions are the sharpest edge in the whole configuration tier: they carry formulas
 * that compute results which end up on a signed report. So they are versioned, activated
 * explicitly, and — crucially — have a sandbox: a definition is run against sample measurements
 * and its computed values shown before anyone can activate it. A formula that divides by a field
 * nobody fills in is a bad afternoon if it is found in the sandbox, and a re-issued report if it
 * is not.
 */
import { useApi } from "@mizan/api-client";
import { useSession } from "@mizan/app-kit";
import { useTranslation } from "@mizan/i18n";
import {
  Alert,
  Badge,
  Button,
  Card,
  ConfirmDialog,
  DescriptionList,
  EmptyState,
  FormField,
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
import { FlaskConical, Play } from "lucide-react";
import { useMemo, useState } from "react";

import { ListPage, RecordDrawer, parseJsonObject, useList, useSave, textOf } from "../lib/resource";

type Category = { id: string; parent_id: string | null; code: string; labels: Record<string, string>; department_id: string | null; ord: number };
type Service = {
  id: string;
  category_id: string;
  code: string;
  labels: Record<string, string>;
  department_id: string | null;
  kind: string;
  unit_of_sale: string;
  test_definition_code: string;
  phase_template_code: string;
  equipment_class_code: string;
  stock_item_code: string;
  active: boolean;
};
type SpecimenType = { id: string; code: string; labels: Record<string, string>; shape: string; dims: Record<string, unknown>; derived: Record<string, unknown>; active: boolean };
type SieveSet = { id: string; code: string; labels: Record<string, string>; sizes_mm: number[]; active: boolean };
type TestDefinition = {
  id: string;
  code: string;
  version: number;
  status: string;
  labels: Record<string, string>;
  category_id: string | null;
  department_id: string | null;
  method_ref: string;
  unit_under_test: string;
  specimen_type_codes: string[];
  scheduling: Record<string, unknown>;
  stages: Record<string, unknown>[];
  intake_fields: Record<string, unknown>[];
  inputs: Record<string, unknown>[];
  computed: Record<string, unknown>[];
  aggregates: Record<string, unknown>[];
  rules?: Record<string, unknown>[];
};

const SERVICE_KINDS = ["LAB_TEST", "FIELD_SERVICE", "STUDY", "RENTAL", "SALE", "FEE"];
const UNITS_OF_SALE = ["UNIT", "PER_SPECIMEN", "PER_SAMPLE", "PER_DAY", "PER_HOUR", "LUMP_SUM"];
const SHAPES = ["CUBE", "CYLINDER", "PRISM", "BLOCK", "CORE", "OTHER"];

const CATEGORIES_KEY = ["service-categories", "list", {}];
const SERVICES_KEY = ["services", "list", {}];
const SPECIMEN_TYPES_KEY = ["specimen-types", "list", {}];
const SIEVE_SETS_KEY = ["sieve-sets", "list", {}];
const DEFINITIONS_KEY = ["test-definitions", "list", {}];

function labelOf(record: { labels?: Record<string, string>; code: string } | undefined): string {
  return record?.labels?.["fr"] || record?.labels?.["en"] || record?.code || "";
}

function statusTone(status: string): "success" | "amber" | "slate" {
  return status === "ACTIVE" ? "success" : status === "DRAFT" ? "amber" : "slate";
}

/* ------------------------------------------------------------- categories */

export function CategoriesPage() {
  const { t } = useTranslation();
  const api = useApi();
  const session = useSession();
  const toast = useToast();

  const categories = useList<Category>(CATEGORIES_KEY, async () => (await api.client.GET("/service-categories")).data as Category[] | undefined, {
    enabled: session.can("service_category", "view"),
  });

  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ code: "", labels: { fr: "", en: "" }, parent_id: "", ord: 0 });

  const save = useSave(
    async () =>
      (await api.client.POST("/service-categories", {
        body: { code: form.code, labels: form.labels, parent_id: form.parent_id || null, ord: form.ord } as never,
      })).data,
    [CATEGORIES_KEY],
    () => {
      setOpen(false);
      toast.success(t("common.saved"));
    },
  );

  const byId = useMemo(() => new Map((categories.data ?? []).map((category) => [category.id, category])), [categories.data]);

  const columns: ColumnDef<Category, unknown>[] = [
    { id: "ord", header: t("org.order"), accessorKey: "ord", cell: (c) => <span className="tabular text-muted">{textOf(c.getValue())}</span> },
    { id: "code", header: t("common.code"), accessorKey: "code", cell: (c) => <span className="font-medium tabular">{textOf(c.getValue())}</span> },
    { id: "label", header: t("common.label"), accessorFn: (row) => labelOf(row) },
    {
      id: "parent",
      header: t("nav.admin.categories"),
      accessorFn: (row) => (row.parent_id ? labelOf(byId.get(row.parent_id)) : ""),
      cell: (c) => textOf(c.getValue()) || <span className="text-muted">—</span>,
    },
  ];

  return (
    <>
      <ListPage
        title={t("nav.admin.categories")}
        columns={columns}
        rows={categories.data}
        loading={categories.isPending}
        error={categories.error}
        onRetry={() => void categories.refetch()}
        getRowId={(row) => row.id}
        searchable={(row, needle) => `${row.code} ${labelOf(row)}`.toLowerCase().includes(needle)}
        onCreate={() => {
          const next = Math.max(0, ...(categories.data ?? []).map((category) => category.ord)) + 10;
          setForm({ code: "", labels: { fr: "", en: "" }, parent_id: "", ord: next });
          setOpen(true);
        }}
        canCreate={session.can("service_category", "configure")}
      />

      <RecordDrawer open={open} onOpenChange={setOpen} title={t("common.new")} onSubmit={() => save.mutate(undefined as never)} saving={save.isPending}>
        <FormField label={t("common.code")} required error={save.fieldErrors["code"]}>
          <Input value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value.toUpperCase() })} />
        </FormField>
        <FormField label={t("common.labels")} required error={save.fieldErrors["labels"]}>
          <LabelsInput value={form.labels} onChange={(labels) => setForm({ ...form, labels: { fr: labels.fr ?? "", en: labels.en ?? "" } })} />
        </FormField>
        <div className="grid grid-cols-2 gap-4">
          <FormField label={t("nav.admin.categories")} optionalLabel={t("common.optional")}>
            <Select
              value={form.parent_id}
              onValueChange={(value) => setForm({ ...form, parent_id: value })}
              allowEmpty
              emptyLabel={t("common.none")}
              options={(categories.data ?? []).map((category) => ({ value: category.id, label: labelOf(category) }))}
            />
          </FormField>
          <FormField label={t("org.order")}>
            <Input type="number" value={String(form.ord)} onChange={(e) => setForm({ ...form, ord: Number(e.target.value) || 0 })} className="tabular" />
          </FormField>
        </div>
      </RecordDrawer>
    </>
  );
}

/* --------------------------------------------------------------- services */

export function ServicesPage() {
  const { t } = useTranslation();
  const api = useApi();
  const session = useSession();
  const toast = useToast();

  const services = useList<Service>(SERVICES_KEY, async () => (await api.client.GET("/services")).data as Service[] | undefined, {
    enabled: session.can("service", "view"),
  });
  const categories = useList<Category>(CATEGORIES_KEY, async () => (await api.client.GET("/service-categories")).data as Category[] | undefined, {
    enabled: session.can("service_category", "view"),
  });
  const definitions = useList<TestDefinition>(DEFINITIONS_KEY, async () => (await api.client.GET("/test-definitions")).data as TestDefinition[] | undefined, {
    enabled: session.can("test_definition", "view"),
  });

  const [editing, setEditing] = useState<Service | null>(null);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({
    category_id: "",
    code: "",
    labels: { fr: "", en: "" },
    kind: "LAB_TEST",
    unit_of_sale: "PER_SPECIMEN",
    test_definition_code: "",
    active: true,
  });

  const save = useSave(
    async () => {
      const body = {
        labels: form.labels,
        category_id: form.category_id,
        unit_of_sale: form.unit_of_sale,
        test_definition_code: form.test_definition_code,
      };
      if (editing) {
        return (await api.client.PATCH("/services/{service_id}", {
          params: { path: { service_id: editing.id } },
          body: { ...body, active: form.active } as never,
        })).data;
      }
      return (await api.client.POST("/services", { body: { ...body, code: form.code, kind: form.kind } as never })).data;
    },
    [SERVICES_KEY],
    () => {
      setOpen(false);
      toast.success(t("common.saved"));
    },
  );

  const categoryNames = useMemo(() => new Map((categories.data ?? []).map((category) => [category.id, labelOf(category)])), [categories.data]);

  const columns: ColumnDef<Service, unknown>[] = [
    { id: "code", header: t("common.code"), accessorKey: "code", cell: (c) => <span className="font-medium tabular">{textOf(c.getValue())}</span> },
    { id: "label", header: t("common.label"), accessorFn: (row) => labelOf(row) },
    { id: "category", header: t("nav.admin.categories"), accessorFn: (row) => categoryNames.get(row.category_id) ?? row.category_id },
    { id: "kind", header: t("numbering.kind"), accessorKey: "kind", cell: (c) => <Badge tone="blue">{textOf(c.getValue())}</Badge> },
    { id: "unit_of_sale", header: t("common.amount"), accessorKey: "unit_of_sale" },
    {
      id: "test_definition_code",
      header: t("nav.admin.test_definitions"),
      accessorKey: "test_definition_code",
      cell: (c) => (c.getValue() ? <code className="text-sm">{textOf(c.getValue())}</code> : <span className="text-muted">—</span>),
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
        title={t("nav.admin.services")}
        columns={columns}
        rows={services.data}
        loading={services.isPending}
        error={services.error}
        onRetry={() => void services.refetch()}
        getRowId={(row) => row.id}
        searchable={(row, needle) => `${row.code} ${labelOf(row)}`.toLowerCase().includes(needle)}
        onRowClick={(row) => {
          setEditing(row);
          setForm({
            category_id: row.category_id,
            code: row.code,
            labels: { fr: row.labels?.["fr"] ?? "", en: row.labels?.["en"] ?? "" },
            kind: row.kind,
            unit_of_sale: row.unit_of_sale,
            test_definition_code: row.test_definition_code,
            active: row.active,
          });
          setOpen(true);
        }}
        onCreate={() => {
          setEditing(null);
          setForm({
            category_id: categories.data?.[0]?.id ?? "",
            code: "",
            labels: { fr: "", en: "" },
            kind: "LAB_TEST",
            unit_of_sale: "PER_SPECIMEN",
            test_definition_code: "",
            active: true,
          });
          setOpen(true);
        }}
        canCreate={session.can("service", "configure") && !!categories.data?.length}
      />

      <RecordDrawer
        open={open}
        onOpenChange={setOpen}
        title={editing ? `${editing.code} — ${t("common.edit")}` : t("common.new")}
        onSubmit={() => save.mutate(undefined as never)}
        saving={save.isPending}
      >
        <div className="grid grid-cols-2 gap-4">
          <FormField label={t("common.code")} required error={save.fieldErrors["code"]}>
            <Input value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value.toUpperCase() })} disabled={!!editing} />
          </FormField>
          <FormField label={t("numbering.kind")} required error={save.fieldErrors["kind"]}>
            <Select value={form.kind} onValueChange={(value) => setForm({ ...form, kind: value })} disabled={!!editing} options={SERVICE_KINDS.map((kind) => ({ value: kind, label: kind }))} />
          </FormField>
        </div>
        <FormField label={t("common.labels")} required error={save.fieldErrors["labels"]}>
          <LabelsInput value={form.labels} onChange={(labels) => setForm({ ...form, labels: { fr: labels.fr ?? "", en: labels.en ?? "" } })} />
        </FormField>
        <FormField label={t("nav.admin.categories")} required error={save.fieldErrors["category_id"]}>
          <Select
            value={form.category_id}
            onValueChange={(value) => setForm({ ...form, category_id: value })}
            placeholder={t("common.select_placeholder")}
            options={(categories.data ?? []).map((category) => ({ value: category.id, label: labelOf(category) }))}
          />
        </FormField>
        <FormField label={t("common.amount")}>
          <Select value={form.unit_of_sale} onValueChange={(value) => setForm({ ...form, unit_of_sale: value })} options={UNITS_OF_SALE.map((unit) => ({ value: unit, label: unit }))} />
        </FormField>
        {/* Only a laboratory test runs a definition; offering one on a rental would be noise. */}
        {form.kind === "LAB_TEST" && (
          <FormField label={t("nav.admin.test_definitions")} help={t("common.optional")}>
            <Select
              value={form.test_definition_code}
              onValueChange={(value) => setForm({ ...form, test_definition_code: value })}
              allowEmpty
              emptyLabel={t("common.none")}
              options={(definitions.data ?? []).map((definition) => ({ value: definition.code, label: `${definition.code} — ${labelOf(definition)}` }))}
            />
          </FormField>
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

/* --------------------------------------------------------- specimen types */

export function SpecimenTypesPage() {
  const { t } = useTranslation();
  const api = useApi();
  const session = useSession();
  const toast = useToast();

  const types = useList<SpecimenType>(SPECIMEN_TYPES_KEY, async () => (await api.client.GET("/specimen-types")).data as SpecimenType[] | undefined, {
    enabled: session.can("specimen_type", "view"),
  });

  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ code: "", labels: { fr: "", en: "" }, shape: "CUBE", dims: '{"a_mm": 150}' });

  const save = useSave(
    async () => {
      const dims = parseJsonObject(form.dims) ?? {};
      return (await api.client.POST("/specimen-types", { body: { code: form.code, labels: form.labels, shape: form.shape, dims } as never })).data;
    },
    [SPECIMEN_TYPES_KEY],
    () => {
      setOpen(false);
      toast.success(t("common.saved"));
    },
  );

  const columns: ColumnDef<SpecimenType, unknown>[] = [
    { id: "code", header: t("common.code"), accessorKey: "code", cell: (c) => <span className="font-medium tabular">{textOf(c.getValue())}</span> },
    { id: "label", header: t("common.label"), accessorFn: (row) => labelOf(row) },
    { id: "shape", header: "shape", accessorKey: "shape", cell: (c) => <Badge tone="teal">{textOf(c.getValue())}</Badge> },
    {
      id: "dims",
      header: "dims",
      accessorFn: (row) => JSON.stringify(row.dims ?? {}),
      cell: (c) => (
        <span className="flex flex-wrap gap-1">
          {Object.entries(c.row.original.dims ?? {}).map(([key, value]) => (
            <Badge key={key} tone="slate">
              {key}: {String(value)}
            </Badge>
          ))}
        </span>
      ),
    },
    {
      id: "derived",
      header: "derived",
      accessorFn: (row) => Object.keys(row.derived ?? {}).join(", "),
      cell: (c) => <span className="text-sm text-muted">{textOf(c.getValue()) || "—"}</span>,
    },
  ];

  return (
    <>
      <ListPage
        title={t("nav.admin.specimen_types")}
        columns={columns}
        rows={types.data}
        loading={types.isPending}
        error={types.error}
        onRetry={() => void types.refetch()}
        getRowId={(row) => row.id}
        searchable={(row, needle) => `${row.code} ${labelOf(row)}`.toLowerCase().includes(needle)}
        onCreate={() => {
          setForm({ code: "", labels: { fr: "", en: "" }, shape: "CUBE", dims: '{"a_mm": 150}' });
          setOpen(true);
        }}
        canCreate={session.can("specimen_type", "configure")}
      />

      <RecordDrawer open={open} onOpenChange={setOpen} title={t("common.new")} onSubmit={() => save.mutate(undefined as never)} saving={save.isPending}>
        <FormField label={t("common.code")} required error={save.fieldErrors["code"]}>
          <Input value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value.toUpperCase() })} />
        </FormField>
        <FormField label={t("common.labels")} required error={save.fieldErrors["labels"]}>
          <LabelsInput value={form.labels} onChange={(labels) => setForm({ ...form, labels: { fr: labels.fr ?? "", en: labels.en ?? "" } })} />
        </FormField>
        <FormField label="shape" required error={save.fieldErrors["shape"]}>
          <Select value={form.shape} onValueChange={(value) => setForm({ ...form, shape: value })} options={SHAPES.map((shape) => ({ value: shape, label: shape }))} />
        </FormField>
        {/* The dimensions feed the derived area a compression formula divides by, so they are
            typed as the JSON the engine will actually receive. */}
        <FormField label="dims" required help='{"a_mm": 150} · {"d_mm": 160, "h_mm": 320}' error={save.fieldErrors["dims"]}>
          <Textarea value={form.dims} onChange={(e) => setForm({ ...form, dims: e.target.value })} rows={3} className="tabular" />
        </FormField>
      </RecordDrawer>
    </>
  );
}

/* -------------------------------------------------------------- sieve sets */

export function SieveSetsPage() {
  const { t } = useTranslation();
  const api = useApi();
  const session = useSession();
  const toast = useToast();

  const sets = useList<SieveSet>(SIEVE_SETS_KEY, async () => (await api.client.GET("/sieve-sets")).data as SieveSet[] | undefined, {
    enabled: session.can("sieve_set", "view"),
  });

  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ code: "", labels: { fr: "", en: "" }, sizes: "" });

  // Descending is the order a grading curve is read in, and the order the sieves are stacked.
  const parsedSizes = useMemo(
    () =>
      form.sizes
        .split(/[,\s]+/)
        .map((value) => Number(value))
        .filter((value) => Number.isFinite(value) && value > 0)
        .sort((a, b) => b - a),
    [form.sizes],
  );

  const save = useSave(
    async () => (await api.client.POST("/sieve-sets", { body: { code: form.code, labels: form.labels, sizes_mm: parsedSizes } as never })).data,
    [SIEVE_SETS_KEY],
    () => {
      setOpen(false);
      toast.success(t("common.saved"));
    },
  );

  const columns: ColumnDef<SieveSet, unknown>[] = [
    { id: "code", header: t("common.code"), accessorKey: "code", cell: (c) => <span className="font-medium tabular">{textOf(c.getValue())}</span> },
    { id: "label", header: t("common.label"), accessorFn: (row) => labelOf(row) },
    {
      id: "sizes_mm",
      header: "mm",
      accessorFn: (row) => (row.sizes_mm ?? []).join(" "),
      cell: (c) => <span className="tabular text-sm">{(c.row.original.sizes_mm ?? []).join(" · ")}</span>,
    },
    {
      id: "count",
      header: t("common.total"),
      accessorFn: (row) => (row.sizes_mm ?? []).length,
      cell: (c) => <span className="tabular">{textOf(c.getValue())}</span>,
    },
  ];

  return (
    <>
      <ListPage
        title={t("nav.admin.sieve_sets")}
        columns={columns}
        rows={sets.data}
        loading={sets.isPending}
        error={sets.error}
        onRetry={() => void sets.refetch()}
        getRowId={(row) => row.id}
        searchable={(row, needle) => `${row.code} ${labelOf(row)}`.toLowerCase().includes(needle)}
        onCreate={() => {
          setForm({ code: "", labels: { fr: "", en: "" }, sizes: "" });
          setOpen(true);
        }}
        canCreate={session.can("sieve_set", "configure")}
      />

      <RecordDrawer
        open={open}
        onOpenChange={setOpen}
        title={t("common.new")}
        onSubmit={() => parsedSizes.length > 0 && save.mutate(undefined as never)}
        saving={save.isPending}
      >
        <FormField label={t("common.code")} required error={save.fieldErrors["code"]}>
          <Input value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value.toUpperCase() })} />
        </FormField>
        <FormField label={t("common.labels")} required error={save.fieldErrors["labels"]}>
          <LabelsInput value={form.labels} onChange={(labels) => setForm({ ...form, labels: { fr: labels.fr ?? "", en: labels.en ?? "" } })} />
        </FormField>
        <FormField label="mm" required help="31.5 25 20 16 12.5 10 8 6.3 5 4 2" error={save.fieldErrors["sizes_mm"]}>
          <Textarea value={form.sizes} onChange={(e) => setForm({ ...form, sizes: e.target.value })} rows={3} className="tabular" />
        </FormField>
        {parsedSizes.length > 0 && (
          <div className="rounded-card border border-line bg-subtle px-3 py-2">
            <p className="text-xs font-medium uppercase tracking-wide text-muted">{t("common.preview")}</p>
            <p className="tabular text-sm">{parsedSizes.join(" · ")}</p>
          </div>
        )}
      </RecordDrawer>
    </>
  );
}

/* --------------------------------------------------------- test definitions */

export function TestDefinitionsPage() {
  const { t } = useTranslation();
  const api = useApi();
  const session = useSession();
  const navigate = useNavigate();

  const definitions = useList<TestDefinition>(DEFINITIONS_KEY, async () => (await api.client.GET("/test-definitions")).data as TestDefinition[] | undefined, {
    enabled: session.can("test_definition", "view"),
  });

  const columns: ColumnDef<TestDefinition, unknown>[] = [
    { id: "code", header: t("common.code"), accessorKey: "code", cell: (c) => <span className="font-medium tabular">{textOf(c.getValue())}</span> },
    { id: "label", header: t("common.label"), accessorFn: (row) => labelOf(row) },
    { id: "method_ref", header: "method", accessorKey: "method_ref", cell: (c) => <code className="text-sm">{textOf(c.getValue()) || "—"}</code> },
    { id: "unit_under_test", header: "unit", accessorKey: "unit_under_test" },
    {
      id: "inputs",
      header: "inputs",
      accessorFn: (row) => (row.inputs ?? []).length,
      cell: (c) => <span className="tabular">{textOf(c.getValue())}</span>,
    },
    {
      id: "computed",
      header: "computed",
      accessorFn: (row) => (row.computed ?? []).length,
      cell: (c) => <span className="tabular">{textOf(c.getValue())}</span>,
    },
    { id: "version", header: t("common.version"), accessorKey: "version", cell: (c) => <span className="tabular">v{textOf(c.getValue())}</span> },
    { id: "status", header: t("common.status"), accessorKey: "status", cell: (c) => <Badge tone={statusTone(textOf(c.getValue()))}>{textOf(c.getValue())}</Badge> },
  ];

  return (
    <ListPage
      title={t("nav.admin.test_definitions")}
      columns={columns}
      rows={definitions.data}
      loading={definitions.isPending}
      error={definitions.error}
      onRetry={() => void definitions.refetch()}
      getRowId={(row) => row.id}
      searchable={(row, needle) => `${row.code} ${labelOf(row)} ${row.method_ref}`.toLowerCase().includes(needle)}
      onRowClick={(row) => void navigate({ to: "/catalog/test-definitions/$definitionId", params: { definitionId: row.id } })}
      canCreate={false}
      emptyHint={t("vocab.hint")}
    />
  );
}

/**
 * One definition, with its sandbox.
 *
 * The sandbox is the reason this screen exists. Sample measurements go in, the server evaluates
 * the definition's formulas exactly as a real worksheet would, and the computed values and rule
 * verdicts come back. Activating without running it is possible but foolish, which is why the
 * sandbox sits above the activate button rather than behind a tab.
 */
export function TestDefinitionPage() {
  const { t } = useTranslation();
  const api = useApi();
  const session = useSession();
  const toast = useToast();
  const navigate = useNavigate();
  const params = useParams({ strict: false }) as { definitionId: string };

  const detailKey = ["test-definitions", "one", params.definitionId];
  const definition = useList<TestDefinition>(detailKey, async () => {
    const result = (await api.client.GET("/test-definitions/{definition_id}", { params: { path: { definition_id: params.definitionId } } })).data;
    return result ? [result as TestDefinition] : [];
  });
  const record = definition.data?.[0];

  const [sample, setSample] = useState('{\n  "subjects": [\n    { "id": "S1", "inputs": {} }\n  ]\n}');
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [activating, setActivating] = useState(false);

  const run = useSave(async () => {
    const data = parseJsonObject(sample);
    if (!data) {
      toast.error(t("common.error_title"), "JSON");
      return undefined;
    }
    const response = await api.client.POST("/test-definitions/{definition_id}:sandbox", {
      params: { path: { definition_id: params.definitionId } },
      body: data as never,
    });
    setResult((response.data ?? null) as Record<string, unknown> | null);
    return response.data;
  }, []);

  const activate = useSave(
    async () => (await api.client.POST("/test-definitions/{definition_id}:activate", { params: { path: { definition_id: params.definitionId } } })).data,
    [detailKey, DEFINITIONS_KEY],
    () => {
      setActivating(false);
      toast.success(t("common.saved"));
    },
  );

  const canConfigure = session.can("test_definition", "configure");

  return (
    <div className="flex flex-col gap-4">
      <PageHeader
        title={record ? `${record.code} — ${labelOf(record)}` : params.definitionId}
        subtitle={record?.method_ref}
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
            <Button variant="outline" onClick={() => void navigate({ to: "/catalog/test-definitions" })}>
              {t("common.back")}
            </Button>
            {record?.status === "DRAFT" && canConfigure && (
              <Button onClick={() => setActivating(true)} leftIcon={<Play className="size-4" aria-hidden />}>
                {t("numbering.activate")}
              </Button>
            )}
          </>
        }
      />

      {record?.status === "ACTIVE" && <Alert tone="info">{t("numbering.superseded")}</Alert>}

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <div className="flex flex-col gap-4">
          <Card title={t("common.details")}>
            <DescriptionList
              items={[
                { label: "unit", value: record?.unit_under_test },
                { label: "method", value: record?.method_ref },
                { label: t("nav.admin.specimen_types"), value: (record?.specimen_type_codes ?? []).join(", ") || "—" },
                { label: "scheduling", value: String((record?.scheduling as { type?: string })?.type ?? "—") },
              ]}
            />
          </Card>

          <Card title="inputs">
            <FieldList rows={record?.inputs ?? []} empty={t("common.empty_title")} />
          </Card>
          <Card title="computed">
            <FieldList rows={record?.computed ?? []} empty={t("common.empty_title")} />
          </Card>
          <Card title="aggregates">
            <FieldList rows={record?.aggregates ?? []} empty={t("common.empty_title")} />
          </Card>
        </div>

        <div className="flex flex-col gap-4">
          <Card
            title={
              <span className="flex items-center gap-2">
                <FlaskConical className="size-4 text-primary" aria-hidden />
                sandbox
              </span>
            }
          >
            <div className="flex flex-col gap-3">
              <Textarea value={sample} onChange={(e) => setSample(e.target.value)} rows={10} className="tabular" aria-label="sandbox" />
              <Button onClick={() => run.mutate(undefined as never)} loading={run.isPending} leftIcon={<Play className="size-4" aria-hidden />} disabled={!canConfigure}>
                {t("common.preview")}
              </Button>
              {result && <pre className="max-h-96 overflow-auto rounded-card border border-line bg-subtle p-3 text-xs">{JSON.stringify(result, null, 2)}</pre>}
            </div>
          </Card>
        </div>
      </div>

      <ConfirmDialog
        open={activating}
        onOpenChange={setActivating}
        title={t("numbering.activate_confirm")}
        consequences={t("numbering.activate_consequences")}
        confirmLabel={t("numbering.activate")}
        cancelLabel={t("common.cancel")}
        loading={activate.isPending}
        onConfirm={() => activate.mutate(undefined as never)}
      />
    </div>
  );
}

/** The `{code, label, unit, formula}` rows a definition is made of, rendered as a compact table. */
function FieldList({ rows, empty }: { rows: Record<string, unknown>[]; empty: string }) {
  if (rows.length === 0) return <p className="text-sm text-muted">{empty}</p>;
  return (
    <ul className="flex flex-col divide-y divide-line">
      {rows.map((row, index) => (
        <li key={index} className="flex items-baseline gap-2 py-1.5">
          <code className="text-sm font-medium">{String(row["code"] ?? row["name"] ?? index)}</code>
          {row["unit"] ? <span className="text-xs text-muted">{String(row["unit"])}</span> : null}
          {row["formula"] ? <code className="truncate text-xs text-muted">{String(row["formula"])}</code> : null}
        </li>
      ))}
    </ul>
  );
}

/* ------------------------------------------- not yet served by the API */

/**
 * Equipment classes and phase templates belong to the assets and delivery epics (SPEC §32,
 * phases 4 and 2.5): the models and endpoints do not exist yet, so these screens say so rather
 * than presenting an empty table that looks like a configuration problem.
 */
function NotYetAvailable({ title, epic }: { title: string; epic: string }) {
  const { t } = useTranslation();
  return (
    <div className="flex flex-col gap-4">
      <PageHeader title={title} />
      <EmptyState title={title} hint={`${t("common.empty_hint")} — ${epic}`} />
    </div>
  );
}

export function EquipmentClassesPage() {
  const { t } = useTranslation();
  return <NotYetAvailable title={t("nav.admin.equipment_classes")} epic="E4.1" />;
}

export function PhaseTemplatesPage() {
  const { t } = useTranslation();
  return <NotYetAvailable title={t("nav.admin.phase_templates")} epic="E4.4" />;
}
