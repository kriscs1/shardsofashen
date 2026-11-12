"""What in the data points at the maps, so the map editor can show it (a badge on the map, a list in the inspector):
  * places, by name: Id tiles and things' Id= - in a script's place arguments, its "<Verb> <Id>" script (the thing's
    own), a quest's markers, the world map's labels, a shardstone ([Key]: its place is Waystone_<Key>);
  * tiles, by coordinates: a quest's or label's "map x y", a script's teleport or queued action (they name their map),
    and the bare coordinates in a map's own arrival script;
  * people, by kind: the NPCs quests are given by (Giver=);
  * whole maps: their arrival script, the teleports to them, their music, sounds and weather.
Each use keeps the very lines that point (a script's numbered lines, a quest's Marker1=...), so the inspector can show
exactly what. Read from the saved files, again when any of them changes (looked at every couple of seconds at most; a
script is read again only when it's changed).

What a thing runs: script_for() finds the script the game runs when it's clicked (as dsengine's find_action_script
does), and lines_here() the lines of a shared one that can run where it stands."""
import os
import time

from .project import read_text_lines, parse_map_name, COORD_TYPES, IniDoc
from .region import COORD_ARGS, MAPPED, NUM_XY
from . import scriptlang as SL
from ashen.lb import strip_digits

MAP_INIS = ("Ambient.ini", "Music.ini", "Weather.ini", "DayNight.ini", "Waves.ini")   # ([section] map=...)
COORD_ARG = {}                                      # command -> [(its coordinates' argument, in tiles?)]
for _cmd, _i, _in_tiles in COORD_ARGS:
    COORD_ARG.setdefault(_cmd, []).append((_i, _in_tiles))


class Refs:
    def __init__(self, project):
        self.project = project
        self._sig, self._looked = None, 0.0
        self._scripts = {}                  # script -> (its file's time and size, [(table, key, use, its line)])
        self.names, self.tiles, self.givers, self.maps = {}, {}, {}, {}
        self.detail = {}                    # (table, key, use) -> [the lines that point, as written]

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

    def lines(self, use, keys):
        """The lines in use that point at any of keys ((table, key): ("names", "Isle_Bank"), ("tiles", (map, x, y)),
        ("givers", kind), ("maps", map)), each once, as written: "04  Teleport  Isle_Bank  -", "Marker1=Isle_Bank"."""
        out = []
        for table, key in keys:
            if table in ("names", "givers"):
                key = (key or "").upper()
            for ln in self.detail.get((table, key, use), []):
                if ln not in out:
                    out.append(ln)
        return out

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
                        if d.is_file() and d.name.lower().endswith((".script", ".map", ".ini")):
                            st = d.stat()
                            out.append((d.name, st.st_mtime_ns, st.st_size))
            except OSError:
                pass
        return tuple(sorted(out))

    def _build(self):
        tables = {"names": {}, "tiles": {}, "givers": {}, "maps": {}}
        detail = {}

        def add(table, key, use, line=None):
            got = tables[table].setdefault(key, [])
            if use not in got:
                got.append(use)
            if line:
                said = detail.setdefault((table, key, use), [])
                if line not in said:
                    said.append(line)

        def place(text, use, line):
            """A place named in text: "map x y" (tiles from 1), or a place's name."""
            w = text.split()
            if len(w) == 3 and parse_map_name(w[0]) and w[1].lstrip("-").isdigit() and w[2].lstrip("-").isdigit():
                add("tiles", (w[0], int(w[1]), int(w[2])), use, line)
            elif len(w) == 1:
                add("names", w[0].upper(), use, line)

        kept = {}
        try:
            with os.scandir(self.project.p("data", "Scripts")) as it:
                for d in it:
                    if not d.name.lower().endswith(".script"):
                        continue
                    s, st = d.name[:-7], d.stat()
                    stamp = (st.st_mtime_ns, st.st_size)
                    old = self._scripts.get(s)
                    kept[s] = old if old is not None and old[0] == stamp else (stamp, self._script_refs(s, d.path))
                    for table, key, use, line in kept[s][1]:
                        add(table, key, use, line)
        except OSError:
            pass
        self._scripts = kept
        q = IniDoc(self.project.p("data", "Quests.ini"))       # (as saved: read afresh, off the editor's copy)
        for sec in q.sections():
            use = ("quest", sec)
            for k, v in q.items(sec):
                if k.lower().startswith("marker"):
                    for part in v.split(";"):
                        place(part.strip(), use, "%s=%s" % (k, v))
                elif k.lower() == "giver" and v.strip():
                    add("givers", v.strip().upper(), use, "%s=%s" % (k, v))
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
                        add("names", ("Waystone_" + sec).upper(), (fname, sec),
                            "[%s]: its stone is Waystone_%s" % (sec, sec))
                    continue
                if "=" not in s:
                    continue
                k, v = (x.strip() for x in s.split("=", 1))
                if fname == "WorldMap.ini":
                    place(v, (fname, k), "%s=%s" % (k, v))
                elif parse_map_name(k):
                    add("maps", k, (fname, "%s %s" % (sec, v)), "[%s] %s=%s" % (sec, k, v))
        self.names, self.tiles = tables["names"], tables["tiles"]
        self.givers, self.maps = tables["givers"], tables["maps"]
        self.detail = detail

    def _script_refs(self, s, path):
        """[(table, key, use, the line, as written)]: what one script points at."""
        out = []
        tw, th = self.project.tile_w, self.project.tile_h
        use = ("script", s)
        if " " in s:                                        # ("<Verb> <Id>": the thing's own script)
            out.append(("names", s.rsplit(" ", 1)[1].upper(), use,
                        "its own script: runs when it's clicked to %s" % s.rsplit(" ", 1)[0]))
        arrival = s if parse_map_name(s) else None
        if arrival:
            out.append(("maps", s, use, "its arrival script: runs as you come onto the map"))
        try:
            lines = read_text_lines(path)
        except OSError:
            return out
        types = SL.COMMANDS
        n = 0
        for ln in lines:
            if not ln.strip() or ln.lstrip().startswith("//"):
                continue
            n += 1                                          # (numbered as the game and the script page count them)
            f = ln.split("\t")
            if len(f) < 3:
                continue
            said = line_text(n, f[1].strip(), f[2:])
            cmd = f[1].strip()
            args = types.get(cmd)
            for i, v in enumerate(f[2:]):
                t = args[i].strip() if args and i < len(args) else ""
                if t in COORD_TYPES and not NUM_XY.match(v):
                    for word in v.split():
                        if not word.lstrip("-").isdigit():
                            out.append(("names", word.upper(), use, said))
            if cmd in MAPPED:                               # (its coordinates on the map it names, in pixels)
                ci, mi = MAPPED[cmd]
                if len(f) > max(ci, mi) + 1:
                    m, xy = f[mi + 1].strip(), NUM_XY.match(f[ci + 1])
                    if parse_map_name(m):
                        out.append(("maps", m, use, said))
                        if xy:
                            out.append(("tiles", (m, int(xy.group(1)) // tw + 1, int(xy.group(2)) // th + 1), use,
                                        said))
            elif arrival and cmd in COORD_ARG:              # (a map's own script: its bare coordinates are its own)
                for i, in_tiles in COORD_ARG[cmd]:
                    xy = NUM_XY.match(f[i + 1]) if len(f) > i + 1 else None
                    if xy:
                        x, y = int(xy.group(1)), int(xy.group(2))
                        out.append(("tiles", (arrival, x, y) if in_tiles else (arrival, x // tw + 1, y // th + 1),
                                    use, said))
        return out


def line_text(n, cmd, args):
    """A script line as the inspector shows it: "04  Teleport  Isle_Bank  -" (blank arguments at the end left off)."""
    args = [a.strip() for a in args]
    while args and not args[-1]:
        args.pop()
    return "  ".join(["%02d" % n, cmd] + args)


SHARED_KINDS = ("NPC", "MapItem", "StaticObject", "Tile")      # (a "<Verb> [Kind]" script is every one's)


def script_for(names, verb, name, kind, oid=""):
    """The script the game runs when this is clicked to verb, found as find_action_script finds it
    (dsengine/scripting.py): "<Verb> <Id>", "<Verb> <Name>", "<Verb> <Name without its number>", "<Verb> [<Kind>]".
    (script, "own") for the one thing's own (by its Id), (script, "shared") for one every such thing runs, or None."""
    have = {n.upper(): n for n in names}
    tries = [("%s %s" % (verb, oid), "own")] if oid else []
    tries.append(("%s %s" % (verb, name), "shared"))
    if strip_digits(name) != name:
        tries.append(("%s %s" % (verb, strip_digits(name)), "shared"))
    if kind in SHARED_KINDS:
        tries.append(("%s [%s]" % (verb, kind), "shared"))
    for s, how in tries:
        if s.upper() in have:
            return have[s.upper()], how
    return None


def lines_here(cmds, map_name):
    """The lines of a script that can run on map_name: from line 1, every way on (both ways at a condition, any answer
    to a conversation), except that >On.Map and >Not.On.Map are settled by the map. cmds: ScriptDoc.commands().
    [(number, its text)], in order."""
    n, seen, todo = len(cmds), set(), [1]
    while todo:
        i = todo.pop()
        if not 1 <= i <= n or i in seen:
            continue
        seen.add(i)
        cmd, args = cmds[i - 1].command.strip(), [a.strip() for a in cmds[i - 1].args]
        types = SL.COMMANDS.get(cmd) or []
        jumps = [int(a) for k, a in enumerate(args) if a.isdigit() and
                 (SL.is_goto(types[k]) if k < len(types) else not types and cmd.startswith(">") and k == len(args) - 1)]
        if cmd in (">On.Map", ">Not.On.Map") and args:
            met = (args[0].replace(" ", "") == map_name) == (cmd == ">On.Map")
            todo.append(i + 1 if met else (jumps[-1] if jumps else n + 1))
        elif cmd in ("End", "Goto.Line", "Goto.Script"):
            todo += jumps
        elif cmd == "Display.Conversation" and len(args) > 2:  # (it waits for an answer, and goes where that says)
            todo += jumps
        else:
            todo += jumps + [i + 1]
    return [(i, line_text(i, cmds[i - 1].command.strip(), cmds[i - 1].args)) for i in sorted(seen)]


def label(use):
    """How a use reads in a list: Script Talk to Wim, Quest The Last Will, WorldMap.ini The Chapel."""
    kind, what = use
    return {"script": "Script", "quest": "Quest"}.get(kind, kind) + " " + what
