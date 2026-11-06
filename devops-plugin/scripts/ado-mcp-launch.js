#!/usr/bin/env node
// Launches the pinned Azure DevOps MCP server (@azure-devops/mcp@2.8.0).
//
// Configuration comes from two places, in this order:
//
//   1. the plugin's userConfig, which .mcp.json passes in as
//        ADO_PLUGIN_ORGANIZATION  <- ${user_config.ado_organization}
//        ADO_PLUGIN_TOKEN         <- ${user_config.ado_token}      (sensitive, OS keychain)
//        ADO_PLUGIN_PROJECT       <- ${user_config.ado_project}
//        ADO_PLUGIN_TEAM          <- ${user_config.ado_team}
//        ADO_PLUGIN_AUTH_MODE     <- ${user_config.ado_auth_mode}
//        ADO_PLUGIN_TENANT        <- ${user_config.ado_tenant}
//        ADO_PLUGIN_READONLY      <- ${user_config.ado_read_only}
//   2. plain environment variables (for hosts without userConfig, e.g. OpenClaw bots):
//        ADO_ORGANIZATION, ADO_MCP_AUTH_TOKEN, ADO_MCP_AUTH_TOKEN_FILE, ADO_MCP_PROJECT,
//        ADO_MCP_TEAM, ADO_AUTH_MODE, ADO_TENANT, ADO_MCP_READONLY
//
// A value that is empty, whitespace, or still an unexpanded "${...}" placeholder counts as unset.
//
// AUTHENTICATION. No system variable, admin right or PAT is needed for the default path:
//   auto (default)  PAT if one is configured, otherwise interactive
//   interactive     browser sign-in with the user's Entra ID account; the server caches tokens
//   azcli           reuse an existing `az login` session
//   pat             Personal Access Token from ADO_PLUGIN_TOKEN, ADO_MCP_AUTH_TOKEN, or the file
//                   named by ADO_MCP_AUTH_TOKEN_FILE (read once; its content is never printed)
//
// READ-ONLY MODE (ADO_PLUGIN_READONLY / ADO_MCP_READONLY = true). The launcher stands between
// the host and the server as a stdio proxy: write tools are removed from tools/list and any
// tools/call outside the allowlist is answered with an error and never reaches the server.
// The allowlist is data/write_tools.json ("read"); a tool it does not list is blocked. This
// is enforced outside the model and outside any host hook, so it holds on every host.
//
// Stdlib only. Keep the version pin in sync with README and CHANGELOG: 2.9.0 renames
// every tool and breaks the hooks, agents and rules of this plugin.
"use strict";

const fs = require("fs");
const os = require("os");
const path = require("path");
const { spawn } = require("child_process");

const PACKAGE = "@azure-devops/mcp@2.8.0";
// An Azure DevOps organization name: letters, digits, '.', '_' and '-' only. Checked
// because on Windows npx is a .cmd shim that only runs through cmd.exe.
const ORG_RE = /^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$/;
// A tenant: a GUID or a domain name. Same reason as ORG_RE.
const TENANT_RE = /^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$/;
const MODES = ["auto", "interactive", "azcli", "pat"];
const TOOLS_FILE = path.join(__dirname, "..", "data", "write_tools.json");

function clean(value) {
  const v = typeof value === "string" ? value.trim() : "";
  return v.startsWith("${") ? "" : v;
}

function pick(env, primary, fallback) {
  return clean(env[primary]) || clean(env[fallback]);
}

function isTrue(value) {
  return /^(1|true|yes|on)$/i.test(clean(value));
}

function expandHome(p) {
  return p === "~" || p.startsWith("~/") || p.startsWith("~\\") ? path.join(os.homedir(), p.slice(1)) : p;
}

// Reads the PAT from a file: first non-empty line, trimmed. Returns {token} or {error}.
// The error names the path, never the content.
function readTokenFile(file) {
  const p = expandHome(file);
  try {
    const text = fs.readFileSync(p, "utf8");
    const line = text.split(/\r?\n/).map((s) => s.trim()).find((s) => s.length > 0) || "";
    if (!line) return { error: "the token file " + p + " is empty" };
    return { token: line };
  } catch (e) {
    return { error: "the token file " + p + " cannot be read (" + (e && e.code ? e.code : "error") + ")" };
  }
}

function resolveConfig(env) {
  let organization = pick(env, "ADO_PLUGIN_ORGANIZATION", "ADO_ORGANIZATION");
  // Accept a pasted URL: https://dev.azure.com/<org>/... -> <org>
  const m = organization.match(/^https?:\/\/dev\.azure\.com\/([^/?#]+)/i);
  if (m) organization = m[1];
  const requestedMode = (pick(env, "ADO_PLUGIN_AUTH_MODE", "ADO_AUTH_MODE") || "auto").toLowerCase();
  return {
    organization,
    token: pick(env, "ADO_PLUGIN_TOKEN", "ADO_MCP_AUTH_TOKEN"),
    tokenFile: clean(env.ADO_MCP_AUTH_TOKEN_FILE),
    project: pick(env, "ADO_PLUGIN_PROJECT", "ADO_MCP_PROJECT"),
    team: pick(env, "ADO_PLUGIN_TEAM", "ADO_MCP_TEAM"),
    requestedMode,
    tenant: pick(env, "ADO_PLUGIN_TENANT", "ADO_TENANT"),
    readOnly: isTrue(env.ADO_PLUGIN_READONLY) || isTrue(env.ADO_MCP_READONLY),
  };
}

function buildLaunch(env, platform) {
  const cfg = resolveConfig(env);
  const errors = [];
  if (!cfg.organization) errors.push("no Azure DevOps organization is configured");
  else if (!ORG_RE.test(cfg.organization)) errors.push("the organization name contains characters an Azure DevOps organization cannot have");

  if (!MODES.includes(cfg.requestedMode)) {
    errors.push("the authentication mode '" + cfg.requestedMode + "' is not one of " + MODES.join(", "));
  }
  if (cfg.tenant && !TENANT_RE.test(cfg.tenant)) errors.push("the tenant contains characters a tenant id or domain cannot have");

  // Token: explicit value first, then the token file.
  let token = cfg.token;
  if (!token && cfg.tokenFile) {
    const r = readTokenFile(cfg.tokenFile);
    if (r.error) errors.push(r.error);
    else token = r.token;
  }

  // Mode: auto means "PAT if one is configured, else interactive sign-in".
  let mode = cfg.requestedMode;
  let reason = "set explicitly";
  if (mode === "auto") {
    mode = token ? "pat" : "interactive";
    reason = token ? "a token is configured" : "no token is configured";
  }
  if (mode === "pat" && !token && !errors.length) {
    errors.push("authentication mode 'pat' needs a Personal Access Token (ado_token, ADO_MCP_AUTH_TOKEN or ADO_MCP_AUTH_TOKEN_FILE)");
  }
  const serverAuth = { pat: "envvar", interactive: "interactive", azcli: "azcli" }[mode];

  const childEnv = Object.assign({}, env);
  for (const k of ["ADO_PLUGIN_ORGANIZATION", "ADO_PLUGIN_TOKEN", "ADO_PLUGIN_PROJECT", "ADO_PLUGIN_TEAM",
    "ADO_PLUGIN_AUTH_MODE", "ADO_PLUGIN_TENANT", "ADO_PLUGIN_READONLY", "ADO_MCP_AUTH_TOKEN_FILE"]) {
    delete childEnv[k];
  }
  // Only a PAT session carries a token; a stale ADO_MCP_AUTH_TOKEN must not leak into another mode.
  if (mode === "pat") childEnv.ADO_MCP_AUTH_TOKEN = token;
  else delete childEnv.ADO_MCP_AUTH_TOKEN;
  childEnv.ado_mcp_project = cfg.project;
  childEnv.ado_mcp_team = cfg.team;

  const isWin = platform === "win32";
  const command = isWin ? "npx.cmd" : "npx";
  const args = ["-y", PACKAGE, cfg.organization, "--authentication", serverAuth];
  if (cfg.tenant && mode !== "pat") args.push("--tenant", cfg.tenant);
  // On Windows npx is a .cmd shim, which only cmd.exe can run. Spawn cmd.exe ourselves
  // with an explicit command line instead of `shell: true` plus an args array (Node 24
  // deprecates that pattern, DEP0190). Every token here is a fixed string or a value
  // already checked against ORG_RE / TENANT_RE, so nothing needs escaping.
  const spawnCommand = isWin ? (clean(env.ComSpec) || "cmd.exe") : command;
  const spawnArgs = isWin ? ["/d", "/s", "/c", "\"" + [command].concat(args).join(" ") + "\""] : args;
  return {
    errors,
    mode,
    reason,
    readOnly: cfg.readOnly,
    command,
    args,
    shell: false,
    spawnCommand,
    spawnArgs,
    windowsVerbatimArguments: isWin,
    env: childEnv,
  };
}

// --- read-only proxy -------------------------------------------------------------------

function loadAllowedTools(file) {
  const data = JSON.parse(fs.readFileSync(file || TOOLS_FILE, "utf8"));
  return new Set(data.read);
}

function blockedResult(id, name) {
  return {
    jsonrpc: "2.0",
    id,
    result: {
      isError: true,
      content: [{
        type: "text",
        text: "Blocked: '" + name + "' is not available because the Azure DevOps connection is in read-only mode. " +
          "Do not retry; tell the user the change must be made by them or in a session that is not read-only.",
      }],
    },
  };
}

// Handles one message from the host. Returns { forward: msg|null, reply: msg|null }.
function filterRequest(msg, allowed, state) {
  if (!msg || typeof msg !== "object" || Array.isArray(msg)) return { forward: msg, reply: null };
  if (msg.method === "tools/call") {
    const name = msg.params && msg.params.name;
    if (typeof name !== "string" || !allowed.has(name)) {
      // A notification (no id) cannot be answered; drop it.
      return { forward: null, reply: msg.id === undefined ? null : blockedResult(msg.id, String(name)) };
    }
  } else if (msg.method === "tools/list" && msg.id !== undefined) {
    state.listIds.add(JSON.stringify(msg.id));
  }
  return { forward: msg, reply: null };
}

// Handles one message from the server: hides non-allowed tools from tools/list results.
function filterResponse(msg, allowed, state) {
  if (!msg || typeof msg !== "object" || Array.isArray(msg) || msg.id === undefined) return msg;
  const key = JSON.stringify(msg.id);
  if (state.listIds.has(key) && msg.result) {
    state.listIds.delete(key);
    if (Array.isArray(msg.result.tools)) {
      msg.result.tools = msg.result.tools.filter((t) => t && allowed.has(t.name));
    }
  }
  return msg;
}

function mapMessages(line, fn) {
  let parsed;
  try { parsed = JSON.parse(line); } catch (e) { return { raw: line }; }
  return { parsed: Array.isArray(parsed) ? parsed.map(fn).filter((x) => x !== null) : fn(parsed) };
}

function lineStream(readable, onLine, onEnd) {
  let buf = "";
  readable.setEncoding("utf8");
  readable.on("data", (chunk) => {
    buf += chunk;
    let i;
    while ((i = buf.indexOf("\n")) >= 0) {
      const line = buf.slice(0, i).replace(/\r$/, "");
      buf = buf.slice(i + 1);
      if (line.trim()) onLine(line);
    }
  });
  readable.on("end", () => { if (buf.trim()) onLine(buf.replace(/\r$/, "")); if (onEnd) onEnd(); });
}

// Wires host <-> server through the allowlist. hostIn/hostOut are the host-facing streams,
// serverIn/serverOut the server-facing ones.
function proxy(hostIn, hostOut, serverIn, serverOut, allowed) {
  const state = { listIds: new Set() };
  const send = (stream, obj) => stream.write(JSON.stringify(obj) + "\n");
  lineStream(hostIn, (line) => {
    const r = mapMessages(line, (m) => {
      const f = filterRequest(m, allowed, state);
      if (f.reply) send(hostOut, f.reply);
      return f.forward;
    });
    if (r.raw !== undefined) serverIn.write(r.raw + "\n");
    else if (r.parsed !== null && !(Array.isArray(r.parsed) && r.parsed.length === 0)) send(serverIn, r.parsed);
  }, () => { try { serverIn.end(); } catch (e) { /* closed */ } });
  lineStream(serverOut, (line) => {
    const r = mapMessages(line, (m) => filterResponse(m, allowed, state));
    if (r.raw !== undefined) hostOut.write(r.raw + "\n");
    else send(hostOut, r.parsed);
  });
}

// --- entry point -----------------------------------------------------------------------

function main() {
  const launch = buildLaunch(process.env, process.platform);
  if (launch.errors.length) {
    process.stderr.write(
      "[devops] Azure DevOps MCP not started: " + launch.errors.join("; ") +
      ". Set the devops plugin options in /config (ado_organization; ado_token only for PAT mode) or the " +
      "ADO_ORGANIZATION / ADO_MCP_AUTH_TOKEN environment variables, then restart Claude Code.\n"
    );
    process.exit(1);
  }
  let allowed = null;
  if (launch.readOnly) {
    try {
      allowed = loadAllowedTools();
    } catch (e) {
      // Fail closed: read-only was requested, so never start without the allowlist.
      process.stderr.write("[devops] Azure DevOps MCP not started: read-only mode needs data/write_tools.json (" +
        (e && e.code ? e.code : "unreadable") + ").\n");
      process.exit(1);
    }
  }
  if (process.env.ADO_MCP_LAUNCH_DRY_RUN === "1") {
    // Test seam: report what would run, without the token, and do not start anything.
    process.stdout.write(JSON.stringify({ command: launch.command, args: launch.args, shell: launch.shell,
      spawnCommand: launch.spawnCommand, spawnArgs: launch.spawnArgs, mode: launch.mode, readOnly: launch.readOnly,
      project: launch.env.ado_mcp_project, team: launch.env.ado_mcp_team,
      tokenSet: Boolean(launch.env.ADO_MCP_AUTH_TOKEN) }) + "\n");
    return;
  }
  process.stderr.write("[devops] authentication: " + launch.mode + " (" + launch.reason + ")" +
    (launch.readOnly ? "; read-only mode on" : "") + "\n");
  const child = spawn(launch.spawnCommand, launch.spawnArgs, {
    stdio: launch.readOnly ? ["pipe", "pipe", "inherit"] : "inherit",
    env: launch.env, shell: false,
    windowsVerbatimArguments: launch.windowsVerbatimArguments,
  });
  if (launch.readOnly) proxy(process.stdin, process.stdout, child.stdin, child.stdout, allowed);
  for (const sig of ["SIGINT", "SIGTERM"]) {
    process.on(sig, () => { try { child.kill(sig); } catch (e) { /* already gone */ } });
  }
  child.on("error", (err) => {
    process.stderr.write("[devops] could not start npx (" + err.message + "). Install Node.js 20+ (a per-user install needs no admin rights) and make sure npx is on PATH.\n");
    process.exit(1);
  });
  child.on("exit", (code, signal) => process.exit(code === null ? (signal ? 1 : 0) : code));
}

module.exports = { resolveConfig, buildLaunch, readTokenFile, loadAllowedTools, filterRequest, filterResponse, proxy, PACKAGE };

if (require.main === module) main();
