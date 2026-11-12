"""Stairs and ladders: the climb is heard first, then you move (the owner: "do the sound then actually move").

The six that go to the same X,Y a level up or down (Climb Up/Down Stairs, Ladder001/002/008/009) are written again
from build_content.py's climb_script: >Map.Exists first, then the Ladder sound, a moment (Wait 0.4), then the
Teleport. Every other Climb script that teleports somewhere fixed gets its Ladder sound before the Teleport and the
same moment between them. Safe to run again (a script with its Wait already is left alone).

  python -I "dev\\migrate\\climb_sound_first.py"
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRIPTS = os.path.join(ROOT, "data", "Scripts")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

GENERIC = (("Climb Up Ladder001", "up", "+1", "You climb up the ladder."),
           ("Climb Down Ladder002", "down", "-1", "You climb down the ladder."),
           ("Climb Up Ladder008", "up", "+1", "You climb up the ladder into the loft."),
           ("Climb Down Ladder009", "down", "-1", "You climb down the ladder."),
           ("Climb Up Stairs", "up", "+1", "You go up the stairs."),
           ("Climb Down Stairs", "down", "-1", "You go down the stairs."))
PAUSE = "0.4"


def compile_steps(steps):
    """Steps (comments, "label:" and command tuples, "@label" for a line) as a script's lines."""
    labels, n = {}, 0
    for st in steps:
        if isinstance(st, str) and st.endswith(":") and not st.startswith("//"):
            labels[st[:-1]] = "%02d" % (n + 1)
        elif not isinstance(st, str):
            n += 1
    out, n = [], 0
    for st in steps:
        if isinstance(st, str):
            if st.startswith("//"):
                out.append(st)
            continue
        n += 1
        out.append("\t".join(["%02d" % n] + [labels[a[1:]] if a.startswith("@") else a for a in st]))
    return out


def read(name):
    path = os.path.join(SCRIPTS, name + ".script")
    return open(path, "rb").read().decode("cp1252").split("\r\n")


def write(name, lines):
    with open(os.path.join(SCRIPTS, name + ".script"), "wb") as f:
        f.write("\r\n".join(lines).encode("cp1252"))


def insert_line(lines, at, fields):
    """Puts a command in as line number at (1-based), renumbering the rest and every goto that pointed past it."""
    out = []
    for ln in lines:
        b = ln.split("\t")
        if not re.fullmatch(r"\d\d+", b[0]):
            out.append(ln)
            continue
        no = int(b[0])
        cmd = b[1] if len(b) > 1 else ""
        if cmd.startswith(">") or cmd == "Display.Conversation" or cmd == "Goto":
            for k in range(2, len(b)):
                if re.fullmatch(r"\d\d+", b[k]) and int(b[k]) >= at and (cmd != "Display.Conversation" or k % 2 == 1):
                    b[k] = "%02d" % (int(b[k]) + 1)
        if no == at:
            out.append("\t".join(["%02d" % at] + list(fields)))
        if no >= at:
            b[0] = "%02d" % (no + 1)
        out.append("\t".join(b))
    return out


def fix_fixed(name):
    lines = read(name)
    cmds = [ln.split("\t") for ln in lines]
    if any(len(b) > 1 and b[1] == "Wait" for b in cmds):
        return False
    tele = next((int(b[0]) for b in cmds if len(b) > 1 and b[1] == "Teleport"), None)
    if tele is None:
        return False
    sound = next((int(b[0]) for b in cmds if len(b) > 2 and b[1] == "Play.Sound" and b[2] == "Ladder"), None)
    if sound is None:
        return False
    if sound == tele + 1:                            # (heard after the move: the sound goes first)
        for i, b in enumerate(cmds):
            if len(b) > 1 and int(b[0] or 0) in (tele, sound) and re.fullmatch(r"\d\d+", b[0]):
                b[0] = "%02d" % (sound if int(b[0]) == tele else tele)
        cmds.sort(key=lambda b: (0, int(b[0])) if re.fullmatch(r"\d\d+", b[0]) else (-1, 0))
        lines = ["\t".join(b) for b in cmds]
    elif sound > tele:
        return False
    tele = next(int(ln.split("\t")[0]) for ln in lines if "\tTeleport\t" in ln)
    write(name, insert_line(lines, tele, ("Wait", PAUSE)))
    return True


def main():
    from build_content import climb_script
    n = 0
    for name, verb, dz, msg in GENERIC:
        new = compile_steps(climb_script(verb, dz, msg))
        if read(name)[:len(new)] != new:
            write(name, new)
            n += 1
    for f in sorted(os.listdir(SCRIPTS)):
        name = f[:-7]
        if f.startswith("Climb ") and f.endswith(".script") and name not in dict((g[0], 1) for g in GENERIC):
            n += fix_fixed(name)
    print("Climbs: %d scripts heard first, then moved" % n)


if __name__ == "__main__":
    main()
