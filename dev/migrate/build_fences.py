"""Stolen goods and the fences who buy them (dsengine/thieving.py, dev\\Roadmap-6.md group 3):

  * data\\Thieving.ini [Fence]: what a fence gives for stolen goods (a share of what an honest shop would), and
    [Fence.<rack>] a fence's own (Red Meg: better, and best to those on her side). Only the keys missing are added.
  * data\\ItemRacks.ini: Fence=1 on Red Meg's goods, and the two new fences' own.
  * The smugglers' side (Side=Smugglers: the Smuggler kind and Red Meg), for Red Meg's best price.
  * The fences: Wick, who walks Northport's docks at night (the man who was already there), and Old Sully in the corner
    of a Galaith tavern (-7,15,0), each with their Talk script.

Safe to run again.

  python -I "dev\\migrate\\build_fences.py"
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_isle import Map                     # noqa: E402
from build_stealth import ini_keys             # noqa: E402
import story_kit as K                          # noqa: E402

MAKER = "build_fences.py"

FENCE = [   # data\Thieving.ini: (section, key, value, what it means)
    ("Fence", "Rate", "0.5", "What a fence gives for stolen goods (its rack has Fence=1): this share of an honest "
                             "shop's price; its own, [Fence.<rack>] (Side.Rate: to those on its side)"),
    ("Fence.SHOP-Smugglers", "Rate", "0.6", "Red Meg"),
    ("Fence.SHOP-Smugglers", "Side", "Smugglers", None),
    ("Fence.SHOP-Smugglers", "Side.Rate", "0.8", None),
]

RACKS = {
    "SHOP-Fence_Northport": ["Type=Shop", "Buy.Rate=1.3", "Sell.Rate=0.8", "Specific=0", "Fence=1",
                             "Item1=Silver_Ring,1", "Item2=Sapphire,1", "Item3=Owl_Potion,2"],
    "SHOP-Fence_Galaith": ["Type=Shop", "Buy.Rate=1.3", "Sell.Rate=0.8", "Specific=0", "Fence=1",
                           "Item1=Gold_Ring,1", "Item2=Silver_Ring,2", "Item3=Emerald,1"],
}

WICK = "NPC\tMan\t512\t256\tAttitude=Good Zone=14,7,24,9 Schedule=Night"      # (Northport's docks, by night)
SULLY = ("NPC\tMan\t704\t216\tAttitude=Good Stand=1 Face=W Schedule=Always Id=Galaith_Fence Name=Old_Sully "
         "Look=0")                                                             # (as drawn: all in dark cloth)


def thieving():
    ini_keys("Thieving.ini", FENCE, "")


def smugglers():
    K.section(K.ENTS, "Smuggler", [("Side", "Smugglers")])
    m = Map("17,4,0")
    for i, ln in enumerate(m.ents):
        if ln.startswith("NPC	") and "Id=Red_Meg" in ln.split("	")[-1].split() and "Side=" not in ln:
            m.ents[i] = ln + " Side=Smugglers"
            m.save()
            print("17,4,0: Red Meg is on the smugglers' side")


def racks():
    K.section(K.RACKS, "SHOP-Smugglers", [("Fence", "1")])           # (Red Meg: the best of them)
    for name, lines in RACKS.items():
        K.set_section(K.RACKS, name, lines, after="SHOP-Smuggler")


def place():
    m = Map("4,4,0")
    if not K.has_id(m, "Northport_Fence"):
        at = [i for i, ln in enumerate(m.ents) if ln.startswith(WICK)]
        assert at, "4,4,0: the man on the docks at night isn't there"
        m.ents[at[0]] = WICK + " Id=Northport_Fence Name=Wick"
        m.save()
        print("4,4,0: Wick, on the docks at night")
    m = Map("-7,15,0")
    if not K.has_id(m, "Galaith_Fence"):
        m.ents.append(SULLY)
        m.save()
        print("-7,15,0: Old Sully, in the tavern's corner")


def scripts():
    K.write_script("Talk to Northport_Fence", [
        K.say("Man", "Evening. Not many come down the docks this late with nothing to sell.\\I don't ask where a "
                      "thing's been, and I don't remember faces. It costs you a little off the price, that's all.",
              ("Let's see what you'll give me.", "@shop"), ("Goodbye.", "@end")),
        ("@shop",),
        ("Display.Item.Rack", "GENERAL", "Man", "SHOP-Fence_Northport", "@end"),
        ("@end",),
        ("End",),
    ], MAKER)
    K.write_script("Talk to Galaith_Fence", [
        K.say("Man", "Keep your voice down. Rings, stones, a lord's silver spoons: whatever found its way into "
                           "your pack, I'll find it a new home.\\Less than it's worth, mind. That's what no questions "
                           "cost.",
              ("Show me.", "@shop"), ("Goodbye.", "@end")),
        ("@shop",),
        ("Display.Item.Rack", "GENERAL", "Man", "SHOP-Fence_Galaith", "@end"),
        ("@end",),
        ("End",),
    ], MAKER)


def main():
    smugglers()
    thieving()
    racks()
    place()
    scripts()
    print("Fences: done")


if __name__ == "__main__":
    main()
