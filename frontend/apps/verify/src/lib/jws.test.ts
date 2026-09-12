// @vitest-environment node
import { CompactSign, exportJWK, generateKeyPair } from "jose";
import { describe, expect, it } from "vitest";

import { tokenOf, verifyOffline } from "./jws";

describe("offline QR verification", () => {
  it("accepts a JWS signed by a cached key and rejects tampering", async () => {
    const { publicKey, privateKey } = await generateKeyPair("EdDSA", { crv: "Ed25519", extractable: true });
    const jwk = { ...(await exportJWK(publicKey)), kid: "nkc-qr-1", alg: "EdDSA" };
    const payload = new TextEncoder().encode(JSON.stringify({ t: "7Q4M2K9X", h: "abc", n: "PV-NKC-2026-0412" }));
    const jws = await new CompactSign(payload).setProtectedHeader({ alg: "EdDSA", kid: "nkc-qr-1" }).sign(privateKey);
    const ok = await verifyOffline(jws, { keys: [jwk] });
    expect(ok.status).toBe("valid");
    if (ok.status === "valid") expect(ok.payload.n).toBe("PV-NKC-2026-0412");
    const [h, p, s] = jws.split(".");
    const tampered = `${h}.${p!.slice(0, -2)}AA.${s}`;
    expect((await verifyOffline(tampered, { keys: [jwk] })).status).toBe("invalid");
    expect((await verifyOffline(jws, { keys: [] })).status).toBe("unknown_key");
    expect((await verifyOffline("garbage", null)).status).toBe("invalid");
  });

  it("extracts tokens from URLs, hashes and raw input", () => {
    expect(tokenOf("https://verify.mizan.mr/d/7Q4M2K9Xabc")).toEqual({ token: "7Q4M2K9Xabc", jws: null });
    expect(tokenOf(" 7Q4M 2K9X ")).toEqual({ token: "7Q4M2K9X", jws: null });
    const jws = "a".repeat(30) + "." + "b".repeat(30) + "." + "c".repeat(30);
    expect(tokenOf(`https://verify.mizan.mr/#${jws}`)).toEqual({ token: null, jws });
    expect(tokenOf("")).toEqual({ token: null, jws: null });
  });
});
