import { defineConfig, devices } from "@playwright/test";

const baseURL = process.env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:3100";
const skipWebServer = process.env.PLAYWRIGHT_SKIP_WEBSERVER === "1";

export default defineConfig({
  testDir: "./tests",
  fullyParallel: false,
  workers: 1,
  timeout: 90_000,
  reporter: "list",
  use: {
    baseURL,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    launchOptions: { channel: process.env.PLAYWRIGHT_BROWSER === "chromium" ? undefined : "msedge" },
  },
  projects: [{ name: "desktop", use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 1000 } } }],
  webServer: skipWebServer ? undefined : {
    command: "npm run dev --workspace @prisme/web -- --port 3100",
    url: "http://127.0.0.1:3100",
    reuseExistingServer: !process.env.CI,
    timeout: 300_000,
    env: { NEXT_TELEMETRY_DISABLED: "1" },
  },
});
