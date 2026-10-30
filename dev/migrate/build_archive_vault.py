"""The Royal Guard's stealthy step (dev\\Roadmap.md group 8): the Archivist won't vouch for the amulet on its own. The
Queen's own papers lie sealed in the Archive vault under Galaith's City Hall (by the old Chancellor's order, the night
she fled); bring them, and she'll put her seal to it.

  * A hatch at the back of the hall (place Id Archive_Hatch): shut till the Archivist sends you down
    (ArchiveVault>=1). Under it the vault (the City Hall's map, level -1): a ladder up, a passage and the vault room, its
    shelves of charters; two watchmen of the Royal Guard keeping it (lookouts: they see a cone ahead of them, hear you
    coming, and fight anyone they catch), a chest with a lock (Stealth 5 to pick; Break Open is loud).
  * In the chest, Mary's Notes (Marys_Notes, Read): what she found out at the Wizards' Court, the Pact's price, the
    Heart of Ashen. GuardQuest's stages don't change: ArchiveVault is the step inside stage 2 (1: sent down, 2: found).
  * The Archivist's script (build_heir_mainland.py writes it: the same rows are there) asks for the notes first.

Safe to run again (it finds the hall by its Archivist, wherever Galaith's had her set down).

  python -I "dev\\migrate\\build_archive_vault.py"
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import story_kit as SK                                  # noqa: E402
from story_kit import Map, obj_line, say               # noqa: E402
from common import Ini, p                              # noqa: E402

MAKER = "build_archive_vault.py"
ROOT = os.path.dirname(os.path.dirname(HERE))
ARCHIVIST = "Galaith_Clerk_73"
NOTES = ("Mary's Notes\\Folded small, in your mother's hand:\\They told me at the Court that the Shards are only "
         "magic, splintered. They are not. They are the Heart of Ashen, the first king's crystal, broken on the mountain "
         "to bind the dragon. Every splinter wants to be whole. The dragon carries the largest; and the Pact keeps the "
         "rest apart with the blood of every firstborn heir.\\I will not pay it with my child. If the pieces could be "
         "kept apart some other way, or made whole and held, the price would end. I go to find out how.\\The place it "
         "broke is under the mountain behind the city. Remember the Seam.")


def find_hall():
    """(map, x, y of the Archivist, the hall's roof cells) on whichever map she stands."""
    for f in os.listdir(os.path.join(ROOT, "maps")):
        if not f.endswith(",0.txt"):
            continue
        text = open(os.path.join(ROOT, "maps", f), "rb").read().decode("cp1252")
        if "Id=%s" % ARCHIVIST not in text:
            continue
        m = Map(f[:-4])
        ln = next(ln for ln in m.ents if "Id=%s" % ARCHIVIST in ln)
        x, y = int(float(ln.split("\t")[2]) // 32) + 1, int((float(ln.split("\t")[3]) + 28) // 32) + 1
        grp = re.search(r"Roof\([^)]*\.(\d+)\)", m.rows[y - 1][x - 1])
        if not grp:
            for dy in range(-3, 4):
                for dx in range(-3, 4):
                    c = m.rows[min(20, max(0, y - 1 + dy))][min(24, max(0, x - 1 + dx))]
                    grp = grp or re.search(r"Roof\([^)]*\.(\d+)\)", c)
        cells = [(cx, cy) for cy in range(1, 22) for cx in range(1, 26)
                 if grp and re.search(r"Roof\([^)]*\.%s\)" % grp.group(1), m.rows[cy - 1][cx - 1])]
        return m, x, y, cells
    raise SystemExit("The Archivist isn't on any map.")


def hatch_spot(m, cells):
    """A floor cell at the back of the hall, nothing on it (the row under its back wall)."""
    top = min(y for _, y in cells)
    for row in (top + 1, top + 2):
        for x, y in sorted(cells, key=lambda c: c[0]):
            if y == row:
                t, over = m.parts(x, y)
                if "Thin" not in t and not over.get("Decor") and not over.get("Under"):
                    return x, y
    raise SystemExit("No floor for the hatch.")


def vault(name, hx, hy):
    """The vault under the hall: the ladder at hx, hy, a passage east or west, the vault room, shelves, the chest,
    two watchmen."""
    v = Map(name, new=True)
    room_x = hx + 6 if hx < 13 else hx - 14                      # (the room off to one side)
    room_x = max(2, min(15, room_x))
    floor = lambda x, y: v.set(x, y, tile="Flagstone001", decor="")   # noqa: E731
    for y in range(1, 22):
        for x in range(1, 26):
            v.set(x, y, tile="Cave_Wall001", decor="")
    for y in range(hy - 1, hy + 2):                              # (round the ladder)
        for x in range(hx - 1, hx + 2):
            floor(x, y)
    a, b = sorted((hx, room_x + 4))
    for x in range(a, b + 1):                                     # the passage
        floor(x, hy + 1)
    ry = max(2, min(13, hy - 3))
    for y in range(ry, ry + 7):                                   # the vault room
        for x in range(room_x, room_x + 9):
            floor(x, y)
    for x in range(room_x, room_x + 9, 2):                        # shelves of charters along its back wall
        v.set(x, ry, decor="Bookshelf001")
    for y in range(min(hy + 1, ry), max(hy + 1, ry + 6) + 1):     # (the passage into the room)
        floor(room_x + 4, y)
    v.set(hx, hy, decor="Ladder001")
    cx = room_x + 7
    v.ents.append(obj_line("StaticObject", "Chest", cx, ry + 1, "Id=Archive_Vault_Chest Lock=5", -8))
    w1 = obj_line("NPC", "Royal_Guard", room_x + 4, ry + 5, "Attitude=Bad Stand=1 Face=W Cone=100 Group=Archive_Watch "
                  "Id=Archive_Watchman_1 Name=Watchman", -8)
    w2 = obj_line("NPC", "Royal_Guard", (hx + room_x + 4) // 2, hy + 1, "Attitude=Bad Patrol=%d,%d/%d,%d PatrolMode=PingPong "
                  "Cone=100 Group=Archive_Watch Id=Archive_Watchman_2 Name=Watchman" %
                  (min(hx, room_x + 4) + 1, hy + 1, max(hx, room_x + 4) - 1, hy + 1), -8)
    v.ents += [w1, w2]
    v.save()


def scripts(hall, hx, hy, vault_name):
    w = lambda n, rows: SK.write_script(n, rows, MAKER)       # noqa: E731
    w("Climb Down Archive_Hatch", [
        (">Distance.From.Clicked.Tile", "48", "@far"),
        (">Conditional", "$Attr.ArchiveVault>=1", "@shut"),
        ("Play.Sound", "Ladder"),
        ("Display.Message", "Cyan", "You lift the hatch and climb down into the dark. Somewhere below, boots.", "-"),
        ("Teleport", "%d,%d" % ((hx - 1) * 32, (hy - 1) * 32 - 8), vault_name),
        ("End",),
        ("@shut",), ("Display.Message", "DarkRed", "The hatch is locked.", "Locked"), ("End",),
        ("@far",), ("Display.Message", "DarkRed", "You are too far away!", "Denied"), ("End",)])
    w("Open Archive_Vault_Chest", [
        (">Distance.From.Clicked.Entity", "48", "@far"),
        ("Get.Value", "ATTRIBUTE", "ArchiveVault", "Variable.1$"),
        (">Conditional", "$Variable.1<2", "@empty"),
        ("Update.Attribute", "ArchiveVault", "=2"),
        ("Give.Item", "Marys_Notes", "1"),
        ("Give.Item", "Gold_Coin(s)", "12"),
        ("End",),
        ("@empty",), ("Display.Refusal", "The chest is empty."), ("End",),
        ("@far",), ("Display.Message", "DarkRed", "You are too far away!", "Denied"), ("End",)])
    w("Read Marys_Notes", [say("Notice", NOTES, ("Fold them away.", "@end")), ("@end",), ("End",)])


def data():
    ents = Ini(p("data", "Entities.ini"))
    for k, v in (("Type", "MapItem"), ("Display.Name", "Mary's Notes"), ("Use.Words", "Read,Examine"),
                 ("Droppable", "0"), ("Value", "0"), ("Stackable", "1"),
                 ("Examine.Info", "Your mother's notes, folded small, from the Archive vault.")):
        ents.set("Marys_Notes", k, v)
    ents.save(p("data", "Entities.ini"))
    import build_heir_mainland as HM
    SK.save("Entities", "Marys_Notes", HM.scroll_letter((120, 80, 160)))


def main():
    hall, ax, ay, cells = find_hall()
    hx, hy = hatch_spot(hall, cells)
    if not any(ln.startswith("Id\tArchive_Hatch\t") for ln in hall.ents):
        hall.set(hx, hy, decor="Hatch001")
        SK.place_id(hall, "Archive_Hatch", hx, hy)
        hall.save()
    else:
        ln = next(ln for ln in hall.ents if ln.startswith("Id\tArchive_Hatch\t"))
        hx, hy = int(ln.split("\t")[2]), int(ln.split("\t")[3])
    mx, my = (int(v) for v in hall.name.split(",")[:2])
    vault_name = "%d,%d,-1" % (mx, my)
    if not os.path.exists(os.path.join(ROOT, "maps", vault_name + ".txt")):
        vault(vault_name, hx, hy)
    scripts(hall, hx, hy, vault_name)
    data()
    import build_heir_mainland as HM                   # (the Archivist's own script, with the vault in it)
    HM.archivist_script()
    print("The Archive vault: under %s, its hatch at %d,%d" % (hall.name, hx, hy))


if __name__ == "__main__":
    main()
