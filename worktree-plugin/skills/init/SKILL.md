---
name: init
description: One-time setup for the worktree plugin - installs the status line into user settings, optionally sets worktree defaults and a prefer-worktrees instruction. Use --remove to undo.
disable-model-invocation: true
allowed-tools: Bash(bash "${CLAUDE_PLUGIN_ROOT}/scripts/wt-install-statusline.sh"*), Bash(bash ${CLAUDE_PLUGIN_ROOT}/scripts/wt-install-statusline.sh *)
---

# Set up the worktree plugin

Everything here is **user-level and optional**. The plugin's commands work
without any of it; this only adds the always-visible status line and the
defaults. Show every change as a diff and confirm each one separately. Never
write more than the user agreed to.

Flags: `--statusline` only the status line · `--project` also offer the
project-level files · `--remove` undo everything.

## 1. Detect

```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/wt-install-statusline.sh" detect
```

Report `PLATFORM`, `GIT_BASH`, and `FLAVOUR`. On Windows, `FLAVOUR=bash` means
Git Bash was found and will be used — that is the fast path (~80ms per render
versus ~600ms for PowerShell).

## 2. Install the status line

A plugin **cannot** ship a `statusLine`: a plugin's own `settings.json`
supports only the `agent` and `subagentStatusLine` keys. So the script is
copied to a stable path in the user's home and referenced from their settings.
The copy is deliberate — the plugin itself lives in a *versioned* cache
directory, and pointing settings there would break on every plugin update.

```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/wt-install-statusline.sh" install
```

Read the `COMMAND=` line from the output — that is the exact value to use.

Then edit `~/.claude/settings.json` yourself with Read and Edit so the user
sees the diff:

- If the file does not exist, create it with just this key.
- If a `statusLine` already exists, **stop and show it.** Ask whether to
  replace it. Never overwrite silently.
- Back it up first: copy to `settings.json.bak-worktree-plugin`.

```json
{
  "statusLine": {
    "type": "command",
    "command": "<the COMMAND= value, verbatim>",
    "padding": 1
  }
}
```

On Windows the path must use forward slashes. The installer already emits it
that way — do not "fix" it to backslashes. Claude Code runs status-line
commands through Git Bash, which consumes unquoted backslashes and the command
then fails with no visible error.

Mention the optional environment overrides once: `WT_GLYPH_TREE`,
`WT_GLYPH_MAIN`, `WT_SEP`, and `WT_SHOW_DIRTY=1` for a dirty-file count
(off by default because it costs a `git status` on every render).

## 3. Worktree defaults (offer, do not assume)

In the same `~/.claude/settings.json`:

```json
{
  "worktree": {
    "baseRef": "fresh"
  }
}
```

- `baseRef`: `"fresh"` (default) branches new worktrees from
  `origin/<default-branch>`; `"head"` branches from the current local HEAD,
  carrying unpushed work. It cannot be set to a branch name.
- `symlinkDirectories`: e.g. `["node_modules", ".venv"]` — avoids re-installing
  dependencies per worktree. Worth offering on large JS/Python repos.
- `sparsePaths`: only for large monorepos.

Only write keys the user picked; leave the rest absent.

## 4. Prefer worktrees globally (optional)

`EnterWorktree` is documented to act on instructions in CLAUDE.md, so this
needs no hook and no setting. If the user wants worktrees preferred for
parallel work, append to `~/.claude/CLAUDE.md`:

```markdown
## Parallel development

When starting work that is independent of what I am currently doing, create an
isolated worktree for it rather than editing the main checkout. Use
/worktree:new. Continuing existing work in the current checkout is fine.
```

Show it as a diff. Skip this by default — without it the plugin stays
"available but only when asked", which is the right setting for most people.

## 5. Project-level files (only with `--project`)

Offer these in the current repository:

- **`.gitignore`** — add `.claude/worktrees/`. Without it every worktree's
  files appear as untracked in the main checkout. Recommend this one.
- **`.worktreeinclude`** — `.gitignore` syntax; lists gitignored files to copy
  into each new worktree, typically `.env`. **State plainly that this copies
  secrets into every worktree** before writing it, and check `.gitignore`
  covers the worktrees directory first.

## 6. Verify

Ask the user to confirm the status line appears. It updates on the next event;
if nothing shows, check that the workspace is trusted — Claude Code skips
status-line execution in an untrusted directory — and that
`disableAllHooks` is not set, which disables the status line too.

## `--remove`

1. `bash "${CLAUDE_PLUGIN_ROOT}/scripts/wt-install-statusline.sh" remove`
2. Delete the `statusLine` key from `~/.claude/settings.json` (diff first).
3. Ask before touching the `worktree` settings or the CLAUDE.md stanza — the
   user may want to keep those.

Removing the plugin leaves no other trace: worktrees are plain git objects and
keep working through `--worktree`, `EnterWorktree`, and `git worktree`.
