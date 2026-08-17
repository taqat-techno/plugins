---
name: multi-tenancy-isolation
description: >-
  Design-time multi-tenant isolation rules for Odoo 14-19 — the decisions that are already
  wrong before anything raises. Owns the tenant-anchor contract (a nullable anchor disables
  isolation in four non-raising ways at once, so it is required, and a refactor that could
  null it re-anchors in the SAME change), NULL-kills-UNIQUE (a Postgres UNIQUE over a
  nullable column stops deduplicating — use a partial unique index), the host-gate brick
  rule (a deny-by-default gate in ir.http._authenticate / _pre_dispatch precedes route
  dispatch, so it also 404s /xmlrpc and /jsonrpc and leaves no channel to undo a bad
  hostname claim), Host resolution as two decoupled layers (db_filter vs
  get_current_website, so website_id is not a tenant boundary), isolation-comes-from-rendering
  (fields are instance-global whatever the branding), and ACL-is-not-isolation (portal users
  are blocked only by accidental default-deny). Activates on the artifact, not on a phase —
  when a tenant_id / company_id anchor is added, moved, made related= or compute=, or made
  optional; when an ir.rule domain is written or reviewed; when a UNIQUE, models.Constraint
  or index lands on a tenant-scoped model; when a route gate or ir.http override keys on
  hostname or website_id; when an ir.model.access.csv row is added to make a screen work;
  when a portal or frontend controller builds a domain from a tenant field; or when someone
  asks to run two brands, tenants, or websites on one instance. Not the audit-time scan of
  an existing module (odoo-security) and not test authoring or running (odoo-test).
version: 0.1.0
last_reviewed: 2026-08-10
owns:
  - the tenant-anchor contract (the anchor field is required; a nullable anchor disables isolation in four non-raising ways)
  - the re-anchor-in-the-same-change rule for refactors that move or null a tenant anchor
  - the NULL-kills-UNIQUE rule and the decision to replace the constraint with a partial unique index (the declaration syntax itself belongs to odoo-reviewer)
  - the host-gate brick rule (a pre-dispatch host gate also gates /xmlrpc and /jsonrpc; reserved hosts + resolver-side repair)
  - the two-layer Host resolution model (db_filter vs get_current_website) and why website_id is not a tenant boundary
  - the isolation-comes-from-rendering rule (fields on shared models are instance-global)
  - the ACL-is-not-isolation rule (a broad ACL row with no matching ir.rule; default-deny is accident, not design)
defers_to:
  - odoo-security for the audit-time scan of an existing module (ACL completeness, sudo() usage, route auth, SQL injection); this skill owns the design-time rules that decide what that scan should find
  - odoo-test for authoring and running the per-role reproduction, and for the HttpCase reliability caveat (HttpCase reads 200 + placeholder rather than 403 on denied Binary / /web/image routes, so it false-greens exactly the host-gated and attachment cases this skill cares about)
  - odoo-reviewer (references/v19_deltas.md) for the v19 declaration syntax itself — _sql_constraints tuples vs models.Constraint / models.UniqueIndex class attributes, and where they sit in class-attribute order
  - odoo-upgrade for cross-version migration mechanics when a pre-19 module has to gain a partial index through a migration script
  - theme-create for the exact per-website hook naming and available helpers (_theme_<module>_post_copy on theme.utils)
  - odoo-stack-doctor (references/db-safety.md) for per-instance separation at the deployment layer (own hostname / port pair / db_filter / filestore), which is a different boundary from tenant isolation inside one database
user-invocable: false
---

# multi-tenancy-isolation

## Purpose

Multi-tenant isolation in Odoo fails quietly. A missing record rule, a nullable anchor field, a
UNIQUE that stopped deduplicating, an ACL row added to unblock a screen — none of these raise, none
turn a test red, and all of them read as working software until one tenant sees another tenant's
rows. This skill holds the design-time decisions that determine whether isolation exists at all, so
the failure is caught while the field is being declared rather than after the leak.

## When to use

Activate when any of these appear:

- A model gains, loses, moves, or reshapes a tenant / company / owner anchor field (`tenant_id`,
  `company_id`, `owner_id`, or the project's equivalent) — especially when it becomes `related=`,
  `compute=`, or `store=True`.
- An `ir.rule` domain is being written or reviewed, particularly one with a `('<anchor>','=',False)`
  escape branch for platform-owned rows.
- A `_sql_constraints` UNIQUE, a `models.Constraint`, or an index is added on a tenant-scoped model.
- A route gate, controller, or `ir.http` override keys on **hostname**, `website_id`, or a
  sign-in domain.
- An `ir.model.access.csv` row is added because a screen 403s or a list renders empty.
- Someone asks to "isolate", "separate", or "white-label" two brands, tenants, or websites on one
  instance.
- A portal / frontend controller builds a search domain out of a tenant field.

Do NOT use this for auditing an already-written module for access findings — that is
**odoo-security**. This skill decides; that one scans.

Do NOT use this to write, generate, or run tests, even isolation tests — that is **odoo-test**
(and the framework's own testing skill outside Odoo). This skill states what must be proven; the
testing skill owns how to prove it and which harness is honest for a given route type.

## The isolation rules

### 1. Host resolution is two decoupled layers, and `website_id` is not a tenant boundary

Odoo resolves the request `Host` **twice, independently**: Host → database via `db_filter()`
(`odoo/http.py`, substituting `%h` / `%d` from `HTTP_HOST` into the `--db-filter` regex), and
Host → website via `website.get_current_website()` / `website.domain`
(`website/models/website.py`) *after* a database has already been selected. Nothing links the two.

And `website_id` is **shared by default**: records with `website_id = False` serve on **every**
domain, and an unmatched Host **silently falls back to the first website** instead of failing. That
fallback is the mechanism — an unknown or misconfigured hostname does not deny, it defaults, so a
boundary built on `website_id` opens rather than closes under error.

The single interception spine for per-request behaviour is the `ir.http` AbstractModel MRO
(`base` → `http_routing` → `website` / `portal` / `web`) via `_match` / `_authenticate` /
`_pre_dispatch` / `_dispatch` / `_post_dispatch` / `routing_map`. Hook **there**, not by inheriting
an arbitrary controller: controller inheritance only re-enters for requests that resolve to *that*
endpoint, so every route the module did not think of — a sibling list route, an export, `/web/image`,
another addon's controller — keeps the un-hooked behaviour, and the gap is invisible because the
routes you did override work. The `ir.http` methods run for every matched request, so a rule placed
there has no such gap. All real isolation is server-side (record rules, or `sudo()`-then-rescope);
anything enforced only in a template is a display choice, because the record was already read.

### 2. The tenant anchor must be `required` — a nullable anchor disables isolation four ways at once

Whatever field anchors a row to its tenant, it must be non-nullable. When it can be NULL, isolation
breaks in **four independent, non-raising** places:

1. **The record rule's NULL escape inverts.** The common rule
   `['|', ('tenant_id','=',False), ('tenant_id','=',user_tenant)]` — the escape that exists so
   platform-owned rows are visible to everyone — makes every NULL-tenant row **world-visible**.
2. **A portal ownership helper hides the row from its own tenant.** A `_owned()`-style helper pins
   `tenant_id = tenant.id` into the domain, so a NULL-anchored row is invisible to the tenant that
   owns it while remaining visible to everyone else. The two failures compound: wrong direction on
   both sides.
3. **A relation guard stops rejecting cross-tenant writes.** Guards that validate an m2o points at
   the same tenant almost always `continue` on a falsy anchor (to tolerate platform rows). A NULL
   anchor therefore skips the check entirely — cross-tenant writes are accepted.
4. **A domain built from it reads across tenants.** `[('tenant_id','=',rec.tenant_id.id)]` becomes
   `[('tenant_id','=',False)]`, which is a cross-tenant read, not an empty result.

None of the four raises. All four are reachable from the same single NULL.

### 3. If a refactor can null the anchor, re-anchor it in the SAME change

A stored-related or computed anchor (`tenant_id = fields.Many2one(related='parent_id.tenant_id',
store=True)`) becomes nullable the moment its source relation becomes optional, is replaced, or is
removed. The mechanism is that the field keeps existing and keeps reading — it just reads NULL —
so nothing signals the loss.

- Re-anchor to the **new** owner in the same commit (e.g. `related='category_id.tenant_id'` when
  `parent_id` goes away), and keep `required=True`.
- Never ship an intermediate state where the anchor is nullable "until the data migration lands":
  during that window rules 2.1–2.4 are all live.
- A write-time constraint cannot repair rows that are already NULL. If old data can already be
  NULL, put the guard in the **resolver / read path** too, so deploying the code is itself the
  repair.

### 4. A UNIQUE containing a nullable column stops deduplicating — use a partial index

Postgres treats NULLs as distinct, so a `UNIQUE (a_id, b_id)` silently permits unlimited duplicates
once either column is NULL. The constraint does not error and does not warn; it just stops being a
constraint for exactly the rows that most need one.

Use a **partial unique index** with the nullable column moved into the predicate instead: the
predicate removes the NULL rows from the index's scope entirely, so the remaining rows are compared
on columns that cannot be NULL and the uniqueness is real again. Odoo 19 exposes this directly
(declaration syntax and its place in class-attribute order belong to **odoo-reviewer**):

```python
_unique_active = models.UniqueIndex(
    "(parent_id, template_id) WHERE state = 'active'",
    "Only one active record per parent/template pair.",
)
```

On pre-19 codebases the equivalent is a `CREATE UNIQUE INDEX ... WHERE ...` issued from `init()` /
a migration, not a `_sql_constraints` entry — `_sql_constraints` cannot express the predicate.

### 5. A host-based route gate also gates RPC, so a bad hostname claim can brick the instance

A deny-by-default gate that decides "which tenant does this Host belong to" typically lives in
`ir.http._authenticate` or `_pre_dispatch`. Both run **after werkzeug has matched a rule but before
the endpoint executes, on every matched route** — and the RPC endpoints are ordinary `@route`s, so
the gate rejects `/xmlrpc/2/*` and `/jsonrpc` along with everything else. That makes a bad state
**unrecoverable over HTTP**: the exact channels an admin, a deploy script, or an external
integration would use to delete the offending row sit behind the gate that the row created. A
single tenant record claiming the instance's own hostname takes the whole instance down.

Design requirements for any host-keyed gate:

- **Reserve hosts explicitly and reject the claim at write time**: the deployment's own
  build/deploy hostname, the host in `web.base.url`, `localhost`, IP literals, and the hosting
  platform's build-host wildcards. Derive the reserved host from `web.base.url` rather than a
  second dedicated setting, because two settings drift: whoever moves the instance updates the one
  the framework already forces them to update, and the gate then defends a hostname nobody uses.
- **Carve the backend out by path**, not by inference: `/web` and `/odoo` must be excluded from any
  `is_frontend`-style deny logic explicitly. `is_frontend` is per-route metadata declared by the
  route itself, so a gate that infers "frontend" from anything else (a missing marker, a path
  prefix test, a website-present check) classifies backend routes as frontend and locks the
  operator out of the only UI that could delete the offending row.
- **Repair in the resolver too** (rule 3): a write-time constraint cannot fix a database that is
  already broken, because applying the fix requires the access the bug removed.
- **Keep the policy read outside any cached call.** `ir.config_parameter.set_param` clears only the
  `stable` ormcache; a model-level `@tools.ormcache` sits in the default cache, cleared by
  `registry.clear_cache()`. A config-driven guard placed *inside* a cached method keeps answering
  from the old configuration — the gate you "fixed" is still denying.
- **Verify reachability with a real POST**, e.g. a `common.version` call against `/xmlrpc/2/common`.
  The RPC routes are declared `methods=["POST"]`, so a GET is rejected by werkzeug's method check
  during routing — *before* dispatch, and therefore before the gate. The `405` you get back proves
  only that routing works; it says nothing about whether the gate would have let a real call
  through.

### 6. Per-tenant / per-website isolation comes from the rendering layer; fields are instance-global

Model fields are global to the database — Python-declared or XML manual fields alike. There is no
per-website or per-tenant field, so visual separation between two brands on one instance implies
nothing about data separation behind it.

- Put website-facing behaviour in a **pure inheriting presentation layer** (a `theme_*` module:
  XML / QWeb / assets only). No controllers, no model overrides — those apply to every website.
- The one sanctioned Python hook there is the `theme.utils` post-copy hook, which the framework
  invokes per website as the theme is applied, so its `enable_view` / `disable_view` effects land
  on that website's records only — the reason it is the exception to "no Python in a theme". Its
  exact method name (`_theme_<module>_post_copy`) and helper set belong to **theme-create**; do not
  restate them here.
- The leaks to watch: an unscoped QWeb override, and a field-attribute redefinition (e.g. flipping
  `translate=False` on a shared model's field) — both instance-wide even inside a per-brand module.
- Never promise "field-level isolation": the promise cannot be kept, because the field is a column
  on one shared table and every website reads that table. Promise scoped rendering plus server-side
  record rules.

### 7. A broad ACL row with no matching `ir.rule` is not isolation

An `ir.model.access.csv` row granting `base.group_user` `1,1,1,1` with **no `ir.rule`** lets every
internal user CRUD every tenant's rows. The dangerous half is why it *looks* fine: portal and public
users are blocked only **by accident** — no ACL row at all means default-deny. So the moment someone
adds an ACL row to make a portal screen work, the accidental protection disappears and cross-tenant
PII opens with it.

- Every ACL row on a tenant-scoped model ships **with** its `ir.rule` in the same change. Treat
  "it was already secure without a rule" as a statement about default-deny, never about isolation.
- The opposite-direction trap: a custom group implying **no** core group (`base.group_public` /
  `group_portal` / `group_user`) breaks framework reads on the render path. Diagnostic signature:
  **public route works, authenticated route 403s on a framework model** — the anonymous path is more
  privileged than the logged-in one. That is not "login is broken"; walk the render path and either
  `sudo()` each core read or verify it sudoes internally.

## Decision framework

| Question | Answer | Consequence |
|---|---|---|
| Can the tenant anchor ever be NULL? | yes | Isolation is already off (rule 2). Make it `required`; re-anchor in the same change. |
| Is the anchor `related=`/`compute=` on an optional source? | yes | It will null silently on refactor. Re-anchor, don't defer to a migration. |
| Does an `ir.rule` carry a `('<anchor>','=',False)` branch? | yes | That branch is world-visibility. It is only safe if the anchor cannot be NULL. |
| Does a UNIQUE include a nullable column? | yes | It has stopped deduplicating. Move the nullable column into a partial-index predicate. |
| Does a gate deny by hostname / sign-in domain? | yes | It also gates `/xmlrpc` + `/jsonrpc`. Reserve hosts, carve out `/web` + `/odoo`, guard in the resolver. |
| Is `website_id` being used as the tenant boundary? | yes | It is shared-by-default and falls back to the first website. Use a server-side rule anchored on a required field. |
| Is the separation between brands only visual? | yes | Fields are instance-global. Scope rendering in a pure theme layer; state that field-level isolation is not on offer. |
| Is an ACL row being added to unblock a screen? | yes | Ship its `ir.rule` in the same change; the previous safety was default-deny, not design. |

Ladder for "is this row isolated?" — every step must hold, in order:

```
anchor field exists on the model            --no--> not isolated (nothing to scope by)
        |yes
anchor is required / cannot be NULL         --no--> not isolated (4 silent failures, rule 2)
        |yes
an ir.rule scopes reads AND writes to it    --no--> not isolated (ACL alone is default-deny luck)
        |yes
the rule's NULL escape is provably unreachable --no--> world-visible rows exist
        |yes
uniqueness/indexes don't depend on it being nullable --no--> duplicates accumulate silently
        |yes
   ISOLATED (and only now)
```

## Validation checklist

- [ ] Every tenant-scoped model has an anchor field declared `required=True` (or an equivalent
      NOT NULL), and `SELECT count(*) ... WHERE <anchor> IS NULL` returns 0 on real data.
- [ ] Every `ir.rule` NULL-escape branch is justified in a comment and unreachable for tenant rows.
- [ ] Every ACL row on a tenant-scoped model has a matching `ir.rule` in the same change; no model
      relies on "no ACL row" for its protection.
- [ ] Every UNIQUE / index on a tenant-scoped model was checked for a nullable member; nullable
      members moved into a partial-index predicate (`models.UniqueIndex` on Odoo 19).
- [ ] Any host-keyed gate rejects the reserved set at write time (platform build host, `web.base.url`
      host, `localhost`, IP literals, build-host wildcards) **and** in the resolver.
- [ ] `/web` and `/odoo` are excluded from the gate by explicit path, and `/xmlrpc/2/common` answers
      a real **POST** (`common.version`) while the gate is active — a GET 405 proves nothing.
- [ ] No policy read sits inside an `@tools.ormcache`d method; cache invalidation path identified
      (`registry.clear_cache()` vs the `stable` cache cleared by `set_param`).
- [ ] Cross-tenant access is proven per role, asserting both the allow **and** the deny — a test
      whose fixture builds records with `sudo()` proves nothing, because `sudo()` is exactly the
      bypass of the record rules under test. Which harness makes that assertion trustworthy is
      **odoo-test**'s call, and it is not always `HttpCase`: on Binary / `/web/image` routes a
      denied read answers `200` with a placeholder rather than `403`, so an `HttpCase` assertion
      there goes green on a leak. Route those two cases (attachment routes, host-gated auth) to the
      controller/ACL-layer form odoo-test prescribes.
- [ ] Host-based behaviour is exercised by sending the header explicitly
      (`curl -H "Host: tenant.example" http://127.0.0.1:<http-port>/...`) rather than by relying on
      name resolution, so the test cannot pass or fail for resolver reasons. `*.localhost` is only
      dependable where the platform's resolver implements RFC 6761 for sub-names (systemd-resolved
      does; the Windows resolver does not), which is why per-instance `<name>.localhost` hostnames
      work as a dev convention (see odoo-stack-doctor `references/db-safety.md`) but must not be
      the mechanism a gate test depends on.

## Anti-patterns

| Anti-pattern | Why it fails | Do instead |
|---|---|---|
| Optional `tenant_id` "for platform-owned rows" | The rule's NULL escape makes those rows world-visible, the portal helper hides them from their owner, the relation guard stops rejecting, and derived domains read cross-tenant — all silent | Make the anchor required; model platform ownership as an explicit flag or a dedicated platform tenant |
| Reshape a model now, re-anchor `tenant_id` "in the follow-up" | The window between the two changes has isolation fully off, with nothing raising | Re-anchor to the new owner in the same commit and keep it required |
| `_sql_constraints` `UNIQUE (a_id, b_id)` where `b_id` is nullable | Postgres treats NULLs as distinct; the constraint stops deduplicating exactly the rows at risk | Partial unique index with the nullable column in the predicate (`models.UniqueIndex`) |
| Deny by hostname in `_pre_dispatch` without reserved hosts | The gate runs on every matched route before its endpoint, and the RPC endpoints are ordinary routes, so it rejects `/xmlrpc` and `/jsonrpc` too — no channel is left to delete the bad row | Reserve the platform host / `web.base.url` host / `localhost` / IP literals; guard in the resolver too |
| Block the frontend with `is_frontend` logic and assume the backend is safe | `/web` and `/odoo` fall inside frontend inference and lock the operator out | Carve `/web` and `/odoo` out by explicit path |
| Read the tenant policy inside an `@tools.ormcache`d method | `set_param` clears only the `stable` cache; the cached method keeps answering with the old policy after the "fix" | Keep policy reads outside cached calls; clear via `registry.clear_cache()` when they must be cached |
| Use `website_id` as the tenant boundary | `website_id = False` serves on every domain and an unmatched Host falls back to the first website — the failure mode is *open* | Anchor on a required tenant field with server-side record rules; hook `ir.http`, not a random controller |
| Add a model override or controller to a per-brand module | Model-layer changes are instance-global; only rendering is per-website | Pure `theme_*` layer (XML/QWeb/assets) plus the `theme.utils` post-copy hook for per-website setup (naming: theme-create) |
| Promise "per-website fields" | No such thing — fields are global to the database, Python- or XML-declared | Promise scoped rendering plus record rules; say field-level isolation is not available |
| Add an ACL row to make a portal screen work | Portal users were blocked only by accidental default-deny; the row opens every tenant's rows at once | Ship the `ir.rule` with the ACL row, in the same change |
| Read "authenticated route 403s, public route works" as a login bug | It means the custom group implies no core group, so an unelevated core-model read fails for the one account the screen exists for | Walk the render path; `sudo()` each core read or verify it sudoes internally |
| Prove isolation with a green unit-test suite | Fixtures usually build records with `sudo()`, which is the very bypass under test, so record rules are never exercised and a leak stays green | Assert per role, both allow and deny, in the harness **odoo-test** prescribes for that route type |

## Cross-references

- **odoo-security** (`skills/security/`) — the **audit-time** scan of an existing module: ACL
  completeness against declared models, route authentication, `sudo()` risk, SQL injection,
  record-rule coverage reporting. This skill owns the **design-time** rules that decide what a clean
  scan should mean; that skill finds where they were not followed. (It defers back here for the
  tenant-isolation rules themselves — do not restate them there.)
- **odoo-test** (`skills/test/`) — authoring and running the per-role reproduction, and the owner of
  the harness caveat: a denied Binary / `/web/image` read answers `200` with a placeholder, so that
  route type must be asserted at the controller/ACL layer instead of by HTTP status.
- **odoo-reviewer** (`skills/reviewer/references/v19_deltas.md`) — the owner of the v19 declaration
  syntax quoted in rule 4 (`_sql_constraints` tuples → `models.Constraint` / `models.UniqueIndex`
  class attributes, and their position in class-attribute order).
- **odoo-upgrade** (`skills/upgrade/`) — migration mechanics when a pre-19 module has to acquire a
  partial index through a migration script rather than a declaration.
- **theme-create** / **theme-design** (`skills/theme-create/`, `skills/theme-design/`) — the pure presentation layer rule 6
  requires, and the exact per-website post-copy hook name and helper set.
- **odoo-stack-doctor** (`skills/stack-doctor/references/db-safety.md`) — separation at the
  *deployment* layer (one hostname / port pair / `db_filter` / filestore per instance). That is a
  different boundary: it keeps two instances apart, and says nothing about two tenants inside one
  database, which is the only thing this skill governs.
