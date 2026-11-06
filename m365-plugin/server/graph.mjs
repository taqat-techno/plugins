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
];

function accessNeeded(path) {
  const need = NEEDS.find(([re]) => re.test(path))?.[1] ?? "the matching delegated Graph permission";
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
      if (body !== undefined) { init.headers["Content-Type"] = "application/json"; init.body = JSON.stringify(body); }
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
      if (res.status === 204) return {};
      const j = await res.json().catch(() => ({}));
      if (res.ok) return j;
      const gcode = String(j?.error?.code ?? res.status);
      if (res.status === 403 || /AccessDenied|Authorization_RequestDenied|Forbidden/i.test(gcode)) throw accessNeeded(path);
      if (res.status === 404) throw new M365Error("NOT_FOUND", `Not found: ${path.split("?")[0].replace(/\/[A-Za-z0-9_\-=+%.:@]{30,}/g, "/<id>")}`);
      if (res.status === 429) throw new M365Error("THROTTLED", "Microsoft is throttling requests. Wait a minute and retry.");
      throw new M365Error("GRAPH_ERROR", `Graph ${res.status} ${gcode}: ${String(j?.error?.message ?? "request failed").slice(0, 200)}`);
    }
  }
  return {
    get: (path, opts) => call("GET", path, undefined, opts),
    /** POST for lookups that change nothing. Callers pass fixed paths only. */
    postRead: (path, body, opts) => call("POST", path, body, opts),
  };
}
