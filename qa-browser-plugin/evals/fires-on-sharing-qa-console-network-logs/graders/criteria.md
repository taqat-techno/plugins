---
type: llm
---
PASS if the reply says to redact Authorization, Cookie and Set-Cookie headers, passwords or OTP codes in
request bodies and token-shaped values (for example JWTs) before the files are written or shared,
and gives a severity rule that separates console errors (fail the check unless allow-listed) from
warnings and info.
FAIL if the reply gives no redaction guidance for headers, cookies or tokens, or treats every console
message the same without a severity mapping.
