"""Fishing spots: you can't fish just anywhere in the water any more, only at a fishing spot, an animated patch of
water where the fish gather (Entities.ini Anim.Frames: the game cycles <Name>1-4). Each spot is one kind of fish,
and the better fish are in harder places:

  * Fish_Spot       ripples                  Raw_Herring       Fishing 1    the sea round the Isle and the Southlands
  * Trout_Spot      ripples and a flick      Raw_Trout      Fishing 10   the Southlands' rivers and ponds, some in the Wildlands
  * Salmon_Spot     a salmon leaping         Raw_Salmon     Fishing 20   rivers and lakes of the Wildlands and the far lands
  * Swordfish_Spot  a fin cutting the water  Raw_Swordfish  Fishing 35   the sea off the far south and the Eastreach
  * Eel_Spot        bubbles in a black pool  Raw_Cave_Eel   Fishing 15   the pools in the caves

Every catch needs a rod and uses one bait (a miss keeps it). Fishing in plain water just says to look for a spot.

Not run on its own: build_content.extend() calls extend() (before the scenery pass, which then keeps clear of them),
and build_content.patches() takes protected_spots() for the original Isle maps. `python -I build_fishing.py` (or
build_sprites) draws the sprites.
"""
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import MAP_W, MAP_H, p, read_lines, built_base  # noqa: E402

W = C = R = None

# spot: (fish, level, xp, where (Examine), what you're doing)
SPOTS = {
    "Fish_Spot": ("Raw_Herring", 1, "0.1", "Ripples on the water: a shoal of fish feeding near the surface.",
                  "cast your line among the ripples"),
    "Trout_Spot": ("Raw_Trout", 10, "0.2", "Trout rising to snap at flies. Fishing 10.", "flick your line over the rising trout"),
    "Salmon_Spot": ("Raw_Salmon", 20, "0.35", "A salmon run: silver fish leaping. Fishing 20.",
                    "cast into the run of leaping salmon"),
    "Swordfish_Spot": ("Raw_Swordfish", 35, "0.6", "A great fin cuts the water. Swordfish! Fishing 35.",
                       "heave your line out towards the fin"),
    "Eel_Spot": ("Raw_Cave_Eel", 15, "0.3", "Bubbles rise from the black water. Something pale coils below. Fishing 15.",
                 "lower your line into the bubbling pool"),
}
FRAMES = 4
LEVELS = {"Raw_Herring": 1, "Raw_Trout": 10, "Raw_Salmon": 20, "Raw_Swordfish": 35, "Raw_Cave_Eel": 15}


# ------------------------------------------------------------------------------------------- sprites
FOAM, FOAM_DIM = (232, 244, 255), (150, 196, 228)


def ring(img, cx, cy, rx, col, ry=None, gaps=0, rng=None):
    ry = ry if ry is not None else rx * 0.45
    n = max(12, int(rx * 6))
    for k in range(n):
        a = 2 * math.pi * k / n
        if gaps and (k * gaps // n) % 2:
            continue
        x, y = int(round(cx + rx * math.cos(a))), int(round(cy + ry * math.sin(a)))
        if 0 <= x < 32 and 0 <= y < 32:
            img[y][x] = col


def blob(img, cx, cy, rx, ry, col):
    for y in range(32):
        for x in range(32):
            if ((x + 0.5 - cx) / rx) ** 2 + ((y + 0.5 - cy) / ry) ** 2 <= 1:
                img[y][x] = col


def fish_shape(img, cx, cy, length, angle, body, belly, tail=True):
    """A little fish seen from the side, nose along angle (radians)."""
    ca, sa = math.cos(angle), math.sin(angle)
    for t10 in range(-int(length * 10 / 2), int(length * 10 / 2) + 1):
        t = t10 / 10.0
        half = max(0.6, (length / 4.2) * math.sqrt(max(0.0, 1 - (2 * t / length) ** 2)))
        for s10 in range(-int(half * 10), int(half * 10) + 1):
            s = s10 / 10.0
            x, y = int(round(cx + t * ca - s * sa)), int(round(cy + t * sa + s * ca))
            if 0 <= x < 32 and 0 <= y < 32:
                img[y][x] = belly if s > half * 0.3 else body
    if tail:
        tx, ty = cx - (length / 2 + 1) * ca, cy - (length / 2 + 1) * sa
        for s in (-2, -1, 0, 1, 2):
            x, y = int(round(tx - s * sa - abs(s) * 0.6 * ca)), int(round(ty + s * ca - abs(s) * 0.6 * sa))
            if 0 <= x < 32 and 0 <= y < 32:
                img[y][x] = body


def frame_img(kind, f):
    img = [[None] * 32 for _ in range(32)]
    rng = random.Random("%s%d" % (kind, f))
    if kind == "Fish_Spot":                          # rings spreading from two little rises
        for cx, cy, ph in ((13, 18, 0), (21, 14, 2)):
            r = 2 + ((f + ph) % FRAMES) * 2.5
            ring(img, cx, cy, r, FOAM if r < 7 else FOAM_DIM, gaps=4 if r > 6 else 0)
        for _ in range(3):
            img[rng.randrange(10, 24)][rng.randrange(8, 26)] = FOAM
    elif kind == "Trout_Spot":                       # rings, and a trout's tail flicking up on frames 2-3
        r = 3 + f * 2.5
        ring(img, 15, 18, r, FOAM if r < 8 else FOAM_DIM, gaps=4 if r > 7 else 0)
        ring(img, 22, 21, 2 + ((f + 2) % 4) * 2, FOAM_DIM)
        if f in (1, 2):
            fish_shape(img, 15, 15 - f, 9, -1.2 if f == 1 else -1.6, (110, 104, 64), (196, 160, 120))
            ring(img, 15, 19, 3, FOAM)
    elif kind == "Salmon_Spot":                      # a salmon leaping in an arc over a splash
        ring(img, 10, 22, 2 + f * 2, FOAM_DIM)
        ring(img, 22, 22, 8 - f * 2 if f < 3 else 2, FOAM)
        t = f / 3.0
        x, y = 8 + 16 * t, 20 - 14 * math.sin(math.pi * t)
        angle = -0.9 + 1.8 * t
        fish_shape(img, x, y, 11, angle, (150, 160, 176), (236, 150, 140))
        for k in range(4):                           # drops shaken off
            img[int(y + 4 + k)][int(min(31, max(0, x - 5 + k * 3)))] = FOAM
    elif kind == "Swordfish_Spot":                   # a dark fin circling, with its wake
        a = 2 * math.pi * f / FRAMES
        cx, cy = 16 + 7 * math.cos(a), 18 + 3 * math.sin(a)
        for k in range(1, 6):                        # the wake behind it
            b = a - 0.35 * k
            ring(img, 16 + 7 * math.cos(b), 18 + 3 * math.sin(b), 1.5 + k * 0.4, FOAM if k < 3 else FOAM_DIM, ry=0.9)
        fin, edge = (34, 46, 68), (92, 112, 146)
        tri = ((cx - 4, cy + 0.5), (cx + 5, cy + 0.5), (cx - 2.5, cy - 11))     # a tall fin, swept back
        def inside(px, py):
            (x1, y1), (x2, y2), (x3, y3) = tri
            d1 = (px - x2) * (y1 - y2) - (x1 - x2) * (py - y2)
            d2 = (px - x3) * (y2 - y3) - (x2 - x3) * (py - y3)
            d3 = (px - x1) * (y3 - y1) - (x3 - x1) * (py - y1)
            return not ((d1 < 0 or d2 < 0 or d3 < 0) and (d1 > 0 or d2 > 0 or d3 > 0))
        for y in range(32):
            for x in range(32):
                if inside(x + 0.5, y + 0.5):
                    img[y][x] = edge if not inside(x - 0.5, y + 0.5) else fin
        ring(img, cx, cy + 1, 4, FOAM, ry=1.3)
    else:                                            # Eel_Spot: bubbles rising, and a pale coil turning below
        coil = (196, 204, 188)
        for k in range(14):
            a = 2 * math.pi * (k / 14.0) + f * math.pi / 2
            r = 3 + k * 0.45
            x, y = int(16 + r * math.cos(a)), int(19 + r * 0.5 * math.sin(a))
            if 0 <= x < 32 and 0 <= y < 32:
                img[y][x] = coil if k % 3 else (150, 160, 146)
        for k, (bx, by0) in enumerate(((11, 22), (19, 20), (15, 24), (22, 25))):
            by = by0 - ((f + k) % FRAMES) * 4
            if by > 6:
                ring(img, bx, by, 1.3 + (k % 2) * 0.6, FOAM, ry=1.3)
    return img


def draw_sprites():
    import sprite_kit as K
    made = []
    for kind in SPOTS:
        frames = [frame_img(kind, f) for f in range(FRAMES)]
        for f, img in enumerate(frames):
            if K.save("Entities", "%s%d" % (kind, f + 1), img):
                made.append("%s%d" % (kind, f + 1))
        if K.save("Entities", kind, frames[0]):         # the plain name: the first frame (the editors, the minimap)
            made.append(kind)
    return made


# ------------------------------------------------------------------------------------------- scripts and data
def spot_script(spot):
    fish, level, xp, _, doing = SPOTS[spot]
    name = fish.replace("Raw_", "").replace("_", " ").lower()
    steps = ["// Fishing at a %s (build_fishing.py): a rod, Fishing %d and one bait a catch (a miss keeps it)."
             % (spot.replace("_", " ").lower(), level),
             (">Distance.From.Clicked.Entity", "64", "@far"),
             (">Got.Item", "Fishing_Rod", "1", "@norod"),
             ("Get.Value", "SKILL", "Fishing", "Variable.1$")]
    if level > 1:
        steps += [(">Conditional", "$Variable.1>=%d" % level, "@low")]
    steps += [(">Got.Item", "Bait", "1", "@nobait"),
              ("Display.Message", "Cyan", "You bait the hook and %s..." % doing),
              ("Play.Sound", "Splash"),
              ("Wait", "4"),
              (">Conditional", "($Variable.1-%d+40)>$Random.Percent" % level, "@fail"),
              ("Take.Item", "Bait", "1"),
              ("Display.Message", "Yellow", "...and land a %s!" % name),
              ("Give.Item", fish, "1"),
              ("Update.Skill", "Fishing", "+" + xp),
              ("End",),
              "fail:", ("Display.Message", "DarkRed", "...but it slips the hook. Your bait's still on."), ("End",),
              "nobait:", ("Display.Message", "DarkRed", "You need bait on the hook. Fishing shops sell worms."), ("End",),
              "norod:", ("Display.Message", "DarkRed", "You need a fishing rod."), ("End",)]
    if level > 1:
        steps += ["low:", ("Display.Message", "DarkRed", "You need level %d Fishing to catch the %s here." % (level, name)),
                  ("End",)]
    steps += ["far:", ("Display.Message", "DarkRed", "You need to stand at the water's edge, by the spot!"), ("End",)]
    return steps


NO_SPOT = [("Display.Message", "DarkRed", "Nothing's biting here. Look for a fishing spot: ripples where the fish gather."),
           ("End",)]


def scripts():
    S = W.S
    for spot in SPOTS:
        if spot not in ("Salmon_Spot", "Swordfish_Spot"):        # (those two take seal blubber too: build_water_animals)
            S["Fish " + spot] = spot_script(spot)
        S["Use Fishing_Rod With " + spot] = [("Goto.Script", "Fish " + spot), ("End",)]
    for water in ("Water", "Pond", "Sand_Water", "Snow_Water", "Cave_Pool"):
        S["Use Fishing_Rod With " + water] = list(NO_SPOT)
    S["Fishing Skill"] = [("Display.Message", "Cyan", "Fishing: find a fishing spot (ripples on the water) and fish "
                           "there with a rod and bait. Better fish in harder places."), ("End",)]


def data():
    for spot, (fish, level, _, examine, _) in SPOTS.items():
        C.ENTITIES[spot] = [("Type", "StaticObject"), ("Use.Words", "Fish"), ("Examine.Info", examine),
                            ("Solid", "0"), ("Anim.Frames", str(FRAMES)), ("Anim.Speed", "220")]
    wheres = {"Raw_Herring": "Fish spots (ripples) in the sea round the Isle and the Southlands",
              "Raw_Trout": "Trout spots on the Southlands' rivers and ponds, and some in the Wildlands",
              "Raw_Salmon": "Salmon spots on the rivers and lakes of the Wildlands and the far lands",
              "Raw_Swordfish": "Swordfish spots in the sea off the far south and the Eastreach",
              "Raw_Cave_Eel": "Eel spots (bubbles) in the black pools of the caves"}
    spot_of = {v[0]: k for k, v in SPOTS.items()}
    for _, g in C.GATHERING:
        if g.get("Tool") == "Fishing_Rod" and g.get("Gives") in spot_of:
            g["Source"] = spot_of[g["Gives"]]
            g["Where"] = wheres[g["Gives"]] + " (a rod and bait; each catch uses one bait)"


# ------------------------------------------------------------------------------------------- where the spots go
def is_water(t):
    return t.startswith(("Water", "Sand_Water", "Snow_Water")) or t in ("Pond001", "Cave_Pool001")


ROADS = {"Dirt001", "Paving001", "Plank001"}


def tier(name):
    x, y, z = (int(v) for v in name.split(","))
    if x <= 3 and y <= 4:
        return 1                                     # the Isle and the Southlands
    if R is not None and R.MX0 <= x <= R.MX1 and R.MY0 <= y <= R.MY1:
        return 2 if y <= 7 else 3                    # the Wildlands: the north, then the far south
    if x >= 6:
        return 3                                     # the Eastreach
    return 2


def choose(name, grid, walk_ok, taken):
    """[(x, y, spot)] for one map (grid[y][x] tile names, 0-based)."""
    x0, y0, z = (int(v) for v in name.split(","))
    h, w = len(grid), len(grid[0])
    body, size, edge = {}, [], []
    for y in range(h):                               # the bodies of water, and which reach the map's edge
        for x in range(w):
            if is_water(grid[y][x]) and (x, y) not in body:
                k, todo, n, touches = len(size), [(x, y)], 0, False
                body[(x, y)] = k
                while todo:
                    cx, cy = todo.pop()
                    n += 1
                    touches |= cx in (0, w - 1) or cy in (0, h - 1)
                    for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                        if 0 <= nx < w and 0 <= ny < h and (nx, ny) not in body and is_water(grid[ny][nx]):
                            body[(nx, ny)] = k
                            todo.append((nx, ny))
                size.append(n)
                edge.append(touches)
    # the land you can walk to: from the roads and paths (they always lead somewhere), and in a cave its ladders and
    # edges (a shore cut off behind thick forest or cliffs won't do; a map with no road gets no spot)
    todo = [(x, y) for y in range(h) for x in range(w) if grid[y][x] in ROADS or grid[y][x].startswith(("Ladder", "Stairs"))]
    if z < 0:
        todo += [(x, y) for y in range(h) for x in range(w) if x in (0, w - 1) or y in (0, h - 1)]
    land = set()
    while todo:
        x, y = todo.pop()
        if (x, y) in land or not (0 <= x < w and 0 <= y < h) or is_water(grid[y][x]) or not (
                walk_ok(grid[y][x]) or grid[y][x].startswith(("Ladder", "Stairs"))):
            continue
        land.add((x, y))
        todo += [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
    cands = []
    for (x, y), k in body.items():
        if not (2 <= x < w - 2 and 2 <= y < h - 2) or (x, y) in taken:
            continue
        if not grid[y][x] in ("Water001", "Pond001", "Cave_Pool001") and not grid[y][x].startswith(("Sand_Water", "Snow_Water")):
            continue
        shore = [(nx, ny) for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1))
                 if (nx, ny) in land and (nx, ny) not in taken]
        if shore:
            cands.append((x, y, k))
    if not cands:
        return []
    rng = random.Random("fish/" + name)
    rng.shuffle(cands)
    want = 2 if len(cands) >= 60 else 1
    out = []
    t = tier(name)
    for x, y, k in cands:
        if len(out) >= want:
            break
        if any(abs(x - ox) + abs(y - oy) < 8 for ox, oy, _ in out):
            continue
        t_ = grid[y][x]
        sea = edge[k] and size[k] > 120              # (a big body reaching the map's edge: the sea)
        if z < 0 or t_ == "Cave_Pool001":
            spot = "Eel_Spot"
        elif t == 1:
            spot = "Fish_Spot" if sea else "Trout_Spot"
        elif t == 2:
            spot = "Fish_Spot" if sea else rng.choice(("Trout_Spot", "Salmon_Spot"))
        else:
            spot = "Swordfish_Spot" if sea else "Salmon_Spot"
        out.append((x + 1, y + 1, spot))
    return out


def entity_tiles(entities):
    out = set()
    for e in entities:
        try:
            tx, ty = int(float(e[2]) + 16) // 32 + 1, int(float(e[3]) + 28) // 32 + 1
        except (ValueError, IndexError):
            continue
        out |= {(tx - 1 + dx, ty - 1 + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)}   # 0-based, and round them
    return out


def walk_ok_fn():
    from common import Ini
    tiles = Ini(p("data", "Tiles.ini"))

    def ok(t):
        if t in C.TILES and C.TILES[t][0]:
            return C.TILES[t][0][24] == "1"
        return (tiles.get(t, "Walkable.Data", "1" * 49) or "1" * 49)[24:25] == "1"
    return ok


def place():
    """Spots on every built map (the original Isle maps: protected_spots, through build_content's patches)."""
    ok = walk_ok_fn()
    for name, spec in W.MAPS.items():
        if name in W.PROTECTED_MAPS or name in getattr(W, "NO_SCENERY", ()) or name == "0,0,-9":
            continue
        grid = [[W.LEGEND[ch].split("+")[0] for ch in row] for row in spec["rows"]]
        taken = entity_tiles(spec["entities"])
        for x, y, spot in choose(name, grid, ok, taken):
            spec["entities"].append(W.obj(spot, x, y))


def protected_spots(world, content):
    """{map: [entity]} for the original maps, from their files (as they are, patches and all)."""
    global W, C
    W, C = world, content
    ok = walk_ok_fn()
    out = {}
    for name in sorted(W.PROTECTED_MAPS):
        path = p("maps", name + ".txt")
        if not os.path.exists(path):
            continue
        lines = read_lines(path)
        grid = [[built_base(c) for c in r.split(":")] for r in lines[:MAP_H]]       # (decor: as the old tiles)
        if len(grid) < MAP_H or any(len(r) < MAP_W for r in grid):
            continue
        ents = [l.split("\t") for l in lines[MAP_H:] if l.strip()]
        ents = [e for e in ents if not (len(e) > 1 and e[1] in SPOTS)]     # (our own, from the last build)
        taken = entity_tiles([e for e in ents if len(e) >= 4])
        spots = choose(name, grid, ok, taken)
        if spots:
            out[name] = [W.obj(spot, x, y) for x, y, spot in spots]
    return out


def extend(world, content, regions):
    global W, C, R
    W, C, R = world, content, regions
    W.WATER_ENTITIES = set(getattr(W, "WATER_ENTITIES", ())) | set(SPOTS)
    place()
    data()


def finish():
    scripts()


if __name__ == "__main__":
    print("\n".join("wrote " + n for n in draw_sprites()))
