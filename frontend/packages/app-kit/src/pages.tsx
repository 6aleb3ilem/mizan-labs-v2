import { useTranslation, type Locale } from "@mizan/i18n";
import { Alert, Button, FormField, Input, Select } from "@mizan/ui";
import { Component, useState, type FormEvent, type ReactNode } from "react";

import { useErrorMessage } from "./hooks";
import { useSession } from "./session";
import { useTheme, type ThemeChoice } from "./theme";
import { setLocale, currentLocale } from "@mizan/i18n";

export function LoginPage({ title, askTenant = false, logo }: { title: ReactNode; askTenant?: boolean; logo?: ReactNode }) {
  const { t } = useTranslation();
  const session = useSession();
  const message = useErrorMessage();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [tenant, setTenant] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await session.login(email, password, tenant || undefined);
    } catch (err) {
      setError(message(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-dvh items-center justify-center bg-canvas px-4">
      <form onSubmit={submit} className="flex w-full max-w-sm flex-col gap-4 rounded-dialog border border-line bg-surface p-6 shadow-2" aria-labelledby="login-title">
        {logo}
        <h1 id="login-title" className="text-lg font-semibold">
          {title}
        </h1>
        {error && <Alert tone="danger">{error}</Alert>}
        <FormField label={t("auth.email")} required>
          <Input type="email" autoComplete="username" value={email} onChange={(e) => setEmail(e.target.value)} required />
        </FormField>
        <FormField label={t("auth.password")} required>
          <Input type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} required />
        </FormField>
        {askTenant && (
          <FormField label={t("auth.tenant_code")} optionalLabel={t("common.optional")}>
            <Input value={tenant} onChange={(e) => setTenant(e.target.value.toUpperCase())} />
          </FormField>
        )}
        <Button type="submit" size="lg" loading={busy}>
          {busy ? t("auth.signing_in") : t("auth.sign_in")}
        </Button>
      </form>
    </div>
  );
}

export function NotFoundPage({ onHome }: { onHome: () => void }) {
  const { t } = useTranslation();
  return (
    <div className="flex flex-col items-center gap-3 py-20 text-center">
      <p className="text-2xl font-semibold">404</p>
      <p className="text-md">{t("common.not_found_title")}</p>
      <p className="text-sm text-muted">{t("common.not_found_hint")}</p>
      <Button onClick={onHome}>{t("common.go_home")}</Button>
    </div>
  );
}

export function ForbiddenPage() {
  const { t } = useTranslation();
  return (
    <div className="flex flex-col items-center gap-3 py-20 text-center">
      <p className="text-2xl font-semibold">403</p>
      <p className="text-md">{t("authz.forbidden")}</p>
    </div>
  );
}

export function PreferencesControls() {
  const { t } = useTranslation();
  const theme = useTheme();
  const [locale, setLocaleState] = useState<Locale>(currentLocale());
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
      <FormField label={t("common.locale")}>
        <Select
          value={locale}
          onValueChange={(v) => {
            setLocaleState(v as Locale);
            void setLocale(v as Locale);
          }}
          options={[
            { value: "fr", label: t("common.language_fr") },
            { value: "en", label: t("common.language_en") },
          ]}
        />
      </FormField>
      <FormField label={t("common.theme")}>
        <Select
          value={theme.choice}
          onValueChange={(v) => theme.setChoice(v as ThemeChoice)}
          options={[
            { value: "system", label: t("common.theme_system") },
            { value: "light", label: t("common.theme_light") },
            { value: "dark", label: t("common.theme_dark") },
          ]}
        />
      </FormField>
    </div>
  );
}

type BoundaryState = { error: Error | null };

export class AppErrorBoundary extends Component<{ children: ReactNode; fallback: (error: Error, reset: () => void) => ReactNode }, BoundaryState> {
  state: BoundaryState = { error: null };
  static getDerivedStateFromError(error: Error): BoundaryState {
    return { error };
  }
  render() {
    if (this.state.error) return this.props.fallback(this.state.error, () => this.setState({ error: null }));
    return this.props.children;
  }
}
