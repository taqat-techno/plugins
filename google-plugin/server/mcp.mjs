// mcp.mjs - the smallest MCP stdio server that works: newline-delimited JSON-RPC with initialize, ping, tools/list and
// tools/call, plus ONE kind of server-to-client request: elicitation/create, used only to show Google's own
// confirmation form to the human through a client that declared elicitation support. No SDK, so the plugin has no npm
// dependencies and runs on any machine with Node 18+.
//
// Result contract (kept for agent hosts):
//   success -> one text block holding { ok: true, ...result }
//   failure -> isError true and TEXT BLOCKS ONLY (an image in an error result breaks some hosts' sessions), holding
//              { ok: false, error: { code, message, hint? } }. Short and secret-free.
import { createInterface } from "node:readline";
import { GoogleError } from "./util.mjs";

const text = (v) => (typeof v === "string" ? v : JSON.stringify(v, null, 2));

export function errorBody(e) {
  const error = { code: String(e?.code ?? "ERROR"), message: String(e?.message ?? e).slice(0, 400) };
  if (e?.hint) error.hint = String(e.hint).slice(0, 600);
  return { ok: false, error };
}

/** What the client said about elicitation at initialize: can it show a form, and does it speak the newer "mode" field. */
export function elicitationSupport(capabilities) {
  const e = capabilities?.elicitation;
  if (!e || typeof e !== "object") return { form: false, modeField: false };
  const keys = Object.keys(e);
  // {} = form support (older spec); {form:{}} / {form:{}, url:{}} = newer spec; {url:{}} alone = no forms.
  return { form: keys.length === 0 || "form" in e, modeField: keys.length > 0 };
}

/**
 * Builds the request handler; exported so tests can drive it without a process.
 * request(method, params, timeoutMs) sends a server-to-client request and resolves with the client's result.
 */
export function createHandler({ info, listTools, callTool, confirmTimeoutMs = 600_000 }, { request } = {}) {
  let support = { form: false, modeField: false };
  const session = {
    get canElicit() { return support.form && typeof request === "function"; },
    async elicit({ tool, module, params }) {
      let res;
      try {
        res = await request("elicitation/create", {
          ...(support.modeField ? { mode: "form" } : {}),
          message: `Google ${module} asks before ${tool} runs: ${String(params?.message ?? "").slice(0, 1000)}`,
          requestedSchema: params?.requestedSchema ?? { type: "object", properties: {} },
        }, confirmTimeoutMs);
      } catch (e) {
        throw new GoogleError("CONFIRMATION_NOT_ANSWERED", `Google's confirmation form for ${tool} was not answered (${String(e?.message ?? e).slice(0, 120)}). Nothing was sent to Google.`);
      }
      return res;
    },
  };
  return async function handle(msg) {
    switch (msg.method) {
      case "initialize":
        support = elicitationSupport(msg.params?.capabilities);
        return { protocolVersion: msg.params?.protocolVersion || "2024-11-05", capabilities: { tools: {} }, serverInfo: info };
      case "ping":
        return {};
      case "tools/list":
        return { tools: listTools() };
      case "tools/call": {
        const { name, arguments: args } = msg.params ?? {};
        try {
          const out = await callTool(name, args ?? {}, session);
          return { content: [{ type: "text", text: text({ ok: true, ...out }) }] };
        } catch (e) {
          return { isError: true, content: [{ type: "text", text: text(errorBody(e)) }] };
        }
      }
      default: {
        const err = new Error(`method not found: ${msg.method}`);
        err.rpcCode = -32601;
        throw err;
      }
    }
  };
}

export function serveStdio(opts, { input = process.stdin, output = process.stdout } = {}) {
  const send = (m) => output.write(JSON.stringify(m) + "\n");
  const pending = new Map();
  let next = 0;
  function request(method, params, timeoutMs) {
    const id = `google-plugin-${++next}`;
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => { pending.delete(id); reject(new Error("timed out")); }, timeoutMs);
      pending.set(id, { resolve: (v) => { clearTimeout(timer); resolve(v); }, reject: (e) => { clearTimeout(timer); reject(e); } });
      send({ jsonrpc: "2.0", id, method, params });
    });
  }
  const handle = createHandler(opts, { request });
  const rl = createInterface({ input });
  rl.on("line", async (line) => {
    if (!line.trim()) return;
    let msg;
    try { msg = JSON.parse(line); } catch {
      return send({ jsonrpc: "2.0", id: null, error: { code: -32700, message: "parse error" } });
    }
    // A response to one of our own requests (an elicitation answer).
    if (msg.method === undefined && msg.id !== undefined && pending.has(msg.id)) {
      const p = pending.get(msg.id);
      pending.delete(msg.id);
      if (msg.error) p.reject(new Error(String(msg.error.message ?? "client error").slice(0, 200)));
      else p.resolve(msg.result);
      return;
    }
    if (msg.id === undefined || msg.id === null || msg.method === undefined) return; // notification or stray response
    try {
      send({ jsonrpc: "2.0", id: msg.id, result: await handle(msg) });
    } catch (e) {
      send({ jsonrpc: "2.0", id: msg.id, error: { code: e.rpcCode ?? -32603, message: String(e.message).slice(0, 300) } });
    }
  });
  return rl;
}
