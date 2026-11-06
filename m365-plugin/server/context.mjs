// context.mjs - wires config, auth, Graph and the profile into one object the tools receive.
import { resolveConfig } from "./config.mjs";
import { createAuth } from "./auth.mjs";
import { createGraph } from "./graph.mjs";
import { createProfile } from "./profile.mjs";
import { activeTools } from "./tools/index.mjs";
import { M365Error } from "./util.mjs";

export function createContext(env = process.env, deps = {}) {
  const cfg = resolveConfig(env);
  const auth = createAuth(cfg, deps);
  const graph = createGraph(cfg, auth, deps);
  const profile = createProfile(cfg);
  const ctx = { cfg, auth, graph, profile, now: deps.now ?? (() => Date.now()) };
  const tools = activeTools(cfg);
  const byName = new Map(tools.map((t) => [t.name, t]));
  return {
    ctx,
    tools,
    listTools: () => tools.map(({ name, description, inputSchema }) => ({ name, description, inputSchema })),
    async callTool(name, args) {
      const t = byName.get(name);
      if (!t) throw new M365Error("UNKNOWN_TOOL", `unknown tool: ${name}`);
      return t.handler(args ?? {}, ctx);
    },
  };
}
