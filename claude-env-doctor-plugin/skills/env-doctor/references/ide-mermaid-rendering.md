# Mermaid / SVG rendering-environment diagnosis

A Mermaid diagram that "won't render" is almost never a syntax problem — it is a **missing
renderer** in whatever surface you are viewing it in. Same for an SVG-generation script that dies
on layout: the wrong headless engine cannot measure text. This doc localizes *where the renderer
is missing*; it does not teach Mermaid authoring (that lives in the docs-wiki plugin's
`wiki-mermaid` skill — cross-reference it for diagram syntax, direction, palette, and per-platform
fence compatibility). Follow **observe → localize → safe action**; no mutation is involved beyond
installing the viewer component the user chooses.

## Symptom: a Mermaid block shows as raw ```` ```mermaid ```` text (or an empty box)

The block renders as literal fenced text, or a blank rectangle, instead of a diagram. This means
the surface displaying the Markdown has **no Mermaid renderer wired in**. Renderer support is
per-surface — the same file renders in one place and not another — so localize by surface:

| Surface | Renders Mermaid? | What it actually needs |
|---|---|---|
| GitHub / GitLab (web) | **Natively** | nothing — a raw ```` ```mermaid ```` fence renders on push |
| VS Code built-in Markdown **preview** | **No, by default** | a Mermaid **preview extension** (the core preview does not include Mermaid) |
| JetBrains IDEs (IDEA/PyCharm/WebStorm) | **No, by default** | the **Mermaid Marketplace plugin** — a separately installed plugin, *not* a Markdown-settings checkbox |
| A plain Markdown viewer / static host | Usually **no** | a build step (mermaid-cli / a Mermaid-aware SSG) or a browser-rendered page |

The two localizing traps:

- **JetBrains has no "enable Mermaid" toggle.** Users hunt through *Settings → Languages →
  Markdown* for a checkbox; there isn't one. Mermaid support arrives **only** by installing the
  dedicated Mermaid plugin from the JetBrains Marketplace, then reopening the preview. Absence of
  the plugin — not a disabled setting — is the cause.
- **VS Code's preview is not Mermaid-aware on its own.** The built-in Markdown preview needs a
  Mermaid extension added; without one, the fence is inert.

Observe → localize:

- Does the **same file** render on GitHub/GitLab but not in the IDE? → the diagram is valid; the
  IDE surface lacks a renderer (install the plugin/extension).
- Does it fail **everywhere including GitHub**? → then, and only then, suspect the diagram syntax —
  hand off to `wiki-mermaid` for the authoring rules and the platform-specific fence form.

Safe action: name the exact component for the user's surface (JetBrains Marketplace **plugin**;
a VS Code Mermaid **extension**) and let them install it — a viewer capability, applied by the
user. Do not restructure the diagram to "work around" a rendering gap that is really a missing
plugin; a valid diagram does not need rewriting.

## Symptom: an SVG-rendering script fails on `getBBox` / text has no size under jsdom

A Node script that builds or measures SVG (Mermaid-to-SVG, D3, chart rasterization) throws
`TypeError: … getBBox is not a function`, or produces an SVG where every text element collapses to
zero width/height and labels overlap. The script is running the SVG through **jsdom**.

Root cause: **jsdom is a DOM, not a layout/rendering engine.** It implements the SVG element API
surface but performs **no geometry** — `getBBox()`, `getComputedTextLength()`, and font metrics
either throw or return zeros, because nothing actually lays the text out. Mermaid (and any layout
that sizes nodes to their label text) depends on those measurements, so it cannot compute a correct
layout under jsdom.

Observe → localize:

- The stack trace names `getBBox` / a `*.getComputedTextLength` on a jsdom element, or the output
  SVG has `width="0"` text nodes → jsdom's missing layout, not your diagram data.

Safe action: **rasterize/measure with a real headless browser** (headless Chrome/Chromium via
Puppeteer or Playwright, which is what mermaid-cli uses under the hood), not jsdom. The browser has
a genuine layout engine, so `getBBox` and text metrics return real values and the diagram lays out
correctly. Reserve jsdom for DOM-shape assertions, never for SVG geometry. (Browser-binary and
headless-launch failures then fall to `references/playwright-browser.md`.)

## Cross-references

- `wiki-mermaid` (docs-wiki plugin) — Mermaid **authoring**: direction, shape/colour vocabulary,
  label hygiene, and the per-platform fence compatibility (e.g. the Azure DevOps colon-container
  form). This doc owns "my local viewer has no renderer"; `wiki-mermaid` owns "how to write the
  diagram."
- `references/playwright-browser.md` — when the headless-Chrome rasterizer itself will not launch
  (missing browser binary, profile lock).
