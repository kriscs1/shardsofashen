"""The last of Roadmap 6's standing (dev\\Roadmap-6.md groups 1 and 5): an Outlaw's gates shut at night, a door in each
town that opens to those it trusts, and a choice in the towns that had none.

  * Mirefold's huts open: each had a thin wall along its bottom row as well as its front wall below, so its door led
    nowhere (build_mirefen.py draws them right now).
  * The Court's gate and Wardhaven's are barred to an Outlaw of the town after dark ($World.Dark), and say why.
  * A house in each mainland town (not the Isle: every house there is the first quests') is locked to all but those
    the town trusts ($Standing.<Town>>=45), with a chest of the town's thanks inside, once each.
  * The Deserter (the Keep): Sergeant Brask wants the boy who ran from the levy. Tell him where Pip hides (the Keep
    +15), or pay Pip's way south on a carter's cart (the Keep -10; Pip turns up in Saltmarsh). (DeserterWay: 1, 2.)
  * The Dry Spring (Dunerest): Elder Sabra's spring has failed; Corvin the water-seller dammed it. Pull the dam down
    (Dunerest +15) or take Corvin's 100 gold to leave it (Dunerest -10). (WellWay: 1 the bribe, 2 the dam down.)
  * The Eel Traps (Saltmarsh): someone cuts Morwen's traps. It's Tobin, whose father's sick. Tell her (Saltmarsh +5,
    and her gold), or keep his secret, mend the traps and talk her into sharing her catch (Saltmarsh +15).
    (EelWay: 1 told, 2 kept.)
  * Marsh Fever (Mirefold): Bryony the healer wants to know what's in Doctor Pallister's cure. Swamp water. Take his
    cut to keep quiet (Mirefold -15), or run him out of the marsh (Mirefold +15; Bryony sells her fever tonic).
    (FeverWay: 1 his cut, 2 run out.)

Safe to run again.

  python -I "dev\\migrate\\build_town_choices.py"     (then validate.py, export_web_assets.py, build_minimaps.py)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_isle import Map, obj_line            # noqa: E402
import story_kit as K                           # noqa: E402

MAKER = "build_town_choices.py"
KEEP, KEEP_WOODS = "26,19,0", "25,20,0"
DUNEREST, SPRING = "3,21,0", "3,20,0"
SALTMARSH, SALT_EDGE = "11,23,0", "12,23,0"
MIREFOLD, MIRE_WALK = "-6,4,0", "-6,5,0"


def V(n):
    return "Variable.%d$" % n


def get(attr, n):
    return ("Get.Value", "ATTRIBUTE", attr, V(n))


def msg(text, colour="Yellow", sound=""):
    return ("Display.Message", colour, text) + ((sound,) if sound else ())


FAR = [("@far",), msg("You are too far away!", "DarkRed", "Denied"), ("End",)]


# ================================================================== the gates: barred to an Outlaw after dark
NIGHT = "The gate's barred for the night, and the watch on the wall knows your face. Come back by day."
GATES = {   # map: [(x, y, the closed tile, its condition, its message)]
    "21,5,0": [(12, 16, "City_Gate003", "$Standing.Court>=-60 or $World.Dark=0", NIGHT),
               (12, 17, "City_Gate001", "$Standing.Court>=-60 or $World.Dark=0", NIGHT)],
    "16,3,0": [(x, 3, "City_Gate001",
                "$Attr.WardhavenQuest>=3 and $Standing.Wardhaven>=-60 or $Attr.WardhavenQuest>=3 and $World.Dark=0",
                "The gates of Wardhaven are barred. Nobody answers from the wall. [if $Attr.WardhavenQuest<3] | " +
                NIGHT) for x in (13, 14)],
}


# ================================================================== the Trusted doors
TRUSTED = [  # (town, map, the door, the chest (its map if not the door's: a cellar), what the lock says, what the chest
             #  gives, what's said). The chest stands where it can't be reached through a wall (validate.py).
    ("Northport", "2,7,0", (12, 7), (13, 5), "The harbour pilots' house. They open it to friends of Northport, and "
     "nobody else.", [("Teleport_Scroll", 2), ("Wardbound_Sealskin_Boots", 1), ("Gold_Coin(s)", 150)],
     "The pilots' chest, and a note on top: \"For a friend of the harbour.\""),
    ("Ashford", "11,-1,0", (10, 7), (11, 5), "Locked. Whoever lives here likes it that way, and only opens it to "
     "friends of the town.", [("Major_Healing_Draught", 2), ("Emerald_Ring", 1), ("Gold_Coin(s)", 120)],
     "A chest, and a note in a careful hand: \"Ashford doesn't forget a friend.\""),
    ("Oakhollow", "9,11,0", (4, 15), (6, 13), "The old forester's door. Oakhollow keeps it for those it trusts.",
     [("Quiet_Draught", 3), ("Magic_Potion", 2), ("Gold_Coin(s)", 100)],
     "The forester's chest. The village has left you something in it."),
    ("Greyford", "13,8,0", (9, 17), (7, 14), "The miners' strongroom. Greyford opens it to friends, and keeps the key "
     "close.", [("Mithril_Bar", 2), ("Gold_Coin(s)", 150)],
     "The miners' chest: two bars of mithril, put by for a friend of Greyford."),
    ("Wildwood", "2,9,0", (18, 18), (19, 15), "Shut. The woodsfolk here open their doors to friends, and you're not "
     "one yet.", [("Major_Healing_Draught", 1), ("Quiet_Draught", 2), ("Gold_Coin(s)", 100)],
     "A chest under the bed, and a sprig of oak tied to its lid: Wildwood's thanks."),
    ("Thornwick", "20,14,0", (15, 8), (17, 5), "Locked. Thornwick's elders meet here, and only with friends.",
     [("Ruby_Ring", 1), ("Gold_Coin(s)", 150)], "The elders' chest. A ruby ring, and a word: \"With Thornwick's "
                                                "thanks.\""),
    ("Court", "19,4,0", (23, 20), (20, 17), "A wizard's door. The Court lets in those it trusts, and nobody else.",
     [("Shard_Ward_Scroll", 2), ("Magic_Potion", 2), ("Gold_Coin(s)", 150)],
     "A wizard's chest, and inside, scrolls sealed with the Court's mark."),
    ("Emberwatch", "26,5,0", (10, 14), (8, 11), "The watch's house. Emberwatch opens it to friends of the wall.",
     [("Ember_Tonic", 3), ("Wardbound_Steel_Helm", 1)], "The watch's chest: a helm and tonics, for a friend of the "
                                                         "wall."),
    ("Wardhaven", "17,2,0", (3, 15), (3, 13), "Barred. The folk of Wardhaven open their doors to friends, and you're "
     "not one yet.",
     [("Wardbound_Gold_Ring", 1), ("Gold_Coin(s)", 100)], "A Warden's chest, and a gold ring with their seal."),
    ("Keep", "25,20,0", (19, 7), ("25,20,-1", 15, 4), "The King's men's house. They open it to friends of the Keep.",
     [("Steel_Shield", 1), ("Gold_Coin(s)", 200)], "The garrison's chest: a steel shield, and the Keep's thanks."),
    ("Frosthold", "17,21,0", (13, 6), ("17,21,-1", 13, 3), "Locked. Frosthold's door is open to friends, and shut to the rest.",
     [("Mithril_Gauntlets", 1), ("Gold_Coin(s)", 100)], "A chest, and a pair of mithril gauntlets wrapped in fur."),
    ("Dunerest", "4,21,0", (3, 18), ("4,21,-1", 3, 16), "A merchant's house. Dunerest opens it to those it trusts.",
     [("Sapphire_Ring", 1), ("Gold_Coin(s)", 120)], "The merchant's chest, and a sapphire ring for a friend of "
                                                    "Dunerest."),
    ("Saltmarsh", "11,23,0", (17, 19), (18, 17), "The fishers' house. Saltmarsh opens it to friends.",
     [("Mega_Potion", 2), ("Gold_Coin(s)", 120)], "The fishers' chest. They've put by something for you."),
    ("Mirefold", "-6,4,0", (2, 15), (2, 13), "Shut. Mirefold's folk open their doors to friends of the marsh.",
     [("Fever_Tonic", 3), ("Major_Healing_Draught", 2), ("Gold_Coin(s)", 100)],
     "A chest, and in it tonics against the marsh fever, and more."),
    ("Galaith", "-10,16,0", (20, 6), ("-10,16,-1", 20, 3), "A noble's door. It opens to those Galaith trusts.",
     [("Teleport_Scroll", 2), ("Ruby", 1), ("Gold_Coin(s)", 250)],
     "A noble's chest, and in it a gift for a friend of the city."),
]


def trusted_id(town):
    return "Trusted_Chest_" + town


def trusted_attr(town):
    return "TrustedChest" + town


def trusted_chest(town, gives, words):
    a = trusted_attr(town)
    rows = [(">Distance.From.Clicked.Entity", "48", "@far"),
            get(a, 1), (">Conditional", "$Variable.1=0", "@empty"),
            ("Update.Attribute", a, "=1"), ("Play.Sound", "Chest")]
    rows += [("Give.Item", item, str(n)) for item, n in gives]
    rows += [msg(words), ("End",),
             ("@empty",), msg("The chest is empty: you've had what was left for you.", "Cyan", "Empty"), ("End",)]
    return rows + FAR


# ================================================================== kinds, shops, the quests
def art():
    K.copy_sprite("Entities", "Castaway_Cairn", "Spring_Dam")
    K.copy_sprite("Entities", "Full_Vial", "Pallisters_Cure")


KINDS = {
    "Spring_Dam": [("Type", "StaticObject"), ("Use.Words", "Break,Examine"),
                   ("Examine.Info", "Stones and sacking, packed across the spring's channel. Somebody brought them "
                                    "here on a cart.")],
    "Pallisters_Cure": [("Type", "MapItem"), ("Display.Name", "Pallister's Cure"), ("Use.Words", "Examine"),
                        ("Stackable", "1"), ("Droppable", "0"), ("Value", "0"),
                        ("Examine.Info", "A little bottle of Doctor Pallister's cure for the marsh fever. It's "
                                         "greenish, and smells of the marsh.")],
}

RACKS = {
    "SHOP-Mirefold_Healer": ["Type=Shop", "Buy.Rate=1.0", "Sell.Rate=0.6", "Specific=0", "Item1=Fever_Tonic,10",
                             "Item2=Healing_Draught,6", "Item3=Marigold,8"],
}

MAINLAND = "Passage to the Mainland"

DESERTER = ["Giver=Constable", "Attribute=DeserterQuest",
            "Stage0=Sergeant Brask, at the King's Keep, is looking for someone.",
            "Stage1=A boy called Pip has run from the Keep's levy. Sergeant Brask thinks he's hiding in the woods "
            "south of the Keep.",
            "Stage2=You found Pip in the woods south of the Keep. Tell Sergeant Brask.",
            "Done=3", "Marker0=Keep_Sergeant_Brask", "Marker1=Deserter_Pip", "Marker2=Keep_Sergeant_Brask",
            "Type=Side", "Requires.Quests=" + MAINLAND, "Reward.Shards=8", "Ending=DeserterWay",
            "Ending1=You told Sergeant Brask where Pip was hiding. The boy's back in the levy.",
            "Ending2=You paid Pip's way south on a carter's cart. The Keep is a deserter short, and Brask would like "
            "to know why.",
            "Reward.Standing1=Keep 15", "Reward.Standing2=Keep -10",
            "Rumour=They say a boy ran from the Keep's levy, and the sergeant's out for him."]

WELL = ["Giver=Elder", "Attribute=WellQuest",
        "Stage0=Elder Sabra of Dunerest is worried about the town's water.",
        "Stage1=The spring that feeds Dunerest's well has failed, and Corvin sells water by the cup. Elder Sabra "
        "wants to know why. The spring is north of the town.",
        "Stage2=Someone's dammed the spring north of Dunerest, and the stones came on Corvin's cart. Pull the dam "
        "down, or see what Corvin has to say.",
        "Stage3=The spring runs again. Tell Elder Sabra.",
        "Done=4", "Marker0=Dunerest_Elder_Sabra", "Marker1=Dunerest_Spring", "Marker2=Dunerest_Spring",
        "Marker3=Dunerest_Elder_Sabra", "Type=Side", "Requires.Quests=" + MAINLAND, "Reward.Shards=8",
        "Ending=WellWay",
        "Ending1=You took Corvin's gold to leave his dam be. Dunerest still buys its water by the cup.",
        "Ending2=You pulled down Corvin's dam, and the spring runs to Dunerest's well again.",
        "Reward.Standing1=Dunerest -10", "Reward.Standing2=Dunerest 15",
        "Rumour=Dunerest's well is low, they say, and Corvin the water-seller has never been richer."]

EELS = ["Giver=Woman", "Attribute=EelQuest",
        "Stage0=Morwen, an eel-catcher in Saltmarsh, has trouble with her traps.",
        "Stage1=Someone's been cutting Morwen's eel traps in the night. Find out who: the reeds east of the "
        "village are the place to look.",
        "Stage2=It's Tobin cutting Morwen's traps: his father's sick, and she took his trapping place. Tell Morwen.",
        "Stage3=You'll keep Tobin's secret. Bring Morwen 3 planks to mend her traps, and talk to her about Tobin's "
        "father.",
        "Done=4", "Marker0=Eel_Catcher_Morwen", "Marker1=Saltmarsh_Tobin", "Marker2=Eel_Catcher_Morwen",
        "Marker3=Eel_Catcher_Morwen", "Type=Side", "Requires.Quests=" + MAINLAND, "Reward.Shards=8",
        "Ending=EelWay",
        "Ending1=You told Morwen it was Tobin. His mother's sent him to an uncle inland.",
        "Ending2=You mended Morwen's traps, and she shares her catch with Tobin's father now.",
        "Reward.Standing1=Saltmarsh 5", "Reward.Standing2=Saltmarsh 15",
        "Rumour=Somebody's cutting the eel traps at Saltmarsh, they say."]

FEVER = ["Giver=Woman", "Attribute=FeverQuest",
         "Stage0=Bryony, Mirefold's healer, has her doubts about a doctor.",
         "Stage1=Half of Mirefold has the marsh fever, and they're buying a cure from Doctor Pallister on the "
         "boardwalk. Buy a bottle and bring it to Bryony.",
         "Stage2=You have a bottle of Pallister's cure. Bring it to Bryony.",
         "Stage3=Pallister's cure is swamp water and salt. Bryony wants him gone. He's on the boardwalk.",
         "Done=4", "Marker0=Mirefold_Healer_Bryony", "Marker1=Doctor_Pallister", "Marker2=Mirefold_Healer_Bryony",
         "Marker3=Doctor_Pallister", "Type=Side", "Requires.Quests=" + MAINLAND, "Reward.Shards=8",
         "Ending=FeverWay",
         "Ending1=You took Doctor Pallister's gold, and he still sells his cure in Mirefold.",
         "Ending2=You ran Doctor Pallister out of Mirefold. Bryony sells a real tonic now.",
         "Reward.Standing1=Mirefold -15", "Reward.Standing2=Mirefold 15",
         "Rumour=There's a doctor in Mirefold with a cure for the fever. Bryony the healer doesn't think much of it."]


def data():
    for name, keys in KINDS.items():
        K.section(K.ENTS, name, keys)
    for name, lines in RACKS.items():
        K.set_section(K.RACKS, name, lines)
    K.set_section(K.QUESTS, "The Deserter", DESERTER)
    K.set_section(K.QUESTS, "The Dry Spring", WELL)
    K.set_section(K.QUESTS, "The Eel Traps", EELS)
    K.set_section(K.QUESTS, "Marsh Fever", FEVER)


# ================================================================== where things are
def npc(kind, x, y, pid, name, more="", face="S"):
    return pid, obj_line("NPC", kind, x, y, "Attitude=Good Stand=1 Face=%s Id=%s Name=%s%s" % (
        face, pid, name, (" " + more) if more else ""), dy=-8)


PLACES = {   # map: [(Id, the line)]
    KEEP: [npc("Constable", 14, 9, "Keep_Sergeant_Brask", "Sergeant_Brask")],
    KEEP_WOODS: [npc("Villager", 13, 11, "Deserter_Pip", "Pip", "Here.After=DeserterQuest:1 "
                                                                 "Gone.After=DeserterQuest:3")],
    SALTMARSH: [npc("Woman", 16, 11, "Eel_Catcher_Morwen", "Morwen", face="W"),
                npc("Villager", 4, 12, "Saltmarsh_Pip", "Pip", "Here.After=DeserterWay:2")],
    SALT_EDGE: [npc("Villager", 5, 12, "Saltmarsh_Tobin", "Tobin", "Here.After=EelQuest:1 Gone.After=EelWay:1")],
    DUNEREST: [npc("Elder", 9, 12, "Dunerest_Elder_Sabra", "Elder_Sabra"),
               npc("Merchant", 17, 12, "Water_Seller_Corvin", "Corvin")],
    SPRING: [("Dunerest_Dam", obj_line("StaticObject", "Spring_Dam", 12, 8, "Id=Dunerest_Dam Here.After=WellQuest:1 "
                                                                            "Gone.After=WellDamDown:1"))],
    MIREFOLD: [npc("Woman", 7, 18, "Mirefold_Healer_Bryony", "Bryony")],   # (not a Herbalist: The Herbalist's Remedy asks for the one)
    MIRE_WALK: [npc("Doctor", 8, 6, "Doctor_Pallister", "Doctor_Pallister", "Gone.After=FeverWay:2")],
}
PLACE_IDS = {SPRING: [("Dunerest_Spring", 12, 9)]}


def lock_line(x, y, cond, message):
    return "Lock\t%d\t%d\t%s\t%s" % (x, y, cond, message)


def without_lock(m, x, y):
    K.ents_without(m, lambda f: f[0] == "Lock" and len(f) > 2 and f[1:3] == [str(x), str(y)])


MIREFOLD_MAPS = ("-7,4,0", "-6,4,0", "-5,4,0", "-7,5,0", "-6,5,0", "-5,5,0")
OPEN_BOTTOM = {"Timber_Thin_Plank007": "Timber_Thin_Plank004", "Timber_Thin_Plank003": "Plank001",
               "Timber_Thin_Plank006": "Timber_Thin_Plank002"}


def open_huts():
    """Mirefold's huts: a hut's bottom row is floor and side walls, as its front wall (below it) is its wall."""
    for name in MIREFOLD_MAPS:
        if not K.map_exists(name):
            continue
        m = Map(name)
        before = [list(r) for r in m.rows]
        for y in range(1, 21):
            for x in range(1, 26):
                if m.tile(x, y) in OPEN_BOTTOM and m.tile(x, y + 1) in ("Timber001", "Door001"):
                    m.set(x, y, tile=OPEN_BOTTOM[m.tile(x, y)])
        if m.rows != before:
            m.save()
            print("%s: huts opened" % name)


def chest_at(t):
    """(map, x, y) of a Trusted door's chest."""
    c = t[3]
    return c if len(c) == 3 else (t[1],) + tuple(c)


def place():
    names = set(PLACES) | set(PLACE_IDS) | set(GATES) | {t[1] for t in TRUSTED} | {chest_at(t)[0] for t in TRUSTED}
    names |= {"-6,5,0", "17,2,0"}                                   # (where Mirefold's and Wardhaven's were first)
    for name in sorted(names):
        m = Map(name)
        before = (list(m.ents), [list(r) for r in m.rows])
        for pid, line in PLACES.get(name, ()):
            K.ents_without(m, lambda f: ("Id=%s" % pid) in f[-1].split())
            m.ents.append(line)
        for pid, x, y in PLACE_IDS.get(name, ()):
            K.place_id(m, pid, x, y)
        for x, y, tile, cond, words in GATES.get(name, ()):
            m.set(x, y, tile=tile)                                  # (drawn shut: the lock draws it open)
            without_lock(m, x, y)
            m.ents.append(lock_line(x, y, cond, words))
        K.ents_without(m, lambda f: (f[0] == "Lock" and len(f) > 3 and f[3].startswith("$Standing.") and
                                     f[3].endswith(">=45")) or any(o.startswith("Id=Trusted_Chest_")
                                                                   for o in f[-1].split()))
        for t in TRUSTED:
            town, mp, (dx, dy), _, words, _, _ = t
            if mp == name:
                without_lock(m, dx, dy)
                m.ents.append(lock_line(dx, dy, "$Standing.%s>=45" % town, words))
            cm, cx, cy = chest_at(t)
            if cm == name:
                assert not m.decor(cx, cy), "%s: %s's chest on %s" % (name, town, m.decor(cx, cy))
                m.ents.append(obj_line("StaticObject", "Chest", cx, cy, "Lock=0 Id=" + trusted_id(town)))   # (left for you: not locked)
        if (m.ents, m.rows) != before:
            m.save()
            print("%s: placed" % name)


# ================================================================== the Deserter: Sergeant Brask, and Pip
def brask():
    say = lambda text, *a: K.say("Constable", text, *a)
    return [
        get("DeserterQuest", 1), (">Conditional", "$Variable.1=0", "@begun"),
        (">Quest.Can.Start", "DeserterQuest", "@busy"),
        say("Sergeant Brask, of the King's levy. A boy called Pip ran off three nights ago, spear and all. Farm boy. "
            "They're all farm boys.\\He'll be in the woods south of the Keep: they always are. Find him and tell me "
            "where. There's coin in it.", ("I'll look.", "@start"), ("Not my business.", "@end")),
        ("End",),
        ("@start",), ("Update.Attribute", "DeserterQuest", "=1"),
        ("Quest.Note", "DeserterQuest", "A boy called Pip has run from the Keep's levy. Sergeant Brask thinks he's "
                                        "hiding in the woods south of the Keep."),
        msg("Quest started: The Deserter."), ("End",),
        ("@begun",), (">Conditional", "$Variable.1<=2", "@done"),
        (">Conditional", "$Variable.1=2", "@looking"),
        ("Update.Attribute", "DeserterWay", "=1"),               # (first: the Keep hears which way it went)
        ("Update.Attribute", "DeserterQuest", "=3"), ("Quest.Note.Done", "DeserterQuest", "*"),
        ("Give.Item", "Gold_Coin(s)", "60"),
        ("Quest.Note", "DeserterQuest", "You told Sergeant Brask where Pip was hiding, and he paid you 60 gold."),
        say("In the woods south. I knew it. My men will have him back by supper.\\Here: 60 gold, the levy's price. "
            "The Keep won't forget you did your part.", ("Thank you, sergeant.", "@paid")),
        ("@paid",), msg("Quest complete: The Deserter! You receive 60 gold."), ("End",),
        ("@looking",), say("Any sign of the boy? The woods south of the Keep. Look under the trees.",
                           ("Still looking.", "@end")), ("End",),
        ("@done",), get("DeserterWay", 2), (">Conditional", "$Variable.2=2", "@thanks"),
        say("The boy's gone. Somebody paid his way south on a cart, the carters say. If I find out who...",
            ("Goodbye.", "@end")), ("End",),
        ("@thanks",), say("Pip's drilling with the rest of them. He'll make a soldier yet.", ("Goodbye.", "@end")),
        ("End",),
        ("@busy",), say("Move along. The levy's business is the levy's.", ("Goodbye.", "@end")),
        ("@end",), ("End",),
    ]


def pip():
    say = lambda text, *a: K.say("Villager", text, *a)
    return [
        get("DeserterQuest", 1), (">Conditional", "$Variable.1=1", "@told"),
        say("Don't shout! Please. Brask sent you, didn't he?\\I'm a farmer's boy. They gave me a spear and pointed me "
            "at trolls. Old Wat's cart goes south tomorrow, and for 40 gold he'd take me. Nobody need ever know.",
            ("Here's 40 gold. Go.", "@pay"), ("Brask will hear of this.", "@tell"), ("I'll think about it.",
                                                                                   "@end")),
        ("End",),
        ("@pay",), (">Got.Item", "Gold_Coin(s)", "40", "@poor"),
        ("Take.Item", "Gold_Coin(s)", "40"), ("Update.Attribute", "DeserterWay", "=2"),
        ("Update.Attribute", "DeserterQuest", "=3"), ("Quest.Note.Done", "DeserterQuest", "*"),
        ("Quest.Note", "DeserterQuest", "You paid Pip's way south on Old Wat's cart. Sergeant Brask will never know "
                                        "who."),
        say("You mean it? I'll never forget this. Never!", ("Go on, before I change my mind.", "@gone")),
        ("@gone",), msg("Quest complete: The Deserter. Pip's away south, and the Keep's a soldier short."), ("End",),
        ("@poor",), msg("You haven't 40 gold.", "DarkRed", "Denied"), ("End",),
        ("@tell",), ("Update.Attribute", "DeserterQuest", "=2"),
        ("Quest.Note", "DeserterQuest", "You found Pip in the woods south of the Keep. Tell Sergeant Brask."),
        msg("Pip goes white, and doesn't run. There's nowhere to run to.", "Red", "-"), ("End",),
        ("@told",), say("You're going to tell him. I know you are.", ("Here's 40 gold. Go.", "@pay"),
                        ("I'm sorry.", "@end")),
        ("@end",), ("End",),
    ]


def pip_saltmarsh():
    say = lambda text, *a: K.say("Villager", text, *a)
    return [
        say("It's you! I'm Pip still, but nobody here knows I was ever a soldier. I gut eels now. It's better than "
            "trolls.\\Here, it's not much, but it's what I've got.", ("Keep it, Pip.", "@keep"),
            ("Thank you.", "@take")), ("End",),
        ("@take",), get("PipsThanks", 1), (">Conditional", "$Variable.1=0", "@again"),
        ("Update.Attribute", "PipsThanks", "=1"), ("Give.Item", "Fish_Pie", "2"),
        msg("Pip gives you two fish pies."), ("End",),
        ("@again",), say("That's all I've got, honest.", ("I know. Look after yourself.", "@end")), ("End",),
        ("@keep",), say("You're a strange one. Thank you, though.", ("Goodbye, Pip.", "@end")),
        ("@end",), ("End",),
    ]


# ================================================================== the Dry Spring: Elder Sabra, Corvin, the dam
def sabra():
    say = lambda text, *a: K.say("Elder", text, *a)
    return [
        get("WellQuest", 1), (">Conditional", "$Variable.1=0", "@begun"),
        (">Quest.Can.Start", "WellQuest", "@busy"),
        say("The spring north of the town has fed our well since before there was a town. This spring it failed, "
            "and now Corvin sells us water by the cup.\\Springs don't just fail. Will you go and see?",
            ("I'll go.", "@start"), ("Not now.", "@end")), ("End",),
        ("@start",), ("Update.Attribute", "WellQuest", "=1"),
        ("Quest.Note", "WellQuest", "The spring that feeds Dunerest's well has failed. Elder Sabra wants to know "
                                    "why: it's north of the town."),
        msg("Quest started: The Dry Spring."), ("End",),
        ("@begun",), (">Conditional", "$Variable.1<=3", "@done"),
        (">Conditional", "$Variable.1=3", "@waiting"),
        ("Update.Attribute", "WellWay", "=2"), ("Update.Attribute", "WellQuest", "=4"),
        ("Quest.Note.Done", "WellQuest", "*"), ("Give.Item", "Gold_Coin(s)", "50"),
        ("Quest.Note", "WellQuest", "You pulled down Corvin's dam, and the spring runs to Dunerest's well again."),
        say("Corvin! Damming our spring to sell us our own water. Well, the well is filling, and the town knows "
            "who to thank.\\It's not much, but here's 50 gold from all of us.", ("Thank you, Elder.", "@paid")),
        ("@paid",), msg("Quest complete: The Dry Spring! You receive 50 gold."), ("End",),
        ("@waiting",), say("Have you been to the spring? It's north of the town, past the dunes.",
                           ("Not yet.", "@end")), ("End",),
        ("@done",), get("WellWay", 2), (">Conditional", "$Variable.2=1", "@water"),
        say("Still dry. Whatever you found up there, you never told me. Corvin's never looked happier.",
            ("Goodbye.", "@end")), ("End",),
        ("@water",), say("Clean water in the well, and no thanks to Corvin. Bless you.", ("Goodbye.", "@end")),
        ("End",),
        ("@busy",), say("The sand gets everywhere. Into the bread, into the beds.", ("Goodbye.", "@end")),
        ("@end",), ("End",),
    ]


def corvin():
    say = lambda text, *a: K.say("Merchant", text, *a)
    return [
        get("WellQuest", 1), get("WellWay", 2),
        (">Conditional", "$Variable.2=0", "@after"),
        (">Conditional", "$Variable.1<=2", "@ruined"),
        (">Conditional", "$Variable.1=2", "@plain"),
        say("You've been up at the spring. Don't look like that: I saw you on the dunes.\\Here's how it is. Leave the "
            "stones be, say the spring's dried up, and there's 100 gold in it for you. Water's a business, friend.",
            ("Done. Give me the gold.", "@bribe"), ("I'm pulling it down.", "@no")), ("End",),
        ("@bribe",), ("Update.Attribute", "WellWay", "=1"), ("Update.Attribute", "WellQuest", "=4"),
        ("Quest.Note.Done", "WellQuest", "*"), ("Give.Item", "Gold_Coin(s)", "100"),
        ("Quest.Note", "WellQuest", "You took Corvin's 100 gold to leave his dam be."),
        msg("Quest complete: The Dry Spring... Corvin counts 100 gold into your hand."), ("End",),
        ("@no",), say("Then you're a fool, and a thirsty one.", ("Goodbye.", "@end")), ("End",),
        ("@after",), (">Conditional", "$Variable.2=1", "@ruined"),
        say("A cup of water? A silver a cup. Prices are prices, friend.", ("Goodbye.", "@end")), ("End",),
        ("@ruined",), say("You pulled my dam down. Nobody buys water with a full well.", ("Goodbye.", "@end")),
        ("End",),
        ("@plain",), say("Water! Clean water, a silver a cup. Dunerest's well is dry, didn't you hear?",
                         ("Goodbye.", "@end")),
        ("@end",), ("End",),
    ]


def dam():
    return [
        (">Distance.From.Clicked.Entity", "48", "@far"),
        get("WellQuest", 1), get("WellWay", 2),
        (">Conditional", "$Variable.2=0", "@paid"),
        (">Conditional", "$Variable.1=2", "@first"),
        ("Update.Attribute", "WellDamDown", "=1"), ("Update.Attribute", "WellQuest", "=3"),   # (gone, for you)
        ("Play.Sound", "DigHole"), ("Quest.Note", "WellQuest", "The spring runs again. Tell Elder Sabra."),
        msg("You haul the stones aside and drag out the sacking. The spring runs again, down towards Dunerest."),
        ("End",),
        ("@first",), (">Conditional", "$Variable.1=1", "@end"),
        ("Update.Attribute", "WellQuest", "=2"),
        ("Quest.Note", "WellQuest", "Someone's dammed the spring north of Dunerest, and the stones came on Corvin's "
                                    "cart. Pull the dam down, or see what Corvin has to say."),
        msg("Stones and sacking, packed across the spring's channel, and cart tracks back to Dunerest: Corvin's cart, "
            "with his barrels on it."), ("End",),
        ("@paid",), msg("Corvin paid you to leave it be.", "DarkRed", "Denied"),
        ("@end",), ("End",),
    ] + FAR


# ================================================================== the Eel Traps: Morwen, and Tobin
def morwen():
    say = lambda text, *a: K.say("Woman", text, *a)
    return [
        get("EelQuest", 1), (">Conditional", "$Variable.1=0", "@begun"),
        (">Quest.Can.Start", "EelQuest", "@busy"),
        say("Three nights now, and every morning my eel traps are cut. Not torn: cut, with a knife.\\Find out who's "
            "doing it. The reeds east of the village, that's where they'd hide.", ("I'll find out.", "@start"),
            ("Not now.", "@end")), ("End",),
        ("@start",), ("Update.Attribute", "EelQuest", "=1"),
        ("Quest.Note", "EelQuest", "Someone's been cutting Morwen's eel traps in the night. The reeds east of "
                                   "Saltmarsh are the place to look."),
        msg("Quest started: The Eel Traps."), ("End",),
        ("@begun",), (">Conditional", "$Variable.1<=3", "@done"),
        (">Conditional", "$Variable.1>=2", "@looking"),
        (">Conditional", "$Variable.1=2", "@mend"),
        ("Update.Attribute", "EelWay", "=1"), ("Update.Attribute", "EelQuest", "=4"),
        ("Quest.Note.Done", "EelQuest", "*"), ("Give.Item", "Gold_Coin(s)", "60"),
        ("Quest.Note", "EelQuest", "You told Morwen it was Tobin cutting her traps. She paid you 60 gold."),
        say("Tobin? That little... His mother will hear of this, and so will the whole village.\\Here, 60 gold. "
            "You've earned it.", ("Thank you.", "@paid")),
        ("@paid",), msg("Quest complete: The Eel Traps! You receive 60 gold."), ("End",),
        ("@mend",), (">Got.Item", "Plank", "3", "@noplanks"),
        say("Planks? And you won't say who did it.\\...Tobin's father had this spot before me. When he took sick, I "
            "moved in. I've thought about that more than I'd like.", ("Share your catch with him.", "@share")),
        ("End",),
        ("@share",), ("Take.Item", "Plank", "3"), ("Update.Attribute", "EelWay", "=2"),
        ("Update.Attribute", "EelQuest", "=4"), ("Quest.Note.Done", "EelQuest", "*"),
        ("Quest.Note", "EelQuest", "You mended Morwen's traps, and she'll share her catch with Tobin's father."),
        say("Half the catch, till he's on his feet. And whoever was cutting my traps can stop now, can't they?",
            ("I think they will.", "@kind")),
        ("@kind",), msg("Quest complete: The Eel Traps! Morwen's traps are mended, and Tobin's father eats tonight."),
        ("End",),
        ("@noplanks",), say("Planks for the traps: three of them. You'll find them at any sawmill or carpenter's.",
                            ("I'll bring them.", "@end")), ("End",),
        ("@looking",), say("Any sign of who's cutting them? Try the reeds east of the village.",
                           ("Still looking.", "@end")), ("End",),
        ("@done",), say("The traps are full every morning now. Eels for the market, and some over.",
                        ("Goodbye.", "@end")), ("End",),
        ("@busy",), say("Eels! Fresh this morning!", ("Goodbye.", "@end")),
        ("@end",), ("End",),
    ]


def tobin():
    say = lambda text, *a: K.say("Villager", text, *a)
    return [
        get("EelQuest", 1), (">Conditional", "$Variable.1=1", "@after"),
        say("All right! It was me! I cut her traps.\\Da had this spot for twenty years. He took sick, and Morwen moved "
            "in before he was cold in his bed. He's not dead, but he might as well be, for all she cares.",
            ("I'll have to tell Morwen.", "@tell"), ("Your secret's safe. I'll talk to her.", "@keep")), ("End",),
        ("@tell",), ("Update.Attribute", "EelQuest", "=2"),
        ("Quest.Note", "EelQuest", "It's Tobin cutting Morwen's traps: his father's sick, and she took his trapping "
                                   "place. Tell Morwen."),
        msg("Tobin stares at you, then runs off into the reeds.", "Red", "-"), ("End",),
        ("@keep",), ("Update.Attribute", "EelQuest", "=3"),
        ("Quest.Note", "EelQuest", "You'll keep Tobin's secret. Bring Morwen 3 planks to mend her traps, and talk "
                                   "to her about Tobin's father."),
        say("You'd do that? I won't cut them again. I swear it.", ("See that you don't.", "@end")), ("End",),
        ("@after",), get("EelWay", 2), (">Conditional", "$Variable.2<2", "@thanks"),
        say("Well? Have you been to Morwen?", ("Soon.", "@end")), ("End",),
        ("@thanks",), say("Morwen brought Da eels last night! Half her catch. I don't know what you said to her.",
                          ("Look after him.", "@end")),
        ("@end",), ("End",),
    ]


# ================================================================== Marsh Fever: Bryony, and Doctor Pallister
def bryony():
    say = lambda text, *a: K.say("Woman", text, *a)
    return [
        get("FeverQuest", 1), (">Conditional", "$Variable.1=0", "@begun"),
        (">Quest.Can.Start", "FeverQuest", "@busy"),
        say("Bryony, the healer here, for what it's worth. Half of Mirefold has the marsh fever, and none of them "
            "come to me now. They buy Doctor Pallister's cure on the boardwalk.\\If it works, I'll be glad. Buy me a "
            "bottle, and I'll tell you what's in it.", ("I'll buy one.", "@start"), ("Not now.", "@end")),
        ("End",),
        ("@start",), ("Update.Attribute", "FeverQuest", "=1"),
        ("Quest.Note", "FeverQuest", "Half of Mirefold has the marsh fever, and they're buying a cure from Doctor "
                                     "Pallister on the boardwalk. Buy a bottle and bring it to Bryony."),
        msg("Quest started: Marsh Fever."), ("End",),
        ("@begun",), (">Conditional", "$Variable.1<=3", "@done"),
        (">Conditional", "$Variable.1<3", "@goaway"),
        (">Got.Item", "Pallisters_Cure", "1", "@nocure"),
        ("Take.Item", "Pallisters_Cure", "1"), ("Update.Attribute", "FeverQuest", "=3"),
        ("Quest.Note", "FeverQuest", "Pallister's cure is swamp water and salt. Bryony wants him gone: he's on the "
                                     "boardwalk."),
        say("Let me see. Swamp water. Salt, a little green from the reeds. That's all.\\He's selling them the marsh "
            "in a bottle. Make him go, before somebody dies trusting it.", ("I'll see to him.", "@end")), ("End",),
        ("@nocure",), say("A bottle of Pallister's cure. He's on the boardwalk, south of here.",
                          ("I'll get one.", "@end")), ("End",),
        ("@goaway",), say("Is he gone yet? The boardwalk, south.", ("Not yet.", "@end")), ("End",),
        ("@done",), get("FeverWay", 2), (">Conditional", "$Variable.2=1", "@shop"),
        say("He's still selling it, and they still buy it. I don't know what you said to him.", ("Goodbye.", "@end")),
        ("End",),
        ("@shop",), say("They come to me again now. Fever tonic, the real thing: willow bark and marigold.",
                        ("Show me.", "@rack"), ("Goodbye.", "@end")), ("End",),
        ("@rack",), ("Display.Item.Rack", "GENERAL", "Woman", "SHOP-Mirefold_Healer", "@end"), ("End",),
        ("@busy",), say("Mind the mosquitoes. They bring the fever.", ("Goodbye.", "@end")),
        ("@end",), ("End",),
    ]


def pallister():
    say = lambda text, *a: K.say("Doctor", text, *a)
    return [
        get("FeverQuest", 1),
        (">Conditional", "$Variable.1>=1 and $Variable.1<=2", "@not_selling"),
        get("FeverCureBought", 2), (">Conditional", "$Variable.2=0", "@sold"),
        say("Doctor Pallister's cure for the marsh fever! A bottle a day, and the fever flees. 20 gold, and cheap at "
            "the price.", ("I'll take one.", "@buy"), ("No thank you.", "@end")), ("End",),
        ("@buy",), (">Got.Item", "Gold_Coin(s)", "20", "@poor"),
        ("Take.Item", "Gold_Coin(s)", "20"), ("Give.Item", "Pallisters_Cure", "1"),
        ("Update.Attribute", "FeverCureBought", "=1"), ("Update.Attribute", "FeverQuest", "=2"),
        ("Quest.Note", "FeverQuest", "You have a bottle of Pallister's cure. Bring it to Bryony."),
        msg("You buy a bottle of Pallister's cure."), ("End",),
        ("@poor",), msg("You haven't 20 gold.", "DarkRed", "Denied"), ("End",),
        ("@sold",), say("A bottle a day, friend! Come back when you need another.", ("Goodbye.", "@end")), ("End",),
        ("@not_selling",), (">Conditional", "$Variable.1=3", "@plain"),
        say("Bryony sent you? That witch. Look: what they buy, they believe in, and believing does them good.\\80 "
            "gold, and you tell her it's a fine tonic. Everyone's happy.", ("Done.", "@bribe"),
            ("Get out of Mirefold.", "@out")), ("End",),
        ("@bribe",), ("Update.Attribute", "FeverWay", "=1"), ("Update.Attribute", "FeverQuest", "=4"),
        ("Quest.Note.Done", "FeverQuest", "*"), ("Give.Item", "Gold_Coin(s)", "80"),
        ("Quest.Note", "FeverQuest", "You took Doctor Pallister's 80 gold to say nothing."),
        msg("Quest complete: Marsh Fever... Pallister counts 80 gold into your hand, smiling."), ("End",),
        ("@out",), ("Update.Attribute", "FeverWay", "=2"), ("Update.Attribute", "FeverQuest", "=4"),
        ("Quest.Note.Done", "FeverQuest", "*"),
        ("Quest.Note", "FeverQuest", "You ran Doctor Pallister out of Mirefold. Bryony will sell a real tonic now."),
        msg("Pallister packs his bottles in a hurry, and is gone down the boardwalk."),
        msg("Quest complete: Marsh Fever!"), ("End",),
        ("@plain",), say("Doctor Pallister's cure! Healthy folk needn't trouble themselves. Yet.",
                         ("Goodbye.", "@end")),
        ("@end",), ("End",),
    ]


def scripts():
    for town, _, _, _, _, gives, words in TRUSTED:
        K.write_script("Open " + trusted_id(town), trusted_chest(town, gives, words), MAKER)
    K.write_script("Talk to Keep_Sergeant_Brask", brask(), MAKER)
    K.write_script("Talk to Deserter_Pip", pip(), MAKER)
    K.write_script("Talk to Saltmarsh_Pip", pip_saltmarsh(), MAKER)
    K.write_script("Talk to Dunerest_Elder_Sabra", sabra(), MAKER)
    K.write_script("Talk to Water_Seller_Corvin", corvin(), MAKER)
    K.write_script("Break Dunerest_Dam", dam(), MAKER)
    K.write_script("Talk to Eel_Catcher_Morwen", morwen(), MAKER)
    K.write_script("Talk to Saltmarsh_Tobin", tobin(), MAKER)
    K.write_script("Talk to Mirefold_Healer_Bryony", bryony(), MAKER)
    K.write_script("Talk to Doctor_Pallister", pallister(), MAKER)


def main():
    open_huts()
    art()
    data()
    place()
    scripts()
    print("Town choices: done")


if __name__ == "__main__":
    main()
