"""The kingdom of Estforlan becomes Ashen, the game Shards of Ashen, and Southport Northgate - in what's shown and
said: the data, the scripts, the maps' words, the page, the server, the app, the builders and the docs.

What's a name in the game's workings keeps it, so saves and scripts still find it: place Ids (Southport_Square,
Waystone_Southport), attunements (Waystone.Southport, Shardstone.Southport), script names (Ferry to Southport, Read
Southport for the notice with Id=Southport) and the builders' town keys ("Southport" in estforlan/layout.py; its
title is what's shown). The Staff of Estforlan is an item, shown by its name: it becomes Staff_of_Ashen, its pictures
and scripts with it (old saves: dsengine/renames.py).
Safe to run again (a second run finds nothing to rename).
Usage: python -I dev/migrate/rename_ashen.py"""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PROTECT = ["Ferry to Southport", "Bess Sails to Southport", "Read Southport", "Id=Southport", "Id\tSouthport\t"]
TOWN_TEXT = re.compile(r"(?<![A-Za-z0-9_.$=])Southport(?![A-Za-z0-9_])")
SKIP_DIRS = {".git", "Archive", "__pycache__", "build", ".gradle", "node_modules", "server-data", "saves"}
TEXT = (".ini", ".txt", ".md", ".py", ".js", ".html", ".css", ".json", ".xml", ".java", ".kt", ".gradle")


def rename_text(s, code):
    s = s.replace("Staff_of_Estforlan", "Staff_of_Ashen").replace("Estforlan", "Ashen").replace("ESTFORLAN", "ASHEN")
    s = re.sub(r"(?<![A-Z_])SOUTHPORT(?![A-Z_])", "NORTHGATE", s)            # (a sign's name, in capitals)
    keep = {}
    for i, p in enumerate(PROTECT):
        if p in s:
            keep["\x00%d\x00" % i] = p
            s = s.replace(p, "\x00%d\x00" % i)
    if code:                                    # (a key on its own in quotes, "Southport", stays: it makes Ids)
        def town(m):
            q = m.string[m.start() - 1:m.start()]
            return m.group(0) if q in ("\"", "'") and m.string[m.end():m.end() + 1] == q else "Northgate"
        s = TOWN_TEXT.sub(town, s)
    else:
        s = TOWN_TEXT.sub("Northgate", s)
    for k, p in keep.items():
        s = s.replace(k, p)
    return s


def redo(path):
    b = open(path, "rb").read()
    try:
        s, enc = b.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        s, enc = b.decode("cp1252"), "cp1252"
    code = path.endswith((".py", ".js", ".java", ".kt"))
    t = rename_text(s, code)
    if t != s:
        open(path, "wb").write(t.encode(enc))
        return 1
    return 0


def files():
    me = os.path.abspath(__file__)
    for d, dirs, names in os.walk(ROOT):
        dirs[:] = [x for x in dirs if x not in SKIP_DIRS and not x.startswith(".")
                   and os.path.join(d, x) != os.path.join(ROOT, "web", "assets")]     # (generated: exported again)
        for n in names:
            p = os.path.join(d, n)
            if n.endswith(TEXT) and os.path.abspath(p) != me and n != "renames.py":
                yield p


def rename_files():
    n = 0
    for sub in (os.path.join("sprites", "Entities"), os.path.join("sprites", "Worn"), os.path.join("data", "Scripts")):
        folder = os.path.join(ROOT, sub)
        for f in os.listdir(folder):
            if "Staff_of_Estforlan" in f:
                os.replace(os.path.join(folder, f), os.path.join(folder, f.replace("Staff_of_Estforlan", "Staff_of_Ashen")))
                n += 1
    return n


def renames():
    p = os.path.join(ROOT, "dsengine", "renames.py")
    s = open(p, "rb").read().decode("utf-8")
    if '"Staff_of_Estforlan"' not in s:
        nl = "\r\n" if "\r\n" in s else "\n"
        s = s.replace("\r\n", "\n").replace('''    "Stone_Skin": "Shard_Ward",''', '''    "Stone_Skin": "Shard_Ward",
    "Staff_of_Estforlan": "Staff_of_Ashen",          # (rename_ashen.py: the kingdom is Ashen)''')
        open(p, "wb").write(s.replace("\n", nl).encode("utf-8"))


def main():
    n = sum(redo(p) for p in files())
    m = rename_files()
    renames()
    print("Ashen: %d files changed, %d renamed" % (n, m))


if __name__ == "__main__":
    main()
