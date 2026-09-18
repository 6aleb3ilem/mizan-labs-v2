/**
 * Platform operator screens (SPEC §23.8, §5).
 *
 * These sit above the tenant boundary and are reachable only by a platform operator — an
 * identity with no tenant of its own. They exist so that onboarding a new laboratory and
 * checking the signing keys never require a database session.
 *
 * Nothing here reads tenant data. Tenant creation writes one row and its first administrator;
 * the signing keys are the public half of the QR key set, which is deliberately world-readable
 * (the verification site fetches the same document); health is the readiness probe the load
 * balancer uses.
 */
import { useApi } from "@mizan/api-client";
import { useSession } from "@mizan/app-kit";
import { currentLocale, formatDateTime, useTranslation } from "@mizan/i18n";
import {
  Alert,
  Badge,
  Button,
  Card,
  DescriptionList,
  EmptyState,
  FormField,
  Input,
  PageHeader,
  Spinner,
  useToast,
} from "@mizan/ui";
import { useQuery } from "@tanstack/react-query";
import { Activity, KeyRound, Plus } from "lucide-react";
import { useState } from "react";

import { RecordDrawer, useSave } from "../lib/resource";

type Jwk = { kid?: string; kty?: string; crv?: string; alg?: string; use?: string; [key: string]: unknown };
type TransparencyHead = { tree_size?: number; root_hash?: string; published_at?: string; kid?: string; [key: string]: unknown };

/** Platform screens are invisible to tenant users; this is the guard every one of them shows. */
function OperatorOnly({ children }: { children: React.ReactNode }) {
  const { t } = useTranslation();
  const session = useSession();
  if (session.me?.realm !== "PLATFORM") {
    return <EmptyState title={t("authz.forbidden")} hint={t("authz.forbidden_action", { action: "platform" })} />;
  }
  return <>{children}</>;
}

/* --------------------------------------------------------------- tenants */

export function PlatformTenantsPage() {
  const { t } = useTranslation();
  const api = useApi();
  const toast = useToast();

  const [open, setOpen] = useState(false);
  const [created, setCreated] = useState<{ code: string; name: string } | null>(null);
  const [form, setForm] = useState({ code: "", name: "", admin_email: "", admin_display_name: "", admin_temporary_password: "" });

  const save = useSave(
    async () =>
      (await api.client.POST("/platform/tenants", {
        body: {
          code: form.code,
          name: form.name,
          admin_email: form.admin_email,
          admin_display_name: form.admin_display_name,
          admin_temporary_password: form.admin_temporary_password,
        } as never,
      })).data,
    [],
    () => {
      setOpen(false);
      setCreated({ code: form.code, name: form.name });
      toast.success(t("common.saved"));
    },
  );

  return (
    <OperatorOnly>
      <div className="flex flex-col gap-4">
        <PageHeader
          title={t("nav.admin.tenants")}
          subtitle={t("org.tenant_hint")}
          actions={
            <Button onClick={() => setOpen(true)} leftIcon={<Plus className="size-4" aria-hidden />}>
              {t("common.new")}
            </Button>
          }
        />

        {/*
          There is no list endpoint: a platform operator enumerating every tenant would be a
          cross-tenant read, which the RLS policies exist to make impossible. The screen
          therefore confirms what it created rather than listing what exists.
        */}
        {created ? (
          <Card title={created.name}>
            <DescriptionList
              items={[
                { label: t("common.code"), value: created.code },
                { label: t("access.member"), value: form.admin_email },
                { label: t("access.force_password_change"), value: t("common.yes") },
              ]}
              columns={3}
            />
          </Card>
        ) : (
          <EmptyState title={t("common.empty_title")} hint={t("common.empty_hint")} />
        )}
      </div>

      <RecordDrawer open={open} onOpenChange={setOpen} title={t("common.new")} onSubmit={() => save.mutate(undefined as never)} saving={save.isPending}>
        <div className="grid grid-cols-2 gap-4">
          <FormField label={t("common.code")} required error={save.fieldErrors["code"]}>
            <Input value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value.toUpperCase() })} className="tabular" />
          </FormField>
          <FormField label={t("common.name")} required error={save.fieldErrors["name"]}>
            <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          </FormField>
        </div>
        <FormField label={t("auth.email")} required error={save.fieldErrors["admin_email"]}>
          <Input type="email" value={form.admin_email} onChange={(e) => setForm({ ...form, admin_email: e.target.value })} autoComplete="off" />
        </FormField>
        <FormField label={t("access.display_name")} error={save.fieldErrors["admin_display_name"]}>
          <Input value={form.admin_display_name} onChange={(e) => setForm({ ...form, admin_display_name: e.target.value })} />
        </FormField>
        <FormField label={t("access.temporary_password")} required help={t("access.temporary_password_help")} error={save.fieldErrors["admin_temporary_password"]}>
          <Input
            type="text"
            value={form.admin_temporary_password}
            onChange={(e) => setForm({ ...form, admin_temporary_password: e.target.value })}
            autoComplete="off"
            className="tabular"
          />
        </FormField>
      </RecordDrawer>
    </OperatorOnly>
  );
}

/* ------------------------------------------------------------------ keys */

export function PlatformKeysPage() {
  const { t } = useTranslation();
  const api = useApi();
  const locale = currentLocale();

  const jwks = useQuery({
    queryKey: ["verify", "keys"],
    queryFn: async () => (await api.client.GET("/verify/keys")).data as { keys?: Jwk[] } | undefined,
  });
  const head = useQuery({
    queryKey: ["verify", "transparency", "head"],
    queryFn: async () => (await api.client.GET("/verify/transparency/head")).data as TransparencyHead | null | undefined,
  });

  const keys = jwks.data?.keys ?? [];

  return (
    <OperatorOnly>
      <div className="flex flex-col gap-4">
        <PageHeader title={t("nav.admin.keys")} subtitle={t("verify.keys")} />

        {/* The private halves live in KMS and are never served; this is the set a verifier uses. */}
        <Alert tone="info">{t("verify.keys")}</Alert>

        <Card
          title={
            <span className="flex items-center gap-2">
              <KeyRound className="size-4 text-primary" aria-hidden />
              JWKS
            </span>
          }
        >
          {jwks.isPending ? (
            <Spinner delay={0} label={t("common.loading")} />
          ) : keys.length === 0 ? (
            <p className="text-sm text-muted">{t("common.empty_title")}</p>
          ) : (
            <ul className="flex flex-col gap-2">
              {keys.map((key, index) => (
                <li key={String(key.kid ?? index)} className="rounded-card border border-line p-3">
                  <div className="mb-1 flex flex-wrap items-center gap-2">
                    <code className="tabular text-sm font-medium">{String(key.kid ?? "—")}</code>
                    {key.alg && <Badge tone="blue">{String(key.alg)}</Badge>}
                    {key.crv && <Badge tone="teal">{String(key.crv)}</Badge>}
                    {key.use && <Badge tone="slate">{String(key.use)}</Badge>}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card title={t("verify.transparency")}>
          {head.isPending ? (
            <Spinner delay={0} label={t("common.loading")} />
          ) : !head.data ? (
            <p className="text-sm text-muted">{t("common.empty_title")}</p>
          ) : (
            <DescriptionList
              items={[
                { label: "tree_size", value: <span className="tabular">{String(head.data.tree_size ?? "—")}</span> },
                { label: "published_at", value: head.data.published_at ? formatDateTime(String(head.data.published_at), locale) : "—" },
                { label: "root_hash", value: <code className="tabular break-all text-xs">{String(head.data.root_hash ?? "—")}</code> },
              ]}
              columns={1}
            />
          )}
        </Card>
      </div>
    </OperatorOnly>
  );
}

/* ---------------------------------------------------------------- health */

export function PlatformHealthPage() {
  const { t } = useTranslation();
  const api = useApi();

  /* Polled rather than fetched once: this page is left open on a second monitor during a
     deploy, and a stale "ready" is worse than no answer. */
  const ready = useQuery({
    queryKey: ["platform", "ready"],
    queryFn: async () => (await api.client.GET("/ready")).data as { status?: string; database?: boolean } | undefined,
    refetchInterval: 15_000,
    retry: false,
  });

  const ok = ready.data?.status === "ready";

  return (
    <OperatorOnly>
      <div className="flex flex-col gap-4">
        <PageHeader
          title={t("nav.admin.health")}
          badges={<Badge tone={ready.isError ? "danger" : ok ? "success" : "warning"}>{ready.isError ? "unreachable" : (ready.data?.status ?? "…")}</Badge>}
          actions={
            <Button variant="outline" onClick={() => void ready.refetch()} loading={ready.isFetching}>
              {t("common.retry")}
            </Button>
          }
        />

        <Card
          title={
            <span className="flex items-center gap-2">
              <Activity className="size-4 text-primary" aria-hidden />
              /ready
            </span>
          }
        >
          <DescriptionList
            items={[
              { label: "status", value: <Badge tone={ok ? "success" : "danger"}>{ready.data?.status ?? "—"}</Badge> },
              { label: "database", value: <Badge tone={ready.data?.database ? "success" : "danger"}>{ready.data?.database ? t("common.yes") : t("common.no")}</Badge> },
            ]}
            columns={2}
          />
        </Card>
      </div>
    </OperatorOnly>
  );
}
