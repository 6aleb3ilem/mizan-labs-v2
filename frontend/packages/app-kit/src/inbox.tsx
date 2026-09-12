import { keys, openEventStream, useApi, type Notification } from "@mizan/api-client";
import { useToast } from "@mizan/ui";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

import { useSession } from "./session";

export type InboxValue = { unread: number; live: "connecting" | "open" | "closed"; markRead: (ids: string[]) => Promise<void>; markAllRead: () => Promise<void> };

const InboxContext = createContext<InboxValue | null>(null);

/** Unread counter and live notifications over SSE, with a toast for each new one (SPEC §22.1). */
export function InboxProvider({ children, onOpen }: { children: ReactNode; onOpen?: (notification: Notification) => void }) {
  const api = useApi();
  const session = useSession();
  const queryClient = useQueryClient();
  const toast = useToast();
  const [live, setLive] = useState<"connecting" | "open" | "closed">("closed");
  const authenticated = session.status === "authenticated";

  const unreadQuery = useQuery({
    queryKey: keys.unread(),
    queryFn: async () => (await api.client.GET("/me/notifications/unread-count")).data?.unread ?? 0,
    enabled: authenticated,
    refetchInterval: 120_000,
  });

  useEffect(() => {
    if (!authenticated) return;
    const handle = openEventStream({
      baseUrl: api.baseUrl,
      getAccessToken: async () => {
        const session = api.tokens.get();
        if (!session) return null;
        if (session.expiresAt - 30_000 > Date.now()) return session.accessToken;
        return (await api.refresh())?.accessToken ?? null;
      },
      onStatus: setLive,
      onEvent: (event) => {
        if (event.event === "inbox") {
          const data = event.data as { unread?: number };
          if (typeof data?.unread === "number") queryClient.setQueryData(keys.unread(), data.unread);
          return;
        }
        if (event.event === "notification") {
          const data = event.data as Partial<Notification> & { title?: string; body?: string; link?: string };
          queryClient.setQueryData(keys.unread(), (old: number | undefined) => (old ?? 0) + 1);
          void queryClient.invalidateQueries({ queryKey: ["me", "notifications"] });
          toast.show({
            title: data.title ?? "",
            description: data.body,
            action: data.link && onOpen ? { label: "→", onClick: () => onOpen(data as Notification) } : undefined,
          });
          return;
        }
        // Domain events: refresh the lists that may have changed.
        const type = String(event.event).split(".")[0];
        if (type) void queryClient.invalidateQueries({ queryKey: [type] });
      },
    });
    return () => handle.close();
  }, [authenticated, api, queryClient, toast, onOpen]);

  const value = useMemo<InboxValue>(
    () => ({
      unread: unreadQuery.data ?? 0,
      live,
      async markRead(ids) {
        await api.client.POST("/me/notifications:read", { body: { ids } });
        await queryClient.invalidateQueries({ queryKey: ["me", "notifications"] });
      },
      async markAllRead() {
        await api.client.POST("/me/notifications:read-all");
        await queryClient.invalidateQueries({ queryKey: ["me", "notifications"] });
      },
    }),
    [unreadQuery.data, live, api, queryClient],
  );
  return <InboxContext.Provider value={value}>{children}</InboxContext.Provider>;
}

export function useInbox(): InboxValue {
  const value = useContext(InboxContext);
  if (!value) throw new Error("useInbox must be used inside <InboxProvider>");
  return value;
}
