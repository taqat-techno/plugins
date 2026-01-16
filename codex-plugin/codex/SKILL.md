---
name: codex
description: "Universal development assistant with comprehensive code analysis, generation, refactoring, and optimization tools for all languages and frameworks"
version: "1.0.0"
author: "TAQAT Techno"
license: "MIT"
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - Glob
  - Grep
metadata:
  category: "development"
  tags:
    - code-analysis
    - code-generation
    - refactoring
    - optimization
    - testing
    - documentation
    - security
    - performance
---

# Codex - Universal Development Assistant

Comprehensive coding assistant that helps with ANY programming task. This skill provides intelligent code analysis, generation, refactoring, and optimization across all languages and frameworks.

## When to Use This Skill

Activate the codex skill when you need:
- **Code Analysis**: Deep understanding of code structure, patterns, complexity, and quality metrics
- **Code Generation**: Create boilerplate, tests, documentation, or entire modules from scratch
- **Refactoring**: Improve code performance, readability, or maintainability
- **Project Management**: Analyze dependencies, create project structures, manage technical debt
- **Learning**: Get explanations, examples, or best practices for any technology
- **Conversion**: Convert code between languages or frameworks
- **Security**: Identify vulnerabilities and security issues
- **Optimization**: Find performance bottlenecks and optimization opportunities

## Key Features

### 🔍 Intelligent Analysis
- Analyze code structure, complexity, and quality metrics
- Detect design patterns, anti-patterns, and code smells
- Check dependencies for vulnerabilities and updates
- Security vulnerability scanning
- Performance bottleneck identification

### 🚀 Smart Generation
- Framework-specific boilerplate (React, Vue, Django, Flask, Express, Odoo, etc.)
- Comprehensive test suites (Jest, Pytest, Mocha, etc.)
- Documentation (JSDoc, Python docstrings, markdown, OpenAPI)
- Complete project scaffolding for any technology stack

### ♻️ Advanced Refactoring
- Performance optimization recommendations
- Code readability improvements
- Maintainability enhancements
- Import organization and optimization
- Code conversion between languages/patterns

### 📚 Knowledge Base
- Multi-level explanations (beginner, intermediate, expert)
- Relevant code examples from extensive knowledge base
- Best practices for all major languages and frameworks
- Personalized learning paths

## Available MCP Tools

### Analysis Tools
```
analyze_code - Deep analysis of code structure, patterns, dependencies, and quality
  - path: File or directory to analyze
  - language: Programming language (auto-detect if not specified)
  - depth: Analysis depth (quick, standard, deep)

find_patterns - Detect design patterns, anti-patterns, and code smells
  - path: Path to analyze
  - patterns: Specific patterns to look for (optional)

analyze_dependencies - Check project dependencies
  - projectPath: Project root path
  - checkSecurity: Check for vulnerabilities (default: true)
  - checkUpdates: Check for updates (default: true)
```

### Generation Tools
```
generate_boilerplate - Create framework-specific boilerplate code
  - type: Boilerplate type (e.g., react-component, vue-store, django-model, odoo-module)
  - name: Name for generated code
  - options: Framework-specific options
  - outputPath: Where to save (optional)

generate_tests - Auto-generate comprehensive test suites
  - sourcePath: Path to source code
  - framework: Test framework (jest, pytest, unittest, mocha)
  - coverage: Coverage level (basic, comprehensive, edge-cases)

generate_documentation - Create comprehensive documentation
  - path: Path to code
  - format: Documentation format (jsdoc, docstring, markdown, openapi)
  - includeExamples: Include usage examples

create_project_structure - Generate complete project scaffolding
  - stack: Technology stack (MERN, Django+React, Vue+FastAPI, Odoo)
  - projectName: Project name
  - features: Features to include
  - outputPath: Where to create project
```

### Optimization Tools
```
suggest_refactoring - Get specific refactoring recommendations
  - path: Path to analyze
  - focus: Areas to focus on (performance, readability, maintainability, security, dry)

optimize_imports - Organize and optimize import statements
  - path: File or directory path
  - style: Organization style (grouped, alphabetical, auto)

convert_code - Convert between languages or frameworks
  - source: Source code or path
  - from: Source format/language
  - to: Target format/language
  - preserveComments: Keep comments (default: true)
```

### Knowledge Tools
```
explain_code - Get detailed code explanations
  - code: Code to explain
  - level: Explanation level (beginner, intermediate, expert)
  - focus: Specific aspect to focus on

find_examples - Find relevant code examples
  - query: What you want examples for
  - language: Programming language
  - framework: Specific framework
  - limit: Max examples (default: 5)
```

### Specialized Tools
```
odoo_module_wizard - Create complete Odoo modules
  - moduleName: Module name
  - version: Odoo version (14-19)
  - features: Features to include
  - projectPath: Project path

odoo_security_generator - Generate Odoo security configurations
  - modulePath: Module path
  - models: Model names to secure
  - groups: User groups to create
```

## Available Prompts

### code-review
Comprehensive code review with actionable feedback on:
- Code quality and clean code principles
- Performance bottlenecks
- Security vulnerabilities
- Architecture and design patterns
- Testing coverage
- Documentation

### architecture-design
System architecture design considering:
- Scalability and performance
- Security best practices
- Technology stack selection
- Data flow and integration
- Monitoring and observability

### performance-optimization
Optimize code for:
- Algorithm efficiency
- Memory usage
- Database queries
- Caching strategies
- Async operations
- Resource management

### security-audit
Security assessment including:
- OWASP Top 10 vulnerabilities
- Authentication and authorization
- Data protection
- Input validation
- Dependency vulnerabilities
- Configuration security

### best-practices
Apply best practices for:
- Coding standards
- Design patterns
- Project structure
- Testing strategies
- Documentation
- Version control
- CI/CD

### debug-assistant
Advanced debugging help:
- Error analysis
- Root cause identification
- Debugging strategies
- Tool usage
- Edge case handling

### learning-path
Personalized learning roadmap:
- Skill assessment
- Learning objectives
- Structured curriculum
- Resources and projects
- Progress milestones

## Usage Examples

### Basic Analysis
```
Use the codex skill to analyze my codebase for quality issues and patterns
```

### Code Generation
```
Use codex to generate a React component with TypeScript, including tests and documentation
```

### Refactoring
```
Use codex to suggest refactoring improvements for performance in my Python code
```

### Security Check
```
Use codex to find security vulnerabilities in my Express API
```

### Learning
```
Use codex to explain this sorting algorithm at a beginner level with examples
```

### Project Setup
```
Use codex to create a MERN stack project structure with authentication and testing
```

### Odoo Development
```
Use codex to create an Odoo 17 module with models, views, and security
```

## Supported Technologies

### Languages
JavaScript, TypeScript, Python, Java, C++, C#, Go, Rust, Ruby, PHP, Swift, Kotlin, Scala, R, MATLAB, Dart, Lua, Perl, Shell, SQL, HTML, CSS, SCSS, XML, JSON, YAML, Markdown

### Frameworks
React, Vue, Angular, Svelte, Next.js, Nuxt.js, Express, Nest.js, Django, Flask, FastAPI, Spring, .NET, Rails, Laravel, Symfony

### Specialized Platforms
Odoo (14-19), WordPress, Shopify, Salesforce, SAP

### Databases
PostgreSQL, MySQL, MongoDB, Redis, Cassandra, DynamoDB, SQLite

### Testing Frameworks
Jest, Mocha, Jasmine, Cypress, Playwright, Pytest, Unittest, JUnit, TestNG

### Build Tools
Webpack, Vite, Rollup, Parcel, Gradle, Maven, Make

## Best Practices

1. **Be Specific**: Provide clear context about what you need
2. **Include Code**: Share relevant code snippets for better analysis
3. **Specify Language/Framework**: Help the skill provide targeted assistance
4. **Choose Analysis Depth**: Use 'quick' for rapid checks, 'deep' for comprehensive analysis
5. **Review Suggestions**: Always review generated code and refactoring suggestions
6. **Test Changes**: Verify all modifications with appropriate testing

## Limitations

- Analysis depth depends on file size and complexity
- Generated code should always be reviewed and tested
- Security checks are not exhaustive - use dedicated security tools for production
- Performance suggestions are general - benchmark for your specific use case

## Version History

- v1.0.0: Initial release with comprehensive analysis, generation, and optimization tools

---

For more information or to report issues, contact the maintainer.