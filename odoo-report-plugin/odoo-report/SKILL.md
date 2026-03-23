---
name: odoo-report
description: |
  Professional Odoo Email Templates & QWeb Reports - Complete toolkit for creating, managing, and debugging email templates and PDF reports across Odoo 14-19. Includes wkhtmltopdf setup, Arabic/RTL support, bilingual patterns, and comprehensive validation.


  <example>
  Context: User wants to create an email template
  user: "Create an invoice confirmation email template in Odoo 17"
  assistant: "I will use the odoo-report skill to create a mail.template record with QWeb body, dynamic fields, and correct ir.attachment handling."
  <commentary>Core trigger - new email template creation.</commentary>
  </example>

  <example>
  Context: User wants a PDF report
  user: "Design a QWeb PDF report for purchase orders"
  assistant: "I will use the odoo-report skill to create a report action, QWeb template with page layout, header/footer, and register it in the module manifest."
  <commentary>PDF report workflow trigger.</commentary>
  </example>

  <example>
  Context: User has a broken email template
  user: "My email template is sending plain text instead of HTML"
  assistant: "I will use the odoo-report skill to diagnose the template body_html field, check subtype_id, and verify the mail.template arch is structured correctly for HTML rendering."
  <commentary>Debugging trigger - email template not rendering correctly.</commentary>
  </example>

  <example>
  Context: User wants to analyze a template
  user: "Analyze this email template for issues and improvements"
  assistant: "I will use the odoo-report skill to check template structure, context variables, rendering patterns, and suggest improvements."
  <commentary>Analyze trigger - template quality review.</commentary>
  </example>

  <example>
  Context: User wants to migrate templates between versions
  user: "Migrate my templates from Odoo 14 to 17"
  assistant: "I will use the odoo-report skill to apply version-specific transformations: t-esc to t-out, report_template to report_template_ids, and add template_category."
  <commentary>Migration trigger - version upgrade.</commentary>
  </example>

  <example>
  Context: User wants pre-deployment validation
  user: "Validate my QWeb report template before deployment"
  assistant: "I will check syntax, context variable usage, security patterns, and version compatibility."
  <commentary>Validate trigger - pre-deployment template check.</commentary>
  </example>

  <example>
  Context: User wants to see templates
  user: "List all email templates for sale.order in my module"
  assistant: "I will scan the module for mail.template and ir.actions.report records targeting the sale.order model."
  <commentary>List trigger - template discovery.</commentary>
  </example>

  <example>
  Context: User wants to preview output
  user: "Preview this email template with sample data"
  assistant: "I will generate a preview using the template's QWeb expressions with realistic sample context variables."
  <commentary>Preview trigger - template output preview.</commentary>
  </example>

  <example>
  Context: User wants automatic fixes
  user: "Fix common issues in my email template"
  assistant: "I will apply safe transformations to fix encoding, missing fields, broken QWeb expressions, and version-specific syntax."
  <commentary>Fix trigger - auto-fix template issues.</commentary>
  </example>
version: "2.1.0"
author: "TaqaTechno"
license: "LGPL-3"
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - Glob
  - Grep
  - WebFetch
metadata:
  filePattern:
    - "**/data/mail_template*.xml"
    - "**/data/*email*.xml"
    - "**/report*/**/*.xml"
    - "**/reports/**/*.xml"
    - "**/__manifest__.py"
  bashPattern:
    - "wkhtmltopdf"
  supported-versions: ["14", "15", "16", "17", "18", "19"]
---

# Odoo Email Templates & QWeb Reports Skill (v2.1)

A skill for creating, managing, debugging, and migrating Odoo email templates and QWeb reports across versions 14-19.

## Workflows

This skill handles all template and report workflows via natural language:

| What you want | What to say |
|---------------|-------------|
| Create email template | "Create an email template for sale.order quotation" |
| Create QWeb PDF report | "Create a QWeb PDF report for purchase.order" |
| Migrate templates | "Migrate this template from Odoo 14 to 17" |
| Analyze template | "Analyze this template for issues" |
| Debug rendering | "Debug why my email shows plain text" |
| Fix template | "Fix the broken QWeb expressions" |
| Validate before deploy | "Validate this template before deployment" |
| List templates | "List all templates for sale.order" |
| Preview output | "Preview this email template" |

## Configuration

- **Supported Versions**: Odoo 14, 15, 16, 17, 18, 19
- **Core Model**: `mail.template`
- **Rendering Engines**: inline_template (Jinja2-like) for headers, QWeb for body_html

**User overrides**: Check for `odoo-report.local.md` in the project `.claude/` directory. If found, use its YAML frontmatter settings (default_version, author, default_layout) as defaults.

---

## Template Architecture

```
mail.template
├── Inherits: mail.render.mixin (rendering engine)
├── Inherits: template.reset.mixin (reset - Odoo 16+)
│
├── Header Fields (inline_template engine):
│   subject, email_from, email_to, email_cc, reply_to, partner_to
│
├── Content Fields (QWeb engine):
│   body_html
│
├── Attachment Fields:
│   attachment_ids (static)
│   report_template (Odoo 14-16) / report_template_ids (Odoo 17+)
│   report_name (dynamic filename)
│
└── Configuration:
    email_layout_xmlid, auto_delete, mail_server_id,
    use_default_to, scheduled_date, template_category (16+)
```

### Rendering Flow

```
mail.template.send_mail_batch(res_ids)
  ├─► _generate_template(res_ids, render_fields)
  │     ├─► _classify_per_lang()
  │     ├─► _render_field() per field (inline_template or qweb)
  │     ├─► _generate_template_recipients()
  │     ├─► _generate_template_attachments() (static + PDF report)
  │     └─► Return rendered values dict
  ├─► Create mail.mail records
  ├─► Apply email_layout_xmlid (if set)
  └─► Send via mail_server_id or default
```

---

## Two Rendering Engines

### 1. Inline Template (Jinja2-like)

**Used for**: subject, email_from, email_to, email_cc, reply_to, partner_to, lang, scheduled_date

```python
{{ object.name }}
{{ object.partner_id.name }}
{{ (object.user_id.email_formatted or user.email_formatted) }}
{{ object.state == 'draft' and 'Quotation' or 'Order' }}
{{ ctx.get('proforma') and 'Proforma' or '' }}
```

### 2. QWeb Engine

**Used for**: body_html

```xml
<!-- Output (use t-out for Odoo 15+, t-esc for Odoo 14) -->
<t t-out="object.name"/>
<t t-out="format_amount(object.amount_total, object.currency_id)"/>

<!-- Conditionals -->
<t t-if="object.state == 'draft'">Draft</t>
<t t-elif="object.state == 'sent'">Sent</t>
<t t-else="">Confirmed</t>

<!-- Loops -->
<t t-foreach="object.order_line" t-as="line">
    <tr><td t-out="line.name"/></tr>
</t>

<!-- Dynamic attributes -->
<a t-att-href="object.get_portal_url()">View</a>
```

---

## Version Decision Matrix

| Feature | 14 | 15 | 16 | 17 | 18 | 19 |
|---------|:--:|:--:|:--:|:--:|:--:|:--:|
| Output tag | `t-esc` | `t-out` | `t-out` | `t-out` | `t-out` | `t-out` |
| `report_template` (M2O) | Y | Y | Y | - | - | - |
| `report_template_ids` (M2M) | - | - | - | Y | Y | Y |
| `template_category` | - | - | Y | Y | Y | Y |
| Company branding colors | - | - | - | - | - | Y |
| `format_datetime()` | - | Y | Y | Y | Y | Y |
| `is_html_empty()` | - | - | Y | Y | Y | Y |

### Version Detection Priority

1. User-specified `--version` flag
2. Directory path (`odoo14`, `odoo17`, etc.)
3. `__manifest__.py` version string (e.g., `'17.0.1.0.0'`)
4. Ask user if ambiguous

---

## Email Layout Templates

| Layout | Width | Use Case |
|--------|-------|----------|
| `mail.mail_notification_layout` | 900px | Full notifications with header/footer |
| `mail.mail_notification_light` | 590px | Simple notifications |
| `mail.mail_notification_layout_with_responsible_signature` | 900px | Uses record's `user_id` signature (16+) |

---

## Best Practices

### 1. Always Use Fallbacks
```xml
<t t-out="object.partner_id.name or 'Valued Customer'"/>
```

### 2. Use Format Helpers
```xml
<t t-out="format_amount(object.amount_total, object.currency_id)"/>
<t t-out="format_date(object.date_order)"/>
```

### 3. Use Layouts for Consistency
```xml
<field name="email_layout_xmlid">mail.mail_notification_layout</field>
```

### 4. Handle Empty HTML (16+)
```xml
<t t-if="not is_html_empty(object.description)">
    <div t-out="object.description"/>
</t>
```

### 5. Version-Appropriate Output
```xml
<!-- Odoo 15+ --> <t t-out="value"/>
<!-- Odoo 14 -->  <t t-esc="value"/>
```

### 6. Report Attachment by Version
```xml
<!-- Odoo 14-16 -->
<field name="report_template" ref="module.report_action"/>
<!-- Odoo 17+ -->
<field name="report_template_ids" eval="[(4, ref('module.report_action'))]"/>
```

### 7. Email Tables for Compatibility
```xml
<!-- Email clients require table-based layout with inline styles -->
<table border="0" cellpadding="0" cellspacing="0" width="100%">
    <tr><td style="padding: 20px;">Content</td></tr>
</table>
```

### 8. Safe Dynamic Filenames
```xml
<field name="report_name">{{ (object.name or 'Document').replace('/', '-') }}</field>
```

---

## wkhtmltopdf (Required for PDF Reports)

### Installation
```bash
# Windows
winget install wkhtmltopdf.wkhtmltox

# Ubuntu/Debian
sudo apt-get install wkhtmltopdf

# macOS
brew install wkhtmltopdf
```

### Odoo Configuration (MANDATORY)
```ini
[options]
bin_path = C:\Program Files\wkhtmltopdf\bin   # Windows
# bin_path = /usr/local/bin                    # Linux
```

### Key Limitation: OFFLINE Mode

wkhtmltopdf runs WITHOUT network access:
- Google Fonts CDN will NOT load
- External images will NOT render
- Use `web.external_layout` for fonts
- Use system fonts: `'DejaVu Sans', 'Arial', sans-serif`

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `Unable to find Wkhtmltopdf` | bin_path not configured | Add bin_path to odoo.conf |
| PDF generation timeout | External resources requested | Remove CDN URLs |
| Blank PDF generated | CSS/SCSS errors | Validate SCSS syntax |
| Exit with code 1 | HTML syntax error | Validate QWeb XML |

---

## Arabic/RTL Support

### MANDATORY Template Wrapper for Non-Latin Text

```xml
<template id="report_document">
    <t t-call="web.html_container">        <!-- Provides UTF-8 meta tag -->
        <t t-foreach="docs" t-as="o">
            <t t-call="web.external_layout"> <!-- Loads proper fonts -->
                <div class="page">
                    <!-- Content here -->
                </div>
            </t>
        </t>
    </t>
</template>
```

Without `web.html_container`, Arabic text displays as `ÙØ§ØªÙˆØ±Ø©` (UTF-8 bytes read as Latin-1).

### Bilingual Labels
```xml
<th style="background: #1a5276; color: white; padding: 12px;">
    Date | التاريخ
</th>
```

### RTL Alignment
```xml
<div style="direction: rtl; text-align: right;">
    يرجى إرسال حوالاتكم على الحساب المذكور أعلاه
</div>
```

---

## Report SCSS Styling

### Asset Bundle
```python
'assets': {
    'web.report_assets_common': [
        'module/static/src/scss/report_styles.scss',
    ],
},
```

### Google Fonts Pitfall
```scss
// BROKEN - Semicolons in URL break SCSS parsing
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap');

// FIXED - Use weight range syntax
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300..700&display=swap');

// BEST - Don't use Google Fonts (wkhtmltopdf is offline!)
```

### Recommended Font Stack
```scss
$report-font-family: 'DejaVu Sans', 'Arial', 'Helvetica', sans-serif;
```

---

## Paper Format Configuration

```xml
<record id="paperformat_custom" model="report.paperformat">
    <field name="name">Custom A4</field>
    <field name="format">A4</field>
    <field name="orientation">Portrait</field>
    <field name="margin_top">20</field>
    <field name="margin_bottom">20</field>
    <field name="margin_left">15</field>
    <field name="margin_right">15</field>
    <field name="header_line" eval="False"/>
    <field name="dpi">90</field>
</record>
```

Link to report: `<field name="paperformat_id" ref="module.paperformat_custom"/>`

| Format | Dimensions | Use Case |
|--------|------------|----------|
| A4 | 210 x 297 mm | Standard international |
| Letter | 216 x 279 mm | US standard |
| Legal | 216 x 356 mm | Legal documents |
| Landscape | Any + `Landscape` | Wide tables, charts |

---

## Debug Workflow

When diagnosing report or template issues, follow this order:

1. **Infrastructure**: wkhtmltopdf installed? bin_path in odoo.conf? Server restarted?
2. **Template structure**: web.html_container → web.external_layout → div.page?
3. **Report action**: report_name matches template id? binding_model_id correct?
4. **Shell test**: `env.ref('module.report_action')._render_qweb_pdf([record_id])`
5. **Browser cache**: Clear cache (Ctrl+Shift+R)

---

## Reference Files

When working on specific tasks, read these files from the plugin directory for deeper context:

### For template creation
- **Pattern selection by purpose/model**: `memories/template_patterns.md`
- **Starter email XML**: `templates/email/basic_notification.xml`, `templates/email/document_email.xml`
- **Starter report XML**: `templates/qweb/basic_report.xml`, `templates/qweb/table_report.xml`
- **Field definitions**: `data/template_fields.json`
- **Context variables by version**: `data/context_variables.json`
- **Layout options**: `data/layouts.json`

### For version decisions
- **Version routing rules and migration paths**: `memories/version_routing.md`
- **Version detection logic and feature map**: `helpers/version_helper.md`

### For validation
- **Pre-flight validation checklist**: `validators/template_validator.md`

### For QWeb quality
- **Safety, performance, email/report guidelines**: `memories/qweb_best_practices.md`

### For module-specific templates
- **Known Odoo template IDs by module**: `data/module_templates.md`

---

## Migration Reference

### Automatic Transformations

| From → To | Transformation |
|-----------|---------------|
| 14 → 15+ | `t-esc` → `t-out`, `t-raw` → `t-out` |
| 14-16 → 17+ | `report_template` → `report_template_ids` with `eval="[(4, ref(...))]"` |
| Any → 16+ | Add `template_category` field |
| Any → 19 | Add company branding: `company.email_secondary_color`, `company.email_primary_color` |

### Migration Workflow

1. Detect source version (syntax heuristics or directory name)
2. Create backup: `{file}.bak`
3. Apply transformations in order
4. Validate migrated XML
5. Show diff summary

For full migration matrix and rules, read `memories/version_routing.md`.

---

## Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `AttributeError: 'NoneType' has no attribute 'name'` | Null field access | Use `object.field.name or ''` |
| `QWebException: t-esc is deprecated` | Old syntax in 15+ | Replace `t-esc` with `t-out` |
| `KeyError: 'format_amount'` | Missing context helper | Ensure `mail.render.mixin` inherited |
| `ValidationError: Invalid XML` | Malformed QWeb | Check tag closure |
| Arabic text as `ÙØ§ØªÙˆØ±Ø©` | Missing web.html_container | Add UTF-8 wrapper |
| Blank PDF | wkhtmltopdf not found or CSS error | Check bin_path, validate SCSS |
