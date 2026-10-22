"""One-off (safe to run again: it does nothing the second time): rugs become decor, and the potted plants once drawn
against each wall become the one plant pot (decor_sets.py).

* Rug001-017 (on planks) become see-through decor; Rug031-047 (the same rugs on stone tiles) are merged into them:
  a map cell RugNNN becomes Plank001+Decor(RugNNN) or Tile001+Decor(Rug<NNN-30>).
* Decor(Potted_Plant_<Wall>_Thin_<Floor>NNN) and Decor(Potted_Plant001) become one of Potted_Plant001-005
  (common.decor_variant: by where it is).
* decor_map.json learns both, so the builders draw with the old rugs (kept in Dev\\Archive\\Decor split <date> rugs)
  and put the decor on new maps. The maps the builders made and you haven't changed are left for the next build.
Everything changed is copied first to Dev\\Archive\\Rugs and pots <date>. Then run build_world.py (it draws the new
rugs and plants: decor_sets.make_art)."""
import json
import os
import re
import shutil
import sys
import time

from common import HERE, NEW, GEN, MAP_H, p, read_lines, write_lines, decor_variant

RUG_KS = list(range(9)) + list(range(10, 17))
RUGS = {}
for _k in RUG_KS:
    RUGS["Rug%03d" % (1 + _k)] = ("Plank001", "Rug%03d" % (1 + _k))
    RUGS["Rug%03d" % (31 + _k)] = ("Tile001", "Rug%03d" % (1 + _k))


def main():
    sys.path.insert(0, NEW)
    from dsedit.project import IniDoc
    tiles = IniDoc(p("Data", "Tiles.ini"))
    if tiles.get("Rug001", "Layer") == "Decor":
        print("Already done: Rug001 is decor.")
        return
    dm_path = os.path.join(HERE, "decor_map.json")
    with open(dm_path, encoding="utf-8") as f:
        dm = json.load(f)
    pot_gone = sorted({d for _, d in dm.values() if d.startswith("Potted_Plant_")})
    stamp = time.strftime("%Y-%m-%d %H%M%S")
    backup = p("Dev", "Archive", "Rugs and pots " + stamp)
    opaque = p("Dev", "Archive", "Decor split %s rugs" % stamp, "Sprites", "Tiles")     # (the builders read these)
    os.makedirs(opaque, exist_ok=True)

    def keep(*rel):
        src = p(*rel)
        if os.path.exists(src):
            dst = os.path.join(backup, *rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
    for rel in (("Data", "Tiles.ini"), ("Dev", "Minimap Colours.txt"), ("Dev", "migrate", "decor_map.json")):
        keep(*rel)
    # the maps
    GEN.enable()
    done = {"rugs": 0, "pots": 0, "maps": 0, "left": 0}
    for folder, _, names in os.walk(p("Maps")):
        for fn in sorted(names):
            if not re.fullmatch(r"-?\d+,-?\d+,-?\d+\.txt", fn):
                continue
            path = os.path.join(folder, fn)
            if GEN.untouched(path):
                done["left"] += 1                       # (the next build makes it again, with the decor)
                continue
            lines = read_lines(path)
            changed = False
            for y in range(min(MAP_H, len(lines))):
                cells = lines[y].split(":")
                for x, cell in enumerate(cells):
                    parts = cell.split("+")
                    if parts[0] in RUGS and not any(q.startswith("Decor(") for q in parts[1:]):
                        floor, decor = RUGS[parts[0]]
                        parts = [floor, "Decor(%s)" % decor] + parts[1:]
                        done["rugs"] += 1
                    for i, q in enumerate(parts):
                        m = re.fullmatch(r"Decor\((Potted_Plant\w*)\)", q)
                        if m and (m.group(1) in pot_gone or m.group(1) == "Potted_Plant001"):
                            parts[i] = "Decor(%s)" % decor_variant("Potted_Plant001", x, y)
                            done["pots"] += 1
                    if "+".join(parts) != cell:
                        cells[x] = "+".join(parts)
                        changed = True
                lines[y] = ":".join(cells)
            if changed:
                keep(os.path.relpath(path, NEW))
                write_lines(path, lines)
                done["maps"] += 1
    # the sprites: the old rugs kept for the builders; the stone ones and the wall pots go
    for name in RUGS:
        src = p("Sprites", "Tiles", name + ".png")
        if os.path.exists(src):
            keep("Sprites", "Tiles", name + ".png")
            shutil.copy2(src, os.path.join(opaque, name + ".png"))
    gone = [n for n, (f, d) in RUGS.items() if d != n] + pot_gone
    for name in gone:
        src = p("Sprites", "Tiles", name + ".png")
        if os.path.exists(src):
            keep("Sprites", "Tiles", name + ".png")
            os.remove(src)
        tiles.remove_section(name)
    for name in RUGS:
        if RUGS[name][1] == name:
            tiles.set(name, "Layer", "Decor")
    tiles.save()
    mm = p("Dev", "Minimap Colours.txt")
    lines = read_lines(mm)
    write_lines(mm, [l for l in lines if l.split("\t")[0] not in set(gone)])
    # decor_map.json
    for k, (f, d) in list(dm.items()):
        if d in pot_gone:
            dm[k] = [f, "Potted_Plant001"]
    dm.update({k: list(v) for k, v in RUGS.items()})
    with open(dm_path, "w", encoding="utf-8") as f:
        json.dump(dict(sorted(dm.items())), f, indent=1)
    with open(os.path.join(backup, "README.txt"), "w", encoding="utf-8") as f:
        f.write("Made by Dev\\migrate\\migrate_rugs_pots.py on %s: the files as they were before.\n%s\n" % (stamp, done))
    print("Rugs to decor: %(rugs)d cells, plant pots: %(pots)d, in %(maps)d maps (%(left)d left for the build)." % done)
    print("Gone:", ", ".join(gone))
    print("Backup:", backup)


if __name__ == "__main__":
    main()
