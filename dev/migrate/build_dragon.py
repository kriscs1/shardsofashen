"""The Dragon of Ashpeak: the last quest, offered by the court wizard once every other quest is finished.

Not run on its own: build_content.extend() calls extend() here at the very end (after the other scripts, as it
adds to the wizard's), so `python -I "dev\\migrate\\build_world.py"` builds it.

  * DragonQuest 0  the wizard offers it only when every other quest in QUESTS is done (worked out at build time,
                   so a quest added later is included automatically)
               1  accepted: ask the wizard to open the portal
               2  sent to the lair (map 0,0,-9: a cave on its own level, reached only by the wizard's portal)
               3  Ignaroth slain (Kill Dragon): step into the portal and tell the wizard
               4  done: the Dragon Sword, gold and experience
  * The portal in the lair (trigger Lair Portal) always takes you back to the wizard's tower: after the kill, or to
    flee (the wizard sends you back as often as you like).
"""
import build_places as PL

W = C = None

LAIR = "0,0,-9"
PORTAL = "Ω"            # legend character for Portal001 (the printable ASCII ones are all taken)
LAIR_ROWS = [
    "XXXXXXXXXXXXXXXXXXXXXXXXX",
    "XXXXXXXZXXXXXXXXXZXXXXXXX",
    "XXXXXNGfffffffffffGNXXXXX",
    "XXXXNffgfffffffffgffNXXXX",
    "XXXAffffffffffffffffffAXX",
    "XXXffffffffffffffffffffXX",
    "XXAffwwffffffffffffwwffAX",
    "XXfffwwfffffAfffffffwffXX",
    "XXXffffffffffffffffffffXX",
    "XXXXffffAfffffffffAffffXX",
    "XXXXXfffffffffffffffffXXX",
    "XXXXXXffffffgggffffffXXXX",
    "XXXXXXXZfffffffffffZXXXXX",
    "XXXXXXXXXfffffffffXXXXXXX",
    "XXXXXXXXXXfffffffXXXXXXXX",
    "XXXXXXXXXXrfffffrXXXXXXXX",
    "XXXXXXXXXXXfffffXXXXXXXXX",
    "XXXXXXXXXXXfffffXXXXXXXXX",
    "XXXXXXXXXXXff" + PORTAL + "ffXXXXXXXXX",
    "XXXXXXXXXXXXXXXXXXXXXXXXX",
    "XXXXXXXXXXXXXXXXXXXXXXXXX",
]
ARRIVE = (14, 17)            # where the wizard's portal puts you (a step above the way back)
PORTAL_TILE = (14, 19)
TOWER = ("4,4,1", 21, 9)    # back beside the wizard

QUEST = ("The Dragon of Ashpeak", [
    ("Giver", "Wizard"), ("Attribute", "DragonQuest"),
    ("Stage0", "A last challenge waits for whoever has read the Ashen Omens. Speak to the court wizard at the top of the palace tower on the Royal Isle."),
    ("Stage1", "Ask the court wizard to open a portal to the lair of Ignaroth the dragon. Bring your best armour, food and potions."),
    ("Stage2", "Slay Ignaroth the dragon in its lair. (The portal at the bottom of the lair takes you back to the wizard.)"),
    ("Stage3", "Ignaroth is dead! Step into the portal and tell the court wizard."),
    ("Done", "4")])


def at(tx, ty):
    return "%d,%d" % W.at(tx, ty)


def wizard_steps(quests):
    """Steps for the wizard's script: the dragon quest at each stage (labels dq...), falling through to main."""
    conv = lambda text, *ans: ("Display.Conversation", "Wizard", text) + tuple(a for pair in ans for a in pair)
    steps = ["dq:",
             ("Get.Value", "ATTRIBUTE", "DragonQuest", "Variable.2$"),
             (">Conditional", "$Variable.2=0", "@dq1")]
    # the main story: The Ashen Omens (build_omens.py) first, as the wizard tells it (@om); it has its own Requires
    # (build_cinder.REQUIREMENTS), checked when he offers it
    for name, keys in quests:
        k = dict(keys)
        if k["Attribute"] == "OmenQuest":
            steps += [("Get.Value", "ATTRIBUTE", k["Attribute"], "Variable.3$"),
                      (">Conditional", "$Variable.3>=%s" % k["Done"], "@om")]
    steps += [
        conv("So the omens were true.\\Ignaroth the dragon has woken under Ashpeak. In a month it will burn the Southlands to ash.\\No road leads to its lair, but I can open a portal. Will you face it?",
             ("I'll face the dragon.", "@dqstart"), ("Not yet.", "@bye")),
        "dqstart:",
        ("Update.Attribute", "DragonQuest", "=1"),
        ("Display.Message", "Yellow", "Quest started: The Dragon of Ashpeak."),
        conv("Brave soul. Make ready: your best armour, food, potions. When you're ready, I'll send you.",
             ("Send me now.", "@dqsend"), ("I'll get ready first.", "@bye")),
        ("End",),
        "dq1:",
        (">Conditional", "$Variable.2<3", "@dq3"),
        conv("Are you ready to face Ignaroth? The portal in its lair will bring you back to me.",
             ("Send me to the lair.", "@dqsend"), ("Something else.", "@main"), ("Not yet.", "@bye")),
        ("End",),
        "dqsend:",
        ("Update.Attribute", "DragonQuest", "=2"),
        ("Play.Sound", "Teleporter"),
        ("Display.Message", "Yellow", "The wizard traces a ring of fire in the air... and you step through."),
        ("Teleport", PL.tile("Lair_Arrival", LAIR, *ARRIVE), "-"),
        ("Display.Message", "Red", "Heat, smoke, and the smell of sulphur. Something enormous breathes in the dark."),
        ("End",),
        "dq3:",
        (">Conditional", "$Variable.2=3", "@main"),
        # the reward: the sword, or the hoard (less if you swore to the Ashen Hand: The Ashen Omens)
        ("Get.Value", "ATTRIBUTE", "AshenSworn", "Variable.3$"),
        (">Conditional", "$Variable.3=1", "@dqhero"),
        conv("Ignaroth is dead... and with it, the oath you swore to its cult, I hope.\The king is grateful, but wary. "
             "He offers you a choice: the Dragon Sword, forged in dragonfire long ago, or a share of the dragon's hoard: "
             "1500 gold.", ("The Dragon Sword.", "@dqsword"), ("The gold.", "@dqgold_s")),
        ("End",),
        "dqhero:",
        conv("Ignaroth is dead? Then the Southlands are saved, and you are the greatest hero they have known.\The king "
             "offers you a choice: the Dragon Sword, forged in dragonfire long ago and waiting for a hand worthy of it, "
             "or Ignaroth's hoard: 2500 gold.", ("The Dragon Sword.", "@dqsword"), ("The hoard.", "@dqgold")),
        ("End",),
        "dqsword:",
        ("Update.Attribute", "DragonQuest", "=4"),
        ("Update.Skill", "Strength", "+3"),
        ("Update.Skill", "Defence", "+3"),
        ("Give.Item", "Dragon_Sword", "1"),
        ("Quest.Note", "DragonQuest", "You chose the Dragon Sword."),
        ("Display.Message", "Yellow", "Quest complete: The Dragon of Ashpeak! You receive the Dragon Sword and Strength and Defence experience."),
        ("Goto.Line", "@dqdone"),
        "dqgold:",
        ("Update.Attribute", "DragonQuest", "=4"),
        ("Update.Skill", "Strength", "+3"),
        ("Update.Skill", "Defence", "+3"),
        ("Give.Item", "Gold_Coin(s)", "2500"),
        ("Quest.Note", "DragonQuest", "You chose Ignaroth's hoard: 2500 gold."),
        ("Display.Message", "Yellow", "Quest complete: The Dragon of Ashpeak! You receive 2500 gold and Strength and Defence experience."),
        ("Goto.Line", "@dqdone"),
        "dqgold_s:",
        ("Update.Attribute", "DragonQuest", "=4"),
        ("Update.Skill", "Strength", "+3"),
        ("Update.Skill", "Defence", "+3"),
        ("Give.Item", "Gold_Coin(s)", "1500"),
        ("Quest.Note", "DragonQuest", "You chose a share of the hoard: 1500 gold. (The king remembers your oath to the Ashen Hand.)"),
        ("Display.Message", "Yellow", "Quest complete: The Dragon of Ashpeak! You receive 1500 gold and Strength and Defence experience."),
        "dqdone:",
        ("Display.Message", "Cyan", "Word travels fast: the gates of Wardhaven, over the bridge east of Ashford's farms, are open to you at last."),
        ("End",),
    ]
    return steps


def extend(world, content):
    global W, C
    W, C = world, content
    W.LEGEND[PORTAL] = "Portal001"
    dx, dy = W.place("Dragon", 13, 6)
    W.MAPS[LAIR] = dict(rows=list(LAIR_ROWS), roofs=[], triggers=[("Lair Portal",) + PORTAL_TILE], entities=[
        ("BadNPC", "Dragon", dx, dy),
        W.npc("BadNPC", "Skeleton", 8, 9), W.npc("BadNPC", "Skeleton", 19, 9),
        W.item("Gold_Coin(s)", 8, 3, 60), W.item("Gold_Coin(s)", 17, 3, 60), W.item("Bones", 11, 10), W.item("Bones", 16, 8),
        W.item("Ruby", 10, 3), W.item("Emerald", 15, 3)])

    # data
    C.TILES["Portal001"] = ("1" * 49, "1", "", "A ring of violet fire: the wizard's portal. Step in to go back to his tower.", "1", "170 60 220")
    C.ENTITIES["Dragon"] = C.bad("Ignaroth, the dragon of Ashpeak: red scales, burning eyes and a hoard to match.",
                                 240, 1.5, 10, 14, 200, 1.6, 1, 900,   # hits for 1-11, about every 1.5 s
                                 "Gold_Coin(s),200-400,100 Ruby,1-2,100 Emerald,1-2,80 Sapphire,1-2,80 Bones,1-1,100")
    # it breathes fire from a distance (the engine: Missile = the picture that flies, Weapon.Range = how far), bites close up
    C.ENTITIES["Dragon"] += [("Weapon.Range", "180"), ("Missile", "Dragon_Fire_Missile"), ("Missile.Impact", "Fire_Burst"),
                             ("Missile.Sound", "SpellFire")]
    C.ENTITIES["Dragon_Sword"] = C.equip(2000, "The Dragon Sword, forged in dragonfire: its red blade is warm to the touch.",
                                         "Weapon", 11, 2, "Strength 20")
    C.MOVEMENT["Dragon"] = (2, 5, "0.4", "3-8")
    others = [q for q in C.QUESTS if q[0] != QUEST[0]]
    if QUEST not in C.QUESTS:
        C.QUESTS.append(QUEST)

    # scripts
    W.S["Kill Dragon"] = [
        "// Ignaroth dies (The Dragon of Ashpeak). Generated by build_dragon.py",
        ("Get.Value", "ATTRIBUTE", "DragonQuest", "Variable.1$"),
        (">Conditional", "$Variable.1=2", "@end"),
        ("Update.Attribute", "DragonQuest", "=3"),
        ("Display.Message", "Yellow", "Ignaroth crashes to the ground and moves no more! Step into the portal and tell the wizard."),
        "end:", ("End",)]
    W.S["Lair Portal"] = [
        "// The portal in the dragon's lair: back to the wizard's tower. Generated by build_dragon.py",
        ("Get.Value", "ATTRIBUTE", "DragonQuest", "Variable.1$"),
        (">Conditional", "$Variable.1>=3", "@flee"),
        "go:",
        ("Play.Sound", "Teleporter"),
        ("Display.Message", "Yellow", "The violet fire takes you, and you tumble out in the wizard's tower."),
        ("Teleport", PL.tile("Wizard_Tower_Portal", *TOWER), "-"),
        ("End",),
        "flee:",
        ("Display.Conversation", "Wizard", "(The wizard's voice, through the portal:) Ignaroth still lives! Come back to the tower?",
         "Flee!", "@go", "Stay and fight.", "@end"),
        "end:", ("End",)]
    wiz = W.S["Talk to Wizard"]
    i = wiz.index((">Conditional", "$Variable.1=0", "@main"))     # gift already given: on to the dragon quest
    wiz[i] = (">Conditional", "$Variable.1=0", "@dq")
    wiz[wiz.index("main:"):wiz.index("main:")] = wizard_steps(others)
