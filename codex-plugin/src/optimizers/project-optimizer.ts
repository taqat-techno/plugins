import fs from 'fs-extra';
import path from 'path';
import glob from 'glob';

export class ProjectOptimizer {
  async suggestRefactoring(
    targetPath: string,
    focus: string[] = ['performance', 'readability', 'maintainability']
  ): Promise<any> {
    const suggestions: any = {
      path: targetPath,
      timestamp: new Date().toISOString(),
      focus: focus,
      refactorings: [],
      priority: {
        high: [],
        medium: [],
        low: []
      },
      estimatedImpact: {},
      implementation: []
    };

    const content = await this.readContent(targetPath);

    for (const area of focus) {
      const areaRefactorings = await this.analyzeForRefactoring(content, area);
      suggestions.refactorings.push(...areaRefactorings);
    }

    // Categorize by priority
    suggestions.refactorings.forEach((refactoring: any) => {
      suggestions.priority[refactoring.priority].push(refactoring);
    });

    // Calculate impact
    suggestions.estimatedImpact = this.calculateImpact(suggestions.refactorings);

    // Generate implementation steps
    suggestions.implementation = this.generateImplementationSteps(suggestions.refactorings);

    return suggestions;
  }

  async optimizeImports(
    targetPath: string,
    style: string = 'auto'
  ): Promise<string> {
    const content = await this.readContent(targetPath);
    const language = this.detectLanguage(targetPath);

    if (language === 'javascript' || language === 'typescript') {
      return this.optimizeJavaScriptImports(content, style);
    } else if (language === 'python') {
      return this.optimizePythonImports(content, style);
    } else if (language === 'java') {
      return this.optimizeJavaImports(content, style);
    }

    return content;
  }

  async analyzeDependencies(
    projectPath: string,
    checkSecurity: boolean = true,
    checkUpdates: boolean = true
  ): Promise<any> {
    const analysis: any = {
      path: projectPath,
      timestamp: new Date().toISOString(),
      dependencies: {
        direct: [],
        dev: [],
        peer: [],
        total: 0
      },
      security: {
        vulnerabilities: [],
        riskLevel: 'low'
      },
      updates: {
        available: [],
        breaking: [],
        patches: []
      },
      unused: [],
      duplicates: [],
      recommendations: []
    };

    // Detect package manager
    const packageManager = await this.detectPackageManager(projectPath);

    if (packageManager === 'npm' || packageManager === 'yarn') {
      await this.analyzeNodeDependencies(projectPath, analysis);
    } else if (packageManager === 'pip') {
      await this.analyzePythonDependencies(projectPath, analysis);
    } else if (packageManager === 'maven' || packageManager === 'gradle') {
      await this.analyzeJavaDependencies(projectPath, analysis);
    }

    if (checkSecurity) {
      analysis.security = await this.checkSecurityVulnerabilities(analysis.dependencies);
    }

    if (checkUpdates) {
      analysis.updates = await this.checkForUpdates(analysis.dependencies);
    }

    // Find unused dependencies
    analysis.unused = await this.findUnusedDependencies(projectPath, analysis.dependencies);

    // Find duplicate dependencies
    analysis.duplicates = this.findDuplicateDependencies(analysis.dependencies);

    // Generate recommendations
    analysis.recommendations = this.generateDependencyRecommendations(analysis);

    return analysis;
  }

  private async readContent(targetPath: string): Promise<string> {
    const stats = await fs.stat(targetPath);

    if (stats.isDirectory()) {
      // Read all relevant files in directory
      const files = glob.sync('**/*.{js,ts,jsx,tsx,py,java}', {
        cwd: targetPath,
        ignore: ['**/node_modules/**', '**/dist/**', '**/build/**']
      });

      let combinedContent = '';
      for (const file of files.slice(0, 10)) { // Limit to first 10 files
        combinedContent += await fs.readFile(path.join(targetPath, file), 'utf-8') + '\n';
      }
      return combinedContent;
    }

    return fs.readFile(targetPath, 'utf-8');
  }

  private detectLanguage(filePath: string): string {
    const ext = path.extname(filePath).toLowerCase();
    const languageMap: Record<string, string> = {
      '.js': 'javascript',
      '.jsx': 'javascript',
      '.ts': 'typescript',
      '.tsx': 'typescript',
      '.py': 'python',
      '.java': 'java',
      '.rb': 'ruby',
      '.go': 'go',
      '.rs': 'rust',
      '.php': 'php'
    };
    return languageMap[ext] || 'unknown';
  }

  private async analyzeForRefactoring(content: string, focus: string): Promise<any[]> {
    const refactorings: any[] = [];

    switch (focus) {
      case 'performance':
        refactorings.push(...this.analyzePerformanceRefactoring(content));
        break;
      case 'readability':
        refactorings.push(...this.analyzeReadabilityRefactoring(content));
        break;
      case 'maintainability':
        refactorings.push(...this.analyzeMaintainabilityRefactoring(content));
        break;
      case 'security':
        refactorings.push(...this.analyzeSecurityRefactoring(content));
        break;
      case 'dry':
        refactorings.push(...this.analyzeDryRefactoring(content));
        break;
    }

    return refactorings;
  }

  private analyzePerformanceRefactoring(content: string): any[] {
    const refactorings: any[] = [];

    // Check for nested loops
    if (/for.*\{[\s\S]*?for.*\{/i.test(content)) {
      refactorings.push({
        type: 'nested-loops',
        description: 'Replace nested loops with more efficient algorithms',
        priority: 'high',
        location: 'Multiple locations',
        suggestion: 'Consider using Map/Set for lookups or array methods like reduce'
      });
    }

    // Check for synchronous file operations
    if (/readFileSync|writeFileSync/g.test(content)) {
      refactorings.push({
        type: 'sync-io',
        description: 'Replace synchronous I/O with async operations',
        priority: 'high',
        location: 'File operations',
        suggestion: 'Use async/await with readFile/writeFile'
      });
    }

    // Check for inefficient array operations
    if (/\.forEach.*\.push/g.test(content)) {
      refactorings.push({
        type: 'array-operations',
        description: 'Replace forEach+push with map',
        priority: 'medium',
        location: 'Array transformations',
        suggestion: 'Use .map() for array transformations'
      });
    }

    // Check for repeated DOM queries
    if (/document\.querySelector.*document\.querySelector/g.test(content)) {
      refactorings.push({
        type: 'dom-queries',
        description: 'Cache DOM queries',
        priority: 'medium',
        location: 'DOM manipulation',
        suggestion: 'Store DOM elements in variables'
      });
    }

    return refactorings;
  }

  private analyzeReadabilityRefactoring(content: string): any[] {
    const refactorings: any[] = [];

    // Check for long lines
    const lines = content.split('\n');
    const longLines = lines.filter(line => line.length > 120);
    if (longLines.length > 10) {
      refactorings.push({
        type: 'long-lines',
        description: 'Break long lines for better readability',
        priority: 'low',
        location: `${longLines.length} lines`,
        suggestion: 'Break lines at logical points, use intermediate variables'
      });
    }

    // Check for complex conditionals
    if (/if.*&&.*&&.*\|\|/g.test(content)) {
      refactorings.push({
        type: 'complex-conditionals',
        description: 'Simplify complex conditional expressions',
        priority: 'medium',
        location: 'Conditional statements',
        suggestion: 'Extract to named boolean variables or functions'
      });
    }

    // Check for magic numbers
    if (/[^a-zA-Z0-9_](?:86400|3600|1024|255|100|60)[^a-zA-Z0-9_]/g.test(content)) {
      refactorings.push({
        type: 'magic-numbers',
        description: 'Replace magic numbers with named constants',
        priority: 'medium',
        location: 'Numeric literals',
        suggestion: 'Define constants with descriptive names'
      });
    }

    // Check for unclear variable names
    if (/\b[a-z]\b\s*=/g.test(content)) {
      refactorings.push({
        type: 'variable-names',
        description: 'Use descriptive variable names',
        priority: 'medium',
        location: 'Single-letter variables',
        suggestion: 'Replace with descriptive names'
      });
    }

    return refactorings;
  }

  private analyzeMaintainabilityRefactoring(content: string): any[] {
    const refactorings: any[] = [];

    // Check for large functions
    const functionPattern = /function[\s\S]{500,}?\n\}/g;
    if (functionPattern.test(content)) {
      refactorings.push({
        type: 'large-functions',
        description: 'Split large functions into smaller ones',
        priority: 'high',
        location: 'Large function bodies',
        suggestion: 'Extract logical sections into separate functions'
      });
    }

    // Check for deep nesting
    if (/\{[\s\S]*?\{[\s\S]*?\{[\s\S]*?\{[\s\S]*?\{/g.test(content)) {
      refactorings.push({
        type: 'deep-nesting',
        description: 'Reduce nesting depth',
        priority: 'medium',
        location: 'Deeply nested blocks',
        suggestion: 'Use early returns, extract functions, or flatten logic'
      });
    }

    // Check for missing error handling
    if (/async.*function(?![\s\S]*try[\s\S]*catch)/g.test(content)) {
      refactorings.push({
        type: 'error-handling',
        description: 'Add error handling to async functions',
        priority: 'high',
        location: 'Async functions',
        suggestion: 'Wrap async operations in try-catch blocks'
      });
    }

    // Check for code duplication indicators
    if (this.detectDuplication(content)) {
      refactorings.push({
        type: 'duplication',
        description: 'Extract duplicate code',
        priority: 'medium',
        location: 'Multiple locations',
        suggestion: 'Create shared functions or modules'
      });
    }

    return refactorings;
  }

  private analyzeSecurityRefactoring(content: string): any[] {
    const refactorings: any[] = [];

    // Check for eval usage
    if (/eval\s*\(/g.test(content)) {
      refactorings.push({
        type: 'eval-usage',
        description: 'Remove eval() usage',
        priority: 'high',
        location: 'eval() calls',
        suggestion: 'Use JSON.parse or safer alternatives'
      });
    }

    // Check for SQL injection risks
    if (/query.*\+|query.*\$\{/g.test(content)) {
      refactorings.push({
        type: 'sql-injection',
        description: 'Use parameterized queries',
        priority: 'high',
        location: 'SQL queries',
        suggestion: 'Use prepared statements or query builders'
      });
    }

    // Check for hardcoded secrets
    if (/password\s*=\s*["'][^"']+["']|api[_-]?key\s*=\s*["'][^"']+["']/gi.test(content)) {
      refactorings.push({
        type: 'hardcoded-secrets',
        description: 'Move secrets to environment variables',
        priority: 'high',
        location: 'Hardcoded credentials',
        suggestion: 'Use environment variables or secure vaults'
      });
    }

    return refactorings;
  }

  private analyzeDryRefactoring(content: string): any[] {
    const refactorings: any[] = [];

    // Find similar code blocks
    const codeBlocks = this.extractCodeBlocks(content);
    const duplicates = this.findSimilarBlocks(codeBlocks);

    if (duplicates.length > 0) {
      refactorings.push({
        type: 'duplicate-blocks',
        description: 'Extract duplicate code blocks',
        priority: 'medium',
        location: `${duplicates.length} duplicate blocks`,
        suggestion: 'Create reusable functions or components'
      });
    }

    return refactorings;
  }

  private detectDuplication(content: string): boolean {
    // Simple duplication detection
    const lines = content.split('\n');
    const chunks: string[] = [];

    for (let i = 0; i < lines.length - 3; i++) {
      chunks.push(lines.slice(i, i + 3).join('\n'));
    }

    const duplicates = chunks.filter((chunk, index) =>
      chunks.indexOf(chunk) !== index && chunk.trim().length > 30
    );

    return duplicates.length > 5;
  }

  private extractCodeBlocks(content: string): string[] {
    const blocks: string[] = [];
    const blockPattern = /\{[^{}]*\}/g;
    let match;

    while ((match = blockPattern.exec(content)) !== null) {
      if (match[0].length > 50) {
        blocks.push(match[0]);
      }
    }

    return blocks;
  }

  private findSimilarBlocks(blocks: string[]): string[] {
    const similar: string[] = [];

    for (let i = 0; i < blocks.length; i++) {
      for (let j = i + 1; j < blocks.length; j++) {
        if (this.calculateSimilarity(blocks[i], blocks[j]) > 0.8) {
          similar.push(blocks[i]);
          break;
        }
      }
    }

    return similar;
  }

  private calculateSimilarity(str1: string, str2: string): number {
    const longer = str1.length > str2.length ? str1 : str2;
    const shorter = str1.length > str2.length ? str2 : str1;

    if (longer.length === 0) return 1.0;

    const distance = this.levenshteinDistance(longer, shorter);
    return (longer.length - distance) / longer.length;
  }

  private levenshteinDistance(str1: string, str2: string): number {
    const matrix: number[][] = [];

    for (let i = 0; i <= str2.length; i++) {
      matrix[i] = [i];
    }

    for (let j = 0; j <= str1.length; j++) {
      matrix[0][j] = j;
    }

    for (let i = 1; i <= str2.length; i++) {
      for (let j = 1; j <= str1.length; j++) {
        if (str2.charAt(i - 1) === str1.charAt(j - 1)) {
          matrix[i][j] = matrix[i - 1][j - 1];
        } else {
          matrix[i][j] = Math.min(
            matrix[i - 1][j - 1] + 1,
            matrix[i][j - 1] + 1,
            matrix[i - 1][j] + 1
          );
        }
      }
    }

    return matrix[str2.length][str1.length];
  }

  private calculateImpact(refactorings: any[]): any {
    return {
      performance: refactorings.filter(r => r.type.includes('performance')).length * 20,
      readability: refactorings.filter(r => r.type.includes('readability')).length * 15,
      maintainability: refactorings.filter(r => r.type.includes('maintainability')).length * 25,
      overall: refactorings.length * 18
    };
  }

  private generateImplementationSteps(refactorings: any[]): string[] {
    const steps: string[] = [];

    // Sort by priority
    const highPriority = refactorings.filter(r => r.priority === 'high');
    const mediumPriority = refactorings.filter(r => r.priority === 'medium');
    const lowPriority = refactorings.filter(r => r.priority === 'low');

    if (highPriority.length > 0) {
      steps.push('1. Address high-priority refactorings first:');
      highPriority.forEach((r, i) => {
        steps.push(`   ${i + 1}.${i + 1} ${r.description}`);
      });
    }

    if (mediumPriority.length > 0) {
      steps.push('2. Then tackle medium-priority items:');
      mediumPriority.forEach((r, i) => {
        steps.push(`   2.${i + 1} ${r.description}`);
      });
    }

    if (lowPriority.length > 0) {
      steps.push('3. Finally, improve low-priority areas:');
      lowPriority.forEach((r, i) => {
        steps.push(`   3.${i + 1} ${r.description}`);
      });
    }

    steps.push('4. Run tests after each refactoring');
    steps.push('5. Commit changes incrementally');

    return steps;
  }

  private optimizeJavaScriptImports(content: string, style: string): string {
    const lines = content.split('\n');
    const imports: string[] = [];
    const otherLines: string[] = [];

    // Separate imports from other code
    for (const line of lines) {
      if (/^import\s+|^const\s+.*=\s*require/.test(line)) {
        imports.push(line);
      } else {
        otherLines.push(line);
      }
    }

    // Sort imports based on style
    let sortedImports: string[] = [];

    switch (style) {
      case 'grouped':
        sortedImports = this.groupImports(imports);
        break;
      case 'alphabetical':
        sortedImports = imports.sort();
        break;
      default: // auto
        sortedImports = this.autoOrganizeImports(imports);
        break;
    }

    return [...sortedImports, '', ...otherLines].join('\n');
  }

  private groupImports(imports: string[]): string[] {
    const external: string[] = [];
    const internal: string[] = [];
    const relative: string[] = [];

    for (const imp of imports) {
      if (/from\s+['"]\./.test(imp)) {
        relative.push(imp);
      } else if (/from\s+['"]@/.test(imp)) {
        internal.push(imp);
      } else {
        external.push(imp);
      }
    }

    return [
      ...external.sort(),
      '',
      ...internal.sort(),
      '',
      ...relative.sort()
    ].filter(line => line !== '' || imports.length > 0);
  }

  private autoOrganizeImports(imports: string[]): string[] {
    // Group by type and sort alphabetically within groups
    return this.groupImports(imports);
  }

  private optimizePythonImports(content: string, style: string): string {
    const lines = content.split('\n');
    const imports: string[] = [];
    const otherLines: string[] = [];

    // Separate imports
    for (const line of lines) {
      if (/^import\s+|^from\s+/.test(line)) {
        imports.push(line);
      } else {
        otherLines.push(line);
      }
    }

    // Organize imports (PEP 8 style)
    const stdlib: string[] = [];
    const thirdParty: string[] = [];
    const local: string[] = [];

    for (const imp of imports) {
      const module = imp.match(/(?:from\s+|import\s+)(\S+)/)?.[1] || '';

      if (this.isPythonStdlib(module)) {
        stdlib.push(imp);
      } else if (module.startsWith('.')) {
        local.push(imp);
      } else {
        thirdParty.push(imp);
      }
    }

    return [
      ...stdlib.sort(),
      '',
      ...thirdParty.sort(),
      '',
      ...local.sort(),
      '',
      ...otherLines
    ].join('\n');
  }

  private optimizeJavaImports(content: string, style: string): string {
    const lines = content.split('\n');
    const imports: string[] = [];
    const otherLines: string[] = [];

    for (const line of lines) {
      if (/^import\s+/.test(line)) {
        imports.push(line);
      } else {
        otherLines.push(line);
      }
    }

    // Group Java imports
    const javaImports: string[] = [];
    const javaxImports: string[] = [];
    const orgImports: string[] = [];
    const comImports: string[] = [];
    const otherImports: string[] = [];

    for (const imp of imports) {
      if (imp.startsWith('import java.')) {
        javaImports.push(imp);
      } else if (imp.startsWith('import javax.')) {
        javaxImports.push(imp);
      } else if (imp.startsWith('import org.')) {
        orgImports.push(imp);
      } else if (imp.startsWith('import com.')) {
        comImports.push(imp);
      } else {
        otherImports.push(imp);
      }
    }

    return [
      ...javaImports.sort(),
      ...javaxImports.sort(),
      '',
      ...orgImports.sort(),
      ...comImports.sort(),
      ...otherImports.sort(),
      '',
      ...otherLines
    ].join('\n');
  }

  private isPythonStdlib(module: string): boolean {
    const stdlibModules = [
      'os', 'sys', 'json', 'datetime', 'time', 'math', 'random',
      'collections', 'itertools', 'functools', 're', 'typing',
      'pathlib', 'urllib', 'http', 'socket', 'threading'
    ];

    return stdlibModules.includes(module.split('.')[0]);
  }

  private async detectPackageManager(projectPath: string): Promise<string> {
    if (await fs.pathExists(path.join(projectPath, 'package-lock.json'))) {
      return 'npm';
    }
    if (await fs.pathExists(path.join(projectPath, 'yarn.lock'))) {
      return 'yarn';
    }
    if (await fs.pathExists(path.join(projectPath, 'requirements.txt')) ||
        await fs.pathExists(path.join(projectPath, 'setup.py'))) {
      return 'pip';
    }
    if (await fs.pathExists(path.join(projectPath, 'pom.xml'))) {
      return 'maven';
    }
    if (await fs.pathExists(path.join(projectPath, 'build.gradle'))) {
      return 'gradle';
    }
    return 'unknown';
  }

  private async analyzeNodeDependencies(projectPath: string, analysis: any): Promise<void> {
    const packageJsonPath = path.join(projectPath, 'package.json');

    if (await fs.pathExists(packageJsonPath)) {
      const packageJson = await fs.readJson(packageJsonPath);

      analysis.dependencies.direct = Object.keys(packageJson.dependencies || {});
      analysis.dependencies.dev = Object.keys(packageJson.devDependencies || {});
      analysis.dependencies.peer = Object.keys(packageJson.peerDependencies || {});
      analysis.dependencies.total =
        analysis.dependencies.direct.length +
        analysis.dependencies.dev.length +
        analysis.dependencies.peer.length;
    }
  }

  private async analyzePythonDependencies(projectPath: string, analysis: any): Promise<void> {
    const requirementsPath = path.join(projectPath, 'requirements.txt');

    if (await fs.pathExists(requirementsPath)) {
      const requirements = await fs.readFile(requirementsPath, 'utf-8');
      const lines = requirements.split('\n').filter(line => line.trim() && !line.startsWith('#'));

      analysis.dependencies.direct = lines.map(line => line.split('==')[0].split('>=')[0].split('~=')[0]);
      analysis.dependencies.total = analysis.dependencies.direct.length;
    }
  }

  private async analyzeJavaDependencies(projectPath: string, analysis: any): Promise<void> {
    // Simplified Java dependency analysis
    analysis.dependencies.direct = ['java.base'];
    analysis.dependencies.total = 1;
  }

  private async checkSecurityVulnerabilities(dependencies: any): Promise<any> {
    // Simulated security check
    const knownVulnerabilities: Record<string, string> = {
      'lodash': 'CVE-2021-23337: Command injection vulnerability in versions < 4.17.21',
      'axios': 'CVE-2021-3749: Inefficient regular expression in versions < 0.21.2',
      'minimist': 'CVE-2021-44906: Prototype pollution in versions < 1.2.6'
    };

    const vulnerabilities: any[] = [];
    let riskLevel = 'low';

    for (const dep of [...dependencies.direct, ...dependencies.dev]) {
      if (knownVulnerabilities[dep]) {
        vulnerabilities.push({
          package: dep,
          vulnerability: knownVulnerabilities[dep],
          severity: 'high'
        });
        riskLevel = 'high';
      }
    }

    return { vulnerabilities, riskLevel };
  }

  private async checkForUpdates(dependencies: any): Promise<any> {
    // Simulated update check
    const updates = {
      available: dependencies.direct.slice(0, 3).map((dep: string) => ({
        package: dep,
        current: '1.0.0',
        latest: '2.0.0',
        type: 'major'
      })),
      breaking: [],
      patches: []
    };

    return updates;
  }

  private async findUnusedDependencies(projectPath: string, dependencies: any): Promise<string[]> {
    // Simplified unused dependency detection
    const unused: string[] = [];
    const sourceFiles = glob.sync('**/*.{js,ts,jsx,tsx}', {
      cwd: projectPath,
      ignore: ['**/node_modules/**']
    });

    for (const dep of dependencies.direct) {
      let isUsed = false;

      for (const file of sourceFiles) {
        const content = await fs.readFile(path.join(projectPath, file), 'utf-8');
        if (content.includes(dep)) {
          isUsed = true;
          break;
        }
      }

      if (!isUsed) {
        unused.push(dep);
      }
    }

    return unused;
  }

  private findDuplicateDependencies(dependencies: any): string[] {
    // Find packages that appear in multiple categories
    const all = [
      ...dependencies.direct,
      ...dependencies.dev,
      ...dependencies.peer
    ];

    const counts: Record<string, number> = {};
    for (const dep of all) {
      counts[dep] = (counts[dep] || 0) + 1;
    }

    return Object.keys(counts).filter(dep => counts[dep] > 1);
  }

  private generateDependencyRecommendations(analysis: any): string[] {
    const recommendations: string[] = [];

    if (analysis.security.vulnerabilities.length > 0) {
      recommendations.push(`Fix ${analysis.security.vulnerabilities.length} security vulnerabilities immediately`);
    }

    if (analysis.updates.available.length > 0) {
      recommendations.push(`Update ${analysis.updates.available.length} packages to latest versions`);
    }

    if (analysis.unused.length > 0) {
      recommendations.push(`Remove ${analysis.unused.length} unused dependencies`);
    }

    if (analysis.duplicates.length > 0) {
      recommendations.push(`Resolve ${analysis.duplicates.length} duplicate dependencies`);
    }

    if (analysis.dependencies.total > 100) {
      recommendations.push('Consider reducing dependency count for better maintainability');
    }

    return recommendations;
  }
}