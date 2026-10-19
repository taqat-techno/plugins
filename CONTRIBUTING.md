# Contributing

Thanks for helping. This repository is a Claude Code **plugin marketplace**: each
`<name>-plugin/` directory is one plugin, registered in `.claude-plugin/marketplace.json`.
This guide covers how to change a plugin, add one, and get the change merged.

The rules every plugin must follow are in [`shared/PLUGIN_STANDARDS.md`](shared/PLUGIN_STANDARDS.md).
Read it before your first change. CI enforces most of it.

## Set up

```bash
git clone https://github.com/taqat-techno/plugins.git
cd plugins
python -m pip install pyyaml pytest
npm install --global @anthropic-ai/claude-code   # provides `claude plugin validate`
```

To try your working copy in Claude Code, add it as a local marketplace:

```bash
claude plugin marketplace add ./
```

Then run `/plugin install <name>@taqat-techno-plugins`. Claude Code runs plugins from its
cache (`~/.claude/plugins/cache/...`), not from your checkout, and reads hooks once at
session start. After an edit, run `/reload-plugins` or start a new session.

## Change a plugin

1. **Find the owning file.** Larger plugins use single-owner layering:
   commands → skills → agents → rules → data. Each concern lives in one file and the others
   reference it, so change the owner rather than restating it.
2. **Make the change and test it.** Every script and hook has offline tests in the plugin's
   `tests/`. Add or update them:
   ```bash
   cd <name>-plugin && python -m pytest -q -p no:cacheprovider
   ```
3. **Bump the version** in `.claude-plugin/plugin.json` and add an entry to the plugin's
   `CHANGELOG.md` (`## [x.y.z] - YYYY-MM-DD`). Without a bump, users who installed the
   plugin never receive the change. A change to default behaviour bumps the major version
   (the minor version while at 0.x).
4. **Run the checks CI runs:**
   ```bash
   claude plugin validate . --strict
   python validate_marketplace.py
   python validate_plugin.py <name>-plugin
   python validate_evals.py
   python tools/sync_vendor.py --check
   python tools/check_privacy.py
   python tools/readme_versions.py --check
   python tools/hook_smoke.py <name>-plugin
   ```
   `tools/readme_versions.py` without `--check` updates the root README's version table for you.

## Add a plugin

1. Create `<name>-plugin/` with `.claude-plugin/plugin.json` (`name`, `version`,
   `description`, `author`, `license`, `homepage`, `repository`, `keywords`), a `LICENSE`
   file, `README.md` (the template in PLUGIN_STANDARDS §5), `CHANGELOG.md` and `tests/`.
   The name must not start with `claude-`, `anthropic-` or `cc-plugin-`; those are reserved.
2. Add the plugin's entry to `.claude-plugin/marketplace.json` and a row to the root
   README table. An unregistered plugin is invisible, and no per-plugin check notices.
3. Skills go in `skills/<skill-name>/SKILL.md`. The description is the trigger, so start it
   with "Use when …" and keep it to 1,024 characters. Put custom frontmatter under
   `metadata:`.
4. Hooks use the portable launcher and the vendored `hooklib`: create `hooks/_vendor/` and
   run `python tools/sync_vendor.py`.
5. Add one must-fire and one must-not-fire eval case per skill under `evals/`.

For canonical examples, see Anthropic's `plugin-dev` plugin
(<https://github.com/anthropics/claude-plugins-official/tree/main/plugins/plugin-dev>).

## Shared code

`shared/hooklib.py` is the canonical hook runtime. Never edit a plugin's
`hooks/_vendor/hooklib.py` directly: change `shared/hooklib.py`, run
`python tools/sync_vendor.py`, and bump every plugin whose copy changed.

## Privacy

Never commit real names, e-mail addresses, client or project names, home-directory paths,
tokens or internal reports. Use placeholders such as `acme`, `jane.doe@example.com` and
`C:\Users\<user>`. To catch your own identifying strings before CI does, list them one per
line in `.privacy-denylist` at the repository root. That file is git-ignored, and
`tools/check_privacy.py` reads it.

## Pull requests

- One purpose per PR. Explain what changed and why, and how you tested it.
- CI must be green: validators, privacy, version bumps and secret scan on Linux, plus tests
  and hook smoke on Linux, macOS and Windows.
- A code owner reviews every PR (`.github/CODEOWNERS`).

## Reporting issues

Open an issue at <https://github.com/taqat-techno/plugins/issues>. Include the plugin name
and version, your OS and Claude Code version (`claude --version`), what you expected, and
what happened. Remove tokens, internal hostnames and private project names from logs
before you paste them.

## License

By contributing, you agree that your contributions are licensed under the MIT License
(see `LICENSE`).
