// me.mjs - fill the profile's identity, time zone and working hours from the account and from Outlook's own settings
// (GET /me/mailboxSettings). Called by profile_refresh_me and automatically on the first tool call after sign-in.
// A value the user set with profile_set is never overwritten.
import { isValidZone, systemZone } from "./util.mjs";

// Windows time zone names Graph returns most often, mapped to IANA. Anything else is resolved from the city names
// in Outlook's own zone list ("(UTC+02:00) Cairo" -> Africa/Cairo), then falls back to this computer's zone.
const WINDOWS_TO_IANA = {
  "UTC": "Etc/UTC", "GMT Standard Time": "Europe/London", "Greenwich Standard Time": "Atlantic/Reykjavik",
  "W. Europe Standard Time": "Europe/Berlin", "Romance Standard Time": "Europe/Paris", "Central Europe Standard Time": "Europe/Budapest",
  "Central European Standard Time": "Europe/Warsaw", "E. Europe Standard Time": "Europe/Chisinau", "FLE Standard Time": "Europe/Kiev",
  "GTB Standard Time": "Europe/Bucharest", "Turkey Standard Time": "Europe/Istanbul", "Russian Standard Time": "Europe/Moscow",
  "Egypt Standard Time": "Africa/Cairo", "South Africa Standard Time": "Africa/Johannesburg", "W. Central Africa Standard Time": "Africa/Lagos",
  "Morocco Standard Time": "Africa/Casablanca", "Libya Standard Time": "Africa/Tripoli", "Sudan Standard Time": "Africa/Khartoum",
  "Arab Standard Time": "Asia/Riyadh", "Arabian Standard Time": "Asia/Dubai", "Arabic Standard Time": "Asia/Baghdad",
  "Jordan Standard Time": "Asia/Amman", "Syria Standard Time": "Asia/Damascus", "Middle East Standard Time": "Asia/Beirut",
  "Israel Standard Time": "Asia/Jerusalem", "Iran Standard Time": "Asia/Tehran", "Pakistan Standard Time": "Asia/Karachi",
  "India Standard Time": "Asia/Kolkata", "Bangladesh Standard Time": "Asia/Dhaka", "SE Asia Standard Time": "Asia/Bangkok",
  "China Standard Time": "Asia/Shanghai", "Singapore Standard Time": "Asia/Singapore", "Tokyo Standard Time": "Asia/Tokyo",
  "Korea Standard Time": "Asia/Seoul", "AUS Eastern Standard Time": "Australia/Sydney", "New Zealand Standard Time": "Pacific/Auckland",
  "Eastern Standard Time": "America/New_York", "Central Standard Time": "America/Chicago", "Mountain Standard Time": "America/Denver",
  "Pacific Standard Time": "America/Los_Angeles", "US Mountain Standard Time": "America/Phoenix", "Alaskan Standard Time": "America/Anchorage",
  "Hawaiian Standard Time": "Pacific/Honolulu", "Atlantic Standard Time": "America/Halifax", "E. South America Standard Time": "America/Sao_Paulo",
  "Argentina Standard Time": "America/Buenos_Aires", "Canada Central Standard Time": "America/Regina", "Mexico Standard Time": "America/Mexico_City",
};
const REGIONS = ["Africa", "Asia", "Europe", "America", "Australia", "Pacific", "Atlantic", "Indian"];

/** An Outlook time zone name (Windows or IANA) to an IANA name, or null. */
export async function toIana(ctx, name) {
  const n = String(name ?? "").trim();
  if (!n) return null;
  if (n.includes("/") && isValidZone(n)) return n;
  if (WINDOWS_TO_IANA[n] && isValidZone(WINDOWS_TO_IANA[n])) return WINDOWS_TO_IANA[n];
  try {
    const j = await ctx.graph.get("/me/outlook/supportedTimeZones(TimeZoneStandard=microsoft.graph.timeZoneStandard'Windows')");
    const hit = (j.value ?? []).find((z) => z.alias === n);
    const cities = String(hit?.displayName ?? "").replace(/^\([^)]*\)\s*/, "").split(/\s*,\s*/).map((c) => c.trim().replace(/\s+/g, "_")).filter(Boolean);
    for (const city of cities) for (const r of REGIONS) if (isValidZone(`${r}/${city}`)) return `${r}/${city}`;
  } catch { /* no list: fall through */ }
  return null;
}

const hhmm = (t) => (/^\d\d:\d\d/.test(String(t ?? "")) ? String(t).slice(0, 5) : null);

/**
 * Fill identity, time zone and working hours. Fields the user set themselves are kept.
 * Returns { me, defaults, filled: [...], kept: [...], notes: [...] }.
 */
export async function fillFromAccount(ctx) {
  const notes = [];
  const me = await ctx.graph.get("/me?$select=id,displayName,mail,userPrincipalName,preferredLanguage");
  let mbx = null;
  try { mbx = await ctx.graph.get("/me/mailboxSettings?$select=timeZone,workingHours,language"); }
  catch (e) { notes.push(`Outlook settings could not be read (${e.code ?? "error"}); used this computer's time zone and the default working hours. Ask the user to confirm them.`); }

  const computer = systemZone();
  const values = {
    name: me.displayName || null,
    email: (me.mail || me.userPrincipalName || "").toLowerCase() || null,
    id: me.id ?? null,
    language: mbx?.language?.locale || me.preferredLanguage || null,
  };
  const sources = { name: "account", email: "account", id: "account", language: "account" };

  // Time zone: Outlook keeps two (the display zone and the working-hours zone). They usually agree; when they do not,
  // the one that matches this computer wins, and the user is told so they can correct it.
  const display = mbx ? await toIana(ctx, mbx.timeZone) : null;
  const working = mbx ? await toIana(ctx, mbx.workingHours?.timeZone?.name) : null;
  if (display && working && display !== working) {
    values.timezone = [display, working].includes(computer) ? computer : working;
    notes.push(`Outlook's display time zone is ${display} but its working hours are set in ${working}; using ${values.timezone}. Confirm with the user (profile_set timezone).`);
    sources.timezone = "outlook";
  } else if (display || working) { values.timezone = display || working; sources.timezone = "outlook"; }
  else { values.timezone = computer; sources.timezone = "computer"; if (mbx) notes.push(`Outlook's time zone "${mbx.timeZone}" could not be mapped; used this computer's zone ${computer}.`); }

  const wh = mbx?.workingHours;
  if (wh && Array.isArray(wh.daysOfWeek) && wh.daysOfWeek.length && hhmm(wh.startTime) && hhmm(wh.endTime)) {
    values.working_hours = { days: wh.daysOfWeek.map((d) => String(d).toLowerCase()), start: hhmm(wh.startTime), end: hhmm(wh.endTime) };
    sources.working_hours = "outlook";
  }
  const r = ctx.profile.fillAuto(values, sources);
  return { ...r, notes };
}
