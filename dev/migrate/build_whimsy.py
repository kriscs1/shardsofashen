"""Whimsy: secrets, traps and a sense of humour, all over the world.

  * A secret in every settlement: something by its square to Search (a hollow stump, a loose cobble, a barrel, an
    old statue, a well), once each, each with its own find and its own line; finding five, ten and all of them is
    noticed (the attribute SecretsFound).
  * Traps in the old dungeons (Trigger Trap_<Kind>: dsengine/deep.py world_trap - darts, gas, a weakness rune, a
    shallow pit, an alarm, a bucket of water, a custard pie), resting ten minutes after they spring.
  * Funnier words: what the commonest creatures and things say when examined; what ordinary townsfolk say.
  * Three odd things to find (a rubber duck, a lucky sock, a suspicious key) and three silly quests:
    The Scarecrow's Hat (Oakhollow), Duchess Has Opinions (a talking cow, outside Ashford), and The Mayor's
    Missing Trousers (Constable Dobbs, Ashford: three clues and a culprit).
  * (In an animal's body, the animals talk to you: tricks.py ANIMAL_TALK.)

Safe to run again (what's placed is placed once; texts are set again).

  python -I "dev\\migrate\\build_whimsy.py"
"""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import Ini, p                      # noqa: E402
import sprite_kit as K                         # noqa: E402
import story_kit as SK                         # noqa: E402
from story_kit import Map, obj_line            # noqa: E402

MAKER = "build_whimsy.py"
TILES = Ini(p("data", "Tiles.ini"))
ROADISH = ("Path", "Road", "Paving", "Cobble", "Gravel", "Dirt", "Board", "Plank", "Bridge", "Sand")

# ================================================================== where things go
_ids = None


def place_ids():
    global _ids
    if _ids is None:
        _ids = {}
        for f in os.listdir(p("maps")):
            if f.endswith(".txt"):
                for ln in open(p("maps", f), "rb").read().decode("cp1252").split("\r\n"):
                    bits = ln.split("\t")
                    if bits[0] == "Id" and len(bits) >= 4:
                        _ids[bits[1]] = (f[:-4], int(bits[2]), int(bits[3]))
    return _ids


def walkable(tile):
    w = TILES.get(tile, "Walkable.Data") or ""
    return w and w.count("1") >= 40


def free_spot(anchor, rmin, rmax, seed, avoid_road=True):
    """A clear tile rmin-rmax tiles from place anchor, on its map: open ground, nothing on it, nothing round it."""
    name, ax, ay = place_ids()[anchor]
    m = Map(name)
    taken = set()
    for ln in m.ents:
        b = ln.split("\t")
        if b[0] in ("NPC", "StaticObject", "MapItem") and len(b) >= 4:
            taken.add((int(float(b[2])) // 32 + 1, int(float(b[3])) // 32 + 1))
            taken.add((int(float(b[2])) // 32 + 1, int(float(b[3])) // 32 + 2))
        elif b[0] in ("Id", "Trigger", "Lock") and len(b) >= 4:
            try:
                taken.add((int(b[2]), int(b[3])) if b[0] != "Lock" else (int(b[1]), int(b[2])))
            except ValueError:
                pass
    good = []
    for y in range(3, 20):
        for x in range(3, 24):
            d = abs(x - ax) + abs(y - ay)
            if not (rmin <= d <= rmax) or (x, y) in taken:
                continue
            ok = True
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    t, over = m.parts(x + dx, y + dy)
                    if over or not walkable(t) or (avoid_road and any(r in t for r in ROADISH)):
                        ok = False
            if ok:
                good.append((d, x, y))
    if not good:
        return name, None
    good.sort()
    return name, good[random.Random(seed).randrange(min(6, len(good)))][1:]


def put(map_name, line):
    m = Map(map_name)
    if line not in m.ents:
        m.ents.append(line)
        m.save()


def placed(pid):
    return any(("Id=%s" % pid) in ln for f in os.listdir(p("maps")) if f.endswith(".txt")
               for ln in open(p("maps", f), "rb").read().decode("cp1252").split("\r\n")[21:])


# ================================================================== pictures
def rubber_duck():
    img = K.new()
    for y in range(12, 26):
        for x in range(7, 25):
            if ((x - 16) / 9.0) ** 2 + ((y - 20) / 6.0) ** 2 <= 1:
                K.put(img, x, y, (250, 220, 60))
    for y in range(6, 15):
        for x in range(15, 25):
            if ((x - 20) / 5.0) ** 2 + ((y - 10) / 4.5) ** 2 <= 1:
                K.put(img, x, y, (250, 220, 60))
    for x in range(24, 28):
        K.put(img, x, 11, (240, 130, 40))
        K.put(img, x, 12, (220, 110, 30))
    K.put(img, 21, 9, (30, 30, 30))
    return K.outline_img(img, (90, 70, 20))


def sock():
    img = K.new()
    for y in range(5, 22):
        for x in range(12, 19):
            K.put(img, x, y, (200, 60, 60) if (y // 3) % 2 else (240, 240, 230))
    for y in range(20, 27):
        for x in range(12, 25):
            if y < 23 or x < 24:
                K.put(img, x, y, (200, 60, 60) if (y // 3) % 2 else (240, 240, 230))
    K.put(img, 22, 24, (60, 40, 30))                              # (a hole)
    return K.outline_img(img, (60, 30, 30))


def key():
    img = K.new()
    for y in range(8, 16):
        for x in range(6, 14):
            if 9 <= ((x - 10) ** 2 + (y - 12) ** 2) <= 16:
                K.put(img, x, y, (190, 160, 70))
    for x in range(13, 27):
        K.put(img, x, 12, (190, 160, 70))
        K.put(img, x, 13, (150, 120, 50))
    for x, d in ((20, 3), (24, 2)):
        for y in range(13, 13 + d):
            K.put(img, x, y, (190, 160, 70))
    K.put(img, 10, 12, (120, 60, 160))                            # (a tiny violet eye in the bow. It winks.)
    return K.outline_img(img, (60, 50, 20))


def cobble():
    img = K.new()
    for y in range(18, 29):
        for x in range(8, 25):
            if ((x - 16) / 8.5) ** 2 + ((y - 23) / 5.0) ** 2 <= 1:
                K.put(img, x, y, (130, 124, 116) if y > 21 else (160, 154, 146))
    K.put(img, 9, 23, (40, 36, 32))
    K.put(img, 23, 22, (40, 36, 32))
    return K.outline_img(img, (50, 46, 40))


SECRET_KINDS = {"Hollow_Stump": ("Tiles", "Tree_Stump001", "An old stump. It sounds hollow when you knock on it."),
                "Old_Statue": ("Tiles", "Statue001", "A worn statue of somebody important. Nobody remembers who. "
                                                     "One of its eyes looks slightly... loose."),
                "Odd_Barrel": ("Tiles", "Suspicious_Barrel001", "A barrel. It's a perfectly ordinary barrel. Why are "
                                                                "you looking at it like that."),
                "Wishing_Well": ("Tiles", "Well001", "An old well. Something glints, a long way down."),
                "Loose_Cobble": (None, None, "A cobble that doesn't quite sit right with the others.")}


def art():
    out = [("Entities", "Rubber_Duck", rubber_duck()), ("Entities", "Lucky_Sock", sock()),
           ("Entities", "Suspicious_Key", key()), ("Entities", "Loose_Cobble", cobble())]
    n = sum(1 for kind, name, img in out if K.save(kind, name, img))
    for name, (kind, src, _) in SECRET_KINDS.items():
        if src and K.save("Entities", name, K.load(kind, src)):
            n += 1
    if K.save("Entities", "Talking_Scarecrow", K.load("Tiles", "Scarecrow001")):
        n += 1
    SK.copy_sprite("Entities", "Cow", "Duchess")
    SK.copy_walk("Cow", "Duchess")
    print("Pictures: %d written" % n)


# ================================================================== secrets
SECRETS = [   # (town, kind, what's found: [(item, n)], the line)
    ("Southport", "Odd_Barrel", [("Shard", 8)], "Inside the barrel, under a layer of herring: a little pouch of Shards. "
                                                "The herring watches you take it."),
    ("Ashford", "Hollow_Stump", [("Rubber_Duck", 1)], "Something squeaks inside the stump. A rubber duck! It looks at "
                                                       "you as if you were the strange one."),
    ("Oakhollow", "Hollow_Stump", [("Gold_Coin(s)", 40)], "Somebody's savings, hidden in the stump. A note: 'NOT FOR "
                                                          "SQUIRRELS.' You're not a squirrel. Probably fine."),
    ("Fenwick", "Wishing_Well", [("Shard", 10)], "You fish about with a bucket and bring up a handful of wishes: coins "
                                                 "gone green, and Shards. Somebody wished very hard."),
    ("Moorcross", "Loose_Cobble", [("Lucky_Sock", 1)], "Under the loose cobble: one sock. It's warm. It feels lucky. "
                                                       "It's definitely lucky."),
    ("Highwatch", "Old_Statue", [("Shard", 12)], "You press the statue's loose eye. Click: a little drawer slides out "
                                                 "of its plinth, full of Shards."),
    ("Frosthold", "Odd_Barrel", [("Super_Potion", 1)], "The barrel's full of snow, and buried in it, a potion someone "
                                                       "was keeping cold."),
    ("Dunerest", "Loose_Cobble", [("Shard", 9), ("Gold_Coin(s)", 20)], "Under the hot stone, a scorpion. And under the "
                                                                       "scorpion, a purse. The scorpion lets you have "
                                                                       "it. Today."),
    ("Emberwatch", "Old_Statue", [("Suspicious_Key", 1)], "A key, wedged behind the statue's ear. It winks at you. Keys "
                                                          "shouldn't wink."),
    ("Thornwick", "Hollow_Stump", [("Healing_Draught", 2)], "Two draughts, tucked in the stump with a note: 'In case "
                                                            "of hedgehog.'"),
    ("Ravensgate", "Wishing_Well", [("Shard", 14)], "Deep in the well, a raven's hoard: shiny things, and Shards. A "
                                                    "raven watches from the roof, taking notes."),
    ("Keep", "Odd_Barrel", [("Gold_Coin(s)", 50)], "The barrel's labelled TURNIPS. It is not full of turnips. It is "
                                                   "full of the Steward's 'turnip money'."),
    ("Court", "Old_Statue", [("Shard", 15)], "A statue of a wizard, its hat a lid. Under it: Shards, and a note in "
                                             "Bert's hand: 'IF FOUND, NO YOU DIDN'T.'"),
    ("Wildwood", "Hollow_Stump", [("Shard", 8), ("Herb", 3)], "An owl lives in this stump. An owl with Shards. It "
                                                              "looks at you, sighs, and hands them over."),
    ("Saltmarsh", "Wishing_Well", [("Invisibility_Potion", 1)], "You pull up a bottle you can barely see. Somebody "
                                                                "threw away an Invisibility Potion. Or did they?"),
    ("Galaith", "Old_Statue", [("Shard", 25)], "Behind the statue of a long-dead king, the words 'I hid it here so my "
                                               "son wouldn't find it'. He didn't."),
    ("Wardhaven", "Loose_Cobble", [("Shard", 10)], "Under the cobble, a guard's secret stash. And a list of everyone "
                                                   "who owes him a drink. You're on it, somehow."),
]


def secrets():
    count = 0
    for i, (town, kind, finds, line) in enumerate(SECRETS):
        pid = "Secret_%s" % town
        anchor = "%s_Square" % town
        if anchor not in place_ids():
            print("  !! no %s" % anchor)
            continue
        if not placed(pid):
            for rmin, rmax, off_road in ((4, 9, True), (4, 13, True), (3, 10, False)):
                mname, at = free_spot(anchor, rmin, rmax, i, off_road)     # (a paved city: on the paving)
                if at:
                    break
            if at is None:
                print("  !! no room by %s" % anchor)
                continue
            put(mname, obj_line("StaticObject", kind, at[0], at[1], "Id=%s" % pid))
            count += 1
        rows = [(">Distance.From.Clicked.Entity", "48", "@far"),
                (">Conditional", "$Attr.%s=0" % pid, "@empty"),
                ("Update.Attribute", pid, "=1"),
                ("Update.Attribute", "SecretsFound", "+1"),
                ("Play.Sound", "Pickup"),
                ("Display.Message", "Yellow", line, "-")]
        rows += [("Give.Item", item, str(n)) for item, n in finds]
        rows += [(">Conditional", "$Attr.SecretsFound=5", "@ten"),
                 ("Display.Message", "Yellow", "Five secrets found. You're developing a nose for it.", "Quest"),
                 ("Give.Item", "Shard", "10"),
                 ("@ten",), (">Conditional", "$Attr.SecretsFound=10", "@all"),
                 ("Display.Message", "Yellow", "Ten secrets! People have started hiding things from you on purpose.",
                  "Quest"),
                 ("Give.Item", "Shard", "20"),
                 ("@all",), (">Conditional", "$Attr.SecretsFound=%d" % len(SECRETS), "@end"),
                 ("Display.Message", "Yellow", "Every secret in Ashen, found. Somewhere, a squirrel weeps.", "Quest"),
                 ("Give.Item", "Shard", "50"),
                 ("End",),
                 ("@empty",), ("Display.Message", "Cyan", "You've found what was here already.", "-"),
                 ("@end",), ("End",),
                 ("@far",), ("Display.Message", "DarkRed", "You are too far away!", "Denied"), ("End",)]
        SK.write_script("Search %s" % pid, rows, MAKER)
    print("Secrets: %d placed" % count)


# ================================================================== traps
DUNGEONS = ["15,18,-1", "16,4,-1", "17,4,-1", "24,12,-1", "25,12,-1", "25,12,-2", "25,12,-3", "3,18,-1"]
TRAP_KINDS = ["Darts", "Gas", "Weakness", "Pit", "Alarm", "Bucket", "Pie", "Darts"]


def traps():
    n = 0
    for i, name in enumerate(DUNGEONS):
        if not os.path.exists(p("maps", name + ".txt")):
            continue
        m = Map(name)
        if any(ln.startswith("Trigger\tTrap_") for ln in m.ents):
            continue
        near = set()
        for ln in m.ents:
            b = ln.split("\t")
            if len(b) >= 4 and b[0] in ("Id", "Trigger"):
                near |= {(int(b[2]) + dx, int(b[3]) + dy) for dx in range(-3, 4) for dy in range(-3, 4)}
            elif len(b) >= 4 and b[0] in ("NPC", "StaticObject", "MapItem"):
                near.add((int(float(b[2])) // 32 + 1, int(float(b[3])) // 32 + 2))
        cells = []
        for y in range(2, 21):
            for x in range(2, 25):
                t, over = m.parts(x, y)
                dec = over.get("Decor", "")
                if (x, y) in near or "Ladder" in dec or "Stairs" in t or "Stairs" in dec:
                    continue
                if not over and walkable(t) and all(walkable(m.parts(x + dx, y + dy)[0])
                                                    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                    cells.append((x, y))
        rng = random.Random(name)
        for k in range(min(3, len(cells))):
            c = rng.choice(cells)
            cells = [q for q in cells if abs(q[0] - c[0]) + abs(q[1] - c[1]) > 4]
            m.ents.append("Trigger\tTrap_%s\t%d\t%d" % (TRAP_KINDS[(i + k * 3) % len(TRAP_KINDS)], c[0], c[1]))
            n += 1
            if not cells:
                break
        m.save()
    print("Traps: %d set" % n)


# ================================================================== words
EXAMINES = {
    "Rabbit": "A rabbit. It has the look of somebody who has heard about wolves.",
    "Duck": "A duck. It's looking at your hands for bread with the patience of a saint and the eyes of a debt collector.",
    "Frog": "A frog. It might be a prince. It might just be a frog. Kissing it is a gamble you're not ready to take.",
    "Butterfly": "A butterfly, very busy doing nothing in particular.",
    "Blue_Butterfly": "A blue butterfly. It knows it's the pretty one.",
    "Wolf": "A grey wolf. It looks hungry. It looks at you. It looks hungrier.",
    "Scorpion": "A scorpion. Every part of it is pointing at you.",
    "Skeleton": "A skeleton, rattling with purpose. It has no muscles and still hits harder than you'd think.",
    "Cart": "A cart. One wheel squeaks. It has always squeaked. It will always squeak.",
    "Moored_Boat": "A little boat, tied up and bobbing. It has a name painted on the side: 'BOAT'.",
    "Dice_Table": "A table for dice. Three of the dice are loaded. Nobody will tell you which three.",
    "Rubber_Duck": "A rubber duck. It squeaks. It judges.",
    "Lucky_Sock": "One sock, red and white, with a hole in the toe. It's lucky. It told you so.",
    "Suspicious_Key": "A key. It opens nothing you've found. Yet. Its bow has a tiny violet eye, which winks.",
}
for kind, (_, _, words) in SECRET_KINDS.items():
    EXAMINES[kind] = words

MAN = ["Northgate's a quiet place, mostly. The ferry brings folk over from the Isle, and the fish come in at dawn.",
       "Heading inland? Ashford's east of here. Mind the woods to the south: wolves, and worse past the old mine.",
       "My uncle went down the Shifting Deep once. Came back up through a different hole. Different county, too.",
       "Don't trust geese. That's all I'll say. Don't trust them.",
       "I once saw a cow look at the moon for a whole night. Changed me, that did.",
       "If you see a hat floating about the Wizards' Court, say hello. That's Pip. He's shy.",
       "They say the old king hid treasure all over Ashen. My grandad said that. My grandad also said he was a "
       "duck, so."]
WOMAN = ["Have you seen my husband? About so tall, about so wide, owes everybody money?",
         "The bakery's lovely this time of year. The bakery's lovely every time of year. It's a bakery.",
         "Lady Pettigrew's lost her hat again. To the geese. Again.",
         "A Shard Remnant got into my kitchen once. I hit it with a ladle. It's fine. The ladle isn't.",
         "My son wants to be an adventurer. I told him, get a proper job. Like goose herding.",
         "Somebody keeps pressing the big red button in the wizard's tower. I can tell. My washing turns into chickens."]


def gossip(npc, lines):
    rows = []
    for i, line in enumerate(lines[:-1]):
        rows += [(">Random", str(100 // (len(lines) - i)), "@n%d" % i),
                 SK.say(npc, line, ("Ha. Thanks.", "@end")), ("End",), ("@n%d" % i,)]
    rows += [SK.say(npc, lines[-1], ("Ha. Thanks.", "@end")), ("@end",), ("End",)]
    SK.write_script("Talk to %s" % npc, rows, MAKER)


def words():
    ents = Ini(p("data", "Entities.ini"))
    for name, text in EXAMINES.items():
        if ents.section(name) is not None or name in SECRET_KINDS or name in ("Rubber_Duck", "Lucky_Sock",
                                                                               "Suspicious_Key"):
            ents.set(name, "Examine.Info", text)
    for name in ("Rubber_Duck", "Lucky_Sock", "Suspicious_Key"):
        for k, v in (("Type", "MapItem"), ("Value", "1"), ("Stackable", "10")):
            ents.set(name, k, v)
    for name in SECRET_KINDS:
        for k, v in (("Type", "StaticObject"), ("Use.Words", "Search,Examine"),
                     ("Solid", "0" if name == "Loose_Cobble" else "1")):
            ents.set(name, k, v)
    for k, v in (("Type", "StaticObject"), ("Use.Words", "Talk to,Examine"), ("Solid", "1"),
                 ("Examine.Info", "A scarecrow in a field, arms out, gazing at the horizon as if it's just had a "
                                  "very big thought.")):
        ents.set("Talking_Scarecrow", k, v)
    for k, v in (("Type", "NPC"), ("Attitude", "Good"), ("Use.Words", "Talk to,Examine"), ("Respawn", "60"),
                 ("Walk.Speed", "0.4"), ("Pause", "6-15"),
                 ("Examine.Info", "A cow with a very particular expression. It's the look of a cow with opinions.")):
        ents.set("Duchess", k, v)
    for k, v in (("Type", "StaticObject"), ("Use.Words", "Search,Examine"), ("Solid", "0")):
        for clue in ("Muddy_Footprints", "Torn_Washing", "Goose_Feather_Clue"):
            ents.set(clue, k, v)
    ents.set("Muddy_Footprints", "Examine.Info", "Footprints in the mud: wide, webbed, and very determined.")
    ents.set("Torn_Washing", "Examine.Info", "A washing line, snapped. Something pulled very hard, and honked.")
    ents.set("Goose_Feather_Clue", "Examine.Info", "A white feather, caught on a nail. Quite a big one.")
    ents.save(p("data", "Entities.ini"))
    gossip("Man", MAN)
    gossip("Woman", WOMAN)


# ================================================================== quests
def scarecrow():
    if not placed("Philosopher_Scarecrow"):
        mname, at = free_spot("Oakhollow_Square", 7, 12, 3)
        if at:
            put(mname, obj_line("StaticObject", "Talking_Scarecrow", at[0], at[1], "Id=Philosopher_Scarecrow"))
    SK.quest("The Scarecrow's Hat", "Talking_Scarecrow", "ScarecrowQuest", {
        0: "A scarecrow outside Oakhollow is deep in thought. Out loud.",
        1: "Find the philosophical scarecrow outside Oakhollow a hat. Any hat. He's not fussy. He says he's not fussy."},
        2, markers={0: "Oakhollow_Square", 1: "Oakhollow_Square"}, kind="Side", requires="Passage to the Mainland")
    SK.section(p("data", "Quests.ini"), "The Scarecrow's Hat", [("Reward.Shards", "8"), ("Reward.XP", "Homesteading 2")])
    hats = ["Chefs_Hat", "Fur_Cap", "Leather_Cap", "Bronze_Helm", "Iron_Helm"]
    rows = [("Get.Value", "ATTRIBUTE", "ScarecrowQuest", "Variable.1$"),
            (">Conditional", "$Variable.1=0", "@s1"),
            (">Quest.Can.Start", "ScarecrowQuest", "@chat"),
            SK.say("Talking_Scarecrow", "Ah, a visitor. Tell me: if a crow lands on a scarecrow and nobody sees it, was the "
                                "scarecrow ever really scary? ...Also my head's cold. They never give us hats. "
                                "Twenty years in this field and not one hat.", ("I'll find you a hat.", "@start"),
                   ("Did you just talk?", "@talk")),
            ("@talk",), SK.say("Talking_Scarecrow", "Everything talks, if you stand still long enough. I've had a lot of time "
                                            "to stand still.", ("I'll find you a hat.", "@start")),
            ("@start",), ("Update.Attribute", "ScarecrowQuest", "=1"),
            ("Display.Message", "Yellow", "Quest started: The Scarecrow's Hat.", "Quest"),
            ("End",),
            ("@s1",), (">Conditional", "$Variable.1=1", "@chat")]
    for i, h in enumerate(hats):
        rows += [(">Got.Item", h, "1", "@h%d" % (i + 1) if i + 1 < len(hats) else "@nohat"),
                 ("Take.Item", h, "1"), ("Goto.Line", "@chef" if h == "Chefs_Hat" else "@done"),
                 ("@h%d" % (i + 1),)]
    rows += [("@nohat",), SK.say("Talking_Scarecrow", "No hat? That's all right. I'll just stand here. Thinking. Coldly.",
                                 ("I'll keep looking.", "@end")),
             ("End",),
             ("@chef",), SK.say("Talking_Scarecrow", "A chef's hat! I shall finally cook! ...I have no hands. Or a kitchen. Or "
                                             "a mouth. But the THOUGHT of it.", ("Enjoy it.", "@done")),
             ("@done",), ("Update.Attribute", "ScarecrowQuest", "=2"),
             SK.say("Talking_Scarecrow", "Warm at last. I feel... profound. Here's a thought to take with you: the crows were "
                                 "never afraid of me. They just liked the company.", ("That's... nice.", "@fin")),
             ("@fin",), ("Display.Message", "Yellow", "Quest complete: The Scarecrow's Hat!", "Quest"),
             ("End",),
             ("@chat",), SK.say("Talking_Scarecrow", "I've been thinking about clouds. Mostly about how they never come down "
                                             "to say hello.", ("Goodbye.", "@end")),
             ("@end",), ("End",)]
    SK.write_script("Talk to Philosopher_Scarecrow", rows, MAKER)


def duchess():
    if not placed("Duchess_The_Cow"):
        mname, at = free_spot("Ashford_Square", 9, 14, 7)
        if at:
            put(mname, obj_line("NPC", "Duchess", at[0], at[1], "Stand=1 Id=Duchess_The_Cow"))
    SK.quest("Duchess Has Opinions", "Cow", "CowQuest", {
        0: "A cow outside Ashford has something to say. Literally.",
        1: "Bring Duchess the cow three bunches of herbs: 'the good grass'. She has standards."}, 2,
        markers={0: "Duchess_The_Cow", 1: "Duchess_The_Cow"}, kind="Side", requires="Passage to the Mainland")
    SK.section(p("data", "Quests.ini"), "Duchess Has Opinions",
               [("Reward.Items", "Bucket_of_Milk 1"), ("Reward.Shards", "8"), ("Reward.XP", "Homesteading 1")])
    SK.write_script("Talk to Duchess_The_Cow", [
        ("Get.Value", "ATTRIBUTE", "CowQuest", "Variable.1$"),
        (">Conditional", "$Variable.1=0", "@s1"),
        (">Quest.Can.Start", "CowQuest", "@chat"),
        SK.say("Cow", "Yes, I can talk. No, nobody else has noticed. Yes, it's a burden. This grass is TERRIBLE. Bring "
                      "me three bunches of the good stuff, the herbs, and I'll make it worth your while. I have a "
                      "very good udder.", ("Three herbs. Got it.", "@start"), ("Cows can't talk.", "@cant")),
        ("@cant",), SK.say("Cow", "And yet. Here we are. Herbs, please.", ("Fine.", "@start")),
        ("@start",), ("Update.Attribute", "CowQuest", "=1"),
        ("Display.Message", "Yellow", "Quest started: Duchess Has Opinions.", "Quest"),
        ("End",),
        ("@s1",), (">Conditional", "$Variable.1=1", "@chat"),
        (">Got.Item", "Herb", "3", "@nope"),
        ("Take.Item", "Herb", "3"),
        ("Update.Attribute", "CowQuest", "=2"),
        ("Play.Sound", "EatFood"),
        SK.say("Cow", "Mmm. Yes. That's the stuff. You may milk me. Once. Respectfully.", ("Thank you, Duchess.", "@fin")),
        ("@fin",), ("Display.Message", "Yellow", "Quest complete: Duchess Has Opinions!", "Quest"),
        ("End",),
        ("@nope",), SK.say("Cow", "Three bunches of herbs. I can count, you know. I'm a very educated cow.",
                           ("I'll get them.", "@end")),
        ("End",),
        ("@chat",), SK.say("Cow", "Moo. That's a joke. I don't actually say moo. Much.", ("Goodbye, Duchess.", "@end")),
        ("@end",), ("End",)], MAKER)


def trousers():
    spots = {}
    for i, pid in enumerate(("Constable_Dobbs", "Clue_Footprints", "Clue_Washing", "Clue_Feather")):
        if placed(pid):
            continue
        for rmin, rmax, off_road in ((3 + i * 2, 6 + i * 3, True), (3, 12, True), (2, 10, False)):
            mname, at = free_spot("Ashford_Square", rmin, rmax, 11 + i, off_road)
            if at:
                break
        if at is None:
            continue
        kind, opts = {"Constable_Dobbs": ("Guard", "Attitude=Good Stand=1 Id=Constable_Dobbs Name=Constable_Dobbs"),
                      "Clue_Footprints": ("Muddy_Footprints", "Id=Clue_Footprints"),
                      "Clue_Washing": ("Torn_Washing", "Id=Clue_Washing"),
                      "Clue_Feather": ("Goose_Feather_Clue", "Id=Clue_Feather")}[pid]
        put(mname, obj_line("NPC" if kind == "Guard" else "StaticObject", kind, at[0], at[1], opts))
    SK.quest("The Mayor's Missing Trousers", "Guard", "TrousersQuest", {
        0: "Constable Dobbs, in Ashford's square, has a case. A very embarrassing case.",
        1: "The Mayor's trousers are gone. Look round Ashford's square for three clues, then tell "
           "Constable Dobbs who did it.",
        2: "You've found the clues. Tell Constable Dobbs who took the Mayor's trousers."}, 3,
        markers={0: "Constable_Dobbs", 1: "Ashford_Square", 2: "Constable_Dobbs"}, kind="Side",
        requires="The Ashford Road")
    SK.section(p("data", "Quests.ini"), "The Mayor's Missing Trousers",
               [("Reward.Items", "Gold_Coin(s) 50"), ("Reward.Shards", "10"), ("Reward.XP", "Defence 1")])
    SK.write_script("Talk to Constable_Dobbs", [
        ("Get.Value", "ATTRIBUTE", "TrousersQuest", "Variable.1$"),
        (">Conditional", "$Variable.1=0", "@s1"),
        (">Quest.Can.Start", "TrousersQuest", "@chat"),
        SK.say("Guard", "Psst. You. Can you keep a secret? The Mayor's trousers have been stolen. Off the washing "
                        "line. While he was, er, between trousers. Find me some clues round the square. Discreetly. "
                        "He's been in his office all day with a tablecloth round him.",
               ("I'll find the culprit.", "@start")),
        ("@start",), ("Update.Attribute", "TrousersQuest", "=1"),
        ("Update.Attribute", "TrouserClues", "=0"),
        ("Display.Message", "Yellow", "Quest started: The Mayor's Missing Trousers.", "Quest"),
        ("End",),
        ("@s1",), (">Conditional", "$Variable.1>=1 and $Variable.1<=2", "@chat"),
        (">Conditional", "$Attr.TrouserClues>=3", "@more"),
        SK.say("Guard", "Three clues, eh? Then who did it? Think carefully. I've already arrested the baker twice.",
               ("The butcher.", "@wrong"), ("The baker's apprentice.", "@wrong"), ("A goose.", "@right")),
        ("@wrong",), SK.say("Guard", "No, no. Alibi. Look at the clues again: webbed feet? A honk? A white feather?",
                            ("Let me think again.", "@end")),
        ("End",),
        ("@right",), ("Update.Attribute", "TrousersQuest", "=3"),
        ("Play.Sound", "Honk"),
        SK.say("Guard", "A goose! Of course! They're in the duck pond, wearing them. Both legs. One goose in each "
                        "leg. I'll... handle it. The Mayor thanks you. Discreetly.", ("Discreetly.", "@fin")),
        ("@fin",), ("Display.Message", "Yellow", "Quest complete: The Mayor's Missing Trousers!", "Quest"),
        ("End",),
        ("@more",), SK.say("Guard", "Clues, clues. You've found $Attr.TrouserClues of 3. Look round the square.",
                           ("On it.", "@end")),
        ("End",),
        ("@chat",), SK.say("Guard", "Move along. Nothing to see here. Especially not the Mayor.", ("Goodbye.", "@end")),
        ("@end",), ("End",)], MAKER)
    for pid, words in (("Clue_Footprints", "Webbed footprints, heading off towards the duck pond with great purpose."),
                       ("Clue_Washing", "The washing line's been snapped, and there's a single honk-shaped dent in "
                                        "the post."),
                       ("Clue_Feather", "A big white feather. Not a duck's. Bigger. Angrier.")):
        SK.write_script("Search %s" % pid, [
            (">Distance.From.Clicked.Entity", "48", "@far"),
            (">Conditional", "$Attr.TrousersQuest=1", "@look"),
            (">Conditional", "$Attr.%s=0" % pid, "@seen"),
            ("Update.Attribute", pid, "=1"),
            ("Update.Attribute", "TrouserClues", "+1"),
            ("Play.Sound", "Pickup"),
            ("Display.Message", "Yellow", "A clue! %s ($Attr.TrouserClues of 3)" % words, "-"),
            (">Conditional", "$Attr.TrouserClues>=3", "@end"),
            ("Update.Attribute", "TrousersQuest", "=2"),
            ("End",),
            ("@seen",), ("Display.Message", "Cyan", words, "-"),
            ("End",),
            ("@look",), ("Display.Message", "Cyan", words, "-"),
            ("@end",), ("End",),
            ("@far",), ("Display.Message", "DarkRed", "You are too far away!", "Denied"), ("End",)], MAKER)


def clue_art():
    """The clues' pictures: muddy webbed footprints, a snapped washing line, a big feather."""
    fp = K.new()
    for cx, cy in ((10, 12), (18, 18), (12, 25), (21, 8)):
        for dx, dy in ((0, 0), (-2, -3), (2, -3), (0, -4)):
            K.put(fp, cx + dx, cy + dy, (90, 66, 40))
            K.put(fp, cx + dx + 1, cy + dy, (90, 66, 40))
    wash = K.new()
    for y in range(8, 30):
        K.put(wash, 6, y, (110, 80, 50))
        K.put(wash, 7, y, (90, 64, 40))
    for x in range(8, 20):
        K.put(wash, x, 9 + (x - 8) // 3, (220, 220, 210))
    for y in range(12, 18):
        for x in range(12, 17):
            K.put(wash, x, y, (200, 200, 230))
    feather = K.load("Entities", "Feather")
    out = [("Muddy_Footprints", fp), ("Torn_Washing", K.outline_img(wash, (50, 40, 30))),
           ("Goose_Feather_Clue", K.hue_shift(feather, sat=0.0, val_mul=1.5))]
    print("Clues: %d written" % sum(1 for n, img in out if K.save("Entities", n, img)))


def main():
    art()
    clue_art()
    words()
    secrets()
    traps()
    scarecrow()
    duchess()
    trousers()
    print("Whimsy: done")


if __name__ == "__main__":
    main()
