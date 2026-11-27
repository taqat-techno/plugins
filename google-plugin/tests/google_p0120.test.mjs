// 0.12.0 tests: the opt-in Google Photos module (GOOGLE_PHOTOS=1): scopes, visibility, SCOPE_MISSING, the Picker
// (sessions, list, download with the Bearer header to googleusercontent.com only), upload + batchCreate, and the
// app-created Library tools. Fake Google only.
import test from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, readFileSync, readdirSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { basename, join } from "node:path";
import { TOKEN, FULL_GRANT, ctxFor, json } from "./_helpers.mjs";
import { SCOPES, resolveConfig } from "../server/config.mjs";
import { pickerMediaUrl } from "../server/tools/photos.mjs";
import { CLASSES } from "../server/tools/bridge.mjs";

const tokenOk = [TOKEN, () => json({ access_token: "at-live", expires_in: 3599 })];
const API = /^(GET|POST|PATCH|DELETE) https:\/\/photos(library|picker)\.googleapis\.com\/v1\//;
const MEDIA = /^GET https:\/\/[a-z0-9.-]+\.googleusercontent\.com\//;
const PHOTO_SCOPES = [SCOPES.photosPicker, SCOPES.photosAppend, SCOPES.photosReadApp, SCOPES.photosEditApp];
const SEED = { account: { email: "me@mail.example" }, scopes_granted: [...FULL_GRANT, ...PHOTO_SCOPES] };
const ON = { GOOGLE_PHOTOS: "1" };
const dl = () => mkdtempSync(join(tmpdir(), "gp-ph-"));
const READ = ["photos_picker_start", "photos_picker_status", "photos_picker_list", "photos_picker_download", "photos_picker_end", "photos_list_app_items", "photos_search_app_items", "photos_get_app_item", "photos_list_app_albums"];
const WRITE = ["photos_upload", "photos_update_app_item_description", "photos_create_album", "photos_album_add_items", "photos_album_remove_items", "photos_update_album_title"];

/** Photos fake: routes keyed "METHOD api path-regex" (api = library | picker); records method, api, path, query, headers, body. */
function photos(routes, seen = []) {
  return [API, async ({ url, init, body }) => {
    const u = new URL(url);
    const api = u.hostname.startsWith("photospicker") ? "picker" : "library";
    const path = u.pathname.replace(/^\/v1\//, "");
    const method = init.method || "GET";
    const rec = { method, api, path, query: Object.fromEntries(u.searchParams), headers: init.headers ?? {}, raw: body, body: undefined };
    try { rec.body = body && typeof body === "string" ? JSON.parse(body) : undefined; } catch { /* raw upload */ }
    seen.push(rec);
    for (const [k, h] of routes) {
      const [m, a, re] = k.split(" ");
      if (m === method && a === api && new RegExp(`^${re}$`).test(path)) return h(rec, u);
    }
    return json({ error: { code: 404, message: `no fake for ${method} ${api} ${path}` } }, 404);
  }];
}
const picked = (id, extra = {}) => ({ id, type: "PHOTO", createTime: "2026-11-01T10:00:00Z", mediaFile: { baseUrl: `https://lh3.googleusercontent.com/pp/${id}`, mimeType: "image/jpeg", filename: `IMG_${id}`, mediaFileMetadata: { width: 400, height: 300 } }, ...extra });

// ------------------------------------------------------------------------------------------------ config + visibility

test("GOOGLE_PHOTOS: off by default; adds the four Photos scopes (two in read-only mode); tools only with it, writes not in read-only; no REST switch needed", () => {
  assert.ok(!resolveConfig({}).scopes.some((s) => s.includes("photos")));
  assert.deepEqual(resolveConfig(ON).scopes.filter((s) => s.includes("photos")).sort(), [...PHOTO_SCOPES].sort());
  assert.deepEqual(resolveConfig({ ...ON, GOOGLE_READONLY: "1" }).scopes.filter((s) => s.includes("photos")).sort(), [SCOPES.photosPicker, SCOPES.photosReadApp].sort());
  assert.ok(!resolveConfig(ON).scopes.some((s) => /photoslibrary(\.readonly|\.sharing)?$/.test(s)), "never the removed whole-library scopes");
  const names = (env) => ctxFor([], { seed: SEED, extraEnv: env }).listTools().map((t) => t.name);
  const off = names({}), on = names(ON), ro = names({ ...ON, GOOGLE_READONLY: "1" });
  for (const n of [...READ, ...WRITE]) { assert.ok(!off.includes(n), n); assert.ok(on.includes(n), n); }
  for (const n of READ) assert.ok(ro.includes(n), n);
  for (const n of WRITE) assert.ok(!ro.includes(n), n);
  for (const n of [...READ, ...WRITE]) assert.ok(CLASSES.option_tools.includes(n) && CLASSES.plugin_tools.includes(n) && !CLASSES.rest_tools.includes(n), n);
  const tools = ctxFor([], { seed: SEED, extraEnv: ON }).listTools();
  for (const n of [...WRITE, "photos_list_app_items", "photos_search_app_items", "photos_get_app_item", "photos_list_app_albums"]) {
    assert.match(tools.find((t) => t.name === n).description, /cannot see, search or delete photos the plugin did not upload/, n);
  }
});

test("SCOPE_MISSING with the sign-in hint (GOOGLE_CLI_COMMAND) before any Photos call; status lists the missing Photos scopes", async () => {
  const seen = [];
  const c = ctxFor([tokenOk, photos([], seen)], { seed: { account: { email: "me@mail.example" }, scopes_granted: FULL_GRANT }, extraEnv: { ...ON, GOOGLE_CLI_COMMAND: "google-nino" } });
  await assert.rejects(c.callTool("photos_picker_start", {}), (e) => e.code === "SCOPE_MISSING" && /google-nino sign-in/.test(e.hint) && /GOOGLE_PHOTOS=1/.test(e.hint));
  await assert.rejects(c.callTool("photos_create_album", { title: "x" }), { code: "SCOPE_MISSING" });
  assert.equal(seen.length, 0);
  const st = await c.callTool("google_auth_status", { verify: false });
  for (const s of PHOTO_SCOPES) assert.ok(st.scopes_missing.includes(s), s);
});

// ------------------------------------------------------------------------------------------------ Picker

test("picker start / status / list / end: Google's session paths, maxItemCount as a string, picked items shaped", async () => {
  const seen = [];
  const c = ctxFor([tokenOk, photos([
    ["POST picker sessions", () => json({ id: "s1", pickerUri: "https://photos.google.com/picker/s1", expireTime: "2026-11-27T12:00:00Z", pollingConfig: { pollInterval: "5s", timeoutIn: "1800s" }, mediaItemsSet: false })],
    ["GET picker sessions/s1", () => json({ id: "s1", mediaItemsSet: true, pollingConfig: { pollInterval: "5s" } })],
    ["GET picker mediaItems", () => json({ mediaItems: [picked("a"), { ...picked("v"), type: "VIDEO", mediaFile: { ...picked("v").mediaFile, mimeType: "video/mp4", mediaFileMetadata: { width: 1, height: 2, videoMetadata: { processingStatus: "READY" } } } }], nextPageToken: "n2" })],
    ["DELETE picker sessions/s1", () => json({})],
  ], seen)], { seed: SEED, extraEnv: ON });
  const s = await c.callTool("photos_picker_start", { maxItems: 9000 });
  assert.deepEqual(seen[0].body, { pickingConfig: { maxItemCount: "2000" } });
  assert.deepEqual(s, { sessionId: "s1", pickerUri: "https://photos.google.com/picker/s1", expireTime: "2026-11-27T12:00:00Z", pollingConfig: { pollInterval: "5s", timeoutIn: "1800s" }, mediaItemsSet: false });
  assert.equal((await c.callTool("photos_picker_status", { sessionId: "s1" })).mediaItemsSet, true);
  const l = await c.callTool("photos_picker_list", { sessionId: "s1" });
  assert.equal(seen.at(-1).query.sessionId, "s1");
  assert.equal(seen.at(-1).query.pageSize, "100");
  assert.deepEqual(l.items[0], { id: "a", type: "PHOTO", createTime: "2026-11-01T10:00:00Z", mimeType: "image/jpeg", filename: "IMG_a", width: 400, height: 300 });
  assert.equal(l.items[1].videoStatus, "READY");
  assert.equal(l.nextPageToken, "n2");
  assert.equal(l.untrusted, true);
  assert.doesNotMatch(JSON.stringify(l), /googleusercontent/, "baseUrls are not handed out");
  assert.deepEqual(await c.callTool("photos_picker_end", { sessionId: "s1" }), { sessionId: "s1", ended: true });
  assert.equal(seen.at(-1).method, "DELETE");
});

test("picker download: =d for photos and =dv for videos with the Bearer header; extension added; unready video, foreign host and limits per item", async () => {
  const dir = dl(), media = [];
  const items = [
    picked("a"),
    { ...picked("v"), type: "VIDEO", mediaFile: { baseUrl: "https://video.googleusercontent.com/vv/v", mimeType: "video/mp4", filename: "clip.mp4", mediaFileMetadata: { videoMetadata: { processingStatus: "READY" } } } },
    { ...picked("p"), type: "VIDEO", mediaFile: { baseUrl: "https://lh3.googleusercontent.com/pp/p", mimeType: "video/mp4", filename: "slow.mp4", mediaFileMetadata: { videoMetadata: { processingStatus: "PROCESSING" } } } },
    { ...picked("x"), mediaFile: { ...picked("x").mediaFile, baseUrl: "https://evil.example/steal" } },
  ];
  const c = ctxFor([tokenOk, photos([["GET picker mediaItems", () => json({ mediaItems: items })]]),
    [MEDIA, ({ url, init }) => { media.push({ url, auth: init.headers?.Authorization }); return new Response(Buffer.from(`BYTES ${url}`)); }],
  ], { seed: SEED, extraEnv: { ...ON, GOOGLE_DOWNLOAD_DIR: dir } });
  const r = await c.callTool("photos_picker_download", { sessionId: "s1", all: true });
  const by = Object.fromEntries(r.results.map((x) => [x.id, x]));
  assert.equal(basename(by.a.path), "IMG_a.jpg");
  assert.equal(readFileSync(by.a.path, "utf8"), "BYTES https://lh3.googleusercontent.com/pp/a=d");
  assert.equal(basename(by.v.path), "clip.mp4");
  assert.ok(media.some((m) => m.url.endsWith("/vv/v=dv")));
  assert.ok(media.every((m) => m.auth === "Bearer at-live"));
  assert.equal(by.p.ok, false);
  assert.equal(by.p.error.code, "NOT_READY");
  assert.equal(by.x.ok, false);
  assert.ok(!media.some((m) => m.url.includes("evil")), "no request to a foreign host");
  assert.equal(c.fetch.calls.filter((x) => x.url.includes("evil")).length, 0);
  await assert.rejects(c.callTool("photos_picker_download", { sessionId: "s1", ids: ["zzz"] }), { code: "NOT_FOUND" });
  await assert.rejects(c.callTool("photos_picker_download", { sessionId: "s1" }), { code: "INVALID_ARGUMENT" });
  assert.equal(readdirSync(dir).length, 2);
});

test("picker download: at most 50 per call (the rest come back as not_downloaded); oversized items fail alone", async () => {
  const many = Array.from({ length: 53 }, (_, i) => picked(`m${i}`));
  const c = ctxFor([tokenOk, photos([["GET picker mediaItems", () => json({ mediaItems: many })]]), [MEDIA, () => new Response(Buffer.alloc(3000, 1))]],
    { seed: SEED, extraEnv: { ...ON, GOOGLE_DOWNLOAD_DIR: dl(), GOOGLE_MAX_SAVE_MB: String(2000 / 1048576) } });
  const r = await c.callTool("photos_picker_download", { sessionId: "s", all: true });
  assert.equal(r.results.length, 50);
  assert.deepEqual(r.not_downloaded, ["m50", "m51", "m52"]);
  assert.ok(r.results.every((x) => !x.ok && x.error.code === "TOO_LARGE"));
});

test("pickerMediaUrl: https googleusercontent.com hosts only", () => {
  assert.equal(pickerMediaUrl("https://lh3.googleusercontent.com/a/b", "=d"), "https://lh3.googleusercontent.com/a/b=d");
  for (const u of ["http://lh3.googleusercontent.com/a", "https://googleusercontent.com.evil.example/a", "https://evil.example/googleusercontent.com", "", undefined]) {
    assert.throws(() => pickerMediaUrl(u, "=d"), { code: "GOOGLE_ERROR" }, String(u));
  }
});

// ------------------------------------------------------------------------------------------------ upload

test("photos_upload: allowed files only, raw upload with Google's headers, one batchCreate with tokens, names, album and description; per-file status", async () => {
  const dir = dl(), seen = [];
  writeFileSync(join(dir, "a.jpg"), "AAA");
  writeFileSync(join(dir, "b.png"), "BBB");
  let n = 0;
  const c = ctxFor([tokenOk, photos([
    ["POST library uploads", () => new Response(`tok-${++n}`)],
    ["POST library mediaItems:batchCreate", (rec) => json({ newMediaItemResults: [
      { uploadToken: rec.body.newMediaItems[0].simpleMediaItem.uploadToken, status: { message: "Success" }, mediaItem: { id: "mi1", filename: "a.jpg", mimeType: "image/jpeg", productUrl: "https://photos.google.com/lr/photo/mi1", mediaMetadata: { creationTime: "2026-11-27T00:00:00Z", width: "4", height: "3", photo: {} } } },
      { uploadToken: rec.body.newMediaItems[1].simpleMediaItem.uploadToken, status: { code: 3, message: "Failed: There was an error while trying to create this media item." } },
    ] })],
  ], seen)], { seed: SEED, extraEnv: { ...ON, GOOGLE_ATTACH_DIRS: dir } });
  const r = await c.callTool("photos_upload", { paths: [join(dir, "a.jpg"), join(dir, "b.png")], albumId: "al1", description: "Trip" });
  const ups = seen.filter((s) => s.path === "uploads");
  assert.equal(ups.length, 2);
  assert.equal(ups[0].headers["Content-Type"], "application/octet-stream");
  assert.equal(ups[0].headers["X-Goog-Upload-Protocol"], "raw");
  assert.equal(ups[0].headers["X-Goog-Upload-Content-Type"], "image/jpeg");
  assert.equal(String(ups[0].raw), "AAA");
  const bc = seen.find((s) => s.path === "mediaItems:batchCreate").body;
  assert.deepEqual(bc, { albumId: "al1", newMediaItems: [
    { description: "Trip", simpleMediaItem: { uploadToken: "tok-1", fileName: "a.jpg" } },
    { description: "Trip", simpleMediaItem: { uploadToken: "tok-2", fileName: "b.png" } },
  ] });
  assert.equal(r.uploaded, 1);
  assert.equal(r.failed, 1);
  assert.equal(r.results[0].mediaItem.id, "mi1");
  assert.equal(r.results[0].mediaItem.width, 4);
  assert.match(r.results[1].error.message, /error while trying/);

  const before = seen.length;
  await assert.rejects(c.callTool("photos_upload", { paths: [join(tmpdir(), "elsewhere.jpg")] }), { code: "PATH_NOT_ALLOWED" });
  await assert.rejects(c.callTool("photos_upload", { paths: Array.from({ length: 51 }, () => join(dir, "a.jpg")) }), { code: "INVALID_ARGUMENT" });
  await assert.rejects(c.callTool("photos_upload", { paths: [join(dir, "a.jpg")], description: "x".repeat(1000) }), { code: "INVALID_ARGUMENT" });
  assert.equal(seen.length, before, "refused before any upload");
});

// ------------------------------------------------------------------------------------------------ app-created library

test("app-created items: list (pageSize capped), search filters (dates, range, media type; not with albumId), get, description patch", async () => {
  const seen = [];
  const ITEM = { id: "mi1", filename: "a.jpg", mimeType: "image/jpeg", description: "d", productUrl: "u", baseUrl: "https://lh3.googleusercontent.com/x", mediaMetadata: { creationTime: "t", width: "10", height: "20", video: { status: "READY" } } };
  const c = ctxFor([tokenOk, photos([
    ["GET library mediaItems", () => json({ mediaItems: [ITEM], nextPageToken: "n" })],
    ["POST library mediaItems:search", () => json({ mediaItems: [ITEM] })],
    ["GET library mediaItems/mi1", () => json(ITEM)],
    ["PATCH library mediaItems/mi1", (rec) => json({ ...ITEM, description: rec.body.description })],
  ], seen)], { seed: SEED, extraEnv: ON });
  const l = await c.callTool("photos_list_app_items", { pageSize: 500 });
  assert.equal(seen[0].query.pageSize, "100");
  assert.deepEqual(l.items[0], { id: "mi1", filename: "a.jpg", mimeType: "image/jpeg", description: "d", productUrl: "u", creationTime: "t", width: 10, height: 20, type: "VIDEO", videoStatus: "READY" });
  assert.doesNotMatch(JSON.stringify(l), /googleusercontent/);
  await c.callTool("photos_search_app_items", { dates: ["2026-11-01"], dateFrom: "2026-01-01", dateTo: "2026-02-01", mediaType: "PHOTO" });
  assert.deepEqual(seen.at(-1).body, { filters: { dateFilter: { dates: [{ year: 2026, month: 11, day: 1 }], ranges: [{ startDate: { year: 2026, month: 1, day: 1 }, endDate: { year: 2026, month: 2, day: 1 } }] }, mediaTypeFilter: { mediaTypes: ["PHOTO"] } }, pageSize: 25 });
  await c.callTool("photos_search_app_items", { albumId: "al1" });
  assert.deepEqual(seen.at(-1).body, { albumId: "al1", pageSize: 25 });
  await assert.rejects(c.callTool("photos_search_app_items", { albumId: "al1", mediaType: "PHOTO" }), { code: "INVALID_ARGUMENT" });
  await assert.rejects(c.callTool("photos_search_app_items", { dates: ["2026/11/01"] }), { code: "INVALID_ARGUMENT" });
  await assert.rejects(c.callTool("photos_search_app_items", { dates: ["2026-01-01", "2026-01-02", "2026-01-03", "2026-01-04", "2026-01-05", "2026-01-06"] }), { code: "INVALID_ARGUMENT" });
  assert.equal((await c.callTool("photos_get_app_item", { mediaItemId: "mi1" })).item.id, "mi1");
  const p = await c.callTool("photos_update_app_item_description", { mediaItemId: "mi1", description: "New" });
  assert.equal(seen.at(-1).query.updateMask, "description");
  assert.deepEqual(seen.at(-1).body, { description: "New" });
  assert.equal(p.item.description, "New");
});

test("app-created albums: create, list (pageSize capped at 50), add / remove items (50 max, no repeats), rename with updateMask title", async () => {
  const seen = [];
  const c = ctxFor([tokenOk, photos([
    ["POST library albums", (rec) => json({ id: "al1", title: rec.body.album.title, productUrl: "u", isWriteable: true })],
    ["GET library albums", () => json({ albums: [{ id: "al1", title: "Trip", mediaItemsCount: "3" }] })],
    ["POST library albums/al1:batchAddMediaItems", () => json({})],
    ["POST library albums/al1:batchRemoveMediaItems", () => json({})],
    ["PATCH library albums/al1", (rec) => json({ id: "al1", title: rec.body.title })],
  ], seen)], { seed: SEED, extraEnv: ON });
  const a = await c.callTool("photos_create_album", { title: "Trip" });
  assert.deepEqual(seen[0].body, { album: { title: "Trip" } });
  assert.deepEqual(a.album, { id: "al1", title: "Trip", productUrl: "u", mediaItemsCount: 0, isWriteable: true });
  const l = await c.callTool("photos_list_app_albums", { pageSize: 99 });
  assert.equal(seen.at(-1).query.pageSize, "50");
  assert.equal(l.albums[0].mediaItemsCount, 3);
  assert.deepEqual(await c.callTool("photos_album_add_items", { albumId: "al1", mediaItemIds: ["m1", "m2"] }), { albumId: "al1", added: 2 });
  assert.deepEqual(seen.at(-1).body, { mediaItemIds: ["m1", "m2"] });
  assert.deepEqual(await c.callTool("photos_album_remove_items", { albumId: "al1", mediaItemIds: ["m1"] }), { albumId: "al1", removed: 1 });
  assert.equal(seen.at(-1).path, "albums/al1:batchRemoveMediaItems");
  const before = seen.length;
  await assert.rejects(c.callTool("photos_album_add_items", { albumId: "al1", mediaItemIds: Array.from({ length: 51 }, (_, i) => `m${i}`) }), { code: "INVALID_ARGUMENT" });
  await assert.rejects(c.callTool("photos_album_remove_items", { albumId: "al1", mediaItemIds: ["m1", "m1"] }), { code: "INVALID_ARGUMENT" });
  await assert.rejects(c.callTool("photos_album_remove_items", { albumId: "al1", mediaItemIds: [] }), { code: "INVALID_ARGUMENT" });
  await assert.rejects(c.callTool("photos_create_album", { title: "x".repeat(501) }), { code: "INVALID_ARGUMENT" });
  assert.equal(seen.length, before);
  const t = await c.callTool("photos_update_album_title", { albumId: "al1", title: "Trip 2026" });
  assert.equal(seen.at(-1).query.updateMask, "title");
  assert.equal(t.album.title, "Trip 2026");
});

test("the REST client itself refuses Photos calls when GOOGLE_PHOTOS is off, and needs no REST switch when it is on", async () => {
  const { createRest } = await import("../server/rest.mjs");
  const off = ctxFor([tokenOk, photos([])], { seed: SEED });
  await assert.rejects(createRest(off.ctx).call("photos", "GET", "albums"), { code: "PHOTOS_DISABLED" });
  await assert.rejects(createRest(off.ctx).call("gmail", "GET", "labels"), { code: "REST_DISABLED" });
  const on = ctxFor([tokenOk, photos([["GET library albums", () => json({ albums: [] })]])], { seed: SEED, extraEnv: ON });
  assert.deepEqual(await createRest(on.ctx).call("photos", "GET", "albums"), { albums: [] });
  await assert.rejects(createRest(on.ctx).call("gmail", "GET", "labels"), { code: "REST_DISABLED" }, "Photos does not open the Workspace REST tools");
});
