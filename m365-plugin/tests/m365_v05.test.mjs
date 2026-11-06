// 0.5.0: profile filled from Outlook, categories, local file attachments, HTML drafts with the user's signature.
// Run: node --test tests/
import test from "node:test";
import assert from "node:assert/strict";
import { mkdirSync, mkdtempSync, symlinkSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { ctxFor, call, g, json, TOK } from "./_helpers.mjs";
import { resolveConfig } from "../server/config.mjs";
import { saveSettings } from "../server/setup.mjs";
import { textToHtml, loadSignature } from "../server/signature.mjs";
import { extractLinks } from "../server/tools/mail_write.mjs";

const calls = (c, method, re) => c.fetch.calls.filter((x) => x.method === method && re.test(x.url));
const dir = (p = "m365-v05-") => mkdtempSync(join(tmpdir(), p));

// ---------------------------------------------------------------- profile from Outlook

const ME = g("/me\\?\\$select=id,displayName", { id: "u1", displayName: "Ahmed Test", mail: "Ahmed@Contoso.com", preferredLanguage: "ar-EG" });
const MBX = (over = {}) => g("/me/mailboxSettings", { timeZone: "Egypt Standard Time", language: { locale: "en-US" },
  workingHours: { daysOfWeek: ["sunday", "monday", "tuesday", "wednesday", "thursday"], startTime: "08:30:00.0000000", endTime: "16:30:00.0000000", timeZone: { name: "Egypt Standard Time" } }, ...over });

test("profile: the first tool call after sign-in fills identity, zone and working hours from Outlook", async () => {
  const c = ctxFor([TOK, ME, MBX(), g("mailFolders/inbox/messages", { value: [] })]);
  assert.equal(c.ctx.profile.load().me.email, null);
  await call(c, "email_list_recent", {});
  const p = c.ctx.profile.load();
  assert.deepEqual([p.me.email, p.me.name, p.me.id, p.me.timezone, p.me.language], ["ahmed@contoso.com", "Ahmed Test", "u1", "Africa/Cairo", "en-US"]);
  assert.deepEqual(p.defaults.working_hours, { days: ["sunday", "monday", "tuesday", "wednesday", "thursday"], start: "08:30", end: "16:30" });
  assert.equal(p.sources.timezone, "outlook");
  await call(c, "email_list_recent", {});
  assert.equal(calls(c, "GET", /mailboxSettings/).length, 1, "only once");
});

test("profile: status polls never call Microsoft, and a failed fill never blocks the tool", async () => {
  const c = ctxFor([TOK, [/\/me\?/, () => json({ error: { code: "ServiceUnavailable" } }, 503)], g("mailFolders/inbox/messages", { value: [] })]);
  await call(c, "m365_auth_status", {});
  assert.equal(c.fetch.calls.filter((x) => x.url.includes("graph.microsoft.com")).length, 0);
  assert.equal((await call(c, "email_list_recent", {})).count, 0, "the tool still ran");
});

test("profile: values the user set are never overwritten; a missing permission falls back to the computer's zone", async () => {
  const c = ctxFor([TOK, ME, MBX({ timeZone: "Arab Standard Time" })]);
  c.ctx.profile.set({ timezone: "Europe/London", working_days: ["monday"] });
  const r = await call(c, "profile_refresh_me", {});
  assert.equal(r.me.timezone, "Europe/London"); assert.deepEqual(r.working_hours.days, ["monday"]);
  assert.deepEqual(r.kept_because_user_set.sort(), ["timezone", "working_hours"]);
  assert.equal(r.me.email, "ahmed@contoso.com", "account values are still filled");

  const d = ctxFor([TOK, ME, [/mailboxSettings/, () => json({ error: { code: "ErrorAccessDenied" } }, 403)]]);
  const r2 = await call(d, "profile_refresh_me", {});
  assert.equal(r2.sources.timezone, "computer"); assert.match(r2.notes[0], /could not be read/);
});

test("profile: when Outlook's two zones disagree, the one matching this computer wins and the user is told", async () => {
  const c = ctxFor([TOK, ME, MBX({ timeZone: "Arab Standard Time" })]);
  const r = await call(c, "profile_refresh_me", {});
  assert.ok(["Asia/Riyadh", "Africa/Cairo"].includes(r.me.timezone));
  assert.match(r.notes.join(" "), /Asia\/Riyadh.*Africa\/Cairo/);
});

test("profile: an unknown Windows zone is resolved from Outlook's own list by city name", async () => {
  const c = ctxFor([TOK, ME, MBX({ timeZone: "Some Rare Standard Time", workingHours: null }),
    g("supportedTimeZones", { value: [{ alias: "Some Rare Standard Time", displayName: "(UTC+05:45) Kathmandu" }] })]);
  const r = await call(c, "profile_refresh_me", {});
  assert.equal(r.me.timezone, "Asia/Kathmandu");
});

// ---------------------------------------------------------------- categories

test("categories: set, de-duplicated and cleaned; an empty list clears; the master list is readable", async () => {
  const c = ctxFor([TOK, [/^PATCH .*\/me\/messages\/m1$/, ({ body }) => json({ categories: JSON.parse(body).categories })],
    g("masterCategories", { value: [{ displayName: "Red category", color: "preset0" }] })]);
  const r = await call(c, "email_set_categories", { message_id: "m1", categories: ["Project X", "project x", "Follow‮up"] });
  assert.deepEqual(r.categories, ["Project X", "Followup"]);
  assert.deepEqual((await call(c, "email_set_categories", { message_id: "m1", categories: [] })).categories, []);
  await assert.rejects(call(c, "email_set_categories", { message_id: "m1", categories: "x" }), (e) => e.code === "INVALID_ARGUMENT");
  assert.deepEqual((await call(c, "email_list_categories", {})).categories, [{ name: "Red category", color: "preset0" }]);
});

// ---------------------------------------------------------------- attachments

function attachCtx(extraEnv = {}, extraRoutes = []) {
  const state = { atts: [] };
  const draft = () => ({ id: "d1", isDraft: true, subject: "S", toRecipients: [{ emailAddress: { address: "m@x.com" } }], ccRecipients: [], bccRecipients: [], body: { contentType: "text", content: "See the attached report." }, hasAttachments: state.atts.length > 0 });
  const c = ctxFor([TOK, ...extraRoutes,
    [/^POST .*\/me\/messages\/d1\/attachments\/createUploadSession$/, () => json({ uploadUrl: "https://outlook.office.com/api/v2.0/upload?token=x" })],
    [/^PUT https:\/\/outlook\.office\.com\//, ({ init }) => { if (!/bytes \d+-\d+\/\d+/.test(init.headers["Content-Range"])) return json({}, 400); return new Response(null, { status: 200 }); }],
    [/^POST .*\/me\/messages\/d1\/attachments$/, ({ body }) => { const b = JSON.parse(body); state.atts.push({ id: "a" + (state.atts.length + 1), name: b.name, size: Buffer.from(b.contentBytes, "base64").length, isInline: !!b.isInline }); return json({ id: "a" + state.atts.length }, 201); }],
    [/^DELETE .*\/attachments\/a1$/, () => { state.atts = state.atts.filter((x) => x.id !== "a1"); return new Response(null, { status: 204 }); }],
    [/^GET .*\/me\/messages\/d1\/attachments/, () => json({ value: state.atts })],
    [/^GET .*\/me\/messages\/d1\?/, () => json(draft())],
    [/^POST .*\/me\/messages\/d1\/send$/, () => new Response(null, { status: 202 })],
  ], extraEnv);
  c.state = state;
  return c;
}

test("attachments: refused until the person allows a folder; the tool can never set that folder itself", async () => {
  const c = attachCtx();
  await assert.rejects(call(c, "email_add_attachment", { draft_id: "d1", path: join(dir(), "x.txt") }), (e) => e.code === "ATTACH_NOT_CONFIGURED");
  await assert.rejects(call(c, "m365_setup_save", { attach_dirs: dir() }), (e) => e.code === "CREDENTIAL_SETTING_NOT_ALLOWED");
  await assert.rejects(call(c, "m365_setup_save", { signature_file: join(dir(), "s.html") }), (e) => e.code === "CREDENTIAL_SETTING_NOT_ALLOWED");
  const h = dir(), allowed = dir();
  assert.deepEqual(saveSettings(resolveConfig({ M365_HOME: h }), { attach_dirs: allowed }, { viaTool: false }).saved, ["attach_dirs"]);
  assert.deepEqual(resolveConfig({ M365_HOME: h }).attachDirs, [allowed]);
  assert.throws(() => saveSettings(resolveConfig({ M365_HOME: h }), { attach_dirs: "C:\\" }, { viaTool: false }), (e) => e.code === "INVALID_ARGUMENT");
});

test("attachments: only files inside an allowed folder; '..', other folders and links that point outside are refused", async () => {
  const root = dir("m365-allowed-"), outside = dir("m365-outside-");
  writeFileSync(join(root, "report.pdf"), "%PDF-1.7 fine");
  writeFileSync(join(outside, "secret.txt"), "TOKEN");
  mkdirSync(join(root, "sub"));
  const c = attachCtx({ M365_ATTACH_DIRS: root });
  for (const p of [join(outside, "secret.txt"), join(root, "..", outside.split(/[\\/]/).pop(), "secret.txt"), "relative.txt", root, join(root, "nope.pdf")]) {
    await assert.rejects(call(c, "email_add_attachment", { draft_id: "d1", path: p }), (e) => ["PATH_NOT_ALLOWED", "INVALID_ARGUMENT", "NOT_FOUND"].includes(e.code), p);
  }
  let linked = false;
  try { symlinkSync(outside, join(root, "sub", "escape"), "junction"); linked = true; } catch { /* links not available here */ }
  if (linked) await assert.rejects(call(c, "email_add_attachment", { draft_id: "d1", path: join(root, "sub", "escape", "secret.txt") }), (e) => e.code === "PATH_NOT_ALLOWED", "a link inside the folder pointing outside");
  assert.equal(c.state.atts.length, 0, "nothing was attached");
  const r = await call(c, "email_add_attachment", { draft_id: "d1", path: join(root, "report.pdf") });
  assert.equal(r.attached, true); assert.equal(r.name, "report.pdf");
  assert.equal(calls(c, "POST", /\/attachments$/)[0].json.contentType, "application/pdf");
});

test("attachments: adding or removing a file invalidates the preview; the preview lists files and the digest covers them", async () => {
  const root = dir("m365-allowed-");
  writeFileSync(join(root, "a.txt"), "hello");
  const c = attachCtx({ M365_ATTACH_DIRS: root });
  const p0 = await call(c, "email_preview_draft", { draft_id: "d1" });
  await call(c, "email_add_attachment", { draft_id: "d1", path: join(root, "a.txt") });
  await assert.rejects(call(c, "email_send_draft", { draft_id: "d1", digest: p0.digest }), (e) => e.code === "NOT_PREVIEWED");
  const p1 = await call(c, "email_preview_draft", { draft_id: "d1" });
  assert.deepEqual(p1.attachments, [{ attachment_id: "a1", name: "a.txt", size_bytes: 5 }]); assert.notEqual(p1.digest, p0.digest);
  await call(c, "email_remove_attachment", { draft_id: "d1", attachment_id: "a1" });
  await assert.rejects(call(c, "email_send_draft", { draft_id: "d1", digest: p1.digest }), (e) => e.code === "NOT_PREVIEWED");
  // a file added behind the preview's back (for example in Outlook) is caught at send time
  const p2 = await call(c, "email_preview_draft", { draft_id: "d1" });
  c.state.atts.push({ id: "zz", name: "sneaky.exe", size: 9, isInline: false });
  await assert.rejects(call(c, "email_send_draft", { draft_id: "d1", digest: p2.digest, confirm_no_attachment: true }), (e) => e.code === "DRAFT_CHANGED");
});

test("attachments: a file over 3 MB goes through an upload session in chunks, without the Graph token", async () => {
  const root = dir("m365-allowed-");
  writeFileSync(join(root, "big.zip"), Buffer.alloc(7 * 1024 * 1024, 1));
  const c = attachCtx({ M365_ATTACH_DIRS: root }, [[/^GET .*\/me\/messages\/d1\/attachments\?\$select=id,name,size$/, () => json({ value: [{ id: "big1", name: "big.zip", size: 7 * 1024 * 1024 + 300 }] })]]);
  const r = await call(c, "email_add_attachment", { draft_id: "d1", path: join(root, "big.zip") });
  assert.equal(r.attachment_id, "big1");
  const puts = c.fetch.calls.filter((x) => x.method === "PUT");
  assert.equal(puts.length, 3, "7 MB in 3.2 MB chunks");
  assert.ok(puts.every((x) => !x.headers.Authorization), "the upload URL carries its own authorization");
  assert.match(puts[2].headers["Content-Range"], /^bytes 6553600-7340031\/7340032$/);
});

// ---------------------------------------------------------------- HTML drafts with the user's signature

test("signature: text is escaped (only **bold** becomes <b>), so a model can never inject HTML", () => {
  const h = textToHtml('Hi <a href="https://evil">x</a> & **ship it**\n\nLine1\nLine2 <img src=x onerror=alert(1)>');
  assert.ok(!/<a |<img /i.test(h));
  assert.match(h, /&lt;a href=&quot;https:\/\/evil&quot;&gt;/); assert.match(h, /<b>ship it<\/b>/); assert.match(h, /Line1<br>Line2/);
  assert.ok(!/<(a|img)\b/i.test(h), "no live link or image tag in what the model wrote");
});

test("links: the whole body is scanned, so odd markup cannot hide a link (over-reporting inert text is fine)", () => {
  assert.deepEqual(extractLinks('<a title="a>b" href="https://hidden.example">x</a>'), ["https://hidden.example"]);
  assert.deepEqual(extractLinks("<img alt='1>2' src=https://img.example/x.png>"), ["https://img.example/x.png"]);
  assert.ok(extractLinks('<a x=y"z href="https://stray-quote.example">t</a>').includes("https://stray-quote.example"), "a stray quote in an unquoted value");
  assert.ok(extractLinks('<a x=\'y href="https://single.example">').includes("https://single.example"));
  assert.ok(extractLinks('<div style="background:url(https://css.example/b.png)">').includes("https://css.example/b.png"));
});

test("links: a fake attribute inside another attribute's value cannot swallow the real link", () => {
  const has = (html, url) => assert.ok(extractLinks(html).includes(url), `${url} in ${html}`);
  has('<a title="x href=" href="https://evil.example/1">t</a>', "https://evil.example/1");
  has("<a title='src=' src='https://evil.example/2'>", "https://evil.example/2");
  has('<a data-x="href=\'" href=https://evil.example/3>t</a>', "https://evil.example/3");
  has('<a href="&#104;ttps://evil.example/4">t</a>', "https://evil.example/4");
  has('<a href="&#x6A;avascript:alert(1)">t</a>', "javascript:alert(1)");
  has('<!-- <a href="x"> --><a href="https://evil.example/5">t</a>', "https://evil.example/5");
  has('<img srcset="https://a.example/1x.png 1x, https://a.example/2x.png 2x">', "https://a.example/2x.png");
  has("<p>visit //evil.example/path now</p>", "//evil.example/path");
});

test("links: the tokenizer reads attributes as HTML does", async () => {
  const { tagAttributes } = await import("../server/tools/mail_write.mjs");
  assert.deepEqual(tagAttributes('<a title="x href=" href="https://e/1" disabled data=y>'), [["title", "x href="], ["href", "https://e/1"], ["data", "y"]]);
});

test("attachments: network, device, drive-relative and stream paths are refused before the disk is touched", async () => {
  const root = dir("m365-allowed-");
  const c = attachCtx({ M365_ATTACH_DIRS: root });
  const bad = ["\\\\attacker.example\\share\\x.txt", "//attacker.example/share/x.txt", "\\\\?\\C:\\Windows\\win.ini", "\\\\.\\PhysicalDrive0"];
  if (process.platform === "win32") bad.push(`${root}\\a.txt:secret`, "C:Windows\\win.ini");
  for (const p of bad) await assert.rejects(call(c, "email_add_attachment", { draft_id: "d1", path: p }), (e) => ["PATH_NOT_ALLOWED", "INVALID_ARGUMENT"].includes(e.code), p);
  if (process.platform === "win32") {
    writeFileSync(join(root, "Case.txt"), "x");
    assert.equal((await call(c, "email_add_attachment", { draft_id: "d1", path: join(root.toUpperCase(), "Case.txt") })).attached, true, "folder match ignores case on Windows");
  }
});

test("signature: an unsafe signature file is refused; local images become inline attachments", () => {
  const d = dir();
  writeFileSync(join(d, "bad.html"), '<p onclick="x()">Hi</p>');
  assert.throws(() => loadSignature({ signatureFile: join(d, "bad.html") }), (e) => e.code === "NOT_CONFIGURED");
  writeFileSync(join(d, "logo.png"), Buffer.from([0x89, 0x50, 0x4e, 0x47]));
  writeFileSync(join(d, "sig.html"), '<html><body><p>Ahmed</p><img src="logo.png"><img src="https://cdn.example.com/x.png"><img src="../escape.png"></body></html>');
  const s = loadSignature({ signatureFile: join(d, "sig.html") });
  assert.equal(s.images.length, 1); assert.equal(s.images[0].name, "logo.png");
  assert.match(s.html, /src="cid:sig-[0-9a-f]{12}@m365-plugin"/); assert.match(s.html, /https:\/\/cdn\.example\.com/); assert.match(s.html, /\.\.\/escape\.png/);
  assert.ok(!/<body/i.test(s.html));
});

test("signature: new drafts become HTML with the signature and its image; signature:false keeps plain text", async () => {
  const d = dir();
  writeFileSync(join(d, "logo.png"), Buffer.from([1, 2, 3]));
  writeFileSync(join(d, "sig.html"), '<p>Ahmed | <a href="https://contoso.com">Contoso</a></p><img src="logo.png">');
  const c = ctxFor([TOK, [/^POST .*\/me\/messages$/, () => json({ id: "n1" }, 201)], [/^POST .*\/me\/messages\/n1\/attachments$/, () => json({ id: "img1" }, 201)], g("/messages/n1/attachments\\?", { value: [] })],
    { M365_SIGNATURE_FILE: join(d, "sig.html") });
  await call(c, "email_create_draft", { to: ["m@x.com"], subject: "Hi", body: "Hello **team**" });
  const body = calls(c, "POST", /\/me\/messages$/)[0].json.body;
  assert.equal(body.contentType, "HTML"); assert.match(body.content, /Hello <b>team<\/b>/); assert.match(body.content, /contoso\.com/);
  const img = calls(c, "POST", /\/n1\/attachments$/)[0].json;
  assert.equal(img.isInline, true); assert.match(img.contentId, /^sig-/);
  await call(c, "email_create_draft", { to: ["m@x.com"], subject: "Hi", body: "plain", signature: false });
  assert.equal(calls(c, "POST", /\/me\/messages$/)[1].json.body.contentType, "Text");
});

test("signature: a reply keeps Outlook's quoted original below the new text and signature", async () => {
  const d = dir();
  writeFileSync(join(d, "sig.html"), "<p>-- Ahmed</p>");
  let patched;
  const c = ctxFor([TOK, [/createReply$/, () => json({ id: "r1" }, 201)],
    g("/me/messages/r1\\?\\$select=body", { body: { contentType: "html", content: '<html><head></head><body><div id="divRplyFwdMsg">From: Sara</div></body></html>' } }),
    [/^PATCH .*\/me\/messages\/r1$/, ({ body }) => { patched = JSON.parse(body); return json({}); }]],
    { M365_SIGNATURE_FILE: join(d, "sig.html") });
  await call(c, "email_create_reply_draft", { message_id: "m1", comment: "Thanks <b>" });
  assert.deepEqual(calls(c, "POST", /createReply$/)[0].json, {}, "no comment: the text goes on top of Outlook's body instead");
  const html = patched.body.content;
  assert.ok(html.indexOf("Thanks &lt;b&gt;") < html.indexOf("-- Ahmed") && html.indexOf("-- Ahmed") < html.indexOf("divRplyFwdMsg"));
});
