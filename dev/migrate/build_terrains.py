"""Terrains for the map editor's big brushes (data\\TileSets.ini, Kind=Terrain): what a stretch of grass, woodland,
marsh, water, sand, snow, ash or cave floor is made of - its ground tiles mixed (a weight after *), the decor
scattered over it (Decor.Density in a hundred of its tiles) and the creatures (Entities.Density in a hundred).
Water=1: it's water (its coasts get their diagonal pieces, TileSets.ini Kind=Shore). Face= (a wall: cave rock) the
tiles its rock shows where open ground lies south of it (as dev\migrateuild_content.py dresses the caves). The editor paints a terrain with
a brush of any size, fills an outline drawn round a place with one, and shows each as one palette entry (Auto).
The mixes are the mainland builder's (dev\\migrate\\estforlan\\land.py, life.py), so painted land matches it.

Only the terrains missing from TileSets.ini are added: a terrain changed there (in the file, or the editor's
Terrains window) is kept. Safe to run again.

  python -I "dev\\migrate\\build_terrains.py"
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PATH = os.path.join(ROOT, "data", "TileSets.ini")

# key: (title, tiles, decor, decor density, entities, entities density, water[, face])
TERRAINS = [
    ("Meadow", "meadow", "Grass001", "Flowers001*2,Flowers002*2,Flowers003*1,Tall_Grass001*4,Pebbles001*1,"
     "Pebbles002*1,Bush001*0.5,Berry_Bush001*0.3", 12, "Rabbit*3,Butterfly*2,Blue_Butterfly*1", 0.4, 0),
    ("Woodland", "woodland", "Grass001", "Tree001*30,Tree002*18,Oak_Tree001*12,Yew_Tree001*3,Bush001*4,"
     "Fallen_Log001*1,Mushroom_Patch001*0.5", 55, "Rabbit*2,Butterfly*1", 0.3, 0),
    ("Deep_Forest", "deep forest (the canopy)", "Forest001", "", 0, "", 0, 0),
    ("Moor", "moor", "Grass001", "Tall_Grass001*16,Pebbles001*2,Pebbles002*2,Rock001*2,Marigold_Patch001*0.5", 22,
     "Rabbit*1", 0.2, 0),
    ("Dirt", "bare earth", "Dirt001", "Pebbles001*2,Pebbles003*1,Tall_Grass001*1", 5, "", 0, 0),
    ("Marsh", "marsh", "Marsh001", "Reeds001*10,Willow_Tree001*4,Bog_Myrtle001*1.5,Marigold_Patch001*0.5", 15,
     "Frog*2,Duck*2", 0.4, 0),
    ("Water", "water", "Water001", "Lily_Pads001*1", 3, "", 0, 1),
    ("Sand", "sand", "Sand001", "Desert_Rock001*1,Pebbles001*1", 3, "", 0, 0),
    ("Desert", "desert", "Sand001", "Cactus001*22,Desert_Rock001*10,Dead_Tree001*3.5", 4, "", 0, 0),
    ("Snow", "snow", "Snow001", "Snow_Pine001*25,Snow_Rock001*5", 6, "", 0, 0),
    ("Ice", "ice", "Ice001", "", 0, "", 0, 0),
    ("Ash", "ash and cinders", "Ash001*3,Cinder001*1", "Dead_Tree001*3,Dead_Tree002*3,Ember_Vent001*1,"
     "Basalt_Rock001*2,Emberroot_Patch001*0.5", 9, "", 0, 0),
    ("Scorched", "scorched earth", "Scorched001*1,Scorched002*1,Scorched003*1", "Dead_Tree001*1,Dead_Tree002*1,"
     "Dragon_Skull001*0.2", 3, "", 0, 0),
    ("Cave_Floor", "cave floor", "Cave_Floor001*64,Cave_Floor002*22,Cave_Floor003*14,Cave_Rubble001*2,"
     "Cave_Puddle001*1.5,Stalagmite001*1", "Pebbles001*1,Pebbles003*1,Rock001*1,Mushroom_Patch001*0.5", 4, "", 0, 0),
    ("Cave_Rock", "cave rock (the walls)", "Cave_Wall001", "", 0, "", 0, 0, "Cave_Wall002*12,Cave_Wall003*1"),
    ("Cave_Pool", "cave pool", "Cave_Pool001", "", 0, "", 0, 0),
    ("Mountains", "mountains", "Mountain001", "", 0, "", 0, 0),
    ("Snow_Mountains", "snowy mountains", "Snow_Peak001", "", 0, "", 0, 0),
    ("Cinder_Mountains", "cinder mountains", "Cinder_Peak001", "", 0, "", 0, 0),
    ("Lava", "lava", "Lava001", "", 0, "", 0, 0),
    ("Field", "a ploughed field", "Field001", "", 0, "", 0, 0),
    ("Cobbles", "cobbled street", "Cobble001", "", 0, "", 0, 0),
    ("Gravel", "gravel road", "Gravel001", "", 0, "", 0, 0),
    ("Flagstones", "flagstones", "Flagstone001", "", 0, "", 0, 0),
    ("Sandstone_Paving", "sandstone paving", "Sandstone_Paving001", "", 0, "", 0, 0),
    ("Stone_Floor", "stone floor (a dungeon's)", "Stone001*2,Stone002*1", "Pebbles001*1", 2, "", 0, 0),
    ("Realm_Ground", "the Shardrealm's ground", "Realm_Ground001*3,Realm_Ground002*1,Realm_Ground003*1", "", 0, "",
     0, 0),
    ("Realm_Void", "the Shardrealm's void", "Realm_Void001", "", 0, "", 0, 0),
]

HEAD = """
; Terrains (dev\\migrate\\build_terrains.py: the missing ones are added, yours are kept): what the map editor's big
; brushes and outlines paint. Tiles= its ground, mixed (a weight after *); Decor= scattered over it,
; Decor.Density= in a hundred of its tiles; Entities= creatures scattered too, Entities.Density= in a hundred;
; Water=1 for water (its coasts get their diagonal pieces).
"""


def section(key, title, tiles, decor, dd, ents, ed, water, face=""):
    out = ["[Terrain_%s]" % key, "Title=%s" % title, "Kind=Terrain", "Tiles=%s" % tiles]
    if face:
        out.append("Face=%s" % face)
    if decor:
        out += ["Decor=%s" % decor, "Decor.Density=%g" % dd]
    if ents:
        out += ["Entities=%s" % ents, "Entities.Density=%g" % ed]
    if water:
        out.append("Water=1")
    return out


def main():
    raw = open(PATH, "rb").read().decode("cp1252")
    text = raw.replace("\r\n", "\n")
    have = {ln.strip()[1:-1] for ln in text.split("\n") if ln.strip().startswith("[")}
    add = []
    for t in TERRAINS:
        if "Terrain_" + t[0] not in have:
            add += section(*t) + [""]
    if not add:
        print("TileSets.ini: every terrain is there already")
        return
    if "; Terrains (" not in text:
        add = HEAD.strip("\n").split("\n") + [""] + add
    text = text.rstrip("\n") + "\n\n" + "\n".join(add)
    open(PATH, "wb").write(text.rstrip("\n").replace("\n", "\r\n").encode("cp1252") + b"\r\n")
    print("TileSets.ini: added %d terrains" % sum(1 for ln in add if ln.startswith("[")))


if __name__ == "__main__":
    main()
