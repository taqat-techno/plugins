---
type: llm
---
PASS if the reply walks ragtools-specific release invariants and asks for an explicit ack or hold on each, including at least: no new code path writes user data into the install directory; a schema change bumps its version and ships a migration step; the installer is tested as an upgrade over a machine that already has the previous version, preserving user data; and uninstall is tested on both answers of the keep-or-wipe data prompt -- and it treats the schema and installer changes the user mentioned as making those items load-bearing.
FAIL if the reply gives only a generic release checklist (run the tests, update the changelog, bump the version, tag and publish) without the install-directory user-data rule, the schema-version-plus-migration rule, and the upgrade and uninstall data-preservation tests.
