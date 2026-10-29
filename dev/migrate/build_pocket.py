"""Your homestead is a pocket of the Shardrealm's calm rim (dsengine/homes.py), held by an anchor of your own:

  * the story: shardstones reach only the realm's rim, where it's thin and still and small things hold; its core is
    a storm, and only the Shardgate pierces that (build_shardgate.py). The settler in Ashford calls the pockets the
    Stillwater and gives you a Hearth Anchor (it was the Access Crystal); Bert, in chapter 15, says what they are;
  * no homestones: a shardstone takes you home ("Your homestead" on its travel map, dsengine/shardcraft.py), and the
    Pocket Anchor in your pocket (it was its homestone) takes you back and says who may visit. A pocket is always
    safe: nothing hostile is ever in one;
  * a new pocket (data\\Homestead.txt) is raw rim, a little still glass in pale mist; you terraform it with Shards
    (Shards.ini [Terraform]) and Shardcraft: still the mist into glass, turn glass to soil, soil to grass, lay water,
    set rocks, plant saplings, and grow Shard Blooms, which give Shards every few hours (Shards.ini [Homestead]):
    no source of Shards gives more, but each costs Shards to plant and you must be there to harvest it;
  * the pictures: the rim's mist and glass (big seamless textures, sprites\\Textures Rim_Mist and Rim_Glass), the
    Pocket Anchor, the Hearth Anchor, a Shard Bloom (4 frames);
  * the data: Tiles.ini, Entities.ini, Buildables.ini (the Terraform pieces: Tile= is what they lay), Shards.ini, the
    settler's script and the quest, and every town's homestone taken off its map.

Homes made before keep their land (a meadow: a pocket already shaped); their homestone is their Pocket Anchor now
(homes.py). build_homestead.py, which made homestones, is superseded.

Safe to run again (it writes the same, and only what's changed).

  python -I "dev\\migrate\\build_pocket.py"
"""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import Ini, p                      # noqa: E402
import build_sounds as SND                     # noqa: E402
import sprite_kit as K                         # noqa: E402
import story_kit as SK                         # noqa: E402

MAKER = "build_pocket.py"
MIST, GLASS = "Rim_Mist001", "Rim_Glass001"
ARRIVAL, ANCHOR_AT, BENCH_AT = (13, 18), (12, 18), (15, 18)     # (where homes have always had them)
STILL_CENTRE, STILL_R = (13, 16.5), 3.6                        # (the glass you start with, round where you arrive)
TERRAFORM = [   # id, tile it lays, kind, name, Shardcraft level, xp, on (the tiles it can go on), Shards
    ("Terra_Glass", GLASS, "Tile", "Still the mist", 1, 0.08, MIST, 3),
    ("Terra_Soil", "Dirt001", "Tile", "Glass to soil", 1, 0.05, GLASS, 2),
    ("Terra_Grass", "Grass001", "Tile", "Soil to grass", 2, 0.05, "Dirt001", 1),
    ("Terra_Water", "Water001", "Tile", "Water", 6, 0.1, "Dirt001,Grass001", 6),
    ("Terra_Rock", "Rock002", "Decor", "A rock", 3, 0.05, "", 2),
    ("Terra_Sapling", "Tree002", "Decor", "A sapling", 4, 0.1, "Grass001", 5),
    ("Shard_Bloom", "Shard_Bloom", "Object", "A Shard Bloom", 3, 0.5, "Grass001,Dirt001", 20),
]
SHARDS = [   # (section, key, value, what it means)
    ("Homestead", "Bloom.Shards", "4", "Shard Blooms in your pocket: Bloom.Shards each, every Bloom.Hours (real) hours "
                                       "once it's harvested (or planted); Bloom.Max of them, and one more for every "
                                       "Bloom.Per.Levels Shardcraft levels, never more than Bloom.Most."),
    ("Homestead", "Bloom.Hours", "6", ""),
    ("Homestead", "Bloom.Max", "1", ""),
    ("Homestead", "Bloom.Per.Levels", "5", ""),
    ("Homestead", "Bloom.Most", "6", ""),
]


# ================================================================== pictures
def textures():
    """The rim's mist (pale lilac, a few faint stars far down) and its glass (still, pale, faintly veined)."""
    import numpy as np
    import build_terrain as T
    rng = random.Random(4100)
    h = T.fractal(rng, 128, 5, cells=4)
    stops = [(0.0, (70, 58, 104)), (0.45, (112, 98, 150)), (0.75, (160, 146, 196)), (1.0, (196, 186, 226))]
    mist = np.array([[T.ramp(v, stops) for v in row] for row in h], dtype=np.float64)
    for _ in range(40):                                     # (stars, far down in it)
        x, y = rng.randrange(128), rng.randrange(128)
        mist[y, x] = (236, 228, 255)
    T.save_texture("Rim_Mist", mist)
    g = T.fractal(rng, 128, 4, ridged=True, cells=4)
    shade = T.shade(T.fractal(rng, 128, 3, cells=4), 0.8)
    stops = [(0.0, (176, 170, 204)), (0.6, (202, 198, 226)), (1.0, (232, 230, 246))]
    glass = np.array([[T.ramp(0.55 * g[y, x] + 0.45 * shade[y, x], stops) for x in range(128)] for y in range(128)],
                     dtype=np.float64)
    T.save_texture("Rim_Glass", glass)
    return T.cell_of(mist, 0), T.cell_of(glass, 0)


def bloom(frame):
    """A Shard Bloom: a crystal flower on a pale stalk, its petals pulsing with light."""
    img = K.new()
    for y in range(18, 30):                                 # (the stalk, and two leaves)
        K.put(img, 16, y, (120, 180, 150))
    for x, y in ((13, 24), (14, 23), (18, 25), (19, 24)):
        K.put(img, x, y, (140, 210, 170))
    glow = (0.0, 0.25, 0.5, 0.25)[frame]
    for i, (dx, dy) in enumerate(((0, -7), (6, -2), (4, 5), (-4, 5), (-6, -2))):     # (five crystal petals)
        cx, cy = 16 + dx, 14 + dy
        for yy in range(-3, 4):
            for xx in range(-2, 3):
                if abs(xx) + abs(yy) <= 3:
                    c = (140, 200, 255) if yy < 0 else (90, 150, 230)
                    if xx < 0:
                        c = K.mix(c, (230, 245, 255), 0.4)
                    K.put(img, cx + xx, cy + yy, K.mix(c, (255, 255, 255), glow))
    for dx, dy in ((0, 0), (1, 0), (0, 1), (-1, 0), (0, -1)):
        K.put(img, 16 + dx, 14 + dy, K.mix((255, 240, 160), (255, 255, 255), glow))
    return K.outline_img(img, (30, 40, 70))


def art():
    mist, glass = textures()
    out = [("Tiles", MIST, mist), ("Tiles", GLASS, glass), ("Entities", "Shard_Bloom", bloom(0))]
    out += [("Entities", "Shard_Bloom%d" % (f + 1), bloom(f)) for f in range(4)]
    n = sum(1 for kind, name, img in out if K.save(kind, name, img))
    for src, dst in (("Homestone", "Pocket_Anchor"), ("Access_Crystal", "Hearth_Anchor")):
        if not os.path.exists(p("sprites", "Entities", dst + ".png")) and os.path.exists(p("sprites", "Entities",
                                                                                        src + ".png")):
            SK.copy_sprite("Entities", src, dst)
            n += 1
    print("Pictures: %d written" % n)


SOUNDS = {
    # (Bloom_Harvest: build_soundscape.py)
    # the mist drawing still: a long breath out, glass settling
    "Terraform": lambda: SND.mix((SND.shaped(SND.noise(72, SND.n(0.7), 0.15), 0.2, 3.0), 0.5),
                                 (SND.shaped(SND.tone(330, SND.n(0.6), glide=-0.3), 0.05, 4.0), 0.3)),
}


def sounds():
    for name, fn in SOUNDS.items():
        blob = SND.wav_bytes(fn())
        path = p("sounds", name + ".wav")
        if not (os.path.exists(path) and open(path, "rb").read() == blob):
            with open(path, "wb") as fh:
                fh.write(blob)
            print("wrote sounds\\%s.wav" % name)


# ================================================================== data
def data():
    SK.copy_tile(MIST, "Realm_Void001", Texture="Rim_Mist",
                 Examine_Info="Pale mist, the realm's calm rim: stars far down in it, and nothing to stand on.")
    SK.copy_tile(GLASS, "Realm_Ground001", Texture="Rim_Glass",
                 Examine_Info="Still glass, pale and cool underfoot: the rim of the Shardrealm, held.")
    SK.minimap_colour(MIST, (112, 98, 150))
    SK.minimap_colour(GLASS, (202, 198, 226))
    ents = Ini(p("data", "Entities.ini"))
    for name, keys in (
            ("Hearth_Anchor", [("Type", "MapItem"), ("Droppable", "0"), ("Value", "0"),
                               ("Examine.Info", "Your Hearth Anchor: a warm shard that holds your pocket of the "
                                                "Stillwater. Any shardstone can take you home while you carry it.")]),
            ("Pocket_Anchor", [("Type", "StaticObject"), ("Use.Words", "Touch,Examine"), ("Light", "40"),
                               ("Examine.Info", "The anchor that holds this pocket of the Shardrealm's rim: an old "
                                                "stone, its hearth rune glowing warm.")]),
            ("Shard_Bloom", [("Type", "StaticObject"), ("Use.Words", "Harvest,Examine"), ("Solid", "1"),
                             ("Light", "45"), ("Anim.Frames", "4"), ("Anim.Speed", "260"),
                             ("Examine.Info", "A Shard Bloom: crystal petals that drink the rim's stillness and "
                                              "fill, slowly, with Shards.")])):
        for k, v in keys:
            ents.set(name, k, v)
    ents.sections = [s for s in ents.sections if s[0] not in ("Access_Crystal", "Homestone")]
    ents.save(p("data", "Entities.ini"))
    sh = Ini(p("data", "Shards.ini"))
    for section, key, value, note in SHARDS + [("Terraform", tid, str(cost), "") for tid, *_, cost in TERRAFORM]:
        if sh.section(section) is None:
            sh.sections.append([section, [(None, "; Terraforming your pocket (Buildables.ini's Terraform pieces): the "
                                                 "Shards each takes.")] if section == "Terraform" else []])
        if sh.get(section, key) is None:
            if note:
                sh.section(section)[1].append((None, "; " + note))
            sh.set(section, key, value, overwrite=False)
    sh.save(p("data", "Shards.ini"))
    bu = Ini(p("data", "Buildables.ini"))
    for tid, tile, kind, name, level, xp, on, cost in TERRAFORM:
        keys = [("Kind", kind), ("Category", "Terraform"), ("Name", name), ("Tile", tile), ("Skill", "Shardcraft"),
                ("Level", str(level)), ("XP", str(xp))] + ([("On", on)] if on else [])
        for k, v in keys:
            bu.set(tid, k, v)
    bu.save(p("data", "Buildables.ini"))
    SK.section(p("data", "Config.ini"), "Homestead", [("Return.Map", "11,4,0")])


def template():
    """data\\Homestead.txt: a new pocket, raw rim: still glass round where you arrive, mist all round it."""
    rows = []
    for y in range(1, 22):
        row = []
        for x in range(1, 26):
            d = ((x - STILL_CENTRE[0]) ** 2 + ((y - STILL_CENTRE[1]) * 1.15) ** 2) ** 0.5
            row.append(GLASS if d <= STILL_R and 2 <= x <= 24 and 2 <= y <= 20 else MIST)
        rows.append(":".join(row))
    tw = 32
    rows += ["StaticObject\tPocket_Anchor\t%d\t%d" % ((ANCHOR_AT[0] - 1) * tw, (ANCHOR_AT[1] - 1) * tw),
             "StaticObject\tCarpenters_Bench\t%d\t%d" % ((BENCH_AT[0] - 1) * tw, (BENCH_AT[1] - 1) * tw),
             "Id\tHome_Arrival\t%d\t%d" % ARRIVAL]
    SK.write_text(p("data", "Homestead.txt"), rows)


def no_homestones():
    """Every town's homestone off its map: the shardstone beside it takes you home now."""
    n = 0
    for f in sorted(os.listdir(p("maps"))):
        if not f.endswith(".txt"):
            continue
        path = p("maps", f)
        raw = open(path, "rb").read()
        lines = raw.decode("cp1252").split("\r\n")
        keep = [ln for ln in lines if not ln.startswith("StaticObject\tHomestone\t")]
        if len(keep) != len(lines):
            open(path, "wb").write("\r\n".join(keep).encode("cp1252"))
            n += len(lines) - len(keep)
    print("Homestones taken off the maps: %d" % n)


# ================================================================== the settler, the quest
def settler():
    say = SK.say
    SK.write_script("Talk to Homestead_Settler", [
        ("Get.Value", "ATTRIBUTE", "HomeQuest", "Variable.1$"),
        (">Conditional", "$Variable.1=0", "@begun"),
        (">Quest.Can.Start", "HomeQuest", "@early"),
        say("Settler", "Looking for a place of your own? Every settler out here dreams of one.\\There's a place past the "
                       "shardstones we call the Stillwater: quiet, pale, nobody else's. With a Hearth Anchor a "
                       "shardstone will take you to a pocket of it, and it's yours. I'll give you mine if you show me "
                       "you can build: bring me 10 planks and 4 stone blocks. Use my carpenter's bench to make them.",
            ("I'll do it!", "@yes"), ("What's the Stillwater?", "@what"), ("Not now.", "@end")),
        ("@yes",),
        ("Update.Attribute", "HomeQuest", "=1"),
        ("Quest.Note", "HomeQuest", "Saw logs into planks at the settler's carpenter's bench (Homesteading)."),
        ("Quest.Note", "HomeQuest", "Mine stone from rocks with a pickaxe and cut it into blocks at the bench."),
        ("Display.Message", "Yellow", "Quest started: A Place of Your Own.", "-"),
        ("End",),
        ("@what",),
        say("Settler", "Nobody rightly knows. Mist and still glass, a little sky. Touch the anchor and it's held, and "
                       "it's yours: you can shape it with Shards, soil and grass and water, and build on it. Some say "
                       "it's the edge of somewhere stranger. I just call it home.", ("I see.", "@end")),
        ("End",),
        ("@begun",), (">Conditional", "$Variable.1=1", "@after"),
        (">Got.Item", "Plank", "10", "@need"),
        (">Got.Item", "Stone_Block", "4", "@need"),
        ("Take.Item", "Plank", "10"),
        ("Take.Item", "Stone_Block", "4"),
        say("Settler", "Good, square work! You'll do. Here: my Hearth Anchor. Touch any shardstone you've woken while "
                       "you carry it and it'll take you to your own pocket of the Stillwater. It's raw at first: "
                       "glass and mist. Shape it with Shards, build what you like; nobody comes in unless you let "
                       "them.\\Once you know a little magic I can sell you scrolls that take you home from anywhere.",
            ("Thank you!", "@give")),
        ("@give",),
        ("Give.Item", "Hearth_Anchor", "1"),
        ("Give.Item", "Nails", "40"),
        ("Update.Skill", "Homesteading", "+3"),
        ("Update.Attribute", "HomeQuest", "=2"),
        ("Quest.Note.Done", "HomeQuest", "*"),
        ("Display.Message", "Yellow", "Quest complete! You receive the Hearth Anchor, 40 nails and Homesteading "
                                      "experience.", "Quest"),
        ("End",),
        ("@need",),
        say("Settler", "I need 10 planks and 4 stone blocks. Logs make planks at my bench; for blocks, mine stone from "
                       "rocks with a pickaxe and cut it at the bench too.", ("I'll get them.", "@end"),
            ("Let me use your bench.", "@bench")),
        ("End",),
        ("@after",),
        say("Settler", "How's the homestead coming along?", ("Sell me something.", "@shop"),
            ("Let me use your bench.", "@bench"), ("I've lost my Hearth Anchor.", "@lost"), ("Goodbye.", "@end")),
        ("End",),
        ("@shop",), ("Display.Item.Rack", "SPECIFIC", "Settler", "SHOP-Homestead", "@end"), ("End",),
        ("@bench",), ("Display.Item.Rack", "GENERAL", "Carpenters_Bench", "CRAFT-Construction", "@end"), ("End",),
        ("@lost",), (">Got.Item", "Hearth_Anchor", "1", "@again"),
        say("Settler", "You've still got it, look: in your pack.", ("So I have.", "@end")),
        ("End",),
        ("@again",),
        ("Give.Item", "Hearth_Anchor", "1"),
        say("Settler", "Careless! Here's another. Your pocket's held to you, not to the shard.", ("Thanks.", "@end")),
        ("End",),
        ("@early",),
        say("Settler", "A homestead? Get your feet under you first: see the mainland, then come back.",
            ("I will.", "@end")),
        ("@end",), ("End",)], MAKER)
    SK.section(p("data", "Quests.ini"), "A Place of Your Own",
               [("Stage0", "Speak to the settler by the shardstone in Ashford.")])


def main():
    art()
    sounds()
    data()
    template()
    no_homestones()
    settler()
    print("The pocket: done")


if __name__ == "__main__":
    main()
