export class KnowledgeBase {
  private knowledgeMap = {
    javascript: {
      concepts: [
        'closures', 'prototypes', 'hoisting', 'event loop', 'promises', 'async/await',
        'destructuring', 'spread operator', 'arrow functions', 'modules', 'classes'
      ],
      patterns: [
        'module pattern', 'factory pattern', 'observer pattern', 'singleton pattern',
        'prototype pattern', 'decorator pattern', 'facade pattern', 'proxy pattern'
      ],
      frameworks: ['React', 'Vue', 'Angular', 'Svelte', 'Next.js', 'Nuxt.js', 'Express', 'Nest.js'],
      best_practices: [
        'Use const/let instead of var',
        'Prefer arrow functions for callbacks',
        'Use template literals for string concatenation',
        'Implement proper error handling',
        'Use async/await over callbacks',
        'Avoid global variables',
        'Use strict mode'
      ]
    },
    python: {
      concepts: [
        'decorators', 'generators', 'context managers', 'metaclasses', 'descriptors',
        'GIL', 'list comprehensions', 'lambda functions', 'type hints', 'dataclasses'
      ],
      patterns: [
        'singleton', 'factory', 'observer', 'strategy', 'decorator', 'adapter',
        'template method', 'iterator', 'command'
      ],
      frameworks: ['Django', 'Flask', 'FastAPI', 'Pyramid', 'Tornado', 'Sanic', 'Bottle'],
      best_practices: [
        'Follow PEP 8 style guide',
        'Use virtual environments',
        'Write docstrings for functions',
        'Use type hints',
        'Prefer f-strings for formatting',
        'Use context managers for resources',
        'Handle exceptions properly'
      ]
    },
    odoo: {
      concepts: [
        'ORM', 'models', 'views', 'controllers', 'security', 'workflows', 'reports',
        'wizards', 'computed fields', 'related fields', 'inheritance', 'domains'
      ],
      patterns: [
        'model inheritance', 'view inheritance', 'delegation inheritance',
        'prototype inheritance', 'mixin classes', 'abstract models'
      ],
      modules: [
        'base', 'sale', 'purchase', 'account', 'stock', 'hr', 'crm', 'project',
        'website', 'point_of_sale', 'manufacturing', 'fleet'
      ],
      best_practices: [
        'Use _inherit for extending models',
        'Implement proper security (ir.model.access)',
        'Use computed fields with store=True when appropriate',
        'Follow Odoo naming conventions',
        'Use @api.depends for computed fields',
        'Implement _check constraints for validation',
        'Use record rules for row-level security'
      ]
    },
    databases: {
      sql: {
        concepts: ['joins', 'indexes', 'transactions', 'normalization', 'views', 'triggers'],
        optimization: [
          'Use indexes on frequently queried columns',
          'Avoid SELECT *',
          'Use EXPLAIN to analyze queries',
          'Optimize JOIN operations',
          'Use appropriate data types',
          'Implement connection pooling'
        ]
      },
      nosql: {
        concepts: ['documents', 'collections', 'sharding', 'replication', 'aggregation'],
        databases: ['MongoDB', 'Redis', 'Cassandra', 'CouchDB', 'DynamoDB']
      }
    },
    architecture: {
      patterns: [
        'MVC', 'MVP', 'MVVM', 'microservices', 'serverless', 'event-driven',
        'layered', 'hexagonal', 'clean architecture', 'domain-driven design'
      ],
      principles: [
        'SOLID', 'DRY', 'KISS', 'YAGNI', 'separation of concerns',
        'dependency inversion', 'single responsibility'
      ]
    },
    testing: {
      types: [
        'unit testing', 'integration testing', 'e2e testing', 'performance testing',
        'security testing', 'acceptance testing', 'smoke testing', 'regression testing'
      ],
      frameworks: {
        javascript: ['Jest', 'Mocha', 'Jasmine', 'Cypress', 'Playwright', 'Vitest'],
        python: ['pytest', 'unittest', 'nose2', 'behave', 'robot framework'],
        general: ['Selenium', 'Postman', 'JMeter', 'LoadRunner']
      }
    }
  };

  async explainCode(
    code: string,
    level: string = 'intermediate',
    focus?: string
  ): Promise<string> {
    const explanation = {
      beginner: this.generateBeginnerExplanation(code, focus),
      intermediate: this.generateIntermediateExplanation(code, focus),
      expert: this.generateExpertExplanation(code, focus)
    };

    return explanation[level] || explanation.intermediate;
  }

  async findExamples(
    query: string,
    language?: string,
    framework?: string,
    limit: number = 5
  ): Promise<any[]> {
    const examples: any[] = [];

    // Search for relevant examples based on query
    const queryLower = query.toLowerCase();

    // Common example patterns
    const examplePatterns = {
      'api': this.getApiExamples(language, framework),
      'database': this.getDatabaseExamples(language, framework),
      'authentication': this.getAuthExamples(language, framework),
      'testing': this.getTestingExamples(language, framework),
      'async': this.getAsyncExamples(language),
      'error handling': this.getErrorHandlingExamples(language),
      'validation': this.getValidationExamples(language, framework),
      'crud': this.getCrudExamples(language, framework),
      'routing': this.getRoutingExamples(language, framework),
      'middleware': this.getMiddlewareExamples(language, framework)
    };

    // Find matching examples
    for (const [pattern, getExamples] of Object.entries(examplePatterns)) {
      if (queryLower.includes(pattern)) {
        const patternExamples = getExamples;
        if (patternExamples && patternExamples.length > 0) {
          examples.push(...patternExamples.slice(0, limit));
        }
      }
    }

    // If no specific pattern matched, provide general examples
    if (examples.length === 0) {
      examples.push(...this.getGeneralExamples(query, language, framework, limit));
    }

    return examples.slice(0, limit);
  }

  private generateBeginnerExplanation(code: string, focus?: string): string {
    let explanation = '## Code Explanation for Beginners\n\n';

    // Analyze code structure
    const hasClasses = /class\s+\w+/.test(code);
    const hasFunctions = /function\s+\w+|=>\s*{/.test(code);
    const hasLoops = /for\s*\(|while\s*\(|\.forEach|\.map/.test(code);
    const hasConditions = /if\s*\(|else|switch\s*\(|\?.*:/.test(code);

    explanation += 'This code contains:\n';
    if (hasClasses) explanation += '- **Classes**: Templates for creating objects\n';
    if (hasFunctions) explanation += '- **Functions**: Reusable blocks of code\n';
    if (hasLoops) explanation += '- **Loops**: Code that repeats multiple times\n';
    if (hasConditions) explanation += '- **Conditions**: Decision-making logic\n';

    explanation += '\n### How it works:\n';
    explanation += '1. The code starts by setting up necessary components\n';
    explanation += '2. It processes data or responds to events\n';
    explanation += '3. It returns results or updates the state\n';

    if (focus) {
      explanation += `\n### Focus on ${focus}:\n`;
      explanation += `The ${focus} part of this code is responsible for specific functionality.\n`;
    }

    explanation += '\n### Key concepts to understand:\n';
    explanation += '- Variables store data\n';
    explanation += '- Functions perform actions\n';
    explanation += '- Control flow determines execution order\n';

    return explanation;
  }

  private generateIntermediateExplanation(code: string, focus?: string): string {
    let explanation = '## Code Analysis\n\n';

    // Detect patterns and structures
    const patterns = this.detectCodePatterns(code);

    explanation += '### Structure Overview:\n';
    explanation += this.analyzeStructure(code);

    explanation += '\n### Design Patterns Detected:\n';
    for (const pattern of patterns) {
      explanation += `- ${pattern}\n`;
    }

    explanation += '\n### Code Flow:\n';
    explanation += this.analyzeFlow(code);

    if (focus) {
      explanation += `\n### Detailed Analysis of ${focus}:\n`;
      explanation += this.analyzeFocus(code, focus);
    }

    explanation += '\n### Performance Considerations:\n';
    explanation += this.analyzePerformance(code);

    explanation += '\n### Potential Improvements:\n';
    explanation += this.suggestImprovements(code);

    return explanation;
  }

  private generateExpertExplanation(code: string, focus?: string): string {
    let explanation = '## Expert Analysis\n\n';

    explanation += '### Architectural Patterns:\n';
    explanation += this.analyzeArchitecture(code);

    explanation += '\n### Complexity Analysis:\n';
    explanation += `- Time Complexity: ${this.analyzeTimeComplexity(code)}\n`;
    explanation += `- Space Complexity: ${this.analyzeSpaceComplexity(code)}\n`;
    explanation += `- Cyclomatic Complexity: ${this.analyzeCyclomaticComplexity(code)}\n`;

    explanation += '\n### Advanced Patterns and Techniques:\n';
    explanation += this.analyzeAdvancedPatterns(code);

    if (focus) {
      explanation += `\n### Deep Dive: ${focus}\n`;
      explanation += this.deepDiveAnalysis(code, focus);
    }

    explanation += '\n### Security Analysis:\n';
    explanation += this.analyzeSecurityConcerns(code);

    explanation += '\n### Scalability Considerations:\n';
    explanation += this.analyzeScalability(code);

    explanation += '\n### Optimization Opportunities:\n';
    explanation += this.analyzeOptimizations(code);

    return explanation;
  }

  private detectCodePatterns(code: string): string[] {
    const patterns: string[] = [];

    if (/class.*extends/i.test(code)) patterns.push('Inheritance');
    if (/new\s+\w+\(/i.test(code)) patterns.push('Object instantiation');
    if (/async.*await/i.test(code)) patterns.push('Async/Await pattern');
    if (/Promise/i.test(code)) patterns.push('Promise pattern');
    if (/\.map\(|\.filter\(|\.reduce\(/i.test(code)) patterns.push('Functional programming');
    if (/try.*catch/i.test(code)) patterns.push('Error handling');
    if (/import.*from|require\(/i.test(code)) patterns.push('Module pattern');
    if (/export|module\.exports/i.test(code)) patterns.push('Module exports');

    return patterns;
  }

  private analyzeStructure(code: string): string {
    const lines = code.split('\n').length;
    const functions = (code.match(/function|=>|\bdef\b|\bfn\b/g) || []).length;
    const classes = (code.match(/\bclass\b/g) || []).length;

    return `- Total lines: ${lines}\n- Functions: ${functions}\n- Classes: ${classes}\n`;
  }

  private analyzeFlow(code: string): string {
    return '1. Initialization phase\n2. Main processing logic\n3. Result handling/output\n';
  }

  private analyzeFocus(code: string, focus: string): string {
    return `The ${focus} aspect involves specific implementation details and patterns.\n`;
  }

  private analyzePerformance(code: string): string {
    const issues: string[] = [];

    if (/for.*for/i.test(code)) issues.push('- Nested loops detected (O(n²) complexity)');
    if (/\.forEach.*\.forEach/i.test(code)) issues.push('- Nested iterations may impact performance');
    if (/new Array\(\d{4,}\)/i.test(code)) issues.push('- Large array allocation detected');
    if (/while\s*\(true\)/i.test(code)) issues.push('- Infinite loop risk detected');

    return issues.length > 0 ? issues.join('\n') : 'No obvious performance issues detected';
  }

  private suggestImprovements(code: string): string {
    const suggestions: string[] = [];

    if (!/const|let/i.test(code) && /var/i.test(code)) {
      suggestions.push('- Replace var with const/let');
    }
    if (/console\.\w+/i.test(code)) {
      suggestions.push('- Remove console statements for production');
    }
    if (!(/try.*catch/i.test(code))) {
      suggestions.push('- Consider adding error handling');
    }

    return suggestions.length > 0 ? suggestions.join('\n') : 'Code follows good practices';
  }

  private analyzeArchitecture(code: string): string {
    return 'Analyzing architectural patterns and design decisions...\n';
  }

  private analyzeTimeComplexity(code: string): string {
    if (/for.*for|while.*while/i.test(code)) return 'O(n²) or higher';
    if (/for|while|map|filter|reduce/i.test(code)) return 'O(n)';
    return 'O(1)';
  }

  private analyzeSpaceComplexity(code: string): string {
    if (/new Array|\.slice|\.concat/i.test(code)) return 'O(n)';
    return 'O(1)';
  }

  private analyzeCyclomaticComplexity(code: string): number {
    const decisionPoints = [
      /\bif\b/g, /\belse\s+if\b/g, /\bfor\b/g, /\bwhile\b/g,
      /\bcase\b/g, /\bcatch\b/g, /\&\&/g, /\|\|/g
    ];

    let complexity = 1;
    for (const pattern of decisionPoints) {
      const matches = code.match(pattern);
      if (matches) complexity += matches.length;
    }

    return complexity;
  }

  private analyzeAdvancedPatterns(code: string): string {
    return 'Identifying advanced patterns and techniques used...\n';
  }

  private deepDiveAnalysis(code: string, focus: string): string {
    return `Performing deep analysis on ${focus} aspects of the code...\n`;
  }

  private analyzeSecurityConcerns(code: string): string {
    const concerns: string[] = [];

    if (/eval\(/i.test(code)) concerns.push('- eval() usage detected (security risk)');
    if (/innerHTML/i.test(code)) concerns.push('- innerHTML usage (XSS risk)');
    if (/password|secret|token/i.test(code)) concerns.push('- Sensitive data handling detected');

    return concerns.length > 0 ? concerns.join('\n') : 'No obvious security concerns';
  }

  private analyzeScalability(code: string): string {
    return 'Evaluating scalability aspects and bottlenecks...\n';
  }

  private analyzeOptimizations(code: string): string {
    return 'Identifying optimization opportunities...\n';
  }

  // Example generation methods
  private getApiExamples(language?: string, framework?: string): any[] {
    const examples: any[] = [];

    if (language === 'javascript' && framework === 'express') {
      examples.push({
        title: 'Express REST API Example',
        code: `app.get('/api/users', async (req, res) => {
  try {
    const users = await User.findAll();
    res.json(users);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});`,
        description: 'Basic Express endpoint with error handling'
      });
    }

    if (language === 'python' && framework === 'fastapi') {
      examples.push({
        title: 'FastAPI Endpoint Example',
        code: `@app.get("/api/users")
async def get_users():
    users = await User.all()
    return users`,
        description: 'FastAPI async endpoint'
      });
    }

    return examples;
  }

  private getDatabaseExamples(language?: string, framework?: string): any[] {
    const examples: any[] = [];

    if (language === 'javascript') {
      examples.push({
        title: 'MongoDB Query Example',
        code: `const users = await User.find({ age: { $gte: 18 } })
  .sort({ createdAt: -1 })
  .limit(10);`,
        description: 'MongoDB query with filtering and sorting'
      });
    }

    if (language === 'python') {
      examples.push({
        title: 'SQLAlchemy Query Example',
        code: `users = session.query(User)\\
  .filter(User.age >= 18)\\
  .order_by(User.created_at.desc())\\
  .limit(10)\\
  .all()`,
        description: 'SQLAlchemy ORM query'
      });
    }

    return examples;
  }

  private getAuthExamples(language?: string, framework?: string): any[] {
    const examples: any[] = [];

    examples.push({
      title: 'JWT Authentication',
      code: language === 'javascript' ?
        `const token = jwt.sign({ userId: user.id }, SECRET_KEY, { expiresIn: '24h' });` :
        `token = jwt.encode({'user_id': user.id}, SECRET_KEY, algorithm='HS256')`,
      description: 'JWT token generation'
    });

    return examples;
  }

  private getTestingExamples(language?: string, framework?: string): any[] {
    const examples: any[] = [];

    if (language === 'javascript') {
      examples.push({
        title: 'Jest Test Example',
        code: `describe('User Service', () => {
  it('should create a new user', async () => {
    const user = await createUser({ name: 'Test' });
    expect(user.name).toBe('Test');
  });
});`,
        description: 'Jest unit test'
      });
    }

    return examples;
  }

  private getAsyncExamples(language?: string): any[] {
    const examples: any[] = [];

    if (language === 'javascript') {
      examples.push({
        title: 'Async/Await Example',
        code: `async function fetchData() {
  try {
    const response = await fetch('/api/data');
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Error:', error);
  }
}`,
        description: 'Async function with error handling'
      });
    }

    return examples;
  }

  private getErrorHandlingExamples(language?: string): any[] {
    const examples: any[] = [];

    examples.push({
      title: 'Error Handling Pattern',
      code: language === 'javascript' ?
        `try {
  // risky operation
} catch (error) {
  logger.error(error);
  throw new CustomError('Operation failed', error);
}` :
        `try:
    # risky operation
except Exception as e:
    logger.error(e)
    raise CustomError('Operation failed') from e`,
      description: 'Proper error handling with logging'
    });

    return examples;
  }

  private getValidationExamples(language?: string, framework?: string): any[] {
    const examples: any[] = [];

    if (framework === 'express') {
      examples.push({
        title: 'Express Validation Middleware',
        code: `const validateUser = [
  body('email').isEmail(),
  body('age').isInt({ min: 0 }),
  handleValidationErrors
];`,
        description: 'Express-validator usage'
      });
    }

    return examples;
  }

  private getCrudExamples(language?: string, framework?: string): any[] {
    return [
      {
        title: 'CRUD Operations',
        code: `// Create
const item = await Model.create(data);

// Read
const items = await Model.findAll();
const item = await Model.findById(id);

// Update
await Model.update(id, updates);

// Delete
await Model.delete(id);`,
        description: 'Basic CRUD operations'
      }
    ];
  }

  private getRoutingExamples(language?: string, framework?: string): any[] {
    const examples: any[] = [];

    if (framework === 'express') {
      examples.push({
        title: 'Express Router',
        code: `const router = express.Router();

router.get('/', getAll);
router.get('/:id', getById);
router.post('/', create);
router.put('/:id', update);
router.delete('/:id', remove);

app.use('/api/items', router);`,
        description: 'RESTful routing with Express'
      });
    }

    return examples;
  }

  private getMiddlewareExamples(language?: string, framework?: string): any[] {
    const examples: any[] = [];

    if (framework === 'express') {
      examples.push({
        title: 'Express Middleware',
        code: `const authMiddleware = (req, res, next) => {
  const token = req.headers.authorization;
  if (!token) {
    return res.status(401).json({ error: 'No token' });
  }
  // Verify token
  next();
};`,
        description: 'Authentication middleware'
      });
    }

    return examples;
  }

  private getGeneralExamples(
    query: string,
    language?: string,
    framework?: string,
    limit: number = 5
  ): any[] {
    return [
      {
        title: 'General Example',
        code: '// Example code based on your query',
        description: `Example for: ${query}`
      }
    ];
  }
}