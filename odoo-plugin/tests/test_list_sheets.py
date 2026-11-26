"""scripts/dashboard/list_sheets.py: data sheets of a list-based spreadsheet dashboard.

Offline: workbooks are plain dicts and temp files. The behaviour the script works around
(ODOO.LIST loads only the rows written; a list without fieldMatching inherits another
list's mapping) is in addons/spreadsheet/static/src/list/ of Odoo 17.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = PLUGIN_ROOT / "scripts" / "dashboard" / "list_sheets.py"
sys.path.insert(0, str(SCRIPT.parent))

import list_sheets  # noqa: E402

SPEC = [
    {"name": "DATA_SALES", "model": "x_report.sales_daily", "columns": ["x_date", "x_status", "x_count"], "rows": 3},
    {"name": "DATA_STOCK", "model": "x_report.stock", "columns": ["x_site", "x_count"], "rows": 0,
     "order_by": [{"name": "x_site", "asc": True}]},
]


def _workbook(spec=SPEC, **kw):
    built = list_sheets.build(spec, **kw)
    return {"sheets": [{"id": "d", "name": "Dashboard", "cells": {}}] + built["sheets"],
            "lists": built["lists"], "listNextId": built["listNextId"], "globalFilters": []}


def test_column_letter():
    assert [list_sheets.column_letter(i) for i in (0, 25, 26, 27, 51, 52, 701, 702)] == \
        ["A", "Z", "AA", "AB", "AZ", "BA", "ZZ", "AAA"]
    with pytest.raises(ValueError):
        list_sheets.column_letter(-1)


def test_headroom_never_below_one_and_grows():
    assert list_sheets.headroom(0) == 500
    assert list_sheets.headroom(3) == 503
    assert list_sheets.headroom(1000) == 2000
    assert list_sheets.headroom(-5) == 500


def test_build_writes_header_rows_and_headroom():
    built = list_sheets.build(SPEC)
    sales = built["sheets"][0]
    assert sales["cells"]["A1"]["content"] == '=ODOO.LIST.HEADER(1,"x_date")'
    assert sales["cells"]["C2"]["content"] == '=ODOO.LIST(1,1,"x_count")'
    assert sales["cells"]["C504"]["content"] == '=ODOO.LIST(1,503,"x_count")'
    assert "C505" not in sales["cells"]
    assert sales["rowNumber"] == 505 and sales["colNumber"] == 4
    assert built["ranges"]["DATA_SALES"]["x_count"] == "DATA_SALES!C2:C"
    assert built["listNextId"] == 3


def test_build_sets_empty_field_matching_and_id_tiebreak():
    lists = list_sheets.build(SPEC)["lists"]
    assert lists["1"]["fieldMatching"] == {} and lists["2"]["fieldMatching"] == {}
    assert lists["1"]["orderBy"] == [{"name": "id", "asc": True}]
    assert lists["2"]["orderBy"] == [{"name": "x_site", "asc": True}, {"name": "id", "asc": True}]


def test_build_empty_view_still_gets_one_row_without_headroom():
    built = list_sheets.build(SPEC, with_headroom=False)
    stock = built["sheets"][1]
    assert stock["cells"]["A2"]["content"] == '=ODOO.LIST(2,1,"x_site")'
    assert "A3" not in stock["cells"]


def test_build_rejects_duplicate_ids_and_missing_keys():
    with pytest.raises(ValueError):
        list_sheets.build([dict(SPEC[0], id=1), dict(SPEC[1], id=1)])
    with pytest.raises(ValueError):
        list_sheets.build([{"name": "DATA_X", "model": "m", "columns": []}])


def test_check_clean_workbook_has_no_problems():
    report = list_sheets.check(_workbook())
    assert report["problems"] == []
    assert {(item["name"], item["rows_written"]) for item in report["lists"]} == {("DATA_SALES", 503), ("DATA_STOCK", 500)}


def test_check_flags_missing_field_matching_unless_mapped_by_list_fields():
    workbook = _workbook()
    del workbook["lists"]["1"]["fieldMatching"]
    del workbook["lists"]["2"]["fieldMatching"]
    workbook["globalFilters"] = [{"id": "f", "listFields": {"2": {"field": "x_site", "type": "char"}}}]
    problems = list_sheets.check(workbook)["problems"]
    assert len(problems) == 1 and "list 1 (DATA_SALES)" in problems[0] and "fieldMatching" in problems[0]


def test_check_flags_unknown_list_unwritten_list_and_missing_tiebreak():
    workbook = _workbook()
    workbook["sheets"][0]["cells"]["A1"] = {"content": '=ODOO.LIST(9,1,"x")'}
    workbook["lists"]["3"] = {"id": "3", "name": "DATA_EMPTY", "model": "m", "columns": ["a"],
                              "fieldMatching": {}, "orderBy": []}
    problems = "\n".join(list_sheets.check(workbook)["problems"])
    assert "reads list 9" in problems
    assert "list 3 (DATA_EMPTY): no ODOO.LIST row" in problems
    assert "list 3 (DATA_EMPTY): orderBy has no id tie-breaker" in problems


def test_resize_grows_shrinks_and_keeps_other_cells():
    workbook = _workbook(with_headroom=False)
    sales = workbook["sheets"][1]
    sales["cells"]["F1"] = {"content": "note"}
    sales["cells"]["C2"]["format"] = 4
    assert list_sheets.resize(workbook, {"DATA_SALES": 10}) == {"DATA_SALES": 510}
    assert sales["cells"]["C511"] == {"content": '=ODOO.LIST(1,510,"x_count")', "format": 4}
    assert "C512" not in sales["cells"]
    assert sales["cells"]["A1"]["content"] == '=ODOO.LIST.HEADER(1,"x_date")'
    assert sales["cells"]["F1"] == {"content": "note"}
    assert sales["rowNumber"] == 512
    list_sheets.resize(workbook, {"DATA_SALES": 2}, with_headroom=False)
    assert "A4" not in sales["cells"] and sales["cells"]["A3"]["content"] == '=ODOO.LIST(1,2,"x_date")'
    assert list_sheets.check(workbook)["problems"] == []


def test_resize_unknown_sheet_or_sheet_without_lists_fails():
    workbook = _workbook()
    with pytest.raises(ValueError):
        list_sheets.resize(workbook, {"NOPE": 5})
    with pytest.raises(ValueError):
        list_sheets.resize(workbook, {"Dashboard": 5})


def _run(*args):
    return subprocess.run([sys.executable, str(SCRIPT), *map(str, args)], capture_output=True, text=True, encoding="utf-8")


def test_cli_build_resize_check_round_trip(tmp_path):
    spec, out = tmp_path / "spec.json", tmp_path / "built.json"
    spec.write_text(json.dumps(SPEC), encoding="utf-8")
    assert _run("build", spec, "--out", out).returncode == 0
    built = json.loads(out.read_text(encoding="utf-8"))
    workbook = tmp_path / "wb.json"
    workbook.write_text(json.dumps({"sheets": built["sheets"], "lists": built["lists"]}), encoding="utf-8")
    result = _run("check", workbook)
    assert result.returncode == 0 and "no problems found" in result.stdout
    result = _run("resize", workbook, "--rows", "DATA_STOCK=40")
    assert result.returncode == 0 and "DATA_STOCK: 540 rows written" in result.stderr
    report = json.loads(_run("check", workbook, "--json").stdout)
    assert {i["name"]: i["rows_written"] for i in report["lists"]}["DATA_STOCK"] == 540


def test_cli_check_exits_1_on_problems_and_2_on_bad_input(tmp_path):
    workbook = tmp_path / "wb.json"
    workbook.write_text(json.dumps({"sheets": [], "lists": {"1": {"name": "L", "model": "m"}}}), encoding="utf-8")
    result = _run("check", workbook)
    assert result.returncode == 1 and "PROBLEM:" in result.stdout
    assert _run("check", tmp_path / "missing.json").returncode == 2
    assert _run("resize", workbook, "--rows", "NOPE=3").returncode == 2
