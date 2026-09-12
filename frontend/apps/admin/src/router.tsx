/** Route map of the admin console (SPEC Appendix O). Pages live in ./routes. */
import { LoginPage, NotFoundPage } from "@mizan/app-kit";
import { Outlet, createRootRoute, createRoute, createRouter, redirect, useNavigate } from "@tanstack/react-router";

import { tokens } from "./app";
import { AuditPage } from "./routes/audit";
import { RolesPage, RoleMatrixPage, ViewAsPage } from "./routes/access-roles";
import { MembershipsPage, UsersPage } from "./routes/access-users";
import { CategoriesPage, EquipmentClassesPage, PhaseTemplatesPage, ServicesPage, SieveSetsPage, SpecimenTypesPage, TestDefinitionPage, TestDefinitionsPage } from "./routes/catalog";
import { PrintProfilesPage, TemplatePage, TemplatesPage } from "./routes/documents";
import { InboxPage } from "./routes/inbox";
import { IntegrationsPage, PortalSettingsPage } from "./routes/misc";
import { DeliveryLogPage, MessageTemplatesPage, NotificationRulesPage, ProvidersPage } from "./routes/notifications";
import { NumberingPage } from "./routes/numbering";
import { BranchPage, BranchesPage, DepartmentsPage, SignatoriesPage, TenantPage, TreasuryAccountsPage } from "./routes/org";
import { OverviewPage } from "./routes/overview";
import { PaymentTermsPage } from "./routes/payment-terms";
import { PlatformHealthPage, PlatformKeysPage, PlatformTenantsPage } from "./routes/platform";
import { PriceListsPage, TaxRulesPage } from "./routes/pricing";
import { ProfilePage } from "./routes/profile";
import { SetupWizardPage } from "./routes/setup";
import { VocabulariesPage } from "./routes/vocabularies";
import { WorkflowsPage } from "./routes/workflows";
import { AdminShell } from "./shell";

function RootLayout() {
  return <Outlet />;
}

function NotFound() {
  const navigate = useNavigate();
  return <NotFoundPage onHome={() => void navigate({ to: "/" })} />;
}

function Login() {
  const navigate = useNavigate();
  if (tokens.get()) void navigate({ to: "/" });
  return <LoginPage title="Mizan Labs — Administration" askTenant />;
}

const rootRoute = createRootRoute({ component: RootLayout, notFoundComponent: NotFound });
const loginRoute = createRoute({ getParentRoute: () => rootRoute, path: "/login", component: Login });
const appRoute = createRoute({
  getParentRoute: () => rootRoute,
  id: "app",
  beforeLoad: ({ location }) => {
    if (!tokens.get()) throw redirect({ to: "/login", search: { next: location.pathname } as never });
  },
  component: AdminShell,
});

const page = <P extends string>(path: P, component: () => React.JSX.Element) => createRoute({ getParentRoute: () => appRoute, path, component });

const routes = [
  page("/", OverviewPage),
  page("/inbox", InboxPage),
  page("/settings/profile", ProfilePage),
  page("/platform/tenants", PlatformTenantsPage),
  page("/platform/keys", PlatformKeysPage),
  page("/platform/health", PlatformHealthPage),
  page("/org/tenant", TenantPage),
  page("/org/branches", BranchesPage),
  page("/org/branches/$branchId", BranchPage),
  page("/org/departments", DepartmentsPage),
  page("/org/signatories", SignatoriesPage),
  page("/org/treasury-accounts", TreasuryAccountsPage),
  page("/access/users", UsersPage),
  page("/access/memberships", MembershipsPage),
  page("/access/roles", RolesPage),
  page("/access/roles/$roleId/matrix", RoleMatrixPage),
  page("/access/view-as", ViewAsPage),
  page("/numbering", NumberingPage),
  page("/vocabularies", VocabulariesPage),
  page("/vocabularies/$kind", VocabulariesPage),
  page("/workflows", WorkflowsPage),
  page("/workflows/$kind", WorkflowsPage),
  page("/catalog/categories", CategoriesPage),
  page("/catalog/services", ServicesPage),
  page("/catalog/test-definitions", TestDefinitionsPage),
  page("/catalog/test-definitions/$definitionId", TestDefinitionPage),
  page("/catalog/specimen-types", SpecimenTypesPage),
  page("/catalog/sieve-sets", SieveSetsPage),
  page("/catalog/phase-templates", PhaseTemplatesPage),
  page("/catalog/equipment-classes", EquipmentClassesPage),
  page("/pricing/price-lists", PriceListsPage),
  page("/pricing/tax-rules", TaxRulesPage),
  page("/payment-terms", PaymentTermsPage),
  page("/documents/templates", TemplatesPage),
  page("/documents/templates/$templateId", TemplatePage),
  page("/documents/print-profiles", PrintProfilesPage),
  page("/notifications/rules", NotificationRulesPage),
  page("/notifications/templates", MessageTemplatesPage),
  page("/notifications/providers", ProvidersPage),
  page("/notifications/log", DeliveryLogPage),
  page("/portal", PortalSettingsPage),
  page("/integrations", IntegrationsPage),
  page("/audit", AuditPage),
  page("/setup", SetupWizardPage),
];

const routeTree = rootRoute.addChildren([loginRoute, appRoute.addChildren(routes)]);

export const router = createRouter({ routeTree, defaultPreload: "intent", scrollRestoration: true });

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}
