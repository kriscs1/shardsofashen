"""The hanging signs over shop doors (Sign001-008, decor on a wall) are gone: every shop has its signboard on a post
outside now (build_market.py). Takes them off the maps (the wall stays) and out of the game's files: their pictures,
Tiles.ini, TileSets.ini, dev\\Minimap Colours.txt and decor_map.json. A second run does nothing.

  python -I "dev\\migrate\\remove_wall_signs.py"
"""
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SIGNS = ["Sign%03d" % i for i in range(1, 9)]
DECOR = re.compile(r"\+Decor\((%s)\)" % "|".join(SIGNS))


def rewrite(path, fix, enc="cp1252"):
    """fix(text) -> text; written back (as it was: its encoding and line ends) only if it changed."""
    with open(path, "rb") as f:
        raw = f.read()
    text = raw.decode(enc)
    new = fix(text)
    if new == text:
        return False
    with open(path, "wb") as f:
        f.write(new.encode(enc))
    return True


def drop_sections(text, names):
    """An ini file without the [name] sections (and the blank line after each)."""
    nl = "\r\n" if "\r\n" in text else "\n"
    out, skip = [], False
    for ln in text.split(nl):
        if ln.startswith("["):
            skip = ln.strip()[1:-1] in names
        if not skip:
            out.append(ln)
    return nl.join(out)


def main():
    n = 0
    for f in sorted(os.listdir(os.path.join(ROOT, "maps"))):
        if f.endswith(".txt") and rewrite(os.path.join(ROOT, "maps", f), lambda t: DECOR.sub("", t)):
            print("maps\\%s: the hanging signs taken down" % f)
            n += 1
    for name in SIGNS:
        pic = os.path.join(ROOT, "sprites", "Tiles", name + ".png")
        if os.path.exists(pic):
            os.remove(pic)
            n += 1
    data = os.path.join(ROOT, "data")
    n += rewrite(os.path.join(data, "Tiles.ini"), lambda t: drop_sections(t, set(SIGNS)))
    n += rewrite(os.path.join(data, "TileSets.ini"), lambda t: drop_sections(t, {"Sign"}))
    colours = os.path.join(ROOT, "dev", "Minimap Colours.txt")
    if os.path.exists(colours):
        n += rewrite(colours, lambda t: "".join(ln for ln in t.splitlines(True) if ln.split("\t")[0] not in SIGNS))
    dm = os.path.join(ROOT, "dev", "migrate", "decor_map.json")
    with open(dm, encoding="utf-8") as f:
        m = json.load(f)
    kept = {k: v for k, v in m.items() if v[1] not in SIGNS}
    if len(kept) != len(m):
        with open(dm, "w", encoding="utf-8", newline="\r\n") as f:
            json.dump(kept, f, indent=1)
        n += 1
    print("Wall signs removed (%d changes)" % n if n else "The wall signs are gone already")


if __name__ == "__main__":
    main()
