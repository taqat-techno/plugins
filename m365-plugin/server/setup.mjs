// setup.mjs - validates and saves <M365_HOME>/settings.json. Two callers with different trust:
//   viaTool: true   the MCP tool m365_setup_save, which a model (and so injected text) can call. It may only set the
//                   identity of the app on FIRST setup, never credential FILES, and never change an app already in use.
//   viaTool: false  the command line (`node server/cli.mjs setup`), typed by the person themselves. May also point the
//                   plugin at another tool's token and secret files.
// Credential files can therefore only be chosen by the human: in the plugin settings, in the environment, or here.
import { mkdirSync, readFileSync, statSync, writeFileSync } from "node:fs";
import { delimiter, isAbsolute, join } from "node:path";
import { randomUUID } from "node:crypto";
import { SETTINGS_KEYS, parseRedirectUri, settingsPath } from "./config.mjs";
import { M365Error, replaceFile } from "./util.mjs";

export const CREDENTIAL_KEYS = ["refresh_token_file", "client_secret_file"];
// Settings only the person may choose: credential files, the folders files may be mailed out from, the signature file.
export const HUMAN_ONLY_KEYS = [...CREDENTIAL_KEYS, "attach_dirs", "signature_file"];
const GUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const TENANT = /^([0-9a-f-]{36}|[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)+|organizations|common|consumers)$/i;

/** Single-line, printable, no spaces: what a token or a secret looks like. Keeps a wrong file (a key, a document) out. */
function checkSecretFile(path, field) {
  if (!isAbsolute(path)) throw new M365Error("INVALID_ARGUMENT", `${field} must be an absolute path`);
  let st;
  try { st = statSync(path); } catch { throw new M365Error("INVALID_ARGUMENT", `${field}: no such file`); }
  if (!st.isFile() || st.size > 4096 || st.size < 8) throw new M365Error("INVALID_ARGUMENT", `${field} does not look like a token or secret file (it must be a small single-line file)`);
  const text = readFileSync(path, "utf8").trim();
  if (!/^[\x21-\x7E]{8,3000}$/.test(text)) throw new M365Error("INVALID_ARGUMENT", `${field} does not look like a token or secret file (one line, no spaces). Nothing was saved.`);
}

function readSaved(home) {
  try { return JSON.parse(readFileSync(settingsPath(home), "utf8")); } catch { return {}; }
}

export function saveSettings(cfg, input, { viaTool }) {
  const saved = readSaved(cfg.home);
  const next = { ...saved };
  // "Already configured" is judged on what is on disk right now plus what this process was started with, so a setup the
  // person made in their terminal after start-up is never overwritten by a stale view.
  const currentId = cfg.clientId || (typeof saved.client_id === "string" ? saved.client_id.trim() : "");
  const currentTenant = (typeof saved.tenant === "string" && saved.tenant.trim()) || cfg.tenant;
  const changed = [];
  for (const k of SETTINGS_KEYS) {
    if (input[k] === undefined) continue;
    if (viaTool && HUMAN_ONLY_KEYS.includes(k)) {
      throw new M365Error("CREDENTIAL_SETTING_NOT_ALLOWED", `${k} cannot be set through a tool: only the person at the keyboard may choose credential files, the folders files may be attached from, and the signature file.`,
        { hint: "Ask the user to run, in their own terminal: node server/cli.mjs setup --token-file <path> --secret-file <path>   (or to fill in the plugin settings 'Shared token file' / 'App secret file'). Never ask them to paste a token or secret." });
    }
    if (viaTool && (k === "client_id" || k === "tenant") && currentId && String(input[k]).trim().toLowerCase() !== (k === "client_id" ? currentId : currentTenant).toLowerCase()) {
      throw new M365Error("ALREADY_CONFIGURED", `The Microsoft app is already set up, so ${k} cannot be changed from here.`,
        { hint: "To switch to a different app, the user changes it in the plugin settings, or runs in their own terminal: node server/cli.mjs setup --client-id <id> [--tenant <id>]" });
    }
    const v = String(input[k] ?? "").trim();
    if (v === "") { delete next[k]; changed.push(k); continue; }
    if (k === "client_id" && !GUID.test(v)) throw new M365Error("INVALID_ARGUMENT", "client_id must be the Application (client) ID, a GUID like 00000000-0000-0000-0000-000000000000");
    if (k === "tenant" && !TENANT.test(v)) throw new M365Error("INVALID_ARGUMENT", "tenant must be a tenant id, a domain such as contoso.com, or organizations");
    if (k === "scope_mode" && !["requested", "app"].includes(v.toLowerCase())) throw new M365Error("INVALID_ARGUMENT", "scope_mode must be requested or app");
    if (k === "auth_mode" && !["auto", "interactive", "device-code"].includes(v.toLowerCase())) throw new M365Error("INVALID_ARGUMENT", "auth_mode must be auto, interactive or device-code");
    if (k === "redirect_uri") { try { parseRedirectUri(v); } catch (e) { throw new M365Error("INVALID_ARGUMENT", e.message); } }
    if (CREDENTIAL_KEYS.includes(k)) checkSecretFile(v, k);
    if (k === "attach_dirs") for (const d of v.split(delimiter).map((x) => x.trim()).filter(Boolean)) {
      if (!isAbsolute(d)) throw new M365Error("INVALID_ARGUMENT", "attach_dirs must be absolute folder paths");
      let st; try { st = statSync(d); } catch { st = null; }
      if (!st?.isDirectory()) throw new M365Error("INVALID_ARGUMENT", `attach_dirs: ${d} is not a folder`);
      if (/^([a-z]:\\?|\/)$/i.test(d)) throw new M365Error("INVALID_ARGUMENT", "attach_dirs cannot be a whole drive or the root folder");
    }
    if (k === "signature_file") {
      if (!isAbsolute(v)) throw new M365Error("INVALID_ARGUMENT", "signature_file must be an absolute path");
      let st; try { st = statSync(v); } catch { st = null; }
      if (!st?.isFile() || st.size > 100 * 1024) throw new M365Error("INVALID_ARGUMENT", "signature_file must be an HTML file under 100 KB");
    }
    next[k] = k === "scope_mode" || k === "auth_mode" ? v.toLowerCase() : v;
    changed.push(k);
  }
  if (!changed.length) throw new M365Error("INVALID_ARGUMENT", `give at least one of: ${(viaTool ? SETTINGS_KEYS.filter((k) => !HUMAN_ONLY_KEYS.includes(k)) : SETTINGS_KEYS).join(", ")}`);
  const out = {};
  for (const k of SETTINGS_KEYS) if (next[k]) out[k] = next[k];
  const path = settingsPath(cfg.home);
  mkdirSync(cfg.home, { recursive: true });
  const tmp = `${path}.${process.pid}.${randomUUID()}.tmp`;
  writeFileSync(tmp, JSON.stringify(out, null, 2) + "\n", { mode: 0o600 });
  replaceFile(tmp, path);
  return { saved: changed, settings_file: join(cfg.home, "settings.json") };
}
