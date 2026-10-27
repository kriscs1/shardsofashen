"""The new mainland put together, in order: the land; the lifted quest places set down; Galaith's walls, field and
pass; Wardhaven's bridge and gate; the settlements, biggest first (each with its port or dock if it's on a coast);
the roads between them; the old towns' people in their new homes; the wild creatures and the fish."""
import time

from atlas import Atlas, XT, YT, map_name
import layout as L
import land as LAND
import places as P
import galaith as G
import settlements as S
import ways as W
import life

ORDER = ["Galaith", "Southport", "Keep", "Court", "Ravensgate", "Fenwick", "Ashford", "Highwatch", "Frosthold",
         "Wardhaven", "Oakhollow", "Thornwick", "Emberwatch", "Moorcross", "Wildwood", "Dunerest", "Saltmarsh"]
CITY = ("huge", "large", "medium", "small")


def map_names():
    """The new mainland's maps: every map with land on it, and the sea maps next to one (its coast's view), not the
    Isle's."""
    land = set()
    for my in range(L.H):
        for mx in range(L.XMIN, L.W):
            if any(LAND.land_here(mx * XT + x, my * YT + y) for x in range(1, XT, 3) for y in range(1, YT, 3)):
                land.add((mx, my))
    for name in L.parts()["parts"].values():
        land.add(tuple(int(v) for v in name["new"].split(",")[:2]))
    out = set()
    for mx, my in land:
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if 0 <= mx + dx < L.W and 0 <= my + dy < L.H or (mx + dx, my + dy) in land:
                    out.add(map_name(mx + dx, my + dy))     # (west of the range: only Galaith's own, no sea)
    return sorted(n for n in out if n not in L.ISLE)


def cart_targets(atlas, key):
    def targets(plan):
        out = [("the market", plan.centre)]
        if key == "Galaith":
            out += [("the palace", (-9 * XT + 12, L.ty(12) * YT + 14)), ("the east gate", (G.EAST - 4, G.GATE))]
        posh = [lt for lt in plan.lots if lt.kind == "shop" and lt.name in ("clothes", "shoes")]
        if posh:
            out.append(("the posh end", (posh[0].door, posh[0].y2 + 1)))
        hall = [lt for lt in plan.lots if lt.kind in ("parliament", "hall")]
        if key == "Southport":
            out.append(("the port", (4 * XT + 14, 4 * YT + 8)))
            if hall:
                out.append(("the City Hall", (hall[0].door, hall[0].y2 + 1)))
        return out
    return targets


def assemble(log=print):
    t0 = time.time()
    atlas = Atlas(map_names())
    log("%d maps" % len(atlas.maps))
    LAND.generate(atlas)
    log("land: %.0fs" % (time.time() - t0))
    reserved = P.reserved()
    P.clearings(atlas)
    P.stamp(atlas)
    pier = P.rook_pier(atlas)
    if pier:
        L.POIS["Rooks_Pier"] = ((pier[0] // XT, pier[1] // YT), (pier[0] % XT + 1, pier[1] % YT + 1), "road")
    clear = G.walls(atlas)
    G.field(atlas)
    G.pass_(atlas)
    keep_w, gate_map, foot, bridge = G.wardhaven(atlas)
    L.POIS["Wardhaven_Bridge"] = ((foot[0] // XT, foot[1] // YT), (foot[0] % XT + 1, foot[1] % YT + 1), "road")
    plans = {}
    for key in ORDER:
        spec = L.SETTLEMENTS[key]
        hooks = []
        if spec.get("coast"):
            big = spec["size"] in CITY
            hooks.append(lambda p, big=big: W.harbour(atlas, p, big) and p.connect(p.harbour[0]))
        keep = G.inside if key == "Galaith" else keep_w if key == "Wardhaven" else None
        plan = S.settle(atlas, key, reserved | (clear if key == "Galaith" else set()), keep=keep,
                        carts=cart_targets(atlas, key), staff=P.STAFF.get(key, ()), hooks=hooks)
        plans[key] = plan
        log("%-11s %3d buildings, %3d houses, %2d streets%s" % (
            key, len(plan.lots), sum(1 for lt in plan.lots if lt.kind == "house"), plan.streets,
            ("  (no room for: %s)" % ", ".join(plan.missing)) if plan.missing else ""))
    g = plans["Galaith"]
    for c in ((G.WEST + 1, G.GATE), (G.EAST - 1, G.GATE)):
        g.cells.add(c)
        g.lay(c)
        g.connect(c)
    w = plans["Wardhaven"]
    gate_in = (G.BRIDGE_X, min(y for (x, y) in atlas.taken if x == G.BRIDGE_X and
                               atlas.tile(x, y).startswith("City_Gate")) - 1)
    w.cells.add(gate_in)
    w.lay(gate_in)
    w.connect(gate_in)
    for plan in plans.values():                      # (the lifted places in a town: joined to its streets)
        for part in L.parts()["parts"].values():
            if not plan.box_has(P.world(part, 13, 11), S.SPREAD):
                continue
            ends = [c for c in P.rect_cells(part) if c in atlas.roads and any(
                n in plan.cells and n not in atlas.taken and n not in plan.street
                for n in ((c[0] + 1, c[1]), (c[0] - 1, c[1]), (c[0], c[1] + 1), (c[0], c[1] - 1)))]
            for c in ends[:3]:
                for n in ((c[0] + 1, c[1]), (c[0] - 1, c[1]), (c[0], c[1] + 1), (c[0], c[1] - 1)):
                    if n in plan.cells and n not in atlas.taken and n not in plan.street:
                        plan.lay(n)
                        plan.connect(n)
                        break
    LAND.repeak(atlas, L.XMIN * XT, L.ty(10) * YT, G.PASS_X * XT + XT - 1, L.ty(17) * YT)   # (Galaith's peaks, whole)
    ways = W.Ways(atlas, plans)
    missed = ways.build()
    log("roads: %d tiles%s (%.0fs)" % (len(ways.road), ("; no way for: " + ", ".join(missed)) if missed else "",
                                        time.time() - t0))
    scripts = {}
    posts = ways.signposts(scripts)
    homes, rehoused = P.rehouse(atlas, plans)
    log("signposts: %d; people moved: %d" % (posts, sum(len(v) for v in rehoused.values())))
    parts_maps = {p["new"] for p in L.parts()["parts"].values()}
    log("creatures: %d, by the water: %d" % (life.populate(atlas, plans, parts_maps), life.waters(atlas, plans)))
    log("out of reach, gone: %d" % life.prune(atlas, plans["Southport"].centre))
    return atlas, plans, homes, rehoused, gate_map, scripts, bridge
