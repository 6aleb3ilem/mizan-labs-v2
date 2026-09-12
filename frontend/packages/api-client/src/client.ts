/**
 * The typed HTTP client: `openapi-fetch` over the generated paths, with a fetch wrapper that
 * adds the bearer token, the app and branch headers, refreshes an expired session once
 * (single flight) and turns problem-detail responses into `ApiError`.
 */
import createClient, { type Client } from "openapi-fetch";

import type { paths } from "./generated/schema";
import { ApiError, NetworkError, problemFrom } from "./problem";
import type { Session, TokenStore } from "./tokens";

export type AppName = "back-office" | "admin" | "portal" | "verify";

export type ApiOptions = {
  baseUrl: string;
  app: AppName;
  tokens: TokenStore;
  /** Branch selected in the top bar (X-Branch-Id). */
  getBranchId?: () => string | null | undefined;
  getLocale?: () => string;
  onSessionLost?: () => void;
  fetch?: typeof fetch;
};

export type Api = Client<paths>;

type LoginBody = paths["/auth/login"]["post"]["requestBody"]["content"]["application/json"];
type TokenResponse = { access_token: string; refresh_token: string; expires_in: number; token_type?: string };

export type MizanApi = {
  client: Api;
  tokens: TokenStore;
  baseUrl: string;
  login(body: LoginBody): Promise<TokenResponse>;
  logout(): Promise<void>;
  refresh(): Promise<Session | null>;
  /** Fetch a binary (PDF) with the same auth handling. */
  fetchBlob(path: string, init?: RequestInit): Promise<Blob>;
  /** A raw authenticated fetch of an absolute API path. */
  fetch(path: string, init?: RequestInit): Promise<Response>;
};

const REFRESH_SKEW_MS = 20_000;

export function sessionFromTokens(t: TokenResponse): Session {
  return {
    accessToken: t.access_token,
    refreshToken: t.refresh_token,
    expiresAt: Date.now() + t.expires_in * 1000,
  };
}

export function createMizanApi(options: ApiOptions): MizanApi {
  const baseFetch = options.fetch ?? ((input, init) => globalThis.fetch(input, init));
  const baseUrl = options.baseUrl.replace(/\/$/, "");
  let refreshing: Promise<Session | null> | null = null;

  async function refresh(): Promise<Session | null> {
    if (refreshing) return refreshing;
    const session = options.tokens.get();
    if (!session?.refreshToken) return null;
    refreshing = (async () => {
      try {
        const response = await baseFetch(`${baseUrl}/auth/refresh`, {
          method: "POST",
          headers: { "Content-Type": "application/json", Accept: "application/json", "X-Mizan-App": options.app },
          body: JSON.stringify({ refresh_token: session.refreshToken }),
        });
        if (!response.ok) {
          options.tokens.set(null);
          options.onSessionLost?.();
          return null;
        }
        const next = sessionFromTokens((await response.json()) as TokenResponse);
        options.tokens.set(next);
        return next;
      } catch {
        return session; // network problem: keep the current tokens, the caller retries later
      } finally {
        refreshing = null;
      }
    })();
    return refreshing;
  }

  async function accessToken(): Promise<string | null> {
    const session = options.tokens.get();
    if (!session) return null;
    if (session.accessToken && session.expiresAt - REFRESH_SKEW_MS > Date.now()) return session.accessToken;
    const refreshed = await refresh();
    return refreshed?.accessToken ?? null;
  }

  function decorate(init: RequestInit | undefined, token: string | null): RequestInit {
    const headers = new Headers(init?.headers ?? {});
    headers.set("Accept", headers.get("Accept") ?? "application/json");
    headers.set("X-Mizan-App", options.app);
    if (token) headers.set("Authorization", `Bearer ${token}`);
    const branch = options.getBranchId?.();
    if (branch) headers.set("X-Branch-Id", branch);
    const locale = options.getLocale?.();
    if (locale) headers.set("Accept-Language", locale);
    return { ...init, headers };
  }

  const authFetch: typeof fetch = async (input, init) => {
    const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;
    let response: Response;
    try {
      response = await baseFetch(url, decorate(init, await accessToken()));
    } catch (error) {
      throw new NetworkError(error);
    }
    if (response.status === 401 && options.tokens.get()?.refreshToken) {
      const session = await refresh();
      if (session?.accessToken) {
        try {
          response = await baseFetch(url, decorate(init, session.accessToken));
        } catch (error) {
          throw new NetworkError(error);
        }
      }
    }
    return response;
  };

  const client = createClient<paths>({ baseUrl, fetch: authFetch });
  client.use({
    async onResponse({ response }) {
      if (response.ok) return response;
      const contentType = response.headers.get("content-type") ?? "";
      const body: unknown = contentType.includes("json") ? await response.clone().json().catch(() => null) : null;
      throw new ApiError(problemFrom(response.status, body));
    },
  });

  async function rawFetch(path: string, init?: RequestInit): Promise<Response> {
    const response = await authFetch(`${baseUrl}${path}`, init);
    if (!response.ok) {
      const body: unknown = await response.clone().json().catch(() => null);
      throw new ApiError(problemFrom(response.status, body));
    }
    return response;
  }

  return {
    client,
    tokens: options.tokens,
    baseUrl,
    async login(body) {
      const response = await baseFetch(`${baseUrl}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json", "X-Mizan-App": options.app },
        body: JSON.stringify(body),
      }).catch((error: unknown) => {
        throw new NetworkError(error);
      });
      if (!response.ok) {
        const problem: unknown = await response.json().catch(() => null);
        throw new ApiError(problemFrom(response.status, problem));
      }
      const tokens = (await response.json()) as TokenResponse;
      options.tokens.set(sessionFromTokens(tokens));
      return tokens;
    },
    async logout() {
      const session = options.tokens.get();
      options.tokens.set(null);
      if (!session?.refreshToken) return;
      try {
        await baseFetch(`${baseUrl}/auth/logout`, {
          method: "POST",
          headers: { "Content-Type": "application/json", "X-Mizan-App": options.app },
          body: JSON.stringify({ refresh_token: session.refreshToken }),
        });
      } catch {
        /* best effort */
      }
    },
    refresh,
    async fetchBlob(path, init) {
      const response = await rawFetch(path, init);
      return response.blob();
    },
    fetch: rawFetch,
  };
}

/** Build a query string, dropping empty values (helper for list filters). */
export function query(params: Record<string, string | number | boolean | null | undefined>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === "") continue;
    search.set(key, String(value));
  }
  const text = search.toString();
  return text ? `?${text}` : "";
}
