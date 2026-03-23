# DevOps Plugin - Predefined References

> **Purpose**: This directory contains predefined references that help Claude Code make intelligent decisions when working with Azure DevOps. These references are automatically loaded and provide best practices, routing rules, and automation templates.

## Reference System Overview

References are markdown files that Claude loads to understand:
- **When to use CLI vs MCP** (intelligent routing)
- **Best practices** for each tool
- **Reusable templates** for common workflows
- **WIQL patterns** for work item queries
- **Team-specific workflows** for YOUR-ORG

## Reference Files

| File | Priority | Description |
|------|----------|-------------|
| `hybrid_routing.md` | HIGH | Decision matrix for CLI vs MCP routing |
| `cli_best_practices.md` | HIGH | Azure DevOps CLI patterns and tips |
| `work_tracking.md` | HIGH | Work tracker file patterns, time logging, compliance checks |
| `mcp_best_practices.md` | MEDIUM | MCP tool usage patterns |
| `automation_templates.md` | MEDIUM | Reusable scripts (PowerShell, Bash, Python) |
| `wiql_queries.md` | LOW | Common Work Item Query Language patterns |
| `team_workflows.md` | LOW | organization-specific workflows |

---

## How References Work

### 1. Automatic Loading
When Claude Code starts a DevOps-related task, relevant references are loaded based on:
- Task keywords (e.g., "automate", "query", "batch")
- Tool requirements (CLI-only, MCP-only, hybrid)
- Context (sprint planning, code review, CI/CD)

### 2. Intelligent Routing
The `hybrid_routing.md` reference teaches Claude when to:
- **Use CLI**: Batch operations, infrastructure, variables, scripting
- **Use MCP**: Interactive queries, code reviews, test plans, search
- **Use Both**: Complex workflows requiring both tools

### 3. Best Practices Application
CLI and MCP best practices references ensure:
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

## Reference Usage Examples

### Example 1: User asks for batch work item updates

```
User: "Update all tasks in Sprint 15 to Active state"

Claude's Reference Access:
1. hybrid_routing.md -> Determines CLI is best for batch operations
2. cli_best_practices.md -> Gets parallel execution pattern
3. automation_templates.md -> Uses bulk update template

Result: Claude uses CLI with parallel execution for speed
```

### Example 2: User asks for code review

```
User: "Review PR #45 and add comments"

Claude's Reference Access:
1. hybrid_routing.md -> Determines MCP is best for PR reviews
2. mcp_best_practices.md -> Gets PR thread handling pattern

Result: Claude uses MCP tools for natural code review workflow
```

### Example 3: User asks for sprint report

```
User: "Generate full sprint report with test results"

Claude's Reference Access:
1. hybrid_routing.md -> Determines HYBRID approach needed
2. cli_best_practices.md -> CLI for iteration/capacity data
3. mcp_best_practices.md -> MCP for test results
4. automation_templates.md -> Uses sprint report template

Result: Claude combines CLI + MCP for comprehensive report
```

---

## Adding New References

To add a new reference file:

1. Create a markdown file in `references/` directory
2. Use clear headers and structured content
3. Include practical examples
4. Update this README with the new file

### Reference File Template

```markdown
# Reference Title

> **Purpose**: Brief description of what this reference provides.

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

## Related References
- reference_name.md
```

---

## Environment Variables

These references reference environment variables:

| Variable | Used By | Purpose |
|----------|---------|---------|
| `AZURE_DEVOPS_EXT_PAT` | CLI | PAT authentication for CLI |
| `ADO_PAT_TOKEN` | MCP | PAT authentication for MCP server |
| `DEVOPS_HYBRID_MODE` | Plugin | Enables hybrid routing (true/false) |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 2.0.0 | 2025-12 | Initial reference system with hybrid routing |

---

## Related Files

- `../commands/init.md` - Setup command documentation (formerly devops.md)
- `../devops/SKILL.md` - Main skill definition
- `../.claude-plugin/plugin.json` - Plugin configuration
