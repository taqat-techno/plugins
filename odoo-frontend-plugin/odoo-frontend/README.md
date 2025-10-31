# Odoo Frontend Development Skill v2.0

Advanced Odoo frontend development with modern JavaScript, PWA support, testing frameworks, performance optimization, and comprehensive theme development capabilities.

## 🚀 Features

### Core Capabilities
- **Auto-Detection**: Automatically detects Odoo version (14-19) and maps to correct Bootstrap version
- **Theme Scaffolding**: Generate complete theme modules with proper structure
- **Version-Aware**: Handles differences between Odoo versions (Owl v1/v2, snippet structures)
- **Bootstrap Mapping**: Automatic Bootstrap 4 → 5 class conversion

### Modern Development
- **Progressive Web Apps**: Service Workers, offline support, push notifications
- **TypeScript Support**: Full type safety with TypeScript configurations
- **ES2020+ JavaScript**: Modern patterns including optional chaining, nullish coalescing
- **Web Components**: Custom elements with Shadow DOM
- **Real-time Features**: WebSockets, Server-Sent Events, live collaboration

### Testing & Quality
- **Unit Testing**: Jest framework with Owl component testing
- **E2E Testing**: Cypress for end-to-end scenarios
- **Visual Regression**: BackstopJS for UI consistency
- **Performance Testing**: Lighthouse CI integration
- **Accessibility Testing**: WCAG 2.1 AA compliance checking

### Performance & Optimization
- **Core Web Vitals**: LCP, FID/INP, CLS optimization
- **Resource Optimization**: Critical CSS, code splitting, lazy loading
- **Image Optimization**: WebP/AVIF support, responsive images
- **Caching Strategies**: Service Worker caching, memory caching
- **Build Tools**: Vite configuration, bundle optimization

### Integration & DevOps
- **MCP Integration**: Figma design conversion, Chrome DevTools extraction
- **CI/CD Pipelines**: GitHub Actions workflows
- **Performance Monitoring**: Real-time metrics tracking
- **Error Boundaries**: Robust error handling
- **State Management**: Global store patterns

## Supported Versions

- **Odoo**: 14, 15, 16, 17, 18, 19
- **Bootstrap**: 4.x (Odoo 14-15), 5.1.3 (Odoo 16-19)
- **Owl Framework**: v1 (Odoo 16-17), v2 (Odoo 18-19)

## Quick Start

### 1. Scaffold a New Theme

```
Create a new Odoo theme called "modern" for Odoo 17
```

Claude Code will:
- Detect Odoo version (17.0)
- Map to Bootstrap 5.1.3
- Generate complete theme module structure
- Create primary_variables.scss
- Set up proper asset bundles

### 2. Convert Figma Design

```
Convert this Figma design to Odoo theme: <figma_url>
```

Claude Code will:
- Use Figma MCP to fetch design
- Extract colors and map to o-color-1 through o-color-5
- Convert components to Odoo snippets
- Generate SCSS with theme variables
- Create version-appropriate snippet registration

### 3. Extract from Website

```
Extract styles from https://example.com and convert to Odoo theme
```

Claude Code will:
- Use Chrome DevTools MCP to inspect site
- Extract computed styles
- Map to Bootstrap utilities
- Convert DOM to QWeb templates
- Generate Odoo-compatible code

### 4. Create Custom Snippet

```
Create a hero snippet with image, title, and CTA button
```

Claude Code will:
- Detect Odoo version
- Use correct snippet registration method (17 vs 18/19)
- Generate snippet template
- Add snippet options (layout choices, add item, color picker)
- Include JavaScript if needed

## Common Commands

### Theme Development
- `"scaffold theme <name>"` - Create complete theme module
- `"create snippet <name>"` - Add custom snippet with options
- `"add SCSS variables for colors"` - Generate primary_variables.scss
- `"create public widget for <feature>"` - Generate jQuery widget
- `"create Owl component for <feature>"` - Generate Owl component (version-aware)
- `"create web component <name>"` - Generate custom element

### Progressive Web Apps
- `"make PWA"` - Setup Progressive Web App
- `"add offline support"` - Implement Service Worker caching
- `"enable push notifications"` - Setup push notification system
- `"add background sync"` - Implement offline form submission

### Modern JavaScript
- `"setup TypeScript"` - Configure TypeScript for Odoo
- `"add ES2020 patterns"` - Implement modern JS features
- `"setup code splitting"` - Configure dynamic imports
- `"add error boundaries"` - Implement error handling

### Testing
- `"setup Jest testing"` - Configure unit testing
- `"setup Cypress"` - Configure E2E testing
- `"add visual regression"` - Setup BackstopJS
- `"setup performance testing"` - Configure Lighthouse CI

### Performance
- `"optimize Core Web Vitals"` - Improve LCP, FID, CLS
- `"add lazy loading"` - Implement image lazy loading
- `"extract critical CSS"` - Optimize CSS delivery
- `"setup Vite build"` - Configure modern build tool

### Accessibility
- `"add ARIA labels"` - Implement accessibility attributes
- `"setup keyboard navigation"` - Add keyboard support
- `"check WCAG compliance"` - Run accessibility audit
- `"add screen reader support"` - Optimize for screen readers

### Real-time Features
- `"add WebSocket support"` - Implement real-time updates
- `"setup SSE"` - Configure Server-Sent Events
- `"add live collaboration"` - Implement collaborative features

### Figma Integration
- `"convert Figma <url> to Odoo"` - Full design conversion
- `"extract colors from Figma <url>"` - Color palette only
- `"import Figma component as snippet"` - Single component conversion

### DevTools Integration
- `"extract styles from <url>"` - Style extraction
- `"copy layout from <url>"` - Structure extraction
- `"convert <url> to Bootstrap grid"` - Grid mapping

### Migration
- `"migrate theme from Odoo 17 to 18"` - Version migration
- `"convert Bootstrap 4 classes to 5"` - Class conversion
- `"update snippets for Odoo 18"` - Snippet structure update

## Version-Specific Behavior

### Odoo 17 and Earlier

- Uses simple snippet insertion (no groups)
- Supports Owl v1 components
- jQuery fully available for widgets

### Odoo 18/19

- Requires snippet groups
- Uses Owl v2 (breaking changes from v1)
- Enhanced website builder features

### Bootstrap Versions

- **Odoo 14-15**: Bootstrap 4.x classes (ml-, mr-, text-left, etc.)
- **Odoo 16-19**: Bootstrap 5.1.3 classes (ms-, me-, text-start, etc.)

## File Structure

Generated themes follow this structure:

```
theme_<name>/
├── __init__.py
├── __manifest__.py                    # Module metadata
├── data/
│   └── pages.xml                      # Theme pages
├── views/
│   ├── templates.xml                  # Base templates
│   └── snippets/
│       └── custom_snippets.xml        # Snippet definitions
├── static/
│   └── src/
│       ├── scss/
│       │   ├── primary_variables.scss # Theme colors & fonts
│       │   └── bootstrap_overridden.scss  # Bootstrap overrides
│       ├── js/
│       │   ├── theme.js               # Public widgets
│       │   └── snippets_options.js    # Snippet options JS
│       └── img/
│           └── snippets/              # Snippet thumbnails
└── README.md
```

## Helper Scripts

### Version Detection

```bash
python scripts/version_detector.py <module_path>
```

Outputs:
- Odoo version (e.g., 17.0)
- Bootstrap version (e.g., 5.1.3)
- Owl version (e.g., 2.x)
- Module type (theme/website/custom)
- Snippet groups support

### Bootstrap Mapper

```bash
python scripts/bootstrap_mapper.py ml-3 mr-2 text-left
```

Outputs:
- Converted classes: `ms-3 me-2 text-start`
- Migration notes

### Figma Converter

```bash
python scripts/figma_converter.py <figma_url> <output_dir> [odoo_version]
```

Provides instructions for using Figma MCP.

### DevTools Extractor

```bash
python scripts/devtools_extractor.py <website_url> <output_dir>
```

Provides instructions for using Chrome DevTools MCP.

## MCP Tools

This skill integrates with three MCP tools:

### 1. Figma MCP

Converts Figma designs to HTML with Bootstrap classes:
- Automatic Bootstrap version selection
- Color palette extraction
- Typography mapping
- Component conversion

### 2. Chrome DevTools MCP

Extracts styles from live websites:
- Computed style extraction
- DOM structure analysis
- Bootstrap utility mapping
- QWeb template generation

### 3. File System MCP

Advanced file operations:
- Batch processing
- Multi-module management
- Automated backups

## Best Practices

### Always Detect Version First

Never assume Odoo or Bootstrap version. Always use auto-detection.

### Prefer Bootstrap Utilities

Use Bootstrap classes instead of custom CSS whenever possible for better performance and editor compatibility.

### Server-Side Rendering

Render primary content server-side for SEO. Use Owl/JavaScript for enhancements only.

### Test in Website Builder

Always test your themes and snippets in Odoo's Website Builder edit mode.

### Follow Odoo Patterns

Study core themes in `odoo/addons/theme_*` to understand Odoo's conventions.

## Troubleshooting

### Snippet Not Appearing

**Check:**
1. Odoo version (17 vs 18/19 use different structures)
2. Template ID exists
3. XML syntax is correct
4. Look for errors in Odoo log

### Styles Not Applying

**Check:**
1. SCSS included in correct asset bundle
2. Browser cache cleared
3. Assets regenerated (update module)
4. CSS specificity not conflicting

### JavaScript Errors

**Check:**
1. Import paths correct for Odoo version
2. Widget/component properly registered
3. Owl version matches (v1 in 17, v2 in 18/19)
4. Console for specific errors

## Examples

### Example 1: Complete Theme from Figma

```
User: "Convert this Figma design to an Odoo 17 theme: https://figma.com/file/xyz"

Claude Code will:
1. Detect Odoo 17 → Bootstrap 5.1.3
2. Use Figma MCP with appropriate prompt
3. Extract colors → primary_variables.scss
4. Convert components → snippets (Odoo 17 structure)
5. Generate complete theme module
6. Test installation
```

### Example 2: Add Custom Snippet

```
User: "Create a testimonial carousel snippet for Odoo 18"

Claude Code will:
1. Detect Odoo 18 → needs snippet group
2. Generate carousel HTML with Bootstrap 5.1.3
3. Create snippet with group="custom"
4. Add options (add item, layout choice)
5. Generate JavaScript for carousel functionality
6. Include in website.assets_wysiwyg
```

### Example 3: Migrate Theme

```
User: "Migrate my theme from Odoo 17 to Odoo 18"

Claude Code will:
1. Analyze current theme structure
2. Update snippet registration (add groups)
3. Update Owl components (v1 → v2)
4. Keep Bootstrap 5.1.3 (no change needed)
5. Test all snippets and functionality
6. Generate migration report
```

## 📚 Reference Documentation

Comprehensive guides for advanced topics:

- **[PWA Patterns](reference/pwa_patterns.md)** - Service Workers, offline support, push notifications
- **[Testing Strategies](reference/testing_strategies.md)** - Jest, Cypress, visual regression testing
- **[Performance Optimization](reference/performance_optimization.md)** - Core Web Vitals, resource optimization
- **[Snippet Patterns](reference/snippet_patterns.md)** - Common snippet structures and options
- **[Bootstrap Versions](reference/bootstrap_versions.md)** - Version mapping and migration
- **[Owl Migration](reference/owl_migration.md)** - Owl v1 to v2 migration guide

## Resources

- **Odoo Documentation**: https://www.odoo.com/documentation/
- **Bootstrap 5.1.3 Docs**: https://getbootstrap.com/docs/5.1/
- **Owl Framework**: https://github.com/odoo/owl
- **TypeScript**: https://www.typescriptlang.org/docs/
- **Jest Testing**: https://jestjs.io/docs/
- **Cypress Testing**: https://docs.cypress.io/
- **Web Components**: https://developer.mozilla.org/en-US/docs/Web/Web_Components
- **Helper Scripts**: `scripts/` directory

## License

MIT License - See LICENSE file for details.

## Author

TAQAT Techno - Odoo Development and Consulting

## Support

For issues or questions:
- Check troubleshooting section
- Review reference documentation
- Consult helper script outputs
- Test in clean Odoo environment

## Version

- **v2.0.0** - Added PWA, TypeScript, testing, performance optimization, accessibility, real-time features
- **v1.0.0** - Initial release with full Odoo 14-19 support
