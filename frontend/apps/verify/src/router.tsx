/** Verification site routes (SPEC §25, Appendix O): /#<jws>, /d/:token, /keys, /transparency, /offline. */
import { NotFoundPage } from "@mizan/app-kit";
import { Outlet, createRootRoute, createRoute, createRouter, useNavigate } from "@tanstack/react-router";

import { KeysPage } from "./routes/keys";
import { LookupPage } from "./routes/lookup";
import { OfflinePage } from "./routes/offline";
import { TransparencyPage } from "./routes/transparency";
import { VerifyShell } from "./shell";

function NotFound() {
  const navigate = useNavigate();
  return <NotFoundPage onHome={() => void navigate({ to: "/" })} />;
}

const rootRoute = createRootRoute({
  component: () => (
    <VerifyShell>
      <Outlet />
    </VerifyShell>
  ),
  notFoundComponent: NotFound,
});
const routeTree = rootRoute.addChildren([
  createRoute({ getParentRoute: () => rootRoute, path: "/", component: LookupPage }),
  createRoute({ getParentRoute: () => rootRoute, path: "/d/$token", component: LookupPage }),
  createRoute({ getParentRoute: () => rootRoute, path: "/keys", component: KeysPage }),
  createRoute({ getParentRoute: () => rootRoute, path: "/transparency", component: TransparencyPage }),
  createRoute({ getParentRoute: () => rootRoute, path: "/offline", component: OfflinePage }),
]);

export const router = createRouter({ routeTree, defaultPreload: "intent" });

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}
