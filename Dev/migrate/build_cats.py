"""Cats: a grey tabby (Cat), a black cat (Black_Cat) and a ginger (Ginger_Cat) - drawn, given a meow and a purr,
put about the towns - and Jimmy, a strawberry-blond ginger, at home in the cottage where new characters wake.
Run it again to draw and make the sounds again; the cats are only placed once.

  python -I "Dev\\migrate\\build_cats.py"

  * Sprites\\Walk\\<Cat>2a-c / 8a-c (trotting, right and left), Sprites\\Entities\\<Cat>.png.
  * Sounds\\Meow.wav (a "mrrow?": its pitch up, then down) and Purr.wav (a rumble, in and out).
  * Entities.ini: friendly (Attitude=Good), not solid (they don't block a doorway), Talk to (a meow), Stroke (a purr).
  * A cat by each of a few towns' squares; Jimmy (Ginger_Cat, Id=Jimmy, Name=Jimmy) in the cottage, 4,0,0.
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
from build_isle import Map, TW, DATA, obj_line, write_script  # noqa: E402

OUTLINE = (34, 30, 30)
# fur, its shadow, its light, the chest, the eye, stripes?
CATS = {
    "Cat": ((150, 150, 156), (96, 96, 104), (192, 192, 198), (224, 224, 228), (130, 196, 90), True,
            "A grey tabby cat, watching you with half-closed eyes."),
    "Black_Cat": ((48, 44, 50), (26, 24, 28), (86, 82, 92), (62, 58, 66), (232, 204, 60), False,
                  "A sleek black cat. Lucky, probably."),
    "Ginger_Cat": ((232, 166, 110), (198, 120, 72), (250, 208, 164), (252, 236, 214), (112, 172, 90), True,
                   "A ginger cat - more strawberry-blond, really."),
}
LEGS = [(12, (0, 1, -1), True), (14, (0, -1, 1), False), (18, (0, -1, 1), True), (20, (0, 1, -1), False)]
RATE = 22050


# ---------------------------------------------------------------- the pictures
def draw_cat(fur, dark, light, chest, eye, stripes, frame):
    """A small cat, drawn to be sweet: a big round head turned to you, big shining eyes, a little body, stubby legs."""
    s = pygame.Surface((32, 32), pygame.SRCALPHA)
    bob = (0, -1, 0)[frame]

    def leg(x, dx, far):
        pygame.draw.line(s, dark if far else fur, (x, 23 + bob), (x + dx, 26), 2)
        pygame.draw.line(s, dark if far else chest, (x + dx, 27), (x + dx + 1, 27))       # (a paw)
    for x, offs, far in LEGS:
        if far:
            leg(x, offs[frame], True)
    sway = (0, 1, -1)[frame]                                                  # the tail: up, curling at its tip
    pts = [(11, 22 + bob), (8, 19 + bob), (8 + sway, 15 + bob), (10 + sway, 13 + bob)]
    pygame.draw.lines(s, fur, False, pts, 2)
    s.set_at((10 + sway, 13 + bob), dark if stripes else light)
    pygame.draw.ellipse(s, fur, (10, 19 + bob, 12, 7))                        # the body: small and round
    pygame.draw.ellipse(s, chest, (16, 21 + bob, 5, 4))                       # (the chest)
    pygame.draw.line(s, light, (12, 19 + bob), (17, 19 + bob))                # (light along its back)
    if stripes:
        for x in (13, 16):
            pygame.draw.line(s, dark, (x, 20 + bob), (x, 21 + bob))
    hx, hy = 21, 16 + bob                                                     # the head: big and round, ears up
    pygame.draw.polygon(s, fur, [(16, hy - 1), (17, hy - 7), (21, hy - 4)])
    pygame.draw.polygon(s, fur, [(21, hy - 4), (25, hy - 7), (26, hy - 1)])
    pygame.draw.line(s, (240, 168, 178), (18, hy - 5), (18, hy - 3))          # (pink inside the ears)
    pygame.draw.line(s, (240, 168, 178), (24, hy - 5), (24, hy - 3))
    pygame.draw.circle(s, fur, (hx, hy), 5)
    pygame.draw.ellipse(s, chest, (18, hy + 1, 7, 4))                         # the muzzle
    if stripes:
        pygame.draw.line(s, dark, (21, hy - 4), (21, hy - 3))
        s.set_at((19, hy - 4), dark)
        s.set_at((23, hy - 4), dark)
    for ex in (18, 22):                                                       # big eyes, a shine in each
        if sum(fur) < 200:                                                    # (a dark cat: its eyes all gold)
            pygame.draw.rect(s, eye, (ex, hy - 2, 2, 3))
            s.set_at((ex + 1, hy - 1), (24, 20, 24))
        else:
            pygame.draw.rect(s, (24, 20, 24), (ex, hy - 2, 2, 3))
            s.set_at((ex + 1, hy), eye)
        s.set_at((ex, hy - 2), (255, 255, 255))
    s.set_at((21, hy + 1), (236, 128, 146))                                   # the nose
    s.set_at((20, hy + 2), (120, 80, 80))                                     # (a little smile)
    s.set_at((22, hy + 2), (120, 80, 80))
    s.set_at((17, hy + 1), (246, 150, 160))                                   # (rosy cheeks)
    s.set_at((25, hy + 1), (246, 150, 160))
    for x, offs, far in LEGS:
        if not far:
            leg(x, offs[frame], False)
    shape = pygame.mask.from_surface(s)
    out = pygame.Surface((32, 32), pygame.SRCALPHA)
    sil = shape.to_surface(setcolor=OUTLINE + (255,), unsetcolor=(0, 0, 0, 0))
    for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        out.blit(sil, (dx, dy))
    out.blit(s, (0, 0))
    for wy in (hy + 1, hy + 2):                                                # whiskers (over the outline)
        out.set_at((27, wy), (236, 236, 236))
        out.set_at((15, wy), (236, 236, 236))
    return out


def pictures():
    pygame.init()
    pygame.display.set_mode((1, 1))
    walk, ents = os.path.join(ROOT, "Sprites", "Walk"), os.path.join(ROOT, "Sprites", "Entities")
    for name, pal in CATS.items():
        frames = [draw_cat(*pal[:6], frame=i) for i in range(3)]
        for f, img in zip("abc", frames):
            pygame.image.save(img, os.path.join(walk, "%s2%s.png" % (name, f)))
            pygame.image.save(pygame.transform.flip(img, True, False), os.path.join(walk, "%s8%s.png" % (name, f)))
        pygame.image.save(frames[0], os.path.join(ents, name + ".png"))
    print("Drew the cats: %s" % ", ".join(CATS))


# ---------------------------------------------------------------- the sounds
def write_wav(name, samples):
    with wave.open(os.path.join(ROOT, "Sounds", name + ".wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(b"".join(struct.pack("<h", int(max(-1, min(1, v)) * 30000)) for v in samples))


def meow():
    """A "mrrow?": a voice whose pitch climbs, then falls away, its vowel opening from "mm" to "ow"."""
    secs = 0.6
    out, phase = [], 0.0
    for i in range(int(RATE * secs)):
        t = i / RATE
        u = t / secs
        f = 420 + 380 * math.sin(math.pi * min(1.0, u * 1.6)) - 120 * max(0.0, u - 0.6)
        phase += 2 * math.pi * f / RATE
        bright = 0.2 + 0.8 * math.sin(math.pi * u)                        # ("mm" - "ee" - "ow")
        v = sum(math.sin(phase * h) * (bright ** (h - 1)) / h for h in range(1, 9))
        env = min(1.0, t / 0.05) * min(1.0, (secs - t) / 0.15)
        out.append(v * env * 0.45)
    write_wav("Meow", out)


def purr():
    """A purr: a low rumble, pulsing some twenty-five times a second, breathed in and out."""
    rng = random.Random(3)
    secs = 1.8
    out, low = [], 0.0
    for i in range(int(RATE * secs)):
        t = i / RATE
        low += (rng.uniform(-1, 1) - low) * 0.05                            # (noise, its highs taken off)
        pulse = 0.5 + 0.5 * math.sin(2 * math.pi * 26 * t)
        breath = 0.55 + 0.45 * math.sin(2 * math.pi * t / 0.9 - 1.2)
        env = min(1.0, t / 0.1) * min(1.0, (secs - t) / 0.3)
        out.append((low * 3.5 + 0.25 * math.sin(2 * math.pi * 52 * t)) * pulse ** 2 * breath * env)
    write_wav("Purr", out)


def sounds():
    meow()
    purr()
    print("Made Sounds\\Meow.wav and Purr.wav")


# ---------------------------------------------------------------- the data, and where they live
def data():
    ents = os.path.join(DATA, "Entities.ini")
    for name, pal in CATS.items():
        if ini.section(name, ents):
            continue
        for k, v in (("Type", "NPC"), ("Use.Words", "Stroke,Talk to"), ("Examine.Info", pal[6]),
                     ("Movement.Speed", "1.5"), ("Roam.Radius", "3"), ("Chase.Radius", "0"), ("Walk.Speed", "0.4"),
                     ("Pause", "3-10"), ("Attitude", "Good"), ("Solid", "0")):
            ini.write(name, k, v, ents)
        write_script("Talk to " + name, ["01\tPlay.Sound\tMeow", "02\tDisplay.Message\tCyan\tMrrow?", "03\tEnd"])
        write_script("Stroke " + name, ["01\tPlay.Sound\tPurr",
                                        "02\tDisplay.Message\tCyan\tThe cat arches its back and purrs.", "03\tEnd"])
    write_script("Talk to Jimmy", [
        "01\tPlay.Sound\tMeow",
        "02\tDisplay.Message\tCyan\tJimmy looks up at you and gives a little chirp, very pleased with himself.",
        "03\tEnd"])
    write_script("Stroke Jimmy", [
        "01\tPlay.Sound\tPurr",
        "02\tDisplay.Message\tCyan\tJimmy purrs like a little engine and headbutts your hand for more.",
        "03\tEnd"])
    print("Entities and scripts for the cats; Jimmy's own")


TOWN_CATS = [("Ashford_Market", "Cat"), ("Southport_Landing", "Black_Cat"), ("Oakhollow_Square", "Ginger_Cat"),
             ("Fenwick_Square", "Cat"), ("Moorcross_Square", "Black_Cat"), ("Highwatch_Square", "Ginger_Cat"),
             ("Isle_Landing", "Cat")]


def place():
    from dsengine.data import GameData
    d = GameData(ROOT)
    n = 0
    for place_id, kind in TOWN_CATS:
        pl = d.place(place_id)
        if pl is None:
            continue
        m = Map(pl.map)
        if any(ln.startswith("NPC\t%s\t" % k) for ln in m.ents for k in CATS):
            continue
        spots = sorted(((x, y) for y in range(max(2, pl.ty - 4), min(20, pl.ty + 4) + 1)
                        for x in range(max(2, pl.tx - 4), min(24, pl.tx + 4) + 1)
                        if m.open_ground(x, y, 0) and not m.ent_near(x, y)),
                       key=lambda p: abs(p[0] - pl.tx) + abs(p[1] - pl.ty))
        if not spots:
            continue
        x, y = spots[min(2, len(spots) - 1)]
        m.ents.append(obj_line("NPC", kind, x, y, "Attitude=Good Zone=%d,%d,%d,%d" %
                               (max(2, x - 3), max(2, y - 3), min(24, x + 3), min(20, y + 3)), -8))
        m.save()
        n += 1
    c = Map("4,0,0")                                         # Jimmy, at home in the cottage
    if not c.has_line("Id=Jimmy"):
        c.ents.append(obj_line("NPC", "Ginger_Cat", 9, 12, "Attitude=Good Zone=6,10,9,12 Pause=6-15 Id=Jimmy Name=Jimmy",
                               -8))
        c.save()
        n += 1
    print("Cats about the towns, and Jimmy in the cottage (%d placed)" % n)


def main():
    pictures()
    sounds()
    data()
    place()


if __name__ == "__main__":
    main()
