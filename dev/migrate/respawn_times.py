"""Every NPC has its own Respawn= (seconds before one that was killed comes back), by how tough it is: prey and
vermin soonest, then the ordinary foes, the hard ones, the great ones last. Townsfolk and the other friendly NPCs
(they only die if a quest turns them on you) take 5 minutes. Run it again to set them again; a kind not listed keeps
what it has (dev\\migrate\\validate.py says if one has none).

  python -I "dev\\migrate\\respawn_times.py"
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from dragonsword import ini  # noqa: E402

TIERS = [
    (45, "Rat Bat"),                                                               # vermin
    (60, "Chicken Rabbit Duck Goblin"),                                            # prey, the weakest foes
    (75, "Goblin_Archer"),
    (90, "Cow Sheep Wolf Giant_Spider"),
    (120, "Hobgoblin Goblin_Shaman Skeleton Skeleton_Archer Snow_Wolf Scorpion Ember_Hound"),
    (150, "Bear Bandit Smuggler"),
    (180, "Ashen_Cultist"),
    (300, "Cave_Troll Bog_Troll Frost_Witch"),                                     # the hard ones
    (600, "Alpha_Wolf Frost_Troll"),                                               # the great ones
    (900, "Barrow_King Ashen_Priest"),
    (1800, "Dragon"),
]
KEEP = {"Ashen_Acolyte", "Hob"}                    # (a quest's own: their times are part of the story)
FRIENDLY = 300


def main():
    path = os.path.join(ROOT, "data", "Entities.ini")
    times = {name: secs for secs, names in TIERS for name in names.split()}
    text = open(path, encoding="cp1252").read()
    n = 0
    for m in re.finditer(r"(?ms)^\[([^\]]+)\]\s*\n(.*?)(?=^\[|\Z)", text):
        name, body = m.group(1), m.group(2)
        if not re.search(r"(?m)^Type=NPC\s*$", body) or name in KEEP:
            continue
        good = re.search(r"(?m)^Attitude=Good\s*$", body) and not re.search(r"(?m)^Hitpoints=", body)
        secs = times.get(name, FRIENDLY if good else None)
        if secs is not None and ini.read(name, "Respawn", "", path) != str(secs):
            ini.write(name, "Respawn", str(secs), path)
            n += 1
    print("Respawn times set: %d" % n)


if __name__ == "__main__":
    main()
