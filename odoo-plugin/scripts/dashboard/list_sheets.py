#!/usr/bin/env python3
"""Build, re-size and check the data sheets of a list-based spreadsheet dashboard.

A list-based board keeps each Odoo list on its own sheet: row 1 holds ODOO.LIST.HEADER, the
rows under it hold ODOO.LIST(id, n, field). ODOO.LIST only loads the rows written in the
sheet, so a sheet sized to today's data silently drops tomorrow's rows. This script writes
the sheets with headroom and reports what a workbook can currently hold.

    list_sheets.py build  SPEC.json [--out FILE] [--no-headroom]
    list_sheets.py resize WORKBOOK.json --rows SHEET=N [--rows SHEET=N ...] [--out FILE] [--no-headroom]
    list_sheets.py check  WORKBOOK.json [--json]

SPEC.json is a list of {"name", "model", "columns", "rows"} with optional "id", "domain",
"context" and "order_by" ([{"name", "asc"}]). `rows` and `--rows` are the row counts of the
data today; headroom (the larger of twice the rows and rows + 500) is added on top.

It reads and writes JSON files only: no database, no network, no Odoo import. Saving the
workbook to a record is a separate, deliberate step (references/list-workbooks.md, section 7).
"""
from __future__ import annotations

import argparse
import json
import re
import sys

LIST_CALL = re.compile(r"ODOO\.LIST\(\s*\"?(\w+)\"?\s*,\s*(\d+)\s*,", re.IGNORECASE)
LIST_ROW = re.compile(r"(ODOO\.LIST\(\s*\"?\w+\"?\s*,\s*)(\d+)(\s*,)", re.IGNORECASE)
HEADER_CALL = re.compile(r"ODOO\.LIST\.HEADER\(\s*\"?(\w+)\"?\s*,", re.IGNORECASE)
CELL_REF = re.compile(r"^([A-Z]+)(\d+)$")


def column_letter(index):
    """0 -> A, 25 -> Z, 26 -> AA."""
    if index < 0:
        raise ValueError("column index must be 0 or more")
    letters = ""
    index += 1
    while index:
        index, rest = divmod(index - 1, 26)
        letters = chr(65 + rest) + letters
    return letters


def headroom(rows):
    """Rows to write for a view that holds `rows` today. Never less than 1."""
    rows = max(int(rows), 0)
    return max(rows * 2, rows + 500, 1)


def _sheet_id(name):
    return "list-" + re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def build(spec, with_headroom=True):
    """Return {"lists", "listNextId", "sheets", "ranges"} for the lists in `spec`."""
    lists, sheets, ranges, used = {}, [], {}, set()
    next_id = 1
    for entry in spec:
        for key in ("name", "model", "columns"):
            if not entry.get(key):
                raise ValueError("list spec needs %r: %r" % (key, entry))
        list_id = str(entry.get("id") or next_id)
        if list_id in used:
            raise ValueError("duplicate list id %s" % list_id)
        used.add(list_id)
        if list_id.isdigit():
            next_id = max(next_id, int(list_id) + 1)
        name, columns = entry["name"], list(entry["columns"])
        order = list(entry.get("order_by") or [])
        if not any(o.get("name") == "id" for o in order):
            order.append({"name": "id", "asc": True})  # tie-breaker: stable row order
        lists[list_id] = {
            "id": list_id, "name": name, "model": entry["model"], "columns": columns,
            "domain": entry.get("domain") or [], "context": entry.get("context") or {},
            "orderBy": order,
            "fieldMatching": {},  # explicit: stops Odoo copying another list's filter mapping
        }
        rows = headroom(entry.get("rows", 0)) if with_headroom else max(int(entry.get("rows", 0)), 1)
        cells, ranges[name] = {}, {}
        for c, field in enumerate(columns):
            col = column_letter(c)
            cells["%s1" % col] = {"content": '=ODOO.LIST.HEADER(%s,"%s")' % (list_id, field)}
            for n in range(1, rows + 1):
                cells["%s%d" % (col, n + 1)] = {"content": '=ODOO.LIST(%s,%d,"%s")' % (list_id, n, field)}
            ranges[name][field] = "%s!%s2:%s" % (name, col, col)
        sheets.append({
            "id": _sheet_id(name), "name": name, "colNumber": len(columns) + 1, "rowNumber": rows + 2,
            "cells": cells, "cols": {}, "rows": {}, "merges": [], "conditionalFormats": [],
            "figures": [], "areGridLinesVisible": True, "isVisible": True,
        })
    return {"lists": lists, "listNextId": next_id, "sheets": sheets, "ranges": ranges}


def _list_rows(sheet):
    """{list_id: highest row index n written with ODOO.LIST} for one sheet."""
    found = {}
    for cell in (sheet.get("cells") or {}).values():
        for list_id, n in LIST_CALL.findall((cell or {}).get("content") or ""):
            found[list_id] = max(found.get(list_id, 0), int(n))
    return found


def check(workbook):
    """Report what each list can hold and what is missing. Pure: reads the dict only."""
    lists = workbook.get("lists") or {}
    report = {"lists": [], "problems": []}
    written, referenced = {}, set()
    for sheet in workbook.get("sheets") or []:
        for list_id, n in _list_rows(sheet).items():
            if n > written.get(list_id, (0, ""))[0]:
                written[list_id] = (n, sheet.get("name", ""))
        for cell in (sheet.get("cells") or {}).values():
            content = (cell or {}).get("content") or ""
            referenced.update(m for m, _ in LIST_CALL.findall(content))
            referenced.update(HEADER_CALL.findall(content))
    mapped = set()
    for flt in workbook.get("globalFilters") or []:
        mapped.update((flt.get("listFields") or {}).keys())
    for list_id, definition in lists.items():
        rows, sheet = written.get(list_id, (0, ""))
        report["lists"].append({"id": list_id, "name": definition.get("name", ""),
                                "model": definition.get("model", ""), "sheet": sheet, "rows_written": rows})
        if "fieldMatching" not in definition and list_id not in mapped:
            report["problems"].append(
                "list %s (%s): no fieldMatching and no listFields entry; Odoo copies another list's "
                "filter mapping onto it. Write \"fieldMatching\": {}" % (list_id, definition.get("name", "")))
        if not rows:
            report["problems"].append("list %s (%s): no ODOO.LIST row in any sheet" % (list_id, definition.get("name", "")))
        order = definition.get("orderBy") or []
        if not any(o.get("name") == "id" for o in order):
            report["problems"].append("list %s (%s): orderBy has no id tie-breaker" % (list_id, definition.get("name", "")))
    for list_id in sorted(referenced - set(lists)):
        report["problems"].append("a formula reads list %s, which the workbook does not define" % list_id)
    return report


def resize(workbook, rows_by_sheet, with_headroom=True):
    """Rewrite the ODOO.LIST rows of the named sheets for new row counts. Returns {sheet: rows written}."""
    done = {}
    sheets = {s.get("name"): s for s in workbook.get("sheets") or []}
    for name, rows in rows_by_sheet.items():
        sheet = sheets.get(name)
        if sheet is None:
            raise ValueError("no sheet named %r" % name)
        template, kept = {}, {}
        for ref, cell in (sheet.get("cells") or {}).items():
            match = CELL_REF.match(ref)
            content = (cell or {}).get("content") or ""
            if match and LIST_CALL.search(content):
                if match.group(2) == "2":
                    template[match.group(1)] = cell
            else:
                kept[ref] = cell
        if not template:
            raise ValueError("sheet %r has no ODOO.LIST formula in row 2" % name)
        target = headroom(rows) if with_headroom else max(int(rows), 1)
        for col, cell in template.items():
            for n in range(1, target + 1):
                new = dict(cell)
                new["content"] = LIST_ROW.sub(lambda m, n=n: "%s%d%s" % (m.group(1), n, m.group(3)), cell["content"])
                kept["%s%d" % (col, n + 1)] = new
        sheet["cells"] = kept
        last = max((int(m.group(2)) for m in map(CELL_REF.match, kept) if m), default=0)
        sheet["rowNumber"] = max(target + 2, last + 1)
        done[name] = target
    return done


def _load(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def _dump(data, path):
    text = json.dumps(data, ensure_ascii=False)
    if path:
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
    else:
        sys.stdout.buffer.write(text.encode("utf-8") + b"\n")


def main(argv=None):
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    p_build = sub.add_parser("build", help="write data sheets and list definitions from a spec")
    p_build.add_argument("spec")
    p_build.add_argument("--out")
    p_build.add_argument("--no-headroom", action="store_true")
    p_resize = sub.add_parser("resize", help="re-size data sheets of an exported workbook")
    p_resize.add_argument("workbook")
    p_resize.add_argument("--rows", action="append", default=[], metavar="SHEET=N", required=True)
    p_resize.add_argument("--out")
    p_resize.add_argument("--no-headroom", action="store_true")
    p_check = sub.add_parser("check", help="report rows written per list and missing settings")
    p_check.add_argument("workbook")
    p_check.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    try:
        if args.command == "build":
            _dump(build(_load(args.spec), not args.no_headroom), args.out)
        elif args.command == "resize":
            rows = {}
            for item in args.rows:
                name, sep, count = item.rpartition("=")
                if not sep or not count.isdigit():
                    parser.error("--rows takes SHEET=N, got %r" % item)
                rows[name] = int(count)
            workbook = _load(args.workbook)
            done = resize(workbook, rows, not args.no_headroom)
            _dump(workbook, args.out or args.workbook)
            for name, written in done.items():
                print("%s: %d rows written" % (name, written), file=sys.stderr)
        else:
            report = check(_load(args.workbook))
            if args.json:
                _dump(report, None)
            else:
                for item in report["lists"]:
                    print("list %(id)s  %(name)s  %(model)s  sheet=%(sheet)s  rows written=%(rows_written)d" % item)
                for problem in report["problems"]:
                    print("PROBLEM: " + problem)
                if not report["problems"]:
                    print("no problems found")
            return 1 if report["problems"] else 0
    except (OSError, ValueError) as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
