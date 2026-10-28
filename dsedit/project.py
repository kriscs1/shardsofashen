"""The game's data, as the editor sees it: paths, ini files edited in place, maps, scripts, sprites, and an index of
where everything is used. Files are read and written the way dev\\migrate does (ANSI cp1252, CRLF on every line), so
the builders' "keep your edits" check (dev\\migrate\\common.py GEN) sees exactly what you changed."""
import os
import re

from PIL import Image

ENC = "cp1252"
SLOTS = ["Weapon", "Shield", "Head", "Body", "Legs", "Feet", "Hands", "Ring"]
ENTITY_TYPES = ["MapItem", "StaticObject", "NPC"]
# Tile families (the Tiles list and the map palette): a tile is in the first family with a keyword in its name
TILE_FAMILIES = [("Roofs", "roof"), ("Furniture & Props", "bed table chair bookshelf plant fireplace rug carpet throne "
                 "pillar banner torch statue fountain hedge stairs anvil furnace range barrel crate log fence grave "
                 "haystack portal scarecrow tent well"),
                 ("Cave", "cave mine_ stalagmite"), ("Water", "water pool puddle pond"),
                 ("Trees", "tree pine forest stump willow oak yew"), ("Rocks & Ore", "rock ore"),
                 ("Plants", "bush herb mushroom weed wheat nest flower reed grass_tall tall_grass cactus myrtle"),
                 ("Cliffs & Ladders", "cliff ladder"), ("Walls & Buildings", "wall brick door window upper plank tile "
                 "timber plaster sandstone city_ gate paving marble"),
                 ("Ground", "grass dirt sand stone black snow ice marsh field")]


def tile_family(name):
    n = name.lower()
    for fam, keys in TILE_FAMILIES:
        if any(k in n for k in keys.split()):
            return fam
    return "Other"


def read_text_lines(path):
    with open(path, "rb") as f:
        data = f.read()
    if data.startswith(b"\xef\xbb\xbf"):
        data = data[3:]
    text = data.decode(ENC, errors="replace")
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    return lines


def write_text_lines(path, lines):
    """ANSI, CRLF after every line. Only writes when something changed. Returns True if written."""
    data = "".join(l + "\r\n" for l in lines).encode(ENC, errors="replace")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if os.path.exists(path):
        with open(path, "rb") as f:
            if f.read() == data:
                return False
    with open(path, "wb") as f:
        f.write(data)
    return True


def mtime(path):
    try:
        st = os.stat(path)
        return (st.st_mtime_ns, st.st_size)
    except OSError:
        return None


# =================================================================================================================
# Ini files, edited in place: every comment, blank line and key you don't touch stays as it was
# =================================================================================================================
class IniDoc:
    def __init__(self, path):
        self.path = path
        self.load()

    def load(self):
        self.lines = read_text_lines(self.path) if os.path.exists(self.path) else []
        self.stamp = mtime(self.path)

    def changed_on_disk(self):
        return mtime(self.path) != self.stamp

    # --- where things are
    def _bounds(self, sec):
        """(header line, first body line, end) of the first section called sec, or None."""
        want = sec.strip().lower()
        start = None
        for i, l in enumerate(self.lines):
            s = l.strip()
            if s.startswith("[") and "]" in s:
                if start is not None:
                    return start, start + 1, i
                if s[1:s.index("]")].strip().lower() == want:
                    start = i
        if start is not None:
            return start, start + 1, len(self.lines)
        return None

    @staticmethod
    def _key_of(line):
        s = line.strip()
        if not s or s.startswith(";") or s.startswith("[") or "=" not in s:
            return None
        return s.split("=", 1)[0].strip()

    def sections(self):
        out, seen = [], set()
        for l in self.lines:
            s = l.strip()
            if s.startswith("[") and "]" in s:
                name = s[1:s.index("]")].strip()
                if name.lower() not in seen:
                    seen.add(name.lower())
                    out.append(name)
        return out

    def has_section(self, sec):
        return self._bounds(sec) is not None

    def items(self, sec):
        """[(key, value)] in file order (every one, even repeats)."""
        b = self._bounds(sec)
        if not b:
            return []
        out = []
        for l in self.lines[b[1]:b[2]]:
            k = self._key_of(l)
            if k is not None:
                v = l.split("=", 1)[1].strip()
                if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
                    v = v[1:-1]
                out.append((k, v))
        return out

    def get(self, sec, key, default=""):
        for k, v in self.items(sec):
            if k.lower() == key.lower():
                return v
        return default

    # --- changes
    def add_section(self, sec):
        if self.has_section(sec):
            return
        while self.lines and self.lines[-1].strip() == "":
            self.lines.pop()
        if self.lines:
            self.lines.append("")
        self.lines.append("[%s]" % sec)

    def set(self, sec, key, value):
        """Sets key (its first line in the section), or adds it after the section's last key. "" removes it."""
        value = str(value)
        if value == "":
            self.remove(sec, key)
            return
        b = self._bounds(sec)
        if not b:
            self.add_section(sec)
            self.lines.append("%s=%s" % (key, value))
            return
        last = b[0]
        for i in range(b[1], b[2]):
            k = self._key_of(self.lines[i])
            if k is not None:
                last = i
                if k.lower() == key.lower():
                    self.lines[i] = "%s=%s" % (k, value)
                    return
        self.lines.insert(last + 1, "%s=%s" % (key, value))

    def remove(self, sec, key):
        b = self._bounds(sec)
        if not b:
            return
        keep = self.lines[:b[1]]
        for l in self.lines[b[1]:b[2]]:
            k = self._key_of(l)
            if k is None or k.lower() != key.lower():
                keep.append(l)
        self.lines = keep + self.lines[b[2]:]

    def set_items(self, sec, items):
        """The section's keys become items [(key, value)] (comments in it stay at the top)."""
        b = self._bounds(sec)
        if not b:
            self.add_section(sec)
            b = self._bounds(sec)
        body = self.lines[b[1]:b[2]]
        comments = [l for l in body if self._key_of(l) is None and l.strip()]
        trailing = [""] if b[2] < len(self.lines) else []
        new = comments + ["%s=%s" % (k, v) for k, v in items if str(v) != ""] + trailing
        self.lines = self.lines[:b[1]] + new + self.lines[b[2]:]

    def remove_section(self, sec):
        b = self._bounds(sec)
        if not b:
            return
        start = b[0]
        while start > 0 and self.lines[start - 1].strip() == "":
            start -= 1
        self.lines = self.lines[:start] + ([""] if start > 0 and b[2] < len(self.lines) else []) + self.lines[b[2]:]
        while self.lines and self.lines[-1].strip() == "":
            self.lines.pop()

    def rename_section(self, old, new):
        b = self._bounds(old)
        if b:
            self.lines[b[0]] = "[%s]" % new

    def snapshot(self):
        return list(self.lines)

    def restore(self, snap):
        self.lines = list(snap)

    def save(self):
        written = write_text_lines(self.path, self.lines)
        self.stamp = mtime(self.path)
        return written


# =================================================================================================================
# Maps
# =================================================================================================================
OVERLAY = re.compile(r"\+([A-Za-z]+)\(([^)]*)\)")


class Cell:
    """A map cell: its tile and its overlays in their order ([(kind, arg)]; +Decor(Name), +Roof(Name.Group),
    +Infront(Name), and anything else kept as it is)."""
    __slots__ = ("tile", "parts")

    def __init__(self, text):
        text = text.strip()
        i = text.find("+")
        self.tile = text if i < 0 else text[:i]
        self.parts = [(m.group(1), m.group(2)) for m in OVERLAY.finditer(text[i:])] if i >= 0 else []

    def text(self):
        return self.tile + "".join("+%s(%s)" % p for p in self.parts)

    def _get(self, kind):
        for k, a in self.parts:
            if k.lower() == kind.lower():
                return a
        return None

    def _set(self, kind, arg):
        for i, (k, a) in enumerate(self.parts):
            if k.lower() == kind.lower():
                if arg is None:
                    del self.parts[i]
                else:
                    self.parts[i] = (k, arg)
                return
        if arg is not None:
            self.parts.append((kind, arg))

    @property
    def decor(self):
        return self._get("Decor") or ""

    def set_decor(self, name):
        """The see-through tile over the ground (written first, before any roof or tree top)."""
        if name and self._get("Decor") is None:
            self.parts.insert(0, ("Decor", name))
        else:
            self._set("Decor", name or None)

    @property
    def under(self):
        return self._get("Under") or ""

    def set_under(self, name):
        """Something flat on the floor (a rug, Layer=Under), under the decor: written before it."""
        if name and self._get("Under") is None:
            self.parts.insert(0, ("Under", name))
        else:
            self._set("Under", name or None)

    @property
    def roof(self):
        a = self._get("Roof")
        return a.rsplit(".", 1)[0] if a else ""

    @property
    def roof_group(self):
        a = self._get("Roof")
        return a.rsplit(".", 1)[1] if a and "." in a else ""

    def set_roof(self, name, group="01"):
        self._set("Roof", "%s.%s" % (name, group) if name else None)

    @property
    def infront(self):
        return self._get("Infront") or ""

    def set_infront(self, name):
        self._set("Infront", name or None)


PLACE_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]*$")       # a place ID (the game's places.py)
COORD_TYPES = {"X COORDINATE,Y COORDINATE", "TARGET X,TARGET Y", "REQUIRED TILE COORDINATES",
               "DISALLOWED TILE COORDINATES"}             # script arguments that can name a place instead


class Entity:
    """A map line after the tile rows. kind: MapItem, StaticObject, NPC, Trigger, Lock, Id (or the line's own first
    field, kept as raw). x, y: pixels (MapItem/StaticObject/NPC) or 1-based tiles (Trigger/Lock/Id). An Id line names
    its tile (name): a place scripts and quests can use instead of coordinates."""

    def __init__(self, kind, name="", x=0, y=0, qty="1", opts="", script="", cond="", msg="", extra=None, raw=None):
        self.kind, self.name, self.x, self.y = kind, name, x, y
        self.qty, self.opts, self.script, self.cond, self.msg = qty, opts, script, cond, msg
        self.extra = list(extra or [])      # fields after the ones we know, kept
        self.raw = raw                      # a line we don't understand: written back exactly

    @classmethod
    def parse(cls, line):
        f = line.split("\t")
        kind = f[0].strip()
        num = lambda s: int(float(s)) if re.fullmatch(r"\s*-?\d+(\.\d+)?\s*", s or "") else 0
        try:
            if kind == "MapItem":
                return cls(kind, f[1], num(f[2]), num(f[3]), qty=(f[4].strip() if len(f) > 4 else "1") or "1",
                           opts=f[5].strip() if len(f) > 5 else "", extra=f[6:])
            if kind == "StaticObject":
                return cls(kind, f[1], num(f[2]), num(f[3]), opts=f[4].strip() if len(f) > 4 else "", extra=f[5:])
            if kind in ("NPC", "GoodNPC", "BadNPC"):
                opts = f[4].strip() if len(f) > 4 else ""
                if kind != "NPC" and "attitude=" not in opts.lower():
                    opts = ("Attitude=%s %s" % ("Good" if kind == "GoodNPC" else "Bad", opts)).strip()
                return cls("NPC", f[1], num(f[2]), num(f[3]), opts=opts, extra=f[5:])
            if kind == "Trigger":
                return cls(kind, x=num(f[2]), y=num(f[3]), script=f[1], extra=f[4:])
            if kind == "Lock":
                return cls(kind, x=num(f[1]), y=num(f[2]), cond=f[3] if len(f) > 3 else "",
                           msg=f[4] if len(f) > 4 else "", extra=f[5:])
            if kind == "Id":
                return cls(kind, f[1].strip(), num(f[2]), num(f[3]), extra=f[4:])
        except (IndexError, ValueError):
            pass
        return cls(kind, raw=line)

    def line(self):
        if self.raw is not None:
            return self.raw
        k = self.kind
        if k == "MapItem":
            f = [k, self.name, str(self.x), str(self.y), str(self.qty or "1")] + ([self.opts] if self.opts or self.extra
                                                                                  else [])
        elif k == "StaticObject":
            f = [k, self.name, str(self.x), str(self.y)] + ([self.opts] if self.opts or self.extra else [])
        elif k == "NPC":
            f = [k, self.name, str(self.x), str(self.y), self.opts]
        elif k == "Trigger":
            f = [k, self.script, str(self.x), str(self.y)]
        elif k == "Id":
            f = [k, self.name, str(self.x), str(self.y)]
        else:
            f = [k, str(self.x), str(self.y), self.cond, self.msg]
        return "\t".join(f + self.extra)

    def copy(self):
        e = Entity(self.kind)
        e.__dict__.update(self.__dict__)
        e.extra = list(self.extra)
        return e

    # --- NPC options (Key=Value words)
    def opt(self, key, default=""):
        for w in self.opts.split():
            if "=" in w and w.split("=", 1)[0].lower() == key.lower():
                return w.split("=", 1)[1]
        return default

    def set_opt(self, key, value):
        words = self.opts.split()
        out, done = [], False
        for w in words:
            if "=" in w and w.split("=", 1)[0].lower() == key.lower():
                if value not in (None, "") and not done:
                    out.append("%s=%s" % (key, value))
                done = True
            else:
                out.append(w)
        if not done and value not in (None, ""):
            out.append("%s=%s" % (key, value))
        self.opts = " ".join(out)

    @property
    def on_tile(self):
        return self.kind in ("Trigger", "Lock", "Id")


class MapDoc:
    def __init__(self, project, name):
        self.project, self.name = project, name
        self.path = project.map_path(name)
        self.load()

    def load(self):
        W, H = self.project.map_w, self.project.map_h
        lines = read_text_lines(self.path) if os.path.exists(self.path) else []
        self.exists = os.path.exists(self.path)
        rows = lines[:H]
        self.cells = []
        for y in range(H):
            parts = rows[y].split(":") if y < len(rows) else []
            self.cells.append([Cell(parts[x]) if x < len(parts) else Cell("Black001") for x in range(W)])
        # (blank and unknown lines are kept as raw entries, written back where they were)
        self.entities = [Entity.parse(l) if l.strip() else Entity("", raw=l) for l in lines[H:]]
        self.stamp = mtime(self.path)

    def placed(self):
        """The entities the editor works with (not the raw lines)."""
        return [e for e in self.entities if e.raw is None]

    def fill(self, tile):
        self.cells = [[Cell(tile) for _ in range(self.project.map_w)] for _ in range(self.project.map_h)]
        self.entities = []

    def lines(self):
        return [":".join(c.text() for c in row) for row in self.cells] + [e.line() for e in self.entities]

    def snapshot(self):
        return "\n".join(self.lines())

    def restore(self, snap):
        W, H = self.project.map_w, self.project.map_h
        lines = snap.split("\n")
        self.cells = [[Cell(t) for t in lines[y].split(":")] for y in range(H)]
        self.entities = [Entity.parse(l) if l.strip() else Entity("", raw=l) for l in lines[H:]]

    def save(self):
        written = write_text_lines(self.path, self.lines())
        self.exists = True
        self.stamp = mtime(self.path)
        return written


def parse_map_name(name):
    """(x, y, z) of a map's name. The homestead's starting land isn't in the world: it's drawn as level 1000 (the
    homes themselves are 0,0,1001 up, made by the server), so it has no neighbours."""
    if name == HOMESTEAD_MAP:
        return 0, 0, 1000
    try:
        x, y, z = (int(v) for v in name.split(","))
        return x, y, z
    except ValueError:
        return None


# =================================================================================================================
# Scripts
# =================================================================================================================
class ScriptLine:
    """A script line: a command with its arguments, or a // comment (comments aren't numbered)."""
    __slots__ = ("command", "args", "comment")

    def __init__(self, command="", args=None, comment=None):
        self.command, self.args, self.comment = command, list(args or []), comment

    @property
    def is_comment(self):
        return self.comment is not None

    def copy(self):
        return ScriptLine(self.command, list(self.args), self.comment)

    def normalise(self):
        """After an edit: no blank arguments at the end, a blank one in the middle written as a space (as the old
        editor did, so the tabs don't run together)."""
        args = [a if a.strip() else "" for a in self.args]
        while args and args[-1] == "":
            args.pop()
        self.args = [a if a else " " for a in args]


class ScriptDoc:
    def __init__(self, project, name):
        self.project, self.name = project, name
        self.path = project.script_path(name)
        self.load()

    def load(self):
        self.exists = os.path.exists(self.path)
        self.lines = []
        for l in (read_text_lines(self.path) if self.exists else []):
            s = l.strip()
            if not s:
                continue
            if s.startswith("//"):
                self.lines.append(ScriptLine(comment=s[2:]))           # (exactly what follows the //)
                continue
            f = l.split("\t")
            self.lines.append(ScriptLine(f[1].strip() if len(f) > 1 else "", f[2:]))
        self.stamp = mtime(self.path)

    def commands(self):
        return [l for l in self.lines if not l.is_comment]

    def text_lines(self):
        out, n = [], 0
        for l in self.lines:
            if l.is_comment:
                out.append("//" + l.comment)
                continue
            n += 1
            out.append("\t".join(["%02d" % n, l.command] + list(l.args)))
        return out

    def snapshot(self):
        return [(l.command, list(l.args), l.comment) for l in self.lines]

    def restore(self, snap):
        self.lines = [ScriptLine(c, a, m) for c, a, m in snap]

    def save(self):
        written = write_text_lines(self.path, self.text_lines())
        self.exists = True
        self.stamp = mtime(self.path)
        return written


# =================================================================================================================
# The project
# =================================================================================================================
HOMESTEAD_MAP = "Homestead"    # the land a new homestead starts as (data\Homestead.txt), on a level of its own


class Project:
    def __init__(self, root):
        self.root = root
        self.config = IniDoc(self.p("data", "Config.ini"))
        self.map_w = int(self.config.get("Interface", "Map.X.Tiles", "25") or 25)
        self.map_h = int(self.config.get("Interface", "Map.Y.Tiles", "21") or 21)
        self.tile_w = self.tile_h = 32
        self.tiles_ini = IniDoc(self.p("data", "Tiles.ini"))
        self.entities_ini = IniDoc(self.p("data", "Entities.ini"))
        self.racks_ini = IniDoc(self.p("data", "ItemRacks.ini"))
        self.spells_ini = IniDoc(self.p("data", "Spells.ini"))
        self.quests_ini = IniDoc(self.p("data", "Quests.ini"))
        self.buildables_ini = IniDoc(self.p("data", "Buildables.ini"))
        self.crops_ini = IniDoc(self.p("data", "Crops.ini"))
        self._sprites = {}
        self._lists = {}
        self._index = None
        self.minimap_colours = self.load_minimap_colours()
        b = self.sprite("Tiles", "Black001")
        if b is not None:
            self.tile_w, self.tile_h = b.size

    def p(self, *parts):
        return os.path.join(self.root, *parts)

    def map_path(self, name):
        if name == HOMESTEAD_MAP:
            return self.p("data", self.config.get("Homestead", "Template", "Homestead.txt") or "Homestead.txt")
        return self.p("maps", name + ".txt")

    def script_path(self, name):
        return self.p("data", "Scripts", name + ".txt")

    @property
    def skills(self):
        return [s.strip() for s in self.config.get("Skills", "List", "").split(",") if s.strip()]

    # --- lists (cached; refresh() after files are added or removed)
    def refresh(self, *which):
        for k in (which or list(self._lists)):
            self._lists.pop(k, None)
            if k == "tiles":
                self._lists.pop("tiles_shown", None)
            if k == "entities":
                self._lists.pop("entity_set", None)
        self._index = None

    def _files(self, key, folder, ext):
        if key not in self._lists:
            d = self.p(*folder)
            exts = ext if isinstance(ext, tuple) else (ext,)
            names = {os.path.splitext(f)[0] for f in os.listdir(d)
                     if os.path.splitext(f)[1].lower() in exts} if os.path.isdir(d) else set()
            self._lists[key] = sorted(names, key=str.lower)
        return self._lists[key]

    def tiles(self):
        """Every tile (not the extra pictures of a tile drawn from several: <Name>1..N for Tiles.ini Anim.Frames)."""
        if "tiles_shown" not in self._lists:
            names = self._files("tiles", ("sprites", "Tiles"), (".png", ".bmp"))
            self._lists["tiles_shown"] = [t for t in names if not self.is_tile_frame(t)]
        return self._lists["tiles_shown"]

    def is_tile_frame(self, name):
        """One of a tile's animation pictures (Water0011 is frame 1 of Water001 with Anim.Frames), not a tile."""
        if self.tiles_ini.has_section(name):
            return False
        for i in range(len(name) - 1, 0, -1):
            if not name[i:].isdigit():
                break
            if self.tiles_ini.get(name[:i], "Anim.Frames", "") not in ("", "0", "1"):
                return True
        return False

    def is_under(self, name):
        """Tiles.ini Layer=Under: a rug, flat on the floor; decor can stand on it (painted with the Decor layer)."""
        return bool(name) and name.lower() in self.layer_tiles("under")

    def is_decor(self, name):
        """Tiles.ini Layer=Decor: a see-through tile for the Decor layer (over any ground tile), not a ground tile."""
        return name.lower() in self.decor_tiles()

    def decor_tiles(self):
        """The (lower-case) names of every Layer=Decor tile, read in one pass (again whenever Tiles.ini changes)."""
        return self.layer_tiles("decor")

    def layer_tiles(self, layer):
        """The (lower-case) names of every tile with Layer=<layer> (decor, under), read again when Tiles.ini changes."""
        lines = self.tiles_ini.lines
        key = hash(tuple(lines))
        if getattr(self, "_layers_key", None) != key:
            out, sec = {}, None
            for l in lines:
                s = l.strip()
                if s.startswith("[") and "]" in s:
                    sec = s[1:s.index("]")].strip().lower()
                elif sec and "=" in s and not s.startswith(";"):
                    k, v = s.split("=", 1)
                    if k.strip().lower() == "layer":
                        out.setdefault(v.strip().lower(), set()).add(sec)
            self._layers_key, self._layers = key, out
        return self._layers.get(layer, set())

    def tile_sets(self):
        """data\\TileSets.ini: [(set, title, columns, [tile names row by row, "" = a gap])], read again when it
        changes. A set is tiles that go together (a roof, a rug, a fence); each tile's Tiles.ini Piece= says which
        piece it is."""
        path = self.p("data", "TileSets.ini")
        stamp = mtime(path)
        if getattr(self, "_sets_stamp", None) != stamp:
            doc = IniDoc(path) if os.path.exists(path) else None
            out = []
            for sec in (doc.sections() if doc else []):
                names = [n.strip() for n in doc.get(sec, "Tiles", "").split(",")]
                try:
                    cols = max(1, int(doc.get(sec, "Columns", "") or 0) or len(names))
                except ValueError:
                    cols = len(names)
                if any(names):
                    out.append((sec, doc.get(sec, "Title", "") or sec.replace("_", " "), cols, names))
            self._sets_stamp, self._sets = stamp, out
        return self._sets

    def tile_set_of(self, name):
        """(set, title, columns, names) of the first set name is in, or None."""
        low = name.lower()
        for st in self.tile_sets():
            if any(n.lower() == low for n in st[3]):
                return st
        return None

    def entities(self):
        return self._files("entities", ("sprites", "Entities"), (".png", ".bmp"))

    def scripts(self):
        return self._files("scripts", ("data", "Scripts"), ".txt")

    def sounds(self):
        return sorted(set(self._files("sounds", ("sounds",), ".wav")) |
                      {s + ".mid" for s in self._files("midis", ("sounds",), ".mid")}, key=str.lower)

    def maps(self):
        if "maps" not in self._lists:
            d = self.p("maps")
            names = [f[:-4] for f in os.listdir(d) if f.endswith(".txt") and parse_map_name(f[:-4])]
            if os.path.exists(self.map_path(HOMESTEAD_MAP)) and HOMESTEAD_MAP not in names:
                names.append(HOMESTEAD_MAP)
            self._lists["maps"] = sorted(names, key=lambda n: (parse_map_name(n)[2], parse_map_name(n)[1],
                                                               parse_map_name(n)[0]))
        return self._lists["maps"]

    # --- named places (Id lines and Id= options): what scripts and quests use instead of coordinates
    def places(self):
        """{UPPER ID: (ID, map, tile x, tile y, what)} from the saved maps; what: "tile" or the thing's name."""
        out = {}
        for m in self.maps():
            try:
                lines = read_text_lines(self.map_path(m))[self.map_h:]
            except OSError:
                continue
            for l in lines:
                e = Entity.parse(l)
                if e.kind == "Id" and e.name:
                    out.setdefault(e.name.upper(), (e.name, m, e.x, e.y, "tile"))
                elif e.kind in ("MapItem", "StaticObject", "NPC") and e.opt("Id"):
                    out.setdefault(e.opt("Id").upper(), (e.opt("Id"), m, (e.x + 16) // 32 + 1, (e.y + 28) // 32 + 1,
                                                         e.name))
        return out

    def place_uses(self, name):
        """[("script", name) / ("quest", name)]: what names the place (a script's coordinates, a quest's marker)."""
        from . import scriptlang as SL
        types = SL.COMMANDS                                  # command -> [argument types]
        out, key = [], name.upper()
        for s in self.scripts():
            try:
                lines = read_text_lines(self.script_path(s))
            except OSError:
                continue
            if any(self._names_place(l, key, types) for l in lines):
                out.append(("script", s))
        for q in self.quests_ini.sections():
            for k, v in self.quests_ini.items(q):
                if k.lower().startswith("marker") and key in [x.strip().upper() for x in v.split(";")]:
                    out.append(("quest", q))
                    break
        return out

    @staticmethod
    def _names_place(line, key, types):
        f = line.split("	")
        if len(f) < 3 or line.lstrip().startswith("//"):
            return False
        args = types.get(f[1].strip())
        for i, v in enumerate(f[2:]):
            t = args[i].strip() if args and i < len(args) else ""
            if args and t not in COORD_TYPES:
                continue
            if v.strip().upper() == key or (("TILE COORDINATES" in t) and key in v.upper().split()):
                return True
        return False

    def rename_place_uses(self, old, new):
        """Every script argument and quest marker naming place old now names new. Returns how many files changed."""
        from . import scriptlang as SL
        types = SL.COMMANDS                                  # command -> [argument types]
        n, key = 0, old.upper()
        for kind, what in self.place_uses(old):
            if kind == "script":
                path = self.script_path(what)
                lines = read_text_lines(path)
                for j, l in enumerate(lines):
                    if not self._names_place(l, key, types):
                        continue
                    f = l.split("	")
                    args = types.get(f[1].strip())
                    for i in range(2, len(f)):
                        t = args[i - 2].strip() if args and i - 2 < len(args) else ""
                        if args and t not in COORD_TYPES:
                            continue
                        f[i] = " ".join(new if w.upper() == key else w for w in f[i].split(" "))
                    lines[j] = "	".join(f)
                n += write_text_lines(path, lines)
            else:
                for k, v in list(self.quests_ini.items(what)):
                    if k.lower().startswith("marker"):
                        nv = ";".join(new if x.strip().upper() == key else x for x in v.split(";"))
                        if nv != v:
                            self.quests_ini.set(what, k, nv)
                self.quests_ini.save()
                n += 1
        return n

    def entity_type(self, name):
        if self.is_decor_object(name):
            return "StaticObject"
        t = self.entities_ini.get(name, "Type", "")
        return t if t in ENTITY_TYPES else ("NPC" if t in ("GoodNPC", "BadNPC") else ("MapItem" if not t else t))

    def is_frame(self, name):
        """An animation frame (<Name>1..N of an entity with Anim.Frames), not an entity of its own."""
        if self.entities_ini.has_section(name):
            return False
        for i in range(len(name) - 1, 0, -1):           # Boat0011 is frame 1 of Boat001
            if not name[i:].isdigit():
                break
            if self.entities_ini.get(name[:i], "Anim.Frames", "") not in ("", "0"):
                return True
        return False

    def placeable(self):
        """What can go on the Entities layer: the entities, and the decor tiles (placed as objects: anywhere, drawn in
        front of or behind the player, with an Id for scripts)."""
        return sorted([e for e in self.entities() if not self.is_frame(e)] +
                      [t for t in self.tiles() if self.is_decor_object(t)], key=str.lower)

    def is_decor_object(self, name):
        """A decor tile used as an object: no entity of that name, so its picture and data are the tile's."""
        if "entity_set" not in self._lists:
            self._lists["entity_set"] = set(self.entities())
        return self.is_decor(name) and name not in self._lists["entity_set"] and not self.entities_ini.has_section(name)

    def items(self):
        """The entities that are items (MapItem: the Type, or no Type at all)."""
        return [e for e in self.placeable() if self.entity_type(e) == "MapItem"]

    def npcs(self):
        return [e for e in self.entities() if self.entity_type(e) == "NPC"]

    def attributes(self):
        """Attribute names used by scripts and quests."""
        if "attributes" not in self._lists:
            names = set()
            for q in self.quests_ini.sections():
                a = self.quests_ini.get(q, "Attribute", "")
                if a:
                    names.add(a)
            for s in self.scripts():
                try:
                    for l in read_text_lines(self.script_path(s)):
                        f = l.split("\t")
                        if len(f) > 2 and f[1] in ("Update.Attribute",):
                            names.add(f[2].strip())
                        if len(f) > 3 and f[1] == "Get.Value" and f[2].strip().upper() == "ATTRIBUTE":
                            names.add(f[3].strip())
                        names.update(re.findall(r"\$Attr\.([A-Za-z0-9_.]+?)(?=[<>=! ]|$)", l))
                except OSError:
                    pass
            self._lists["attributes"] = sorted((n for n in names if n), key=str.lower)
        return self._lists["attributes"]

    def verbs(self):
        """Every verb the game knows of: Use.Words in Tiles.ini and Entities.ini, Gathering.ini and the built-in ones."""
        if "verbs" not in self._lists:
            vs = {"Pickup", "Drop", "Examine", "Eat", "Drink", "Talk to", "Attack", "Walk here", "Use", "Open", "Unlock",
                  "Climb Up", "Climb Down", "Cast", "Read", "Travel", "Fish", "Chop", "Mine", "Pick", "Harvest",
                  "Sleep"}
            for ini in (self.tiles_ini, self.entities_ini):
                for sec in ini.sections():
                    for w in ini.get(sec, "Use.Words", "").split(","):
                        if w.strip():
                            vs.add(w.strip())
            g = IniDoc(self.p("data", "Gathering.ini"))
            for sec in g.sections():
                if g.get(sec, "Verb"):
                    vs.add(g.get(sec, "Verb"))
            self._lists["verbs"] = sorted(vs, key=str.lower)
        return self._lists["verbs"]

    # --- sprites (PIL images with transparency)
    def sprite(self, kind, name):
        key = (kind, name)
        if key not in self._sprites and kind == "Entities" and self.is_decor_object(name):
            self._sprites[key] = self.sprite("Tiles", name)        # (a decor tile placed as an object)
        if key not in self._sprites:
            folder = ("dev", "Sprites") if kind == "Dev" else ("sprites", kind)
            path = self.p(*folder, name + ".png")       # a PNG (with its transparency), or an old two-half BMP
            if not os.path.exists(path):
                path = self.p(*folder, name + ".bmp")
            img = None
            if os.path.exists(path):
                try:
                    if path.endswith(".png"):
                        img = Image.open(path).convert("RGBA")
                        self._sprites[key] = img
                        return img
                    im = Image.open(path).convert("RGB")
                    w, h = im.size
                    if h >= 2 and h % 2 == 0:
                        mask = im.crop((0, 0, w, h // 2)).convert("L")
                        pic = im.crop((0, h // 2, w, h))
                        alpha = mask.point(lambda v: 255 if v < 128 else 0)
                        pic.putalpha(alpha)
                        img = pic
                    else:
                        img = im.convert("RGBA")
                except OSError:
                    img = None
            self._sprites[key] = img
        return self._sprites[key]

    def forget_sprite(self, kind, name):
        self._sprites.pop((kind, name), None)

    # --- minimap colours (dev\Minimap Colours.txt: Tile<TAB>R G B or a colour name)
    def load_minimap_colours(self):
        path = self.p("dev", "Minimap Colours.txt")
        out = {}
        if os.path.exists(path):
            for l in read_text_lines(path):
                if "\t" in l:
                    k, v = l.split("\t", 1)
                    out[k.strip()] = v.strip()
        return out

    def save_minimap_colours(self):
        path = self.p("dev", "Minimap Colours.txt")
        lines = ["%s\t%s" % (k, v) for k, v in sorted(self.minimap_colours.items(), key=lambda kv: kv[0].lower())]
        return write_text_lines(path, lines)

    # --- where things are used
    def index(self):
        """{("map"|"script"|...): ...} built from every map and script: what places, triggers and mentions what."""
        if self._index is None:
            idx = {"tile": {}, "entity": {}, "script_trigger": {}, "script_mention": {}, "rack": {}, "item_rack": {},
                   "drops": {}}
            W, H = self.map_w, self.map_h
            for m in self.maps():
                try:
                    lines = read_text_lines(self.map_path(m))
                except OSError:
                    continue
                for y, row in enumerate(lines[:H]):
                    for x, c in enumerate(row.split(":")):
                        cell = Cell(c)
                        for t in (cell.tile, cell.decor, cell.roof, cell.infront):
                            if t:
                                idx["tile"].setdefault(t, {}).setdefault(m, (x + 1, y + 1))
                for l in lines[H:]:
                    e = Entity.parse(l)
                    if e.raw is not None:
                        continue
                    if e.kind == "Trigger":
                        idx["script_trigger"].setdefault(e.script, []).append((m, e.x, e.y))
                    elif e.kind != "Lock":
                        idx["entity"].setdefault(e.name, {}).setdefault(m, (e.x // self.tile_w + 1, e.y // self.tile_h + 1))
            names = set(self.entities())
            for s in self.scripts():
                try:
                    text = "\n".join(read_text_lines(self.script_path(s)))
                except OSError:
                    continue
                for word in set(re.findall(r"[A-Za-z][A-Za-z0-9_()']*", text)):
                    if word in names:
                        idx["script_mention"].setdefault(word, []).append(s)
                for m in re.finditer(r"Display\.Item\.Rack\t[^\t]*\t[^\t]*\t([^\t\r\n]+)", text):
                    idx["rack"].setdefault(m.group(1).strip(), []).append(s)
            for rack in self.racks_ini.sections():
                for k, v in self.racks_ini.items(rack):
                    if k.lower().startswith("item"):
                        parts = v.split(",")
                        for w in [parts[0]] + (parts[1].split()[::2] if len(parts) > 1 and
                                               rack.upper().startswith("CRAFT") else []):
                            if w.strip():
                                idx["item_rack"].setdefault(w.strip(), []).append(rack)
            for npc in self.entities_ini.sections():
                for d in self.entities_ini.get(npc, "Drops", "").split():
                    idx["drops"].setdefault(d.split(",")[0], []).append(npc)
            self._index = idx
        return self._index
