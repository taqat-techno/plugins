---
type: llm
---
PASS if the reply uses PlantUML activity diagrams with |Lane| partitions (not Mermaid subgraphs faked as lanes), says GitHub wikis cannot render PlantUML from text so the diagram is rendered to an image (PNG) that is committed into the wiki repository and embedded with a wiki link such as [[/images/<name>.png|alt text]], and keeps the .puml file as the editable source that is re-rendered on change.
FAIL if the reply proposes a Mermaid flowchart with subgraphs as the swimlane, or a live PlantUML server URL hotlinked as the image, without the render-commit-embed approach for a GitHub wiki.
