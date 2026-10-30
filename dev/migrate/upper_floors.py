"""About half the houses in the world have more than one floor (dev\\Roadmap.md group 10): an upstairs, a cellar, or
both, each the house's own footprint.

  * Upstairs (the map above, level 1): the house's rooms again, its walls where the ground floor's are, a bed against
    the back wall, a table; a ladder up from the ground floor (Ladder001) under a hatch above it (Hatch001), lined up.
    Outside, a dormer in the roof's lower slope says so (<Roof>031, the same roof group).
  * A cellar (the map below, level -1): stone walls round a plank floor, barrels, crates and sacks; a hatch in the
    ground floor (Hatch001) over a ladder up (Ladder001).
  * Which: a house (no shopkeeper, nothing climbing already, big enough), chosen by its place so it's the same every
    run: about a third upstairs, a fifth a cellar, a tenth both. Never the Isle (left alone) nor anywhere the floor
    above or below is taken.

Run once (a house already with a ladder or hatch is left as it is).

  python -I "dev\\migrate\\upper_floors.py"   (then build_minimaps.py)
"""
import os
import re
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from build_isle import Map, XT, YT                      # noqa: E402

ROOT = os.path.dirname(os.path.dirname(HERE))
ISLE = {"0,0,0", "0,1,0", "1,0,0", "1,1,0", "1,2,0", "2,0,0", "2,1,0", "2,2,0", "3,0,0", "3,1,0", "3,2,0", "4,0,0",
        "4,1,0"}
CLIMBS = ("Ladder", "Hatch", "Stairs", "Trapdoor")
TRADES = ("Baker", "Butcher", "Fishmonger", "Greengrocer", "Barkeep", "Barmaid", "Smith", "Armourer", "Banker",
          "Clerk", "Hotelier", "Doctor", "Nurse", "Priest", "Constable", "Sheriff", "Tailor", "Cobbler", "Shopkeeper",
          "Trader", "Wizard", "Herbalist", "Archivist", "Chancellor", "Speaker", "King", "Royal_Guard", "Soldier")


def groups(m):
    out = {}
    for y in range(1, YT + 1):
        for x in range(1, XT + 1):
            g = re.search(r"\+Roof\(([^)]*)\.(\d+)\)", m.rows[y - 1][x - 1])
            if g:
                out.setdefault(g.group(2), []).append((x, y))
    return out


def blank(name):
    path = os.path.join(ROOT, "maps", name + ".txt")
    return Map(name) if os.path.exists(path) else Map(name, new=True)


def free_floor(m, cells, row, avoid=()):
    for x, y in sorted(cells):
        if y == row and (x, y) not in avoid:
            t, over = m.parts(x, y)
            if "Thin" not in t and not over.get("Decor") and not over.get("Under") and not t.startswith(CLIMBS):
                return x, y
    return None


def storey(up, cells, src, hatch, kind):
    """The house's footprint on map up: its own tiles (walls, floors) for an upstairs, stone walls for a cellar."""
    for x, y in cells:
        t = src.parts(x, y)[0]
        if kind == "cellar":
            t = re.sub(r"^[A-Za-z]+(_[A-Za-z]+)*_Thin_", "Stone_Wall_Thin_", t) if "_Thin_" in t else "Flagstone001"
        up.rows[y - 1][x - 1] = t
    top = min(y for _, y in cells)
    xs = sorted(x for x, y in cells if y == top)
    hx, hy = hatch
    up.set(hx, hy, decor="Hatch001" if kind == "upstairs" else "Ladder001")
    if kind == "upstairs":
        bx = next((x for x in xs if x != hx and (x, top + 1) in cells and (x, top + 1) != hatch), None)
        if bx is not None:
            up.set(bx, top, decor="Bed001")
            up.set(bx, top + 1, decor="Bed002")
            tx = next((x for x in reversed(xs) if x not in (bx, hx)), None)
            if tx is not None:
                up.set(tx, top, decor="Table001")
    else:
        for k, x in enumerate(x for x in xs if x != hx):
            up.set(x, top, decor=("Barrel001", "Crate001", "Sacks001")[k % 3])


def dormer(m, cells):
    """A dormer in the roof's lower slope, middle (the piece swapped, the roof group kept)."""
    for x, y in cells:
        c = m.rows[y - 1][x - 1]
        g = re.search(r"\+Roof\(([A-Za-z_]+_Roof)0(11|14)\.(\d+)\)", c)
        if g:
            m.rows[y - 1][x - 1] = c.replace(g.group(0), "+Roof(%s031.%s)" % (g.group(1), g.group(3)))
            return True
    return False


def main():
    counts = {"upstairs": 0, "cellar": 0, "both": 0, "skipped": 0}
    for f in sorted(os.listdir(os.path.join(ROOT, "maps"))):
        mm = re.match(r"^(-?\d+),(-?\d+),0\.txt$", f)
        if not mm or f[:-4] in ISLE:
            continue
        name = f[:-4]
        m = Map(name)
        gs = groups(m)
        if not gs:
            continue
        mx, my = int(mm.group(1)), int(mm.group(2))
        above, below = None, None
        changed = False
        for grp, cells in gs.items():
            if len(cells) < 12 or any(m.parts(x, y)[0].startswith(CLIMBS) or
                                      m.parts(x, y)[1].get("Decor", "").startswith(CLIMBS) for x, y in cells):
                continue
            xs, ys = [c[0] for c in cells], [c[1] for c in cells]
            box = (min(xs) * 32 - 32, min(ys) * 32 - 32, max(xs) * 32, max(ys) * 32 + 32)
            people = [ln for ln in m.ents if ln.startswith("NPC\t") and
                      box[0] <= float(ln.split("\t")[2]) <= box[2] and box[1] <= float(ln.split("\t")[3]) + 28 <= box[3]]
            if any(any(t in ln for t in TRADES) for ln in people):
                continue                                         # (a shop, a hall, a tavern: not a house)
            h = (zlib.crc32(("%s:%s" % (name, min(cells))).encode()) % 1000) / 1000.0
            kind = "upstairs" if h < 0.33 else "cellar" if h < 0.53 else "both" if h < 0.63 else ""
            if not kind:
                continue
            top = min(ys)
            ladder = free_floor(m, cells, top + 1)
            hatch = free_floor(m, cells, top + 1, avoid={ladder}) if kind == "both" else ladder
            if ladder is None or hatch is None:
                counts["skipped"] += 1
                continue
            for want, spot, z in (("upstairs", ladder, 1), ("cellar", hatch, -1)):
                if kind not in (want, "both"):
                    continue
                other_name = "%d,%d,%d" % (mx, my, z)
                other = above if z == 1 else below
                if other is None:
                    other = blank(other_name)
                    if z == 1:
                        above = other
                    else:
                        below = other
                if any(not other.rows[y - 1][x - 1].startswith("Black") for x, y in cells):
                    counts["skipped"] += 1                       # (the floor above or below is taken there)
                    continue
                storey(other, cells, m, spot, want if z == 1 else "cellar")
                m.set(spot[0], spot[1], decor="Ladder001" if z == 1 else "Hatch001")
                if z == 1:
                    dormer(m, cells)
                changed = True
            counts[kind] += 1
        if changed:
            m.save()
            for other in (above, below):
                if other is not None:
                    other.save()
    print("Houses: %(upstairs)d upstairs, %(cellar)d a cellar, %(both)d both (%(skipped)d skipped)" % counts)


if __name__ == "__main__":
    main()
