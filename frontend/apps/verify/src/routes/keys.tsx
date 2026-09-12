import { useApi } from "@mizan/api-client";
import { useOnline } from "@mizan/app-kit";
import { useTranslation } from "@mizan/i18n";
import { Alert, Button, Card, PageHeader } from "@mizan/ui";
import { useQuery } from "@tanstack/react-query";
import { RefreshCw } from "lucide-react";

import { fetchJwks, loadCachedJwks } from "../lib/jws";

export function KeysPage() {
  const { t } = useTranslation();
  const api = useApi();
  const online = useOnline();
  const jwks = useQuery({ queryKey: ["verify", "keys"], queryFn: () => fetchJwks(api.baseUrl), enabled: online, initialData: loadCachedJwks() ?? undefined });
  const keys = jwks.data?.keys ?? [];
  return (
    <div className="flex flex-col gap-4">
      <PageHeader title={t("verify.keys")} subtitle={t("verify.keys_cached", { count: keys.length })} actions={<Button variant="outline" size="sm" leftIcon={<RefreshCw className="size-4" aria-hidden />} onClick={() => void jwks.refetch()} disabled={!online} loading={jwks.isFetching}>{t("verify.refresh_keys")}</Button>} />
      {!online && <Alert tone="warning">{t("verify.offline_mode")}</Alert>}
      <div className="flex flex-col gap-3">
        {keys.map((key) => (
          <Card key={key.kid ?? JSON.stringify(key)} title={key.kid}>
            <pre className="overflow-x-auto text-xs">{JSON.stringify(key, null, 2)}</pre>
          </Card>
        ))}
      </div>
    </div>
  );
}
