/**
 * Users and assignments (SPEC §23.2, §9).
 *
 * A user is an identity; what they may do comes entirely from their assignments — a role, on a
 * branch, optionally narrowed to a department. Keeping those two screens separate is deliberate:
 * an account outlives the roles it is given, and revoking access should never mean deleting a
 * person along with the audit trail that points at them.
 *
 * New staff accounts are created with a temporary password that must be changed at first
 * sign-in (E0.4); the console never shows or stores a permanent one.
 */
import { useApi } from "@mizan/api-client";
import { useSession } from "@mizan/app-kit";
import { currentLocale, formatDateTime, useTranslation } from "@mizan/i18n";
import {
  Badge,
  Button,
  ConfirmDialog,
  DropdownMenu,
  FormField,
  Input,
  Select,
  Tooltip,
  useToast,
  type ColumnDef,
} from "@mizan/ui";
import { useQuery } from "@tanstack/react-query";
import { MoreHorizontal, ShieldCheck, ShieldOff } from "lucide-react";
import { useMemo, useState } from "react";

import { ListPage, RecordDrawer, useList, useSave, textOf } from "../lib/resource";

type User = {
  id: string;
  email: string;
  display_name: string;
  locale: string;
  realm: string;
  status: string;
  mfa_enrolled: boolean;
  must_change_password: boolean;
  last_login: string | null;
};

type Membership = {
  id: string;
  user_id: string;
  role_id: string;
  role_code: string;
  branch_id: string | null;
  department_id: string | null;
  status: string;
};

type Role = { id: string; code: string; labels: Record<string, string>; description: string; is_template: boolean; status: string; memberships_count: number };
type Branch = { id: string; code: string; trade_name: string; legal_name: string };
type Department = { id: string; branch_id: string; code: string; labels: Record<string, string> };

const USERS_KEY = ["users", "list", { limit: 200 }];
const MEMBERSHIPS_KEY = ["memberships", "list", {}];

export function useRoles(enabled = true) {
  const api = useApi();
  return useList<Role>(["roles", "list", {}], async () => (await api.client.GET("/roles")).data as Role[] | undefined, { enabled });
}

function useBranchOptions() {
  const api = useApi();
  const session = useSession();
  const branches = useList<Branch>(["branches", "list", {}], async () => (await api.client.GET("/branches")).data as Branch[] | undefined, {
    enabled: session.can("branch", "view"),
  });
  const names = useMemo(() => new Map((branches.data ?? []).map((b) => [b.id, b.trade_name || b.legal_name || b.code])), [branches.data]);
  return { branches: branches.data ?? [], names };
}

function statusBadge(status: string, t: (key: string) => string) {
  const tone = status === "ACTIVE" ? "success" : status === "DISABLED" ? "danger" : "warning";
  return <Badge tone={tone}>{status === "ACTIVE" ? t("common.active") : status === "DISABLED" ? t("common.inactive") : status}</Badge>;
}

/* ------------------------------------------------------------------ users */

const REALMS = ["STAFF", "CLIENT"];

export function UsersPage() {
  const { t } = useTranslation();
  const api = useApi();
  const session = useSession();
  const toast = useToast();

  const users = useQuery({
    queryKey: USERS_KEY,
    queryFn: async () => ((await api.client.GET("/users", { params: { query: { limit: 200 } } })).data?.items ?? []) as User[],
    enabled: session.can("user", "view"),
  });

  const [editing, setEditing] = useState<User | null>(null);
  const [open, setOpen] = useState(false);
  const [disabling, setDisabling] = useState<User | null>(null);
  const [form, setForm] = useState({ email: "", display_name: "", locale: "fr", realm: "STAFF", temporary_password: "", status: "ACTIVE" });

  const save = useSave(
    async () => {
      if (editing) {
        return (await api.client.PATCH("/users/{user_id}", {
          params: { path: { user_id: editing.id } },
          body: { display_name: form.display_name, locale: form.locale, status: form.status } as never,
        })).data;
      }
      return (await api.client.POST("/users", {
        body: {
          email: form.email,
          display_name: form.display_name,
          locale: form.locale,
          realm: form.realm,
          temporary_password: form.temporary_password || undefined,
        } as never,
      })).data;
    },
    [USERS_KEY],
    () => {
      setOpen(false);
      toast.success(t("common.saved"));
    },
  );

  const disable = useSave(
    async (user: User) => (await api.client.POST("/users/{user_id}:disable", { params: { path: { user_id: user.id } } })).data,
    [USERS_KEY],
    () => {
      setDisabling(null);
      toast.success(t("common.saved"));
    },
  );

  const columns: ColumnDef<User, unknown>[] = [
    {
      id: "display_name",
      header: t("access.display_name"),
      accessorFn: (row) => row.display_name || row.email,
      cell: (c) => {
        const row = c.row.original;
        return (
          <div className="flex items-center gap-2">
            <span className="font-medium">{row.display_name || "—"}</span>
            {/* Security signals belong next to the name, not in a column nobody scrolls to. */}
            {row.mfa_enrolled ? (
              <Tooltip content="MFA">
                <ShieldCheck className="size-4 text-success" aria-label="MFA" />
              </Tooltip>
            ) : (
              <Tooltip content="MFA">
                <ShieldOff className="size-4 text-muted" aria-label="no MFA" />
              </Tooltip>
            )}
            {row.must_change_password && <Badge tone="amber">{t("access.force_password_change")}</Badge>}
          </div>
        );
      },
    },
    { id: "email", header: t("auth.email"), accessorKey: "email" },
    { id: "realm", header: t("access.realm"), accessorKey: "realm", cell: (c) => <Badge tone={c.getValue() === "STAFF" ? "blue" : "violet"}>{textOf(c.getValue())}</Badge> },
    { id: "locale", header: t("common.locale"), accessorKey: "locale" },
    {
      id: "last_login",
      header: t("access.last_login"),
      accessorKey: "last_login",
      cell: (c) => (c.getValue() ? <span className="tabular">{formatDateTime(String(c.getValue()), currentLocale())}</span> : <span className="text-muted">{t("access.never")}</span>),
    },
    { id: "status", header: t("common.status"), accessorKey: "status", cell: (c) => statusBadge(textOf(c.getValue()), t) },
    {
      id: "actions",
      header: "",
      enableSorting: false,
      cell: (c) => {
        const row = c.row.original;
        if (!session.can("user", "edit")) return null;
        return (
          <DropdownMenu
            trigger={
              <Button variant="ghost" size="icon-sm" aria-label={t("common.actions")} onClick={(e) => e.stopPropagation()}>
                <MoreHorizontal className="size-4" aria-hidden />
              </Button>
            }
            items={[
              {
                key: "edit",
                label: t("common.edit"),
                onSelect: () => {
                  setEditing(row);
                  setForm({ email: row.email, display_name: row.display_name, locale: row.locale, realm: row.realm, temporary_password: "", status: row.status });
                  setOpen(true);
                },
              },
              ...(row.status === "ACTIVE"
                ? [{ key: "disable", label: t("access.disable"), destructive: true, onSelect: () => setDisabling(row) }]
                : []),
            ]}
          />
        );
      },
    },
  ];

  return (
    <>
      <ListPage
        title={t("nav.admin.users")}
        columns={columns}
        rows={users.data}
        loading={users.isPending}
        error={users.error}
        onRetry={() => void users.refetch()}
        getRowId={(row) => row.id}
        searchable={(row, needle) => `${row.email} ${row.display_name}`.toLowerCase().includes(needle)}
        createLabel={t("access.invite")}
        onCreate={() => {
          setEditing(null);
          setForm({ email: "", display_name: "", locale: "fr", realm: "STAFF", temporary_password: "", status: "ACTIVE" });
          setOpen(true);
        }}
        canCreate={session.can("user", "create")}
      />

      <RecordDrawer
        open={open}
        onOpenChange={setOpen}
        title={editing ? editing.display_name || editing.email : t("access.invite")}
        onSubmit={() => save.mutate(undefined as never)}
        saving={save.isPending}
      >
        <FormField label={t("auth.email")} required error={save.fieldErrors["email"]}>
          {/* The e-mail is the identity: changing it would silently re-point every audit entry. */}
          <Input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} disabled={!!editing} autoComplete="off" />
        </FormField>
        <FormField label={t("access.display_name")} error={save.fieldErrors["display_name"]}>
          <Input value={form.display_name} onChange={(e) => setForm({ ...form, display_name: e.target.value })} />
        </FormField>
        <div className="grid grid-cols-2 gap-4">
          <FormField label={t("common.locale")}>
            <Select
              value={form.locale}
              onValueChange={(value) => setForm({ ...form, locale: value })}
              options={[
                { value: "fr", label: t("common.language_fr") },
                { value: "en", label: t("common.language_en") },
              ]}
            />
          </FormField>
          <FormField label={t("access.realm")}>
            <Select value={form.realm} onValueChange={(value) => setForm({ ...form, realm: value })} disabled={!!editing} options={REALMS.map((realm) => ({ value: realm, label: realm }))} />
          </FormField>
        </div>
        {!editing && (
          <FormField label={t("access.temporary_password")} help={t("access.temporary_password_help")} error={save.fieldErrors["temporary_password"]}>
            <Input
              type="text"
              value={form.temporary_password}
              onChange={(e) => setForm({ ...form, temporary_password: e.target.value })}
              autoComplete="off"
              className="tabular"
            />
          </FormField>
        )}
        {editing && (
          <FormField label={t("common.status")}>
            <Select
              value={form.status}
              onValueChange={(value) => setForm({ ...form, status: value })}
              options={[
                { value: "ACTIVE", label: t("common.active") },
                { value: "DISABLED", label: t("common.inactive") },
              ]}
            />
          </FormField>
        )}
      </RecordDrawer>

      <ConfirmDialog
        open={!!disabling}
        onOpenChange={(next) => !next && setDisabling(null)}
        title={`${t("access.disable")} — ${disabling?.display_name || disabling?.email}`}
        consequences={t("access.revoke_consequences")}
        confirmLabel={t("access.disable")}
        cancelLabel={t("common.cancel")}
        destructive
        loading={disable.isPending}
        onConfirm={() => disabling && disable.mutate(disabling)}
      />
    </>
  );
}

/* ------------------------------------------------------------ memberships */

export function MembershipsPage() {
  const { t } = useTranslation();
  const api = useApi();
  const session = useSession();
  const toast = useToast();
  const { branches, names: branchNames } = useBranchOptions();
  const roles = useRoles(session.can("role", "view"));

  const users = useQuery({
    queryKey: USERS_KEY,
    queryFn: async () => ((await api.client.GET("/users", { params: { query: { limit: 200 } } })).data?.items ?? []) as User[],
    enabled: session.can("user", "view"),
  });
  const memberships = useQuery({
    queryKey: MEMBERSHIPS_KEY,
    queryFn: async () => ((await api.client.GET("/memberships", { params: { query: { limit: 200 } } })).data?.items ?? []) as Membership[],
    enabled: session.can("user", "view"),
  });
  const departments = useList<Department>(["departments", "list", {}], async () => (await api.client.GET("/departments")).data as Department[] | undefined, {
    enabled: session.can("department", "view"),
  });

  const userNames = useMemo(() => new Map((users.data ?? []).map((u) => [u.id, u.display_name || u.email])), [users.data]);
  const roleNames = useMemo(() => new Map((roles.data ?? []).map((r) => [r.id, r.labels?.["fr"] || r.labels?.["en"] || r.code])), [roles.data]);

  const [open, setOpen] = useState(false);
  const [revoking, setRevoking] = useState<Membership | null>(null);
  const [form, setForm] = useState({ user_id: "", role_id: "", branch_id: "", department_id: "" });

  const save = useSave(
    async () =>
      (await api.client.POST("/memberships", {
        body: {
          user_id: form.user_id,
          role_id: form.role_id,
          branch_id: form.branch_id || null,
          department_id: form.department_id || null,
        } as never,
      })).data,
    [MEMBERSHIPS_KEY],
    () => {
      setOpen(false);
      toast.success(t("common.saved"));
    },
  );

  const revoke = useSave(
    async (membership: Membership) => (await api.client.DELETE("/memberships/{membership_id}", { params: { path: { membership_id: membership.id } } })).data,
    [MEMBERSHIPS_KEY],
    () => {
      setRevoking(null);
      toast.success(t("common.saved"));
    },
  );

  // Only the chosen branch's departments are offerable; anything else is a grant that can never fire.
  const departmentOptions = (departments.data ?? []).filter((d) => !form.branch_id || d.branch_id === form.branch_id);

  const columns: ColumnDef<Membership, unknown>[] = [
    { id: "user", header: t("access.member"), accessorFn: (row) => userNames.get(row.user_id) ?? row.user_id, cell: (c) => <span className="font-medium">{textOf(c.getValue())}</span> },
    { id: "role", header: t("access.role"), accessorFn: (row) => roleNames.get(row.role_id) ?? row.role_code, cell: (c) => <Badge tone="primary">{textOf(c.getValue())}</Badge> },
    {
      id: "branch",
      header: t("common.branch"),
      accessorFn: (row) => (row.branch_id ? (branchNames.get(row.branch_id) ?? row.branch_id) : ""),
      cell: (c) => (c.getValue() ? textOf(c.getValue()) : <span className="text-muted">{t("access.all_branches")}</span>),
    },
    {
      id: "department",
      header: t("common.department"),
      accessorFn: (row) => row.department_id ?? "",
      cell: (c) => {
        const id = textOf(c.getValue());
        if (!id) return <span className="text-muted">—</span>;
        const department = departments.data?.find((d) => d.id === id);
        return department?.labels?.["fr"] ?? department?.code ?? id;
      },
    },
    { id: "status", header: t("common.status"), accessorKey: "status", cell: (c) => statusBadge(textOf(c.getValue()), t) },
    {
      id: "actions",
      header: "",
      enableSorting: false,
      cell: (c) =>
        session.can("user", "edit") ? (
          <Button
            variant="ghost"
            size="sm"
            className="text-danger"
            onClick={(e) => {
              e.stopPropagation();
              setRevoking(c.row.original);
            }}
          >
            {t("access.revoke")}
          </Button>
        ) : null,
    },
  ];

  return (
    <>
      <ListPage
        title={t("nav.admin.memberships")}
        columns={columns}
        rows={memberships.data}
        loading={memberships.isPending}
        error={memberships.error}
        onRetry={() => void memberships.refetch()}
        getRowId={(row) => row.id}
        searchable={(row, needle) => `${userNames.get(row.user_id) ?? ""} ${row.role_code}`.toLowerCase().includes(needle)}
        onCreate={() => {
          setForm({ user_id: "", role_id: "", branch_id: "", department_id: "" });
          setOpen(true);
        }}
        canCreate={session.can("user", "edit")}
      />

      <RecordDrawer open={open} onOpenChange={setOpen} title={t("access.membership")} onSubmit={() => save.mutate(undefined as never)} saving={save.isPending}>
        <FormField label={t("access.member")} required error={save.fieldErrors["user_id"]}>
          <Select
            value={form.user_id}
            onValueChange={(value) => setForm({ ...form, user_id: value })}
            placeholder={t("common.select_placeholder")}
            options={(users.data ?? []).map((u) => ({ value: u.id, label: u.display_name || u.email }))}
          />
        </FormField>
        <FormField label={t("access.role")} required error={save.fieldErrors["role_id"]}>
          <Select
            value={form.role_id}
            onValueChange={(value) => setForm({ ...form, role_id: value })}
            placeholder={t("common.select_placeholder")}
            options={(roles.data ?? []).map((r) => ({ value: r.id, label: r.labels?.["fr"] || r.code }))}
          />
        </FormField>
        <FormField label={t("common.branch")} help={t("access.all_branches")}>
          <Select
            value={form.branch_id}
            onValueChange={(value) => setForm({ ...form, branch_id: value, department_id: "" })}
            allowEmpty
            emptyLabel={t("access.all_branches")}
            options={branches.map((b) => ({ value: b.id, label: b.trade_name || b.code }))}
          />
        </FormField>
        {form.branch_id && departmentOptions.length > 0 && (
          <FormField label={t("common.department")} optionalLabel={t("common.optional")}>
            <Select
              value={form.department_id}
              onValueChange={(value) => setForm({ ...form, department_id: value })}
              allowEmpty
              emptyLabel={t("common.all")}
              options={departmentOptions.map((d) => ({ value: d.id, label: d.labels?.["fr"] || d.code }))}
            />
          </FormField>
        )}
      </RecordDrawer>

      <ConfirmDialog
        open={!!revoking}
        onOpenChange={(next) => !next && setRevoking(null)}
        title={t("access.revoke_confirm")}
        consequences={t("access.revoke_consequences")}
        confirmLabel={t("access.revoke")}
        cancelLabel={t("common.cancel")}
        destructive
        loading={revoke.isPending}
        onConfirm={() => revoking && revoke.mutate(revoking)}
      />
    </>
  );
}
