"""The Shardfall Deep (the owner's wish): a great underground zone under the sea north of Ashford, level 20 and up, round
8,-13,-1. Long ago a great Shard fell burning out of the sky into the sea here, and its magic has worked on the rock and
everything in it since. The first king set an order to keep watch over it, the Glass Wardens; they built a hold beside it,
under the sea, and the Shard sang to them till they were hollow.

  * Gull Point (12,-5,0): the rocky tip of Ashford's peninsula, a sea cave in it, and the cottage of Nell Tarrow, a
    fisherwoman, and Bryony, her grandmother. Nell's nets come up full of glowing glass (Glass in the Nets, ShardfallGate:
    the way in). The cave goes down to the Drowned Stair, and the Wardens' Seal, a door of black glass that only opens to
    a Warden's signet woken with Shards (Shardcraft 15). Requires level 20.
  * The Drowned Stair: a long tunnel under the sea, salt and dripping, down to the deep.
  * The Glimmering Galleries: crystal caves, a secret grotto behind a wall that isn't there, the Singing Geode.
  * The Brinewater: an underground sea (Brine001), its shingle shore, glowfin to fish (Fishing 22), the Brine Mother.
  * The Lantern Wood: giant glowing mushrooms; a delvers' camp (Pell Varrow, cartographer: Charting the Deep; Morrow, an
    angler: The Brine Mother), a shardstone, no monster near it.
  * Leviathan's Rest: chalk, and the bones of something vast, walked among; a chest in its jaw.
  * The Wardens' Hold: dressed stone, great rooms (the Gatehall, barracks, cells, the Great Hall, a library with the
    Wardens' journals, the Chapel of the Flame, the ossuary, the armoury, the cistern, the Reliquary behind its iron door),
    traps. Warden Ysolde's ghost keeps the gate (The Last Watch: the Hollow Marshal; The Fallen Shard: the Shardborn).
  * The Shardfall: the crater where it struck, fused glass and pools of liquid Shard light round the Fallen Shard, which
    gives Shards once a (real) day to whoever finished the watch (Shards.ini Shardfall.Draw, Shardfall.Draw.Hours).
  * All of it dim (Config.ini [Darkness] Maps: sky.js), lit by what glows in it.

The art and sounds are shardfall_art.py's. The maps are laid out once (dev\\migrate\\.shardfall_built; --maps lays them
out again, over the owner's edits to them); the pictures, data and scripts are written every run.

  python -I "dev\\migrate\\build_shardfall.py"   (then build_minimaps.py, export_web_assets.py, validate.py)
"""
import math
import os
import random
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import shardfall_art as ART                              # noqa: E402
import story_kit as SK                                   # noqa: E402
from story_kit import Map, obj_line, XT, YT, say          # noqa: E402
from common import Ini, p                                 # noqa: E402
from ashen import ini                                     # noqa: E402

MAKER = "build_shardfall.py"
DONE = p("dev", "migrate", ".shardfall_built")
Z = -1
MX0, MX1, MY0, MY1 = 4, 12, -17, -5                       # (the box of maps it's laid out in, the stair from Gull Point too)
GX0, GY0 = MX0 * XT, MY0 * YT
GW, GH = (MX1 - MX0 + 1) * XT, (MY1 - MY0 + 1) * YT
SURFACE = "12,-5,0"
MOUTH = (7, 8)                                            # (the sea cave on Gull Point, 1-based on SURFACE)
LEVEL = 20

ROCK, FLOOR, WATER, POOL = 0, 1, 2, 3
STAIR, GALLERY, BRINE, WOOD, REST, HOLD, FALL = 1, 2, 3, 4, 5, 6, 7
WALK = "1" * 49
BLOCK_MID = "1111111111111111000111100011110001111111111111111"
BLOCK = "0" * 49


def T(mx, my):
    """Global tile of a spot given in maps (10.5, -9.5: the middle of map 10,-10)."""
    return int(round(mx * XT)), int(round(my * YT))


# ================================================================== the creatures: base's picture, colour, level, kind, words,
# options (Spikes: crystals grown on it; Scale: bigger; Ghost: see-through; and Entities.ini keys)
SHARD_V, SHARD_C = (190, 150, 255), (140, 210, 250)
MOBS = {
    "Brine_Crawler": ("Giant_Spider", (90, 160, 150), 20, "melee", "A crab's idea of a spider, or a spider's of a crab. It clicks.",
                      {"On.Hit": "Bleed 20", "Sight.Cone": "200", "Hearing": "1.4", "Kill.Sound": "Bug"}),
    "Drowned_Warden": ("Drowned_Sailor", (110, 170, 170), 21, "melee", "Salt-white rags that were a Warden's tabard. It still keeps its post.",
                       {"On.Hit": "Weaken 15", "Sight.Cone": "140", "Hearing": "0.8", "Kill.Sound": "Undead"}),
    "Glass_Bat": ("Bat", (150, 200, 240), 20, "melee", "Its wings are panes of glass. It rings as it turns.",
                  {"Sight.Cone": "360", "Hearing": "2", "Kill.Sound": "Small", "Movement.Speed": "2.4", "Spikes": SHARD_C}),
    "Prism_Crawler": ("Giant_Spider", (170, 120, 240), 21, "melee", "A spider grown through with crystal. Light bends round it.",
                      {"On.Hit": "Bleed 25", "Sight.Cone": "200", "Hearing": "1.4", "Kill.Sound": "Bug", "Spikes": SHARD_V}),
    "Shard_Wraith": ("Dark_Mage", (150, 220, 255), 22, "magic", "Loose magic in a body of light, humming one note.",
                     {"On.Hit": "Daze 20", "Sight.Cone": "360", "Hearing": "1", "Kill.Sound": "Undead", "Light": "40"}),
    "Crystal_Golem": ("Cave_Troll", (180, 140, 250), 23, "melee", "Rock that grew crystals, and then grew tired of standing still.",
                      {"Sight.Cone": "160", "Hearing": "0.8", "Kill.Sound": "Troll", "Spikes": SHARD_V, "Movement.Speed": "1.2"}),
    "Deep_Lurker": ("Bog_Troll", (50, 110, 120), 22, "melee", "Something from the lake, with too many teeth for one mouth.",
                    {"On.Hit": "Bleed 20", "Sight.Cone": "200", "Hearing": "1.2", "Kill.Sound": "Troll"}),
    "Spore_Shambler": ("Bog_Troll", (150, 120, 170), 21, "melee", "Mushrooms, walking, in the shape of whatever they grew on.",
                       {"On.Hit": "Poison 20", "Sight.Cone": "200", "Hearing": "1", "Kill.Sound": "Beast"}),
    "Lantern_Moth": ("Bat", (230, 200, 110), 20, "melee", "A moth as wide as a cart-wheel, its wings glowing like lanterns.",
                     {"On.Hit": "Daze 15", "Sight.Cone": "360", "Hearing": "1.6", "Kill.Sound": "Bug", "Light": "50"}),
    "Fossil_Horror": ("Skeleton", (226, 220, 198), 23, "melee", "Old bones, and not all of them from one thing.",
                      {"On.Hit": "Frailty 15", "Sight.Cone": "200", "Hearing": "0.8", "Kill.Sound": "Undead", "Scale": 1.25}),
    "Chalk_Wraith": ("Tunnel_Wraith", (220, 220, 228), 22, "melee", "Pale as the chalk it walks out of.",
                     {"Sight.Cone": "200", "Hearing": "1", "Kill.Sound": "Undead"}),
    "Hollow_Warden": ("Valour_Guardian", (140, 170, 184), 23, "melee", "A Warden still at their post, though there's nothing left in the armour but the habit.",
                      {"On.Hit": "Weaken 25", "Sight.Cone": "140", "Hearing": "1", "Kill.Sound": "Undead"}),
    "Warden_Spellbinder": ("Dark_Mage", (90, 200, 210), 24, "magic", "Once a Warden's scholar. Still reading, still casting.",
                           {"On.Hit": "Daze 20", "Sight.Cone": "200", "Hearing": "1", "Kill.Sound": "Humanoid"}),
    "Glass_Sentinel": ("Stone_Golem", (160, 210, 230), 24, "melee", "A statue the Wardens made to stand watch. It took the order to heart.",
                       {"Sight.Cone": "120", "Hearing": "0.6", "Kill.Sound": "Troll", "Spikes": SHARD_C, "Movement.Speed": "1.2"}),
    "Shard_Drake": ("Drake", (170, 110, 240), 24, "drake", "A drake grown in the Shard's light: scales of violet glass, breath like a struck bell.",
                    {"Sight.Cone": "200", "Hearing": "1.4", "Kill.Sound": "Dragon", "Spikes": SHARD_V, "Light": "40"}),
    # (the three of a kind)
    "Brine_Mother": ("Bog_Troll", (40, 92, 104), 24, "boss", "The lake's mother. Everything in it is hers, and she counts.",
                     {"On.Hit": "Bleed 30", "Sight.Cone": "360", "Hearing": "1.4", "Kill.Sound": "Troll", "Scale": 1.5}),
    "Hollow_Marshal": ("Valour_Guardian", (110, 118, 160), 25, "boss", "Marshal Corvane of the Glass Wardens, who listened to the Shard too long.",
                       {"On.Hit": "Weaken 30", "Sight.Cone": "360", "Hearing": "1", "Kill.Sound": "Undead", "Scale": 1.25,
                        "Fear.Immune": "1"}),
    "Shardborn": ("Cave_Troll", (200, 160, 255), 25, "boss", "The Shard's own guardian: crystal grown into the shape of a giant, and waking.",
                  {"On.Hit": "Daze 35", "Sight.Cone": "360", "Hearing": "1.2", "Kill.Sound": "Troll", "Scale": 1.5,
                   "Spikes": SHARD_V, "Light": "70", "Fear.Immune": "1", "Freeze.Immune": "1"}),
}
PEOPLE = {   # (the Deep's own people's pictures: Ysolde's ghost)
    "Ghost_Warden": ("Warden", (170, 220, 230), 1, "good", "A Warden of the old order, in a cloak of grey light. You can see the wall through her.",
                     {"Ghost": True}),
}
ART_ONLY = ("Spikes", "Scale", "Ghost")


def mob_stats(level, kind):
    hp, st, de = round(8.3 * level), max(1, round(0.68 * level)), max(1, round(0.75 * level))
    if kind == "boss":
        hp, st, de = round(hp * 2.6), st + 3, de + 3
    return hp, st, de


def mob_data():
    ents = Ini(p("data", "Entities.ini"))
    for name, (base, col, level, kind, words, opts) in MOBS.items():
        hp, st, de = mob_stats(level, kind)
        gold = "Gold_Coin(s),%d-%d,100" % (level * 3, level * 5)
        vals = [("Type", "NPC"), ("Attitude", "Bad"), ("Use.Words", "Attack,Examine"), ("Examine.Info", words),
                ("Aggressive", "1"), ("Level", str(level)), ("Hitpoints", str(hp)), ("Strength", str(st)), ("Defence", str(de)),
                ("Attack.Speed", "2" if kind == "magic" else "1.5"), ("Respawn", "1800" if kind == "boss" else "480"),
                ("Movement.Speed", "1.5"), ("Aggro.Range", "260" if kind == "boss" else "230"), ("Roam.Radius", "3"),
                ("Chase.Radius", "12" if kind == "boss" else "9"), ("Walk.Speed", "0.5"), ("Pause", "2-7"),
                ("Drops", "%s Mithril_Ore,1-1,14 Sapphire,1-1,14 Ruby,1-1,10%s" % (
                    gold, " Ward_Shard,1-1,40 Storm_Shard,1-1,40" if kind == "boss" else ""))]
        if kind == "magic":
            vals += [("Weapon.Range", "190"), ("Missile", "Dark_Bolt_Missile"), ("Missile.Impact", "Dark_Burst")]
        elif kind == "drake":
            vals += [("Weapon.Range", "130"), ("Missile", "Ice_Bolt_Missile"), ("Missile.Impact", "Dark_Burst"),
                     ("Missile.Sound", "SpellFire")]
        else:
            vals += [("Weapon.Range", "0")]
        if kind == "boss":
            vals += [("Boss", "1")]
        vals += [(k, str(v)) for k, v in opts.items() if k not in ART_ONLY]
        SK.section(SK.ENTS, name, vals)
    SK.section(SK.ENTS, "Ghost_Warden", [
        ("Type", "NPC"), ("Use.Words", "Talk to,Examine"), ("Attitude", "Good"), ("Examine.Info", PEOPLE["Ghost_Warden"][4]),
        ("Movement.Speed", "0.6"), ("Roam.Radius", "1"), ("Chase.Radius", "0"), ("Walk.Speed", "0.3"), ("Pause", "6-14"),
        ("Schedule", "Always"), ("Respawn", "300"), ("Light", "40"), ("Level", "1"), ("Solid", "0")])


# ================================================================== the ground, the walls and what stands about: Tiles.ini
FACES = {   # area: its walls' faces (by weight)
    STAIR: [("Wet_Face001", 3), ("Wet_Face002", 2), ("Cave_Wall002", 2)],
    GALLERY: [("Crystal_Face001", 3), ("Crystal_Face002", 2), ("Crystal_Face003", 2), ("Cave_Wall002", 2)],
    BRINE: [("Wet_Face001", 3), ("Wet_Face002", 3)],
    WOOD: [("Fungal_Face001", 3), ("Fungal_Face002", 3), ("Cave_Wall002", 1)],
    REST: [("Chalk_Face001", 3), ("Chalk_Face002", 2)],
    FALL: [("Crystal_Face001", 2), ("Crystal_Face002", 2), ("Crystal_Face003", 3)],
    HOLD: [("Warden_Wall002", 8), ("Warden_Wall003", 1)],
}
FLOORS = {  # area: its floor (by weight; patches, not speckle)
    STAIR: [("Cave_Floor001", 5), ("Cave_Floor003", 2)],
    GALLERY: [("Gallery_Floor001", 1)],
    BRINE: [("Deep_Shingle001", 1)],
    WOOD: [("Spore_Loam001", 1)],
    REST: [("Chalk_Floor001", 1)],
    FALL: [("Shardglass001", 1)],
    HOLD: [("Warden_Flag001", 1)],
}
ROCKS = {   # area: its rock behind the faces (each wall terrain its own, so the editor's faces never mix them up)
    STAIR: "Wet_Rock001", GALLERY: "Crystal_Rock001", BRINE: "Wet_Rock001", WOOD: "Fungal_Rock001", REST: "Chalk_Rock001",
    FALL: "Crystal_Rock001",
}
DECOR = {   # area: (decor by weight, how many in 100 floor tiles); "*" ones block, so only where it's open all round
    STAIR: ([("Deep_Kelp001", 3), ("Deep_Kelp002", 2), ("Pebbles001", 3), ("Bones001", 1), ("Glow_Moss001", 1)], 6),
    GALLERY: ([("*Shard_Crystal001", 4), ("*Shard_Crystal002", 3), ("*Shard_Crystal003", 2), ("*Shard_Crystal004", 2),
               ("Pebbles003", 2), ("*Shardglass_Rock001", 2)], 9),
    BRINE: ([("Deep_Kelp001", 4), ("Deep_Kelp002", 4), ("Pebbles001", 2), ("Glow_Moss001", 1), ("Bones002", 1)], 7),
    WOOD: ([("*Lantern_Cap001", 4), ("*Lantern_Cap002", 3), ("*Lantern_Cap003", 3), ("Glow_Moss001", 6),
            ("Mushroom_Patch001", 3), ("Mushroom_Patch002", 3), ("Mushroom_Ring001", 1)], 13),
    REST: ([("Bones001", 3), ("Bones002", 3), ("Pebbles003", 2)], 4),
    FALL: ([("*Shard_Crystal001", 3), ("*Shard_Crystal003", 3), ("*Shard_Crystal002", 2), ("*Shard_Crystal004", 1),
            ("*Shardglass_Rock001", 2)], 8),
    HOLD: ([], 0),
}

TILES = {   # name: keys (Tiles.ini)
    "Shard_Pool001": [("Walkable.Data", BLOCK), ("Show.Name", "1"), ("Examine.Info", "A pool of liquid light: Shard, melted. It moves "
                      "when nothing touches it."), ("Line.of.Sight", "1"), ("Texture", "Shard_Pool"),
                      ("Texture.Frames", str(ART.POOL_FRAMES)), ("Texture.Speed", str(ART.POOL_SPEED)), ("Light", "60"),
                      ("Round", "1"), ("Blend", "8")],
    "Gull_Cave001": [("Walkable.Data", WALK), ("Show.Name", "1"), ("Use.Words", "Enter,Examine"), ("Line.of.Sight", "0"),
                     ("Examine.Info", "A sea cave in the rocks of the point. The gulls keep away from it."), ("Blend", "8"),
                     ("Blend.Texture", "Mountain001")],
    "Warden_Wall001": [("Walkable.Data", BLOCK), ("Show.Name", "0"), ("Examine.Info", "Dressed stone, set without mortar, every "
                       "block cut to fit."), ("Line.of.Sight", "0")],
    "Warden_Wall002": [("Walkable.Data", BLOCK), ("Show.Name", "1"), ("Examine.Info", "A wall of pale dressed stone, cut and laid by "
                       "careful hands, a long time ago."), ("Line.of.Sight", "0")],
    "Warden_Wall003": [("Walkable.Data", BLOCK), ("Show.Name", "1"), ("Examine.Info", "A rune of glass is set in the stone. It "
                       "glows, faintly, when you look away."), ("Line.of.Sight", "0"), ("Light", "30")],
    "Warden_Seal001": [("Walkable.Data", WALK), ("Show.Name", "1"), ("Use.Words", "Touch,Examine"), ("Line.of.Sight", "0"),
                       ("Examine.Info", "A door of black glass in a frame of dressed stone. Runes glow round it. In its middle, "
                        "a small round hollow."), ("Unlocked.Tile", "Warden_Seal002"), ("Light", "30")],
    "Warden_Seal002": [("Walkable.Data", WALK), ("Show.Name", "1"), ("Examine.Info", "The Wardens' Seal, open: a way into the "
                       "dark."), ("Line.of.Sight", "1")],
    "Warden_Door001": [("Walkable.Data", WALK), ("Show.Name", "1"), ("Line.of.Sight", "0"), ("Unlocked.Tile", "Warden_Door002"),
                       ("Examine.Info", "A door of black iron, the Wardens' seal on its lock.")],
    "Warden_Door002": [("Walkable.Data", WALK), ("Show.Name", "1"), ("Examine.Info", "The Reliquary's iron door, standing "
                       "open."), ("Line.of.Sight", "1")],
    "Shard_Crystal001": [("Walkable.Data", BLOCK_MID), ("Layer", "Decor"), ("Show.Name", "1"), ("Light", "40"),
                         ("Examine.Info", "Crystals growing out of the rock, violet and warm.")],
    "Shard_Crystal002": [("Walkable.Data", BLOCK_MID), ("Layer", "Decor"), ("Show.Name", "1"), ("Light", "40"),
                         ("Examine.Info", "A tall crystal, pale blue, ringing faintly if you breathe on it.")],
    "Shard_Crystal003": [("Walkable.Data", BLOCK_MID), ("Layer", "Decor"), ("Show.Name", "1"), ("Light", "55"),
                         ("Examine.Info", "A thicket of crystals as tall as you are, humming together.")],
    "Shard_Crystal004": [("Walkable.Data", BLOCK_MID), ("Layer", "Decor"), ("Show.Name", "1"), ("Light", "35"),
                         ("Examine.Info", "Rose-white crystals, cold to the touch.")],
    "Lantern_Cap001": [("Walkable.Data", BLOCK_MID), ("Layer", "Decor"), ("Show.Name", "1"), ("Light", "50"),
                       ("Examine.Info", "A mushroom taller than you are. Its gills give off a soft green light.")],
    "Lantern_Cap002": [("Walkable.Data", BLOCK_MID), ("Layer", "Decor"), ("Show.Name", "1"), ("Light", "50"),
                       ("Examine.Info", "A great orange mushroom, glowing like a lantern left on.")],
    "Lantern_Cap003": [("Walkable.Data", BLOCK_MID), ("Layer", "Decor"), ("Show.Name", "1"), ("Light", "50"),
                       ("Examine.Info", "A blue-capped mushroom as tall as a door, humming with spores.")],
    "Glow_Moss001": [("Walkable.Data", WALK), ("Layer", "Decor"), ("Show.Name", "0"), ("Light", "20"),
                     ("Examine.Info", "Moss that glows where you step on it.")],
    "Deep_Kelp001": [("Walkable.Data", WALK), ("Layer", "Decor"), ("Show.Name", "0"), ("Examine.Info", "Weed, washed up and left.")],
    "Deep_Kelp002": [("Walkable.Data", WALK), ("Layer", "Decor"), ("Show.Name", "0"), ("Examine.Info", "Black weed, still wet.")],
    "Stalk_Foot001": [("Walkable.Data", BLOCK_MID), ("Layer", "Decor"), ("Show.Name", "0"), ("Examine.Info", "")],
    "Leviathan_Spine001": [("Walkable.Data", BLOCK_MID), ("Layer", "Decor"), ("Show.Name", "1"),
                           ("Examine.Info", "Its backbone: each bone of it the size of a barrel.")],
    "Warden_Statue001": [("Walkable.Data", BLOCK), ("Layer", "Decor"), ("Show.Name", "1"), ("Light", "30"),
                         ("Examine.Info", "A Glass Warden in stone, a shard held up. The shard is real, and still glows.")],
    "Warden_Brazier001": [("Walkable.Data", BLOCK_MID), ("Layer", "Decor"), ("Show.Name", "1"), ("Light", "70"),
                          ("Examine.Info", "A brazier of violet fire that gives off no heat at all.")],
    "Warden_Tomb001": [("Walkable.Data", BLOCK), ("Layer", "Decor"), ("Show.Name", "1"),
                       ("Examine.Info", "A Warden's tomb, a glass sword carved on its lid. The lid has been moved.")],
    "Cell_Bars001": [("Walkable.Data", BLOCK), ("Layer", "Decor"), ("Show.Name", "1"), ("Line.of.Sight", "1"),
                     ("Examine.Info", "Iron bars. Whoever was kept here was kept a long time.")],
    "Shardglass_Rock001": [("Walkable.Data", BLOCK_MID), ("Layer", "Decor"), ("Show.Name", "1"), ("Use.Words", "Mine,Examine"),
                           ("Light", "30"), ("Examine.Info", "A boulder glassed through with Shard. Dig it, and its remnants come "
                            "loose (Mining 18).")],
    "Shardglass_Rock002": [("Walkable.Data", BLOCK_MID), ("Layer", "Decor"), ("Show.Name", "1"),
                           ("Examine.Info", "A boulder, its glass dug out. It will grow back, slowly.")],
}
for _i in range(1, 5):
    TILES["Leviathan_Rib%03d" % _i] = [("Walkable.Data", WALK), ("Layer", "Decor"), ("Show.Name", "1"),
                                       ("Examine.Info", "A rib, longer than a ship's mast, curving over you.")]
for _i in range(1, 10):
    TILES["Leviathan_Skull%03d" % _i] = [("Walkable.Data", BLOCK), ("Layer", "Decor"), ("Show.Name", "1"),
                                         ("Examine.Info", "The skull of something that swam these seas before there were "
                                          "seas. Something has made a nest of its jaw.")]
for _n in ("Crystal_Face", "Wet_Face", "Fungal_Face", "Chalk_Face"):
    for _i in (1, 2, 3):
        TILES["%s%03d" % (_n, _i)] = [("Walkable.Data", BLOCK), ("Show.Name", "1"), ("Line.of.Sight", "0"), ("Blend", "4"),
                                      ("Blend.Texture", "Cave_Wall001"), ("Examine.Info", {
                                          "Crystal_Face": "Rock, crystals pushing out of it like teeth.",
                                          "Wet_Face": "Wet rock. The sea is somewhere just the other side of it.",
                                          "Fungal_Face": "Rock, shelved with fungus that glows at its rims.",
                                          "Chalk_Face": "A face of chalk, a shell pressed into it."}[_n])]
for _n in ("Crystal", "Wet", "Fungal", "Chalk"):
    TILES["%s_Rock001" % _n] = [("Walkable.Data", BLOCK), ("Show.Name", "1"), ("Line.of.Sight", "0"), ("Blend", "4"),
                                ("Blend.Texture", "Cave_Wall001"), ("Examine.Info", "Solid rock.")]
del TILES["Wet_Face003"], TILES["Fungal_Face003"], TILES["Chalk_Face003"]

COLOURS = {"Shardglass001": (96, 66, 160), "Gallery_Floor001": (74, 72, 90), "Spore_Loam001": (54, 42, 48),
           "Chalk_Floor001": (164, 158, 142), "Deep_Shingle001": (66, 72, 74), "Brine001": (16, 48, 60),
           "Shard_Pool001": (150, 110, 240), "Warden_Flag001": (116, 122, 134), "Warden_Wall001": (40, 42, 52),
           "Warden_Wall002": (96, 102, 116), "Warden_Wall003": (96, 102, 116), "Warden_Seal001": (40, 30, 70),
           "Warden_Seal002": (30, 26, 40), "Warden_Door001": (58, 56, 62), "Warden_Door002": (30, 28, 34),
           "Crystal_Face001": (70, 62, 96), "Crystal_Face002": (70, 62, 96), "Crystal_Face003": (70, 62, 96),
           "Wet_Face001": (42, 56, 58), "Wet_Face002": (42, 56, 58), "Fungal_Face001": (60, 48, 54), "Fungal_Face002": (60, 48, 54),
           "Chalk_Face001": (140, 134, 120), "Chalk_Face002": (140, 134, 120), "Gull_Cave001": (40, 40, 44), "Shard_Crystal001": (150, 100, 240), "Shard_Crystal002": (110, 190, 240),
           "Shard_Crystal003": (170, 120, 245), "Shard_Crystal004": (220, 190, 245), "Lantern_Cap001": (120, 70, 140),
           "Lantern_Cap002": (180, 110, 60), "Lantern_Cap003": (70, 110, 150), "Glow_Moss001": (80, 200, 170), "Deep_Kelp001": (44, 96, 66),
           "Deep_Kelp002": (44, 96, 66), "Leviathan_Spine001": (214, 206, 186), "Warden_Statue001": (150, 152, 160),
           "Warden_Brazier001": (160, 130, 250), "Warden_Tomb001": (120, 124, 134), "Cell_Bars001": (96, 94, 100),
           "Shardglass_Rock001": (120, 90, 200), "Shardglass_Rock002": (80, 76, 90), "Stalk_Foot001": (60, 50, 60), "Crystal_Rock001": (46, 42, 56), "Wet_Rock001": (36, 44, 46),
           "Fungal_Rock001": (44, 38, 42), "Chalk_Rock001": (110, 104, 92)}

TERRAINS = [   # TileSets.ini: for the map editor's brushes
    ("Terrain_Shardglass", "fused Shard glass", ["Tiles=Shardglass001", "Decor=Shard_Crystal001*3,Shard_Crystal003*3,"
                                                 "Shard_Crystal002*2,Shardglass_Rock001*1", "Decor.Density=6"]),
    ("Terrain_Gallery_Floor", "crystal-veined cave floor", ["Tiles=Gallery_Floor001*6,Cave_Floor002*1",
                                                            "Decor=Shard_Crystal001*4,Shard_Crystal002*3,Shard_Crystal004*2,"
                                                            "Pebbles003*2", "Decor.Density=7"]),
    ("Terrain_Spore_Loam", "fungal loam (the Lantern Wood)", ["Tiles=Spore_Loam001", "Decor=Lantern_Cap001*4,Lantern_Cap002*3,"
                                                              "Lantern_Cap003*3,Glow_Moss001*6,Mushroom_Patch001*3",
                                                              "Decor.Density=12"]),
    ("Terrain_Chalk", "chalk floor", ["Tiles=Chalk_Floor001", "Decor=Bones001*3,Bones002*3,Pebbles003*2", "Decor.Density=4"]),
    ("Terrain_Deep_Shingle", "wet shingle", ["Tiles=Deep_Shingle001", "Decor=Deep_Kelp001*4,Deep_Kelp002*4,Pebbles001*2",
                                             "Decor.Density=7"]),
    ("Terrain_Brine", "the deep's black water", ["Tiles=Brine001", "Water=1"]),
    ("Terrain_Shard_Pool", "liquid Shard light", ["Tiles=Shard_Pool001", "Water=1"]),
    ("Terrain_Warden_Flags", "the Wardens' flagstones", ["Tiles=Warden_Flag001"]),
    ("Terrain_Crystal_Rock", "crystal rock (the walls)", ["Tiles=Crystal_Rock001", "Face=Crystal_Face001*3,Crystal_Face002*2,"
                                                          "Crystal_Face003*2"]),
    ("Terrain_Wet_Rock", "wet rock (the walls)", ["Tiles=Wet_Rock001", "Face=Wet_Face001*3,Wet_Face002*2"]),
    ("Terrain_Fungal_Rock", "fungal rock (the walls)", ["Tiles=Fungal_Rock001", "Face=Fungal_Face001*3,Fungal_Face002*3"]),
    ("Terrain_Chalk_Rock", "chalk (the walls)", ["Tiles=Chalk_Rock001", "Face=Chalk_Face001*3,Chalk_Face002*2"]),
    ("Terrain_Warden_Wall", "the Wardens' walls", ["Tiles=Warden_Wall001", "Face=Warden_Wall002*8,Warden_Wall003*1"]),
]


def tile_data():
    for tile, (tex, _, words) in ART.GROUNDS.items():
        water = tile == "Brine001"
        keys = [("Walkable.Data", BLOCK if water else WALK), ("Show.Name", "1" if water else "0"), ("Use.Words", ""),
                ("Examine.Info", words), ("Line.of.Sight", "1"), ("Texture", tex), ("Blend", "6" if water else "4"),
                ("Blend.Texture", tile)]
        if water:
            keys += [("Water", "1"), ("Round", "1")]
        elif tile != "Warden_Flag001":
            keys += [("Round", "1")]
        else:
            keys += [("Walk.Speed", "1.1")]
        SK.section(SK.TILES, tile, keys)
    for tile, keys in TILES.items():
        SK.section(SK.TILES, tile, keys)
    for tile, rgb in COLOURS.items():
        SK.minimap_colour(tile, rgb)
    for i in range(1, 10):                               # (the bones, on the minimap as bone)
        SK.minimap_colour("Leviathan_Skull%03d" % i, (214, 206, 186))
    for i in range(1, 5):
        SK.minimap_colour("Leviathan_Rib%03d" % i, (214, 206, 186))
    path = p("data", "TileSets.ini")
    for name, title, lines in TERRAINS:
        SK.set_section(path, name, ["Title=%s" % title, "Kind=Terrain"] + lines)
    SK.set_section(path, "Leviathan_Skull", ["Title=the leviathan's skull", "Columns=3",
                                             "Tiles=" + ",".join("Leviathan_Skull%03d" % i for i in range(1, 10)), "Kind=Whole"])


# ================================================================== the layout
class Deep:
    def __init__(self, seed=8130):
        self.rng = random.Random(seed)
        self.cell = np.zeros((GH, GW), np.int8)
        self.area = np.zeros((GH, GW), np.int8)
        self.built = np.zeros((GH, GW), bool)            # (the Wardens' masonry: their floors, and walls round them)
        self.keep = np.zeros((GH, GW), bool)             # (kept open: paths, doorways, where people stand)
        self.decor = {}                                  # (gx, gy): decor
        self.tile = {}                                   # (gx, gy): a tile set by hand
        self.ents = []                                   # (gx, gy, kind, name, opts)
        self.ids = []                                    # (gx, gy, id)
        self.triggers = []                               # (gx, gy, script)
        self.locks = []                                  # (gx, gy, condition, message)
        self.roof = {}                                   # (gx, gy): roof
        self.taken = set()
        self.tall = []                                   # (gx, gy, entity): what stands taller than a tile

    # ----- the grid
    def inside(self, gx, gy, edge=2):
        return GX0 + edge <= gx < GX0 + GW - edge and GY0 + edge <= gy < GY0 + GH - edge

    def get(self, gx, gy):
        if not self.inside(gx, gy, 0):
            return ROCK
        return self.cell[gy - GY0, gx - GX0]

    def put(self, gx, gy, kind, area=None, built=None):
        if not self.inside(gx, gy):
            return
        self.cell[gy - GY0, gx - GX0] = kind
        if area is not None:
            self.area[gy - GY0, gx - GX0] = area
        if built is not None:
            self.built[gy - GY0, gx - GX0] = built

    def area_of(self, gx, gy):
        return self.area[gy - GY0, gx - GX0] if self.inside(gx, gy, 0) else 0

    def is_built(self, gx, gy):
        return bool(self.built[gy - GY0, gx - GX0]) if self.inside(gx, gy, 0) else False

    def open_(self, gx, gy):
        return self.get(gx, gy) == FLOOR

    # ----- natural shapes
    @staticmethod
    def wobble(angle, seed):
        r = random.Random(seed)
        ph = [r.uniform(0, 6.28) for _ in range(5)]
        return 1 + 0.2 * math.sin(2 * angle + ph[0]) + 0.14 * math.sin(3 * angle + ph[1]) + 0.08 * math.sin(5 * angle + ph[2]) + \
            0.05 * math.sin(7 * angle + ph[3]) + 0.04 * math.sin(11 * angle + ph[4])

    def blob(self, cx, cy, rx, ry, area, seed):
        out = []
        for gy in range(int(cy - ry * 1.6), int(cy + ry * 1.6) + 1):
            for gx in range(int(cx - rx * 1.6), int(cx + rx * 1.6) + 1):
                dx, dy = (gx - cx) / rx, (gy - cy) / ry
                d = math.hypot(dx, dy) / self.wobble(math.atan2(dy, dx), seed)
                if d <= 1 and self.inside(gx, gy, 3) and not self.is_built(gx, gy):
                    self.put(gx, gy, FLOOR, area)
                    out.append((gx, gy, d))
        return out

    def path(self, pts, area, seed, rmin=1.0, rmax=2.2, way=True):
        """A winding tunnel through pts: each leg bent by midpoints pushed aside, as water and time would cut it; its width
        wandering between rmin and rmax. Returns its centre line."""
        rng = random.Random(seed)
        line = [pts[0]]
        for a, b in zip(pts, pts[1:]):
            seg = [a, b]
            for _ in range(4):
                nxt = [seg[0]]
                for u, v in zip(seg, seg[1:]):
                    mx, my = (u[0] + v[0]) / 2, (u[1] + v[1]) / 2
                    ln = math.hypot(v[0] - u[0], v[1] - u[1])
                    nx, ny = -(v[1] - u[1]) / max(ln, 1e-6), (v[0] - u[0]) / max(ln, 1e-6)
                    k = rng.uniform(-0.22, 0.22) * ln
                    nxt += [(mx + nx * k, my + ny * k), v]
                seg = nxt
            line += seg[1:]
        centre = []
        phase = rng.uniform(0, 6.28)
        for u, v in zip(line, line[1:]):
            ln = max(1, int(math.hypot(v[0] - u[0], v[1] - u[1]) * 2))
            for i in range(ln):
                x, y = u[0] + (v[0] - u[0]) * i / ln, u[1] + (v[1] - u[1]) * i / ln
                centre.append((int(round(x)), int(round(y))))
        for i, (x, y) in enumerate(centre):
            r = rmin + (rmax - rmin) * (0.5 + 0.5 * math.sin(i / 23.0 + phase))
            ri = int(math.ceil(r))
            for dy in range(-ri, ri + 1):
                for dx in range(-ri, ri + 1):
                    if dx * dx + dy * dy <= r * r + 0.3 and not self.is_built(x + dx, y + dy):
                        if self.get(x + dx, y + dy) == ROCK:
                            self.put(x + dx, y + dy, FLOOR, area)
        self.paths.append(centre)
        if way:                                          # (a way through: never under water, nothing in its way)
            self.ways.append(centre)
        return centre

    def smooth(self, passes=2):
        """Caves' edges worn smooth (never the Wardens' stone), then the tunnels' middles opened again so nothing's cut off."""
        for _ in range(passes):
            f = (self.cell == FLOOR).astype(np.int16)
            n = sum(np.roll(np.roll(f, dy, 0), dx, 1) for dy in (-1, 0, 1) for dx in (-1, 0, 1))
            grow = (f == 0) & (n >= 6) & ~self.built
            shrink = (f == 1) & (n <= 3) & ~self.built & ~self.keep
            self.cell[grow] = FLOOR
            self.cell[shrink] = ROCK
            if grow.any():                                 # (a new floor takes the area round it)
                ys, xs = np.nonzero(grow & (self.area == 0))
                for y, x in zip(ys, xs):
                    near = self.area[max(0, y - 1):y + 2, max(0, x - 1):x + 2]
                    nz = near[near > 0]
                    if nz.size:
                        self.area[y, x] = np.bincount(nz).argmax()
        for centre in self.paths:
            for x, y in centre:
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if self.get(x + dx, y + dy) == ROCK and not self.is_built(x + dx, y + dy) and self.inside(x + dx, y + dy):
                            a = self.area_of(x, y) or self.area_of(x + dx, y + dy)
                            self.put(x + dx, y + dy, FLOOR, a)

    def reachable(self, start):
        seen = np.zeros_like(self.built)
        sx, sy = start
        todo = [(sx - GX0, sy - GY0)]
        seen[sy - GY0, sx - GX0] = True
        while todo:
            x, y = todo.pop()
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < GW and 0 <= ny < GH and not seen[ny, nx] and self.cell[ny, nx] == FLOOR:
                    seen[ny, nx] = True
                    todo.append((nx, ny))
        return seen

    # ----- the Wardens' stone
    def room(self, x0, y0, w, h, area=HOLD):
        for gy in range(y0, y0 + h):
            for gx in range(x0, x0 + w):
                self.put(gx, gy, FLOOR, area, True)
        for gy in range(y0 - 1, y0 + h + 1):             # (its walls are the Wardens' too, whatever's beyond)
            for gx in range(x0 - 1, x0 + w + 1):
                if self.get(gx, gy) == ROCK:
                    self.built[gy - GY0, gx - GX0] = True
        return (x0, y0, w, h)

    def corridor(self, x0, y0, x1, y1, width=3):
        """Straight, as the Wardens cut them: across, then down."""
        hw = width // 2
        for gx in range(min(x0, x1), max(x0, x1) + 1):
            for k in range(-hw, hw + 1):
                self.put(gx, y0 + k, FLOOR, HOLD, True)
                self.keep[y0 + k - GY0, gx - GX0] = True
        for gy in range(min(y0, y1), max(y0, y1) + 1):
            for k in range(-hw, hw + 1):
                self.put(x1 + k, gy, FLOOR, HOLD, True)
                self.keep[gy - GY0, x1 + k - GX0] = True
        for gy in range(min(y0, y1) - hw - 1, max(y0, y1) + hw + 2):
            for gx in range(min(x0, x1) - hw - 1, max(x0, x1) + hw + 2):
                if self.get(gx, gy) == ROCK:
                    self.built[gy - GY0, gx - GX0] = True

    def wall_across(self, gx, gy):
        """A cell made the Wardens' wall again (a door's frame)."""
        self.put(gx, gy, ROCK, None, True)


def lay_out():
    d = Deep()
    d.paths, d.ways = [], []
    rng = d.rng

    # ----- the Wardens' Gate and the Hold first: their stone stays as it's laid
    arrive = (306, -99)
    vest = d.room(302, -110, 9, 5, STAIR)
    for gx in range(305, 308):                               # (its way in from the cave, on the south)
        d.put(gx, -105, FLOOR, STAIR, True)
        d.keep[-105 - GY0, gx - GX0] = True
    for gx in range(302, 311):
        d.wall_across(gx, -111)
    d.put(306, -111, FLOOR, STAIR, True)                     # (the Seal, in the middle of its north wall)
    d.keep[-111 - GY0, 306 - GX0] = True
    d.tile[(306, -111)] = "Warden_Seal001"
    d.ids.append((306, -111, "Shardfall_Seal"))
    d.locks.append((306, -111, "$Attr.ShardfallGate>=5", "Black glass, sealed fast. A ward holds it shut."))

    R = {}
    R["cells"] = d.room(243, -350, 18, 11)
    R["library"] = d.room(266, -350, 16, 12)
    R["chapel"] = d.room(287, -350, 14, 12)
    R["reliquary"] = d.room(306, -350, 13, 10)
    R["barracks"] = d.room(243, -334, 14, 11)
    R["hall"] = d.room(266, -332, 26, 18)
    R["ossuary"] = d.room(297, -332, 22, 13)
    R["gate"] = d.room(243, -318, 16, 12)
    R["armoury"] = d.room(297, -312, 16, 11)
    R["cistern"] = d.room(264, -306, 28, 8)
    d.corridor(250, -339, 250, -335)                         # cells - barracks
    d.corridor(250, -323, 250, -319)                         # barracks - gatehall
    d.corridor(259, -316, 265, -316)                         # gatehall - great hall
    d.corridor(273, -338, 273, -333)                         # great hall - library
    d.corridor(282, -345, 286, -345)                         # library - chapel
    d.corridor(301, -345, 304, -345)                         # chapel - reliquary (its door in the wall between)
    d.corridor(292, -326, 296, -326)                         # great hall - ossuary
    d.corridor(305, -319, 305, -313)                         # ossuary - armoury
    d.corridor(278, -314, 278, -307)                         # great hall - cistern
    d.corridor(292, -304, 296, -304)                         # cistern - armoury
    for gy in range(-350, -340):                             # (the Reliquary's west wall, its door in the middle)
        d.wall_across(305, gy)
    d.put(305, -345, FLOOR, HOLD, True)
    d.tile[(305, -345)] = "Warden_Door001"
    d.locks.append((305, -345, "$Attr.WardenQuest>=3", "A door of black iron, the Wardens' seal on its lock. It won't move."))
    d.ids.append((305, -345, "Wardens_Reliquary_Door"))
    for gx in range(250, 253):                               # (the Gatehall's great gate, broken open, on the south)
        d.put(gx, -306, FLOOR, HOLD, True)
        d.keep[-306 - GY0, gx - GX0] = True
    for gy in range(-346, -343):                             # (the Watch Gallery: out of the cells' west wall)
        for gx in range(236, 243):
            d.put(gx, gy, FLOOR, HOLD, True)
            d.keep[gy - GY0, gx - GX0] = True

    # ----- the caves
    d.blob(*arrive, 6, 4, STAIR, 1)
    d.path([(306, -102), (306, -105)], STAIR, 2, 1.0, 1.0)
    stair = d.path([(306, -112), (300, -124), (293, -137), (285, -150), (276, -163), (268, -176), (264, -192), (266, -204)],
                   STAIR, 3, 1.0, 2.0)
    chambers = {   # area: its chambers ((centre in maps), radii, seed), each joined to the one before it
        GALLERY: [((10.8, -9.6), 13, 9, 11), ((11.6, -10.6), 12, 8, 12), ((11.7, -11.8), 9, 7, 14), ((10.5, -12.0), 9, 7, 15),
                  ((9.9, -10.9), 10, 8, 13), ((9.3, -9.1), 11, 8, 16), ((12.2, -8.9), 9, 7, 17)],
        BRINE: [((6.7, -10.2), 12, 8, 23), ((5.6, -11.0), 24, 15, 21), ((4.8, -12.0), 13, 9, 22), ((5.4, -9.7), 15, 9, 24)],
        WOOD: [((9.3, -11.9), 10, 7, 33), ((8.5, -12.5), 18, 12, 31), ((7.6, -13.3), 12, 8, 32), ((9.9, -13.6), 10, 7, 34)],
        REST: [((5.0, -14.6), 17, 11, 41), ((5.6, -15.4), 12, 8, 42), ((4.7, -16.2), 10, 6, 43)],
        STAIR: [((11.6, -6.6), 9, 6, 51), ((10.9, -8.2), 8, 6, 52)],
    }
    lake = []
    for area, rooms in chambers.items():
        for i, ((mx, my), rx, ry, s) in enumerate(rooms):
            cx, cy = T(mx, my)
            got = d.blob(cx, cy, rx, ry, area, s)
            if area == BRINE and i in (1, 3):              # (the lake: the big chambers' middles)
                lake += [(gx, gy, dd, (cx, cy)) for gx, gy, dd in got]
            if i:
                d.path([T(*rooms[i - 1][0]), (cx, cy)], area, s * 7, 1.2, 2.4, way=area != BRINE)
    fall_c = T(7.9, -15.5)
    d.blob(fall_c[0], fall_c[1], 22, 15, FALL, 57)
    # (the ways between, middle to middle)
    G, B, W_, Rr = chambers[GALLERY], chambers[BRINE], chambers[WOOD], chambers[REST]
    d.path([T(*G[4][0]), T(*W_[0][0])], GALLERY, 61)
    d.path([T(*G[4][0]), T(8.4, -10.0), T(*B[0][0])], BRINE, 62)
    d.path([T(*B[0][0]), T(7.3, -11.6), T(*W_[2][0])], WOOD, 63)
    d.path([T(*B[2][0]), T(4.6, -13.2), T(*Rr[0][0])], REST, 64)
    d.path([T(*W_[1][0]), T(8.1, -14.2), fall_c], FALL, 65)
    d.path([T(*Rr[1][0]), T(6.5, -15.9), fall_c], FALL, 66)
    d.path([(251, -305), (246, -292), (238, -274), T(*W_[0][0])], WOOD, 67)
    d.path([(236, -345), (226, -341), (214, -336), fall_c], FALL, 68)
    d.smooth()

    # ----- only what joins up stays (nothing sealed off in the rock)
    seen = d.reachable(arrive)
    lost = (d.cell == FLOOR) & ~seen
    d.cell[lost] = ROCK

    # ----- the Brinewater: its middle the deep's black water, a shore of shingle all round (never across a way through)
    ways = set()
    for centre in d.ways:
        for x, y in centre:
            for dy in range(-2, 3):
                for dx in range(-2, 3):
                    ways.add((x + dx, y + dy))
    for gx, gy, dd, (cx, cy) in lake:
        if d.get(gx, gy) != FLOOR or (gx, gy) in ways:
            continue
        shore = all(d.get(gx + dx, gy + dy) in (FLOOR, WATER) for dx in range(-2, 3) for dy in range(-2, 3))
        if shore and dd < 0.8:
            d.put(gx, gy, WATER, BRINE)
    for (cx, cy), r in ((T(5.3, -11.1), 2.6), (T(6.0, -10.8), 1.7)):       # (two islets)
        for gy in range(int(cy - 3), int(cy + 4)):
            for gx in range(int(cx - 3), int(cx + 4)):
                if math.hypot(gx - cx, gy - cy) <= r and d.get(gx, gy) == WATER:
                    d.put(gx, gy, FLOOR, BRINE)
    # (the Shardfall: pools of light in a broken ring round the Fallen Shard, the way to it kept)
    for gy in range(fall_c[1] - 14, fall_c[1] + 15):
        for gx in range(fall_c[0] - 20, fall_c[0] + 21):
            if d.get(gx, gy) != FLOOR or (gx, gy) in ways:
                continue
            dx, dy = (gx - fall_c[0]) / 1.4, gy - fall_c[1]
            r, a = math.hypot(dx, dy), math.atan2(dy, dx)
            if 4.5 <= r <= 6.8 + 1.2 * math.sin(3 * a) and math.sin(4 * a + 0.6) > -0.35:
                d.put(gx, gy, POOL, FALL)
            elif 9.5 <= r <= 10.6 and math.sin(7 * a) > 0.55:
                d.put(gx, gy, POOL, FALL)
    for gy in range(fall_c[1] - 2, fall_c[1] + 9):           # (a causeway to it from the south, and from the east)
        for gx in range(fall_c[0] - 1, fall_c[0] + 2):
            if d.get(gx, gy) == POOL:
                d.put(gx, gy, FLOOR, FALL)
    for gx in range(fall_c[0], fall_c[0] + 18):
        for gy in range(fall_c[1] - 1, fall_c[1] + 2):
            if d.get(gx, gy) == POOL:
                d.put(gx, gy, FLOOR, FALL)
    d.seen = d.reachable(arrive)                             # (what the water cut off: islets, nothing put on them)
    d.arrive = arrive
    d.R = R
    d.fall_c = fall_c
    d.stair = stair
    return d, seen


# ================================================================== what's put in it
def pick(pairs, rng):
    tot = sum(w for _, w in pairs)
    r = rng.uniform(0, tot)
    for v, w in pairs:
        r -= w
        if r <= 0:
            return v
    return pairs[-1][0]


def patch_noise(seed, scale=6.0):
    r = random.Random(seed)
    ph = [r.uniform(0, 100) for _ in range(6)]
    return lambda x, y: (math.sin(x / scale + ph[0]) * math.cos(y / scale + ph[1]) + 0.6 * math.sin((x + y) / (scale * 0.6) + ph[2])
                         + 0.4 * math.cos((x - y) / (scale * 1.7) + ph[3]))


def dress(d):
    """Decor, the people, the creatures, the chests and the special things."""
    rng = random.Random(99)
    R = d.R

    def floor_cells(area, interior=False):
        out = []
        ys, xs = np.nonzero((d.cell == FLOOR) & (d.area == area) & ~d.built & d.seen)
        for y, x in zip(ys, xs):
            gx, gy = x + GX0, y + GY0
            if interior and not all(d.get(gx + a, gy + b) == FLOOR for a in (-1, 0, 1) for b in (-1, 0, 1)):
                continue
            out.append((gx, gy))
        return out

    def stand(gx, gy, kind, name, opts=""):
        if kind == "NPC" and gy % YT in (0, YT - 1):      # (never on a map's top or bottom row: off the map)
            gy += 1 if gy % YT == 0 else -1
        d.ents.append((gx, gy, kind, name, opts))
        for a in (-1, 0, 1):
            for b in (-1, 0, 1):
                d.taken.add((gx + a, gy + b))

    def deco(gx, gy, name):
        if (gx, gy) not in d.taken and d.get(gx, gy) == FLOOR:
            d.decor[(gx, gy)] = name
            d.taken.add((gx, gy))

    # ----- the special places first (what's kept clear round them)
    camp = T(8.5, -12.5)
    fall = d.fall_c
    gx, gy = R["gate"][0] + 8, R["gate"][1] + 4
    stand(gx, gy, "NPC", "Ghost_Warden", "Attitude=Good Stand=1 Face=S Id=Warden_Ysolde Name=Ysolde")
    # (the camp: a tent, a fire, the cartographer and the angler, the shardstone; nothing hostile near it)
    for a in range(-5, 6):
        for b in range(-4, 5):
            if d.get(camp[0] + a, camp[1] + b) == ROCK and a * a / 30 + b * b / 20 < 1:
                d.put(camp[0] + a, camp[1] + b, FLOOR, WOOD)
    deco(camp[0], camp[1], "Campfire001")
    deco(camp[0] - 3, camp[1] - 2, "Tent001")
    deco(camp[0] + 3, camp[1] - 2, "Tent002")
    deco(camp[0] + 4, camp[1] + 1, "Crate001")
    deco(camp[0] + 4, camp[1] + 2, "Barrel001")
    deco(camp[0] - 4, camp[1] + 1, "Bedroll001")
    stand(camp[0] - 2, camp[1] + 2, "NPC", "Scholar", "Attitude=Good Zone=%s Pause=6-14 Id=Pell_Varrow Name=Pell" % "{camp}")
    stand(camp[0] + 2, camp[1] + 2, "NPC", "Fisherman", "Attitude=Good Zone=%s Pause=6-14 Id=Morrow_Angler Name=Morrow" % "{camp}")
    stand(camp[0], camp[1] - 3, "StaticObject", "Shardstone", "")
    d.ids.append((camp[0], camp[1] - 3, "Waystone_Shardfall"))
    d.ids.append((camp[0], camp[1] + 1, "Lantern_Wood_Camp"))
    d.camp = camp
    # (the Shardfall: the Fallen Shard in the middle, the Shardborn by it)
    stand(fall[0] - 1, fall[1] - 1, "StaticObject", "Fallen_Shard", "Id=The_Fallen_Shard")
    for a in (-1, 0, 1):                                     # (its foot: nobody walks through it)
        d.decor[(fall[0] + a, fall[1] + 1)] = "Stalk_Foot001"
    d.ids.append((fall[0], fall[1], "Shardfall_Crater"))
    stand(fall[0] + 3, fall[1] + 2, "NPC", "Shardborn", "Attitude=Bad Zone=%d,%d,%d,%d" % (0, 0, 0, 0))
    # (the Brinewater's mother: on the north shore, where the water's deepest)
    north = min(((gx, gy) for gx, gy in floor_cells(BRINE) if d.get(gx, gy + 1) == WATER and abs(gx - T(5.4, 0)[0]) < 10),
                key=lambda c: c[1], default=None)
    if north:
        stand(north[0], north[1], "NPC", "Brine_Mother", "Attitude=Bad")
        d.ids.append((north[0], north[1], "Brinewater_Deep"))
    # (the Hollow Marshal on the Great Hall's dais)
    hx, hy, hw, hh = R["hall"]
    stand(hx + hw // 2, hy + 3, "NPC", "Hollow_Marshal", "Attitude=Bad")
    d.ids.append((hx + hw // 2, hy + hh // 2, "Hold_Great_Hall"))
    d.ids.append((R["gate"][0] + 8, R["gate"][1] + 6, "Wardens_Hold"))
    # (Leviathan's Rest: the bones, lying east from the skull, a ribcage five tiles tall; the chest in its jaw)
    rest = T(5.0, -14.6)
    sx, sy = rest[0] - 10, rest[1]
    for i in range(9):
        a, b = i % 3, i // 3 - 1
        d.put(sx + a, sy + b, FLOOR, REST)
        d.decor[(sx + a, sy + b)] = "Leviathan_Skull%03d" % (i + 1)
        d.taken.add((sx + a, sy + b))
    for k in range(3, 22):
        x = sx + k
        if d.get(x, sy) == ROCK:
            break
        d.decor[(x, sy)] = "Leviathan_Spine001"
        d.taken.add((x, sy))
        if k % 2 == 1 and k < 17:
            for b, part in ((-2, 1), (-1, 2), (1, 3), (2, 4)):
                if d.get(x, sy + b) == FLOOR and (x, sy + b) not in d.decor:
                    d.decor[(x, sy + b)] = "Leviathan_Rib%03d" % part
                    d.taken.add((x, sy + b))
    stand(sx + 1, sy + 2, "StaticObject", "Chest", "Id=Leviathans_Jaw")
    d.ids.append((sx + 8, sy + 3, "Leviathans_Rest"))
    # (the Singing Geode: the Galleries' far end)
    geo = T(11.7, -11.8)
    stand(geo[0], geo[1], "StaticObject", "Singing_Geode", "Id=The_Singing_Geode")
    d.ids.append((geo[0], geo[1] + 1, "Glimmering_Galleries"))

    # ----- the Galleries' secret grotto: through a wall that isn't there, under a roof of black
    gro = secret_grotto(d)

    # ----- the Hold's rooms, each furnished for what it was
    furnish(d, stand, deco)

    # ----- the Stair: its foot (up to Gull Point), the vestibule's statues
    ax, ay = d.arrive
    d.put(ax, ay + 3, FLOOR, STAIR)
    d.tile[(ax, ay + 3)] = "Cave_Steps001"
    d.ids.append((ax, ay + 3, "Gull_Stair_Foot"))
    d.taken |= {(ax + a, ay + b) for a in (-1, 0, 1) for b in range(0, 5)}
    for gx in (302, 310):
        d.decor[(gx, -110)] = "Warden_Statue001"
        d.taken.add((gx, -110))
    d.decor[(304, -106)] = "Warden_Brazier001"
    d.decor[(308, -106)] = "Warden_Brazier001"
    d.ids.append((306, -107, "Wardens_Gate"))
    d.ids.append((d.stair[len(d.stair) // 2][0], d.stair[len(d.stair) // 2][1], "Drowned_Stair"))

    # ----- the decor, area by area (never on the ways through, nothing that blocks where it's narrow)
    lanes = set()
    for centre in d.paths:
        lanes |= {(x, y) for x, y in centre}
    for area, (pairs, dens) in DECOR.items():
        if not pairs:
            continue
        cells = floor_cells(area)
        rng.shuffle(cells)
        want = len(cells) * dens // 100
        put = 0
        for gx, gy in cells:
            if put >= want:
                break
            if (gx, gy) in d.taken or (gx, gy) in lanes or (gx, gy) in d.decor:
                continue
            name = pick(pairs, rng)
            if name.startswith("*"):
                name = name[1:]
                if not all(d.get(gx + a, gy + b) == FLOOR for a in (-1, 0, 1) for b in (-1, 0, 1)):
                    continue
                if any((gx + a, gy + b) in d.decor and d.decor[(gx + a, gy + b)] in BLOCKERS
                       for a in (-1, 0, 1) for b in (-1, 0, 1)):
                    continue                             # (two that block, never side by side: always a way between)
            d.decor[(gx, gy)] = name
            put += 1
    # (the Brinewater's weed on the shore, the camp kept clear)
    for a in range(-6, 7):
        for b in range(-5, 6):
            c = (camp[0] + a, camp[1] + b)
            if d.decor.get(c, "").startswith(("Lantern_Cap", "Mushroom")):
                del d.decor[c]

    # ----- the tall things: lantern caps as tall as houses in the wood, crystal spires in the galleries and the Shardfall
    for area, kind, per in ((WOOD, "Lantern_Tree", 45), (GALLERY, "Shard_Spire", 90), (FALL, "Shard_Spire", 70)):
        cells = floor_cells(area, interior=True)
        rng.shuffle(cells)
        want, put = len(cells) // per, 0
        for gx, gy in cells:
            if put >= want:
                break
            if not (3 <= gy % YT <= YT - 1 and 1 <= gx % XT <= XT - 2):
                continue                                 # (all of it on its own map: none off its top or sides)
            if any((gx + a, gy + b) in d.taken or (gx + a, gy + b) in lanes or (gx + a, gy + b) in d.decor
                   for a in (-1, 0, 1) for b in (-1, 0, 1)):
                continue
            if math.hypot(gx - camp[0], gy - camp[1]) < 6 or math.hypot(gx - fall[0], gy - fall[1]) < 5:
                continue
            d.decor[(gx, gy)] = "Stalk_Foot001"
            d.tall.append((gx, gy, "%s%03d" % (kind, 1 + put % 3)))
            d.taken.add((gx, gy))
            put += 1

    # ----- glowfin in the Brinewater, off its shore
    spots = [(gx, gy) for gx, gy in floor_cells(BRINE) if any(d.get(gx + a, gy + b) == WATER for a, b in ((0, 1), (1, 0), (-1, 0), (0, -1)))]
    rng.shuffle(spots)
    done = []
    for gx, gy in spots:
        w = next(((gx + a, gy + b) for a, b in ((0, 1), (1, 0), (-1, 0), (0, -1)) if d.get(gx + a, gy + b) == WATER), None)
        if w and all(abs(w[0] - a) + abs(w[1] - b) > 12 for a, b in done):
            d.ents.append((w[0], w[1], "StaticObject", "Glowfin_Spot", ""))
            done.append(w)
        if len(done) >= 5:
            break

    # ----- the creatures, area by area
    plan = [(STAIR, ["Brine_Crawler", "Drowned_Warden", "Glass_Bat"], 150),
            (GALLERY, ["Prism_Crawler", "Shard_Wraith", "Crystal_Golem", "Glass_Bat"], 120),
            (BRINE, ["Deep_Lurker", "Brine_Crawler", "Drowned_Warden"], 130),
            (WOOD, ["Spore_Shambler", "Lantern_Moth"], 130),
            (REST, ["Fossil_Horror", "Chalk_Wraith"], 120),
            (FALL, ["Shard_Drake", "Shard_Wraith", "Crystal_Golem"], 110)]
    vest_x, vest_y = 306, -108
    for area, kinds, per in plan:
        cells = floor_cells(area)
        rng.shuffle(cells)
        n = max(4, len(cells) // per)
        k = 0
        for gx, gy in cells:
            if k >= n:
                break
            if (gx, gy) in d.taken or (gx, gy) in d.decor or (gx % XT) in (0,) or (gy % YT) in (0, YT - 1):
                continue
            if math.hypot(gx - camp[0], gy - camp[1]) < 16 or math.hypot(gx - vest_x, gy - vest_y) < 14 \
                    or math.hypot(gx - d.arrive[0], gy - d.arrive[1]) < 14:
                continue
            if any(math.hypot(gx - e[0], gy - e[1]) < 5 for e in d.ents if e[2] == "NPC"):
                continue
            room = sum(1 for a in range(-3, 4) for b in range(-3, 4) if d.get(gx + a, gy + b) == FLOOR
                       and d.decor.get((gx + a, gy + b)) not in BLOCKERS | {"Stalk_Foot001"}
                       and (gx + a) // XT == gx // XT and (gy + b) // YT == gy // YT)
            if room < 12:                                    # (somewhere to roam, on its own map)
                continue
            if any(d.decor.get((gx + a, gy + b)) in BLOCKERS | {"Stalk_Foot001"} for a in (-1, 0, 1) for b in (-1, 0, 1, 2)):
                continue                                     # (nothing it can't walk through where it stands)
            stand(gx, gy, "NPC", kinds[k % len(kinds)], "Attitude=Bad {zone}")
            k += 1
    d.grotto = gro


BLOCKERS = {"Shard_Crystal001", "Shard_Crystal002", "Shard_Crystal003", "Shard_Crystal004", "Lantern_Cap001", "Lantern_Cap002",
            "Lantern_Cap003", "Shardglass_Rock001"}


def secret_grotto(d):
    """A crystal grotto behind a Galleries wall: a hollow wall face, a chamber under a black roof, a chest."""
    found = None
    for cx0, cy0 in (T(11.6, -10.6), T(10.8, -9.6), T(11.7, -11.8), T(10.5, -12.0), T(9.9, -10.9)):
        for dx in (0, -2, 2, -4, 4, -6, 6):
            cx, y = cx0 + dx, cy0
            if d.get(cx, y) != FLOOR or d.area_of(cx, y) != GALLERY:
                continue
            while d.get(cx, y - 1) == FLOOR:              # (north from the middle to its wall: the grotto beyond it)
                y -= 1
            wall_y = y - 1
            room = [(cx + a, wall_y - 1 - b) for a in range(-3, 4) for b in range(0, 4)]
            if all(d.get(x, yy) == ROCK and d.inside(x, yy, 4) for x, yy in room) and not any(
                    d.get(x, yy) != ROCK for x in range(cx - 5, cx + 6) for yy in range(wall_y - 6, wall_y)):
                found = (cx, wall_y, room)
                break
        if found:
            break
    if not found:
        print("No room for the grotto")
        return None
    cx, wall_y, room = found
    for x, yy in room:
        d.put(x, yy, FLOOR, GALLERY)
        d.keep[yy - GY0, x - GX0] = True
        d.roof[(x, yy)] = "Hidden_Dark001.97"
    d.put(cx, wall_y, FLOOR, GALLERY)
    d.tile[(cx, wall_y)] = "Cave_Wall_Hollow001"            # (from outside, only a wall: its face isn't under the roof)
    d.triggers.append((cx, wall_y, "Hidden_Way_Grotto"))
    for x in range(cx - 4, cx + 5):                         # (its walls under the black roof too: nothing shows outside)
        for yy in range(wall_y - 5, wall_y):
            if d.get(x, yy) == ROCK:
                d.roof[(x, yy)] = "Hidden_Dark001.97"
    d.ents.append((cx, wall_y - 4, "StaticObject", "Chest", "Id=Prism_Grotto"))
    for x, yy in ((cx - 3, wall_y - 4), (cx + 3, wall_y - 4), (cx - 2, wall_y - 1), (cx + 2, wall_y - 1)):
        d.decor[(x, yy)] = "Shard_Crystal003" if yy == wall_y - 4 else "Shard_Crystal004"
    d.taken |= set(room) | {(cx, wall_y), (cx, wall_y + 1)}
    return (cx, wall_y)


def furnish(d, stand, deco):
    R = d.R

    def row(y, xs, name):
        for x in xs:
            if any(d.keep[y + b - GY0, x + a - GX0] for a, b in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1))):
                continue                                 # (never in a doorway, nor across one)
            d.decor[(x, y)] = name
            d.taken.add((x, y))

    # (the Gatehall: statues of the Wardens down its sides, braziers by the gate)
    x, y, w, h = R["gate"]
    row(y, range(x + 1, x + w - 1, 3), "Warden_Statue001")
    row(y + h - 2, (x + 5, x + w - 6), "Warden_Brazier001")
    for k in range(2, h - 2, 3):
        row(y + k, (x + 2, x + w - 3), "Pillar001")
    # (the barracks: bunks against the back wall, a chest, the dead at ease)
    x, y, w, h = R["barracks"]
    for bx in range(x + 1, x + w - 1, 3):
        if any(d.keep[y - 1 - GY0, bx + a - GX0] for a in (-1, 0, 1)):
            continue
        d.decor[(bx, y)] = "Bed001"
        d.decor[(bx, y + 1)] = "Bed002"
        d.taken |= {(bx, y), (bx, y + 1)}
    stand(x + w - 2, y + h - 2, "StaticObject", "Chest", "Id=Wardens_Footlocker")
    row(y + h - 1, (x + 2, x + 6), "Bones001")
    row(y + 4, (x + 5, x + 9), "Table001")
    # (the cells: bars across, a prisoner who stayed)
    x, y, w, h = R["cells"]
    for k in range(0, w, 4):
        for yy in range(y, y + 4):
            if k > 0:
                d.decor[(x + k, yy)] = "Cell_Bars001"
                d.taken.add((x + k, yy))
        if k + 2 < w:
            d.decor[(x + k + 1, y + 4)] = "Cell_Bars001"
            d.decor[(x + k + 3, y + 4)] = "Cell_Bars001"
            d.taken |= {(x + k + 1, y + 4), (x + k + 3, y + 4)}
    row(y + 1, (x + 2, x + 9), "Bones002")
    row(y + 2, (x + 14,), "Bedroll001")
    # (the Great Hall: two rows of pillars, the dais and its throne, banners and braziers)
    x, y, w, h = R["hall"]
    for k in range(3, h - 2, 3):
        row(y + k, (x + 4, x + w - 5), "Pillar001")
    if not d.keep[y - GY0, x + w // 2 - GX0]:              # (the throne's a floor tile of its own, as in Galaith)
        d.tile[(x + w // 2, y)] = "Throne001"
    row(y, (x + 3, x + w - 4), "Banner001")
    row(y + 1, (x + w // 2 - 3, x + w // 2 + 3), "Warden_Brazier001")
    row(y + h - 1, (x + 6, x + w - 7), "Warden_Brazier001")
    # (the library: shelves on the back wall, the journals on their lecterns)
    x, y, w, h = R["library"]
    row(y, range(x, x + w, 2), "Bookshelf001")
    for k in range(3, w - 2, 4):
        row(y + 4, (x + k,), "Bookshelf001")
        row(y + 8, (x + k,), "Bookshelf001")
    for i, (a, b) in enumerate(((2, 2), (w // 2, 6), (w - 3, 10)), 1):
        stand(x + a, y + b, "StaticObject", "Wardens_Journal", "Id=Wardens_Journal_%d" % i)
    row(y + h - 1, (x + 1, x + w - 2), "Candles001")
    # (the Chapel of the Flame: its altar, the Wardens' Flame either side, statues)
    x, y, w, h = R["chapel"]
    row(y, (x + w // 2,), "Altar001")
    row(y, (x + w // 2 - 2, x + w // 2 + 2), "Warden_Brazier001")
    row(y + 3, range(x + 2, x + w - 2, 3), "Bench001")
    row(y + 6, range(x + 2, x + w - 2, 3), "Bench001")
    row(y + h - 1, (x + 1, x + w - 2), "Warden_Statue001")
    # (the Reliquary: what the Order kept, for whoever finished the watch)
    x, y, w, h = R["reliquary"]
    stand(x + w // 2, y + 1, "StaticObject", "Chest", "Id=Wardens_Reliquary")
    row(y, (x + 2, x + w - 3), "Warden_Statue001")
    row(y + h - 1, (x + 2, x + w - 3), "Warden_Brazier001")
    d.ids.append((x + w // 2, y + 4, "Wardens_Reliquary_Room"))
    # (the ossuary: tombs in rows, their lids moved)
    x, y, w, h = R["ossuary"]
    for yy in range(y + 1, y + h - 1, 3):
        row(yy, range(x + 2, x + w - 2, 3), "Warden_Tomb001")
    stand(x + w - 2, y, "StaticObject", "Chest", "Id=Wardens_Ossuary")
    # (the armoury: racks of crates and barrels, a forge gone cold)
    x, y, w, h = R["armoury"]
    row(y, range(x + 1, x + w - 1, 2), "Crate002")
    row(y + h - 1, range(x + 2, x + w - 2, 3), "Barrel002")
    stand(x + w // 2, y + 4, "StaticObject", "Chest", "Id=Wardens_Armoury")
    # (the cistern: a long pool of the deep's black water, a walk round it)
    x, y, w, h = R["cistern"]
    for yy in range(y + 2, y + h - 2):
        for xx in range(x + 3, x + w - 3):
            d.put(xx, yy, WATER, HOLD, True)
    # (the hold's guards: Hollow Wardens and Spellbinders in its rooms, Sentinels at its doors)
    guards = [("gate", "Glass_Sentinel", 2), ("barracks", "Hollow_Warden", 3), ("cells", "Hollow_Warden", 2),
              ("hall", "Hollow_Warden", 3), ("hall", "Warden_Spellbinder", 1), ("library", "Warden_Spellbinder", 2),
              ("chapel", "Warden_Spellbinder", 1), ("chapel", "Hollow_Warden", 1), ("ossuary", "Hollow_Warden", 3),
              ("armoury", "Glass_Sentinel", 2), ("cistern", "Drowned_Warden", 2), ("reliquary", "Glass_Sentinel", 1)]
    rng = random.Random(5)
    for room, kind, n in guards:
        x, y, w, h = R[room]
        cells = [(a, b) for a in range(x + 1, x + w - 1) for b in range(y + 2, y + h - 1)
                 if (a, b) not in d.taken and (a, b) not in d.decor and d.get(a, b) == FLOOR and (b % YT) not in (0, YT - 1)]
        rng.shuffle(cells)
        placed = 0
        for a, b in cells:
            if placed >= n:
                break
            if room == "gate" and math.hypot(a - (x + 8), b - (y + 4)) < 5:
                continue
            if any(math.hypot(a - e[0], b - e[1]) < 3 for e in d.ents if e[2] == "NPC"):
                continue
            stand(a, b, "NPC", kind, "Attitude=Bad Zone={room}" + (" Face=S Cone=140" if kind == "Glass_Sentinel" else ""))
            placed += 1
    # (traps in the corridors: an old dungeon's)
    for (a, b), kind in (((250, -337), "Darts"), ((250, -321), "Gas"), ((262, -316), "Weakness"), ((273, -336), "Alarm"),
                         ((294, -326), "Darts"), ((305, -316), "Pit"), ((303, -345), "Weakness")):
        d.triggers.append((a, b, "Trap_" + kind))
    d.rooms = R


# ================================================================== the maps
def map_name(mx, my):
    return "%d,%d,%d" % (mx, my, Z)


def write_maps(d):
    rng = random.Random(7)
    noise = {a: patch_noise(100 + a, 5.5) for a in FLOORS}
    built_cells = {}
    maps = {}

    def open_at(gx, gy):
        return d.get(gx, gy) in (FLOOR, WATER, POOL)

    for my in range(MY0, MY1 + 1):
        for mx in range(MX0, MX1 + 1):
            rows = [["Black001"] * XT for _ in range(YT)]
            any_ = False
            for y in range(YT):
                for x in range(XT):
                    gx, gy = mx * XT + x, my * YT + y
                    c = d.get(gx, gy)
                    a = d.area_of(gx, gy)
                    if c == FLOOR:
                        if d.is_built(gx, gy):
                            t = "Warden_Flag001"
                        else:
                            pairs = FLOORS.get(a, FLOORS[STAIR])
                            v = noise.get(a, noise[STAIR])(gx, gy)
                            t = pairs[0][0] if len(pairs) == 1 or v < 0.9 else pick(pairs[1:], random.Random(gx * 7919 + gy))
                        t = d.tile.get((gx, gy), t)
                    elif c == WATER:
                        t = "Brine001"
                    elif c == POOL:
                        t = "Shard_Pool001"
                    else:
                        near = [(gx + a2, gy + b2) for a2 in (-1, 0, 1) for b2 in (-1, 0, 1) if (a2 or b2)]
                        areas = [d.area_of(*n) for n in near if open_at(*n)]
                        if not any(open_at(*n) for n in near):
                            t = "Black001"
                            if (gx, gy) in d.roof:
                                t = "Black001"
                        else:
                            built = d.is_built(gx, gy) and any(d.is_built(*n) and open_at(*n) for n in near)
                            south_open = open_at(gx, gy + 1)
                            if built:
                                t = pick(FACES[HOLD], random.Random(gx * 31 + gy * 17)) if south_open else "Warden_Wall001"
                            else:
                                aa = max(set(areas), key=areas.count) if areas else STAIR
                                t = pick(FACES.get(aa, FACES[STAIR]), random.Random(gx * 31 + gy * 17)) if south_open \
                                    else ROCKS.get(aa, "Cave_Wall001")
                        t = d.tile.get((gx, gy), t)
                    over = ""
                    if (gx, gy) in d.decor and c == FLOOR:
                        over += "+Decor(%s)" % d.decor[(gx, gy)]
                    if (gx, gy) in d.roof:
                        over += "+Roof(%s)" % d.roof[(gx, gy)]
                    rows[y][x] = t + over
                    if t != "Black001":
                        any_ = True
            if any_:
                maps[(mx, my)] = rows
    # (the lines: Ids, triggers, locks, things and creatures, each on its own map)
    lines = {k: [] for k in maps}

    def local(gx, gy):
        mx, my = gx // XT, gy // YT
        return (mx, my), gx - mx * XT + 1, gy - my * YT + 1

    for gx, gy, pid in d.ids:
        k, x, y = local(gx, gy)
        lines[k].append("Id\t%s\t%d\t%d" % (pid, x, y))
    for gx, gy, script in d.triggers:
        k, x, y = local(gx, gy)
        lines[k].append("Trigger\t%s\t%d\t%d" % (script, x, y))
    for gx, gy, cond, msg in d.locks:
        k, x, y = local(gx, gy)
        lines[k].append("Lock\t%d\t%d\t%s\t%s" % (x, y, cond, msg))
    for gx, gy, kind, name, opts in d.ents:
        k, x, y = local(gx, gy)
        if "{zone}" in opts:
            opts = opts.replace("{zone}", "Zone=%d,%d,%d,%d Chase=%d,%d,%d,%d" % (
                max(1, x - 3), max(2, y - 3), min(XT, x + 3), min(YT - 1, y + 3),
                max(1, x - 7), max(2, y - 7), min(XT, x + 7), min(YT - 1, y + 7)))
        if "{camp}" in opts:
            opts = opts.replace("{camp}", "%d,%d,%d,%d" % (max(1, x - 3), max(2, y - 2), min(XT, x + 3), min(YT - 1, y + 2)))
        if "{room}" in opts:
            room = next(r for r in d.rooms.values() if r[0] <= gx < r[0] + r[2] and r[1] <= gy < r[1] + r[3])
            rx0, ry0 = room[0] - k[0] * XT + 1, room[1] - k[1] * YT + 1
            zx0, zy0 = max(1, rx0), max(2, ry0)
            zx1, zy1 = min(XT, rx0 + room[2] - 1), min(YT - 1, ry0 + room[3] - 1)
            opts = opts.replace("{room}", "%d,%d,%d,%d Chase=%d,%d,%d,%d" % (
                zx0, zy0, zx1, zy1, max(1, zx0 - 3), max(2, zy0 - 3), min(XT, zx1 + 3), min(YT - 1, zy1 + 3)))
        if name == "Shardborn":
            opts = "Attitude=Bad Zone=%d,%d,%d,%d Chase=%d,%d,%d,%d" % (max(1, x - 5), max(2, y - 4), min(XT, x + 5), min(YT - 1, y + 4),
                                                                      max(1, x - 9), max(2, y - 7), min(XT, x + 9), min(YT - 1, y + 7))
        if name in ("Brine_Mother", "Hollow_Marshal"):
            opts = "Attitude=Bad Zone=%d,%d,%d,%d Chase=%d,%d,%d,%d" % (max(1, x - 4), max(2, y - 2), min(XT, x + 4), min(YT - 1, y + 4),
                                                                      max(1, x - 9), max(2, y - 6), min(XT, x + 9), min(YT - 1, y + 8))
        dy = -8 if kind == "NPC" else 0
        if name in ("Brine_Mother", "Shardborn", "Shard_Drake"):
            dy = -24                                         # (half again as big: its feet on the same ground)
        elif name in ("Hollow_Marshal", "Fossil_Horror"):
            dy = -16
        if name == "Fallen_Shard":
            dy = -40
        lines[k].append(obj_line(kind, name, x, y, opts, dy=dy))
    for gx, gy, name in d.tall:                               # (its foot on the tile, the rest over the ones above)
        k, x, y = local(gx, gy)
        w, h = (48, 72) if name.startswith("Lantern_Tree") else (32, 72)
        lines[k].append("StaticObject\t%s\t%d\t%d" % (name, (x - 1) * 32 - (w - 32) // 2, (y - 1) * 32 - (h - 32) + 2))
    for (mx, my), rows in maps.items():
        m = Map(map_name(mx, my), new=True)
        m.rows = rows
        m.ents = lines[(mx, my)]
        m.save()
    print("The Shardfall Deep: %d maps on level %d" % (len(maps), Z))
    return sorted(maps)


def gull_point():
    """The tip of Ashford's peninsula: a knoll of rock with the sea cave in it, Nell and Bryony's cottage behind."""
    m = Map(SURFACE)
    if any("Gull_Point_Cave" in ln for ln in m.ents):
        return
    rng = random.Random(12)
    rows = {4: (7, 8), 5: (5, 9), 6: (4, 10), 7: (4, 9), 8: (5, 9)}  # (a rock, worn round, jutting into the sea)
    knoll = [(x, y) for y, (x0, x1) in rows.items() for x in range(x0, x1 + 1)]
    for x, y in knoll:
        m.set(x, y, tile="Peak%03d" % rng.randint(1, 6), decor="")
    m.set(MOUTH[0], MOUTH[1], tile="Gull_Cave001", decor="")
    m.set(MOUTH[0], MOUTH[1] + 1, tile="Sand001", decor="")
    SK.place_id(m, "Gull_Point_Cave", MOUTH[0], MOUTH[1])
    SK.place_id(m, "Gull_Point", 12, 10)
    # (the cottage: timber and thatch, two beds against its back wall)
    for y in range(11, 18):
        for x in range(9, 17):
            m.set(x, y, tile="Grass001", decor="")
    SK.building(m, 10, 12, 15, 16, door=12, wall="Timber001", roof="Thatch", chimney=14)
    for bx in (11, 14):
        m.set(bx, 12, decor="Bed001")
        m.set(bx, 13, decor="Bed002")
    m.set(13, 15, decor="Table001")
    m.set(12, 14, decor="Chair001")
    m.ents.append(obj_line("NPC", "Woman", 12, 10, "Attitude=Good Zone=8,9,16,11 Pause=6-14 Id=Nell_Tarrow Name=Nell "
                           "Home=11,13,14,15 Bed=11,12", dy=-8))
    m.ents.append(obj_line("NPC", "Old_Woman", 14, 18, "Attitude=Good Zone=10,17,16,19 Pause=8-16 Id=Bryony_Tarrow Name=Bryony "
                           "Home=11,13,14,15 Bed=14,12", dy=-8))
    m.save()
    print("Gull Point: the sea cave and the cottage, on %s" % SURFACE)


# ================================================================== the things: Entities.ini
def thing_data():
    S = SK.section
    S(SK.ENTS, "Fallen_Shard", [("Type", "StaticObject"), ("Use.Words", "Touch,Draw From,Examine"), ("Solid", "1"),
                                ("Light", "140"), ("Anim.Frames", "4"), ("Anim.Speed", "260"),
                                ("Examine.Info", "A crystal taller than a house, standing in the glass it made when it fell. Light "
                                 "breathes in it, slow, like something asleep.")])
    for n, cap in enumerate(("green", "orange", "blue"), 1):
        S(SK.ENTS, "Lantern_Tree%03d" % n, [("Type", "StaticObject"), ("Use.Words", "Examine"), ("Solid", "1"), ("Light", "60"),
                                            ("Examine.Info", "A mushroom as tall as a house, its %s cap glowing from "
                                             "underneath. Spores drift down from it, slow as snow." % cap)])
        S(SK.ENTS, "Shard_Spire%03d" % n, [("Type", "StaticObject"), ("Use.Words", "Examine"), ("Solid", "1"), ("Light", "50"),
                                           ("Examine.Info", "A spire of crystal twice your height. It rings, very faintly, when "
                                            "you stand close.")])
    S(SK.ENTS, "Singing_Geode", [("Type", "StaticObject"), ("Use.Words", "Listen,Examine"), ("Solid", "1"), ("Light", "50"),
                                 ("Examine.Info", "A stone split open, full of crystals. It's humming.")])
    S(SK.ENTS, "Glowfin_Spot", [("Type", "StaticObject"), ("Use.Words", "Fish"), ("Solid", "0"), ("Anim.Frames", "4"),
                                ("Anim.Speed", "240"), ("Light", "30"),
                                ("Examine.Info", "Lights move under the black water: glowfin. Fishing 22.")])
    S(SK.ENTS, "Wardens_Journal", [("Type", "StaticObject"), ("Use.Words", "Read,Examine"), ("Solid", "1"),
                                   ("Examine.Info", "A Warden's journal, open on its lectern where it was left.")])
    items = [
        ("Wardens_Signet", [("Display.Name", "Warden's Signet"), ("Stackable", "1"), ("Droppable", "0"), ("Value", "0"),
                            ("Use.Words", "Examine"),
                            ("Examine.Info", "A ring of grey metal set with a chip of violet glass, cold as the sea it came "
                             "out of.")]),
        ("Marshals_Seal", [("Display.Name", "Marshal's Seal"), ("Stackable", "1"), ("Droppable", "0"), ("Value", "0"),
                           ("Examine.Info", "Marshal Corvane's seal of office: the Glass Wardens' shard, in silver.")]),
        ("Raw_Glowfin", [("Examine.Info", "A glowfin, its scales still giving off light. Cook it on a fire or a range "
                          "(Cooking 22)."), ("Stackable", "0"), ("Value", "60")]),
        ("Cooked_Glowfin", [("Use.Words", "Eat"), ("Examine.Info", "Glowfin, cooked: rich and strange, and it warms you to "
                             "your toes. Heals 20."), ("Stackable", "0"), ("Value", "90"), ("Food.Value", "20")]),
        ("Shardglass_Blade", [("Display.Name", "Shardglass Blade"), ("Slot", "Weapon"), ("Attack", "12"), ("Defence", "1"),
                              ("Magic", "2"), ("Requires", "Strength 20"), ("Durability", "720"), ("Stackable", "1"),
                              ("Value", "0"), ("Droppable", "0"),
                              ("Examine.Info", "A blade of the Fallen Shard's own glass, grown, not forged. It hums when you "
                               "swing it.")]),
        ("Wardens_Aegis", [("Display.Name", "Wardens' Aegis"), ("Slot", "Shield"), ("Attack", "0"), ("Defence", "10"),
                           ("Magic", "1"), ("Requires", "Defence 20"), ("Durability", "720"), ("Stackable", "1"),
                           ("Value", "0"), ("Droppable", "0"),
                           ("Examine.Info", "The Glass Wardens' shield, kept for whoever finished their watch.")]),
        ("Brine_Pearl_Ring", [("Display.Name", "Brine Pearl Ring"), ("Slot", "Ring"), ("Magic", "3"), ("Defence", "2"),
                              ("Stackable", "1"), ("Value", "0"), ("Droppable", "0"),
                              ("Examine.Info", "A pearl as big as a thumbnail, out of the Brine Mother. It's cold, and it "
                               "never gets warmer.")]),
    ]
    for name, keys in items:
        S(SK.ENTS, name, [("Type", "MapItem")] + keys)
    gath = p("data", "Gathering.ini")
    SK.set_section(gath, "Glowfin", ["Gives=Raw_Glowfin", "Source=Glowfin_Spot", "Verb=Use", "Tool=Fishing_Rod",
                                     "Skill=Fishing", "Level=22", "XP=0.8",
                                     "Where=Glowfin spots in the Brinewater, deep in the Shardfall Deep (a rod and bait; "
                                     "each catch uses one bait)"], after="Swordfish")
    shards = Ini(p("data", "Shards.ini"))
    if shards.get("Shards", "Shardfall.Draw") is None:
        shards.section("Shards")[1].append((None, "; Shardfall.Draw: the Shards the Fallen Shard gives whoever finished the "
                                                  "watch, once every Shardfall.Draw.Hours (real) hours."))
    for k, v in (("Shardfall.Draw", "10"), ("Shardfall.Draw.Hours", "20"), ("Shardstone.Shardfall", "30"),
                 ("Shardfall.Seal", "100")):
        shards.set("Shards", k, v, overwrite=False)
    shards.save(p("data", "Shards.ini"))
    SK.set_section(p("data", "Shardstones.ini"), "Shardfall", ["Title=The Shardfall Deep"])


def config_data(names):
    """The Deep is dim (sky.js): its maps, the dark's colour and the glow of what's lit in it."""
    SK.section(SK.CONFIG, "Darkness", [("Maps", " ".join(names)), ("Colour", "8 6 22 205"), ("Glow.Colour", "34 18 60"),
                                       ("Player.Light", "150")])


def labels():
    for group, label, where in (("Regions", "The Shardfall Deep", "Lantern_Wood_Camp"),
                                ("Places", "Gull Point", "Gull_Point"),
                                ("Places", "The Drowned Stair", "Drowned_Stair"),
                                ("Places", "The Wardens' Gate", "Wardens_Gate"),
                                ("Places", "The Glimmering Galleries", "Glimmering_Galleries"),
                                ("Places", "The Brinewater", "Brinewater_Deep"),
                                ("Places", "The Lantern Wood", "Lantern_Wood_Camp"),
                                ("Places", "Leviathan's Rest", "Leviathans_Rest"),
                                ("Places", "The Wardens' Hold", "Wardens_Hold"),
                                ("Places", "The Shardfall", "Shardfall_Crater")):
        SK.place_label(group, label, where)


# ================================================================== the quests
GATE = "ShardfallGate"
CHART = "DeepChartQuest"
BRINEQ = "BrineQuest"
WARD = "WardenQuest"
FALLQ = "FallenShardQuest"
CHART_SPOTS = [("Brinewater", "Brinewater_Deep", "the Brinewater"), ("Rest", "Leviathans_Rest", "Leviathan's Rest"),
               ("Geode", "Glimmering_Galleries", "the singing stone"), ("Hold", "Wardens_Hold", "the Wardens' Hold"),
               ("Fall", "Shardfall_Crater", "the Shardfall")]


def quests():
    SK.quest("Glass in the Nets", "Woman", GATE, {
        0: "A fisherwoman at Gull Point, the tip of Ashford's peninsula, has been pulling glass out of the sea. It glows.",
        1: "Nell Tarrow's nets come up full of glass that glows. Find out where it comes from.",
        2: "Under Gull Point, a door of black glass, sealed, a small round hollow in its middle. Tell Nell.",
        3: "Nell says her grandmother Bryony remembers the old stories. Ask her.",
        4: "Bryony gave you a Warden's signet, her husband's find. It's cold: wake it at the door, with Shards and the knack "
           "(Shardcraft 15).",
    }, 5, markers={0: "Nell_Tarrow", 1: "Gull_Point_Cave", 2: "Nell_Tarrow", 3: "Bryony_Tarrow", 4: "Shardfall_Seal"},
        kind="Side", requires="Passage to the Mainland", level=LEVEL)
    SK.section(SK.QUESTS, "Glass in the Nets", [("Reward.Shards", "40"), ("Reward.XP", "Shardcraft 3"),
                                                ("Rumour", "They say the nets come up glowing off Gull Point, north of Ashford."),
                                                ("Rumour.2", "There's a fisherwoman out on Gull Point selling sea glass that "
                                                 "shines in the dark. Won't say where she gets it.")])
    SK.quest("Charting the Deep", "Scholar", CHART, {
        0: "A cartographer has a camp in the Lantern Wood, deep under the sea, and wants someone to walk where she can't.",
        1: "Pell Varrow wants five places of the deep set on her chart: the Brinewater, Leviathan's Rest, the singing stone, "
           "the Wardens' Hold and the Shardfall. Stand in each.",
        2: "Every place is on the chart. Take it back to Pell.",
    }, 3, markers={0: "Pell_Varrow", 1: ";".join(s[1] for s in CHART_SPOTS), 2: "Pell_Varrow"}, kind="Side",
        requires="Glass in the Nets", level=LEVEL)
    SK.section(SK.QUESTS, "Charting the Deep", [("Reward.Items", "Gold_Coin(s) 600"), ("Reward.Shards", "40"),
                                                ("Reward.XP", "Defence 3 Hitpoints 3"),
                                                ("Rumour", "A cartographer went down under Gull Point with a lantern and a "
                                                 "great deal of paper. She's still down there, they say, drawing.")])
    SK.quest("The Brine Mother", "Fisherman", BRINEQ, {
        0: "An angler in the Lantern Wood fishes the Brinewater, and there's something in it he'd like dead.",
        1: "Morrow wants the Brine Mother dead: she took his boat, and his partner in it. She keeps to the Brinewater's north "
           "shore.",
        2: "The Brine Mother is dead. Tell Morrow.",
    }, 3, markers={0: "Morrow_Angler", 1: "Brinewater_Deep", 2: "Morrow_Angler"}, kind="Side", requires="Glass in the Nets",
        level=LEVEL)
    SK.section(SK.QUESTS, "The Brine Mother", [("Reward.Items", "Brine_Pearl_Ring 1 Gold_Coin(s) 500"), ("Reward.Shards", "30"),
                                               ("Reward.XP", "Strength 3 Fishing 2"),
                                               ("Rumour", "An angler fishes a lake under the sea, below Gull Point. He wants "
                                                "something in it dead.")])
    SK.quest("The Last Watch", "Ghost_Warden", WARD, {
        0: "Something keeps the gate of the Wardens' Hold, deep under the sea. It isn't alive, and it isn't hostile.",
        1: "Ysolde, the last of the Glass Wardens, asks you to end Marshal Corvane, who listened to the Shard too long. He "
           "keeps the Great Hall.",
        2: "The Hollow Marshal is dead. Take his seal to Ysolde.",
    }, 3, markers={0: "Warden_Ysolde", 1: "Hold_Great_Hall", 2: "Warden_Ysolde"}, kind="Side", requires="Glass in the Nets",
        level=LEVEL)
    SK.section(SK.QUESTS, "The Last Watch", [("Reward.Shards", "60"), ("Reward.XP", "Strength 4 Defence 4"),
                                             ("Rumour", "Fishermen off Gull Point tell of a light under the water, and a "
                                              "woman's voice calling the watch.")])
    SK.quest("The Fallen Shard", "Ghost_Warden", FALLQ, {
        0: "With the Marshal gone, the Wardens' charge is stirring. Ysolde has one more thing to ask.",
        1: "Ysolde says the Shardborn, the Fallen Shard's own guardian, is waking. Put it down, in the Shardfall, west of the "
           "Hold through the Watch Gallery.",
        2: "The Shardborn is broken. Lay your hand on the Fallen Shard.",
    }, 3, markers={0: "Warden_Ysolde", 1: "Shardfall_Crater", 2: "Shardfall_Crater"}, kind="Side", requires="The Last Watch",
        level=LEVEL)
    SK.section(SK.QUESTS, "The Fallen Shard", [("Reward.Items", "Shardglass_Blade 1"), ("Reward.Shards", "80"),
                                               ("Reward.XP", "Shardcraft 5 Strength 3"),
                                               ("Rumour", "The ghost at the Wardens' Hold still has a watch to finish, they "
                                                "say, and nobody left to finish it.")])


def scripts(grotto_map):
    W = lambda name, rows: SK.write_script(name, rows, MAKER)    # noqa: E731
    far = [("@far",), ("Display.Message", "DarkRed", "You are too far away!", "Denied"), ("End",)]
    # ----- in and out
    sx, sy = 306 - 12 * XT, -99 - (-5) * YT                       # (the arrival cave, on 12,-5,-1)
    W("Enter Gull_Cave", [(">Distance.From.Clicked.Tile", "48", "@far"), ("Play.Sound", "Ladder"), ("Wait", "0.4"),
                          ("Display.Message", "Cyan", "You climb down into the sea cave. The sound of the waves goes on "
                           "above you, and then it doesn't.", "-"),
                          ("Teleport", "%d,%d" % (sx * 32, (sy + 1) * 32 - 8), "12,-5,-1"), ("End",)] + far)
    W("Climb Up Gull_Stair_Foot", [(">Distance.From.Clicked.Tile", "48", "@far"), ("Play.Sound", "Ladder"), ("Wait", "0.4"),
                                   ("Teleport", "%d,%d" % ((MOUTH[0] - 1) * 32, MOUTH[1] * 32 - 8), SURFACE), ("End",)] + far)
    # ----- Glass in the Nets
    W("Talk to Nell_Tarrow", [
        ("Get.Value", "ATTRIBUTE", GATE, "Variable.1$"),
        (">Conditional", "$Variable.1=0", "@one"),
        (">Quest.Can.Start", GATE, "@idle"),
        say("Woman", "Look at this. Go on, take it, it doesn't bite. Glass, out of the sea, and it glows. Three weeks now my nets "
                     "come up full of it, and the fish come up dead, or don't come up at all.\\Gran says leave it be. Gran "
                     "says that about everything.", ("Where does it come from?", "@ask"), ("Good luck with it.", "@end")),
        ("@ask",),
        say("Woman", "If I knew that I'd be rich or dead. The tide brings it in round the point, on the north side, where the "
                     "rocks are. The gulls won't go near there. Gulls go near everything.", ("I'll go and look.", "@start"),
            ("Not now.", "@end")),
        ("@start",),
        ("Update.Attribute", GATE, "=1"),
        ("Display.Message", "Yellow", "Quest started: Glass in the Nets.", "Quest"),
        ("End",),
        ("@one",), (">Conditional", "$Variable.1=1", "@two"),
        say("Woman", "Round the north side of the point. Mind the rocks: they're sharper than they look, and so's the glass.",
            ("I'll look.", "@end")), ("End",),
        ("@two",), (">Conditional", "$Variable.1=2", "@three"),
        say("Woman", "A door? Under the point? A glass door, sealed?\\...You'd best talk to Gran. She tells a story about "
                     "glass men who walked into the sea. I always thought it was to keep me off the rocks.",
            ("Where is she?", "@gran")),
        ("@gran",), ("Update.Attribute", GATE, "=3"),
        ("Quest.Note", "Glass in the Nets", "Bryony keeps the cottage on Gull Point with Nell."),
        ("End",),
        ("@three",), (">Conditional", "$Variable.1<5", "@open"),
        say("Woman", "Gran's the one to ask. Mind, she'll want you to sit down first. Everybody sits down first.",
            ("All right.", "@end")), ("End",),
        ("@open",),
        say("Woman", "You went in? Through that door? And came out again?\\The glass is still coming in on the tide. I've "
                     "started selling it. Somebody may as well.", ("Goodbye, Nell.", "@end")), ("End",),
        ("@idle",),
        say("Woman", "Nets, glass, nets. Mind the rocks on the north side if you're walking: they've cut better boots than "
                     "yours.", ("Goodbye.", "@end")),
        ("@end",), ("End",)])
    W("Talk to Bryony_Tarrow", [
        ("Get.Value", "ATTRIBUTE", GATE, "Variable.1$"),
        (">Conditional", "$Variable.1=3", "@after"),
        say("Old_Woman", "So you're the one Nell sent. Sit down. No, there. Now.\\When I was a girl my mother told me about the "
                         "Glass Wardens. The first king set them to keep watch over something that fell in the sea, a "
                         "long time ago, and they built a house for it under the water, and they went down to it, and they "
                         "didn't come back up.", ("Go on.", "@more")),
        ("@more",),
        say("Old_Woman", "My Tam, rest him, pulled this up in his nets the summer we were married. A Warden's ring, my mother "
                         "said, and she said they woke theirs with Shards, the way you light a lamp. It's been cold in a "
                         "drawer for fifty years.\\You take it. And you bring Nell back her fish.",
            ("I'll do what I can.", "@give")),
        ("@give",),
        ("Give.Item", "Wardens_Signet", "1"),
        ("Update.Attribute", GATE, "=4"),
        ("Display.Message", "Yellow", "Bryony gives you a Warden's Signet.", "Quest"),
        ("End",),
        ("@after",), (">Conditional", "$Variable.1=4", "@later"),
        say("Old_Woman", "The ring wants waking, my mother said. Shards, and somebody who knows how to give them. Not me. I "
                         "only know how to give advice, and nobody takes that.", ("Thank you, Bryony.", "@end")), ("End",),
        ("@later",), (">Conditional", "$Variable.1>=5", "@idle"),
        say("Old_Woman", "It opened, did it? Then the Wardens are still down there, in a manner of speaking. Be careful how you "
                         "talk to them. They'll have been alone a long time.", ("I will.", "@end")), ("End",),
        ("@idle",),
        say("Old_Woman", "Sit down, sit down. Nell's out on the rocks again. That girl will have the sea in her pockets one of "
                         "these days.", ("Goodbye, Bryony.", "@end")),
        ("@end",), ("End",)])
    W("Touch Shardfall_Seal", [
        (">Distance.From.Clicked.Tile", "48", "@far"),
        ("Get.Value", "ATTRIBUTE", GATE, "Variable.1$"),
        (">Conditional", "$Variable.1>=5", "@shut"),
        ("Display.Message", "Cyan", "The Seal stands open. Cold air comes up out of the dark beyond it, and the smell of the sea.",
         "-"),
        ("End",),
        ("@shut",), (">Conditional", "$Variable.1=4", "@look"),
        (">Got.Item", "Wardens_Signet", "1", "@look"),
        ("Get.Value", "SKILL", "Shardcraft", "Variable.2$"),
        (">Conditional", "$Variable.2>=15", "@knack"),
        (">Pay.Shards", "$Shards.Shardfall.Seal", "waking the Warden's signet", "@end"),
        ("Take.Item", "Wardens_Signet", "1"),
        ("Update.Attribute", GATE, "=5"),
        ("Update.Skill", "Shardcraft", "+2"),
        ("Play.Sound", "Seal_Break"),
        ("Display.Message", "Yellow", "You press the signet into the hollow and let the Shards go into it. The ward drinks them. "
                                      "The black glass clears like breath off a window, and the way is open.", "-"),
        ("End",),
        ("@knack",),
        ("Display.Message", "DarkRed", "The signet stays cold in the hollow: you don't know enough Shardcraft to wake it "
                                       "(Shardcraft 15).", "Denied"),
        ("End",),
        ("@look",), (">Conditional", "$Variable.1=1", "@cold"),
        ("Update.Attribute", GATE, "=2"),
        ("Quest.Note.Done", "Glass in the Nets", "The glass comes from somewhere beyond a sealed door under Gull Point."),
        ("@cold",),
        ("Display.Message", "Cyan", "Black glass, cold as deep water, sealed fast. Runes glow round its frame. In its middle "
                                    "there's a small round hollow, about the size of a ring.", "-"),
        ("@end",), ("End",)] + far)
    W("Use Wardens_Signet With Shardfall_Seal", [("Goto.Script", "Touch Shardfall_Seal"), ("End",)])

    # ----- Charting the Deep
    W("Talk to Pell_Varrow", [
        ("Get.Value", "ATTRIBUTE", CHART, "Variable.1$"),
        (">Conditional", "$Variable.1=0", "@one"),
        (">Quest.Can.Start", CHART, "@idle"),
        say("Scholar", "Oh! A person. With a face. Sorry, I've been talking to the mushrooms.\\Pell Varrow, cartographer to "
                       "the Crown, or I was. I came down after the Wardens' old charts and found they were wrong about "
                       "everything except how dangerous it is.", ("What are you mapping?", "@ask"),
            ("Good luck down here.", "@end")),
        ("@ask",),
        say("Scholar", "All of it, eventually. For now, five places I can't get to without being eaten: the lake, the great "
                       "bones to the west, the singing stone in the galleries, the Wardens' hold and the pit where the light "
                       "comes from. Stand in each, and I'll take it from your telling.", ("I'll go.", "@start"),
            ("Not now.", "@end")),
        ("@start",), ("Update.Attribute", CHART, "=1"),
        ("Display.Message", "Yellow", "Quest started: Charting the Deep.", "Quest"), ("End",),
        ("@one",), (">Conditional", "$Variable.1=1", "@two"),
        say("Scholar", "$Attr.DeepChart_Count of five on the chart so far. The rest is still blank, and blank is where the "
                       "monsters live.", ("On my way.", "@end")), ("End",),
        ("@two",), (">Conditional", "$Variable.1=2", "@idle"),
        ("Update.Attribute", CHART, "=3"),
        say("Scholar", "Five! Look at it. A real map of a real place nobody's ever seen. The Crown will want it. The Crown will "
                       "pay for it, which is better.\\Here: your share.", ("Thank you, Pell.", "@end")),
        ("Display.Message", "Yellow", "Quest complete: Charting the Deep!", "Quest"), ("End",),
        ("@idle",),
        say("Scholar", "The lake's north, the bones are west, the pit's north again. The mushrooms are everywhere. Mind the "
                       "moths.", ("Goodbye, Pell.", "@end")),
        ("@end",), ("End",)])
    for key, pid, words in CHART_SPOTS:
        W("Chart_%s" % key, [
            (">Conditional", "$Attr.%s=1" % CHART, "@end"),
            (">Conditional", "$Attr.DeepChart.%s=0" % key, "@end"),
            ("Update.Attribute", "DeepChart.%s" % key, "=1"),
            ("Update.Attribute", "DeepChart_Count", "+1"),
            ("Display.Message", "Cyan", "You take it all in: %s, for Pell's chart." % words, "-"),
            (">Conditional", "$Attr.DeepChart_Count>=5", "@end"),
            ("Update.Attribute", CHART, "=2"),
            ("Quest.Note.Done", "Charting the Deep", "Every place is on the chart."),
            ("Display.Message", "Yellow", "That's all five: back to Pell.", "-"),
            ("@end",), ("End",)])

    # ----- The Brine Mother
    W("Talk to Morrow_Angler", [
        ("Get.Value", "ATTRIBUTE", BRINEQ, "Variable.1$"),
        (">Conditional", "$Variable.1=0", "@one"),
        (">Quest.Can.Start", BRINEQ, "@idle"),
        say("Fisherman", "There's fish in that lake nobody's ever eaten. Glowfin, I call them. They light up the pan.\\There's "
                         "also her. The Brine Mother. She took my boat, and Davey in it, and she sits on the north shore "
                         "like she's waiting for me to build another.", ("I'll deal with her.", "@start"),
            ("I'm sorry.", "@end")),
        ("@start",), ("Update.Attribute", BRINEQ, "=1"),
        ("Display.Message", "Yellow", "Quest started: The Brine Mother.", "Quest"), ("End",),
        ("@one",), (">Conditional", "$Variable.1=1", "@two"),
        say("Fisherman", "North shore. You'll know her. Everything else in that lake moves out of her way.", ("Right.", "@end")),
        ("End",),
        ("@two",), (">Conditional", "$Variable.1=2", "@idle"),
        ("Update.Attribute", BRINEQ, "=3"),
        say("Fisherman", "She's dead? She's really dead.\\...Davey would have liked to see that. Here. This came out of her "
                         "last time I put a hook in her, before she bit through the line. Take it. I don't want it near me.",
            ("Thank you, Morrow.", "@end")),
        ("Display.Message", "Yellow", "Quest complete: The Brine Mother!", "Quest"), ("End",),
        ("@idle",),
        say("Fisherman", "Glowfin bite where the water lights up, off the shore. You'll want a good rod, good bait, and good "
                         "fishing: twenty-two years of it, I'd say.", ("Thanks.", "@end")),
        ("@end",), ("End",)])
    W("Kill Brine_Mother", [(">Conditional", "$Attr.%s=1" % BRINEQ, "@end"), ("Update.Attribute", BRINEQ, "=2"),
                            ("Quest.Note.Done", "The Brine Mother", "The Brine Mother is dead."),
                            ("Display.Message", "Yellow", "The Brine Mother sinks into her lake for the last time. Morrow will "
                             "want to know.", "-"),
                            ("@end",), ("End",)])

    # ----- The Last Watch, The Fallen Shard
    W("Talk to Warden_Ysolde", [
        ("Get.Value", "ATTRIBUTE", WARD, "Variable.1$"),
        ("Get.Value", "ATTRIBUTE", FALLQ, "Variable.2$"),
        (">Conditional", "$Variable.1=0", "@w1"),
        (">Quest.Can.Start", WARD, "@idle"),
        say("Ghost_Warden", "Another one come to listen to it? No. No, you're warm. I can feel it from here.\\I am Ysolde, of the "
                            "Glass Wardens. The first king set us to keep watch over the Shard that fell, so nobody would "
                            "use it, and nothing would wake it. We kept the watch four hundred years.",
            ("What happened?", "@w0b")),
        ("@w0b",),
        say("Ghost_Warden", "It sings. Did nobody tell you? It sings all the time, a long slow song with no end, and if you "
                            "listen long enough you'll do anything it asks.\\Marshal Corvane "
                            "listened longest. He keeps the Great Hall still, and the others with him. End him, warm one. "
                            "End the watch.", ("I will.", "@w0c"), ("Not yet.", "@end")),
        ("@w0c",), ("Update.Attribute", WARD, "=1"),
        ("Display.Message", "Yellow", "Quest started: The Last Watch.", "Quest"), ("End",),
        ("@w1",), (">Conditional", "$Variable.1=1", "@w2"),
        say("Ghost_Warden", "He sits on the dais in the Great Hall, through the east passage. He was kind, once. Don't let that "
                            "slow your hand.", ("I won't.", "@end")), ("End",),
        ("@w2",), (">Conditional", "$Variable.1=2", "@f0"),
        (">Got.Item", "Marshals_Seal", "1", "@noseal"),
        ("Take.Item", "Marshals_Seal", "1"),
        ("Update.Attribute", WARD, "=3"),
        say("Ghost_Warden", "His seal. Then it's done, and he's quiet.\\The Reliquary will open to you now, past the chapel. "
                            "What the Order kept there was always meant for whoever finished the watch. I never thought it "
                            "would be somebody alive.", ("Thank you, Ysolde.", "@end")),
        ("Display.Message", "Yellow", "Quest complete: The Last Watch!", "Quest"), ("End",),
        ("@noseal",),
        say("Ghost_Warden", "He's gone; I felt it. But his seal: you left it with him? Then go back for it. I'll wait. I'm good "
                            "at waiting.", ("I'll fetch it.", "@end")), ("End",),
        ("@f0",), (">Conditional", "$Variable.2=0", "@f1"),
        (">Quest.Can.Start", FALLQ, "@idle"),
        say("Ghost_Warden", "There's one more thing, and I'm sorry for it. Corvane kept the Shard's guardian asleep, in his way. "
                            "With him gone it's stirring: the Shardborn, crystal grown in the shape of a giant.\\Go west "
                            "through the Watch Gallery, past the cells. Put it down. Then lay your hand on the Shard, and "
                            "you'll know what we knew.", ("I'll go.", "@f0b"), ("Not yet.", "@end")),
        ("@f0b",), ("Update.Attribute", FALLQ, "=1"),
        ("Display.Message", "Yellow", "Quest started: The Fallen Shard.", "Quest"), ("End",),
        ("@f1",), (">Conditional", "$Variable.2<3", "@done"),
        say("Ghost_Warden", "West, through the Watch Gallery. The light will show you the way. It always does.",
            ("I'm going.", "@end")), ("End",),
        ("@done",),
        say("Ghost_Warden", "You've heard it now. Everybody who touches it does.\\The watch is yours, warm one. I think I'll rest.",
            ("Rest well, Ysolde.", "@end")), ("End",),
        ("@idle",),
        say("Ghost_Warden", "Warm hands, warm feet. You don't belong down here. Go carefully.", ("I will.", "@end")),
        ("@end",), ("End",)])
    W("Kill Hollow_Marshal", [(">Conditional", "$Attr.%s=1" % WARD, "@end"), ("Update.Attribute", WARD, "=2"),
                              ("Give.Item", "Marshals_Seal", "1"),
                              ("Quest.Note.Done", "The Last Watch", "Marshal Corvane is dead. You have his seal."),
                              ("Display.Message", "Yellow", "The Hollow Marshal falls, and his armour falls empty. His seal "
                               "rolls to your feet.", "-"),
                              ("@end",), ("End",)])
    W("Kill Shardborn", [(">Conditional", "$Attr.%s=1" % FALLQ, "@end"), ("Update.Attribute", FALLQ, "=2"),
                         ("Quest.Note.Done", "The Fallen Shard", "The Shardborn is broken."),
                         ("Display.Message", "Yellow", "The Shardborn comes apart into a thousand chiming pieces. Behind it, "
                          "the Fallen Shard's light steadies.", "-"),
                         ("@end",), ("End",)])
    W("Touch Fallen_Shard", [
        (">Distance.From.Clicked.Entity", "72", "@far"),
        (">Conditional", "$Attr.%s=2" % FALLQ, "@not"),
        ("Update.Attribute", FALLQ, "=3"),
        ("Play.Sound", "Geode_Song"),
        ("Display.Conversation", "Player", "You lay your hand on the Fallen Shard, and it isn't cold at all.\\It's singing: "
                                           "one long note, like the sea heard from inside a shell, and under it a "
                                           "hundred others, every crystal in the deep joining in. For a moment you "
                                           "understand why the Wardens stayed.\\Then it's only glass again, warm under "
                                           "your hand.", "Step back.", "@end"),
        ("End",),
        ("@not",), (">Conditional", "$Attr.%s>=3" % FALLQ, "@push"),
        ("Display.Message", "Cyan", "It hums under your hand, slow as the sea.", "-"),
        ("End",),
        ("@push",),
        ("Display.Message", "DarkRed", "Its light pushes you back, cold as deep water.", "Denied"),
        ("@end",), ("End",)] + far)
    W("Draw From Fallen_Shard", [
        (">Distance.From.Clicked.Entity", "72", "@far"),
        (">Conditional", "$Attr.%s>=3" % FALLQ, "@not"),
        ("Get.Value", "ATTRIBUTE", "FallenShardAt", "Variable.4$"),
        ("Get.Value", "CALCULATION", "$Clock-$Variable.4", "Variable.5$"),
        ("Get.Value", "CALCULATION", "$Shards.Shardfall.Draw.Hours*3600", "Variable.6$"),
        (">Conditional", "$Variable.5>=$Variable.6", "@dim"),
        ("Show.Skill", "Shardcraft"),
        ("Display.Message", "Cyan", "You open your hand to the Fallen Shard and let it give.."),
        ("Wait", "2"),
        ("Update.Attribute", "FallenShardAt", "=$Clock"),
        ("Give.Item", "Shard", "$Shards.Shardfall.Draw"),
        ("Update.Skill", "Shardcraft", "+0.6"),
        ("Play.Sound", "Absorb"),
        ("Display.Message", "Yellow", "..and $Shards.Shardfall.Draw Shards come away into you, warm, still singing."),
        ("End",),
        ("@dim",), ("Display.Message", "DarkRed", "The Shard's light is low: it has given what it will for now.", "Fail"),
        ("End",),
        ("@not",), ("Display.Message", "DarkRed", "Its light pushes you back, cold as deep water.", "Denied"),
        ("End",)] + far)

    # ----- the Singing Geode, the Wardens' journals
    W("Listen Singing_Geode", [
        (">Distance.From.Clicked.Entity", "56", "@far"),
        ("Play.Sound", "Geode_Song"),
        (">Conditional", "$Attr.Singing_Geode=0", "@heard"),
        ("Update.Attribute", "Singing_Geode", "=1"),
        ("Update.Skill", "Shardcraft", "+1"),
        ("Display.Message", "Cyan", "You put your ear to the stone. It sings four notes, over and over, and every crystal in "
                                    "the gallery sings them back.", "-"),
        ("End",),
        ("@heard",),
        ("Display.Message", "Cyan", "Four notes, over and over. You find you're humming them too.", "-"),
        ("End",)] + far)
    pages = [
        "WARDENS' JOURNAL: the hand of Ysolde\\Year 211 of the watch. The Shard is quiet. Marshal Corvane says it sleeps. "
        "Brother Hale says it never sleeps, it only waits, and has been made to scrub the cistern for saying so.",
        "WARDENS' JOURNAL: the hand of Brother Hale\\It grows. We have measured it every year since the first: a hair "
        "a year, always. Marshal Corvane says it's the rock settling. Rock doesn't settle upwards.",
        "WARDENS' JOURNAL: the hand of Marshal Corvane\\I have heard it now. It isn't asking to be used. It's asking "
        "to be listened to, and nobody has, in four hundred years of standing guard over it with our ears stopped.\\"
        "The others will understand. I'll make them listen."]
    for i, text in enumerate(pages, 1):
        W("Read Wardens_Journal_%d" % i, [(">Distance.From.Clicked.Entity", "64", "@far"),
                                          ("Display.Conversation", "Notice", text, "Okay", "@end"), ("@end",), ("End",)] + far)

    # ----- the chests (each player's own)
    loot = {"Prism_Grotto": [("Shard", 45), ("Gold_Coin(s)", 400), ("Storm_Shard", 1), ("Sapphire", 2)],
            "Leviathans_Jaw": [("Gold_Coin(s)", 500), ("Ruby", 2), ("Major_Healing_Draught", 2), ("Ward_Shard", 1)],
            "Wardens_Footlocker": [("Gold_Coin(s)", 300), ("Major_Healing_Draught", 2), ("Shard", 30)],
            "Wardens_Ossuary": [("Gold_Coin(s)", 450), ("Shard", 40), ("Ember_Shard", 1)],
            "Wardens_Armoury": [("Gold_Coin(s)", 350), ("Mithril_Bar", 3), ("Shard", 30)],
            "Wardens_Reliquary": [("Wardens_Aegis", 1), ("Lightning_Scroll_II", 1), ("Shard", 60)]}
    for cid, items in loot.items():
        rows = [(">Distance.From.Clicked.Entity", "48", "@far"),
                (">Conditional", "$Attr.%s=0" % cid, "@empty"),
                ("Update.Attribute", cid, "=1"), ("Play.Sound", "Chest")]
        rows += [("Give.Item", it, str(n)) for it, n in items]
        rows += [("End",), ("@empty",), ("Display.Message", "Cyan", "The chest is empty.", "Empty"), ("End",)] + far
        W("Open %s" % cid, rows)

    # ----- the grotto's way in
    if grotto_map:
        W("Hidden_Way_Grotto", [(">Conditional", "$Attr.Hidden_Way_Grotto=0", "@end"),
                                ("Update.Attribute", "Hidden_Way_Grotto", "=1"),
                                ("Display.Message", "Cyan", "You lean on the crystal wall and it isn't there. Light, a lot of "
                                 "it, and a hush like held breath.", "Hidden_Way"),
                                ("Update.Skill", "Stealth", "+0.5"), ("@end",), ("End",)])

    # ----- digging Shardglass, fishing and cooking glowfin
    picks = (("Mithril_Pickaxe", 24), ("Steel_Pickaxe", 14), ("Pickaxe", 6), ("Bronze_Pickaxe", 0))
    rows = [(">Distance.From.Clicked.Tile", "40", "@far"),
            ("Get.Value", "CALCULATION", "$Tile.under.Cursor.X", "Variable.5$"),
            ("Get.Value", "CALCULATION", "$Tile.under.Cursor.Y", "Variable.6$")]
    for i, (tool, bonus) in enumerate(picks):
        rows += [("@pick%d" % i,), (">Got.Item", tool, "1", "@pick%d" % (i + 1) if i + 1 < len(picks) else "@nopick"),
                 ("Get.Value", "CALCULATION", str(bonus), "Variable.2$"), ("Goto.Line", "@dig")]
    rows += [("@dig",), ("Get.Value", "SKILL", "Mining", "Variable.1$"),
             (">Conditional", "$Variable.1>=18", "@low"),
             ("Display.Message", "Cyan", "You work your pickaxe into the glassed rock..."),
             ("Show.Skill", "Mining"), ("Play.Animation", "Rock_Chips", "4", "Mine"), ("Wait", "3"),
             (">Conditional", "($Variable.1*2+$Variable.2)>$Random.Percent", "@miss"),
             ("Display.Message", "Yellow", "...and Shard Remnants come loose from it, glowing.", "Gather_Ore"),
             ("Give.Item", "Shard_Remnant", "2"),
             ("Update.Skill", "Mining", "+0.8"),
             ("Change.Tile", "$Variable.5,$Variable.6", "Shardglass_Rock002", "0", "900"),
             ("End",),
             ("@miss",), ("Display.Message", "DarkRed", "...but only chip the glass.", "Fail"), ("End",),
             ("@low",), ("Display.Message", "DarkRed", "You need level 18 Mining to dig the Shard out of this rock.", "Denied"),
             ("End",),
             ("@nopick",), ("Display.Message", "DarkRed", "You need a pickaxe!", "Denied"), ("End",)] + \
        [("@far",), ("Display.Message", "DarkRed", "You are too far away!", "Denied"), ("End",)]
    W("Mine Shardglass_Rock", rows)
    for tool, _ in picks:
        W("Use %s With Shardglass_Rock" % tool, [("Goto.Script", "Mine Shardglass_Rock"), ("End",)])
    W("Fish Glowfin_Spot", [
        (">Distance.From.Clicked.Entity", "64", "@edge"),
        (">Got.Item", "Fishing_Rod", "1", "@rod"),
        ("Get.Value", "SKILL", "Fishing", "Variable.1$"),
        (">Conditional", "$Variable.1>=22", "@low"),
        (">Got.Item", "Bait", "1", "@bait"),
        ("Display.Message", "Cyan", "You bait the hook and cast towards the lights under the water..."),
        ("Show.Skill", "Fishing"), ("Play.Animation", "Splash", "1", "Splash"), ("Wait", "4"),
        (">Conditional", "($Variable.1*2-10)>$Random.Percent", "@slip"),
        ("Take.Item", "Bait", "1"),
        ("Display.Message", "Yellow", "...and land a glowfin, shining like a lamp!", "Gather_Fish"),
        ("Give.Item", "Raw_Glowfin", "1"),
        ("Update.Skill", "Fishing", "+0.8"),
        ("End",),
        ("@slip",), ("Display.Message", "DarkRed", "...but it slips the hook. Your bait's still on.", "Fail"), ("End",),
        ("@bait",), ("Display.Message", "DarkRed", "You need bait on the hook.", "Denied"), ("End",),
        ("@low",), ("Display.Message", "DarkRed", "You need level 22 Fishing to catch the glowfin here.", "Denied"), ("End",),
        ("@rod",), ("Display.Message", "DarkRed", "You need a fishing rod.", "Denied"), ("End",),
        ("@edge",), ("Display.Message", "DarkRed", "You need to stand at the water's edge, by the spot!", "Denied"), ("End",)])
    W("Use Fishing_Rod With Glowfin_Spot", [("Goto.Script", "Fish Glowfin_Spot"), ("End",)])
    for where, bonus in (("Fire", 30), ("Fireplace", 35), ("Range", 40)):
        W("Use Raw_Glowfin With %s" % where, [
            (">Distance.From.Clicked.Entity", "40", "@far"),
            ("Get.Value", "SKILL", "Cooking", "Variable.1$"),
            (">Conditional", "$Variable.1>=22", "@low"),
            (">Got.Item", "Raw_Glowfin", "1", "@none"),
            ("Take.Item", "Raw_Glowfin", "1"),
            ("Display.Message", "Cyan", "You lay the glowfin on the %s. Its light goes out slowly as it cooks.." % where.lower()),
            ("Play.Sound", "CookingFood"), ("Wait", "3"),
            (">Conditional", "($Variable.1*2+%d)>$Random.Percent" % bonus, "@burn"),
            ("Display.Message", "Yellow", "..and cook it perfectly!", "Cooked"),
            ("Update.Skill", "Cooking", "+0.8"),
            ("Give.Item", "Cooked_Glowfin", "1"),
            ("End",),
            ("@burn",), ("Display.Message", "DarkRed", "..but accidentally burn it!", "Fail"), ("Give.Item", "Burnt_Food", "1"),
            ("End",),
            ("@none",), ("Display.Message", "DarkRed", "You don't have any Raw Glowfin.", "Denied"), ("End",),
            ("@low",), ("Display.Message", "DarkRed", "You need level 22 Cooking to cook Raw Glowfin.", "Denied"), ("End",)]
            + far)


def chart_triggers(d):
    """Where each of Pell's five places is stood in: a few tiles round each, so it can't be missed."""
    spots = {pid: (gx, gy) for gx, gy, pid in d.ids}
    for key, pid, _ in CHART_SPOTS:
        gx, gy = spots[pid]
        n = 0
        for a in range(-3, 4):
            for b in range(-3, 4):
                if d.get(gx + a, gy + b) == FLOOR and (gx + a, gy + b) not in {(t[0], t[1]) for t in d.triggers} \
                        and abs(a) + abs(b) <= 3:
                    d.triggers.append((gx + a, gy + b, "Chart_%s" % key))
                    n += 1
        assert n, "No floor round %s" % pid


def main():
    ART.draw_all(dict(MOBS, **PEOPLE))
    mob_data()
    tile_data()
    thing_data()
    quests()
    labels()
    remake = "--maps" in sys.argv or not os.path.exists(DONE)
    names = None
    grotto = True
    if remake:
        d, _ = lay_out()
        dress(d)
        chart_triggers(d)
        grotto = d.grotto is not None
        names = write_maps(d)
        gull_point()
        open(DONE, "w").write("laid out\n")
    else:
        print("The Shardfall Deep's maps are laid out already (--maps to lay them out again)")
    if names is None:
        names = sorted({tuple(map(int, f[:-4].split(",")[:2])) for f in os.listdir(p("maps"))
                        if f.endswith(",-1.txt") and MX0 <= int(f.split(",")[0]) <= MX1 and MY0 <= int(f.split(",")[1]) <= MY1})
    config_data([map_name(mx, my) for mx, my in names])
    scripts(grotto)
    print("The Shardfall Deep: done")


if __name__ == "__main__":
    main()
