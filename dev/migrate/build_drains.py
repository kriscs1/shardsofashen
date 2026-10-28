"""Drains: monsters whose blows leave a skill lower for a while (dsengine/player_combat.py EFFECTS Weaken, Daze,
Frailty: the Stats tab shows it, 18/20). On.Hit=<Effect> <chance %>, on monsters that had none: the dead sap your
strength, magic things your wits, a brute's blows your guard. (The Antidote cures them as it cures the rest.)

Safe to run again (only the On.Hit lines that are missing are set).

  python -I "dev\\migrate\\build_drains.py"
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import Ini, p                      # noqa: E402

DRAINS = {"Skeleton": "Weaken 15", "Skeleton_Archer": "Weaken 10", "Tomb_Guardian": "Weaken 30",
          "Shard_Warden": "Daze 35", "Living_Remnant": "Daze 15", "Hob": "Frailty 15", "Hobgoblin": "Frailty 10"}


def main():
    ents = Ini(p("data", "Entities.ini"))
    for name, hit in DRAINS.items():
        if ents.section(name) is not None:
            ents.set(name, "On.Hit", hit, overwrite=False)
    cures = ents.get("Antidote", "Cures") or ""
    for fx in ("Weaken", "Daze", "Frailty"):
        if fx not in cures.split():
            cures = (cures + " " + fx).strip()
    ents.set("Antidote", "Cures", cures)
    ents.save(p("data", "Entities.ini"))
    print("Drains: %d monsters" % len(DRAINS))


if __name__ == "__main__":
    main()
