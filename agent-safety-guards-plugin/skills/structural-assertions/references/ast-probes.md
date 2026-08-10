# AST probes and sweeps

Companion catalog for the `structural-assertions` skill. The skill owns the decisions; this
file owns the mechanism and the runnable code.

---

## 1. Why `ast.walk` order is not source order

`ast.walk` is implemented as a **breadth-first** traversal over a queue:

```python
def walk(node):
    todo = deque([node])
    while todo:
        node = todo.popleft()
        todo.extend(ast.iter_child_nodes(node))
        yield node
```

Children are appended to the right and consumed from the left, so every node at depth *d* is
yielded before every node at depth *d+1*. Consequences:

- A call on line 90 at module level is yielded **before** a call on line 12 nested inside an
  `if` inside a `with` inside a function.
- A decorator (`ast.Call` in `node.decorator_list`) is a child of the `FunctionDef`, so it
  sorts by depth, not by its position above the `def`.
- Calls inside `try` / `except` / `finally` sit one level deeper than the surrounding block,
  so a `finally` cleanup can be yielded after code that follows the whole `try`.

Therefore `list(...).index(x) < list(...).index(y)` is a statement about **tree depth and
sibling order**, never about the file.

### The correct ordering probe

```python
import ast
from pathlib import Path


def call_order(path, names=None):
    """Return [(lineno, col_offset, name), ...] in true source order."""
    tree = ast.parse(Path(path).read_text(encoding="utf-8"))
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name):
            name = func.id
        elif isinstance(func, ast.Attribute):
            name = func.attr
        else:
            continue
        if names is None or name in names:
            out.append((node.lineno, node.col_offset, name))
    return sorted(out)


order = [n for _, _, n in call_order("src/app/lifecycle.py", {"close_writer", "flush_queue"})]
assert order.index("flush_queue") < order.index("close_writer"), order
```

Notes:

- `col_offset` is the tie-break for two calls on one line (`f(g())` — `f` and `g` share a
  `lineno`; `g` has the larger `col_offset`, which is also the evaluation order for the
  argument, so read the tie-break carefully before asserting on it).
- If ordering only matters **within one function**, scope the walk to that node
  (`next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "shutdown")`)
  rather than the module — a same-named helper elsewhere in the file will otherwise pollute
  the list.
- If a name can appear more than once, compare `min(...)`/`max(...)` of its positions
  deliberately instead of `.index()`, which silently picks the first.

Use `ast.NodeVisitor` when you want depth-first document order for free: `generic_visit`
recurses in field order, which matches source order for statement bodies.

---

## 2. The side-by-side wiring probe

The control of choice for a binary "is X wired up?" claim. It reads two file paths — no
import, no `sys.path`, no fixtures, no test collection. Old prints `False`, new prints
`True`, and there is nothing in between to misconfigure.

```python
"""probe_wiring.py — usage: python probe_wiring.py OLD_FILE NEW_FILE"""
import ast
import sys
from pathlib import Path

TARGET = "register_storage_backend"   # the call that proves the wiring


def is_wired(path):
    tree = ast.parse(Path(path).read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", None)
        if name == TARGET:
            return True, node.lineno
    return False, None


for label, path in zip(("OLD", "NEW"), sys.argv[1:3]):
    wired, line = is_wired(path)
    print(f"{label:4} {path}: wired={wired} line={line}")
```

Expected output shape — anything else means the probe, not the code, is wrong:

```
OLD  .../v1/bootstrap.py: wired=False line=None
NEW  src/app/bootstrap.py: wired=True line=64
```

Get the old file without touching the working tree:

```bash
git show "v1.2.3:src/app/bootstrap.py" > /tmp/bootstrap.old.py
python probe_wiring.py /tmp/bootstrap.old.py src/app/bootstrap.py
```

Note that the probe prints the paths it read. That is deliberate: the only thing it can get
wrong is which file you pointed it at, and printing the path makes that failure visible in
the same output as the result.

### If you must use the test harness for a version comparison

Do not do it on the strength of this file. Both traps that make a harness lie about a
cross-version comparison — an editable install pinning the working tree's `src/` onto
`sys.path`, and a baseline-missing symbol raising one `ImportError` at collection so no
discriminating test runs — are owned by the **`test-result-evidence`** skill, together with
the artifact-identity check that has to precede the run. Read it there and run its check
first; this file will not repeat it.

---

## 3. Sweep recipes

A sweep answers "how many instances of this shape exist", which is the question you have the
moment you find one. Run it before declaring a fix complete, and again afterwards.

### Skeleton

```python
import ast
from pathlib import Path


def sweep(root, predicate, globs=("**/*.py",), skip=(".venv", "node_modules", "build", ".git")):
    hits = []
    for pattern in globs:
        for path in Path(root).glob(pattern):
            if any(part in skip for part in path.parts):
                continue
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            except (SyntaxError, UnicodeDecodeError) as exc:
                hits.append((path, 0, f"UNPARSED: {exc.__class__.__name__}"))
                continue
            for node in ast.walk(tree):
                note = predicate(node)
                if note:
                    hits.append((path, getattr(node, "lineno", 0), note))
    return hits
```

Record unparsed files as hits, never as silence. A sweep that returns zero because it
swallowed a `SyntaxError` reads exactly like a clean repository.

### Recipe A — broad handler returning a plausible literal

The shape that turns "my code is wrong" into "your data is gone": the caller cannot
distinguish the failure value from a legitimate result.

```python
PLAUSIBLE = (0, 0.0, "", False, None)


def broad_handler_returning_literal(node):
    if not isinstance(node, ast.ExceptHandler):
        return None
    bare = node.type is None
    broad = isinstance(node.type, ast.Name) and node.type.id in {"Exception", "BaseException"}
    if not (bare or broad):
        return None
    for child in ast.walk(node):
        if isinstance(child, ast.Return) and isinstance(child.value, ast.Constant):
            if child.value.value in PLAUSIBLE:
                return f"except -> return {child.value.value!r}"
    return None
```

Expect a large, mostly-legitimate population (best-effort telemetry, optional caches). The
value is knowing the population; the one that matters is usually the handler *below* the
layer you were fixing, which absorbs the exception so your new sentinel can never fire.

### Recipe B — a construct that must live behind one seam

Platform dispatch, clock reads, randomness, direct env access, raw SQL — anything the
project routes through a single module. Assert the negative universal everywhere else.

```python
SEAM = "src/app/platform_seam.py"


def platform_branch_outside_seam(node):
    if isinstance(node, ast.Attribute) and node.attr == "platform":
        if isinstance(node.value, ast.Name) and node.value.id == "sys":
            return "sys.platform"
    if isinstance(node, ast.Call):
        func = node.func
        name = getattr(func, "attr", None) or getattr(func, "id", None)
        if name in {"system", "platform", "machine"}:
            return f"platform.{name}()"
    return None
```

Then filter the seam file out of the hits. Note that this predicate catches spelling variants
a substring search for `"sys.platform"` misses (`platform.system()`, `from sys import platform`
used bare), and — because comments are gone after parsing — it will never match your
explanation of the rule. The dynamic form is *not* covered by the clauses above and needs its
own: an `ast.Call` to `getattr` whose first argument is the `Name` `sys` and whose second is
the constant `"platform"`. Add it explicitly rather than assuming a node predicate reaches
every spelling for free.

### Recipe C — no path reaches the primitive directly

For a function with several exit branches, quantify over the whole module rather than
walking each branch.

```python
FORBIDDEN = {"_close_socket_raw", "os._exit"}


def direct_primitive_call(node):
    if not isinstance(node, ast.Call):
        return None
    func = node.func
    name = getattr(func, "attr", None) or getattr(func, "id", None)
    return f"direct call to {name}" if name in FORBIDDEN else None
```

Scope the sweep to every module except the single wrapper that is allowed to call it. A new
early-return branch added later is covered automatically — that is the point.

---

## 4. Non-Python stacks

The rule is "use the language's parser", not "use Python's `ast`".

| Stack | Structural check |
|---|---|
| TypeScript / JavaScript | TS compiler API (`ts.createSourceFile` + `forEachChild`), or an ESLint rule with an AST selector (`no-restricted-syntax` accepts esquery selectors) |
| Any language, one script | `tree-sitter` bindings — one query per rule, `.captures()` gives nodes with row/column |
| Go | `go/ast` + `go/parser`, or a `go vet` analyzer |
| Config / IaC (YAML, HCL) | Parse to a document tree and assert on paths; never regex a YAML file for a key |

In every case the same three traps apply: comments are not code, traversal order is not
source order, and one instance is not the population.
