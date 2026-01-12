---
name: odoo-report
description: "Professional Odoo Email Templates & QWeb Reports - Complete toolkit for creating, managing, and debugging email templates and PDF reports across Odoo 14-19. Provides smart pattern-based template generation, version-aware syntax, and comprehensive validation."
version: "1.0.0"
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
  mode: "codebase"
  supported-versions: ["14", "15", "16", "17", "18", "19"]
  primary-version: "17"
  template-patterns: "50+"
  qweb-patterns: "30+"
  categories:
    - email-templates
    - qweb-reports
    - pdf-generation
    - mail-template
    - notification-layouts
---

# Odoo Email Templates & QWeb Reports Skill (v1.0)

A comprehensive skill for creating, managing, debugging, and migrating Odoo email templates and QWeb reports across versions 14-19 with intelligent pattern recognition and version-aware syntax.

## Configuration

- **Supported Versions**: Odoo 14, 15, 16, 17, 18, 19
- **Primary Version**: Odoo 17
- **Templates Database**: 400+ templates analyzed
- **Pattern Library**: 50+ email patterns, 30+ QWeb patterns
- **Core Model**: `mail.template`
- **Rendering Engines**: inline_template (Jinja2), QWeb

---

## Quick Reference

### Template Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     ODOO EMAIL TEMPLATE ARCHITECTURE                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  mail.template                                                               │
│  ├── Inherits: mail.render.mixin (rendering engine)                          │
│  ├── Inherits: template.reset.mixin (reset - Odoo 16+)                       │
│  │                                                                           │
│  ├── Header Fields (inline_template engine):                                 │
│  │   • subject        • email_from       • email_to                          │
│  │   • email_cc       • reply_to         • partner_to                        │
│  │                                                                           │
│  ├── Content Fields (QWeb engine):                                           │
│  │   • body_html                                                             │
│  │                                                                           │
│  ├── Attachment Fields:                                                      │
│  │   • attachment_ids (static)                                               │
│  │   • report_template (Odoo 14-16) / report_template_ids (Odoo 17+)        │
│  │   • report_name (dynamic filename)                                        │
│  │                                                                           │
│  └── Configuration:                                                          │
│      • email_layout_xmlid   • auto_delete    • mail_server_id               │
│      • use_default_to       • scheduled_date                                 │
│                                                                               │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Rendering Flow

```
mail.template.send_mail_batch(res_ids)
    │
    ├─► _generate_template(res_ids, render_fields)
    │       │
    │       ├─► _classify_per_lang()        # Group by language
    │       │
    │       ├─► _render_field() for each:
    │       │       • subject (inline_template)
    │       │       • body_html (qweb)
    │       │       • email_from, email_to, etc.
    │       │
    │       ├─► _generate_template_recipients()
    │       │
    │       ├─► _generate_template_attachments()
    │       │       • Static attachments
    │       │       • Report PDF generation
    │       │
    │       └─► Return rendered values dict
    │
    ├─► Create mail.mail records
    │
    ├─► Apply email_layout_xmlid (if set)
    │       └─► ir.qweb._render(layout_xmlid, context)
    │
    └─► Send via mail_server_id or default
```

---

## Two Rendering Engines

### 1. Inline Template Engine (Jinja2-like)

**Used for**: `subject`, `email_from`, `email_to`, `email_cc`, `reply_to`, `partner_to`, `lang`, `scheduled_date`

```python
# Simple field access
{{ object.name }}
{{ object.partner_id.name }}
{{ object.company_id.name }}

# Method calls
{{ object.get_portal_url() }}
{{ object.email_formatted }}

# Conditional expressions (ternary-like)
{{ object.state == 'draft' and 'Quotation' or 'Order' }}

# Or chains (fallback)
{{ (object.user_id.email_formatted or object.company_id.email_formatted or user.email_formatted) }}

# Context access
{{ ctx.get('proforma') and 'Proforma' or '' }}

# String operations
{{ (object.name or '').replace('/', '-') }}
```

### 2. QWeb Engine

**Used for**: `body_html`

**Output Tags**:
```xml
<!-- Escaped output (safe) -->
<t t-out="object.name"/>
<t t-out="object.partner_id.name or 'Unknown'"/>

<!-- Format with helper -->
<t t-out="format_amount(object.amount_total, object.currency_id)"/>
<t t-out="format_date(object.date_order)"/>
<t t-out="format_datetime(object.create_date, tz='UTC', dt_format='long')"/>
```

**Conditional Tags**:
```xml
<t t-if="object.state == 'draft'">
    This is a draft.
</t>
<t t-elif="object.state == 'sent'">
    This has been sent.
</t>
<t t-else="">
    This is confirmed.
</t>
```

**Loop Tags**:
```xml
<t t-foreach="object.order_line" t-as="line">
    <tr>
        <td t-out="line.name"/>
        <td t-out="line.product_uom_qty"/>
        <td t-out="format_amount(line.price_subtotal, object.currency_id)"/>
    </tr>
</t>
```

**Attribute Tags**:
```xml
<!-- Dynamic attribute -->
<a t-att-href="object.get_portal_url()">View</a>

<!-- Formatted attribute (with interpolation) -->
<a t-attf-href="/web/image/product.product/{{ line.product_id.id }}/image_128">
    <img t-attf-src="/web/image/product.product/{{ line.product_id.id }}/image_128"/>
</a>
```

---

## Version Decision Matrix

| Feature | Odoo 14 | Odoo 15 | Odoo 16 | Odoo 17 | Odoo 18 | Odoo 19 |
|---------|:-------:|:-------:|:-------:|:-------:|:-------:|:-------:|
| `t-out` syntax | N | **Y** | **Y** | **Y** | **Y** | **Y** |
| `t-esc` (legacy) | **Y** | **Y** | **Y** | **Y** | **Y** | **Y** |
| `render_engine='qweb'` | N | **Y** | **Y** | **Y** | **Y** | **Y** |
| `template_category` | N | N | **Y** | **Y** | **Y** | **Y** |
| `report_template_ids` M2M | N | N | N | **Y** | **Y** | **Y** |
| Company branding colors | N | N | N | N | N | **Y** |
| `email_primary_color` | N | N | N | N | N | **Y** |
| `email_secondary_color` | N | N | N | N | N | **Y** |
| `mail_notification_layout_with_responsible_signature` | N | N | **Y** | **Y** | **Y** | **Y** |
| Enhanced security in sandbox | N | N | **Y** | **Y** | **Y** | **Y** |

---

## Email Layout Templates

### Available Layouts

| Layout | Width | Use Case |
|--------|-------|----------|
| `mail.mail_notification_layout` | 900px | Full notifications with header/footer |
| `mail.mail_notification_light` | 590px | Simple notifications |
| `mail.mail_notification_layout_with_responsible_signature` | 900px | Uses record's `user_id` signature |

### Layout Context Variables

```python
{
    # Message Information
    'message': mail.message,           # Message object with body, record_name
    'subtype': mail.message.subtype,   # Message subtype

    # Display Control
    'has_button_access': Boolean,      # Show action button
    'button_access': {                 # CTA button config
        'url': String,
        'title': String
    },
    'subtitles': List[String],         # Header subtitles

    # Record Information
    'record': record,                  # The document
    'record_name': String,             # Display name
    'model_description': String,       # Human-readable model

    # Tracking
    'tracking_values': [               # Field changes
        (field_name, old_value, new_value),
    ],

    # Signature
    'email_add_signature': Boolean,    # Include signature
    'signature': HTML,                 # User signature

    # Company
    'company': res.company,            # Company object
    'website_url': String,             # Base URL

    # Branding (Odoo 19+)
    'company.email_primary_color': String,    # Button text color
    'company.email_secondary_color': String,  # Button background

    # Utilities
    'is_html_empty': Function,         # Check empty HTML
}
```

---

## Commands Reference

### Template Creation Commands

| Command | Description |
|---------|-------------|
| `/create-email-template` | Create a new email template for any model |
| `/create-qweb-report` | Create a new QWeb PDF report |
| `/create-notification` | Create a notification template with layout |
| `/create-digest-email` | Create a digest/summary email template |

### Template Management Commands

| Command | Description |
|---------|-------------|
| `/list-templates` | List all templates for a model or module |
| `/analyze-template` | Analyze an existing template for issues |
| `/debug-template` | Debug template rendering issues |
| `/preview-template` | Generate preview of template output |

### Migration Commands

| Command | Description |
|---------|-------------|
| `/migrate-template` | Migrate template between Odoo versions |
| `/fix-template` | Fix common template issues |
| `/validate-template` | Validate template syntax and context |

### QWeb Report Commands

| Command | Description |
|---------|-------------|
| `/create-report-action` | Create report action with menu/button |
| `/style-report` | Add CSS styling to QWeb report |
| `/add-header-footer` | Add header/footer to report |

---

## Template Patterns Library

### Pattern 1: Basic Notification Email

```xml
<?xml version="1.0" encoding="UTF-8"?>
<odoo>
    <data noupdate="1">
        <record id="email_template_basic_notification" model="mail.template">
            <field name="name">Basic Notification</field>
            <field name="model_id" ref="model_your_model"/>
            <field name="subject">{{ object.name }} - Notification</field>
            <field name="email_from">{{ (object.company_id.email or user.email_formatted) }}</field>
            <field name="email_to">{{ object.partner_id.email }}</field>
            <field name="email_layout_xmlid">mail.mail_notification_layout</field>
            <field name="body_html" type="html">
<div>
    <p>Dear <t t-out="object.partner_id.name"/>,</p>
    <p>This is a notification regarding <strong t-out="object.name"/>.</p>
    <t t-if="object.description">
        <p t-out="object.description"/>
    </t>
    <p>Best regards,<br/><t t-out="object.company_id.name"/></p>
</div>
            </field>
            <field name="auto_delete" eval="True"/>
        </record>
    </data>
</odoo>
```

### Pattern 2: Document Email with Report Attachment

```xml
<?xml version="1.0" encoding="UTF-8"?>
<odoo>
    <data noupdate="1">
        <record id="email_template_document" model="mail.template">
            <field name="name">Send Document</field>
            <field name="model_id" ref="model_your_model"/>
            <field name="subject">
                {{ object.state in ('draft', 'sent') and 'Quotation' or 'Order' }} {{ object.name }}
            </field>
            <field name="email_from">{{ (object.user_id.email_formatted or user.email_formatted) }}</field>
            <field name="partner_to">{{ object.partner_id.id }}</field>
            <!-- Odoo 17+ use report_template_ids -->
            <field name="report_template_ids" eval="[(4, ref('module.report_action_id'))]"/>
            <field name="report_name">{{ (object.name or 'Document').replace('/', '-') }}</field>
            <field name="email_layout_xmlid">mail.mail_notification_layout</field>
            <field name="body_html" type="html">
<div>
    <t t-set="doc_name" t-value="'quotation' if object.state in ('draft', 'sent') else 'order'"/>
    <p>Dear <t t-out="object.partner_id.name"/>,</p>
    <p>Please find attached your <t t-out="doc_name"/>
       <strong t-out="object.name"/> amounting to
       <strong t-out="format_amount(object.amount_total, object.currency_id)"/>.</p>
    <p>Do not hesitate to contact us if you have any questions.</p>
</div>
            </field>
        </record>
    </data>
</odoo>
```

### Pattern 3: Order Lines Table

```xml
<table border="0" cellpadding="0" cellspacing="0" width="100%"
       style="border-collapse: collapse;">
    <thead>
        <tr style="background-color: #875A7B; color: white;">
            <th style="padding: 8px;">Product</th>
            <th style="padding: 8px;">Quantity</th>
            <th style="padding: 8px; text-align: right;">Price</th>
        </tr>
    </thead>
    <tbody>
        <t t-foreach="object.order_line" t-as="line">
            <t t-if="line.display_type == 'line_section'">
                <tr>
                    <td colspan="3" style="font-weight: bold; padding: 8px; background-color: #f5f5f5;">
                        <t t-out="line.name"/>
                    </td>
                </tr>
            </t>
            <t t-elif="line.display_type == 'line_note'">
                <tr>
                    <td colspan="3" style="font-style: italic; padding: 8px;">
                        <t t-out="line.name"/>
                    </td>
                </tr>
            </t>
            <t t-else="">
                <tr t-att-style="'background-color: #f9f9f9' if line_index % 2 == 0 else ''">
                    <td style="padding: 8px;">
                        <t t-out="line.product_id.name"/>
                    </td>
                    <td style="padding: 8px; text-align: center;">
                        <t t-out="line.product_uom_qty"/>
                        <t t-out="line.product_uom.name"/>
                    </td>
                    <td style="padding: 8px; text-align: right;">
                        <t t-out="format_amount(line.price_subtotal, object.currency_id)"/>
                    </td>
                </tr>
            </t>
        </t>
    </tbody>
    <tfoot>
        <tr style="font-weight: bold; background-color: #f5f5f5;">
            <td colspan="2" style="padding: 8px; text-align: right;">Total:</td>
            <td style="padding: 8px; text-align: right;">
                <t t-out="format_amount(object.amount_total, object.currency_id)"/>
            </td>
        </tr>
    </tfoot>
</table>
```

### Pattern 4: CTA Button

```xml
<t t-set="button_color" t-value="company.email_secondary_color or '#875A7B'"/>
<table border="0" cellpadding="0" cellspacing="0" width="100%">
    <tr>
        <td align="center" style="padding: 16px;">
            <a t-att-href="object.get_portal_url()"
               t-att-style="'display: inline-block; padding: 10px 20px; color: #ffffff; text-decoration: none; border-radius: 3px; background-color: %s' % button_color">
                View Online
            </a>
        </td>
    </tr>
</table>
```

### Pattern 5: Conditional Content Based on State

```xml
<t t-if="object.state == 'draft'">
    <p style="color: #856404; background-color: #fff3cd; padding: 10px; border-radius: 4px;">
        <strong>Draft:</strong> This document is not yet confirmed.
    </p>
</t>
<t t-elif="object.state == 'sent'">
    <p style="color: #0c5460; background-color: #d1ecf1; padding: 10px; border-radius: 4px;">
        <strong>Awaiting Confirmation:</strong> Please review and confirm.
    </p>
</t>
<t t-elif="object.state == 'done'">
    <p style="color: #155724; background-color: #d4edda; padding: 10px; border-radius: 4px;">
        <strong>Completed:</strong> This document has been processed.
    </p>
</t>
```

### Pattern 6: Payment Information Block

```xml
<t t-if="object.payment_state not in ('paid', 'in_payment')">
    <div style="background-color: #f8f9fa; padding: 15px; margin: 15px 0; border-radius: 4px;">
        <h4 style="margin: 0 0 10px 0;">Payment Information</h4>
        <t t-if="object.payment_reference">
            <p><strong>Reference:</strong> <t t-out="object.payment_reference"/></p>
        </t>
        <t t-if="object.partner_bank_id">
            <p><strong>Bank Account:</strong> <t t-out="object.partner_bank_id.acc_number"/></p>
            <t t-if="object.partner_bank_id.bank_id">
                <p><strong>Bank:</strong> <t t-out="object.partner_bank_id.bank_id.name"/></p>
            </t>
        </t>
        <t t-if="object.amount_residual">
            <p><strong>Amount Due:</strong>
               <t t-out="format_amount(object.amount_residual, object.currency_id)"/>
            </p>
        </t>
    </div>
</t>
```

---

## QWeb Report Patterns

### Pattern 1: Basic Report Structure

```xml
<?xml version="1.0" encoding="UTF-8"?>
<odoo>
    <!-- Report Action -->
    <record id="action_report_document" model="ir.actions.report">
        <field name="name">Document Report</field>
        <field name="model">your.model</field>
        <field name="report_type">qweb-pdf</field>
        <field name="report_name">module_name.report_document_template</field>
        <field name="report_file">module_name.report_document_template</field>
        <field name="print_report_name">'Document - %s' % object.name</field>
        <field name="binding_model_id" ref="model_your_model"/>
        <field name="binding_type">report</field>
    </record>

    <!-- Report Template -->
    <template id="report_document_template">
        <t t-call="web.html_container">
            <t t-foreach="docs" t-as="doc">
                <t t-call="web.external_layout">
                    <div class="page">
                        <h2><t t-out="doc.name"/></h2>

                        <div class="row">
                            <div class="col-6">
                                <strong>Date:</strong>
                                <span t-field="doc.date"/>
                            </div>
                            <div class="col-6 text-end">
                                <strong>Reference:</strong>
                                <span t-out="doc.reference"/>
                            </div>
                        </div>

                        <!-- Content goes here -->

                    </div>
                </t>
            </t>
        </t>
    </template>
</odoo>
```

### Pattern 2: Report with Table

```xml
<table class="table table-sm o_main_table">
    <thead>
        <tr>
            <th class="text-start">Description</th>
            <th class="text-center">Quantity</th>
            <th class="text-end">Unit Price</th>
            <th class="text-end">Amount</th>
        </tr>
    </thead>
    <tbody>
        <t t-foreach="doc.line_ids" t-as="line">
            <tr>
                <td><span t-field="line.name"/></td>
                <td class="text-center"><span t-field="line.quantity"/></td>
                <td class="text-end"><span t-field="line.price_unit"/></td>
                <td class="text-end"><span t-field="line.price_subtotal"/></td>
            </tr>
        </t>
    </tbody>
</table>

<!-- Totals -->
<div class="row justify-content-end">
    <div class="col-4">
        <table class="table table-sm">
            <tr>
                <td><strong>Subtotal</strong></td>
                <td class="text-end"><span t-field="doc.amount_untaxed"/></td>
            </tr>
            <tr>
                <td>Taxes</td>
                <td class="text-end"><span t-field="doc.amount_tax"/></td>
            </tr>
            <tr class="border-top">
                <td><strong>Total</strong></td>
                <td class="text-end"><span t-field="doc.amount_total"/></td>
            </tr>
        </table>
    </div>
</div>
```

### Pattern 3: Page Break Control

```xml
<!-- Force page break before element -->
<div style="page-break-before: always;">
    <h3>New Page Content</h3>
</div>

<!-- Prevent page break inside element -->
<div style="page-break-inside: avoid;">
    <table><!-- Table that should stay together --></table>
</div>

<!-- Force page break after element -->
<div style="page-break-after: always;">
    <p>End of section</p>
</div>
```

---

## Validation Rules

### MANDATORY Pre-Flight Checks

Before creating any template, Claude MUST validate:

```
┌─────────────────────────────────────────────────────────────────┐
│                 TEMPLATE VALIDATION CHECKLIST                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  1. MODEL VALIDATION                                             │
│     □ Model exists in target Odoo version                        │
│     □ Model has required fields (partner_id, etc.)               │
│     □ Model inherits mail.thread (if notification)               │
│                                                                   │
│  2. FIELD VALIDATION                                             │
│     □ All {{ object.field }} references exist                    │
│     □ All t-out="object.field" references exist                  │
│     □ Related fields are valid (object.partner_id.name)          │
│                                                                   │
│  3. SYNTAX VALIDATION                                            │
│     □ QWeb tags properly closed                                  │
│     □ Jinja2 expressions balanced {{ }}                          │
│     □ No mixing of t-esc (Odoo 14) and t-out (Odoo 15+)         │
│                                                                   │
│  4. VERSION COMPATIBILITY                                        │
│     □ report_template vs report_template_ids (Odoo 17+)          │
│     □ template_category (Odoo 16+)                               │
│     □ Company branding colors (Odoo 19+)                         │
│                                                                   │
│  5. SECURITY VALIDATION                                          │
│     □ No unsafe eval() or exec()                                 │
│     □ No arbitrary file access                                   │
│     □ Sandbox-safe expressions                                   │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Error Recovery

### Common Errors and Solutions

| Error | Cause | Solution |
|-------|-------|----------|
| `AttributeError: 'NoneType' has no attribute 'name'` | Null field access | Use `object.field_id.name or ''` |
| `QWebException: t-esc is deprecated` | Old syntax in Odoo 15+ | Replace `t-esc` with `t-out` |
| `KeyError: 'format_amount'` | Missing context helper | Ensure `mail.render.mixin` is inherited |
| `ValidationError: Invalid XML` | Malformed QWeb | Check XML structure, close all tags |
| `NameError: name 'object' is not defined` | Wrong rendering context | Use template's model context |

### Debug Template Rendering

```python
# In Odoo shell
template = env['mail.template'].browse(TEMPLATE_ID)
record = env['your.model'].browse(RECORD_ID)

# Render and inspect
rendered = template._render_field(
    'body_html',
    [record.id],
    compute_lang=True
)
print(rendered[record.id])
```

---

## Module-Specific Templates

### Sales Module

| Template ID | Purpose | Model |
|-------------|---------|-------|
| `email_template_edi_sale` | Send quotation/order | sale.order |
| `mail_template_sale_confirmation` | Order confirmation | sale.order |
| `mail_template_sale_payment_executed` | Payment received | sale.order |

### Purchase Module

| Template ID | Purpose | Model |
|-------------|---------|-------|
| `email_template_edi_purchase` | Send RFQ | purchase.order |
| `email_template_edi_purchase_done` | Send PO | purchase.order |
| `email_template_edi_purchase_reminder` | Delivery reminder | purchase.order |

### Accounting Module

| Template ID | Purpose | Model |
|-------------|---------|-------|
| `email_template_edi_invoice` | Send invoice | account.move |
| `email_template_edi_credit_note` | Send credit note | account.move |
| `mail_template_data_payment_receipt` | Payment receipt | account.payment |

### HR Recruitment

| Template ID | Purpose | Model |
|-------------|---------|-------|
| `email_template_data_applicant_employee` | Applicant to employee | hr.employee |
| `email_template_data_applicant_congratulations` | Congratulations | hr.applicant |
| `email_template_data_applicant_refuse` | Refusal notice | hr.applicant |

---

## Best Practices

### 1. Always Use Fallbacks

```xml
<!-- Good -->
<t t-out="object.partner_id.name or 'Valued Customer'"/>

<!-- Bad - will fail if partner_id is None -->
<t t-out="object.partner_id.name"/>
```

### 2. Use Format Helpers

```xml
<!-- Good - consistent formatting -->
<t t-out="format_amount(object.amount_total, object.currency_id)"/>
<t t-out="format_date(object.date_order)"/>

<!-- Bad - manual formatting -->
<t t-out="'$%.2f' % object.amount_total"/>
```

### 3. Respect Translations

```xml
<!-- Good - translatable -->
<p>Dear <t t-out="object.partner_id.name"/>,</p>

<!-- Bad - hardcoded in template, use data records instead -->
```

### 4. Use Layouts for Consistency

```xml
<!-- Good - uses company branding -->
<field name="email_layout_xmlid">mail.mail_notification_layout</field>

<!-- Avoid - custom inline styling for every email -->
```

### 5. Handle Empty HTML

```xml
<t t-if="not is_html_empty(object.description)">
    <div t-out="object.description"/>
</t>
```

### 6. Version-Specific Syntax

```xml
<!-- Odoo 15+ -->
<t t-out="value"/>

<!-- Odoo 14 only -->
<t t-esc="value"/>
```

### 7. Report Attachment Handling

```xml
<!-- Odoo 14-16: Single report -->
<field name="report_template" ref="module.report_action"/>

<!-- Odoo 17+: Multiple reports -->
<field name="report_template_ids" eval="[(4, ref('module.report_action'))]"/>
```

### 8. Dynamic Filenames

```python
# Safe filename generation
<field name="report_name">{{ (object.name or 'Document').replace('/', '-') }}</field>
```

---

## File Locations Reference

### Core Template Locations

```
odoo/addons/mail/
├── models/
│   ├── mail_template.py           # Main model
│   └── mail_render_mixin.py       # Rendering engine
├── data/
│   └── mail_template_data.xml     # Base templates
└── views/
    └── mail_template_views.xml    # UI views

odoo/addons/sale/
└── data/
    └── mail_template_data.xml     # Sales templates

odoo/addons/purchase/
└── data/
    └── mail_template_data.xml     # Purchase templates

odoo/addons/account/
└── data/
    └── mail_template_data.xml     # Accounting templates
```

---

## Related Documentation

| Document | Path | Purpose |
|----------|------|---------|
| Email Research | `C:\odoo\researches\ODOO_EMAIL_TEMPLATES_COMPLETE_RESEARCH.md` | Full research documentation |
| Odoo 17 CLAUDE.md | `odoo17\CLAUDE.md` | Development commands |
| Design System | `odoo17\DESIGN_SYSTEM_RULES.md` | Theme styling rules |

---

*Odoo Report Plugin v1.0*
*TaqaTechno - Professional Email Templates & QWeb Reports*
*Supports Odoo 14-19*
