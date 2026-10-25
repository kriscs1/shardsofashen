"""Shared helpers for the Dragon Sword v2 data migration and validation scripts.

Paths are resolved relative to this file, so the scripts can be run from anywhere:
    python -I "dev\\migrate\\migrate.py"
    python -I "dev\\migrate\\validate.py"
"""
import os
import re
import struct

HERE = os.path.dirname(os.path.abspath(__file__))
NEW = os.path.normpath(os.path.join(HERE, "..", ".."))            # ...\New (converted)
OLD = os.path.normpath(os.path.join(NEW, "..", "Previous (to convert)"))

ENC = "cp1252"   # ANSI, what Liberty BASIC and the *PrivateProfileString*A APIs expect
MAP_W, MAP_H = 25, 21
TILE_W, TILE_H = 32, 32
WALK_RES = 7


def p(*parts):
    return os.path.join(NEW, *parts)


def o(*parts):
    return os.path.join(OLD, *parts)


# ---------------------------------------------------------------- file io
def read_lines(path):
    """Read a text file as a list of lines without line endings."""
    with open(path, "rb") as f:
        data = f.read()
    if data.startswith(b"\xef\xbb\xbf"):
        data = data[3:]
    text = data.decode(ENC, errors="replace")
    return text.replace("\r\n", "\n").replace("\r", "\n").split("\n")


def write_lines(path, lines):
    """Write lines as ANSI with CRLF endings (every line, including the last, ends in CRLF).
    Only writes when the content actually changes (keeps OneDrive quiet and the run idempotent)."""
    data = "".join(l + "\r\n" for l in lines).encode(ENC)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if os.path.exists(path):
        with open(path, "rb") as f:
            if f.read() == data:
                return False
    with open(path, "wb") as f:
        f.write(data)
    return True


def strip_trailing_blank(lines):
    lines = list(lines)
    while lines and lines[-1].strip() == "":
        lines.pop()
    return lines


# ---------------------------------------------------------------- sprites / names
def sprite_names(kind):
    folder = p("sprites", kind)
    return sorted({f[:-4] for f in os.listdir(folder) if f.lower().endswith((".png", ".bmp"))})


def _key(name):
    return name.replace("_", "").replace(" ", "").lower()


# Explicit renames that the generic "ignore underscores and case" rule can't find.
EXPLICIT_RENAMES = {
    "GoldCoins": "Gold_Coin(s)",
    "GoldCoin": "Gold_Coin(s)",
    "PlaceHolder": "Placeholder",
    "Picaxe": "Pickaxe",
}


class Renamer:
    """Maps old CamelCase names to the sprite names in sprites\\Tiles and sprites\\Entities."""

    def __init__(self):
        self.tiles = sprite_names("Tiles")
        self.entities = sprite_names("Entities")
        self.by_key = {}
        for n in self.tiles + self.entities:
            self.by_key.setdefault(_key(n), n)

    def name(self, old):
        if old in self.tiles or old in self.entities:
            return old
        if old in EXPLICIT_RENAMES:
            return EXPLICIT_RENAMES[old]
        return self.by_key.get(_key(old), old)

    def known(self, name):
        return name in self.tiles or name in self.entities


# ---------------------------------------------------------------- your edits survive a rebuild
class Generated:
    """What the builders last wrote (dev\\migrate\\generated.json), so a rebuild can tell your edits from its own.

    Three levels: an ini key (Ini.set), an ini section (Ini.replace_section: shop and crafting racks, spells, quests)
    and a whole file (write_generated: maps, scripts). On a rebuild a value is only updated when it still matches what
    the builder wrote last time (or the builder never wrote it); if it's different you changed it in an editor and it is
    kept, and if it's gone you deleted it and it stays deleted. Kept edits are listed at the end of the build.
    Only on while build_world.py runs (enable()); everything else that uses Ini is untouched."""

    PATH = os.path.join(HERE, "generated.json")

    def __init__(self):
        self.on = False
        self.data = None
        self.dirty = False
        self.kept = []

    def enable(self):
        import json
        self.on = True
        if self.data is None:
            self.data = {"keys": {}, "sections": {}, "files": {}}
            if os.path.exists(self.PATH):
                with open(self.PATH, encoding="utf-8") as f:
                    self.data.update(json.load(f))

    def save(self):
        import json
        if self.on and self.dirty:
            with open(self.PATH, "w", encoding="utf-8", newline="\n") as f:
                json.dump(self.data, f, indent=0, sort_keys=True)
            self.dirty = False

    @staticmethod
    def rel(path):
        return os.path.relpath(os.path.abspath(path), NEW).lower()

    def _allow(self, table, file, item, current, new, what):
        """True if the builder may write new over current; records new as what it wrote."""
        rec = self.data[table].setdefault(file, {}).get(item)
        if rec is not None and current != rec and current != new:
            self.kept.append(what + (" (deleted)" if current is None else ""))
            return False
        if rec != new:
            self.data[table][file][item] = new
            self.dirty = True
        return True

    def key(self, path, sec, key, current, new):
        return self._allow("keys", self.rel(path), sec.lower() + "|" + key.lower(), current, new,
                           "%s [%s] %s" % (os.path.basename(path), sec, key))

    def section(self, path, sec, current, new):
        return self._allow("sections", self.rel(path), sec.lower(), current, new, "%s [%s]" % (os.path.basename(path), sec))

    def file(self, path, current, new):
        import hashlib
        h = lambda b: None if b is None else hashlib.sha1(b).hexdigest()
        return self._allow("files", "all", self.rel(path), h(current), h(new), os.path.relpath(path, NEW))

    def untouched(self, path):
        """Did a builder write path last, and is it still as written (not edited since)?"""
        import hashlib
        rec = self.data["files"].get("all", {}).get(self.rel(path))
        if rec is None or not os.path.exists(path):
            return False
        with open(path, "rb") as f:
            return hashlib.sha1(f.read()).hexdigest() == rec

    def forget(self, path):
        self.data["files"].get("all", {}).pop(self.rel(path), None)
        self.dirty = True

    def report(self):
        if self.kept:
            print("Kept %d of your edits (changed or deleted since the last build, so not overwritten):" % len(self.kept))
            for k in self.kept[:40]:
                print("   ", k)
            if len(self.kept) > 40:
                print("    ...and %d more" % (len(self.kept) - 40))


GEN = Generated()


def write_generated(path, lines):
    """write_lines for files a builder makes whole (maps, scripts), unless you've edited or deleted it since."""
    data = "".join(l + "\r\n" for l in lines).encode(ENC)
    if GEN.on:
        current = None
        if os.path.exists(path):
            with open(path, "rb") as f:
                current = f.read()
        if not GEN.file(path, current, data):
            return False
    return write_lines(path, lines)


# ---------------------------------------------------------------- ini files
class Ini:
    """Order- and case-preserving ini model compatible with GetPrivateProfileString.
    header: lines before the first section (comments). sections: list of [name, [(key, value) | (None, rawline)]]"""

    def __init__(self, path=None):
        self.header = []
        self.sections = []
        self.path = path              # GEN (your edits survive a rebuild) knows the file by it
        if path and os.path.exists(path):
            cur = None
            for line in read_lines(path):
                s = line.strip()
                if s.startswith("[") and s.endswith("]") and not s.startswith(";"):
                    cur = [s[1:-1].strip(), []]
                    self.sections.append(cur)
                elif cur is None:
                    self.header.append(line.rstrip())
                elif s == "":
                    continue
                elif s.startswith(";") or "=" not in s:
                    cur[1].append((None, line.rstrip()))
                else:
                    k, v = s.split("=", 1)
                    cur[1].append((k.strip(), v.strip()))
            self.header = strip_trailing_blank(self.header)

    def section(self, name, create=False):
        for s in self.sections:
            if s[0].lower() == name.lower():
                return s
        if create:
            s = [name, []]
            self.sections.append(s)
            return s
        return None

    def get(self, sec, key, default=None):
        s = self.section(sec)
        if s:
            for k, v in s[1]:
                if k is not None and k.lower() == key.lower():
                    return v
        return default

    def has(self, sec, key):
        return self.get(sec, key) is not None

    def set(self, sec, key, value, overwrite=True):
        if GEN.on and self.path and overwrite and not GEN.key(self.path, sec, key, self.get(sec, key), str(value)):
            return                    # you changed (or deleted) it since the last build: kept
        s = self.section(sec, create=True)
        for i, (k, v) in enumerate(s[1]):
            if k is not None and k.lower() == key.lower():
                if overwrite:
                    s[1][i] = (k, str(value))
                return
        s[1].append((key, str(value)))

    def replace_section(self, name, items):
        """Sets a whole section to items [(key, value)] (a shop or crafting rack, a spell, a quest), unless you've
        changed or deleted that section since the last build (GEN). Returns True if it was set."""
        new = "\n".join("%s=%s" % (k, v) for k, v in items)
        s = self.section(name)
        if GEN.on and self.path:
            current = None if s is None else "\n".join("%s=%s" % (k, v) for k, v in s[1] if k is not None)
            if not GEN.section(self.path, name, current, new):
                return False
        s = self.section(name, create=True)
        s[1] = [(k, str(v)) for k, v in items]
        return True

    def remove(self, sec, key):
        s = self.section(sec)
        if s:
            s[1] = [(k, v) for k, v in s[1] if not (k is not None and k.lower() == key.lower())]

    def rename_key(self, sec, old, new):
        s = self.section(sec)
        if not s:
            return
        if self.has(sec, new):
            self.remove(sec, old)
            return
        s[1] = [((new if (k is not None and k.lower() == old.lower()) else k), v) for k, v in s[1]]

    def lines(self):
        out = list(self.header)
        if out:
            out.append("")
        for name, items in self.sections:
            out.append("[%s]" % name)
            for k, v in items:
                out.append(v if k is None else "%s=%s" % (k, v))
            out.append("")
        return out

    def save(self, path):
        return write_lines(path, strip_trailing_blank(self.lines()))


# ---------------------------------------------------------------- sprite files
# Sprites are PNGs: a picture with transparency (or a plain picture: the interface panels, the textures). The builders
# still work on the old Liberty BASIC layout in memory (a picture twice as high: the top half the mask, black = drawn,
# white = see-through, the bottom half the picture), so read_bmp gives a PNG in that layout and write_sprite takes it.
PLAIN = {"ChatBar", "InfoBox", "ResponseBox", "SideBarBorder", "StatBox", "Forest_Canopy", "World"}


def png_path(path):
    """...\\Name.bmp (or .png) -> ...\\Name.png"""
    return path[:-4] + ".png" if path.lower().endswith((".bmp", ".png")) else path + ".png"


def sprite_exists(path):
    """A sprite file given as ...\\Name.bmp or .png: there as a PNG (or an old BMP)."""
    return os.path.exists(png_path(path)) or os.path.exists(path[:-4] + ".bmp")


def read_png(path):
    """(width, height, rows) of a PNG: in the mask layout (height twice the picture's) if it has transparency."""
    from PIL import Image
    im = Image.open(path)
    has_alpha = im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info)
    im = im.convert("RGBA" if has_alpha else "RGB")
    w, h = im.size
    px = list(im.getdata())
    pic = [[c[:3] for c in px[y * w:(y + 1) * w]] for y in range(h)]
    if not has_alpha:
        return w, h, pic
    mask = [[(0, 0, 0) if c[3] >= 128 else (255, 255, 255) for c in px[y * w:(y + 1) * w]] for y in range(h)]
    return w, 2 * h, mask + pic


def write_sprite(path, rows, plain=False):
    """Writes ...\\Name.png from rows in the mask layout (or a plain picture), only if it changed (an old
    ...\\Name.bmp beside it is removed). Returns True when written."""
    from PIL import Image
    out = png_path(path)
    w = len(rows[0])
    if plain:
        im = Image.new("RGB", (w, len(rows)))
        im.putdata([tuple(int(v) for v in c[:3]) for r in rows for c in r])
    else:
        h = len(rows) // 2
        im = Image.new("RGBA", (w, h))
        im.putdata([tuple(int(v) for v in rows[h + y][x][:3]) + ((255,) if sum(rows[y][x][:3]) < 384 else (0,))
                    for y in range(h) for x in range(w)])
    return write_image(out, im)


def write_image(path, im, decor=False):
    """Saves a PIL image as path (a .png) only if its pixels changed; removes an old .bmp of the same name. Not a tile
    split into decor (DECOR_MAP): that stays as the split made it, unless this is its decor picture (decor=True: drawn
    see-through by a builder, decor_sets.py)."""
    if tile_sprite_name(path) in DECOR_MAP and not decor:
        return False
    import io
    buf = io.BytesIO()
    im.save(buf, "PNG", optimize=True)
    blob = buf.getvalue()
    old = path[:-4] + ".bmp"
    if os.path.exists(old):
        os.remove(old)
    if os.path.exists(path):
        with open(path, "rb") as f:
            if f.read() == blob:
                return False
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(blob)
    return True


# ---------------------------------------------------------------- decor (the editor's "Split props off their floors")
# A tile split into decor (Tiles.ini Layer=Decor) is see-through now, and a copy drawn on another floor may be gone.
# decor_map.json says what each old tile became: {tile: [floor, decor]}. The builders still draw with the old opaque
# pictures (kept in dev\Archive\Decor split <date>\sprites\Tiles): reading one gets the old picture, writing one is
# skipped (the decor stays as it is), and a map cell they make with one becomes Floor+Decor(Name) (decor_cells).
def load_decor_map():
    import json
    path = os.path.join(HERE, "decor_map.json")
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return {k: tuple(v) for k, v in json.load(f).items()}


DECOR_MAP = load_decor_map()


def tile_sprite_name(path):
    """The tile's name if path is a sprite in sprites\Tiles, else None."""
    folder, f = os.path.split(os.path.normpath(path))
    if os.path.normcase(folder) != os.path.normcase(os.path.join(NEW, "sprites", "Tiles")):
        return None
    return os.path.splitext(f)[0]


def decor_archive_path(name):
    """The old opaque picture of a tile split into decor (the newest archive copy), or None."""
    import glob
    found = sorted(glob.glob(os.path.join(NEW, "dev", "Archive", "Decor split *", "Sprites", "Tiles", name + ".png")))
    return found[-1] if found else None


def _decor_reverse():
    rev = {}
    for t, (f, d) in DECOR_MAP.items():
        if (f, d) not in rev or t == d:
            rev[(f, d)] = t
    return rev


DECOR_REVERSE = _decor_reverse()        # (floor, decor) -> the old tile the builders know it as
# a decor the builders put down that the maps get one of several of (decor_sets.PLANTS), by where it is
DECOR_VARIANTS = {"Potted_Plant001": ["Potted_Plant%03d" % n for n in range(1, 6)]}
VARIANT_OF = {v: k for k, vs in DECOR_VARIANTS.items() for v in vs}


def decor_variant(decor, x, y):
    vs = DECOR_VARIANTS.get(decor)
    import hashlib
    return vs[int(hashlib.md5(("%d,%d" % (x, y)).encode()).hexdigest(), 16) % len(vs)] if vs else decor


def built_cell(cell):
    """A map cell as the builders know it: Floor+Decor(Name) back to the old tile it was split from (the rest of the
    cell, its roof and so on, kept). Anything else as it is."""
    parts = cell.split("+")
    for i, part in enumerate(parts[1:], 1):
        if part.startswith("Decor(") and part.endswith(")"):
            d = part[6:-1]
            t = DECOR_REVERSE.get((parts[0], VARIANT_OF.get(d, d)))
            if t:
                return "+".join([t] + parts[1:i] + parts[i + 1:])
    return cell


def built_base(cell):
    """The ground tile of a cell as the builders know it (see built_cell)."""
    return built_cell(cell).split("+")[0]


def decor_cells(cells):
    """Cells (rows of map cell texts) with an old tile split into decor as their ground: Floor+Decor(Name)."""
    for y, row in enumerate(cells):
        for i, c in enumerate(row):
            base, rest = (c.split("+", 1) + [""])[:2]
            if base in DECOR_MAP and "Decor(" not in rest:
                floor, decor = DECOR_MAP[base]
                row[i] = "%s+Decor(%s)" % (floor, decor_variant(decor, i, y)) + ("+" + rest if rest else "")
    return cells


def read_bmp(path):
    """(width, height, rows) of a sprite, rows top-to-bottom of (r, g, b) tuples. A PNG (asked for as .png, or as .bmp
    when only the PNG is there) comes in the mask layout (see above); a BMP as it is (8/24/32 bpp). A tile split into
    decor: its old opaque picture (DECOR_MAP)."""
    name = tile_sprite_name(path)
    if name in DECOR_MAP and decor_archive_path(name):
        path = decor_archive_path(name)
    if path.lower().endswith(".png") or not os.path.exists(path):
        if os.path.exists(png_path(path)):
            return read_png(png_path(path))
    with open(path, "rb") as f:
        b = f.read()
    off, = struct.unpack_from("<I", b, 10)
    hsize, w, h, planes, bpp, comp = struct.unpack_from("<IiiHHI", b, 14)
    top_down = h < 0
    h = abs(h)
    palette = []
    if bpp <= 8:
        ncol, = struct.unpack_from("<I", b, 46)
        ncol = ncol or (1 << bpp)
        pal_off = 14 + hsize
        for i in range(ncol):
            bl, gr, rd, _ = struct.unpack_from("<BBBB", b, pal_off + 4 * i)
            palette.append((rd, gr, bl))
    masks = None
    if comp == 3 and bpp in (16, 32):
        masks = struct.unpack_from("<III", b, 14 + 40) if hsize == 40 else struct.unpack_from("<III", b, 54)
    stride = ((w * bpp + 31) // 32) * 4
    rows = []
    for y in range(h):
        base = off + y * stride
        row = []
        for x in range(w):
            if bpp == 24:
                bl, gr, rd = b[base + 3 * x], b[base + 3 * x + 1], b[base + 3 * x + 2]
                row.append((rd, gr, bl))
            elif bpp == 32:
                v, = struct.unpack_from("<I", b, base + 4 * x)
                if masks:
                    def ch(m):
                        if m == 0:
                            return 0
                        shift = (m & -m).bit_length() - 1
                        mx = m >> shift
                        return ((v & m) >> shift) * 255 // mx
                    row.append((ch(masks[0]), ch(masks[1]), ch(masks[2])))
                else:
                    row.append(((v >> 16) & 255, (v >> 8) & 255, v & 255))
            elif bpp == 8:
                row.append(palette[b[base + x]])
            elif bpp == 4:
                byte = b[base + x // 2]
                idx = (byte >> 4) if x % 2 == 0 else (byte & 15)
                row.append(palette[idx])
            else:
                raise ValueError("unsupported bpp %d in %s" % (bpp, path))
        rows.append(row)
    if not top_down:
        rows.reverse()
    return w, h, rows


# ---------------------------------------------------------------- script language
def script_language():
    """dragonsword/script_language.py: the commands, their argument types, help and variables."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("script_language", p("dragonsword", "script_language.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def script_commands():
    """{command name: number of arguments}."""
    return {name: len(args) for name, args in script_language().commands().items()}


def script_command_arg_types():
    """{command name: {1: type of argument 1, 2: ...}}."""
    return {name: {k + 1: t.strip() for k, t in enumerate(args)} for name, args in script_language().commands().items()}


def script_variables():
    return {name for name, _ in script_language().VARIABLES}


# Variables named in dev\Data Formats.md (in addition to the Script Editor's list)
SPEC_VARIABLES = {"$Player.X", "$Player.Y", "$Map.Name", "$Cursor.X", "$Cursor.Y",
                  "$Tile.under.Cursor.X", "$Tile.under.Cursor.Y", "$Entity.under.Cursor.ID"} | \
                 {"$Variable.%d" % i for i in range(1, 10)}
