---
title: Application dependencies (ragtools) discovered by the v0.18.0 plugin work
topic: issues
status: drafted — NOT filed
target-repo: taqat-techno/rag
plugin-release: v0.18.0
date: 2026-08-02
---

# Application dependencies — A-01 … A-09

Nine ragtools defects found while implementing the plugin's retrieval upgrade. **These are drafts, not filed issues** — filing is a GitHub write and needs explicit permission (workspace `CLAUDE.md`: "never push or commit any update before asking my permission").

Each carries the plugin-side mitigation shipped in v0.18.0 and the condition that retires it. Two of them (**A-01**, **A-02**) let the plugin *delete* a workaround rather than carry it, so they are worth filing first. One (**A-04**) cannot be mitigated plugin-side at all.

Evidence base: `C:\MY-WorkSpace\rag\RAG_MCP_CLAUDE_CAPABILITY_AND_PLUGIN_UPGRADE_REPORT.md` (§32 carries the reproduction commands), plus this session's measurements against the live `:21420` service running v3.5.1.

---

## A-01 (P0) — `search_knowledge_base`'s docstring promises the unscoped search its own guard refuses

**Why this is not merely a doc bug:** the docstring **is** the MCP tool description. It is not documentation *about* the API — it is the API's user interface for an LLM, shipped with the tool. Every agent that reads it learns the wrong contract, and no amount of plugin text fully overrides a description that travels with the tool.

`src/ragtools/integration/mcp_server.py:323`:

```
Scope:
  - Pass neither ``project`` nor ``projects`` → search ALL indexed content.
```

`src/ragtools/retrieval/scope.py:78-83` via `service/owner.py:1256` (`allow_unscoped=False`, and no HTTP route passes `True`):

```
$ curl -s -w " [%{http_code}]" "http://127.0.0.1:21420/api/search?query=x&top_k=1"
{"detail":{"error_code":"SCOPE_UNRESOLVED","error":"no project scope resolved; refusing
to search globally. Pass an explicit project/projects, or opt in to an authorized
global search."}} [422]
```

**Ask:** rewrite the `Scope:` block on `search_knowledge_base` and `search_project_context` to state the refusal, and **add a test asserting the docstring contains no phrase promising an unscoped global search**. The class of defect is "the description drifted from the guard"; only a test pins that.

**Consider:** an explicit `all_projects: bool = False` parameter that opts into `allow_unscoped=True`. "Search all my projects for X" is a legitimate request currently expressible only as `projects=[<every id>]`.

**Plugin mitigation:** rule, skill, and hook all teach the scoped form; a structural test fails the build if any artefact emits an unscoped call.
**Retires:** the plugin's need to contradict the tool's own description.

---

## A-02 (P0) — the text formatter re-prefixes an already-prefixed path

`indexing/scanner.py:401-410` (`get_project_relative_path`) returns `"{project_id}/{rel}"`. `retrieval/formatter.py:12` (`_loc`) prefixes `project_id/` **again**. Same defect at `:136` (`format_definitions`), `:160` (`format_secret_audit`), `:180`, `:243`.

Measured:

```
structured file_path : rag/docs/decisions.md            -> exists
formatted context    : rag/rag/docs/decisions.md        -> does not exist
```

Framework hits are triple-prefixed: a corpus storing `odoo/odoo/addons/…` renders as `odoo/odoo/odoo/addons/…`.

Every citation on every text-returning surface — MCP default output, CLI search, admin panel — is unopenable. `structured=True` is unaffected, which is what proves the defect is in rendering rather than storage.

**Ask:** make `_loc` conditional — do not prefix when `file_path` already starts with `f"{project_id}/"`. One conditional, five call sites.
**Test:** for every result whose `project_id` is a prefix of `file_path`, the rendered location equals `file_path`.

**Plugin mitigation:** `scripts/citation_path.py` — one conditional strip keyed on the scoped project id, then an existence check. Idempotent, so it becomes a no-op rather than a second defect when this ships.
**Retires:** `scripts/citation_path.py` and `rules/mcp-envelope.md` §6.

---

## A-03 (P1) — the scope contract is not uniform across retrieval entry points

| Entry point | `resolve_scope`? | Unscoped behaviour |
|---|---|---|
| `owner.search` (`/api/search`) | yes | **422** |
| `owner.search_project_context` (`/api/dev-search`) | yes | **422** |
| `owner.find_definitions:1419` (`/api/definitions`) | **no** | **200**, spans every project and framework corpus |
| `owner.audit_secrets:1437` (`/api/secret-audit`) | **no** | **200**, scans everything |

Measured: an unscoped `find_definition(symbol="Settings")` returned three hits, all `project_id: "odoo"` — a **framework corpus**, not a project.

**Ask:** either apply `resolve_scope` to all four, or document the asymmetry deliberately in both docstrings. Today it is neither stated nor consistent, so no caller can form one rule.
**Also:** add `scope` to definition output so a cross-project hit is never mistaken for a local one.

**Plugin mitigation:** both rules taught explicitly; scope passed anyway.

---

## A-04 (P1) — proxy-mode retrieval enforces neither capability nor scope

**The plugin cannot mitigate this.** It does not sit in the request path.

`_direct_search`, `_direct_dev_search`, `_direct_find_definition` each call `_capability_error()` **and** `_authorized_scope()`. Their proxy counterparts — `_proxy_search:1330`, `_proxy_dev_search:1371`, `_proxy_find_definition:1454`, `_proxy_secret_audit:1527` — call **neither**; they forward the caller's arguments plus an `X-Client-Profile` header.

`mcp_common.py:56-62` states the header exists "so the SERVICE re-checks the same capability the MCP process already checked … the service is where the decision has to be re-made." Grepping `X-Client-Profile` across `src/ragtools/service/` returns exactly one consumer: `destructive.py:214`. No retrieval route reads it; `routes.search:439` takes only query parameters and has no `Request` object to read a header from.

Net: for a scoped client in **proxy mode — the normal mode** — an omitted `project` is refused by `resolve_scope` (so nothing leaks), but a *foreign* project id the profile does not permit is **not checked**.

`tests/test_client_scope_enforcement.py:135-179` parameterises over `_direct_search`, `_direct_dev_search`, `_direct_find_definition` only. There is no proxy-path equivalent, which is why the gap is invisible to CI.

**Scope, stated fairly:** the single-owner default (`allowed_projects: None`) is unaffected. v3.5.1's own notes already concede the header "is not a defence against a hostile local process" — this finding is narrower and different: it is a gap against a **cooperating** restricted client, which is exactly what the header was introduced to bind.

**Ask:** read the profile in the retrieval routes via `destructive.request_profile(request)` and apply `mcp_authz.scope_for_search` server-side, as `_direct_*` does. **Extend the existing AST test to the `_proxy_*` entry points.**

**Plugin mitigation:** none possible. `rules/mcp-envelope.md` §9 forbids the plugin from ever describing client profiles as isolating retrieval, and `/doctor` warns when `RAG_CLIENT_PROFILE` is set.

---

## A-05 (P1) — five of six core tools have no structured error channel

`search_project_context`, `find_definition`, `secret_audit`, `list_projects`, `index_status` return prose only. A proxied HTTP error is stringified at `mcp_server.py:1359`:

```
[RAG ERROR] Service returned 404: {"error":"UNKNOWN_PROJECT","message":"no registered
project 'x'; refusing to fall back to the shared collection (that would read another
project's data)","remediation":"check the project id against /api/projects"}
```

An excellent server-side error — named, with a remediation — flattened into a string. The MCP layer's own advice ("branch on `error_code`") is therefore unfollowable for those tools.

**Ask:** extend `structured=True` to the other core tools; on the proxy error path, parse the JSON body and surface `meta.error_code` rather than stringifying the whole response.

---

## A-06 (P1) — no machine-readable tool inventory

`GET /api/mcp-config` returns launch configuration only:

```json
{"config": {"mcpServers": {"ragtools": {"command": "…\\rag.exe", "args": ["serve"]}}}}
```

Every consumer therefore transcribes the tool list by hand and each drifts differently — ragtools' own `mcp_server.py` module docstring says "3 core" when six carry the decorator; the plugin's said 21 of 30.

**Ask:** return per-tool metadata — `name`, `tier`, `enabled`, `mutating`, `destructive`, `requires_proxy`, `confirm_token_field`, `cooldown_seconds`, `capability_group`.
**Retires:** the plugin's static Tier 1–2 tables (D-035's stated end state — a deletion, not a rewrite).

---

## A-07 (P2) — `set_project_mode` has no cooldown

`mcp_common.py:100-111` — `WriteCooldown.DEFAULTS` covers eight write tools. `set_project_mode` is absent, so `check()` returns `None` (window `0.0`) and `_cooldown_guard` never fires; `mark()` is called and does nothing. It is the only write tool with no rate limit, and it triggers a delete-aware reindex.

**Ask:** register it. Suggested 5.0 s.
**Plugin mitigation:** typed confirmation is treated as its only guard, and the plugin never auto-retries it.

---

## A-08 (P2) — mixed naive-local and UTC timestamps

`last_indexed` / `historical_as_of` are naive local time; the MCP envelope's `as_of` is UTC:

```
as_of        2026-08-01T20:33:00+00:00   (UTC)
last_indexed 2026-08-01T22:39:05.701763  (naive local, UTC+3)
```

A consumer subtracting them gets a **negative** age — "indexed in the future".

**Ask:** emit ISO-8601 with an offset, or document the mixture at every emission point.
**Plugin mitigation:** never subtract; use the server's `freshness.age_seconds` / `state`.

---

## A-09 (P2, new in this session) — `/identity.install_mode` is inverted for packaged installs

`service/routes.py:379-382`:

```python
def _install_mode() -> str:
    import ragtools
    return "packaged" if "site-packages" in (getattr(ragtools, "__file__", "") or "") else "source"
```

A **PyInstaller bundle** puts the package under `_internal/`, which contains no `site-packages` — so a genuinely packaged installation reports `source`. Measured on the live installed service:

```
$ curl -s http://127.0.0.1:21420/identity
install_mode : source        <- wrong; the binary is …\Programs\RAGTools\rag.exe
profile      : installed     <- right, but see below
data_dir     : C:\Users\ahmed\AppData\Local\RAGTools\data
```

`profile` is unreliable in the opposite direction: `os.environ.get("RAG_PROFILE", "installed")` defaults to `"installed"`, which is exactly how a developer runs from source. **Neither self-report can be trusted alone.**

**Ask:** detect the frozen case (`getattr(sys, "frozen", False)` / `sys._MEIPASS`) as `packaged`, and treat `site-packages` as one of several packaged signals rather than the only one.
**Plugin mitigation:** `install_kind` is inferred from `data_dir` — a property of where the bytes are, not of a string the process computed about itself.

---

## Filing order

1. **A-01** and **A-02** — each retires a plugin workaround.
2. **A-04** — the only one with no plugin-side mitigation.
3. **A-06** — unlocks generated inventories and retires D-035's static tier.
4. **A-03**, **A-05**, **A-09**.
5. **A-07**, **A-08**.

Reproduction commands for every item are in the investigation report's §32 validation log.
