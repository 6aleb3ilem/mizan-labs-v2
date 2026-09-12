import "@testing-library/jest-dom/vitest";
import { ApiProvider, createMizanApi, createMemoryStorage, createQueryClient, createTokenStore } from "@mizan/api-client";
import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { SessionProvider, useSession } from "./session";

function json(status: number, body: unknown) {
  return new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } });
}

function Probe() {
  const session = useSession();
  return (
    <div>
      <span data-testid="status">{session.status}</span>
      <span data-testid="can">{String(session.can("branch", "configure"))}</span>
      <span data-testid="cannot">{String(session.can("invoice", "issue"))}</span>
    </div>
  );
}

describe("SessionProvider", () => {
  it("loads /me and /me/permissions and answers can()", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/me")) return json(200, { id: "u1", email: "a@b.dev", display_name: "A", locale: "fr", realm: "STAFF", memberships: [{ id: "m1", role_code: "TENANT_ADMIN", role_id: "r1", branch_id: null, department_id: null, account_id: null, project_ids: [], status: "ACTIVE", user_id: "u1" }] });
      if (url.endsWith("/me/permissions")) return json(200, { user_id: "u1", tenant_id: "t1", is_platform_operator: false, grants: [{ resource: "branch", action: "configure", scope: "ALL_BRANCHES", branch_id: null, department_id: null, account_id: null, membership_id: "m1", role: "TENANT_ADMIN", field_groups: [] }] });
      return json(404, {});
    });
    const tokens = createTokenStore("t", createMemoryStorage());
    tokens.set({ accessToken: "A", refreshToken: "R", expiresAt: Date.now() + 600_000 });
    const api = createMizanApi({ baseUrl: "http://api.test/api/v1", app: "admin", tokens, fetch: fetchMock as typeof fetch });
    render(
      <ApiProvider api={api} queryClient={createQueryClient()}>
        <SessionProvider>
          <Probe />
        </SessionProvider>
      </ApiProvider>,
    );
    await waitFor(() => expect(screen.getByTestId("status")).toHaveTextContent("authenticated"));
    expect(screen.getByTestId("can")).toHaveTextContent("true");
    expect(screen.getByTestId("cannot")).toHaveTextContent("false");
  });

  it("is anonymous without tokens", () => {
    const tokens = createTokenStore("t", createMemoryStorage());
    const api = createMizanApi({ baseUrl: "http://api.test/api/v1", app: "admin", tokens, fetch: vi.fn() as unknown as typeof fetch });
    render(
      <ApiProvider api={api} queryClient={createQueryClient()}>
        <SessionProvider>
          <Probe />
        </SessionProvider>
      </ApiProvider>,
    );
    expect(screen.getByTestId("status")).toHaveTextContent("anonymous");
  });
});
