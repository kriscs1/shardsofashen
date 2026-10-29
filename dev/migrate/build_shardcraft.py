"""Shardcraft and the shardstones (dsengine/shardcraft.py; the skills' names: rename_skills.py):

  * the pictures: a dormant shardstone (Shardstone_Dormant: the rune dark, no star), the rare shards (Ember_Shard,
    Ward_Shard, Storm_Shard), every enchanted kind of gear (the gear with its shard's glow round its edge and a glint),
    and the skill icons for Alchemy, Shardcraft and Homesteading (sprites\\Interface);
  * the sounds: Stone_Dormant (a dull knock on cold stone), Stone_Wake (the rune catching), Enchant (a shard melting
    in), Rare_Shard (something bright in the dust);
  * Entities.ini: the rare shards (Enchant=<word>: what they make), and an enchanted kind of every piece of gear
    that can take one (Emberbound_<Gear>, Stormbound_<Gear>: weapons; Wardbound_<Gear>: armour), its Base= the gear
    and Enchanted= its word, a little better than the gear. Not quest gear (Droppable=0), nor gear a script names;
  * Shards.ini: [Channeling] (fewer Shards a cast), [Shardcraft], [Enchant], and the Shardgate's Shardgate.Stones and
    Shardgate.Level in [Shards] (only what's missing is added: edit them there);
  * data\\Shardstones.ini: every shardstone's key and name (read from the old travel scripts, the first time), and
    the old scripts gone (Travel Shardstone, Shardstone Menu: the engine travels now, on a copy of the world map);
  * the skills' scripts (clicking one on the Stats tab: what it's for).

Safe to run again (it writes the same, and only what's changed).

  python -I "dev\\migrate\\build_shardcraft.py"
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import Ini, p                      # noqa: E402
import build_sounds as SND                     # noqa: E402
import sprite_kit as K                         # noqa: E402
import story_kit as SK                         # noqa: E402

MAKER = "build_shardcraft.py"
RARE = {   # shard: (its word, what it takes, the key it raises, its colours: light, mid, dark)
    "Ember_Shard": ("Emberbound", "weapon", "Attack", ((255, 214, 120), (236, 120, 40), (150, 52, 24))),
    "Storm_Shard": ("Stormbound", "weapon", "Magic", ((214, 200, 255), (130, 110, 240), (64, 44, 150))),
    "Ward_Shard": ("Wardbound", "armour", "Defence", ((250, 246, 214), (214, 196, 120), (128, 110, 60))),
}
RARE_INFO = {
    "Ember_Shard": "An ember shard: a splinter of fire-magic, warm in the hand. Bound into a weapon, it bites harder.",
    "Storm_Shard": "A storm shard: a splinter of lightning, prickling your fingers. Bound into a weapon, its spells "
                   "strike harder.",
    "Ward_Shard": "A ward shard: a pale splinter that hums when you hold it. Bound into armour, it turns blows aside.",
}
ARTICLE = {"Ember_Shard": "an ember shard", "Storm_Shard": "a storm shard", "Ward_Shard": "a ward shard"}
ENCHANTED_WORDS = {"Attack": "+%d Attack", "Magic": "+%d spell damage", "Defence": "+%d Defence"}
SHARDS = [   # (section, key, value, what it means)
    ("Shards", "Shardgate.Stones", "8", "Shardgate.Stones: the shardstones you must have activated before the ring "
                                        "will hold; Shardgate.Level: the Shardcraft it needs."),
    ("Shards", "Shardgate.Level", "5", ""),
    ("Channeling", "Saving.Per.Level", "1.5", "Higher Channeling, fewer Shards a cast: Saving.Per.Level percent off "
                                              "for each level past the first, at most Saving.Max percent, never under "
                                              "Min.Cost (and a spell that costs nothing still costs nothing)."),
    ("Channeling", "Saving.Max", "30", ""),
    ("Channeling", "Min.Cost", "1", ""),
    ("Shardcraft", "Dismantle.XP", "0.04", "Shardcraft xp for each Shard a dismantling gives (at least "
                                            "Dismantle.XP.Min); for activating a shardstone (Shardstone.XP)."),
    ("Shardcraft", "Dismantle.XP.Min", "0.05", ""),
    ("Shardcraft", "Shardstone.XP", "0.5", ""),
    ("Shardcraft", "Rare.Chance", "4", "In 100: dismantling gear worth Rare.Min.Value gold or more also gives a rare "
                                       "shard (Rare.Chance.Per.Level more for each Shardcraft level)."),
    ("Shardcraft", "Rare.Chance.Per.Level", "0.4", ""),
    ("Shardcraft", "Rare.Min.Value", "30", ""),
    ("Enchant", "Level", "4", "Enchanting gear with a rare shard (Enchant, in the pack): the Shardcraft level it "
                              "needs, the Shards it binds with (Shards, and Shards.Per.Value more for each gold the "
                              "gear's worth), and its Shardcraft xp."),
    ("Enchant", "Shards", "8", ""),
    ("Enchant", "Shards.Per.Value", "0.05", ""),
    ("Enchant", "XP", "0.8", ""),
]
SKILL_TEXT = {
    "Crafting": "Crafting: smelt ore and forge tools at a furnace or anvil (the Ashford smithy, Brokk's hall); shear "
                "sheep, then tan, spin and make jewellery at a workbench.",
    "Alchemy": "Alchemy: pick herbs, berries and mushrooms, and brew potions at an alchemy table.",
    "Channeling": "Channeling: cast spells. The better you are, the fewer Shards each cast drinks.",
    "Shardcraft": "Shardcraft: work Shard magic. Wake shardstones, break gear down for its Shards, write scrolls, "
                  "enchant gear with rare shards and shape your pocket of the Shardrealm.",
    "Homesteading": "Homesteading: build on your homestead, and sow and harvest crops.",
}
OLD_SCRIPTS = ("Travel Shardstone", "Travel Shardstone 2", "Shardstone Menu", "Shardstone Menu 2", "Smithing Skill",
               "Potion_Making Skill")


# ================================================================== pictures
def dormant():
    """The shardstone as it stands till you activate it: its rune cut dark into the stone, no glow."""
    import build_sprites
    img = build_sprites.shardstone()
    for y, row in enumerate(img):
        for x, c in enumerate(row):
            if c is not None and c[2] > c[0] + 24:      # (the rune and its glow: blue)
                g = int(sum(c) / 3 * 0.32) + 30
                img[y][x] = (g, g, g + 6)
    return img


def crystal(light, mid, dark):
    """A rare shard: a long faceted splinter, lit down one side."""
    img = K.new()
    pts = [(16, 4), (21, 12), (19, 26), (13, 28), (11, 15)]
    for y in range(32):
        xs = []
        for i in range(len(pts)):
            (x1, y1), (x2, y2) = pts[i], pts[(i + 1) % len(pts)]
            if (y1 <= y < y2) or (y2 <= y < y1):
                xs.append(x1 + (y - y1) * (x2 - x1) / float(y2 - y1))
        if len(xs) >= 2:
            a, b = int(min(xs)), int(max(xs))
            for x in range(a, b + 1):
                t = (x - a) / float(max(1, b - a))
                img[y][x] = light if t < 0.3 else mid if t < 0.7 else dark
    for y in range(7, 24):                               # (the ridge down its middle)
        K.put(img, 16 + (y - 7) // 6 - 1, y, K.mix(light, (255, 255, 255), 0.5))
    for x, y in ((22, 6), (23, 5), (24, 6), (23, 7)):    # (a glint)
        K.put(img, x, y, (255, 255, 255))
    return K.outline_img(img, tuple(max(0, v // 3) for v in dark))


def enchanted(base, colours):
    """The gear with its shard's glow along its edge and a glint at its corner."""
    img = [list(r) for r in K.load("Entities", base)]
    h, w = len(img), len(img[0])
    edge = [(x, y) for y in range(h) for x in range(w) if img[y][x] is not None and any(
        not (0 <= x + dx < w and 0 <= y + dy < h) or img[y + dy][x + dx] is None
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))]
    for x, y in edge:
        img[y][x] = K.mix(img[y][x], colours[1], 0.75)
    drawn = [(x, y) for y in range(h) for x in range(w) if img[y][x] is not None]
    if drawn:
        gx = max(x for x, _ in drawn)
        gy = min(y for _, y in drawn)
        for dx, dy in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
            K.put(img, min(w - 1, gx - 1) + dx, max(0, gy + 1) + dy, colours[0] if (dx, dy) != (0, 0)
                  else (255, 255, 255))
    return img


def flask():
    """Alchemy: a round flask, green brew bubbling in it, a cork."""
    img = K.new()
    for y in range(13, 29):
        for x in range(6, 27):
            d = ((x - 16) ** 2 + (y - 21) ** 2) ** 0.5
            if d <= 8.5:
                inside = y >= 18
                c = (90, 200, 90) if inside else (200, 226, 236)
                if x < 13:
                    c = K.mix(c, (255, 255, 255), 0.35)
                elif x > 20:
                    c = K.mix(c, (0, 0, 0), 0.25)
                img[y][x] = c
    for y in range(5, 14):
        for x in range(13, 20):
            img[y][x] = (200, 226, 236) if x > 13 else (236, 246, 250)
    for y in range(2, 6):
        for x in range(13, 20):
            img[y][x] = (150, 104, 62)
    for x, y in ((14, 21), (18, 19), (16, 24), (20, 23), (15, 15), (17, 11)):
        K.put(img, x, y, (220, 255, 210))
    return K.outline_img(img, (30, 40, 30))


def shardcraft_icon():
    """Shardcraft: a blue shard and the little hammer that works it."""
    img = crystal((210, 240, 255), (110, 190, 255), (40, 90, 170))
    for x in range(3, 15):                               # (the hammer's haft, across the shard's foot)
        K.put(img, x, 28 - (x - 3) // 3, (150, 104, 62))
    for y in range(20, 27):
        for x in range(2, 7):
            K.put(img, x, y, (170, 170, 180) if x < 5 else (120, 120, 130))
    return K.outline_img([[c if c != (13, 30, 56) else None for c in r] for r in img], (24, 24, 30))


def house():
    """Homesteading: a little house, a garden row before it."""
    img = K.new()
    for y in range(14, 27):
        for x in range(7, 25):
            img[y][x] = (214, 190, 150) if x < 20 else (180, 158, 120)
    for y in range(5, 15):                               # (the roof)
        half = (y - 5) + 3
        for x in range(16 - half, 16 + half):
            if 3 <= x <= 28:
                img[y][x] = (178, 70, 50) if x < 17 else (140, 52, 38)
    for y in range(19, 27):
        for x in range(14, 19):
            img[y][x] = (110, 70, 40)
    for y in range(17, 21):
        for x in range(9, 12):
            img[y][x] = (150, 200, 230)
    for x in range(4, 28, 3):                            # (the garden)
        K.put(img, x, 29, (70, 150, 60))
        K.put(img, x + 1, 28, (90, 180, 70))
    return K.outline_img(img, (40, 30, 24))


def art(gear):
    out = [("Entities", "Shardstone_Dormant", dormant())]
    out += [("Entities", name, crystal(*v[3])) for name, v in RARE.items()]
    out += [("Interface", "Skill_Alchemy", flask()), ("Interface", "Skill_Shardcraft", shardcraft_icon()),
            ("Interface", "Skill_Homesteading", house())]
    for shard, base, name in gear:
        if os.path.exists(p("sprites", "Entities", base + ".png")):
            out.append(("Entities", name, enchanted(base, RARE[shard][3])))
    n = sum(1 for kind, name, img in out if K.save(kind, name, img))
    print("Pictures: %d written (of %d)" % (n, len(out)))


# ================================================================== sounds
SOUNDS = {
    # a dull knock on cold stone, and nothing answering
    "Stone_Dormant": lambda: SND.mix((SND.shaped(SND.noise(61, SND.n(0.18), 0.2), 0.002, 14), 0.7),
                                     (SND.shaped(SND.tone(82, SND.n(0.4), glide=-0.2), 0.005, 8), 0.5)),
    # the rune catching: a low hum swelling into a chime
    "Stone_Wake": lambda: SND.mix((SND.shaped(SND.tone(98, SND.n(1.1), glide=0.5), 0.3, 2.5), 0.5),
                                  (SND.arpeggio([440, 660, 880, 1320], 0.09, 1.0, decay=2.6), 0.45),
                                  (SND.shaped(SND.noise(62, SND.n(0.9), 0.5, high=0.5), 0.4, 3.0), 0.2)),
    # a shard melting into the gear: a hiss, and a ring as it sets
    "Enchant": lambda: SND.mix((SND.shaped(SND.noise(63, SND.n(0.7), 0.6, high=0.6), 0.05, 4.0), 0.35),
                               (SND.arpeggio([784, 988, 1175, 1568, 1976], 0.06, 0.9, decay=3.0), 0.5),
                               (SND.shaped(SND.tone(1568, SND.n(0.9)), 0.3, 3.0, delay=0.35), 0.3)),
    # something bright in the dust: a quick high twinkle
    "Rare_Shard": lambda: SND.mix((SND.arpeggio([1319, 1760, 2093, 2637, 3136], 0.045, 0.7, decay=4.0), 0.6),
                                  (SND.shaped(SND.tone(2637, SND.n(0.5)), 0.02, 6.0, delay=0.22), 0.25)),
}


def sounds():
    for name, fn in SOUNDS.items():
        blob = SND.wav_bytes(fn())
        path = p("sounds", name + ".wav")
        if not (os.path.exists(path) and open(path, "rb").read() == blob):
            with open(path, "wb") as fh:
                fh.write(blob)
            print("wrote sounds\\%s.wav" % name)


# ================================================================== data
def named_in_scripts():
    """The things a script asks for by name (has it, takes it, wears it): an enchanted one wouldn't count."""
    words = set()
    for f in os.listdir(p("data", "Scripts")):
        with open(p("data", "Scripts", f), "rb") as fh:
            text = fh.read().decode("cp1252", "replace")
        words |= set(re.findall(r"(?:>Got\.Item|Take\.Item|>Equipped)	([A-Za-z0-9_']+)", text))
        words |= set(re.findall(r"\$Item\.([A-Za-z0-9_']+)", text))
        words |= set(re.findall(r"\$Equipped\.[A-Za-z]+[=<>]+([A-Za-z0-9_']+)", text))
    for f in ("Quests.ini", "Entities.ini"):                 # (a quest's or a death's Slain.By: that one weapon)
        with open(p("data", f), "rb") as fh:
            words |= set(re.findall(r"(?m)^(?:Slain\.By|Requires\.Items?)=([A-Za-z0-9_']+)", fh.read().decode("cp1252")))
    return words


def gear_list(ents):
    """[(shard, base, enchanted name)] for every piece of gear a rare shard can be bound into."""
    named = named_in_scripts()
    out = []
    for sec, items in ents.sections:
        kv = {k: v for k, v in items if k}
        slot = (kv.get("Slot") or "").strip()
        if not slot or kv.get("Base") or (kv.get("Droppable") or "1").strip() == "0" or sec in named:
            continue
        for shard, (word, takes, key, colours) in RARE.items():
            if (takes == "weapon") == (slot == "Weapon"):
                out.append((shard, sec, "%s_%s" % (word, sec)))
    return out


def data(gear):
    ents = Ini(p("data", "Entities.ini"))
    for shard, (word, takes, key, colours) in RARE.items():
        for k, v in (("Type", "MapItem"), ("Use.Words", "Enchant,Examine"), ("Stackable", "50"), ("Value", "60"),
                     ("Enchant", word), ("Examine.Info", RARE_INFO[shard])):
            ents.set(shard, k, v)
    keep = {name for _, _, name in gear}
    for sec, items in list(ents.sections):         # (gear that's gone, or can't take one now: its kinds go)
        kv = {k: v for k, v in items if k}
        if kv.get("Enchanted") and sec not in keep:
            ents.sections = [s for s in ents.sections if s[0] != sec]
    for shard, base, name in gear:
        word, takes, key, colours = RARE[shard]
        kv = {k: v for k, v in ents.section(base)[1] if k}
        now = float(kv.get(key, "0") or 0)
        more = max(2, int(round(now * (0.3 if key == "Magic" else 0.25))))
        for k, v in kv.items():
            if k not in ("Examine.Info", "Value"):
                ents.set(name, k, v)
        ents.set(name, key, ("%d" % (now + more)) if now == int(now) else ("%g" % (now + more)))
        ents.set(name, "Base", base)
        ents.set(name, "Enchanted", word)
        ents.set(name, "Value", str(int(float(kv.get("Value", "0") or 0) * 1.6 + 40)))
        ents.set(name, "Examine.Info", "%s %s: %s burns in it (%s)." % (
            (kv.get("Examine.Info") or "").strip(), word, ARTICLE[shard], ENCHANTED_WORDS[key] % more))
    for k, v in (("Type", "StaticObject"), ("Use.Words", "Examine"),
                 ("Examine.Info", "A shardstone, its rune dark and cold.")):
        ents.set("Shardstone_Dormant", k, v)            # (its picture: how a stone looks till you activate it)
    ents.set("Shardstone", "Use.Words", "Travel,Examine")
    ents.set("Shardstone", "Examine.Info", "An ancient shardstone, a rune carved deep in it.")
    ents.save(p("data", "Entities.ini"))
    sh = Ini(p("data", "Shards.ini"))
    for section, key, value, note in SHARDS:
        if sh.section(section) is None:
            sh.sections.append([section, []])
        if sh.get(section, key) is None:
            if note:
                sh.section(section)[1].append((None, "; " + note))
            sh.set(section, key, value, overwrite=False)
    sh.save(p("data", "Shards.ini"))
    print("Entities.ini: %d enchanted kinds of gear" % len(gear))


def shardstones():
    """data\\Shardstones.ini (kept if it's there: the mainland's builder writes it, estforlan/story.py)."""
    path = p("data", "Shardstones.ini")
    if not os.path.exists(path):
        rows = []
        for name in ("Travel Shardstone", "Travel Shardstone 2"):
            f = p("data", "Scripts", name + ".txt")
            if os.path.exists(f):
                text = open(f, "rb").read().decode("cp1252")
                rows += re.findall(r"The (.+?) shardstone's rune is dark\..*?Shardstone\.([A-Za-z]+) Shards", text)
        write_shardstones([(k, t) for t, k in rows])
    for name in OLD_SCRIPTS:
        SK.remove_script(name)


def write_shardstones(rows):
    lines = ["; The shardstones (dsengine/shardcraft.py): [Key] (its place is its map's Id Waystone_<Key>, a player's",
             "; attunement the attribute Waystone.<Key>) and the name it's shown by. Shards.ini Shardstone.<Key> is",
             "; what activating it costs. Written by dev\\migrate\\build_estforlan.py (estforlan/story.py).", ""]
    for key, title in rows:
        lines += ["[%s]" % key, "Title=%s" % title, ""]
    SK.write_text(p("data", "Shardstones.ini"), lines)
    print("data\\Shardstones.ini: %d shardstones" % len(rows))


def skill_scripts():
    for skill, text in SKILL_TEXT.items():
        SK.write_script("%s Skill" % skill, [("Display.Message", "Cyan", text), ("End",)], MAKER)


def main():
    ents = Ini(p("data", "Entities.ini"))
    gear = gear_list(ents)
    art(gear)
    sounds()
    data(gear)
    shardstones()
    skill_scripts()
    print("Shardcraft: done")


if __name__ == "__main__":
    main()
