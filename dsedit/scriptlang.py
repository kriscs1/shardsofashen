"""What the script editor knows about the language: the choices for each argument type, which builder it gets,
what an argument refers to (so the editor can jump there), and the checks."""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
from ashen import script_language as L  # noqa: E402

COMMANDS = L.commands()
COMMAND_NAMES = sorted(COMMANDS, key=lambda n: n.lstrip(">").lower())
VARIABLES = L.VARIABLES

COLOURS = ["Black", "Blue", "Brown", "Cyan", "DarkBlue", "DarkCyan", "DarkGray", "DarkGreen", "DarkPink", "DarkRed",
           "Green", "LightGray", "Pink", "Red", "White", "Yellow"]
NUMERIC = {"DELAY", "SECONDS BEFORE CHANGING", "SECONDS BEFORE CHANGING BACK", "SECONDS TO WAIT", "REQUIRED DISTANCE",
           "CHANCE (%)", "SPEED", "VIEW DISTANCE", "QUANTITY TO ADD", "QUANTITY TO REMOVE", "QUANTITY REQUIRED",
           "DISALLOWED QUANTITY"}
PIXEL_COORDS = {"X COORDINATE,Y COORDINATE", "TARGET X,TARGET Y"}
TILE_COORDS = {"REQUIRED TILE COORDINATES", "DISALLOWED TILE COORDINATES"}
ITEM_TYPES = {"ITEM NAME", "REQUIRED ITEM", "DISALLOWED ITEM"}
ENTITY_TYPES = {"ENTITY NAME", "PLAYER SPRITE"}
TILE_TYPES = {"CHANGE TO TILE", "CHANGE FROM TILE", "REQUIRED TILE NAME", "DISALLOWED TILE NAME"}
MAP_TYPES = {"REQUIRED MAP NAME", "DISALLOWED MAP NAME", "MAP NAME"}


def norm(t):
    t = t.strip()
    if "GOTO LINE" in t:
        return "GOTO LINE"
    if t.startswith("RESPONSE "):
        return "RESPONSE"
    return t


def help_for(t):
    return L.help_for(t).replace("|", "\n")


def is_goto(t):
    return "GOTO LINE" in t


def builder_kind(t, line_args, cmd):
    """'COND', 'COORD', 'TILE', 'QTY', 'PICK' or '' for an argument type (the "…" button)."""
    n = norm(t)
    if n == "REQUIREMENT":
        return "COND"
    if n == "NAME / CALCULATION":
        return "COND" if (line_args[0].strip().upper() if line_args else "") == "CALCULATION" else "PICK"
    if n in PIXEL_COORDS:
        return "COORD"
    if n in TILE_COORDS:
        return "TILE"
    if n == "QUANTITY (+, - or =)":
        return "QTY"
    if n == "CHANGE TO":
        vt = line_args[2].strip().upper() if len(line_args) > 2 else ""
        if vt and vt not in ("POSITION", "TYPE", "NAME", "AGGRESSIVE", "ATTITUDE"):
            return "QTY"
    if n in ITEM_TYPES | ENTITY_TYPES | TILE_TYPES | MAP_TYPES | {"GOTO SCRIPT NAME", "SOUND FILE", "NPC NAME",
                                                                  "RACK ID", "QUEST NAME", "ATTRIBUTE NAME"}:
        return "PICK"
    return ""


def link_of(t, value):
    """(section kind, key) an argument refers to, for a jump button; or None."""
    n, v = norm(t), value.strip()
    if not v or "$" in v:
        return None
    if n in ITEM_TYPES | ENTITY_TYPES | {"NPC NAME"}:
        return ("entity", v)
    if n in TILE_TYPES:
        return ("tile", v)
    if n in MAP_TYPES:
        return ("map", v)
    if n == "GOTO SCRIPT NAME":
        return ("script", v)
    if n == "RACK ID" and v != "-":
        return ("rack", v)
    if n == "QUEST NAME":
        return ("quest", v)
    if n in PIXEL_COORDS | TILE_COORDS and "," not in v and " " not in v:
        return ("place", v)                         # a named place: its map, at its tile
    return None


def options(project, t, line_args, all_lines, line_summary):
    """The drop-down's choices for an argument type. line_args: this line's arguments; all_lines: the script's
    command lines [(command, args)]; line_summary(i): "05  Display.Message  ..." for goto lists."""
    n = norm(t)
    a = lambda i: line_args[i].strip().upper() if len(line_args) > i else ""
    if n == "$PLAYER.NAME":
        return ["$Player.Name"]
    if n == "REQUIREMENT":
        return sorted(v for v, _ in VARIABLES) + ["$Random.Percent>50", "$Variable.1=0", "$Variable.1>0",
                                                  "$Attr.Name>=1", "$Item.Name>=1", "$Skill.Name>=10",
                                                  "$Equipped.Weapon=none"]
    if n == "SAVE AS":
        return ["Variable.%d$" % i for i in range(1, 10)]
    if n == "ADD/REMOVE":
        return ["ADD", "REMOVE"]
    if n == "BLACKOUT TILE ID":
        return [str(i) for i in range(1, 91)]
    if n == "VIEW DISTANCE":
        return [str(i) for i in range(50, 501, 50)]
    if n == "SPEED":
        return ["1", "2", "3", "4", "5"]
    if n == "ON/OFF":
        return ["ON", "OFF"]
    if n == "CHANCE (%)":
        return ["5", "10", "20", "25", "33", "50", "66", "75", "90", "100"]
    if n == "CHANGE TO":
        vt = a(2)
        return {"POSITION": ["=X,Y", "+X,Y", "-X,Y", "=$Player.X,$Player.Y"], "TYPE": ["MapItem", "StaticObject", "NPC"],
                "NAME": project.placeable(), "AGGRESSIVE": ["=1", "=0"], "ATTITUDE": ["Good", "Bad"]}.get(
            vt, ["=N", "+N", "-N"] if vt else [])
    if n in TILE_TYPES:
        return project.tiles()
    if n == "COMMAND":
        return COMMAND_NAMES
    if n == "COLOUR":
        return COLOURS
    if n == "GOTO LINE":
        return [line_summary(i) for i in range(1, len(all_lines) + 1)]
    if n == "GOTO SCRIPT NAME":
        return project.scripts()
    if n == "VALUE TYPE":
        return ["ATTRIBUTE", "BANK", "CALCULATION", "EQUIPPED", "HITPOINTS", "INVENTORY", "SKILL", "XP"]
    if n == "NAME / CALCULATION":
        vt = a(0)
        return {"SKILL": project.skills, "XP": project.skills, "BANK": project.items(), "INVENTORY": project.items(),
                "EQUIPPED": ["Weapon", "Shield", "Head", "Body", "Legs", "Feet", "Hands", "Ring"], "HITPOINTS": ["-"],
                "CALCULATION": sorted(v for v, _ in VARIABLES) + ["$Random.Percent>50"],
                "ATTRIBUTE": project.attributes()}.get(vt, [])
    if n == "ATTRIBUTE NAME":
        return project.attributes()
    if n == "ATTITUDE":
        return ["Good", "Bad"]
    if n == "NPC ID":
        ids = set()
        for m in project.maps():
            from .project import read_text_lines
            for l in read_text_lines(project.map_path(m))[project.map_h:]:
                for w in re.findall(r"\bId=(\S+)", l):
                    ids.add(w)
        return ["CLICKED"] + sorted(ids)
    if n == "QUEST NAME":
        return project.quests_ini.sections()
    if n == "NOTE":
        return []
    if n in ("MESSAGE", "MESSAGE (\\)"):
        return ["You are too far away!", "You are not high enough level to do that!",
                "You don't have enough space in your inventory!", "Nothing interesting happens."]
    if n in ENTITY_TYPES:
        return project.placeable()
    if n in ITEM_TYPES:
        return project.items()
    if n in ("ENTITY TYPE", "REQUIRED ENTITY TYPE"):
        return ["MapItem", "StaticObject", "NPC"]
    if n == "NPC NAME":
        return ["$Player.Name"] + project.npcs()
    if n == "ENTITY MISC":
        return ["-"] + [str(i) for i in range(1, 31)]
    if n == "QUEUE ENTRY":
        out = []
        for cmd, args in all_lines:
            if cmd == "Add.Action.To.Queue":
                out.append("[TAB]".join(x.strip() for x in args[:6]) + "*")
        return out + ["REMOVE[TAB]Name[TAB]StaticObject[TAB]-[TAB]$Map.Name[TAB]X,Y*"]
    if n in ("QUANTITY TO REMOVE", "QUANTITY TO ADD", "QUANTITY REQUIRED", "DISALLOWED QUANTITY", "DISALLOWED LEVEL"):
        return [str(i) for i in range(1, 31)]
    if n == "QUANTITY (+, - or =)":
        return ["+1", "+5", "+10", "+0.05", "-1", "-5", "=0", "=1"]
    if n == "RACK ID":
        return ["-"] if a(0) == "BANK" else project.racks_ini.sections()
    if n in ("REQUIRED DIRECTION(S)", "DISALLOWED DIRECTION(S)"):
        return ["N", "S", "E", "W", "NE", "NS", "NW", "SE", "SW", "EW", "NEW", "NSW", "NSE", "SEW"]
    places = sorted((v[0] for v in project.places().values()), key=str.lower) if n in PIXEL_COORDS | TILE_COORDS         else []                                     # (a place's name works wherever coordinates do)
    if n == "TARGET X,TARGET Y":
        return ["$Player.X,$Player.Y", "$Cursor.X,$Cursor.Y", "$Object.under.Cursor.X,$Object.under.Cursor.Y",
                "$Variable.1,$Variable.2"] + places
    if n == "X COORDINATE,Y COORDINATE":
        return ["$Player.X,$Player.Y", "$Cursor.X,$Cursor.Y", "$Object.under.Cursor.X,$Object.under.Cursor.Y"] + places
    if n in TILE_COORDS:
        return ["$Tile.under.Player.X,$Tile.under.Player.Y", "$Tile.under.Cursor.X,$Tile.under.Cursor.Y"] + places
    if n in ("SECONDS BEFORE CHANGING", "SECONDS BEFORE CHANGING BACK", "SECONDS", "SECONDS TO WAIT", "DELAY"):
        return [str(i) for i in (0, 1, 2, 3, 4, 5, 10, 15, 20, 30, 60, 90)]
    if n == "REQUIRED DISTANCE":
        return [str(i) for i in range(5, 101, 5)]
    if n in MAP_TYPES:
        return ["$Map.Name"] + project.maps()
    if n in ("SKILL NAME", "DISALLOWED SKILL NAME", "REQUIRED SKILL NAME"):
        return project.skills
    if n == "SOUND FILE":
        return project.sounds()
    if n == "CONVERSATION TYPE":
        return ["OK", "NEXT", "BYE", "YN"]
    if n == "RESPONSE":
        return ["Yes", "No", "OK", "Bye", "Shop", "Bank"]
    if n == "ITEMRACK TYPE":
        return ["BANK", "GENERAL", "SPECIFIC"]
    if n == "VALUE TO CHANGE":
        return ["X", "Y", "POSITION", "TYPE", "NAME", "MISC", "QUANTITY", "HP", "MAXHP", "SPEED", "STRENGTH",
                "DEFENCE", "AGGRESSIVE", "ATTITUDE", "AGGRO.RANGE", "ORIGINAL.X", "ORIGINAL.Y"]
    return []


def kind_of(project, name):
    """The kind of script, from its name (the Scripts list's filter)."""
    from .project import parse_map_name
    if name.startswith("Talk to "):
        return "Talk to"
    if name.startswith("Use ") and " With " in name:
        return "Use … With …"
    if name.startswith("Kill "):
        return "Kill"
    if parse_map_name(name):
        return "Map entry"
    if name.endswith(" Skill"):
        return "Skill"
    if name in project.index()["script_trigger"]:
        return "Trigger"
    first = name.split(" ")[0]
    if first in project.verbs() or name.split(" [")[0] in project.verbs():
        return "Verb on a thing"
    return "Other"


KINDS = ["Talk to", "Use … With …", "Verb on a thing", "Kill", "Map entry", "Trigger", "Skill", "Other"]


def check(project, doc):
    """[(line number or 0, "error"|"warn", text)] for a script."""
    out = []
    cmds = doc.commands()
    n = len(cmds)
    names = set(project.scripts())
    places = None                                   # (read when a line names one)
    for i, l in enumerate(cmds, 1):
        args_t = COMMANDS.get(l.command)
        if args_t is None:
            out.append((i, "error", "%s isn't a command the game knows." % (l.command or "(nothing)")))
            continue
        extra = len(l.args) - len(args_t)
        if l.command == "Display.Conversation" and extra > 0 and extra % 2 == 0:
            pass                        # (more answers than the 4 the editor shows: the game shows them all)
        elif extra > 0 and any(a.strip() for a in l.args[len(args_t):]):
            out.append((i, "error", "%s takes %d arguments, this line has %d." % (l.command, len(args_t), len(l.args))))
        for k, t in enumerate(args_t):
            v = l.args[k].strip() if k < len(l.args) else ""
            nt = norm(t)
            if is_goto(t):
                if v and not (v.isdigit() and 1 <= int(v) <= n):
                    out.append((i, "error", "%s goes to line %s, but the script has %d lines." % (l.command, v, n)))
                elif not v and nt == "GOTO LINE" and "RESPONSE" not in t and "CANCELLED" not in t:
                    out.append((i, "error", "%s needs its %s." % (l.command, t.strip().lower())))
                continue
            if not v:
                if nt not in ("ENTITY MISC", "RESPONSE", "NOTE", "MESSAGE (\\)") and not t.startswith("RESPONSE"):
                    out.append((i, "warn", "%s: %s is empty." % (l.command, t.strip().lower())))
                continue
            if "$" in v:
                continue
            if nt in NUMERIC and not re.fullmatch(r"-?\d+(\.\d+)?(-\d+)?", v):
                out.append((i, "warn", "%s: %s should be a number, not %r." % (l.command, t.strip().lower(), v)))
            if nt in PIXEL_COORDS | TILE_COORDS and "," not in v:
                if places is None:
                    places = project.places()
                for w in (v.split() if nt in TILE_COORDS else [v]):
                    if "," not in w and w.upper() not in places:
                        out.append((i, "error", "%s: %s should be X,Y or a place's ID; there's no place %s."
                                    % (l.command, t.strip().lower(), w)))
            if nt == "GOTO SCRIPT NAME" and v not in names:
                out.append((i, "warn", "There's no script called %s." % v))
            if nt in ITEM_TYPES | ENTITY_TYPES and v not in project.entities():
                out.append((i, "warn", "%s has no sprite in sprites\\Entities." % v))
            if nt in TILE_TYPES and v not in project.tiles():
                out.append((i, "warn", "%s has no sprite in sprites\\Tiles." % v))
            if nt == "RACK ID" and v != "-" and not project.racks_ini.has_section(v):
                out.append((i, "warn", "There's no rack %s in ItemRacks.ini." % v))
    if n and cmds[-1].command not in ("End", "Goto.Script", "Goto.Line"):
        out.append((n, "warn", "The script doesn't end with End."))
    return out
