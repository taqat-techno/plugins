---
type: llm
---
PASS if the reply recommends separate Pydantic schemas for input and output (for example UserCreate without is_admin or server-set fields, and UserRead without hashed_password, using from_attributes / ConfigDict(from_attributes=True)), set as the request body type and response_model, and flags that accepting is_admin in the request body is a mass-assignment risk.
FAIL if the reply only suggests deleting the field from the returned dict, or excluding it ad hoc, without separating request and response models, or does not mention the mass-assignment risk of the shared input model.
