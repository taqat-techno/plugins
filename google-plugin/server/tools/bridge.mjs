// bridge.mjs - re-exposes Google's own Workspace MCP tools (Gmail, Calendar, Drive) through this local server.
//
// What is exposed comes from two files, never from the live tool list:
//   data/tools.json              the class of every exposed tool (read | write | confirm) and description rewrites
//   data/google_mcp_snapshot.json Google's recorded tool list (name, description, inputSchema)
// So a tool Google adds or changes never appears silently; `node server/cli.mjs schema-check` shows the drift.
// Local names are <module>_<Google name>: gmail_get_thread, calendar_list_events, drive_search_files.
//
// Confirmations: Google may answer a call with "input_required" (a form asking the human to allow the read). The
// bridge NEVER answers such a form itself. It forwards the form to its own MCP client when that client declared
// elicitation support (the client shows it to the human), or fails with CONFIRMATION_NEEDED, telling the agent to ask
// the human to run `cli.mjs grant` in their own terminal.
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { cliCmd, GoogleError } from "../util.mjs";
import { guestGuard } from "../guards.mjs";
import { WRITE_GRANT_PLAN } from "../grant.mjs";

/** Google's calendar get_event, for the guest guard (same confirmation handling as every bridged call). */
const GET_EVENT = { name: "calendar_get_event", module: "calendar", remote: "get_event" };
async function readEvent(q, ctx, session) {
  const r = await callGoogle(GET_EVENT, q, ctx, session);
  if (r.isError) throw new GoogleError("TOOL_ERROR", "get_event failed");
  if (r.structuredContent !== undefined) return r.structuredContent;
  try { return JSON.parse((r.content ?? []).find((c) => c.type === "text")?.text ?? "null"); } catch { return null; }
}

const DATA = new URL("../../data/", import.meta.url);
export const CLASSES = JSON.parse(readFileSync(new URL("tools.json", DATA), "utf8"));
export const SNAPSHOT = JSON.parse(readFileSync(new URL("google_mcp_snapshot.json", DATA), "utf8"));
export const CLI_PATH = fileURLToPath(new URL("../cli.mjs", import.meta.url));
export const MAX_DESCRIPTION = 1024;

// Tools the plugin implements itself (not a Google tool passed through) are classified in tools.json too, but listed in
// plugin_tools so the bridge does not look for them in the snapshot.
const OWN = new Set(CLASSES.plugin_tools ?? []);
const KIND = {};
for (const k of ["read", "write", "confirm"]) for (const n of CLASSES[k] ?? []) if (!OWN.has(n)) KIND[n] = k;

/** Every Google tool in the snapshot, by local name. */
export function snapshotTools() {
  const out = new Map();
  for (const [mod, srv] of Object.entries(SNAPSHOT.servers)) for (const t of srv.tools) out.set(`${mod}_${t.name}`, { module: mod, remote: t.name, ...t });
  return out;
}

const short = (s, n) => String(s ?? "").replace(/\s+/g, " ").trim().slice(0, n);

// ------------------------------------------------------------------------------------------------ results

/** Cuts long strings and, if still too big, long arrays; replaces non-text content blocks with a description. */
export function capResult(data, { maxString, maxTotal }) {
  let truncated = false;
  const walk = (v) => {
    if (typeof v === "string") {
      if (v.length <= maxString) return v;
      truncated = true;
      return `${v.slice(0, maxString)}…[cut ${v.length - maxString} characters]`;
    }
    if (Array.isArray(v)) return v.map(walk);
    if (v && typeof v === "object") return Object.fromEntries(Object.entries(v).map(([k, x]) => [k, walk(x)]));
    return v;
  };
  let out = walk(data);
  // Still too large: shorten the longest arrays from the end until it fits.
  for (let guard = 0; JSON.stringify(out ?? null).length > maxTotal && guard < 200; guard++) {
    let best = null;
    const find = (v) => {
      if (Array.isArray(v)) { if (v.length > 1 && (!best || v.length > best.length)) best = v; v.forEach(find); }
      else if (v && typeof v === "object") Object.values(v).forEach(find);
    };
    find(out);
    if (!best) {
      const s = JSON.stringify(out);
      out = { cut_text: `${s.slice(0, maxTotal)}…[cut]` };
      truncated = true;
      break;
    }
    best.splice(Math.max(1, Math.floor(best.length / 2)));
    truncated = true;
  }
  return { data: out, truncated };
}

/** Turns Google's tool result into the plugin's success payload; Google's own tool errors become TOOL_ERROR. */
export function shapeResult(localName, x, caps) {
  if (x.isError) {
    const text = (x.content ?? []).filter((c) => c.type === "text").map((c) => c.text).join(" ");
    // Seen live (2026-11-26, drive_download_file_content): Google refuses with this text instead of sending a form,
    // although the plugin declares form support. `grant` cannot fix that, so it gets its own code.
    if (/requires user confirmation, which this client does not support/i.test(text)) {
      throw new GoogleError("CONFIRMATION_UNSUPPORTED", `Google refused ${localName}: it requires a confirmation that Google does not offer to this client. Nothing was changed.`, {
        hint: "Running grant does not help for this tool. Use another tool for the same need where one exists (for example drive_read_file_content instead of drive_download_file_content).",
      });
    }
    throw new GoogleError("TOOL_ERROR", `Google reported an error for ${localName}${text ? `: ${short(text, 300)}` : "."}`);
  }
  let data = x.structuredContent;
  const blocks = x.content ?? [];
  if (data === undefined) {
    const texts = blocks.filter((c) => c.type === "text").map((c) => c.text);
    if (texts.length === 1) { try { data = JSON.parse(texts[0]); } catch { data = texts[0]; } }
    else if (texts.length > 1) data = texts;
    else data = null;
  }
  const omitted = blocks.filter((c) => c.type !== "text").map((c) => ({
    type: c.type, mimeType: c.mimeType ?? c.resource?.mimeType, uri: c.resource?.uri ?? c.uri,
    approx_chars: String(c.data ?? c.resource?.blob ?? c.resource?.text ?? "").length,
  }));
  const capped = capResult(data, caps);
  return {
    tool: localName,
    // Everything Google returns can hold text written by third parties (emails, documents, event invitations).
    untrusted: true,
    data: capped.data,
    ...(capped.truncated ? { truncated: true } : {}),
    ...(omitted.length ? { omitted_content: omitted } : {}),
  };
}

// ------------------------------------------------------------------------------------------------ confirmations

function confirmationNeeded(localName, why, grantName = localName, kind = "read", cfg) {
  const cli = cliCmd(cfg, `node "${CLI_PATH}"`);
  let hint;
  if (kind === "read") hint = `Ask the human to run this in their own terminal and choose an answer on Google's form (for example "Always allow this tool"): ${cli} grant ${grantName} . Then try again. Do not retry before they have.`;
  else if (WRITE_GRANT_PLAN[grantName]) hint = `Ask the human to run this in their own terminal, on an item they are happy to change (it really performs ${grantName} on it), and answer Google's form: ${cli} grant ${grantName} --target <id> . Then try again. Do not retry before they have.`;
  else hint = `grant cannot ask Google's question for ${grantName}. The human can do this change in Google's own app, or use a client that shows Google's confirmation forms.`;
  return new GoogleError("CONFIRMATION_NEEDED", `Google asks the human to confirm before ${localName} can run, and ${why}. The plugin never answers Google's confirmation for the human.`, { hint });
}

/** Checks the human's answer against Google's form before passing it back, so nothing outside the form is sent. */
export function checkAnswer(ans, schema) {
  const action = ans?.action;
  if (action === "decline" || action === "cancel") return { action };
  if (action !== "accept") return { action: "cancel" };
  const props = schema?.properties ?? {};
  const content = {};
  for (const [k, v] of Object.entries(ans.content ?? {})) {
    const p = props[k];
    if (!p) continue;
    if (Array.isArray(p.enum) && !p.enum.includes(v)) throw new GoogleError("INVALID_CONFIRMATION_ANSWER", `The answer for ${short(k, 60)} is not one of Google's choices; nothing was sent.`);
    content[k] = v;
  }
  for (const r of schema?.required ?? []) if (!(r in content)) throw new GoogleError("INVALID_CONFIRMATION_ANSWER", `The answer misses the required field ${short(r, 60)}; nothing was sent.`);
  return { action: "accept", content };
}

/**
 * Calls one Google tool and returns Google's final result, handling Google's confirmation forms on the way.
 * session = { canElicit, elicit({ tool, module, params }) -> {action, content?} } describes the local MCP client (or the
 * `grant` terminal). Without canElicit, any confirmation ends in CONFIRMATION_NEEDED. def.grantAs names the tool the
 * human should run `grant` for (default def.name).
 */
export async function callGoogle(def, args, ctx, session = {}) {
  const grantName = def.grantAs ?? def.name;
  let extra = {};
  for (let round = 0; round < 4; round++) {
    const r = await ctx.remote.callTool(def.module, def.remote, args, extra);
    if (r.resultType !== "input_required") return r;
    if (ctx.cfg.confirmMode === "error") throw confirmationNeeded(def.name, "the plugin is set to never forward confirmations (GOOGLE_CONFIRM_MODE=error)", grantName, def.kind, ctx.cfg);
    if (!session.canElicit || typeof session.elicit !== "function") throw confirmationNeeded(def.name, "this client cannot show Google's confirmation form", grantName, def.kind, ctx.cfg);
    const inputResponses = {};
    for (const [key, req] of Object.entries(r.inputRequests ?? {})) {
      const mode = req?.params?.mode ?? "form";
      if (req?.method !== "elicitation/create" || mode !== "form") {
        throw new GoogleError("UNSUPPORTED_CONFIRMATION", `Google asked for input the plugin cannot pass on (${short(req?.method, 40)}, mode ${short(mode, 20)}). Nothing was answered.`);
      }
      const ans = await session.elicit({ tool: def.name, module: def.module, params: req.params });
      inputResponses[key] = checkAnswer(ans, req.params?.requestedSchema);
    }
    extra = { inputResponses, ...(r.requestState !== undefined ? { requestState: r.requestState } : {}) };
  }
  throw new GoogleError("CONFIRMATION_LOOP", `Google kept asking for confirmation for ${def.name}; stopped after 4 rounds.`);
}

// Write-class label tools must not do what the confirm-class tools exist for: putting mail in Trash or Spam through a
// plain "add label" call would bypass the human's confirmation. (Whether Google itself accepts these system labels there
// is not relied on.)
const SENSITIVE_LABELS = new Set(["TRASH", "SPAM"]);
const LABEL_ARGS = { gmail_label_thread: "labelIds", gmail_label_message: "labelIds", gmail_update_message_labels: "addLabelIds" };

/** Refuses arguments that would turn a write-class call into a confirm-class effect. */
export function guardArgs(name, args) {
  const key = LABEL_ARGS[name];
  if (!key) return;
  const bad = (Array.isArray(args?.[key]) ? args[key] : []).filter((l) => SENSITIVE_LABELS.has(String(l).trim().toUpperCase()));
  if (bad.length) {
    const thread = name.includes("thread");
    throw new GoogleError("NEEDS_CONFIRM_TOOL", `${name} does not put mail in Trash or Spam; nothing was changed.`, {
      hint: `Use ${thread ? "gmail_trash_thread or gmail_mark_thread_spam" : "gmail_trash_message or gmail_mark_message_spam"}, which ask the human first.`,
    });
  }
}

/** Runs one bridged tool: Google's result, marked untrusted and size-capped. */
export async function runBridged(def, args, ctx, session = {}) {
  guardArgs(def.name, args);
  await guestGuard(def.name, args, ctx, (q) => readEvent(q, ctx, session));
  ctx.limiter?.check(def.name, ctx.cfg.writeLimitPerHour);
  const r = await callGoogle(def, args, ctx, session);
  return shapeResult(def.name, r, { maxString: ctx.cfg.maxStringChars, maxTotal: ctx.cfg.maxResultChars });
}

// ------------------------------------------------------------------------------------------------ tool definitions

/** All bridged tool definitions (every class), built from tools.json + the snapshot. */
export function bridgedTools() {
  const snap = snapshotTools();
  const out = [];
  for (const [name, kind] of Object.entries(KIND)) {
    const t = snap.get(name);
    if (!t) throw new Error(`tools.json lists ${name}, which is not in data/google_mcp_snapshot.json`);
    const description = CLASSES.descriptions?.[name] ?? t.description ?? "";
    const def = {
      name, kind, module: t.module, remote: t.remote, confirm: kind === "confirm",
      description: description.length <= MAX_DESCRIPTION ? description : `${description.slice(0, MAX_DESCRIPTION - 1)}…`,
      inputSchema: t.inputSchema ?? { type: "object", properties: {} },
    };
    def.handler = (args, ctx, session) => runBridged(def, args, ctx, session);
    out.push(def);
  }
  return out;
}
