---
title: 'Odoo Database Operations'
read_only: false
type: 'command'
description: 'Backup, restore, create, drop, list databases and reset admin passwords'
argument-hint: '<backup|restore|create|drop|list|reset-admin|modules> [options]'
---

# /db — Database Operations

```
/db <operation> [options]
```

With no operation, run `list`.

## Script

Every operation runs the plugin script:

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/service/db_manager.py" <operation> [options]
```

## Operations

| Operation | Usage |
|-----------|-------|
| `backup` | `/db backup --db NAME [--format sql\|dump] [--output DIR]` |
| `restore` | `/db restore --file PATH --db NAME [--no-create]` |
| `create` | `/db create --db NAME` |
| `drop` | `/db drop --db NAME` (see "Destructive operations") |
| `list` | `/db list` |
| `reset-admin` | `/db reset-admin --db NAME` (see "Reset Admin") |
| `modules` | `/db modules --db NAME` |

## Destructive operations: the user confirms, not you

`drop`, `restore --no-create` (restoring over an existing database) and `reset-admin`
cannot be undone. Before running any of them:

1. Tell the user exactly what will happen: the operation, the database name and the host.
2. Ask them to confirm **that database name**. Earlier messages do not count.
3. Only after an explicit yes, run the script. For `drop`, add `--yes` (without it the
   script refuses, because Claude's shell has no terminal to confirm in).

The plugin's Bash guard also asks the user before these commands run. `drop` refuses a
non-local `--host` unless `--allow-remote` is given; pass that only when the user named
the remote server.

## Connection Defaults

```
--host localhost   --port 5432   --user odoo   --password $PGPASSWORD (else odoo)
```

Prefer setting `PGPASSWORD` in the environment over `--password`: a flag is visible in
the process list. Values may also come from `odoo-service.local.md` if present.

## Backup

Default: custom format (pg_dump -Fc, compressed). Output: `backups/NAME_YYYYMMDD_HHMMSS.dump`

## Restore

Auto-detects format from extension. Use `--no-create` if database already exists
(destructive: confirm first, see above).

## Reset Admin

Sets the `admin` login's password with an `UPDATE res_users` sent to `psql` on stdin.
Odoo re-hashes the password on next login. The script never prints the password.

Never ask the user to paste the new password into chat. Ask them to run it themselves,
or to export it first:

```bash
# the user types the password; it never appears in argv or the transcript
python "${CLAUDE_PLUGIN_ROOT}/scripts/service/db_manager.py" reset-admin --db NAME --password-stdin
# or, if the user already exported ODOO_ADMIN_NEW_PASSWORD in their own shell:
python "${CLAUDE_PLUGIN_ROOT}/scripts/service/db_manager.py" reset-admin --db NAME
```

`--password PASS` still works but is deprecated (process-list exposure).

## Docker Database

For Docker containers, add `--docker CONTAINER`:
```bash
docker exec CONTAINER pg_dump -U odoo -Fc DBNAME > backup.dump
```
