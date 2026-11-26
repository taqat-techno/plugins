// remote.mjs - a minimal client for Google's Workspace MCP servers (Streamable HTTP, MCP protocol 2026-07-28).
// 2026-07-28 is stateless: no initialize, no session id. Every request carries the protocol version, the client's
// capabilities and identity in params._meta, plus Mcp-Method / Mcp-Name headers. When Google needs the human to
// confirm, it answers a tools/call with resultType "input_required" (inputRequests + an opaque requestState); the
// caller retries the same call with inputResponses and the requestState echoed. This file only transports: it never
// answers a confirmation. Deciding who answers is the bridge's job (server/tools/bridge.mjs).
import { GoogleError } from "./util.mjs";

export const PROTOCOL = "2026-07-28";
/** One stable client identity for every call (runtime and `grant`), so a grant made with one applies to the other. The
 *  version is fixed on purpose, not the plugin version: whether Google ties "Always allow" to it is not known, and a
 *  plugin update must not silently undo the human's grants. */
export const CLIENT_INFO = { name: "google-plugin", version: "1" };

const EXPIRED_HINT = "Run google_auth_status (or `node server/cli.mjs status`). If it reports AUTH_EXPIRED, a human must sign in again; do not retry in a loop.";

/** Reads a JSON or SSE response and returns the JSON-RPC message whose id matches. */
async function readMessage(res, id) {
  const t = await res.text();
  if ((res.headers.get("content-type") ?? "").includes("text/event-stream")) {
    let found = null;
    for (const block of t.split(/\r?\n\r?\n/)) {
      const data = block.split(/\r?\n/).filter((l) => l.startsWith("data:")).map((l) => l.slice(5)).join("\n");
      if (!data.trim()) continue;
      try { const m = JSON.parse(data); if (m.id === id) found = m; } catch { /* skip */ }
    }
    return { m: found, raw: found ? undefined : t };
  }
  try { return { m: JSON.parse(t), raw: undefined }; } catch { return { m: null, raw: t }; }
}

const short = (s, n = 300) => String(s ?? "").replace(/\s+/g, " ").trim().slice(0, n);

/** Maps an HTTP / JSON-RPC failure to a stable, secret-free error. */
export function remoteError(status, m, raw, mod) {
  const msg = short(m?.error?.message ?? raw ?? "");
  if (status === 401) return new GoogleError("AUTH_EXPIRED", `Google's ${mod} service did not accept the sign-in (401).`, { hint: EXPIRED_HINT });
  if (status === 403) return new GoogleError("GOOGLE_FORBIDDEN", `Google's ${mod} service refused the request (403)${msg ? `: ${msg}` : ""}.`, { hint: "Check in Google Cloud that the API and its MCP API are enabled for the project and that the OAuth client has 'Use this client for an AI-powered agent' ticked (docs/GOOGLE_CLOUD_SETUP.md)." });
  if (status === 429) return new GoogleError("RATE_LIMITED", `Google's ${mod} service is rate limiting requests (429).`, { hint: "Wait a minute before trying again." });
  if (status >= 500) return new GoogleError("GOOGLE_UNAVAILABLE", `Google's ${mod} service failed (${status}).`, { hint: "Try again later." });
  if (m?.error) return new GoogleError("GOOGLE_ERROR", `Google's ${mod} service returned an error${m.error.code !== undefined ? ` (${m.error.code})` : ""}${msg ? `: ${msg}` : ""}.`);
  return new GoogleError("GOOGLE_ERROR", `Unexpected reply from Google's ${mod} service (HTTP ${status}).`);
}

/**
 * createRemote({ urls, auth, fetch, timeoutMs }) -> { request(mod, method, params, name?) }
 * request returns the JSON-RPC result object; failures throw GoogleError.
 */
export function createRemote({ urls, auth, fetch: fetchImpl = globalThis.fetch, timeoutMs = 30_000 }) {
  let rpcId = 0;
  async function request(mod, method, params = {}, name) {
    const url = urls[mod];
    if (!url) throw new GoogleError("MODULE_DISABLED", `No Google MCP server is known for module ${mod}.`);
    const token = await auth.getAccessToken(mod);
    const id = ++rpcId;
    const body = {
      jsonrpc: "2.0", id, method,
      params: {
        ...params,
        _meta: {
          "io.modelcontextprotocol/protocolVersion": PROTOCOL,
          // Declared so Google can ask for a confirmation instead of refusing; answering is never automatic.
          "io.modelcontextprotocol/clientCapabilities": { elicitation: { form: {} } },
          "io.modelcontextprotocol/clientInfo": CLIENT_INFO,
        },
      },
    };
    const headers = {
      Authorization: `Bearer ${token}`, "Content-Type": "application/json", Accept: "application/json, text/event-stream",
      "MCP-Protocol-Version": PROTOCOL, "Mcp-Method": method, ...(name ? { "Mcp-Name": name } : {}),
    };
    let res;
    try {
      res = await fetchImpl(url, { method: "POST", headers, body: JSON.stringify(body), signal: AbortSignal.timeout(timeoutMs) });
    } catch (e) {
      if (e?.name === "TimeoutError" || e?.name === "AbortError") throw new GoogleError("TIMEOUT", `Google's ${mod} service did not answer within ${Math.round(timeoutMs / 1000)} s.`);
      throw new GoogleError("NETWORK_ERROR", `Cannot reach Google's ${mod} service: ${short(e?.message, 120)}.`);
    }
    const { m, raw } = await readMessage(res, id);
    if (!res.ok || !m || m.error || !m.result) throw remoteError(res.status, m, raw, mod);
    return m.result;
  }

  /** tools/call; extra = { inputResponses, requestState } when answering a confirmation. */
  const callTool = (mod, name, args, extra = {}) => request(mod, "tools/call", { name, arguments: args ?? {}, ...extra }, name);

  /** tools/list, all pages. */
  async function listTools(mod) {
    const tools = [];
    let cursor;
    for (let page = 0; page < 20; page++) {
      const r = await request(mod, "tools/list", cursor ? { cursor } : {});
      tools.push(...(r.tools ?? []));
      cursor = r.nextCursor;
      if (!cursor) break;
    }
    return tools;
  }

  return { request, callTool, listTools };
}
