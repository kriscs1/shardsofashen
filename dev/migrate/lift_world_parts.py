"""Lifts the quest places out of the old mainland's maps, once, before build_estforlan.py rebuilds it (dev\\World
Plan.md): each part's tiles and what stands on them (things, people, place Ids, locks, triggers), to be set down at the
same tiles of its new map, so every script's coordinates stay right. Also copies the levels under and over the places
that move (caves, a solar, Bert's study) under their new names.

  python -I "dev\\migrate\\lift_world_parts.py"

It writes dev\\migrate\\world_parts\\parts.json and world_parts\\levels\\<new map>.txt. Run again it does nothing: the
old maps it lifts from are gone once the new world is built.
"""
import json
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from ashen import ini  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "world_parts")
XT, YT, TW = 25, 21, 32
WET = ("Water", "Sand_Water", "Snow_Water", "Marsh_Water")      # (left behind: the new land's own sea and shore)
BEACH = ("Sand001",)

# name: (old map, [rects x1,y1,x2,y2 (1-based tiles)], new map, what's left behind)
PARTS = {
    "iron_mine":       ("1,4,0", [(3, 3, 12, 12), (9, 15, 11, 17)], "20,10,0", WET),
    "keep":            ("2,4,0", [(9, 4, 21, 18), (7, 12, 7, 12)], "22,11,0", WET),
    "court_castle":    ("4,4,0", [(3, 3, 24, 20)], "18,5,0", WET + BEACH),
    "hollow_barrel":   ("3,5,0", [(11, 14, 13, 16)], "13,4,0", WET),
    "smugglers_cove":  ("4,5,0", [(3, 7, 18, 21)], "14,4,0", WET + BEACH),
    "farm":            ("3,3,0", [(1, 7, 16, 21), (18, 12, 25, 21)], "11,4,0", WET + BEACH),
    "ashford_core":    ("2,3,0", [(1, 4, 25, 21)], "9,4,0", WET),
    "southport_port":  ("1,3,0", [(9, 2, 17, 9)], "4,4,0", WET),
    "hobs_house":      ("1,6,0", [(16, 5, 23, 11)], "7,8,0", WET),
    "spider_nest":     ("0,5,0", [(15, 11, 22, 21)], "4,9,0", WET + BEACH),
    "buried_library":  ("1,9,0", [(11, 8, 15, 12)], "3,16,0", WET),
    "caravan_wreck":   ("0,10,0", [(5, 4, 19, 12)], "1,18,0", WET),
    "frost_caverns":   ("4,9,0", [(19, 8, 23, 10)], "12,16,0", WET),
    "wolf_den":        ("5,6,0", [(8, 6, 14, 13)], "14,9,0", WET),
    "bandit_camp":     ("5,8,0", [(5, 3, 16, 14)], "15,14,0", WET),
    "troll_lair":      ("5,9,0", [(9, 9, 16, 16)], "15,18,0", WET),
    "cinder_fort":     ("8,2,0", [(6, 4, 19, 15)], "23,4,0", WET + BEACH),
    "shrine_1":        ("6,4,0", [(7, 9, 11, 13)], "21,4,0", WET),
    "shrine_3":        ("7,3,0", [(16, 16, 20, 20)], "21,7,0", WET),
    "shrine_2":        ("9,4,0", [(12, 7, 16, 11)], "23,8,0", WET),
    "heartwood":       ("8,5,0", [(12, 10, 18, 16)], "19,12,0", WET),
    "barrow":          ("9,7,0", [(3, 8, 14, 18)], "18,17,0", WET),
    "rooks_pier":      ("9,8,0", [(1, 1, 25, 21)], "23,17,0", ()),
    "dragon_island":   ("8,10,0", [(1, 1, 25, 21)], "22,20,0", ()),
    "downs_graves":    ("6,7,0", [(17, 3, 25, 14)], "17,14,0", WET + BEACH),
    "hill_graves":     ("7,8,0", [(8, 17, 11, 19), (4, 12, 6, 14)], "19,18,0", WET),
    "ravensgate_old":  ("8,7,0", [(7, 1, 9, 3), (3, 12, 5, 14)], "22,15,0", WET),
    "ravensgate_yard": ("8,8,0", [(16, 16, 25, 20)], "22,16,0", WET + BEACH),
    "palace":          ("12,5,0", [(3, 5, 23, 14)], "2,12,0", WET),
    "watch_stone_1":   ("2,5,0", [(6, 7, 8, 10)], "5,7,0", WET),
    "watch_stone_2":   ("0,6,0", [(18, 6, 20, 9)], "2,9,0", WET),
    "watch_stone_3":   ("1,5,0", [(14, 16, 16, 19)], "8,6,0", WET),
    "old_hob":         ("0,6,0", [(16, 2, 18, 4)], "3,8,0", WET),
    "chest_2_10":      ("2,10,0", [(6, 11, 8, 13)], "4,19,0", WET),
    "chest_2_8":       ("2,8,0", [(16, 19, 16, 19)], "7,18,0", WET),
    "chest_3_6":       ("3,6,0", [(4, 16, 4, 16)], "11,8,0", WET),
    "chest_5_7":       ("5,7,0", [(1, 6, 3, 8)], "13,12,0", WET),
    "chest_6_3":       ("6,3,0", [(8, 3, 12, 7)], "22,7,0", WET),
    "chest_6_6":       ("6,6,0", [(16, 7, 20, 11)], "16,8,0", WET),
    "chest_9_2":       ("9,2,0", [(2, 12, 6, 16)], "21,9,0", WET),
}
# the levels that move with them: old -> new (copied whole: their tiles are where the ladders are)
LEVELS = {"1,4,-1": "20,10,-1", "2,4,-1": "21,10,-1", "2,4,-2": "21,10,-2", "2,4,-3": "21,10,-3",
          "2,4,1": "22,11,1", "4,4,1": "18,5,1", "3,5,-1": "13,4,-1", "4,5,-1": "14,4,-1",
          "1,9,-1": "3,16,-1", "4,9,-1": "12,16,-1", "14,6,-1": "0,12,-1"}


def read_map(name):
    lines = ini.read_text(os.path.join(ROOT, "maps", name + ".txt")).replace("\r", "").split("\n")
    rows = [[c.strip() for c in lines[y].split(":")][:XT] for y in range(YT)]
    return rows, [ln for ln in lines[YT:] if ln.strip()]


def line_tile(ln):
    """The tile a map line stands on (1-based), or None."""
    p = ln.split("\t")
    try:
        if p[0] in ("NPC", "StaticObject", "MapItem"):
            return int(float(p[2])) // TW + 1, (int(float(p[3])) + 24) // TW + 1
        if p[0] in ("Id", "Trigger"):
            return int(p[2]), int(p[3])
        if p[0] == "Lock":
            return int(p[1]), int(p[2])
    except (ValueError, IndexError):
        pass
    return None


FILLER = ("_Barkeep_", "_Barmaid_", "_Resident_", "_Notice_", "_Clerk_", "_Doctor_", "_Nurse_", "_Carter_", "_Horse_",
          "_Baker_", "_Butcher_", "_Fishmonger_", "_Greengrocer_", "_Tailor_", "_Cobbler_", "_Armourer_", "_Hotelier_",
          "_Banker_", "_Soldier_", "_Stall_")
GENERIC = {"Wolf", "Bear", "Giant_Spider", "Scorpion", "Skeleton", "Bandit", "Butterfly", "Blue_Butterfly", "Rabbit",
           "Dog", "Cat", "Black_Cat", "Ginger_Cat", "Cow", "Sheep", "Chicken", "Duck", "Bones", "Rat", "Bat", "Fire",
           "Notice", "Waystone", "Homestone", "Market_Board", "Chest"}


def lift_people():
    """The people (and the odd thing) that a script is written for, wherever they stood on the old mainland: their map
    lines, to be put in the matching place of the new world (world_parts\\people.json)."""
    scripts = {f[:-4] for f in os.listdir(os.path.join(ROOT, "data", "Scripts"))}
    targets = {s.split(" ", 2)[-1] for s in scripts if s.startswith(("Talk to ", "Forge ", "Read "))}
    lifted = {ln for p in json.load(open(os.path.join(OUT, "parts.json"), encoding="utf-8"))["parts"].values()
              for ln in p["lines"]}
    people = {}
    for f in sorted(os.listdir(os.path.join(ROOT, "maps"))):
        name = f[:-4]
        if not name.endswith(",0") or name in ISLE:
            continue
        for ln in read_map(name)[1]:
            p = ln.split("\t")
            if p[0] not in ("NPC", "StaticObject") or ln in lifted:
                continue
            pid = ln.split("Id=")[1].split()[0] if "Id=" in ln else ""
            if pid and not any(s in pid for s in FILLER):
                people.setdefault(name, []).append(ln)
            elif not pid and p[1] not in GENERIC and (p[1] in targets or p[1] in ("Dragonforge", "Anvil", "Furnace")):
                people.setdefault(name, []).append(ln)
    with open(os.path.join(OUT, "people.json"), "w", encoding="utf-8") as fh:
        json.dump(people, fh, indent=1, sort_keys=True)
    print("Wrote dev\\migrate\\world_parts\\people.json: %d lines" % sum(len(v) for v in people.values()))


ISLE = {"0,0,0", "0,1,0", "1,0,0", "1,1,0", "1,2,0", "2,0,0", "2,1,0", "2,2,0", "3,0,0", "3,1,0", "3,2,0", "4,0,0",
        "4,1,0"}


def main():
    if os.path.exists(os.path.join(OUT, "parts.json")):
        if not os.path.exists(os.path.join(OUT, "people.json")) and os.path.exists(os.path.join(ROOT, "maps", "1,4,0.txt")):
            lift_people()
        else:
            print("The parts are lifted already (dev\\migrate\\world_parts): nothing to do.")
        return
    rows, _ = read_map("1,4,0")
    if "Ashford_Iron_Mine" not in open(os.path.join(ROOT, "maps", "1,4,0.txt"), encoding="cp1252").read():
        sys.exit("The old mainland isn't there to lift from (has build_estforlan.py rebuilt it?).")
    os.makedirs(os.path.join(OUT, "levels"), exist_ok=True)
    parts = {}
    for name, (old, rects, new, wet) in PARTS.items():
        rows, lines = read_map(old)
        inside = lambda x, y: any(x1 <= x <= x2 and y1 <= y <= y2 for x1, y1, x2, y2 in rects)   # noqa: E731
        cells = {}
        for y in range(1, YT + 1):
            for x in range(1, XT + 1):
                c = rows[y - 1][x - 1]
                if inside(x, y) and not (c.split("+")[0].startswith(wet) and "+" not in c):
                    cells["%d,%d" % (x, y)] = c
        kept = [ln for ln in lines if line_tile(ln) and inside(*line_tile(ln))]
        parts[name] = {"old": old, "new": new, "rects": rects, "cells": cells, "lines": kept}
        print("%-16s %s -> %s: %d tiles, %d lines" % (name, old, new, len(cells), len(kept)))
    for old, new in LEVELS.items():
        shutil.copyfile(os.path.join(ROOT, "maps", old + ".txt"), os.path.join(OUT, "levels", new + ".txt"))
        print("level %s -> %s" % (old, new))
    with open(os.path.join(OUT, "parts.json"), "w", encoding="utf-8") as f:
        json.dump({"parts": parts, "levels": LEVELS}, f, indent=1, sort_keys=True)
    print("Wrote dev\\migrate\\world_parts\\parts.json")


if __name__ == "__main__":
    main()
