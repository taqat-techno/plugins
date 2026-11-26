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

export async function schemaCheck(ctx, { update = false, modules = ctx.cfg.modules } = {}) {
  const report = {};
  const next = structuredClone(SNAPSHOT);
  for (const mod of modules) {
    const live = await ctx.remote.listTools(mod);
    report[mod] = { live_tools: live.length, ...diffModule(mod, live) };
    next.servers[mod] = { url: ctx.cfg.mcpUrls[mod], tools: live.map(snapEntry) };
  }
  if (update) {
    next.recorded_at = new Date().toISOString().slice(0, 10);
    writeFileSync(new URL("../data/google_mcp_snapshot.json", import.meta.url), JSON.stringify(next, null, 1) + "\n");
  }
  return report;
}
