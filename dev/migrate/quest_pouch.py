"""The Quest pouch (the owner's wish, 2026-11-12): a quest's own things (keys, letters, papers, the hat a goose took)
take no room in the pack, so a full pack can never lose one. Each is marked Quest=1 in Entities.ini; the engine keeps
them in the inventory as before (Take.Item and Use With work unchanged) but doesn't count them against its slots
(data.is_quest_item, player_items.pack_used), they can't be banked, and the page shows them in the Stats box's Quest
tab, not the pack.

  python -I "dev\migrate\quest_pouch.py"

The list is written out, not worked out from Droppable=0, so a new undroppable thing isn't swept in by running this
again; a new quest item gets Quest=1 from its own builder. Safe to run again.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from ashen import ini  # noqa: E402

ENTS = os.path.join(ROOT, "data", "Entities.ini")

POUCH = ("Beggars_House_Key", "Witch_Brew", "Caravan_Ledger", "Ferry_Ticket", "Calming_Draught", "Frost_Lily",
         "Dragonsbane", "Ashen_Sigil", "Ashen_Codex", "Chapel_Cellar_Key", "Ticket_Book", "Last_Will",
         "Amulet_of_Succession", "Lair_Key", "Fathers_House_Key", "Marys_Papers", "Fathers_Compass",
         "Parliament_Letter", "Mayors_Pass", "Archivists_Attestation", "Chancellors_Warrant", "Grimoire_of_Unbinding",
         "Solar_Key", "Valour_Seal", "Shardgate_Plans", "Fancy_Hat", "Marys_Notes", "Fenmoor_Hall_Key",
         "Redrock_Signet", "Marys_Map", "Heart_Splinter", "Wardens_Signet", "Marshals_Seal", "Seam_Hammerhead",
         "Odiles_Log", "Pells_Book", "Singing_Remnant", "Wardens_Lantern", "Caels_Lines", "Valour_Chart",
         "Frozen_Lodestar", "Cael_Confession", "Smuggled_Brandy", "Grain_Ledger", "Galaith_Treasury_Key",
         "Pallisters_Cure", "Pips_Spectacles", "Ashen_Order", "Ashen_Ledger", "Marys_Charm", "Royal_Miniature",
         "Tobias_Tin")


def main():
    changed = 0
    for name in POUCH:
        if ini.read(name, "Type", "", ENTS) != "MapItem":
            print("  not an item (left alone):", name)
            continue
        if ini.read(name, "Quest", "0", ENTS) != "1":
            ini.write(name, "Quest", "1", ENTS)
            changed += 1
    print(f"Quest=1 on {len(POUCH)} things ({changed} changed).")


if __name__ == "__main__":
    main()
