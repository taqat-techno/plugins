// schema.mjs - compares Google's live tool list with the recorded snapshot (data/google_mcp_snapshot.json).
// The bridge exposes tools from the snapshot only, so drift never changes what agents see; this shows the drift so a
// maintainer can review it and, with --update, record the new list (the tests then demand a class for any new tool).
import { createHash } from "node:crypto";
import { writeFileSync } from "node:fs";
import { SNAPSHOT, CLASSES } from "./tools/bridge.mjs";

const hash = (o) => createHash("sha256").update(JSON.stringify(o ?? null)).digest("hex").slice(0, 16);

/** The snapshot's form of one live tool. */
export const snapEntry = (t) => ({ name: t.name, title: t.annotations?.title, description: t.description, annotations: t.annotations, inputSchema: t.inputSchema, outputSchema_sha256: hash(t.outputSchema) });

/** diff(module, liveTools) -> { added, removed, changed: [{name, fields}], exposed_affected } */
export function diffModule(mod, live) {
  const old = new Map((SNAPSHOT.servers[mod]?.tools ?? []).map((t) => [t.name, t]));
  const now = new Map(live.map((t) => [t.name, snapEntry(t)]));
  const added = [...now.keys()].filter((n) => !old.has(n));
  const removed = [...old.keys()].filter((n) => !now.has(n));
  const changed = [];
  for (const [n, t] of now) {
    const o = old.get(n);
    if (!o) continue;
    const fields = ["description", "inputSchema", "annotations", "outputSchema_sha256"].filter((f) => hash(o[f]) !== hash(t[f]));
    if (fields.length) changed.push({ name: n, fields });
  }
  const exposed = new Set(["read", "write", "confirm"].flatMap((k) => CLASSES[k] ?? []));
  const exposed_affected = [...removed, ...changed.map((c) => c.name)].filter((n) => exposed.has(`${mod}_${n}`)).map((n) => `${mod}_${n}`);
  return { added, removed, changed, exposed_affected };
}

/** Google tools whose name suggests they do what a REST fallback tool does (so the REST one can be removed). */
const REST_TWINS = [
  [/send/i, "gmail_rest_send_draft"], [/update_draft|edit_draft/i, "gmail_rest_update_draft"], [/delete_draft/i, "gmail_rest_delete_draft"],
  [/reply/i, "gmail_rest_create_reply_draft"], [/forward/i, "gmail_rest_create_forward_draft"],
  [/trash|delete/i, "drive_rest_trash_file"], [/untrash|restore/i, "drive_rest_untrash_file"], [/move/i, "drive_rest_move_file"],
  [/rename/i, "drive_rest_rename_file"], [/share|permission/i, "drive_rest_share_file"], [/unshare|remove_permission|delete_permission/i, "drive_rest_unshare_file"],
];
export function restTwins(mod, names) {
  const out = [];
  for (const n of names) for (const [re, rest] of REST_TWINS) if (re.test(n) && rest.startsWith(`${mod}_`)) out.push({ google_tool: `${mod}_${n}`, may_replace: rest });
  return out;
}

export async function schemaCheck(ctx, { update = false, modules = ctx.cfg.modules } = {}) {
  const report = {};
  const next = structuredClone(SNAPSHOT);
  for (const mod of modules) {
    const live = await ctx.remote.listTools(mod);
    const d = diffModule(mod, live);
    report[mod] = { live_tools: live.length, ...d, may_replace_rest: restTwins(mod, [...d.added, ...d.changed.map((c) => c.name)]) };
    next.servers[mod] = { url: ctx.cfg.mcpUrls[mod], tools: live.map(snapEntry) };
  }
  if (update) {
    next.recorded_at = new Date().toISOString().slice(0, 10);
    writeFileSync(new URL("../data/google_mcp_snapshot.json", import.meta.url), JSON.stringify(next, null, 1) + "\n");
  }
  return report;
}
