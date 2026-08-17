# Changelog

All notable changes to `odoo-plugin` are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/). Versioning follows [SemVer](https://semver.org/).

## [2.9.0] - 2026-08-18

Marketplace-wide architecture upgrade. Skill discovery, invocation-mode metadata, and identity consistency were corrected across the marketplace; no skill, command, agent, hook, or MCP behaviour was removed.

**Restored 11 undiscovered skills.** `skills/frontend/<sub>/SKILL.md` and `skills/owl/<sub>/SKILL.md` were nested one level too deep; Claude Code only discovers `skills/<name>/SKILL.md` and never descends, so frontend-js, spreadsheet-dashboards, theme-create, theme-design, theme-scss, theme-snippets and the five odoo-owl-* skills were all invisible at runtime. Flattened to `skills/<name>/` (git mv, history preserved) with internal references updated. **Plugin identity is now `odoo`** (was `odoo-plugin`), matching the marketplace entry; the `odoo-plugin/` folder name is unchanged and intentionally differs. Normalized 5 CRLF files to LF. Fixed `user_invocable` -> `user-invocable` on 2 skills.

## [2.8.0] — 2026-08-12 — OWL: the constructive half — reference architecture + a 28-file app scaffold

2.7.0 covered what NOT to do. This adds what a healthy OWL application actually looks like, so
the domain now answers "how do I build one", not only "why did mine break".

### Added

- `skills/owl/owl-app-structure/SKILL.md` (`odoo-owl-app-structure`) — the reference
  architecture for a full standalone OWL application inside Odoo, generalised from how Odoo's
  own large SPA is organised:
  - **Module layout** and the four rules it enforces mechanically — `static/src/app/` *is* the
    app so directory placement (not manifest editing) routes a file to a bundle; co-locate
    `.js`/`.xml`/`.scss` per component with `static/src/scss/` global-only; `screens/` is
    routable and `components/` is not; `overrides/` is for changing *webclient* behaviour, never
    your own.
  - **The three-bundle split and why the boot file is separated** — a framework floor a second
    smaller app can reuse alone, a private app bundle that is the published extension point, and
    a prod entry bundle that re-appends `main.js` last. `main.js` mounts as an import side
    effect, so a broad glob sweeping it into the middle of the bundle is the bug the split fixes;
    it is also what lets the unit-test bundle take prod, remove `main.js` again, and load every
    module *without* mounting, so tests mount the app themselves.
  - **Minimum viable bootstrap** — controller with the auth gate before rendering and
    `Cache-Control: no-store`; a standalone HTML document (not a backend-layout inherit) whose
    `<body>` is empty because the root owns the DOM, carrying the global `odoo` object and the
    menu-service short-circuit; `mountComponent` from `@web/env`; a root that renders
    `MainComponentsContainer`, without which every dialog and notification silently renders
    nothing. Includes the two-app loader pattern that covers the multi-second service start.
  - **Six-layer dependency rules** — components obtain the store from a hook and never import it;
    screens never call `orm`/`rpc`; exactly one service owns the server; services never import
    the store; models never know about components; mirror the path you patch.
  - **The server-side load contract**, its four design points (`load=False`, the ordered-pipeline
    `data` argument, per-model `AccessError` tolerance, the incremental hook built up front) and
    an explicit "when not to build this".
  - **Scaling checkpoints** — the observable signal for each subsystem, and **"start smaller"**:
    four subsystems to leave out of a v1 (records layer, IndexedDB, service worker, URL router)
    each with a stand-in and a migration path.
  - **Build order from zero**, 13 steps.
- `scripts/owl/owl_scaffold.py` — generates a complete, correctly-structured OWL application:
  28 files covering the bundle triple, controller, index document, `main.js`, root component,
  a reactive store service, a data service that is the only holder of `orm`, the `useStore()`
  hook, a loader, a self-registering first screen, a navbar, security groups + ACLs + a company
  record rule, a config model with a backend `act_url` entry point, a load mixin, a test
  bootstrap and a first HOOT test. Standard library only. Supports `--dry-run`, `--force`,
  `--route`, `--title`. The generated module carries its own `README.md` stating the layer rules
  and the deliberately-omitted subsystems.
- `tests/owl/test_owl_scaffold.py` — 16 tests. The load-bearing one is
  `test_generated_module_lints_clean`: the scaffold and the linter are two halves of the same
  opinion, so the generator's output must satisfy the checker at every severity. The rest assert
  structural invariants directly — `main.js` is the last entry of the prod bundle and removed
  from both the private and unit-test bundles, the index document is standalone with an empty
  body, `mountComponent` comes from `@web/env`, the root renders `MainComponentsContainer`, only
  the data service touches `orm`, no component captures `env.services`, the screen registers at
  column 0, and the store extends `Reactive`.

### Changed

- `commands/owl.md` — new `scaffold` subcommand, including the gate that a self-rooted app needs
  one of four forcing requirements and should otherwise be a client action, and the instruction
  to state the deliberate omissions out loud.
- `.claude-plugin/plugin.json` — version 2.7.0 → 2.8.0.
- `README.md` — `/owl` description and the **owl** domain updated.

### Validation

- `python tests/owl/test_owl_scaffold.py` → 16 passed, 0 failed.
- `python tests/owl/test_owl_lint.py` → 23 passed, 0 failed.
- `python tests/mcp/test_mcp_server.py` → 20 passed, 0 failed.
- `python validate_plugin.py odoo-plugin` → 0 errors (exit 0).
- Scaffold output linted end to end: `owl_lint` reports **no findings** on the generated module.
- Genericness sweep over every added file → 0 project, workspace, host, path or client tokens.

## [2.7.0] — 2026-08-12 — OWL front-end domain: 4 skills, an anti-pattern catalogue, and a static linter

The plugin had no coverage of OWL application development — the layer where Odoo front-end work
actually fails. Its distinguishing property is that **almost every mistake is silent**: a file
outside every asset glob produces no console error, a mistyped registry category returns a fresh
empty registry, a patch on a renamed method installs as a brand-new property, and registry
schema validation returns immediately when `!odoo.debug`. There is no compiler, so review is the
only gate. This release makes the mechanical half of that review automatic.

### Added

- `scripts/owl/owl_lint.py` — static scanner for OWL anti-patterns, **standard library only**,
  matching the plugin's existing `python "${CLAUDE_PLUGIN_ROOT}/scripts/..."` convention.
  Detects, with rule ids that match the catalogue:
  - **Assets** — `A1` a file matched by no manifest glob (parses `__manifest__.py` with `ast`,
    expands Odoo asset globs where `**` crosses separators and `*` does not, and diffs against
    the files actually on disk); `A2` an ordering directive placed after a glob that already
    matched, which is a no-op; `A3` `('remove', …)` of a path owned by another module, which is
    global for that bundle.
  - **Registry** — `R2` a *one-shot* category registered below module top level. Live categories
    (`services`, `main_components`, `systray`, `error_handlers`, `web_tour.tours`) are
    deliberately exempt, because they re-read after boot.
  - **Services** — `S1` force-replaced service; `S3` `env.services.x` captured inside a
    component, which silently stops the component re-rendering.
  - **patch()** — `P1` a patched method with no `super`; `P2` class/prototype confusion;
    `P5` raw prototype assignment, a shared (mutated) extension literal, and bare `patch()` in a
    HOOT test body.
  - **Templates** — `X2` positional or text-anchored xpath (resolved client-side at first render,
    so it ships green); `X3` `t-inherit` without an explicit `t-inherit-mode`.
  - **Data / security** — `D2` awaited RPC inside a loop; `SEC2` payload-widening methods;
    `SEC3` `sudo()` on the data-loading path.
  - **Stale patterns** — 15 idioms that are widely documented online and provably absent from
    Odoo 19, including the three-argument `patch(obj, "name", ext)` form that throws on sight,
    `PosGlobalState`, `pos_screens`, `addControlButton`, `_loader_params_*`, `--dev=assets`,
    `orm.nameGet`/`nameSearch`/`readGroup`, `type='json'` routes,
    `check_access_rights`/`check_access_rule`, `QUnit`, `name_get` (removed in **18.0**, not
    17.0 as widely believed) and `fields_view_get` (removed in 17.0).
- `reference/owl/anti-pattern-catalogue.md` — the full catalogue behind the linter, including the
  `[review]`-only entries a static scanner cannot decide (registry category correctness, xpath
  matching, payload exposure, patch-order coupling) and the stale-pattern index.
- `skills/owl/owl-architecture/SKILL.md` (`odoo-owl-architecture`) — choosing the front-end
  *shape* before writing code: backend view vs `ir.actions.client` client action vs self-rooted
  application, with the decision table and an explicit accounting of what a self-rooted app gives
  up (router, error handling, core service semantics, breadcrumbs/navbar/systray, and
  upgrade-following). Only four requirements force it.
- `skills/owl/owl-extending/SKILL.md` (`odoo-owl-extending`) — the fixed extension menu, the six
  `patch()` rules, template inheritance (`extension` vs `primary`), registry placement and
  one-shot categories, and service/store extension.
- `skills/owl/owl-state-data/SKILL.md` (`odoo-owl-state-data`) — the four state-ownership
  questions, why copying store data into `useState` silently loses user edits, the four ways a
  value escapes reactivity, relation mutation by command, the data-loading contract, and the six
  payload-exposure questions.
- `skills/owl/owl-diagnostics/SKILL.md` (`odoo-owl-diagnostics`) — the ordered triage checklist
  for code that produces no error, browser-console introspection of the module loader and
  registries, the two-cache trap that makes a *new* file invisible even under `?debug=assets`,
  matching the rebuild to the edit, and why "the server started" is not evidence.
- `commands/owl.md` (`/owl`) — `lint` / `decide` / `doctor` / `rules`. Bare `/owl` auto-detects
  the module from the working directory and lints it.
- `tests/owl/test_owl_lint.py` — 23 tests covering both directions: each anti-pattern is
  detected, and correct code written the way Odoo core writes it produces nothing.

### Validation

- `python tests/owl/test_owl_lint.py` → 23 passed, 0 failed.
- `python tests/mcp/test_mcp_server.py` → 20 passed, 0 failed (unchanged).
- `python validate_plugin.py odoo-plugin` → 0 errors (exit 0).
- **False-positive baseline measured against real Odoo 19 core addons.** An early build reported
  128 errors on `web` alone; three genuine rule bugs were found and fixed (`\s` matching newlines
  so column-0 code was reported as indented and one line off; `static/lib/` vendored assets
  scanned; HOOT `*.data.js` mock fixtures treated as test bodies). Final baseline —
  `pos_sale`, `pos_loyalty`, `account`, `stock`, `sale`, `purchase`, `mrp_mps`: **0 errors**;
  `point_of_sale` 4, `pos_restaurant` 4, `hr` 1, all spot-checked and confirmed genuine
  (`env.services` captured in a component; raw prototype assignment inside a test).
- Genericness sweep over every added file → 0 project, workspace, host, path or client tokens.

### Changed

- `.claude-plugin/plugin.json` — version 2.6.0 → 2.7.0; description mentions the OWL domain.
- `README.md` — `/owl` added to the command table; new **owl** domain.

## [2.6.0] — 2026-08-11 — Bundle a live-instance MCP server (`odoo`) for Odoo 14-19

Adds a live connection to a **running** Odoo instance. Until now every skill in this plugin
reasoned about source code; this lets Claude read real records, real field metadata and the
caller's real access rights. Ships with **no credentials and no default instance** — each
developer points it at their own Odoo.

### Added

- `mcp/` — an MCP server over the stdio transport, **standard library only** (`json`, `os`,
  `re`, `socket`, `ssl`, `urllib`, `xmlrpc`, `configparser`, `pathlib`). No `pip`, `npm` or
  `uv` step: a plugin distributed to a team cannot assume a package manager is present, and
  a server that fails to start is worse than no server. Single-owner layering —
  `server.py` (protocol) → `tools.py` (surface) → `odoo_client.py` (transport) →
  `profiles.py` (configuration) → `guards.py` (every access decision).
- **Version-adaptive transport**, chosen from `server_version_info`: Odoo 19+ uses the
  JSON-2 API (`POST /json/2/<model>/<method>`, `Authorization: Bearer <api_key>`); Odoo 18
  and older use XML-RPC (`/xmlrpc/2/common` → `/xmlrpc/2/object` `execute_kw`, API key sent
  as the password). JSON-2 does not exist before 19.0.
- **Ten tools, capped by a test**: `odoo_status`, `odoo_list_models`, `odoo_inspect_model`,
  `odoo_search`, `odoo_count`, `odoo_read_group`, `odoo_call`, `odoo_create`, `odoo_write`,
  `odoo_unlink`. Every MCP schema is injected into the context window of every session where
  the server is enabled, including sessions doing pure source work — so breadth lives in
  parameters, not in tool names.
- **Connection profiles**, resolved first-match-wins: `ODOO_MCP_PROFILE` →
  `<project>/.odoo-mcp.json` → `~/.odoo-mcp/profiles.json` (with a `project_map` so one file
  serves many checkouts) → `ODOO_URL`/`ODOO_DB`/`ODOO_USERNAME`/`ODOO_API_KEY`. Any string
  value may reference `${ENV_VAR}`, so a profile file can be kept free of secrets.
- `.mcp.json` — plugin MCP registration. Forwards `${CLAUDE_PROJECT_DIR}` (substituted
  directly for plugin-provided configs) so the server resolves the profile for the project
  in use. Interpreter overridable via `${ODOO_MCP_PYTHON:-python}`.
- `commands/mcp-setup.md` (`/mcp-setup`) — `status` / `setup` / `test` / `doctor`. Refuses to
  write a key into a file that is not git-ignored, never accepts a password, and steers away
  from administrator accounts.
- `skills/mcp/SKILL.md` (`odoo-live-instance`) — when to query the instance versus the source
  tree, token-efficient querying, multi-company/`active_test`/`lang` context traps, the
  safety model, and treating record content as untrusted data rather than instructions.
- `config/odoo-mcp.profiles.json.example` — full option reference.
- `tests/mcp/test_mcp_server.py` — 20 tests driving the real process over stdio. No Odoo
  instance and no network required: protocol behaviour, profile resolution and every guard
  resolve before a socket opens.
- `.gitignore` — blocks `.odoo-mcp.json` (may contain an API key) and Python caches.

### Security

- The server acts **as the authenticated Odoo user**. No `sudo`, no superuser, no SQL, no
  shell, no filesystem, no module install/upgrade — a structural test asserts those patterns
  are absent from `mcp/*.py`. Odoo's `ir.model.access`, `ir.rule` and field groups apply to
  every call; the guards are a second layer, not a replacement.
- **Read-only by default.** `create`/`write`/`unlink`, and any method not on the read-only
  list, require `"mode": "write"`.
- **Production marker** — a profile marked `"production": true` refuses writes unless
  `allow_production_writes` is set deliberately. Combining `production` with
  `verify_ssl: false` is refused outright; disabling TLS verification elsewhere warns.
- **Delete is separately gated** behind `allow_unlink`.
- **Privilege-escalation models blocked for writes** even in write mode: `res.users`,
  `res.groups`, `ir.actions.server`, `ir.cron`, `base.automation`, `ir.module.module`,
  `ir.config_parameter`, `ir.model*`, `ir.rule`, `ir.ui.view`, `ir.mail_server`.
- Private methods, code-execution and module-install methods, string domains (an injection
  vector) and audit-suppressing context keys (`tracking_disable`, `mail_notrack`, …) are all
  refused.
- Credentials are redacted from every tool result and error by exact value and by key name.

### Portability

- Odoo API drift already handled: `name_get` was removed in **18.0** (not 17.0, as widely
  claimed) so `display_name` is read instead; `fields_view_get` was removed in 17.0 so
  `get_views` is used; `read_group` is deprecated in 19.0 but still callable, which keeps it
  the portable choice across 14-19.
- MCP protocol: the `initialize` handshake is implemented, and `server/discover` answers
  *method not found* — which the specification's own backward-compatibility rule tells a
  newer client to read as a legacy server and fall back to `initialize`. Both client
  generations work.
- On Windows the stdio streams are reconfigured so `\n` is not translated to `\r\n`, which
  would corrupt the newline framing.

### Changed

- `.claude-plugin/plugin.json` — version 2.5.0 → 2.6.0; description mentions the live-instance
  MCP connection.
- `README.md` — `/mcp-setup` added to the command table; new **mcp** domain.

### Validation

- `python tests/mcp/test_mcp_server.py` → 20 passed, 0 failed.
- `python validate_plugin.py odoo-plugin` → 0 errors (exit 0).
- Genericness sweep over every added file → 0 workspace, project, host, path or credential
  tokens; placeholders only.

## [2.5.0] — 2026-06-23 — Enhance the testing skill (`odoo-test`) with a classification-first test-units workflow

### Added

- `skills/test/SKILL.md` (`odoo-test`, skill v2.0.0 → v2.1.0) gains a **"Test Strategy Workflow (classify → write → review → run → diagnose)"** section at the top of the body — a test-units brain grafted onto the existing pattern library. It mirrors how Odoo's own standard addons (`base`, `account`, `stock`, `sale`, `mail`, `web`, `portal`) test Odoo. Adds:
  - **Classification-first Step 1** — inspect `__manifest__.py` / `models` / `views` / `security` (`ir.model.access.csv` + `ir.rule`) / `wizard` / `controllers` / `report` / `data` / existing `tests` (and an issue's Required Changes / Acceptance Criteria) **before** writing, then answer the version / artifacts / category / runtime / phase / multi-company / regression questions.
  - **Step 2 base-class + tag + file matrix** mapping each work type (computed, `@api.constrains`, `_sql_constraints`, onchange, workflow, access rights, record rules, wizard, controller, report, mail) to `TransactionCase`/`HttpCase`, `at_install`/`post_install`, the target `test_*.py`, and the key assertion.
  - **Modern patterns** the existing skill lacked: the **`Form`** helper for onchange/view-driven tests, **`assertRecordValues`**, and the **`Command` API** (Odoo 13+) over legacy tuples.
  - A **Security & access discipline** that corrects the prior "bypass security with `sudo()`" guidance: test as a non-admin (`with_user` / `@users`), assert both the forbidden (`AccessError`) and allowed paths, invalidate cache between privilege levels, and reserve `sudo()` for deliberate bypass / fixture setup only.
  - **Four workflows** (Generate / Review / Diagnose / Requirements→tests), **quality gates**, a consolidated **anti-pattern** list, and the **four output templates** (Test Plan / Test Review / Implementation Report / Failure Diagnosis).
- `skills/test/references/` — four new reference files: `test-pattern-catalogue.md` (reusable per-pattern structures incl. record-rule, `@users`, report/QWeb `_render_qweb_html`, mail, multi-company, regression), `custom-module-test-blueprint.md` (recommended `tests/` layout + per-file skeletons + the `tests/__init__.py` discovery rule), `review-checklist.md` (review checklist A–I + anti-pattern catalogue with fixes), and `odoo-version-matrix.md` (base classes, `Command`, `<list>`/`<tree>`, `json`/`jsonrpc`, helper availability across 14–19).

### Changed

- `skills/test/SKILL.md` frontmatter — `description` now advertises planning / reviewing / diagnosing / security / regression / requirements→tests triggers + three new `<example>` blocks (review, diagnose, security); `version` 2.0.0 → 2.1.0; `metadata.categories` add `security-tests`, `record-rules`, `test-review`, `regression`, `diagnosis`; last-updated date refreshed.
- The existing pattern library, running, coverage, CI, version-table, and troubleshooting sections are **unchanged** (single-owner: the new workflow references them rather than duplicating). No existing example or command was removed.
- `.claude-plugin/plugin.json` — version 2.4.0 → 2.5.0.
- `README.md` — `test` domain line expanded with the new capabilities.

### Validation

- `python validate_plugin.py odoo-plugin` → 0 errors.
- Genericness sweep over `skills/test/references/` and the added SKILL.md section → 0 client/project/host/credential tokens (placeholders only: `<module_name>`, etc.).

## [2.4.0] — 2026-06-14 — Consolidate the Odoo code-review knowledge base (`odoo-reviewer` skill)

### Added

- `skills/reviewer/` (`odoo-reviewer`) — Authoritative Odoo 17 + 19 code-review and technical-debt knowledge base, moved in from a standalone `odoo-reviewer` plugin and folded into this unified toolkit. Auto-activates on review/audit/tech-debt phrasing and whenever a `.py` / `.xml` / `__manifest__.py` from an Odoo addon is in scope. Ships:
  - **12-section review checklist** in `SKILL.md` (manifest hygiene, module layout & file naming, XML conventions, Python style, symbols & class-attribute order, ORM patterns & inheritance, security, performance, views, JS/Owl/assets, testing, translation `_()`), v17 baseline with v19 deltas inlined.
  - **8 reference files** — `coding_guidelines.md`, `orm_patterns.md`, `security_pitfalls.md`, `performance.md`, `module_manifest.md`, `testing.md`, `severity_model.md` (BLOCKER/MAJOR/MINOR/STYLE rubric + effort table), and `v19_deltas.md` (every reviewer-relevant 17→19 change + mixed-version cluster checklist).
  - Every rule traces back to the official Odoo 17/19 documentation and cites its source.

### Changed

- Skill **normalized to the plugin's naming convention**: folder `odoo-17-reviewer` → `reviewer`, frontmatter `name: odoo-17-reviewer` → `odoo-reviewer` (the skill already covers 17+19, matching sibling skills `odoo-i18n-audit` / `odoo-stack-doctor`).
- Skill content **genericized** for this fleet-agnostic toolkit: workspace-specific deployment and cluster tokens replaced with generic mixed-version / multi-cluster wording. No rule, citation, or severity changed.
- `.claude-plugin/plugin.json` — version 2.3.0 → 2.4.0; description now leads with "code review & technical-debt".
- `README.md` — `odoo-reviewer` added to the Audit/Doctor skills table and a `reviewer` domain added to the Domains list.

### Validation

- `python validate_plugin.py odoo-plugin` → 0 errors.
- Genericness sweep over `skills/reviewer/` → 0 workspace-specific deployment/cluster tokens.

## [2.3.0] — 2026-06-13 — Odoo stack & DB lifecycle safety (restart/clone advisory + stack-doctor expansion)

### Added

- `hooks/pre_odoo_restart_guard.py` — PreToolUse hook on the **Bash** tool. **Advisory only** (stdlib-only, fail-OPEN, **always exits 0**, never blocks, never mutates files, never kills processes). Prints a one-line nudge to stderr on three documented-dangerous shapes: an unbounded Odoo readiness poll (`curl --retry-connrefused` against an Odoo-like port/endpoint with no `--max-time`/`--retry-max-time`/`--retry-delay`); a combined `pkill … && … odoo-bin` chain (the pkill self-matches and SIGTERMs the chain → exit 144); and a raw Odoo DB clone (`CREATE DATABASE … TEMPLATE` / `createdb -T`, which copies SQL only and breaks the filestore). Stays silent on bounded curls, split stop/start, `odoo-bin db duplicate`, and non-Odoo commands.
- `skills/stack-doctor/references/db-safety.md` — snapshot backup + sha256 before regeneration; real Odoo uninstall/upgrade (not SQL hacks); filestore-aware clone (`odoo-bin db duplicate` / `exp_duplicate_database`) vs the `psql TEMPLATE` trap; re-inventory + `pg_stat_activity` before destructive DB action on a shared instance; multi-instance isolation (own hostname / HTTP+gevent port pair / `db_filter` / filestore / log / addons_path); separate local config from the Docker config.

### Changed

- `skills/stack-doctor/SKILL.md` (`odoo-stack-doctor`, 0.1.0 → 0.2.0) — added a **Stack & DB lifecycle safety** section: standalone-Postgres-via-its-own-`pg_ctl` (a WAL-recovery timeout/exit is not failure — verify with `pg_isready`/log); shared-instance re-inventory before destructive DB actions; restart hygiene (kill by PID, never `pkill && odoo-bin`, split stop/start, free the port, tail the right log); bounded readiness polling only; verify install/upgrade from the LOG not the wrapper/background exit code; filestore-aware clone; separate local config. Updated frontmatter (description, `owns`, `defers_to`, metadata), When-to-use triggers, Doctor checklist, and Anti-patterns.
- `hooks/hooks.json` — added the Bash-matched advisory restart/clone guard to `PreToolUse` (all existing hooks — core-file, inline-JS, volume-destruction, session-start — unchanged).
- `README.md` — Safety Hooks table documents the new advisory guard.

### Validation

- `python validate_plugin.py odoo-plugin` → 0 errors.
- `python -m py_compile hooks/pre_odoo_restart_guard.py` → clean; hook self-tested across 12 cases (every case exits 0; warns only on the three risky shapes).

## [2.2.0] — 2026-06-13 — volume-destruction Bash guard + audit/doctor skills

### Added

- `hooks/pre_odoo_volume_guard.py` — PreToolUse hook on the **Bash** tool. Hard-blocks (exit 2) `docker compose down -v`/`--volumes` (and legacy `docker-compose down -v`), `docker volume rm`, and `docker volume prune`, which destroy the Postgres DB + Odoo filestore volumes. Passes silently unless an explicit override token (`ALLOW_VOLUME_DELETE` or `--i-understand-data-loss`) is present in the same command. Stdlib-only, fail-OPEN on internal error/timeout. Reads and non-destructive docker commands (`down` without `-v`, `volume ls/inspect`, `run -v` bind mounts, `--volumes-from`) pass silently.
- `skills/i18n-audit/SKILL.md` (`odoo-i18n-audit`) — audit checklist for translations that look complete but fall back to source: typed PO references (not source paths), source-string-edit → msgid invalidation, explicit-UTF-8 decode (no latin-1 / unicode_escape), one-arch/one-.po-per-language pipeline (no forked `_<lang>` views). Version-aware 14-19.
- `skills/stack-doctor/SKILL.md` (`odoo-stack-doctor`) — diagnostic checklist for a stack that "comes up clean but is wrong": mount-point change orphans the old volume (copy forward, never `down -v`), preserve the running Postgres major (forward-incompatible data dir), upgrade via `odoo-bin --stop-after-init` not the RPC button (website configurator hijack silently skips reload), theme-load post-copy after languages are active, theme-translated-fields mapping completeness. Version-aware 14-19.

### Changed

- `hooks/hooks.json` — added the Bash-matched volume-destruction guard to `PreToolUse` (existing core-file and inline-JS guards unchanged).
- `README.md` — Safety Hooks table documents the new volume-destruction guard.

### Validation

- `python validate_plugin.py odoo-plugin` -> 0 errors.
- Hook self-test: 22/22 classification cases pass (8 blocks, 3 override-allows, 11 safe-allows including bind-mount/`--volumes-from`/bare-`down` false-positive guards).
- Genericness sweep: 0 project-specific tokens outside labeled examples.

## [2.1.0] — 2026-05-31 — i18n/PO + volume/PG + theme-load references

### Added

- `skills/i18n/references/po-gettext-discipline.md` — typed PO references, source-string-invalidation audit, .pot/msgmerge workflow, UTF-8 decode (no unicode_escape).
- `skills/docker/references/volume-and-pg-safety.md` — never blind `down -v`, orphan-volume drift, preserve Postgres major version.
- `skills/upgrade/references/theme-load-and-cli-upgrade.md` — `_theme_load` after website/languages, prefer odoo-bin CLI over RPC immediate-upgrade, declare all translatable theme fields.

### Validation

- `python validate_plugin.py odoo-plugin` -> 0 errors.
- Genericness sweep: 0 project-specific tokens outside labeled examples.

## [2.0.0] — 2026-05-01 — BREAKING command rename + bare-invocation discipline

Two binding rules adopted across the marketplace are now applied to odoo-plugin:

1. **Command file names must not include the plugin name as a prefix.** Claude Code already namespaces plugin commands as `/<plugin-name>:<command>`, so `commands/odoo-init.md` produced the awkward `/odoo-plugin:odoo-init`. All sixteen `odoo-*` command files renamed to drop the prefix.
2. **Every command must run sensibly with no arguments.** Bare `/foo` always works; flags are optional shortcuts, never required. The eight commands that previously required positional arguments now auto-detect the target module from the working directory or prompt for the missing piece.

### Renamed (file → new file → invocation form)

| Before | After | Plugin-namespaced |
|---|---|---|
| `commands/odoo-db.md` | `commands/db.md` | `/odoo-plugin:db` |
| `commands/odoo-docker.md` | `commands/docker.md` | `/odoo-plugin:docker` |
| `commands/odoo-frontend.md` | `commands/frontend.md` | `/odoo-plugin:frontend` |
| `commands/odoo-i18n.md` | `commands/i18n.md` | `/odoo-plugin:i18n` |
| `commands/odoo-ide.md` | `commands/ide.md` | `/odoo-plugin:ide` |
| `commands/odoo-init.md` | `commands/init.md` | `/odoo-plugin:init` |
| `commands/odoo-precheck.md` | `commands/precheck.md` | `/odoo-plugin:precheck` |
| `commands/odoo-quickfix.md` | `commands/quickfix.md` | `/odoo-plugin:quickfix` |
| `commands/odoo-report.md` | `commands/report.md` | `/odoo-plugin:report` |
| `commands/odoo-scaffold.md` | `commands/scaffold.md` | `/odoo-plugin:scaffold` |
| `commands/odoo-security.md` | `commands/security.md` | `/odoo-plugin:security` |
| `commands/odoo-service.md` | `commands/service.md` | `/odoo-plugin:service` |
| `commands/odoo-start.md` | `commands/start.md` | `/odoo-plugin:start` |
| `commands/odoo-stop.md` | `commands/stop.md` | `/odoo-plugin:stop` |
| `commands/odoo-test.md` | `commands/test.md` | `/odoo-plugin:test` |
| `commands/odoo-upgrade.md` | `commands/upgrade.md` | `/odoo-plugin:upgrade` |

`commands/create-theme.md` was already prefix-free and is unchanged.

### Bare-invocation fixes (no args required)

Eight commands that previously required positional arguments now auto-detect from the working directory:

- **`/precheck`**, **`/quickfix`**, **`/upgrade`**, **`/security`** — walk up from `$CWD` to find `__manifest__.py`; if `$CWD` has multiple direct subdirectories with manifests, list them and ask which.
- **`/test`** — auto-detects the module the same way and runs the full workflow (coverage → generate-missing → run) instead of "show help".
- **`/init`** — detects Odoo version from `odoo/release.py` if present; uses `$CWD` basename for the project name when reasonable; prompts only for what's actually missing.
- **`/scaffold`** — module name has no filesystem-derivable default, so the bare form prompts interactively rather than refusing. Still does something useful with no args.

Each command's `argument-hint` now uses `[brackets]` for everything since nothing is strictly required.

### Cross-reference rewrites

- 92 internal `/odoo-X` references rewritten across `odoo-plugin/` (commands, skills, scripts, references, tests).
- 7 marketplace-level files updated (`README.md`, `HOOK_AUDIT_REPORT.md`, `wiki/Contribution-Guide.md`, `wiki/Ntfy-Plugin.md`, `wiki/Odoo-Plugin.md`, `wiki/Plugin-Catalog.md`, `wiki/Troubleshooting.md`).
- Plugin manifest version `1.0.0` → `2.0.0` (BREAKING — old `/odoo-X` invocations no longer resolve).

### Migration

Replace any `/odoo-X` muscle memory with the bare command name:
- `/odoo-init --version 19 --project foo` → `/init` (auto-detect) or `/init --version 19 --project foo`
- `/odoo-test mymodule` → `/test mymodule` (or just `/test` from inside the module dir)
- `/odoo-upgrade ./addons/foo 19` → `/upgrade ./addons/foo 19` (or just `/upgrade` from inside the module)

Plugin-namespaced forms are always correct: `/odoo-plugin:init`, `/odoo-plugin:test`, etc.

### Verification

- `python validate_plugin_simple.py odoo-plugin` — passes.
- All 17 commands now run sensibly with no arguments.
