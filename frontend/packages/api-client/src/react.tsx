/** React bindings: an `ApiProvider`, `useApi()` and query-key helpers for TanStack Query. */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createContext, useContext, useMemo, type ReactNode } from "react";

import { ApiError, NetworkError } from "./problem";
import type { MizanApi } from "./client";

const ApiContext = createContext<MizanApi | null>(null);

export function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 30_000,
        retry: (count, error) => {
          if (ApiError.is(error)) return error.status >= 500 && count < 2;
          return error instanceof NetworkError && count < 3;
        },
        refetchOnWindowFocus: false,
      },
      mutations: { retry: 0 },
    },
  });
}

export function ApiProvider({
  api,
  queryClient,
  children,
}: {
  api: MizanApi;
  queryClient?: QueryClient;
  children: ReactNode;
}) {
  const client = useMemo(() => queryClient ?? createQueryClient(), [queryClient]);
  return (
    <ApiContext.Provider value={api}>
      <QueryClientProvider client={client}>{children}</QueryClientProvider>
    </ApiContext.Provider>
  );
}

export function useApi(): MizanApi {
  const api = useContext(ApiContext);
  if (!api) throw new Error("useApi must be used inside <ApiProvider>");
  return api;
}

/** Stable query keys: `keys.list("branches", {active: true})`, `keys.one("branches", id)`. */
export const keys = {
  me: () => ["me"] as const,
  permissions: () => ["me", "permissions"] as const,
  inbox: (filters?: Record<string, unknown>) => ["me", "notifications", filters ?? {}] as const,
  unread: () => ["me", "notifications", "unread"] as const,
  list: (resource: string, filters?: Record<string, unknown>) => [resource, "list", filters ?? {}] as const,
  one: (resource: string, id: string) => [resource, "one", id] as const,
  sub: (resource: string, id: string, child: string) => [resource, "one", id, child] as const,
};
