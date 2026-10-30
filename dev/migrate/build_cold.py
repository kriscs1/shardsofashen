"""The cold (dsengine/cold.py): out on snow or ice and not warm, health drops a little at a time. So wool has a use.

  * data\\Cold.ini: how long before it bites, how often, how much, how near a fire warms you, the ground that's cold
    (only the keys missing are added: edit them there).
  * Warm things (Entities.ini Warm=1): the Fur Cap; a Wool Hood and Wool Mittens, made at a workbench from balls of
    wool (Crafting); a Warming Draught, brewed of emberroot and marigold (Alchemy: herbs, so a potion, inside you): it
    keeps the cold off for Draught.Minutes (WarmUntil).
  * Their pictures: the hood and mittens the fur cap's and leather gloves' in cream wool (worn too), the draught a
    healing draught gone ember-orange.

Safe to run again.

  python -I "dev\\migrate\\build_cold.py"
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import Ini, p                      # noqa: E402
import sprite_kit as K                         # noqa: E402
import story_kit as SK                         # noqa: E402

MAKER = "build_cold.py"
COLD = [("Grace", "20", "Seconds out in the cold before it bites; then Damage hitpoints every Every seconds"),
        ("Every", "8", None), ("Damage", "1", None),
        ("Fire.Range", "96", "How near a fire (pixels) warms you; the ground that's cold (tiles starting so)"),
        ("Tiles", "Snow,Ice", None),
        ("Draught.Minutes", "10", "How long a Warming Draught keeps the cold off")]
ITEMS = {
    "Wool_Hood": [("Type", "MapItem"), ("Display.Name", "Wool Hood"), ("Slot", "Head"), ("Attack", "0"),
                  ("Defence", "1"), ("Warm", "1"), ("Stackable", "1"), ("Value", "30"), ("Durability", "120"),
                  ("Examine.Info", "A thick hood of spun wool. Warm as a hearth.")],
    "Wool_Mittens": [("Type", "MapItem"), ("Display.Name", "Wool Mittens"), ("Slot", "Hands"), ("Attack", "0"),
                     ("Defence", "0"), ("Warm", "1"), ("Stackable", "1"), ("Value", "20"), ("Durability", "100"),
                     ("Examine.Info", "Mittens of spun wool, no fingers to speak of, and warm.")],
    "Warming_Draught": [("Type", "MapItem"), ("Display.Name", "Warming Draught"), ("Use.Words", "Drink"),
                        ("Stackable", "5"), ("Value", "18"),
                        ("Examine.Info", "Emberroot and marigold: it burns all the way down and keeps burning.")],
}
RECIPES = [("CRAFT-Crafting", "Wool_Hood,Ball_of_Wool 3,0.3,3"), ("CRAFT-Crafting", "Wool_Mittens,Ball_of_Wool 2,0.25,2"),
           ("CRAFT-Potion_Making", "Warming_Draught,Emberroot 1 Marigold 1 Empty_Vial 1,0.6,5")]
WOOL, EMBER = (232, 222, 196), (236, 120, 40)


def tint(img, col, keep_dark=0.22):
    """Every pixel the colour col, as light or dark as it was (the outline left dark)."""
    out = []
    for row in img:
        r2 = []
        for c in row:
            if c is None:
                r2.append(None)
                continue
            lum = sum(c[:3]) / 765.0
            r2.append(c if lum < keep_dark else tuple(min(255, int(v * (0.35 + 0.8 * lum))) for v in col))
        out.append(r2)
    return out


def pictures():
    n = 0
    for name, src, col in (("Wool_Hood", "Fur_Cap", WOOL), ("Wool_Mittens", "Leather_Gloves", WOOL)):
        n += K.save("Entities", name, tint(K.load("Entities", src), col))
        for f in os.listdir(p("sprites", "Worn")):
            if f.startswith("Worn_%s" % src) and f.endswith(".png"):
                n += K.save("Worn", f[:-4].replace(src, name), tint(K.load("Worn", f[:-4]), col))
    img = K.load("Entities", "Healing_Draught")
    liquid = [[(EMBER if c is not None and c[0] < c[2] and sum(c) > 200 else c) for c in row] for row in img]
    n += K.save("Entities", "Warming_Draught", liquid)
    print("Pictures: %d written" % n)


def data():
    path = p("data", "Cold.ini")
    if not os.path.exists(path):
        open(path, "wb").write(b"; The cold (dsengine/cold.py). Written by dev\\migrate\\build_cold.py: edit the numbers "
                               b"here.\r\n")
    ini = Ini(path)
    for key, value, note in COLD:
        if ini.get("Cold", key) is None:
            s = ini.section("Cold", create=True)
            if note:
                s[1].append((None, "; " + note))
            s[1].append((key, value))
    ini.save(path)
    ents = Ini(p("data", "Entities.ini"))
    ents.set("Fur_Cap", "Warm", "1", overwrite=False)
    for name, keys in ITEMS.items():
        for k, v in keys:
            ents.set(name, k, v, overwrite=False)
    ents.save(p("data", "Entities.ini"))
    racks = Ini(p("data", "ItemRacks.ini"))
    for sec, line in RECIPES:
        items = [v for k, v in racks.section(sec)[1] if k and k.startswith("Item")]
        if any(v.split(",")[0] == line.split(",")[0] for v in items):
            continue
        racks.set(sec, "Item%d" % (len(items) + 1), line)
    racks.save(p("data", "ItemRacks.ini"))


def scripts():
    minutes = float(Ini(p("data", "Cold.ini")).get("Cold", "Draught.Minutes") or 10)   # (written in: from Cold.ini)
    SK.write_script("Drink Warming_Draught", [
        ("Take.Item", "Warming_Draught", "1"),
        ("Play.Sound", "EatFood"),
        ("Get.Value", "CALCULATION", "$Clock+%d" % int(minutes * 60), "Variable.1$"),
        ("Update.Attribute", "WarmUntil", "=$Variable.1"),
        ("Display.Message", "Cyan", "It burns all the way down, and the warmth spreads out to your toes.", "-"),
        ("End",)], MAKER)


def main():
    data()
    pictures()
    scripts()
    print("The cold: done")


if __name__ == "__main__":
    main()
