# odoo-plugin - decisions

Append-only log of binding decisions (house rule HR-4). Never rewrite an entry;
supersede it with a new dated entry that references the old one.

## D-001 - MCP connections: three owners, session-scoped switching, tiered approval, database auto-follow

Date: 2026-09-27
Phase: Post-2.11
Status: binding
Ships in: v2.12.0
Design: `.claude/docs/2026-09-27_odoo-mcp-connection-design.md` (marketplace repo)

Decision:

1. **Three stores, each with one owner.**
   - `~/.odoo-mcp/servers.json` (legacy `profiles.json`) and `<project>/.odoo-mcp.json`
     belong to the developer. Claude writes them only when the developer asks.
   - `~/.odoo-mcp/local/<project-key>.json` is written only by
     `scripts/mcp/local_profile.py`.
   - `~/.odoo-mcp/state/learned.json` is written only by the server.
2. **Profile schema: `tier` / `ceiling` / `start` / `approval` / `projects`.**
   - The developer's `ceiling` is absolute. No session action can exceed it.
   - Legacy keys still load: `mode`, `production`, `allow_unlink`,
     `allow_production_writes`, `project_map`.
3. **Tier `local` requires a loopback URL**, enforced at load: localhost, 127.x, ::1,
   `*.localhost`, `*.test`. That proof is what lets local profiles skip approval.
4. **Approval to raise the mode:** local `none`, staging `chat`, production `human`.
   - `chat` means the developer's verbatim answer, passed as `approved_by_user`.
   - `human` means a grant file written by `odoo_mcp_ctl.py approve`, which refuses to run
     without an interactive terminal.
   - A production profile may be set to `chat`, never to `none`.
   - Switching a session onto a production profile needs the developer's explicit yes
     even though it stays read-only.
5. **Switching is per session, in memory, through one tool (`odoo_session`).**
   - No switch or elevation writes a config file, so one session cannot change another.
   - Elevations expire: staging 60 minutes by default (max 480), production 30 (max 120).
6. **A remote profile is never auto-selected as a global default.** It is used only when
   bound to the checkout (`projects`) or chosen in the session.
7. **Local connections are created without asking.** `local_profile.py provision`:
   - refuses non-loopback targets;
   - keys the local admin through the project's own `odoo-bin shell`, with a 30-day
     expiry;
   - verifies the key before writing;
   - prunes stale entries.
8. **A renamed staging database is followed automatically.**
   - When the configured database no longer exists, the server discovers the database now
     behind the same URL (`/web/database/list`, `db.list`, or JSON-2 host selection) and
     narrows candidates with `db_pattern` or the name stem.
   - It records the new name in `learned.json` and says so in a `NOTE:`.
   - Production database changes are reported, never followed.
   - When the key then fails, the message gives the durable fix: create the MCP key in
     production, so staging builds inherit it.
9. **The server package (`mcp/`) contains no process-execution path.** The CLIs that need
   one live in `scripts/mcp/`. `tests/mcp/test_mcp_server.py` enforces both rules.
10. **Every switch, elevation, refusal, grant, database follow and non-local write is
    appended to `~/.odoo-mcp/audit.log`**, without secrets or record values.

Rationale:

The mode used to live only in the shared, credential-bearing `profiles.json`. Switching
therefore meant editing a global file, which was blocked as a security edit and silently
changed every other Claude session. A parallel session once repointed it at production
mid-task (lesson 2026-09-27). The same file accumulated a remote staging default in write
mode plus unrelated data files. The developer asked for four things:
- Claude may switch modes on request, with the developer's approval;
- Claude connects to local instances without asking;
- staging database renames are followed without manual reconfiguration;
- the file never becomes a mess.

This design delivers those while keeping the ceiling, and every remote approval, in the
developer's hands.

`chat` approval is procedural: the transcript is the record. `human` approval is stronger
but not cryptographic. A process that fakes a terminal could satisfy the check, so the skill
forbids Claude from running `approve` at all. Both limits are stated in the skill and the
design.

Non-violation of prior decisions:

- The server still never uses sudo, SQL, a shell or the filesystem for Odoo operations,
  and it keeps the privileged-model write blocklist in every tier, including local.
- Legacy profile files load unchanged. A legacy `mode: read` profile now *starts* read-only
  and can be raised within its tier's default ceiling. That default is exactly the change
  the developer asked for.

Reverse-only criteria:

Supersede, rather than edit, if any of these holds:
- Claude Code documents MCP elicitation. `human` approval should then prefer it over the
  grant file.
- The audit log shows `chat` approvals being supplied without a preceding question.
- A hosted platform exposes database discovery that names a different database than the
  one serving the URL.

Evals:

This skill ships in the existing odoo-plugin eval suite. The connection behaviour is covered
by `tests/mcp/test_mcp_connections.py` (19 cases, including a fake Odoo for database follow)
and `tests/mcp/test_mcp_server.py` (22 cases).

## D-002 - Odoo's official agent skills are fetched per project, never vendored

Date: 2026-09-28
Phase: Post-2.12
Status: binding
Ships in: v2.13.0

Decision:

1. **odoo-plugin never copies Odoo's official skills into its own tree.**
   `/official-skills` fetches the set that matches the project's Odoo branch from
   `odoo/odoo` into `<project>/.claude/skills/`, and marks each skill directory with
   `.odoo-official.json`.
2. **Installation happens only for 20.0+.** Before 20.0, `odoo/odoo` has no `skills/`, and
   the 20.0 rules contradict 14-19: `ir.access`, removed `t-esc`/`t-raw`, and
   `models.Constraint`-only constraints. The command refuses. `--branch` exists for a
   project that really targets that branch.
3. **Precedence on 20.0+ with the set installed:** the official rules are the floor, and
   odoo-plugin's reviewer and security skills add what they lack. A finding from both is
   reported once, citing the official section.
4. **Rules that also hold on older versions are restated in odoo-plugin's own words,
   version-gated and verified against the 17.0/18.0/19.0 source**: `@api.private`,
   `related_sudo`, `_allow_sudo_commands`, `SQL.identifier`, `file_open` and `consteq`.
   Their wording is never copied.

Rationale:

The official skills are high quality, authoritative and updated weekly. They are also
tied to one branch, licensed LGPL-3, and would compete with odoo-plugin's reviewer and
security skills for the same requests. Fetching keeps them exact and current and
redistributes nothing. Deferral removes the routing competition. Restating the
version-independent rules closes the gaps for the 14-19 projects the official set
cannot serve.

Non-violation of prior decisions:

- D-001 is unaffected. No MCP change.

Reverse-only criteria:

Supersede if Odoo publishes skills on a 14-19 branch (install those per branch), or ships
them as a Claude Code plugin in a marketplace (then depend on it rather than fetching).

## D-003 - MCP connections: one file, project-scoped, per-call instance routing (supersedes D-001)

Date: 2026-10-23
Phase: 4.0
Status: binding
Ships in: v4.0.0
Supersedes: D-001
Design: `.claude/docs/2026-10-23_odoo-mcp-one-file-design.md` (marketplace repo)

Why D-001 is superseded (evidence, 2026-09-29 -> 2026-10-22):

- **Six sources decided the connection**: env profile, project pin, local store, `projects`,
  local-only default, `ODOO_*`. On top came a learned-db overlay, two file names and, on
  the developer's machine, a second per-project MCP server system.
- **Legacy keys were inferred into tiers.** Every remote production profile ran as
  "staging". A `-ro` profile allowed 34 production writes. The db auto-follow re-pointed one
  production profile at another client's database.
- **Sessions switched instead of naming targets.** There were 192 `use` and 115 `mode` calls,
  and the shared default was rewritten 61 times.

Decision:

1. **One file per Windows account:** `~/.odoo-mcp/profiles.json`, `"version": 2`.
   - **Projects** own their folders (`paths`) and their **instances**.
   - Nothing else selects a connection: no pins, no local store, no learned overlay, no
     environment profile, no global default.
2. **The session folder picks the project.** A worktree counts as its main checkout, but only
   when the checkout's back-pointer confirms it. Two projects may not claim one folder.
3. **No switching.** Every tool takes an optional `instance` (`"name"` or
   `"project/instance"`), else the project default. A prod instance is the default only when
   written so. Every result is tagged `[project/instance · database · access]`.
4. **Explicit tier, single limit.**
   - A remote instance must state `tier: stage|prod`; it is never inferred.
   - `local` needs a loopback IP literal, `localhost` or `*.localhost`.
   - `access` (`read` / `write` / `full`) is the limit.
   - Production writes also need an in-memory, expiring session unlock on the developer's
     verbatim yes.
5. **Widening is the developer's call, recorded.** The developer decided on 2026-10-23 that
   Claude may widen a remote instance after their verbatim yes (`--approved-by`). Widening
   means more access, another host, prod relabelled stage, TLS checks off, or protected
   models allowed. Every widening is audited. A key never follows an instance to another host.
6. **`db: "auto"`** (local/stage) follows an Odoo.sh rebuild in memory, including mid-session.
   Fixed and production databases are never followed.
7. **The file is written only by `scripts/mcp/odoo_mcp.py`**: validated, backed up (last 10),
   atomic, `0600`. A hook blocks direct edits. Edits apply on the next call, and an invalid
   file keeps the last valid version serving.
8. **Old files load read-only** as `legacy/<name>` until `odoo_mcp.py migrate`.
   - `migrate` folds in project `.mcp.json` Odoo servers through a keyless, reviewed plan.
   - It never moves a key to another host, and reads key files only from inside the project.
9. **Removed:** `servers.json`, `.odoo-mcp.json` pins, `local/`, `learned.json`,
   `ODOO_MCP_PROFILE`, the `ODOO_URL` environment profile, `ceiling` / `start` / `approval`,
   HMAC grants, `odoo_mcp_ctl.py`, and `odoo_session use/mode/reset`.

Known limits, stated plainly:

- The unlock and `--approved-by` are procedural: they record an answer, they cannot prove
  who gave it.
- A session can read another project's instances by naming them.

Reverse-only criteria:

Supersede if Claude Code offers an approval channel the model cannot answer (for example MCP
elicitation answered by the user). Production unlocks and widenings should then move to it.

