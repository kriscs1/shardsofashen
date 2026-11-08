"""Other choices (dev\\Roadmap-6.md group 5): quests that end more than one way, and a town that thinks better or worse
of you for it. Takes over the scripts it names from build_hob.py, build_regions.py, build_hush_and_dread.py and
build_heir_mainland.py (story_kit.TAKES_OVER).

  * Old Hob: give back his savings (or leave them in his chest) and Oakhollow thinks better of you; keep them and it
    thinks worse (Ending=HobAngry, Reward.Standing1).
  * Bandits on the Road: the goods back to Captain Hale (Frosthold +10), or, for those on Red Meg's side, sold to her
    for more (Frosthold -10). Meg's half is in build_smugglers_run.py. (BanditWay: 1 Hale's, 2 Meg's.)
  * The Redrock Signet: to Ambrose (the manor's his again, its bandits gone, a fire to rest by), or sold to Spleen, who
    waits by the manor's door for whoever finds it (Ambrose gone; the bandits there your friends: Side=Redrock_Bandits).
    (RedrockWay: 1 sold, 2 given back.)
  * The Chancellor's Grain (new, Galaith, after The True Heir): the Archivist wants the ledger in the Chancellor's
    strongbox. To Captain Hart: the Chancellor taken below, the Archivist in his chair, Galaith +20 and its bread
    cheaper (Towns.ini Cheaper.If). To the Chancellor: his gold, his stores' shop, the treasury's key, and the
    Archivist never speaks to you again. (GrainQuest 0-3; GrainWay: 1 the bribe, 2 the captain.)
  * The Old Grove (new, Oakhollow, after The Wildwood Watch): Master Bramble wants the old oaks south-east of the
    village felled; Ranger Ash wants them kept. Felled (you blaze the great oak for his men): the oaks are stumps for you
    and a sawmill sells cheap planks. Kept (you drive off his woodcutters): the rangers' lodge, with rare herbs and a
    cot. The village is split (build_banter.py). (GroveQuest 0-6; GroveWay: 1 felled, 2 kept.)

Safe to run again.

  python -I "dev\\migrate\\build_choices.py"     (then validate.py, export_web_assets.py, build_minimaps.py)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_isle import Map, obj_line            # noqa: E402
import story_kit as K                           # noqa: E402

MAKER = "build_choices.py"
VILLAGE, GROVE = "8,11,0", "9,12,0"
MANOR, MANOR_ROAD = "15,15,0", "16,15,0"
MANOR_FLOORS = ("15,15,-1", "15,15,0", "15,15,1")
HALL = "-10,13,0"


def px(tx, ty, npc=True):
    """A tile's top-left in pixels, as Add.Entity and Teleport take it (an NPC stands 8 px up)."""
    return "%d,%d" % ((tx - 1) * 32, (ty - 1) * 32 - (8 if npc else 0))


def V(n):
    return "Variable.%d$" % n


def get(attr, n):
    return ("Get.Value", "ATTRIBUTE", attr, V(n))


def msg(text, colour="Yellow", sound=""):
    return ("Display.Message", colour, text) + ((sound,) if sound else ())


# ================================================================== art, kinds, shops
def art():
    K.copy_sprite("Entities", "Caravan_Ledger", "Grain_Ledger")
    K.copy_sprite("Entities", "Fenmoor_Hall_Key", "Galaith_Treasury_Key")
    K.copy_sprite("Entities", "Smugglers_Cot", "Rangers_Cot")
    K.copy_sprite("Entities", "Bandit", "Woodcutter")
    K.copy_walk("Bandit", "Woodcutter")
    K.copy_sprite("Entities", "Ranger", "Grove_Ranger")               # (a ranger of the lodge: not Ash himself)
    K.copy_walk("Ranger", "Grove_Ranger")
    a = os.path.join(K.SPR, "Tiles", "Oak_Tree001.png")
    b = os.path.join(K.SPR, "Entities", "Great_Oak.png")
    if not os.path.exists(b) or open(a, "rb").read() != open(b, "rb").read():
        open(b, "wb").write(open(a, "rb").read())


KINDS = {
    "Grain_Ledger": [("Type", "MapItem"), ("Use.Words", "Examine"), ("Stackable", "1"), ("Droppable", "0"),
                     ("Value", "0"), ("Examine.Info", "The Chancellor's own ledger: grain bought by the city in the "
                                                      "hungry years, and sold on at three times the price. His hand.")],
    "Galaith_Treasury_Key": [("Type", "MapItem"), ("Use.Words", "Examine"), ("Stackable", "1"), ("Droppable", "0"),
                             ("Value", "0"), ("Examine.Info", "A heavy key with the city's arms on its bow. The "
                                                              "Chancellor's, and now yours: the City Hall's treasury.")],
    "Rangers_Cot": [("Type", "StaticObject"), ("Use.Words", "Sleep,Examine"),
                    ("Examine.Info", "A ranger's cot under the oaks. Ash says it's yours whenever you pass.")],
    "Great_Oak": [("Type", "StaticObject"), ("Use.Words", "Blaze,Examine"),
                  ("Examine.Info", "The oldest oak in the grove, broader than a cart. Bramble wants his mark cut "
                                   "into it.")],
    "Grove_Ranger": [("Type", "NPC"), ("Use.Words", "Talk to"),
                     ("Examine.Info", "One of Ash's rangers, keeping the lodge in the old grove."),
                     ("Roam.Radius", "1"), ("Chase.Radius", "0"), ("Walk.Speed", "0.5"), ("Pause", "3-8"),
                     ("Attitude", "Good"), ("Respawn", "300"), ("Level", "1"),
                     ("Look.Parts", "skin:f4b8a0 ce927c;shirt:466032 2b3b1f 52713b;legs:504028 382c1c;"
                                    "hair:5a3c1e 3c2812")],
    "Woodcutter": [("Type", "NPC"), ("Use.Words", "Examine"),
                   ("Examine.Info", "One of Bramble's woodcutters, an axe on his shoulder and no wish to go home."),
                   ("Hitpoints", "24"), ("Attack.Speed", "1.3"), ("Strength", "5"), ("Defence", "4"),
                   ("Aggro.Range", "200"), ("Weapon.Range", "0"), ("Movement.Speed", "2"), ("Aggressive", "1"),
                   ("Respawn", "0"), ("Drops", "Logs,1-3,60"), ("Roam.Radius", "2"), ("Chase.Radius", "8"),
                   ("Walk.Speed", "0.6"), ("Pause", "2-5"), ("Kill.Sound", "Humanoid"), ("Attitude", "Bad"),
                   ("Level", "5"),
                   ("Look.Parts", "skin:f4b8a0 ce927c;shirt:463c32 2b251f 52463b;legs:3c3228 2a231c;hair:281e18 140e0c"),
                   ("Looks", "shirt=8c2a22 legs=4a3c2a hair=6e4a28 skin=d29a78|shirt=2a5a3a legs=3a3428 hair=2a2018 "
                             "skin=a8724e")],
}

RACKS = {
    "SHOP-Chancellors_Stores": ["Type=Shop", "Buy.Rate=0.9", "Sell.Rate=0.6", "Specific=0", "Item1=Bread,30",
                                "Item2=Meat_Pie,10", "Item3=Fish_Pie,10", "Item4=Berry_Pie,10",
                                "Item5=Healing_Draught,6"],
    "SHOP-Sawmill": ["Type=Shop", "Buy.Rate=0.6", "Sell.Rate=0.6", "Specific=0", "Item1=Plank,60", "Item2=Logs,30",
                     "Item3=Oak_Logs,20"],
    "SHOP-Rangers_Lodge": ["Type=Shop", "Buy.Rate=1.0", "Sell.Rate=0.6", "Specific=0", "Item1=Nightshade,6",
                           "Item2=Marigold,8", "Item3=Sage,10", "Item4=Arrows,200", "Item5=Oak_Bow,2"],
}


# ================================================================== the quests
HOB = [("Ending", "HobAngry"),
       ("Ending0", "Hob is himself again, and his door is open to you."),
       ("Ending1", "You kept Hob's savings, and the madness took him again."),
       ("Reward.Standing", "Oakhollow 10"), ("Reward.Standing1", "Oakhollow -15")]

BANDITS = [("Ending", "BanditWay"),
           ("Ending1", "You brought the stolen goods back to Captain Hale."),
           ("Ending2", "You sold the stolen goods to Red Meg. Frosthold's carts went without."),
           ("Reward.Standing", "Frosthold 10"), ("Reward.Standing2", "Frosthold -10")]

SIGNET = [("Ending", "RedrockWay"),
          ("Ending1", "You sold the Redrock signet to Spleen. The bandits keep the manor, and you're welcome in it."),
          ("Ending2", "You gave the signet back to Ambrose. The manor is his again.")]

GRAIN = ["Giver=Archivist", "Attribute=GrainQuest",
         "Stage0=The Royal Archivist at Galaith's City Hall has something on her mind.",
         "Stage1=The Archivist believes the Chancellor hoarded the city's grain while Galaith starved. His ledger "
         "would prove it: he keeps a strongbox in the City Hall.",
         "Stage2=You have the Chancellor's ledger. Captain Hart, at the palace door, answers to the King, not to the "
         "Chancellor.",
         "Done=3", "Marker0=Galaith_City_Hall", "Marker1=Galaith_City_Hall", "Marker2=Palace_Gate", "Type=Side",
         "Requires.Quests=The True Heir", "Reward.Shards=15", "Ending=GrainWay",
         "Ending1=You sold the Chancellor his ledger back. He's richer, you're richer, and the Archivist won't speak "
         "to you.",
         "Ending2=You gave the ledger to Captain Hart. The Chancellor is in a cell, and the Archivist sits in his "
         "chair.",
         "Reward.Standing2=Galaith 20",
         "Rumour=They say the Chancellor's cellars are full, and the city's bakers can't get flour."]

GROVE_Q = ["Giver=Ranger", "Attribute=GroveQuest",
           "Stage0=Ranger Ash and a timber merchant in Oakhollow are at odds over the old oaks south-east of the "
           "village.",
           "Stage1=Master Bramble wants the old oaks south-east of Oakhollow felled for timber; Ranger Ash wants them "
           "kept. Side with one of them.",
           "Stage2=Cut Bramble's mark into the great oak in the old grove, south-east of Oakhollow. His men will do "
           "the rest.",
           "Stage3=Bramble's woodcutters are in the old grove already. Drive them off ($GroveCutters of 2).",
           "Stage4=The great oak bears Bramble's mark. Go back to him.",
           "Stage5=Bramble's woodcutters are gone. Go back to Ranger Ash.",
           "Done=6", "Marker0=Oakhollow_Grove_Talk", "Marker1=Oakhollow_Grove_Talk", "Marker2=Old_Grove",
           "Marker3=Old_Grove", "Marker4=Oakhollow_Grove_Talk", "Marker5=Oakhollow_Grove_Talk", "Type=Side",
           "Requires.Quests=The Wildwood Watch", "Reward.Shards=10", "Reward.Standing=Oakhollow 5", "Ending=GroveWay",
           "Ending1=The old grove is felled. Bramble's sawmill is busy, and half the village has work.",
           "Ending2=The old grove stands. The rangers keep a lodge there, and half the village is still poor.",
           "Rumour=There's talk of felling the old oaks by Oakhollow. Ranger Ash won't hear of it."]

GALAITH_CHEAPER = [("Cheaper.If", "$Attr.GrainWay=2"), ("Cheaper.Racks", "SHOP-Bakery,SHOP-Baker"),
                   ("Cheaper.Rate", "0.7")]


def data():
    for name, keys in KINDS.items():
        K.section(K.ENTS, name, keys)
    for name, lines in RACKS.items():
        K.set_section(K.RACKS, name, lines)
    K.section(K.QUESTS, "Old Hob", HOB)
    K.section(K.QUESTS, "Bandits on the Road", BANDITS)
    K.section(K.QUESTS, "The Redrock Signet", SIGNET)
    K.set_section(K.QUESTS, "The Chancellor's Grain", GRAIN, after="The True Heir")
    K.set_section(K.QUESTS, "The Old Grove", GROVE_Q, after="The Wildwood Watch")
    K.section(os.path.join(K.DATA, "Towns.ini"), "Galaith", GALAITH_CHEAPER)


# ================================================================== where things are
PLACES = {   # map: [(Id, the line)]
    VILLAGE: [
        ("Timber_Merchant", obj_line("NPC", "Merchant", 9, 12, "Attitude=Good Stand=1 Face=E Id=Timber_Merchant "
                                     "Name=Master_Bramble", dy=-8)),
    ],
    GROVE: [
        ("Old_Grove_Oak", obj_line("StaticObject", "Great_Oak", 22, 5, "Id=Old_Grove_Oak Gone.After=GroveWay:1")),
        ("Grove_Sawyer", obj_line("NPC", "Carter", 18, 7, "Attitude=Good Stand=1 Face=S Id=Grove_Sawyer "
                                  "Name=Sawyer_Tom Here.After=GroveWay:1 Gone.After=GroveWay:2", dy=-8)),
        ("Grove_Warden", obj_line("NPC", "Grove_Ranger", 18, 7, "Attitude=Good Stand=1 Face=S Id=Grove_Warden "
                                  "Name=Warden_Ivy Here.After=GroveWay:2", dy=-8)),
        ("Grove_Cot", obj_line("StaticObject", "Rangers_Cot", 17, 7, "Id=Grove_Cot Here.After=GroveWay:2")),
    ],
    MANOR: [
        ("Spleen_Parley", obj_line("NPC", "Bandit", 17, 20, "Attitude=Good Stand=1 Face=W Id=Spleen_Parley "
                                   "Name=Spleen Here.After=RedrockSignetQuest:1 Gone.After=RedrockWay:1", dy=-8)),
        ("Ambrose_At_Home", obj_line("NPC", "Manor_Steward", 11, 15, "Attitude=Good Stand=1 Face=S "
                                     "Id=Ambrose_At_Home Name=Ambrose Here.After=RedrockWay:2", dy=-8)),
    ],
    HALL: [
        ("Chancellors_Strongbox", obj_line("StaticObject", "Chest", 12, 5,
                                           "Id=Chancellors_Strongbox Lock=5 Sturdy=1")),
        ("Galaith_Treasury", obj_line("StaticObject", "Chest", 5, 5,
                                      "Id=Galaith_Treasury Lock=8 Sturdy=1 Key=Galaith_Treasury_Key")),
        ("Chancellor_Sefton", obj_line("NPC", "Archivist", 9, 5, "Attitude=Good Stand=1 Face=S "
                                       "Id=Chancellor_Sefton Name=Chancellor_Sefton Here.After=GrainWay:2", dy=-8)),
    ],
}
PLACE_IDS = {VILLAGE: [("Oakhollow_Grove_Talk", 11, 11)], GROVE: [("Old_Grove", 20, 5)]}


def add_option(ln, key, value):
    """A map line with key=value among its options (once)."""
    if any(o.startswith(key + "=") for o in ln.split("\t")[-1].split()):
        return ln
    return ln + " %s=%s" % (key, value)


def place():
    for name in set(PLACES) | set(PLACE_IDS) | set(MANOR_FLOORS) | {MANOR_ROAD, HALL}:
        m = Map(name)
        before = list(m.ents)
        for pid, line in PLACES.get(name, ()):
            K.ents_without(m, lambda f: ("Id=%s" % pid) in f[-1].split())
            m.ents.append(line)
        for pid, x, y in PLACE_IDS.get(name, ()):
            K.place_id(m, pid, x, y)
        for i, ln in enumerate(m.ents):
            opts = ln.split("\t")[-1].split()
            if name in MANOR_FLOORS and ln.startswith("NPC\tBandit\t") and "Group=REDROCK_MANOR" in opts:
                ln = add_option(add_option(ln, "Side", "Redrock_Bandits"), "Gone.After", "RedrockWay:2")
            if name == MANOR_ROAD and "Id=Redrock_Steward" in opts:
                ln = add_option(ln, "Gone.After", "RedrockWay:1")          # (home, or gone for good)
            if name == HALL and ("Id=Galaith_Clerk_73" in opts or "Id=Galaith_Speaker_70" in opts):
                ln = add_option(ln, "Gone.After", "GrainWay:2")          # (the Archivist in his chair; he's below)
            m.ents[i] = ln
        if m.ents != before:
            m.save()
            print("%s: placed" % name)


# ================================================================== Old Hob (build_hob.py's, with Oakhollow's word)
def hob():
    say = lambda text, *a: K.say("Hob", text, *a)
    return [
        get("HobQuest", 1), get("HobAngry", 3),
        (">Conditional", "$Variable.1>=3 and $Variable.3=0", "@wild"),
        (">Conditional", "$Variable.1=3", "@after"),
        get("HobsChest", 2), (">Conditional", "$Variable.2=1", "@kept"),
        (">Got.Item", "Gold_Coin(s)", "150", "@cant_pay"),             # (you took his savings)
        say("You brought me back... but I've been home in my head, and I know what's in my chest. Or was. You've been "
            "in my house, haven't you? That was all I had.\\Give me back my 150 gold, and we'll say no more about it.",
            ("Here, take it back.", "@give_back"), ("Finders keepers.", "@refuse")),
        ("End",),
        ("@cant_pay",),
        say("You brought me back... and you emptied my chest while I was gone. 150 gold, my life's savings!\\Bring it "
            "back, thief, or by the trees I'll-", ("I'll bring it back.", "@end"), ("It's mine now.", "@refuse")),
        ("End",),
        ("@give_back",), ("Take.Item", "Gold_Coin(s)", "150"), ("Update.Attribute", "HobAngry", "=0"),
        ("Update.Attribute", "HobQuest", "=4"), ("Quest.Note.Done", "HobQuest", "*"),
        ("Update.Attribute", "HobsDoorOpen", "=1"), ("Give.Item", "Gold_Coin(s)", "40"),
        ("Quest.Note", "HobQuest", "You gave Hob back his savings, and he gave you 40 gold for your honesty."),
        say("An honest thief! Here, 40 of it for your trouble, and keep the ring. My door's open to you any time.",
            ("Thank you, Hob.", "@paid")),
        ("@paid",), msg("Quest complete: Old Hob! He's himself again, and you're 40 gold the richer."), ("End",),
        ("@refuse",), ("Update.Attribute", "HobAngry", "=1"),          # (first: Oakhollow hears which way it went)
        ("Update.Attribute", "HobQuest", "=4"), ("Quest.Note.Done", "HobQuest", "*"),
        ("Set.NPC.Attitude", "OldHob", "Bad"),
        ("Quest.Note", "HobQuest", "You kept Hob's savings, and the madness took him again. He's wild for good now."),
        msg("Hob's eyes go wild again. He goes for your throat!", "Red", "-"),
        msg("Quest complete: Old Hob... though not the way anyone hoped."), ("End",),
        ("@kept",), ("Update.Attribute", "HobAngry", "=0"),          # (you left his savings alone: they're yours)
        ("Update.Attribute", "HobQuest", "=4"), ("Quest.Note.Done", "HobQuest", "*"),
        ("Update.Attribute", "HobsDoorOpen", "=1"),
        ("Quest.Note", "HobQuest", "Hob says the savings in his chest are yours. His house is in Oakhollow, and the "
                                   "door's open now."),
        say("You brought me back. I remember the spider, the woods, the hunger. And you.\\Thank you, friend. My door "
            "is open now, and what's in my chest is yours: you've earned it.", ("Thank you, Hob.", "@thanked")),
        ("@thanked",), msg("Quest complete: Old Hob! His savings are yours: they're in the chest in his house."),
        ("End",),
        ("@after",), say("Mind how you go out there. And mind the spiders.", ("I will.", "@end")), ("End",),
        ("@wild",), msg("He only snarls at you.", "DarkRed", "Fail"),
        ("@end",), ("End",),
    ]


# ================================================================== Captain Hale (build_regions.py's, with Meg's way)
def hale():
    say = lambda text, *a: K.say("Captain", text, *a)
    return [
        get("BanditQuest", 1), (">Conditional", "$Variable.1=0", "@begun"),
        (">Quest.Can.Start", "BanditQuest", "@green"),
        say("You look handy with a blade. Bandits are robbing every cart on the Redrock road, and my men are too few.\\"
            "Kill five of them and come back to me.", ("Consider it done.", "@start"), ("Not now.", "@end")),
        ("End",),
        ("@start",), ("Update.Attribute", "BanditQuest", "=1"),
        ("Quest.Note", "BanditQuest", "Bandits rob travellers on the Redrock road and in the hills: slay five."),
        msg("Quest started: Bandits on the Road."), ("End",),
        ("@begun",), (">Conditional", "$Variable.1=1", "@two"),
        get("BanditsSlain", 2), (">Conditional", "$Variable.2>=5", "@more"),
        ("Update.Attribute", "BanditQuest", "=2"),
        ("Quest.Note.Done", "BanditQuest", "Report to Captain Hale in Frosthold."),
        ("Quest.Note", "BanditQuest", "The bandits' camp is somewhere in the eastern hills."),
        ("Quest.Note", "BanditQuest", "Break open their strongbox and take back the stolen goods."),
        say("Five! Now for their camp: somewhere in the eastern hills. They keep what they steal in an iron "
            "strongbox. Bring the goods back.", ("I'll find it.", "@end")),
        ("End",),
        ("@more",), say("Five bandits. They lurk on the roads and up in the hills.", ("Yes, captain.", "@end")),
        ("End",),
        ("@two",), (">Conditional", "$Variable.1=2", "@three"),
        say("The camp is in the eastern hills. Look for their tents.", ("On my way.", "@end")), ("End",),
        ("@three",), (">Conditional", "$Variable.1=3", "@done"),
        (">Got.Item", "Stolen_Goods", "1", "@lost"),
        ("Take.Item", "Stolen_Goods", "1"), ("Update.Attribute", "BanditWay", "=1"),
        ("Update.Attribute", "BanditQuest", "=4"), ("Quest.Note.Done", "BanditQuest", "*"),
        ("Give.Item", "Gold_Coin(s)", "200"), ("Give.Item", "Steel_Platebody", "1"), ("Update.Skill", "Strength", "+2"),
        say("The town's goods! You've done the Redrock road a great service. Take this armour, and the reward.",
            ("Thank you!", "@thanked")),
        ("@thanked",),
        msg("Quest complete: Bandits on the Road! You receive 200 gold, a steel platebody and Strength experience."),
        ("End",),
        ("@lost",), say("Where are the goods? Did you lose them?", ("I'll get them.", "@end")), ("End",),
        ("@done",), get("BanditWay", 3), (">Conditional", "$Variable.3=2", "@salute"),
        say("The bandits are gone, and so are the town's goods. Word is they turned up on the coast, sold to "
            "smugglers. Funny, that.", ("Goodbye.", "@end")), ("End",),
        ("@salute",), say("The road is safe again. Frosthold salutes you.", ("Goodbye.", "@end")), ("End",),
        ("@green",), say("The road's no place for civilians while it's crawling with bandits. When you can swing a "
                         "sword like you mean it, report back to me.", ("Yes, Captain.", "@end")),
        ("@end",), ("End",),
    ]


# ================================================================== the Redrock Signet: Ambrose, and Spleen
def ambrose():
    say = lambda text, *a: K.say("Manor_Steward", text, *a)
    return [
        get("RedrockSignetQuest", 1), (">Conditional", "$Variable.1=0", "@begun"),
        (">Quest.Can.Start", "RedrockSignetQuest", "@away"),
        say("You there! Forgive an old man for shouting: I'm not allowed any nearer. Ambrose, steward of Redrock Manor "
            "these fifty years. Well. Steward of the road outside it, these three months.", ("What happened?", "@why"),
            ("Good day to you.", "@end")),
        ("@why",),
        say("Bandits. They came in the spring and threw me out by my collar. The old lord, rest him, was a careful "
            "man: he built that house so no thief could ever find his way about it. Rooms with no doors. Stairs to "
            "nowhere. It took me twenty years to learn it, and I still go the long way round to the kitchen.\\They've "
            "never found the vault. I can hear them swearing about it from here.",
            ("And you want something from it.", "@ask")),
        ("@ask",),
        say("The family's signet: a ruby in gold, the Redrock seal. If the young master ever comes home, he'll want "
            "it, and I'll not have it melted down by a man called Spleen. Bring it to me and you'll be paid. The rest "
            "of the old lord's things in there are yours, with my blessing.", ("I'll bring it back.", "@start"),
            ("Not today.", "@end")),
        ("@start",), ("Update.Attribute", "RedrockSignetQuest", "=1"),
        msg("Quest started: The Redrock Signet.", "Yellow", "Quest"),
        (">Got.Item", "Redrock_Signet", "1", "@end"),
        ("Goto.Line", "@give"),
        ("@begun",), (">Conditional", "$Variable.1=1", "@after"),
        (">Got.Item", "Redrock_Signet", "1", "@looking"),
        ("@give",), ("Take.Item", "Redrock_Signet", "1"), ("Update.Attribute", "RedrockWay", "=2"),
        ("Update.Attribute", "RedrockSignetQuest", "=2"),
        say("The signet! And you came back out again, which is more than the last two did.\\Was the old lord's scroll "
            "there beside it? The Dread, he called it. He read it at tax collectors. Keep it: it's done its work in "
            "this family.\\And with the seal in my hand, the law's on my side: the sheriff's men will have those "
            "bandits out by nightfall. Come and sit by my fire, any time.", ("Goodbye, Ambrose.", "@paid")),
        ("@paid",), msg("Quest complete: The Redrock Signet! The manor is Ambrose's again.", "Yellow", "Quest"),
        ("End",),
        ("@looking",), say("The signet's in the vault, and the vault's where it always was. Mind how you go: the old "
                           "lord's house is a liar, every wall of it.", ("I'll keep looking.", "@end")), ("End",),
        ("@away",), say("Move along, traveller. Nothing here but an old man and his grudge.", ("Goodbye.", "@end")),
        ("End",),
        ("@after",), say("I polish it every morning. The young master will come home one day. I'm quite sure of it.",
                         ("Goodbye, Ambrose.", "@end")),
        ("@end",), ("End",),
    ]


def ambrose_at_home():
    say = lambda text, *a: K.say("Manor_Steward", text, *a)
    return [
        say("My own hall again, and the kitchen still the long way round. Sit, sit. There's a fire, and a chair by it "
            "with your name on it.", ("I'll rest a while.", "@rest"), ("Goodbye, Ambrose.", "@end")),
        ("End",),
        ("@rest",), ("Sleep", "Next"), ("End",),
        ("@end",), ("End",),
    ]


def spleen():
    say = lambda text, *a: K.say("Bandit", text, *a)
    return [
        get("RedrockSignetQuest", 1), (">Conditional", "$Variable.1=1", "@end"),
        (">Got.Item", "Redrock_Signet", "1", "@hunting"),
        say("You found it. The old man's ring, in the old man's vault, and you walked out with it under my nose.\\"
            "I'll give you more for it than he can: 130 gold, and the run of my house. My lads won't lift a hand to "
            "you again. What's it to be?", ("Sell it to Spleen.", "@sell"), ("It's going back to Ambrose.", "@no")),
        ("End",),
        ("@sell",), ("Take.Item", "Redrock_Signet", "1"), ("Give.Item", "Gold_Coin(s)", "130"),
        ("Update.Attribute", "RedrockWay", "=1"), ("Set.Side.Attitude", "Redrock_Bandits", "Good"),
        ("Update.Attribute", "RedrockSignetQuest", "=2"),
        ("Quest.Note", "RedrockSignetQuest", "You sold the signet to Spleen. Ambrose has gone from the road."),
        msg("Quest complete: The Redrock Signet... sold to Spleen. The bandits at Redrock are your friends now.",
            "Yellow", "Quest"),
        say("\"One more thing, friend, since you're one of us now.\" Spleen shows you a thumb in the eye, a knee "
            "where it hurts, a fistful of grit: how a bandit wins a fair fight. \"Never fight fair.\"",
            ("I'll remember.", "@taught")),
        ("@taught",), ("Learn.Stance", "Fighting", "Dirty_Fighting"),
        ("End",),
        ("@no",), say("Then don't let my lads catch you on the stairs.", ("We'll see.", "@end")), ("End",),
        ("@hunting",), say("Spleen. This is my house now. The old man sent you after his ring, I suppose.\\Find it, "
                           "and bring it to me, not him. I pay better.", ("We'll see.", "@end")),
        ("@end",), ("End",),
    ]


# ================================================================== the Chancellor's Grain
def archivist():
    say = lambda text, *a: K.say("Archivist", text, *a)
    return [
        get("GrainWay", 4), (">Conditional", "$Variable.4=1", "@grain"),
        say("I have nothing to say to you. Good day.", ("...", "@end")), ("End",),
        ("@grain",), get("GrainQuest", 6), (">Conditional", "$Variable.6=0", "@g1"),
        (">Quest.Can.Start", "GrainQuest", "@heir"),
        say("My $Player.Lord. May I speak plainly?\\In the hungry years, the city bought grain to feed Galaith. Little "
            "of it reached the bakers, and what did cost three times its worth. The Chancellor signed every bill of "
            "it. He keeps his own ledger in the strongbox by his desk: I've seen him lock it.\\If that ledger came to "
            "light... Will you find it?", ("I'll find his ledger.", "@g_start"), ("Not now.", "@end")),
        ("End",),
        ("@g_start",), ("Update.Attribute", "GrainQuest", "=1"), msg("Quest started: The Chancellor's Grain."),
        ("End",),
        ("@g1",), (">Conditional", "$Variable.6=1", "@g2"),
        say("His strongbox is by his desk, at the end of the hall. It's locked, of course.", ("I'll find a way.", "@end")),
        ("End",),
        ("@g2",), (">Conditional", "$Variable.6=2", "@heir"),
        say("You have it? Then take it to Captain Hart at the palace door. He answers to the King, not to the "
            "Chancellor.", ("I will.", "@end")), ("End",),
        ("@heir",), get("GuardQuest", 1), (">Conditional", "$Variable.1=2", "@plain"),
        (">Got.Item", "Amulet_of_Succession", "1", "@amulet"),
        (">Got.Item", "Marys_Notes", "1", "@notes"),
        say("Her own hand. Then there's nothing left to doubt.\\She turns the amulet in the lamplight once more, and "
            "her hands begin to shake.", ("She was my mother.", "@vouch")),
        ("@vouch",), ("Give.Item", "Archivists_Attestation", "1"), ("Update.Attribute", "GuardQuest", "=3"),
        say("Then welcome home, my $Player.Lord. Take my word to the Chancellor, under my own seal.",
            ("Thank you.", "@end")), ("End",),
        ("@notes",),
        say("The Chancellor sent you? Let me see it.\\The crown, the sapphire, the mark of the old smiths under the "
            "clasp. This is the Amulet of Ashen Succession. Queen Mary wore it the night she vanished.\\But an amulet "
            "can be stolen, and my seal can't be given back. The night she fled, the old Chancellor had her papers "
            "sealed in the vault under this hall, and set the Guard to keep them. Bring me something in her own "
            "hand, and I'll know.", ("How do I get down there?", "@vault")),
        ("@vault",), ("Update.Attribute", "ArchiveVault", "=1"),
        say("There's a hatch at the back of the hall. I'll leave it unbarred. The watchmen down there answer to the "
            "Chancellor, not to me, and they don't ask who you are first. Go softly.", ("I will.", "@end")),
        ("End",),
        ("@amulet",), say("An amulet? You'd better show it to me, then. I can't vouch for a story.",
                          ("Right.", "@end")), ("End",),
        ("@plain",), say("The archive of Galaith: every charter, every seal, every deed since the city was founded.",
                         ("Goodbye.", "@end")),
        ("@end",), ("End",),
    ]


def chancellor():
    say = lambda text, *a: K.say("Chancellor", text, *a)
    return [
        get("GrainWay", 4), (">Conditional", "$Variable.4=1", "@grain"),
        say("My $Player.Lord. My stores are at your disposal, as agreed. And the treasury's key is in good hands.",
            ("Show me your stores.", "@stores"), ("Goodbye.", "@end")), ("End",),
        ("@stores",), ("Display.Item.Rack", "GENERAL", "Chancellor", "SHOP-Chancellors_Stores", "@end"), ("End",),
        ("@grain",), get("GrainQuest", 5), (">Conditional", "$Variable.5=2", "@heir"),
        (">Got.Item", "Grain_Ledger", "1", "@heir"),
        say("That book. Where did you... no. It doesn't matter where.\\Let us be practical, my $Player.Lord. Give it "
            "to me, and you'll have 250 gold, the run of my stores at a fair price, and the key to the City Hall's "
            "treasury. Give it to Hart, and you'll have a hungry city's thanks. Which feeds you better?",
            ("Give him the ledger, for his price.", "@bribe"), ("It's going to Captain Hart.", "@refuse")),
        ("End",),
        ("@bribe",), ("Take.Item", "Grain_Ledger", "1"), ("Give.Item", "Gold_Coin(s)", "250"),
        ("Give.Item", "Galaith_Treasury_Key", "1"), ("Update.Attribute", "GrainWay", "=1"),
        ("Update.Attribute", "GrainQuest", "=3"),
        ("Quest.Note", "GrainQuest", "You sold the Chancellor his ledger. His stores are open to you, and the "
                                     "treasury's key is yours."),
        msg("Quest complete: The Chancellor's Grain... you took his price."), ("End",),
        ("@refuse",), say("Then we have nothing more to discuss.", ("No, we don't.", "@end")), ("End",),
        ("@heir",), get("GuardQuest", 1), (">Conditional", "$Variable.1=1", "@warrant"),
        say("You wish to see the King? You, and every merchant, beggar and poet in Galaith, now the gates are open.\\"
            "What makes you more than they are?", ("I am his $Player.Son.", "@son")),
        ("@son",),
        say("Bold. The Queen's child would be eighteen now, and would carry the Amulet of Succession. Show it to the "
            "Royal Archivist, at the City Hall: she knows every true seal in Ashen. If she vouches for it, so shall "
            "I.", ("I'll go to the Archivist.", "@to_her")),
        ("@to_her",), ("Update.Attribute", "GuardQuest", "=2"), ("End",),
        ("@warrant",), (">Conditional", "$Variable.1=3 and $Item.Archivists_Attestation>=1", "@plain"),
        ("Take.Item", "Archivists_Attestation", "1"), ("Give.Item", "Chancellors_Warrant", "1"),
        ("Update.Attribute", "GuardQuest", "=4"),
        say("The Archivist's seal, in green. Then it is true.\\My $Player.Lord. Forgive an old man his doubts. Here is "
            "my warrant: show it to the captain of the guard.", ("Thank you, Chancellor.", "@end")), ("End",),
        ("@plain",), say("The Parliament of Ashen will return from Northport, now the road is open. There is much to "
                         "do.", ("Goodbye.", "@end")),
        ("@end",), ("End",),
    ]


def hart():
    say = lambda text, *a: K.say("Guard_Captain", text, *a)
    return [
        get("GrainQuest", 2), (">Conditional", "$Variable.2=2", "@guard"),
        (">Got.Item", "Grain_Ledger", "1", "@guard"),
        say("The Chancellor's hand, and the city's grain sold on at three times its price. In the hungry years.\\"
            "My $Player.Lord, if I take this, I go to the King with it, and the Chancellor goes below. Well?",
            ("Hand the ledger to Captain Hart.", "@hand"), ("Not yet.", "@end")),
        ("End",),
        ("@hand",), ("Take.Item", "Grain_Ledger", "1"), ("Give.Item", "Gold_Coin(s)", "100"),
        ("Update.Attribute", "GrainWay", "=2"), ("Update.Attribute", "GrainQuest", "=3"),
        ("Quest.Note", "GrainQuest", "Captain Hart took the ledger to the King. The Chancellor is in a cell, and the "
                                     "Archivist sits in his chair."),
        msg("Quest complete: The Chancellor's Grain! The Chancellor is taken below, and the Archivist is Chancellor "
            "now. Bread is cheaper in Galaith."), ("End",),
        ("@guard",), get("GuardQuest", 1), (">Conditional", "$Variable.1=0", "@asked"),
        (">Quest.Can.Start", "GuardQuest", "@end"),
        say("Halt. You're the one who killed the dragon? Then Galaith owes you everything, and you have my thanks.\\"
            "But nobody sees the King without the Lord Chancellor's leave. Not even dragon-slayers. He sits in the "
            "Parliament.", ("I'll see the Chancellor.", "@start")),
        ("@start",), ("Update.Attribute", "GuardQuest", "=1"),
        msg("Quest started: The Royal Guard.", "Yellow", "Quest"), ("End",),
        ("@asked",), (">Conditional", "$Variable.1=4 and $Item.Chancellors_Warrant>=1", "@plain"),
        ("Take.Item", "Chancellors_Warrant", "1"), ("Update.Attribute", "GuardQuest", "=5"),
        say("The Chancellor's warrant. Then you may pass, and... my $Player.Lord.\\The King is in the throne room.",
            ("Thank you, Captain.", "@pass")),
        ("@pass",), msg("Quest complete: The Royal Guard!", "Yellow", "Quest"), ("End",),
        ("@plain",), say("The palace is guarded day and night.", ("Goodbye.", "@end")),
        ("@end",), ("End",),
    ]


def sefton():
    say = lambda text, *a: K.say("Archivist", text, *a)
    return [
        say("Chancellor Sefton. It still sounds strange.\\The granaries are open, and bread is cheaper in every "
            "bakery in Galaith. That was your doing, my $Player.Lord, and the city knows it.", ("Goodbye.", "@end")),
        ("@end",), ("End",),
    ]


def strongbox():
    return [
        (">Distance.From.Clicked.Entity", "48", "@far"),
        get("GrainQuest", 1), (">Conditional", "$Variable.1=1", "@papers"),
        (">Got.Item", "Grain_Ledger", "1", "@ledger"),
        ("@papers",), msg("Tax rolls and letters of credit. Nothing you need.", "Cyan", "Empty"), ("End",),
        ("@ledger",), ("Play.Sound", "Chest"), ("Give.Item", "Grain_Ledger", "1"),
        ("Update.Attribute", "GrainQuest", "=2"),
        ("Quest.Note", "GrainQuest", "You have the Chancellor's ledger. Captain Hart, at the palace door, answers to "
                                     "the King."),
        msg("Under the tax rolls: a ledger in the Chancellor's own hand. Grain, bought by the city, sold on at three "
            "times the price."), ("End",),
        ("@far",), msg("You are too far away!", "DarkRed", "Denied"),
        ("End",),
    ]


def treasury():
    return [
        (">Distance.From.Clicked.Entity", "48", "@far"),
        get("GalaithTreasury", 1), (">Conditional", "$Variable.1=0", "@empty"),
        ("Update.Attribute", "GalaithTreasury", "=1"), ("Play.Sound", "Chest"),
        ("Give.Item", "Gold_Coin(s)", "300"), ("Give.Item", "Sapphire", "1"),
        msg("The City Hall's treasury. You take what you dare: 300 gold and a sapphire."), ("End",),
        ("@empty",), msg("You've taken what you dared already.", "Cyan", "Empty"), ("End",),
        ("@far",), msg("You are too far away!", "DarkRed", "Denied"),
        ("End",),
    ]


# ================================================================== the Old Grove: Ranger Ash, and Bramble
def ash():
    say = lambda text, *a: K.say("Ranger", text, *a)
    return [
        get("RangerQuest", 1), (">Conditional", "$Variable.1>=4", "@watch"),
        get("GroveQuest", 3), get("GroveWay", 4),
        (">Conditional", "$Variable.3<=1", "@grove2"),
        (">Quest.Can.Start", "GroveQuest", "@quiet"),
        say("You've met Bramble? The timber man. He wants the old oaks south-east of the village: three hundred "
            "years of them, for planks.\\His woodcutters are already there, waiting for his word. Stand with me, and "
            "drive them off. The village wants the work, I know. But the grove won't grow back in our lifetimes.",
            ("I'll stand with you: the grove stays.", "@keep"), ("I'll hear Bramble out first.", "@hear"),
            ("Not now.", "@end")),
        ("End",),
        ("@hear",), ("Update.Attribute", "GroveQuest", "=1"), ("End",),
        ("@keep",), ("Update.Attribute", "GroveQuest", "=3"), ("Update.Attribute", "GroveCutters", "=0"),
        ("Quest.Note", "GroveQuest", "You've sided with Ranger Ash. Drive Bramble's woodcutters out of the old grove."),
        msg("You've sided with Ranger Ash. Bramble's woodcutters are in the old grove, south-east of the village."),
        ("End",),
        ("@grove2",), (">Conditional", "$Variable.3=2 or $Variable.3=4", "@grove3"),
        say("You'd let him have the grove? Then we've nothing to say to each other.", ("...", "@end")), ("End",),
        ("@grove3",), (">Conditional", "$Variable.3=3", "@grove5"),
        say("His woodcutters are in the grove, south-east of here. Send them home.", ("I'm going.", "@end")),
        ("End",),
        ("@grove5",), (">Conditional", "$Variable.3=5", "@grove6"),
        say("Gone? And not coming back, I'd wager. The grove's safe, friend, for as long as I live.\\My rangers will "
            "keep a lodge there now. There's a cot under the oaks with your name on it, and Ivy will sell you what "
            "grows there: herbs you'll not find anywhere else this side of the Elderwood.",
            ("Thank you, Ash.", "@kept")),
        ("@kept",), ("Update.Attribute", "GroveWay", "=2"), ("Update.Attribute", "GroveQuest", "=6"),
        ("Give.Item", "Gold_Coin(s)", "80"), ("Update.Skill", "Woodcutting", "+1"),
        msg("Quest complete: The Old Grove! The grove stands, and the rangers keep a lodge there."), ("End",),
        ("@grove6",), (">Conditional", "$Variable.4=1", "@grove_safe"),
        say("Stumps. Three hundred years of oak, and now stumps.", ("...", "@end")), ("End",),
        ("@grove_safe",), say("The grove's quiet, and the rangers' lodge is busy. The Wildwood thanks you.",
                              ("Goodbye.", "@end")), ("End",),
        ("@watch",), (">Conditional", "$Variable.1=0", "@w1"),
        (">Quest.Can.Start", "RangerQuest", "@green"),
        say("Well met. I'm Ash, warden of the Wildwood.\\Three old watch stones stand in these woods, and I can't "
            "leave the village to check them. Will you visit them for me?", ("I'll check the stones.", "@w_start"),
            ("Not now.", "@end")),
        ("End",),
        ("@w_start",), ("Update.Attribute", "RangerQuest", "=1"),
        ("Quest.Note", "RangerQuest", "Watch stone by the north road, between King Rupert's Keep and Oakhollow."),
        ("Quest.Note", "RangerQuest", "Watch stone in the western woods."),
        ("Quest.Note", "RangerQuest", "Watch stone east of the river."),
        msg("Quest started: The Wildwood Watch."), ("End",),
        ("@w1",), (">Conditional", "$Variable.1=1", "@w2"),
        say("One stone by the north road, one in the western woods, one by the river. Touch each one.",
            ("I'm on it.", "@end")), ("End",),
        ("@w2",), (">Conditional", "$Variable.1=2", "@w3"),
        say("All three stones? Then my fears are true: their moss is torn, webs everywhere.\\Spiders. A nest of them "
            "in the deep woods to the west. Clear it out: five of them, at least.", ("I'll deal with them.", "@nest"),
            ("Later.", "@end")),
        ("End",),
        ("@nest",), ("Update.Attribute", "RangerQuest", "=3"),
        ("Quest.Note", "RangerQuest", "The spider nest is in the deep woods west of Oakhollow."),
        ("Quest.Note", "RangerQuest", "Slay five giant spiders there."),
        msg("The Wildwood Watch: slay five giant spiders in the deep woods."), ("End",),
        ("@w3",), (">Conditional", "$Variable.1=3", "@quiet"), get("WildSpidersSlain", 2), (">Conditional", "$Variable.2>=5", "@five"),
        ("Update.Attribute", "RangerQuest", "=4"), ("Quest.Note.Done", "RangerQuest", "*"),
        ("Give.Item", "Gold_Coin(s)", "120"), ("Give.Item", "Yew_Staff", "1"), ("Update.Skill", "Woodcutting", "+2"),
        ("Update.Skill", "Strength", "+1"),
        say("The nest is gone? The woods will breathe easier. Take my old yew staff, and this gold. You've earned "
            "them.", ("Thank you!", "@paid")),
        ("@paid",), msg("Quest complete: The Wildwood Watch! You receive 120 gold, a yew staff and experience."),
        ("End",),
        ("@five",), say("Five spiders, friend. The nest is west of the village, deep in the trees.",
                        ("I'll keep at it.", "@end")), ("End",),
        ("@quiet",), say("The stones are quiet and the spiders are gone. The Wildwood thanks you.",
                         ("Goodbye.", "@end")), ("End",),
        ("@green",), say("The Wildwood eats the careless. Prove yourself to the King, and come back with a steadier "
                         "sword arm. Then I'll show you the trees.", ("Understood.", "@end")),
        ("@end",), ("End",),
    ]


def bramble():
    say = lambda text, *a: K.say("Merchant", text, *a)
    return [
        get("GroveQuest", 1), get("GroveWay", 2),
        (">Conditional", "$Variable.1<=1", "@b2"),
        (">Quest.Can.Start", "GroveQuest", "@trade"),
        say("Bramble, timber and planks. You look like someone who gets things done.\\There's a grove of old oaks "
            "south-east of the village: the best wood in the Wildwood, and Ash won't let a soul near it. My men are "
            "there now, waiting. Cut my mark into the great oak in the middle of it, and they'll take that as leave "
            "to start. There's 150 gold in it, and work for half this village.",
            ("I'll cut your mark: fell the grove.", "@fell"), ("I'll hear Ash out first.", "@hear"),
            ("Not now.", "@end")),
        ("End",),
        ("@hear",), ("Update.Attribute", "GroveQuest", "=1"), ("End",),
        ("@fell",), ("Update.Attribute", "GroveQuest", "=2"),
        ("Quest.Note", "GroveQuest", "You've sided with Master Bramble. Cut his mark into the great oak in the old "
                                     "grove, south-east of the village."),
        msg("You've sided with Master Bramble. The great oak is in the old grove, south-east of the village."),
        ("End",),
        ("@b2",), (">Conditional", "$Variable.1=2", "@b3"),
        say("The great oak, in the middle of the grove. You can't miss it: it's the size of a house.",
            ("I'm going.", "@end")), ("End",),
        ("@b3",), (">Conditional", "$Variable.1=3 or $Variable.1=5 or $Variable.2=2", "@b4"),
        say("Thrown in with Ash, have you? My men will remember that. Good day.", ("...", "@end")), ("End",),
        ("@b4",), (">Conditional", "$Variable.1=4", "@b6"),
        say("Marked? Then my men start at first light. Here's your 150, and my thanks.\\Tom will have a saw-pit going "
            "there by the week's end. Come by for planks: you'll pay what I pay.", ("Thank you, Master Bramble.",
                                                                                    "@felled")),
        ("@felled",), ("Update.Attribute", "GroveWay", "=1"), ("Update.Attribute", "GroveQuest", "=6"),
        ("Give.Item", "Gold_Coin(s)", "150"),
        msg("Quest complete: The Old Grove! Bramble's men are felling the grove, and his sawmill is open to you."),
        ("End",),
        ("@b6",), (">Conditional", "$Variable.2=1", "@trade"),
        say("The mill's busy, and so is half the village. That's your doing.", ("Goodbye.", "@end")), ("End",),
        ("@trade",), say("Timber and planks. Nothing for you just now.", ("Goodbye.", "@end")),
        ("@end",), ("End",),
    ]


def grove_entry():
    """The old grove: Bramble's woodcutters, for one who stands with Ash; stumps, for one who let him fell it."""
    cutter = "Attitude=Bad Zone=17,2,24,8 Chase=14,1,25,10"
    return [
        get("GroveWay", 1), (">Conditional", "$Variable.1=1", "@cutters"),
        ("Change.All.Tiles", "Oak_Tree001", "Tree_Stump001"), ("End",),
        ("@cutters",), get("GroveQuest", 2), (">Conditional", "$Variable.2=3", "@end"),
        get("GroveCutters", 3), (">Conditional", "$Variable.3<2", "@end"),
        ("Add.Entity", px(20, 7), "Woodcutter", "NPC", cutter),
        ("Add.Entity", px(22, 7), "Woodcutter", "NPC", cutter),
        msg("Bramble's woodcutters are in the grove, axes ready.", "Cyan"),
        ("@end",), ("End",),
    ]


def kill_woodcutter():
    return [
        get("GroveQuest", 1), (">Conditional", "$Variable.1=3", "@end"),
        get("GroveCutters", 2), (">Conditional", "$Variable.2<2", "@end"),
        ("Update.Attribute", "GroveCutters", "+1"),
        ("Get.Value", "CALCULATION", "$Variable.2+1", V(2)),
        (">Conditional", "$Variable.2<2", "@gone"),
        msg("One of Bramble's woodcutters runs for the village."), ("End",),
        ("@gone",), ("Update.Attribute", "GroveQuest", "=5"),
        ("Quest.Note", "GroveQuest", "Bramble's woodcutters are gone. Go back to Ranger Ash."),
        msg("Bramble's woodcutters are gone. Go back to Ranger Ash."),
        ("@end",), ("End",),
    ]


def blaze_oak():
    return [
        (">Distance.From.Clicked.Entity", "48", "@far"),
        get("GroveQuest", 1), (">Conditional", "$Variable.1=2", "@not"),
        ("Play.Sound", "Gather_Wood"), ("Update.Attribute", "GroveQuest", "=4"),
        ("Quest.Note", "GroveQuest", "The great oak bears Bramble's mark. Go back to him."),
        msg("You cut Bramble's mark deep into the great oak's bark. His men will take it as leave to start."),
        ("End",),
        ("@not",), msg("Three hundred years old, at least. It would be a shame to cut it.", "Cyan"), ("End",),
        ("@far",), msg("You are too far away!", "DarkRed", "Denied"),
        ("End",),
    ]


def scripts():
    K.write_script("Talk to Hob", hob(), MAKER)
    K.write_script("Talk to Captain", hale(), MAKER)
    K.write_script("Talk to Redrock_Steward", ambrose(), MAKER)
    K.write_script("Talk to Ambrose_At_Home", ambrose_at_home(), MAKER)
    K.write_script("Talk to Spleen_Parley", spleen(), MAKER)
    K.write_script("Talk to Galaith_Clerk_73", archivist(), MAKER)
    K.write_script("Talk to Galaith_Speaker_70", chancellor(), MAKER)
    K.write_script("Talk to Palace_Captain", hart(), MAKER)
    K.write_script("Talk to Chancellor_Sefton", sefton(), MAKER)
    K.write_script("Open Chancellors_Strongbox", strongbox(), MAKER)
    K.write_script("Open Galaith_Treasury", treasury(), MAKER)
    K.write_script("Talk to Ranger", ash(), MAKER)
    K.write_script("Talk to Timber_Merchant", bramble(), MAKER)
    K.write_script(GROVE, grove_entry(), MAKER)
    K.write_script("Kill Woodcutter", kill_woodcutter(), MAKER)
    K.write_script("Blaze Old_Grove_Oak", blaze_oak(), MAKER)
    K.write_script("Talk to Grove_Sawyer", [
        K.say("Carter", "Tom, Bramble's sawyer. Planks, cut this morning, at what the mill pays. Logs, if you'd "
                        "rather.", ("Show me.", "@shop"), ("Goodbye.", "@end")), ("End",),
        ("@shop",), ("Display.Item.Rack", "GENERAL", "Carter", "SHOP-Sawmill", "@end"),
        ("@end",), ("End",),
    ], MAKER)
    K.write_script("Talk to Grove_Warden", [
        K.say("Ranger", "Ivy, of Ash's rangers. Nightshade and marigold grow thick under these oaks, and nowhere else "
                        "near. Ash says you're to have what you need.", ("Show me.", "@shop"), ("Goodbye.", "@end")),
        ("End",),
        ("@shop",), ("Display.Item.Rack", "GENERAL", "Ranger", "SHOP-Rangers_Lodge", "@end"),
        ("@end",), ("End",),
    ], MAKER)


def main():
    art()
    data()
    place()
    scripts()
    print("Other choices: done")


if __name__ == "__main__":
    main()
