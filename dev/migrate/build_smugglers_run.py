"""The Smugglers' Run, three ways (dev\\Roadmap-6.md group 4). It was build_isle_quest.py's; this takes it over.

  * Red Meg, found at last, offers Holt a truce. Say yes and carry it (the old way: SmugglerSide 0), or tell her you'll
    send Holt to the wrong cove (Meg's way: SmugglerSide 1). Or, with the truce in hand, tell Holt where the camp is and
    lead his men in (Holt's way: SmugglerSide 2): the smugglers are your foes, four of them must fall (your men's kills
    count as yours: npcs.npc_killed_by_npc), and Meg gets away by sea.
  * Meg's way: Holt pays and thinks less of you (Court standing); Meg's camp is yours (a cot, a stash that's your bank,
    a trapdoor to a tunnel coming up in Ashford's fields), and she has a job: Under the Tide, a cask carried past the
    watch in the Wizards' Court (watchmen with Spotted.Script=Watch_Search take it if they see you).
  * Holt's way: the Court thinks better of you, the watch's quartermaster sells to you (SHOP-Watch), and Holt has a
    last job: The Tide Turns, rowing out to the sandbar where Meg hides, and bringing her in.
  * The Court's guards talk of what you did (build_banter.py, When=$Attr.SmugglerSide=...).

Attributes: SmugglerQuest (0-4), SmugglerSide (0 truce, 1 Meg's, 2 Holt's), SmugglerRaid (the camp's fallen, to 4),
TideQuest (0-3), TideGuards (Meg's guards on the sandbar, to 2), UnderTideQuest (0-3).

Safe to run again.

  python -I "dev\\migrate\\build_smugglers_run.py"     (then validate.py, export_web_assets.py, build_minimaps.py)
"""
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_isle import Map, obj_line            # noqa: E402
import story_kit as K                           # noqa: E402

MAKER = "build_smugglers_run.py"
COVE, COURT, SANDBAR, FIELDS = "17,4,0", "21,5,0", "18,3,0", "12,-1,0"


def px(tx, ty, npc=True):
    """A tile's top-left in pixels, as Add.Entity and Teleport take it (an NPC stands 8 px up)."""
    return "%d,%d" % ((tx - 1) * 32, (ty - 1) * 32 - (8 if npc else 0))


# ================================================================== art
def draw_cot():
    """A smuggler's cot: a low wooden frame, sailcloth stretched on it, a rolled blanket at its head."""
    p = K.pg()
    s = K.surface()
    wood, dark, cloth, shade = (112, 78, 46), (78, 52, 30), (196, 184, 150), (164, 150, 118)
    p.draw.rect(s, wood, (4, 9, 24, 18))
    p.draw.rect(s, cloth, (6, 10, 20, 15))
    for y in (14, 19, 23):
        p.draw.line(s, shade, (6, y), (25, y))                   # (the cloth's sag between the slats)
    p.draw.rect(s, (122, 46, 40), (6, 10, 20, 4))                # (the blanket, rolled at its head)
    p.draw.line(s, (92, 30, 28), (6, 12), (25, 12))
    for x in (4, 26):
        p.draw.rect(s, dark, (x, 26, 2, 3))                      # (its feet)
    return K.outlined(s)


def draw_cask():
    """A little cask of brandy: staves, two iron hoops, a bung."""
    p = K.pg()
    s = K.surface()
    p.draw.ellipse(s, (138, 92, 50), (8, 7, 16, 20))
    for x in (12, 16, 20):
        p.draw.line(s, (108, 70, 38), (x, 9), (x, 25))           # (the staves)
    for y in (11, 22):
        p.draw.line(s, (70, 70, 76), (9, y), (22, y), 2)         # (the hoops)
    p.draw.rect(s, (60, 40, 22), (15, 15, 3, 3))                 # (the bung)
    return K.outlined(s)


def art():
    K.save("Entities", "Smugglers_Cot", draw_cot())
    K.save("Entities", "Smuggled_Brandy", draw_cask())
    for i in ("", "1", "2"):
        K.copy_sprite("Entities", "Moored_Boat" + i, "Rowing_Boat" + i)
    K.copy_sprite("Entities", "Chest", "Smugglers_Stash")
    a = os.path.join(K.SPR, "Tiles", "Trapdoor001.png")
    b = os.path.join(K.SPR, "Entities", "Smugglers_Trapdoor.png")
    if not os.path.exists(b) or open(a, "rb").read() != open(b, "rb").read():
        shutil.copy(a, b)


# ================================================================== kinds, the watch's shop, the quests
KINDS = {
    "Smugglers_Cot": [("Type", "StaticObject"), ("Use.Words", "Sleep,Examine"),
                      ("Examine.Info", "A smuggler's cot, sailcloth on a frame. Red Meg says it's yours.")],
    "Smugglers_Stash": [("Type", "StaticObject"), ("Use.Words", "Bank,Examine"),
                        ("Examine.Info", "A sea chest, iron-bound. Whatever you leave in it, Meg's people keep for you.")],
    "Smugglers_Trapdoor": [("Type", "StaticObject"), ("Use.Words", "Climb Down,Examine"), ("Solid", "0"),
                           ("Examine.Info", "A trapdoor, half hidden. Meg's tunnel runs under it.")],
    "Rowing_Boat": [("Type", "StaticObject"), ("Use.Words", "Row,Examine"), ("Solid", "0"), ("Anim.Frames", "2"),
                    ("Anim.Speed", "900"), ("Examine.Info", "The watch's rowing boat.")],
    "Smuggled_Brandy": [("Type", "MapItem"), ("Use.Words", "Examine"), ("Stackable", "1"), ("Droppable", "0"),
                        ("Value", "0"), ("Examine.Info", "A little cask of Red Meg's best brandy. No duty paid on it.")],
}

WATCH_RACK = ["Type=Shop", "Buy.Rate=1.1", "Sell.Rate=0.6", "Specific=0", "Item1=Steel_Sword,2",
              "Item2=Steel_Shield,2", "Item3=Iron_Platebody,1", "Item4=Steel_Platebody,1", "Item5=Healing_Draught,8"]

RUN = [   # [The Smugglers' Run]: the keys this changes (the rest are left as they are)
    ("Stage3", "Red Meg offered a truce: her trade off the town's streets, the watch off her cove. Go back to "
               "Sergeant Holt at the castle's south gate."),
    ("Ending", "SmugglerSide"),
    ("Ending0", "You carried Red Meg's truce to Sergeant Holt. The market's quiet."),
    ("Ending1", "You sent Sergeant Holt to the wrong beach. Red Meg owes you, and the watch doesn't quite trust you."),
    ("Ending2", "You led the watch into the smugglers' camp. It's theirs now, but Red Meg got away by sea."),
]

TIDE = ["Giver=Guard", "Attribute=TideQuest",
        "Stage0=Sergeant Holt at the castle's south gate has word of Red Meg.",
        "Stage1=Red Meg is hiding on a sandbar off the coast. Row the watch's boat out from the cove's shore, deal "
        "with her guards, and bring her in.",
        "Stage2=Red Meg has given herself up. Tell Sergeant Holt.",
        "Done=3", "Marker0=Sergeant_Post", "Marker1=Megs_Sandbar", "Marker2=Sergeant_Post", "Type=Side",
        "Requires.Quests=The Smugglers' Run", "Requires.If=$Attr.SmugglerSide=2", "Reward.Shards=10",
        "Reward.Standing=Court 10"]

UNDER = ["Giver=Captain", "Attribute=UnderTideQuest",
         "Stage0=Red Meg, at her camp on the cove, has a job for a friend.",
         "Stage1=Carry a cask of Red Meg's brandy to Pell, the cellarer, in the courtyard of the Wizards' Court. "
         "The watch walks there now: if they see you with it, they'll take it.",
         "Stage2=Pell has the brandy. Go back to Red Meg.",
         "Done=3", "Marker0=Smugglers_Cove", "Marker1=Castle_Cellar", "Marker2=Smugglers_Cove", "Type=Side",
         "Requires.Quests=The Smugglers' Run", "Requires.If=$Attr.SmugglerSide=1", "Reward.Shards=10",
         "Reward.XP=Stealth 3"]


def data():
    for name, keys in KINDS.items():
        K.section(K.ENTS, name, keys)
    K.set_section(K.RACKS, "SHOP-Watch", WATCH_RACK, after="SHOP-Smugglers")
    K.section(K.QUESTS, "The Smugglers' Run", RUN)
    K.set_section(K.QUESTS, "The Tide Turns", TIDE, after="The Smugglers' Run")
    K.set_section(K.QUESTS, "Under the Tide", UNDER, after="The Tide Turns")


# ================================================================== where things are
PLACES = {   # map: [(an Id or a test that finds the line, the line)]
    COVE: [
        ("Meg_Tunnel_Cove", obj_line("StaticObject", "Smugglers_Trapdoor", 10, 11,
                                     "Id=Meg_Tunnel_Cove Here.After=SmugglerSide:1 Gone.After=SmugglerSide:2")),
        ("Meg_Cot", obj_line("StaticObject", "Smugglers_Cot", 6, 16,
                             "Id=Meg_Cot Here.After=SmugglerSide:1 Gone.After=SmugglerSide:2")),
        ("Meg_Stash", obj_line("StaticObject", "Smugglers_Stash", 7, 16,
                               "Id=Meg_Stash Here.After=SmugglerSide:1 Gone.After=SmugglerSide:2")),
        ("Watch_Boat_Cove", obj_line("StaticObject", "Rowing_Boat", 7, 8,
                                     "Id=Watch_Boat_Cove Here.After=TideQuest:1 Gone.After=TideQuest:3")),
    ],
    SANDBAR: [
        ("Watch_Boat_Sandbar", obj_line("StaticObject", "Rowing_Boat", 11, 5,
                                        "Id=Watch_Boat_Sandbar Here.After=TideQuest:1 Gone.After=TideQuest:3")),
        ("Meg_On_The_Sandbar", obj_line("NPC", "Captain", 13, 3, "Attitude=Good Stand=1 Face=S "
                                        "Id=Meg_On_The_Sandbar Name=Red_Meg Here.After=TideQuest:1 "
                                        "Gone.After=TideQuest:2", dy=-8)),
    ],
    COURT: [
        ("Castle_Cellarer", obj_line("NPC", "Barkeep", 7, 13, "Attitude=Good Stand=1 Face=E Id=Castle_Cellarer "
                                     "Name=Pell", dy=-8)),
        ("Watch_Quartermaster", obj_line("NPC", "Guard", 14, 19, "Attitude=Good Stand=1 Face=N "
                                         "Id=Watch_Quartermaster Name=Quartermaster_Brand", dy=-8)),
    ],
    FIELDS: [
        ("Meg_Tunnel_Ashford", obj_line("StaticObject", "Smugglers_Trapdoor", 5, 18,
                                        "Id=Meg_Tunnel_Ashford Here.After=SmugglerSide:1")),
    ],
}
PLACE_IDS = {SANDBAR: [("Megs_Sandbar", 13, 4)], COURT: [("Castle_Cellar", 7, 13)]}


def place():
    for name, lines in PLACES.items():
        m = Map(name)
        before = list(m.ents)
        for pid, line in lines:
            K.ents_without(m, lambda f: ("Id=%s" % pid) in f[-1].split())
            m.ents.append(line)
        for pid, x, y in PLACE_IDS.get(name, ()):
            K.place_id(m, pid, x, y)
        for i, ln in enumerate(m.ents):                  # (Meg: gone from her camp once you've sold her out)
            if name == COVE and ln.startswith("NPC\t") and "Id=Red_Meg" in ln.split("\t")[-1].split() and \
                    "Gone.After=" not in ln:
                m.ents[i] = ln + " Gone.After=SmugglerSide:2"
        if m.ents != before:
            m.save()
            print("%s: placed" % name)


# ================================================================== scripts
def V(n):
    return "Variable.%d$" % n


def get(attr, n):
    return ("Get.Value", "ATTRIBUTE", attr, V(n))


def msg(text, colour="Yellow", sound=""):
    return ("Display.Message", colour, text) + ((sound,) if sound else ())


def holt():
    say = lambda text, *a: K.say("Guard", text, *a)
    return [
        get("SmugglerQuest", 1), get("SmugglerSide", 2),
        (">Conditional", "$Variable.1=0", "@asked"),
        say("Sergeant Holt. Smuggled goods turn up in the market every week - brandy, silk, potions no apothecary "
            "made - and not one of my men has seen a cart come in.\\The fishermen by the lake talk of an old barrel on "
            "the path that nobody ever moves. Will you take a look?", ("I'll look into it.", "@start"),
            ("Not now.", "@end")),
        ("@start",), ("Update.Attribute", "SmugglerQuest", "=1"),
        msg("Quest started: The Smugglers' Run. (H: your journal)"), ("End",),
        ("@asked",), (">Conditional", "$Variable.1<3", "@three"),
        say("Anything? The barrel's on the lake path, south-west of the castle.", ("Still looking.", "@end")),
        ("End",),
        ("@three",), (">Conditional", "$Variable.1=3", "@after"),
        (">Conditional", "$Variable.2=1", "@not_megs"),
        say("Well? Where are they bringing it in?",
            ("At the old cove past the point. They'll be long gone by now.", "@wrong")),
        ("@wrong",), ("Give.Item", "Gold_Coin(s)", "60"), ("Change.Standing", "Court", "-15"),
        ("Update.Attribute", "SmugglerQuest", "=4"),
        msg("Quest complete: The Smugglers' Run! (60 gold) Holt's men will find an empty beach."), ("End",),
        ("@not_megs",), (">Conditional", "$Variable.2=2", "@choose"),
        get("SmugglerRaid", 3), (">Conditional", "$Variable.3>=4", "@raiding"),
        say("The camp's ours, and their cargo with it. Meg got away, but she won't be back in a hurry. Here: you've "
            "earned this.", ("Thank you, Sergeant.", "@raided")),
        ("@raided",), ("Give.Item", "Gold_Coin(s)", "60"), ("Change.Standing", "Court", "20"),
        ("Quest.Note.Done", "SmugglerQuest", "*"), ("Update.Attribute", "SmugglerQuest", "=4"),
        msg("Quest complete: The Smugglers' Run! (60 gold)"), ("End",),
        ("@raiding",), say("My men are waiting at the camp's gate. Go in through the barrel, and clear the camp with "
                           "them.", ("I'm going.", "@end")), ("End",),
        ("@choose",), say("A tunnel, under the shore? Well? What did you find down there?",
                          ("Red Meg offers a truce: her trade off your streets, your men off her cove.", "@truce"),
                          ("Their camp's on the cove, through the barrel. I'll lead your men in.", "@raid")),
        ("@truce",), say("A truce with Red Meg... Ha! Fair enough: a quiet market is all I want. Here, you've earned "
                         "this.", ("Thank you, Sergeant.", "@paid")),
        ("@paid",), ("Give.Item", "Gold_Coin(s)", "60"), ("Update.Attribute", "SmugglerSide", "=0"),
        ("Update.Attribute", "SmugglerQuest", "=4"), msg("Quest complete: The Smugglers' Run! (60 gold)"), ("End",),
        ("@raid",), ("Update.Attribute", "SmugglerSide", "=2"), ("Set.Side.Attitude", "Smugglers", "Bad"),
        ("Quest.Note", "SmugglerQuest", "Holt's men wait at the smugglers' camp. Go in with them and take it."),
        say("Then we go tonight. My men will be at their camp's gate: go in through the barrel and take it with them. "
            "They'll fight, mind.", ("I'm ready.", "@end")),
        msg("You've turned on the smugglers. Holt's men wait at their camp."), ("End",),
        ("@after",), (">Conditional", "$Variable.2=2", "@not_holts"),
        get("TideQuest", 3), (">Conditional", "$Variable.3=0", "@tide1"),
        say("One more thing. A fisherman saw Red Meg on a sandbar off the coast, north of the cove, with two of her "
            "lads. The watch's boat is on the cove's shore. Will you bring her in?",
            ("I'll bring her in.", "@tide"), ("Not now.", "@end")),
        ("@tide",), ("Update.Attribute", "TideQuest", "=1"), ("Update.Attribute", "TideGuards", "=0"),
        msg("Quest started: The Tide Turns."), ("End",),
        ("@tide1",), (">Conditional", "$Variable.3=1", "@tide2"),
        say("The boat's on the cove's shore. Mind her lads: they won't come quietly, even if she does.",
            ("I'm going.", "@end")), ("End",),
        ("@tide2",), (">Conditional", "$Variable.3=2", "@tide3"),
        say("She gave herself up? To you? Well, well. She'll have a cell with a view of the sea. Here.",
            ("Thank you, Sergeant.", "@tidepaid")),
        ("@tidepaid",), ("Give.Item", "Gold_Coin(s)", "80"), ("Update.Attribute", "TideQuest", "=3"),
        msg("Quest complete: The Tide Turns! (80 gold)"), ("End",),
        ("@tide3",), say("Meg's in a cell and the cove's quiet. The watch won't forget it.", ("Goodbye.", "@end")),
        ("End",),
        ("@not_holts",), (">Conditional", "$Variable.2=1", "@quiet"),
        say("Not a keg on that beach. Not a footprint. Somebody had a word in Meg's ear, I'd say.",
            ("Bad luck, Sergeant.", "@end")), ("End",),
        ("@quiet",), say("Quiet market these days. Good work.", ("Goodbye.", "@end")),
        ("@end",), ("End",),
    ]


def meg():
    say = lambda text, *a: K.say("Captain", text, *a)
    return [
        get("SmugglerQuest", 1), get("SmugglerSide", 2),
        (">Conditional", "$Variable.1>=3", "@before"),
        (">Conditional", "$Variable.2=1", "@plain"),
        get("UnderTideQuest", 3), (">Conditional", "$Variable.3=0", "@under1"),
        say("Holt's men had a lovely walk on the wrong beach, I hear. I owe you.\\And I've a job for a friend. A cask "
            "of my best for Pell, the castle's cellarer: he's in the Court's courtyard. The watch walks there now, "
            "and if they see a cask they'll have it off you.",
            ("I'll carry it.", "@under"), ("Show me your goods.", "@shop"), ("Not now.", "@end")),
        ("@under",), ("Give.Item", "Smuggled_Brandy", "1"), ("Update.Attribute", "UnderTideQuest", "=1"),
        msg("Quest started: Under the Tide."), ("End",),
        ("@under1",), (">Conditional", "$Variable.3=1", "@under2"),
        (">Got.Item", "Smuggled_Brandy", "1", "@lost"),
        say("Pell's in the courtyard, by its west wall. Keep out of the watch's eyes.",
            ("Show me your goods.", "@shop"), ("Goodbye.", "@end")), ("End",),
        ("@lost",), say("The watch had it off you? Here's another. Mind their eyes this time: they only see ahead of "
                        "them.", ("I will.", "@again")),
        ("@again",), ("Give.Item", "Smuggled_Brandy", "1"), ("End",),
        ("@under2",), (">Conditional", "$Variable.3=2", "@plain"),
        say("Pell has it? Then you're paid, and you're welcome at my fire any night.", ("Thank you.", "@underpaid")),
        ("@underpaid",), ("Give.Item", "Gold_Coin(s)", "90"), ("Update.Attribute", "UnderTideQuest", "=3"),
        msg("Quest complete: Under the Tide! (90 gold)"), ("End",),
        ("@plain",), say("Need something? I've goods you won't find in any market. And you're welcome on my cove: my "
                         "lads know your face.", ("Show me your goods.", "@shop"), ("Goodbye.", "@end")), ("End",),
        ("@shop",), ("Display.Item.Rack", "GENERAL", "Captain", "SHOP-Smugglers", "@end"), ("End",),
        ("@before",), (">Conditional", "$Variable.1=2", "@stranger"),
        say("Well, well. Up through my barrel and past my lads without a peep? I've had sailors who couldn't cross a "
            "deck that quiet.\\I'm Red Meg. Let's not make this ugly: you go back to Holt and tell him this - we keep "
            "our trade off his streets, he keeps his men off my cove. Deal?",
            ("Deal. I'll take your word to Holt.", "@deal"), ("Better: I'll send Holt to the wrong cove.", "@ours")),
        ("@deal",), ("Update.Attribute", "SmugglerQuest", "=3"),
        msg("The smugglers are your friends now. Tell Sergeant Holt about the deal."), ("End",),
        ("@ours",), ("Update.Attribute", "SmugglerQuest", "=3"), ("Update.Attribute", "SmugglerSide", "=1"),
        ("Set.Side.Attitude", "Smugglers", "Good"),
        ("Quest.Note", "SmugglerQuest", "You told Red Meg you'll send Holt to the wrong cove. Go and tell him so."),
        say("Ha! I like you. Tell him the old cove past the point: nobody's used it in years.\\And there's a cot by "
            "the fire, and a chest to keep your things, whenever you want them.", ("Done.", "@end")),
        msg("You've sided with the smugglers. Go and send Sergeant Holt the wrong way."), ("End",),
        ("@stranger",), say("Who let you in? Out, before my lads see you - they're not as friendly as me.",
                            ("I'm going.", "@end")),
        ("@end",), ("End",),
    ]


def kill_smuggler():
    return [
        get("SmugglerQuest", 1), (">Conditional", "$Variable.1=3", "@tide"),
        get("SmugglerSide", 2), (">Conditional", "$Variable.2=2", "@tide"),
        (">On.Map", COVE, "@tide"),
        get("SmugglerRaid", 3), (">Conditional", "$Variable.3<4", "@end"),
        ("Update.Attribute", "SmugglerRaid", "+1"),
        ("Get.Value", "CALCULATION", "$Variable.3+1", V(3)),
        (">Conditional", "$Variable.3<4", "@taken"),
        msg("Smugglers down: $Variable.3 of 4."), ("End",),
        ("@taken",), ("Quest.Note.Done", "SmugglerQuest", "*"),
        ("Quest.Note", "SmugglerQuest", "The camp is taken. Red Meg got away by sea. Report to Sergeant Holt."),
        msg("The camp is taken! No sign of Red Meg: she got away by sea. Report to Sergeant Holt."), ("End",),
        ("@tide",), get("TideQuest", 4), (">Conditional", "$Variable.4=1", "@end"),
        (">On.Map", SANDBAR, "@end"),
        get("TideGuards", 5), (">Conditional", "$Variable.5<2", "@end"),
        ("Update.Attribute", "TideGuards", "+1"),
        ("Get.Value", "CALCULATION", "$Variable.5+1", V(5)),
        (">Conditional", "$Variable.5<2", "@alone"),
        msg("One of Meg's lads is down."), ("End",),
        ("@alone",), ("Quest.Note", "TideQuest", "Meg's lads are down. Talk to her."),
        msg("Meg's lads are down. She's alone now."), ("End",),
        ("@end",), ("End",),
    ]


def scripts():
    K.write_script("Talk to Smuggler_Sergeant", holt(), MAKER)
    K.write_script("Talk to Red_Meg", meg(), MAKER)
    K.write_script("Kill Smuggler", kill_smuggler(), MAKER)
    smug = "Attitude=Bad Stand=1 Face=S Name=Smuggler"
    K.write_script(SANDBAR, [
        get("TideQuest", 1), (">Conditional", "$Variable.1=1", "@end"),
        get("TideGuards", 2), (">Conditional", "$Variable.2<2", "@end"),
        ("Add.Entity", px(12, 4), "Smuggler", "NPC", smug),
        ("Add.Entity", px(14, 4), "Smuggler", "NPC", smug),
        ("@end",), ("End",),
    ], MAKER)
    watch = "Attitude=Bad Name=Watchman Cone=100 PatrolMode=PingPong Pause=2-4 Spotted.Script=Watch_Search " \
            "Chase=6,11,18,15 Patrol="
    K.write_script(COURT, [
        msg("The Wizards' Court.", "Cyan"),
        get("UnderTideQuest", 1), (">Conditional", "$Variable.1=1", "@end"),
        (">Got.Item", "Smuggled_Brandy", "1", "@end"),
        ("Add.Entity", px(9, 12), "Guard", "NPC", watch + "9,12/17,12"),
        ("Add.Entity", px(17, 14), "Guard", "NPC", watch + "17,14/9,14"),
        ("@end",), ("End",),
    ], MAKER)
    K.write_script(COVE, [
        get("SmugglerQuest", 1), (">Conditional", "$Variable.1=3", "@end"),
        get("SmugglerSide", 2), (">Conditional", "$Variable.2=2", "@end"),
        get("SmugglerRaid", 3), (">Conditional", "$Variable.3<4", "@end"),
        ("Add.Entity", px(10, 18), "Guard", "NPC", "Attitude=Good Name=Watchman Zone=6,11,16,18 Chase=5,10,17,19"),
        ("Add.Entity", px(11, 18), "Guard", "NPC", "Attitude=Good Name=Watchman Zone=6,11,16,18 Chase=5,10,17,19"),
        ("Add.Entity", px(12, 18), "Guard", "NPC", "Attitude=Good Name=Watchman Zone=6,11,16,18 Chase=5,10,17,19"),
        msg("Sergeant Holt's men are through the camp's gate."),
        ("@end",), ("End",),
    ], MAKER)
    K.write_script("Watch_Search", [
        (">Got.Item", "Smuggled_Brandy", "1", "@end"),
        ("Take.Item", "Smuggled_Brandy", "1"),
        msg("Watchman: \"What's in the cask? Brandy, and no duty paid. That's the watch's now. Out you go.\"", "Red",
            "Fail"),
        ("Quest.Note", "UnderTideQuest", "The watch took the cask. Red Meg might spare another."),
        ("Teleport", px(12, 20), COURT),
        ("@end",), ("End",),
    ], MAKER)
    K.write_script("Talk to Castle_Cellarer", [
        get("UnderTideQuest", 1), (">Conditional", "$Variable.1=1", "@plain"),
        (">Got.Item", "Smuggled_Brandy", "1", "@plain"),
        K.say("Barkeep", "Is that... from our friend on the coast? Quick, before the watch comes round.",
              ("Here.", "@hand")),
        ("@hand",), ("Take.Item", "Smuggled_Brandy", "1"), ("Update.Attribute", "UnderTideQuest", "=2"),
        ("Quest.Note", "UnderTideQuest", "Pell has the brandy. Go back to Red Meg."),
        msg("Pell has the brandy. Go back to Red Meg."), ("End",),
        ("@plain",), K.say("Barkeep", "Pell, the castle's cellarer. The Magister likes his wine, and I like a quiet "
                                      "cellar.", ("Goodbye.", "@end")),
        ("@end",), ("End",),
    ], MAKER)
    K.write_script("Talk to Watch_Quartermaster", [
        get("SmugglerSide", 1), (">Conditional", "$Variable.1=2", "@no"),
        get("SmugglerQuest", 2), (">Conditional", "$Variable.2>=4", "@no"),
        K.say("Guard", "You're the one who took the cove with our lads. The watch looks after its own: what do you "
                       "need?", ("Show me.", "@shop"), ("Goodbye.", "@end")),
        ("@shop",), ("Display.Item.Rack", "GENERAL", "Guard", "SHOP-Watch", "@end"), ("End",),
        ("@no",), K.say("Guard", "The watch's stores. Not for sale, not to you.", ("Goodbye.", "@end")),
        ("@end",), ("End",),
    ], MAKER)
    K.write_script("Climb Down Meg_Tunnel_Cove", [
        msg("You crawl the length of Meg's tunnel, and come up in a field outside Ashford.", "Cyan"),
        ("Teleport", px(6, 18), FIELDS), ("End",),
    ], MAKER)
    K.write_script("Climb Down Meg_Tunnel_Ashford", [
        msg("You crawl the length of Meg's tunnel, and come up in her camp.", "Cyan"),
        ("Teleport", px(10, 12), COVE), ("End",),
    ], MAKER)
    K.write_script("Row Watch_Boat_Cove", [
        msg("You row out to the sandbar.", "Cyan"), ("Teleport", px(12, 5), SANDBAR), ("End",),
    ], MAKER)
    K.write_script("Row Watch_Boat_Sandbar", [
        msg("You row back to the cove.", "Cyan"), ("Teleport", px(7, 9), COVE), ("End",),
    ], MAKER)
    K.write_script("Talk to Meg_On_The_Sandbar", [
        get("TideGuards", 1), (">Conditional", "$Variable.1>=2", "@guarded"),
        K.say("Captain", "All right, all right. You've beaten my lads, and I can't swim that far.\\Tell Holt he can "
                         "have his cell. I've slept in worse.", ("Come on, then.", "@taken")),
        ("@taken",), ("Update.Attribute", "TideQuest", "=2"),
        ("Quest.Note", "TideQuest", "Red Meg gave herself up. Tell Sergeant Holt."),
        msg("Red Meg gives herself up. Tell Sergeant Holt."), ("End",),
        ("@guarded",), K.say("Captain", "Come to take me in? You'll have to get past my lads first.",
                             ("We'll see.", "@end")),
        ("@end",), ("End",),
    ], MAKER)


def main():
    art()
    data()
    place()
    scripts()
    print("The Smugglers' Run, three ways: done")


if __name__ == "__main__":
    main()
