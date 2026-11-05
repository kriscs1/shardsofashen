"""Mary's grave moves to the chapel graveyard's east end, by the sea (4,1,0 tile 2,5: the owner's wish), and the
graveyard's fence grows round it: its east side on 3,1,0 comes down, and the fence runs on along the top of 4,1,0, with
a gate toward the cottage, and down to the sea. The funeral, its entry script and a new character's start follow
(build_heir_isle.py GRAVE_MAP, GRAVE).

  python -I "dev\\migrate\\move_marys_grave.py"

Safe to run again: once the grave's on 4,1,0 it does nothing.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_heir_isle as H
import story_kit as K
from build_isle import Map
from common import p

OLD = "3,1,0"


def drop_ids(m, names):
    m.ents = [ln for ln in m.ents if not (ln.startswith("Id\t") and ln.split("\t")[1] in names)]


def main():
    new = Map(H.GRAVE_MAP)
    if K.has_id(new, "Mothers_Grave"):
        print("Mary's grave is already on", H.GRAVE_MAP)
        return
    old = Map(OLD)
    for x in range(1, 26):                                      # (the old grave: grass again)
        for y in range(1, 22):
            if old.decor(x, y) == "Fresh_Grave001":
                old.set(x, y, decor="")
    drop_ids(old, ("Mothers_Grave", "Funeral_Spot"))
    old.set(24, 2, decor="Wood_Fence001")                       # (the east side comes down; the top runs on)
    old.set(25, 2, decor="Wood_Fence001")
    for y in range(3, 9):
        if old.decor(24, y) == "Wood_Fence002":
            old.set(24, y, decor="")
    old.save()

    for x in range(1, 6):                                       # (inside: the rocks and trees cleared, flowers kept)
        for y in range(3, 9):
            if new.decor(x, y).startswith(("Rock", "Tree", "Bush", "Pebbles")):
                new.set(x, y, decor="")
    for x in range(1, 6):
        new.set(x, 2, decor="Wood_Fence001")
    new.set(H.GRAVE_GATE[0], 2, decor="Wood_Gate001")
    new.set(6, 2, decor="Wood_Fence004")                        # (the corner, then down to the sea)
    for y in range(3, 9):
        new.set(6, y, decor="Wood_Fence002")
    new.save()
    H.grave()
    H.opening()
    H.template()
    gone = p("data", "Scripts", OLD + ".txt")                   # (the funeral's no longer 3,1,0's entry script)
    if os.path.exists(gone) and "The Funeral" in open(gone, encoding="cp1252").read():
        os.remove(gone)
    print("Mary's grave: %s tile %d,%d" % ((H.GRAVE_MAP,) + H.GRAVE))


if __name__ == "__main__":
    main()
