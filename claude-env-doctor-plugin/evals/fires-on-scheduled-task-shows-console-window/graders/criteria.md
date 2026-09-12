---
type: llm
---
PASS if the reply explains that -WindowStyle Hidden on a PowerShell/console action still
lets the window flash and that the reliable fix is to point the Scheduled Task action at
a hidden-window wrapper, such as wscript.exe //B (or //B //Nologo) running a VBS script
that calls CreateObject("WScript.Shell").Run "<command>", 0, True and then propagates the
exit code with WScript.Quit, because wscript is a GUI host so no console host appears at
all.

FAIL if the reply only recommends -WindowStyle Hidden (or minimized/-NoLogo) as sufficient,
suggests running the script manually instead of via Scheduled Task, or gives generic
Scheduled Task setup advice without naming the wscript/VBS wrapper as the fix for the
console flash.
