# DevOps Plugin

**Package:** `devops` · **Version:** `6.3.0` · **Category:** productivity · **License:** MIT · **Source:** [`devops-plugin/`](../../devops-plugin/) · **MCP server:** `azure-devops` (via `@azure-devops/mcp`)

## Purpose

Complete Azure DevOps integration for Claude Code via a **HYBRID CLI + MCP architecture**. Enables natural-language interaction with work items, pull requests, pipelines, repos, and wiki while enforcing TAQAT Techno's business rules (role-based state machine, user-story format, sprint assignment, time-tracking discipline).

## What it does

- **Work items:** create, update, query, link, add comments, batch operations. Enforces hierarchy (Epic > Feature > User Story/PBI > Task | Bug | Enhancement) and state-transition permissions by role (Developer, QA/QC, PM/Lead).
- **Pull requests:** create, review, approve, thread management, reviewer assignment, diff analysis.
- **Pipelines:** run, monitor, view logs, update build stages, list runs.
- **Repos:** create branches, list repos, search commits, search code, link work items to PRs.
- **Wiki:** search, list pages, read page content, create or update pages.
- **Sprint management:** capacity planning, iteration management, team member assignments, standup reports.
- **Time tracking:** log hours against work items, manage time-off, generate timesheets (local-only — no API writes for time).

## How it works (HYBRID architecture)

The plugin combines two interfaces:

1. **CLI** (`mcp__plugin_devops_azure-devops__*` is a small part; CLI handles high-volume ops) — via `/cli-run` command, Claude shells out to `az devops` commands when the MCP tool doesn't cover the operation or when batch efficiency matters.
2. **MCP server** (Azure DevOps MCP — registered via plugin-level `.mcp.json`) — 100+ tools for natural-language queries, single-item fetches, and analytical workflows.

Routing decisions live in the agents (`work-item-ops`, `sprint-planner`, `pr-reviewer`) — each is tuned to a model tier (Haiku for high-volume CRUD, Sonnet for analytical work).

### Layer ownership

Per [`devops-plugin/ARCHITECTURE.md`](../../devops-plugin/ARCHITECTURE.md):

```
commands/  →  skills/ (N/A — devops uses agent-first)  →  agents/  →  rules/  →  data/
```

- `rules/` contains behavior contracts (`rules/profile-loader.md`, `rules/tool-selection-guard.md`, `rules/write-gate.md`). Agents and commands reference rules; they never duplicate them.
- `data/state_machine.json` is the single source of truth for state transitions. Both agents and commands read it; neither hardcodes the machine.

## Commands (9)

| Command | Agent / layer | Purpose |
|---|---|---|
| `/init` | dispatcher | One-time setup: install CLI + MCP, configure auth, validate connectivity |
| `/init profile` | dispatcher | Generate persistent user profile (role, team GUID, project defaults) |
| `/create` | `work-item-ops` agent | Unified work-item creation — auto-detects type (task/bug/enhancement/user-story) from context |
| `/workday` | dispatcher | Daily login dashboard — tasks, hours, compliance flags, optional `--sync` / `--tasks` / `--todo` |
| `/standup` | dispatcher | Generate daily standup notes from yesterday's work item activity |
| `/sprint` | `sprint-planner` agent | Sprint progress summary; `--full` for hybrid report with builds, tests, PRs, security |
| `/log-time` | dispatcher | Log working hours against work items or general categories |
| `/timesheet` | dispatcher | View time-tracking status, manage time-off — local only, no API calls |
| `/cli-run` | dispatcher | Execute arbitrary Azure DevOps CLI commands for automation/batch operations |
| `/task-monitor` | dispatcher (periodic) | Alerts on new work item assignments — use with `/loop 15m /task-monitor` |

## Agents (3)

| Agent | Model tier | Role |
|---|---|---|
| `work-item-ops` | haiku | High-volume CRUD on work items; enforces tool selection guard + write-gate |
| `sprint-planner` | sonnet | Analytical — sprint capacity, burndown, velocity, risk analysis |
| `pr-reviewer` | sonnet | Pull request analysis, review threads, diff reasoning, repository resolution |

## Business rules (enforced)

All rules defined in `data/state_machine.json`. Documented in [`devops-plugin/README.md`](../../devops-plugin/README.md) §Business-Rules:

| Rule | Description |
|---|---|
| **Hierarchy** | Epic > Feature > User Story/PBI > Task \| Bug \| Enhancement — parent required |
| **User Story format** | How? > What? > Why? sequence in the title |
| **State transitions** | Role-based permissions; PBI must pass through "Ready for QC" before "Done" |
| **Task prefixes** | Fetched from Azure DevOps project settings (e.g., `[Dev]`, `[Front]`, `[IMP]`, `[QC Bug Fixing]`, `[QC Test Execution]`) |
| **Auto-Sprint** | Tasks auto-assigned to the current sprint by date |
| **Task completion** | Requires Original Estimate + Completed Hours |
| **Bug completion** | Requires Completed Work + Resolved Reason |
| **Bug creation** | QA/QC roles only; developers create `[Dev-Internal-fix]` Tasks instead |
| **State permissions** | Role-based transition matrix (Developer, QA/QC, PM/Lead) |

## Inputs and outputs

**Inputs:**
- `/create` — natural-language description of the work item (type auto-detected from context and hierarchy).
- `/sprint` — iteration name or default (current sprint).
- `/log-time` — work item ID + hours + optional description.

**Outputs:**
- Work item IDs, URLs, structured status reports, sprint burndown tables, standup markdown.

## Configuration

Configuration flows through `/init` and `/init profile`:

1. **Azure DevOps organization:** set at `/init` time; persisted.
2. **User profile:** role (Developer / QA-QC / PM-Lead), team GUID, project defaults. Generated by `/init profile`.
3. **Authentication:** via Azure CLI (`az login`). MCP server picks up credentials from env.
4. **Time-tracking:** local-only at `~/.claude/devops-plugin/timesheet/` (JSONL). Opt-in; no network egress.

## Dependencies

- **Azure CLI** (`az`) with the `azure-devops` extension.
- **Node.js + npx** for the `@azure-devops/mcp` server.
- **Python 3.10+** for plugin scripts.
- **Read/write access** to the target Azure DevOps organization.

## Usage examples

```
"Create a task: Fix the login redirect bug in auth module"
→ /create
  (agent detects Task type, infers parent User Story, assigns current sprint, 
   prefixes [Dev-Internal-fix] for developer role, asks for Original Estimate)

"What's on my plate today?"
→ /workday

"Generate my standup notes"
→ /standup

"Review PR 4521"
→ pr-reviewer agent is invoked with the PR URL

"Start tracking 3 hours on task 12345 for backend refactor"
→ /log-time 12345 3 "backend refactor"

"Give me a full sprint report for the current iteration"
→ /sprint --full
```

## Known limitations

- **Single organization at a time.** Multi-org workflows require switching via `/init` re-run.
- **Time tracking is local.** No API write to Azure DevOps time-entry endpoints — the local JSONL is the truth. By design (privacy + offline support).
- **Role permissions are client-enforced.** The plugin enforces them in agent behavior; Azure DevOps itself still has its own RBAC that takes precedence server-side.
- **MCP server is npx-launched.** First invocation after `/plugins` install has a cold-start cost (~5–10s) while npx downloads the package.

## Related plugins and integrations

- **odoo** — link Odoo development sprints to DevOps work items via `/create --link <odoo-ref>`.
- **rag** — search internal runbooks/SOPs while triaging PRs (via ragtools MCP — separate plugin).
- **ntfy** — push `/task-monitor` alerts to phone.

## See also

- Source: [`devops-plugin/README.md`](../../devops-plugin/README.md) — commands, business rules, setup
- [`devops-plugin/ARCHITECTURE.md`](../../devops-plugin/ARCHITECTURE.md) — layer ownership, single-owner rule
- [`devops-plugin/CHANGELOG.md`](../../devops-plugin/CHANGELOG.md) — v2.0 → v6.3 evolution (command consolidation wave, persistent profile, role-based state machine)
- [`devops-plugin/data/state_machine.json`](../../devops-plugin/data/state_machine.json) — the state transition truth
