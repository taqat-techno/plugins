// grant.mjs - lets the HUMAN answer Google's confirmation forms once per tool, in their own terminal.
//
// Google's MCP servers may ask the human to allow a read ("Allow once", "Always allow this tool", ...). The plugin never
// answers that itself. `node server/cli.mjs grant [tool ...]` calls each read tool once on a harmless target (the first
// thread, draft, event or file it finds; METADATA_ONLY where Google offers it), shows Google's form exactly as sent and
// passes back only the choice the human types. It prints whether Google asked and what was chosen; it never prints the
// data the calls return. With no tool names it covers every enabled read tool.
import { GoogleError } from "./util.mjs";

const pad = (n) => String(n).padStart(2, "0");
/** Local time with no offset, as Google's Calendar tools ask for. */
const localIso = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}:00`;

/**
 * One harmless test call per read tool. needs = values found by earlier calls; yields = values this call finds.
 * The order matters: a tool that yields a value comes before the tools that need it.
 */
export const GRANT_PLAN = {
  gmail_search_threads: { args: () => ({ pageSize: 1, view: "THREAD_VIEW_METADATA_ONLY" }), yields: (d) => ({ threadId: d?.threads?.[0]?.id, messageId: d?.threads?.[0]?.messages?.[0]?.id }) },
  gmail_list_labels: { args: () => ({}) },
  gmail_list_drafts: { args: () => ({ pageSize: 1 }), yields: (d) => ({ draftId: d?.drafts?.[0]?.id }) },
  gmail_get_thread: { needs: ["threadId"], args: (f) => ({ threadId: f.threadId, messageFormat: "METADATA_ONLY" }), yields: (d) => ({ messageId: d?.messages?.[0]?.id }) },
  gmail_get_message: { needs: ["messageId"], args: (f) => ({ messageId: f.messageId, messageFormat: "METADATA_ONLY" }) },
  gmail_get_draft: { needs: ["draftId"], args: (f) => ({ draftId: f.draftId, messageFormat: "METADATA_ONLY" }) },
  calendar_list_calendars: { args: () => ({ pageSize: 1 }) },
  calendar_list_events: { args: () => ({ pageSize: 1 }), yields: (d) => ({ eventId: d?.events?.[0]?.id }) },
  calendar_get_event: { needs: ["eventId"], args: (f) => ({ eventId: f.eventId }) },
  calendar_search_events: { args: () => ({ query: "meeting", pageSize: 1 }) },
  calendar_suggest_time: {
    needs: ["account"],
    args: (f, now) => {
      const start = new Date(now); start.setDate(start.getDate() + 1); start.setHours(9, 0, 0, 0);
      const end = new Date(start); end.setHours(17);
      return { attendeeEmails: [f.account], startTime: localIso(start), endTime: localIso(end) };
    },
  },
  drive_list_recent_files: { args: () => ({ pageSize: 1, excludeContentSnippets: true }), yields: (d) => ({ fileId: d?.files?.[0]?.id }) },
  drive_search_files: { args: () => ({ pageSize: 1, excludeContentSnippets: true }) },
  drive_get_file_metadata: { needs: ["fileId"], args: (f) => ({ fileId: f.fileId, excludeContentSnippets: true }) },
  drive_get_file_permissions: { needs: ["fileId"], args: (f) => ({ fileId: f.fileId }) },
  drive_read_file_content: { needs: ["fileId"], args: (f) => ({ fileId: f.fileId }) },
  drive_download_file_content: { needs: ["fileId"], args: (f) => ({ fileId: f.fileId }) },
};

/**
 * `grant --fresh`: Google's per-item answers ("Always allow for this email / owner") mean the first thread or file is
 * often already allowed, so Google no longer asks there. --fresh looks further: the list tools read a larger page, and
 * the per-item tools try the items found one by one (up to FRESH_TRIES) until Google asks. Data read on the way stays in
 * memory and is never printed, as in a normal run.
 */
export const FRESH_TRIES = 25;
const ids = (list, pick = (x) => x?.id) => [...new Set((list ?? []).map(pick).filter(Boolean))];
export const FRESH_PLAN = {
  gmail_search_threads: { args: () => ({ pageSize: FRESH_TRIES, view: "THREAD_VIEW_METADATA_ONLY" }), yields: (d) => ({ threadIds: ids(d?.threads), messageIds: ids(d?.threads, (t) => t?.messages?.[0]?.id) }) },
  gmail_get_thread: { from: "threadIds", args: (id) => ({ threadId: id, messageFormat: "METADATA_ONLY" }) },
  gmail_get_message: { from: "messageIds", args: (id) => ({ messageId: id, messageFormat: "METADATA_ONLY" }) },
  drive_list_recent_files: { args: () => ({ pageSize: FRESH_TRIES, excludeContentSnippets: true }), yields: (d) => ({ fileIds: ids(d?.files) }) },
  drive_get_file_metadata: { from: "fileIds", args: (id) => ({ fileId: id, excludeContentSnippets: true }) },
  drive_get_file_permissions: { from: "fileIds", args: (id) => ({ fileId: id }) },
  drive_read_file_content: { from: "fileIds", args: (id) => ({ fileId: id }) },
};

/** Which plan step finds each value. */
const PRODUCER = {
  threadId: "gmail_search_threads", messageId: "gmail_search_threads", draftId: "gmail_list_drafts", eventId: "calendar_list_events", fileId: "drive_list_recent_files",
  threadIds: "gmail_search_threads", messageIds: "gmail_search_threads", fileIds: "drive_list_recent_files",
};

/** The ordered steps for the requested tools, with the helper steps they need added (marked helper). */
export function grantSteps(requested, available, { fresh = false } = {}) {
  const want = new Set(requested.length ? requested : available.filter((n) => GRANT_PLAN[n]));
  const helpers = new Set();
  const needsOf = (n) => (fresh && FRESH_PLAN[n]?.from ? [FRESH_PLAN[n].from] : GRANT_PLAN[n]?.needs ?? []);
  for (const n of want) for (const need of needsOf(n)) {
    const p = PRODUCER[need];
    if (p && !want.has(p) && available.includes(p)) helpers.add(p);
  }
  const ordered = Object.keys(GRANT_PLAN).filter((n) => want.has(n) || helpers.has(n)).map((n) => ({ name: n, helper: helpers.has(n) }));
  const unknown = [...want].filter((n) => !GRANT_PLAN[n]).map((n) => ({ name: n, unknown: true }));
  return [...ordered, ...unknown];
}

/** Shows one Google form in the terminal and returns exactly what the human chose. Never answers by itself. */
export async function askInTerminal({ tool, params }, { prompt, print }) {
  const props = params?.requestedSchema?.properties ?? {};
  print("");
  print(`  Google asks before ${tool} runs:`);
  print(`  "${String(params?.message ?? "").slice(0, 1000)}"`);
  const content = {};
  for (const [name, s] of Object.entries(props)) {
    const values = Array.isArray(s.enum) ? s.enum : s.type === "boolean" ? [true, false] : null;
    const labels = s.enumNames ?? (Array.isArray(s.oneOf) ? s.oneOf.map((o) => o.title) : null);
    print(`  ${s.title ?? name}`);
    if (!values) { print("  (this form asks for free text, which grant does not support: cancelling)"); return { action: "cancel" }; }
    // A plain statement of what each kind of answer covers, so the choice is informed. The choice stays the human's.
    const toolWide = values.indexOf("ALLOW_TOOL_ALWAYS");
    if (toolWide >= 0) {
      const perItem = values.some((v) => /^ALLOW_\w+_ALWAYS$/.test(String(v)) && v !== "ALLOW_TOOL_ALWAYS");
      print(`  Note: option ${toolWide + 1} ("Always allow this tool") covers every item for this tool, so an unattended agent is not stopped by new senders or owners.${perItem ? " The other \"Always\" option covers only this one item." : ""} Google keeps the answer 90 days and you cannot revoke it yourself.`);
    }
    values.forEach((v, i) => print(`    ${i + 1}) ${labels?.[i] ?? v}`));
    print("    c) Cancel: answer nothing");
    for (;;) {
      const a = String(await prompt("  Your choice (number or c): ")).trim().toLowerCase();
      if (a === "c" || a === "") return { action: "cancel" };
      const n = Number(a);
      if (Number.isInteger(n) && n >= 1 && n <= values.length) { content[name] = values[n - 1]; print(`  -> sending: ${labels?.[n - 1] ?? values[n - 1]}`); break; }
      print("  Not one of the choices; try again.");
    }
  }
  return { action: "accept", content };
}

/**
 * runGrant({ ctx, callTool, available, requested, prompt, print, now }) -> { steps: [...] }
 * callTool(name, args, session) is the server's own tool runner, so the calls go through the same bridge code.
 */
export async function runGrant({ ctx, callTool, available, requested = [], prompt, print, now = Date.now(), fresh = false }) {
  const bad = requested.filter((n) => !available.includes(n));
  if (bad.length) throw new GoogleError("UNKNOWN_TOOL", `Not an enabled read tool: ${bad.join(", ").slice(0, 200)}.`, { hint: `Enabled read tools: ${available.join(", ")}` });
  const found = {};
  try { found.account = (await ctx.auth.status({ verify: false })).account ?? undefined; } catch { /* not signed in: the calls will say so */ }
  const steps = [];
  for (const step of grantSteps(requested, available, { fresh })) {
    const rec = { tool: step.name, ...(step.helper ? { helper: true } : {}), asked: false, answers: [] };
    steps.push(rec);
    print("");
    print(`[${step.name}]${step.helper ? " (helper: finds something to test the next tools on)" : ""}`);
    const freshPlan = fresh ? FRESH_PLAN[step.name] : undefined;
    const plan = freshPlan && !freshPlan.from ? { ...GRANT_PLAN[step.name], ...freshPlan, needs: [] } : GRANT_PLAN[step.name];
    if (!plan) { rec.result = "skipped"; rec.reason = "no harmless test call is known for this tool"; print(`  skipped: ${rec.reason}`); continue; }
    const missing = (freshPlan?.from ? [freshPlan.from] : plan.needs ?? []).filter((k) => !(Array.isArray(found[k]) ? found[k].length : found[k]));
    if (missing.length) { rec.result = "skipped"; rec.reason = `nothing found to test it on (${missing.join(", ")})`; print(`  skipped: ${rec.reason}`); continue; }
    const session = {
      canElicit: true,
      elicit: async (req) => {
        rec.asked = true;
        const ans = await askInTerminal(req, { prompt, print });
        rec.answers.push({ form: String(req.params?.message ?? "").slice(0, 300), answer: ans.action === "accept" ? ans.content : ans.action });
        return ans;
      },
    };
    try {
      if (freshPlan?.from) {
        // Try the items found, one by one, until Google asks (an item it does not ask about is already allowed).
        const items = found[freshPlan.from].slice(0, FRESH_TRIES);
        let tried = 0, lastError = null;
        for (const id of items) {
          tried++;
          try { await callTool(step.name, freshPlan.args(id), session); lastError = null; }
          catch (e) {
            if (rec.asked || e?.code === "ABORT_ERR" || e?.name === "AbortError" || ["AUTH_REQUIRED", "AUTH_EXPIRED", "NOT_CONFIGURED", "GOOGLE_FORBIDDEN"].includes(e?.code)) throw e;
            lastError = e;
          }
          if (rec.asked) break;
        }
        rec.tried = tried;
        if (!rec.asked && lastError) throw lastError;
        rec.result = "ok";
        print(rec.asked ? `  Google asked (item ${tried} of ${items.length} tried); the call then worked.` : `  Google asked about none of the ${tried} items tried: they are all allowed already, or the tool is.`);
      } else {
        const out = await callTool(step.name, plan.args(found, now), session);
        Object.assign(found, Object.fromEntries(Object.entries(plan.yields?.(out.data) ?? {}).filter(([k, v]) => (Array.isArray(v) ? v.length : v) && !found[k])));
        rec.result = "ok";
        print(`  ${rec.asked ? "Google asked; the call then worked." : "Google did not ask; the call worked."}`);
      }
    } catch (e) {
      // Ctrl+C at a prompt: the human wants to stop, not to go on to the next tool.
      if (e?.code === "ABORT_ERR" || e?.name === "AbortError") { rec.result = "stopped"; print("  stopped: nothing was answered."); break; }
      rec.result = "error";
      rec.error = { code: e.code ?? "ERROR", message: String(e.message).slice(0, 300) };
      print(`  error ${rec.error.code}: ${rec.error.message}`);
      if (["AUTH_REQUIRED", "AUTH_EXPIRED", "NOT_CONFIGURED", "GOOGLE_FORBIDDEN"].includes(rec.error.code)) { print("  stopping: fix the sign-in or project setup first."); break; }
    }
  }
  return { steps };
}
