"""Signs read the right way round: "Smithy Sign", not "Sign Smithy". Each Sign_<Kind> in Entities.ini gets a
Display.Name (its Id stays Sign_<Kind>, so the maps and scripts that name it are as they were).

Safe to run again (a Display.Name already there is kept).

  python -I "dev\\migrate\\sign_names.py"
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import Ini, p                      # noqa: E402

NAMES = {"Dwarf": "Dwarven Wares", "Farm": "Farm Shop", "General": "General Store", "Magic": "Magic Shop",
         "Builder": "Builder's"}


def main():
    ents = Ini(p("data", "Entities.ini"))
    n = 0
    for sec, items in ents.sections:
        if not sec or not sec.startswith("Sign_") or (ents.get(sec, "Display.Name") or ""):
            continue
        kind = sec[len("Sign_"):]
        ents.set(sec, "Display.Name", "%s Sign" % NAMES.get(kind, kind.replace("_", " ")), overwrite=False)
        n += 1
    ents.save(p("data", "Entities.ini"))
    print("Signs named: %d" % n)


if __name__ == "__main__":
    main()
