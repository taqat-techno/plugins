#!/usr/bin/env node
// Command line for the humans around the plugin (no agent needed):
//   node server/cli.mjs sign-in [--device-code]   sign in once (a bot's first login; an admin test)
//   node server/cli.mjs status                    who is signed in
//   node server/cli.mjs events --since now|<cursor|ISO> [--types mail,chat-mention]   what concerns the user (a poll; keep the cursor)
//   node server/cli.mjs sign-out
// Reads the same settings as the server (M365_CLIENT_ID, M365_TENANT, M365_HOME ...).
import { createContext } from "./context.mjs";
import { collectEvents } from "./events.mjs";

const [cmd = "status", ...rest] = process.argv.slice(2);
const { ctx } = createContext();
const out = (o) => process.stdout.write(JSON.stringify(o, null, 2) + "\n");

try {
  if (cmd === "status") out(ctx.auth.status());
  else if (cmd === "sign-out") out(ctx.auth.signOut());
  else if (cmd === "events") {
    const get = (f) => { const i = rest.indexOf(f); return i >= 0 ? rest[i + 1] : undefined; };
    out(await collectEvents(ctx, { since: get("--since") ?? "now", types: get("--types")?.split(",").filter(Boolean) }));
  }
  else if (cmd === "sign-in") {
    const started = await ctx.auth.startSignIn({ mode: rest.includes("--device-code") ? "device-code" : undefined });
    process.stdout.write(`${started.message}\n`);
    for (;;) {
      await new Promise((r) => setTimeout(r, 2000));
      const s = ctx.auth.status();
      if (s.sign_in?.state === "failed") { out(s); process.exit(1); }
      if (s.signed_in && s.sign_in?.state === "done") { out(s); break; }
    }
    process.exit(0);
  } else { process.stderr.write("usage: cli.mjs sign-in [--device-code] | status | sign-out | events --since now|<cursor>\n"); process.exit(2); }
} catch (e) {
  out({ error: e.code ?? "ERROR", message: e.message, hint: e.hint });
  process.exit(1);
}
