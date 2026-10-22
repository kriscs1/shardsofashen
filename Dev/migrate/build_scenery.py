"""Scenery, landmarks, wildlife and secrets, to make the maps varied and alive. Part of build_content.py (it calls
extend() here), so `python -I "Dev\\migrate\\build_world.py"` builds it.

  * Scatter: on every surface map, some grass becomes flowers or tall grass, and a little becomes rocks, bushes or
    fallen logs (only where all 8 neighbours are open grass, so no way through is ever blocked). The choice for each
    cell is a hash of the map and cell, so it's the same every build.
  * Landmarks (LANDMARKS): a stone circle, a ruined watchtower, a graveyard, a hermit's camp, a goblin camp, wells, a
    lily pond, a farmyard with a scarecrow, crates and barrels at Southport, a fairy ring in the Whispering Woods.
  * Secrets: a chest at most landmarks, each opened once (CHESTS, the Open Chest script), and villagers who drop hints.
  * Wildlife (WILDLIFE): rabbits and butterflies in the meadows, ducks by the water. They roam (Entities.ini Roam.Radius).
  * The Hermit's Fire: a small quest from the hermit in the Isle's western woods.
On the 13 original Isle maps all of this is added as patches (see build_content.py), on the Southlands maps directly.
"""
import zlib

C = None        # build_content
W = None        # build_world

# ------------------------------------------------------------------ the tiles' data (Tiles.ini)
OPEN = "1" * 49
SMALL = "1111111" "1111111" "1100011" "1100011" "1100011" "1111111" "1111111"
BIG = "1111111" "1000001" "1000001" "1000001" "1000001" "1000001" "1111111"
SOLID = "0" * 49
FENCE_H = "1111111" * 3 + "0000000" + "1111111" * 3
FENCE_V = "1110111" * 7
LOG = "1111111" "1111111" "0000000" "0000000" "1111111" "1111111" "1111111"
SCENERY_TILES = {
    # name: (walkable, show name, use words, examine, line of sight)
    "Flowers001": (OPEN, "0", "", "Daisies and buttercups.", "1"),
    "Flowers002": (OPEN, "0", "", "Red poppies and purple heather.", "1"),
    "Flowers003": (OPEN, "0", "", "Bluebells, nodding in the breeze.", "1"),
    "Tall_Grass001": (OPEN, "0", "", "Long grass, swaying in the wind.", "1"),
    "Mushroom_Ring001": (OPEN, "1", "", "A ring of red toadstools. Fairies dance here, they say.", "1"),
    "Rock001": (BIG, "1", "", "A mossy boulder.", "1"),
    "Rock002": (BIG, "1", "", "A big grey boulder, furred with moss on top.", "1"),
    "Rock003": (SMALL, "1", "", "Three stones huddled together.", "1"),
    "Pebbles001": (OPEN, "0", "", "Pebbles in the grass.", "1"),
    "Pebbles002": (OPEN, "0", "", "Pebbles in the grass.", "1"),
    "Pebbles003": (OPEN, "0", "", "Stones and pebbles, half sunk in the turf.", "1"),
    "Bush001": (BIG, "1", "", "A thick, prickly bush.", "1"),
    "Fallen_Log001": (LOG, "1", "Chop", "A fallen tree trunk. It would make good firewood.", "1"),
    "Standing_Stone001": (SMALL, "1", "", "A standing stone, carved with spirals. It hums faintly when you touch it.", "1"),
    "Ruined_Wall001": (SOLID, "1", "", "The broken wall of an old watchtower.", "0"),
    "Ruined_Wall002": (SOLID, "1", "", "What's left of a wall: a few courses of stone.", "1"),
    "Grave001": (SMALL, "1", "", "'Here lies Old Tom Barrow. He went to sea and the sea kept him.'", "1"),
    "Grave002": (SMALL, "1", "", "'Mary Croft, beloved mother. She baked the best pies on the Isle.'", "1"),
    "Grave003": (SMALL, "1", "", "The name has worn away. The earth in front of it looks... disturbed.", "1"),
    "Fence001": (FENCE_H, "1", "", "A wooden fence.", "1"),
    "Fence002": (FENCE_V, "1", "", "A wooden fence.", "1"),
    "Well001": (BIG, "1", "", "A stone well. Use a bucket on it to draw water.", "1"),
    "Pond001": (SOLID, "1", "", "A lily pond. Fish rise to the surface now and then.", "1"),
    "Haystack001": (BIG, "1", "", "A big haystack. Something rustles inside it.", "0"),
    "Scarecrow001": (SMALL, "1", "", "A scarecrow in a ragged coat. The crows don't seem very scared.", "1"),
    "Tent001": (BIG, "1", "", "A patched canvas tent.", "0"),
    "Tent002": (BIG, "1", "", "A grubby hide tent. It smells of goblin.", "0"),
    "Crate001": (SMALL, "1", "", "A wooden crate, stencilled 'SOUTHPORT'.", "1"),
    "Barrel001": (SMALL, "1", "", "A barrel of salted fish. Phew.", "1"),
    "Sea_Rock001": (SOLID, "1", "", "A rock in the sea, white with gull droppings.", "1"),
    "Sea_Rock002": (SOLID, "1", "", "Two rocks poking out of the waves.", "1"),
}
WALK_DECOR = ["Flowers001", "Flowers002", "Flowers003", "Tall_Grass001", "Tall_Grass001", "Pebbles001", "Pebbles002",
              "Pebbles003"]
BLOCK_DECOR = ["Rock001", "Rock002", "Rock003", "Rock002", "Bush001", "Bush001", "Fallen_Log001"]
GRASS = {"Grass001"}
SEA = {"Water001"}
SEA_ROCKS = ["Sea_Rock001", "Sea_Rock002"]
SEA_ROCK_RATE = 14   # per 1000 open-sea cells (every cell round it is sea too), at least 3 tiles apart
SCATTER = {   # map: (walkable decor per 1000 grass cells, blocking decor per 1000, copses of trees per 1000)
    "default": (150, 30, 14),
    "1,3,0": (60, 8, 0), "2,3,0": (60, 8, 0), "3,3,0": (80, 10, 4),     # towns and the farm: tidier
    "2,0,0": (110, 14, 4),                                                # the Isle's farm
}
COPSES = [[(0, 0), (1, 0), (0, 1)], [(0, 0), (1, 0), (0, 1), (1, 1)], [(0, 0), (1, 0), (2, 0), (1, 1)],
          [(0, 0), (1, 1)], [(0, 0), (0, 1), (1, 1)]]
COPSE_TREES = ["Tree001", "Tree002", "Tree001", "Oak_Tree001"]

# ------------------------------------------------------------------ landmarks: (x, y, tile) and entities, 1-based tiles
LANDMARKS = {
    # the Isle (original maps: patched)
    "0,0,0": dict(   # a stone circle on the north-west headland, a chest in the middle
        tiles=[(17, 9, "Standing_Stone001"), (20, 10, "Standing_Stone001"), (20, 14, "Standing_Stone001"),
               (17, 15, "Standing_Stone001"), (14, 14, "Standing_Stone001"), (14, 10, "Standing_Stone001"),
               (16, 13, "Mushroom_Ring001"), (18, 11, "Mushroom_Ring001")],
        entities=[("obj", "Chest", 17, 12)]),
    "3,0,0": dict(   # a ruined watchtower by the sea in the north-east, wolves about
        tiles=[(5, 13, "Ruined_Wall001"), (6, 13, "Ruined_Wall001"), (7, 13, "Ruined_Wall001"), (8, 13, "Ruined_Wall001"),
               (8, 14, "Ruined_Wall002"), (8, 16, "Ruined_Wall002"), (5, 16, "Ruined_Wall002"), (6, 16, "Ruined_Wall001")],
        entities=[("obj", "Chest", 7, 14)]),
    "3,1,0": dict(   # a fenced graveyard (the gate is at 7,2); something walks among the graves
        tiles=[(x, 2, "Fence001") for x in range(2, 13) if x != 7] +
              [(x, y, "Grave00%d" % (1 + (x + y) % 3)) for y in (3, 5) for x in (3, 5, 7, 9, 11)],
        entities=[("obj", "Chest", 12, 4), ("npc", "BadNPC", "Skeleton", 8, 4)]),
    "0,1,0": dict(   # the hermit's camp in the western woods
        tiles=[(15, 3, "Tent001"), (13, 5, "Fallen_Log001")],
        entities=[("obj", "Fire", 16, 5), ("npc", "GoodNPC", "Hermit", 17, 4)]),
    "2,2,0": dict(   # a goblin camp on the south shore
        tiles=[(10, 8, "Tent002"), (16, 8, "Tent002")],
        entities=[("obj", "Fire", 13, 9), ("obj", "Chest", 13, 7), ("npc", "BadNPC", "Goblin", 15, 11)]),
    "1,1,0": dict(tiles=[(8, 6, "Well001")], entities=[]),
    # the Southlands (generated maps)
    "2,3,0": dict(tiles=[(11, 9, "Well001")], entities=[]),           # Ashford's well
    "1,3,0": dict(tiles=[(20, 10, "Barrel001"), (21, 10, "Barrel001"), (22, 10, "Crate001"), (21, 11, "Crate001")],
                  entities=[]),                                         # Southport's quay
    "3,3,0": dict(tiles=[(4, 20, "Scarecrow001"), (2, 17, "Haystack001"), (3, 21, "Haystack001")], entities=[]),
    "1,4,0": dict(tiles=[(6, 14, "Mushroom_Ring001")], entities=[("obj", "Chest", 10, 16)]),   # the yew grove
    "3,4,0": dict(tiles=[(11, 17, "Pond001"), (12, 17, "Pond001"), (11, 18, "Pond001"), (12, 18, "Pond001")],
                  entities=[]),
}

# ------------------------------------------------------------------ wildlife: map -> [(kind, name, how many)]
WILDLIFE = {
    "0,0,0": [("BadNPC", "Rabbit", 2), ("GoodNPC", "Butterfly", 1)],
    "1,0,0": [("BadNPC", "Duck", 3), ("GoodNPC", "Butterfly", 2)],
    "2,0,0": [("GoodNPC", "Butterfly", 2)],
    "3,0,0": [("BadNPC", "Rabbit", 2)],
    "0,1,0": [("BadNPC", "Rabbit", 2), ("GoodNPC", "Butterfly", 1)],
    "1,1,0": [("GoodNPC", "Butterfly", 2), ("BadNPC", "Rabbit", 1), ("BadNPC", "Duck", 2)],
    "2,1,0": [("BadNPC", "Rabbit", 2), ("GoodNPC", "Butterfly", 2)],
    "3,1,0": [("BadNPC", "Rabbit", 1)],
    "1,2,0": [("BadNPC", "Duck", 2)],
    "2,2,0": [("BadNPC", "Rabbit", 1)],
    "3,2,0": [("BadNPC", "Rabbit", 2), ("GoodNPC", "Butterfly", 1)],
    "1,3,0": [("BadNPC", "Duck", 2)],
    "2,3,0": [("GoodNPC", "Butterfly", 2)],
    "3,3,0": [("GoodNPC", "Butterfly", 2), ("BadNPC", "Duck", 2)],
    "1,4,0": [("BadNPC", "Rabbit", 3), ("GoodNPC", "Butterfly", 1)],
    "2,4,0": [("BadNPC", "Rabbit", 2)],
    "3,4,0": [("BadNPC", "Duck", 3), ("BadNPC", "Rabbit", 2), ("GoodNPC", "Butterfly", 2)],
}

CHESTS = {   # map: (attribute, [(item, quantity)], what you find)
    "0,0,0": ("StoneCircleChest", [("Magic_Potion", 1), ("Lightning_Scroll", 2), ("Gold_Coin(s)", 40)],
              "Hidden among the standing stones: a magic potion, two lightning scrolls and 40 gold!"),
    "3,0,0": ("TowerChest", [("Oak_Shield", 1), ("Defence_Potion", 2), ("Gold_Coin(s)", 60)],
              "The old guards' chest holds an oak shield, two defence potions and 60 gold!"),
    "3,1,0": ("GraveChest", [("Teleport_Scroll", 2), ("Silver_Ring", 1), ("Gold_Coin(s)", 50)],
              "Grave goods: two teleport scrolls, a silver ring and 50 gold. Sorry, Old Tom."),
    "2,2,0": ("GoblinChest", [("Fire_Bolt_Scroll", 3), ("Bronze_Sword", 1), ("Gold_Coin(s)", 30)],
              "The goblins' loot: three fire bolt scrolls, a bronze sword and 30 gold!"),
    "1,4,0": ("YewGroveChest", [("Willow_Staff", 1), ("Mega_Potion", 1), ("Gold_Coin(s)", 80)],
              "Under the old yews, a mossy chest: a willow staff, a mega potion and 80 gold!"),
}

ENTITIES = {
    "Rabbit": dict(kind="bad", examine="A brown rabbit, twitching its nose.", hp=3, aspeed=1, strength=0, defence=1,
                   aggro=0, move=2.5, aggressive=0, respawn=40, drops="Raw_Meat,1-1,100", solid="0", layer="Under"),
    "Duck": dict(kind="bad", examine="A mallard duck. Quack.", hp=3, aspeed=1, strength=0, defence=1, aggro=0,
                 move=1.2, aggressive=0, respawn=40, drops="Raw_Chicken,1-1,100", solid="0", layer="Under"),
    "Butterfly": dict(kind="good", examine="A butterfly with bright orange wings.", use="Examine", speed="1.5",
                      solid="0", layer="Over"),
    "Hermit": dict(kind="good", examine="A wild-haired hermit. He smells of woodsmoke and moss.", use="Talk to"),
}
MOVEMENT = {"Rabbit": (3, 0, "0.8", "1-3"), "Duck": (2, 0, "0.4", "2-6"), "Butterfly": (3, 0, "0.6", "0-1"),
            "Hermit": (1, 0, "0.4", "4-10")}


def h(*parts):
    return zlib.crc32(":".join(str(v) for v in parts).encode()) % 1000


# ------------------------------------------------------------------ planning (the same for both kinds of map)
def plan(name, grid, busy, fixed):
    """grid[y][x] = base tile name (0-based); busy = {(x, y)} 1-based cells near entities/locks/landmarks where
    nothing blocking may go; fixed = {(x, y): tile} landmarks. Returns {(x, y): tile} for scatter + landmarks."""
    walk_rate, block_rate, copse_rate = SCATTER.get(name, SCATTER["default"])
    H, Wd = len(grid), len(grid[0])
    out = dict(fixed)
    ring = set()

    def grass(x, y):
        return 1 <= x <= Wd and 1 <= y <= H and grid[y - 1][x - 1] in GRASS and (x, y) not in fixed

    # copses: a few trees together, only where they and a ring of open grass round them fit
    for y in range(3, H - 1):
        for x in range(3, Wd - 1):
            if h(name, x, y, "copse") >= copse_rate:
                continue
            shape = COPSES[h(name, x, y, "shape") % len(COPSES)]
            cells = [(x + dx, y + dy) for dx, dy in shape]
            around = {(cx + ex, cy + ey) for cx, cy in cells for ex in (-1, 0, 1) for ey in (-1, 0, 1)}
            if all(2 <= ax <= Wd - 1 and 2 <= ay <= H - 1 and grass(ax, ay) and (ax, ay) not in out and
                   (ax, ay) not in ring and (ax, ay) not in busy for ax, ay in around):
                for cx, cy in cells:
                    out[(cx, cy)] = COPSE_TREES[h(name, cx, cy, "tree") % len(COPSE_TREES)]
                ring |= around - set(cells)

    def wants_block(x, y):
        return walk_rate <= h(name, x, y, "decor") < walk_rate + block_rate

    for y in range(1, H + 1):
        for x in range(1, Wd + 1):
            if not grass(x, y) or (x, y) in out:
                continue
            v = h(name, x, y, "decor")
            if v < walk_rate:
                out[(x, y)] = WALK_DECOR[h(name, x, y, "kind") % len(WALK_DECOR)]
            elif wants_block(x, y):
                ok = 1 < x < Wd and 1 < y < H
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        if (dx or dy) and (not grass(x + dx, y + dy) or wants_block(x + dx, y + dy) or
                                           (x + dx, y + dy) in out and out[(x + dx, y + dy)] not in WALK_DECOR):
                            ok = False
                        if (x, y) in ring:
                            ok = False
                        if (x + dx, y + dy) in busy:
                            ok = False
                if ok:
                    out[(x, y)] = BLOCK_DECOR[h(name, x, y, "kind") % len(BLOCK_DECOR)]
    # rocks in the open sea: never next to land, a shore piece or anything placed, and spread out
    rocks = []
    for y in range(2, H):
        for x in range(2, Wd):
            if h(name, x, y, "searock") >= SEA_ROCK_RATE or (x, y) in out or (x, y) in busy:
                continue
            if all(grid[y - 1 + dy][x - 1 + dx] in SEA and (x + dx, y + dy) not in out
                   for dx in (-1, 0, 1) for dy in (-1, 0, 1)) and all(abs(x - rx) + abs(y - ry) >= 3 for rx, ry in rocks):
                rocks.append((x, y))
                out[(x, y)] = SEA_ROCKS[h(name, x, y, "rockkind") % len(SEA_ROCKS)]
    return out


def critter_spots(name, grid, taken, busy, n, near_water=False):
    """n open grass cells for animals (spread out, deterministic)."""
    H, Wd = len(grid), len(grid[0])
    cells = []
    for y in range(2, H):
        for x in range(2, Wd):
            if grid[y - 1][x - 1] not in GRASS or (x, y) in busy:
                continue
            if taken.get((x, y)) and taken[(x, y)] not in WALK_DECOR and taken[(x, y)] != "Mushroom_Ring001":
                continue
            if near_water and not any(grid[yy][xx].startswith("Water") or grid[yy][xx] == "Pond001" or
                                      taken.get((xx + 1, yy + 1)) == "Pond001"
                                      for yy in range(max(0, y - 3), min(H, y + 2))
                                      for xx in range(max(0, x - 3), min(Wd, x + 2))):
                continue
            cells.append((h(name, x, y, "critter"), x, y))
    cells.sort()
    out = []
    for _, x, y in cells:
        if all(abs(x - ox) + abs(y - oy) > 4 for ox, oy in out):
            out.append((x, y))
        if len(out) == n:
            break
    return out


def landmark_entities(name):
    ents = []
    for e in LANDMARKS.get(name, {}).get("entities", []):
        if e[0] == "obj":
            ents.append(W.obj(e[1], e[2], e[3]))
        else:
            ents.append(W.npc(e[1], e[2], e[3], e[4]))
    return ents


def busy_cells(entities, extra=()):
    """Cells next to entities (pixel coords) and locks/triggers/landmarks: nothing blocking goes there."""
    busy = set()
    for e in entities:
        try:
            tx, ty = int(float(e[2]) + 16) // 32 + 1, int(float(e[3]) + 28) // 32 + 1
        except (ValueError, IndexError):
            continue
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                busy.add((tx + dx, ty + dy))
    for x, y in extra:
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                busy.add((x + dx, y + dy))
    return busy


def wildlife_entities(name, grid, taken, busy):
    ents = []
    for kind, creature, n in WILDLIFE.get(name, []):
        for x, y in critter_spots(name + creature, grid, taken, busy, n, near_water=(creature == "Duck")):
            ents.append(W.npc(kind, creature, x, y))
            busy |= {(x, y)}
    return ents


# ------------------------------------------------------------------ the Southlands (generated): rows of legend chars
DECOR_CHARS = {}


def decorate_generated():
    spare = [c for c in "$%&*()[]{}<|?@`;'/0245678bglxSkqv\"" if c not in W.LEGEND]
    spare += [chr(c) for c in range(0x300, 0x380) if chr(c) not in W.LEGEND]     # (when the ASCII ones run out)
    for i, name in enumerate(SCENERY_TILES):
        DECOR_CHARS[name] = spare[i]
        W.LEGEND[spare[i]] = name
    for name, spec in W.MAPS.items():
        if not name.endswith(",0") or name in W.PROTECTED_MAPS or name in getattr(W, "NO_SCENERY", ()):
            continue
        grid = [[W.LEGEND[ch].split("+")[0] for ch in row] for row in spec["rows"]]
        fixed = {(x, y): t for x, y, t in LANDMARKS.get(name, {}).get("tiles", [])}
        for (x, y), t in fixed.items():
            assert grid[y - 1][x - 1] in GRASS, (name, x, y, grid[y - 1][x - 1], t)
        extra = [(int(l[0]), int(l[1])) for l in spec.get("locks", [])] + list(fixed) +             [(int(t[1]), int(t[2])) for t in spec.get("triggers", [])]
        new_ents = landmark_entities(name)
        busy = busy_cells(list(spec["entities"]) + new_ents, extra)
        chosen = plan(name, grid, busy, fixed)
        spec["rows"] = C.set_cells(spec["rows"], [(x, y, decor_char(t)) for (x, y), t in chosen.items()])
        spec["entities"] = list(spec["entities"]) + new_ents + wildlife_entities(name, grid, chosen, busy)


def decor_char(tile):
    """The legend character for a scenery tile (copse trees use the legend's own: T, t...)."""
    if tile in DECOR_CHARS:
        return DECOR_CHARS[tile]
    return next(ch for ch, t in W.LEGEND.items() if t == tile)


# ------------------------------------------------------------------ the Isle (original maps): patches
SCENERY_NAMES = set(SCENERY_TILES)


LOGGED = {}


def isle_patches():
    """{map: dict(tiles=[(x, y, old, new)], entities=[...])} for build_content.patches()."""
    import os
    LOGGED.clear()
    if os.path.exists(C.PATCH_LOG):
        for l in C.read_lines(C.PATCH_LOG):
            r = l.split("\t")
            if len(r) == 6 and r[0] == "TILE":
                LOGGED.setdefault(r[1], []).append((int(r[2]), int(r[3]), r[4], r[5]))
    out = {}
    for name in sorted(W.PROTECTED_MAPS):
        if not name.endswith(",0"):
            continue
        lines = C.read_lines(C.p("Maps", name + ".txt"))
        rows = [r.split(":") for r in lines[:21]]
        grid = [[C.built_base(c) for c in r] for r in rows]          # (decor: as the old tiles)
        for x, y, old, new in LOGGED.get(name, []):          # undo our own earlier patches: plan from the original
            if grid[y - 1][x - 1] == new:
                grid[y - 1][x - 1] = old
        ents = [l.split("\t") for l in lines[21:] if "\t" in l]
        ents = [e for e in ents if e[0] in ("NPC", "GoodNPC", "BadNPC", "MapItem", "StaticObject")]
        lm = LANDMARKS.get(name, {})
        fixed = {(x, y): t for x, y, t in lm.get("tiles", [])}
        for (x, y), t in fixed.items():
            assert grid[y - 1][x - 1] in GRASS, (name, x, y, grid[y - 1][x - 1], t)
        locks = [(int(e[1]), int(e[2])) for e in (l.split("\t") for l in lines[21:]) if e[0] in ("Lock", "Trigger") and len(e) > 2 and e[1].isdigit()]
        new_ents = landmark_entities(name)
        # our own earlier wildlife lines are in the file too: leave them out so the choice doesn't drift
        own = {"\t".join(str(v) for v in e) for e in new_ents}
        base_ents = [e for e in ents if e[1] not in ENTITIES and "\t".join(e) not in own]
        busy = busy_cells(base_ents + new_ents, locks + list(fixed))
        chosen = plan(name, grid, busy, fixed)
        tiles = [(x, y, grid[y - 1][x - 1], t) for (x, y), t in sorted(chosen.items())]
        out[name] = dict(tiles=tiles, entities=new_ents + wildlife_entities(name, grid, chosen, busy))
    return out


# ------------------------------------------------------------------ scripts
def scripts():
    S = {}
    # chests: one script for all of them; each map's chest gives its treasure once
    steps = ["// Chests: the royal treasury (4,4,0), Brokk's vault (2,4,-3) and the landmarks' hidden chests",
             "// (build_scenery.py CHESTS). Each gives its reward once. Generated by build_content.py",
             (">Distance.From.Clicked.Entity", "48", "@far")]
    chests = [("4,4,0", ("TreasuryLooted", [("Gold_Coin(s)", 80), ("Iron_Platebody", 1), ("Super_Potion", 1)],
                         "The King's chest holds 80 gold, an iron platebody and a super potion!")),
              ("2,4,-3", ("VaultLooted", [("Gold_Coin(s)", 120), ("Steel_Helm", 1), ("Emerald", 2)],
                          "Brokk's chest holds 120 gold, a steel helm and two emeralds!"))] + sorted(CHESTS.items())
    # Scripts are at most 99 lines, so 7 chests a script: Open Chest, then Open Chest 2, 3... (each goes on to the next
    # when the chest isn't on its maps)
    groups = [chests[i:i + 7] for i in range(0, len(chests), 7)]
    for gi, group in enumerate(groups):
        name = "Open Chest" if gi == 0 else "Open Chest %d" % (gi + 1)
        if gi:
            steps = ["// More chests (Open Chest goes on here). Generated by build_content.py"]
        for i, (m, (attr, loot, msg)) in enumerate(group):
            nxt = "@chest%d" % (i + 1) if i + 1 < len(group) else "@more"
            if i:
                steps.append("chest%d:" % i)
            steps += [(">On.Map", m, nxt),
                      ("Get.Value", "ATTRIBUTE", attr, "Variable.1$"),
                      (">Conditional", "$Variable.1=0", "@empty"),
                      ("Update.Attribute", attr, "=1"),
                      ("Play.Sound", "Chest")]
            steps += [("Give.Item", item, str(q)) for item, q in loot]
            steps += [("Display.Message", "Yellow", msg), ("End",)]
        steps.append("more:")
        if gi + 1 < len(groups):
            steps += [("Goto.Script", "Open Chest %d" % (gi + 2)), ("End",)]
        steps += ["empty:", ("Display.Message", "Cyan", "The chest is empty."), ("End",)]
        if gi == 0:
            steps += C.too_far()
        S[name] = steps
    # fallen logs: firewood for anyone with an axe; the log goes, and a new one has fallen a few minutes later
    S["Chop Fallen_Log"] = C.chop_script("Fallen_Log", "fallen log", "Logs", 1, "0.05", 70, 240)
    for i, st in enumerate(S["Chop Fallen_Log"]):
        if isinstance(st, tuple) and st[0] == "Change.Tile":
            S["Chop Fallen_Log"][i] = ("Change.Tile", st[1], "Grass001", st[3], st[4])
        if isinstance(st, tuple) and st[0] == ">Random":
            S["Chop Fallen_Log"][i] = (">Random", "100", st[2])    # always used up
    for tool, _, _ in C.AXES:
        S["Use %s With Fallen_Log" % tool] = [("Goto.Script", "Chop Fallen_Log"), ("End",)]
    # wells and the pond: water, and fish in the pond
    S["Use Bucket With Well"] = [("Goto.Script", "Use Bucket With Water"), ("End",)]
    S["Use Bucket With Pond"] = [("Goto.Script", "Use Bucket With Water"), ("End",)]
    S["Use Fishing_Rod With Pond"] = [("Goto.Script", "Use Fishing_Rod With Water"), ("End",)]
    S["Talk to Butterfly"] = [(">Random", "50", "@b2"),
                              ("Display.Message", "Cyan", "The butterfly lands on your nose for a moment, then flutters off."),
                              ("End",), "b2:",
                              ("Display.Message", "Cyan", "The butterfly has nothing to say. It's a butterfly."), ("End",)]
    # the hermit and his quest
    S["Talk to Hermit"] = [
        "// The Hermit's Fire (HermitQuest 0-2). Generated by build_content.py",
        ("Get.Value", "ATTRIBUTE", "HermitQuest", "Variable.1$"),
        (">Conditional", "$Variable.1=0", "@q1"),
        ("Display.Conversation", "Hermit", "A visitor! Nobody comes out here but the rabbits.\\My fire's dying, and my old bones won't swing an axe. Fetch me five oak logs and I'll give you something for your trouble.\\Oaks grow in these woods. You'll need Woodcutting 10.",
         "I'll fetch them.", "@accept", "Not now.", "@bye"),
        ("End",),
        "accept:",
        ("Update.Attribute", "HermitQuest", "=1"),
        ("Display.Message", "Yellow", "Quest started: The Hermit's Fire."),
        ("End",),
        "q1:",
        (">Conditional", "$Variable.1=1", "@done"),
        (">Got.Item", "Oak_Logs", "5", "@notyet"),
        ("Take.Item", "Oak_Logs", "5"),
        ("Update.Attribute", "HermitQuest", "=2"),
        ("Give.Item", "Oak_Staff", "1"),
        ("Give.Item", "Gold_Coin(s)", "25"),
        ("Update.Skill", "Woodcutting", "+1.5"),
        ("Display.Conversation", "Hermit", "Ahh, good oak. That'll burn all week. Here, take my old staff: it'll put some fire in your spells.\\And a secret, for a friend: the standing stones on the north-west headland hide more than moss.",
         "Thank you!", "@bye"),
        ("Display.Message", "Yellow", "Quest complete! You receive an oak staff, 25 gold and Woodcutting experience."),
        ("End",),
        "notyet:",
        ("Display.Conversation", "Hermit", "Five oak logs, friend. Oaks are the broad ones with the acorns. Woodcutting 10, mind.", "I'll keep looking.", "@bye"),
        ("End",),
        "done:",
        (">Random", "50", "@done2"),
        ("Display.Conversation", "Hermit", "The fire's lovely, thanks to you.\\They say the graveyard in the east isn't as quiet as it should be. And goblins have camped on the south shore.", "Interesting.", "@bye"),
        ("End",),
        "done2:",
        ("Display.Conversation", "Hermit", "In the Southlands, past the King's guard, there's a grove of ancient yews in the Whispering Woods.\\Somebody hid something under them long ago. I never went back for it.", "Interesting.", "@bye"),
        "bye:",
        ("End",)]
    # villagers: more gossip, with hints about the landmarks
    isle = ["Lovely day on the Isle! If you're bored, there's a hole under the cliffs to the east. Bats down there, mind.",
            "The milkmaid up north keeps cows and sheep. She'll sell you shears if you fancy some wool.\\The ferry to the mainland leaves from the pier in the south.",
            "There's a ring of old stones on the north-west headland. My granny said never to dig there. So of course I did. Found nothing. Wrong spot, probably.",
            "An old watchtower stands in ruins by the sea in the north-east. The wolves have it now.",
            "A hermit lives in the western woods. Odd fellow, but he knows every tree on the Isle.",
            "Don't go near the graveyard in the east after dark. Or before dark. Just don't."]
    south = ["Fresh bread at the bakery, tools at the general store, and the smithy has a furnace if you've ore to smelt.",
             "Watch out for wolves in the Whispering Woods. And goblins. And hobgoblins. Honestly, I never leave the village.",
             "Ducks on the lily pond in the east, rabbits in the woods. You'll not starve out there, if you can catch them.",
             "My cousin swears there's treasure buried under the yew trees deep in the Whispering Woods."]
    steps = ["// Villagers' gossip, with hints about the landmarks. Generated by build_content.py",
             (">Conditional", "$Map.Y<3", "@south")]
    for group, lines_, prefix in ((isle, None, "isle"), (south, None, "south")):
        if prefix == "south":
            steps.append("south:")
        n = len(group)
        for i, text in enumerate(group):
            if i < n - 1:
                # pick line i with chance 1/(n-i) of what's left, so each is equally likely
                steps.append((">Random", str(100 // (n - i)), "@%s%d" % (prefix, i + 1)))
            steps += [("Display.Conversation", "Villager", text, "Thanks.", "@bye"), ("End",)]
            if i < n - 1:
                steps.append("%s%d:" % (prefix, i + 1))
    steps += ["bye:", ("End",)]
    S["Talk to Villager"] = steps
    return S


QUEST = ("The Hermit's Fire", [
    ("Giver", "Hermit"), ("Attribute", "HermitQuest"),
    ("Stage0", "Find the hermit at his camp in the Isle's western woods."),
    ("Stage1", "Bring the hermit 5 oak logs (chop oak trees: Woodcutting 10)."),
    ("Done", "2")])


# ------------------------------------------------------------------ hook
def extend(world, content):
    global W, C
    W, C = world, content
    for name, (walk, show, use, exa, los) in SCENERY_TILES.items():
        C.TILES[name] = (walk, show, use, exa, los, None)
    for name, e in ENTITIES.items():
        if e["kind"] == "bad":
            C.ENTITIES[name] = C.bad(e["examine"], e["hp"], e["aspeed"], e["strength"], e["defence"], e["aggro"],
                                     e["move"], e["aggressive"], e["respawn"], e["drops"])
        else:
            C.ENTITIES[name] = C.good(e["examine"], use=e["use"], speed=e.get("speed"))
        # Small creatures don't block the way: you walk over rabbits and ducks (drawn under you) and under butterflies
        if "solid" in e:
            C.ENTITIES[name] = C.ENTITIES[name] + [("Solid", e["solid"]), ("Layer", e["layer"])]
    C.MOVEMENT.update(MOVEMENT)
    if not any(q[0] == QUEST[0] for q in C.QUESTS):
        C.QUESTS.append(QUEST)
    if not any(g[0] == "Firewood" for g in C.GATHERING):
        C.GATHERING.insert(1, ("Firewood", dict(Gives="Logs", Source="Fallen_Log001", Verb="Chop",
                                                Tool="Bronze_Axe/Axe/Steel_Axe/Mithril_Axe", Skill="Woodcutting",
                                                Level="1", XP="0.05", Where="Fallen logs lying in the meadows and woods")))
    decorate_generated()
