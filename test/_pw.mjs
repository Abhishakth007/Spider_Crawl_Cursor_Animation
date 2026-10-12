// Starts Chrome through playwright-core. `npm i` installs it; if yours lives somewhere else, point PLAYWRIGHT_DIR at that folder.
import { createRequire } from "node:module";

let chromium;
try {
  ({ chromium } = await import("playwright-core"));
} catch {
  const dir = (process.env.PLAYWRIGHT_DIR || process.env.LOCALAPPDATA + "/hairline-look").replace(/\/?$/, "/");
  chromium = createRequire(dir)("playwright-core").chromium;
}

export const launch = (opts = {}) => chromium.launch({ channel: "chrome", ...opts });
