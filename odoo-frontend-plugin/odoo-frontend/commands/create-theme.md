---
title: 'Create Theme'
description: 'Create a complete Odoo website theme module with all necessary files, SCSS variables, pages, and JavaScript'
author: TAQAT Techno
author-url: https://github.com/taqat-techno
version: 3.1.0
---

# /create-theme - Complete Odoo Theme Generator

Generate a professional, production-ready Odoo website theme module with all necessary files based on comprehensive best practices discovered from 40+ real-world theme implementations.

## Overview

This command creates a complete theme module structure including:
- **SCSS Variables**: Full `$o-website-values-palettes` configuration with color semantics
- **Color Palette**: Properly structured `o-color-1` through `o-color-5` with semantic meanings
- **Typography**: Complete heading hierarchy and font configurations
- **Layout Files**: Header, footer, and base templates
- **Individual Page Files**: Homepage, About, Contact, Services (best practice pattern)
- **Menu Configuration**: Complete navigation structure
- **JavaScript**: publicWidget patterns with editableMode handling
- **Security**: Model access rules
- **Asset Bundles**: Properly configured for all Odoo versions (14-19)

## Usage

### Interactive Mode (Recommended)
```
/create-theme
```
Prompts for all configuration options interactively.

### Quick Mode with Arguments
```
/create-theme <theme_name> <project_path>
```
Creates theme with defaults, then allows customization.

### Full Arguments
```
/create-theme <theme_name> <project_path> --version=17 --colors="#207AB7,#FB9F54,#F6F4F0,#FFFFFF,#191A19" --font="IBM Plex Sans"
```

## What Gets Created

### Complete Directory Structure
```
theme_<name>/
├── __init__.py
├── __manifest__.py
├── security/
│   └── ir.model.access.csv
├── data/
│   ├── assets.xml                    # Theme assets configuration
│   ├── menu.xml                      # Navigation menu items
│   └── pages/                        # Individual page files (BEST PRACTICE!)
│       ├── home_page.xml            # Homepage (inherits website.homepage)
│       ├── aboutus_page.xml         # About Us page
│       ├── contactus_page.xml       # Contact (inherits website.contactus)
│       ├── services_page.xml        # Services page
│       └── thanks_page.xml          # Thank you page
├── views/
│   ├── layout/
│   │   ├── header.xml               # Header customization
│   │   ├── footer.xml               # Footer customization
│   │   └── templates.xml            # Base layout templates
│   └── snippets/
│       └── custom_snippets.xml      # Custom snippet definitions
└── static/
    ├── description/
    │   ├── cover.png                # Theme cover image
    │   └── screenshot.png           # Theme screenshot
    └── src/
        ├── scss/
        │   ├── primary_variables.scss    # $o-website-values-palettes + colors
        │   ├── bootstrap_overridden.scss # Bootstrap overrides
        │   └── theme.scss               # Custom theme styles
        ├── js/
        │   ├── theme.js                 # publicWidget implementations
        │   └── snippets_options.js      # Snippet option handlers
        └── img/
            └── .gitkeep                 # Image placeholder
```

## Configuration Options

### Theme Name
- **Format**: snake_case (converted automatically)
- **Example**: `relief_center`, `corporate_blue`, `modern_dark`

### Primary Colors (o-color System)
Based on Odoo's semantic color structure:

| Variable | Semantic Meaning | Default |
|----------|------------------|---------|
| o-color-1 | Primary brand color | #207AB7 |
| o-color-2 | Secondary/accent color | #FB9F54 |
| o-color-3 | Light backgrounds | #F6F4F0 |
| o-color-4 | White/body base | #FFFFFF |
| o-color-5 | Dark text/headings | #191A19 |

### Typography Options
| Option | Description | Default |
|--------|-------------|---------|
| font | Body text font | IBM Plex Sans |
| headings-font | Heading font (h1-h6) | IBM Plex Sans |
| navbar-font | Navigation font | IBM Plex Sans |
| buttons-font | Button text font | IBM Plex Sans |

### Header Templates
- `default` - Standard horizontal header
- `hamburger` - Mobile-first hamburger menu
- `centered` - Center-aligned navigation
- `boxed` - Contained header layout

### Footer Templates
- `default` - Standard footer
- `headline` - Large headline focus
- `minimalist` - Clean minimal footer
- `contact` - Contact-focused layout

## Implementation Details

### Step 1: Gather Configuration

When invoked, prompt for:
1. Theme name (snake_case)
2. Target Odoo version (14-19, affects Bootstrap version)
3. Project path (where to create the theme)
4. Primary colors (5 colors with semantic meanings)
5. Typography preferences (font families)
6. Header/footer templates
7. Pages to include

### Step 2: Detect Odoo Version

Use the version detector to determine:
- Odoo version (affects manifest format)
- Bootstrap version (4.x for 14-15, 5.1.3 for 16+)
- Snippet structure (simple vs grouped for 18+)
- Owl version if needed

### Step 3: Generate Files

Create all files using templates with placeholders replaced:

#### __manifest__.py Pattern
```python
{
    'name': 'Theme {{THEME_DISPLAY_NAME}}',
    'version': '{{ODOO_VERSION}}.1.0.0',
    'summary': '{{THEME_DISPLAY_NAME}} - Modern Odoo Website Theme',
    'category': 'Website/Theme',
    'author': 'TaqaTechno',
    'website': 'https://www.taqatechno.com/',
    'support': 'info@taqatechno.com',
    'license': 'LGPL-3',
    'depends': ['website'],
    'data': [
        'security/ir.model.access.csv',
        'data/assets.xml',
        'views/layout/header.xml',
        'views/layout/footer.xml',
        'views/layout/templates.xml',
        'views/snippets/custom_snippets.xml',
        'data/menu.xml',
        'data/pages/home_page.xml',
        'data/pages/aboutus_page.xml',
        'data/pages/contactus_page.xml',
        'data/pages/services_page.xml',
    ],
    'assets': {
        'web._assets_primary_variables': [
            'theme_{{THEME_NAME}}/static/src/scss/primary_variables.scss',
        ],
        'web._assets_frontend_helpers': [
            ('prepend', 'theme_{{THEME_NAME}}/static/src/scss/bootstrap_overridden.scss'),
        ],
        'web.assets_frontend': [
            'theme_{{THEME_NAME}}/static/src/scss/theme.scss',
            'theme_{{THEME_NAME}}/static/src/js/theme.js',
        ],
        'website.assets_wysiwyg': [
            'theme_{{THEME_NAME}}/static/src/js/snippets_options.js',
        ],
    },
    'images': [
        'static/description/cover.png',
        'static/description/screenshot.png',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
```

#### primary_variables.scss Pattern
```scss
// ===================================================================
// Theme: {{THEME_DISPLAY_NAME}}
// Generated by TAQAT Techno Plugin
// ===================================================================

// === Typography Hierarchy ===
$o-theme-h1-font-size-multiplier: (64 / 16); // 4rem - Hero text
$o-theme-h2-font-size-multiplier: (48 / 16); // 3rem - Section headers
$o-theme-h3-font-size-multiplier: (32 / 16); // 2rem - Sub-section headers
$o-theme-h4-font-size-multiplier: (28 / 16); // 1.75rem - Card headers
$o-theme-h5-font-size-multiplier: (24 / 16); // 1.5rem - Small headers
$o-theme-h6-font-size-multiplier: (18 / 16); // 1.125rem - Captions

$o-theme-headings-font-weight: 700;
$o-theme-font-weight-normal: 400;
$o-theme-font-weight-medium: 500;
$o-theme-font-weight-semibold: 600;
$o-theme-font-weight-bold: 700;

// === Website Values Palette ===
$o-website-values-palettes: (
    (
        'color-palettes-name': '{{PALETTE_NAME}}',

        // Typography
        'font': '{{BODY_FONT}}',
        'headings-font': '{{HEADINGS_FONT}}',
        'navbar-font': '{{NAVBAR_FONT}}',
        'buttons-font': '{{BUTTONS_FONT}}',
        'headings-line-height': 1.3,
        'line-height-base': 1.6,

        // Header
        'header-template': '{{HEADER_TEMPLATE}}',
        'header-links-style': 'default',
        'hamburger-position': 'right',
        'logo-height': 3rem,
        'fixed-logo-height': 2rem,

        // Buttons
        'btn-padding-y': 0.75rem,
        'btn-padding-x': 2rem,
        'btn-padding-y-sm': 0.5rem,
        'btn-padding-x-sm': 1.5rem,
        'btn-padding-y-lg': 1rem,
        'btn-padding-x-lg': 3rem,
        'btn-border-radius': 0.5rem,
        'btn-border-radius-sm': 0.25rem,
        'btn-border-radius-lg': 0.75rem,
        'btn-font-weight': 500,

        // Inputs
        'input-padding-y': 0.75rem,
        'input-padding-x': 1rem,
        'input-border-radius': 0.5rem,

        // Footer
        'footer-template': '{{FOOTER_TEMPLATE}}',
        'footer-scrolltop': true,

        // Links
        'link-underline': 'never',
    ),
);

// === Color Palette (Semantic Structure) ===
// o-color-1: Primary brand color
// o-color-2: Secondary/accent color
// o-color-3: Light backgrounds
// o-color-4: White/body base
// o-color-5: Dark text/headings
$o-color-palettes: map-merge($o-color-palettes, (
    '{{PALETTE_NAME}}': (
        'o-color-1': {{COLOR_1}},
        'o-color-2': {{COLOR_2}},
        'o-color-3': {{COLOR_3}},
        'o-color-4': {{COLOR_4}},
        'o-color-5': {{COLOR_5}},
        'menu': 1,
        'footer': 1,
        'copyright': 5,
    ),
));

// === Font Configuration ===
$o-theme-font-configs: map-merge($o-theme-font-configs, (
    '{{BODY_FONT}}': (
        'family': ('{{BODY_FONT}}', sans-serif),
        'url': '{{FONT_URL}}',
        'properties': (
            'base': (
                'font-size-base': 1rem,
                'line-height-base': 1.6,
            ),
        ),
    ),
));

// === Extended Color System ===
$o-white: #FFFFFF !default;
$o-black: {{COLOR_5}} !default;
$o-success: #28a745 !default;
$o-info: #17a2b8 !default;
$o-warning: #ffc107 !default;
$o-danger: #dc3545 !default;

// === Background Shapes ===
$o-bg-shapes: change-shape-colors-mapping('web_editor', 'Wavy/21', (2: 1));
```

#### Homepage Pattern (data/pages/home_page.xml)
```xml
<?xml version="1.0" encoding="UTF-8"?>
<odoo>
    <data noupdate="0">
        <template
            name="{{THEME_DISPLAY_NAME}} Home Page"
            id="{{THEME_NAME}}_home_page"
            inherit_id="website.homepage"
            active="True">
            <xpath expr="//div[@id='wrap']" position="replace">
                <t t-set="is_home_page" t-value="True"/>
                <div id="wrap" class="oe_structure oe_empty">
                    <main class="main__content">
                        <!-- Hero Section -->
                        <section class="s_hero pt-5 pb-5 o_cc o_cc1">
                            <div class="container">
                                <div class="row align-items-center">
                                    <div class="col-lg-6">
                                        <h1 class="display-4 fw-bold mb-4">
                                            Welcome to {{THEME_DISPLAY_NAME}}
                                        </h1>
                                        <p class="lead mb-4">
                                            Your compelling tagline goes here.
                                            Describe your value proposition.
                                        </p>
                                        <div class="d-flex gap-3 flex-wrap">
                                            <a href="/contactus"
                                               class="btn btn-primary btn-lg">
                                                Get Started
                                            </a>
                                            <a href="/aboutus"
                                               class="btn btn-outline-secondary btn-lg">
                                                Learn More
                                            </a>
                                        </div>
                                    </div>
                                    <div class="col-lg-6 mt-4 mt-lg-0">
                                        <div class="position-relative">
                                            <!-- Hero image or content -->
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </section>

                        <!-- Editable structure for snippets -->
                        <div class="oe_structure"/>

                        <!-- Features Section -->
                        <section class="s_features pt-5 pb-5 o_cc o_cc3">
                            <div class="container">
                                <div class="text-center mb-5">
                                    <h2 class="fw-bold">Our Features</h2>
                                    <p class="text-muted">
                                        Discover what makes us different
                                    </p>
                                </div>
                                <div class="row g-4">
                                    <div class="col-md-4">
                                        <div class="card h-100 border-0 shadow-sm">
                                            <div class="card-body text-center p-4">
                                                <div class="feature-icon mb-3">
                                                    <i class="fa fa-star fa-2x text-primary"></i>
                                                </div>
                                                <h5 class="card-title">Feature One</h5>
                                                <p class="card-text text-muted">
                                                    Description of your first feature.
                                                </p>
                                            </div>
                                        </div>
                                    </div>
                                    <div class="col-md-4">
                                        <div class="card h-100 border-0 shadow-sm">
                                            <div class="card-body text-center p-4">
                                                <div class="feature-icon mb-3">
                                                    <i class="fa fa-heart fa-2x text-primary"></i>
                                                </div>
                                                <h5 class="card-title">Feature Two</h5>
                                                <p class="card-text text-muted">
                                                    Description of your second feature.
                                                </p>
                                            </div>
                                        </div>
                                    </div>
                                    <div class="col-md-4">
                                        <div class="card h-100 border-0 shadow-sm">
                                            <div class="card-body text-center p-4">
                                                <div class="feature-icon mb-3">
                                                    <i class="fa fa-rocket fa-2x text-primary"></i>
                                                </div>
                                                <h5 class="card-title">Feature Three</h5>
                                                <p class="card-text text-muted">
                                                    Description of your third feature.
                                                </p>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </section>

                        <!-- Editable structure -->
                        <div class="oe_structure"/>
                    </main>
                </div>
            </xpath>
        </template>
    </data>
</odoo>
```

#### publicWidget Pattern (static/src/js/theme.js)
```javascript
/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

/**
 * Animate On Scroll Widget
 * Uses IntersectionObserver to add animation classes when elements enter viewport
 */
publicWidget.registry.{{THEME_NAME}}AnimateOnScroll = publicWidget.Widget.extend({
    selector: '.animate-on-scroll',
    disabledInEditableMode: false,

    /**
     * @override
     */
    start: function () {
        // Only initialize animations in read mode
        if (!this.editableMode) {
            this._initAnimationObserver();
        }
        return this._super.apply(this, arguments);
    },

    /**
     * @override - CRITICAL: Clean up observers to prevent memory leaks
     */
    destroy: function () {
        if (this.animationObserver) {
            this.animationObserver.disconnect();
        }
        return this._super.apply(this, arguments);
    },

    /**
     * Initialize IntersectionObserver for scroll animations
     * @private
     */
    _initAnimationObserver: function () {
        this.animationObserver = new IntersectionObserver(
            (entries) => {
                entries.forEach((entry) => {
                    entry.target.classList.toggle('animated', entry.isIntersecting);
                });
            },
            { threshold: 0.1 }
        );

        document.querySelectorAll('.animate-on-scroll').forEach((el) => {
            this.animationObserver.observe(el);
        });
    },
});

/**
 * Smooth Scroll Widget
 * Handles smooth scrolling for anchor links
 */
publicWidget.registry.{{THEME_NAME}}SmoothScroll = publicWidget.Widget.extend({
    selector: 'a[href^="#"]',
    events: {
        'click': '_onAnchorClick',
    },

    /**
     * Handle click on anchor links
     * @private
     * @param {Event} ev
     */
    _onAnchorClick: function (ev) {
        // Don't run in edit mode
        if (this.editableMode) return;

        const href = this.$el.attr('href');
        if (href && href.length > 1) {
            const target = document.querySelector(href);
            if (target) {
                ev.preventDefault();
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start',
                });
            }
        }
    },
});

/**
 * Lazy Image Load Widget
 * Uses native lazy loading with fallback
 */
publicWidget.registry.{{THEME_NAME}}LazyLoad = publicWidget.Widget.extend({
    selector: 'img.lazy-load',

    /**
     * @override
     */
    start: function () {
        if (!this.editableMode) {
            this._initLazyLoad();
        }
        return this._super.apply(this, arguments);
    },

    /**
     * @override
     */
    destroy: function () {
        if (this.lazyObserver) {
            this.lazyObserver.disconnect();
        }
        return this._super.apply(this, arguments);
    },

    /**
     * Initialize lazy loading
     * @private
     */
    _initLazyLoad: function () {
        // Use IntersectionObserver for lazy loading
        this.lazyObserver = new IntersectionObserver(
            (entries) => {
                entries.forEach((entry) => {
                    if (entry.isIntersecting) {
                        const img = entry.target;
                        if (img.dataset.src) {
                            img.src = img.dataset.src;
                            img.classList.add('loaded');
                        }
                        this.lazyObserver.unobserve(img);
                    }
                });
            },
            { threshold: 0.1, rootMargin: '50px' }
        );

        this.lazyObserver.observe(this.el);
    },
});

export default {
    AnimateOnScroll: publicWidget.registry.{{THEME_NAME}}AnimateOnScroll,
    SmoothScroll: publicWidget.registry.{{THEME_NAME}}SmoothScroll,
    LazyLoad: publicWidget.registry.{{THEME_NAME}}LazyLoad,
};
```

#### Menu Configuration (data/menu.xml)
```xml
<?xml version="1.0" encoding="UTF-8"?>
<odoo>
    <data>
        <record id="menu_home" model="theme.website.menu">
            <field name="name">Home</field>
            <field name="url">/</field>
            <field name="sequence" type="int">10</field>
        </record>

        <record id="menu_about" model="theme.website.menu">
            <field name="name">About</field>
            <field name="url">/aboutus</field>
            <field name="sequence" type="int">20</field>
        </record>

        <record id="menu_services" model="theme.website.menu">
            <field name="name">Services</field>
            <field name="url">/services</field>
            <field name="sequence" type="int">30</field>
        </record>

        <record id="menu_contact" model="theme.website.menu">
            <field name="name">Contact</field>
            <field name="url">/contactus</field>
            <field name="sequence" type="int">40</field>
        </record>
    </data>
</odoo>
```

### Step 4: Post-Generation Guidance

After creating all files, provide:
1. Installation command
2. How to activate the theme
3. Customization tips
4. Testing checklist

## Version-Specific Adjustments

### Odoo 14-15 (Bootstrap 4)
- Use `ml-*`, `mr-*` classes (not `ms-*`, `me-*`)
- Different asset bundle syntax
- No snippet groups

### Odoo 16-17 (Bootstrap 5.1.3)
- Use `ms-*`, `me-*` classes
- Modern asset bundle syntax
- Simple snippet registration

### Odoo 18-19 (Bootstrap 5.1.3 + Snippet Groups)
- Use snippet groups in registration
- Owl v2 patterns available
- Enhanced website builder integration

## Example Outputs

### Successful Creation
```
╔══════════════════════════════════════════════════════════════╗
║           THEME CREATED SUCCESSFULLY!                        ║
╠══════════════════════════════════════════════════════════════╣
║ Theme Name:    theme_corporate_blue                          ║
║ Odoo Version:  17.0                                          ║
║ Bootstrap:     5.1.3                                          ║
║ Location:      projects/corporate/theme_corporate_blue/      ║
╠══════════════════════════════════════════════════════════════╣
║ FILES CREATED:                                               ║
║ ✓ __manifest__.py                                            ║
║ ✓ __init__.py                                                ║
║ ✓ security/ir.model.access.csv                               ║
║ ✓ static/src/scss/primary_variables.scss                     ║
║ ✓ static/src/scss/bootstrap_overridden.scss                  ║
║ ✓ static/src/scss/theme.scss                                 ║
║ ✓ static/src/js/theme.js                                     ║
║ ✓ static/src/js/snippets_options.js                          ║
║ ✓ views/layout/header.xml                                    ║
║ ✓ views/layout/footer.xml                                    ║
║ ✓ views/layout/templates.xml                                 ║
║ ✓ views/snippets/custom_snippets.xml                         ║
║ ✓ data/assets.xml                                            ║
║ ✓ data/menu.xml                                              ║
║ ✓ data/pages/home_page.xml                                   ║
║ ✓ data/pages/aboutus_page.xml                                ║
║ ✓ data/pages/contactus_page.xml                              ║
║ ✓ data/pages/services_page.xml                               ║
╠══════════════════════════════════════════════════════════════╣
║ NEXT STEPS:                                                  ║
║ 1. Update module list:                                       ║
║    python -m odoo -c conf/config.conf -d db --update-list    ║
║                                                              ║
║ 2. Install theme:                                            ║
║    python -m odoo -c conf/config.conf -d db                  ║
║    -i theme_corporate_blue --stop-after-init                 ║
║                                                              ║
║ 3. Activate theme:                                           ║
║    Website → Configuration → Settings → Theme                ║
╚══════════════════════════════════════════════════════════════╝
```

## Best Practices Applied

This command automatically applies best practices discovered from 40+ theme implementations:

1. **Individual Page Files** - Each page in separate XML file (not single pages.xml)
2. **Mirror Model Architecture** - Proper `theme.website.page` for multi-website support
3. **Semantic Color System** - o-color-1 through o-color-5 with consistent meanings
4. **publicWidget Patterns** - Proper lifecycle methods with editableMode handling
5. **Asset Bundle Structure** - Correct bundle assignments for each file type
6. **Typography Hierarchy** - Consistent heading size multipliers
7. **Font Configuration** - Proper Google Fonts integration via Odoo's system
8. **Security Rules** - Pre-configured model access
9. **TaqaTechno Standards** - Author, website, support fields in manifest

## Notes

- Always verify Odoo version before creating theme
- Test theme in both read mode and edit mode
- Individual page files is the recommended pattern (not single pages.xml)
- Use publicWidget for website themes (not Owl)
- Clean up IntersectionObservers in destroy() to prevent memory leaks
