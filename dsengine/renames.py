"""Items and skills that were renamed (dev\\migrate\\rename_items.py, rename_potion_making.py rename them in the data):
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
    "Staff_of_Estforlan": "Staff_of_Ashen",          # (rename_ashen.py: the kingdom is Ashen)                      # (the spell, as it was learnt)
}
RENAMED_SKILLS = {
    "Herblore": "Potion_Making",
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
