"""The Shifting Deep (dsengine/deep.py): an old Shard mine south of Moorcross whose tunnels rearrange themselves.

  * Its entrance, by the road south of Moorcross (15,10,0), its place Id (Deep_Entrance_Site) and the world map's
    label; its floors are made by the game, not here.
  * Pictures: the entrance (a timbered mine mouth, violet light in the dark), the stairs up and down, the Deep's
    chest, its Heart (a great crystal), the cracked wall that hides a secret room, a sprung trap's plate.
  * Sounds: Darts (a trap's), Rumble (the Deep, groaning).
  * data/Deep.ini: how many floors, rooms, chests, traps, secrets and monsters, how strong, how often it shifts, and
    what its chests and Heart hold (only what's missing is added: edit them there).

Safe to run again.

  python -I "dev\\migrate\\build_deep.py"
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import Ini, p                      # noqa: E402
import build_sounds as SND                     # noqa: E402
import sprite_kit as K                         # noqa: E402
import story_kit as SK                         # noqa: E402
from story_kit import Map, obj_line            # noqa: E402

MAKER = "build_deep.py"
ROAD, ENTRANCE, SITE = "15,10,0", (17, 5), (17, 6)
DEEP = [   # Deep.ini [Deep] (key, value, note)
    ("Floors", "3", "Floors: how deep it goes. Shift.Minutes: how often it shifts (once nobody's down there)."),
    ("Shift.Minutes", "60", None),
    ("Rooms", "6-8", "Each floor: Rooms, Chests, Secrets (rooms behind a cracked wall), Traps and Monsters (lo-hi)."),
    ("Chests", "2-3", None), ("Secrets", "1", None), ("Traps", "3-5", None), ("Monsters", "5-7", None),
    ("Level.Base", "4", "Its Shard Remnants' level on floor 1, and Level.Per.Floor more each floor down."),
    ("Level.Per.Floor", "3", None),
    ("Mimic.Chance", "12", "In 100: a chest that bites."),
    ("Loot", "Gold_Coin(s),10-30,100 Shard,2-6,60 Shard_Remnant,2-5,40 Healing_Draught,1-2,35 "
             "Invisibility_Potion,1-1,8 Fire_Bolt_Scroll,1-1,4",
     "What a chest holds (item,lo-hi,chance in 100; more the deeper), a secret room's, and the Heart's."),
    ("Secret.Loot", "Gold_Coin(s),40-80,100 Shard,8-15,100 Invisibility_Potion,1-2,40 Swap_Scroll,1-1,10 "
                    "Ice_Bolt_Scroll_II,1-1,8", None),
    ("Heart.Shards", "15-30", None),
    ("Heart.Loot", "Mega_Potion,1-2,50 Fire_Bolt_Scroll_II,1-1,15 Lightning_Scroll,1-1,10", None),
]
VIOLET, PALE = (150, 90, 220), (215, 200, 255)


def entrance():
    """A mine mouth in a mound of rock: timber props, darkness, a violet glint deep inside."""
    img = K.new()
    for y in range(6, 31):
        half = int(14 * math.sqrt(max(0.0, 1 - ((y - 31) / 25.0) ** 2)))
        for x in range(16 - half, 16 + half + 1):
            K.put(img, x, y, (112, 104, 96) if (x * 3 + y * 7) % 11 else (90, 84, 78))
    for y in range(14, 31):
        for x in range(10, 23):
            K.put(img, x, y, (14, 10, 18))
    for y in range(13, 31):                                       # (timber props, and a lintel)
        for x in (9, 10, 22, 23):
            K.put(img, x, y, (120, 82, 44) if x in (9, 22) else (96, 64, 34))
    for x in range(8, 25):
        K.put(img, x, 13, (130, 90, 50))
        K.put(img, x, 14, (100, 70, 38))
    for x, y in ((15, 24), (17, 22), (14, 27)):
        K.put(img, x, y, VIOLET)
    K.put(img, 16, 23, PALE)
    return K.outline_img(img, (30, 24, 20))


def heart():
    img = K.new()
    for i in range(24):                                           # (a great crystal, standing)
        half = int(6 * math.sin(math.pi * i / 24.0)) + 1
        y = 29 - i
        for x in range(16 - half, 16 + half + 1):
            d = abs(x - 16) / float(half)
            K.put(img, x, y, PALE if d < 0.3 else VIOLET if d < 0.8 else (90, 50, 150))
    for x in range(8, 25):
        K.put(img, x, 30, (60, 40, 90))
    return K.outline_img(img, (24, 14, 40))


def cracked():
    img = K.load("Tiles", "Cave_Wall001")
    for i in range(12):                                           # (a crack running down the stones)
        K.put(img, 12 + (i % 3) - 1 + i // 4, 8 + i, (30, 26, 24))
    for i in range(5):
        K.put(img, 16 + i, 15 + i // 2, (30, 26, 24))
    return img


def sprung():
    img = K.load("Tiles", "Flagstone001")
    for y in range(10, 22):                                       # (a plate sunk into the floor)
        for x in range(10, 22):
            K.put(img, x, y, (70, 66, 62) if (x in (10, 21) or y in (10, 21)) else (96, 92, 86))
    return img


def art():
    out = [("Entities", "Deep_Entrance", entrance()), ("Entities", "Deep_Heart", heart()),
           ("Tiles", "Cave_Wall_Cracked001", cracked()), ("Tiles", "Trap_Sprung001", sprung())]
    n = sum(1 for kind, name, img in out if K.save(kind, name, img))
    SK.copy_sprite("Entities", "Chest", "Deep_Chest")
    for src, dst in (("Stairs001", "Deep_Stairs_Up"), ("Library_Stairs001", "Deep_Stairs_Down")):
        if K.save("Entities", dst, K.load("Tiles", src)):
            n += 1
    print("Pictures: %d written" % n)


SOUNDS = {
    "Darts": lambda: SND.mix((SND.shaped(SND.noise(71, SND.n(0.08), 0.9, high=0.9), 0.001, 30), 0.5),
                             (SND.shaped(SND.noise(72, SND.n(0.08), 0.9, high=0.9), 0.001, 30, delay=0.07), 0.4),
                             (SND.shaped(SND.noise(73, SND.n(0.08), 0.9, high=0.9), 0.001, 30, delay=0.15), 0.3)),
    "Rumble": lambda: SND.mix((SND.shaped(SND.noise(74, SND.n(1.8), 0.03), 0.4, 1.5), 0.9),
                              (SND.shaped(SND.tone(45, SND.n(1.8), glide=-0.2), 0.4, 1.5), 0.5)),
}


def sounds():
    for name, fn in SOUNDS.items():
        blob = SND.wav_bytes(fn())
        path = p("sounds", name + ".wav")
        if not (os.path.exists(path) and open(path, "rb").read() == blob):
            with open(path, "wb") as fh:
                fh.write(blob)
            print("wrote sounds\\%s.wav" % name)


def data():
    ents = Ini(p("data", "Entities.ini"))
    for name, keys in (
            ("Deep_Entrance", [("Type", "StaticObject"), ("Use.Words", "Enter,Examine"), ("Solid", "1"), ("Light", "20"),
                               ("Examine.Info", "An old Shard mine's mouth, its timbers black with age. Violet "
                                                "light glints somewhere far down, never in the same place twice.")]),
            ("Deep_Stairs_Down", [("Type", "StaticObject"), ("Use.Words", "Climb Down,Examine"), ("Solid", "0"),
                                  ("Examine.Info", "Steps, down into the dark.")]),
            ("Deep_Stairs_Up", [("Type", "StaticObject"), ("Use.Words", "Climb Up,Examine"), ("Solid", "0"),
                                ("Examine.Info", "Steps, up.")]),
            ("Deep_Chest", [("Type", "StaticObject"), ("Use.Words", "Open,Examine"), ("Solid", "1"),
                            ("Examine.Info", "An old miner's chest. It's probably just a chest.")]),
            ("Deep_Heart", [("Type", "StaticObject"), ("Use.Words", "Touch,Examine"), ("Solid", "1"), ("Light", "90"),
                            ("Examine.Info", "The Deep's Heart: a great crystal, humming. The tunnels move to its "
                                             "beat.")])):
        for k, v in keys:
            ents.set(name, k, v)
    ents.save(p("data", "Entities.ini"))
    SK.copy_tile("Cave_Wall_Cracked001", "Cave_Wall001", Use_Words="Search,Examine",
                 Examine_Info="Cave wall. These stones are cracked, and a draught comes through them.")
    SK.copy_tile("Trap_Sprung001", "Flagstone001", Examine_Info="A plate sunk into the floor. It already went click.")
    SK.minimap_colour("Cave_Wall_Cracked001", (70, 64, 60))
    SK.minimap_colour("Trap_Sprung001", (120, 110, 100))
    path = p("data", "Deep.ini")
    ini = Ini(path) if os.path.exists(path) else Ini()
    if not ini.header:
        ini.header = ["; The Shifting Deep (dsengine/deep.py): an old Shard mine south of Moorcross whose floors are",
                      "; made again every time it shifts. Written by dev\\migrate\\%s: edit the numbers here." % MAKER]
    if ini.section("Deep") is None:
        s = ini.section("Deep", create=True)
        for k, v, note in DEEP:
            if note:
                s[1].append((None, "; " + note))
            s[1].append((k, v))
    for k, v, note in DEEP:
        ini.set("Deep", k, v, overwrite=False)
    ini.save(path)


def place():
    m = Map(ROAD)
    if not any("\tDeep_Entrance\t" in ln for ln in m.ents):
        m.ents.append(obj_line("StaticObject", "Deep_Entrance", ENTRANCE[0], ENTRANCE[1], "Id=Shifting_Deep_Mouth"))
        SK.place_id(m, "Deep_Entrance_Site", SITE[0], SITE[1])
        m.save()
        print("The Deep's entrance, on %s at %d,%d" % (ROAD, ENTRANCE[0], ENTRANCE[1]))
    SK.place_label("Places", "The Shifting Deep", "Deep_Entrance_Site")


def main():
    art()
    sounds()
    data()
    place()
    print("The Shifting Deep: done")


if __name__ == "__main__":
    main()
