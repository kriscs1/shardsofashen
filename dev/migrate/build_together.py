"""Playing alone or together (dsengine/together.py, dev\\Roadmap.md group 15): its data and its people.

  * data\\Projects.ini: the towns' projects (what they need, the maps they're for, their perk).
  * Config.ini [Together]: a party's size, how much tougher a boss grows for each fighter, a sellsword's hire.
  * Entities.ini Boss=1 on the bosses; [Project_Plaque] (and its picture).
  * Set down by each town's square: the foremen (Foreman_<Project>), the town criers (Town_Crier_<Town>), the bounty
    clerk and the record keeper in Northport, a sellsword; each project's plaque and Mirefold's shardstone, shown once
    their project's done (Project=<Key>).

Safe to run again (nothing is set down twice).

  python -I "dev\\migrate\\build_together.py"
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import Ini, p                      # noqa: E402
import sprite_kit as K                         # noqa: E402
import build_whimsy as BW                      # noqa: E402

PROJECTS = """; The towns' projects (dsengine/together.py): anyone gives to its foreman (Foreman_<Key>) what it Needs; when it's
; all there the town changes for everyone: what has Project=<Key> on its map line appears, and its Perk holds for the
; Maps (x1,y1,x2,y2): FreeTravel (a shardstone there is free to come to), Restock (shops there restock twice as fast).
; Written by dev\\migrate\\build_together.py: edit the numbers here.

[Northport_Harbour]
Title=Northport's harbour
Town=Northport
Maps=2,4,5,6
Needs=Logs 200, Iron_Bar 40, Gold_Coin(s) 1500
Perk=FreeTravel

[Galaith_Market]
Title=Galaith's market
Town=Galaith
Maps=-12,11,-4,18
Needs=Logs 150, Iron_Bar 60, Silver_Bar 10, Gold_Coin(s) 3000
Perk=Restock

[Mirefold_Boardwalks]
Title=Mirefold's boardwalks
Town=Mirefold
Maps=-8,4,-6,6
Needs=Logs 300, Gold_Coin(s) 800
Perk=
"""
CONFIG = [("Party.Size", "5"), ("Boss.Per.Player", "0.6"), ("Hire.Gold", "25"), ("Hire.Minutes", "10"),
          ("Away.Hours", "20")]
BOSSES = ["Galaith_Dragon", "Dragon", "Shard_Warden", "Barrow_King", "Ashen_Priest", "Tomb_Guardian", "Valour_Guardian",
          "Frost_Witch", "Alpha_Wolf"]
# (place by, kind, options, seed): set down near a square
PEOPLE = [
    ("Northport_Square", "Settler", "Id=Foreman_Northport_Harbour Name=Foreman_Hale", 1),
    ("Galaith_Square", "Settler", "Id=Foreman_Galaith_Market Name=Foreman_Brannock", 2),
    ("Mirefold_Square", "Settler", "Id=Foreman_Mirefold_Boardwalks Name=Foreman_Tansy", 3),
    ("Northport_Square", "Villager", "Id=Town_Crier_Northport Name=Town_Crier", 4),
    ("Ashford_Square", "Villager", "Id=Town_Crier_Ashford Name=Town_Crier", 5),
    ("Galaith_Square", "Villager", "Id=Town_Crier_Galaith Name=Town_Crier", 6),
    ("Northport_Square", "Clerk", "Id=Bounty_Clerk Name=Bounty_Clerk", 7),
    ("Northport_Square", "Clerk", "Id=Record_Keeper Name=Keeper_of_Records", 8),
    ("Northport_Square", "Guard", "Id=Sellsword_Northport Name=Sellsword", 9),
]
THINGS = [   # (place by, kind, options, seed): shown once their project's done
    ("Northport_Square", "Project_Plaque", "Id=Plaque_Northport_Harbour Project=Northport_Harbour", 11),
    ("Galaith_Square", "Project_Plaque", "Id=Plaque_Galaith_Market Project=Galaith_Market", 12),
    ("Mirefold_Square", "Project_Plaque", "Id=Plaque_Mirefold_Boardwalks Project=Mirefold_Boardwalks", 13),
]


def plaque():
    """A stone plaque on a post: carved lines, a little gilt."""
    img = K.new()
    for y in range(8, 22):
        for x in range(8, 24):
            img[y][x] = (196, 190, 176) if y > 9 and 9 < x < 22 else (150, 144, 132)
    for y in (12, 15, 18):
        for x in range(11, 21):
            if (x + y) % 3:
                img[y][x] = (110, 104, 94)
    img[10][15], img[10][16] = (230, 196, 90), (210, 170, 70)
    for y in range(22, 29):
        for x in (14, 15, 16, 17):
            img[y][x] = (120, 84, 50) if x < 16 else (96, 66, 40)
    return K.outline_img(img, (40, 36, 30))


def data():
    path = p("data", "Projects.ini")
    if not os.path.exists(path):
        with open(path, "wb") as f:
            f.write(PROJECTS.replace("\n", "\r\n").encode("cp1252"))
    cfg = p("data", "Config.ini")
    text = open(cfg, "rb").read().decode("cp1252")
    if "[Together]" not in text:
        text = text.rstrip("\r\n") + "\r\n\r\n[Together]\r\n; Playing together (dsengine/together.py): a party's size; how much more health a boss has for each\r\n" \
               "; player past the first fighting it; a sellsword's gold and minutes; hours away before a 'while you were away'.\r\n" + \
               "".join("%s=%s\r\n" % kv for kv in CONFIG)
        open(cfg, "wb").write(text.encode("cp1252"))
    ents = Ini(p("data", "Entities.ini"))
    for b in BOSSES:
        if ents.get(b, "Type") is not None and ents.get(b, "Boss") is None:
            ents.set(b, "Boss", "1")
    for k, v in (("Type", "StaticObject"), ("Use.Words", "Read,Examine"), ("Solid", "1"),
                 ("Examine.Info", "A stone plaque, carved with names.")):
        if ents.get("Project_Plaque", k) is None:
            ents.set("Project_Plaque", k, v)
    ents.save(p("data", "Entities.ini"))
    K.save("Entities", "Project_Plaque", plaque())
    stones = p("data", "Shardstones.ini")
    if "[Mirefold]" not in open(stones, "rb").read().decode("cp1252"):
        with open(stones, "ab") as f:
            f.write(b"\r\n[Mirefold]\r\nTitle=Mirefold\r\n")


def set_down():
    n = 0
    for anchor, kind, opts, seed in PEOPLE + THINGS:
        pid = next(o.split("=", 1)[1] for o in opts.split() if o.startswith("Id="))
        if BW.placed(pid) or anchor not in BW.place_ids():
            continue
        mname, at = None, None
        for rmin, rmax, off_road in ((3, 8, True), (3, 12, False), (2, 14, False)):
            mname, at = BW.free_spot(anchor, rmin, rmax, seed, off_road)
            if at:
                break
        if at is None:
            print("  !! no room for %s by %s" % (pid, anchor))
            continue
        x, y = at
        if kind == "Project_Plaque":
            line = "StaticObject\t%s\t%d\t%d\t%s" % (kind, (x - 1) * 32, (y - 1) * 32 - 8, opts)
        else:
            line = "NPC\t%s\t%d\t%d\tAttitude=Good Stand=1 Face=S %s" % (kind, (x - 1) * 32, (y - 1) * 32 - 8, opts)
        BW.put(mname, line)
        n += 1
    if not BW.placed("Waystone_Mirefold_Stone") and "Mirefold_Square" in BW.place_ids():
        for rmin, rmax, off_road in ((2, 7, True), (2, 12, False), (2, 16, False)):
            mname, at = BW.free_spot("Mirefold_Square", rmin, rmax, 21, off_road)
            if at:
                break
        if at:                                          # (Mirefold's shardstone: once the boardwalks are mended)
            BW.put(mname, "StaticObject\tShardstone\t%d\t%d\tProject=Mirefold_Boardwalks Id=Waystone_Mirefold_Stone"
                   % ((at[0] - 1) * 32, (at[1] - 1) * 32))
            BW.put(mname, "Id\tWaystone_Mirefold\t%d\t%d" % (at[0], at[1] + 1))
            n += 1
    print("Together: %d set down" % n)


def main():
    data()
    set_down()


if __name__ == "__main__":
    main()
