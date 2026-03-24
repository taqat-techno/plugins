---
name: pm-bilingual-standards
description: |
  Bilingual EN/AR document standards — data-i18n from day one, RTL validation, language parity, Arabic toggle planning, and paired span architecture. Use when creating or editing documents that need both English and Arabic versions.


  <example>
  Context: User wants a bilingual dashboard
  user: "Create a bilingual EN/AR dashboard for the project"
  assistant: "I will use the pm-bilingual-standards skill to build the HTML with data-i18n attributes from the start, paired lang-en/lang-ar spans, RTL-safe CSS, and a language toggle."
  <commentary>Core trigger - bilingual document creation from scratch.</commentary>
  </example>

  <example>
  Context: User asks to add Arabic to an existing page
  user: "Add Arabic translation to this HTML report"
  assistant: "I will use the pm-bilingual-standards skill to retrofit data-i18n attributes, create paired AR spans for every EN span, add RTL CSS overrides, and implement the language toggle."
  <commentary>Retrofit trigger - adding Arabic to existing English-only document.</commentary>
  </example>

  <example>
  Context: User modified English text in a bilingual file
  user: "Update the English title in the dashboard header"
  assistant: "I will update the English span AND the corresponding Arabic span. Both languages must be updated for every text change."
  <commentary>Edit trigger - always update both language spans.</commentary>
  </example>

  <example>
  Context: User reports layout issues in Arabic view
  user: "The Arabic version has broken table alignment"
  assistant: "I will use the pm-bilingual-standards skill to diagnose RTL layout issues — checking dir attributes, CSS logical properties, table padding, and border alignment."
  <commentary>RTL debug trigger - layout issues in Arabic view.</commentary>
  </example>
license: "MIT"
metadata:
  version: "1.0.0"
  priority: 65
  filePattern:
    - "**/*bilingual*"
    - "**/*ar_*"
    - "**/*_ar.*"
    - "**/*_arabic*"
  bashPattern: []
  promptSignals:
    phrases:
      - "bilingual"
      - "Arabic"
      - "RTL"
      - "EN/AR"
      - "data-i18n"
      - "language toggle"
      - "both languages"
      - "right to left"
      - "Arabic translation"
    minScore: 6
---

# PM Bilingual EN/AR Standards

## Rule 33: Plan Arabic Toggle from Day One

Every PM dashboard and deliverable intended for bilingual audiences MUST have `data-i18n` attributes planned from the first line of HTML. Adding bilingual support after the fact requires touching every text element — a complete rework.

## HTML Architecture: Paired Spans

### Pattern: Side-by-Side Language Spans

```html
<!-- Every text element gets paired spans -->
<h1>
    <span class="lang-en" data-i18n="page-title">Project Status Report</span>
    <span class="lang-ar" data-i18n="page-title">تقرير حالة المشروع</span>
</h1>

<p>
    <span class="lang-en" data-i18n="intro">This report covers Q1 2026 progress.</span>
    <span class="lang-ar" data-i18n="intro">يغطي هذا التقرير تقدم الربع الأول 2026.</span>
</p>
```

### Language Toggle Implementation

```html
<!-- Toggle button -->
<button onclick="toggleLanguage()" class="lang-toggle">
    <span class="lang-en">عربي</span>
    <span class="lang-ar">English</span>
</button>

<script>
function toggleLanguage() {
    const html = document.documentElement;
    const isArabic = html.getAttribute('dir') === 'rtl';

    if (isArabic) {
        html.setAttribute('dir', 'ltr');
        html.setAttribute('lang', 'en');
        document.querySelectorAll('.lang-en').forEach(el => el.style.display = '');
        document.querySelectorAll('.lang-ar').forEach(el => el.style.display = 'none');
    } else {
        html.setAttribute('dir', 'rtl');
        html.setAttribute('lang', 'ar');
        document.querySelectorAll('.lang-ar').forEach(el => el.style.display = '');
        document.querySelectorAll('.lang-en').forEach(el => el.style.display = 'none');
    }
}

// Default: show English
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.lang-ar').forEach(el => el.style.display = 'none');
});
</script>
```

## Rule 8: Always Update Both Languages

**CRITICAL**: Never edit English text without updating the Arabic span. This is the #1 bilingual bug.

When editing any text:
1. Find the English span
2. Update it
3. Find the sibling Arabic span (same `data-i18n` key)
4. Update it too
5. Verify both visually

## Rule 9: Verify RTL Visually

Arabic layout can break:
- **Borders** — left/right borders swap in RTL
- **Alignment** — text-align must flip
- **Padding** — padding-left becomes padding-right
- **Table cells** — column order reverses
- **Icons** — directional icons (arrows) must flip

### RTL CSS Pattern

```css
/* Base styles (LTR) */
.card { padding-left: 20px; text-align: left; border-left: 3px solid #007bff; }

/* RTL overrides */
[dir="rtl"] .card { padding-right: 20px; padding-left: 0; text-align: right; border-right: 3px solid #007bff; border-left: none; }

/* Or use CSS logical properties (modern approach) */
.card {
    padding-inline-start: 20px;
    text-align: start;
    border-inline-start: 3px solid #007bff;
}
```

### Separate RTL File

Always create a dedicated `rtl.css` file:

```css
/* rtl.css — Arabic/RTL overrides only */
[dir="rtl"] { font-family: 'Noto Kufi Arabic', 'Segoe UI', Tahoma, sans-serif; }
[dir="rtl"] table { direction: rtl; }
[dir="rtl"] .text-left { text-align: right; }
[dir="rtl"] .float-left { float: right; }
[dir="rtl"] .me-3 { margin-right: 0 !important; margin-left: 1rem !important; }
[dir="rtl"] .ms-3 { margin-left: 0 !important; margin-right: 1rem !important; }
```

## Rule 10: Check Both Languages After Toggle

After any change:
1. Open the HTML file in browser
2. View in English — check layout, alignment, content
3. Click toggle to Arabic — check:
   - All text switched (no orphaned English)
   - Table columns properly reversed
   - Numbers still readable (Arabic numerals OK, but keep Western numerals for data)
   - Borders and padding look correct
   - No overflow or clipping

## Table Bilingual Pattern

```html
<table class="table">
    <thead>
        <tr>
            <th>
                <span class="lang-en">Department</span>
                <span class="lang-ar">القسم</span>
            </th>
            <th>
                <span class="lang-en">Status</span>
                <span class="lang-ar">الحالة</span>
            </th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>
                <span class="lang-en">Engineering</span>
                <span class="lang-ar">الهندسة</span>
            </td>
            <td>
                <span class="lang-en">Training completed</span>
                <span class="lang-ar">اكتمل التدريب</span>
            </td>
        </tr>
    </tbody>
</table>
```

## Bilingual Checklist

Before delivering any bilingual document:

- [ ] Every text element has paired `lang-en` / `lang-ar` spans
- [ ] All spans have `data-i18n` keys for identification
- [ ] Language toggle button works in both directions
- [ ] RTL CSS file exists and is loaded
- [ ] Both views checked visually (no orphaned text, no overflow)
- [ ] Table columns render correctly in both directions
- [ ] Font family includes Arabic-supporting font (Noto Kufi Arabic, Segoe UI)
- [ ] Numbers use consistent format in both languages
