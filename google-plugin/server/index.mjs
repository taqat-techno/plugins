#!/usr/bin/env node
// Entry point of the Google (Gmail, Calendar, Drive) MCP server (stdio). No dependencies; needs Node 18+.
// It is a local bridge to Google's own Workspace MCP servers, signed in with the user's own OAuth client.
import { createContext } from "./context.mjs";
import { serveStdio } from "./mcp.mjs";

const { listTools, callTool, ctx, tools } = createContext();
process.stderr.write(`[google] ready: modules=${ctx.cfg.modules.join(",")} read_only=${ctx.cfg.readOnly} tools=${tools.length} confirm_mode=${ctx.cfg.confirmMode} client_file=${ctx.cfg.clientSecretFile ? "set" : "MISSING"}\n`);
serveStdio({ info: { name: "google", version: "0.8.0" }, listTools, callTool, confirmTimeoutMs: ctx.cfg.confirmTimeoutMs });
