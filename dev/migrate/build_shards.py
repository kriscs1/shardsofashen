"""Shards: the world's magic, a balance each player has (shown under their health), in place of mana
(dsengine/shards.py does the counting).

What this sets, so the numbers live in one place each:
  * the Shard (its picture, for the balance and the journal: drawn by build_sprites.py, saved here; "Shard" given as
    an item goes on the balance);
  * data/Shards.ini, every Shard number in one place (only what's missing is added: edit them there):
    [Shards] a new character's, the grant for one from before Shards, the gap between casts, shardstones' costs
    (Shardstone.<Key>, else Shardstone; a journey after: Shardstone.Travel), chests' chance of a few;
    [Dismantle] the gold of value a Shard, by kind; [Upgrade.<Spell>] each rank's scroll and values;
    ([Remnants]: build_remnants.py);
  * Spells.ini: each spell's Cost (Shards) and Cooldown, and the violet potion's Shards (it gave mana);
  * the spell scrolls' words (read one to learn its spell for good);
  * monsters give no Shards themselves (their remnants do: build_remnants.py);
  * Digging.ini: Shards in a dug hole (more under the ground and in old places), and a rare cache;
  * Quests.ini Reward.Shards, Reward.Items and Reward.XP: what finishing a quest gives (once: shards.py, its reward
    screen);
  * spells' ranks: upgrade scrolls (Fire_Bolt_Scroll_II...) and each rank's values in Shards.ini (Damage.2...),
    some given by quests;
  * scrolls made rarer (once): fewer dropped by beasts, fewer in the shops, and dearer;
  * The Shard Scholar: Magister Quill of the Wizards' Court asks for fifteen Shards, and says what they are;
  * the dragon's words: the mountain's gold and its Shards (not its mana).

Safe to run again.

  python -I "dev\\migrate\\build_shards.py"
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import Ini, p                      # noqa: E402
import build_sprites as BS                     # noqa: E402
import sprite_kit as K                         # noqa: E402
import story_kit as SK                         # noqa: E402

MAKER = "build_shards.py"

SHARDS = [   # Shards.ini [Shards]
    ("Start", "12"), ("Old.Save.Grant", "20"), ("Cast.Gap", "0.8"),
    ("Shardstone", "5"), ("Shardstone.Wardhaven", "10"), ("Shardstone.Emberwatch", "10"), ("Shardstone.Frosthold", "10"),
    ("Shardstone.Dunerest", "10"), ("Shardstone.Saltmarsh", "10"), ("Shardstone.Galaith", "20"), ("Shardstone.Travel", "2"),
    ("Chest.Chance", "40"), ("Chest", "3-15"),
]
SHARDS_NOTE = ["; Start: a new character's Shards. Old.Save.Grant: given once to a character from before Shards.",
               "; Cast.Gap: seconds between any two casts.",
               "; Shardstone: waking a shardstone the first time (Shardstone.<Place>: one that costs more);",
               "; Shardstone.Travel: each journey after.",
               "; Chest.Chance in 100 that a chest's treasure has Chest=lo-hi Shards too.",
               "; Scrolls.Rarer: the builder's mark that scrolls were made rarer, once (leave it)."]
DISMANTLE = [("Weapon", "25"), ("Armour", "25"), ("Scroll", "10")]
DISMANTLE_NOTE = ["; Breaking things down (Dismantle, in the pack): a Shard for every <n> gold an item's worth, at least",
                  "; one. Weapon: anything wielded; Armour: anything worn; Scroll: a scroll whose spell you know already."]
HEADER = ["; Shards of Ashen: every Shard number in one place (dsengine/shards.py and remnants.py read it as the",
          "; game runs). Spells' own costs are Spells.ini Cost=; digging's Shards Digging.ini; quests' Quests.ini",
          "; Reward.Shards. dev\\migrate\\build_shards.py and build_remnants.py only add what's missing: edit them here."]

SPELLS = {   # spell: (Shards a cast, cooldown seconds[, other keys]) - five ideas of the brief, mapped onto these
    "Fire_Bolt": ("3", "1.5"),                 # (Magic Bolt: no faster, or it outdoes Lightning all game)
    "Ice_Bolt": ("6", "3"),
    "Lightning": ("10", "2", {"Damage": "10-20", "Chain": "1", "Chain.Range": "96", "Chain.Share": "50"}),
    # (Fireball: the bolt above Fire Bolt III; it leaps on to Chain more foes within Chain.Range, each hit at
    # Chain.Share percent: player_combat.py spell_hit)
    "Grasp": ("2", "2"),
    "Shard_Ward": ("10", "60"),
    "Frost_Nova": ("15", "8"),                 # (Frost Nova)
    "Thunderclap": ("18", "10"),
    "Blizzard": ("25", "15"),
    "Fire_Storm": ("30", "18", {"Damage": "9-18", "Radius": "160"}),   # (Meteor: the most damage, no ice)
}
RANKS = {   # spell: {rank: (its scroll, value, {its Spells.ini values at that rank})}
    # (a rank is never worse at anything but its Shards and the Channeling to learn it; more of what the spell is for;
    # more damage a Shard than the rank below; and never better than the next spell at its own job:
    # tests/test_engine.py test_every_spell_rank_is_plainly_better; a bolt's rank looks its own: Missile, drawn by
    # build_effects.py)
    "Fire_Bolt": {2: ("Fire_Bolt_Scroll_II", 60, {"Level": "4", "Damage": "4-9", "Cost": "4", "Cooldown": "1.4",
                                                     "Missile": "Fire_Bolt_Missile_II"}),
                  3: ("Fire_Bolt_Scroll_III", 140, {"Level": "8", "Damage": "6-12", "Cost": "5", "Cooldown": "1.3",
                                                       "Missile": "Fire_Bolt_Missile_III"})},
    "Ice_Bolt": {2: ("Ice_Bolt_Scroll_II", 110, {"Level": "9", "Damage": "4-10", "Slow": "35,10", "Cost": "8",
                                                   "Missile": "Ice_Bolt_Missile_II"})},
    "Lightning": {2: ("Lightning_Scroll_II", 220, {"Level": "14", "Damage": "14-28", "Cost": "13", "Cooldown": "1.5",
                                                   "Range": "384", "Chain": "2", "Missile": "Lightning_Missile_II"})},
    "Frost_Nova": {2: ("Frost_Nova_Scroll_II", 180, {"Level": "11", "Damage": "3-8", "Radius": "128", "Freeze": "7",
                                                     "Cost": "18"})},
    "Fire_Storm": {2: ("Fire_Storm_Scroll_II", 400, {"Level": "20", "Damage": "14-28", "Radius": "192", "Cost": "36"})},
    "Grasp": {2: ("Grasp_Scroll_II", 340, {"Level": "6", "Range": "320", "Cost": "3"})},   # (the Court's wizard sells it)
}
RANK_SHOPS = {"Grasp_Scroll_II": "SHOP-Wizard"}   # (an upgrade no quest gives: ItemRacks.ini, one in stock)
ROMAN = {2: "II", 3: "III"}
QUEST_ITEMS = {   # Quests.ini Reward.Items: upgrade scrolls for the harder quests
    "The Herbalist's Remedy": "Mega_Potion 3", "The Steward's Hunt": "Fire_Bolt_Scroll_II 1",
    "The Sunken Grimoire": "Ice_Bolt_Scroll_II 1", "The Ember Ring": "Lightning_Scroll_II 1",
    "Bert's Three Treasures": "Frost_Nova_Scroll_II 1", "The Barrow King": "Fire_Bolt_Scroll_III 1",
    "The Dragon of Galaith": "Fire_Storm_Scroll_II 1",
}
QUEST_XP = {   # Quests.ini Reward.XP: skill xp for finishing (as a script's Update.Skill +n), for the quests whose
    # scripts give none of their own
    "Dinner at Edwin's": "Cooking 2 Woodcutting 1", "The Amulet of Succession": "Attack 2 Defence 2 Crafting 1",
    "Passage to the Mainland": "Attack 2 Defence 2", "The Temporary Capital": "Channeling 1",
    "The Ashford Road": "Attack 3 Defence 3", "The Staff of Ashen": "Channeling 3",
    "The Sunken Grimoire": "Channeling 4", "The Ember Ring": "Channeling 4 Defence 3", "Bert's Three Treasures": "Channeling 6",
    "A Ship for Dragon Island": "Woodcutting 2 Crafting 2", "The Island of Dragons": "Attack 5 Defence 5",
    "The Sword of Valour": "Attack 6", "The Dragon of Galaith": "Attack 8 Defence 8 Channeling 4",
    "The Royal Guard": "Defence 4", "The True Heir": "Attack 5 Defence 5 Channeling 5",
    "Wolves of the Greyflats": "Attack 3", "Bandits on the Road": "Attack 3 Defence 2",
    "The Lost Caravan": "Defence 3", "The Wardhaven Bridge": "Homesteading 3", "Granny Wren's Walk": "Defence 1",
    "The Shard Scholar": "Channeling 2",
}
RARER = "Scrolls.Rarer"          # (Shards.ini [Shards]: set once they've been made rarer, so a second run doesn't again)
SCROLL_TAIL = "Right-click it and Cast, or use it on a monster."
SCROLL_NEW = "Learn it, and the spell is yours for good (the scroll is used up); cast it from Channeling."   # (as
# rare_scrolls.py left it: a scroll only teaches, one at a time, and an upgrade a quest gives is never for sale)

DIG = [("Shards.Chance", "5"), ("Shards", "1-3"), ("Shards.Underground.Chance", "15"), ("Shards.Underground", "1-5"),
       ("Cache.Chance", "0.5"), ("Cache", "6-12")]
DIG_PLACES = {"Sunscar_Desert": ("15", "1-5"), "Cinder_Peaks": ("15", "1-5")}   # (the buried library; the ash)
DIG_NOTE = ["; Shards, besides, in a hole dug: Shards.Chance in 100 of Shards=lo-hi; under the ground",
            "; Shards.Underground.Chance and Shards.Underground; a [Finds.<Place>] may say its own Shards.Chance and",
            "; Shards (old places: the desert's buried library, the ash). Cache.Chance in 100: a cache, Cache=lo-hi."]

REWARDS = {  # Quests.ini Reward.Shards
    "Dinner at Edwin's": 5, "The Amulet of Succession": 10, "Passage to the Mainland": 15,
    "The Temporary Capital": 10, "The Ashford Road": 15, "The Steward's Hunt": 20, "Bert's Three Treasures": 40,
    "The Staff of Ashen": 15, "The Sunken Grimoire": 20, "The Ember Ring": 25, "A Ship for Dragon Island": 15,
    "The Island of Dragons": 25, "The Sword of Valour": 30, "The Dragon of Galaith": 40, "The Royal Guard": 15,
    "The True Heir": 40,
    "The Herbalist's Remedy": 8, "The Dwarf's Grudge": 12, "The Wildwood Watch": 10, "Wolves of the Greyflats": 10,
    "Bog Lights": 15, "Bandits on the Road": 10, "The Lost Caravan": 12, "The Frozen Forge": 12,
    "The Hermit's Fire": 5, "The Withering Wood": 12, "The Barrow King": 25, "Old Hob": 10, "The Lost Patrol": 10,
    "A Place of Your Own": 8, "The Smugglers' Run": 12, "Granny Wren's Walk": 5, "A Portrait of Mo": 5,
    "The Wardhaven Bridge": 15, "The Dragonforge": 15,
}

QUILL = "Magister_Quill"
WIZARD = "Wizard"           # (who speaks: his sprite; the box names him)
LORE = {
    "what": "When the world was young, the Old Ones raised the shardstones and bound the land's magic into them. When "
            "the dragon came to Galaith's mountain it drank that magic down, and what it couldn't hold it shattered: "
            "Shards. They're everywhere now: in the earth, in the old places, in the beasts that swallow them.",
    "ways": "A shardstone is an Old One's door, and its rune sleeps until it's fed. A few Shards wake it, and once it "
            "knows you it remembers you: that's why you pay only the once. The far ones are hungrier.",
    "beasts": "Magic draws them, the way a fire draws moths. A wolf that's swallowed a Shard runs faster and bites "
              "harder, and when it dies the Shard falls out of it, for whoever picks it up. The "
              "worse the beast, the more it's eaten. And sometimes the magic won't die with it: it rises, all "
              "splinters and spite, and goes for whoever killed it.",
    "mountain": "And Galaith's mountain was the deepest seam of all. Your forefathers dug its gold, and its Shards, "
                "until the dragon came for them. It sits on them still.",
    "potions": "Shards reach out of you: they strike, freeze, carry things, carry you, or bind round you as a ward. "
               "What they can't do is get inside a living body. They'll never mend a wound or sharpen an eye.\\That's "
               "the brewer's art: herbs work from within, on whoever drinks them, and on nothing else. And no herb "
               "ever made a Shard.",
}


def rank_words(spell, keys):
    bits = []
    if "Damage" in keys:
        bits.append("%s damage" % keys["Damage"])
    if "Heal" in keys:
        bits.append("heals %s" % keys["Heal"])
    if "Freeze" in keys:
        bits.append("frozen for %s s" % keys["Freeze"])
    if "Radius" in keys:
        bits.append("over %d tiles" % (int(keys["Radius"]) // 32))
    if "Slow" in keys:
        bits.append("slowed to %s%% for %s s" % tuple(keys["Slow"].split(",")))
    if "Range" in keys:
        bits.append("reaching %d tiles" % (int(keys["Range"]) // 32))
    if "Chain" in keys:
        bits.append("leaping on to %s more foes" % keys["Chain"])
    if "Cooldown" in keys:
        bits.append("ready again after %s s" % keys["Cooldown"])
    return ", ".join(bits)


def ranks(ents, spells_ini, shards):
    """The upgrade scrolls (Entities.ini: Spell=, Rank=) and each rank's values (Shards.ini [Upgrade.<Spell>]
    Key.<rank>, Scroll.<rank>: moved there from Spells.ini, where they were first)."""
    for spell, by_rank in RANKS.items():
        sec = "Upgrade." + spell
        if shards.section(sec) is None:
            shards.section(sec, create=True)[1].append(
                (None, "; %s's ranks: Scroll.<rank> raises it to that rank; Key.<rank> is its Spells.ini Key from that "
                       "rank on." % spell.replace("_", " ")))
        for rank, (scroll, value, keys) in by_rank.items():
            name = spell.replace("_", " ") + " " + ROMAN[rank]
            for k, v in [("Scroll", scroll)] + list(keys.items()):
                key = "%s.%d" % (k, rank)
                old = spells_ini.get(spell, key)
                shards.set(sec, key, old if old is not None else v, overwrite=False)
                spells_ini.remove(spell, key)
            keys = {k: shards.get(sec, "%s.%d" % (k, rank)) for k in keys}            # (as they are now)
            sold = scroll in RANK_SHOPS                 # (else a quest's: never for sale)
            for k, v in (("Type", "MapItem"), ("Use.Words", "Learn"),
                         ("Examine.Info", "A scroll of %s: it raises %s, once you know it, to rank %d (%s). Channeling %s. "
                                          "Learn it to know it for good." % (name, spell.replace("_", " "), rank,
                                                                              rank_words(spell, keys), keys["Level"])),
                         ("Stackable", "1"), ("Value", str(value) if sold else "0"), ("Spell", spell),
                         ("Rank", str(rank))):
                ents.set(scroll, k, v)
            if not sold:
                ents.set(scroll, "Droppable", "0")


def rarer(ents, racks, shards):
    """Once: scrolls a third as likely from beasts, a quarter as many in shops, and twice the price."""
    if shards.get("Shards", RARER) == "1":
        return
    for sec, items in ents.sections:
        drops = ents.get(sec, "Drops") or ""
        if "_Scroll," in drops:
            parts = []
            for d in drops.split():
                f = d.split(",")
                if f[0].endswith("_Scroll") and len(f) == 3:
                    f[2] = str(max(1, int(round(float(f[2]) / 3))))
                parts.append(",".join(f))
            ents.set(sec, "Drops", " ".join(parts))
        if sec.endswith("_Scroll") and ents.get(sec, "Spell") and ents.get(sec, "Value"):
            ents.set(sec, "Value", str(int(float(ents.get(sec, "Value"))) * 2))
    for sec, items in racks.sections:
        if racks.get(sec, "Type") != "Shop":
            continue
        for i, (k, v) in enumerate(items):
            if k and k.startswith("Item") and v.split(",")[0].endswith("_Scroll"):
                name, stock = v.split(",")[:2]
                n = int(float(stock))
                items[i] = (k, "%s,%d" % (name, max(1, n // 4) if n > 0 else 0))
    shards.set("Shards", RARER, "1")


def entities():
    ents = Ini(p("data", "Entities.ini"))
    for k, v in (("Type", "MapItem"), ("Examine.Info", "A Shard: a splinter of the world's old magic, humming faintly. "
                                                       "Spells, shardstones and old things drink them."),
                 ("Stackable", "99999"), ("Value", "2"), ("Light", "24")):
        ents.set("Shard", k, v)
    ents.set("Fire_Storm_Scroll", "Examine.Info", "A scroll of Fire Storm: fire rains on every foe within five tiles "
                                                  "of you (9-18 damage). Channeling 15. " + SCROLL_NEW)
    ents.set("Magic_Potion", "Examine.Info", "A violet potion: it clears your head, and your spells do 5 more damage "
                                             "for two minutes.")    # (herbs can't make Shards: potions_and_spells.py)
    for sec, items in ents.sections:
        info = ents.get(sec, "Examine.Info") or ""
        for tail in (SCROLL_TAIL, "Right-click it and Cast."):        # (Homestead's said only that)
            if (ents.get(sec, "Spell") or "") and info.endswith(tail):
                info = info[:-len(tail)] + SCROLL_NEW
                ents.set(sec, "Examine.Info", info)
    shards = Ini(SHARDS_INI)
    spells_ini = Ini(p("data", "Spells.ini"))
    ranks(ents, spells_ini, shards)
    spells_ini.save(p("data", "Spells.ini"))
    racks = Ini(p("data", "ItemRacks.ini"))
    rarer(ents, racks, shards)
    for scroll, shop in RANK_SHOPS.items():           # (an upgrade sold, not given: one in stock)
        sec = racks.section(shop)
        if sec is not None and not any(k and k.startswith("Item") and v.split(",")[0] == scroll for k, v in sec[1]):
            n = 1 + max([int(k[4:]) for k, v in sec[1] if k and k.startswith("Item") and k[4:].isdigit()] or [0])
            racks.set(shop, "Item%d" % n, scroll + ",1")
    racks.save(p("data", "ItemRacks.ini"))
    ents.save(p("data", "Entities.ini"))
    shards.save(SHARDS_INI)


def spells():
    ini = Ini(p("data", "Spells.ini"))
    for spell, row in SPELLS.items():
        if ini.section(spell) is None:
            continue
        ini.set(spell, "Cost", row[0])
        ini.set(spell, "Cooldown", row[1])
        for k, v in (row[2] if len(row) > 2 else {}).items():
            ini.set(spell, k, v)
    ini.remove("Magic_Potion", "Mana")
    ini.header = ["; Spells, learnt for good by reading their scroll (an item with Spell=<section> and Use.Words=Cast),",
                  "; then cast for Cost Shards (dsengine/shards.py), each with its own Cooldown (seconds). Potions are",
                  "; drunk (Kind=Potion; Shards= puts that many in your pack). See dev\\Data Formats.md. Costs and",
                  "; cooldowns: dev\\migrate\\build_shards.py."]
    ini.save(p("data", "Spells.ini"))


SHARDS_INI = p("data", "Shards.ini")


def shards_ini():
    """Shards.ini's [Shards] and [Dismantle]: what's missing added; Config.ini's old [Shards] (where they were first)
    moved in, its values kept, and taken out of Config.ini."""
    ini = Ini(SHARDS_INI)
    ini.header = HEADER
    old = Ini(p("data", "Config.ini")).section("Shards")
    old = {k: v for k, v in old[1] if k is not None} if old else {}
    moved = {"Dismantle.Per": ("Dismantle", "Weapon"), "Dismantle.Scroll.Per": ("Dismantle", "Scroll")}
    for sec, rows, note in (("Shards", SHARDS + [(RARER, None)], SHARDS_NOTE), ("Dismantle", DISMANTLE, DISMANTLE_NOTE)):
        if ini.section(sec) is None:
            ini.section(sec, create=True)[1].extend((None, ln) for ln in note)
        for k, v in rows:
            was = old.get(k) or next((old[o] for o, (s2, k2) in moved.items() if (s2, k2) == (sec, k) and o in old),
                                     None)
            if was is not None or v is not None:
                ini.set(sec, k, was if was is not None else v, overwrite=False)
    if "Dismantle.Per" in old and ini.get("Dismantle", "Armour") == "25":
        ini.set("Dismantle", "Armour", old["Dismantle.Per"])
    ini.save(SHARDS_INI)
    if old:                                    # (out of Config.ini: Shards.ini is where they live now)
        SK.remove_section(SK.CONFIG, "Shards")


def digging():
    ini = Ini(p("data", "Digging.ini"))
    s = ini.section("Digging")
    s[1] = [(k, v) for k, v in s[1] if k not in dict(DIG) and not (k is None and "Shards" in v)]
    s[1] += [(None, ln) for ln in DIG_NOTE] + DIG
    for place, (chance, rng) in DIG_PLACES.items():
        if ini.section("Finds." + place) is not None:
            ini.set("Finds." + place, "Shards.Chance", chance)
            ini.set("Finds." + place, "Shards", rng)
    ini.save(p("data", "Digging.ini"))


def quests():
    ini = Ini(p("data", "Quests.ini"))
    for name, n in REWARDS.items():
        if ini.section(name) is not None:
            ini.set(name, "Reward.Shards", str(n))
    for name, items in QUEST_ITEMS.items():
        if ini.section(name) is not None:
            ini.set(name, "Reward.Items", items)
    for name, xp in QUEST_XP.items():
        if ini.section(name) is not None:
            ini.set(name, "Reward.XP", xp, overwrite=False)
    ini.save(p("data", "Quests.ini"))
    own = ("Giver", "Attribute", "Stage", "Done", "Marker", "Type", "Chapter", "Requires.")   # (what SK.quest writes)
    later = [(k, v) for k, v in (ini.section("The Shard Scholar") or (None, []))[1]
             if k and not k.startswith(own)]
    SK.quest("The Shard Scholar", WIZARD, "ShardQuest", {
        0: "Magister Quill, in the Wizards' Court's great hall, studies the Shards.",
        1: "Bring Magister Quill fifteen Shards for the Court's study (talk to him to give them)."}, 2,
        markers={0: "Court_Magister", 1: "Court_Magister"}, kind="Side", requires="Passage to the Mainland")
    SK.section(p("data", "Quests.ini"), "The Shard Scholar", [("Reward.XP", QUEST_XP["The Shard Scholar"])] +
               [kv for kv in later if kv[0] != "Reward.XP"])     # (what later builders added: its rumour, standing)
    lore = [("What are Shards?", "@what"), ("Why do the shardstones need them?", "@ways"),
            ("Why do beasts carry them?", "@beasts"), ("Spells or potions?", "@potions")]   # (the mountain: after what)
    rows = [
        ("Get.Value", "ATTRIBUTE", "ShardQuest", "Variable.1$"),
        (">Conditional", "$Variable.1=0", "@asked"),
        (">Quest.Can.Start", "ShardQuest", "@chat"),
        SK.say(WIZARD, "Shards! You've some in your pack: I can feel them humming from here.\\I'm Quill, Magister of "
                      "this Court, and I've spent forty years on what those splinters are. Bring me fifteen of them for "
                      "the Court's study and I'll pay you in something better than gold.",
               ("I'll bring you fifteen.", "@start"), ("What are Shards?", "@what"), ("Not now.", "@end")),
        ("@start",), ("Update.Attribute", "ShardQuest", "=1"),
        ("Display.Message", "Yellow", "Quest started: The Shard Scholar.", "Quest"),
        ("End",),
        ("@asked",), (">Conditional", "$Variable.1=1", "@chat"),
        SK.say(WIZARD, "Fifteen Shards for the study: have you brought them? You carry $Item.Shard.",
               ("Here: take fifteen.", "@give"), ("What are Shards?", "@what"), ("Not yet.", "@end")),
        ("@give",), (">Pay.Shards", "15", "The_Magister's_study", "@end"),
        ("Update.Attribute", "ShardQuest", "=2"),
        ("Play.Sound", "SpellCast"),
        ("Give.Item", "Frost_Nova_Scroll", "1"),
        SK.say(WIZARD, "Fifteen! Feel how they hum together... Here's my payment, as I promised: a scroll of Frost Nova, "
                      "written in my own hand. It drinks Shards like a shardstone does, and holds every foe round you in "
                      "ice. Read it and it's yours for good.", ("Thank you, Magister.", "@paid")),
        ("@paid",), ("Display.Message", "Yellow", "Quest complete: The Shard Scholar! You receive a scroll of Frost Nova.",
                     "Quest"),
        ("End",),
        ("@chat",), SK.say(WIZARD, "Ask, ask: a Magister who won't answer questions is just an old man in a hat.",
                           ("Tell me about Shards.", "@lore"),
                           ("About spellcraft... [if $Attr.ShardQuest>=2]", "@spellcraft"), ("Goodbye.", "@end")),
        ("@spellcraft",), ("Goto.Script", "Quill the Spellwright"),          # (build_spellwright.py)
        ("@lore",), SK.say(WIZARD, "What would you know?", *lore),
    ]
    for key, label in (("what", "@what"), ("ways", "@ways"), ("beasts", "@beasts"), ("mountain", "@mountain"),
                       ("potions", "@potions")):
        more = [("And Galaith's mountain?", "@mountain")] if key == "what" else []
        rows += [(label,), SK.say(WIZARD, LORE[key], *(more + [("Tell me more.", "@lore"), ("Thank you.", "@end")]))]
    rows += [("@end",), ("End",)]
    SK.write_script("Talk to Court_Magister", rows, MAKER)


def dragon():
    path = p("data", "Scripts", "The Dragon Speaks.script")
    text = open(path, "rb").read().decode("cp1252")
    old = "wanted the mountain's gold and its mana, and I let them have it"
    if old in text:
        open(path, "wb").write(text.replace(old, "wanted the mountain's gold and its Shards, and I let them have them")
                               .encode("cp1252"))


def main():
    for name in ["Shard"] + [sc for r in RANKS.values() for sc, _, _ in r.values()]:
        print(("wrote " if K.save("Entities", name, BS.SPRITES[name]()) else "unchanged ") + name)
    shards_ini()                               # (first: the rarity's once-only mark is kept in it)
    entities()
    spells()
    digging()
    quests()
    dragon()
    print("Shards: done")


if __name__ == "__main__":
    main()
