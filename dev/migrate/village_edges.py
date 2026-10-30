"""Settlements tidied (dev\\Roadmap.md group 10):

  * One path through each: its streets one paving from end to end (its own paving where it has one, else gravel),
    where before they gave out into dirt and gravel by turns. A street is a run of path five long or more; a garden's
    path (by a fence or a hedge) and a patch of dirt are left as they are. (Galaith's quarters keep their own, and the
    Isle is left alone.)
  * Fences round some villages: a wood fence round Oakhollow and Moorcross, a palisade round Thornwick, Emberwatch and
    Wildwood, a little way out from their houses; open where a road or a path goes through (the gate), pieces joining
    (TileSets.ini Kind=Join: dsedit/world.py lay_joins, the editor's own).

Run once (a second run finds the streets one already and the fences up).

  python -I "dev\\migrate\\village_edges.py"
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "estforlan"))
sys.path.insert(0, ROOT)
from build_isle import Map, XT, YT                      # noqa: E402
import layout as L                                      # noqa: E402
from dsedit.project import Project                      # noqa: E402
from dsedit import world as WD                          # noqa: E402

PAVED = re.compile(r"(Pav|Cobble|Flag|Boardwalk)", re.I)
PATH = re.compile(r"^(Dirt|Gravel)\d{3}$")
FENCES = {"Oakhollow": "Wood_Fence001", "Moorcross": "Wood_Fence001", "Thornwick": "Palisade001",
          "Emberwatch": "Palisade001", "Wildwood": "Palisade001"}
PLAIN = re.compile(r"^(Grass|Snow|Ash|Sand|Marsh|Moss|Heath)\d{3}$")


class World:
    """The settlement's maps as one grid of world cells (load once, save what changed)."""

    def __init__(self, names):
        self.maps = {n: Map(n) for n in names if os.path.exists(os.path.join(ROOT, "maps", n + ".txt"))}
        self.dirty = set()

    def at(self, gx, gy):
        m = self.maps.get("%d,%d,0" % (gx // XT, gy // YT))
        return (m, gx - (gx // XT) * XT + 1, gy - (gy // YT) * YT + 1) if m else (None, 0, 0)

    def parts(self, gx, gy):
        m, x, y = self.at(gx, gy)
        return m.parts(x, y) if m else ("", {})

    def set(self, gx, gy, tile=None, decor=None):
        m, x, y = self.at(gx, gy)
        if m:
            m.set(x, y, tile=tile, decor=decor)
            self.dirty.add(m)

    def cells(self):
        for name in self.maps:
            mx, my = (int(v) for v in name.split(",")[:2])
            for y in range(YT):
                for x in range(XT):
                    yield mx * XT + x, my * YT + y

    def save(self):
        for m in self.dirty:
            m.save()


def one_path(w):
    tiles = {c: w.parts(*c) for c in w.cells()}
    paved = {}
    for c, (t, over) in tiles.items():
        if PAVED.search(t):
            paved[t] = paved.get(t, 0) + 1
    street = max(paved, key=paved.get) if paved and max(paved.values()) >= 20 else "Gravel001"
    pathy = {c for c, (t, over) in tiles.items() if (PATH.match(t) or t == street) and not over.get("Roof")}

    def run(c, dx, dy):
        n, x, y = 1, c[0] + dx, c[1] + dy
        while (x, y) in pathy:
            n, x, y = n + 1, x + dx, y + dy
        x, y = c[0] - dx, c[1] - dy
        while (x, y) in pathy:
            n, x, y = n + 1, x - dx, y - dy
        return n

    def garden(c):
        return any(re.match(r"(Fence|Wood_Fence|Iron_Fence|Hedge|Palisade)", tiles.get((c[0] + dx, c[1] + dy),
                                                                                      ("", {}))[1].get("Decor", ""))
                   for dx in (-1, 0, 1) for dy in (-1, 0, 1))
    n = 0
    for c in pathy:
        t = tiles[c][0]
        if t != street and (run(c, 1, 0) >= 5 or run(c, 0, 1) >= 5) and not garden(c):
            w.set(c[0], c[1], tile=street)
            n += 1
    return street, n


def fence(w, piece, project):
    """A fence a little way out round the houses, open where a path crosses it."""
    roofs = [c for c in w.cells() if w.parts(*c)[1].get("Roof")]
    if not roofs:
        return 0
    x1, y1 = min(c[0] for c in roofs) - 4, min(c[1] for c in roofs) - 4
    x2, y2 = max(c[0] for c in roofs) + 4, max(c[1] for c in roofs) + 5
    if any(w.parts(x, y)[1].get("Decor", "").startswith(("Wood_Fence", "Palisade")) for x in (x1, x2) for y in (y1, y2)):
        return 0                                               # (up already)
    ring = []
    for x in range(x1, x2 + 1):
        ring += [(x, y1), (x, y2)]
    for y in range(y1 + 1, y2):
        ring += [(x1, y), (x2, y)]
    cells = []
    for c in ring:
        t, over = w.parts(*c)
        if PLAIN.match(t) and not over.get("Roof") and not over.get("Decor", "").startswith(("Tree", "House", "Sign")):
            cells.append(c)
    get = lambda x, y: w.parts(x, y)[1].get("Decor") or None       # noqa: E731
    put = lambda x, y, name: w.set(x, y, decor=name)               # noqa: E731
    WD.lay_joins(project, piece, cells, get, put)
    return len(cells)


def main():
    project = Project(ROOT)
    for key, spec in L.SETTLEMENTS.items():
        if key == "Galaith":
            continue
        x1, y1, x2, y2 = spec["maps"]
        names = ["%d,%d,0" % (x, y) for x in range(x1, x2 + 1) for y in range(y1, y2 + 1)]
        w = World(names)
        street, n = one_path(w)
        f = fence(w, FENCES[key], project) if key in FENCES else 0
        w.save()
        print("%s: %d street tiles made %s%s" % (key, n, street, (", a fence %d long" % f) if f else ""))


if __name__ == "__main__":
    main()
