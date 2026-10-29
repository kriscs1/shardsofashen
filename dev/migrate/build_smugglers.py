"""The Smugglers' Run: a hollow barrel, a tunnel, a camp on the cove you sneak through. Run it once (again: it sees
what's done).

  python -I "dev\\migrate\\build_smugglers.py"

  * Sergeant Holt (a Guard, Id=Smuggler_Sergeant), inside the King's castle's south gate (4,4,0): smuggled goods in
    the market, and the fishermen's talk of an old barrel on the lake path nobody moves.                 SmugglerQuest 1
  * The barrel (Suspicious_Barrel001, 3,5,0 by the lake): Search it - it's hollow, a hatch and a ladder down.   -> 2
  * The tunnel (3,5,-1 and 4,5,-1) under the shore, its far ladder up into the smugglers' camp on the cove (4,5,0):
    a palisade, tents, stacked cargo (it hides you), a campfire; smugglers on watch at the gate and the fire and
    one walking the camp. They see only ahead of them (Sight.Cone), never through cargo, tents or the palisade
    (line of sight) - but right beside one, you're seen. One that sees you raises the whole camp (Group=COVE).
  * Red Meg (a Captain, Id=Red_Meg) in her tent: reach her and she'll deal - the camp is your friend from then on
    (Friendly.If=$Attr.SmugglerQuest>=3), and she sells what no market does.                                    -> 3
  * Back to Holt: 60 gold.                                                                                      -> 4 (done)
"""
import os
import random
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame  # noqa: E402
from ashen import ini  # noqa: E402
from build_isle import Map, XT, YT, TW, DATA, TILES_INI, obj_line  # noqa: E402
from build_isle_quest import write, say  # noqa: E402

ENTS = os.path.join(DATA, "Entities.ini")
SPR = os.path.join(ROOT, "sprites")
BARREL = (12, 14)                     # on 3,5,0, by the lake path
CAMP = (5, 10, 17, 19)                # the palisade on 4,5,0 (the gate: 11-12 in its south side)
GATE = (11, 12)
HATCH = (16, 11)                      # in the camp's north-east corner; the tunnel's ladder under it
MEG = (7, 12)
SERGEANT = (11, 18)                   # on 4,4,0
WALL_DATA = "0" * 49
COVE = "Attitude=Bad Group=COVE Friendly.If=$Attr.SmugglerQuest>=3"


# ---------------------------------------------------------------- pictures
def cargo():
    """Crates and a sack piled high: nobody sees past them."""
    s = pygame.Surface((32, 32), pygame.SRCALPHA)
    sh = pygame.Surface((32, 32), pygame.SRCALPHA)
    pygame.draw.rect(sh, (0, 0, 0, 100), (3, 27, 28, 4))
    s.blit(sh, (0, 0))

    def crate(x, y, w, h):
        pygame.draw.rect(s, (40, 26, 14), (x, y, w, h))
        pygame.draw.rect(s, (150, 106, 60), (x + 1, y + 1, w - 2, h - 2))
        pygame.draw.line(s, (110, 76, 40), (x + 1, y + 1), (x + w - 2, y + h - 2))
        pygame.draw.line(s, (110, 76, 40), (x + w - 2, y + 1), (x + 1, y + h - 2))
        pygame.draw.line(s, (186, 140, 86), (x + 1, y + 1), (x + w - 2, y + 1))
    crate(2, 14, 16, 14)
    crate(15, 16, 15, 12)
    crate(6, 2, 15, 13)
    pygame.draw.ellipse(s, (40, 30, 20), (19, 3, 11, 13))                                     # a sack
    pygame.draw.ellipse(s, (196, 170, 120), (20, 4, 9, 11))
    pygame.draw.line(s, (150, 120, 80), (24, 4), (25, 7))
    return s


def campfire():
    s = pygame.Surface((32, 32), pygame.SRCALPHA)
    for a in range(8):                                                                          # a ring of stones
        import math
        x = 16 + 11 * math.cos(a * math.pi / 4)
        y = 21 + 6 * math.sin(a * math.pi / 4)
        pygame.draw.circle(s, (110, 106, 100), (int(x), int(y)), 3)
        pygame.draw.circle(s, (150, 146, 140), (int(x) - 1, int(y) - 1), 1)
    pygame.draw.line(s, (90, 60, 30), (9, 24), (23, 18), 3)                                    # logs
    pygame.draw.line(s, (100, 66, 34), (9, 18), (23, 24), 3)
    pygame.draw.polygon(s, (230, 90, 20), [(10, 22), (16, 4), (22, 22)])                        # flames
    pygame.draw.polygon(s, (250, 170, 40), [(12, 22), (16, 9), (20, 22)])
    pygame.draw.polygon(s, (255, 236, 150), [(14, 22), (16, 14), (18, 22)])
    return s


def draw_pictures():
    pygame.init()
    pygame.display.set_mode((1, 1))
    tiles = os.path.join(SPR, "Tiles")
    for name, img in (("Cargo_Stack001", cargo()), ("Campfire001", campfire())):   # (the palisade: build_palisades.py)
        pygame.image.save(img, os.path.join(tiles, name + ".png"))
    for new, old in (("Suspicious_Barrel001", "Barrel001"), ("Tunnel_Ladder001", "Ladder001"),
                     ("Tunnel_Ladder002", "Ladder001")):
        shutil.copy(os.path.join(tiles, old + ".png"), os.path.join(tiles, new + ".png"))
    shutil.copy(os.path.join(SPR, "Entities", "Bandit.png"), os.path.join(SPR, "Entities", "Smuggler.png"))
    walk = os.path.join(SPR, "Walk")
    for f in os.listdir(walk):                                                                  # the smugglers: bandits
        if f.startswith("Bandit") and f[6:7].isdigit():
            shutil.copy(os.path.join(walk, f), os.path.join(walk, "Smuggler" + f[6:]))
    print("Drew the palisade, the cargo, the campfire; the barrel, the ladders, the smugglers")


# ---------------------------------------------------------------- data
def tile(name, **keys):
    if ini.section(name, TILES_INI):
        return
    for k, v in keys.items():
        ini.write(name, k.replace("_", "."), v, TILES_INI)


def data():
    tile("Palisade001", Walkable_Data=WALL_DATA, Show_Name="1", Use_Words="",
         Examine_Info="A palisade of sharpened logs: no seeing over it.", Line_of_Sight="0", Layer="Decor")
    tile("Cargo_Stack001", Walkable_Data=WALL_DATA, Show_Name="1", Use_Words="",
         Examine_Info="Crates and sacks piled high, stencilled with names of ports you've never heard of.",
         Line_of_Sight="0", Layer="Decor")
    tile("Campfire001", Walkable_Data="1111111110001111000111100011111111111111111111111", Show_Name="1", Use_Words="",
         Examine_Info="A crackling campfire.", Line_of_Sight="1", Light="60", Layer="Decor")
    if not ini.section("Suspicious_Barrel001", TILES_INI):
        for k, v in ini.section("Barrel001", TILES_INI):
            ini.write("Suspicious_Barrel001", k, v, TILES_INI)
        ini.write("Suspicious_Barrel001", "Use.Words", "Search,Examine", TILES_INI)
        ini.write("Suspicious_Barrel001", "Examine.Info", "A barrel of salted fish, by the smell. It's been here "
                  "a long while: nobody seems to move it.", TILES_INI)
    for n in ("Tunnel_Ladder001", "Tunnel_Ladder002"):
        if not ini.section(n, TILES_INI):
            for k, v in ini.section("Ladder001", TILES_INI):
                ini.write(n, k, v, TILES_INI)
            ini.write(n, "Use.Words", "Climb Up,Examine", TILES_INI)
            ini.write(n, "Examine.Info", "A ladder, worn smooth by many feet.", TILES_INI)
    colours = os.path.join(ROOT, "dev", "Minimap Colours.txt")
    have = "\n" + ini.read_text(colours)
    with open(colours, "a", encoding="cp1252", newline="\r\n") as f:
        for n, c in (("Palisade001", "110 76 40"), ("Cargo_Stack001", "150 106 60"), ("Campfire001", "240 120 30"),
                     ("Suspicious_Barrel001", "120 80 40"), ("Tunnel_Ladder001", "255 0 0"),
                     ("Tunnel_Ladder002", "255 0 0")):
            if "\n" + n + "\t" not in have:
                f.write("%s\t%s\n" % (n, c))
    if not ini.section("Smuggler", ENTS):
        for k, v in ini.section("Bandit", ENTS):
            ini.write("Smuggler", k, v, ENTS)
        for k, v in (("Examine.Info", "A smuggler, salt-stained and watchful."), ("Aggro.Range", "170"),
                     ("Sight.Cone", "110"), ("Respawn", "60"), ("Chase.Radius", "8"),
                     ("Drops", "Bones,1-1,100 Gold_Coin(s),5-14,90 Healing_Draught,1-1,6")):
            ini.write("Smuggler", k, v, ENTS)
    racks = os.path.join(DATA, "ItemRacks.ini")
    if not ini.section("SHOP-Smugglers", racks):
        stock = [("Teleport_Scroll", 3), ("Owl_Potion", 3), ("Combat_Potion", 3), ("Healing_Draught", 6),
                 ("Iron_Sword", 1)]
        for k, v in (("Type", "Shop"), ("Buy.Rate", "1.5"), ("Sell.Rate", "0.9"), ("Specific", "0")):
            ini.write("SHOP-Smugglers", k, v, racks)
        n = 0
        for name, q in stock:
            if ini.section(name, ENTS):
                n += 1
                ini.write("SHOP-Smugglers", "Item%d" % n, "%s,%d" % (name, q), racks)
    quest()
    print("Tiles, the Smuggler, Red Meg's shop, the quest")


def quest():
    path = os.path.join(DATA, "Quests.ini")
    if ini.section("The Smugglers' Run", path):
        return
    text = open(path, "rb").read().decode("cp1252")
    nl = "\r\n" if "\r\n" in text else "\n"
    lines = ["", "[The Smugglers' Run]", "Giver=Guard", "Attribute=SmugglerQuest",
             "Stage0=Sergeant Holt, at the King's castle's south gate, wants to know how smuggled goods get into town.",
             "Stage1=The fishermen talk of an old barrel on the lake path, south-west of the castle, that nobody "
             "ever moves. Search it.",
             "Stage2=The barrel hides a tunnel to a smugglers' camp on the cove. Get to their leader without being "
             "seen: they only see ahead of them, never through cargo, tents or walls.",
             "Stage3=Red Meg made you a deal: tell Sergeant Holt.",
             "Done=4", "Marker1=Hollow_Barrel", "Marker2=Smugglers_Cove", "Marker3=Sergeant_Post", "Type=Side", ""]
    open(path, "wb").write((text.rstrip("\r\n") + nl + nl.join(lines)).encode("cp1252"))


# ---------------------------------------------------------------- maps
def cave(m, floor_cells, rng):
    for y in range(1, YT + 1):
        for x in range(1, XT + 1):
            if (x, y) in floor_cells:
                m.set(x, y, tile=rng.choice(["Cave_Floor001", "Cave_Floor001", "Cave_Floor003"]))
            elif any((x + dx, y + dy) in floor_cells for dx in (-1, 0, 1) for dy in (-1, 0, 1)):
                m.set(x, y, tile=rng.choice(["Cave_Wall001", "Cave_Wall002"]))


def tunnels():
    rng = random.Random(77)
    if not os.path.exists(os.path.join(ROOT, "maps", "3,5,-1.txt")):
        w = Map("3,5,-1", new=True)
        bx, by = BARREL
        cells = {(bx, by), (bx, by + 1)}
        for x in range(bx, XT + 1):                        # east, under the shore, wider here and there
            cells.add((x, by + 1))
            if 15 <= x <= 19:
                cells.add((x, by + 2))
            if x % 4 == 0:
                cells.add((x, by))
        cave(w, cells, rng)
        w.set(bx, by, decor="Tunnel_Ladder001")
        w.ents = [obj_line("NPC", "Rat", 18, by + 2, "Attitude=Bad Zone=15,%d,22,%d" % (by + 1, by + 2))]
        w.save()
    if not os.path.exists(os.path.join(ROOT, "maps", "4,5,-1.txt")):
        e = Map("4,5,-1", new=True)
        hx, hy = HATCH
        by = BARREL[1] + 1
        cells = set()
        for x in range(1, hx + 1):
            cells.add((x, by))
            if 6 <= x <= 9:
                cells.add((x, by - 1))
        for y in range(hy, by + 1):
            cells.add((hx, y))
            cells.add((hx - 1, y) if y < by - 1 else (hx, y))
        cave(e, cells, rng)
        e.set(hx, hy, decor="Tunnel_Ladder002")
        e.ents = [obj_line("NPC", "Bat", 8, by, "Attitude=Bad Zone=4,%d,12,%d" % (by - 1, by))]
        e.save()
    print("The smugglers' tunnel: 3,5,-1 and 4,5,-1")


def surface():
    lake = Map("3,5,0")
    bx, by = BARREL
    if lake.decor(bx, by) != "Suspicious_Barrel001":
        lake.set(bx, by, decor="Suspicious_Barrel001")
        lake.ents = [ln for ln in lake.ents if not ln.startswith("Id\tHollow_Barrel")]
        lake.ents.append("Id\tHollow_Barrel\t%d\t%d" % (bx, by + 1))
        lake.save()
    castle = Map("4,4,0")
    if not castle.has_line("Id=Smuggler_Sergeant"):
        sx, sy = SERGEANT
        castle.ents.append(obj_line("NPC", "Guard", sx, sy, "Attitude=Good Stand=1 Face=S Id=Smuggler_Sergeant "
                                    "Name=Sergeant_Holt", -8))
        castle.ents.append("Id\tSergeant_Post\t%d\t%d" % (sx, sy + 1))
        castle.save()
    camp()
    print("The hollow barrel, Sergeant Holt, the camp on the cove")


def camp():
    m = Map("4,5,0")
    if m.has_line("Id=Red_Meg"):
        return
    x1, y1, x2, y2 = CAMP
    for y in range(y1, y2 + 1):                       # cleared ground, a palisade round it
        for x in range(x1, x2 + 1):
            edge = x in (x1, x2) or y in (y1, y2)
            m.set(x, y, tile="Grass001" if not m.tile(x, y).startswith("Sand") else m.tile(x, y), decor="")
            if edge and not (y == y2 and x in GATE):
                m.set(x, y, decor="Palisade001")
    for x, y in ((GATE[0], y2), (GATE[1], y2), (GATE[0], y2 - 1), (GATE[1], y2 - 1), (11, 16), (12, 16), (11, 17),
                 (12, 17)):
        m.set(x, y, tile="Dirt001")
    for x, y, d in ((6, 11, "Tent001"), (8, 11, "Tent002"), (6, 13, "Tent001"),          # Red Meg's tents
                    (12, 11, "Tent002"), (6, 17, "Tent001"), (7, 18, "Tent002"), (16, 17, "Tent001"),
                    (14, 11, "Cargo_Stack001"), (15, 13, "Cargo_Stack001"), (10, 12, "Cargo_Stack001"),
                    (13, 12, "Cargo_Stack001"), (9, 15, "Cargo_Stack001"), (14, 16, "Cargo_Stack001"),
                    (8, 13, "Cargo_Stack001"), (11, 15, "Campfire001"),
                    (HATCH[0], HATCH[1], "Hatch001"), (16, 15, "Barrel001"), (13, 18, "Crate001")):
        m.set(x, y, decor=d)
    m.ents = [ln for ln in m.ents if not (ln.startswith("NPC\tWolf") and _inside(ln)) and
              not (ln.startswith("NPC\tRabbit") and _inside(ln))]
    mx, my = MEG
    m.ents += [
        obj_line("NPC", "Captain", mx, my, "Attitude=Good Stand=1 Face=E Id=Red_Meg Name=Red_Meg", -8),
        obj_line("NPC", "Smuggler", GATE[0] - 1, y2 - 1, COVE + " Stand=1 Face=S Name=Smuggler", -8),     # at the gate
        obj_line("NPC", "Smuggler", GATE[1] + 1, y2 - 1, COVE + " Stand=1 Face=S Name=Smuggler", -8),
        obj_line("NPC", "Smuggler", 11, 14, COVE + " Stand=1 Face=S Name=Smuggler", -8),                  # by the fire
        obj_line("NPC", "Smuggler", 9, 14, COVE + " Patrol=9,14/16,14 PatrolMode=PingPong Pause=3-6 Name=Smuggler", -8),
        "Id\tSmugglers_Cove\t%d\t%d" % (mx + 1, my),
    ]
    m.save()


def _inside(line):
    p = line.split("\t")
    x1, y1, x2, y2 = CAMP
    tx, ty = int(float(p[2]) // TW) + 1, int(float(p[3]) // TW) + 1
    return x1 - 1 <= tx <= x2 + 1 and y1 - 1 <= ty <= y2 + 1


# ---------------------------------------------------------------- scripts
def scripts():
    V = "Variable.1"
    write("Talk to Smuggler_Sergeant", [
        ("Get.Value", "ATTRIBUTE", "SmugglerQuest", V + "$"),
        (">Conditional", "$Variable.1=0", "@s1"),
        say("Guard", "Sergeant Holt. Smuggled goods turn up in the market every week - brandy, silk, potions no "
            "apothecary made - and not one of my men has seen a cart come in.\\The fishermen by the lake talk of an old "
            "barrel on the path that nobody ever moves. Will you take a look?",
            ("I'll look into it.", "@start"), ("Not now.", "@end")),
        ("@start",), ("Update.Attribute", "SmugglerQuest", "=1"),
        ("Display.Message", "Yellow", "Quest started: The Smugglers' Run. (H: your journal)"),
        ("End",),
        ("@s1",), (">Conditional", "$Variable.1<3", "@s3"),
        say("Guard", "Anything? The barrel's on the lake path, south-west of the castle.", ("Still looking.", "@end")),
        ("End",),
        ("@s3",), (">Conditional", "$Variable.1=3", "@done"),
        say("Guard", "A tunnel, under the shore? And Red Meg says she'll keep her trade off my streets if I keep my men "
            "off her cove... Ha! Fair enough: a quiet market is all I want. Here, you've earned this.",
            ("Thank you, Sergeant.", "@pay")),
        ("@pay",), ("Give.Item", "Gold_Coin(s)", "60"),
        ("Update.Attribute", "SmugglerQuest", "=4"),
        ("Display.Message", "Yellow", "Quest complete: The Smugglers' Run! (60 gold)"),
        ("End",),
        ("@done",), say("Guard", "Quiet market these days. Good work.", ("Goodbye.", "@end")),
        ("@end",), ("End",),
    ])
    bx, by = BARREL
    write("Search Suspicious_Barrel", [
        (">Distance.From.Clicked.Tile", "40", "@far"),
        ("Display.Message", "Cyan", "You lift the lid and rummage under the salted fish..."),
        ("Play.Sound", "Pickup"),
        ("Wait", "1"),
        (">Conditional", "$Attr.SmugglerQuest>=1", "@just_fish"),
        ("Display.Message", "Yellow", "...it's hollow! A hatch in its bottom, and a ladder going down into the dark."),
        (">Conditional", "$Attr.SmugglerQuest=1", "@down"),
        ("Update.Attribute", "SmugglerQuest", "=2"),
        ("@down",), ("Play.Sound", "Ladder"),
        ("Teleport", "%d,%d" % ((bx - 1) * TW, (by + 1) * TW - 8), "3,5,-1"),
        ("End",),
        ("@just_fish",), ("Display.Message", "Cyan", "...nothing but fish. Odd, though: it sounds hollow."),
        ("End",),
        ("@far",), ("Display.Message", "DarkRed", "You are too far away!"),
        ("End",),
    ])
    write("Climb Up Tunnel_Ladder001", [
        ("Play.Sound", "Ladder"),
        ("Display.Message", "Cyan", "You climb up through the barrel, and out by the lake."),
        ("Teleport", "%d,%d" % ((bx - 1) * TW, (by + 1) * TW - 8), "3,5,0"),
        ("End",),
    ])
    hx, hy = HATCH
    write("Climb Up Tunnel_Ladder002", [
        ("Play.Sound", "Ladder"),
        ("Display.Message", "Cyan", "You push up a hatch behind stacked cargo... a palisade, tents, a campfire: a "
         "smugglers' camp! Keep out of their sight."),
        ("Teleport", "%d,%d" % ((hx - 1) * TW, (hy + 1) * TW - 8), "4,5,0"),
        ("End",),
    ])
    write("Talk to Red_Meg", [
        ("Get.Value", "ATTRIBUTE", "SmugglerQuest", V + "$"),
        (">Conditional", "$Variable.1>=3", "@meet"),
        say("Captain", "Need something? I've goods you won't find in any market. And you're welcome on my cove: my lads "
            "know your face.", ("Show me your goods.", "@shop"), ("Goodbye.", "@end")),
        ("@shop",), ("Display.Item.Rack", "GENERAL", "Captain", "SHOP-Smugglers", "@end"),
        ("End",),
        ("@meet",), (">Conditional", "$Variable.1=2", "@stranger"),
        say("Captain", "Well, well. Up through my barrel and past my lads without a peep? I've had sailors who couldn't "
            "cross a deck that quiet.\\I'm Red Meg. Let's not make this ugly: you go back to Holt and tell him this - "
            "we keep our trade off his streets, he keeps his men off my cove. Deal?",
            ("Deal.", "@deal")),
        ("@deal",), ("Update.Attribute", "SmugglerQuest", "=3"),
        ("Display.Message", "Yellow", "The smugglers are your friends now. Tell Sergeant Holt about the deal."),
        ("End",),
        ("@stranger",), say("Captain", "Who let you in? Out, before my lads see you - they're not as friendly as me.",
                            ("I'm going.", "@end")),
        ("@end",), ("End",),
    ])
    print("Scripts: Holt, the barrel, the tunnel's ladders, Red Meg")


def main():
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import story_kit as K
    if K.new_mainland():
        sys.exit("Superseded: build_estforlan.py rebuilt the mainland. This one would put back the old smugglers' cove and tunnels.")
    draw_pictures()
    data()
    tunnels()
    surface()
    scripts()


if __name__ == "__main__":
    main()
