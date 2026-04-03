"""
Data consistency tests for the Odoo Frontend plugin.

Validates internal consistency of data files — typography hierarchy,
template structure, and cross-file references.
"""

import json
import pytest
from pathlib import Path


PLUGIN_ROOT = Path(__file__).parent.parent
DATA_DIR = PLUGIN_ROOT / "data"


# ─── Typography Consistency ──────────────────────────────────────


class TestTypographyConsistency:
    """Verify typography_defaults.json follows critical rules."""

    @pytest.fixture(scope="class")
    def typography(self):
        with open(DATA_DIR / "typography_defaults.json") as f:
            return json.load(f)

    def test_base_font_size_is_16(self, typography):
        assert typography["base_font_size"] == 16, "Base font size must be 16px"

    def test_h6_multiplier_is_1(self, typography):
        """H6 is ALWAYS 16px (1rem) — fixed base reference. This is a critical rule."""
        headings = typography.get("heading_hierarchy", {})
        h6 = headings.get("h6", {})
        assert h6.get("multiplier") == 1.0, "H6 multiplier must be exactly 1.0 (16px fixed)"

    def test_h1_multiplier_is_4(self, typography):
        headings = typography.get("heading_hierarchy", {})
        h1 = headings.get("h1", {})
        assert h1.get("multiplier") == 4.0, "H1 multiplier should be 4.0"

    def test_has_6_heading_levels(self, typography):
        headings = typography.get("heading_hierarchy", {})
        for level in ["h1", "h2", "h3", "h4", "h5", "h6"]:
            assert level in headings, f"Missing heading level: {level}"

    def test_multipliers_decrease(self, typography):
        """Heading multipliers should decrease from H1 to H6."""
        headings = typography.get("heading_hierarchy", {})
        prev = 99.0
        for level in ["h1", "h2", "h3", "h4", "h5", "h6"]:
            mult = headings.get(level, {}).get("multiplier", 0)
            assert mult <= prev, f"{level} multiplier ({mult}) should be <= previous ({prev})"
            prev = mult

    def test_has_popular_fonts(self, typography):
        fonts = typography.get("popular_fonts", {})
        assert "sans_serif" in fonts, "Missing sans_serif fonts"
        assert len(fonts["sans_serif"]) >= 5, "Should have at least 5 sans-serif fonts"


# ─── Template Consistency ────────────────────────────────────────


class TestTemplateConsistency:
    """Verify theme_templates.json has correct structure."""

    @pytest.fixture(scope="class")
    def templates(self):
        with open(DATA_DIR / "theme_templates.json") as f:
            return json.load(f)

    def test_has_header_templates(self, templates):
        headers = templates.get("header_templates", {})
        assert len(headers) >= 3, f"Should have at least 3 header templates, got {len(headers)}"

    def test_has_footer_templates(self, templates):
        footers = templates.get("footer_templates", {})
        assert len(footers) >= 3, f"Should have at least 3 footer templates, got {len(footers)}"

    def test_has_asset_bundles(self, templates):
        bundles = templates.get("asset_bundles", {})
        assert len(bundles) >= 2, "Should have at least 2 asset bundles"

    def test_primary_variables_bundle_exists(self, templates):
        """primary_variables bundle must target web._assets_primary_variables (loaded first by Odoo)."""
        bundles = templates.get("asset_bundles", {})
        pv = bundles.get("primary_variables", {})
        assert "bundle" in pv, "primary_variables must have a bundle key"
        assert "primary_variables" in pv["bundle"], "primary_variables bundle must target _assets_primary_variables"

    def test_frontend_helpers_is_prepend(self, templates):
        """frontend_helpers MUST use prepend to load before Odoo core helpers."""
        bundles = templates.get("asset_bundles", {})
        fh = bundles.get("frontend_helpers", {})
        assert fh.get("prepend") is True, "frontend_helpers bundle must have prepend: true"

    def test_has_required_files(self, templates):
        required = templates.get("required_files", [])
        assert "__manifest__.py" in required, "required_files must include __manifest__.py"
        assert len(required) >= 3, "Should have at least 3 required files"

    def test_has_page_files(self, templates):
        pages = templates.get("page_files", {})
        assert "pattern" in pages, "page_files should define a pattern"
        common = pages.get("common_pages", [])
        assert len(common) >= 4, "Should have at least 4 common page types"


# ─── Version Mapping Consistency ─────────────────────────────────


class TestVersionMappingConsistency:
    """Verify version_mapping.json internal consistency."""

    @pytest.fixture(scope="class")
    def version_map(self):
        with open(DATA_DIR / "version_mapping.json") as f:
            return json.load(f)

    def test_all_versions_have_js_info(self, version_map):
        for ver, config in version_map.get("odoo_versions", {}).items():
            assert "javascript" in config, f"Version {ver} missing javascript field"

    def test_bootstrap_5_versions_have_data_bs_attributes(self, version_map):
        """Bootstrap 5 uses data-bs-* attributes instead of data-*."""
        for ver, config in version_map.get("odoo_versions", {}).items():
            bs = config.get("bootstrap_version", "")
            if bs.startswith("5."):
                attrs = config.get("data_attributes", {})
                if attrs:
                    for key, val in attrs.items():
                        assert "data-bs-" in val, (
                            f"Odoo {ver} (BS5) should use data-bs-* attributes, got {val}"
                        )

    def test_all_versions_have_snippet_registration(self, version_map):
        """Each version should specify snippet registration type."""
        for ver, config in version_map.get("odoo_versions", {}).items():
            assert "snippet_registration" in config, f"Version {ver} missing snippet_registration"
            assert config["snippet_registration"] in ("simple_xpath", "groups_required"), (
                f"Version {ver} has invalid snippet_registration: {config['snippet_registration']}"
            )

    def test_all_versions_have_js_pattern(self, version_map):
        """Each version should specify JS pattern."""
        for ver, config in version_map.get("odoo_versions", {}).items():
            assert "js_pattern" in config, f"Version {ver} missing js_pattern"

    def test_odoo_18_19_require_groups(self, version_map):
        """Odoo 18-19 must have groups_required snippet registration."""
        for ver in ["18", "19"]:
            config = version_map.get("odoo_versions", {}).get(ver, {})
            assert config.get("snippet_registration") == "groups_required", (
                f"Odoo {ver} should require groups for snippets"
            )
