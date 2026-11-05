"""Galaith's harbour, burnt (the owner's wish): Galaith can't be reached from the sea. Its south wall stays whole, and outside
it, where the shore comes up under the wall, the old harbour lies in ruin and still burning: a charred quay, its piers
broken off, ships burnt to the waterline at their moorings, fires, wreckage.

  python -I "dev\\migrate\\galaith_harbour.py"     (then build_minimaps.py, export_web_assets.py)

Run once (a second run finds the hulls there and stops).
"""
import os
import random
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pygame  # noqa: E402
import build_world_art as A  # noqa: E402
import story_kit as K  # noqa: E402
from build_isle import Map, XT, YT  # noqa: E402

TW = 32
SPAN = (-136, -92)                                      # (the shore's columns under the wall's east half)
PIERS = ((-130, 6, None), (-116, 6, 3), (-102, 3, None))   # (column, length, the plank gone)
HULLS = ((-125, 3), (-110, 5), (-96, 2))                 # (left column, rows out from the shore)


def burnt_hulls():
    """A ship burnt to the waterline: the sunken barge's six pieces, charred, an ember or two."""
    made = []
    for v in range(1, 7):
        src = pygame.image.load(os.path.join(A.TILES_DIR, "Sunken_Barge%03d.png" % v)).convert_alpha()
        rng = random.Random("hull%d" % v)
        out = src.copy()
        for y in range(A.S):
            for x in range(A.S):
                c = src.get_at((x, y))
                if c.a < 10:
                    continue
                k = rng.uniform(0.45, 0.7)
                out.set_at((x, y), (int(c.r * (1 - k) + 16 * k), int(c.g * (1 - k) + 12 * k), int(c.b * (1 - k) + 10 * k), c.a))
        for _ in range(3):
            x, y = rng.randrange(A.S), rng.randrange(A.S)
            if out.get_at((x, y)).a > 100:
                out.set_at((x, y), rng.choice([(232, 108, 40, 255), (200, 70, 30, 255)]))
        name = "Burnt_Hull%03d" % v
        A.save(name, out)
        K.minimap_colour(name, A.average(out))
        K.section(K.TILES, name, [("Walkable.Data", "0" * 49), ("Show.Name", "0"), ("Use.Words", ""),
                                  ("Examine.Info", "A ship burnt to the waterline at its moorings. The water still steams round it."),
                                  ("Line.of.Sight", "1"), ("Layer", "Decor"), ("Foam", "0")])
        made.append(name)
    return made


class World:
    def __init__(self):
        self.maps = {}

    def map_of(self, gx, gy):
        n = "%d,%d,0" % (gx // XT, gy // YT)
        if n not in self.maps:
            self.maps[n] = Map(n)
        return self.maps[n]

    def get(self, gx, gy):
        return self.map_of(gx, gy).rows[gy % YT][gx % XT]

    def put(self, gx, gy, text):
        self.map_of(gx, gy).rows[gy % YT][gx % XT] = text

    def add(self, gx, gy, line):
        self.map_of(gx, gy).ents.append(line)


def main():
    w = World()
    if any("Burnt_Hull" in c for gx in range(*SPAN) for gy in range(380, 402) for c in [w.get(gx, gy)]):
        print("The harbour's burnt already")
        return
    pygame.init()
    pygame.display.set_mode((1, 1))
    burnt_hulls()
    rng = random.Random(1879)
    shore = {}
    for gx in range(SPAN[0], SPAN[1] + 1):
        for gy in range(380, 402):
            if w.get(gx, gy).split("+")[0] == "Water001":
                shore[gx] = gy
                break
    quay = []
    for gx, sy in shore.items():                         # (the quay: two rows of stone along the water, charred)
        for gy in (sy - 1, sy - 2):
            c = w.get(gx, gy)
            if c.split("+")[0] in ("Sand001", "Grass001"):
                r = rng.random()
                deco = "+Decor(Scorch_Mark%03d)" % rng.randint(1, 3) if r < 0.4 else \
                       "+Decor(%s)" % rng.choice(("Cellar_Crate001", "Cellar_Barrel001", "Rock001")) if r < 0.5 else ""
                w.put(gx, gy, "Flagstone001" + deco)
                if not deco:
                    quay.append((gx, gy))
    ends = []
    for px, length, gone in PIERS:                       # (the piers, broken off)
        if px not in shore:
            continue
        for k in range(length):
            gy = shore[px] + k
            if k == gone or w.get(px, gy).split("+")[0] != "Water001":
                continue
            w.put(px, gy, "Boardwalk001")
        ends.append((px, shore[px] + (gone - 1 if gone else length - 1)))
    for hx, out in HULLS:                                 # (the ships, burnt at their moorings)
        if hx not in shore:
            continue
        top = shore[hx] + out
        if all(w.get(hx + i, top + j).split("+")[0] == "Water001" and "+" not in w.get(hx + i, top + j)
               for i in range(3) for j in range(2)):
            for i in range(3):
                for j in range(2):
                    w.put(hx + i, top + j, "Water001+Decor(Burnt_Hull%03d)" % (1 + i + 3 * j))
    rng.shuffle(quay)
    for gx, gy in quay[:7] + ends:                        # (still burning)
        w.add(gx, gy, "StaticObject\tFire\t%d\t%d" % ((gx % XT) * TW, max(0, (gy % YT) * TW - 6)))
    gx = (SPAN[0] + SPAN[1]) // 2
    if gx in shore:
        w.add(gx, shore[gx] - 2, "Id\tGalaith_Harbour\t%d\t%d" % (gx % XT + 1, (shore[gx] - 2) % YT + 1))
    for m in w.maps.values():
        m.save()
    K.place_label("Places", "Galaith's Burnt Harbour", "Galaith_Harbour")
    print("Galaith's harbour: %d cells of quay, %d piers, burning" % (len(quay), len(ends)))


if __name__ == "__main__":
    main()
