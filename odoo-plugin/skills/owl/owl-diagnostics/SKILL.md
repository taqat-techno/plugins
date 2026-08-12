---
name: odoo-owl-diagnostics
description: |
  Diagnose Odoo 17-19 OWL front-end problems that produce NO error — a file in no asset bundle, a patch that did not apply, a registry entry nobody read, a template xpath that failed at first render, a stale asset cache. Covers the ordered triage checklist, browser-console introspection of the module loader and registries, which rebuild each kind of edit actually needs, and how to prove a change is live rather than assuming it.

  <example>
  Context: User's new JS file appears to do nothing.
  user: "I added the file and nothing happens, no error in the console"
  assistant: "Silence is the signature of a bundle-membership problem. Let me prove the file is in a bundle before looking at anything else."
  <commentary>Rule one: a file outside every glob never executes and produces no build error.</commentary>
  </example>

  <example>
  Context: User edited a static file and does not see the change.
  user: "I changed the SCSS but the page looks the same after restarting Odoo"
  assistant: "Restarting doesn't rebuild assets. Let me check which bundle you actually loaded and clear the right cache."
  <commentary>Assets are cached independently of the server process.</commentary>
  </example>

  <example>
  Context: User asks whether their change works.
  user: "The server started fine so the fix is good, right?"
  assistant: "A green terminal isn't evidence for an OWL change — let me verify at the layer the change lives."
  <commentary>A live server happily serves a frozen bundle.</commentary>
  </example>
---

# Diagnosing OWL problems that produce no error

Almost every OWL failure mode is **silent**. Before debugging behaviour, prove the code runs.

## The ordered checklist

Work top to bottom. Most "my patch doesn't work" investigations end at step 1 or 2 — after an
hour spent at step 6.

1. **Is the file in a bundle?**
   `odoo.loader.factories.has("@my_module/app/my_file")`
   Server side, ask the asset model for the bundle's resolved path list and filter for yours.
   *Signature of failure*: no error at all, or a consumer reporting "needed by other modules but
   have not been defined".

2. **Did the module throw while loading?**
   `[...odoo.loader.failed]` and `odoo.loader.findErrors()`
   Read the **first** `Error while loading "<name>"` — later "unmet dependencies" lines are
   fallout. A top-level throw aborts everything below it in the file, including your
   registration.

3. **Is the import path real?** There is no build-time resolution — a wrong `@addon/path` is
   invisible until runtime. `odoo.loader.factories.get("@addon/path")` before you rely on it.
   Core doc comments have been observed pointing at paths that moved.

4. **Prototype or class?** `patch(Cls, …)` adds a static instances never call.
   `Object.getOwnPropertyDescriptor(Cls.prototype, "m").value.toString()`

5. **Did the patch land on a name that still exists?** A patch on a renamed method is silently
   additive — it installs as a brand-new property.

6. **Was the registration read?** One-shot categories are snapshotted once by their consumer.
   ```js
   const {registry} = odoo.loader.modules.get("@web/core/registry");
   Object.keys(registry.subRegistries);
   registry.category("my_category").content
   ```
   A mistyped category silently creates a fresh empty one.

7. **Load order.** Order comes from manifest glob order and the module topological sort — not
   from registration order or import order.

8. **Template xpath.** Resolved **client-side at first render**, so failures appear in the
   browser, never at build. `Element '<xpath …>' cannot be located in element tree`.

## Reproduce registration and prop bugs with debug on

Registry schema validation and OWL prop validation both short-circuit when `odoo.debug` is
falsy. The loader also **clears `odoo.debug` unless `?debug` is in the URL** — so the server
session can be in debug while the client is not.

Navigate with `?debug=assets` explicitly and confirm with `odoo.debug` in the console.

## Match the rebuild to the edit

Most edits need neither a module upgrade nor a restart. Picking the wrong row is the main time
sink in OWL work.

| Edit | What it needs |
|---|---|
| Python code | **restart** (`sys.modules` is never reloaded) |
| Manifest / views / new fields / security | `-u <module> --stop-after-init` |
| Existing file under `static/src` | clear the assets cache + hard reload |
| **New** file matching an existing glob | regenerate assets (see below) |
| `.po` used by JS translations | restart |

### The new-file trap

There are **two independent caches**: the file list (ormcached) and the generated URLs.
`?debug=assets` bypasses only the second. A brand-new file matching an existing glob is simply
**absent** — no error, no 404, nothing in the loader.

Fix it by regenerating assets from the debug menu, restarting, or running the server with the
XML dev mode.

## Prove which bundle you loaded

`?debug=assets` is a *session* flag, so a later fetch without the parameter is still in debug
mode. You cannot use it to prove the normal bundle updated.

View-source and read the `<script src>` segment: a short hex checksum means the normal
bundle, the literal `debug` means the debug one. Verifying a fix only against the debug bundle
and shipping a broken minified one is a real failure mode.

If the app registers a service worker, clear its cache too — it typically caches every GET.

## "The server started" is not evidence

Assets are cached independently of the process, so a live server serves a frozen bundle. For an
OWL change, verification means:

1. the app responds (an HTTP check on a known route),
2. the server log has **zero** `ERROR`-level lines — match the level field, never `grep -i error`,
   since tests and expected-exception paths log the word legitimately,
3. **and** you loaded the actual screen and read the browser console.

Verify at the layer the change lives, with the cheapest test that binds: unit tests for record
classes and store methods, a component test for one screen, a tour for multi-screen sequencing,
and a Python test for every server-side computation. Read the summary line and exit code — not a
log grep.

A test can only see its own addon's declared dependencies: a patch "tested" from an addon that
does not depend on the patched one was never loaded at all.

## Read the current source, not documentation or memory

Trees carry stale comments, dead code, and docstrings that disagree with the code beside them.
Grep the symbol; if the only hits are a comment and a translation file, it is dead. See the
stale-pattern index in `reference/owl/anti-pattern-catalogue.md` for idioms that are widely
documented online and provably absent from Odoo 19.

## Distinguish proven from inferred

When reporting, mark claims explicitly: `[INFERRED]`, `[UNVERIFIED]`, `[GAP] <what you looked at>`.
Cite `<module>/<path>` only after reading it. Unmarked inference is how a wrong belief becomes
permanent across sessions.

## Automate the mechanical half

```
/owl lint <module-path>          # full scan
/owl lint <module-path> --severity error
```

`scripts/owl/owl_lint.py` implements the detectable subset of the anti-pattern catalogue —
bundle membership, registry placement, patch shape, service capture, xpath fragility, N+1 RPC,
and the stale-pattern index.

Related: `odoo-owl-extending`, `odoo-owl-state-data`, `odoo-owl-architecture`.
