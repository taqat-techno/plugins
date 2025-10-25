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

                # Update version to 19.0.x.x.x format
                content = re.sub(
                    r"'version'\s*:\s*['\"]([0-9.]+)['\"]",
                    lambda m: f"'version': '19.0.{m.group(1).replace('.', '.')}.0'",
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

                # 1. Convert tree to list views
                content = re.sub(r'<tree(\s+[^>]*)?>', r'<list\1>', content)
                content = content.replace('</tree>', '</list>')

                # 2. Fix search views - remove group tags
                content = self._fix_search_views(content)

                # 3. Fix kanban templates
                content = content.replace('t-name="kanban-box"', 't-name="card"')

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

        for js_file in js_files:
            if 'node_modules' in str(js_file) or '.min.js' in str(js_file):
                continue

            try:
                with open(js_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                original = content

                # Remove RPC service import
                content = re.sub(
                    r'this\.rpc\s*=\s*useService\(["\']rpc["\']\);?\s*\n?',
                    '',
                    content
                )

                # Replace this.rpc calls
                content = content.replace('this.rpc(', 'this._jsonRpc(')

                # Add _jsonRpc method if needed
                if 'this._jsonRpc(' in content and '_jsonRpc(endpoint, params' not in content:
                    # Find setup() method and add after it
                    setup_pattern = r'(setup\(\)\s*\{[^}]*\})'

                    def add_method(match):
                        return match.group(0) + json_rpc_method

                    content = re.sub(setup_pattern, add_method, content, count=1)

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

    def run(self):
        """Run the complete upgrade process"""
        print("\n Starting Odoo 19 Upgrade Process\n")
        print("=" * 50)

        # Step 1: Backup
        print("\n Step 1: Creating backup...")
        self.create_backup()

        # Step 2: Manifests
        print("\n Step 2: Updating manifest files...")
        self.update_manifest_files()

        # Step 3: XML Views
        print("\n Step 3: Fixing XML views...")
        self.fix_xml_views()

        # Step 4: Python Code
        print("\n Step 4: Updating Python code...")
        self.update_python_code()

        # Step 5: JavaScript
        print("\n Step 5: Migrating JavaScript RPC...")
        self.migrate_javascript_rpc()

        # Step 6: SCSS
        print("\n Step 6: Updating SCSS files...")
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
