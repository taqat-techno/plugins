# Installation and Usage

## Prerequisites

- **Claude Code** (CLI / desktop / web / IDE extension) — current version.
- **Git** for manual-clone installation.
- **Network access** to clone the marketplace (one-time). After install, the plugins themselves are local unless they make explicit network calls (ntfy, devops, and the rag upgrade-check are the only network paths; all others are offline).

## Method 1 — Claude Code UI (recommended)

1. Open Claude Code.
2. Run `/plugins`.
3. Click **Add Marketplace**.
4. Enter the repository URL:
   ```
   https://github.com/taqat-techno/plugins.git
   ```
5. Click **Install**.

All 7 plugins become available automatically. Claude Code clones the marketplace to `~/.claude/plugins/cache/taqat-techno-plugins/` (or the platform equivalent) and registers every plugin's components with the current session.

## Method 2 — Manual clone

If you prefer to manage the marketplace directory yourself:

**Linux / macOS:**
```bash
cd ~/.claude/plugins/marketplaces
git clone https://github.com/taqat-techno/plugins.git taqat-techno-plugins
```

**Windows:**
```cmd
cd %USERPROFILE%\.claude\plugins\marketplaces
git clone https://github.com/taqat-techno/plugins.git taqat-techno-plugins
```

Then restart Claude Code so it picks up the new marketplace.

## Verify the installation

In Claude Code, run `/plugins`. You should see:

```
taqat-techno-plugins
  - odoo                   ✓ enabled
  - devops                 ✓ enabled
  - rag                    ✓ enabled
  - paper                  ✓ enabled
  - pandoc                 ✓ enabled
  - remotion               ✓ enabled
  - ntfy-notifications     ✓ enabled
```

Run `/mcp` to verify any MCP servers that your installed plugins registered (Azure DevOps, ragtools). They should show `connected`.

## First-time plugin setup

Most plugins have a one-time setup step:

| Plugin | First command | What it does |
|---|---|---|
| odoo | no setup required — works on any Odoo source tree | — |
| devops | `/init` then `/init profile` | Install Azure CLI + MCP; configure auth; generate persistent user profile |
| rag | `/rag-setup` | Detect install state; walk install/upgrade/verify; auto-install CLAUDE.md rule; dedupe MCP registrations |
| paper | `/paper` (status check) | Verify Figma MCP installation status if using figma-workflow |
| pandoc | `/pandoc setup` | Install Pandoc + LaTeX if missing |
| remotion | `/remotion <project-name>` | Scaffold a Remotion project with continuous-audio skeleton |
| ntfy | `/ntfy setup` | Pick a topic, configure server, test delivery |

## Daily usage pattern

Most plugins are **auto-activating on user intent** via their skills. You rarely need to type a slash command for routine work:

- Say "upgrade my Odoo module" → `odoo-plugin` skills take over.
- Say "why isn't this file in my search results?" → `rag-plugin`'s `ragtools-ops` skill runs the why-not-indexed workflow.
- Say "design a login page for iOS" → `paper-plugin`'s `design` skill produces a wireframe + HTML.

Slash commands are there for **deliberate dispatch** when you want a specific operation — `/rag-doctor --full`, `/sprint --full`, `/pandoc convert`, etc.

## Updates

### Auto-update (recommended)

1. Open Claude Code settings.
2. Navigate to the **Plugins** section.
3. Find **taqat-techno-plugins**.
4. Toggle **Auto-Update** to ON.

New plugin releases arrive automatically on session restart.

### Manual update

```bash
cd ~/.claude/plugins/marketplaces/taqat-techno-plugins
git pull
```

Then restart Claude Code.

## Uninstalling

1. In Claude Code, run `/plugins`.
2. Find **taqat-techno-plugins**.
3. Click **Remove**.

Or manually delete the marketplace directory:

```bash
# macOS / Linux
rm -rf ~/.claude/plugins/marketplaces/taqat-techno-plugins

# Windows
rmdir /s /q %USERPROFILE%\.claude\plugins\marketplaces\taqat-techno-plugins
```

Per-plugin state (like `~/.claude/ntfy-plugin/config.json`, `~/.claude/rag-plugin/usage.log`, or `~/.claude/devops-plugin/timesheet/`) persists unless you delete those directories explicitly.

## Common issues after install

See [[Troubleshooting]] for the full catalog. The most common:

1. **Plugins don't appear** — Claude Code hasn't restarted since install. Restart and re-run `/plugins`.
2. **MCP server shows disconnected** — the plugin-level `.mcp.json` is wired correctly, but the target binary isn't on PATH. For `rag`, the RAGTools installer adds `rag` to PATH by default; verify with `where rag` / `which rag`. For `devops`, Node.js + npx must be installed for the Azure DevOps MCP.
3. **Cache is stale after a plugin version bump** — the source under `plugins/` was updated but the cache under `~/.claude/plugins/cache/` is the old version. `git pull` inside the marketplace dir + restart Claude Code.

## See also

- [[Plugin Catalog|Plugin-Catalog]] — every plugin at a glance
- [[Troubleshooting]] — common issues + resolutions
- Individual plugin pages in the sidebar
