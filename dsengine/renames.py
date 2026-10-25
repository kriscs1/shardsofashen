"""Items that were renamed (dev\\migrate\\rename_items.py renames them in the data): what a character or the world was
saved with is put right as it loads - inventories, banks, hotbars, gear, market listings, the action queue."""
import json

RENAMED_ITEMS = {
    "Raw_Chicken": "Raw_Poultry",
    "Cooked_Chicken": "Cooked_Poultry",
    "Burnt_Chicken": "Burnt_Poultry",
}


def renamed(state):
    """state (anything JSON can hold) with every old item name the new one."""
    if not state:
        return state
    text = json.dumps(state)
    if not any(old in text for old in RENAMED_ITEMS):
        return state
    for old, new in RENAMED_ITEMS.items():
        text = text.replace(old, new)
    return json.loads(text)
