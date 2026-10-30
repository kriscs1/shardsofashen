"""An altar in every church (dev\\Roadmap.md group 10): Altar001, a stone altar under a white cloth, two candles; set
against the back wall of each hall a priest keeps. Pray at it: once a day a blessing (your guard steadier a while),
else a quiet moment.

Safe to run again (an altar already in a hall is kept).

  python -I "dev\\migrate\\build_altars.py"
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import Ini, p                      # noqa: E402
import sprite_kit as K                         # noqa: E402
import story_kit as SK                         # noqa: E402
from build_isle import Map                     # noqa: E402

MAKER = "build_altars.py"
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def altar():
    img = K.new()
    stone, light, dark = (150, 146, 140), (186, 182, 174), (104, 100, 96)
    for y in range(14, 30):                                           # the stone block
        for x in range(5, 27):
            img[y][x] = light if x < 9 else dark if x > 23 or y > 26 else stone
    for y in range(12, 18):                                           # the white cloth, hanging over its front
        for x in range(4, 28):
            img[y][x] = (244, 240, 230) if y < 16 or 12 <= x <= 19 else None
    for x in range(12, 20):                                           # (its gold trim)
        img[18][x] = (214, 170, 60)
    for cx in (8, 23):                                                # two candles, lit
        for y in range(6, 12):
            img[y][cx] = (236, 230, 210)
            img[y][cx + 1] = (210, 204, 186)
        img[4][cx], img[5][cx], img[5][cx + 1] = (255, 220, 120), (255, 170, 60), (255, 200, 90)
    return K.outline_img(img, (40, 34, 30))


def tiles():
    ini = Ini(p("data", "Tiles.ini"))
    for k, v in (("Walkable.Data", "0" * 49), ("Show.Name", "1"), ("Use.Words", "Pray,Examine"), ("Layer", "Decor"),
                 ("Examine.Info", "An altar of plain stone under a white cloth, its candles burning low.")):
        ini.set("Altar001", k, v, overwrite=False)
    ini.save(p("data", "Tiles.ini"))
    colours = p("dev", "Minimap Colours.txt")                  # (the minimap's colour for it)
    if "\nAltar001\t" not in "\n" + open(colours, encoding="cp1252").read():
        with open(colours, "a", encoding="cp1252", newline="\r\n") as f:
            f.write("Altar001\t214 208 196\n")


def script():
    SK.write_script("Pray Altar001", [
        (">Distance.From.Clicked.Tile", "56", "@far"),
        ("Get.Value", "ATTRIBUTE", "PrayedAt", "Variable.1$"),
        ("Get.Value", "CALCULATION", "$Clock-$Variable.1", "Variable.2$"),
        (">Conditional", "$Variable.2>=72000", "@quiet"),            # (a blessing once a day)
        ("Update.Attribute", "PrayedAt", "=$Clock"),
        ("Play.Sound", "Bell"),
        ("Boost.Skill", "Defence", "2", "300"),
        ("Display.Message", "Yellow", "You kneel a while. When you rise, you feel steadier, guarded.", "-"),
        ("End",),
        ("@quiet",),
        ("Display.Message", "Cyan", "You kneel and pray a while, and the hall is very still.", "-"),
        ("End",),
        ("@far",), ("Display.Message", "DarkRed", "You are too far away!", "Denied"), ("End",)], MAKER)


def place():
    """Each priest's hall: the altar at the middle of its back wall's row (the row under it), on bare floor."""
    n = 0
    for f in sorted(os.listdir(os.path.join(ROOT, "maps"))):
        if not f.endswith(".txt"):
            continue
        text = open(os.path.join(ROOT, "maps", f), "rb").read().decode("cp1252")
        if "\tPriest\t" not in text and "Priest_" not in text:
            continue
        m = Map(f[:-4])
        if any("Altar001" in c for row in m.rows for c in row):
            continue
        for ln in m.ents:
            q = ln.split("\t")
            if q[0] != "NPC" or "Priest" not in q[1] + ln:
                continue
            x, y = int(float(q[2]) // 32) + 1, int((float(q[3]) + 28) // 32) + 1
            grp = None
            for r in range(0, 4):
                for dy in range(-r, r + 1):
                    for dx in range(-r, r + 1):
                        if 1 <= x + dx <= 25 and 1 <= y + dy <= 21:
                            g = re.search(r"Roof\([^)]*\.(\d+)\)", m.rows[y + dy - 1][x + dx - 1])
                            grp = grp or (g.group(1) if g else None)
                if grp:
                    break
            if not grp:
                continue
            cells = [(cx, cy) for cy in range(1, 22) for cx in range(1, 26)
                     if re.search(r"Roof\([^)]*\.%s\)" % grp, m.rows[cy - 1][cx - 1])]
            top = min(c[1] for c in cells) + 1
            mid = (min(c[0] for c in cells) + max(c[0] for c in cells)) // 2
            for dx in (0, -1, 1, -2, 2):
                cx = mid + dx
                if (cx, top) in cells:
                    t, over = m.parts(cx, top)
                    if "Thin" not in t and not over.get("Decor"):
                        m.set(cx, top, decor="Altar001")
                        m.save()
                        n += 1
                        break
            break
    print("Altars: %d set down" % n)


def main():
    K.save("Tiles", "Altar001", altar())
    tiles()
    script()
    place()


if __name__ == "__main__":
    main()
