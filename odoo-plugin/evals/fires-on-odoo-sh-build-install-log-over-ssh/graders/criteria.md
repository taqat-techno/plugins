---
type: llm
---
PASS if the reply reads the build itself over SSH (the plugin's odoo-sh tools such as sh_logs
with file=install and sh_commit, or the equivalent git log -1 of ~/src/user and ~/logs/install.log
on the build), points to a setup/doctor step for the SSH connection, and treats the timeout as a
network/port-22 problem to diagnose (for example 443 works but 22 is blocked, with a ProxyJump or
port override or another network as the fix) rather than as a wrong key.
FAIL if it only says to look at the Odoo.sh web UI or rebuild, asks the user to paste a private
key, or claims Odoo.sh has an API token for build logs.
