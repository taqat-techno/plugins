---
type: llm
---
PASS if the reply explains that Qdrant local mode takes an exclusive single-process file lock on the data directory, that the running ragtools service already holds it, and that the CLI "rag index" (like "rag rebuild", "rag watch" or a standalone "rag-mcp") opens Qdrant directly and so fights the service -- and says to re-index through the running service instead (its HTTP API on 127.0.0.1, or the plugin's projects/rebuild flow) or to stop the service first with "rag service stop" before using the CLI.
FAIL if the reply only suggests deleting a lock file, killing random Python processes, rebooting, or reinstalling, without naming the service-versus-CLI lock conflict and the "index through the service or stop it first" remedy.
