/** Session tokens for the SPAs: short-lived access token in memory, rotating refresh token persisted. */

export type Session = {
  accessToken: string;
  refreshToken: string;
  expiresAt: number; // epoch ms
};

export type TokenStore = {
  get(): Session | null;
  set(session: Session | null): void;
  subscribe(listener: (session: Session | null) => void): () => void;
};

export function createTokenStore(storageKey = "mizan.session", storage?: Storage): TokenStore {
  const backing = storage ?? safeStorage();
  let current: Session | null = read();
  const listeners = new Set<(session: Session | null) => void>();

  function read(): Session | null {
    try {
      const raw = backing?.getItem(storageKey);
      if (!raw) return null;
      const parsed = JSON.parse(raw) as Partial<Session>;
      if (typeof parsed.refreshToken !== "string") return null;
      return {
        accessToken: typeof parsed.accessToken === "string" ? parsed.accessToken : "",
        refreshToken: parsed.refreshToken,
        expiresAt: typeof parsed.expiresAt === "number" ? parsed.expiresAt : 0,
      };
    } catch {
      return null;
    }
  }

  return {
    get: () => current,
    set(session) {
      current = session;
      try {
        if (session) backing?.setItem(storageKey, JSON.stringify(session));
        else backing?.removeItem(storageKey);
      } catch {
        /* private mode or quota: keep the session in memory only */
      }
      for (const listener of listeners) listener(session);
    },
    subscribe(listener) {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
  };
}

function safeStorage(): Storage | undefined {
  try {
    return globalThis.sessionStorage ?? undefined;
  } catch {
    return undefined;
  }
}

export function createMemoryStorage(): Storage {
  const map = new Map<string, string>();
  return {
    get length() {
      return map.size;
    },
    clear: () => map.clear(),
    getItem: (k) => map.get(k) ?? null,
    key: (i) => Array.from(map.keys())[i] ?? null,
    removeItem: (k) => {
      map.delete(k);
    },
    setItem: (k, v) => {
      map.set(k, v);
    },
  };
}
