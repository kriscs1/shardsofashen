"""Homes and beds, and animals kept out of houses by where they roam (not by a rule):

* Townsfolk (an NPC whose kind's hours are Day - Schedule=Day - and that walks in four directions: a person; not one
  with hours of its own on its map line, set up by hand: Maren at her counter by day, upstairs at night) on the world's surface get a house of their own: Home= (the walkable floor under the nearest
  building's roof, on its map) and, where there's a bed free in it, Bed= (its head, Bed001): at night they walk home
  and go to bed (dsengine/npcs.py). The nearest house with a bed free, else the nearest with room (3 to a house), on
  the same map - never a building someone else lives or works in (a person there who isn't townsfolk: Edwin and
  Maren's house, a shop with its keeper at the counter; one an earlier run housed there is moved). Dogs get a home too (the nearest house: no bed).
* A hen's Roost= is Home= now (the coop). The hens on 2,0,0 and the sheep in the churchyard (3,1,0) are Passive.
* The rule that kept animals out of houses (Entities.ini Indoors=0) is gone: instead each animal's Zone= (and its
  Chase=) leaves out the roofed tiles of its map - but the building it stands in at the start (a barn, a coop) and its
  Home. Cats and dogs come in, as before.

Only what isn't there yet is added: a line with Home= or Bed= is left alone, and so is a Zone that keeps out of
houses already. Safe to run again.

  python -I "dev\\migrate\\assign_homes.py"
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from ashen import ini  # noqa: E402
from ashen import areas as AR  # noqa: E402
from dsedit.project import read_text_lines, write_text_lines  # noqa: E402

MAPS = os.path.join(ROOT, "maps")
ENTITIES = os.path.join(ROOT, "data", "Entities.ini")
TILES = os.path.join(ROOT, "data", "Tiles.ini")
W, H, T = 25, 21, 32
PER_HOUSE = 3
# (the animals the Indoors=0 rule kept out of houses - written here as it was, so a second run still knows them)
ANIMALS = {"Chicken", "Rat", "Bat", "Cow", "Sheep", "Wolf", "Giant_Spider", "Rabbit", "Duck", "Butterfly", "Bear",
           "Snow_Wolf", "Alpha_Wolf", "Scorpion", "Dragon", "Ember_Hound", "Blue_Butterfly", "Horse",
           "Galaith_Dragon", "Drake", "Otter", "Seal", "Frog", "Goose", "Duchess"}
PASSIVE = {"2,0,0": {"Chicken"}, "3,1,0": {"Sheep"}}
BEDS = ("Bed001",)                                  # (a bed's head, its foot below it: the ones a person lies in)
OVER = re.compile(r"\+([A-Za-z]+)\(([^)]*)\)")


def kind(name, key, default=""):
    return (ini.read(name, key, default, ENTITIES) or default).strip()


_walk = {}


def walkable(tile):
    if tile not in _walk:
        data = (ini.read(tile, "Walkable.Data", "", TILES) or "").strip()
        _walk[tile] = len(data) == 49 and data[24] == "1" if data else True
    return _walk[tile]


def read_map(name):
    lines = read_text_lines(os.path.join(MAPS, name + ".txt"))
    grid = []
    for row in lines[:H]:
        cells = []
        for c in row.split(":"):
            base = c.split("+")[0]
            over = dict(OVER.findall(c))
            cells.append((base, over))
        grid.append(cells)
    return lines, grid


def buildings(grid):
    """{roof group: {"floor": [(x, y)], "beds": [(x, y)], "mid": (x, y)}} - tiles from 1."""
    out = {}
    for y, row in enumerate(grid, 1):
        for x, (base, over) in enumerate(row, 1):
            roof = over.get("Roof")
            if not roof:
                continue
            b = out.setdefault(roof.rsplit(".", 1)[-1], {"floor": [], "beds": [], "roofed": []})
            b["roofed"].append((x, y))
            decor = over.get("Decor", "")
            if decor in BEDS:
                b["beds"].append((x, y))
            elif walkable(base) and (not decor or walkable(decor)):
                b["floor"].append((x, y))
    for b in out.values():
        xs, ys = [t[0] for t in b["roofed"]], [t[1] for t in b["roofed"]]
        b["mid"] = (sum(xs) / len(xs), sum(ys) / len(ys))
        b["people"] = 0
    return {k: b for k, b in out.items() if len(b["floor"]) >= 4}


def opts_of(f):
    return f[4] if len(f) > 4 else ""


def get_opt(opts, key):
    for w in opts.split():
        if "=" in w and w.split("=", 1)[0].lower() == key.lower():
            return w.split("=", 1)[1]
    return ""


def set_opt(opts, key, value):
    words = [w for w in opts.split() if not ("=" in w and w.split("=", 1)[0].lower() == key.lower())]
    if value:
        words.append("%s=%s" % (key, value))
    return " ".join(words)


_size = {}


def spawn_tile(name, x, y):
    if name not in _size:
        try:
            from PIL import Image
            _size[name] = Image.open(os.path.join(ROOT, "sprites", "Entities", name + ".png")).size
        except OSError:
            _size[name] = (T, T)
    w, h = _size[name]
    return int((x + w / 2) // T) + 1, int((y + h - 1) // T) + 1


def person(name):
    return os.path.exists(os.path.join(ROOT, "sprites", "Walk", name + "4a.png"))


def roofed_part(grid, start):
    """The roofed tiles joined to start (the building an animal starts in)."""
    seen, todo = set(), [start]
    while todo:
        x, y = todo.pop()
        if (x, y) in seen or not (1 <= x <= W and 1 <= y <= H) or not grid[y - 1][x - 1][1].get("Roof"):
            continue
        seen.add((x, y))
        todo += [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
    return seen


def main():
    news = {"home": 0, "bed": 0, "dog": 0, "zone": 0, "chase": 0, "passive": 0, "roost": 0, "moved": 0}
    for f in sorted(os.listdir(MAPS)):
        if not f.endswith(".txt"):
            continue
        name = f[:-4]
        p = name.split(",")
        if len(p) != 3:
            continue
        z = int(p[2])
        lines, grid = read_map(name)
        houses = buildings(grid) if z == 0 else {}
        busy = set()                                 # (a building someone else lives or works in is nobody's home)
        for ln in lines[H:]:
            fl = ln.split("\t")
            if fl[0] != "NPC" or len(fl) < 4 or not person(fl[1]):
                continue
            if not get_opt(opts_of(fl), "Schedule") and kind(fl[1], "Schedule").capitalize() == "Day":
                continue
            try:
                t = spawn_tile(fl[1], int(float(fl[2])), int(float(fl[3])))
            except ValueError:
                continue
            for key, b in list(houses.items()):
                if t in b["roofed"]:
                    busy |= set(b["floor"])
                    del houses[key]
        moving = lambda opts: bool(AR.parse(get_opt(opts, "Home"))) and \
            bool(busy & AR.tiles_of(AR.parse(get_opt(opts, "Home"))))
        taken = set()                                # (beds given already, on this map)
        for ln in lines[H:]:
            opts = opts_of(ln.split("\t"))
            bed = get_opt(opts, "Bed")
            if bed and not moving(opts):             # (one being moved out of someone else's house: its bed's free)
                taken.add(tuple(int(v) for v in bed.split(",")))
        roofed = {(x, y) for y, row in enumerate(grid, 1) for x, (_, over) in enumerate(row, 1) if over.get("Roof")}
        out = list(lines)
        for i in range(H, len(lines)):
            fl = lines[i].split("\t")
            if fl[0] != "NPC" or len(fl) < 4:
                continue
            npc, opts = fl[1], opts_of(fl)
            try:
                tx, ty = spawn_tile(npc, int(float(fl[2])), int(float(fl[3])))
            except ValueError:
                continue
            was = opts
            if moving(opts) and not get_opt(opts, "Schedule") and (person(npc) or npc == "Dog"):
                opts = set_opt(set_opt(opts, "Home", ""), "Bed", "")     # (an earlier run's, in someone else's house)
                news["moved"] += 1
            if get_opt(opts, "Roost"):                                   # (a coop's roost: its Home now)
                opts = set_opt(set_opt(opts, "Home", get_opt(opts, "Roost")), "Roost", "")
                news["roost"] += 1
            if npc in PASSIVE.get(name, ()) and get_opt(opts, "Attitude") != "Passive":
                opts = set_opt(opts, "Attitude", "Passive")
                news["passive"] += 1
            hours = "" if get_opt(opts, "Schedule") else kind(npc, "Schedule").capitalize()
            if houses and hours == "Day" and not get_opt(opts, "Home") and not get_opt(opts, "Bed") and \
                    not get_opt(opts, "Patrol") and (person(npc) or npc == "Dog"):
                d = lambda b: abs(b["mid"][0] - tx) + abs(b["mid"][1] - ty)
                free = [b for b in houses.values() if npc != "Dog" and any(t not in taken for t in b["beds"])]
                roomy = [b for b in houses.values() if b["people"] < PER_HOUSE]
                b = min(free, key=d) if free else (min(roomy, key=d) if roomy else None)
                if b is not None and d(b) <= 30:
                    opts = set_opt(opts, "Home", AR.rects_text(set(b["floor"])))
                    b["people"] += 1
                    news["dog" if npc == "Dog" else "home"] += 1
                    beds = [t for t in b["beds"] if t not in taken]
                    if beds and npc != "Dog":
                        bed = min(beds, key=lambda t: abs(t[0] - tx) + abs(t[1] - ty))
                        taken.add(bed)
                        opts = set_opt(opts, "Bed", "%d,%d" % bed)
                        news["bed"] += 1
            if npc in ANIMALS and roofed and get_opt(opts, "Stand") != "1" and not get_opt(opts, "Patrol"):
                keep = set(AR.tiles_of(AR.parse(get_opt(opts, "Home")) or []))
                if (tx, ty) in roofed:
                    keep |= roofed_part(grid, (tx, ty))
                out_of = lambda tiles: {t for t in tiles if t not in roofed or t in keep}
                zone = AR.parse(get_opt(opts, "Zone"))
                if zone is None:
                    r = int(float(kind(npc, "Roam.Radius", "3") or 3))
                    zone = [(max(1, tx - r), max(1, ty - r), min(W, tx + r), min(H, ty + r))]
                tiles = AR.tiles_of(zone)
                left = out_of(tiles)
                if left != tiles and left:
                    opts = set_opt(opts, "Zone", AR.rects_text(left))
                    news["zone"] += 1
                chase = AR.parse(get_opt(opts, "Chase"))
                if chase is None:
                    c = int(float(kind(npc, "Chase.Radius", "4") or 4))
                    zs = AR.parse(get_opt(opts, "Zone")) or zone
                    chase = [(max(1, min(q[0] for q in zs) - c), max(1, min(q[1] for q in zs) - c),
                              min(W, max(q[2] for q in zs) + c), min(H, max(q[3] for q in zs) + c))]
                tiles = AR.tiles_of(chase)
                left = out_of(tiles)
                if left != tiles and left:
                    opts = set_opt(opts, "Chase", AR.rects_text(left))
                    news["chase"] += 1
            if opts != was:
                while len(fl) < 5:
                    fl.append("")
                fl[4] = opts
                out[i] = "\t".join(fl)
        if out != lines:
            write_text_lines(os.path.join(MAPS, f), out)
    # (Entities.ini: the Indoors rule's lines go)
    raw = read_text_lines(ENTITIES)
    kept = [ln for ln in raw if not ln.strip().lower().startswith("indoors=")]
    if kept != raw:
        write_text_lines(ENTITIES, kept)
        ini.forget(ENTITIES)
        print("Entities.ini: %d Indoors= lines gone" % (len(raw) - len(kept)))
    print("%(moved)d moved out of a building that's someone else's; homes for %(home)d townsfolk (%(bed)d with a bed), %(dog)d dogs; %(roost)d roosts now homes; %(passive)d "
          "made passive; %(zone)d animals' zones and %(chase)d chase areas kept out of houses" % news)


if __name__ == "__main__":
    main()
