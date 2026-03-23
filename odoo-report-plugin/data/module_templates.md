# Module-Specific Template IDs

Known Odoo email template and report action IDs by module.

## Sales Module

| Template ID | Purpose | Model |
|-------------|---------|-------|
| `email_template_edi_sale` | Send quotation/order | sale.order |
| `mail_template_sale_confirmation` | Order confirmation | sale.order |
| `mail_template_sale_payment_executed` | Payment received | sale.order |

## Purchase Module

| Template ID | Purpose | Model |
|-------------|---------|-------|
| `email_template_edi_purchase` | Send RFQ | purchase.order |
| `email_template_edi_purchase_done` | Send PO | purchase.order |
| `email_template_edi_purchase_reminder` | Delivery reminder | purchase.order |

## Accounting Module

| Template ID | Purpose | Model |
|-------------|---------|-------|
| `email_template_edi_invoice` | Send invoice | account.move |
| `email_template_edi_credit_note` | Send credit note | account.move |
| `mail_template_data_payment_receipt` | Payment receipt | account.payment |

## HR Recruitment

| Template ID | Purpose | Model |
|-------------|---------|-------|
| `email_template_data_applicant_employee` | Applicant to employee | hr.employee |
| `email_template_data_applicant_congratulations` | Congratulations | hr.applicant |
| `email_template_data_applicant_refuse` | Refusal notice | hr.applicant |
