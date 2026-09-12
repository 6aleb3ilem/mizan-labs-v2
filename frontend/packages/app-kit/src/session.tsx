import { ApiError, keys, useApi, type Me, type Permissions } from "@mizan/api-client";
import { setLocale, toLocale } from "@mizan/i18n";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

export type Membership = Me["memberships"][number];

export type SessionValue = {
  status: "loading" | "anonymous" | "authenticated";
  me: Me | null;
  permissions: Permissions | null;
  branchId: string | null;
  setBranchId: (id: string | null) => void;
  /** Branches the user may act in (from memberships); `null` entry means every branch. */
  branchIds: (string | null)[];
  can: (resource: string, action: string) => boolean;
  login: (email: string, password: string, tenantCode?: string) => Promise<void>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
};

const SessionContext = createContext<SessionValue | null>(null);
const BRANCH_KEY = "mizan.branch";

function readBranch(): string | null {
  try {
    return globalThis.localStorage?.getItem(BRANCH_KEY) ?? null;
  } catch {
    return null;
  }
}

type GrantRow = Permissions["grants"][number];

function grantsOf(permissions: Permissions | null): GrantRow[] {
  return permissions?.grants ?? [];
}

/** Session: tokens live in the API client; `/me` and `/me/permissions` are cached queries. */
export function SessionProvider({ children }: { children: ReactNode }) {
  const api = useApi();
  const queryClient = useQueryClient();
  const [hasSession, setHasSession] = useState(() => !!api.tokens.get());
  const [storedBranchId, setBranchState] = useState<string | null>(readBranch);

  useEffect(() => api.tokens.subscribe((session) => setHasSession(!!session)), [api]);

  const meQuery = useQuery({
    queryKey: keys.me(),
    queryFn: async () => (await api.client.GET("/me")).data ?? null,
    enabled: hasSession,
    staleTime: 5 * 60_000,
    retry: false,
  });
  const permissionsQuery = useQuery({
    queryKey: keys.permissions(),
    queryFn: async () => (await api.client.GET("/me/permissions")).data ?? null,
    enabled: hasSession && !!meQuery.data,
    staleTime: 5 * 60_000,
  });

  useEffect(() => {
    if (meQuery.error && ApiError.is(meQuery.error) && meQuery.error.status === 401) api.tokens.set(null);
  }, [meQuery.error, api]);

  useEffect(() => {
    const locale = meQuery.data?.locale;
    if (locale) void setLocale(toLocale(locale));
  }, [meQuery.data?.locale]);

  const me = meQuery.data ?? null;
  const branchIds = useMemo(() => {
    const ids = new Set<string | null>();
    for (const m of me?.memberships ?? []) ids.add(m.branch_id ?? null);
    return Array.from(ids);
  }, [me]);

  const branchId = useMemo(() => {
    if (!me) return storedBranchId;
    const concrete = branchIds.filter((b): b is string => !!b);
    if (storedBranchId && (concrete.includes(storedBranchId) || branchIds.includes(null))) return storedBranchId;
    return concrete[0] ?? null;
  }, [me, branchIds, storedBranchId]);

  const setBranchId = useCallback((id: string | null) => {
    setBranchState(id);
    try {
      if (id) globalThis.localStorage?.setItem(BRANCH_KEY, id);
      else globalThis.localStorage?.removeItem(BRANCH_KEY);
    } catch {
      /* ignore */
    }
  }, []);

  const grants = useMemo(() => grantsOf(permissionsQuery.data ?? null), [permissionsQuery.data]);
  const can = useCallback(
    (resource: string, action: string) => {
      if (me?.realm === "PLATFORM" || permissionsQuery.data?.is_platform_operator) return true;
      return grants.some((g) => g.resource === resource && g.action === action && (g.branch_id == null || !branchId || g.branch_id === branchId));
    },
    [grants, me, branchId, permissionsQuery.data?.is_platform_operator],
  );

  const value = useMemo<SessionValue>(
    () => ({
      status: !hasSession ? "anonymous" : meQuery.isPending || (me && permissionsQuery.isPending) ? "loading" : me ? "authenticated" : "anonymous",
      me,
      permissions: permissionsQuery.data ?? null,
      branchId,
      setBranchId,
      branchIds,
      can,
      async login(email, password, tenantCode) {
        await api.login({ email, password, tenant_code: tenantCode || undefined } as Parameters<typeof api.login>[0]);
        await queryClient.invalidateQueries({ queryKey: keys.me() });
      },
      async logout() {
        await api.logout();
        queryClient.clear();
      },
      async refresh() {
        await queryClient.invalidateQueries({ queryKey: keys.me() });
      },
    }),
    [hasSession, meQuery.isPending, me, permissionsQuery.isPending, permissionsQuery.data, branchId, setBranchId, branchIds, can, api, queryClient],
  );
  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession(): SessionValue {
  const value = useContext(SessionContext);
  if (!value) throw new Error("useSession must be used inside <SessionProvider>");
  return value;
}

export function useCan(resource: string, action: string): boolean {
  return useSession().can(resource, action);
}
