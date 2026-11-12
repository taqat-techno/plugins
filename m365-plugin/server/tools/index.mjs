// Tool registry. A tool is exposed only if its module is enabled, and a 'write' tool is never exposed
// in read-only mode.
import { tools as auth } from "./auth.mjs";
import { tools as mail } from "./mail.mjs";
import { tools as calendar } from "./calendar.mjs";
import { tools as teams } from "./teams.mjs";
import { tools as people } from "./people.mjs";
import { tools as profile } from "./profile.mjs";
import { tools as mailWrite } from "./mail_write.mjs";
import { tools as calendarWrite } from "./calendar_write.mjs";
import { tools as teamsWrite } from "./teams_write.mjs";
import { tools as files } from "./files.mjs";
import { tools as events } from "./events.mjs";
import { tools as folders } from "./mail_folders.mjs";
import { tools as meetings } from "./meetings.mjs";
import { tools as save } from "./save.mjs";
import { tools as drive } from "./drive.mjs";

export const ALL_TOOLS = [...auth, ...profile, ...mail, ...mailWrite, ...calendar, ...calendarWrite, ...teams, ...teamsWrite, ...people, ...files, ...events, ...folders, ...meetings, ...save, ...drive];

export function activeTools(cfg) {
  return ALL_TOOLS.filter((t) => {
    if (t.kind === "write" && cfg.readOnly) return false;
    if (t.module === "auth" || t.module === "profile" || t.module === "events") return true;
    return cfg.modules.includes(t.module);
  });
}
