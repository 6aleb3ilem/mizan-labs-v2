import type { Decorator, Preview } from "@storybook/react-vite";
import { applyTheme } from "@mizan/tokens";
import { initI18n, setLocale, type Locale } from "@mizan/i18n";
import { useEffect, type ReactNode } from "react";

import "../src/styles.css";

initI18n({ locale: "fr" });

function ThemeFrame({ theme, brand, locale, children }: { theme: "light" | "dark"; brand: string | undefined; locale: Locale; children: ReactNode }) {
  useEffect(() => {
    applyTheme(document.documentElement, theme, brand);
    void setLocale(locale);
  }, [theme, brand, locale]);
  return <div className="min-h-64 bg-canvas p-6 text-primary">{children}</div>;
}

const withTheme: Decorator = (Story, context) => (
  <ThemeFrame theme={(context.globals["theme"] as "light" | "dark") ?? "light"} brand={(context.globals["brand"] as string) || undefined} locale={(context.globals["locale"] as Locale) ?? "fr"}>
    <Story />
  </ThemeFrame>
);

const preview: Preview = {
  decorators: [withTheme],
  globalTypes: {
    theme: { description: "Theme", toolbar: { icon: "mirror", items: ["light", "dark"], dynamicTitle: true } },
    locale: { description: "Locale", toolbar: { icon: "globe", items: ["fr", "en"], dynamicTitle: true } },
    brand: { description: "Tenant primary", toolbar: { icon: "paintbrush", items: ["", "#FF8A00", "#0F766E"], dynamicTitle: true } },
  },
  initialGlobals: { theme: "light", locale: "fr", brand: "" },
  parameters: {
    a11y: { test: "error" },
    layout: "fullscreen",
    controls: { expanded: true },
  },
};

export default preview;
