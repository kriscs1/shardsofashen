"""The monsters that fight from afar, status effects and the gravestone (the game's side: dragonsword\\extras.py).

  * Ranged and casting monsters (drawn by build_people.py, walking frames by build_walk.py): the Goblin_Archer and the
    Skeleton_Archer shoot arrows; the Goblin_Shaman throws fire (it can set you alight) and the Frost_Witch ice (it
    chills you, slowing you down). They keep their distance and shoot (Weapon.Range, Missile). In the goblin camp,
    and among the Wildlands' and the Eastreach's monsters.
  * On.Hit=<Effect> <chance %> on the monsters that poison (spiders, scorpions), burn (the dragon, the shaman), make you
    bleed (wolves, bears, bandits, trolls) or chill (the frost creatures).
  * The Antidote (Cures= every effect): brewed at the alchemy table (Herblore 3), dropped by spiders, scorpions and the
    frost witch, and sold by the herbalists.
  * The Gravestone: the StaticObject the game puts where you died, holding what you carried (Search it).
before_regions() runs before the Wildlands and the Eastreach are generated (their monster lists); extend() after.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sprite_kit as K  # noqa: E402
from common import p, read_bmp  # noqa: E402

ON_HIT = {"Giant_Spider": "Poison 35", "Scorpion": "Poison 45", "Bog_Troll": "Poison 20",
          "Dragon": "Burn 50", "Goblin_Shaman": "Burn 60",
          "Wolf": "Bleed 10", "Alpha_Wolf": "Bleed 30", "Bear": "Bleed 25", "Bandit": "Bleed 20", "Cave_Troll": "Bleed 20",
          "Snow_Wolf": "Chill 20", "Frost_Troll": "Chill 40", "Barrow_King": "Chill 35", "Frost_Witch": "Chill 75"}
RANGED = {   # name: (hp, attack speed, strength, defence, aggro, move, respawn, drops, range, missile, impact, examine)
    "Goblin_Archer": (8, 1.6, 2, 1, 130, 2.2, 40, "Bones,1-1,100 Arrows,2-6,70 Gold_Coin(s),1-3,40", 150,
                      "Arrow_Missile", "", "A goblin with a short bow and a quiver of crooked arrows."),
    "Goblin_Shaman": (14, 2.4, 3, 2, 140, 2.0, 60, "Bones,1-1,100 Gold_Coin(s),3-8,70 Fire_Bolt_Scroll,1-1,20 Herb,1-2,50",
                      160, "Fire_Bolt_Missile", "Fire_Burst", "A goblin shaman, bones in its hair and fire in its hands."),
    "Skeleton_Archer": (18, 1.9, 4, 3, 140, 1.5, 50, "Bones,1-2,100 Arrows,3-8,60 Gold_Coin(s),2-8,50", 160,
                        "Arrow_Missile", "", "A skeleton with a cracked longbow. Its aim is still good."),
    "Frost_Witch": (34, 2.4, 6, 4, 150, 1.8, 120, "Gold_Coin(s),10-25,100 Ice_Bolt_Scroll,1-1,30 Sapphire,1-1,10 "
                    "Antidote,1-1,30", 170, "Ice_Bolt_Missile", "Ice_Burst",
                    "A witch of the high snows. Her breath freezes in the air."),
}
MOVEMENT = {"Goblin_Archer": (3, 4, "0.6", "1-4"), "Goblin_Shaman": (2, 3, "0.5", "2-6"),
            "Skeleton_Archer": (2, 3, "0.4", "2-5"), "Frost_Witch": (2, 3, "0.5", "3-8")}
CAMP = [("Goblin_Archer", 8, 8, "Zone=6,7,11,10"), ("Goblin_Archer", 16, 12, "Zone=14,11,19,13"),
        ("Goblin_Shaman", 13, 8, "Zone=11,7,15,10")]


DURABILITY = [("Copper", 60), ("Bronze", 100), ("Iron", 160), ("Steel", 240), ("Mithril", 360), ("Dragon", 600),
              ("Leather", 110), ("Wooden", 80), ("Oak", 110), ("Willow", 150), ("Yew", 220), ("Chefs", 40),
              ("Silver", 90), ("Rusty", 50)]


def durability(name):
    return next((d for m, d in DURABILITY if name.startswith(m)), 120)


def before_regions(R, E):
    """The Wildlands' and the Eastreach's monster lists get the archers and casters."""
    R.MONSTERS["hills"] = [("Bandit", 2), ("Goblin_Archer", 1), ("Goblin_Shaman", 1)]
    R.MONSTERS["desert"] = R.MONSTERS["desert"] + [("Skeleton_Archer", 1)]
    R.MONSTERS["snow"] = R.MONSTERS["snow"] + [("Frost_Witch", 1)]
    E.MONSTERS["downs"] = E.MONSTERS["downs"] + [("Skeleton_Archer", 1)]


def make_sprites():
    """The Antidote (the basic potion, yellow-green) and the Gravestone, in sprites\\Entities."""
    w, h, rows = read_bmp(p("sprites", "Entities", "Basic_Potion.png"))
    mask, img = rows[:h // 2], rows[h // 2:]
    out = []
    for y in range(h // 2):
        row = []
        for x in range(w):
            if sum(mask[y][x]) > 384:
                row.append(None)
                continue
            r, g, b = img[y][x]
            if r > g + 30 and r > b + 30:                       # the red potion: now a sharp yellow-green
                k = (r + g + b) / 3.0 / 140.0
                row.append((min(255, int(150 * k)), min(255, int(210 * k)), min(255, int(60 * k))))
            else:
                row.append((r, g, b))
        out.append(row)
    changed = K.save("Entities", "Antidote", out)
    grave = [[None] * 32 for _ in range(32)]

    def put(x, y, c):
        if 0 <= x < 32 and 0 <= y < 32:
            grave[y][x] = c
    for y in range(24, 31):                                     # the mound of fresh earth
        half = int(14 * (1 - ((y - 27.5) / 4.0) ** 2) ** 0.5) if abs(y - 27.5) < 4 else 0
        for x in range(16 - half, 16 + half):
            put(x, y, (96, 70, 44) if (x + y) % 3 else (78, 56, 34))
    for y in range(6, 27):                                      # the headstone, rounded at the top
        for x in range(9, 23):
            if y < 10 and (x - 15.5) ** 2 + (y - 10) ** 2 > 42:
                continue
            c = (150, 150, 156) if x < 21 else (112, 112, 118)
            put(x, y, (176, 176, 182) if x == 9 or y == 6 else c)
    for y in range(10, 20):                                     # a cross cut into it
        put(15, y, (90, 90, 96)); put(16, y, (90, 90, 96))
    for x in range(12, 20):
        put(x, 13, (90, 90, 96))
    changed |= K.save("Entities", "Gravestone", grave)
    return changed


def extend(W, C):
    # the monsters
    for name, (hp, aspeed, st, de, aggro, move, respawn, drops, rng, missile, impact, examine) in RANGED.items():
        keys = C.bad(examine, hp, aspeed, st, de, aggro, move, 1, respawn, drops)
        keys += [("Weapon.Range", str(rng)), ("Missile", missile)] + ([("Missile.Impact", impact)] if impact else [])
        keys += [("Kill.Sound", C.kill_sound(name))]
        C.ENTITIES[name] = keys
    C.MOVEMENT.update(MOVEMENT)
    for name, effect in ON_HIT.items():
        C.ENTITY_KEYS.setdefault(name, []).append(("On.Hit", effect))
    # who's out when (dragonsword\daynight.py): townsfolk and the meadow's creatures by day, bats and the
    # skeletons of the open country by night (in the caves they're always about)
    for name in ("Villager", "Man", "Woman", "Settler", "Dog", "Butterfly", "Rabbit", "Chicken", "Duck"):
        C.ENTITY_KEYS.setdefault(name, []).append(("Schedule", "Day"))
    for name in ("Bat", "Skeleton", "Skeleton_Archer"):
        C.ENTITY_KEYS.setdefault(name, []).append(("Schedule", "Night"))
    # durability (dragonsword\durability.py): how many blows each weapon and piece of armour takes, by what it's made
    # of; and the smiths who mend it all for gold
    import re
    slots = {}
    for source in (C.ENTITIES, getattr(W, "ENTITY_KEYS", {})):
        for name, keys in source.items():
            for k, v in keys:
                if k == "Slot":
                    slots[name] = v
    cur = None
    for line in open(p("data", "Entities.ini"), encoding="cp1252"):
        line = line.strip()
        if line.startswith("["):
            cur = line[1:-1]
        elif cur and line.startswith("Slot=") and cur not in slots:
            slots[cur] = line[5:]
    for name, slot in slots.items():
        if slot and slot != "Ring":
            C.ENTITY_KEYS.setdefault(name, []).append(("Durability", str(durability(name))))
    for smith in ("Blacksmith", "Forgemaster", "Dwarf"):
        C.ENTITY_KEYS.setdefault(smith, []).append(("Use.Words", "Talk to,Repair"))
    # the antidote and the gravestone
    C.ENTITIES["Antidote"] = [("Type", "MapItem"), ("Use.Words", "Drink"), ("Examine.Info",
                              "A sharp green tonic: it cures poison, burns, bleeding and frostbite."),
                              ("Value", "12"), ("Stackable", "10"),
                              ("Cures", "Poison Burn Bleed Chill")]
    C.ENTITIES["Gravestone"] = [("Type", "StaticObject"), ("Use.Words", "Search"), ("Solid", "0"),
                                ("Examine.Info", "Your grave. What you were carrying when you died is buried here.")]
    rack = C.CRAFT["CRAFT-Herblore"][1]                         # (brewed at the alchemy table, Herblore 3)
    if not any(r.startswith("Antidote,") for r in rack):
        rack.insert(1, "Antidote,Herb 2 Spider_Silk 1 Empty_Vial 1,0.4,3")
    for name in ("Giant_Spider", "Scorpion"):                   # (their poison's cure, sometimes)
        for i, (k, v) in enumerate(C.ENTITIES.get(name, [])):
            if k == "Drops" and "Antidote" not in v:
                C.ENTITIES[name][i] = ("Drops", v + " Antidote,1-1,15")
    # the goblin camp's archers and shaman
    m = W.MAPS["3,4,0"]
    for name, x, y, zone in CAMP:
        m["entities"].append(W.npc("BadNPC", name, x, y))
        C.NPC_OPTIONS["3,4,0"][(name, x, y)] = zone + " " + C.CAMP_CHASE
    make_sprites()
