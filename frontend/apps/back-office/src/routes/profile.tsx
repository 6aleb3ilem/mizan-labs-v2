import { PreferencesControls, useSession } from "@mizan/app-kit";
import { useTranslation } from "@mizan/i18n";
import { Card, DescriptionList, PageHeader } from "@mizan/ui";

export function ProfilePage() {
  const { t } = useTranslation();
  const session = useSession();
  return (
    <div className="flex flex-col gap-4">
      <PageHeader title={t("common.profile")} />
      <Card title={session.me?.display_name || session.me?.email}>
        <DescriptionList
          items={[
            { label: t("auth.email"), value: session.me?.email },
            { label: t("common.locale"), value: session.me?.locale },
            { label: "Realm", value: session.me?.realm },
            { label: t("nav.admin.memberships"), value: session.me?.memberships.length ?? 0 },
          ]}
        />
      </Card>
      <Card title={t("common.settings")}>
        <PreferencesControls />
      </Card>
    </div>
  );
}
