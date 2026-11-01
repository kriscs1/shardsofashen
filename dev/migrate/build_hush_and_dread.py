"""Two spells for fighting a crowd, and the quest that leads into Redrock Manor's maze.

  * Silence (Spells.ini Effect=Silence: tricks.py go_silent): a hush of Shards round you for a while; whatever you
    fight makes no sound, so the others near it don't come running (npcs.py npc_rouse) and a camp's lookout can't raise
    the alarm. Its scroll is sold by the wizards, dearly (rare_scrolls.py: 100 + 40 a level).
  * Dread (a bolt with Fear=seconds: player_combat.py frighten): a shard of cold fear; the foe it strikes runs from you
    for a while, and a blow doesn't turn it. Not the great ones (Boss, Slain.By, Fear.Immune). Its scroll lies in
    Redrock Manor's vault, at the end of the maze (build_manors.py: each player's own, once), and is never sold.
  * The Redrock Signet (RedrockSignetQuest 0-2): Ambrose, the manor's last steward, thrown out by the bandits, waits on
    the road by its gate. The old lord built the house so no thief could find his way about it; the bandits have
    never found the vault. He wants the family's signet back from it, and the old lord's other things are yours.
  * Pictures: the two scrolls, Dread's bolt (Ice Bolt's, gone violet), the signet (a ruby ring), Ambrose (the King's
    Steward's picture in a faded brown livery). Sounds: Hush and Dread (build_soundscape.py).

Safe to run again.

  python -I "dev\\migrate\\build_hush_and_dread.py"
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import Ini, p                      # noqa: E402
import build_manors as BM                      # noqa: E402
import build_sprites as BS                     # noqa: E402
import sprite_kit as K                         # noqa: E402
import story_kit as SK                         # noqa: E402
from story_kit import Map, obj_line            # noqa: E402

MAKER = "build_hush_and_dread.py"
ROAD, AMBROSE = "16,15,0", (3, 19)             # (on the road by Redrock Manor's gate, looking at it)
SILENCE_LEVEL, DREAD_LEVEL = 6, 8


# ================================================================== pictures
def art():
    blues = lambda c: c[2] > c[0] + 25 and c[2] > 60          # noqa: E731  (the Steward's blue coat)
    out = [("Entities", "Silence_Scroll", BS.scroll((70, 80, 110), ((200, 210, 235), (90, 100, 140)))),
           ("Entities", "Dread_Scroll", BS.scroll((60, 20, 70), ((190, 120, 230), (90, 40, 120)))),
           ("Entities", "Redrock_Signet", K.load("Entities", "Ruby_Ring")),
           ("Effects", "Dread_Missile", K.hue_shift(K.load("Effects", "Ice_Bolt_Missile"), target_hue=0.79,
                                                     val_mul=0.8)),
           ("Entities", "Manor_Steward", K.hue_shift(K.load("Entities", "Steward"), target_hue=0.08, sat=0.45,
                                                     val_mul=0.85, pred=blues))]
    for d in "1248":
        for f in "abc":
            out.append(("Walk", "Manor_Steward%s%s" % (d, f),
                        K.hue_shift(K.load("Walk", "Steward%s%s" % (d, f)), target_hue=0.08, sat=0.45, val_mul=0.85,
                                    pred=blues)))
    print("Pictures: %d written" % sum(1 for kind, name, img in out if K.save(kind, name, img)))


# ================================================================== data
LEARN = "Learn it, and the spell is yours for good (the scroll is used up); cast it from Spells."


def data():
    ents = Ini(p("data", "Entities.ini"))
    for name, keys in (
            ("Silence_Scroll", [("Type", "MapItem"), ("Use.Words", "Learn"), ("Spell", "Silence"), ("Stackable", "1"),
                                ("Value", str(100 + 40 * SILENCE_LEVEL)),
                                ("Examine.Info", "A scroll of Silence: a hush of Shards round you for 30 seconds. "
                                                 "Whatever you fight makes no sound, so nothing near it comes "
                                                 "running. Channeling %d. %s" % (SILENCE_LEVEL, LEARN))]),
            ("Dread_Scroll", [("Type", "MapItem"), ("Use.Words", "Learn"), ("Spell", "Dread"), ("Stackable", "1"),
                              ("Value", "0"), ("Droppable", "0"),
                              ("Examine.Info", "A scroll of Dread: a shard of cold fear that sends a foe running from "
                                               "you for 6 seconds (1-2 damage). The great ones stand their ground. "
                                               "Channeling %d. %s" % (DREAD_LEVEL, LEARN))]),
            ("Redrock_Signet", [("Type", "MapItem"), ("Stackable", "1"), ("Value", "0"), ("Droppable", "0"),
                                ("Examine.Info", "A heavy gold ring set with a ruby, cut with a hill and a tower: the "
                                                 "Redrock seal.")]),
            ("Manor_Steward", [("Type", "NPC"), ("Attitude", "Good"), ("Use.Words", "Talk to,Examine"),
                               ("Roam.Radius", "0"), ("Chase.Radius", "0"), ("Walk.Speed", "0.5"), ("Pause", "4-10"),
                               ("Respawn", "300"), ("Schedule", "Always"),
                               ("Examine.Info", "An old man in a faded livery, brushed very carefully, keeping watch "
                                                "on a house that isn't his any more.")])):
        for k, v in keys:
            ents.set(name, k, v)
    ents.save(p("data", "Entities.ini"))
    spells = Ini(p("data", "Spells.ini"))
    for name, keys in (
            ("Silence", [("Cost", "6"), ("Cooldown", "60"), ("Scroll", "Silence_Scroll"), ("Effect", "Silence"),
                         ("Level", str(SILENCE_LEVEL)), ("Duration", "30"), ("Impact", "Stone_Glow"),
                         ("Sound", "Hush"), ("XP", "0.4")]),
            ("Dread", [("Cost", "7"), ("Cooldown", "20"), ("Scroll", "Dread_Scroll"), ("Effect", "Bolt"),
                       ("Level", str(DREAD_LEVEL)), ("Damage", "1-2"), ("Range", "224"), ("Fear", "6"),
                       ("Missile", "Dread_Missile"), ("Impact", "Teleport_Glow"), ("Sound", "Dread"),
                       ("XP", "0.5")])):
        if spells.section(name) is None:
            spells.replace_section(name, keys)
    spells.save(p("data", "Spells.ini"))
    racks = Ini(p("data", "ItemRacks.ini"))
    s = racks.section("SHOP-Wizard")
    if s is not None and not any(v.startswith("Silence_Scroll,") for k, v in s[1] if k):
        n = sum(1 for k, v in s[1] if k and k.startswith("Item"))
        racks.set("SHOP-Wizard", "Item%d" % (n + 1), "Silence_Scroll,1")
    racks.save(p("data", "ItemRacks.ini"))


# ================================================================== Ambrose and his quest
def place():
    m = Map(ROAD)
    line = obj_line("NPC", "Manor_Steward", AMBROSE[0], AMBROSE[1],
                    "Attitude=Good Stand=1 Face=W Id=Redrock_Steward Name=Ambrose")
    if not any("Id=Redrock_Steward" in ln for ln in m.ents):
        m.ents.append(line)
        m.save()
        print("%s: Ambrose on the road" % ROAD)


def quest():
    SK.quest("The Redrock Signet", "Manor_Steward", "RedrockSignetQuest", {
        0: "An old man in a faded livery waits on the road by Redrock Manor's gate.",
        1: "Bring Ambrose, the last steward of Redrock Manor, the family's signet from the manor's vault. The old lord "
           "built the house so that no thief could find his way about it."}, 2,
        markers={0: "Redrock_Steward", 1: "Redrock_Manor"}, kind="Side", requires="Passage to the Mainland", level=6)
    SK.section(p("data", "Quests.ini"), "The Redrock Signet",
               [("Reward.Items", "Gold_Coin(s) 120"), ("Reward.Shards", "15"), ("Reward.XP", "Stealth 2 Strength 2")])
    SK.write_script("Talk to Redrock_Steward", [
        ("Get.Value", "ATTRIBUTE", "RedrockSignetQuest", "Variable.1$"),
        (">Conditional", "$Variable.1=0", "@s1"),
        (">Quest.Can.Start", "RedrockSignetQuest", "@wait"),
        SK.say("Manor_Steward", "You there! Forgive an old man for shouting: I'm not allowed any nearer. Ambrose, "
                                "steward of Redrock Manor these fifty years. Well. Steward of the road outside it, "
                                "these three months.", ("What happened?", "@what"), ("Good day to you.", "@end")),
        ("@what",),
        SK.say("Manor_Steward", "Bandits. They came in the spring and threw me out by my collar. The old lord, rest "
                                "him, was a careful man: he built that house so no thief could ever find his way about "
                                "it. Rooms with no doors. Stairs to nowhere. It took me twenty years to learn it, and I "
                                "still go the long way round to the kitchen.\\They've never found the vault. I can "
                                "hear them swearing about it from here.", ("And you want something from it.", "@want")),
        ("@want",),
        SK.say("Manor_Steward", "The family's signet: a ruby in gold, the Redrock seal. If the young master ever comes "
                                "home, he'll want it, and I'll not have it melted down by a man called Spleen. Bring "
                                "it to me and you'll be paid. The rest of the old lord's things in there are yours, with "
                                "my blessing.", ("I'll bring it back.", "@start"), ("Not today.", "@end")),
        ("@start",),
        ("Update.Attribute", "RedrockSignetQuest", "=1"),
        ("Display.Message", "Yellow", "Quest started: The Redrock Signet.", "Quest"),
        (">Got.Item", "Redrock_Signet", "1", "@end"),
        ("Goto.Line", "@give"),
        ("@s1",), (">Conditional", "$Variable.1=1", "@done_chat"),
        (">Got.Item", "Redrock_Signet", "1", "@missing"),
        ("@give",),
        ("Take.Item", "Redrock_Signet", "1"),
        ("Update.Attribute", "RedrockSignetQuest", "=2"),
        SK.say("Manor_Steward", "The signet! And you came back out again, which is more than the last two did.\\Was "
                                "the old lord's scroll there beside it? The Dread, he called it. He read it at tax "
                                "collectors. Keep it: it's done its work in this family.", ("Goodbye, Ambrose.",
                                                                                            "@done")),
        ("@done",),
        ("Display.Message", "Yellow", "Quest complete: The Redrock Signet!", "Quest"),
        ("End",),
        ("@missing",),
        SK.say("Manor_Steward", "The signet's in the vault, and the vault's where it always was. Mind how you go: the "
                                "old lord's house is a liar, every wall of it.", ("I'll keep looking.", "@end")),
        ("End",),
        ("@wait",),
        SK.say("Manor_Steward", "Move along, traveller. Nothing here but an old man and his grudge.",
               ("Goodbye.", "@end")),
        ("End",),
        ("@done_chat",),
        SK.say("Manor_Steward", "I polish it every morning. The young master will come home one day. I'm quite sure of "
                                "it.", ("Goodbye, Ambrose.", "@end")),
        ("@end",), ("End",)], MAKER)


def vault():
    """(the vault's chest: build_manors.py writes it, the signet and the scroll in it too)"""
    pid = BM.MAZE
    BM.scripts(pid, BM.MANORS[pid][2])


def main():
    art()
    data()
    place()
    quest()
    vault()


if __name__ == "__main__":
    main()
