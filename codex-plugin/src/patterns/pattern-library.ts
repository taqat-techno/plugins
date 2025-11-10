import fs from 'fs-extra';
import path from 'path';
import glob from 'glob';

export class PatternLibrary {
  private patterns = {
    designPatterns: {
      singleton: /class\s+\w*Singleton\w*|getInstance\s*\(|private\s+static\s+\w+\s*:/gi,
      factory: /class\s+\w*Factory\w*|create\w+\s*\(|factory\s*\(/gi,
      observer: /class\s+\w*Observer\w*|subscribe\s*\(|notify\w*\s*\(|emit\s*\(/gi,
      strategy: /class\s+\w*Strategy\w*|execute\s*\(|algorithm\s*\(/gi,
      decorator: /class\s+\w*Decorator\w*|wrapper|enhance\w*\s*\(/gi,
      adapter: /class\s+\w*Adapter\w*|adapt\s*\(/gi,
      facade: /class\s+\w*Facade\w*|simplify\s*\(/gi,
      proxy: /class\s+\w*Proxy\w*|forward\s*\(/gi,
      mvc: /\b(Model|View|Controller)\b/gi,
      mvvm: /\b(Model|View|ViewModel)\b/gi,
      repository: /class\s+\w*Repository\w*|getAll|findBy|save|delete/gi,
      dependency_injection: /inject\s*\(|@Injectable|constructor\s*\([^)]+\)/gi
    },
    antiPatterns: {
      god_object: { test: (content: string) => this.detectGodObject(content) },
      spaghetti_code: { test: (content: string) => this.detectSpaghettiCode(content) },
      copy_paste: { test: (content: string) => this.detectCopyPaste(content) },
      magic_numbers: /\b\d{2,}\b(?!\s*[;,)])|(?<!\w)(?:3\.14|2\.71|1\.41|0\.577)/g,
      long_method: { test: (content: string) => this.detectLongMethod(content) },
      feature_envy: { test: (content: string) => this.detectFeatureEnvy(content) },
      dead_code: /^\s*\/\/.*$|\/\*[\s\S]*?\*\/|if\s*\(\s*false\s*\)/gm,
      hardcoded_values: /["'](https?:\/\/|localhost|127\.0\.0\.1|root|admin|password|secret)["']/gi
    },
    codeSmells: {
      long_parameter_list: /\([^)]{100,}\)/g,
      duplicate_code: { test: (content: string) => this.detectDuplicateCode(content) },
      large_class: { test: (content: string) => this.detectLargeClass(content) },
      comments: /\/\/\s*(TODO|FIXME|HACK|XXX|BUG|OPTIMIZE)/gi,
      nested_conditionals: { test: (content: string) => this.detectDeepNesting(content) },
      refused_bequest: { test: (content: string) => this.detectRefusedBequest(content) },
      shotgun_surgery: { test: (content: string) => this.detectShotgunSurgery(content) }
    },
    architecturalPatterns: {
      microservices: /\b(service|micro|api|endpoint)\b/gi,
      monolithic: /\b(monolith|single)\b/gi,
      layered: /\b(layer|tier|presentation|business|data)\b/gi,
      eventDriven: /\b(event|emit|listen|subscribe|publish|bus)\b/gi,
      serverless: /\b(lambda|function|serverless|faas)\b/gi,
      hexagonal: /\b(port|adapter|domain|infrastructure)\b/gi,
      clean_architecture: /\b(usecase|entity|gateway|presenter)\b/gi,
      cqrs: /\b(command|query|handler|bus)\b/gi,
      event_sourcing: /\b(event|aggregate|projection|snapshot)\b/gi
    },
    securityPatterns: {
      sql_injection: /(\$|:)\w+|string\s*\+|concat.*sql/gi,
      xss_vulnerable: /(innerHTML|document\.write|eval)\s*\(/gi,
      hardcoded_secrets: /\b(api[_-]?key|secret|password|token)\s*=\s*["'][^"']+["']/gi,
      weak_crypto: /\b(md5|sha1|des|rc4)\b/gi,
      insecure_random: /Math\.random\(\)/g,
      path_traversal: /\.\.[\/\\]/g
    },
    performancePatterns: {
      n_plus_one: { test: (content: string) => this.detectNPlusOne(content) },
      memory_leak: /setInterval|setTimeout(?!.*clear)/g,
      blocking_io: /readFileSync|writeFileSync|execSync/g,
      inefficient_loops: /for.*in\s+|forEach.*await/g,
      unnecessary_renders: /setState.*loop|render.*forEach/g
    }
  };

  async findPatterns(targetPath: string, specificPatterns?: string[]): Promise<any> {
    const results: any = {
      path: targetPath,
      timestamp: new Date().toISOString(),
      patternsFound: {
        design: [],
        antiPatterns: [],
        codeSmells: [],
        architectural: [],
        security: [],
        performance: []
      },
      statistics: {
        totalPatterns: 0,
        byCategory: {}
      },
      recommendations: []
    };

    const files = await this.getFilesToAnalyze(targetPath);

    for (const file of files) {
      const content = await fs.readFile(file, 'utf-8');
      await this.analyzeContent(content, file, results, specificPatterns);
    }

    // Calculate statistics
    results.statistics.totalPatterns = Object.values(results.patternsFound)
      .flat()
      .length;

    for (const [category, patterns] of Object.entries(results.patternsFound)) {
      results.statistics.byCategory[category] = (patterns as any[]).length;
    }

    // Generate recommendations
    results.recommendations = this.generatePatternRecommendations(results);

    return results;
  }

  private async getFilesToAnalyze(targetPath: string): Promise<string[]> {
    const stats = await fs.stat(targetPath);

    if (!stats.isDirectory()) {
      return [targetPath];
    }

    return glob.sync('**/*.{js,ts,jsx,tsx,py,java,cpp,cs,rb,go,php}', {
      cwd: targetPath,
      absolute: true,
      ignore: ['**/node_modules/**', '**/.git/**', '**/dist/**', '**/build/**']
    });
  }

  private async analyzeContent(
    content: string,
    filePath: string,
    results: any,
    specificPatterns?: string[]
  ): Promise<void> {
    const fileName = path.basename(filePath);

    // Check design patterns
    for (const [pattern, regex] of Object.entries(this.patterns.designPatterns)) {
      if (specificPatterns && !specificPatterns.includes(pattern)) continue;

      if (regex instanceof RegExp && regex.test(content)) {
        results.patternsFound.design.push({
          pattern,
          file: fileName,
          confidence: 'high'
        });
      }
    }

    // Check anti-patterns
    for (const [pattern, detector] of Object.entries(this.patterns.antiPatterns)) {
      if (specificPatterns && !specificPatterns.includes(pattern)) continue;

      let found = false;
      if (typeof detector === 'object' && 'test' in detector) {
        found = detector.test(content);
      } else if (detector instanceof RegExp) {
        found = detector.test(content);
      }

      if (found) {
        results.patternsFound.antiPatterns.push({
          pattern,
          file: fileName,
          severity: this.getAntiPatternSeverity(pattern)
        });
      }
    }

    // Check code smells
    for (const [smell, detector] of Object.entries(this.patterns.codeSmells)) {
      if (typeof detector === 'object' && 'test' in detector) {
        if (detector.test(content)) {
          results.patternsFound.codeSmells.push({
            smell,
            file: fileName,
            severity: 'medium'
          });
        }
      } else if (detector instanceof RegExp && detector.test(content)) {
        const matches = content.match(detector) || [];
        if (matches.length > 0) {
          results.patternsFound.codeSmells.push({
            smell,
            file: fileName,
            occurrences: matches.length,
            severity: this.getCodeSmellSeverity(smell, matches.length)
          });
        }
      }
    }

    // Check security patterns
    for (const [vuln, pattern] of Object.entries(this.patterns.securityPatterns)) {
      if (pattern.test(content)) {
        results.patternsFound.security.push({
          vulnerability: vuln,
          file: fileName,
          severity: this.getSecuritySeverity(vuln),
          recommendation: this.getSecurityRecommendation(vuln)
        });
      }
    }

    // Check performance patterns
    for (const [issue, detector] of Object.entries(this.patterns.performancePatterns)) {
      let found = false;
      if (typeof detector === 'object' && 'test' in detector) {
        found = detector.test(content);
      } else if (detector instanceof RegExp) {
        found = detector.test(content);
      }

      if (found) {
        results.patternsFound.performance.push({
          issue,
          file: fileName,
          impact: this.getPerformanceImpact(issue),
          solution: this.getPerformanceSolution(issue)
        });
      }
    }
  }

  private detectGodObject(content: string): boolean {
    const lines = content.split('\n').length;
    const methods = content.match(/(?:function|def|public|private|protected)\s+\w+/g) || [];
    const properties = content.match(/(?:this\.|self\.)\w+/g) || [];

    return lines > 500 && methods.length > 20 && properties.length > 30;
  }

  private detectSpaghettiCode(content: string): boolean {
    const gotos = content.match(/goto\s+\w+/g) || [];
    const deepNesting = this.detectDeepNesting(content);
    const longLines = content.split('\n').filter(line => line.length > 120).length;

    return gotos.length > 0 || deepNesting || longLines > 50;
  }

  private detectCopyPaste(content: string): boolean {
    const lines = content.split('\n');
    const chunks: string[] = [];

    for (let i = 0; i < lines.length - 5; i++) {
      chunks.push(lines.slice(i, i + 5).join('\n'));
    }

    const duplicates = chunks.filter((chunk, index) =>
      chunks.indexOf(chunk) !== index && chunk.trim().length > 50
    );

    return duplicates.length > 3;
  }

  private detectLongMethod(content: string): boolean {
    const methodPattern = /(?:function|def|public|private|protected)\s+\w+[\s\S]*?(?:\n\}|\n\s{0,4}def|\n\s{0,4}function)/g;
    const methods = content.match(methodPattern) || [];

    return methods.some(method => method.split('\n').length > 50);
  }

  private detectFeatureEnvy(content: string): boolean {
    const otherObjectCalls = content.match(/\w+\.\w+\.\w+/g) || [];
    const ownMethodCalls = content.match(/this\.\w+|self\.\w+/g) || [];

    return otherObjectCalls.length > ownMethodCalls.length * 2;
  }

  private detectDuplicateCode(content: string): boolean {
    const functions = content.match(/function[\s\S]*?\}/g) || [];
    const similar = functions.filter((func, index) => {
      return functions.some((other, otherIndex) =>
        index !== otherIndex && this.calculateSimilarity(func, other) > 0.8
      );
    });

    return similar.length > 2;
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

  private detectLargeClass(content: string): boolean {
    const lines = content.split('\n').length;
    const methods = content.match(/(?:function|def|public|private|protected)\s+\w+/g) || [];

    return lines > 500 || methods.length > 20;
  }

  private detectDeepNesting(content: string): boolean {
    const lines = content.split('\n');
    let maxDepth = 0;
    let currentDepth = 0;

    for (const line of lines) {
      const openBraces = (line.match(/\{/g) || []).length;
      const closeBraces = (line.match(/\}/g) || []).length;
      currentDepth += openBraces - closeBraces;
      maxDepth = Math.max(maxDepth, currentDepth);
    }

    return maxDepth > 5;
  }

  private detectRefusedBequest(content: string): boolean {
    const overrides = content.match(/@override|super\.\w+\(\)/g) || [];
    const emptyOverrides = content.match(/@override[\s\S]*?\{\s*\}/g) || [];

    return emptyOverrides.length > overrides.length / 2;
  }

  private detectShotgunSurgery(content: string): boolean {
    const publicMethods = content.match(/public\s+\w+/g) || [];
    const dependencies = content.match(/import|require/g) || [];

    return publicMethods.length > 10 && dependencies.length > 15;
  }

  private detectNPlusOne(content: string): boolean {
    const loops = content.match(/for|while|map|forEach/g) || [];
    const queries = content.match(/query|select|find|fetch|get/gi) || [];

    // Simple heuristic: loops containing queries
    return loops.length > 0 && queries.length > loops.length;
  }

  private getAntiPatternSeverity(pattern: string): string {
    const severities: Record<string, string> = {
      god_object: 'high',
      spaghetti_code: 'high',
      copy_paste: 'medium',
      magic_numbers: 'low',
      long_method: 'medium',
      feature_envy: 'medium',
      dead_code: 'low',
      hardcoded_values: 'high'
    };
    return severities[pattern] || 'medium';
  }

  private getCodeSmellSeverity(smell: string, count: number): string {
    if (count > 10) return 'high';
    if (count > 5) return 'medium';
    return 'low';
  }

  private getSecuritySeverity(vulnerability: string): string {
    const severities: Record<string, string> = {
      sql_injection: 'critical',
      xss_vulnerable: 'high',
      hardcoded_secrets: 'critical',
      weak_crypto: 'high',
      insecure_random: 'medium',
      path_traversal: 'high'
    };
    return severities[vulnerability] || 'medium';
  }

  private getSecurityRecommendation(vulnerability: string): string {
    const recommendations: Record<string, string> = {
      sql_injection: 'Use parameterized queries or prepared statements',
      xss_vulnerable: 'Sanitize user input and use safe DOM manipulation methods',
      hardcoded_secrets: 'Use environment variables or secure key management',
      weak_crypto: 'Use strong encryption algorithms (AES, RSA, SHA-256)',
      insecure_random: 'Use crypto.randomBytes() or similar secure random generators',
      path_traversal: 'Validate and sanitize file paths'
    };
    return recommendations[vulnerability] || 'Review and fix the security issue';
  }

  private getPerformanceImpact(issue: string): string {
    const impacts: Record<string, string> = {
      n_plus_one: 'high',
      memory_leak: 'high',
      blocking_io: 'medium',
      inefficient_loops: 'medium',
      unnecessary_renders: 'medium'
    };
    return impacts[issue] || 'medium';
  }

  private getPerformanceSolution(issue: string): string {
    const solutions: Record<string, string> = {
      n_plus_one: 'Use eager loading or batch queries',
      memory_leak: 'Clear intervals/timeouts and remove event listeners',
      blocking_io: 'Use async/await or callbacks for I/O operations',
      inefficient_loops: 'Use optimized loop constructs or array methods',
      unnecessary_renders: 'Implement memoization or shouldComponentUpdate'
    };
    return solutions[issue] || 'Optimize the performance bottleneck';
  }

  private generatePatternRecommendations(results: any): string[] {
    const recommendations: string[] = [];

    if (results.patternsFound.antiPatterns.length > 0) {
      recommendations.push('Refactor code to eliminate anti-patterns');
    }

    if (results.patternsFound.security.length > 0) {
      recommendations.push('Address security vulnerabilities immediately');
    }

    if (results.patternsFound.codeSmells.length > 5) {
      recommendations.push('Consider code refactoring to reduce code smells');
    }

    if (results.patternsFound.performance.length > 0) {
      recommendations.push('Optimize performance bottlenecks');
    }

    if (results.patternsFound.design.length === 0) {
      recommendations.push('Consider implementing design patterns for better structure');
    }

    return recommendations;
  }
}