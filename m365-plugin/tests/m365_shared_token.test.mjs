// Shared token file mode: reuse a refresh token another tool already holds, without ever leaking or clobbering it.
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync, writeFileSync, existsSync } from "node:fs";
import { join } from "node:path";
import { createContext } from "../server/context.mjs";
import { resolveConfig } from "../server/config.mjs";
import { fakeFetch, home, json, TOKEN } from "./_helpers.mjs";
// Never read the real ~/.m365-plugin of the person running the tests.
const ISOLATED_HOME = (await import("node:fs")).mkdtempSync((await import("node:path")).join((await import("node:os")).tmpdir(), "m365-cfg-"));

function setup(over = {}, routes = null) {
  const h = home();
  const tokenFile = join(h, "owner-refresh.txt"), secretFile = join(h, "owner-secret.txt");
  writeFileSync(tokenFile, "RT-ORIGINAL\n"); writeFileSync(secretFile, "SUPER-SECRET\n");
  const seen = [];
  const f = fakeFetch(routes ?? [
    [TOKEN, ({ body }) => { const p = new URLSearchParams(body); seen.push(p); return json({ access_token: "AT-1", refresh_token: "RT-ROTATED", expires_in: 3600 }); }],
    [/mailFolders\/inbox\/messages/, { value: [] }],
  ]);
  const env = { M365_CLIENT_ID: "cid", M365_TENANT: "t-id", M365_HOME: join(h, "home"), M365_REFRESH_TOKEN_FILE: tokenFile, M365_CLIENT_SECRET_FILE: secretFile, ...over };
  const c = createContext(env, { fetch: f, sleep: async () => {}, now: () => Date.parse("2026-11-06T00:00:00Z") });
  return { c, f, seen, tokenFile, secretFile, h };
}

test("shared mode: the app's permissions, the secret and the owner's token are used; the rotated token is written back", async () => {
  const { c, seen, tokenFile } = setup();
  assert.equal(c.ctx.cfg.scopeMode, "app");
  await c.callTool("email_list_recent", {});
  const p = seen[0];
  assert.equal(p.get("grant_type"), "refresh_token"); assert.equal(p.get("refresh_token"), "RT-ORIGINAL"); assert.equal(p.get("client_secret"), "SUPER-SECRET");
  assert.equal(p.get("scope"), "https://graph.microsoft.com/.default offline_access openid profile");
  assert.equal(readFileSync(tokenFile, "utf8"), "RT-ROTATED", "the owner's file now holds the newest token, exactly as the owner would write it");
  assert.ok(!existsSync(join(c.ctx.cfg.home, "token-cache.json")), "no second copy of the token is kept");
});

test("shared mode: if the owner rotated the token meanwhile (invalid_grant), the newer one is retried once", async () => {
  const h = home(); const tokenFile = join(h, "rt.txt"); writeFileSync(tokenFile, "RT-OLD");
  let n = 0; const used = [];
  const f = fakeFetch([[TOKEN, ({ body }) => { const t = new URLSearchParams(body).get("refresh_token"); used.push(t); if (++n === 1) { writeFileSync(tokenFile, "RT-NEWER-FROM-OWNER"); return json({ error: "invalid_grant" }, 400); } return json({ access_token: "AT", refresh_token: "RT-X", expires_in: 3600 }); }], [/messages/, { value: [] }]]);
  const c = createContext({ M365_CLIENT_ID: "c", M365_HOME: join(h, "home"), M365_REFRESH_TOKEN_FILE: tokenFile }, { fetch: f, sleep: async () => {} });
  await c.callTool("email_list_recent", {});
  assert.deepEqual(used, ["RT-OLD", "RT-NEWER-FROM-OWNER"]);
});

test("shared mode: write-back can be turned off and then the file is never modified", async () => {
  const { c, tokenFile } = setup({ M365_REFRESH_TOKEN_WRITEBACK: "false" });
  await c.callTool("email_list_recent", {});
  assert.equal(readFileSync(tokenFile, "utf8"), "RT-ORIGINAL\n");
});

test("shared mode: sign-in is not offered, sign-out leaves the owner's file, status never shows a secret", async () => {
  const { c, tokenFile } = setup();
  await assert.rejects(c.callTool("m365_sign_in", {}), (e) => e.code === "MANAGED_EXTERNALLY" && /owns the token file/.test(e.hint));
  const s = await c.callTool("m365_auth_status", {});
  assert.equal(s.signed_in, true); assert.equal(s.auth_source, "shared token file"); assert.equal(s.permissions, "app");
  assert.equal((await c.callTool("m365_sign_out", {})).signed_out, true);
  assert.equal(readFileSync(tokenFile, "utf8"), "RT-ORIGINAL\n", "sign-out never deletes another tool's token");
  assert.ok(!JSON.stringify(s).includes("RT-ORIGINAL") && !JSON.stringify(s).includes("SUPER-SECRET"));
});

test("shared mode: a missing or empty token file asks to sign in with the owning tool; a missing secret file is a clear error", async () => {
  const { c, tokenFile } = setup();
  writeFileSync(tokenFile, "");
  await assert.rejects(c.callTool("email_list_recent", {}), (e) => e.code === "NOT_SIGNED_IN" && /owns that file/.test(e.hint));
  assert.equal((await c.callTool("m365_auth_status", {})).signed_in, false);
  const m = setup({ M365_CLIENT_SECRET_FILE: join(home(), "nope.txt") });
  await assert.rejects(m.c.callTool("email_list_recent", {}), (e) => e.code === "NOT_CONFIGURED" && /secret file/.test(e.message));
});

test("shared mode: neither the token nor the secret can leak through an error", async () => {
  const { c } = setup({}, [[TOKEN, () => json({ error: "invalid_client", error_description: "AADSTS7000215: Invalid client secret provided SUPER-SECRET RT-ORIGINAL" }, 401)]]);
  await assert.rejects(c.callTool("email_list_recent", {}), (e) => { const s = JSON.stringify({ m: e.message, h: e.hint, c: e.code }); assert.ok(!s.includes("SUPER-SECRET") && !s.includes("RT-ORIGINAL"), s); return true; });
});

test("without a shared token file nothing changes: the normal sign-in mode and its own cache apply", () => {
  const cfg = resolveConfig({ M365_HOME: ISOLATED_HOME, M365_CLIENT_ID: "c" });
  assert.equal(cfg.refreshTokenFile, ""); assert.equal(cfg.scopeMode, "requested"); assert.equal(cfg.refreshTokenWriteback, true);
  assert.equal(resolveConfig({ M365_HOME: ISOLATED_HOME, M365_PLUGIN_REFRESH_TOKEN_FILE: "a", M365_REFRESH_TOKEN_FILE: "b" }).refreshTokenFile, "a", "plugin setting wins");
});
