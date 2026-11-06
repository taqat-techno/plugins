// profile tools: the user's local memory (contacts, chats, defaults). These change only a local
// JSON file, never Microsoft 365, so they are 'local' tools: allowed in read-only mode, no confirmation.
import { M365Error, clampLimit, systemZone } from "../util.mjs";

export const tools = [
  {
    name: "profile_get", kind: "local", module: "profile",
    description: "Show the user's local profile: identity (name, email, time zone, language), defaults (meeting length, working hours), remembered contacts with aliases, and remembered Teams chats. Holds no tokens. Read it before asking the user for an address you may already know.",
    inputSchema: { type: "object", properties: {} },
    async handler(_a, ctx) { return { path: ctx.profile.path, profile: ctx.profile.load() }; },
  },
  {
    name: "profile_refresh_me", kind: "local", module: "profile",
    description: "Fill the profile's identity from the signed-in account (name, email, id, preferred language) and set the time zone to this computer's zone if none is saved. Run once after sign-in; safe to repeat. Tell the user the time zone it chose so they can correct it with profile_set.",
    inputSchema: { type: "object", properties: {} },
    async handler(_a, ctx) {
      const me = await ctx.graph.get("/me?$select=id,displayName,mail,userPrincipalName,preferredLanguage");
      const p = ctx.profile.load();
      const fields = { name: me.displayName ?? p.me.name, email: (me.mail || me.userPrincipalName || p.me.email || "").toLowerCase() || undefined };
      if (me.preferredLanguage) fields.language = me.preferredLanguage;
      if (!p.me.timezone) fields.timezone = systemZone();
      const saved = ctx.profile.set(fields);
      const withId = { ...saved }; withId.me.id = me.id; ctx.profile.save(withId);
      return { me: withId.me, note: p.me.timezone ? "Time zone kept." : `Time zone set to ${fields.timezone} (this computer's zone). Correct it with profile_set if wrong.` };
    },
  },
  {
    name: "profile_set", kind: "local", module: "profile",
    description: "Change profile fields: name, email, timezone (IANA, e.g. Africa/Cairo), language, meeting_minutes (default meeting length), working_days (e.g. sunday,monday,tuesday,wednesday,thursday) and work_start / work_end (HH:MM). Only the fields you pass change.",
    inputSchema: { type: "object", properties: {
      name: { type: "string" }, email: { type: "string" }, timezone: { type: "string" }, language: { type: "string" },
      meeting_minutes: { type: "number" }, working_days: { type: "array", items: { type: "string" } },
      work_start: { type: "string", description: "HH:MM" }, work_end: { type: "string", description: "HH:MM" } } },
    async handler(a, ctx) { const p = ctx.profile.set(a); return { me: p.me, defaults: p.defaults }; },
  },
  {
    name: "profile_remember_contact", kind: "local", module: "profile",
    description: "Remember a person so a name resolves to their email next time: 'Mahmoud' -> mahmoud@example.com. Give the full name, the verified email and optional aliases (nicknames, Arabic spelling). Call it after the user confirms who someone is.",
    inputSchema: { type: "object", properties: {
      name: { type: "string" }, email: { type: "string" }, aliases: { type: "array", items: { type: "string" } }, note: { type: "string" } }, required: ["name", "email"] },
    async handler(a, ctx) { return { saved: ctx.profile.rememberContact(a) }; },
  },
  {
    name: "profile_forget_contact", kind: "local", module: "profile",
    description: "Remove a remembered contact by name, alias or email.",
    inputSchema: { type: "object", properties: { who: { type: "string" } }, required: ["who"] },
    async handler(a, ctx) { return ctx.profile.forgetContact(a.who); },
  },
  {
    name: "profile_remember_chat", kind: "local", module: "profile",
    description: "Remember a Teams chat under a friendly name (and aliases) so 'the project group' finds it later. Get chat_id from teams_find_chat.",
    inputSchema: { type: "object", properties: {
      name: { type: "string" }, chat_id: { type: "string" }, aliases: { type: "array", items: { type: "string" } }, kind: { type: "string" } }, required: ["name", "chat_id"] },
    async handler(a, ctx) { return { saved: ctx.profile.rememberChat(a) }; },
  },
  {
    name: "profile_forget_chat", kind: "local", module: "profile",
    description: "Remove a remembered Teams chat by name, alias or chat_id.",
    inputSchema: { type: "object", properties: { who: { type: "string" } }, required: ["who"] },
    async handler(a, ctx) { return ctx.profile.forgetChat(a.who); },
  },
  {
    name: "profile_suggest_contacts", kind: "read", module: "profile",
    description: "Suggest people worth remembering, from the user's frequent contacts and the people they most recently emailed. Returns candidates not yet remembered, with name and email. Show them to the user and call profile_remember_contact only for the ones they keep.",
    inputSchema: { type: "object", properties: { limit: { type: "number", description: "1-30, default 15." } } },
    async handler(a, ctx) {
      const n = clampLimit(a.limit, 15, 30);
      const known = new Set(ctx.profile.load().contacts.map((c) => (c.email ?? "").toLowerCase()));
      const me = (ctx.profile.load().me.email ?? "").toLowerCase();
      const counts = new Map();
      const notes = [];
      const bump = (name, email, w) => {
        const e = String(email ?? "").toLowerCase();
        if (!e || e === me || known.has(e)) return;
        const c = counts.get(e) ?? { name: name || null, email: e, score: 0 };
        c.score += w; if (!c.name && name) c.name = name; counts.set(e, c);
      };
      const [people, sent] = await Promise.allSettled([
        ctx.graph.get("/me/people?$top=30"),
        ctx.graph.get("/me/mailFolders/sentitems/messages?$top=50&$select=toRecipients&$orderby=" + encodeURIComponent("sentDateTime desc")),
      ]);
      if (people.status === "fulfilled") (people.value.value ?? []).forEach((p, i) => bump(p.displayName, p.scoredEmailAddresses?.[0]?.address || p.userPrincipalName, 30 - i));
      else notes.push(`frequent contacts unavailable (${people.reason?.code ?? "error"})`);
      if (sent.status === "fulfilled") (sent.value.value ?? []).forEach((m) => (m.toRecipients ?? []).forEach((r) => bump(r.emailAddress?.name, r.emailAddress?.address, 1)));
      else notes.push(`sent mail unavailable (${sent.reason?.code ?? "error"})`);
      if (people.status === "rejected" && sent.status === "rejected") throw new M365Error("ACCESS_NEEDED", "Could not read frequent contacts or sent mail.", { hint: "Sign in first (m365_sign_in), or the app lacks People.Read / Mail.Read." });
      return { candidates: [...counts.values()].sort((x, y) => y.score - x.score).slice(0, n).map(({ name, email }) => ({ name, email })), notes };
    },
  },
];
