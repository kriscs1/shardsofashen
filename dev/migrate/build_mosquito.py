"""Mosquitoes: the marsh's own pest, tiny, and never alone (the owner's wish: small, and they swarm; throughout the marsh).

  * One Mosquito on the map is a swarm: the page draws Swarm= of them (Entities.ini) buzzing about its spot, each its
    own way and never still, fewer as it's hurt (render.js drawSwarm). The pictures are one tiny mosquito, a few pixels
    long, its wings beating in its frames (Mosquito2a-c, and 8a-c the other way); Mosquito.png, what the editor shows, a
    little cloud of them. Too small for an outline: the body's dark enough.
  * Entities.ini: weak, fast, it sees all round and hears you coming; it flies (over the pools); it buzzes now and
    then (Calls=Buzz: build_soundscape.py). Level 2.
  * Out over the marsh: on every map of the world with marsh enough (not a settlement's), a swarm for every
    MARSH_PER marsh tiles, MOST at most, each roaming the marsh round where it starts. The Marsh and Bog terrains
    scatter them too (build_marsh.py).

Safe to run again (they are laid out afresh, the same each time).

  python -I "dev\migrate\build_mosquito.py"
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


def marshy(t):
    return t.startswith("Marsh0") or t.startswith("Bog0")


# ================================================================== pictures
def bug(d, x, y, beat):
    """One mosquito, facing east, its middle at x, y: a few pixels of striped body, a nose, legs and a beating wing."""
    dark, brown, wing = (40, 32, 28, 255), (92, 66, 48, 255), (214, 226, 232, 190)
    d.point([(x - 2, y), (x, y)], fill=brown)                    # (its abdomen, striped)
    d.point([(x - 1, y), (x + 1, y), (x + 2, y)], fill=dark)     # (thorax, head)
    d.point((x + 3, y + 1), fill=dark)                           # (and that nose)
    d.point([(x - 1, y + 1), (x + 1, y + 1)], fill=dark)         # (its legs)
    d.point({0: [(x, y - 1), (x - 1, y - 2)], 1: [(x - 1, y - 1), (x - 2, y - 1)], 2: [(x, y + 1), (x - 1, y + 2)]}[beat],
            fill=wing)


def frame(beat):
    """One mosquito in the middle of the tile. beat 0, 1, 2: its wings up, level, down."""
    im = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    bug(ImageDraw.Draw(im), 16, 16, beat)
    return im


def cloud():
    """A little cloud of them, for the editor."""
    im = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for i, (x, y) in enumerate(((8, 10), (20, 7), (13, 15), (24, 16), (9, 22), (18, 24))):
        bug(d, x, y, i % 3)
    return im


def art():
    made = write_image(p("sprites", "Entities", "Mosquito.png"), cloud())
    for f, im in zip("abc", [frame(b) for b in range(3)]):
        made += write_image(p("sprites", "Walk", "Mosquito2%s.png" % f), im)
        made += write_image(p("sprites", "Walk", "Mosquito8%s.png" % f), im.transpose(Image.Transpose.FLIP_LEFT_RIGHT))
    return made


# ================================================================== data
def data():
    ents = Ini(p("data", "Entities.ini"))
    for k, v in (("Type", "NPC"), ("Examine.Info", "A cloud of marsh mosquitoes. They want your blood, and they "
                                                   "aren't sorry."),
                 ("Swarm", "6"), ("Hitpoints", "6"), ("Attack.Speed", "0.7"), ("Strength", "1"), ("Defence", "1"),
                 ("Aggro.Range", "150"), ("Weapon.Range", "0"), ("Movement.Speed", "2.8"), ("Aggressive", "1"),
                 ("Respawn", "60"), ("Roam.Radius", "4"), ("Chase.Radius", "7"), ("Walk.Speed", "0.9"),
                 ("Pause", "0.2-1.2"), ("Kill.Sound", "Small"), ("Attitude", "Bad"), ("Level", "2"),
                 ("Sight.Cone", "360"), ("Hearing", "1.5"), ("Layer", "Over"), ("Calls", "Buzz"),
                 ("On.Hit", "Malaria 5")):        # (build_malaria.py)
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
