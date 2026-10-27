"""Shards: the world's magic, a balance each player has (shown under their health), in place of mana
(dsengine/shards.py does the counting).

What this sets, so the numbers live in one place each:
  * the Shard (its picture, for the balance and the journal: drawn by build_sprites.py, saved here; "Shard" given as
    an item goes on the balance);
  * Config.ini [Shards]: a new character's, the grant for one from before Shards, the gap between casts, waystones'
    costs (Waystone.<Key>, else Waystone; a journey after: Waystone.Travel), chests' chance of a few;
  * Spells.ini: each spell's Cost (Shards) and Cooldown, and the violet potion's Shards (it gave mana);
  * the spell scrolls' words (read one to learn its spell for good);
  * Entities.ini Drops: the hostile creatures' Shards, by how tough they are (prey and townsfolk none);
  * Digging.ini: Shards in a dug hole (more under the ground and in old places), and a rare cache;
  * Quests.ini Reward.Shards and Reward.Items: what finishing a quest gives (once: shards.py, its reward screen);
  * spells' ranks: upgrade scrolls (Fire_Bolt_Scroll_II...) and each rank's values in Spells.ini (Damage.2...),
    some given by quests;
  * scrolls made rarer (once): fewer dropped by beasts, fewer in the shops, and dearer;
  * dismantling: Config [Shards] Dismantle.Per (gold of value a Shard) and Dismantle.Scroll.Per;
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

CONFIG = [   # Config.ini [Shards]
    ("Start", "12"), ("Old.Save.Grant", "20"), ("Cast.Gap", "0.8"),
    ("Waystone", "5"), ("Waystone.Wardhaven", "10"), ("Waystone.Emberwatch", "10"), ("Waystone.Frosthold", "10"),
    ("Waystone.Dunerest", "10"), ("Waystone.Saltmarsh", "10"), ("Waystone.Galaith", "20"), ("Waystone.Travel", "2"),
    ("Chest.Chance", "40"), ("Chest", "3-15"), ("Dismantle.Per", "25"), ("Dismantle.Scroll.Per", "10"),
]
CONFIG_NOTE = ["; Shards (dsengine/shards.py), the world's magic: a balance each player has. Start: a new character's.",
               "; Old.Save.Grant: given once to a character from before Shards. Cast.Gap: seconds between any two casts.",
               "; Waystone.<Key>: waking that waystone the first time (else Waystone); Waystone.Travel: each journey.",
               "; Chest.Chance in 100 that a chest's treasure has Chest=lo-hi Shards too. Dismantling gives a Shard",
               "; for every Dismantle.Per gold an item's worth (Dismantle.Scroll.Per for a scroll you know already).",
               "; Spells cost Spells.ini Cost=; monsters drop them (Entities.ini Drops); digging: Digging.ini;",
               "; quests give Quests.ini Reward.Shards. Written by dev\\migrate\\build_shards.py."]

SPELLS = {   # spell: (Shards a cast, cooldown seconds[, other keys]) - five ideas of the brief, mapped onto these
    "Fire_Bolt": ("3", "0.8"),                 # (Magic Bolt)
    "Ice_Bolt": ("6", "3"),
    "Lightning": ("10", "4"),                  # (Fireball)
    "Healing": ("6", "6"),
    "Grasp": ("2", "2"),
    "Farsight": ("6", "30"),
    "Stone_Skin": ("10", "60"),
    "Teleport_Home": ("12", "60"),             # (Blink: the one that moves you)
    "Frost_Nova": ("15", "8"),                 # (Frost Nova)
    "Thunderclap": ("18", "10"),
    "Blizzard": ("25", "15"),
    "Fire_Storm": ("30", "18", {"Damage": "9-18", "Radius": "160"}),   # (Meteor: the most damage, no ice)
}
RANKS = {   # spell: {rank: (its scroll, value, {its Spells.ini values at that rank})}
    "Fire_Bolt": {2: ("Fire_Bolt_Scroll_II", 60, {"Level": "8", "Damage": "4-9", "Cost": "4"}),
                  3: ("Fire_Bolt_Scroll_III", 140, {"Level": "16", "Damage": "7-13", "Cost": "5"})},
    "Healing": {2: ("Healing_Scroll_II", 80, {"Level": "12", "Heal": "16-26", "Cost": "8"})},
    "Ice_Bolt": {2: ("Ice_Bolt_Scroll_II", 110, {"Level": "18", "Damage": "4-10", "Slow": "35,10", "Cost": "8"})},
    "Lightning": {2: ("Lightning_Scroll_II", 220, {"Level": "28", "Damage": "10-22", "Cost": "14"})},
    "Frost_Nova": {2: ("Frost_Nova_Scroll_II", 180, {"Level": "22", "Damage": "3-8", "Radius": "128", "Freeze": "7",
                                                     "Cost": "18"})},
    "Fire_Storm": {2: ("Fire_Storm_Scroll_II", 400, {"Level": "40", "Damage": "14-28", "Cost": "36"})},
}
ROMAN = {2: "II", 3: "III"}
QUEST_ITEMS = {   # Quests.ini Reward.Items: upgrade scrolls for the harder quests
    "The Herbalist's Remedy": "Healing_Scroll_II 1", "The Steward's Hunt": "Fire_Bolt_Scroll_II 1",
    "The Sunken Grimoire": "Ice_Bolt_Scroll_II 1", "The Ember Ring": "Lightning_Scroll_II 1",
    "Bert's Three Treasures": "Frost_Nova_Scroll_II 1", "The Barrow King": "Fire_Bolt_Scroll_III 1",
    "The Dragon of Galaith": "Fire_Storm_Scroll_II 1",
}
RARER = "Scrolls.Rarer"          # (Config [Shards]: set once they've been made rarer, so a second run doesn't again)
SCROLL_TAIL = "Right-click it and Cast, or use it on a monster."
SCROLL_NEW = "Read it to learn the spell for good; casting it then costs Shards (the journal's Spells)."

WEAK, STRONG, ELITE, BOSS = "Shard,1-3,30", "Shard,4-10,35", "Shard,10-25,60", "Shard,10-25,100"

DIG = [("Shards.Chance", "5"), ("Shards", "1-3"), ("Shards.Underground.Chance", "15"), ("Shards.Underground", "1-5"),
       ("Cache.Chance", "0.5"), ("Cache", "6-12")]
DIG_PLACES = {"Sunscar_Desert": ("15", "1-5"), "Cinder_Peaks": ("15", "1-5")}   # (the buried library; the ash)
DIG_NOTE = ["; Shards, besides, in a hole dug: Shards.Chance in 100 of Shards=lo-hi; under the ground",
            "; Shards.Underground.Chance and Shards.Underground; a [Finds.<Place>] may say its own Shards.Chance and",
            "; Shards (old places: the desert's buried library, the ash). Cache.Chance in 100: a cache, Cache=lo-hi."]

REWARDS = {  # Quests.ini Reward.Shards
    "Dinner at the Bank": 5, "The Amulet of Succession": 10, "Passage to the Mainland": 15,
    "The Temporary Capital": 10, "The Ashford Road": 15, "The Steward's Hunt": 20, "Bert's Three Treasures": 40,
    "The Staff of Estforlan": 15, "The Sunken Grimoire": 20, "The Ember Ring": 25, "A Ship for Dragon Island": 15,
    "The Island of Dragons": 25, "The Sword of Valour": 30, "The Dragon of Galaith": 40, "The Royal Guard": 15,
    "The True Heir": 40,
    "The Herbalist's Remedy": 8, "The Dwarf's Grudge": 12, "The Wildwood Watch": 10, "Wolves of the Moor": 10,
    "Bog Lights": 15, "Bandits on the Road": 10, "The Lost Caravan": 12, "The Frozen Forge": 12,
    "The Hermit's Fire": 5, "The Withering Wood": 12, "The Barrow King": 25, "Old Hob": 10, "The Lost Patrol": 10,
    "A Place of Your Own": 8, "The Smugglers' Run": 12, "Granny Wren's Walk": 5, "A Portrait of Mo": 5,
    "The Wardhaven Bridge": 15, "The Dragonforge": 15,
}

QUILL = "Magister_Quill"
WIZARD = "Wizard"           # (who speaks: his sprite; the box names him)
LORE = {
    "what": "When the world was young, the Old Ones raised the waystones and bound the land's magic into them. When "
            "the dragon came to Galaith's mountain it drank that magic down, and what it couldn't hold it shattered: "
            "Shards. They're everywhere now: in the earth, in the old places, in the beasts that swallow them.",
    "ways": "A waystone is an Old One's door, and its rune sleeps until it's fed. A few Shards wake it, and once it "
            "knows you it remembers you: that's why you pay only the once. The far ones are hungrier.",
    "beasts": "Magic draws them, the way a fire draws moths. A wolf that's swallowed a Shard runs faster and bites "
              "harder, and when it dies, the Shard's still in it. The worse the beast, the more it's eaten.",
    "mountain": "And Galaith's mountain was the deepest seam of all. Your forefathers dug its gold, and its Shards, "
                "until the dragon came for them. It sits on them still.",
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
    return ", ".join(bits)


def ranks(ents, spells_ini):
    """The upgrade scrolls (Entities.ini: Spell=, Rank=) and each rank's values (Spells.ini Key.<rank>, Scroll.<rank>)."""
    for spell, by_rank in RANKS.items():
        for rank, (scroll, value, keys) in by_rank.items():
            name = spell.replace("_", " ") + " " + ROMAN[rank]
            for k, v in (("Type", "MapItem"), ("Use.Words", "Cast"),
                         ("Examine.Info", "A scroll of %s: it raises %s, once you know it, to rank %d (%s). Magic %s. "
                                          "Read it to learn it for good." % (name, spell.replace("_", " "), rank,
                                                                              rank_words(spell, keys), keys["Level"])),
                         ("Stackable", "10"), ("Value", str(value)), ("Spell", spell), ("Rank", str(rank))):
                ents.set(scroll, k, v)
            spells_ini.set(spell, "Scroll.%d" % rank, scroll)
            for k, v in keys.items():
                spells_ini.set(spell, "%s.%d" % (k, rank), v)


def rarer(ents, racks, config):
    """Once: scrolls a third as likely from beasts, a quarter as many in shops, and twice the price."""
    if config.get("Shards", RARER) == "1":
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
    SK.section(SK.CONFIG, "Shards", [(RARER, "1")])


def entities():
    ents = Ini(p("data", "Entities.ini"))
    for k, v in (("Type", "MapItem"), ("Examine.Info", "A Shard: a splinter of the world's old magic, humming faintly. "
                                                       "Spells, waystones and old things drink them."),
                 ("Stackable", "99999"), ("Value", "2"), ("Light", "24")):
        ents.set("Shard", k, v)
    ents.set("Fire_Storm_Scroll", "Examine.Info", "A scroll of Fire Storm: fire rains on every foe within five tiles "
                                                  "of you (9-18 damage). Magic 30. " + SCROLL_NEW)
    ents.set("Magic_Potion", "Examine.Info", "A violet potion: your spells do 5 more damage for two minutes, and its "
                                             "magic settles into 10 Shards in your pack.")
    for sec, items in ents.sections:
        info = ents.get(sec, "Examine.Info") or ""
        if (ents.get(sec, "Spell") or "") and SCROLL_TAIL in info:
            ents.set(sec, "Examine.Info", info.replace(SCROLL_TAIL, SCROLL_NEW))
        if (ents.get(sec, "Type") or "") != "NPC" or (ents.get(sec, "Attitude") or "") != "Bad" or \
                (ents.get(sec, "Flees") or "") == "1":
            continue
        hp = float(ents.get(sec, "Hitpoints") or 0)
        respawn = float(ents.get(sec, "Respawn") or 0)
        drop = WEAK if hp <= 15 else STRONG if hp < 60 else BOSS if respawn >= 900 else ELITE
        drops = re.sub(r"\s*Shard,\S+", "", ents.get(sec, "Drops") or "").strip()
        ents.set(sec, "Drops", (drops + " " + drop).strip())
    spells_ini = Ini(p("data", "Spells.ini"))
    ranks(ents, spells_ini)
    spells_ini.save(p("data", "Spells.ini"))
    racks = Ini(p("data", "ItemRacks.ini"))
    rarer(ents, racks, Ini(p("data", "Config.ini")))
    racks.save(p("data", "ItemRacks.ini"))
    ents.save(p("data", "Entities.ini"))


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
    ini.set("Magic_Potion", "Shards", "10")
    ini.header = ["; Spells, learnt for good by reading their scroll (an item with Spell=<section> and Use.Words=Cast),",
                  "; then cast for Cost Shards (dsengine/shards.py), each with its own Cooldown (seconds). Potions are",
                  "; drunk (Kind=Potion; Shards= puts that many in your pack). See dev\\Data Formats.md. Costs and",
                  "; cooldowns: dev\\migrate\\build_shards.py."]
    ini.save(p("data", "Spells.ini"))


def config():
    done = Ini(p("data", "Config.ini")).get("Shards", RARER) == "1"            # (kept: the scrolls are rarer already)
    SK.set_section(SK.CONFIG, "Shards", CONFIG_NOTE + ["%s=%s" % kv for kv in CONFIG] + (["%s=1" % RARER] if done else []))


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
    ini.save(p("data", "Quests.ini"))
    SK.quest("The Shard Scholar", WIZARD, "ShardQuest", {
        0: "Magister Quill, in the Wizards' Court's great hall, studies the Shards.",
        1: "Bring Magister Quill fifteen Shards for the Court's study (talk to him to give them)."}, 2,
        markers={0: "Court_Magister", 1: "Court_Magister"}, kind="Side", requires="Passage to the Mainland")
    lore = [("What are Shards?", "@what"), ("Why do the waystones need them?", "@ways"),
            ("Why do beasts carry them?", "@beasts")]          # (and Galaith's mountain: after what they are)
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
        ("Update.Skill", "Magic", "+1"),
        SK.say(WIZARD, "Fifteen! Feel how they hum together... Here's my payment, as I promised: a scroll of Frost Nova, "
                      "written in my own hand. It drinks Shards like a waystone does, and holds every foe round you in "
                      "ice. Read it and it's yours for good.", ("Thank you, Magister.", "@paid")),
        ("@paid",), ("Display.Message", "Yellow", "Quest complete: The Shard Scholar! You receive a scroll of Frost Nova.",
                     "Quest"),
        ("End",),
        ("@chat",), SK.say(WIZARD, "Ask, ask: a Magister who won't answer questions is just an old man in a hat.",
                           *(lore + [("Goodbye.", "@end")])),
    ]
    for key, label in (("what", "@what"), ("ways", "@ways"), ("beasts", "@beasts"), ("mountain", "@mountain")):
        more = [("And Galaith's mountain?", "@mountain")] if key == "what" else []
        rows += [(label,), SK.say(WIZARD, LORE[key], *(more + [("Tell me more.", "@chat"), ("Thank you.", "@end")]))]
    rows += [("@end",), ("End",)]
    SK.write_script("Talk to Court_Magister", rows, MAKER)


def dragon():
    path = p("data", "Scripts", "The Dragon Speaks.txt")
    text = open(path, "rb").read().decode("cp1252")
    old = "wanted the mountain's gold and its mana, and I let them have it"
    if old in text:
        open(path, "wb").write(text.replace(old, "wanted the mountain's gold and its Shards, and I let them have them")
                               .encode("cp1252"))


def main():
    for name in ["Shard"] + [sc for r in RANKS.values() for sc, _, _ in r.values()]:
        print(("wrote " if K.save("Entities", name, BS.SPRITES[name]()) else "unchanged ") + name)
    config()                                   # (first: the rarity's once-only mark is kept in it)
    entities()
    spells()
    digging()
    quests()
    dragon()
    print("Shards: done")


if __name__ == "__main__":
    main()
