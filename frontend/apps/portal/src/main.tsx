import "@mizan/ui/styles.css";

import { ApiProvider } from "@mizan/api-client/react";
import { InboxProvider, SessionProvider, ThemeProvider } from "@mizan/app-kit";
import { initI18n } from "@mizan/i18n";
import { ToastProvider } from "@mizan/ui";
import { RouterProvider } from "@tanstack/react-router";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { api, queryClient } from "./app";
import { router } from "./router";

initI18n();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ApiProvider api={api} queryClient={queryClient}>
      <ThemeProvider>
        <ToastProvider>
          <SessionProvider>
            <InboxProvider onOpen={(n) => n.link && void router.navigate({ to: n.link as never })}>
              <RouterProvider router={router} />
            </InboxProvider>
          </SessionProvider>
        </ToastProvider>
      </ThemeProvider>
    </ApiProvider>
  </StrictMode>,
);
