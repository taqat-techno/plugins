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
