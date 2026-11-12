"""The Isle's secrets: three things for the Isle (the demo) to leave a player wanting more.

  * Who sent the hobgoblins. In the lair's corner barrel, with Tobias's key, an order folded small (Ashen_Order, Read):
    find the woman from Galaith, her papers under a crowned seal, the child's name; signed with a hand pressed in ash.
    Tobias, shown it, knows why they took him (he writes the Isle's papers) and who signs so (the Ashen Hand, in the
    north). Chapter 11 pays it off: the Ashen Priest drops his ledger (Ashen_Ledger, Read), the same careful hand.
  * What Jimmy Kept (JimmyQuest, a side quest after the amulet): Brother Aldous gives you Mary's charm (Marys_Charm,
    Read): read aloud, its Shards make you a cat for two minutes (Turn.Into). As a cat, Jimmy tells you what Mary hid
    under the cottage, through his way in (Cat_Gap, low in its front wall, cats only): a miniature of the three of you.
  * Tobias's Tin (TobiasTin, a side quest once he's free): the hobgoblins have his savings in the chest by their camp
    fire. He teaches you to sneak; two lookouts keep the camp now (Stand=1 Face= Turn= Group=Hob_Camp, in place of
    the two that wandered), and there's a way round behind them.

Takes over Search Lair_Corner_Barrel, Talk to Chapel_Verger, Talk to Tobias (build_heir_isle.py), Talk to Jimmy
(build_isle.py), Open Hob_Camp_Chest (grow_isle.py) and Kill Ashen_Priest (build_heir_mainland.py): story_kit.TAKES_OVER.
Safe to run again.

  python -I "dev\\migrate\\build_isle_secrets.py"
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import story_kit as K                                   # noqa: E402
from story_kit import Map, obj_line, say                # noqa: E402
from common import Ini, p                              # noqa: E402

MAKER = "build_isle_secrets.py"
V1 = "Variable.1$"
COTTAGE, GAP = "4,0,0", (11, 13)                        # (the cottage's front wall, east of its window)
CAMP = "2,2,0"
LOOKOUTS = (((10, 6), "N", 8, 1), ((14, 8), "N", 6, 2))  # (by the chest, and by the west tents: both watch the gate)
FAR = [("@far",), ("Display.Message", "DarkRed", "You are too far away!", "Denied"), ("End",)]

ORDER = ("A scrap of good paper, folded small, in a careful hand:\\There is a woman on the Isle who came from Galaith "
         "the year it shut, with a child. She has papers under a crowned seal, or the old man who writes the Isle's "
         "papers keeps them for her. Bring them, and the child's name, and the Shards are yours.\\No name under it. "
         "Only a hand, pressed in ash.")
LEDGER = ("A little ledger bound in black, in a careful hand: Shards in, Shards out. Two lines are marked with a "
          "thumbprint of ash:\\'To the hobgoblins on the Isle, forty Shards, for the woman's papers and the child's "
          "name. They took the old man, and nothing came of it.'\\And newer, the ink still dark: 'The child has crossed "
          "the strait. The grey ones pay double now. They say the one beyond the wall is waiting.'")
CHARM = ("Your mother's hand, small and quick, on a scrap of the Wizards' Court's paper. The ink has a blue glint to "
         "it:\\Velvet paw and whisker-wise,\\see the house with Jimmy's eyes.\\And under it: For my little one, when "
         "it's time. Jimmy knows where.")


# ================================================================== pictures
def order():
    """A scrap of paper folded small, a grey handprint pressed on it."""
    pg = K.pg()
    s = K.surface()
    paper, shade, line, ash = (232, 224, 200), (196, 184, 152), (150, 130, 96), (92, 90, 88)
    pg.draw.polygon(s, paper, [(7, 10), (25, 8), (26, 25), (8, 26)])
    pg.draw.polygon(s, shade, [(7, 10), (25, 8), (25, 12), (7, 14)])                # (the fold)
    for y in (17, 20, 23):
        pg.draw.line(s, line, (10, y), (16, y))
    pg.draw.ellipse(s, ash, (16, 16, 7, 7))                                          # the palm, in ash
    for i, (x, top) in enumerate(((16, 12), (18, 11), (20, 11), (22, 12))):       # the fingers
        pg.draw.line(s, ash, (x, top), (x, 17))
    pg.draw.line(s, ash, (23, 20), (25, 18))                                         # the thumb
    return K.outlined(s)


def ledger():
    """A little black book, a smudge of ash on its cover."""
    pg = K.pg()
    s = K.surface()
    pg.draw.rect(s, (238, 228, 198), (9, 8, 16, 19))                                 # (the pages' edge)
    pg.draw.rect(s, (36, 32, 34), (7, 7, 16, 20))
    pg.draw.rect(s, (60, 54, 58), (8, 8, 2, 18))                                     # (the spine)
    pg.draw.circle(s, (120, 116, 112), (16, 16), 3)
    s.set_at((17, 15), (150, 146, 140))
    return K.outlined(s)


def charm():
    """A scrap of paper, a blue glint of ink, a little cat drawn in the corner."""
    pg = K.pg()
    s = K.surface()
    paper, line, blue = (240, 232, 206), (120, 110, 150), (110, 170, 240)
    pg.draw.polygon(s, paper, [(6, 9), (26, 7), (27, 24), (7, 25)])
    for y in (12, 15, 18):
        pg.draw.line(s, line, (9, y), (22, y - 1))
    for x, y in ((12, 12), (19, 15), (15, 18)):
        s.set_at((x, y), blue)
    cat = (60, 50, 70)
    pg.draw.circle(s, cat, (21, 21), 2)                                              # (the cat: a head, ears, a tail)
    s.set_at((19, 19), cat)
    s.set_at((22, 19), cat)
    pg.draw.line(s, cat, (23, 22), (25, 20))
    return K.outlined(s)


def miniature():
    """A tiny portrait in an oval gold frame: two faces and a little one."""
    pg = K.pg()
    s = K.surface()
    gold, dark = (214, 170, 54), (150, 110, 30)
    pg.draw.ellipse(s, dark, (8, 5, 17, 22))
    pg.draw.ellipse(s, gold, (8, 5, 16, 21))
    pg.draw.ellipse(s, (60, 80, 130), (10, 7, 12, 17))                               # (a blue ground)
    skin = (232, 196, 160)
    pg.draw.circle(s, skin, (14, 13), 2)                                             # him
    pg.draw.line(s, (240, 210, 80), (12, 10), (16, 10))                              # (a little crown)
    pg.draw.circle(s, skin, (18, 14), 2)                                             # her
    pg.draw.line(s, (170, 90, 50), (16, 12), (20, 12))
    pg.draw.ellipse(s, (238, 232, 220), (14, 17, 5, 4))                              # the little one, in white
    s.set_at((16, 18), skin)
    pg.draw.line(s, dark, (16, 3), (16, 5))                                          # (its loop)
    return K.outlined(s)


def tin():
    """A dented tin, a T scratched on its lid."""
    pg = K.pg()
    s = K.surface()
    pg.draw.rect(s, (150, 156, 160), (8, 14, 17, 11))
    pg.draw.rect(s, (182, 188, 192), (7, 11, 19, 4))                                 # (the lid)
    pg.draw.line(s, (110, 114, 118), (14, 12), (19, 12))                             # the T
    pg.draw.line(s, (110, 114, 118), (16, 12), (16, 14))
    pg.draw.line(s, (120, 124, 128), (10, 20), (12, 22))                             # (a dent)
    return K.outlined(s)


def gap():
    """A dark gap where a board at the foot of the wall has rotted away."""
    pg = K.pg()
    s = K.surface()
    pg.draw.rect(s, (24, 18, 14), (11, 24, 10, 8))
    pg.draw.ellipse(s, (24, 18, 14), (11, 21, 10, 6))
    pg.draw.line(s, (96, 66, 40), (10, 23), (10, 31))                                # (the rotten board's edges)
    pg.draw.line(s, (96, 66, 40), (21, 22), (21, 31))
    s.set_at((15, 26), (90, 80, 60))                                                 # (a wisp of ginger fur)
    s.set_at((16, 25), (220, 130, 60))
    return s


def art():
    made = [K.save("Entities", n, f()) for n, f in (("Ashen_Order", order), ("Ashen_Ledger", ledger),
                                                    ("Marys_Charm", charm), ("Royal_Miniature", miniature),
                                                    ("Tobias_Tin", tin), ("Cat_Gap", gap))]
    print("Pictures: %d written" % sum(made))


# ================================================================== data
def data():
    E = K.ENTS
    items = [
        ("Ashen_Order", "An order folded small, from the hobgoblins' lair. Signed with a hand, pressed in ash.",
         "Read,Examine", "The Order in Ash"),
        ("Ashen_Ledger", "The Ashen Priest's ledger, bound in black. The same careful hand as the order in the "
         "hobgoblins' lair.", "Read,Examine", "The Ashen Priest's Ledger"),
        ("Marys_Charm", "Your mother's charm, a scrap of the Wizards' Court's paper. The ink glints blue.",
         "Read,Examine", "Mary's Charm"),
        ("Royal_Miniature", "A tiny portrait in a gold frame: a tall young man in a crown, a woman with your eyes, and "
         "a baby in white in her arms. On the back, in your mother's hand: R. and M. and the little one. Galaith, the "
         "spring before.", "Examine", "The Miniature"),
        ("Tobias_Tin", "Tobias's savings tin, dented, a T scratched on the lid. It rattles.", "Examine",
         "Tobias's Tin"),
    ]
    for name, info, words, shown in items:
        K.section(E, name, [("Type", "MapItem"), ("Use.Words", words), ("Examine.Info", info), ("Stackable", "1"),
                            ("Droppable", "0"), ("Value", "0"), ("Display.Name", shown)])
    K.section(E, "Cat_Gap", [("Type", "StaticObject"), ("Use.Words", "Squeeze Through,Examine"), ("Solid", "1"),
                             ("Examine.Info", "A gap low in the cottage wall, where a board has rotted away. Jimmy's "
                                              "way in under the floor. Far too small for you.")])


NEW = set()


def quest(name, *a, **k):
    """A quest, the first time only (tuned since: kept)."""
    if Ini(p("data", "Quests.ini")).section(name) is None:
        NEW.add(name)
        K.quest(name, *a, **k)


def section(name, keys):
    if name in NEW:
        K.section(K.QUESTS, name, keys)


def quests():
    quest("What Jimmy Kept", "Gravekeeper", "JimmyQuest", {
        0: "Brother Aldous, at the chapel, kept something of your mother's for you.",
        1: "Mary told Brother Aldous: 'Jimmy knows where.' Read her charm by Jimmy at the cottage, by day, and ask "
           "him as a cat.",
        2: "Jimmy says your mother hid something under the cottage, through his way in: a gap low in its front wall. "
           "Squeeze through it as a cat."}, 3,
        markers={0: "Chapel_Verger", 1: "Jimmy", 2: "Cottage_Cat_Gap"}, kind="Side",
        requires="The Amulet of Succession")
    section("What Jimmy Kept", [("Reward.Shards", "10"), ("Reward.XP", "Channeling 2"),
                                ("Rumour", "Brother Aldous at the chapel was asking after you. Something of your mother's, "
                                           "he said.")])
    quest("Tobias's Tin", "Tobias", "TobiasTin", {
        0: "Tobias is staying with Edwin and Maren since you freed him.",
        1: "The hobgoblins took Tobias's savings tin. It'll be in the chest by the fire in their camp, south-east of "
           "the village. Two of them keep watch: sneak, and keep out of the way they're looking.",
        2: "You have Tobias's tin. Take it back to him at Edwin and Maren's."}, 3,
        markers={0: "Isle_Bank", 1: "Hob_Camp_Chest", 2: "Isle_Bank"}, kind="Side",
        requires="The Last Will")
    section("Tobias's Tin", [("Requires.If", "$Attr.Passage>=3"), ("Reward.Items", "Gold_Coin(s) 25"),
                             ("Reward.Shards", "5"), ("Reward.XP", "Stealth 2"),
                             ("Rumour", "Old Tobias is safe at Edwin's, they say, but them hobgoblins had every penny "
                                        "he owned.")])


# ================================================================== places
def places():
    m = Map(COTTAGE)
    if not K.has_id(m, "Cottage_Cat_Gap"):
        m.ents.append(obj_line("StaticObject", "Cat_Gap", GAP[0], GAP[1], "Id=Cottage_Cat_Gap"))
        m.save()
        print("%s: Jimmy's way in" % COTTAGE)
    m = Map(CAMP)
    went = K.ents_without(m, lambda f: f[:2] == ["NPC", "Hobgoblin"] and "Zone=8,4,18,12" in f[-1])
    added = 0
    for (x, y), face, turn, n in LOOKOUTS:
        if not K.has_id(m, "Hob_Camp_Lookout_%d" % n):
            m.ents.append(obj_line("NPC", "Hobgoblin", x, y, "Attitude=Bad Stand=1 Face=%s Turn=%d Group=Hob_Camp "
                                                             "Id=Hob_Camp_Lookout_%d" % (face, turn, n), -8))
            added += 1
    if went or added:
        m.save()
        print("%s: %d wanderers gone, %d lookouts" % (CAMP, went, added))


# ================================================================== scripts
def w(name, rows):
    K.write_script(name, rows, MAKER)


def the_order():
    w("Search Lair_Corner_Barrel", [
        (">Distance.From.Clicked.Tile", "48", "@far"),
        ("Display.Message", "Cyan", "You rummage through the barrel..", "-"), ("Play.Sound", "Pickup"), ("Wait", "1"),
        ("Get.Value", "ATTRIBUTE", "AshenOrder", V1),
        (">Got.Item", "Fathers_House_Key", "1", "@find"),
        (">Conditional", "$Variable.1=0", "@nothing"),
        ("Update.Attribute", "AshenOrder", "=1"),
        ("Give.Item", "Ashen_Order", "1"),
        ("Display.Message", "Yellow", "..and stuffed down the side, where you missed it before: a scrap of paper, "
                                      "folded small.", "-"),
        ("End",),
        ("@nothing",), ("Display.Message", "Cyan", "..rags and bones, nothing more.", "-"), ("End",),
        ("@find",), ("Give.Item", "Fathers_House_Key", "1"),
        (">Conditional", "$Variable.1=0", "@keyonly"),
        ("Update.Attribute", "AshenOrder", "=1"),
        ("Give.Item", "Ashen_Order", "1"),
        ("Display.Message", "Yellow", "..and there, under the rags: a brass house key. Tobias's! Wrapped round it, a "
                                      "scrap of paper, folded small.", "-"),
        ("End",),
        ("@keyonly",),
        ("Display.Message", "Yellow", "..and there, under the rags: a brass house key. Tobias's!", "-"),
        ("End",)] + FAR)
    w("Read Ashen_Order", [say("Notice", ORDER, ("Fold it away.", "@end")), ("@end",), ("End",)])
    w("Read Ashen_Ledger", [say("Notice", LEDGER, ("Close it.", "@end")), ("@end",), ("End",)])
    w("Kill Ashen_Priest", [
        ("Get.Value", "ATTRIBUTE", "RingQuest", V1),
        (">Conditional", "$Variable.1=1", "@end"),
        ("Give.Item", "Ember_Ring", "1"),
        ("Update.Attribute", "RingQuest", "=2"),
        ("Display.Message", "Yellow", "The Ashen Priest falls, and the Ember Ring rolls from his finger, glowing like a "
                                      "coal. Quest complete: The Ember Ring! Take it to Bert.", "Quest"),
        (">Got.Item", "Ashen_Ledger", "1", "@ledger"),
        ("End",),
        ("@ledger",), ("Give.Item", "Ashen_Ledger", "1"),
        ("Display.Message", "Cyan", "Something else falls from his robe: a little ledger, bound in black.", "-"),
        ("@end",), ("End",),
    ])


def aldous():
    w("Talk to Chapel_Verger", [
        ("Get.Value", "ATTRIBUTE", "AmuletQuest", V1),
        (">Conditional", "$Variable.1=3", "@not3"),
        (">Conditional", "$Equipped.Weapon<>none and $Equipped.Shield<>none", "@unarmed"),
        (">Conditional", "$Skill.Attack>=2 and $Skill.Defence>=2", "@untrained"),
        (">Conditional", "$Item.Chapel_Cellar_Key>=1", "@nokey"),
        ("Update.Attribute", "AmuletQuest", "=4"),
        say("Gravekeeper", "Mary's $Player.Boy. So the time has come.\\She came to me years ago with something to hide: an amulet. "
                           "We put it at the back of the caves under this chapel, behind bars no hand could reach "
                           "through.\\You have the trapdoor's key from Maren, and a sword and a shield, and you look as "
                           "if you can use them now. Go down. I'll not be far behind you.",
            ("Thank you, Brother.", "@end")),
        ("End",),
        ("@nokey",),
        say("Gravekeeper", "You're ready, I'd say. But the trapdoor's locked, and I gave its key to Maren, the doctor, "
                           "for safekeeping.", ("I'll ask her.", "@end")),
        ("End",),
        ("@untrained",),
        say("Gravekeeper", "Wooden swords and good intentions. Practise first: the goblins in the woods to the west, until "
                           "your Attack and Defence are level 2. Then come back.", ("I will.", "@end")),
        ("End",),
        ("@unarmed",),
        say("Gravekeeper", "Down there, with your sword and shield in your pack? Wield them both, then we'll talk.",
            ("Right.", "@end")),
        ("End",),
        ("@not3",), (">Conditional", "$Variable.1<3", "@after"),
        say("Gravekeeper", "Peace be with you. I'm Brother Aldous: I keep the chapel, and the graves out there. I buried "
                           "your mother this morning. She was a good woman.",
            ("What's down in the cellar?", "@cellar"), ("Goodbye.", "@end")),
        ("@cellar",),
        say("Gravekeeper", "Barrels and dust, and a trapdoor down to the caves, where no one should go unarmed.",
            ("I see.", "@end")),
        ("End",),
        ("@after",), (">Conditional", "$Variable.1=4", "@s5"),
        say("Gravekeeper", "The trapdoor is in the cellar, down the steps behind the altar. The amulet is at the very back "
                           "of the caves.", ("I'll find it.", "@end")),
        ("End",),
        ("@s5",), (">Conditional", "$Variable.1=5", "@done"),
        say("Gravekeeper", "Cast the Grasp at the bars, and the amulet will come to you.", ("I will.", "@end")),
        ("End",),
        ("@done",),
        say("Gravekeeper", "Keep the amulet close, and show it to no one but your father. Go with God.",
            ("Did my mother leave anything else with you? [if $Attr.JimmyQuest=0]", "@jimmy"),
            ("What did she mean, 'Jimmy knows where'? [if $Attr.JimmyQuest>=1 and $Attr.JimmyQuest<=2]", "@hint"),
            ("Someone else here says they're Mary's heir too. [if $Players.Near>=1]", "@heirs"), ("Goodbye.", "@end")),
        ("End",),
        ("@heirs",),                                # (the others the Shards know: only when one's near)
        say("Gravekeeper", "Do they? The Shards don't count the way we do. When the first king cut the dragon down, it "
                           "took royal blood to hold the cut, and that blood has run in more veins than one "
                           "since. The Shards will know each of you for an heir. Whether the crown does is your father's "
                           "business, not mine.", ("Thank you, Brother.", "@end")),
        ("End",),
        ("@jimmy",),                                # (What Jimmy Kept: build_isle_secrets.py)
        (">Quest.Can.Start", "JimmyQuest", "@end"),
        say("Gravekeeper", "One thing, yes. Near the end she gave me this, and made me promise to keep it till the "
                           "amulet was yours.\\A charm, in her hand. She studied at the Wizards' Court when she was "
                           "young, did you know? She said: 'Jimmy knows where. Read it by him, and ask him.'\\I read it "
                           "once. Nothing happened to me, thank the Lord. Perhaps it wants her blood to read it.",
            ("I'll try it.", "@charm")),
        ("@charm",), ("Update.Attribute", "JimmyQuest", "=1"),
        ("Give.Item", "Marys_Charm", "1"),
        ("Display.Message", "Yellow", "Quest started: What Jimmy Kept.", "Quest"),
        ("End",),
        ("@hint",), (">Got.Item", "Marys_Charm", "1", "@lost"),
        say("Gravekeeper", "Read her charm by Jimmy, and ask him. Not in the chapel, mind. I'll not have a cat at the "
                           "altar.", ("I'll go to him.", "@end")),
        ("End",),
        ("@lost",), ("Give.Item", "Marys_Charm", "1"),
        say("Gravekeeper", "Lost it? She left me two, in case. She knew you, I think, before you were born.",
            ("Thank you, Brother.", "@end")),
        ("@end",), ("End",),
    ])


def jimmy():
    w("Read Marys_Charm", [
        say("Notice", CHARM, ("Read it aloud.", "@aloud"), ("Fold it away.", "@end")),
        ("@aloud",),
        ("Turn.Into", "Cat", "120", "You read your mother's words aloud. The ink flares blue, the Shards in it take "
                                    "hold.. and you're a cat! For two minutes."),
        ("@end",), ("End",),
    ])
    w("Talk to Jimmy", [
        (">Conditional", "$Player.Form=-", "@animal"),
        ("Play.Sound", "Meow"),
        ("Display.Message", "Cyan", "Jimmy looks up at you and gives a little chirp, very pleased with himself.", "-"),
        ("End",),
        ("@animal",), ("Play.Sound", "Meow"),
        ("Get.Value", "ATTRIBUTE", "JimmyQuest", V1),
        (">Conditional", "$Variable.1>=1 and $Variable.1<=2", "@other"),
        ("Update.Attribute", "JimmyQuest", "=2"),
        say("Strawberry_Cat", "Mrrp! You smell like her. Like Mary. Like.. oh. OH. It's YOU, in there! The small one! "
                              "You got big.\\She said you'd come like this one day. She put a thing under the house, "
                              "through my way in: the gap low in the front wall, past the window. Only a cat fits. I've "
                              "been minding it. Nobody's touched it. I sat on it a lot.\\Go on, then. And after, come "
                              "and stroke me with hands. You owe me about four hundred strokes.",
            ("Thank you, Jimmy.", "@end")),
        ("End",),
        ("@other",), (">Conditional", "$Variable.1=3", "@stranger"),
        say("Strawberry_Cat", "You found it? Good. I'm still owed those strokes. I'm keeping count.", ("...", "@end")),
        ("End",),
        ("@stranger",),
        say("Strawberry_Cat", "Mrrp. You smell like someone I know. Come back with hands, and a fish.", ("...", "@end")),
        ("@end",), ("End",),
    ])
    w("Squeeze Through Cat_Gap", [
        (">Distance.From.Clicked.Entity", "48", "@far"),
        (">Conditional", "$Player.Form=Cat or $Player.Form=Strawberry_Cat", "@big"),
        ("Get.Value", "ATTRIBUTE", "JimmyQuest", V1),
        (">Conditional", "$Variable.1>=1 and $Variable.1<=2", "@dust"),
        ("Play.Sound", "Pickup"),
        ("Take.Item", "Marys_Charm", "1"),
        ("Give.Item", "Royal_Miniature", "1"),
        ("Update.Attribute", "JimmyQuest", "=3"),
        ("Display.Message", "Yellow", "You squeeze in under the cottage. Cobwebs, a dead beetle, Jimmy's smell on "
                                      "everything.. and tucked up between two joists, a little bundle in oilcloth, warm "
                                      "where he's slept on it. You drag it out in your teeth: a tiny portrait in a gold "
                                      "frame.", "-"),
        ("Display.Message", "Yellow", "Quest complete: What Jimmy Kept!", "Quest"),
        ("End",),
        ("@dust",), ("Display.Message", "Cyan", "You squeeze in under the cottage: dust, cobwebs and a dead beetle. "
                                                "Nothing worth a cat's while.", "-"), ("End",),
        ("@big",), ("Display.Message", "DarkRed", "The gap is far too small for you. Something small and furry might "
                                                  "fit.", "Denied"), ("End",)] + FAR)


def tobias():
    told = ("I found this in the lair. [if $Item.Ashen_Order>=1]", "@order")
    w("Talk to Tobias", [
        ("Get.Value", "ATTRIBUTE", "TobiasTin", V1),
        (">Conditional", "$Variable.1=0", "@s1"),
        (">Quest.Can.Start", "TobiasTin", "@plain"),
        say("Tobias", "There's my rescuer! Maren's feeding me up like a Midsummer goose.\\The house is yours, mind: I'll "
                      "not go back, not with those brutes so near it. Keep it well.\\There's one thing, though. My "
                      "savings, in a tin with a T on the lid. They had it off my shelf when they took me, and I'd wager "
                      "it's in that chest by their fire, up in their camp.",
            ("I'll get it back.", "@how"), told, ("Another time.", "@end")),
        ("@how",),
        say("Tobias", "Not all boots and elbows, you won't! Two of them keep watch up there now, and a hobgoblin's got "
                      "ears like a hare.\\Keep low and soft (that's sneaking: the slow way, the way you stand), and "
                      "keep out of the way they're looking. They look one way, mostly, and glance about now and then. "
                      "Get behind one and it'll never know you were there. Right beside one, mind, it'll smell you "
                      "whichever way it's facing.\\And if one does see you, it shouts, and the other comes.",
            ("Low, soft, and behind them.", "@start")),
        ("@start",), ("Update.Attribute", "TobiasTin", "=1"),
        ("Display.Message", "Yellow", "Quest started: Tobias's Tin.", "Quest"),
        ("End",),
        ("@s1",), (">Conditional", "$Variable.1<=2", "@plain"),
        (">Got.Item", "Tobias_Tin", "1", "@notyet"),
        ("Take.Item", "Tobias_Tin", "1"),
        ("Update.Attribute", "TobiasTin", "=3"),
        say("Tobias", "My tin! And not a dent more than it had. You went in soft, didn't you? I can tell.\\Here: a few "
                      "of these are yours. And keep up the sneaking. Some days it'll serve you better than a sword.",
            ("Thank you, Tobias.", "@done")),
        ("@done",), ("Display.Message", "Yellow", "Quest complete: Tobias's Tin!", "Quest"),
        ("End",),
        ("@notyet",),
        say("Tobias", "Low and soft, and out of the way they're looking. The chest's by their fire, in the camp "
                      "south-east of the village.", ("I'll go.", "@end"), told),
        ("End",),
        ("@plain",),
        say("Tobias", "There's my rescuer! Maren's feeding me up like a Midsummer goose.\\The house is yours, mind: I'll "
                      "not go back, not with those brutes so near it. Keep it well.", ("I will.", "@end"), told),
        ("End",),
        ("@order",),                                # (who sent them: build_isle_secrets.py)
        say("Tobias", "Let's see.. 'the old man who writes the Isle's papers'. That's me. So that's why they took me! "
                      "Every night the big one asked me where Mary's papers were. I never told them.\\And a hand in "
                      "ash. There's folk in the north who sign that way: the Ashen Hand, they call themselves. "
                      "Fire-worshippers, up past the Elderwood.\\What would the likes of them want with your mother? "
                      "Or with you? Keep that, and keep your eyes open over there.", ("I will.", "@end")),
        ("@end",), ("End",),
    ])
    w("Open Hob_Camp_Chest", [
        (">Distance.From.Clicked.Entity", "48", "@far"),
        (">Conditional", "$Attr.TobiasTin=1", "@loot"),
        ("Update.Attribute", "TobiasTin", "=2"),
        ("Give.Item", "Tobias_Tin", "1"),
        (">Conditional", "$Attr.GoblinChest=0", "@tin"),
        ("@loot",), (">Conditional", "$Attr.GoblinChest=0", "@empty"),
        ("Update.Attribute", "GoblinChest", "=1"),
        ("Play.Sound", "Chest"),
        ("Give.Item", "Bronze_Sword", "1"),
        ("Give.Item", "Gold_Coin(s)", "30"),
        ("End",),
        ("@tin",), ("Play.Sound", "Chest"), ("End",),
        ("@empty",), ("Display.Message", "Cyan", "The chest is empty.", "Empty"), ("End",)] + FAR)


def main():
    art()
    data()
    quests()
    places()
    the_order()
    aldous()
    jimmy()
    tobias()
    print("The Isle's secrets: done")


if __name__ == "__main__":
    main()
