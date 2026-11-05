"""Where natural grounds meet, rounded by the game and the editor themselves (the owner's wish: things that look
natural), not by pieces laid in the maps: worked out at every corner of the grid from the four cells round it
(ground.js paintRounds, dsedit/render.py round_fills). So a lone tile is round, a staircase a slope, an inlet's end a
bay, two grounds' corners round into each other, for every pair of grounds that has it, no tiles of its own.

  * Tiles.ini Round=1 on the natural grounds (water, lakes, a pond, lava, bog, ice, sand, ash, scorched ground, snow, grass, marsh,
    dirt and gravel paths, cinder, the forest's canopy): the grounds that round into each other (streets, floors,
    walls, mountains and caves keep their own edges).
  * Every piece laid in the maps (Tiles.ini Corner.Base: build_ground_pieces.py's, and the old coasts' diagonals)
    back to the ground it's laid on, on every level. A piece put down by hand from Detail is still drawn as it is.

Safe to run again.

  python -I "dev\migrate\round_world.py"
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import world_edit as W                                   # noqa: E402
from common import Ini, p                                # noqa: E402

ROUND = re.compile(r"^(Water|Lake|Pond|Lava|Bog|Ice|Sand|Ash|Scorched|Snow|Grass|Marsh|Dirt|Gravel|Cinder|Forest)\d{3}$")


def main():
    tiles = Ini(p("data", "Tiles.ini"))
    marked = 0
    bases = {}
    for sec, items in tiles.sections:
        keys = {k: v for k, v in items if k}
        if keys.get("Corner.Base"):
            bases[sec] = keys["Corner.Base"]
        elif ROUND.match(sec) and keys.get("Retired") != "1" and keys.get("Layer", "").lower() not in ("decor", "under") \
                and keys.get("Round") != "1":
            tiles.set(sec, "Round", "1")
            marked += 1
    if marked:
        tiles.save(p("data", "Tiles.ini"))
    undone = maps = 0
    for z in sorted({lv[2] for lv in W.all_levels()}):
        w = W.World(z)
        for (mx, my), m in w.maps.items():
            for y in range(len(m.rows)):
                for x in range(len(m.rows[y])):
                    t, over = W.parts(m.rows[y][x])
                    if t in bases:
                        w.put(mx * W.XT + x, my * W.YT + y, W.join(bases[t], over))
                        undone += 1
        maps += w.save()
    print("Round=1 on %d grounds; %d pieces back to their ground, on %d maps" % (marked, undone, maps))


if __name__ == "__main__":
    main()
