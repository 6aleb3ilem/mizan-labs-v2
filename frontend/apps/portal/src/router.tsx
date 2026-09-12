/** Route map of the client portal (SPEC Appendix O). */
import { LoginPage, NotFoundPage } from "@mizan/app-kit";
import { Outlet, createRootRoute, createRoute, createRouter, redirect, useNavigate } from "@tanstack/react-router";

import { tokens } from "./app";
import { AccountPage } from "./routes/account";
import { HomePage } from "./routes/home";
import { HistoryPage, InvoicesPage, PaymentsPage, ProjectsPage, QuotesPage, ReportsPage, RequestsPage } from "./routes/sections";
import { PortalShell } from "./shell";

function RootLayout() {
  return <Outlet />;
}
function NotFound() {
  const navigate = useNavigate();
  return <NotFoundPage onHome={() => void navigate({ to: "/home" })} />;
}
function Login() {
  const navigate = useNavigate();
  if (tokens.get()) void navigate({ to: "/home" });
  return <LoginPage title="Mizan Labs — Espace client" askTenant />;
}

const rootRoute = createRootRoute({ component: RootLayout, notFoundComponent: NotFound });
const loginRoute = createRoute({ getParentRoute: () => rootRoute, path: "/login", component: Login });
const appRoute = createRoute({
  getParentRoute: () => rootRoute,
  id: "app",
  beforeLoad: () => {
    if (!tokens.get()) throw redirect({ to: "/login" });
  },
  component: PortalShell,
});
const page = <P extends string>(path: P, component: () => React.JSX.Element) => createRoute({ getParentRoute: () => appRoute, path, component });

const routeTree = rootRoute.addChildren([
  loginRoute,
  appRoute.addChildren([
    createRoute({ getParentRoute: () => appRoute, path: "/", beforeLoad: () => { throw redirect({ to: "/home" }); } }),
    page("/home", HomePage),
    page("/projects", ProjectsPage),
    page("/projects/$projectId", ProjectsPage),
    page("/quotes", QuotesPage),
    page("/quotes/$quoteId", QuotesPage),
    page("/reports", ReportsPage),
    page("/invoices", InvoicesPage),
    page("/invoices/$invoiceId", InvoicesPage),
    page("/payments", PaymentsPage),
    page("/requests", RequestsPage),
    page("/requests/new", RequestsPage),
    page("/account", AccountPage),
    page("/history", HistoryPage),
  ]),
]);

export const router = createRouter({ routeTree, defaultPreload: "intent", scrollRestoration: true });

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}
