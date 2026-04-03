---
name: frontend-js
description: |
  Odoo frontend JavaScript patterns for website themes. Covers publicWidget framework (complete pattern with editableMode handling), Owl v1/v2 component patterns, _t() translation best practices, Bootstrap 4-to-5 migration, version detection, and critical development rules. Supports Odoo 14-19.

  <example>
  Context: User wants to create a publicWidget
  user: "Create a publicWidget for my Odoo website"
  assistant: "I will create a publicWidget with editableMode handling and proper cleanup."
  <commentary>publicWidget creation.</commentary>
  </example>

  <example>
  Context: User asks about Owl components
  user: "How do I create an Owl component in Odoo 18?"
  assistant: "I will show the Owl v2 pattern with static template and props."
  <commentary>Owl component pattern.</commentary>
  </example>

  <example>
  Context: User needs help with translations
  user: "How do I translate JavaScript strings in Odoo?"
  assistant: "Use _t() at DEFINITION TIME for static labels, not runtime wrappers."
  <commentary>Translation best practices.</commentary>
  </example>

  <example>
  Context: User migrating Bootstrap classes
  user: "Convert Bootstrap 4 classes to Bootstrap 5 for Odoo 17"
  assistant: "Replace ml-* with ms-*, mr-* with me-*, text-left with text-start."
  <commentary>Bootstrap migration.</commentary>
  </example>
license: "MIT"
metadata:
  version: "8.0.0"
  author: "TaqaTechno"
  allowed-tools: "Read, Write, Edit, Bash, Grep, Glob"
---

# Odoo Frontend JavaScript Patterns

## Critical Rules

1. **Website themes**: Use `publicWidget` framework ONLY — NOT Owl or vanilla JS
2. **JS modules**: Start every file with `/** @odoo-module **/`
3. **No inline JS/CSS**: Always separate files in `static/src/js/` and `static/src/scss/`
4. **Bootstrap**: v5.1.3 for Odoo 16+ (never Tailwind)
5. **Translations**: Use `_t()` at DEFINITION TIME for static JS labels

## Version Detection

For complete version mapping (Odoo → Bootstrap → Owl → JavaScript), see `data/version_mapping.json`.

**Quick reference**: Bootstrap 4.x for Odoo 14-15, Bootstrap 5.1.3 for Odoo 16+. Owl v2 for Odoo 18+.

Detect from path (`odoo17/` → v17), manifest version field, or config file.

---

## publicWidget Pattern (REQUIRED for Themes)

**Use for**: Website interactions, theme functionality, animations, forms

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
     * CRITICAL: Check editableMode for website builder compatibility
     */
    start: function () {
        if (!this.editableMode) {
            this._initializeAnimation();
            this._bindExternalEvents();
        }
        return this._super.apply(this, arguments);
    },

    _initializeAnimation: function () {
        this.$el.addClass('animated');
    },

    _bindExternalEvents: function () {
        $(window).on('scroll.myWidget', this._onScroll.bind(this));
        $(window).on('resize.myWidget', this._onResize.bind(this));
    },

    _onClick: function (ev) {
        ev.preventDefault();
        if (this.editableMode) return;
        // Handler logic
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

### Key Points

1. **ALWAYS check `this.editableMode`** before animations/interactions
2. **`disabledInEditableMode: false`** makes widgets work in website builder
3. **ALWAYS clean up** event listeners in `destroy()`
4. **NEVER use Owl or vanilla JS** for website themes
5. Use **namespaced events** (`.myWidget`) for easy cleanup

### Include in Manifest

```python
'assets': {
    'web.assets_frontend': [
        'module_name/static/src/js/my_widget.js',
    ],
}
```

---

## Owl Component Pattern

### Odoo 17 (Owl v1)

```javascript
/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";

class MyComponent extends Component {
    setup() {
        this.state = useState({ items: [], loading: false });
    }

    async willStart() {
        await this.loadData();
    }
}

MyComponent.template = "module_name.MyComponentTemplate";
registry.category("public_components").add("MyComponent", MyComponent);
```

### Odoo 18-19 (Owl v2 — Breaking Changes)

```javascript
/** @odoo-module **/

import { Component, useState } from "@odoo/owl";

class MyComponent extends Component {
    static template = "module_name.MyComponentTemplate";  // Static property
    static props = {
        title: { type: String, optional: true },
        items: { type: Array },
    };

    setup() {
        this.state = useState({ selectedId: null });
    }
}
```

### XML Template

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

---

## Translation (_t) Best Practices

### CORRECT — Wrap at DEFINITION TIME

```javascript
/** @odoo-module **/
import { _t } from "@web/core/l10n/translation";

// Static labels wrapped where defined
const MONTHS = [
    {value: 1, short: _t("Jan"), full: _t("January")},
    {value: 2, short: _t("Feb"), full: _t("February")},
    // ...
];

const STATUS_LABELS = {
    draft: _t("Draft"),
    pending: _t("Pending"),
    approved: _t("Approved"),
};
```

### WRONG — Runtime wrappers DON'T WORK

```javascript
// WRONG: Strings without _t() at definition
const MONTHS = [{value: 1, label: "Jan"}]; // NOT found by PO extractor!

// WRONG: Variable passed to _t() at runtime
translateLabel(key) {
    return _t(key);  // PO extractor can't find string literals
}
```

### When to use _t()

| Use _t() | Don't use _t() |
|----------|----------------|
| Static labels in JS arrays/objects | Static text in XML templates (auto-translated) |
| Error messages in JS constants | Dynamic variables passed at runtime |
| User-facing strings defined in JS | Hardcoded strings in .xml files |

---

## Bootstrap 4 → 5 Migration (Odoo 14/15 → 16+)

### Class Replacements

| Bootstrap 4 | Bootstrap 5 |
|-------------|-------------|
| `ml-*` | `ms-*` (margin-start) |
| `mr-*` | `me-*` (margin-end) |
| `pl-*` | `ps-*` (padding-start) |
| `pr-*` | `pe-*` (padding-end) |
| `text-left` | `text-start` |
| `text-right` | `text-end` |
| `float-left` | `float-start` |
| `float-right` | `float-end` |
| `form-group` | `mb-3` |
| `custom-select` | `form-select` |
| `close` | `btn-close` |
| `badge-*` | `bg-*` |
| `font-weight-bold` | `fw-bold` |
| `sr-only` | `visually-hidden` |
| `no-gutters` | `g-0` |

### Data Attributes

| Bootstrap 4 | Bootstrap 5 |
|-------------|-------------|
| `data-toggle` | `data-bs-toggle` |
| `data-target` | `data-bs-target` |
| `data-dismiss` | `data-bs-dismiss` |

### Removed Classes (find alternatives)

- `form-inline` → Use grid/flex utilities
- `jumbotron` → Recreate with utilities
- `media` → Use `d-flex` with flex utilities

---

## SCSS Bootstrap Overrides

**File**: `static/src/scss/bootstrap_overridden.scss`
**Bundle**: `web._assets_frontend_helpers`

```scss
@import "~bootstrap/scss/functions";
@import "~bootstrap/scss/variables";

$spacer: 1rem !default;
$border-radius: 0.25rem !default;
$border-radius-lg: 0.5rem !default;
$box-shadow: 0 .5rem 1rem rgba(0, 0, 0, .15) !default;
```

Use `!default` flag on all overrides.

---

## Version-Specific Notes

### Odoo 17

- Owl v1: template as separate property
- Snippet registration: simple XPath
- Import: `@web/legacy/js/public/public_widget`

### Odoo 18-19

- Owl v2: static template, props validation
- Snippet groups required
- Website builder: plugin architecture (Odoo 19)
- Breaking: `type='json'` → `type='jsonrpc'` in controllers
