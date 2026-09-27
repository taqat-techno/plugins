# Odoo MCP connections — design (2026-09-27)

**Goal.** One MCP setup that serves local investigation and implementation, and staging
and production work, for any developer and any number of projects.
- The **developer decides the configuration and its limits.**
- **Claude can switch profile or mode on request**, with the developer's approval scaled to
  the risk.
- **Claude creates local connections itself**, without asking.
- **The config never becomes a mess.**

---

## 1. Why Claude cannot switch today

| Cause | Effect |
|---|---|
| Read/write lives only in `mode` inside `~/.odoo-mcp/profiles.json` | The only way to switch is to edit a hand-maintained file outside the project |
| That file holds live API keys (the current one is literal, not `${ENV}`) | Editing it counts as editing a credential/security file, so it is blocked or judged risky |
| That file is **global**: every Claude session on the machine reads it | A switch for one task silently changes every other session. A parallel session once repointed it at production mid-task (lesson 2026-09-27) |
| There is no session-level state and no approval concept in the server | There is nothing safe to call, so "switch to write" has no sanctioned path |

What the current machine state shows:
- `default` is a remote staging profile with `write` and `allow_unlink`, so every project
  that has no mapping connects to staging in write mode.
- `seed.json` and `master_data.yml` files sit next to the config.

This is the mess, already happening.

## 2. Principles

1. **Three owners, three lifetimes.** The developer owns *servers*, Claude owns *locals*,
   and a *session* lives in memory. Nobody writes another owner's file.
2. **The developer sets the ceiling; Claude moves inside it.** A profile declares the most
   it may ever do. Claude can raise or lower the session mode up to that ceiling, and never
   above it.
3. **Approval scales with the tier:**
   - local: none;
   - staging: an explicit developer "yes" in chat;
   - production: an approval the model structurally cannot produce.
4. **"Local" is proven, not labelled.** Only a loopback host (`localhost`, `127.0.0.1`,
   `::1`, `*.localhost`, `*.test`) can be tier `local`. Code enforces this.
5. **Nothing Claude does changes another session.** Switches and elevations are
   in-memory, per MCP server process.

## 3. Layout

```
~/.odoo-mcp/
  servers.json              developer-owned: staging, production, shared instances. Claude never writes it.
  local/<project-key>.json  Claude-owned: one file per project checkout, auto-created, auto-pruned.
  grants/                   short-lived human approvals for 'human' tier; written only by the approve CLI.
  audit.log                 JSONL: every switch, elevation, grant and write. No secrets.
<project>/.odoo-mcp.json    optional project pin (existing behaviour, still git-ignored).
```

`profiles.json` is still read as the servers file, so nothing breaks. Renaming it to
`servers.json` is optional.

## 4. Profile schema (servers)

```json
{
  "profiles": {
    "acme-staging": {
      "url": "https://acme-stage.example.com",
      "db": "acme_stage",
      "username": "mcp_agent",
      "api_key": "${ACME_STAGE_KEY}",
      "tier": "staging",
      "ceiling": "write",
      "start": "read",
      "approval": "chat",
      "projects": ["~/work/acme"]
    },
    "acme-prod": {
      "url": "https://erp.acme.example.com",
      "db": "acme",
      "username": "mcp_readonly",
      "api_key": "${ACME_PROD_KEY}",
      "tier": "production",
      "ceiling": "read",
      "approval": "human",
      "projects": ["~/work/acme"]
    }
  }
}
```

| Key | Meaning | Default |
|---|---|---|
| `tier` | `local` / `staging` / `production`. `production: true` (old key) implies `production` | `staging` for a remote URL |
| `ceiling` | The most this profile may ever do: `read`, `write` or `write+unlink` | Taken from the old `mode` / `allow_unlink` / `allow_production_writes` |
| `start` | The mode a session starts in | `read` (local: `write`) |
| `approval` | What raising the mode needs: `none`, `chat` or `human` | local `none`, staging `chat`, production `human` |
| `projects` | Checkouts this profile serves (replaces `project_map`) | none |
| `allow_write_models` | Unchanged: escape hatch for the privileged-model blocklist | none |

Validation, all enforced in code:
- tier `local` with a non-loopback URL is an error;
- `production` with `approval: none` is an error;
- `production` with `verify_ssl: false` is an error, as today.

## 5. Which profile a session uses

This order is shown in `odoo_status` with the reason:

1. the session's explicit choice (`odoo_session use`);
2. `<project>/.odoo-mcp.json`;
3. **the local auto-profile for this project** (`~/.odoo-mcp/local/…`);
4. a server profile whose `projects` contains this checkout (longest path wins);
5. `servers.json` `default`, **but only if it is tier `local`**;
6. `ODOO_URL` / env variables.

A remote profile is never picked by accident: it has to be bound to the project or chosen
in the session.

## 6. Session control: one new tool, `odoo_session`

The server goes from 10 tools to 11. Breadth lives in parameters, as today.

| Action | Effect |
|---|---|
| `list` | Every profile available here: tier, ceiling, approval, and which one is active and why |
| `use <profile>` | Switch the connection for **this session only** |
| `mode <read\|write\|write+unlink>` | Raise or lower this session's mode within the ceiling. Optional: `ttl_minutes`, `models` (restrict writes to these), `reason` |
| `reset` | Back to the resolved profile at its `start` mode |

| | local | staging (`chat`) | production (`human`) |
|---|---|---|---|
| `use` | free | free, read-only | human approval |
| raise mode within ceiling | free | developer "yes" in chat | human approval |
| above ceiling | refused | refused | refused: only the developer edits `servers.json` |
| elevation lifetime | whole session | 60 min default | 30 min default |

**`chat` approval.**
1. Claude asks the developer, with AskUserQuestion for example.
2. The call carries `approved_by_user`: the developer's answer, verbatim.
3. The server refuses the call without it and writes the answer to `audit.log`.

This is a procedural gate. The transcript is the record. It matches "switch it when I ask"
with no extra friction.

**`human` approval** is something the model cannot fabricate:
- **MCP elicitation**, if the client advertises it at `initialize`. The server asks the
  human directly, and Claude cannot answer. This is not documented for Claude Code today, so
  the server checks for it at runtime.
- **Otherwise, a grant file.** The developer runs
  `python <plugin>/mcp/odoo_mcp_ctl.py approve acme-prod write --ttl 30` in their own
  terminal. The CLI **refuses without an interactive TTY**, and Claude's Bash tool has none.
  The grant is profile-scoped and expires. The server reads it on the next `mode` call.

Claude Code permission prompts on `odoo_session` are an extra layer where they exist. They
are not relied on, because bypass mode never prompts.

## 7. Local connections, created by Claude without asking

**Trigger.** Claude needs live data from a local instance, and no local profile exists for
this project. `odoo_status` then reports `local_candidate` with the discovered conf, port and
database.

**Provisioning** runs as a separate script,
`mcp/local_profile.py provision [--conf X] [--db Y]`, which Claude runs with Bash. The MCP
server keeps its "no shell" guarantee.

1. Discover the project's Odoo conf(s), then its `http_port`, `db_name` and `dbfilter`.
2. **Refuse unless the target is loopback.**
3. Confirm Odoo answers on `127.0.0.1:<port>`. If the database is not pinned, list the
   databases and take the conf's database. If several match, create one profile per
   candidate and let the task pick.
4. Create an API key through the project's own `odoo-bin shell`
   (`res.users.apikeys._generate('rpc', 'claude-mcp-local', <expiry>)`) for the local user.
   The expiry is 30 days on Odoo 17+. No passwords are stored.
5. Write `~/.odoo-mcp/local/<project-key>.json` atomically, with project dir, conf, db,
   url, user, key, `created_at`, `expires_at`, Odoo version and `last_used`.
6. `odoo_status` reloads it. There is no restart.

Local profiles start in `write` with approval `none`. `write+unlink` also needs no approval
locally. The privileged-model blocklist (`res.users`, `ir.rule`, …) still applies locally,
because it protects against mistakes, not intruders.

**Pruning** (`local_profile.py prune`) removes a local profile when any of these holds:
- the project directory is gone;
- the database no longer exists;
- the key has expired;
- it has been unused for 30 days.

It runs on every provision and via `/mcp-setup doctor`.

## 8. Anti-mess rules

1. One owner per file. Claude never writes `servers.json`, and the developer never needs to
   touch `local/`.
2. Local profiles are one file per project, with deterministic names
   (`local:<project>/<db>`). The shared file never grows with throwaway databases.
3. Local keys expire and stale entries are pruned automatically.
4. `odoo_status` and `/mcp-setup doctor` warn about:
   - a remote `default`;
   - a literal (non-`${ENV}`) key in `servers.json`;
   - a production profile with a write ceiling;
   - any non-config file in `~/.odoo-mcp`, because seed and master-data files belong in
     the project.
5. `audit.log` answers "who switched what, when, and on whose approval" without anyone
   inspecting config.

## 9. Migrating this machine (with your approval, not automatically)

- Keep `profiles.json` (it is read as the servers file).
- The current staging profile becomes:
  - `tier: staging`
  - `ceiling: write+unlink`
  - `start: read`
  - `approval: chat`
  - `projects: [<its checkout>]`
- Move its key to an environment variable, and drop `default`.
- Move `medline-stage.seed.json` and `medline-staging.master_data.yml` into that project's
  `.claude/docs/`.

## 10. Implementation

| File | Change |
|---|---|
| `mcp/profiles.py` | `tier` / `ceiling` / `start` / `approval` / `projects`; loopback proof; local dir; new resolution order; legacy-key mapping |
| `mcp/session_state.py` (new) | In-memory active profile, mode, TTL, write-model scope; grant-file reader; elicitation hook |
| `mcp/guards.py` | Gate on the *session* mode, not the file mode; approval checks; audit writes |
| `mcp/tools.py` | `odoo_session` tool; `odoo_status` shows the resolution reason, elevation and warnings |
| `mcp/server.py` | Record the client's `elicitation` capability; server→client request plumbing |
| `mcp/local_profile.py` (new) | `provision` / `list` / `prune` |
| `mcp/odoo_mcp_ctl.py` (new) | `approve` (TTY-only) / `revoke` / `audit` |
| `commands/mcp-setup.md`, `skills/mcp/SKILL.md`, `mcp/README.md`, `config/*.example` | New model, auto-local behaviour, approval rules |
| `tests/mcp/test_mcp_server.py` (+ new) | Loopback proof, ceiling, approvals, TTL expiry, session isolation, prune, TTY refusal, legacy file compatibility, tool count = 11 |
| `docs/decisions.md` | D-NNN for the approval tiers and the three-owner layout (HR-4) |

---

## 11. Decisions taken (2026-09-27) and what shipped (odoo 2.12.0)

| Question | Decision |
|---|---|
| Staging write approval | The developer's yes in chat (`approved_by_user`, verbatim) |
| Production write approval | `human` (terminal grant) by default. The developer may set `chat` per profile, never `none` |
| Remote global default | Never auto-selected. Only a local-tier profile can be a default |
| Local key owner | The local admin, on loopback instances only |

**Added after review: database auto-follow.**
- When the configured database is gone (an Odoo.sh staging rebuild or restore renamed it),
  the server lists what the same URL now serves (`/web/database/list`, `db.list`, or JSON-2
  host selection). It narrows the candidates with `db_pattern` or the old name's stem, and
  switches to the one left.
- It records the new name in `~/.odoo-mcp/state/learned.json`, keyed by profile and url, and
  prints a `NOTE:`.
- Production changes are reported, never followed.
- If the key is rejected afterwards, the message gives the durable fix: create the MCP key in
  production, so every staging build inherits it.

**Placement change during implementation.** `local_profile.py` and `odoo_mcp_ctl.py` live in
`scripts/mcp/`, not `mcp/`. The server package keeps its tested "no process execution"
guarantee.

**Elicitation** (the server asking the human directly) is not documented for Claude Code, so
it was not built. It is listed as a reverse-only criterion in `odoo-plugin/docs/decisions.md`
D-001.
