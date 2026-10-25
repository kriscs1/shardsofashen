"""Cats: a grey tabby (Cat), a black cat (Black_Cat) and a ginger (Ginger_Cat) - drawn, given a meow and a purr,
put about the towns - and Jimmy, a strawberry-blond ginger (Strawberry_Cat: no white on him), at home in the cottage where
new characters wake; Noops (Fat_Grey_Cat: very round, dark grey, his face and legs paler) by the Isle's bank, Vincent
(Southport's black cat) and Mo (Tuxedo_Cat: black, a white bib and white socks) by Ashford's market.
Run it again to draw and make the sounds again; the cats are only placed once.

  python -I "Dev\\migrate\\build_cats.py"

  * Sprites\\Walk\\<Cat>2a-c / 8a-c (trotting, right and left), Sprites\\Entities\\<Cat>.png, and <Cat>_Sit2 / _Sit8
    (sitting: States=Sit, its pose when it stops a while), _Stretch2 / 8 and _Butt2 / 8 (Fidgets=: for a moment,
    now and then, a stretch or its back to you).
  * Sounds\\Meow.wav (a "mrrow?": its pitch up, then down) and Purr.wav (a rumble, in and out).
  * Entities.ini: friendly (Attitude=Good), not solid (they don't block a doorway), Talk to (a meow), Stroke (a purr).
  * A cat by each of a few towns' squares; the named cats (Id= and Name=, with a meow and a purr of their own).
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
# fur, its shadow, its light, the chest, the eye, stripes?, what you see on Examine (and LOOKS: what's its own)
CATS = {
    "Cat": ((150, 150, 156), (96, 96, 104), (192, 192, 198), (224, 224, 228), (130, 196, 90), True,
            "A grey tabby cat, watching you with half-closed eyes."),
    "Black_Cat": ((48, 44, 50), (26, 24, 28), (86, 82, 92), (62, 58, 66), (232, 204, 60), False,
                  "A sleek black cat. Lucky, probably."),
    "Ginger_Cat": ((232, 166, 110), (198, 120, 72), (250, 208, 164), (252, 236, 214), (112, 172, 90), True,
                   "A ginger cat - more strawberry-blond, really."),
    "Strawberry_Cat": ((240, 182, 132), (210, 136, 92), (252, 214, 176), (246, 198, 154), (112, 172, 90), True,
                       "A strawberry-blond cat, ginger from nose to tail."),     # (Jimmy: no white on him anywhere)
    "Fat_Grey_Cat": ((92, 92, 100), (58, 58, 66), (122, 122, 130), (168, 168, 176), (214, 180, 70), False,
                     "A very round dark grey cat, his face and legs a paler grey."),   # (Noops)
    "Tuxedo_Cat": ((44, 40, 46), (24, 22, 26), (80, 76, 86), (244, 244, 246), (150, 206, 96), False,
                   "A black cat with a white bib and four white socks."),      # (Mo)
}
LOOKS = {   # face, legs, paws (socks), fat?
    "Fat_Grey_Cat": {"face": (150, 150, 158), "legs": (150, 150, 158), "fat": True},
    "Tuxedo_Cat": {"paws": (244, 244, 246)},
}
LEGS = [(12, (0, 1, -1), True), (14, (0, -1, 1), False), (18, (0, -1, 1), True), (20, (0, 1, -1), False)]
RATE = 22050


# ---------------------------------------------------------------- the pictures
def draw_head(s, hx, hy, fur, dark, chest, eye, stripes, face):
    """The head: big and round, ears up, big shining eyes, a nose, a smile, rosy cheeks."""
    pygame.draw.polygon(s, fur, [(hx - 5, hy - 1), (hx - 4, hy - 7), (hx, hy - 4)])
    pygame.draw.polygon(s, fur, [(hx, hy - 4), (hx + 4, hy - 7), (hx + 5, hy - 1)])
    pygame.draw.line(s, (240, 168, 178), (hx - 3, hy - 5), (hx - 3, hy - 3))  # (pink inside the ears)
    pygame.draw.line(s, (240, 168, 178), (hx + 3, hy - 5), (hx + 3, hy - 3))
    pygame.draw.circle(s, face or fur, (hx, hy), 5)
    pygame.draw.ellipse(s, face or chest, (hx - 3, hy + 1, 7, 4))             # the muzzle
    if stripes:
        pygame.draw.line(s, dark, (hx, hy - 4), (hx, hy - 3))
        s.set_at((hx - 2, hy - 4), dark)
        s.set_at((hx + 2, hy - 4), dark)
    for ex in (hx - 3, hx + 1):                                               # big eyes, a shine in each
        if sum(face or fur) < 200:                                            # (a dark cat: its eyes all gold)
            pygame.draw.rect(s, eye, (ex, hy - 2, 2, 3))
            s.set_at((ex + 1, hy - 1), (24, 20, 24))
        else:
            pygame.draw.rect(s, (24, 20, 24), (ex, hy - 2, 2, 3))
            s.set_at((ex + 1, hy), eye)
        s.set_at((ex, hy - 2), (255, 255, 255))
    s.set_at((hx, hy + 1), (236, 128, 146))                                   # the nose
    s.set_at((hx - 1, hy + 2), (120, 80, 80))                                 # (a little smile)
    s.set_at((hx + 1, hy + 2), (120, 80, 80))
    s.set_at((hx - 4, hy + 1), (246, 150, 160))                               # (rosy cheeks)
    s.set_at((hx + 4, hy + 1), (246, 150, 160))


def outlined(s, hx, hy, whiskers=True):
    """The 1 px dark outline round it (the mask's silhouette, a pixel out each way), the whiskers over it."""
    shape = pygame.mask.from_surface(s)
    out = pygame.Surface((32, 32), pygame.SRCALPHA)
    sil = shape.to_surface(setcolor=OUTLINE + (255,), unsetcolor=(0, 0, 0, 0))
    for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        out.blit(sil, (dx, dy))
    out.blit(s, (0, 0))
    for wy in (hy + 1, hy + 2) if whiskers else ():                                                # whiskers (over the outline)
        out.set_at((hx + 6, wy), (236, 236, 236))
        out.set_at((hx - 6, wy), (236, 236, 236))
    return out


def draw_cat(fur, dark, light, chest, eye, stripes, frame, face=None, legs=None, paws=None, fat=False):
    """A small cat, drawn to be sweet: a big round head turned to you, big shining eyes, a little body, stubby legs."""
    s = pygame.Surface((32, 32), pygame.SRCALPHA)
    bob = (0, -1, 0)[frame]

    def leg(x, dx, far):
        pygame.draw.line(s, dark if far else (legs or fur), (x, 23 + bob), (x + dx, 26), 2)
        if paws:                                                              # (white socks)
            pygame.draw.line(s, paws, (x + dx, 26), (x + dx + 1, 26))
        pygame.draw.line(s, paws or (dark if far else (legs or chest)), (x + dx, 27), (x + dx + 1, 27))   # (a paw)
    for x, offs, far in LEGS:
        if far:
            leg(x, offs[frame], True)
    sway = (0, 1, -1)[frame]                                                  # the tail: up, curling at its tip
    pts = [(11, 22 + bob), (8, 19 + bob), (8 + sway, 15 + bob), (10 + sway, 13 + bob)]
    pygame.draw.lines(s, fur, False, pts, 2)
    s.set_at((10 + sway, 13 + bob), dark if stripes else light)
    if fat:                                                                   # the body: small and round (or round)
        pygame.draw.ellipse(s, fur, (8, 17 + bob, 16, 10))
        pygame.draw.ellipse(s, chest, (16, 20 + bob, 6, 5))
        pygame.draw.line(s, light, (11, 17 + bob), (18, 17 + bob))
    else:
        pygame.draw.ellipse(s, fur, (10, 19 + bob, 12, 7))
        pygame.draw.ellipse(s, chest, (16, 21 + bob, 5, 4))                   # (the chest)
        pygame.draw.line(s, light, (12, 19 + bob), (17, 19 + bob))            # (light along its back)
    if stripes:
        for x in (13, 16):
            pygame.draw.line(s, dark, (x, 20 + bob), (x, 21 + bob))
    hx, hy = 21, 16 + bob
    draw_head(s, hx, hy, fur, dark, chest, eye, stripes, face)
    for x, offs, far in LEGS:
        if not far:
            leg(x, offs[frame], False)
    return outlined(s, hx, hy)


def draw_sitting(fur, dark, light, chest, eye, stripes, face=None, legs=None, paws=None, fat=False):
    """The cat sitting down, side on: its haunch round at the back, front legs straight, its tail round its feet."""
    s = pygame.Surface((32, 32), pygame.SRCALPHA)
    w = 12 if fat else 10
    pygame.draw.lines(s, fur, False, [(10 - (2 if fat else 0), 26), (13, 28), (19, 28), (22, 27)], 2)   # the tail
    s.set_at((22, 27), dark if stripes else light)
    pygame.draw.ellipse(s, fur, (19 - w, 15 if fat else 17, w + 3, 13 if fat else 11))   # the haunch (round, if fat)
    pygame.draw.ellipse(s, fur, (13 if fat else 14, 14, 10 if fat else 8, 13))           # the body, upright
    pygame.draw.ellipse(s, chest, (17, 17, 5, 7))                             # (the chest)
    pygame.draw.line(s, light, (12 - (3 if fat else 0), 19), (15, 16))        # (light along its back)
    if stripes:
        for x in (12, 14):
            pygame.draw.line(s, dark, (x, 20), (x + 1, 22))
    for x in (17, 20):                                                        # the front legs, straight down
        pygame.draw.line(s, legs or fur, (x, 23), (x, 26), 2)
        pygame.draw.line(s, paws or legs or chest, (x, 27), (x + 1, 27))
    hx, hy = 19, 11
    draw_head(s, hx, hy, fur, dark, chest, eye, stripes, face)
    return outlined(s, hx, hy)


def draw_stretch(fur, dark, light, chest, eye, stripes, face=None, legs=None, paws=None, fat=False):
    """A long stretch, side on: front legs out along the ground, chest down, its rump and tail up in the air."""
    s = pygame.Surface((32, 32), pygame.SRCALPHA)
    pygame.draw.lines(s, fur, False, [(10, 16), (8, 11), (9, 6), (11, 5)], 2)  # the tail, straight up
    s.set_at((11, 5), dark if stripes else light)
    for x in (10, 13):                                                        # the back legs, straight
        pygame.draw.line(s, legs or fur, (x, 19), (x, 26), 2)
        pygame.draw.line(s, paws or legs or chest, (x, 27), (x + 1, 27))
    r = 4 if fat else 3
    pygame.draw.line(s, fur, (12, 18), (21, 23), r * 2)                       # the body, sloping down to the chest
    pygame.draw.circle(s, fur, (12, 18), r + 1)
    pygame.draw.circle(s, fur, (21, 23), r)
    pygame.draw.line(s, light, (10, 15), (16, 18))                            # (light along its back)
    if stripes:
        for x in (14, 17):
            pygame.draw.line(s, dark, (x, 18), (x + 1, 19))
    for x in (22, 24):                                                        # the front legs, out in front
        pygame.draw.line(s, legs or fur, (x - 2, 25), (x + 5, 26), 2)
        pygame.draw.line(s, paws or legs or chest, (x + 5, 27), (x + 6, 27))
    hx, hy = 23, 20
    draw_head(s, hx, hy, fur, dark, chest, eye, stripes, face)
    return outlined(s, hx, hy)


def draw_butt(fur, dark, light, chest, eye, stripes, face=None, legs=None, paws=None, fat=False):
    """Turned away, tail straight up: the view every cat owner knows."""
    s = pygame.Surface((32, 32), pygame.SRCALPHA)
    w = 16 if fat else 13
    pygame.draw.polygon(s, fur, [(11, 9), (12, 3), (15, 7)])                  # the ears, from behind
    pygame.draw.polygon(s, fur, [(17, 7), (20, 3), (21, 9)])
    pygame.draw.circle(s, fur, (16, 10), 5)                                   # the back of its head
    pygame.draw.ellipse(s, fur, (16 - w // 2, 13, w, 13))                     # its back
    for x in (16 - w // 2 + 3, 16 + w // 2 - 3):                             # the haunches
        pygame.draw.circle(s, fur, (x, 23), 4 if fat else 3)
        pygame.draw.line(s, paws or legs or dark, (x - 1, 27), (x + 1, 27))   # (the back feet)
    pygame.draw.line(s, light, (16 - w // 2 + 2, 16), (16 - w // 2 + 2, 20))  # (light down one side)
    if stripes:
        for y in (15, 18):
            pygame.draw.line(s, dark, (14, y), (18, y))
    pygame.draw.line(s, dark, (13, 14), (19, 14))                             # (where its head meets its back)
    tail = [(16, 21), (19, 17), (23, 12), (25, 7), (24, 4)]                   # the tail, up like a flag
    pygame.draw.lines(s, dark, False, [(x - 1, y + 1) for x, y in tail[:3]], 1)   # (its shadow on the back)
    pygame.draw.lines(s, fur, False, tail, 2)
    s.set_at((24, 4), dark if stripes else light)
    s.set_at((16, 23), (200, 110, 120))                                       # (ahem)
    return outlined(s, 16, 10, whiskers=False)


FIDGETS = {"Stretch": draw_stretch, "Butt": draw_butt}   # (now and then, at rest: Fidgets=)


def pictures():
    pygame.init()
    pygame.display.set_mode((1, 1))
    walk, ents = os.path.join(ROOT, "Sprites", "Walk"), os.path.join(ROOT, "Sprites", "Entities")
    for name, pal in CATS.items():
        looks = LOOKS.get(name, {})
        frames = [draw_cat(*pal[:6], frame=i, **looks) for i in range(3)]
        for f, img in zip("abc", frames):
            pygame.image.save(img, os.path.join(walk, "%s2%s.png" % (name, f)))
            pygame.image.save(pygame.transform.flip(img, True, False), os.path.join(walk, "%s8%s.png" % (name, f)))
        pygame.image.save(frames[0], os.path.join(ents, name + ".png"))
        sit = draw_sitting(*pal[:6], **looks)                                 # (at rest: States=Sit)
        pygame.image.save(sit, os.path.join(ents, name + "_Sit2.png"))
        pygame.image.save(pygame.transform.flip(sit, True, False), os.path.join(ents, name + "_Sit8.png"))
        for fid, draw in FIDGETS.items():                                     # (a moment's stretch, or its back to you)
            img = draw(*pal[:6], **looks)
            pygame.image.save(img, os.path.join(ents, "%s_%s2.png" % (name, fid)))
            pygame.image.save(pygame.transform.flip(img, True, False), os.path.join(ents, "%s_%s8.png" % (name, fid)))
    print("Drew the cats, walking, sitting, stretching and turned away: %s" % ", ".join(CATS))


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
NAMED = {   # a cat of its own: its kind, the place it lives by, a meow and a purr of its own
    "Jimmy": ("Strawberry_Cat", None, "Jimmy looks up at you and gives a little chirp, very pleased with himself.",
              "Jimmy purrs like a little engine and headbutts your hand for more."),
    "Noops": ("Fat_Grey_Cat", "Isle_Bank", "Noops opens one eye, considers you, and closes it again.",
              "Noops rolls onto his back, a great grey belly to the sky, and rumbles."),
    "Vincent": ("Black_Cat", "Southport_Landing", "Vincent gives you a long, cool look. \"Mrrp.\"",
                "Vincent leans into your hand, then strolls off as if it never happened."),
    "Mo": ("Tuxedo_Cat", "Ashford_Market_Square", "Mo trots up, white socks twinkling, and mews at you.",
           "Mo kneads the air with a white paw and purrs."),
}


def data():
    ents = os.path.join(DATA, "Entities.ini")
    for name, pal in CATS.items():
        if not ini.section(name, ents):
            for k, v in (("Type", "NPC"), ("Use.Words", "Stroke,Talk to"), ("Examine.Info", pal[6]),
                         ("Movement.Speed", "1.5"), ("Roam.Radius", "3"), ("Chase.Radius", "0"), ("Walk.Speed", "0.4"),
                         ("Pause", "3-10"), ("Attitude", "Good"), ("Solid", "0")):
                ini.write(name, k, v, ents)
            write_script("Talk to " + name, ["01\tPlay.Sound\tMeow", "02\tDisplay.Message\tCyan\tMrrow?", "03\tEnd"])
            write_script("Stroke " + name, ["01\tPlay.Sound\tPurr",
                                            "02\tDisplay.Message\tCyan\tThe cat arches its back and purrs.", "03\tEnd"])
        if not ini.read(name, "Respawn", "", ents):
            ini.write(name, "Respawn", "300", ents)                    # (back five minutes after it's gone)
        if ini.read(name, "States", "", ents) != "Sit":
            ini.write(name, "States", "Sit", ents)                     # (it sits down when it stops a while)
        if ini.read(name, "Fidgets", "", ents) != ",".join(FIDGETS):
            ini.write(name, "Fidgets", ",".join(FIDGETS), ents)        # (now and then a stretch, or its back to you)
    for who, (kind, _, meow, purr) in NAMED.items():
        write_script("Talk to " + who, ["01\tPlay.Sound\tMeow", "02\tDisplay.Message\tCyan\t" + meow, "03\tEnd"])
        write_script("Stroke " + who, ["01\tPlay.Sound\tPurr", "02\tDisplay.Message\tCyan\t" + purr, "03\tEnd"])
    print("Entities and scripts for the cats (they sit); %s their own" % ", ".join(NAMED))


TOWN_CATS = [("Ashford_Market", "Cat"), ("Southport_Landing", "Black_Cat"), ("Oakhollow_Square", "Ginger_Cat"),
             ("Fenwick_Square", "Cat"), ("Moorcross_Square", "Black_Cat"), ("Highwatch_Square", "Ginger_Cat"),
             ("Isle_Landing", "Cat")]


def free_spot(m, pl):
    spots = sorted(((x, y) for y in range(max(2, pl.ty - 4), min(20, pl.ty + 4) + 1)
                    for x in range(max(2, pl.tx - 4), min(24, pl.tx + 4) + 1)
                    if m.open_ground(x, y, 0) and not m.ent_near(x, y)),
                   key=lambda p: abs(p[0] - pl.tx) + abs(p[1] - pl.ty))
    return spots[min(2, len(spots) - 1)] if spots else None


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
        spot = free_spot(m, pl)
        if not spot:
            continue
        x, y = spot
        m.ents.append(obj_line("NPC", kind, x, y, "Attitude=Good Zone=%d,%d,%d,%d" %
                               (max(2, x - 3), max(2, y - 3), min(24, x + 3), min(20, y + 3)), -8))
        m.save()
        n += 1
    c = Map("4,0,0")                                         # Jimmy, at home in the cottage
    if not c.has_line("Id=Jimmy"):
        c.ents.append(obj_line("NPC", "Strawberry_Cat", 9, 12, "Attitude=Good Zone=6,10,9,12 Pause=6-15 Id=Jimmy Name=Jimmy",
                               -8))
        c.save()
        n += 1
    vincent = d.place("Southport_Landing")                   # (the black cat by Southport's landing is Vincent)
    if vincent is not None:
        m = Map(vincent.map)
        for i, ln in enumerate(m.ents):
            if ln.startswith("NPC\tBlack_Cat\t") and "Id=" not in ln:
                m.ents[i] = ln + " Id=Vincent Name=Vincent"
                m.save()
                n += 1
                break
    for who, (kind, place_id, _, _) in NAMED.items():        # Noops by the Isle's bank, Mo by Ashford's market
        pl = d.place(place_id) if place_id and who != "Vincent" else None
        if pl is None or any(("Id=%s " % who) in ln + " " for name in all_maps() for ln in Map(name).ents):
            continue
        m = Map(pl.map)
        spot = free_spot(m, pl)
        if not spot:
            continue
        x, y = spot
        m.ents.append(obj_line("NPC", kind, x, y, "Attitude=Good Zone=%d,%d,%d,%d Pause=5-14 Id=%s Name=%s" % (
            max(2, x - 3), max(2, y - 3), min(24, x + 3), min(20, y + 3), who, who), -8))
        m.save()
        n += 1
    print("Cats about the towns: Jimmy in the cottage, Noops, Vincent and Mo (%d placed)" % n)


def all_maps():
    return [f[:-4] for f in os.listdir(os.path.join(ROOT, "Maps")) if f.endswith(".txt")]


def main():
    pictures()
    sounds()
    data()
    place()


if __name__ == "__main__":
    main()
