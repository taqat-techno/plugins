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

## Operations

| Operation | Usage |
|-----------|-------|
| `backup` | `/db backup --db NAME [--format sql\|dump] [--output DIR]` |
| `restore` | `/db restore --file PATH --db NAME [--no-create]` |
| `create` | `/db create --db NAME` |
| `drop` | `/db drop --db NAME [--yes]` |
| `list` | `/db list` |
| `reset-admin` | `/db reset-admin --db NAME --password PASS` |
| `modules` | `/db modules --db NAME` |

## Connection Defaults

```
--host localhost   --port 5432   --user odoo   --password odoo
```

Override any with flags. Values also read from `odoo-service.local.md` if present.

## Backup

Default: custom format (pg_dump -Fc, compressed). Output: `backups/NAME_YYYYMMDD_HHMMSS.dump`

## Restore

Auto-detects format from extension. Use `--no-create` if database already exists.

## Reset Admin

Runs: `UPDATE res_users SET password='PASS' WHERE login='admin';`
Odoo re-hashes the password on next login.

## Docker Database

For Docker containers, add `--docker CONTAINER`:
```bash
docker exec CONTAINER pg_dump -U odoo -Fc DBNAME > backup.dump
```

## Script

Use `db_manager.py <operation> [options]` from the plugin scripts directory.
