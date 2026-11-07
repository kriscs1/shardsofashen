"""The Glass Wardens: a storyline in the Shardfall Deep (level 20+), after its own quests, that puts the secret of the
Shards together (dev/Story and Quests.md, "The Glass Wardens"; CLAUDE.md, "the Cutting").

  * The Wardens' Words (WardensWords, Pell): nine journals on lecterns all over the Deep, read in any order, counted
    (WardensJournal.<n>, WardensJournals). Three were build_shardfall.py's; this places the other six and writes all nine.
  * The Four Notes (FourNotes, the Singing Geode): four chimes in four places (water at the Brinewater, bone at
    Leviathan's Rest, flame in the Wardens' chapel, glass at the Shardfall's rim), struck in the Geode's order, which goes
    by the season. The fourth opens the hatch in the Reliquary.
  * What the Wardens Heard (WardensHeard, Ysolde): once both are done and Odile's Log is read (the Brine Mother gives it
    up), the Listening Room under the Reliquary (12,-17,-2): stand in the Channelling stance at the horn, hear the voice
    out and never answer it. It gives you the truth (WardensTruth=1), which is what the King's Seam's Unmake asks for.
  * Along the way: the Shardsong (Diseases.ini: a voice now and then, held still; after it, sharp eyes), caught near the
    Shard and the Geode, cured by a Quiet Draught (Morrow gives the first); the Singing Remnant the Shardborn leaves (a
    vision of the Cutting); the Wardens' Lantern (Carried.Light: it lights further round you in the dark).

build_shardfall.py's scripts Goto.Script into the ones here (Pell's, Morrow's, Ysolde's, Nell's and Bryony's idle words,
the Brine Mother's and the Shardborn's deaths, the Fallen Shard, the Geode). Safe to run again: what's placed is placed
once (anything with its Id already on a map stays where it is, the owner's moves kept).
"""
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import story_kit as SK                                           # noqa: E402
from story_kit import say, obj_line, Map                         # noqa: E402
import build_sounds as BS                                        # noqa: E402
import build_soundscape as SS                                    # noqa: E402

MAKER = "build_glass_wardens.py"
XT, YT = 25, 21
MX0, MX1, MY0, MY1 = 4, 12, -17, -5                              # (the Deep's maps on level -1)
ROOM = "12,-17,-2"                                               # (the Listening Room, under the Reliquary)

WORDS_Q = "The Glass Wardens: The Wardens' Words"
NOTES_Q = "The Glass Wardens: The Four Notes"
HEARD_Q = "The Glass Wardens: What the Wardens Heard"
FLOORS = {"Warden_Flag001", "Deep_Shingle001", "Chalk_Floor001", "Shardglass001", "Spore_Loam001", "Gallery_Floor001",
          "Cave_Floor001", "Cave_Floor003"}

# ----- the journals: (number, where it's wanted, global tile), 1-3 build_shardfall.py's on the maps already
JOURNALS = {
    1: "WARDENS' JOURNAL: the hand of Ysolde\\Year 211 of the watch. The Shard is quiet. Marshal Corvane says it sleeps. "
       "Brother Hale says it never sleeps, it only waits, and has been made to scrub the cistern for saying so.",
    2: "WARDENS' JOURNAL: the hand of Brother Hale\\It grows. We have measured it every year since the first: a hair "
       "a year, always. Marshal Corvane says it's the rock settling. Rock doesn't settle upwards.",
    3: "WARDENS' JOURNAL: the hand of Marshal Corvane\\I have heard it now. It isn't asking to be used. It's asking "
       "to be listened to, and nobody has, in four hundred years of standing guard over it with our ears stopped.\\"
       "The others will understand. I'll make them listen.",
    4: "WARDENS' JOURNAL: the hand of Odile Brask, cook\\Year 302. The water in the cistern hums when I draw it. Not loud. "
       "Just a hum, like somebody in the next room. Some days it's my mother's songs, and my mother's been dead thirty "
       "years.\\I've stopped telling the Marshal. He only says to drink less of it.",
    5: "WARDENS' JOURNAL: the hand of Brother Hale\\Year 344. Measured it again from the rim. Two hairs this year, three "
       "in the summer. It's growing faster.\\When I put the rule against it, something sighed. Not the wind: there's no "
       "wind down here. As if it had been waiting a long time for somebody to notice, and was glad.",
    6: "WARDENS' JOURNAL: the hand of Marshal Corvane\\I asked it what it wanted. Four hundred years, and nobody had "
       "asked. It said: to be whole.\\It knows my name. It knew my mother's. It only wants to be whole, and it's so small, "
       "and it's been alone so long. What sort of guard keeps a thing from its own body?",
    7: "WARDENS' JOURNAL: the hand of Ysolde\\The Order has split. Half the watch stand with Corvane, ears open. The rest "
       "of us keep the first king's orders, the ones under the altar: keep it asleep, and never, ever let it be joined "
       "to the rest of itself.\\The rest of itself. I asked the Marshal once what that meant. He didn't know. He knows "
       "now, and I think that's worse.",
    8: "WARDENS' JOURNAL: the hand of Odile Brask, cook\\I'm going in. Into the lake, I mean. The humming's loudest there, "
       "and I want to see what's singing, and I'm too old to be frightened of water.\\Whoever finds this: mind the "
       "sailors. It calls them too. I can hear it calling them, up through the rock, every night.",
    9: "WARDENS' JOURNAL: the hand of Ysolde, the last\\I'm the last who never answered it. If you're warm, and reading "
       "this, then listen: you can hear it, and you can learn from it, but never answer. Answering is how it gets in.\\"
       "There's a room under the Reliquary where we listened in turns. The four chimes keep it shut. The singing stone "
       "in the galleries remembers their order; it changes with the year, the way the old song does. I've built a cairn "
       "here, so somebody would stop.",
}
NEW_JOURNALS = [(4, (290, -303)),        # (by the cistern: Odile drew its water)
                (5, (184, -328)),        # (on the Shardfall's rim, where Hale measured it)
                (6, (297, -342)),        # (in the Wardens' chapel)
                (7, (118, -300)),        # (among the bones of Leviathan's Rest)
                (8, (165, -231)),        # (on the Brinewater's east shore, away from the Brine Mother)
                (9, (216, -258))]        # (by the delvers' camp in the Lantern Wood, a cairn beside it)
JOURNAL_IDS = ["Wardens_Journal_%d" % i for i in range(1, 10)]

# ----- the chimes, and the Geode's order by the season
CHIMES = [("Water", (164, -236), "a bronze bowl of still water on a stand, a striker hung beside it",
           "a low note, round as a drop into a well"),
          ("Bone", (128, -300), "bones as long as your arm, hung from a frame of whalebone, a striker beside them",
           "a hollow knock that goes on knocking"),
          ("Flame", (289, -348), "a bell of dark iron over a dish of embers that never go out",
           "a low bell, and the embers breathe brighter"),
          ("Glass", (206, -335), "a rod of the Shard's own glass hung from a post, a striker beside it",
           "a clear note that hangs in the air a long time")]
ORDER = {"Spring": ["Water", "Bone", "Flame", "Glass"],
         "Summer": ["Flame", "Glass", "Water", "Bone"],
         "Autumn": ["Bone", "Water", "Glass", "Flame"],
         "Winter": ["Glass", "Flame", "Bone", "Water"]}
CHIME_IDS = ["%s_Chime" % c for c, _, _, _ in CHIMES]           # (an Id is never a sprite's name: not the kind's)
HORN_ID = "Wardens_Horn"
OLD_IDS = dict([("Wardens_Chime_%s" % c, "%s_Chime" % c) for c, _, _, _ in CHIMES] + [("Listening_Horn", HORN_ID)])


# ================================================================== the Deep's maps, and where things can go
class Level:
    """Level -1's maps of the Deep, by global tile (map mx,my holds gx mx*25..mx*25+24, gy my*21..my*21+20)."""
    def __init__(self):
        self.maps, self.taken, self.changed = {}, {}, set()

    def at(self, gx, gy):
        mx, my = gx // XT, gy // YT
        name = "%d,%d,-1" % (mx, my)
        if name not in self.maps:
            self.maps[name] = Map(name) if SK.map_exists(name) else None
            if self.maps[name] is not None:
                self.taken[name] = self.occupied(self.maps[name])
        return self.maps[name], gx - mx * XT + 1, gy - my * YT + 1

    @staticmethod
    def occupied(m):
        out = set()
        for ln in m.ents:
            p = ln.split("\t")
            try:
                if p[0] in ("NPC", "StaticObject", "MapItem"):
                    out.add((int(float(p[2])) // 32 + 1, (int(float(p[3])) + 16) // 32 + 1))
                elif p[0] in ("Id", "Trigger"):
                    out.add((int(p[2]), int(p[3])))
                elif p[0] == "Lock":
                    out.add((int(p[1]), int(p[2])))
            except (IndexError, ValueError):
                pass
        return out

    def floor(self, gx, gy, bare=True):
        m, x, y = self.at(gx, gy)
        if m is None:
            return False
        t, over = m.parts(x, y)
        return t in FLOORS and (not bare or not any(over.get(k) for k in ("Decor", "Under", "Roof", "Infront", "Trigger")))

    def busy(self, gx, gy):
        m, x, y = self.at(gx, gy)
        return m is None or (x, y) in self.taken[m.name]

    def free(self, gx, gy, solid):
        if not self.floor(gx, gy) or self.busy(gx, gy):
            return False
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if (dx or dy) and (self.busy(gx + dx, gy + dy) or (solid and not self.floor(gx + dx, gy + dy))):
                    return False
        return True

    def find(self, gx, gy, solid=True, most=10):
        for r in range(most + 1):
            ring = [(gx + dx, gy + dy) for dx in range(-r, r + 1) for dy in range(-r, r + 1) if max(abs(dx), abs(dy)) == r]
            ring.sort(key=lambda c: (c[0] - gx) ** 2 + (c[1] - gy) ** 2)
            for c in ring:
                if self.free(c[0], c[1], solid):
                    return c
        return None

    def take(self, gx, gy):
        m, x, y = self.at(gx, gy)
        self.taken[m.name].add((x, y))
        self.changed.add(m.name)
        return m, x, y

    def save(self):
        for name in sorted(self.changed):
            self.maps[name].save()


def id_somewhere(pid):
    """(map name, line) where something already has the Id pid, on the Deep's maps (or the Listening Room)."""
    names = ["%d,%d,-1" % (mx, my) for mx in range(MX0, MX1 + 1) for my in range(MY0, MY1 + 1)] + [ROOM]
    for name in names:
        if SK.map_exists(name):
            for ln in Map(name).ents:
                p = ln.split("\t")
                if ("Id=%s" % pid) in p[-1].split() or p[:2] == ["Id", pid]:
                    return name, ln
    return None


def reid():
    """The first run gave the chimes and the horn their kinds' names as Ids (validate.py: an Id is never a sprite's)."""
    names = ["%d,%d,-1" % (mx, my) for mx in range(MX0, MX1 + 1) for my in range(MY0, MY1 + 1)] + [ROOM]
    for name in names:
        if not SK.map_exists(name):
            continue
        m, changed = Map(name), False
        for i, ln in enumerate(m.ents):
            p = ln.split("	")
            opts = p[-1].split()
            for old, new in OLD_IDS.items():
                if "Id=%s" % old in opts and len(p) > 4:
                    p[-1] = " ".join("Id=%s" % new if o == "Id=%s" % old else o for o in opts)
                    m.ents[i] = "	".join(p)
                    changed = True
        if changed:
            m.save()
            print("  new Ids on %s" % name)


def place_things(lv):
    """The six new journals, the cairn by the last, and the four chimes."""
    for i, (gx, gy) in NEW_JOURNALS:
        pid = "Wardens_Journal_%d" % i
        there = id_somewhere(pid)
        if there:
            print("  %s: already on %s" % (pid, there[0]))
            continue
        c = lv.find(gx, gy)
        assert c, "nowhere for %s near %d,%d" % (pid, gx, gy)
        m, x, y = lv.take(*c)
        m.ents.append(obj_line("StaticObject", "Wardens_Journal", x, y, "Id=%s" % pid))
        print("  %s: %s at %d,%d" % (pid, m.name, x, y))
        if i == 9:                                   # (Ysolde's cairn beside her last page)
            for dx, dy in ((1, 0), (-1, 0), (0, -1), (1, -1), (-1, -1)):
                if lv.floor(c[0] + dx, c[1] + dy) and not lv.busy(c[0] + dx, c[1] + dy):
                    cm, cx, cy = lv.take(c[0] + dx, c[1] + dy)
                    cm.set(cx, cy, decor="Cairn001")
                    break
    for kind, (gx, gy), _, _ in CHIMES:
        pid = "%s_Chime" % kind
        there = id_somewhere(pid)
        if there:
            print("  %s: already on %s" % (pid, there[0]))
            continue
        c = lv.find(gx, gy)
        assert c, "nowhere for %s near %d,%d" % (pid, gx, gy)
        m, x, y = lv.take(*c)
        m.ents.append(obj_line("StaticObject", "Wardens_Chime_%s" % kind, x, y, "Id=%s" % pid, -16))
        print("  %s: %s at %d,%d" % (pid, m.name, x, y))


def hatch_and_room(lv):
    """The hatch in the Reliquary (12,-17,-1) and the Listening Room under it (12,-17,-2). Returns the hatch's tile."""
    rel = Map("12,-17,-1")
    for ln in rel.ents:
        p = ln.split("\t")
        if p[:2] == ["Id", "Listening_Hatch"]:
            hx, hy = int(p[2]), int(p[3])
            break
    else:
        c = lv.find(300 + 12, -357 + 14, solid=False, most=5)           # (the Reliquary's south half, local 13,15)
        assert c, "nowhere in the Reliquary for the hatch"
        m, hx, hy = lv.take(*c)
        assert m.name == "12,-17,-1"
        m.set(hx, hy, decor="Hatch001")
        SK.place_id(m, "Listening_Hatch", hx, hy)
        print("  the Listening Room's hatch: 12,-17,-1 at %d,%d" % (hx, hy))
    assert 6 <= hx <= 20 and 7 <= hy <= 19, (hx, hy)
    if SK.map_exists(ROOM):
        return hx, hy
    r = Map(ROOM, new=True)
    x0, x1, y0, y1 = hx - 4, hx + 4, hy - 5, hy + 1               # (the floor)
    for y in range(y0 - 1, y1 + 2):
        for x in range(x0 - 1, x1 + 2):
            if x0 <= x <= x1 and y0 <= y <= y1:
                t = "Warden_Flag001"
            elif y == y0 - 1 and x0 <= x <= x1:
                t = "Warden_Wall003" if x in (x0 + 1, x1 - 1) else "Warden_Wall002"    # (the back wall's face, two runes)
            else:
                t = "Warden_Wall001"
            r.put(x, y, t, {})
    r.set(hx, hy, decor="Ladder001")
    for x in (x0, x1):
        r.set(x, y0, decor="Warden_Brazier001")
    r.set(x1, y1, decor="Candles001")
    r.set(x0, y1, decor="Candles001")
    r.ents.append(obj_line("StaticObject", "Listening_Horn", hx, y0, "Id=%s" % HORN_ID))
    SK.place_id(r, "Listening_Room", hx, hy - 2)
    r.save()
    print("  the Listening Room: %s, its ladder at %d,%d" % (ROOM, hx, hy))
    return hx, hy


def dim_room():
    """The Listening Room is as dim as the rest of the Deep (build_shardfall.py config_data keeps it so too)."""
    have = (SK.ini.read("Darkness", "Maps", "", SK.CONFIG) or "").split()
    if ROOM not in have:
        SK.ini.write("Darkness", "Maps", " ".join(have + [ROOM]), SK.CONFIG)


# ================================================================== data: things, items, the disease, the recipe, quests
def data():
    S = SK.section
    for kind, _, looks, _ in CHIMES:
        S(SK.ENTS, "Wardens_Chime_%s" % kind, [
            ("Type", "StaticObject"), ("Display.Name", "%s Chime" % kind), ("Use.Words", "Strike,Examine"), ("Solid", "1"),
            ("Light", "30"), ("Examine.Info", "One of the Wardens' chimes: %s." % looks)])
    S(SK.ENTS, "Listening_Horn", [("Type", "StaticObject"), ("Display.Name", "Listening Horn"), ("Use.Words", "Listen,Examine"),
                                  ("Solid", "1"), ("Light", "40"),
                                  ("Examine.Info", "A great horn of black glass, its mouth to the wall, its narrow end at the "
                                   "height of an ear. The stone round it is worn smooth by people leaning.")])
    S(SK.ENTS, "The_Voice", [("Type", "StaticObject"), ("Use.Words", "Examine"),
                             ("Examine.Info", "Nothing. Nothing at all.")])
    S(SK.ENTS, "Ysolde", [("Type", "NPC"), ("Use.Words", "Talk to,Examine"), ("Attitude", "Good"),
                          ("Examine.Info", "Ysolde, the last of the Glass Wardens, hardly there at all."),
                          ("Movement.Speed", "0.6"), ("Roam.Radius", "0"), ("Chase.Radius", "0"), ("Walk.Speed", "0.3"),
                          ("Schedule", "Always"), ("Light", "40"), ("Level", "1"), ("Solid", "0"),
                          ("Respawn", "300")])
    items = [
        ("Odiles_Log", [("Display.Name", "Odile's Log"), ("Use.Words", "Read,Examine"), ("Stackable", "1"),
                        ("Droppable", "0"), ("Value", "0"),
                        ("Examine.Info", "A book in an oilskin, out of the Brine Mother's lake, its pages stuck together.")]),
        ("Pells_Book", [("Display.Name", "Pell's Book"), ("Use.Words", "Read,Examine"), ("Stackable", "1"), ("Value", "0"),
                        ("Droppable", "0"),
                        ("Examine.Info", "Pell Varrow's fair copy of the Wardens' journals: the first true history of "
                         "the Glass Wardens.")]),
        ("Singing_Remnant", [("Display.Name", "Singing Remnant"), ("Use.Words", "Listen,Examine"), ("Stackable", "1"),
                             ("Droppable", "0"), ("Value", "0"), ("Light", "30"),
                             ("Examine.Info", "A piece of the Shardborn that won't stop chiming. It's warm.")]),
        ("Quiet_Draught", [("Display.Name", "Quiet Draught"), ("Use.Words", "Drink"), ("Stackable", "1"), ("Value", "60"),
                           ("Cures", "Shardsong Listening"),
                           ("Examine.Info", "A grey-blue draught of glowfin and cave mushroom. It stills a voice in your "
                            "head that isn't yours.")]),
        ("Wardens_Lantern", [("Display.Name", "Wardens' Lantern"), ("Use.Words", "Examine"), ("Stackable", "1"),
                             ("Droppable", "0"), ("Value", "0"), ("Light", "60"), ("Carried.Light", "260"),
                             ("Examine.Info", "Ysolde's lantern, its glass the Shard's own. Carried, it lights the dark "
                              "a long way round you.")]),
    ]
    for name, keys in items:
        S(SK.ENTS, name, [("Type", "MapItem")] + keys)
    SK.copy_tile("Cairn001", "Warden_Brazier001", Light="0", Show_Name="1", Use_Words="Examine",
                 Examine_Info="Stones piled up with care, the top one a chip of the Shard's glass.", Piece="a cairn")
    dis = os.path.join(SK.DATA, "Diseases.ini")
    SK.set_section(dis, "Shardsong", [
        "; What a bout of it is: a voice, held still to hear it, then sharp eyes a while (player_combat.py Listening, Keen)",
        "Effect=Listening",
        "Incubation.Seconds=60",
        "Every.Min.Minutes=6",
        "Every.Max.Minutes=12",
        "Words=A voice comes and goes in your head: a Quiet Draught would still it",
        "Caught=The song stays in your head after you've let go of it. It's still there a minute later.",
        "Caught.Sound=Shard_Voice",
        "Bout.Sound=Shard_Voice",
        "Cured=The humming in your head goes quiet, and stays quiet.",
        "Cured.Sound=Fever_Cured"])
    craft_line("CRAFT-Potion_Making", "Quiet_Draught", "Quiet_Draught,Raw_Glowfin 1 Cave_Mushroom 1 Empty_Vial 1,1.4,18")
    SK.quest(WORDS_Q, "Scholar", "WardensWords", {
        0: "Pell Varrow, in the delvers' camp, has read three of the Glass Wardens' journals, and they don't make sense in "
           "threes.",
        1: "Pell wants all nine of the Wardens' journals read. They're on lecterns all over the Deep, where the Wardens "
           "left them.",
        2: "All nine of the Wardens' journals read. Tell Pell."}, 3,
        markers={0: "Pell_Varrow", 1: ";".join(JOURNAL_IDS), 2: "Pell_Varrow"}, kind="Side", requires="Charting the Deep",
        level=20)
    S(SK.QUESTS, WORDS_Q, [("Reward.Items", "Pells_Book 1 Gold_Coin(s) 800"), ("Reward.Shards", "50"),
                           ("Reward.XP", "Shardcraft 3"),
                           ("Rumour", "A map-maker's gone down under the sea after the Glass Wardens' old books. She says "
                            "they wrote standing up.")])
    SK.quest(NOTES_Q, "Singing_Geode", "FourNotes", {
        0: "The singing stone in the Glimmering Galleries sings four notes, over and over.",
        1: "The Wardens left four chimes: water at the Brinewater, bone at Leviathan's Rest, flame in their chapel and "
           "glass at the Shardfall's rim. Strike them in the Singing Geode's order; it changes with the seasons."}, 2,
        markers={0: "The_Singing_Geode", 1: ";".join(CHIME_IDS)}, kind="Side", requires="Glass in the Nets", level=20)
    S(SK.QUESTS, NOTES_Q, [("Reward.Shards", "40"), ("Reward.XP", "Shardcraft 4"),
                           ("Rumour", "There's a stone under the sea that sings, the fishermen say, and it never sings the "
                            "same tune two seasons running.")])
    SK.quest(HEARD_Q, "Ghost_Warden", "WardensHeard", {
        0: "Ysolde, the last of the Glass Wardens, has something she never finished.",
        1: "Go down into the Listening Room under the Reliquary. Stand still in the Channelling stance at the horn, and "
           "listen. Whatever it says, don't answer."}, 2,
        markers={0: "Warden_Ysolde", 1: "Listening_Hatch"}, kind="Side", requires="The Fallen Shard", level=20)
    S(SK.QUESTS, HEARD_Q, [("Reward.Items", "Wardens_Lantern 1"), ("Reward.Shards", "100"), ("Reward.XP", "Shardcraft 6"),
                           ("Rumour", "The Glass Wardens listened to something under the sea for four hundred years, the "
                            "old songs say, and never once answered it.")])


def craft_line(rack, product, line):
    """An ItemN= line in a rack of ItemRacks.ini, once (the next free number)."""
    path = os.path.join(SK.DATA, "ItemRacks.ini")
    keys = SK.ini.section(rack, path)
    if any(v.split(",")[0] == product for _, v in keys):
        return
    n = 1 + max([int(k[4:]) for k, _ in keys if k.startswith("Item") and k[4:].isdigit()] or [0])
    SK.ini.write(rack, "Item%d" % n, line, path)


# ================================================================== scripts
def scripts(hx, hy):
    W = lambda name, rows: SK.write_script(name, rows, MAKER)        # noqa: E731
    far = [("@far",), ("Display.Message", "DarkRed", "You are too far away!", "Denied"), ("End",)]

    # ----- the journals (all nine), counted for Pell
    for i, text in JOURNALS.items():
        W("Read Wardens_Journal_%d" % i, [
            (">Distance.From.Clicked.Entity", "64", "@far"),
            ("Display.Conversation", "Notice", text, "Okay", "@read"),
            ("@read",),
            (">Conditional", "$Attr.WardensJournal.%d=0" % i, "@end"),
            ("Update.Attribute", "WardensJournal.%d" % i, "=1"),
            ("Update.Attribute", "WardensJournals", "+1"),
            (">Conditional", "$Attr.WardensWords=1", "@end"),
            (">Conditional", "$Attr.WardensJournals>=9", "@end"),
            ("Update.Attribute", "WardensWords", "=2"),
            ("Quest.Note.Done", WORDS_Q, "All nine journals read."),
            ("Display.Message", "Yellow", "That's all nine of the Wardens' journals: back to Pell.", "-"),
            ("@end",), ("End",)] + far)

    # ----- Pell: The Wardens' Words (from her idle words, once Charting the Deep's done)
    W("Pell and the Wardens", [
        (">Conditional", "$Attr.DeepChartQuest>=3", "@idle"),
        ("Get.Value", "ATTRIBUTE", "WardensWords", "Variable.1$"),
        (">Conditional", "$Variable.1=0", "@one"),
        (">Quest.Can.Start", "WardensWords", "@idle"),
        say("Scholar", "The Wardens wrote everything down. Nine journals, I think, left on lecterns all over the Deep, "
                       "wherever the last of them were standing when they stopped.\\I've read three. They don't make sense "
                       "in threes. Read them all for me? I'll pay, and I'll write it up properly: the first true history "
                       "of the Glass Wardens.", ("I'll find them.", "@start"), ("Not now.", "@end")),
        ("@start",), ("Update.Attribute", "WardensWords", "=1"),
        ("Display.Message", "Yellow", "Quest started: %s." % WORDS_Q, "Quest"),
        (">Conditional", "$Attr.WardensJournals>=9", "@end"),
        ("Update.Attribute", "WardensWords", "=2"),
        ("Quest.Note.Done", WORDS_Q, "All nine journals read."), ("End",),
        ("@one",), (">Conditional", "$Variable.1<=2", "@after"),
        (">Conditional", "$Attr.WardensJournals>=9", "@more"),
        ("Update.Attribute", "WardensWords", "=3"),
        say("Scholar", "All nine. All nine! Let me... oh. Oh, that's not what I thought at all.\\They weren't guarding a "
                       "treasure. They were guarding a mouth. Here: I've copied it fair. Take the book. I don't think I "
                       "want it in my tent.", ("Thank you, Pell.", "@end")),
        ("Display.Message", "Yellow", "Quest complete: %s!" % WORDS_Q, "Quest"), ("End",),
        ("@more",),
        say("Scholar", "$Attr.WardensJournals of nine. Lecterns, remember: the Wardens wrote standing up. Probably so "
                       "they'd notice if they fell asleep.", ("I'll keep looking.", "@end")), ("End",),
        ("@after",), (">Conditional", "$Attr.WardensTruth=1", "@idle"),
        say("Scholar", "I've redrawn the chart. Where it said 'the Fallen Shard' I've written 'here it sleeps'. It seemed "
                       "more honest.", ("Goodbye, Pell.", "@end")), ("End",),
        ("@idle",),
        say("Scholar", "The lake's north, the bones are west, the pit's north again. The mushrooms are everywhere. Mind the "
                       "moths.", ("Goodbye, Pell.", "@end")),
        ("@end",), ("End",)])

    # ----- the Brine Mother's log, and Morrow
    W("Brine Mother's Log", [
        (">Conditional", "$Attr.OdilesLogGot=0", "@end"),
        ("Update.Attribute", "OdilesLogGot", "=1"),
        ("Give.Item", "Odiles_Log", "1"),
        ("Display.Message", "Cyan", "Something comes up where she sank: a book in an oilskin, its pages stuck together.", "-"),
        ("@end",), ("End",)])
    W("Read Odiles_Log", [
        say("Notice", "ODILE'S LOG, in an oilskin\\Forty years I've cooked for the Wardens. Bread on the first day of the "
                      "week, fish the rest. The cistern hums. The lake hums louder.\\(The writing gets bigger, page by page.) "
                      "It's warm in the water. I don't need the lamp. I hardly need to breathe.\\(The last pages, in "
                      "letters as tall as your hand.) THEY HEAR IT TOO, THE SAILORS. THEY COME DOWN THROUGH THE ROCK TO "
                      "IT. I ONLY KEEP THEM FROM GOING TO IT. I'M SORRY. I'M SORRY ABOUT THE BOAT.",
            ("Close it.", "@read")),
        ("@read",), (">Conditional", "$Attr.OdilesLog=0", "@end"),
        ("Update.Attribute", "OdilesLog", "=1"),
        ("@end",), ("End",)])
    W("Morrow and the Log", [
        (">Conditional", "$Attr.OdilesLogShown=0", "@song"),
        (">Got.Item", "Odiles_Log", "1", "@song"),
        ("Update.Attribute", "OdilesLogShown", "=1"),
        say("Fisherman", "What's that? ...That's Odile's hand. Odile Brask. She cooked for the Wardens, my granddad said; "
                         "there's songs about her soup.\\'I'm sorry about the boat.' Davey heard something, the week "
                         "before. Said the lake was singing to him. I told him it was the wind.",
            ("I'm sorry, Morrow.", "@end")), ("End",),
        ("@song",), (">Conditional", "$Player.Shardsong=1", "@idle"),
        (">Conditional", "$Attr.MorrowQuietGift=0", "@recipe"),
        ("Update.Attribute", "MorrowQuietGift", "=1"),
        say("Fisherman", "You've got it, haven't you. The humming. You keep stopping like somebody's said your name.\\Here. "
                         "Davey's mother made these for him: glowfin and a cave mushroom, boiled down. It shuts it up. "
                         "I've only the one. You'll have to brew the next yourself.", ("Thank you.", "@give")),
        ("@give",), ("Give.Item", "Quiet_Draught", "1"),
        ("Display.Message", "Yellow", "Morrow gives you a Quiet Draught.", "-"), ("End",),
        ("@recipe",),
        say("Fisherman", "Still humming? Glowfin and a cave mushroom in a vial, boiled down slow: eighteen years of alchemy, "
                         "that wants. It's the only thing that shuts it up.", ("Thanks.", "@end")), ("End",),
        ("@idle",),
        say("Fisherman", "Glowfin bite where the water lights up, off the shore. You'll want a good rod, good bait, and good "
                         "fishing: twenty-two years of it, I'd say.", ("Thanks.", "@end")),
        ("@end",), ("End",)])

    # ----- the Shardsong (the Fallen Shard, the Geode)
    W("Shardsong Near", [
        (">Conditional", "$Player.Shardsong=0", "@end"),
        (">Conditional", "$Random.Percent<=12", "@end"),
        ("Catch.Disease", "Shardsong"),
        ("@end",), ("End",)])

    # ----- the Shardborn's Singing Remnant: the Cutting
    W("Shardborn's Remnant", [
        (">Conditional", "$Attr.SingingRemnantGot=0", "@end"),
        ("Update.Attribute", "SingingRemnantGot", "=1"),
        ("Give.Item", "Singing_Remnant", "1"),
        ("Display.Message", "Cyan", "One piece of it doesn't stop chiming. You pick it up. It's warm.", "-"),
        ("@end",), ("End",)])
    W("Listen Singing_Remnant", [
        ("Play.Sound", "Cutting_Vision"),
        say("Singing_Remnant", "You hold it to your ear, and you're not you.\\You're huge. You're hungry. Everything that "
                               "shines, you swallow: the light off the sea, the warmth out of the ground, the magic out of "
                               "everything. You swallow, and you're still hungry.", ("...", "@two")),
        ("@two",),
        say("Singing_Remnant", "A man stands in front of you, so small you could breathe him in. He holds up a blade that "
                               "isn't metal. It's a line in the air, and it's bright.\\The first king.", ("...", "@three")),
        ("@three",),
        say("Singing_Remnant", "He cuts. Not at you: through you. Most of you falls away, out of the world, into a hollow "
                               "dark where nothing shines. What's left is small enough to tie down.", ("...", "@four")),
        ("@four",),
        say("Singing_Remnant", "And where the blade went through, sparks: a rain of them, all over the world, and every one "
                               "of them still hungry.\\Shards.", ("Let go of it.", "@done")),
        ("@done",),
        ("Take.Item", "Singing_Remnant", "1"),
        ("Give.Item", "Shard", "25"),
        ("Update.Attribute", "SawCutting", "=1"),
        ("Update.Skill", "Shardcraft", "+1"),
        ("Display.Message", "Cyan", "The remnant goes quiet in your hand, and comes apart into Shards.", "Absorb"),
        ("End",)])

    # ----- the Four Notes: the Geode plays today's order; the chimes
    rows = [("Wait", "1.5")]
    seasons = list(ORDER)
    for k, season in enumerate(seasons):
        nxt = "@%s" % seasons[k + 1] if k + 1 < len(seasons) else None
        rows += [("@%s" % season,)]
        if nxt:
            rows += [(">Conditional", "$World.Season=%s" % season, nxt)]
        for j, c in enumerate(ORDER[season]):
            rows += [("Play.Sound", "Chime_%s" % c)] + ([("Wait", "0.9")] if j < 3 else [])
        rows += [("Display.Message", "Cyan", "Four notes, over and over: %s. You find you're humming them too." %
                  ", ".join(c.lower() for c in ORDER[season]), "-"), ("Goto.Line", "@after")]
    rows += [("@after",),
             (">Conditional", "$Attr.FourNotes=0", "@song"),
             (">Quest.Can.Start", "FourNotes", "@song"),
             ("Update.Attribute", "FourNotes", "=1"),
             ("Update.Attribute", "FourNotes.Step", "=0"),
             ("Display.Message", "Yellow", "Quest started: %s." % NOTES_Q, "Quest"),
             ("@song",), ("Goto.Script", "Shardsong Near"), ("End",)]
    W("Geode's Four Notes", rows)
    for kind, _, _, heard in CHIMES:
        rows = [(">Distance.From.Clicked.Entity", "56", "@far"),
                ("Play.Sound", "Chime_%s" % kind),
                (">Conditional", "$Attr.FourNotes=1", "@plain"),
                ("Get.Value", "ATTRIBUTE", "FourNotes.Step", "Variable.1$")]
        for k, season in enumerate(seasons):
            rows += [("@c%s" % season,)]
            if k + 1 < len(seasons):
                rows += [(">Conditional", "$World.Season=%s" % season, "@c%s" % seasons[k + 1])]
            rows += [(">Conditional", "$Variable.1=%d" % ORDER[season].index(kind), "@wrong"), ("Goto.Line", "@right")]
        rows += [("@right",),
                 ("Update.Attribute", "FourNotes.Step", "+1"),
                 (">Conditional", "$Attr.FourNotes.Step>=4", "@good"),
                 ("Update.Attribute", "FourNotes", "=2"),
                 ("Update.Attribute", "FourNotes.Step", "=0"),
                 ("Quest.Note.Done", NOTES_Q, "The four notes rang true."),
                 ("Display.Message", "Yellow", "The four notes hang in the air together. Far off, under the Reliquary, "
                                               "something heavy settles open.", "-"),
                 ("Display.Message", "Yellow", "Quest complete: %s!" % NOTES_Q, "Quest"), ("End",),
                 ("@good",), ("Display.Message", "Cyan", "%s. Somewhere, a crystal answers it." % heard.capitalize(), "-"),
                 ("End",),
                 ("@wrong",), ("Update.Attribute", "FourNotes.Step", "=0"),
                 ("Display.Message", "DarkRed", "The note jars against the last one, and the crystals fall silent.", "Fail"),
                 ("End",),
                 ("@plain",), ("Display.Message", "Cyan", "%s." % heard.capitalize(), "-"), ("End",)] + far
        W("Strike Wardens_Chime_%s" % kind, rows)

    # ----- Ysolde: What the Wardens Heard (from her words once both watches are done)
    W("Ysolde and the Wardens", [
        ("Get.Value", "ATTRIBUTE", "WardensHeard", "Variable.3$"),
        (">Conditional", "$Variable.3=0", "@one"),
        (">Conditional", "$Attr.WardensWords>=3", "@rest"),
        (">Conditional", "$Attr.FourNotes>=2", "@rest"),
        (">Conditional", "$Attr.OdilesLog>=1", "@rest"),
        (">Quest.Can.Start", "WardensHeard", "@rest"),
        say("Ghost_Warden", "You've read our words. You've rung the four notes. You've read Odile. Poor Odile: she kept them "
                            "from it in the end, the only way she had left.\\Then you nearly know what we were for. Not to "
                            "guard the Shard. To listen to it, and never once answer. Corvane answered.",
            ("What did it say to him?", "@b"), ("Not now.", "@end")),
        ("@b",),
        say("Ghost_Warden", "Come and hear for yourself. Under the Reliquary there's a room the chimes keep shut: the "
                            "Listening Room. Stand still in it the way you'd stand to cast, and listen at the horn. It will "
                            "talk to you. Don't answer. Whatever it says, don't answer.\\I'll be there. I was always there.",
            ("I'll come.", "@c"), ("Not yet.", "@end")),
        ("@c",), ("Update.Attribute", "WardensHeard", "=1"),
        ("Display.Message", "Yellow", "Quest started: %s." % HEARD_Q, "Quest"), ("End",),
        ("@one",), (">Conditional", "$Variable.3=1", "@two"),
        say("Ghost_Warden", "The Listening Room, under the Reliquary. Stand as if to cast. Listen. Don't answer.",
            ("I remember.", "@end")), ("End",),
        ("@two",),
        ("Display.Message", "Cyan", "Ysolde is very faint now, hardly there at all. She smiles at you and says nothing, the "
                                    "way you taught her.", "-"), ("End",),
        ("@rest",),
        say("Ghost_Warden", "You've heard it now. Everybody who touches it does.\\The watch is yours, warm one. I'd rest, if "
                            "I could. There's something I never finished, and I can't think what.",
            ("Rest well, Ysolde.", "@end")),
        ("@end",), ("End",)])

    # ----- the Listening Room
    W("Climb Down Listening_Hatch", [
        (">Distance.From.Clicked.Tile", "48", "@far"),
        (">Conditional", "$Attr.FourNotes>=2", "@shut"),
        (">Map.Exists", ROOM, "@shut"),
        ("Play.Sound", "Ladder"), ("Wait", "0.4"),
        ("Teleport", "%d,%d" % ((hx - 1) * 32, (hy - 1) * 32 - 8), ROOM),
        ("Display.Message", "Cyan", "You climb down into a small stone room. The sea is very close, the other side of the "
                                    "wall.", "-"),
        ("End",),
        ("@shut",), ("Display.Message", "DarkRed", "The hatch won't move.", "Denied"), ("End",)] + far)
    yx, yy = (hx + 2 - 1) * 32, (hy - 4 - 1) * 32 - 8                 # (her spot, by the horn)
    W(ROOM, [
        ("Get.Value", "ATTRIBUTE", "WardensHeard", "Variable.1$"),
        (">Conditional", "$Variable.1=1", "@end"),
        ("Add.Entity", "%d,%d" % (yx, yy), "Ysolde", "NPC", "Attitude=Good Stand=1"),
        ("@end",), ("End",)])
    W("Talk to Ysolde", [
        say("Ysolde", "Stand still the way you would to cast, and listen at the horn. And whatever it says, warm one, don't "
                      "answer.", ("I won't.", "@end")),
        ("@end",), ("End",)])
    voice = [
        "You came. I know you. I knew you before you had a name.\\Your mother carried my sparks, and she asked them how the "
        "Pact was made, and I told her, because she asked so nicely. Then she ran. Where is she now?\\...Ah. I'm sorry. I "
        "am. Say something.",
        "Do you know what I am? Ask the king who cut me.\\Long ago I was big enough to swallow the light out of the sky, "
        "and so hungry. He cut me down with a line of light and pushed most of me out, into the dark where all broken "
        "magic goes. The sparks were left behind. You call them Shards. You keep them in jars.",
        "Every piece of me wants to be whole. That's all. That's why a beast's sparks come for the one who killed it: they "
        "want a body, and yours is so warm.\\And the little bit of me they tied down by the mountains? They fed it a child "
        "every king, and called it a Pact. I call it supper.",
        "Answer me! Corvane answered. Your mother answered. Everybody answers!\\Is it the Seam? Has somebody told you "
        "about the Seam? Where the first cut was made, where the firstborn's blood keeps it open, so I can feed through it, "
        "so I can... If it broke, I'd never be whole. I'd be a shadow, asleep, for ever.\\Don't. Don't break it. Answer "
        "me."]
    replies = ["Leave my mother out of this.", "That's a lie.", "You monster.", "Never."]
    rows = [(">Distance.From.Clicked.Entity", "56", "@far"),
            (">Conditional", "$Attr.WardensHeard=1", "@quiet"),
            (">Conditional", "$Player.Stance=Channelling", "@nostance"),
            ("Play.Sound", "Shard_Voice"),
            ("Display.Message", "Cyan", "You stand very still, and let the Shards round you go quiet, and put your ear to the "
                                        "horn.", "-"),
            ("Wait", "1.5")]
    for k, text in enumerate(voice):
        nxt = "@v%d" % (k + 2) if k + 1 < len(voice) else "@heard"
        if k:
            rows += [("@v%d" % (k + 1),), (">Conditional", "$Player.Stance=Channelling", "@broke"), ("Play.Sound", "Shard_Voice")]
        rows += [say("The_Voice", text, ("Say nothing.", nxt), (replies[k], "@answered"))]
    rows += [("@heard",), (">Conditional", "$Player.Stance=Channelling", "@broke"),
             ("Goto.Script", "Listening Room's End"),
             ("@answered",),
             ("Display.Message", "DarkRed", "You answered it. For a moment the voice is very close, and very pleased, and then "
                                            "it's gone, and Ysolde's light gutters.", "Fail"),
             (">Conditional", "$Random.Percent<=30", "@end"),
             ("Catch.Disease", "Shardsong"), ("End",),
             ("@broke",),
             ("Display.Message", "DarkRed", "You let go of the stillness, and the voice slides away into the hum.", "Fail"),
             ("End",),
             ("@nostance",),
             say("Ysolde", "Not like that. Stand the way you would to cast: still, the Shards round you held quiet. Then "
                           "listen. And whatever it says, don't answer.", ("I'll try.", "@end")), ("End",),
             ("@quiet",),
             ("Display.Message", "Cyan", "Only the sea, far off, the other side of the stone.", "-"),
             ("@end",), ("End",)] + far
    W("Listen Listening_Horn", rows)
    W("Listening Room's End", [
        say("Ysolde", "You heard it all, and you never said a word.\\That's all we were ever for. Not to guard it: to hear "
                      "it, and not answer. Four hundred years, and it took a warm one to do it properly.",
            ("What now?", "@b")),
        ("@b",),
        say("Ysolde", "Now you know what it is, and what it's afraid of: the Seam, where the first cut was made. If it's "
                      "ever yours to break, warm one, break it.\\I think I can rest now. Tell Pell her chart's wrong about "
                      "one thing. It was never the Shard's Deep. It was ours.", ("Rest well, Ysolde.", "@c")),
        ("@c",),
        ("Update.Attribute", "WardensTruth", "=1"),
        ("Update.Attribute", "WardensHeard", "=2"),
        ("Quest.Note.Done", HEARD_Q, "You heard the voice out, and never answered it."),
        ("Play.Sound", "Ysolde_Rest"),
        ("Remove.Entity", "%d,%d" % (yx, yy), "Ysolde"),
        ("Display.Message", "Cyan", "Ysolde's light goes out, gently, like a lamp turned down.", "-"),
        ("Display.Message", "Yellow", "Quest complete: %s!" % HEARD_Q, "Quest"),
        ("End",)])

    # ----- Pell's book, Nell and Bryony after
    W("Read Pells_Book", [
        say("Notice", "THE GLASS WARDENS, a true history, by Pell Varrow\\The first king set the Wardens to keep the Shard "
                      "that fell into the sea. Their orders, kept under the chapel's altar, were to keep it asleep, and "
                      "never let it be joined to the rest of itself.\\For four hundred years they listened to it and never "
                      "answered. Then Marshal Corvane asked it a question. Half the Order followed him; the cook walked "
                      "into the lake; the last of them, Ysolde, kept the watch alone.\\I don't know yet what 'the rest of "
                      "itself' is. I'm not sure I want to.", ("Close it.", "@end")),
        ("@end",), ("End",)])
    W("Nell and the Wardens", [
        (">Conditional", "$Attr.WardensTruth=1", "@open"),
        say("Woman", "You look like somebody who's heard something they can't unhear. Sit down. Gran'll make tea. Gran makes "
                     "tea for everything.", ("Goodbye, Nell.", "@end")), ("End",),
        ("@open",),
        say("Woman", "You went in? Through that door? And came out again?\\The glass is still coming in on the tide. I've "
                     "started selling it. Somebody may as well.", ("Goodbye, Nell.", "@end")),
        ("@end",), ("End",)])
    W("Bryony and the Wardens", [
        (">Conditional", "$Attr.WardensTruth=1", "@idle"),
        say("Old_Woman", "My mother said the Wardens listened so that nobody else would have to. Was it like that?\\...No. "
                         "Don't tell me. Sit down.", ("Goodbye, Bryony.", "@end")), ("End",),
        ("@idle",),
        say("Old_Woman", "Sit down, sit down. Nell's out on the rocks again. That girl will have the sea in her pockets one of "
                         "these days.", ("Goodbye, Bryony.", "@end")),
        ("@end",), ("End",)])


# ================================================================== pictures
def pictures():
    p = SK.pg()
    rnd = random.Random(4471)

    def frame(base, hang):
        """A chime: two posts and a beam (32 x 48), what hangs drawn by hang(s)."""
        s = SK.surface(32, 48)
        p.draw.rect(s, base, (5, 14, 3, 32))
        p.draw.rect(s, base, (24, 14, 3, 32))
        p.draw.rect(s, tuple(min(255, c + 25) for c in base), (3, 12, 26, 4))
        p.draw.rect(s, (60, 56, 64), (2, 44, 28, 4))
        hang(s)
        return SK.outlined(s)

    def water(s):
        p.draw.ellipse(s, (150, 104, 52), (8, 30, 16, 9))
        p.draw.ellipse(s, (70, 130, 160), (10, 31, 12, 5))
        p.draw.rect(s, (110, 80, 44), (14, 38, 4, 7))
        p.draw.line(s, (180, 170, 150), (22, 16), (22, 27))
        p.draw.circle(s, (120, 90, 60), (22, 28), 2)

    def bone(s):
        for k, x in enumerate((10, 14, 18, 22)):
            p.draw.line(s, (200, 196, 180), (x, 16), (x, 30 + k * 3), 2)
            p.draw.circle(s, (220, 216, 200), (x, 30 + k * 3), 2)

    def flame(s):
        p.draw.line(s, (60, 56, 60), (16, 16), (16, 20))
        p.draw.polygon(s, (54, 50, 58), [(10, 30), (12, 21), (20, 21), (22, 30)])
        p.draw.ellipse(s, (70, 64, 70), (9, 28, 14, 4))
        p.draw.rect(s, (60, 56, 64), (11, 37, 10, 3))
        for _ in range(6):
            p.draw.circle(s, rnd.choice([(230, 120, 40), (250, 180, 60), (200, 70, 30)]), (rnd.randint(12, 19), 36), 1)

    def glass(s):
        p.draw.line(s, (170, 160, 180), (16, 16), (16, 19))
        p.draw.polygon(s, (170, 120, 230), [(14, 19), (18, 19), (17, 40), (15, 40)])
        p.draw.line(s, (230, 210, 255), (15, 21), (15, 37))

    looks = {"Water": ((96, 90, 98), water), "Bone": ((190, 182, 160), bone), "Flame": ((70, 64, 72), flame),
             "Glass": ((96, 84, 110), glass)}
    for kind, (base, hang) in looks.items():
        SK.save("Entities", "Wardens_Chime_%s" % kind, frame(base, hang))
    # the horn
    s = SK.surface()
    p.draw.polygon(s, (30, 26, 40), [(4, 4), (28, 4), (19, 20), (17, 29), (15, 29), (13, 20)])
    p.draw.polygon(s, (60, 46, 90), [(7, 6), (25, 6), (18, 18), (14, 18)])
    p.draw.ellipse(s, (14, 10, 22), (9, 6, 14, 6))
    SK.save("Entities", "Listening_Horn", SK.outlined(s))
    # the voice: nothing, and a mouth of light in it
    s = SK.surface()
    p.draw.circle(s, (10, 6, 18), (16, 16), 15)
    for k in range(5, 0, -1):
        p.draw.ellipse(s, (60 + k * 20, 30 + k * 8, 110 + k * 25), (16 - k * 2, 15 - k, k * 4, k * 2 + 1))
    SK.save("Entities", "The_Voice", s)
    # books, the log and Pell's
    for name, cover, band in (("Odiles_Log", (78, 84, 50), (40, 44, 26)), ("Pells_Book", (130, 52, 40), (210, 180, 90))):
        s = SK.surface()
        p.draw.rect(s, cover, (7, 6, 18, 22))
        p.draw.rect(s, (230, 222, 196), (23, 7, 3, 20))
        p.draw.rect(s, band, (7, 13, 18, 3))
        p.draw.line(s, tuple(c // 2 for c in cover), (8, 6), (8, 27))
        SK.save("Entities", name, SK.outlined(s))
    # the Singing Remnant
    s = SK.surface()
    p.draw.polygon(s, (150, 100, 220), [(16, 4), (23, 14), (19, 28), (12, 27), (9, 13)])
    p.draw.polygon(s, (210, 180, 255), [(16, 6), (19, 14), (16, 25), (13, 14)])
    SK.save("Entities", "Singing_Remnant", SK.outlined(s))
    # the Quiet Draught: the Healing Draught, grey-blue
    src = SK.load("Entities", "Healing_Draught")
    s = src.copy()
    w, h = s.get_size()
    for y in range(h):
        for x in range(w):
            r, g, b, a = s.get_at((x, y))
            if a and r > g + 30 and r > b:                    # (the pink of it)
                lum = (r + g + b) // 3
                s.set_at((x, y), (max(0, lum - 30), min(255, lum + 5), min(255, lum + 45), a))
    SK.save("Entities", "Quiet_Draught", s)
    # the Wardens' Lantern
    s = SK.surface()
    p.draw.arc(s, (90, 90, 100), (11, 2, 10, 10), 0, math.pi, 2)
    p.draw.rect(s, (70, 70, 84), (9, 8, 14, 3))
    p.draw.rect(s, (190, 150, 250), (10, 11, 12, 13))
    p.draw.rect(s, (240, 225, 255), (14, 13, 4, 9))
    p.draw.line(s, (70, 70, 84), (10, 11), (10, 23))
    p.draw.line(s, (70, 70, 84), (21, 11), (21, 23))
    p.draw.rect(s, (70, 70, 84), (9, 24, 14, 3))
    SK.save("Entities", "Wardens_Lantern", SK.outlined(s))
    # Ysolde: the ghost's own picture and frames, under her own name (so the conversation says Ysolde)
    SK.copy_walk("Ghost_Warden", "Ysolde")
    SK.copy_sprite("Entities", "Ghost_Warden", "Ysolde")
    # the cairn
    s = SK.surface()
    for (x, y, rw, rh, c) in ((7, 22, 18, 8, (110, 106, 112)), (9, 16, 14, 7, (128, 124, 128)), (11, 11, 10, 6, (100, 98, 106)),
                              (13, 7, 6, 5, (120, 116, 122))):
        p.draw.ellipse(s, c, (x, y, rw, rh))
    p.draw.polygon(s, (190, 150, 250), [(16, 2), (18, 7), (14, 7)])
    SK.save("Tiles", "Cairn001", SK.outlined(s))
    SK.minimap_colour("Cairn001", (112, 108, 116))


# ================================================================== sounds (old-world: nothing above C6)
def sounds():
    N = SS.NOTE
    SK.wav("Chime_Water", SS.room(BS.mix((SS.bell(N["D3"] * 2, 1.6, 2.2), 0.6),
                                         (BS.shaped(BS.tone(N["D3"], BS.n(1.4), glide=-0.08), 0.004, 5), 0.5)), 0.4, 0.6))
    SK.wav("Chime_Bone", SS.room(BS.mix((SS.knock(150, 0.35, 3, 0.3), 0.8), (BS.delay(SS.knock(140, 0.3, 4, 0.3), 0.16), 0.5),
                                        (BS.delay(SS.knock(130, 0.25, 5, 0.3), 0.32), 0.3)), 0.35, 0.5))
    SK.wav("Chime_Flame", SS.room(BS.mix((SS.bell(N["A3"], 2.0, 2.6), 0.7), (BS.crackle(7, 1.2, 0.015), 0.25)), 0.3, 0.6))
    SK.wav("Chime_Glass", SS.room(SS.bell(784.0, 2.4, 1.6), 0.45, 0.8))
    SK.wav("Shard_Voice", SS.room(BS.mix((SS.breath(11, 2.2, 0.05, 0.5), 0.6),
                                         (BS.shaped(BS.tone(N["G3"] / 2, BS.n(2.2), glide=0.06), 0.6, 1.4), 0.4),
                                         (BS.shaped(BS.tone(N["D3"], BS.n(2.2), glide=-0.04), 0.8, 1.6), 0.25)), 0.4, 0.8))
    SK.wav("Cutting_Vision", SS.room(BS.mix((SS.breath(21, 3.0, 0.04, 0.3), 0.5),
                                            (BS.delay(SS.bell(N["D3"], 2.2, 1.8), 1.0), 0.7),
                                            (BS.shaped(BS.tone(N["G3"] / 2, BS.n(3.0)), 0.3, 1.0), 0.35)), 0.4, 0.9))
    SK.wav("Ysolde_Rest", SS.room(SS.harp_run([N["D3"] * 2, N["A3"], N["F3"] * 2, N["A3"] * 2, N["D3"] * 4], 0.32, 2.6),
                                  0.4, 0.9))


def main():
    pictures()
    sounds()
    data()
    lv = Level()
    reid()
    place_things(lv)
    hx, hy = hatch_and_room(lv)
    lv.save()
    dim_room()
    scripts(hx, hy)
    print("The Glass Wardens: done")


if __name__ == "__main__":
    main()
