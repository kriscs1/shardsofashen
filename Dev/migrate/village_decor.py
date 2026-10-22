"""Character for the houses and the villages round them: each house front gets its own mix of a painted door, window
boxes, ivy, a lantern by the door and (a shop) a hanging sign for its trade, and the ground in front flower beds,
a bench, a lamp post or a barrel. Seeded by the map and the house, so the same build always gives the same village.

Tiles (drawn here; Tiles.ini entries in TILE_DATA, put in by build_content):
  * <Base>_Ivy001-003: the wall with ivy climbing it (from the left, all over, from the right)
  * <Base>_Window004 / 005: the window with a box of flowers under it / with ivy round it
  * <Base>_Lamp001: the wall with an iron lantern on a bracket, lit
  * <Base>_Sign001-008: the wall with a hanging sign: SIGNS (bread, coin, anvil, sack, potion, fish, hammer, crown)
  * Flower_Bed001-003, Bench001, Lamp_Post001: on grass in front of the houses
  * Painted doors (Door025-042: house_tiles.PAINTED) go in place of the plain ones.
dress_villages() runs in build_content.extend, on every map's rows once the houses are built and furnished.
"""
import os
import random
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from farm_tiles import S, to_rows  # noqa: E402
import house_tiles as H  # noqa: E402

YS, XS = np.mgrid[0:S, 0:S]
LEAVES = [(34, 84, 38), (46, 108, 44), (66, 134, 56), (90, 154, 70)]
SIGNS = ["Bread", "Coin", "Anvil", "Sack", "Potion", "Fish", "Hammer", "Crown"]
SIGN_OF_NPC = {"Baker": "Bread", "Banker": "Coin", "Blacksmith": "Anvil", "Trader": "Sack", "Shopkeeper": "Sack",
               "Herbalist": "Potion", "Fisherman": "Fish"}
SIGN_OF_OBJECT = {"Anvil": "Anvil", "Furnace": "Anvil", "Workbench": "Hammer", "Range": "Bread",
                  "Alchemy_Table": "Potion"}


def C(c):
    return np.array(c, dtype=np.float32)


def base_name(wall):
    return H.WALL_BASES[wall]


# ------------------------------------------------------------------------------------------------- ivy
def grow_ivy(img, rng, starts, height, spread, density):
    """Vines from the start points up the tile, wandering a little, leaves along them."""
    for sx in starts:
        x, y = float(sx), float(S - 1)
        top = S - height
        while y > top:
            ix, iy = int(round(x)), int(round(y))
            if 0 <= ix < S and 0 <= iy < S:
                img[iy, ix] = C((70, 52, 30))                            # the stem
            if rng.random() < density:
                for _ in range(rng.randint(2, 4)):                       # a cluster of leaves
                    lx, ly = ix + rng.randint(-2, 2), iy + rng.randint(-2, 1)
                    col = C(rng.choice(LEAVES))
                    for dx, dy in ((0, 0), (1, 0), (0, 1), (1, 1)):
                        if 0 <= lx + dx < S and 0 <= ly + dy < S and rng.random() < 0.85:
                            img[ly + dy, lx + dx] = col * (0.8 if dy else 1.0)
                    if 0 <= lx < S and 0 <= ly - 1 < S:
                        img[ly - 1, lx] = C((22, 54, 26))                # a dark edge on top
            x += rng.uniform(-spread, spread)
            y -= rng.uniform(0.6, 1.2)
    return img


def ivy_wall(wall, kind):
    rng = random.Random(7100 + kind * 13 + len(wall))
    img = H.wall_image(wall).copy()
    if kind == 1:
        starts, height = [1, 4, 8], 30
    elif kind == 2:
        starts, height = [2, 7, 12, 17, 22, 27, 30], 32
    else:
        starts, height = [S - 2, S - 5, S - 9], 30
    return to_rows(grow_ivy(img, rng, starts, height, 1.1, 0.55 if kind != 2 else 0.7))


def ivy_window(wall):
    rng = random.Random(7300 + len(wall))
    img = H.draw_window(H.wall_image(wall).copy(), wall, 10, 8, 21, 21)
    keep = img.copy()
    grow_ivy(img, rng, [2, 5, 26, 29], 32, 1.0, 0.6)
    win = (XS >= 11) & (XS <= 20) & (YS >= 9) & (YS <= 20)               # the glass stays clear
    img[win] = keep[win]
    return to_rows(img)


def flower_window(wall):
    return to_rows(H.draw_window(H.wall_image(wall).copy(), wall, 10, 8, 21, 21, flowers=True))


# ------------------------------------------------------------------------------------------------- the lantern
def lamp_wall(wall):
    img = H.wall_image(wall).copy()
    glow = np.exp(-(((XS - 17) ** 2 + (YS - 15) ** 2) / 60.0))[:, :, None]
    img = img * (1 + 0.45 * glow) + C((60, 34, 0)) * glow                # warm light on the wall round it
    iron = C((40, 38, 40))
    img[7:9, 6:18] = iron                                               # the bracket
    img[7, 6:18] = C((80, 78, 80))
    img[9:11, 6:8] = iron
    img[9, 16:18] = iron
    img[10:12, 15:20] = iron                                            # the lantern's cap
    img[12:20, 14:21] = C((255, 214, 120))                              # its glass, lit
    img[14:18, 16:19] = C((255, 244, 200))
    img[12:20, 14] = iron
    img[12:20, 20] = iron
    img[12:20, 17] = iron * 1.4
    img[20:22, 14:21] = iron
    img[22, 16:19] = iron
    return to_rows(np.clip(img, 0, 255))


# ------------------------------------------------------------------------------------------------- shop signs
def sign_icon(img, kind, cx, cy):
    def disc(x0, y0, r):
        return (XS - x0) ** 2 + (YS - y0) ** 2 <= r * r
    if kind == "Bread":
        m = ((XS - cx) / 6.5) ** 2 + ((YS - cy) / 3.6) ** 2 <= 1
        img[m] = C((200, 140, 70))
        img[m & (YS < cy - 1)] = C((222, 168, 92))
        for k in (-3, 0, 3):
            img[cy - 2:cy + 1, cx + k] = C((150, 96, 44))
    elif kind == "Coin":
        img[disc(cx, cy, 5)] = C((168, 128, 30))
        img[disc(cx, cy, 4)] = C((230, 190, 60))
        img[disc(cx - 1, cy - 1, 2)] = C((255, 230, 140))
    elif kind == "Anvil":
        img[cy - 3:cy - 1, cx - 6:cx + 5] = C((70, 70, 76))
        img[cy - 3, cx - 7:cx - 5] = C((70, 70, 76))
        img[cy - 1:cy + 2, cx - 2:cx + 2] = C((60, 60, 66))
        img[cy + 2:cy + 4, cx - 4:cx + 4] = C((70, 70, 76))
        img[cy - 3, cx - 6:cx + 5] = C((120, 120, 128))
    elif kind == "Sack":
        m = ((XS - cx) / 5.0) ** 2 + ((YS - cy - 1) / 4.2) ** 2 <= 1
        img[m] = C((196, 166, 112))
        img[m & (XS > cx + 1)] = C((168, 138, 90))
        img[cy - 5:cy - 3, cx - 1:cx + 2] = C((196, 166, 112))
        img[cy - 3, cx - 2:cx + 3] = C((110, 76, 40))
    elif kind == "Potion":
        img[disc(cx, cy + 1, 4)] = C((70, 160, 80))
        img[disc(cx - 1, cy, 1)] = C((170, 230, 170))
        img[cy - 5:cy - 2, cx - 1:cx + 2] = C((180, 200, 210))
        img[cy - 6, cx - 1:cx + 2] = C((120, 80, 40))
    elif kind == "Fish":
        m = ((XS - cx + 1) / 5.0) ** 2 + ((YS - cy) / 2.6) ** 2 <= 1
        img[m] = C((120, 150, 176))
        img[m & (YS > cy)] = C((90, 116, 140))
        for k in range(4):
            img[cy - k:cy + k + 1, cx + 4 + k] = C((100, 130, 156))
        img[cy - 1, cx - 3] = C((20, 20, 24))
    elif kind == "Hammer":
        img[cy - 4:cy - 1, cx - 5:cx + 3] = C((90, 90, 96))
        img[cy - 4, cx - 5:cx + 3] = C((140, 140, 148))
        img[cy - 1:cy + 5, cx - 1:cx + 1] = C((150, 104, 56))
    elif kind == "Crown":
        img[cy:cy + 3, cx - 5:cx + 6] = C((226, 182, 56))
        for k in (-5, 0, 5):
            img[cy - 3:cy, cx + k] = C((226, 182, 56))
            img[cy - 4, cx + k] = C((200, 40, 40))
        img[cy + 2, cx - 5:cx + 6] = C((168, 128, 30))


def sign_wall(wall, kind):
    img = H.wall_image(wall).copy()
    iron = C((40, 38, 40))
    img[4:6, 2:28] = iron                                               # the bracket out from the wall
    img[4, 2:28] = C((84, 82, 84))
    img[6:9, 2:4] = iron
    for x in (8, 23):                                                   # its chains
        img[6:10:2, x] = C((120, 118, 120))
        img[7:10:2, x] = iron
    board = (XS >= 5) & (XS <= 26) & (YS >= 10) & (YS <= 25)
    img[board] = C((150, 104, 62))
    img[board & ((YS - 10) % 5 == 4)] *= 0.86                           # the boards
    img[board & ((XS == 5) | (YS == 10))] = C((186, 136, 84))
    img[board & ((XS == 26) | (YS == 25))] = C((92, 60, 34))
    img[(YS == 26) & (XS >= 6) & (XS <= 27)] *= 0.6                     # its shadow on the wall
    sign_icon(img, kind, 16, 18)
    return to_rows(np.clip(img, 0, 255))


# ------------------------------------------------------------------------------------------------- the ground
def on_grass():
    return np.array(H.tile_image("Grass001"), dtype=np.float32).copy()


def flower_bed(n):
    rng = random.Random(7500 + n)
    img = on_grass()
    bed = (XS >= 2) & (XS <= 29) & (YS >= 6) & (YS <= 27)
    soil = C((92, 64, 40)) * (1 + 0.08 * np.array([[rng.uniform(-1, 1) for _ in range(S)] for _ in range(S)]))[:, :, None]
    img[bed] = soil[bed]
    edge = bed & ((XS == 2) | (XS == 29) | (YS == 6) | (YS == 27))
    img[edge] = C((150, 140, 128))                                      # a stone edging
    img[edge & ((XS + YS) % 4 == 0)] *= 0.8
    colours = [[(214, 60, 70), (240, 200, 70)], [(150, 90, 200), (250, 250, 240)], [(240, 140, 50), (220, 80, 120)]][n - 1]
    for _ in range(26):
        x, y = rng.randint(4, 27), rng.randint(8, 25)
        img[y:y + 2, x] = C((52, 112, 46))                              # the stalk and leaves
        img[y + 1, x - 1:x + 2] = C((64, 128, 52))
        col = C(rng.choice(colours))
        img[y - 1, x - 1:x + 2] = col
        img[y - 2, x] = col
        img[y - 1, x] = C((255, 236, 140))
    return to_rows(np.clip(img, 0, 255))


def bench():
    img = on_grass()
    wood, dark = C((150, 100, 58)), C((92, 60, 34))
    img[(XS >= 3) & (XS <= 28) & (YS >= 22) & (YS <= 24)] *= 0.62       # its shadow
    img[10:13, 3:29] = wood                                             # the back rail
    img[10, 3:29] = wood * 1.2
    img[15:20, 3:29] = wood                                             # the seat
    img[15, 3:29] = wood * 1.25
    img[19, 3:29] = dark
    for x in (5, 26):
        img[10:24, x:x + 2] = dark                                      # the legs
    return to_rows(np.clip(img, 0, 255))


def lamp_post():
    img = on_grass()
    iron = C((44, 42, 46))
    img[26:29, 11:21] = img[26:29, 11:21] * 0.6                         # its shadow
    img[24:28, 13:19] = iron                                            # the foot
    img[8:25, 15:17] = iron                                             # the post
    img[8:25, 15] = C((90, 88, 92))
    glow = np.exp(-(((XS - 16) ** 2 + (YS - 5) ** 2) / 40.0))[:, :, None]
    img = img * (1 + 0.35 * glow) + C((70, 44, 0)) * glow
    img[1:3, 12:21] = iron                                              # the lantern
    img[3:8, 13:20] = C((255, 214, 120))
    img[4:7, 15:18] = C((255, 244, 200))
    img[3:8, 13] = iron
    img[3:8, 19] = iron
    img[8, 12:21] = iron
    return to_rows(np.clip(img, 0, 255))


# ------------------------------------------------------------------------------------------------- the tiles
TILES = {}
TILE_DATA = {}          # name: (Walkable.Data, Show.Name, Use.Words, Examine.Info, Line.of.Sight, minimap)
for _w, _b in H.WALL_BASES.items():
    _blocked = ("0" * 49, "1", "", None, "0", None)
    for _k in (1, 2, 3):
        TILES["%s_Ivy%03d" % (_b, _k)] = (lambda w=_w, k=_k: ivy_wall(w, k))
        TILE_DATA["%s_Ivy%03d" % (_b, _k)] = ("0" * 49, "1", "", "Ivy climbing the wall.", "0", None)
    TILES["%s_Window004" % _b] = (lambda w=_w: flower_window(w))
    TILE_DATA["%s_Window004" % _b] = ("0" * 49, "1", "", "A window with a box of flowers under it.", "1", None)
    TILES["%s_Window005" % _b] = (lambda w=_w: ivy_window(w))
    TILE_DATA["%s_Window005" % _b] = ("0" * 49, "1", "", "A window half hidden by ivy.", "1", None)
    TILES["%s_Lamp001" % _b] = (lambda w=_w: lamp_wall(w))
    TILE_DATA["%s_Lamp001" % _b] = ("0" * 49, "1", "", "A lantern by the door, burning day and night.", "0", None)
    for _i, _s in enumerate(SIGNS, 1):
        TILES["%s_Sign%03d" % (_b, _i)] = (lambda w=_w, s=_s: sign_wall(w, s))
        TILE_DATA["%s_Sign%03d" % (_b, _i)] = ("0" * 49, "1", "", "A sign hangs over the door: %s." % {
            "Bread": "a loaf of bread", "Coin": "a gold coin", "Anvil": "an anvil", "Sack": "a sack of goods",
            "Potion": "a green potion", "Fish": "a fish", "Hammer": "a hammer", "Crown": "a crown"}[_s], "0", None)
for _n in (1, 2, 3):
    TILES["Flower_Bed%03d" % _n] = (lambda n=_n: flower_bed(n))
    TILE_DATA["Flower_Bed%03d" % _n] = ("1" * 49, "1", "", "A flower bed, somebody's pride and joy.", "1", None)
TILES["Bench001"] = bench
TILE_DATA["Bench001"] = ("1111111" + "0000000" * 3 + "1111111" * 3, "1", "", "A wooden bench.", "1", None)
TILES["Lamp_Post001"] = lamp_post
TILE_DATA["Lamp_Post001"] = ("1111111" * 2 + "1110111" * 4 + "1111111", "1", "", "A lamp post.", "1", None)


# ------------------------------------------------------------------------------------------------- dressing the maps
def dress_villages(W, R, C):
    """Every house front (the row of wall just below a roof with a door in it) on every map W builds."""
    new = set(TILES) | set(H.PAINTED.values()) | {"Barrel001", "Crate001"}
    chars = R.legend_chars(new)
    count = 0
    for name, spec in sorted(W.MAPS.items()):
        if name in W.PROTECTED_MAPS or not spec.get("roofs"):
            continue
        rows = spec["rows"]
        h, w = len(rows), len(rows[0])

        def tile(x, y):
            if 1 <= x <= w and 1 <= y <= h:
                return W.LEGEND[rows[y - 1][x - 1]].split("+")[0]
            return ""
        changes = {}
        inside = []                                         # (tx, ty, name, is_npc)
        for e in spec["entities"]:
            try:
                tx, ty = int(float(e[2]) + 16) // 32 + 1, int(float(e[3]) + 28) // 32 + 1
            except (ValueError, IndexError):
                continue
            inside.append((tx, ty, e[1], e[0] in W.NPC_KINDS))
        taken = {(tx, ty) for tx, ty, _, _ in inside}
        for k, roof in enumerate(spec["roofs"]):
            x1, y1, x2, y2 = roof[:4]
            fy = y2 + 1
            front = [(x, fy) for x in range(x1, x2 + 1)]
            doors = [x for x, y in front if tile(x, y) in H.DOOR_WALLS]
            walls = [tile(x, y) for x, y in front if tile(x, y) in H.WALL_BASES]
            if len(doors) != 1 or not walls:
                continue
            door, wall = doors[0], max(set(walls), key=walls.count)
            b = base_name(wall)
            rng = random.Random("%s:%d:%d" % (name, x1, y1))
            count += 1
            # the house's trade, from who (or what) is inside it
            trade = None
            for tx, ty, n, npc in inside:
                if x1 <= tx <= x2 and y1 <= ty <= y2:
                    trade = (SIGN_OF_NPC.get(n) if npc else SIGN_OF_OBJECT.get(n)) or trade
            plain = [x for x, y in front if tile(x, y) == wall and x not in (x1, x2)]
            # (the windows sit either side of the door, so: the plain wall nearest it, on each side)
            beside = [min(side, key=lambda x: abs(x - door)) for side in
                      ([x for x in plain if x < door and door - x <= 3], [x for x in plain if x > door and x - door <= 3])
                      if side]
            # the door: painted (most), or plain oak
            if rng.random() < 0.75:
                paint = rng.choice(list(H.PAINTS))
                changes[(door, fy)] = H.PAINTED[(tile(door, fy), paint)]
            # a sign for a shop, a lantern for some of the rest (beside the door)
            if trade and beside:
                x = rng.choice(beside)
                changes[(x, fy)] = "%s_Sign%03d" % (b, SIGNS.index(trade) + 1)
                beside.remove(x)
                plain.remove(x)
            if beside and rng.random() < 0.45:
                x = rng.choice(beside)
                changes[(x, fy)] = "%s_Lamp001" % b
                plain.remove(x)
            # the windows: boxes of flowers, or ivy round them, or as they are
            look = rng.random()
            for x, y in front:
                if tile(x, y) == "%s_Window001" % b:
                    if look < 0.4:
                        changes[(x, y)] = "%s_Window004" % b
                    elif look < 0.55:
                        changes[(x, y)] = "%s_Window005" % b
            # ivy up a corner or two (the ivy-windowed houses all along)
            corners = [x for x in (x1, x2) if tile(x, fy) == wall]
            if look >= 0.4 and (look < 0.55 or rng.random() < 0.45):
                for x in corners:
                    if rng.random() < 0.75:
                        changes[(x, fy)] = "%s_Ivy%03d" % (b, 1 if x == x1 else 3)
                for x in plain:
                    if (x, fy) not in changes and rng.random() < (0.5 if look < 0.55 else 0.2):
                        changes[(x, fy)] = "%s_Ivy002" % b
            # in front: flower beds along the front, a bench, a lamp post or a barrel at the corners
            gy = fy + 1
            gardener = rng.random() < 0.6
            for x in range(x1, x2 + 1):
                if abs(x - door) <= 1 or tile(x, gy) != "Grass001" or (x, gy) in taken:
                    continue
                if gardener and rng.random() < 0.55:
                    changes[(x, gy)] = "Flower_Bed%03d" % rng.randint(1, 3)
            open_ground = {"Grass001", "Weed001", "Dirt001", "Paving001", "Sand001", "Flowers001", "Flowers002",
                           "Flowers003", "Tall_Grass001"}

            def clear_round(x, y):
                """Open ground all round it (the house itself aside), so nothing gets shut in."""
                for dx, dy in ((-1, 0), (1, 0), (0, 1), (0, -1)):
                    nx, ny = x + dx, y + dy
                    if x1 <= nx <= x2 and y1 <= ny <= fy:
                        continue
                    if tile(nx, ny) not in open_ground or (nx, ny) in changes:
                        return False
                return True
            extras = []
            if rng.random() < 0.35:
                extras.append("Bench001")
            if rng.random() < 0.35:
                extras.append("Lamp_Post001")
            if rng.random() < 0.4:
                extras.append(rng.choice(["Barrel001", "Crate001"]))
            spots = [(x1 - 1, fy), (x2 + 1, fy), (x1 - 1, gy), (x2 + 1, gy)] + \
                [(x, gy) for x in range(x1, x2 + 1) if abs(x - door) >= 2]
            rng.shuffle(spots)
            for thing in extras:
                for x, y in spots:
                    if tile(x, y) == "Grass001" and (x, y) not in changes and (x, y) not in taken and \
                            abs(x - door) >= 2 and clear_round(x, y):
                        changes[(x, y)] = thing
                        spots.remove((x, y))
                        break
        if changes:
            spec["rows"] = C.set_cells(rows, [(x, y, chars[t]) for (x, y), t in changes.items()])
    return count
