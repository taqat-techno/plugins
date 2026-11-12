// 0.11.0: OneDrive and SharePoint files - browse folders and libraries; upload, create folder, move/rename, delete and
// share in the user's OWN OneDrive. Run: node --test tests/
import test from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { ctxFor, call, json, TOK } from "./_helpers.mjs";
import { activeTools } from "../server/tools/index.mjs";
import { resolveConfig } from "../server/config.mjs";

const calls = (c, method, re) => c.fetch.calls.filter((x) => x.method === method && re.test(x.url));
const ITEM = (over = {}) => ({ id: "f1", name: "report.pdf", size: 10, webUrl: "https://x.example/report.pdf", parentReference: { driveId: "d-me", path: "/drive/root:/Docs" }, file: {}, ...over });
const ctx = (routes = [], env = {}) => ctxFor([TOK, ...routes], { M365_ATTACH_SCOPE: "anywhere", ...env });

test("list a folder: own OneDrive by path, any library by drive_id; paths cannot escape", async () => {
  const c = ctx([[/^GET .*\/children\?/, () => json({ value: [ITEM(), ITEM({ id: "d2", name: "Old", folder: { childCount: 3 }, file: undefined })] })]]);
  const r = await call(c, "onedrive_list_folder", { folder_path: "Documents/Reports 2026" });
  assert.match(calls(c, "GET", /children/)[0].url, /\/me\/drive\/root:\/Documents\/Reports%202026:\/children\?/);
  assert.deepEqual(r.items.map((i) => [i.name, i.is_folder]), [["report.pdf", false], ["Old", true]]);
  assert.equal(r.items[1].child_count, 3);
  await call(c, "onedrive_list_folder", {});
  assert.match(calls(c, "GET", /children/)[1].url, /\/me\/drive\/root\/children\?/);
  await call(c, "onedrive_list_folder", { drive_id: "b!lib", item_id: "x1" });
  assert.match(calls(c, "GET", /children/)[2].url, /\/drives\/b!lib\/items\/x1\/children\?/);
  for (const bad of ["../secret", "a/../b", "a:b", "a/b?x", "a#b"]) await assert.rejects(call(c, "onedrive_list_folder", { folder_path: bad }), (e) => e.code === "INVALID_ARGUMENT", bad);
  await assert.rejects(call(c, "onedrive_list_folder", { folder_path: "a", drive_id: "b" }), (e) => e.code === "INVALID_ARGUMENT");
});

test("SharePoint: sites and libraries live in the separate 'sites' module, off by default", async () => {
  const names = (env) => activeTools(resolveConfig({ M365_HOME: "x", M365_CLIENT_ID: "c", ...env })).map((t) => t.name);
  assert.ok(!names({}).includes("sharepoint_list_sites"));
  assert.ok(names({ M365_MODULES: "files,sites" }).includes("sharepoint_list_libraries"));
  assert.ok(!resolveConfig({ M365_HOME: "x", M365_CLIENT_ID: "c" }).scopes.includes("Sites.Read.All"), "default sign-in never asks for it");
  const c = ctx([[/^GET .*\/sites\?search=/, () => json({ value: [{ id: "s1", displayName: "HR", webUrl: "https://x.example/sites/hr" }] })],
    [/^GET .*\/me\/followedSites/, () => json({ value: [{ id: "s2", displayName: "Eng" }] })],
    [/^GET .*\/sites\/s1\/drives/, () => json({ value: [{ id: "b!docs", name: "Documents" }] })]], { M365_MODULES: "files,sites" });
  assert.equal((await call(c, "sharepoint_list_sites", { query: "HR policies" })).sites[0].site_id, "s1");
  assert.match(calls(c, "GET", /\/sites\?search=/)[0].url, /search=HR%20policies/);
  assert.equal((await call(c, "sharepoint_list_sites", {})).source, "followed");
  assert.deepEqual((await call(c, "sharepoint_list_libraries", { site_id: "s1" })).libraries[0], { drive_id: "b!docs", name: "Documents", web_url: null, description: null });
});

test("upload: same file rules as email; never overwrites; into an existing folder of your own OneDrive", async () => {
  const d = mkdtempSync(join(tmpdir(), "m365-v11-")); const f = join(d, "plan.pdf"); writeFileSync(f, "%PDF-plan");
  writeFileSync(join(d, ".env"), "KEY=1");
  const c = ctx([[/^GET .*\/me\/drive\/root:\/Projects:\?/, () => json({ id: "fold1", name: "Projects", folder: {} })],
    [/^GET .*\/me\/drive\/root:\/Notes\.txt:\?/, () => json({ id: "n1", name: "Notes.txt", file: {} })],
    [/^PUT .*\/me\/drive\/root:\/Projects\/plan\.pdf:\/content\?@microsoft\.graph\.conflictBehavior=rename$/, () => json({ id: "u1", name: "plan 1.pdf", webUrl: "https://x.example/p", parentReference: { driveId: "d-me" } }, 201)]]);
  const r = await call(c, "onedrive_upload", { path: f, folder_path: "Projects" });
  assert.equal(r.uploaded, true); assert.equal(r.renamed, true); assert.equal(r.name, "plan 1.pdf"); assert.equal(r.shared, false);
  assert.equal(calls(c, "PUT", /content/)[0].body, "%PDF-plan");
  await assert.rejects(call(c, "onedrive_upload", { path: join(d, ".env"), folder_path: "Projects" }), (e) => e.code === "PATH_NOT_ALLOWED");
  await assert.rejects(call(c, "onedrive_upload", { chat_image: 1 }), (e) => e.code === "CHAT_IMAGE_UNAVAILABLE");
  await assert.rejects(call(c, "onedrive_upload", { path: f, folder_path: "Notes.txt" }), (e) => e.code === "INVALID_ARGUMENT" && /not a folder/.test(e.message));
  await assert.rejects(call(c, "onedrive_upload", { path: f, folder_path: "Projects", name: "a/b.pdf" }), (e) => e.code === "INVALID_ARGUMENT");
  const bot = ctx([], { M365_ATTACH_SCOPE: "folders" });
  await assert.rejects(call(bot, "onedrive_upload", { path: f }), (e) => e.code === "ATTACH_NOT_CONFIGURED");
  assert.equal(calls(c, "PUT", /content/).length, 1);
});

test("create a folder: refuses a taken name instead of renaming", async () => {
  const c = ctx([[/^POST .*\/me\/drive\/root:\/Projects:\/children$/, () => json({ id: "nf", name: "2026", parentReference: { driveId: "d-me" } }, 201)],
    [/^POST .*\/me\/drive\/root\/children$/, () => json({ error: { code: "nameAlreadyExists" } }, 409)]]);
  const r = await call(c, "onedrive_create_folder", { folder_path: "Projects", name: "2026" });
  assert.equal(r.folder_path, "Projects/2026");
  assert.equal(calls(c, "POST", /children$/)[0].json["@microsoft.graph.conflictBehavior"], "fail");
  await assert.rejects(call(c, "onedrive_create_folder", { name: "Projects" }), (e) => e.code === "GRAPH_ERROR" && /409/.test(e.message));
  await assert.rejects(call(c, "onedrive_create_folder", { name: "bad:name" }), (e) => e.code === "INVALID_ARGUMENT");
});

test("move / rename in your own OneDrive; the top level and system folders are refused", async () => {
  const c = ctx([[/^GET .*\/me\/drive\/items\/f1\?/, () => json(ITEM())], [/^GET .*\/me\/drive\/items\/root1\?/, () => json(ITEM({ id: "root1", root: {} }))],
    [/^GET .*\/me\/drive\/items\/docs\?/, () => json(ITEM({ id: "docs", specialFolder: { name: "documents" }, folder: {} }))],
    [/^GET .*\/me\/drive\/root:\/Archive:\?/, () => json({ id: "arch", folder: {} })],
    [/^PATCH .*\/me\/drive\/items\/f1\?@microsoft\.graph\.conflictBehavior=fail$/, ({ body }) => json({ ...ITEM(), name: JSON.parse(body).name ?? "report.pdf", parentReference: { path: "/drive/root:/Archive" } })]]);
  const r = await call(c, "onedrive_move", { item_id: "f1", new_name: "report-final.pdf", to_folder_path: "Archive" });
  assert.deepEqual(calls(c, "PATCH", /items\/f1/)[0].json, { name: "report-final.pdf", parentReference: { id: "arch" } });
  assert.deepEqual(r.was, { name: "report.pdf", folder: "/Docs" }); assert.deepEqual(r.now, { name: "report-final.pdf", folder: "/Archive" });
  for (const id of ["root1", "docs"]) await assert.rejects(call(c, "onedrive_move", { item_id: id, new_name: "x" }), (e) => e.code === "INVALID_ARGUMENT" && /system folders/.test(e.message));
  await assert.rejects(call(c, "onedrive_move", { item_id: "f1" }), (e) => e.code === "INVALID_ARGUMENT");
});

test("delete goes to the recycle bin and reports what went", async () => {
  const c = ctx([[/^GET .*\/me\/drive\/items\/fold\?/, () => json(ITEM({ id: "fold", name: "Old stuff", folder: { childCount: 12 }, file: undefined }))],
    [/^GET .*\/me\/drive\/items\/root1\?/, () => json(ITEM({ id: "root1", root: {} }))],
    [/^DELETE .*\/me\/drive\/items\/fold$/, () => new Response(null, { status: 204 })]]);
  const r = await call(c, "onedrive_delete", { item_id: "fold" });
  assert.deepEqual([r.deleted, r.to, r.name, r.is_folder, r.items_inside], [true, "OneDrive recycle bin", "Old stuff", true, 12]);
  await assert.rejects(call(c, "onedrive_delete", { item_id: "root1" }), (e) => e.code === "INVALID_ARGUMENT");
  assert.equal(calls(c, "DELETE", /items/).length, 1);
});

test("a retention hold is reported as a policy, never as a missing permission", async () => {
  const c = ctx([[/^GET .*\/me\/drive\/items\/fold\?/, () => json(ITEM({ id: "fold", name: "Project", folder: { childCount: 2 }, file: undefined }))],
    [/^DELETE .*\/me\/drive\/items\/fold$/, () => json({ error: { code: "accessDenied", message: "Request was cancelled by event received. If attempting to delete a non-empty folder, it's possible that it's on hold" } }, 403)]]);
  await assert.rejects(call(c, "onedrive_delete", { item_id: "fold" }), (e) => e.code === "BLOCKED_BY_POLICY" && /delete what is inside it first/.test(e.hint) && !/permission Files/.test(e.message));
});

test("share with named people: sign-in required, no invitation unless asked, outsiders flagged", async () => {
  const c = ctx([[/^GET .*\/me\/drive\/items\/f1\?/, () => json(ITEM())], [/^GET .*\/me\?\$select=mail/, () => json({ mail: "me@contoso.example" })],
    [/^POST .*\/me\/drive\/items\/f1\/invite$/, () => json({ value: [{ id: "p1" }, { id: "p2" }] })]]);
  const r = await call(c, "onedrive_share_with", { item_id: "f1", emails: ["Sara@Contoso.example", "guest@partner.example"], role: "edit" });
  const inv = calls(c, "POST", /invite$/)[0].json;
  assert.deepEqual(inv, { recipients: [{ email: "sara@contoso.example" }, { email: "guest@partner.example" }], requireSignIn: true, sendInvitation: false, roles: ["write"] }, "edit access is Graph's write role");
  assert.deepEqual(r.outside_your_domain, ["guest@partner.example"]); assert.equal(r.invitation_email_sent, false); assert.equal(r.granted, 2);
  await call(c, "onedrive_share_with", { item_id: "f1", emails: ["sara@contoso.example"], notify: true, message: "For review" });
  const inv2 = calls(c, "POST", /invite$/)[1].json;
  assert.equal(inv2.sendInvitation, true); assert.equal(inv2.message, "For review"); assert.deepEqual(inv2.roles, ["read"]);
  for (const bad of [{ emails: [] }, { emails: ["Sara"] }, { emails: ["a@b.example"], role: "owner" }]) {
    await assert.rejects(call(c, "onedrive_share_with", { item_id: "f1", ...bad }), (e) => e.code === "INVALID_ARGUMENT", JSON.stringify(bad));
  }
});

test("writes are confined to the user's own OneDrive and missing permissions are named", async () => {
  const { ALL_TOOLS } = await import("../server/tools/index.mjs");
  for (const t of ALL_TOOLS.filter((x) => /^onedrive_(upload|create_folder|move|delete|share_with)$/.test(x.name))) {
    assert.ok(!("drive_id" in (t.inputSchema.properties ?? {})), `${t.name} must not take a drive_id`);
  }
  const c = ctx([[/^GET .*\/me\/drive\/items\/f1\?/, () => json(ITEM())], [/^DELETE .*\/me\/drive\/items\/f1$/, () => json({ error: { code: "accessDenied" } }, 403)]]);
  await assert.rejects(call(c, "onedrive_delete", { item_id: "f1" }), (e) => e.code === "ACCESS_NEEDED" && /Files\.ReadWrite/.test(e.message));
  const s = ctx([[/^GET .*\/sites\?/, () => json({ error: { code: "accessDenied" } }, 403)]], { M365_MODULES: "files,sites" });
  await assert.rejects(call(s, "sharepoint_list_sites", { query: "hr" }), (e) => e.code === "ACCESS_NEEDED" && /Sites\.Read\.All/.test(e.message));
});
