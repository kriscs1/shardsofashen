"""The Mosquito: a marsh's own pest, as big as a sparrow and twice as rude (the owner's wish: throughout the marsh).

  * Its pictures: a striped body, long legs, a needle of a nose and glassy wings, beating in its frames (Mosquito2a-c,
    and 8a-c the other way); a 1 px dark outline (build_wolf.py's way).
  * Entities.ini: weak, fast, it sees all round and hears you coming; it flies (over the pools); it buzzes now and
    then (Calls=Buzz: build_soundscape.py). Level 2.
  * Out over the marsh: on every map of the world with marsh enough (not a settlement's), a mosquito for every
    MARSH_PER marsh tiles, MOST at most, each roaming the marsh round where it starts. The Marsh and Bog terrains
    scatter them too (build_marsh.py).

Safe to run again (they are laid out afresh, the same each time).

  python -I "dev\\migrate\\build_mosquito.py"
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "estforlan"))
from common import Ini, p, write_image          # noqa: E402
import world_edit as W                           # noqa: E402
from world_edit import XT, YT, h01              # noqa: E402

from PIL import Image, ImageDraw                 # noqa: E402

MARSH_PER, MOST = 110, 2
OUTLINE = (30, 24, 20, 255)


def marshy(t):
    return t.startswith("Marsh0") or t.startswith("Bog0")


# ================================================================== pictures
def frame(beat):
    """Facing east. beat 0, 1, 2: its wings up, level, down."""
    im = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    lift = (0, 1, 0)[beat]                                       # (it bobs as it beats)
    y = 14 + lift
    for lx, ly in ((13, y + 3), (16, y + 3), (19, y + 3)):        # (its legs, long and bent)
        d.line((lx, ly, lx - 2, ly + 5), fill=(46, 38, 34, 255))
        d.line((lx - 2, ly + 5, lx - 3, ly + 8), fill=(46, 38, 34, 255))
    for i, x in enumerate(range(9, 18)):                          # (its abdomen, striped)
        d.line((x, y, x, y + 3), fill=(90, 66, 50, 255) if i % 2 else (52, 40, 34, 255))
    d.ellipse((17, y - 1, 21, y + 3), fill=(70, 56, 46, 255))    # (its thorax)
    d.ellipse((21, y, 24, y + 3), fill=(52, 42, 36, 255))        # (its head)
    d.point((23, y + 1), fill=(170, 40, 30, 255))                 # (a red eye)
    d.line((24, y + 2, 29, y + 4), fill=(36, 30, 26, 255))       # (and that nose)
    wing = {0: [(18, y), (12, y - 9), (9, y - 7)], 1: [(18, y), (8, y - 3), (7, y - 1)],
            2: [(18, y + 1), (11, y + 7), (8, y + 6)]}[beat]
    d.polygon(wing, fill=(206, 222, 230, 170), outline=(150, 170, 180, 220))
    return outlined(im)


def outlined(im):
    """The 1 px dark outline round its silhouette (not round the glassy wing: it's see-through)."""
    a = im.getchannel("A")
    solid = a.point(lambda v: 255 if v > 200 else 0)
    out = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ring = Image.new("RGBA", im.size, OUTLINE)
    for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        out.paste(ring, (dx, dy), solid)
    out.alpha_composite(im)
    return out


def art():
    made = 0
    frames = [frame(b) for b in range(3)]
    made += write_image(p("sprites", "Entities", "Mosquito.png"), frames[0])
    for f, im in zip("abc", frames):
        made += write_image(p("sprites", "Walk", "Mosquito2%s.png" % f), im)
        made += write_image(p("sprites", "Walk", "Mosquito8%s.png" % f), im.transpose(Image.Transpose.FLIP_LEFT_RIGHT))
    return made


# ================================================================== data
def data():
    ents = Ini(p("data", "Entities.ini"))
    for k, v in (("Type", "NPC"), ("Examine.Info", "A marsh mosquito as big as a sparrow. It wants your blood, and it "
                                                   "isn't sorry."),
                 ("Hitpoints", "4"), ("Attack.Speed", "0.7"), ("Strength", "1"), ("Defence", "1"),
                 ("Aggro.Range", "150"), ("Weapon.Range", "0"), ("Movement.Speed", "2.8"), ("Aggressive", "1"),
                 ("Respawn", "60"), ("Roam.Radius", "4"), ("Chase.Radius", "7"), ("Walk.Speed", "0.9"),
                 ("Pause", "0.2-1.2"), ("Kill.Sound", "Small"), ("Attitude", "Bad"), ("Level", "2"),
                 ("Sight.Cone", "360"), ("Hearing", "1.5"), ("Layer", "Over"), ("Calls", "Buzz")):
        ents.set("Mosquito", k, v)
    ents.save(p("data", "Entities.ini"))


# ================================================================== out over the marsh
def place():
    w = W.World(0)
    added = 0
    for (mx, my), m in sorted(w.maps.items()):
        for ln in [ln for ln in m.ents if ln.startswith("NPC\tMosquito\t")]:
            w.drop(m, ln)                                       # (laid out afresh: the same each run)
        if any((W.line_id(ln) or "").endswith("_Square") for ln in m.ents):
            continue                                            # (not in a settlement)
        cells = [(x, y) for y in range(1, YT + 1) for x in range(1, XT + 1)
                 if marshy(W.parts(m.rows[y - 1][x - 1])[0]) and not W.parts(m.rows[y - 1][x - 1])[1].get("Decor")]
        n = min(MOST, len(cells) // MARSH_PER)
        cells.sort(key=lambda c: h01("mosquito", mx, my, *c))
        for x, y in cells[:n]:
            zone = "%d,%d,%d,%d" % (max(1, x - 4), max(1, y - 4), min(XT, x + 4), min(YT, y + 4))
            w.place(mx * XT + x - 1, my * YT + y - 1, "NPC", "Mosquito", "Attitude=Bad Zone=%s" % zone)
            added += 1
    return added, w.save()


def main():
    made = art()
    data()
    added, maps = place()
    print("Mosquito: %d pictures written; %d placed over the marsh, on %d maps" % (made, added, maps))


if __name__ == "__main__":
    main()
