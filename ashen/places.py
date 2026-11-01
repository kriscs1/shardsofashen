"""Named places: IDs that scripts and quests use instead of coordinates.

A place is either a tile with an ID (a map line "Id<TAB>Name<TAB>X<TAB>Y", X and Y the tile, 1-25 and 1-21, as for
a Trigger) or anything placed on a map with Id=Name in its options (an NPC, an item, an object: the Id= that already
picks its scripts, e.g. Read Ashford). IDs are unique across the whole world, so a name says which map too.

Where a script takes coordinates ("X COORDINATE,Y COORDINATE", "TARGET X,TARGET Y", tile coordinates) it can take a
place's name instead: Teleport  Ashford_Bank_Door  (no map needed), Change.Tile  Old_Well  Well002, Edit.Entity
Lair_Dragon  Dragon  HP  -90. A named NPC or object is found by its ID wherever it has wandered to. Quests.ini
markers may name places too: Marker1=Ferry_Pier;Milkmaid (the old "<map> <x> <y>" still works)."""
import os

from .lb import field, trim, val

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

