// people tools: turn a name into a verified email address. The local profile is consulted first,
// then the organization directory and the user's frequent contacts. An address is never invented.
import { M365Error, clampLimit, normName, safeStr } from "../util.mjs";

const USER_SELECT = "id,displayName,mail,userPrincipalName,jobTitle,department";

function viaUser(u) {
  const email = (u.mail || u.userPrincipalName || "").toLowerCase();
  return { name: u.displayName ?? null, email: email || null, title: u.jobTitle ?? null, department: u.department ?? null, source: "directory" };
}
function viaPerson(p) {
  const email = (p.scoredEmailAddresses?.[0]?.address || p.userPrincipalName || "").toLowerCase();
  return { name: p.displayName ?? null, email: email || null, title: p.jobTitle ?? null, department: p.department ?? null, source: "people" };
}

/** Directory + relevance search; partial failures are reported, not fatal. */
export async function searchPeople(ctx, query, limit = 10) {
  const q = safeStr(query, "query", 100)?.replace(/["\\]/g, " ").trim();
  if (!q) throw new M365Error("INVALID_ARGUMENT", "query is required");
  const [people, users] = await Promise.allSettled([
    ctx.graph.get(`/me/people?$search=${encodeURIComponent(`"${q}"`)}&$top=${limit}`),
    ctx.graph.get(`/users?$search=${encodeURIComponent(`"displayName:${q}" OR "mail:${q}"`)}&$top=${limit}&$select=${USER_SELECT}`, { headers: { ConsistencyLevel: "eventual" } }),
  ]);
  const notes = [];
  const seen = new Map();
  const add = (c) => { if (c.email && !seen.has(c.email)) seen.set(c.email, c); else if (c.email) seen.set(c.email, { ...seen.get(c.email), title: seen.get(c.email).title ?? c.title, department: seen.get(c.email).department ?? c.department }); };
  if (people.status === "fulfilled") (people.value.value ?? []).map(viaPerson).forEach(add); else notes.push(`people search unavailable (${people.reason?.code ?? "error"})`);
  if (users.status === "fulfilled") (users.value.value ?? []).map(viaUser).forEach(add); else notes.push(`directory search unavailable (${users.reason?.code ?? "error"})`);
  if (people.status === "rejected" && users.status === "rejected") throw people.reason;
  return { candidates: [...seen.values()].slice(0, limit), notes };
}

export const tools = [
  {
    name: "people_find", kind: "read", module: "people",
    description: "Search the organization directory and the user's frequent contacts for people by name or email. Returns name, email, job title and department. Use people_resolve when you need one address to send to; use this to browse or disambiguate.",
    inputSchema: { type: "object", properties: {
      query: { type: "string", description: "Name or part of an email." }, limit: { type: "number", description: "1-20, default 10." } }, required: ["query"] },
    async handler(a, ctx) {
      const r = await searchPeople(ctx, a.query, clampLimit(a.limit, 10, 20));
      return { query: a.query, count: r.candidates.length, people: r.candidates, notes: r.notes };
    },
  },
  {
    name: "people_resolve", kind: "read", module: "people",
    description: "Turn a name (for example 'Mahmoud') into a verified email address. Checks the user's remembered contacts and aliases first, then the directory. Returns status 'resolved' (use the email), 'candidates' (several people match: ask which one) or 'not_found'. Never guess an address. After the user confirms a directory match, call profile_remember_contact so it resolves instantly next time.",
    inputSchema: { type: "object", properties: { name: { type: "string", description: "Name, alias or email." } }, required: ["name"] },
    async handler(a, ctx) {
      const name = safeStr(a.name, "name", 100)?.trim();
      if (!name) throw new M365Error("INVALID_ARGUMENT", "name is required");
      const mine = ctx.profile.findContacts(name);
      if (mine.matches.length === 1 && mine.exact) {
        const c = mine.matches[0];
        return { status: "resolved", source: "profile", name: c.name, email: c.email };
      }
      if (mine.matches.length > 1) {
        return { status: "candidates", source: "profile", candidates: mine.matches.map((c) => ({ name: c.name, email: c.email })), next_step: "Several remembered contacts match. Ask the user which one." };
      }
      if (mine.matches.length === 1) {
        const c = mine.matches[0];
        return { status: "candidates", source: "profile", candidates: [{ name: c.name, email: c.email }], next_step: "One remembered contact is a partial match. Confirm with the user before using it." };
      }
      const found = await searchPeople(ctx, name, 8);
      const n = normName(name);
      const strong = found.candidates.filter((c) => normName(c.name ?? "") === n || (c.email ?? "") === name.toLowerCase());
      if (strong.length === 1) return { status: "resolved", source: strong[0].source, name: strong[0].name, email: strong[0].email, next_step: "Confirm once, then call profile_remember_contact to remember it.", notes: found.notes };
      if (found.candidates.length === 0) return { status: "not_found", notes: found.notes, next_step: "Ask the user for the email address." };
      return { status: "candidates", source: "directory", candidates: found.candidates, notes: found.notes, next_step: "Ask the user which person is meant." };
    },
  },
];
