# PM Guidelines Plugin for Claude Code

> **Cross-project PM best practices enforcement — automated quality checks for status reports, dashboards, bilingual documents, and stakeholder deliverables.**

**v1.0.0** | 48 guidelines | 10 hooks | 6 skills | 2 agents

---

## What It Does

Encodes 48 real-world PM lessons learned into a 3-layer enforcement system:

| Layer | Purpose | How It Works |
|-------|---------|-------------|
| **Hooks** (10) | Real-time enforcement | Fire automatically on Write/Edit/Bash/Read/Stop events |
| **Skills** (6) | Knowledge injection | Loaded into context during document generation |
| **Agents** (2) | Batch quality review | Invoked after completing a deliverable for comprehensive audit |

**Scoped to PM directories only** — hooks only fire on files in `researches/`, `reports/`, `deliverables/`, `dashboards/`, `proposals/`, `presentations/`, and `tasks/`. Zero noise for code files.

---

## Hooks (10)

### Tier 1: Security (Block)

| Hook | Event | Behavior |
|------|-------|----------|
| `pat_token_guard` | PreToolUse (Write/Edit/Bash) | Blocks secrets: GitHub tokens, API keys, Azure PATs with context keywords |
| `source_file_protection` | PreToolUse (Write/Edit) | Blocks edits to files listed in `.pm-protected-paths` config |

### Tier 2: Quality (Advisory)

| Hook | Event | Behavior |
|------|-------|----------|
| `status_label_enforcer` | PostToolUse (Write/Edit) | Warns on "Ongoing", "independently" without specifics |
| `bilingual_parity_check` | PostToolUse (Write/Edit) | Warns on EN/AR span count mismatch |
| `dashboard_quality_check` | PostToolUse (Write/Edit) | Warns on missing source tab, live clocks |
| `html_version_naming` | PreToolUse (Write) | Warns when overwriting deliverables without `_v2` suffix |
| `html_render_reminder` | PostToolUse (Write/Edit) | Reminds to open HTML in browser after changes |

### Tier 3: Session Lifecycle (Advisory)

| Hook | Event | Behavior |
|------|-------|----------|
| `git_pull_before_analysis` | PreToolUse (Read) | Warns if reading data files before running `git pull` |
| `search_index_rebuild` | PostToolUse (Bash) | Reminds to rebuild search index after `git pull` |
| `session_end_lessons` | Stop | Prompts for lesson capture at session end |

---

## Skills (6)

| Skill | Model | Purpose |
|-------|-------|---------|
| `pm-report-writing` | Sonnet | Report quality: specificity, consistent labels, email 3-version pattern |
| `pm-dashboard-design` | Sonnet | Dashboard design: auto-scoring, source tabs, modular CSS, pipelines |
| `pm-session-discipline` | Sonnet | Session workflow: memory vs tasks, lesson capture, pull-before-analyze |
| `pm-bilingual-standards` | Sonnet | Bilingual EN/AR: data-i18n, RTL CSS, paired spans, language toggle |
| `pm-estimation` | Opus | Effort estimation: SP scales, person-months, AI multipliers, variance tables |
| `pm-consolidation` | Opus | Multi-source merge: conflict tracking, gap classification, source attribution |

---

## Agents (2)

| Agent | Model | Skills Preloaded | Purpose |
|-------|-------|-----------------|---------|
| `pm-report-reviewer` | Opus | pm-report-writing, pm-dashboard-design, pm-bilingual-standards | Batch review of completed PM deliverables with quality score and violation list |
| `pm-bilingual-qa` | Opus | pm-bilingual-standards | Deep structural validation of bilingual EN/AR HTML files |

Both agents are **read-only** (tools: Read, Grep, Glob). They never modify files.

---

## Configuration

### Protected Source Files

Create a `.pm-protected-paths` file in your project root to block edits to source analysis files:

```
# One glob pattern per line
**/S1/*
**/S2/*
**/source-analysis/*
```

The `source_file_protection` hook reads this file and blocks any Write/Edit to matching paths. If no config file exists, the hook is a no-op.

### PM Directories

Hooks only fire on files in these directories:

- `researches/`
- `reports/`
- `deliverables/`
- `dashboards/`
- `proposals/`
- `presentations/`
- `tasks/`

Files outside these directories are never checked.

---

## Plugin Structure

```
pm-guidelines-plugin/
├── .claude-plugin/
│   └── plugin.json
├── .gitignore
├── README.md
├── agents/
│   ├── pm-report-reviewer.md
│   └── pm-bilingual-qa.md
├── hooks/
│   ├── hooks.json
│   ├── pm_utils.py
│   ├── pat_token_guard.py
│   ├── source_file_protection.py
│   ├── status_label_enforcer.py
│   ├── bilingual_parity_check.py
│   ├── dashboard_quality_check.py
│   ├── html_version_naming.py
│   ├── html_render_reminder.py
│   ├── git_pull_before_analysis.py
│   ├── search_index_rebuild.py
│   └── session_end_lessons.py
├── pm-report-writing/
│   └── SKILL.md
├── pm-dashboard-design/
│   └── SKILL.md
├── pm-session-discipline/
│   └── SKILL.md
├── pm-bilingual-standards/
│   └── SKILL.md
├── pm-estimation/
│   └── SKILL.md
└── pm-consolidation/
    └── SKILL.md
```

---

## Guidelines Covered

The 48 guidelines are organized into domains:

| Domain | Guidelines | Components |
|--------|-----------|------------|
| Report Quality | 1-4 | pm-report-writing skill, status_label_enforcer hook |
| Status Labels | 5-7 | pm-report-writing skill, status_label_enforcer hook |
| Bilingual EN/AR | 8-10, 33 | pm-bilingual-standards skill, bilingual_parity_check hook |
| Email Drafting | 11-13 | pm-report-writing skill |
| HTML Deliverables | 14-15 | html_render_reminder hook, html_version_naming hook |
| Data Validation | 16-18 | pm-estimation skill |
| OKR/KPI Dashboards | 19-21 | pm-dashboard-design skill, dashboard_quality_check hook |
| Search Index | 22-23 | search_index_rebuild hook |
| Project Estimation | 24-27 | pm-estimation skill |
| DevOps Integration | 28-35 | pm-dashboard-design skill, pat_token_guard hook |
| Session Workflow | 28b-31b, 36-38 | pm-session-discipline skill, git_pull_before_analysis hook, session_end_lessons hook |
| Data Analysis | 32b-35b | pm-estimation skill |
| Consolidation | 39-42, 48 | pm-consolidation skill, source_file_protection hook |
| Portal Architecture | 43-47 | pm-dashboard-design skill |

---

## License

MIT - TaqaTechno
