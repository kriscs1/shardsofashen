"""Walking frames for the NPCs and monsters, so they turn to face the way they move (Sprites\\Walk\\*.png).

Run:  python -I "Dev\\migrate\\build_walk.py" [--preview]
Deterministic and re-runnable: only frames that change are written. --preview writes Dev\\Renders\\Walk preview.png.
Re-run it after changing an NPC's sprite in Sprites\\Entities (build_sprites.py, or by hand).

Each sprite in Sprites\\Entities is the standing pose; the frames are made from it:
  * FRONT (people, goblins, skeletons, the troll: drawn facing the viewer). Four directions, the same frame names as
    the player: <Name><Dir><Frame>, Dir 1 = north (away), 2 = east, 4 = south (towards you), 8 = west; Frame a =
    standing, b and c = a step with the left and the right foot.
      south  the sprite itself, with the feet stepping
      north  the back: mirrored (so what they hold swaps hands, as seen from behind), the face painted over with the
             hair, hat or helmet colour (or the skin, shaded, for bald heads)
      east   the face slides towards the east and the back of the head shows hair: a three-quarter view
      west   the east frames mirrored
  * SIDE (animals: drawn side-on, all facing west). Two directions, east (mirrored) and west; walking going north or
    south keeps the way it last faced. Frames b and c bob the body and move the legs apart and together.
  * FLAP (the bat and the giant spider: symmetric, seen from the front). Two directions; the frames bob.
The game (animation_available in dragonsword\\entities.py) loads Sprites\\Walk\\<Name>1a.png ... the first time an entity of
that name is shown: all 12 frames = four directions, <Name>2a..c and <Name>8a..c only = side-on.
"""
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sprite_kit as K
import build_people as BPEOPLE
from common import p

FRONT = ["Cave_Troll", "Bog_Troll", "Frost_Troll"]          # the people and goblins come from build_people.py
SIDE = ["Wolf", "Rat", "Cow", "Tallulah", "Sheep", "Chicken", "Dog", "Rabbit", "Duck", "Bear", "Snow_Wolf", "Alpha_Wolf"]          # all drawn facing west
FLAP = ["Bat", "Giant_Spider", "Butterfly", "Scorpion", "Dragon"]
OUT = "Walk"
BALD = {"Skeleton"}            # the back of the head is shaded skin (or bone), whatever frames the face
HEAD = {"Cave_Troll": (6, 15), "Bog_Troll": (6, 15), "Frost_Troll": (6, 15)}  # (first row, neck row) where finding them by shape fails (the troll has no neck)
NAME = ""                      # the sprite being built (for BALD and HEAD)


# ------------------------------------------------------------------ image helpers (img = rows of (r,g,b) or None)
def mirror(img):
    return [list(reversed(r)) for r in img]


def blank_like(img):
    return [[None] * len(img[0]) for _ in img]


def lum(c):
    return 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]


def runs(row):
    """[(x0, x1)] runs of drawn pixels in a row."""
    out, start = [], None
    for x, c in enumerate(row + [None]):
        if c is not None and start is None:
            start = x
        elif c is None and start is not None:
            out.append((start, x - 1))
            start = None
    return out


def opaque_rows(img):
    ys = [y for y, r in enumerate(img) if any(c is not None for c in r)]
    return ys[0], ys[-1]


def body_centre(img, top, bottom):
    """Middle column of the body: the median x of the drawn pixels in the middle third of the figure."""
    xs = []
    for y in range(top + (bottom - top) // 3, top + 2 * (bottom - top) // 3 + 1):
        xs += [x for x, c in enumerate(img[y]) if c is not None]
    xs.sort()
    return xs[len(xs) // 2] if xs else len(img[0]) // 2


def run_at(row, cx, reach=3):
    """The run containing column cx (or the nearest within reach)."""
    best = None
    for x0, x1 in runs(row):
        d = 0 if x0 <= cx <= x1 else min(abs(cx - x0), abs(cx - x1))
        if d <= reach and (best is None or d < best[0]):
            best = (d, x0, x1)
    return (best[1], best[2]) if best else None


# ------------------------------------------------------------------ front figures
def analyse(img):
    top, bottom = opaque_rows(img)
    cx = body_centre(img, top, bottom)
    # neck: the narrowest row of the body's run, 4..14 rows below the top of the head
    widths = []
    for y in range(top + 4, min(bottom, top + 14) + 1):
        r = run_at(img[y], cx)
        if r:
            widths.append((r[1] - r[0], y))
    neck = min(widths)[1] if widths else top + 8
    # the head starts at the first row whose drawn run is on the body's centre line (not a spear tip or a staff)
    head_top = next((y for y in range(top, neck) if run_at(img[y], cx, reach=1)), top)
    if NAME in HEAD:
        head_top, neck = HEAD[NAME]
    # skin: the colour around the eyes (the whites, or the brightest pixels of the face); failing that, the most
    # common colour across the middle third of the head
    face, near_eyes = Counter(), Counter()
    for y in range(head_top, neck):
        r = run_at(img[y], cx, reach=1)
        if not r:
            continue
        for x in range(r[0], r[1] + 1):
            c = img[y][x]
            if c is not None and lum(c) > 235:
                for yy, xx in ((y, x - 1), (y, x + 1), (y - 1, x), (y + 1, x)):
                    n = img[yy][xx] if 0 <= yy < len(img) and 0 <= xx < len(img[0]) else None
                    if n is not None and 60 < lum(n) <= 235:
                        near_eyes[n] += 1
            if head_top + (neck - head_top) // 3 <= y <= head_top + 2 * (neck - head_top) // 3:
                if c is not None and lum(c) > 40:
                    face[c] += 1
    skin = (near_eyes or face).most_common(1)[0][0] if (near_eyes or face) else None
    # hair / hat / helmet: what frames the face. The colours at both edges of each row of the face, and right across
    # the two rows above it; skin doesn't count (bald heads, goblins: their back of the head is shaded skin)
    face_ys = [y for y in range(head_top, neck) if skin is not None and skin in img[y]]
    frame = Counter()
    if face_ys:
        for y in face_ys:
            r = run_at(img[y], cx, reach=1)
            if r:
                for x in (r[0], r[0] + 1, r[1] - 1, r[1]):
                    frame[img[y][x]] += 1
        for y in (face_ys[0] - 1, face_ys[0] - 2):
            r = run_at(img[y], cx, reach=1) if y >= 0 else None
            if r:
                for x in range(r[0], r[1] + 1):
                    frame[img[y][x]] += 2
    frame.pop(skin, None)
    frame.pop(None, None)
    hair = frame.most_common(1)[0][0] if frame else None
    if hair is not None and frame[hair] < 4:
        hair = None                                  # a stray outline pixel or two: treat as bald
    if NAME in BALD:
        hair = None
    # legs: rows near the bottom where the body's centre column is see-through (a gap between the legs)
    leg_top = bottom - 2
    y = bottom
    while y > top + (bottom - top) // 2:
        row = img[y]
        gap = row[cx] is None or (cx + 1 < len(row) and row[cx + 1] is None and row[cx - 1] is None)
        if gap and any(c is not None for c in row[:cx]) and any(c is not None for c in row[cx + 1:]):
            leg_top = y
            y -= 1
        elif y >= bottom - 2:
            y -= 1                 # feet/boots rows may join up; keep looking above them
        else:
            break
    return dict(top=top, head_top=head_top, bottom=bottom, cx=cx, neck=neck, skin=skin, hair=hair,
                leg_top=min(leg_top, bottom - 2))


def step(img, a, side):
    """A step: one leg (side -1 = the figure's left half on screen, +1 = right) lifted by a pixel."""
    out = [list(r) for r in img]
    cx = a["cx"]
    xs = range(0, cx) if side < 0 else range(cx + 1, len(img[0]))
    for x in xs:
        for y in range(a["leg_top"], a["bottom"] + 1):
            out[y][x] = img[y + 1][x] if y + 1 <= a["bottom"] else None
            if y == a["leg_top"] and img[y][x] is not None and out[y][x] is None:
                out[y][x] = img[y][x]          # don't open a hole at the hip
    return out


def head_rows(a):
    return range(a["head_top"], a["neck"])


def face_rows(img, a):
    """Rows of the head that show face (contain skin), up to the neck."""
    rows = [y for y in head_rows(a) if a["skin"] is not None and a["skin"] in img[y]]
    return range(rows[0], a["neck"]) if rows else range(0)


def is_outline(c):
    return c is not None and lum(c) < 34


def back_view(img, a):
    out = [list(r) for r in img]
    fill = a["hair"]
    if fill is None or fill == a["skin"]:
        fill = K.mul(a["skin"], 0.85) if a["skin"] else None
    if fill is None:
        return mirror(out)
    for y in face_rows(img, a):
        r = run_at(img[y], a["cx"], reach=2)
        if not r:
            continue
        x0, x1 = r
        for x in range(x0, x1 + 1):
            c = img[y][x]
            if c is None or (is_outline(c) and (x == x0 or x == x1)):
                continue
            out[y][x] = fill
    # a little shading down the middle of the back of the head
    for y in face_rows(img, a):
        if out[y][a["cx"]] == fill:
            out[y][a["cx"]] = K.mul(fill, 0.86)
    return mirror(out)


def side_view(img, a, shift=2):
    """East: the face slides east, hair (or skin) shows at the back of the head (west side)."""
    out = [list(r) for r in img]
    back = a["hair"] if a["hair"] is not None else (K.mul(a["skin"], 0.85) if a["skin"] else None)
    for y in face_rows(img, a):
        r = run_at(img[y], a["cx"], reach=2)
        if not r:
            continue
        x0, x1 = r
        inner = list(range(x0 + 1, x1))
        if len(inner) <= shift + 1:
            continue
        for x in inner:
            src = x - shift
            if src >= x0 + 1:
                out[y][x] = img[y][src]
            else:
                out[y][x] = back if back is not None else img[y][x]
    return out


def front_frames(img):
    a = analyse(img)
    south = img
    north = back_view(img, a)
    east = side_view(img, a)
    frames = {}
    for d, base in (("4", south), ("1", north), ("2", east)):
        frames[d + "a"] = base
        frames[d + "b"] = step(base, a, -1)
        frames[d + "c"] = step(base, a, +1)
    for f in "abc":
        frames["8" + f] = mirror(frames["2" + f])
    return frames, a


# ------------------------------------------------------------------ side-on animals and flappers
def shift_rows(img, y0, y1, dy):
    """Moves rows y0..y1 by dy (up < 0), leaving the rest."""
    out = [list(r) for r in img]
    for y in range(y0, y1 + 1):
        out[y] = [None] * len(img[0])
    for y in range(y0, y1 + 1):
        ny = y + dy
        if 0 <= ny < len(img):
            for x, c in enumerate(img[y]):
                if c is not None:
                    out[ny][x] = c
    return out


def animal_frames(img):
    top, bottom = opaque_rows(img)
    widths = [sum(1 for c in img[y] if c is not None) for y in range(top, bottom + 1)]
    widest = max(widths)
    # legs: the bottom rows that are much narrower than the body
    leg_top = bottom
    for y in range(bottom, top, -1):
        if sum(1 for c in img[y] if c is not None) < widest * 0.55:
            leg_top = y
        else:
            break
    xs = [x for y in range(top, bottom + 1) for x, c in enumerate(img[y]) if c is not None]
    mid = (min(xs) + max(xs)) // 2

    def legs(spread):
        out = shift_rows(img, top, leg_top - 1, -1)          # the body bobs up a pixel
        for y in range(leg_top, bottom + 1):
            row = [None] * len(img[0])
            for x, c in enumerate(img[y]):
                if c is None:
                    continue
                nx = x + (spread if x >= mid else -spread)
                if 0 <= nx < len(row):
                    row[nx] = c
            out[y] = row
        # stretch: the row just above the legs repeats so there is no gap under the lifted body
        if leg_top - 1 >= 0:
            out[leg_top - 1] = [c if c is not None else img[leg_top - 1][x] for x, c in enumerate(out[leg_top - 1])]
        return out

    west = {"a": img, "b": legs(1), "c": legs(-1) if leg_top < bottom else shift_rows(img, top, bottom, -1)}
    frames = {}
    for f, im in west.items():
        frames["8" + f] = im
        frames["2" + f] = mirror(im)
    return frames, dict(top=top, bottom=bottom, leg_top=leg_top)


def flap_frames(img):
    top, bottom = opaque_rows(img)
    up = shift_rows(img, top, bottom, -1)
    down = shift_rows(img, top, bottom, 1) if bottom + 1 < len(img) else img
    frames = {}
    for f, im in (("a", img), ("b", up), ("c", down)):
        frames["8" + f] = im
        frames["2" + f] = mirror(im)
    return frames, {}


# ------------------------------------------------------------------ main
def frames_for(name):
    global NAME
    NAME = name
    if name in BPEOPLE.PEOPLE:                      # drawn on the player's body: real side and back views
        return BPEOPLE.frames(name), {}
    img = K.load("Entities", name)
    fn = front_frames if name in FRONT else animal_frames if name in SIDE else flap_frames
    return fn(img)


def build():
    made = {}
    for names in (FRONT, SIDE, FLAP, [n for n in BPEOPLE.PEOPLE if n not in FRONT]):
        for name in names:
            made[name] = frames_for(name)
    return made


def main():
    os.makedirs(p("Sprites", OUT), exist_ok=True)
    made = build()
    wanted = set()
    written = 0
    for name, (frames, _) in made.items():
        for key, im in frames.items():
            wanted.add(name + key)
            if K.save(OUT, name + key, im):
                written += 1
    stale = [f for f in os.listdir(p("Sprites", OUT)) if f.lower().endswith(".png") and f[:-4] not in wanted]
    for f in stale:
        os.remove(p("Sprites", OUT, f))
    print("%d frame(s) for %d sprites, %d written, %d stale removed" % (len(wanted), len(made), written, len(stale)))
    if "--preview" in sys.argv:
        items = []
        for name, (frames, _) in made.items():
            for d in ("4", "1", "2", "8"):
                for f in "abc":
                    if d + f in frames:
                        items.append(frames[d + f])
        K.sheet(p("Dev", "Renders", "Walk preview.png"), items, scale=3, cols=12)
        print("preview: Dev\\Renders\\Walk preview.png (one row per front figure: S N E W x a b c)")


if __name__ == "__main__":
    main()
