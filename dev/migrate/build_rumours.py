"""What townsfolk say of the quests you could start (dsengine/rumours.py): each side quest's Rumour= (and Rumour.2=)
in Quests.ini, the kinds who gossip (Entities.ini Gossip=1) and how often (Config.ini [Rumours]). Edit the words in
Quests.ini: what's there is kept (only a quest with no rumour yet gets one). The main story has none: it's found, not
told.

Safe to run again.

  python -I "dev\\migrate\\build_rumours.py"
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import Ini, p                        # noqa: E402

RUMOURS = {
    "The Smugglers' Run": ["Sergeant Holt at the castle's south gate is tearing his hair out. Goods turn up in town that "
                           "never came through his gate."],
    "Granny Wren's Walk": ["There's an old dear down at Northport's landing who looks like she's lost her way. Somebody "
                           "ought to see her home."],
    "A Portrait of Mo": ["That painter in Ashford's market square can't get his sitter to sit still. Mo, the sitter's "
                         "called. I won't say more."],
    "The Wardhaven Bridge": ["Mayor Hollis in Ashford is after help with the Wardhaven bridge. Hands are short, I hear."],
    "The Dragonforge": ["The Wyrmsmith over in Wardhaven wants someone brave. Something about a forge hot enough for "
                        "dragon scale."],
    "The Shard Scholar": ["Magister Quill at the Wizards' Court talks about nothing but Shards. He's always wanting "
                          "something fetched."],
    "The Spellwright": ["They say Magister Quill can teach a body to write a spell of their own, if you help him first."],
    "The Invisible Apprentice": ["Folk at the Wizards' Court say there's a voice in the great hall with nobody attached "
                                 "to it."],
    "Lady Pettigrew's Hat": ["There's a lady out on Goose Green, east of Northport, losing a war with some geese.",
                             "Lady Pettigrew's been shouting at geese all morning. The geese are winning."],
    "Granny Bramble's Practice Hex": ["Granny Bramble on Thornwick's green wants someone to practise a hex on. Don't "
                                      "stand still near her."],
    "The Scarecrow's Hat": ["The scarecrow outside Oakhollow has been talking again. Big questions, apparently. Very "
                            "big."],
    "Duchess Has Opinions": ["There's a cow outside Ashford with opinions, and she says them out loud."],
    "The Mayor's Missing Trousers": ["Constable Dobbs in Ashford has a case he won't talk about. Something to do with "
                                     "the Mayor. And trousers."],
    "The Redrock Signet": ["An old steward sits by the road at Redrock Manor's gate, waiting for someone brave enough to "
                           "go in."],
    "The Herbalist's Remedy": ["The herbalist out on Ashford's farmlands could do with a hand, I hear."],
    "The Dwarf's Grudge": ["Miners swear there's a dwarf deep under the hobgoblin warren, nursing a grudge as old as the "
                           "hills."],
    "The Wildwood Watch": ["Ranger Ash in Oakhollow is short of eyes in the Wildwood. Strange goings on, they say."],
    "Wolves of the Greyflats": ["The shepherd in Greyford is losing sheep to the wolves on the Greyflats.",
                           "Wolves on the Greyflats again. The Greyford shepherd's at his wits' end."],
    "Bog Lights": ["Old Morwen the witch in Saltmarsh wants bog myrtle, and someone daft enough to fetch it."],
    "Bandits on the Road": ["Captain Hale in Frosthold wants the bandits off the Redrock road, and he's paying."],
    "The Lost Caravan": ["Qadir the merchant in Dunerest has lost a whole caravan in the Sunscar. A whole one!"],
    "The Frozen Forge": ["Brann the forgemaster in Frosthold can't keep his forge lit, and he's not taking it well."],
    "The Hermit's Fire": ["The hermit in the Isle's western woods could do with good wood for his fire."],
    "The Withering Wood": ["The druid in Thornwick says the Elderwood is dying, and nobody listens."],
    "The Barrow King": ["The gravekeeper at King Rupert's Keep won't go near the barrows on the downs any more. Says "
                        "they've woken."],
    "Old Hob": ["Old Hob of Oakhollow's gone missing, and his house is boarded up tight. Odd, that."],
    "The Lost Patrol": ["The scout in Emberwatch is waiting on a patrol that never came back from the Ashwold."],
    "A Place of Your Own": ["There's a settler by Ashford's shardstone talking about a place of your own. Land you can't "
                            "walk to, whatever that means."],
}
GOSSIPS = ("Villager", "Man", "Woman", "Farmer", "Barkeep", "Barmaid", "Greengrocer", "Fishmonger", "Butcher", "Baker",
           "Clerk", "Blacksmith", "Doctor", "Nurse", "Banker", "Trader", "Settler", "Merchant", "Shepherd", "Tailor",
           "Cobbler", "Hotelier", "Carter", "Guard", "Shopkeeper", "Fisherman", "Miner", "Herbalist", "Old_Woman")
CONFIG = [("On", "1", "1 = townsfolk who gossip (Entities.ini Gossip=1) now and then mention a quest you could start"),
          ("Every.Minutes", "8", "No more than one rumour every this many minutes"),
          ("Chance", "35", "In 100: when one's due, how often talking to a gossip brings one"),
          ("Times", "2", "How many times you'll hear about the same quest")]


def main():
    quests = Ini(p("data", "Quests.ini"))
    told = 0
    for name, said in RUMOURS.items():
        if quests.section(name) is None or quests.get(name, "Rumour") is not None:
            continue
        for i, text in enumerate(said):
            quests.set(name, "Rumour" if i == 0 else "Rumour.%d" % (i + 1), text)
        told += 1
    quests.save(p("data", "Quests.ini"))
    ents = Ini(p("data", "Entities.ini"))
    for kind in GOSSIPS:
        if ents.section(kind) is not None:
            ents.set(kind, "Gossip", "1")
    ents.save(p("data", "Entities.ini"))
    path = p("data", "Config.ini")                       # (added as text: the rest of the file as it's written)
    text = open(path, "rb").read().decode("cp1252")
    if "[Rumours]" not in text:
        lines = ["", "[Rumours]"] + [x for k, v, note in CONFIG for x in (";" + note, "%s=%s" % (k, v))]
        open(path, "wb").write((text.rstrip("\r\n") + "\r\n" + "\r\n".join(lines) + "\r\n").encode("cp1252"))
    print("Rumours: %d quests given theirs" % told)


if __name__ == "__main__":
    main()
