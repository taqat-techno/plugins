// A fixed sign-in redirect (M365_REDIRECT_URI) for apps that allow one exact address, such as a bot's confidential app
// registered with http://localhost:8400/callback. Run: node --test tests/
import test from "node:test";
import assert from "node:assert/strict";
import { createServer } from "node:http";
import { readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { home, env, json, fakeFetch, TOKEN } from "./_helpers.mjs";
import { createAuth, classifyTokenError } from "../server/auth.mjs";
import { parseRedirectUri, resolveConfig } from "../server/config.mjs";
import { saveSettings } from "../server/setup.mjs";

const real = globalThis.fetch;
const freePort = () => new Promise((ok) => { const s = createServer(); s.listen(0, "127.0.0.1", () => { const p = s.address().port; s.close(() => ok(p)); }); });
const waitWhile = async (a) => { for (let i = 0; i < 150 && a.status().sign_in?.state === "waiting"; i++) await new Promise((x) => setTimeout(x, 20)); };

test("redirect: only http on localhost/127.0.0.1 with a fixed port >= 1024 is accepted", () => {
  assert.deepEqual(parseRedirectUri(" http://localhost:8400/callback "), { uri: "http://localhost:8400/callback", host: "localhost", port: 8400, path: "/callback" });
  assert.equal(parseRedirectUri("http://127.0.0.1:9000").path, "/");
  for (const bad of ["https://localhost:8400/callback", "http://evil.example:8400/callback", "http://localhost/callback", "http://localhost:80/x",
    "http://localhost:8400/callback?x=1", "http://localhost:8400/cb#f", "http://u:p@localhost:8400/", "localhost:8400", ""]) {
    assert.throws(() => parseRedirectUri(bad), (e) => e.code === "INVALID_ARGUMENT", bad);
  }
});

test("redirect: with M365_REDIRECT_URI the browser flow uses exactly that address, path checked, secret sent", async () => {
  const h = home();
  const port = await freePort();
  const uri = `http://localhost:${port}/callback`;
  const secretFile = join(h, "secret.txt"); writeFileSync(secretFile, "s3cr3t-value\n");
  let exchange;
  const f = fakeFetch([[TOKEN, ({ body }) => { exchange = new URLSearchParams(body); return json({ access_token: "at", refresh_token: "rt-fixed", expires_in: 3600 }); }]]);
  let authorize;
  const open = (url) => { authorize = new URL(url); return true; };
  const a = createAuth(resolveConfig(env(h, { M365_REDIRECT_URI: uri, M365_CLIENT_SECRET_FILE: secretFile })), { fetch: f, open });
  const r = await a.startSignIn({});            // auto: still the browser flow
  assert.equal(r.mode, "interactive");
  assert.equal(authorize.searchParams.get("redirect_uri"), uri, "exactly the registered address");
  assert.equal(a.status().redirect_uri, uri);
  const state = authorize.searchParams.get("state");
  // a request to another path on that port is not the sign-in answer
  const wrong = await real(`http://127.0.0.1:${port}/?code=x&state=${state}`);
  assert.equal(wrong.status, 404); assert.equal(a.status().sign_in.state, "waiting");
  const ok = await real(`http://127.0.0.1:${port}/callback?code=the-code&state=${state}`);
  assert.equal(ok.status, 200);
  await waitWhile(a);
  assert.equal(a.status().sign_in.state, "done");
  assert.equal(exchange.get("redirect_uri"), uri, "the token request repeats the same address");
  assert.equal(exchange.get("client_secret"), "s3cr3t-value", "a confidential app's secret is sent");
  assert.equal(exchange.get("code"), "the-code");
  assert.equal(JSON.parse(readFileSync(join(h, "token-cache.json"), "utf8")).refresh_token, "rt-fixed");
});

test("redirect: a busy port is REDIRECT_PORT_BUSY and auto mode does not fall back to a device code", async () => {
  const h = home();
  const holder = createServer();
  await new Promise((ok) => holder.listen(0, "127.0.0.1", ok));
  const port = holder.address().port;
  const f = fakeFetch([]);
  const a = createAuth(resolveConfig(env(h, { M365_REDIRECT_URI: `http://localhost:${port}/callback` })), { fetch: f, open: () => true });
  try {
    await assert.rejects(a.startSignIn({}), (e) => e.code === "REDIRECT_PORT_BUSY" && /in use/.test(e.message));
    assert.equal(f.calls.filter((c) => c.url.includes("devicecode")).length, 0, "no misleading device-code attempt");
    assert.equal(a.status().sign_in, undefined, "nothing left pending");
  } finally { holder.close(); }
});

test("redirect: an invalid setting is refused at sign-in, and an error sent to the redirect is classified", async () => {
  const h = home();
  const bad = createAuth(resolveConfig(env(h, { M365_REDIRECT_URI: "https://example.com/cb" })), { fetch: fakeFetch([]), open: () => true });
  await assert.rejects(bad.startSignIn({ mode: "interactive" }), (e) => e.code === "INVALID_ARGUMENT" && /M365_REDIRECT_URI/.test(e.hint));

  const port = await freePort();
  let authorize;
  const a = createAuth(resolveConfig(env(home(), { M365_REDIRECT_URI: `http://localhost:${port}/callback` })), { fetch: fakeFetch([]), open: (u) => { authorize = new URL(u); return true; } });
  await a.startSignIn({});
  const q = new URLSearchParams({ error: "invalid_request", error_description: "AADSTS65001: The user or administrator has not consented", state: authorize.searchParams.get("state") });
  await real(`http://127.0.0.1:${port}/callback?${q}`);
  await waitWhile(a);
  assert.equal(a.status().sign_in.state, "failed");
  assert.equal(a.status().sign_in.error.code, "CONSENT_NEEDED");
});

test("hints: AADSTS7000218 points a confidential app to the browser flow with its registered redirect; 50011 to the setting", () => {
  const e = classifyTokenError({ error: "invalid_client", error_description: "AADSTS7000218: The request body must contain client_assertion or client_secret." }, 401);
  assert.equal(e.code, "PUBLIC_CLIENT_NOT_ENABLED");
  assert.match(e.hint, /Allow public client flows/); assert.match(e.hint, /m365_access_request/); assert.match(e.hint, /M365_REDIRECT_URI/);
  assert.match(e.hint, /Do not ask the user for a token or secret/);
  const m = classifyTokenError({ error: "invalid_request", error_description: "AADSTS50011: The redirect URI does not match" }, 400);
  assert.equal(m.code, "REDIRECT_URI_MISMATCH"); assert.match(m.hint, /M365_REDIRECT_URI/);
});

test("setup: redirect_uri is saved after validation and read back with the lowest priority", () => {
  const h = home();
  const cfg = resolveConfig({ M365_HOME: h });
  assert.deepEqual(saveSettings(cfg, { redirect_uri: "http://localhost:8400/callback" }, { viaTool: false }).saved, ["redirect_uri"]);
  assert.equal(resolveConfig({ M365_HOME: h }).redirectUri, "http://localhost:8400/callback");
  assert.equal(resolveConfig({ M365_HOME: h, M365_REDIRECT_URI: "http://localhost:9001/x" }).redirectUri, "http://localhost:9001/x", "env wins");
  assert.throws(() => saveSettings(cfg, { redirect_uri: "https://evil.example/cb" }, { viaTool: true }), (e) => e.code === "INVALID_ARGUMENT");
  assert.equal(resolveConfig({ M365_HOME: h }).redirectUri, "http://localhost:8400/callback", "the bad value was not saved");
});
