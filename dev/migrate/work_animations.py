"""The work of the hands, seen: gathering scripts show the skill over the player's head as they start (Show.Skill),
and their work sound becomes Play.Animation - chips fly off the tree at each swing of the axe, the player leaning
in, as a blow in a fight does. Run it again: a script that has them already is left alone.

  python -I "dev\\migrate\\work_animations.py"

  Chop *            Woodcutting   Wood_Chips  a beat each 0.8 s of the script's Wait
  Mine *            Mining        Rock_Chips
  Fish *            Fishing       Splash      (one cast)
  Dig Sand          (none)        Dirt_Clods
  Use Shears With Sheep  Crafting  Wool_Tufts
  Pick *            Alchemy      (no animation: a skill shown)
Inserting a line moves the ones after it down: every jump to them (any argument that is a line number, as
dragonsword/script_language.py names them) moves with them.
"""
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from dragonsword import script_language as L  # noqa: E402

SCRIPTS = os.path.join(ROOT, "data", "Scripts")
# script name pattern: (skill, animation, the work sound it replaces or None, fixed beats or None)
WORK = [
    (r"Chop .*", "Woodcutting", "Wood_Chips", None),
    (r"Mine .*", "Mining", "Rock_Chips", None),
    (r"Fish .*", "Fishing", "Splash", 1),
    (r"Dig Sand", "", "Dirt_Clods", None),
    (r"Use Shears With Sheep", "Crafting", "Wool_Tufts", None),
    (r"Pick .*", "Alchemy", "", None),
]
LINE_ARGS = {name: [i for i, t in enumerate(args) if "LINE" in t.upper() and "FILE" not in t.upper()
                    and t.upper() not in ("LINE", "LINE TO ADD", "LINE TO REMOVE")]
             for name, args in L.COMMANDS}


def parse(path):
    raw = open(path, "rb").read().decode("cp1252")
    nl = "\r\n" if "\r\n" in raw else "\n"
    head, body = [], []
    for ln in raw.split(nl):
        if not body and (ln.startswith("//") or not ln.strip()):
            head.append(ln)
        elif ln.strip():
            body.append(ln.split("\t"))
    return nl, head, body


def insert(body, at, fields):
    """fields as line at (1-based); every line number from at on, and every jump to one, moves down one."""
    for f in body:
        for i in LINE_ARGS.get(f[1], []):
            k = 2 + i
            if k < len(f) and f[k].strip().isdigit() and int(f[k]) >= at:
                f[k] = "%02d" % (int(f[k]) + 1)
    body.insert(at - 1, ["", fields[0]] + fields[1:])
    for n, f in enumerate(body, 1):
        f[0] = "%02d" % n


def beats(body, i):
    """A beat every 0.8 s of the Wait after line i (at least one)."""
    for f in body[i:i + 3]:
        if f[1] == "Wait" and len(f) > 2:
            try:
                return max(1, min(8, int(round(float(f[2]) / 0.8))))
            except ValueError:
                pass
    return 2


def main():
    n = 0
    for path in sorted(glob.glob(os.path.join(SCRIPTS, "*.txt"))):
        name = os.path.splitext(os.path.basename(path))[0]
        rule = next((r for r in WORK if re.fullmatch(r[0], name)), None)
        if rule is None:
            continue
        nl, head, body = parse(path)
        if any(f[1] in ("Show.Skill", "Play.Animation") for f in body):
            continue
        _, skill, anim, fixed = rule
        # where the work starts: its sound, else the Wait that stands for it
        at = next((i for i, f in enumerate(body) if f[1] == "Play.Sound"), None)
        if at is None:
            at = next((i for i, f in enumerate(body) if f[1] == "Wait"), None)
            if at is None:
                continue
            if anim:
                insert(body, at + 1, ["Play.Animation", anim, str(fixed or beats(body, at)), ""])
        elif anim:
            sound = body[at][2] if len(body[at]) > 2 else ""
            body[at] = [body[at][0], "Play.Animation", anim, str(fixed or beats(body, at + 1)), sound]
        if skill:
            insert(body, at + 1, ["Show.Skill", skill])
        text = nl.join(head + ["\t".join(f) for f in body]) + nl
        open(path, "wb").write(text.encode("cp1252"))
        n += 1
    print("Work shown in %d scripts" % n)


if __name__ == "__main__":
    main()
