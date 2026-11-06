// mcp.mjs - the smallest MCP stdio server that works: newline-delimited JSON-RPC with
// initialize, ping, tools/list and tools/call. No SDK, so the plugin has no npm dependencies
// and runs on any machine that has Node 18+.
import { createInterface } from "node:readline";

const text = (v) => (typeof v === "string" ? v : JSON.stringify(v, null, 2));

/** Builds the request handler; exported so tests can drive it without a process. */
export function createHandler({ info, listTools, callTool }) {
  return async function handle(msg) {
    switch (msg.method) {
      case "initialize":
        return {
          protocolVersion: msg.params?.protocolVersion || "2024-11-05",
          capabilities: { tools: {} },
          serverInfo: info,
        };
      case "ping":
        return {};
      case "tools/list":
        return { tools: listTools() };
      case "tools/call": {
        const { name, arguments: args } = msg.params ?? {};
        try {
          const out = await callTool(name, args ?? {});
          return { content: [{ type: "text", text: text(out) }] };
        } catch (e) {
          // Short and secret-free: tools throw M365Error with a code and a hint.
          const body = { error: e?.code ?? "ERROR", message: String(e?.message ?? e).slice(0, 400) };
          if (e?.hint) body.hint = e.hint;
          return { isError: true, content: [{ type: "text", text: text(body) }] };
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
  const handle = createHandler(opts);
  const send = (m) => output.write(JSON.stringify(m) + "\n");
  const rl = createInterface({ input });
  rl.on("line", async (line) => {
    if (!line.trim()) return;
    let msg;
    try { msg = JSON.parse(line); } catch {
      return send({ jsonrpc: "2.0", id: null, error: { code: -32700, message: "parse error" } });
    }
    if (msg.id === undefined || msg.id === null) return; // notification: no reply
    try {
      send({ jsonrpc: "2.0", id: msg.id, result: await handle(msg) });
    } catch (e) {
      send({ jsonrpc: "2.0", id: msg.id, error: { code: e.rpcCode ?? -32603, message: String(e.message).slice(0, 300) } });
    }
  });
  return rl;
}
