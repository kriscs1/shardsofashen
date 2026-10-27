"""Feathers, frost spells and the shardstones' sparkle.

  * Feather: hens and ducks drop them (the dairy and the farm sell them too), and arrows are fletched with three.
  * Three spells that strike every foe round you and hold them still (Spells.ini Freeze=seconds; Freeze.Word: frozen
    or stunned; Entities.ini Freeze.Immune=1 for the bosses): Frost Nova, Thunderclap and Blizzard, their scrolls
    written at the scroll desk and sold by the wizards.
  * The shardstones twinkle: a star at the tip (Shardstone1..4, drawn by build_sprites.py).
  * Their sounds, synthesised: Freeze (ice forming, a crack) and Thunderclap (a crack, a boom).

Safe to run again: it sets what it adds and leaves the rest alone.

  python -I "dev\\migrate\\build_feathers_and_frost.py"
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import Ini, p                      # noqa: E402
import build_sounds as SND                     # noqa: E402
import build_sprites as BS                     # noqa: E402
import sprite_kit as K                         # noqa: E402

ART = ["Feather", "Frost_Nova_Scroll", "Thunderclap_Scroll", "Blizzard_Scroll"] + ["Shardstone%d" % i for i in range(1, 5)]

SPELLS = [   # (name, scroll value, what it does for the scroll's text, its Spells.ini keys)
    ("Frost_Nova", 45, "a ring of frost bursts out from you, freezing every foe within three tiles for 5 seconds",
     dict(Cost="10", Cooldown="15", Scroll="Frost_Nova_Scroll", Effect="Area", Level="6", Damage="2-5", Radius="96",
          Freeze="5", **{"Freeze.Word": "frozen"}, Impact="Ice_Burst", Sound="Freeze", XP="0.6")),
    ("Thunderclap", 70, "a clap of thunder stuns every foe within four tiles for 2 seconds",
     dict(Cost="14", Cooldown="20", Scroll="Thunderclap_Scroll", Effect="Area", Level="9", Damage="4-9", Radius="128",
          Freeze="2", **{"Freeze.Word": "stunned"}, Impact="Spark", Sound="Thunderclap", XP="0.8")),
    ("Blizzard", 150, "a howling blizzard freezes every foe within five tiles for 4 seconds",
     dict(Cost="22", Cooldown="40", Scroll="Blizzard_Scroll", Effect="Area", Level="13", Damage="6-12", Radius="160",
          Freeze="4", **{"Freeze.Word": "frozen"}, Impact="Ice_Burst", Sound="Freeze", XP="1.1")),
]
RECIPES = {   # CRAFT-Scrolls: scroll -> ingredients, XP, level
    "Frost_Nova_Scroll": "Blank_Scroll 1 Bucket_of_Water 2 Sapphire 1,0.6,6",
    "Thunderclap_Scroll": "Blank_Scroll 1 Silver_Bar 1 Coal 2,0.8,9",
    "Blizzard_Scroll": "Blank_Scroll 1 Sapphire 2 Bucket_of_Water 2,1.1,13",
}
STOCK = {     # shop -> [(item, stock)] added when missing
    "SHOP-Wizard": [("Frost_Nova_Scroll", "3"), ("Thunderclap_Scroll", "2")],
    "SHOP-Wardhaven": [("Blizzard_Scroll", "3")],
    "SHOP-Dairy": [("Feather", "40")],
    "SHOP-Farm": [("Feather", "40")],
}
DROPS = {"Chicken": "Feather,1-3,100", "Duck": "Feather,1-2,100"}
IMMUNE = ("Dragon", "Galaith_Dragon", "Valour_Guardian", "Ashen_Priest", "Barrow_King")
ARROWS_OLD = "Arrows,Logs 1 Bronze_Bar 1,"
ARROWS_NEW = "Arrows,Logs 1 Bronze_Bar 1 Feather 3,"

SOUNDS = {
    # ice forming: a glassy shimmer climbing, and the crack of it setting
    "Freeze": lambda: SND.mix((SND.arpeggio([1568, 2093, 2637, 3136, 4186], 0.06, 0.9, decay=4.0), 0.5),
                              (SND.shaped(SND.noise(31, SND.n(0.9), 0.5, high=0.6), 0.2, 3.5), 0.25),
                              (SND.shaped(SND.noise(32, SND.n(0.12), 0.9, high=0.8), 0.001, 30, delay=0.35), 0.7)),
    # a sharp crack, then the boom rolling off
    "Thunderclap": lambda: SND.mix((SND.shaped(SND.noise(33, SND.n(0.15), 0.95, high=0.7), 0.001, 26), 0.9),
                                   (SND.shaped(SND.noise(34, SND.n(1.1), 0.04), 0.01, 3.0, delay=0.04), 0.9),
                                   (SND.shaped(SND.tone(55, SND.n(1.0), glide=-0.3), 0.01, 3.5, delay=0.04), 0.5)),
}


def scroll_text(spell, info, d):
    return ("A scroll of %s: %s (%s damage). Magic %s. Right-click it and Cast, or use it on a monster."
            % (spell.replace("_", " "), info, d["Damage"], d["Level"]))


def add_items(ini, sec, items):
    """Appends ItemN=item,rest to a rack for each item not in it yet."""
    s = ini.section(sec)
    if s is None:
        print("  !! no [%s] in ItemRacks.ini" % sec)
        return
    have = {v.split(",")[0] for k, v in s[1] if k and k.lower().startswith("item")}
    n = sum(1 for k, v in s[1] if k and k.lower().startswith("item"))
    for name, rest in items:
        if name not in have:
            n += 1
            ini.set(sec, "Item%d" % n, "%s,%s" % (name, rest))


def main():
    for name in ART:
        print(("wrote " if K.save("Entities", name, BS.SPRITES[name]()) else "unchanged ") + name)
    for name, fn in SOUNDS.items():
        blob = SND.wav_bytes(fn())
        path = p("sounds", name + ".wav")
        if not (os.path.exists(path) and open(path, "rb").read() == blob):
            with open(path, "wb") as f:
                f.write(blob)
            print("wrote sounds\\%s.wav" % name)

    ents = Ini(p("data", "Entities.ini"))
    for key, value in (("Type", "MapItem"), ("Examine.Info", "A grey goose feather. Arrows are fletched with them."),
                       ("Stackable", "999"), ("Value", "1")):
        ents.set("Feather", key, value)
    for spell, value, info, d in SPELLS:          # (only what's missing: build_shards.py sets their price and words)
        for key, v in (("Type", "MapItem"), ("Use.Words", "Cast"), ("Examine.Info", scroll_text(spell, info, d)),
                       ("Stackable", "10"), ("Value", str(value)), ("Spell", spell)):
            ents.set(d["Scroll"], key, v, overwrite=False)
    for npc, drop in DROPS.items():
        drops = ents.get(npc, "Drops") or ""
        if "Feather," not in drops:
            ents.set(npc, "Drops", (drops + " " + drop).strip())
    for npc in IMMUNE:
        if ents.section(npc) is not None:
            ents.set(npc, "Freeze.Immune", "1")
    ents.set("Shardstone", "Anim.Frames", "4")
    ents.set("Shardstone", "Anim.Speed", "180")
    ents.save(p("data", "Entities.ini"))

    spells = Ini(p("data", "Spells.ini"))
    for spell, value, info, d in SPELLS:          # (likewise: their Shards and cooldowns are build_shards.py's)
        for key, v in d.items():
            spells.set(spell, key, v, overwrite=False)
    spells.save(p("data", "Spells.ini"))

    racks = Ini(p("data", "ItemRacks.ini"))
    s = racks.section("CRAFT-Crafting")
    s[1] = [(k, ARROWS_NEW + v[len(ARROWS_OLD):] if k and v.startswith(ARROWS_OLD) else v) for k, v in s[1]]
    add_items(racks, "CRAFT-Scrolls", list(RECIPES.items()))
    for shop, items in STOCK.items():
        add_items(racks, shop, items)
    racks.save(p("data", "ItemRacks.ini"))
    print("Feathers, %d spells and the shardstones' sparkle: done" % len(SPELLS))


if __name__ == "__main__":
    main()
