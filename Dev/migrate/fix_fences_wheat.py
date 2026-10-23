"""Fences with corners, and no more squares of wheat. Run it once (again: it finds nothing left to do).

  python -I "Dev\\migrate\\fix_fences_wheat.py"

  * Every fence drawn with the old plain rails and posts (Fence001/Fence002) is a joined-up Wood_Fence now: corners,
    T's and ends where they meet (dsengine/fences.py picks the pieces; homesteads join theirs up the same way). The
    homestead's Fence is a Wood_Fence; the editor's "old wooden fence" set is gone.
  * The wheat-field tile (Wheat001, and its stubble Wheat002) is gone from the game: a field of it is ploughed earth
    (Field001) with ripe wheat plants standing on it (Ripe_Wheat001-003, harvested one by one), as the Ashford
    farmlands are.
"""
import glob
import os
import random
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dragonsword import ini  # noqa: E402
from dsengine.fences import is_fence, fence_piece, OLD  # noqa: E402
from build_isle import Map, XT, YT, TW  # noqa: E402

DATA = os.path.join(ROOT, "Data")
WHEAT = ("Wheat001", "Wheat002")


def read(path):
    return open(path, "rb").read().decode("cp1252")


def write(path, text):
    with open(path, "wb") as f:
        f.write(text.encode("cp1252"))


def drop_sections(path, names):
    """The file without the [name] sections (each up to the next section)."""
    text = read(path)
    nl = "\r\n" if "\r\n" in text else "\n"
    out, skip, n = [], False, 0
    for ln in text.split(nl):
        s = ln.strip()
        if s.startswith("[") and s.endswith("]"):
            skip = s[1:-1] in names
            n += skip
        if not skip:
            out.append(ln)
    write(path, nl.join(out))
    return n


def wheat_plants(cells, rng):
    """Two ripe wheat plants a field square, one behind the other, a little out of line (as the farmlands have)."""
    cellset, out = set(cells), []
    for tx, ty in cells:
        edge = any((tx + dx, ty + dy) not in cellset for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)))
        for bx, by in ((-6, -10), (6, 0)):
            if edge and rng.random() < 0.15:
                continue
            x, y = (tx - 1) * TW + bx + rng.randint(-3, 3), (ty - 1) * TW + by + rng.randint(-2, 2)
            out.append("StaticObject\tRipe_Wheat%03d\t%d\t%d" % (rng.randint(1, 3), x, y))
    return out


def fix_maps():
    rng = random.Random(4242)
    fences = fields = 0
    for path in glob.glob(os.path.join(ROOT, "Maps", "*.txt")):
        name = os.path.basename(path)[:-4]
        if name.count(",") != 2:
            continue
        m = Map(name)
        changed = False
        fence_at = lambda x, y: 1 <= x <= XT and 1 <= y <= YT and is_fence(m.decor(x, y))
        old = [(x, y) for y in range(1, YT + 1) for x in range(1, XT + 1) if m.decor(x, y) in OLD]
        redo = {(x + dx, y + dy) for x, y in old for dx, dy in ((0, 0), (0, -1), (1, 0), (0, 1), (-1, 0))}
        for x, y in sorted(redo):
            if fence_at(x, y):
                piece = fence_piece(fence_at, x, y)
                if m.decor(x, y) != piece:
                    m.set(x, y, decor=piece)
                    fences += 1
                    changed = True
        # (pieces are worked out from the old fences' places, so they join whichever way they're set down)
        wheat = [(x, y) for y in range(1, YT + 1) for x in range(1, XT + 1) if m.tile(x, y) in WHEAT]
        if wheat:
            for x, y in wheat:
                m.set(x, y, tile="Field001")
            m.ents += wheat_plants(wheat, rng)
            fields += len(wheat)
            changed = True
        if changed:
            m.save()
    print("Fences: %d squares joined up; wheat: %d squares are a field with wheat plants" % (fences, fields))


def fix_data():
    tiles = os.path.join(DATA, "Tiles.ini")
    n = drop_sections(tiles, set(WHEAT))
    n += drop_sections(os.path.join(DATA, "TileSets.ini"), {"Fence"})
    builds = os.path.join(DATA, "Buildables.ini")
    n += drop_sections(builds, {"Fence001", "Fence002", "Wheat001"})
    if not ini.section("Wood_Fence001", builds):
        text = read(builds)
        nl = "\r\n" if "\r\n" in text else "\n"
        block = nl.join(["[Wood_Fence001]", "Kind=Decor", "Category=Walls", "Name=Fence (joins up at the corners)",
                         "Needs=Plank 1 Nails 2", "Level=2", "XP=0.06", ""])
        text = text.replace(nl + "[Door001]", nl + block + nl + "[Door001]", 1)
        write(builds, text)
    gath = os.path.join(DATA, "Gathering.ini")
    text = read(gath)
    write(gath, text.replace("Ripe_Wheat003 Wheat001", "Ripe_Wheat003"))
    colours = os.path.join(ROOT, "Dev", "Minimap Colours.txt")
    text = read(colours)
    write(colours, re.sub(r"(?m)^Wheat00[12]\t[^\r\n]*\r?\n", "", text))
    for f in [os.path.join(ROOT, "Sprites", "Tiles", w + ".png") for w in WHEAT] + \
             [os.path.join(DATA, "Scripts", "Harvest Wheat.txt")]:
        if os.path.exists(f):
            os.remove(f)
            n += 1
    print("Data: the wheat tile and the old fence set gone (%d things)" % n)


def fix_generators():
    """So the older build scripts don't make the wheat tile or the plain fences again."""
    here = os.path.dirname(os.path.abspath(__file__))
    edits = {
        "build_homestead.py": [
            ('b("Fence001", "Decor", "Walls", "Fence", "Plank 1 Nails 2", 2, 0.06)\n'
             'b("Fence002", "Decor", "Walls", "Fence (posts)", "Plank 1 Nails 2", 2, 0.06)\n',
             'b("Wood_Fence001", "Decor", "Walls", "Fence (joins up at the corners)", "Plank 1 Nails 2", 2, 0.06)\n'),
            ('b("Wheat001", "Tile", "Garden", "Wheat (harvest)", "Wheat 2", 6, 0.2)\n', '')],
        "build_content.py": [
            ('    "Wheat001": ("1" * 49, "1", "Walk here,Harvest", "Ripe golden wheat.", "1", None),\n', ''),
            ('    "Wheat002": ("1" * 49, "1", "", "Stubble. The wheat will grow again.", "1", None),\n', ''),
            ('    S["Harvest Wheat"] = pick_script("wheat", "Wheat", "Wheat002", 60, "", 0, "0", 100,\n'
             '                                     "You cut an armful of wheat...", "...and tie it into a sheaf.")\n', ''),
            ('Source="Ripe_Wheat001 Ripe_Wheat002 Ripe_Wheat003 Wheat001"', 'Source="Ripe_Wheat001 Ripe_Wheat002 Ripe_Wheat003"'),
            ('"Wheat001": "0.7", "Wheat002": "0.7", ', '')],
        "farm_tiles.py": [('    "Wheat001": wheat,\n    "Wheat002": lambda: wheat(True),\n', '')],
        "cave_tiles.py": [('    "Wheat001": wheat,\n    "Wheat002": lambda: wheat(True),\n', ''),
                          (', "Wheat001", "Wheat002"]', ']')],
    }
    n = 0
    for name, pairs in edits.items():
        path = os.path.join(here, name)
        raw = open(path, newline="").read()
        crlf = "\r\n" in raw
        s = raw.replace("\r\n", "\n")
        for a, b in pairs:
            if a in s:
                s = s.replace(a, b, 1)
                n += 1
        open(path, "w", newline="\r\n" if crlf else "\n").write(s)
    print("Generators: %d lines changed" % n)


if __name__ == "__main__":
    fix_maps()
    fix_data()
    fix_generators()
