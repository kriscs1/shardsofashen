"""(Done, and since undone in part: dev\\migrate\\long_beds.py gives beds a foot again (Bed002). Don't run this again.)

Beds in one tile: a bed was two (Bed001 its head, Bed002 its foot under it). Run it once (again: nothing to do).

  python -I "dev\\migrate\\one_tile_beds.py"

  * Bed001: a single bed in one tile, drawn here: a wooden frame with corner posts, headboard and footboard, a
    pillow, a red patchwork quilt turned back at the top. (The old two-tile pictures are kept in dev\\Archive\\Sprites.)
  * The double bed (Bed002) and the old pieces (Bed102, Bed201) are gone: their pictures, Tiles.ini, Buildables.ini.
  * Every map: a Bed002 under a Bed001 (the old foot) is taken away; any other old piece is a Bed001.
"""
import glob
import os
import re
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame  # noqa: E402
from build_isle import Map, XT, YT  # noqa: E402

TILES = os.path.join(ROOT, "sprites", "Tiles")
ARCHIVE = os.path.join(ROOT, "dev", "Archive", "Sprites")


def pictures():
    os.makedirs(ARCHIVE, exist_ok=True)
    head_src, foot_src = os.path.join(ARCHIVE, "Bed001 (head).png"), os.path.join(ARCHIVE, "Bed002 (foot).png")
    if not os.path.exists(head_src):                    # (the old two-tile pictures kept, to cut from again)
        shutil.copy(os.path.join(TILES, "Bed001.png"), head_src)
        shutil.copy(os.path.join(TILES, "Bed002.png"), foot_src)
    pygame.init()
    pygame.display.set_mode((1, 1))
    pygame.image.save(single_bed(), os.path.join(TILES, "Bed001.png"))
    from dragonsword import ini
    tiles_ini = os.path.join(ROOT, "data", "Tiles.ini")
    for old in ("Bed002", "Bed102", "Bed201"):         # (the double bed, and the old pieces: gone)
        f = os.path.join(TILES, old + ".png")
        if os.path.exists(f):
            os.remove(f)
    drop_sections(tiles_ini, {"Bed002", "Bed102", "Bed201"})
    drop_sections(os.path.join(ROOT, "data", "Buildables.ini"), {"Bed002"})
    colours = os.path.join(ROOT, "dev", "Minimap Colours.txt")
    text = open(colours, "rb").read().decode("cp1252")
    text = re.sub(r"(?m)^(Bed002|Bed102|Bed201)\t[^\r\n]*\r?\n", "", text)
    open(colours, "wb").write(text.encode("cp1252"))
    print("Bed001: a single bed in one tile; the double bed and the old pieces gone")


def single_bed():
    """A single bed seen from above, in one tile: a wooden frame with corner posts, the headboard and footboard, a
    pillow on a cream sheet, a red patchwork quilt with its top turned back."""
    s = pygame.Surface((32, 32), pygame.SRCALPHA)
    wood, wood_lt, wood_dk = (138, 88, 48), (176, 122, 72), (84, 52, 26)
    sh = pygame.Surface((32, 32), pygame.SRCALPHA)
    pygame.draw.rect(sh, (0, 0, 0, 80), (8, 5, 20, 26), border_radius=2)          # (its shadow)
    s.blit(sh, (0, 0))
    pygame.draw.rect(s, wood_dk, (6, 3, 20, 27), border_radius=2)                  # the frame
    pygame.draw.rect(s, wood, (7, 4, 18, 25))
    pygame.draw.rect(s, (236, 228, 208), (8, 8, 16, 18))                          # the sheet
    pygame.draw.rect(s, (252, 250, 244), (9, 8, 14, 5), border_radius=2)          # the pillow
    pygame.draw.line(s, (214, 206, 190), (10, 12), (21, 12))
    pygame.draw.line(s, (255, 255, 255), (10, 9), (16, 9))
    quilt = ((196, 52, 48), (150, 34, 36))                                          # the quilt, patchwork
    for qy in range(16, 26, 3):
        for qx in range(8, 24, 3):
            col = quilt[((qx - 8) // 3 + (qy - 16) // 3) % 2]
            pygame.draw.rect(s, col, (qx, qy, 3, 3))
    pygame.draw.rect(s, (232, 210, 170), (8, 14, 16, 2))                          # its top, turned back
    pygame.draw.line(s, (120, 28, 30), (8, 25), (23, 25))
    pygame.draw.rect(s, wood_dk, (6, 1, 20, 7), border_radius=1)                   # the headboard
    pygame.draw.rect(s, wood, (7, 2, 18, 5))
    pygame.draw.line(s, wood_lt, (7, 2), (24, 2))
    pygame.draw.rect(s, wood_dk, (6, 26, 20, 5), border_radius=1)                  # the footboard
    pygame.draw.rect(s, wood, (7, 27, 18, 3))
    pygame.draw.line(s, wood_lt, (7, 27), (24, 27))
    for px, py in ((5, 0), (25, 0), (5, 26), (25, 26)):                            # corner posts, capped
        pygame.draw.rect(s, wood_dk, (px, py, 3, 6))
        pygame.draw.rect(s, wood_lt, (px, py, 3, 2))
    return s


def drop_sections(path, names):
    text = open(path, "rb").read().decode("cp1252")
    nl = "\r\n" if "\r\n" in text else "\n"
    out, skip = [], False
    for ln in text.split(nl):
        s = ln.strip()
        if s.startswith("[") and s.endswith("]"):
            skip = s[1:-1] in names
        if not skip:
            out.append(ln)
    open(path, "wb").write(nl.join(out).encode("cp1252"))


def maps():
    n = 0
    for path in glob.glob(os.path.join(ROOT, "maps", "**", "*.txt"), recursive=True):
        name = os.path.splitext(os.path.relpath(path, os.path.join(ROOT, "maps")))[0]
        if name.count(",") != 2 or os.sep in name:
            continue
        text = open(path, "rb").read().decode("cp1252")
        if "Bed002" not in text:
            continue
        m = Map(name)
        changed = False
        for y in range(1, YT):
            for x in range(1, XT + 1):
                if m.decor(x, y) == "Bed001" and m.decor(x, y + 1) == "Bed002":
                    m.set(x, y + 1, decor="")
                    changed = True
                    n += 1
                elif m.decor(x, y) in ("Bed002", "Bed102", "Bed201"):     # (a piece of an old bed: a bed now)
                    m.set(x, y, decor="Bed001")
                    changed = True
                    n += 1
        if changed:
            m.save()
    print("Maps: %d beds' old foot taken away" % n)


if __name__ == "__main__":
    sys.exit("Superseded by long_beds.py: running this would take the beds' feet away.")
    pictures()
    maps()
