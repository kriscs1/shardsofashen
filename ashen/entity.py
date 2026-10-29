"""Entity types and the Entity record (the original kept these in the Entity.Info$(id, field) string array)."""
import itertools

PLAYER = 1
TILE = 2
MAPITEM = 3
STATICOBJECT = 4
NPC = 5             # people and monsters: one type, each Good (friendly) or Bad (a foe): Entity.hostile
MISSILE = 7
TEMPORARY = 8
ROOF = 9
INFRONTTILE = 10
FOGOFWAR = 11
ACTIONBOX = 12
ACTIONBOXITEM = 13
INVENTORYITEM = 14
QUANTITYDIGIT = 15
RIGHTCLICKMENU = 16
HEALTHBAR = 17
PLAYERGEAR = 18

TYPE_NAMES = {
    PLAYER: "Player", TILE: "Tile", MAPITEM: "MapItem", STATICOBJECT: "StaticObject", NPC: "NPC",
    MISSILE: "Missile", TEMPORARY: "TemporaryEntity", ROOF: "Roof", INFRONTTILE: "InfrontTile",
    FOGOFWAR: "FogOfWar", ACTIONBOX: "ActionBox", ACTIONBOXITEM: "ActionBoxItem", INVENTORYITEM: "InventoryItem",
    QUANTITYDIGIT: "QuantityDigit", RIGHTCLICKMENU: "RightClickMenu", HEALTHBAR: "Healthbar", PLAYERGEAR: "PlayerGear",
}

# How many of each the original allowed at once (Config [Entities] total.<Type>.IDs could change them)
DEFAULT_LIMITS = {MAPITEM: 300, STATICOBJECT: 160, NPC: 200, MISSILE: 20, TEMPORARY: 40}

WORLD_TYPES = (MAPITEM, STATICOBJECT, NPC, MISSILE, TEMPORARY)

# NPC movement states
AI_IDLE, AI_ROAM, AI_PATROL, AI_CHASE, AI_FLEE, AI_RETURN = 0, 1, 2, 3, 4, 5

_ids = itertools.count(1)


def normalise_type(type_name):
    t = str(type_name).strip().upper()
    if t in ("MAPITEM", "OBJECT", "ITEM"):
        return "MapItem"
    if t in ("STATICOBJECT", "STATIC"):
        return "StaticObject"
    if t in ("NPC", "GOODNPC", "BADNPC"):        # (GoodNPC and BadNPC: the old types, an NPC with that attitude)
        return "NPC"
    if t == "MISSILE":
        return "Missile"
    if t in ("TEMPORARY", "TEMPORARYENTITY"):
        return "TemporaryEntity"
    if t == "TILE":
        return "Tile"
    if t in ("INVENTORYITEM", "INVENTORY"):
        return "InventoryItem"
    return ""


def attitude_of_type(type_name):
    """The attitude an old type name stands for: GoodNPC -> Good, BadNPC -> Bad, anything else -> "" (not given)."""
    t = str(type_name).strip().upper()
    return {"GOODNPC": "Good", "BADNPC": "Bad"}.get(t, "")


def is_passive(value):
    """Attitude=Passive: can be attacked, but never attacks first (a rabbit, a hen)."""
    return str(value).strip().upper() == "PASSIVE"


def parse_attitude(value):
    """Good / Bad / Passive (any case; also Friendly, Hostile, 0, 1) -> True for Bad and Passive (they can be attacked),
    False for Good, None if it's neither."""
    v = str(value).strip().upper()
    if v in ("BAD", "HOSTILE", "ENEMY", "1", "PASSIVE"):
        return True
    if v in ("GOOD", "FRIENDLY", "FRIEND", "0"):
        return False
    return None


TYPE_BY_NAME = {v: k for k, v in TYPE_NAMES.items()}


class Entity:
    def __init__(self, etype, name):
        self.uid = next(_ids)
        self.type = etype
        self.name = name
        self.alive = True
        self.x = 0.0
        self.y = 0.0
        self.w = 32
        self.h = 32
        self.misc = ""
        self.quantity = 1
        self.qty_text = ""  # ActionBoxItem: what the digits show ("+" = unlimited)
        self.use_words = ""
        self.source = ""
        self.map = ""  # home map (world entities)
        self.active = True  # False while hidden under a roof or fog
        self.orig_x = 0.0
        self.orig_y = 0.0
        self.orig_quantity = 1
        # Pictures
        self.image = ""  # the picture shown now
        self.animated = False
        self.frame = 0
        self.last_changed = 0
        self.anim_dist = 0.0  # Pixels walked since the last step of the walking animation
        self.direction = 4
        # Fighting
        self.hp = 0
        self.max_hp = 0
        self.attack_speed = 0.8
        self.move_speed = 0.0
        self.strength = 0
        self.defence = 0
        self.aggro_range = 0
        self.weapon_range = 0
        self.aggressive = 0
        self.respawn_delay = 0
        self.last_attack = 0
        self.last_combat = 0
        self.in_combat = False
        self.show_bar = False
        self.slow_until = None
        self.normal_speed = None
        # Script moves and paths
        self.target_x = None
        self.target_y = None
        self.script_move = 0.0
        self.path = []  # [(x, y)...] waypoints (centre coordinates)
        self.path_goal = ""
        self.path_time = 0
        self.path_stuck = 0
        self.path_best = None
        # Lunge/recoil (Fx.Nudge)
        self.nudge_x = 0
        self.nudge_y = 0
        # NPC movement, and whether it's a foe (attitude Bad) or friendly (Good)
        self.ai = None
        self.hostile = False
        self.once = False  # a one-time item (Once=1): picked up, it never comes back
        self.npc_id = ""  # Id= on its map line (an NPC, item or object): scripts "<Verb> <Id>" come first (Read
        #                   Ashford, Pickup CellarKey, Kill OldHob); for an NPC it's also who Set.NPC.Attitude means

    def __repr__(self):
        return "<%s %s %d>" % (TYPE_NAMES.get(self.type, "?"), self.name, self.uid)

    @property
    def cx(self):
        return self.x + self.w / 2

    @property
    def cy(self):
        return self.y + self.h / 2

    @property
    def fx(self):
        return self.x + self.w / 2

    @property
    def fy(self):
        return self.y + self.h - 1


class NPCAI:
    """The movement settings and state of one NPC (the NPC.* slot arrays of the original)."""

    def __init__(self):
        self.state = AI_IDLE
        self.resume = AI_ROAM
        self.timer = 0
        self.turn_at = 0
        self.stand = 0
        self.goal_x = 0.0
        self.goal_y = 0.0
        self.goal_until = 0
        self.back_x = 0.0
        self.back_y = 0.0
        self.zone = [0, 0, 0, 0]  # L T R B (feet pixels)
        self.chase = [0, 0, 0, 0]
        self.walk_speed = 0.0
        self.pause_min = 1.0
        self.pause_max = 4.0
        self.calm_until = 0
        self.progress_time = 0
        self.best_d = 0.0
        self.options = ""
        self.way = []  # [(tx, ty)...]
        self.way_index = 1
        self.way_step = 1
        self.pingpong = 0
        self.solid = 1
        self.under = 0
        self.flying = 0
        self.indoors = True
        self.poses, self.pose_next, self.pose_next_at = [], "", 0
        self.roost = None
        self.home_ox = 0
        self.home_oy = 0
        self.skip_delta = 0.0
