import { useTranslation } from "@mizan/i18n";
import { Card, PageHeader } from "@mizan/ui";
import { useParams } from "@tanstack/react-router";

import { useSpaces } from "../shell";

/** Space screens of Phase 1 epics (SPEC §22.4–22.8): the shell, navigation and permissions are in
 * place; each screen lands here until its module ships. */
export function SpacePage() {
  const { t } = useTranslation();
  const params = useParams({ strict: false }) as { space?: string; screen?: string; id?: string };
  const spaces = useSpaces();
  const space = spaces.find((s) => s.key === params.space);
  const entry = space?.entries.find((e) => e.href.endsWith(`/${params.screen ?? ""}`));
  return (
    <div className="flex flex-col gap-4">
      <PageHeader title={entry?.label ?? params.screen ?? ""} subtitle={space?.label} />
      <Card>
        <p className="text-base">{t("common.empty_title")}</p>
        <p className="text-sm text-muted">{t("common.empty_hint")}</p>
      </Card>
    </div>
  );
}
