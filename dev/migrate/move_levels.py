"""Moves two levels of their own: the arena from 0,0,5 to 0,0,10 (well above any upstairs) and the Shardrealm from
21,4,-7 to 21,4,-10 (far below, under the hill's ring of stones). The maps, their entry scripts, their minimaps, and
every name for them in the data, the builders, the tests and the docs. dsengine/renames.py RENAMED_MAPS puts a save
that was on the old map on the new one.

Safe to run again (a second run finds nothing to move).

  python -I "dev\\migrate\\move_levels.py"
"""
import os
import re
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MOVES = {"0,0,5": "0,0,10", "21,4,-7": "21,4,-10"}
ZS = {"5": "10", "-7": "-10"}                   # (their levels: the minimaps' pictures and origins)


def at(*p):
    return os.path.join(ROOT, *p)


def mv(old, new):
    if os.path.exists(at(old)) and not os.path.exists(at(new)):
        r = subprocess.run(["git", "mv", old, new], cwd=ROOT, capture_output=True)
        if r.returncode:
            os.rename(at(old), at(new))
        print("moved", old, "->", new)


def rewrite(path, fn):
    with open(path, "rb") as f:
        raw = f.read()
    new = fn(raw.decode("latin-1")).encode("latin-1")  # (byte for byte: cp1252 data and utf-8 code alike)
    if new != raw:
        with open(path, "wb") as f:
            f.write(new)
        print("updated", os.path.relpath(path, ROOT))


def names(text):
    for old, new in MOVES.items():
        text = re.sub(r"(?<![\d,.\-])%s(?![\d,])" % re.escape(old), new, text)
    return text


def main():
    for old, new in MOVES.items():
        mv("maps/%s.txt" % old, "maps/%s.txt" % new)
        mv("data/Scripts/%s.txt" % old, "data/Scripts/%s.txt" % new)
    for old, new in ZS.items():
        mv("sprites/Interface/Minimap%s.png" % old, "sprites/Interface/Minimap%s.png" % new)
    rewrite(at("data", "Config.ini"), lambda t: names(re.sub(
        r"(?m)^Origin\.(5|-7)=", lambda m: "Origin.%s=" % ZS[m.group(1)], t)))
    files = [at("data", f) for f in os.listdir(at("data")) if f.lower().endswith(".ini")]
    files += [at("data", "Scripts", f) for f in os.listdir(at("data", "Scripts")) if f.endswith(".txt")]
    files += [at("maps", f) for f in os.listdir(at("maps")) if f.endswith(".txt")]
    for d in ("dev/migrate", "dev/migrate/estforlan", "tests", "dsengine", "server"):
        files += [at(d, f) for f in os.listdir(at(d)) if f.endswith(".py") and f != "move_levels.py"]
    files += [at("CLAUDE.md"), at("README-Server.md"), at("dev", "Story and Quests.md"), at("dev", "World Plan.md")]
    for path in files:
        if os.path.isfile(path) and not path.endswith("renames.py"):
            rewrite(path, names)


if __name__ == "__main__":
    main()
