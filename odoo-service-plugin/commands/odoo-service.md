---
title: 'Odoo Service Manager'
read_only: false
type: 'command'
description: 'Odoo server lifecycle — start, stop, init, database, Docker, and IDE configuration'
argument-hint: '[start|stop|init|db|docker|ide] [args...]'
---

# /odoo-service — Unified Odoo Service Manager

One command for the entire Odoo server lifecycle: start, stop, initialize, database ops, Docker management, and IDE configuration. Supports Odoo 14-19, local venv, Docker, and bare Python environments.

---

## Routing

Parse the first argument after `/odoo-service` and dispatch:

| Input | Sub-command |
|-------|------------|
| *(none)* | **Help + Status** |
| `start` | **Start Server** |
| `stop` | **Stop Server** |
| `init` | **Initialize Environment** |
| `db` | **Database Operations** |
| `docker` | **Docker Management** |
| `ide` | **IDE Configuration** |

Natural language also routes: "start odoo" -> `start`, "backup database" -> `db backup`, "generate vscode config" -> `ide vscode`, etc.

---

## Environment Detection (All Sub-commands)

Before any operation, detect the environment:

```
1. docker-compose.yml found? --> Docker mode
2. Dockerfile found?         --> Docker build mode
3. .venv/ or venv/ found?   --> Local venv mode
4. None of above?            --> Bare Python mode
```

Override with flags: `--docker`, `--venv`, `--env local`.

Also detect:
- **Odoo version**: from `odoo/release.py` or directory name pattern `odoo{14-19}`
- **Config file**: scan `conf/` for `.conf` files
- **Venv path**: `.venv/` or `venv/`
- **Addons paths**: parse `addons_path` from the active config file
- **Running server**: check port 8069 listener

---

## 0. No Arguments — Help + Status

When invoked with no arguments (`/odoo-service`):

1. **Detect running server**: check if port 8069 (or 8072) is listening
2. **Detect environment**: venv, Docker, or bare Python
3. **Show status summary**:

```
Odoo Service Manager
====================
Environment: Local venv (.venv/)
Odoo Version: 17.0
Server: RUNNING on port 8069 (PID 12345)
Config: conf/TAQAT17.conf
Database: TAQAT17

Sub-commands:
  /odoo-service start [config] [--dev]       Start server
  /odoo-service stop [--port PORT]           Stop server
  /odoo-service init [--version N]           Initialize environment
  /odoo-service db [operation]               Database operations
  /odoo-service docker [operation]           Docker management
  /odoo-service ide [vscode|pycharm|all]     Generate IDE configs

Examples:
  /odoo-service start TAQAT17.conf --dev
  /odoo-service stop
  /odoo-service db backup --db TAQAT17
  /odoo-service ide vscode
```

---

## 1. start — Start Odoo Server

```
/odoo-service start [CONFIG] [--dev] [--workers N] [--db DATABASE] [--port PORT] [--detach] [--docker]
```

| Flag | Description | Default |
|------|-------------|---------|
| `CONFIG` | Config filename or path (positional) | Auto-detected / prompt |
| `--dev` | Enable `--dev=all` (auto-reload, debug) | False |
| `--workers N` | Worker processes | 0 |
| `--db DATABASE` | Override database | From config |
| `--port PORT` | HTTP port override | From config |
| `--detach` | Run in background | False |
| `--docker` | Force Docker mode | Auto |

### Behavior

**No config specified**: Scan `conf/` directory, list available `.conf` files, prompt user to select one.

**Local venv mode**:
```bash
python -m odoo -c conf/PROJECT.conf              # basic
python -m odoo -c conf/PROJECT.conf --dev=all     # with --dev
python -m odoo -c conf/PROJECT.conf --workers=4   # production
```

**Docker mode**:
```bash
docker-compose up -d
docker-compose up -d --build   # if --build flag
```

### Post-Start Verification

1. Port 8069 is listening within 10 seconds
2. HTTP GET to `/web/login` returns 200
3. Print: `Odoo is running at http://localhost:PORT`

### Troubleshooting

| Error | Fix |
|-------|-----|
| Address already in use | Run `/odoo-service stop` first |
| Config file not found | Check `conf/` directory |
| No module named odoo | Activate venv or check Python path |
| PostgreSQL connection failed | Start PostgreSQL service |

---

## 2. stop — Stop Odoo Server

```
/odoo-service stop [--port PORT] [--docker] [--all] [--force]
```

| Flag | Description | Default |
|------|-------------|---------|
| `--port PORT` | HTTP port to kill | 8069 |
| `--docker` | Stop Docker containers | Auto-detect |
| `--all` | Kill ALL Odoo Python processes | False |
| `--force` | Skip confirmation | False |

### Behavior

**Auto-detect**: If `docker-compose.yml` exists, run `docker-compose stop`. Otherwise kill local processes.

**Local — kill by port** (Windows):
```powershell
FOR /F "tokens=5" %P IN ('netstat -ano ^| findstr :8069') DO taskkill /PID %P /F
FOR /F "tokens=5" %P IN ('netstat -ano ^| findstr :8072') DO taskkill /PID %P /F
```

**Local — kill by port** (Linux/Mac):
```bash
lsof -ti:8069 | xargs kill -9
lsof -ti:8072 | xargs kill -9
```

**Docker**:
```bash
docker-compose stop
```

**Nuclear option** (`--all`): Kill all Python/Odoo processes on the system.

### Verification

After stopping, confirm port 8069 is no longer listening. If still in use after 3 seconds, suggest force kill.

---

## 3. init — Initialize Odoo Environment

```
/odoo-service init --version VERSION --project NAME [--port PORT] [--docker] [--db DATABASE] [--workers N] [--no-venv]
```

| Flag | Description | Default |
|------|-------------|---------|
| `--version N` | Odoo version (14-19) | Required |
| `--project NAME` | Project/client name | Required |
| `--port PORT` | HTTP port | 8069 |
| `--docker` | Generate Docker files instead of venv | False |
| `--db DATABASE` | Database name | project+version |
| `--workers N` | Workers in config | 0 |
| `--no-venv` | Skip venv creation | False |

### Local Venv Init

Creates:
```
PROJECT/
├── .venv/                    # Virtual environment
├── conf/
│   └── PROJECT{VER}.conf     # Generated config
├── logs/
├── data/
├── backups/
├── projects/PROJECT/         # Addon directory
└── .gitignore
```

Generated config (`conf/PROJECT17.conf`):
```ini
[options]
addons_path = odoo\addons,projects\PROJECT
admin_passwd = 123
db_host = localhost
db_port = 5432
db_user = odoo
db_password = odoo
dbfilter = PROJECT17.*
http_port = 8069
gevent_port = 8072
workers = 0
```

### Docker Init

Creates `Dockerfile`, `docker-compose.yml`, `.env`, `.env.example`, plus the same directory structure.

### Step-by-Step Output

```
ODOO {VER} ENVIRONMENT INITIALIZATION
======================================
[STEP 1] Creating directory structure...     [OK]
[STEP 2] Creating virtual environment...     [OK]
[STEP 3] Installing requirements...          [OK]
[STEP 4] Checking PostgreSQL connection...   [OK]
[STEP 5] Generating configuration file...    [OK]
[STEP 6] Creating .gitignore...              [OK]
[STEP 7] Checking wkhtmltopdf...             [OK]
======================================
INITIALIZATION COMPLETE
Config: conf/PROJECT17.conf
Next: /odoo-service start PROJECT17.conf --dev
```

---

## 4. db — Database Operations

```
/odoo-service db <operation> [options]
```

### Operations

| Operation | Usage |
|-----------|-------|
| `backup` | `/odoo-service db backup --db NAME [--format sql\|dump] [--output DIR] [--docker CONTAINER]` |
| `restore` | `/odoo-service db restore --file PATH --db NAME [--no-create] [--docker CONTAINER]` |
| `create` | `/odoo-service db create --db NAME [--host H] [--port P]` |
| `drop` | `/odoo-service db drop --db NAME [--yes]` |
| `list` | `/odoo-service db list [--host H] [--user U]` |
| `reset-admin` | `/odoo-service db reset-admin --db NAME --password PASS` |
| `modules` | `/odoo-service db modules --db NAME` |
| `auto-backup` | `/odoo-service db auto-backup --config CONF --output DIR` |

### Connection Options (all operations)

```
--host localhost   --port 5432   --user odoo   --password odoo
```

### Backup

Default format: `.dump` (pg_dump -Fc, compressed). SQL format with `--format sql`.
Output: `backups/NAME_YYYYMMDD_HHMMSS.dump`

### Restore

Auto-detects format from file extension. Use `--no-create` if database already exists.

### Docker Database Operations

```bash
# Backup via Docker
docker exec CONTAINER pg_dump -U odoo -Fc DBNAME > backups/NAME.dump

# Restore via Docker
docker exec -i CONTAINER pg_restore -U odoo -d DBNAME < backup.dump
```

### Reset Admin

Executes: `UPDATE res_users SET password='PASS' WHERE login='admin';`
Odoo re-hashes the password on next login.

---

## 5. docker — Docker Management

```
/odoo-service docker <operation> [options]
```

### Operations

| Operation | Command Executed |
|-----------|-----------------|
| `init --version N --project NAME` | Generate Dockerfile + docker-compose.yml + .env |
| `build [--no-cache]` | `docker-compose build` |
| `up [--build]` | `docker-compose up -d` |
| `down [--volumes]` | `docker-compose down` |
| `start` | `docker-compose start` |
| `stop` | `docker-compose stop` |
| `restart [--service SVC]` | `docker-compose restart [SVC]` |
| `logs [--tail N] [--service SVC]` | `docker-compose logs -f --tail=N SVC` |
| `shell [--service SVC]` | `docker-compose exec SVC bash` |
| `odoo-shell --db DB` | `docker-compose exec odoo python -m odoo shell -d DB` |
| `update --db DB --module MOD` | `docker-compose exec odoo python -m odoo -u MOD --stop-after-init` |
| `install --db DB --module MOD` | `docker-compose exec odoo python -m odoo -i MOD --stop-after-init` |
| `status` | `docker-compose ps` |

### Generated Dockerfile

Version-appropriate Dockerfile with: Python base image, system deps (libpq, libxml2, npm), wkhtmltopdf 0.12.6.1, rtlcss, pip requirements. Exposes 8069 + 8072.

---

## 6. ide — IDE Configuration Generator

```
/odoo-service ide [vscode|pycharm|all] [--config CONFIG] [--project NAME] [--venv PATH]
```

Auto-detects from the environment:
- **Odoo version**: from `odoo/release.py` or directory name
- **Config path**: from `conf/` scan
- **Venv path**: `.venv/` or `venv/`
- **Addons paths**: parsed from the active `.conf` file's `addons_path`
- **Python path**: `{venv}/Scripts/python.exe` (Windows) or `{venv}/bin/python` (Linux/Mac)

### 6a. `/odoo-service ide vscode`

Generates four files under `.vscode/`:

#### `.vscode/launch.json` — 3 Debug Configurations

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Odoo: Launch",
      "type": "debugpy",
      "request": "launch",
      "module": "odoo",
      "args": ["-c", "conf/${CONFIG}", "--dev=all"],
      "pythonPath": "${VENV}/Scripts/python.exe",
      "cwd": "${workspaceFolder}",
      "console": "integratedTerminal",
      "justMyCode": false
    },
    {
      "name": "Odoo: Attach",
      "type": "debugpy",
      "request": "attach",
      "connect": { "host": "localhost", "port": 5678 },
      "pathMappings": [
        { "localRoot": "${workspaceFolder}", "remoteRoot": "${workspaceFolder}" }
      ],
      "justMyCode": false
    },
    {
      "name": "Odoo: Test Module",
      "type": "debugpy",
      "request": "launch",
      "module": "odoo",
      "args": [
        "-c", "conf/${CONFIG}",
        "-d", "${DB}",
        "--test-enable",
        "-i", "${input:moduleName}",
        "--stop-after-init"
      ],
      "pythonPath": "${VENV}/Scripts/python.exe",
      "cwd": "${workspaceFolder}",
      "console": "integratedTerminal",
      "justMyCode": false
    }
  ],
  "inputs": [
    {
      "id": "moduleName",
      "type": "promptString",
      "description": "Module name to test"
    }
  ]
}
```

Replace `${CONFIG}`, `${VENV}`, `${DB}` with detected values. On Linux/Mac use `bin/python` instead of `Scripts/python.exe`.

#### `.vscode/tasks.json` — 4 Tasks

```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Odoo: Start Server",
      "type": "shell",
      "command": "${PYTHON}",
      "args": ["-m", "odoo", "-c", "conf/${CONFIG}", "--dev=all"],
      "group": "build",
      "isBackground": true,
      "problemMatcher": []
    },
    {
      "label": "Odoo: Update Module",
      "type": "shell",
      "command": "${PYTHON}",
      "args": [
        "-m", "odoo",
        "-c", "conf/${CONFIG}",
        "-d", "${DB}",
        "-u", "${input:updateModule}",
        "--stop-after-init"
      ],
      "problemMatcher": []
    },
    {
      "label": "Odoo: Run Tests",
      "type": "shell",
      "command": "${PYTHON}",
      "args": [
        "-m", "odoo",
        "-c", "conf/${CONFIG}",
        "-d", "${DB}",
        "--test-enable",
        "-i", "${input:testModule}",
        "--stop-after-init"
      ],
      "problemMatcher": []
    },
    {
      "label": "Odoo: Scaffold Module",
      "type": "shell",
      "command": "${PYTHON}",
      "args": [
        "odoo-bin", "scaffold",
        "${input:scaffoldName}",
        "projects/${input:scaffoldProject}/"
      ],
      "problemMatcher": []
    }
  ],
  "inputs": [
    { "id": "updateModule", "type": "promptString", "description": "Module name to update" },
    { "id": "testModule", "type": "promptString", "description": "Module name to test" },
    { "id": "scaffoldName", "type": "promptString", "description": "New module name" },
    { "id": "scaffoldProject", "type": "promptString", "description": "Project directory name" }
  ]
}
```

Replace `${PYTHON}` with the full venv Python path, `${CONFIG}` and `${DB}` with detected values.

#### `.vscode/settings.json` — Python + Odoo Settings

```json
{
  "python.defaultInterpreterPath": "${VENV}/Scripts/python.exe",
  "python.analysis.extraPaths": [
    "./odoo",
    "./odoo/addons",
    "./projects",
    "./projects/${PROJECT}"
  ],
  "python.analysis.typeCheckingMode": "off",
  "python.analysis.diagnosticSeverityOverrides": {
    "reportMissingImports": "none"
  },
  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff",
    "editor.formatOnSave": true
  },
  "ruff.args": ["--line-length=120"],
  "python.linting.pylintEnabled": true,
  "python.linting.pylintArgs": [
    "--load-plugins=pylint_odoo",
    "--disable=all",
    "--enable=anomalous-backslash-in-string,dangerous-default-value,duplicate-key,missing-manifest-dependency,redundant-modulename-xml,xml-syntax-error"
  ],
  "files.associations": {
    "*.xml": "xml",
    "*.conf": "ini",
    "*.po": "po"
  },
  "files.exclude": {
    "**/__pycache__": true,
    "**/*.pyc": true,
    ".venv": true,
    "odoo/addons/**": false
  },
  "editor.rulers": [120],
  "editor.tabSize": 4,
  "editor.insertSpaces": true,
  "search.exclude": {
    ".venv": true,
    "**/__pycache__": true,
    "odoo/addons": true
  }
}
```

Populate `python.analysis.extraPaths` with actual addons paths parsed from the config file. Adjust `python.defaultInterpreterPath` for the platform.

#### `.vscode/extensions.json` — Recommended Extensions

```json
{
  "recommendations": [
    "ms-python.python",
    "ms-python.vscode-pylance",
    "charliermarsh.ruff",
    "redhat.vscode-xml",
    "eamodio.gitlens",
    "trinhanhngoc.vscode-odoo-snippets"
  ]
}
```

---

### 6b. `/odoo-service ide pycharm`

Generates PyCharm run configurations under `.run/` and source roots under `.idea/`.

#### `.run/odoo-server.run.xml` — Server Run Config

```xml
<component name="ProjectRunConfigurationManager">
  <configuration default="false" name="Odoo: ${PROJECT}" type="PythonConfigurationType" factoryName="Python">
    <module name="${PROJECT}" />
    <option name="INTERPRETER_OPTIONS" value="" />
    <option name="PARENT_ENVS" value="true" />
    <option name="SDK_HOME" value="${VENV}/Scripts/python.exe" />
    <option name="WORKING_DIRECTORY" value="$PROJECT_DIR$" />
    <option name="IS_MODULE_SDK" value="false" />
    <option name="ADD_CONTENT_ROOTS" value="true" />
    <option name="ADD_SOURCE_ROOTS" value="true" />
    <option name="SCRIPT_NAME" value="$PROJECT_DIR$/odoo-bin" />
    <option name="PARAMETERS" value="-c conf/${CONFIG} --dev=all" />
  </configuration>
</component>
```

#### `.run/odoo-test.run.xml` — Test Run Config

```xml
<component name="ProjectRunConfigurationManager">
  <configuration default="false" name="Odoo: Test Module" type="PythonConfigurationType" factoryName="Python">
    <module name="${PROJECT}" />
    <option name="SDK_HOME" value="${VENV}/Scripts/python.exe" />
    <option name="WORKING_DIRECTORY" value="$PROJECT_DIR$" />
    <option name="SCRIPT_NAME" value="$PROJECT_DIR$/odoo-bin" />
    <option name="PARAMETERS" value="-c conf/${CONFIG} -d ${DB} --test-enable -i MODULE_NAME --stop-after-init" />
  </configuration>
</component>
```

#### `.idea/` Source Roots

Create or update `.idea/${PROJECT}.iml` to include source roots:

```xml
<module type="PYTHON_MODULE" version="4">
  <component name="NewModuleRootManager">
    <content url="file://$MODULE_DIR$">
      <sourceFolder url="file://$MODULE_DIR$/odoo" isTestSource="false" />
      <sourceFolder url="file://$MODULE_DIR$/odoo/addons" isTestSource="false" />
      <sourceFolder url="file://$MODULE_DIR$/projects" isTestSource="false" />
      <excludeFolder url="file://$MODULE_DIR$/.venv" />
      <excludeFolder url="file://$MODULE_DIR$/logs" />
    </content>
    <orderEntry type="inheritedJdk" />
    <orderEntry type="sourceFolder" forTests="false" />
  </component>
</module>
```

Replace all `${PROJECT}`, `${CONFIG}`, `${DB}`, `${VENV}` placeholders with auto-detected values. On Linux/Mac use `bin/python`.

---

### 6c. `/odoo-service ide all`

Generates everything from 6a + 6b, plus shared config files:

#### `.editorconfig` — Universal Editor Settings

```ini
root = true

[*]
charset = utf-8
end_of_line = lf
insert_final_newline = true
trim_trailing_whitespace = true
indent_style = space

[*.{py,xml,js,scss,css}]
indent_size = 4

[*.{json,yml,yaml}]
indent_size = 2

[*.md]
trim_trailing_whitespace = false

[Makefile]
indent_style = tab
```

### IDE Output Summary

After generation, print:

```
IDE Configuration Generated
============================
Odoo Version: 17.0
Config File:  conf/TAQAT17.conf
Python Path:  .venv/Scripts/python.exe
Addons Path:  odoo/addons, projects/TAQAT

Files created:
  .vscode/launch.json      (3 debug configs)
  .vscode/tasks.json        (4 tasks)
  .vscode/settings.json     (Pylance + Ruff + Odoo paths)
  .vscode/extensions.json   (6 recommended extensions)
  .run/odoo-server.run.xml  (PyCharm server config)
  .run/odoo-test.run.xml    (PyCharm test config)
  .idea/${PROJECT}.iml      (source roots)
  .editorconfig             (universal formatting)
```

---

## Supported Odoo Versions

| Version | Python | Longpolling Key | Extra Deps |
|---------|--------|----------------|------------|
| 14 | 3.7 - 3.10 | `longpolling_port` | — |
| 15 | 3.8 - 3.11 | `longpolling_port` | — |
| 16 | 3.9 - 3.12 | `gevent_port` | — |
| 17 | 3.10 - 3.13 | `gevent_port` | — |
| 18 | 3.10 - 3.13 | `gevent_port` | cbor2 |
| 19 | 3.10 - 3.13 | `gevent_port` | libmagic1 |

---

## Scripts Reference

Located in `odoo-service/scripts/`:

| Script | Used By |
|--------|---------|
| `server_manager.py` | `start`, `stop` |
| `env_initializer.py` | `init` |
| `db_manager.py` | `db` |
| `docker_manager.py` | `docker` |
| `ide_configurator.py` | `ide` |

---

## Previously Separate Commands

The following commands are now unified under `/odoo-service`:

| Old Command | New Equivalent |
|-------------|---------------|
| `/odoo-start` | `/odoo-service start` |
| `/odoo-stop` | `/odoo-service stop` |
| `/odoo-init` | `/odoo-service init` |
| `/odoo-db` | `/odoo-service db` |
| `/odoo-docker` | `/odoo-service docker` |
| `/odoo-ide` | `/odoo-service ide` |
