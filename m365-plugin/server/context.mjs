// context.mjs - wires config, auth, Graph and the profile into one object the tools receive.
// `ctx.reload()` rebuilds it from the current settings (used after /m365:init saves a setup), so no restart is needed.
import { resolveConfig } from "./config.mjs";
import { createAuth } from "./auth.mjs";
import { createGraph } from "./graph.mjs";
import { createProfile } from "./profile.mjs";
import { createStaging } from "./staging.mjs";
import { activeTools } from "./tools/index.mjs";
import { M365Error } from "./util.mjs";
import { settingsPath } from "./config.mjs";
import { statSync } from "node:fs";

export function createContext(env = process.env, deps = {}) {
  const now = deps.now ?? (() => Date.now());
  const ctx = {};
  let tools = [];
  let byName = new Map();
  let stamp = null;
  const stampOf = () => { try { return statSync(settingsPath(ctx.cfg.home)).mtimeMs; } catch { return 0; } };

  const build = () => {
    const cfg = resolveConfig(env);
    const auth = createAuth(cfg, deps);
    const graph = createGraph(cfg, auth, deps);
    Object.assign(ctx, { cfg, auth, graph, profile: createProfile(cfg), staging: createStaging(cfg, { now }), now, reload: build });
    tools = activeTools(cfg);
    byName = new Map(tools.map((t) => [t.name, t]));
    stamp = stampOf();
  };
  build();

  return {
    ctx,
    get tools() { return tools; },
    listTools: () => tools.map(({ name, description, inputSchema }) => ({ name, description, inputSchema })),
    async callTool(name, args) {
      // the user may have run `cli.mjs setup` or edited settings.json since this process started: always act on current settings
      if (stampOf() !== stamp) build();
      const t = byName.get(name);
      if (!t) throw new M365Error("UNKNOWN_TOOL", `unknown tool: ${name}`);
      return t.handler(args ?? {}, ctx);
    },
  };
}
