import { ApiError, NetworkError, useApi, type MizanApi } from "@mizan/api-client";
import { messageForKey, useTranslation } from "@mizan/i18n";
import { useToast } from "@mizan/ui";
import { useInfiniteQuery, type QueryKey } from "@tanstack/react-query";
import { useCallback, useEffect, useState } from "react";

export type Page<T> = { items: T[]; next?: string | null; limit?: number };

/** Cursor pagination over a `Page<T>` endpoint (SPEC §8): `items` flattened, `loadMore` while `hasMore`. */
export function usePagedQuery<T>(queryKey: QueryKey, fetchPage: (api: MizanApi, after: string | null) => Promise<Page<T> | undefined>, options?: { enabled?: boolean }) {
  const api = useApi();
  const query = useInfiniteQuery({
    queryKey,
    queryFn: async ({ pageParam }) => (await fetchPage(api, pageParam)) ?? { items: [], next: null, limit: 0 },
    initialPageParam: null as string | null,
    getNextPageParam: (last) => last.next ?? null,
    enabled: options?.enabled ?? true,
  });
  const items = query.data?.pages.flatMap((p) => p.items) ?? [];
  return {
    items,
    query,
    loading: query.isPending || query.isFetchingNextPage,
    hasMore: !!query.hasNextPage,
    loadMore: () => void query.fetchNextPage(),
    error: query.error,
    refetch: () => void query.refetch(),
  };
}

/** Translate any thrown error (problem details, network, unknown) for the user. */
export function useErrorMessage() {
  const { t } = useTranslation();
  return useCallback(
    (error: unknown): string => {
      if (ApiError.is(error)) return messageForKey(error.messageKey, error.problem.params);
      if (error instanceof NetworkError) return t("errors.common.network");
      return t("errors.common.internal_error");
    },
    [t],
  );
}

/** Show a translated error toast for a mutation failure; returns the field errors for forms. */
export function useErrorToast() {
  const toast = useToast();
  const message = useErrorMessage();
  const { t } = useTranslation();
  return useCallback(
    (error: unknown): Record<string, string> => {
      toast.error(t("common.error_title"), message(error));
      return ApiError.is(error) ? error.fieldErrors() : {};
    },
    [toast, message, t],
  );
}

export function useOnline(): boolean {
  const [online, setOnline] = useState(() => globalThis.navigator?.onLine ?? true);
  useEffect(() => {
    const up = () => setOnline(true);
    const down = () => setOnline(false);
    window.addEventListener("online", up);
    window.addEventListener("offline", down);
    return () => {
      window.removeEventListener("online", up);
      window.removeEventListener("offline", down);
    };
  }, []);
  return online;
}

/** Warn before leaving with unsaved changes (SPEC §21.5). */
export function useUnsavedChangesGuard(dirty: boolean) {
  useEffect(() => {
    if (!dirty) return;
    const handler = (event: BeforeUnloadEvent) => {
      event.preventDefault();
    };
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [dirty]);
}

export function useDebounced<T>(value: T, delay = 250): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const id = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(id);
  }, [value, delay]);
  return debounced;
}

export type Bilingual = { fr: string; en: string };

/** Page-local bilingual strings (FR/EN, SPEC §21.7) without touching the shared catalogue. */
export function useTx(): (text: Bilingual, params?: Record<string, string | number>) => string {
  const { i18n } = useTranslation();
  return useCallback(
    (text, params) => {
      let value = i18n.language?.toLowerCase().startsWith("en") ? text.en : text.fr;
      for (const [key, param] of Object.entries(params ?? {})) value = value.replaceAll(`{{${key}}}`, String(param));
      return value;
    },
    [i18n.language],
  );
}
