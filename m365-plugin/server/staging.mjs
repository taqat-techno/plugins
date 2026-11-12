// staging.mjs - a small per-user store for things that are prepared first and confirmed second:
// calendar events, Teams messages and mail-draft previews. A stage records a digest of exactly what the user
// saw; the commit tool refuses unless the digest matches, and a state machine blocks a second send.
//   staged -> committed          (calendar)
//   staged -> sending -> sent    (Teams: 'sending' is written BEFORE the request, so an unknown outcome blocks a repeat)
//   mail:  (none) -> sending -> sent, same rule, keyed by draft id
// File: <M365_HOME>/staged.json, atomic writes, entries expire after 24 hours.
//
// Several processes share this file (Claude Code and an agent bot can both use ~/.m365-plugin), so every
// read-modify-write runs under a lock file, and the "check, then move to sending" step is one locked operation:
// two processes can never both claim the same send.
import { createHash, randomUUID } from "node:crypto";
import { closeSync, mkdirSync, openSync, readFileSync, statSync, unlinkSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { M365Error, replaceFile } from "./util.mjs";

const TTL_MS = 24 * 3600 * 1000;
const LOCK_WAIT_MS = 5000, LOCK_STALE_MS = 10_000, LOCK_STEP_MS = 15;

const canon = (v) => JSON.stringify(v, (_k, x) => (x && typeof x === "object" && !Array.isArray(x) ? Object.fromEntries(Object.keys(x).sort().map((k) => [k, x[k]])) : x));
export const digestOf = (payload) => createHash("sha256").update(canon(payload)).digest("hex").slice(0, 16);

const pause = (ms) => Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, ms);

/** Run fn while holding <file>.lock. A lock older than LOCK_STALE_MS is from a crashed process and is taken over. */
export function withFileLock(file, fn) {
  const lock = `${file}.lock`;
  const deadline = Date.now() + LOCK_WAIT_MS;
  let fd = null;
  while (fd === null) {
    try { fd = openSync(lock, "wx"); }
    catch (e) {
      // EEXIST: someone holds it. On Windows, EPERM/EACCES also mean "held": the previous holder's lock file is still
      // being deleted. Anything else (a missing folder, a real permission problem) is a real error.
      if (!["EEXIST", "EPERM", "EACCES"].includes(e.code)) throw e;
      if (Date.now() > deadline) {
        if (e.code !== "EEXIST") throw e;
        throw new M365Error("BUSY", "Another Microsoft 365 action is in progress. Try again in a moment.");
      }
      let age = 0;
      try { age = Date.now() - statSync(lock).mtimeMs; } catch { /* vanished: just try again */ }
      if (age > LOCK_STALE_MS) { try { unlinkSync(lock); } catch { /* someone else took it over */ } continue; }
      pause(LOCK_STEP_MS);
    }
  }
  try { return fn(); }
  finally { closeSync(fd); try { unlinkSync(lock); } catch { /* already gone */ } }
}

const stateError = (kind, s) => {
  const done = s.state === "sent" || s.state === "committed";
  return new M365Error(done ? "ALREADY_DONE" : "STAGE_NOT_READY", done
    ? `This ${kind} was already ${s.state}. Nothing was repeated.`
    : s.state === "sending"
      ? `The earlier attempt to send this ${kind} may or may not have gone through. Check the result before trying again; nothing was repeated.`
      : `This ${kind} is ${s.state}.`);
};

export function createStaging(cfg, { now = () => Date.now() } = {}) {
  const path = join(cfg.home, "staged.json");
  const load = () => { try { const j = JSON.parse(readFileSync(path, "utf8")); return j && typeof j === "object" ? j : {}; } catch { return {}; } };
  const save = (all) => {
    for (const [k, v] of Object.entries(all)) if (now() - v.created > TTL_MS) delete all[k];
    const tmp = `${path}.${process.pid}.${randomUUID()}.tmp`;
    writeFileSync(tmp, JSON.stringify(all, null, 2), { mode: 0o600 });
    replaceFile(tmp, path);
  };
  /** Locked read-modify-write. fn may change `all` and return a value; the file is saved afterwards. */
  const update = (fn) => {
    mkdirSync(cfg.home, { recursive: true });
    return withFileLock(path, () => { const all = load(); const r = fn(all); save(all); return r; });
  };
  // Ids and digests must be plain text: String(["calchange_x"]) would otherwise reach a different stage than the
  // confirmation hook described.
  const plain = (v, field) => { if (typeof v !== "string") throw new M365Error("INVALID_ARGUMENT", `${field} must be a string`); return v; };
  const check = (all, id, kind, digest, states) => {
    plain(id, "stage_id"); plain(digest, "digest");
    const s = all[String(id)];
    if (!s || s.kind !== kind) throw new M365Error("STAGE_NOT_FOUND", `No staged ${kind} with id ${id} (it may have expired after 24 hours).`);
    if (!states.includes(s.state)) throw stateError(kind, s);
    if (String(digest ?? "") !== s.digest) throw new M365Error("DIGEST_MISMATCH", "The digest does not match what was previewed. Show the user the preview again and pass its digest.");
    return s;
  };
  const mailKey = (draftId) => `mailsent_${draftId}`;

  return {
    create(kind, payload) {
      return update((all) => {
        const id = `${kind}_${randomUUID().slice(0, 8)}`;
        all[id] = { id, kind, state: "staged", payload, digest: digestOf(payload), created: now() };
        return { ...all[id] };
      });
    },
    /** Remember a mail preview under the draft id (replaces an older preview). */
    setPreview(draftId, digest) {
      update((all) => { all[`mailpreview_${draftId}`] = { id: `mailpreview_${draftId}`, kind: "mailpreview", state: "previewed", digest, created: now() }; });
    },
    getPreview(draftId) { return load()[`mailpreview_${draftId}`] ?? null; },
    clearPreview(draftId) { update((all) => { delete all[`mailpreview_${draftId}`]; }); },
    /** Mail send state for a draft: null, "sending" or "sent". */
    mailSendState(draftId) { return load()[mailKey(draftId)]?.state ?? null; },
    /** Atomically claim a draft for sending: refuses if it is already sending or sent, or if the preview digest changed. */
    claimMailSend(draftId, digest) {
      return update((all) => {
        const s = all[mailKey(draftId)];
        if (s) throw stateError("email", s);
        if (all[`mailpreview_${draftId}`]?.digest !== digest) throw new M365Error("NOT_PREVIEWED", "This draft has not been previewed (or it changed since). Call email_preview_draft, show the user, then send.");
        all[mailKey(draftId)] = { id: mailKey(draftId), kind: "mailsent", state: "sending", created: now() };
      });
    },
    /** Microsoft definitely refused the send: nothing went out, so the draft may be sent again later. */
    releaseMailSend(draftId) { update((all) => { delete all[mailKey(draftId)]; }); },
    markMailSent(draftId) {
      update((all) => {
        all[mailKey(draftId)] = { id: mailKey(draftId), kind: "mailsent", state: "sent", created: now() };
        delete all[`mailpreview_${draftId}`];
      });
    },
    wasMailSent(draftId) { return load()[mailKey(draftId)]?.state === "sent"; },
    /** Returns the stage if it is of `kind`, in one of `states`, and the digest matches what the user saw. */
    require(id, kind, digest, states = ["staged"]) { return { ...check(load(), id, kind, digest, states) }; },
    /** require() and a state change as one locked step, so two processes cannot both commit the same stage. */
    transition(id, kind, digest, to, states = ["staged"]) {
      return update((all) => { const s = check(all, id, kind, digest, states); s.state = to; return { ...s }; });
    },
    set(id, patch) { return update((all) => { if (all[id]) Object.assign(all[id], patch); return all[id] ? { ...all[id] } : undefined; }); },
    /** Change state only if the entry is still in `from` (for cancel/discard). Returns the entry or throws. */
    move(id, kind, from, to) {
      plain(id, "stage_id");
      return update((all) => {
        const s = all[String(id)];
        if (!s || s.kind !== kind) throw new M365Error("STAGE_NOT_FOUND", `No staged ${kind} with that id.`);
        if (s.state !== from) throw new M365Error("ALREADY_DONE", `This ${kind} is already ${s.state}; it cannot be ${to} here.`);
        s.state = to;
        return { ...s };
      });
    },
    get(id) { return load()[String(id)] ?? null; },
  };
}
