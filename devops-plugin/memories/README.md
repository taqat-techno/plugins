# DevOps Plugin - Predefined Memories

> **Purpose**: This directory contains predefined memories that help Claude Code make intelligent decisions when working with Azure DevOps. These memories are automatically loaded and provide best practices, routing rules, and automation templates.

## Memory System Overview

Memories are markdown files that Claude loads to understand:
- **When to use CLI vs MCP** (intelligent routing)
- **Best practices** for each tool
- **Reusable templates** for common workflows
- **WIQL patterns** for work item queries
- **Team-specific workflows** for TaqaTechno

## Memory Files

| File | Priority | Description |
|------|----------|-------------|
| `hybrid_routing.md` | HIGH | Decision matrix for CLI vs MCP routing |
| `cli_best_practices.md` | HIGH | Azure DevOps CLI patterns and tips |
| `mcp_best_practices.md` | MEDIUM | MCP tool usage patterns |
| `automation_templates.md` | MEDIUM | Reusable scripts (PowerShell, Bash, Python) |
| `wiql_queries.md` | LOW | Common Work Item Query Language patterns |
| `team_workflows.md` | LOW | TaqaTechno-specific workflows |

---

## How Memories Work

### 1. Automatic Loading
When Claude Code starts a DevOps-related task, relevant memories are loaded based on:
- Task keywords (e.g., "automate", "query", "batch")
- Tool requirements (CLI-only, MCP-only, hybrid)
- Context (sprint planning, code review, CI/CD)

### 2. Intelligent Routing
The `hybrid_routing.md` memory teaches Claude when to:
- **Use CLI**: Batch operations, infrastructure, variables, scripting
- **Use MCP**: Interactive queries, code reviews, test plans, search
- **Use Both**: Complex workflows requiring both tools

### 3. Best Practices Application
CLI and MCP best practices memories ensure:
- Optimal command structure
- Performance optimization (parallel execution, caching)
- Security (PAT handling, minimal scopes)
- Error handling

### 4. Template Reuse
Automation templates provide ready-to-use:
- PowerShell scripts (Windows)
- Bash scripts (macOS/Linux)
- Python scripts (cross-platform)

---

## Memory Usage Examples

### Example 1: User asks for batch work item updates

```
User: "Update all tasks in Sprint 15 to Active state"

Claude's Memory Access:
1. hybrid_routing.md -> Determines CLI is best for batch operations
2. cli_best_practices.md -> Gets parallel execution pattern
3. automation_templates.md -> Uses bulk update template

Result: Claude uses CLI with parallel execution for speed
```

### Example 2: User asks for code review

```
User: "Review PR #45 and add comments"

Claude's Memory Access:
1. hybrid_routing.md -> Determines MCP is best for PR reviews
2. mcp_best_practices.md -> Gets PR thread handling pattern

Result: Claude uses MCP tools for natural code review workflow
```

### Example 3: User asks for sprint report

```
User: "Generate full sprint report with test results"

Claude's Memory Access:
1. hybrid_routing.md -> Determines HYBRID approach needed
2. cli_best_practices.md -> CLI for iteration/capacity data
3. mcp_best_practices.md -> MCP for test results
4. automation_templates.md -> Uses sprint report template

Result: Claude combines CLI + MCP for comprehensive report
```

---

## Adding New Memories

To add a new memory file:

1. Create a markdown file in `memories/` directory
2. Use clear headers and structured content
3. Include practical examples
4. Update this README with the new file

### Memory File Template

```markdown
# Memory Title

> **Purpose**: Brief description of what this memory provides.

## Quick Reference

| Item | Description |
|------|-------------|
| ... | ... |

## Detailed Patterns

### Pattern 1: Name
Description and example...

### Pattern 2: Name
Description and example...

## Examples

### Example 1
...

## Related Memories
- memory_name.md
```

---

## Environment Variables

These memories reference environment variables:

| Variable | Used By | Purpose |
|----------|---------|---------|
| `AZURE_DEVOPS_EXT_PAT` | CLI | PAT authentication for CLI |
| `ADO_PAT_TOKEN` | MCP | PAT authentication for MCP server |
| `DEVOPS_HYBRID_MODE` | Plugin | Enables hybrid routing (true/false) |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 2.0.0 | 2025-12 | Initial memory system with hybrid routing |

---

## Related Files

- `../commands/devops.md` - Setup command documentation
- `../devops/SKILL.md` - Main skill definition
- `../.claude-plugin/plugin.json` - Plugin configuration
