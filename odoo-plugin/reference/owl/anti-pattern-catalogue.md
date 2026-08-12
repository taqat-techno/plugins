# Odoo OWL anti-pattern catalogue (Odoo 17–19)

Rule ids are stable and match `scripts/owl/owl_lint.py`. Cite them in reviews (`P5`, `A1`, …).

**The organising fact: almost every one of these fails silently.** A file outside every asset
glob produces no console error. A mistyped registry category returns a fresh empty registry. A
patch on a renamed method installs as a brand-new property. An unmatched route falls back to a
default screen. An `AccessError` during load blanks a whole model behind an INFO log line.
There is no compiler, and registry schema validation returns immediately when `!odoo.debug`.
**Review is the only gate** — which is why each entry ends with what to grep for.

Legend: **[lint]** = detected by `owl_lint.py`; **[review]** = human review only.

---

## Assets — "my code never ran"

### A1 — A file that no bundle glob matches **[lint]**
Creating `my_module/static/js/foo.js`, or any file outside the glob the manifest actually
declares, and expecting it to load.

Nothing breaks visibly. `odoo.loader.factories.has("@my_module/foo")` is `false`. If another
module imports it you get only *"needed by other modules but have not been defined"* — missing
UI, no stack trace. A manifest comment saying "you don't need to declare new assets, just put
files in the proper directory" only ever covers **that module's own glob**, never yours.

Only `.js/.xml/.scss/.css` are asset extensions — `img/`, `sounds/`, `fonts/` land nowhere.

> **Fix**: one manifest line targeting the shared body, files under `static/src/`.
> **Verify**: `odoo.loader.factories.has("@addon/path")`.

### A2 — An ordering directive placed after a glob that already matched **[lint]**
`('after', target, path)` written *below* a glob covering the same file is a **no-op**: the
inserter skips any path already in its memo. Repeating a path never re-orders it.

Order only matters for SCSS (all stylesheets compile as one unit). JS order is decided by the
module loader's dependency resolution, not by bundle position.

> **Fix**: put ordering directives **before** the glob.

### A3 — `('remove', …)`-ing another module's file to disable behaviour **[lint]**
Removal is **global for that bundle**. Every module importing the removed export stops
starting, reported only as a loader "not defined" line. If the path is not currently in the
bundle you get an install-time `ValueError: File(s) … not found in bundle` instead.

> **Fix**: `patch()` the exported object. If you must remove, re-add what consumers still need.

### A4 — Treating `?debug=assets` as proof **[review]**
The debug branch pins the URL segment to the literal `debug` and regenerates every time, so it
proves nothing about the minified bundle. Worse, `odoo.debug` is cleared unless `?debug` is in
the **URL** — the server can be in assets mode while `env.debug` is falsy.

> **Fix**: view-source, read the `<script src>` segment (7-hex = normal, `debug` = debug), then
> verify with no `?debug` at all.

### A5 — Expecting a new file to appear under `?debug=assets` **[review]**
Two independent caches: the **file list** (ormcached) and the **URL list**. `?debug=assets`
bypasses only the second. A brand-new file matching an existing glob is simply absent — no
error, no 404.

> **Fix**: Regenerate Assets from the debug menu, or restart, or run with `--dev=xml`.

---

## Registry and loader

### R1 — Importing for a side effect and assuming order **[review]**
Bundle order is not execution order. The loader picks the first-defined job whose
*dependencies* are resolved; bundle position only breaks ties. A duplicate `odoo.define` name
is silently ignored, so a copy-pasted file keeping the original path never runs.

> **Detect**: a comment saying "must load after X" with no import of X and no `depends` edge.

### R2 — Registering after the consumer already read the registry **[lint]**
One-shot consumers never re-read. Registering into a snapshotted category from inside
`setup()`, `onWillStart`, a service `start`, or a lazily-imported module is silently ignored.

Live categories (`services`, `main_components`, `systray`, `error_handlers`, `web_tour.tours`)
**do** re-read — late registration there is fine. The one-shot ones are the trap.

> **Fix**: register at module top level, as every shipped screen does.

### R3 — Typing the category name by hand **[review]**
`category()` creates a fresh empty sub-registry on demand. A typo returns `[]`, nothing throws,
the feature is simply absent. The TypeScript surface is not authoritative — it omits real
categories and misspells one of its own keys.

> **Detect**: grep the category string. If it appears exactly once in the tree, that occurrence
> is the bug.

### R4 — Hardcoding what a registry exists to invert **[review]**
A `switch (name)` in code third-party addons must extend cannot be extended by them. Inversion
is the whole design: core never imports the addon that adds a screen.

Conversely, do not invent a registry where core solves it with `patch`. There is **no**
control-button registry in Odoo 19 — addons that add one use `patch(ControlButtons.prototype)`
plus a `t-inherit` xpath.

---

## Services

### S1 — Re-registering a service instead of patching it **[lint]**
Without `force` you get a `DuplicatedKeyError` **at import time**, which aborts the rest of that
file's top-level code — often taking unrelated registrations down with it. With `{force: true}`
it is last-writer-wins by topological order: the next addon forcing the same key silently
discards you. A `force` *after* boot does nothing at all.

> **Fix**: `patch()` the service definition object before startup.

### S2 — Application state in a plain service, or a capability in the store **[review]**
A non-reactive service never drives a render. A store hidden behind a service has no test seam.

> **Fix**: a **store** returns `reactive(this)` or extends `Reactive`; a **capability** is a
> small definition object with declared dependencies.

### S3 — `env.services.x` instead of `useService(x)` inside a component **[lint]**
You skip the `useState(service)` branch, so the component **stops re-rendering** when the store
changes. This is the single most common OWL bug in Odoo code. You also lose the
destroyed-component guard, and a missing service yields `undefined` plus a `TypeError` at an
unrelated frame instead of a clear error at setup.

`env.services.x` is correct only *outside* a component — another service's `start`, an error
handler, a registry callback.

### S4 — Resolving a service cycle by back-assignment **[review]**
`this.otherService.me = this` hides a design fault, makes both services untestable in isolation,
and leaves a field that is `undefined` for whatever window precedes the assignment.

> **Fix**: split the shared concern into a third, dependency-free service.

---

## `patch()`

### P1 — Patching without `super`, or forwarding positionally **[lint]**
Omitting `super` drops the base implementation **and every earlier patch in the chain** — the
symptom usually lands on a distant addon, not on you. A positional forward silently discards a
parameter added upstream.

> **Fix**: `super.method(...arguments)`. If you deliberately replace the base, say so in a
> comment on the line above.

### P2 — Patching the class where the prototype is meant, or vice versa **[lint]**
Neither throws. `patch(Cls, {method(){}})` adds a *static* that instances never call.
`patch(Cls.prototype, {staticField})` never reaches the reader, which reads it off the class.

> **Fix**: prototype for instance behaviour; the class for statics (`components`, `extraFields`).

### P3 — Depending on patch order between sibling addons **[review]**
Order is only *defined* along dependency edges. The sort keys on
`(not application, sequence, name)` before topologically sorting `depends` — a one-line manifest
edit anywhere flips it.

> **Fix**: add the real `depends` edge, or make the patch commutative.

### P4 — Patching a private, renamed, or unstable method **[review]**
A patch on a name that no longer exists is **silently additive**: the property installs as
brand new and `super.thatMethod()` throws only if you call it. Instance fields assigned in a
constructor shadow prototype patches entirely.

> **Fix**: patch a declared seam — `setup()` exists to be patched.
> **Verify**: `Object.getOwnPropertyDescriptor(Cls.prototype, "m").value.toString()`.

### P5 — Monkey-patching a prototype, or reusing one extension literal **[lint]**
A raw `Cls.prototype.x = fn` creates no skeleton, so `super` is unavailable and any later
`patch()` of the same key records **your** function as "the original". In tests it leaks into
every later test in the run.

Sharing one extension literal across two targets is unsafe because `patch()` **mutates it** —
the first target's `super` chain gets silently rewired to the second target's skeleton.

And never `patch(obj, "name", ext)`: the three-argument form **throws on sight** in Odoo 19.

> **Fix**: always `patch()`, always an inline object literal, always at module scope. In tests
> always `patchWithCleanup`.

---

## Templates

### X1 — Copying a core template instead of `t-inherit` **[review]**
Both templates ship. Core's original keeps being extended by every other addon — those
extensions land on the original while your users see the frozen copy, and upstream fixes never
reach you. A duplicated *primary* `t-name` with different content throws.

> **Fix**: `t-inherit` + `t-inherit-mode="extension"` to change what everyone sees; `primary`
> plus a subclass only for a genuinely coexisting variant.

### X2 — Anchoring an xpath on a fragile selector **[lint]**
Template xpaths resolve **client-side at first render**, not at bundle build — so a broken
xpath ships green and breaks in the browser. An ambiguous expression silently picks the first
match with no warning.

> **Fix**: anchor on semantic classes. Corollary: **renaming a non-utility CSS class is a
> breaking change for downstream addons**, with no build-time warning.

### X3 — Template name collisions and misleading `t-name` **[lint, partial]**
Extension-mode templates never register their name, so a `t-name` from another module works —
and becomes a lie about which template you changed. Converting the same file to `primary` later
throws.

> **Fix**: omit `t-name` on extensions; always state `t-inherit-mode` explicitly.

### X4 — Logic in the template **[review]**
Business expressions in `t-if`/`t-esc` are untestable and invisible to a reader of the JS.

> **Fix**: a getter on the component; the template reads it.

---

## Data

### D1 — Fetching from a component instead of the data layer **[review]**
Data fetched ad hoc in a component diverges the moment the sync bus updates the record.

> **Fix**: new server data enters through the module's declared loading contract, or an
> on-demand method returning `{model: rows}` merged into the same store.

### D2 — N+1 RPCs in a loop **[lint]**
One network round trip per iteration.

> **Fix**: one call with a domain or a list of ids.

### D3 — Loading a model into the initial payload "just in case" **[review]**
Every field reaches every client with the app open — and their IndexedDB. It also slows every
cold start.

### D4 — Trusting client-computed money **[review]**
Client-sent numbers are assertions. Recompute derived artefacts from inputs at the state change
that makes them binding; never let a ledger read a client subtotal.

---

## Security

### SEC1 — Hiding a button as authorization **[review]**
A UI change is never authorization. For every capability, name the ACL line, record rule, or
explicit `has_group`/`check_access` in the RPC-reachable method. If you cannot name one, it is
not enforced — `call_kw` from the browser console does what the hidden button would have done.

### SEC2 — Adding a field to the payload without classifying it **[lint, info]**
Worse than a leak: a field carrying `groups=` blanks the **whole model** for users outside that
group, because the loader catches `AccessError` per model and substitutes `[]` behind an INFO
log line. Blank screen, no error.

Ask: who sees it, does it carry `groups=`, is it commercially sensitive, is it a secret, does it
widen the load domain, is company containment explicit.

### SEC3 — `sudo()` to make an error go away **[lint, on the load path]**
`sudo()` removes the user from the security decision entirely.

> **Fix**: grant the access deliberately, or keep the operation server-side behind a checked
> entry point.

### SEC4 — Treating a public method as internal **[review]**
`call_kw` reaches any non-underscore method, and `readonly` is a UI attribute that does not
block an RPC write.

> **Fix**: prefix helpers `_`; use the private-method decorator for a public name that must stop
> being callable.

---

## Process

### Q1 — Reporting success from a running process **[lint, in tests]**
"The server started" is not evidence an OWL change works — assets are cached independently of
the process, so a live server serves a frozen bundle. A stray `.only()` fails CI.

### Q2 — `-u <module>` after every edit **[review]**
Match the rebuild to the edit. Python → restart. Manifest / views / new fields / security →
`-u <module> --stop-after-init`. An existing `static/src` file → clear the assets cache and
hard-reload. A registry load is expensive; an unnecessary `-u` is the main time sink.

### Q3 — Inferring behaviour from a filename or a remembered version **[review]**
Directory names are conventions, not mechanisms. Read the manifest, read the current source.

---

## Stale-pattern index — provably dead in Odoo 19 **[lint]**

Each is widely documented online and does not apply to Odoo 19.

| Pattern | Use instead |
|---|---|
| `pos.js` / `PosGlobalState` / `models.PosModel` | `patch(PosStore.prototype, …)` |
| `registry.category("pos_screens")` / `showScreen("X")` | `pos_pages` + `pos.navigate(name, params)` |
| `ProductScreen.addControlButton(...)` | `patch(ControlButtons.prototype)` + `t-inherit` xpath |
| `_loader_params_<model>()` / `search_params` | `_load_pos_data_fields` / `_domain` / `_models` |
| `patch(obj, "name", ext)` and `unpatch` | two-argument `patch`; `patchWithCleanup` in tests |
| `--dev=assets` | `?debug=assets` in the URL (with A4's caveats) |
| `orm.nameSearch` / `orm.nameGet` / `orm.readGroup` | `orm.call(model, "web_name_search", …)`, `formattedReadGroup` |
| `type='json'` route | `type='jsonrpc'` |
| `check_access_rights()` / `check_access_rule()` | `check_access` / `has_access` / `_filtered_access` |
| `owl="1"` on a template | omit it |
| `QUnit.module(...)` for JS tests | HOOT — `<addon>/static/tests/**/*.test.js` |
| `name_get()` | **removed in 18.0**, not 17.0 — compute `display_name` |
| `fields_view_get()` | removed in 17.0 — `get_views` / `get_view` |

---

## Provenance

Derived from a source-level investigation of the Odoo 19 `web` and `point_of_sale` families.
Mechanisms cited here were read from source rather than documentation; where a claim was
inferred rather than observed, the originating analysis marked it so. Line-level anchors are
deliberately omitted because they drift between point releases — grep the symbol instead.
