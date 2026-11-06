// staging.mjs - a small per-user store for things that are prepared first and confirmed second:
// calendar events, Teams messages and mail-draft previews. A stage records a digest of exactly what the user
// saw; the commit tool refuses unless the digest matches, and a state machine blocks a second send.
//   staged -> committed          (calendar)
//   staged -> sending -> sent    (Teams: 'sending' is written BEFORE the request, so an unknown outcome blocks a repeat)
// File: <M365_HOME>/staged.json, atomic writes, entries expire after 24 hours.
import { createHash, randomUUID } from "node:crypto";
import { mkdirSync, readFileSync, renameSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { M365Error } from "./util.mjs";

const TTL_MS = 24 * 3600 * 1000;

const canon = (v) => JSON.stringify(v, (_k, x) => (x && typeof x === "object" && !Array.isArray(x) ? Object.fromEntries(Object.keys(x).sort().map((k) => [k, x[k]])) : x));
export const digestOf = (payload) => createHash("sha256").update(canon(payload)).digest("hex").slice(0, 16);

export function createStaging(cfg, { now = () => Date.now() } = {}) {
  const path = join(cfg.home, "staged.json");
  const load = () => { try { const j = JSON.parse(readFileSync(path, "utf8")); return j && typeof j === "object" ? j : {}; } catch { return {}; } };
  const save = (all) => {
    for (const [k, v] of Object.entries(all)) if (now() - v.created > TTL_MS) delete all[k];
    mkdirSync(cfg.home, { recursive: true });
    const tmp = `${path}.${process.pid}.${randomUUID()}.tmp`;
    writeFileSync(tmp, JSON.stringify(all, null, 2), { mode: 0o600 });
    renameSync(tmp, path);
  };
  return {
    create(kind, payload) {
      const all = load();
      const id = `${kind}_${randomUUID().slice(0, 8)}`;
      all[id] = { id, kind, state: "staged", payload, digest: digestOf(payload), created: now() };
      save(all);
      return all[id];
    },
    /** Remember a mail preview under the draft id (replaces an older preview). */
    setPreview(draftId, digest) {
      const all = load();
      all[`mailpreview_${draftId}`] = { id: `mailpreview_${draftId}`, kind: "mailpreview", state: "previewed", digest, created: now() };
      save(all);
    },
    getPreview(draftId) { return load()[`mailpreview_${draftId}`] ?? null; },
    clearPreview(draftId) { const all = load(); if (all[`mailpreview_${draftId}`]) { delete all[`mailpreview_${draftId}`]; save(all); } },
    markMailSent(draftId) {
      const all = load();
      all[`mailsent_${draftId}`] = { id: `mailsent_${draftId}`, kind: "mailsent", state: "sent", created: now() };
      delete all[`mailpreview_${draftId}`];
      save(all);
    },
    wasMailSent(draftId) { return Boolean(load()[`mailsent_${draftId}`]); },
    /** Returns the stage if it is of `kind`, in one of `states`, and the digest matches what the user saw. */
    require(id, kind, digest, states = ["staged"]) {
      const s = load()[String(id)];
      if (!s || s.kind !== kind) throw new M365Error("STAGE_NOT_FOUND", `No staged ${kind} with id ${id} (it may have expired after 24 hours).`);
      if (!states.includes(s.state)) {
        const done = s.state === "sent" || s.state === "committed";
        throw new M365Error(done ? "ALREADY_DONE" : "STAGE_NOT_READY", done
          ? `This ${kind} was already ${s.state}. Nothing was repeated.`
          : s.state === "sending"
            ? `The earlier attempt to send this ${kind} may or may not have gone through. Check the result before trying again; nothing was repeated.`
            : `This ${kind} is ${s.state}.`);
      }
      if (String(digest ?? "") !== s.digest) throw new M365Error("DIGEST_MISMATCH", "The digest does not match what was previewed. Show the user the preview again and pass its digest.");
      return s;
    },
    set(id, patch) { const all = load(); if (all[id]) { Object.assign(all[id], patch); save(all); } return all[id]; },
    get(id) { return load()[String(id)] ?? null; },
  };
}
