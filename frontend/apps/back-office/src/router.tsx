/** Route map of the back-office (SPEC Appendix O). */
import { LoginPage, NotFoundPage } from "@mizan/app-kit";
import { Outlet, createRootRoute, createRoute, createRouter, redirect, useNavigate } from "@tanstack/react-router";

import { tokens } from "./app";
import { HomePage } from "./routes/home";
import { InboxPage } from "./routes/inbox";
import { ProfilePage } from "./routes/profile";
import { ProjectPage, ProjectsPage } from "./routes/projects";
import { SearchPage } from "./routes/search";
import { SpacePage } from "./routes/spaces";
import { BackOfficeShell } from "./shell";

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
  return <LoginPage title="Mizan Labs" askTenant />;
}

const rootRoute = createRootRoute({ component: RootLayout, notFoundComponent: NotFound });
const loginRoute = createRoute({ getParentRoute: () => rootRoute, path: "/login", component: Login });
const appRoute = createRoute({
  getParentRoute: () => rootRoute,
  id: "app",
  beforeLoad: () => {
    if (!tokens.get()) throw redirect({ to: "/login" });
  },
  component: BackOfficeShell,
});
const page = <P extends string>(path: P, component: () => React.JSX.Element) => createRoute({ getParentRoute: () => appRoute, path, component });

const routeTree = rootRoute.addChildren([
  loginRoute,
  appRoute.addChildren([
    createRoute({ getParentRoute: () => appRoute, path: "/", beforeLoad: () => { throw redirect({ to: "/home" }); } }),
    page("/home", HomePage),
    page("/search", SearchPage),
    page("/inbox", InboxPage),
    page("/projects", ProjectsPage),
    page("/projects/$projectId", ProjectPage),
    page("/projects/$projectId/$tab", ProjectPage),
    page("/settings/profile", ProfilePage),
    page("/$space/$screen", SpacePage),
    page("/$space/$screen/$id", SpacePage),
    page("/$space/$screen/$id/$sub", SpacePage),
    page("/$space/$screen/$id/$sub/$n/$action", SpacePage),
  ]),
]);

export const router = createRouter({ routeTree, defaultPreload: "intent", scrollRestoration: true });

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}
