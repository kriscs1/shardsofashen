"""Convert the old Dragon Sword data ("Previous (to convert)") to the v2 formats in dev\\Data Formats.md.

Run:  python -I "dev\\migrate\\migrate.py"     (from anywhere)

Idempotent: re-running produces the same files. Existing values in the v2 ini files
(Config/Tiles/Entities) always win over values migrated from the old data, so edits made
with the editors after the first run are kept.
"""
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (NEW, OLD, MAP_W, MAP_H, Ini, Renamer, p, o, read_lines, write_lines,
                    strip_trailing_blank, read_bmp, sprite_names, script_command_arg_types)

R = Renamer()
LOG = []


def log(msg):
    LOG.append(msg)
    print(msg)


# =====================================================================================
# 1. Maps
# =====================================================================================
ENTITY_TYPE_MAP = {"Object": "MapItem", "Static": "StaticObject", "GoodNPC": "GoodNPC",
                   "BadNPC": "BadNPC", "Trigger": "Trigger", "MapItem": "MapItem",
                   "StaticObject": "StaticObject"}


def move_test_maps():
    test_dir = p("maps", "Test")
    os.makedirs(test_dir, exist_ok=True)
    for name in ("0,0,0.txt", "1,0,0.txt"):
        src, dst = p("maps", name), os.path.join(test_dir, name)
        if os.path.exists(dst):
            continue            # already moved on an earlier run; maps\name is now the converted map
        if os.path.exists(src):
            shutil.move(src, dst)
            log("Moved test map maps\\%s -> maps\\Test\\%s" % (name, name))


def convert_cell(cell):
    cell = cell.strip()
    roof = None
    if "-" in cell:                                   # old: Base-<1 digit group><RoofName>
        base, rest = cell.split("-", 1)
        group, roof_name = rest[:1], rest[1:]
        roof = (R.name(roof_name), int(group) if group.isdigit() else 0)
        cell = base
    out = R.name(cell)
    if roof:
        out += "+Roof(%s.%02d)" % roof
    return out


def convert_map(old_path, new_path, script_renames):
    lines = read_lines(old_path)
    rows = []
    notes = []
    for y in range(MAP_H):
        cells = lines[y].split(":") if y < len(lines) else []
        if len(cells) > MAP_W:
            notes.append("row %d had %d columns" % (y + 1, len(cells)))
            cells = cells[:MAP_W]       # 26th column = duplicate of the east neighbour's 1st column
        if len(cells) < MAP_W:
            raise SystemExit("%s row %d has only %d columns" % (old_path, y + 1, len(cells)))
        rows.append(":".join(convert_cell(c) for c in cells))
    entities = []
    for line in lines[MAP_H:]:
        f = [x.strip() for x in line.split("\t")]
        if not f or f[0] == "":
            continue
        typ = ENTITY_TYPE_MAP.get(f[0])
        if typ is None:
            log("  WARNING %s: unknown entity type %r skipped" % (os.path.basename(old_path), f[0]))
            continue
        name = f[1] if len(f) > 1 else ""
        x = f[2] if len(f) > 2 else "0"
        y = f[3] if len(f) > 3 else "0"
        x, y = str(int(float(x or 0))), str(int(float(y or 0)))
        if typ == "Trigger":
            name = script_renames.get(name, name)
            entities.append("\t".join([typ, name, x, y]))       # already 1-based tile coords
        elif typ == "MapItem":
            q = f[4] if len(f) > 4 and f[4] else "1"
            q = str(int(float(q))) if float(q) > 0 else "1"
            entities.append("\t".join([typ, R.name(name), x, y, q]))
        else:
            entities.append("\t".join([typ, R.name(name), x, y]))
    out = rows + [""] + entities
    write_lines(new_path, out)
    return notes


def migrate_maps(script_renames):
    move_test_maps()
    old_dir = o("maps")
    count = 0
    for f in sorted(os.listdir(old_dir)):
        if not re.match(r"^-?\d+,-?\d+,-?\d+\.txt$", f):
            continue
        notes = convert_map(os.path.join(old_dir, f), p("maps", f), script_renames)
        count += 1
        if notes:
            log("  Map %s: trimmed to 25 columns (%s)" % (f, "all 21 rows had 26 columns" if len(notes) == MAP_H else "; ".join(notes)))
    log("Maps: converted %d maps" % count)


# =====================================================================================
# 2. Scripts
# =====================================================================================
ARG_TYPES_TO_RENAME = {"ITEM NAME", "REQUIRED ITEM", "DISALLOWED ITEM", "ENTITY NAME", "CHANGE TO TILE",
                       "CHANGE FROM TILE", "NPC NAME", "PLAYER SPRITE", "REQUIRED TILE NAME",
                       "DISALLOWED TILE NAME"}
RACK_TYPE_MAP = {"CREATABLES": "SPECIFIC", "GENERAL": "GENERAL", "BANK": "BANK"}
RACK_ID_MAP = {"CREATABLES-Cooking": "CRAFT-Cooking", "CREATABLES-Smithing": "CRAFT-Smithing",
               "SHOP-General": "SHOP-General"}
QUEUE_ACTION_MAP = {"Remove.Entity": "REMOVE", "Add.Entity": "ADD"}
SCRIPT_ENTITY_TYPE_MAP = {"Object": "MapItem", "Static": "StaticObject"}
VARIABLE_RENAMES = [("$Map.X,$Map.Y,$Map.Z", "$Map.Name"),
                    ("$Entity.under.Cursor.X", "$Object.under.Cursor.X"),
                    ("$Entity.under.Cursor.Y", "$Object.under.Cursor.Y")]

# Scripts whose old commands don't exist in the v2 language: hand-written replacements.
SCRIPT_OVERRIDES = {
    # Old version used Get.Entity.Info / Get.X.Direction.Vector / Get.Y.Direction.Vector /
    # Travel.In.Direction, none of which are in [Get.Commands]. Same behaviour (Tallulah trots
    # away from the player) using Get.Value CALCULATION + Move.Entity.
    "Stroke Tallulah.txt": [
        "01\t>Distance.From.Clicked.Entity\t40\t06",
        "02\tGet.Value\tCALCULATION\t2*$Object.under.Cursor.X-$Player.X\tVariable.1$",
        "03\tGet.Value\tCALCULATION\t2*$Object.under.Cursor.Y-$Player.Y\tVariable.2$",
        "04\tMove.Entity\t$Object.under.Cursor.X,$Object.under.Cursor.Y\tTallulah\t$Variable.1,$Variable.2\t2",
        "05\tEnd",
        "06\tDisplay.Message\tDarkRed\tYou are too far away!",
        "07\tEnd",
    ],
}


def new_script_name(old_file):
    stem = old_file[:-4]
    words = stem.split(" ")
    out = []
    for w in words:
        n = R.name(w)
        out.append(n if R.known(n) else w)
    stem = " ".join(out)
    stem = re.sub(r"^Talk To ", "Talk to ", stem)
    stem = re.sub(r" with ", " With ", stem)
    return stem + ".txt"


def convert_script_line(line, next_line_no, arg_types, script_renames):
    if line.strip() == "":
        return None
    if line.lstrip().startswith("//"):
        return line.rstrip()
    f = line.split("\t")
    num = f[0].strip()
    num = "%02d" % int(num) if num.isdigit() else num
    cmd = f[1].strip() if len(f) > 1 else ""
    args = [a.strip() for a in f[2:]]
    while args and args[-1] == "":
        args.pop()
    types = arg_types.get(cmd, {})
    # variables
    args2 = []
    for a in args:
        for old, new in VARIABLE_RENAMES:
            a = a.replace(old, new)
        args2.append(a)
    args = args2
    # entity / item / tile names
    for i, a in enumerate(args):
        if types.get(i + 1) in ARG_TYPES_TO_RENAME:
            args[i] = R.name(a)
    # command specific fixes
    if cmd == "Display.Item.Rack":
        args[0] = RACK_TYPE_MAP.get(args[0].upper(), args[0])
        if len(args) > 2:
            args[2] = RACK_ID_MAP.get(args[2], args[2])
        if len(args) == 3:
            args.append(next_line_no)          # GOTO LINE IF CANCELLED -> just continue
    elif cmd == "Add.Entity":
        if len(args) > 2:
            args[2] = SCRIPT_ENTITY_TYPE_MAP.get(args[2], args[2])
        while len(args) < 4:
            args.append("1" if args[2:3] == ["MapItem"] else "-")
    elif cmd == "Add.Action.To.Queue":
        args[0] = QUEUE_ACTION_MAP.get(args[0], args[0])
        args[1] = R.name(args[1])
        args[2] = SCRIPT_ENTITY_TYPE_MAP.get(args[2], args[2])
        if args[3] == "":
            args[3] = "-"
    elif cmd == "Remove.Action.From.Queue":
        a = args[0]
        for old, new in QUEUE_ACTION_MAP.items():
            if a.startswith(old + "[TAB]"):
                a = new + a[len(old):]
        a = a.replace("[TAB]Static[TAB]", "[TAB]StaticObject[TAB]").replace("[TAB]Object[TAB]", "[TAB]MapItem[TAB]")
        a = a.replace("[TAB][TAB]", "[TAB]-[TAB]")
        a = a.replace("$Object.under.Cursor.X[TAB]$Object.under.Cursor.Y", "$Object.under.Cursor.X,$Object.under.Cursor.Y")
        args[0] = a
    elif cmd == "Goto.Script":
        args[0] = script_renames.get(args[0], args[0])
    return "\t".join([num, cmd] + args)


def migrate_scripts():
    old_dir = o("data", "Custom Scripts")
    new_dir = p("data", "Scripts")
    arg_types = script_command_arg_types()
    files = sorted(f for f in os.listdir(old_dir) if f.lower().endswith(".txt"))
    renames = {f[:-4]: new_script_name(f)[:-4] for f in files}
    for f in files:
        new_f = renames[f[:-4]] + ".txt"
        if f in SCRIPT_OVERRIDES:
            out = SCRIPT_OVERRIDES[f]
        else:
            lines = [l for l in read_lines(os.path.join(old_dir, f)) if l.strip() != ""]
            out = []
            for i, l in enumerate(lines):
                nxt = "%02d" % (i + 2)
                c = convert_script_line(l, nxt, arg_types, renames)
                if c is not None:
                    out.append(c)
        write_lines(os.path.join(new_dir, new_f), out)
        if new_f != f:
            log("  Script %s -> %s" % (f, new_f))
    # Pickup [MapItem] / Drop [InventoryItem]: deliberately left empty = engine built-in default.
    for f in ("Pickup [MapItem].txt", "Drop [InventoryItem].txt"):
        path = os.path.join(new_dir, f)
        if not os.path.exists(path):
            open(path, "wb").close()
    log("Scripts: converted %d scripts" % len(files))
    return renames


# =====================================================================================
# 3. Entities.ini
# =====================================================================================
BAD_NPCS = {"Goblin", "Hobgoblin", "Chicken"}
GOOD_NPCS = {"Man", "Woman", "Tallulah", "Farmer", "Baker", "Banker", "Shopkeeper", "Beggar",
             "Blacksmith", "Herbalist", "King_Tyron", "Miner", "Wizard"}
STATIC_OBJECTS = {"Notice", "Fire"}
NOT_ENTITIES = {"Trigger", "Placeholder"}     # editor/engine helper sprites; Player* too
BIG_STACK = "9999999999"
DEFAULT_RESPAWN = "10"

ENTITY_KEY_ORDER = ["Type", "Use.Words", "Examine.Info", "Stackable", "Droppable", "Value", "Food.Value",
                    "Hitpoints", "Attack.Speed", "Strength", "Defence", "Aggro.Range", "Weapon.Range",
                    "Movement.Speed", "Aggressive", "Respawn", "Drops"]

ENTITIES_HEADER = [
    ";[Default]",
    ";Type=MapItem                ; MapItem|StaticObject|GoodNPC|BadNPC (what the Map Editor places it as)",
    ";Use.Words=                  ; comma list of extra right-click verbs, the first is the left-click action",
    ";Examine.Info=It's not very interesting (all entities are examinable)",
    ";Stackable=1                 ; max quantity per inventory slot (1 = not stackable)",
    ";Droppable=1                 ; 0 = can't be dropped",
    ";Value=0                     ; shop price in Gold_Coin(s)",
    ";Food.Value=0                ; hitpoints healed when eaten (0 = not food)",
    ";; NPC only (defaults from the old BadNPC Stats 'Default' row):",
    ";Hitpoints=5",
    ";Attack.Speed=0.8",
    ";Strength=1",
    ";Defence=1",
    ";Aggro.Range=60",
    ";Weapon.Range=0",
    ";Movement.Speed=1",
    ";Aggressive=0",
    ";Respawn=10",
    ";Drops=Bones,1-1,100         ; space-separated Item,min-max,percent",
]


def read_tab_file(path):
    out = []
    for l in read_lines(path):
        if l.strip() == "":
            continue
        out.append([x.strip() for x in l.split("\t")])
    return out


def read_use_words():
    """Old Use Words.txt -> {(name, kind): [verbs]} in file order."""
    res = {}
    verb = None
    for l in read_lines(o("data", "Misc", "Use Words.txt")):
        l = l.strip()
        if l.startswith(">"):
            verb = l[1:].strip()
        elif l.startswith("#") and verb:
            for tok in l.split():
                tok = tok.lstrip("#")
                name, _, kind = tok.rpartition(".")
                res.setdefault((name, kind), []).append(verb)
    return res


def merge_words(existing, extra):
    words = [w.strip() for w in existing.split(",") if w.strip()] if existing else []
    for w in extra:
        if w not in words:
            words.append(w)
    return ",".join(words)


def set_if_unset(ini, sec, key, value):
    cur = ini.get(sec, key)
    if cur is None or cur.strip() == "":
        ini.set(sec, key, value)


def convert_drops(s):
    out = []
    for d in s.split():
        parts = d.split(",")
        parts[0] = R.name(parts[0])
        out.append(",".join(parts))
    return " ".join(out)


def migrate_entities():
    path = p("data", "Entities.ini")
    ini = Ini(path)
    # normalise Undroppable -> Droppable
    for name, items in ini.sections:
        v = ini.get(name, "Undroppable")
        if v is not None:
            ini.remove(name, "Undroppable")
            if ini.get(name, "Droppable") in (None, ""):
                ini.set(name, "Droppable", "0" if v.strip() not in ("", "0") else "1")
    sprites = [s for s in R.entities if s not in NOT_ENTITIES and not s.startswith("Player")]

    # old data
    stats = read_tab_file(o("data", "Misc", "BadNPC Stats.txt"))
    hdr, rows = stats[0], {r[0]: r for r in stats[1:]}
    default_row = rows.get("Default")
    examine = {R.name(r[0]): r[1] for r in read_tab_file(o("data", "Misc", "Examine Information.txt")) if len(r) > 1}
    food = {R.name(r[0]): r[1] for r in read_tab_file(o("data", "Misc", "Food Values.txt")) if r[0] != "Default"}
    stack = {R.name(r[0]) for r in read_tab_file(o("data", "Misc", "Stackable Objects.txt"))}
    undrop = {R.name(r[0]) for r in read_tab_file(o("data", "Misc", "Undroppable Items.txt"))}
    prices = {R.name(r[0]): r[1] for r in read_tab_file(o("data", "ItemRack", "Price List.txt")) if len(r) > 1}
    uses = {}
    for (name, kind), verbs in read_use_words().items():
        if kind != "Tile":
            uses.setdefault(R.name(name), []).extend(verbs)

    for s in sprites:
        ini.section(s, create=True)
        if s in BAD_NPCS:
            typ = "BadNPC"
        elif s in GOOD_NPCS:
            typ = "GoodNPC"
        elif s in STATIC_OBJECTS:
            typ = "StaticObject"
        else:
            typ = "MapItem"
        set_if_unset(ini, s, "Type", typ)
        if s in uses:
            ini.set(s, "Use.Words", merge_words(ini.get(s, "Use.Words"), [u for u in uses[s] if u != "Examine"]))
        if s in examine:
            set_if_unset(ini, s, "Examine.Info", examine[s])
        if s in stack:
            set_if_unset(ini, s, "Stackable", BIG_STACK)
        if s in undrop:
            set_if_unset(ini, s, "Droppable", "0")
        if s in prices:
            set_if_unset(ini, s, "Value", prices[s])
        if s in food:
            set_if_unset(ini, s, "Food.Value", food[s])
        if typ == "BadNPC":
            row = rows.get(s, default_row)
            # columns: Name Hits AttSpd Str Def AgRnge AtSpeed WepRnge MovSpd Aggres Drops
            # (the old game used column 7 'AtSpeed' as the attack speed; column 3 was unused)
            set_if_unset(ini, s, "Hitpoints", row[1])
            set_if_unset(ini, s, "Attack.Speed", row[6])
            set_if_unset(ini, s, "Strength", row[3])
            set_if_unset(ini, s, "Defence", row[4])
            set_if_unset(ini, s, "Aggro.Range", row[5])
            set_if_unset(ini, s, "Weapon.Range", row[7])
            set_if_unset(ini, s, "Movement.Speed", row[8])
            set_if_unset(ini, s, "Aggressive", row[9])
            set_if_unset(ini, s, "Respawn", DEFAULT_RESPAWN)
            if len(row) > 10:
                set_if_unset(ini, s, "Drops", convert_drops(row[10]))
    # drop empty placeholder keys, order keys, sort sections
    for sec in ini.sections:
        items = [(k, v) for k, v in sec[1] if k is None or v.strip() != ""]
        known = [kv for kv in items if kv[0] in ENTITY_KEY_ORDER]
        other = [kv for kv in items if kv[0] not in ENTITY_KEY_ORDER]
        known.sort(key=lambda kv: ENTITY_KEY_ORDER.index(kv[0]))
        sec[1] = known + other
    ini.sections.sort(key=lambda s: s[0].lower())
    ini.header = ENTITIES_HEADER
    ini.save(path)
    log("Entities.ini: %d sections" % len(ini.sections))


# =====================================================================================
# 4. Tiles.ini
# =====================================================================================
TILE_KEY_ORDER = ["Walkable.Data", "Show.Name", "Use.Words", "Examine.Info", "Line.of.Sight"]


def migrate_tiles():
    path = p("data", "Tiles.ini")
    ini = Ini(path)
    uses = {}
    for (name, kind), verbs in read_use_words().items():
        if kind == "Tile":
            uses.setdefault(name, []).extend(verbs)
    added = []
    for t in R.tiles:
        if ini.section(t) is None:
            added.append(t)
            ini.set(t, "Walkable.Data", "1" * 49)
        extra = []
        for (old, verbs) in uses.items():
            pat = old.replace("XXX", r"\d{3}")
            if re.fullmatch(pat, t) or R.name(old) == t:
                extra.extend(verbs)
        if extra:
            ini.set(t, "Use.Words", merge_words(ini.get(t, "Use.Words"), extra))
    for sec in ini.sections:
        items = [(k, v) for k, v in sec[1]]
        known = [kv for kv in items if kv[0] in TILE_KEY_ORDER]
        other = [kv for kv in items if kv[0] not in TILE_KEY_ORDER]
        known.sort(key=lambda kv: TILE_KEY_ORDER.index(kv[0]))
        sec[1] = known + other
    ini.sections.sort(key=lambda s: s[0].lower())
    ini.save(path)
    log("Tiles.ini: %d sections%s" % (len(ini.sections), (", added " + ", ".join(added)) if added else ""))


# =====================================================================================
# 5. ItemRacks.ini
# =====================================================================================
def migrate_itemracks():
    ini = Ini()
    ini.header = [
        "; Item racks (shops and crafting lists). See dev\\Data Formats.md.",
        "; Display.Item.Rack <ITEMRACK TYPE> <NPC NAME> <RACK ID> <GOTO LINE IF CANCELLED>; RACK ID is a section name here.",
        "; Shop:  Type=Shop, Buy.Rate (player pays Value*Buy.Rate), Sell.Rate (player receives Value*Sell.Rate), ItemN=Name,stock",
        "; Craft: Type=Craft, Skill=<skill>, ItemN=Product,ingredients (name qty pairs),xp gained",
    ]
    rack_dir = o("data", "ItemRack")
    for f in sorted(os.listdir(rack_dir)):
        stem = f[:-4]
        rows = read_tab_file(os.path.join(rack_dir, f))
        if stem.startswith("SHOP-"):
            sec = stem
            ini.set(sec, "Type", "Shop")
            ini.set(sec, "Buy.Rate", rows[0][0])
            ini.set(sec, "Sell.Rate", rows[0][1])
            for i, r in enumerate(rows[1:], 1):
                ini.set(sec, "Item%d" % i, "%s,%s" % (R.name(r[0]), r[1]))
        elif stem.startswith("CREATABLES-"):
            skill = stem.split("-", 1)[1]
            sec = "CRAFT-" + skill
            ini.set(sec, "Type", "Craft")
            ini.set(sec, "Skill", skill)
            if skill == "Smithing":
                # The old CREATABLES-Smithing.txt is a verbatim copy of the Cooking list (a Meat Sandwich
                # isn't smithed), so the Smithing rack is migrated empty.
                ini.section(sec)[1].append((None, "; (no recipes yet: the old file was a copy of CREATABLES-Cooking)"))
                continue
            for i, r in enumerate(rows, 1):
                # old: NN  Product  xp  "Ingredient qty Ingredient qty"
                ingr = r[3].split()
                ingr = " ".join(R.name(w) if k % 2 == 0 else w for k, w in enumerate(ingr))
                ini.set(sec, "Item%d" % i, "%s,%s,%s" % (R.name(r[1]), ingr, r[2]))
    ini.save(p("data", "ItemRacks.ini"))
    log("ItemRacks.ini: %s" % ", ".join(s[0] for s in ini.sections))


# =====================================================================================
# 6. Config.ini
# =====================================================================================
SKILLS_LIST = "Strength,Defence,Hitpoints,Cooking,Smithing,Fishing,Mining,Woodcutting,Firemaking"


def walkable_at(map_name, px, py, tiles_ini):
    """Is the player's feet point (X+15, Y+28, as the old game used) on a walkable sub-cell?"""
    fx, fy = px + 15, py + 28
    col, row = int(fx // 32), int(fy // 32)
    lines = read_lines(p("maps", map_name + ".txt"))
    cell = lines[row].split(":")[col]
    tile = cell.split("+")[0]
    data = tiles_ini.get(tile, "Walkable.Data", "1" * 49)
    sx, sy = int((fx % 32) * 7 // 32), int((fy % 32) * 7 // 32)
    return data[sy * 7 + sx] == "1", tile


def migrate_config():
    path = p("data", "Config.ini")
    lines = strip_trailing_blank(read_lines(path))
    # split into sections (keep raw lines)
    secs = [["", []]]
    for l in lines:
        s = l.strip()
        if s.startswith("[") and s.endswith("]"):
            secs.append([s[1:-1], []])
        else:
            secs[-1][1].append(l)

    def sec(name):
        for s in secs:
            if s[0].lower() == name.lower():
                return s
        s = [name, []]
        secs.append(s)
        return s

    def key_of(l):
        s = l.strip()
        if s.startswith(";") or "=" not in s:
            return None
        return s.split("=", 1)[0].strip()

    def has(s, key):
        return any((key_of(l) or "").lower() == key.lower() for l in s[1])

    def add(s, key, value):
        if has(s, key):
            return
        body = s[1]
        i = len(body)
        while i > 0 and body[i - 1].strip() == "":
            i -= 1
        body.insert(i, "%s=%s" % (key, value))

    dbg = sec("Debugging")
    dbg[1] = [l for l in dbg[1] if (key_of(l) or "").lower() != "fogofwar.enabled"]
    gp = sec("Gameplay")
    gp[1] = [l.replace("NPC.Repawn.Delay", "NPC.Respawn.Delay") for l in gp[1]]
    tiles_ini = Ini(p("data", "Tiles.ini"))
    start = (300, 300)
    ok, tile = walkable_at("1,1,0", start[0], start[1], tiles_ini)
    if not ok:
        raise SystemExit("Start position 300,300 on 1,1,0 is not walkable (%s)" % tile)
    add(gp, "Start.Map", "1,1,0")
    add(gp, "Start.X", str(start[0]))
    add(gp, "Start.Y", str(start[1]))
    add(sec("Skills"), "List", SKILLS_LIST)
    snd = sec("Sounds")
    add(snd, "Enabled", "1")
    add(snd, "Music", "TownTheme.ogg")

    out = []
    for name, body in secs:
        body = strip_trailing_blank(body)
        if name:
            out.append("[%s]" % name)
        out.extend(body)
        out.append("")
    write_lines(path, strip_trailing_blank(out))
    log("Config.ini: updated (start 1,1,0 at 300,300 on %s)" % tile)


# =====================================================================================
# 7. Saves
# =====================================================================================
def old_skills():
    return [l.strip().lstrip("#") for l in read_lines(o("data", "Misc", "Skills.txt")) if l.strip().startswith("#")]


def split2(s):
    return s.split("\t") if "\t" in s else s.split(",")


def num(s):
    try:
        v = float(s)
    except ValueError:
        return s
    return str(int(v)) if v == int(v) else ("%g" % v)


def convert_save(old_path, new_path, template=False):
    lines = [l.rstrip() for l in read_lines(old_path)]
    while lines and lines[-1] == "":
        lines.pop()
    i = 0
    map_name = lines[i].strip(); i += 1
    xy = split2(lines[i].strip()); i += 1
    # old order: skills line then explored line (TEMPLATE.txt has them swapped and comma separated)
    a, b = lines[i], lines[i + 1]; i += 2
    if re.match(r"^\s*[\d.]+([\t,][\d.]+)+\s*$", a):
        skills_line, explored = a, b
    else:
        skills_line, explored = b, a
    sk = split2(skills_line.strip())
    inv, bank, attrs = [], [], []
    while i < len(lines) and lines[i].strip() != "-":
        if lines[i].strip():
            inv.append(split2(lines[i].strip()))
        i += 1
    i += 1
    while i < len(lines) and lines[i].strip() != "-":
        if lines[i].strip():
            bank.append(split2(lines[i].strip()))
        i += 1
    i += 1
    while i < len(lines):
        if lines[i].strip():
            attrs.append(split2(lines[i].strip()))
        i += 1

    ini = Ini()
    ini.header = ["; Converted from the old saves\\%s by dev\\migrate\\migrate.py" % os.path.basename(old_path)]
    hp = num(sk[0])
    ini.set("Player", "Map", map_name)
    ini.set("Player", "X", str(int(round(float(xy[0])))))
    ini.set("Player", "Y", str(int(round(float(xy[1])))))
    ini.set("Player", "Hitpoints", hp)
    ini.set("Player", "Direction", "4")
    names = old_skills()
    vals = dict(zip(names, [num(v) for v in sk[1:]]))
    vals["Hitpoints"] = hp
    for s in SKILLS_LIST.split(","):
        ini.set("Skills", s, vals.get(s, "0"))
    ini.section("Inventory", create=True)
    for n, (name, q) in enumerate(inv, 1):
        ini.set("Inventory", "Slot%d" % n, "%s,%s" % (R.name(name), num(q)))
    ini.section("Bank", create=True)
    for n, (name, q) in enumerate(bank, 1):
        ini.set("Bank", "Slot%d" % n, "%s,%s" % (R.name(name), num(q)))
    ini.section("Attributes", create=True)
    for at in attrs:
        if template and at[0] == "Attribute":
            continue                     # format placeholder in TEMPLATE.txt
        ini.set("Attributes", at[0], at[1] if len(at) > 1 else "")
    ini.section("Explored", create=True)
    maps, cells = [], {}
    if explored.strip() != "Explored Map":
        for tok in explored.split():
            parts = tok.split(",")
            m = ",".join(parts[:3])
            if m not in maps:
                maps.append(m)
            if len(parts) > 3 and parts[3] != "X":
                cells.setdefault(m, set()).add(int(parts[3]))
            elif len(parts) > 3 and parts[3] == "X":
                cells[m] = None             # whole map revealed
        ini.set("Explored", "Maps", " ".join(maps))
        for m in maps:
            if cells.get(m):
                ini.set("Explored", m, " ".join(str(c) for c in sorted(cells[m])))
    else:
        ini.set("Explored", "Maps", "")
    ini.save(new_path)


def migrate_saves():
    convert_save(o("saves", "Kris.txt"), p("saves", "Kris.ini"))
    convert_save(o("saves", "TEMPLATE.txt"), p("saves", "TEMPLATE.ini"), template=True)
    log("Saves: Kris.ini, TEMPLATE.ini")


# =====================================================================================
# 8. Sounds
# =====================================================================================
def migrate_sounds():
    src, dst = o("sounds"), p("sounds")
    os.makedirs(dst, exist_ok=True)
    n = 0
    for f in sorted(os.listdir(src)):
        s, d = os.path.join(src, f), os.path.join(dst, f)
        if not os.path.exists(d) or os.path.getsize(d) != os.path.getsize(s):
            shutil.copy2(s, d)
        n += 1
    log("Sounds: %d files" % n)


# =====================================================================================
# 9. Minimap colours
# =====================================================================================
FIXED_COLOURS = {"Ladder001": (255, 0, 0), "Ladder002": (255, 0, 0), "Ladder003": (255, 0, 0)}  # ladders marked red, as before


def tile_colour(name):
    w, h, rows = read_bmp(p("sprites", "Tiles", name + ".bmp"))
    half = h // 2
    # Liberty BASIC sprite BMPs: the MASK is the visual top half (black = drawn, white = transparent)
    # and the IMAGE is the visual bottom half (checked: Grass001 top half is all black, Pine_Tree002's
    # top half is a black/white silhouette). Data Formats.md says the opposite; the files are the truth.
    mask, img = rows[:half], rows[half:]
    tot, n = [0, 0, 0], 0
    for y in range(half):
        for x in range(w):
            m = mask[y][x] if y < len(mask) else (0, 0, 0)
            if sum(m) < 384:               # black mask = drawn pixel
                c = img[y][x]
                tot[0] += c[0]; tot[1] += c[1]; tot[2] += c[2]; n += 1
    if n == 0:
        for y in range(half):
            for c in img[y]:
                tot[0] += c[0]; tot[1] += c[1]; tot[2] += c[2]; n += 1
    return tuple(int(round(t / n)) for t in tot)


def migrate_minimap():
    out = []
    for t in R.tiles:
        c = FIXED_COLOURS.get(t) or tile_colour(t)
        out.append("%s\t%d %d %d" % (t, c[0], c[1], c[2]))
    write_lines(p("dev", "Minimap Colours.txt"), out)
    log("Minimap Colours.txt: %d tiles" % len(out))


def main():
    renames = migrate_scripts()
    migrate_maps(renames)
    migrate_entities()
    migrate_tiles()
    migrate_itemracks()
    migrate_config()
    migrate_saves()
    migrate_sounds()
    migrate_minimap()
    print("Done.")


if __name__ == "__main__":
    main()
