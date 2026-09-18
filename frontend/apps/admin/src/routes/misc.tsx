/**
 * Client portal settings and integrations (SPEC §23, §24).
 *
 * Portal settings are per-branch, not per-tenant: a branch decides which sections its clients
 * see and how self-service its acceptance flow is, and those choices live in the branch's
 * `settings` document rather than in a table of their own. That keeps them versioned with the
 * branch and means enabling online payment is one PATCH, not a migration.
 *
 * Integrations (payment providers, e-signature) arrive with Phase 3 and Phase 5. There is no
 * endpoint yet, so that screen says which epic brings it rather than showing an empty table that
 * reads as a configuration fault.
 */
import { useApi } from "@mizan/api-client";
import { useSession } from "@mizan/app-kit";
import { useTranslation } from "@mizan/i18n";
import { Alert, Button, Card, EmptyState, FormField, Input, PageHeader, Select, Spinner, Switch, useToast } from "@mizan/ui";
import { useState } from "react";

import { useList, useSave } from "../lib/resource";

type Branch = {
  id: string;
  code: string;
  trade_name: string;
  legal_name: string;
  settings: Record<string, unknown>;
  row_version: number;
};

/** The portal section of a branch's settings, with the defaults an unset branch behaves as. */
type PortalSettings = {
  enabled: boolean;
  show_reports: boolean;
  show_invoices: boolean;
  allow_online_payment: boolean;
  allow_quote_acceptance: boolean;
  allow_requests: boolean;
  support_email: string;
  acceptance_mode: string;
};

const DEFAULTS: PortalSettings = {
  enabled: true,
  show_reports: true,
  show_invoices: true,
  allow_online_payment: false,
  allow_quote_acceptance: true,
  allow_requests: true,
  support_email: "",
  acceptance_mode: "PORTAL_OTP",
};

const ACCEPTANCE_MODES = ["PORTAL_OTP", "PAPER", "ESIGN"];

function portalOf(branch: Branch | undefined): PortalSettings {
  const raw = (branch?.settings?.["portal"] ?? {}) as Partial<PortalSettings>;
  return { ...DEFAULTS, ...raw };
}

export function PortalSettingsPage() {
  const { t } = useTranslation();
  const api = useApi();
  const session = useSession();
  const toast = useToast();

  const branches = useList<Branch>(["branches", "list", {}], async () => (await api.client.GET("/branches")).data as Branch[] | undefined, {
    enabled: session.can("branch", "view"),
  });
  const [branchId, setBranchId] = useState("");
  const branch = branches.data?.find((b) => b.id === branchId) ?? branches.data?.[0];

  /* The draft carries its branch, so switching branch cannot show one branch's unsaved edits
     against another's stored settings. */
  const [draft, setDraft] = useState<{ branchId: string; values: PortalSettings } | null>(null);
  const stored = portalOf(branch);
  const pending = branch && draft?.branchId === branch.id ? draft.values : null;
  const values = pending ?? stored;
  const dirty = pending !== null;

  const set = <K extends keyof PortalSettings>(key: K, value: PortalSettings[K]) => {
    if (!branch) return;
    setDraft({ branchId: branch.id, values: { ...values, [key]: value } });
  };

  const save = useSave(
    async () =>
      (await api.client.PATCH("/branches/{branch_id}", {
        params: { path: { branch_id: branch!.id } },
        body: {
          // Merge, never replace: `settings` holds more than the portal section.
          settings: { ...(branch!.settings ?? {}), portal: values },
          row_version: branch!.row_version,
        } as never,
      })).data,
    [["branches", "list", {}]],
    () => {
      setDraft(null);
      toast.success(t("common.saved"));
    },
  );

  const canEdit = session.can("branch", "update");

  if (branches.isPending) {
    return (
      <div className="flex flex-col gap-4">
        <PageHeader title={t("nav.admin.portal")} />
        <Card>
          <Spinner delay={0} label={t("common.loading")} />
        </Card>
      </div>
    );
  }

  if (!branch) {
    return (
      <div className="flex flex-col gap-4">
        <PageHeader title={t("nav.admin.portal")} />
        <EmptyState title={t("common.empty_title")} hint={t("org.branches_hint")} />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <PageHeader
        title={t("nav.admin.portal")}
        subtitle={branch.trade_name || branch.code}
        actions={
          branches.data && branches.data.length > 1 ? (
            <Select
              value={branch.id}
              onValueChange={setBranchId}
              className="w-56"
              options={branches.data.map((b) => ({ value: b.id, label: b.trade_name || b.code }))}
              aria-label={t("common.branch")}
            />
          ) : undefined
        }
      />

      {!values.enabled && <Alert tone="warning">{t("common.inactive")}</Alert>}

      <Card title={t("common.settings")}>
        <div className="flex max-w-xl flex-col gap-4">
          <FormField label={t("common.status")}>
            <Switch checked={values.enabled} onCheckedChange={(v) => set("enabled", v)} disabled={!canEdit} label={values.enabled ? t("common.active") : t("common.inactive")} />
          </FormField>

          {/* Everything below only matters while the portal is on. */}
          <fieldset disabled={!values.enabled || !canEdit} className="flex flex-col gap-4 disabled:opacity-60">
            <FormField label={t("nav.reports")}>
              <Switch checked={values.show_reports} onCheckedChange={(v) => set("show_reports", v)} label={values.show_reports ? t("common.yes") : t("common.no")} />
            </FormField>
            <FormField label={t("nav.invoices")}>
              <Switch checked={values.show_invoices} onCheckedChange={(v) => set("show_invoices", v)} label={values.show_invoices ? t("common.yes") : t("common.no")} />
            </FormField>
            <FormField label={t("nav.payments")} help={t("nav.admin.integrations")}>
              {/* No provider is configured yet, so this stays off and says why. */}
              <Switch
                checked={values.allow_online_payment}
                onCheckedChange={(v) => set("allow_online_payment", v)}
                disabled
                label={t("common.no")}
              />
            </FormField>
            <FormField label={t("nav.requests")}>
              <Switch checked={values.allow_requests} onCheckedChange={(v) => set("allow_requests", v)} label={values.allow_requests ? t("common.yes") : t("common.no")} />
            </FormField>
            <FormField label={t("nav.quotes")}>
              <Switch
                checked={values.allow_quote_acceptance}
                onCheckedChange={(v) => set("allow_quote_acceptance", v)}
                label={values.allow_quote_acceptance ? t("common.yes") : t("common.no")}
              />
            </FormField>
            {values.allow_quote_acceptance && (
              <FormField label={t("nav.contracts")} help="PORTAL_OTP · PAPER · ESIGN">
                <Select value={values.acceptance_mode} onValueChange={(v) => set("acceptance_mode", v)} options={ACCEPTANCE_MODES.map((value) => ({ value, label: value }))} />
              </FormField>
            )}
            <FormField label={t("org.email")} help={t("common.optional")}>
              <Input type="email" value={values.support_email} onChange={(e) => set("support_email", e.target.value)} />
            </FormField>
          </fieldset>

          {canEdit && (
            <div className="flex gap-2">
              <Button onClick={() => save.mutate(undefined as never)} loading={save.isPending} disabled={!dirty}>
                {t("common.save")}
              </Button>
              {dirty && (
                <Button variant="ghost" onClick={() => setDraft(null)}>
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

export function IntegrationsPage() {
  const { t } = useTranslation();
  return (
    <div className="flex flex-col gap-4">
      <PageHeader title={t("nav.admin.integrations")} />
      <EmptyState title={t("nav.admin.integrations")} hint={`${t("common.empty_hint")} — E3.3 / E5`} />
    </div>
  );
}
