import { useApi } from "@mizan/api-client";
import { useTranslation, formatDateTime, currentLocale } from "@mizan/i18n";
import { Card, DescriptionList, EmptyState, PageHeader } from "@mizan/ui";
import { useQuery } from "@tanstack/react-query";

export function TransparencyPage() {
  const { t } = useTranslation();
  const api = useApi();
  const head = useQuery({ queryKey: ["verify", "transparency", "head"], queryFn: async () => (await api.client.GET("/verify/transparency/head")).data as Record<string, unknown> | null });
  return (
    <div className="flex flex-col gap-4">
      <PageHeader title={t("verify.transparency")} />
      <Card>
        {head.data ? (
          <DescriptionList
            items={[
              { label: "tree_size", value: String(head.data["tree_size"] ?? "") },
              { label: "root_hash", value: <code className="break-all text-xs">{String(head.data["root_hash"] ?? "")}</code> },
              { label: "published_at", value: head.data["published_at"] ? formatDateTime(String(head.data["published_at"]), currentLocale()) : "" },
              { label: "kid", value: String(head.data["kid"] ?? "") },
            ]}
          />
        ) : (
          <EmptyState title={t("common.empty_title")} />
        )}
        {head.data?.["signature"] ? <pre className="mt-3 overflow-x-auto rounded-control bg-subtle p-3 text-xs">{String(head.data["signature"])}</pre> : null}
      </Card>
    </div>
  );
}
