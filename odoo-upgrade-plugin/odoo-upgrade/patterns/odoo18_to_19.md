# Odoo 18 to 19 Migration Patterns

## 🔴 CRITICAL Breaking Changes (Must Fix)

### 1. XML View Type Renamed
**Impact**: CRITICAL - Installation will fail
**Error**: `Invalid view type: 'tree'`

#### Issue
- ALL `<tree>` view tags have been renamed to `<list>` in Odoo 19
- Affects all tree view definitions

#### Detection
```bash
grep -r "<tree" --include="*.xml"
grep -r "</tree>" --include="*.xml"
```

#### Fix
```xml
<!-- BEFORE (Odoo 17/18) -->
<tree string="Items" editable="top">
    <field name="name"/>
</tree>

<!-- AFTER (Odoo 19) -->
<list string="Items" editable="top">
    <field name="name"/>
</list>
```

### 2. Search View Group Tags Removed
**Impact**: CRITICAL - Installation will fail
**Error**: `Invalid view definition`

#### Issue
- `<group>` tags are NO LONGER ALLOWED inside `<search>` views
- All filters must be at root level

#### Detection
```bash
grep -A5 -B5 "<group.*Group By" --include="*.xml"
```

#### Fix
```xml
<!-- BEFORE (Odoo 17/18) -->
<search>
    <field name="name"/>
    <group expand="0" string="Group By">
        <filter name="type" string="Type" context="{'group_by': 'type_id'}"/>
    </group>
</search>

<!-- AFTER (Odoo 19) -->
<search>
    <field name="name"/>
    <separator/>
    <filter name="type" string="Group by Type" context="{'group_by': 'type_id'}"/>
</search>
```

### 3. Action Window view_mode References
**Impact**: CRITICAL - Runtime error
**Error**: `View types not defined tree found in act_window`

#### Issue
- Action windows still reference 'tree' in view_mode field
- Must be changed to 'list' for Odoo 19 compatibility

#### Detection
```bash
grep -r "view_mode.*tree" --include="*.xml"
```

#### Fix
```xml
<!-- BEFORE (Odoo 17/18) -->
<field name="view_mode">tree,form</field>
<field name="view_mode">kanban,tree,form</field>

<!-- AFTER (Odoo 19) -->
<field name="view_mode">list,form</field>
<field name="view_mode">kanban,list,form</field>
```

### 4. Cron Job numbercall Field Removed
**Impact**: HIGH - Installation will fail
**Error**: `Invalid field 'numbercall' in 'ir.cron'`

#### Issue
- The `numbercall` field has been completely removed from cron jobs

#### Detection
```bash
grep -r "numbercall" --include="*.xml"
```

#### Fix
```xml
<!-- BEFORE (Odoo 17/18) -->
<record id="cron_job" model="ir.cron">
    <field name="name">My Cron Job</field>
    <field name="interval_number">1</field>
    <field name="interval_type">days</field>
    <field name="numbercall">-1</field> <!-- REMOVE THIS LINE -->
</record>

<!-- AFTER (Odoo 19) -->
<record id="cron_job" model="ir.cron">
    <field name="name">My Cron Job</field>
    <field name="interval_number">1</field>
    <field name="interval_type">days</field>
    <!-- numbercall field removed -->
</record>
```

## 🟡 Major Changes

### 4. RPC Service Removal in Frontend
**Impact**: HIGH
**Affected**: All public website components using RPC

The `rpc` service is no longer available in frontend/public components in Odoo 19.

#### Detection
```javascript
grep -r "useService.*['\"]rpc['\"]" --include="*.js"
```

#### Solution
Replace with fetch-based JSON-RPC calls. Add this helper to each affected component:

```javascript
async _jsonRpc(endpoint, params = {}) {
    try {
        const response = await fetch(endpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Csrf-Token': document.querySelector('meta[name="csrf-token"]')?.content || '',
            },
            body: JSON.stringify({
                jsonrpc: "2.0",
                method: "call",
                params: params,
                id: Math.floor(Math.random() * 1000000)
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        if (data.error) {
            console.error('JSON-RPC Error:', data.error);
            throw new Error(data.error.message || 'RPC call failed');
        }
        return data.result;
    } catch (error) {
        console.error('JSON-RPC call failed:', error);
        throw error;
    }
}
```

### 5. Kanban Template Name Change
**Impact**: MEDIUM

#### Issue
- Kanban box template name changed from `kanban-box` to `card`

#### Fix
```xml
<!-- BEFORE -->
<t t-name="kanban-box">

<!-- AFTER -->
<t t-name="card">
```

### 6. URL Generation Changes
**Impact**: MEDIUM

#### Issue
- `url_for` import location changed and should use IR.http service

#### Fix
```python
# BEFORE
from odoo.addons.http_routing.models.ir_http import url_for
url = url_for('/path')

# AFTER
url = self.env['ir.http']._url_for('/path')
```

### 7. Context active_id Changes
**Impact**: LOW

#### Issue
- `active_id` not available in some form view contexts

#### Fix
```xml
<!-- BEFORE -->
context="{'default_type_id': active_id}"

<!-- AFTER -->
context="{'default_type_id': id}"
```

## 🟢 Theme/SCSS Changes

### 8. SCSS Variable Updates
**Impact**: LOW

#### Issue
- Some SCSS variables renamed for consistency

#### Fix
```scss
// BEFORE
$headings-font-weight: 700;

// AFTER
$o-theme-headings-font-weight: 700;
```

### 9. Color Palette Menu/Footer
**Impact**: LOW

#### Issue
- Themes need explicit menu/footer color assignments

#### Fix
```scss
$o-color-palettes: (
    'my_theme': (
        'o-color-1': #207AB7,
        'o-color-2': #FB9F54,
        'o-color-3': #F6F4F0,
        'o-color-4': #ffffff,
        'o-color-5': #191A19,
        'menu': 4,        // Add these
        'footer': 1,      // Add these
        'copyright': 5,   // Add these
    ),
);
```

## Automated Upgrade Script

Use the comprehensive upgrade script:
```bash
python upgrade_to_odoo19.py /path/to/project
```

This script automatically handles:
- ✅ Tree to List view conversion
- ✅ Search view group removal
- ✅ Cron job numbercall removal
- ✅ RPC service migration
- ✅ Manifest version updates
- ✅ Python API updates
- ✅ SCSS variable fixes

## Quick Checklist

- [ ] Run upgrade script first
- [ ] Check for any remaining `<tree>` tags
- [ ] Verify no `<group>` in search views
- [ ] Remove all `numbercall` fields
- [ ] Test RPC calls in JavaScript
- [ ] Update manifest versions
- [ ] Test module installation
- [ ] Run tests