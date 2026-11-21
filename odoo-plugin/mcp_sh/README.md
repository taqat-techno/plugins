# odoo-sh MCP server

The third MCP server of the odoo plugin, beside `mcp/` (record data, `profiles.json`) and
`mcp_local/` (local services, `local-services.json`). It reaches **Odoo.sh builds over SSH**,
which is the only programmatic access Odoo.sh offers to build logs and the deployed code.
Standard library only.

| File | Owns |
|---|---|
| `shconfig.py` | `~/.odoo-mcp/odoo-sh.json`: validation, atomic writes, backups (`sh-backups/`), the audit log, profile selection, the allow-list opt-in |
| `shcore.py` | Build resolution, the ssh runner, the doctor's classification, the remote scripts, redaction |
| `sh_tools.py` | MCP tool schemas and handlers, the write gate |
| `server.py` | stdio JSON-RPC transport |
| `../scripts/mcp/odoo_sh.py` | CLI: keys, add, allow/deny, doctor, and read-only `run` as a fallback |

Setup: `/odoo:sh-setup`.

## Why MCP tools, not a guarded script

- **No shell text from the model**, outside the opt-in `shell` action. Each action is a fixed
  script built from validated arguments (module names, a regex passed as one quoted argument,
  a timestamp) and sent to `bash -s` on stdin. The `shell` command and the `odoo_shell` snippet
  travel base64-encoded, so no quoting is involved.
- **Redaction cannot be skipped.** Every byte goes through `redact_text` before it reaches
  the model: values of secret-looking keys in the build's `odoo.conf` and environment
  (collected by the remote prelude, used only locally), then pattern masks for passwords,
  tokens, bearer headers, URL credentials and private key blocks. It reuses the data MCP's
  `guards.redact` for the exact-value pass.
- **The gate is code.** `update`, `restart`, `shell` and `odoo_shell` each need the
  profile's opt-in (written only by the CLI with `--approved-by`), and a `prod`-role profile
  needs `approved_by_user` on every call. A prompt can forget a rule; the handler cannot.
- **The yes comes from the user, not the model.** `approved_by_user` and `--approved-by` are
  text the model passes, so they are an audit record, not proof. `hooks/pre_odoo_sh_guard.py`
  (PreToolUse) returns `ask`, so Claude Code shows the user a permission prompt they answer
  themselves, for: every `sh_update` / `sh_restart` / `sh_shell` / `sh_odoo_shell` call on a
  prod-role profile; every `odoo_sh.py allow` that adds an action; changing a prod profile to
  dev or stage; and a shell command that writes `odoo-sh.json` directly. Only the user can
  switch it off (`ODOO_SH_APPROVAL_PROMPT=off` in the environment before starting Claude Code).

The CLI shares the core because setup has to work before the server is loaded (a plugin
update needs a restart) and because config changes follow the plugin's rule that
connection files change only through a CLI that a hook protects.

## Resolution, every call

```
POST <url>/web/database/list -> "<project>-<branch>-<buildid>" (highest build id)
ssh -l <buildid> <project>-<branch>-<buildid>.dev.odoo.com bash -s
```

`host` and `ssh_user` take `{project} {branch} {build} {db}` templates. Fixed values for both
(pinned) skip resolution. That is for a URL that does not list databases, or for an address
that differs from the derived one: `odoo_sh.py edit <name> --ssh "<the ssh command Odoo.sh
shows>"` parses and pins it. Pins go stale on every rebuild.

## Profiles

Any number of profiles per machine. Selection order: the `profile` argument, then the profile
whose `paths` contain the project folder (`ODOO_SH_PROJECT_DIR`), then the `default`, then the
only profile. Every default can be overridden per profile:

| Field | Default |
|---|---|
| `key` | none: ssh-agent and the user's default keys. With a key: `-i <key>` plus `IdentitiesOnly`. A `.pub` path works when the agent holds the private half |
| `ssh_binary` | Windows: Windows OpenSSH, then ssh on PATH (Git Bash, MSYS2). Others: ssh on PATH |
| `ssh_user` / `host` | `{build}` / `{db}.dev.odoo.com` |
| `port` / `proxy_jump` | 22 / none |
| `ssh_options` | none. Allow-listed `Key=Value` only (`SSH_OPTION_KEYS`) |
| `connect_timeout` / `command_timeout` | 10 s / 60 s |
| `src_dir` / `logs_dir` | `~/src/user` / `~/logs` |
| `allow` | `read`. Opt-in: `update`, `restart`, `shell`, `odoo_shell` |

## ssh options

`BatchMode=yes`, password and keyboard-interactive login off,
`StrictHostKeyChecking=accept-new` with one known_hosts file per host under
`~/.odoo-mcp/odoo-sh-known_hosts/`, a connect timeout, keepalives, and a command timeout
(300 s max per call). The safety options come before a profile's `ssh_options`, and ssh keeps
the first value it sees for each option, so a profile cannot weaken them. A passphrase is
never asked for: keys with one must be in an agent (`ssh-add` in the developer's own
terminal).

## Platforms

- **Windows:** keys are read from `~/.ssh`. Windows OpenSSH comes first so the Windows
  ssh-agent service is used; Git Bash's ssh is the fallback, or is chosen with `ssh_binary`.
- **macOS, Linux:** ssh from PATH, `~/.ssh`, the agent at `SSH_AUTH_SOCK`.
- **WSL:** Linux ssh. `keys` also lists the Windows profiles' `.ssh` folders, but a key under
  `/mnt/c` must be copied to `~/.ssh` and `chmod 600`'d before ssh accepts it (the doctor's
  `key_permissions` result says so).

## Tests

`tests/mcp_sh/test_odoo_sh.py`, offline: the network seams (`http_post`, `resolve_host`,
`tcp_probe`, `run_process`) are faked.
