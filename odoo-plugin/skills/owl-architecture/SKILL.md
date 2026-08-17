---
name: odoo-owl-architecture
description: |
  Choose and justify the SHAPE of an Odoo 17-19 front-end before writing code — a normal backend view, an ir.actions.client OWL client action, or a self-rooted full OWL application mounted on your own route. Covers the three bootstrap paths, the decision table, what a self-rooted app gives up (router, error handling, breadcrumbs, navbar, systray, upgrade-following), and the layer map from manifest glob to mounted component.

  <example>
  Context: User wants to build a new screen and reaches straight for a full OWL app.
  user: "I want to build a custom kiosk UI in Odoo, like POS"
  assistant: "Before scaffolding, let me check which of the three shapes this actually needs — a self-rooted app is a large, permanent cost and only three requirements genuinely force it."
  <commentary>Shape choice is architectural and near-irreversible; run the decision table first.</commentary>
  </example>

  <example>
  Context: User asks where a client action lives.
  user: "How do I register an OWL component as a client action?"
  assistant: "That's Shape B. Let me walk the actions-registry registration and the props contract the action service injects."
  <commentary>Client action = ir.actions.client + the actions registry category.</commentary>
  </example>

  <example>
  Context: User is deciding whether to keep the WebClient chrome.
  user: "Can I get rid of the Odoo navbar for this screen but keep breadcrumbs?"
  assistant: "Those come as a pair. Let me show what target=fullscreen gives you versus going self-rooted."
  <commentary>Chrome is all-or-nothing; the decision table makes the trade explicit.</commentary>
  </example>
---

# Choosing the shape of an Odoo OWL front-end

Three shapes exist. They differ in who owns the root component and the environment — everything
else follows from that.

| | **A — backend view** | **B — client action** | **C — self-rooted app** |
|---|---|---|---|
| Root component | `WebClient` (framework) | `WebClient` (framework) | **yours** |
| Env owner | framework | framework | **yours** |
| Registry entry | `views` category | **`actions` category** | none — you mount directly |
| Server record | `ir.actions.act_window` | **`ir.actions.client`** | an `http.route` + QWeb page |
| Asset bundle | `web.assets_backend` | `web.assets_backend` | **your own bundle** |
| URL | `/odoo/<path>/<id>` | `/odoo/<path>` (if `path` set) | whatever your route says |
| Breadcrumbs / navbar / systray | free | free | **gone** |

## The decision table

Run this before scaffolding anything. Most requirements point at **B**, which is the
best-evidenced path and by far the cheapest place to put a custom OWL UI.

| Requirement | → A | → B | → C |
|---|---|---|---|
| Records + list/form/kanban + search | ✅ | | |
| Needs WebClient chrome (navbar, apps menu, systray, breadcrumbs) | ✅ | ✅ | ✗ **hard no** |
| Needs a URL under `/odoo/…` | ✅ | ✅ (`path`) | n/a — own route |
| Needs a URL **outside** `/odoo` | ✗ | ✗ | ✅ **forcing** |
| Must serve **unauthenticated / public** users | ✗ | ✗ | ✅ **forcing** |
| Must run **offline** after first load | ✗ | ✗ | ✅ **forcing** |
| Non-CRUD interaction model (scan / tap / tender / queue) | ✗ | ✅ | ✅ |
| Custom client-side data layer with local mutation and sync | ✗ | ⚠ | ✅ |
| Kiosk / full-screen, no chrome | ✗ | ✅ `target=fullscreen` | ✅ |
| Different security surface (token in URL, no session) | ✗ | ✗ | ✅ **forcing** |
| Sub-second interaction over a large **local** dataset | ✗ | ⚠ | ✅ |
| Must reuse `ir.filters`, group-bys, favourites | ✅ | ✅ | ✗ |
| Team wants Odoo upgrades to carry the UI forward | ✅ | ✅ | ✗ |

**Only four rows force C**: a URL outside `/odoo`, public users, offline operation, and a
different security surface. If none of those is a hard requirement, choose B.

## What Shape C actually costs

A self-rooted app does not merely "skip the chrome". It opts out of framework services that
then have to be rebuilt and maintained forever:

- **The router.** Removing it is not possible in practice — the views and action services import
  it — so the real pattern is to re-add the module and then neuter it with a no-op patch, plus a
  bespoke router service of your own.
- **Standard error handling.** Removed deliberately, then replaced with a hand-written handler
  set that must re-register RPC and offline handlers.
- **Core service semantics.** Patching `doAction` so every `act_window` becomes a dialog, and
  shifting the responsive breakpoint, changes behaviour for *every* module loaded into the app.
- **Breadcrumbs, navbar, systray, apps menu.** Rendered in exactly one place, which you never
  mount. All rebuilt by hand.
- **Standard views and search UI.** Still bundled, because they cannot be untangled from the
  action service — so you pay the asset cost and get little of the behaviour.
- **Upgrade-following.** A private data layer has no upstream counterpart to inherit fixes from.

Say all of this out loud before recommending C. If the requirement is "it should feel like an
app", that is not one of the four forcing rows.

## Shape B in practice

Two registration forms exist; the branch that separates them is whether the registry value is a
component or a function. Either way:

- The server record is `ir.actions.client` with a `tag`.
- The client side registers under the `actions` registry category with the same tag.
- The action service injects a props contract — action, actionId, params, and the update
  callbacks the breadcrumb integration needs. Read the current contract rather than guessing:
  the props a client action receives are framework-owned and have changed across versions.
- `target` has four modes, one of which (`fullscreen`) is nearly Shape C without any of its cost.
- Set `path` on the action if you want a stable `/odoo/<path>` URL.

Reusing the search view from a client action is possible and shipped in core — it is the
strongest argument for B over C when a team thinks they need "a real app".

## The layer map

Trace a change through these, in order. Any one of them can be the broken link:

```
__manifest__.py glob   ─ decides whether the file exists at runtime at all
   └─ asset bundle     ─ ordered file list; order matters only for SCSS
       └─ module loader ─ defines @addon/path ids; resolves by dependency, not bundle position
           └─ registry  ─ the string-keyed inversion points (services, actions, views, …)
               └─ service / store ─ singletons in env.services; reactive or not
                   └─ component  ─ setup(), hooks, getters
                       └─ template ─ t-inherit resolved CLIENT-SIDE at first render
```

Two consequences worth internalising:

1. **Bundle order is not execution order.** The loader resolves by dependency edges; bundle
   position only breaks ties.
2. **Template inheritance is resolved in the browser**, not at build time — so a broken xpath
   ships green and fails at first render.

## Before you commit to a shape

- Name the forcing requirement, or choose B.
- If C: list, in the design note, which framework services you are giving up and who maintains
  the replacements.
- If B: confirm the chrome you keep is the chrome you want, and check whether
  `target=fullscreen` already covers the "kiosk" requirement.
- Either way, decide the bundle before writing the first file — see
  `odoo-owl-diagnostics` for why a file outside every glob fails silently.

Related: `odoo-owl-extending` (changing existing OWL code), `odoo-owl-state-data` (where state
lives), `odoo-owl-diagnostics` (why it did not run). Anti-pattern ids: `reference/owl/anti-pattern-catalogue.md`.
