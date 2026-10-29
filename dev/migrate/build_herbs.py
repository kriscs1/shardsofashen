"""Herbs: the herb redrawn to match the other items, and four more to find and brew with.

Not run on its own: build_content.extend() calls extend() here last (after every map exists and the scenery is down),
so `python -I "dev\\migrate\\build_world.py"` builds it.

  * THE HERB and BOG MYRTLE: drawn again as sprigs with an outline and a light side, like the berries and mushrooms
    (they were flat smudges). Frost_Lily (build_omens) is the herb recoloured, so it follows.
  * FOUR NEW HERBS (HERBS), each growing in its own lands, in patches (decor: <Herb>_Patch001, picked: ...002, grows
    back): Sage on the moors, hills and downs (Alchemy 5), Marigold in the Southlands' meadows (10), Nightshade in the
    deep woods (20), Emberroot in the Ashwold's ash (30). Picked like herb patches (Pick <Herb>_Patch), listed in the
    journal's Gathering tab, bought by the herbalist.
  * BREWING (CRAFT-Potion_Making): the Owl, Defence, Combat and Mega potions now need the new herbs, and two new potions
    use them: the Healing Draughts (Marigold, Sage, Cave Mushroom: Minor 8-12, 15-20, Major 26-32) and the Ember Tonic (Emberroot, Nightshade: +5 Attack).
  * WHERE: a couple of patches of each on the generated surface maps of its lands, on open ground away from people and
    doors (the cell and the choice are a hash of the map and cell, so every build puts them in the same places).
"""
import math
import zlib

import sprite_kit as K

W = C = None        # build_world, build_content

OPEN = "1" * 49

# name: (patch examine, lands, ground tiles it grows on, Alchemy level, XP, seconds to grow back, item value,
#        item examine, picking messages, the herbalist's Where)
HERBS = {
    "Sage": ("A clump of sage, soft and grey-green. It smells clean and sharp.", ("moor", "hills", "downs"),
             ("Grass001",), 5, "0.15", 55, 6, "A sprig of sage: soft grey leaves that smell clean and sharp.",
             ("You pinch off some sage...", "...soft leaves, sharp scent."),
             "Sage clumps on the moors, the hills and the downs"),
    "Marigold": ("Marigolds, bright as little suns.", ("south",), ("Grass001",), 10, "0.2", 60, 8,
                 "A marigold: an orange flower, good for salves and potions.",
                 ("You pick a marigold or two...", "...bright orange, and sticky with sap."),
                 "Marigolds in the meadows of the Southlands"),
    "Nightshade": ("Nightshade: dark leaves, purple stars and glossy black berries. Handle with care.",
                   ("wood", "elder"), ("Grass001", "Forest_Floor001", "Dirt001"), 20, "0.3", 75, 12,
                   "A sprig of nightshade. Its berries are poison, but a skilled hand can brew with it.",
                   ("You carefully cut a sprig of nightshade...", "...without touching the berries."),
                   "Nightshade in the deep woods of the Wildwood and the Elderwood"),
    "Emberroot": ("Emberroot: red roots glowing in the ash like coals.", ("ash",), ("Ash001", "Dirt001", "Grass001"),
                  30, "0.45", 90, 20, "Emberroot, still warm. It glows faintly in your hand.",
                  ("You dig at the emberroot with your fingers...", "...and pull up a root, warm as a coal."),
                  "Emberroot in the ash of the Ashwold"),
}
PER_MAP = {"Marigold": 3}    # patches of each herb on a map of its lands (2 unless said here: the Southlands
                             # have fewer maps)

POTIONS = {     # name: (hue of the Basic_Potion recoloured, value, examine, Spells.ini keys)
    "Minor_Healing_Draught": (0.95, 15, "A pale pink draught of marigold. Drink it to heal 8-12 hitpoints.",
                              dict(Effect="Heal", Heal="8-12", Impact="Heal_Glow", Sound="SpellHeal",
                                   Info="heals 8-12 hitpoints")),
    "Healing_Draught": (0.93, 35, "A rose-pink draught of sage and marigold. Drink it to heal 15-20 hitpoints.",
                        dict(Effect="Heal", Heal="15-20", Impact="Heal_Glow", Sound="SpellHeal",
                             Info="heals 15-20 hitpoints")),
    "Major_Healing_Draught": (0.99, 80, "A deep crimson draught of sage, marigold and cave mushroom. Drink it to heal "
                                        "26-32 hitpoints.", dict(Effect="Heal", Heal="26-32", Impact="Heal_Glow",
                                                                 Sound="SpellHeal", Info="heals 26-32 hitpoints")),
    "Ember_Tonic": (0.04, 110, "A smouldering orange tonic. +5 Attack for two and a half minutes.",
                    dict(Effect="Boost", Attack="5", Duration="150", Impact="Stone_Glow", Sound="SpellShield",
                         Info="+5 Attack for two and a half minutes")),
}
RECIPES = {     # CRAFT-Potion Making: the recipes the new herbs go into (a potion's line replaced, or added)
    "Owl_Potion": "Owl_Potion,Sage 2 Egg 1 Empty_Vial 1,0.7,8",
    "Minor_Healing_Draught": "Minor_Healing_Draught,Marigold 1 Empty_Vial 1,0.4,1",
    "Healing_Draught": "Healing_Draught,Sage 1 Marigold 2 Empty_Vial 1,0.8,6",
    "Major_Healing_Draught": "Major_Healing_Draught,Sage 2 Marigold 2 Cave_Mushroom 1 Empty_Vial 1,1.3,13",
    "Defence_Potion": "Defence_Potion,Marigold 2 Iron_Ore 1 Empty_Vial 1,0.9,15",
    "Combat_Potion": "Combat_Potion,Nightshade 2 Spider_Silk 1 Cave_Mushroom 1 Empty_Vial 1,1.2,22",
    "Ember_Tonic": "Ember_Tonic,Emberroot 2 Nightshade 1 Empty_Vial 1,1.6,32",
    "Mega_Potion": "Mega_Potion,Emberroot 1 Herb 2 Cave_Mushroom 2 Emerald 1 Empty_Vial 1,2,35",
}


def h(*parts):
    return zlib.crc32(":".join(str(v) for v in parts).encode()) % 1000


# =================================================================================================== drawing
def leaf(img, x0, y0, ang, ln, wd, light, mid, dark, rib=None):
    """A pointed leaf from (x0, y0) along angle ang (radians, 0 = right, -pi/2 = up): lit on its upper-left half."""
    ca, sa = math.cos(ang), math.sin(ang)
    lit = 1 if sa - ca > 0 else -1                      # which side of the leaf faces the light (up and left)
    for y in range(32):
        for x in range(32):
            px, py = x + 0.5 - x0, y + 0.5 - y0
            t = px * ca + py * sa                       # along the leaf
            s = -px * sa + py * ca                      # across it
            if not 0 <= t <= ln:
                continue
            half = wd * math.sin(math.pi * t / ln) ** 0.75
            if abs(s) > half:
                continue
            v = s * lit / max(0.5, half)
            c = light if v > 0.25 else dark if v < -0.45 else mid
            if rib and abs(s) < 0.5 and 1 < t < ln - 1:
                c = rib
            img[y][x] = c


def stroke(img, pts, width, light, mid, dark):
    """A shaded stem through pts [(x, y)...]."""
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        vx, vy = x1 - x0, y1 - y0
        ln = math.hypot(vx, vy) or 1
        for y in range(32):
            for x in range(32):
                px, py = x + 0.5 - x0, y + 0.5 - y0
                t = max(0, min(1, (px * vx + py * vy) / (ln * ln)))
                dx, dy = px - vx * t, py - vy * t
                d = math.hypot(dx, dy)
                if d <= width / 2.0:
                    side = (dx * vy - dy * vx) / ln
                    img[y][x] = light if side < -width * 0.15 else dark if side > width * 0.2 else mid


def disc(img, cx, cy, r, light, mid, dark):
    K.shaded_ellipse(img, cx, cy, r, r, mid, light, dark)


def star(img, cx, cy, petal, centre):
    for dx, dy in ((0, -2), (-2, -1), (2, -1), (-1, 1), (1, 1), (0, -1), (-1, 0), (1, 0), (0, 0)):
        K.put(img, cx + dx, cy + dy, petal)
    K.put(img, cx, cy, centre)


def berry(img, cx, cy):
    disc(img, cx, cy, 1.6, (90, 80, 110), (34, 28, 46), (14, 10, 20))
    K.put(img, cx - 1, cy - 1, (220, 220, 240))


GREEN = ((132, 204, 98), (74, 152, 60), (36, 90, 32))
SAGE = ((196, 214, 176), (142, 166, 124), (86, 108, 78))
DARK = ((92, 146, 86), (50, 98, 56), (24, 56, 32))
MYRTLE = ((140, 176, 116), (84, 126, 76), (44, 76, 42))


def sprig(colours, pairs, ln, wd, top=True, lean=0.0, rib=None):
    """A stem with pairs of leaves up it: the shape the herb items share."""
    img = K.new()
    light, mid, dark = colours
    stem = [(17 + lean, 29), (16.5 + lean * 0.5, 20), (16, 11), (15.5, 6)]
    for i in range(pairs):
        t = 0.25 + 0.6 * i / max(1, pairs - 1)
        x, y = 17 + lean * (1 - t) - t, 28 - 21 * t
        size = ln * (1.1 - 0.35 * t)
        leaf(img, x, y, -math.pi / 2 - 0.95 + 0.1 * i, size, wd, light, mid, dark, rib)
        leaf(img, x, y - 1, -math.pi / 2 + 0.95 - 0.1 * i, size, wd, light, mid, dark, rib)
    stroke(img, stem, 1.6, light, K.mul(mid, 0.9), dark)
    if top:
        leaf(img, 15.8, 9, -math.pi / 2 - 0.08, ln * 0.85, wd * 0.9, light, mid, dark, rib)
    return img


def herb_item():
    return K.outline_img(sprig(GREEN, 3, 9, 2.8, rib=(56, 120, 46)), (18, 44, 16))


def bog_myrtle_item():
    img = sprig(MYRTLE, 4, 7, 1.9)
    for x, y in ((11, 13), (21, 12), (12, 19), (21, 18), (15, 6)):     # little red-brown catkins
        K.put(img, x, y, (170, 84, 92))
        K.put(img, x, y + 1, (120, 52, 64))
    return K.outline_img(img, (24, 40, 22))


def sage_item():
    img = sprig(SAGE, 3, 7, 2.7, rib=(120, 144, 108))
    for x, y in ((11, 15), (20, 14), (13, 21), (19, 20), (15, 8)):     # the soft fuzz
        K.put(img, x, y, (228, 236, 214))
    return K.outline_img(img, (46, 58, 40))


def marigold_item():
    img = K.new()
    stroke(img, [(17, 29), (16, 21), (13, 13)], 1.6, *GREEN)
    stroke(img, [(16, 21), (21, 15)], 1.4, *GREEN)
    leaf(img, 16.5, 25, -math.pi / 2 - 1.1, 8, 2.6, *GREEN)
    leaf(img, 16.5, 24, -math.pi / 2 + 1.0, 8, 2.6, *GREEN)
    for cx, cy, r in ((12, 10, 5.0), (22, 13, 4.2)):
        disc(img, cx, cy, r, (255, 206, 84), (244, 142, 30), (186, 86, 18))
        for a in range(10):                         # ruffled petal edge
            ang = a * math.pi / 5
            K.put(img, int(round(cx + math.cos(ang) * (r - 0.6))), int(round(cy + math.sin(ang) * (r - 0.6))),
                  (255, 176, 52) if a % 2 else (214, 104, 22))
        disc(img, cx, cy, r * 0.32, (170, 90, 30), (130, 64, 20), (96, 44, 14))
    return K.outline_img(img, (92, 40, 10))


def nightshade_item():
    img = sprig(DARK, 2, 9, 2.9, top=False)
    stroke(img, [(16, 12), (12, 6)], 1.2, *DARK)
    stroke(img, [(16, 12), (21, 7)], 1.2, *DARK)
    star(img, 12, 6, (164, 104, 214), (250, 214, 70))
    star(img, 21, 7, (138, 84, 190), (250, 214, 70))
    for cx, cy in ((20, 21), (23, 23), (20, 25)):
        berry(img, cx, cy)
    return K.outline_img(img, (14, 18, 20))


def emberroot_item():
    img = K.new()
    red = ((232, 112, 54), (168, 60, 34), (96, 30, 22))
    stroke(img, [(15, 9), (17, 14), (14, 19), (17, 24), (15, 29)], 3.6, *red)
    stroke(img, [(17, 14), (22, 17), (24, 22)], 1.8, *red)
    stroke(img, [(14, 19), (10, 22), (9, 26)], 1.6, *red)
    for x, y in ((16, 12), (15, 18), (16, 22), (21, 17), (11, 22), (15, 26)):     # glowing cracks
        K.put(img, x, y, (255, 204, 96))
        K.put(img, x, y + 1, (255, 150, 60))
    leaf(img, 15, 9, -math.pi / 2 - 0.6, 7, 2.2, (156, 60, 52), (110, 36, 34), (66, 20, 22))
    leaf(img, 15.5, 9, -math.pi / 2 + 0.5, 6, 2.0, (156, 60, 52), (110, 36, 34), (66, 20, 22))
    return K.outline_img(img, (44, 14, 10))


ITEMS = {"Herb": herb_item, "Bog_Myrtle": bog_myrtle_item, "Sage": sage_item, "Marigold": marigold_item,
         "Nightshade": nightshade_item, "Emberroot": emberroot_item}


def fan(img, seed, n, ln, colours, cx=16, cy=22, spread=1.0, wd=1):
    """A clump of leaves fanned up from (cx, cy): the shape of a herb patch."""
    rng = __import__("random").Random(seed)
    light, mid, dark = colours
    for i in range(n):
        a = -math.pi / 2 + spread * (math.pi / 2) * ((i + 0.5) / n * 2 - 1) + rng.uniform(-0.1, 0.1)
        size = rng.uniform(0.7, 1.0) * ln * (0.65 + 0.35 * abs(math.sin(a)))
        for t in range(int(size)):
            x, y = cx + math.cos(a) * t, cy + math.sin(a) * t * 0.85
            c = light if t > size * 0.55 else mid if i % 2 else K.add(mid, -14)
            K.put(img, int(round(x)), int(round(y)), c)
            if wd and 1 < t < size - 1:
                K.put(img, int(round(x + 1)), int(round(y)), dark if t < size * 0.5 else mid)
    for x in range(cx - 5, cx + 6):                 # the clump's foot, dark against the ground
        if abs(x - cx) < 5:
            K.put(img, x, cy + 1, dark)


def sage_patch():
    img = K.new()
    for x0, top in ((11, 7), (16, 4), (21, 8)):     # lilac flower spikes on grey stalks
        for y in range(top, 21):
            K.put(img, x0, y, ((176, 148, 222) if y % 2 else (124, 98, 180)) if y < top + 7 else SAGE[2])
        K.put(img, x0, top - 1, (206, 188, 240))
    fan(img, 11, 18, 12, SAGE, wd=1)
    return img


def marigold_patch():
    img = K.new()
    fan(img, 12, 18, 12, GREEN)
    for cx, cy in ((9, 13), (16, 8), (23, 12), (12, 18), (20, 16)):
        for dx, dy in ((0, -2), (-1, -2), (1, -2), (-2, -1), (2, -1), (-2, 0), (2, 0), (-2, 1), (2, 1), (-1, 2),
                       (0, 2), (1, 2)):         # a round flower: orange petals, lit at the top left
            K.put(img, cx + dx, cy + dy, (255, 200, 80) if dx + dy < -1 else (232, 128, 26) if dx + dy < 2
                  else (178, 82, 18))
        for dx, dy in ((-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1)):
            K.put(img, cx + dx, cy + dy, (246, 150, 34))
        K.put(img, cx, cy, (120, 60, 18))
    return img


def nightshade_patch():
    img = K.new()
    fan(img, 13, 18, 12, DARK)
    for cx, cy in ((11, 10), (20, 9), (16, 13)):
        star(img, cx, cy, (156, 98, 206), (250, 214, 70))
    for cx, cy in ((22, 17), (24, 19), (9, 17)):
        berry(img, cx, cy)
    return img


def emberroot_patch():
    img = K.new()
    for pts in ([(16, 23), (11, 24), (6, 22)], [(16, 23), (21, 25), (27, 24)], [(16, 23), (14, 27), (10, 29)],
                [(16, 23), (19, 28), (23, 30)]):    # roots across the ash, glowing
        stroke(img, pts, 1.3, (250, 150, 60), (200, 80, 36), (120, 40, 24))
    for x, y in ((9, 23), (24, 25), (12, 28), (21, 29)):
        K.put(img, x, y, (255, 220, 120))
    fan(img, 14, 12, 9, ((170, 70, 58), (122, 42, 38), (70, 22, 22)), cy=22, spread=0.85)
    for x, y in ((13, 14), (19, 15)):
        K.put(img, x, y, (255, 180, 80))
    return img


def picked(colours, seed):
    """What's left once it's picked: a few stalks."""
    img = K.new()
    rng = __import__("random").Random(seed)
    for _ in range(6):
        x, y = rng.randint(10, 22), rng.randint(17, 23)
        K.rect(img, x, y - rng.randint(1, 2), x, y, colours[1])
        K.put(img, x, y + 1, colours[2])
    return img


PATCHES = {"Sage": (sage_patch, SAGE), "Marigold": (marigold_patch, GREEN), "Nightshade": (nightshade_patch, DARK),
           "Emberroot": (emberroot_patch, ((170, 70, 58), (122, 42, 38), (70, 22, 22)))}


def potion_img(hue):
    return K.hue_shift(K.load("Entities", "Basic_Potion"), target_hue=hue, sat_mul=1.05,
                       pred=lambda c: max(c) - min(c) > 40)


def make_art():
    """The items, the patches (see-through: decor over any ground) and the two potions. Only changed files are written."""
    made = []
    for name, fn in ITEMS.items():
        if K.save("Entities", name, fn()):
            made.append("sprites\\Entities\\%s.png" % name)
    for herb, (fn, colours) in PATCHES.items():
        for tile, img in (("%s_Patch001" % herb, fn()), ("%s_Patch002" % herb, picked(colours, len(herb)))):
            if K.save("Tiles", tile, img):
                made.append("sprites\\Tiles\\%s.png" % tile)
    for name, (hue, _, _, _) in POTIONS.items():
        if K.save("Entities", name, potion_img(hue)):
            made.append("sprites\\Entities\\%s.png" % name)
    return made


# =================================================================================================== where they grow
def land(name):
    """The lands a surface map is in: a Wildlands land (wood, moor, marsh, hills, desert, snow), the Eastreach's (elder,
    downs), the Cinderlands' (ash, cinder) or "south" (the Southlands); None for caves, upper floors and the rest."""
    import build_regions as R
    import build_eastreach as E
    import build_cinder as CI
    x, y, z = (int(v) for v in name.split(","))
    if z != 0:
        return None
    for mod in (R, E, CI):
        if mod.MX0 <= x <= mod.MX1 and mod.MY0 <= y <= mod.MY1:
            return mod.land_of(x * mod.GW + 12, y * mod.GH + 10)
    if 0 <= x <= 4 and 0 <= y <= 4:
        return "south"
    return None


def legend_char(cell):
    """The legend character for a cell text (one is added for a new one)."""
    for ch, t in W.LEGEND.items():
        if t == cell:
            return ch
    ch = next(chr(c) for c in range(0x400, 0x500) if chr(c) not in W.LEGEND)
    W.LEGEND[ch] = cell
    return ch


def scatter():
    import build_scenery as SC
    placed = 0
    for name in sorted(W.MAPS):
        spec = W.MAPS[name]
        if name in W.PROTECTED_MAPS or not name.endswith(",0"):
            continue
        here = land(name)
        herbs = [hb for hb, d in HERBS.items() if here in d[1]]
        if not herbs:
            continue
        extra = [(int(l[0]), int(l[1])) for l in spec.get("locks", [])] + \
                [(int(t[1]), int(t[2])) for t in spec.get("triggers", [])]
        busy = SC.busy_cells([e for e in spec["entities"] if e[0] != "Id"], extra)
        rows = spec["rows"]
        taken, changes = set(), []
        for hb in herbs:
            grounds = HERBS[hb][2]
            spots = sorted((h(name, x, y, hb), x, y) for y in range(3, len(rows) - 1) for x in range(3, len(rows[0]) - 1)
                           if W.LEGEND.get(rows[y - 1][x - 1]) in grounds and (x, y) not in busy and
                           all(abs(x - tx) + abs(y - ty) >= 4 for tx, ty in taken))
            n = 0
            for _, x, y in spots:
                if n >= PER_MAP.get(hb, 2):
                    break
                if any(abs(x - tx) + abs(y - ty) < 4 for tx, ty in taken):
                    continue
                ground = W.LEGEND[rows[y - 1][x - 1]]
                changes.append((x, y, legend_char("%s+Decor(%s_Patch001)" % (ground, hb))))
                taken.add((x, y))
                n += 1
        if changes:
            spec["rows"] = C.set_cells(rows, changes)
            placed += len(changes)
    return placed


# =================================================================================================== the data
def extend(world, content):
    global W, C
    W, C = world, content
    for hb, (pexa, _, _, level, xp, regrow, value, iexa, (msg_try, msg_ok), where) in HERBS.items():
        p1, p2 = "%s_Patch001" % hb, "%s_Patch002" % hb
        C.TILES[p1] = (OPEN, "1", "Pick", "%s (Alchemy %d)" % (pexa, level), "1", None)
        C.TILES[p2] = (OPEN, "1", "", "The %s has been picked. It will grow back." % hb.lower(), "1", None)
        for t in (p1, p2):
            C.TILE_EXTRA[t] = [("Layer", "Decor"), ("Sway", "1.2")]
            C.WALK_SPEED[t] = "0.85"
        C.ENTITIES[hb] = C.item(value, iexa, 50)
        if not any(g[0] == hb for g in C.GATHERING):
            C.GATHERING.append((hb, dict(Gives=hb, Source=p1, Verb="Pick", Tool="", Skill="Alchemy", Level=str(level),
                                         XP=xp, Where=where)))
        W.S["Pick %s_Patch" % hb] = C.pick_script(hb.lower(), hb, p2, regrow, "Alchemy", level, xp, 60, msg_try,
                                                  msg_ok)
    for name, (_, value, exa, keys) in POTIONS.items():
        C.ENTITIES[name] = C.item(value, exa, 1, use="Drink") + [("Spell", name)]
        if not any(s[0] == name for s in C.SPELLS):
            C.SPELLS.append((name, dict(dict(Scroll=name, Kind="Potion", Skill="Alchemy", Level="1",
                                             Leaves="Empty_Vial", XP="0"), **keys)))
    rack = C.CRAFT["CRAFT-Potion_Making"][1]
    for potion, line in RECIPES.items():
        i = next((k for k, r in enumerate(rack) if r.startswith(potion + ",")), None)
        if i is None:
            rack.append(line)
        else:
            rack[i] = line
    rack.sort(key=lambda r: int(r.split(",")[3]) if len(r.split(",")) > 3 else 1)    # (by level, as the rack shows)
    shop = C.SHOP_ADD.setdefault("SHOP-Herbalist", [])
    for hb in HERBS:
        if not any(s.startswith(hb + ",") for s in shop):
            shop.append(hb + ",0")
    scatter()
    W.EXTRA_STEPS.insert(0, make_art)       # (first: Frost_Lily, build_omens, is the herb recoloured)
