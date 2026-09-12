import { describe, expect, it, vi } from "vitest";

import { createMizanApi, query } from "./client";
import { ApiError } from "./problem";
import { createMemoryStorage, createTokenStore } from "./tokens";

function jsonResponse(status: number, body: unknown, contentType = "application/json"): Response {
  return new Response(JSON.stringify(body), { status, headers: { "content-type": contentType } });
}

describe("createMizanApi", () => {
  it("logs in, sends the bearer and app headers, and parses typed responses", async () => {
    const calls: { url: string; init: RequestInit | undefined }[] = [];
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      calls.push({ url, init });
      if (url.endsWith("/auth/login")) return jsonResponse(200, { access_token: "A1", refresh_token: "R1", expires_in: 900 });
      if (url.endsWith("/me")) return jsonResponse(200, { id: "u1", email: "a@b.dev", display_name: "A", locale: "fr", realm: "STAFF", memberships: [] });
      return jsonResponse(404, {});
    });
    const tokens = createTokenStore("t", createMemoryStorage());
    const api = createMizanApi({ baseUrl: "http://api.test/api/v1/", app: "admin", tokens, fetch: fetchMock as typeof fetch, getBranchId: () => "b1" });
    await api.login({ email: "a@b.dev", password: "x" });
    expect(tokens.get()?.accessToken).toBe("A1");
    const { data } = await api.client.GET("/me");
    expect(data?.email).toBe("a@b.dev");
    const headers = new Headers(calls[1]?.init?.headers);
    expect(headers.get("authorization")).toBe("Bearer A1");
    expect(headers.get("x-mizan-app")).toBe("admin");
    expect(headers.get("x-branch-id")).toBe("b1");
  });

  it("refreshes once on 401 and retries the request", async () => {
    let refreshed = 0;
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const auth = new Headers(init?.headers).get("authorization");
      if (url.endsWith("/auth/refresh")) {
        refreshed += 1;
        return jsonResponse(200, { access_token: "A2", refresh_token: "R2", expires_in: 900 });
      }
      if (auth === "Bearer A2") return jsonResponse(200, { unread: 3 });
      return jsonResponse(401, { code: "unauthorized", message_key: "auth.unauthorized", status: 401 });
    });
    const tokens = createTokenStore("t", createMemoryStorage());
    tokens.set({ accessToken: "A1", refreshToken: "R1", expiresAt: Date.now() + 600_000 });
    const api = createMizanApi({ baseUrl: "http://api.test/api/v1", app: "back-office", tokens, fetch: fetchMock as typeof fetch });
    const { data } = await api.client.GET("/me/notifications/unread-count");
    expect(data).toEqual({ unread: 3 });
    expect(refreshed).toBe(1);
    expect(tokens.get()?.refreshToken).toBe("R2");
  });

  it("turns problem details into ApiError with field errors", async () => {
    const fetchMock = vi.fn(async () =>
      jsonResponse(
        422,
        { code: "validation_error", message_key: "common.validation_error", status: 422, details: [{ loc: ["body", "email"], msg: "invalid" }] },
        "application/problem+json",
      ),
    );
    const tokens = createTokenStore("t", createMemoryStorage());
    const api = createMizanApi({ baseUrl: "http://api.test/api/v1", app: "admin", tokens, fetch: fetchMock as typeof fetch });
    const error = await api.client.POST("/users", { body: { email: "x", display_name: "", realm: "STAFF", locale: "fr" } }).catch((e: unknown) => e);
    expect(ApiError.is(error)).toBe(true);
    expect((error as ApiError).messageKey).toBe("common.validation_error");
    expect((error as ApiError).fieldErrors()).toEqual({ email: "invalid" });
  });

  it("drops the session when the refresh token is rejected", async () => {
    const lost = vi.fn();
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/auth/refresh")) return jsonResponse(401, { code: "invalid_refresh" });
      return jsonResponse(401, { code: "unauthorized" });
    });
    const tokens = createTokenStore("t", createMemoryStorage());
    tokens.set({ accessToken: "", refreshToken: "R1", expiresAt: 0 });
    const api = createMizanApi({ baseUrl: "http://api.test/api/v1", app: "portal", tokens, fetch: fetchMock as typeof fetch, onSessionLost: lost });
    await expect(api.client.GET("/me")).rejects.toBeInstanceOf(ApiError);
    expect(tokens.get()).toBeNull();
    expect(lost).toHaveBeenCalled();
  });

  it("builds query strings without empty values", () => {
    expect(query({ a: 1, b: "", c: undefined, d: false })).toBe("?a=1&d=false");
    expect(query({})).toBe("");
  });
});
