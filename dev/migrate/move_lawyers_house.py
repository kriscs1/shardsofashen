"""Edwin and Maren's house to the Isle's north-west corner, and the hobgoblins' camp back where it was (the owner's
wish, after grow_isle.py: the corner for the lawyer and the doctor, not the hobgoblins).

  * The camp: its ground as it was before grow_isle.py moved it (git: CAMP_FROM), and its things (the fire, the chest -
    Hob_Camp_Chest still - its two hobgoblins, its Id) back by the offset that took them; where it stood in the
    north-west is wild again.
  * The house: moved by whole maps, 2,1 to 0,-2, so every tile and thing in it keeps its place on its map (Edwin's
    desk, Maren's counter, their beds, the stairs): the ground floor's walls, floor and roof and its brass plate onto
    0,-2,0, and the upstairs map 2,1,1 renamed 0,-2,1 (Maren's range in it). Edwin, Maren and Noops come with it.
    Where it stood (by the chapel) is wild again. The coast west of it pushed out a little, so it isn't on the beach;
    a path from its door to the camp's old one, which joins the Isle's roads.
  * What names the house's place: Locks.ini (the Isle's maps), Music.ini and Ambient.ini, Dinner at Edwin's first
    stage and Edwin's word at the funeral (build_heir_isle.py too).

Run it once (a second run finds the house moved and stops).

  python -I "dev\\migrate\\move_lawyers_house.py"
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "estforlan"))
import world_edit as W                                   # noqa: E402
from world_edit import XT, YT                           # noqa: E402

ROOT = W.ROOT
DATA = os.path.join(ROOT, "data")
CAMP = (56, 43, 68, 54)                                 # (grow_isle.py's: the camp's box where it was)
CAMP_DX, CAMP_DY = -41, -86                             # (and how far grow_isle.py moved it)
CAMP_FROM = "844a4c2"                                   # (the commit before it moved)
OLD, NEW = (2, 1), (0, -2)                              # (the house's maps: ground floor; upstairs at z 1)
HOUSE = (11, 1, 22, 7)                                  # (its walls and roof, on its map)
DOOR = (16, 8)                                          # (the step outside its door)
FOLK = ("Maren_At_Counter", "Edwin_At_Desk", "Noops", "Isle_Bank_Notice", "Isle_Bank")


def old_rows(name):
    text = subprocess.run(["git", "show", "%s:maps/%s.txt" % (CAMP_FROM, name)], cwd=ROOT, capture_output=True,
                          check=True).stdout.decode("cp1252")
    lines = text.replace("\r", "").split("\n")
    return [[c.strip() for c in lines[y].split(":")][:XT] for y in range(YT)]


def camp_back(w):
    x1, y1, x2, y2 = CAMP
    rows = old_rows("2,2,0")
    for gx in range(x1, x2 + 1):
        for gy in range(y1, y2 + 1):
            w.put(gx, gy, rows[gy - 2 * YT][gx - 2 * XT])
    box = (x1 + CAMP_DX, y1 + CAMP_DY, x2 + CAMP_DX, y2 + CAMP_DY)
    for m, ln, c in w.lines(box):
        w.drop(m, ln)
        mx, my, _ = W.mxyz(m.name)
        w.add_line(ln, (mx, my), -CAMP_DX, -CAMP_DY)
    return {(gx, gy) for gx in range(box[0], box[2] + 1) for gy in range(box[1], box[3] + 1)}


def house(w, wild):
    """The ground floor lifted from OLD to NEW (by whole maps: the same tiles on its map), and its people."""
    dx, dy = (NEW[0] - OLD[0]) * XT, (NEW[1] - OLD[1]) * YT
    ox, oy = OLD[0] * XT - 1, OLD[1] * YT - 1
    x1, y1, x2, y2 = HOUSE
    lift = [(ox + x, oy + y) for x in range(x1, x2 + 1) for y in range(y1, y2 + 1)] + [(ox + DOOR[0], oy + DOOR[1])]
    # (the ground round its new place: open, the coast a little further off to the west)
    for gx in range(ox + x1 + dx - 8, ox + x2 + dx + 3):
        for gy in range(oy + y1 + dy - 2, oy + y2 + dy + 6):
            c = w.cell(gx, gy)
            if c is None:
                continue
            if W.watery(c) or W.parts(c)[0] == "Sand001" or (gx, gy) in wild or not W.natural(c):
                w.put(gx, gy, "Grass001")
    for c in lift:
        w.put(c[0] + dx, c[1] + dy, w.cell(*c))
    w.smooth_shores({(gx, gy) for gx in range(ox + dx - 2, ox + dx + XT) for gy in range(oy + dy - 2, oy + dy + 14)})
    for gx in range(ox + x1 + dx - 12, ox + x1 + dx - 6):         # (a beach where the land meets the sea again)
        for gy in range(oy + y1 + dy - 2, oy + y2 + dy + 6):
            c = w.cell(gx, gy)
            if c is not None and W.natural(c) and not W.watery(c) and any(
                    W.watery(w.cell(gx + i, gy + j) or "Water001") for i in (-1, 0, 1) for j in (-1, 0, 1)):
                w.put(gx, gy, "Sand001")
    m = w.maps[OLD]
    for ln in [ln for ln in m.ents if W.line_id(ln) in FOLK]:
        w.drop(m, ln)
        w.add_line(ln, OLD, dx, dy)
    w.rewild([c for c in lift if c != (ox + DOOR[0], oy + DOOR[1])], seed="lawyers")
    W.rename_level_map(W.mname(*OLD, 1), W.mname(*NEW, 1))
    return (ox + DOOR[0] + dx, oy + DOOR[1] + dy)


def coast(w):
    """The coast west of the house wandering again (bays and points a few cells across), never within 4 of its wall."""
    x0 = NEW[0] * XT + HOUSE[0] - 1                         # (the house's west wall)
    y0, y1 = NEW[1] * YT + HOUSE[1] - 5, NEW[1] * YT + HOUSE[3] + 9
    edge = set()
    for gy in range(y0, y1 + 1):
        shore = int(round(-3 + 10 * W.fbm(0, gy, 6, 2401) + 3 * W.fbm(0, gy, 2, 2402)))
        shore = min(shore, x0 - 4)
        for gx in range(0, x0 - 3):
            c = w.cell(gx, gy)
            if c is None or not W.natural(c):
                continue
            want_sea = gx < shore
            if want_sea and not W.watery(c):
                w.put(gx, gy, W.SEA)
            elif not want_sea and W.watery(c):
                w.put(gx, gy, "Grass001")
            edge.add((gx, gy))
    for gx, gy in edge:                                     # (sand where it meets the sea)
        c = w.cell(gx, gy)
        if not W.watery(c) and any(W.watery(w.cell(gx + i, gy + j) or W.SEA) for i in (-1, 0, 1) for j in (-1, 0, 1)):
            w.put(gx, gy, "Sand001")
        elif W.parts(c)[0] == "Sand001":
            w.put(gx, gy, "Grass001")
    w.smooth_shores(edge)


def path(w, door):
    """A path from the house's door to the Isle's roads (its own step isn't one)."""
    net = {(gx, gy) for gx in range(0, 125) for gy in range(-63, 63)
           if w.cell(gx, gy) is not None and W.is_road(w.cell(gx, gy)) and abs(gx - door[0]) + abs(gy - door[1]) > 4}
    return W.join_roads(w, [(door[0], door[1] + 1)], network=net)


def yard(w):
    """Open ground round the house (the wild that grew where the camp was came up as thick wood to its walls)."""
    ox, oy = NEW[0] * XT - 1, NEW[1] * YT - 1
    x1, y1, x2, y2 = HOUSE
    for x in range(x1 - 2, x2 + 3):
        for y in range(y1, y2 + 7):
            c = w.cell(ox + x, oy + y)
            if c is not None and W.parts(c)[0] == "Forest001":
                w.put(ox + x, oy + y, "Grass001")


def words():
    up_old, up_new = W.mname(*OLD, 1), W.mname(*NEW, 1)
    for f in ("Locks.ini", "Music.ini", "Ambient.ini"):
        path = os.path.join(DATA, f)
        s = W.read(path)
        t = re.sub(r"(?<![-\d,])%s(?![\d,])" % re.escape(up_old), up_new, s)
        if t != s:
            W.write(path, t)
    pairs = [("live in the brick house by the chapel.", "live in the brick house in the Isle's north-west, by the sea."),
             ("at our house, by the chapel.", "at our house, up in the north-west, by the sea.")]
    W.replace_in_files([os.path.join(DATA, "Quests.ini"), os.path.join(DATA, "Scripts", "The Funeral.txt")], pairs)
    path = os.path.join(HERE, "build_heir_isle.py")
    s = open(path, encoding="utf-8").read()
    t = s.replace('"by the chapel.",', '"in the Isle\'s north-west, by the sea.",').replace(
        "at our house, by the chapel. ", "at our house, up in the north-west, by the sea. ")
    if t != s:
        open(path, "w", encoding="utf-8", newline="").write(t)


def main():
    if os.path.exists(os.path.join(ROOT, "maps", "1,-2,1.txt")):
        print("Superseded: cut_isle_corner.py moved the house on, to 1,-2.")
        return
    if os.path.exists(os.path.join(ROOT, "maps", W.mname(*NEW, 1) + ".txt")):
        print("Edwin and Maren's house is in the north-west already.")
        return
    w = W.World(0)
    wild = camp_back(w)
    w.rewild(wild, seed="hobcamp-gone")
    door = house(w, wild)
    coast(w)
    yard(w)
    n = path(w, door)
    changed = w.save()
    words()
    print("The camp back on 2,2,0; Edwin and Maren's house on %s (its door at %s, %d path); %d maps changed" %
          (W.mname(*NEW), door, n, changed))


if __name__ == "__main__":
    main()
