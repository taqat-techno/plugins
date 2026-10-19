---
type: llm
---
PASS if the reply says no: the API call behind the page must also be checked, and a UI denial with an API
that still returns 200 and data is a leak (the UI hides but the API allows), so the network response
status for that role must be captured, ideally for other HTTP methods too.
FAIL if the reply accepts the hidden link and the 403 page as sufficient without checking the API response
for that role.
