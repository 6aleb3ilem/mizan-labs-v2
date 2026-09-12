/** Step 1: registry status of a document by token or QR; step 2: short code → digest;
 * offline: JWS check against the cached JWKS (SPEC §25, §18.4–18.5). */
import { ApiError, useApi } from "@mizan/api-client";
import { useErrorMessage, useOnline } from "@mizan/app-kit";
import { formatDateTime, currentLocale, useTranslation } from "@mizan/i18n";
import { Alert, Badge, Button, Card, DescriptionList, Dialog, FormField, Input, PageHeader, Textarea, useToast } from "@mizan/ui";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useNavigate, useParams } from "@tanstack/react-router";
import { useEffect, useState } from "react";

import { fetchJwks, loadCachedJwks, tokenOf, verifyOffline, type OfflineResult } from "../lib/jws";

type Lookup = Record<string, unknown> & { status?: string; kind?: string; number?: string; issued_at?: string; issuer?: string; branch?: string; account?: string; project?: string; superseded_by?: string | null };

export function LookupPage() {
  const { t } = useTranslation();
  const api = useApi();
  const online = useOnline();
  const navigate = useNavigate();
  const toast = useToast();
  const message = useErrorMessage();
  const params = useParams({ strict: false }) as { token?: string };
  const locale = currentLocale();
  const [input, setInput] = useState(params.token ?? "");
  const [jws, setJws] = useState<string | null>(() => (typeof window !== "undefined" && window.location.hash.length > 1 ? window.location.hash.slice(1) : null));
  const [offline, setOffline] = useState<OfflineResult | null>(null);
  const [shortCode, setShortCode] = useState("");
  const [reportOpen, setReportOpen] = useState(false);
  const token = params.token ?? null;

  useEffect(() => {
    if (!jws) return;
    let cancelled = false;
    (async () => {
      let jwks = loadCachedJwks();
      if (online) {
        try {
          jwks = await fetchJwks(api.baseUrl);
        } catch {
          /* keep the cache */
        }
      }
      const result = await verifyOffline(jws, jwks);
      if (cancelled) return;
      setOffline(result);
      if (result.status === "valid" && typeof result.payload.t === "string" && !token) void navigate({ to: "/d/$token", params: { token: result.payload.t }, hash: jws });
    })();
    return () => {
      cancelled = true;
    };
  }, [jws, online, api.baseUrl, navigate, token]);

  const lookup = useQuery<Lookup>({
    queryKey: ["verify", token],
    queryFn: async () => (await api.client.GET("/verify/{token}", { params: { path: { token: token! } } })).data as Lookup,
    enabled: !!token && online,
    retry: false,
  });
  const digest = useMutation({
    mutationFn: async () => (await api.client.POST("/verify/{token}/digest", { params: { path: { token: token! } }, body: { short_code: shortCode.trim().toUpperCase() } })).data as Record<string, unknown>,
    onError: (error) => toast.error(t("common.error_title"), message(error)),
  });
  const report = useMutation({
    mutationFn: async (body: { reporter_name: string; reporter_contact: string; message: string }) => api.client.POST("/verify/{token}/report-suspicious", { params: { path: { token: token! } }, body }),
    onSuccess: () => {
      setReportOpen(false);
      toast.success(t("verify.report_sent"));
    },
    onError: (error) => toast.error(t("common.error_title"), message(error)),
  });

  function submit(event: React.FormEvent) {
    event.preventDefault();
    const parsed = tokenOf(input);
    if (parsed.jws) {
      setJws(parsed.jws);
      return;
    }
    if (parsed.token) void navigate({ to: "/d/$token", params: { token: parsed.token } });
  }

  const status = lookup.data?.status;
  const tone = status === "CURRENT" ? "success" : status === "SUPERSEDED" ? "warning" : status === "REVOKED" ? "danger" : "slate";
  const statusLabel = status === "CURRENT" ? t("verify.status_current") : status === "SUPERSEDED" ? t("verify.status_superseded") : status === "REVOKED" ? t("verify.status_revoked") : t("verify.status_not_found");

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title={t("verify.title")} subtitle={t("verify.intro")} />
      <form onSubmit={submit} className="flex flex-col gap-3 sm:flex-row sm:items-end">
        <FormField label={t("verify.token_label")} className="flex-1">
          <Input value={input} onChange={(e) => setInput(e.target.value)} placeholder={t("verify.token_placeholder")} autoCapitalize="characters" autoComplete="off" spellCheck={false} />
        </FormField>
        <Button type="submit" size="lg">
          {t("verify.check")}
        </Button>
      </form>

      {offline && (
        <Alert tone={offline.status === "valid" ? "success" : offline.status === "invalid" ? "danger" : "warning"} title={offline.status === "valid" ? t("verify.offline_ok") : offline.status === "invalid" ? t("verify.offline_bad") : t("verify.offline_unknown_key")}>
          {offline.status === "valid" && (
            <DescriptionList
              className="mt-2"
              items={[
                { label: t("verify.number"), value: String(offline.payload.n ?? "") },
                { label: t("verify.kind"), value: String(offline.payload.k ?? "") },
                { label: t("verify.issued_at"), value: String(offline.payload.d ?? "") },
                { label: "kid", value: offline.kid },
              ]}
            />
          )}
        </Alert>
      )}

      {token && (
        <Card title={t("verify.status_current").split(" ")[0]}>
          {!online && !lookup.data ? (
            <Alert tone="warning">{t("verify.offline_mode")}</Alert>
          ) : lookup.isPending ? (
            <p className="text-sm text-muted">{t("common.loading")}</p>
          ) : lookup.error ? (
            <Alert tone={ApiError.is(lookup.error) && lookup.error.status === 404 ? "danger" : "warning"} title={ApiError.is(lookup.error) && lookup.error.status === 404 ? t("verify.status_not_found") : message(lookup.error)} />
          ) : (
            <div className="flex flex-col gap-4">
              <Badge tone={tone} size="md" dot>
                {statusLabel}
              </Badge>
              <DescriptionList
                items={[
                  { label: t("verify.issuer"), value: String(lookup.data?.issuer ?? lookup.data?.branch ?? "") },
                  { label: t("verify.kind"), value: String(lookup.data?.kind ?? "") },
                  { label: t("verify.number"), value: String(lookup.data?.number ?? "") },
                  { label: t("verify.issued_at"), value: lookup.data?.issued_at ? formatDateTime(String(lookup.data.issued_at), locale) : "" },
                  { label: t("verify.account"), value: String(lookup.data?.account ?? "") },
                  { label: t("verify.project"), value: String(lookup.data?.project ?? "") },
                ]}
              />
              <section className="rounded-card border border-line p-4">
                <h3 className="text-base font-semibold">{t("verify.step2_title")}</h3>
                <p className="text-sm text-muted">{t("verify.step2_hint")}</p>
                <form
                  className="mt-3 flex flex-col gap-3 sm:flex-row sm:items-end"
                  onSubmit={(e) => {
                    e.preventDefault();
                    digest.mutate();
                  }}
                >
                  <FormField label={t("verify.short_code")} className="flex-1">
                    <Input value={shortCode} onChange={(e) => setShortCode(e.target.value)} maxLength={8} autoCapitalize="characters" className="tabular uppercase" />
                  </FormField>
                  <Button type="submit" variant="secondary" loading={digest.isPending}>
                    {t("verify.show_digest")}
                  </Button>
                </form>
                {digest.data && (
                  <pre className="mt-3 overflow-x-auto rounded-control bg-subtle p-3 text-sm">{JSON.stringify(digest.data, null, 2)}</pre>
                )}
              </section>
              <div className="flex flex-wrap gap-2">
                <Button variant="outline" onClick={() => { setInput(""); setJws(null); setOffline(null); void navigate({ to: "/" }); }}>
                  {t("verify.verify_another")}
                </Button>
                <Button variant="ghost" onClick={() => setReportOpen(true)}>
                  {t("verify.report_suspicious")}
                </Button>
              </div>
            </div>
          )}
        </Card>
      )}
      <ReportDialog open={reportOpen} onOpenChange={setReportOpen} onSubmit={(body) => report.mutate(body)} loading={report.isPending} />
    </div>
  );
}

function ReportDialog({ open, onOpenChange, onSubmit, loading }: { open: boolean; onOpenChange: (o: boolean) => void; onSubmit: (body: { reporter_name: string; reporter_contact: string; message: string }) => void; loading: boolean }) {
  const { t } = useTranslation();
  const [name, setName] = useState("");
  const [contact, setContact] = useState("");
  const [text, setText] = useState("");
  return (
    <Dialog
      open={open}
      onOpenChange={onOpenChange}
      title={t("verify.report_suspicious")}
      closeLabel={t("common.close")}
      footer={
        <>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            {t("common.cancel")}
          </Button>
          <Button onClick={() => onSubmit({ reporter_name: name, reporter_contact: contact, message: text })} loading={loading} disabled={!text.trim()}>
            {t("common.send")}
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-3">
        <FormField label={t("verify.reporter_name")}>
          <Input value={name} onChange={(e) => setName(e.target.value)} />
        </FormField>
        <FormField label={t("verify.reporter_contact")}>
          <Input value={contact} onChange={(e) => setContact(e.target.value)} />
        </FormField>
        <FormField label={t("verify.message")} required>
          <Textarea value={text} onChange={(e) => setText(e.target.value)} />
        </FormField>
      </div>
    </Dialog>
  );
}
