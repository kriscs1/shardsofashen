"""People asleep in bed: <Name>_Sleep4.png for every friendly person (an NPC walked in four directions,
sprites\\Walk\\<Name>4a.png), what dsengine/npcs.py shows when one with a Bed= is in it at night. Seen from above: the
head on the pillow, eyes shut, and the turned-down sheet across the shoulders; the bed's own quilt (Bed001, Bed002)
covers the rest. It's laid 2 px below the top of the bed's head tile, so the head lies on the pillow and the sheet
over the sheet's fold. The pixels are the walking frame's own, so a trade's other colourings (Looks) recolour it too.
Run it again to draw them again.

  python -I "dev\\migrate\\build_sleepers.py"
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame  # noqa: E402
from ashen import ini  # noqa: E402

WALK = os.path.join(ROOT, "sprites", "Walk")
OUT = os.path.join(ROOT, "sprites", "Entities")
HEAD = 10                   # (rows of the head, from the top of the hair)
TOP = 3                     # (where the head starts in the picture: on the pillow)
SHEET = ((236, 226, 200), (206, 192, 160))   # (the turned-down sheet, its fold's shade: Bed001's)
OUTLINE = (34, 30, 30)
NOT_PEOPLE = {"Horse_Cart"}


def people():
    """The friendly kinds walked in four directions (townsfolk, traders, the story's people)."""
    path = os.path.join(ROOT, "data", "Entities.ini")
    get = lambda n, k: (ini.read(n, k, "", path) or "").strip()
    out = []
    for f in sorted(os.listdir(WALK)):
        if not f.endswith("4a.png"):
            continue
        name = f[:-6]
        if name in NOT_PEOPLE or get(name, "Attitude") == "Bad":
            continue
        if get(name, "Type") not in ("NPC", "GoodNPC", ""):
            continue
        out.append(name)
    return out


def sleeper(walk):
    """The asleep picture from a front-facing walking frame."""
    w, h = walk.get_size()
    rows = [y for y in range(h) if any(walk.get_at((x, y)).a > 40 for x in range(w))]
    top = rows[0] if rows else 0
    out = pygame.Surface((w, h), pygame.SRCALPHA)
    mid = top + HEAD // 2                           # (the head alone: the widest run across the face, not a staff)
    runs, run = [], []
    for x in range(w + 1):
        if x < w and walk.get_at((x, mid)).a > 40:
            run.append(x)
        elif run:
            runs.append(run)
            run = []
    head = max(runs, key=len) if runs else [0, w - 1]
    for y in range(HEAD):
        for x in range(head[0] - 1, head[-1] + 2):
            c = walk.get_at((x, top + y))
            if c.a > 40:
                out.set_at((x, TOP + y), c)
    # eyes shut: the darkest pixels of the face (its eyes) become a lid's line, one row down
    face = [(x, y) for y in range(TOP + 4, TOP + HEAD - 2) for x in range(w)
            if out.get_at((x, y)).a > 40 and sum(out.get_at((x, y))[:3]) < 200 and
            out.get_at((x - 1, y)).a > 40 and out.get_at((x + 1, y)).a > 40 and
            sum(out.get_at((x - 1, y))[:3]) > 350 and sum(out.get_at((x + 1, y))[:3]) > 350]
    for x, y in face:
        skin = out.get_at((x - 1, y))
        out.set_at((x, y), skin)
        lid = tuple(max(0, v - 90) for v in skin[:3])
        out.set_at((x, y + 1), lid)
    # the sheet across the shoulders, turned down over the quilt, a dark edge round it
    xs = [x for x in range(w) if any(out.get_at((x, y)).a > 40 for y in range(TOP, TOP + HEAD))]
    x0, x1 = max(7, min(xs) - 4), min(25, max(xs) + 4)          # (inside the bed's frame, x 7-25)
    y0 = TOP + HEAD - 1
    for y in range(y0, y0 + 3):
        for x in range(x0, x1 + 1):
            edge = x in (x0, x1) or y == y0 + 2
            out.set_at((x, y), OUTLINE if edge else (SHEET[1] if y == y0 + 1 else SHEET[0]))
    return out


def main():
    pygame.init()
    made = 0
    for name in people():
        walk = pygame.image.load(os.path.join(WALK, name + "4a.png"))
        pygame.image.save(sleeper(walk), os.path.join(OUT, name + "_Sleep4.png"))
        made += 1
    print("asleep in bed: %d people (sprites\\Entities\\<Name>_Sleep4.png)" % made)


if __name__ == "__main__":
    main()
