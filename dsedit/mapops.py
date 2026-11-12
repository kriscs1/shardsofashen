"""Whole maps moved to another square of the world, copied there, or deleted (the Maps page: right-click a map, or
its inspector). What names a map does so by its name, "X,Y,Z": the data files (Config's start map, the music, the
locks, the carts, the quests' markers, the world map's labels...) and the scripts (teleports, queued actions); and a
map's arrival script is the script of its name. Moving a map renames it in all of them, and its arrival script with
it, only where a map is meant: a key that's a map's name (Music, Ambient), a key that holds maps (Start.Map, Maps,
Return, MarkerN, PointN...: MAP_KEY), the world map's places, and a script command's map argument; never a colour or
a list that happens to read the same. The old name goes in dsengine/renames.py RENAMED_MAPS, so a character saved on
it comes back where it is now. The game's own code and the builders in dev\\migrate can name maps too: those are
only listed, to look at (a builder run again puts things back where it had them).

A map's tiles and entities are its own (their coordinates are the map's), so they need nothing."""
import os
import re

from . import scriptlang as SL
from .project import read_text_lines, write_text_lines, parse_map_name, Entity

CODE_DIRS = ("dsengine", "server", os.path.join("web", "js"), os.path.join("dev", "migrate"), "tests")


MAP_KEY = re.compile(r"(^|\.)(maps?|return)$|^(marker|point|node)\d*$", re.I)   # (keys whose values are maps)
SEP = re.compile(r"([\s;|]+)")
RENAMES = os.path.join("dsengine", "renames.py")


def _in_value(v, old, new, lead=False):
    """A value's maps renamed: a word that's old (and with lead, a first word old,X,Y,...: a cart's point)."""
    parts = SEP.split(v)
    for i in range(0, len(parts), 2):
        if parts[i] == old:
            parts[i] = new
        elif lead and i == 0 and parts[i].startswith(old + ","):
            parts[i] = new + parts[i][len(old):]
    return "".join(parts)


def renamed_line(label, ln, old, new):
    """One line of a data file or script (label: _text_files'), with map old called new where it names a map."""
    s = ln.strip()
    if not s or s.startswith((";", "//", "[")):
        return ln
    if label.startswith("Script "):
        f = ln.split("\t")
        types = SL.COMMANDS.get(f[1].strip()) if len(f) > 2 else None
        for i in range(2, len(f)):
            t = SL.norm(types[i - 2]) if types and i - 2 < len(types) else ""
            if t in SL.MAP_TYPES and f[i].strip() == old:
                f[i] = f[i].replace(old, new)
        return "\t".join(f)
    if "=" not in ln:
        return ln
    k, v = ln.split("=", 1)
    key = k.strip()
    if key == old:
        return k.replace(old, new) + "=" + v
    if label == "WorldMap.ini" or MAP_KEY.search(key):
        return k + "=" + _in_value(v, old, new, lead=bool(re.match(r"(point|node)\d", key, re.I)))
    return ln


def name_re(name):
    """A map's name standing on its own ("4,0,0" - not "14,0,0", "-4,0,0" or "4,0,01"; "4,0,0,5,17" is a cart's
    point on it)."""
    return re.compile(r"(?<![\d-])" + re.escape(name) + r"(?!\d)")


def _text_files(project):
    """Every data file and script that can name a map: [(path, label)]."""
    out = []
    data = project.p("data")
    for f in sorted(os.listdir(data)):
        if f.lower().endswith(".ini"):
            out.append((os.path.join(data, f), f))
    folder = project.p("data", "Scripts")
    for f in sorted(os.listdir(folder)):
        if f.lower().endswith(".script"):
            out.append((os.path.join(folder, f), "Script " + f[:-7]))
    return out


def uses(project, name):
    """[(label, line number, the line)] in the data and scripts that name map name (its own arrival script's file
    name isn't a use: it goes with it)."""
    out = []
    for path, label in _text_files(project):
        try:
            lines = read_text_lines(path)
        except OSError:
            continue
        for i, ln in enumerate(lines, 1):
            if name in ln and renamed_line(label, ln, name, "\0") != ln:
                out.append((label, i, ln.strip()))
    return out


def code_uses(project, name):
    """[(file, line number)] in the game's code and the builders that name map name: listed, not changed."""
    pat, out = name_re(name), []
    for d in CODE_DIRS:
        for root, dirs, files in os.walk(project.p(d)):
            dirs[:] = [x for x in dirs if x != "__pycache__"]
            for f in files:
                if not f.endswith((".py", ".js")):
                    continue
                path = os.path.join(root, f)
                try:
                    text = open(path, encoding="utf-8", errors="replace").read()
                except OSError:
                    continue
                for i, ln in enumerate(text.splitlines(), 1):
                    if pat.search(ln):
                        out.append((os.path.relpath(path, project.root), i))
    return out


def move(project, old, new):
    """Map old becomes map new (its square in the world changes): its file, its arrival script, and every data
    file and script that names it. Returns [the files changed]."""
    if not os.path.exists(project.map_path(old)) or os.path.exists(project.map_path(new)):
        raise ValueError("can't move %s to %s" % (old, new))
    todo = []                                           # (every file's new text first: nothing's written till all are)
    for path, label in _text_files(project):
        try:
            lines = read_text_lines(path)
        except OSError:
            continue
        out = [renamed_line(label, ln, old, new) if old in ln else ln for ln in lines]
        if out != lines:
            todo.append((path, label, out))
    changed = []
    for path, label, out in todo:
        write_text_lines(path, out)
        changed.append(label)
    if remember_rename(project, old, new):
        changed.append(RENAMES + " (a character saved there comes back at %s)" % new)
    if os.path.exists(project.script_path(old)) and not os.path.exists(project.script_path(new)):
        os.replace(project.script_path(old), project.script_path(new))
        changed.append("Script %s -> %s (its arrival script)" % (old, new))
    os.replace(project.map_path(old), project.map_path(new))      # (last: a failure before it leaves the map be)
    changed.insert(0, "maps\\%s.map -> %s.map" % (old, new))
    project.refresh()
    for ini in (project.config, project.quests_ini, project.tiles_ini, project.entities_ini):
        ini.load()                                       # (the editor's own copies: as they are now)
    return changed


def remember_rename(project, old, new):
    """RENAMED_MAPS (dsengine/renames.py) told old is new now: what was renamed to old follows it, and new isn't
    renamed away any more (a map there again). False if there's no such file (a project without the engine)."""
    path = project.p(RENAMES)
    if not os.path.exists(path):
        return False
    text = open(path, encoding="utf-8").read()
    m = re.search(r"^RENAMED_MAPS = \{[^\n]*\n(.*?)^\}", text, re.S | re.M)
    if not m:
        return False
    lines = []
    for ln in m.group(1).splitlines():
        kv = re.match(r'\s*"([^"]+)":\s*"([^"]+)"', ln)
        if kv and kv.group(1) == new:
            continue
        if kv and kv.group(2) == old:
            ln = ln.replace('"%s"' % old, '"%s"' % new, 1)
        lines.append(ln)
    lines.append('    "%s": "%s",%s# (the editor\'s Move map)' % (old, new, " " * max(1, 31 - len(old) - len(new))))
    body = "".join(l + "\n" for l in lines if l.strip())
    open(path, "w", encoding="utf-8", newline="\n").write(text[:m.start(1)] + body + text[m.end(1):])
    return True


def copy(project, old, new, entities=True):
    """Map old copied to new: every layer, and its entities too if entities (but not their Ids, nor its named
    places: an Id names one thing in the world). Nothing points at the copy."""
    if not os.path.exists(project.map_path(old)) or os.path.exists(project.map_path(new)):
        raise ValueError("can't copy %s to %s" % (old, new))
    lines = read_text_lines(project.map_path(old))
    H = project.map_h
    keep = []
    for ln in lines[H:] if entities else []:
        e = Entity.parse(ln)
        if e.raw is not None:
            keep.append(ln)
            continue
        if e.kind == "Id":
            continue
        if e.kind not in ("Trigger", "Lock") and e.opt("Id"):
            e.set_opt("Id", "")
        keep.append(e.line())
    write_text_lines(project.map_path(new), lines[:H] + keep)
    project.refresh("maps")


def delete(project, name, with_script=False):
    """Map name's file gone (and its arrival script, if with_script). It's kept in git if it was committed."""
    os.remove(project.map_path(name))
    if with_script and os.path.exists(project.script_path(name)):
        os.remove(project.script_path(name))
    project.refresh()


def free(project, name):
    p = parse_map_name(name)
    return bool(p) and not os.path.exists(project.map_path(name))
