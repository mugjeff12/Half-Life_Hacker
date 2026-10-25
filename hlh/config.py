"""Run-time switches.

Students' build: the 👁 Solution button is hidden.
Instructor / testing: set the environment variable HLH_INSTRUCTOR=1 before launching to bring it back, e.g.
    Windows (cmd):   set HLH_INSTRUCTOR=1 && HalfLifeHacker.exe
    macOS / Linux:   HLH_INSTRUCTOR=1 ./HalfLifeHacker
(The self-test loads solutions straight into the editor, so it does not need the button.)
"""
import os

SOLUTIONS_ENABLED = os.environ.get("HLH_INSTRUCTOR", "").strip().lower() in ("1", "true", "yes")
