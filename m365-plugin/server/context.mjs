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
import { fillFromAccount } from "./me.mjs";

// Sign-in and status tools stay free of Microsoft calls (a status poll must not touch the account), and the profile
// tools fill or set the profile themselves: no automatic profile fill before any of them.
const NO_AUTOFILL = new Set(["m365_sign_in", "m365_sign_out", "m365_auth_status", "m365_setup_save", "m365_access_request", "profile_refresh_me", "profile_set"]);

export function createContext(env = process.env, deps = {}) {
  const now = deps.now ?? (() => Date.now());
  const ctx = {};
  let tools = [];
  let byName = new Map();
  let stamp = null;
  let autofillTried = false;
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
      // First call after sign-in with an empty profile: fill identity, time zone and working hours from Outlook once,
      // so free-slot search and dates use the user's real week and zone. A failure never blocks the tool itself.
      if (!autofillTried && !NO_AUTOFILL.has(name) && !ctx.profile.load().me.email) {
        autofillTried = true;
        try { if (ctx.auth.status().signed_in) await fillFromAccount(ctx); } catch { /* the tool still runs; profile_refresh_me reports why */ }
      }
      return t.handler(args ?? {}, ctx);
    },
  };
}
