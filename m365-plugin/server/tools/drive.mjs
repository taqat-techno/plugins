// OneDrive and SharePoint files: browse folders and libraries, and manage the user's OWN OneDrive (upload, folders,
// move/rename, delete to the recycle bin, share with named people).
//
// Writes are limited to /me/drive on purpose: Files.ReadWrite covers only the user's own OneDrive, and keeping writes
// there means a tool can never change a team library. Reading any drive the user can open (a SharePoint library, a file
// shared with them) uses Files.Read.All like onedrive_search. Listing SharePoint sites needs Sites.Read.All, which is
// its own module ("sites", off by default) so enabling it never changes the permissions of an existing sign-in.
//
// Folder paths are plain "Documents/Reports" style paths inside the user's OneDrive; every segment is checked and
// encoded, so a path can never step outside the drive or smuggle Graph syntax.
import { EMAIL_RE, M365Error, UNTRUSTED_FIELDS, clampLimit, clean, safeId, safeStr, seg } from "../util.mjs";
import { allowedFile, contentTypeOf, readAllowed } from "../attach.mjs";

const SELECT = "id,name,size,lastModifiedDateTime,webUrl,parentReference,file,folder,root,specialFolder";

/** A folder path inside the user's OneDrive: "" is the top level. Returns the cleaned segments. */
function folderSegments(v, field = "folder_path") {
  const s = safeStr(v ?? "", field, 400) ?? "";
  const parts = s.replace(/\\/g, "/").split("/").map((p) => p.trim()).filter(Boolean);
  for (const p of parts) {
    if (p === "." || p === ".." || /[:*?"<>|#%]/.test(p)) throw new M365Error("INVALID_ARGUMENT", `${field} has an invalid folder name: "${p}"`);
  }
  return parts;
}
const pathOf = (parts) => (parts.length ? `/me/drive/root:/${parts.map(seg).join("/")}:` : "/me/drive/root");

/** A file or folder name: no path separators or characters OneDrive refuses. */
function itemName(v, field = "name") {
  const s = (safeStr(v, field, 200) ?? "").trim();
  if (!s || s === "." || s === ".." || /[\\/:*?"<>|]/.test(s) || /[. ]$/.test(s)) throw new M365Error("INVALID_ARGUMENT", `${field} is not a valid file or folder name`);
  return s;
}

function itemOut(f) {
  return {
    name: clean(f.name, 200), is_folder: !!f.folder, ...(f.folder ? { child_count: f.folder.childCount ?? null } : { size_bytes: f.size ?? null }),
    modified: f.lastModifiedDateTime ?? null, web_url: f.webUrl ?? null, drive_id: f.parentReference?.driveId ?? null, item_id: f.id,
  };
}

/** An item in the user's own OneDrive, refusing the drive's top level and its system folders. */
async function ownItem(ctx, itemId) {
  const id = safeId(itemId, "item_id");
  const f = await ctx.graph.get(`/me/drive/items/${seg(id)}?$select=${SELECT}`);
  if (f.root || f.specialFolder) throw new M365Error("INVALID_ARGUMENT", "That is the top of your OneDrive or one of its system folders, which cannot be changed from here.");
  return { id, f };
}

async function ownFolderId(ctx, parts) {
  const f = await ctx.graph.get(`${pathOf(parts)}?$select=id,name,folder`);
  if (!f.folder) throw new M365Error("INVALID_ARGUMENT", "folder_path is a file, not a folder.");
  return f.id;
}

export const tools = [
  {
    name: "onedrive_list_folder", kind: "read", module: "files",
    description: "List what is in a folder: by folder_path in the user's own OneDrive (\"\" = top level, \"Documents/Reports\"), or by drive_id (+ item_id, default the library's top) for a SharePoint library or a shared folder (ids from onedrive_search or sharepoint_list_libraries). Returns name, is_folder, size, modified, web link, drive_id and item_id. Newest first.",
    inputSchema: { type: "object", properties: {
      folder_path: { type: "string" }, drive_id: { type: "string" }, item_id: { type: "string" }, limit: { type: "number", description: "1-200, default 50." } } },
    async handler(a, ctx) {
      const n = clampLimit(a.limit, 50, 200);
      let base;
      if (a.drive_id) {
        if (a.folder_path) throw new M365Error("INVALID_ARGUMENT", "give folder_path (your OneDrive) or drive_id, not both");
        base = `/drives/${seg(safeId(a.drive_id, "drive_id"))}/${a.item_id ? `items/${seg(safeId(a.item_id, "item_id"))}` : "root"}`;
      } else {
        if (a.item_id) throw new M365Error("INVALID_ARGUMENT", "item_id needs drive_id");
        base = pathOf(folderSegments(a.folder_path));
      }
      const out = [];
      let url = `${base}/children?$top=${Math.min(n, 200)}&$orderby=${encodeURIComponent("lastModifiedDateTime desc")}&$select=${SELECT}`;
      while (url && out.length < n) {
        const j = await ctx.graph.get(url);
        out.push(...(j.value ?? []));
        url = j["@odata.nextLink"] ?? null;
      }
      return { count: Math.min(out.length, n), more_available: out.length > n || Boolean(url), items: out.slice(0, n).map(itemOut), note: UNTRUSTED_FIELDS };
    },
  },
  {
    name: "sharepoint_list_sites", kind: "read", module: "sites",
    description: "Find SharePoint sites: with query, sites whose name matches; without, the sites the user follows. Returns site_id, name and web link; then sharepoint_list_libraries.",
    inputSchema: { type: "object", properties: { query: { type: "string" }, limit: { type: "number", description: "1-50, default 20." } } },
    async handler(a, ctx) {
      const n = clampLimit(a.limit, 20, 50);
      const words = String(safeStr(a.query, "query", 100) ?? "").replace(/["'()\\:*<>=&?#%]/g, " ").replace(/\s+/g, " ").trim();
      const j = words
        ? await ctx.graph.get(`/sites?search=${encodeURIComponent(words)}&$top=${n}&$select=id,displayName,name,webUrl,description`)
        : await ctx.graph.get(`/me/followedSites?$select=id,displayName,name,webUrl,description`);
      const sites = (j.value ?? []).slice(0, n).map((s) => ({ site_id: s.id, name: clean(s.displayName || s.name, 200), web_url: s.webUrl ?? null, description: clean(s.description, 300) || null }));
      return { source: words ? "search" : "followed", count: sites.length, sites, note: UNTRUSTED_FIELDS };
    },
  },
  {
    name: "sharepoint_list_libraries", kind: "read", module: "sites",
    description: "List the document libraries of one SharePoint site (site_id from sharepoint_list_sites). Returns drive_id for onedrive_list_folder and onedrive_read_file.",
    inputSchema: { type: "object", properties: { site_id: { type: "string" } }, required: ["site_id"] },
    async handler(a, ctx) {
      const s = safeId(a.site_id, "site_id");
      const j = await ctx.graph.get(`/sites/${seg(s)}/drives?$select=id,name,webUrl,description,driveType`);
      return { site_id: s, libraries: (j.value ?? []).map((d) => ({ drive_id: d.id, name: clean(d.name, 200), web_url: d.webUrl ?? null, description: clean(d.description, 300) || null })), note: UNTRUSTED_FIELDS };
    },
  },
  {
    name: "onedrive_upload", kind: "write", module: "files", confirm: true,
    description: "Upload a file from this computer (path) or an image the user pasted into this chat (chat_image: 1 = the most recent) into the user's own OneDrive, into folder_path (\"\" = top level; the folder must exist). Never overwrites: a name already taken gets a number. The file stays private until shared. Same file rules as email attachments: keys and token files are never uploaded; a refusal is final. Claude Code shows the user the file first. Up to 25 MB.",
    inputSchema: { type: "object", properties: {
      path: { type: "string", description: "Absolute path of the file. Give this or chat_image." },
      chat_image: { type: "number", description: "An image the user pasted into this chat: 1 = the most recent. Claude Code only." },
      folder_path: { type: "string" }, name: { type: "string", description: "Optional name in OneDrive (default the file's own name)." } } },
    async handler(a, ctx) {
      if ((a.path === undefined || a.path === "") && a.chat_image !== undefined) {
        throw new M365Error("CHAT_IMAGE_UNAVAILABLE", "That pasted image could not be found or saved, so nothing was uploaded.",
          { hint: "Pasted images can be uploaded only in Claude Code with the plugin's hooks on. Otherwise ask the user to save the image as a file and give its path." });
      }
      if (a.path === undefined || a.path === "") throw new M365Error("INVALID_ARGUMENT", "give path (a file) or chat_image (a pasted image)");
      const f = allowedFile(ctx.cfg, a.path);
      const parts = folderSegments(a.folder_path);
      await ownFolderId(ctx, parts);
      const name = a.name !== undefined && a.name !== "" ? itemName(a.name) : itemName(f.name.replace(/[\\/:*?"<>|]/g, "_").replace(/[. ]+$/, "") || "file");
      const bytes = readAllowed(f);
      const target = parts.length ? `/me/drive/root:/${[...parts, name].map(seg).join("/")}:/content` : `/me/drive/root:/${seg(name)}:/content`;
      const r = await ctx.graph.putBytes(`${target}?@microsoft.graph.conflictBehavior=rename`, bytes, contentTypeOf(name));
      return { uploaded: true, name: clean(r.name ?? name, 200), renamed: Boolean(r.name && r.name !== name), size_bytes: bytes.length, folder_path: parts.join("/"), web_url: r.webUrl ?? null, drive_id: r.parentReference?.driveId ?? null, item_id: r.id ?? null, shared: false };
    },
  },
  {
    name: "onedrive_create_folder", kind: "write", module: "files",
    description: "Create a folder in the user's own OneDrive, inside folder_path (\"\" = top level). Refuses if that name is already taken there.",
    inputSchema: { type: "object", properties: { folder_path: { type: "string" }, name: { type: "string" } }, required: ["name"] },
    async handler(a, ctx) {
      const parts = folderSegments(a.folder_path);
      const name = itemName(a.name);
      const r = await ctx.graph.post(`${pathOf(parts)}/children`, { name, folder: {}, "@microsoft.graph.conflictBehavior": "fail" });
      return { created: true, name: clean(r.name, 200), folder_path: [...parts, name].join("/"), web_url: r.webUrl ?? null, drive_id: r.parentReference?.driveId ?? null, item_id: r.id };
    },
  },
  {
    name: "onedrive_move", kind: "write", module: "files",
    description: "Rename and/or move a file or folder in the user's own OneDrive (item_id from onedrive_list_folder or onedrive_search). new_name renames; to_folder_path moves (\"\" = top level; the folder must exist). Refuses if the name is taken at the destination. Can be undone by moving it back.",
    inputSchema: { type: "object", properties: { item_id: { type: "string" }, new_name: { type: "string" }, to_folder_path: { type: "string" } }, required: ["item_id"] },
    async handler(a, ctx) {
      if (a.new_name === undefined && a.to_folder_path === undefined) throw new M365Error("INVALID_ARGUMENT", "give new_name, to_folder_path, or both");
      const { id, f } = await ownItem(ctx, a.item_id);
      const patch = {};
      if (a.new_name !== undefined) patch.name = itemName(a.new_name, "new_name");
      if (a.to_folder_path !== undefined) {
        const parts = folderSegments(a.to_folder_path, "to_folder_path");
        patch.parentReference = { id: await ownFolderId(ctx, parts) };
        if (f.folder && patch.parentReference.id === id) throw new M365Error("INVALID_ARGUMENT", "A folder cannot be moved into itself.");
      }
      const r = await ctx.graph.patch(`/me/drive/items/${seg(id)}?@microsoft.graph.conflictBehavior=fail`, patch);
      return { moved: true, was: { name: clean(f.name, 200), folder: clean(f.parentReference?.path?.replace(/^\/drive\/root:?/, ""), 400) || "/" },
        now: { name: clean(r.name ?? patch.name ?? f.name, 200), folder: clean(r.parentReference?.path?.replace(/^\/drive\/root:?/, ""), 400) || "/" }, item_id: id, web_url: r.webUrl ?? null };
    },
  },
  {
    name: "onedrive_delete", kind: "write", module: "files", confirm: true,
    description: "Move a file or folder in the user's own OneDrive to its recycle bin (restorable from there for a while; Claude Code asks the user to confirm). A folder goes with everything in it, unless the organization's retention policy refuses non-empty folders (BLOCKED_BY_POLICY): then delete what is inside first. item_id from onedrive_list_folder or onedrive_search. Show the user the name first.",
    inputSchema: { type: "object", properties: { item_id: { type: "string" } }, required: ["item_id"] },
    async handler(a, ctx) {
      const { id, f } = await ownItem(ctx, a.item_id);
      await ctx.graph.del(`/me/drive/items/${seg(id)}`);
      return { deleted: true, to: "OneDrive recycle bin", name: clean(f.name, 200), is_folder: !!f.folder, ...(f.folder ? { items_inside: f.folder.childCount ?? null } : {}), item_id: id };
    },
  },
  {
    name: "onedrive_share_with", kind: "write", module: "files", confirm: true,
    description: "Give named people access to a file or folder in the user's own OneDrive: role read (view) or edit. They must sign in to open it; no anonymous link is made. notify: true also emails them Microsoft's sharing invitation with your optional message. emails must be addresses (people_resolve first). Claude Code asks the user to confirm; show who and which role before.",
    inputSchema: { type: "object", properties: {
      item_id: { type: "string" }, emails: { type: "array", items: { type: "string" } },
      role: { type: "string", enum: ["read", "edit"], description: "Default read." },
      notify: { type: "boolean", description: "Send Microsoft's invitation email. Default false." },
      message: { type: "string", description: "Short note in the invitation email (only with notify)." } }, required: ["item_id", "emails"] },
    async handler(a, ctx) {
      if (!Array.isArray(a.emails) || !a.emails.length || a.emails.length > 25) throw new M365Error("INVALID_ARGUMENT", "emails must list 1 to 25 addresses");
      const emails = [...new Set(a.emails.map((e) => String(safeStr(e, "emails", 254) ?? "").trim().toLowerCase()))];
      for (const e of emails) if (!EMAIL_RE.test(e)) throw new M365Error("INVALID_ARGUMENT", `"${e}" is not an email address. Resolve names with people_resolve first.`);
      const role = a.role === undefined ? "read" : String(a.role);
      if (!["read", "edit"].includes(role)) throw new M365Error("INVALID_ARGUMENT", "role must be read or edit");
      const notify = a.notify === true;
      const message = notify && a.message ? clean(safeStr(a.message, "message", 500), 500) : undefined;
      const { id, f } = await ownItem(ctx, a.item_id);
      const r = await ctx.graph.post(`/me/drive/items/${seg(id)}/invite`, {
        // Graph calls edit access "write".
        recipients: emails.map((email) => ({ email })), requireSignIn: true, sendInvitation: notify, roles: [role === "edit" ? "write" : "read"], ...(message ? { message } : {}),
      });
      const mine = String((await ctx.graph.get("/me?$select=mail,userPrincipalName")).mail ?? "").split("@")[1]?.toLowerCase();
      return {
        shared: true, name: clean(f.name, 200), role, with: emails, invitation_email_sent: notify,
        ...(mine ? { outside_your_domain: emails.filter((e) => e.split("@")[1] !== mine) } : {}),
        granted: (r.value ?? []).length, item_id: id, web_url: f.webUrl ?? null,
      };
    },
  },
];
