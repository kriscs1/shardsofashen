"""Skills out of 25 (they were out of 50), once. What a level needs is halved everywhere it's written, so the same
progress is the same place on the way:
  * Config.ini [Gameplay]: Skill.Max.Level 25, Hitpoints.Per.Level doubled (the same hitpoints for the same
    progress), XP.Slowdown halved and XP.Scale 0.5 (every skill's gains halved: as fast to the top as before);
  * every level asked for: Gathering, Buildables, Crops and Spells.ini Level=, Shards.ini Level.<rank>=, a crafting
    recipe's level, an item's Requires=, a quest's Requires.Level and Requires.Skills, the scripts' skill checks
    ($Variable.N>=10 after Get.Value SKILL, $Skill.Strength>=2), and what's said of them ("level 10 Woodcutting",
    "(Potion Making 5)", "Magic 30");
  * the scripts' chances of success, which add the skill to a roll: it counts twice ($Variable.1*2), so the odds
    are as they were. (The monsters' Level= is out of 25 already: build_remnants.py.)
A level L becomes max(min(L, 2), ceil(L / 2)): 1 stays 1, 2 stays 2 (Brother Aldous's sword and shield), 10 is 5.
Characters' skills are scaled as they load (dsengine/session.py: "skills_of" in a save says what they were out of).
It refuses to run again (Config.ini Skill.Max.Level is 25 already).
Usage: python -I dev/migrate/scale_skills.py"""
import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import Ini, p                      # noqa: E402

SKILLS = ["Strength", "Defence", "Cooking", "Smithing", "Fishing", "Mining", "Woodcutting", "Potion Making",
          "Potion_Making", "Crafting", "Magic", "Construction", "Farming"]
SK = "|".join(re.escape(s) for s in SKILLS)
CHANGED = []


def h(n):
    n = int(n)
    return max(min(n, 2), int(math.ceil(n / 2.0)))


def words(s):
    """What's said of a level: "level 10 Woodcutting", "Woodcutting level 10", "(Potion Making 5)", "Magic 30"."""
    s = re.sub(r"\b(level )(\d+)( (?:%s))\b" % SK, lambda m: m.group(1) + str(h(m.group(2))) + m.group(3), s)
    s = re.sub(r"\b((?:%s) level (?:of )?)(\d+)\b" % SK, lambda m: m.group(1) + str(h(m.group(2))), s)
    s = re.sub(r"\b((?:%s) )(\d+)\b" % SK, lambda m: m.group(1) + str(h(m.group(2))), s)
    return s


def pairs(v):
    """"Woodcutting 10, Potion_Making 5" (Requires.Skills, Requires=): each level halved."""
    return re.sub(r"\b([A-Za-z_]+)(\s+)(\d+)\b", lambda m: m.group(1) + m.group(2) + str(h(m.group(3))), v)


def edit_ini(name, fn):
    path = p("data", name)
    ini = Ini(path)
    before = "\n".join(ini.lines())
    for sec, items in ini.sections:
        for i, (k, v) in enumerate(items):
            items[i] = fn(sec, k, v)
    if "\n".join(ini.lines()) != before:
        ini.save(path)
        CHANGED.append(name)
    return ini


def level_key(sec, k, v):
    if k is not None and (k == "Level" or re.fullmatch(r"Level\.\d+", k)) and v.strip().isdigit():
        return k, str(h(v))
    if k is not None and k in ("Examine.Info", "Where", "Name"):
        return k, words(v)
    return k, v


def config():
    path = p("data", "Config.ini")
    text = open(path, "rb").read().decode("cp1252")
    if re.search(r"(?m)^Skill\.Max\.Level\s*=\s*25\s*$", text):
        sys.exit("Skills are out of 25 already: this has been run.")
    text = re.sub(r"(?m)^Skill\.Max\.Level\s*=\s*\d+", "Skill.Max.Level = 25", text)
    text = re.sub(r"(?m)^Hitpoints\.Per\.Level\s*=\s*([\d.]+)",
                  lambda m: "Hitpoints.Per.Level = %g" % (float(m.group(1)) * 2), text)
    text = re.sub(r"(?m)^(XP\.Slowdown\s*=\s*)([\d.]+)\r?$",
                  lambda m: "%s%g\r\n;Every skill's gains are XP.Scale times what a script or the game gives\r\n"
                            "XP.Scale = 0.5" % (m.group(1), float(m.group(2)) / 2), text)
    open(path, "wb").write(text.encode("cp1252"))
    CHANGED.append("Config.ini")


def entities(sec, k, v):
    if k == "Requires":
        return k, pairs(v)
    if k == "Examine.Info":
        return k, words(v)
    return k, v


def quests(sec, k, v):
    if k == "Requires.Level" and v.strip().isdigit():
        return k, str(h(v))
    if k == "Requires.Skills":
        return k, pairs(v)
    if k is not None and (k.startswith("Stage") or k in ("Description", "Summary")):
        return k, words(v)
    return k, v


def racks(sec, k, v):
    if k is not None and re.fullmatch(r"Item\d+", k) and sec.upper().startswith("CRAFT"):
        f = v.split(",")
        if len(f) >= 4 and f[3].strip().isdigit():
            f[3] = str(h(f[3]))
            return k, ",".join(f)
    return k, v


def script(text):
    """A script: its skill checks halved, its rolls counting the skill twice, and what it says of levels."""
    held = set(re.findall(r"Get\.Value\tSKILL\t[^\t]+\t(Variable\.\d+)\$", text))
    out = []
    for line in text.split("\n"):
        f = line.split("\t")
        if len(f) > 2 and f[1] == ">Conditional":
            cond = f[2]
            for v in held:
                cond = re.sub(r"\$%s(\s*)(>=|>|<=|<|=)(\s*)(\d+)\b" % re.escape(v),
                              lambda m: "$%s%s%s%s%s" % (v, m.group(1), m.group(2), m.group(3), h(m.group(4))), cond)
                if "$Random.Percent" in cond:
                    cond = re.sub(r"\$%s(?![\d*])" % re.escape(v), "$%s*2" % v, cond)
            cond = re.sub(r"(\$Skill\.[A-Za-z_]+\s*(?:>=|>|<=|<|=)\s*)(\d+)\b",
                          lambda m: m.group(1) + str(h(m.group(2))), cond)
            f[2] = cond
        elif len(f) > 2 and f[1] in ("Display.Message", "Display.Conversation", "Quest.Note", "Display.Text"):
            f = f[:2] + [words(x) for x in f[2:]]
        out.append("\t".join(f))
    return "\n".join(out)


def scripts():
    sd = p("data", "Scripts")
    n = 0
    for name in sorted(os.listdir(sd)):
        path = os.path.join(sd, name)
        raw = open(path, "rb").read().decode("cp1252")
        text = raw.replace("\r\n", "\n")
        new = script(text)
        if new != text:
            open(path, "wb").write(new.replace("\n", "\r\n").encode("cp1252"))
            n += 1
    CHANGED.append("%d scripts" % n)


def template():
    path = p("saves", "TEMPLATE.ini")
    ini = Ini(path)
    for i, (k, v) in enumerate((ini.section("Skills") or [None, []])[1]):
        if k is not None and k.upper() != "HITPOINTS" and v.strip() not in ("", "0", "1"):
            ini.section("Skills")[1][i] = (k, "%g" % max(1.0, float(v) / 2))
    ini.save(path)


def main():
    config()
    for name in ("Gathering.ini", "Buildables.ini", "Crops.ini", "Spells.ini", "Shards.ini", "Tiles.ini"):
        edit_ini(name, level_key)
    edit_ini("Entities.ini", entities)
    edit_ini("Quests.ini", quests)
    edit_ini("ItemRacks.ini", racks)
    scripts()
    template()
    print("Skills out of 25: " + ", ".join(CHANGED))


if __name__ == "__main__":
    main()
