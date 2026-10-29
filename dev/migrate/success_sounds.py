"""Doing well is heard as well as read: a gathering or cooking script's line that says it worked (the one before its
Give.Item) gets a sound of its own, by what was done (build_soundscape.py made them):

  Chop -> Gather_Wood    Mine -> Gather_Ore    Fish -> Gather_Fish    Pick, Harvest, Collect -> Harvest
  Use <food> With <fire, range...>, giving Cooked_ or Fried_ -> Cooked    Use <a with b>, making something -> Crafted

Only a line with no sound given (a sound already there, or "-", is kept), never a red one. New gathering scripts
should say theirs (as work_animations.py adds the work's animation). Run it again: nothing left to do.

  python -I "dev\\migrate\\success_sounds.py"
"""
import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import p                           # noqa: E402

BY_VERB = {"Chop": "Gather_Wood", "Mine": "Gather_Ore", "Fish": "Gather_Fish", "Pick": "Harvest",
           "Harvest": "Harvest", "Collect": "Harvest"}


def sound_for(script, given):
    verb = script.split(" ")[0]
    if verb in BY_VERB:
        return BY_VERB[verb]
    if verb == "Use" and " With " in script:
        if given.startswith(("Cooked_", "Fried_")):
            return "Cooked"
        if given not in ("Bucket",):                   # (a bucket thrown on a fire gives the bucket back: not made)
            return "Crafted"
    return ""


def main():
    changed = 0
    for path in glob.glob(p("data", "Scripts", "*.txt")):
        script = os.path.basename(path)[:-4]
        text = open(path, "rb").read().decode("cp1252")
        lines = text.split("\r\n")
        out = False
        for i, ln in enumerate(lines):
            parts = ln.split("\t")
            if len(parts) != 4 or parts[1] != "Display.Message" or parts[2] in ("DarkRed", "Red"):
                continue
            given = [q.split("\t")[2] for q in lines[i + 1:i + 3]
                     if len(q.split("\t")) > 2 and q.split("\t")[1] == "Give.Item"]
            if not given:
                continue
            sound = sound_for(script, given[0])
            if sound:
                lines[i] = ln + "\t" + sound
                out = True
        if out:
            open(path, "wb").write("\r\n".join(lines).encode("cp1252"))
            changed += 1
    print("Success sounds: %d scripts" % changed)


if __name__ == "__main__":
    main()
