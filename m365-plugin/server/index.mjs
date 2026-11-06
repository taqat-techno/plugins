#!/usr/bin/env node
// Entry point of the Microsoft 365 MCP server (stdio). No dependencies; needs Node 18+.
import { createContext } from "./context.mjs";
import { serveStdio } from "./mcp.mjs";

const { listTools, callTool, ctx } = createContext();
process.stderr.write(`[m365] ready: modules=${ctx.cfg.modules.join(",")} read_only=${ctx.cfg.readOnly} client=${ctx.cfg.clientId ? "set" : "MISSING"}\n`);
serveStdio({ info: { name: "m365", version: "1.0.0" }, listTools, callTool });
