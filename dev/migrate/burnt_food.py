"""Burnt food is one thing: Burnt_Food, a heap of charcoal that stacks, whatever it was before (Burnt_Meat,
Burnt_Poultry, Burnt_Herring). Their names in the data, the scripts, the maps, the saves and the builders become
Burnt_Food; their three Entities.ini sections one; their pictures go (build_items.py draws Burnt_Food). Saves made
with the old names are put right as they load (dsengine/renames.py).

Safe to run again (nothing left to do).

  python -I "dev\\migrate\\burnt_food.py"
"""
import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import Ini, p                      # noqa: E402

OLD = ("Burnt_Meat", "Burnt_Poultry", "Burnt_Herring")
NEW = "Burnt_Food"
ENTRY = [("Type", "MapItem"), ("Display.Name", "Burnt Food"), ("Value", "0"), ("Stackable", "100"),
         ("Examine.Info", "Charcoal. Whatever it was, it isn't now.")]


def swap(text):
    for old in OLD:
        text = text.replace(old, NEW)
    return text


def main():
    ents = Ini(p("data", "Entities.ini"))
    had = [o for o in OLD if ents.section(o) is not None]
    ents.sections = [s for s in ents.sections if s[0] not in had]
    if ents.section(NEW) is None:
        for k, v in ENTRY:
            ents.set(NEW, k, v)
    ents.save(p("data", "Entities.ini"))
    files = [p("data", f) for f in ("ItemRacks.ini", "Gathering.ini", "Crops.ini", "Digging.ini", "Waves.ini",
                                    "Buildables.ini", "Quests.ini")]
    files += glob.glob(p("data", "Scripts", "*.txt")) + glob.glob(p("maps", "*.txt")) + glob.glob(p("saves", "*.ini"))
    files += [p("dev", "migrate", f) for f in ("build_content.py", "build_world.py", "build_water_animals.py")]
    n = 0
    for path in files:
        if not os.path.exists(path):
            continue
        text = open(path, "rb").read().decode("cp1252")
        new = swap(text)
        if new != text:
            open(path, "wb").write(new.encode("cp1252"))
            n += 1
    gone = 0
    for o in OLD:
        f = p("sprites", "Entities", o + ".png")
        if os.path.exists(f):
            os.remove(f)
            gone += 1
    print("Burnt food: %d sections made one, %d files changed, %d old pictures gone" % (len(had), n, gone))


if __name__ == "__main__":
    main()
