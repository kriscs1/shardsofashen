"""King Rupert's Keep moved south to where Ravensgate stood (the owner's wish; remove_towns.py took Ravensgate away
first). Five maps south, exactly: every cell, thing, roof, upstairs and cellar of it keeps its place on its map, and
only the maps' names change (25,13,0 is 25,18,0 now), so its people's zones, its stair and its scripts hold.

  * Moved: what was built (its streets, houses, the keep itself, the King's solar over it) and everyone and everything
    in it; the wild ground under it is the downs' own. The river it stood above stays where it runs.
  * Stays where it was: the old iron mine in the hills (the Steward's Hunt) and the cinder cache's chest; the road
    north to Emberwatch, joined to the Keep again, over the river's bridge. The ground the Keep stood on is wild again.
  * Its harbour: Ravensgate's old jetty, which reaches the sea (the Keep's own pier would stand on dry land now): the
    harbour master and Keep_Port go there.
  * Ravensgate's graves and its Gravekeeper (The Barrow King) laid out again in a graveyard of their own, west of the
    Keep; Captain Rook on his shore below it, as he was.
  * Every name of a moved map, in the scripts, Ambient.ini, the builders and the tests.

Run it once (a second run finds the Keep moved and stops).

  python -I "dev\\migrate\\move_keep.py"
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import world_edit as W                                   # noqa: E402
from world_edit import XT, YT                           # noqa: E402

ROOT = W.ROOT
DATA = os.path.join(ROOT, "data")
DONE = os.path.join(HERE, ".keep_moved")
DY_MAPS = 5
DY = DY_MAPS * YT
BOX = (600, 245, 701, 322)                             # (the Keep, above the river)
STAYS = (595, 240, 619, 266)                           # (the old iron mine's yard: in the hills, where it is)
PIER_X = 676                                           # (east of this, its pier's planks: not moved)
GRAVES = ["Grave_Old_Wat", "Grave_Raven_Mark", "Grave_Osric_Raven", "Grave_Elsa_Moor", "Grave_Gideon_Sexton",
          "Grave_Rowan_Twins", "Grave_Martha_Lark", "Grave_Snow_Traveller", "Grave_Cobb_Digger", "Grave_Isolde_Ashby",
          "Grave_Bram_Smith", "Grave_Fresh_Flowers"]


def inside(c, box):
    return box[0] <= c[0] <= box[2] and box[1] <= c[1] <= box[3]


def pier(text, x):
    """Its pier's planks (out over the water, no roof): left to the sea."""
    t, over = W.parts(text)
    return x >= PIER_X and t in ("Boardwalk001", "Plank001") and not over.get("Roof")


def moving_cells(w):
    out = set()
    for x in range(BOX[0], BOX[2] + 1):
        for y in range(BOX[1], BOX[3] + 1):
            text = w.cell(x, y)
            if text is None or W.natural(text) or inside((x, y), STAYS):
                continue
            if pier(text, x):
                continue
            out.add((x, y))
    return out


def moving_lines(w, cells):
    near = {(c[0] + dx, c[1] + dy) for c in cells for dx in (-1, 0, 1) for dy in (-1, 0, 1)}
    out = []
    for m, ln, c in w.lines(BOX):
        p = ln.split("\t")
        pid = W.line_id(ln)
        if inside(c, STAYS) or pid in ("Keep_Port", "Keep_Harbour_Master_311") or p[1] == "Moored_Boat":
            continue
        town = p[0] == "NPC" and "Attitude=Good" in ln and re.search(r"\b(Zone|Stand|Patrol)=", ln)
        if c in near or pid.startswith("Keep_") or town:
            out.append((m, ln, c))
    return out


def regroup_roofs(w, moved):
    """A moved roof's group number made one of its own on the map it's on now (another may have it there)."""
    by_map = {}
    for c in moved:
        by_map.setdefault((c[0] // XT, c[1] // YT), set()).add(c)
    for key, cells in by_map.items():
        m = w.maps[key]
        have = set()
        for y in range(YT):
            for x in range(XT):
                g = (key[0] * XT + x, key[1] * YT + y)
                if g in cells:
                    continue
                mm = re.search(r"\+Roof\([^)]*\.(\d+)\)", m.rows[y][x])
                if mm:
                    have.add(int(mm.group(1)))
        remap = {}
        for c in sorted(cells):
            text = w.cell(*c)
            mm = re.search(r"\+Roof\(([^)]*)\.(\d+)\)", text)
            if not mm:
                continue
            g = int(mm.group(2))
            if g in have:
                if g not in remap:
                    n = 1
                    while n in have or n in remap.values():
                        n += 1
                    remap[g] = n
                w.put(c[0], c[1], text.replace(mm.group(0), "+Roof(%s.%02d)" % (mm.group(1), remap[g])))
    return


def move_levels():
    """The Keep's upstairs and cellars: their maps renamed five maps south."""
    moved = []
    for (mx, my, mz) in sorted(W.all_levels()):
        if mz == 0 or mz >= 10 or mz <= -9:
            continue
        if not (BOX[0] // XT <= mx <= BOX[2] // XT and BOX[1] // YT <= my <= BOX[3] // YT):
            continue
        if (mx, my) in ((24, 12), (25, 12)):
            continue                                            # (the old iron mine's levels: where it is)
        W.rename_level_map(W.mname(mx, my, mz), W.mname(mx, my + DY_MAPS, mz))
        moved.append((W.mname(mx, my, mz), W.mname(mx, my + DY_MAPS, mz)))
    return moved


def graveyard(w, keep_cells, keeper):
    """Ravensgate's graves in rows west of the Keep (a gravel path between them), and the Gravekeeper among them."""
    graves = []
    for pid in GRAVES:
        m, c = w.find_id(pid)
        if m is None:
            continue
        graves.append((pid, W.parts(w.cell(*c))[1].get("Decor", "Grave001")))
        for ln in list(m.ents):
            if W.line_id(ln) == pid:
                w.drop(m, ln)
        w.rewild([c], seed="grave")
    taken = {(c[0] + dx, c[1] + dy) for c in keep_cells for dx in range(-4, 5) for dy in range(-4, 5)}
    gw, gh = 9, 7                                               # (four rows of three, a path down the middle)
    best = None
    for y0 in range(BOX[1] + DY, BOX[3] + DY - gh):
        for x0 in range(BOX[0] - 30, BOX[0] + 20):
            if x0 // XT != (x0 + gw - 1) // XT or y0 // YT != (y0 + gh - 1) // YT:
                continue
            cells = [(x, y) for x in range(x0, x0 + gw) for y in range(y0, y0 + gh)]
            if any(q in taken or w.cell(*q) is None or not W.natural(w.cell(*q)) or
                   W.parts(w.cell(*q))[0] not in ("Grass001",) for q in cells):
                continue
            d = abs(x0 + gw - BOX[0]) + abs(y0 - (BOX[1] + DY + 50))
            if best is None or d < best[0]:
                best = (d, x0, y0)
    _, x0, y0 = best
    for x in range(x0, x0 + gw):
        for y in range(y0, y0 + gh):
            w.put(x, y, "Grass001")
    for y in range(y0, y0 + gh):
        w.put(x0 + gw // 2, y, "Gravel001")
    spots = [(x0 + dx, y0 + dy) for dy in (1, 3, 5) for dx in (0, 2, 6, 8)]
    for (pid, decor), c in zip(graves, spots):
        w.put(c[0], c[1], "Grass001+Decor(%s)" % decor)
        w.place_id(c[0], c[1], pid)
    if keeper is not None:
        m, ln = keeper
        w.drop(m, ln)
        p = ln.split("\t")
        opts = re.sub(r"\bZone=\S+", "", p[4]).strip()
        at = (x0 + gw // 2, y0 + gh - 1)
        w.place(at[0], at[1], "NPC", "Gravekeeper",
                opts + " Zone=%s" % w.zone(x0, y0, x0 + gw - 1, y0 + gh - 1, *at), dy=-8)
    for m, ln, c in w.lines():
        if W.line_id(ln) == "Keep_Gravekeeper":
            w.drop(m, ln)
    w.place_id(x0 + gw // 2, y0 + gh - 1, "Keep_Gravekeeper")
    return (x0, y0, x0 + gw - 1, y0 + gh - 1)


def harbour(w):
    """The Keep's harbour master and Keep_Port on Ravensgate's old jetty."""
    planks = [(x, y) for x in range(686, 702) for y in range(360, 374) if w.tile(x, y) in ("Boardwalk001", "Plank001")]
    if not planks:
        print("  !! no jetty")
        return
    land_end = min(planks)
    for m, ln, c in w.lines((660, 270, 701, 300)):
        pid = W.line_id(ln)
        if pid == "Keep_Port":
            w.drop(m, ln)
        elif pid == "Keep_Harbour_Master_311":
            w.drop(m, ln)
            stand = (land_end[0] - 1, land_end[1])
            w.place(stand[0], stand[1], "NPC", "Fisherman", ln.split("\t")[4], dy=-8)
        elif ln.split("\t")[1] == "Moored_Boat":
            w.drop(m, ln)
    w.place_id(land_end[0] + 2, land_end[1], "Keep_Port")


def scripts_and_data(levels):
    """What names a moved map: its entry script, the scripts, Ambient.ini, the builders, the tests."""
    names = {}
    for mx in range(BOX[0] // XT, BOX[2] // XT + 1):
        for my in range(BOX[1] // YT, BOX[3] // YT + 1):
            if (mx, my) not in ((24, 12),):
                names[W.mname(mx, my, 0)] = W.mname(mx, my + DY_MAPS, 0)
    for a, b in levels:
        names[a] = b
    for a, b in names.items():                                  # (the maps' arrival words: the keep's, the town's)
        sa, sb = os.path.join(W.SCRIPTS, a + ".txt"), os.path.join(W.SCRIPTS, b + ".txt")
        if os.path.exists(sa) and not os.path.exists(sb):
            os.rename(sa, sb)
    pairs = [("\t%s\t" % a, "\t%s\t" % b) for a, b in names.items()] + \
            [("\t%s\r\n" % a, "\t%s\r\n" % b) for a, b in names.items()]
    stays = ("25,11,0",)                                        # (the cinder cache's chest)
    pairs = [(a, b) for a, b in pairs if a.strip() not in stays]
    changed = W.replace_in_files(W.scripts(), pairs)
    amb = os.path.join(DATA, "Ambient.ini")
    s = W.read(amb)
    for a, b in levels:
        mm = re.search(r"(?m)^%s=(\w+)\r$" % re.escape(a), s)
        if mm:
            s = s.replace("%s=%s\r\n" % (a, mm.group(1)), "")
            s = s.replace("[Maps]\r\n", "[Maps]\r\n%s=%s\r\n" % (b, mm.group(1)), 1)
    W.write(amb, s)
    return changed


def main():
    if os.path.exists(DONE):
        print("The Keep's moved already (delete %s to do it again)." % DONE)
        return
    w = W.World(0)
    cells = moving_cells(w)
    lines = moving_lines(w, cells)
    dest = {(x, y + DY) for x, y in cells}
    dbox = (BOX[0], BOX[1] + DY, BOX[2], BOX[3] + DY)
    # (what's still at the new place: its roads made wild again, the graves and the keeper kept to lay out anew)
    keeper = next(((m, ln) for m, ln, c in w.lines(dbox) if ln.split("\t")[1] == "Gravekeeper"), None)
    clear = {(x, y) for x in range(dbox[0], dbox[2] + 1) for y in range(dbox[1], dbox[3] + 1)
             if w.cell(x, y) is not None and not W.natural(w.cell(x, y)) and
             not (x >= 686 and w.tile(x, y) in ("Boardwalk001", "Plank001")) and
             not w.cell(x, y).split("+")[-1].startswith("Decor(Grave")}
    w.rewild(clear, seed="downs")
    in_the_way = {(c[0] + dx, c[1] + dy) for c in dest for dx in (-1, 0, 1) for dy in (-1, 0, 1)}
    displaced = [(m, ln, c) for m, ln, c in w.lines(dbox) if c in in_the_way and not W.line_id(ln).startswith("Grave_")
                 and ln.split("\t")[1] != "Gravekeeper"]
    for x, y in sorted(cells):
        w.put(x, y + DY, w.cell(x, y))
    regroup_roofs(w, dest)
    for m, ln, c in lines:
        w.drop(m, ln)
        mx, my, _ = W.mxyz(m.name)
        w.add_line(ln, (mx, my), 0, DY)
    moved_off = 0
    for m, ln, c in displaced:                                   # (a secret, a stray: out from under the buildings)
        w.drop(m, ln)
        for r in range(2, 12):
            q = next(((c[0] + dx, c[1] + dy) for dx in range(-r, r + 1) for dy in range(-r, r + 1)
                      if (c[0] + dx, c[1] + dy) not in in_the_way and w.cell(c[0] + dx, c[1] + dy) is not None
                      and W.natural(w.cell(c[0] + dx, c[1] + dy)) and not W.watery(w.cell(c[0] + dx, c[1] + dy))
                      and not W.parts(w.cell(c[0] + dx, c[1] + dy))[1].get("Decor")), None)
            if q:
                mx, my, _ = W.mxyz(m.name)
                w.add_line(ln, (mx, my), q[0] - c[0], q[1] - c[1])
                moved_off += 1
                break
    planks = {(x, y) for x in range(PIER_X, BOX[2] + 1) for y in range(BOX[1], BOX[3] + 1)
              if w.cell(x, y) is not None and pier(w.cell(x, y), x)}
    old_ends = W.road_ends(w, BOX, cells | planks)
    w.rewild(cells | planks, seed="keep")
    yard = graveyard(w, dest, keeper)
    harbour(w)
    streets = {c for c in dest if W.is_road(w.cell(*c))}
    new_ends = W.road_ends(w, dbox, clear - dest)
    n = W.join_roads(w, old_ends + new_ends, network=streets)
    W.join_roads(w, [(yard[0] + (yard[2] - yard[0]) // 2, yard[3] + 1)], network=streets)
    changed = w.save()
    levels = move_levels()
    scr = scripts_and_data(levels)
    print("The Keep: %d cells and %d things moved five maps south; %d moved out from under it; %d roads joined; "
          "%d maps changed; levels moved: %s; %d scripts" % (len(cells), len(lines), moved_off, n, changed,
                                                             ", ".join(b for _, b in levels), len(scr)))
    print("Its graveyard: %s" % (yard,))
    open(DONE, "w").write("moved\n")


if __name__ == "__main__":
    main()
