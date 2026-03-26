# SCSS Load Order Rule

Theme SCSS files load BEFORE core Odoo variables are defined:

```
1. YOUR theme's primary_variables.scss (via prepend)  <- FIRST
2. Odoo core primary_variables.scss                    <- SECOND
```

## Consequences

- **NEVER** use `map-merge()` with core Odoo variables -- they are undefined at load time
- **ALWAYS** use `('prepend', ...)` for primary_variables.scss in asset bundles
- **NEVER** use `ir.asset` records for Google Fonts -- use `$o-theme-font-configs` instead
- **H6 is ALWAYS 16px** (1rem) -- the fixed base reference, never change this multiplier

## WRONG

```scss
$o-color-palettes: map-merge($o-color-palettes, (...));
// ERROR: $o-color-palettes is undefined at this point
```

## RIGHT

```scss
// Define standalone variables without map-merge in primary_variables.scss
$o-color-palettes: (
  (
    'color-palettes-name': 'my-palette',
    'o-color-1': #207AB7,
    'o-color-2': #FB9F54,
    'o-color-3': #F6F4F0,
    'o-color-4': #FFFFFF,
    'o-color-5': #191A19,
  ),
);
```

## Manifest Asset Bundle Syntax

```python
'assets': {
    'web._assets_primary_variables': [
        ('prepend', 'theme_name/static/src/scss/primary_variables.scss'),
    ],
}
```

The `('prepend', ...)` tuple ensures your theme variables load before Odoo core.
