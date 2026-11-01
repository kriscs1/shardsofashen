"""A tent for townsfolk with nowhere to sleep. One with no home of its own goes to bed by the nearest door on its map
(npcs.py schedule_npc); one whose map has no door at all goes into the nearest shelter (Tiles.ini Shelter=1: the
canvas tent, Tent001), and a zzz rises over it while they're in. This puts a tent down for anyone who'd have none: on
open ground a few tiles from where they stand, with room to walk in front of it and round it, never on a road's
middle, under a roof or on anything placed. Tent001 gets Shelter=1 here too. Safe to run again (a map with a
shelter already is left alone).

  python -I "dev\\migrate\\houseless_tents.py"
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)
from build_isle import Map, XT, YT   # noqa: E402
import story_kit as K                # noqa: E402


def houseless(w):
    """{map: [(tile x, tile y)]} of the people who'd go to bed with no door and no shelter on their map."""
    out = {}
    for e in w.ents:
        if e.ai is None or e.hostile or e.source != "MAP" or e.z != 0 or w.data.animation_available(e.name) != 4:
            continue
        sched = w.data.npc_schedule(e.name)
        own = getattr(e.ai, "schedule", None)
        if own is not None:
            sched = "" if own.upper() in ("ALWAYS", "NONE", "") else own.capitalize()
        if sched != "Day" or getattr(e.ai, "home", None) or getattr(e.ai, "bed", None) or w.bed_of(e):
            continue
        if w.nearest_door(e) is None and w.nearest_shelter(e) is None:
            m = w.maps[e.map]
            out.setdefault(e.map, []).append((int(e.cx - m.ox) // 32 + 1, int(e.cy - m.oy) // 32 + 1))
    return out


def open_ground(w, m, x, y, taken):
    """Can a tent go at x,y: it, the cell in front and the cells round it walkable bare ground, nothing on them?"""
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1, 2):
            tx, ty = x + dx, y + dy
            if not (2 <= tx <= XT - 1 and 2 <= ty <= YT - 1) or (tx, ty) in taken:
                return False
            tile, over = m.parts(tx, ty)
            if over.get("Decor") or over.get("Roof") or over.get("Trigger") or over.get("Infront"):
                return False
            if w.data.tile_walk_data(tile).count("1") < 49 or w.data.door_kind(tile):
                return False
            if any(k in tile for k in ("Water", "Bridge", "Road", "Cobble", "Paving", "Flag", "Stairs")):
                return False
    return True


def main():
    K.section(K.TILES, "Tent001", [("Shelter", "1")])
    from dsengine import World
    w = World(ROOT)
    n = 0
    for name, people in sorted(houseless(w).items()):
        m = Map(name)
        taken = set()
        for ln in m.ents:                                   # (nothing placed under a tent)
            b = ln.split("\t")
            if len(b) >= 4:
                try:
                    taken.add((int(float(b[2])) // 32 + 1, int(float(b[3]) + 16) // 32 + 1))
                except ValueError:
                    pass
        px, py = people[0]
        spots = sorted(((x, y) for x in range(2, XT) for y in range(2, YT - 1)),
                       key=lambda c: (abs(c[0] - px) + abs(c[1] - py)))
        for x, y in spots:
            if abs(x - px) + abs(y - py) >= 2 and open_ground(w, m, x, y, taken):
                m.set(x, y, decor="Tent001")
                m.save()
                n += 1
                print("A tent on %s at %d,%d (for %d with nowhere to sleep)" % (name, x, y, len(people)))
                break
    print("Tents: %d put down" % n)


if __name__ == "__main__":
    main()
