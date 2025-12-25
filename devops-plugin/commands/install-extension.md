---
title: 'Install Extension'
read_only: false
type: 'command'
description: 'Install Azure DevOps marketplace extensions using CLI. Browse, search, and install extensions to enhance your DevOps experience. This is a CLI-only feature.'
---

# Install Extension

Install extensions from the Azure DevOps Marketplace using CLI. Extension management is a **CLI-only feature** - MCP does not support this.

## Usage

```
/install-extension <publisher>.<extension-id>
/install-extension search <query>
/install-extension list
/install-extension info <publisher>.<extension-id>
```

## Sub-Commands

| Sub-Command | Description |
|-------------|-------------|
| `<publisher>.<extension-id>` | Install specific extension |
| `search <query>` | Search marketplace for extensions |
| `list` | List installed extensions |
| `info <publisher>.<extension-id>` | Get extension details |
| `uninstall <publisher>.<extension-id>` | Remove extension |
| `enable <publisher>.<extension-id>` | Enable disabled extension |
| `disable <publisher>.<extension-id>` | Disable extension |

---

## Examples

### Install Extension

```
/install-extension ms-devlabs.workitem-feature-timeline-extension
```

**Execution:**
```bash
az devops extension install \
    --publisher-id ms-devlabs \
    --extension-id workitem-feature-timeline-extension
```

**Output:**
```
Extension 'workitem-feature-timeline-extension' by 'ms-devlabs' installed successfully.
```

---

### Search Extensions

```
/install-extension search "time tracker"
```

**Execution:**
```bash
az devops extension search --search-query "time tracker" --output table
```

**Sample Output:**
```
Publisher       Extension ID              Name                    Version
--------------  -----------------------  ----------------------  --------
ms-devlabs      timetracker              Time Tracker            1.5.0
7pace           Timetracker              7pace Timetracker       5.1.0
techtalk        timelog                  TimeLog                 2.3.1
```

---

### List Installed Extensions

```
/install-extension list
```

**Execution:**
```bash
az devops extension list --output table
```

**Sample Output:**
```
Publisher       Extension ID                            Name                              Version   State
--------------  -------------------------------------  --------------------------------  --------  -------
ms-devlabs      workitem-feature-timeline-extension    Feature Timeline                   1.2.0     enabled
ms              vss-services-gitflow                   GitFlow Release Management         1.0.0     enabled
ms-devlabs      vsts-extensions-myExtensions           My Extensions                      1.0.5     enabled
```

---

### Get Extension Info

```
/install-extension info ms-devlabs.workitem-feature-timeline-extension
```

**Execution:**
```bash
az devops extension show \
    --publisher-id ms-devlabs \
    --extension-id workitem-feature-timeline-extension \
    --output yaml
```

---

### Uninstall Extension

```
/install-extension uninstall ms-devlabs.workitem-feature-timeline-extension
```

**Execution:**
```bash
az devops extension uninstall \
    --publisher-id ms-devlabs \
    --extension-id workitem-feature-timeline-extension \
    --yes
```

---

## Popular Extensions

### Work Item Enhancements

| Extension | Publisher.ID | Description |
|-----------|--------------|-------------|
| Feature Timeline | `ms-devlabs.workitem-feature-timeline-extension` | Visualize features on timeline |
| Work Item Visualization | `ms-devlabs.vsts-extensions-workitem-vis` | Visualize work item relationships |
| Estimate | `ms-devlabs.estimate` | Planning poker for estimation |
| Retrospectives | `ms-devlabs.team-retrospectives` | Sprint retrospective tool |

**Install all:**
```bash
/cli-run az devops extension install --publisher-id ms-devlabs --extension-id workitem-feature-timeline-extension
/cli-run az devops extension install --publisher-id ms-devlabs --extension-id estimate
/cli-run az devops extension install --publisher-id ms-devlabs --extension-id team-retrospectives
```

### Pipeline Enhancements

| Extension | Publisher.ID | Description |
|-----------|--------------|-------------|
| GitFlow | `ms.vss-services-gitflow` | GitFlow branching visualization |
| Pull Request Manager | `ms-devlabs.pull-request-manager` | Advanced PR management |
| Build Quality Checks | `ms-devlabs.vss-extensions-buildqualitychecks` | Quality gates for builds |

### Time Tracking

| Extension | Publisher.ID | Description |
|-----------|--------------|-------------|
| 7pace Timetracker | `7pace.Timetracker` | Enterprise time tracking |
| Time Tracker | `ms-devlabs.timetracker` | Simple time tracking |

### Testing & Quality

| Extension | Publisher.ID | Description |
|-----------|--------------|-------------|
| Test & Feedback | `ms.vss-exploratorytesting-web` | Exploratory testing |
| Code Coverage | `ms-devlabs.codecoveragesummary` | Code coverage summary |

---

## Extension Categories

### Search by Category

```bash
# Agile tools
/install-extension search "agile"

# Build and release
/install-extension search "pipeline"

# Code quality
/install-extension search "code quality"

# Testing
/install-extension search "test"

# Time tracking
/install-extension search "time"
```

---

## Bulk Installation

### Install Multiple Extensions

```bash
# DevOps essentials bundle
EXTENSIONS=(
    "ms-devlabs.workitem-feature-timeline-extension"
    "ms-devlabs.estimate"
    "ms-devlabs.team-retrospectives"
    "ms-devlabs.vss-extensions-buildqualitychecks"
)

for EXT in "${EXTENSIONS[@]}"; do
    PUBLISHER=$(echo $EXT | cut -d. -f1)
    EXTID=$(echo $EXT | cut -d. -f2-)
    echo "Installing $EXT..."
    az devops extension install --publisher-id $PUBLISHER --extension-id $EXTID
done
```

**Or use Claude:**
```
Install these extensions: feature timeline, estimate, retrospectives
```

---

## Extension States

| State | Description | Action |
|-------|-------------|--------|
| `enabled` | Active and working | None needed |
| `disabled` | Installed but inactive | Use `enable` command |
| `uninstalled` | Removed | Use `install` command |

### Enable/Disable Extensions

```bash
# Disable extension temporarily
/install-extension disable ms-devlabs.timetracker

# Re-enable extension
/install-extension enable ms-devlabs.timetracker
```

---

## Permission Requirements

Installing extensions typically requires:

| Permission | Level |
|------------|-------|
| Organization Owner | Full access |
| Project Collection Admin | Full access |
| Extension Manager | Can install/uninstall |
| Regular User | Can request extensions |

### Request Extension (Non-Admin)

If you don't have install permissions:
```bash
# This will create an extension request
az devops extension request \
    --publisher-id ms-devlabs \
    --extension-id timetracker
```

---

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| "Extension not found" | Wrong publisher or ID | Use `search` to find correct ID |
| "Access denied" | Insufficient permissions | Contact admin or request extension |
| "Extension already installed" | Already in org | Use `list` to verify |
| "Incompatible version" | Extension needs update | Check marketplace for compatibility |
| "License required" | Paid extension | Purchase license in marketplace |

---

## Extension Discovery Workflow

1. **Search** for extensions matching your need:
   ```
   /install-extension search "retrospective"
   ```

2. **Get info** on promising extensions:
   ```
   /install-extension info ms-devlabs.team-retrospectives
   ```

3. **Check reviews** in Azure DevOps Marketplace web UI

4. **Install** the extension:
   ```
   /install-extension ms-devlabs.team-retrospectives
   ```

5. **Verify** installation:
   ```
   /install-extension list
   ```

---

## Recommended Extensions for TaqaTechno

Based on team workflows, consider installing:

### Must-Have

```
/install-extension ms-devlabs.workitem-feature-timeline-extension
/install-extension ms-devlabs.team-retrospectives
/install-extension ms-devlabs.estimate
```

### Nice-to-Have

```
/install-extension ms-devlabs.vss-extensions-buildqualitychecks
/install-extension ms-devlabs.pull-request-manager
```

---

## Related Commands

- `/cli-run` - Execute any CLI command
- `/setup-pipeline-vars` - Manage pipeline variables
- `/devops setup` - Install CLI and MCP
