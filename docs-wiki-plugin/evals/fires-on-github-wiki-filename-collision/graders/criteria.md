---
type: llm
---
PASS if the reply says GitHub Wiki is a flat namespace where the filename, not the
folder path, becomes the URL slug, so two files anywhere in the wiki repo with the
same basename collide and silently overwrite or shadow each other, and recommends
giving each page a unique basename.
FAIL if the reply blames a git merge conflict, browser caching, or a push ordering
issue, or claims that putting the files in different folders is enough to keep them
separate, without naming the flat-namespace / filename-is-the-slug behavior.
