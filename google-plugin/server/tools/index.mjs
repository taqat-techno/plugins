// Tool registry. Every tool declares its class (kind): read | local | write | confirm. A write or confirm tool is never
// exposed in read-only mode. data/tools.json holds the classification; a test keeps the registry in step with it.
//   auth tools   (local)  server/tools/auth.mjs: on unless named in the deny list
//   bridged tools         server/tools/bridge.mjs: Google's own MCP tools, filtered by module, read-only mode and the
//                         optional allow / deny lists
//   identity tools        server/tools/identity.mjs: the plugin's own (gmail module), filtered the same way
//   file tools            server/tools/files.mjs: save an attachment or a Drive file into GOOGLE_DOWNLOAD_DIR
//   REST tools            server/tools/rest.mjs: only with GOOGLE_REST_FALLBACK=1 (never listed or callable otherwise)
//   Gmail admin tools     server/tools/gmail_admin.mjs: REST too, plus GOOGLE_GMAIL_SETTINGS / GOOGLE_FULL_MAILBOX
//   Gmail read tools      server/tools/gmail_read.mjs: REST twins of the Gmail MCP reads (own quota)
import { tools as auth } from "./auth.mjs";
import { bridgedTools } from "./bridge.mjs";
import { tools as identity } from "./identity.mjs";
import { tools as files } from "./files.mjs";
import { tools as rest } from "./rest.mjs";
import { tools as gmailAdmin } from "./gmail_admin.mjs";
import { tools as gmailRead } from "./gmail_read.mjs";

export const ALL_TOOLS = [...auth, ...bridgedTools(), ...identity, ...files, ...rest, ...gmailAdmin, ...gmailRead];

export function activeTools(cfg) {
  return filterTools(ALL_TOOLS, cfg);
}

/**
 * The tools a configuration exposes. The deny list applies to every tool, the sign-in tools included (deny means deny).
 * The allow list narrows only the module tools: the sign-in tools stay unless denied, so a host that allows a few Google
 * tools can still report and fix the sign-in.
 */
export function filterTools(list, cfg) {
  return list.filter((t) => {
    if (cfg.toolsDeny.includes(t.name)) return false;
    if (t.module === "auth") return true;
    if (t.rest && !cfg.restFallback) return false;
    // Opt-in Gmail options: settings tools need GOOGLE_GMAIL_SETTINGS, permanent delete needs GOOGLE_FULL_MAILBOX.
    if (t.needs === "settings" && !cfg.gmailSettings) return false;
    if (t.needs === "full" && !cfg.fullMailbox) return false;
    if (!cfg.modules.includes(t.module)) return false;
    if (cfg.readOnly && (t.kind === "write" || t.kind === "confirm")) return false;
    if (cfg.toolsAllow.length && !cfg.toolsAllow.includes(t.name)) return false;
    return true;
  });
}
