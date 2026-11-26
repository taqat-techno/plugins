#!/usr/bin/env node
// Command line for the humans around the plugin (no agent needed). Reads the same settings as the server
// (GOOGLE_CLIENT_SECRET_FILE, GOOGLE_PLUGIN_HOME, GOOGLE_READONLY, GOOGLE_MODULES ...).
//   node server/cli.mjs sign-in              sign in once in a browser on this computer; prints account and scopes
//   node server/cli.mjs status [--offline]   who is signed in; refreshes the token live unless --offline
//   node server/cli.mjs sign-out             delete the saved sign-in on this computer
//   node server/cli.mjs grant [--fresh] [tool ...]  answer Google's confirmation forms yourself, once per read tool;
//                                            --fresh looks past items already allowed (per email / owner)
//   node server/cli.mjs schema-check [--update]   compare Google's live tool list with the recorded snapshot
//   node server/cli.mjs identity <messageId>  which configured identity one message was sent to (headers only, no
//                                            body); Google's form, if any, is shown here for you to answer
// Exit codes: 0 = OK; 3 = not signed in, sign-in failed, a live check failed, a grant step failed or the schema drifted
// for an exposed tool (a scheduled check can alert on it); 1 = unexpected error; 2 = usage.
// Output never contains a token or the client secret; grant never prints the data its test calls return.
import { createInterface } from "node:readline/promises";
import { createContext } from "./context.mjs";
import { runGrant, askInTerminal } from "./grant.mjs";
import { schemaCheck } from "./schema.mjs";

const [cmd = "status", ...rest] = process.argv.slice(2);
const out = (o) => process.stdout.write(JSON.stringify(o, null, 2) + "\n");
const USAGE = "usage: cli.mjs sign-in | status [--offline] | sign-out | grant [--fresh] [tool ...] | schema-check [--update] | identity <messageId>\n";

try {
  const c = createContext();
  const { ctx } = c;
  if (cmd === "status") {
    const s = await ctx.auth.status({ verify: !rest.includes("--offline") });
    out(s);
    process.exit(s.signed_in && s.verified !== false ? 0 : 3);
  } else if (cmd === "sign-out") {
    out(ctx.auth.signOut());
  } else if (cmd === "sign-in") {
    const started = await ctx.auth.startSignIn();
    process.stdout.write(`${started.message}\n`);
    if (started.url && !started.message.includes(started.url)) process.stdout.write(`If no browser opened, open this address on this computer: ${started.url}\n`);
    for (;;) {
      await new Promise((r) => setTimeout(r, 1000));
      const s = await ctx.auth.status({ verify: false });
      if (s.sign_in?.state === "failed") { out(s); process.exit(3); }
      if (s.signed_in && s.sign_in?.state === "done") {
        out({ signed_in: true, account: s.account, scopes_granted: s.scopes_granted, scopes_missing: s.scopes_missing, modules: s.modules, token_obtained_at: s.token_obtained_at, home: ctx.cfg.home });
        process.exit(0);
      }
    }
  } else if (cmd === "grant") {
    const available = c.tools.filter((t) => t.kind === "read").map((t) => t.name);
    const rl = createInterface({ input: process.stdin, output: process.stdout });
    const print = (s) => process.stdout.write(`${s}\n`);
    print("Google may ask you to allow each tool. Your answer is sent as you type it; nothing is answered for you.");
    print("Only whether Google asked and what you chose is shown here, never the data the test calls read.");
    let result;
    try {
      result = await runGrant({ ctx, callTool: c.callTool, available, requested: rest.filter((a) => !a.startsWith("-")), fresh: rest.includes("--fresh"), prompt: (q) => rl.question(q), print });
    } finally { rl.close(); }
    print("\nSummary:");
    for (const s of result.steps) {
      const ans = s.answers.map((a) => (typeof a.answer === "string" ? a.answer : Object.values(a.answer).join("/"))).join(", ");
      print(`  ${s.tool.padEnd(30)} ${s.result.padEnd(8)} asked=${s.asked ? "yes" : "no "}${ans ? ` answer=${ans}` : ""}${s.reason ? ` (${s.reason})` : ""}${s.error ? ` (${s.error.code})` : ""}`);
    }
    process.exit(result.steps.some((s) => s.result === "error") ? 3 : 0);
  } else if (cmd === "identity") {
    if (!rest[0]) { process.stderr.write(USAGE); process.exit(2); }
    const rl = createInterface({ input: process.stdin, output: process.stdout });
    const print = (s) => process.stdout.write(`${s}\n`);
    let asked = false;
    try {
      const session = { canElicit: true, elicit: async (req) => { asked = true; return askInTerminal(req, { prompt: (q) => rl.question(q), print }); } };
      const r = await c.callTool("gmail_message_identity", { messageId: rest[0] }, session);
      out({ google_asked: asked, ...r });
    } finally { rl.close(); }
  } else if (cmd === "schema-check") {
    const report = await schemaCheck(ctx, { update: rest.includes("--update") });
    out(report);
    process.exit(Object.values(report).some((r) => r.exposed_affected.length || r.added.length) ? 3 : 0);
  } else {
    process.stderr.write(USAGE);
    process.exit(2);
  }
} catch (e) {
  out({ ok: false, error: { code: e.code ?? "ERROR", message: e.message, ...(e.hint ? { hint: e.hint } : {}) } });
  process.exit(e.code ? 3 : 1);
}
