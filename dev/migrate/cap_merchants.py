"""At most two merchants of a trade in a settlement (CLAUDE.md): the two nearest the square keep their trade (a market
stall first, then the shops the town was built round first: the lowest Ids); the others' shops are shut. A shopkeeper
past the two stays at home behind their counter and says why; a tavern past the two is an inn now, its kitchen shut,
its rooms still let. A trade is what's sold, whoever sells it: a market stall's meat and a butcher's shop are both the
butcher's trade. Run it again: it does nothing more (the shut ones sell nothing, so they don't count).

  python -I "dev\\migrate\\cap_merchants.py"
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import story_kit as K  # noqa: E402
from story_kit import say  # noqa: E402

CAP = 2
MAKER = "cap_merchants.py"
SCRIPTS = os.path.join(K.ROOT, "data", "Scripts")
MAPS = os.path.join(K.ROOT, "maps")
# what a rack sells, as a trade (the racks not here are each a trade of their own)
TRADES = {"SHOP-Baker": "baker", "SHOP-Bakery": "baker", "SHOP-Butchery": "butcher", "SHOP-Market_Butcher": "butcher",
          "SHOP-Fishmongery": "fish", "SHOP-Market_Fishmonger": "fish", "SHOP-Greengrocery": "greens",
          "SHOP-Market_Greengrocer": "greens", "SHOP-Pub": "pub"}
STALLS = ("SHOP-Baker", "SHOP-Market_")          # (a market stall's racks: on the square, so kept first)
# a shut shop's keeper, by their trade: what they say ("TOWN": the settlement)
SHUT = {
    "baker": "Shut, I'm afraid. There's a bakery by the square, and a town can only eat so much bread. I bake for my "
             "own table now, and very good it is too.",
    "butcher": "The shop's shut. Two butchers nearer the square, and not enough sausages in TOWN to go round three. "
               "I keep the cleaver sharp, though. Habit.",
    "fish": "Closed for good. The fish all go to the stalls by the square now. The smell, sadly, stayed here.",
    "greens": "No more greens, I'm afraid. The market sells the cabbages now. I grow roses. Nobody haggles over roses.",
    "SHOP-Armour": "The forge is cold. Two armourers in one street was one too many; I lost the coin toss. Mind the "
                   "anvil.",
    "SHOP-Weapons": "Shut. Too many swords, not enough wars. I'm told that's a good thing.",
    "SHOP-Cobbler": "I've hung up my last. The other cobblers have the town's feet well in hand. Feet? Well shod, then.",
    "SHOP-Tailor": "The shop's shut. Two tailors in TOWN sew all it needs. I take in my own trousers now.",
}
SHUT_ANY = "The shop's shut for good, I'm afraid. You'll find what you need nearer the square."


def read(path):
    return open(path, "rb").read().decode("cp1252")


def merchants():
    """{(settlement, trade): [(its kept order, Id, rack, script text)]} of everyone who sells (a Display.Item.Rack in
    their Talk to script) on a map."""
    racks = {}
    for fn in os.listdir(SCRIPTS):
        if fn.startswith("Talk to ") and fn.endswith(".txt"):
            text = read(os.path.join(SCRIPTS, fn))
            found = re.findall(r"Display\.Item\.Rack\t\S+\t\S+\t(SHOP-\S+)", text)
            if found:
                racks[fn[8:-4]] = (found[0], text)
    out = {}
    for fn in os.listdir(MAPS):
        if not fn.endswith(".txt"):
            continue
        for line in read(os.path.join(MAPS, fn)).split("\r\n"):
            p = line.split("\t")
            m = re.search(r"\bId=(\S+)", p[4]) if p[0] == "NPC" and len(p) > 4 else None
            if not m or m.group(1) not in racks:
                continue
            pid = m.group(1)
            rack, text = racks[pid]
            place, n = pid.split("_")[0], re.search(r"_(\d+)$", pid)
            key = (0 if rack.startswith(STALLS) else 1, int(n.group(1)) if n else 0, pid)
            out.setdefault((place, TRADES.get(rack, rack)), []).append((key, pid, rack, text))
    return out


def town_title(place):
    return {"Court": "the Court", "Keep": "the Keep"}.get(place, place)


def shut(pid, place, trade, rack, text):
    """pid's Talk to script, their shop shut: an inn for a tavern (its rooms), a word at home for a shop."""
    who = re.search(r"Display\.Conversation\t(\S+)\t", text).group(1)
    if trade == "pub":
        name = re.search(r"Welcome to (.+?)! ", text)
        price = re.search(r"A room for the night \((\d+) gold\)", text)
        name, price = (name.group(1) if name else "the inn"), int(price.group(1)) if price else 5
        rows = [say(who, "Welcome to %s! The kitchen's shut for good: two taverns feed all of %s. But a bed's a bed, "
                         "and ours are the softest in town." % (name, town_title(place)),
                    ("A room for the night (%d gold)." % price, "@room"), ("Goodbye.", "@end")),
                ("@room",), (">Got.Item", "Gold_Coin(s)", str(price), "@poor"),
                ("Take.Item", "Gold_Coin(s)", str(price)),
                ("Display.Message", "Cyan", "You take a room upstairs and sleep the night through.", "-"),
                ("Sleep", "Morning"), ("End",),
                ("@poor",), ("Display.Refusal", "You need %d gold coins for a room." % price),
                ("@end",), ("End",)]
    else:
        rows = [say(who, SHUT.get(trade, SHUT.get(rack, SHUT_ANY)).replace("TOWN", town_title(place)),
                    ("Goodbye.", "@end")),
                ("@end",), ("End",)]
    K.write_script("Talk to " + pid, rows, MAKER)


def main():
    n = 0
    for (place, trade), sellers in sorted(merchants().items()):
        sellers.sort()
        for _, pid, rack, text in sellers[CAP:]:
            shut(pid, place, trade, rack, text)
            n += 1
            print("%-10s %-14s shut: %s" % (place, trade, pid))
    print("%d shut" % n if n else "No settlement has more than %d of a trade." % CAP)


if __name__ == "__main__":
    main()
