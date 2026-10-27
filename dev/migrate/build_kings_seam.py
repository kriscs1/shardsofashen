"""The King's Shard Seam: the reward the bargain was made for. Deep in Galaith's mine (-11,14,-1, open once you are
king), against its far wall, a seam of Shards grows in the rock. Only the Crown may work it: with a pickaxe, once
every Shards.ini [Shards] Galaith.Seam.Hours hours (real ones), for Galaith.Seam Shards and some Mining.

  * Shard_Seam: the picture (a dark outcrop, violet crystals jutting from it, glowing), its Entities.ini section;
  * its place on the mine's map (tile 3,11, the back of the cave; the ladder is at the other end);
  * Mine Shard_Seam: the script ($Clock and the attribute ShardSeamAt: when you last worked it);
  * Shards.ini [Shards] Galaith.Seam and Galaith.Seam.Hours (only if missing: edit them there).

Safe to run again. (If build_estforlan.py makes the mine's map again, run this after it.)

  python -I "dev\\migrate\\build_kings_seam.py"
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import Ini, p                      # noqa: E402
import sprite_kit as K                         # noqa: E402
import story_kit as SK                         # noqa: E402
from story_kit import Map, obj_line            # noqa: E402

MAKER = "build_kings_seam.py"
MINE = "-11,14,-1"
AT = (3, 11)
SHARDS = [("Galaith.Seam", "12"), ("Galaith.Seam.Hours", "20")]
PICKAXES = ("Mithril_Pickaxe", "Steel_Pickaxe", "Pickaxe", "Bronze_Pickaxe")


def seam():
    """A dark outcrop of rock against the wall, violet crystals jutting from it, their light pooling at its foot."""
    img = K.new()
    rock, dark, light = (74, 66, 78), (50, 44, 56), (98, 90, 104)
    for y in range(9, 30):                                # the outcrop: wide at its foot, rounded at the top
        half = int(4 + (y - 9) * 0.45) if y < 26 else 13
        for x in range(16 - half, 16 + half):
            c = light if x < 16 - half + 3 else dark if x > 16 + half - 4 else rock
            if (x * 5 + y * 3) % 13 == 0:
                c = K.mul(c, 0.8)                         # (pits in the rock)
            img[y][x] = c
    edge, mid, heart = (110, 60, 190), (150, 120, 245), (210, 235, 255)
    for (bx, by, h, lean) in ((11, 22, 9, -1), (15, 18, 12, 0), (19, 21, 8, 1), (22, 26, 5, 1), (9, 27, 4, -1),
                              (17, 25, 6, 0)):
        for i in range(h):                                # each crystal: a splinter, its heart pale
            x, y = bx + (lean * i) // 3, by - i
            w = 1 if i > h - 3 else 2
            for dx in range(-w + 1, w):
                K.put(img, x + dx, y, heart if dx == 0 and i < h - 1 else mid)
            K.put(img, x - w, y, edge)
            K.put(img, x + w, y, K.mul(edge, 0.8))
    for x in range(6, 27):                                # the glow pooled at its foot
        if (x % 3) != 1:
            K.put(img, x, 30, K.mix((90, 60, 140), mid, 0.4))
    return K.outline_img(img, (30, 22, 40))


def script():
    rows = [(">Distance.From.Clicked.Entity", "48", "@far"),
            ("Get.Value", "ATTRIBUTE", "KingQuest", "Variable.1$"),
            (">Conditional", "$Variable.1>=1", "@crown")]
    for i, tool in enumerate(PICKAXES):                   # (any pickaxe: it wears, as on any rock)
        rows += [("@pick%d" % i,), (">Got.Item", tool, "1", "@pick%d" % (i + 1) if i + 1 < len(PICKAXES) else "@nopick"),
                 ("Goto.Line", "@dig")]
    rows += [
        ("@dig",),
        ("Get.Value", "ATTRIBUTE", "ShardSeamAt", "Variable.4$"),
        ("Get.Value", "CALCULATION", "$Clock-$Variable.4", "Variable.5$"),
        ("Get.Value", "CALCULATION", "$Shards.Galaith.Seam.Hours*3600", "Variable.6$"),
        (">Conditional", "$Variable.5>=$Variable.6", "@dim"),
        ("Show.Skill", "Mining"),
        ("Play.Animation", "Rock_Chips", "4", "Mine"),
        ("Display.Message", "Cyan", "You work your pickaxe into the glowing seam.."),
        ("Wait", "3"),
        ("Update.Attribute", "ShardSeamAt", "=$Clock"),
        ("Give.Item", "Shard", "$Shards.Galaith.Seam"),
        ("Update.Skill", "Mining", "+0.5"),
        ("Play.Sound", "Absorb"),
        ("Display.Message", "Yellow", "..and prise loose $Shards.Galaith.Seam Shards: the mountain's magic, the "
                                      "Crown's again."),
        ("End",),
        ("@dim",), ("Display.Message", "DarkRed", "The seam glows dimly: its Shards haven't grown back yet.", "Fail"),
        ("End",),
        ("@nopick",), ("Display.Message", "DarkRed", "You need a pickaxe!", "Denied"), ("End",),
        ("@crown",), ("Display.Message", "DarkRed", "The seam is the Crown's.", "Denied"), ("End",),
        ("@far",), ("Display.Message", "DarkRed", "You are too far away!", "Denied"), ("End",)]
    SK.write_script("Mine Shard_Seam", rows, MAKER)


def data():
    ents = Ini(p("data", "Entities.ini"))
    for k, v in (("Type", "StaticObject"), ("Use.Words", "Mine,Examine"), ("Solid", "1"), ("Light", "60"),
                 ("Examine.Info", "A seam of Shards in the rock, glowing violet: the mountain's magic, growing back "
                                  "as fast as it's dug.")):
        ents.set("Shard_Seam", k, v)
    ents.save(p("data", "Entities.ini"))
    shards = Ini(p("data", "Shards.ini"))
    if shards.get("Shards", "Galaith.Seam") is None:
        shards.section("Shards")[1].append((None, "; Galaith.Seam: the Shards the King's seam in Galaith's mine "
                                                  "gives, once every Galaith.Seam.Hours (real) hours."))
    for k, v in SHARDS:
        shards.set("Shards", k, v, overwrite=False)
    shards.save(p("data", "Shards.ini"))


def place():
    m = Map(MINE)
    if any("\tShard_Seam\t" in ln for ln in m.ents):
        return
    m.ents.append(obj_line("StaticObject", "Shard_Seam", AT[0], AT[1], "Id=Kings_Shard_Seam", dy=-8))
    m.save()
    print("The seam, on %s at %d,%d" % (MINE, AT[0], AT[1]))


def main():
    print(("wrote " if K.save("Entities", "Shard_Seam", seam()) else "unchanged ") + "Shard_Seam")
    data()
    place()
    script()
    print("The King's Shard Seam: done")


if __name__ == "__main__":
    main()
