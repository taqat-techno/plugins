---
name: odoo-owl-app-structure
description: |
  Build and organise a full standalone OWL application inside Odoo 17-19 — the healthy structure behind a large Odoo SPA, generalised. Covers the module layout, the three-bundle manifest and why the boot file is split out, the minimum viable bootstrap (controller, index document, main.js, root component), the six-layer dependency rules, the store and data services, screen registration, the server-side load contract, scaling checkpoints, what to deliberately NOT copy in a v1, and the build order from zero. Includes a scaffold generator.

  <example>
  Context: User wants to start a new full OWL app.
  user: "I want to build a standalone OWL app in Odoo like POS"
  assistant: "Let me scaffold the reference structure — bundle triple, bootstrap chain, store and data services — then we add screens on top."
  <commentary>The structure is the hard part and is the same every time; generate it rather than hand-rolling it.</commentary>
  </example>

  <example>
  Context: User asks where a piece of the app should live.
  user: "Where should I put the code that loads products for my kiosk app?"
  assistant: "In the data service — it's the only holder of orm. Screens never call orm directly."
  <commentary>The layer rules are what keep a large OWL app maintainable.</commentary>
  </example>

  <example>
  Context: User's app has grown and screens are duplicating state.
  user: "Two screens need the same selected record and they keep getting out of sync"
  assistant: "That's the signal for a store service. Let me show the shape and the migration."
  <commentary>Scaling checkpoints: each subsystem has an observable signal that it is now needed.</commentary>
  </example>
---

# Structuring a full OWL application inside Odoo

This is the constructive counterpart to `odoo-owl-extending` (changing someone else's OWL code).
Here you own the app.

**First**: confirm you actually need a self-rooted app. Only four requirements force it — a URL
outside the backend path, unauthenticated users, offline operation, or a distinct security
surface. See `odoo-owl-architecture`. Everything below assumes one of those applies.

## Scaffold it

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/owl/owl_scaffold.py" \
    --name my_console --title "My Console" --dest <addons-dir>
```

28 files: the bundle triple, controller, index document, `main.js`, root component, store
service, data service, `useStore()` hook, loader, a self-registering first screen, security
groups and record rule, a config model with a backend entry point, and a test bootstrap. The
output is expected to lint clean — verify with `/owl lint`.

Use `--dry-run` to preview. Read the generated `README.md`: it states the layer rules and the
deliberately-omitted subsystems for that specific app.

## The module layout

```
my_console/
├── controllers/main.py              the route
├── models/                          config record + the load mixin
├── security/                        groups, ACLs, record rules
├── views/
│   ├── my_console_assets_index.xml  ⚑ THE BOOTSTRAP DOCUMENT
│   └── my_console_config_views.xml  backend admin views
└── static/
    ├── src/
    │   ├── utils.js                 dependency-free, OUTSIDE app/ so a second
    │   │                            smaller app can include it alone
    │   ├── app/                     EVERYTHING THE SPA LOADS
    │   │   ├── main.js              boot only; removed from the private bundle
    │   │   ├── my_console_app.js|.xml|.scss   the root
    │   │   ├── services/            store, data, and any capability services
    │   │   ├── models/              client-side record classes
    │   │   ├── screens/             things a route can point at
    │   │   ├── components/          everything else
    │   │   ├── hooks/               useStore() and friends
    │   │   └── utils/               formatters, error handlers
    │   ├── overrides/               patches to `web`, NOT to your own app
    │   ├── backend/                 web.assets_backend only
    │   └── scss/                    GLOBAL styles only
    └── tests/{unit,tours}/
```

Four layout rules that pay for themselves:

1. **`static/src/app/` is the app; everything else is not.** Directory placement, not manifest
   editing, routes a file to a bundle. Keep the glob broad and subtract by directory.
2. **Co-locate `.js` + `.xml` + `.scss` per component.** There is no central `xml/` directory.
   `static/src/scss/` holds global files only.
3. **`screens/` = routable; `components/` = everything else.** Screens self-register; components
   never do.
4. **`overrides/` is for changing *webclient* behaviour**, not your own. Anything patching your
   app lives beside what it patches.

## The bundle triple — and why the boot file is split out

Three cooperating bundles:

| Bundle | Contents | Purpose |
|---|---|---|
| `<app>.base_app` | framework floor: helpers, bootstrap SCSS, `web._assets_core` | A second, smaller app (kiosk, customer display) reuses this **alone** |
| `<app>._assets_app` | everything **except** `main.js` | **Publish this name** as your extension point |
| `<app>.assets_prod` | the private bundle + `main.js` appended last | What the index document calls |

`main.js` mounts the app as an **import side effect**, so where it sits in the file order
matters. A broad glob sweeps it into the *middle* of the bundle; `('remove', …/main.js)` cancels
that, and `assets_prod` re-appends it last. That split is what guarantees the boot file loads
last — and it is also what lets the unit-test bundle take `assets_prod`, remove `main.js` again,
and get all your modules **without** mounting the app, so tests mount it themselves.

**Satellite addons inject one line** targeting the *private* bundle:
`'<app>._assets_app': ['my_addon/static/src/**/*']`. An extender targeting `assets_prod` would
be invisible to your tests.

One bundle is defensible only if you will never unit-test with HOOT, never ship a second entry
point, and accept no addon injecting into you. The cost of doing the split on day one is two
extra dict keys.

## Minimum viable bootstrap — four artifacts

1. **The controller.** Auth gate *before* rendering, and `Cache-Control: no-store` because the
   document embeds session state.
2. **The index template.** A full OWL app needs its **own HTML document**, not a backend-layout
   inherit. Three load-bearing details: the global `odoo` object carries server state to JS
   before any RPC; `odoo.loadMenusPromise = Promise.resolve()` short-circuits the webclient menu
   service that `web._assets_core` drags in; and `<body>` is **empty** — the root owns the DOM.
3. **`main.js`.** `mountComponent` from `@web/env` — not from the webclient module.
4. **The root component.** Must render `<MainComponentsContainer/>`, the mount point every
   `dialog`, `notification` and `overlay` service renders into. Omit it and `this.dialog.add(…)`
   silently does nothing.

**The two-app loader trick is worth copying.** `mountComponent` awaits `startServices`, and your
data service does its first RPC there — so the screen is blank for seconds. Mount a throwaway
`Loader` app first, hand the root a `disableLoader` prop, and let the loader destroy **its own
app** when it flips. Two independent OWL apps share one `document.body`.

## The six-layer dependency rules

```
main.js ──mounts──► Root
                     │ useStore()
        screens/ components/  ── use ──► hooks/ utils/
                     │ useStore() / useService()
        services/store  ──────────────► services/* (data, printer, …)
                     │                        │
        models/ (client records)          @web ORM / RPC / bus
```

| Rule | Why it holds |
|---|---|
| **Components and screens must not import the store module.** They obtain it with a hook. | The hook wraps a reactive service in `useState`; a direct import or `env.services.x` capture means the component stops re-rendering. |
| **Screens must never call `orm` or `rpc`.** | They go through the store or the data service. |
| **Exactly one service owns the server.** | Swapping transports, adding retries, or going offline becomes a one-file change. |
| **Services must not import the store.** | The graph is strictly one-way. A back-assignment to break a cycle hides a design fault. |
| **Models must not know about components.** | Records are plain reactive data; they never open a dialog. |
| **Components may import a record *class*** only for typing or construction. | Extending addons *do* import the class — that is what `patch()` needs. |
| **Mirror the path you patch.** | Path parity is how a reader finds an override. |

Where a given piece of state belongs is a separate decision — see `odoo-owl-state-data`.

## The server-side load contract

Build one only if the app must load a bounded working set once and then run without the server.

The shape is a per-model mixin with two hooks — a domain and an explicit field list — plus an
ordered model list and one RPC entry point. Four design points worth stealing:

- **`read(fields, load=False)`** returns raw ids for relational fields rather than
  `(id, display_name)` tuples. Omitting it doubles the payload and breaks the record graph.
- **Pass the accumulated `data` into every domain** so later models can filter on what earlier
  ones loaded. The model list is an ordered *pipeline*, not a set.
- **Catch `AccessError` per model, not fatally** — a user missing rights on one model gets an
  empty list and a log line, not a broken app. (Know the flip side: this is exactly why a field
  carrying `groups=` blanks a whole model silently.)
- **Build the incremental-load hook now**, even if you always pass `False`. Retrofitting it into
  forty domains later is miserable.

**When not to build it**: if the app is online-only and each screen queries what it needs, one
data service calling `webSearchRead` is correct and far cheaper. The signal to switch — you are
re-fetching the same reference data on every screen mount, or two screens need the same records
to be *the same object*.

## Scaling checkpoints — add each at its signal, not before

| Add | Signal |
|---|---|
| **A store service** | Two sibling screens need the same mutable value, or you cannot write a unit test because state lives inside a component |
| **A dedicated data service** | More than ~3 modules import `rpc` directly, or you need one place for retry/offline |
| **A records layer** | You hand-write `list.find(x => x.id === id)` in three places, or a relation must be traversable both ways and stay reactive |
| **A URL router** | Users ask for a back button, a deep link, or a refresh that lands where they were |
| **An offline queue** | The app must accept writes with no connection |
| **A service worker** | The app must *cold start* offline — stricter than queuing writes |
| **A second, smaller app** | A second device needs a subset of the UI. Reuse `base_app` + hand-picked components; do **not** include the private bundle |
| **Registry extension points** | A satellite addon must add a screen or button without you editing a list |

## Start smaller — four subsystems to leave out of a v1

| Do not copy | Do instead | Migration path |
|---|---|---|
| A records layer (well over a thousand lines) | Plain objects over what the data service returns; a `Map` per model keyed by id | Keep every access behind `data.get(model, id)`-shaped accessors from day one, then drop a real layer in behind the same API |
| IndexedDB persistence | Nothing. Reload = refetch | Route *all* browser storage through the framework's IndexedDB util and all globals through its browser wrapper — test mocks can only intercept those |
| A service worker | Nothing | Add the route and the asset-URL precomputation together; the worker is useless without the asset list |
| A custom URL router | `store.page = "Foo"` + a registry category + dynamic `<t t-component>` (~15 lines) | Keep the registry from the start; adding URL matching later means only adding `route:` to registrations you already have |

One more restraint: **do not remove the framework's error handlers** unless you are actually
writing replacements. Remove them and write nothing, and unhandled promise rejections vanish
silently.

## Build order, from zero

1. Module skeleton — manifest with `application: True`, security groups, config model.
2. Backend entry point — an `ir.actions.act_url` with `target: 'self'`. Needs no JS.
3. Controller + index template. **Verify**: the URL returns an empty body with your bundle in
   `<head>`, before any component exists.
4. The bundle triple. **Verify** in a shell: `_get_asset_links('<app>.assets_prod')` contains
   `main.js`; the private bundle does not.
5. `main.js` + root component + `MainComponentsContainer`. Milestone: a blank styled page mounts.
6. **The store service + the `useStore()` hook — before the second screen exists.** Retrofitting
   this is the expensive move.
7. The data service, the only holder of `orm`. Its `start` returns an already-loaded instance so
   no component sees a half-loaded store.
8. The load contract — or an explicit decision to use `webSearchRead` and revisit at the signal.
9. Screen registry + the first two screens, self-registering at module top level.
10. The loader. Cheap, and what makes a multi-second service start tolerable.
11. Test bootstrap — one `setup<App>Env()` returning the store via `getService`. This only works
    because root state is a **service**.
12. One tour, end to end, before a third screen exists.
13. Publish the extension contract: private bundle name, registry categories, and which classes
    are `patch()`-stable.

Steps 1–11 are what the scaffold generates.

Related: `odoo-owl-architecture` (should this be an app at all), `odoo-owl-state-data`,
`odoo-owl-extending`, `odoo-owl-diagnostics`.
