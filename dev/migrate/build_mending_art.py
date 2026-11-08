"""The Mending's look and sound (Roadmap 6, group 9): its people in grey robes with glass growing through them, the robe
you can wear, the Shard Font, the great Shard, Mary's Whisper, the Ashwold's shrines lit cold and blue, a low choir's
chant and a whisper. The quests that use them are build_mending.py's.

Run:  python -I "dev\\migrate\\build_mending_art.py"
Safe to run again: only files that change are written. It writes the sections of what it draws in Entities.ini and
Tiles.ini (the people's numbers, the things' words); the robe's worn frames come from build_worn.py (its "Mending"
grey and "Robe"), run after this.
"""
import io
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import story_kit as SK                                           # noqa: E402
import build_sounds as BS                                        # noqa: E402
import build_soundscape as SS                                    # noqa: E402
import numpy as np                                               # noqa: E402
from PIL import Image                                            # noqa: E402

MAKER = "build_mending_art.py"
GLASS = ((58, 96, 150), (120, 176, 230), (210, 236, 255))         # (dark edge, body, the light in it: cold blue)
BASE = "Penitent"                                                # (Cael's grey robe and hood, with his staff)

# kind: (shown as, tint, scale, shards, how long, glass over the cloth (0..1), seed)
PEOPLE = {
    "Mending_Sister": ("Sister of the Mending", (176, 178, 184), 1.0, 2, 3, 0.0, 11),
    "Mending_Acolyte": ("Acolyte of the Mending", (150, 154, 166), 1.0, 4, 4, 0.0, 12),
    "Mending_Cantor": ("Cantor of the Mending", (132, 142, 178), 1.0, 6, 4, 0.04, 13),
    "Glassbound": ("Glassbound", (118, 122, 134), 1.3, 10, 6, 0.18, 14),
    "Eldest_of_the_Mending": ("Eldest of the Mending", (164, 172, 196), 1.45, 16, 7, 0.45, 15),
}


# ================================================================== pictures
def _png(img):
    b = io.BytesIO()
    img.save(b, "PNG", optimize=True)
    return b.getvalue()


def save_pil(kind, name, img):
    path = os.path.join(SK.SPR, kind, name + ".png")
    data = _png(img)
    if os.path.exists(path) and open(path, "rb").read() == data:
        return
    open(path, "wb").write(data)


def tint(im, col):
    """The Penitent's near-black robe made the Mending's grey (col), its shading kept and lifted, the outline (every
    pixel beside a see-through one) left dark."""
    a = np.array(im.convert("RGBA"), dtype=np.float32)
    solid = a[..., 3] > 0
    pad = np.pad(solid, 1)
    edge = solid & ~(pad[:-2, 1:-1] & pad[2:, 1:-1] & pad[1:-1, :-2] & pad[1:-1, 2:])
    lum = a[..., 0] * 0.3 + a[..., 1] * 0.59 + a[..., 2] * 0.11
    k = np.clip(0.5 + (lum - 25) / 70.0, 0.45, 1.3)[..., None]
    out = np.array(col, dtype=np.float32)[None, None, :] * k
    face = (lum >= 65)[..., None]                       # (the face in the hood: pale skin, not grey)
    out = np.where(face, np.array((206, 184, 166), dtype=np.float32)[None, None, :] * np.clip(lum / 80.0, 0.8, 1.1)[..., None], out)
    a[..., :3] = np.clip(np.where(edge[..., None], a[..., :3], out), 0, 255)
    return Image.fromarray(a.astype(np.uint8), "RGBA")


def bigger(im, scale):
    if scale == 1:
        return im
    w, h = im.size
    return im.resize((round(w * scale), round(h * scale)), Image.NEAREST)


def glassed(im, shards, length, cover, seed):
    """Glass growing through the cloth: patches of it (cover, of the robe) and crystals pushing out, up and away
    from the middle, at the same places on every frame (so it doesn't crawl as they walk)."""
    a = np.array(im.convert("RGBA"))
    h, w = a.shape[:2]
    solid = a[..., 3] > 0
    if not solid.any():
        return im
    ys, xs = np.nonzero(solid)
    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    lum = a[..., 0] * 0.3 + a[..., 1] * 0.59 + a[..., 2] * 0.11
    cloth = solid & (lum >= 42)
    rng = random.Random(seed)
    if cover > 0:                                       # (patches: the cloth turned to glass, shaded as it was)
        for _ in range(int(3 + cover * 14)):
            cx = x0 + rng.random() * (x1 - x0)
            cy = y0 + (0.25 + rng.random() * 0.75) * (y1 - y0)
            r = 1.5 + cover * 7 * rng.random()
            yy, xx = np.ogrid[:h, :w]
            patch = cloth & ((xx - cx) ** 2 + (yy - cy) ** 2 <= r * r)
            band = np.clip(lum / 70.0, 0, 2).astype(int)
            for k in range(3):
                a[patch & (band == k)] = GLASS[k] + (255,)
    mid = (x0 + x1) / 2.0
    for _ in range(shards):                             # (crystals: from a spot on the cloth, out and up)
        fx, fy = rng.random(), 0.2 + rng.random() * 0.6
        sx, sy = int(x0 + fx * (x1 - x0)), int(y0 + fy * (y1 - y0))
        near = [(abs(x - sx) + abs(y - sy), x, y) for y in range(max(0, sy - 3), min(h, sy + 4))
                for x in range(max(0, sx - 3), min(w, sx + 4)) if cloth[y, x]]
        if not near:
            continue
        _, sx, sy = min(near)
        dx = -1 if sx < mid - 1 else (1 if sx > mid + 1 else 0)
        n = max(2, int(length * (0.5 + rng.random() * 0.5)))
        for i in range(n):
            x, y = sx + int(round(dx * i * 0.6)), sy - i
            if 0 <= x < w and 0 <= y < h:
                a[y, x] = (GLASS[2] if i >= n - 2 else GLASS[1]) + (255,)
            if i < n - 1 and 0 <= x + 1 < w and 0 <= y < h:
                a[y, x + 1] = GLASS[0] + (255,)
    return Image.fromarray(a, "RGBA")


def people():
    walk = os.path.join(SK.SPR, "Walk")
    for name, (_, col, scale, shards, length, cover, seed) in PEOPLE.items():
        paint = lambda im: glassed(bigger(tint(im, col), scale), shards, length, cover, seed)   # noqa: E731
        for d in "1248":
            for f in "abc":
                src = os.path.join(walk, "%s%s%s.png" % (BASE, d, f))
                if os.path.exists(src):
                    save_pil("Walk", "%s%s%s" % (name, d, f), paint(Image.open(src)))
        save_pil("Entities", name, paint(Image.open(os.path.join(SK.SPR, "Entities", BASE + ".png"))))


def things():
    p = SK.pg()
    D = p.draw
    dark, body, light = GLASS
    # the robe, folded: grey wool, a cord belt, a sliver of glass at the collar
    s = SK.surface()
    D.polygon(s, (128, 130, 138), [(9, 9), (23, 9), (27, 28), (5, 28)])
    D.polygon(s, (150, 152, 160), [(11, 10), (21, 10), (24, 26), (8, 26)])
    D.ellipse(s, (112, 114, 122), (10, 4, 12, 9))
    D.ellipse(s, (70, 72, 80), (13, 6, 6, 5))
    D.line(s, (196, 186, 150), (7, 19), (25, 19), 2)
    D.line(s, (196, 186, 150), (16, 20), (15, 25))
    D.line(s, (104, 106, 114), (16, 12), (16, 27))
    D.polygon(s, body, [(19, 9), (21, 4), (22, 9)])
    s.set_at((21, 6), light + (255,))
    SK.save("Entities", "Mending_Robe", SK.outlined(s))
    # the Shard Font: a grey stone basin, cold blue light in the water
    s = SK.surface()
    D.rect(s, (96, 98, 106), (12, 18, 8, 10))
    D.rect(s, (82, 84, 92), (8, 27, 16, 3))
    D.ellipse(s, (120, 122, 132), (3, 9, 26, 12))
    D.ellipse(s, (84, 86, 96), (5, 10, 22, 9))
    D.ellipse(s, body, (7, 11, 18, 6))
    D.ellipse(s, light, (11, 12, 9, 3))
    for x, y in ((9, 7), (16, 4), (22, 6), (13, 2)):
        s.set_at((x, y), light + (255,))
    SK.save("Entities", "Shard_Font", SK.outlined(s))
    # the great Shard: a cluster of glass taller than a man, its heart violet (it's a Shard, after all)
    s = SK.surface(48, 64)
    for pts, shade in (([(10, 60), (6, 36), (12, 28), (17, 60)], 0), ([(30, 60), (34, 30), (40, 38), (39, 60)], 0),
                       ([(15, 61), (18, 8), (24, 2), (31, 10), (33, 61)], 1), ([(20, 58), (22, 14), (25, 9), (28, 58)], 2)):
        D.polygon(s, GLASS[shade], pts)
    D.polygon(s, (150, 104, 224), [(22, 44), (24, 30), (27, 44), (24, 54)])
    D.polygon(s, (214, 186, 255), [(23, 44), (24, 36), (26, 44), (24, 50)])
    D.line(s, (240, 250, 255), (21, 18), (21, 40))
    D.ellipse(s, (70, 72, 82), (6, 56, 36, 7))
    SK.save("Entities", "Great_Shard", SK.outlined(s))
    # Mary's Whisper: a splinter of it on a cord
    s = SK.surface()
    D.arc(s, (160, 140, 110), (9, 3, 14, 14), 0, math.pi, 1)
    D.polygon(s, body, [(15, 11), (18, 11), (17, 27), (16, 27)])
    D.line(s, light, (16, 13), (16, 24))
    s.set_at((17, 19), (190, 150, 250, 255))
    SK.save("Entities", "Marys_Whisper", SK.outlined(s))
    # the Hand's shrine relit cold: its candles' flames blue and white, the rest as it was
    src = SK.load("Tiles", "Cult_Shrine001")
    s = src.copy()
    w, h = s.get_size()
    for y in range(h):
        for x in range(w):
            r, g, b, al = s.get_at((x, y))
            if al and r > 240 and g > 150 and b < 200:                     # (the candles' flames)
                s.set_at((x, y), (light if g > 220 else body) + (al,))
    SK.save("Tiles", "Cult_Shrine_Cold001", s)
    SK.minimap_colour("Cult_Shrine_Cold001", (60, 64, 80))
    # ... and as a thing over the old one, for those who've seen it relit (Cold_Shrine: two frames, the flames up and
    #  down, as a flame tile flickers)
    flames = [(x, y) for y in range(h) for x in range(w) if s.get_at((x, y))[:3] in (light, body)]
    SK.save("Entities", "Cold_Shrine", s)
    SK.save("Entities", "Cold_Shrine1", s)
    f2 = s.copy()
    for x, y in flames:
        f2.set_at((x, y), (body if f2.get_at((x, y))[:3] == light else light) + (255,))
        if y > 0 and (x, y - 1) not in flames:
            f2.set_at((x, y - 1), (160, 220, 255, 255))
    SK.save("Entities", "Cold_Shrine2", f2)
    # the washing line behind the Mending's house: two posts, a line, a grey robe and a cloth pegged out
    s = SK.surface(64, 32)
    for x in (3, 60):
        D.line(s, (110, 80, 48), (x, 6), (x, 30), 2)
    D.line(s, (200, 196, 180), (4, 7), (60, 9))
    D.polygon(s, (140, 142, 150), [(14, 8), (30, 8), (32, 26), (12, 26)])
    D.polygon(s, (120, 122, 130), [(14, 8), (12, 26), (16, 26), (18, 8)])
    D.line(s, body, (24, 9), (24, 12))
    D.rect(s, (226, 220, 200), (40, 9, 12, 12))
    for x in (16, 28, 42, 50):
        D.line(s, (150, 110, 70), (x, 6), (x, 10))
    SK.save("Entities", "Washing_Line", SK.outlined(s))
    s = SK.surface(64, 32)
    for x in (3, 60):
        D.line(s, (110, 80, 48), (x, 6), (x, 30), 2)
    D.line(s, (200, 196, 180), (4, 7), (60, 9))
    D.rect(s, (226, 220, 200), (40, 9, 12, 12))
    SK.save("Entities", "Washing_Line_Bare", SK.outlined(s))
    # the hidden way in: a slab of the field's glass, smoother than the rest, a hairline round it
    s = SK.surface()
    D.rect(s, (150, 160, 190), (5, 7, 22, 18))
    D.rect(s, (176, 188, 216), (7, 9, 18, 14))
    D.line(s, (214, 226, 246), (9, 11), (20, 11))
    D.rect(s, (96, 104, 130), (5, 7, 22, 18), 1)
    SK.save("Entities", "Glass_Slab", s)
    # the stair down under Wardhaven's chapel: a stone hatch lifted, steps, blue light coming up
    s = SK.surface()
    D.rect(s, (88, 88, 96), (5, 5, 22, 22))
    for k, y in enumerate((8, 12, 16, 20)):
        D.rect(s, (70 - k * 12, 76 - k * 12, 100 - k * 10), (7, y, 18, 4))
    D.line(s, body, (8, 23), (23, 23))
    SK.save("Entities", "Undercroft_Stair", SK.outlined(s))


# ================================================================== sounds (low and old: nothing above C6)
def voice(f, secs, vowel=(1.0, 0.55, 0.35, 0.12, 0.08), vib=0.006, seed=1):
    """One singer: a held note on a vowel (its first few harmonics), a slow swell, a slight waver."""
    rng = random.Random(seed)
    total = BS.n(secs)
    rate, depth = 4.6 + rng.random(), vib
    out, ph = [], [0.0] * len(vowel)
    for i in range(total):
        t = i / float(BS.RATE)
        k = 1 + depth * math.sin(2 * math.pi * rate * t)
        v = 0.0
        for j, g in enumerate(vowel):
            ph[j] += 2 * math.pi * f * (j + 1) * k / BS.RATE
            v += g * math.sin(ph[j])
        u = i / float(total)
        out.append(v * min(1.0, u / 0.25) * min(1.0, (1 - u) / 0.3))
    return out


def chant():
    """A low choir: three chords, slow, in a stone hall (the sermon, the Font's room)."""
    N = SS.NOTE
    D2, A2, F2, G2, C3 = N["D3"] / 2, N["A3"] / 2, N["F3"] / 2, N["G3"] / 2, N["C4"] / 2
    chords = [(D2, A2, N["D3"]), (F2, C3, N["F3"]), (G2, N["D3"], N["G3"]), (D2, A2, N["D3"])]
    parts, at = [], 0.0
    for k, chord in enumerate(chords):
        for j, f in enumerate(chord):
            parts.append((BS.delay(voice(f, 1.5, seed=k * 3 + j), at), 0.32 if j else 0.4))
        at += 1.15
    parts.append((SS.breath(5, at + 0.4, 0.04, 0.5), 0.12))
    return SS.room(BS.mix(*parts), 0.45, 0.8)


def whisper():
    """Breath shaped into a few syllables, close by: a Shard, or Mary's Whisper, speaking."""
    total = BS.n(1.6)
    air = BS.noise(41, total, 0.55, high=0.35)
    rng = random.Random(42)
    sylls = [(0.05 + 0.27 * k + rng.random() * 0.05, 0.16 + rng.random() * 0.1) for k in range(5)]
    out = []
    for i, v in enumerate(air):
        t = i / float(BS.RATE)
        a = sum(math.sin(math.pi * min(1.0, max(0.0, (t - s) / d))) ** 2 for s, d in sylls if s <= t <= s + d)
        out.append(v * a * 2.4)
    tone = BS.shaped(BS.tone(SS.NOTE["D3"], total, glide=-0.03), 0.4, 1.2)
    return SS.room(BS.mix((out, 0.9), (tone, 0.08)), 0.3, 0.5)


def sounds():
    SK.wav("Mending_Chant", chant(), 0.8)
    SK.wav("Mending_Whisper", whisper(), 0.7)


# ================================================================== what they are (Entities.ini, Tiles.ini)
def fighter(name, level, hp, st, de, speed, more=()):
    shown = PEOPLE[name][0]
    words = {
        "Mending_Acolyte": "A grey robe, a kind face, and glass growing out of the shoulders like frost. He looks "
                           "glad to see you.",
        "Mending_Cantor": "One of the Mending's singers. The air round her hums a little, and is colder than it "
                          "should be.",
        "Glassbound": "More glass than cloth now, and slow with it. Whatever it hears, it's listened to for a long "
                      "time.",
        "Eldest_of_the_Mending": "An old man, mostly glass, who smiles as if he's known you all your life.",
    }[name]
    lines = ["Type=NPC", "Attitude=Bad", "Display.Name=%s" % shown, "Use.Words=Attack,Examine", "Examine.Info=%s" % words,
             "Hitpoints=%d" % hp, "Attack.Speed=%s" % speed, "Strength=%d" % st, "Defence=%d" % de,
             "Aggro.Range=210", "Movement.Speed=1.8", "Aggressive=1", "Respawn=300", "Roam.Radius=2",
             "Chase.Radius=8", "Walk.Speed=0.4", "Pause=3-8", "Level=%d" % level, "Sight.Cone=160", "Hearing=1",
             "Kill.Sound=Humanoid"]
    keys = dict(l.split("=", 1) for l in lines)
    keys.update(l.split("=", 1) for l in more)           # (its own numbers over the common ones)
    SK.set_section(SK.ENTS, name, ["%s=%s" % kv for kv in keys.items()], after="Penitent")


def data():
    SK.set_section(SK.ENTS, "Mending_Sister", [
        "Type=NPC", "Attitude=Good", "Display.Name=Sister of the Mending", "Use.Words=Talk to,Examine",
        "Examine.Info=A woman in a plain grey robe, a sliver of glass at her collar. She has the kindest voice "
        "you've heard in a long while.",
        "Roam.Radius=2", "Chase.Radius=0", "Walk.Speed=0.4", "Pause=4-10", "Respawn=300"], after="Penitent")
    fighter("Mending_Acolyte", 14, 116, 10, 10, 1.6, [
        "Friend.If.Wearing=Mending_Robe", "Weapon.Range=0", "Drops=Gold_Coin(s),28-56,100 Mending_Robe,1-1,10"])
    fighter("Mending_Cantor", 15, 110, 11, 9, 2, [
        "Friend.If.Wearing=Mending_Robe", "Weapon.Range=180", "Missile=Ice_Bolt_Missile",
        "Missile.Impact=Ice_Burst", "Missile.Sound=SpellIce", "On.Hit=Daze 20",
        "Drops=Gold_Coin(s),30-60,100 Sapphire,1-1,10"])
    fighter("Glassbound", 17, 170, 14, 15, 2.2, [
        "Friend.If.Wearing=Mending_Robe", "Weapon.Range=0", "Movement.Speed=1.3",
        "Drops=Gold_Coin(s),34-68,100 Shard_Remnant,2-4,100"])
    fighter("Eldest_of_the_Mending", 20, 320, 15, 16, 1.6, [
        "Boss=1", "Absorbs.Remnants=1", "Weapon.Range=170", "Missile=Ice_Bolt_Missile",
        "Missile.Impact=Ice_Burst", "Missile.Sound=SpellIce", "Respawn=900", "Chase.Radius=6",
        "Drops=Gold_Coin(s),80-140,100 Sapphire,1-2,60"])
    SK.set_section(SK.ENTS, "Mending_Robe", [
        "Type=MapItem", "Display.Name=Robe of the Mending",
        "Examine.Info=A grey robe of the Mending, rough wool, a sliver of glass sewn at the collar. In it, they'd "
        "take you for one of their own.",
        "Stackable=1", "Value=20", "Slot=Body", "Attack=0", "Defence=1", "Durability=80"], after="Penitent")
    SK.set_section(SK.ENTS, "Marys_Whisper", [
        "Type=MapItem", "Display.Name=Mary's Whisper",
        "Examine.Info=A splinter of the great Shard, no longer than a finger, on a cord. Hold it and it speaks in "
        "your mother's voice.",
        "Use.Words=Listen,Examine", "Value=0", "Keep.On.Death=1"], after="Penitent")
    SK.set_section(SK.ENTS, "Shard_Font", [
        "Type=StaticObject", "Use.Words=Pour Shards,Examine",
        "Examine.Info=A stone basin of still water with a cold blue light in it. The water doesn't move when you "
        "breathe on it.",
        "Light=48", "Glow=30"], after="Penitent")
    SK.set_section(SK.ENTS, "Great_Shard", [
        "Type=StaticObject", "Use.Words=Listen,Examine",
        "Examine.Info=A Shard as tall as a man and a half, cold to stand near. Something in it is listening back.",
        "Light=96", "Glow=48"], after="Penitent")
    SK.set_section(SK.ENTS, "Cold_Shrine", [
        "Type=StaticObject", "Use.Words=Examine", "Solid=0", "Anim.Frames=2", "Anim.Speed=260",
        "Examine.Info=The Hand's altar, its candles lit again. The flames are blue, and give no warmth at all.",
        "Light=36", "Glow=30"], after="Penitent")
    SK.set_section(SK.ENTS, "Washing_Line", [
        "Type=StaticObject", "Use.Words=Take Robe,Examine", "Solid=0",
        "Examine.Info=A washing line behind the house: a cloth, and a grey robe of the Mending pegged out to dry."],
        after="Penitent")
    SK.set_section(SK.ENTS, "Washing_Line_Bare", [
        "Type=StaticObject", "Use.Words=Examine", "Solid=0",
        "Examine.Info=A washing line with a cloth on it, and an empty peg where a robe was."], after="Penitent")
    SK.set_section(SK.ENTS, "Glass_Slab", [
        "Type=StaticObject", "Use.Words=Climb Down,Examine", "Solid=0",
        "Examine.Info=A slab of the field's glass, smoother than the rest, with a hairline crack all the way round it. "
        "Put your ear to it and something under it is singing."], after="Penitent")
    SK.set_section(SK.ENTS, "Undercroft_Stair", [
        "Type=StaticObject", "Use.Words=Climb Down,Examine", "Solid=0", "Light=30", "Glow=24",
        "Examine.Info=A flagstone lifted out of the chapel floor, and steps going down. Cold blue light comes up them."],
        after="Penitent")
    SK.copy_sprite("Entities", "Shard_Cluster", "Mending_House_Shard")
    SK.set_section(SK.ENTS, "Mending_House_Shard", [
        "Type=StaticObject", "Use.Words=Listen,Examine", "Light=40", "Glow=30",
        "Examine.Info=A Shard the size of a loaf, on a cloth on the table. It's warm, and there's a hum in it, "
        "like someone about to speak."], after="Penitent")
    SK.copy_sprite("Entities", "Cael_Confession", "Caels_Lines")
    SK.set_section(SK.ENTS, "Caels_Lines", [
        "Type=MapItem", "Display.Name=Cael's Lines", "Use.Words=Read,Examine", "Stackable=1", "Droppable=0",
        "Value=0", "Examine.Info=A few lines in Cael's hand, for Annis of Ashford."], after="Penitent")
    SK.copy_sprite("Entities", "Mending_Sister", "Mending_Wayfarer")     # (one of the Mending, met on the road)
    SK.copy_walk("Mending_Sister", "Mending_Wayfarer")
    SK.set_section(SK.ENTS, "Mending_Wayfarer", [
        "Type=NPC", "Attitude=Good", "Display.Name=One of the Mending", "Use.Words=Talk to,Examine",
        "Examine.Info=A traveller in a plain grey robe, a sliver of glass at the collar, smiling at you as if you'd "
        "met before.",
        "Roam.Radius=1", "Chase.Radius=0", "Walk.Speed=0.4", "Pause=4-10", "Respawn=300",
        "Schedule=Always"], after="Penitent")
    SK.copy_tile("Cult_Shrine_Cold001", "Cult_Shrine001",
                 Examine_Info="An altar of the Ashen Hand, lit again: its candles burn blue, and give no warmth.",
                 Glow_Colour="140 190 255", Light="36")


def main():
    people()
    things()
    sounds()
    data()
    print("The Mending's art: done (now build_worn.py for the robe)")


if __name__ == "__main__":
    main()
