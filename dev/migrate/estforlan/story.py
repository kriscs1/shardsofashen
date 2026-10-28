"""Everything outside the maps that the new mainland changes: the scripts that name a map that moved (its new name),
the entry scripts of moved maps (renamed), the pass's scripts (the barrier mirrored), the shardstones' travel scripts
(every settlement has one now), Quests.ini markers, WorldMap.ini, Waves.ini, Config.ini, Ambient.ini; and the old
towns' scripts nobody is left to use."""
import os
import re

import story_kit as K
from atlas import XT, YT, TW
import layout as L
import galaith as G

MAKER = "build_estforlan.py"
ISLE_LEVELS = {"0,0,10"}
MAP = re.compile(r"(?<![\d,.\-])(-?\d+,-?\d+,-?\d+)(?![\d,])")
SUPERSEDED = ("build_towns.py", "build_regions.py", "build_eastreach.py", "build_content.py", "build_galaith.py",
              "build_heir_mainland.py", "build_cinder.py", "build_palace.py", "build_walled.py", "build_smugglers.py",
              "build_town_life.py", "build_travel.py", "build_world.py", "build_scenery.py", "build_places.py",
              "build_omens.py", "build_estforlan.py")
TOWN_IDS = re.compile(r"^(Talk to|Read) [A-Z][A-Za-z]+_(Barkeep|Barmaid|Resident|Notice|Clerk|Doctor|Nurse|Carter|"
                      r"Baker|Butcher|Fishmonger|Greengrocer|Tailor|Cobbler|Armourer|Hotelier|Banker|Soldier|Stall|"
                      r"Sheriff|Constable|Speaker|Priest|Smith|Harbour_Master|Stall)_\d+$")


# ------------------------------------------------------------------ the maps' new names
def renames(homes, gate_map):
    """{old map: new map} for every map that moved (its place, its levels, its people)."""
    out = dict(homes)
    out.update(L.parts()["levels"])
    out.update({"10,6,0": G.PASS, "14,6,0": "0,12,0", "5,3,0": gate_map})
    return out


def chest_maps():
    """{old map: new map} for the chests: where each old map's chest was lifted to."""
    out = {}
    for part in L.parts()["parts"].values():
        if any(ln.split("\t")[:2] == ["StaticObject", "Chest"] for ln in part["lines"]):
            out[part["old"]] = part["new"]
    return out


def read(path):
    return open(path, "rb").read().decode("cp1252").replace("\r\n", "\n").split("\n")


def write(path, lines):
    while lines and lines[-1] == "":
        lines.pop()
    data = ("\r\n".join(lines) + "\r\n").encode("cp1252")
    if not os.path.exists(path) or open(path, "rb").read() != data:
        with open(path, "wb") as f:
            f.write(data)


def squares():
    """{settlement: the map its middle (<key>_Square) is on now}, from the maps as they are."""
    out = {}
    maps = os.path.join(K.ROOT, "maps")
    for f in os.listdir(maps):
        if f.endswith(",0.txt"):
            for ln in read(os.path.join(maps, f)):
                p = ln.split("\t")
                if p[0] == "Id" and len(p) > 1 and p[1].endswith("_Square") and p[1].count("_") == 1:
                    out[p[1][:-len("_Square")]] = f[:-4]
    return out


def moved_towns(before, plans):
    """{a settlement's middle's map before this build: after} for those that moved (their people's branches)."""
    return {before[k]: p.home_map() for k, p in plans.items() if k in before and before[k] != p.home_map()}


def people_branches(strays):
    """Talk to Settler / Trader / Guard: a branch for a map its people were on and aren't now (strays: {that map:
    theirs}) asks for theirs."""
    for name in ("Talk to Settler", "Talk to Trader", "Talk to Guard"):
        path = os.path.join(K.SCRIPTS, name + ".txt")
        lines = read(path)
        new = []
        for ln in lines:
            f = ln.split("\t")
            if len(f) > 2 and f[1] == ">On.Map" and f[2] in strays:
                f[2] = strays[f[2]]
            new.append("\t".join(f))
        if new != lines:
            write(path, new)


def remap_scripts(table, chests):
    """Every script naming a map that moved: its new name (chests: where that chest went)."""
    changed = 0
    for f in sorted(os.listdir(K.SCRIPTS)):
        path = os.path.join(K.SCRIPTS, f)
        lines = read(path)
        use = dict(table)
        if f.startswith("Open Chest"):
            use.update(chests)
        new = [MAP.sub(lambda mm: use.get(mm.group(1), mm.group(1)), ln) for ln in lines]
        if f == "Climb Up Mine_Ladder.txt":
            new = [ln.replace("672,344\t0,12,0", "%d,344\t0,12,0" % ((G.MINE[0] % XT + 1) * TW)) for ln in new]
        if new != lines:
            write(path, new)
            changed += 1
    return changed


ENTRY = {   # old entry script -> its new name (None: it goes), and lines changed in it
    "1,3,0": "4,4,0", "1,4,-1": "20,10,-1", "1,4,0": None, "1,9,-1": "3,16,-1", "1,9,0": "3,16,0",
    "2,3,0": "9,4,0", "2,4,-1": "21,10,-1", "2,4,-2": "21,10,-2", "2,4,-3": "21,10,-3", "2,4,0": "22,11,0",
    "2,4,1": "22,11,1", "3,3,0": "11,4,0", "3,4,0": None, "4,4,0": "18,5,0", "4,4,1": "18,5,1", "8,10,0": "22,20,0",
    "8,2,0": "23,4,0", "12,5,0": "-9,12,0", "10,6,0": None, "7,4,0": None,
}
ENTRY_WORDS = {"Ashford village. You smell fresh bread.": "Ashford. You smell fresh bread.",
               "The Royal Isle: the Wizards' Court.": "The Wizards' Court."}


def entry_scripts(plans, first, extra=None):
    """The entry scripts of moved maps under their new names (the first run: all read before any is written, as some
    new names are old ones); the rest of the old mainland's go."""
    keep = set()
    if first:
        old_ones = {}
        for old in ENTRY:
            src = os.path.join(K.SCRIPTS, old + ".txt")
            if os.path.exists(src):
                old_ones[old] = read(src)
                os.remove(src)
        for old, lines in old_ones.items():
            if ENTRY[old]:
                for a, b in ENTRY_WORDS.items():
                    lines = [ln.replace(a, b) for ln in lines]
                write(os.path.join(K.SCRIPTS, L.tname(ENTRY[old]) + ".txt"), lines)
    for f in os.listdir(K.SCRIPTS):                        # (old mainland maps' entry scripts left over)
        name = f[:-4]
        if MAP.fullmatch(name) and name not in keep and name not in (extra or {}) and name.split(",")[0:2] != ["0", "0"] and not isle(name) and \
                name not in (G.PASS,) and name not in ISLE_LEVELS and name not in {L.tname(v) for v in ENTRY.values() if v}:
            os.remove(os.path.join(K.SCRIPTS, f))
    arrive = {}
    for key, plan in plans.items():                        # a word on arriving in each settlement
        name = plan.home_map()
        if not os.path.exists(os.path.join(K.SCRIPTS, name + ".txt")) or name in (extra or {}):
            arrive[name] = [("Display.Message", "Cyan", ARRIVE.get(key, "%s." % plan.title), "-")]
    for name, rows in (extra or {}).items():               # (a quest's lines on a map: after its arrival words)
        K.write_script(name, arrive.pop(name, []) + rows, MAKER)
    for name, rows in arrive.items():
        K.write_script(name, rows, MAKER)


ARRIVE = {"Galaith": "Galaith, the royal city. Its white towers shine over the rooftops.",
          "Southport": "Northgate. Gulls wheel over the harbour.",
          "Keep": "King Rupert's Keep. The sea booms against the rocks below the walls.",
          "Court": "The Wizards' Court. The air tingles with magic.",
          "Fenwick": "Fenwick, on its boardwalks over the marsh.",
          "Ravensgate": "Ravensgate. Ravens croak from the rooftops.",
          "Highwatch": "Highwatch, high in the red hills.",
          "Frosthold": "Frosthold. Your breath steams in the cold.",
          "Wardhaven": "Wardhaven, on its island.",
          "Emberwatch": "Emberwatch, the last town before the Cinder Peaks. Smoke on the wind.",
          "Dunerest": "Dunerest, at the desert's edge.",
          "Saltmarsh": "Saltmarsh. The tide hisses in the reeds."}


def isle(name):
    x, y = name.split(",")[:2]
    return "%s,%s,0" % (x, y) in L.ISLE


# ------------------------------------------------------------------ the pass
def pass_scripts():
    px = (G.BARRIER_X - 1) * TW
    ys = [(y - 1) * TW for _, y in G.barrier_rows()]
    rows = [("Get.Value", "ATTRIBUTE", "GalaithQuest", "Variable.1$"), (">Conditional", "$Variable.1=0", "@end")]
    rows += [("Add.Entity", "%d,%d" % (px, y), "Barrier_Light", "StaticObject", "-") for y in ys]
    rows += [("@end",), ("End",)]
    K.write_script(G.PASS, rows, MAKER)
    K.write_script("Use Staff_of_Ashen With Barrier", [
        (">Distance.From.Clicked.Tile", "64", "@far"),
        ("Get.Value", "ATTRIBUTE", "GalaithQuest", "Variable.1$"),
        (">Conditional", "$Variable.1=0", "@broken"),
        (">Conditional", "$Attr.BarrierSpell>=1", "@words"),
        (">Conditional", "$Attr.ShardgateQuest>=5", "@anchored"),      # (its anchor in the Shardrealm cut first:
        (">Quest.Can.Start", "GalaithQuest", "@end"),                   #  The Shardgate, build_shardgate.py)
        ("Display.Message", "Cyan", "You hold the Staff of Ashen to the barrier and speak Bert's words of "
                                    "Unbinding..", "-"),
        ("Play.Sound", "SpellCast"),
        ("Wait", "2")] + [("Remove.Entity", "%d,%d" % (px, y), "Barrier_Light") for y in ys] + [
        ("Play.Sound", "Thunder"),
        ("Update.Attribute", "GalaithQuest", "=1"),
        ("Display.Message", "Yellow", "..and the barrier shatters like glass. Beyond it, on the scorched ground before "
                                      "Galaith's black walls, something huge lifts its head.", "-"),
        ("End",),
        ("@words",), ("Display.Refusal", "The staff hums against the barrier, but you don't know the words."),
        ("End",),
        ("@anchored",),
        ("Display.Message", "Cyan", "You hold the Staff of Ashen to the barrier and speak Bert's words of "
                                    "Unbinding..", "-"),
        ("Play.Sound", "SpellCast"),
        ("Wait", "2"),
        ("Display.Message", "DarkRed", "..and the barrier flares, shudders, and holds. Something beyond the world is "
                                       "feeding it.", "Fail"),
        (">Conditional", "$Attr.ShardgateQuest=0", "@end"),
        (">Quest.Can.Start", "ShardgateQuest", "@end"),
        ("Update.Attribute", "ShardgateQuest", "=1"),
        ("Display.Message", "Yellow", "Quest started: The Shardgate.", "Quest"),
        ("End",),
        ("@broken",), ("Display.Message", "Cyan", "The barrier is broken.", "-"),
        ("@end",), ("End",),
        ("@far",), ("Display.Message", "DarkRed", "You are too far away!", "Denied"), ("End",)], MAKER)


def wardhaven_guard():
    K.write_script("Wardhaven Guard", [
        (">Conditional", "$Attr.GalaithQuest>=2", "@shut"),
        K.say("Guard", "The dragon of Galaith is dead! Welcome to Wardhaven. The gates are open, and they're staying "
                       "open.", ("Thank you.", "@end")),
        ("End",),
        ("@shut",),
        K.say("Guard", "Halt! Wardhaven's gates have been barred since the dragon came down on Galaith, and they stay "
                       "barred while it lives.\\Until then: off you go.", ("Goodbye.", "@end")),
        ("@end",), ("End",)], MAKER)


# ------------------------------------------------------------------ shardstones
WEST = ["Southport", "Ashford", "Wardhaven", "Oakhollow", "Wildwood", "Moorcross", "Galaith", "Fenwick", "Dunerest",
        "Saltmarsh"]
EAST = ["Court", "Emberwatch", "Thornwick", "Keep", "Ravensgate", "Highwatch", "Frosthold"]


def shardstones(atlas, plans):
    """Travel Shardstone (which shardstone is this? wake it, the first time, with Shards - Config.ini [Shards]
    Shardstone.<Key>, else Shardstone - and so attune to it) and its menu, two pages (the west and the east). A journey
    costs Shardstone.Travel (a few Shards)."""
    where = {}
    for name, m in atlas.maps.items():
        for ln in m.ents:
            f = ln.split("\t")
            if f[0] == "Id" and f[1].startswith("Waystone_"):
                where[f[1][len("Waystone_"):]] = name
    keys = [k for k in WEST + EAST if k in where]
    halves = [keys[:9], keys[9:]]
    for n, half in enumerate(halves):
        rows = [(">Distance.From.Clicked.Entity", "48", "@far")] if n == 0 else []
        for i, k in enumerate(half):
            label = short(plans[k].title)
            rows += [(">On.Map", where[k], "@next%d" % i),
                     ("Get.Value", "CALCULATION", label.replace(" ", "_"), "Variable.9$"),
                     (">Conditional", "$Attr.Waystone.%s=0" % k, "@menu"),
                     K.say("Shardstone", "The %s shardstone's rune is dark. Waking it takes $Shards.Shardstone.%s Shards, "
                                       "and you carry $Item.Shard.\\Once it's awake it knows you: you can travel to it "
                                       "from any shardstone you've woken." % (label, k),
                           ("Wake it ($Shards.Shardstone.%s Shards)" % k, "@wake%d" % i), ("Not now", "@leave")),
                     ("@wake%d" % i,),
                     (">Pay.Shards", "Shardstone." + k, "Waking_the_shardstone", "@leave"),
                     ("Update.Attribute", "Waystone." + k, "=1"),
                     ("Display.Message", "Yellow", "The rune drinks the Shards and flares blue: you are attuned to "
                                                   "the %s shardstone." % label),
                     ("Goto.Line", "@attuned"),
                     ("@next%d" % i,)]
        if n == 0:
            rows += [("Goto.Script", "Travel Shardstone 2"), ("@attuned",), ("Play.Sound", "SpellCast"),
                     ("Play.Animation", "Teleport_Glow", "1", "-"),
                     ("@menu",), ("Goto.Script", "Shardstone Menu"), ("End",), ("@leave",), ("End",),
                     ("@far",), ("Display.Message", "DarkRed", "You are too far away!", "Denied"), ("End",)]
            K.write_script("Travel Shardstone", rows, MAKER)
        else:
            rows += [("Get.Value", "CALCULATION", "old", "Variable.9$"), ("Goto.Line", "@menu"),
                     ("@attuned",), ("Play.Sound", "SpellCast"), ("Play.Animation", "Teleport_Glow", "1", "-"),
                     ("@menu",), ("Goto.Script", "Shardstone Menu"), ("End",), ("@leave",), ("End",)]
            K.write_script("Travel Shardstone 2", rows, MAKER)
    pages = [("Shardstone Menu", [k for k in WEST if k in where], "The east...", "Shardstone Menu 2"),
             ("Shardstone Menu 2", [k for k in EAST if k in where], "The west...", "Shardstone Menu")]
    for script, page, other, other_script in pages:
        answers = []
        for k in page:
            answers += ["%s [if $Attr.Waystone.%s>=1 and $Map.Name<>%s]" % (plans[k].title, k, where[k]), "@go_" + k]
        answers += [other, "@other", "Stay here", "@stay"]
        rows = [("Display.Conversation", "Shardstone",
                 "This is the $Variable.9 shardstone. Its rune glows softly under your hand.\\Where would you like to go? "
                 "Each journey costs $Shards.Shardstone.Travel Shards, and you carry $Item.Shard. (Only the shardstones "
                 "you have woken are listed.)") + tuple(answers),
                ("@stay",), ("End",), ("@other",), ("Goto.Script", other_script), ("End",)]
        for k in page:
            rows += [("@go_" + k,), (">Pay.Shards", "Shardstone.Travel", "Travelling", "@stay"),
                     ("Play.Sound", "Teleporter"),
                     ("Display.Message", "Yellow", "The world blurs... and you step out by the %s shardstone."
                      % short(plans[k].title)),
                     ("Teleport", "Waystone_" + k, "-"), ("End",)]
        K.write_script(script, rows, MAKER)
    return keys


def short(title):
    return title.replace("the ", "").replace("The ", "")


# ------------------------------------------------------------------ the world stretched (layout.INSERT_COLS, _ROWS)
STRETCHED = os.path.join(L.PARTS, "stretched.txt")
STRETCH_FILES = ("Quests.ini", "WorldMap.ini", "Waves.ini", "Config.ini", "Ambient.ini")


def stretch_names():
    """Once, when layout's stretch is new: every map name in the scripts, the data and the tests -> its name now (a
    script named after a map renamed too). All read before any is written: some new names are old ones."""
    spec = "cols %s rows %s" % (L.INSERT_COLS, L.INSERT_ROWS)
    if os.path.exists(STRETCHED) and open(STRETCHED).read().strip() == spec:
        return 0

    def name(mm):
        x, y, z = (int(v) for v in mm.group(1).split(","))
        if not (-3 <= z <= 1 and x < 25 and y < 22) or isle(mm.group(1)):
            return mm.group(1)
        return L.tname(mm.group(1))
    files = {os.path.join(K.SCRIPTS, f): f for f in os.listdir(K.SCRIPTS)}
    files.update({os.path.join(K.DATA, f): f for f in STRETCH_FILES})
    tests = os.path.join(K.ROOT, "tests", "test_engine.py")
    read_all = {p: read(p) for p in files}
    for p in files:
        if MAP.fullmatch(files[p][:-4]):
            os.remove(p)                                   # (a map's own script: written again under its new name)
    changed = 0
    for p, lines in read_all.items():
        new = [MAP.sub(name, ln) for ln in lines]
        f = files[p]
        if MAP.fullmatch(f[:-4]):
            p = os.path.join(K.SCRIPTS, MAP.sub(name, f[:-4]) + ".txt")
        if new != lines or not os.path.exists(p):
            write(p, new)
            changed += 1
    text = open(tests, encoding="utf-8").read()
    text = re.sub(r'"(-?\d+,-?\d+,-?\d+)"', lambda mm: '"%s"' % name(mm), text)
    open(tests, "w", encoding="utf-8").write(text)
    with open(STRETCHED, "w") as fh:
        fh.write(spec + "\n")
    return changed


# ------------------------------------------------------------------ Galaith moved west of the West Range
GALAITH_MOVED = os.path.join(L.PARTS, "galaith_west.txt")
GALAITH_NAMES = {"2,14,0": "-9,14,0", "0,14,0": "-11,14,0", "0,14,-1": "-11,14,-1", "11,14,0": "0,14,0",
                 "8,14,0": "-3,14,0", "9,15,0": "-2,15,0"}    # (the palace, the mine, its level, the pass, the field)


def galaith_west_names():
    """Once: the scripts, data and tests that name Galaith's maps from before it moved west name its maps now (all
    read before any is written: the pass now has the old mine's name)."""
    if os.path.exists(GALAITH_MOVED):
        return 0
    swap = lambda mm: GALAITH_NAMES.get(mm.group(1), mm.group(1))      # noqa: E731
    files = {os.path.join(K.SCRIPTS, f): f for f in os.listdir(K.SCRIPTS)}
    files.update({os.path.join(K.DATA, f): f for f in STRETCH_FILES})
    read_all = {p: read(p) for p in files}
    for p in files:
        if files[p][:-4] in GALAITH_NAMES:
            os.remove(p)
    changed = 0
    for p, lines in read_all.items():
        new = [MAP.sub(swap, ln) for ln in lines]
        name = files[p][:-4]
        if name in GALAITH_NAMES:
            p = os.path.join(K.SCRIPTS, GALAITH_NAMES[name] + ".txt")
        if new != lines or not os.path.exists(p):
            write(p, new)
            changed += 1
    tests = os.path.join(K.ROOT, "tests", "test_engine.py")
    text = open(tests, encoding="utf-8").read()
    text = re.sub(r'"(-?\d+,-?\d+,-?\d+)"', lambda mm: '"%s"' % swap(mm), text)
    open(tests, "w", encoding="utf-8").write(text)
    with open(GALAITH_MOVED, "w") as fh:
        fh.write("moved\n")
    return changed


# ------------------------------------------------------------------ the data files
def quests(table, rehoused):
    """Quests.ini markers: a map and tile on a map that moved -> its new map (a lifted place: the same tile), or the
    person who stood there (rehoused: their place's name)."""
    lines = read(K.QUESTS)
    out = []
    lifted = {p["old"]: p for p in L.parts()["parts"].values()}
    for ln in lines:
        m = re.match(r"^(Marker\d+)=(.*)$", ln)
        if m:
            marks = []
            for mark in m.group(2).split(";"):
                f = mark.split()
                if len(f) == 3 and MAP.fullmatch(f[0]):
                    old, tx, ty = f[0], int(f[1]), int(f[2])
                    part = lifted.get(old)
                    if part and any(x1 <= tx <= x2 and y1 <= ty <= y2 for x1, y1, x2, y2 in part["rects"]):
                        mark = "%s %d %d" % (part["new"], tx, ty)
                    elif old in rehoused:
                        near = min(rehoused[old], key=lambda r: abs(r[0] - tx) + abs(r[1] - ty))
                        mark = near[2]
                    elif old in table:
                        mark = "%s %d %d" % (table[old], tx, ty)
                marks.append(mark)
            ln = "%s=%s" % (m.group(1), ";".join(marks))
        out.append(ln)
    write(K.QUESTS, out)


def world_map(plans):
    lines = read(K.WORLDMAP)
    towns = {"Northgate": "Southport", "Ashford": "Ashford", "Oakhollow": "Oakhollow", "Fenwick": "Fenwick",
             "Moorcross": "Moorcross", "Highwatch": "Highwatch", "Frosthold": "Frosthold", "Dunerest": "Dunerest",
             "Emberwatch": "Emberwatch", "Thornwick": "Thornwick", "Ravensgate": "Ravensgate",
             "Wizards' Court": "Court", "King Rupert's Keep": "Keep", "Wildwood": "Wildwood",
             "Saltmarsh": "Saltmarsh", "Galaith": "Galaith", "Wardhaven": "Wardhaven"}
    regions = {"Sunscar Desert": "1,17,0 12 10", "Saltmarsh Fens": "6,18,0 12 10", "Cinder Peaks": "20,6,0 12 10",
               "Frostpeak": "13,19,0 12 6", "The Pass of Galaith": "0,12,0 12 4", "The Wildwood": "3,7,0 12 10",
               "Greymoor": "12,9,0 12 10", "The Redrock Hills": "11,14,0 12 10", "The Elderwood": "17,8,0 12 10",
               "The Ashwold": "22,4,0 6 10", "The Downs": "19,15,0 12 10", "The West Range": "0,9,0 12 10"}
    regions = {k: "%s %s" % (L.tname(v.split()[0]), " ".join(v.split()[1:])) for k, v in regions.items()}
    out, section = [], None
    for ln in lines:
        m = re.match(r"^\[(\w+)\]$", ln)
        if m:
            section = m.group(1)
            out.append(ln)
            if section == "Towns":
                out += ["%s=%s_Square" % (label, key) for label, key in towns.items() if key in plans]
                out.append("Isle Village=1,1,0 13 15")
            elif section == "Regions":
                out.append("The Isle=2,1,0 3 4")
                out += ["%s=%s" % kv for kv in regions.items()]
            continue
        if section in ("Towns", "Regions") and "=" in ln and not ln.startswith(";"):
            continue
        if section == "Places" and ln.startswith("Smugglers' Tunnel="):
            ln = "Smugglers' Tunnel=%s 18 15" % L.tname("13,4,-1")
        out.append(ln)
    write(K.WORLDMAP, out)


def waves(plans):
    lines = read(os.path.join(K.DATA, "Waves.ini"))
    section, out = None, []
    for ln in lines:
        m = re.match(r"^\[(\w+)\]$", ln)
        if m:
            section = m.group(1)
        elif section == "Ashford_Raid" and ln.startswith("Map="):
            ln = "Map=" + plans["Ashford"].atlas.at(*plans["Ashford"].centre)[0].name
        elif section == "Ashford_Raid" and ln.startswith("Centre="):
            ln = "Centre=Ashford_Square"
        elif section == "Farm_Raid" and ln.startswith("Map="):
            ln = "Map=" + L.tname("11,4,0")
        out.append(ln)
    write(os.path.join(K.DATA, "Waves.ini"), out)


DIGGING = {"Saltmarsh": "6-10,16-20,0", "Sunscar_Desert": "1-5,16-19,0", "Cinder_Peaks": "19-23,4-8,0",
           "Frostpeak": "11-15,16-19,0", "Dragon_Island": "22,20,0"}


def block(spec):
    """A Digging.ini block (x1-x2,y1-y2,z) of the plan as first drawn -> now."""
    xs, ys, z = spec.split(",")
    x = [L.tx(int(v)) for v in xs.split("-")]
    y = [L.ty(int(v)) for v in ys.split("-")]
    return "%s,%s,%s" % ("-".join(map(str, x)), "-".join(map(str, y)), z)


def digging():
    """Digging.ini's parts of the world: the new mainland's lands."""
    path = os.path.join(K.DATA, "Digging.ini")
    section, out = None, []
    for ln in read(path):
        m = re.match(r"^\[Finds\.(\w+)\]$", ln)
        if m:
            section = m.group(1)
        elif ln.startswith("[") or not ln.strip():
            section = section if not ln.startswith("[") else None
        if ln.startswith("Maps=") and section in DIGGING:
            ln = "Maps=" + block(DIGGING[section])
        out.append(ln)
    write(path, out)


def config():
    lines = read(K.CONFIG)
    write(K.CONFIG, [("Return.Map=9,4,0" if ln.startswith("Return.Map=") else ln) for ln in lines])


def ambient(sounds, levels):
    path = os.path.join(K.DATA, "Ambient.ini")
    lines = read(path)
    head = []
    for ln in lines:
        head.append(ln)
        if ln == "[Maps]":
            break
    kept = [ln for ln in lines[len(head):] if "=" in ln and isle(ln.split("=")[0])]
    new = ["%s=%s" % (n, s) for n, s in sounds.items()]
    new += ["%s=%s" % (n, "Cave" if n.split(",")[2].startswith("-") else "Indoors") for n in levels]
    write(path, head + sorted(set(kept + new), key=lambda s: [int(v) for v in s.split("=")[0].split(",")]))


# ------------------------------------------------------------------ what's left over
def present_ids():
    ids = set()
    for f in os.listdir(os.path.join(K.ROOT, "maps")):
        if not f.endswith(".txt"):
            continue
        for ln in read(os.path.join(K.ROOT, "maps", f)):
            if "Id=" in ln:
                ids.add(ln.split("Id=")[1].split()[0])
            f2 = ln.split("\t")
            if f2[0] == "Id" and len(f2) > 1:
                ids.add(f2[1])
    return ids


def orphans():
    """The old towns' people's and notices' scripts with nobody left to use them (only scripts the old builders made,
    and only when nothing on any map has that Id)."""
    ids = present_ids()
    gone = []
    for f in sorted(os.listdir(K.SCRIPTS)):
        name = f[:-4]
        if not name.startswith(("Talk to ", "Read ")):
            continue
        target = name.split(" ", 2)[2] if name.startswith("Talk to ") else name.split(" ", 1)[1]
        if target in ids:
            continue
        first = read(os.path.join(K.SCRIPTS, f))[0]
        if not any(b in first for b in SUPERSEDED):
            continue
        if not (TOWN_IDS.match(name) or name.startswith("Read ") or re.match(r"^Talk to Market_Vendor_\d+$", name)):
            continue
        if "_" not in target and target not in ("Ashford", "Southport", "Oakhollow", "Fenwick", "Moorcross",
                                                "Highwatch", "Frosthold", "Dunerest", "Emberwatch", "Thornwick",
                                                "Ravensgate", "Wardhaven"):
            continue
        os.remove(os.path.join(K.SCRIPTS, f))
        gone.append(name)
    return gone
