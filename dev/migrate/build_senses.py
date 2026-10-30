"""Each monster's senses, by its kind (Entities.ini; npcs.py reads them):

  Sight.Cone    how wide it sees, in degrees: 360 all round (a bat, a spider's eyes, a Shard Remnant), a narrow wedge
                for the dull-eyed and the dead; a lookout's map line Cone= says otherwise. Its Aggro.Range is how far.
  Hearing       how keen its ears are: how far your noise carries to it, as a part of how far it carries (2 a bat,
                1.6 a wolf, 0.5 a scorpion, 0.3 a slime). One that looks one way turns to a sound; one that sees all
                round comes for it.
  Chase.Radius  how far from its ground it'll chase you, in tiles: raised to the least here for its kind (never
                lowered: a map line's Chase= still says).

Change the numbers in Entities.ini, or here and run it again (it sets what's here; safe to run again).

  python -I "dev\\migrate\\build_senses.py"
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import Ini, p                      # noqa: E402

# kind: (sight cone, hearing, chase radius at least)
SENSES = {
    "Goblin": (140, 1.0, 8), "Goblin_Archer": (140, 1.1, 8), "Goblin_Shaman": (160, 1.2, 7), "Hobgoblin": (130, 1.0, 8),
    "Hob": (150, 1.0, 7), "Rat": (200, 1.2, 5), "Bat": (360, 2.0, 9), "Wolf": (220, 1.6, 10),
    "Snow_Wolf": (220, 1.6, 10), "Alpha_Wolf": (240, 1.8, 11), "Ember_Hound": (220, 1.7, 10), "Bear": (160, 1.3, 8),
    "Giant_Spider": (360, 0.8, 7), "Scorpion": (180, 0.5, 6), "Skeleton": (110, 0.6, 6), "Skeleton_Archer": (120, 0.6, 6),
    "Barrow_King": (140, 0.8, 7), "Tomb_Guardian": (100, 0.5, 6), "Cave_Troll": (120, 0.7, 6), "Bog_Troll": (130, 0.7, 6),
    "Frost_Troll": (130, 0.8, 7), "Bandit": (150, 1.1, 9), "Smuggler": (110, 1.1, 8), "Ashen_Cultist": (150, 1.0, 8),
    "Ashen_Priest": (180, 1.2, 6), "Frost_Witch": (200, 1.3, 7), "Drake": (200, 1.4, 9), "Dragon": (360, 1.5, 9),
    "Galaith_Dragon": (360, 1.5, 6), "Living_Remnant": (360, 1.2, 10), "Shard_Warden": (360, 1.0, 10),
    "Goose": (300, 1.5, 4),
}
DEFAULT = (160, 1.0, 7)                         # (a foe not named here: one added later)


def main():
    ents = Ini(p("data", "Entities.ini"))
    n = 0
    for sec, _ in ents.sections:
        if (ents.get(sec, "Type") or "") != "NPC" or (ents.get(sec, "Attitude") or "") != "Bad":
            continue
        cone, hearing, chase = SENSES.get(sec, DEFAULT)
        old = float(ents.get(sec, "Chase.Radius") or 4)
        ents.set(sec, "Sight.Cone", str(cone))
        ents.set(sec, "Hearing", ("%g" % hearing))
        ents.set(sec, "Chase.Radius", ("%g" % max(old, chase)))
        n += 1
    ents.save(p("data", "Entities.ini"))
    print("Senses: %d monsters' sight, hearing and chase set" % n)
    print("Chase rectangles: %d given" % bound_chases(ents))


def bound_chases(ents):
    """A placed foe whose zone and Chase.Radius would cover its whole map gets a Chase rectangle a tile inside the
    edges (still its zone and more, never the whole map: validate.py)."""
    import re
    from build_isle import XT, YT
    n = 0
    for f in sorted(os.listdir(p("maps"))):
        if not re.match(r"^-?\d+,-?\d+,-?\d+\.txt$", f):
            continue
        path = p("maps", f)
        lines = open(path, "rb").read().decode("cp1252").split("\r\n")
        changed = False
        for i, ln in enumerate(lines):
            b = ln.split("\t")
            if len(b) < 4 or b[0] != "NPC" or (ents.get(b[1], "Aggressive") or "") != "1":
                continue
            opts = dict(o.split("=", 1) for o in (b[4] if len(b) > 4 else "").split() if "=" in o)
            if "Chase" in opts or "Patrol" in opts or opts.get("Stand", "0") not in ("0", ""):
                continue
            sx, sy = int(float(b[2])) // 32 + 1, int(float(b[3]) + 8) // 32 + 1
            roam = int(float(ents.get(b[1], "Roam.Radius") or 0))
            if "Zone" in opts:
                z = [int(v) for v in opts["Zone"].split(",")]
            else:
                z = [max(1, sx - roam), max(1, sy - roam), min(XT, sx + roam), min(YT, sy + roam)]
            cr = int(float(ents.get(b[1], "Chase.Radius") or 0))
            if (max(1, z[0] - cr), max(1, z[1] - cr), min(XT, z[2] + cr), min(YT, z[3] + cr)) != (1, 1, XT, YT):
                continue
            chase = (max(z[0] - cr, min(z[0], 2)), max(z[1] - cr, min(z[1], 2)),
                     min(z[2] + cr, max(z[2], XT - 1)), min(z[3] + cr, max(z[3], YT - 1)))
            if chase == (1, 1, XT, YT):
                continue                                        # (its zone's the whole map already)
            if len(b) == 4:
                b.append("")
            b[4] = (b[4] + " " if b[4] else "") + "Chase=%d,%d,%d,%d" % chase
            lines[i] = "\t".join(b)
            changed = True
            n += 1
        if changed:
            open(path, "wb").write("\r\n".join(lines).encode("cp1252"))
    return n


if __name__ == "__main__":
    main()
