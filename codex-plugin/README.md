# Codex - Universal Development Assistant

A powerful MCP (Model Context Protocol) server that provides Claude with comprehensive coding assistance capabilities. This plugin enhances Claude's ability to analyze, generate, refactor, and optimize code across all programming languages and frameworks.

## Features

### 🔍 Code Analysis
- **Deep Code Analysis**: Analyze structure, complexity, and quality metrics
- **Pattern Detection**: Find design patterns, anti-patterns, and code smells
- **Dependency Analysis**: Check for vulnerabilities, updates, and unused packages
- **Security Scanning**: Identify potential security vulnerabilities

### 🚀 Code Generation
- **Boilerplate Generation**: Create framework-specific boilerplate (React, Vue, Django, Flask, Express, Odoo)
- **Test Generation**: Auto-generate comprehensive test suites (Jest, Pytest, Mocha)
- **Documentation Generation**: Create JSDoc, Python docstrings, markdown, or OpenAPI docs
- **Project Scaffolding**: Generate complete project structures for any stack

### ♻️ Refactoring & Optimization
- **Smart Refactoring**: Get specific recommendations for performance, readability, and maintainability
- **Import Optimization**: Organize and optimize import statements
- **Code Conversion**: Convert between languages (JS→TS) or patterns (callbacks→promises)
- **DRY Principle**: Detect and eliminate code duplication

### 📚 Knowledge & Learning
- **Code Explanation**: Get explanations at beginner, intermediate, or expert level
- **Example Finder**: Find relevant code examples from comprehensive knowledge base
- **Best Practices**: Apply industry standards and conventions
- **Learning Paths**: Get personalized learning roadmaps for any technology

### 🎯 Specialized Support
- **Odoo Development**: Advanced Odoo module creation with security, views, and best practices
- **Multi-Framework**: Support for React, Vue, Angular, Django, Flask, Express, and more
- **Multi-Language**: JavaScript, TypeScript, Python, Java, Go, Rust, and more

## Installation

### Prerequisites
- Node.js 18+ installed
- Claude Desktop app

### Setup Steps

1. **Navigate to the plugin directory**:
```bash
cd C:\odoo\tmp\odoo-claude-plugins\codex
```

2. **Install dependencies**:
```bash
npm install
```

3. **Build the TypeScript code**:
```bash
npm run build
```

4. **Configure Claude Desktop**:

Edit your Claude Desktop configuration file:
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Linux: `~/.config/Claude/claude_desktop_config.json`

Add the codex server configuration:

```json
{
  "mcpServers": {
    "codex": {
      "command": "node",
      "args": ["C:\\odoo\\tmp\\odoo-claude-plugins\\codex\\dist\\index.js"],
      "env": {}
    }
  }
}
```

5. **Restart Claude Desktop** to load the plugin

## Usage

Once installed, you can use the codex skill in Claude by typing:

```
skill: codex
```

Then use any of the available tools:

### Analysis Examples

```
Use the analyze_code tool to analyze my project for quality and patterns
```

```
Find security vulnerabilities in my codebase using find_patterns tool
```

```
Check my project dependencies for updates and vulnerabilities
```

### Generation Examples

```
Generate a React component with TypeScript using generate_boilerplate tool
```

```
Create comprehensive Jest tests for my module using generate_tests tool
```

```
Generate API documentation in OpenAPI format using generate_documentation tool
```

### Refactoring Examples

```
Suggest refactoring improvements for performance using suggest_refactoring tool
```

```
Optimize and organize my imports using optimize_imports tool
```

```
Convert my callback-based code to async/await using convert_code tool
```

### Learning Examples

```
Explain this complex algorithm at a beginner level using explain_code tool
```

```
Find examples of authentication implementation using find_examples tool
```

## Available Tools

| Tool | Description | Use Case |
|------|-------------|----------|
| `analyze_code` | Deep code analysis | Understanding code quality and structure |
| `find_patterns` | Pattern detection | Finding design patterns and anti-patterns |
| `generate_boilerplate` | Code generation | Creating framework-specific starter code |
| `generate_tests` | Test generation | Auto-generating test suites |
| `generate_documentation` | Doc generation | Creating comprehensive documentation |
| `suggest_refactoring` | Refactoring suggestions | Improving code quality |
| `optimize_imports` | Import optimization | Organizing import statements |
| `explain_code` | Code explanation | Understanding complex code |
| `find_examples` | Example finder | Finding relevant code examples |
| `analyze_dependencies` | Dependency analysis | Checking packages for issues |
| `create_project_structure` | Project scaffolding | Setting up new projects |
| `convert_code` | Code conversion | Converting between languages/patterns |
| `odoo_module_wizard` | Odoo module creation | Creating Odoo modules |
| `odoo_security_generator` | Odoo security | Generating security configurations |

## Available Prompts

| Prompt | Description | Focus |
|--------|-------------|-------|
| `code-review` | Comprehensive code review | Quality, performance, security |
| `architecture-design` | System architecture design | Scalability, patterns, technology |
| `performance-optimization` | Performance analysis | Bottlenecks, optimization |
| `security-audit` | Security assessment | Vulnerabilities, best practices |
| `best-practices` | Apply best practices | Standards, conventions |
| `debug-assistant` | Debugging help | Error analysis, solutions |
| `learning-path` | Learning roadmap | Personalized curriculum |

## Development

### Running in Development Mode

```bash
npm run dev
```

This will watch for changes and rebuild automatically.

### Testing the MCP Server

```bash
npm run inspector
```

This launches the MCP inspector to test your server's functionality.

## Architecture

The plugin is built with:
- **TypeScript**: For type safety and better development experience
- **MCP SDK**: For Claude integration
- **Modular Design**: Separate modules for analysis, generation, optimization, and knowledge

### Project Structure

```
codex/
├── src/
│   ├── index.ts                 # Main MCP server
│   ├── analyzers/
│   │   └── code-analyzer.ts     # Code analysis logic
│   ├── patterns/
│   │   └── pattern-library.ts   # Pattern detection
│   ├── generators/
│   │   └── code-generator.ts    # Code generation templates
│   ├── knowledge/
│   │   └── knowledge-base.ts    # Knowledge and examples
│   └── optimizers/
│       └── project-optimizer.ts # Refactoring and optimization
├── dist/                         # Compiled JavaScript
├── package.json                  # Dependencies
├── tsconfig.json                # TypeScript configuration
├── skill.md                     # Skill definition
└── README.md                    # This file
```

## Troubleshooting

### Plugin not showing in Claude

1. Ensure the path in `claude_desktop_config.json` is correct
2. Check that the plugin is built (`npm run build`)
3. Restart Claude Desktop completely
4. Check Claude's MCP logs for errors

### Build errors

```bash
# Clean and rebuild
rm -rf dist/
npm run build
```

### Runtime errors

Check the MCP inspector for detailed error messages:
```bash
npm run inspector
```

## Contributing

Contributions are welcome! To add new features:

1. Add new tool definitions in `src/index.ts`
2. Implement tool logic in appropriate module
3. Update skill.md with new capabilities
4. Test with MCP inspector
5. Submit pull request

## License

MIT

## Support

For issues or questions, create an issue in the repository or contact the maintainer.

## Roadmap

- [ ] Add support for more languages and frameworks
- [ ] Implement AI-powered code reviews
- [ ] Add visual code complexity analysis
- [ ] Create interactive learning modules
- [ ] Add team collaboration features
- [ ] Implement custom rule definitions
- [ ] Add IDE integration support

## Credits

Created by Ahmed for enhancing development productivity with Claude.