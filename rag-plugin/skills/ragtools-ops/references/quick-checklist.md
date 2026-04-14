---
title: Quick Support Checklist
topic: triage
relates-to: [post-install-verify, known-failures, repair-playbooks, paths-and-layout]
source-sections: [§20, §21]
---

# Quick Support Checklist

A one-page triage for "ragtools isn't working — where do I start?". Use this when you don't yet know what's wrong.

## Step 1 — Is the service alive?

```bash
curl http://127.0.0.1:21420/health
```

| Result | Meaning | Next |
|---|---|---|
| `{"status":"ready",...}` | Service is up | Step 2 |
| Connection refused | Service is down | Step 4 (start it) |
| HTTP 500 / hangs | Service is broken | Step 5 (logs) |

## Step 2 — Are projects loaded?

```bash
curl http://127.0.0.1:21420/api/projects
```

| Result | Meaning | Next |
|---|---|---|
| Non-empty list | Config is loaded — proceed to step 3 | Step 3 |
| `[]` | Config didn't load — F-006 | `repair-playbooks.md#projects-empty-after-restart` |

## Step 3 — Is the index ready?

```bash
curl http://127.0.0.1:21420/api/status
```

Look at the `last_indexed` and `chunks` fields. If chunks > 0 and `last_indexed` is recent, search should work. If chunks = 0, run `rag rebuild` or check the watcher (`/api/watcher/status`).

## Step 4 — Service is down: try to start it

```bash
rag service start
```

Then wait ~10 seconds and re-run step 1. If it still fails:

```bash
rag service run
```

This runs in the foreground and shows startup output directly. Look for `ERROR` lines.

## Step 5 — Read the logs

| Platform | Path |
|---|---|
| Windows | `%LOCALAPPDATA%\RAGTools\logs\service.log` |
| macOS | `~/Library/Application Support/RAGTools/logs/service.log` |
| Dev mode | `./data/logs/service.log` |

Match log substrings against the table in `logs-and-diagnostics.md` to identify the failure ID. Then jump to the playbook in `repair-playbooks.md`.

## Step 6 — Run `rag doctor`

```bash
rag doctor
```

This is the structured health check. **Note:** if the service is up, expect "Collection NOT FOUND" in the output — that's expected lock contention with the running service, not a real failure (F-010).

## Step 7 — Last resort

If nothing above identifies the issue:

1. Check `versioning.md` — is the user on pre-v2.4.1? Recommend upgrade.
2. Check `gaps.md` — is the feature they're asking about actually unimplemented?
3. Read the most recent ~50 lines of `service.log` directly.
4. Recommend a soft reset: `rag rebuild` (preserves config).

## Source files to recheck when updating this doc

When ragtools releases a new version, these are the upstream files that drive the doc and references — re-read them in this order:

1. `src/ragtools/__init__.py` (version)
2. `pyproject.toml` (deps + version)
3. `src/ragtools/config.py` (path resolution, env vars, schema migration)
4. `src/ragtools/integration/mcp_server.py` (proxy/direct mode, retry logic)
5. `src/ragtools/service/run.py` + `app.py` + `startup.py` (startup sequence)
6. `src/ragtools/service/routes.py` (HTTP API surface)
7. `src/ragtools/service/owner.py` (Qdrant lock semantics)
8. `src/ragtools/cli.py` (CLI surface, `rag doctor` output)
9. `installer.iss` and `scripts/launch.vbs` (installer + launcher behavior)
10. `docs/decisions.md` (upstream architectural decisions)
11. Any new `docs/` notes since the last update

## See also

- `post-install-verify.md` — checklist after install/upgrade
- `known-failures.md` — full failure-mode catalog
- `repair-playbooks.md` — step-by-step fixes
- `recovery-and-reset.md` — when triage fails
