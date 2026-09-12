---
type: llm
---
PASS if the reply identifies that Django adds every ORDER BY column to the GROUP BY, so the model's Meta ordering ("-created_at") is silently joining the GROUP BY alongside "status" and splitting each status into one bucket per distinct created_at value, which is why the summed bucket counts exceed the real row count. The fix must be to clear the inherited ordering with a bare .order_by() placed before .values("status").annotate(...), applying any desired ordering after the annotate call.
FAIL if the reply attributes the inflation to a different generic cause (duplicate rows, a join fan-out, needing .distinct(), miscounting Count("id") vs Count("status")) without naming the ordering-joins-GROUP-BY mechanism, or if it "fixes" it only by removing ordering = [...] from the model's Meta class entirely instead of clearing/reordering it within the query itself.
