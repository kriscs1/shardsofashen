"""House materials for the generated villages (villages.py): walls, their doors and roofs. Used by build_tiles.py
through cave_tiles.TILES; each function returns a 32x32 opaque image (rows of (r, g, b)).

  * Walls (the front of a house, seen from the street): Timber001 (boards under a beam), Plaster001 (whitewash between
    dark timbers), Sandstone001 (big sandy blocks). Brick001 and Stone_Wall001 are the others.
  * Doors: Door004 / Door005 / Door006, the house door in those three walls (farm_tiles.door).
  * Roofs: four materials, each in 15 pieces, <Material>_Roof001-015, so a roof has eaves, a ridge and gable ends:
    piece = row * 3 + column + 1, rows T (top eave), U (upper slope), R (the ridge), D (lower slope), B (bottom eave),
    columns W (west gable), M (middle), E (east gable). villages.roof_piece() picks them; build_world.map_cells puts
    them on the map. The upper slope faces the light (top left), the lower one is in shade. 016-030: the same pieces
    with a chimney stack (and a wisp of smoke); 031 / 032: a dormer window on the lower slope / the bottom eave.
  * Windows and upper storeys, for each wall (Base = Brick, Stone_Wall, Timber, Plaster, Sandstone): <Base>_Window001
    (a window with a sill, a lintel or shutters), <Base>_Window002 (the same with a loose shutter and the casement
    open), <Base>_Window003 (001 upside down, for a front wall facing north), <Base>_Upper001 / 002 (the upper storey's front, with a window / plain: the eaves' shadow at the top, a jetty
    beam or a stone string course at the bottom).
"""
import os
import random
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from farm_tiles import S, to_rows, smooth_noise, door  # noqa: E402

ROOF_MATERIALS = ("Thatch", "Shingle", "Slate", "Clay", "Copper")     # (Copper: the banks' green roofs, build_cinder.py)
ROWS = "TURDB"
COLS = "WME"


def grain(rng, amp):
    return np.array([[rng.uniform(-amp, amp) for _ in range(S)] for _ in range(S)], dtype=np.float32)


# ---------------------------------------------------------------- walls
def timber_wall():
    rng = random.Random(1001)
    img = np.empty((S, S, 3), dtype=np.float32)
    img[:, :] = (112, 76, 44)
    ys, xs = np.mgrid[0:S, 0:S]
    board = xs // 8
    tone = np.array([rng.uniform(-14, 14) for _ in range(4)], dtype=np.float32)[board]
    img += tone[:, :, None]
    streak = np.array([[np.sin(y * 0.9 + rng.uniform(0, 6.3)) for y in range(S)] for _ in range(S)], dtype=np.float32).T
    img += (5 * streak + grain(rng, 4))[:, :, None]
    img[xs % 8 == 0] *= 0.55                                         # the gaps between the boards
    img[xs % 8 == 1] *= 1.12
    img[ys < 4] = np.array((82, 54, 32), dtype=np.float32) + grain(rng, 5)[ys < 4][:, None]   # the beam along the top
    img[ys == 4] *= 0.6
    img[ys >= 29] *= 0.7                                             # the sill
    return to_rows(img)


def plaster_wall():
    rng = random.Random(1002)
    img = np.empty((S, S, 3), dtype=np.float32)
    img[:, :] = (226, 214, 184)
    img += smooth_noise(rng, 7, 2)[:, :, None] + grain(rng, 3)[:, :, None]
    beam = np.array((76, 52, 34), dtype=np.float32)
    ys, xs = np.mgrid[0:S, 0:S]
    timber = (ys < 3) | (ys >= 29) | (xs < 2) | (xs >= 30)
    diag = np.abs((xs - 2) - (28 - ys) * 28 / 26.0) < 1.6             # a brace across each bay
    timber |= diag & (ys >= 3) & (ys < 29) & (xs >= 2) & (xs < 30)
    img[timber] = beam + grain(rng, 6)[timber][:, None]
    edge = ~timber & (np.roll(timber, 1, 0) | np.roll(timber, 1, 1))
    img[edge] *= 0.85                                                # the plaster in their shadow
    return to_rows(img)


def sandstone_wall():
    rng = random.Random(1003)
    img = np.empty((S, S, 3), dtype=np.float32)
    img[:, :] = (210, 176, 118)
    ys, xs = np.mgrid[0:S, 0:S]
    course = ys // 8
    off = (course % 2) * 8
    block = ((xs + off) // 16) % 2 + course * 2
    tones = np.array([rng.uniform(-14, 14) for _ in range(16)], dtype=np.float32)
    img += tones[block % 16][:, :, None] + grain(rng, 5)[:, :, None]
    joint = (ys % 8 == 7) | ((xs + off) % 16 == 15)
    img[joint] = np.array((168, 136, 88), dtype=np.float32)
    img[(ys % 8 == 0)] *= 1.08                                        # the tops of the blocks catch the light
    return to_rows(img)


# ---------------------------------------------------------------- roofs
def roof_texture(material):
    """The covering, without any shaping: rows of 8 pixels, repeating every 32 across and down."""
    rng = random.Random(1100 + ROOF_MATERIALS.index(material))
    ys, xs = np.mgrid[0:S, 0:S]
    img = np.empty((S, S, 3), dtype=np.float32)
    if material == "Thatch":
        img[:, :] = (190, 152, 76)
        for _ in range(420):                                         # straw: short strokes hanging down
            x, y = rng.randrange(S), rng.randrange(S)
            c = rng.uniform(-36, 30)
            for i in range(rng.randrange(3, 7)):
                img[(y + i) % S, x] += c * 0.5
        lay = (ys % 8) / 7.0
        img *= (0.82 + 0.26 * lay)[:, :, None]                       # each layer hangs over the one below
    elif material == "Shingle":
        img[:, :] = (124, 80, 50)
        off = (ys // 8 % 2) * 4
        piece = (xs + off) // 8 + (ys // 8) * 4
        tones = np.array([rng.uniform(-18, 18) for _ in range(16)], dtype=np.float32)
        img += tones[piece % 16][:, :, None] + grain(rng, 6)[:, :, None]
        img[(xs + off) % 8 == 0] *= 0.6
        img *= (0.8 + 0.3 * ((ys % 8) / 7.0))[:, :, None]
    elif material == "Slate":
        img[:, :] = (86, 94, 108)
        off = (ys // 8 % 2) * 5
        piece = (xs + off) // 8 + (ys // 8) * 5
        tones = np.array([rng.uniform(-12, 12) for _ in range(20)], dtype=np.float32)
        img += tones[piece % 20][:, :, None] + grain(rng, 4)[:, :, None]
        img[(xs + off) % 8 == 0] *= 0.62
        img *= (0.78 + 0.32 * ((ys % 8) / 7.0))[:, :, None]
        img[ys % 8 == 7] += np.array((14, 14, 18), dtype=np.float32)  # the lower edge of each slate catches the light
    elif material == "Copper":                                       # verdigris sheets: standing seams every 8
        img[:, :] = (92, 158, 132)
        img += smooth_noise(rng, 6, 10)[:, :, None] * np.array((0.6, 1.0, 0.8), dtype=np.float32)
        img += grain(rng, 3)[:, :, None]
        img[xs % 8 == 0] = img[xs % 8 == 0] * 0.6 + np.array((40, 70, 58), dtype=np.float32) * 0.4
        img[xs % 8 == 1] *= 1.18
        img[(ys % 16 == 15)] *= 0.85                                 # where one sheet laps over the next
        brown = smooth_noise(rng, 1, 3) > 0.7                        # a little bare copper showing through
        img[brown] = img[brown] * 0.75 + np.array((176, 120, 70), dtype=np.float32) * 0.25
    else:                                                            # Clay: rows of round tiles, channels every 8
        img[:, :] = (178, 86, 52)
        round_ = np.cos((xs % 8 - 3.5) / 4.0 * np.pi / 1.15)
        img *= (0.72 + 0.36 * round_)[:, :, None]
        img += grain(rng, 5)[:, :, None]
        img *= (0.8 + 0.28 * ((ys % 8) / 7.0))[:, :, None]
    return img


def roof_piece(material, row, col):
    img = roof_texture(material).copy()
    ys, xs = np.mgrid[0:S, 0:S]
    light, shade = 1.1, 0.8                                          # the upper slope faces the light
    if row in "TU":
        img *= light
    elif row in "DB":
        img *= shade
    else:                                                            # the ridge: light above, shade below, a capping
        img[ys < 15] *= light
        img[ys >= 15] *= shade
        cap = (ys >= 13) & (ys <= 17)
        img[cap] = img[cap] * 0.55 + np.array({"Thatch": (150, 116, 56), "Shingle": (96, 60, 36),
                                               "Slate": (70, 74, 84), "Clay": (150, 70, 44),
                                               "Copper": (196, 160, 70)}[material]) * 0.45
        img[ys == 13] *= 1.25
        img[ys == 17] *= 0.65
    if row == "T":                                                   # the top eave: a lit edge
        img[ys == 0] *= 0.6
        img[ys == 1] *= 1.2
    if row == "B":                                                   # the bottom eave: the edge, dark under it
        img[ys >= 29] *= 0.7
        img[ys == 31] *= 0.6
    if col == "W":                                                   # the gable ends: a verge board
        img[xs < 2] *= 0.75
        img[xs == 2] *= 1.15
    if col == "E":
        img[xs >= 29] *= 0.62
    return to_rows(img)


# ---------------------------------------------------------------- windows, upper storeys, chimneys and dormers
# Each wall material has <Base>_Window001 (a window in the ground-floor front wall), <Base>_Window002 (the same with a
# shutter hanging loose and the casement open: one house's way in, villages.LOCKED_HOUSE), <Base>_Upper001 (the upper
# storey with a window, drawn as part of the roof so it hides with it) and <Base>_Upper002 (the upper storey, plain).
WALL_BASES = {"Brick001": "Brick", "Stone_Wall001": "Stone_Wall", "Timber001": "Timber", "Plaster001": "Plaster",
              "Sandstone001": "Sandstone"}
WOODEN = {"Timber001", "Plaster001"}             # jettied upper storeys and painted shutters
SHUTTERS = {"Timber001": (64, 104, 72), "Plaster001": (70, 94, 126), "Brick001": (60, 82, 60)}
FRAME = {"Timber001": (226, 214, 190), "Plaster001": (88, 60, 38), "Brick001": (232, 226, 210),
         "Stone_Wall001": (196, 188, 170), "Sandstone001": (232, 210, 160)}


def wall_image(wall):
    from farm_tiles import tile_array
    from common import p
    return tile_array(p("sprites", "Tiles", wall + ".png"))


def draw_window(img, wall, x0, y0, x1, y1, loose=False, flowers=False):
    """A window: frame x0..x1, y0..y1, a sill under it, shutters on wooden and brick walls. loose: the right shutter
    hangs by one hinge and the casement stands open (dark inside)."""
    ys, xs = np.mgrid[0:S, 0:S]
    frame = np.array(FRAME[wall], dtype=np.float32)
    if wall not in WOODEN:                                           # a lintel stone over it
        lint = (ys >= y0 - 3) & (ys < y0) & (xs >= x0 - 2) & (xs <= x1 + 2)
        img[lint] = img[lint] * 0.35 + np.array((200, 192, 176), dtype=np.float32) * 0.65
        img[(ys == y0 - 3) & lint] *= 1.12
    sh = SHUTTERS.get(wall)
    if sh:
        for side, (a, b) in (("L", (x0 - 6, x0 - 1)), ("R", (x1 + 1, x1 + 6))):
            if loose and side == "R":
                continue
            m = (xs >= a) & (xs <= b) & (ys >= y0) & (ys <= y1)
            img[m] = np.array(sh, dtype=np.float32)
            img[m & ((ys - y0) % 4 == 0)] *= 0.78                    # the slats
            img[m & (xs == a)] *= 1.18
            img[m & (xs == b)] *= 0.7
    box = (xs >= x0) & (xs <= x1) & (ys >= y0) & (ys <= y1)
    img[box] = frame
    inner = (xs > x0) & (xs < x1) & (ys > y0) & (ys < y1)
    if loose:
        t = (ys - y0) / float(max(1, y1 - y0))
        dark = np.stack([22 + 10 * t, 18 + 8 * t, 16 + 6 * t], axis=-1).astype(np.float32)
        img[inner] = dark[inner]
    else:
        t = (ys - y0) / float(max(1, y1 - y0))
        glass = np.stack([84 - 40 * t, 104 - 46 * t, 132 - 50 * t], axis=-1).astype(np.float32)
        img[inner] = glass[inner]
        shine = inner & (np.abs((xs - x0) + (ys - y0) - 9) < 1.5)
        img[shine] = img[shine] * 0.4 + np.array((200, 214, 228), dtype=np.float32) * 0.6
        img[inner & (ys == y0 + 1)] *= 0.6                           # the recess: shadow under the head and the
        img[inner & (xs == x0 + 1)] *= 0.72                          # left jamb
        mx, my = (x0 + x1) // 2, (y0 + y1) // 2
        img[inner & ((xs == mx) | (ys == my))] = frame * 0.92        # the glazing bars
    img[box & ~inner & ((xs == x0) | (ys == y0))] = frame * 1.08
    img[box & ~inner & ((xs == x1) | (ys == y1))] = frame * 0.7
    sill = (ys >= y1 + 1) & (ys <= y1 + 2) & (xs >= x0 - 2) & (xs <= x1 + 2)
    img[sill] = np.array((214, 206, 190) if wall not in WOODEN else (120, 82, 50), dtype=np.float32)
    img[sill & (ys == y1 + 1)] *= 1.15
    img[sill & (ys == y1 + 2)] *= 0.72
    under = (ys == y1 + 3) & (xs >= x0 - 1) & (xs <= x1 + 2)
    img[under] *= 0.62                                               # the sill's shadow
    if flowers:                                                      # a window box of geraniums
        rng = random.Random(3000 + x0 + y0)
        bx = (xs >= x0 - 1) & (xs <= x1 + 1) & (ys >= y1 - 1) & (ys <= y1 + 2)
        img[bx] = np.array((110, 72, 44), dtype=np.float32)
        img[bx & (ys == y1 - 1)] *= 1.2
        for x in range(x0 - 1, x1 + 2):
            for y in (y1 - 4, y1 - 3, y1 - 2):
                if rng.random() < 0.75:
                    img[y, x] = rng.choice([(70, 130, 56), (52, 104, 44), (204, 52, 60), (232, 84, 96), (88, 150, 64)])
    if loose and sh:                                                 # the loose shutter, hanging askew
        for y in range(y0 + 2, y1 + 4):
            for k in range(6):
                x = x1 + 1 + k
                yy = y + int(k * 0.8)
                if 0 <= yy < S and 0 <= x < S:
                    c = np.array(sh, dtype=np.float32) * (0.92 if (y - y0) % 4 else 0.72)
                    img[yy, x] = c * (1.15 if k == 0 else 0.8 if k == 5 else 1)
    elif loose:                                                      # the casement swung out
        for y in range(y0 + 1, y1):
            for k in range(4):
                x = x1 + 1 + k
                if x < S:
                    img[y, x] = frame * (0.95 if k in (0, 3) else 0.5)
    return img


def window_wall(wall, loose=False):
    img = wall_image(wall).copy()
    return to_rows(draw_window(img, wall, 10, 8, 21, 21, loose=loose))


def turned_window(wall):
    """<Base>_Window003: the window upside down (its sill at the top), for a house whose front faces north; the wall
    round it stays the right way up."""
    plain = wall_image(wall).copy()
    win = np.array(window_wall(wall), dtype=np.float32)
    m = np.flipud(np.abs(win - plain).sum(2) > 6)
    img = plain.copy()
    img[m] = np.flipud(win)[m]
    return to_rows(img)


def upper_wall(wall, window):
    """The upper storey of a house's front, under the eaves: in shadow at the top, and a jettied beam (wooden houses) or
    a string course of stone (the others) along the floor line."""
    img = wall_image(wall).copy()
    ys, xs = np.mgrid[0:S, 0:S]
    if window:
        draw_window(img, wall, 10, 9, 21, 21, flowers=(wall == "Plaster001" or wall == "Timber001"))
    for y in range(6):                                               # the eaves' shadow
        img[y] *= 0.42 + 0.1 * y
    if wall in WOODEN:
        beam = ys >= 27
        img[beam] = np.array((86, 56, 34), dtype=np.float32)
        img[ys == 27] *= 1.3
        img[ys == 31] *= 0.55
        img[(ys >= 28) & (ys <= 30) & (xs % 8 < 3)] = np.array((64, 42, 26), dtype=np.float32)   # the joist ends
        img[(ys == 28) & (xs % 8 < 3)] *= 1.25
    else:
        band = (ys >= 27) & (ys <= 30)
        mean = img.reshape(-1, 3).mean(0)
        img[band] = mean * 1.18
        img[ys == 27] *= 1.12
        img[band & (xs % 12 == 0)] *= 0.75
        img[ys == 31] = mean * 0.5
    return to_rows(img)


CHIMNEY = {"Thatch": (150, 140, 128), "Shingle": (160, 82, 60), "Slate": (128, 124, 120), "Clay": (170, 96, 66),
           "Copper": (210, 204, 190)}


def add_chimney(img, material):
    """A chimney stack standing up out of the roof, with a wisp of smoke."""
    ys, xs = np.mgrid[0:S, 0:S]
    shadow = (xs >= 21) & (xs <= 27) & (ys >= 11) & (ys <= 28) & (xs - 21 <= (ys - 11))
    img[shadow] *= 0.6                                               # cast down and right (light from the top left)
    base = np.array(CHIMNEY[material], dtype=np.float32)
    face = (xs >= 11) & (xs <= 20) & (ys >= 10) & (ys <= 25)
    img[face] = base
    img[face & (ys % 4 == 1)] *= 0.72                                # mortar
    img[face & (((xs + (ys // 4) * 3) % 6) == 0)] *= 0.8
    img[face & (xs == 11)] *= 1.15
    side = (xs >= 21) & (xs <= 22) & (ys >= 9) & (ys <= 24)
    img[side] = base * 0.55
    cap = (xs >= 10) & (xs <= 22) & (ys >= 6) & (ys <= 9)
    img[cap] = base * 1.25
    img[cap & (ys == 9)] = base * 0.6
    flue = (xs >= 12) & (xs <= 19) & (ys >= 7) & (ys <= 8)
    img[flue] = np.array((26, 20, 18), dtype=np.float32)
    img[(ys == 25) & (xs >= 11) & (xs <= 22)] *= 0.6                 # where the stack meets the roof
    for (cx, cy, r, a) in ((17, 4, 2.6, 0.55), (21, 1.5, 2.4, 0.4), (25, 0, 2.0, 0.28)):
        puff = (xs - cx) ** 2 + (ys - cy) ** 2 <= r * r
        img[puff] = img[puff] * (1 - a) + np.array((214, 214, 220), dtype=np.float32) * a
    return img


def add_dormer(img, material):
    """A dormer window on the lower slope: a little gabled roof over a window (the attic is lived in)."""
    ys, xs = np.mgrid[0:S, 0:S]
    tex = roof_texture(material)
    shadow = (xs >= 24) & (xs <= 28) & (ys >= 9) & (ys <= 30)
    img[shadow] *= 0.62
    front = (xs >= 9) & (xs <= 22) & (ys >= 15) & (ys <= 30)
    img[front] = np.array((222, 210, 182), dtype=np.float32)
    img[front & (ys == 30)] *= 0.7
    win = (xs >= 12) & (xs <= 19) & (ys >= 18) & (ys <= 28)
    t = (ys - 18) / 10.0
    glass = np.stack([80 - 36 * t, 100 - 42 * t, 128 - 46 * t], axis=-1).astype(np.float32)
    img[win] = glass[win]
    img[win & ((xs == 15) | (ys == 23))] = np.array((88, 60, 38), dtype=np.float32)
    img[win & ((xs == 12) | (xs == 19) | (ys == 18) | (ys == 28))] = np.array((96, 64, 40), dtype=np.float32)
    for y in range(3, 17):                                           # the gable: lit west half, shaded east half
        half = (y - 3) * 0.95 + 1
        for x in range(S):
            d = x + 0.5 - 16
            if abs(d) <= half:
                c = tex[y, x] * (1.12 if d < 0 else 0.72)
                if abs(d) > half - 1.2:
                    c = c * 0.55                                     # the verge boards
                img[y, x] = c
    img[(ys == 16) & (xs >= 3) & (xs <= 28)] *= 0.55
    return img


def roof_extra(material, row, col, extra):
    img = np.array(roof_piece(material, row, col), dtype=np.float32)
    return to_rows(add_chimney(img, material) if extra == "chimney" else add_dormer(img, material))


TILES = {
    "Timber001": timber_wall,
    "Plaster001": plaster_wall,
    "Sandstone001": sandstone_wall,
    "Door004": lambda: door("Timber001", (84, 56, 34), (58, 38, 22)),
    "Door005": lambda: door("Plaster001", (76, 52, 34), (54, 36, 22)),
    "Door006": lambda: door("Sandstone001", (186, 152, 98), (150, 120, 76)),
}
for _m in ROOF_MATERIALS:
    for _r, _row in enumerate(ROWS):
        for _c, _col in enumerate(COLS):
            TILES["%s_Roof%03d" % (_m, _r * 3 + _c + 1)] = (lambda m=_m, row=_row, col=_col: roof_piece(m, row, col))
            # 016-030: the same piece with a chimney stack on it
            TILES["%s_Roof%03d" % (_m, 15 + _r * 3 + _c + 1)] = (
                lambda m=_m, row=_row, col=_col: roof_extra(m, row, col, "chimney"))
    # 031 / 032: a dormer window on the middle of the lower slope / of the bottom eave
    TILES["%s_Roof031" % _m] = (lambda m=_m: roof_extra(m, "D", "M", "dormer"))
    TILES["%s_Roof032" % _m] = (lambda m=_m: roof_extra(m, "B", "M", "dormer"))

# ---------------------------------------------------------------- doors facing other ways
# Every door is drawn with its foot at the bottom (the street below the house's front wall). A door in a wall with the
# outside to the north, west or east is the same door turned so its foot faces out, on the wall's texture the right
# way up. DOOR_TURNS[(door, side the outside is on)] = the turned tile; build_content.door_facing picks them.
DOOR_WALLS = {"Door001": "Brick001", "Door002": "Stone_Wall001", "Door003": "Cave_Wall002", "Door004": "Timber001",
              "Door005": "Plaster001", "Door006": "Sandstone001"}
DOOR_SIDES = {"N": 2, "W": -1, "E": 1}              # np.rot90 turns: N = upside down, W = a quarter clockwise
DOOR_TURNS = {(d, side): "Door%03d" % (7 + i * 3 + j)
              for i, d in enumerate(DOOR_WALLS) for j, side in enumerate(DOOR_SIDES)}


def tile_image(name):
    """A tile as it will be built (from its maker if a builder draws it, else its sprite)."""
    from farm_tiles import TILES as FARM_TILES, tile_array
    from common import p
    make = TILES.get(name) or FARM_TILES.get(name)
    if make:
        return np.array(make(), dtype=np.float32)
    return tile_array(p("sprites", "Tiles", name + ".png"))


# Every door fills its whole tile: a post of the wall's stone (or timber) either side and the door between, the same
# seen from inside or out, so it serves a doorway whichever side the street is on. 007-024 are the same turned to
# stand in a west or east wall (and north, for old maps).
DOOR_FRAMES = {"Door001": ((182, 174, 160), (140, 132, 120)), "Door002": ((150, 146, 138), (104, 100, 94)),
               "Door003": ((96, 86, 76), (62, 56, 50)), "Door004": ((96, 64, 38), (62, 40, 24)),
               "Door005": ((86, 60, 40), (58, 38, 24)), "Door006": ((190, 156, 102), (150, 120, 76))}
POST = 4                                            # each post's width: the door is x 4-27


# Painted doors (village_decor gives each house its own): the same doors with the planks painted
PAINTS = {"Green": (58, 98, 62), "Blue": (56, 80, 120), "Red": (134, 48, 42)}
PAINTED = {}                                        # (door, paint): its tile, Door025-042


def full_door(door_name, paint=None):
    rng = random.Random(500 + int(door_name[-3:]))
    frame, frame_dark = (np.array(c, dtype=np.float32) for c in DOOR_FRAMES[door_name])
    ys, xs = np.mgrid[0:S, 0:S]
    img = np.empty((S, S, 3), dtype=np.float32)
    # the posts: dressed blocks (or a timber jamb), lit on the left, shaded on the right
    img[:, :] = frame
    img += np.array([[rng.uniform(-6, 6) for _ in range(S)] for _ in range(S)], dtype=np.float32)[:, :, None]
    img[(ys % 8 == 7)] = frame_dark
    img[xs == 0] *= 1.12
    img[xs == POST - 1] = frame_dark * 0.8
    img[xs == S - POST] = frame_dark * 0.8
    img[xs == S - 1] *= 0.85
    # the door: oak planks, iron bands with studs, a ring handle and a keyhole
    leaf = (xs >= POST) & (xs < S - POST)
    plank = (xs - POST) // 6
    oak = np.array(PAINTS[paint] if paint else (112, 70, 38), dtype=np.float32)
    grain = np.sin(ys * 0.9 + plank * 1.7 + np.array([[rng.uniform(0, 0.8) for _ in range(S)] for _ in range(S)]))
    wood = oak * (1 + 0.07 * grain)[:, :, None] * (1 + 0.05 * (plank % 2))[:, :, None]
    img[leaf] = wood[leaf]
    img[leaf & ((xs - POST) % 6 == 0)] = oak * 0.55                 # the joins between the planks
    img[leaf & ((xs - POST) % 6 == 1)] *= 1.08
    for y0 in (5, 24):                                               # two iron bands, near the top and the bottom
        band = leaf & (ys >= y0) & (ys <= y0 + 2)
        img[band] = (58, 56, 58)
        img[leaf & (ys == y0)] = (92, 90, 92)
        for x in range(POST + 3, S - POST - 1, 6):
            img[y0 + 1, x] = (150, 146, 140)
    img[14:19, 21:24] = (196, 156, 62)                               # the ring handle
    img[15:18, 22] = (112, 70, 38)
    img[14, 21:24] = (236, 200, 110)
    img[21:23, 22] = (30, 22, 18)                                    # the keyhole
    return np.clip(img, 0, 255)


def turned_door(door_name, side):
    return to_rows(np.rot90(full_door(door_name), DOOR_SIDES[side]))


for _d in DOOR_WALLS:
    TILES[_d] = (lambda d=_d: to_rows(full_door(d)))


for (_d, _s), _n in DOOR_TURNS.items():
    TILES[_n] = (lambda d=_d, s=_s: turned_door(d, s))


# ---------------------------------------------------------------- doors standing open
# Door_Open<n> is Door<n> open: the doorway dark inside (lighter at the threshold, where the daylight falls in) and the
# door swung back against its hinge, seen edge on. The game shows it while someone is in the doorway (Tiles.ini
# Open.Tile) and shuts it again after.
def door_shape():
    ys, xs = np.mgrid[0:S, 0:S]
    return (xs >= POST) & (xs < S - POST)


def open_door_upright(door_name, paint=None):
    """A door (Door001-006) standing open: the doorway's floor between the posts, lighter at both ends where the
    daylight and the room's light fall in, the door swung back against its hinge."""
    img = full_door(door_name, paint).copy()
    m = door_shape()
    ys, xs = np.mgrid[0:S, 0:S]
    f = (np.abs(ys - (S - 1) / 2.0) / ((S - 1) / 2.0)).clip(0, 1)[:, :, None]
    inside = np.array((22, 17, 13), dtype=np.float32) * (1 - f) + np.array((66, 50, 36), dtype=np.float32) * f
    rng = random.Random(77)
    inside += np.array([[rng.uniform(-3, 3) for _ in range(S)] for _ in range(S)], dtype=np.float32)[:, :, None]
    wood = img[m].mean(0) if m.any() else np.array((110, 70, 40), dtype=np.float32)
    img[m] = inside[m]
    cols = np.where(m.any(0))[0]
    x0 = cols.min()
    leaf = m & (xs < x0 + 5)                        # the door, swung back against the hinge (on the left)
    img[leaf] = wood * 0.72
    img[leaf & (xs == x0 + 4)] = np.minimum(255, wood * 1.18)       # its edge catches the light
    img[leaf & (xs == x0)] = wood * 0.5
    img[m & (xs == x0 + 5)] = inside[m & (xs == x0 + 5)] * 0.6      # its shadow on the floor inside
    return img


def open_door(name):
    if name in DOOR_WALLS:
        return to_rows(open_door_upright(name))
    painted = next((k for k, v in PAINTED.items() if v == name), None)
    if painted:
        return to_rows(open_door_upright(*painted))
    door_name, side = next(k for k, v in DOOR_TURNS.items() if v == name)
    return to_rows(np.rot90(open_door_upright(door_name), DOOR_SIDES[side]))


for _i, _p in enumerate(PAINTS):
    for _j, _d in enumerate(DOOR_WALLS):
        _n = 7 + 3 * len(DOOR_WALLS) + _i * len(DOOR_WALLS) + _j         # Door025-042
        PAINTED[(_d, _p)] = "Door%03d" % _n
        TILES["Door%03d" % _n] = (lambda d=_d, c=_p: to_rows(full_door(d, c)))
DOOR_OPEN = {"Door%03d" % n: "Door_Open%03d" % n for n in range(1, 7 + 3 * len(DOOR_WALLS) + len(PAINTED))}
for _d, _o in DOOR_OPEN.items():
    TILES[_o] = (lambda d=_d: open_door(d))
for _w, _b in WALL_BASES.items():
    TILES["%s_Window001" % _b] = (lambda w=_w: window_wall(w))
    TILES["%s_Window002" % _b] = (lambda w=_w: window_wall(w, loose=True))
    TILES["%s_Window003" % _b] = (lambda w=_w: turned_window(w))
    TILES["%s_Upper001" % _b] = (lambda w=_w: upper_wall(w, True))
    TILES["%s_Upper002" % _b] = (lambda w=_w: upper_wall(w, False))


# ---------------------------------------------------------------- thin walls inside a house
# Under a house's roof, its side and back walls take a whole tile each, which leaves the rooms poky. These are the
# floor with the wall as a strip along the outside edge(s) (a little over a quarter of the tile), so the room runs out
# nearly to the wall: <Wall>_Thin_<Floor>001-008, the strip on the N, E, S, W side or the NE, SE, SW, NW corner.
# build_content.thin_walls() puts them in place of the wall tiles under every roof.
THIN_EDGES = ["N", "E", "S", "W", "NE", "SE", "SW", "NW"]
THIN_FLOORS = {"Plank001": "Plank", "Tile001": "Tile", "Marble001": "Marble"}
THIN_PX = 9                                         # the strip's width (2 of the 7 walk cells)


def thin_name(wall, floor, edges):
    """The thin-wall tile for the wall tile, the floor tile and the edges ("N", "SW"...), or None."""
    if wall not in WALL_BASES or floor not in THIN_FLOORS or edges not in THIN_EDGES:
        return None
    return "%s_Thin_%s%03d" % (WALL_BASES[wall], THIN_FLOORS[floor], THIN_EDGES.index(edges) + 1)


def thin_walk(edges):
    rows = []
    for y in range(7):
        rows.append("".join("0" if ("N" in edges and y < 2) or ("S" in edges and y > 4) or
                                   ("W" in edges and x < 2) or ("E" in edges and x > 4) else "1" for x in range(7)))
    return "".join(rows)


def thin_wall(wall, floor, edges):
    img = tile_image(floor).copy()
    w = tile_image(wall)
    ys, xs = np.mgrid[0:S, 0:S]
    t = THIN_PX
    strip = np.zeros((S, S), dtype=bool)
    if "N" in edges:
        strip |= ys < t
    if "S" in edges:
        strip |= ys >= S - t
    if "W" in edges:
        strip |= xs < t
    if "E" in edges:
        strip |= xs >= S - t
    img[strip] = w[strip]
    # the wall's top lit along its inner face, its shadow on the floor beside it
    inner = np.zeros((S, S), dtype=bool)
    shade = np.zeros((S, S), dtype=bool)
    for side, face, sh1, sh2 in (("N", ys == t - 1, ys == t, ys == t + 1), ("S", ys == S - t, ys == S - t - 1,
                                                                       ys == S - t - 2),
                                 ("W", xs == t - 1, xs == t, xs == t + 1), ("E", xs == S - t, xs == S - t - 1,
                                                                       xs == S - t - 2)):
        if side in edges:
            inner |= face & strip
            shade |= sh1 & ~strip
            img[sh2 & ~strip] *= 0.82
    img[inner] = np.minimum(255, img[inner] * 0.7)
    img[shade] *= 0.6
    return to_rows(img)


for _w in WALL_BASES:
    for _f in THIN_FLOORS:
        for _e in THIN_EDGES:
            TILES[thin_name(_w, _f, _e)] = (lambda w=_w, f=_f, e=_e: thin_wall(w, f, e))
