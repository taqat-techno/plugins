// 0.10.0 tests: GOOGLE_CLI_COMMAND in every CLI hint (and the old text when unset), drive_rest_search_files and
// drive_rest_download_file (media and export, size caps, names, refusals). Fake Google only.
import test from "node:test";
import assert from "node:assert/strict";
import { existsSync, mkdtempSync, readFileSync, readdirSync } from "node:fs";
import { tmpdir } from "node:os";
import { basename, dirname, join } from "node:path";
import { realpathSync } from "node:fs";
import { TOKEN, FULL_GRANT, ctxFor, json } from "./_helpers.mjs";
import { CLASSES } from "../server/tools/bridge.mjs";

const tokenOk = [TOKEN, () => json({ access_token: "at-live", expires_in: 3599 })];
const MCP = /^POST https:\/\/(gmail|calendar|drive)mcp\.googleapis\.com\/mcp\/v1$/;
const DRIVE = /^GET https:\/\/www\.googleapis\.com\/drive\/v3\//;
const SEED = { account: { email: "me@mail.example" }, scopes_granted: FULL_GRANT };
const ON = { GOOGLE_REST_FALLBACK: "1" };
const CMD = "google-nino";
const dl = () => mkdtempSync(join(tmpdir(), "gp-dl-"));
const FORM = { resultType: "input_required", requestState: "s", inputRequests: { approval_choice: { method: "elicitation/create", params: { mode: "form", message: "Allow?", requestedSchema: { type: "object", properties: { approval_choice: { type: "string", enum: ["ALLOW_ONCE"] } } } } } } };
const mcp = (fn) => [MCP, async ({ body }) => { const rpc = JSON.parse(body); const r = await fn(rpc.params); return r instanceof Response ? r : json({ jsonrpc: "2.0", id: rpc.id, result: r }); }];

/** A Drive REST fake: routes keyed by path-regex over the URL after /drive/v3/; handler gets the URL. */
function drive(routes, seen = []) {
  return [DRIVE, async ({ url }) => {
    const u = new URL(url);
    const path = u.pathname.replace(/^\/drive\/v3\//, "");
    seen.push({ path, query: Object.fromEntries(u.searchParams) });
    for (const [re, h] of routes) if (new RegExp(`^${re}$`).test(path) && (!h.when || h.when(u))) return (h.fn ?? h)(u);
    return json({ error: { code: 404, message: `no fake for ${path}` } }, 404);
  }];
}
const bytes = (b, headers = {}) => new Response(b, { status: 200, headers });

// ------------------------------------------------------------------------------------------------ GOOGLE_CLI_COMMAND

test("GOOGLE_CLI_COMMAND names the CLI in every hint: sign-in (auth), status (MCP 401), grant (confirmation), SCOPE_MISSING (REST and settings tools)", async () => {
  const env = { ...ON, GOOGLE_CLI_COMMAND: CMD };
  const notSigned = ctxFor([tokenOk], { seed: false, extraEnv: env });
  await assert.rejects(notSigned.callTool("gmail_search_threads", {}), (e) => e.code === "AUTH_REQUIRED" && e.hint.includes(`${CMD} sign-in`) && !e.hint.includes("cli.mjs"));
  const st = await notSigned.callTool("google_auth_status", {});
  assert.match(st.hint, new RegExp(`${CMD} sign-in`));

  const expired = ctxFor([tokenOk, [MCP, () => json({}, 401)]], { seed: SEED, extraEnv: env });
  await assert.rejects(expired.callTool("gmail_search_threads", {}), (e) => e.code === "AUTH_EXPIRED" && e.hint.includes(`\`${CMD} status\``));

  const dead = ctxFor([[TOKEN, () => json({ error: "invalid_grant" }, 400)]], { seed: SEED, extraEnv: env });
  await assert.rejects(dead.callTool("gmail_search_threads", {}), (e) => e.code === "AUTH_EXPIRED" && e.hint.includes(`${CMD} sign-in`));

  const asks = ctxFor([tokenOk, mcp(() => FORM)], { seed: SEED, extraEnv: env });
  await assert.rejects(asks.callTool("gmail_get_thread", { threadId: "t1" }), (e) => e.code === "CONFIRMATION_NEEDED" && e.hint.includes(`${CMD} grant gmail_get_thread`) && !e.hint.includes("cli.mjs"));
  await assert.rejects(asks.callTool("calendar_delete_event", { eventId: "e1" }), (e) => e.code === "CONFIRMATION_NEEDED" && e.hint.includes(`${CMD} grant calendar_delete_event --target <id>`));

  const scope = ctxFor([tokenOk, drive([["files", () => json({ error: { code: 403, message: "Request had insufficient authentication scopes." } }, 403)]])], { seed: SEED, extraEnv: env });
  await assert.rejects(scope.callTool("drive_rest_search_files", {}), (e) => e.code === "SCOPE_MISSING" && e.hint.includes(`${CMD} sign-in`));

  const settings = ctxFor([tokenOk], { seed: SEED, extraEnv: { ...env, GOOGLE_GMAIL_SETTINGS: "1" } });
  await assert.rejects(settings.callTool("gmail_rest_create_filter", { criteria: { from: "a@b.example" }, action: { addLabelIds: ["X"] } }), (e) => e.code === "SCOPE_MISSING" && e.hint.includes(`${CMD} sign-in`));
});

test("without GOOGLE_CLI_COMMAND the hints keep their old text; a line break in it is flattened", async () => {
  const notSigned = ctxFor([tokenOk], { seed: false });
  await assert.rejects(notSigned.callTool("gmail_search_threads", {}), (e) => e.hint.includes("run: node server/cli.mjs sign-in"));
  const asks = ctxFor([tokenOk, mcp(() => FORM)], { seed: SEED });
  await assert.rejects(asks.callTool("gmail_get_thread", { threadId: "t1" }), (e) => /node ".*cli\.mjs" grant gmail_get_thread/.test(e.hint));
  const expired = ctxFor([tokenOk, [MCP, () => json({}, 401)]], { seed: SEED });
  await assert.rejects(expired.callTool("gmail_search_threads", {}), (e) => e.hint.includes("`node server/cli.mjs status`"));
  const odd = ctxFor([tokenOk, mcp(() => FORM)], { seed: SEED, extraEnv: { GOOGLE_CLI_COMMAND: "g\r\nrm -rf x" } });
  await assert.rejects(odd.callTool("gmail_get_thread", { threadId: "t1" }), (e) => !/[\r\n]/.test(e.hint) && e.hint.includes("g rm -rf x grant"));
});

// ------------------------------------------------------------------------------------------------ registration

test("the two Drive REST tools are read class, exist only with the REST switch, and also in read-only mode", () => {
  for (const n of ["drive_rest_search_files", "drive_rest_download_file"]) {
    assert.ok(CLASSES.read.includes(n) && CLASSES.rest_tools.includes(n) && CLASSES.plugin_tools.includes(n), n);
    assert.ok(!ctxFor([], { seed: SEED }).listTools().some((t) => t.name === n), `${n} off without the switch`);
    assert.ok(ctxFor([], { seed: SEED, extraEnv: ON }).listTools().some((t) => t.name === n), n);
    assert.ok(ctxFor([], { seed: SEED, extraEnv: { ...ON, GOOGLE_READONLY: "1" } }).listTools().some((t) => t.name === n), `${n} in read-only`);
  }
  const d = ctxFor([], { seed: SEED, extraEnv: ON }).listTools().find((t) => t.name === "drive_rest_download_file").description;
  assert.match(d, /does not go through Google's confirmation/);
});

// ------------------------------------------------------------------------------------------------ search

test("drive_rest_search_files: passes q, paging, corpora and the requested fields; maps owners, size and canTrash; results untrusted", async () => {
  const seen = [];
  const c = ctxFor([tokenOk, drive([["files", () => json({ nextPageToken: "p2", files: [
    { id: "f1", name: "Invoice.pdf", mimeType: "application/pdf", owners: [{ emailAddress: "x@other.example", displayName: "X" }], modifiedTime: "2026-11-01T00:00:00Z", size: "1234", capabilities: { canTrash: false }, webViewLink: "https://drive.example/f1" },
    { id: "f2", name: "Doc", mimeType: "application/vnd.google-apps.document" },
  ] })]], seen)], { seed: SEED, extraEnv: ON });
  const r = await c.callTool("drive_rest_search_files", { q: "name contains 'invoice'", pageSize: 500, pageToken: "p1", corpora: "allDrives", orderBy: "modifiedTime desc" });
  assert.equal(r.untrusted, true);
  assert.equal(r.nextPageToken, "p2");
  assert.deepEqual(r.files[0], { id: "f1", name: "Invoice.pdf", mimeType: "application/pdf", owners: [{ email: "x@other.example", name: "X" }], modifiedTime: "2026-11-01T00:00:00Z", size: 1234, can_trash: false, webViewLink: "https://drive.example/f1" });
  assert.equal(r.files[1].size, null);
  const q = seen[0].query;
  assert.equal(q.q, "name contains 'invoice'");
  assert.equal(q.pageSize, "100", "capped at 100");
  assert.equal(q.pageToken, "p1");
  assert.equal(q.corpora, "allDrives");
  assert.equal(q.includeItemsFromAllDrives, "true", "on by default for allDrives");
  assert.equal(q.supportsAllDrives, "true");
  assert.equal(q.orderBy, "modifiedTime desc");
  for (const f of ["id", "name", "mimeType", "owners(emailAddress,displayName)", "modifiedTime", "size", "capabilities/canTrash", "webViewLink", "nextPageToken"]) assert.ok(q.fields.includes(f), f);

  await c.callTool("drive_rest_search_files", {});
  assert.equal(seen[1].query.q, undefined);
  assert.equal(seen[1].query.pageSize, "25");
  assert.equal(seen[1].query.includeItemsFromAllDrives, "false");
  await assert.rejects(c.callTool("drive_rest_search_files", { corpora: "drive" }), { code: "INVALID_ARGUMENT" });
  await assert.rejects(c.callTool("drive_rest_search_files", { corpora: "everything" }), { code: "INVALID_ARGUMENT" });
  assert.equal(seen.length, 2, "refused before any call");
});

// ------------------------------------------------------------------------------------------------ download

test("drive_rest_download_file: a binary file is fetched with alt=media and saved as is; nothing but the path comes back", async () => {
  const dir = dl(), seen = [];
  const BIN = Buffer.from([0, 1, 2, 250, 255, 10, 13]);
  const c = ctxFor([tokenOk, drive([
    ["files/ext1", { when: (u) => u.searchParams.get("alt") === "media", fn: () => bytes(BIN, { "content-type": "application/pdf" }) }],
    ["files/ext1", () => json({ id: "ext1", name: "Contract.pdf", mimeType: "application/pdf", size: String(BIN.length) })],
  ], seen)], { seed: SEED, extraEnv: { ...ON, GOOGLE_DOWNLOAD_DIR: dir } });
  const r = await c.callTool("drive_rest_download_file", { fileId: "ext1" });
  assert.deepEqual(readFileSync(r.saved.path), BIN);
  assert.equal(dirname(r.saved.path), realpathSync(dir));
  assert.deepEqual({ ...r.saved, path: undefined }, { path: undefined, filename: "Contract.pdf", mimeType: "application/pdf", size: BIN.length });
  assert.equal(r.untrusted, true);
  assert.equal(r.exported, false);
  assert.equal(seen[1].query.supportsAllDrives, "true");
  assert.equal(seen[0].query.supportsAllDrives, "true");
  const again = await c.callTool("drive_rest_download_file", { fileId: "ext1" });
  assert.equal(basename(again.saved.path), "Contract (2).pdf", "never overwrites");
  await assert.rejects(c.callTool("drive_rest_download_file", { fileId: "ext1", mimeType: "text/plain" }), { code: "INVALID_ARGUMENT" });
});

test("drive_rest_download_file: Google-native files are exported (PDF by default, PNG for drawings, or the given mimeType) with the extension added", async () => {
  const dir = dl(), seen = [];
  const META = { doc: "document", sheet: "spreadsheet", draw: "drawing" };
  const c = ctxFor([tokenOk, drive([
    ["files/(doc|sheet|draw)/export", (u) => bytes(Buffer.from(`EXPORT ${u.searchParams.get("mimeType")}`))],
    ["files/(doc|sheet|draw)", (u) => { const id = u.pathname.split("/").pop(); return json({ id, name: `My ${id}`, mimeType: `application/vnd.google-apps.${META[id]}` }); }],
  ], seen)], { seed: SEED, extraEnv: { ...ON, GOOGLE_DOWNLOAD_DIR: dir } });
  const d = await c.callTool("drive_rest_download_file", { fileId: "doc" });
  assert.equal(d.saved.filename, "My doc.pdf");
  assert.equal(d.saved.mimeType, "application/pdf");
  assert.equal(d.exported, true);
  assert.equal(readFileSync(d.saved.path, "utf8"), "EXPORT application/pdf");
  assert.equal((await c.callTool("drive_rest_download_file", { fileId: "draw" })).saved.filename, "My draw.png");
  const x = await c.callTool("drive_rest_download_file", { fileId: "sheet", mimeType: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" });
  assert.equal(x.saved.filename, "My sheet.xlsx");
  assert.equal(readFileSync(x.saved.path, "utf8"), "EXPORT application/vnd.openxmlformats-officedocument.spreadsheetml.sheet");
  assert.ok(seen.every((s) => s.query.alt === undefined), "exports never use alt=media");
  await assert.rejects(c.callTool("drive_rest_download_file", { fileId: "doc", mimeType: "text/plain\r\nX: y" }), { code: "INVALID_ARGUMENT" });
});

test("drive_rest_download_file: folders, forms and shortcuts are NOT_DOWNLOADABLE before any download", async () => {
  const seen = [];
  const c = ctxFor([tokenOk, drive([
    ["files/fold", () => json({ id: "fold", name: "F", mimeType: "application/vnd.google-apps.folder" })],
    ["files/form", () => json({ id: "form", name: "F", mimeType: "application/vnd.google-apps.form" })],
    ["files/sc", () => json({ id: "sc", name: "S", mimeType: "application/vnd.google-apps.shortcut", shortcutDetails: { targetId: "real1" } })],
  ], seen)], { seed: SEED, extraEnv: { ...ON, GOOGLE_DOWNLOAD_DIR: dl() } });
  await assert.rejects(c.callTool("drive_rest_download_file", { fileId: "fold" }), { code: "NOT_DOWNLOADABLE" });
  await assert.rejects(c.callTool("drive_rest_download_file", { fileId: "form" }), { code: "NOT_DOWNLOADABLE" });
  await assert.rejects(c.callTool("drive_rest_download_file", { fileId: "sc" }), (e) => e.code === "NOT_DOWNLOADABLE" && /real1/.test(e.message));
  assert.equal(seen.length, 3, "metadata only");
});

test("drive_rest_download_file: size limit from the metadata, from Content-Length, and while reading; nothing is saved", async () => {
  const dir = dl(), seen = [];
  const big = Buffer.alloc(3000, 65);
  const stream = () => new ReadableStream({ start(ctl) { for (let i = 0; i < 3; i++) ctl.enqueue(new Uint8Array(1000).fill(66)); ctl.close(); } });
  const c = ctxFor([tokenOk, drive([
    ["files/meta", { when: (u) => u.searchParams.get("alt") === "media", fn: () => bytes(big) }],
    ["files/meta", () => json({ id: "meta", name: "m.bin", mimeType: "application/octet-stream", size: "3000" })],
    ["files/hdr", { when: (u) => u.searchParams.get("alt") === "media", fn: () => bytes(big, { "content-length": "3000" }) }],
    ["files/hdr", () => json({ id: "hdr", name: "h.bin", mimeType: "application/octet-stream" })],
    ["files/doc/export", () => new Response(stream(), { status: 200 })],
    ["files/doc", () => json({ id: "doc", name: "d", mimeType: "application/vnd.google-apps.document" })],
  ], seen)], { seed: SEED, extraEnv: { ...ON, GOOGLE_DOWNLOAD_DIR: dir, GOOGLE_MAX_SAVE_MB: String(2000 / 1048576) } });
  await assert.rejects(c.callTool("drive_rest_download_file", { fileId: "meta" }), { code: "TOO_LARGE" });
  assert.ok(!seen.some((s) => s.path === "files/meta" && s.query.alt === "media"), "no download when the metadata already says too large");
  await assert.rejects(c.callTool("drive_rest_download_file", { fileId: "hdr" }), { code: "TOO_LARGE" });
  await assert.rejects(c.callTool("drive_rest_download_file", { fileId: "doc" }), { code: "TOO_LARGE" });
  assert.deepEqual(readdirSync(dir), []);
});

test("drive_rest_download_file: a hostile file name is cleaned and stays in the download folder; Google's refusal passes through", async () => {
  const dir = dl();
  const c = ctxFor([tokenOk, drive([
    ["files/evil", { when: (u) => u.searchParams.get("alt") === "media", fn: () => bytes(Buffer.from("x")) }],
    ["files/evil", () => json({ id: "evil", name: "..\\..\\CON:a/b?.txt", mimeType: "text/plain" })],
    ["files/locked", { when: (u) => u.searchParams.get("alt") === "media", fn: () => json({ error: { code: 403, message: "The user has not granted the app access to download this file.", errors: [{ reason: "cannotDownloadFile" }] } }, 403) }],
    ["files/locked", () => json({ id: "locked", name: "l.pdf", mimeType: "application/pdf" })],
  ])], { seed: SEED, extraEnv: { ...ON, GOOGLE_DOWNLOAD_DIR: dir } });
  const r = await c.callTool("drive_rest_download_file", { fileId: "evil" });
  assert.equal(dirname(r.saved.path), realpathSync(dir));
  assert.doesNotMatch(basename(r.saved.path), /[\\/:?]/);
  await assert.rejects(c.callTool("drive_rest_download_file", { fileId: "locked" }), (e) => e.code === "GOOGLE_FORBIDDEN" && /download this file/.test(e.message));
  const noDir = ctxFor([tokenOk, drive([["files/evil", () => json({ id: "evil", name: "a.txt", mimeType: "text/plain" })]])], { seed: SEED, extraEnv: ON });
  await assert.rejects(noDir.callTool("drive_rest_download_file", { fileId: "evil" }), { code: "DOWNLOAD_NOT_CONFIGURED" });
  assert.ok(existsSync(dir));
});

// ------------------------------------------------------------------------------------------------ 0.10.1 extensions

test("withExtension: adds the standard extension when missing or wrong, keeps a fitting one (any case or alias), leaves unknown types alone", async () => {
  const { withExtension } = await import("../server/save.mjs");
  assert.equal(withExtension("عبد الرحمن ايمن ", "image/jpeg"), "عبد الرحمن ايمن.jpg");
  assert.equal(withExtension("photo.JPEG", "image/jpeg"), "photo.JPEG");
  assert.equal(withExtension("photo.jfif", "image/jpeg; name=x"), "photo.jfif");
  assert.equal(withExtension("a.png", "image/jpeg"), "a.png.jpg");
  assert.equal(withExtension("page.htm", "text/html"), "page.htm");
  assert.equal(withExtension("Mr. Smith", "application/pdf"), "Mr. Smith.pdf");
  assert.equal(withExtension("data", "application/octet-stream"), "data");
  assert.equal(withExtension("data", undefined), "data");
  assert.equal(withExtension("x".repeat(400), "image/png").slice(-4), ".png", "length cap keeps the extension");
});

test("drive_rest_download_file: a name without extension (Nino's case) is saved as name.jpg, then name (2).jpg", async () => {
  const dir = dl(), NAME = "عبد الرحمن ايمن ";
  const c = ctxFor([tokenOk, drive([
    ["files/img", { when: (u) => u.searchParams.get("alt") === "media", fn: () => bytes(Buffer.from([0xff, 0xd8, 0xff])) }],
    ["files/img", () => json({ id: "img", name: NAME, mimeType: "image/jpeg", size: "3" })],
  ])], { seed: SEED, extraEnv: { ...ON, GOOGLE_DOWNLOAD_DIR: dir } });
  const a = await c.callTool("drive_rest_download_file", { fileId: "img" });
  const b = await c.callTool("drive_rest_download_file", { fileId: "img" });
  assert.equal(basename(a.saved.path), "عبد الرحمن ايمن.jpg");
  assert.equal(basename(b.saved.path), "عبد الرحمن ايمن (2).jpg");
  assert.equal(a.saved.filename, "عبد الرحمن ايمن.jpg");
});

test("gmail_get_attachment and drive_save_file add the extension too; a fitting one is not doubled", async () => {
  const dir = dl();
  const RAW = ["MIME-Version: 1.0", 'Content-Type: multipart/mixed; boundary="b"', "", "--b", "Content-Type: text/plain", "", "hi",
    "--b", 'Content-Type: image/png; name="scan"', 'Content-Disposition: attachment; filename="scan"', "Content-Transfer-Encoding: base64", "", Buffer.from("PNG").toString("base64"), "--b--", ""].join("\r\n");
  const ok = (data) => ({ content: [{ type: "text", text: JSON.stringify(data) }], structuredContent: data });
  const c = ctxFor([tokenOk, mcp((p) => (p.name === "get_message"
    ? ok({ id: "m1", raw: Buffer.from(RAW).toString("base64url") })
    : ok({ id: p.arguments.fileId, title: p.arguments.fileId === "j" ? "holiday.jpeg" : "holiday", mimeType: "image/jpeg", content: Buffer.from("JPG").toString("base64") })))], { seed: SEED, extraEnv: { GOOGLE_DOWNLOAD_DIR: dir } });
  const att = await c.callTool("gmail_get_attachment", { messageId: "m1", attachment: "1" });
  assert.equal(basename(att.saved.path), "scan.png");
  assert.equal(basename((await c.callTool("drive_save_file", { fileId: "n" })).saved.path), "holiday.jpg");
  assert.equal(basename((await c.callTool("drive_save_file", { fileId: "j" })).saved.path), "holiday.jpeg", "not holiday.jpeg.jpg");
});
