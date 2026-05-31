# Docker Volume & Postgres Safety (Odoo Stacks)

Destroying a Docker volume on an Odoo stack is irreversible: the named volumes hold the **Postgres database** and the **Odoo filestore** (attachments, generated assets, report PDFs). This reference covers the four ways an Odoo Docker stack loses data or fails to boot — and how to avoid each. Read it before any `docker compose down`, mount-point edit, or stack regeneration.

## Never run destructive volume commands blindly

`docker compose down -v` and `docker volume rm` delete the named volumes attached to the stack. On a typical Odoo `docker-compose.yml` that means the Postgres data directory and the Odoo filestore are gone — there is no undo, and a stack with no recent dump is unrecoverable.

The flag matters: `docker compose down` (no `-v`) stops and removes containers but **keeps** named volumes; `docker compose down -v` additionally removes them. Treat the `-v` form as a delete command, not a stop command.

Before running anything that can remove a volume:

1. Enumerate the volumes the stack actually uses. Do not guess from the compose file alone — a renamed service or a previously orphaned volume may still hold the live data.

   ```bash
   docker volume ls
   docker compose config --volumes        # volumes the current compose file declares
   docker inspect <container> --format '{{json .Mounts}}'   # what the running container mounts
   ```

2. Inspect each candidate before deleting. Confirm size, mountpoint, and which container (if any) is attached.

   ```bash
   docker volume inspect <volume-name>
   ```

3. Take a fresh backup of the database and filestore first (logical dump for the DB, archive for the filestore). A volume you are about to delete should already be captured somewhere else.

4. Only then remove the specific volume by name — never the blanket `-v` on a stack you are not certain is empty.

   ```bash
   docker volume rm <specific-volume-name>
   ```

When a mount point changes (see the next section), the correct move is to **migrate data forward with a copy step**, not to delete the old volume and let the new one initialize empty.

## Orphan-volume drift when a mount point changes

Editing a volume mount in `docker-compose.yml` — renaming the named volume, or changing the container path the filestore/DB mounts at — does **not** move the existing data. Docker creates a fresh empty volume for the new mount and leaves the old volume orphaned. The old volume still holds every byte of data; it is simply no longer attached to anything.

The failure signature is recognizable: the stack comes up "clean," the database may even initialize fresh, and the **first request that needs the filestore 500s** because the attachments/assets the database rows point to are not present in the new (empty) volume. Logs show missing-file or "could not find attachment" errors even though the data was never actually lost.

Do not delete the orphan to "clean up." Copy forward instead:

1. Identify the orphaned (old) volume and the new (empty) one with `docker volume ls` and `docker volume inspect`.

2. Copy the contents from old to new using a throwaway helper container that mounts both. Preserve ownership and permissions — Odoo's filestore and Postgres's data directory are owned by specific UIDs, and a copy that resets ownership to root will not be readable by the service.

   ```bash
   # Copy preserving ownership/permissions; -a keeps UID/GID and modes.
   docker run --rm \
     -v <old-volume>:/from \
     -v <new-volume>:/to \
     alpine sh -c "cp -a /from/. /to/"
   ```

3. After Odoo (or Postgres) is confirmed healthy on the new volume, the orphan can be archived and then removed — by explicit name, never by a blanket prune that might catch volumes you still need.

For the Odoo filestore specifically, the data must end up owned by the UID the Odoo container runs as; for the Postgres data directory it must end up owned by the `postgres` user inside the image. `cp -a` from a container that runs as root preserves the numeric UID/GID from the source, which is what you want.

## Preserve the running Postgres major version

Postgres data directories are **forward-incompatible across major versions**. A data directory written by Postgres 15 cannot be opened by Postgres 14 — and a fresh Postgres 16 image pointed at a 15 data directory refuses to start with a "database files are incompatible with server" / version-mismatch error. The stack bricks on boot.

This bites hardest when **regenerating a compose stack from a template**. Templates often pin a default image tag (e.g. a generic `postgres:latest` or whatever the template author chose), which may not match the major version that actually wrote the existing volume. Regenerating blindly can silently downgrade — or upgrade — the pinned major and break the boot.

Before regenerating or editing the Postgres image tag, read the actual major version recorded **inside the named DB volume** and preserve it:

```bash
# The PG_VERSION marker at the root of the data dir holds the major version.
docker run --rm -v <db-volume>:/var/lib/postgresql/data alpine \
  cat /var/lib/postgresql/data/PG_VERSION
```

(If the data directory is nested under a subpath in your image, adjust the mount target accordingly — check `docker volume inspect` and the image's documented `PGDATA`.)

Pin the regenerated compose file to that same major version. Rules of thumb:

- **Never silently change the major** when regenerating from a template — match the tag to the `PG_VERSION` you just read.
- **Never downgrade a major** against an existing data directory. It is forward-incompatible and will refuse to start.
- To intentionally **upgrade** a major, do a real migration: `pg_dumpall` from the old major, start the new major on a fresh volume, restore the dump. Do not point the new image at the old data directory and hope.

> Example (illustrative — not required): if `PG_VERSION` reads `15`, the regenerated compose file should pin `postgres:15` (or a `15.x` patch tag), not `postgres:16` or `postgres:latest`.

## Git-Bash / Windows path translation note

When you run `docker exec` or `docker run` from **Git Bash on Windows**, MSYS path translation rewrites Unix-looking arguments into Windows paths. A container path such as `/var/lib/postgresql/data` can get mangled into something like `C:/Program Files/Git/var/lib/...` before Docker ever sees it, so the command targets the wrong path or fails outright.

The usual workaround is to disable MSYS path conversion for that invocation:

```bash
MSYS_NO_PATHCONV=1 docker exec <container> ls /var/lib/postgresql/data
```

Caveat: disabling conversion globally can break **other** arguments that legitimately need a translated path (for example a `-v C:\host\path:/container/path` flag where the host side is a real Windows path). Toggling it per-command is fiddly.

The more robust habit is to **`cd` into the compose directory and run plain `docker compose` commands** so paths stay relative and inside the container's own filesystem, where MSYS has nothing to translate:

```bash
cd /path/to/compose-dir
docker compose exec db ls /var/lib/postgresql/data
```

For broader Windows, Git Bash, and WSL environment problems (PATH issues, line-ending mangling, Docker Desktop integration, shell quoting), do not duplicate diagnostics here — reach for the **claude-env-doctor** plugin, which owns generic environment troubleshooting. This section is scoped only to the Odoo-on-Docker volume/exec path-translation gotcha.

## Quick checklist before touching volumes

- Did I run `docker volume ls` + `docker volume inspect` and confirm which volume holds live data?
- Do I have a fresh DB dump and filestore archive somewhere outside the volume I'm about to change?
- If a mount point changed, did I copy forward with `cp -a` (preserving ownership) instead of deleting the orphan?
- Did I read `PG_VERSION` from the DB volume and pin the regenerated stack to that exact major?
- Am I avoiding a blanket `down -v` / `volume prune` in favor of removing volumes by explicit name?
