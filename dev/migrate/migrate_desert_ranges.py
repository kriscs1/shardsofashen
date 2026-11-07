"""The Sunscar's mountains are red sandstone (Range_Desert, build_terrain.py), not the blue-grey of the north: every
range of plain peaks (Peak..., Mountain...) round the desert whose foot is mostly sand becomes Desert_Peak... (the
same size of peak, in the same place). A range is the peaks joined side by side; each peak's foot is the open ground
nearest it. Only the desert and its edges (maps -4..3, 16..22); a beach's few peaks elsewhere stay grey. Changes the
maps in place (the owner's edits kept). Safe to run again.

  python -I "dev\\migrate\\migrate_desert_ranges.py"
"""
import os
import re
import sys
from collections import deque

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import world_edit as W                       # noqa: E402

BOX = (-4, 16, 3, 22)                        # (the maps: mx1, my1, mx2, my2)
PLAIN = re.compile(r"^(Peak|Peak_Big|Peak_Huge|Mountain)(\d{3})$")
SANDY = ("Sand", "Dust")


def desert_peak(tile):
    kind, n = PLAIN.match(tile).groups()
    if kind == "Mountain":
        return "Desert_Peak%03d" % ((int(n) - 1) % 6 + 1)
    return "Desert_" + tile


def main():
    w = W.World(0)
    ground = {}
    for (mx, my), m in w.maps.items():
        for y in range(W.YT):
            for x in range(W.XT):
                ground[(mx * W.XT + x, my * W.YT + y)] = W.parts(m.rows[y][x])[0]
    steps = ((1, 0), (-1, 0), (0, 1), (0, -1))
    peaky = {c for c, t in ground.items() if W.PEAKY.match(t) or PLAIN.match(t)}
    foot, q = {}, deque()                                  # (each peak's foot: the open ground nearest it)
    for c, t in ground.items():
        if c in peaky or W.WATERY.match(t):
            continue
        if any((c[0] + dx, c[1] + dy) in peaky for dx, dy in steps):
            foot[c] = re.sub(r"\d{3}$", "", t)
            q.append(c)
    while q:
        c = q.popleft()
        for dx, dy in steps:
            n = (c[0] + dx, c[1] + dy)
            if n in peaky and n not in foot:
                foot[n] = foot[c]
                q.append(n)
    inbox = lambda c: BOX[0] <= c[0] // W.XT <= BOX[2] and BOX[1] <= c[1] // W.YT <= BOX[3]
    plain = {c for c, t in ground.items() if PLAIN.match(t) and inbox(c)}
    seen, swapped = set(), 0
    for start in sorted(plain):
        if start in seen:
            continue
        rng, todo = [], [start]                           # (one range: the plain peaks joined side by side)
        seen.add(start)
        while todo:
            c = todo.pop()
            rng.append(c)
            for dx, dy in steps:
                n = (c[0] + dx, c[1] + dy)
                if n in plain and n not in seen:
                    seen.add(n)
                    todo.append(n)
        sandy = sum(1 for c in rng if foot.get(c, "").startswith(SANDY))
        if sandy * 2 <= len(rng):
            continue
        for c in rng:
            w.set(c[0], c[1], tile=desert_peak(ground[c]))
            swapped += 1
    print("%d peaks made sandstone, %d maps changed" % (swapped, w.save()))


if __name__ == "__main__":
    main()
