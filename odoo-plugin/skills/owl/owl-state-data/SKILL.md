---
name: odoo-owl-state-data
description: |
  Decide where state lives in an Odoo 17-19 OWL front-end and how server data reaches the client. Covers the state-ownership questions (backend field / record uiState / store / getter / component useState), the four ways a value escapes reactivity, why copying store data into useState silently loses edits, relation mutation by command, the declared data-loading contract versus ad-hoc RPC, and payload exposure review.

  <example>
  Context: User adds component state that resets unexpectedly.
  user: "My selected filter resets every time I switch screens"
  assistant: "That's a state-ownership question. Let me run the four questions — this one probably belongs on the store, not in useState."
  <commentary>State that survives a screen switch cannot live in component state.</commentary>
  </example>

  <example>
  Context: User reports the UI not updating.
  user: "I change the value and the console shows it changed but the screen doesn't repaint"
  assistant: "That's a reactivity escape. Let me check the four known ones before calling it a rendering bug."
  <commentary>toRaw, markRaw, constructor-captured callbacks, and not re-reading are the four escapes.</commentary>
  </example>

  <example>
  Context: User wants new server data in the client.
  user: "I need the customer's credit limit available in the UI"
  assistant: "That goes through the loading contract, not an RPC in the component — and adding a field to the payload is an exposure decision."
  <commentary>Ad-hoc component fetches diverge from the store the moment the record updates.</commentary>
  </example>
---

# State ownership and data loading in OWL

## Where does this state belong? Four questions, in order

Answer them in order and stop at the first yes. Put the answer in the PR description.

1. **Does it survive a page reload?** → a backend field, or the record's `uiState` channel.
2. **Is it per-record?** → the record's `uiState`.
3. **Does it survive a screen switch, or is it read by another component?** → the store.
4. **Is it derivable from other state?** → a **getter**, not a stored value.

Only if all four are no does it belong in component `useState`.

Getting this wrong produces three recognisable symptoms: state resets on navigation (should
have been store), vanishes on reload (should have been persisted), or two components disagree
(two sources of truth).

## Never copy store data into component state

```js
// WRONG — a snapshot. It never tracks the store again, and edits are lost at sync.
this.state = useState({ lines: this.pos.getOrder().lines });

// RIGHT — derive on read.
get lines() { return this.pos.getOrder().lines; }
```

`useState(obj)` does not *own* the object, it **subscribes** the component to it. A record, or
an array of records, assigned into a fresh literal is a snapshot — and serialization reads the
record, not your copy, so user edits disappear at sync with no error.

The one legitimate cache is a derived index whose invalidation you name explicitly, via
`useEffect` with a real dependency array.

## The four ways a value escapes reactivity

Before calling something a rendering bug, rule these out:

1. **Mutating through `toRaw(x)`** — you hold the raw object, not the proxy.
2. **Mutating a `markRaw`ed bag** — deliberately outside reactivity; core parks scratch state
   there on purpose.
3. **A callback captured in a `constructor`** — mutates the raw instance invisibly. This is
   exactly what the `Reactive` base class exists to prevent.
4. **Not re-reading** — the subscription is created *by the read*, and every notification clears
   all subscriptions. Reading outside a render never subscribes.

Diagnose: `__OWL_DEVTOOLS__.toRaw(obj) === obj` being true means you hold the raw object.

**Lazy getters have a matching trap**: a getter whose inputs are *not* reactive — `DateTime.now()`,
a module-level variable, a deliberately unwatched bag — returns its first value **forever**.
Opt out via the class's excluded-lazy-getters list.

## Prefer a getter to a stored value

Recomputing a total into `this.state.total` on every mutation creates two sources of truth and a
synchronisation obligation you will miss in one branch. Core derives everything of consequence —
totals, finalised flags, filtered product lists — as getters. On records and stores these are
lazily memoised and invalidated by reactive dependencies, so the performance objection is
already answered.

**Detect in review**: an assignment whose right-hand side is a pure function of other reactive
state.

## Relations change by command, never in place

```js
// WRONG — bypasses two-sided bookkeeping, leaves the inverse side stale
order.lines.push(line);
order.lines = [...];

// WRONG — raw is a deep-immutable clone; this throws
record.raw.field = 1;

// RIGHT
record.update({ lines: [...commands] });
```

Relation fields are generated accessors over two-sided bookkeeping. An in-place mutation skips
the connect/disconnect step. And a component holding the *old* array reference keeps rendering
the old array, because subscriptions come from reads — assign, then re-read through the store.

## UI state does not belong on a persisted record

Adding `is_selected` / `show_details` as a real server field means it round-trips on every sync,
becomes visible to every other device, and enters the payload a reviewer must classify.

Use the record's `uiState` channel — kept in one object by convention, persisted locally rather
than to the server. For a client-only *relation*, declare it in the class's extra-fields with a
`local` marker so serialization skips it.

## Data loading: the contract, not an RPC

New server data enters through the module's **declared loading contract** — the small set of
mixin methods that decide which models load, with what domain, and which fields. Plus, for
on-demand data, a public method returning `{model: rows}` merged into the same store.

Ad-hoc RPC inside a component is the anti-pattern: the data diverges from the store the moment
the sync bus or a later load updates the record.

Two failure modes worth knowing:

- **A JS class member whose name matches a loaded Python field crashes the boot** with a hard
  throw naming your property. Prefix client-only additions, or declare them as local extra fields.
- **Dropping `...super` from a patched options getter silently deletes persistence.** Those
  getters list the local database tables; returning a fresh object removes the core ones and
  orders vanish on reload with no error. Always spread.

## Adding a field to the payload is an exposure decision

Six questions before you widen the payload:

1. Who sees it? Everyone with the app open — plus anyone reading their local database.
2. Does it carry `groups=`?
3. Is it commercially sensitive?
4. Is it a secret?
5. Does it widen the load domain?
6. Is company containment explicit?

Question 2 is the sharp one. **A field carrying `groups=` blanks the whole model** for users
outside that group, because the loader catches the access error per model and substitutes an
empty list behind an INFO log line. The symptom is a blank screen with no error anywhere.

And treat client-sent numbers as **assertions**: recompute derived artefacts from inputs at the
state change that makes them binding. Never let a ledger read a client subtotal.

## N+1

An awaited RPC inside a loop is one network round trip per iteration. Batch it — one call with a
domain or a list of ids. `/owl lint` flags this as `D2`.

Related: `odoo-owl-extending` (how to patch the loading methods), `odoo-owl-diagnostics`
(why data never arrived). Ids: `reference/owl/anti-pattern-catalogue.md`.
