---
name: theme-snippets
description: |
  Complete Odoo website snippet reference and creation guide. Covers snippet architecture, 81+ static snippet templates (structure, gallery, features, dynamic, inner content, mega menus), dynamic snippets system, snippet options (we-* elements), custom snippet creation for Odoo 14-19, and version-aware registration (simple vs groups).

  <example>
  Context: User wants to create a custom snippet
  user: "Create a custom snippet for my Odoo website"
  assistant: "I will create a version-aware snippet with template, registration, and options."
  <commentary>Custom snippet creation.</commentary>
  </example>

  <example>
  Context: User wants to know available snippets
  user: "What snippets are available in Odoo?"
  assistant: "Odoo has 81+ static snippets across 6 categories."
  <commentary>Snippet inventory reference.</commentary>
  </example>

  <example>
  Context: User wants a dynamic snippet
  user: "Create a dynamic snippet that shows latest products"
  assistant: "I will create a dynamic snippet with filter, display template, and data source."
  <commentary>Dynamic snippet creation.</commentary>
  </example>

  <example>
  Context: User needs snippet options
  user: "Add customization options to my snippet"
  assistant: "I will create snippet_options XML with we-* elements."
  <commentary>Snippet options system.</commentary>
  </example>
version: "8.0.0"
author: "TaqaTechno"
license: "MIT"
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - Grep
  - Glob
---

# Odoo Website Snippets Reference

## Snippet Architecture

```
STATIC SNIPPETS (81+ templates)    DYNAMIC SNIPPETS (data-driven)
├── Pre-built HTML                  ├── ir.filters (data source)
├── Drag & drop                     ├── website.snippet.filter (fetcher)
└── 6 categories                    └── Display templates (renderer)

              SNIPPET OPTIONS SYSTEM
              we-select | we-button | we-colorpicker | we-input
              data-selector | data-select-class | data-js
```

## Static Snippets Inventory (81+ Templates)

### Structure (14)

| ID | Name | Best For |
|----|------|----------|
| `s_banner` | Banner | Landing pages |
| `s_cover` | Cover | Headers |
| `s_text_image` | Text - Image | Features |
| `s_image_text` | Image - Text | Features |
| `s_title` | Title | Section headers |
| `s_text_block` | Text Block | Content |
| `s_numbers` | Numbers | Achievements |
| `s_three_columns` | Columns | Content grids |
| `s_features` | Features | Benefits |
| `s_masonry_block` | Masonry | Galleries |
| `s_image_gallery` | Image Gallery | Portfolios |

### Features (11)

| ID | Name | Best For |
|----|------|----------|
| `s_comparisons` | Comparisons | Product comparison |
| `s_company_team` | Team | About pages |
| `s_call_to_action` | CTA | Conversions |
| `s_references` | References | Social proof |
| `s_accordion` | Accordion | FAQs |
| `s_features_grid` | Features Grid | Benefits |
| `s_pricelist` | Pricelist | Products |
| `s_faq_collapse` | FAQ | Support |
| `s_tabs` | Tabs | Organization |

### Dynamic Content (15)

| ID | Name | Best For |
|----|------|----------|
| `s_google_map` | Google Map | Contact pages |
| `s_website_form` | Form | Lead capture |
| `s_social_media` | Social Media | Engagement |
| `s_dynamic_snippet` | Dynamic | Data display |
| `s_countdown` | Countdown | Events |
| `s_popup` | Popup | Promotions |
| `s_newsletter_block` | Newsletter | Marketing |

### Inner Content (16)

| ID | Name | Best For |
|----|------|----------|
| `s_card` | Card | Items |
| `s_three_cards` / `s_four_cards` | Cards | Services/Features |
| `s_timeline` | Timeline | History |
| `s_process_steps` | Steps | Tutorials |
| `s_quotes_carousel` | Testimonials | Social proof |
| `s_blockquote` | Blockquote | Emphasis |

### Mega Menus (9)

| ID | Name |
|----|------|
| `s_mega_menu_multi_menus` | Multiple menu columns |
| `s_mega_menu_cards` | Card-style menu |
| `s_mega_menu_big_icons` | Large icon menu |
| `s_mega_menu_thumbnails` | Thumbnail gallery |

---

## Creating Custom Snippets

### Odoo 14-17: Simple Registration

```xml
<!-- 1. Snippet Template -->
<template id="s_my_snippet" name="My Snippet">
    <section class="s_my_snippet pt48 pb48 o_cc o_cc1">
        <div class="container">
            <div class="row">
                <div class="col-lg-12 text-center">
                    <h2>My Custom Snippet</h2>
                    <p>Content goes here...</p>
                </div>
            </div>
        </div>
    </section>
</template>

<!-- 2. Registration -->
<template id="s_my_snippet_insert" inherit_id="website.snippets">
    <xpath expr="//div[@id='snippet_structure']//t[@t-snippet][last()]" position="after">
        <t t-snippet="my_module.s_my_snippet"
           t-thumbnail="/my_module/static/src/img/snippets/s_my_snippet.svg">
            <keywords>my, custom, snippet</keywords>
        </t>
    </xpath>
</template>
```

### Odoo 18-19: With Snippet Groups (Required)

```xml
<!-- 1. Snippet Template (same as above) -->

<!-- 2. Custom Group (optional) -->
<template id="snippet_group_custom" inherit_id="website.snippets">
    <xpath expr="//div[@id='snippet_groups']" position="inside">
        <t snippet-group="custom"
           t-snippet="website.s_snippet_group"
           string="Custom Snippets"/>
    </xpath>
</template>

<!-- 3. Registration with Group -->
<template id="s_my_snippet_insert" inherit_id="website.snippets">
    <xpath expr="//div[@id='snippet_structure']/*[1]" position="before">
        <t t-snippet="my_module.s_my_snippet"
           string="My Snippet"
           group="custom"
           t-thumbnail="/my_module/static/src/img/snippets/s_my_snippet.svg"/>
    </xpath>
</template>
```

### Panel Categories

| Panel ID | Category | XPath |
|----------|----------|-------|
| `snippet_structure` | Structure | `//div[@id='snippet_structure']` |
| `snippet_media` | Gallery | `//div[@id='snippet_media']` |
| `snippet_feature` | Features | `//div[@id='snippet_feature']` |
| `snippet_dynamic` | Dynamic | `//div[@id='snippet_dynamic']` |
| `snippet_inner_content` | Inner Content | `//div[@id='snippet_inner_content']` |

---

## Snippet Options System

### We-* Elements

| Element | Purpose | Key Attributes |
|---------|---------|----------------|
| `we-select` | Dropdown | `data-name`, `data-dependencies` |
| `we-button` | Toggle | `data-select-class`, `data-toggle-class` |
| `we-colorpicker` | Color picker | `data-css-property` |
| `we-input` | Text/number | `data-attribute-name`, `data-unit` |
| `we-range` | Slider | `data-min`, `data-max`, `data-step` |
| `we-checkbox` | Toggle | `data-select-class` |

### Data Attributes

| Attribute | Purpose |
|-----------|---------|
| `data-selector` | Target CSS selector |
| `data-select-class` | Toggle CSS class |
| `data-css-property` | CSS property to modify |
| `data-js` | JavaScript handler class |
| `data-dependencies` | Conditional visibility |
| `data-no-preview` | Disable live preview |

### Complete Options Example

```xml
<template id="s_my_snippet_options" inherit_id="website.snippet_options">
    <xpath expr="." position="inside">
        <div data-js="MySnippetHandler"
             data-selector=".s_my_snippet"
             data-drop-in=".oe_structure">

            <we-select string="Layout" data-name="layout_opt">
                <we-button data-select-class="layout-grid">Grid</we-button>
                <we-button data-select-class="layout-list">List</we-button>
            </we-select>

            <we-colorpicker string="Background"
                            data-select-style="true"
                            data-css-property="background-color"/>

            <we-range string="Spacing"
                      data-select-style="true"
                      data-css-property="gap"
                      data-min="0" data-max="100" data-step="5" data-unit="px"/>
        </div>
    </xpath>
</template>
```

### Built-in JS Handlers

`BackgroundImage`, `BackgroundPosition`, `BackgroundToggler`, `ColoredLevelBackground`, `BackgroundShape`, `ImageTools`, `Carousel`, `DynamicSnippet`

---

## Dynamic Snippets

### Architecture

```
Data Source (ir.filters) → Filter (website.snippet.filter) → Display Template
```

### Creating a Dynamic Snippet

**Step 1: Define Filter**
```xml
<record id="dynamic_filter_my_items" model="website.snippet.filter">
    <field name="name">My Items</field>
    <field name="model_name">my.model</field>
    <field name="limit">12</field>
    <field name="filter_id" ref="ir_filter_my_items"/>
</record>
```

**Step 2: Display Template**
```xml
<template id="dynamic_filter_template_my_model_card" name="Card">
    <t t-foreach="records" t-as="record">
        <div class="col-lg-4 mb-4">
            <div class="card h-100 shadow-sm">
                <img t-att-src="record.image_url" class="card-img-top"/>
                <div class="card-body">
                    <h5 class="card-title" t-esc="record.name"/>
                </div>
            </div>
        </div>
    </t>
</template>
```

**Step 3: Dynamic Snippet**
```xml
<template id="s_dynamic_my_items" name="Dynamic My Items">
    <section class="s_dynamic_snippet s_dynamic_my_items pt48 pb48"
             data-snippet="s_dynamic_my_items"
             data-filter-id="my_module.dynamic_filter_my_items"
             data-template-key="my_module.dynamic_filter_template_my_model_card"
             data-number-of-elements="6">
        <div class="container">
            <div class="dynamic_snippet_template row"/>
        </div>
    </section>
</template>
```

### Product Dynamic Snippets (website_sale)

Filters: `dynamic_filter_newest_products`, `dynamic_filter_recently_sold_products`, `dynamic_filter_recently_viewed_products`

Display templates: `card_style`, `centered`, `horizontal_card`, `mini`, `minimalist_*`, `banner`

---

## Snippet JavaScript

### publicWidget for Snippets

```javascript
/** @odoo-module **/
import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.MySnippet = publicWidget.Widget.extend({
    selector: '.s_my_snippet',
    disabledInEditableMode: false,

    start: function () {
        if (!this.editableMode) {
            this._initializeAnimations();
        }
        return this._super(...arguments);
    },

    destroy: function () {
        $(window).off('.mySnippet');
        this._super(...arguments);
    },
});
```

### Snippet Options Handler

```javascript
/** @odoo-module **/
import options from "@web_editor/js/editor/snippets.options";

options.registry.MySnippetOption = options.Class.extend({
    selectDataAttribute: function(previewMode, widgetValue, params) {
        this._super(...arguments);
        if (params.attributeName === 'layout') {
            this._applyLayout(widgetValue);
        }
    },
});
```

---

## Version Differences

| Feature | Odoo 14-17 | Odoo 18-19 |
|---------|-----------|-----------|
| Registration | Simple XPath | Groups required |
| JavaScript | `@odoo-module` | Plugin-based (19) |
| Bootstrap | 4.x (14-15) / 5.1.3 (16-17) | 5.1.3 |
| Dynamic Snippets | Basic | Full + Categories |

### Odoo 19 Plugin Pattern

```javascript
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

export class MySnippetPlugin extends Plugin {
    static id = "mySnippet";
    resources = {
        builder_options: [{
            template: "my_module.MySnippetOption",
            selector: "section",
            applyTo: ".s_my_snippet",
        }],
    };
}
registry.category("website-plugins").add("mySnippet", MySnippetPlugin);
```
