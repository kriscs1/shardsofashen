"""Shard Remnants: what a monster's magic leaves when it dies, in place of Shards straight to the killer and the bones
(dsengine/remnants.py).

  * Shard_Remnant: dull splinters on the ground where a monster died. Picked up, Absorb turns them into Shards.
  * Living_Remnant ("Shard Remnant"): now and then a monster's magic rises as a monster of its own, a knot of jagged
    crystal round a violet light, as strong as the one that died, and goes for its killer; killed, it leaves more
    remnants. Its walking frames (Living_Remnant2a-c, 8a-c: it drifts), drawn here.
  * Every monster and animal that can be attacked (Bad or Passive: prey too) gets a Level= (1-25, from its strength,
    defence and hitpoints): how many remnants it leaves and how strong a remnant rising from it is (a level 1 never
    rises: Mob.Min.Level). Its Drops lose their Bones and Shards.
  * Shards.ini [Remnants]: the chances and numbers (only the keys missing are added: edit them there).
  * Their sounds, synthesised: Remnant_Rise (a glassy shriek, a hum) and Absorb (a rising shimmer).

Safe to run again.

  python -I "dev\\migrate\\build_remnants.py"
"""
import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import Ini, p                      # noqa: E402
import build_sounds as SND                     # noqa: E402
import sprite_kit as K                         # noqa: E402

MAKER = "build_remnants.py"
REMNANTS = [   # Shards.ini [Remnants] (key, value, what it means: written as the comment above it)
    ("Chance", "45", "In 100: a monster that dies leaves Shard Remnants on the ground"),
    ("Count", "1-2", "How many"),
    ("Count.Per.Level", "0.25", "And this many more for each level of the monster (Entities.ini Level=)"),
    ("Mob.Chance", "6", "In 100: instead, its magic rises as a Shard Remnant and attacks its killer"),
    ("Mob.Min.Level", "2", "Only from monsters of this level and up"),
    ("Mob.Hitpoints", "5", "The Shard Remnant's hitpoints: this, and Mob.Hitpoints.Per.Level for each level"),
    ("Mob.Hitpoints.Per.Level", "5", None),
    ("Mob.Strength", "1", "Its strength and defence the same way"),
    ("Mob.Strength.Per.Level", "0.5", None),
    ("Mob.Defence", "1", None),
    ("Mob.Defence.Per.Level", "0.5", None),
    ("Mob.Count", "3-6", "The remnants it leaves when it's killed (and Count.Per.Level more for each level)"),
    ("Mob.Lasts", "120", "Seconds it lingers if nobody fights it"),
    ("Absorb", "1", "Shards from each remnant absorbed"),
    ("Absorb.XP", "0.05", "Shardcraft xp for each"),
]

VIOLET, PALE, DARK, DULL = (150, 90, 220), (210, 190, 255), (70, 40, 110), (120, 110, 140)


def remnant_item():
    """Three small splinters, grey and dull, a faint violet light still in them."""
    img = K.new()
    for (cx, base, top, lean) in ((12, 27, 17, 1), (18, 27, 13, -1), (23, 27, 20, 0)):
        for y in range(top, base + 1):
            t = (y - top) / max(1, base - top)
            half = int(round(2.2 * t + 0.4))
            x0 = cx + int(lean * (1 - t) * 2)
            for x in range(x0 - half, x0 + half + 1):
                d = abs(x - x0) / max(1, half)
                img[y][x] = K.mix(DULL, VIOLET, 0.55 if d < 0.4 else 0.15) if y > top + 1 else PALE
    for y in range(26, 29):                               # (grit at their feet)
        for x in (9, 15, 21, 26):
            if (x + y) % 3:
                K.put(img, x, y, (96, 90, 104))
    return K.outline_img(img, (34, 26, 48))


def living_remnant(frame, flip=False):
    """A knot of jagged crystal round a violet light, drifting: the splinters turn round it a little each frame and
    it bobs. Facing right (flip: left)."""
    img = K.new()
    bob = (0, -1, -2)[frame]
    cx, cy = 16, 15 + bob
    for r in range(7, 0, -1):                             # the light at its heart, glowing out
        c = K.mix(PALE, VIOLET, r / 7.0)
        for y in range(cy - r, cy + r + 1):
            for x in range(cx - r, cx + r + 1):
                if (x - cx) ** 2 + (y - cy) ** 2 <= r * r and (r < 5 or (x + y + frame) % 2 == 0):
                    K.put(img, x, y, c)
    turn = frame * 0.35
    for i in range(7):                                    # the splinters round it, pointing out
        a = turn + i * 2 * math.pi / 7
        for k in range(5, 12):
            x = int(round(cx + math.cos(a) * k))
            y = int(round(cy + math.sin(a) * k * 0.9))
            w = 1 if k > 8 else 2
            for d in range(-w + 1, w):
                K.put(img, x + int(round(-math.sin(a) * d)), y + int(round(math.cos(a) * d)),
                      K.mix(DULL, VIOLET, 0.7 - (k - 5) * 0.07) if k < 11 else PALE)
    for dx, dy in ((2, -1), (3, -1)):                     # (two cold eyes, looking the way it goes)
        K.put(img, cx + dx, cy + dy, (255, 255, 255))
    for y in range(28, 30):                               # its faint shadow on the ground
        for x in range(10, 23):
            if (x + y) % 2 == 0:
                K.put(img, x, y, DARK)
    img = K.outline_img(img, (30, 18, 46))
    return K.flip_h(img) if flip else img


SOUNDS = {
    # a glassy shriek sliding down, over a low hum swelling
    "Remnant_Rise": lambda: SND.mix((SND.shaped(SND.tone(1760, SND.n(0.6), glide=-0.5), 0.01, 4.0), 0.35),
                                    (SND.arpeggio([2637, 2093, 1568, 1319], 0.05, 0.6, decay=5.0), 0.3),
                                    (SND.shaped(SND.tone(82, SND.n(0.9), glide=0.2), 0.25, 3.0), 0.6)),
    # a soft shimmer rising, into you
    "Absorb": lambda: SND.mix((SND.arpeggio([784, 1047, 1319, 1568, 2093], 0.05, 0.6, decay=4.5), 0.45),
                              (SND.shaped(SND.noise(41, SND.n(0.5), 0.3, high=0.5), 0.15, 5.0), 0.15)),
}


def level_of(ents, sec):
    """A monster's level, 1-25, from its strength, defence and hitpoints."""
    f = lambda k: float(ents.get(sec, k) or 0)
    return max(1, min(25, int(round((f("Strength") + f("Defence")) / 2 + f("Hitpoints") / 30))))


def entities():
    ents = Ini(p("data", "Entities.ini"))
    for k, v in (("Type", "MapItem"), ("Use.Words", "Absorb"), ("Stackable", "9999"), ("Value", "1"),
                 ("Examine.Info", "Shard Remnants: dull splinters of the magic a monster carried. Absorb them for "
                                  "Shards.")):
        ents.set("Shard_Remnant", k, v)
    for k, v in (("Type", "NPC"), ("Examine.Info", "A Shard Remnant: a dead beast's magic, risen in a knot of jagged "
                                                   "crystal. It hates the living."),
                 ("Hitpoints", "10"), ("Attack.Speed", "1"), ("Strength", "1"), ("Defence", "1"), ("Aggro.Range", "160"),
                 ("Weapon.Range", "0"), ("Movement.Speed", "2"), ("Aggressive", "1"), ("Chase.Radius", "8"),
                 ("Walk.Speed", "0.7"), ("Respawn", "60"), ("Kill.Sound", "Beast"), ("Attitude", "Bad"), ("Light", "40"), ("Level", "1")):
        ents.set("Living_Remnant", k, v)
    n = 0
    for sec, items in ents.sections:
        if (ents.get(sec, "Type") or "") != "NPC" or (ents.get(sec, "Attitude") or "") not in ("Bad", "Passive") or \
                sec == "Living_Remnant":
            continue
        ents.set(sec, "Level", str(level_of(ents, sec)), overwrite=False)
        drops = ents.get(sec, "Drops") or ""
        kept = re.sub(r"\s*\b(Bones|Shard),\S+", "", drops).strip()
        if kept != drops:
            ents.set(sec, "Drops", kept) if kept else ents.remove(sec, "Drops")
            n += 1
    ents.save(p("data", "Entities.ini"))
    print("Monsters' Drops without Bones or Shards: %d changed" % n)


def shards_ini():
    path = p("data", "Shards.ini")
    ini = Ini(path) if os.path.exists(path) else Ini()
    if ini.section("Remnants") is None:
        lines = ["; Shard Remnants (dsengine/remnants.py): a monster's magic, left when it dies. Its level is its",
                 "; Entities.ini Level= (1-25). Written by dev\\migrate\\%s: edit the numbers here." % MAKER]
        for k, v, note in REMNANTS:
            if note:
                lines.append("; " + note)
            lines.append("%s=%s" % (k, v))
        ini.sections.append(["Remnants", [(None, ln) if ln.startswith(";") else tuple(ln.split("=", 1))
                                          for ln in lines]])
    else:
        for k, v, note in REMNANTS:
            ini.set("Remnants", k, v, overwrite=False)
    ini.save(path)


def main():
    print(("wrote " if K.save("Entities", "Shard_Remnant", remnant_item()) else "unchanged ") + "Shard_Remnant")
    print(("wrote " if K.save("Entities", "Living_Remnant", living_remnant(0)) else "unchanged ") + "Living_Remnant")
    for f, letter in enumerate("abc"):
        for d, flip in (("2", False), ("8", True)):
            K.save("Walk", "Living_Remnant%s%s" % (d, letter), living_remnant(f, flip))
    for name, fn in SOUNDS.items():
        blob = SND.wav_bytes(fn())
        path = p("sounds", name + ".wav")
        if not (os.path.exists(path) and open(path, "rb").read() == blob):
            with open(path, "wb") as fh:
                fh.write(blob)
            print("wrote sounds\\%s.wav" % name)
    entities()
    shards_ini()
    print("Shard Remnants: done")


if __name__ == "__main__":
    main()
