"""Night folk: in each town (townsfolk on maps that lie together), one ordinary man, woman or villager (never on the
Isle) keeps the night's hours (Schedule=Night on their map line: npcs.py schedule_npc): at home by day, asleep in
their bed if they have one, and out about the streets after dark, when the rest are abed. Never anyone with words of their own (a Talk to script by
their Id), a part to play (an Id that's more than where they live: the town crier) or a quest. The guards and the tavern keepers already stay up all night (no bed, no hours); Schedule=Always
says so for anyone else (never home, never to bed). Safe to run again (a town with a night owl already is left alone).

  python -I "dev\\migrate\\night_folk.py"
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MAPS = os.path.join(ROOT, "maps")
SCRIPTS = os.path.join(ROOT, "data", "Scripts")
KINDS = ("Man", "Woman", "Villager")
PLAIN = re.compile(r"_(Resident|Villager|Man|Woman|Townsfolk)_?\d*$")   # (an Id that's only where they live)
ISLE = {"0,0,0", "0,1,0", "1,0,0", "1,1,0", "1,2,0", "2,0,0", "2,1,0", "2,2,0", "3,0,0", "3,1,0", "3,2,0", "4,0,0",
        "4,1,0"}                                     # (the Isle is left as it's built)


def towns():
    """[[(map, line no, fields)]] of the plain townsfolk, grouped by town (maps no more than 2 apart, on level 0)."""
    folk = []
    for f in sorted(os.listdir(MAPS)):
        m = re.match(r"^(-?\d+),(-?\d+),0\.txt$", f)
        if not m or f[:-4] in ISLE:
            continue
        lines = open(os.path.join(MAPS, f), "rb").read().decode("cp1252").split("\r\n")
        for i, ln in enumerate(lines):
            b = ln.split("\t")
            if len(b) >= 4 and b[0] == "NPC" and b[1] in KINDS:
                folk.append(((int(m.group(1)), int(m.group(2))), f[:-4], i, b))
    groups = []
    for at, *rest in folk:
        home = next((g for g in groups if any(max(abs(at[0] - o[0][0]), abs(at[1] - o[0][1])) <= 2 for o in g)), None)
        if home is None:
            groups.append([(at, *rest)])
        else:
            home.append((at, *rest))
    return [[r[1:] for r in g] for g in groups]


def opts_of(b):
    return dict(o.split("=", 1) for o in (b[4] if len(b) > 4 else "").split() if "=" in o)


def main():
    n = 0
    for town in towns():
        if len(town) < 3 or any(opts_of(b).get("Schedule") == "Night" for _, _, b in town):
            continue                                 # (a hamlet's few: all of them abed; or it has its night owl)
        pick = None
        for name, i, b in sorted(town, key=lambda t: (t[0], t[1])):
            o = opts_of(b)
            if o.get("Schedule") or o.get("Patrol") or (o.get("Id") and (os.path.exists(
                    os.path.join(SCRIPTS, "Talk to %s.txt" % o["Id"])) or not PLAIN.search(o["Id"]))):
                continue                             # (a crier, a foreman, anyone with a part to play: never)
            pick = (name, i, b)
            break
        if pick is None:
            continue
        name, i, b = pick
        path = os.path.join(MAPS, name + ".txt")
        lines = open(path, "rb").read().decode("cp1252").split("\r\n")
        b = lines[i].split("\t")
        while len(b) < 5:
            b.append("")
        b[4] = (b[4] + " Schedule=Night").strip()
        lines[i] = "\t".join(b)
        open(path, "wb").write("\r\n".join(lines).encode("cp1252"))
        n += 1
        print("A night owl: the %s at %s,%s on %s" % (b[1].lower(), b[2], b[3], name))
    print("Night folk: %d" % n)


if __name__ == "__main__":
    main()
