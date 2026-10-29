"""What in the data points at the maps, so the map editor can show it (a badge on the map, a list in the inspector):
  * places, by name: Id tiles and things' Id= - in a script's place arguments, its "<Verb> <Id>" script (the thing's
    own), a quest's markers, the world map's labels, a shardstone ([Key]: its place is Waystone_<Key>);
  * tiles, by coordinates: a quest's or label's "map x y", a script's teleport or queued action (they name their map),
    and the bare coordinates in a map's own arrival script;
  * people, by kind: the NPCs quests are given by (Giver=);
  * whole maps: their arrival script, the teleports to them, their music, sounds and weather.
Read from the saved files, again when any of them changes (looked at every couple of seconds at most; a script is
read again only when it's changed)."""
import os
import time

from .project import read_text_lines, parse_map_name, COORD_TYPES, IniDoc
from .region import COORD_ARGS, MAPPED, NUM_XY
from . import scriptlang as SL

MAP_INIS = ("Ambient.ini", "Music.ini", "Weather.ini", "DayNight.ini", "Waves.ini")   # ([section] map=...)
COORD_ARG = {}                                      # command -> [(its coordinates' argument, in tiles?)]
for _cmd, _i, _in_tiles in COORD_ARGS:
    COORD_ARG.setdefault(_cmd, []).append((_i, _in_tiles))


class Refs:
    def __init__(self, project):
        self.project = project
        self._sig, self._looked = None, 0.0
        self._scripts = {}                  # script -> (its file's time and size, [(table, key, use)])
        self.names, self.tiles, self.givers, self.maps = {}, {}, {}, {}

    # ----- what points at what (each a list of (kind, what): kind "script", "quest" or a file's name)
    def of_name(self, name):
        return self.names.get((name or "").upper(), [])

    def of_tile(self, map_name, tx, ty):
        """tx, ty: tiles from 1."""
        return self.tiles.get((map_name, tx, ty), [])

    def of_kind(self, kind):
        return self.givers.get((kind or "").upper(), [])

    def of_map(self, map_name):
        return self.maps.get(map_name, [])

    # ----- kept up to date
    def fresh(self):
        """Read again if a script or a data file changed since. True if it was."""
        now = time.time()
        if now - self._looked < 2 and self._sig is not None:
            return False
        self._looked = now
        sig = self._signature()
        if sig == self._sig:
            return False
        self._sig = sig
        self._build()
        return True

    def forget(self):
        """Look again next time (a script or quest was just saved here)."""
        self._looked = 0.0

    def _signature(self):
        out = []
        for folder in (self.project.p("data", "Scripts"), self.project.p("data")):
            try:
                with os.scandir(folder) as it:
                    for d in it:
                        if d.is_file() and d.name.lower().endswith((".txt", ".ini")):
                            st = d.stat()
                            out.append((d.name, st.st_mtime_ns, st.st_size))
            except OSError:
                pass
        return tuple(sorted(out))

    def _build(self):
        tables = {"names": {}, "tiles": {}, "givers": {}, "maps": {}}

        def add(table, key, use):
            got = tables[table].setdefault(key, [])
            if use not in got:
                got.append(use)

        def place(text, use):
            """A place named in text: "map x y" (tiles from 1), or a place's name."""
            w = text.split()
            if len(w) == 3 and parse_map_name(w[0]) and w[1].lstrip("-").isdigit() and w[2].lstrip("-").isdigit():
                add("tiles", (w[0], int(w[1]), int(w[2])), use)
            elif len(w) == 1:
                add("names", w[0].upper(), use)

        kept = {}
        try:
            with os.scandir(self.project.p("data", "Scripts")) as it:
                for d in it:
                    if not d.name.lower().endswith(".txt"):
                        continue
                    s, st = d.name[:-4], d.stat()
                    stamp = (st.st_mtime_ns, st.st_size)
                    old = self._scripts.get(s)
                    kept[s] = old if old is not None and old[0] == stamp else (stamp, self._script_refs(s, d.path))
                    for table, key, use in kept[s][1]:
                        add(table, key, use)
        except OSError:
            pass
        self._scripts = kept
        q = IniDoc(self.project.p("data", "Quests.ini"))       # (as saved: read afresh, off the editor's copy)
        for sec in q.sections():
            use = ("quest", sec)
            for k, v in q.items(sec):
                if k.lower().startswith("marker"):
                    for part in v.split(";"):
                        place(part.strip(), use)
                elif k.lower() == "giver" and v.strip():
                    add("givers", v.strip().upper(), use)
        data = self.project.p("data")
        for fname in ("WorldMap.ini", "Shardstones.ini") + MAP_INIS:
            path = os.path.join(data, fname)
            if not os.path.exists(path):
                continue
            sec = ""
            for ln in read_text_lines(path):
                s = ln.strip()
                if not s or s.startswith(";"):
                    continue
                if s.startswith("[") and s.endswith("]"):
                    sec = s[1:-1]
                    if fname == "Shardstones.ini":
                        add("names", ("Waystone_" + sec).upper(), (fname, sec))
                    continue
                if "=" not in s:
                    continue
                k, v = (x.strip() for x in s.split("=", 1))
                if fname == "WorldMap.ini":
                    place(v, (fname, k))
                elif parse_map_name(k):
                    add("maps", k, (fname, "%s %s" % (sec, v)))
        self.names, self.tiles = tables["names"], tables["tiles"]
        self.givers, self.maps = tables["givers"], tables["maps"]

    def _script_refs(self, s, path):
        """[(table, key, use)]: what one script points at."""
        out = []
        tw, th = self.project.tile_w, self.project.tile_h
        use = ("script", s)
        if " " in s:                                        # ("<Verb> <Id>": the thing's own script)
            out.append(("names", s.rsplit(" ", 1)[1].upper(), use))
        arrival = s if parse_map_name(s) else None
        if arrival:
            out.append(("maps", s, use))
        try:
            lines = read_text_lines(path)
        except OSError:
            return out
        types = SL.COMMANDS
        for ln in lines:
            f = ln.split("\t")
            if len(f) < 3 or ln.lstrip().startswith("//"):
                continue
            cmd = f[1].strip()
            args = types.get(cmd)
            for i, v in enumerate(f[2:]):
                t = args[i].strip() if args and i < len(args) else ""
                if t in COORD_TYPES and not NUM_XY.match(v):
                    for word in v.split():
                        if not word.lstrip("-").isdigit():
                            out.append(("names", word.upper(), use))
            if cmd in MAPPED:                               # (its coordinates on the map it names, in pixels)
                ci, mi = MAPPED[cmd]
                if len(f) > max(ci, mi) + 1:
                    m, xy = f[mi + 1].strip(), NUM_XY.match(f[ci + 1])
                    if parse_map_name(m):
                        out.append(("maps", m, use))
                        if xy:
                            out.append(("tiles", (m, int(xy.group(1)) // tw + 1, int(xy.group(2)) // th + 1), use))
            elif arrival and cmd in COORD_ARG:              # (a map's own script: its bare coordinates are its own)
                for i, in_tiles in COORD_ARG[cmd]:
                    xy = NUM_XY.match(f[i + 1]) if len(f) > i + 1 else None
                    if xy:
                        x, y = int(xy.group(1)), int(xy.group(2))
                        out.append(("tiles", (arrival, x, y) if in_tiles else (arrival, x // tw + 1, y // th + 1),
                                    use))
        return out


def label(use):
    """How a use reads in a list: Script Talk to Wim, Quest The Last Will, WorldMap.ini The Chapel."""
    kind, what = use
    return {"script": "Script", "quest": "Quest"}.get(kind, kind) + " " + what
