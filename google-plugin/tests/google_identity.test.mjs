// Identity tests (milestone B2): headers decide, never the body; X-Forwarded-For first; Delivered-To never.
// Fixtures are synthetic (example domains). A fake Google MCP server stands in for the network.
import test from "node:test";
import assert from "node:assert/strict";
import { writeFileSync } from "node:fs";
import { join } from "node:path";
import { TOKEN, ctxFor, json, home } from "./_helpers.mjs";
import { headerBlock, loadIdentities, matchIdentity, parseHeaders, decodeHeader } from "../server/identity.mjs";
import { resolveConfig } from "../server/config.mjs";

const tokenOk = [TOKEN, () => json({ access_token: "at-live", expires_in: 3599 })];
const MCP = /^POST https:\/\/gmailmcp\.googleapis\.com\/mcp\/v1$/;
const BODY = "BODY-SECRET-TEXT that must never leave the plugin";
const IDS = { identities: [
  { id: "sales", label: "Sales desk", address: "info@shop.example" },
  { id: "school", label: "School", address: "admin@school.example", matchTo: ["@school.example"] },
  { id: "personal", label: "Personal", address: "owner@mail.example", default: true },
] };

const mime = (headers) => `${headers.join("\r\n")}\r\n\r\n${BODY}\r\n`;
const b64 = (s) => Buffer.from(s, "utf8").toString("base64url");
/** Cloudflare-style forward: the alias is only in X-Forwarded-For (first) and To; Delivered-To is the mailbox. */
const FORWARDED = mime([
  "Delivered-To: owner@mail.example",
  "X-Forwarded-To: owner@mail.example",
  "X-Forwarded-For: info@shop.example owner@mail.example",
  "From: =?UTF-8?B?" + Buffer.from("متجر الأمل", "utf8").toString("base64") + "?= <orders@vendor.example>",
  "To: Info Desk <info@shop.example>",
  "Subject: =?UTF-8?Q?Order_=E2=84=96_42?=",
  "Date: Thu, 26 Nov 2026 08:00:00 +0000",
]);

function google(raw, seen = []) {
  return [MCP, ({ body }) => {
    const rpc = JSON.parse(body);
    seen.push(rpc.params);
    const data = { id: "m1", threadId: "t1", raw };
    return json({ jsonrpc: "2.0", id: rpc.id, result: { content: [{ type: "text", text: JSON.stringify(data) }], structuredContent: data } });
  }];
}
const run = async (raw, idsJson = IDS, extraEnv = {}) => {
  const seen = [];
  const c = ctxFor([tokenOk, google(raw, seen)], { extraEnv: { GOOGLE_IDENTITIES: JSON.stringify(idsJson), ...extraEnv } });
  const r = await c.callTool("gmail_message_identity", { messageId: "m1" });
  return { r, seen, c };
};

test("forwarded mail: X-Forwarded-For decides; headers are decoded; the body never leaves the plugin", async () => {
  for (const raw of [b64(FORWARDED), FORWARDED]) {
    const { r, seen } = await run(raw);
    assert.deepEqual(seen.map((p) => [p.name, p.arguments]), [["get_message", { messageId: "m1", messageFormat: "RAW" }]]);
    assert.deepEqual(r.identity, { id: "sales", label: "Sales desk", address: "info@shop.example" });
    assert.equal(r.matched_by, "x-forwarded-for");
    assert.equal(r.matched_address, "info@shop.example");
    assert.equal(r.untrusted, true);
    assert.equal(r.thread_id, "t1");
    assert.equal(r.headers.subject, "Order № 42");
    assert.equal(r.headers.from, "متجر الأمل <orders@vendor.example>");
    assert.deepEqual(r.headers.x_forwarded_for, ["info@shop.example owner@mail.example"]);
    const out = JSON.stringify(r);
    assert.doesNotMatch(out, /BODY-SECRET/);
    assert.equal(out.includes(raw.slice(0, 40)), false, "the raw message is not returned");
    assert.deepEqual(Object.keys(r.headers).sort(), ["cc", "date", "from", "subject", "to", "x_forwarded_for"]);
  }
});

test("Bcc'd alias: To names someone else, X-Forwarded-For still finds the identity; X-Forwarded-For beats To", async () => {
  const bcc = mime(["X-Forwarded-For: admin@school.example owner@mail.example", "To: parents@other.example", "Subject: hi"]);
  const a = await run(b64(bcc));
  assert.equal(a.r.identity.id, "school");
  assert.equal(a.r.matched_by, "x-forwarded-for");

  const both = mime(["X-Forwarded-For: info@shop.example owner@mail.example", "To: teacher@school.example"]);
  assert.equal((await run(b64(both))).r.identity.id, "sales");
});

test("no X-Forwarded-For: To, then Cc, then the default; @domain rules; Delivered-To is never used", async () => {
  assert.deepEqual([(await run(b64(mime(["To: a@x.example", "Cc: head@school.example"])))).r].map((r) => [r.identity.id, r.matched_by, r.matched_address])[0], ["school", "cc", "head@school.example"]);
  assert.equal((await run(b64(mime(["To: info@SHOP.example"])))).r.identity.id, "sales", "addresses compare case-insensitively");

  const delivered = await run(b64(mime(["Delivered-To: info@shop.example", "To: stranger@x.example"])));
  assert.equal(delivered.r.identity.id, "personal");
  assert.equal(delivered.r.matched_by, "default", "Delivered-To alone never matches");

  const noDefault = await run(b64(mime(["To: stranger@x.example"])), { identities: IDS.identities.filter((x) => !x.default) });
  assert.equal(noDefault.r.identity, null);
  assert.equal(noDefault.r.matched_by, null);

  const none = await run(b64(mime(["To: info@shop.example"])), []);
  assert.equal(none.r.identity, null);
  assert.equal(none.r.identities_configured, 0);
});

test("header parsing: folding, encoded words, a headers-only window; a message without a header end is refused", () => {
  const h = parseHeaders(headerBlock(b64("Subject: one\r\n two\r\nX-Forwarded-For: a@b.example\r\nX-Forwarded-For: c@d.example\r\n\r\nbody")));
  assert.deepEqual(h.subject, ["one two"]);
  assert.deepEqual(h["x-forwarded-for"], ["a@b.example", "c@d.example"]);
  assert.equal(decodeHeader("=?ISO-8859-1?Q?caf=E9?= =?UTF-8?B?w6k=?="), "caféé");
  assert.throws(() => headerBlock(b64("Subject: x".padEnd(300_000, "y"))), { code: "HEADERS_TOO_LARGE" });
  assert.deepEqual(matchIdentity({ "x-forwarded-for": ["Info <INFO@shop.example>"] }, loadIdentities(resolveConfig({ GOOGLE_IDENTITIES: JSON.stringify(IDS) }))).matched_address, "info@shop.example");
});

test("identity configuration: file or environment, checked; problems are CONFIG_INVALID", async () => {
  const h = home();
  const f = join(h, "ids.json");
  writeFileSync(f, "﻿" + JSON.stringify(IDS.identities));
  assert.deepEqual(loadIdentities(resolveConfig({ GOOGLE_IDENTITIES_FILE: f })).map((x) => x.id), ["sales", "school", "personal"]);
  assert.deepEqual(loadIdentities(resolveConfig({})), []);
  const bad = [
    "{not json", JSON.stringify({ x: 1 }), JSON.stringify([{ address: "a@b.example" }]),
    JSON.stringify([{ id: "a", address: "nope" }]), JSON.stringify([{ id: "a", address: "a@b.example" }, { id: "a", address: "c@d.example" }]),
    JSON.stringify([{ id: "a", address: "a@b.example", default: true }, { id: "b", address: "c@d.example", default: true }]),
    JSON.stringify([{ id: "a", address: "a@b.example", matchTo: ["*"] }]), JSON.stringify([{ id: "a", address: "a@b.example", matchTo: [] }]),
  ];
  for (const b of bad) assert.throws(() => loadIdentities(resolveConfig({ GOOGLE_IDENTITIES: b })), { code: "CONFIG_INVALID" }, b);
  assert.throws(() => loadIdentities(resolveConfig({ GOOGLE_IDENTITIES_FILE: join(h, "missing.json") })), { code: "CONFIG_INVALID" });

  const c = ctxFor([tokenOk], { extraEnv: { GOOGLE_IDENTITIES: JSON.stringify(IDS) } });
  const listed = await c.callTool("gmail_identities", {});
  assert.equal(listed.source, "environment");
  assert.deepEqual(listed.identities[1], { id: "school", label: "School", address: "admin@school.example", matchTo: ["@school.example"], default: false });
  assert.equal(c.fetch.calls.length, 0, "gmail_identities contacts nobody");

  const broken = ctxFor([tokenOk, google(b64(FORWARDED))], { extraEnv: { GOOGLE_IDENTITIES: "{bad" } });
  await assert.rejects(broken.callTool("gmail_message_identity", { messageId: "m1" }), { code: "CONFIG_INVALID" });
  assert.equal(broken.fetch.calls.length, 0, "a bad configuration is reported before Google is called");
});

test("confirmation: the identity tool goes through the same never-auto-answer path, and points grant at gmail_get_message", async () => {
  const FORM = { resultType: "input_required", requestState: "s", inputRequests: { approval_choice: { method: "elicitation/create", params: { mode: "form", message: "Allow?", requestedSchema: { type: "object", properties: { approval_choice: { type: "string", enum: ["ALLOW_ONCE", "DENY_ONCE"] } } } } } } };
  const c = ctxFor([tokenOk, [MCP, ({ body }) => json({ jsonrpc: "2.0", id: JSON.parse(body).id, result: FORM })]], { extraEnv: { GOOGLE_IDENTITIES: JSON.stringify(IDS) } });
  await assert.rejects(c.callTool("gmail_message_identity", { messageId: "m1" }), (e) => e.code === "CONFIRMATION_NEEDED" && /grant gmail_get_message \./.test(e.hint));
  await assert.rejects(c.callTool("gmail_message_identity", {}), { code: "INVALID_ARGUMENT" });
});

test("module and read-only filtering apply to the identity tools; the server lists them only with gmail on", async () => {
  const names = (env) => ctxFor([], { extraEnv: env }).tools.map((t) => t.name);
  assert.ok(names({}).includes("gmail_message_identity") && names({}).includes("gmail_identities"));
  assert.ok(names({ GOOGLE_READONLY: "true" }).includes("gmail_message_identity"));
  assert.ok(!names({ GOOGLE_MODULES: "calendar" }).some((n) => n.startsWith("gmail_")));
});
