// Setup from /m365:init: saved settings, validation, the admin request, and a live reload. Run: node --test tests/
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync, writeFileSync, existsSync, statSync } from "node:fs";
import { join } from "node:path";
import { createContext } from "../server/context.mjs";
import { resolveConfig } from "../server/config.mjs";
import { fakeFetch, home } from "./_helpers.mjs";

const mk = (extraEnv = {}) => {
  const h = home();
  const c = createContext({ M365_HOME: h, ...extraEnv }, { fetch: fakeFetch([]), sleep: async () => {} });
  return { c, h };
};
const CID = "a2dc313a-9774-4ecf-abae-8865db08a99a", TID = "2cba7780-c301-4e7d-a494-f0aea716e04b";

test("a fresh install is not configured, and the status points at /m365:init", async () => {
  const { c } = mk();
  const s = await c.callTool("m365_auth_status", {});
  assert.equal(s.configured, false); assert.match(s.hint, /m365:init/); assert.deepEqual(s.saved_setup, []);
});

test("m365_setup_save stores ids, applies them at once without a restart, and writes a user-private file with no secret in it", async () => {
  const { c, h } = mk();
  const r = await c.callTool("m365_setup_save", { client_id: CID.toUpperCase(), tenant: TID, scope_mode: "APP" });
  assert.deepEqual(r.saved.sort(), ["client_id", "scope_mode", "tenant"]);
  assert.equal(c.ctx.cfg.clientId, CID.toUpperCase()); assert.equal(c.ctx.cfg.scopeMode, "app"); assert.deepEqual(c.ctx.cfg.scopes, [".default"]);
  const saved = JSON.parse(readFileSync(join(h, "settings.json"), "utf8"));
  assert.deepEqual(Object.keys(saved).sort(), ["client_id", "scope_mode", "tenant"]); assert.equal(saved.scope_mode, "app");
  const s = await c.callTool("m365_auth_status", {});
  assert.equal(s.configured, true); assert.equal(s.permissions, "app"); assert.deepEqual(s.saved_setup.sort(), ["client_id", "scope_mode", "tenant"]);
  if (process.platform !== "win32") assert.equal(statSync(join(h, "settings.json")).mode & 0o077, 0, "not readable by others");
  // a new process reads the same file
  assert.equal(resolveConfig({ M365_HOME: h }).clientId, CID.toUpperCase());
});

test("priority: plugin settings and environment variables beat the saved file; an empty value clears a saved field", async () => {
  const { c, h } = mk();
  await c.callTool("m365_setup_save", { client_id: CID, auth_mode: "device-code" });
  assert.equal(resolveConfig({ M365_HOME: h, M365_CLIENT_ID: "11111111-1111-1111-1111-111111111111" }).clientId, "11111111-1111-1111-1111-111111111111");
  assert.equal(resolveConfig({ M365_HOME: h, M365_PLUGIN_CLIENT_ID: "${user_config.x}" }).clientId, CID, "an unexpanded placeholder counts as unset");
  assert.equal(c.ctx.cfg.authMode, "device-code");
  await c.callTool("m365_setup_save", { auth_mode: "" });
  assert.equal(c.ctx.cfg.authMode, "auto"); assert.equal(JSON.parse(readFileSync(join(h, "settings.json"), "utf8")).client_id, CID);
});

test("m365_setup_save refuses bad input and saves nothing", async () => {
  const { c, h } = mk();
  for (const bad of [{ client_id: "not-a-guid" }, { tenant: "bad tenant!" }, { scope_mode: "everything" }, { auth_mode: "magic" }, {}]) {
    await assert.rejects(c.callTool("m365_setup_save", bad), (e) => e.code === "INVALID_ARGUMENT", JSON.stringify(bad));
  }
  assert.ok(!existsSync(join(h, "settings.json")), "nothing was written");
  assert.deepEqual(Object.keys(c.ctx.cfg).includes("readOnly") && c.ctx.cfg.readOnly, false);
});

test("it cannot change read-only mode or the modules: those are not settings it can write", async () => {
  const { c, h } = mk();
  await c.callTool("m365_setup_save", { client_id: CID, read_only: false, modules: "mail,channels" });
  const saved = JSON.parse(readFileSync(join(h, "settings.json"), "utf8"));
  assert.deepEqual(Object.keys(saved), ["client_id"]);
  writeFileSync(join(h, "settings.json"), JSON.stringify({ client_id: CID, read_only: "false", modules: "channels" }));
  const cfg = resolveConfig({ M365_HOME: h, M365_READONLY: "true" });
  assert.equal(cfg.readOnly, true); assert.ok(!cfg.modules.includes("channels"));
});

test("the tool can never point the plugin at a credential file; only the person can (command line or plugin settings)", async () => {
  const { c, h } = mk();
  const rt = join(h, "rt.txt"), sec = join(h, "secret.txt");
  writeFileSync(rt, "0.AAAA-fake-refresh-token_1234567890\n"); writeFileSync(sec, "fake~secret.value-12345\n");
  for (const bad of [{ refresh_token_file: rt }, { client_secret_file: sec }, { client_id: CID, refresh_token_file: rt }]) {
    await assert.rejects(c.callTool("m365_setup_save", bad), (e) => e.code === "CREDENTIAL_SETTING_NOT_ALLOWED" && /cli\.mjs setup/.test(e.hint), JSON.stringify(bad));
  }
  assert.ok(!existsSync(join(h, "settings.json")), "a refused call saves nothing, not even the harmless part");
  assert.equal(c.ctx.cfg.refreshTokenFile, "");
  const props = (await import("../server/tools/index.mjs")).ALL_TOOLS.find((x) => x.name === "m365_setup_save").description;
  assert.match(props, /never point the plugin at a token or secret file/);
});

test("the person's own command (viaTool: false) can set credential files; files are shape-checked and never shown", async () => {
  const { saveSettings } = await import("../server/setup.mjs");
  const { c, h } = mk();
  const rt = join(h, "rt.txt"), sec = join(h, "secret.txt"), key = join(h, "id_rsa"), doc = join(h, "notes.txt");
  writeFileSync(rt, "0.AAAA-fake-refresh-token_1234567890\n"); writeFileSync(sec, "fake~secret.value-12345\n");
  writeFileSync(key, "-----BEGIN OPENSSH PRIVATE KEY-----\nabc\n-----END OPENSSH PRIVATE KEY-----\n"); writeFileSync(doc, "meeting notes with spaces in one line here");
  const r = saveSettings(c.ctx.cfg, { client_id: CID, tenant: TID, refresh_token_file: rt, client_secret_file: sec }, { viaTool: false });
  assert.ok(!JSON.stringify(r).includes("fake-refresh") && !JSON.stringify(r).includes("fake~secret"));
  const cfg = resolveConfig({ M365_HOME: h });
  assert.equal(cfg.refreshTokenFile, rt); assert.equal(cfg.clientSecretFile, sec); assert.equal(cfg.scopeMode, "app", "a shared token always means the app's permissions");
  for (const bad of [{ refresh_token_file: key }, { refresh_token_file: doc }, { client_secret_file: join(h, "missing.txt") }, { refresh_token_file: "relative/path.txt" }, { refresh_token_file: h }]) {
    assert.throws(() => saveSettings(cfg, bad, { viaTool: false }), (e) => e.code === "INVALID_ARGUMENT" && !/BEGIN|notes with/.test(e.message), JSON.stringify(bad));
  }
  assert.equal(resolveConfig({ M365_HOME: h }).refreshTokenFile, rt, "a refused save changes nothing");
});

test("a running agent picks up a setup the person made in their terminal, without a restart", async () => {
  const { saveSettings } = await import("../server/setup.mjs");
  const { c, h } = mk();
  assert.equal((await c.callTool("m365_auth_status", {})).configured, false);
  await new Promise((r) => setTimeout(r, 20));
  saveSettings(c.ctx.cfg, { client_id: CID, tenant: TID }, { viaTool: false });
  const s = await c.callTool("m365_auth_status", {});
  assert.equal(s.configured, true); assert.equal(s.tenant, TID); assert.deepEqual(s.saved_setup.sort(), ["client_id", "tenant"]);
  void h;
});

test("first setup only: once an app is configured, the tool cannot swap it for another (a redirect of the sign-in)", async () => {
  const { c } = mk();
  await c.callTool("m365_setup_save", { client_id: CID, tenant: TID });
  const attacker = "99999999-9999-9999-9999-999999999999";
  await assert.rejects(c.callTool("m365_setup_save", { client_id: attacker }), (e) => e.code === "ALREADY_CONFIGURED" && /cli\.mjs setup|plugin settings/.test(e.hint));
  await assert.rejects(c.callTool("m365_setup_save", { tenant: "evil.example.com" }), (e) => e.code === "ALREADY_CONFIGURED");
  assert.equal(c.ctx.cfg.clientId, CID);
  assert.equal((await c.callTool("m365_setup_save", { client_id: CID, scope_mode: "app" })).saved.length, 2, "re-saving the same app and a harmless mode change is fine");
  const fromEnv = mk({ M365_CLIENT_ID: CID }).c;
  await assert.rejects(fromEnv.callTool("m365_setup_save", { client_id: attacker }), (e) => e.code === "ALREADY_CONFIGURED", "an app set by environment or plugin settings is locked too");
});

test("the admin request is a ready-to-send message built from the enabled modules, with each permission explained", async () => {
  const { c } = mk({ M365_MODULES: "mail,channels" });
  const r = await c.callTool("m365_access_request", { note: "I need it for daily client emails." });
  for (const must of ["Subject:", "http://localhost", "Allow public client flows", "Mail.Send", "Mail.Read", "ChannelMessage.Read.All: read team channel messages (admin consent required)", "Grant admin consent", "client) ID", "daily client emails"]) assert.ok(r.message.includes(must), must);
  assert.ok(!r.message.includes("Calendars.Read"), "only the enabled modules are requested");
  assert.deepEqual(r.permissions.admin_consent.sort(), ["Channel.ReadBasic.All", "ChannelMessage.Read.All", "Team.ReadBasic.All"]);
  assert.equal(r.client_id_known, false);
  const ro = createContext({ M365_HOME: home(), M365_MODULES: "mail", M365_READONLY: "true" }, { fetch: fakeFetch([]) });
  const rr = await ro.callTool("m365_access_request", {});
  assert.deepEqual(rr.permissions.write, []); assert.ok(!rr.message.includes("Mail.Send") && /Read-only/.test(rr.message));
});

test("with a client id already known, the request asks for that app to be approved instead of a new registration", async () => {
  const { c } = mk({ M365_CLIENT_ID: CID });
  const r = await c.callTool("m365_access_request", {});
  assert.equal(r.client_id_known, true); assert.ok(r.message.includes(CID) && /already an app/.test(r.message));
});

test("setup tools are local (allowed in read-only mode) and setup_save is the only confirm-gated local tool", async () => {
  const { ALL_TOOLS } = await import("../server/tools/index.mjs");
  const t = (n) => ALL_TOOLS.find((x) => x.name === n);
  assert.equal(t("m365_setup_save").kind, "local"); assert.equal(t("m365_setup_save").confirm, true);
  assert.equal(t("m365_access_request").kind, "local"); assert.ok(!t("m365_access_request").confirm);
  assert.deepEqual(ALL_TOOLS.filter((x) => x.kind === "local" && x.confirm).map((x) => x.name), ["m365_setup_save"]);
  const ro = mk({ M365_READONLY: "true" }).c.listTools().map((x) => x.name);
  assert.ok(ro.includes("m365_setup_save") && ro.includes("m365_access_request"));
});
