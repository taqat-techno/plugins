---
title: Post-Install Verification
topic: verify
relates-to: [install, quick-checklist, logs-and-diagnostics]
source-sections: [§7]
---

# Post-Install Verification

Run this sequence after any install or upgrade.

## Verification commands

```bash
# 1. Version check
rag version
# Expected: "ragtools v<X.Y.Z>"

# 2. Health check
rag doctor
# Expected: all components OK except possibly "Collection NOT FOUND"
# if the service is running and holds the Qdrant lock — this is expected.

# 3. Service should be running (installer starts it automatically)
curl http://127.0.0.1:21420/health
# Expected: {"status":"ready","collection":"markdown_kb"}

# 4. Admin panel smoke test
# Open http://127.0.0.1:21420 in a browser.
# Expected: Dashboard with "Add Your First Project" if no projects configured.
```

## Validation checklist

- [ ] `rag version` returns the expected version
- [ ] `rag doctor` reports all dependencies present
- [ ] `curl http://127.0.0.1:21420/health` returns status `ready`
- [ ] Admin panel opens in browser
- [ ] Service process is visible in Task Manager (Windows) or Activity Monitor (macOS)
- [ ] Data directory exists at the correct platform-specific path (see `paths-and-layout.md`)
- [ ] Service log shows no `ERROR` lines since startup
- [ ] After adding a project, indexing starts automatically

## Important: "Collection NOT FOUND" is expected when the service is up

`rag doctor` opens its own Qdrant client to inspect the collection. When the service is running and holds the Qdrant exclusive file lock, this second client cannot read the collection and reports `Collection NOT FOUND`. **This is not a bug.** Confirm the service is up via `curl /health` instead. See `known-failures.md#collection-not-found-while-service-up`.

## See also

- `quick-checklist.md` — one-page support triage
- `logs-and-diagnostics.md` — where to look when verification fails
- `repair-playbooks.md` — what to do when a check fails
