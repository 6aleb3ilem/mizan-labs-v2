/** Portal sections of Phase 1 (projects, quotes with OTP acceptance, reports, invoices, payments,
 * requests, history): navigation and shell are in place; the modules land with their epics. */
import { useTranslation } from "@mizan/i18n";
import { Card, EmptyState, PageHeader } from "@mizan/ui";
import { useParams } from "@tanstack/react-router";

function Section({ titleKey }: { titleKey: string }) {
  const { t } = useTranslation();
  const params = useParams({ strict: false }) as Record<string, string | undefined>;
  const id = Object.values(params).find(Boolean);
  return (
    <div className="flex flex-col gap-4">
      <PageHeader title={t(titleKey)} subtitle={id} />
      <Card>
        <EmptyState title={t("common.empty_title")} hint={t("common.empty_hint")} />
      </Card>
    </div>
  );
}

export const ProjectsPage = () => <Section titleKey="nav.portal.projects" />;
export const QuotesPage = () => <Section titleKey="nav.portal.quotes" />;
export const ReportsPage = () => <Section titleKey="nav.portal.reports" />;
export const InvoicesPage = () => <Section titleKey="nav.portal.invoices" />;
export const PaymentsPage = () => <Section titleKey="nav.portal.payments" />;
export const RequestsPage = () => <Section titleKey="nav.portal.requests" />;
export const HistoryPage = () => <Section titleKey="nav.portal.history" />;
