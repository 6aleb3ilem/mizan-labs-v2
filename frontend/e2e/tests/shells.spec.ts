import { expect, test } from "@playwright/test";

test.describe("application shells", () => {
  test("back-office asks for a sign-in", async ({ page }) => {
    await page.goto("http://127.0.0.1:5173/home");
    await expect(page).toHaveURL(/\/login(\?.*)?$/);
    await expect(page.getByRole("heading", { name: "Mizan Labs" })).toBeVisible();
    await expect(page.getByLabel(/e-mail/i)).toBeVisible();
  });

  test("admin console login form has the tenant code", async ({ page }) => {
    await page.goto("http://127.0.0.1:5174/org/branches");
    await expect(page).toHaveURL(/\/login(\?.*)?$/);
    await expect(page.getByLabel(/code société|company code/i)).toBeVisible();
  });

  test("portal login renders", async ({ page }) => {
    await page.goto("http://127.0.0.1:5175/");
    await expect(page).toHaveURL(/\/login(\?.*)?$/);
    await expect(page.getByRole("button", { name: /se connecter|sign in/i })).toBeVisible();
  });
});
