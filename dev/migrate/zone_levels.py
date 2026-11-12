"""Townsfolk at home roam their house's other floors: every friendly person who starts indoors and roams a Zone with
stairs or a ladder (Tiles.ini Climb=1) in it, in the same room, gets Zone.Levels= on its map line - the levels its
Zone holds on (0,1 the room above; -1 the cellar, unless something hostile is down there). Now and then it climbs
up or down and roams there (npcs.py npc_pick_floor_goal). A pass over the built maps (the owner's hand is on them),
as coast_reshape.py is: it only adds the option. Safe to run again.

  python -I "dev\\migrate\\zone_levels.py"
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from dsedit.project import read_text_lines, write_text_lines  # noqa: E402
from dsengine import World  # noqa: E402
from dsengine.entity import NPC  # noqa: E402

H = 21


def climbs_from(w, e):
    """The levels next to e's that a climb in its Zone, in the room it starts in, leads to (none with a foe there)."""
    a = e.ai
    if (a is None or e.z != 0 or e.hostile or e.owner is not None or "ZONE=" not in a.options.upper() or a.stand or
            a.way or a.flees or w.data.animation_available(e.name) != 4):
        return set()
    spawn = a.spawn_at
    m = w.map_at(e.z, *spawn)
    if m is None or not w.roofed(e.z, *spawn):
        return set()                                    # (out in the street by day: not into someone's house)
    own = w.grid_region_at(e.z, *spawn)
    out = set()
    for n in w.neighbours(m):
        for x, y, dz in w.climb_spots(n):
            if not (a.zone.has(x, y) and w.roofed(e.z, x, y) and w.grid_region_at(e.z, x, y) == own):
                continue
            there = w.map_at(e.z + dz, x, y)
            if not any(b.type == NPC and b.alive and b.hostile and b.z == e.z + dz and w.map_at(b.z, b.x, b.y) is there
                       for b in w.ents):
                out.add(e.z + dz)
    return out


def main():
    w = World(ROOT)
    wants = {}                                          # (map, name, x, y) -> its levels
    for e in w.ents:
        if e.type != NPC:
            continue
        up = climbs_from(w, e)
        m = w.maps.get(e.map)
        if up and m is not None:
            wants[(e.map, e.name, int(e.orig_x - m.ox), int(e.orig_y - m.oy))] = ",".join(
                str(z) for z in sorted(up | {e.z}))
    n, maps = 0, 0
    for name in sorted({k[0] for k in wants}):
        path = os.path.join(ROOT, "maps", name + ".map")
        lines = read_text_lines(path)
        out = list(lines)
        for i in range(H, len(lines)):
            f = lines[i].split("\t")
            if f[0] != "NPC" or len(f) < 5:
                continue
            try:
                key = (name, f[1], int(float(f[2])), int(float(f[3])))
            except ValueError:
                continue
            levels = wants.get(key)
            if not levels:
                continue
            words = [t for t in f[4].split() if not t.startswith("Zone.Levels=")]
            new = " ".join(words + ["Zone.Levels=" + levels])
            if new != f[4]:
                f[4] = new
                out[i] = "\t".join(f)
                n += 1
        if out != lines:
            write_text_lines(path, out)
            maps += 1
    print("townsfolk who roam their house's other floors: %d (%d more on %d maps)" % (len(wants), n, maps))


if __name__ == "__main__":
    main()
