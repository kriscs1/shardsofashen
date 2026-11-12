"""Galaith still burning (the owner's wish): blazes (build_blaze.py: wreckage burning, not a campfire) across the dragon's scorched field before the east gate, and along the
ramparts at the war end inside it. Each is a player's own to see go out (a map line's Gone.After, world.py visible_to),
all of them once The Royal Guard is done (GuardQuest 5): the city's own again, its guard behind its heir.

  python -I "dev\\migrate\\galaith_fires.py"

Run once (a second run finds the fires there and stops).
"""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_isle import Map, XT, YT  # noqa: E402

TW = 32
FIELD = (-77, 286, -40, 324, "Scorched", 24, "GuardQuest:5")      # (x1, y1, x2, y2, ground, how many, out after)
RAMPARTS = (-111, 270, -83, 375, ("Flagstone001", "Boardwalk001"), 16, "GuardQuest:5")
BLVD = (301, 308)                                                      # (the boulevard and its trees: kept clear)


class Atlas:
    def __init__(self):
        self.maps = {}

    def map_of(self, gx, gy):
        n = "%d,%d,0" % (gx // XT, gy // YT)
        if n not in self.maps:
            if not os.path.exists(os.path.join(os.path.dirname(__file__), "..", "..", "maps", n + ".map")):
                return None
            self.maps[n] = Map(n)
        return self.maps[n]

    def cell(self, gx, gy):
        m = self.map_of(gx, gy)
        return m.rows[gy % YT][gx % XT] if m else None


def lay(atlas, area, rng, taken):
    x1, y1, x2, y2, ground, count, out = area
    spots = []
    for _ in range(20000):
        if len(spots) >= count:
            break
        gx, gy = rng.randint(x1, x2), rng.randint(y1, y2)
        if BLVD[0] <= gy <= BLVD[1] or (gx, gy) in taken:
            continue
        c = atlas.cell(gx, gy)
        if c is None or "+" in c or not c.startswith(ground) or any(abs(gx - a) + abs(gy - b) < 6 for a, b in spots):
            continue
        spots.append((gx, gy))
        for dx, dy in [(0, 0)] + rng.sample([(1, 0), (-1, 0), (0, 1), (1, 1), (-1, 1)], rng.randint(0, 2)):   # (a blaze: 1-3)
            c = atlas.cell(gx + dx, gy + dy)
            if c is None or "+" in c or not c.startswith(ground) or (gx + dx, gy + dy) in taken or \
                    gx // XT != (gx + dx) // XT or gy // YT != (gy + dy) // YT:
                continue
            taken.add((gx + dx, gy + dy))
            atlas.map_of(gx, gy).ents.append("StaticObject\tBlaze\t%d\t%d\tGone.After=%s" % (
                ((gx + dx) % XT) * TW + rng.randint(-6, 6), max(0, ((gy + dy) % YT) * TW - 6 + rng.randint(-4, 4)), out))
    return len(spots)


def main():
    atlas = Atlas()
    for mx in range(-5, -1):
        for my in range(12, 18):
            m = atlas.map_of(mx * XT, my * YT)
            if m and any("Gone.After=GuardQuest" in ln for ln in m.ents):
                print("Galaith's fires are lit already")
                return
    taken = set()
    for m in [atlas.map_of(gx, gy) for gx in range(-120, -30, 25) for gy in range(260, 380, 21)]:
        if m is None:
            continue
        mx, my = (int(v) for v in m.name.split(",")[:2])
        for ln in m.ents:
            f = ln.split("\t")
            if f[0] in ("NPC", "StaticObject", "MapItem") and len(f) > 3:
                taken.add((mx * XT + int(float(f[2]) + 16) // TW, my * YT + int(float(f[3]) + 28) // TW))
    rng = random.Random(1666)
    a = lay(atlas, FIELD, rng, taken)
    b = lay(atlas, RAMPARTS, rng, taken)
    for m in atlas.maps.values():
        m.save()
    print("Galaith burning: %d fires on the field, %d on the ramparts" % (a, b))


if __name__ == "__main__":
    main()
