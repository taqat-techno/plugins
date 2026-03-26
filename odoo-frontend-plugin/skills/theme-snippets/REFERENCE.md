# Snippet Reference -- Full Catalog & Options System

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
Data Source (ir.filters) -> Filter (website.snippet.filter) -> Display Template
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

## Snippet Options Handler (JavaScript)

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
