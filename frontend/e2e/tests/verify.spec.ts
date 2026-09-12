import { expect, test } from "@playwright/test";
import { CompactSign, exportJWK, generateKeyPair } from "jose";

test.describe("verification site (SPEC §25)", () => {
  test("checks a QR payload offline against the cached keys", async ({ page }) => {
    const { publicKey, privateKey } = await generateKeyPair("EdDSA", { crv: "Ed25519", extractable: true });
    const jwk = { ...(await exportJWK(publicKey)), kid: "nkc-qr-e2e", alg: "EdDSA" };
    const payload = new TextEncoder().encode(JSON.stringify({ t: "E2ETOKEN01", h: "abc", n: "PV-NKC-2026-0001", k: "REPORT", d: "2026-09-12" }));
    const jws = await new CompactSign(payload).setProtectedHeader({ alg: "EdDSA", kid: "nkc-qr-e2e" }).sign(privateKey);

    await page.goto("http://127.0.0.1:5176/offline");
    await page.evaluate((keys) => localStorage.setItem("mizan.verify.jwks", JSON.stringify({ keys })), [jwk]);
    await page.reload();
    await page.getByLabel("QR (JWS)").fill(jws);
    await page.getByRole("button", { name: /vérifier|verify/i }).click();
    await expect(page.getByRole("status")).toContainText(/valide|valid/i);
    await expect(page.getByText("PV-NKC-2026-0001")).toBeVisible();

    const [h, p, s] = jws.split(".");
    await page.getByLabel("QR (JWS)").fill(`${h}.${p!.slice(0, -2)}AA.${s}`);
    await page.getByRole("button", { name: /vérifier|verify/i }).click();
    await expect(page.getByRole("alert")).toContainText(/invalide|invalid/i);
  });

  test("typed tokens go to the lookup route", async ({ page }) => {
    await page.goto("http://127.0.0.1:5176/");
    await page.getByLabel(/code du document|document code/i).fill("7Q4M2K9XAB");
    await page.getByRole("button", { name: /vérifier|verify/i }).click();
    await expect(page).toHaveURL(/\/d\/7Q4M2K9XAB$/);
  });
});
