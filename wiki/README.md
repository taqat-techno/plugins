# `plugins/wiki/` — source files for the GitHub Wiki

This directory is the **source of truth** for the marketplace's GitHub Wiki, published at [github.com/taqat-techno/plugins/wiki](https://github.com/taqat-techno/plugins/wiki).

We keep the wiki source in the main repo so:
- **PRs can review wiki changes** alongside code changes.
- **Plugin changes + wiki updates land in the same commit** (no docs drift).
- **`git log` captures wiki history** in the main repo, not in a parallel `.wiki.git`.

## Layout

```
wiki/
├── Home.md                      ← landing page
├── Marketplace-Overview.md
├── Plugin-Catalog.md
├── Odoo-Plugin.md
├── DevOps-Plugin.md
├── Rag-Plugin.md
├── Paper-Plugin.md
├── Pandoc-Plugin.md
├── Remotion-Plugin.md
├── Ntfy-Plugin.md
├── Installation-and-Usage.md
├── Plugin-Development-Guide.md
├── Architecture.md
├── Troubleshooting.md
├── Contribution-Guide.md
├── Change-History.md
├── _Sidebar.md                  ← GitHub Wiki sidebar navigation
├── _Footer.md                   ← GitHub Wiki footer
└── README.md                    ← this file
```

### GitHub Wiki naming conventions

- Each `.md` file becomes a wiki page; the filename (minus `.md`) becomes the URL slug.
- `Home.md` is the landing page — do not rename.
- `_Sidebar.md` renders as the left sidebar on every page.
- `_Footer.md` renders as the page footer.
- Use `[[Title|File-Name]]` syntax for inter-page links — GitHub Wiki resolves these to other pages in the same wiki.
- Use relative links (`../../<file>`) from wiki pages back to repo files. The wiki lives at `<repo>.wiki.git` (one directory up from the repo root in the GitHub URL structure), so `../../` from a wiki page reaches the repo root.

## Publishing to GitHub Wiki

### One-time setup

1. On GitHub: **Settings → Features → Wiki** (make sure it's enabled).
2. Visit `https://github.com/taqat-techno/plugins/wiki` and click **Create the first page**. Any placeholder content works — this creates the `.wiki.git` repo GitHub ignores until it has at least one page.

### Sync source → published wiki

```bash
# Clone the wiki repo (once)
cd ~
git clone https://github.com/taqat-techno/plugins.wiki.git wiki-taqat-techno

# Copy source files
cp ~/code/plugins/plugins/wiki/*.md ~/wiki-taqat-techno/
cp ~/code/plugins/plugins/wiki/_Sidebar.md ~/wiki-taqat-techno/
cp ~/code/plugins/plugins/wiki/_Footer.md ~/wiki-taqat-techno/
# DO NOT copy this README.md — the wiki doesn't need it.

# Commit and push to the wiki (remember: taqat-techno/* needs a-lakosha)
cd ~/wiki-taqat-techno
gh auth switch --user a-lakosha
git add -A
git commit -m "docs(wiki): sync from plugins/wiki/"
git push origin master
gh auth switch --user ahmed-lakosha
```

### Alternative: PowerShell / Windows

```powershell
# Clone the wiki repo (once)
cd $HOME
git clone https://github.com/taqat-techno/plugins.wiki.git wiki-taqat-techno

# Copy source files (exclude this README)
Copy-Item -Path "C:\MY-WorkSpace\claude_plugins\plugins\wiki\*.md" -Destination "$HOME\wiki-taqat-techno\" -Exclude "README.md"

# Commit and push
cd $HOME\wiki-taqat-techno
gh auth switch --user a-lakosha
git add -A
git commit -m "docs(wiki): sync from plugins/wiki/"
git push origin master
gh auth switch --user ahmed-lakosha
```

### Automation (optional, future)

A GitHub Action triggered on push to `main` could auto-sync the wiki:

```yaml
# .github/workflows/wiki-sync.yml (proposal, not shipped)
name: Sync wiki
on:
  push:
    branches: [main]
    paths: ['plugins/wiki/**']
jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: Andrew-Chen-Wang/github-wiki-action@v4
        with:
          path: plugins/wiki/
          token: ${{ secrets.WIKI_SYNC_TOKEN }}
```

Not currently enabled — manual sync is the documented path. Automation can land in a later docs pass.

## Editing conventions

- **Do not invent plugin behavior** that isn't supported by the codebase. When something is uncertain, mark it as a TODO or cite the source file that's ambiguous.
- **Preserve existing useful documentation** — the plugin READMEs, CHANGELOGs, and ARCHITECTURE files are the authoritative sources. The wiki is the reader-friendly narrative, not a replacement.
- **Cross-link to source files** with relative paths (`../../<plugin>/README.md`) — they render in the GitHub Wiki as links back to the main repo.
- **Cross-link to other wiki pages** with `[[Title|File-Name]]` syntax.
- **Use the existing plugin pages as templates** for any new plugin documentation.
- **Keep examples short and evidence-based.** Cite specific commands, specific file paths, specific version numbers.

## See also

- `plugins/README.md` — the marketplace README (GitHub front page)
- `plugins/CONTRIBUTING.md` — older, skill-first-era contribution guide
- `plugins/CLAUDE_CODE_PLUGIN_DEVELOPMENT_GUIDE.md` — Anthropic's plugin development spec (vendored)
- `plugins/agent_skills_spec.md` — skills spec (vendored)
