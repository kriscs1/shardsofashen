"""The Isle's chapel as a chapel, gates, a square way down. Run it after build_isle_art.py (the pictures); once is
enough (again: it sees what's done).

  python -I "Dev\\migrate\\build_isle_chapel.py"

  * The chapel (3,1,0): pale dressed stone (Chapel_Stone001), a storey above the door with stained glass, a bell
    tower over the door with a slate spire and a gilt cross, a slate roof; stone walls and flagstones inside, and
    its verger, Brother Aldous (a Gravekeeper, Id=Chapel_Verger), who'll lend you the cellar key if you ask.
  * The cellar's way down (3,1,-1) is a trapdoor, locked (a Lock line): with the key it opens (Trapdoor002) and you
    climb down; without it, it says so (with the Denied sound).
  * Gates (Wood_Gate001-004: doors, in the picket fence): one in the cow pasture's fence; homesteads can build them.
  * The hen coop's door stands open for good; the beggar's house has a square hatch down (Hatch001) instead of the
    old ladder.
  * The tiles' entries (Tiles.ini), the editor's sets (TileSets.ini) and the minimap's colours for all of them.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from dragonsword import ini  # noqa: E402
from dsengine.homes import roof_piece  # noqa: E402
from build_isle import Map, TW, DATA, TILES_INI, obj_line  # noqa: E402

CHAPEL = (13, 7, 19, 12)                       # its walls on 3,1,0; the door at 16,12
TOWER_X = 16
TRAPDOOR = (14, 9)                             # in the cellar, 3,1,-1
WALK_ALL, WALK_NONE = "1" * 49, "0" * 49
KEY_CONDITION = "$Item.Chapel_Cellar_Key>=1 or $Attr.ChapelCellarOpen>=1"


def tile_entry(name, **keys):
    if ini.section(name, TILES_INI):
        return
    for k, v in keys.items():
        ini.write(name, k.replace("_", "."), v, TILES_INI)


def register_tiles():
    for n, (shut, open_) in enumerate((("Wood_Gate001", "Wood_Gate002"), ("Wood_Gate003", "Wood_Gate004"))):
        way = ("east-west", "north-south")[n]
        tile_entry(shut, Walkable_Data=WALK_ALL, Show_Name="1", Use_Words="", Examine_Info="A gate in the picket fence.",
                   Line_of_Sight="1", Open_Tile=open_, Door="1", Piece="a gate, shut (%s)" % way)
        tile_entry(open_, Walkable_Data=WALK_ALL, Show_Name="1", Use_Words="", Examine_Info="An open gate.",
                   Line_of_Sight="1", Door="1", Piece="a gate, open (%s)" % way)
    tile_entry("Chapel_Stone001", Walkable_Data=WALK_NONE, Show_Name="1", Use_Words="",
               Examine_Info="Pale dressed stone, laid true.", Line_of_Sight="0")
    for n in ("Chapel_Stone_Upper001", "Chapel_Stone_Upper002", "Steeple001", "Steeple002"):
        tile_entry(n, Walkable_Data=WALK_NONE, Show_Name="0", Use_Words="", Examine_Info="", Line_of_Sight="1")
    tile_entry("Stained_Glass001", Walkable_Data=WALK_ALL, Show_Name="1", Use_Words="",
               Examine_Info="Stained glass: saints and stars in red, blue and gold.", Line_of_Sight="1", Light="34",
               Layer="Decor", Piece="a window")
    ladder = ini.read("Ladder002", "Walkable.Data", WALK_ALL, TILES_INI)
    tile_entry("Hatch001", Walkable_Data=ladder, Show_Name="1", Use_Words="Climb Down",
               Examine_Info="A square hatch in the floor, a ladder going down.", Layer="Decor", Piece="a hatch, a ladder down")
    tile_entry("Trapdoor001", Walkable_Data=WALK_ALL, Show_Name="1", Use_Words="Climb Down",
               Examine_Info="A stout trapdoor, banded with iron. Locked.", Line_of_Sight="1", Unlocked_Tile="Trapdoor002")
    tile_entry("Trapdoor002", Walkable_Data=ladder, Show_Name="1", Use_Words="Climb Down",
               Examine_Info="The trapdoor stands open: a ladder goes down into the dark.", Line_of_Sight="1")
    for n, way in (("Bench002", "east"), ("Bench003", "west")):
        tile_entry(n, Walkable_Data="1100011" * 7, Show_Name="1", Use_Words="",
                   Examine_Info="A wooden bench, facing %s." % way, Line_of_Sight="1", Layer="Decor")
    sets = os.path.join(DATA, "TileSets.ini")
    for sec, title, cols, tiles in (
            ("Wood_Gate", "wood fence gates (shut, open)", 2, "Wood_Gate001,Wood_Gate002,Wood_Gate003,Wood_Gate004"),
            ("Chapel", "chapel stone: wall, upper storey, stained glass, bell tower", 3,
             "Chapel_Stone001,Chapel_Stone_Upper001,Chapel_Stone_Upper002,Stained_Glass001,Steeple001,Steeple002"),
            ("Bench", "benches: facing you, facing east, facing west", 3, "Bench001,Bench002,Bench003"),
            ("Hatch", "ways down with a square base: a hatch, a trapdoor (shut, open)", 3,
             "Hatch001,Trapdoor001,Trapdoor002")):
        if not ini.section(sec, sets):
            ini.write(sec, "Title", title, sets)
            ini.write(sec, "Columns", str(cols), sets)
            ini.write(sec, "Tiles", tiles, sets)
    colours = os.path.join(ROOT, "Dev", "Minimap Colours.txt")
    have = ini.read_text(colours)
    add = [("Wood_Gate00%d" % i, "150 110 60") for i in range(1, 5)] + \
          [("Chapel_Stone001", "204 198 186"), ("Chapel_Stone_Upper001", "204 198 186"),
           ("Chapel_Stone_Upper002", "204 198 186"), ("Stained_Glass001", "120 80 160"), ("Steeple001", "204 198 186"),
           ("Steeple002", "204 198 186"), ("Hatch001", "255 0 0"), ("Trapdoor001", "255 0 0"),
           ("Trapdoor002", "255 0 0"), ("Bench002", "150 90 30"), ("Bench003", "150 90 30")] + [("Steeple_Spire00%d" % i, "84 92 106") for i in (1, 2, 3)]
    with open(colours, "a", encoding="cp1252", newline="\r\n") as f:
        for name, col in add:
            if "\n" + name + "\t" not in "\n" + have:
                f.write("%s\t%s\n" % (name, col))
    builds = os.path.join(DATA, "Buildables.ini")
    for bid, name in (("Bench002", "Bench (facing east)"), ("Bench003", "Bench (facing west)")):
        if not ini.section(bid, builds):
            for k, v in (("Kind", "Decor"), ("Category", "Furniture"), ("Name", name), ("Needs", "Plank 2 Nails 2"),
                         ("Level", ini.read("Bench001", "Level", "2", builds)), ("XP", "0.06")):
                ini.write(bid, k, v, builds)
    for gid, name in (("Wood_Gate001", "Gate (east-west)"), ("Wood_Gate003", "Gate (north-south)")):
        if not ini.section(gid, builds):
            for k, v in (("Kind", "Tile"), ("Category", "Walls"), ("Name", name), ("Needs", "Plank 2 Nails 4"),
                         ("Level", "3"), ("XP", "0.08")):
                ini.write(gid, k, v, builds)
    ents = os.path.join(DATA, "Entities.ini")
    if not ini.section("Chapel_Cellar_Key", ents):
        for k, v in (("Type", "MapItem"), ("Droppable", "0"), ("Value", "0"),
                     ("Examine.Info", "The chapel's cellar key: it opens the trapdoor down to the caves.")):
            ini.write("Chapel_Cellar_Key", k, v, ents)
        import shutil
        shutil.copy(os.path.join(ROOT, "Sprites", "Entities", "Beggars_House_Key.png"),
                    os.path.join(ROOT, "Sprites", "Entities", "Chapel_Cellar_Key.png"))
    print("Tiles, sets, colours, gates to build, the cellar key")


def spires(m, g):
    """The spire over the roof: pictures made from the roof pieces under it (Steeple_Spire001-003, top down)."""
    import pygame
    import build_isle_art as art
    pygame.init()
    pygame.display.set_mode((1, 1))
    x1, y1, x2, _ = CHAPEL
    for k, y in enumerate((y1, y1 + 1, y1 + 2)):           # (top: the tip and the cross; then its middle; its foot)
        base_name = roof_piece("Slate", TOWER_X, y, x1, y1, x2, y1 + 3)
        base = pygame.image.load(os.path.join(ROOT, "Sprites", "Tiles", base_name + ".png")).convert_alpha()
        name = "Steeple_Spire%03d" % (k + 1)
        pygame.image.save(art.spire(base, 2 - k), os.path.join(ROOT, "Sprites", "Tiles", name + ".png"))
        tile_entry(name, Walkable_Data=WALK_NONE, Show_Name="0", Use_Words="", Examine_Info="", Line_of_Sight="1")
        m.set(TOWER_X, y, roof="%s.%02d" % (name, g))


def chapel():
    m = Map("3,1,0")
    x1, y1, x2, y2 = CHAPEL
    if m.tile(x1, y2) == "Chapel_Stone001":
        print("The chapel is stone already")
        return
    g = int(m.parts(x1, y1)[1]["Roof"].split(".")[1])
    for y in range(y1, y2 + 1):
        for x in range(x1, x2 + 1):
            t, over = m.parts(x, y)
            if t == "Timber001":
                t = "Chapel_Stone001"
            elif t.startswith("Timber_Thin_Plank"):
                t = "Stone_Wall_Thin_Tile" + t[-3:]
            elif t == "Plank001":
                t = "Tile001"
            if over.get("Decor") == "Timber_Window001":
                over["Decor"] = "Stained_Glass001"
            elif over.get("Decor", "").startswith(("Flowers", "Pebbles", "Tall_Grass")):
                over["Decor"] = ""                       # (the meadow's flowers don't grow in the walls)
            m.put(x, y, t, over)
    for y in range(y1, y2 - 1):                              # a slate roof
        for x in range(x1, x2 + 1):
            m.set(x, y, roof="%s.%02d" % (roof_piece("Slate", x, y, x1, y1, x2, y2 - 2), g))
    for x in range(x1, x2 + 1):                              # the storey over the door, glass either side
        piece = "Chapel_Stone_Upper002" if x in (x1 + 1, x2 - 1) else "Chapel_Stone_Upper001"
        m.set(x, y2 - 1, roof="%s.%02d" % (piece, g))
    m.set(TOWER_X, y2 - 1, roof="Steeple001.%02d" % g)       # the tower: its face, its belfry, its spire
    m.set(TOWER_X, y2 - 2, roof="Steeple002.%02d" % g)
    spires(m, g)
    if not m.has_line("Id=Chapel_Verger"):
        m.ents.append(obj_line("NPC", "Gravekeeper", 14, 9, "Attitude=Good Stand=1 Id=Chapel_Verger Name=Brother_Aldous", -8))
    m.save()
    print("The chapel: stone, stained glass, a bell tower and spire, a slate roof; Brother Aldous inside")


def cellar_trapdoor():
    c = Map("3,1,-1")
    x, y = TRAPDOOR
    if c.tile(x, y) == "Trapdoor001":
        return
    c.set(x, y, tile="Trapdoor001", decor="")
    c.ents = [ln for ln in c.ents if not ln.startswith("Lock\t%d\t%d\t" % (x, y))]
    c.ents.append("Lock\t%d\t%d\t%s\tThe trapdoor is locked. Brother Aldous, in the chapel above, keeps the key."
                  % (x, y, KEY_CONDITION))
    c.save()
    hx, hy = TRAPDOOR

    def script(name, lines):
        with open(os.path.join(DATA, "Scripts", name + ".txt"), "w", encoding="cp1252", newline="\r\n") as f:
            f.write("// Generated by Dev\\migrate\\build_isle_chapel.py\n" + "\n".join(lines) + "\n")
    script("Climb Down Trapdoor", [
        "01\tGet.Value\tATTRIBUTE\tChapelCellarOpen\tVariable.1$",
        "02\t>Conditional\t$Variable.1>=1\t04",
        "03\tGoto.Line\t08",
        "04\t>Got.Item\tChapel_Cellar_Key\t1\t12",
        "05\tUpdate.Attribute\tChapelCellarOpen\t=1",
        "06\tDisplay.Message\tCyan\tYou unlock the trapdoor with the cellar key and heave it open.",
        "07\tPlay.Sound\tDoor",
        "08\tPlay.Sound\tLadder",
        "09\tDisplay.Message\tCyan\tYou climb down the ladder, into the caves under the Isle.",
        "10\tTeleport\t%d,%d\t3,1,-2" % ((hx - 1) * TW, hy * TW - 8),
        "11\tEnd",
        "12\tDisplay.Refusal\tThe trapdoor is locked.",
        "13\tEnd"])
    script("Climb Down Hatch", [
        "// The same X,Y one level down (as Climb Down Ladder002)",
        "01\tGet.Value\tCALCULATION\t$Map.Z-1\tVariable.9$",
        "02\tGet.Value\tCALCULATION\t$Map.Name\tVariable.8$",
        "03\tTeleport\t$Player.X,$Player.Y\t$Map.X,$Map.Y,$Variable.9",
        "04\t>Conditional\t$Map.Name<>$Variable.8\t07",
        "05\tPlay.Sound\tLadder",
        "06\tDisplay.Message\tCyan\tYou climb down the ladder.",
        "07\tEnd"])
    script("Talk to Chapel_Verger", [
        "01\t>Got.Item\tChapel_Cellar_Key\t1\t04",
        "02\tDisplay.Conversation\tGravekeeper\tYou have the cellar key already. Mind the trapdoor down there: the "
        "ladder goes a long way.\tThank you.\t03",
        "03\tEnd",
        "04\tDisplay.Conversation\tGravekeeper\tPeace be with you. I'm Brother Aldous: I keep the chapel, and the "
        "graves out there.\\The cellar? Barrels, old candles... and a trapdoor down to the caves. Rats and bats, "
        "mostly. I keep it locked.\tCould I have the cellar key?\t05\tGoodbye.\t03",
        "05\tGive.Item\tChapel_Cellar_Key\t1",
        "06\tDisplay.Conversation\tGravekeeper\tHere. The steps are behind the altar; the trapdoor's in the cellar "
        "floor. Bring a lantern, and a sword.\tThank you.\t03"])
    p = os.path.join(DATA, "Scripts", "Read Isle_Chapel.txt")
    text = open(p, "rb").read().decode("cp1252")
    text = re.sub(r"(THE ISLE CHAPEL\\\\Rest in peace, all who sleep in the yard\.)[^\t]*", r"\1", text)   # (no hints)
    open(p, "wb").write(text.encode("cp1252"))
    print("The cellar: a locked trapdoor (Brother Aldous has the key)")


def gates_and_doors():
    d = Map("2,0,0")
    if d.tile(8, 11) != "Wood_Gate003":
        d.set(8, 11, tile="Wood_Gate003", decor="")          # the cow pasture's gate (its fence runs north-south)
    if d.tile(22, 14).startswith("Door001"):
        d.set(22, 14, tile="Door_Open001")                   # the hen coop: an open doorway, always
    d.save()
    v = Map("1,1,0")
    for y in range(1, 22):
        for x in range(1, 26):
            if v.decor(x, y) == "Ladder002":                 # the beggar's house: a square hatch down
                v.set(x, y, decor="Hatch001")
    v.save()
    print("The pasture's gate, the coop's open door, the beggar's hatch")


def chapel_bench():
    """A bench by the chapel's west wall, facing it."""
    m = Map("3,1,0")
    if any(m.decor(x, y) == "Bench002" for y in range(1, 22) for x in range(1, 26)):
        return
    for x, y in ((11, 9), (11, 10), (11, 11), (11, 8)):
        if m.open_ground(x, y) and not m.ent_near(x, y):
            m.set(x, y, decor="Bench002")
            m.save()
            print("A bench by the chapel, at 3,1,0 %d,%d" % (x, y))
            return


KEY_CRATE = (17, 12)                           # (the cellar crate the lost key is in, 3,1,-1)


def write_script(name, lines):
    with open(os.path.join(DATA, "Scripts", name + ".txt"), "w", encoding="cp1252", newline="\r\n") as f:
        f.write("// Generated by Dev\\migrate\\build_isle_chapel.py\n" + "\n".join(lines) + "\n")


def lost_key():
    """Brother Aldous has lost the cellar key (ask him about the cellar and he'll say so): it's in a crate down there,
    among the barrels and crates you can search. With it, the trapdoor stands open for you and down you go."""
    import shutil
    tiles = os.path.join(ROOT, "Sprites", "Tiles")
    for new, old, info in (("Cellar_Barrel001", "Barrel001", "An old barrel, its lid loose."),
                           ("Cellar_Crate001", "Crate001", "A dusty crate, its lid nailed down badly.")):
        if not os.path.exists(os.path.join(tiles, new + ".png")):
            shutil.copy(os.path.join(tiles, old + ".png"), os.path.join(tiles, new + ".png"))
        if not ini.section(new, TILES_INI):
            for k, v in ini.section(old, TILES_INI):
                ini.write(new, k, v, TILES_INI)
            ini.write(new, "Use.Words", "Search,Examine", TILES_INI)
            ini.write(new, "Examine.Info", info, TILES_INI)
        colours = os.path.join(ROOT, "Dev", "Minimap Colours.txt")
        text = ini.read_text(colours)
        if "\n" + new + "\t" not in "\n" + text:
            col = next((ln.split("\t", 1)[1] for ln in text.splitlines() if ln.startswith(old + "\t")), "120 80 40")
            with open(colours, "a", encoding="cp1252", newline="\r\n") as f:
                f.write("%s\t%s\n" % (new, col.strip()))
    c = Map("3,1,-1")
    for y in range(1, 22):
        for x in range(1, 26):
            d = c.decor(x, y)
            if d in ("Barrel001", "Crate001"):
                c.set(x, y, decor="Cellar_" + d)
    c.save()
    kx, ky = KEY_CRATE
    nothing = {"Cellar_Barrel": "Only old candle ends and dust.", "Cellar_Crate": "Mouldy hymn books. No key."}
    for kind in ("Cellar_Barrel", "Cellar_Crate"):
        write_script("Search " + kind, [
            "01	>Distance.From.Clicked.Tile	40	14",
            "02	Get.Value	CALCULATION	$Tile.under.Cursor.X	Variable.5$",
            "03	Get.Value	CALCULATION	$Tile.under.Cursor.Y	Variable.6$",
            "04	Display.Message	Cyan	You rummage through the %s..." % kind.split("_")[1].lower(),
            "05	Play.Sound	Pickup",
            "06	Wait	1",
            "07	>Conditional	$Variable.5=%d	12" % kx,
            "08	>Conditional	$Variable.6=%d	12" % ky,
            "09	>Got.Item	Chapel_Cellar_Key	1	11",
            "10	Goto.Line	12",
            "11	Goto.Line	16",
            "12	Display.Message	Cyan	" + nothing[kind],
            "13	End",
            "14	Display.Message	DarkRed	You are too far away!",
            "15	End",
            "16	Give.Item	Chapel_Cellar_Key	1",
            "17	Display.Message	Yellow	...and there, under the straw: an iron key. The cellar key!",
            "18	End"])
    write_script("Talk to Chapel_Verger", [
        "01	Display.Conversation	Gravekeeper	Peace be with you. I'm Brother Aldous: I keep the chapel, and the "
        "graves out there.	What's down in the cellar?	02	Goodbye.	05",
        "02	>Got.Item	Chapel_Cellar_Key	1	04",
        "03	Display.Conversation	Gravekeeper	You found my key! Bless you. Keep it: the trapdoor will open for you. "
        "Rats and bats down there, mind.	I will.	05",
        "04	Display.Conversation	Gravekeeper	Barrels, old candles... and a trapdoor, down to the caves under the "
        "Isle. Locked, and I've lost the key.\I had it last down there, sorting through the barrels and crates. If "
        "you find it, it's yours to keep.	I'll look for it.	05	Goodbye.	05",
        "05	End"])
    write_script("Climb Down Trapdoor", [
        "01	>Got.Item	Chapel_Cellar_Key	1	06",
        "02	Play.Sound	Ladder",
        "03	Display.Message	Cyan	You climb down the ladder, into the caves under the Isle.",
        "04	Teleport	%d,%d	3,1,-2" % ((TRAPDOOR[0] - 1) * TW, TRAPDOOR[1] * TW - 8),
        "05	End",
        "06	Display.Refusal	The trapdoor is locked. Brother Aldous, in the chapel above, might know where the key is.",
        "07	End"])
    c = Map("3,1,-1")                            # (the lock: the key, nothing else, opens it)
    c.ents = [("Lock\t%d\t%d\t$Item.Chapel_Cellar_Key>=1\tThe trapdoor is locked." % TRAPDOOR)
              if ln.startswith("Lock\t%d\t%d\t" % TRAPDOOR) else ln for ln in c.ents]
    c.save()
    print("The cellar key: lost, in a crate in the cellar; the trapdoor opens for whoever has it")


def chapel_touches():
    """A runner down the chapel's aisle; the bench by its east wall turned to look out to sea."""
    m = Map("3,1,0")
    for y, rug in ((9, "Rug014"), (10, "Rug015"), (11, "Rug016")):
        if not m.decor(16, y):
            m.set(16, y, decor=rug)
    for y in range(1, 22):
        for x in range(20, 26):
            if m.decor(x, y) == "Bench001":
                m.set(x, y, decor="Bench002")
    m.save()
    print("The chapel: a rug down the aisle; the sea bench turned to the sea")


def main():
    register_tiles()
    chapel()
    cellar_trapdoor()
    gates_and_doors()
    chapel_bench()
    lost_key()
    chapel_touches()


if __name__ == "__main__":
    main()
