import { useTranslation } from "@mizan/i18n";
import { Card, PageHeader } from "@mizan/ui";
import type { ReactNode } from "react";

/** A section of the console not yet backed by an API in this phase (SPEC Appendix R step 15). */
export function PlaceholderPage({ title, description, children }: { title: ReactNode; description: ReactNode; children?: ReactNode }) {
  const { t } = useTranslation();
  return (
    <div className="flex flex-col gap-4">
      <PageHeader title={title} />
      <Card>
        <p className="text-base">{description}</p>
        <p className="mt-2 text-sm text-muted">{t("common.empty_hint")}</p>
        {children}
      </Card>
    </div>
  );
}
