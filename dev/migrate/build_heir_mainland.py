"""The heir's story on the mainland: the main quest line's chapters 5 to 17, from the ferry to the throne (it replaces
King Tyron's hobgoblin hunt as the King's, The Ashen Hand, The Ashen Omens and The Dragon of Ashpeak). Run it again: it
writes the same again. Run build_towns.py and build_galaith.py first (their buildings hold this story's people).

  python -I "dev\\migrate\\build_heir_mainland.py"

  5  The Temporary Capital (ParliamentQuest 0-2). Southport's port guard: Galaith is shut, Southport is the capital for
     now, and its City Hall is the Parliament. The Speaker: only Bert, the great wizard at the Wizards' Court, can break
     the barrier; take the Parliament's letter east, to the Mayor of Ashford, who keeps the road.
  6  The Ashford Road (AshfordQuest 0-3). The Mayor, in Ashford's Town Hall: goblins raid the farms; drive them off (the
     Farm_Raid wave) and the road east is open: the Mayor's pass, for the King's Steward.
  7  The Steward's Hunt (HobgoblinQuest 0-2, the old King's Hobgoblin Hunt). The Steward at King Rupert's Keep: five
     hobgoblins from the old iron mine, and the causeway to the Wizards' Court is yours.
  8  Bert's Three Treasures (BertQuest 0-2). Bert, at the top of the Wizards' Court's tower: the staff, the spell book
     and the ring (9, 10, 11). Brought, he owns up: he only wanted the ring (it goes with his new robe, and he can't
     stand the Ashen Priest). He teaches you the spell, gives you the staff, and warns: only the Sword of Valour, driven
     into its heart, kills the dragon.
  9  The Staff of Estforlan (StaffQuest 0-2): the Steward's key to the King's solar at the top of the keep (2,4,1),
     its old guard risen; the staff on its rack.
 10  The Sunken Grimoire (GrimoireQuest 0-3): the scholar in Dunerest; a sand-buried library in the desert north of
     it (dig it out: a spade), its guardians; the Grimoire of Unbinding on its lectern (1,9,-1).
 11  The Ember Ring (RingQuest 0-2): the Warden in Emberwatch; the Ashen Priest, in the Cinder Fort, wears it.
 12  A Ship for Dragon Island (ShipQuest 0-2): Captain Rook, on the shore by Ravensgate: planks and nails for his hull.
 13  The Island of Dragons (DragonIsleQuest 0-2): the island (8,10,0); three Valour Seals from its drakes open the
     Temple of Valour.
 14  The Sword of Valour (ValourQuest 0-3): the temple's guardian tests you (a fight); the sword in the stone.
 15  The Dragon of Galaith (GalaithQuest 0-2): the staff on the barrier, Bert's spell; the dragon speaks; the fight.
 16  The Royal Guard (GuardQuest 0-5): the palace's captain; the Lord Chancellor in Parliament; the Royal Archivist in
     the City Hall, who knows the amulet's seal; the Chancellor's warrant; the captain lets you in.
 17  The True Heir (KingQuest 0-1): King Rupert. The amulet, the will. He makes you king. Jimmy sleeps on the throne;
     Wardhaven's gates and Galaith's mine open.
"""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import story_kit as K  # noqa: E402
from story_kit import Map, obj_line, say, ini  # noqa: E402

MAKER = "build_heir_mainland.py"
XT, YT, TW = K.XT, K.YT, K.TW
V1, V2 = "Variable.1$", "Variable.2$"
FAR = [("@far",), ("Display.Message", "DarkRed", "You are too far away!", "Denied"), ("End",)]


def w(name, rows):
    K.write_script(name, rows, MAKER)


def at(x, y, dy=0):
    return "%d,%d" % ((x - 1) * TW, (y - 1) * TW + dy)


# ================================================================== finding things the other builders put down
def all_maps():
    return [f[:-4] for f in os.listdir(os.path.join(K.ROOT, "maps")) if f.endswith(".txt")]


def find_npc(prefix, sprite=None):
    """(map name, line index, fields) of the first NPC whose Id starts with prefix (and sprite, if given)."""
    for name in sorted(all_maps()):
        m = Map(name)
        for i, ln in enumerate(m.ents):
            f = ln.split("\t")
            if f[0] == "NPC" and ("Id=" + prefix) in ln and (sprite is None or f[1] == sprite):
                return name, i, f
    return None


def npc_tile(f):
    return int(float(f[2])) // TW + 1, (int(float(f[3])) + 8) // TW + 1


def find_place(pid):
    for name in all_maps():
        for ln in Map(name).ents:
            f = ln.split("\t")
            if f[:2] == ["Id", pid]:
                return name, int(f[2]), int(f[3])
            if ("Id=" + pid) in ln.split("\t")[-1].split():
                return name, int(float(f[2])) // TW + 1, (int(float(f[3])) + 8) // TW + 1
    return None


def swap_npc(prefix, sprite_was, sprite, extra=""):
    """The NPC (Id starting prefix) becomes sprite (its Id kept); returns (map, tile x, tile y, its Id)."""
    hit = find_npc(prefix, sprite_was) or find_npc(prefix, sprite)
    assert hit, prefix
    name, i, f = hit
    m = Map(name)
    f = m.ents[i].split("\t")
    f[1] = sprite
    opts = " ".join(o for o in f[4].split() if not o.startswith("Name=")) + (" " + extra if extra else "")
    f[4] = opts
    m.ents[i] = "\t".join(f)
    m.save()
    pid = [o[3:] for o in opts.split() if o.startswith("Id=")][0]
    x, y = npc_tile(f)
    return name, x, y, pid


# ================================================================== pictures
def book(cover, trim):
    pg = K.pg()
    s = K.surface()
    pg.draw.rect(s, (40, 26, 20), (6, 6, 21, 22))
    pg.draw.rect(s, cover, (7, 7, 19, 20))
    pg.draw.rect(s, (236, 226, 196), (24, 8, 2, 18))
    pg.draw.rect(s, trim, (10, 11, 11, 11), 1)
    pg.draw.circle(s, trim, (15, 16), 3, 1)
    return K.outlined(s)


def ring(gem):
    pg = K.pg()
    s = K.surface()
    pg.draw.ellipse(s, (150, 110, 30), (8, 12, 16, 14), 3)
    pg.draw.ellipse(s, (240, 200, 90), (9, 13, 14, 12), 1)
    pg.draw.circle(s, gem, (16, 11), 4)
    pg.draw.circle(s, (255, 240, 200), (15, 10), 1)
    return K.outlined(s)


def seal():
    pg = K.pg()
    s = K.surface()
    pg.draw.circle(s, (120, 90, 30), (16, 16), 10)
    pg.draw.circle(s, (220, 180, 70), (16, 16), 8)
    pg.draw.polygon(s, (170, 40, 40), [(16, 9), (20, 16), (16, 23), (12, 16)])       # a sword's point, on gold
    pg.draw.line(s, (250, 230, 160), (16, 10), (16, 22))
    return K.outlined(s)


def scroll_letter(seal_col):
    pg = K.pg()
    s = K.surface()
    pg.draw.rect(s, (236, 226, 196), (7, 6, 18, 22))
    pg.draw.rect(s, (200, 186, 150), (7, 6, 18, 3))
    for y in (12, 15, 18):
        pg.draw.line(s, (150, 130, 96), (10, y), (22, y))
    pg.draw.circle(s, seal_col, (16, 23), 4)
    return K.outlined(s)


def recolour(img, fn):
    out = img.copy()
    w_, h_ = img.get_size()
    for y in range(h_):
        for x in range(w_):
            r, g, b, a = img.get_at((x, y))
            if a:
                out.set_at((x, y), fn(r, g, b) + (a,))
    return out


def drake(img):
    """A drake of Dragon Island: a green dragon, three quarters of the dragon's size."""
    pg = K.pg()
    w_, h_ = img.get_size()
    small = pg.transform.scale(img, (w_ * 3 // 4, h_ * 3 // 4))
    return recolour(small, lambda r, g, b: (int(g * 0.5), min(255, int(r * 0.85)), int(b * 0.5)))


def lectern(with_book):
    pg = K.pg()
    s = K.surface()
    pg.draw.rect(s, (190, 160, 110), (12, 16, 8, 13))
    pg.draw.rect(s, (160, 130, 84), (8, 28, 16, 3))
    pg.draw.polygon(s, (200, 170, 120), [(5, 16), (27, 12), (27, 17), (5, 21)])
    if with_book:
        pg.draw.polygon(s, (90, 40, 120), [(8, 14), (24, 11), (24, 15), (8, 18)])
        pg.draw.line(s, (230, 200, 90), (16, 12), (16, 17))
    return K.outlined(s)


def sword_in_stone(with_sword):
    pg = K.pg()
    s = K.surface()
    pg.draw.ellipse(s, (110, 106, 100), (4, 18, 24, 12))
    pg.draw.ellipse(s, (150, 146, 140), (6, 18, 20, 8))
    if with_sword:
        pg.draw.rect(s, (220, 230, 240), (15, 4, 3, 16))
        pg.draw.line(s, (255, 255, 255), (15, 4), (15, 18))
        pg.draw.rect(s, (220, 180, 60), (11, 3, 11, 2))
        pg.draw.rect(s, (130, 60, 30), (15, 0, 3, 3))
    else:
        pg.draw.line(s, (40, 36, 34), (16, 20), (17, 22))
    return K.outlined(s)


def sand_mound():
    pg = K.pg()
    s = K.surface()
    pg.draw.ellipse(s, (214, 190, 130), (2, 10, 28, 18))
    pg.draw.ellipse(s, (232, 210, 152), (5, 11, 20, 10))
    pg.draw.rect(s, (170, 150, 110), (9, 8, 14, 4))                 # a lintel's corner, sticking out
    pg.draw.rect(s, (130, 110, 80), (9, 11, 14, 1))
    return s


def draw_pictures():
    staff = K.load("Entities", "Oak_Staff")
    sword = K.load("Entities", "Steel_Sword")
    for name, img in (
            ("Parliament_Letter", scroll_letter((150, 20, 40))), ("Mayors_Pass", scroll_letter((40, 80, 160))),
            ("Archivists_Attestation", scroll_letter((60, 120, 60))),
            ("Chancellors_Warrant", scroll_letter((200, 160, 40))),
            ("Grimoire_of_Unbinding", book((80, 36, 110), (230, 200, 90))),
            ("Ember_Ring", ring((240, 90, 30))), ("Valour_Seal", seal()),
            ("Solar_Key", K.outlined(K.load("Entities", "Lair_Key"))),
            ("Staff_of_Estforlan", recolour(staff, lambda r, g, b: (min(255, int(r * 1.1 + 40)), min(255, int(g * 1.0 + 30)),
                                                                   min(255, int(b * 0.6 + 90))))),
            ("Sword_of_Valour", recolour(sword, lambda r, g, b: (min(255, int(r * 1.05 + 25)), min(255, int(g * 1.0 + 20)),
                                                                min(255, int(b * 0.7 + 10))))),
            ("Grimoire_Lectern", lectern(True)), ("Empty_Lectern", lectern(False)),
            ("Sword_In_Stone", sword_in_stone(True)), ("Empty_Stone", sword_in_stone(False)),
            ("Drake", drake(K.load("Entities", "Dragon")))):
        K.save("Entities", name, img)
    for d in "28":
        for f in "abc":
            K.save("Walk", "Drake%s%s" % (d, f), drake(K.load("Walk", "Dragon%s%s" % (d, f))))
    K.save("Tiles", "Sand_Mound001", sand_mound())
    K.copy_sprite("Tiles", "Stairs002", "Library_Stairs001")
    K.copy_sprite("Tiles", "Stairs001", "Library_Steps001")
    # the tomb guardian's walking frames (build_people drew it), and the new weapons worn
    import build_walk as BWK
    import build_worn as BW
    import sprite_kit as SK
    frames, _ = BWK.build()["Tomb_Guardian"]
    for key, im in frames.items():
        SK.save("Walk", "Tomb_Guardian" + key, im)
    for item, slot in (("Sword_of_Valour", "Weapon"), ("Staff_of_Estforlan", "Weapon")):
        fr = BW.worn_frames(item, slot)
        for key, im in (fr or {}).items():
            SK.save("Worn", "Worn_%s%s" % (item, key), im)
    print("Pictures: letters, the grimoire, the ring, the seals, the staff, the sword, the drake, the lectern, the "
          "stone, the mound")


# ================================================================== data
def data():
    E = K.ENTS
    K.people_sections()
    items = [
        ("Parliament_Letter", "The Parliament's letter, sealed in crimson, for the Mayor of Ashford.", ""),
        ("Mayors_Pass", "The Mayor of Ashford's pass, sealed in blue: the road east is yours.", ""),
        ("Archivists_Attestation", "The Royal Archivist's word, in green wax: the amulet is the true seal of "
         "succession.", ""),
        ("Chancellors_Warrant", "The Lord Chancellor's warrant, in gold wax: let the bearer see the King.", ""),
        ("Grimoire_of_Unbinding", "The Grimoire of Unbinding: the spell that undoes what magic has bound.", ""),
        ("Solar_Key", "The key to the King's solar, at the top of the keep.", ""),
        ("Valour_Seal", "A Valour Seal: gold, a sword's point in red. A drake carried it.", ""),
    ]
    for name, info, _ in items:
        K.section(E, name, [("Type", "MapItem"), ("Use.Words", "Examine"), ("Examine.Info", info),
                            ("Stackable", "3" if name == "Valour_Seal" else "1"), ("Droppable", "0"), ("Value", "0")])
    K.section(E, "Ember_Ring", [("Type", "MapItem"), ("Examine.Info", "The Ember Ring: a ruby that glows like a "
                                                                      "coal. Warm to the touch."),
                                ("Slot", "Ring"), ("Magic", "2"), ("Defence", "1"), ("Droppable", "0"), ("Value", "0")])
    K.section(E, "Staff_of_Estforlan", [("Type", "MapItem"), ("Examine.Info", "The Staff of Estforlan, the kings' staff: "
                                        "gold and blue, warm with magic."), ("Slot", "Weapon"), ("Attack", "4"),
                                        ("Magic", "8"), ("Droppable", "0"), ("Value", "0"), ("Durability", "600")])
    K.section(E, "Sword_of_Valour", [("Type", "MapItem"), ("Examine.Info", "The Sword of Valour. Its edge hums. Only it "
                                     "can reach a dragon's heart."), ("Slot", "Weapon"), ("Attack", "14"),
                                     ("Defence", "2"), ("Droppable", "0"), ("Value", "0"), ("Durability", "900"),
                                     ("Requires", "Strength 10")])
    objects = [
        ("Grimoire_Lectern", "Take,Examine", "A stone lectern. On it, a book bound in violet: the Grimoire."),
        ("Empty_Lectern", "Examine", "A stone lectern, bare."),
        ("Sword_In_Stone", "Draw,Examine", "A sword, sunk to the hilt in a stone. Its edge hums."),
        ("Empty_Stone", "Examine", "The stone, a sword's slot in it, empty."),
    ]
    for name, words, info in objects:
        K.section(E, name, [("Type", "StaticObject"), ("Use.Words", words), ("Examine.Info", info), ("Solid", "1")])
    K.section(E, "Drake", [("Type", "NPC"), ("Attitude", "Bad"), ("Use.Words", "Attack,Examine"),
                           ("Examine.Info", "A drake of Dragon Island: green scales, a hot temper."),
                           ("Hitpoints", "70"), ("Attack.Speed", "1.3"), ("Strength", "7"), ("Defence", "8"),
                           ("Aggro.Range", "150"), ("Weapon.Range", "120"), ("Movement.Speed", "1.8"),
                           ("Aggressive", "1"), ("Respawn", "240"), ("Drops", "Bones,1-1,100 Gold_Coin(s),10-25,80"),
                           ("Roam.Radius", "4"), ("Chase.Radius", "5"), ("Walk.Speed", "0.5"), ("Pause", "2-6"),
                           ("Missile", "Dragon_Fire_Missile"), ("Missile.Impact", "Fire_Burst"),
                           ("Missile.Sound", "SpellFire"), ("Kill.Sound", "Dragon"), ("On.Hit", "Burn 20")])
    K.section(E, "Tomb_Guardian", [("Type", "NPC"), ("Attitude", "Bad"), ("Use.Words", "Attack,Examine"),
                                   ("Examine.Info", "A guardian of the buried library, wrapped in old linen."),
                                   ("Hitpoints", "45"), ("Attack.Speed", "1.3"), ("Strength", "6"), ("Defence", "6"),
                                   ("Aggro.Range", "110"), ("Movement.Speed", "1.2"), ("Aggressive", "1"),
                                   ("Respawn", "300"), ("Drops", "Bones,1-1,100 Gold_Coin(s),5-15,60"),
                                   ("Roam.Radius", "2"), ("Chase.Radius", "4"), ("Walk.Speed", "0.4"),
                                   ("Pause", "2-6"), ("Kill.Sound", "Undead")])
    K.section(E, "Valour_Guardian", [("Hitpoints", "160"), ("Attack.Speed", "1.3"), ("Strength", "10"),
                                     ("Defence", "11"), ("Aggro.Range", "120"), ("Movement.Speed", "1.6"),
                                     ("Aggressive", "1"), ("Respawn", "300"), ("Kill.Sound", "Undead"),
                                     ("Use.Words", "Talk to,Attack,Examine")])
    K.copy_tile("Sand_Mound001", "Sand001", Layer="Decor", Use_Words="Dig,Examine", Show_Name="1",
                Examine_Info="A mound of sand, the corner of a carved stone lintel sticking out of it.")
    K.copy_tile("Library_Stairs001", "Stairs002", Use_Words="Climb Down,Examine",
                Examine_Info="Stone steps, down into the dark under the sand.")
    K.copy_tile("Library_Steps001", "Stairs001", Use_Words="Climb Up,Examine", Examine_Info="Steps up, to the desert.")
    for t, rgb in (("Sand_Mound001", (214, 190, 130)), ("Library_Stairs001", (255, 0, 0)), ("Library_Steps001", (255, 0, 0))):
        K.minimap_colour(t, rgb)
    print("Data: the story's items, the drake, the tomb guardian, the Valour guardian, the lectern and the stone")


# ================================================================== the places
def solar():
    """The King's solar, at the top of the keep (2,4,1): its stairs up from the keep's hall, locked."""
    keep = Map("2,4,0")
    stx, sty = 19, 6
    lock = "Lock\t%d\t%d\t$Item.Solar_Key>=1 or $Attr.StaffQuest>=2\tThe stair door to the King's solar is locked." % (
        stx, sty)
    if keep.tile(stx, sty) != "Stairs001" or lock not in keep.ents:
        keep.set(stx, sty, tile="Stairs001", decor="")
        keep.ents = [ln for ln in keep.ents if not ln.startswith("Lock\t%d\t%d\t" % (stx, sty))] + [lock]
        keep.save()
    if K.map_exists("2,4,1") and Map("2,4,1").tile(18, 3) == "Fireplace001":
        return
    up = Map("2,4,1", new=True)
    x1, y1, x2, y2 = 14, 3, 22, 9
    for y in range(y1, y2 + 1):
        for x in range(x1, x2 + 1):
            edge = x in (x1, x2) or y in (y1, y2)
            up.put(x, y, "Stone_Wall001" if edge else "Tile001", {})
    up.set(stx, sty, tile="Stairs002")
    up.set(18, y1, tile="Fireplace001")                          # (the hearth, in the back wall)
    for (x, y), d in {(15, 4): "Bookshelf001", (21, 4): "Banner001",
                      (16, 8): "Potted_Plant002", (17, 6): "Table001"}.items():
        up.set(x, y, decor=d)
    up.set(15, 7, decor="Bed001")
    up.set(15, 8, decor="Bed002")
    up.ents = []
    K.place_id(up, "Kings_Solar", 18, 7)
    up.save()
    print("2,4,1: the King's solar, up a locked stair from the keep's hall")


def library():
    """The buried library of the sun priests (1,9,-1), under a mound in the desert north of Dunerest (1,9,0)."""
    top = Map("1,9,0")
    if not K.has_id(top, "Buried_Library"):
        best = None
        for y in range(4, 18):
            for x in range(4, 22):
                if top.tile(x, y) == "Sand001" and not top.decor(x, y) and top.tile(x, y + 1) == "Sand001":
                    d = abs(x - 13) + abs(y - 10)
                    if best is None or d < best[0]:
                        best = (d, x, y)
        _, mx_, my_ = best
        top.set(mx_, my_, decor="Sand_Mound001")
        K.place_id(top, "Buried_Library", mx_, my_)
        top.save()
    if K.map_exists("1,9,-1"):
        return
    pl = [ln.split("\t") for ln in top.ents if ln.startswith("Id\tBuried_Library\t")][0]
    mx_, my_ = int(pl[2]), int(pl[3])
    lib = Map("1,9,-1", new=True)
    x1, y1, x2, y2 = 6, 4, 20, 17
    for y in range(y1, y2 + 1):
        for x in range(x1, x2 + 1):
            edge = x in (x1, x2) or y in (y1, y2)
            lib.put(x, y, "Sandstone001" if edge else "Sand001", {})
    for y in range(y1 + 2, y2 - 1, 3):                            # rows of shelves, half buried
        for x in range(x1 + 2, x2 - 1):
            if x not in (13, 14):
                lib.set(x, y, decor="Bookshelf001")
    for x, y in ((x1 + 1, y1 + 1), (x2 - 1, y1 + 1), (x1 + 1, y2 - 1), (x2 - 1, y2 - 1)):
        lib.set(x, y, decor="Pillar001")
    sx, sy = 13, y2 - 1                                           # the steps up (beside the mound above, by script)
    lib.set(sx, sy, tile="Library_Steps001")
    lib.ents = []                                                 # (its lectern and guardians: its entry script)
    K.place_id(lib, "Library_Steps", sx, sy)
    K.place_id(lib, "Library_Lectern", 14, y1 + 1)
    lib.save()
    print("1,9,-1: the buried library, under a mound in the desert (1,9,0 %d,%d)" % (mx_, my_))


def rooks_pier():
    m = Map("9,8,0")
    if K.has_id(m, "Rooks_Pier"):
        return
    for x in range(13, 17):
        m.set(x, 9, tile="Plank001", decor="")
    m.ents += [obj_line("StaticObject", "Boat001", 16, 9, dy=-16),
               obj_line("NPC", "Sea_Captain", 12, 9, "Attitude=Good Stand=1 Face=E Id=Captain_Rook Name=Captain_Rook",
                        -8)]
    K.place_id(m, "Rooks_Pier", 12, 10)
    m.save()
    print("9,8,0: Captain Rook's pier, on the shore east of Ravensgate")


def dragon_island():
    """Dragon Island (8,10,0): far out in the south-eastern sea. Only Captain Rook sails there."""
    if K.map_exists("8,10,0"):
        return
    rng = random.Random(1588)
    m = Map("8,10,0", new=True)
    land = set()
    for y in range(1, YT + 1):
        for x in range(1, XT + 1):
            r = ((x - 13) / 10.5) ** 2 + ((y - 11) / 8.5) ** 2
            land.add((x, y)) if r <= 1 - 0.06 * rng.random() else None
    for y in range(1, YT + 1):
        for x in range(1, XT + 1):
            if (x, y) not in land:
                m.put(x, y, "Water001", {})
            elif any((x + i, y + j) not in land for i in (-1, 0, 1) for j in (-1, 0, 1)):
                m.put(x, y, "Sand001", {})
            else:
                m.put(x, y, rng.choice(("Grass001", "Grass001", "Ash001", "Grass001")), {})
    for _ in range(26):
        x, y = rng.randint(4, 22), rng.randint(9, 19)
        if m.tile(x, y) in ("Grass001", "Ash001") and not (10 <= x <= 16 and y >= 15):
            m.set(x, y, decor=rng.choice(("Rock002", "Dead_Tree001", "Tree001", "Dragon_Skull001", "Basalt_Rock001")))
    # the Temple of Valour: stone, on the island's north, its door shut until the seals open it
    K.building(m, 9, 3, 17, 9, 13, wall="Stone_Wall001", roof="Slate", windows=(11, 15), floor="Marble001")
    for x in (10, 16):
        for y in (5, 7):
            m.set(x, y, decor="Pillar001")
    m.set(12, 4, decor="Banner001")
    m.set(14, 4, decor="Banner001")
    for x in range(13, 14):                                       # (a path from the temple to the landing)
        for y in range(10, 19):
            m.set(x, y, tile="Dirt001", decor="")
    m.ents = ["Lock\t13\t9\t$Attr.DragonIsleQuest>=2\tThe temple's door is sealed: three hollows in it, the shape of "
              "seals.",
              "StaticObject\tBoat001\t%d\t%d" % ((13 - 1) * TW, (20 - 1) * TW - 16),
              obj_line("NPC", "Sea_Captain", 14, 18, "Attitude=Good Stand=1 Face=S Id=Captain_Rook_Island "
                                                     "Name=Captain_Rook", -8),
              obj_line("NPC", "Valour_Guardian", 13, 6, "Attitude=Good Stand=1 Face=S Id=Valour_Guardian_Knight", -8),
              "Trigger\tTemple Door\t13\t10"]                    # (the stone and its sword: the entry script)
    for x, y in ((6, 12), (19, 11), (8, 16), (18, 16), (11, 13)):
        m.ents.append(obj_line("NPC", "Drake", x, y, "Attitude=Bad Zone=%d,%d,%d,%d" % (x - 3, y - 2, x + 3, y + 2), -16))
    K.place_id(m, "Dragon_Island_Landing", 13, 18)
    K.place_id(m, "Temple_of_Valour", 13, 10)
    m.save()
    amb = os.path.join(K.DATA, "Ambient.ini")
    ini.write("Maps", "8,10,0", "Waves", amb)
    K.place_label("Places", "Dragon Island", "Dragon_Island_Landing")
    print("Made maps\\8,10,0.txt: Dragon Island, its drakes and the Temple of Valour")


def court():
    """The King's Castle is the Wizards' Court: King Tyron's throne is the court's, a magister on it; the court wizard in
    the tower is Bert."""
    m = Map("4,4,0")
    changed = False
    ents = []
    for ln in m.ents:
        f = ln.split("\t")
        if f[:2] == ["NPC", "King_Tyron"]:
            ln = "\t".join([f[0], "Wizard", f[2], f[3], "Attitude=Good Stand=1 Id=Court_Magister Name=Magister_Quill"])
            changed = True
        if f[0] == "Lock" and "King Tyron" in ln:
            ln = ln.replace("Only a hero of King Tyron may enter.", "Only the Steward's friends may enter.")
            changed = True
        ents.append(ln)
    if changed:
        m.ents = ents
        m.save()
    t = Map("4,4,1")
    lines = [ln.replace("NPC\tWizard\t", "NPC\tBert\t") for ln in t.ents]
    lines = [ln + " Name=Bert" if ln.startswith("NPC\tBert\t") and "Name=" not in ln else ln for ln in lines]
    if lines != t.ents:
        t.ents = lines
        t.save()
        print("4,4,0 and 4,4,1: the Wizards' Court; its great wizard is Bert")


def southport_guard():
    m = Map("1,3,0")
    if K.has_id(m, "Southport_Port"):
        return
    pl = find_place("Southport_Pier")
    x, y = pl[1] + 2, pl[2] + 3
    m.ents.append(obj_line("NPC", "Port_Guard", x, y, "Attitude=Good Stand=1 Face=W Id=Southport_Port_Guard "
                                                      "Name=Sergeant_Brand", -8))
    K.place_id(m, "Southport_Port", x, y + 1)
    m.save()


def southport_hall():
    """Southport's City Hall, where the Speaker sits, is Estforlan's Parliament while Galaith is lost."""
    name, _, f = find_npc("Southport_Speaker", "Speaker")
    x, y = npc_tile(f)
    m = Map(name)
    if not K.has_id(m, "Southport_City_Hall"):
        K.place_id(m, "Southport_City_Hall", x, y)
        m.save()
    for f in os.listdir(K.SCRIPTS):
        if f.startswith("Read Southport_Notice_"):
            path = os.path.join(K.SCRIPTS, f)
            text = open(path, "rb").read()
            new = text.replace(b"CITY HALL\\The seat of the city's council.",
                               b"CITY HALL\\The seat of Estforlan's Parliament while Galaith is lost.")
            if new != text:
                open(path, "wb").write(new)


def steward():
    m = Map("2,4,0")
    if any("Id=Keep_Steward" in ln for ln in m.ents):
        return
    m.ents.append(obj_line("NPC", "Steward", 15, 12, "Attitude=Good Stand=1 Face=S Id=Keep_Steward Name=Steward_Aldric",
                           -8))
    K.place_id(m, "Keep_Steward_Post", 15, 13)
    m.save()


def dunerest_scholar():
    sq = find_place("Dunerest_Square")
    m = Map(sq[0])
    if any("Id=Dunerest_Scholar" in ln for ln in m.ents):
        return
    m.ents.append(obj_line("NPC", "Scholar", sq[1] + 2, sq[2], "Attitude=Good Stand=1 Face=S Id=Dunerest_Scholar "
                                                              "Name=Yusra", -8))
    m.save()


def galaith_people():
    """In Galaith's palace, Parliament and City Hall: the King, his captain and guards, the Chancellor, the Archivist."""
    p = Map("12,5,0")
    if not any("Id=Rupert_On_Throne" in ln for ln in p.ents):
        door, front = (13, 13), (13, 14)
        p.ents += [obj_line("NPC", "King_Rupert", 14, 8, "Attitude=Good Stand=1 Face=S Id=Rupert_On_Throne", -8),
                   obj_line("NPC", "Royal_Guard", 12, 12, "Attitude=Good Stand=1 Face=S Id=Palace_Guard_1", -8),
                   obj_line("NPC", "Royal_Guard", 14, 12, "Attitude=Good Stand=1 Face=S Id=Palace_Guard_2", -8),
                   obj_line("NPC", "Guard_Captain", 15, 14, "Attitude=Good Stand=1 Face=W Id=Palace_Captain "
                                                            "Name=Captain_Hart", -8),
                   "Lock\t%d\t%d\t$Attr.GuardQuest>=5 or $Attr.KingQuest>=1\tThe Royal Guard bar the palace door." % door]
        K.place_id(p, "Palace_Gate", *front)
        K.place_id(p, "Throne_Room", 13, 8)
        p.save()
    old = "Lock\t13\t13\t$Attr.GuardQuest>=4 "                    # (it opened before the captain saw the warrant)
    if any(ln.startswith(old) for ln in p.ents):
        p.ents = [ln.replace("GuardQuest>=4", "GuardQuest>=5") if ln.startswith(old) else ln for ln in p.ents]
        p.save()
    if not find_npc("Galaith_Speaker", "Chancellor"):
        name, x, y, pid = swap_npc("Galaith_Speaker", "Speaker", "Chancellor", "Name=Lord_Chancellor_Vane")
        mm = Map(name)
        K.place_id(mm, "Galaith_Parliament", x, y + 5)
        mm.save()
        open_hall("Galaith", "City Hall", "Archivist", "Galaith_City_Hall", "Name=Archivist_Sefton")


def open_hall(key, title, sprite, place, extra):
    """The clerk in key's hall titled title becomes sprite; place names its door. (The hall: its notice says so.)"""
    for f in os.listdir(K.SCRIPTS):
        if f.startswith("Read %s_Notice_" % key):
            text = open(os.path.join(K.SCRIPTS, f), "rb").read().decode("cp1252")
            if "\t%s\\" % title.upper() not in text:
                continue
            pid = f[5:-4]
            hit = find_place(pid)
            if hit is None:
                continue
            name, nx, ny = hit
            m = Map(name)
            best = None
            for i, ln in enumerate(m.ents):
                fl = ln.split("\t")
                if fl[0] == "NPC" and fl[1] in ("Clerk", sprite) and ("Id=%s_Clerk" % key) in ln:
                    x, y = npc_tile(fl)
                    d = abs(x - nx) + abs(y - ny)
                    if best is None or d < best[0]:
                        best = (d, i, x, y)
            _, i, x, y = best
            fl = m.ents[i].split("\t")
            fl[1] = sprite
            fl[4] = " ".join(o for o in fl[4].split() if not o.startswith("Name=")) + " " + extra
            m.ents[i] = "\t".join(fl)
            K.place_id(m, place, nx, ny)
            m.save()
            return [o[3:] for o in fl[4].split() if o.startswith("Id=")][0]
    raise AssertionError("no %s in %s" % (title, key))


def places():
    court()
    southport_guard()
    southport_hall()
    steward()
    dunerest_scholar()
    if not find_npc("Ashford_Clerk", "Mayor"):
        open_hall("Ashford", "Town Hall", "Mayor", "Ashford_Town_Hall", "Name=Mayor_Hollis")
    solar()
    library()
    rooks_pier()
    dragon_island()
    galaith_people()
    w5 = Map("5,3,0")                                            # Wardhaven opens when the dragon is dead
    w5.ents = [ln.replace("$Attr.DragonQuest>=4", "$Attr.GalaithQuest>=2") for ln in w5.ents]
    w5.save()


# ================================================================== the quests
def quests():
    Q = K.QUESTS
    for old in ("The Ashen Hand", "The Ashen Omens", "The Dragon of Ashpeak", "King's Hobgoblin Hunt"):
        K.remove_section(Q, old)
    text = open(Q, "rb").read().decode("cp1252")
    text = text.replace("Requires.Quests=King's Hobgoblin Hunt", "Requires.Quests=The Steward's Hunt")
    open(Q, "wb").write(text.encode("cp1252"))
    ini.forget(Q)
    K.quest("The Temporary Capital", "Port_Guard", "ParliamentQuest", {
        0: "Speak to the city guard at Southport's port.",
        1: "Go to Southport's City Hall, where Estforlan's Parliament sits until Galaith opens again.",
    }, 2, markers={0: "Southport_Port", 1: "Southport_City_Hall"}, chapter=5, requires="Passage to the Mainland",
        marker0="Southport_Port")
    K.quest("The Ashford Road", "Mayor", "AshfordQuest", {
        0: "Take the Parliament's letter to the Mayor of Ashford, in Ashford's Town Hall.",
        1: "Goblins raid the farms east of Ashford. Drive them off: wait for them at the farm's crossroads.",
        2: "Tell the Mayor the goblins are beaten.",
    }, 3, markers={0: "Ashford_Town_Hall", 1: "Farmlands_Crossroads", 2: "Ashford_Town_Hall"}, chapter=6,
        requires="The Temporary Capital", marker0="Ashford_Town_Hall")
    K.quest("The Steward's Hunt", "Steward", "HobgoblinQuest", {
        0: "Show the Mayor's pass to the King's Steward, at King Rupert's Keep, south of Ashford.",
        1: "Slay five hobgoblins ($HobgoblinsSlain of 5) in the old iron mine, the mine depths or the warren, then "
           "return to the Steward.",
    }, 2, markers={0: "Keep_Steward_Post", 1: "Iron_Mine_Entrance"}, chapter=7, requires="The Ashford Road",
        marker0="Keep_Steward_Post")
    K.quest("Bert's Three Treasures", "Bert", "BertQuest", {
        0: "Find Bert, the great wizard, at the top of the Wizards' Court's tower, on the Royal Isle.",
        1: "Bring Bert the Staff of Estforlan, the Grimoire of Unbinding and the Ember Ring.",
    }, 2, markers={0: "Court_Wizard", 1: "Court_Wizard"}, chapter=8, requires="The Steward's Hunt",
        marker0="Court_Wizard")
    K.quest("The Staff of Estforlan", "Steward", "StaffQuest", {
        0: "Ask the Steward at King Rupert's Keep about the King's staff.",
        1: "Climb to the King's solar at the top of the keep (the stair in the keep's hall: the Steward's key) and take "
           "the Staff of Estforlan.",
    }, 2, markers={0: "Keep_Steward_Post", 1: "Kings_Solar"}, chapter=9,
        requires="The Steward's Hunt", marker0="Keep_Steward_Post")
    K.quest("The Sunken Grimoire", "Scholar", "GrimoireQuest", {
        0: "Ask the scholar Yusra, in Dunerest, about the Grimoire of Unbinding.",
        1: "The Grimoire lies in the sun priests' buried library, in the desert north of Dunerest. Dig out its "
           "entrance (a spade).",
        2: "Take the Grimoire of Unbinding from its lectern in the buried library.",
    }, 3, markers={0: "Dunerest_Square", 1: "Buried_Library", 2: "Library_Lectern"}, chapter=10,
        requires="The Steward's Hunt", marker0="Dunerest_Square")
    K.quest("The Ember Ring", "Warden", "RingQuest", {
        0: "Ask the Warden in Emberwatch about the Ashen Priest's ring.",
        1: "The Ashen Priest wears the Ember Ring, in the Cinder Fort high in the Cinder Peaks. Take it from him.",
    }, 2, markers={0: "Emberwatch_Square", 1: "Cinder_Fort"}, chapter=11, requires="The Steward's Hunt",
        marker0="Emberwatch_Square")
    K.quest("A Ship for Dragon Island", "Sea_Captain", "ShipQuest", {
        0: "Find Captain Rook, the only captain mad enough to sail to Dragon Island, on the shore east of Ravensgate.",
        1: "Bring Captain Rook 10 planks and 20 nails to mend his hull.",
    }, 2, markers={0: "Rooks_Pier", 1: "Rooks_Pier"}, chapter=12, requires="Bert's Three Treasures",
        marker0="Rooks_Pier", level=12)
    K.quest("The Island of Dragons", "Sea_Captain", "DragonIsleQuest", {
        0: "Sail to Dragon Island with Captain Rook.",
        1: "The Temple of Valour is sealed. Take three Valour Seals from the island's drakes ($ValourSeals of 3), and "
           "open its door.",
    }, 2, markers={0: "Rooks_Pier", 1: "Temple_of_Valour"}, chapter=13, requires="A Ship for Dragon Island",
        marker0="Rooks_Pier")
    K.quest("The Sword of Valour", "Valour_Guardian", "ValourQuest", {
        0: "Enter the Temple of Valour and speak to its guardian.",
        1: "Defeat the Guardian of Valour.",
        2: "Draw the Sword of Valour from its stone.",
    }, 3, markers={0: "Temple_of_Valour", 1: "Temple_of_Valour", 2: "Temple_of_Valour"}, chapter=14,
        requires="The Island of Dragons", marker0="Temple_of_Valour")
    K.quest("The Dragon of Galaith", "Bert", "GalaithQuest", {
        0: "Go east, over the causeway from the Elderwood, to the pass of Galaith. Break the barrier with Bert's spell "
           "(use the Staff of Estforlan on it).",
        1: "Kill the dragon before Galaith's walls. Only the Sword of Valour, wielded, can reach its heart.",
    }, 2, markers={0: "Galaith_Barrier", 1: "Dragons_Field"}, chapter=15, requires="The Sword of Valour",
        marker0="Galaith_Barrier", level=16)
    K.quest("The Royal Guard", "Guard_Captain", "GuardQuest", {
        0: "Ask the captain of the Royal Guard, at the palace door, to let you see the King.",
        1: "The Lord Chancellor must give his leave. Find him in Galaith's Parliament.",
        2: "Show your mother's amulet to the Royal Archivist, in Galaith's City Hall.",
        3: "Take the Archivist's word to the Lord Chancellor, in the Parliament.",
        4: "Show the Chancellor's warrant to the captain at the palace door.",
    }, 5, markers={0: "Palace_Gate", 1: "Galaith_Parliament", 2: "Galaith_City_Hall", 3: "Galaith_Parliament",
                   4: "Palace_Gate"}, chapter=16, requires="The Dragon of Galaith", marker0="Palace_Gate")
    K.quest("The True Heir", "King_Rupert", "KingQuest", {
        0: "Go to King Rupert, in the throne room of the palace, and tell him of your mother.",
    }, 1, markers={0: "Throne_Room"}, chapter=17, requires="The Royal Guard", marker0="Throne_Room")
    print("Quests: chapters 5 to 17; The Ashen Hand, The Ashen Omens and The Dragon of Ashpeak are gone")


# ================================================================== the scripts: to the Wizards' Court
def npc_id(prefix, sprite):
    hit = find_npc(prefix, sprite)
    assert hit, prefix
    return [o[3:] for o in hit[2][4].split() if o.startswith("Id=")][0]


def southport_and_ashford():
    w("Talk to Southport_Port_Guard", [
        ("Get.Value", "ATTRIBUTE", "ParliamentQuest", V1),
        (">Conditional", "$Variable.1=0", "@chat"),
        (">Quest.Can.Start", "ParliamentQuest", "@end"),
        say("Port_Guard", "Welcome to Southport, the capital of Estforlan. For now, anyway.\\Galaith's been shut these "
                          "eighteen years: a wall of light across the pass, and a dragon behind it. So the city hall "
                          "here is the Parliament, till the barrier falls.\\Business in Galaith, you say? Then the City "
                          "Hall's where you ask. They say it was sealed the very year the Queen vanished.",
            ("I'll go to the City Hall.", "@start")),
        ("@start",),
        ("Update.Attribute", "ParliamentQuest", "=1"),
        ("Display.Message", "Yellow", "Quest started: The Temporary Capital.", "Quest"),
        ("End",),
        ("@chat",),
        say("Port_Guard", "Keep your purse close in the market, and your sword in its scabbard. Southport's a good "
                          "city, mostly.", ("Goodbye.", "@end")),
        ("@end",), ("End",),
    ])
    speaker = npc_id("Southport_Speaker", "Speaker")
    w("Talk to " + speaker, [
        ("Get.Value", "ATTRIBUTE", "ParliamentQuest", V1),
        (">Conditional", "$Variable.1=1", "@chat"),
        say("Speaker", "You want to go to Galaith? Half this Parliament wants nothing else.\\The barrier is the "
                       "dragon's: violet light across the pass, hard as glass. No sword, no ram and no spell of ours "
                       "has so much as scratched it. Only one person living might break it: Bert, the great wizard of "
                       "the Wizards' Court, on the Royal Isle.",
            ("How do I get to him?", "@road")),
        ("@road",),
        say("Speaker", "East, through Ashford and King Rupert's Keep. The road's the Mayor of Ashford's to keep, and the "
                       "causeway to the Royal Isle is the King's Steward's.\\Take the Parliament's letter to the Mayor: "
                       "it asks every friend of the crown to help you on your way.",
            ("Thank you, Madam Speaker.", "@letter")),
        ("@letter",),
        ("Give.Item", "Parliament_Letter", "1"),
        ("Update.Attribute", "ParliamentQuest", "=2"),
        ("Display.Message", "Yellow", "Quest complete: The Temporary Capital! The Speaker gave you the Parliament's "
                                      "letter for the Mayor of Ashford.", "Quest"),
        ("End",),
        ("@chat",),
        say("Speaker", "Order, order! Oh, it's you. The Parliament sits from dawn till the members fall asleep.",
            ("Goodbye.", "@end")),
        ("@end",), ("End",),
    ])
    mayor = npc_id("Ashford_Clerk", "Mayor")
    w("Talk to " + mayor, [
        ("Get.Value", "ATTRIBUTE", "AshfordQuest", V1),
        (">Conditional", "$Variable.1=0 and $Item.Parliament_Letter>=1", "@s1"),
        (">Quest.Can.Start", "AshfordQuest", "@end"),
        ("Take.Item", "Parliament_Letter", "1"),
        say("Mayor", "A letter from the Parliament? \"Every friend of the crown...\" Well, I'm a friend of the crown, "
                     "and I'd be a better one if the goblins would leave my farms alone.\\They come out of the hedges "
                     "east of town and carry off the hens. Drive them off for me, at the farm crossroads, and I'll give "
                     "you my pass for the Steward.", ("I'll deal with the goblins.", "@start")),
        ("@start",),
        ("Update.Attribute", "AshfordQuest", "=1"),
        ("Display.Message", "Yellow", "Quest started: The Ashford Road.", "Quest"),
        ("Start.Wave", "Farm_Raid"),
        ("End",),
        ("@s1",), (">Conditional", "$Variable.1=1", "@s2"),
        say("Mayor", "The goblins are still at it! The farm crossroads, east of town.", ("Send them in.", "@wave"),
            ("I'm on my way.", "@end")),
        ("@wave",), ("Start.Wave", "Farm_Raid"),
        ("End",),
        ("@s2",), (">Conditional", "$Variable.1=2", "@chat"),
        ("Update.Attribute", "AshfordQuest", "=3"),
        ("Give.Item", "Mayors_Pass", "1"),
        say("Mayor", "Beaten them, have you? Then here's my pass. The Steward at King Rupert's Keep, south of here, "
                     "will see you right.", ("Thank you, Mayor.", "@done")),
        ("@done",), ("Display.Message", "Yellow", "Quest complete: The Ashford Road!", "Quest"),
        ("End",),
        ("@chat",),
        say("Mayor", "Ashford's Town Hall: births, weddings, deeds and goblins. Mostly goblins.", ("Goodbye.", "@end")),
        ("@end",), ("End",),
    ])
    w("Farm Raid Won", [
        ("Update.Attribute", "FarmRaidsBeaten", "+1"),
        ("Display.Message", "Yellow", "The farmer waves his hat at you: \"Come back any time those goblins do!\""),
        ("Get.Value", "ATTRIBUTE", "AshfordQuest", V1),
        (">Conditional", "$Variable.1=1", "@end"),
        ("Update.Attribute", "AshfordQuest", "=2"),
        ("Display.Message", "Yellow", "The Ashford Road: tell the Mayor the goblins are beaten.", "-"),
        ("@end",), ("End",),
    ])


def keep():
    w("Talk to Keep_Steward", [
        ("Get.Value", "ATTRIBUTE", "HobgoblinQuest", V1),
        (">Conditional", "$Variable.1=0 and $Item.Mayors_Pass>=1", "@s1"),
        (">Quest.Can.Start", "HobgoblinQuest", "@end"),
        ("Take.Item", "Mayors_Pass", "1"),
        say("Steward", "The Mayor's pass. So you want the causeway to the Wizards' Court.\\I keep this keep for King "
                       "Rupert, these eighteen years, and its roads. Hobgoblins have come up from the deep into the old "
                       "iron mine, west of here. Slay five of them, and the causeway's yours.",
            ("I'll hunt them.", "@start")),
        ("@start",),
        ("Update.Attribute", "HobgoblinQuest", "=1"),
        ("Update.Attribute", "HobgoblinsSlain", "=0"),
        ("Quest.Note", "HobgoblinQuest", "Hobgoblins: in the old iron mine, the mine depths and the warren."),
        ("Quest.Note", "HobgoblinQuest", "The mine's guard only lets you in wearing body armour (the quartermaster "
                                         "here sells it)."),
        ("Display.Message", "Yellow", "Quest started: The Steward's Hunt.", "Quest"),
        ("End",),
        ("@s1",), (">Conditional", "$Variable.1=1", "@staff"),
        (">Conditional", "$Attr.HobgoblinsSlain>=5", "@hunting"),
        say("Steward", "Five hobgoblins! The King would thank you himself, if he could. Take this, and the causeway: the "
                       "Wizards' Court is the walled island east of the goblin camp. Bert will see you; I'll send word.",
            ("Thank you, Steward.", "@reward")),
        ("@reward",),
        ("Give.Item", "Gold_Coin(s)", "100"),
        ("Give.Item", "Ruby", "1"),
        ("Update.Skill", "Strength", "+1"),
        ("Update.Attribute", "HobgoblinQuest", "=2"),
        ("Quest.Note.Done", "HobgoblinQuest", "*"),
        ("Display.Message", "Yellow", "Quest complete: The Steward's Hunt! 100 gold and a ruby.", "Quest"),
        ("End",),
        ("@hunting",),
        say("Steward", "Five hobgoblins, from the old iron mine. You've $Attr.HobgoblinsSlain so far.",
            ("I'll keep at it.", "@end")),
        ("End",),
        ("@staff",), (">Conditional", "$Attr.StaffQuest=0 and $Attr.BertQuest>=1", "@staff2"),
        (">Quest.Can.Start", "StaffQuest", "@end"),
        say("Steward", "Bert wants the King's staff? It hangs in his solar, at the top of the keep, where he left it the "
                       "night he rode for Galaith.\\Nobody's been up since. The stair door is locked, and the old guard, "
                       "they say, never left their post, even dead. Here's the key. Go carefully.",
            ("I'll fetch it.", "@key")),
        ("@key",),
        ("Give.Item", "Solar_Key", "1"),
        ("Update.Attribute", "StaffQuest", "=1"),
        ("Display.Message", "Yellow", "Quest started: The Staff of Estforlan.", "Quest"),
        ("End",),
        ("@staff2",),
        say("Steward", "The keep stands, and the King's roads are open. Long may they stay so.", ("Goodbye.", "@end")),
        ("@end",), ("End",),
    ])
    w("Kill Hobgoblin", [
        ("Get.Value", "ATTRIBUTE", "HobgoblinQuest", V1),
        (">Conditional", "$Variable.1=1", "@end"),
        ("Get.Value", "ATTRIBUTE", "HobgoblinsSlain", V2),
        (">Conditional", "$Variable.2<5", "@end"),
        ("Update.Attribute", "HobgoblinsSlain", "+1"),
        ("Get.Value", "CALCULATION", "$Variable.2+1", V2),
        (">Conditional", "$Variable.2<5", "@five"),
        ("Display.Message", "Yellow", "Hobgoblins slain for the Steward: $Variable.2 of 5."),
        ("End",),
        ("@five",),
        ("Quest.Note", "HobgoblinQuest", "Return to the Steward at King Rupert's Keep."),
        ("Display.Message", "Yellow", "That's five hobgoblins! Return to the Steward at King Rupert's Keep."),
        ("@end",), ("End",),
    ])
    w("2,4,1", [                                                  # (the solar's old guard; the staff on its rack)
        ("Display.Message", "Red", "Dust, cold, and the clatter of old bones standing to attention.", "-"),
        ("Add.Entity", at(16, 5, -8), "Skeleton", "NPC", "Attitude=Bad Zone=15,4,21,8"),
        ("Add.Entity", at(20, 7, -8), "Skeleton", "NPC", "Attitude=Bad Zone=15,4,21,8"),
        ("Add.Entity", at(17, 8, -8), "Skeleton", "NPC", "Attitude=Bad Zone=15,4,21,8"),
        ("Get.Value", "ATTRIBUTE", "StaffQuest", V1),
        (">Conditional", "$Variable.1<2 and $Item.Staff_of_Estforlan<1", "@end"),
        ("Add.Entity", at(21, 5, -6), "Staff_of_Estforlan", "MapItem", "1"),
        ("@end",), ("End",),
    ])
    w("Pickup Staff_of_Estforlan", [
        (">Distance.From.Clicked.Entity", "48", "@far"),
        ("Remove.Entity", "$Object.under.Cursor.X,$Object.under.Cursor.Y", "Staff_of_Estforlan"),
        ("Give.Item", "Staff_of_Estforlan", "1"),
        ("Play.Sound", "Quest"),
        ("Display.Message", "Yellow", "The Staff of Estforlan: gold and blue, and warm in your hand.", "-"),
        ("Get.Value", "ATTRIBUTE", "StaffQuest", V1),
        (">Conditional", "$Variable.1<2", "@end"),
        ("Update.Attribute", "StaffQuest", "=2"),
        ("Display.Message", "Yellow", "Quest complete: The Staff of Estforlan! Take it to Bert.", "Quest"),
        ("@end",), ("End",),
    ] + FAR)


def bert():
    w("Talk to Bert", [
        ("Get.Value", "ATTRIBUTE", "WizardGift", V1),
        (">Conditional", "$Variable.1=0", "@quest"),
        say("Bert", "A new face! Every adventurer should know a little magic. Take these.\\Right-click a scroll and "
                    "choose Cast, or use it on a monster. Reading it uses it up.", ("Thank you!", "@gift")),
        ("@gift",),
        ("Give.Item", "Fire_Bolt_Scroll", "3"),
        ("Give.Item", "Healing_Scroll", "2"),
        ("Update.Attribute", "WizardGift", "=1"),
        ("@quest",),
        ("Get.Value", "ATTRIBUTE", "BertQuest", V1),
        (">Conditional", "$Variable.1=0 and $Attr.HobgoblinQuest>=2", "@s1"),
        (">Quest.Can.Start", "BertQuest", "@menu"),
        say("Bert", "The Steward's friend! Come in, come in, mind the cat. Not a real cat. Well.\\You want the barrier "
                    "down. Everyone wants the barrier down. I can do it: Bert, greatest wizard of the age, at your "
                    "service. But even I need the proper things.",
            ("What things?", "@things")),
        ("@things",),
        say("Bert", "Three. The Staff of Estforlan: the King's own, in his solar at the top of his keep. The Grimoire of "
                    "Unbinding: buried with the sun priests' library, in the desert outside Dunerest. And the Ember "
                    "Ring, which the Ashen Priest wears in his fort above Emberwatch.\\Bring me all three, and we'll "
                    "see about that barrier.", ("I'll bring them.", "@start")),
        ("@start",),
        ("Update.Attribute", "BertQuest", "=1"),
        ("Display.Message", "Yellow", "Quest started: Bert's Three Treasures.", "Quest"),
        ("End",),
        ("@s1",), (">Conditional", "$Variable.1=1", "@menu"),
        (">Conditional", "$Item.Staff_of_Estforlan>=1 and $Item.Grimoire_of_Unbinding>=1 and $Item.Ember_Ring>=1",
         "@missing"),
        ("Goto.Script", "Bert's Confession"),
        ("@missing",),
        say("Bert", "The staff from the King's keep, the grimoire from under the desert, the ring from the Ashen Priest. "
                    "All three, mind.", ("Something else.", "@menu"), ("On my way.", "@end")),
        ("End",),
        ("@menu",),
        say("Bert", "I study the arcane arts up here, far from the noise of the court.\\I sell spell scrolls, and I can "
                    "teach you to write your own. Or I can send you anywhere I've been.",
            ("Show me your scrolls.", "@shop"), ("Teach me to write scrolls.", "@craft"),
            ("Can you teleport me?", "@away"), ("Goodbye.", "@end")),
        ("@shop",), ("Display.Item.Rack", "SPECIFIC", "Bert", "SHOP-Wizard", "@end"),
        ("End",),
        ("@craft",), ("Display.Item.Rack", "GENERAL", "Bert", "CRAFT-Scrolls", "@end"),
        ("End",),
        ("@away",),
        say("Bert", "Where to?", ("To the Isle.", "@isle"), ("To Southport.", "@southport"), ("Nowhere, thanks.", "@end")),
        ("@isle",), ("Play.Sound", "Teleporter"), ("Display.Message", "Yellow", "Bert waves his hands, and the world "
                                                                               "spins..."),
        ("Teleport", "Isle_Landing", "-"),
        ("End",),
        ("@southport",), ("Play.Sound", "Teleporter"), ("Display.Message", "Yellow", "Bert waves his hands, and the "
                                                                                    "world spins..."),
        ("Teleport", "Southport_Landing", "-"),
        ("End",),
        ("@end",), ("End",),
    ])
    w("Bert's Confession", [
        ("Take.Item", "Grimoire_of_Unbinding", "1"),
        ("Take.Item", "Ember_Ring", "1"),
        ("Take.Item", "Staff_of_Estforlan", "1"),
        say("Bert", "The staff! The grimoire! And the ring... oh, look at it. Look at that glow.\\He slips the Ember Ring "
                    "on his finger and holds it up against his sleeve.\\Purple and ember. I knew it. It goes with the "
                    "robe perfectly.", ("And the spell?", "@spell")),
        ("@spell",),
        say("Bert", "Ah. Yes. Well. Between ourselves, the spell doesn't need the ring. Never did. I wanted it because "
                    "it suits me, and because the Ashen Priest is an insufferable windbag who deserved to lose it.\\The "
                    "grimoire's what matters. Listen, and remember: these are the words of Unbinding.",
            ("I'm listening.", "@words")),
        ("@words",),
        ("Play.Sound", "SpellCast"),
        ("Display.Message", "Cyan", "Bert reads from the grimoire. The words slide into your memory and stay there, "
                                    "humming.", "-"),
        ("Update.Attribute", "BarrierSpell", "=1"),
        ("Give.Item", "Staff_of_Estforlan", "1"),
        say("Bert", "Take the staff back: it's the King's, and the spell needs a king's staff. Hold it to the barrier and "
                    "say the words, and it will fall.\\But hear me. Behind the barrier waits the dragon, and no blade "
                    "made by men will kill it. Only the Sword of Valour, driven into its heart. It lies on Dragon "
                    "Island, far out in the eastern sea. Captain Rook, by Ravensgate, is the only sailor mad enough to "
                    "take you there.", ("Thank you, Bert.", "@done")),
        ("@done",),
        ("Update.Attribute", "BertQuest", "=2"),
        ("Display.Message", "Yellow", "Quest complete: Bert's Three Treasures! You know the spell of Unbinding.",
         "Quest"),
        ("End",),
    ])
    w("Talk to Court_Magister", [
        say("Wizard", "The Wizards' Court is in session. Mostly we argue about hats.", ("Goodbye.", "@end")),
        ("@end",), ("End",),
    ])
    w("Talk to Wizard", [
        say("Wizard", "Magic is a matter of patience, and of not setting your beard on fire.", ("Goodbye.", "@end")),
        ("@end",), ("End",),
    ])


# ================================================================== the grimoire and the ring
def grimoire_and_ring():
    top = Map("1,9,0")
    pl = [ln.split("\t") for ln in top.ents if ln.startswith("Id\tBuried_Library\t")][0]
    mx_, my_ = int(pl[2]), int(pl[3])
    w("Talk to Dunerest_Scholar", [
        ("Get.Value", "ATTRIBUTE", "GrimoireQuest", V1),
        (">Conditional", "$Variable.1=0 and $Attr.BertQuest>=1", "@chat"),
        (">Quest.Can.Start", "GrimoireQuest", "@end"),
        say("Scholar", "The Grimoire of Unbinding? You're the first in thirty years to ask me that.\\The sun priests "
                       "kept their library under the desert north of here, and the sand took it. I've found the corner "
                       "of its lintel, sticking out of a dune. Bring a spade and dig it out, and you'll find the steps. "
                       "Its guardians, mind, never stopped guarding.", ("I'll dig it out.", "@start")),
        ("@start",),
        ("Update.Attribute", "GrimoireQuest", "=1"),
        ("Display.Message", "Yellow", "Quest started: The Sunken Grimoire.", "Quest"),
        ("End",),
        ("@chat",),
        say("Scholar", "Sand gets everywhere. In the books, in the bread, in the beard.", ("Goodbye.", "@end")),
        ("@end",), ("End",),
    ])
    w("Dig Sand_Mound", [
        (">Distance.From.Clicked.Tile", "48", "@far"),
        (">Got.Item", "Spade", "1", "@nospade"),
        ("Get.Value", "ATTRIBUTE", "GrimoireQuest", V1),
        ("Display.Message", "Cyan", "You dig into the dune..", "-"),
        ("Play.Animation", " ", "3", "DigHole"),
        ("Wait", "2"),
        ("Change.Tile", "%d,%d" % (mx_, my_), "Library_Stairs001", "0", "0"),
        ("Display.Message", "Yellow", "..and the sand slides away from a carved doorway, and steps going down.", "-"),
        (">Conditional", "$Variable.1=1", "@end"),
        ("Update.Attribute", "GrimoireQuest", "=2"),
        ("@end",), ("End",),
        ("@nospade",), ("Display.Message", "DarkRed", "You need a spade to dig.", "Denied"),
        ("End",),
    ] + FAR)
    w("1,9,0", [                                                  # (the doorway they've dug out stays dug)
        ("Get.Value", "ATTRIBUTE", "GrimoireQuest", V1),
        (">Conditional", "$Variable.1>=2", "@end"),
        ("Change.Tile", "%d,%d" % (mx_, my_), "Library_Stairs001", "0", "0"),
        ("@end",), ("End",),
    ])
    w("Climb Down Library_Stairs", [
        (">Distance.From.Clicked.Tile", "48", "@far"),
        ("Play.Sound", "Ladder"),
        ("Display.Message", "Cyan", "You go down the steps, into the dark under the sand.", "-"),
        ("Teleport", at(13, 15, -8), "1,9,-1"),
        ("End",),
    ] + FAR)
    w("Climb Up Library_Steps", [
        (">Distance.From.Clicked.Tile", "48", "@far"),
        ("Play.Sound", "Ladder"),
        ("Teleport", at(mx_, my_ + 1, -8), "1,9,0"),
        ("End",),
    ] + FAR)
    w("1,9,-1", [
        ("Display.Message", "Red", "Dry air, old paper, and something shuffling between the shelves.", "-"),
        ("Add.Entity", at(9, 8, -8), "Tomb_Guardian", "NPC", "Attitude=Bad Zone=7,5,12,10"),
        ("Add.Entity", at(18, 9, -8), "Tomb_Guardian", "NPC", "Attitude=Bad Zone=15,5,19,12"),
        ("Add.Entity", at(14, 12, -8), "Tomb_Guardian", "NPC", "Attitude=Bad Zone=8,11,19,15"),
        ("Get.Value", "ATTRIBUTE", "GrimoireQuest", V1),
        (">Conditional", "$Variable.1<3", "@taken"),
        ("Add.Entity", at(14, 5), "Grimoire_Lectern", "StaticObject", "-"),
        ("End",),
        ("@taken",), ("Add.Entity", at(14, 5), "Empty_Lectern", "StaticObject", "-"),
        ("End",),
    ])
    w("Take Grimoire_Lectern", [
        (">Distance.From.Clicked.Entity", "48", "@far"),
        ("Get.Value", "ATTRIBUTE", "GrimoireQuest", V1),
        ("Remove.Entity", "$Object.under.Cursor.X,$Object.under.Cursor.Y", "Grimoire_Lectern"),
        ("Add.Entity", at(14, 5), "Empty_Lectern", "StaticObject", "-"),
        ("Give.Item", "Grimoire_of_Unbinding", "1"),
        ("Play.Sound", "Quest"),
        ("Update.Attribute", "GrimoireQuest", "=3"),
        ("Display.Message", "Yellow", "Quest complete: The Sunken Grimoire! Take it to Bert.", "Quest"),
        ("End",),
    ] + FAR)
    w("Talk to Warden", [
        ("Get.Value", "ATTRIBUTE", "RingQuest", V1),
        (">Conditional", "$Variable.1=0 and $Attr.BertQuest>=1", "@s1"),
        (">Quest.Can.Start", "RingQuest", "@end"),
        say("Warden", "The Ember Ring? The Ashen Priest wears it, and he's welcome to it, as far as I'm concerned.\\He "
                      "holds the Cinder Fort, high in the Cinder Peaks, with his cult and his chanting. If Bert wants "
                      "that ring, you'll have to take it off his finger yourself.", ("Then I will.", "@start")),
        ("@start",),
        ("Update.Attribute", "RingQuest", "=1"),
        ("Display.Message", "Yellow", "Quest started: The Ember Ring.", "Quest"),
        ("End",),
        ("@s1",), (">Conditional", "$Variable.1=1", "@chat"),
        say("Warden", "The Cinder Fort is up the road north, high in the peaks. Take water. Take armour.",
            ("I will.", "@end")),
        ("End",),
        ("@chat",),
        say("Warden", "Emberwatch: the last fort before the Cinderlands. Smoke on the wind, and ash on the bread.",
            ("Goodbye.", "@end")),
        ("@end",), ("End",),
    ])
    w("Kill Ashen_Priest", [
        ("Get.Value", "ATTRIBUTE", "RingQuest", V1),
        (">Conditional", "$Variable.1=1", "@end"),
        ("Give.Item", "Ember_Ring", "1"),
        ("Update.Attribute", "RingQuest", "=2"),
        ("Display.Message", "Yellow", "The Ashen Priest falls, and the Ember Ring rolls from his finger, glowing like a "
                                      "coal. Quest complete: The Ember Ring! Take it to Bert.", "Quest"),
        ("@end",), ("End",),
    ])


# ================================================================== the Sword of Valour
def sword():
    w("Talk to Captain_Rook", [
        ("Get.Value", "ATTRIBUTE", "ShipQuest", V1),
        (">Conditional", "$Variable.1=0 and $Attr.BertQuest>=2", "@s1"),
        (">Quest.Can.Start", "ShipQuest", "@end"),
        say("Sea_Captain", "Dragon Island? Ha! Nobody sails there. Nobody but me, and I've a hole in my hull you could "
                           "drive a cart through.\\Bring me ten planks and twenty nails, and I'll take you there and "
                           "back, dragons or no dragons.", ("I'll bring them.", "@start")),
        ("@start",),
        ("Update.Attribute", "ShipQuest", "=1"),
        ("Display.Message", "Yellow", "Quest started: A Ship for Dragon Island.", "Quest"),
        ("End",),
        ("@s1",), (">Conditional", "$Variable.1=1", "@sail"),
        (">Conditional", "$Item.Plank>=10 and $Item.Nails>=20", "@short"),
        ("Take.Item", "Plank", "10"),
        ("Take.Item", "Nails", "20"),
        ("Update.Attribute", "ShipQuest", "=2"),
        ("Display.Message", "Yellow", "Quest complete: A Ship for Dragon Island! Captain Rook's hull is whole.", "Quest"),
        say("Sea_Captain", "Good timber, good iron. She'll float! Say the word and we'll sail.",
            ("Sail to Dragon Island.", "@go"), ("Not yet.", "@end")),
        ("@go",), ("Goto.Script", "Sail to Dragon Island"),
        ("@short",),
        say("Sea_Captain", "Ten planks and twenty nails, matey. A carpenter's bench makes planks from logs.",
            ("Right.", "@end")),
        ("End",),
        ("@sail",), (">Conditional", "$Variable.1>=2", "@chat"),
        say("Sea_Captain", "Dragon Island, is it? Hold on to your hat.", ("Sail to Dragon Island.", "@go2"),
            ("Not today.", "@end")),
        ("@go2",), ("Goto.Script", "Sail to Dragon Island"),
        ("@chat",),
        say("Sea_Captain", "Sea's calm. Too calm. I don't trust it.", ("Goodbye.", "@end")),
        ("@end",), ("End",),
    ])
    w("Sail to Dragon Island", [
        ("Display.Message", "Cyan", "Captain Rook casts off, and the coast falls away behind you..", "-"),
        ("Play.Sound", "Boat"),
        ("Toggle.User.Input", "OFF"),
        ("Wait", "3"),
        ("Toggle.User.Input", "ON"),
        ("Teleport", "Dragon_Island_Landing", "-"),
        ("Display.Message", "Yellow", "..and Dragon Island rises out of the sea, smoking. Something roars inland.", "-"),
        ("Get.Value", "ATTRIBUTE", "DragonIsleQuest", V1),
        (">Conditional", "$Variable.1=0", "@end"),
        ("Update.Attribute", "DragonIsleQuest", "=1"),
        ("Update.Attribute", "ValourSeals", "=0"),
        ("Display.Message", "Yellow", "Quest started: The Island of Dragons.", "Quest"),
        ("@end",), ("End",),
    ])
    w("Talk to Captain_Rook_Island", [
        say("Sea_Captain", "Back to the mainland? The boat's ready when you are.", ("Take me back.", "@go"),
            ("Not yet.", "@end")),
        ("@go",),
        ("Display.Message", "Cyan", "Captain Rook pushes off, and Dragon Island smokes behind you..", "-"),
        ("Play.Sound", "Boat"),
        ("Toggle.User.Input", "OFF"),
        ("Wait", "3"),
        ("Toggle.User.Input", "ON"),
        ("Teleport", "Rooks_Pier", "-"),
        ("Display.Message", "Yellow", "..and you step ashore by Ravensgate.", "-"),
        ("@end",), ("End",),
    ])
    w("Kill Drake", [
        ("Get.Value", "ATTRIBUTE", "DragonIsleQuest", V1),
        (">Conditional", "$Variable.1=1", "@end"),
        ("Get.Value", "ATTRIBUTE", "ValourSeals", V2),
        (">Conditional", "$Variable.2<3", "@end"),
        ("Update.Attribute", "ValourSeals", "+1"),
        ("Give.Item", "Valour_Seal", "1"),
        ("Get.Value", "CALCULATION", "$Variable.2+1", V2),
        ("Display.Message", "Yellow", "A Valour Seal falls from the drake's hoard-hide: $Variable.2 of 3.", "-"),
        ("@end",), ("End",),
    ])
    w("Temple Door", [
        ("Get.Value", "ATTRIBUTE", "DragonIsleQuest", V1),
        (">Conditional", "$Variable.1=1", "@end"),
        (">Got.Item", "Valour_Seal", "3", "@few"),
        ("Take.Item", "Valour_Seal", "3"),
        ("Play.Sound", "Door"),
        ("Update.Attribute", "DragonIsleQuest", "=2"),
        ("Display.Message", "Yellow", "The three seals sink into the hollows of the door, and it grinds open. Quest "
                                      "complete: The Island of Dragons!", "Quest"),
        ("End",),
        ("@few",), ("Display.Message", "Cyan", "Three hollows in the door, the shape of seals.", "-"),
        ("@end",), ("End",),
    ])
    w("8,10,0", [
        ("Get.Value", "ATTRIBUTE", "ValourQuest", V1),
        (">Conditional", "$Variable.1<3", "@drawn"),
        ("Add.Entity", at(13, 4), "Sword_In_Stone", "StaticObject", "-"),
        ("End",),
        ("@drawn",), ("Add.Entity", at(13, 4), "Empty_Stone", "StaticObject", "-"),
        ("End",),
    ])
    w("Talk to Valour_Guardian_Knight", [
        ("Get.Value", "ATTRIBUTE", "ValourQuest", V1),
        (">Conditional", "$Variable.1=0", "@after"),
        (">Quest.Can.Start", "ValourQuest", "@end"),
        say("Valour_Guardian", "Who comes for the Sword of Valour?\\The sword was forged for one deed: to end the dragon "
                               "of Galaith, and the bargain your forefathers made with it. It goes only to the heir of "
                               "Estforlan, and only if the heir is worthy.", ("I am the heir.", "@heir")),
        ("@heir",),
        say("Valour_Guardian", "Words. Show me valour.", ("Then I will.", "@fight")),
        ("@fight",),
        ("Update.Attribute", "ValourQuest", "=1"),
        ("Set.NPC.Attitude", "Valour_Guardian_Knight", "Bad"),
        ("Display.Message", "Red", "The guardian draws a sword of light.", "Fight1"),
        ("End",),
        ("@after",),
        say("Valour_Guardian", "The sword is yours, heir. Carry it well.", ("I will.", "@end")),
        ("@end",), ("End",),
    ])
    w("Kill Valour_Guardian", [
        ("Get.Value", "ATTRIBUTE", "ValourQuest", V1),
        ("Set.NPC.Attitude", "Valour_Guardian_Knight", "Good"),
        (">Conditional", "$Variable.1=1", "@end"),
        ("Update.Attribute", "ValourQuest", "=2"),
        ("Display.Message", "Yellow", "The guardian kneels, and fades into light: \"Take it, heir.\"", "-"),
        ("@end",), ("End",),
    ])
    w("Draw Sword_In_Stone", [
        (">Distance.From.Clicked.Entity", "48", "@far"),
        ("Get.Value", "ATTRIBUTE", "ValourQuest", V1),
        (">Conditional", "$Variable.1=2", "@stuck"),
        ("Remove.Entity", "$Object.under.Cursor.X,$Object.under.Cursor.Y", "Sword_In_Stone"),
        ("Add.Entity", at(13, 4), "Empty_Stone", "StaticObject", "-"),
        ("Give.Item", "Sword_of_Valour", "1"),
        ("Play.Sound", "LevelUp"),
        ("Update.Attribute", "ValourQuest", "=3"),
        ("Display.Message", "Yellow", "The Sword of Valour slides from the stone as if it had been waiting for your hand. "
                                      "Quest complete: The Sword of Valour!", "Quest"),
        ("End",),
        ("@stuck",), ("Display.Refusal", "The sword won't move. The guardian is watching you.", "Fail"),
        ("End",),
    ] + FAR)


# ================================================================== Galaith
def galaith():
    rows = [("Get.Value", "ATTRIBUTE", "GalaithQuest", V1), (">Conditional", "$Variable.1=0", "@end")]
    rows += [("Add.Entity", at(7, y), "Barrier_Light", "StaticObject", "-") for y in (10, 11, 12)]
    rows += [("@end",), ("End",)]
    w("10,6,0", rows)
    w("Use Staff_of_Estforlan With Barrier", [
        (">Distance.From.Clicked.Tile", "64", "@far"),
        ("Get.Value", "ATTRIBUTE", "GalaithQuest", V1),
        (">Conditional", "$Variable.1=0", "@open"),
        (">Conditional", "$Attr.BarrierSpell>=1", "@nospell"),
        (">Quest.Can.Start", "GalaithQuest", "@end"),
        ("Display.Message", "Cyan", "You hold the Staff of Estforlan to the barrier and speak Bert's words of "
                                    "Unbinding..", "-"),
        ("Play.Sound", "SpellCast"),
        ("Wait", "2"),
        ("Remove.Entity", at(7, 10), "Barrier_Light"),
        ("Remove.Entity", at(7, 11), "Barrier_Light"),
        ("Remove.Entity", at(7, 12), "Barrier_Light"),
        ("Play.Sound", "Thunder"),
        ("Update.Attribute", "GalaithQuest", "=1"),
        ("Display.Message", "Yellow", "..and the barrier shatters like glass. Beyond it, on the scorched ground before "
                                      "Galaith's black walls, something huge lifts its head.", "-"),
        ("End",),
        ("@nospell",), ("Display.Refusal", "The staff hums against the barrier, but you don't know the words."),
        ("End",),
        ("@open",), ("Display.Message", "Cyan", "The barrier is broken.", "-"),
        ("@end",), ("End",),
    ] + FAR)
    w("The Dragon Speaks", [
        ("Get.Value", "ATTRIBUTE", "GalaithQuest", V1),
        (">Conditional", "$Variable.1=1 and $Attr.DragonSpoke=0", "@end"),
        ("Update.Attribute", "DragonSpoke", "=1"),
        ("Toggle.User.Input", "OFF"),
        ("Play.Sound", "Kill_Dragon"),
        say("Galaith_Dragon", "So. The heir of Estforlan comes to me at last, and on his own feet.\\Eighteen winters I "
                              "have waited at these walls. Eighteen winters the city has starved for want of the road, "
                              "and all for one small debt.", ("What debt?", "@debt")),
        ("@debt",),
        say("Galaith_Dragon", "A bargain, child, not a curse. Your forefathers wanted the mountain's gold and its mana, "
                              "and I let them have it, for the firstborn heir of every generation. They signed in "
                              "blood. Your mother broke it, and ran.", ("She saved me.", "@saved")),
        ("@saved",),
        say("Player", "My mother saved my life. The bargain ends today.", ("...", "@answer")),
        ("@answer",),
        say("Galaith_Dragon", "Ends? It ends when I have you.\\...What is that at your side? That blade. Valour. So the old "
                              "knights left a sting in the tale after all.\\Come, then, heir. Let us see whose debt is "
                              "paid.", ("Fight!", "@fight")),
        ("@fight",),
        ("Toggle.User.Input", "ON"),
        ("Display.Message", "Red", "The dragon of Galaith rises, wings blotting out the sky!", "-"),
        ("@end",), ("End",),
    ])
    w("Kill Galaith_Dragon", [
        ("Get.Value", "ATTRIBUTE", "GalaithQuest", V1),
        (">Conditional", "$Variable.1=1", "@end"),
        ("Update.Attribute", "GalaithQuest", "=2"),
        ("Display.Message", "Yellow", "The Sword of Valour finds the dragon's heart. With its last breath it hisses: "
                                      "\"Paid... in full...\" and the black hulk crashes to the scorched earth.", "-"),
        ("Play.Sound", "Quest"),
        ("Display.Message", "Yellow", "Quest complete: The Dragon of Galaith! The gates of Galaith swing open.", "-"),
        ("@end",), ("End",),
    ])
    chancellor = npc_id("Galaith_Speaker", "Chancellor")
    archivist = npc_id("Galaith_Clerk", "Archivist")
    w("Talk to Palace_Captain", [
        ("Get.Value", "ATTRIBUTE", "GuardQuest", V1),
        (">Conditional", "$Variable.1=0", "@s4"),
        (">Quest.Can.Start", "GuardQuest", "@end"),
        say("Guard_Captain", "Halt. You're the one who killed the dragon? Then Galaith owes you everything, and you have "
                             "my thanks.\\But nobody sees the King without the Lord Chancellor's leave. Not even dragon-"
                             "slayers. He sits in the Parliament.", ("I'll see the Chancellor.", "@start")),
        ("@start",),
        ("Update.Attribute", "GuardQuest", "=1"),
        ("Display.Message", "Yellow", "Quest started: The Royal Guard.", "Quest"),
        ("End",),
        ("@s4",), (">Conditional", "$Variable.1=4 and $Item.Chancellors_Warrant>=1", "@chat"),
        ("Take.Item", "Chancellors_Warrant", "1"),
        ("Update.Attribute", "GuardQuest", "=5"),
        say("Guard_Captain", "The Chancellor's warrant. Then you may pass, and... my lord.\\The King is in the throne "
                             "room.", ("Thank you, Captain.", "@done")),
        ("@done",), ("Display.Message", "Yellow", "Quest complete: The Royal Guard!", "Quest"),
        ("End",),
        ("@chat",),
        say("Guard_Captain", "The palace is guarded day and night.", ("Goodbye.", "@end")),
        ("@end",), ("End",),
    ])
    w("Talk to " + chancellor, [
        ("Get.Value", "ATTRIBUTE", "GuardQuest", V1),
        (">Conditional", "$Variable.1=1", "@s3"),
        say("Chancellor", "You wish to see the King? You, and every merchant, beggar and poet in Galaith, now the gates "
                          "are open.\\What makes you more than they are?", ("I am his son.", "@son")),
        ("@son",),
        say("Chancellor", "Bold. The Queen's child would be eighteen now, and would carry the Amulet of Succession. "
                          "Show it to the Royal Archivist, at the City Hall: she knows every true seal in Estforlan. If "
                          "she vouches for it, so shall I.", ("I'll go to the Archivist.", "@go")),
        ("@go",), ("Update.Attribute", "GuardQuest", "=2"),
        ("End",),
        ("@s3",), (">Conditional", "$Variable.1=3 and $Item.Archivists_Attestation>=1", "@chat"),
        ("Take.Item", "Archivists_Attestation", "1"),
        ("Give.Item", "Chancellors_Warrant", "1"),
        ("Update.Attribute", "GuardQuest", "=4"),
        say("Chancellor", "The Archivist's seal, in green. Then it is true.\\My lord. Forgive an old man his doubts. Here "
                          "is my warrant: show it to the captain of the guard.", ("Thank you, Chancellor.", "@end")),
        ("End",),
        ("@chat",),
        say("Chancellor", "The Parliament of Estforlan will return from Southport, now the road is open. There is much "
                          "to do.", ("Goodbye.", "@end")),
        ("@end",), ("End",),
    ])
    w("Talk to " + archivist, [
        ("Get.Value", "ATTRIBUTE", "GuardQuest", V1),
        (">Conditional", "$Variable.1=2", "@chat"),
        (">Got.Item", "Amulet_of_Succession", "1", "@noamulet"),
        say("Archivist", "The Chancellor sent you? Let me see it.\\She turns the amulet in the lamplight, and her hands "
                         "begin to shake.\\The crown, the sapphire, the mark of the old smiths under the clasp. This is "
                         "the Amulet of Estforlan Succession. Queen Mary wore it the night she vanished.",
            ("She was my mother.", "@mother")),
        ("@mother",),
        ("Give.Item", "Archivists_Attestation", "1"),
        ("Update.Attribute", "GuardQuest", "=3"),
        say("Archivist", "Then welcome home, my lord. Take my word to the Chancellor, under my own seal.",
            ("Thank you.", "@end")),
        ("End",),
        ("@noamulet",),
        say("Archivist", "An amulet? You'd better show it to me, then. I can't vouch for a story.", ("Right.", "@end")),
        ("End",),
        ("@chat",),
        say("Archivist", "The archive of Galaith: every charter, every seal, every deed since the city was founded.",
            ("Goodbye.", "@end")),
        ("@end",), ("End",),
    ])
    w("Talk to Rupert_On_Throne", [
        ("Get.Value", "ATTRIBUTE", "KingQuest", V1),
        (">Conditional", "$Variable.1=0", "@after"),
        (">Quest.Can.Start", "KingQuest", "@end"),
        say("King_Rupert", "They tell me the dragon is dead, and that the one who killed it asks to see me.\\Come closer. "
                           "Let me see your face.", ("Show him the amulet.", "@amulet")),
        ("@amulet",),
        say("King_Rupert", "That amulet... where did you get that? I gave it to my wife, the night before... the night "
                           "she ran.", ("Tell him of Mary's will.", "@will")),
        ("@will",),
        say("Player", "My mother, Mary, died on the Isle, where she raised me. Her last will told me who I am. She asked "
                      "me to come home to you and tell you of her death.\\And to tell you she never stopped loving you.",
            ("...", "@weep")),
        ("@weep",),
        ("Play.Sound", "Quest"),
        ("Display.Message", "Cyan", "The King comes down from his throne, and holds you, and weeps.", "-"),
        say("King_Rupert", "Mary. My Mary. She took you away so the dragon couldn't have you, and I let them call it a "
                           "betrayal. Eighteen years.\\My son. My son.", ("Father.", "@crown")),
        ("@crown",),
        say("King_Rupert", "I have held this throne for a city in chains. You broke the chains. It's yours.\\He lifts the "
                           "crown from his head and sets it on yours.\\Long live the King of Estforlan!",
            ("Long live Estforlan.", "@king")),
        ("@king",),
        ("Update.Attribute", "KingQuest", "=1"),
        ("Play.Sound", "LevelUp"),
        ("Display.Message", "Yellow", "Quest complete: The True Heir! You are the King of Estforlan. The world is yours "
                                      "to explore.", "Quest"),
        ("Add.Entity", at(13, 7, -2), "Strawberry_Cat", "NPC", JIMMY),
        ("Display.Message", "Cyan", "A ginger cat you'd know anywhere has curled up on the throne. Jimmy, how did you "
                                    "get here?", "-"),
        ("End",),
        ("@after",),
        say("King_Rupert", "My son, the King. Your mother would be proud.", ("Goodbye, Father.", "@end")),
        ("@end",), ("End",),
    ])
    w("12,5,0", [                                 # (Jimmy, asleep on the throne once you're king: throne_jimmy.py)
        ("Get.Value", "ATTRIBUTE", "KingQuest", V1),
        (">Conditional", "$Variable.1>=1", "@end"),
        ("Add.Entity", at(13, 7, -2), "Strawberry_Cat", "NPC", JIMMY),
        ("@end",), ("End",),
    ])
    # (Stroke / Talk to Throne_Jimmy: throne_jimmy.py, as he's curled up on the throne or not)


# Jimmy in the throne room: the cat himself, curling up on the throne when it's free (throne_jimmy.py)
JIMMY = "Attitude=Good Zone=6,8,20,12 Nap=13,7 Pause=4-12 Id=Throne_Jimmy Name=Jimmy"

def retired():
    """The old main quest line's scripts with nothing left to do (their places stay, quiet)."""
    for name in ("Talk to King_Tyron", "Lair Portal", "0,0,-9"):
        K.remove_script(name)
    for n in (1, 2, 3):
        w("Ashen Shrine %d" % n, [("Display.Message", "Cyan", "A burnt shrine of the Ashen Hand, cold now.", "-"),
                                  ("End",)])
    w("Talk to Ashen_Acolyte", [
        say("Ashen_Acolyte", "The dragon of Galaith will have its due. It always does.", ("Goodbye.", "@end")),
        ("@end",), ("End",),
    ])
    w("Kill Ashen_Acolyte", [("Display.Message", "Cyan", "The acolyte crumples into the ash.", "-"), ("End",)])
    cut_lines("Talk to Witch", "OmenQuest", "OmenWitchTold")     # (Morwen's part in the Ashen Omens; her own goes on)
    lair = os.path.join(K.ROOT, "maps", "0,0,-9.txt")         # (Ignaroth's lair under Ashpeak: the dragon is Galaith's)
    if os.path.exists(lair):
        os.remove(lair)
        for name in ("Ambient.ini", "Music.ini"):
            path = os.path.join(K.DATA, name)
            with open(path, "rb") as fh:
                text = fh.read()
            with open(path, "wb") as fh:
                fh.write(b"".join(ln for ln in text.splitlines(True) if not ln.startswith(b"0,0,-9=")))
        print("Removed maps\\0,0,-9.txt (the old dragon's lair)")


def cut_lines(name, first, last):
    """Takes out of a numbered script the lines from the first naming `first` to the last naming `last`, its jumps
    renumbered (a jump into the cut goes on to the line after it)."""
    path = os.path.join(K.SCRIPTS, name + ".txt")
    with open(path, "rb") as fh:
        lines = fh.read().decode("cp1252").split("\r\n")
    body = [ln.split("\t") for ln in lines if ln[:2].isdigit()]
    hits = [i for i, f in enumerate(body) if first in f or last in f]
    if not hits:
        return
    a, b = hits[0], max(i for i, f in enumerate(body) if last in f)
    while body[b][1] != "End":                              # (to the end of the last part)
        b += 1
    gone = b - a + 1
    renum = lambda n: n if n <= a else (a + 1 if n <= b + 1 else n - gone)

    def jumps(f):
        if f[1] == "Display.Conversation":
            return list(range(5, len(f), 2))
        if f[1].startswith(">") or f[1] == "Goto.Line":
            return [len(f) - 1]
        return []
    out = []
    for f in body[:a] + body[b + 1:]:
        f = list(f)
        for j in jumps(f):
            if f[j].isdigit():
                f[j] = "%02d" % renum(int(f[j]))
        out.append(f)
    for i, f in enumerate(out):
        f[0] = "%02d" % (i + 1)
    head = [ln for ln in lines if not ln[:2].isdigit() and ln]
    with open(path, "wb") as fh:
        fh.write(("\r\n".join(head + ["\t".join(f) for f in out]) + "\r\n").encode("cp1252"))
    print("%s: lines %d to %d taken out" % (name, a + 1, b + 1))


REWORDS = {   # (file under Data: the old King Tyron's words, as they read now)
    "Scripts\\2,4,0.txt": [("Tyron's Keep, the King's garrison.", "King Rupert's Keep, held by his Steward.")],
    "Scripts\\4,4,0.txt": [("The Royal Isle: King Tyron's palace.", "The Royal Isle: the Wizards' Court.")],
    "Scripts\\Read Ashford_Iron_Mine.txt": [("Closed by order of King Tyron. Hobgoblins below!",
                                             "Closed by order of the King's Steward.")],
    "Scripts\\Read Royal_Treasury.txt": [("By order of King Tyron this door stays locked.",
                                          "The Wizards' Court's strongroom.")],
    "Scripts\\Read The_Royal_Isle.txt": [("King Tyron's palace. The gate is open to all honest folk. Its gate faces south.",
                                          "The Wizards' Court and its tower.")],
    "Scripts\\Talk to Farmer.txt": [("King Tyron ought to do something.", "The King's Steward ought to do something."),
                                    ("I'll speak to the King.", "I'll speak to the Steward.")],
    "Scripts\\Talk to Guard.txt": [
        ("King Tyron holds court in the throne hall.\\Mind your manners before the throne, and keep your blade sheathed.",
         "The wizards hold court in the great hall.\\Mind your manners, and keep your blade sheathed."),
        ("closed by order of King Tyron", "closed by order of the King's Steward"),
        ("Unless the King himself sent you, of course.", "Unless the Steward sent you, of course."),
        ("the King pays well for hobgoblin ears.\\His palace is on the Royal Isle: south to his keep, east along the "
         "goblin camp road, then over the causeway.",
         "the King's Steward pays well for hobgoblin ears.\\The Steward keeps the King's keep, south of here."),
        ("The King holds court in the great hall.", "The Steward holds the hall while the King is away.")],
    "Entities.ini": [("A guard of King Tyron, spear in hand.", "A guard of the King's, spear in hand.")],
}
KEEP_NAMED = ("Scripts\\Read Ashford.txt", "Scripts\\Read Oakhollow.txt", "Scripts\\Talk to Ranger.txt",
              "Scripts\\Watch Stone 1.txt", "Quests.ini")   # (where "Tyron's Keep" is only the place's old name)


def reword():
    """King Tyron is gone (King Rupert's Keep is held by his Steward; the Royal Isle is the Wizards' Court): his name
    and his palace come out of the old signs, guards and quest text."""
    done = []
    for name in list(REWORDS) + list(KEEP_NAMED):
        path = os.path.join(K.DATA, name)
        if not os.path.exists(path):
            continue
        with open(path, "rb") as fh:
            text = fh.read().decode("cp1252")
        new = text
        for old, words in REWORDS.get(name, []):
            new = new.replace(old, words)
        new = new.replace("Tyron's Keep", "King Rupert's Keep")
        if new != text:
            with open(path, "wb") as fh:
                fh.write(new.encode("cp1252"))
            done.append(os.path.basename(name))
    if done:
        print("Reworded for King Rupert: " + ", ".join(done))


def scripts():
    reword()
    southport_and_ashford()
    keep()
    bert()
    grimoire_and_ring()
    sword()
    galaith()
    retired()
    print("Scripts: Southport, Ashford, the Keep, Bert, the grimoire, the ring, Dragon Island, Galaith, the throne")


def main():
    draw_pictures()
    data()
    places()
    quests()
    scripts()


if __name__ == "__main__":
    main()

