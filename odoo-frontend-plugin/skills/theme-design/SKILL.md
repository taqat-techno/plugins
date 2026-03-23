---
name: theme-design
description: |
  Figma-to-Odoo design workflow and complete page template reference. Covers Figma extraction pipeline (colors, typography, layout), Chrome MCP automation, design-to-template matching methodology, header/footer decision flowcharts, and dynamic page reference (11 headers, 9 footers, shop, blog, cart templates with XML IDs).

  <example>
  Context: User wants to implement a Figma design
  user: "Implement this Figma design as an Odoo 17 theme"
  assistant: "I will analyze the Figma design and match it to Odoo templates."
  <commentary>Design-to-code workflow.</commentary>
  </example>

  <example>
  Context: User asks which header template to use
  user: "Which Odoo header template matches a hamburger menu design?"
  assistant: "Use template_header_hamburger."
  <commentary>Template matching query.</commentary>
  </example>

  <example>
  Context: User wants to know footer options
  user: "What footer templates are available in Odoo?"
  assistant: "There are 9 footer templates ranging from default to slideout."
  <commentary>Footer template reference.</commentary>
  </example>
version: "8.0.0"
author: "TaqaTechno"
license: "MIT"
allowed-tools:
  - Read
  - Grep
  - Glob
  - WebFetch
---

# Figma-to-Odoo Design Workflow

## Design Workflow Methodology

```
1. ANALYZE DESIGN → Extract colors, fonts, layout, components
2. COMPARE TO ODOO TEMPLATES → Match header, footer, page layouts
3. CHOOSE CLOSEST TEMPLATE → Select best matching built-in template
4. CONFIGURE VIA VARIABLES → Set $o-website-values-palettes
5. ENHANCE WITH CUSTOM CSS → Only what templates can't provide
6. CREATE CUSTOM SNIPPETS → Components not available in Odoo
```

## Figma Extraction Pipeline

### Using Figma MCP

```
1. Use Figma MCP with prompt:
   "Convert this Figma design to HTML for Odoo <version> website theme.
   Use Bootstrap v5.1.3 classes (not Tailwind).
   Apply proper Odoo theme structure with sections and containers."

2. Extract Color Palette:
   "Extract the color palette and map to o-color-1 through o-color-5."

3. Extract Typography:
   "Convert text styling to Bootstrap typography classes."
```

### Using Chrome MCP (Browser Automation)

1. Navigate to Figma URL → Open **Pages** (not components!)
2. Click on page elements to extract:
   - Header/navbar → primary color
   - CTA buttons → secondary color
   - Section backgrounds → o-color-3
   - Body text → text color, font family
   - Headings (H1-H6) → heading fonts, sizes

**Pages to check**: Homepage, About/Services, Contact, Footer area

### Color Mapping

| Design Element | Maps To |
|---------------|---------|
| Primary brand color (buttons, links) | `o-color-1` |
| Accent/CTA color | `o-color-2` |
| Light section backgrounds | `o-color-3` |
| Main content background | `o-color-4` |
| Dark text / headings | `o-color-5` |

---

## Header Templates (11 Primary + Variants)

| XML ID | Name | Best For |
|--------|------|----------|
| `website.template_header_default` | Default | Most websites |
| `website.template_header_hamburger` | Hamburger | Minimal designs |
| `website.template_header_stretch` | Stretch | Wide layouts |
| `website.template_header_vertical` | Vertical | App-like sites |
| `website.template_header_search` | Search | E-commerce, directories |
| `website.template_header_sales_one` | Sales 1 | Online stores |
| `website.template_header_sales_two` | Sales 2 | Large catalogs |
| `website.template_header_sales_three` | Sales 3 | Product-focused |
| `website.template_header_sales_four` | Sales 4 | Fashion, retail |
| `website.template_header_sidebar` | Sidebar | Dashboard sites |
| `website.template_header_boxed` | Boxed | Modern brands |

### Header Alignment Variants
- `..._align_center` / `..._align_right` — Desktop alignment
- `..._mobile_align_center` / `..._mobile_align_right` — Mobile alignment

### Header Visibility (mutually exclusive)

| XML ID | Effect |
|--------|--------|
| `website.header_visibility_standard` | Scrolls with page |
| `website.header_visibility_fixed` | Sticks to top |
| `website.header_visibility_disappears` | Hides on scroll down |
| `website.header_visibility_fade_out` | Fades out |

### Header Components (combinable)

| XML ID | Component | Default |
|--------|-----------|---------|
| `website.option_header_brand_logo` | Logo image | Active |
| `website.option_header_brand_name` | Text name | Inactive |
| `website.header_call_to_action` | CTA button | Active |
| `website.header_search_box` | Search bar | Active |
| `website.header_social_links` | Social icons | Inactive |

### Header Decision Flowchart

```
Is navigation hidden? → YES → template_header_hamburger
                       → NO → Vertical sidebar? → YES → Full page? → sidebar / vertical
                                                 → NO → E-commerce? → YES → Categories? → sales_two / sales_one
                                                                    → NO → Search prominent? → template_header_search
                                                                                             → Boxed? → boxed / stretch / default
```

---

## Footer Templates (9 Options)

| XML ID | Name | Best For |
|--------|------|----------|
| `website.footer_custom` | Default | General use |
| `website.template_footer_descriptive` | Descriptive | Corporate sites |
| `website.template_footer_centered` | Centered | Landing pages |
| `website.template_footer_links` | Links | Large sites |
| `website.template_footer_minimalist` | Minimalist | Clean designs |
| `website.template_footer_contact` | Contact | Service businesses |
| `website.template_footer_call_to_action` | CTA | Marketing sites |
| `website.template_footer_headline` | Headline | Brand statements |
| `website.template_footer_slideout` | Slideout | Modern/trendy |

### Footer Decision Flowchart

```
Minimal (just copyright)? → YES → template_footer_minimalist
                          → NO → Center-aligned? → template_footer_centered
                                 Newsletter/CTA? → template_footer_call_to_action
                                 Contact info? → template_footer_contact
                                 Primarily links? → template_footer_links
                                 Detailed description? → template_footer_descriptive
                                 Default → footer_custom
```

---

## Shop Page Templates (website_sale)

### Layout Options

| XML ID | Feature |
|--------|---------|
| `website_sale.products_design_card` | Card layout |
| `website_sale.products_design_grid` | Grid layout |
| `website_sale.products_thumb_4_3` | 4:3 image ratio |
| `website_sale.products_thumb_cover` | Image fills container (default) |

### Categories & Filters

| XML ID | Feature | Default |
|--------|---------|---------|
| `website_sale.products_categories` | Left sidebar | Inactive |
| `website_sale.products_categories_top` | Top nav | Active |
| `website_sale.products_attributes` | Attribute filters | Active |
| `website_sale.filter_products_price` | Price filter | Inactive |
| `website_sale.search` | Search box | Active |
| `website_sale.sort` | Sort dropdown | Active |

### Product Detail Options

| XML ID | Feature | Default |
|--------|---------|---------|
| `website_sale.product_comment` | Reviews | Inactive |
| `website_sale.product_buy_now` | Buy Now button | Inactive |
| `website_sale.alternative_products` | Alternatives | Active |

---

## Blog Templates (website_blog)

### Blog Listing

| XML ID | Feature | Default |
|--------|---------|---------|
| `website_blog.opt_blog_cover_post` | Featured banner | Active |
| `website_blog.opt_blog_list_view` | List view | Inactive |
| `website_blog.opt_blog_cards_design` | Card components | Inactive |
| `website_blog.opt_blog_sidebar_show` | Sidebar | Inactive |

### Blog Post Detail

| XML ID | Feature | Default |
|--------|---------|---------|
| `website_blog.opt_blog_post_breadcrumb` | Breadcrumbs | Active |
| `website_blog.opt_blog_post_read_next` | Read next | Active |
| `website_blog.opt_blog_post_comment` | Comments | Inactive |

---

## Cart & Checkout

| XML ID | Feature | Default |
|--------|---------|---------|
| `website_sale.suggested_products_list` | Suggested products | Active |
| `website_sale.reduction_code` | Promo code | Active |
| `website_sale.accept_terms_and_conditions` | T&C checkbox | Inactive |

---

## Generating Theme Configuration from Design

After analyzing the design and matching templates:

```scss
// primary_variables.scss — Generated from Design Analysis
$o-theme-font-configs: (
    'Poppins': (
        'family': ('Poppins', sans-serif),
        'url': 'Poppins:300,400,500,600,700',
    ),
);

$o-website-values-palettes: (
    (
        'color-palettes-name': 'default-1',
        'font': 'Poppins',
        'headings-font': 'Poppins',
        'header-template': 'hamburger',
        'header-links-style': 'pills',
        'logo-height': 48px,
        'footer-template': 'contact',
        'footer-scrolltop': true,
        'btn-padding-y': 0.75rem,
        'btn-border-radius': 8px,
        'link-underline': 'never',
    )
);
```

Then create `theme.utils` to activate the matched templates programmatically:

```python
def _theme_yourtheme_post_copy(self, mod):
    self.enable_view('website.template_header_hamburger')
    self.enable_view('website.template_footer_contact')
    self.enable_view('website.option_header_brand_logo')
    self.disable_view('website.header_visibility_standard')
    self.enable_view('website.header_visibility_fixed')
```
