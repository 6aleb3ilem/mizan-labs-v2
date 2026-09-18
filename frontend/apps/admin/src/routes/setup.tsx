/**
 * The setup wizard (SPEC §23.9, E0.11).
 *
 * A new branch is not usable until roughly six things exist: the branch itself, its departments,
 * the numbering schemes that give its documents numbers, a vocabulary or two, a payment-terms
 * template and a price list. Each already has its own screen; the wizard exists because nobody
 * knows that list on their first day, and discovering it one failed action at a time is how an
 * hour becomes a week.
 *
 * So this is a *checklist over live data*, not a form that duplicates the others. Every step
 * reads the real API, reports what is already there, and links to the screen that fixes it. That
 * means it is correct whether the branch was set up here, by the seed command or by hand — and
 * it cannot drift from the screens it points at, because it owns no fields of its own.
 */
import { useApi } from "@mizan/api-client";
import { useSession } from "@mizan/app-kit";
import { useTranslation } from "@mizan/i18n";
import { Badge, Button, Card, PageHeader, Select, Spinner, Stepper } from "@mizan/ui";
import { Link } from "@tanstack/react-router";
import { ArrowRight, CheckCircle2, Circle } from "lucide-react";
import { useMemo, useState } from "react";

import { useList } from "../lib/resource";

type Branch = { id: string; code: string; trade_name: string; legal_name: string; currency: string };
type Department = { id: string; branch_id: string; code: string };
type Scheme = { id: string; branch_id: string; applies_to: string; status: string };
type Signatory = { id: string; branch_id: string; active: boolean };
type PaymentTerms = { id: string; branch_id: string; is_default: boolean };
type PriceList = { id: string; branch_id: string };
type VocabularyEntry = { id: string; kind: string };

/** A step is done when the data says so; there is no separate wizard state to fall out of sync. */
type Step = {
  key: string;
  label: string;
  hint: string;
  href: string;
  done: boolean;
  detail: string;
};

export function SetupWizardPage() {
  const { t } = useTranslation();
  const api = useApi();
  const session = useSession();

  const branches = useList<Branch>(["branches", "list", {}], async () => (await api.client.GET("/branches")).data as Branch[] | undefined, {
    enabled: session.can("branch", "view"),
  });
  const [branchId, setBranchId] = useState("");
  const branch = branches.data?.find((b) => b.id === branchId) ?? branches.data?.[0];

  const departments = useList<Department>(["departments", "list", {}], async () => (await api.client.GET("/departments")).data as Department[] | undefined, {
    enabled: session.can("department", "view"),
  });
  const schemes = useList<Scheme>(["numbering-schemes", "list", {}], async () => (await api.client.GET("/numbering-schemes")).data as Scheme[] | undefined, {
    enabled: session.can("numbering_scheme", "view"),
  });
  const signatories = useList<Signatory>(["signatories", "list", {}], async () => (await api.client.GET("/signatories")).data as Signatory[] | undefined, {
    enabled: session.can("signatory", "view"),
  });
  const paymentTerms = useList<PaymentTerms>(
    ["payment-terms-templates", "list", {}],
    async () => (await api.client.GET("/payment-terms-templates")).data as PaymentTerms[] | undefined,
    { enabled: session.can("payment_terms_template", "view") },
  );
  const priceLists = useList<PriceList>(["price-lists", "list", {}], async () => (await api.client.GET("/price-lists")).data as PriceList[] | undefined, {
    enabled: session.can("price_list", "view"),
  });
  const services = useList<{ id: string }>(["services", "list", {}], async () => (await api.client.GET("/services")).data as { id: string }[] | undefined, {
    enabled: session.can("service", "view"),
  });
  const units = useList<VocabularyEntry>(
    ["vocabularies", "unit", "entries"],
    async () => (await api.client.GET("/vocabularies/{kind}/entries", { params: { path: { kind: "unit" } } })).data as VocabularyEntry[] | undefined,
    { enabled: session.can("vocabulary", "view") },
  );

  const loading =
    branches.isPending || departments.isPending || schemes.isPending || signatories.isPending || paymentTerms.isPending || priceLists.isPending;

  const steps: Step[] = useMemo(() => {
    const id = branch?.id;
    const mine = <T extends { branch_id: string }>(rows: T[] | undefined) => (rows ?? []).filter((row) => !id || row.branch_id === id);

    const ownDepartments = mine(departments.data);
    // Only an ACTIVE scheme issues numbers; a draft one leaves the first document without a number.
    const activeSchemes = mine(schemes.data).filter((scheme) => scheme.status === "ACTIVE");
    const activeSignatories = mine(signatories.data).filter((signatory) => signatory.active);
    const defaultTerms = mine(paymentTerms.data).filter((template) => template.is_default);
    const ownPriceLists = mine(priceLists.data);
    const unitEntries = units.data ?? [];
    const catalogueServices = services.data ?? [];

    return [
      {
        key: "branch",
        label: t("common.branch"),
        hint: t("org.branches_hint"),
        href: "/org/branches",
        done: !!branch,
        detail: branch ? `${branch.code} · ${branch.currency}` : "—",
      },
      {
        key: "departments",
        label: t("common.departments"),
        hint: t("org.department"),
        href: "/org/departments",
        done: ownDepartments.length > 0,
        detail: t("common.results", { count: ownDepartments.length }),
      },
      {
        key: "vocabularies",
        label: t("nav.admin.vocabularies"),
        hint: t("vocab.hint"),
        href: "/vocabularies/unit",
        done: unitEntries.length > 0,
        detail: t("common.results", { count: unitEntries.length }),
      },
      {
        key: "numbering",
        label: t("nav.admin.numbering"),
        hint: t("numbering.pattern_help"),
        href: "/numbering",
        done: activeSchemes.length > 0,
        detail: t("common.results", { count: activeSchemes.length }),
      },
      {
        key: "signatories",
        label: t("nav.admin.signatories"),
        hint: t("org.signature_mode"),
        href: "/org/signatories",
        done: activeSignatories.length > 0,
        detail: t("common.results", { count: activeSignatories.length }),
      },
      {
        key: "catalog",
        label: t("nav.admin.services"),
        hint: t("nav.admin.catalog"),
        href: "/catalog/services",
        done: catalogueServices.length > 0,
        detail: t("common.results", { count: catalogueServices.length }),
      },
      {
        key: "payment_terms",
        label: t("nav.admin.payment_terms"),
        hint: t("numbering.gapless_help"),
        href: "/payment-terms",
        done: defaultTerms.length > 0,
        detail: defaultTerms.length > 0 ? t("common.yes") : t("common.no"),
      },
      {
        key: "prices",
        label: t("nav.admin.price_lists"),
        hint: t("nav.admin.pricing"),
        href: "/pricing/price-lists",
        done: ownPriceLists.length > 0,
        detail: t("common.results", { count: ownPriceLists.length }),
      },
    ];
  }, [branch, departments.data, schemes.data, signatories.data, paymentTerms.data, priceLists.data, services.data, units.data, t]);

  const doneCount = steps.filter((step) => step.done).length;
  // The first unfinished step is where the wizard points; the rest stay visible as context.
  const currentIndex = Math.max(0, steps.findIndex((step) => !step.done));

  return (
    <div className="flex flex-col gap-4">
      <PageHeader
        title={t("nav.admin.setup")}
        subtitle={t("common.showing", { shown: doneCount, total: steps.length })}
        badges={<Badge tone={doneCount === steps.length ? "success" : "amber"}>{`${doneCount} / ${steps.length}`}</Badge>}
        actions={
          branches.data && branches.data.length > 1 ? (
            <Select
              value={branch?.id ?? ""}
              onValueChange={setBranchId}
              className="w-56"
              options={branches.data.map((b) => ({ value: b.id, label: b.trade_name || b.code }))}
              aria-label={t("common.branch")}
            />
          ) : undefined
        }
      />

      {loading ? (
        <Card>
          <Spinner delay={0} label={t("common.loading")} />
        </Card>
      ) : (
        <>
          <Card>
            <Stepper steps={steps.map((step) => ({ key: step.key, label: step.label }))} current={currentIndex} />
          </Card>

          <ul className="flex flex-col gap-2">
            {steps.map((step, index) => (
              <li key={step.key}>
                <Link
                  to={step.href as never}
                  className="flex items-center gap-3 rounded-card border border-line bg-surface px-4 py-3 shadow-1 hover-colors hover:bg-subtle"
                >
                  {step.done ? (
                    <CheckCircle2 className="size-5 shrink-0 text-success" aria-hidden />
                  ) : (
                    <Circle className={`size-5 shrink-0 ${index === currentIndex ? "text-primary" : "text-muted"}`} aria-hidden />
                  )}
                  <span className="min-w-0 flex-1">
                    <span className="block font-medium">{step.label}</span>
                    <span className="block truncate text-sm text-muted">{step.hint}</span>
                  </span>
                  <span className="tabular shrink-0 text-sm text-muted">{step.detail}</span>
                  <ArrowRight className="size-4 shrink-0 text-muted" aria-hidden />
                </Link>
              </li>
            ))}
          </ul>

          {doneCount === steps.length && (
            <Card>
              <div className="flex items-center justify-between gap-4">
                <p className="text-base">{t("common.saved")}</p>
                <Link to="/" className="shrink-0">
                  <Button variant="outline">{t("common.finish")}</Button>
                </Link>
              </div>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
