---
max_turns: 12
allowed_tools: [Skill]
tags: [routing]
---

Our sprint-recap run built the Remotion project for this sprint's demo video. The app
under test has an Arabic interface, and in the rendered video the Arabic step captions
are laid out left-to-right with the work-item badge on the wrong side. I was about to
open the generated project and patch its caption component by hand. Is
that the right fix, and how is the caption direction supposed to be decided?
