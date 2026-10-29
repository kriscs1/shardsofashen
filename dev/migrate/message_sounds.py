"""Scripts say what's heard with their messages: Display.Message COLOUR MESSAGE [SOUND]. The engine used to add the
Denied sound to any red message on its own; now a script's messages are silent unless the script gives a sound, so
this writes one into every red one (DarkRed, Red): Fail (a lute's "oh well") for an attempt that came to nothing -
the second half of a line, "..but fail to get any logs!" - and Denied (a low knock on a shut shutter) for anything else. Not one
with a sound already played right beside it (a Play.Sound or Play.Animation on the line before or after), nor one in
a map's own script (what you find on arriving). "-" says a line has no sound on purpose (a story's moment). Run it
again: nothing left to do.

  python -I "dev\\migrate\\message_sounds.py"
"""
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SOUNDING = ("Play.Sound", "Play.Animation", "Display.Refusal")
RED = ("DARKRED", "RED")


def main():
    files = lines_done = 0
    for path in sorted(glob.glob(os.path.join(ROOT, "data", "Scripts", "*.txt"))):
        if re.fullmatch(r"-?\d+,-?\d+,-?\d+", os.path.splitext(os.path.basename(path))[0]):
            continue                                      # (a map's own script: what you find on arriving)
        raw = open(path, "rb").read().decode("cp1252")
        nl = "\r\n" if "\r\n" in raw else "\n"
        lines = raw.split(nl)
        fields = [ln.split("\t") for ln in lines]
        cmd = [f[1] if len(f) > 1 and f[0].strip().isdigit() else "" for f in fields]
        changed = False
        for i, f in enumerate(fields):
            if cmd[i] != "Display.Message" or len(f) < 4 or f[2].strip().upper() not in RED:
                continue
            if len(f) > 4 and f[4].strip():
                continue                                  # (it says its sound already, or "-": none)
            near = [cmd[j] for j in (i - 1, i + 1) if 0 <= j < len(cmd)]
            if any(c in SOUNDING for c in near):
                continue                                  # (a sound is played right beside it)
            lines[i] = "\t".join(f[:4] + ["Fail" if f[3].startswith("..") else "Denied"])
            changed = True
            lines_done += 1
        if changed:
            open(path, "wb").write(nl.join(lines).encode("cp1252"))
            files += 1
    print("Fail or Denied written into %d messages in %d scripts" % (lines_done, files))


if __name__ == "__main__":
    main()
