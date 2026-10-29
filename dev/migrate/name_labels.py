"""What the player sees things called, put right where a thing's own name doesn't read well (Display.Name=; its name
stays what scripts, saves and pictures go by): the apostrophes the names can't have (Chef's Hat, Hob's Diary), a state
that's only for the game (Market Stall Open, Shardstone Dormant: a market stall, a shardstone), a picture's parts (a
shelf against a thin wall, Herb_Rack_Brick_Thin_Plank001: a herb rack). Safe to run again; a Display.Name already set
is left as it is.
Usage: python -I dev/migrate/name_labels.py"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import Ini, p  # noqa: E402

ENTITIES = {
    "Gold_Coin(s)": "Gold Coins", "Archivists_Attestation": "Archivist's Attestation",
    "Beggars_House_Key": "Beggar's House Key", "Chancellors_Warrant": "Chancellor's Warrant", "Chefs_Hat": "Chef's Hat",
    "Fathers_Compass": "Tobias's Compass", "Fathers_House_Key": "Tobias's House Key", "Mayors_Pass": "Mayor's Pass",
    "Spellwrights_Page": "Spellwright's Page", "Hobs_Diary": "Hob's Diary", "Carpenters_Bench": "Carpenter's Bench",
    "Market_Stall_Open": "Market Stall", "Barred_Niche_Empty": "Barred Niche", "Caged_Tobias": "Tobias",
    "Hob_Cage_Open": "Cage", "Sleeping_Jimmy": "Jimmy", "Empty_Lectern": "Lectern", "Deep_Stairs_Down": "Stairs Down",
    "Deep_Stairs_Up": "Stairs Up", "Shardstone_Dormant": "Shardstone",
}
FURNITURE = {"Shelf_Goods": "Shelf of Goods"}             # (a family's name, if not just its words)
FAMILIES = ("Bookshelf", "Potted_Plant", "Bed", "Shelf_Goods", "Herb_Rack", "Potion_Shelf", "Nets")   # (wall_furniture.py)


def main():
    ents = Ini(p("data", "Entities.ini"))
    n = 0
    for name, shown in ENTITIES.items():
        if ents.section(name) and not ents.has(name, "Display.Name"):
            ents.set(name, "Display.Name", shown)
            n += 1
    ents.save(p("data", "Entities.ini"))
    tiles = Ini(p("data", "Tiles.ini"))
    for sec, _ in tiles.sections:
        shown = ""
        m = re.fullmatch(r"(%s)_\w+?_Thin_(?:Plank|Tile|Marble)\d{3}" % "|".join(FAMILIES), sec)   # (against a wall)
        if m:
            fam = m.group(1)
            shown = FURNITURE.get(fam, fam.replace("_", " "))
            if tiles.get(sec, "Display.Name") != shown:
                tiles.set(sec, "Display.Name", shown)
                n += 1
            continue
        elif re.fullmatch(r"Shelf_Goods\d{3}", sec):
            shown = FURNITURE["Shelf_Goods"]
        elif re.fullmatch(r"Door_Open\d{3}", sec):                                  # (a door, open)
            shown = "Door"
        if shown and not tiles.has(sec, "Display.Name"):
            tiles.set(sec, "Display.Name", shown)
            n += 1
    tiles.save(p("data", "Tiles.ini"))
    print("Display names: %d set" % n)


if __name__ == "__main__":
    main()
