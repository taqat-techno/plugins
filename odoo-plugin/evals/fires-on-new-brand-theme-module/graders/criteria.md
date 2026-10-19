---
type: llm
---
PASS if the reply scaffolds a theme_ module whose manifest has the Theme category and depends on
website, puts the colour palette and font configuration in a primary variables SCSS file loaded in
web._assets_primary_variables, and includes the theme's templates and preview images.
FAIL if it edits the core website module or loads the variables in the backend asset bundle.
