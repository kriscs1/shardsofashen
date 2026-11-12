"""Malaria (dsengine/disease.py), the owner's wish: a disease a mosquito may give you, that only a potion cures, and the
potion doesn't keep.

  * data\\Diseases.ini: how long before the first fever and how often after, and what's said (only the keys missing are
    added: edit them there). The bout itself is EFFECTS' Fever (player_combat.py).
  * Entities.ini: the Mosquito's On.Hit=Malaria (a small chance a bite; armour is no help: it's the bite that does it).
    The Fever_Tonic (Cures=Malaria Fever), good for Shelf.Minutes of real time wherever it's kept, then it's a
    Spoiled_Tonic, which you can only pour out for its vial.
  * The tonic is brewed of bog myrtle and mangrove bark (the marsh's own) (Alchemy 4), sold by the herbalist and sometimes the
    travelling salesman, and Morwen, in Saltmarsh, who knows what's wrong with you when she sees you shaking: one free,
    then for coin. So nothing in the marsh is out of reach, but it can't just sit in a bank till it's needed.
  * Pictures: a healing draught gone amber; the spoiled one murky.

Safe to run again.

  python -I "dev\\migrate\\build_malaria.py"
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import Ini, p, sound_file                      # noqa: E402
import sprite_kit as K                         # noqa: E402
import story_kit as SK                         # noqa: E402

MAKER = "build_malaria.py"
DISEASE = [("Effect", "Fever", "What a bout of it is (an effect in player_combat.py EFFECTS)"),
           ("Incubation.Seconds", "150", "How long after the bite the first bout comes; then one every so many minutes"),
           ("Every.Min.Minutes", "5", None), ("Every.Max.Minutes", "9", None),
           ("Words", "Fever comes back until it's cured: only a Fever Tonic will do it",
            "The hover by your health"),
           ("Caught", "That bite itches worse than the rest. You feel it in your blood.", "What's said, and heard"),
           ("Caught.Sound", "Buzz", None), ("Bout.Sound", "Fever_Shiver", None),
           ("Cured", "The fever goes out of your blood, and stays out.", None), ("Cured.Sound", "Fever_Cured", None)]
ITEMS = {
    "Fever_Tonic": [("Type", "MapItem"), ("Display.Name", "Fever Tonic"), ("Use.Words", "Drink"), ("Stackable", "1"),
                    ("Value", "34"), ("Shelf.Minutes", "120"), ("Spoils.To", "Spoiled_Tonic"),
                    ("Cures", "Malaria Fever"),
                    ("Examine.Info", "Bog myrtle and mangrove bark, brewed bitter. The one thing that clears marsh fever "
                                     "from the blood, and it doesn't keep.")],
    "Spoiled_Tonic": [("Type", "MapItem"), ("Display.Name", "Spoiled Tonic"), ("Use.Words", "Pour Out"),
                      ("Stackable", "1"), ("Value", "0"),
                      ("Examine.Info", "It was a fever tonic. It's cloudy now, and it smells of old ponds. The vial "
                                       "would be worth keeping.")],
}
RECIPES = [("CRAFT-Potion_Making", "Fever_Tonic,Bog_Myrtle 2 Mangrove_Bark 1 Empty_Vial 1,0.7,4")]
SHOPS = [("SHOP-Herbalist", "Fever_Tonic,2"), ("SHOP-Salesman", "Fever_Tonic,2")]
AMBER, MURK = (206, 160, 60), (92, 88, 62)
TONIC_PRICE = 45
WITCH = "Talk to Witch"


def data():
    path = p("data", "Diseases.ini")
    if not os.path.exists(path):
        open(path, "wb").write(b"; Diseases (dsengine/disease.py). Written by dev\\migrate\\build_malaria.py: edit the "
                               b"numbers and words here.\r\n")
    ini = Ini(path)
    for key, value, note in DISEASE:
        if ini.get("Malaria", key) is None:
            s = ini.section("Malaria", create=True)
            if note:
                s[1].append((None, "; " + note))
            s[1].append((key, value))
    ini.save(path)
    ents = Ini(p("data", "Entities.ini"))
    ents.set("Mosquito", "On.Hit", "Malaria 5", overwrite=False)
    for name, keys in ITEMS.items():
        for k, v in keys:
            ents.set(name, k, v, overwrite=False)
    ents.save(p("data", "Entities.ini"))
    racks = Ini(p("data", "ItemRacks.ini"))
    for sec, line in RECIPES + SHOPS:
        items = [v for k, v in racks.section(sec)[1] if k and k.startswith("Item")]
        if any(v.split(",")[0] == line.split(",")[0] for v in items):
            continue
        racks.set(sec, "Item%d" % (len(items) + 1), line)
    racks.save(p("data", "ItemRacks.ini"))


def recolour(c, col):
    """The draught's red liquid in col, as light or dark as it was; its glass, cork and outline as they are."""
    if c is None or c[0] < c[1] + 40 or c[0] < c[2] + 20:
        return c
    k = 0.45 + 0.8 * (sum(c) / 765.0)
    return tuple(min(255, int(v * k)) for v in col)


def pictures():
    n = 0
    img = K.load("Entities", "Healing_Draught")
    for name, col in (("Fever_Tonic", AMBER), ("Spoiled_Tonic", MURK)):
        n += K.save("Entities", name, [[recolour(c, col) for c in row] for row in img])
    print("Pictures: %d written" % n)


def scripts():
    SK.write_script("Pour Out Spoiled_Tonic", [
        ("Take.Item", "Spoiled_Tonic", "1"),
        ("Play.Sound", "Water_Pour" if os.path.exists(sound_file("Water_Pour")) else "Drop"),
        ("Give.Item", "Empty_Vial", "1"),
        ("End",)], MAKER)
    witch()


def witch():
    """Morwen, before her quests, when she sees you shaking (lines added after build_regions.py's; its first line goes
    round by them, so its numbers stay)."""
    path = p("data", "Scripts", WITCH + ".script")
    text = open(path, "rb").read().decode("cp1252")
    if "$Player.Malaria" in text:
        return
    lines = text.split("\r\n")
    first = "01\tGet.Value\tATTRIBUTE\tHobQuest\tVariable.4$"
    assert first in lines, "Talk to Witch's first line has changed"
    lines[lines.index(first)] = "01\tGoto.Line\t52"
    while lines and not lines[-1].strip():
        lines.pop()
    lines += [
        "52\tGet.Value\tATTRIBUTE\tHobQuest\tVariable.4$",
        "53\t>Conditional\t$Player.Malaria=1\t02",
        "54\tGet.Value\tATTRIBUTE\tMorwenFeverGift\tVariable.3$",
        "55\t>Conditional\t$Variable.3=0\t60",
        "56\tDisplay.Conversation\tWitch\tLook at the shake on you, and that yellow in your eye. Marsh fever, dearie: "
        "malaria, the Court's wizards call it, the mosquitoes put it in your blood. It won't leave of itself, and dying "
        "won't shift it either.\\Here, a tonic, drink it while it's good. It turns in a few days, so there's no keeping "
        "it by. Bog myrtle and mangrove bark, if you've to brew your own.\tThank you.\t57",
        "57\tUpdate.Attribute\tMorwenFeverGift\t=1",
        "58\tGive.Item\tFever_Tonic\t1",
        "59\tEnd",
        "60\tDisplay.Conversation\tWitch\tStill shaking? A fever tonic's %d gold, fresh from the pot.\tI'll take one.\t"
        "61\tNot now.\t02" % TONIC_PRICE,
        "61\t>Got.Item\tGold_Coin(s)\t%d\t65" % TONIC_PRICE,
        "62\tTake.Item\tGold_Coin(s)\t%d" % TONIC_PRICE,
        "63\tGive.Item\tFever_Tonic\t1",
        "64\tEnd",
        "65\tDisplay.Conversation\tWitch\tMy pot's not free, dearie. Bog myrtle grows all round you, if you've the "
        "hands to brew it.\tI see.\t02",
        ""]
    open(path, "wb").write("\r\n".join(lines).encode("cp1252"))
    print("Morwen knows malaria when she sees it")


def main():
    data()
    pictures()
    scripts()
    print("Malaria: done")


if __name__ == "__main__":
    main()
