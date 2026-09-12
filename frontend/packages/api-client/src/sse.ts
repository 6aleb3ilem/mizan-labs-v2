/** The live event stream (SSE over LISTEN/NOTIFY, SPEC §27.3): reconnects with a fresh token. */

export type StreamEvent = { id?: string; event: string; data: unknown };

export type StreamOptions = {
  baseUrl: string;
  getAccessToken: () => Promise<string | null>;
  onEvent: (event: StreamEvent) => void;
  onStatus?: (status: "connecting" | "open" | "closed") => void;
  /** Event names to listen for besides `message` (EventSource needs explicit listeners). */
  events?: string[];
  eventSource?: typeof EventSource;
};

export type StreamHandle = { close(): void };

const DEFAULT_EVENTS = ["notification", "inbox"];

export function openEventStream(options: StreamOptions): StreamHandle {
  const EventSourceCtor = options.eventSource ?? globalThis.EventSource;
  let source: EventSource | null = null;
  let closed = false;
  let retryMs = 3000;

  async function connect(): Promise<void> {
    if (closed) return;
    options.onStatus?.("connecting");
    const token = await options.getAccessToken();
    if (closed) return;
    if (!token) {
      schedule();
      return;
    }
    const url = `${options.baseUrl.replace(/\/$/, "")}/events/stream?access_token=${encodeURIComponent(token)}`;
    source = new EventSourceCtor(url);
    const names = new Set([...DEFAULT_EVENTS, ...(options.events ?? [])]);
    const handler = (name: string) => (raw: Event) => {
      const message = raw as MessageEvent<string>;
      let data: unknown = message.data;
      try {
        data = JSON.parse(message.data);
      } catch {
        /* plain text */
      }
      options.onEvent({ id: message.lastEventId || undefined, event: name, data });
    };
    for (const name of names) source.addEventListener(name, handler(name));
    source.onmessage = handler("message");
    source.onopen = () => {
      retryMs = 3000;
      options.onStatus?.("open");
    };
    source.onerror = () => {
      // The token may have expired (15 min): rebuild the connection with a fresh one.
      source?.close();
      source = null;
      options.onStatus?.("closed");
      schedule();
    };
  }

  function schedule(): void {
    if (closed) return;
    setTimeout(() => void connect(), retryMs);
    retryMs = Math.min(retryMs * 2, 60_000);
  }

  void connect();
  return {
    close() {
      closed = true;
      source?.close();
      source = null;
      options.onStatus?.("closed");
    },
  };
}
