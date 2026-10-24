"""The Isle's first quest, Passage to the Mainland, as a beginning: woodcutting, cooking, crafting a sword and a shield,
the chapel cellar, the caves, and a spell to reach what you can't. Run it once (again: it writes the same again).

  python -I "Dev\\migrate\\build_isle_quest.py"

The story (the attribute Passage, 0-12; FerryQuest>=4 is the old quest's ending, still honoured at the ferry):
   0  Maren the ferrywoman: the first crossing needs a ticket - her sister Bess keeps the ticket book.         -> 1
   1  Bess: a goblin came up out of the chapel cellar and stole the book. Not unarmed and hungry: here's an
      axe, chop three logs for the range.                                                                      -> 2
   2  Three logs to Bess. Fry an egg (from the coop) on her range.                                             -> 3
   3  The fried egg to Bess. Make a wooden sword and shield at the barn's workbench, and wield them.           -> 4
   4  Armed, to Bess: go and ask Brother Aldous about the cellar.                                              -> 5
   5  Brother Aldous (only now will he talk of it): the key's lost, among the cellar's barrels and crates.     -> 6
      (The chapel's steps down only let you by with a sword and a shield wielded, from here on.)
   6  The key, in a crate: the trapdoor opens for you.                                                         -> 7
   7  Deep in the caves, the goblin's cage: the book inside, the bars too close. Back to Brother Aldous.       -> 8
   8  Brother Aldous gives you a scroll of Grasp (a spell that keeps: it pulls things to you from afar).       -> 9
   9  Grasp at the cage: the book is yours.                                                                    -> 10
  10  The book to Bess: a stamped ticket.                                                                       -> 11
  11  The ticket to Maren: across to Southport.                                                                -> 12 (done)

Also: new characters start with no sword; the wooden sword (Crafting 1, 2 logs) and shield (Crafting 1, 3 logs) at a
workbench; a fried egg (an egg on a range); the pictures for the new things.
"""
import colorsys
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame  # noqa: E402
from dragonsword import ini  # noqa: E402
from build_isle import Map, TW, DATA, TILES_INI, obj_line  # noqa: E402

ENTS = os.path.join(DATA, "Entities.ini")
SPELLS = os.path.join(DATA, "Spells.ini")
RACKS = os.path.join(DATA, "ItemRacks.ini")
QUESTS = os.path.join(DATA, "Quests.ini")
SPR = os.path.join(ROOT, "Sprites")
CAGE = (5, 12)                                  # (on 1,1,-2: the west chamber of the caves)
THIEF = (8, 13)
DONE = 12


# ---------------------------------------------------------------- pictures
def load(*p):
    return pygame.image.load(os.path.join(SPR, *p)).convert_alpha()


def recolour(img, hue=None, sat=None, light=1.0):
    """img with its colours turned: hue (0-1) and saturation set, lightness scaled (outlines stay dark)."""
    out = img.copy()
    for y in range(img.get_height()):
        for x in range(img.get_width()):
            r, g, b, a = img.get_at((x, y))
            if a == 0:
                continue
            h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
            if l < 0.12:
                continue
            h = h if hue is None else hue
            s = s if sat is None else min(1, sat)
            r2, g2, b2 = colorsys.hls_to_rgb(h, min(1, l * light), s)
            out.set_at((x, y), (int(r2 * 255), int(g2 * 255), int(b2 * 255), a))
    return out


def fried_egg():
    s = pygame.Surface((32, 32), pygame.SRCALPHA)
    pygame.draw.ellipse(s, (60, 50, 40), (5, 10, 22, 15))
    pygame.draw.ellipse(s, (250, 248, 238), (6, 10, 20, 14))
    pygame.draw.ellipse(s, (230, 222, 200), (7, 18, 18, 6))
    pygame.draw.circle(s, (200, 120, 20), (16, 16), 5)
    pygame.draw.circle(s, (250, 180, 40), (16, 16), 4)
    pygame.draw.circle(s, (255, 236, 150), (14, 14), 1)
    return s


def ticket_book():
    s = pygame.Surface((32, 32), pygame.SRCALPHA)
    pygame.draw.rect(s, (40, 20, 20), (7, 7, 19, 20))
    pygame.draw.rect(s, (150, 40, 40), (8, 8, 17, 18))
    pygame.draw.rect(s, (240, 230, 200), (24, 9, 2, 16))                     # (the pages' edge)
    pygame.draw.rect(s, (110, 26, 26), (8, 8, 3, 18))                        # the spine
    pygame.draw.rect(s, (230, 190, 70), (13, 13, 9, 6), 1)                   # a gilt label
    pygame.draw.line(s, (230, 190, 70), (15, 16), (20, 16))
    return s


def goblin_cage():
    """A squat iron cage, padlocked, a red book on its floor inside."""
    s = pygame.Surface((32, 32), pygame.SRCALPHA)
    pygame.draw.rect(s, (0, 0, 0, 90), (4, 27, 26, 3))                       # (its shadow)
    pygame.draw.rect(s, (54, 48, 44), (4, 23, 24, 5))                        # the floor of it
    book = ticket_book()
    s.blit(pygame.transform.scale(book, (16, 16)), (9, 11))
    iron, lit = (58, 58, 64), (120, 120, 130)
    pygame.draw.rect(s, iron, (4, 5, 24, 3))                                 # the top
    pygame.draw.line(s, lit, (4, 5), (27, 5))
    for x in range(5, 28, 4):                                                # the bars
        pygame.draw.line(s, iron, (x, 8), (x, 24), 2)
        pygame.draw.line(s, lit, (x, 8), (x, 24))
    pygame.draw.rect(s, iron, (4, 23, 24, 2))
    pygame.draw.rect(s, (170, 140, 60), (14, 15, 5, 5))                      # the padlock
    pygame.draw.arc(s, (170, 140, 60), (14, 11, 5, 7), 0, 3.14, 1)
    return s


def draw_pictures():
    pygame.init()
    pygame.display.set_mode((1, 1))
    ents = os.path.join(SPR, "Entities")
    pygame.image.save(recolour(load("Entities", "Bronze_Sword.png"), hue=0.08, sat=0.45, light=0.9),
                      os.path.join(ents, "Wooden_Sword.png"))
    pygame.image.save(recolour(load("Entities", "Teleport_Scroll.png"), hue=0.33, sat=0.5),
                      os.path.join(ents, "Grasp_Scroll.png"))
    pygame.image.save(fried_egg(), os.path.join(ents, "Fried_Egg.png"))
    pygame.image.save(ticket_book(), os.path.join(ents, "Ticket_Book.png"))
    pygame.image.save(goblin_cage(), os.path.join(ents, "Goblin_Cage.png"))
    import shutil
    shutil.copy(os.path.join(SPR, "Tiles", "Stairs002.png"), os.path.join(SPR, "Tiles", "Chapel_Stairs001.png"))
    print("Drew the wooden sword, the Grasp scroll, the fried egg, the ticket book, the goblin's cage")


# ---------------------------------------------------------------- data
def section(path, name, keys):
    for k, v in keys:
        ini.write(name, k, v, path)


def data():
    section(ENTS, "Wooden_Sword", [("Type", "MapItem"), ("Examine.Info", "A sword whittled from a log: better than a fist."),
                                   ("Stackable", "1"), ("Value", "3"), ("Slot", "Weapon"), ("Attack", "1"),
                                   ("Defence", "0"), ("Durability", "60")])
    section(ENTS, "Fried_Egg", [("Type", "MapItem"), ("Use.Words", "Eat"), ("Examine.Info", "A fried egg, crisp at the edges."),
                                ("Value", "2"), ("Food.Value", "3")])
    section(ENTS, "Ticket_Book", [("Type", "MapItem"), ("Examine.Info", "Bess's ferry ticket book, and her stamp. The goblin "
                                  "chewed the corner."), ("Stackable", "1"), ("Droppable", "0"), ("Value", "0")])
    section(ENTS, "Grasp_Scroll", [("Type", "MapItem"), ("Use.Words", "Cast"),
                                   ("Examine.Info", "A scroll of Grasp: an unseen hand takes hold of a thing out of reach "
                                    "and brings it to you. Its words are woven into the vellum: it doesn't crumble."),
                                   ("Stackable", "1"), ("Droppable", "0"), ("Value", "0"), ("Spell", "Grasp")])
    section(ENTS, "Goblin_Cage", [("Type", "StaticObject"), ("Use.Words", "Open,Examine"),
                                  ("Examine.Info", "A goblin's cage, padlocked. Something red lies inside."), ("Solid", "1")])
    section(SPELLS, "Grasp", [("Cost", "2"), ("Cooldown", "2"), ("Scroll", "Grasp_Scroll"), ("Effect", "Grasp"),
                              ("Level", "1"), ("Range", "192"), ("Keep", "1"), ("Impact", "Puff"), ("Sound", "SpellCast"),
                              ("XP", "0.2")])
    # crafting: a wooden sword, and the shield at level 1 (a beginner's pair)
    have = [ini.read("CRAFT-Crafting", "Item%d" % i, "", RACKS) for i in range(1, 60)]
    have = [h for h in have if h]
    if not any(h.startswith("Wooden_Sword,") for h in have):
        ini.write("CRAFT-Crafting", "Item%d" % (len(have) + 1), "Wooden_Sword,Logs 2,0.15,1", RACKS)
    for i, h in enumerate(have, 1):
        if h.startswith("Wooden_Shield,"):
            ini.write("CRAFT-Crafting", "Item%d" % i, "Wooden_Shield,Logs 3,0.2,1", RACKS)
    tiles = os.path.join(DATA, "Tiles.ini")
    if not ini.section("Chapel_Stairs001", tiles):
        for k, v in ini.section("Stairs002", tiles):
            ini.write("Chapel_Stairs001", k, v, tiles)
        ini.write("Chapel_Stairs001", "Examine.Info", "Steps down to the chapel's cellar.", tiles)
    colours = os.path.join(ROOT, "Dev", "Minimap Colours.txt")
    if "\nChapel_Stairs001\t" not in "\n" + ini.read_text(colours):
        with open(colours, "a", encoding="cp1252", newline="\r\n") as f:
            f.write("Chapel_Stairs001\t255 0 0\n")
    # no sword to start with: you make your own
    tpl = os.path.join(ROOT, "Saves", "TEMPLATE.ini")
    text = open(tpl, "rb").read().decode("cp1252")
    text = text.replace("Weapon=Bronze_Sword\r\n", "").replace("Weapon=Bronze_Sword\n", "")
    open(tpl, "wb").write(text.encode("cp1252"))
    quest()
    print("Items, the Grasp spell, the crafting, the start kit, the quest")


def quest():
    """Quests.ini [Passage to the Mainland], its stages and markers."""
    text = open(QUESTS, "rb").read().decode("cp1252")
    nl = "\r\n" if "\r\n" in text else "\n"
    a = text.index("[Passage to the Mainland]")
    b = text.index(nl + "[", a + 5)
    stages = [
        ("Speak to Maren, the ferrywoman, at the end of the pier in the south of the Isle.", "Isle_Ferry_Pier"),
        ("The first crossing needs a ticket. Ask Bess, Maren's sister, the milkmaid on the farm in the north.", "Milkmaid_Farm"),
        ("A goblin stole Bess's ticket book. First, chop 3 logs for her range with the axe she lent you (Chop a tree).", "Milkmaid_Farm"),
        ("Collect an egg from the hen coop and fry it on Bess's range, in her hut (use the egg on the range). Take it to her.", "Hen_Coop"),
        ("Make a wooden sword and a wooden shield at the workbench in the barn, wield both, and show Bess.", "Dairy_Barn"),
        ("Ask Brother Aldous at the chapel about the cellar.", "Chapel_Door"),
        ("Brother Aldous lost the cellar key among the barrels and crates in the cellar. Find it (Search them).", "Chapel_Cellar"),
        ("Go down through the cellar's trapdoor into the caves and find Bess's ticket book.", "Thief_Cage"),
        ("The book is in a locked goblin's cage, out of reach. Ask Brother Aldous for help.", "Chapel_Door"),
        ("Cast Grasp at the goblin's cage to pull the ticket book out (Cast the scroll, then click the cage).", "Thief_Cage"),
        ("Take the ticket book back to Bess.", "Milkmaid_Farm"),
        ("Show your stamped ticket to Maren on the pier and sail to Southport.", "Isle_Ferry_Pier"),
    ]
    lines = ["[Passage to the Mainland]", "Giver=Woman", "Attribute=Passage"]
    lines += ["Stage%d=%s" % (i, s) for i, (s, _) in enumerate(stages)]
    lines += ["Done=%d" % DONE]
    lines += ["Marker%d=%s" % (i, m) for i, (_, m) in enumerate(stages)]
    lines += ["Type=Main", "Chapter=1", ""]
    text = text[:a] + nl.join(lines) + text[b:]
    open(QUESTS, "wb").write(text.encode("cp1252"))


# ---------------------------------------------------------------- the maps
def maps():
    m = Map("3,1,0")
    for y in range(1, 22):
        for x in range(1, 26):
            if m.tile(x, y) == "Stairs002":
                m.set(x, y, tile="Chapel_Stairs001")
    m.save()
    c = Map("1,1,-2")
    if not c.has_line("StaticObject\tGoblin_Cage"):
        cx, cy = CAGE
        c.ents.append(obj_line("StaticObject", "Goblin_Cage", cx, cy))
        c.ents.append("Id\tThief_Cage\t%d\t%d" % (cx + 1, cy))     # (the place, for the journal's marker)
        tx, ty = THIEF
        c.ents.append(obj_line("NPC", "Goblin", tx, ty, "Attitude=Bad Zone=6,11,10,15 Chase=4,10,12,17 Name=Goblin_Thief",
                               -8))
        c.save()
    print("The chapel's steps (guarded); the goblin's cage and its thief in the caves")


# ---------------------------------------------------------------- the scripts (labels, not line numbers)
def write(name, rows):
    """rows: ("@label",) marks a line; a field "@label" is that line's number. Numbered 01, 02... here."""
    numbered, labels, n = [], {}, 0
    for r in rows:
        if len(r) == 1 and r[0].startswith("@"):
            labels[r[0]] = n + 1
            continue
        n += 1
        numbered.append(r)
    out = ["// Passage to the Mainland. Generated by Dev\\migrate\\build_isle_quest.py"]
    for i, r in enumerate(numbered, 1):
        fields = [("%02d" % labels[f]) if isinstance(f, str) and f.startswith("@") else str(f) for f in r]
        out.append("%02d\t%s" % (i, "\t".join(fields)))
    with open(os.path.join(DATA, "Scripts", name + ".txt"), "w", encoding="cp1252", newline="\r\n") as f:
        f.write("\n".join(out) + "\n")


def say(npc, text, *answers):
    r = ["Display.Conversation", npc, text]
    for words, goto in answers:
        r += [words, goto]
    return tuple(r)


def scripts():
    V = "Variable.1"
    write("Talk to Woman", [
        ("Get.Value", "ATTRIBUTE", "Passage", V + "$"),
        ("Get.Value", "ATTRIBUTE", "FerryQuest", "Variable.2$"),
        (">On.Map", "1,2,0", "@back"),
        (">Conditional", "$Variable.1>=%d or $Variable.2>=4" % DONE, "@not_done"),
        say("Woman", "Ahoy again! Southport, is it? The fare is 1 gold coin.", ("Yes, take me to Southport (1 gold).", "@pay"),
            ("Not today.", "@end")),
        ("@pay",), (">Got.Item", "Gold_Coin(s)", "1", "@no_gold"),
        ("Take.Item", "Gold_Coin(s)", "1"),
        ("Goto.Script", "Ferry to Southport"),
        ("End",),
        ("@not_done",), (">Got.Item", "Ferry_Ticket", "1", "@no_ticket"),
        say("Woman", "A ticket, stamped by my sister - and you got her book back from that goblin! Hop aboard. After this "
            "it's a gold coin a crossing.", ("Take me to Southport.", "@sail"), ("Not yet.", "@end")),
        ("@sail",), ("Take.Item", "Ferry_Ticket", "1"),
        ("Update.Attribute", "Passage", "=%d" % DONE),
        ("Display.Message", "Yellow", "Quest complete: Passage to the Mainland! The ferry is yours for 1 gold a crossing."),
        ("Goto.Script", "Ferry to Southport"),
        ("End",),
        ("@no_ticket",), (">Conditional", "$Variable.1=0", "@waiting"),
        say("Woman", "Ahoy there! I'm Maren: I sail across the strait to Southport, on the southern mainland.\\First "
            "crossing is by ticket only. My sister Bess, the milkmaid, keeps the ticket book, on the farm up north.",
            ("I'll get a ticket.", "@started"), ("Not today.", "@end")),
        ("@started",), ("Update.Attribute", "Passage", "=1"),
        ("Display.Message", "Yellow", "Quest started: Passage to the Mainland. (H: your journal)"),
        ("End",),
        ("@waiting",), say("Woman", "No ticket, no crossing, I'm afraid. Bess has the ticket book, on the farm in the north "
                           "of the Isle.", ("I'll see her.", "@end")),
        ("End",),
        ("@back",), (">On.Map", "1,3,0", "@farewell"),
        say("Woman", "Back to the Isle, is it? That's 1 gold coin, then climb aboard.",
            ("Yes, back to the Isle (1 gold).", "@pay_back"), ("Not yet.", "@end")),
        ("@pay_back",), (">Got.Item", "Gold_Coin(s)", "1", "@no_gold"),
        ("Take.Item", "Gold_Coin(s)", "1"),
        ("Goto.Script", "Ferry to the Isle"),
        ("End",),
        ("@no_gold",), ("Display.Refusal", "You need 1 gold coin for the ferry fare."),
        ("End",),
        ("@farewell",), say("Woman", "Fair winds to you!", ("Goodbye.", "@end")),
        ("@end",), ("End",),
    ])
    write("Talk to Milkmaid", [
        say("Milkmaid", "Morning! Mind the cows, they're friendly but they tread on toes.\\Use a bucket on a cow for milk, "
            "shears on a sheep for wool. The hens lay in their coop, by the barn.", ("What do you sell?", "@shop"),
            ("What's wool for?", "@wool"), ("About a ferry ticket...", "@ticket"), ("Goodbye.", "@end")),
        ("@shop",), ("Display.Item.Rack", "SPECIFIC", "Milkmaid", "SHOP-Dairy", "@end"),
        ("End",),
        ("@wool",), say("Milkmaid", "Spin it into balls of wool on a workbench, there's one in the barn. Cowhide can be "
                        "tanned into leather there too.", ("Thanks!", "@end")),
        ("End",),
        ("@ticket",), ("Get.Value", "ATTRIBUTE", "Passage", V + "$"),
        (">Conditional", "$Variable.1=0", "@s1"),
        say("Milkmaid", "A ferry ticket? My sister Maren sails the ferry, down at the pier in the south. Ask her first.",
            ("I will.", "@end")),
        ("End",),
        ("@s1",), (">Conditional", "$Variable.1=1", "@s2"),
        say("Milkmaid", "She sent you? Oh, love - my ticket book's gone! A goblin came up out of the chapel cellar in the "
            "night, snatched it, stamp and all, and ran back down into the caves. No book, no ticket.\\Go after it? Not "
            "like that: no sword, nothing in your belly. Let's set you right first. Here's my old axe: chop me three "
            "logs for the range.", ("I'll chop some logs.", "@axe")),
        ("@axe",), ("Give.Item", "Bronze_Axe", "1"),
        ("Update.Attribute", "Passage", "=2"),
        ("Display.Message", "Yellow", "Passage to the Mainland: chop 3 logs for Bess (Chop a tree, with her axe)."),
        ("End",),
        ("@s2",), (">Conditional", "$Variable.1=2", "@s3"),
        (">Got.Item", "Logs", "3", "@no_logs"),
        ("Take.Item", "Logs", "3"),
        ("Update.Attribute", "Passage", "=3"),
        say("Milkmaid", "Good dry logs! Now, a hot meal: take an egg from the nests in the hen coop and fry it on my range, "
            "in the hut there (use the egg on the range). Bring it here and I'll check it's done.", ("I'll cook an egg.", "@end")),
        ("End",),
        ("@no_logs",), say("Milkmaid", "Three logs, love. Chop a tree with the axe I gave you.", ("I'll keep chopping.", "@end")),
        ("End",),
        ("@s3",), (">Conditional", "$Variable.1=3", "@s4"),
        (">Got.Item", "Fried_Egg", "1", "@no_egg"),
        ("Update.Attribute", "Passage", "=4"),
        say("Milkmaid", "Lovely and crisp - eat that before you go anywhere! Now: a sword and a shield. There's a workbench "
            "in the barn. Make a wooden sword and a wooden shield from logs (Make, on the workbench), and wield them both.",
            ("I'll make them.", "@end")),
        ("End",),
        ("@no_egg",), say("Milkmaid", "A fried egg, love: one from the coop, cooked on my range.", ("Right.", "@end")),
        ("End",),
        ("@s4",), (">Conditional", "$Variable.1=4", "@s10"),
        (">Conditional", "$Equipped.Weapon<>none and $Equipped.Shield<>none", "@unarmed"),
        ("Update.Attribute", "Passage", "=5"),
        say("Milkmaid", "Now you look the part! That cellar is Brother Aldous's - he keeps the chapel, by the graveyard. Ask "
            "him about it. And bring my book back!", ("I will.", "@end")),
        ("End",),
        ("@unarmed",), say("Milkmaid", "A sword AND a shield, love, and wield them both. The workbench is in the barn.",
                           ("Right.", "@end")),
        ("End",),
        ("@s10",), (">Conditional", "$Variable.1=10", "@later"),
        (">Got.Item", "Ticket_Book", "1", "@later"),
        ("Take.Item", "Ticket_Book", "1"),
        ("Give.Item", "Ferry_Ticket", "1"),
        ("Update.Attribute", "Passage", "=11"),
        say("Milkmaid", "My ticket book! And the stamp! Oh, you're a treasure. Here's your ticket, stamped and all: show it "
            "to Maren on the pier.", ("Thank you!", "@end")),
        ("End",),
        ("@later",), (">Conditional", "$Variable.1>=11", "@hunting"),
        say("Milkmaid", "You've had your ticket. After the first crossing Maren just charges a gold coin.", ("Right.", "@end")),
        ("End",),
        ("@hunting",), say("Milkmaid", "Any sign of my ticket book? That goblin took it down into the caves, under the chapel.",
                           ("I'm on it.", "@end")),
        ("@end",), ("End",),
    ])
    write("Talk to Chapel_Verger", [
        ("Get.Value", "ATTRIBUTE", "Passage", V + "$"),
        (">Conditional", "$Variable.1<5", "@greet"),          # (true: on; false: off to the label)
        say("Gravekeeper", "Peace be with you. I'm Brother Aldous: I keep the chapel, and the graves out there.",
            ("Goodbye.", "@end")),
        ("End",),
        ("@greet",), (">Conditional", "$Variable.1=5", "@s6"),
        say("Gravekeeper", "Peace be with you. I'm Brother Aldous: I keep the chapel, and the graves out there.",
            ("What's down in the cellar?", "@lost"), ("Goodbye.", "@end")),
        ("@lost",), ("Update.Attribute", "Passage", "=6"),
        say("Gravekeeper", "A goblin, from my cellar? So that was the scratching in the night! There's a trapdoor down there, "
            "to the caves under the Isle. Locked - and I've lost the key.\\I had it last down there, sorting the barrels "
            "and crates. Find it, and you can go down. You're armed, I see: good.", ("I'll look for it.", "@end")),
        ("End",),
        ("@s6",), (">Conditional", "$Variable.1=6", "@s7"),
        say("Gravekeeper", "Found my key yet? It's down in the cellar somewhere, among the barrels and crates. The steps are "
            "behind the altar.", ("I'll keep looking.", "@end")),
        ("End",),
        ("@s7",), (">Conditional", "$Variable.1=7", "@s8"),
        say("Gravekeeper", "You've the key: the trapdoor will open for you. Go carefully.", ("I will.", "@end")),
        ("End",),
        ("@s8",), (">Conditional", "$Variable.1=8", "@s9"),
        say("Gravekeeper", "In a cage, with bars too close for your hand? Then you need a little magic. Here: a scroll of "
            "Grasp. Read it at the cage and an unseen hand will bring the book to you.\\It won't crumble like other "
            "scrolls: keep it. It'll fetch you anything you can see but not reach.", ("Thank you, Brother.", "@scroll")),
        ("@scroll",), ("Give.Item", "Grasp_Scroll", "1"),
        ("Update.Attribute", "Passage", "=9"),
        ("Display.Message", "Yellow", "You can cast Grasp: Cast the scroll, then click what you want brought to you."),
        ("End",),
        ("@s9",), (">Conditional", "$Variable.1=9", "@after"),
        say("Gravekeeper", "Read the Grasp scroll at the cage: Cast it, then click the cage.", ("I will.", "@end")),
        ("End",),
        ("@after",), say("Gravekeeper", "Peace be with you, friend of the chapel.", ("Goodbye.", "@end")),
        ("@end",), ("End",),
    ])
    write("Climb Down Chapel_Stairs", [
        (">Conditional", "$Attr.Passage>=5 or $Attr.FerryQuest>=4", "@private"),
        (">Conditional", "$Equipped.Weapon<>none and $Equipped.Shield<>none", "@unarmed"),
        ("Get.Value", "CALCULATION", "$Map.Z-1", "Variable.9$"),
        ("Teleport", "$Player.X,$Player.Y", "$Map.X,$Map.Y,$Variable.9"),
        ("Play.Sound", "Ladder"),
        ("Display.Message", "Cyan", "You go down the steps, into the cellar."),
        ("End",),
        ("@private",), ("Display.Refusal", "Brother Aldous stops you: \"The cellar's not for visitors, friend.\""),
        ("End",),
        ("@unarmed",), ("Display.Refusal", "Brother Aldous stops you: \"Not down there without a sword and a shield!\""),
        ("End",),
    ])
    for kind, nothing in (("Cellar_Barrel", "Only old candle ends and dust."),
                          ("Cellar_Crate", "Mouldy hymn books. No key.")):
        write("Search " + kind, [
            (">Distance.From.Clicked.Tile", "40", "@far"),
            ("Get.Value", "CALCULATION", "$Tile.under.Cursor.X", "Variable.5$"),
            ("Get.Value", "CALCULATION", "$Tile.under.Cursor.Y", "Variable.6$"),
            ("Display.Message", "Cyan", "You rummage through the %s..." % kind.split("_")[1].lower()),
            ("Play.Sound", "Pickup"),
            ("Wait", "1"),
            (">Conditional", "$Variable.5=17 and $Variable.6=12 and $Attr.Passage>=6", "@nothing"),
            (">Got.Item", "Chapel_Cellar_Key", "1", "@found"),
            ("@nothing",), ("Display.Message", "Cyan", nothing),
            ("End",),
            ("@found",), ("Give.Item", "Chapel_Cellar_Key", "1"),
            ("Display.Message", "Yellow", "...and there, under the straw: an iron key. The cellar key!"),
            (">Conditional", "$Attr.Passage=6", "@done"),
            ("Update.Attribute", "Passage", "=7"),
            ("@done",), ("End",),
            ("@far",), ("Display.Message", "DarkRed", "You are too far away!"),
            ("End",),
        ])
    write("Use Egg With Range", [
        (">Distance.From.Clicked.Entity", "40", "@far"),
        (">Got.Item", "Egg", "1", "@none"),
        ("Take.Item", "Egg", "1"),
        ("Display.Message", "Cyan", "You crack the egg onto the hot range..."),
        ("Play.Sound", "CookingFood"),
        ("Wait", "2"),
        ("Display.Message", "Yellow", "...and fry it to a turn!"),
        ("Update.Skill", "Cooking", "+0.05"),
        ("Give.Item", "Fried_Egg", "1"),
        ("End",),
        ("@none",), ("Display.Message", "DarkRed", "You don't have an egg."),
        ("End",),
        ("@far",), ("Display.Message", "DarkRed", "You are too far away!"),
        ("End",),
    ])
    write("Open Goblin_Cage", [
        ("Get.Value", "ATTRIBUTE", "Passage", V + "$"),
        (">Conditional", "$Variable.1<10", "@empty"),
        (">Conditional", "$Variable.1=7", "@locked"),
        ("Update.Attribute", "Passage", "=8"),
        ("Display.Message", "Yellow", "Passage to the Mainland: the ticket book is in the cage, out of reach. Brother "
         "Aldous might know a way."),
        ("@locked",), ("Display.Refusal", "The cage is padlocked fast, its bars too close for a hand. Inside: Bess's ticket book!"),
        ("End",),
        ("@empty",), ("Display.Message", "Cyan", "The cage is empty now."),
        ("End",),
    ])
    write("Grasp Goblin_Cage", [
        ("Get.Value", "ATTRIBUTE", "Passage", V + "$"),
        (">Conditional", "$Variable.1<10", "@empty"),
        ("Give.Item", "Ticket_Book", "1"),
        ("Update.Attribute", "Passage", "=10"),
        ("Display.Message", "Yellow", "The ticket book slips between the bars and into your hands! Take it back to Bess."),
        ("End",),
        ("@empty",), ("Display.Message", "Cyan", "There's nothing left in the cage."),
        ("End",),
    ])
    # the old Brother Aldous asides (the key lost) are these scripts now; the trapdoor opens with the key, as it was
    print("Scripts: Maren, Bess, Brother Aldous, the chapel steps, the cellar's crates, the egg, the cage")


def main():
    draw_pictures()
    data()
    maps()
    scripts()


if __name__ == "__main__":
    main()
