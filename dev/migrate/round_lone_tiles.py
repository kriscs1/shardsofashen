"""The lone natural tiles the rounding missed (ground.js paintRounds, dsedit/render.py round_fills):

  * Sea_Rock002 was a square picture of rocks on water, a ground of its own: now see-through decor on Water001, as
    Sea_Rock001 is (build_tiles.py draws them both), so the water under it rounds and the foam goes round the rocks.
  * Lava001 and Pond001 round into what's round them (round_world.py's ROUND).

Safe to run again.

  python -I "dev\\migrate\\round_lone_tiles.py"
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_tiles as B                                  # noqa: E402
from common import Ini, p                                # noqa: E402

ROCK = "Sea_Rock002"
ON_THE_GROUND = re.compile(rb"(?<![\w(])Sea_Rock002(?![\w)])")


def main():
    for name in ("Sea_Rock001", ROCK):
        print(("wrote " if B.write_see_through(name) else "unchanged ") + name)
    tiles = Ini(p("data", "Tiles.ini"))
    tiles.set(ROCK, "Layer", "Decor")
    rock = tiles.section(ROCK)
    rock[1] = [(k, v) for k, v in rock[1] if k not in ("Blend", "Blend.Texture", "Water")]
    for name in ("Lava001", "Pond001"):
        tiles.set(name, "Round", "1")
    tiles.save(p("data", "Tiles.ini"))
    cells = maps = 0
    for f in sorted(os.listdir(p("maps"))):
        if not f.endswith(".txt"):
            continue
        with open(p("maps", f), "rb") as fh:
            old = fh.read()
        new, n = ON_THE_GROUND.subn(b"Water001+Decor(Sea_Rock002)", old)
        if n:
            with open(p("maps", f), "wb") as fh:
                fh.write(new)
            cells += n
            maps += 1
    print("%d rocks on water, on %d maps" % (cells, maps))


if __name__ == "__main__":
    main()
