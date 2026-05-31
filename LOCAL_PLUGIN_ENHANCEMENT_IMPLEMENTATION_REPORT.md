# Local Plugin Enhancement Implementation Report

> **Execution of** `OFFICIAL_PLUGINS_COVERAGE_AUDIT.md` + `LESSONS_TO_PLUGINS_GLOBAL_RECOMMENDATION_PLAN.md`. Local edits only — **no push, no PR, no remote mutation, no official-plugin edits**. The `plugins/` workspace is **not a git repo**, so changes are on disk (unstaged); exact files listed below. Date: 2026-05-31.

## 1. Summary of changes

- **1 new plugin built:** `claude-env-doctor` (v0.1.0) — the genuinely-uncovered capability from the audit.
- **1 plugin renamed + broadened:** `react-admin-kit` → **`react-kit`** (v0.3.0), scope generalized to all React/Next.js patterns (admin = one capability).
- **5 plugins enhanced** with only the capabilities official plugins do **not** cover: `qa-browser` (v0.3.0), `docs-wiki` (v0.3.0), `devops` (v6.4.0), `odoo` (v2.1.0), `rag` (v0.13.2).
- **4 plugins untouched** (per brief): `ntfy`, `pandoc`, `remotion`, `paper`.
- **Marketplace** updated: 10 → **11 plugins** (rename + new entry).
- **No official-plugin duplication**: plugin-authoring, static/diff security review, GitHub PR/commit/API, and the raw browser engine were deliberately **not** rebuilt — they are consumed from official plugins (`plugin-dev`, `security-guidance`, `code-review`/`commit-commands`/`github`, `playwright`).
- **Skill-first**: 7 new skills + 6 reference docs + 5 rule/reference docs + 7 page templates + 1 thin command + 1 read-only agent + 1 non-blocking hook. Commands stayed thin; hooks stayed minimal.
- **Validation:** 0 errors on all 7 touched plugins. **Genericness sweep:** clean. **Secrets:** none.

## 2. Plugins created

### claude-env-doctor (v0.1.0) — `plugins/claude-env-doctor-plugin/`
Generic local-environment doctor for Claude Code. **Diagnoses, never blindly mutates.** Registered in `marketplace.json` as `claude-env-doctor` (`./claude-env-doctor-plugin`, category productivity). Scope is strictly local environment diagnosis — **not** server ops, deployment runbooks, or GitHub/DevOps workflow logic.

## 3. Plugins renamed

### react-admin-kit → react-kit (v0.2.0 → v0.3.0) — `plugins/react-kit-plugin/`
- Folder renamed; single-token swap `react-admin-kit` → `react-kit` across 7 files (UTF-8, no BOM); cache file `.react-admin-kit.local.json` → `.react-kit.local.json`.
- `plugin.json` name/homepage/description/keywords updated; broadened to general React/Next.js scope.
- `marketplace.json` entry renamed + re-described + `source: ./react-kit-plugin`.
- The 8 existing `admin-*` skills (the admin-capabilities cluster) are **preserved unchanged**; commands `/admin-scaffold`, `/admin-audit`, `/admin-role-matrix` kept (admin-scoped commands inside a broader kit).

## 4. Plugins enhanced

| Plugin | Ver | What was added (uncovered-by-official only) |
|---|---|---|
| react-kit | 0.3.0 | 3 React-quality skills (below) + broadened README |
| qa-browser | 0.3.0 | live identity/RBAC proof + host-scoped headers + destructive-safety hardening |
| docs-wiki | 0.3.0 | source-of-truth doctrine skill + 7 page templates |
| devops | 6.4.0 | provider-neutral remote-write gate + CI-hardening checklist (Azure core untouched) |
| odoo | 2.1.0 | Odoo i18n/PO + volume/PG + theme-load reference docs |
| rag | 0.13.2 | doctor command defers generic MCP diagnosis to claude-env-doctor |

## 5. Files changed/created per plugin

**`.claude-plugin/marketplace.json`** — renamed `react-admin-kit`→`react-kit` entry; added `claude-env-doctor` entry (11 plugins total).

**claude-env-doctor-plugin/ (NEW):**
- `.claude-plugin/plugin.json`, `LICENSE`, `README.md`, `CHANGELOG.md`
- `commands/env-doctor.md` (thin, runs with no args)
- `skills/env-doctor/SKILL.md` + `references/{mcp-not-loading,windows-wsl,login-auth,lsp-node-spawn,python-encoding,playwright-browser}.md`
- `agents/env-probe-reporter.md` (read-only)
- `hooks/hooks.json` + `hooks/session_start_env_advisory.py` (non-blocking advisory)

**react-kit-plugin/:**
- NEW `skills/react-lint-triage/SKILL.md`, `skills/data-fetching-states/SKILL.md`, `skills/react19-migration/SKILL.md`
- EDITED `README.md` (broadened), `CHANGELOG.md` (0.3.0), `.claude-plugin/plugin.json` (v0.3.0)
- RENAMED-token: `agents/admin-route-auditor.md`, `commands/{admin-audit,admin-role-matrix,admin-scaffold}.md`

**qa-browser-plugin/:**
- NEW `skills/verify-identity-and-rbac/SKILL.md`, `skills/host-scoped-auth-headers/SKILL.md`
- EDITED `skills/safe-destructive-testing/SKILL.md` (external side-effects + cancel-first), `.claude-plugin/plugin.json` (v0.3.0), `CHANGELOG.md`
- VERIFIED (no change) `hooks/pre_navigate_prod_gate.py` — already case-insensitive

**docs-wiki-plugin/:**
- NEW `skills/wiki-source-of-truth/SKILL.md`
- NEW `templates/{README,sop,runbook,role-guide,user-manual,workflow,release-handover,onboarding}.md`
- EDITED `.claude-plugin/plugin.json` (v0.3.0), `CHANGELOG.md`

**devops-plugin/:**
- NEW `rules/git-remote-write-gate.md`, `devops/CI_HARDENING.md`
- EDITED `rules/write-gate.md` (cross-ref), `.claude-plugin/plugin.json` (v6.4.0), `CHANGELOG.md`

**odoo-plugin/:**
- NEW `skills/i18n/references/po-gettext-discipline.md`, `skills/docker/references/volume-and-pg-safety.md`, `skills/upgrade/references/theme-load-and-cli-upgrade.md`
- EDITED `.claude-plugin/plugin.json` (v2.1.0), `CHANGELOG.md`

**rag-plugin/:**
- EDITED `commands/doctor.md` (defer generic MCP → claude-env-doctor), `.claude-plugin/plugin.json` (v0.13.2), `CHANGELOG.md`

## 6. Skills added/updated

| Skill | Plugin | Owns |
|---|---|---|
| `env-doctor` (+6 references) | claude-env-doctor | diagnose-don't-mutate discipline; symptom→branch router; failure taxonomy; ENVIRONMENT REPORT contract; secret redaction |
| `react-lint-triage` | react-kit | classify findings (safe-mechanical/needs-judgment/false-positive/forbidden-zone); never chase score; FP catalog |
| `data-fetching-states` | react-kit | status→state contract (403→access-required, 404→not-found, 400/409→business-rule); no empty shell on access error |
| `react19-migration` | react-kit | forwardRef→ref-prop, useContext→use, server/client metadata split; behavior-preserving |
| `verify-identity-and-rbac` | qa-browser | auth-endpoint over UI labels; 401/403 vs 400/409 proof; Shape A/B |
| `host-scoped-auth-headers` | qa-browser | host-scoped header injection; CORS-leak avoidance |
| `wiki-source-of-truth` | docs-wiki | knowledge-layer order; current-vs-target; stale-checkbox distrust; config drift |
| `safe-destructive-testing` (enhanced) | qa-browser | + external side-effect scope-out + cancel-first |

## 7. Commands added/updated
- NEW `/env-doctor` (claude-env-doctor) — thin, **works with no arguments** (bare invocation = general triage); optional `[symptom]` routes faster.
- EDITED `/doctor` (rag) — generic MCP-not-loading now defers to claude-env-doctor.
- (No command-name changes in react-kit; `admin-*` commands kept as admin-scoped entries.)

## 8. Hooks added/updated
- NEW `claude-env-doctor` SessionStart advisory (`session_start_env_advisory.py`) — non-blocking, utf-8-safe, ASCII one-liner, always exits 0. Wired via `hooks/hooks.json` using `${CLAUDE_PLUGIN_ROOT}`.
- VERIFIED `qa-browser/pre_navigate_prod_gate.py` already lowercases host before matching — **no change** (avoided a needless edit).

## 9. Agents added/updated
- NEW `env-probe-reporter` (claude-env-doctor) — read-only (`Read, Bash, Glob, Grep`; no Edit/Write), redacts secrets, mutates nothing, emits the ENVIRONMENT REPORT.

## 10. Validation commands and results

`PYTHONIOENCODING=utf-8 python validate_plugin.py <plugin>` (lesson L1567 for emoji output):

| Plugin | Errors | Notes |
|---|---|---|
| claude-env-doctor | **0** | warnings: command author/version (marketplace-wide convention), hooks.json `description`/`hooks` (documented benign quirk) |
| react-kit | **0** | ✅ passes all checks |
| qa-browser | **0** | benign hook quirk only |
| docs-wiki | **0** | benign hook quirk only |
| devops | **0** | warnings all pre-existing (untouched commands/agents) |
| odoo | **0** | suggestions only |
| rag | **0** | warnings all pre-existing |

All 7 touched plugins: **0 errors**. The 2 `hooks.json` "unknown top-level key" warnings are the known validator quirk noted in `CLAUDE.md` (every hook-bearing plugin in the marketplace shows them).

## 11. Genericness sweep result

`grep -rniE "aqraboon|royal.preps|almajal|khairgate|openclaw|adahi|beneficiar|coupon|qid|qatar"` over all new/changed content + absolute-path sweep (`C:\Users\…`, `/home/…`, `LAKOSHA-HOME`) + secret-shape sweep (`sk-ant-`, `ghp_`, `github_pat_`, bypass tokens, `AKIA…`):
- **Project/business tokens:** clean. Only hits are pre-existing CHANGELOG lines that *describe* the sweep methodology (the token list itself), not behavior.
- **Absolute user paths:** none.
- **Secrets/credentials:** none.
- All artifacts are adapter-driven; any concrete value is a labeled illustrative example.

## 12. Official-plugin duplication avoided

| Official capability | Official plugin(s) | How we avoided rebuilding it |
|---|---|---|
| Plugin/skill/hook/MCP authoring | plugin-dev, skill-creator, mcp-server-dev, hookify | No authoring plugin built |
| Static + diff security review, secrets, injection | security-guidance | qa-browser owns only **live** RBAC proof; static security left to official |
| Browser automation engine + evidence | playwright, chrome-devtools-mcp | qa-browser is a methodology layer; references official transport |
| GitHub PR/review/commit/API | code-review, pr-review-toolkit, commit-commands, github | devops added only a provider-neutral **safety gate** + CI **checklist**, not GitHub features |
| Generic env recommend (setup) | claude-code-setup | claude-env-doctor does **diagnosis/repair** (the inverse), no overlap |

## 13. Remaining follow-ups

1. **Adopt official plugins** (config, not code): enable/document `plugin-dev`, `security-guidance`, `playwright`, `code-review`, `commit-commands` (Scenario A of the coverage audit).
2. **devops hook-wiring drift** (pre-existing): `session-start.sh`, `pre-bash-check.sh`, `post-bash-suggest.sh` exist but are not wired in `hooks/hooks.json`. **Reported, not changed** — rewiring SessionStart/Bash hooks changes runtime behavior and needs a deliberate decision; out of safe scope for this pass.
3. **wiki-memory-sync** — remains deferred (design as a `claude-md-management`-aligned source adapter; build after docs-wiki stabilizes).
4. **Optional polish** (suggestions only, non-blocking): add `allowed-tools`/`metadata`/`version` to new SKILLs; odoo could add a `LICENSE` file (has `LICENSES.md`).

## 14. Blocked / skipped work and why

- **prod-gate hook edit — skipped (intentional):** already case-insensitive; editing would have been a needless change.
- **devops hook rewiring — skipped (safety):** behavior-changing; reported as follow-up #2.
- **Push / PR / commit — not performed:** brief forbids remote mutation, and `plugins/` is not a git repo (changes are on-disk/unstaged).
- **No official plugins or `claude-plugins-official/` touched** — read-only reference, untouched.

---

*All work local and reversible. 7 plugins validated at 0 errors; genericness and secret sweeps clean.*
