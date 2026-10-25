"""Every grave has its own name and its own inscription: a place ID on its tile (Id <name> x y, as the editor's Place
ID puts down) and a script, Data\\Scripts\\Examine <name>.txt, that reads it out. (A tile with a place ID looks for
its own scripts first: dsengine/data.py tile_place.) The graves are taken in each map's order, row by row; a map
whose graves have their names already is left alone. Inscriptions say who lies there - never a hint.

  python -I "Dev\\migrate\\name_graves.py"
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from build_isle import Map, XT, YT  # noqa: E402

GRAVES = {
    "3,1,0": [                                                         # the Isle chapel's yard
        ("Grave_Tom_Barrow", "'Here lies Old Tom Barrow. He went to sea and the sea kept him.'"),
        ("Grave_Worn_Away", "The name has worn away. The earth in front of it looks... disturbed."),
        ("Grave_Mary_Croft", "'Mary Croft, beloved mother. She baked the best pies on the Isle.'"),
        ("Grave_Ned_Pike", "'Ned Pike, ferryman. Forty years across the strait, and never lost a passenger.'"),
        ("Grave_Agnes_Reed", "'Agnes Reed. She mended every net on the Isle and swore at every gull.'"),
        ("Grave_Little_Wren", "'Little Wren, aged six. Gone to chase the butterflies.'"),
        ("Grave_Will_Hollis", "'Will Hollis, shepherd.' A little stone dog is carved at the foot of it."),
        ("Grave_Tam_Thatcher", "'Old Tam, thatcher. He built Rose Cottage the year the great storm took the pier.'"),
        ("Grave_Brother_Edric", "'Brother Edric, who kept this chapel fifty years and rang its bell every dawn.'"),
        ("Grave_Hester_Bell", "'Hester Bell, midwife. Half the Isle came into the world through her hands.'"),
    ],
    "8,8,0": [                                                         # Ravensgate, the gravekeepers' town
        ("Grave_Osric_Raven", "'Osric Raven, first gravekeeper of Ravensgate. He dug his own, and dug it well.'"),
        ("Grave_Elsa_Moor", "'Elsa Moor. She walked the downs at night with a lantern, so the dead had light.'"),
        ("Grave_Gideon_Sexton", "'Gideon Sexton, bell-ringer. Deaf by forty; ringing still at eighty.'"),
        ("Grave_Rowan_Twins", "'The Rowan twins. Born together, buried together. One stone was always enough.'"),
        ("Grave_Martha_Lark", "'Martha Lark, who sang at every burial in this yard but her own.'"),
        ("Grave_Snow_Traveller", "'A traveller, name unknown, found on the downs in the snow. The town paid for "
                                 "this stone.'"),
        ("Grave_Cobb_Digger", "'Cobb, digger of graves. He'd want you to know the soil here is good and soft.'"),
        ("Grave_Isolde_Ashby", "'Lady Isolde Ashby. She left her fortune to the town and her temper to her son.'"),
    ],
    "9,7,0": [                                                         # round the old king's barrow
        ("Grave_Kings_Shieldman", "Runes, worn almost smooth: '...the king's shieldman, who stood at the door.'"),
        ("Grave_Kings_Spearman", "A spear is carved on it. Beneath, in the old letters: 'He did not run.'"),
        ("Grave_Kings_Steward", "'Here waits the king's steward, until his king has need of him.' The stone is "
                                "cold to the touch."),
        ("Grave_Kings_Hound", "A small stone, carved with a hound. The old kings buried their dogs with honour."),
    ],
    "6,7,0": [                                                         # the Barrowdowns: old graves, weathered
        ("Grave_Mossed_Over", "So mossed over you can't read it. A wren has nested on top."),
        ("Grave_Aldwin_Shepherd", "'Aldwin, shepherd of the downs. His flock outlived him by a winter.'"),
        ("Grave_Three_Sisters", "Three names, sisters by the look of it, and one date for all three. A hard winter."),
        ("Grave_Old_Bowman", "A bow is carved on it, and one word in the old tongue: 'Steady.'"),
        ("Grave_Cracked_Stone", "The stone has cracked clean in two. Someone has tied the halves together with rope."),
        ("Grave_Road_Walker", "'Here lies one who walked every road on the downs, and rests at last beside this one.'"),
        ("Grave_Godric_Miller", "'Godric Miller. The wind took his mill, and then the wind took him.'"),
        ("Grave_Wooden_Horse", "A tiny stone. A wooden horse lies in front of it, bleached white by the sun."),
        ("Grave_Ford_Holder", "'Fell at the ford, holding it.' No name: only a sword, scratched into the stone."),
    ],
    "7,8,0": [
        ("Grave_Hill_Poet", "'I loved these hills. Bury me where I can see them.' The stone faces the sunrise."),
        ("Grave_Hal_And_Bryony", "Two names in a ring of carved ivy: Hal and Bryony."),
    ],
    "8,7,0": [
        ("Grave_Old_Wat", "'Old Wat, who lived alone and liked it. Leave him be.'"),
        ("Grave_Raven_Mark", "A raven is carved where a name should be: Ravensgate's mark, very old."),
    ],
    "9,8,0": [
        ("Grave_Bram_Smith", "'Bram, smith. His hammer lies with him, so he may mend things on the other side.'"),
        ("Grave_Fresh_Flowers", "No name, no date. Fresh flowers lie in front of it, though no one lives near."),
    ],
}


def main():
    named = written = 0
    for map_name, names in GRAVES.items():
        m = Map(map_name)
        graves = [(x, y) for y in range(1, YT + 1) for x in range(1, XT + 1) if m.decor(x, y).startswith("Grave")]
        if len(graves) != len(names):
            print("%s: %d graves, %d names - left alone" % (map_name, len(graves), len(names)))
            continue
        have = {(ln.split("\t")[2], ln.split("\t")[3]) for ln in m.ents if ln.startswith("Id\t")}
        added = False
        for (x, y), (pid, text) in zip(graves, names):
            if (str(x), str(y)) not in have:
                m.ents.append("Id\t%s\t%d\t%d" % (pid, x, y))
                added = True
                named += 1
            path = os.path.join(ROOT, "Data", "Scripts", "Examine %s.txt" % pid)
            if not os.path.exists(path):
                lines = ["// The grave %s on %s (Dev\\migrate\\name_graves.py)" % (pid, map_name),
                         "01\tDisplay.Message\tBlack\t%s" % text, "02\tEnd"]
                with open(path, "wb") as f:
                    f.write(("\r\n".join(lines) + "\r\n").encode("cp1252"))
                written += 1
        if added:
            m.save()
    print("Graves named: %d; their inscriptions written: %d" % (named, written))


if __name__ == "__main__":
    main()
