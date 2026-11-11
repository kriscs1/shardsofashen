"""Playing alone or together (dsengine/together.py, dev\\Roadmap.md group 15): its data and its people.

  * data\\Projects.ini: the towns' projects (what they need, the maps they're for, their perk).
  * Config.ini [Together]: a party's size, how much tougher a boss grows for each fighter, a sellsword's hire.
  * Entities.ini Boss=1 on the bosses; [Project_Plaque] (and its picture).
  * Set down by each town's square: the foremen (Foreman_<Project>), the town criers (Town_Crier_<Town>), the bounty
    clerk and the record keeper in Northport, a sellsword; each project's plaque and Mirefold's shardstone, shown once
    their project's done (Project=<Key>).
  * Beside Northport's two clerks, their boards: the bounty board (Read: the day's hunt) and the hall of records (Read:
    the records), each drawn here; and the clerks' own words (Talk to Bounty_Clerk, Talk to Record_Keeper).

Safe to run again (nothing is set down twice).

  python -I "dev\\migrate\\build_together.py"
"""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import Ini, p                      # noqa: E402
import sprite_kit as K                         # noqa: E402
import build_whimsy as BW                      # noqa: E402
import story_kit as SK                         # noqa: E402
from story_kit import Map                      # noqa: E402

MAKER = "build_together.py"

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
# (the clerk, the board set down beside them, which side: 1 east, -1 west; Read on it: together.py together_do)
BOARDS = [("Bounty_Clerk", "Bounty_Board", 1), ("Record_Keeper", "Records_Board", -1)]
BOARD_INFO = {"Bounty_Board": "A bounty board, its frame scored with claw marks. A dagger pins today's notice to it.",
              "Records_Board": "The hall of records, carved in pale stone and gilded: the names that have done the most "
                               "in Ashen."}
# (the record keeper, as first set down, stood in the mouth of Northport's north road: across from the bounty clerk
#  instead, the two boards between them; only if they're still where they were put)
MOVES = [("4,5,0", "Record_Keeper", (96, 344), (224, 376))]
WORDS = {
    "Bounty_Clerk": [
        SK.say("Clerk", "Every beast that bothers Ashen ends up on my board sooner or later. Today's is pinned up "
               "beside me. Bring me the count and I'll bring the purse.", ("Who pays for it?", "@pays"),
               ("Goodbye.", "@end")),
        ("@end",), ("End",),
        ("@pays",),
        SK.say("Clerk", "The towns put in, the farms put in, and anyone who's lost a sheep puts in twice. One bounty a "
               "day, mind. The purse isn't bottomless.", ("Goodbye.", "@end")),
    ],
    "Record_Keeper": [
        SK.say("Clerk", "Every beast slain, every secret found, every win in the arena: it's all on the board, and I "
               "check the sums twice. Ink doesn't lie. People do.", ("Am I on it?", "@me"), ("Goodbye.", "@end")),
        ("@end",), ("End",),
        ("@me",),
        SK.say("Clerk", "Anyone who's done anything worth writing down is. Have a look. If your name's not near the "
               "top, there's always tomorrow.", ("Goodbye.", "@end")),
    ],
}


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


def bounty_board():
    """A dark oak board on two posts, banded in iron, claw-scored: a WANTED notice with a paw print and a dagger
    through it, two torn notices: 32 x 48."""
    img, rng = K.new(32, 48), random.Random(7)
    oak, dark = (88, 60, 38), (54, 36, 22)
    for x in (4, 5, 6, 25, 26, 27):                             # the posts
        K.rect(img, x, 14, x, 47, dark if x in (6, 27) else (70, 48, 30))
    for y in range(11, 38):                                     # the planks
        for x in range(2, 30):
            K.put(img, x, y, dark if (y - 11) % 7 == 6 else K.jitter(oak, rng, 7))
    for y in (11, 37):                                          # the iron bands, riveted
        K.rect(img, 1, y, 30, y, (96, 96, 104))
        for x in (3, 10, 21, 28):
            K.put(img, x, y, (170, 170, 178))
    for i in range(3):                                          # claw marks down the left
        K.line(img, 3 + i * 2, 25, 6 + i * 2, 34, (150, 118, 84))
    paper, old = (228, 212, 172), (196, 176, 132)
    for y in range(15, 35):                                     # the WANTED notice
        for x in range(9, 23):
            K.put(img, x, y, old if (x in (9, 22) or y in (15, 34)) else K.jitter(paper, rng, 5))
    K.rect(img, 11, 17, 20, 18, (156, 36, 30))                  # (its heading, in red)
    ink = (36, 28, 24)
    for y, x0, x1 in ((25, 14, 17), (26, 13, 18), (27, 13, 18), (28, 13, 18), (29, 14, 15), (29, 17, 17)):
        K.rect(img, x0, y, x1, y, ink)                          # the paw: its pad...
    for x, y in ((11, 23), (13, 20), (17, 20), (19, 23)):       # (...and four toes apart from it)
        K.rect(img, x, y, x + 1, y + 2, ink)
    for x in (11, 14, 17):
        K.rect(img, x, 32, x + 2, 32, (120, 108, 90))
    for x0, y0, x1, y1 in ((2, 14, 7, 21), (24, 24, 29, 31)):   # two torn notices
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                if not (y == y1 and (x + y) % 2):
                    K.put(img, x, y, K.jitter(old, rng, 6))
        K.put(img, (x0 + x1) // 2, y0, (60, 60, 66))
    K.rect(img, 15, 12, 16, 16, (196, 200, 210))                # the dagger, through the top of the notice
    K.put(img, 16, 16, (140, 144, 156))
    K.rect(img, 13, 10, 18, 10, (150, 120, 60))                 # (its guard)
    K.rect(img, 15, 6, 16, 9, (96, 56, 30))                     # (its grip)
    K.rect(img, 15, 5, 16, 5, (200, 168, 80))
    return K.outline_img(img, (28, 20, 14))


def records_board():
    """The hall of records: a pale stone tablet in a gilt frame, its top arched with a gold star, two columns of names
    (the first of each gilded), a blue rosette, on a stepped plinth: 32 x 48."""
    img, rng = K.new(32, 48), random.Random(8)
    stone, gilt, deep = (222, 218, 206), (214, 176, 72), (150, 116, 40)
    for y in range(2, 40):                                      # the tablet, its top arched
        for x in range(3, 29):
            if y < 10 and (x - 15.5) ** 2 + ((y - 10) * 1.6) ** 2 > 12.5 ** 2:
                continue
            edge = x in (3, 4, 27, 28) or y in (38, 39)
            K.put(img, x, y, (deep if x in (4, 27) or y == 39 else gilt) if edge else
                  K.jitter(K.mix(stone, (190, 186, 178), (x + y) / 70.0), rng, 4))
    for x in range(5, 27):                                      # (the arch's gilt rim)
        for y in range(1, 11):
            if K.get(img, x, y) is not None and K.get(img, x, y - 1) is None:
                K.put(img, x, y, gilt)
                K.put(img, x, y + 1, deep)
    K.rect(img, 12, 8, 19, 9, gilt)                             # a little crown: its band...
    for x in (12, 15, 16, 19):                                  # (...three points)
        K.rect(img, x, 5 if x in (15, 16) else 6, x, 7, gilt)
    K.rect(img, 13, 7, 18, 7, gilt)
    K.put(img, 15, 5, (250, 228, 140))
    K.put(img, 16, 9, (180, 40, 40))                            # (a ruby in it)
    K.rect(img, 6, 11, 25, 11, deep)                            # (under the crest)
    for x0 in (7, 17):                                          # two columns of names
        for i, y in enumerate(range(14, 36, 3)):
            n = 3 + rng.randrange(4)
            K.rect(img, x0, y, x0 + n, y, gilt if i == 0 else (112, 108, 116))
            K.put(img, x0 + n + 2, y, (150, 146, 152))          # (and a number)
    K.rect(img, 24, 13, 26, 15, (52, 86, 168))                  # a blue rosette
    K.put(img, 25, 14, (230, 200, 90))
    K.put(img, 24, 16, (40, 66, 140))
    K.put(img, 26, 16, (40, 66, 140))
    for y, (x0, x1) in ((40, (8, 23)), (41, (8, 23)), (42, (6, 25)), (43, (6, 25)), (44, (4, 27)), (45, (4, 27)),
                        (46, (4, 27))):
        for x in range(x0, x1 + 1):                             # the plinth's steps
            K.put(img, x, y, K.jitter((168, 164, 156) if y in (40, 42, 44) else (136, 132, 126), rng, 4))
    return K.outline_img(img, (40, 38, 44))


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
    for board, info in BOARD_INFO.items():
        for k, v in (("Type", "StaticObject"), ("Use.Words", "Read,Examine"), ("Examine.Info", info)):
            if ents.get(board, k) is None:
                ents.set(board, k, v)
    ents.save(p("data", "Entities.ini"))
    K.save("Entities", "Project_Plaque", plaque())
    K.save("Entities", "Bounty_Board", bounty_board())
    K.save("Entities", "Records_Board", records_board())
    for pid, rows in WORDS.items():
        SK.write_script("Talk to " + pid, rows, MAKER)
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


def npc_line(m, pid):
    """(index, fields) of the NPC with Id=pid on map m, or (None, None)."""
    for i, ln in enumerate(m.ents):
        b = ln.split("\t")
        if b[0] == "NPC" and len(b) > 4 and ("Id=%s" % pid) in b[4].split():
            return i, b
    return None, None


def map_of(pid):
    """The map NPC pid stands on, or None."""
    for f in sorted(os.listdir(p("maps"))):
        if f.endswith(".txt") and npc_line(Map(f[:-4]), pid)[1] is not None:
            return f[:-4]
    return None


def boards():
    """Each clerk's board beside them (the record keeper out of the road first)."""
    for mname, pid, was, now in MOVES:
        m = Map(mname)
        i, b = npc_line(m, pid)
        if b is not None and (int(b[2]), int(b[3])) == was:
            b[2], b[3] = str(now[0]), str(now[1])
            m.ents[i] = "\t".join(b)
            m.save()
            print("  %s moved to %d,%d on %s" % (pid, now[0], now[1], mname))
    n = 0
    for pid, board, side in BOARDS:
        bid = "%s_Northport" % board
        mname = None if BW.placed(bid) else map_of(pid)
        if mname is None:
            continue
        m = Map(mname)
        b = npc_line(m, pid)[1]
        x, y = int(b[2]) + 32 * side, int(b[3]) + 8             # (a board stands on the clerk's row)
        taken = {(int(float(f[2])) // 32, (int(float(f[3])) + (8 if f[0] == "NPC" else 0)) // 32)
                 for f in (ln.split("\t") for ln in m.ents) if f[0] in ("NPC", "StaticObject") and len(f) > 3}
        if (x // 32, y // 32) in taken or not 0 <= x < 24 * 32:
            print("  !! no room for %s beside %s" % (board, pid))
            continue
        BW.put(mname, "StaticObject\t%s\t%d\t%d\tId=%s" % (board, x, y, bid))
        n += 1
    print("Boards: %d set down" % n)


def main():
    data()
    set_down()
    boards()


if __name__ == "__main__":
    main()
