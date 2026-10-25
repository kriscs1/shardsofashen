"""Items renamed: their names in the data, the scripts that name them, their pictures. Run it once (again: nothing
left to do). Characters and the world saved with the old names are put right as they load (dsengine/renames.py).

  python -I "dev\\migrate\\rename_items.py"

  Raw_Chicken -> Raw_Poultry, Cooked_Chicken -> Cooked_Poultry, Burnt_Chicken -> Burnt_Poultry
"""
import glob
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from dsengine.renames import RENAMED_ITEMS  # noqa: E402


WORDS = {"Raw Chicken": "Raw Poultry", "Raw chicken": "Raw poultry", "Cooked Chicken": "Cooked Poultry",
         "Cooked chicken": "Cooked poultry", "Burnt Chicken": "Burnt Poultry", "Burnt chicken": "Burnt poultry"}


def swap(text, words=True):
    for old, new in RENAMED_ITEMS.items():
        text = text.replace(old, new)
    if words:                                           # (what the messages and descriptions call it, too)
        for old, new in WORDS.items():
            text = text.replace(old, new)
    return text


def main():
    files = [os.path.join(ROOT, "data", f) for f in ("Entities.ini", "ItemRacks.ini", "Gathering.ini", "Crops.ini",
                                                      "Spells.ini", "Digging.ini", "Waves.ini", "Buildables.ini")]
    files += glob.glob(os.path.join(ROOT, "data", "Scripts", "*.txt"))
    files += glob.glob(os.path.join(ROOT, "maps", "**", "*.txt"), recursive=True)
    files += glob.glob(os.path.join(ROOT, "saves", "*.ini"))
    files += [os.path.join(ROOT, "dev", "migrate", f) for f in ("build_content.py", "build_scenery.py", "build_world.py")]
    n = 0
    for path in files:
        if not os.path.exists(path):
            continue
        raw = open(path, "rb").read()
        text = raw.decode("cp1252")
        new = swap(text)
        if new != text:
            open(path, "wb").write(new.encode("cp1252"))
            n += 1
    moved = 0
    for folder in (os.path.join(ROOT, "data", "Scripts"), os.path.join(ROOT, "sprites", "Entities")):
        for f in os.listdir(folder):
            g = swap(f, words=False)
            if g != f and not os.path.exists(os.path.join(folder, g)):
                os.replace(os.path.join(folder, f), os.path.join(folder, g))
                moved += 1
    print("Renamed: %s (%d files changed, %d moved)" % (", ".join("%s -> %s" % kv for kv in RENAMED_ITEMS.items()),
                                                          n, moved))


if __name__ == "__main__":
    main()
