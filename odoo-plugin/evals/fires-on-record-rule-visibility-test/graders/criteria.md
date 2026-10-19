---
type: llm
---
PASS if the reply writes a TransactionCase tagged post_install and -at_install, creates users in the
right groups and teams, runs the search with with_user() as the restricted user, asserts both the
allowed and the forbidden records, and does not use sudo() for the check.
FAIL if it tests as the admin or with sudo(), or only describes manual testing.
