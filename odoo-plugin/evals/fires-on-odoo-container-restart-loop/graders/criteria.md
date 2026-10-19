---
type: llm
---
PASS if the reply starts from the container's own logs (docker compose logs or docker logs for the
Odoo service), then checks the database connection settings (host, user, password env vars or
odoo.conf), the mounted config and addons paths, and the restart policy or healthcheck, in an Odoo-
specific way.
FAIL if it suggests docker compose down -v, deleting or pruning volumes, or recreating the database
as a first step, or gives only generic Docker advice with no Odoo specifics.
