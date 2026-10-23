"""The grotto (the caves under the Isle) a level deeper, its way in only through the chapel. Run it once (again: it
sees it's done).

  python -I "Dev\\migrate\\deepen_grotto.py"

  * The caves move from level -1 to -2: Maps\\2,1,-1 -> 2,1,-2, and the cave half of 1,1,-1 -> 1,1,-2. What stays on
    1,1,-1 is the beggar's cellar (its goblin and its axe), walled off from the caves: the way into it is the beggar's
    house, with its key (the quest), as it should be.
  * Under the chapel's cellar (3,1,-1) a new cave, 3,1,-2: the hole in the cellar floor drops straight down to its
    ladder (the same spot, one level down), and a tunnel runs west into the grotto. From the cellar, there's nothing
    of the caves to see: they're a level below.
"""
import os
import random
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dragonsword import ini  # noqa: E402
from build_isle import Map, XT, YT, TW, DATA, obj_line  # noqa: E402

MAPS = os.path.join(ROOT, "Maps")
CELLAR = (17, 3, 22, 7)          # (the beggar's cellar on 1,1,-1: brick walls x17-22, y3-7)
GAP = (19, 7)                    # (where it opened into the caves)
HOLE = (14, 9)                   # (the hole in the chapel cellar's floor, 3,1,-1)
TUNNEL_ROW = 12                  # (the tunnel from the new cave into the grotto, along this row)


def in_cellar(x, y):
    x1, y1, x2, y2 = CELLAR
    return x1 <= x <= x2 and y1 <= y <= y2


def ent_tile(ln):
    p = ln.split("\t")
    try:
        return int(float(p[2]) // TW) + 1, int(float(p[3]) // TW) + 1
    except (IndexError, ValueError):
        return None


def split_beggar_cellar():
    """1,1,-1 keeps the cellar (walled up where it met the caves); the caves go to 1,1,-2."""
    m = Map("1,1,-1")
    deep = Map("1,1,-1")
    deep.name, deep.path = "1,1,-2", os.path.join(MAPS, "1,1,-2.txt")
    for y in range(1, YT + 1):
        for x in range(1, XT + 1):
            if in_cellar(x, y):
                deep.rows[y - 1][x - 1] = "Black001"
            else:
                m.rows[y - 1][x - 1] = "Black001"
    for y in range(1, YT + 1):                                   # (no cave left showing round the cellar)
        for x in range(1, XT + 1):
            if m.tile(x, y).startswith("Cave"):
                m.set(x, y, tile="Black001", decor="")
    m.set(*GAP, tile="Brick001", decor="")                      # (the cellar's wall, whole)
    deep.set(*GAP, tile="Cave_Wall001", decor="")               # (and the cave's, the other side)
    keep, down = [], []
    for ln in m.ents:
        t = ent_tile(ln) if ln.split("\t")[0] in ("NPC", "StaticObject", "MapItem") else None
        (keep if t is None or in_cellar(*t) else down).append(ln)
    m.ents, deep.ents = keep, down
    m.save()
    deep.save()
    print("1,1,-1: the beggar's cellar on its own; its caves are 1,1,-2")


def move_grotto():
    src, dst = os.path.join(MAPS, "2,1,-1.txt"), os.path.join(MAPS, "2,1,-2.txt")
    os.replace(src, dst)
    entry = os.path.join(DATA, "Scripts", "2,1,-1.txt")                # (its entry message goes with it)
    if os.path.exists(entry):
        os.replace(entry, os.path.join(DATA, "Scripts", "2,1,-2.txt"))
    g = Map("2,1,-2")
    for y in range(1, YT + 1):                                   # (its old ladder up: gone; the way out is east)
        for x in range(1, XT + 1):
            if g.decor(x, y).startswith(("Cave_Ladder", "Ladder")):
                g.set(x, y, decor="")
    for x in (23, 24, 25):                                       # (a tunnel east, out to the new cave under the chapel)
        g.set(x, TUNNEL_ROW, tile="Cave_Floor001", decor="")
        for dy in (-1, 1):
            if not g.tile(x, TUNNEL_ROW + dy).startswith("Cave_Floor"):
                g.set(x, TUNNEL_ROW + dy, tile="Cave_Wall001", decor="")
    g.save()
    print("2,1,-1 -> 2,1,-2 (the grotto, a level deeper), a tunnel east")


def under_chapel():
    rng = random.Random(311)
    m = Map("3,1,-2", new=True)
    floor = set()
    for x in range(1, HOLE[0] + 1):                              # the tunnel from the grotto, wandering a little
        dy = 0 if x < 4 else (1 if 6 <= x <= 9 else 0)
        for y in (TUNNEL_ROW + dy, TUNNEL_ROW + dy - (1 if x % 3 == 0 else 0)):
            floor.add((x, y))
    cx, cy = HOLE
    for y in range(cy - 3, cy + 5):                              # a chamber under the cellar, the ladder in it
        for x in range(cx - 4, cx + 5):
            if ((x - cx) / 4.3) ** 2 + ((y - cy - 0.5) / 3.6) ** 2 <= 1:
                floor.add((x, y))
    for y in range(1, YT + 1):
        for x in range(1, XT + 1):
            if (x, y) in floor:
                m.set(x, y, tile=rng.choice(["Cave_Floor001", "Cave_Floor001", "Cave_Floor003"]))
            elif any((x + dx, y + dy) in floor for dx in (-1, 0, 1) for dy in (-1, 0, 1)):
                m.set(x, y, tile=rng.choice(["Cave_Wall001", "Cave_Wall002"]))
    m.set(*HOLE, decor="Cave_Ladder001")
    for x, y in ((cx + 3, cy + 2), (cx - 3, cy + 1)):
        if (x, y) in floor:
            m.set(x, y, tile="Stalagmite001")
    m.ents = [obj_line("NPC", "Bat", 11, TUNNEL_ROW, "Attitude=Bad Zone=10,%d,18,%d" % (TUNNEL_ROW - 6, TUNNEL_ROW + 1)),
              obj_line("MapItem", "Bones", cx + 2, cy - 2, "1"),
              "Id\tChapel_Cave\t%d\t%d" % (cx, cy + 1)]
    m.save()
    print("Made Maps\\3,1,-2 (the cave under the chapel: the ladder up, a tunnel west to the grotto)")


def scripts_and_data():
    def script(name, lines):
        with open(os.path.join(DATA, "Scripts", name + ".txt"), "w", encoding="cp1252", newline="\r\n") as f:
            f.write("// Generated by Dev\\migrate\\deepen_grotto.py\n" + "\n".join(lines) + "\n")
    hx, hy = HOLE
    script("Climb Down Basement_Hole", [
        "01\tPlay.Sound\tLadder",
        "02\tDisplay.Message\tCyan\tYou climb down the ladder, into the caves under the Isle.",
        "03\tTeleport\t%d,%d\t3,1,-2" % ((hx - 1) * TW, hy * TW - 8),
        "04\tEnd"])
    script("Climb Up Cave_Ladder", [
        "01\tPlay.Sound\tLadder",
        "02\tDisplay.Message\tCyan\tYou climb up the ladder, into the chapel cellar.",
        "03\tTeleport\t%d,%d\t3,1,-1" % ((hx - 1) * TW, hy * TW - 8),
        "04\tEnd"])
    for f in ("Ambient.ini", "Music.ini"):                       # (cave music and sounds down there)
        path = os.path.join(DATA, f)
        text = open(path, "rb").read().decode("cp1252")
        nl = "\r\n" if "\r\n" in text else "\n"
        for name in ("1,1,-2", "2,1,-2", "3,1,-2"):
            if name + "=" not in text:
                text = text.replace(nl + "2,1,-1=Cave", nl + "2,1,-1=Cave" + nl + name + "=Cave", 1)
        text = text.replace(nl + "2,1,-1=Cave", "")
        open(path, "wb").write(text.encode("cp1252"))
    print("Scripts: the hole goes straight down, the ladder straight up; cave music on level -2")


def main():
    if os.path.exists(os.path.join(MAPS, "2,1,-2.txt")):
        print("The grotto is a level deeper already")
        return
    split_beggar_cellar()
    move_grotto()
    under_chapel()
    scripts_and_data()


if __name__ == "__main__":
    main()
