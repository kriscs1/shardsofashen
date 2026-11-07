"""The Dark Mage (the owner's wish: it teleports around, so it's hard to hit). Entities.ini Blink.Every and Blink.Near;
what it does is npcs.py npc_blink. It throws dark bolts from afar, and when you come near, or hit it, or it's stood long
enough, it's somewhere else. It needs a moment to throw again, and ice or a stun holds it where it is. It hits softly
for its level: it's meant to take a while to pin down, not to kill quickly (played through at level 12 in steel: about
14 s, 7 jumps, a quarter of your health, where a Frost Witch takes 5 s and far more of it).

  * The person: build_people.py PEOPLE (robes and a hood in violet, a staff with a glowing orb); here its pictures, for
    it alone (build_walk.py deletes frames it didn't make, so it isn't run for one more person).
  * Its bolt and burst: the ice bolt's, turned violet.
  * Three, out in the wild, where there's room to jump about: by the Barrow, outside the Drowned Abbey, on the Greyflats.

Safe to run again (they are laid out afresh, the same each time).

  python -I "dev\\migrate\\build_dark_mage.py"
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "estforlan"))
from common import Ini, p                      # noqa: E402
import build_people as BP                      # noqa: E402
import sprite_kit as K                         # noqa: E402
import world_edit as W                         # noqa: E402
from world_edit import XT, YT                  # noqa: E402

NAME = "Dark_Mage"
ENTITY = [("Type", "NPC"), ("Attitude", "Bad"),
          ("Examine.Info", "A mage who went looking for what broke the world, and liked it. The air keeps moving "
                           "after they've gone."),
          ("Hitpoints", "54"), ("Attack.Speed", "2"), ("Strength", "5"), ("Defence", "6"), ("Aggro.Range", "260"),
          ("Weapon.Range", "180"), ("Missile", "Dark_Bolt_Missile"), ("Missile.Impact", "Dark_Burst"),
          ("Movement.Speed", "1.6"), ("Aggressive", "1"), ("Respawn", "300"),
          ("Drops", "Gold_Coin(s),20-45,100 Sapphire,1-1,12 Empty_Vial,1-1,30"), ("On.Hit", "Daze 30"),
          ("Roam.Radius", "2"), ("Chase.Radius", "9"), ("Walk.Speed", "0.5"), ("Pause", "3-8"), ("Kill.Sound", "Beast"),
          ("Level", "7"), ("Sight.Cone", "220"), ("Hearing", "1.3"), ("Blink.Every", "2"), ("Blink.Near", "72")]
# (map, its tile, the rectangle it roams and the one it fights in: clear of the Barrow's skeletons, or the fight brings
# them too)
PLACES = [((21, 19), (21, 5), "17,2,24,9", "15,1,24,11"), ((9, 16), (19, 5), "15,2,24,12", "15,1,25,14"),
          ((15, 11), (13, 14), "9,10,18,17", "6,8,21,20")]
VIOLET = (150, 80, 235)


def violet(img):
    """As light or dark as it was, in violet."""
    out = []
    for row in img:
        r2 = []
        for c in row:
            if c is None:
                r2.append(None)
                continue
            lum = sum(c[:3]) / 765.0
            r2.append(tuple(min(255, int(v * (0.3 + 1.1 * lum) + 90 * max(0, lum - 0.65))) for v in VIOLET))
        out.append(r2)
    return out


def pictures():
    n = 0
    fr = BP.frames(NAME)
    n += K.save("Entities", NAME, fr["4a"])
    for key, im in fr.items():
        n += K.save("Walk", NAME + key, im)
    n += K.save("Effects", "Dark_Bolt_Missile", violet(K.load("Effects", "Ice_Bolt_Missile")))
    for i in range(1, 5):
        n += K.save("Effects", "Dark_Burst%d" % i, violet(K.load("Effects", "Ice_Burst%d" % i)))
    print("Pictures: %d written" % n)


def data():
    ents = Ini(p("data", "Entities.ini"))
    for k, v in ENTITY:
        ents.set(NAME, k, v, overwrite=False)
    ents.save(p("data", "Entities.ini"))


def place():
    w = W.World(0)
    for m in w.maps.values():
        for ln in [ln for ln in m.ents if ln.startswith("NPC\t%s\t" % NAME)]:
            w.drop(m, ln)                               # (laid out afresh: the same each run)
    for (mx, my), (x, y), zone, chase in PLACES:
        w.place(mx * XT + x - 1, my * YT + y - 1, "NPC", NAME, "Attitude=Bad Zone=%s Chase=%s" % (zone, chase))
    return w.save()


def main():
    pictures()
    data()
    print("The Dark Mage: %d maps" % place())


if __name__ == "__main__":
    main()
