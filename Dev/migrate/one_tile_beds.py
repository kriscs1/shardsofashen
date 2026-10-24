"""Beds in one tile: a bed was two (Bed001 its head, Bed002 its foot under it). Run it once (again: nothing to do).

  python -I "Dev\\migrate\\one_tile_beds.py"

  * Bed001: the whole bed in one tile - its headboard, a pillow, the quilt and its footboard (cut from the old two
    pictures, kept in Dev\Archive\Sprites, so it looks as it did), half the length and narrower: a single bed.
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

TILES = os.path.join(ROOT, "Sprites", "Tiles")
ARCHIVE = os.path.join(ROOT, "Dev", "Archive", "Sprites")


def pictures():
    os.makedirs(ARCHIVE, exist_ok=True)
    head_src, foot_src = os.path.join(ARCHIVE, "Bed001 (head).png"), os.path.join(ARCHIVE, "Bed002 (foot).png")
    if not os.path.exists(head_src):                    # (the old two-tile pictures kept, to cut from again)
        shutil.copy(os.path.join(TILES, "Bed001.png"), head_src)
        shutil.copy(os.path.join(TILES, "Bed002.png"), foot_src)
    pygame.init()
    pygame.display.set_mode((1, 1))
    head, foot = pygame.image.load(head_src).convert_alpha(), pygame.image.load(foot_src).convert_alpha()
    bed = pygame.Surface((32, 32), pygame.SRCALPHA)
    bed.blit(head, (0, 0), (0, 0, 32, 8))               # the headboard
    bed.blit(head, (0, 8), (0, 8, 32, 6))               # the pillow, slimmer
    bed.blit(head, (0, 14), (0, 18, 32, 2))
    bed.blit(head, (0, 16), (0, 20, 32, 8))             # the quilt
    bed.blit(foot, (0, 24), (0, 24, 32, 8))             # the footboard
    body = bed.subsurface((3, 0, 29, 32)).copy()        # narrower: a single bed, not as wide as the tile
    narrow = pygame.Surface((32, 32), pygame.SRCALPHA)
    narrow.blit(pygame.transform.scale(body, (20, 32)), (6, 0))
    pygame.image.save(narrow, os.path.join(TILES, "Bed001.png"))
    from dragonsword import ini
    tiles_ini = os.path.join(ROOT, "Data", "Tiles.ini")
    for old in ("Bed002", "Bed102", "Bed201"):         # (the double bed, and the old pieces: gone)
        f = os.path.join(TILES, old + ".png")
        if os.path.exists(f):
            os.remove(f)
    drop_sections(tiles_ini, {"Bed002", "Bed102", "Bed201"})
    drop_sections(os.path.join(ROOT, "Data", "Buildables.ini"), {"Bed002"})
    colours = os.path.join(ROOT, "Dev", "Minimap Colours.txt")
    text = open(colours, "rb").read().decode("cp1252")
    text = re.sub(r"(?m)^(Bed002|Bed102|Bed201)\t[^\r\n]*\r?\n", "", text)
    open(colours, "wb").write(text.encode("cp1252"))
    print("Bed001: a single bed in one tile; the double bed and the old pieces gone")


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
    for path in glob.glob(os.path.join(ROOT, "Maps", "**", "*.txt"), recursive=True):
        name = os.path.splitext(os.path.relpath(path, os.path.join(ROOT, "Maps")))[0]
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
    pictures()
    maps()
