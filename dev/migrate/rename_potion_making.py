"""Herblore becomes Potion Making: the skill (Config.ini [Skills], its icon, Gathering.ini, Spells.ini, the alchemy
table's CRAFT-Potion_Making, the scripts that train or check it, "Potion_Making Skill"), what's said of it, the
builders (and dev\\migrate\\generated.json, so a rebuild knows the new names are its own), the docs and the new
character's start (saves\\TEMPLATE.ini). As a name it's Potion_Making (a script's word); in a sentence, Potion Making.
Characters saved before load with theirs renamed (dsengine/renames.py).
Safe to run again (a second run finds nothing to rename).
Usage: python -I dev/migrate/rename_potion_making.py"""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TOKEN = re.compile(r"(?:^|(?<=[=\t,\"'.\-]))Herblore(?!:)", re.M)     # (a name: Skill=Herblore, "Herblore")


def rename_text(s):
    s = TOKEN.sub("Potion_Making", s)
    s = s.replace("HERBLORE", "POTION_MAKING").replace("Herblore", "Potion Making").replace("herblore", "potion making")
    return s


def redo(path):
    b = open(path, "rb").read()
    try:
        s, enc = b.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        s, enc = b.decode("cp1252"), "cp1252"
    t = rename_text(s)
    if t != s:
        open(path, "wb").write(t.encode(enc))
        return 1
    return 0


def main():
    n = 0
    files = [os.path.join("data", f) for f in os.listdir(os.path.join(ROOT, "data")) if f.endswith(".ini")]
    files += [os.path.join("data", "Scripts", f) for f in os.listdir(os.path.join(ROOT, "data", "Scripts"))]
    files += [os.path.join("dev", "migrate", f) for f in os.listdir(os.path.join(ROOT, "dev", "migrate"))
              if f.endswith((".py", ".json")) and f != os.path.basename(__file__)]
    files += [os.path.join("dev", f) for f in ("Data Formats.md", "Story and Quests.md")]
    files += [os.path.join("dsengine", "player_items.py"), os.path.join("dsedit", "pages", "quests.py"),
              os.path.join("saves", "TEMPLATE.ini")]
    for f in files:
        if os.path.isfile(os.path.join(ROOT, f)):
            n += redo(os.path.join(ROOT, f))
    sd = os.path.join(ROOT, "data", "Scripts")
    old, new = os.path.join(sd, "Herblore Skill.txt"), os.path.join(sd, "Potion_Making Skill.txt")
    if os.path.exists(old):
        os.replace(old, new)
        n += 1
    print("Potion Making: %d files changed" % n)


if __name__ == "__main__":
    main()
