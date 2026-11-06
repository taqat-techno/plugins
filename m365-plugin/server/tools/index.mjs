// Tool registry. A tool is exposed only if its module is enabled, and a 'write' tool is never exposed
// in read-only mode (phase 1 has no write tools; the filter is here so phase 2 inherits it).
import { tools as auth } from "./auth.mjs";
import { tools as mail } from "./mail.mjs";
import { tools as calendar } from "./calendar.mjs";
import { tools as teams } from "./teams.mjs";
import { tools as people } from "./people.mjs";
import { tools as profile } from "./profile.mjs";

export const ALL_TOOLS = [...auth, ...profile, ...mail, ...calendar, ...teams, ...people];

export function activeTools(cfg) {
  return ALL_TOOLS.filter((t) => {
    if (t.kind === "write" && cfg.readOnly) return false;
    if (t.module === "auth" || t.module === "profile") return true;
    return cfg.modules.includes(t.module);
  });
}
