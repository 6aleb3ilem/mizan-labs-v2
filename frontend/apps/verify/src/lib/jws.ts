/**
 * Offline verification of the QR payload (SPEC §18.4, ADR 0004): the QR carries a compact JWS
 * (EdDSA) whose `kid` selects a branch key from the cached JWKS. The payload binds the document
 * token and the content hash; a valid signature proves the document was issued by the branch.
 */
import { compactVerify, importJWK, type JWK } from "jose";

export type QrPayload = { t?: string; h?: string; k?: string; n?: string; d?: string; b?: string; [key: string]: unknown };
export type Jwks = { keys: (JWK & { kid?: string })[] };
export type OfflineResult = { status: "valid"; payload: QrPayload; kid: string } | { status: "invalid"; reason: string } | { status: "unknown_key"; kid: string | null };

const JWKS_KEY = "mizan.verify.jwks";

export function loadCachedJwks(): Jwks | null {
  try {
    const raw = globalThis.localStorage?.getItem(JWKS_KEY);
    return raw ? (JSON.parse(raw) as Jwks) : null;
  } catch {
    return null;
  }
}

export function storeJwks(jwks: Jwks): void {
  try {
    globalThis.localStorage?.setItem(JWKS_KEY, JSON.stringify(jwks));
  } catch {
    /* ignore */
  }
}

export async function fetchJwks(baseUrl: string): Promise<Jwks> {
  const response = await fetch(`${baseUrl.replace(/\/$/, "")}/verify/keys`, { headers: { Accept: "application/json" } });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  const jwks = (await response.json()) as Jwks;
  storeJwks(jwks);
  return jwks;
}

function headerOf(jws: string): { kid?: string; alg?: string } | null {
  const head = jws.split(".")[0];
  if (!head) return null;
  try {
    const json = atob(head.replace(/-/g, "+").replace(/_/g, "/"));
    return JSON.parse(json) as { kid?: string; alg?: string };
  } catch {
    return null;
  }
}

/** Verify a compact JWS against a JWKS; never throws. */
export async function verifyOffline(jws: string, jwks: Jwks | null): Promise<OfflineResult> {
  const header = headerOf(jws.trim());
  if (!header) return { status: "invalid", reason: "malformed" };
  const kid = header.kid ?? null;
  const key = jwks?.keys.find((k) => k.kid === kid);
  if (!key) return { status: "unknown_key", kid };
  try {
    const publicKey = await importJWK(key, header.alg ?? "EdDSA");
    const { payload } = await compactVerify(jws.trim(), publicKey, { algorithms: ["EdDSA"] });
    const decoded = JSON.parse(new TextDecoder().decode(payload)) as QrPayload;
    return { status: "valid", payload: decoded, kid: kid ?? "" };
  } catch (error) {
    return { status: "invalid", reason: error instanceof Error ? error.message : "signature" };
  }
}

/** The document token of a scanned QR: from the JWS payload, or a typed token. */
export function tokenOf(input: string): { token: string | null; jws: string | null } {
  const text = input.trim();
  if (!text) return { token: null, jws: null };
  if (text.split(".").length === 3 && text.length > 60) return { token: null, jws: text };
  const fromUrl = text.match(/\/d\/([A-Za-z0-9_-]{8,})/);
  if (fromUrl?.[1]) return { token: fromUrl[1], jws: null };
  const hash = text.match(/#(.+)$/);
  if (hash?.[1] && hash[1].split(".").length === 3) return { token: null, jws: hash[1] };
  return { token: text.replace(/\s+/g, ""), jws: null };
}
