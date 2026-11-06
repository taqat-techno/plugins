// profile.mjs - the user's local memory: who they are, the people they email, the Teams chats they use.
// A plain JSON file the user can read and edit (<M365_HOME>/profile.json, default ~/.m365-plugin).
// It holds no tokens or secrets. Per user and per machine; never shared between users.
import { mkdirSync, readFileSync, renameSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { randomUUID } from "node:crypto";
import { EMAIL_RE, M365Error, isValidZone, normName } from "./util.mjs";

const empty = () => ({
  version: 1,
  updated_at: null,
  me: { name: null, email: null, id: null, timezone: null, language: null },
  defaults: { meeting_minutes: 30, working_hours: { days: ["monday", "tuesday", "wednesday", "thursday", "friday"], start: "09:00", end: "17:00" } },
  contacts: [],
  chats: [],
});

const DAYS = ["sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday"];
const HHMM = /^([01]\d|2[0-3]):[0-5]\d$/;
const aliasesOf = (a) => [...new Set((Array.isArray(a) ? a : a ? [a] : []).map((s) => String(s).trim()).filter(Boolean))];

export function createProfile(cfg, { now = () => new Date() } = {}) {
  const path = join(cfg.home, "profile.json");

  function load() {
    try {
      const p = JSON.parse(readFileSync(path, "utf8"));
      const e = empty();
      return {
        ...e, ...p,
        me: { ...e.me, ...(p.me ?? {}) },
        defaults: { ...e.defaults, ...(p.defaults ?? {}), working_hours: { ...e.defaults.working_hours, ...(p.defaults?.working_hours ?? {}) } },
        contacts: Array.isArray(p.contacts) ? p.contacts : [],
        chats: Array.isArray(p.chats) ? p.chats : [],
      };
    } catch { return empty(); }
  }

  function save(p) {
    p.updated_at = now().toISOString();
    mkdirSync(cfg.home, { recursive: true });
    const tmp = `${path}.${process.pid}.${randomUUID()}.tmp`;
    writeFileSync(tmp, JSON.stringify(p, null, 2) + "\n", "utf8");
    renameSync(tmp, path);
    return p;
  }

  const matchesName = (entry, q) => {
    const n = normName(q);
    if (!n) return false;
    return [entry.name, ...(entry.aliases ?? [])].some((x) => normName(x) === n);
  };
  const looseName = (entry, q) => {
    const n = normName(q);
    if (!n) return false;
    return [entry.name, ...(entry.aliases ?? [])].some((x) => { const t = normName(x); return t.includes(n) || n.includes(t) || t.split(" ").some((w) => w === n); });
  };

  return {
    path, load, save,

    /** Exact, then loose, match of a name or alias among remembered contacts. */
    findContacts(q) {
      const p = load();
      const exact = p.contacts.filter((c) => matchesName(c, q) || (c.email ?? "").toLowerCase() === String(q).trim().toLowerCase());
      if (exact.length) return { exact: true, matches: exact };
      return { exact: false, matches: p.contacts.filter((c) => looseName(c, q)) };
    },
    findChats(q) {
      const p = load();
      const exact = p.chats.filter((c) => matchesName(c, q));
      return exact.length ? exact : p.chats.filter((c) => looseName(c, q));
    },

    set(fields) {
      const p = load();
      const m = p.me;
      for (const k of ["name", "email", "language"]) if (fields[k] !== undefined) m[k] = fields[k] === null ? null : String(fields[k]).trim();
      if (fields.email) {
        if (!EMAIL_RE.test(m.email)) throw new M365Error("INVALID_ARGUMENT", "email is not a valid address");
        m.email = m.email.toLowerCase();
      }
      if (fields.timezone !== undefined) {
        if (fields.timezone !== null && !isValidZone(fields.timezone)) throw new M365Error("INVALID_ARGUMENT", `timezone must be an IANA name such as Africa/Cairo (got "${fields.timezone}")`);
        m.timezone = fields.timezone;
      }
      if (fields.meeting_minutes !== undefined) {
        const n = Number(fields.meeting_minutes);
        if (!Number.isInteger(n) || n < 5 || n > 480) throw new M365Error("INVALID_ARGUMENT", "meeting_minutes must be a whole number from 5 to 480");
        p.defaults.meeting_minutes = n;
      }
      const wh = p.defaults.working_hours;
      if (fields.working_days !== undefined) {
        const d = (Array.isArray(fields.working_days) ? fields.working_days : String(fields.working_days).split(/[,\s]+/)).map((s) => String(s).toLowerCase()).filter(Boolean);
        if (!d.length || d.some((x) => !DAYS.includes(x))) throw new M365Error("INVALID_ARGUMENT", `working_days must be names such as ${DAYS.slice(0, 3).join(", ")}`);
        wh.days = d;
      }
      for (const [arg, key] of [["work_start", "start"], ["work_end", "end"]]) {
        if (fields[arg] !== undefined) {
          if (!HHMM.test(String(fields[arg]))) throw new M365Error("INVALID_ARGUMENT", `${arg} must look like 09:00`);
          wh[key] = String(fields[arg]);
        }
      }
      return save(p);
    },

    rememberContact({ name, email, aliases, note, source = "user", allow_same_name = false }) {
      const nm = String(name ?? "").trim();
      const em = String(email ?? "").trim().toLowerCase();
      if (!nm) throw new M365Error("INVALID_ARGUMENT", "name is required");
      if (!EMAIL_RE.test(em)) throw new M365Error("INVALID_ARGUMENT", "email is not a valid address");
      const p = load();
      let c = p.contacts.find((x) => (x.email ?? "").toLowerCase() === em);
      if (!allow_same_name) {
        // A name or alias that already points at another address must not be silently re-pointed: that is how a
        // poisoned contact would redirect mail. The user confirms two people really share a name.
        for (const label of [nm, ...aliasesOf(aliases)]) {
          const clash = p.contacts.find((x) => (x.email ?? "").toLowerCase() !== em && matchesName(x, label));
          if (clash) throw new M365Error("CONTACT_CONFLICT", `"${label}" already belongs to ${clash.name} <${clash.email}>.`,
            { hint: "Ask the user. If two different people really share it, repeat with allow_same_name: true; otherwise forget the old contact first." });
        }
      }
      if (c) {
        c.name = nm;
        c.aliases = aliasesOf([...(c.aliases ?? []), ...aliasesOf(aliases)]);
        if (note !== undefined) c.note = note;
      } else {
        c = { name: nm, email: em, aliases: aliasesOf(aliases), added_at: now().toISOString(), source };
        if (note) c.note = String(note).slice(0, 200);
        p.contacts.push(c);
      }
      save(p);
      return c;
    },

    forgetContact(q) {
      const p = load();
      const q2 = String(q ?? "").trim();
      const keep = p.contacts.filter((c) => !(matchesName(c, q2) || (c.email ?? "").toLowerCase() === q2.toLowerCase()));
      const removed = p.contacts.length - keep.length;
      if (removed) { p.contacts = keep; save(p); }
      return { removed };
    },

    rememberChat({ name, chat_id, aliases, kind }) {
      const nm = String(name ?? "").trim();
      if (!nm) throw new M365Error("INVALID_ARGUMENT", "name is required");
      const id = String(chat_id ?? "").trim();
      if (!id) throw new M365Error("INVALID_ARGUMENT", "chat_id is required");
      const p = load();
      let c = p.chats.find((x) => x.chat_id === id);
      if (c) { c.name = nm; c.aliases = aliasesOf([...(c.aliases ?? []), ...aliasesOf(aliases)]); if (kind) c.kind = kind; }
      else { c = { name: nm, chat_id: id, aliases: aliasesOf(aliases), added_at: now().toISOString(), ...(kind ? { kind } : {}) }; p.chats.push(c); }
      save(p);
      return c;
    },

    forgetChat(q) {
      const p = load();
      const keep = p.chats.filter((c) => !(matchesName(c, q) || c.chat_id === String(q).trim()));
      const removed = p.chats.length - keep.length;
      if (removed) { p.chats = keep; save(p); }
      return { removed };
    },
  };
}
