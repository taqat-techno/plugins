// "app" permissions mode: use what is already approved for the app instead of asking for a new list.
import test from "node:test";
import assert from "node:assert/strict";
import { resolveConfig } from "../server/config.mjs";
import { createAuth, scopeString } from "../server/auth.mjs";
import { fakeFetch, home, env, json } from "./_helpers.mjs";
// Never read the real ~/.m365-plugin of the person running the tests.
const ISOLATED_HOME = (await import("node:fs")).mkdtempSync((await import("node:path")).join((await import("node:os")).tmpdir(), "m365-cfg-"));

test("scope mode: default asks for the module list, 'app' asks for the app's approved permissions only", () => {
  assert.equal(resolveConfig({ M365_HOME: ISOLATED_HOME }).scopeMode, "requested");
  assert.ok(resolveConfig({ M365_HOME: ISOLATED_HOME }).scopes.includes("Mail.Send"));
  const app = resolveConfig({ M365_HOME: ISOLATED_HOME, M365_SCOPE_MODE: "App" });
  assert.equal(app.scopeMode, "app"); assert.deepEqual(app.scopes, [".default"]);
  assert.equal(resolveConfig({ M365_HOME: ISOLATED_HOME, M365_PLUGIN_SCOPE_MODE: "app", M365_SCOPE_MODE: "requested" }).scopeMode, "app", "plugin setting wins");
  assert.equal(resolveConfig({ M365_HOME: ISOLATED_HOME, M365_SCOPE_MODE: "bogus" }).scopeMode, "requested");
  assert.equal(resolveConfig({ M365_HOME: ISOLATED_HOME, M365_SCOPE_MODE: "app", M365_SCOPES: "Mail.Read" }).scopeMode, "app");
  assert.deepEqual(resolveConfig({ M365_HOME: ISOLATED_HOME, M365_SCOPE_MODE: "app", M365_SCOPES: "Mail.Read" }).scopes, ["Mail.Read"], "an explicit list still wins");
  assert.equal(scopeString([".default"]), "https://graph.microsoft.com/.default offline_access openid profile");
});

test("scope mode 'app': the sign-in request carries .default, never the plugin's own permission list", async () => {
  const h = home();
  let device;
  const f = fakeFetch([[/devicecode/, ({ body }) => { device = new URLSearchParams(body); return json({ device_code: "dc", user_code: "ABCD", verification_uri: "https://x/device", expires_in: 60, interval: 1 }); }],
    [/oauth2\/v2\.0\/token/, () => json({ error: "authorization_pending" }, 400)]]);
  const a = createAuth(resolveConfig(env(h, { M365_SCOPE_MODE: "app" })), { fetch: f, sleep: async () => { throw new Error("stop"); } });
  await a.startSignIn({ mode: "device-code" });
  assert.equal(device.get("scope"), "https://graph.microsoft.com/.default offline_access openid profile");
  assert.equal(a.status().permissions, "app");
  assert.ok(!device.get("scope").includes("Mail.Send"));
});
