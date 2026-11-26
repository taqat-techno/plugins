// 0.7.0 tests: per-address Gmail signatures on REST drafts, and the HTML snapshot of a draft. Fake Google only.
import test from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, readFileSync, readdirSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { TOKEN, ctxFor, json } from "./_helpers.mjs";
import { parseMime, bodyViews, bodySources } from "../server/mime.mjs";
import { putSignature, sanitizeHtml, SIG_START } from "../server/signature.mjs";
import { fetchSignatureImages, ipv6Words, isPrivateAddress, pinnedGet, publicOnlyLookup, signatureImageUrls } from "../server/sigimages.mjs";

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

// ------------------------------------------------------------------------------------------------ 0.7.1 signature images


const PNG = Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]);
const img = (bytes = PNG, type = "image/png", status = 200) => ({ status, type, bytes });
/** A callback-style resolver (like dns.lookup) with a fixed table; unknown hosts get a public address. */
const dnsTable = (table = {}) => (host, opts, cb) => { const r = table[host] ?? [{ address: "93.184.216.34", family: 4 }]; cb(null, r); };

test("snapshot embeds only the From address's real signature images; draft-only URLs and quoted images are never fetched", async () => {
  const dir = mkdtempSync(join(tmpdir(), "gp-sigimg-"));
  const LOGO = "https://cdn.shop.example/logo.png?v=1&amp;s=2";
  const sendAs = { sendAs: [{ sendAsEmail: "info@shop.example", verificationStatus: "accepted", signature: `<div>Shop<img src="${LOGO}"></div>` }] };
  const html = `<p>Hi</p><img src="https://track.example/q.gif"><br><!--gp-signature-start--><div class="gmail_signature"><div>Shop<img src="${LOGO}"><img src="https://evil.example/forged.png"></div></div><!--gp-signature-end-->`;
  const raw = Buffer.from(["From: Shop <info@shop.example>", "To: a@b.example", "Subject: s", "Content-Type: text/html; charset=UTF-8", "", html].join("\r\n")).toString("base64url");
  const fetched = [];
  const c = ctxFor([tokenOk, rest([
    ["GET gmail:drafts/d1", () => json({ id: "d1", message: { raw } })],
    ["GET gmail:settings/sendAs", () => json(sendAs)],
  ])], { seed: SEED, extraEnv: { GOOGLE_REST_FALLBACK: "1", GOOGLE_DOWNLOAD_DIR: dir }, deps: { lookup: dnsTable(), imageGet: async (url) => { fetched.push(url); return img(); } } });
  const r = await c.callTool("gmail_rest_save_draft_html", { draftId: "d1" });
  assert.deepEqual([r.signature_images_inlined, r.signature_images_failed], [1, []]);
  assert.deepEqual(fetched, ["https://cdn.shop.example/logo.png?v=1&s=2"], "only the real signature's image");
  const page = readFileSync(r.path, "utf8");
  assert.match(page, /<img src="data:image\/png;base64,iVBORw0KGgo=">/);
  assert.match(page, /src="https:\/\/evil\.example\/forged\.png"/, "a URL only the draft has stays remote (and blocked by the policy)");
  assert.match(page, /src="https:\/\/track\.example\/q\.gif"/);
  assert.match(page, /default-src 'none'; img-src data:/);
});

test("signature image fetch limits: https, public hosts only, no redirects, image types, size caps; failures are reported, never thrown", async () => {
  const replies = {
    "redir.example": () => img(Buffer.alloc(0), "", 302),
    "html.example": () => img(Buffer.from("<html>"), "text/html"),
    "svg.example": () => img(Buffer.from("<svg/>"), "image/svg+xml"),
    "big.example": () => img(Buffer.alloc(1024 * 1024 + 1)),
  };
  const { images, failed } = await fetchSignatureImages([
    "http://plain.example/a.png", "https://127.0.0.1/a.png", "https://[::1]/a.png", "https://[::ffff:7f00:1]/a.png", "https://int.example/a.png", "https://mixed.example/a.png",
    "https://redir.example/a.png", "https://html.example/a.png", "https://svg.example/a.svg", "https://big.example/a.png", "https://ok.example/a.png",
    "https://user:pw@cred.example/a.png",
  ], {
    lookup: dnsTable({ "int.example": [{ address: "10.0.0.5", family: 4 }], "mixed.example": [{ address: "93.184.216.34", family: 4 }, { address: "::ffff:7f00:1", family: 6 }] }),
    get: async (url) => (replies[new URL(url).hostname] ?? (() => img()))(),
  });
  assert.deepEqual([...images.keys()], ["https://ok.example/a.png"]);
  assert.deepEqual(failed.map((f) => f.reason), [
    "not https", "host is not a public address", "host is not a public address", "host is not a public address", "host is not a public address", "host is not a public address",
    "redirects are not followed", "not an allowed image type (text/html)", "not an allowed image type (image/svg+xml)", "over the 1 MB limit", "credentials in URL",
  ]);

  const many = Array.from({ length: 4 }, (_, i) => `https://h${i}.example/x.png`);
  const total = await fetchSignatureImages(many, { lookup: dnsTable(), get: async () => img(Buffer.alloc(900 * 1024)) });
  assert.equal(total.images.size, 3, "the 3 MB total stops the fourth");
  assert.match(total.failed[0].reason, /total/);
});

test("the connection's own lookup refuses private answers (DNS rebinding cannot pass the check)", async () => {
  // First answer public, every later one private: the early check passes, the connection's lookup must refuse.
  let n = 0;
  const flipping = (host, opts, cb) => { n++; cb(null, n === 1 ? [{ address: "93.184.216.34", family: 4 }] : [{ address: "127.0.0.1", family: 4 }]); };
  const guarded = publicOnlyLookup(flipping);
  await new Promise((done) => guarded("x.example", { all: true }, (err) => { assert.equal(err, null); done(); }));
  await new Promise((done) => guarded("x.example", {}, (err) => { assert.equal(err?.code, "EPRIVATEHOST"); done(); }));
  // The real https path with that lookup never connects to the private answer.
  await assert.rejects(pinnedGet("https://x.example/logo.png", { cap: 1000, lookup: publicOnlyLookup((h, o, cb) => cb(null, [{ address: "127.0.0.1", family: 4 }])) }), { code: "EPRIVATEHOST" });
});

test("signature image helpers: only public IPv4 and global-unicast IPv6 pass, in any notation; URL extraction", () => {
  const priv = ["10.1.2.3", "172.16.0.1", "192.168.1.1", "127.0.0.1", "169.254.169.254", "100.64.0.1", "0.0.0.0", "224.0.0.1",
    "::", "::1", "fd00::1", "fe80::1", "fec0::1", "ff02::1", "::ffff:127.0.0.1", "::ffff:7f00:1", "0:0:0:0:0:ffff:7f00:1", "::127.0.0.1",
    "64:ff9b::a00:1", "2002:7f00:1::1", "2001:0:4136:e378::1", "2001:db8::1", "not-an-ip", "1::2::3"];
  for (const ip of priv) assert.ok(isPrivateAddress(ip), ip);
  for (const ip of ["93.184.216.34", "8.8.8.8", "2606:4700:4700::1111", "2a00:1450:4001:80b::200e"]) assert.ok(!isPrivateAddress(ip), ip);
  assert.deepEqual(ipv6Words("::ffff:127.0.0.1"), [0, 0, 0, 0, 0, 0xffff, 0x7f00, 1]);
  assert.deepEqual(signatureImageUrls(`<img src="https://a.example/1.png"><img src='http://b.example/2.png'><IMG alt=x SRC="https://a.example/1.png">`), ["https://a.example/1.png"]);
});
