/** Account (SPEC §24): contacts & access, channel preferences, locale, password. */
import { useApi } from "@mizan/api-client";
import { PreferencesControls, useErrorToast, useSession } from "@mizan/app-kit";
import { useTranslation } from "@mizan/i18n";
import { Button, Card, DescriptionList, FormField, Input, PageHeader, Switch, useToast } from "@mizan/ui";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

const CHANNELS = ["email", "sms", "whatsapp", "in_app"] as const;

export function AccountPage() {
  const { t } = useTranslation();
  const api = useApi();
  const session = useSession();
  const queryClient = useQueryClient();
  const toast = useToast();
  const errorToast = useErrorToast();
  const prefs = useQuery({ queryKey: ["me", "notification-preferences"], queryFn: async () => (await api.client.GET("/me/notification-preferences")).data });
  const save = useMutation({
    mutationFn: async (body: Partial<Record<(typeof CHANNELS)[number], boolean>>) => (await api.client.PUT("/me/notification-preferences", { body })).data,
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["me", "notification-preferences"] }),
    onError: errorToast,
  });
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const changePassword = useMutation({
    mutationFn: async () => api.client.POST("/auth/change-password", { body: { current_password: current, new_password: next } }),
    onSuccess: () => {
      toast.success(t("common.saved"));
      setCurrent("");
      setNext("");
      setErrors({});
    },
    onError: (error) => setErrors(errorToast(error)),
  });

  return (
    <div className="flex flex-col gap-4">
      <PageHeader title={t("nav.portal.account")} />
      <Card title={session.me?.display_name || session.me?.email}>
        <DescriptionList items={[{ label: t("auth.email"), value: session.me?.email }, { label: t("common.locale"), value: session.me?.locale }]} />
      </Card>
      <Card title={t("common.notifications")}>
        <div className="flex flex-col gap-3">
          {CHANNELS.map((channel) => (
            <Switch key={channel} checked={prefs.data?.[channel] ?? true} onCheckedChange={(v) => save.mutate({ [channel]: v })} label={channel.replace("_", "-")} disabled={prefs.isPending} />
          ))}
        </div>
      </Card>
      <Card title={t("common.settings")}>
        <PreferencesControls />
      </Card>
      <Card title={t("auth.password")}>
        <form
          className="flex max-w-md flex-col gap-3"
          onSubmit={(e) => {
            e.preventDefault();
            changePassword.mutate();
          }}
        >
          <FormField label={t("auth.password")} required error={errors["current_password"]}>
            <Input type="password" autoComplete="current-password" value={current} onChange={(e) => setCurrent(e.target.value)} />
          </FormField>
          <FormField label={`${t("auth.password")} (${t("common.new").toLowerCase()})`} required error={errors["new_password"]}>
            <Input type="password" autoComplete="new-password" value={next} onChange={(e) => setNext(e.target.value)} minLength={10} />
          </FormField>
          <div>
            <Button type="submit" loading={changePassword.isPending}>
              {t("common.save")}
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
}
