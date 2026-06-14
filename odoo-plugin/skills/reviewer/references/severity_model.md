# Severity model & tech-debt estimation

A consistent rubric for grading findings during an Odoo 17 review, and a
rough effort table for converting counts into hours.

## Severity levels

| Severity | Definition | Examples |
|---|---|---|
| **BLOCKER** | Install / runtime fails, security hole, or data corruption risk. Must be fixed before any deploy. | Missing `ir.model.access` row; SQL injection; `sudo()` masking ACL; missing `depends` causing install error; `cr.commit()` in a model method; compute reassigns `self.field` without `for record in self:`. |
| **MAJOR** | Works today but introduces brittleness, performance cliff, or convention drift that compounds. Fix in the current sprint. | ORM bypass (`cr.execute` where ORM works); missing `external_dependencies`; misnamed compute / onchange (Odoo binding magic misses it); incomplete `@api.depends`; unsafe public method; `t-raw` on user input; missing `license`; missing `index=True` on a heavily filtered column. |
| **MINOR** | Style / hygiene drift. Confuses contributors but doesn't break anything. Fix opportunistically. | Bare `1.0` `version`; deprecated `main.py`; file naming drift; comments and translation strings violating idioms; `_()` wrapping a field value. |
| **STYLE** | Pure aesthetics within Odoo's relaxed PEP8 (E501/E301/E302 ignored). | Class attribute order; SCSS variable naming; very long line where Odoo policy says it's OK. |

## How to bucket a finding

Ask the four questions in order, stop at the first "yes":

1. **Does this break install, runtime, or security?** → BLOCKER.
2. **Does this hide a future bug, performance cliff, or compounding cost?** →
   MAJOR.
3. **Does this confuse a future maintainer or auto-tooling?** → MINOR.
4. Otherwise → STYLE.

## Effort estimate per finding

Rough heuristics for converting findings into hours of remediation work.
Calibrate against your team's actual numbers when you can.

| Severity | Avg fix hours | Includes |
|---|---|---|
| BLOCKER | 4–8h | Reproduce, fix, write/extend a test, code-review round |
| MAJOR | 2–4h | Fix + targeted test |
| MINOR | 0.5–1h | Fix in place, no new test |
| STYLE | 0.1–0.3h | Quick reformat |

These assume an experienced Odoo developer working in a known module. New
module / unfamiliar code = multiply by 1.5–2×.

## Per-module debt score

For each module compute:

```
debt_hours = 6  * blocker_count
           + 3  * major_count
           + 0.75 * minor_count
           + 0.2  * style_count
```

(Midpoints of the table above.)

This gives a single number per module that's directly comparable to a
sprint allocation.

## Per-module top-risk line

In addition to the count, write one sentence: *"Top risk is …"*. This forces
the reviewer to identify the single most damaging issue, which usually
drives prioritisation more than the total count.

## Repository-level rollup

Once per-module numbers exist:

| Bucket | Definition |
|---|---|
| **Healthy** | 0 blockers, ≤ 2 majors, < 5h estimated debt |
| **Manageable** | 0 blockers, ≤ 6 majors, < 20h estimated debt |
| **At risk** | 1–2 blockers, or > 6 majors, or > 20h estimated debt |
| **Critical** | ≥ 3 blockers, or > 50h estimated debt |

A module is only **shippable** if it's *Healthy* or *Manageable* with a
named owner and a deadline for the remaining majors.

## Reporting format

Use this Markdown skeleton when delivering a review:

```markdown
## Review of <module>

**Severity counts:** BLOCKER=2  MAJOR=5  MINOR=7  STYLE=3
**Estimated debt:** ~24h
**Bucket:** At risk
**Top risk:** <one-sentence summary>

### Findings

| # | Severity | File:line | Rule | Note |
|---|---|---|---|---|
| 1 | BLOCKER | models/foo.py:42 | Security → unsafe public method | `action_done` writes state without re-checking caller groups |
| 2 | MAJOR | models/foo.py:88 | ORM → N+1 search in loop | `search([...])` inside `for partner in partners` — pull above |
| ... | | | | |
```

Cite the **rule name** every time so the user can verify against the docs
and against the rule files inside this skill.

## Calibration sanity checks

- If a review of a small module (≤ 5 models) produces > 30 findings,
  re-bucket — STYLE noise is drowning the real signal.
- If every finding is MAJOR, the bar is calibrated wrong. A 10-finding
  review should have ~1 BLOCKER, ~3 MAJOR, ~5 MINOR, ~1 STYLE on average.
- If estimated debt > 80h for a single module, recommend rewrite over
  remediation.
