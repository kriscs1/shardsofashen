"""Each town its own look (dev\\Roadmap.md group 10): its houses' roofs and walls of the town's own kind, four in five
of them (the rest as they were, so no street's all one), the same piece of each (a roof's slope, a wall's corner):

  Northport slate and brick; the Keep shingle and stone; the Wizards' Court copper and stone; Fenwick thatch and
  plaster; Ravensgate slate and stone; Ashford clay and brick; Highwatch shingle and stone; Frosthold slate and stone;
  Wardhaven clay and stone; Oakhollow thatch and timber; Thornwick thatch and plaster; Emberwatch slate and stone;
  Moorcross shingle and stone; Wildwood and Saltmarsh thatch and timber; Dunerest clay and sandstone. Galaith by
  quarter: the nobles' slate and stone, the merchants' clay and brick, the commons' thatch and timber.

Only houses (no shop, hall or tavern: their keepers' trades), never the Isle. Safe to run again (it's chosen by place).

  python -I "dev\\migrate\\town_looks.py"
"""
import os
import re
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "estforlan"))
from build_isle import Map, YT                          # noqa: E402
import layout as L                                      # noqa: E402
from upper_floors import groups, TRADES                 # noqa: E402

ROOT = os.path.dirname(os.path.dirname(HERE))
STYLE = {"Northport": ("Slate", "Brick"), "Keep": ("Shingle", "Stone_Wall"), "Court": ("Copper", "Stone_Wall"),
         "Fenwick": ("Thatch", "Plaster"), "Ravensgate": ("Slate", "Stone_Wall"), "Ashford": ("Clay", "Brick"),
         "Highwatch": ("Shingle", "Stone_Wall"), "Frosthold": ("Slate", "Stone_Wall"), "Wardhaven": ("Clay", "Stone_Wall"),
         "Oakhollow": ("Thatch", "Timber"), "Thornwick": ("Thatch", "Plaster"), "Emberwatch": ("Slate", "Stone_Wall"),
         "Moorcross": ("Shingle", "Stone_Wall"), "Wildwood": ("Thatch", "Timber"), "Saltmarsh": ("Thatch", "Timber"),
         "Dunerest": ("Clay", "Sandstone")}
GALAITH = [(304, ("Slate", "Stone_Wall")), (346, ("Clay", "Brick")), (999, ("Thatch", "Timber"))]   # (by row: quarters)
ROOFS = "Thatch|Shingle|Slate|Clay|Copper"
WALLS = "Brick|Plaster|Sandstone|Stone_Wall|Timber"
TILES = None


def tile_names():
    global TILES
    if TILES is None:
        TILES = {f[:-4] for f in os.listdir(os.path.join(ROOT, "sprites", "Tiles")) if f.endswith(".png")}
    return TILES


def restyle(text, roof, walls):
    """A cell in roof and walls of their kind, piece for piece (where that piece exists)."""
    def r(m):
        new = "%s_Roof%s" % (roof, m.group(2))
        return "+Roof(%s." % new if new in tile_names() else m.group(0)
    text = re.sub(r"\+Roof\((%s)_Roof(\d{3})\." % ROOFS, r, text)

    def w(m):
        new = walls + m.group(2)
        return new if new in tile_names() else m.group(0)
    parts = text.split("+")
    parts[0] = re.sub(r"^(%s)((?:_Thin_[A-Za-z]+|_Window)?\d{3})$" % WALLS, w, parts[0])
    for i in range(1, len(parts)):
        if parts[i].startswith("Decor("):
            parts[i] = re.sub(r"\((%s)(_Window\d{3})\)" % WALLS, lambda m: "(%s)" % w(m), parts[i])
    return "+".join(parts)


def settlement_maps():
    out = {}
    for key, spec in L.SETTLEMENTS.items():
        x1, y1, x2, y2 = (-12, 12, -4, 18) if key == "Galaith" else spec["maps"]
        for x in range(x1, x2 + 1):
            for y in range(y1, y2 + 1):
                out["%d,%d,0" % (x, y)] = key
    return out


def main():
    n = kept = 0
    for name, key in settlement_maps().items():
        if not os.path.exists(os.path.join(ROOT, "maps", name + ".txt")):
            continue
        m = Map(name)
        mx, my = (int(v) for v in name.split(",")[:2])
        changed = False
        for grp, cells in groups(m).items():
            xs, ys = [c[0] for c in cells], [c[1] for c in cells]
            box = (min(xs) * 32 - 32, min(ys) * 32 - 32, max(xs) * 32, max(ys) * 32 + 32)
            if any(ln.startswith("NPC\t") and any(t in ln for t in TRADES) and
                   box[0] <= float(ln.split("\t")[2]) <= box[2] and box[1] <= float(ln.split("\t")[3]) + 28 <= box[3]
                   for ln in m.ents):
                continue
            if zlib.crc32(("look:%s:%s" % (name, min(cells))).encode()) % 5 == 0:
                kept += 1
                continue                                        # (one in five: as it was)
            if key == "Galaith":
                gy = my * YT + min(ys) - 1
                roof, walls = next(s for lim, s in GALAITH if gy <= lim)
            else:
                roof, walls = STYLE.get(key, (None, None))
            if roof is None:
                continue
            front = {(x, max(ys) + 1) for x in xs if max(ys) + 1 <= YT}
            for x, y in set(cells) | front:
                old = m.rows[y - 1][x - 1]
                new = restyle(old, roof, walls)
                if new != old:
                    m.rows[y - 1][x - 1] = new
                    changed = True
            n += 1
        if changed:
            m.save()
    print("Town looks: %d houses in their town's kind (%d left as they were)" % (n, kept))


if __name__ == "__main__":
    main()
