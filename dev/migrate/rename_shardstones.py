"""Waystones become Shardstones: the object (Entities.ini, its sprites, the maps' StaticObject lines), its scripts
(Travel Shardstone, Shardstone Menu...), what's said of them, and the Config.ini [Shards] keys (Shardstone,
Shardstone.<Key>, Shardstone.Travel). What a save holds stays as it was: the attunements (attribute Waystone.<Key>)
and the place Ids (Waystone_<Key>), so nobody has to wake their stones again.
Safe to run again (a second run finds nothing to rename).
Usage: python -I dev/migrate/rename_shardstones.py"""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
KEEP = [r"Attr\.Waystone\.", r"Attribute\tWaystone\.", r"Waystone_"]  # (what saves hold)


def rename_text(s):
    held = []

    def hold(m):
        held.append(m.group(0))
        return "\x00%d\x00" % (len(held) - 1)
    for k in KEEP:
        s = re.sub(k, hold, s)
    s = s.replace("Waystone", "Shardstone").replace("waystone", "shardstone").replace("WAYSTONE", "SHARDSTONE")
    return re.sub("\x00(\\d+)\x00", lambda m: held[int(m.group(1))], s)


def redo(path, enc="cp1252"):
    b = open(path, "rb").read()
    s = b.decode(enc)
    t = rename_text(s)
    if t != s:
        open(path, "wb").write(t.encode(enc))
        return 1
    return 0


def main():
    n = 0
    data = os.path.join(ROOT, "data")
    for f in ("Entities.ini", "Config.ini"):
        n += redo(os.path.join(data, f))
    sd = os.path.join(data, "Scripts")
    for f in sorted(os.listdir(sd)):
        p = os.path.join(sd, f)
        n += redo(p)
        if "Waystone" in f:
            os.replace(p, os.path.join(sd, f.replace("Waystone", "Shardstone")))
            n += 1
    md = os.path.join(ROOT, "maps")
    for f in os.listdir(md):
        if f.endswith(".txt"):
            n += redo(os.path.join(md, f))
    ed = os.path.join(ROOT, "sprites", "Entities")
    for f in os.listdir(ed):
        if f.startswith("Waystone"):
            os.replace(os.path.join(ed, f), os.path.join(ed, f.replace("Waystone", "Shardstone")))
            n += 1
    print("Shardstones: %d files changed" % n)


if __name__ == "__main__":
    main()
