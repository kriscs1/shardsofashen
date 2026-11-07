"""Every building's rooms on the levels just under and over the world (-1: cellars; 1: the upper floors) are under a
black roof (`Hidden_Dark001`, as the secret caves' chambers are), each building its own roof group, so from inside one
you can't see into the next one's rooms across the dark (the owner's wish). Standing in a building lifts its roof, as
a house's on the world does.

A building is a patch of cells that aren't the dark (`Black001` or nothing) joined side by side, all on one map, made
of built ground (planks, flagstones, tiles, marble, thin walls...). Caves and mines are left open: a cave runs on from
map to map, and a roof only lifts on the map you're on, so the cave over the edge would stay black. A patch with any
roof already (a secret chamber) is left as it is, so this is safe to run again.

  python -I "dev\\migrate\\build_level_roofs.py"   (then validate.py)
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import world_edit as W                           # noqa: E402

LEVELS = (-1, 1)
DARK = {"", "Black001"}
ROOF = "Hidden_Dark001"
BUILT = re.compile(r"^(Plank|Flagstone|Tile|Marble|Brick|Stone_Wall|Chapel_Stone|Fireplace|Stairs|Ladder|Trapdoor|"
                   r"Carpet|Cobble|Steeple|\w+_Thin_\w+|\w+_Upper|\w+_Wall)\d{3}$")


def patches(w):
    """Each patch of not-dark cells, as (map, [(x, y) of its cells, from 1], all on that one map?)."""
    dark = lambda c: w.cell(*c) is None or W.parts(w.cell(*c))[0] in DARK
    out, seen = [], set()
    for (mx, my), m in w.maps.items():
        for y in range(W.YT):
            for x in range(W.XT):
                c = (mx * W.XT + x, my * W.YT + y)
                if c in seen or dark(c):
                    continue
                todo, cells = [c], []
                seen.add(c)
                while todo:
                    a = todo.pop()
                    cells.append(a)
                    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        n = (a[0] + dx, a[1] + dy)
                        if n not in seen and not dark(n):
                            seen.add(n)
                            todo.append(n)
                alone = all((a[0] // W.XT, a[1] // W.YT) == (mx, my) for a in cells)
                out.append((m, [(a[0] - mx * W.XT + 1, a[1] - my * W.YT + 1) for a in cells], alone))
    return out


def main():
    roofed = left = 0
    for z in LEVELS:
        w = W.World(z)
        for m, cells, alone in patches(w):
            if not alone:
                left += 1
                continue
            texts = [m.rows[y - 1][x - 1] for x, y in cells]
            grounds = [W.parts(t)[0] for t in texts]
            if any("Roof(" in t for t in texts) or not all(BUILT.match(g) for g in grounds):
                left += 1
                continue
            used = {int(g) for row in m.rows for g in re.findall(r"Roof\([^.)]+\.(\d+)\)", "".join(row))}
            group = next(g for g in range(1, 100) if g not in used)
            for x, y in cells:
                t, over = W.parts(m.rows[y - 1][x - 1])
                over["Roof"] = "%s.%02d" % (ROOF, group)
                m.rows[y - 1][x - 1] = W.join(t, over)
            w.changed.add(m.name)
            roofed += 1
        w.save()
    print("%d buildings roofed over, %d patches left open (caves, mines, roofed already)" % (roofed, left))


if __name__ == "__main__":
    main()
