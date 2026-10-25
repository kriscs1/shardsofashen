"""Beds a tile and a half long: the head in its tile (Bed001), the foot in the top half of the tile below (Bed002 -
its lower half open floor, to stand on by the bed). Run it again to draw them again; a foot is only added once.

  python -I "dev\\migrate\\long_beds.py"

  * sprites\\Tiles\\Bed001 / Bed002: one bed drawn 48 px long, cut in two.
  * Tiles.ini [Bed002] (its top half solid; Sleep, as the head), dev\\Minimap Colours.txt.
  * Every map: a Bed002 under each Bed001 (every bed has floor there). A bed built at home takes its foot with it
    (dsengine/homes.py: BED_FEET).
"""
import glob
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame  # noqa: E402
from dragonsword import ini  # noqa: E402
from build_isle import Map, XT, YT  # noqa: E402

TILES = os.path.join(ROOT, "sprites", "Tiles")
LONG = 48


def long_bed():
    """A single bed seen from above, 48 px long: a wooden frame with corner posts, the headboard and footboard, a
    pillow on a cream sheet, a red patchwork quilt with its top turned back."""
    s = pygame.Surface((32, LONG), pygame.SRCALPHA)
    wood, wood_lt, wood_dk = (138, 88, 48), (176, 122, 72), (84, 52, 26)
    foot = LONG - 3                                                                 # (the footboard's bottom)
    sh = pygame.Surface((32, LONG), pygame.SRCALPHA)
    pygame.draw.rect(sh, (0, 0, 0, 80), (8, 5, 20, foot - 3), border_radius=2)     # (its shadow)
    s.blit(sh, (0, 0))
    pygame.draw.rect(s, wood_dk, (6, 3, 20, foot - 3), border_radius=2)             # the frame
    pygame.draw.rect(s, wood, (7, 4, 18, foot - 5))
    pygame.draw.rect(s, (236, 228, 208), (8, 8, 16, foot - 12))                     # the sheet
    pygame.draw.rect(s, (252, 250, 244), (9, 8, 14, 6), border_radius=2)           # the pillow
    pygame.draw.line(s, (214, 206, 190), (10, 13), (21, 13))
    pygame.draw.line(s, (255, 255, 255), (10, 9), (16, 9))
    quilt = ((196, 52, 48), (150, 34, 36))                                          # the quilt, patchwork
    for qy in range(18, foot - 5, 3):
        for qx in range(8, 24, 3):
            col = quilt[((qx - 8) // 3 + (qy - 18) // 3) % 2]
            pygame.draw.rect(s, col, (qx, qy, 3, min(3, foot - 5 - qy)))
    pygame.draw.rect(s, (232, 210, 170), (8, 16, 16, 2))                          # its top, turned back
    pygame.draw.line(s, (120, 28, 30), (8, foot - 6), (23, foot - 6))
    pygame.draw.rect(s, wood_dk, (6, 1, 20, 7), border_radius=1)                   # the headboard
    pygame.draw.rect(s, wood, (7, 2, 18, 5))
    pygame.draw.line(s, wood_lt, (7, 2), (24, 2))
    pygame.draw.rect(s, wood_dk, (6, foot - 5, 20, 5), border_radius=1)            # the footboard
    pygame.draw.rect(s, wood, (7, foot - 4, 18, 3))
    pygame.draw.line(s, wood_lt, (7, foot - 4), (24, foot - 4))
    for px, py in ((5, 0), (25, 0), (5, foot - 6), (25, foot - 6)):               # corner posts, capped
        pygame.draw.rect(s, wood_dk, (px, py, 3, 6))
        pygame.draw.rect(s, wood_lt, (px, py, 3, 2))
    return s


def pictures():
    pygame.init()
    pygame.display.set_mode((1, 1))
    bed = long_bed()
    pygame.image.save(bed.subsurface((0, 0, 32, 32)).copy(), os.path.join(TILES, "Bed001.png"))
    foot = pygame.Surface((32, 32), pygame.SRCALPHA)
    foot.blit(bed.subsurface((0, 32, 32, LONG - 32)), (0, 0))
    pygame.image.save(foot, os.path.join(TILES, "Bed002.png"))
    tiles_ini = os.path.join(ROOT, "data", "Tiles.ini")
    if not ini.section("Bed002", tiles_ini):
        for k, v in (("Walkable.Data", "0" * 21 + "1" * 28), ("Show.Name", "1"), ("Use.Words", "Sleep"),
                     ("Examine.Info", ini.read("Bed001", "Examine.Info", "", tiles_ini)),
                     ("Line.of.Sight", "1"), ("Layer", "Decor"), ("Piece", "the foot of a bed")):
            ini.write("Bed002", k, v, tiles_ini)
    colours = os.path.join(ROOT, "dev", "Minimap Colours.txt")
    text = open(colours, "rb").read().decode("cp1252")
    if "\nBed002\t" not in text:
        nl = "\r\n" if "\r\n" in text else "\n"
        text = text.replace("Bed001\t148 103 81" + nl, "Bed001\t148 103 81" + nl + "Bed002\t148 103 81" + nl)
        open(colours, "wb").write(text.encode("cp1252"))
    print("Bed001 and Bed002: a bed a tile and a half long")


def maps():
    n = 0
    for path in glob.glob(os.path.join(ROOT, "maps", "*.txt")):
        name = os.path.splitext(os.path.basename(path))[0]
        if name.count(",") != 2 or "Bed001" not in open(path, "rb").read().decode("cp1252"):
            continue
        m = Map(name)
        changed = False
        for y in range(1, YT):
            for x in range(1, XT + 1):
                if m.decor(x, y) == "Bed001" and not m.decor(x, y + 1):
                    m.set(x, y + 1, decor="Bed002")
                    changed = True
                    n += 1
        if changed:
            m.save()
    print("Maps: %d beds given their foot" % n)


if __name__ == "__main__":
    pictures()
    maps()
