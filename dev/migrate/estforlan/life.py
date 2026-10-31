"""What lives in the wild between the settlements: each land's creatures (the gentle ones everywhere, the dangerous
ones well away from the towns and the roads), fish in the sea and the rivers, seals, ducks, otters and frogs by the
water; and each map's background sound."""
from collections import Counter

from atlas import XT, YT, TW, h01
import land as LAND
import layout as L

# land: [(creature, how many to a map (at most), its options)]
CREATURES = {
    "meadow": [("Rabbit", 3, ""), ("Butterfly", 2, "Attitude=Good"), ("Blue_Butterfly", 1, "Attitude=Good")],
    "wood": [("Rabbit", 2, ""), ("Wolf", 2, ""), ("Butterfly", 1, "Attitude=Good")],
    "moor": [("Rabbit", 2, ""), ("Wolf", 2, "")],
    "hills": [("Rabbit", 1, ""), ("Bandit", 1, ""), ("Wolf", 1, "")],
    "marsh": [("Frog", 2, ""), ("Duck", 2, "")],
    "desert": [("Scorpion", 3, "")],
    "snow": [("Snow_Wolf", 2, "")],
    "elder": [("Bear", 1, ""), ("Rabbit", 2, ""), ("Butterfly", 1, "Attitude=Good")],
    "ash": [("Ember_Hound", 2, "")],
    "downs": [("Rabbit", 3, ""), ("Butterfly", 1, "Attitude=Good"), ("Skeleton", 1, "")],
    "field": [],
    "galaith": [],
}
GENTLE = {"Rabbit", "Butterfly", "Blue_Butterfly", "Frog", "Duck"}
PREY = {"Rabbit", "Frog", "Duck", "Seal", "Otter", "Chicken", "Cow", "Sheep"}     # (Flees=1: Passive, never Bad)
OPEN = ("Grass001", "Sand001", "Snow001", "Marsh001", "Ash001", "Cinder001", "Dirt001")
SOUND = {"meadow": "Wind", "moor": "Wind", "hills": "Wind", "downs": "Wind", "wood": "Forest", "elder": "Forest",
         "marsh": "Marsh", "desert": "Desert", "snow": "Snow", "ash": "Wind", "field": "Wind", "galaith": "Wind",
         "mount": "Wind", "cinder_mount": "Wind", "snow_mount": "Snow", "pass": "Wind"}


def lands_of(mx, my):
    c = Counter()
    for y in range(my * YT, my * YT + YT):
        for x in range(mx * XT, mx * XT + XT):
            b = LAND.BIOME.get((x, y))
            if b and not LAND.GROUND.get((x, y), "").startswith("Water"):
                c[b] += 1
    return c


def near_town(c, plans, r):
    return any(p.box_has(c, r) for p in plans.values())


def free(atlas, c):
    return LAND.GROUND.get(c) in OPEN and not LAND.DECOR.get(c) and c not in atlas.taken and c not in atlas.roads


def populate(atlas, plans, parts_maps):
    """The creatures of each map's land (not in the towns, nor on the maps the quest places stand on, where they
    have their own)."""
    made = 0
    for name, m in sorted(atlas.maps.items()):
        mx, my = (int(v) for v in name.split(",")[:2])
        if name in parts_maps or L.macro(mx, my) in ("G", "F", "P"):
            continue
        lands = lands_of(mx, my)
        if sum(lands.values()) < 120:
            continue
        land = lands.most_common(1)[0][0]
        for kind, most, opts in CREATURES.get(land, []):
            n = int(h01("n", name, kind) * (most + 1))
            for i in range(n):
                for tries in range(30):
                    x = mx * XT + 2 + int(h01("x", name, kind, i, tries) * (XT - 4))
                    y = my * YT + 2 + int(h01("y", name, kind, i, tries) * (YT - 4))
                    if not free(atlas, (x, y)):
                        continue
                    if kind not in GENTLE and (near_town((x, y), plans, 16) or any(
                            (x + dx, y + dy) in atlas.roads for dx in range(-4, 5) for dy in range(-4, 5))):
                        continue
                    if kind in GENTLE and near_town((x, y), plans, 0):
                        continue
                    lx, ly = x - mx * XT + 1, y - my * YT + 1
                    zone = "Zone=%d,%d,%d,%d" % (max(2, lx - 5), max(2, ly - 4), min(XT - 1, lx + 5), min(YT - 1, ly + 4))
                    o = (opts or ("Attitude=Passive" if kind in PREY else "Attitude=Bad")) + " " + zone
                    m.ents.append("NPC\t%s\t%d\t%d\t%s" % (kind, (lx - 1) * TW, (ly - 1) * TW - 8, o))
                    atlas.taken.add((x, y))
                    made += 1
                    break
    return made


def waters(atlas, plans):
    """Fishing spots: sea ones (and swordfish further out) off the coasts, trout and salmon in the rivers; seals on
    the rocks, ducks, otters and frogs where the water's still."""
    made = 0
    for name, m in sorted(atlas.maps.items()):
        mx, my = (int(v) for v in name.split(",")[:2])
        sea, river, shore = [], [], []
        for y in range(my * YT + 1, my * YT + YT - 1):
            for x in range(mx * XT + 1, mx * XT + XT - 1):
                c = (x, y)
                g = LAND.GROUND.get(c, "")
                if g != "Water001" or c in atlas.taken:
                    continue
                near = [LAND.GROUND.get((x + dx, y + dy), "") for dx in (-2, 0, 2) for dy in (-2, 0, 2)]
                landish = sum(1 for t in near if not t.startswith("Water"))
                if c in LAND.RIVER:
                    river.append(c)
                elif landish:
                    shore.append(c)
                elif all(LAND.GROUND.get((x + dx, y + dy), "Water001") == "Water001"
                         for dx in (-5, 0, 5) for dy in (-5, 0, 5)):
                    sea.append(c)
        picks = []
        if shore and h01("fs", name) < 0.5:
            picks.append(("Fish_Spot", shore[int(h01("fsc", name) * len(shore))]))
        if sea and h01("sw", name) < 0.25 and lands_of(mx, my):
            picks.append(("Swordfish_Spot", sea[int(h01("swc", name) * len(sea))]))
        if river and h01("rv", name) < 0.7:
            picks.append(("Trout_Spot" if h01("rk", name) < 0.6 else "Salmon_Spot",
                          river[int(h01("rvc", name) * len(river))]))
        for kind, (x, y) in picks:
            lx, ly = x - mx * XT + 1, y - my * YT + 1
            m.ents.append("StaticObject\t%s\t%d\t%d" % (kind, (lx - 1) * TW, (ly - 1) * TW))
            atlas.taken.add((x, y))
            made += 1
        if shore and h01("seal", name) < 0.15 and not any(p.box_has(shore[0], 10) for p in plans.values()):
            x, y = shore[int(h01("sealc", name) * len(shore))]
            lx, ly = min(XT - 2, x - mx * XT + 1), y - my * YT + 1
            for k in range(2):
                m.ents.append("NPC\tSeal\t%d\t%d\tAttitude=Passive Zone=%d,%d,%d,%d" % (
                    (lx - 1) * TW + k * 32, (ly - 1) * TW, max(2, lx - 5), max(2, ly - 4), min(XT - 1, lx + 5),
                    min(YT - 1, ly + 4)))
            made += 2
        if river and h01("otter", name) < 0.3:
            x, y = river[int(h01("otc", name) * len(river))]
            lx, ly = x - mx * XT + 1, y - my * YT + 1
            m.ents.append("NPC\tOtter\t%d\t%d\tAttitude=Passive Zone=%d,%d,%d,%d" % (
                (lx - 1) * TW, (ly - 1) * TW, max(2, lx - 4), max(2, ly - 4), min(XT - 1, lx + 4), min(YT - 1, ly + 4)))
            made += 1
    return made


def reach(atlas, start):
    """Every world tile you can walk to from start (locks open, roofs lifted)."""
    from collections import deque
    import towns as OLD
    ok = {}

    def walk(c):
        if c not in ok:
            m, x, y = atlas.at(*c)
            if m is None:
                ok[c] = False
            else:
                cell = m.rows[y - 1][x - 1].split("+")
                names = [cell[0]] + [p[6:-1] for p in cell[1:] if p.startswith("Decor(")]
                ok[c] = all(OLD.walk_middle(n) for n in names)
        return ok[c]
    seen = {start}
    q = deque([start])
    while q:
        x, y = q.popleft()
        for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if n not in seen and walk(n):
                seen.add(n)
                q.append(n)
    return seen


WILD = {k for v in CREATURES.values() for k, _, _ in v} | {"Seal", "Otter"}
SPOTS = ("Fish_Spot", "Swordfish_Spot", "Trout_Spot", "Salmon_Spot", "Moored_Boat")


def prune(atlas, start, seen=None):
    """Fishing spots, boats and wild creatures nobody can get to (out at sea, on an islet) go."""
    seen = seen or reach(atlas, start)
    gone = 0
    for name, m in atlas.maps.items():
        mx, my = (int(v) for v in name.split(",")[:2])
        keep = []
        for ln in m.ents:
            f = ln.split("\t")
            if len(f) > 3 and (f[1] in SPOTS or f[0] == "NPC" and f[1] in WILD and "Id=" not in ln):
                x = mx * XT + int(float(f[2])) // TW
                y = my * YT + (int(float(f[3])) + 24) // TW
                inside = 0 < x - mx * XT < XT - 1 and 0 < y - my * YT < YT - 1     # (not on its edge)
                near = [(x, y), (x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
                if not inside or not any(c in seen for c in near):
                    gone += 1
                    continue
            keep.append(ln)
        m.ents = keep
    return gone


def cut_off(atlas, seen):
    """The lifted places (their Id tiles) you can't walk to from the mainland (Dragon Island's are by boat)."""
    out = []
    for part in L.parts()["parts"].values():
        mx, my = (int(v) for v in part["new"].split(",")[:2])
        if L.macro(mx, my) == "D":
            continue
        for ln in part["lines"]:
            f = ln.split("	")
            if f[0] == "Id":
                c = (mx * XT + int(f[2]) - 1, my * YT + int(f[3]) - 1)
                if not any((c[0] + dx, c[1] + dy) in seen for dx in (-1, 0, 1) for dy in (-1, 0, 1)):
                    out.append(f[1])
    return out


def fix_zones(atlas):
    """Someone whose Zone= (where they wander) has nowhere to walk now the land round them changed: a smaller one
    round where they stand, or, if even that's shut in, they stand."""
    import re
    import towns as OLD
    fixed = 0
    for name, m in atlas.maps.items():
        def walk(x, y):
            if not (1 <= x <= XT and 1 <= y <= YT):
                return False
            cell = m.rows[y - 1][x - 1].split("+")
            names = [cell[0]] + [p[6:-1] for p in cell[1:] if p.startswith("Decor(")]
            return all(OLD.walk_middle(n) for n in names)
        out = []
        for ln in m.ents:
            f = ln.split("\t")
            z = re.search(r"Zone=(\d+),(\d+),(\d+),(\d+)", ln) if f[0] == "NPC" else None
            if z:
                x1, y1, x2, y2 = (int(v) for v in z.groups())
                if sum(1 for y in range(y1, y2 + 1) for x in range(x1, x2 + 1) if walk(x, y)) < 3:
                    sx, sy = int(float(f[2])) // TW + 1, (int(float(f[3])) + 24) // TW + 1
                    box = (max(1, sx - 2), max(1, sy - 2), min(XT, sx + 2), min(YT, sy + 2))
                    room = sum(1 for y in range(box[1], box[3] + 1) for x in range(box[0], box[2] + 1) if walk(x, y))
                    new = "Zone=%d,%d,%d,%d" % box if room >= 3 else "Stand=1"
                    if new == "Stand=1" and "Stand=1" in ln:
                        new = ""
                    opts = " ".join(o for o in " ".join(f[4:]).split() if not o.startswith("Zone=")) + \
                        (" " + new if new else "")
                    ln = "\t".join(f[:4] + ([opts.strip()] if opts.strip() else []))
                    fixed += 1
            out.append(ln)
        m.ents = out
    return fixed


def sounds(atlas):
    """{map: its background sound}: its land's, the waves where it's mostly sea."""
    out = {}
    for name in atlas.maps:
        mx, my = (int(v) for v in name.split(",")[:2])
        lands = lands_of(mx, my)
        total = sum(lands.values())
        if total < XT * YT * 0.35:
            out[name] = "Waves"
        else:
            out[name] = SOUND.get(lands.most_common(1)[0][0], "Wind")
    return out
