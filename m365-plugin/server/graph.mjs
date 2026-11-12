// graph.mjs - the plugin's only door to Microsoft Graph.
//
// Every tool builds its own fixed path from validated arguments. There is deliberately NO generic
// "graph_request(method, url)" tool anywhere. Phase 1 is read-only: `get`, plus `postRead` for the
// two Graph lookups that need POST but change nothing (getSchedule, findMeetingTimes).
// Calls are bounded by a timeout; GET is retried on throttling and transient failures.
import { M365Error } from "./util.mjs";

const GRAPH = "https://graph.microsoft.com/v1.0";
const RETRYABLE = new Set([429, 500, 502, 503, 504]);

const sleepDefault = (ms) => new Promise((r) => setTimeout(r, ms));

// Which permission a forbidden call most likely needs, by path prefix. Shown in ACCESS_NEEDED.
const NEEDS = [
  [/^\/me\/(messages|mailFolders)/, "Mail.Read"],
  [/^\/me\/(calendar|events)/, "Calendars.Read"],
  [/^\/(me\/)?chats/, "Chat.Read"],
  [/^\/teams\/.+\/channels\/.+\/messages/, "ChannelMessage.Read.All (admin consent)"],
  [/^\/(me\/joinedTeams|teams)/, "Team.ReadBasic.All / Channel.ReadBasic.All"],
  [/^\/me\/people/, "People.Read"],
  [/^\/users/, "User.ReadBasic.All"],
  [/^\/search\/query/, "Files.Read.All"],
  [/^\/me\/onlineMeetings\/.+\/transcripts/, "OnlineMeetingTranscript.Read.All (admin consent)"],
  [/^\/shares\//, "Files.Read.All"],
];

const NEEDS_WRITE = [
  [/^\/chats$/, "Chat.Create (or Chat.ReadWrite)"],
  [/^\/users\/[^/]+\/chats\/.+\/softDelete$/, "Chat.ReadWrite"],
  [/^\/teams\/.+\/messages/, "ChannelMessage.Send"],
  [/^\/me\/(messages|mailFolders)/, "Mail.ReadWrite / Mail.Send"],
  [/^\/me\/(calendar|events)/, "Calendars.ReadWrite"],
  [/^\/chats/, "ChatMessage.Send (or Chat.ReadWrite)"],
  [/^\/(drives|me\/drive)/, "Files.ReadWrite"],
];

function accessNeeded(path, method = "GET") {
  const table = method === "GET" ? NEEDS : NEEDS_WRITE;
  const need = method === "PATCH" && /^\/chats\//.test(path) ? "Chat.ReadWrite"
    : table.find(([re]) => re.test(path))?.[1] ?? "the matching delegated Graph permission";
  return new M365Error("ACCESS_NEEDED", `Microsoft refused this request: missing permission ${need}.`, {
    hint: "Do not work around it. Ask a tenant admin to grant that delegated permission to the app (or sign in again to approve it), then retry. A forwardable request: 'Please grant the delegated Microsoft Graph permission " + need + " to the Microsoft 365 plugin app.'",
  });
}

export function createGraph(cfg, auth, { fetch: fetchImpl = globalThis.fetch, sleep = sleepDefault } = {}) {
  async function call(method, path, body, opts = {}) {
    const url = path.startsWith("http") ? path : GRAPH + path;
    if (!url.startsWith(GRAPH)) throw new M365Error("INVALID_ARGUMENT", "refusing a non-Graph address");
    const canRetry = method === "GET";
    for (let attempt = 1; ; attempt++) {
      const token = await auth.getAccessToken();
      const init = {
        method,
        headers: { Authorization: `Bearer ${token}`, Accept: "application/json", ...(opts.headers ?? {}) },
        signal: AbortSignal.timeout(cfg.timeoutMs),
      };
      if (opts.bytes) { init.headers["Content-Type"] = opts.contentType ?? "application/octet-stream"; init.body = opts.bytes; init.signal = AbortSignal.timeout(Math.max(cfg.timeoutMs, 120_000)); }
      else if (body !== undefined) { init.headers["Content-Type"] = "application/json"; init.body = JSON.stringify(body); }
      let res;
      try { res = await fetchImpl(url, init); }
      catch (e) {
        if (canRetry && attempt < cfg.attempts) { await sleep(Math.min(1000 * 2 ** (attempt - 1), 8000)); continue; }
        const timedOut = e?.name === "TimeoutError" || e?.name === "AbortError";
        throw new M365Error(timedOut ? "TIMEOUT" : "NETWORK_ERROR", `${method} ${path.split("?")[0]} ${timedOut ? "timed out" : "failed"}`);
      }
      if (canRetry && RETRYABLE.has(res.status) && attempt < cfg.attempts) {
        const ra = Number(res.headers?.get?.("retry-after"));
        await sleep(Number.isFinite(ra) && ra > 0 ? Math.min(ra * 1000, 30_000) : Math.min(1000 * 2 ** (attempt - 1), 8000));
        continue;
      }
      if (opts.raw && res.ok) return Buffer.from(await res.arrayBuffer());
      if (res.status === 204) return {};
      const j = await res.json().catch(() => ({}));
      if (res.ok) return j;
      const gcode = String(j?.error?.code ?? res.status);
      if (res.status === 403 || /AccessDenied|Authorization_RequestDenied|Forbidden/i.test(gcode)) throw Object.assign(accessNeeded(path, method), { status: res.status });
      if (res.status === 404) throw new M365Error("NOT_FOUND", `Not found: ${path.split("?")[0].replace(/\/[A-Za-z0-9_\-=+%.:@]{30,}/g, "/<id>")}`, { status: 404 });
      if (res.status === 429) throw new M365Error("THROTTLED", "Microsoft is throttling requests. Wait a minute and retry.", { status: 429 });
      throw new M365Error("GRAPH_ERROR", `Graph ${res.status} ${gcode}: ${String(j?.error?.message ?? "request failed").slice(0, 200)}`, { status: res.status });
    }
  }
  const mutate = (method) => (path, body, opts) => {
    // Defense in depth: read-only mode already removes the write tools; this stops a bug from writing.
    if (cfg.readOnly) throw new M365Error("READ_ONLY", "Read-only mode is on; nothing can be changed.");
    return call(method, path, body, opts);
  };
  return {
    get: (path, opts) => call("GET", path, undefined, opts),
    /** Changes Microsoft 365. Never retried: a timed-out POST may already have happened. */
    post: mutate("POST"), patch: mutate("PATCH"), del: (path, opts) => mutate("DELETE")(path, undefined, opts),
    /** PUT a file's bytes to a fixed Graph path (a OneDrive upload). Never retried. */
    putBytes: (path, bytes, contentType) => mutate("PUT")(path, undefined, { bytes, contentType }),
    /** POST for lookups that change nothing. Callers pass fixed paths only. */
    postRead: (path, body, opts) => call("POST", path, body, opts),
    /** PUT one chunk to an Outlook attachment upload session. The upload URL carries its own short-lived
     *  authorization, so the Graph token is NOT sent; only Microsoft's Outlook hosts are accepted. */
    async uploadChunk(uploadUrl, chunk, start, total) {
      if (cfg.readOnly) throw new M365Error("READ_ONLY", "Read-only mode is on; nothing can be changed.");
      let u;
      try { u = new URL(uploadUrl); } catch { u = null; }
      if (!u || u.protocol !== "https:" || !/(^|\.)outlook\.office(365)?\.com$/i.test(u.hostname)) throw new M365Error("INVALID_ARGUMENT", "refusing an upload address that is not Microsoft's Outlook service");
      let res;
      try {
        res = await fetchImpl(u.href, { method: "PUT", body: chunk, signal: AbortSignal.timeout(Math.max(cfg.timeoutMs, 60_000)),
          headers: { "Content-Type": "application/octet-stream", "Content-Length": String(chunk.length), "Content-Range": `bytes ${start}-${start + chunk.length - 1}/${total}` } });
      } catch (e) { throw new M365Error(e?.name === "TimeoutError" ? "TIMEOUT" : "NETWORK_ERROR", "the attachment upload did not complete"); }
      if (!res.ok) throw new M365Error("GRAPH_ERROR", `attachment upload refused (${res.status})`, { status: res.status });
      return res.status === 204 ? {} : res.json().catch(() => ({}));
    },
  };
}
