// mail folders: list the folder tree, move a message into any ordinary folder (by well-known name, path or id), create a
// folder. Deleting stays with email_delete (which asks the human): Deleted Items, Junk, Recoverable Items, Outbox and
// Drafts, and every folder inside them, are refused as move destinations. Nothing is ever created implicitly.
import { M365Error, UNTRUSTED_FIELDS, clean, safeId, safeStr, seg } from "../util.mjs";

const WELL_KNOWN = ["inbox", "archive", "sentitems"];
// Refused by name. Recoverable Items live outside the visible folder root, so the id check (which must reach that root)
// excludes them by construction; they are listed here too so their names are refused without any lookup.
const REQUIRED_FORBIDDEN = ["deleteditems", "junkemail", "outbox", "drafts"];
const FORBIDDEN = [...REQUIRED_FORBIDDEN, "recoverableitemsroot", "recoverableitemsdeletions", "recoverableitemspurges", "recoverableitemsversions"];
const MAX_FOLDERS = 1000, MAX_DEPTH = 10;
const SELECT = "id,displayName,parentFolderId,childFolderCount,unreadItemCount,totalItemCount";

async function pages(ctx, first, cap = MAX_FOLDERS) {
  const out = [];
  let url = first;
  while (url && out.length < cap) { const j = await ctx.graph.get(url); out.push(...(j.value ?? [])); url = j["@odata.nextLink"] ?? null; }
  return { items: out.slice(0, cap), complete: !url };
}

/** The whole folder tree, breadth-first, each folder with its path ("Inbox/Projects/NAFLA"). Bounded. */
export async function folderTree(ctx, { maxDepth = MAX_DEPTH } = {}) {
  const top = await pages(ctx, `/me/mailFolders?$top=100&$select=${SELECT}`);
  const all = top.items.map((f) => ({ ...f, path: f.displayName, depth: 1 }));
  let complete = top.complete;
  for (let i = 0; i < all.length && all.length < MAX_FOLDERS; i++) {
    const f = all[i];
    if (!f.childFolderCount || f.depth >= maxDepth) { if (f.childFolderCount) complete = false; continue; }
    const kids = await pages(ctx, `/me/mailFolders/${seg(f.id)}/childFolders?$top=100&$select=${SELECT}`, MAX_FOLDERS - all.length);
    if (!kids.complete) complete = false;
    for (const k of kids.items) all.push({ ...k, path: `${f.path}/${k.displayName}`, depth: f.depth + 1 });
  }
  if (all.length >= MAX_FOLDERS) complete = false;
  return { folders: all, complete };
}

/** The ids of the folders that must never be destinations. Fails CLOSED: if one of them cannot be looked up, nothing
 *  is moved, rather than checking against an incomplete list. */
async function forbiddenIds(ctx) {
  const ids = new Set();
  await Promise.all(REQUIRED_FORBIDDEN.map(async (w) => {
    let f;
    try { f = await ctx.graph.get(`/me/mailFolders/${w}?$select=id`); } catch (e) { throw checkFailed(e); }
    if (!f?.id) throw checkFailed();
    ids.add(f.id);
  }));
  return ids;
}
const checkFailed = (e) => new M365Error("FOLDER_CHECK_FAILED", "Could not confirm the destination is not a deleting or sending folder, so nothing was moved.", { hint: `Try again in a moment${e?.code ? ` (${e.code})` : ""}.` });

/** A folder by well-known name, id or path; refused if unknown, or if it is (inside) a deleting/sending folder. */
export async function resolveFolder(ctx, spec, { purpose = "move" } = {}) {
  const s = String(spec ?? "").trim();
  if (!s) throw new M365Error("INVALID_ARGUMENT", "folder is required");
  const refuse = () => new M365Error("FOLDER_NOT_ALLOWED", `Messages cannot be ${purpose === "move" ? "moved" : "filed"} into that folder from here (Deleted Items, Junk, Recoverable Items, Outbox and Drafts are excluded).`, { hint: "To delete a message use email_delete, which asks the user." });
  if (FORBIDDEN.includes(s.toLowerCase())) throw refuse(); // by name: refused before any lookup
  const bad = await forbiddenIds(ctx);
  if (WELL_KNOWN.includes(s.toLowerCase())) {
    const f = await ctx.graph.get(`/me/mailFolders/${s.toLowerCase()}?$select=${SELECT}`);
    return { id: f.id, path: clean(f.displayName, 200), well_known: s.toLowerCase() };
  }
  // A Graph folder id is a long URL-safe base64 string; anything else (even one word, e.g. "Projects") is a path.
  const looksLikeId = /^[A-Za-z0-9_=+-]{40,}$/.test(s);
  if (!looksLikeId) {
    // A path: walk it name by name (case-insensitive), so the ancestry is known and checked at every step.
    // A folder name may itself contain '/' (e.g. "CI/CD"), so at each level the LONGEST run of parts that names a
    // folder there wins: the same paths email_list_folders shows resolve back exactly.
    const parts = s.split("/").map((p) => p.trim()).filter(Boolean);
    let level = (await pages(ctx, `/me/mailFolders?$top=100&$select=${SELECT}`)).items, cur = null;
    const path = [];
    for (let i = 0; i < parts.length;) {
      let hits = [], used = 0;
      for (let j = parts.length; j > i && !hits.length; j--) {
        const name = parts.slice(i, j).join("/").toLowerCase();
        hits = level.filter((f) => String(f.displayName).trim().toLowerCase() === name);
        used = j - i;
      }
      const name = parts.slice(i, i + Math.max(used, 1)).join("/");
      if (hits.length !== 1) throw new M365Error(hits.length ? "AMBIGUOUS_FOLDER" : "FOLDER_NOT_FOUND", hits.length ? `"${name}" matches ${hits.length} folders at that level. Use the folder id from email_list_folders.` : `No folder "${[...path, parts[i]].join("/")}". Check email_list_folders; folders are never created implicitly.`);
      i += used;
      cur = hits[0];
      if (bad.has(cur.id)) throw refuse();
      path.push(cur.displayName);
      level = cur.childFolderCount ? (await pages(ctx, `/me/mailFolders/${seg(cur.id)}/childFolders?$top=100&$select=${SELECT}`)).items : [];
    }
    return { id: cur.id, path: clean(path.join("/"), 400) };
  }
  // An id: climb its parents. It is accepted ONLY if the climb reaches the visible folder root (msgfolderroot) within the
  // depth limit without passing a forbidden folder. Any failed lookup, a loop, or running out of depth is a refusal, and
  // folders outside that root (Recoverable Items and other system folders) can never qualify.
  const id = safeId(s, "folder");
  let root;
  try { root = (await ctx.graph.get("/me/mailFolders/msgfolderroot?$select=id")).id; } catch (e) { throw checkFailed(e); }
  if (!root) throw checkFailed();
  let f;
  try { f = await ctx.graph.get(`/me/mailFolders/${seg(id)}?$select=${SELECT}`); }
  catch (e) { if (e.code === "NOT_FOUND") throw new M365Error("FOLDER_NOT_FOUND", "No folder with that id. Use email_list_folders."); throw e; }
  if (f.id === root) throw refuse();
  const names = [f.displayName];
  const seen = new Set();
  let cur = f, reached = false;
  for (let i = 0; i < MAX_DEPTH; i++) {
    if (bad.has(cur.id) || seen.has(cur.id)) throw refuse();
    seen.add(cur.id);
    if (cur.parentFolderId === root) { reached = true; break; }
    if (!cur.parentFolderId) break;
    try { cur = await ctx.graph.get(`/me/mailFolders/${seg(cur.parentFolderId)}?$select=${SELECT}`); } catch { throw refuse(); }
    if (!cur?.id) throw refuse();
    names.unshift(cur.displayName);
  }
  if (!reached) throw refuse();
  return { id: f.id, path: clean(names.join("/"), 400) };
}

export const tools = [
  {
    name: "email_list_folders", kind: "read", module: "mail",
    description: "List the user's mail folders as a tree: each folder's id, name, path (e.g. Inbox/Projects/NAFLA), sub-folder count, unread and total counts. Use a path or id from here with email_move or email_create_folder. If 'complete' is false the mailbox has more folders than listed.",
    inputSchema: { type: "object", properties: { max_depth: { type: "number", description: "1-10, default 10." } } },
    async handler(a, ctx) {
      const depth = a.max_depth == null ? MAX_DEPTH : Math.max(1, Math.min(MAX_DEPTH, Math.floor(Number(a.max_depth)) || MAX_DEPTH));
      const t = await folderTree(ctx, { maxDepth: depth });
      return {
        count: t.folders.length, complete: t.complete,
        folders: t.folders.map((f) => ({ folder_id: f.id, name: clean(f.displayName, 200), path: clean(f.path, 400), child_count: f.childFolderCount ?? 0, unread: f.unreadItemCount ?? 0, total: f.totalItemCount ?? 0 })),
        note: UNTRUSTED_FIELDS,
      };
    },
  },
  {
    name: "email_move", kind: "write", module: "mail",
    description: "Move a message into a folder: inbox, archive, a path from email_list_folders such as Inbox/Projects/NAFLA, or a folder id. Unknown paths are refused (nothing is created). Deleted Items, Junk, Recoverable Items, Outbox and Drafts are not allowed: to delete a message use email_delete, which asks for confirmation.",
    inputSchema: { type: "object", properties: { message_id: { type: "string" }, folder: { type: "string", description: "inbox, archive, a folder path, or a folder id." } }, required: ["message_id", "folder"] },
    async handler(a, ctx) {
      const id = safeId(a.message_id, "message_id");
      const f = await resolveFolder(ctx, a.folder);
      const m = await ctx.graph.post(`/me/messages/${seg(id)}/move`, { destinationId: f.id });
      return { moved: true, folder: f.well_known ?? f.path, folder_id: f.id, message_id: m.id ?? id };
    },
  },
  {
    name: "email_create_folder", kind: "write", module: "mail",
    description: "Create a mail folder under a parent (inbox, archive, a folder path or id, or 'top' for the top level). Refuses a name containing '/' and a parent inside Deleted Items or Junk. Returns the new folder's id and path.",
    inputSchema: { type: "object", properties: {
      parent: { type: "string", description: "inbox, archive, top, a folder path, or a folder id." },
      name: { type: "string", description: "The new folder's name." } }, required: ["parent", "name"] },
    async handler(a, ctx) {
      const name = clean(safeStr(a.name, "name", 120) ?? "", 120).trim();
      if (!name) throw new M365Error("INVALID_ARGUMENT", "name is required");
      if (/[\\/]/.test(name)) throw new M365Error("INVALID_ARGUMENT", "a folder name cannot contain / or \\ (they separate folder paths here)");
      const top = String(a.parent ?? "").trim().toLowerCase() === "top";
      const parent = top ? { id: null, path: "" } : await resolveFolder(ctx, a.parent, { purpose: "create" });
      const f = await ctx.graph.post(top ? "/me/mailFolders" : `/me/mailFolders/${seg(parent.id)}/childFolders`, { displayName: name });
      return { created: true, folder_id: f.id, path: parent.path ? `${parent.path}/${clean(f.displayName ?? name, 200)}` : clean(f.displayName ?? name, 200) };
    },
  },
];
