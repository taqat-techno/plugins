---
name: odoo-owl-extending
description: |
  Safely extend existing Odoo 17-19 OWL code from your own addon — patch() semantics and ordering, t-inherit template extension, registry categories and which are one-shot, extending services and stores, and the fixed menu of extension points. Covers the rules that prevent silent breakage: always super(...arguments), prototype vs class, inline extension literals, never the three-argument patch, never copy a core component, never force-replace a registry entry.

  <example>
  Context: User wants to change behaviour in a core OWL component.
  user: "I need to add a button to the POS product screen"
  assistant: "That's patch(ControlButtons.prototype) plus a t-inherit xpath, shipped in the same commit. Let me check the current seam first."
  <commentary>There is no control-button registry in Odoo 19; patch + t-inherit is the shipped pattern.</commentary>
  </example>

  <example>
  Context: User's patch appears to do nothing.
  user: "I patched the method but the original still runs"
  assistant: "Let me check prototype vs class, whether the file is in the bundle, and whether the method name still exists upstream."
  <commentary>A patch on a renamed method is silently additive — it installs as a brand-new property.</commentary>
  </example>

  <example>
  Context: User wants to replace a core service.
  user: "How do I override the pos service with my own?"
  assistant: "Re-registering it is last-writer-wins and breaks silently. Patch the service definition instead."
  <commentary>force:true means the next addon that forces the same key discards you.</commentary>
  </example>
---

# Extending Odoo OWL code without breaking it

## The extension menu is fixed

Before writing anything, find which of these the change actually needs. Re-implementing a
mechanism that already exists is the most expensive mistake here, because it diverges at the
next upgrade.

| Want to change | Use | Not |
|---|---|---|
| JS behaviour on an existing class | `patch(X.prototype, {...})` | copying the class |
| Markup everyone should see | `t-inherit` + `t-inherit-mode="extension"` | copying the template |
| A genuinely new *noun* (page, model class, handler) | the registry category | a switch statement |
| Server data reaching the client | the module's declared loading contract | an ad-hoc RPC in a component |
| A coexisting variant of a component | `primary` template + subclass | editing the original |

Grep the target module for its loading-contract methods, `registry.category(`, and `t-inherit`
before touching anything.

## patch() — the six rules

1. **Two arguments, never three.** `patch(obj, "name", ext)` **throws on sight** in Odoo 19.
2. **Always `super.method(...arguments)`.** Omitting `super` drops the base implementation *and
   every earlier patch in the chain* — and the symptom usually lands on a different addon.
   Forwarding positionally silently discards a parameter added upstream.
3. **Prototype for instance behaviour, the class for statics.** Neither form throws.
   `patch(Cls, {method(){}})` adds a static instances never call. `patch(Cls.prototype, {staticField})`
   never reaches the reader, which reads it off the class. Check which the reader uses.
4. **Write the extension object inline at every call site.** `patch()` *mutates* the extension
   to build the super chain, so reusing one literal across two targets silently rewires the
   first target's chain.
5. **Never assign to a prototype directly.** `Cls.prototype.x = fn` creates no skeleton: `super`
   is unavailable inside it, and a later `patch()` of the same key records *your* function as
   "the original".
6. **In tests always `patchWithCleanup`.** Nothing unpatches between HOOT tests, so a bare
   `patch()` leaks into every later test in the run and passes in isolation.

### Patch a declared seam, not a private method

A patch on a name that no longer exists is **silently additive** — the property installs as
brand new and `super.thatMethod()` throws only if you call it. `setup()` exists to be patched;
core says so in a comment. Instance fields assigned in a constructor shadow prototype patches
entirely.

Verify after boot: `Object.getOwnPropertyDescriptor(Cls.prototype, "m").value.toString()`.

### Assume you are neither first nor last

Patch order is the module topological sort, keyed `(not application, sequence, name)` before
`depends` is applied. Two addons patching the same method with no dependency edge between them
can flip on a one-line manifest change elsewhere.

Either declare the real `depends` edge, or make the patch commutative: spread `super`, never
assume an initial value, never mutate an argument another patch may still read.

## Templates

- **Never copy a core template.** Both ship. Core's original keeps being extended by every other
  addon — those extensions land on the original while your users see the frozen copy, and
  upstream fixes never reach you.
- **`extension` vs `primary`.** `extension` changes what everyone sees. `primary` creates a
  coexisting variant and *freezes the parent at that point*, so later extensions never reach it —
  pair it with a subclass. Always state `t-inherit-mode` explicitly.
- **Anchor xpaths on semantic classes.** Positional predicates and text matches break silently.
  Template xpaths resolve **client-side at first render**, so a broken one ships green.
- **Renaming a non-utility CSS class is a breaking change** for every downstream addon whose
  xpath anchors on it — with no build-time warning.
- **Ship the JS patch and its XML extension in the same commit and bundle.** A patched method a
  template must call is inert without the matching `t-inherit`, and vice versa.

## Registries

- **Register at module top level.** Never inside `setup()`, `onWillStart`, a service `start`, or
  a lazily-imported module.
- **Know which categories are one-shot.** Live categories (`services`, `main_components`,
  `systray`, `error_handlers`, `web_tour.tours`) re-read after boot. Others are snapshotted once
  by their consumer at construction — anything registered later is silently ignored, and the
  failure looks like an unmatched route falling back to a default screen.
- **A mistyped category name creates a fresh empty registry** and never errors. Grep the string
  first; if it appears exactly once in the tree, that occurrence is the bug. The TypeScript
  surface is not authoritative — it omits real categories and misspells one of its own keys.
- **Do not invent a registry** where core solves the same problem with `patch`.

## Services and stores

- **Never re-register a service.** Without `force` you get a duplicate-key error *at import
  time*, which aborts the rest of that file's top-level code and can take unrelated
  registrations down with it. With `{force: true}` it is last-writer-wins by topological order,
  and a `force` after boot does nothing at all.
- **Patch the definition object instead**, and choose deliberately: patching the *definition*
  changes every future `start()`; patching an *instance* changes one object.
- **Inside a component, always `useService("x")`** — never `env.services.x`. The hook wraps the
  service in `useState` when it is reactive; capturing it directly means the component **stops
  re-rendering**. This is the single most common OWL bug in Odoo code. `env.services.x` is
  correct only outside a component.
- **A store is reactive; a capability is not.** A store returns `reactive(this)` or extends
  `Reactive`. A non-reactive service never drives a render.

## Verify the extension actually landed

```js
// is the file in the bundle at all?
odoo.loader.factories.has("@my_module/app/my_file")
// did the module throw while loading?
[...odoo.loader.failed]; odoo.loader.findErrors()
// did the patch reach the prototype?
Object.getOwnPropertyDescriptor(Cls.prototype, "myMethod").value.toString()
// what is actually in the category?
const {registry} = odoo.loader.modules.get("@web/core/registry");
registry.category("my_category").content
```

Run `/owl lint <module>` to catch the mechanical mistakes before review.

Related: `odoo-owl-architecture` (which shape), `odoo-owl-state-data` (where state lives),
`odoo-owl-diagnostics` (why it did not run). Ids: `reference/owl/anti-pattern-catalogue.md`.
