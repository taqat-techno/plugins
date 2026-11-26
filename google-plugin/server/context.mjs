// context.mjs - wires config, auth and the Google MCP client into one object the tools receive. Settings come from the
// environment at start; the client JSON file and the token cache are read on each use, so replacing either needs no
// restart.
import { resolveConfig } from "./config.mjs";
import { createAuth } from "./auth.mjs";
import { createRemote } from "./remote.mjs";
import { activeTools } from "./tools/index.mjs";
import { GoogleError } from "./util.mjs";
import { createWriteLimiter } from "./guards.mjs";

export function createContext(env = process.env, deps = {}) {
  const ctx = {};
  let tools = [];
  let byName = new Map();
  const build = () => {
    const cfg = resolveConfig(env);
    const auth = createAuth(cfg, deps);
    const remote = createRemote({ urls: cfg.mcpUrls, auth, fetch: deps.fetch ?? globalThis.fetch, timeoutMs: cfg.timeoutMs });
    const now = deps.now ?? (() => Date.now());
    Object.assign(ctx, { cfg, auth, remote, now, limiter: createWriteLimiter(now), fetch: deps.fetch ?? globalThis.fetch, ...(deps.lookup ? { lookup: deps.lookup } : {}), ...(deps.imageGet ? { imageGet: deps.imageGet } : {}), sleep: deps.sleep ?? ((ms) => new Promise((r) => setTimeout(r, ms))) });
    tools = activeTools(cfg);
    byName = new Map(tools.map((t) => [t.name, t]));
  };
  build();
  return {
    ctx,
    get tools() { return tools; },
    listTools: () => tools.map(({ name, description, inputSchema }) => ({ name, description, inputSchema })),
    /** session describes the caller (see server/tools/bridge.mjs): whether it can show Google's confirmation forms. */
    async callTool(name, args, session = {}) {
      const t = byName.get(name);
      if (!t) throw new GoogleError("UNKNOWN_TOOL", `unknown tool: ${String(name).slice(0, 80)}`);
      return t.handler(args ?? {}, ctx, session);
    },
  };
}
