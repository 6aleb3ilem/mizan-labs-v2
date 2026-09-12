import "@mizan/ui/styles.css";

import { ApiProvider } from "@mizan/api-client/react";
import { ThemeProvider } from "@mizan/app-kit";
import { initI18n } from "@mizan/i18n";
import { ToastProvider } from "@mizan/ui";
import { RouterProvider } from "@tanstack/react-router";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { registerSW } from "virtual:pwa-register";

import { api } from "./app";
import { router } from "./router";

initI18n();
registerSW({ immediate: true });

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ApiProvider api={api}>
      <ThemeProvider>
        <ToastProvider>
          <RouterProvider router={router} />
        </ToastProvider>
      </ThemeProvider>
    </ApiProvider>
  </StrictMode>,
);
