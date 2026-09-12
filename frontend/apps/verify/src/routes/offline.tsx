/** Offline mode: paste or scan a QR payload; the signature is checked against the cached JWKS. */
import { useTranslation } from "@mizan/i18n";
import { Alert, Button, Card, DescriptionList, FormField, PageHeader, Textarea } from "@mizan/ui";
import { useState } from "react";

import { loadCachedJwks, tokenOf, verifyOffline, type OfflineResult } from "../lib/jws";

export function OfflinePage() {
  const { t } = useTranslation();
  const [input, setInput] = useState("");
  const [result, setResult] = useState<OfflineResult | null>(null);
  const cached = loadCachedJwks();
  return (
    <div className="flex flex-col gap-4">
      <PageHeader title={t("verify.offline_mode")} subtitle={t("verify.keys_cached", { count: cached?.keys.length ?? 0 })} />
      <Card>
        <form
          className="flex flex-col gap-3"
          onSubmit={async (e) => {
            e.preventDefault();
            const parsed = tokenOf(input);
            setResult(parsed.jws ? await verifyOffline(parsed.jws, cached) : { status: "invalid", reason: "not a QR payload" });
          }}
        >
          <FormField label="QR (JWS)">
            <Textarea value={input} onChange={(e) => setInput(e.target.value)} rows={5} spellCheck={false} />
          </FormField>
          <div>
            <Button type="submit">{t("verify.check")}</Button>
          </div>
        </form>
        {result && (
          <Alert className="mt-4" tone={result.status === "valid" ? "success" : result.status === "invalid" ? "danger" : "warning"} title={result.status === "valid" ? t("verify.offline_ok") : result.status === "invalid" ? t("verify.offline_bad") : t("verify.offline_unknown_key")}>
            {result.status === "valid" && <DescriptionList className="mt-2" items={Object.entries(result.payload).map(([k, v]) => ({ label: k, value: String(v) }))} />}
          </Alert>
        )}
      </Card>
    </div>
  );
}
