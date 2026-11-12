"""Fenwick, Highwatch and Ravensgate taken off the map (the owner's wish), their quests moved to towns that stay.

  * Each town's streets, houses, stalls, people, notices and shardstone are gone and the ground they stood on is wild
    again (as the wild round it: marsh in the fens, grass on the hills); the levels over and under its houses go too.
    The roads that ran into it are joined up again across the ground it stood on.
  * Kept: Fenwick's cathedral (empty now: build_manors.py makes it the Drowned Abbey), Ravensgate's graves and its
    Gravekeeper (move_keep.py gives them to King Rupert's Keep, which takes Ravensgate's place), the secrets by each
    square (where they were: in the wild now, so the count of them all still holds), and Captain Rook on his shore.
  * The quests: Morwen the witch and Elder Pike (Bog Lights, Old Hob) to Saltmarsh, in the same fens; Granny Bramble
    and her market rats (the Practice Hex) to Thornwick's green; Captain Hale (Bandits on the Road) to Frosthold, on
    the Redrock road; the Barrow King's Gravekeeper to the Keep. Their words, markers and notes say so.
  * Everything that named them: the shardstones (Shardstones.ini), the world map, the traders' wares, the towns' own
    scripts, the signposts (refresh_signposts.py), the tests.

Run it once (a second run finds the towns gone and stops).

  python -I "dev\\migrate\\remove_towns.py"
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import world_edit as W                                   # noqa: E402
from world_edit import XT, YT, TW                       # noqa: E402
import story_kit as SK                                   # noqa: E402

ROOT = W.ROOT
DATA = os.path.join(ROOT, "data")
MAKER = "remove_towns.py"
DONE = os.path.join(HERE, ".towns_removed")

TOWNS = {   # name: the world cells it covered (x1, y1, x2, y2), its buildings kept (by an Id in them)
    "Fenwick": dict(box=(163, 322, 263, 390), keep=("Fenwick_Cathedral",)),
    "Highwatch": dict(box=(370, 302, 442, 357), keep=()),
    "Ravensgate": dict(box=(612, 344, 701, 413), keep=()),
}
KEPT = re.compile(r"^(Grave_|Secret_|Ravensgate_Gravekeeper$|Captain_Rook|Rooks_Pier$|Fenwick_Cathedral$)")
MOVED = {   # an NPC (its kind on the map, and the town it was in): to the place it goes, its new Id, its roam
    ("Witch", "Fenwick"): ("Saltmarsh_Square", None, 3),
    ("Elder", "Fenwick"): ("Saltmarsh_Square", "Saltmarsh_Elder", 3),
    ("Old_Woman", "Fenwick"): ("Thornwick_Square", None, 0),
    ("Captain", "Highwatch"): ("Frosthold_Square", "Frosthold_Captain", 3),
    ("Gravekeeper", "Ravensgate"): (None, None, 0),               # (stays: move_keep.py)
}
RENAMED_IDS = {"Fenwick_Elder": "Saltmarsh_Elder", "Highwatch_Captain": "Frosthold_Captain",
               "Ravensgate_Gravekeeper": "Keep_Gravekeeper"}


# ================================================================== the buildings kept
def block_of(w, pid):
    """The cells of the building an Id stands in or at: its roof's cells (joined), and a cell round them."""
    _, c = w.find_id(pid)
    roofed = lambda q: w.cell(*q) is not None and "Roof(" in w.cell(*q)       # noqa: E731
    start = next((q for r in range(0, 5) for q in ((c[0] + dx, c[1] + dy) for dx in range(-r, r + 1)
                                                    for dy in range(-r, r + 1)) if roofed(q)), None)
    seen, todo = set(), [start]
    while todo:
        q = todo.pop()
        if q in seen or not roofed(q):
            continue
        seen.add(q)
        todo += [(q[0] + dx, q[1] + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)]
    xs, ys = [q[0] for q in seen], [q[1] for q in seen]
    return {(x, y) for x in range(min(xs) - 1, max(xs) + 2) for y in range(min(ys) - 1, max(ys) + 2)}


# ================================================================== the levels over and under
def clear_levels(gone):
    """The cells over and under the town's (its upstairs and cellars) made black; a level left with nothing goes."""
    n = 0
    for (mx, my, mz) in W.all_levels():
        if mz == 0 or mz >= 10 or mz <= -9:
            continue
        here = [(x, y) for x in range(XT) for y in range(YT) if (mx * XT + x, my * YT + y) in gone]
        if not here:
            continue
        m = W.Map(W.mname(mx, my, mz))
        for x, y in here:
            m.rows[y][x] = "Black001"
        m.ents = [ln for ln in m.ents if (lambda c: c is None or c not in gone)(W.line_cell(ln, mx, my))]
        if all(t == "Black001" for row in m.rows for t in row) and not m.ents:
            os.remove(m.path)
            n += 1
        else:
            m.save()
    return n


# ================================================================== a town, gone
def remove(w, town, spec, report):
    box = spec["box"]
    x1, y1, x2, y2 = box
    kept = set()
    for pid in spec["keep"]:
        kept |= block_of(w, pid)
    for m, ln, c in w.lines(box):
        if KEPT.match(W.line_id(ln)) and ln.startswith("Id\t"):
            kept.add(c)                                        # (a grave's tile)
    if town == "Ravensgate":                                   # (its port: the Keep's now)
        kept |= {(x, y) for x in range(690, 702) for y in range(362, 372)
                 if w.tile(x, y) in ("Boardwalk001", "Plank001")}
    gone = {(x, y) for x in range(x1, x2 + 1) for y in range(y1, y2 + 1)
            if w.cell(x, y) is not None and not W.natural(w.cell(x, y)) and (x, y) not in kept}
    near_gone = {(c[0] + dx, c[1] + dy) for c in gone for dx in (-1, 0, 1) for dy in (-1, 0, 1)}
    movers, removed_ids = [], set()
    for m, ln, c in w.lines(box):
        p = ln.split("\t")
        pid = W.line_id(ln)
        if KEPT.match(pid) or c in kept and not pid.startswith(town + "_"):
            continue
        if p[0] == "NPC" and (p[1], town) in MOVED:
            if MOVED[(p[1], town)][0] is not None:
                movers.append((p[1], town, m, ln, c))
                w.drop(m, ln)
            continue
        if p[0] == "StaticObject" and p[1] == "Moored_Boat" and c not in near_gone:
            continue
        mine = pid.startswith(town + "_") or "Name=%s" % town in ln
        on = c in near_gone
        pet = p[0] == "NPC" and "Attitude=Good" in ln and ("Zone=" in ln or "Stand=1" in ln)
        if mine or on or pet or p[0] in ("Id", "Lock", "Trigger") and c in gone:
            w.drop(m, ln)
            if pid:
                removed_ids.add(pid)
    ends = W.road_ends(w, box, gone)
    w.rewild(gone, seed=town)
    n = W.join_roads(w, ends)
    report.append("%s: %d cells wild again, %d things gone, %d roads joined up, %d kept cells" %
                  (town, len(gone), len(removed_ids), n, len(kept)))
    return gone, movers, removed_ids


# ================================================================== the quest folk, moved
def free_near(w, c, taken, r_min=2, r_max=9, edge=1):
    """A free open cell near c on c's own map (not on its outer rows)."""
    for r in range(r_min, r_max + 1):
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                q = (c[0] + dx, c[1] + dy)
                if max(abs(dx), abs(dy)) != r or q in taken or q[0] // XT != c[0] // XT or q[1] // YT != c[1] // YT:
                    continue
                lx, ly = q[0] % XT, q[1] % YT
                if not (edge <= lx < XT - edge and edge <= ly < YT - edge):
                    continue
                text = w.cell(*q)
                t, over = W.parts(text)
                if over.get("Roof") or over.get("Decor") and not over["Decor"].startswith(("Flowers", "Tall_Grass",
                                                                                          "Pebbles")):
                    continue
                if t in ("Grass001", "Dirt001", "Sand001", "Snow001", "Marsh001", "Gravel001", "Cobble001",
                         "Flagstone001", "Boardwalk001"):
                    if not any(W.line_cell(ln, q[0] // XT, q[1] // YT) == q for ln in w.maps[(q[0] // XT, q[1] // YT)].ents):
                        return q
    return None


def move_folk(w, movers):
    taken = set()
    placed = {}
    for kind, town, m, ln, c in movers:
        place, new_id, roam = MOVED[(kind, town)]
        _, sq = w.find_id(place)
        spot = free_near(w, sq, taken, 2, 9)
        taken |= {(spot[0] + dx, spot[1] + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)}
        p = ln.split("\t")
        opts = re.sub(r"\b(Zone|Chase)=\S+", "", p[4] if len(p) > 4 else "").strip()
        if roam:
            opts += " Zone=%s" % w.zone(spot[0] - roam, spot[1] - roam, spot[0] + roam, spot[1] + roam, *spot)
        tm = w.place(spot[0], spot[1], "NPC", kind, " ".join(opts.split()), dy=-8)
        if new_id:
            w.place_id(spot[0], spot[1], new_id)
        placed[kind] = (tm, spot)
    return placed


def granny_rats(w, spot):
    """Granny Bramble's four market rats: on open ground round her new spot, on her map (pixels on it)."""
    taken = {spot}
    out, tiles = [], []
    for k in range(4):
        q = free_near(w, spot, taken, 3 + k, 9)
        taken |= {(q[0] + dx, q[1] + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)}
        out.append(((q[0] % XT) * TW, (q[1] % YT) * TW - 8))
        tiles.append((q[0] % XT + 1, q[1] % YT + 1))
    path = os.path.join(W.SCRIPTS, "Talk to Granny_Bramble.script")
    s = W.read(path)
    old = re.findall(r"\tAdd\.Entity\t(-?\d+,-?\d+)\tRat\t", s)
    for (a, (px, py)) in zip(old, out):
        s = s.replace("\tAdd.Entity\t%s\tRat\t" % a, "\tAdd.Entity\t%d,%d\tRat\t" % (px, py), 1)
    W.write(path, s)
    p = os.path.join(HERE, "build_tricks.py")
    t = open(p, encoding="utf-8").read()
    t = re.sub(r"RATS = \[[^\]]*\]", "RATS = [%s]" % ", ".join("(%d, %d)" % xy for xy in tiles), t, count=1)
    t = re.sub(r'MARKET, GRANNY = "[^"]*", \(\d+, \d+\)', 'MARKET, GRANNY = "%d,%d,0", (%d, %d)' % (
        spot[0] // XT, spot[1] // YT, spot[0] % XT + 1, spot[1] % YT + 1), t, count=1)
    open(p, "w", encoding="utf-8", newline="\n").write(t)


# ================================================================== the words
WORDS = [   # (file, old, new): every line that named them
    ("Quests.ini", "Speak to Old Morwen the witch in Fenwick, in the Saltmarsh.",
     "Speak to Old Morwen the witch in Saltmarsh, in the fens."),
    ("Quests.ini", "Gather 4 bog myrtle in the Saltmarsh", "Gather 4 bog myrtle in the fens"),
    ("Quests.ini", "Take Morwen's brew to Elder Pike in Fenwick.", "Take Morwen's brew to Elder Pike in Saltmarsh."),
    ("Quests.ini", "Marker1=Fenwick_Square", "Marker1=Saltmarsh_Square"),
    ("Quests.ini", "Marker2=Fenwick_Elder", "Marker2=Saltmarsh_Elder"),
    ("Quests.ini", "Marker3=Fenwick_Square", "Marker3=Saltmarsh_Square"),
    ("Quests.ini", "Speak to Captain Hale in Highwatch, the hill fort on the Redrock road.",
     "Speak to Captain Hale in Frosthold, on the Redrock road."),
    ("Quests.ini", "Bring the stolen goods to Captain Hale in Highwatch.",
     "Bring the stolen goods to Captain Hale in Frosthold."),
    ("Quests.ini", "Marker1=Highwatch_Square", "Marker1=Frosthold_Square"),
    ("Quests.ini", "Marker3=Highwatch_Square", "Marker3=Frosthold_Square"),
    ("Quests.ini", "Marker0=Highwatch_Captain", "Marker0=Frosthold_Captain"),
    ("Quests.ini", "Speak to the Gravekeeper in Ravensgate, on the Barrowdowns.",
     "Speak to the Gravekeeper at King Rupert's Keep, on the Barrowdowns."),
    ("Quests.ini", "Find the old king's barrow, out on the downs east of Ravensgate.",
     "Find the old king's barrow, out on the downs west of King Rupert's Keep."),
    ("Quests.ini", "Return to the Gravekeeper in Ravensgate.", "Return to the Gravekeeper at King Rupert's Keep."),
    ("Quests.ini", "Marker3=Ravensgate_Square", "Marker3=Keep_Square"),
    ("Quests.ini", "Marker0=Ravensgate_Gravekeeper", "Marker0=Keep_Gravekeeper"),
    ("Quests.ini", "Ask Morwen the witch in Fenwick for a cure.", "Ask Morwen the witch in Saltmarsh for a cure."),
    ("Quests.ini", "on the shore east of Ravensgate.", "on the shore below King Rupert's Keep."),
    ("Quests.ini", "An old woman at Fenwick's market is looking for someone to practise a hex on.",
     "An old woman on Thornwick's green is looking for someone to practise a hex on."),
    ("Quests.ini", "Clear the rats round Fenwick's market anyway", "Clear the rats round Thornwick's green anyway"),
    ("Entities.ini", "Elder Pike of Fenwick.", "Elder Pike of Saltmarsh."),
    ("Entities.ini", "Captain Hale of Highwatch, in battered armour.", "Captain Hale of the Redrock road, in battered "
                                                                       "armour."),
    ("Entities.ini", "A sack of goods the bandits stole from Highwatch.", "A sack of goods the bandits stole on the "
                                                                          "Redrock road."),
    ("Entities.ini", "The Gravekeeper of Ravensgate.", "The Gravekeeper of the Barrowdowns."),
    ("Scripts/Barrow Door.script", "out on the downs east of Ravensgate", "out on the downs west of King Rupert's Keep"),
    ("Scripts/Talk to Gravekeeper.script", "out on the downs east of Ravensgate", "out on the downs west of King "
                                                                               "Rupert's Keep"),
    ("Scripts/Talk to Gravekeeper.script", "His barrow is out on the downs, east of Ravensgate.",
     "His barrow is out on the downs, west of the Keep."),
    ("Scripts/Talk to Gravekeeper.script", "East, on the open downs.", "West, on the open downs."),
    ("Scripts/Talk to Gravekeeper.script", "Ravensgate will sleep tonight.", "The Keep will sleep tonight."),
    ("Scripts/Examine Grave_Osric_Raven.script", "first gravekeeper of Ravensgate", "first gravekeeper of the "
                                                                                  "Barrowdowns"),
    ("Scripts/Examine Grave_Raven_Mark.script", "Ravensgate's mark, very old.", "the mark of Ravensgate, a town "
                                                                             "long gone."),
    ("Scripts/Kill Bandit.script", "Report to Captain Hale in Highwatch.", "Report to Captain Hale in Frosthold."),
    ("Scripts/Kill Barrow_King.script", "Return to the Gravekeeper in Ravensgate.", "Return to the Gravekeeper at "
                                                                                 "King Rupert's Keep."),
    ("Scripts/Read Hobs_Diary.script", "fetch Morwen in Fenwick.", "fetch Morwen in Saltmarsh."),
    ("Scripts/Read Hobs_Diary.script", "Morwen the witch lives in Fenwick, in the Saltmarsh south of Oakhollow.",
     "Morwen the witch lives in Saltmarsh, in the fens on the south coast."),
    ("Scripts/Talk to Witch.script", "Morwen the witch lives in Fenwick, in the Saltmarsh south of Oakhollow.",
     "Morwen the witch lives in Saltmarsh, in the fens on the south coast."),
    ("Scripts/Talk to Witch.script", "Bog myrtle grows in the Saltmarsh round Fenwick", "Bog myrtle grows in the fens "
                                                                                     "round Saltmarsh"),
    ("Scripts/Talk to Witch.script", "The Elder's house is in the south-west of the village.",
     "The Elder's never far from the inn."),
    ("Scripts/Talk to Elder.script", "Welcome to Fenwick, traveller. Keep to the boardwalks.",
     "Welcome to Saltmarsh, traveller. Keep to the dry ground."),
    ("Scripts/Talk to Captain.script", "Report to Captain Hale in Highwatch.", "Report to Captain Hale in Frosthold."),
    ("Scripts/Talk to Captain.script", "You've done Highwatch a great service.", "You've done the Redrock road a great "
                                                                              "service."),
    ("Scripts/Talk to Captain.script", "Highwatch salutes you.", "Frosthold salutes you."),
    ("Scripts/Talk to Captain_Rook_Island.script", "..and you step ashore by Ravensgate.",
     "..and you step ashore below King Rupert's Keep."),
    ("Scripts/Bert's Confession.script", "Captain Rook, by Ravensgate,", "Captain Rook, on the shore below the Keep,"),
]
BUILDERS = [   # (the builders that wrote those words, so a run again says the same)
    "build_regions.py", "build_tricks.py", "build_hob.py", "build_heir_mainland.py", "name_graves.py",
    "build_eastreach.py", "quest_notes.py", "build_omens.py",
]


def words():
    n = 0
    for f, old, new in WORDS:
        path = os.path.join(DATA, *f.split("/"))
        if os.path.exists(path):
            n += len(W.replace_in_files([path], [(old, new)]))
    for b in BUILDERS:
        path = os.path.join(HERE, b)
        if not os.path.exists(path):
            continue
        s = open(path, encoding="utf-8").read()
        t = s
        for _, old, new in WORDS:
            if old.startswith("Marker"):
                continue
            t = t.replace(old, new)
        for a, b2 in RENAMED_IDS.items():
            t = t.replace('"%s"' % a, '"%s"' % b2)
        if t != s:
            open(path, "w", encoding="utf-8", newline="\n").write(t)
    return n


def traders():
    """The traders' script without the three towns' wares (and their racks gone)."""
    path = os.path.join(W.SCRIPTS, "Talk to Trader.script")
    lines = W.read(path).split("\r\n")
    rows, cur = [], None
    for ln in lines[1:]:
        p = ln.split("\t")
        if len(p) >= 3 and p[1] == ">On.Map":
            cur = p[2]
        elif len(p) >= 2 and p[1] == "Display.Conversation" and "Welcome to " in ln:
            rows.append((cur, re.search(r"Welcome to ([^!]+)!", ln).group(1)))
    keep = [(m, t) for m, t in rows if t not in TOWNS]
    keep = [kt for i, kt in enumerate(keep) if kt not in keep[:i]]
    out = []
    for m, t in keep:
        out += [(">On.Map", m, "@next_%s" % m),
                SK.say("Trader", "Welcome to %s! Have a look at my wares." % t, ("Show me.", "@show_%s" % m),
                       ("Goodbye.", "@end")),
                ("End",), ("@show_%s" % m,),
                ("Display.Item.Rack", "SPECIFIC", "Trader", "SHOP-%s" % t, "@end"),
                ("End",), ("@next_%s" % m,)]
    out += [SK.say("Trader", "Nothing to sell here, I'm afraid.", ("Goodbye.", "@end")), ("@end",), ("End",)]
    os.remove(path)
    SK.write_script("Talk to Trader", out, "build_regions.py")
    racks = os.path.join(DATA, "ItemRacks.ini")
    s = W.read(racks)
    for t in TOWNS:
        s = re.sub(r"\[SHOP-%s\]\r\n(?:[^\[\r\n][^\r\n]*\r\n|\r\n)*" % t, "", s)
    W.write(racks, s)


def ini_sections(path, names):
    s = W.read(path)
    for n in names:
        s = re.sub(r"\[%s\]\r\n(?:[^\[\r\n][^\r\n]*\r\n)*\r\n?" % re.escape(n), "", s)
    W.write(path, s)


def data(removed_ids):
    ini_sections(os.path.join(DATA, "Shardstones.ini"), list(TOWNS))
    wm = os.path.join(DATA, "WorldMap.ini")
    s = W.read(wm)
    for t in TOWNS:
        s = re.sub(r"%s=%s_Square\r\n" % (t, t), "", s)
    W.write(wm, s)
    gone = 0
    for f in os.listdir(W.SCRIPTS):
        name = f[:-7]
        if name in ("8,16,0", "16,15,0", "26,17,0"):            # (the towns' arrival words)
            os.remove(os.path.join(W.SCRIPTS, f))
            gone += 1
            continue
        verb_id = name.rsplit(" ", 1)
        if len(verb_id) == 2 and verb_id[1] in removed_ids and not KEPT.match(verb_id[1]):
            os.remove(os.path.join(W.SCRIPTS, f))
            gone += 1
    for a, b in RENAMED_IDS.items():
        for f in os.listdir(W.SCRIPTS):
            if f.endswith(" %s.script" % a):
                os.rename(os.path.join(W.SCRIPTS, f), os.path.join(W.SCRIPTS, f.replace(a, b)))
    return gone


def rename_ids(w):
    for (mx, my), m in w.maps.items():
        new = []
        for ln in m.ents:
            p = ln.split("\t")
            if p[0] == "Id" and p[1] in RENAMED_IDS:
                p[1] = RENAMED_IDS[p[1]]
                w.changed.add(m.name)
            new.append("\t".join(p))
        m.ents = new


def main():
    if os.path.exists(DONE):
        print("The towns are gone already (delete %s to do it again)." % DONE)
        return
    w = W.World(0)
    report, gone_all, movers, removed = [], set(), [], set()
    for town, spec in TOWNS.items():
        g, mv, ids = remove(w, town, spec, report)
        gone_all |= g
        movers += mv
        removed |= ids
    placed = move_folk(w, movers)
    rename_ids(w)
    if "Old_Woman" in placed:
        granny_rats(w, placed["Old_Woman"][1])
    n = w.save()
    levels = clear_levels(gone_all)
    for r in report:
        print(r)
    print("Moved: %s; %d maps changed; %d levels over and under gone" % (
        ", ".join("%s to %s" % (k, v[0].name) for k, v in placed.items()), n, levels))
    print("Words: %d changed; scripts gone: %d" % (words(), data(removed)))
    traders()
    open(DONE, "w").write("removed\n")


if __name__ == "__main__":
    main()
