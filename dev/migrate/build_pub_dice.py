"""Dice in every pub (the owner's wish): every barkeep plays Three Cups and High or Low (Play, tavern.py), and every pub has a
Dice_Table for Dragon Dice, on a clear floor cell near the bar: never by a door or a stair, and with room to walk round it.
Safe to run again: a pub with a table is left alone.

  python -I "dev\\migrate\\build_pub_dice.py"
"""
import glob
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from common import Ini, p                        # noqa: E402

XT, YT, TW = 25, 21, 32
ROOF = re.compile(r"Roof\(([^.)]+)\.([^)]+)\)")
PLAIN = ("Plank001", "Tile001", "Marble001", "Flagstone001")


def main():
    placed, kept, none = 0, 0, []
    for path in glob.glob(p("maps", "*,0.map")):
        name = os.path.basename(path)[:-4]
        lines = open(path, "rb").read().decode("cp1252").split("\r\n")
        ents = [ln for ln in lines if "\t" in ln]
        bars = [ln.split("\t") for ln in ents if ln.startswith("NPC\tBarkeep\t")]
        if not bars:
            continue
        rows = [ln.split(":") for ln in lines[:YT]]
        taken = set()
        tables = set()
        for ln in ents:
            f = ln.split("\t")
            if f[0] in ("NPC", "StaticObject", "MapItem") and len(f) >= 4:
                try:
                    cell = (int(f[2]) // TW, (int(f[3]) + 8) // TW)
                except ValueError:
                    continue
                taken.add(cell)
                if f[1] == "Dice_Table":
                    tables.add(cell)
            elif f[0] in ("Trigger", "Id", "Lock") and len(f) >= 4 and f[2].isdigit() and f[3].isdigit():
                taken.add((int(f[2]) - 1, int(f[3]) - 1))

        def group_at(x, y):
            m = ROOF.search(rows[y][x]) if 0 <= y < YT and 0 <= x < XT else None
            return m[2] if m else None

        def clear(x, y):
            if not (0 <= x < XT and 0 <= y < YT) or (x, y) in taken:
                return False
            c = rows[y][x]
            return c.split("+")[0] in PLAIN and "Decor(" not in c and "Infront(" not in c

        added = False
        seen = set()
        for bar in bars:
            bx, by = int(bar[2]) // TW, (int(bar[3]) + 8) // TW
            g = next((group_at(x, y) for r in range(3) for x in range(bx - r, bx + r + 1)
                      for y in range(by - r, by + r + 1) if group_at(x, y)), None)
            if g is None or g in seen:
                continue
            seen.add(g)
            if any(group_at(x, y) == g for x, y in tables):
                kept += 1
                continue
            best = None
            for y in range(YT):
                for x in range(XT):
                    if group_at(x, y) != g or not clear(x, y):
                        continue
                    round_it = [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
                    if sum(clear(*c) for c in round_it) < 2 or abs(x - bx) + abs(y - by) < 2:
                        continue
                    if (x, y - 1) == (bx, by) or (x, y + 1) == (bx, by):        # (not in front of the bar)
                        continue
                    if any("Door" in rows[cy][cx].split("+")[0] for cx, cy in
                           ((x, y + 1), (x, y + 2)) if 0 <= cy < YT):
                        continue
                    if any(group_at(cx, cy) == g and re.search(r"Stairs|Ladder|Hatch|Trapdoor", rows[cy][cx]) for cx, cy in round_it
                           if 0 <= cx < XT and 0 <= cy < YT):
                        continue
                    score = abs(abs(x - bx) + abs(y - by) - 4)                  # (a few steps from the bar)
                    if best is None or score < best[0]:
                        best = (score, x, y)
            if best is None:
                none.append("%s %s" % (name, bar[-1][-24:]))
                continue
            _, x, y = best
            taken.add((x, y))
            tables.add((x, y))
            lines.insert(YT, "StaticObject\tDice_Table\t%d\t%d\tId=Dice_Table_%s_%s" % (
                x * TW, y * TW, name.replace(",", "_").replace("-", "n"), g))
            placed += 1
            added = True
        if added:
            open(path, "wb").write("\r\n".join(lines).encode("cp1252"))

    ents_ini = Ini(p("data", "Entities.ini"))
    if "Play" not in ents_ini.get("Barkeep", "Use.Words"):
        ents_ini.set("Barkeep", "Use.Words", "Talk to,Play,Examine")
        ents_ini.save(p("data", "Entities.ini"))
    print("Dice tables: %d placed, %d pubs had one; no room in: %s" % (placed, kept, none))


if __name__ == "__main__":
    main()
