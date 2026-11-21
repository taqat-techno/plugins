---
title: 'Odoo.sh SSH Setup and Doctor'
read_only: false
type: 'command'
description: 'Set up SSH access to Odoo.sh builds on any machine (pick a key, write a profile, test it), manage several projects and branches, and diagnose a failing connection: status, keys, add, edit, doctor, allow, deny, remove'
argument-hint: '[status|keys|add|edit|show|doctor|allow|deny|remove|default] [profile]'
---

# /sh-setup — SSH access to Odoo.sh builds

Odoo.sh has no API token for builds or logs. The only programmatic way in is SSH to a build,
with a key you added to your Odoo.sh profile. This command sets that up on the machine you are
on and tests it. After that, the plugin's `odoo-sh` tools read the build: the deployed commit,
the install and server logs, module versions and health.

## What you need

- An Odoo.sh account with access to the project (as a collaborator).
- An SSH client. Windows 10/11 ships OpenSSH (Settings > System > Optional features >
  OpenSSH Client), and Git for Windows' ssh works too. macOS ships ssh. On Linux and WSL,
  install `openssh-client`.
- Python 3, which the plugin already needs.

## Where the settings live

There is one file per machine and per user account: `~/.odoo-mcp/odoo-sh.json`.

- It is separate from the data MCP's `profiles.json`, and it is refused inside a git
  repository, so it cannot be committed with a project.
- It stores the **path** of your private key, never the key, and never a passphrase.
- It holds any number of profiles: several Odoo.sh projects, and several branches of each.
- Change it only through the CLI. A hook blocks direct edits, so no hand-editing is needed or
  allowed:

```
python "${CLAUDE_PLUGIN_ROOT}/scripts/mcp/odoo_sh.py" <subcommand>
```

Below, `odoo_sh.py` means that full command.

## Bare `/sh-setup`: the guided flow

Run the steps in order. Stop at any step that needs the developer, and wait for their answer.

1. **Status.** Run `odoo_sh.py`. If a profile for this folder exists and resolves, go to
   step 6. If there is none, continue.
2. **Pick a key.** Run `odoo_sh.py keys`. It lists every key in `~/.ssh` (any type, any file
   name) with its fingerprint and whether it has a passphrase. Under WSL it also lists the
   Windows profile's `.ssh` folders. Under each key it prints the fingerprint the way Odoo.sh
   shows it (the colon-separated MD5 form). Ask the developer which key to use for Odoo.sh.
   - **They already added a key in Odoo.sh** (typed in, or "Imported from GitHub"): ask for
     the fingerprint shown in Odoo.sh under avatar > Profile > SSH keys > Active keys, then run
     `odoo_sh.py keys --match <fingerprint>`. It names the local key that is the same one. Use
     that key and skip step 3. Never guess: a profile pointing at a different key is refused
     by Odoo.sh even though the key file is valid. If nothing matches, the listed key is not on
     this machine; continue with a local key and step 3.
   - **Odoo.sh can import keys from GitHub.** A key listed there as "Imported from GitHub"
     is the developer's GitHub key, so the right local key is often the one they push to
     GitHub with, not the default `id_ed25519`.
   - **Where it is in Odoo.sh:** the avatar menu > Profile. Do not give a direct link to it.
   - **Key types:** Odoo.sh accepts only `ssh-ed25519` and `ssh-rsa`. Do not offer another type.
   - **They want a new key:** ask first, then run `odoo_sh.py keys --generate odoo_sh`. That
     makes an ed25519 key with no passphrase. Add `--type rsa` for RSA. With
     `--passphrase-prompt`, ssh-keygen asks for the passphrase in their own terminal.
   - **Their key lives only in an agent** (1Password, KeePassXC, a hardware key): use `--agent`
     in step 4 instead of `--key`.
3. **Add the public half in Odoo.sh.** Run `odoo_sh.py keys --print <private key path>`. It
   prints the single line to paste into Odoo.sh: avatar > Profile > SSH keys. The developer
   pastes it in the browser; wait for their "done". Never print, copy or ask for the private
   key or its passphrase.
4. **Write the profile.** Ask only for what you cannot infer:
   - a short profile name, such as `acme-stage`;
   - the project slug (the start of the build URL, such as `acme-erp`), the branch (such as
     `stage`), and the role (`dev`, `stage` or `prod`);
   - the URL of the branch, copied from Odoo.sh (such as `https://acme-erp-stage.odoo.com`).
     A custom domain works too, if it lists databases.

   ```
   odoo_sh.py add acme-stage --project acme-erp --branch stage --role stage --url https://acme-erp-stage.odoo.com --key ~/.ssh/odoo_sh --path "<this project folder>"
   ```

   - A new profile is **read-only**.
   - `--path` binds the profile to the project folder, so the tools pick it without a
     `profile` argument.
   - An unknown role counts as `prod`.
5. **Test.** Run `odoo_sh.py doctor acme-stage`, or call the `sh_doctor` tool. Read the result
   line and the `fix:` lines to the developer. On `ok`, it shows the commit the build runs.
   On a failure, apply the fix it names and run the doctor again (see the table below).
6. **Use it.**
   - `sh_logs file=install errors_only=true`: why an install or upgrade failed.
   - `sh_logs`: the server log, `odoo.log`.
   - `sh_commit`: proof of the deployed code.
   - `sh_modules names=[...]`: whether a version landed.
   - `sh_health`: disk, workers and load.

   If the tools are missing because the session started before the plugin was updated, the
   CLI has the same reads: `odoo_sh.py run logs --file install --errors-only`,
   `odoo_sh.py run commit`.

## When automatic resolution does not fit

On every call, the build is found from `<url>/web/database/list`. Odoo.sh names a build's
database `<project>-<branch>-<build id>`, and SSH goes to
`<build id>@<project>-<branch>-<build id>.dev.odoo.com`. That is the address Odoo.sh shows in
the branch's SSH menu. If your case differs, override only what differs:

| Situation | Option |
|---|---|
| The URL does not list databases, or the address Odoo.sh shows differs from the derived one (for example on production) | Paste the address: `odoo_sh.py edit <name> --ssh "ssh 1234567@acme-erp-main-1234567.dev.odoo.com"`. This pins the user and host, so update it after a rebuild |
| A different host or user pattern | `--host '{db}.dev.odoo.com'`, `--ssh-user '{build}'` (placeholders: `{project}` `{branch}` `{build}` `{db}`) |
| The network blocks outbound port 22 | `--proxy-jump user@jumphost[:port]` through a host that can reach port 22, or `--port N` if your network forwards one |
| An old server offers only ssh-rsa | `--ssh-option HostKeyAlgorithms=+ssh-rsa --ssh-option PubkeyAcceptedAlgorithms=+ssh-rsa` |
| A specific ssh client | `--ssh-binary <path>` (on Windows, the default is Windows OpenSSH first, then any ssh on PATH, such as Git Bash's) |
| A slow link or long reads | `--connect-timeout S` (3-120), `--command-timeout S` (5-600) |
| A non-standard layout | `--src-dir ~/src/user`, `--logs-dir ~/logs` |
| Undo an override | `--clear host`, `--clear ssh_options`, ... |

The extra `--ssh-option` keys allowed are listed in `mcp_sh/shconfig.py` (`SSH_OPTION_KEYS`).
Options that could run local commands or weaken host-key checking are refused.

## Doctor results

The doctor stops at the first step that fails and names one result:

| Result | Meaning | What to do |
|---|---|---|
| `key_missing` / `key_not_private` | The key path is wrong, or it points at a `.pub` while no agent holds the private half | `odoo_sh.py edit <name> --key <private key>` |
| `key_encrypted_no_agent` | The key has a passphrase and no ssh-agent holds it; ssh runs with `BatchMode=yes` and never prompts | Start the agent and run `ssh-add <key>` in your own terminal (the doctor prints the command for each platform) |
| `no_key` | An agent-mode profile, and the agent holds no key | `ssh-add`, or set `--key` |
| `ssh_missing` | No ssh client found | Install one, or set `--ssh-binary` |
| `url_dns_failure` / `url_unreachable` | The URL does not resolve or does not answer | Fix the URL; check DNS, VPN or proxy |
| `db_list_unavailable` | The URL does not list databases | Use the branch's Odoo.sh URL, or paste `--ssh` |
| `build_not_found` | No `<project>-<branch>-<id>` database on that URL | Check the project slug and branch; a build that is still starting has none yet |
| `stale_build` | The build host is gone, or the build was replaced during the check | Retry; check the branch's current build |
| `dns_failure` | A host override does not resolve | Fix it, or `--clear host` |
| `tcp_timeout` | Port 22 times out. The result says whether 443 on the same host and `github.com:22` connect. If they do, on a staging or production build the usual cause is the project's SSH allow-list: Odoo.sh drops SSH from addresses not listed under project Settings > Firewall. Otherwise the network drops SSH to Odoo.sh | A project admin adds the public IP the doctor prints to the allow-list (takes about 5 minutes). If it is already listed: `--proxy-jump`, `--port`, or another network |
| `tcp_refused` | Port 22 is refused | Check a `--port` override |
| `auth_refused` | The server refused the key. The result lists every local key with the fingerprint Odoo.sh shows | Point the profile at the key Odoo.sh lists (`odoo_sh.py keys --match <fingerprint>`, then `edit <name> --key`), or add the public key in Odoo.sh > avatar > Profile > SSH keys; check access to the project; compare with the address in the SSH menu and paste it with `--ssh`; some users report ed25519 refused where RSA works |
| `key_permissions` | ssh refuses a key file that other accounts can read | Windows: `icacls`; macOS/Linux: `chmod 600`; WSL: copy the key out of `/mnt/c` into `~/.ssh` |
| `host_key_changed` | The recorded host key differs | Check the build, then delete that host's file in `~/.odoo-mcp/odoo-sh-known_hosts/` |
| `algorithm_mismatch` | The client and server share no algorithm | `--ssh-option ...+ssh-rsa`, or update ssh |

## Several projects and branches

Add one profile per project and branch: `acme-stage`, `acme-dev`, `globex-prod`, and so on.

- **Which profile a call uses:**
  1. the `profile` argument;
  2. otherwise, the profile whose `--path` contains the current folder;
  3. otherwise, the default (`odoo_sh.py default <name>`; the first profile added becomes the
     default);
  4. otherwise, the only profile.
- **Managing them:** `odoo_sh.py list`, `show <name>`, `edit <name> ...`, `remove <name>`.

## Actions and their gates

| Action | Tool | Gate |
|---|---|---|
| Deployed commit, uncommitted changes on the build, submodules | `sh_commit` | read (always on) |
| odoo.log, install.log, pip.log, any file in the logs folder, with grep / since / errors_only / pid filters | `sh_logs` | read |
| Module versions and states | `sh_modules` | read |
| Disk, load, memory, workers, limits | `sh_health` | read |
| Module update (`odoo-bin -u <modules> --stop-after-init`), as a background job | `sh_update` + `sh_job` | opt-in `update` |
| Restart (`odoosh-restart http`) | `sh_restart` + `sh_job` | opt-in `restart` |
| A one-off, non-interactive shell command | `sh_shell` | opt-in `shell` |
| An `odoo-bin shell` snippet, always rolled back; `commit()` is refused | `sh_odoo_shell` | opt-in `odoo_shell` |

- **Turning an action on:** each opt-in action is enabled separately, and only after the
  developer says yes in chat:
  `odoo_sh.py allow <name> update shell --approved-by "<their words>"`.
- **Turning them off:** `odoo_sh.py deny <name>` returns the profile to read-only, with no
  approval needed.
- **Production:** on a `prod` profile, every opt-in call also needs the developer's yes for
  that call, passed verbatim as `approved_by_user`. Production stays read-only unless the
  developer opts in, and they confirm each time.
- **The approval prompt:** Claude Code shows the developer a permission prompt, which they
  answer themselves, before `odoo_sh.py allow` adds an action and before every write or shell
  call on a `prod` profile. Tell them it is coming and what it is for. A declined prompt is a
  no: stop there.
- **The rollback has limits.** Rolling back an `odoo-bin shell` snippet undoes database
  changes only. Mail sent, HTTP calls made and files written by the snippet still happen.

### Left out on purpose

- **Database dumps and filestore downloads.** These are large transfers that Odoo.sh already
  offers as backups in its UI. Pulling production data onto a laptop is a decision for the
  developer, not a tool call.
- **Uploading, editing or deleting files on the build.** The build filesystem is replaced on
  every rebuild, so changes belong in the repository.
- **git pull, checkout or any change to `~/src` on the build.** Odoo.sh deploys from git; a
  change made on the build is lost on the next rebuild.
- **Interactive sessions and port forwarding.** These are long-lived and cannot run under
  `BatchMode` in a tool call.
- **A write-capable `psql`.** Record changes go through the `odoo` data MCP, which has its own
  access gate. Schema changes belong in module upgrades.

## Safety notes

- ssh always runs with `BatchMode=yes`, password and keyboard-interactive login off,
  `StrictHostKeyChecking=accept-new` with one known_hosts file per host, a connect timeout and
  a command timeout.
- Output passes redaction before anyone sees it. That covers values from the build's
  `odoo.conf` and environment whose names look like secrets, plus passwords, tokens, bearer
  headers and URL credentials found in the text.
- Changes to profiles and every opt-in call are recorded in `~/.odoo-mcp/odoo-sh-audit.log`.
  It records the action and the approval, not the output.
