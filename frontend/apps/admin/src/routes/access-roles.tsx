/**
 * Roles, the permission matrix and "view as" (SPEC §23.2, §9.2, Appendix T).
 *
 * A grant is a `(resource, action, scope)` triple. The matrix is the only screen where all three
 * are visible at once, which is what makes an over-broad role obvious: a column of `ALL_BRANCHES`
 * where the rest of the role reads `OWN_BRANCH` stands out at a glance.
 *
 * The axes come from the server's own catalogue rather than a copy in the console, so the editor
 * can never offer a triple that `validate_grant` would reject. Edits are staged locally and
 * written in one `PUT`, because a role that is half-saved is a role that is briefly wrong.
 */
import { useApi } from "@mizan/api-client";
import { useSession } from "@mizan/app-kit";
import { useTranslation } from "@mizan/i18n";
import {
  Alert,
  Badge,
  Button,
  Card,
  Checkbox,
  DescriptionList,
  Dialog,
  FormField,
  Input,
  LabelsInput,
  MatrixGrid,
  PageHeader,
  SearchInput,
  Select,
  Textarea,
  Tooltip,
  useToast,
  type ColumnDef,
} from "@mizan/ui";
import { useNavigate, useParams } from "@tanstack/react-router";
import { Copy, ShieldAlert } from "lucide-react";
import { useCallback, useMemo, useState } from "react";

import { ListPage, RecordDrawer, useList, useSave, textOf } from "../lib/resource";

type Grant = { resource: string; action: string; scope: string; field_groups: string[] };
type Role = {
  id: string;
  code: string;
  labels: Record<string, string>;
  description: string;
  is_template: boolean;
  status: string;
  grants: Grant[];
  memberships_count: number;
};
type Catalogue = {
  resources: string[];
  actions: string[];
  scopes: string[];
  field_groups: Record<string, string[]>;
  configuration_resources: string[];
  step_up_actions: string[];
};
type User = { id: string; email: string; display_name: string };
type ResolvedGrant = Grant & { role: string; branch_id: string | null; department_id: string | null };

const ROLES_KEY = ["roles", "list", {}];

function useCatalogue(enabled = true) {
  const api = useApi();
  return useList<Catalogue>(
    ["permission-catalogue"],
    async () => {
      const result = (await api.client.GET("/permission-catalogue")).data;
      return result ? [result as Catalogue] : [];
    },
    { enabled },
  );
}

function roleName(role: Role | undefined): string {
  return role?.labels?.["fr"] || role?.labels?.["en"] || role?.code || "";
}

/* ------------------------------------------------------------------ roles */

export function RolesPage() {
  const { t } = useTranslation();
  const api = useApi();
  const session = useSession();
  const toast = useToast();
  const navigate = useNavigate();
  const roles = useList<Role>(ROLES_KEY, async () => (await api.client.GET("/roles")).data as Role[] | undefined, { enabled: session.can("role", "view") });

  const [editing, setEditing] = useState<Role | null>(null);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ code: "", labels: { fr: "", en: "" }, description: "" });

  const save = useSave(
    async () => {
      if (editing) {
        return (await api.client.PATCH("/roles/{role_id}", {
          params: { path: { role_id: editing.id } },
          body: { labels: form.labels, description: form.description } as never,
        })).data;
      }
      return (await api.client.POST("/roles", { body: { code: form.code, labels: form.labels, description: form.description, grants: [] } as never })).data;
    },
    [ROLES_KEY],
    () => {
      setOpen(false);
      toast.success(t("common.saved"));
    },
  );

  /*
   * Duplicating needs a new code and a new label — a copy sharing either would be impossible to
   * tell apart in the assignment list — so it asks rather than cloning silently.
   */
  const [duplicating, setDuplicating] = useState<Role | null>(null);
  const [copy, setCopy] = useState({ code: "", labels: { fr: "", en: "" } });

  const duplicate = useSave(
    async (role: Role) =>
      (await api.client.POST("/roles/{role_id}:duplicate", {
        params: { path: { role_id: role.id }, query: { code: copy.code } },
        body: { labels: copy.labels } as never,
      })).data,
    [ROLES_KEY],
    () => {
      setDuplicating(null);
      toast.success(t("common.saved"));
    },
  );

  const columns: ColumnDef<Role, unknown>[] = [
    { id: "code", header: t("common.code"), accessorKey: "code", cell: (c) => <span className="font-medium tabular">{textOf(c.getValue())}</span> },
    { id: "label", header: t("common.label"), accessorFn: (row) => roleName(row) },
    { id: "description", header: t("common.description"), accessorKey: "description" },
    {
      id: "grants",
      header: t("access.permissions"),
      accessorFn: (row) => row.grants?.length ?? 0,
      cell: (c) => <span className="tabular">{textOf(c.getValue())}</span>,
    },
    {
      id: "memberships_count",
      header: t("nav.admin.memberships"),
      accessorKey: "memberships_count",
      cell: (c) => <span className="tabular">{textOf(c.getValue())}</span>,
    },
    {
      id: "is_template",
      header: "",
      enableSorting: false,
      cell: (c) => (c.row.original.is_template ? <Badge tone="slate">{t("access.builtin")}</Badge> : null),
    },
    {
      id: "actions",
      header: "",
      enableSorting: false,
      cell: (c) => {
        const role = c.row.original;
        return (
          <div className="flex justify-end gap-1">
            {session.can("role", "configure") && (
              <Tooltip content={t("access.duplicate")}>
                <Button
                  variant="ghost"
                  size="icon-sm"
                  aria-label={t("access.duplicate")}
                  onClick={(e) => {
                    e.stopPropagation();
                    setDuplicating(role);
                    setCopy({ code: `${role.code}_COPY`, labels: { fr: t("access.duplicate_of", { name: roleName(role) }), en: "" } });
                  }}
                >
                  <Copy className="size-4" aria-hidden />
                </Button>
              </Tooltip>
            )}
            <Button
              variant="ghost"
              size="sm"
              onClick={(e) => {
                e.stopPropagation();
                void navigate({ to: "/access/roles/$roleId/matrix", params: { roleId: role.id } });
              }}
            >
              {t("nav.admin.matrix")}
            </Button>
          </div>
        );
      },
    },
  ];

  return (
    <>
      <ListPage
        title={t("nav.admin.roles")}
        subtitle={t("access.builtin_hint")}
        columns={columns}
        rows={roles.data}
        loading={roles.isPending}
        error={roles.error}
        onRetry={() => void roles.refetch()}
        getRowId={(row) => row.id}
        searchable={(row, needle) => `${row.code} ${roleName(row)} ${row.description}`.toLowerCase().includes(needle)}
        onRowClick={(row) => {
          setEditing(row);
          setForm({ code: row.code, labels: { fr: row.labels?.["fr"] ?? "", en: row.labels?.["en"] ?? "" }, description: row.description });
          setOpen(true);
        }}
        onCreate={() => {
          setEditing(null);
          setForm({ code: "", labels: { fr: "", en: "" }, description: "" });
          setOpen(true);
        }}
        canCreate={session.can("role", "configure")}
      />

      <RecordDrawer
        open={open}
        onOpenChange={setOpen}
        title={editing ? `${editing.code} — ${t("common.edit")}` : t("common.new")}
        onSubmit={() => save.mutate(undefined as never)}
        saving={save.isPending}
        extraActions={
          editing && (
            <Button variant="outline" onClick={() => void navigate({ to: "/access/roles/$roleId/matrix", params: { roleId: editing.id } })}>
              {t("nav.admin.matrix")}
            </Button>
          )
        }
      >
        {editing?.is_template && <Alert tone="info">{t("access.builtin_hint")}</Alert>}
        <FormField label={t("common.code")} required error={save.fieldErrors["code"]}>
          {/* Grants and audit entries reference the code, so it is fixed once the role exists. */}
          <Input value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value.toUpperCase() })} disabled={!!editing} />
        </FormField>
        <FormField label={t("common.labels")} required error={save.fieldErrors["labels"]}>
          <LabelsInput value={form.labels} onChange={(labels) => setForm({ ...form, labels: { fr: labels.fr ?? "", en: labels.en ?? "" } })} />
        </FormField>
        <FormField label={t("common.description")} error={save.fieldErrors["description"]}>
          <Textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} rows={3} />
        </FormField>
      </RecordDrawer>

      <Dialog
        open={!!duplicating}
        onOpenChange={(next) => !next && setDuplicating(null)}
        title={`${t("access.duplicate")} — ${roleName(duplicating ?? undefined)}`}
        description={t("access.builtin_hint")}
        size="sm"
        closeLabel={t("common.close")}
        footer={
          <>
            <Button variant="outline" onClick={() => setDuplicating(null)} disabled={duplicate.isPending}>
              {t("common.cancel")}
            </Button>
            <Button onClick={() => duplicating && duplicate.mutate(duplicating)} loading={duplicate.isPending} disabled={!copy.code}>
              {t("access.duplicate")}
            </Button>
          </>
        }
      >
        <div className="flex flex-col gap-4">
          <FormField label={t("common.code")} required error={duplicate.fieldErrors["code"]}>
            <Input value={copy.code} onChange={(e) => setCopy({ ...copy, code: e.target.value.toUpperCase() })} />
          </FormField>
          <FormField label={t("common.labels")} required error={duplicate.fieldErrors["labels"]}>
            <LabelsInput value={copy.labels} onChange={(labels) => setCopy({ ...copy, labels: { fr: labels.fr ?? "", en: labels.en ?? "" } })} />
          </FormField>
        </div>
      </Dialog>
    </>
  );
}

/* ----------------------------------------------------------------- matrix */

/** A grant keyed for O(1) lookup while the grid renders a few thousand cells. */
// `::` cannot occur inside a resource or action, which are lowercase identifiers.
const grantKey = (resource: string, action: string) => `${resource}::${action}`;

export function RoleMatrixPage() {
  const { t } = useTranslation();
  const api = useApi();
  const session = useSession();
  const toast = useToast();
  const navigate = useNavigate();
  const params = useParams({ strict: false }) as { roleId: string };

  const roles = useList<Role>(ROLES_KEY, async () => (await api.client.GET("/roles")).data as Role[] | undefined, { enabled: session.can("role", "view") });
  const catalogue = useCatalogue(session.can("role", "view"));
  const role = roles.data?.find((r) => r.id === params.roleId);
  const cat = catalogue.data?.[0];

  /*
   * The draft carries the role it belongs to. Navigating to another role's matrix then makes it
   * stale by construction, which is safer than resetting it from an effect: there is no render
   * in between where one role's edits could be shown against another role's baseline.
   */
  const [draft, setDraft] = useState<{ roleId: string; grants: Map<string, Grant> } | null>(null);
  const [filter, setFilter] = useState("");
  const [onlyGranted, setOnlyGranted] = useState(false);

  // The server's grants are the baseline; the draft only exists once something is changed.
  const baseline = useMemo(() => new Map((role?.grants ?? []).map((g) => [grantKey(g.resource, g.action), g])), [role]);
  const pending = draft?.roleId === params.roleId ? draft.grants : null;
  const grants = pending ?? baseline;

  const mutate = useCallback(
    (update: (next: Map<string, Grant>) => void) => {
      setDraft((current) => {
        const next = new Map(current?.roleId === params.roleId ? current.grants : baseline);
        update(next);
        return { roleId: params.roleId, grants: next };
      });
    },
    [baseline, params.roleId],
  );

  const save = useSave(
    async () =>
      (await api.client.PUT("/roles/{role_id}/grants", {
        params: { path: { role_id: params.roleId } },
        body: { grants: [...grants.values()] } as never,
      })).data,
    [ROLES_KEY],
    () => {
      setDraft(null);
      toast.success(t("common.saved"));
    },
  );

  const editable = session.can("role", "configure") && !role?.is_template;
  const dirty = pending !== null;

  const resources = useMemo(() => {
    const all = cat?.resources ?? [];
    const needle = filter.trim().toLowerCase();
    return all
      .filter((resource) => !needle || resource.includes(needle))
      .filter((resource) => !onlyGranted || (cat?.actions ?? []).some((action) => grants.has(grantKey(resource, action))));
  }, [cat, filter, onlyGranted, grants]);

  const actions = cat?.actions ?? [];
  const defaultScope = cat?.scopes?.[0] ?? "OWN_BRANCH";

  return (
    <div className="flex flex-col gap-4">
      <PageHeader
        title={`${t("nav.admin.matrix")} — ${roleName(role)}`}
        subtitle={t("access.matrix_hint")}
        badges={
          <>
            {role?.is_template && <Badge tone="slate">{t("access.builtin")}</Badge>}
            <Badge tone="primary">{t("common.results", { count: grants.size })}</Badge>
          </>
        }
        actions={
          <>
            <Button variant="outline" onClick={() => void navigate({ to: "/access/roles" })}>
              {t("common.back")}
            </Button>
            {editable && (
              <>
                {dirty && (
                  <Button variant="ghost" onClick={() => setDraft(null)}>
                    {t("common.cancel")}
                  </Button>
                )}
                <Button onClick={() => save.mutate(undefined as never)} loading={save.isPending} disabled={!dirty}>
                  {t("common.save")}
                </Button>
              </>
            )}
          </>
        }
      />

      {role?.is_template && <Alert tone="info">{t("access.builtin_hint")}</Alert>}

      <div className="flex flex-wrap items-center gap-3">
        <SearchInput
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          onClear={() => setFilter("")}
          placeholder={t("access.resource")}
          aria-label={t("access.resource")}
          className="w-64"
        />
        <Checkbox checked={onlyGranted} onCheckedChange={setOnlyGranted} label={t("access.granted")} />
        {dirty && <Badge tone="amber">{t("common.unsaved_changes")}</Badge>}
      </div>

      {catalogue.isPending || roles.isPending ? (
        <Card>
          <p className="text-sm text-muted">{t("common.loading")}</p>
        </Card>
      ) : (
        <MatrixGrid
          rows={resources}
          columns={actions}
          rowKey={(resource) => resource}
          columnKey={(action) => action}
          rowLabel={(resource) => (
            <span className="flex items-center gap-1.5">
              {resource}
              {cat?.configuration_resources.includes(resource) && (
                <Tooltip content={t("common.settings")}>
                  <span className="size-1.5 rounded-full bg-info" aria-hidden />
                </Tooltip>
              )}
            </span>
          )}
          columnLabel={(action) => (
            <span className="flex items-center justify-center gap-1">
              {action}
              {/* Step-up actions demand MFA at use time; flagging them here prevents a role that
                  quietly cannot be exercised by a member who has not enrolled. */}
              {cat?.step_up_actions.includes(action) && (
                <Tooltip content="MFA">
                  <ShieldAlert className="size-3 text-warning" aria-label="MFA" />
                </Tooltip>
              )}
            </span>
          )}
          cell={(resource, action) => {
            const key = grantKey(resource, action);
            const grant = grants.get(key);
            return (
              <div className="flex items-center justify-center gap-1">
                <Checkbox
                  checked={!!grant}
                  disabled={!editable}
                  aria-label={`${resource} ${action}`}
                  onCheckedChange={(checked) =>
                    mutate((next) => {
                      if (checked) next.set(key, { resource, action, scope: defaultScope, field_groups: [] });
                      else next.delete(key);
                    })
                  }
                />
                {/* The scope only exists once the action is granted, so it appears with it. */}
                {grant && (
                  <Select
                    value={grant.scope}
                    onValueChange={(scope) => mutate((next) => next.set(key, { ...grant, scope }))}
                    disabled={!editable}
                    options={(cat?.scopes ?? []).map((scope) => ({ value: scope, label: scope }))}
                    className="h-7 w-36 text-xs"
                    aria-describedby={undefined}
                  />
                )}
              </div>
            );
          }}
        />
      )}
    </div>
  );
}

/* ---------------------------------------------------------------- view as */

export function ViewAsPage() {
  const { t } = useTranslation();
  const api = useApi();
  const session = useSession();
  const [userId, setUserId] = useState("");

  const users = useList<User>(
    ["users", "list", { limit: 200 }],
    async () => (await api.client.GET("/users", { params: { query: { limit: 200 } } })).data?.items as User[] | undefined,
    { enabled: session.can("user", "view") },
  );

  const permissions = useList<ResolvedGrant>(
    ["users", userId, "effective-permissions"],
    async () => (await api.client.GET("/users/{user_id}/effective-permissions", { params: { path: { user_id: userId } } })).data?.grants as ResolvedGrant[] | undefined,
    { enabled: !!userId && session.can("user", "impersonate_view") },
  );

  // Grouped by resource: a flat list of 300 triples answers no question anyone actually has.
  const byResource = useMemo(() => {
    const groups = new Map<string, ResolvedGrant[]>();
    for (const grant of permissions.data ?? []) {
      const list = groups.get(grant.resource) ?? [];
      list.push(grant);
      groups.set(grant.resource, list);
    }
    return [...groups.entries()].sort(([a], [b]) => a.localeCompare(b));
  }, [permissions.data]);

  const selected = users.data?.find((u) => u.id === userId);

  return (
    <div className="flex flex-col gap-4">
      <PageHeader title={t("access.view_as")} subtitle={t("access.view_as_hint")} />
      <Card>
        <FormField label={t("access.member")} className="max-w-md">
          <Select
            value={userId}
            onValueChange={setUserId}
            placeholder={t("common.select_placeholder")}
            options={(users.data ?? []).map((u) => ({ value: u.id, label: u.display_name || u.email }))}
          />
        </FormField>
      </Card>

      {userId && (
        <Card title={t("access.effective_permissions")}>
          {permissions.isPending ? (
            <p className="text-sm text-muted">{t("common.loading")}</p>
          ) : byResource.length === 0 ? (
            <p className="text-sm text-muted">{t("common.empty_title")}</p>
          ) : (
            <div className="flex flex-col gap-4">
              <DescriptionList
                items={[
                  { label: t("access.member"), value: selected?.display_name || selected?.email },
                  { label: t("access.permissions"), value: <span className="tabular">{permissions.data?.length ?? 0}</span> },
                  { label: t("access.resource"), value: <span className="tabular">{byResource.length}</span> },
                ]}
                columns={3}
              />
              <ul className="flex flex-col gap-2">
                {byResource.map(([resource, list]) => (
                  <li key={resource} className="rounded-card border border-line p-3">
                    <p className="mb-1.5 font-medium">{resource}</p>
                    <div className="flex flex-wrap gap-1.5">
                      {list.map((grant, index) => (
                        <Badge key={`${grant.action}-${grant.scope}-${index}`} tone={grant.scope === "ALL_BRANCHES" ? "amber" : "teal"}>
                          {grant.action} · {grant.scope}
                        </Badge>
                      ))}
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </Card>
      )}
    </div>
  );
}
