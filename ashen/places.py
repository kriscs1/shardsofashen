"""Named places: IDs that scripts and quests use instead of coordinates.

A place is either a tile with an ID (a map line "Id<TAB>Name<TAB>X<TAB>Y", X and Y the tile, 1-25 and 1-21, as for
a Trigger) or anything placed on a map with Id=Name in its options (an NPC, an item, an object: the Id= that already
picks its scripts, e.g. Read Ashford). IDs are unique across the whole world, so a name says which map too.

Where a script takes coordinates ("X COORDINATE,Y COORDINATE", "TARGET X,TARGET Y", tile coordinates) it can take a
place's name instead: Teleport  Ashford_Bank_Door  (no map needed), Change.Tile  Old_Well  Well002, Edit.Entity
Lair_Dragon  Dragon  HP  -90. A named NPC or object is found by its ID wherever it has wandered to. Quests.ini
markers may name places too: Marker1=Ferry_Pier;Milkmaid (the old "<map> <x> <y>" still works)."""
import os

from .lb import field, trim, val, word

PIXEL_ARGS = {"Remove.Entity": (1,), "Add.Entity": (1,), "Teleport": (1,), "Edit.Entity": (1,), "Move.Entity": (1, 3),
              "Move.Player": (1,), ">Distance.From.Coordinates": (1,), ">Entity.In.Line.Of.Sight": (1,),
              "Add.Action.To.Queue": (6,)}
TILE_ARGS = {"Change.Tile": (1,), ">Tile.In.Line.Of.Sight": (1,), ">On.Tile.Coordinates": (1,),
             ">Not.On.Tile.Coordinates": (1,)}
MAP_ARGS = {"Teleport": 2, "Add.Action.To.Queue": 5}
ENTITY_COMMANDS = ("Remove.Entity", "Edit.Entity", "Move.Entity")
ENTITY_TYPES = ("NPC", "GoodNPC", "BadNPC", "MapItem", "StaticObject", "Object", "Static")


class Place:
    __slots__ = ("name", "map", "tx", "ty", "px", "py", "kind", "entity")

    def __init__(self, name, map_name, tx, ty, px, py, kind, entity=""):
        self.name, self.map, self.kind, self.entity = name, map_name, kind, entity
        self.tx, self.ty, self.px, self.py = tx, ty, px, py


def option_id(misc):
    """The Id= in a map line's options ("3 Id=CellarKey Once=1" -> CellarKey)."""
    for part in misc.split():
        if part.upper().startswith("ID="):
            return part[3:]
    return ""


def read_places(maps_dir, map_h=21, tile=32):
    """{UPPER name: Place} for every map in maps_dir, and [(name, map, other map)] for names used twice."""
    found, twice = {}, []
    try:
        files = sorted(f for f in os.listdir(maps_dir) if f.lower().endswith(".txt"))
    except OSError:
        return found, twice
    for f in files:
        name = f[:-4]
        try:
            with open(os.path.join(maps_dir, f), "rb") as fh:
                lines = fh.read().decode("cp1252", errors="replace").replace("\r", "").split("\n")
        except OSError:
            continue
        for line in lines[map_h:]:
            kind = trim(field(line, 1, "\t"))
            if kind == "Id":
                pid = trim(field(line, 2, "\t"))
                tx, ty = int(val(field(line, 3, "\t"))), int(val(field(line, 4, "\t")))
                place = Place(pid, name, tx, ty, (tx - 1) * tile, (ty - 1) * tile, "TILE")
            elif kind in ENTITY_TYPES:
                misc = trim(field(line, 5, "\t") + " " + field(line, 6, "\t"))
                pid = option_id(misc)
                if not pid:
                    continue
                px, py = val(field(line, 3, "\t")), val(field(line, 4, "\t"))
                place = Place(pid, name, int((px + 16) // tile) + 1, int((py + 28) // tile) + 1, px, py, kind,
                              trim(field(line, 2, "\t")))
            else:
                continue
            if not pid:
                continue
            key = pid.upper()
            if key in found:
                twice.append((pid, found[key].map, name))
                continue
            found[key] = place
    return found, twice


class PlacesMixin:
    def places(self):
        """Every named place, read from the maps (again when a map file has changed since: the editor's IDs show up
        without restarting)."""
        folder = os.path.join(self.root, "maps")
        try:
            stamp = max((e.stat().st_mtime for e in os.scandir(folder) if e.name.lower().endswith(".txt")), default=0)
        except OSError:
            stamp = 0
        cache = self.__dict__.get("places_cache")
        if cache is None or cache[0] != stamp:
            found, twice = read_places(folder, self.yt, self.tw)
            for pid, a, b in twice:
                self.log("ERROR - Place ID '%s' is on both %s and %s (IDs must be unique; %s's is used)" % (pid, a, b, a))
            cache = self.places_cache = (stamp, found)
        return cache[1]

    def place(self, name):
        """The Place called name (any case), or None. Coordinates, numbers and $ variables are never places."""
        name = trim(name)
        if not name or "," in name or " " in name or name[:1] in "$-+=0123456789":
            return None
        return self.places().get(name.upper())

    def placed_entity(self, pid):
        """The entity in the world with this Id= (where it is now), or None."""
        pid = pid.upper()
        for e in self.world:
            if getattr(e, "npc_id", "") and e.npc_id.upper() == pid and e.alive:
                return e
        return None

    def place_args(self, command, arg):
        """A script line's arguments with any place names turned into the coordinates (and map) the command wants.
        Returns the Place given for an entity command (Remove/Edit/Move.Entity), so it is found by its ID."""
        tiles = TILE_ARGS.get(command, ())
        pixels = PIXEL_ARGS.get(command, ())
        if command == "Add.Action.To.Queue" and arg[1].upper() == "CHANGE.TILE":
            tiles, pixels = pixels, ()
        named = None
        for i in tiles + pixels:
            if command in (">On.Tile.Coordinates", ">Not.On.Tile.Coordinates"):    # (a list: "x,y x,y" or names)
                parts = []
                for part in arg[i].split():
                    pl = self.place(part)
                    parts.append("%d,%d" % (pl.tx, pl.ty) if pl else part)
                    if pl:
                        self.place_on_this_map(pl, command)
                arg[i] = " ".join(parts)
                continue
            pl = self.place(arg[i])
            if pl is None:
                if arg[i] and "," not in arg[i] and arg[i][:1] not in "$-" and command != "Add.Action.To.Queue":
                    self.log("ERROR - Script %s: '%s' is not a place ID or coordinates (%s)" % (
                        self.script_name, arg[i], command))
                continue
            if i == 1 and command in ENTITY_COMMANDS and pl.kind != "TILE":
                named = pl
            if command == "Add.Entity" and pl.kind == "TILE":  # standing on the tile: centred, feet on its bottom row
                w, h = self.assets.width(arg[2]), self.assets.height(arg[2])
                arg[i] = "%d,%d" % (pl.px + (self.tw - w) // 2, pl.py + self.th - h)
            else:
                arg[i] = "%d,%d" % ((pl.tx, pl.ty) if i in tiles else (pl.px, pl.py))
            m = MAP_ARGS.get(command)
            if m:
                if arg[m] in ("", "-"):
                    arg[m] = pl.map
            elif named is None:
                self.place_on_this_map(pl, command)
        return named

    def place_on_this_map(self, pl, command):
        if pl.map != self.screen_name:
            self.log("ERROR - Script %s: %s uses place '%s', which is on map %s, not this one (%s)" % (
                self.script_name, command, pl.name, pl.map, self.screen_name))

    def place_marker(self, part):
        """A quest marker: (map, tile x, tile y) from "<map> <x> <y>" or a place's name; None if it names nothing."""
        part = trim(part)
        if " " in part:
            return word(part, 1), val(word(part, 2)), val(word(part, 3))
        pl = self.place(part)
        if pl is None:
            self.log("ERROR - Quests.ini: marker '%s' is not a place ID" % part)
            return None
        return pl.map, pl.tx, pl.ty
