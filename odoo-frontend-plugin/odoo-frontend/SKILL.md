---
name: odoo-frontend
description: "Advanced Odoo frontend development with comprehensive theme development, PWA support, modern JavaScript/TypeScript, testing frameworks, performance optimization, accessibility compliance, and real-time features. Features complete $o-website-values-palettes reference, theme mirror model architecture, publicWidget patterns with editableMode handling, and MCP integration. Supports Odoo 14-19 with auto-detection."
allowed-tools: [Read, Write, Edit, Bash, Grep, Glob, WebFetch]
metadata:
  version: "3.0.0"
  odoo-versions: "14,15,16,17,18,19"
  bootstrap-versions: "4.x,5.1.3"
  javascript-features: ["ES2020+", "TypeScript", "Owl v1/v2", "Web Components", "publicWidget"]
  testing-frameworks: ["Jest", "Cypress", "BackstopJS"]
  performance-tools: ["Core Web Vitals", "Lighthouse", "Vite"]
  accessibility: ["WCAG 2.1 AA", "ARIA", "Screen Readers"]
  real-time: ["WebSockets", "SSE", "Push Notifications"]
  mcp-tools: ["figma", "chrome-devtools", "filesystem"]
  theme-features: ["o-website-values-palettes", "mirror-models", "snippet-groups", "color-palettes"]
  author: "TAQAT Techno"
  license: "MIT"
---

# Odoo Frontend Development Skill v3.0

## Overview

This skill provides advanced Odoo frontend development capabilities with:
- **Theme Development**: Complete `$o-website-values-palettes` reference, color semantics, theme mirror models
- **Auto-detection**: Automatically detect Odoo version and map to correct Bootstrap version
- **publicWidget Framework**: Comprehensive patterns with `editableMode` handling for website builder
- **Progressive Web Apps**: Service Workers, offline support, push notifications
- **Modern JavaScript**: TypeScript, ES2020+, Web Components, Owl v1/v2 patterns
- **Testing Frameworks**: Jest, Cypress, visual regression testing
- **Performance Optimization**: Core Web Vitals, resource hints, critical CSS
- **Accessibility**: WCAG 2.1 AA compliance, ARIA patterns, keyboard navigation
- **Real-time Features**: WebSockets, Server-Sent Events, live collaboration
- **MCP Integration**: Figma design conversion and Chrome DevTools style extraction
- **Theme Scaffolding**: Complete theme module generation with proper structure
- **Version-Aware**: Handle differences between Odoo 14-19 (Bootstrap 4/5, Owl v1/v2, Snippet structures)
- **DevOps Ready**: CI/CD pipelines, Vite builds, automated testing

## CRITICAL RULES

1. **NEVER edit core Odoo** in `odoo/` or `odoo/addons/` directories
2. **No inline JS/CSS** - Create separate `.js` and `.scss` files
3. **JS modules**: Use `/** @odoo-module **/` annotation
4. **Website themes**: Use `publicWidget` framework ONLY (not Owl or vanilla JS)
5. **Bootstrap**: Use v5.1.3 classes for Odoo 16+ (never Tailwind)
6. **Module naming**: Use `snake_case` convention
7. **Translations**: Wrap static labels in JS arrays/constants with `_t()` AT DEFINITION TIME (not via runtime wrappers). Static XML strings are auto-translated.

## Auto-Detection Workflow

### Step 1: Detect Odoo Version

When starting any frontend task, first detect the Odoo version:

```python
# Use the version detector script
python scripts/version_detector.py <module_path>
```

The version detector will:
1. Look for `__manifest__.py` or `__openerp__.py`
2. Parse the version field
3. If not found, detect from parent directory (e.g., `odoo17/`)
4. Return:
   - Odoo version (e.g., "17.0")
   - Bootstrap version (e.g., "5.1.3")
   - Owl version (e.g., "2.x" or None)
   - Module type (theme, website, custom)

### Step 2: Bootstrap Version Mapping

**Automatic Bootstrap Version Selection:**
- Odoo 14-15: Bootstrap 4.5.0
- Odoo 16-19: Bootstrap 5.1.3

### Step 3: Owl Version Detection

**JavaScript Framework Selection:**
- Odoo 14-15: Owl experimental or jQuery only
- Odoo 16-17: Owl v1
- Odoo 18-19: Owl v2 (with breaking changes)

### Step 4: Snippet Structure Detection

**Snippet Registration Method:**
- Odoo 14-17: Simple snippet insertion without groups
- Odoo 18-19: Snippet groups required (`snippet_structure` with groups)

## Complete Website Theme Variables System

### $o-website-values-palettes - Full Reference

Themes define comprehensive configuration presets. Based on analysis of 27+ standard Odoo themes:

```scss
$o-website-values-palettes: (
    (
        // === CORE CONFIGURATION ===
        'color-palettes-name': 'your-theme-palette',  // Required: Links to color palette

        // === HEADER & NAVIGATION ===
        'header-template': 'default',           // Layout style
        'header-font-size': 1rem,               // Navigation text size
        'header-links-style': 'default',        // Navigation link styling
        'hamburger-position': 'right',          // Mobile menu position
        'logo-height': 3rem,                    // Logo size
        'fixed-logo-height': 2rem,              // Logo size when header is fixed

        // === TYPOGRAPHY ===
        'font': 'Source Sans Pro',              // Body text font
        'headings-font': 'Spartan',             // Heading font (h1-h6)
        'navbar-font': 'Inter',                 // Navigation font
        'buttons-font': 'Montserrat',           // Button text font
        'headings-line-height': 1.1,            // Heading line spacing

        // === BUTTONS ===
        'btn-padding-y': .45rem,                // Vertical button padding
        'btn-padding-x': 1.35rem,               // Horizontal button padding
        'btn-padding-y-sm': .3rem,              // Small button vertical padding
        'btn-padding-x-sm': .9rem,              // Small button horizontal padding
        'btn-padding-y-lg': .6rem,              // Large button vertical padding
        'btn-padding-x-lg': 1.8rem,             // Large button horizontal padding
        'btn-border-radius': 10rem,             // Button corner rounding (10rem = pill)
        'btn-border-radius-sm': 10rem,          // Small button rounding
        'btn-border-radius-lg': 10rem,          // Large button rounding
        'btn-border-width': 2px,                // Button border thickness
        'btn-font-size': 1.2rem,                // Button text size
        'btn-ripple': true,                     // Material design ripple effect
        'btn-primary-flat': true,               // Flat primary button style
        'btn-secondary-flat': true,             // Flat secondary button style
        'btn-secondary-outline': true,          // Outline secondary button style

        // === INPUT FIELDS ===
        'input-padding-y': .45rem,              // Vertical input padding
        'input-padding-y-sm': .3rem,            // Small input vertical padding
        'input-padding-y-lg': .6rem,            // Large input vertical padding
        'input-border-radius': .125rem,         // Input corner rounding
        'input-border-radius-sm': .125rem,      // Small input rounding
        'input-border-radius-lg': .125rem,      // Large input rounding

        // === FOOTER ===
        'footer-template': 'headline',          // Footer layout style
        'footer-effect': 'slideout_slide_hover', // Footer animation effect
        'footer-scrolltop': true,               // Show scroll-to-top button

        // === LINKS ===
        'link-underline': 'never',              // Link underline behavior

        // === LAYOUT ===
        'layout': 'boxed',                      // Overall page layout
        'menu-border-radius': 0,                // Menu corner rounding
    ),
);
```

### Variable Options Reference

**Header Template Options:**
- `'default'` - Standard horizontal header
- `'vertical'` - Sidebar-style navigation
- `'hamburger'` - Mobile-first hamburger menu
- `'search'` - Search-focused header layout
- `'boxed'` - Contained header layout
- `'sales_four'` - Sales-optimized layout
- `'custom-theme'` - Theme-specific custom layout

**Header Links Style Options:**
- `'default'` - Standard link styling
- `'pills'` - Pill-shaped link backgrounds
- `'flat'` - Flat, borderless links
- `'fill'` - Filled background links
- `'border-bottom'` - Bottom border on hover

**Footer Template Options:**
- `'default'` - Standard footer layout
- `'headline'` - Large headline focus
- `'centered'` - Center-aligned content
- `'descriptive'` - Detailed description layout
- `'contact'` - Contact information focus
- `'call_to_action'` - CTA-focused footer
- `'minimalist'` - Clean, minimal footer
- `'vertical'` - Vertical layout footer
- `'links'` - Link-heavy footer
- `'sales_four'` - Sales conversion optimized

### Theme Color Palettes (o-color Semantic Structure)

**Color Semantic Meanings:**
- **o-color-1** = Primary brand color (main brand identity)
- **o-color-2** = Secondary brand color (supporting brand color)
- **o-color-3** = Light color (light backgrounds, light mode base)
- **o-color-4** = White/body base color (main content background)
- **o-color-5** = Dark color/font base (text color, dark mode considerations)

```scss
$o-theme-color-palettes: map-merge($o-theme-color-palettes, (
    'my-theme-palette': (
        'o-color-1': #007bff,      // Primary brand color
        'o-color-2': #6c757d,      // Secondary brand color
        'o-color-3': #f8f9fa,      // Light backgrounds
        'o-color-4': #ffffff,      // White/body base
        'o-color-5': #343a40,      // Dark text/dark mode base
        'menu': 1,                  // Which color for menu (1-5)
        'footer': 4,                // Which color for footer (1-5)
        'copyright': 5,             // Which color for copyright (1-5)
    ),
));
```

### Font Configuration System

```scss
$o-theme-font-configs: map-merge($o-theme-font-configs, (
    'Inter': (
        'family': ('Inter', sans-serif),
        'url': 'Inter:wght@300;400;500;600;700&display=swap',
        'properties': (
            'base': (
                'font-size-base': 1rem,
                'line-height-base': 1.6,
            ),
        )
    ),
    'Montserrat': (
        'family': ('Montserrat', sans-serif),
        'url': 'Montserrat:300,300i,400,400i,700,700i',
    ),
));
```

### Typography Hierarchy

```scss
// Common heading multipliers
$o-theme-h1-font-size-multiplier: (64 / 16);  // ~4rem
$o-theme-h2-font-size-multiplier: (48 / 16);  // ~3rem
$o-theme-h3-font-size-multiplier: (36 / 16);  // ~2.25rem
$o-theme-h4-font-size-multiplier: (28 / 16);  // ~1.75rem
$o-theme-h5-font-size-multiplier: (24 / 16);  // ~1.5rem
$o-theme-h6-font-size-multiplier: (21 / 16);  // ~1.3125rem

// Font weights
$o-theme-headings-font-weight: 700;   // Bold headings
$o-theme-font-weight-normal: 400;     // Regular body text
$o-theme-font-weight-light: 300;      // Light text
```

## Theme Page Creation Standard

### Individual Page Files Pattern (Recommended)

Create individual page files instead of a single `pages.xml`:
```
theme_name/
├── data/
│   ├── home.xml          # Homepage template + page
│   ├── about.xml         # About page template + page
│   ├── contact.xml       # Contact page (inherits website.contactus)
│   ├── services.xml      # Services page template + page
│   └── menu.xml          # Menu configuration
└── views/
    └── templates.xml     # Shared templates and layout
```

### Homepage (Inherits website.homepage)
```xml
<!-- data/home.xml -->
<template id="view_home" inherit_id="website.homepage" name="Home">
    <xpath expr="//div[@id='wrap']" position="replace">
        <div id="wrap" class="oe_structure">
            <!-- Homepage content here -->
        </div>
    </xpath>
</template>
```

### Contact Page (Inherits website.contactus)
```xml
<!-- data/contact.xml -->
<template id="view_contact" inherit_id="website.contactus" name="Contact">
    <xpath expr="//h1" position="replace">
        <h1>Get in Touch</h1>
    </xpath>
</template>
```

### Custom Pages (theme.website.page)
```xml
<!-- data/about.xml -->
<template id="view_about" name="About">
    <t t-call="website.layout">
        <div id="wrap" class="oe_structure">
            <section class="s_title pt96 pb48">
                <div class="container">
                    <h1>About Us</h1>
                </div>
            </section>
        </div>
    </t>
</template>

<record id="page_about" model="theme.website.page">
    <field name="view_id" ref="view_about"/>
    <field name="is_published" eval="True"/>
    <field name="url">/about</field>
    <field name="name">About</field>
</record>
```

## Theme Mirror Model Architecture

### How Themes Install to Pages

```
Theme Module XML
    ↓
theme.ir.ui.view (Template View)
    ↓
theme.website.page (Template Page)
    ↓ (Theme Installation)
    ↓
ir.ui.view (Actual View with website_id)
    ↓
website.page (Actual Page with website_id)
```

### Key Points
- Theme modules contain `theme.*` models (templates)
- On installation, these convert to actual models with `website_id`
- Each website gets independent copies, enabling theme reuse
- `website_id` assignment happens at view creation level

## Theme Scaffolding Commands

### Command: Scaffold Complete Theme Module

**Trigger**: User asks to "create theme", "scaffold theme", "generate theme module"

**Workflow**:

1. **Detect Context**
   ```bash
   # Determine current Odoo version
   cd <project_path>
   python -c "import sys; sys.path.insert(0, 'helpers'); from version_detector import detect_version; print(detect_version('.'))"
   ```

2. **Create Module Structure**
   ```
   theme_<name>/
   ├── __init__.py
   ├── __manifest__.py
   ├── data/
   │   └── pages.xml
   ├── views/
   │   ├── templates.xml
   │   └── snippets/
   │       └── custom_snippets.xml
   ├── static/
   │   └── src/
   │       ├── scss/
   │       │   ├── primary_variables.scss
   │       │   └── bootstrap_overridden.scss
   │       ├── js/
   │       │   └── theme.js
   │       └── img/
   └── README.md
   ```

3. **Generate `__manifest__.py`**
   ```python
   {
       'name': 'Theme <Name>',
       'version': '<odoo_version>.1.0.0',
       'category': 'Website/Theme',
       'author': 'Your Company',
       'depends': ['website'],
       'data': [
           'views/templates.xml',
           'views/snippets/custom_snippets.xml',
           'data/pages.xml',
       ],
       'assets': {
           'web._assets_primary_variables': [
               'theme_<name>/static/src/scss/primary_variables.scss',
           ],
           'web._assets_frontend_helpers': [
               'theme_<name>/static/src/scss/bootstrap_overridden.scss',
           ],
           'web.assets_frontend': [
               'theme_<name>/static/src/js/theme.js',
           ],
       },
       'installable': True,
       'auto_install': False,
       'application': False,
       'license': 'LGPL-3',
   }
   ```

4. **Generate `primary_variables.scss`**
   ```scss
   // Theme Primary Variables
   // Override Odoo's default variables here

   // Color Palette (o-color-1 through o-color-5)
   $o-color-1: #3498db !default;
   $o-color-2: #2ecc71 !default;
   $o-color-3: #e74c3c !default;
   $o-color-4: #f39c12 !default;
   $o-color-5: #9b59b6 !default;

   // Website Values Palette
   $o-website-values-palettes: (
       (
           'color-palettes-name': 'theme-<name>-palette',
           // Typography
           'font': 'Inter',
           'headings-font': 'Inter',
           'navbar-font': 'Inter',
           'buttons-font': 'Inter',
           // Header
           'header-template': 'default',
           'logo-height': 3rem,
           // Buttons
           'btn-border-radius': 0.25rem,
           'btn-padding-y': 0.45rem,
           'btn-padding-x': 1.35rem,
       )
   );
   ```

5. **Generate Initial Template**
   ```xml
   <?xml version="1.0" encoding="utf-8"?>
   <odoo>
       <!-- Base template inheritance -->
       <template id="layout" inherit_id="website.layout">
           <xpath expr="//head" position="inside">
               <meta name="theme-name" content="<Name>"/>
           </xpath>
       </template>
   </odoo>
   ```

### Command: Create Snippet (Version-Aware)

**Trigger**: User asks to "create snippet", "add custom snippet"

**Workflow**:

1. **Detect Odoo Version** (determines registration method)

2. **For Odoo 17 and Earlier:**
   ```xml
   <!-- Snippet Template -->
   <template id="s_<snippet_name>" name="<Snippet Name>">
       <section class="s_<snippet_name>" data-name="<Snippet Name>">
           <div class="container">
               <!-- Content here -->
           </div>
       </section>
   </template>

   <!-- Snippet Registration (Odoo 17) -->
   <template id="s_<snippet_name>_insert" inherit_id="website.snippets">
       <xpath expr="//div[@id='snippet_effect']//t[@t-snippet][last()]" position="after">
           <t t-snippet="theme_<name>.s_<snippet_name>"
              string="<Snippet Name>"
              t-thumbnail="/theme_<name>/static/img/snippets/<snippet_name>.svg"/>
       </xpath>
   </template>
   ```

3. **For Odoo 18/19:**
   ```xml
   <!-- Snippet Template -->
   <template id="s_<snippet_name>" name="<Snippet Name>">
       <section class="s_<snippet_name>" data-name="<Snippet Name>">
           <div class="container">
               <!-- Content here -->
           </div>
       </section>
   </template>

   <!-- Snippet Group (if custom group needed) -->
   <template id="snippet_group_custom" inherit_id="website.snippets">
       <xpath expr="//div[@id='snippet_groups']" position="inside">
           <t snippet-group="custom"
              t-snippet="website.s_snippet_group"
              string="Custom Snippets"/>
       </xpath>
   </template>

   <!-- Snippet Registration (Odoo 18/19) -->
   <template id="s_<snippet_name>_insert" inherit_id="website.snippets">
       <xpath expr="//div[@id='snippet_structure']/*[1]" position="before">
           <t t-snippet="theme_<name>.s_<snippet_name>"
              string="<Snippet Name>"
              group="custom"
              t-thumbnail="/theme_<name>/static/img/snippets/<snippet_name>.svg"/>
       </xpath>
   </template>
   ```

4. **Generate Snippet Options** (if needed)
   ```xml
   <template id="s_<snippet_name>_options" inherit_id="website.snippet_options">
       <xpath expr="." position="inside">
           <div data-selector=".s_<snippet_name>">
               <!-- Layout Options -->
               <we-select string="Layout">
                   <we-button data-select-class="">Default</we-button>
                   <we-button data-select-class="s_<snippet_name>_alt">Alternate</we-button>
               </we-select>

               <!-- Add Item Button -->
               <we-row string="Items">
                   <we-button data-add-item="true"
                              data-no-preview="true"
                              class="o_we_bg_brand_primary">Add Item</we-button>
               </we-row>

               <!-- Color Picker -->
               <we-colorpicker string="Background Color"
                               data-css-property="background-color"/>
           </div>
       </xpath>
   </template>
   ```

5. **Generate JavaScript for Options** (if dynamic behavior needed)
   ```javascript
   /** @odoo-module **/

   import options from "@web_editor/js/editor/snippets.options";

   options.registry.<SnippetName> = options.Class.extend({
       /**
        * Add item to snippet
        */
       addItem: function(previewMode, widgetValue, params) {
           let $lastItem = this.$target.find('.snippet-item').last();
           if ($lastItem.length) {
               $lastItem.clone().appendTo(this.$target.find('.snippet-container'));
           }
       },
   });
   ```

   **Include in manifest assets**:
   ```python
   'assets': {
       'website.assets_wysiwyg': [
           'theme_<name>/static/src/js/snippets_options.js',
       ],
   }
   ```

## Figma Integration Workflow

### Command: Convert Figma Design to Odoo Theme

**Trigger**: User provides Figma URL or asks to "convert Figma to Odoo", "import Figma design"

**Prerequisites**: Figma MCP must be available

**Workflow**:

1. **Use Figma MCP with Version-Specific Prompt**
   ```
   Convert this Figma design to HTML for Odoo <version> website theme with these requirements:
   - Use Bootstrap v<bootstrap_version> classes (not Tailwind)
   - Apply proper Odoo theme structure with sections and containers
   - Include responsive classes (col-sm-*, col-md-*, col-lg-*)
   - Use semantic HTML5 elements (header, nav, main, section, article)
   - Add data attributes for Odoo website builder compatibility
   - Map colors to CSS custom properties for theme variables
   - Include accessibility attributes (aria-labels, alt text)
   ```

2. **Extract Color Palette**
   ```
   Extract the color palette from this Figma design and map to CSS custom properties using the o-color-1 through o-color-5 naming convention for Odoo themes.
   ```

3. **Convert HTML to QWeb Template**
   - Wrap in `<template>` tags
   - Add `t-name` attribute
   - Add data attributes for Odoo editor
   - Convert to section-based structure

4. **Generate SCSS from Figma Colors**
   ```python
   python scripts/figma_converter.py <figma_url> <output_dir> <odoo_version>
   ```

5. **Create Snippet from Figma Component**
   - Use converted HTML as snippet content
   - Add proper Odoo structure
   - Register snippet based on version (17 vs 18/19)
   - Generate options if interactive

### Figma MCP Prompts Reference

**Basic HTML + Bootstrap:**
```
Generate this Figma selection as HTML with Bootstrap v<version> classes instead of React and Tailwind. Use Odoo-compatible structure with proper semantic HTML5 elements.
```

**Color Extraction:**
```
Extract colors as CSS custom properties for Odoo theme
```

**Typography Extraction:**
```
Convert this Figma text styling to Bootstrap v<version> typography classes and CSS custom properties. Map font families to Google Fonts configuration for Odoo theme integration.
```

**Layout Extraction:**
```
Convert this Figma layout to Bootstrap v<version> grid system and utility classes. Use proper container, row, col-* structure with responsive breakpoints.
```

## Chrome DevTools Integration Workflow

### Command: Extract Styles from Live Website

**Trigger**: User provides website URL or asks to "extract from website", "copy styles from site"

**Prerequisites**: Chrome DevTools MCP must be available

**Workflow**:

1. **Connect to DevTools MCP**
   - Open URL in Chrome DevTools MCP
   - Select element(s) to extract

2. **Extract Computed Styles**
   ```python
   python scripts/devtools_extractor.py <url> <output_dir>
   ```

3. **Convert to Odoo SCSS**
   - Map CSS properties to SCSS variables
   - Convert colors to Odoo theme variables (o-color-*)
   - Use Bootstrap variables where applicable

4. **Map to Bootstrap Utilities**
   - Identify equivalent Bootstrap classes
   - Replace custom CSS with utilities where possible
   - Generate suggestions for class-based approach

5. **Convert DOM to QWeb**
   - Extract HTML structure
   - Add Odoo-specific attributes
   - Wrap in proper template structure
   - Add Bootstrap grid structure

6. **Generate Complete Theme Code**
   - SCSS file with extracted styles
   - QWeb template with structure
   - Bootstrap class suggestions
   - Snippet registration XML

## JavaScript Development

### Public Widget Pattern (publicWidget - REQUIRED for Themes)

**IMPORTANT**: For website themes, ALWAYS use publicWidget framework - NOT Owl or vanilla JS.

**Use for**: Website interactions, theme functionality, form handling, animations

**Complete Structure with editableMode**:
```javascript
/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.MyWidget = publicWidget.Widget.extend({
    selector: '.my-selector',
    disabledInEditableMode: false,  // Allow in website builder

    events: {
        'click .button': '_onClick',
        'change input': '_onChange',
        'submit form': '_onSubmit',
    },

    /**
     * Lifecycle: Called when widget starts
     * CRITICAL: Check editableMode for website builder compatibility
     */
    start: function () {
        // IMPORTANT: Only run animations/interactions in read mode
        if (!this.editableMode) {
            this._initializeAnimation();
            this._bindExternalEvents();
        }
        return this._super.apply(this, arguments);
    },

    /**
     * Initialize animations (only in read mode)
     */
    _initializeAnimation: function () {
        // Animation code that should NOT run in edit mode
        this.$el.addClass('animated');
    },

    /**
     * Bind events outside the widget element
     */
    _bindExternalEvents: function () {
        $(window).on('scroll.myWidget', this._onScroll.bind(this));
        $(window).on('resize.myWidget', this._onResize.bind(this));
    },

    /**
     * Click handler
     */
    _onClick: function (ev) {
        ev.preventDefault();
        // Don't run in edit mode
        if (this.editableMode) return;
        // Handler logic
    },

    /**
     * Scroll handler
     */
    _onScroll: function () {
        // Throttle scroll events for performance
    },

    /**
     * CRITICAL: Clean up event listeners to prevent memory leaks
     */
    destroy: function () {
        $(window).off('.myWidget');  // Remove namespaced events
        this._super.apply(this, arguments);
    },
});

export default publicWidget.registry.MyWidget;
```

**Key publicWidget Points:**
1. **ALWAYS check `this.editableMode`** before running animations/interactions
2. Use `disabledInEditableMode: false` to make widgets work in website builder
3. **ALWAYS clean up** event listeners in `destroy()` method
4. **NEVER use Owl or vanilla JS** for website themes - publicWidget only
5. Use namespaced events (`.myWidget`) for easy cleanup

**Include in Manifest**:
```python
'assets': {
    'web.assets_frontend': [
        'module_name/static/src/js/my_widget.js',
    ],
}
```

### Owl Component Pattern (Modern, Reactive)

**Use for**: Complex interactive UIs, reactive state management, component composition

**Odoo 17 (Owl v1)**:
```javascript
/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";

class MyComponent extends Component {
    setup() {
        this.state = useState({
            items: [],
            loading: false,
        });
    }

    async willStart() {
        await this.loadData();
    }

    async loadData() {
        this.state.loading = true;
        // Fetch data via RPC
        const data = await this.rpc('/my/route');
        this.state.items = data.items;
        this.state.loading = false;
    }

    onItemClick(item) {
        console.log('Clicked:', item);
    }
}

MyComponent.template = "module_name.MyComponentTemplate";

registry.category("public_components").add("MyComponent", MyComponent);

export default MyComponent;
```

**Odoo 18/19 (Owl v2 - Note differences)**:
```javascript
/** @odoo-module **/

import { Component, useState } from "@odoo/owl";

class MyComponent extends Component {
    static template = "module_name.MyComponentTemplate";
    static props = {
        // Define props with validation
        title: { type: String, optional: true },
        items: { type: Array },
    };

    setup() {
        this.state = useState({
            selectedId: null,
        });
    }

    // Owl v2 uses static template property
}

export default MyComponent;
```

**XML Template**:
```xml
<template id="MyComponentTemplate" name="My Component">
    <div class="my-component">
        <h3 t-if="props.title"><t t-esc="props.title"/></h3>
        <ul>
            <li t-foreach="props.items" t-as="item" t-key="item.id">
                <t t-esc="item.name"/>
            </li>
        </ul>
    </div>
</template>
```

### Translation (_t) Best Practices

**CRITICAL RULE**: Use `_t()` at **DEFINITION TIME** for static labels in JavaScript arrays/constants, NOT via runtime wrapper methods. Static strings in XML templates are automatically translated by Odoo.

**Why?**
- Static strings in XML templates (`.xml` files) are automatically extracted by Odoo's translation system
- Using `_t()` in templates for static strings duplicates translation entries and adds unnecessary overhead
- `_t()` MUST wrap strings **at definition time** in JS so Odoo's PO extractor can find them
- Runtime wrapper methods (like `translateLabel(key)`) do NOT work - the strings are never found by the extractor

**CORRECT - Wrap static labels with `_t()` AT DEFINITION TIME:**
```javascript
/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";

// ✅ CORRECT: Wrap each string with _t() at definition time
const MONTHS = [
    {value: 1, short: _t("Jan"), full: _t("January")},
    {value: 2, short: _t("Feb"), full: _t("February")},
    {value: 3, short: _t("Mar"), full: _t("March")},
    {value: 4, short: _t("Apr"), full: _t("April")},
    {value: 5, short: _t("May"), full: _t("May")},
    {value: 6, short: _t("Jun"), full: _t("June")},
    {value: 7, short: _t("Jul"), full: _t("July")},
    {value: 8, short: _t("Aug"), full: _t("August")},
    {value: 9, short: _t("Sep"), full: _t("September")},
    {value: 10, short: _t("Oct"), full: _t("October")},
    {value: 11, short: _t("Nov"), full: _t("November")},
    {value: 12, short: _t("Dec"), full: _t("December")},
];

// ✅ CORRECT: Status labels wrapped at definition
const STATUS_LABELS = {
    draft: _t("Draft"),
    pending: _t("Pending"),
    approved: _t("Approved"),
    rejected: _t("Rejected"),
};

export class DatePicker extends Component {
    setup() {
        this.months = MONTHS;  // Already translated at definition
    }

    get displayLabel() {
        const month = this.months.find(m => m.value === this.selectedMonth);
        // No translateLabel() needed - values are already translated
        return `${month?.short || ""} ${this.selectedYear}`;
    }
}
```

**WRONG - Runtime wrapper methods don't work:**
```javascript
// ❌ WRONG: Strings without _t() at definition will NOT be translated
const MONTHS = [
    {value: 1, label: "Jan", full: "January"},  // NOT FOUND by PO extractor!
    {value: 2, label: "Feb", full: "February"},
];

// ❌ WRONG: This pattern does NOT work for translation
translateLabel(key) {
    return _t(key);  // key is a variable, not a literal - PO extractor can't find it!
}
```

**CORRECT - Template using pre-translated values:**
```xml
<!-- Month values come from JS MONTHS array - already translated at definition -->
<t t-foreach="getAvailableMonths()" t-as="month" t-key="month.value">
    <a href="#" t-on-click.prevent="() => this.selectMonth(month.value)">
        <!-- No wrapper needed - month.full is already translated -->
        <t t-esc="month.full"/>
    </a>
</t>
```

**CORRECT - Static XML strings need NO wrapper:**
```xml
<!-- Static strings in XML are auto-translated by Odoo -->
<span>No data available</span>
<a href="#">Live</a>
<button type="submit">Submit</button>
```

**When to use `_t()` at DEFINITION TIME:**
1. ✅ Static labels in JavaScript arrays (month names, day names, status labels)
2. ✅ Static labels in JavaScript objects/constants
3. ✅ Error messages defined as constants
4. ✅ Any string literal that will be displayed to users from JS

**When NOT to use `_t()`:**
1. ❌ Static text directly in XML templates (auto-translated)
2. ❌ Runtime wrapper methods like `translateLabel(key)` (doesn't work!)
3. ❌ Dynamic variables passed to `_t()` at runtime
4. ❌ Any hardcoded string in `.xml` files

**REMEMBER**: If you define a string in JavaScript that will be shown to users, wrap it with `_t()` **where it's defined**, not where it's used.

## SCSS and Bootstrap Customization

### Primary Variables Override

**File**: `static/src/scss/primary_variables.scss`

**Purpose**: Override Odoo's built-in style variables (colors, fonts, spacing)

**Include in**: `web._assets_primary_variables` bundle

**Structure**:
```scss
// ============================================================
// Theme Primary Variables
// Override Odoo defaults with !default to allow further overriding
// ============================================================

// Color Palette
$o-color-1: #3498db !default;  // Primary
$o-color-2: #2ecc71 !default;  // Success
$o-color-3: #e74c3c !default;  // Danger
$o-color-4: #f39c12 !default;  // Warning
$o-color-5: #9b59b6 !default;  // Info

// Website Values Palette Configuration
$o-website-values-palettes: (
    (
        // Color Configuration
        'color-palettes-name': 'my-theme',

        // Typography
        'font': 'Inter',
        'headings-font': 'Inter',
        'navbar-font': 'Inter',
        'buttons-font': 'Inter',
        'headings-line-height': 1.2,

        // Header & Navigation
        'header-template': 'default',  // or 'centered', 'boxed'
        'header-font-size': 1rem,
        'logo-height': 3rem,
        'fixed-logo-height': 2rem,
        'hamburger-position': 'right',  // Mobile menu

        // Buttons
        'btn-padding-y': 0.45rem,
        'btn-padding-x': 1.35rem,
        'btn-padding-y-sm': 0.3rem,
        'btn-padding-x-sm': 0.9rem,
        'btn-padding-y-lg': 0.6rem,
        'btn-padding-x-lg': 1.8rem,
        'btn-border-radius': 0.25rem,
        'btn-border-width': 1px,
        'btn-font-size': 1rem,

        // Input Fields
        'input-padding-y': 0.45rem,
        'input-border-radius': 0.25rem,

        // Colors (map to palette)
        'color-1': $o-color-1,
        'color-2': $o-color-2,
        'color-3': $o-color-3,
        'color-4': $o-color-4,
        'color-5': $o-color-5,
    )
);

// Google Fonts Configuration
$o-theme-font-configs: (
    'Inter': (
        'family': ('Inter', sans-serif),
        'url': 'Inter:wght@300;400;500;600;700',
    ),
);
```

### Bootstrap Overrides

**File**: `static/src/scss/bootstrap_overridden.scss`

**Purpose**: Override Bootstrap variables that Odoo hasn't exposed

**Include in**: `web._assets_frontend_helpers` bundle

**Structure**:
```scss
// ============================================================
// Bootstrap Variable Overrides
// Only override Bootstrap vars not available in Odoo variables
// ============================================================

@import "~bootstrap/scss/functions";
@import "~bootstrap/scss/variables";

// Spacing
$spacer: 1rem !default;

// Grid breakpoints
$grid-breakpoints: (
    xs: 0,
    sm: 576px,
    md: 768px,
    lg: 992px,
    xl: 1200px,
    xxl: 1400px
) !default;

// Container max widths
$container-max-widths: (
    sm: 540px,
    md: 720px,
    lg: 960px,
    xl: 1140px,
    xxl: 1320px
) !default;

// Typography
$font-size-base: 1rem !default;
$line-height-base: 1.5 !default;

// Border radius
$border-radius: 0.25rem !default;
$border-radius-sm: 0.125rem !default;
$border-radius-lg: 0.5rem !default;

// Shadows
$box-shadow-sm: 0 .125rem .25rem rgba(0, 0, 0, .075) !default;
$box-shadow: 0 .5rem 1rem rgba(0, 0, 0, .15) !default;
$box-shadow-lg: 0 1rem 3rem rgba(0, 0, 0, .175) !default;
```

## Version-Specific Considerations

### Odoo 17 Specifics

1. **Owl v1**
   - Use `useState` from `@odoo/owl`
   - Legacy import paths
   - Component template as separate property

2. **Snippet Structure**
   - Simple insertion without groups
   - Use XPath targeting `//div[@id='snippet_effect']`

3. **Public Widgets**
   - Import from `@web/legacy/js/public/public_widget`
   - jQuery fully available

### Odoo 18/19 Specifics

1. **Owl v2**
   - Static template property
   - Props validation required
   - New reactive hooks
   - Breaking changes from v1

2. **Snippet Groups**
   - Required `snippet-group` attribute
   - Organized in categories
   - XPath targets `//div[@id='snippet_structure']`

3. **Bootstrap 5.1.3**
   - All use same Bootstrap version
   - Consistent utility classes

4. **Website Builder Enhancements**
   - Theme browsing in editor
   - Custom font upload via UI
   - Enhanced snippet options

### Bootstrap 4 to 5 Migration (Odoo 14/15 → 16+)

When migrating themes:

1. **Class Replacements**:
   ```python
   python scripts/bootstrap_mapper.py <old_classes>
   ```

   Common replacements:
   - `ml-*` → `ms-*` (margin-left → margin-start)
   - `mr-*` → `me-*` (margin-right → margin-end)
   - `pl-*` → `ps-*` (padding-left → padding-start)
   - `pr-*` → `pe-*` (padding-right → padding-end)
   - `text-left` → `text-start`
   - `text-right` → `text-end`
   - `float-left` → `float-start`
   - `float-right` → `float-end`
   - `form-group` → `mb-3`
   - `custom-select` → `form-select`
   - `close` → `btn-close`
   - `badge-*` → `bg-*` (e.g., `badge-primary` → `bg-primary`)
   - `font-weight-bold` → `fw-bold`
   - `sr-only` → `visually-hidden`
   - `no-gutters` → `g-0`

2. **Removed Classes** (find alternatives):
   - `form-inline` - Use grid/flex utilities
   - `jumbotron` - Recreate with utilities
   - `media` - Use `d-flex` with flex utilities

3. **jQuery Removal**:
   - Bootstrap 5 uses vanilla JavaScript
   - May need to adjust widget initialization

## Frontend Performance Best Practices

1. **Asset Bundling**
   - Always use Odoo's asset bundles
   - Don't link external files individually
   - Leverage minification (enabled in production)

2. **Lazy Loading**
   - Use `loading="lazy"` on images
   - Leverage Odoo's `/website/image` route for auto-resizing
   - Lazy load videos (Odoo 18+ has built-in support)

3. **Optimize Snippets**
   - Batch server calls (one RPC for all data)
   - Use QWeb for efficient rendering
   - Minimize DOM manipulation

4. **CSS Optimization**
   - Use Bootstrap utilities instead of custom CSS
   - Keep HTML structure lean
   - Remove unused CSS/JS from bundles

5. **Caching**
   - Utilize computed fields with `store=True`
   - Cache expensive computations
   - Do heavy work server-side

6. **SEO Considerations**
   - Server-render critical content
   - Use Owl for enhancements, not primary content
   - Ensure fast load times

## Security & Access Control

### Model-Level Access

Always create `security/ir.model.access.csv`:

```csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_model_user,model.user,model_model_name,base.group_user,1,1,1,0
access_model_public,model.public,model_model_name,,1,0,0,0
```

### Record-Level Rules

Create `security/rules.xml` for fine-grained control:

```xml
<record id="model_rule" model="ir.rule">
    <field name="name">Model: User own records</field>
    <field name="model_id" ref="model_model_name"/>
    <field name="domain_force">[('user_id', '=', user.id)]</field>
    <field name="groups" eval="[(4, ref('base.group_user'))]"/>
</record>
```

### Controller Security

```python
from odoo import http

class MyController(http.Controller):
    @http.route('/public/route', auth='public')  # No login required
    def public_route(self):
        pass

    @http.route('/user/route', auth='user')  # Login required
    def user_route(self):
        pass
```

### Safe Data Exposure

```python
# Use sudo() carefully
records = request.env['model'].sudo().search([('published', '=', True)])

# Check access rights
if not request.env['model'].check_access_rights('read', raise_exception=False):
    return request.redirect('/access-denied')
```

## Common Workflows

### Create Complete Theme from Figma

1. User provides Figma URL
2. Detect target Odoo version
3. Use Figma MCP to extract design
4. Generate theme module structure
5. Convert colors to SCSS variables
6. Convert components to snippets
7. Create snippet options
8. Test in Odoo Website Builder

### Extend Existing Theme

1. Detect current theme and version
2. Analyze existing structure
3. Create inheriting module
4. Override specific templates
5. Add custom snippets
6. Extend SCSS variables

### Migrate Theme Across Versions

1. Detect source and target versions
2. Convert Bootstrap classes (if 4→5)
3. Update snippet structure (if 17→18/19)
4. Update JavaScript (if Owl v1→v2)
5. Test all functionality
6. Generate migration report

## Testing & Validation

### Theme Installation Test

```bash
# Install theme
python -m odoo -c conf/<config>.conf -d <db> -i theme_<name> --stop-after-init

# Check for errors in log
grep ERROR odoo.log
```

### Snippet Registration Test

1. Install theme
2. Go to Website → Edit
3. Check snippets panel
4. Verify snippet appears in correct category
5. Test drag-and-drop
6. Test snippet options

### Browser Testing

1. Test in multiple browsers (Chrome, Firefox, Safari, Edge)
2. Test responsive breakpoints (sm, md, lg, xl, xxl)
3. Validate accessibility (ARIA labels, keyboard navigation)
4. Check performance (Lighthouse, Page Speed)

## Troubleshooting

### Snippet Not Appearing

**Causes:**
- Incorrect XPath (version mismatch)
- Missing group attribute (Odoo 18/19)
- Template not found
- Syntax error in XML

**Solutions:**
1. Check Odoo version and use correct insertion method
2. Verify template ID exists
3. Check XML syntax
4. Look for errors in log

### Styles Not Applying

**Causes:**
- SCSS not included in correct bundle
- Variable override not using `!default`
- CSS specificity issues
- Asset not compiled

**Solutions:**
1. Verify asset bundle in manifest
2. Clear browser cache
3. Check asset regeneration: `odoo-bin --update theme_<name>`
4. Use browser DevTools to inspect computed styles

### JavaScript Not Working

**Causes:**
- Import path incorrect for Odoo version
- Widget not registered
- jQuery conflicts (Bootstrap 5)
- Owl version mismatch

**Solutions:**
1. Check import paths for Odoo version
2. Verify widget/component registration
3. Check console for errors
4. Ensure correct Owl version usage

## Expert Tips

1. **Always Use Version Detection First**
   - Don't assume Odoo version
   - Check before generating any code

2. **Prefer Bootstrap Utilities**
   - Less custom CSS = easier maintenance
   - Better performance
   - Editor-compatible

3. **Server-Side Rendering for SEO**
   - Don't rely on client-side JS for content
   - Use Owl for enhancements only

4. **Test in Edit Mode**
   - Ensure Website Builder can handle your code
   - Test snippet options thoroughly

5. **Follow Odoo Patterns**
   - Study core themes (`odoo/addons/theme_*`)
   - Match existing conventions
   - Use same class prefixes (`s_`, `o_`)

6. **Documentation**
   - Comment complex SCSS
   - Document snippet options
   - Provide README for theme

## Progressive Web App (PWA) Implementation

### Command: Setup PWA for Odoo Website

**Trigger**: User asks to "make PWA", "add offline support", "enable push notifications"

**Workflow**:

1. **Generate Service Worker**
   ```javascript
   // static/src/service-worker.js
   const CACHE_NAME = 'odoo-pwa-v1';
   const urlsToCache = ['/', '/web/static/lib/owl/owl.js'];

   self.addEventListener('install', event => {
     event.waitUntil(
       caches.open(CACHE_NAME)
         .then(cache => cache.addAll(urlsToCache))
     );
   });

   self.addEventListener('fetch', event => {
     event.respondWith(
       caches.match(event.request)
         .then(response => response || fetch(event.request))
     );
   });
   ```

2. **Create Web App Manifest**
   ```json
   {
     "name": "Odoo PWA",
     "short_name": "OdooPWA",
     "start_url": "/",
     "display": "standalone",
     "background_color": "#875A7B",
     "theme_color": "#875A7B",
     "icons": [...]
   }
   ```

3. **Register Service Worker**
   ```javascript
   /** @odoo-module **/
   import publicWidget from "@web/legacy/js/public/public_widget";

   publicWidget.registry.ServiceWorkerRegistration = publicWidget.Widget.extend({
     selector: 'body',
     start: function() {
       if ('serviceWorker' in navigator) {
         navigator.serviceWorker.register('/service-worker.js');
       }
       return this._super(...arguments);
     }
   });
   ```

## Modern JavaScript & TypeScript

### Command: Setup TypeScript

**Trigger**: User asks to "use TypeScript", "add type safety", "configure TypeScript"

**Workflow**:

1. **Generate tsconfig.json**
   ```json
   {
     "compilerOptions": {
       "target": "ES2020",
       "module": "ES2020",
       "lib": ["ES2020", "DOM"],
       "strict": true,
       "paths": {
         "@web/*": ["./addons/web/static/src/*"],
         "@owl/*": ["./addons/web/static/lib/owl/*"]
       }
     }
   }
   ```

2. **Create Typed Owl Component**
   ```typescript
   /** @odoo-module **/
   import { Component, useState } from "@odoo/owl";

   interface ProductProps {
     id: number;
     name: string;
     price: number;
   }

   export class ProductComponent extends Component<ProductProps> {
     static template = xml`...`;

     setup() {
       this.state = useState({ loading: false });
     }
   }
   ```

### ES2020+ Patterns

**Use modern JavaScript features**:
```javascript
// Optional chaining
const userName = this.props.user?.profile?.name;

// Nullish coalescing
const displayName = userName ?? 'Guest User';

// Dynamic imports
const module = await import('./HeavyFeatureComponent');

// Private class fields
class SecureWidget {
  #apiKey = null;
  #generateKey() {
    return crypto.randomUUID();
  }
}
```

## Testing Infrastructure

### Command: Setup Testing

**Trigger**: User asks to "add tests", "setup Jest", "configure Cypress"

**Workflow**:

1. **Jest Configuration**
   ```javascript
   // jest.config.js
   module.exports = {
     testEnvironment: 'jsdom',
     moduleNameMapper: {
       '^@web/(.*)$': '<rootDir>/addons/web/static/src/$1',
     },
     collectCoverageFrom: ['static/src/**/*.{js,jsx}']
   };
   ```

2. **Cypress E2E Tests**
   ```javascript
   // cypress/e2e/ecommerce.cy.js
   describe('E-commerce Flow', () => {
     it('should complete purchase', () => {
       cy.visit('/shop');
       cy.get('[data-product-id="1"]').click();
       cy.get('#add_to_cart').click();
       cy.get('.btn-primary').contains('Checkout').click();
     });
   });
   ```

3. **Visual Regression Testing**
   ```javascript
   // backstop.config.js
   module.exports = {
     scenarios: [{
       label: 'Homepage',
       url: 'http://localhost:8069',
       misMatchThreshold: 0.1
     }]
   };
   ```

## Performance Optimization

### Command: Optimize Core Web Vitals

**Trigger**: User asks to "improve performance", "optimize LCP/FID/CLS", "speed up website"

**Workflow**:

1. **Optimize Largest Contentful Paint (LCP)**
   ```javascript
   // Preload critical resources
   const link = document.createElement('link');
   link.rel = 'preload';
   link.as = 'image';
   link.href = '/web/image/website/1/logo';
   document.head.appendChild(link);
   ```

2. **Reduce First Input Delay (FID)**
   ```javascript
   // Break up long tasks
   function optimizeLongTask(items) {
     const chunks = [];
     for (let i = 0; i < items.length; i += 100) {
       chunks.push(items.slice(i, i + 100));
     }
     chunks.forEach(chunk => {
       requestIdleCallback(() => processChunk(chunk));
     });
   }
   ```

3. **Minimize Cumulative Layout Shift (CLS)**
   ```css
   /* Reserve space for dynamic content */
   .product-image-container {
     aspect-ratio: 1/1;
     contain: layout;
   }
   ```

## Accessibility (WCAG Compliance)

### Command: Implement Accessibility

**Trigger**: User asks to "add ARIA", "make accessible", "WCAG compliance"

**Workflow**:

1. **ARIA Implementation**
   ```xml
   <form role="form" aria-label="Contact Form">
     <input type="email"
            aria-labelledby="email-label"
            aria-describedby="email-error"
            aria-required="true"
            aria-invalid="false"/>
     <span id="email-error" role="alert" aria-live="polite"></span>
   </form>
   ```

2. **Keyboard Navigation**
   ```javascript
   class KeyboardNavigationManager {
     handleTab(event) {
       if (event.shiftKey) {
         // Backward navigation
       } else {
         // Forward navigation
       }
     }
     trapFocus() {
       // Trap focus within modal
     }
   }
   ```

3. **Screen Reader Support**
   ```javascript
   class ScreenReaderAnnouncer {
     announce(message, priority = 'polite') {
       this.liveRegion.setAttribute('aria-live', priority);
       this.liveRegion.textContent = message;
     }
   }
   ```

## Real-time Features

### Command: Add WebSocket Support

**Trigger**: User asks to "add real-time", "implement WebSocket", "live updates"

**Workflow**:

1. **WebSocket Manager**
   ```javascript
   /** @odoo-module **/
   export class WebSocketManager {
     constructor(url) {
       this.socket = new WebSocket(url);
       this.setupEventHandlers();
     }

     setupEventHandlers() {
       this.socket.onmessage = (event) => {
         const data = JSON.parse(event.data);
         this.handleMessage(data);
       };
     }

     send(data) {
       if (this.socket.readyState === WebSocket.OPEN) {
         this.socket.send(JSON.stringify(data));
       }
     }
   }
   ```

2. **Server-Sent Events (SSE)**
   ```javascript
   class SSEManager {
     constructor(url) {
       this.eventSource = new EventSource(url);
       this.eventSource.onmessage = (event) => {
         this.handleMessage(event.data);
       };
     }
   }
   ```

## Web Components

### Command: Create Web Component

**Trigger**: User asks to "create web component", "custom element"

**Workflow**:

```javascript
/** @odoo-module **/

export class OdooSearchInput extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
  }

  static get observedAttributes() {
    return ['placeholder', 'value'];
  }

  connectedCallback() {
    this.render();
  }

  render() {
    this.shadowRoot.innerHTML = `
      <style>
        :host { display: block; }
        input { width: 100%; padding: 0.5rem; }
      </style>
      <input type="text" placeholder="${this.getAttribute('placeholder')}"/>
    `;
  }
}

customElements.define('odoo-search-input', OdooSearchInput);
```

## Advanced Odoo Features

### Tour Manager

**Command**: Create guided tour

```javascript
/** @odoo-module **/
import tour from 'web_tour.tour';

tour.register('product_tour', {
  url: '/shop',
}, [{
  content: 'Click on any product',
  trigger: '.oe_product:first',
  position: 'bottom',
}]);
```

### Custom Field Widgets

```javascript
/** @odoo-module **/
import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";

export class ColorPickerField extends Component {
  static template = xml`
    <input type="color" t-att-value="props.value" t-on-change="onChange"/>
  `;

  onChange(event) {
    this.props.update(event.target.value);
  }
}

registry.category("fields").add("color_picker", ColorPickerField);
```

### Systray Components

```javascript
/** @odoo-module **/
import { registry } from "@web/core/registry";
import { Component, useState } from "@odoo/owl";

export class NotificationBell extends Component {
  static template = xml`...`;

  setup() {
    this.state = useState({ notifications: [] });
  }
}

registry.category("systray").add("NotificationBell", {
  Component: NotificationBell,
});
```

## Modern Build Tools

### Vite Configuration

**Command**: Setup Vite build

```javascript
// vite.config.js
import { defineConfig } from 'vite';

export default defineConfig({
  base: '/web/static/',
  build: {
    rollupOptions: {
      input: {
        main: 'static/src/main.js',
        website: 'static/src/website.js'
      }
    }
  },
  server: {
    proxy: {
      '/web': 'http://localhost:8069'
    }
  }
});
```

### CI/CD Pipeline

```yaml
# .github/workflows/odoo-frontend.yml
name: Odoo Frontend CI/CD

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Run tests
      run: |
        npm run test:unit
        npm run test:e2e
    - name: Build assets
      run: npm run build
```

## Resources

- **Odoo Documentation**: https://www.odoo.com/documentation/
- **Bootstrap 5 Docs**: https://getbootstrap.com/docs/5.1/
- **Owl Framework**: https://github.com/odoo/owl
- **TypeScript**: https://www.typescriptlang.org/docs/
- **Jest**: https://jestjs.io/docs/
- **Cypress**: https://docs.cypress.io/
- **Web Components**: https://developer.mozilla.org/en-US/docs/Web/Web_Components
- **Community Forums**: https://www.odoo.com/forum/

## Changelog

- v2.0.0: Added PWA support, TypeScript, testing frameworks, performance optimization, accessibility, real-time features, and modern build tools
- v1.0.0: Initial release with full Odoo 14-19 support, Figma/DevTools MCP integration
