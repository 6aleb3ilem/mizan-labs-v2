import { existsSync } from "node:fs";

import { defineConfig, devices } from "@playwright/test";

/** A pre-installed Chromium (CI image or sandbox) can be pointed to with PLAYWRIGHT_CHROMIUM_EXECUTABLE. */
const executablePath = process.env["PLAYWRIGHT_CHROMIUM_EXECUTABLE"] ?? (existsSync("/opt/pw-browsers/chromium") ? "/opt/pw-browsers/chromium" : undefined);
const launchOptions = executablePath ? { executablePath } : {};

/** Serves the built SPAs with `vite preview` (no API needed for the smoke paths). */
const apps = [
  { name: "back-office", port: 5173 },
  { name: "admin", port: 5174 },
  { name: "portal", port: 5175 },
  { name: "verify", port: 5176 },
];

export default defineConfig({
  testDir: "./tests",
  timeout: 30_000,
  fullyParallel: true,
  retries: process.env["CI"] ? 1 : 0,
  reporter: process.env["CI"] ? [["github"], ["html", { open: "never" }]] : "list",
  use: { trace: "retain-on-failure", locale: "fr-FR", launchOptions },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"] } },
    { name: "phone", use: { ...devices["Pixel 7"] } },
  ],
  webServer: apps.map((app) => ({
    command: `pnpm --filter @mizan/${app.name} preview`,
    url: `http://127.0.0.1:${app.port}`,
    reuseExistingServer: !process.env["CI"],
    timeout: 60_000,
  })),
});
