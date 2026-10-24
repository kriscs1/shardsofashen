"""The chapel's upper floor (3,1,1): Brother Aldous's quarters and the bell loft, up the stairs by the altar. Run it
once (again: it sees it's done; the bell's sound and picture are made again).

  python -I "Dev\\migrate\\build_chapel_upstairs.py"

  * 3,1,1, over the chapel (13-19, 7-12 on 3,1,0): stone walls inside, plank floor, the chapel's upper front with its
    stained glass and the bell tower; a bed, bookshelves, a writing desk; the bell (Chapel_Bell001: Ring it).
  * 3,1,0: stairs up (Stairs001) in the corner left of the altar; Brother Aldous a step aside to let you by.
  * Sounds\\Bell.wav: a church bell, struck - made here from its partials (a bell's hum, prime, minor third, fifth,
    octave...), each ringing on and fading at its own rate.
"""
import math
import os
import random
import struct
import sys
import wave

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame  # noqa: E402
from dragonsword import ini  # noqa: E402
from build_isle import Map, TW, DATA, TILES_INI, write_script  # noqa: E402

CHAPEL = (13, 7, 19, 12)
STAIRS = (14, 8)
BELL = (16, 11)
RATE = 22050


def bell_sound():
    """A bell, struck: its partials (as ratios of the strike note), each with its loudness and how long it rings."""
    base = 233.0
    partials = [(0.5, 0.55, 5.0), (1.0, 0.8, 3.6), (1.19, 0.45, 2.8), (1.5, 0.3, 2.2), (2.0, 0.5, 2.0),
                (2.51, 0.22, 1.4), (2.67, 0.18, 1.2), (3.01, 0.14, 0.9), (4.17, 0.08, 0.5)]
    secs = 4.5
    n = int(RATE * secs)
    rng = random.Random(7)
    out = []
    for i in range(n):
        t = i / RATE
        v = 0.0
        for ratio, amp, ring in partials:
            v += amp * math.exp(-t / ring * 1.6) * math.sin(2 * math.pi * base * ratio * t + ratio)
        if t < 0.02:                                     # (the clapper's strike)
            v += (rng.random() * 2 - 1) * 0.6 * (1 - t / 0.02)
        attack = min(1.0, t / 0.004)
        out.append(max(-1.0, min(1.0, v * 0.28 * attack)))
    path = os.path.join(ROOT, "Sounds", "Bell.wav")
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(b"".join(struct.pack("<h", int(s * 32000)) for s in out))
    print("Made Sounds\\Bell.wav")


def bell_picture():
    """A bronze bell hanging from its beam (decor)."""
    pygame.init()
    pygame.display.set_mode((1, 1))
    s = pygame.Surface((32, 32), pygame.SRCALPHA)
    pygame.draw.rect(s, (70, 46, 26), (2, 2, 28, 4))                         # the beam
    pygame.draw.line(s, (110, 76, 44), (2, 2), (29, 2))
    pygame.draw.rect(s, (40, 40, 44), (15, 6, 2, 3))                          # the hanger
    body = [(11, 10), (21, 10), (23, 20), (26, 25), (6, 25), (9, 20)]
    pygame.draw.polygon(s, (60, 40, 14), [(x, y + 1) for x, y in body])
    pygame.draw.polygon(s, (200, 150, 60), body)
    pygame.draw.polygon(s, (236, 196, 110), [(12, 11), (15, 11), (13, 22), (9, 24)])   # (the light on it)
    pygame.draw.rect(s, (150, 104, 36), (6, 23, 20, 2))                       # the lip
    pygame.draw.circle(s, (90, 64, 30), (16, 27), 2)                          # the clapper
    pygame.draw.line(s, (200, 180, 140), (22, 9), (26, 30))                   # the rope
    pygame.image.save(s, os.path.join(ROOT, "Sprites", "Tiles", "Chapel_Bell001.png"))
    if not ini.section("Chapel_Bell001", TILES_INI):
        for k, v in (("Walkable.Data", "0" * 49), ("Show.Name", "1"), ("Use.Words", "Ring,Examine"),
                     ("Examine.Info", "The chapel's bell, green with age. Its rope hangs within reach."),
                     ("Line.of.Sight", "1"), ("Layer", "Decor")):
            ini.write("Chapel_Bell001", k, v, TILES_INI)
    colours = os.path.join(ROOT, "Dev", "Minimap Colours.txt")
    if "\nChapel_Bell001\t" not in "\n" + ini.read_text(colours):
        with open(colours, "a", encoding="cp1252", newline="\r\n") as f:
            f.write("Chapel_Bell001\t200 150 60\n")
    print("Drew the bell")


def upstairs():
    if os.path.exists(os.path.join(ROOT, "Maps", "3,1,1.txt")):
        print("The chapel's upper floor is there already")
        return
    m = Map("3,1,1", new=True)
    x1, y1, x2, y2 = CHAPEL
    thin = {"nw": "008", "n": "001", "ne": "005", "w": "004", "e": "002"}
    for y in range(y1, y2):                                   # walls on the floor's edges, as downstairs
        for x in range(x1, x2 + 1):
            side = ("n" if y == y1 else "") + ("w" if x == x1 else "e" if x == x2 else "")
            m.set(x, y, tile="Stone_Wall_Thin_Plank" + thin[side] if side else "Plank001")
    for x in range(x1, x2 + 1):                               # the front: the upper wall, stained glass, the tower
        piece = "Chapel_Stone_Upper002" if x in (x1 + 1, x2 - 1) else "Chapel_Stone_Upper001"
        m.set(x, y2, tile="Steeple001" if x == BELL[0] else piece)
    sx, sy = STAIRS
    m.set(sx, sy, tile="Stairs002")                           # (down: the same spot as the stairs up)
    for x, y, d in ((18, 8, "Bed001"), (15, 8, "Bookshelf001"), (16, 8, "Bookshelf001"),
                    (17, 10, "Table001"), (18, 10, "Candles001"), (17, 11, "Chair002"),
                    (BELL[0], BELL[1], "Chapel_Bell001"), (14, 11, "Barrel001")):
        m.set(x, y, decor=d)
    t, over = m.parts(15, 10)                                 # a rug by the desk
    over["Under"] = "Rug017"
    m.put(15, 10, t, over)
    m.ents = ["Id\tChapel_Loft\t15\t9"]
    m.save()
    print("Made Maps\\3,1,1 (the chapel's upper floor)")


def downstairs():
    m = Map("3,1,0")
    sx, sy = STAIRS
    if m.tile(sx, sy) != "Stairs001":
        m.set(sx, sy, tile="Stairs001", decor="")
    ents = []
    for ln in m.ents:                                         # (Brother Aldous: a step aside, off the stairs' foot)
        p = ln.split("\t")
        if len(p) >= 5 and p[0] == "NPC" and "Id=Chapel_Verger" in p[4] and int(float(p[2])) == (sx - 1) * TW:
            p[2] = str(sx * TW)
            ln = "\t".join(p)
        ents.append(ln)
    m.ents = ents
    m.save()
    write_script("Ring Chapel_Bell", [
        "01\tPlay.Sound\tBell",
        "02\tDisplay.Message\tYellow\tDONNNG... The bell's voice rolls out over the Isle.",
        "03\tEnd",
    ])
    music = os.path.join(DATA, "Music.ini")
    if not ini.read("Maps", "3,1,1", "", music) and ini.read("Maps", "3,1,0", "", music):
        ini.write("Maps", "3,1,1", ini.read("Maps", "3,1,0", "", music), music)
    print("Stairs up by the altar; Brother Aldous a step aside; the bell rings")


def main():
    bell_sound()
    bell_picture()
    upstairs()
    downstairs()


if __name__ == "__main__":
    main()
