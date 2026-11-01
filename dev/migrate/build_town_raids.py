"""A surprise raid for every town, not only Ashford (the owner's wish): data\\Waves.ini gets a [<Town>_Raid] for each
of the world map's towns that has none, its raiders fitting its land - goblins in the meadows, wolves and spiders in
the woods, scorpions in the desert, snow wolves round Frosthold, ember hounds and cultists at Emberwatch,
hobgoblins at the Keep, bandits and smugglers off the sea at Northport. Like Ashford's, each comes now and then
(Random.Every) while someone's there to meet it (dsengine/waves.py).

Safe to run again (a raid that's there is kept as it is: edit the numbers in Waves.ini).

  python -I "dev\\migrate\\build_town_raids.py"
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import world_edit as W                                   # noqa: E402

ROOT = W.ROOT
WAVES = os.path.join(ROOT, "data", "Waves.ini")
WORLDMAP = os.path.join(ROOT, "data", "WorldMap.ini")
SKIP = ("Ashford", "Galaith", "Isle Village")            # (Ashford has its own; Galaith's the dragon's; the Isle's
                                                         # where you learn)
RAIDERS = {   # land: (who, the raid's name, the waves)
    "meadow": ("Goblins", "Goblin", "Goblin*3;Goblin*4,Goblin_Archer*1;Hobgoblin*2,Goblin*3,Goblin_Shaman*1"),
    "wood": ("Wolves", "Wolf", "Wolf*3;Wolf*3,Giant_Spider*2;Alpha_Wolf*1,Wolf*3"),
    "marsh": ("Things out of the bog", "Bog", "Giant_Spider*2,Rat*3;Hobgoblin*3,Rat*2;Bog_Troll*1,Hobgoblin*2"),
    "desert": ("Scorpions", "Scorpion", "Scorpion*2;Scorpion*3;Scorpion*3,Bandit*2"),
    "snow": ("Snow wolves", "Snow wolf", "Snow_Wolf*2;Snow_Wolf*3;Frost_Witch*1,Snow_Wolf*3"),
    "ash": ("Ember hounds", "Ember hound", "Ember_Hound*2;Ember_Hound*2,Ashen_Cultist*1;Ashen_Cultist*2,Ember_Hound*2"),
    "keep": ("Hobgoblins", "Hobgoblin", "Hobgoblin*3;Hobgoblin*4,Goblin_Archer*2;Hobgoblin*4,Goblin_Shaman*2"),
    "sea": ("Raiders off the sea", "Sea", "Bandit*3;Bandit*3,Smuggler*2;Bandit*4,Smuggler*2"),
}
OWN = {"King Rupert's Keep": "keep", "Northport": "sea", "Oakhollow": "wood", "Wildwood": "wood",
       "Thornwick": "wood"}


def towns():
    out, sec = [], None
    for ln in W.read(WORLDMAP).splitlines():
        if ln.startswith("["):
            sec = ln.strip("[]")
        elif sec == "Towns" and "=" in ln and not ln.startswith(";"):
            name, place = ln.split("=", 1)
            out.append((name.strip(), place.strip()))
    return out


def land_of(w, c):
    seen = {}
    for dx in range(-12, 13):
        for dy in range(-12, 13):
            t = w.tile(c[0] + dx, c[1] + dy) or ""
            k = "snow" if t.startswith(("Snow", "Ice")) else "desert" if t.startswith("Sand") else \
                "marsh" if t.startswith("Marsh") else "ash" if t.startswith(("Ash", "Cinder")) else \
                "wood" if t.startswith("Forest") else "meadow" if t.startswith("Grass") else None
            if k:
                seen[k] = seen.get(k, 0) + 1
    if seen.get("desert", 0) > 60 and seen.get("desert", 0) > seen.get("meadow", 0) // 2:
        return "desert"
    return max(seen, key=seen.get) if seen else "meadow"


def main():
    w = W.World(0)
    s = W.read(WAVES)
    added = []
    for name, place in towns():
        if name in SKIP:
            continue
        key = re.sub(r"[^A-Za-z]", "", place.replace("_Square", "")) + "_Raid"
        if "[%s]" % key in s:
            continue
        m, c = w.find_id(place)
        if m is None:
            print("  !! no %s" % place)
            continue
        land = OWN.get(name) or land_of(w, c)
        who, label, waves = RAIDERS[land]
        s = s.rstrip("\r\n") + "\r\n\r\n" + "\r\n".join([
            "[%s]" % key,
            "Name=%s raid on %s" % (label, name),
            "Map=%s" % m.name,
            "Centre=%s" % place,
            "Waves=%s" % waves,
            "Gap=12", "Minutes=8", "Random.Every=120", "Random.Players=2", "Gold.Per.Kill=4", "Reward.Gold=60",
            "Reward.Items=Super_Potion 1", "Reward.XP=1",
            "Start.Message=A horn sounds: %s are attacking %s! Defend the square!" % (who.lower(), name),
            "Win.Message=The raiders flee. %s is safe - thanks to its defenders!" % name,
            "Lose.Message=The raiders take what they can and are gone."]) + "\r\n"
        added.append("%s (%s)" % (name, land))
    W.write(WAVES, s)
    print("Raids added: %s" % (", ".join(added) or "none"))


if __name__ == "__main__":
    main()
