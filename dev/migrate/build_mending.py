"""The Mending (dev\\Roadmap-6.md groups 10-12): its places, its five quests and the world round it. Its people and
things are drawn by build_mending_art.py (run that first). It takes over the Ashen Shrine scripts and the Warden's
(build_heir_mainland.py), and Cael's (build_middle_quests.py: story_kit.TAKES_OVER); Amos's and Ashford's sheriff's
were build_estforlan.py's, never run again.

Places:
  * The hall under Shardglass Field (23,7,-1, made once): a slab of glass in the field's east end (two lookouts by it),
    the entry, the sermon hall, the Font, the sanctum behind an iron gate (a Lock: open to those who tithed, or picked)
    with the great Shard, a dormitory.
  * Their house in Ashford (13,-1,0): Sister Linnet, the house's Shard, Annis, a washing line behind it with a robe on
    it. Tam the cooper in the yard over the way.
  * Wardhaven: two Sisters in the chapel once the dragon's dead; a stair under the chapel floor to the Eldest's
    sanctum (17,1,-1, made once) once The Eldest of the Mending is begun.
  * The Ashwold: the three shrines burn blue for whoever's done The Ember Ring; the Hand's camp (25,9,0), where
    strangers in grey pay it, with a ring of triggers round it for listening in.

Attributes: ColdFireQuest (0-4), ColdShrines (to 3), StrangerQuest (0-4), StrangerEnd (1 home, 2 left), AnnisHome,
GreyQuest (0-5), GreyEnd (1 told the guards, 2 kept their secret), MendingShut, RobeTaken, TitheQuest (0-2), TitheOpen,
TitheWay (1 tithed, 2 picked, 3 fought), EldestQuest (0-3), EldestEnd (1 broke it, 2 kept a splinter), MendingGift.
And their helpers: ColdShrine1-3 (each shrine seen), ColdCampNear (told to come quietly), AnnisAway (she's left the
house: home, or the hall), EldestMet (he's greeted you), WhisperAt (when Mary's Whisper last gave Shards).

Safe to run again.

  python -I "dev\\migrate\\build_mending.py"     (then validate.py, export_web_assets.py, build_minimaps.py)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_isle import Map, obj_line            # noqa: E402
import story_kit as K                           # noqa: E402

MAKER = "build_mending.py"
FIELD, HALL = "23,7,0", "23,7,-1"
ASHFORD = "13,-1,0"
CHAPEL, UNDERCROFT = "17,1,0", "17,1,-1"
CAMP = "25,9,0"
SHRINES = {1: ("25,4,0", 9, 10), 2: ("26,9,0", 14, 8), 3: ("25,8,0", 18, 17)}
SLAB = (21, 11)                     # (the way down, on the field and the hall's ladder under it)
STAIR = (8, 16)                     # (in Wardhaven's chapel, and the undercroft's ladder under it)
GATE = (15, 4)                      # (the sanctum's iron gate in the hall)
CAMP_AT = (13, 12)                  # (the Hand's fire)


def px(tx, ty, npc=True):
    """A tile's top-left in pixels, as Add.Entity and Teleport take it (an NPC stands 8 px up)."""
    return "%d,%d" % ((tx - 1) * 32, (ty - 1) * 32 - (8 if npc else 0))


def npc(kind, x, y, extra):
    return obj_line("NPC", kind, x, y, extra, dy=-8)


def thing(kind, x, y, extra):
    return obj_line("StaticObject", kind, x, y, extra)


# ================================================================== places
def rect(m, x1, y1, x2, y2, tile="Flagstone001"):
    for y in range(y1, y2 + 1):
        for x in range(x1, x2 + 1):
            m.put(x, y, tile, {})


def hall_tiles():
    """The hall's rock, rooms and furniture: drawn only when the map's new (after that it's the editor's)."""
    m = Map(HALL, new=True)
    rect(m, 1, 1, 25, 21, "Cave_Wall001")
    rect(m, 18, 9, 23, 13)                              # the entry, the ladder up in the middle
    rect(m, 15, 11, 17, 11)                             # to the sermon hall
    rect(m, 4, 8, 14, 17)                               # the sermon hall
    rect(m, 21, 7, 21, 8)                               # up to the Font
    rect(m, 18, 2, 23, 6)                               # the Font's room
    rect(m, 13, 4, 17, 4)                               # to the sanctum, through the gate
    rect(m, 5, 2, 12, 5)                                # the sanctum
    rect(m, 21, 14, 21, 14)                             # down to the dormitory
    rect(m, 18, 15, 23, 19)                             # the dormitory
    m.set(*SLAB, decor="Ladder001")
    m.set(9, 8, decor="Cult_Shrine_Cold001")            # (the altar, its fire blue)
    for x in (7, 11):
        m.set(x, 8, decor="Candles001")
    for y in (11, 13, 15):                              # the benches, an aisle down the middle
        for x in list(range(5, 9)) + list(range(10, 14)):
            m.set(x, y, decor="Bench001")
    m.set(*GATE, decor="Iron_Gate001")
    for x in (6, 11):
        m.set(x, 2, decor="Candles001")
    for x in (18, 20, 22):
        m.set(x, 15, decor="Bed001")
    m.set(23, 19, decor="Candles001")
    m.save()
    print("%s: the hall drawn" % HALL)


def undercroft_tiles():
    m = Map(UNDERCROFT, new=True)
    rect(m, 1, 1, 25, 21, "Cave_Wall001")
    rect(m, 6, 14, 10, 18)                              # the foot of the stair
    rect(m, 8, 12, 8, 13)
    rect(m, 5, 3, 21, 11)                               # the Eldest's sanctum
    m.set(*STAIR, decor="Ladder001")
    for x in (6, 9, 17, 20):
        m.set(x, 3, decor="Candles001")
    m.set(13, 11, decor="Cult_Shrine_Cold001")
    m.save()
    print("%s: the undercroft drawn" % UNDERCROFT)


def camp_tiles(m):
    """The Hand's camp on the Ashwold: two tents, a fire, crates (drawn once: a tent already there means it's done)."""
    cx, cy = CAMP_AT
    if m.decor(cx - 2, cy - 2) == "Tent001":
        return False
    for y in range(cy - 3, cy + 3):
        for x in range(cx - 4, cx + 5):
            m.set(x, y, tile="Ash001", decor="")
    m.set(cx - 2, cy - 2, decor="Tent001")
    m.set(cx + 2, cy - 2, decor="Tent001")
    m.set(cx, cy, decor="Campfire001")
    m.set(cx + 3, cy + 1, decor="Crate001")
    m.set(cx - 3, cy + 1, decor="Crate001")
    return True


def house_tiles(m):
    """The Mending's house in Ashford: a quiet brick house off the road, a path round to its door, a yard behind."""
    if m.tile(7, 17) != "Grass001":
        return False
    K.building(m, 4, 12, 11, 17, door=7, wall="Brick001", roof="Slate")
    for y in range(7, 19):                              # the path: down from the road, round to the door
        m.set(3, y, tile="Dirt001", decor="")
    for x in range(4, 8):
        m.set(x, 18, tile="Dirt001", decor="")
    m.set(6, 13, decor="Table001")
    m.set(5, 16, decor="Candles001")
    m.set(10, 13, decor="Bed001")
    m.set(10, 16, decor="Crate001")
    for x in (10, 11):                                  # (Tam's barrels in the yard over the way)
        m.set(x, 9, decor="Barrel001")
    return True


PLACES = {   # map: [(Id, the line)]
    FIELD: [
        ("Mending_Slab", thing("Glass_Slab", SLAB[0], SLAB[1], "Id=Mending_Slab")),
        ("Mending_Lookout_1", npc("Mending_Acolyte", 20, 12, "Attitude=Bad Stand=1 Face=W Id=Mending_Lookout_1")),
        ("Mending_Lookout_2", npc("Mending_Acolyte", 19, 10, "Attitude=Bad Zone=18,9,21,12 Id=Mending_Lookout_2")),
    ],
    HALL: [
        ("Hall_Door_1", npc("Mending_Acolyte", 19, 10, "Attitude=Bad Stand=1 Face=E Id=Hall_Door_1")),
        ("Hall_Door_2", npc("Mending_Acolyte", 23, 12, "Attitude=Bad Stand=1 Face=W Id=Hall_Door_2")),
        ("Hall_Preacher", npc("Mending_Cantor", 9, 9, "Attitude=Bad Stand=1 Face=S Id=Hall_Preacher "
                                                     "Name=Cantor_Ivo")),
        ("Hall_Sister_1", npc("Mending_Sister", 6, 12, "Attitude=Good Stand=1 Face=N Id=Hall_Sister_1")),
        ("Hall_Sister_2", npc("Mending_Sister", 12, 14, "Attitude=Good Stand=1 Face=N Id=Hall_Sister_2 "
                                                       "Gone.After=HeartChoice:3")),      # (the Seam unmade: home)
        ("Hall_Sister_3", npc("Mending_Sister", 7, 16, "Attitude=Good Stand=1 Face=N Id=Hall_Sister_3 "
                                                      "Gone.After=HeartChoice:3")),
        ("Hall_Acolyte_1", npc("Mending_Acolyte", 5, 9, "Attitude=Bad Zone=4,8,14,17 Id=Hall_Acolyte_1")),
        ("Hall_Acolyte_2", npc("Mending_Acolyte", 13, 17, "Attitude=Bad Zone=4,8,14,17 Id=Hall_Acolyte_2")),
        ("Hall_Font", thing("Shard_Font", 21, 4, "Id=Hall_Font")),
        ("Font_Keeper", npc("Glassbound", 19, 5, "Attitude=Bad Zone=18,2,23,6 Id=Font_Keeper Name=Font_Keeper")),
        ("Hall_Cantor", npc("Mending_Cantor", 22, 3, "Attitude=Bad Stand=1 Face=S Id=Hall_Cantor")),
        ("Hall_Great_Shard", thing("Great_Shard", 8, 2, "Id=Hall_Great_Shard Gone.After=EldestQuest:1")),
        ("Hall_Annis", npc("Old_Woman", 19, 17, "Attitude=Good Stand=1 Face=S Id=Hall_Annis Name=Annis "
                                               "Here.After=StrangerEnd:2 Gone.After=AnnisHome:1,EldestQuest:1")),
        ("Hall_Sleeper", npc("Mending_Sister", 22, 17, "Attitude=Good Zone=18,16,23,19 Id=Hall_Sleeper")),
    ],
    ASHFORD: [
        ("Sister_Linnet", npc("Mending_Sister", 9, 14, "Attitude=Good Stand=1 Face=S Id=Sister_Linnet "
                                                      "Name=Sister_Linnet Gone.After=MendingShut:1")),
        ("House_Shard", thing("Mending_House_Shard", 6, 13, "Id=House_Shard Gone.After=MendingShut:1")),
        ("House_Annis", npc("Old_Woman", 7, 14, "Attitude=Good Stand=1 Face=N Id=House_Annis Name=Annis "
                                                "Gone.After=AnnisAway:1")),
        ("Mending_Washing_Line", thing("Washing_Line", 7, 11, "Id=Mending_Washing_Line Gone.After=RobeTaken:1")),
        ("Mending_Washing_Bare", thing("Washing_Line_Bare", 7, 11, "Id=Mending_Washing_Bare "
                                                                   "Here.After=RobeTaken:1")),
        ("Tam_Cooper", npc("Villager", 9, 9, "Attitude=Good Stand=1 Face=E Id=Tam_Cooper Name=Tam")),
        ("Home_Annis", npc("Old_Woman", 9, 10, "Attitude=Good Stand=1 Face=N Id=Home_Annis Name=Annis_Home "
                                               "Here.After=AnnisHome:1")),
    ],
    CHAPEL: [
        ("Wardhaven_Undercroft_Stair", thing("Undercroft_Stair", STAIR[0], STAIR[1],
                                             "Id=Wardhaven_Undercroft_Stair Here.After=EldestQuest:1")),
        ("Chapel_Sister_1", npc("Mending_Sister", 5, 17, "Attitude=Good Stand=1 Face=N Id=Chapel_Sister_1 "
                                                        "Here.After=GalaithQuest:2 Gone.After=EldestQuest:2")),
        ("Chapel_Sister_2", npc("Mending_Sister", 8, 18, "Attitude=Good Stand=1 Face=N Id=Chapel_Sister_2 "
                                                        "Here.After=GalaithQuest:2 Gone.After=EldestQuest:2")),
        ("Chapel_Penitent_1", npc("Mending_Sister", 5, 17, "Attitude=Good Stand=1 Face=N Id=Chapel_Penitent_1 "
                                                          "Name=Sister_Hesper Here.After=EldestEnd:1 "
                                                          "Gone.After=EldestEnd:2")),       # (the Shard broken: home)
        ("Chapel_Penitent_2", npc("Mending_Sister", 8, 18, "Attitude=Good Stand=1 Face=N Id=Chapel_Penitent_2 "
                                                          "Name=Brother_Odo Here.After=EldestEnd:1 "
                                                          "Gone.After=EldestEnd:2")),
    ],
    UNDERCROFT: [
        ("Eldest_Great_Shard", thing("Great_Shard", 12, 3, "Id=Eldest_Great_Shard Here.After=EldestQuest:1 "
                                                           "Gone.After=EldestEnd:1")),
        ("Undercroft_Annis", npc("Old_Woman", 16, 9, "Attitude=Good Stand=1 Face=N Id=Undercroft_Annis Name=Annis "
                                                    "Here.After=StrangerEnd:2,EldestQuest:1 Gone.After=AnnisHome:1")),
        ("The_Eldest", npc("Eldest_of_the_Mending", 13, 7, "Attitude=Bad Zone=6,4,20,10 Id=The_Eldest "
                                                           "Here.After=EldestQuest:1 Gone.After=EldestQuest:2")),
    ] + [("Eldest_Choir_%d" % i, npc("Mending_Cantor", x, y, "Attitude=Bad Stand=1 Face=%s Id=Eldest_Choir_%d "
                                     "Here.After=EldestQuest:1 Gone.After=EldestQuest:2" % (f, i)))
         for i, (x, y, f) in enumerate(((7, 5, "E"), (19, 5, "W"), (7, 9, "E"), (19, 9, "W")), 1)],
    CAMP: [
        ("Hand_Camp_Cultist_1", npc("Ashen_Cultist", 11, 13, "Attitude=Bad Zone=10,10,16,14 Id=Hand_Camp_Cultist_1 "
                                                            "Here.After=RingQuest:2")),
        ("Hand_Camp_Cultist_2", npc("Ashen_Cultist", 15, 11, "Attitude=Bad Stand=1 Face=W Id=Hand_Camp_Cultist_2 "
                                                            "Here.After=RingQuest:2")),
        ("Hand_Camp_Stranger_1", npc("Mending_Acolyte", 14, 13, "Attitude=Good Stand=1 Face=W "
                                     "Id=Hand_Camp_Stranger_1 Name=Stranger_in_Grey "
                                     "Here.After=ColdFireQuest:2 Gone.After=ColdFireQuest:3")),
        ("Hand_Camp_Stranger_2", npc("Mending_Sister", 14, 12, "Attitude=Good Stand=1 Face=W "
                                     "Id=Hand_Camp_Stranger_2 Name=Stranger_in_Grey "
                                     "Here.After=ColdFireQuest:2 Gone.After=ColdFireQuest:3")),
    ],
}
for _k, (_m, _x, _y) in SHRINES.items():
    PLACES.setdefault(_m, []).append(("Cold_Shrine_%d" % _k, thing("Cold_Shrine", _x, _y,
                                                                    "Id=Cold_Shrine_%d Here.After=RingQuest:2" % _k)))
PLACE_IDS = {HALL: [("Mending_Hall", 21, 12), ("Mending_Sermon", 9, 14), ("Mending_Font", 21, 5),
                    ("Mending_Sanctum", 9, 4)],
             FIELD: [("Mending_Field", SLAB[0], SLAB[1] + 1)],
             ASHFORD: [("Mending_House", 7, 18), ("Tam_Yard", 9, 10)],
             UNDERCROFT: [("Eldest_Sanctum", 13, 8)],
             CHAPEL: [("Wardhaven_Undercroft", STAIR[0], STAIR[1] + 1)],
             CAMP: [("Hand_Camp", CAMP_AT[0], CAMP_AT[1] - 3)]}
OLD = {FIELD: [("Id", "Mending_Slab")], ASHFORD: [("Id=", "Mending_House_Shard")]}    # (renamed: the lines to go)
TRIGGERS = {HALL: [("Mending Sermon", 14, 11), ("Mending Sanctum", 13, 4)], UNDERCROFT: [("Eldest Sanctum", 8, 13)]}
LOCKS = {HALL: [(GATE[0], GATE[1], "$Attr.TitheOpen>=1",
                 "An iron gate, locked. Past it, a cold blue light, and something humming.", "Pick=12")]}


def camp_ring():
    """The tiles round the Hand's camp where you're near enough to hear (Trigger Hand Camp)."""
    cx, cy = CAMP_AT
    return [(x, y) for y in range(cy - 4, cy + 4) for x in range(cx - 4, cx + 5)
            if x in (cx - 4, cx + 4) or y in (cy - 4, cy + 3)]


def place():
    if not K.map_exists(HALL):
        hall_tiles()
    if not K.map_exists(UNDERCROFT):
        undercroft_tiles()
    for name in sorted(set(PLACES) | set(PLACE_IDS) | set(LOCKS) | set(TRIGGERS)):
        m = Map(name)
        before = (list(m.ents), [list(r) for r in m.rows])
        if name == CAMP:
            camp_tiles(m)
            K.ents_without(m, lambda f: f[0] == "Trigger" and f[1] == "Hand Camp")
            m.ents += ["Trigger\tHand Camp\t%d\t%d" % xy for xy in camp_ring()]
        if name == ASHFORD:
            house_tiles(m)
        for kind, old in OLD.get(name, ()):
            if kind == "Id":
                K.ents_without(m, lambda f: f[0] == "Id" and f[1:2] == [old])
            else:
                K.ents_without(m, lambda f: ("Id=%s" % old) in f[-1].split())
        for pid, line in PLACES.get(name, ()):
            K.ents_without(m, lambda f: ("Id=%s" % pid) in f[-1].split())
            m.ents.append(line)
        for pid, x, y in PLACE_IDS.get(name, ()):
            K.place_id(m, pid, x, y)
        for trig, x, y in TRIGGERS.get(name, ()):
            K.ents_without(m, lambda f: f[0] == "Trigger" and f[1] == trig)
            m.ents.append("Trigger	%s	%d	%d" % (trig, x, y))
        for x, y, cond, text, pick in LOCKS.get(name, ()):
            K.ents_without(m, lambda f: f[0] == "Lock" and f[1:3] == [str(x), str(y)])
            m.ents.append("\t".join(("Lock", str(x), str(y), cond, text, pick)))
        if (m.ents, m.rows) != before:
            m.save()
            print("%s: placed" % name)
    have = (K.ini.read("Darkness", "Maps", "", K.CONFIG) or "").split()
    more = [n for n in (HALL, UNDERCROFT) if n not in have]
    if more:
        K.ini.write("Darkness", "Maps", " ".join(have + more), K.CONFIG)
    K.place_label("Places", "The Hall Under the Glass", "%s %d %d [if $Attr.GreyQuest>=3]" % (FIELD, SLAB[0], SLAB[1]))


# ================================================================== the ways down
def w(name, rows):
    K.write_script(name, rows, MAKER)


def climbs():
    far = [("@far",), ("Display.Message", "DarkRed", "You are too far away!", "Denied"), ("End",)]
    w("Climb Down Mending_Slab", [
        (">Distance.From.Clicked.Entity", "48", "@far"),
        ("Play.Sound", "Ladder"),
        ("Wait", "0.4"),
        ("Teleport", px(*SLAB), HALL),
        ("Display.Message", "Cyan", "The slab tips on a pin, and there are steps under it, cut in the rock. Down "
                                    "below, people are singing.", "-"),
        ("End",)] + far)
    w("Climb Down Wardhaven_Undercroft_Stair", [
        (">Distance.From.Clicked.Entity", "48", "@far"),
        ("Play.Sound", "Ladder"),
        ("Wait", "0.4"),
        ("Teleport", px(*STAIR), UNDERCROFT),
        ("Display.Message", "Cyan", "The steps go down a long way, under the chapel and under the town. It gets "
                                    "colder all the way.", "-"),
        ("End",)] + far)


# ================================================================== the quests' data
SHERIFF = "12,-3,0 10 18"           # (Flo, Ashford's sheriff, at the jail up the road)
ROBED = "$Equipped.Body=Mending_Robe"

QUESTS = [
    ("Cold Fire", [
        "Giver=Warden", "Attribute=ColdFireQuest",
        "Stage0=The Warden in Emberwatch has had word from the Ashwold.",
        "Stage1=The Warden says the Ashen Hand's burnt shrines on the Ashwold are lit again, and the fire's blue. "
        "There are three of them. Go and see.",
        "Stage2=All three shrines burn cold and blue, and the Hand never lit a fire like that. Footprints lead from "
        "them to the Hand's camp on the Ashwold. Get near enough to hear what's said there, without being seen.",
        "Stage3=Strangers in grey are paying the Hand in Shards, to push them through the wall \"for the one beyond "
        "the wall\". Tell the Warden.",
        "Done=4", "Marker0=Emberwatch_Square",
        "Marker1=" + ";".join("%s %d %d" % v for _, v in sorted(SHRINES.items())),
        "Marker2=Hand_Camp", "Marker3=Emberwatch_Square", "Type=Side", "Requires.Level=12",
        "Requires.Quests=The Ember Ring", "Reward.Shards=12", "Reward.XP=Stealth 3",
        "Rumour=A shepherd on the Ashwold swears the Hand's old shrines are lit again, and the fire's the wrong "
        "colour."]),
    ("The Kind Stranger", [
        "Giver=Villager", "Attribute=StrangerQuest",
        "Stage0=Tam, the cooper in Ashford, is worried about his mother.",
        "Stage1=Tam's mother Annis goes every day to a quiet house behind Rufus's yard in Ashford, where she says "
        "her late husband talks to her. Go and see her.",
        "Stage2=Annis won't hear a word against the Shard from you. Cael, the penitent at the Cinder Chapel on the "
        "Ashwold, was fooled by strangers in grey once: he might find the words.",
        "Stage3=Cael wrote a few lines for Annis. Take them to her, at the quiet house in Ashford.",
        "Done=4", "Marker0=Tam_Yard", "Marker1=Mending_House", "Marker2=Cinder_Chapel", "Marker3=Mending_House",
        "Type=Side", "Requires.Level=13", "Requires.Quests=Cold Fire", "Reward.Shards=10",
        "Ending=StrangerEnd",
        "Ending1=You read Annis what Cael wrote, and walked her home to Tam.",
        "Ending2=You left Annis with her Shard. She's gone to the Mending's hall.",
        "Ending3=The watch brought Annis home when they shut the Mending's house.",
        "Reward.Standing1=Ashford 15",
        "Rumour=Tam the cooper's been asking all over Ashford after his mother. She's taken up with them in grey."]),
    ("In Grey", [
        "Giver=Mending_Sister", "Attribute=GreyQuest",
        "Stage0=Sister Linnet of the Mending keeps a quiet house in Ashford.",
        "Stage1=Sister Linnet won't tell an outsider where the Mending gathers. In one of their grey robes, she might "
        "take you for one of them.",
        "Stage2=Sister Linnet took you for one of the Mending. They gather under Shardglass Field, through a slab of "
        "glass at its east end. Keep the robe on, and they'll take you for one of their own.",
        "Stage3=Cantor Ivo of the Mending says the great Shard waits in the sanctum, past the Font, for the "
        "faithful. Listen to it.",
        "Stage4=The great Shard spoke to you in your mother's voice, and now you know what the Mending wants: the "
        "King's Seam opened, under Galaith. Tell Sheriff Flo in Ashford, or tell Sister Linnet you'll keep their "
        "secret.",
        "Done=5", "Marker0=Mending_House", "Marker1=Mending_House", "Marker2=Mending_Field",
        "Marker3=Mending_Sanctum", "Marker4=%s;Mending_House" % SHERIFF, "Type=Side", "Requires.Level=15",
        "Requires.Quests=The Shardgate;Cold Fire", "Reward.Shards=15",
        "Ending=GreyEnd",
        "Ending1=You told Sheriff Flo. The Mending's house in Ashford is shut, and Galaith's watch knows of the hall.",
        "Ending2=You kept the Mending's secret. Their house is open to you, in grey.",
        "Reward.Standing1=Ashford 15 Galaith 15"]),
    ("The Tithe", [
        "Giver=Mending_Cantor", "Attribute=TitheQuest", "Stage0=",
        "Stage1=An iron gate shuts the Mending's sanctum, and it opens to those who pour their Shards into the "
        "Font. A lock can be picked, too, and the Font's keeper is a big one.",
        "Done=2", "Marker0=Mending_Sermon", "Marker1=Mending_Font", "Type=Side",   # (no Stage0: never shown early)
        "Requires.Level=15", "Requires.Quests=The Shardgate;Cold Fire",         # (In Grey's own: the sermon starts it)
        "Reward.XP=Channeling 2",
        "Ending=TitheWay",
        "Ending1=You poured your Shards into the Font, and the gate opened for one of the faithful.",
        "Ending2=You picked the sanctum's lock.",
        "Ending3=You broke the Font's keeper, and went through by force."]),
    ("The Eldest of the Mending", [
        "Giver=Villager", "Attribute=EldestQuest",
        "Stage0=Amos, the priest of Wardhaven, doesn't sleep well since the Sisters came.",
        "Stage1=Amos says the two Sisters in grey in his chapel go down under its floor at night, where there's a "
        "stair he never knew of, and singing. Go down and see.",
        "Stage2=The Eldest of the Mending is dead. The great Shard is still singing.",
        "Done=3", "Marker0=Wardhaven_Church", "Marker1=Wardhaven_Undercroft", "Marker2=Eldest_Sanctum",
        "Type=Side", "Requires.Level=20", "Requires.Quests=The Dragon of Galaith;In Grey", "Reward.Shards=30",
        "Reward.XP=Channeling 4 Defence 4",
        "Ending=EldestEnd",
        "Ending1=You broke the great Shard. The Mending's scattered, and some of them have gone home.",
        "Ending2=You kept a splinter of the great Shard: Mary's Whisper.",
        "Rumour=Old Amos in Wardhaven says there's singing under his chapel at night."]),
]

SHOP = ["Type=Shop", "Buy.Rate=1.2", "Sell.Rate=0.5", "Specific=0", "Item1=Ward_Shard,2", "Item2=Shard_Ward_Scroll,1",
        "Item3=Silence_Scroll,1", "Item4=Healing_Draught,4", "Item5=Mending_Robe,1"]
POCKET = ["; The Mending's Sisters (build_mending.py): a spare robe, now and then", "Level=10", "Gold=4-10",
          "Loot=Mending_Robe,1,25 Shard,1-2,30"]
NUMBERS = ["; The Mending (build_mending.py). Tithe: Shards poured into the Font to open its sanctum; Gift: what one",
           "; of them gives you on the road; Whisper: Mary's Whisper's Shards, once every Whisper.Hours (real) hours.",
           "Tithe=40", "Gift=5", "Whisper=3", "Whisper.Hours=20"]


WAYFARER = ["; One of the Mending on the road (build_mending.py): a few Shards for nothing, remembered (MendingGift)",
            "NPC=Mending_Wayfarer", "Attitude=Good", "Weight=2", "Max=1", "Minutes=6", "Min.Level=12", "Where=Wild",
            "Requires=$Attr.ColdFireQuest>=3 and $Attr.HeartChoice<3 and $Attr.EldestEnd<>1",
            "Say=Cold out, friend. Come and get warm.|Peace on your road, friend.|You look tired, friend. Sit a "
            "while.",
            "Goodbye=Go gently, friend. We'll see you again.|Peace on your road."]
RAID = ["; The Mending, come for the King's Seam (build_mending.py): after The True Heir, till the Seam's unmade",
        "Name=The Mending in the mine", "Map=-7,11,-1", "Centre=Galaith_Mine_Floor",
        "Waves=Mending_Acolyte*2;Mending_Acolyte*3,Mending_Cantor*1;Glassbound*1,Mending_Acolyte*2,Mending_Cantor*1",
        "Gap=12", "Minutes=8", "Random.Every=150", "Random.Players=1",
        "Requires=$Attr.KingQuest>=1 and $Attr.HeartChoice<3", "Gold.Per.Kill=5", "Reward.Gold=80",
        "Reward.Items=Super_Potion 1", "Reward.XP=1",
        "Start.Message=Singing, down the mine's tunnels: folk in grey robes, coming for the King's Seam. Hold the "
        "mine floor!",
        "Win.Message=The last of them goes down still singing. The Seam is the Crown's again.",
        "Lose.Message=They kneel at the Seam a while, singing, and go back the way they came."]


def data():
    K.place_label("Places", "The Hall Under the Glass", "%s %d %d [if $Attr.GreyQuest>=3]" % (FIELD, SLAB[0], SLAB[1]))
    K.set_section(os.path.join(K.DATA, "Encounters.ini"), "Mending_Wayfarer", WAYFARER)
    K.set_section(os.path.join(K.DATA, "Waves.ini"), "Mending_Raid", RAID)
    after = "Under the Tide"
    for name, lines in QUESTS:
        K.set_section(K.QUESTS, name, lines, after=after)
        after = name
    K.set_section(K.RACKS, "SHOP-Mending", SHOP, after="SHOP-Smugglers")
    K.set_section(os.path.join(K.DATA, "Thieving.ini"), "Pickpocket.Mending", POCKET)
    K.set_section(os.path.join(K.DATA, "Shards.ini"), "Mending", NUMBERS, after="Forms")


# ================================================================== the scripts
def V(n):
    return "Variable.%d$" % n


def get(attr, n):
    return ("Get.Value", "ATTRIBUTE", attr, V(n))


def msg(text, colour="Yellow", sound=""):
    return ("Display.Message", colour, text) + ((sound,) if sound else ())


def cyan(text):
    return msg(text, "Cyan", "-")


FAR = [("@far",), msg("You are too far away!", "DarkRed", "Denied"), ("End",)]


def warden():
    """Talk to Warden (build_heir_mainland's, the Ember Ring kept as it was): and Cold Fire."""
    say = lambda text, *a: K.say("Warden", text, *a)               # noqa: E731
    return [
        get("RingQuest", 1),
        (">Conditional", "$Variable.1=0 and $Attr.BertQuest>=1", "@ring1"),
        (">Quest.Can.Start", "RingQuest", "@young"),
        say("The Ember Ring? The Ashen Priest wears it, and he's welcome to it, as far as I'm concerned.\\He holds "
            "the Cinder Fort, high in the Cinder Peaks, with the Ashen Hand: a cult that sings to the dragon, and "
            "sends it what it can. If Bert wants that ring, you'll have to take it off his finger yourself.",
            ("Then I will.", "@ring")),
        ("@ring",), ("Update.Attribute", "RingQuest", "=1"), msg("Quest started: The Ember Ring.", sound="Quest"),
        ("End",),
        ("@ring1",), (">Conditional", "$Variable.1=1", "@cold"),
        say("The Cinder Fort is up the road north, high in the peaks. Take water. Take armour.", ("I will.", "@end")),
        ("End",),
        ("@cold",), get("ColdFireQuest", 2),
        (">Conditional", "$Variable.1>=2 and $Variable.2=0", "@cold1"),
        (">Quest.Can.Start", "ColdFireQuest", "@usual"),
        say("You took the ring off the priest's finger, and the Hand's scattered. You'd think the Ashwold would be "
            "quiet now.\\Then a shepherd comes in and tells me the Hand's old shrines are burning again. Not red: "
            "blue. He held his hand in it, he says, and it was only cold.\\The Hand never lit a fire like that. Will "
            "you go and look?", ("I'll go and look.", "@coldgo"), ("Not now.", "@end")),
        ("@coldgo",), ("Update.Attribute", "ColdFireQuest", "=1"), msg("Quest started: Cold Fire.", sound="Quest"),
        ("End",),
        ("@cold1",), (">Conditional", "$Variable.2=1", "@cold2"),
        say("Three shrines, out on the Ashwold, where the Hand used to sing. Mind the ash.", ("I'm going.", "@end")),
        ("End",),
        ("@cold2",), (">Conditional", "$Variable.2=2", "@cold3"),
        say("Blue, all three? And tracks to the Hand's camp. Get close enough to hear what's said there. Quietly, "
            "mind: they'll not talk in front of you.", ("I'll go quietly.", "@end")),
        ("End",),
        ("@cold3",), (">Conditional", "$Variable.2=3", "@usual"),
        say("Strangers in grey, paying the Hand to feed the dragon? \"Mend it\"... I don't like that word.\\There's "
            "been folk in grey on the roads this year: kind folk, soup and blankets. A carter told me they keep a "
            "quiet house in Ashford. Here, for your trouble, and keep your eyes open.", ("Thank you.", "@colddone")),
        ("@colddone",), ("Update.Attribute", "ColdFireQuest", "=4"), msg("Quest complete: Cold Fire!"), ("End",),
        ("@usual",),
        say("Emberwatch: the last fort before the Cinderlands. Smoke on the wind, and ash on the bread.",
            ("Goodbye.", "@end")),
        ("End",),
        ("@young",),
        say("You? Into the Cinder Fort? The Ashen Hand would have you singing to the dragon by supper.\\Whatever "
            "Bert wants with that ring, it'll keep. Come back with a few more fights behind you.",
            ("I'll be back.", "@end")),
        ("@end",), ("End",),
    ]


def shrine(n):
    """Ashen Shrine N (a trigger before each, build_heir_mainland's): cold, then lit blue, then counted."""
    seen = "ColdShrine%d" % n
    return [
        get("RingQuest", 1), (">Conditional", "$Variable.1>=2", "@old"),
        get("ColdFireQuest", 2), (">Conditional", "$Variable.2=1", "@blue"),
        get(seen, 3), (">Conditional", "$Variable.3=0", "@blue"),
        ("Update.Attribute", seen, "=1"), ("Update.Attribute", "ColdShrines", "+1"),
        get("ColdShrines", 4), (">Conditional", "$Variable.4>=3", "@more"),
        ("Update.Attribute", "ColdFireQuest", "=2"),
        cyan("The last of the three, burning blue like the others. In the ash round it there are footprints, a lot "
             "of them, going off towards the Hand's camp."),
        ("End",),
        ("@more",),
        cyan("The Hand's shrine is lit again, but the flames are blue, and when you hold your hand in them it's only "
             "cold. That's $Variable.4 of the three."),
        ("End",),
        ("@blue",), cyan("The Hand's shrine, lit again. The flames are blue, and give no warmth at all."), ("End",),
        ("@old",), cyan("A burnt shrine of the Ashen Hand, cold now."), ("End",),
    ]


def hand_camp():
    """Trigger Hand Camp (the ring round its fire): overheard, if you came quietly."""
    return [
        get("ColdFireQuest", 1), (">Conditional", "$Variable.1=2", "@end"),
        (">Conditional", "$Player.Stance=Sneaking", "@loud"),
        K.say("Player", "You keep low in the ash, close enough to smell the Hand's fire. By it, two strangers in grey "
                        "robes are counting Shards into a cultist's hands.\\\"Same as before,\" the woman says. \"Up "
                        "the pass, and through the wall. For the one beyond the wall.\"\\\"It eats them,\" the "
                        "cultist says. \"Every one. Why feed a dragon?\"\\\"Not feed it,\" she says gently. \"Mend "
                        "it. Everything that's cut wants to be whole. You'll see.\"", ("Slip away.", "@heard")),
        ("@heard",), ("Update.Attribute", "ColdFireQuest", "=3"),
        msg("You've heard enough. The Warden in Emberwatch will want to know."), ("End",),
        ("@loud",), get("ColdCampNear", 2), (">Conditional", "$Variable.2=0", "@end"),
        ("Update.Attribute", "ColdCampNear", "=1"),
        msg("Voices by the Hand's fire, too low to make out. You'd hear more if you came quietly.", "DarkRed",
            "Denied"),
        ("@end",), ("End",),
    ]


def tam():
    say = lambda text, *a: K.say("Villager", text, *a)              # noqa: E731
    return [
        get("StrangerQuest", 1), (">Conditional", "$Variable.1=0", "@asked"),
        (">Conditional", "$Attr.AnnisAway=0", "@home"),
        (">Quest.Can.Start", "StrangerQuest", "@plain"),
        say("Tam, the cooper. You'll not have seen my mother? Annis: little, a green shawl, and a stick she won't "
            "use.\\Since Father died she goes to that quiet house behind Rufus's yard, every day now, and she comes "
            "back smiling. She says he talks to her there. Out of a stone.\\He's two winters in the ground. Would you "
            "go and see her? She won't hear it from me.", ("I'll talk to her.", "@start"), ("Not now.", "@end")),
        ("@start",), ("Update.Attribute", "StrangerQuest", "=1"),
        msg("Quest started: The Kind Stranger.", sound="Quest"), ("End",),
        ("@asked",), (">Conditional", "$Variable.1<4", "@done"),
        say("She's at the quiet house, round the back of Rufus's yard. Be gentle with her.", ("I will.", "@end")),
        ("End",),
        ("@done",), get("StrangerEnd", 2), (">Conditional", "$Variable.2=2", "@home"),
        say("She's gone with them. Out to wherever it is they go. She sent word she's happy.\\I suppose that's "
            "something.", ("I'm sorry, Tam.", "@end")),
        ("End",),
        ("@home",),
        say("She's home. She sat in Father's chair last night and cried, and then she laughed, and then she ate a "
            "whole pie. Thank you.", ("Look after her.", "@end")),
        ("End",),
        ("@plain",), say("Tam, the cooper. Barrels, buckets, tubs: if it holds water, I made it.", ("Goodbye.", "@end")),
        ("@end",), ("End",),
    ]


def house_annis():
    say = lambda text, *a: K.say("Old_Woman", text, *a)             # noqa: E731
    return [
        get("StrangerQuest", 1), (">Conditional", "$Variable.1=1", "@two"),
        say("Annis looks up from the Shard on the table, and her face is shining.\\\"Have you come to hear him too? "
            "My Oswin. He's in the stone, love. He tells me he's not cold, and the roof wants mending, and I'm to "
            "eat properly.\"\\\"Tam sent you, did he? Tam doesn't understand. You can't tell me it isn't him. You "
            "didn't know him.\"", ("Then I'll find someone who can tell you.", "@next"), ("I'll leave you to him.", "@end")),
        ("@next",), ("Update.Attribute", "StrangerQuest", "=2"), ("End",),
        ("@two",), (">Conditional", "$Variable.1=2", "@three"),
        say("\"Hush now, love, he's talking.\"", ("Goodbye.", "@end")), ("End",),
        ("@three",), (">Conditional", "$Variable.1=3", "@plain"),
        say("\"Back again? Oswin says you're a good sort.\"", ("Cael, of the Cinder Chapel, wrote you this. Let me "
                                                                "read it to you.", "@read"),
            ("Leave her be. She's happy here.", "@leave")),
        ("@read",),
        say("You read it to her.\\\"I heard my mother in the fire, and she told me to feed it. It said what I wanted "
            "to hear, because that's all it can do. It doesn't know you. It only knows what you miss.\"\\Annis is "
            "quiet a long while. Then she turns the Shard over, face down.\\\"He never once said the roof wanted "
            "mending. He'd have done it himself.\" She takes your arm. \"Walk me home, love. Tam'll want his tea.\"",
            ("Come on, then.", "@walk")),
        ("@walk",), ("Take.Item", "Caels_Lines", "1"),            # (taken once it's read: closed, it's kept)
        ("Update.Attribute", "StrangerEnd", "=1"), ("Update.Attribute", "AnnisHome", "=1"),
        ("Update.Attribute", "AnnisAway", "=1"), ("Update.Attribute", "StrangerQuest", "=4"),
        msg("Quest complete: The Kind Stranger!"), ("End",),
        ("@leave",), ("Update.Attribute", "StrangerEnd", "=2"), ("Update.Attribute", "AnnisAway", "=1"),
        ("Update.Attribute", "StrangerQuest", "=4"), msg("Quest complete: The Kind Stranger. You left Annis with "
                                                         "her Shard."), ("End",),
        ("@plain",), say("Annis looks up from the Shard on the table, and smiles. \"Hush, love: my Oswin's talking.\"",
                         ("Goodbye.", "@end")),
        ("@end",), ("End",),
    ]


def annis_elsewhere(where):
    say = lambda text, *a: K.say("Old_Woman", text, *a)             # noqa: E731
    if where == "home":
        return [say("Annis is in her own chair by the door, a blanket on her knees.\\\"Oswin used to sit just there. "
                    "I don't hear him any more. I only miss him, and that's my own, at least.\"", ("Goodbye.", "@end")),
                ("@end",), ("End",)]
    if where == "hall":
        return [say("\"Oh, it's you! Isn't it lovely down here? Oswin's so much clearer. He says I'm to stay, and so "
                    "I shall.\"", ("Goodbye, Annis.", "@end")), ("@end",), ("End",)]
    return [(">Conditional", "$Attr.HeartChoice=3", "@soon"),
            say("\"It's gone quiet, love. He's gone quiet. I keep listening.\"", ("Come home, Annis.", "@end")),
            ("End",),
            ("@soon",), say("\"It won't be long now, love. Oswin says when it's all mended we'll be together.\"",
                            ("Goodbye, Annis.", "@end")),
            ("@end",), ("End",)]


def cael():
    """Talk to Cael (build_middle_quests's, the Brother in the Ash as it was): and a few lines for Annis."""
    say = lambda text, *a: K.say("Penitent", text, *a)              # noqa: E731
    return [
        get("StrangerQuest", 2), (">Conditional", "$Variable.2=2", "@cael"),
        say("Cael listens without looking up, turning a burnt bead over in his fingers.\\'An old woman, hearing her "
            "husband in a Shard. Yes. I heard my mother in the fire, once. Them in grey told me it was her.'\\He "
            "writes slowly on a scrap of paper, a few lines. 'Read her that. If she won't hear it, let her be. You "
            "can't drag a person out of a warm room.'", ("Thank you, Cael.", "@lines")),
        ("@lines",), ("Give.Item", "Caels_Lines", "1"), ("Update.Attribute", "StrangerQuest", "=3"), ("End",),
        ("@cael",), get("CaelQuest", 1), (">Conditional", "$Variable.1=0", "@one"),
        (">Quest.Can.Start", "CaelQuest", "@pray"),
        say("A man in a burnt grey robe kneels by the chapel wall, away from the others.\\'I fed it,' he says, not "
            "looking up. 'We all fed it. Shards through the barrier, a handful a week, singing. They said it would "
            "make the world warm again. It's only made it hungry.'\\'My sister keeps the watch at Ashfall Outpost. "
            "Oska. I can't go to her. Would you take her this?'", ("I'll take it.", "@take"), ("No.", "@end")),
        ("@take",), ("Give.Item", "Cael_Confession", "1"), ("Update.Attribute", "CaelQuest", "=1"),
        msg("Quest started: The Brother in the Ash.", sound="Quest"), ("End",),
        ("@one",), (">Conditional", "$Variable.1=1", "@two"),
        say("'Oska. At the outpost. Please.'", ("I'm going.", "@end")),
        ("@two",), say("'She's coming for me? ...Then I'd better be here when she does.'", ("Goodbye.", "@end")),
        ("@pray",), say("A man in a burnt grey robe kneels by the chapel wall, praying under his breath. He doesn't "
                        "look up.", ("...", "@end")),
        ("@end",), ("End",),
    ]


def linnet():
    say = lambda text, *a: K.say("Mending_Sister", text, *a)        # noqa: E731
    plain = ("Sister Linnet of the Mending. \"Come in out of the cold, friend. There's soup on, and the Shard on the "
             "table is good company: sit by it a while, and listen.\"")
    return [
        get("GreyQuest", 1), (">Conditional", "$Variable.1=0", "@going"),
        (">Quest.Can.Start", "GreyQuest", "@plain"),
        (">Conditional", ROBED, "@stranger"), ("Goto.Line", "@robed"),
        ("@stranger",),
        say(plain + "\\\"The others? Oh, they're at the gathering tonight. I mustn't say where, I'm sorry: it's only "
                    "for those of the Mending.\" She smiles at your coat. \"Grey suits everyone, you know.\"",
            ("Where's the gathering?", "@ask"), ("Goodbye.", "@end")),
        ("@ask",), say("\"Only for the Mending, friend.\" She's still smiling.", ("Goodbye.", "@one")),
        ("@one",), ("Update.Attribute", "GreyQuest", "=1"), msg("Quest started: In Grey.", sound="Quest"), ("End",),
        ("@going",), (">Conditional", "$Variable.1<3", "@later"), (">Conditional", ROBED, "@plain"),
        ("@robed",),
        say("\"Oh! I didn't see you come in, $Player.Brother. You'll be late: the Cantor's speaking tonight. Go on, "
            "down to the field. The glass at the east end, and mind the lookouts know you.\"", ("I'm going.", "@two")),
        ("@two",), ("Update.Attribute", "GreyQuest", "=2"), (">Conditional", "$Variable.1=0", "@end"),
        msg("Quest started: In Grey.", sound="Quest"), ("End",),
        ("@later",), (">Conditional", "$Variable.1=4", "@after"),
        say("Sister Linnet looks at you a long moment. \"You heard it, didn't you? The great Shard. I can see it on "
            "you.\"\\\"Whatever it said, it was true. It always is. You won't tell anyone about the field, will "
            "you? People don't understand.\"", ("I won't tell a soul.", "@keep"), ("Goodbye.", "@end")),
        ("@keep",), ("Update.Attribute", "GreyEnd", "=2"), ("Update.Attribute", "GreyQuest", "=5"),
        say("\"I knew it. Bless you, $Player.Brother. This house is yours as much as ours, and anything on the "
            "shelf is yours at a fair price, whenever you're in grey.\"", ("Thank you, Sister.", "@kept")),
        ("@kept",), msg("Quest complete: In Grey!"), ("End",),
        ("@after",), (">Conditional", ROBED, "@plain"),
        say("\"Anything you need, $Player.Brother?\"", ("Show me what you have.", "@shop"), ("Goodbye.", "@end")),
        ("@shop",), ("Display.Item.Rack", "GENERAL", "Mending_Sister", "SHOP-Mending", "@end"), ("End",),
        ("@plain",), say(plain, ("Goodbye.", "@end")),
        ("@end",), ("End",),
    ]


def sister():
    """Talk to Mending_Sister: any Sister of the Mending with no words of her own."""
    say = lambda text, *a: K.say("Mending_Sister", text, *a)        # noqa: E731
    return [
        (">Conditional", "$Attr.HeartChoice=3", "@hope"),
        say("\"It's gone quiet. All of them, all at once, the night the Seam broke. I keep listening.\" She wipes her "
            "eyes. \"I think I might go home.\"", ("Go home, Sister.", "@end")),
        ("End",),
        ("@hope",), (">Conditional", ROBED, "@out"), (">Random", "50", "@whole"),
        say("\"Welcome home, $Player.Brother. Have you heard it yet? Really heard it? It knew my name before I told "
            "it.\"", ("Goodbye.", "@end")),
        ("End",),
        ("@whole",), say("\"We'll all be whole soon. The first king cut it, and we'll mend it. Isn't that a lovely "
                         "thought?\"", ("Goodbye.", "@end")),
        ("End",),
        ("@out",), say("\"You look tired, friend. Have you ever sat with a Shard? Really listened? It's very "
                       "kind.\"", ("Goodbye.", "@end")),
        ("@end",), ("End",),
    ]


def sheriff():
    """Talk to Ashford_Sheriff_325 (build_estforlan's one line): and the Mending told on."""
    say = lambda text, *a: K.say("Sheriff", text, *a)               # noqa: E731
    return [
        get("GreyQuest", 1), (">Conditional", "$Variable.1=4", "@usual"),
        say("Flo looks up from her ledger. \"Something on your mind?\"",
            ("There's a hall under Shardglass Field. The Mending folk meet there, and they mean to open the King's "
             "Seam.", "@tell"), ("Nothing. Goodbye.", "@end")),
        ("@tell",),
        say("\"Them in grey? The kind ones, with the soup?\" She hears you out, and stops smiling.\\\"The King's "
            "Seam. Right. I'll send word to Galaith tonight, and I'll have their house here shut by morning. Anyone "
            "in there who wants to go home will be taken home.\"", ("Thank you, Sheriff.", "@told")),
        ("@told",), ("Update.Attribute", "GreyEnd", "=1"), ("Update.Attribute", "MendingShut", "=1"),
        (">Conditional", "$Attr.AnnisAway=0 or $Attr.StrangerEnd=2", "@annis"),
        ("Update.Attribute", "AnnisHome", "=1"), ("Update.Attribute", "AnnisAway", "=1"),
        get("StrangerQuest", 2), (">Conditional", "$Variable.2>=1 and $Variable.2<4", "@annis"),
        ("Update.Attribute", "StrangerEnd", "=3"), ("Update.Attribute", "StrangerQuest", "=4"),
        ("@annis",), ("Update.Attribute", "GreyQuest", "=5"), msg("Quest complete: In Grey!"), ("End",),
        ("@usual",),
        say("I'm the sheriff here. The cells are empty and I like them that way.", ("Goodbye.", "@end")),
        ("@end",), ("End",),
    ]


def sermon():
    """Trigger Mending Sermon (where the passage comes into the hall): Cantor Ivo, for those in grey."""
    say = lambda text, *a: K.say("Mending_Cantor", text, *a)        # noqa: E731
    return [
        get("GreyQuest", 1), (">Conditional", "$Variable.1=2", "@end"), (">Conditional", ROBED, "@end"),
        ("Play.Sound", "Mending_Chant"),
        (">Conditional", "$Attr.HeartChoice=3", "@hope"),
        say("Cantor Ivo stands by the cold altar, and the singing stops.\\\"I won't lie to you. The Seam's broken. "
            "The first cut's closed for good, and the rest of it will never come home.\"\\There's crying on the "
            "benches. \"But the great Shard still speaks, past the Font. Go and listen, those who've given to it, "
            "and tell me it isn't true.\"", ("Listen.", "@heard")),
        ("@hope",), (">Conditional", "$Attr.MendingGift>=1", "@sermon"),
        say("Cantor Ivo raises a hand by the cold altar, and the singing stops. \"And a new friend tonight! "
            "$Player.Name took a gift from one of us on the road, and said thank you. Welcome, $Player.Name.\"\\Heads "
            "turn on the benches, and everyone smiles at you.", ("Smile back.", "@sermon")),
        ("@sermon",),
        say("\"Sisters, brothers. You heard them too. A husband. A mother. A voice that said you were wanted. They "
            "were never lost, only cut up small, and scattered, and crying to be whole.\"\\\"The first king cut the "
            "world's magic to pieces, long ago, and he started under Galaith: the first cut, the King's Seam. Open "
            "it, and the rest will come home.\"\\\"Those who are ready to hear the great Shard: give to the Font, "
            "and the way is open.\"", ("Listen.", "@heard")),
        ("@heard",), ("Update.Attribute", "GreyQuest", "=3"),
        get("TitheQuest", 2), (">Conditional", "$Variable.2=0", "@end"),
        ("Update.Attribute", "TitheQuest", "=1"), msg("Quest started: The Tithe.", sound="Quest"),
        ("@end",), ("End",),
    ]


def font():
    return [
        (">Distance.From.Clicked.Entity", "48", "@far"),
        get("TitheOpen", 1), (">Conditional", "$Variable.1=0", "@open"),
        K.say("Player", "The Font's water is still and cold. Those who pour their Shards into it are let through to "
                        "the great Shard.", ("Pour in $Shards.Mending.Tithe Shards.", "@pay"), ("Not now.", "@end")),
        ("@pay",), (">Pay.Shards", "Mending.Tithe", "Tithing_at_the_Font", "@end"),
        ("Update.Attribute", "TitheOpen", "=1"), (">Conditional", "$Attr.TitheWay=0", "@paid"),
        ("Update.Attribute", "TitheWay", "=1"),
        ("@paid",), ("Play.Sound", "Absorb"),
        cyan("The Shards sink, glowing, and go out one by one. Past the Font, an iron gate clicks."), ("End",),
        ("@open",), cyan("The Font's water is still and cold, and full of Shards gone dark."),
        ("@end",), ("End",),
    ] + FAR


def font_keeper():
    """Kill Font_Keeper (the killer's own): the key to the sanctum's gate was in it."""
    return [
        get("TitheOpen", 1), (">Conditional", "$Variable.1=0", "@end"),
        ("Update.Attribute", "TitheOpen", "=1"), (">Conditional", "$Attr.TitheWay=0", "@key"),
        ("Update.Attribute", "TitheWay", "=3"),
        ("@key",), cyan("The Glassbound comes apart like a dropped jug. In the pieces there's a key of blue glass, "
                        "and it's for the sanctum's gate."),
        ("@end",), ("End",),
    ]


def sanctum():
    """Trigger Mending Sanctum (just inside its gate): the Tithe's done, however you came in."""
    return [
        get("TitheQuest", 1), (">Conditional", "$Variable.1=1", "@end"),
        (">Conditional", "$Attr.TitheWay=0", "@in"), ("Update.Attribute", "TitheWay", "=2"),
        ("@in",), ("Update.Attribute", "TitheQuest", "=2"), msg("Quest complete: The Tithe!"),
        ("@end",), ("End",),
    ]


def great_shard():
    """Listen Hall_Great_Shard: Mary's voice, for one in In Grey."""
    say = lambda text, *a: K.say("Great_Shard", text, *a)           # noqa: E731
    return [
        (">Distance.From.Clicked.Entity", "64", "@far"),
        ("Play.Sound", "Mending_Whisper"),
        get("GreyQuest", 1), (">Conditional", "$Variable.1=3", "@heard"),
        say("The hum of it fills your head, and then it isn't a hum. It's a woman's voice, and you know it.\\\"My "
            "beloved $Player.Son. Look at you. This is not what your life should have been like, and still you've "
            "come so far.\"\\\"I was wrong to run. Come home, love. Come and be whole with me, all of us together. "
            "It won't hurt.\"\\You know those words. They were in her letter, and the Shard is giving them back to "
            "you, out of order.", ("Step back.", "@back")),
        ("@back",), ("Update.Attribute", "GreyQuest", "=4"),
        msg("Now you know what the Mending wants. Sheriff Flo in Ashford should hear of it, or Sister Linnet would "
            "be glad of your silence."), ("End",),
        ("@heard",), (">Conditional", "$Attr.HeartChoice=3", "@hum"),
        cyan("It's quiet. Something in it is still listening, but it's got nothing left to say."), ("End",),
        ("@hum",), cyan("It hums, cold. For a moment you'd swear someone you love is about to say your name."),
        ("End",),
    ] + FAR


def house_shard():
    return [
        (">Distance.From.Clicked.Entity", "64", "@far"), ("Play.Sound", "Mending_Whisper"),
        cyan("It hums, warm as bread. Annis says she hears her Oswin in it. For a moment, you'd swear someone you "
             "miss is about to speak."), ("End",),
    ] + FAR


def amos():
    """Talk to Wardhaven_Priest_309 (build_estforlan's one line): and what goes on under his floor."""
    say = lambda text, *a: K.say("Villager", text, *a)              # noqa: E731
    return [
        get("EldestQuest", 1), (">Conditional", "$Variable.1=0", "@asked"),
        (">Conditional", "$Attr.GalaithQuest>=2", "@plain"),
        (">Quest.Can.Start", "EldestQuest", "@uneasy"),
        say("Amos keeps his voice down. \"Since the dragon died, folk have come back to Wardhaven, and I'm glad of "
            "every one. But those two Sisters in grey...\"\\\"They pray with the rest, kind as you like. And at night "
            "they go down under my chapel floor. There's a stair there I never knew of, and singing under it, and "
            "I've been priest here thirty years.\"\\\"Would you go down and see? I'm too old, and I'm afraid.\"",
            ("I'll go down.", "@start"), ("Not now.", "@end")),
        ("@start",), ("Update.Attribute", "EldestQuest", "=1"),
        msg("Quest started: The Eldest of the Mending.", sound="Quest"), ("End",),
        ("@uneasy",),
        say("Welcome to Wardhaven's church. All are welcome here.\\Amos looks over at the two Sisters in grey, and "
            "doesn't say any more.", ("Thank you.", "@end")),
        ("End",),
        ("@asked",), (">Conditional", "$Variable.1<3", "@after"),
        say("The stair's by the wall, where the floor's lifted. Mind yourself down there.", ("I will.", "@end")),
        ("End",),
        ("@after",), (">Conditional", "$Attr.EldestEnd=1", "@kept"),
        say("It's quiet under the floor now, and I sleep. One of the Sisters came to me yesterday and asked if she "
            "could just pray, the ordinary way. I said she could.", ("Goodbye.", "@end")),
        ("End",),
        ("@kept",), say("It's quiet under the floor now. Mostly. Some nights I'd swear there's still singing.",
                        ("Goodbye.", "@end")),
        ("End",),
        ("@plain",), say("Welcome to Wardhaven's church. All are welcome here.", ("Thank you.", "@end")),
        ("@end",), ("End",),
    ]


def eldest_meets():
    """Trigger Eldest Sanctum (the passage up from the stair): how he greets you is how you came to the Font."""
    say = lambda text, *a: K.say("Eldest_of_the_Mending", text, *a)  # noqa: E731
    return [
        get("EldestQuest", 1), (">Conditional", "$Variable.1=1", "@end"),
        get("EldestMet", 2), (">Conditional", "$Variable.2=0", "@end"), ("Update.Attribute", "EldestMet", "=1"),
        ("Play.Sound", "Mending_Chant"),
        get("TitheWay", 3), (">Conditional", "$Variable.3=1", "@other"),
        say("An old man, more glass than man, turns from the great Shard, and his face lights up.\\\"One of the "
            "faithful! I remember your Shards in the Font, every one. Come in, come in. Have you come to sing with "
            "us?\"", ("Walk closer.", "@close")),
        ("@close",), ("Edit.Entity", "The_Eldest", "Eldest_of_the_Mending", "ATTITUDE", "Good"),
        cyan("He opens his arms to you. He doesn't know why you've come."), ("End",),
        ("@other",), (">Conditional", "$Variable.3=2", "@foe"),
        say("An old man, more glass than man, turns from the great Shard and squints at you.\\\"I don't know your "
            "face. Who let you in?\" The choir's song changes. \"Well. Everyone's welcome to hear it, at the end.\"",
            ("Draw your weapon.", "@end")),
        ("End",),
        ("@foe",),
        say("An old man, more glass than man, turns from the great Shard, and stops smiling.\\\"I know you. You're "
            "the one who'll not listen.\" The choir's song changes. \"You will, though. Everyone does, at the end.\"",
            ("Draw your weapon.", "@end")),
        ("@end",), ("End",),
    ]


def eldest_dies():
    return [
        get("EldestQuest", 1), (">Conditional", "$Variable.1=1", "@end"),
        ("Update.Attribute", "EldestQuest", "=2"),
        cyan("The Eldest comes apart into a heap of dull glass, still smiling. Behind him, the great Shard sings on, "
             "alone."),
        ("@end",), ("End",),
    ]


def eldest_shard():
    """Listen Eldest_Great_Shard: break it, or keep a splinter."""
    say = lambda text, *a: K.say("Great_Shard", text, *a)           # noqa: E731
    return [
        (">Distance.From.Clicked.Entity", "64", "@far"), ("Play.Sound", "Mending_Whisper"),
        get("EldestQuest", 1), (">Conditional", "$Variable.1=2", "@after"),
        say("\"My beloved $Player.Son.\" Your mother's voice again, closer now, and frightened. \"Don't, love. "
            "Please. Keep a little of me, at least. Just a little, and I'll talk to you every day.\"",
            ("Break it.", "@break"), ("Keep a splinter.", "@keep"), ("Not yet.", "@end")),
        ("@break",), ("Play.Sound", "Seal_Break"), ("Update.Attribute", "EldestEnd", "=1"),
        (">Conditional", "$Attr.StrangerEnd=2", "@broke"), ("Update.Attribute", "AnnisHome", "=1"),
        ("@broke",), ("Update.Attribute", "EldestQuest", "=3"),
        cyan("You strike it, and it rings like a bell and breaks, and the voice stops in the middle of a word. The "
             "Shards in you drink up what's left of it."),
        msg("Quest complete: The Eldest of the Mending!"), ("End",),
        ("@keep",), ("Give.Item", "Marys_Whisper", "1"), ("Update.Attribute", "EldestEnd", "=2"),
        ("Update.Attribute", "EldestQuest", "=3"),
        cyan("You break off a splinter no longer than your finger. \"Thank you, love,\" it says, very softly. The "
             "great Shard goes on singing."),
        msg("Quest complete: The Eldest of the Mending!"), ("End",),
        ("@after",), (">Conditional", "$Variable.1>=3", "@hum"),
        cyan("It sings on, quieter now. The splinter at your neck sings with it."), ("End",),
        ("@hum",), cyan("It hums, cold. For a moment you'd swear someone you love is about to say your name."),
        ("@end",), ("End",),
    ] + FAR


def whisper():
    """Listen Marys_Whisper: a few Shards, once in a while, in her voice."""
    return [
        ("Play.Sound", "Mending_Whisper"),
        get("WhisperAt", 4), ("Get.Value", "CALCULATION", "$Clock-$Variable.4", V(5)),
        ("Get.Value", "CALCULATION", "$Shards.Mending.Whisper.Hours*3600", V(6)),
        (">Conditional", "$Variable.5>=$Variable.6", "@soon"),
        ("Update.Attribute", "WhisperAt", "=$Clock"), ("Give.Item", "Shard", "$Shards.Mending.Whisper"),
        cyan("\"There you are, love,\" the splinter says, in your mother's voice. \"These are for you.\" It's warm in "
             "your hand: $Shards.Mending.Whisper Shards."),
        ("End",),
        ("@soon",), cyan("\"Soon, love,\" the splinter whispers. \"Soon.\""), ("End",),
    ]


def wayfarer():
    """Talk to Mending_Wayfarer (an encounter on the road, Encounters.ini): a few Shards for nothing, friend."""
    say = lambda text, *a: K.say("Mending_Wayfarer", text, *a)      # noqa: E731
    return [
        (">Conditional", "$Attr.MendingGift=0", "@again"),
        say("A traveller in a plain grey robe, smiling as if you'd been expected.\\\"Cold out, friend, and you've "
            "had a hard road, I can see. Here: a few Shards, for nothing. Everyone deserves a little warmth.\"",
            ("Take them. Thank you.", "@take"), ("No, thank you.", "@no")),
        ("@take",), ("Update.Attribute", "MendingGift", "=1"), ("Give.Item", "Shard", "$Shards.Mending.Gift"),
        ("Play.Sound", "Absorb"),
        say("\"There. Peace on your road, friend. We'll see you again.\"", ("Goodbye.", "@end")), ("End",),
        ("@no",), say("\"Another time, then. The offer doesn't go away.\" A smile. \"Nor do we.\"",
                      ("Goodbye.", "@end")), ("End",),
        ("@again",), say("\"Hello again, friend. Keeping warm?\"", ("Goodbye.", "@end")),
        ("@end",), ("End",),
    ]


def penitent(n):
    """Talk to Chapel_Penitent_N: two of the Mending, home in Wardhaven's chapel once the great Shard's broken."""
    say = lambda text, *a: K.say("Mending_Sister", text, *a)        # noqa: E731
    if n == 1:
        return [say("Sister Hesper kneels on the cold floor, a plain wooden bead in her hands where the Shard used to "
                    "be.\\\"Amos says I can pray the ordinary way. I'm not sure I remember how.\" She tries a "
                    "word or two. \"Nobody answers. That's how it should be, isn't it?\"", ("It is.", "@end")),
                ("@end",), ("End",)]
    return [say("Brother Odo has his grey robe folded on the bench beside him, and doesn't look at it.\\\"I gave it "
                "three years' Shards. It told me my brother forgave me.\" He rubs his eyes. \"I'm going to go and "
                "ask him myself. On foot. It's a long way.\"", ("Go well, Odo.", "@end")),
            ("@end",), ("End",)]


def caels_lines():
    return [K.say("Caels_Lines", "In Cael's hand, for Annis of Ashford:\\I heard my mother in the fire, and she told "
                                 "me to feed it. It said what I wanted to hear, because that's all it can do. It "
                                 "doesn't know you. It only knows what you miss.", ("Fold it away.", "@end")),
            ("@end",), ("End",)]


def scripts():
    w("Talk to Warden", warden())
    for n in SHRINES:
        w("Ashen Shrine %d" % n, shrine(n))
    w("Hand Camp", hand_camp())
    w("Talk to Tam_Cooper", tam())
    w("Talk to House_Annis", house_annis())
    w("Talk to Home_Annis", annis_elsewhere("home"))
    w("Talk to Hall_Annis", annis_elsewhere("hall"))
    w("Talk to Undercroft_Annis", annis_elsewhere("undercroft"))
    w("Talk to Cael", cael())
    w("Read Caels_Lines", caels_lines())
    w("Talk to Sister_Linnet", linnet())
    w("Talk to Mending_Sister", sister())
    w("Talk to Ashford_Sheriff_325", sheriff())
    w("Mending Sermon", sermon())
    w("Pour Shards Hall_Font", font())
    w("Kill Font_Keeper", font_keeper())
    w("Mending Sanctum", sanctum())
    w("Listen Hall_Great_Shard", great_shard())
    w("Listen House_Shard", house_shard())
    w("Talk to Wardhaven_Priest_309", amos())
    w("Eldest Sanctum", eldest_meets())
    w("Kill The_Eldest", eldest_dies())
    w("Listen Eldest_Great_Shard", eldest_shard())
    w("Listen Marys_Whisper", whisper())
    w("Talk to Mending_Wayfarer", wayfarer())
    for n in (1, 2):
        w("Talk to Chapel_Penitent_%d" % n, penitent(n))


def main():
    data()
    place()
    climbs()
    scripts()
    print("The Mending: done")


if __name__ == "__main__":
    main()
