// 0.7.0: attach any file (attach_scope "anywhere", secrets refused) and images pasted into the chat (saved by the hook
// under <home>/chat-files). Run: node --test tests/
import test from "node:test";
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { mkdirSync, mkdtempSync, symlinkSync, writeFileSync } from "node:fs";
import { homedir, tmpdir } from "node:os";
import { join } from "node:path";
import { ctxFor, call, json, TOK } from "./_helpers.mjs";
import { resolveConfig } from "../server/config.mjs";
import { saveSettings } from "../server/setup.mjs";

const dir = (p = "m365-v07-") => mkdtempSync(join(tmpdir(), p));

function attachCtx(extraEnv = {}) {
  const state = { atts: [] };
  const draft = () => ({ id: "d1", isDraft: true, subject: "S", toRecipients: [{ emailAddress: { address: "m@x.example" } }], ccRecipients: [], bccRecipients: [], body: { contentType: "text", content: "hi" }, hasAttachments: state.atts.length > 0 });
  const c = ctxFor([TOK,
    [/^POST .*\/me\/messages\/d1\/attachments$/, ({ body }) => { const b = JSON.parse(body); state.atts.push({ id: "a" + (state.atts.length + 1), name: b.name }); return json({ id: "a" + state.atts.length }, 201); }],
    [/^GET .*\/me\/messages\/d1\/attachments/, () => json({ value: state.atts })],
    [/^GET .*\/me\/messages\/d1\?/, () => json(draft())],
  ], extraEnv);
  c.state = state;
  return c;
}

test("anywhere: any ordinary local file can be attached, no folder setting needed", async () => {
  const d = dir();
  writeFileSync(join(d, "report.pdf"), "%PDF-1.7 fine");
  const c = attachCtx({ M365_ATTACH_SCOPE: "anywhere" });
  const r = await call(c, "email_add_attachment", { draft_id: "d1", path: join(d, "report.pdf") });
  assert.equal(r.attached, true); assert.equal(r.name, "report.pdf");
});

test("anywhere: keys, tokens, sign-in folders and the plugin's own files are never attached", async () => {
  const d = dir();
  const c = attachCtx({ M365_ATTACH_SCOPE: "anywhere", M365_REFRESH_TOKEN_FILE: join(d, "bot-rt.txt") });
  const bad = [];
  for (const name of [".env", ".env.local", "id_rsa", "id_ed25519.pub", "server.pem", "cert.pfx", "vault.kdbx", "credentials.json", "bot-rt.txt"]) {
    writeFileSync(join(d, name), "x"); bad.push(join(d, name));
  }
  mkdirSync(join(d, ".ssh")); writeFileSync(join(d, ".ssh", "config"), "x"); bad.push(join(d, ".ssh", "config"));
  mkdirSync(join(d, ".openclaw", "credentials"), { recursive: true }); writeFileSync(join(d, ".openclaw", "credentials", "t.txt"), "x"); bad.push(join(d, ".openclaw", "credentials", "t.txt"));
  writeFileSync(join(c.home, "settings.json.bak"), "x"); bad.push(join(c.home, "settings.json.bak"));
  bad.push(join(homedir(), ".ssh", "id_rsa"), join(homedir(), ".aws", "credentials"));
  for (const p of bad) await assert.rejects(call(c, "email_add_attachment", { draft_id: "d1", path: p }), (e) => e.code === "PATH_NOT_ALLOWED", p);
  if (process.platform === "win32") {
    for (const p of ["\\\\evil\\share\\x.pdf", "C:x.pdf", join(d, "a.txt:stream")]) await assert.rejects(call(c, "email_add_attachment", { draft_id: "d1", path: p }), (e) => ["PATH_NOT_ALLOWED", "INVALID_ARGUMENT"].includes(e.code), p);
  }
  assert.equal(c.state.atts.length, 0);
});

test("folders (the default, and what a bot gets): outside files still refused; pasted chat images allowed", async () => {
  const c = attachCtx();
  assert.equal(c.ctx.cfg.attachScope, "folders");
  const d = dir(); writeFileSync(join(d, "x.txt"), "hello");
  await assert.rejects(call(c, "email_add_attachment", { draft_id: "d1", path: join(d, "x.txt") }), (e) => e.code === "ATTACH_NOT_CONFIGURED" && /attach-scope anywhere/.test(e.hint));
  const chat = join(c.home, "chat-files", "sess1"); mkdirSync(chat, { recursive: true });
  const png = Buffer.from("89504e470d0a1a0a0000000d49484452", "hex");
  const good = join(chat, `pasted-${sha16(png)}.png`);
  writeFileSync(good, png);
  const r = await call(c, "email_add_attachment", { draft_id: "d1", path: good, name: "screenshot-1.png" });
  assert.equal(r.attached, true); assert.equal(r.name, "screenshot-1.png");
});

const sha16 = (b) => createHash("sha256").update(b).digest("hex").slice(0, 16);

test("0.7.1: chat-files accepts only files exactly as the hook writes them, in both modes", async () => {
  for (const scope of [undefined, "anywhere"]) {
    const c = attachCtx(scope ? { M365_ATTACH_SCOPE: scope } : {});
    const chat = join(c.home, "chat-files", "s"); mkdirSync(chat, { recursive: true });
    const png = Buffer.from("89504e470d0a1a0a00000000", "hex");
    const planted = [
      ["notes.txt", Buffer.from("secret data")],                       // not the hook's name
      ["pasted-0123456789abcdef.png", png],                            // name is not its own hash
      [`pasted-${sha16(Buffer.from("hello"))}.png`, Buffer.from("hello")], // hash fits but it is no image
    ];
    for (const [n, b] of planted) {
      writeFileSync(join(chat, n), b);
      await assert.rejects(call(c, "email_add_attachment", { draft_id: "d1", path: join(chat, n) }), (e) => ["PATH_NOT_ALLOWED", "ATTACH_NOT_CONFIGURED"].includes(e.code), `${scope} ${n}`);
    }
    assert.equal(c.state.atts.length, 0);
  }
});

test("0.7.1: more secret files are refused, and ~/.claude only at the home root", async () => {
  const d = dir();
  const c = attachCtx({ M365_ATTACH_SCOPE: "anywhere" });
  for (const n of [".credentials.json", ".git-credentials", ".netrc", "_netrc", ".npmrc", ".pypirc", "msal_token_cache.json", "msal_token_cache.bin"]) {
    writeFileSync(join(d, n), "x");
    await assert.rejects(call(c, "email_add_attachment", { draft_id: "d1", path: join(d, n) }), (e) => e.code === "PATH_NOT_ALLOWED", n);
  }
  await assert.rejects(call(c, "email_add_attachment", { draft_id: "d1", path: join(homedir(), ".claude", "settings.json") }), (e) => e.code === "PATH_NOT_ALLOWED");
  mkdirSync(join(d, "proj", ".claude", "docs"), { recursive: true });
  writeFileSync(join(d, "proj", ".claude", "docs", "report.md"), "# ok");
  const r = await call(c, "email_add_attachment", { draft_id: "d1", path: join(d, "proj", ".claude", "docs", "report.md") });
  assert.equal(r.attached, true);
});

test("0.7.2: the server never reshapes a path: spaces and hidden characters are refused, not trimmed", async () => {
  const d = dir(); const f = join(d, "report.pdf"); writeFileSync(f, "%PDF-1.7");
  const c = attachCtx({ M365_ATTACH_SCOPE: "anywhere" });
  for (const p of [` ${f}`, `${f} `, `${f}\n`, `‮${f}`, f.replace("report", "rep​ort")]) {
    await assert.rejects(call(c, "email_add_attachment", { draft_id: "d1", path: p }), (e) => e.code === "INVALID_ARGUMENT", JSON.stringify(p));
  }
  assert.equal(c.state.atts.length, 0);
});

test("0.7.2: OS credential and browser-profile folders are refused in any profile, not only the current home", async () => {
  const d = dir();
  for (const sub of [["AppData", "Roaming", "Microsoft", "Protect"], ["AppData", "Local", "Google", "Chrome", "User Data", "Default"]]) {
    const folder = join(d, "OtherUser", ...sub); mkdirSync(folder, { recursive: true }); writeFileSync(join(folder, "blob.txt"), "x");
    const c = attachCtx({ M365_ATTACH_SCOPE: "anywhere" });
    await assert.rejects(call(c, "email_add_attachment", { draft_id: "d1", path: join(folder, "blob.txt") }), (e) => e.code === "PATH_NOT_ALLOWED", folder);
  }
});

test("0.7.1: a link into a secret folder is judged by where it points", { skip: false }, async (t) => {
  const d = dir();
  const sshLike = join(d, ".ssh"); mkdirSync(sshLike); writeFileSync(join(sshLike, "config"), "x");
  try { symlinkSync(sshLike, join(d, "innocent"), "junction"); } catch { t.skip("cannot create a link here"); return; }
  const c = attachCtx({ M365_ATTACH_SCOPE: "anywhere" });
  await assert.rejects(call(c, "email_add_attachment", { draft_id: "d1", path: join(d, "innocent", "config") }), (e) => e.code === "PATH_NOT_ALLOWED");
});

test("chat_image without the hook's saved path explains instead of failing obscurely", async () => {
  const c = attachCtx({ M365_ATTACH_SCOPE: "anywhere" });
  await assert.rejects(call(c, "email_add_attachment", { draft_id: "d1", chat_image: 1 }), (e) => e.code === "CHAT_IMAGE_UNAVAILABLE");
  await assert.rejects(call(c, "email_add_attachment", { draft_id: "d1" }), (e) => e.code === "INVALID_ARGUMENT");
});

test("attach_scope is the person's choice: saved from the terminal, refused from the tool", async () => {
  const h = dir();
  assert.deepEqual(saveSettings(resolveConfig({ M365_HOME: h }), { attach_scope: "Anywhere" }, { viaTool: false }).saved, ["attach_scope"]);
  assert.equal(resolveConfig({ M365_HOME: h }).attachScope, "anywhere");
  assert.throws(() => saveSettings(resolveConfig({ M365_HOME: h }), { attach_scope: "everything" }, { viaTool: false }), (e) => e.code === "INVALID_ARGUMENT");
  const c = attachCtx();
  await assert.rejects(call(c, "m365_setup_save", { attach_scope: "anywhere" }), (e) => e.code === "CREDENTIAL_SETTING_NOT_ALLOWED");
});

test("0.13.4: the email preview shows each attachment's source file; a custom name cannot change the file type", async () => {
  const d = dir(); writeFileSync(join(d, "budget.xlsx"), "xlsx-bytes"); writeFileSync(join(d, "notes.txt"), "hello");
  const c = attachCtx({ M365_ATTACH_SCOPE: "anywhere" });
  await assert.rejects(call(c, "email_add_attachment", { draft_id: "d1", path: join(d, "budget.xlsx"), name: "agenda.pdf" }),
    (e) => e.code === "INVALID_ARGUMENT" && /keep the file's type \(\.xlsx\)/.test(e.message));
  assert.equal(c.state.atts.length, 0, "nothing attached");
  await call(c, "email_add_attachment", { draft_id: "d1", path: join(d, "budget.xlsx"), name: "Q3 numbers.XLSX" });
  await call(c, "email_add_attachment", { draft_id: "d1", path: join(d, "notes.txt") });
  c.state.atts.push({ id: "zz", name: "from-outlook.pdf" });
  const p = await call(c, "email_preview_draft", { draft_id: "d1" });
  const by = Object.fromEntries(p.attachments.map((x) => [x.name, x]));
  assert.match(by["Q3 numbers.XLSX"].from, /budget\.xlsx$/); assert.equal(by["Q3 numbers.XLSX"].real_file_name, "budget.xlsx");
  assert.match(by["notes.txt"].from, /notes\.txt$/); assert.equal(by["notes.txt"].real_file_name, undefined);
  assert.match(by["from-outlook.pdf"].from, /not added by this plugin/);
});
