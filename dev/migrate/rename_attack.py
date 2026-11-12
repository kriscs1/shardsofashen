"""The Strength skill is Attack (dev/Roadmap-8.md, group 3): how well you land a blow and how hard.

What a save was saved with is put right as it loads (dsengine/renames.py SKILL_NAMES: Strength -> Attack), and a
script or a quest still saying Strength means Attack (skill_index). This renames it in the data (Config.ini's list,
Level.Skills, the icon and XP.Strength; Entities.ini's requirements; quests' rewards and words; the scripts) and in the
builders, so a builder run again writes the new name.

What stays Strength: a monster's or a guard's Strength= (how hard it hits: not a skill), Mob.Strength and
Strength.Per.Level (remnants, encounters), and the Strength_Potion (a strength potion still; it trains Attack).

Safe to run again (a second run changes nothing).

  python -I "dev\\migrate\\rename_attack.py"
"""
import glob
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SKIP = {"rename_attack.py", "rename_skills.py", "scale_skills.py", "migrate.py"}   # (the old ones: what they did then)

WORDS = [                                       # (where Strength can only be the skill)
    (r"(Update\.Skill|Boost\.Skill|Show\.Skill|SKILL)(\t|\\t)Strength\b", r"\1\2Attack"),
    (r"(\"(?:Update|Boost|Show)\.Skill\", \")Strength\"", r'\1Attack"'),
    (r"\$Skill\.Strength\b", "$Skill.Attack"),
    (r"\bStrength (?=\d)", "Attack "),                         # (Requires=Strength 5, Reward.XP=Strength 3 Defence 3)
    (r"\bStrength(?= and Defence| experience| drain)", "Attack"),
    (r"\b(your|Your) Strength\b", r"\1 Attack"),
    (r"\(Strength\)", "(Attack)"),
    (r"\bDefence and Strength\b", "Defence and Attack"),
]
CONFIG = [                                      # (data\Config.ini: the skill's own lines)
    (r"(?m)^List=Strength,", "List=Attack,"),
    (r"(?m)^Level\.Skills=Strength,", "Level.Skills=Attack,"),
    (r"(?m)^Icon\.Strength=", "Icon.Attack="),
    (r"(?m)^XP\.Strength=", "XP.Attack="),
    (r"(your )Strength( level)", r"\1Attack\2"),
    (r"\(Strength two thirds\)", "(Attack two thirds)"),
    (r"1 \+ Strength/4", "1 + Attack/4"),
]
STANCES = [(r"(?m)^XP\.To=Strength\b", "XP.To=Attack")]


def fix(path, rules, encoding):
    with open(path, "rb") as f:
        raw = f.read()
    t = raw.decode(encoding)
    new = t
    for a, b in rules:
        new = re.sub(a, b, new)
    if new != t:
        with open(path, "wb") as f:
            f.write(new.encode(encoding))
        print("  " + os.path.relpath(path, ROOT))


def main():
    data = os.path.join(ROOT, "data")
    fix(os.path.join(data, "Config.ini"), CONFIG + WORDS, "cp1252")
    fix(os.path.join(data, "Stances.ini"), STANCES, "cp1252")
    for path in glob.glob(os.path.join(data, "*.ini")) + glob.glob(os.path.join(data, "Scripts", "*.txt")):
        if os.path.basename(path) not in ("Config.ini", "Stances.ini"):
            fix(path, WORDS, "cp1252")
    for path in glob.glob(os.path.join(ROOT, "dev", "migrate", "*.py")):
        if os.path.basename(path) not in SKIP:
            fix(path, WORDS, "utf-8")


if __name__ == "__main__":
    main()
