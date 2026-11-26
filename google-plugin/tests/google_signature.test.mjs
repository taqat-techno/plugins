// 0.7.0 tests: per-address Gmail signatures on REST drafts, and the HTML snapshot of a draft. Fake Google only.
import test from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, readFileSync, readdirSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { TOKEN, ctxFor, json } from "./_helpers.mjs";
import { parseMime, bodyViews, bodySources } from "../server/mime.mjs";
import { putSignature, sanitizeHtml, SIG_START } from "../server/signature.mjs";

const tokenOk = [TOKEN, () => json({ access_token: "at-live", expires_in: 3599 })];
const REST = /^(GET|POST|PUT|PATCH|DELETE) https:\/\/(gmail|www)\.googleapis\.com\//;
const SEED = { account: { email: "me@mail.example" } };
const SIG_SHOP = '<div dir="ltr"><b>Shop team</b><br><a href="https://shop.example">shop.example</a></div>';
const SIG_SCHOOL = "<div>School office</div>";
const SEND_AS = { sendAs: [
  { sendAsEmail: "me@mail.example", isPrimary: true, isDefault: true, signature: "" },
  { sendAsEmail: "info@shop.example", displayName: "Shop", verificationStatus: "accepted", signature: SIG_SHOP },
  { sendAsEmail: "admin@school.example", verificationStatus: "accepted", signature: SIG_SCHOOL },
] };

function rest(routes) {
  return [REST, async ({ url, init, body }) => {
    const path = new URL(url).pathname.replace(/^\/gmail\/v1\/users\/me\//, "gmail:");
    for (const [k, h] of routes) {
      const [m, re] = k.split(" ");
      if (m === (init.method || "GET") && new RegExp(`^${re}$`).test(path)) return h({ body: body ? JSON.parse(body) : undefined });
    }
    return json({ error: { code: 404, message: `no fake for ${init.method} ${path}` } }, 404);
  }];
}
const rawOf = (body) => parseMime(Buffer.from(Buffer.from(body.message.raw, "base64url").toString("utf8")));
const count = (s, sub) => s.split(sub).length - 1;

test("create_draft: the chosen From's own signature goes into the HTML (marked) and the text version; none when the address has none or when switched off", async () => {
  let posted;
  const c = ctxFor([tokenOk, rest([
    ["GET gmail:settings/sendAs", () => json(SEND_AS)],
    ["POST gmail:drafts", ({ body }) => { posted = body; return json({ id: "d1", message: { id: "m1", threadId: "t1" } }); }],
  ])], { seed: SEED, extraEnv: { GOOGLE_REST_FALLBACK: "1" } });

  const r = await c.callTool("gmail_rest_create_draft", { from: "info@shop.example", to: ["smsm@x.example"], subject: "مرحبا", body: "Hello\nSecond line" });
  assert.deepEqual([r.signature_added, r.signature_from, r.from], [true, "info@shop.example", "info@shop.example"]);
  const v = bodyViews(rawOf(posted));
  assert.match(v.text, /^Hello\nSecond line\n\n-- \nShop team\nshop\.example$/);
  const html = bodySources(rawOf(posted)).html;
  assert.equal(count(html, SIG_START), 1);
  assert.match(html, /Hello<br>\nSecond line[\s\S]*<div class="gmail_signature"><div dir="ltr"><b>Shop team<\/b>/);

  const none = await c.callTool("gmail_rest_create_draft", { to: ["a@b.example"], subject: "x", body: "plain" });
  assert.deepEqual([none.signature_added, none.from], [false, "me@mail.example"]);
  assert.equal(bodyViews(rawOf(posted)).htmlParts, 0, "no signature: no HTML part is invented");
  const off = await c.callTool("gmail_rest_create_draft", { from: "info@shop.example", to: ["a@b.example"], body: "x", includeSignature: false });
  assert.equal(off.signature_added, false);
  assert.doesNotMatch(bodyViews(rawOf(posted)).text, /Shop team/);
  await assert.rejects(c.callTool("gmail_rest_create_draft", { from: "stranger@x.example", to: ["a@b.example"], body: "x" }), { code: "IDENTITY_NOT_VERIFIED" });
});

test("reply and forward: signature from the reply's From, placed above the quoted history", async () => {
  let posted;
  const original = ["From: A <a@x.example>", "To: admin@school.example", "Subject: Q", "Date: Mon, 1 Jan 2026 10:00:00 +0000", "Message-ID: <q@x.example>", "Content-Type: text/plain", "", "Original question"].join("\r\n");
  const c = ctxFor([tokenOk, rest([
    ["GET gmail:settings/sendAs", () => json(SEND_AS)],
    ["GET gmail:messages/m1", ({}) => json({ id: "m1", threadId: "t1", raw: Buffer.from(original).toString("base64url"), payload: { headers: [{ name: "From", value: "A <a@x.example>" }, { name: "To", value: "admin@school.example" }, { name: "Subject", value: "Q" }, { name: "Message-ID", value: "<q@x.example>" }] } })],
    ["POST gmail:drafts", ({ body }) => { posted = body; return json({ id: "d2", message: { id: "m2", threadId: "t1" } }); }],
  ])], { seed: SEED, extraEnv: { GOOGLE_REST_FALLBACK: "1" } });

  const rr = await c.callTool("gmail_rest_create_reply_draft", { messageId: "m1", body: "Answer" });
  assert.deepEqual([rr.from, rr.signature_added], ["admin@school.example", true]);
  assert.match(bodyViews(rawOf(posted)).text, /^Answer\n\n-- \nSchool office$/);

  const fw = await c.callTool("gmail_rest_create_forward_draft", { messageId: "m1", to: ["boss@y.example"], body: "FYI" });
  assert.equal(fw.signature_added, true);
  const v = bodyViews(rawOf(posted));
  assert.ok(v.text.indexOf("School office") < v.text.indexOf("---------- Forwarded message"), "signature above the quoted history");
  assert.ok(v.html.indexOf("School office") < v.html.indexOf("Forwarded message") && v.html.includes("Original question"), "the HTML version carries the quote too");
});

test("update_draft: a new body gets the signature once; a From change swaps it in place; no change leaves it alone", async () => {
  let current, putBody;
  const mk = () => ctxFor([tokenOk, rest([
    ["GET gmail:settings/sendAs", () => json(SEND_AS)],
    ["GET gmail:drafts/d1", () => json({ id: "d1", message: { id: "m1", threadId: "t1", raw: current } })],
    ["PUT gmail:drafts/d1", ({ body }) => { putBody = body; current = body.message.raw; return json({ id: "d1", message: { id: "m2", threadId: "t1" } }); }],
    ["POST gmail:drafts", ({ body }) => { current = body.message.raw; return json({ id: "d1", message: { id: "m1", threadId: "t1" } }); }],
  ])], { seed: SEED, extraEnv: { GOOGLE_REST_FALLBACK: "1" } });
  const c = mk();
  await c.callTool("gmail_rest_create_draft", { from: "info@shop.example", to: ["a@b.example"], subject: "s", body: "v1" });

  const u1 = await c.callTool("gmail_rest_update_draft", { draftId: "d1", body: "v2" });
  assert.deepEqual([u1.signature_added, u1.signature_from], [true, "info@shop.example"]);
  let v = bodyViews(rawOf(putBody));
  assert.equal(count(v.text, "Shop team"), 1);
  assert.equal(count(bodySources(rawOf(putBody)).html, SIG_START), 1);
  assert.match(v.text, /^v2\n/);

  const u2 = await c.callTool("gmail_rest_update_draft", { draftId: "d1", from: "admin@school.example" });
  assert.deepEqual([u2.signature_added, u2.signature_from], [true, "admin@school.example"]);
  v = bodyViews(rawOf(putBody));
  assert.equal(count(v.text, "Shop team"), 0, "the old signature is gone from the text");
  assert.equal(count(v.html, "Shop team"), 0, "and from the HTML");
  assert.equal(count(v.text, "School office"), 1);
  assert.match(v.text, /^v2\n/);

  const u3 = await c.callTool("gmail_rest_update_draft", { draftId: "d1", subject: "new subject" });
  assert.equal(u3.signature_added, null, "subject only: the signature is not touched");
  assert.equal(count(bodyViews(rawOf(putBody)).text, "School office"), 1);

  const u4 = await c.callTool("gmail_rest_update_draft", { draftId: "d1", from: "me@mail.example" });
  assert.equal(u4.signature_added, false, "an address without a signature: the old one is removed, nothing added");
  assert.equal(count(bodyViews(rawOf(putBody)).html + bodyViews(rawOf(putBody)).text, "School office"), 0);
});

test("putSignature replaces an existing plugin signature instead of doubling it", () => {
  const a = putSignature({ text: "hi", sig: SIG_SHOP });
  const b = putSignature({ text: a.text, html: a.html, sig: SIG_SHOP, oldSig: SIG_SHOP });
  assert.equal(count(b.html, SIG_START), 1);
  assert.equal(count(b.text, "Shop team"), 1);
  const doc = putSignature({ html: "<html><body><p>x</p></body></html>", sig: SIG_SCHOOL });
  assert.match(doc.html, /<p>x<\/p><br><!--gp-signature-start-->[\s\S]*<\/body><\/html>$/, "inside <body> of a whole document");
});

test("save_draft_html: one safe, self-contained file with the header block, inline images and the send digest", async () => {
  const dir = mkdtempSync(join(tmpdir(), "gp-snap-"));
  const png = Buffer.from([137, 80, 78, 71]);
  const draft = [
    "From: Shop <info@shop.example>", "To: smsm@x.example", "Subject: Offer <script>alert(1)</script>",
    'Content-Type: multipart/related; boundary="r"', "", "--r", "Content-Type: text/html; charset=UTF-8", "",
    '<html><head><style>p{color:red}</style><meta http-equiv="refresh" content="0;url=https://evil.example"></head><body><p onclick="steal()">Hello <img src="cid:logo@x"></p><script>steal()</script><a href="javascript:steal()">x</a><img src="https://track.example/p.gif"></body></html>',
    "--r", "Content-Type: image/png", "Content-ID: <logo@x>", "Content-Transfer-Encoding: base64", "", png.toString("base64"), "--r--", "",
  ].join("\r\n");
  const raw = Buffer.from(draft).toString("base64url");
  const c = ctxFor([tokenOk, rest([
    ["GET gmail:drafts/d9", () => json({ id: "d9", message: { id: "m9", threadId: "t9", raw } })],
    ["GET gmail:settings/sendAs", () => json(SEND_AS)],
  ])], { seed: SEED, extraEnv: { GOOGLE_REST_FALLBACK: "1", GOOGLE_DOWNLOAD_DIR: dir } });
  const pv = await c.callTool("gmail_rest_preview_draft", { draftId: "d9" });
  const r = await c.callTool("gmail_rest_save_draft_html", { draftId: "d9" });
  assert.equal(r.digest, pv.digest, "the same digest as preview and send");
  assert.deepEqual([r.from, r.to, r.subject], ["Shop <info@shop.example>", "smsm@x.example", "Offer <script>alert(1)</script>"]);
  const page = readFileSync(r.path, "utf8");
  assert.match(page, /DRAFT, not sent/);
  assert.match(page, /Content-Security-Policy" content="default-src 'none'; img-src data:/);
  assert.match(page, /Offer &lt;script&gt;alert\(1\)&lt;\/script&gt;/, "header values are escaped");
  assert.match(page, /src="data:image\/png;base64,iVBORw=="/, "cid: image embedded");
  assert.match(page, /p\{color:red\}/, "the draft's styles are kept");
  assert.doesNotMatch(page, /<script|onclick|javascript:|http-equiv="refresh"/i);
  const again = await c.callTool("gmail_rest_save_draft_html", { draftId: "d9" });
  assert.notEqual(again.path, r.path, "never overwrites");
  assert.equal(readdirSync(dir).length, 2);

  // Text-only draft: escaped in <pre>.
  const t = ctxFor([tokenOk, rest([["GET gmail:drafts/d8", () => json({ id: "d8", message: { raw: Buffer.from("From: me@mail.example\r\nSubject: s\r\nContent-Type: text/plain\r\n\r\n<b>not html</b>").toString("base64url") } })]])], { seed: SEED, extraEnv: { GOOGLE_REST_FALLBACK: "1", GOOGLE_DOWNLOAD_DIR: dir } });
  const tp = readFileSync((await t.callTool("gmail_rest_save_draft_html", { draftId: "d8" })).path, "utf8");
  assert.match(tp, /<pre[^>]*>&lt;b&gt;not html&lt;\/b&gt;<\/pre>/);
});

test("sanitizeHtml: event attributes in any quoting, scripts, embeds and javascript: links are removed", () => {
  const s = sanitizeHtml(`<div onmouseover='x()' ONLOAD=y()><iframe src="a"></iframe><object data="b"></object><a href = "javascript:z()">k</a><img src=x onerror=alert(1)></div>`);
  assert.doesNotMatch(s, /on(mouseover|load|error)|iframe|object|javascript:/i);
});
