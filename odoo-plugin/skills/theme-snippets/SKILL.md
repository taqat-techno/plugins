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
license: "MIT"
metadata:
  version: "8.0.0"
  author: "TaqaTechno"
  allowed-tools: "Read, Write, Edit, Bash, Grep, Glob"
---

# Odoo Website Snippets

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

For the full 81+ snippet catalog, options reference, and dynamic snippet details, see **REFERENCE.md** in this skill directory.

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
<!-- 1. Custom Group (optional) -->
<template id="snippet_group_custom" inherit_id="website.snippets">
    <xpath expr="//div[@id='snippet_groups']" position="inside">
        <t snippet-group="custom"
           t-snippet="website.s_snippet_group"
           string="Custom Snippets"/>
    </xpath>
</template>

<!-- 2. Registration with Group -->
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

## Snippet JavaScript (publicWidget)

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

---

## Version Differences

For complete version mapping, see `data/version_mapping.json`.

**Key differences by version**:
- Odoo 14-17: Simple XPath snippet registration
- Odoo 18-19: Groups required, plugin-based JS (Odoo 19), full dynamic snippet categories

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
