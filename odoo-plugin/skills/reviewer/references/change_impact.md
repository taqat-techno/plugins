# Reviewing a change: two passes, and the code the diff never shows

## Pin what you review

Review a checkout of the exact revision, with its base revision pinned. Take the diff
from that checkout, never from a pasted or saved copy: branches move and PRs get
force-pushed. Every file you read around the diff, framework included, comes from that
same revision. For each touched module, read `__manifest__.py` (purpose, `depends`), the
commit messages and the PR description.

## Pass 1: rules

1. Map every changed file to the sections that apply to it:
   - Python gets naming and imports;
   - `static/` gets the web rules;
   - `tests/` gets testing;
   - a fix to a deployed version gets "Changing a module that is already deployed" in
     `coding_guidelines.md`.

   A file left with no section is a mapping mistake. It is never a file without rules.
2. Read every mapped section **before** writing the first finding.
3. Judge the diff against them. On 20.0+ with the official skills installed, their
   sections are the floor (`official_odoo_skills.md`).

## Pass 2: merits

Passing the rules is the minimum bar. Next, attack each hunk: find the input or state
under which it misbehaves:
- edge values and rounding;
- timezones;
- an empty recordset and a multi-record call;
- concurrency;
- the second run of the same code (idempotence).

Also check that:
- the code does what the commit message says it does;
- the new tests would **fail without the change**;
- the change costs something tolerable at the data volume it will see.

This pass finds most blocking defects. Give it the same legwork as pass 1.

## The code the diff never shows

A change reaches further than its diff: other modules, in this repository or outside it,
override and reference what it touches. For every
changed method, field, template, context key or export, find its consumers across every
available addons path:

| Changed | Find | Question |
|---|---|---|
| a method | `grep -rn "def <name>("` | Do the overrides still call `super()` with valid arguments? Does the new behaviour hold with their additions? |
| a renamed or removed name | grep for it in Python, XML (views, domains, xpaths) and JavaScript (`patch()`, imports) | A stale reference fails only at runtime, or only once that module is installed |
| a template, data dictionary or context key | every producer, including the JavaScript twin of a Python one | A new required key must be supplied by every producer, or the untouched callers break at render |
| a public signature in a deployed version | its callers and overrides | Treat any change as a defect on its own |

## Report

For every finding, give:
- where it is (`path:line`);
- what is wrong;
- an input or state that actually triggers it;
- the smallest correct change;
- its source: a rule section from pass 1, or *judgement* from pass 2.

If the finding depends on code outside the diff, state the revision you read that code
at. Close the review by listing which rule sections you opened.
