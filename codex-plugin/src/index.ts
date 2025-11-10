#!/usr/bin/env node

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  ListPromptsRequestSchema,
  GetPromptRequestSchema,
  ErrorCode,
  McpError
} from '@modelcontextprotocol/sdk/types.js';
import fs from 'fs-extra';
import path from 'path';
import glob from 'glob';
import yaml from 'js-yaml';
import { fileURLToPath } from 'url';
import { dirname } from 'path';
import { CodeAnalyzer } from './analyzers/code-analyzer.js';
import { PatternLibrary } from './patterns/pattern-library.js';
import { CodeGenerator } from './generators/code-generator.js';
import { KnowledgeBase } from './knowledge/knowledge-base.js';
import { ProjectOptimizer } from './optimizers/project-optimizer.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

class CodexServer {
  private server: Server;
  private codeAnalyzer: CodeAnalyzer;
  private patternLibrary: PatternLibrary;
  private codeGenerator: CodeGenerator;
  private knowledgeBase: KnowledgeBase;
  private projectOptimizer: ProjectOptimizer;

  constructor() {
    this.server = new Server(
      {
        name: 'codex',
        version: '1.0.0',
      },
      {
        capabilities: {
          tools: {},
          prompts: {}
        },
      }
    );

    this.codeAnalyzer = new CodeAnalyzer();
    this.patternLibrary = new PatternLibrary();
    this.codeGenerator = new CodeGenerator();
    this.knowledgeBase = new KnowledgeBase();
    this.projectOptimizer = new ProjectOptimizer();

    this.setupHandlers();
  }

  private setupHandlers(): void {
    // List available tools
    this.server.setRequestHandler(ListToolsRequestSchema, async () => ({
      tools: [
        // Code Analysis Tools
        {
          name: 'analyze_code',
          description: 'Deep analysis of code structure, patterns, dependencies, and quality metrics',
          inputSchema: {
            type: 'object',
            properties: {
              path: { type: 'string', description: 'File or directory path to analyze' },
              language: { type: 'string', description: 'Programming language (auto-detect if not specified)' },
              depth: { type: 'string', enum: ['quick', 'standard', 'deep'], description: 'Analysis depth' }
            },
            required: ['path']
          }
        },
        {
          name: 'find_patterns',
          description: 'Detect design patterns, anti-patterns, and code smells in your codebase',
          inputSchema: {
            type: 'object',
            properties: {
              path: { type: 'string', description: 'Path to analyze' },
              patterns: {
                type: 'array',
                items: { type: 'string' },
                description: 'Specific patterns to look for (optional)'
              }
            },
            required: ['path']
          }
        },

        // Code Generation Tools
        {
          name: 'generate_boilerplate',
          description: 'Generate boilerplate code for any framework or pattern (React, Vue, Django, Flask, Express, Odoo, etc.)',
          inputSchema: {
            type: 'object',
            properties: {
              type: { type: 'string', description: 'Type of boilerplate (e.g., react-component, vue-store, django-model, odoo-module, express-api)' },
              name: { type: 'string', description: 'Name for the generated code' },
              options: { type: 'object', description: 'Framework-specific options' },
              outputPath: { type: 'string', description: 'Where to save the generated code' }
            },
            required: ['type', 'name']
          }
        },
        {
          name: 'generate_tests',
          description: 'Auto-generate test cases for functions, classes, or modules',
          inputSchema: {
            type: 'object',
            properties: {
              sourcePath: { type: 'string', description: 'Path to source code' },
              framework: { type: 'string', description: 'Test framework (jest, pytest, unittest, mocha, etc.)' },
              coverage: { type: 'string', enum: ['basic', 'comprehensive', 'edge-cases'], description: 'Test coverage level' }
            },
            required: ['sourcePath']
          }
        },
        {
          name: 'generate_documentation',
          description: 'Generate comprehensive documentation from code (JSDoc, Python docstrings, README, API docs)',
          inputSchema: {
            type: 'object',
            properties: {
              path: { type: 'string', description: 'Path to code' },
              format: { type: 'string', enum: ['jsdoc', 'docstring', 'markdown', 'openapi'], description: 'Documentation format' },
              includeExamples: { type: 'boolean', description: 'Include usage examples' }
            },
            required: ['path', 'format']
          }
        },

        // Refactoring & Optimization Tools
        {
          name: 'suggest_refactoring',
          description: 'Analyze code and suggest refactoring improvements',
          inputSchema: {
            type: 'object',
            properties: {
              path: { type: 'string', description: 'Path to analyze' },
              focus: {
                type: 'array',
                items: { type: 'string', enum: ['performance', 'readability', 'maintainability', 'security', 'dry'] },
                description: 'Areas to focus on'
              }
            },
            required: ['path']
          }
        },
        {
          name: 'optimize_imports',
          description: 'Optimize and organize imports/requires in your code',
          inputSchema: {
            type: 'object',
            properties: {
              path: { type: 'string', description: 'File or directory path' },
              style: { type: 'string', enum: ['grouped', 'alphabetical', 'auto'], description: 'Import organization style' }
            },
            required: ['path']
          }
        },

        // Knowledge & Learning Tools
        {
          name: 'explain_code',
          description: 'Get detailed explanation of code functionality, algorithms, or patterns',
          inputSchema: {
            type: 'object',
            properties: {
              code: { type: 'string', description: 'Code to explain' },
              level: { type: 'string', enum: ['beginner', 'intermediate', 'expert'], description: 'Explanation level' },
              focus: { type: 'string', description: 'Specific aspect to focus on (optional)' }
            },
            required: ['code']
          }
        },
        {
          name: 'find_examples',
          description: 'Find code examples from your codebase or knowledge base',
          inputSchema: {
            type: 'object',
            properties: {
              query: { type: 'string', description: 'What you want examples for' },
              language: { type: 'string', description: 'Programming language' },
              framework: { type: 'string', description: 'Specific framework (optional)' },
              limit: { type: 'number', description: 'Max number of examples', default: 5 }
            },
            required: ['query']
          }
        },

        // Project Management Tools
        {
          name: 'analyze_dependencies',
          description: 'Analyze project dependencies, find vulnerabilities, suggest updates',
          inputSchema: {
            type: 'object',
            properties: {
              projectPath: { type: 'string', description: 'Project root path' },
              checkSecurity: { type: 'boolean', description: 'Check for vulnerabilities', default: true },
              checkUpdates: { type: 'boolean', description: 'Check for available updates', default: true }
            },
            required: ['projectPath']
          }
        },
        {
          name: 'create_project_structure',
          description: 'Generate optimal project structure for any technology stack',
          inputSchema: {
            type: 'object',
            properties: {
              stack: { type: 'string', description: 'Technology stack (e.g., MERN, Django+React, Vue+FastAPI, Odoo)' },
              projectName: { type: 'string', description: 'Project name' },
              features: {
                type: 'array',
                items: { type: 'string' },
                description: 'Features to include (auth, api, database, testing, etc.)'
              },
              outputPath: { type: 'string', description: 'Where to create the project' }
            },
            required: ['stack', 'projectName']
          }
        },

        // Conversion & Migration Tools
        {
          name: 'convert_code',
          description: 'Convert code between languages or frameworks (JS to TS, Class to Hooks, etc.)',
          inputSchema: {
            type: 'object',
            properties: {
              source: { type: 'string', description: 'Source code or path' },
              from: { type: 'string', description: 'Source format/language' },
              to: { type: 'string', description: 'Target format/language' },
              preserveComments: { type: 'boolean', description: 'Keep comments', default: true }
            },
            required: ['source', 'from', 'to']
          }
        },

        // Odoo-Specific Tools (since you work with Odoo)
        {
          name: 'odoo_module_wizard',
          description: 'Advanced Odoo module creation with best practices',
          inputSchema: {
            type: 'object',
            properties: {
              moduleName: { type: 'string', description: 'Module name' },
              version: { type: 'string', description: 'Odoo version (14-19)' },
              features: {
                type: 'array',
                items: { type: 'string' },
                description: 'Features to include (models, views, security, reports, etc.)'
              },
              projectPath: { type: 'string', description: 'Project path' }
            },
            required: ['moduleName', 'version']
          }
        },
        {
          name: 'odoo_security_generator',
          description: 'Generate complete security setup for Odoo modules',
          inputSchema: {
            type: 'object',
            properties: {
              modulePath: { type: 'string', description: 'Module path' },
              models: {
                type: 'array',
                items: { type: 'string' },
                description: 'Model names to secure'
              },
              groups: {
                type: 'array',
                items: { type: 'string' },
                description: 'User groups to create'
              }
            },
            required: ['modulePath', 'models']
          }
        }
      ],
    }));

    // List available prompts
    this.server.setRequestHandler(ListPromptsRequestSchema, async () => ({
      prompts: [
        {
          name: 'code-review',
          description: 'Comprehensive code review with actionable feedback'
        },
        {
          name: 'architecture-design',
          description: 'Design system architecture for your project'
        },
        {
          name: 'performance-optimization',
          description: 'Optimize code for better performance'
        },
        {
          name: 'security-audit',
          description: 'Security audit and vulnerability assessment'
        },
        {
          name: 'best-practices',
          description: 'Apply best practices for any technology'
        },
        {
          name: 'debug-assistant',
          description: 'Advanced debugging assistance'
        },
        {
          name: 'learning-path',
          description: 'Create personalized learning path for any technology'
        }
      ]
    }));

    // Handle tool calls
    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      const { name, arguments: args } = request.params;

      try {
        switch (name) {
          case 'analyze_code':
            return await this.handleAnalyzeCode(args);
          case 'find_patterns':
            return await this.handleFindPatterns(args);
          case 'generate_boilerplate':
            return await this.handleGenerateBoilerplate(args);
          case 'generate_tests':
            return await this.handleGenerateTests(args);
          case 'generate_documentation':
            return await this.handleGenerateDocumentation(args);
          case 'suggest_refactoring':
            return await this.handleSuggestRefactoring(args);
          case 'optimize_imports':
            return await this.handleOptimizeImports(args);
          case 'explain_code':
            return await this.handleExplainCode(args);
          case 'find_examples':
            return await this.handleFindExamples(args);
          case 'analyze_dependencies':
            return await this.handleAnalyzeDependencies(args);
          case 'create_project_structure':
            return await this.handleCreateProjectStructure(args);
          case 'convert_code':
            return await this.handleConvertCode(args);
          case 'odoo_module_wizard':
            return await this.handleOdooModuleWizard(args);
          case 'odoo_security_generator':
            return await this.handleOdooSecurityGenerator(args);
          default:
            throw new McpError(
              ErrorCode.MethodNotFound,
              `Tool '${name}' not found`
            );
        }
      } catch (error) {
        if (error instanceof McpError) throw error;
        throw new McpError(
          ErrorCode.InternalError,
          error instanceof Error ? error.message : 'Unknown error'
        );
      }
    });

    // Handle prompt requests
    this.server.setRequestHandler(GetPromptRequestSchema, async (request) => {
      const { name } = request.params;
      return this.getPrompt(name);
    });
  }

  // Tool implementations
  private async handleAnalyzeCode(args: any) {
    const analysis = await this.codeAnalyzer.analyze(args.path, args.language, args.depth);
    return {
      content: [
        {
          type: 'text',
          text: JSON.stringify(analysis, null, 2)
        }
      ]
    };
  }

  private async handleFindPatterns(args: any) {
    const patterns = await this.patternLibrary.findPatterns(args.path, args.patterns);
    return {
      content: [
        {
          type: 'text',
          text: JSON.stringify(patterns, null, 2)
        }
      ]
    };
  }

  private async handleGenerateBoilerplate(args: any) {
    const code = await this.codeGenerator.generateBoilerplate(
      args.type,
      args.name,
      args.options,
      args.outputPath
    );
    return {
      content: [
        {
          type: 'text',
          text: code
        }
      ]
    };
  }

  private async handleGenerateTests(args: any) {
    const tests = await this.codeGenerator.generateTests(
      args.sourcePath,
      args.framework,
      args.coverage
    );
    return {
      content: [
        {
          type: 'text',
          text: tests
        }
      ]
    };
  }

  private async handleGenerateDocumentation(args: any) {
    const docs = await this.codeGenerator.generateDocumentation(
      args.path,
      args.format,
      args.includeExamples
    );
    return {
      content: [
        {
          type: 'text',
          text: docs
        }
      ]
    };
  }

  private async handleSuggestRefactoring(args: any) {
    const suggestions = await this.projectOptimizer.suggestRefactoring(
      args.path,
      args.focus
    );
    return {
      content: [
        {
          type: 'text',
          text: JSON.stringify(suggestions, null, 2)
        }
      ]
    };
  }

  private async handleOptimizeImports(args: any) {
    const optimized = await this.projectOptimizer.optimizeImports(
      args.path,
      args.style
    );
    return {
      content: [
        {
          type: 'text',
          text: optimized
        }
      ]
    };
  }

  private async handleExplainCode(args: any) {
    const explanation = await this.knowledgeBase.explainCode(
      args.code,
      args.level,
      args.focus
    );
    return {
      content: [
        {
          type: 'text',
          text: explanation
        }
      ]
    };
  }

  private async handleFindExamples(args: any) {
    const examples = await this.knowledgeBase.findExamples(
      args.query,
      args.language,
      args.framework,
      args.limit
    );
    return {
      content: [
        {
          type: 'text',
          text: JSON.stringify(examples, null, 2)
        }
      ]
    };
  }

  private async handleAnalyzeDependencies(args: any) {
    const analysis = await this.projectOptimizer.analyzeDependencies(
      args.projectPath,
      args.checkSecurity,
      args.checkUpdates
    );
    return {
      content: [
        {
          type: 'text',
          text: JSON.stringify(analysis, null, 2)
        }
      ]
    };
  }

  private async handleCreateProjectStructure(args: any) {
    const structure = await this.codeGenerator.createProjectStructure(
      args.stack,
      args.projectName,
      args.features,
      args.outputPath
    );
    return {
      content: [
        {
          type: 'text',
          text: structure
        }
      ]
    };
  }

  private async handleConvertCode(args: any) {
    const converted = await this.codeGenerator.convertCode(
      args.source,
      args.from,
      args.to,
      args.preserveComments
    );
    return {
      content: [
        {
          type: 'text',
          text: converted
        }
      ]
    };
  }

  private async handleOdooModuleWizard(args: any) {
    const module = await this.codeGenerator.createOdooModule(
      args.moduleName,
      args.version,
      args.features,
      args.projectPath
    );
    return {
      content: [
        {
          type: 'text',
          text: module
        }
      ]
    };
  }

  private async handleOdooSecurityGenerator(args: any) {
    const security = await this.codeGenerator.generateOdooSecurity(
      args.modulePath,
      args.models,
      args.groups
    );
    return {
      content: [
        {
          type: 'text',
          text: security
        }
      ]
    };
  }

  private getPrompt(name: string) {
    const prompts: Record<string, any> = {
      'code-review': {
        name: 'code-review',
        description: 'Comprehensive code review',
        messages: [
          {
            role: 'user',
            content: {
              type: 'text',
              text: `You are an expert code reviewer. Analyze the provided code for:

1. **Code Quality**: Clean code principles, readability, maintainability
2. **Performance**: Bottlenecks, optimization opportunities
3. **Security**: Vulnerabilities, best practices
4. **Architecture**: Design patterns, SOLID principles
5. **Testing**: Test coverage, edge cases
6. **Documentation**: Comments, docstrings, clarity

Provide actionable feedback with specific examples and improvements.`
            }
          }
        ]
      },
      'architecture-design': {
        name: 'architecture-design',
        description: 'System architecture design',
        messages: [
          {
            role: 'user',
            content: {
              type: 'text',
              text: `You are a senior software architect. Design a comprehensive system architecture considering:

1. **Scalability**: Handle growth efficiently
2. **Performance**: Optimize for speed and efficiency
3. **Security**: Implement defense in depth
4. **Maintainability**: Clean, modular design
5. **Technology Stack**: Choose appropriate tools
6. **Data Flow**: Design efficient data pipelines
7. **Integration**: API design and third-party services
8. **Monitoring**: Observability and logging

Provide detailed architecture with diagrams (as text/ASCII), technology choices, and implementation roadmap.`
            }
          }
        ]
      },
      'performance-optimization': {
        name: 'performance-optimization',
        description: 'Optimize code performance',
        messages: [
          {
            role: 'user',
            content: {
              type: 'text',
              text: `You are a performance optimization expert. Analyze and optimize code for:

1. **Time Complexity**: Algorithm optimization
2. **Space Complexity**: Memory usage
3. **Database Queries**: Query optimization, indexing
4. **Caching**: Strategic caching implementation
5. **Async Operations**: Parallelization, async/await
6. **Resource Usage**: CPU, memory, network
7. **Load Balancing**: Distribution strategies
8. **Benchmarking**: Performance metrics

Provide before/after comparisons with performance metrics and implementation details.`
            }
          }
        ]
      },
      'security-audit': {
        name: 'security-audit',
        description: 'Security vulnerability assessment',
        messages: [
          {
            role: 'user',
            content: {
              type: 'text',
              text: `You are a security expert. Conduct a thorough security audit checking for:

1. **OWASP Top 10**: Common vulnerabilities
2. **Authentication**: Secure auth implementation
3. **Authorization**: Proper access controls
4. **Data Protection**: Encryption, sanitization
5. **Input Validation**: Prevent injection attacks
6. **Dependencies**: Vulnerable packages
7. **Configuration**: Security misconfigurations
8. **Secrets Management**: API keys, credentials

Provide detailed vulnerability report with severity levels and remediation steps.`
            }
          }
        ]
      },
      'best-practices': {
        name: 'best-practices',
        description: 'Apply technology best practices',
        messages: [
          {
            role: 'user',
            content: {
              type: 'text',
              text: `You are an expert in software best practices. Provide guidance on:

1. **Coding Standards**: Language-specific conventions
2. **Design Patterns**: Appropriate pattern usage
3. **Project Structure**: Optimal organization
4. **Testing Strategy**: Unit, integration, E2E
5. **Documentation**: Code, API, user docs
6. **Version Control**: Git workflow, branching
7. **CI/CD**: Automation pipelines
8. **Monitoring**: Logging, metrics, alerts

Provide specific, actionable recommendations with examples.`
            }
          }
        ]
      },
      'debug-assistant': {
        name: 'debug-assistant',
        description: 'Advanced debugging help',
        messages: [
          {
            role: 'user',
            content: {
              type: 'text',
              text: `You are an expert debugger. Help identify and fix issues by:

1. **Error Analysis**: Parse error messages and stack traces
2. **Root Cause**: Identify underlying problems
3. **Debugging Strategy**: Step-by-step approach
4. **Tool Usage**: Debugger, profiler, logging
5. **Common Pitfalls**: Known issues and gotchas
6. **Edge Cases**: Boundary conditions
7. **Testing**: Reproduce and verify fixes
8. **Prevention**: Avoid similar issues

Provide clear debugging steps and multiple solution approaches.`
            }
          }
        ]
      },
      'learning-path': {
        name: 'learning-path',
        description: 'Personalized learning roadmap',
        messages: [
          {
            role: 'user',
            content: {
              type: 'text',
              text: `You are an expert educator and mentor. Create a personalized learning path:

1. **Skill Assessment**: Current knowledge level
2. **Learning Goals**: Short and long-term objectives
3. **Curriculum**: Structured learning modules
4. **Resources**: Books, courses, tutorials, projects
5. **Practice Projects**: Hands-on experience
6. **Milestones**: Progress checkpoints
7. **Community**: Forums, mentors, study groups
8. **Career Path**: Job preparation, portfolio

Design a comprehensive, time-bound learning roadmap with practical exercises.`
            }
          }
        ]
      }
    };

    const prompt = prompts[name];
    if (!prompt) {
      throw new McpError(ErrorCode.InvalidRequest, `Prompt '${name}' not found`);
    }
    return prompt;
  }

  async run(): Promise<void> {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    console.error('Codex MCP server running...');
  }
}

// Main entry point
const server = new CodexServer();
server.run().catch(console.error);