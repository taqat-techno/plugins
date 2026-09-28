"""Regression: scripts/security/access_checker.py on Odoo 20 ir.access.csv and legacy
ir.model.access.csv. On 20 a group-less row is a RESTRICTION, the inverse of the legacy
meaning, so the two paths must never be mixed up.

Run: python tests/security/test_access_checker_v20.py   (or pytest)
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

CHK = str(Path(__file__).resolve().parents[2] / "scripts" / "security" / "access_checker.py")

MODEL_PY = '''from odoo import fields, models
class Book(models.Model):
    _name = "library.book"
    _description = "Book"
    name = fields.Char()
    company_id = fields.Many2one("res.company")
class Loan(models.Model):
    _name = "library.loan"
    _description = "Loan"
'''


def module(csv_name, csv_text):
    d = Path(tempfile.mkdtemp()) / "library"
    (d / "models").mkdir(parents=True)
    (d / "security").mkdir()
    (d / "__manifest__.py").write_text("{'name': 'library', 'version': '20.0.1.0.0'}", encoding="utf-8")
    (d / "models" / "__init__.py").write_text("from . import book\n", encoding="utf-8")
    (d / "models" / "book.py").write_text(MODEL_PY, encoding="utf-8")
    (d / "security" / csv_name).write_text(csv_text, encoding="utf-8")
    return d


def run(mod):
    p = subprocess.run([sys.executable, CHK, str(mod), "--json"], capture_output=True, text=True, timeout=60)
    try:
        data = json.loads(p.stdout)
    except ValueError:
        print("RAW:", p.stdout[:400], p.stderr[:400])
        raise
    return data if isinstance(data, list) else data.get("issues", data)


ok = True


def check(name, cond, info=""):
    global ok
    ok &= bool(cond)
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else " :: " + str(info)[:500]))
    assert cond, "%s: %s" % (name, str(info)[:300])



def test_access_checker_v20_and_legacy():
    v20 = module("ir.access.csv", "\n".join([
        "id,name,model_id,group_id/id,operation,domain",
        "access_book_user,book user,library.book,base.group_user,cru,",
        "access_book_portal,book portal,library.book,base.group_portal,rw,",   # 'w' invalid + wide? uses r,w
        "restrict_book_mine,own books,library.book,,r,[('create_uid','=',user.id)]",
    ]) + "\n")
    issues = run(v20)
    types = [i["type"] for i in issues]
    check("20: loan has no permission row -> missing_access_rule",
          any(i["type"] == "missing_access_rule" and "library.loan" in i["message"] for i in issues), issues)
    check("20: book is covered (no missing rule for it)",
          not any(i["type"] == "missing_access_rule" and "library.book" in i["message"] for i in issues), issues)
    check("20: empty group is NOT reported as all-users access", "empty_group_access" not in types, types)
    check("20: partial restriction flagged (r only, cu granted)", "partial_restriction" in types, types)
    check("20: invalid operation letter flagged", any("not a subset of 'crud'" in i["message"] for i in issues), issues)
    check("20: portal grant flagged", "open_group_access" in types, types)
    check("20: missing company restriction flagged", "missing_record_rule" in types, types)

    v17 = module("ir.model.access.csv", "\n".join([
        "id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink",
        "access_book_user,book user,model_library_book,base.group_user,1,1,1,0",
        "access_book_all,book all,model_library_book,,1,0,0,0",
    ]) + "\n")
    issues17 = run(v17)
    t17 = [i["type"] for i in issues17]
    check("17: legacy path still reports missing loan rule",
          any(i["type"] == "missing_access_rule" and "library.loan" in i["message"] for i in issues17), issues17)
    check("17: legacy empty-group rule still flagged", "empty_group_access" in t17, t17)


if __name__ == "__main__":
    test_access_checker_v20_and_legacy()
    print("all passed")
