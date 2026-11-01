"""Inside walls for rooms that aren't rectangles: <Wall>_Thin_<Floor>009-018 for every wall (Brick, Plaster,
Sandstone, Stone_Wall, Timber) and floor (Plank, Tile, Marble) - the four inner corners (where an L-shaped room turns,
or one wall meets another), walls both sides (a passage a tile wide) and the four dead ends (house_tiles.THIN_EDGES).
Drawn as the first eight are (house_tiles.thin_wall), each with its walk mask and its Piece= in Tiles.ini, and put in
its set in TileSets.ini after a gap row (decor_sets.THIN_MORE): the editor stretches the nine before the gap round a
rectangle, and the rest are in the set's palette to put down by hand. Safe to run again.

  python -I "dev\\migrate\\thin_wall_pieces.py"
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import house_tiles as H                         # noqa: E402
import decor_sets as D                          # noqa: E402
from common import p, write_sprite, Ini         # noqa: E402

FIRST_NEW = 9


def main():
    S = 32
    drawn = 0
    ini = Ini(p("data", "Tiles.ini"))
    for wall in H.WALL_BASES:
        for floor in H.THIN_FLOORS:
            for k, edges in enumerate(H.THIN_EDGES[FIRST_NEW - 1:], FIRST_NEW):
                name = H.thin_name(wall, floor, edges)
                image = H.thin_wall(wall, floor, edges)
                mask = [[(0, 0, 0)] * S for _ in range(S)]
                drawn += write_sprite(p("sprites", "Tiles", name + ".png"), mask + image)
                for key, v in (("Walkable.Data", H.thin_walk(edges)), ("Show.Name", "0"), ("Use.Words", ""),
                               ("Line.of.Sight", "0"), ("Piece", D.THIN_WHAT[k - 1])):
                    if ini.get(name, key) != v:
                        ini.set(name, key, v)
    ini.save(p("data", "Tiles.ini"))
    path = p("data", "TileSets.ini")
    text = open(path, "rb").read().decode("cp1252")
    out, sec, n = [], "", 0
    want = {name: ",".join(names) for name, _, _, names in D.sets() if "_Thin_" in name}
    for ln in text.split("\r\n"):
        if ln.startswith("["):
            sec = ln[1:-1]
        if ln.startswith("Tiles=") and sec in want and ln != "Tiles=" + want[sec]:
            ln = "Tiles=" + want[sec]
            n += 1
        out.append(ln)
    if n:
        open(path, "wb").write("\r\n".join(out).encode("cp1252"))
    cpath = p("dev", "Minimap Colours.txt")      # (on the minimap: the colour of its set's first piece, listed after it)
    lines = open(cpath, "rb").read().decode("cp1252").split("\r\n")
    have = {ln.split("\t")[0] for ln in lines}
    added = 0
    for wall in H.WALL_BASES:
        for floor in H.THIN_FLOORS:
            names = [H.thin_name(wall, floor, e) for e in H.THIN_EDGES]
            last = max((i for i, ln in enumerate(lines) if ln.split("\t")[0] in names), default=None)
            first = next((ln for ln in lines if ln.split("\t")[0] == names[0]), None)
            if last is None or first is None:
                continue
            more = [n + "\t" + first.split("\t", 1)[1] for n in names[FIRST_NEW - 1:] if n not in have]
            lines[last + 1:last + 1] = more
            added += len(more)
    if added:
        open(cpath, "wb").write("\r\n".join(lines).encode("cp1252"))
    print("Inside walls: %d pieces drawn, %d sets given them, %d minimap colours" % (drawn, n, added))


if __name__ == "__main__":
    main()
