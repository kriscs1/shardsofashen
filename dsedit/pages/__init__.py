def all_pages():
    from .maps import MapPage
    from .scripts import ScriptPage
    from .tiles import TilePage
    from .entities import EntityPage
    from .racks import RackPage
    from .spells import SpellPage
    from .quests import QuestPage
    from .buildables import BuildablePage
    from .crops import CropPage
    from .minimaps import MinimapPage
    return [MapPage, ScriptPage, TilePage, EntityPage, RackPage, SpellPage, QuestPage, BuildablePage, CropPage,
            MinimapPage]
