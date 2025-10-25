#!/usr/bin/env python3
"""
Quick Fix Script for Common Odoo 19 Issues
Applies targeted fixes for specific compatibility problems
"""

import os
import re
import sys
from pathlib import Path


class QuickFixer:
    """Quick fixes for common Odoo 19 issues"""

    def __init__(self, project_path):
        self.project_path = Path(project_path)
        self.fixes_applied = []

    def fix_tree_views(self):
        """Fix all tree view references"""
        print("\n[1/6] Fixing tree view references...")
        count = 0

        for xml_file in self.project_path.glob("**/*.xml"):
            try:
                with open(xml_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                original = content

                # Fix tree tags
                content = re.sub(r'<tree(\s+[^>]*)?>', r'<list\1>', content)
                content = content.replace('</tree>', '</list>')

                # Fix view_mode references
                content = re.sub(r'(<field name="view_mode">)tree(</field>)', r'\1list\2', content)
                content = re.sub(r'(<field name="view_mode">)tree,', r'\1list,', content)
                content = re.sub(r',tree([,<])', r',list\1', content)
                content = re.sub(r"'view_mode':\s*'tree'", r"'view_mode': 'list'", content)

                if content != original:
                    with open(xml_file, 'w', encoding='utf-8') as f:
                        f.write(content)
                    count += 1

            except Exception as e:
                print(f"  Error processing {xml_file.name}: {e}")

        self.fixes_applied.append(f"Fixed tree views in {count} files")
        print(f"  [OK] Fixed {count} files")

    def fix_search_groups(self):
        """Remove group tags from search views"""
        print("\n[2/6] Fixing search view groups...")
        count = 0

        for xml_file in self.project_path.glob("**/*.xml"):
            try:
                with open(xml_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                original = content

                # Remove group tags from search views
                pattern = r'(<search[^>]*>)(.*?)(</search>)'

                def remove_groups(match):
                    search_start = match.group(1)
                    search_content = match.group(2)
                    search_end = match.group(3)

                    if '<group' in search_content:
                        # Remove group tags
                        search_content = re.sub(r'<group[^>]*>', '', search_content)
                        search_content = search_content.replace('</group>', '')

                        # Add separator if needed
                        if 'group_by' in search_content and '<separator/>' not in search_content:
                            search_content = re.sub(
                                r'(\s*)(<filter[^>]*group_by[^>]*>)',
                                r'\1<separator/>\1\2',
                                search_content,
                                count=1
                            )

                    return search_start + search_content + search_end

                content = re.sub(pattern, remove_groups, content, flags=re.DOTALL)

                if content != original:
                    with open(xml_file, 'w', encoding='utf-8') as f:
                        f.write(content)
                    count += 1

            except Exception as e:
                print(f"  Error processing {xml_file.name}: {e}")

        self.fixes_applied.append(f"Fixed search groups in {count} files")
        print(f"  [OK] Fixed {count} files")

    def fix_js_class(self):
        """Remove problematic js_class attributes"""
        print("\n[3/6] Fixing js_class attributes...")
        count = 0

        for xml_file in self.project_path.glob("**/*.xml"):
            try:
                with open(xml_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                original = content

                # Remove crm_kanban js_class
                content = re.sub(r'\s+js_class=["\']crm_kanban["\']', '', content)

                # Optionally remove all js_class from kanban views if they cause issues
                # content = re.sub(r'\s+js_class=["\'][^"\']*["\']', '', content)

                if content != original:
                    with open(xml_file, 'w', encoding='utf-8') as f:
                        f.write(content)
                    count += 1

            except Exception as e:
                print(f"  Error processing {xml_file.name}: {e}")

        self.fixes_applied.append(f"Fixed js_class in {count} files")
        print(f"  [OK] Fixed {count} files")

    def fix_cron_numbercall(self):
        """Remove numbercall from cron jobs"""
        print("\n[4/6] Fixing cron numbercall fields...")
        count = 0

        for xml_file in self.project_path.glob("**/*.xml"):
            try:
                with open(xml_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                original = content

                # Remove numbercall fields
                content = re.sub(
                    r'\s*<field\s+name="numbercall"[^>]*>.*?</field>',
                    '',
                    content,
                    flags=re.DOTALL
                )
                content = re.sub(r'\s*<field\s+name="numbercall"[^/]*?/>', '', content)

                if content != original:
                    with open(xml_file, 'w', encoding='utf-8') as f:
                        f.write(content)
                    count += 1

            except Exception as e:
                print(f"  Error processing {xml_file.name}: {e}")

        self.fixes_applied.append(f"Fixed numbercall in {count} files")
        print(f"  [OK] Fixed {count} files")

    def fix_kanban_templates(self):
        """Fix kanban template names"""
        print("\n[5/6] Fixing kanban templates...")
        count = 0

        for xml_file in self.project_path.glob("**/*.xml"):
            try:
                with open(xml_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                original = content

                # Fix kanban-box to card
                content = content.replace('t-name="kanban-box"', 't-name="card"')

                if content != original:
                    with open(xml_file, 'w', encoding='utf-8') as f:
                        f.write(content)
                    count += 1

            except Exception as e:
                print(f"  Error processing {xml_file.name}: {e}")

        self.fixes_applied.append(f"Fixed kanban templates in {count} files")
        print(f"  [OK] Fixed {count} files")

    def fix_rpc_service(self):
        """Add _jsonRpc helper to files using RPC service"""
        print("\n[6/6] Fixing RPC service usage...")
        count = 0

        json_rpc_helper = '''
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

        for js_file in self.project_path.glob("**/*.js"):
            if 'node_modules' in str(js_file) or '.min.js' in str(js_file):
                continue

            try:
                with open(js_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                original = content

                # Remove RPC service
                content = re.sub(r'this\.rpc\s*=\s*useService\(["\']rpc["\']\);?\s*\n?', '', content)

                # Replace this.rpc calls
                if 'this.rpc(' in content:
                    content = content.replace('this.rpc(', 'this._jsonRpc(')

                    # Add helper if not present
                    if '_jsonRpc(endpoint, params' not in content:
                        # Find setup() and add after
                        setup_pattern = r'(setup\(\)\s*\{[^}]*\})'

                        def add_helper(match):
                            return match.group(0) + json_rpc_helper

                        content = re.sub(setup_pattern, add_helper, content, count=1)

                if content != original:
                    with open(js_file, 'w', encoding='utf-8') as f:
                        f.write(content)
                    count += 1

            except Exception as e:
                print(f"  Error processing {js_file.name}: {e}")

        self.fixes_applied.append(f"Fixed RPC service in {count} files")
        print(f"  [OK] Fixed {count} files")

    def generate_summary(self):
        """Generate fix summary"""
        print("\n" + "=" * 60)
        print("QUICK FIX SUMMARY")
        print("=" * 60)

        if self.fixes_applied:
            print("\nFixes applied:")
            for fix in self.fixes_applied:
                print(f"  [OK] {fix}")
        else:
            print("\nNo fixes were needed.")

        print("\n[SUCCESS] All quick fixes completed!")
        print("\nNext steps:")
        print("1. Test module installation")
        print("2. Run full upgrade script if needed: python upgrade_to_odoo19.py")
        print("3. Check for any remaining issues with: python odoo19_precheck.py")

    def run(self):
        """Run all quick fixes"""
        print("\n" + "=" * 60)
        print("ODOO 19 QUICK FIX UTILITY")
        print("=" * 60)
        print(f"Project: {self.project_path}")
        print("\nApplying fixes...")

        self.fix_tree_views()
        self.fix_search_groups()
        self.fix_js_class()
        self.fix_cron_numbercall()
        self.fix_kanban_templates()
        self.fix_rpc_service()

        self.generate_summary()


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python quick_fix_odoo19.py <project_path>")
        print("\nThis script applies quick fixes for common Odoo 19 issues:")
        print("  - Tree to List view conversion")
        print("  - Search view group removal")
        print("  - js_class attribute removal")
        print("  - Cron numbercall field removal")
        print("  - Kanban template fixes")
        print("  - RPC service migration")
        sys.exit(1)

    project_path = sys.argv[1]

    if not os.path.exists(project_path):
        print(f"Error: Path '{project_path}' does not exist")
        sys.exit(1)

    fixer = QuickFixer(project_path)
    fixer.run()


if __name__ == "__main__":
    main()