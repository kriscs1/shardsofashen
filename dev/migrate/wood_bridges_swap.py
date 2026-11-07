"""Every wooden jetty, pier and plank bridge on the world (Plank001 laid out over water, in the open) becomes the
Wood_Bridge set (build_wood_bridge.py): each piece joined to the bridge's own pieces and to the land at its end (so the
landward end is open), railed on every other side. Run once (a second run finds no plank piers).

  python -I "dev\migrate\wood_bridges_swap.py"
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import world_edit as W                                              # noqa: E402
from build_wood_bridge import name_of                               # noqa: E402

DIRS = (("N", 0, -1), ("E", 1, 0), ("S", 0, 1), ("W", -1, 0))


def piers(w):
    cells = set()
    for (mx, my), m in w.maps.items():
        for y, row in enumerate(m.rows):
            for x, c in enumerate(row):
                t, o = W.parts(c)
                if t == "Plank001" and not o.get("Roof") and not o.get("Under"):
                    cells.add((mx * W.XT + x, my * W.YT + y))
    seen, out = set(), []
    for c in cells:
        if c in seen:
            continue
        st, comp = [c], []
        seen.add(c)
        while st:
            a = st.pop()
            comp.append(a)
            for _, dx, dy in DIRS:
                b = (a[0] + dx, a[1] + dy)
                if b in cells and b not in seen:
                    seen.add(b)
                    st.append(b)
        wet = sum(1 for a in comp if any(w.cell(a[0] + dx, a[1] + dy) and W.watery(w.cell(a[0] + dx, a[1] + dy))
                                         for _, dx, dy in DIRS))
        if wet:
            out.append(comp)
    return out


def main():
    w = W.World(0)
    comps = piers(w)
    n = 0
    for comp in comps:
        mine = set(comp)
        for gx, gy in comp:
            mask = ""
            for s, dx, dy in DIRS:
                b = (gx + dx, gy + dy)
                c = w.cell(*b)
                if b in mine or (c is not None and not W.watery(c)):
                    mask += s
            w.set(gx, gy, tile=name_of(mask))
            n += 1
    print("Wooden bridges: %d piers, %d tiles" % (len(comps), n))
    w.save()


if __name__ == "__main__":
    main()
