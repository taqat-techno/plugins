import fs from 'fs-extra';
import path from 'path';
import glob from 'glob';

export class CodeAnalyzer {
  async analyze(targetPath: string, language?: string, depth: string = 'standard'): Promise<any> {
    const stats = await fs.stat(targetPath);
    const isDirectory = stats.isDirectory();

    const analysis: any = {
      path: targetPath,
      type: isDirectory ? 'directory' : 'file',
      language: language || this.detectLanguage(targetPath),
      timestamp: new Date().toISOString(),
      depth,
      metrics: {},
      structure: {},
      patterns: [],
      issues: [],
      suggestions: []
    };

    if (isDirectory) {
      analysis.structure = await this.analyzeDirectoryStructure(targetPath);
      analysis.metrics = await this.analyzeProjectMetrics(targetPath, depth);
    } else {
      const content = await fs.readFile(targetPath, 'utf-8');
      analysis.metrics = this.analyzeFileMetrics(content, analysis.language);
      analysis.patterns = this.detectPatterns(content, analysis.language);
    }

    if (depth === 'deep') {
      analysis.dependencies = await this.analyzeDependencies(targetPath);
      analysis.complexity = await this.analyzeComplexity(targetPath);
      analysis.documentation = await this.analyzeDocumentation(targetPath);
    }

    // Add quality score
    analysis.qualityScore = this.calculateQualityScore(analysis);

    // Add recommendations
    analysis.recommendations = this.generateRecommendations(analysis);

    return analysis;
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
      '.cpp': 'cpp',
      '.c': 'c',
      '.cs': 'csharp',
      '.rb': 'ruby',
      '.go': 'go',
      '.rs': 'rust',
      '.php': 'php',
      '.swift': 'swift',
      '.kt': 'kotlin',
      '.scala': 'scala',
      '.r': 'r',
      '.m': 'matlab',
      '.dart': 'dart',
      '.lua': 'lua',
      '.pl': 'perl',
      '.sh': 'bash',
      '.sql': 'sql',
      '.html': 'html',
      '.css': 'css',
      '.scss': 'scss',
      '.xml': 'xml',
      '.json': 'json',
      '.yaml': 'yaml',
      '.yml': 'yaml',
      '.md': 'markdown'
    };
    return languageMap[ext] || 'unknown';
  }

  private async analyzeDirectoryStructure(dirPath: string): Promise<any> {
    const structure: any = {
      totalFiles: 0,
      totalDirectories: 0,
      fileTypes: {},
      depth: 0,
      tree: []
    };

    const files = glob.sync('**/*', {
      cwd: dirPath,
      nodir: false,
      dot: true,
      ignore: ['**/node_modules/**', '**/.git/**', '**/dist/**', '**/build/**']
    });

    for (const file of files) {
      const fullPath = path.join(dirPath, file);
      const stats = await fs.stat(fullPath);

      if (stats.isDirectory()) {
        structure.totalDirectories++;
      } else {
        structure.totalFiles++;
        const ext = path.extname(file);
        structure.fileTypes[ext] = (structure.fileTypes[ext] || 0) + 1;
      }

      const depth = file.split(path.sep).length;
      structure.depth = Math.max(structure.depth, depth);
    }

    return structure;
  }

  private analyzeFileMetrics(content: string, language: string): any {
    const lines = content.split('\n');
    const metrics: any = {
      lines: {
        total: lines.length,
        code: 0,
        comment: 0,
        blank: 0
      },
      complexity: {
        cyclomatic: 0,
        cognitive: 0
      },
      functions: [],
      classes: [],
      imports: []
    };

    // Basic line counting
    for (const line of lines) {
      const trimmed = line.trim();
      if (trimmed === '') {
        metrics.lines.blank++;
      } else if (this.isComment(trimmed, language)) {
        metrics.lines.comment++;
      } else {
        metrics.lines.code++;
      }
    }

    // Language-specific analysis
    if (language === 'javascript' || language === 'typescript') {
      metrics.functions = this.extractJavaScriptFunctions(content);
      metrics.classes = this.extractJavaScriptClasses(content);
      metrics.imports = this.extractJavaScriptImports(content);
    } else if (language === 'python') {
      metrics.functions = this.extractPythonFunctions(content);
      metrics.classes = this.extractPythonClasses(content);
      metrics.imports = this.extractPythonImports(content);
    }

    // Calculate cyclomatic complexity (simplified)
    metrics.complexity.cyclomatic = this.calculateCyclomaticComplexity(content, language);

    return metrics;
  }

  private isComment(line: string, language: string): boolean {
    const commentPatterns: Record<string, RegExp[]> = {
      javascript: [/^\/\//, /^\/\*/, /^\*/],
      typescript: [/^\/\//, /^\/\*/, /^\*/],
      python: [/^#/, /^""/, /^'''/],
      java: [/^\/\//, /^\/\*/, /^\*/],
      cpp: [/^\/\//, /^\/\*/, /^\*/],
      c: [/^\/\//, /^\/\*/, /^\*/],
      ruby: [/^#/],
      go: [/^\/\//, /^\/\*/]
    };

    const patterns = commentPatterns[language] || [/^\/\//, /^#/];
    return patterns.some(pattern => pattern.test(line));
  }

  private extractJavaScriptFunctions(content: string): string[] {
    const functionPattern = /(?:function\s+(\w+)|const\s+(\w+)\s*=\s*(?:async\s*)?\(|(\w+)\s*:\s*(?:async\s*)?\()/g;
    const matches = [];
    let match;
    while ((match = functionPattern.exec(content)) !== null) {
      matches.push(match[1] || match[2] || match[3]);
    }
    return matches.filter(Boolean);
  }

  private extractJavaScriptClasses(content: string): string[] {
    const classPattern = /class\s+(\w+)/g;
    const matches = [];
    let match;
    while ((match = classPattern.exec(content)) !== null) {
      matches.push(match[1]);
    }
    return matches;
  }

  private extractJavaScriptImports(content: string): string[] {
    const importPattern = /import\s+.+\s+from\s+['"](.+)['"]/g;
    const matches = [];
    let match;
    while ((match = importPattern.exec(content)) !== null) {
      matches.push(match[1]);
    }
    return matches;
  }

  private extractPythonFunctions(content: string): string[] {
    const functionPattern = /def\s+(\w+)\s*\(/g;
    const matches = [];
    let match;
    while ((match = functionPattern.exec(content)) !== null) {
      matches.push(match[1]);
    }
    return matches;
  }

  private extractPythonClasses(content: string): string[] {
    const classPattern = /class\s+(\w+)/g;
    const matches = [];
    let match;
    while ((match = classPattern.exec(content)) !== null) {
      matches.push(match[1]);
    }
    return matches;
  }

  private extractPythonImports(content: string): string[] {
    const importPattern = /(?:from\s+(\S+)\s+import|import\s+(\S+))/g;
    const matches = [];
    let match;
    while ((match = importPattern.exec(content)) !== null) {
      matches.push(match[1] || match[2]);
    }
    return matches;
  }

  private calculateCyclomaticComplexity(content: string, language: string): number {
    // Simplified cyclomatic complexity calculation
    const decisionPoints = [
      /\bif\b/g,
      /\belse\s+if\b/g,
      /\belif\b/g,
      /\bfor\b/g,
      /\bwhile\b/g,
      /\bcase\b/g,
      /\bcatch\b/g,
      /\&\&/g,
      /\|\|/g,
      /\?.*:/g
    ];

    let complexity = 1; // Base complexity
    for (const pattern of decisionPoints) {
      const matches = content.match(pattern);
      if (matches) {
        complexity += matches.length;
      }
    }

    return complexity;
  }

  private detectPatterns(content: string, language: string): string[] {
    const patterns = [];

    // Detect common design patterns
    if (/class\s+\w+Factory/.test(content)) patterns.push('Factory Pattern');
    if (/class\s+\w+Singleton/.test(content)) patterns.push('Singleton Pattern');
    if (/class\s+\w+Observer/.test(content)) patterns.push('Observer Pattern');
    if (/class\s+\w+Strategy/.test(content)) patterns.push('Strategy Pattern');
    if (/class\s+\w+Decorator/.test(content)) patterns.push('Decorator Pattern');

    // Detect potential issues
    if (/console\.\w+/g.test(content) && language === 'javascript') patterns.push('Console statements found');
    if (/TODO|FIXME|HACK/g.test(content)) patterns.push('TODO/FIXME comments found');
    if (/password|secret|key|token/gi.test(content)) patterns.push('Potential sensitive data');

    return patterns;
  }

  private async analyzeDependencies(targetPath: string): Promise<any> {
    const dependencies: any = {
      direct: [],
      dev: [],
      peer: [],
      vulnerabilities: []
    };

    // Check for package.json (Node.js)
    const packageJsonPath = path.join(targetPath, 'package.json');
    if (await fs.pathExists(packageJsonPath)) {
      const packageJson = await fs.readJson(packageJsonPath);
      dependencies.direct = Object.keys(packageJson.dependencies || {});
      dependencies.dev = Object.keys(packageJson.devDependencies || {});
      dependencies.peer = Object.keys(packageJson.peerDependencies || {});
    }

    // Check for requirements.txt (Python)
    const requirementsPath = path.join(targetPath, 'requirements.txt');
    if (await fs.pathExists(requirementsPath)) {
      const requirements = await fs.readFile(requirementsPath, 'utf-8');
      dependencies.direct = requirements.split('\n').filter(line => line.trim() && !line.startsWith('#'));
    }

    return dependencies;
  }

  private async analyzeComplexity(targetPath: string): Promise<any> {
    return {
      overall: 'moderate',
      hotspots: [],
      refactoringCandidates: []
    };
  }

  private async analyzeDocumentation(targetPath: string): Promise<any> {
    return {
      coverage: 0,
      quality: 'needs improvement',
      missingDocs: []
    };
  }

  private async analyzeProjectMetrics(dirPath: string, depth: string): Promise<any> {
    const metrics: any = {
      totalLines: 0,
      totalFiles: 0,
      languages: {},
      largestFiles: [],
      complexity: {
        average: 0,
        highest: 0
      }
    };

    const files = glob.sync('**/*.{js,ts,jsx,tsx,py,java,cpp,c,cs,rb,go,rs,php}', {
      cwd: dirPath,
      ignore: ['**/node_modules/**', '**/.git/**', '**/dist/**', '**/build/**']
    });

    for (const file of files) {
      const fullPath = path.join(dirPath, file);
      const content = await fs.readFile(fullPath, 'utf-8');
      const lines = content.split('\n').length;

      metrics.totalFiles++;
      metrics.totalLines += lines;

      const lang = this.detectLanguage(fullPath);
      metrics.languages[lang] = (metrics.languages[lang] || 0) + 1;

      if (depth === 'deep' && metrics.largestFiles.length < 10) {
        metrics.largestFiles.push({
          path: file,
          lines,
          size: (await fs.stat(fullPath)).size
        });
        metrics.largestFiles.sort((a, b) => b.lines - a.lines);
        metrics.largestFiles = metrics.largestFiles.slice(0, 10);
      }
    }

    return metrics;
  }

  private calculateQualityScore(analysis: any): number {
    let score = 100;

    // Deduct points for issues
    if (analysis.patterns) {
      if (analysis.patterns.includes('Console statements found')) score -= 5;
      if (analysis.patterns.includes('TODO/FIXME comments found')) score -= 3;
      if (analysis.patterns.includes('Potential sensitive data')) score -= 10;
    }

    // Deduct for complexity
    if (analysis.metrics?.complexity?.cyclomatic > 10) score -= 10;
    if (analysis.metrics?.complexity?.cyclomatic > 20) score -= 10;

    // Deduct for poor documentation
    if (analysis.documentation?.coverage < 50) score -= 10;

    return Math.max(0, score);
  }

  private generateRecommendations(analysis: any): string[] {
    const recommendations = [];

    if (analysis.metrics?.complexity?.cyclomatic > 10) {
      recommendations.push('Consider refactoring complex functions to reduce cyclomatic complexity');
    }

    if (analysis.patterns?.includes('Console statements found')) {
      recommendations.push('Remove console statements before production deployment');
    }

    if (analysis.patterns?.includes('Potential sensitive data')) {
      recommendations.push('Review and secure potential sensitive data in the code');
    }

    if (analysis.documentation?.coverage < 50) {
      recommendations.push('Improve documentation coverage for better maintainability');
    }

    if (analysis.metrics?.lines?.comment < analysis.metrics?.lines?.code * 0.1) {
      recommendations.push('Add more comments to explain complex logic');
    }

    return recommendations;
  }
}