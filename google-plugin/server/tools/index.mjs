// Tool registry. Every tool declares its class (kind): read | local | write | confirm. A write or confirm tool is never
// exposed in read-only mode. data/tools.json holds the classification; a test keeps the registry in step with it.
//   auth tools   (local)  server/tools/auth.mjs: on unless named in the deny list
//   bridged tools         server/tools/bridge.mjs: Google's own MCP tools, filtered by module, read-only mode and the
//                         optional allow / deny lists
//   identity tools        server/tools/identity.mjs: the plugin's own (gmail module), filtered the same way
import { tools as auth } from "./auth.mjs";
import { bridgedTools } from "./bridge.mjs";
import { tools as identity } from "./identity.mjs";

export const ALL_TOOLS = [...auth, ...bridgedTools(), ...identity];

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
    if (!cfg.modules.includes(t.module)) return false;
    if (cfg.readOnly && (t.kind === "write" || t.kind === "confirm")) return false;
    if (cfg.toolsAllow.length && !cfg.toolsAllow.includes(t.name)) return false;
    return true;
  });
}
