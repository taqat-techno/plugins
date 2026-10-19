#!/usr/bin/env node
// Launches the pinned Azure DevOps MCP server (@azure-devops/mcp@2.8.0) with its
// configuration resolved from two places, in this order:
//
//   1. the plugin's userConfig, which .mcp.json passes in as
//        ADO_PLUGIN_ORGANIZATION  <- ${user_config.ado_organization}
//        ADO_PLUGIN_TOKEN         <- ${user_config.ado_token}   (sensitive, OS keychain)
//        ADO_PLUGIN_PROJECT       <- ${user_config.ado_project}
//        ADO_PLUGIN_TEAM          <- ${user_config.ado_team}
//   2. the legacy environment variables ADO_ORGANIZATION, ADO_MCP_AUTH_TOKEN,
//      ADO_MCP_PROJECT and ADO_MCP_TEAM.
//
// .mcp.json has no "this, else that" syntax, which is why this launcher exists. A value
// that is empty, whitespace, or still an unexpanded "${...}" placeholder counts as unset.
//
// The server reads the PAT from ADO_MCP_AUTH_TOKEN ("--authentication envvar") and the
// default project/team from ado_mcp_project / ado_mcp_team (2.8.0 uses them to skip its
// interactive project picker). The token is never printed or passed on the command line.
//
// Stdlib only. Keep the version pin in sync with README and CHANGELOG: 2.9.0 renames
// every tool and breaks the hooks, agents and rules of this plugin.
"use strict";

const { spawn } = require("child_process");

const PACKAGE = "@azure-devops/mcp@2.8.0";
// An Azure DevOps organization name: letters, digits, '.', '_' and '-' only. Checked
// because on Windows npx is a .cmd shim that only runs through cmd.exe.
const ORG_RE = /^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$/;

function clean(value) {
  const v = typeof value === "string" ? value.trim() : "";
  return v.startsWith("${") ? "" : v;
}

function pick(env, primary, fallback) {
  return clean(env[primary]) || clean(env[fallback]);
}

function resolveConfig(env) {
  let organization = pick(env, "ADO_PLUGIN_ORGANIZATION", "ADO_ORGANIZATION");
  // Accept a pasted URL: https://dev.azure.com/<org>/... -> <org>
  const m = organization.match(/^https?:\/\/dev\.azure\.com\/([^/?#]+)/i);
  if (m) organization = m[1];
  return {
    organization,
    token: pick(env, "ADO_PLUGIN_TOKEN", "ADO_MCP_AUTH_TOKEN"),
    project: pick(env, "ADO_PLUGIN_PROJECT", "ADO_MCP_PROJECT"),
    team: pick(env, "ADO_PLUGIN_TEAM", "ADO_MCP_TEAM"),
  };
}

function buildLaunch(env, platform) {
  const cfg = resolveConfig(env);
  const errors = [];
  if (!cfg.organization) errors.push("no Azure DevOps organization is configured");
  else if (!ORG_RE.test(cfg.organization)) errors.push("the organization name contains characters an Azure DevOps organization cannot have");
  if (!cfg.token) errors.push("no Personal Access Token is configured");

  const childEnv = Object.assign({}, env);
  for (const k of ["ADO_PLUGIN_ORGANIZATION", "ADO_PLUGIN_TOKEN", "ADO_PLUGIN_PROJECT", "ADO_PLUGIN_TEAM"]) {
    delete childEnv[k];
  }
  childEnv.ADO_MCP_AUTH_TOKEN = cfg.token;
  childEnv.ado_mcp_project = cfg.project;
  childEnv.ado_mcp_team = cfg.team;

  const isWin = platform === "win32";
  const command = isWin ? "npx.cmd" : "npx";
  const args = ["-y", PACKAGE, cfg.organization, "--authentication", "envvar"];
  // On Windows npx is a .cmd shim, which only cmd.exe can run. Spawn cmd.exe ourselves
  // with an explicit command line instead of `shell: true` plus an args array (Node 24
  // deprecates that pattern, DEP0190). Every token here is a fixed string or the
  // organization name already checked against ORG_RE, so nothing needs escaping.
  const spawnCommand = isWin ? (clean(env.ComSpec) || "cmd.exe") : command;
  const spawnArgs = isWin ? ["/d", "/s", "/c", "\"" + [command].concat(args).join(" ") + "\""] : args;
  return {
    errors,
    command,
    args,
    shell: false,
    spawnCommand,
    spawnArgs,
    windowsVerbatimArguments: isWin,
    env: childEnv,
  };
}

function main() {
  const launch = buildLaunch(process.env, process.platform);
  if (launch.errors.length) {
    process.stderr.write(
      "[devops] Azure DevOps MCP not started: " + launch.errors.join("; ") +
      ". Set the devops plugin options in /config (ado_organization, ado_token) or the " +
      "ADO_ORGANIZATION / ADO_MCP_AUTH_TOKEN environment variables, then restart Claude Code.\n"
    );
    process.exit(1);
  }
  if (process.env.ADO_MCP_LAUNCH_DRY_RUN === "1") {
    // Test seam: report what would run, without the token, and do not start anything.
    process.stdout.write(JSON.stringify({ command: launch.command, args: launch.args, shell: launch.shell,
      spawnCommand: launch.spawnCommand, spawnArgs: launch.spawnArgs,
      project: launch.env.ado_mcp_project, team: launch.env.ado_mcp_team,
      tokenSet: Boolean(launch.env.ADO_MCP_AUTH_TOKEN) }) + "\n");
    return;
  }
  const child = spawn(launch.spawnCommand, launch.spawnArgs, {
    stdio: "inherit", env: launch.env, shell: false,
    windowsVerbatimArguments: launch.windowsVerbatimArguments,
  });
  for (const sig of ["SIGINT", "SIGTERM"]) {
    process.on(sig, () => { try { child.kill(sig); } catch (e) { /* already gone */ } });
  }
  child.on("error", (err) => {
    process.stderr.write("[devops] could not start npx (" + err.message + "). Install Node.js 20+ and make sure npx is on PATH.\n");
    process.exit(1);
  });
  child.on("exit", (code, signal) => process.exit(code === null ? (signal ? 1 : 0) : code));
}

module.exports = { resolveConfig, buildLaunch, PACKAGE };

if (require.main === module) main();
