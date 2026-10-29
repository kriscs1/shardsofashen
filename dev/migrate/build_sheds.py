"""Sheds: a roof on two posts, open all round. The posts stand at the front corners (Shed_Post001 on the left, 002 on
the right, each with a brace towards the other), placed as objects so you walk in front of them or behind; the roof
covers the floor behind them and hides as you step in under it. shed() builds one on any map.
The carpenter's shed in Ashford (2,3,0, by the main road east of the smithy) has the carpenter's bench under it.
Run it again to draw the posts again; the shed is only built once.

  python -I "dev\\migrate\\build_sheds.py"
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame  # noqa: E402
from ashen import ini  # noqa: E402
from build_isle import Map, DATA, obj_line, roof_over  # noqa: E402

OUTLINE = (34, 30, 30)
WOOD = ((168, 120, 72), (132, 92, 52), (92, 62, 34))       # light, mid, dark
STONE = ((150, 146, 140), (112, 108, 104))
POSTS = {"Shed_Post001": 1, "Shed_Post002": -1}            # (which way its brace leans: to the right, to the left)


# ---------------------------------------------------------------- the posts
def draw_post(lean):
    """A square timber post on a stone footing, a brace up from it towards the other post, its shadow on the ground."""
    s = pygame.Surface((32, 32), pygame.SRCALPHA)
    pygame.draw.ellipse(s, (0, 0, 0, 60), (12, 26, 14, 5))                     # (its shadow)
    x0 = 13
    pygame.draw.rect(s, WOOD[1], (x0, 0, 6, 27))
    pygame.draw.line(s, WOOD[0], (x0, 0), (x0, 26))                            # (light down one side)
    pygame.draw.line(s, WOOD[2], (x0 + 5, 0), (x0 + 5, 26))                    # (shade down the other)
    for y in (5, 13, 20):                                                      # (the grain)
        s.set_at((x0 + 2, y), WOOD[2])
        s.set_at((x0 + 3, y + 3), WOOD[2])
    bx = x0 + 6 if lean > 0 else x0 - 1                                        # the brace, out from its side
    for i in range(9):
        x = bx + lean * i
        pygame.draw.line(s, WOOD[1], (x, 10 - i), (x, 12 - i))
        s.set_at((x, 12 - i), WOOD[2])
    pygame.draw.rect(s, STONE[0], (x0 - 2, 25, 10, 4))                         # the footing
    pygame.draw.line(s, STONE[1], (x0 - 2, 28), (x0 + 7, 28))
    shape = pygame.mask.from_surface(s, 100)
    out = pygame.Surface((32, 32), pygame.SRCALPHA)
    sil = shape.to_surface(setcolor=OUTLINE + (255,), unsetcolor=(0, 0, 0, 0))
    for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        out.blit(sil, (dx, dy))
    out.blit(s, (0, 0))
    return out


def pictures():
    pygame.init()
    pygame.display.set_mode((1, 1))
    for name, lean in POSTS.items():
        pygame.image.save(draw_post(lean), os.path.join(ROOT, "sprites", "Tiles", name + ".png"))
    print("Drew the shed posts: %s" % ", ".join(POSTS))


def data():
    tiles, sets = os.path.join(DATA, "Tiles.ini"), os.path.join(DATA, "TileSets.ini")
    for name, lean in POSTS.items():
        for k, v in (("Walkable.Data", "1111111" * 5 + "1100011" * 2), ("Show.Name", "1"), ("Use.Words", ""),
                     ("Examine.Info", "A stout post holding up the roof of the shed."), ("Line.of.Sight", "1"),
                     ("Layer", "Decor"), ("Piece", "a shed's post, its brace to the %s" % ("right" if lean > 0 else "left"))):
            if ini.read(name, k, "", tiles) != v:
                ini.write(name, k, v, tiles)
    colours = os.path.join(ROOT, "dev", "Minimap Colours.txt")
    for name in POSTS:
        if "\n%s\t" % name not in "\n" + ini.read_text(colours):
            with open(colours, "a", encoding="cp1252", newline="\r\n") as f:
                f.write("%s\t%d %d %d\n" % ((name,) + WOOD[1]))
    if not ini.section("Shed", sets):
        for k, v in (("Title", "shed posts"), ("Columns", "2"), ("Tiles", ",".join(POSTS))):
            ini.write("Shed", k, v, sets)
    print("Tiles.ini and TileSets.ini: the shed posts")


# ---------------------------------------------------------------- building one
def shed(m, x1, y1, x2, y2, roof="Shingle", floor="Dirt001"):
    """A shed on map m: its floor x1..x2, y1..y2 (tiles), the roof over all but the front row, a post at each end of
    the front row (objects: you pass in front of them and behind)."""
    for y in range(y1, y2 + 1):
        for x in range(x1, x2 + 1):
            m.set(x, y, tile=floor, decor="", roof="")
    roof_over(m, x1, y1, x2, y2 - 1, roof)
    m.ents.append(obj_line("StaticObject", "Shed_Post001", x1, y2))
    m.ents.append(obj_line("StaticObject", "Shed_Post002", x2, y2))


def ashford():
    m = Map("2,3,0")
    if m.has_line("Id\tAshford_Carpenters_Shed"):
        print("Ashford's carpenter's shed is built already")
        return
    shed(m, 24, 13, 25, 16)
    old = [ln for ln in m.ents if ln.startswith("StaticObject\tCarpenters_Bench\t")]
    m.ents = [ln for ln in m.ents if ln not in old]
    m.ents.append(obj_line("StaticObject", "Carpenters_Bench", 25, 13))       # (under the roof, at the back)
    m.ents.append("Id\tAshford_Carpenters_Shed\t24\t14")
    m.save()
    print("Ashford: the carpenter's shed east of the smithy, the bench moved into it")


def main():
    pictures()
    data()
    ashford()


if __name__ == "__main__":
    main()
