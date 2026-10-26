"""Galaith, in its valley in the West Range (dev\\World Plan.md): its walls (white stone, burnt black on the side that
faces the dragon) with a barred gate onto the dragon's field, a back gate to the mine's mouth in the mountains behind
it, the scorched field and the dragon, and the pass (a gap in the peaks) where the barrier stands; the city inside the
walls is grown by settlements.py. And Wardhaven: a walled town on its island, its bridge from the mainland."""
from atlas import XT, YT, TW, h01
import land as LAND
import layout as L

# the walls, in world tiles: Galaith's valley is maps 1-6 by 11-14
WEST, EAST = 1 * XT + 1, 6 * XT + 22            # (the west wall: map 1's tile 2; the east: map 6's tile 23)
NORTH, SOUTH = 11 * YT + 1, 14 * YT + 18        # (the north wall's top row: map 11's tile 2; the south: map 14's 19)
GATE = 12 * YT + 10                             # (the gates' first row: tile 11 of maps 0-9,12, the pass's road)
MINE = (0 * XT + 22, GATE)                      # the mine's mouth: 0,12,0 tile 23,11 (you climb out at 24,11)
PASS = "9,12,0"
BARRIER_X = 19                                  # (the pass's tile column the barrier stands in)
FIELD = "7,12,0"                                # (the dragon's map: before the gate)


def peak(gx, gy):
    return "Peak%03d" % (1 + int(h01("pk", gx, gy) * 6))


def put(atlas, gx, gy, tile, decor=""):
    atlas.set(gx, gy, tile=tile, decor=decor)
    m, x, y = atlas.at(gx, gy)
    if m is not None:
        m.rows[y - 1][x - 1] = tile + ("+Decor(%s)" % decor if decor else "")
    LAND.GROUND[(gx, gy)], LAND.DECOR[(gx, gy)] = tile, decor


def inside(c):
    """Within Galaith's walls."""
    return WEST < c[0] < EAST and NORTH + 1 < c[1] < SOUTH


def walls(atlas):
    """The walls round the city, the mountains up to them outside, the gates; returns the cells kept clear inside."""
    for gy in range(10 * YT, 16 * YT):
        for gx in range(0, 7 * XT):
            c = (gx, gy)
            if L.macro(gx // XT, gy // YT) not in ("G", "M"):
                continue
            outside = gy < NORTH or gy > SOUTH + 1 or gx < WEST
            if outside and LAND.GROUND.get(c, "").startswith(("Grass", "Dirt", "Sand", "Water", "Scorched")):
                if not (gx < WEST and GATE <= gy <= GATE + 1 and gx >= MINE[0]):
                    put(atlas, gx, gy, peak(gx, gy))
            if gx > EAST and NORTH <= gy <= SOUTH + 1 and gx < 7 * XT:
                put(atlas, gx, gy, "Scorched%03d" % (1 + int(h01("sc", gx, gy) * 3)))
    for gx in range(WEST, EAST + 1):                                   # north and south walls
        burnt = gx >= EAST - 6
        for y0 in (NORTH, SOUTH):
            put(atlas, gx, y0, ("Burnt_Wall%03d" if burnt else "Galaith_Wall%03d") % 1)
            put(atlas, gx, y0 + 1, ("Burnt_Wall%03d" if burnt else "Galaith_Wall%03d") % 4)
    for gy in range(NORTH, SOUTH + 2):                                 # west and east walls
        put(atlas, WEST, gy, "Galaith_Wall002")
        put(atlas, EAST, gy, "Burnt_Wall002")
    for gx in (WEST, EAST):                                            # the corner towers
        for y0 in (NORTH, SOUTH):
            kind = "Burnt_Wall%03d" if gx == EAST else "Galaith_Wall%03d"
            put(atlas, gx, y0, kind % 3)
            put(atlas, gx, y0 + 1, kind % 5)
    for k in (0, 1):
        put(atlas, EAST, GATE + k, "Burnt_Gate005")                    # the gate onto the field: barred
        put(atlas, WEST, GATE + k, "Galaith_Gate006")                  # the back gate: open
        for gx in range(MINE[0] + 1, WEST):
            put(atlas, gx, GATE + k, "Dirt001")
            atlas.roads.add((gx, GATE + k))
    m, x, y = atlas.at(EAST, GATE)
    for k in (0, 1):
        m.ents.append("Lock\t%d\t%d\t$Attr.GalaithQuest>=2\tThe gate is barred. Something huge breathes behind you."
                      % (x, y + k))
    atlas.place_id(EAST - 1, GATE, "Galaith_West_Gate")
    put(atlas, MINE[0], MINE[1], "Mine_Mouth001")                      # the mine behind the city
    for gy in (MINE[1] - 1, MINE[1] + 1):
        put(atlas, MINE[0], gy, peak(MINE[0], gy))
    m, x, y = atlas.at(*MINE)
    m.ents.append("Lock\t%d\t%d\t$Attr.KingQuest>=1\tThe mine is shut, by the King's order." % (x, y))
    atlas.place_id(MINE[0] + 1, MINE[1], "Galaith_Mine")
    clear = set()
    for gx in range(WEST + 1, WEST + 4):                               # (the ways in from the gates, kept open)
        for k in (0, 1):
            clear.add((gx, GATE + k))
    for gx in range(EAST - 3, EAST):
        for k in (0, 1):
            clear.add((gx, GATE + k))
    for c in [(gx, gy) for gx in range(WEST, EAST + 1) for gy in (NORTH, NORTH + 1, SOUTH, SOUTH + 1)] + \
             [(gx, gy) for gx in (WEST, EAST) for gy in range(NORTH, SOUTH + 2)]:
        atlas.taken.add(c)
    return clear


def field(atlas):
    """The dragon's field (scorched, bones, dead trees: land.py drew it) and the dragon, before the gate."""
    gx0, gy0 = 7 * XT, 12 * YT
    m = atlas.maps[FIELD]
    m.ents.append("NPC\tGalaith_Dragon\t%d\t%d\tAttitude=Bad Zone=6,4,22,18 Chase=1,2,25,20 Id=Galaith_Dragon_Boss"
                  % (12 * TW, 9 * TW))
    for x, y in ((9, 7), (17, 14), (20, 5)):
        m.ents.append("MapItem\tBones\t%d\t%d\t1" % ((x - 1) * TW, (y - 1) * TW))
    atlas.place_id(gx0 + 12, gy0 + 10, "Dragons_Field")


def pass_(atlas):
    """The pass: peaks all down the pass's maps but a gap three tiles wide (wider away from the barrier), the road
    along it, the barrier (Barrier_Light, put by the map's entry script while it holds), its locks, the trigger where
    the dragon speaks."""
    for my in range(11, 15):
        for gy in range(my * YT, my * YT + YT):
            for gx in range(9 * XT, 10 * XT):
                lx = gx - 9 * XT + 1
                half = 1 if abs(lx - BARRIER_X) <= 2 else 2 + int(h01("pw", gx) * 2)
                if my == 12 and abs(gy - GATE - 0) <= half and gy - GATE >= -half and gy - GATE <= half:
                    if gy == GATE:
                        put(atlas, gx, gy, "Dirt001")
                        atlas.roads.add((gx, gy))
                    else:
                        put(atlas, gx, gy, "Dirt001" if h01("pd", gx, gy) < 0.5 else "Grass001")
                else:
                    put(atlas, gx, gy, peak(gx, gy))
    for k in (-1, 0, 1):                                               # (the barrier's tiles, under its light)
        put(atlas, 9 * XT + BARRIER_X - 1, GATE + k, "Barrier001")
    m = atlas.maps[PASS]
    for k in (-1, 0, 1):
        m.ents.append("Lock\t%d\t%d\t$Attr.GalaithQuest>=1\tThe barrier holds: violet light, hard as glass."
                      % (BARRIER_X, GATE % YT + 1 + k))
        m.ents.append("Trigger\tThe Dragon Speaks\t%d\t%d" % (BARRIER_X - 1, GATE % YT + 1 + k))
    atlas.place_id(9 * XT + BARRIER_X, GATE, "Galaith_Barrier")
    for gy in range(GATE - 1, GATE + 2):                               # (the field's side: the road on to the gate)
        for gx in range(7 * XT, 9 * XT):
            if gy == GATE:
                put(atlas, gx, gy, "Scorched001")


def barrier_rows():
    """The barrier's three tiles on the pass's map (1-based x, y)."""
    return [(BARRIER_X, GATE % YT + 1 + k) for k in (-1, 0, 1)]


# ------------------------------------------------------------------ Wardhaven
BRIDGE_X = 13 * XT + 12                         # (the bridge's west column: 13,y tile 13, the middle; two wide)


def is_land(c):
    g = LAND.GROUND.get(c, "")
    return bool(g) and not g.startswith(("Water", "Sand_Water", "Snow_Water", "Marsh_Water"))


def wardhaven(atlas):
    """Before the town's grown: the bridge from the mainland to the island's south shore, a wall across the island's
    south end with the gatehouse (barred till the goblins on the bridge are gone: quests.py, The Wardhaven Bridge; the
    sea round the rest). Returns (which cells the town may use, the gate's map, the bridge's mainland end, the bridge:
    {"gate": (x, y) outside the gate, "bridge": its planks, "shore": the way from it to the gate})."""
    x1, y1, x2, y2 = L.SETTLEMENTS["Wardhaven"]["maps"]
    cy = (y1 + y2 + 1) * YT // 2
    xs = (BRIDGE_X, BRIDGE_X + 1)
    y = cy
    while all(is_land((x, y + 1)) for x in xs):
        y += 1
    shore = y                                                            # (the island's last row going south)
    yb = shore + 1
    planks = []
    while not all(is_land((x, yb)) for x in xs) and yb < shore + 40:
        for x in xs:
            planks.append((x, yb))
            put(atlas, x, yb, "Plank001")
            atlas.roads.add((x, yb))
            atlas.taken.add((x, yb))
        yb += 1
    wall = shore - 3                                                     # (its battlements' row; its face below)
    span = [x for x in range(x1 * XT, (x2 + 1) * XT) if is_land((x, wall)) or is_land((x, wall + 1))]
    west, east = min(span), max(span)
    for x in range(west, east + 1):
        top, face = ("City_Wall003", "City_Wall005") if x in (west, east, xs[0] - 1, xs[1] + 1) else \
            ("City_Wall001", "City_Wall004")
        if x in xs:
            top, face = "City_Gate003", "City_Gate001"
        put(atlas, x, wall, top)
        put(atlas, x, wall + 1, face)
        atlas.taken.update({(x, wall), (x, wall + 1)})
    for x in xs:
        for gy in range(wall + 2, shore + 1):                             # (the way from the bridge to the gate)
            put(atlas, x, gy, "Cobble001")
            atlas.roads.add((x, gy))
            atlas.taken.add((x, gy))
        m, lx, ly = atlas.at(x, wall + 1)
        m.ents.append("Lock\t%d\t%d\t$Attr.WardhavenQuest>=3\tThe gates of Wardhaven are barred. Nobody answers "
                      "from the wall." % (lx, ly))
    gm = atlas.at(xs[0], wall + 2)[0]
    atlas.place_id(xs[0], wall + 2, "Wardhaven_Gate")
    if planks:
        atlas.place_id(*planks[len(planks) // 2], "Wardhaven_Bridge_Span")
    shore_cells = [(x, gy) for x in xs for gy in range(wall + 2, shore + 1)]
    return (lambda c: c[1] < wall), gm.name, (xs[0], yb), {"gate": (xs[0], wall + 2), "bridge": planks,
                                                           "shore": shore_cells}
