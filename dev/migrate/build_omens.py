"""The Ashen Omens: the quest chain that leads to the dragon (build_dragon.py), with choices that change the fight
and the ending.

Not run on its own: build_content.extend() calls extend() here before build_dragon (so the dragon waits for this
quest) and after_dragon() after it (the wizard's lines go into his script beside the dragon's), so
`python -I "dev\\migrate\\build_world.py"` builds it.

  * OmenQuest 0  when every other quest is done, the court wizard sees ash on the wind: go to Morwen in Fenwick
              1  Morwen reads the ash: the dragon wakes. Bring her a Frost_Lily from the frozen lake under Frostpeak
                 (by the Frost Troll, map 5,9,0)
              2  she brews ONE of two things (your choice):
                   Dragonsbane (OmenBane=1): Ignaroth starts the fight sick, with 90 fewer hitpoints
                   a Fire_Ward_Charm (a ring, Resists=Burn): its fire can't set you alight, its blows hit a third softer
              3  the Ashen Hand cult is waking the dragon: one of its acolytes camps in the hills west of Frosthold.
                 Three ways to deal with him:
                   threaten him: he fights (Set.NPC.Attitude Ashen_Acolyte Bad); his Ashen_Sigil and notes are yours
                   pay him 200 gold for what he knows
                   pretend to join the Hand (AshenSworn=1): free, and the lair's skeletons take you for one of their
                   own... but the wizard and the king find out
                 all three learn of the old scar under the dragon's wing (DragonScar=1: Ignaroth's Defence -6)
              4  back to the wizard: he reacts to what you did (the sigil is worth 300 gold to the king)
              5  done: the wizard offers The Dragon of Ashpeak
  * The lair's map script (0,0,-9) applies the choices each time you go in. The dragon's reward is a choice too
    (build_dragon.py): the Dragon Sword or the hoard, which is smaller if you swore to the Hand.
"""
W = C = R = None        # build_world, build_content, build_regions

QUEST = ("The Ashen Omens", [
    ("Giver", "Wizard"), ("Attribute", "OmenQuest"),
    ("Stage0", "When every other quest is done, speak to the court wizard at the top of the palace tower on the Royal Isle. He has seen something in the sky."),
    ("Stage1", "Ash is falling on the Southlands. The wizard says Morwen the bog witch in Fenwick reads such omens: ask her."),
    ("Stage2", "Morwen needs a frost lily from the frozen lake under Frostpeak, east of Frosthold, where the Frost Troll lives."),
    ("Stage3", "Find the Ashen Hand acolyte camped in the hills west of Frosthold, and learn what the cult knows of the dragon."),
    ("Stage4", "Tell the court wizard what you learned from the Ashen Hand."),
    ("Done", "5")])
ACOLYTE_ID = "AshenAcolyte"
CAMP_MAP = (3, 9)           # the hills west of Frosthold
BANE_HP = 90                # Dragonsbane: the dragon's hitpoints lost
SCAR_DEFENCE = 6            # the scar: its Defence lost


def entities():
    C.ENTITIES.update({
        "Ashen_Acolyte": [("Type", "NPC"), ("Attitude", "Good"), ("Use.Words", "Talk to"),
                          ("Examine.Info", "A thin man in an ash-grey robe. Soot is smeared on his face like war paint."),
                          ("Hitpoints", "70"), ("Attack.Speed", "2.0"), ("Strength", "6"), ("Defence", "7"),
                          ("Aggro.Range", "150"), ("Weapon.Range", "160"), ("Missile", "Fire_Bolt_Missile"),
                          ("Missile.Impact", "Fire_Burst"), ("Missile.Sound", "SpellFire"), ("On.Hit", "Burn 50"),
                          ("Movement.Speed", "1.8"), ("Aggressive", "1"), ("Respawn", "3000"),
                          ("Drops", "Gold_Coin(s),20-40,100 Fire_Bolt_Scroll,1-1,60")],
        "Frost_Lily": C.item(0, "A frost lily from the frozen lake. Its petals are cold as ice and never wilt. For Morwen.",
                             droppable=0),
        "Dragonsbane": C.item(0, "Dragonsbane: a vial of Morwen's brew, thick and green. Its fumes will sicken a dragon "
                                 "the moment you step into its lair.", droppable=0),
        "Fire_Ward_Charm": C.equip(300, "A charm of frost lily and silver wire, cold to the touch. Fire won't catch "
                                        "on whoever wears it, and dragon's fire burns a third less.", "Ring", 0, 1, "")
                           + [("Resists", "Burn"), ("Droppable", "0")],
        "Ashen_Sigil": C.item(0, "The sigil of the Ashen Hand: a black stone disc with a burnt handprint. The court "
                                 "wizard will want to see it.", droppable=0),
    })
    C.MOVEMENT["Ashen_Acolyte"] = (2, 3, "0.4", "3-8")


def place():
    """The acolyte's camp (a free spot in the hills, with a fire) and the frost lily by the frozen lake."""
    mx, my = CAMP_MAP
    name = "%d,%d,0" % (mx, my)
    rows = W.MAPS[name]["rows"]
    walk = {"Grass001", "Weed001", "Tall_Grass001", "Dirt001", "Snow001", "Sand001"}
    for x, y in R.spots(R.GRID, R.BUSY, mx, my, 12, "acolyte"):
        near = [W.LEGEND.get(rows[yy - 1][xx - 1], "").split("+")[0] for yy in range(y - 1, y + 2)
                for xx in range(x - 2, x + 3) if 1 <= xx <= W.MAP_W and 1 <= yy <= W.MAP_H]
        if len(near) == 15 and all(t in walk for t in near):
            px, py = W.at(x, y)
            W.MAPS[name]["entities"].append(("GoodNPC", "Ashen_Acolyte", px, py,
                                             "Id=%s Zone=%d,%d,%d,%d" % (ACOLYTE_ID, x - 2, y - 2, x + 2, y + 2)))
            W.MAPS[name]["entities"].append(W.obj("Fire", x + 1, y))
            W.MAPS[name]["entities"].append(W.item("Bones", x - 1, y + 1))
            break
    else:
        raise AssertionError("no room for the Ashen Hand's camp in " + name)
    sx, sy = R.SITES["TrollLair"]
    m, lx, ly = R.local(sx + 1, sy + 1)                     # (a step from the troll)
    W.MAPS[m]["entities"].append(W.item("Frost_Lily", lx, ly))


def conv(who, text, *answers):
    return R.conv(who, text, *answers)


def witch_steps():
    """Morwen's part (put at the top of Talk to Witch: OmenQuest 1 and 2, then on to her own lines)."""
    w = lambda text, *a: conv("Witch", text, *a)
    return [
        ("Get.Value", "ATTRIBUTE", "OmenQuest", "Variable.5$"),
        (">Conditional", "$Variable.5=1", "@om_w2"),
        w("Red ash in your hair... it smells of sulphur. That's no forest fire, dearie.\\Something under Ashpeak is "
          "breathing in its sleep, and it's waking.\\If you mean to face it, bring me a frost lily, from the frozen "
          "lake east of Frosthold.",("I'll find one.", "@om_w1"), ("A dragon?!", "@om_w1")),
        "om_w1:",
        ("Update.Attribute", "OmenQuest", "=2"),
        ("Display.Message", "Yellow", "The Ashen Omens: bring Morwen a frost lily from the frozen lake east of Frosthold."),
        ("End",),
        "om_w2:",
        (">Conditional", "$Variable.5=2", "@om_w9"),
        (">Got.Item", "Frost_Lily", "1", "@om_nolily"),
        w("A frost lily, and not a petal bruised! Now listen, because I can brew it only one way, and only once.\\"
          "DRAGONSBANE: a poison for the beast's blood. Uncork it in the lair and the dragon will meet you sick and "
          "weak.\\Or a FIRE WARD: a charm to wear. Its fire won't catch on you, and its blows will burn a third "
          "less.\\Which will it be?",
          ("Brew the Dragonsbane.", "@om_bane"), ("Make the Fire Ward.", "@om_ward"), ("Let me think.", "@om_end")),
        ("End",),
        "om_bane:",
        ("Take.Item", "Frost_Lily", "1"),
        ("Give.Item", "Dragonsbane", "1"),
        ("Update.Attribute", "OmenBane", "=1"),
        ("Play.Sound", "Brew"),
        ("Quest.Note", "OmenQuest", "Morwen brewed Dragonsbane: Ignaroth will be sick and weak when you meet it."),
        ("Goto.Line", "@om_cult"),
        "om_ward:",
        ("Take.Item", "Frost_Lily", "1"),
        ("Give.Item", "Fire_Ward_Charm", "1"),
        ("Update.Attribute", "OmenBane", "=0"),
        ("Play.Sound", "Brew"),
        ("Quest.Note", "OmenQuest", "Morwen made a Fire Ward charm: wear it, and the dragon's fire won't catch on you."),
        "om_cult:",
        ("Update.Attribute", "OmenQuest", "=3"),
        w("There. Now, one more thing: dragons don't wake on their own. There's a cult, the Ashen Hand, who worship "
          "the beast and sing to it in its sleep.\\One of their acolytes is camped in the hills west of Frosthold. "
          "Find him. They know things about that dragon nobody else does.",
          ("I'll find him.", "@om_cult2")),
        "om_cult2:",
        ("Display.Message", "Yellow", "The Ashen Omens: find the Ashen Hand acolyte in the hills west of Frosthold."),
        ("End",),
        "om_nolily:",
        w("A frost lily, dearie. They grow only on the frozen lake east of Frosthold. Mind the troll.",
          ("I'll find one.", "@om_end")),
        "om_end:",
        ("End",),
        "om_w9:",
        # after the cult: what she thinks of an oath to the Hand (once)
        ("Get.Value", "ATTRIBUTE", "AshenSworn", "Variable.5$"),
        (">Conditional", "$Variable.5=1", "@om_w10"),
        ("Get.Value", "ATTRIBUTE", "OmenWitchTold", "Variable.5$"),
        (">Conditional", "$Variable.5=0", "@om_w10"),
        ("Update.Attribute", "OmenWitchTold", "=1"),
        w("You swore to the Ashen Hand. Don't look at me like that: the bog hears everything.\\Pretend or not, an oath "
          "is an oath. I hope you know what you're doing.", ("It was a trick.", "@om_end"), ("...", "@om_end")),
        ("End",),
        "om_w10:",
    ]


def acolyte_script():
    a = lambda text, *ans: conv("Ashen_Acolyte", text, *ans)
    return [
        "// The Ashen Hand's acolyte (The Ashen Omens): threaten, pay or join. Generated by build_omens.py",
        ("Get.Value", "ATTRIBUTE", "OmenQuest", "Variable.1$"),
        (">Conditional", "$Variable.1=3", "@after"),
        a("Stay back! These hills are the Ashen Hand's.\\...Unless you've come to hear the song? Ignaroth wakes, "
          "stranger. When it rises, those who sang to it will be spared the fire.",
          ("Tell me what you know, or else.", "@threat"), ("I'll pay for what you know.", "@pay"),
          ("I want to join the Hand.", "@join"), ("Never mind.", "@end")),
        ("End",),
        "threat:",
        a("Threats? From a worm who'll be ash by midsummer? Then burn!", ("So be it.", "@fight")),
        "fight:",
        ("Set.NPC.Attitude", ACOLYTE_ID, "Bad"),
        ("Display.Message", "Red", "The acolyte's hands burst into flame!"),
        ("End",),
        "pay:",
        (">Got.Item", "Gold_Coin(s)", "200", "@poor"),
        a("Gold? Even the Hand must eat. Two hundred, and I'll tell you one thing.", ("Here's 200 gold.", "@paid"),
          ("Too much.", "@end")),
        ("End",),
        "paid:",
        ("Take.Item", "Gold_Coin(s)", "200"),
        ("Update.Attribute", "DragonScar", "=1"),
        ("Update.Attribute", "OmenQuest", "=4"),
        ("Quest.Note", "OmenQuest", "You paid the acolyte 200 gold: Ignaroth has an old wound under its left wing, where the scales never grew back."),
        a("Long ago a knight drove a lance under Ignaroth's left wing. The scales never grew back. Strike there.\\"
          "Now go, before I think better of it.", ("Thank you.", "@told")),
        "told:",
        ("Display.Message", "Yellow", "The Ashen Omens: you know the dragon's weak spot. Tell the court wizard."),
        ("End",),
        "poor:",
        a("Gold? You haven't two hundred to your name. Come back richer.", ("Fine.", "@end")),
        ("End",),
        "join:",
        a("Join? Hah. Then swear it: \"To Ignaroth, my breath, my blood, my ash.\" Say it, and mean it.",
          ("(Swear the oath.)", "@sworn"), ("I've changed my mind.", "@end")),
        ("End",),
        "sworn:",
        ("Update.Attribute", "AshenSworn", "=1"),
        ("Update.Attribute", "DragonScar", "=1"),
        ("Update.Attribute", "OmenQuest", "=4"),
        ("Play.Sound", "SpellFire"),
        ("Quest.Note", "OmenQuest", "You swore the Ashen Hand's oath (as a trick?). The dragon has an old wound under its left wing, and the cult's skeletons in the lair will take you for one of their own."),
        a("Brother! Then hear the secret: under the master's left wing is an old wound where the scales never grew. "
          "We keep it anointed with oil, so it doesn't ache.\\And the bones that guard the master's sleep will know "
          "you now. Go in ash.", ("Go in ash.", "@told")),
        ("End",),
        "after:",
        (">Conditional", "$Variable.1>=4", "@end"),
        ("Get.Value", "ATTRIBUTE", "AshenSworn", "Variable.2$"),
        (">Conditional", "$Variable.2=1", "@stranger"),
        a("Go in ash, brother.", ("Go in ash.", "@end")),
        ("End",),
        "stranger:",
        a("You've had what you paid for. Leave me to my song.", ("Goodbye.", "@end")),
        "end:", ("End",)]


def kill_acolyte():
    return [
        "// The acolyte dies (The Ashen Omens). Generated by build_omens.py",
        ("Get.Value", "ATTRIBUTE", "OmenQuest", "Variable.1$"),
        (">Conditional", "$Variable.1=3", "@end"),
        ("Update.Attribute", "OmenQuest", "=4"),
        ("Update.Attribute", "DragonScar", "=1"),
        ("Give.Item", "Ashen_Sigil", "1"),
        ("Quest.Note", "OmenQuest", "The acolyte's notes: Ignaroth has an old wound under its left wing. You took the Ashen Hand's sigil."),
        ("Display.Message", "Yellow", "The acolyte falls. In his robe: the Ashen Hand's sigil, and notes on the dragon: "
                                      "an old wound under its left wing! Tell the court wizard."),
        "end:", ("End",)]


def wizard_steps():
    """The wizard's part (label om: build_dragon's check sends him here once every other quest is done)."""
    z = lambda text, *a: conv("Wizard", text, *a)
    return [
        "om:",
        ("Get.Value", "ATTRIBUTE", "OmenQuest", "Variable.4$"),
        (">Conditional", "$Variable.4=0", "@om1"),
        z("You! Yes, you: the one the whole kingdom talks about. Look out of the window.\\Ash. Red ash, falling on "
          "the Southlands out of a clear sky, and the wells running warm. Omens, and bad ones.\\Morwen the bog witch "
          "in Fenwick reads such things better than I do. Will you ask her?",
          ("I'll go to Morwen.", "@om_go"), ("Something else.", "@main"), ("Not now.", "@bye")),
        ("End",),
        "om_go:",
        ("Update.Attribute", "OmenQuest", "=1"),
        ("Display.Message", "Yellow", "Quest started: The Ashen Omens."),
        ("End",),
        "om1:",
        (">Conditional", "$Variable.4=4", "@om2"),
        (">Got.Item", "Ashen_Sigil", "1", "@om_nosigil"),
        ("Take.Item", "Ashen_Sigil", "1"),
        ("Give.Item", "Gold_Coin(s)", "300"),
        z("The sigil of the Ashen Hand! So the acolyte is dead, and the cult has one voice fewer singing to the "
          "beast. The king will pay 300 gold for this.\\And a wound under its left wing... good. Very good.",
          ("Then the dragon is real.", "@om_done")),
        ("End",),
        "om_nosigil:",
        ("Get.Value", "ATTRIBUTE", "AshenSworn", "Variable.5$"),
        (">Conditional", "$Variable.5=1", "@om_paid"),
        z("You swore their oath? Even as a trick, an oath to a dragon has weight. I can smell the ash on it.\\Still: a "
          "wound under its left wing, and the bones in its lair will let you pass. I'll trust you. The king, I think, "
          "will be slower to.", ("It was a trick, I swear.", "@om_done")),
        ("End",),
        "om_paid:",
        z("You paid two hundred gold for a cultist's whisper?\\Well, knowledge is never cheap. And a wound under "
          "its left wing is worth far more than that.", ("Then the dragon is real.", "@om_done")),
        ("End",),
        "om_done:",
        ("Update.Attribute", "OmenQuest", "=5"),
        ("Display.Message", "Yellow", "Quest complete: The Ashen Omens!"),
        ("Goto.Line", "@dq"),
        "om2:",
        (">Conditional", "$Variable.4<5", "@main"),
        z("The ash still falls. Do as Morwen told you (Fenwick, in the Saltmarsh), and come back to me when you know more.",
          ("Something else.", "@main"), ("On my way.", "@bye")),
        ("End",),
    ]


def lair_script(d, skeletons):
    """Each time you go into the lair: the Dragonsbane, the scar, the oath. d, skeletons: their IDs (Id= on the lair's
    map lines, so they're found wherever they've moved to)."""
    steps = ["// The dragon's lair: what The Ashen Omens changed. Generated by build_omens.py",
             ("Get.Value", "ATTRIBUTE", "DragonQuest", "Variable.1$"),
             (">Conditional", "$Variable.1=2", "@end"),
             ("Get.Value", "ATTRIBUTE", "OmenBane", "Variable.2$"),
             (">Conditional", "$Variable.2=1", "@scar"),
             ("Edit.Entity", d, "Dragon", "MAXHP", "-%d" % BANE_HP),
             ("Edit.Entity", d, "Dragon", "HP", "-%d" % BANE_HP),
             ("Display.Message", "Green", "You uncork Morwen's Dragonsbane. Green fumes roll into the dark... and "
                                          "somewhere ahead, something huge coughs and retches."),
             "scar:",
             ("Get.Value", "ATTRIBUTE", "DragonScar", "Variable.2$"),
             (">Conditional", "$Variable.2=1", "@oath"),
             ("Edit.Entity", d, "Dragon", "DEFENCE", "-%d" % SCAR_DEFENCE),
             ("Display.Message", "Cyan", "Remember: the old wound under its left wing. Strike there."),
             "oath:",
             ("Get.Value", "ATTRIBUTE", "AshenSworn", "Variable.2$"),
             (">Conditional", "$Variable.2=1", "@end")]
    for sid in skeletons:
        steps.append(("Edit.Entity", sid, "Skeleton", "ATTITUDE", "Good"))
    steps += [("Display.Message", "Cyan", "The skeletons turn their empty eyes on you... and look away. They know "
                                          "the Hand's oath."),
              "end:", ("End",)]
    return steps


def make_art():
    """The items, from others recoloured (the acolyte himself is in build_people.PEOPLE)."""
    import sprite_kit as K
    vivid = lambda c: max(c) - min(c) > 30
    jobs = [("Herb", "Frost_Lily", lambda img: K.hue_shift(img, target_hue=0.55, sat_mul=0.5, val_mul=1.25, pred=vivid)),
            ("Full_Vial", "Dragonsbane", lambda img: K.hue_shift(img, target_hue=0.27, sat_mul=1.2, val_mul=0.8, pred=vivid)),
            ("Sapphire_Ring", "Fire_Ward_Charm", lambda img: K.hue_shift(img, target_hue=0.52, sat_mul=0.6, val_mul=1.2, pred=vivid)),
            ("Emerald", "Ashen_Sigil", lambda img: K.hue_shift(img, dh=0.0, sat_mul=0.05, val_mul=0.45, pred=vivid))]
    made = []
    for src, dst, fn in jobs:
        if K.save("Entities", dst, fn(K.load("Entities", src))):
            made.append("sprites\\Entities\\%s.png" % dst)
    return made


def extend(world, content, regions):
    """Before build_dragon: the quest (so the dragon waits for it), the people, the things, Morwen's lines."""
    global W, C, R
    W, C, R = world, content, regions
    entities()
    place()
    witch = W.S["Talk to Witch"]
    k = next(i for i, s in enumerate(witch) if not (isinstance(s, str) and s.startswith("//")))
    witch[k:k] = witch_steps()
    W.S["Talk to Ashen_Acolyte"] = acolyte_script()
    W.S["Kill Ashen_Acolyte"] = kill_acolyte()
    if not any(q[0] == QUEST[0] for q in C.QUESTS):
        C.QUESTS.append(QUEST)
    W.EXTRA_STEPS.insert(0, make_art)


def after_dragon():
    """After build_dragon: the wizard's lines (om:) and the lair's map script."""
    import build_dragon as D
    wiz = W.S["Talk to Wizard"]
    i = wiz.index("main:")
    wiz[i:i] = wizard_steps()
    ents, skeletons = W.MAPS[D.LAIR]["entities"], []        # the dragon and the skeletons get IDs (Id=)
    for i, e in enumerate(ents):
        if e[1] in ("Dragon", "Skeleton"):
            sid = "Ignaroth" if e[1] == "Dragon" else "Lair_Skeleton_%d" % (len(skeletons) + 1)
            opts = (str(e[4]) + " " if len(e) > 4 else "") + "Id=" + sid
            ents[i] = tuple(e[:4]) + (opts.strip(),)
            if e[1] == "Skeleton":
                skeletons.append(sid)
    W.S[D.LAIR] = lair_script("Ignaroth", skeletons)
