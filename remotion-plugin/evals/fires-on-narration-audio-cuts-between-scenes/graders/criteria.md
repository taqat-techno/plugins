---
type: llm
---
PASS if the reply identifies that the Audio components are nested inside per-scene Sequence elements as the root cause, and instructs moving to a single continuous Audio element placed at the root/top level (outside any Sequence) with one concatenated narration track, rather than one Audio per Sequence.
FAIL if the reply gives generic audio-editing advice (crossfades, adjusting volume, checking file format) without identifying that Audio must live at the root level outside the Sequence, or if it suggests keeping a separate Audio tag inside each Sequence.
