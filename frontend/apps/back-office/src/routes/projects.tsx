/** Projects list and the project page skeleton with its permission-driven tabs (SPEC §22.3). */
import { useSession } from "@mizan/app-kit";
import { useTranslation } from "@mizan/i18n";
import { Badge, Button, Card, EmptyState, PageHeader, TabPanel, Tabs } from "@mizan/ui";
import { useNavigate, useParams } from "@tanstack/react-router";
import { Plus } from "lucide-react";

export function ProjectsPage() {
  const { t } = useTranslation();
  const session = useSession();
  return (
    <div className="flex flex-col gap-4">
      <PageHeader title={t("nav.projects")} actions={session.can("project", "create") && <Button leftIcon={<Plus className="size-4" aria-hidden />}>{t("common.new")}</Button>} />
      <EmptyState title={t("common.empty_title")} hint={t("common.empty_hint")} kind="search" />
    </div>
  );
}

const TABS: { value: string; labelKey: string; permission?: [string, string]; group?: string }[] = [
  { value: "overview", labelKey: "common.overview" },
  { value: "work", labelKey: "nav.projects" },
  { value: "quotes", labelKey: "nav.quotes", permission: ["quote", "view"] },
  { value: "intakes", labelKey: "nav.intakes", permission: ["intake", "view"] },
  { value: "tests", labelKey: "nav.tests", permission: ["test_run", "view"] },
  { value: "reports", labelKey: "nav.reports", permission: ["report", "view"] },
  { value: "finance", labelKey: "nav.invoices", permission: ["invoice", "view"] },
  { value: "assets", labelKey: "nav.assets", permission: ["rental", "view"] },
  { value: "delivery", labelKey: "nav.delivery", permission: ["work_order", "view"] },
  { value: "documents", labelKey: "common.documents" },
  { value: "history", labelKey: "common.history" },
];

export function ProjectPage() {
  const { t } = useTranslation();
  const session = useSession();
  const navigate = useNavigate();
  const params = useParams({ strict: false }) as { projectId: string; tab?: string };
  const tabs = TABS.filter((tab) => !tab.permission || session.can(tab.permission[0], tab.permission[1]));
  const current = params.tab && tabs.some((x) => x.value === params.tab) ? params.tab : "overview";
  return (
    <div className="flex flex-col gap-4">
      <PageHeader title={params.projectId} badges={<Badge tone="blue">{t("common.active")}</Badge>} actions={<Button variant="outline">{t("common.edit")}</Button>} />
      <Tabs value={current} onValueChange={(tab) => void navigate({ to: "/projects/$projectId/$tab", params: { projectId: params.projectId, tab } })} items={tabs.map((tab) => ({ value: tab.value, label: t(tab.labelKey) }))}>
        {tabs.map((tab) => (
          <TabPanel key={tab.value} value={tab.value} className="pt-4">
            <Card>
              <EmptyState title={t(tab.labelKey)} hint={t("common.empty_hint")} />
            </Card>
          </TabPanel>
        ))}
      </Tabs>
    </div>
  );
}
