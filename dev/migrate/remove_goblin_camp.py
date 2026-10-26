"""The goblin camp the first world had at 3,4,0 is gone: Ashford grew over it (its market square is there now), and
no quest needs it. Takes away its goblins, its fires, the bones and scraps round them and its notice ("GO AWAY
HOOMANS!"); the map's arrival line names the square instead, and its music is the town's. A second run does nothing.

  python -I "dev\\migrate\\remove_goblin_camp.py"
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_isle import Map, DATA  # noqa: E402

CAMP = ("NPC\tGoblin_Archer\t", "NPC\tGoblin_Shaman\t", "NPC\tGoblin\t", "StaticObject\tFire\t", "MapItem\tBones\t",
        "MapItem\tRaw_Meat\t", "MapItem\tGold_Coin(s)\t", "StaticObject\tNotice\t417\t98\tId=Goblin_Camp_Sign")


def rewrite(path, old, new):
    if not os.path.exists(path):
        return False
    with open(path, "rb") as f:
        text = f.read().decode("cp1252")
    if old not in text:
        return False
    with open(path, "wb") as f:
        f.write(text.replace(old, new).encode("cp1252"))
    return True


def main():
    n = 0
    m = Map("3,4,0")
    kept = [ln for ln in m.ents if not ln.startswith(CAMP)]
    if len(kept) != len(m.ents):
        n += len(m.ents) - len(kept)
        m.ents = kept
        m.save()
    sign = os.path.join(DATA, "Scripts", "Read Goblin_Camp_Sign.txt")
    if os.path.exists(sign):
        os.remove(sign)
        n += 1
    n += rewrite(os.path.join(DATA, "Scripts", "3,4,0.txt"),
                 "01\tDisplay.Message\tDarkRed\tSmoke and the stink of goblins... this is their camp!\t-",
                 "01\tDisplay.Message\tCyan\tAshford's market square. Stallholders cry their wares.\t-")
    n += rewrite(os.path.join(DATA, "Music.ini"), "3,4,0=Danger", "3,4,0=Town")
    print("The goblin camp is gone from Ashford's market square (%d changes)" % n if n else "The goblin camp is gone already")


if __name__ == "__main__":
    main()
