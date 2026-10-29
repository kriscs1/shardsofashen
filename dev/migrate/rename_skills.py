"""The skills as they are now (CLAUDE.md, Skills):

  * Magic is Channeling (the use and control of magic: casting, and the less a spell costs the better you are);
  * Shardcraft is new (making and working Shard magic: dismantling, writing scrolls and spells, waking shardstones
    and the Shardgate, enchanting, absorbing remnants, shaping your pocket of the Shardrealm);
  * Smithing and Crafting are one skill, Crafting;
  * Construction and Farming are one skill, Homesteading;
  * Potion Making is Alchemy.

The order on the Stats tab: Strength, Defence, Channeling, Shardcraft, then the rest. What a save was saved with is put
right as it loads (dsengine/renames.py SKILL_NAMES, session.load_state): a merged skill keeps the better of the two.
This renames them in the data (Config.ini's list and icons, Entities.ini's requirements and scrolls' words, racks,
quests' rewards, spells, the scripts) and in the builders, so a builder run again writes the new names.

The item stat Magic= (spell damage on a staff, Spells.ini's boost of it) is not the skill and stays.

Safe to run again (a second run changes nothing).

  python -I "dev\\migrate\\rename_skills.py"
"""
import glob
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ORDER = ["Strength", "Defence", "Channeling", "Shardcraft", "Hitpoints", "Cooking", "Crafting", "Fishing", "Mining",
         "Woodcutting", "Alchemy", "Homesteading"]
ICONS = {"Channeling": "Magic_Burst", "Shardcraft": "Skill_Shardcraft", "Crafting": "Anvil", "Alchemy": "Skill_Alchemy",
         "Homesteading": "Skill_Homesteading"}
PLAIN = [                                       # (anywhere the word stands alone: these names mean only the skill)
    (r"\b(Smithing|Crafting) and (Smithing|Crafting)\b", "Crafting"),
    (r"\b(Construction|Farming) and (Construction|Farming)\b", "Homesteading"),
    (r"\bPotion[_ ]Making\b", "Alchemy"),
    (r"\bHerblore\b(?!\")", "Alchemy"),
    (r"\bSmithing\b", "Crafting"),
    (r"\bConstruction\b", "Homesteading"),
    (r"\bFarming\b", "Homesteading"),
]
MAGIC = [                                       # (Magic the skill, not the Magic= stat or a word in a sentence)
    (r"(Skill=|Update\.Skill\t|Show\.Skill\t|SKILL\t|Boost\.Skill\t)Magic\b", r"\1Channeling"),
    (r"(Reward\.XP=[^\r\n]*?)\bMagic( \d)", r"\1Channeling\2"),
    (r"(Requires(?:\.Skills)?=[^\r\n]*?)\bMagic( \d)", r"\1Channeling\2"),
    (r"(Reward\.XP=[^\r\n]*?)\bMagic( \d)", r"\1Channeling\2"),         # (a second Magic on the line)
    (r"\. Magic (\d+)\. ", r". Channeling \1. "),                        # (a scroll's words: "... Magic 5. Read it")
]


def at(*p):
    return os.path.join(ROOT, *p)


def rewrite(path, fn):
    with open(path, "rb") as f:
        raw = f.read()
    new = fn(raw.decode("latin-1")).encode("latin-1")       # (byte for byte: cp1252 data and utf-8 code alike)
    if new != raw:
        with open(path, "wb") as f:
            f.write(new)
        print("updated", os.path.relpath(path, ROOT))


def keeping_racks(fn, t):
    """fn(t), the racks' names (CRAFT-Smithing...) left as they are: they're only names."""
    racks = []

    def hide(m):
        racks.append(m.group(0))
        return "\x00%d\x00" % (len(racks) - 1)
    t = fn(re.sub(r"CRAFT-[A-Za-z_]+", hide, t))
    return re.sub(r"\x00(\d+)\x00", lambda m: racks[int(m.group(1))], t)


def data_text(t):
    return keeping_racks(_data_text, t)


def _data_text(t):
    for pat, rep in PLAIN + MAGIC:
        t = re.sub(pat, rep, t)
    t = t.replace("[CRAFT-Scrolls]\r\nType=Craft\r\nSkill=Channeling", "[CRAFT-Scrolls]\r\nType=Craft\r\nSkill=Shardcraft")
    return t


def config(t):
    t = re.sub(r"(?m)^List=Strength,[^\r\n]*", "List=" + ",".join(ORDER), t)
    t = re.sub(r"(?m)^Level\.Skills=Strength,Defence,Magic\b", "Level.Skills=Strength,Defence,Channeling", t)
    t = re.sub(r"(?m)^Icon\.(Smithing|Magic|Potion_Making|Alchemy|Construction|Farming|Homesteading|Crafting|"
               r"Channeling|Shardcraft)=[^\r\n]*\r\n", "", t)
    icons = "".join("Icon.%s=%s\r\n" % kv for kv in ICONS.items())
    return t.replace("Icon.Hitpoints=Heart\r\n", "Icon.Hitpoints=Heart\r\n" + icons, 1)


def shards_ini(t):
    return t.replace("; Magic xp for each\r\nAbsorb.Magic.XP=", "; Shardcraft xp for each\r\nAbsorb.XP=")


CODE = [                                        # (the builders: the same, where they write a skill's name)
    (r"\b(Smithing|Crafting) and (Smithing|Crafting)\b", "Crafting"),
    (r"\b(Construction|Farming) and (Construction|Farming)\b", "Homesteading"),
    (r"\bPotion[_ ]Making\b", "Alchemy"),
    (r"([\"'\t ])Smithing\b", r"\1Crafting"),
    (r"([\"'\t ])Construction\b", r"\1Homesteading"),
    (r"([\"'\t ])Farming\b", r"\1Homesteading"),
    (r"(Skill=|Update\.Skill\\t|Show\.Skill\\t|SKILL\\t|Boost\.Skill\\t|\"Skill\": \")Magic\b", r"\1Channeling"),
    (r"(Reward\.XP\"?: ?\"[^\"\n]*?)\bMagic( \d)", r"\1Channeling\2"),
    (r"(Reward\.XP=[^\"\n]*?)\bMagic( \d)", r"\1Channeling\2"),
    (r"(\"Requires\"?: ?\"[^\"\n]*?)\bMagic( \d)", r"\1Channeling\2"),
    (r"(Requires=[^\"\n]*?)\bMagic( \d)", r"\1Channeling\2"),
    (r"\. Magic %", ". Channeling %"),
    (r"\. Magic (\d+)\. ", r". Channeling \1. "),
]


def code_text(t):
    return keeping_racks(_code_text, t)


def _code_text(t):
    for pat, rep in CODE:
        t = re.sub(pat, rep, t)
    return t


def save_skills(t):
    """A saves\\*.ini's [Skills] as they are now: renamed, merged (the better of two), Shardcraft from half its Magic."""
    m = re.search(r"(?ms)^\[Skills\]\r?\n(.*?)(?=^\[|\Z)", t)
    if not m:
        return t
    old = dict(ln.split("=", 1) for ln in m.group(1).splitlines() if "=" in ln)
    if all(k in old for k in ORDER):
        return t
    num = lambda v: float(v or 0)
    new = {}
    for k in ORDER:
        froms = [k] + [o for o, n in (("Magic", "Channeling"), ("Smithing", "Crafting"), ("Construction", "Homesteading"),
                                      ("Farming", "Homesteading"), ("Potion_Making", "Alchemy"),
                                      ("Herblore", "Alchemy")) if n == k]
        have = [num(old[f]) for f in froms if f in old]
        new[k] = max(have) if have else (max(1.0, num(old.get("Magic")) * 0.5) if k == "Shardcraft" else 1.0)
    eol = "\r\n" if "\r\n" in t else "\n"
    text = "".join("%s=%s%s" % (k, "%.10g" % v, eol) for k, v in new.items()) + eol
    return t[:m.start(1)] + text + t[m.end(1):]


def main():
    for f in glob.glob(at("saves", "*.ini")):
        rewrite(f, save_skills)
    rewrite(at("data", "Config.ini"), config)
    rewrite(at("data", "Shards.ini"), shards_ini)
    for f in glob.glob(at("data", "*.ini")) + glob.glob(at("data", "Scripts", "*.txt")):
        if not f.endswith("Config.ini"):
            rewrite(f, data_text)
    builders = glob.glob(at("dev", "migrate", "*.py")) + glob.glob(at("dev", "migrate", "estforlan", "*.py"))
    for f in builders:
        if os.path.basename(f) not in ("rename_skills.py", "validate.py", "rename_potion_making.py", "scale_skills.py",
                                       "build_shardcraft.py"):
            rewrite(f, code_text)


if __name__ == "__main__":
    main()
