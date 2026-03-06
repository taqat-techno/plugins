# Plugin Enhancement Report — February 2026
**Author**: Deep analysis across all sessions, MD files, SKILL files, changelogs, session learnings, memory files, pattern libraries, and error catalogs
**Scope**: `C:\TQ-WorkSpace\odoo\tmp\plugins` — 8 active plugins
**Status**: Actionable enhancements + 8 new plugin proposals

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Plugin Health Dashboard](#2-plugin-health-dashboard)
3. [odoo-upgrade-plugin](#3-odoo-upgrade-plugin-v400)
4. [odoo-frontend-plugin](#4-odoo-frontend-plugin-v700)
5. [odoo-report-plugin](#5-odoo-report-plugin-v200)
6. [devops-plugin](#6-devops-plugin-v200)
7. [ntfy-plugin](#7-ntfy-plugin-v200)
8. [pandoc-plugin](#8-pandoc-plugin-v100)
9. [remotion-plugin](#9-remotion-plugin-v100)
10. [codex-plugin](#10-codex-plugin-v100)
11. [New Plugin Proposals](#11-new-plugin-proposals)
12. [Cross-Plugin Integration Opportunities](#12-cross-plugin-integration-opportunities)
13. [Priority Matrix](#13-priority-matrix)

---

## 1. Executive Summary

### What Was Analyzed
- All 8 plugin SKILL.md files (total ~10,000 lines of documentation)
- All plugin.json manifests and marketplace.json
- All memory files (30+ files across plugins)
- All helper and reference files (20+ files)
- Changelogs: devops v2.0, remotion v1.0, upgrade v3.1
- Session learnings: `SESSION_LEARNINGS_2025-11-03.md` (Project Alpha migration)
- Enhancement plans: `ENHANCEMENT_REPORT_JAN_2026.md`, `ENHANCEMENT_PLAN_V2.md`, `ENHANCEMENTS_V3.md`
- Error catalogs: 35+ error categories documented
- Pattern libraries: 150+ upgrade patterns, 50+ email patterns, 30+ QWeb patterns
- Real project context: 6 Odoo versions, 30+ active client projects

### Key Findings

| Finding | Impact |
|---------|--------|
| 3 plugins have Odoo 19 gaps (upgrade, frontend, report) | High — Odoo 19 is actively in use |
| codex-plugin is too generic, no Odoo specialization | Medium — missed value opportunity |
| 0 plugins cover testing, security audit, or i18n | High — daily developer needs |
| Cross-plugin integration is minimal | Medium — combined workflows are powerful |
| remotion/pandoc have no Arabic/RTL support | Low-Medium — needed for your projects |
| No deployment or performance plugin exists | High — production concerns |

---

## 2. Plugin Health Dashboard

| Plugin | Version | Maturity | Odoo 19 Ready | Last Real-World Test | Gaps |
|--------|---------|----------|--------------|---------------------|------|
| **odoo-upgrade** | 4.0.0 | ★★★★★ | 95% | Nov 2025 (Project Alpha) | OWL 2.0 migration, Odoo 18 intermediary |
| **odoo-frontend** | 7.0.0 | ★★★★★ | 85% | Jan 2026 | Odoo 19 snippet API, dark mode |
| **odoo-report** | 2.0.0 | ★★★★☆ | 80% | Dec 2025 (sadad_invoice) | Charts, e-invoice, Odoo 19 company branding |
| **devops** | 2.0.0 | ★★★★☆ | N/A | Active daily use | GitHub integration, Jenkins, deploy hooks |
| **ntfy** | 2.0.0 | ★★★☆☆ | N/A | Active | Fallbacks, aggregation, templates |
| **pandoc** | 1.0.0 | ★★★☆☆ | N/A | Unknown | Arabic RTL, Odoo QWeb import, templates |
| **remotion** | 1.0.0 | ★★★☆☆ | N/A | Feb 2026 | Social formats, subtitles, brand kit |
| **codex** | 1.0.0 | ★★☆☆☆ | N/A | Unknown | Too generic, no Odoo patterns |

---

## 3. odoo-upgrade-plugin (v4.0.0)

### Current Strengths
- 150 transformation patterns covering Odoo 14→19
- 75 automated fixes, 95-98% success rate
- Real-world validated by Project Alpha migration (6 critical issues found and resolved)
- Comprehensive error catalog (35+ categories)
- Unified CLI (`odoo_upgrade_cli.py`) with precheck, validate, quickfix, autofix commands
- Session learnings properly captured in patterns and fixes directories

### Gaps Identified

#### Gap 1: Controller Type Migration (CRITICAL — Odoo 17/18 → 19)
The upgrade plugin detects XML and Python patterns, but **does not yet auto-fix** `type='json'` → `type='jsonrpc'` in controllers.

**What to add to `patterns/odoo18_to_19.md`**:
```python
# CRITICAL: Odoo 19 controller type change
# OLD (Odoo 17/18)
@http.route('/api/endpoint', type='json', auth='user')

# NEW (Odoo 19)
@http.route('/api/endpoint', type='jsonrpc', auth='user')

# Detection:
# grep -r "type='json'" projects/ --include="*.py"
```

**What to add to `auto_fix_library.py`**: A Python fix that regex-replaces `type='json'` with `type='jsonrpc'` in `@http.route` decorators only (not other occurrences of `type='json'`).

#### Gap 2: `attrs={}` → Inline Expression Migration (CRITICAL — Odoo 17 → 18/19)
The `attrs` attribute was deprecated in Odoo 17, fully removed in Odoo 19. Current patterns mention `tree→list` but the `attrs` migration is **not in the automated fix library**.

```xml
<!-- OLD -->
<field name="amount" attrs="{'invisible': [('state', '=', 'draft')], 'required': [('type', '=', 'out_invoice')]}"/>

<!-- NEW (Odoo 18/19) -->
<field name="amount" invisible="state == 'draft'" required="type == 'out_invoice'"/>
```

**Detection**: `grep -r "attrs=" views/ --include="*.xml"`
**Complexity**: Medium — simple list-expression → Python-expression conversion needed

#### Gap 3: OWL 1.x → OWL 2.0 Backend Component Migration (Odoo 18+)
Odoo 18 introduced OWL 2.0 with breaking changes. The upgrade plugin handles XML/Python but **no OWL migration section exists**.

**Key changes to document**:
```javascript
// OLD (OWL 1.x — Odoo 16/17)
import { Component } from "@odoo/owl";
class MyWidget extends Component {
    constructor(parent, props) {
        super(parent, props);
        this.state = useState({ count: 0 });
    }
}

// NEW (OWL 2.0 — Odoo 18+)
import { Component, useState } from "@odoo/owl";
class MyWidget extends Component {
    setup() {
        this.state = useState({ count: 0 });
    }
}
```

**Missing detection patterns**:
- `constructor(parent, props)` in OWL components → must become `setup()`
- `willStart()` → `onWillStart()` lifecycle hook rename
- `patched()` → `onPatched()`
- `mounted()` → `onMounted()`
- `willUnmount()` → `onWillUnmount()`

#### Gap 4: Odoo 19 Company Branding Fields
Odoo 19 changed how company branding fields work in templates:
```xml
<!-- OLD (Odoo 17/18) -->
<t t-set="company" t-value="res_company"/>

<!-- NEW (Odoo 19) — company_branding model -->
<t t-set="company" t-value="company_id"/>
```

**What to add**: Detection + pattern in `patterns/odoo18_to_19.md`

#### Gap 5: Intermediary Odoo 14/15 → 17 Path
Current upgrade scripts focus heavily on 17→19. Projects on Odoo 14 (10 configs) and Odoo 15 (4 configs) need a **multi-hop upgrade path**. The plugin should document and support:
- 14 → 16 intermediary step (significant changes)
- 15 → 16 intermediary step
- 16 → 17 (already partially covered)

**What to add**: `patterns/odoo14_to_16.md` and `patterns/odoo15_to_17.md`

#### Gap 6: `ir.sequence` and Numbercall Field Removal
The error catalog mentions `numbercall` in crons, but `ir.sequence` also had changes. The precheck script should verify all sequence references.

#### Gap 7: Missing Quick-Fix: `edit` Attribute Removal
Odoo 17+ removed the `edit` attribute from list/tree views. This is not in the auto-fix library:
```xml
<!-- OLD -->
<tree editable="bottom">

<!-- This still works, but: -->
<list edit="0">  <!-- 'edit' attribute removed in Odoo 17 -->
```

### Recommended Actions

```
Priority 1 (Add to v4.1):
  - [ ] Add type='json' → type='jsonrpc' to auto_fix_library.py
  - [ ] Add attrs={} → inline expression migration with regex parser
  - [ ] Add OWL 1.x → 2.0 migration section to SKILL.md and patterns/

Priority 2 (Add to v4.2):
  - [ ] Add Odoo 14→16 patterns file
  - [ ] Add company branding field detection for Odoo 19
  - [ ] Add edit attribute removal to XML fixers

Priority 3 (Nice to have):
  - [ ] Interactive upgrade wizard (walk developer through each change)
  - [ ] Upgrade diff report (show all changes made, before/after)
  - [ ] Module dependency graph validator (check if depends= are still valid)
```

---

## 4. odoo-frontend-plugin (v7.0.0)

### Current Strengths
- Most comprehensive plugin — 2000+ line SKILL.md
- Complete `$o-website-values-palettes` reference (115+ keys)
- Figma browser automation for color/typography extraction
- 81+ snippet templates
- publicWidget patterns with editableMode handling
- OWL 2.0 documentation for backend components
- Bootstrap 4→5 migration mapping
- PWA, TypeScript, testing framework support
- Version detection and routing (Odoo 14-19)

### Gaps Identified

#### Gap 1: Odoo 19 Website Snippet API Changes
The snippet options inheritance that was removed in Odoo 19 (`website.snippet_options`) is mentioned in the upgrade plugin but **not documented in the frontend plugin's SKILL.md**. Frontend developers hitting this need guidance.

**What to add to SKILL.md**:
```python
# CRITICAL (Odoo 19): website.snippet_options was removed
# OLD (Odoo 17/18) — WILL FAIL in Odoo 19
class CustomSnippet(models.AbstractModel):
    _inherit = 'website.snippet.options'

# NEW (Odoo 19) — use ir.ui.view inheritance instead
# Or use the new snippet options system
```

#### Gap 2: Dark Mode / Theme Toggle Pattern
Multiple Odoo 17/18/19 projects are building customer-facing sites. Dark mode is expected but **no pattern exists** in the plugin.

**What to add to `memories/publicwidget_patterns.md`**:
```javascript
/** @odoo-module **/
import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.DarkModeToggle = publicWidget.Widget.extend({
    selector: 'body',
    events: {
        'click .dark-mode-toggle': '_onToggleDarkMode',
    },
    start: function() {
        const saved = localStorage.getItem('dark-mode');
        if (saved === 'true') this.$el.addClass('dark-mode');
        return this._super.apply(this, arguments);
    },
    _onToggleDarkMode: function() {
        const isDark = this.$el.toggleClass('dark-mode').hasClass('dark-mode');
        localStorage.setItem('dark-mode', isDark);
    },
});
```

**SCSS pattern**:
```scss
body.dark-mode {
    --color-bg: #1a1a2e;
    --color-text: #e0e0e0;
    background-color: var(--color-bg);
    color: var(--color-text);
}
```

#### Gap 3: Odoo 18 SCSS Variable Changes
Odoo 18 introduced changes to some `$o-` variables. The current SCSS reference covers Odoo 16/17 as primary but doesn't flag Odoo 18-specific changes.

**What to add to `memories/scss_variables.md`**:
- Document any variables added/removed in Odoo 18
- Note that `$o-website-values-palettes` structure is the same but some keys changed

#### Gap 4: Website Builder Custom Snippet Options (Odoo 19)
The plugin documents snippet creation but not the **snippet options/customization panel** that appears in the website builder sidebar. This is important for professional themes.

**What to add**: A section on `data-snippet`, `data-name`, `data-oe-type` attributes and how to register snippet options.

#### Gap 5: Missing: Lazy Loading Images Pattern
Performance-critical for all Odoo websites. No lazy loading pattern exists.

**What to add to `memories/publicwidget_patterns.md`**:
```javascript
publicWidget.registry.LazyImages = publicWidget.Widget.extend({
    selector: 'img[data-lazy-src]',
    start: function() {
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    img.src = img.dataset.lazySrc;
                    img.removeAttribute('data-lazy-src');
                    observer.unobserve(img);
                }
            });
        });
        this.$el.each((i, img) => observer.observe(img));
    }
});
```

#### Gap 6: Multi-Language RTL/LTR Switcher
The projects include Arabic sites (Project Delta, khairgate, relief_center) but the frontend plugin has **no RTL switching pattern**. The report plugin covers RTL for PDFs but not for website themes.

**What to add**: A pattern for dynamic RTL/LTR switching in publicWidget based on `html[dir="rtl"]`.

#### Gap 7: TypeScript Integration Example Is Incomplete
TypeScript is listed as supported but the SKILL.md lacks a complete working example with Odoo's type declarations.

### Recommended Actions

```
Priority 1 (Add to v7.1):
  - [ ] Document Odoo 19 snippet options system changes in SKILL.md
  - [ ] Add dark mode toggle pattern to memories/publicwidget_patterns.md
  - [ ] Add RTL/LTR dynamic switching pattern

Priority 2 (Add to v7.2):
  - [ ] Add lazy loading image widget pattern
  - [ ] Add Odoo 18 SCSS variable changes to memories/scss_variables.md
  - [ ] Complete TypeScript integration example with tsconfig.json for Odoo

Priority 3:
  - [ ] Add website builder snippet options documentation
  - [ ] Add A/B testing pattern for website content
  - [ ] Add IntersectionObserver-based animation trigger pattern
```

---

## 5. odoo-report-plugin (v2.0.0)

### Current Strengths
- 1523-line SKILL.md with comprehensive coverage
- Full sadad_invoice bilingual example (complete working code)
- wkhtmltopdf setup for Windows/Linux/macOS
- Arabic/RTL mandatory template wrapper
- Version decision matrix (Odoo 14-19)
- Memory-driven pattern selection (version_routing.md)
- Debug workflow with 5-step diagnosis
- QWeb best practices with N+1 query prevention

### Gaps Identified

#### Gap 1: Charts and Data Visualization in Reports
Zero coverage of charts in PDF reports. This is a very common request (sales trends, HR dashboards, etc.).

**What to add to SKILL.md**:
```xml
<!-- Option 1: SVG chart inline -->
<svg width="400" height="200" xmlns="http://www.w3.org/2000/svg">
    <t t-foreach="report_lines" t-as="line">
        <rect t-att-x="line.x" t-att-y="line.y"
              t-att-width="line.width" t-att-height="line.height"
              fill="#875a7b"/>
    </t>
</svg>

<!-- Option 2: matplotlib pre-render to base64 -->
<!-- Python: generate chart → base64 → pass to report context -->
```

#### Gap 2: QR Code / Barcode in Reports
Common need for invoices (e-invoice QR codes, product barcodes). The plugin has no pattern for this.

**What to add**:
```xml
<!-- Odoo built-in barcode widget -->
<img t-att-src="'/report/barcode/QR/%s' % record.id"/>

<!-- Custom QR code with python-qrcode -->
<!-- Or use Odoo's built-in barcode API -->
<img t-att-src="'/report/barcode/?type=QR&value=%s&width=150&height=150' % record.name"/>
```

#### Gap 3: Odoo 19 Company Branding in Reports
Odoo 19 changed how `res.company` fields are accessed in report context.

**What to add to `memories/version_routing.md`**:
```python
# Odoo 17/18 — company logo
o.env.company.logo

# Odoo 19 — use company_id from context
docs[0].company_id.logo
```

#### Gap 4: Report with User-Configurable Options (Wizard)
Many reports need user input before generation (date range, grouping, etc.). No wizard pattern exists.

**What to add**:
```python
class ReportWizard(models.TransientModel):
    _name = 'report.wizard'

    date_from = fields.Date(required=True)
    date_to = fields.Date(required=True)
    partner_id = fields.Many2one('res.partner')

    def action_print_report(self):
        data = {'form': self.read()[0]}
        return self.env.ref('module.report_action').report_action(self, data=data)
```

#### Gap 5: E-Invoice / XML Alongside PDF
Several projects (sadad_invoice, khairgate) need electronic invoice formats (ZATCA, UBL/XML) alongside PDF. No guidance exists.

**What to add**: A section on `ir.actions.report` with `report_type='qweb-xml'` for structured XML output.

#### Gap 6: Report Performance — Large Datasets
The QWeb best practices mention N+1 queries but no guidance exists for reports with thousands of lines (pagination, streaming).

**What to add**:
```python
# Chunk large recordsets to prevent memory issues
def _get_report_values(self, docids, data=None):
    records = self.env['sale.order'].browse(docids)
    # Process in chunks for very large reports
    chunk_size = 100
    for i in range(0, len(records), chunk_size):
        yield records[i:i+chunk_size]
```

#### Gap 7: Digital Signature Block
Legal requirement in many Arabic countries for official documents.

**What to add**: A signature block template pattern with authorized signatory fields.

#### Gap 8: Tax Display Patterns
Common requirement for Saudi/UAE invoices — VAT number display, tax breakdown, exemption notes. Missing from the plugin.

### Recommended Actions

```
Priority 1 (Add to v2.1):
  - [ ] Add QR code/barcode patterns (ZATCA invoice QR is legally required in Saudi Arabia)
  - [ ] Add Odoo 19 company branding field changes to version_routing.md
  - [ ] Add report wizard (TransientModel) pattern

Priority 2 (Add to v2.2):
  - [ ] Add SVG/chart in PDF pattern
  - [ ] Add e-invoice XML output pattern (qweb-xml)
  - [ ] Add tax display and VAT breakdown patterns for GCC compliance
  - [ ] Add digital signature block template

Priority 3:
  - [ ] Add large dataset pagination pattern
  - [ ] Add Docker wkhtmltopdf setup (for server deployments)
```

---

## 6. devops-plugin (v2.0.0)

### Current Strengths
- Hybrid CLI + MCP routing — best of both worlds
- Comprehensive WIQL query library (12 sections)
- TaqaTechno business rules enforced
- Automation templates (standup, sprint report, bulk creator)
- 7 memory files covering all workflows
- PR review workflow with checklist

### Gaps Identified

#### Gap 1: GitHub Integration
Your Odoo repos use both Azure DevOps **and** GitHub (`gh` CLI is in CLAUDE.md). The devops plugin only covers Azure DevOps. Many operations (clone, PR, issues) happen on GitHub side.

**What to add**: A `github_integration.md` memory file covering:
```bash
# Sync Azure DevOps work item with GitHub PR
gh pr create --title "feat: [AB#1234] Feature Name" --body "Closes AB#1234"

# Link GitHub PR to Azure DevOps work item
# AB#XXXX in PR title/description auto-links in Azure DevOps
```

#### Gap 2: Jenkins CI/CD Integration
The `project-eta` project uses Jenkins CI/CD (noted in main CLAUDE.md). No Jenkins patterns exist.

**What to add**: A `jenkins_integration.md` memory or helper file covering:
- Triggering Jenkins builds from Azure DevOps
- Webhook configuration
- Build status checking

#### Gap 3: Sprint Retrospective Command
The plugin has standup and sprint commands but no retrospective pattern.

**What to add**: `/retrospective` command that collects completed work items from the sprint and formats a retrospective document.

#### Gap 4: Automated Deployment Hooks
When work items reach "Done" state, there's no hook to trigger deployment. This would be powerful.

**What to add**: A `deployment_hook.md` pattern for triggering Odoo module updates after work item state changes.

#### Gap 5: PR Template Customization
The PR creation command (`/create-pr`) doesn't read or suggest project-specific PR templates.

**What to add**: Template detection from `.github/PULL_REQUEST_TEMPLATE.md` or Azure DevOps PR templates.

#### Gap 6: Work Item Bulk Import
No CSV/Excel import pattern for creating multiple work items (e.g., from a requirements document).

### Recommended Actions

```
Priority 1 (Add to v2.1):
  - [ ] Add github_integration.md memory file with gh CLI + Azure DevOps linking patterns
  - [ ] Add /retrospective command

Priority 2:
  - [ ] Add Jenkins integration patterns
  - [ ] Add PR template detection
  - [ ] Add bulk import from CSV

Priority 3:
  - [ ] Automated deployment trigger on work item Done
  - [ ] Release notes auto-generation from closed work items
```

---

## 7. ntfy-plugin (v2.0.0)

### Current Strengths
- FREE push notifications (no account needed)
- Interactive two-way notification system
- 5 priority levels with emoji tagging
- Session-based auto-notification mode
- Rate limiting and deduplication
- Full notification history and analytics
- iOS and Android differences documented

### Gaps Identified

#### Gap 1: Fallback Notification Channels
If ntfy.sh is down or unreachable, there's no fallback. For a production notification system, this is a reliability concern.

**What to add**:
```python
def notify_with_fallback(title, message, priority="default"):
    """Try ntfy.sh first, fall back to Windows Toast or email."""
    try:
        send_ntfy(title, message, priority)
    except Exception:
        # Fallback 1: Windows Toast notification
        try:
            subprocess.run(['powershell', '-Command',
                f'New-BurntToastNotification -Text "{title}", "{message}"'])
        except Exception:
            # Fallback 2: Print to terminal
            print(f"[NOTIFICATION] {title}: {message}")
```

#### Gap 2: Notification Templates Per Task Type
Currently each notification is custom-built. A template system would reduce repetition.

**What to add** to the memory system:
```python
TEMPLATES = {
    "task_complete": {"title": "✅ Done: {task}", "priority": "default"},
    "error": {"title": "❌ Error in {module}", "priority": "urgent", "tags": "warning"},
    "server_ready": {"title": "🚀 Server Ready", "priority": "low"},
    "needs_input": {"title": "⏸️ Waiting for Input", "priority": "high"},
}
```

#### Gap 3: Notification Aggregation
Long-running tasks with many sub-steps can flood the phone. Need an aggregation mode.

**What to add**: A batching mode that collects multiple notifications and sends one summary after N seconds.

#### Gap 4: Desktop Notification via ntfy.sh Web Push
The plugin documents phone notifications but not browser/desktop web push via the ntfy.sh website.

### Recommended Actions

```
Priority 1 (Add to v2.1):
  - [ ] Add fallback notification to Windows Toast notification
  - [ ] Add TEMPLATES dictionary to SKILL.md for common task types

Priority 2:
  - [ ] Add notification aggregation/batching mode
  - [ ] Add webhook integration (call external URL on task complete)
```

---

## 8. pandoc-plugin (v1.0.0)

### Current Strengths
- 50+ input formats, 60+ output formats
- Complete command set (PDF, Word, HTML, EPUB, slides)
- Setup scripts for Windows/Linux/macOS
- Good format best practices memory file
- CI/CD integration examples

### Gaps Identified

#### Gap 1: Arabic / RTL Document Support
All your other Odoo plugins have Arabic RTL support, but pandoc has none. Converting Arabic documentation is common.

**What to add to `memories/format_best_practices.md`**:
```bash
# Arabic RTL PDF generation
pandoc input.md -o output.pdf \
  --pdf-engine=xelatex \
  --variable=mainfont:"Arial" \
  --variable=dir:rtl \
  --variable=lang:ar \
  --template=rtl-template.tex

# RTL HTML
pandoc input.md -o output.html \
  --metadata=lang:ar \
  -V dir=rtl
```

#### Gap 2: Variable Substitution in Templates
No support for dynamic content in pandoc documents (useful for generating reports with data).

**What to add**: A pattern using pandoc's `--metadata` and Jinja2 preprocessing:
```bash
# Use Python to pre-process with Jinja2, then convert
python preprocess.py template.md data.json | pandoc -o output.pdf
```

#### Gap 3: Odoo QWeb → Word/PDF Export Integration
Odoo already generates PDFs, but there's a gap when someone wants to export an Odoo template as a Word document for client editing.

**What to add**: A pattern for converting Odoo QWeb HTML output to Word using pandoc.

#### Gap 4: Corporate Template Library
No starter templates for common document types (proposal, invoice cover letter, technical spec).

**What to add**: A `templates/` directory with:
- `corporate-letter.md`
- `technical-spec.md`
- `proposal.md`
- `meeting-notes.md`

### Recommended Actions

```
Priority 1 (Add to v1.1):
  - [ ] Add Arabic/RTL PDF and HTML generation patterns
  - [ ] Add corporate template library (4 basic templates)

Priority 2:
  - [ ] Add variable substitution pattern with Jinja2 preprocessing
  - [ ] Add Odoo HTML → Word export pattern
  - [ ] Add batch processing workflow script
```

---

## 9. remotion-plugin (v1.0.0)

### Current Strengths
- Solves the critical continuous audio problem (voice never cuts between slides)
- Free edge-tts with 300+ voices
- Complete pipeline: text → scenes → voice → video
- TailwindCSS integration
- 4 composition templates
- Spring animation transitions
- Quality presets for rendering

### Gaps Identified

#### Gap 1: Social Media Format Presets
The plugin only documents standard video (1920×1080). Social media requires specific formats.

**What to add to `memories/composition_patterns.md`**:
```typescript
// Social media format presets
const FORMATS = {
    youtube: { width: 1920, height: 1080, fps: 30 },
    instagram_reel: { width: 1080, height: 1920, fps: 30 },  // 9:16
    instagram_post: { width: 1080, height: 1080, fps: 30 },  // 1:1
    linkedin: { width: 1280, height: 720, fps: 30 },
    tiktok: { width: 1080, height: 1920, fps: 60 },
    twitter: { width: 1280, height: 720, fps: 30 },
};
```

#### Gap 2: Auto-Subtitle Generation
The voice narration is generated but no subtitles/captions are added. This is critical for accessibility and social media.

**What to add**: A Python script that takes the TTS transcript timestamps and generates `.srt` or overlaid subtitle components in Remotion.

#### Gap 3: Background Music Layer
The continuous audio pattern handles voice, but background music (low-volume) is a common requirement.

**What to add to `memories/audio_patterns.md`**:
```typescript
// Mixing voice + background music
<Audio src={staticFile("background.mp3")} volume={0.1} />
<Audio src={staticFile("voice.mp3")} volume={1.0} />
```

#### Gap 4: Animated Data Visualization
No patterns for charts, counters, or data-driven animations (e.g., product stats, KPIs).

**What to add to `memories/composition_patterns.md`**: Animated bar chart, animated number counter (exists but without data binding), animated pie chart.

#### Gap 5: Thumbnail Generation
After rendering, no helper to generate a thumbnail from the first frame or a designated frame.

**What to add**:
```bash
# Extract thumbnail from frame 0
npx remotion still MyComposition --frame=0 --output=thumbnail.jpg
```

#### Gap 6: YouTube Upload / Social Publishing Helper
No post-render publishing workflow exists.

### Recommended Actions

```
Priority 1 (Add to v1.1):
  - [ ] Add social media format presets (Instagram, TikTok, LinkedIn)
  - [ ] Add background music mixing pattern
  - [ ] Add thumbnail generation command

Priority 2:
  - [ ] Add auto-subtitle generation from TTS timestamps
  - [ ] Add animated bar chart/counter components

Priority 3:
  - [ ] Add YouTube upload helper via yt-dlp or official API
  - [ ] Add brand kit system (logo overlay, color schemes per client)
```

---

## 10. codex-plugin (v1.0.0)

### Current Strengths
- 14 analysis/generation tools
- 7 prompts (code-review, security-audit, etc.)
- Broad language and framework support
- Good for generic code tasks

### Gaps Identified

#### Gap 1: No Odoo-Specific Knowledge (CRITICAL)
This is the most critical gap. The codex plugin is entirely generic. You have a multi-version Odoo installation with 30+ projects. An Odoo-specialized codex would be dramatically more useful.

**What to add**: An Odoo code review ruleset:
```
- Models must define _name, _description
- Computed fields must have @api.depends
- No direct write to core models without _inherit
- All new models need ir.model.access.csv entries
- No bare except: in Odoo models
- Use self.env.ref() not hardcoded IDs
- Use sudo() deliberately, not as default
- RecordSet operations should use mapped(), filtered(), sorted()
```

#### Gap 2: No ORM Best Practices Audit
The plugin has a generic security-audit but no ORM-specific check:
- N+1 query detection in Odoo methods
- Missing `store=True` on high-access computed fields
- Missing `index=True` on frequent search fields
- Unsafe `env.cr.execute()` (SQL injection risk)

#### Gap 3: Should Be an Odoo-Specific Plugin OR Merge Into Main Odoo Workflow
The codex plugin is currently generic enough that it adds minimal value over Claude's base capabilities. It should either:
- **Option A**: Specialize into `odoo-codex-plugin` with Odoo-specific rules
- **Option B**: Merge its capabilities into a new `odoo-dev-plugin` that handles general Odoo development tasks

### Recommended Actions

```
Priority 1:
  - [ ] Add Odoo-specific code review rules to SKILL.md
  - [ ] Add ORM best practices audit prompt
  - [ ] Add security patterns specific to Odoo (sudo, domain bypass, etc.)

OR

  - [ ] Consider transforming codex into odoo-codex specialized plugin
    with: code review, ORM analysis, security audit, performance hints
```

---

## 11. New Plugin Proposals

Based on analysis of your 6 Odoo versions and 30+ client projects, these plugins would fill major gaps in your current toolset:

---

### Proposal 1: `odoo-test-plugin` ⭐⭐⭐⭐⭐ (HIGHEST PRIORITY)

**Why**: Testing is a daily need across all 30+ projects but zero test-related tooling exists.

**What it would do**:
- Generate test classes with `@tagged` decorators from existing model definitions
- Create mock data factories (using `create()` with realistic values)
- Run tests with formatted output, filter by module or tag
- Generate test coverage reports
- Integrate with the devops plugin to post test results to Azure DevOps work items
- Detect missing tests for new methods (code coverage analysis)

**Core commands**:
```
/test-generate <model>     - Generate test skeleton for a model
/test-run <module>         - Run tests with nice output
/test-coverage <module>    - Show test coverage report
/test-data <model>         - Generate realistic demo data
```

**Skill file structure**:
```
odoo-test-plugin/
├── odoo-test/SKILL.md
├── commands/
│   ├── test-generate.md
│   ├── test-run.md
│   ├── test-coverage.md
│   └── test-data.md
├── memories/
│   ├── testing_patterns.md    - TransactionCase, HttpCase patterns
│   ├── mock_data.md           - Realistic test data by model type
│   └── tagged_strategies.md   - post_install vs at_install
└── scripts/
    ├── test_runner.py
    └── coverage_reporter.py
```

---

### Proposal 2: `odoo-security-plugin` ⭐⭐⭐⭐⭐ (HIGHEST PRIORITY)

**Why**: Security is critical for 30+ client projects. Missing access rules, insecure controllers, and improper sudo usage are common bugs that are hard to audit manually.

**What it would do**:
- Audit `ir.model.access.csv` completeness (every model has an entry)
- Check `@http.route` for proper `auth=` settings (no accidental `auth='none'` on sensitive routes)
- Detect `sudo()` usage without proper comment/justification
- Find SQL injection risks in `env.cr.execute()` calls
- Validate record rules don't conflict with each other
- Check group inheritance chains are correct
- Detect hard-coded user/group IDs

**Core commands**:
```
/security-audit <module>   - Full security audit
/check-access <model>      - Verify all access rules for a model
/find-sudo                 - List all sudo() calls with context
/check-routes <module>     - Audit all HTTP routes
```

---

### Proposal 3: `odoo-i18n-plugin` ⭐⭐⭐⭐ (HIGH PRIORITY)

**Why**: You have Arabic sites (Project Delta, khairgate, relief_center, sadad_invoice). The `TRANSLATION_GUIDELINES.md` exists in odoo19 but is not a plugin. Translation work is repeated across all projects.

**What it would do**:
- Generate `.pot` template files from module source
- Find missing translations (strings in code not in `.po` files)
- Validate `.po` file syntax
- Convert between translation formats
- Check RTL/LTR consistency in templates
- Apply translations from one version to another during upgrades
- Support Arabic, English, Turkish (your active languages)

**Core commands**:
```
/i18n-extract <module>     - Extract all translatable strings
/i18n-missing <module>     - Find untranslated strings
/i18n-validate <module>    - Validate .po file syntax
/i18n-export               - Export translations for external translator
/i18n-import               - Import translated .po file
```

---

### Proposal 4: `odoo-db-plugin` ⭐⭐⭐⭐ (HIGH PRIORITY)

**Why**: Managing 6 Odoo versions with 30+ databases requires database operations daily. No tooling exists for this.

**What it would do**:
- Database backup and restore automation
- Schema comparison between environments (dev vs prod)
- Demo data generation for test databases
- Database health checks (orphan records, broken constraints)
- Performance analysis (slow queries, missing indexes)
- Safe database duplication (dev copy from prod, sanitized)

**Core commands**:
```
/db-backup <db>            - Backup database with timestamp
/db-restore <db> <backup>  - Restore from backup
/db-clone <src> <dst>      - Clone database (sanitized)
/db-check <db>             - Health check and integrity scan
/db-demo <module>          - Load demo data for module testing
/db-compare <db1> <db2>    - Compare schemas between environments
```

---

### Proposal 5: `odoo-deploy-plugin` ⭐⭐⭐ (MEDIUM PRIORITY)

**Why**: You have production deployments across multiple clients. No deployment automation exists.

**What it would do**:
- Module deployment workflow (update → test → go-live)
- Multi-server deployment with rollback capability
- Zero-downtime deployment for critical modules
- Nginx/Apache configuration generation
- SSL certificate setup (Let's Encrypt)
- Server health monitoring after deployment
- Deployment log and audit trail

**Core commands**:
```
/deploy <module> <env>     - Deploy module to environment
/deploy-rollback <env>     - Roll back last deployment
/deploy-status             - Check deployment health
/deploy-config <project>   - Generate server configuration
```

---

### Proposal 6: `odoo-performance-plugin` ⭐⭐⭐ (MEDIUM PRIORITY)

**Why**: Large projects (TAQAT with 143+ modules, taqat-property with 96+) have performance concerns.

**What it would do**:
- Odoo profiler integration (identify slow methods)
- N+1 query detection in model code
- RPC call count monitoring
- Memory usage tracking per request
- Worker configuration calculator
- Cache hit rate analysis
- Identify missing `store=True` on heavy computed fields
- `limit_memory_soft/hard` configuration guidance

**Core commands**:
```
/perf-profile <url>        - Profile a web request
/perf-queries <module>     - Find N+1 query risks
/perf-config <workers> <ram> - Calculate optimal server config
/perf-report               - Generate performance report
```

---

### Proposal 7: `odoo-gitflow-plugin` ⭐⭐⭐ (MEDIUM PRIORITY)

**Why**: Multiple developers work on the same projects. No Git workflow automation exists beyond what the devops plugin provides.

**What it would do**:
- Branch creation with naming conventions (`feature/AB#1234-description`)
- Pre-commit hook setup for Odoo (Python lint, XML validation)
- Automated changelog generation from commits
- Module version bumping with Git tag
- Branch cleanup after merge
- Merge conflict resolution hints for Odoo-specific files

**Core commands**:
```
/git-feature <workitem>    - Create feature branch linked to work item
/git-commit <module>       - Commit with proper message format
/git-changelog             - Generate changelog from commits
/git-bump <module>         - Bump module version + tag
/git-cleanup               - Clean merged branches
```

---

### Proposal 8: `odoo-api-docs-plugin` ⭐⭐ (LOW-MEDIUM PRIORITY)

**Why**: The khairgate project has 40+ REST API endpoints. Maintaining API documentation is manual and error-prone.

**What it would do**:
- Generate OpenAPI/Swagger spec from `@http.route` decorators
- Generate Postman collection from controllers
- API endpoint health check
- Request/response schema validation
- Changelog between API versions
- Client SDK generation (Python, JavaScript)

**Core commands**:
```
/api-docs <module>         - Generate OpenAPI spec
/api-postman <module>      - Generate Postman collection
/api-test <endpoint>       - Test endpoint with sample data
/api-changelog <v1> <v2>   - Compare API versions
```

---

## 12. Cross-Plugin Integration Opportunities

These are workflow combinations that would unlock powerful automation:

### Integration 1: Upgrade + Test (odoo-upgrade + odoo-test)
After running an upgrade script, automatically run the test suite for the upgraded module and post results to Azure DevOps.

```
/upgrade-and-test <module> <version>
→ odoo-upgrade: applies all transformations
→ odoo-test: runs test suite
→ devops: updates work item with test results
→ ntfy: sends notification when done
```

### Integration 2: Report + Deploy (odoo-report + devops)
After creating/modifying a report template, automatically create a pull request with the changes.

```
/report-pr <template_name>
→ odoo-report: validates template
→ devops: creates PR with template changes
→ ntfy: notifies reviewer
```

### Integration 3: Figma + Theme + Deploy (odoo-frontend + devops)
Complete theme workflow from Figma to Azure DevOps work item.

```
/theme-from-figma <figma-url> <project>
→ odoo-frontend: extracts design tokens from Figma
→ odoo-frontend: generates theme module
→ devops: creates work item for theme implementation
→ ntfy: notifies when theme is ready for review
```

### Integration 4: Security + DevOps (odoo-security + devops)
Auto-create security work items for found vulnerabilities.

```
/security-audit-report <module>
→ odoo-security: runs full audit
→ devops: creates bug work items for each finding
→ ntfy: sends urgent notification for critical issues
```

### Integration 5: Video + DevOps (remotion + devops)
Generate sprint demo video automatically from completed work items.

```
/sprint-demo-video
→ devops: fetches completed work items from sprint
→ remotion: generates demo video with voice narration
→ ntfy: sends notification with video link
```

---

## 13. Priority Matrix

### Immediate (Do Now — High Impact, Low Effort)

| Item | Plugin | Effort | Impact |
|------|--------|--------|--------|
| Add `type='json'` → `type='jsonrpc'` auto-fix | odoo-upgrade | 1 hour | Critical |
| Add `attrs={}` → inline expression migration | odoo-upgrade | 3 hours | Critical |
| Add QR code pattern for ZATCA compliance | odoo-report | 1 hour | High |
| Add dark mode toggle publicWidget pattern | odoo-frontend | 30 min | High |
| Add Arabic RTL patterns to pandoc | pandoc | 1 hour | Medium |
| Add social media format presets to remotion | remotion | 30 min | Medium |
| Add Odoo security audit rules to codex | codex | 2 hours | High |
| Add notification templates to ntfy | ntfy | 1 hour | Medium |

### Short Term (This Month — High Impact, Medium Effort)

| Item | Plugin | Effort | Impact |
|------|--------|--------|--------|
| Build `odoo-test-plugin` v1.0 | NEW | 1 week | Critical |
| Add OWL 1.x → 2.0 migration section | odoo-upgrade | 1 day | High |
| Add GitHub integration memory to devops | devops | 2 hours | High |
| Add report wizard pattern | odoo-report | 2 hours | High |
| Add Odoo 19 snippet API changes | odoo-frontend | 2 hours | High |
| Add `odoo-security-plugin` v1.0 | NEW | 1 week | High |
| Add `odoo-i18n-plugin` v1.0 | NEW | 3 days | High |

### Medium Term (Next Quarter — Strategic Improvements)

| Item | Plugin | Effort | Impact |
|------|--------|--------|--------|
| Build `odoo-db-plugin` v1.0 | NEW | 2 weeks | High |
| Build `odoo-deploy-plugin` v1.0 | NEW | 2 weeks | Medium |
| Build `odoo-gitflow-plugin` v1.0 | NEW | 1 week | Medium |
| Add Odoo 14/15 → 17 patterns | odoo-upgrade | 3 days | Medium |
| Add cross-plugin integration workflows | All | 1 week | High |
| Transform codex → odoo-codex | codex | 1 week | Medium |

---

## Summary: Total Enhancement Count

| Plugin | Gaps Found | New Features | Priority |
|--------|-----------|-------------|---------|
| odoo-upgrade | 7 gaps | 2 new scripts, 2 new pattern files | P1 |
| odoo-frontend | 7 gaps | 4 new memory patterns | P1 |
| odoo-report | 8 gaps | 3 new templates, 1 new section | P1 |
| devops | 6 gaps | 2 new memory files, 1 new command | P2 |
| ntfy | 4 gaps | 1 new script, 1 template dict | P2 |
| pandoc | 4 gaps | 1 new section, 4 templates | P2 |
| remotion | 6 gaps | 3 new patterns, 1 new script | P2 |
| codex | 3 gaps | Full specialization needed | P2 |
| **NEW: odoo-test** | — | Full new plugin | P1 |
| **NEW: odoo-security** | — | Full new plugin | P1 |
| **NEW: odoo-i18n** | — | Full new plugin | P2 |
| **NEW: odoo-db** | — | Full new plugin | P2 |
| **NEW: odoo-deploy** | — | Full new plugin | P3 |
| **NEW: odoo-performance** | — | Full new plugin | P3 |
| **NEW: odoo-gitflow** | — | Full new plugin | P3 |
| **NEW: odoo-api-docs** | — | Full new plugin | P3 |

**Total gaps addressed**: 45
**New plugins proposed**: 8
**Immediate quick wins (< 1 day each)**: 8

---

*Report generated: February 2026*
*Based on: Full analysis of all plugin SKILL.md files, changelogs, session learnings, memory files, pattern libraries, error catalogs, and cross-reference with 6 Odoo versions and 30+ active client projects.*
