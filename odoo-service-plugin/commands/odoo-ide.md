---
title: 'IDE Configuration Generator'
read_only: false
type: 'command'
description: 'Generate PyCharm and VSCode configurations for Odoo development'
argument-hint: '[vscode|pycharm|all] [--config CONFIG]'
---

# /odoo-ide — IDE Configuration Generator

```
/odoo-ide [vscode|pycharm|all] [--config CONFIG] [--project NAME] [--venv PATH]
```

Auto-detects Odoo version, config path, venv path, and addons paths from the environment.

## VSCode (`/odoo-ide vscode`)

Generates 4 files under `.vscode/`:

- **launch.json**: 3 debug configs (Launch, Attach, Test Module)
- **tasks.json**: 4 tasks (Start, Update, Test, Scaffold)
- **settings.json**: Python interpreter, Pylance extra paths, Ruff formatter, file associations
- **extensions.json**: Recommended extensions (Python, Pylance, Ruff, XML, GitLens, Odoo snippets)

## PyCharm (`/odoo-ide pycharm`)

Generates under `.run/` and `.idea/`:

- **odoo-server.run.xml**: Server run configuration
- **odoo-test.run.xml**: Test run configuration
- **PROJECT.iml**: Source roots (odoo/, addons/, projects/)

## All (`/odoo-ide all`)

Generates everything above plus `.editorconfig` for universal formatting.

## Script

Use `ide_configurator.py --ide <vscode|pycharm|both> --env <local|docker>` from the plugin scripts directory.
