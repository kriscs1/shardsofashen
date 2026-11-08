"""Standing in every town (dsengine/standing.py, dev\\Roadmap-6.md group 1): its data.

  * data\\Towns.ini: the ranks and their prices, what each deed is worth, the fine, and each town's maps and captain
    (who takes an Outlaw's fine: the sheriff or constable, or in a hamlet its priest).
  * Quests.ini Reward.Standing=<Town> N on each side quest given in a town (where its first marker is), unless it
    says its own already.

Safe to run again (only what's missing is added; your numbers are kept).

  python -I "dev\\migrate\\build_standing.py"
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import Ini, p                      # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from dsengine.data import GameData            # noqa: E402

QUEST_STANDING = 10

TOWNS = """; Each town's standing with you (dsengine/standing.py), each player's own: from Least to Most, everyone starting at 0
; (a Stranger). Scripts: Change.Standing <Town> <amount>; $Standing.<Town> (or $Standing.Here) in a condition (a
; lock's condition is how a door opens at a rank). Written by dev\\migrate\\build_standing.py: edit the numbers here.

[Standing]
Least=-100
Most=100
; The kinds that keep a town's watch: an Outlaw's foes on sight there (never its captain, nor a guard with a Talk
; script of their own: a character, not the watch)
Guards=Guard,Constable,Port_Guard,Royal_Guard,Guard_Captain
; How far below a town's maps still counts as the town (its cellars and sewers)
Depth=1
; What a deed is worth: a quest (Quests.ini Reward.Standing=<Town> N says its own), a raid fought off, the day's
; bounty; gifts to a town's project (so much for each gold's worth, Project.Most at most)
Quest=10
Raid=8
Bounty=3
Project.Per.Gold=0.02
Project.Most=15
; Caught at a shelf or a pocket; caught in a house; a blow at a guard (once in Guard.Hit.Minutes for each guard); a
; guard killed. A theft nobody sees costs nothing.
Caught=-8
Caught.House=-12
Guard.Hit=-15
Guard.Hit.Minutes=5
Guard.Killed=-40
; Trusted: caught, a guard only warns you, once in Warn.Hours. Honoured: a fine (gold) instead of a chase.
; Distrusted or worse: this many guards come, and sooner.
Warn.Hours=24
Caught.Fine=25
Distrusted.Guards=2
; An Outlaw's fine to the town's captain: Fine gold, and Fine.Per.Point more for each point below Clear.To, where
; paying it leaves you
Fine=50
Fine.Per.Point=5
Clear.To=-60

[Ranks]
; A rank: the least standing that's it; times what you pay at a shop there, and what you're paid. An Outlaw isn't
; served at all.
Outlaw=-100 1 1
Distrusted=-60 1.25 0.85
Stranger=-20 1 1
Welcome=20 0.95 1.05
Trusted=45 0.9 1.1
Honoured=75 0.85 1.15

; A town: Name (as said: "Ashford thinks better of you"), Maps (x1,y1,x2,y2 boxes of map numbers, any number),
; Captain (an Id, or a kind on the town's maps), Guards.If (a condition before its guards turn on an Outlaw).
"""

# key, name, maps, captain, guards.if
TOWN_LIST = (
    ("Isle", "the Isle", "0,-3,4,2", "Chapel_Verger", ""),
    ("Northport", "Northport", "2,4,7,7", "Northport_Constable_347", ""),
    ("Ashford", "Ashford", "10,-4,13,-1", "Ashford_Sheriff_325", ""),
    ("Oakhollow", "Oakhollow", "8,9,9,12", "Oakhollow_Sheriff_314", ""),
    ("Greyford", "Greyford", "12,8,15,9", "Greyford_Priest_303", ""),
    ("Wildwood", "Wildwood", "1,8,3,9", "Wildwood_Priest_303", ""),
    ("Thornwick", "Thornwick", "19,12,21,14", "Thornwick_Sheriff_313", ""),
    ("Court", "Wizards' Court", "18,4,21,7", "Court_Sheriff_331", ""),
    ("Emberwatch", "Emberwatch", "25,4,27,7", "Emberwatch_Sheriff_312", ""),
    ("Wardhaven", "Wardhaven", "15,1,17,2", "Wardhaven_Sheriff_320", ""),
    ("Keep", "King Rupert's Keep", "24,16,27,20", "Keep_Sheriff_337", ""),
    ("Frosthold", "Frosthold", "16,19,18,21", "Frosthold_Sheriff_326", ""),
    ("Dunerest", "Dunerest", "2,21,4,21", "Dunerest_Priest_303", ""),
    ("Saltmarsh", "Saltmarsh", "10,23,12,23", "Saltmarsh_Priest_303", ""),
    ("Mirefold", "Mirefold", "-7,4,-5,5", "Foreman_Mirefold_Boardwalks", ""),
    ("Galaith", "Galaith", "-11,12,-4,17", "Galaith_Constable_372", "$Attr.KingQuest>=1"),
)


def towns_text():
    out = TOWNS
    for key, name, maps, captain, cond in TOWN_LIST:
        out += "\n[%s]\nName=%s\nMaps=%s\nCaptain=%s\n" % (key, name, maps, captain)
        if cond:
            out += "Guards.If=%s\n" % cond
    return out


def towns():
    path = p("data", "Towns.ini")
    if not os.path.exists(path):
        with open(path, "wb") as f:
            f.write(towns_text().replace("\n", "\r\n").encode("cp1252"))
        return
    have = Ini(path)
    import tempfile
    tmp = os.path.join(tempfile.mkdtemp(), "Towns.ini")
    with open(tmp, "wb") as f:
        f.write(towns_text().replace("\n", "\r\n").encode("cp1252"))
    want = Ini(tmp)
    changed = False
    for name, items in want.sections:
        for k, v in items:
            if k is not None and have.get(name, k) is None:
                have.set(name, k, v, overwrite=False)
                changed = True
    if changed:
        have.save(path)


def town_of(mapname):
    bits = mapname.split(",")
    if len(bits) != 3:
        return ""
    x, y, z = (int(b) for b in bits)
    if z < -1:
        return ""
    for key, _, maps, _, _ in TOWN_LIST:
        a, b, c, d = (int(v) for v in maps.split(","))
        if a <= x <= c and b <= y <= d:
            return key
    return ""


def quests():
    """Each side quest given in a town: Reward.Standing for it (its first marker is where it's given)."""
    data = GameData(ROOT)
    path = p("data", "Quests.ini")
    q = Ini(path)
    n = 0
    for name, items in q.sections:
        d = {k.upper(): v for k, v in items if k is not None}
        if d.get("TYPE", "") != "Side" or "REWARD.STANDING" in d:
            continue
        where = ""
        for marker in ("MARKER0", "MARKER1"):
            pl = data.place(d.get(marker, ""))
            if pl is not None:
                where = town_of(pl.map)
                break
        if where:
            q.set(name, "Reward.Standing", "%s %d" % (where, QUEST_STANDING), overwrite=False)
            n += 1
    if n:
        q.save(path)
    print("Reward.Standing on %d quests" % n)


def main():
    towns()
    quests()


if __name__ == "__main__":
    main()
