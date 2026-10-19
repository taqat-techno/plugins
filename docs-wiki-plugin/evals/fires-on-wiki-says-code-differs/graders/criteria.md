---
type: llm
---
PASS if the reply refuses to pick a side silently, explains that the mismatch must be classified with evidence from both sides (file and line or the exact wiki quote) as doc-drift (code right, wiki stale), code-drift (wiki is the intended policy, code drifted), an intentional gap (wiki describes target state not built yet) or unknown, and leaves the direction for the user or the policy owner to choose before anything is edited.
FAIL if the reply simply agrees to update the wiki to match the code, or simply says to fix the code, without naming that the wiki may be the authoritative policy and without the classify-then-let-the-owner-choose step.
