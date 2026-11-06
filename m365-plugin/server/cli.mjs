#!/usr/bin/env node
// Command line for the humans around the plugin (no agent needed):
//   node server/cli.mjs sign-in [--interactive | --device-code]   sign in once (a bot's first login; an admin test).
//        --interactive: browser only (prints the address too, in case no browser opens)
//   node server/cli.mjs status                    who is signed in
//   node server/cli.mjs events --since now|<cursor|ISO> [--types mail,chat-mention]   what concerns the user (a poll; keep the cursor)
//   node server/cli.mjs setup [--client-id <id>] [--tenant <id>] [--scope-mode app] [--token-file <path>] [--secret-file <path>] [--redirect-uri <url>]
//        saves ids and PATHS (never a token or secret) to settings.json; the only way besides the plugin settings to point
//        the plugin at another tool's sign-in. Run it yourself: an agent cannot.
//   node server/cli.mjs sign-out
// Reads the same settings as the server (M365_CLIENT_ID, M365_TENANT, M365_HOME ...).
import { createContext } from "./context.mjs";
import { collectEvents } from "./events.mjs";
import { saveSettings } from "./setup.mjs";

const [cmd = "status", ...rest] = process.argv.slice(2);
const { ctx } = createContext();
const out = (o) => process.stdout.write(JSON.stringify(o, null, 2) + "\n");

try {
  if (cmd === "status") out(ctx.auth.status());
  else if (cmd === "sign-out") out(ctx.auth.signOut());
  else if (cmd === "setup") {
    const get = (f) => { const i = rest.indexOf(f); return i >= 0 ? rest[i + 1] : undefined; };
    const r = saveSettings(ctx.cfg, { client_id: get("--client-id"), tenant: get("--tenant"), scope_mode: get("--scope-mode"), refresh_token_file: get("--token-file"), client_secret_file: get("--secret-file"), redirect_uri: get("--redirect-uri") }, { viaTool: false });
    out({ ...r, note: "Saved. Restart your agent (or run m365_auth_status) to pick it up." });
  }
  else if (cmd === "events") {
    const get = (f) => { const i = rest.indexOf(f); return i >= 0 ? rest[i + 1] : undefined; };
    out(await collectEvents(ctx, { since: get("--since") ?? "now", types: get("--types")?.split(",").filter(Boolean) }));
  }
  else if (cmd === "sign-in") {
    const mode = rest.includes("--device-code") ? "device-code" : rest.includes("--interactive") ? "interactive" : undefined;
    const started = await ctx.auth.startSignIn({ mode });
    process.stdout.write(`${started.message}\n`);
    if (started.mode === "interactive" && started.url && !started.message.includes(started.url)) process.stdout.write(`If no browser opened, open this address: ${started.url}\n`);
    for (;;) {
      await new Promise((r) => setTimeout(r, 2000));
      const s = ctx.auth.status();
      if (s.sign_in?.state === "failed") { out(s); process.exit(1); }
      if (s.signed_in && s.sign_in?.state === "done") { out(s); break; }
    }
    process.exit(0);
  } else { process.stderr.write("usage: cli.mjs sign-in [--interactive|--device-code] | status | sign-out | setup ... | events --since now|<cursor>\n"); process.exit(2); }
} catch (e) {
  out({ error: e.code ?? "ERROR", message: e.message, hint: e.hint });
  process.exit(1);
}
