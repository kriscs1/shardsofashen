"""Villages for the generated regions (build_regions.py's Wildlands, build_eastreach.py's Eastreach).

build(grid, busy, cx, cy, ...) lays out one village round world tile cx,cy (the middle of its square):
  * a clearing with a ragged edge (not a rectangle cut out of the land), about 29 x 23 tiles;
  * ponds and rivers stay (a street crosses on planks), but a marsh village stands on boardwalks;
  * a dirt square in the middle, kept free for the waystone, the notice, the quest giver and the Settler
    (cx-4..cx+4, cy-3..cy+3);
  * four winding streets out from the square to the gates (cx+-11, cy) and (cx, cy+-9), where the roads join;
  * 5 to 7 houses of different sizes (5-7 x 5-6; smaller ones only if too few fit), placed at random near the streets
    (none on a street, none touching another, each inside one map so its roof stays whole), each facing the viewer: its
    door in the front (bottom) wall, which the roof leaves showing, and a path from the door to the nearest street;
  * each house in a wall and a roof that suit the land (STYLE, ROOFS): timber and thatch in the woods, slate and stone
    on the moors and in the snow, sandstone and clay tiles in the desert...;
  * two storeys to look at: under the eaves the upper storey's front (part of the roof: roof_spec, roof_piece), windows
    either side of the door, a chimney over the hearth and on some roofs dormers;
  * inside (lay_house): a hearth in the back wall, a table and chairs, a bed, a bookshelf, a plant; about half the bigger
    houses have an upper floor with bedrooms (upper_floors: the level-1 maps), up stairs or a ladder.
It returns the houses, nearest the square first (the first three are the bank, the Trader's shop and a workshop), the
streets and the roofs [(x1, y1, x2, y2, material)] (world tiles; the caller numbers the roof groups).
"""
import math
import random
from collections import deque

WALL_DOORS = {"Brick001": "Door001", "Stone_Wall001": "Door002", "Timber001": "Door004", "Plaster001": "Door005",
              "Sandstone001": "Door006"}
WALL_BASES = {"Brick001": "Brick", "Stone_Wall001": "Stone_Wall", "Timber001": "Timber", "Plaster001": "Plaster",
              "Sandstone001": "Sandstone"}     # (house_tiles.py draws <Base>_Window001/002 and <Base>_Upper001/002)


def window_tile(wall, n=1):
    """A window in the front wall (n=2: the loose one you can climb through)."""
    return "%s_Window%03d" % (WALL_BASES[wall], n)


def upper_tile(wall, window):
    """The upper storey's front, part of the roof overlay (so it hides with the roof when you go in)."""
    return "%s_Upper%03d" % (WALL_BASES[wall], 1 if window else 2)


# furniture (interior_tiles.py); the ones you can't walk through are in BLOCKING
BLOCKING = {"Bed001", "Bed002", "Table001", "Potted_Plant001", "Bookshelf001", "Fireplace001", "Fireplace003"}
FURNITURE = BLOCKING | {"Chair001", "Chair002", "Chair003", "Chair004"}
STAIRS = [("Stairs001", "Stairs002"), ("Ladder008", "Ladder009")]      # (up on the ground floor, down upstairs)
RUG_FLOORS = {"Plank001": 1, "Tile001": 31}       # interior_tiles: the rug pieces on planks / on stone tiles
RUGS = {"Rug%03d" % (b + k) for b in RUG_FLOORS.values() for k in list(range(9)) + list(range(10, 17))}
HOUSE_TILES = (set(WALL_DOORS) | set(WALL_DOORS.values()) | {"Plank001"} | FURNITURE | RUGS |
               {window_tile(w, n) for w in WALL_DOORS for n in (1, 2)} | {t for pair in STAIRS for t in pair})
STYLE = {   # land -> [(wall, weight)]
    "wood": [("Timber001", 5), ("Plaster001", 3), ("Brick001", 2)],
    "moor": [("Stone_Wall001", 4), ("Plaster001", 3), ("Brick001", 3)],
    "marsh": [("Timber001", 5), ("Plaster001", 4), ("Brick001", 1)],
    "hills": [("Stone_Wall001", 5), ("Brick001", 3), ("Plaster001", 2)],
    "desert": [("Sandstone001", 6), ("Plaster001", 4)],
    "snow": [("Stone_Wall001", 5), ("Timber001", 5)],
    "elder": [("Timber001", 5), ("Plaster001", 3), ("Stone_Wall001", 2)],
    "downs": [("Stone_Wall001", 5), ("Plaster001", 3), ("Brick001", 2)],
}
ROOFS = {   # wall -> [(roof material, weight)] (house_tiles.ROOF_MATERIALS)
    "Timber001": [("Thatch", 3), ("Shingle", 3)],
    "Plaster001": [("Thatch", 4), ("Clay", 2), ("Slate", 1)],
    "Brick001": [("Clay", 3), ("Slate", 3), ("Shingle", 1)],
    "Stone_Wall001": [("Slate", 4), ("Thatch", 2)],
    "Sandstone001": [("Clay", 5), ("Thatch", 1)],
}
ROW_KINDS = {1: "R", 2: "TB", 3: "TRB", 4: "TRDB", 5: "TURDB", 6: "TURDDB"}


def roof_spec(material, wall, chimney, dormers):
    """A two-storey house's roof for build_world's roof lines: "<roof material>:<wall>:<chimney column>:<dormer
    columns>" (columns counted from the roof's west end; -1 = no chimney)."""
    return "%s:%s:%d:%s" % (material, wall, chimney, ",".join(str(d) for d in dormers))


def upper_window(x, x1, x2):
    """Is there a window in the upper storey above column x (of a front from x1 to x2)? Every other one, not the ends."""
    return x not in (x1, x2) and (x - x1) % 2 == 1


def roof_piece(material, x, y, x1, y1, x2, y2):
    """The roof tile for cell x,y of a roof over x1..x2, y1..y2 (house_tiles: <Material>_Roof001-015, 016-030 with a
    chimney, 031/032 a dormer). material may be a roof_spec(): then the roof's bottom row is the upper storey's front."""
    parts = material.split(":")
    material, chimney, dormers = parts[0], -1, []
    if len(parts) > 1:
        wall, chimney = parts[1], int(parts[2])
        dormers = [int(v) for v in parts[3].split(",") if v]
        if y == y2:
            return upper_tile(wall, upper_window(x, x1, x2))
        y2 -= 1
    rows = ROW_KINDS[max(1, min(6, y2 - y1 + 1))]
    rk = rows[min(len(rows) - 1, y - y1)]
    ck = "W" if x == x1 else ("E" if x == x2 else "M")
    piece = "TURDB".index(rk) * 3 + "WME".index(ck) + 1
    if x - x1 == chimney and rk == ("R" if "R" in rows else rows[0]):
        piece += 15
    elif x - x1 in dormers and ck == "M" and rk == ("D" if "D" in rows else "B") and len(rows) >= 3:
        piece = 31 if rk == "D" else 32
    return "%s_Roof%03d" % (material, piece)


def pick(rng, weighted):
    total = sum(w for _, w in weighted)
    r = rng.uniform(0, total)
    for item, w in weighted:
        r -= w
        if r <= 0:
            return item
    return weighted[-1][0]


def winding(a, b, wobble, rng):
    """A 4-connected line from a to b that wanders up to wobble tiles to the side."""
    (ax, ay), (bx, by) = a, b
    n = max(abs(bx - ax), abs(by - ay), 1)
    px, py = -(by - ay) / float(n), (bx - ax) / float(n)
    ln = math.hypot(px, py) or 1
    px, py = px / ln, py / ln
    ph1, ph2 = rng.uniform(0, 6.3), rng.uniform(0, 6.3)
    pts = []
    for i in range(n + 1):
        t = i / float(n)
        off = wobble * math.sin(math.pi * t) * (0.7 * math.sin(2.1 * math.pi * t + ph1) + 0.3 * math.sin(4.3 * math.pi * t + ph2))
        pts.append((int(round(ax + (bx - ax) * t + px * off)), int(round(ay + (by - ay) * t + py * off))))
    out = [pts[0]]
    for (x1, y1) in pts[1:]:
        x, y = out[-1]
        while (x, y) != (x1, y1):
            if x != x1:
                x += 1 if x1 > x else -1
            elif y != y1:
                y += 1 if y1 > y else -1
            out.append((x, y))
    return out


def build(grid, busy, cx, cy, seed, land, ground, is_sea, gw, gh, ground_tiles, reach=(13, 10), keep_out=(),
          count=(5, 7)):
    """Lays the village into grid (world tile -> tile name) and busy. ground: the land's plain ground tile; is_sea(gx,
    gy): water there stays water (ponds become boardwalks); gw, gh: tiles per map; ground_tiles: tiles a house may stand
    on (the land's walkable ground); reach: how far from the centre (x, y) a house may reach (a walled town: less);
    keep_out: cells no house may cover (the quest sites' clearings, made later); count: how many houses (min, max)."""
    rng = random.Random(seed)
    # the clearing: an ellipse with a wobbly edge
    ph = [rng.uniform(0, 6.3) for _ in range(3)]
    for gy in range(cy - 11, cy + 12):
        for gx in range(cx - 14, cx + 15):
            if (gx, gy) not in grid:
                continue
            a = math.atan2(gy - cy, gx - cx)
            edge = 1 + 0.12 * math.sin(3 * a + ph[0]) + 0.08 * math.sin(5 * a + ph[1]) + 0.05 * math.sin(7 * a + ph[2])
            if ((gx - cx) / 14.0) ** 2 + ((gy - cy) / 11.0) ** 2 > edge * edge:
                continue
            t = grid[(gx, gy)]
            if t.startswith("Water") or t == "Reeds001":
                if land == "marsh" and not is_sea(gx, gy):   # a marsh village stands on boardwalks
                    grid[(gx, gy)] = "Plank001"
                # (elsewhere ponds and rivers stay: the streets cross them on planks)
            else:
                grid[(gx, gy)] = ground
            busy.add((gx, gy))

    def lay_dirt(cells):
        for c in cells:
            t = grid.get(c)
            if t is None or t in HOUSE_TILES and t != "Plank001":
                continue
            if t.startswith("Water") or t == "Reeds001":
                if is_sea(*c):
                    continue
                grid[c] = "Plank001"
            else:
                grid[c] = "Dirt001"
            busy.add(c)

    # the square
    square = set()
    for gy in range(cy - 3, cy + 4):
        for gx in range(cx - 4, cx + 5):
            if ((gx - cx) / 3.6) ** 2 + ((gy - cy) / 2.6) ** 2 <= 1 + 0.15 * rng.random():
                square.add((gx, gy))
    lay_dirt(sorted(square))
    # the streets, out to the gates
    streets = {}
    for d, gate, start in (("W", (cx - 11, cy), (cx - 3, cy)), ("E", (cx + 11, cy), (cx + 3, cy)),
                           ("N", (cx, cy - 9), (cx, cy - 2)), ("S", (cx, cy + 9), (cx, cy + 2))):
        cells = winding(start, gate, 2.2, rng)
        streets[d] = cells
        lay_dirt(cells)
    street_cells = set(square) | {c for cells in streets.values() for c in cells}
    keep_clear = set(street_cells)
    for (x, y) in street_cells:
        keep_clear.update(((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)))
    keep_clear.update((x, y) for x in range(cx - 4, cx + 5) for y in range(cy - 3, cy + 4))
    keep_clear.update(keep_out)

    # the houses
    houses = []
    taken = set()

    def fits(x0, y0, w, h, door_x, clear):
        x1, y1 = x0 + w - 1, y0 + h - 1
        if x0 // gw != x1 // gw or y0 // gh != (y1 + 1) // gh:            # one map (and the step out of the door too)
            return False
        for y in range(y0 - 1, y1 + 3):                                   # a gap all round, two in front
            for x in range(x0 - 1, x1 + 2):
                if (x, y) in taken:
                    return False
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                if (x, y) in clear or grid.get((x, y)) not in ground_tiles:
                    return False
        out = (door_x, y1 + 1)
        if grid.get(out) not in ground_tiles and grid.get(out) != "Dirt001":
            return False
        near = min(abs(x - sx) + abs(y - sy) for (sx, sy) in street_cells for (x, y) in ((x0, y0), (x1, y1), (x0, y1), (x1, y0)))
        return near <= 6

    want = rng.randint(*count)
    best = []
    for tries in range(24):                           # (another arrangement if too few fit; later, smaller houses)
        placed, used, clear = [], set(), set(keep_clear)
        taken.clear()
        for _ in range(1500):
            if len(placed) >= want:
                break
            w, h = rng.randint(5, 7), rng.choice((5, 5, 5, 6, 6))      # two storeys: a roof over an upper floor
            if tries >= 8:
                w, h = rng.randint(4, 6), rng.choice((4, 5))
            x0 = rng.randint(cx - reach[0], cx + reach[0] - w + 1)
            y0 = rng.randint(cy - reach[1], cy + reach[1] - h)
            door_x = rng.randint(x0 + 1, x0 + w - 2)
            if not fits(x0, y0, w, h, door_x, clear):
                continue
            wall = pick(rng, STYLE[land])
            placed.append(dict(x0=x0, y0=y0, w=w, h=h, door=(door_x, y0 + h - 1), wall=wall,
                               roof=pick(rng, ROOFS[wall])))
            for y in range(y0, y0 + h):
                for x in range(x0, x0 + w):
                    taken.add((x, y))
            clear.update(((door_x, y0 + h), (door_x, y0 + h + 1)))     # the way out of the door
        if len(placed) > len(best):
            best, best_taken = placed, set(taken)
        if len(best) >= max(4, count[0] - 1):
            break
    houses = best
    taken.clear()
    taken.update(best_taken)
    assert len(houses) >= 3, "village at %d,%d: only %d houses fit" % (cx, cy, len(houses))

    roofs = []
    houses.sort(key=lambda hs: abs(hs["x0"] + hs["w"] / 2 - cx) + abs(hs["y0"] + hs["h"] / 2 - cy))
    for k, hs in enumerate(houses):
        x0, y0, w, h = hs["x0"], hs["y0"], hs["w"], hs["h"]
        x1, y1 = x0 + w - 1, y0 + h - 1
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                edge = y in (y0, y1) or x in (x0, x1)
                grid[(x, y)] = hs["wall"] if edge else "Plank001"
                busy.add((x, y))
        grid[hs["door"]] = WALL_DOORS[hs["wall"]]
        hs["inside"] = (x0 + w // 2, y0 + 1)                  # where someone stands inside (back of the room)
        hs["benches"] = [(x0 + 1, y0 + 1), (x1 - 1, y0 + 1)]  # two spots against the back wall
        lay_house(grid, hs, k, rng)
        # the roof, and under its eaves the upper storey's front (the ground-floor front, with the door, shows below)
        dormers = [d for d in range(1, w - 1) if d % 2 == 0] if hs["upper"] and rng.random() < 0.6 else []
        roofs.append((x0, y0, x1, y1 - 1, roof_spec(hs["roof"], hs["wall"], hs["fireplace"] - x0, dormers)))
        # a path from the door to the nearest street, round the other houses
        start = (hs["door"][0], y1 + 1)
        prev = {start: None}
        q = deque([start])
        end = None
        while q:
            c = q.popleft()
            if c in street_cells and c != start:
                end = c
                break
            x, y = c
            for n in ((x, y + 1), (x - 1, y), (x + 1, y), (x, y - 1)):
                if n not in prev and n not in taken and abs(n[0] - cx) <= 15 and abs(n[1] - cy) <= 12 \
                        and grid.get(n) is not None and (grid[n] in ground_tiles or grid[n] in ("Dirt001", "Plank001")):
                    prev[n] = c
                    q.append(n)
        path = []
        c = end
        while c is not None:
            path.append(c)
            c = prev[c]
        lay_dirt(path or [start])
    return dict(houses=houses, streets=streets, roofs=roofs)


# ------------------------------------------------------------------------------------------- inside the houses
def connected(cells, blocked, start):
    """Can every cell of cells that isn't blocked be walked to from start (4 ways)?"""
    free = {c for c in cells if c not in blocked}
    if start not in free:
        return False
    seen, todo = {start}, [start]
    while todo:
        x, y = todo.pop()
        for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if n in free and n not in seen:
                seen.add(n)
                todo.append(n)
    return seen == free


def furnish(placed, cells, start, keep, near_stairs, pieces, most=99):
    """Adds to placed ({cell: tile}) up to `most` of pieces (each {cell: tile}, tried in order) that fit: keeping keep
    clear, nothing that blocks next to the stairs, and every free floor cell reachable from start."""
    n = 0
    for piece in pieces:
        if n >= most:
            break
        if any(c not in cells or c in keep or c in placed for c in piece):
            continue
        if any(c in near_stairs and t in BLOCKING for c, t in piece.items()):
            continue
        trial = dict(placed)
        trial.update(piece)
        if connected(cells, {c for c, t in trial.items() if t in BLOCKING}, start):
            placed.update(piece)
            n += 1
    return placed


def rug_piece(i, j, w, h):
    """interior_tiles' rug piece (offset from the floor's base) for cell i, j of a w x h rug."""
    if w == 1 and h == 1:
        return 16
    if h == 1:
        return 10 if i == 0 else (12 if i == w - 1 else 11)
    if w == 1:
        return 13 if j == 0 else (15 if j == h - 1 else 14)
    r = 0 if j == 0 else (2 if j == h - 1 else 1)
    c = 0 if i == 0 else (2 if i == w - 1 else 1)
    return r * 3 + c


def lay_rug(placed, cells, rng, floor="Plank001", sizes=((4, 3), (3, 3), (4, 2), (3, 2), (2, 3), (2, 2), (3, 1),
                                                         (1, 3), (2, 1), (1, 2), (1, 1))):
    """A rug (interior_tiles' pieces) on the biggest free rectangle of floor in cells (not in placed), as near the
    middle of the room as it goes: a runner or a mat where nothing bigger fits. Adds its pieces to placed; returns
    whether one fitted."""
    if not cells:
        return False
    mx = sum(c[0] for c in cells) / float(len(cells))
    my = sum(c[1] for c in cells) / float(len(cells))
    for w, h in sizes:
        spots = []
        for (x, y) in cells:
            box = [(x + i, y + j) for j in range(h) for i in range(w)]
            if all(c in cells and c not in placed for c in box):
                spots.append((abs(x + (w - 1) / 2.0 - mx) + abs(y + (h - 1) / 2.0 - my), rng.random(), x, y))
        if spots:
            _, _, x, y = min(spots)
            base = RUG_FLOORS[floor]
            for j in range(h):
                for i in range(w):
                    placed[(x + i, y + j)] = "Rug%03d" % (base + rug_piece(i, j, w, h))
            return True
    return False


def hearth_tile(wall):
    """A brick house's hearth is red brick (Fireplace003); the others' grey stone (Fireplace001)."""
    return "Fireplace003" if wall == "Brick001" else "Fireplace001"


def lay_house(grid, hs, k, rng):
    """The front's windows, a hearth in the back wall (its chimney goes on the roof), furniture, and for some houses an
    upper floor (hs["upper"]: {world cell: tile} for level 1) up stairs or a ladder. k: the house's place in the village
    (0 the bank, 1 the Trader's, 2 the workshop: their people and benches are kept clear)."""
    x0, y0, w, h = hs["x0"], hs["y0"], hs["w"], hs["h"]
    x1, y1 = x0 + w - 1, y0 + h - 1
    wall, door_x = hs["wall"], hs["door"][0]
    for x in range(x0 + 1, x1):                                    # windows either side of the door, every other cell
        if x != door_x and (x - door_x) % 2 == 1:
            grid[(x, y1)] = window_tile(wall)
    fx = rng.choice((x0 + 1, x1 - 1))
    grid[(fx, y0)] = hearth_tile(wall)
    hs["fireplace"] = fx
    keep = {hs["inside"], (door_x, y1 - 1)}
    if k == 2:
        keep.update(hs["benches"])
    hs["upper"] = {}
    stair = (x1 - 1 if fx == x0 + 1 else x0 + 1, y0 + 1)
    upstairs = k != 2 and w >= 5 and h >= 5 and stair not in keep and rng.random() < 0.55
    near = set()
    floor = {(x, y) for y in range(y0 + 1, y1) for x in range(x0 + 1, x1)}
    start = (door_x, y1 - 1)
    placed = {}
    if upstairs:
        up, down = STAIRS[0] if rng.random() < 0.6 else STAIRS[1]   # stairs, or sometimes just a ladder
        near = {(stair[0] + dx, stair[1] + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)}
        furnish(placed, floor, start, keep, near, [{stair: up}])
        upstairs = stair in placed
    tables = sorted(floor, key=lambda c: (abs(c[0] - (x0 + x1) / 2.0) + abs(c[1] - (y0 + y1) / 2.0), rng.random()))
    furnish(placed, floor, start, keep, near, [p for (tx, ty) in tables[:4] for p in (
        {(tx, ty): "Table001", (tx - 1, ty): "Chair003", (tx + 1, ty): "Chair004"},
        {(tx, ty): "Table001", (tx - 1, ty): "Chair003"},
        {(tx, ty): "Table001", (tx, ty + 1): "Chair002"})] +
        [p for (tx, ty) in tables for p in ({(tx, ty): "Table001", (tx + 1, ty): "Chair004"},       # else anywhere,
                                            {(tx, ty): "Table001", (tx - 1, ty): "Chair003"},       # with a chair
                                            {(tx, ty): "Table001"})], most=1)                      # or on its own
    sides = [x0 + 1, x1 - 1]
    rng.shuffle(sides)
    if not upstairs:                                               # a bed downstairs, then
        furnish(placed, floor, start, keep, near, [{(bx, y0 + 1): "Bed001", (bx, y0 + 2): "Bed002"} for bx in sides],
                most=1)
    furnish(placed, floor, start, keep, near,
            [{(x, y0 + 1): "Bookshelf001"} for x in sorted(range(x0 + 1, x1), key=lambda _: rng.random())], most=1)
    furnish(placed, floor, start, keep, near, [{(bx, y1 - 1): "Potted_Plant001"} for bx in sides], most=1)
    lay_rug(placed, floor - set(placed) - {stair}, random.Random(x0 * 1009 + y0))     # (its own dice: the
    # village's rng goes on as before)
    for c, t in placed.items():
        grid[c] = t
    if not upstairs:
        return
    # the upper floor: the same walls up to the upper storey's front (with its windows), the hearth's flue, beds
    up = hs["upper"]
    yf = y1 - 1
    for y in range(y0, yf + 1):
        for x in range(x0, x1 + 1):
            up[(x, y)] = wall if y in (y0, yf) or x in (x0, x1) else "Plank001"
    for x in range(x0 + 1, x1):
        if upper_window(x, x0, x1):
            up[(x, yf)] = window_tile(wall)
    up[(fx, y0)] = hearth_tile(wall)
    floor2 = {(x, y) for y in range(y0 + 1, yf) for x in range(x0 + 1, x1)}
    placed = {stair: down}
    beds = [{(x, y0 + 1): "Bed001", (x, y0 + 2): "Bed002"} for x in sorted(range(x0 + 1, x1), key=lambda _: rng.random())]
    furnish(placed, floor2, stair, set(), near, beds, most=2)      # bedrooms: one or two beds against the back wall
    furnish(placed, floor2, stair, set(), near,
            [{c: rng.choice(("Bookshelf001", "Potted_Plant001", "Chair001"))}
             for c in sorted(floor2, key=lambda _: rng.random()) if c[1] == y0 + 1 or c[0] in (x0 + 1, x1 - 1)],
            most=2)
    lay_rug(placed, floor2 - set(placed), random.Random(x0 * 1009 + y0 + 1))
    up.update(placed)


def lock_house(grid, hs):
    """Makes hs the locked house: one of its front windows becomes the loose one (<Base>_Window002) and the floor inside
    it is cleared. Returns (the door cell, the window cell)."""
    x0, y0, w, h = hs["x0"], hs["y0"], hs["w"], hs["h"]
    y1 = y0 + h - 1
    wins = [x for x in range(x0 + 1, x0 + w - 1) if grid.get((x, y1)) == window_tile(hs["wall"])]
    wx = max(wins, key=lambda x: abs(x - hs["door"][0]))
    grid[(wx, y1)] = window_tile(hs["wall"], 2)
    inside = (wx, y1 - 1)
    if grid.get(inside) in FURNITURE:
        other = {"Bed001": (wx, y1), "Bed002": (wx, y1 - 2)}.get(grid[inside])   # (the other half of a bed too)
        if other and grid.get(other) in ("Bed001", "Bed002"):
            grid[other] = "Plank001"
        grid[inside] = "Plank001"
    return hs["door"], (wx, y1)


def upper_floors(houses, gw, gh):
    """{"mx,my,1": {(x, y) 1-based tile: tile}}: the upper floors of these houses, by the map above theirs."""
    out = {}
    for hs in houses:
        for (gx, gy), t in hs.get("upper", {}).items():
            mx, my = gx // gw, gy // gh
            out.setdefault("%d,%d,1" % (mx, my), {})[(gx - mx * gw + 1, gy - my * gh + 1)] = t
    return out
