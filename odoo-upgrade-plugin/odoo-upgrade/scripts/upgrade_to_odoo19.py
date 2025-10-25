#!/usr/bin/env python3
"""
Comprehensive Odoo 17/18 to Odoo 19 Upgrade Script
Handles all major compatibility issues automatically
"""

import os
import re
import sys
import glob
import shutil
from pathlib import Path
from datetime import datetime


class Odoo19Upgrader:
    """Main upgrader class for Odoo 19 migration"""

    def __init__(self, project_path):
        self.project_path = Path(project_path)
        self.backup_path = None
        self.report = []
        self.errors = []

    def create_backup(self):
        """Create backup of the project"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{self.project_path.name}_backup_{timestamp}"
        self.backup_path = self.project_path.parent / backup_name

        print(f"Creating backup at: {self.backup_path}")
        shutil.copytree(self.project_path, self.backup_path)
        self.report.append(f"[OK] Backup created: {self.backup_path}")
        return self.backup_path

    def update_manifest_files(self):
        """Update all __manifest__.py files for Odoo 19"""
        manifest_files = self.project_path.glob("**/__manifest__.py")
        updated = 0

        for manifest in manifest_files:
            try:
                with open(manifest, 'r', encoding='utf-8') as f:
                    content = f.read()

                original = content

                # Fix version format - extract numeric version and format properly
                def fix_version(match):
                    version = match.group(1)
                    # Remove any existing 19.0. prefix if duplicated
                    version = re.sub(r'^19\.0\.', '', version)
                    # Extract just the numeric parts
                    parts = re.findall(r'\d+', version)
                    if len(parts) < 3:
                        parts.extend(['0'] * (3 - len(parts)))
                    return f"'version': '19.0.{'.'.join(parts[:3])}'"

                content = re.sub(
                    r"'version'\s*:\s*['\"]([^'\"]+)['\"]",
                    fix_version,
                    content
                )

                # Add license if missing
                if "'license'" not in content:
                    # Add after version
                    content = re.sub(
                        r"('version'\s*:\s*[^,]+,)",
                        r"\1\n    'license': 'LGPL-3',",
                        content
                    )

                if content != original:
                    with open(manifest, 'w', encoding='utf-8') as f:
                        f.write(content)
                    updated += 1
                    print(f"  [OK] Updated: {manifest.name}")

            except Exception as e:
                self.errors.append((str(manifest), str(e)))
                print(f"  [ERROR] Error updating {manifest}: {e}")

        self.report.append(f"[OK] Updated {updated} manifest files")
        return updated

    def fix_xml_views(self):
        """Fix all XML view issues for Odoo 19"""
        xml_files = list(self.project_path.glob("**/*.xml"))
        fixed = 0

        for xml_file in xml_files:
            try:
                with open(xml_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                original = content

                # First, fix any existing malformed comments (from previous runs)
                content = self._fix_malformed_comments(content)

                # 1. Convert tree to list views
                content = re.sub(r'<tree(\s+[^>]*)?>', r'<list\1>', content)
                content = content.replace('</tree>', '</list>')

                # 2. Fix search views - remove group tags
                content = self._fix_search_views(content)

                # 3. Fix kanban templates
                content = content.replace('t-name="kanban-box"', 't-name="card"')

                # Remove js_class="crm_kanban" as it's not available outside CRM
                content = re.sub(r'\s+js_class=["\']crm_kanban["\']', '', content)

                # 4. Remove numbercall from cron jobs
                content = re.sub(
                    r'\s*<field\s+name="numbercall"[^>]*>.*?</field>',
                    '',
                    content,
                    flags=re.DOTALL
                )
                content = re.sub(
                    r'\s*<field\s+name="numbercall"[^/]*/>',
                    '',
                    content
                )

                # 5. Fix active_id references
                content = re.sub(
                    r"context=['\"]([^'\"]*?)active_id([^'\"]*?)['\"]",
                    r"context='\1id\2'",
                    content
                )

                # 6. Remove edit="1" from views
                content = re.sub(r'\s+edit=["\']1["\']', '', content)

                # 7. Remove website.snippet_options inheritance (doesn't exist in Odoo 19)
                # Comment out instead of removing to preserve the code
                if 'inherit_id="website.snippet_options"' in content:
                    # Find and comment out the entire template
                    pattern = r'(<template[^>]*inherit_id="website\.snippet_options"[^>]*>.*?</template>)'
                    def comment_template(match):
                        template_content = match.group(1)
                        # Escape any existing double hyphens in the content to avoid XML comment errors
                        template_content = template_content.replace('--', '- -')
                        return f'''<!-- website.snippet_options removed in Odoo 19 - The snippet system has been redesigned
       This template has been disabled
  {template_content}
  -->'''
                    content = re.sub(pattern, comment_template, content, flags=re.DOTALL)

                # 8. Fix view_mode in act_window actions
                # Replace standalone 'tree'
                content = re.sub(
                    r'(<field name="view_mode">)tree(</field>)',
                    r'\1list\2',
                    content
                )
                # Replace 'tree,' with 'list,'
                content = re.sub(
                    r'(<field name="view_mode">)tree,',
                    r'\1list,',
                    content
                )
                # Replace ',tree' with ',list'
                content = re.sub(
                    r',tree([,<])',
                    r',list\1',
                    content
                )
                # Fix view_mode in view_ids
                content = re.sub(
                    r"'view_mode':\s*'tree'",
                    r"'view_mode': 'list'",
                    content
                )

                if content != original:
                    with open(xml_file, 'w', encoding='utf-8') as f:
                        f.write(content)
                    fixed += 1
                    print(f"  [OK] Fixed: {xml_file.name}")

            except Exception as e:
                self.errors.append((str(xml_file), str(e)))
                print(f"  [ERROR] Error fixing {xml_file}: {e}")

        self.report.append(f"[OK] Fixed {fixed} XML files")
        return fixed

    def _fix_malformed_comments(self, content):
        """Fix malformed XML comments from previous runs"""
        # Fix nested/duplicated comment starts
        pattern = r'<!--[^>]*<!--'
        while re.search(pattern, content):
            content = re.sub(pattern, '<!-- ', content)

        # Fix nested/duplicated comment ends
        pattern = r'-->[^<]*-->'
        while re.search(pattern, content):
            content = re.sub(pattern, ' -->', content)

        # Fix double hyphens within comments (except at boundaries)
        def fix_comment_hyphens(match):
            comment = match.group(0)
            # Replace internal double hyphens
            inner = comment[4:-3]  # Extract content between <!-- and -->
            inner = re.sub(r'--+', '- -', inner)
            return f'<!--{inner}-->'

        content = re.sub(r'<!--.*?-->', fix_comment_hyphens, content, flags=re.DOTALL)

        return content

    def _fix_search_views(self, content):
        """Remove group tags from search views"""
        pattern = r'(<search[^>]*>)(.*?)(</search>)'

        def remove_groups(match):
            search_start = match.group(1)
            search_content = match.group(2)
            search_end = match.group(3)

            # Remove group tags
            search_content = re.sub(r'<group[^>]*>', '', search_content)
            search_content = search_content.replace('</group>', '')

            # Add separator before group_by filters
            if 'group_by' in search_content and '<separator/>' not in search_content:
                search_content = re.sub(
                    r'(\s*)(<filter[^>]*group_by[^>]*>)',
                    r'\1<separator/>\1\2',
                    search_content,
                    count=1
                )

            return search_start + search_content + search_end

        return re.sub(pattern, remove_groups, content, flags=re.DOTALL)

    def update_python_code(self):
        """Update Python code for Odoo 19 compatibility"""
        py_files = list(self.project_path.glob("**/*.py"))
        updated = 0

        for py_file in py_files:
            if '__pycache__' in str(py_file):
                continue

            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                original = content

                # Remove slug/unslug imports from old location
                content = re.sub(
                    r'from\s+odoo\.addons\.http_routing\.models\.ir_http\s+import\s+[^,\n]*slug[^,\n]*,?\s*[^,\n]*unslug[^,\n]*,?\s*',
                    '',
                    content
                )

                # Replace url_for usage
                content = re.sub(
                    r'from\s+odoo\.addons\.http_routing\.models\.ir_http\s+import\s+url_for',
                    '',
                    content
                )
                content = re.sub(
                    r'\burl_for\(',
                    r"self.env['ir.http']._url_for(",
                    content
                )

                if content != original:
                    with open(py_file, 'w', encoding='utf-8') as f:
                        f.write(content)
                    updated += 1
                    print(f"  [OK] Updated: {py_file.name}")

            except Exception as e:
                self.errors.append((str(py_file), str(e)))
                print(f"  [ERROR] Error updating {py_file}: {e}")

        self.report.append(f"[OK] Updated {updated} Python files")
        return updated

    def migrate_javascript_rpc(self):
        """Migrate JavaScript RPC service to fetch API"""
        js_files = list(self.project_path.glob("**/*.js"))
        migrated = 0

        json_rpc_method = '''
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
                throw new Error(data.error.message || 'RPC call failed');
            }
            return data.result;
        } catch (error) {
            console.error('JSON-RPC call failed:', error);
            throw error;
        }
    }'''

        # Helper function for services that use jsonrpc directly
        jsonrpc_function = '''
// JSON-RPC helper function for Odoo 19 (replaces rpc service)
async function jsonrpc(endpoint, params = {}) {
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
            throw new Error(data.error.message || 'RPC call failed');
        }
        return data.result;
    } catch (error) {
        console.error('JSON-RPC call failed:', error);
        throw error;
    }
}'''

        for js_file in js_files:
            if 'node_modules' in str(js_file) or '.min.js' in str(js_file):
                continue

            try:
                with open(js_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                original = content

                # Remove import of jsonrpc from RPC service
                if 'import {jsonrpc} from "@web/core/network/rpc_service"' in content:
                    content = content.replace('import {jsonrpc} from "@web/core/network/rpc_service";', '')
                    # Add the jsonrpc function after imports
                    import_end = content.find('const ')
                    if import_end == -1:
                        import_end = content.find('export ')
                    if import_end > 0:
                        content = content[:import_end] + '\n' + jsonrpc_function + '\n' + content[import_end:]

                # Remove RPC service usage
                content = re.sub(
                    r'this\.rpc\s*=\s*useService\(["\']rpc["\']\);?\s*\n?',
                    '',
                    content
                )

                # Replace this.rpc calls
                content = content.replace('this.rpc(', 'this._jsonRpc(')

                # Add _jsonRpc method if needed for components
                if 'this._jsonRpc(' in content and '_jsonRpc(endpoint, params' not in content:
                    # Check if this is inside a component class setup
                    if 'setup()' in content:
                        # Find the end of setup() method
                        setup_match = re.search(r'setup\(\)\s*\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}', content)
                        if setup_match:
                            # Add the method as a class method after setup
                            setup_end = setup_match.end()
                            content = content[:setup_end] + '\n' + json_rpc_method + '\n' + content[setup_end:]

                if content != original:
                    with open(js_file, 'w', encoding='utf-8') as f:
                        f.write(content)
                    migrated += 1
                    print(f"  [OK] Migrated: {js_file.name}")

            except Exception as e:
                self.errors.append((str(js_file), str(e)))
                print(f"  [ERROR] Error migrating {js_file}: {e}")

        self.report.append(f"[OK] Migrated {migrated} JavaScript files")
        return migrated

    def update_scss_files(self):
        """Update SCSS files for Odoo 19 compatibility"""
        scss_files = list(self.project_path.glob("**/*.scss"))
        updated = 0

        for scss_file in scss_files:
            if 'node_modules' in str(scss_file):
                continue

            try:
                with open(scss_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                original = content

                # Fix headings font weight variable
                content = re.sub(
                    r'\$headings-font-weight:',
                    '$o-theme-headings-font-weight:',
                    content
                )

                # Add menu/footer/copyright to color palettes if missing
                if 'o-color-palettes' in content and "'menu':" not in content:
                    content = re.sub(
                        r"('o-color-5':\s*[^,]+,?)(\s*\))",
                        r"\1,\2        'menu': 4,\2        'footer': 1,\2        'copyright': 5,\2",
                        content
                    )

                if content != original:
                    with open(scss_file, 'w', encoding='utf-8') as f:
                        f.write(content)
                    updated += 1
                    print(f"  [OK] Updated: {scss_file.name}")

            except Exception as e:
                self.errors.append((str(scss_file), str(e)))
                print(f"  [ERROR] Error updating {scss_file}: {e}")

        self.report.append(f"[OK] Updated {updated} SCSS files")
        return updated

    def generate_report(self):
        """Generate migration report"""
        report_path = self.project_path / "MIGRATION_REPORT_ODOO19.md"

        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("# Odoo 19 Migration Report\n\n")
            f.write(f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
            f.write(f"**Project**: {self.project_path.name}\n\n")

            f.write("## Summary\n\n")
            for item in self.report:
                f.write(f"- {item}\n")

            if self.errors:
                f.write("\n## Errors\n\n")
                for file, error in self.errors:
                    f.write(f"- **{file}**: {error}\n")

            if self.backup_path:
                f.write(f"\n## Backup\n\nBackup saved at: `{self.backup_path}`\n")

            f.write("\n## Testing Instructions\n\n")
            f.write("```bash\n")
            f.write("# Create test database\n")
            f.write("python -m odoo -d test_db -i base --stop-after-init\n\n")
            f.write("# Install modules\n")
            f.write("python -m odoo -d test_db -i your_module --stop-after-init\n")
            f.write("```\n")

        print(f"\n[OK] Report saved to: {report_path}")
        return report_path

    def check_python_dependencies(self):
        """Check and list Python dependencies from all manifests"""
        dependencies = set()
        manifest_files = self.project_path.glob("**/__manifest__.py")

        for manifest in manifest_files:
            try:
                with open(manifest, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Find external_dependencies section
                match = re.search(r"'external_dependencies'\s*:\s*\{[^}]*'python'\s*:\s*\[([^\]]+)\]", content, re.DOTALL)
                if match:
                    deps_str = match.group(1)
                    # Extract individual dependencies
                    deps = re.findall(r"'([^']+)'", deps_str)
                    dependencies.update(deps)

            except Exception as e:
                print(f"  [WARNING] Could not check dependencies in {manifest}: {e}")

        if dependencies:
            print(f"\n[INFO] Found Python dependencies: {', '.join(dependencies)}")
            print("[TIP] Install them with: pip install " + " ".join(dependencies))
            self.report.append(f"[INFO] Python dependencies found: {', '.join(dependencies)}")

        return dependencies

    def run(self):
        """Run the complete upgrade process"""
        print("\n Starting Odoo 19 Upgrade Process\n")
        print("=" * 50)

        # Step 1: Backup
        print("\n Step 1: Creating backup...")
        self.create_backup()

        # Step 2: Check Dependencies
        print("\n Step 2: Checking Python dependencies...")
        self.check_python_dependencies()

        # Step 3: Manifests
        print("\n Step 3: Updating manifest files...")
        self.update_manifest_files()

        # Step 4: XML Views
        print("\n Step 4: Fixing XML views...")
        self.fix_xml_views()

        # Step 5: Python Code
        print("\n Step 5: Updating Python code...")
        self.update_python_code()

        # Step 6: JavaScript
        print("\n Step 6: Migrating JavaScript RPC...")
        self.migrate_javascript_rpc()

        # Step 7: SCSS
        print("\n Step 7: Updating SCSS files...")
        self.update_scss_files()

        # Generate report
        print("\n Generating migration report...")
        self.generate_report()

        print("\n" + "=" * 50)
        print("[SUCCESS] Odoo 19 Upgrade Complete!")

        if self.errors:
            print(f"\n[WARNING]  {len(self.errors)} errors encountered. Check the report for details.")


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python upgrade_to_odoo19.py <project_path>")
        sys.exit(1)

    project_path = sys.argv[1]

    if not os.path.exists(project_path):
        print(f"Error: Path '{project_path}' does not exist")
        sys.exit(1)

    upgrader = Odoo19Upgrader(project_path)
    upgrader.run()


if __name__ == "__main__":
    main()
