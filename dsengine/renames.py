"""Items, skills and quests that were renamed (dev\\migrate\\rename_items.py, rename_skills.py rename them in the data):
what a character or the world was saved with is put right as it loads - inventories, banks, hotbars, gear, market
listings, the action queue, skills."""
import json
import re

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
    "Burnt_Poultry": "Burnt_Food",                   # (burnt_food.py: every burnt dish is one heap of charcoal)
    "Burnt_Herring": "Burnt_Food",
    "Burnt_Meat": "Burnt_Food",
}
RENAMED_WHOLE = {                                    # (only the item's own name, never inside another's: Name=Shard_Remnant
    "Shard_Remnant": "Shard",                        # is a risen one's, and stays. Shards in a pack or a bank go onto
}                                                    # the balance as it loads: shards.py; on the ground, picked up so)
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
    "Strength": "Attack",                            # (rename_attack.py)
}
RENAMED_QUESTS = {                                   # (build_heir_isle.py: the Isle's bank is Edwin and Maren's house)
    "Dinner at the Bank": "Dinner at Edwin's",
    "Wolves of the Moor": "Wolves of the Greyflats",          # (rename_sallowcross.py)
}
RENAMED_WORDS = {                                    # (rename_northport.py: in an attribute's name, Waystone.Southport)
    "Southport": "Northport",
    "Moorcross": "Greyford",                             # (rename_sallowcross.py, rename_greyford.py: Waystone.Moorcross,
    "Sallowcross": "Greyford",                           # Secret_Moorcross, and what it was called for a day after)
    "Dustlands": "Sallow_Waste",                         # (and Zone_Chest_Dustlands)
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
    if not any(old in text for old in list(renames) + list(RENAMED_WHOLE)):
        return state
    for old, new in renames.items():
        text = text.replace(old, new)
    return renamed_whole(json.loads(text))


WHOLE = re.compile(r"(?<![\w=])(%s)(?!\w)" % "|".join(map(re.escape, RENAMED_WHOLE)))


def renamed_whole(v):
    """RENAMED_WHOLE in every string of v, as a word of its own (a queue line's tab-parted name, an inventory's)."""
    if isinstance(v, str):
        return WHOLE.sub(lambda m: RENAMED_WHOLE[m.group(1)], v)
    if isinstance(v, list):
        return [renamed_whole(x) for x in v]
    if isinstance(v, dict):
        return {k: renamed_whole(x) for k, x in v.items()}
    return v


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
