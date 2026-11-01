"""The west reshaped as the owner drew it (a picture of the world map with the new coast in red, the mountains' edges in
white and a tunnel in black): a pass over the finished maps, not a rebuild.

  * The coast (COAST, the red line): everything west and north of it the sea - the far west of the Mirefen, its
    northern beach, the strip west of Galaith - and the open sea inside it land (the bay south-east of Galaith's
    harbour, at the foot of the range). The line wanders a little (noise), never over anything built or near it (a
    quay, a pier, a wall); a beach where grass meets the sea, the diagonal shore pieces round it all.
  * The mountains (the white lines): Galaith's valley reaches north to RIDGE (mountains beyond it, the mine's mouth
    still in them); the West Range's east edge is RANGE_EDGE (grassland east of it, but the barrier's pass shut in by
    rock either side); and south of the dragon's field the range meets the valley along FIELD_EDGE. The dragon's field
    stays walled in by mountains (only the east gate and the pass lead out of it).
  * The Mirefen shut away: its northern beach is the sea, its boardwalk to it gone, and the only way in is the Mire
    Tunnel (the black line): a cave mouth at the West Range's east foot, a tunnel under the range (z -1, its own
    maps), and steps up into the fen by the boardwalk to Mirefold. Bats and spiders in the dark, and its traps.

Run it once (a second run finds it done and stops).

  python -I "dev\\migrate\\reshape_west.py"
"""
import math
import os
import random
import sys
from collections import deque

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "estforlan"))
import world_edit as W                                   # noqa: E402
from world_edit import XT, YT, TW, fbm, h01             # noqa: E402
import story_kit as SK                                   # noqa: E402
import sprite_kit as K                                   # noqa: E402

ROOT = W.ROOT
DONE = os.path.join(HERE, ".west_reshaped")
MAKER = "reshape_west.py"

COAST = [(7, 82), (1, 86), (-5, 86), (-11, 83), (-17, 89), (-23, 95), (-29, 97), (-35, 91), (-41, 85), (-44, 79),
         (-46, 73), (-52, 67), (-58, 61), (-64, 57), (-70, 55), (-76, 51), (-82, 50), (-88, 54), (-94, 54), (-100, 50),
         (-106, 49), (-112, 53), (-118, 53), (-124, 49), (-130, 50), (-136, 55), (-142, 56), (-148, 52), (-154, 58),
         (-160, 60), (-166, 61), (-172, 63), (-178, 65), (-184, 70), (-190, 75), (-196, 79), (-202, 82), (-208, 86),
         (-214, 88), (-220, 88), (-226, 84), (-232, 84), (-238, 89), (-244, 90), (-250, 86), (-256, 92), (-259, 98),
         (-259, 104), (-253, 110), (-247, 116), (-241, 117), (-235, 112), (-229, 113), (-223, 118), (-217, 120),
         (-211, 126), (-205, 132), (-202, 138), (-208, 144), (-210, 150), (-212, 156), (-217, 162), (-223, 168),
         (-228, 174), (-234, 180), (-240, 186), (-246, 192), (-250, 198), (-255, 204), (-260, 210), (-266, 216),
         (-272, 222), (-278, 228), (-283, 234), (-287, 240), (-290, 246), (-292, 252), (-293, 258), (-289, 264),
         (-289, 270), (-293, 276), (-293, 282), (-288, 288), (-288, 294), (-293, 300), (-293, 306), (-288, 312),
         (-288, 318), (-292, 324), (-291, 330), (-285, 336), (-280, 342), (-277, 348), (-275, 354), (-274, 360),
         (-272, 366), (-270, 372), (-274, 378), (-274, 384), (-269, 390), (-269, 396), (-275, 402), (-281, 408),
         (-285, 414), (-286, 420), (-281, 426), (-275, 432), (-269, 436), (-263, 436), (-257, 430), (-251, 425),
         (-245, 421), (-239, 417), (-233, 412), (-227, 407), (-221, 405), (-215, 403), (-209, 401), (-203, 399),
         (-197, 397), (-191, 396), (-185, 400), (-179, 402), (-173, 398), (-167, 399), (-161, 403), (-155, 403),
         (-149, 397), (-143, 397), (-137, 400), (-131, 394), (-125, 393), (-119, 391), (-113, 389), (-107, 388),
         (-101, 386), (-95, 391), (-89, 392), (-83, 388), (-77, 390), (-71, 396), (-65, 400), (-59, 400), (-53, 396),
         (-47, 402), (-41, 408), (-35, 414), (-30, 420), (-24, 426), (-18, 425), (-12, 421), (-8, 427), (-7, 433),
         (-12, 439), (-12, 445), (-6, 451), (-3, 457), (1, 463), (7, 469)]
RIDGE = [(-286, 242), (-279, 245), (-272, 238), (-265, 235), (-258, 238), (-251, 234), (-244, 232), (-237, 235),
         (-230, 228), (-223, 223), (-216, 218), (-209, 215), (-202, 213), (-195, 216), (-188, 213), (-181, 216),
         (-174, 218), (-167, 216), (-160, 221), (-153, 228), (-146, 235), (-139, 242), (-132, 249), (-125, 253),
         (-118, 255), (-111, 251), (-104, 256), (-97, 252), (-90, 259), (-83, 263), (-76, 266), (-69, 269), (-62, 275),
         (-55, 280), (-48, 278), (-46, 282)]
RANGE_EDGE = [(17, 223), (10, 230), (3, 237), (-2, 244), (2, 251), (8, 258), (12, 265), (15, 272), (12, 279),
              (17, 286), (14, 293), (17, 300), (12, 307), (17, 314), (10, 321), (5, 328), (8, 335), (2, 342),
              (-1, 349), (-8, 356), (-4, 363), (3, 370), (10, 377), (17, 380), (24, 383)]
FIELD_EDGE = [(-57, 344), (-63, 351), (-69, 358), (-74, 365), (-72, 372), (-77, 379), (-73, 386)]
MINE = (-170, 248)                                       # (Galaith's mine mouth: kept in the mountains)
TUNNEL_W, TUNNEL_E = (-6, 125), (42, 129)                # (the black line's ends: the fen, the range's east foot)
SEAL = (-40, 60, 60, 240)                                # (where the fen meets the range: no way through but the tunnel)
BUILT_GUARD = 3


def interp(points, t, along=0):
    """The polyline's other coordinate at t (along 0: points by x; 1: by y), smoothed over its neighbours."""
    pts = sorted(points, key=lambda p: p[along])
    o = 1 - along
    if t <= pts[0][along]:
        return pts[0][o]
    for a, b in zip(pts, pts[1:]):
        if a[along] <= t <= b[along]:
            k = (t - a[along]) / max(1, b[along] - a[along])
            return a[o] + (b[o] - a[o]) * k
    return pts[-1][o]


def smooth(points, along, n=2):
    """The polyline averaged with its neighbours (the hand's wobble taken out)."""
    pts = sorted(points, key=lambda p: p[along])
    out = []
    for i, p in enumerate(pts):
        near = pts[max(0, i - n):i + n + 1]
        out.append((p[0], sum(q[1] for q in near) / len(near)) if along == 0 else
                   (sum(q[0] for q in near) / len(near), p[1]))
    return out


def inside_coast(gx, gy):
    """Inside the red line (closed east of it, past the noise's reach): land."""
    pts = COAST + [(14, 469), (14, 82), (7, 82)]
    x, y = gx + 0.5 + 5 * (fbm(gx, gy, 9, 1201) - 0.5), gy + 0.5 + 5 * (fbm(gx, gy, 9, 1202) - 0.5)
    c = False
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        if (y1 <= y < y2) or (y2 <= y < y1):
            if x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
                c = not c
    return c


def in_zone(gx, gy):
    """Where the coast may change: the west of the world (never the Isle, never east of the range's spine)."""
    return gx <= 7 and 42 <= gy <= 470


# ================================================================== what's built, kept
def guarded(w, cells_box):
    x1, y1, x2, y2 = cells_box
    built = set()
    for (mx, my), m in w.maps.items():
        if not (x1 // XT - 1 <= mx <= x2 // XT + 1 and y1 // YT - 1 <= my <= y2 // YT + 1):
            continue
        for y in range(YT):
            for x in range(XT):
                text = m.rows[y][x]
                if not W.natural(text):
                    built.add((mx * XT + x, my * YT + y))
        for ln in m.ents:
            c = W.line_cell(ln, mx, my)
            if c and (W.line_id(ln) or ln.startswith(("Trigger", "Lock"))):
                built.add(c)
    near = {(c[0] + dx, c[1] + dy) for c in built for dx in range(-BUILT_GUARD, BUILT_GUARD + 1)
            for dy in range(-BUILT_GUARD, BUILT_GUARD + 1)}
    return built, near


def peak_tile(c):
    return "Peak%03d" % (1 + int(h01("pk", *c) * 6))


# ================================================================== the coast
def coast(w, built, near_built):
    box = (-330, 40, 8, 480)
    cells = [(x, y) for x in range(box[0], box[2]) for y in range(box[1], box[3]) if w.cell(x, y) is not None]
    water = {c for c in cells if W.watery(w.cell(*c))}
    edge = [c for c in water if any(w.cell(c[0] + dx, c[1] + dy) is None for dx, dy in ((1, 0), (-1, 0), (0, 1),
                                                                                         (0, -1)))]
    ocean, q = set(edge), deque(edge)
    while q:
        c = q.popleft()
        for n in ((c[0] + 1, c[1]), (c[0] - 1, c[1]), (c[0], c[1] + 1), (c[0], c[1] - 1)):
            if n in water and n not in ocean:
                ocean.add(n)
                q.append(n)
    to_sea, to_land = [], []
    for c in cells:
        if not in_zone(*c):
            continue
        land_here = inside_coast(*c)
        wet = c in water
        if not land_here and not wet and c not in near_built:
            to_sea.append(c)
        elif land_here and c in ocean and c[1] > 200 and c not in near_built:
            to_land.append(c)
    for c in to_sea:
        w.put(c[0], c[1], W.SEA)
    for c in to_land:
        ground = None
        for r in (2, 4, 7, 11):
            near = [w.tile(c[0] + dx, c[1] + dy) for dx in range(-r, r + 1) for dy in range(-r, r + 1)]
            near = [t for t in near if t and not W.WATERY.match(t) and t != "?"]
            if near:
                peaks = sum(1 for t in near if W.PEAKY.match(t))
                ground = "PEAK" if peaks * 2 > len(near) else max(
                    set(t for t in near if not W.PEAKY.match(t)) or {"Grass001"},
                    key=lambda t: near.count(t))
                break
        w.put(c[0], c[1], "?" if ground is None else ground)
    for c in to_land:
        if w.cell(*c) in ("?", "PEAK"):
            w.put(c[0], c[1], peak_tile(c) if w.cell(*c) == "PEAK" else "Grass001")
        elif W.parts(w.cell(*c))[0] in ("Dirt001", "Gravel001", "Cobble001", "Boardwalk001", "Plank001"):
            w.put(c[0], c[1], "Grass001")
    # (one-tile bumps and notches out; a beach where grass meets the sea; the shore's diagonal pieces)
    changed = set(to_sea) | set(to_land)
    ring = {(c[0] + dx, c[1] + dy) for c in changed for dx in range(-3, 4) for dy in range(-3, 4)}
    for _ in range(3):
        for c in sorted(ring):
            if c in near_built or not in_zone(*c) or w.cell(*c) is None:
                continue
            t = w.tile(*c)
            nb = [w.tile(c[0] + dx, c[1] + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))]
            if None in nb:
                continue
            wet = sum(1 for v in nb if W.WATERY.match(v))
            if t == W.SEA and wet <= 1:
                ground = [v for v in nb if not W.WATERY.match(v) and not W.PEAKY.match(v)]
                w.put(c[0], c[1], max(set(ground), key=ground.count) if ground else peak_tile(c))
                changed.add(c)
            elif (W.NATURAL.match(t) and not W.WATERY.match(t)) and wet >= 3:
                w.put(c[0], c[1], W.SEA)
                changed.add(c)
    for c in sorted(ring):
        if c in near_built or w.cell(*c) is None or w.tile(*c) != "Grass001":
            continue
        if any(w.tile(c[0] + dx, c[1] + dy) == W.SEA for dx in (-2, -1, 0, 1, 2) for dy in (-2, -1, 0, 1, 2)):
            w.put(c[0], c[1], "Sand001")
            changed.add(c)
    w.smooth_shores(changed)
    drowned = 0
    for m, ln, c in w.lines(box):
        if c in changed and W.watery(w.cell(*c)) and ln.split("\t")[0] in W.ENT_KINDS:
            if W.line_id(ln):
                print("  !! %s would drown: left where it is" % W.line_id(ln))
                continue
            w.drop(m, ln)
            drowned += 1
    return len(to_sea), len(to_land), drowned


# ================================================================== the mountains
def mountains(w, built, near_built):
    scorched = {(x, y) for x in range(-110, 10) for y in range(270, 360)
                if (w.tile(x, y) or "").startswith("Scorched")}
    near_field = {(c[0] + dx, c[1] + dy) for c in scorched for dx in range(-6, 7) for dy in range(-6, 7)}
    barrier = {(x, y) for x in range(-5, 30) for y in range(290, 320) if (w.tile(x, y) or "").startswith("Barrier")}
    near_barrier = {(c[0] + dx, c[1] + dy) for c in barrier for dx in range(-12, 16) for dy in range(-9, 10)}
    near_mine = {(MINE[0] + dx, MINE[1] + dy) for dx in range(-7, 8) for dy in range(-7, 5)}
    hold = near_built | near_field | near_barrier | near_mine

    def grassy(c):
        t = w.tile(*c)
        return t in ("Grass001", "Forest001", "Sand001") and W.natural(w.cell(*c))

    def peaky(c):
        return w.tile(*c) is not None and bool(W.PEAKY.match(w.tile(*c)))
    to_peak, to_grass = set(), set()
    ridge = smooth(RIDGE, 0)
    for gx in range(-290, -45):
        yb = interp(ridge, gx, 0) + 4 * (fbm(gx, 0, 14, 1211) - 0.5)
        if abs(gx - MINE[0]) <= 14:
            yb = max(yb, MINE[1] + 5 - abs(gx - MINE[0]) * 0.2)            # (the mine's mouth: in the mountains)
        yb = int(round(yb))
        for gy in range(yb - 30, yb):
            if grassy((gx, gy)) and (gx, gy) not in hold:
                to_peak.add((gx, gy))
        for gy in range(yb, yb + 40):
            if peaky((gx, gy)) and (gx, gy) not in hold:
                to_grass.add((gx, gy))
    edge = smooth(RANGE_EDGE, 1)
    for gy in range(223, 384):
        xb = int(round(interp(edge, gy, 1) + 4 * (fbm(0, gy, 14, 1212) - 0.5)))
        for gx in range(xb + 1, xb + 46):
            if peaky((gx, gy)) and (gx, gy) not in hold:
                to_grass.add((gx, gy))
        for gx in range(xb - 20, xb + 1):
            if grassy((gx, gy)) and (gx, gy) not in hold:
                to_peak.add((gx, gy))
    fe = smooth(FIELD_EDGE, 1, 1)
    for gy in range(344, 388):
        xb = int(round(interp(fe, gy, 1) + 3 * (fbm(0, gy, 9, 1213) - 0.5)))
        for gx in range(xb - 25, xb):
            if peaky((gx, gy)) and (gx, gy) not in hold:
                to_grass.add((gx, gy))
        for gx in range(xb, xb + 9):
            if grassy((gx, gy)) and (gx, gy) not in hold:
                to_peak.add((gx, gy))
    for c in to_peak:
        w.put(c[0], c[1], peak_tile(c))
    w.rewild(to_grass, seed="foothills")
    for c in to_grass:                                     # (rewild picked from the wild round: never a peak back)
        if W.PEAKY.match(w.tile(*c)) or W.watery(w.cell(*c)):
            w.put(c[0], c[1], "Grass001")
    return to_peak, to_grass


def close_field(w):
    """The grass round the outside of Galaith's east wall, north and south of the dragon's field, made rock: the field
    opens on the valley only at the east gate (it had a way round the wall's corner). Returns the cells."""
    out = []
    for x in range(-90, -40):
        for y in range(255, 382):
            if abs(y - 305) < 9 and x > -80:
                continue                                       # (before the east gate: the field's own)
            text = w.cell(x, y)
            if text and W.natural(text) and W.parts(text)[0] in ("Grass001", "Sand001") and any(
                    (w.tile(x + dx, y + dy) or "").startswith("Scorched") for dx in range(-9, 10) for dy in range(-9, 10)):
                w.put(x, y, peak_tile((x, y)))
                out.append((x, y))
    return out


def repeak(w, cells):
    """New peaks joined into big and huge ones where whole blocks of them allow (land.peak_at)."""
    import land as LAND
    solid = set(cells)
    for c in cells:
        LAND.BIOME[c] = "mount"
    for c in cells:
        w.put(c[0], c[1], LAND.peak_at("mount", c[0], c[1], lambda n: n in solid))


# ================================================================== the fen, shut away; the tunnel
def walkable_tiles():
    """{tile: can it be walked on at all} from Tiles.ini's Walkable.Data."""
    out, sec = {}, None
    for ln in W.read(os.path.join(ROOT, "data", "Tiles.ini")).splitlines():
        if ln.startswith("[") and ln.endswith("]"):
            sec = ln[1:-1]
            out.setdefault(sec, True)
        elif sec and ln.startswith("Walkable.Data="):
            out[sec] = "1" in ln.split("=", 1)[1]
    return out


def walkable(w, c, tiles):
    text = w.cell(*c)
    if text is None:
        return False
    t, over = W.parts(text)
    if not tiles.get(t, False):
        return False
    d = over.get("Decor")
    return not d or tiles.get(d, True)


def leaks(w, tiles, start, box, out_of):
    """A walker's way from start (within box) to a cell out_of() says is outside the fen, or None."""
    came, q = {start: None}, deque([start])
    while q:
        c = q.popleft()
        if out_of(c):
            path = []
            while c is not None:
                path.append(c)
                c = came[c]
            return path[::-1]
        for n in ((c[0] + 1, c[1]), (c[0] - 1, c[1]), (c[0], c[1] + 1), (c[0], c[1] - 1)):
            if n not in came and box[0] <= n[0] <= box[2] and box[1] <= n[1] <= box[3] and walkable(w, n, tiles):
                came[n] = c
                q.append(n)
    return None


def outside_fen(c):
    return c[0] > 40 or c[1] > 236


def shut_the_fen(w, tiles, near_built):
    """The old way in gone: Mirefold's boardwalk to the beach, and the beach along the range's north end (the range
    runs down into the sea there now). Returns the cells made rock."""
    gone = [(x, y) for x in range(-27, -20) for y in range(78, 104) if w.tile(x, y) in ("Boardwalk001", "Plank001")]
    w.rewild(gone, seed="fen")
    rock = []
    for x in range(-2, 15):
        for y in range(76, 102):
            text = w.cell(x, y)
            if text and W.natural(text) and not W.watery(text) and not W.PEAKY.match(W.parts(text)[0]):
                w.put(x, y, peak_tile((x, y)))
                rock.append((x, y))
    return rock


def mouth_tile(gx, gy, name):
    """A dark opening drawn on the range's texture where it falls on gx, gy (build_hollow_hill.py's way)."""
    import build_hollow_hill as HH
    img = HH.texture_cell(gx, gy)
    for y in range(32):
        for x in range(32):
            dx, dy = (x - 16) / 13.0, (y - 32) / 24.0
            d = dx * dx + dy * dy
            if d <= 1:
                c = int(8 + 22 * d)
                K.put(img, x, y, (c, c - 2, c + 2))
            elif d <= 1.28 and y < 31:
                K.put(img, x, y, (150, 156, 170) if x < 16 and y < 20 else (58, 60, 72))
    for x, y in ((9, 30), (12, 31), (21, 30), (23, 31), (17, 31)):
        K.put(img, x, y, (96, 92, 88))
    K.save("Tiles", name, img)
    SK.copy_tile(name, "Cave_Mouth001", Examine_Info="A tunnel into the mountain. A cold, wet wind breathes out "
                                                     "of it, smelling of the fen.")
    SK.minimap_colour(name, (24, 20, 22))


def find_mouth(w, near, side, tiles):
    """The peak nearest near with open, walkable ground on its side (+1 east, -1 west)."""
    best = None
    for dx in range(-12, 13):
        for dy in range(-10, 11):
            c = (near[0] + dx, near[1] + dy)
            o = (c[0] + side, c[1])
            if w.tile(*c) and W.PEAKY.match(w.tile(*c)) and walkable(w, o, tiles) and \
                    W.natural(w.cell(*o)) and not W.watery(w.cell(*o)):
                d = abs(dx) + abs(dy)
                if best is None or d < best[0]:
                    best = (d, c, o)
    return best[1], best[2]


def tunnel(w, tiles, west, east):
    """The Mire Tunnel's level (z -1, under the range): a winding tunnel, two chambers, steps up at either end."""
    rng = random.Random("mire tunnel")
    (wm, _), (em, _) = west, east
    way = [wm]
    n = 7
    for i in range(1, n):
        t = i / n
        x = wm[0] + (em[0] - wm[0]) * t
        y = wm[1] + (em[1] - wm[1]) * t + 7 * math.sin(t * math.pi * 2.3) + rng.uniform(-2, 2)
        way.append((x, y))
    way.append(em)
    floor = set()
    for (x0, y0), (x1, y1) in zip(way, way[1:]):
        k = int(math.hypot(x1 - x0, y1 - y0) * 3) + 1
        for i in range(k + 1):
            cx, cy = x0 + (x1 - x0) * i / k, y0 + (y1 - y0) * i / k
            r = 1.2 + 0.7 * fbm(cx, cy, 6, 1221)
            floor |= {(int(round(cx + dx)), int(round(cy + dy))) for dx in (-2, -1, 0, 1, 2) for dy in (-2, -1, 0, 1, 2)
                      if dx * dx + dy * dy <= r * r}
    chambers = [way[2], way[5]]
    for cx, cy in chambers:
        floor |= {(int(cx) + dx, int(cy) + dy) for dx in range(-4, 5) for dy in range(-3, 4)
                  if (dx / 4.3) ** 2 + (dy / 3.2) ** 2 <= 1 + rng.uniform(-0.1, 0.1)}
    names = sorted({(c[0] // XT, c[1] // YT) for c in floor} |
                   {((c[0] + dx) // XT, (c[1] + dy) // YT) for c in floor for dx in (-1, 1) for dy in (-1, 1)})
    maps = {}
    for mx, my in names:
        name = W.mname(mx, my, -1)
        assert not SK.map_exists(name), "%s is there already" % name
        m = W.Map(name, new=True)
        maps[(mx, my)] = m

    def put(c, tile, decor=""):
        m = maps.get((c[0] // XT, c[1] // YT))
        if m is not None:
            m.rows[c[1] % YT][c[0] % XT] = tile + ("+Decor(%s)" % decor if decor else "")
    for c in floor:
        r = rng.random()
        put(c, "Cave_Floor001" if r < 0.6 else "Cave_Floor002" if r < 0.85 else "Cave_Floor003" if r < 0.97
            else "Cave_Puddle001")
    walls = {(c[0] + dx, c[1] + dy) for c in floor for dx in (-1, 0, 1) for dy in (-1, 0, 1)} - floor
    for c in walls:
        face = (c[0], c[1] + 1) in floor
        put(c, ("Cave_Wall003" if rng.random() < 0.08 else "Cave_Wall002") if face else "Cave_Wall001")
    put(wm, "Cave_Steps001")
    put(em, "Cave_Steps001")

    def place(c, kind, opts):
        m = maps[(c[0] // XT, c[1] // YT)]
        m.ents.append("%s\t%s\t%d\t%d\t%s" % ("NPC" if kind not in ("Cave_Mushroom",) else "MapItem", kind,
                                               (c[0] % XT) * TW, (c[1] % YT) * TW - (8 if kind != "Cave_Mushroom" else 0),
                                               opts))

    def spot(near, r=3):
        opts = [c for c in floor if abs(c[0] - near[0]) + abs(c[1] - near[1]) <= r and c not in (wm, em) and
                all((c[0] + i, c[1] + j) in floor for i in (-1, 0, 1) for j in (-1, 0, 1)) and
                (c[0] // XT, c[1] // YT) in maps]
        return rng.choice(opts) if opts else None

    def zone(c, r):
        mx, my = c[0] // XT, c[1] // YT
        return "%d,%d,%d,%d" % (max(1, c[0] - r - mx * XT + 1), max(1, c[1] - r - my * YT + 1),
                                min(XT, c[0] + r - mx * XT + 1), min(YT, c[1] + r - my * YT + 1))
    for kind, at in (("Bat", way[1]), ("Bat", way[3]), ("Giant_Spider", chambers[0]), ("Giant_Spider", chambers[1]),
                     ("Giant_Spider", way[6]), ("Rat", way[4])):
        c = spot((int(at[0]), int(at[1])), 4)
        if c:
            place(c, kind, "Attitude=Bad Zone=%s" % zone(c, 3))
    for at in chambers:
        c = spot((int(at[0]), int(at[1])), 3)
        if c:
            place(c, "Cave_Mushroom", "1")
    traps = ["Darts", "Gas", "Pit", "Weakness"]
    used = set()
    for i, at in enumerate((way[2], way[3], way[4], way[5])):
        c = spot((int(at[0]) + 2, int(at[1])), 4)
        if c and c not in used:
            used.add(c)
            maps[(c[0] // XT, c[1] // YT)].ents.append("Trigger\tTrap_%s\t%d\t%d" % (traps[i], c[0] % XT + 1,
                                                                                    c[1] % YT + 1))
    for m in maps.values():
        m.save()
    wa = min((c for c in floor if abs(c[0] - wm[0]) + abs(c[1] - wm[1]) == 1), key=lambda c: (c[0] - wm[0]) * -1)
    ea = min((c for c in floor if abs(c[0] - em[0]) + abs(c[1] - em[1]) == 1), key=lambda c: (c[0] - em[0]))
    return [W.mname(mx, my, -1) for mx, my in maps], wa, ea


def pixel(c):
    return "%d,%d" % ((c[0] % XT) * TW, (c[1] % YT) * TW - 8)


def tunnel_scripts(west, east, wa, ea):
    (wm, wo), (em, eo) = west, east
    for side, mouth, out, arrive, words in (
            ("West", wm, wo, wa, "You duck into the tunnel. The fen's damp follows you in."),
            ("East", em, eo, ea, "You duck into the tunnel. Water drips somewhere ahead, and something rustles.")):
        SK.write_script("Enter Mire_Tunnel_%s" % side, [
            (">Distance.From.Clicked.Tile", "48", "@far"),
            ("Play.Sound", "Ladder"),
            ("Display.Message", "Cyan", words, "-"),
            ("Teleport", pixel(arrive), W.mname(arrive[0] // XT, arrive[1] // YT, -1)),
            ("End",),
            ("@far",), ("Display.Message", "DarkRed", "You are too far away!", "Denied"), ("End",)], MAKER)
        SK.write_script("Climb Up Mire_Tunnel_%s_Steps" % side, [
            (">Distance.From.Clicked.Tile", "48", "@far"),
            ("Play.Sound", "Ladder"),
            ("Wait", "0.4"),
            ("Teleport", pixel(out), W.mname(out[0] // XT, out[1] // YT, 0)),
            ("End",),
            ("@far",), ("Display.Message", "DarkRed", "You are too far away!", "Denied"), ("End",)], MAKER)


def ids_below(levels, west, east):
    for side, (mouth, _) in (("West", west), ("East", east)):
        name = W.mname(mouth[0] // XT, mouth[1] // YT, -1)
        m = W.Map(name)
        SK.place_id(m, "Mire_Tunnel_%s_Steps" % side, mouth[0] % XT + 1, mouth[1] % YT + 1)
        m.save()
    amb = os.path.join(ROOT, "data", "Ambient.ini")
    s = W.read(amb)
    for name in levels:
        if "\r\n%s=" % name not in s:
            s = s.replace("[Maps]\r\n", "[Maps]\r\n%s=Cave\r\n" % name, 1)
    W.write(amb, s)


def main():
    if os.path.exists(DONE):
        print("The west's been reshaped already (delete %s to do it again)." % DONE)
        return
    w = W.World(0)
    built, near_built = guarded(w, (-340, 30, 120, 490))
    tiles = walkable_tiles()
    sea, land, drowned = coast(w, built, near_built)
    print("The coast: %d cells sea now, %d land now, %d things drowned" % (sea, land, drowned))
    built, near_built = guarded(w, (-340, 30, 120, 490))
    to_peak, to_grass = mountains(w, built, near_built)
    print("The mountains: %d cells rock now, %d open now" % (len(to_peak), len(to_grass)))
    rock = shut_the_fen(w, tiles, near_built) + close_field(w)
    print("The fen shut: %d cells of the old beach rock now" % len(rock))
    west = find_mouth(w, TUNNEL_W, -1, tiles)
    east = find_mouth(w, TUNNEL_E, 1, tiles)
    new_peaks = {c for c in set(to_peak) | set(rock) if W.PEAKY.match(w.tile(*c))}
    repeak(w, new_peaks)
    for side, (mouth, out) in (("West", west), ("East", east)):
        tile = "Mire_Tunnel_Mouth%03d" % (1 if side == "West" else 2)
        mouth_tile(mouth[0], mouth[1], tile)
        w.put(mouth[0], mouth[1], tile)
        w.place_id(mouth[0], mouth[1], "Mire_Tunnel_%s" % side)
    _, mf = w.find_id("Mirefold_Square")
    streets = {(x, y) for x in range(-170, -20) for y in range(60, 140) if w.cell(x, y) and W.is_road(w.cell(x, y))}
    W.join_roads(w, [west[1]], network=streets)
    roads_e = {(x, y) for x in range(east[1][0], east[1][0] + 60) for y in range(east[1][1] - 40, east[1][1] + 40)
               if w.cell(x, y) and W.is_road(w.cell(x, y))}
    W.join_roads(w, [east[1]], network=roads_e)
    way_out = leaks(w, tiles, mf, (-330, 40, 120, 260), outside_fen)
    if way_out:
        print("!! a way out of the fen, not by the tunnel: %s" % [c for c in way_out if c[0] > -60][:40])
        return
    print("From Mirefold: shut in, but for the tunnel")
    n = w.save()
    levels, wa, ea = tunnel(w, tiles, west, east)
    tunnel_scripts(west, east, wa, ea)
    ids_below(levels, west, east)
    SK.place_label("Places", "The Mire Tunnel", "Mire_Tunnel_East")
    print("The Mire Tunnel: %s to %s, under the range (%s); %d maps changed" % (west[0], east[0], ", ".join(levels), n))
    open(DONE, "w").write("reshaped\n")


if __name__ == "__main__":
    main()
