# DevOps Plugin Architecture

## Layer Ownership

Each concern has exactly ONE owner. Other layers reference but never re-implement.

```
┌─────────────────────────────────────────────────────────────────┐
│  COMMANDS (9)                                                   │
│  commands/*.md — User entry points                              │
│  /init, /create, /workday, /log-time, /timesheet,              │
│  /standup, /sprint, /task-monitor, /cli-run                     │
└──────────────────────┬──────────────────────────────────────────┘
                       │ invoke
┌──────────────────────▼──────────────────────────────────────────┐
│  SKILL (1)                                                      │
│  devops/SKILL.md — Routing + workflows                          │
│  Owns: CLI/MCP routing matrix, 6 skill-handled workflows        │
│  References: rules/*, data/*                                    │
└──────────────────────┬──────────────────────────────────────────┘
                       │ delegate
┌──────────────────────▼──────────────────────────────────────────┐
│  AGENTS (3)                                                     │
│  agents/*.md — Specialized execution                            │
│  work-item-ops (haiku) — CRUD queries, updates                  │
│  sprint-planner (sonnet) — Reports, capacity, standup           │
│  pr-reviewer (sonnet) — PRs, diffs, threads                     │
│  References: rules/*, data/*                                    │
└──────────────────────┬──────────────────────────────────────────┘
                       │ enforced by
┌──────────────────────▼──────────────────────────────────────────┐
│  RULES (3) — Behavioral contracts                               │
│                                                                 │
│  write-gate.md      OWNS: confirmation protocol for all writes  │
│  guards.md          OWNS: tool selection, mention, repo guards  │
│  profile-loader.md  OWNS: profile loading, cache, context       │
└──────────────────────┬──────────────────────────────────────────┘
                       │ validated by
┌──────────────────────▼──────────────────────────────────────────┐
│  DATA (5) — Source of truth (JSON/MD)                           │
│                                                                 │
│  state_machine.json      OWNS: states, transitions, roles,      │
│                          required fields, business rules,        │
│                          error patterns + recovery actions        │
│  hierarchy_rules.json    OWNS: parent-child enforcement          │
│  project_defaults.json   OWNS: project aliases, URL templates,   │
│                          work tracking + staleness config         │
│  profile_template.md     OWNS: user profile structure            │
│  bug_report_template.md  OWNS: QA bug report format              │
└──────────────────────┬──────────────────────────────────────────┘
                       │ injected by
┌──────────────────────▼──────────────────────────────────────────┐
│  HOOKS (6) — Lifecycle automation                               │
│                                                                 │
│  session-start.sh       Context: profile check + staleness      │
│  pre-write-validate.sh  Context: state/hierarchy hints           │
│                         Enforce: bug creation block (exit 2)     │
│                         Enforce: close/remove restriction (exit 2)│
│                         Enforce: unresolved @mentions (exit 2)   │
│  pre-bash-check.sh      Context: commit message tips            │
│  post-bash-suggest.sh   Context: git operation suggestions      │
│  error-recovery.sh      Context: API error guidance             │
│                                                                 │
│  Rule: Hooks INJECT context. They do NOT re-implement logic.    │
│  Exception: Bug creation authority block (hard exit 2).         │
└─────────────────────────────────────────────────────────────────┘
```

## Ownership Matrix

| Concern | Owner | Type | Consumers |
|---------|-------|------|-----------|
| Write confirmation | `rules/write-gate.md` | Rule | SKILL, agents, commands |
| Tool selection | `rules/guards.md` G1 | Rule | SKILL, work-item-ops |
| Mention resolution | `rules/guards.md` G2 | Rule | SKILL, work-item-ops, hooks |
| Repo GUID resolution | `rules/guards.md` G3 | Rule | SKILL, pr-reviewer, hooks |
| State transitions | `data/state_machine.json` | Data | SKILL, work-item-ops, hooks |
| Hierarchy enforcement | `data/hierarchy_rules.json` | Data | SKILL, hooks |
| Business rules | `data/state_machine.json` | Data | SKILL, hooks |
| Bug creation authority | `data/state_machine.json` | Data | hooks (enforced exit 2) |
| Error recovery | `data/state_machine.json` (`errorPatterns`) | Data | hooks (single source of truth for all error codes) |
| Profile management | `rules/profile-loader.md` | Rule | SKILL, all agents |
| CLI/MCP routing | `devops/SKILL.md` | Skill | commands |
| WIQL/fields/limits | `devops/SKILL.md` appendix | Skill | all |

## Model Assignment

| Agent | Model | Rationale |
|-------|-------|-----------|
| work-item-ops | **Haiku** | Fast CRUD, structured queries, low reasoning |
| sprint-planner | **Sonnet** | Multi-item analysis, narrative reports |
| pr-reviewer | **Sonnet** | Code diff reasoning, risk assessment |
| Main skill | **Default** | Routing decisions, workflow orchestration |

## Anti-Patterns (Do NOT)

1. **Do NOT re-explain rules in SKILL.md or agents** — reference with file path only
2. **Do NOT add validation logic to hooks** — hooks inject reminders, rules define logic
3. **Do NOT hardcode thresholds** — put them in `data/project_defaults.json` (workTracking section)
4. **Do NOT duplicate the tool selection table** — it lives in `rules/guards.md` Guard 1 only

## Adding New Components

### New work item type
1. Add to `data/state_machine.json` → workItemTypes + rolePermissions
2. Add hierarchy rule to `data/hierarchy_rules.json` if needed
3. Run `pytest tests/` — state machine tests will catch missing fields

### New guard
1. Add to `rules/guards.md` as a new numbered guard
2. Reference from SKILL.md rules table
3. Reference from relevant agents
4. Add context injection to `hooks/pre-write-validate.sh` if detectable

### New agent
1. Create `agents/new-agent.md` with frontmatter (model, tools)
2. Add mandatory guards table referencing `rules/`
3. Add to `tests/test_consistency.py` parametrized lists

### New command
1. Create `commands/new-command.md`
2. Add to SKILL.md commands table
3. Add to `tests/test_consistency.py` EXPECTED_COMMANDS list
