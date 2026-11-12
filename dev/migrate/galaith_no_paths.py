"""Galaith's streets go (the owner's wish): it's all stone inside the walls, so a street of its own in cobble or marble
only draws a line on it. Every street cell inside the walls becomes the paving round it, its quarter's: its lamps and
whatever else stands on it stay. What isn't a path stays: the market square and the Fountain Court's marble, the gravel
on the two lawns, the roads and the quay outside the walls. The palace's path had poked through the Royal quarter's
north wall onto the grass: that stub goes back to grass.

Safe to run again: a second run finds no street left.

  python -I "dev\migrate\galaith_no_paths.py"   (then build_minimaps.py, validate.py)
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "estforlan"))
from build_galaith_city import city, SQUARE, SQ_W, SQ_H     # noqa: E402
from build_galaith_grounds import COURT, GROUND, in_box, quarter     # noqa: E402
from common import p                                        # noqa: E402

XT, YT = 25, 21
STREETS = ("Cobble001", "Marble_Paving001", "Dirt001")
PLAZA = (SQUARE[0] - SQ_W // 2, SQUARE[1] - SQ_H // 2, SQUARE[0] + SQ_W // 2, SQUARE[1] + SQ_H // 2)
STUB = "Marble_Paving001"                                   # (marble outside the walls: only that stub)


def is_path(gx, gy, cell):
    base = cell.split("+")[0]
    return (base in STREETS and "Roof(" not in cell and city(gx, gy) and
            not in_box((gx, gy), COURT) and not in_box((gx, gy), PLAZA))


def main(dry=False):
    total = changed = 0
    for mx in range(-13, 0):
        for my in range(9, 21):
            path = p("maps", "%d,%d,0.map" % (mx, my))
            if not os.path.exists(path):
                continue
            with open(path, "rb") as f:
                lines = f.read().decode("cp1252").split("\r\n")
            n = 0
            for y, line in enumerate(lines[:YT]):                   # (the 21 rows of cells come first)
                cells = line.split(":")
                for x, cell in enumerate(cells):
                    gx, gy = mx * XT + x, my * YT + y
                    stub = cell.split("+")[0] == STUB and not city(gx, gy)
                    if stub or is_path(gx, gy, cell):
                        rest = cell.split("+", 1)
                        rest[0] = "Grass001" if stub else GROUND[quarter((gx, gy))]
                        cells[x] = "+".join(rest)
                        n += 1
                lines[y] = ":".join(cells)
            if n:
                total += n
                changed += 1
                if not dry:
                    with open(path, "wb") as f:
                        f.write("\r\n".join(lines).encode("cp1252"))
    print("%d street cells paved over, on %d maps" % (total, changed))


if __name__ == "__main__":
    main(dry="--dry" in sys.argv)
