---
type: llm
---
PASS if the reply says this is not enough and names at least two of these gaps: (1) admin or superuser bypasses record rules and ACLs, so the change must be tested as a user holding only the clerk role, with both the allowed and the refused case; (2) the other modules that use stock.picking must have their test suites run too, because a rule or ACL on a shared model can break their flows; (3) run the untouched baseline first or report which tests changed colour; (4) check a fresh install as well as the upgrade.
FAIL if the reply accepts green tests from the changed module run as admin as sufficient.
