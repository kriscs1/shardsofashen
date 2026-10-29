"""Items, skills and quests that were renamed (dev\\migrate\\rename_items.py, rename_skills.py rename them in the data):
what a character or the world was saved with is put right as it loads - inventories, banks, hotbars, gear, market
listings, the action queue, skills."""
import json

RENAMED_ITEMS = {
    "Raw_Chicken": "Raw_Poultry",
    "Cooked_Chicken": "Cooked_Poultry",
    "Burnt_Chicken": "Burnt_Poultry",
    "Healing_Scroll_II": "Mega_Potion",              # (potions_and_spells.py: healing is the brewer's art)
    "Healing_Scroll": "Healing_Draught",
    "Farsight_Scroll": "Owl_Potion",
    "Stone_Skin_Scroll": "Shard_Ward_Scroll",
    "Stone_Skin": "Shard_Ward",
    "Access_Crystal": "Hearth_Anchor",                # (build_pocket.py: it holds your pocket of the realm's rim)
    "Staff_of_Estforlan": "Staff_of_Ashen",          # (rename_ashen.py: the kingdom is Ashen)
    "Raw_Fish": "Raw_Herring",                       # (rename_fish.py: the sea's fish is a herring)
    "Cooked_Fish": "Cooked_Herring",
    "Burnt_Fish": "Burnt_Herring",
}
RENAMED_SKILLS = {
    "Herblore": "Alchemy",
}
SKILL_NAMES = {                                      # (rename_skills.py: old name -> the skill it's part of now)
    "Magic": "Channeling",
    "Smithing": "Crafting",
    "Construction": "Homesteading",
    "Farming": "Homesteading",
    "Potion_Making": "Alchemy",
    "Herblore": "Alchemy",
}
RENAMED_QUESTS = {                                   # (build_heir_isle.py: the Isle's bank is Edwin and Maren's house)
    "Dinner at the Bank": "Dinner at Edwin's",
}
RENAMED_WORDS = {                                    # (rename_northport.py: in an attribute's name, Waystone.Southport)
    "Southport": "Northport",
}
RENAMED_MAPS = {                                     # (move_levels.py: levels of their own, moved further off)
    "0,0,5": "0,0,10",
    "21,4,-7": "21,4,-10",
}


def renamed(state):
    """state (anything JSON can hold) with every old item name the new one."""
    if not state:
        return state
    text = json.dumps(state)
    renames = dict(RENAMED_ITEMS, **RENAMED_SKILLS)
    if not any(old in text for old in renames):
        return state
    for old, new in renames.items():
        text = text.replace(old, new)
    return json.loads(text)


def renamed_map(name):
    return RENAMED_MAPS.get(name, name)


def merged_skills(skills):
    """A save's skills ({name: xp}) as they are now: an old name's xp under its new one, and two skills that are one
    now (Smithing and Crafting) the better of the two. A save from before Shardcraft starts it at half its Magic."""
    if not isinstance(skills, dict) or not skills:
        return skills
    out = dict(skills)
    for old, new in SKILL_NAMES.items():
        if old in out:
            x = out.pop(old)
            try:
                out[new] = max(float(out.get(new, 0) or 0), float(x or 0))
            except (TypeError, ValueError):
                out.setdefault(new, x)
    if "Shardcraft" not in out and "Magic" in skills:
        try:
            out["Shardcraft"] = max(1.0, round(float(skills["Magic"] or 0) * 0.5, 3))
        except (TypeError, ValueError):
            pass
    return out
