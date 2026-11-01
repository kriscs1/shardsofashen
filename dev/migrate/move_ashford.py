"""Ashford moved seven maps north (the owner's wish), onto new land grown out into the sea for it: a broad peninsula
off the north coast, its shore wandering, a beach round it, meadow and copses on it.

  * Seven maps north, exactly: everything built in Ashford (its streets, houses, square, port, farms, the Green
    Dragon, the arena's keeper, the homestead yard) and everyone and everything in it keeps its place on its map;
    the maps' names change (12,5,0 is 12,-2,0 now), so zones, scripts and the levels over and under it hold.
  * Its port and the bay beside it come too, water and all, so the harbour still meets the sea.
  * Where it stood is wild again; the roads that ran to it run on to it, up the peninsula. The Wildwood's watch stone
    by the river stays where it is.
  * New maps north of the old coast (the sea, then the land on it); every name of a moved map in the scripts, the data
    (the raids, the homestead's way back, the arena's, a quest's marker, Music.ini and Ambient.ini).

Run it once (a second run finds Ashford moved and stops).

  python -I "dev\\migrate\\move_ashford.py"
"""
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "estforlan"))
import world_edit as W                                   # noqa: E402
from world_edit import XT, YT, fbm, h01                 # noqa: E402

ROOT = W.ROOT
DATA = os.path.join(ROOT, "data")
DONE = os.path.join(HERE, ".ashford_moved")
DY_MAPS = 7
DY = DY_MAPS * YT
BOX = (240, 86, 372, 145)                              # (Ashford and its farms)
PORT = (296, 56, 372, 92)                              # (its port and the bay beside it: moved whole, water and all)
STAYS = ("Watch_Stone_3", "Watch Stone 3")
NEW_MAPS = (7, -6, 16, 1)                              # (the maps that may be new: the sea, to grow land on)
CX = 300


def peninsula(gx, gy):
    """On the new land? A broad cap north of the old coast, narrowing a little to its neck; each side wandering on its
    own (headlands and bays a map or two across), its edge ragged close up."""
    if gy > 52:
        return False
    if gy < -30:
        k = (gy + 30) / 70.0
        hw = 74 * math.sqrt(max(0.0, 1 - k * k))
    else:
        hw = 74 - 0.22 * (gy + 30)
    if hw <= 0:
        return False
    left = CX - hw - 44 * (fbm(0, gy, 45, 1305) - 0.5) - 14 * (fbm(gx, gy, 14, 1306) - 0.5)
    right = CX + hw + 44 * (fbm(0, gy, 45, 1307) - 0.5) + 14 * (fbm(gx, gy, 14, 1308) - 0.5)
    return left <= gx <= right and gy >= -100 - 10 * fbm(gx, 0, 30, 1309)


def ground_for(gx, gy, coast):
    """New land's ground and what grows on it: a beach by the sea, else meadow with copses (land.scenery)."""
    import land as LAND
    if coast:
        return "Sand001", ""
    land = "wood" if fbm(gx, gy, 30, 1304) > 0.62 else "meadow"
    g, d = LAND.scenery(land, gx, gy, h01("cell", gx, gy))
    if g == "Water001":
        g, d = "Grass001", ""
    return g, d


def grow(w):
    """The sea maps made, then the peninsula's land laid on them (and on the old coast's sea and beach inside it)."""
    x1, y1, x2, y2 = NEW_MAPS
    for mx in range(x1, x2 + 1):
        for my in range(y1, y2 + 1):
            w.new_map(mx, my)
    cells = [(x, y) for x in range(x1 * XT, (x2 + 1) * XT) for y in range(y1 * YT, 60)]
    land = {c for c in cells if peninsula(*c)}
    sea_near = lambda c: any(w.cell(c[0] + dx, c[1] + dy) is not None and (c[0] + dx, c[1] + dy) not in land and  # noqa: E731
                             W.watery(w.cell(c[0] + dx, c[1] + dy)) for dx in (-2, 0, 2) for dy in (-2, 0, 2))
    made = []
    for c in sorted(land, key=lambda c: (c[1], c[0])):
        text = w.cell(*c)
        if text is None:
            continue
        t = W.parts(text)[0]
        if W.watery(text) or t == "Black001" or (t == "Sand001" and not sea_near(c)):
            g, d = ground_for(c[0], c[1], False)
            w.put(c[0], c[1], g + ("+Decor(%s)" % d if d else ""))
            made.append(c)
    for c in made:                                     # (a beach where the new land meets the sea)
        if sea_near(c) and W.natural(w.cell(*c)):
            w.put(c[0], c[1], "Sand001")
    return made


def reshape(w, keep):
    """The peninsula's shore drawn again (land where it says, the sea where it doesn't, above the old coast), never
    within a few cells of what keep holds (Ashford, its port). Returns the cells changed."""
    x1, y1, x2, _ = NEW_MAPS
    guard = {(c[0] + dx, c[1] + dy) for c in keep for dx in range(-4, 5) for dy in range(-4, 5)}
    changed = []
    for gx in range(x1 * XT, (x2 + 1) * XT):
        for gy in range(y1 * YT, 52):
            text = w.cell(gx, gy)
            if text is None or (gx, gy) in guard or not W.natural(text) or (gx >= 370 and gy >= 12):
                continue                                       # (and never Wardhaven's island)
            want = peninsula(gx, gy)
            if want and W.watery(text):
                g, d = ground_for(gx, gy, False)
                w.put(gx, gy, g + ("+Decor(%s)" % d if d else ""))
                changed.append((gx, gy))
            elif not want and not W.watery(text) and gy < 40:
                w.put(gx, gy, W.SEA)
                changed.append((gx, gy))
    for c in changed + [(c[0] + dx, c[1] + dy) for c in changed for dx in (-2, 0, 2) for dy in (-2, 0, 2)]:
        text = w.cell(*c)
        if text is None or c in guard or not W.natural(text) or W.watery(text):
            continue
        t = W.parts(text)[0]
        wet = any(w.cell(c[0] + dx, c[1] + dy) is not None and W.watery(w.cell(c[0] + dx, c[1] + dy))
                  for dx in (-2, -1, 0, 1, 2) for dy in (-2, -1, 0, 1, 2))
        if wet and t in ("Grass001", "Forest001") and c[1] < 40:
            w.put(c[0], c[1], "Sand001")
        elif not wet and t == "Sand001" and c[1] < 40:
            g, d = ground_for(c[0], c[1], False)
            w.put(c[0], c[1], g + ("+Decor(%s)" % d if d else ""))
    return changed


def moving(w):
    cells = set()
    for x in range(BOX[0], BOX[2] + 1):
        for y in range(BOX[1], BOX[3] + 1):
            if w.cell(x, y) is not None and not W.natural(w.cell(x, y)):
                cells.add((x, y))
    whole = {(x, y) for x in range(PORT[0], PORT[2] + 1) for y in range(PORT[1], PORT[3] + 1) if w.cell(x, y)}
    near = {(c[0] + dx, c[1] + dy) for c in cells for dx in (-1, 0, 1) for dy in (-1, 0, 1)}
    lines = []
    for m, ln, c in w.lines((min(BOX[0], PORT[0]), min(BOX[1], PORT[1]), max(BOX[2], PORT[2]), max(BOX[3], PORT[3]))):
        pid = W.line_id(ln)
        name = ln.split("\t")[1]
        if pid in STAYS or name in STAYS:
            continue
        town = ln.startswith("NPC") and "Attitude=Good" in ln and re.search(r"\b(Zone|Stand|Patrol)=", ln)
        if c in near or c in whole or pid.startswith("Ashford") or town or (
                BOX[0] <= c[0] <= BOX[2] and BOX[1] <= c[1] <= BOX[3] and ln.startswith(("Id", "Lock", "Trigger"))):
            lines.append((m, ln, c))
    return cells, whole, lines


def regroup(w, moved):
    """(move_keep.py's: a moved roof's group made its own on the map it's on now)"""
    import move_keep
    move_keep.regroup_roofs(w, moved)


def levels():
    out = []
    for (mx, my, mz) in sorted(W.all_levels()):
        if mz == 0 or mz >= 10 or mz <= -9:
            continue
        if BOX[0] // XT <= mx <= BOX[2] // XT and BOX[1] // YT <= my <= BOX[3] // YT:
            W.rename_level_map(W.mname(mx, my, mz), W.mname(mx, my - DY_MAPS, mz))
            out.append((W.mname(mx, my, mz), W.mname(mx, my - DY_MAPS, mz)))
    return out


def names_moved(levels_moved):
    out = {}
    for mx in range(min(BOX[0], PORT[0]) // XT, max(BOX[2], PORT[2]) // XT + 1):
        for my in range(min(BOX[1], PORT[1]) // YT, BOX[3] // YT + 1):
            out[W.mname(mx, my, 0)] = W.mname(mx, my - DY_MAPS, 0)
    out.update(dict(levels_moved))
    return out


SCRIPT_MAPS = ("11,4,0", "12,5,0", "13,4,0", "12,4,0", "11,5,0", "13,5,0", "12,6,0", "11,6,0", "13,6,0", "10,5,0",
               "14,4,0", "14,5,0", "12,3,0")


def words(levels_moved):
    """Every name of a moved map: in the scripts, the raids, the homestead's way back, a quest's marker, the music and
    the ambience."""
    names = names_moved(levels_moved)
    names = {a: b for a, b in names.items() if a in SCRIPT_MAPS or a.split(",")[2] != "0"}
    pairs = []
    for a, b in names.items():
        for pre, post in (("\t", "\t"), ("\t", "\r\n"), ("=", "\r\n"), ("=", " "), (" on ", " "), ("\t", " ")):
            pairs.append((pre + a + post, pre + b + post))
    for a, b in names_moved(levels_moved).items():             # (the maps' arrival words)
        sa, sb = os.path.join(W.SCRIPTS, a + ".txt"), os.path.join(W.SCRIPTS, b + ".txt")
        if a.endswith(",0") and os.path.exists(sa) and not os.path.exists(sb):
            os.rename(sa, sb)
    n = len(W.replace_in_files(W.scripts(), pairs))
    for f in ("Waves.ini", "Config.ini", "Quests.ini"):
        n += len(W.replace_in_files([os.path.join(DATA, f)], pairs))
    for f, wild in (("Music.ini", "Fields"), ("Ambient.ini", "Wind")):
        path = os.path.join(DATA, f)
        s = W.read(path)
        moved = {}
        for a, b in names_moved(levels_moved).items():
            mm = re.search(r"(?m)^%s=(\w+)\r$" % re.escape(a), s)
            if mm:
                moved[b] = mm.group(1)
                if a.endswith(",0"):
                    s = s.replace("%s=%s\r\n" % (a, mm.group(1)), "%s=%s\r\n" % (a, wild))
                else:
                    s = s.replace("%s=%s\r\n" % (a, mm.group(1)), "")
        for b, v in moved.items():
            s = re.sub(r"(?m)^%s=\w+\r\n" % re.escape(b), "", s)
            s = s.replace("\r\n\r\n", "\r\n%s=%s\r\n\r\n" % (b, v), 1) if "[Maps]" not in s else \
                s.replace("[Maps]\r\n", "[Maps]\r\n%s=%s\r\n" % (b, v), 1)
        W.write(path, s)
    return n


def ambience_for_new(w):
    """The new maps' ambience: the sea's, or the open land's (their music: the world's own, as most maps have)."""
    x1, y1, x2, y2 = NEW_MAPS
    for f, sea, land in (("Ambient.ini", "Waves", "Wind"),):
        path = os.path.join(DATA, f)
        s = W.read(path)
        for mx in range(x1, x2 + 1):
            for my in range(y1, y2 + 1):
                name = W.mname(mx, my, 0)
                if re.search(r"(?m)^%s=" % re.escape(name), s):
                    continue
                m = w.maps[(mx, my)]
                wet = sum(1 for row in m.rows for c in row if W.watery(c))
                v = sea if wet > XT * YT * 0.7 else land
                if v is None:
                    continue
                s = s.replace("[Maps]\r\n", "[Maps]\r\n%s=%s\r\n" % (name, v), 1) if "[Maps]" in s else \
                    s.rstrip("\r\n") + "\r\n%s=%s\r\n" % (name, v)
        W.write(path, s)


def main():
    if os.path.exists(DONE):
        print("Ashford's moved already (delete %s to do it again)." % DONE)
        return
    w = W.World(0)
    cells, whole, lines = moving(w)
    made = grow(w)
    dest_box = (BOX[0], BOX[1] - DY, BOX[2], BOX[3] - DY)
    dest = {(x, y - DY) for x, y in cells | whole}
    for x, y in sorted(cells | whole):
        w.put(x, y - DY, w.cell(x, y))
    regroup(w, dest)
    for m, ln, c in lines:
        w.drop(m, ln)
        mx, my, _ = W.mxyz(m.name)
        w.add_line(ln, (mx, my), 0, -DY)
    gone = cells | {c for c in whole if not W.natural(w.cell(*c))}
    ends = W.road_ends(w, BOX, gone)
    w.rewild(gone, seed="ashford")
    reshape(w, dest)
    w.smooth_shores({(x, y) for x in range(NEW_MAPS[0] * XT, (NEW_MAPS[2] + 1) * XT) for y in range(-140, 100)
                     if w.cell(x, y) is not None})
    streets = {c for c in dest if W.is_road(w.cell(*c))}
    n = W.join_roads(w, ends, network=streets)
    changed = w.save()
    lv = levels()
    k = words(lv)
    ambience_for_new(w)
    print("Ashford: %d cells and %d things moved seven maps north onto %d cells of new land; %d roads joined; %d maps "
          "changed; levels moved: %s; %d files named its maps" % (len(cells | whole), len(lines), len(made), n,
                                                                  changed, ", ".join(b for _, b in lv), k))
    print("Its new place: %s" % (dest_box,))
    open(DONE, "w").write("moved\n")


if __name__ == "__main__":
    main()
