"""Teleport Home is gone: a spell that takes you home from anywhere made the roads, the ferries and the waystones
nothing. Takes away the spell (Spells.ini), its scroll (Entities.ini) and the scroll on any shop's shelf, the shelf
numbered again (a gap ends a shop's list). Whoever knew it, or holds its scroll, has the gold Bert sold it for
(dsengine/session.py spells_gone). The Trusted chests that gave two are build_town_choices.py's. A second run does
nothing.

  python -I "dev\\migrate\\remove_teleport_home.py"
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import story_kit as SK  # noqa: E402

SPELL, SCROLL = "Teleport_Home", "Teleport_Scroll"
DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data")


def off_the_shelves(path):
    blocks = SK._blocks(path)
    changed = False
    for i, b in enumerate(blocks):
        lines = b.split("\n")
        items = [ln for ln in lines if re.match(r"Item\d+=", ln)]
        if not any(ln.split("=", 1)[1].split(",")[0].strip() == SCROLL for ln in items):
            continue
        kept = [ln.split("=", 1)[1] for ln in items if ln.split("=", 1)[1].split(",")[0].strip() != SCROLL]
        # (the rest go back where the first one was, in order, numbered from 1)
        first = next(j for j, ln in enumerate(lines) if re.match(r"Item\d+=", ln))
        body = [ln for ln in lines if not re.match(r"Item\d+=", ln)]
        blocks[i] = "\n".join(body[:first] + ["Item%d=%s" % (k + 1, v) for k, v in enumerate(kept)] + body[first:])
        print("%s off the shelf in %s" % (SCROLL, b.split("\n", 1)[0]))
        changed = True
    if changed:
        SK._write_blocks(path, blocks)


def main():
    SK.remove_section(os.path.join(DATA, "Spells.ini"), SPELL)
    SK.remove_section(os.path.join(DATA, "Entities.ini"), SCROLL)
    off_the_shelves(os.path.join(DATA, "ItemRacks.ini"))


if __name__ == "__main__":
    main()
