// util.mjs - small helpers shared by the server: the error type and the atomic file replace.
import { renameSync, unlinkSync } from "node:fs";

/** A failure with a stable code and a short, secret-free message (and optional hint) the agent can act on. */
export class GoogleError extends Error {
  constructor(code, message, extra = {}) {
    super(message);
    this.name = "GoogleError";
    this.code = code;
    Object.assign(this, extra);
  }
}

/** Atomically replace dest with tmp. On Windows a rename fails for a moment (EPERM/EACCES/EBUSY) while another
 *  process or a virus scanner has dest open, so it is retried briefly instead of failing. */
export function replaceFile(tmp, dest) {
  for (let i = 0; ; i++) {
    try { renameSync(tmp, dest); return; }
    catch (e) {
      if (!["EPERM", "EACCES", "EBUSY"].includes(e.code) || i >= 40) { try { unlinkSync(tmp); } catch { /* gone */ } throw e; }
      Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 10 + i * 5);
    }
  }
}

/** The CLI command for a hint: GOOGLE_CLI_COMMAND when set, else the given default text. */
export const cliCmd = (cfg, dflt = "node server/cli.mjs") => (cfg?.cliCommand ? cfg.cliCommand : dflt);
