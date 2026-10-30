"""Stealth, and the stances (dsengine/stances.py):

  * The Stealth skill, after Homesteading (Config [Skills] List, Icon.Stealth: a hooded face, eyes in the shadow).
  * data\\Stances.ini: every number of the stances (Fighting, Channelling, Sneaking) and of being seen and heard,
    sneak attacks, slipping past (only the keys missing are added: edit them there).
  * The stances' pictures for the button by your health (Stance_None, _Fighting, _Channelling, _Sneaking).

Their sounds are build_soundscape.py's. Safe to run again.

  python -I "dev\\migrate\\build_stealth.py"
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import Ini, p                      # noqa: E402
import sprite_kit as K                         # noqa: E402

STANCES = [   # (section, key, value, what it means: the comment above it)
    ("Stances", "Change.Seconds", "1", "Seconds a new stance takes to take hold"),
    ("Stances", "Noise.Walk", "110", "How far off you're heard (pixels): walking, standing still, fighting"),
    ("Stances", "Noise.Still", "24", None),
    ("Stances", "Noise.Fight", "220", None),
    ("Stances", "Sneak.Attack", "2", "A blow a monster never saw coming: its most, times this"),
    ("Stances", "Sneak.Attack.XP", "0.3", "Stealth xp for one, and for slipping past a monster unseen"),
    ("Stances", "Sneak.Past.XP", "0.15", None),
    ("Fighting", "Attack", "1.15", "Harder blows and a firmer guard (times), but magic in a blow and its drains and poisons"),
    ("Fighting", "Damage", "1.15", None),
    ("Fighting", "Defence", "1.15", None),
    ("Fighting", "Spell.Hurt", "1.3", None),
    ("Fighting", "Status.Hurt", "1.5", None),
    ("Channelling", "Spell.Power", "1.25", "Spells stronger, wards and spell boosts longer, drains shrugged off (in 100);"),
    ("Channelling", "Spell.Duration", "1.4", "slower on foot, a weaker guard (potions are herbs: never touched)"),
    ("Channelling", "Resist.Status", "50", None),
    ("Channelling", "Walk", "0.8", None),
    ("Channelling", "Defence", "0.85", None),
    ("Sneaking", "Walk", "0.6", "Slower on foot; heard (times) and seen (a part of a monster's Aggro.Range) less; each"),
    ("Sneaking", "Noise", "0.45", "Stealth level takes a little more off (Per.Level), never under Least; a lookout's cone"),
    ("Sneaking", "Noise.Per.Level", "0.02", "narrows the same way"),
    ("Sneaking", "Sight", "0.6", None),
    ("Sneaking", "Sight.Per.Level", "0.015", None),
    ("Sneaking", "Sight.Least", "0.3", None),
    ("Sneaking", "Cone.Per.Level", "0.015", None),
    ("Senses", "Reach", "80", "Noticing a hidden trap or a secret (senses.py): how near (pixels); in 100, and each Stealth"),
    ("Senses", "Chance", "15", "level, and more sneaking (a secret: six tenths of it); a trap's level to disarm; Stealth xp"),
    ("Senses", "Chance.Per.Level", "3", None),
    ("Senses", "Sneaking", "30", None),
    ("Senses", "Trap.Level", "3", None),
    ("Senses", "Trap.XP", "0.2", None),
    ("Senses", "Secret.XP", "0.2", None),
    ("Senses", "Disarm.XP", "0.4", None),
]


THIEVING = [   # data\Thieving.ini (thieving.py): (section, key, value, what it means)
    ("Pickpocket", "Level", "1", "A pocket's Stealth level (a trade's own below); in 100 at your level, and each level"),
    ("Pickpocket", "Chance", "55", "either way; less if they're looking at you; how far below it you may still try"),
    ("Pickpocket", "Chance.Per.Level", "6", None),
    ("Pickpocket", "Watched", "30", None),
    ("Pickpocket", "Reach", "8", None),
    ("Pickpocket", "Gold", "2-6", "What's in a pocket (a trade's own below); Stealth xp (times the root of the level)"),
    ("Pickpocket", "XP", "0.25", None),
    ("Pickpocket", "Again.Minutes", "10", "Minutes before the same pocket again; a shopkeeper who caught you won't serve"),
    ("Pickpocket", "Caught.Minutes", "15", "you this long; the guard who comes: who, levels above yours, seconds it hunts"),
    ("Pickpocket", "Guard", "Guard", None),
    ("Pickpocket", "Guard.Levels.Above", "2", None),
    ("Pickpocket", "Guard.Lasts", "120", None),
    ("Pickpocket.Resident", "Level", "1", "A trade (the kind, or the word in its Id: Galaith_Baker_336): Level, Gold, Loot"),
    ("Pickpocket.Resident", "Gold", "1-5", "(Item,amount,percent ...)"),
    ("Pickpocket.Resident", "Loot", "Bread,1,15 Egg,1,10", None),
    ("Pickpocket.Baker", "Level", "3", None), ("Pickpocket.Baker", "Gold", "3-9", None),
    ("Pickpocket.Baker", "Loot", "Bread,1-2,45", None),
    ("Pickpocket.Butcher", "Level", "4", None), ("Pickpocket.Butcher", "Gold", "3-10", None),
    ("Pickpocket.Butcher", "Loot", "Raw_Meat,1,35 Cowhide,1,10", None),
    ("Pickpocket.Fishmonger", "Level", "3", None), ("Pickpocket.Fishmonger", "Gold", "2-8", None),
    ("Pickpocket.Fishmonger", "Loot", "Raw_Herring,1,40", None),
    ("Pickpocket.Greengrocer", "Level", "2", None), ("Pickpocket.Greengrocer", "Gold", "2-7", None),
    ("Pickpocket.Greengrocer", "Loot", "Cabbage,1,30 Carrot,1-2,30", None),
    ("Pickpocket.Barkeep", "Level", "5", None), ("Pickpocket.Barkeep", "Gold", "5-14", None),
    ("Pickpocket.Barkeep", "Loot", "Ale,1,30", None),
    ("Pickpocket.Barmaid", "Level", "4", None), ("Pickpocket.Barmaid", "Gold", "3-10", None),
    ("Pickpocket.Barmaid", "Loot", "Ale,1,25", None),
    ("Pickpocket.Clerk", "Level", "6", None), ("Pickpocket.Clerk", "Gold", "6-16", None),
    ("Pickpocket.Banker", "Level", "12", None), ("Pickpocket.Banker", "Gold", "15-40", None),
    ("Pickpocket.Banker", "Loot", "Silver_Ring,1,8 Gold_Ring,1,3", None),
    ("Pickpocket.Smith", "Level", "6", None), ("Pickpocket.Smith", "Gold", "4-12", None),
    ("Pickpocket.Smith", "Loot", "Iron_Ore,1,25 Bronze_Bar,1,15", None),
    ("Pickpocket.Armourer", "Level", "8", None), ("Pickpocket.Armourer", "Gold", "6-16", None),
    ("Pickpocket.Armourer", "Loot", "Iron_Bar,1,20", None),
    ("Pickpocket.Doctor", "Level", "7", None), ("Pickpocket.Doctor", "Gold", "5-12", None),
    ("Pickpocket.Doctor", "Loot", "Minor_Healing_Draught,1,25 Empty_Vial,1,30", None),
    ("Pickpocket.Priest", "Level", "5", None), ("Pickpocket.Priest", "Gold", "1-6", None),
    ("Pickpocket.Sheriff", "Level", "15", None), ("Pickpocket.Sheriff", "Gold", "8-20", None),
    ("Pickpocket.Constable", "Level", "12", None), ("Pickpocket.Constable", "Gold", "5-14", None),
    ("Pickpocket.Guard", "Level", "14", None), ("Pickpocket.Guard", "Gold", "5-15", None),
    ("Steal", "Level.Per.Value", "0.2", "A shelf's ware: its Stealth level, 1 and this for each gold of its Value; Stealth xp"),
    ("Steal", "XP", "0.3", "(times the root of the level); minutes before the same shelves again"),
    ("Steal", "Again.Minutes", "5", None),
    ("Valuables", "Level", "4", "A house's precious things (Valuables): their Stealth level; what's in them (Item,amount,"),
    ("Valuables", "Items", "Gold_Coin(s),3-12,40 Silver_Ring,1,12 Gold_Ring,1,6 Sapphire,1,4 Bread,1,14 "
                           "Minor_Healing_Draught,1,14 Egg,1,10", "weight ...); how far off someone sees your hand;"),
    ("Valuables", "Watch.Range", "192", "minutes before the same box again; Stealth xp (times the root of the level)"),
    ("Valuables", "Again.Minutes", "30", None),
    ("Valuables", "XP", "0.4", None),
]


ISLE = "0,0,0 0,1,0 1,0,0 1,1,0 1,2,0 2,0,0 2,1,0 2,2,0 3,0,0 3,1,0 3,2,0 4,0,0 4,1,0 1,1,-1 1,1,-2 2,2,-2 2,1,1"
LOCKS = [   # data\Locks.ini (locks.py)
    ("Locks", "Level", "3", "A chest's lock (Stealth to pick it): on the mainland, underground, and up to Variance more,"),
    ("Locks", "Dungeon.Level", "8", "chest to chest; Isle.Level on these maps (the Isle: where you learn). A map line's"),
    ("Locks", "Variance", "3", "Lock= and Key=, or a kind's Entities.ini Lock=, say otherwise. Never on a chest a quest needs."),
    ("Locks", "Isle.Maps", ISLE, None),
    ("Locks", "Isle.Level", "1", None),
    ("Locks", "Reach", "4", "How far under its level you may still try to pick it; Stealth xp; Break Open (Strength) in 100"),
    ("Locks", "Pick.XP", "0.2", None),
    ("Locks", "Break.Chance", "40", None),
    ("Locks", "Sturdy.Level", "9", "Iron-bound (never broken open, only picked or keyed): a lock this high, and this many"),
    ("Locks", "Sturdy.Chance", "25", "in 100 of the rest, chest to chest (never on the Isle). A map line's Sturdy= says."),
]


def ini_keys(file, rows, header):
    path = p("data", file)
    if not os.path.exists(path):
        with open(path, "wb") as f:
            f.write(header.encode("cp1252") + b"\r\n")
    ini = Ini(path)
    for sec, key, value, note in rows:
        if ini.get(sec, key) is None:
            s = ini.section(sec, create=True)
            if note:
                s[1].append((None, "; " + note))
            s[1].append((key, value))
    ini.save(path)


def stances_ini():
    path = p("data", "Stances.ini")
    if not os.path.exists(path):
        with open(path, "wb") as f:
            f.write(b"; How you hold yourself (dsengine/stances.py). Written by dev\\migrate\\build_stealth.py: edit the "
                    b"numbers here.\r\n")
    ini = Ini(path)
    for sec, key, value, note in STANCES:
        if ini.get(sec, key) is None:
            s = ini.section(sec, create=True)
            if note:
                s[1].append((None, "; " + note))
            s[1].append((key, value))
    ini.save(path)


def config():
    """Stealth on the end of [Skills] List, and its icon: as text, so the file's own spacing is kept."""
    path = p("data", "Config.ini")
    text = open(path, "rb").read().decode("cp1252")
    lines = text.split("\r\n")
    for i, ln in enumerate(lines):
        if ln.startswith("List=") and "Homesteading" in ln and "Stealth" not in ln.split("=", 1)[1].split(","):
            lines[i] = ln.rstrip() + ",Stealth"
    if not any(ln.startswith("Icon.Stealth=") for ln in lines):
        at = next((i for i, ln in enumerate(lines) if ln.startswith("Icon.")), None)
        if at is not None:
            while at + 1 < len(lines) and lines[at + 1].startswith("Icon."):
                at += 1
            lines.insert(at + 1, "Icon.Stealth=Skill_Stealth")
    new = "\r\n".join(lines)
    if new != text:
        open(path, "wb").write(new.encode("cp1252"))


# ---------------------------------------------------------------- pictures
CLOAK = ((70, 78, 96), (98, 108, 130), (44, 50, 64))


def hood():
    """Stealth: a hooded face in shadow, two eyes catching the light."""
    img = K.new()
    K.shaded_ellipse(img, 16, 17, 11, 12, CLOAK[0], CLOAK[1], CLOAK[2])           # the hood
    K.shaded_ellipse(img, 16, 19, 6.5, 7, (24, 22, 28), (36, 34, 42), (14, 12, 16))  # the dark inside it
    for x in range(5, 28):                                                        # the cloak over the shoulders
        for y in range(25, 31):
            if abs(x - 16) < 6 + (y - 25) * 1.8:
                img[y][x] = CLOAK[0] if x < 16 else CLOAK[2]
    for x, y in ((13, 18), (14, 18), (18, 18), (19, 18)):
        img[y][x] = (236, 224, 150)
    return K.outline_img(img, (20, 18, 24))


def ring(img, col):
    for y in range(32):
        for x in range(32):
            d = math.hypot(x + 0.5 - 16, y + 0.5 - 16)
            if 13 <= d < 15:
                img[y][x] = col


def stance_none():
    img = K.new()
    ring(img, (150, 120, 80))
    for y in range(9, 24):                                                      # a figure standing easy
        for x in range(14, 18):
            img[y][x] = (210, 190, 150)
    K.shaded_ellipse(img, 16, 8, 2.6, 2.6, (230, 210, 170), (250, 236, 200), (190, 160, 120))
    return K.outline_img(img, (30, 22, 16))


def stance_fighting():
    import build_sprites as B
    img = K.new()
    ring(img, (190, 70, 50))
    B.seg(img, 9, 23, 23, 9, 2.6, (236, 240, 248), (200, 208, 220), (130, 140, 156))   # two blades crossed
    B.seg(img, 9, 9, 23, 23, 2.6, (236, 240, 248), (200, 208, 220), (130, 140, 156))
    for x, y in ((8, 24), (24, 24)):
        K.shaded_ellipse(img, x, y, 1.8, 1.8, (180, 130, 60), (220, 170, 90), (120, 80, 30))
    return K.outline_img(img, (30, 22, 16))


def stance_channelling():
    img = K.new()
    ring(img, (150, 120, 230))
    for k in range(6):                                                          # a shard star, gathered
        a = k * math.pi / 3
        for t in range(2, 10):
            K.put(img, int(16 + math.cos(a) * t), int(16 + math.sin(a) * t), (196, 172, 255))
    K.shaded_ellipse(img, 16, 16, 3, 3, (220, 210, 255), (250, 246, 255), (160, 140, 230))
    return K.outline_img(img, (30, 22, 16))


def stance_sneaking():
    img = K.new()
    ring(img, (90, 110, 120))
    for y in range(32):
        for x in range(32):
            if img[y][x] is None and math.hypot(x + 0.5 - 16, y + 0.5 - 19) < 8 and y < 22:
                img[y][x] = CLOAK[0] if x < 16 else CLOAK[2]                     # a crouched, hooded shape
    for x, y in ((14, 17), (17, 17)):
        img[y][x] = (236, 224, 150)
    return K.outline_img(img, (30, 22, 16))


def valuables():
    """A little keepsake box against the wall, its lid up: coins, a ring's glint (a house's precious things)."""
    img = K.new()
    wood, light, dark = (124, 80, 46), (164, 112, 66), (82, 52, 30)
    for y in range(20, 28):
        for x in range(9, 23):
            img[y][x] = light if y == 20 else dark if y >= 26 or x in (9, 22) else wood
    for y in range(13, 20):                                     # (the lid, up)
        for x in range(10, 22):
            img[y][x] = dark if y == 13 or x in (10, 21) else wood
    for x in range(11, 21):
        img[19][x] = (230, 190, 70) if x % 2 else (196, 150, 44)    # (the coins, heaped)
    img[18][13], img[18][14], img[18][17] = (250, 214, 100), (230, 190, 70), (250, 214, 100)
    img[18][19], img[17][19], img[18][20] = (200, 210, 224), (240, 246, 255), (160, 170, 186)   # (a silver ring)
    img[23][16] = (200, 170, 96)                                # (its clasp)
    return K.outline_img(img, (40, 26, 16))


def art():
    out = [("Interface", "Skill_Stealth", hood()), ("Interface", "Stance_None", stance_none()),
           ("Interface", "Stance_Fighting", stance_fighting()), ("Interface", "Stance_Channelling", stance_channelling()),
           ("Interface", "Stance_Sneaking", stance_sneaking()), ("Entities", "Valuables", valuables())]
    n = sum(1 for kind, name, img in out if K.save(kind, name, img))
    print("Pictures: %d written (of %d)" % (n, len(out)))


def entities():
    ents = Ini(p("data", "Entities.ini"))
    for k, v in (("Type", "StaticObject"), ("Use.Words", "Examine"), ("Solid", "1"),
                 ("Examine.Info", "A little box of somebody's precious things. Not yours.")):
        if ents.get("Valuables", k) is None:
            ents.set("Valuables", k, v)
    ents.save(p("data", "Entities.ini"))


HOUSE_TOWNS = [(-12, 11, -4, 18), (-8, 4, -6, 6)]               # (Galaith, redrawn; Mirefold: not in the plan's list)


def place_valuables():
    """In about half the houses of every settlement (not a shop: no shelves of goods), a box of precious things on a
    back-wall tile, against the wall (sneak in and Steal from it). Never twice in a house."""
    import zlib
    from build_isle import Map
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "estforlan"))
    import layout as L
    names = set()
    for spec in list(L.SETTLEMENTS.values()):
        x1, y1, x2, y2 = spec["maps"]
        names |= {"%d,%d,0" % (x, y) for x in range(x1, x2 + 1) for y in range(y1, y2 + 1)}
    for x1, y1, x2, y2 in HOUSE_TOWNS:
        names |= {"%d,%d,0" % (x, y) for x in range(x1, x2 + 1) for y in range(y1, y2 + 1)}
    names -= set(ISLE.split())
    n = 0
    for name in sorted(names):
        if not os.path.exists(p("maps", name + ".txt")):
            continue
        m = Map(name)
        taken = set()
        for ln in m.ents:
            b = ln.split("\t")
            if len(b) >= 4 and b[0] in ("NPC", "StaticObject", "MapItem"):
                try:
                    taken.add((int(float(b[2])) // 32 + 1, int(float(b[3])) // 32 + 1))
                    taken.add((int(float(b[2])) // 32 + 1, int(float(b[3])) // 32 + 2))
                except ValueError:
                    pass
            elif len(b) >= 4 and b[0] in ("Id", "Trigger"):
                taken.add((int(b[2]), int(b[3])))
        groups = {}
        for y in range(1, 22):
            for x in range(1, 26):
                t, over = m.parts(x, y)
                if over.get("Roof"):                            # (Piece.Group: the group's the house)
                    groups.setdefault(over["Roof"].rsplit(".", 1)[-1], []).append((x, y, t, over))
        changed = False
        for g, cells in sorted(groups.items()):
            if any("Shelf_Goods" in (o.get("Decor", "") + t) for _, _, t, o in cells):
                continue                                        # (a shop: its shelves are stolen from instead)
            have = {(x, y) for x, y, _, _ in cells}
            if any(ln.startswith("StaticObject\tValuables\t") and
                   (int(float(ln.split("\t")[2])) // 32 + 1, int(float(ln.split("\t")[3])) // 32 + 2) in have
                   for ln in m.ents):
                continue
            if zlib.crc32(("valuables" + name + g).encode()) % 100 >= 50:
                continue
            top = min(y for _, y, _, _ in cells)
            xs = [x for x, _, _, _ in cells]
            spots = [(x, y) for x, y, t, o in cells if y == top > 1 and "_Thin_" in t and not o.get("Decor")
                     and not o.get("Under") and min(xs) < x < max(xs) and (x, y) not in taken and
                     (x, y + 1) not in taken and (x, y + 1) in have]
            if not spots:
                continue
            x, y = spots[zlib.crc32((name + g).encode()) % len(spots)]
            m.ents.append("StaticObject\tValuables\t%d\t%d" % ((x - 1) * 32, (y - 1) * 32 - 8))
            taken.add((x, y))
            changed = True
            n += 1
        if changed:
            m.save()
    print("Valuables: %d set down in houses" % n)


def main():
    entities()
    place_valuables()
    stances_ini()
    ini_keys("Thieving.ini", THIEVING, "; The hands of a thief (dsengine/thieving.py): pockets and shops' shelves. Written by "
                                       "dev\\migrate\\build_stealth.py: edit the numbers here.")
    ini_keys("Locks.ini", LOCKS, "; Locks on chests (dsengine/locks.py). Written by dev\\migrate\\build_stealth.py: edit "
                                 "the numbers here.")
    config()
    art()
    print("Stealth and the stances: done")


if __name__ == "__main__":
    main()
