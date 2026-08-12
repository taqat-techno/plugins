---
title: 'Odoo OWL Toolkit'
read_only: false
type: 'command'
description: 'OWL front-end toolkit — lint a module for silent anti-patterns, choose a UI shape, diagnose code that never ran'
argument-hint: '[lint|decide|doctor|rules] [module-path]'
---

# /owl — Odoo OWL front-end toolkit

Odoo's OWL layer has no compiler, and its schema validation is debug-gated. Almost every
mistake **fails silently**: a file in no bundle, a mistyped registry category, a patch on a
renamed method, an xpath that resolves only at first render. This command makes the mechanical
half of that review automatic.

Bare `/owl` auto-detects the module from the current directory and runs `lint`.

## Subcommands

| Command | What it does |
|---|---|
| `/owl` or `/owl lint [path]` | Scan a module for OWL anti-patterns |
| `/owl scaffold <name>` | Generate a correctly-structured standalone OWL application |
| `/owl decide` | Walk the shape decision — backend view vs client action vs self-rooted app |
| `/owl doctor` | Diagnose OWL code that produces no error |
| `/owl rules` | The pre-flight checklist to answer before calling an OWL task done |

---

## lint

Auto-detect the module when no path is given: walk up from the working directory to the nearest
ancestor containing `__manifest__.py`. If none is found, ask for a path rather than guessing.

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/owl/owl_lint.py" <module-path>
python "${CLAUDE_PLUGIN_ROOT}/scripts/owl/owl_lint.py" <module-path> --severity error
python "${CLAUDE_PLUGIN_ROOT}/scripts/owl/owl_lint.py" <module-path> --format json
python "${CLAUDE_PLUGIN_ROOT}/scripts/owl/owl_lint.py" <module-path> --only A1,P5
```

Exit codes: `0` clean or warnings only, `1` at least one error, `2` bad invocation.

**What it detects**

| Group | Rules |
|---|---|
| Assets | `A1` file in no bundle glob · `A2` dead ordering directive · `A3` removing another module's file |
| Registry | `R2` one-shot category registered below top level |
| Services | `S1` force-replaced service · `S3` `env.services` captured in a component |
| patch() | `P1` no `super` · `P2` class/prototype confusion · `P5` raw prototype assignment, shared extension literal, bare `patch` in a test |
| Templates | `X2` fragile xpath · `X3` missing `t-inherit-mode` |
| Data | `D2` awaited RPC in a loop |
| Security | `SEC2` payload widened · `SEC3` `sudo()` on the load path |
| Stale | `S-*` idioms that provably do not work in Odoo 19 |

**Reporting the result**

- Lead with errors; they are the ones that break silently in production.
- For each finding give the rule id, the file:line, and the one-line fix — the scanner already
  emits all three.
- `A1` findings are the highest value: that file is not running at all, which usually explains
  every other symptom the user reported.
- Do not auto-fix. Several rules need a judgement call (`P1` may be a deliberate replacement,
  `SEC2` is a classification question). Propose the change and let the user decide.
- Vendored code under `static/lib/` is skipped by design.

**Known limits — say so rather than implying full coverage.** This is a static scanner. It
cannot prove a registry category name is right, that an xpath matches, that a patched method
still exists upstream, or that a payload field is safe to expose. Those stay human review; see
`reference/owl/anti-pattern-catalogue.md` for the `[review]`-only entries.

---

## scaffold

Generate a full standalone OWL application with the reference structure.

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/owl/owl_scaffold.py" \
    --name <snake_case_name> --title "<Human Title>" --dest <addons-dir>
python "${CLAUDE_PLUGIN_ROOT}/scripts/owl/owl_scaffold.py" --name x --dest . --dry-run
```

**Before generating, confirm the shape is right.** A self-rooted app is a large, permanent
cost. Only four requirements force it — a URL outside the backend path, unauthenticated users,
offline operation, or a distinct security surface. If none applies, run `decide` first and
steer to a client action instead. Do not scaffold on a vague "it should feel like an app".

Ask for: the technical module name (snake_case), a human title, the URL route, and the addons
directory. Default the route to `/<name>/ui`.

**What it produces** — 28 files:

| Layer | Files |
|---|---|
| Bundles | `__manifest__.py` with the three-bundle split (floor / private app / prod entry) plus test bundles |
| Bootstrap | `controllers/main.py`, the standalone index document, `main.js`, root component |
| Services | store (reactive, registered as a service), data service (the only holder of `orm`) |
| Access | `useStore()` hook, self-registering first screen, navbar, loader |
| Server | config model with a backend `act_url` entry point, a load mixin, groups + ACLs + a company record rule |
| Tests | a `setup<App>Env()` bootstrap and a first HOOT test |

**After generating**, tell the user to:

1. Install the module and open the config record's *Open …* button, or hit the route directly.
2. Verify the bundle split in a shell — `_get_asset_links('<app>.assets_prod')` must contain
   `main.js`, and `_get_asset_links('<app>._assets_app')` must not.
3. Run `/owl lint` on it. The scaffold is expected to come back with **no findings**; anything
   else means a local edit broke a layer rule.

**What it deliberately leaves out** — say this out loud, because the omissions are the point:
no records layer, no IndexedDB persistence, no service worker, no URL router. Each is a
substantial subsystem that is harmful in a v1, and each has a documented signal for when to add
it and a migration path that the generated structure keeps open. The generated `README.md`
carries that table for the specific app.

Load the `odoo-owl-app-structure` skill for the layer rules, scaling checkpoints and the build
order from zero.

---

## decide

Load the `odoo-owl-architecture` skill and walk the decision table with the user. Establish the
requirement first, then the shape — not the reverse.

Only four requirements force a self-rooted OWL application: a URL outside the backend path,
unauthenticated users, offline operation, and a distinct security surface. If none is a hard
requirement, a client action is cheaper and keeps upgrade-following.

State the cost of a self-rooted app out loud before recommending it.

---

## doctor

Load the `odoo-owl-diagnostics` skill and run its ordered checklist. Start at bundle membership;
never start at the behaviour.

Ask for the actual symptom first, because the signature narrows it fast:

| Symptom | Start at |
|---|---|
| Nothing happens, no console error | bundle membership (`A1`) |
| "Modules failed to load" cascade | the **first** error only; the rest is fallout |
| Patch seems not to apply | prototype vs class, then whether the method name still exists |
| Feature silently absent | registry category name and registration timing |
| Static edit not visible | which bundle was loaded; the two-cache trap for new files |
| Works in debug, breaks in production | debug-gated validation |

If a live instance is connected, `odoo_status` confirms the server version, which decides which
APIs exist.

---

## rules

Print the pre-flight checklist. Every answer must be yes before an OWL task is complete.

1. Is every file I added or changed inside a bundle the target app actually loads?
2. Did I read the current source for every API I used, rather than relying on memory?
3. If I patched: prototype vs class chosen deliberately, `super.x(...arguments)` called,
   extension literal inline, two-argument form?
4. If a template must see the patch, did I ship the matching `t-inherit` in the same bundle and
   commit?
5. If I registered anything: correct category name, module top level, and before the consuming
   service starts if the category is one-shot?
6. Does every new piece of state have a named owner, and is no store data copied into `useState`?
7. Does all new server data arrive through the loading contract rather than an ad-hoc RPC?
8. For every field added to the payload, did I answer the six exposure questions — including
   whether it carries `groups=`?
9. For every capability the UI allows or hides, can I name the server-side check that enforces it?
10. Is every client-sent number recomputed or cross-checked server-side?
11. Did I run the correct rebuild for each kind of edit, and no more?
12. Did I verify in the browser — correct bundle confirmed, console clean?
13. Did I run the cheapest binding test and read its summary line and exit code, not a log grep?
14. Is the diff minimal, and is every claim either file-anchored or marked `[INFERRED]`?

---

## Rules

- Never edit files under a shared or read-only Odoo source tree; extend from your own addon.
- Keep the diff minimal. The ecosystem is held together by xpath anchors into other addons'
  markup and by patch chains keyed on method names — moving markup or renaming a method breaks
  addons that never mention you.
- A green terminal is not evidence an OWL change works.
