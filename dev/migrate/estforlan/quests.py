"""The new mainland's side quests about Wardhaven, and the old chapter's words about it gone:

  * The Wardhaven Bridge (WardhavenQuest): after The Ashford Road, Mayor Hollis tells you goblins have taken the bridge
    to Wardhaven and its guards have fled. The goblins are on the bridge only while you're at it (the gate's map's
    entry script puts them there, for you, as many as are left); kill four ($BridgeGoblins), tell the Mayor, and the
    gates open (their Lock) and the bridge guards are back at their posts whenever you come by again.
  * The Dragonforge (DragonforgeQuest): once Galaith's dragon is dead, the Wyrmsmith of Wardhaven asks for three of its
    scales, makes you a dragonscale helm of them, and lets you use her forge from then on.
"""
import os

import story_kit as K
from atlas import TW

MAKER = "build_estforlan.py"
GOBLINS = 4


def at(atlas, c):
    m, x, y = atlas.at(*c)
    return m.name, x, y


def bridge(atlas, info):
    """The Wardhaven Bridge: its quest, the Mayor's words, the goblins' and the guards' entry script lines, the kills.
    Returns {map: entry script rows}."""
    K.quest("The Wardhaven Bridge", "Mayor", "WardhavenQuest", {
        0: "Speak to Mayor Hollis in Ashford's Town Hall.",
        1: "Goblins hold the bridge to Wardhaven, north of Ashford's farms, and its guards have fled. Clear the "
           "goblins off the bridge ($BridgeGoblins of %d)." % GOBLINS,
        2: "Tell Mayor Hollis the bridge is clear."}, 3,
        markers={0: "Ashford_Town_Hall", 1: "Wardhaven_Bridge_Span", 2: "Ashford_Town_Hall"},
        kind="Side", requires="The Ashford Road")
    gate_map, _, _ = at(atlas, info["gate"])
    on_gate = [c for c in info["shore"] + info["bridge"] if atlas.at(*c)[0].name == gate_map]
    spots = [on_gate[int(i * (len(on_gate) - 1) / max(1, GOBLINS - 1))] for i in range(GOBLINS)]
    rows = [("Get.Value", "ATTRIBUTE", "WardhavenQuest", "Variable.1$"),
            (">Conditional", "$Variable.1=1", "@guards"),
            ("Get.Value", "ATTRIBUTE", "BridgeGoblins", "Variable.2$")]
    for i, c in enumerate(spots, 1):
        _, x, y = at(atlas, c)
        rows += [(">Conditional", "$Variable.2<%d" % (GOBLINS + 1 - i), "@goblin%d" % i),
                 ("Add.Entity", "%d,%d" % ((x - 1) * TW, (y - 1) * TW - 8), "Goblin" if i % 2 else "Goblin_Archer",
                  "NPC", "Attitude=Bad Zone=%d,%d,%d,%d" % (max(2, x - 3), max(2, y - 4), min(24, x + 4),
                                                             min(20, y + 4))),
                 ("@goblin%d" % i,)]
    rows += [("End",), ("@guards",), (">Conditional", "$Variable.1>=3", "@end")]
    gx, gy = info["gate"]
    for c, face in (((gx - 1, gy + 1), "S"), ((gx + 2, gy + 1), "S")):     # (either side of the way to the gate)
        _, x, y = at(atlas, c)
        rows.append(("Add.Entity", "%d,%d" % ((x - 1) * TW, (y - 1) * TW - 8), "Guard", "NPC",
                     "Attitude=Good Stand=1 Face=%s" % face))
    rows += [("@end",), ("End",)]
    K.write_script("Kill Goblin", [
        (">On.Map", gate_map, "@end"),
        ("Get.Value", "ATTRIBUTE", "WardhavenQuest", "Variable.1$"),
        (">Conditional", "$Variable.1=1", "@end"),
        ("Update.Attribute", "BridgeGoblins", "+1"),
        ("Get.Value", "ATTRIBUTE", "BridgeGoblins", "Variable.2$"),
        (">Conditional", "$Variable.2>=%d" % GOBLINS, "@more"),
        ("Update.Attribute", "WardhavenQuest", "=2"),
        ("Display.Message", "Yellow", "The last goblin falls: the bridge to Wardhaven is clear. Tell the Mayor.",
         "Quest"),
        ("End",),
        ("@more",), ("Display.Message", "Yellow", "Goblins cleared from the bridge: $Variable.2 of %d." % GOBLINS),
        ("@end",), ("End",)], MAKER)
    K.write_script("Kill Goblin_Archer", [("Goto.Script", "Kill Goblin")], MAKER)     # (they count the same)
    K.write_script("Wardhaven Guard", [
        K.say("Guard", "We ran when the goblins came over the bridge, and I'm not proud of it. Thanks to you we're back "
                       "at our posts.\\Welcome to Wardhaven.", ("Thank you.", "@end")),
        ("@end",), ("End",)], MAKER)
    mayor()
    return {gate_map: rows}


def mayor():
    """Mayor Hollis (Ashford's Town Hall): The Ashford Road as it was (build_heir_mainland.py wrote it), then The
    Wardhaven Bridge."""
    K.write_script("Talk to Ashford_Clerk_13", [
        ("Get.Value", "ATTRIBUTE", "AshfordQuest", "Variable.1$"),
        (">Conditional", "$Variable.1=0 and $Item.Parliament_Letter>=1", "@a1"),
        (">Quest.Can.Start", "AshfordQuest", "@end"),
        ("Take.Item", "Parliament_Letter", "1"),
        K.say("Mayor", "A letter from the Parliament? \"Every friend of the crown...\" Well, I'm a friend of the crown, "
                       "and I'd be a better one if the goblins would leave my farms alone.\\They come out of the hedges "
                       "east of town and carry off the hens. Drive them off for me, at the farm crossroads, and I'll "
                       "give you my pass for the Steward.", ("I'll deal with the goblins.", "@a0")),
        ("@a0",), ("Update.Attribute", "AshfordQuest", "=1"),
        ("Display.Message", "Yellow", "Quest started: The Ashford Road.", "Quest"),
        ("Start.Wave", "Farm_Raid"),
        ("End",),
        ("@a1",), (">Conditional", "$Variable.1=1", "@a2"),
        K.say("Mayor", "The goblins are still at it! The farm crossroads, east of town.", ("Send them in.", "@raid"),
              ("I'm on my way.", "@end")),
        ("@raid",), ("Start.Wave", "Farm_Raid"),
        ("End",),
        ("@a2",), (">Conditional", "$Variable.1=2", "@w"),
        ("Update.Attribute", "AshfordQuest", "=3"),
        ("Give.Item", "Mayors_Pass", "1"),
        K.say("Mayor", "Beaten them, have you? Then here's my pass. The Steward at King Rupert's Keep will see you "
                       "right.", ("Thank you, Mayor.", "@a3")),
        ("@a3",), ("Display.Message", "Yellow", "Quest complete: The Ashford Road!", "Quest"),
        ("End",),
        ("@w",), ("Get.Value", "ATTRIBUTE", "WardhavenQuest", "Variable.2$"),
        (">Conditional", "$Variable.2=0", "@w1"),
        (">Quest.Can.Start", "WardhavenQuest", "@chat"),
        K.say("Mayor", "There's worse news, I'm afraid. Goblins have come up from the farms and taken the bridge to "
                       "Wardhaven, and the bridge guards turned tail and ran. Nothing's gone across in a week.\\Clear "
                       "them off the bridge, would you? It's north of the farms.", ("I'll clear the bridge.", "@w0"),
              ("Not now.", "@end")),
        ("@w0",), ("Update.Attribute", "WardhavenQuest", "=1"),
        ("Display.Message", "Yellow", "Quest started: The Wardhaven Bridge.", "Quest"),
        ("End",),
        ("@w1",), (">Conditional", "$Variable.2=1", "@w2"),
        K.say("Mayor", "The goblins are still on the Wardhaven bridge, north of the farms.", ("I'm on my way.", "@end")),
        ("End",),
        ("@w2",), (">Conditional", "$Variable.2=2", "@chat"),
        ("Update.Attribute", "WardhavenQuest", "=3"),
        ("Give.Item", "Gold_Coin(s)", "80"),
        K.say("Mayor", "The bridge is clear? Then I'll send word, and the guards will be back at their posts by the time "
                       "you're there. Wardhaven's gates will open to you. Here, for your trouble.",
              ("Thank you, Mayor.", "@w3")),
        ("@w3",), ("Display.Message", "Yellow", "Quest complete: The Wardhaven Bridge! You receive 80 gold.", "Quest"),
        ("End",),
        ("@chat",), K.say("Mayor", "Ashford's Town Hall: births, weddings, deeds and goblins. Mostly goblins.",
                          ("Goodbye.", "@end")),
        ("@end",), ("End",)], MAKER)


def dragonforge():
    """The Dragonforge: the Wyrmsmith's quest, after Galaith's dragon."""
    K.quest("The Dragonforge", "Wyrmsmith", "DragonforgeQuest", {
        0: "Speak to the Wyrmsmith in Wardhaven.",
        1: "Bring the Wyrmsmith of Wardhaven three scales of Galaith's dragon."}, 2,
        markers={0: "Wardhaven_Wyrmsmith", 1: "Wardhaven_Wyrmsmith"}, kind="Side", requires="The Dragon of Galaith")
    K.write_script("Talk to Wyrmsmith", [
        ("Get.Value", "ATTRIBUTE", "DragonforgeQuest", "Variable.1$"),
        (">Conditional", "$Variable.1=0", "@d1"),
        (">Quest.Can.Start", "DragonforgeQuest", "@wait"),
        K.say("Wyrmsmith", "You're the one who slew the dragon of Galaith? Then you'll have its scales.\\This is the "
                           "Dragonforge: the only fire in Estforlan hot enough to work dragon scale. Bring me three, and "
                           "I'll make you a helm of them myself, and teach you the forge.",
              ("I'll bring you three scales.", "@d0"), ("Not now.", "@end")),
        ("@d0",), ("Update.Attribute", "DragonforgeQuest", "=1"),
        ("Display.Message", "Yellow", "Quest started: The Dragonforge.", "Quest"),
        ("End",),
        ("@d1",), (">Conditional", "$Variable.1=1", "@forge"),
        (">Got.Item", "Dragon_Scale", "3", "@short"),
        ("Take.Item", "Dragon_Scale", "3"),
        ("Update.Attribute", "DragonforgeQuest", "=2"),
        ("Play.Sound", "Anvil"),
        ("Give.Item", "Dragonscale_Helm", "1"),
        ("Update.Skill", "Smithing", "+2"),
        K.say("Wyrmsmith", "Three of them, still warm! Watch now...\\There. A dragonscale helm, and nothing on this earth "
                           "will burn through it. The forge is yours to use whenever you've scales and mithril.",
              ("Thank you!", "@d2")),
        ("@d2",), ("Display.Message", "Yellow", "Quest complete: The Dragonforge! You receive a dragonscale helm.",
                   "Quest"),
        ("End",),
        ("@short",), K.say("Wyrmsmith", "Three scales from the dragon's hide: no fewer.", ("I'll find them.", "@end")),
        ("End",),
        ("@forge",), K.say("Wyrmsmith", "Back for the forge? Scale and mithril, and I'll show you how.",
                           ("Show me the Dragonforge.", "@rack"), ("Goodbye.", "@end")),
        ("@rack",), ("Display.Item.Rack", "GENERAL", "Wyrmsmith", "CRAFT-Dragonforge", "@end"),
        ("End",),
        ("@wait",), K.say("Wyrmsmith", "This is the Dragonforge. It's been cold a long time: there's only one dragon "
                                       "left in Estforlan, and it sits before the walls of Galaith.", ("Goodbye.", "@end")),
        ("@end",), ("End",)], MAKER)
    K.write_script("Forge Wyrmsmith", [
        (">Conditional", "$Attr.DragonforgeQuest>=2", "@no"),
        ("Display.Item.Rack", "GENERAL", "Wyrmsmith", "CRAFT-Dragonforge", "@end"),
        ("End",),
        ("@no",), ("Display.Refusal", "The Wyrmsmith shakes her head: not yet."),
        ("@end",), ("End",)], MAKER)


def leftovers():
    """The old chapter's words about Wardhaven (Ignaroth, twelve years behind its walls): gone."""
    K.section(K.ENTS, "Wyrmsmith", [("Examine.Info", "The Wyrmsmith of Wardhaven: she keeps a forge hot enough to "
                                                     "work dragon scale.")])
    K.section(K.ENTS, "Dragon_Scale", [("Examine.Info", "A scale from the hide of Galaith's dragon, still warm. "
                                                        "No ordinary fire will touch it.")])
    path = os.path.join(K.SCRIPTS, "Talk to Settler.txt")
    text = open(path, "rb").read().decode("cp1252")
    old = ("Twelve years behind these walls, and now Ignaroth is dead! They say it was you. Drinks are on the house "
           "at every table in Wardhaven.")
    new = ("Goblins on the bridge and the guards run off: we thought we'd starve out here. They say it was you who "
           "cleared them. Drinks are on the house at every table in Wardhaven!")
    if old in text:
        open(path, "wb").write(text.replace(old, new).encode("cp1252"))
    statue = os.path.join(K.SCRIPTS, "Examine Hero_Statue.txt")
    if os.path.exists(statue):
        os.remove(statue)                                  # (Ignaroth's slayer's statue: not in the new world)
