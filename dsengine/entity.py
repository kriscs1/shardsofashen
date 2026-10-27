"""The Entity record of the desktop game, with what a shared world needs as well: the level it is on (z), whose it is
if it belongs to one player only (a quest's own NPC or item), and who an NPC is fighting."""
from dragonsword.entity import (Entity as _Entity, NPCAI, PLAYER, TILE, MAPITEM, STATICOBJECT, NPC, MISSILE, TEMPORARY,
                                ROOF, INFRONTTILE, ACTIONBOXITEM, INVENTORYITEM, TYPE_NAMES, TYPE_BY_NAME, WORLD_TYPES,
                                AI_IDLE, AI_ROAM, AI_PATROL, AI_CHASE, AI_FLEE, AI_RETURN, normalise_type,
                                attitude_of_type, parse_attitude)

__all__ = ["Entity", "NPCAI", "InvItem", "PLAYER", "TILE", "MAPITEM", "STATICOBJECT", "NPC", "MISSILE", "TEMPORARY",
           "ROOF", "INFRONTTILE", "ACTIONBOXITEM", "INVENTORYITEM", "TYPE_NAMES", "TYPE_BY_NAME", "WORLD_TYPES",
           "AI_IDLE", "AI_ROAM", "AI_PATROL", "AI_CHASE", "AI_FLEE", "AI_RETURN", "normalise_type", "attitude_of_type",
           "parse_attitude"]


class Entity(_Entity):
    def __init__(self, etype, name):
        super().__init__(etype, name)
        self.z = 0
        self.owner = None           # a Session: only that player sees it (made by their quest)
        self.target = None          # an NPC's foe in a fight (a Session)
        self.wear = 0
        self.sched_away = False
        self.sched_stuck = 0
        self.edits_done = set()     # (script, line): a quest's one-off edits already made to it
        self.private_to = None      # a Session: just dropped by them, only they see it until public_at (ms)
        self.public_at = 0
        self.display = ""           # a name of its own (the map's Name=Marta), shown instead of the sprite's
        self.pose = ""              # how it rests when it stops (Sit: <Name>_Sit<dir>), "" = standing
        self.npc_foe = None         # an NPC it hunts, or runs from, or fights back (Hunts=)
        self.follow = None          # the Session it walks after (Follow.Player)
        self.frozen_until = None    # a spell's ice (or stun) holds it still till then (clock ms)
        self.frozen_word = ""       # "frozen" or "stunned": how it's held, and how it looks


class InvItem:
    """One inventory slot: an item, how many, how worn (weapons and armour)."""
    __slots__ = ("uid", "name", "quantity", "wear", "alive", "type", "misc", "x", "y")
    _next = [1]

    def __init__(self, name, quantity=1, wear=0):
        self.uid = InvItem._next[0]
        InvItem._next[0] += 1
        self.name = name
        self.quantity = quantity
        self.wear = wear
        self.alive = True
        self.type = INVENTORYITEM
        self.misc = ""
        self.x = self.y = 0

    @property
    def npc_id(self):
        return ""

    @property
    def display(self):
        return ""

    @property
    def use_words(self):
        return ""
