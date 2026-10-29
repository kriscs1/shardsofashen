"""How tiles go together, in the data files (not in the editor's code), so the map editor lays them out by reading
them:

  * data\\TileSets.ini Kind= on every set: Stretch (corners, edges and a middle stretched over a dragged rectangle:
    a roof, the walls round a room), Rug (that, and a runner each way), Join (pieces that join their neighbours:
    a fence, a palisade, a town wall: drag a line or a rectangle, or paint freehand, and each cell takes the piece
    that joins what's round it), Shore (a coast's diagonal pieces).
  * data\\Tiles.ini Joins= on a Join set's pieces: the sides it joins (N, E, S, W; * any it's asked to: a tower; -
    none: a post on its own), from its Piece= name. Below= on one drawn two tiles tall: the tile under it (a town
    wall's battlements over its face).
  * A Join set for the town wall (City_Wall001-005: battlements over a face east-west, one tile north-south, a tower
    at the corners and ends).
  * A Shore set for each coast (Grass001 and Water002-009; <Land>001 and <Land>_Water002-009): its Land, its Water,
    and which piece goes in which corner (Corners=, and Small= where the coast steps on past it).

Safe to run again (what's there is kept).

  python -I "dev\\migrate\\tile_joins.py"
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import Ini, p                      # noqa: E402

JOINS = [   # (a Piece= name starts with this) -> the sides it joins
    ("east-west", "EW"), ("north-south", "NS"),
    ("corner: east and south", "ES"), ("corner: west and south", "SW"), ("corner: north and east", "NE"),
    ("corner: north and west", "NW"),
    ("a t: east, south and west", "ESW"), ("a t: north, east and west", "NEW"), ("a t: north, east and south", "NES"),
    ("a t: north, south and west", "NSW"), ("a crossing", "NESW"), ("a post on its own", "-"),
]
WALL = [("City_Wall001", "east-west: battlements (its face under it)", "EW", "City_Wall004"),
        ("City_Wall002", "north-south", "NS", ""),
        ("City_Wall003", "a tower (corners, ends and T's; its face under it)", "*", "City_Wall005"),
        ("City_Wall004", "the wall's face, under its battlements", "", ""),
        ("City_Wall005", "a tower's face", "", "")]
CORNERS = "NE:%s002,NW:%s005,SW:%s006,SE:%s008"
SMALL = "NE:%s003,NW:%s004,SW:%s007,SE:%s009"


def joins_of(piece):
    low = piece.lower()
    return next((j for start, j in JOINS if low.startswith(start)), None)


def main():
    sets, tiles = Ini(p("data", "TileSets.ini")), Ini(p("data", "Tiles.ini"))
    names = {s for s, _ in tiles.sections if s}
    made = 0
    if sets.section("City_Wall") is None:
        for k, v in (("Title", "town wall"), ("Columns", "3"), ("Tiles", "City_Wall003,City_Wall001,City_Wall002"),
                     ("Kind", "Join")):
            sets.set("City_Wall", k, v)
        made += 1
    for t, piece, joins, below in WALL:
        tiles.set(t, "Piece", piece, overwrite=False)
        if joins:
            tiles.set(t, "Joins", joins, overwrite=False)
        if below:
            tiles.set(t, "Below", below, overwrite=False)
    for sec, items in sets.sections:
        if not sec or sets.get(sec, "Kind"):
            continue
        members = [n.strip() for n in (sets.get(sec, "Tiles") or "").split(",") if n.strip()]
        pieces = {n: (tiles.get(n, "Piece") or "").lower() for n in members}
        cols = int(sets.get(sec, "Columns") or 1)
        if any(v.startswith("corner: east and south") for v in pieces.values()):
            kind = "Join"
            for n, v in pieces.items():
                j = joins_of(v)
                if j:
                    tiles.set(n, "Joins", j, overwrite=False)
        elif cols == 4 and any("runner" in v for v in pieces.values()):
            kind = "Rug"
        elif cols == 3 and len(members) >= 9:
            kind = "Stretch"
        else:
            kind = "Set"                                       # (just tiles that belong together)
        sets.set(sec, "Kind", kind)
        made += 1
    shores = [("Grass001", "Water%03d", "Water")]
    for t in sorted(names):
        m = re.match(r"(.+)_Water002$", t)
        if m and m.group(1) + "001" in names:
            shores.append((m.group(1) + "001", m.group(1) + "_Water%03d", m.group(1) + "_Water"))
    for land, pat, stem in shores:
        key = "Shore_" + land[:-3]
        if sets.section(key) is not None or not all(pat % k in names for k in range(2, 10)):
            continue
        for k, v in (("Title", "%s coast: diagonal pieces" % land[:-3].replace("_", " ").lower()), ("Columns", "4"),
                     ("Tiles", ",".join(pat % k for k in range(2, 10))), ("Kind", "Shore"), ("Land", land),
                     ("Water", "Water001"), ("Corners", CORNERS % ((stem,) * 4)), ("Small", SMALL % ((stem,) * 4))):
            sets.set(key, k, v)
        made += 1
    sets.save(p("data", "TileSets.ini"))
    tiles.save(p("data", "Tiles.ini"))
    print("Tile sets: %d given their kind or made" % made)


if __name__ == "__main__":
    main()
