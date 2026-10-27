"""Builds the new mainland of Estforlan (dev\\World Plan.md; dev\\migrate\\estforlan does the work): the land, Galaith
in its valley in the West Range, every settlement the size it's given, the quest places lifted from the old maps
(dev\\migrate\\world_parts, made once by lift_world_parts.py) at their old tiles, the roads, the creatures; then the
scripts and data that name its places. The Isle is left alone.

  python -I "dev\\migrate\\build_estforlan.py"

The first run also moves the old mainland's scripts and data over (map names that moved, quest markers, entry
scripts) and deletes its maps; run again, it builds the same world again.
"""
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "estforlan"))

import story_kit as K  # noqa: E402
import layout as L  # noqa: E402
import places as P  # noqa: E402
import story  # noqa: E402
import world  # noqa: E402
import life  # noqa: E402
import quests  # noqa: E402

MAKER = "build_estforlan.py"
MAPS = os.path.join(K.ROOT, "maps")
OLD_LEVELS_GONE = ("1,10,1", "2,8,1", "4,10,1", "4,3,1", "4,8,1", "5,3,1", "7,4,1", "7,6,1", "8,8,1", "14,6,-1",
                   "1,4,-1", "2,4,-1", "2,4,-2", "2,4,-3", "2,4,1", "4,4,1", "3,5,-1", "4,5,-1", "1,9,-1", "4,9,-1")


def old_world():
    """Is the old mainland still there (the first run moves its scripts over)?"""
    path = os.path.join(MAPS, "1,4,0.txt")
    return os.path.exists(path) and "Ashford_Iron_Mine" in open(path, encoding="cp1252").read()


def main():
    first = old_world()
    if not first:
        print("Map names moved on in %d scripts and data files" % story.stretch_names())
    atlas, plans, homes, rehoused, gate_map, scripts, bridge = world.assemble()
    for name, rows in scripts.items():
        K.write_script(name, rows, MAKER)
    keep = set(atlas.maps) | set(L.ISLE)
    for f in os.listdir(MAPS):                                     # the old mainland's maps go
        name = f[:-4]
        if not f.endswith(".txt") or story.isle(name) or name in story.ISLE_LEVELS:
            continue
        if name.endswith(",0") and name not in keep or name in OLD_LEVELS_GONE:
            os.remove(os.path.join(MAPS, f))
    atlas.save()
    levels = P.levels()
    for new, src in levels.items():
        shutil.copyfile(src, os.path.join(MAPS, new + ".txt"))
    print("Saved %d maps and %d levels under them" % (len(atlas.maps), len(levels)))
    for f in os.listdir(MAPS):                                     # (levels under places that have moved on)
        name = f[:-4]
        if f.endswith(".txt") and not name.endswith(",0") and not story.isle(name) and                 name not in story.ISLE_LEVELS and name not in levels:
            os.remove(os.path.join(MAPS, f))
    table = story.renames(homes, gate_map)
    if first:
        print("Moved %d scripts' map names over" % story.remap_scripts(table, story.chest_maps()))
        story.quests(table, rehoused)
        story.config()
    extra = quests.bridge(atlas, bridge)
    quests.dragonforge()
    quests.leftovers()
    story.entry_scripts(plans, first, extra)
    story.people_branches(P.strays(plans))
    story.pass_scripts()
    story.wardhaven_guard()
    print("Waystones: %s" % ", ".join(story.waystones(atlas, plans)))
    story.world_map(plans)
    story.waves(plans)
    story.digging()
    story.ambient(life.sounds(atlas), levels)
    gone = story.orphans()
    print("Removed %d scripts nobody is left to use" % len(gone))


if __name__ == "__main__":
    main()
