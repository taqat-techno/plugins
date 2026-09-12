---
type: llm
---
PASS if the reply explains that manually dispatchable workflows are read from the DEFAULT branch, so a workflow_dispatch trigger defined only on a feature branch has no Run button and gh workflow run rejects it, and that the fix is to merge the workflow file to the default branch before it can be dispatched by hand.
FAIL if the reply diagnoses this as a permissions/token/PAT problem, a YAML syntax error, or a caching/propagation delay, or otherwise never names the default-branch requirement for workflow_dispatch.
