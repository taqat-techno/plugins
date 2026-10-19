# SCSS Load Order Rule

All theme variables live in the `web._assets_primary_variables` bundle. Inside it, core
defines the variables in this order (checked against the Odoo 19 source):

```
1. html_editor / web_editor variables   $o-color-palettes: (...) !default   (base-1 ... base-N)
2. website primary_variables.scss       $o-color-palettes: map-merge($o-color-palettes, ...)
                                        $o-website-values-palettes: (...) !default
                                        $o-theme-font-configs: (...) !default
3. YOUR theme's file (appended)         reads and extends the variables above
```

An `Undefined variable $o-color-palettes` (or `$o-theme-font-configs`, ...) error means your
SCSS reads the variable before step 1-2 has run: the file is `('prepend', ...)`ed, or it sits in
a frontend bundle (`web.assets_frontend`) or an `@import` chain compiled outside the primary
variables. Adding `!default` does not fix it.

## Rules

- **Custom colour palette:** add it with `map-merge` in a file **appended** to
  `web._assets_primary_variables` (Odoo's own `theme_*` modules do exactly this), then select
  it with `'color-palettes-name'` in `$o-website-values-palettes`.
- **Never `map-merge` (or `map-get`) a core variable in a prepended file** - it is undefined
  there. That is the usual cause of the error.
- **Never redefine `$o-color-palettes` standalone in a prepended file.** It wins over the core
  `!default`, removes the stock `base-*` palettes, and website's own
  `map-get($o-color-palettes, 'base-1')` then fails.
- A prepended file may only set the variables core declares `!default` and never reads core
  ones: `$o-website-values-palettes`, `$o-theme-font-configs`. Never put palette or
  website-values variables in `web.assets_frontend`.
- **NEVER** use `ir.asset` records for Google Fonts -- use `$o-theme-font-configs` instead.
- **H6 is ALWAYS 16px** (1rem) -- the fixed base reference, never change this multiplier.

## WRONG

```scss
// primary_variables.scss, loaded with ('prepend', ...) or in web.assets_frontend
$o-color-palettes: map-merge($o-color-palettes, (...));
// ERROR: Undefined variable $o-color-palettes - core has not defined it yet
```

## RIGHT

```scss
// theme_name/static/src/scss/primary_variables.scss, appended to web._assets_primary_variables
$o-color-palettes: map-merge($o-color-palettes, (
    'my-palette': (
        'o-color-1': #207AB7,
        'o-color-2': #FB9F54,
        'o-color-3': #F6F4F0,
        'o-color-4': #FFFFFF,
        'o-color-5': #191A19,
    ),
));

$o-website-values-palettes: (
    (
        'color-palettes-name': 'my-palette',
        'font': 'Inter',
    ),
);
```

## Manifest Asset Bundle Syntax

```python
'assets': {
    'web._assets_primary_variables': [
        # appended (no 'prepend'): loads after website's definitions because the theme
        # depends on website
        'theme_name/static/src/scss/primary_variables.scss',
    ],
}
```

If a theme already prepends a file for `$o-theme-font-configs` / `$o-website-values-palettes`,
keep that file free of reads of core variables and put the palette `map-merge` in a second,
appended file in the same bundle.
