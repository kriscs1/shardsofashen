"""The main quest's middle, spread over the world (chapters 12-13 and 18-21), and points of interest in the zones.

The main quest used to go from Bert's treasures (level 6-8) straight to the dragon: nothing in it took you to the
harder zones. Now it leads you round them, a level band at a time, a piece of gear at each step:

 12 Orrin's Chart (OrrinQuest, 10+): Captain Rook won't sail the moving reefs without Orrin's chart. Orrin's ghost is
    in the Sundered Tower (the Shattered Reach); his Shadow has the chart, on the stones below. Mithril helm.
 13 The Frozen Lodestar (LodestarQuest, 12+): the chart steers by the Lodestar, lost in the Rime. Nils at Frostwatch
    Lodge knows where the Drowned Shrine went under; the Rime Warden guards its altar. Mithril shield.
 14-17 A Ship for Dragon Island, The Island of Dragons, The Sword of Valour, The Shardgate (as they were).
 18 The Sleeping Sword (WakeQuest, 14+): with the anchor gone the barrier only thins: the dragon beyond it is plated
    with Shards (the Ashen Hand has fed it through the wall) and laughs at a sword that's asleep. Bert: it was made in
    three fires, and wants waking in them.
 19 The Ashen Foundry (FoundryQuest, 15+): Warden Oska at Ashfall Outpost; the Forgemother; the bellows (hot, not too
    hot: FoundryHeat 3, past it the fire chokes); the hearth. Mithril platebody.
 20 The Sun-Forge (SunforgeQuest, 17+): Nomad Tarek; the Sun Keeper; the three mirrors turned by his grandmother's
    song (Mirror.Dawn east, Mirror.Noon south, Mirror.Dusk west); the forge. Dragonscale helm.
 21 The Deep Anvil (AnvilQuest, 19+): Delver Maud; the Stone King; the four rune stones struck in the work-song's order
    (Root, Rock, Hammer, Crown: AnvilRunes); the anvil wakes the sword (Replace.Item: the Woken Sword of Valour).
    Dragonscale platebody.
 22-24 The Dragon of Galaith (20+: the barrier breaks only for the woken sword), The Royal Guard, The True Heir.

Each fire's keeper names the next: found, not laid out. Side quests and things to find on the way: The Brother in the
Ash (Cael, a penitent of the Hand at the Cinder Chapel, and his sister Oska), The Wandering Echo (Shardglass Field's
riddles), Old Skadi's Tall Tales (Frostwatch Lodge); Lucky Lem's rat races (Rustwater Halt), Vesna's fortunes
(Ashfall Outpost), the Mirage Trader (the Drakes' Bones), the Echo Pool (the Fungus Grotto), Fenn and his mushrooms
(the Delvers' Camp); bosses of the zones: the Scavenger King (Bonebreak Mesa), Old Whitefang (Yeti Hollow), the Slag
Wyrm (the Lava Fields), the Sand-Mother (the Drakes' Bones).

The scripts it takes over (Talk to Captain_Rook, the barrier) are its own after: story_kit.TAKES_OVER keeps an earlier
builder run again off them. The four givers' own kill quests (build_zones.py) carry on as "Odd Jobs for <who>",
reached from their talk. Run it after build_shardgate.py (which calls renumber() when it's run again).

Safe to run again.

  python -I "dev\\migrate\\build_middle_quests.py"
"""
import io
import math
import os
import random
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import story_kit as K  # noqa: E402
from story_kit import say, ini  # noqa: E402
from build_isle import Map, obj_line, XT, YT  # noqa: E402

import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

MAKER = "build_middle_quests.py"
V1, V2 = "Variable.1$", "Variable.2$"
ROOK, ORRIN, BERT = "Sea_Captain", "Orrin_Ghost", "Bert"
MAN, WOMAN, OLD = "Man", "Woman", "Old_Woman"
ALIVE = "Walking,Standing,Fighting,Following"
SWORD = "$Item.Sword_of_Valour>=1"                  # ($Item counts what's in your hand too)
FAR = [("@far",), ("Display.Message", "DarkRed", "You are too far away!", "Denied"), ("End",)]


def started(title):
    return ("Display.Message", "Yellow", "Quest started: %s." % title, "Quest")


def complete(title):
    return ("Display.Message", "Yellow", "Quest complete: %s!" % title, "Quest")


# ================================================================== pictures
def _png(img):
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


def save_pil(kind, name, img):
    path = os.path.join(K.SPR, kind, name + ".png")
    data = _png(img)
    if os.path.exists(path) and open(path, "rb").read() == data:
        return
    open(path, "wb").write(data)


def tint(im, col, alpha=1.0):
    """As build_zones.tint: another colour, as light and dark as it was, its dark outline kept (alpha: a ghost's)."""
    a = np.array(im.convert("RGBA"), dtype=np.float32)
    lum = a[..., 0] * 0.3 + a[..., 1] * 0.59 + a[..., 2] * 0.11
    k = np.clip(lum / 150.0, 0, 1.45)[..., None]
    out = np.array(col, dtype=np.float32)[None, None, :] * k
    a[..., :3] = np.clip(np.where((lum < 42)[..., None], a[..., :3], out), 0, 255)
    a[..., 3] *= alpha
    return Image.fromarray(a.astype(np.uint8), "RGBA")


def bigger(im, scale):
    """scale times as big, pixel for pixel (nearest), on the same ground line: the client draws it at its own size."""
    if scale == 1:
        return im
    w, h = im.size
    return im.resize((round(w * scale), round(h * scale)), Image.NEAREST)


def kind_from(name, base, col, scale=1.0, alpha=1.0):
    """name's pictures (its walking frames and its still one) from base's, tinted and scaled."""
    walk = os.path.join(K.SPR, "Walk")
    for d in "1248":
        for f in "abc":
            src = os.path.join(walk, "%s%s%s.png" % (base, d, f))
            if os.path.exists(src):
                save_pil("Walk", "%s%s%s" % (name, d, f), bigger(tint(Image.open(src), col, alpha), scale))
    src = os.path.join(K.SPR, "Entities", base + ".png")
    save_pil("Entities", name, bigger(tint(Image.open(src), col, alpha), scale))


def draw_objects():
    p = K.pg()
    S, O, D = K.surface, K.outlined, p.draw

    s = S()                                                     # the Lodestar's altar: stone, a bowl of ice
    D.rect(s, (112, 116, 124), (6, 14, 20, 16))
    D.rect(s, (140, 146, 154), (4, 11, 24, 5))
    D.rect(s, (92, 96, 104), (6, 26, 20, 3))
    D.ellipse(s, (196, 228, 246), (8, 6, 16, 8))
    D.polygon(s, (120, 190, 250), [(16, 2), (18, 8), (24, 9), (18, 11), (16, 16), (14, 11), (8, 9), (14, 8)])
    D.line(s, (240, 250, 255), (16, 4), (16, 13))
    K.save("Entities", "Lodestar_Altar", O(s))

    s = S()                                                     # the Foundry's hearth: a brick arch, coals in it
    D.rect(s, (110, 52, 36), (2, 4, 28, 26))
    for y in range(6, 30, 4):
        for x in range(2 + (y // 4 % 2) * 3, 30, 6):
            D.line(s, (80, 36, 26), (x, y), (x + 4, y))
    D.rect(s, (40, 22, 18), (8, 12, 16, 16))
    D.ellipse(s, (40, 22, 18), (8, 7, 16, 12))
    D.rect(s, (220, 96, 30), (9, 22, 14, 6))
    for x, y in ((11, 21), (15, 20), (19, 22), (13, 24), (17, 23)):
        D.circle(s, (255, 196, 70), (x, y), 2)
    K.save("Entities", "Foundry_Hearth", O(s))

    s = S()                                                     # the bellows: leather between two boards
    D.polygon(s, (120, 80, 44), [(4, 10), (24, 14), (24, 20), (4, 24)])
    D.polygon(s, (92, 60, 40), [(6, 12), (22, 15), (22, 19), (6, 22)])
    D.line(s, (150, 104, 60), (4, 10), (24, 14), 2)
    D.line(s, (150, 104, 60), (4, 24), (24, 20), 2)
    D.rect(s, (110, 110, 116), (24, 15, 6, 4))
    D.rect(s, (120, 80, 44), (1, 8, 4, 4))
    D.rect(s, (120, 80, 44), (1, 22, 4, 4))
    D.rect(s, (80, 56, 32), (8, 26, 16, 4))
    K.save("Entities", "Foundry_Bellows", O(s))

    s = S()                                                     # the Sun-Forge: a gold disc on sandstone
    D.rect(s, (196, 160, 104), (6, 20, 20, 10))
    D.rect(s, (220, 186, 128), (4, 18, 24, 3))
    D.circle(s, (232, 184, 60), (16, 11), 9)
    D.circle(s, (252, 220, 110), (16, 11), 6)
    for a in range(0, 360, 45):
        r = math.radians(a)
        D.line(s, (252, 230, 140), (16 + 7 * math.cos(r), 11 + 7 * math.sin(r)), (16 + 10 * math.cos(r), 11 + 10 * math.sin(r)))
    K.save("Entities", "Sun_Forge", O(s))

    s = S()                                                     # a sun mirror: bronze on a post
    D.rect(s, (110, 78, 44), (15, 16, 3, 12))
    D.rect(s, (90, 64, 40), (10, 27, 13, 3))
    D.ellipse(s, (176, 130, 60), (7, 2, 19, 17))
    D.ellipse(s, (222, 196, 130), (10, 5, 13, 11))
    D.line(s, (250, 240, 200), (13, 8), (16, 6))
    K.save("Entities", "Sun_Mirror", O(s))

    for rune, marks in (("Root", [((16, 6), (16, 20)), ((16, 20), (11, 25)), ((16, 20), (21, 25)), ((16, 14), (12, 18))]),
                        ("Rock", [((10, 22), (16, 8)), ((16, 8), (22, 22)), ((22, 22), (10, 22))]),
                        ("Hammer", [((10, 9), (22, 9)), ((10, 13), (22, 13)), ((16, 13), (16, 25))]),
                        ("Crown", [((10, 20), (10, 10)), ((10, 10), (13, 16)), ((13, 16), (16, 8)), ((16, 8), (19, 16)),
                                   ((19, 16), (22, 10)), ((22, 10), (22, 20)), ((22, 20), (10, 20))])):
        s = S()                                                 # the four rune stones, each its own rune
        D.polygon(s, (118, 116, 122), [(8, 30), (6, 8), (10, 2), (22, 2), (26, 8), (24, 30)])
        D.polygon(s, (96, 94, 102), [(18, 30), (24, 30), (26, 8), (22, 2)])
        for a, b in marks:
            D.line(s, (130, 190, 240), a, b, 2)
        K.save("Entities", "Rune_Stone_" + rune, O(s))

    s = S()                                                     # the Deep Anvil: black iron on a dais, blue runes
    D.rect(s, (90, 88, 96), (2, 24, 28, 6))
    D.rect(s, (52, 52, 60), (10, 16, 12, 8))
    D.polygon(s, (60, 60, 70), [(2, 8), (30, 8), (26, 16), (6, 16)])
    D.polygon(s, (60, 60, 70), [(2, 8), (0, 10), (6, 12)])
    for x in (8, 14, 20, 25):
        D.line(s, (100, 170, 240), (x, 10), (x + 1, 13))
    K.save("Entities", "Deep_Anvil", O(s))

    s = S()                                                     # the Echo Pool: violet water, crystals round it
    D.ellipse(s, (54, 40, 80), (2, 12, 28, 16))
    D.ellipse(s, (140, 104, 210), (5, 14, 22, 11))
    D.ellipse(s, (196, 170, 250), (10, 17, 10, 4))
    for x, h in ((3, 10), (26, 12), (22, 7)):
        D.polygon(s, (190, 160, 250), [(x, 18), (x + 2, 18 - h), (x + 4, 18)])
    K.save("Entities", "Echo_Pool", O(s))

    s = S()                                                     # Lucky Lem's rat track: three lanes, three rats
    D.rect(s, (134, 96, 56), (1, 10, 30, 18))
    for y in (15, 21):
        D.line(s, (96, 66, 38), (1, y), (30, y))
    D.rect(s, (230, 230, 230), (26, 10, 2, 18))
    for x, y, c in ((8, 12, (120, 110, 100)), (14, 18, (90, 80, 76)), (5, 24, (160, 140, 120))):
        D.ellipse(s, c, (x, y, 6, 3))
        D.line(s, (210, 150, 150), (x, y + 1), (x - 3, y + 2))
    K.save("Entities", "Rat_Race_Track", O(s))

    # ----- items
    s = S()                                                     # Orrin's chart, rolled, a red ribbon
    D.rect(s, (226, 208, 160), (5, 11, 22, 10))
    D.ellipse(s, (200, 180, 130), (2, 11, 6, 10))
    D.ellipse(s, (240, 226, 186), (24, 11, 6, 10))
    D.rect(s, (170, 40, 40), (14, 10, 3, 12))
    D.line(s, (110, 120, 160), (7, 14), (22, 17))
    K.save("Entities", "Valour_Chart", O(s))

    s = S()                                                     # the Lodestar, in its ice
    D.polygon(s, (200, 232, 250), [(16, 2), (20, 11), (30, 13), (21, 19), (24, 30), (16, 23), (8, 30), (11, 19), (2, 13), (12, 11)])
    D.polygon(s, (110, 180, 250), [(16, 7), (18, 13), (24, 14), (19, 18), (21, 25), (16, 21), (11, 25), (13, 18), (8, 14), (14, 13)])
    D.circle(s, (250, 252, 255), (16, 15), 2)
    K.save("Entities", "Frozen_Lodestar", O(s))

    s = S()                                                     # a crown of spoons and bottle tops
    D.polygon(s, (180, 170, 150), [(4, 26), (4, 12), (9, 18), (12, 8), (16, 16), (20, 8), (23, 18), (28, 12), (28, 26)])
    D.rect(s, (150, 140, 120), (4, 22, 24, 4))
    D.circle(s, (200, 30, 40), (16, 23), 2)
    for x in (8, 24):
        D.circle(s, (120, 150, 100), (x, 23), 1)
    K.save("Entities", "Scavenger_Crown", O(s))

    s = S()                                                     # Old Whitefang's pelt
    D.ellipse(s, (236, 238, 242), (3, 8, 26, 18))
    for x, y in ((3, 8), (25, 8), (3, 22), (25, 22)):
        D.ellipse(s, (226, 228, 234), (x, y, 5, 5))
    D.ellipse(s, (210, 212, 220), (12, 3, 8, 8))
    D.line(s, (180, 184, 196), (9, 16), (23, 16))
    K.save("Entities", "Whitefang_Pelt", O(s))

    src = K.load("Entities", "Last_Will")                       # Cael's confession: a letter like any other
    K.save("Entities", "Cael_Confession", src)

    sword = Image.open(os.path.join(K.SPR, "Entities", "Sword_of_Valour.png")).convert("RGBA")
    a = np.array(sword, dtype=np.float32)                       # the woken sword: its steel lit violet, a glow round it
    lum = a[..., 0] * 0.3 + a[..., 1] * 0.59 + a[..., 2] * 0.11
    steel = (lum > 120) & (a[..., 3] > 0) & (np.abs(a[..., 0] - a[..., 2]) < 40)
    a[steel, 0] = np.clip(a[steel, 0] * 0.85 + 30, 0, 255)
    a[steel, 1] = np.clip(a[steel, 1] * 0.7, 0, 255)
    a[steel, 2] = np.clip(a[steel, 2] * 0.9 + 40, 0, 255)
    solid = a[..., 3] > 0
    near = np.zeros_like(solid)
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1), (1, -1), (-1, 1)):
        near |= np.roll(np.roll(solid, dy, 0), dx, 1)
    glow = near & ~solid
    a[glow] = (190, 140, 255, 110)
    save_pil("Entities", "Woken_Sword_of_Valour", Image.fromarray(a.astype(np.uint8), "RGBA"))


# name: base, tint, scale, level, melee/magic, words, kill sound, drops, on hit
BOSSES = {
    "Orrins_Shadow": ("Dark_Mage", (72, 66, 112), 1.5, 13, "magic", "Orrin's face, Orrin's coat, and nothing at all "
                      "behind the eyes. It hums the old sailing songs, wrong.", "Undead",
                      "Gold_Coin(s),40-70,100 Sapphire,1-1,30 Storm_Shard,1-1,30", "Daze 30"),
    "Rime_Warden": ("Frost_Troll", (196, 226, 246), 1.5, 14, "melee", "The shrine's guardian, frozen into the job. "
                    "Icicles hang off its brows like a fringe.", "Troll",
                    "Gold_Coin(s),50-80,100 Mithril_Ore,1-2,40 Sapphire,1-1,30", "Chill 25"),
    "Forgemother": ("Cave_Troll", (222, 104, 40), 1.5, 17, "melee", "Slag and spite, poured into the shape of a smith. "
                    "Its hammer-hands are still hot.", "Troll",
                    "Gold_Coin(s),60-100,100 Mithril_Ore,1-2,50 Ember_Shard,1-1,40 Coal,2-4,100", "Burn 40"),
    "Sun_Keeper": ("Skeleton", (236, 204, 120), 1.5, 19, "melee", "A priest of the Sun-Forge, wrapped in gold leaf and "
                   "a very bad temper, still at his post.", "Undead",
                   "Gold_Coin(s),70-110,100 Ruby,1-1,40 Ward_Shard,1-1,40", "Frailty 15"),
    "Stone_King": ("Cave_Troll", (124, 120, 136), 1.5, 21, "melee", "It sits the dwarves' throne as if it built it. It "
                   "didn't. It ate the ones who did.", "Troll",
                   "Gold_Coin(s),80-130,100 Mithril_Ore,2-3,60 Sapphire,1-2,40 Ruby,1-1,30", "Daze 30"),
    # (the zones' own: no quest of theirs, a trophy each)
    "Scavenger_King": ("Bandit", (176, 132, 72), 1.4, 10, "melee", "Crowned in spoons and bottle tops. The knife's "
                       "real.", "Humanoid", "Gold_Coin(s),40-70,100 Scavenger_Crown,1-1,100", "Bleed 25"),
    "Old_Whitefang": ("Snow_Wolf", (246, 246, 250), 1.4, 15, "melee", "The oldest wolf in the Rime, white to the gums. "
                      "Its scars have scars.", "Beast", "Whitefang_Pelt,1-1,100 Raw_Meat,2-3,100", "Chill 40"),
    "Slag_Wyrm": ("Drake", (156, 52, 24), 1.5, 18, "melee", "A drake that went swimming in the lava and liked it. It "
                  "glows where it's cracked.", "Beast", "Gold_Coin(s),60-100,100 Ember_Shard,1-1,60 Ruby,1-1,30",
                  "Burn 40"),
    "Sand_Mother": ("Scorpion", (224, 186, 104), 1.5, 20, "melee", "Every scorpion in the desert is her child, and "
                    "she's come about it.", "Bug", "Gold_Coin(s),70-120,100 Ruby,1-2,40 Antidote,1-1,100", "Poison 45"),
}

# (a boss whose numbers are its own, not its level's: the Rime Warden is fought in steel, the ones after it with
#  the Sword of Valour, so it's gentler than its level would make it: fought at level 12, about as long as Orrin's
#  Shadow at 10)
TUNED = {"Rime_Warden": {"Hitpoints": "225", "Strength": "10", "Defence": "11", "Attack.Speed": "1.8"}}

# name: base, tint, alpha, level, words, light
PEOPLE = {
    "Orrin_Ghost": ("Wizard", (176, 204, 236), 0.72, 13, "A navigator's ghost in a salt-stained coat, still looking "
                    "out to sea.", 90),
    "Wandering_Echo": ("Ghost_Warden", (204, 176, 244), 0.78, 12, "Nobody, standing in the glass. When it moves, the "
                       "glass hums.", 110),
    "Penitent": ("Ashen_Cultist", (128, 124, 120), 1.0, 12, "A cultist of the Hand in a robe gone grey, praying where "
                 "the others can't see him.", 0),
}


def pictures():
    for name, (base, col, scale, *_rest) in BOSSES.items():
        kind_from(name, base, col, scale)
    for name, (base, col, alpha, *_rest) in PEOPLE.items():
        kind_from(name, base, col, 1.0, alpha)
    draw_objects()


# ================================================================== sounds (the old world's: breath, bronze, stone, bells)
def _noise(n, seed, smooth):
    rng = random.Random(seed)
    out, v = [], 0.0
    for _ in range(n):
        v += (rng.uniform(-1, 1) - v) * smooth
        out.append(v)
    return out


def _bell(freq, secs, partials=((1, 1.0), (2.76, 0.5), (5.4, 0.25)), decay=3.0):
    n = int(K.RATE * secs)
    return [sum(a * math.sin(2 * math.pi * freq * m * i / K.RATE) * math.exp(-decay * m * i / n) for m, a in partials)
            * min(1.0, i / 60.0) for i in range(n)]


def _pluck(freq, secs, seed=1):
    """A plucked string (Karplus-Strong): the harp's notes."""
    rng = random.Random(seed)
    period = max(2, int(K.RATE / freq))
    buf = [rng.uniform(-1, 1) for _ in range(period)]
    out = []
    for i in range(int(K.RATE * secs)):
        v = buf[i % period]
        buf[i % period] = 0.996 * 0.5 * (v + buf[(i + 1) % period])
        out.append(v)
    return out


def _mix(*parts):
    n = max(len(s) + at for at, s in parts)
    out = [0.0] * n
    for at, s in parts:
        for i, v in enumerate(s):
            out[at + i] += v
    return out


def sounds():
    r = K.RATE
    n = int(r * 0.9)                                            # Bellows: a long breath in and out, and the boards
    breath = _noise(n, 7, 0.08)
    env = [math.sin(math.pi * i / n) ** 1.5 for i in range(n)]
    creak = [0.25 * math.sin(2 * math.pi * (70 + 30 * i / 2000) * i / r) * math.exp(-i / 900) for i in range(2000)]
    K.wav("Bellows", _mix((0, [b * e for b, e in zip(breath, env)]), (int(r * 0.05), creak), (int(r * 0.75), creak)))

    harp = [_pluck(f, 1.4, k) for k, f in enumerate((220.0, 277.18, 329.63, 440.0, 554.37))]   # Sword_Wake
    K.wav("Sword_Wake", _mix((0, _bell(110, 2.6)), *[(int(r * (0.35 + 0.16 * k)), [0.6 * v for v in h])
                                                      for k, h in enumerate(harp)]))

    n = int(r * 0.45)                                           # Mirror_Turn: bronze grinding round on its pivot
    grind = _noise(n, 11, 0.3)
    K.wav("Mirror_Turn", [g * (0.6 + 0.4 * math.sin(2 * math.pi * 23 * i / r)) * math.sin(math.pi * i / n) +
                          0.2 * math.sin(2 * math.pi * 95 * i / r) * math.sin(math.pi * i / n)
                          for i, g in enumerate(grind)], gain=0.6)

    knock = [v * math.exp(-i / 300) for i, v in enumerate(_noise(1500, 5, 0.5))]   # Rune_Strike: stone, then a hum
    K.wav("Rune_Strike", _mix((0, knock), (0, _bell(146.83, 1.2, ((1, 1.0), (2.0, 0.3), (3.01, 0.15)), 2.2))), gain=0.7)


# ================================================================== the data
def entities():
    for name, (base, col, scale, level, kind, words, ksound, drops, hit) in BOSSES.items():
        lines = ["Type=NPC", "Attitude=Bad", "Use.Words=Attack,Examine", "Examine.Info=%s" % words, "Aggressive=1",
                 "Level=%d" % level, "Hitpoints=%d" % round(15 * level), "Strength=%d" % round(0.8 * level),
                 "Defence=%d" % round(0.85 * level), "Attack.Speed=%s" % ("2" if kind == "magic" else "1.5"),
                 "Respawn=900", "Movement.Speed=1.5", "Aggro.Range=240", "Roam.Radius=3", "Chase.Radius=10",
                 "Walk.Speed=0.5", "Pause=2-7", "Drops=%s" % drops, "On.Hit=%s" % hit, "Sight.Cone=240",
                 "Hearing=1.2", "Kill.Sound=%s" % ksound, "Boss=1", "Fear.Immune=1"]
        lines += ["Weapon.Range=180", "Missile=Dark_Bolt_Missile", "Missile.Impact=Dark_Burst"] if kind == "magic" \
            else ["Weapon.Range=0"]
        tuned = TUNED.get(name, {})
        lines = [k + "=" + tuned[k] if k in tuned else ln for ln in lines for k in [ln.split("=", 1)[0]]]
        K.set_section(K.ENTS, name, lines)
    for name, (base, col, alpha, level, words, light) in PEOPLE.items():
        lines = ["Type=NPC", "Attitude=Good", "Use.Words=Talk to,Examine", "Examine.Info=%s" % words, "Roam.Radius=0",
                 "Chase.Radius=0", "Walk.Speed=0.5", "Pause=4-10", "Respawn=300", "Level=%d" % level]
        K.set_section(K.ENTS, name, lines + (["Light=%d" % light] if light else []))

    def obj(name, verbs, words, *more):
        K.set_section(K.ENTS, name, ["Type=StaticObject", "Use.Words=%s" % verbs, "Solid=1", "Examine.Info=%s" % words]
                      + list(more))

    obj("Lodestar_Altar", "Reach In,Examine", "An altar of grey stone, rimed white. Its bowl is full of ice.", "Light=80")
    obj("Foundry_Hearth", "Temper,Examine", "The Ashen Foundry's great hearth, big enough to walk into.", "Light=140")
    obj("Foundry_Bellows", "Work,Examine", "A smith's bellows the size of a cow, its leather patched and patched again.")
    obj("Sun_Forge", "Temper,Examine", "A great disc of gold-faced bronze on a sandstone altar: the Sun-Forge.", "Light=90")
    obj("Sun_Mirror", "Turn,Examine", "A bronze mirror on a post, green with age. It turns, if you lean on it.")
    for rune in ("Root", "Rock", "Hammer", "Crown"):
        obj("Rune_Stone_" + rune, "Strike,Examine", "A standing stone carved with a dwarf rune: the %s." % rune.lower(),
            "Display.Name=Rune of the %s" % rune)
    obj("Deep_Anvil", "Temper,Examine", "A great anvil of black iron on a dais, runes cut all round it.", "Light=70")
    obj("Echo_Pool", "Listen,Examine", "A pool of violet water among the mushrooms. It hums, and the hum changes.",
        "Light=110")
    obj("Rat_Race_Track", "Bet,Examine", "Three lanes of planking and a chalk line. It smells strongly of rat.")

    def item(name, words, *more):
        K.set_section(K.ENTS, name, ["Type=MapItem", "Examine.Info=%s" % words] + list(more))

    item("Valour_Chart", "Orrin's chart of the waters round Dragon Island: every reef and current, and every mark set "
         "by a star.", "Stackable=1", "Droppable=0", "Value=0")
    item("Frozen_Lodestar", "The Lodestar: a star of ice that never melts. It tugs, gently, north.", "Stackable=1",
         "Droppable=0", "Value=0")
    item("Woken_Sword_of_Valour", "The Sword of Valour, awake: Shard-light runs along its edge, and it hums like a "
         "hive. It pulls, gently, towards Galaith.", "Slot=Weapon", "Attack=20", "Defence=3", "Droppable=0", "Value=0",
         "Durability=900", "Requires=Strength 15", "Base=Sword_of_Valour")
    item("Cael_Confession", "A letter from Cael, of the Cinder Chapel, to his sister Oska.", "Use.Words=Read,Examine",
         "Stackable=1", "Droppable=0", "Value=0")
    item("Scavenger_Crown", "A crown of bent spoons, bottle tops and one real ruby. Mostly spoons.", "Stackable=1",
         "Value=150")
    item("Whitefang_Pelt", "Old Whitefang's pelt, white as new snow and thick as a mattress.", "Stackable=1",
         "Value=200")

    # the dragon, plated in the Hand's Shards: harder, and its death blow the sword's, woken or not (asleep, it could
    #  still finish what's left of an old save's fight). The last fight is the longest: about 45 s and five or six
    #  draughts at level 20 with the woken sword, never one blow from the end (a boss: more for each who fights it)
    K.section(K.ENTS, "Galaith_Dragon", [("Hitpoints", "1300"), ("Strength", "20"), ("Defence", "20"),
                                         ("Slain.By", "Woken_Sword_of_Valour,Sword_of_Valour")])

    K.set_section(K.RACKS, "SHOP-Mirage", ["Type=Shop", "Buy.Rate=1.4", "Sell.Rate=0.7", "Specific=1",
                                           "Item1=Major_Healing_Draught,3", "Item2=Antidote,5", "Item3=Fever_Tonic,2",
                                           "Item4=Warming_Draught,3", "Item5=Ruby,2", "Item6=Sapphire,2"])


# ----- the quests
def renumber():
    """The main quest's chapters, the new ones among them (build_shardgate.py run again calls it)."""
    q = K.QUESTS
    for name, ch in (("A Ship for Dragon Island", 14), ("The Island of Dragons", 15), ("The Sword of Valour", 16),
                     ("The Shardgate", 17), ("The Dragon of Galaith", 22), ("The Royal Guard", 23),
                     ("The True Heir", 24)):
        K.section(q, name, [("Chapter", str(ch))])
    K.section(q, "A Ship for Dragon Island", [
        ("Requires.Quests", "The Frozen Lodestar"), ("Requires.Level", "13"),
        ("Stage0", "Captain Rook has Orrin's chart and the Lodestar to steer by. Now his hull wants mending.")])
    K.section(q, "The Dragon of Galaith", [("Requires.Quests", "The Deep Anvil"), ("Requires.Level", "20")])


def quests():
    q = K.QUESTS
    K.quest("Orrin's Chart", ROOK, "OrrinQuest", {
        0: "Find Captain Rook, the only captain mad enough to sail to Dragon Island, on the shore below King Rupert's "
           "Keep.",
        1: "Captain Rook won't sail the moving reefs round Dragon Island without the chart of Orrin, the navigator "
           "who climbed the Sundered Tower and never came down.",
        2: "Orrin's ghost haunts the Sundered Tower. His Shadow walks off with his face and his chart: break it.",
        3: "Orrin's Shadow is broken. Go back up to Orrin.",
        4: "Take Orrin's chart to Captain Rook.",
    }, 5, markers={0: "Rooks_Pier", 1: "Sundered_Tower", 2: "Orrins_Shadow_Boss", 3: "Orrin", 4: "Rooks_Pier"},
        chapter=12, requires="Bert's Three Treasures", level=10, after="The Ember Ring")
    K.section(q, "Orrin's Chart", [("Reward.Items", "Mithril_Helm 1"), ("Reward.Shards", "40"),
                                    ("Reward.XP", "Channeling 3 Defence 3")])
    K.quest("The Frozen Lodestar", ROOK, "LodestarQuest", {
        0: "Orrin steered by the Lodestar, and Captain Rook won't sail without it.",
        1: "The Lodestar's shrine went under the ice somewhere in the Rime. Ask Nils, the surveyor at Frostwatch "
           "Lodge.",
        2: "Nils says the Drowned Shrine lies frozen north-east of the lodge, past the ridge, with something big and "
           "white on guard. Bring back the Lodestar.",
        3: "Take the Lodestar to Captain Rook.",
    }, 4, markers={0: "Rooks_Pier", 1: "Surveyor_Nils", 2: "Drowned_Shrine", 3: "Rooks_Pier"}, chapter=13,
        requires="Orrin's Chart", level=12, after="Orrin's Chart")
    K.section(q, "The Frozen Lodestar", [("Reward.Items", "Mithril_Shield 1"), ("Reward.Shards", "40"),
                                          ("Reward.XP", "Defence 4 Strength 2")])
    K.quest("The Sleeping Sword", BERT, "WakeQuest", {
        0: "The barrier at the pass only thins now its anchor's gone.",
        1: "Beyond the thinning barrier the dragon wears a hide of Shards, and laughed at the Sword of Valour. Ask Bert "
           "why.",
    }, 2, markers={0: "Galaith_Barrier", 1: "Court_Wizard"}, chapter=18, requires="The Shardgate", level=14,
        after="The Shardgate")
    K.section(q, "The Sleeping Sword", [("Reward.Shards", "30"), ("Reward.XP", "Channeling 3")])
    K.quest("The Ashen Foundry", "Woman", "FoundryQuest", {
        0: "The Sword of Valour was made in three fires, and sleeps. Bert says the first was the Ashen Foundry, and "
           "the warden at Ashfall Outpost keeps watch over it.",
        1: "Warden Oska says the Forgemother holds the Foundry. Break it.",
        2: "Light the Foundry's great hearth with its bellows, hot but not too hot, and temper the Sword of Valour in "
           "it.",
        3: "The sword stirred in the Foundry's fire. Tell Warden Oska.",
    }, 4, markers={0: "Warden_Oska", 1: "Forgemother_Boss", 2: "Ashen_Foundry", 3: "Warden_Oska"}, chapter=19,
        requires="The Sleeping Sword", level=15, after="The Sleeping Sword")
    K.section(q, "The Ashen Foundry", [("Reward.Items", "Mithril_Platebody 1"), ("Reward.Shards", "60"),
                                        ("Reward.XP", "Crafting 5 Strength 4")])
    K.quest("The Sun-Forge", "Man", "SunforgeQuest", {
        0: "Warden Oska says the sword's second fire was the Sun-Forge, under the sands; the nomads at their well "
           "still sing about it.",
        1: "Nomad Tarek says the Sun Keeper still holds the temple south of the well. Break it.",
        2: "The Sun-Forge burns only with the sun on it, brought down by its three mirrors. Tarek's grandmother had a "
           "song for them.",
        3: "The Sun-Forge blazes. Temper the Sword of Valour in it.",
        4: "The sword drank the sun. Tell Tarek.",
    }, 5, markers={0: "Nomad_Tarek", 1: "Sun_Keeper_Boss", 2: "Sunken_Temple", 3: "Sunken_Temple", 4: "Nomad_Tarek"},
        chapter=20, requires="The Ashen Foundry", level=17, after="The Ashen Foundry")
    K.section(q, "The Sun-Forge", [("Reward.Items", "Dragonscale_Helm 1"), ("Reward.Shards", "70"),
                                    ("Reward.XP", "Defence 5 Channeling 3")])
    K.quest("The Deep Anvil", "Woman", "AnvilQuest", {
        0: "Tarek says the sword's last fire was the dwarves' Deep Anvil, under the mountains, and the delvers' camp "
           "is digging after it. Ask for Maud.",
        1: "Maud says the Stone King sits the old dwarf hall's throne. Break it.",
        2: "The dwarves locked the Deep Anvil with four rune stones. Maud's people sing a work-song older than any of "
           "them.",
        3: "The Deep Anvil is awake. Wake the Sword of Valour on it.",
        4: "The Sword of Valour is awake. Tell Maud.",
    }, 5, markers={0: "Delver_Maud", 1: "Stone_King_Boss", 2: "Dwarf_Hall", 3: "Dwarf_Hall", 4: "Delver_Maud"}, chapter=21,
        requires="The Sun-Forge", level=19, after="The Sun-Forge")
    K.section(q, "The Deep Anvil", [("Reward.Items", "Dragonscale_Platebody 1"), ("Reward.Shards", "90"),
                                     ("Reward.XP", "Strength 6 Defence 6")])

    # ----- the side quests on the way
    K.quest("The Brother in the Ash", "Penitent", "CaelQuest", {
        0: "A cultist of the Hand prays apart from the others at the Cinder Chapel.",
        1: "Cael, of the Cinder Chapel, asks you to take his letter to his sister, Warden Oska of Ashfall Outpost.",
    }, 2, markers={0: "Cael", 1: "Warden_Oska"}, kind="Side", requires="The Shardgate", level=14)
    K.section(q, "The Brother in the Ash", [
        ("Reward.Items", "Ward_Shard 1"), ("Reward.Shards", "30"), ("Reward.XP", "Stealth 3"),
        ("Rumour", "There's one of those Hand cultists at the Cinder Chapel who prays with his back to the others. "
                   "Sorry-looking fellow.")])
    K.quest("The Wandering Echo", "Wandering_Echo", "EchoQuest", {
        0: "Something out on Shardglass Field asks riddles, they say, in your own voice.",
        1: "The Wandering Echo of Shardglass Field has three questions nobody has stayed to answer.",
    }, 2, markers={0: "Shardglass_Field", 1: "Shardglass_Echo"}, kind="Side", requires="Passage to the Mainland",
        level=10)
    K.section(q, "The Wandering Echo", [
        ("Reward.Shards", "45"), ("Reward.XP", "Shardcraft 4"),
        ("Rumour", "Out on Shardglass Field there's a voice that asks riddles. Nobody's ever seen who's asking.")])
    K.quest("Old Skadi's Tall Tales", "Old_Woman", "SkadiQuest", {
        0: "Old Skadi at Frostwatch Lodge has never told a lie, she says.",
        1: "Old Skadi tells three tales. Say which are true and which are lies.",
    }, 2, markers={0: "Old_Skadi", 1: "Old_Skadi"}, kind="Side", requires="Passage to the Mainland", level=12)
    K.section(q, "Old Skadi's Tall Tales", [
        ("Reward.Items", "Wool_Mittens 1"), ("Reward.Shards", "15"),
        ("Rumour", "Old Skadi at Frostwatch Lodge says she's never told a lie in her life. She'll bet you a pair of "
                   "mittens on it.")])
    renumber()


# ================================================================== where they stand
_tiles = {}


def walk_ok(name):
    """A tile you can stand all over (its walk mask all open, or none)."""
    if not name:
        return True
    if name not in _tiles:
        w = ini.read(name, "Walkable.Data", "", K.TILES)
        _tiles[name] = (not w or set(w) == {"1"}) and not re.search(r"Water|Bog|Lava|Ice|Wall|Mountain|Cliff", name)
    return _tiles[name]


def free(m, x, y, roofed=False):
    if not (2 <= x <= XT - 1 and 2 <= y <= YT - 1):
        return False
    t, over = m.parts(x, y)
    if over.get("Roof") and not roofed:
        return False
    return walk_ok(t) and walk_ok(over.get("Decor", "")) and not m.ent_near(x, y, 30)


def near_free(m, x, y, roofed=False):
    for r in range(0, 9):
        ring = [(x + dx, y + dy) for dy in range(-r, r + 1) for dx in range(-r, r + 1) if max(abs(dx), abs(dy)) == r]
        for gx, gy in ring:
            if free(m, gx, gy, roofed):
                return gx, gy
    raise SystemExit("No room near %d,%d on %s" % (x, y, m.name))


def place_of(pid):
    """(map name, x, y) of a place Id, on the world (Z=0)."""
    for f in sorted(os.listdir(os.path.join(K.ROOT, "maps"))):
        if not f.endswith(",0.txt"):
            continue
        for ln in ini.read_text(os.path.join(K.ROOT, "maps", f)).replace("\r", "").split("\n"):
            bits = ln.split("\t")
            if bits[:2] == ["Id", pid]:
                return f[:-4], int(bits[2]), int(bits[3])
    raise SystemExit("No place %s" % pid)


_maps = {}


def map_of(name):
    if name not in _maps:
        _maps[name] = (Map(name), None)
        _maps[name] = (_maps[name][0], list(_maps[name][0].ents))
    return _maps[name][0]


def put(mapname, etype, kind, pid, at, opts="", exact=False, roofed=False, zone=None):
    """One entity with Id=pid on mapname (any line with that Id there first goes): at the tile at if exact (a spot
    worked out by hand, its back wall too), else the nearest free tile to it. zone: (r, chase) about it."""
    m = map_of(mapname)
    m.ents = [ln for ln in m.ents if not {"Id=%s" % pid, "Id=%s" % kind} & set(ln.split("\t")[-1].split())]
    # (and one with its kind's own name for an Id, as they had at first: an Id is never a sprite's name)
    x, y = at if exact else near_free(m, at[0], at[1], roofed)
    extra = "Id=%s" % pid + (" " + opts if opts else "")
    if zone:
        r, c = zone
        extra += " Zone=%d,%d,%d,%d Chase=%d,%d,%d,%d" % (max(2, x - r), max(2, y - r), min(XT - 1, x + r),
                                                          min(YT - 1, y + r), max(1, x - c), max(1, y - c),
                                                          min(XT, x + c), min(YT, y + c))
    m.ents.append(obj_line(etype, kind, x, y, extra, -8 if etype == "NPC" else 0))
    return x, y


def person(mapname, kind, pid, at, name=None, exact=False, face="S"):
    return put(mapname, "NPC", kind, pid, at, "Attitude=Good Stand=1 Face=%s Schedule=Always Name=%s" %
               (face, name or pid), exact)


def boss(mapname, kind, at, zone=None, exact=False, more=""):
    opts = ("Zone=%s Chase=%s" % zone if zone else "") + (" " + more if more else "")
    return put(mapname, "NPC", kind, kind + "_Boss", at, opts.strip(), exact, zone=None if zone else (3, 7))


def places():
    # ----- the main quest's (spots worked out on each map by hand)
    person("22,8,0", ORRIN, "Orrin", (6, 12), "Orrin", exact=True)
    boss("22,8,0", "Orrins_Shadow", (11, 16), ("8,14,14,19", "4,10,18,21"), exact=True)
    put("20,25,0", "StaticObject", "Lodestar_Altar", "Drowned_Shrine_Altar", (10, 8), exact=True)
    boss("20,25,0", "Rime_Warden", (10, 14), ("7,12,13,16", "3,9,17,20"), exact=True)
    put("23,9,0", "StaticObject", "Foundry_Hearth", "Ashen_Foundry_Hearth", (13, 11), exact=True)
    put("23,9,0", "StaticObject", "Foundry_Bellows", "Ashen_Foundry_Bellows", (15, 11), exact=True)
    boss("23,9,0", "Forgemother", (13, 17), ("10,16,17,19", "6,14,21,19"), exact=True)
    person("25,7,0", "Penitent", "Cael", (2, 13), exact=True)
    put("0,20,0", "StaticObject", "Sun_Forge", "Sunken_Temple_Forge", (8, 6), exact=True)
    for mid, at in (("Dawn_Mirror", (7, 13)), ("Noon_Mirror", (13, 13)), ("Dusk_Mirror", (10, 15))):
        put("0,20,0", "StaticObject", "Sun_Mirror", mid, at, exact=True)
    boss("0,20,0", "Sun_Keeper", (17, 15), ("14,12,20,18", "10,9,22,21"), exact=True)
    put("-7,10,0", "StaticObject", "Deep_Anvil", "Dwarf_Hall_Anvil", (15, 8), exact=True)
    for rune, at in (("Crown", (11, 16)), ("Root", (13, 16)), ("Hammer", (15, 16)), ("Rock", (17, 16))):
        put("-7,10,0", "StaticObject", "Rune_Stone_" + rune, "Dwarf_Hall_" + rune, at, exact=True)
    boss("-7,10,0", "Stone_King", (21, 14), ("18,13,24,16", "10,9,25,16"), exact=True)

    # ----- the points of interest: near each place's own name
    def near(pid, dx=0, dy=0):
        mapname, x, y = place_of(pid)
        return mapname, (x + dx, y + dy)

    person("18,27,0", OLD, "Old_Skadi", (9, 11), "Old_Skadi")
    m, at = near("Rustwater_Halt", 0, -2)
    x, y = person(m, MAN, "Lucky_Lem", at, "Lucky_Lem")
    put(m, "StaticObject", "Rat_Race_Track", "Lucky_Lems_Track", (x + 1, y))
    m, at = near("Ashfall_Outpost", -3, -2)
    person(m, OLD, "Vesna", at, "Vesna_the_Seer")
    m, at = near("Shardglass_Field")
    put(m, "NPC", "Wandering_Echo", "Shardglass_Echo", at, "Attitude=Good Schedule=Always Name=The_Wandering_Echo",
        zone=(3, 3))
    m, at = near("Drakes_Bones", 2, 0)
    person(m, "Merchant", "Mirage_Trader", at, "The_Mirage_Trader")
    m, at = near("Drakes_Bones", -4, 1)
    boss(m, "Sand_Mother", at)
    m, at = near("Fungus_Grotto", 1, 1)
    put(m, "StaticObject", "Echo_Pool", "Grotto_Echo_Pool", at)
    m, at = near("Delvers_Camp", 3, 0)
    person(m, "Farmer", "Fenn", at, "Fenn")
    m, at = near("Bonebreak_Mesa")
    boss(m, "Scavenger_King", at, more="Group=Bonebreak_Mesa")
    m, at = near("Yeti_Hollow", 3, 2)
    boss(m, "Old_Whitefang", at)
    m, at = near("Lava_Fields")
    boss(m, "Slag_Wyrm", at)

    for name, (m, before) in _maps.items():
        if m.ents != before:
            m.save()
            print("Placed on maps\\%s.txt" % name)


# ================================================================== the scripts
def w(name, rows):
    K.write_script(name, rows, MAKER)


def barrier_lights():
    """The barrier's Remove.Entity lines, as the old script had them (estforlan/story.py lays the lights)."""
    path = os.path.join(K.SCRIPTS, "Use Staff_of_Ashen With Barrier.txt")
    out = []
    for ln in ini.read_text(path).replace("\r", "").split("\n"):
        bits = ln.split("\t")
        if len(bits) >= 4 and bits[1] == "Remove.Entity" and bits[3] == "Barrier_Light":
            out.append(("Remove.Entity", bits[2], "Barrier_Light"))
    return out or [("Remove.Entity", "224,%d" % y, "Barrier_Light") for y in (288, 320, 352)]


def rook():
    w("Talk to Captain_Rook", [
        (">Conditional", "$Attr.ShipQuest=0", "@ship"),           # (sailed before there was a chart to fetch)
        ("Get.Value", "ATTRIBUTE", "OrrinQuest", V1),
        (">Conditional", "$Variable.1=0", "@o1"),
        (">Quest.Can.Start", "OrrinQuest", "@calm"),
        say(ROOK, "Dragon Island? Ha! Nobody sails there and comes back, and I've done it twice. The reefs round it "
                  "move, matey. Not with the tide: they move.\\There was a chart that knew the way, once: Orrin's. "
                  "Best navigator Ashen ever had. He went up the Sundered Tower, south of the Wizards' Court, to read "
                  "the sky, and he never came down. Bring me Orrin's chart and I'll find your island.",
            ("I'll find it.", "@o_go"), ("Not now.", "@end")),
        ("@o_go",), ("Update.Attribute", "OrrinQuest", "=1"), started("Orrin's Chart"), ("End",),
        ("@o1",), (">Conditional", "$Variable.1<=3", "@o4"),
        say(ROOK, "Orrin's chart, matey. The Sundered Tower, south of the Wizards' Court. Mind the stairs: there "
                  "aren't any.", ("Right.", "@end")),
        ("@o4",), (">Conditional", "$Variable.1=4", "@lode"),
        (">Got.Item", "Valour_Chart", "1", "@nochart"),
        ("Take.Item", "Valour_Chart", "1"),
        ("Update.Attribute", "OrrinQuest", "=5"),
        complete("Orrin's Chart"),
        say(ROOK, "Orrin's own hand! See here: the reefs, the currents, the safe water, and every mark of it set by a "
                  "star. He steered by the Lodestar.\\Ah. There's the rub. The Lodestar's lost: the shrine that kept "
                  "it went under the ice, up in the Rime. Without it this is only a pretty picture.",
            ("Then I'll find the Lodestar.", "@lode"), ("Later.", "@end")),
        ("@nochart",), say(ROOK, "You've seen old Orrin, you say? Then where's his chart?", ("I'll fetch it.", "@end")),
        ("@lode",),
        ("Get.Value", "ATTRIBUTE", "LodestarQuest", V2),
        (">Conditional", "$Variable.2=0", "@l1"),
        (">Quest.Can.Start", "LodestarQuest", "@green"),
        ("Update.Attribute", "LodestarQuest", "=1"), started("The Frozen Lodestar"),
        say(ROOK, "There's a surveyor at Frostwatch Lodge, in the Rime: Nils. He's measured every crack in that ice "
                  "for twenty years. If anybody knows where the shrine went under, it's him.", ("I'll ask him.", "@end")),
        ("@green",),
        say(ROOK, "The Rime eats the green ones, matey. Come back with a few more scars and we'll talk about the "
                  "Lodestar.", ("Fair enough.", "@end")),
        ("@l1",), (">Conditional", "$Variable.2<=2", "@l3"),
        say(ROOK, "The Lodestar. Ask Nils at Frostwatch Lodge, and take a thick coat.", ("Right.", "@end")),
        ("@l3",), (">Conditional", "$Variable.2=3", "@ship"),
        (">Got.Item", "Frozen_Lodestar", "1", "@nolode"),
        ("Take.Item", "Frozen_Lodestar", "1"),
        ("Update.Attribute", "LodestarQuest", "=4"),
        complete("The Frozen Lodestar"),
        say(ROOK, "Look at it. Cold as the night it fell, and it still knows north. With this and Orrin's chart I "
                  "could sail blind.\\Which leaves my hull. There's a hole in it you could drive a cart through.",
            ("What do you need?", "@s_ask"), ("Later.", "@end")),
        ("@nolode",), say(ROOK, "Found the Lodestar, have you? Then where is it?", ("I'll fetch it.", "@end")),
        ("@ship",),
        ("Get.Value", "ATTRIBUTE", "ShipQuest", V1),
        (">Conditional", "$Variable.1=0", "@s1"),
        ("@s_ask",),
        (">Quest.Can.Start", "ShipQuest", "@calm"),
        say(ROOK, "Ten planks and twenty nails, and I'll take you to Dragon Island and back, dragons or no dragons.",
            ("I'll bring them.", "@s_go"), ("Not now.", "@end")),
        ("@s_go",), ("Update.Attribute", "ShipQuest", "=1"), started("A Ship for Dragon Island"), ("End",),
        ("@s1",), (">Conditional", "$Variable.1=1", "@s2"),
        (">Conditional", "$Item.Plank>=10 and $Item.Nails>=20", "@need"),
        ("Take.Item", "Plank", "10"), ("Take.Item", "Nails", "20"),
        ("Update.Attribute", "ShipQuest", "=2"),
        ("Display.Message", "Yellow", "Quest complete: A Ship for Dragon Island! Captain Rook's hull is whole.",
         "Quest"),
        say(ROOK, "Good timber, good iron. She'll float! Say the word and we'll sail.",
            ("Sail to Dragon Island.", "@sail"), ("Not yet.", "@end")),
        ("@sail",), ("Goto.Script", "Sail to Dragon Island"),
        ("@need",), say(ROOK, "Ten planks and twenty nails, matey. A carpenter's bench makes planks from logs.",
                        ("Right.", "@end")),
        ("@s2",), say(ROOK, "Dragon Island, is it? Hold on to your hat.", ("Sail to Dragon Island.", "@sail"),
                      ("Not today.", "@end")),
        ("@calm",), say(ROOK, "Sea's calm. Too calm. I don't trust it.", ("Goodbye.", "@end")),
        ("@end",), ("End",)])


def orrin():
    w("Talk to Orrin_Ghost", [
        ("Get.Value", "ATTRIBUTE", "OrrinQuest", V1),
        (">Conditional", "$Variable.1=0", "@a1"),
        say(ORRIN, "A ghost in a navigator's coat stares through you, out to sea. 'I steered by the stars,' it says to "
                   "nobody. 'Now there aren't any.'", ("...", "@end")),
        ("@a1",), (">Conditional", "$Variable.1=1", "@a2"),
        ("Play.Sound", "Whisper"),
        say(ORRIN, "Someone's climbed my tower. Living, too! How long since anyone living...\\Rook sent you? Rook! "
                   "Still afloat, the old barnacle. Then he wants my chart.\\It's yours, if you can take it. I came up "
                   "here to read the sky with Shards in my eyes, and the Shards read me back. What they read stood up "
                   "and walked off with my face and my chart. It's down among the stones below the tower.",
            ("I'll break it.", "@a1go"), ("Not yet.", "@end")),
        ("@a1go",), ("Update.Attribute", "OrrinQuest", "=2"), ("End",),
        ("@a2",), (">Conditional", "$Variable.1=2", "@a3"),
        say(ORRIN, "It's down there, wearing my face. Don't listen if it talks to you: it only knows what I was afraid "
                   "of.", ("I won't.", "@end")),
        ("@a3",), (">Conditional", "$Variable.1=3", "@a4"),
        ("Play.Sound", "Whisper"),
        ("Give.Item", "Valour_Chart", "1"),
        ("Update.Attribute", "OrrinQuest", "=4"),
        say(ORRIN, "It's gone. I can feel the sky again, every star of it.\\Here: my chart. Rook will know what to do "
                   "with it.\\And listen, heir. When the Shards were in my eyes I saw the dragon, over the mountains, "
                   "plain as I see you. It isn't sleeping, whatever they say in the pass. It's eating. And a sword "
                   "that's slept as long as the one you're after cuts like a stick.", ("I'll remember.", "@end")),
        ("@a4",),
        say(ORRIN, "Steer by the Lodestar, if you can find it. I never could again.", ("Goodbye.", "@end")),
        ("@end",), ("End",)])


def kill(mob, attr, lo, hi, to, title, words):  # noqa: ARG001 (title: for reading)
    """A boss's death, for each who fought it: the quest on, if it was at lo..hi."""
    w("Kill %s" % mob, [
        ("Get.Value", "ATTRIBUTE", attr, V1),
        (">Conditional", "$Variable.1>=%d and $Variable.1<=%d" % (lo, hi), "@end"),
        ("Update.Attribute", attr, "=%d" % to),
        ("Display.Message", "Yellow", words, "-"),
        ("@end",), ("End",)])


def lodestar():
    w("Talk to Surveyor_Nils", [
        ("Get.Value", "ATTRIBUTE", "LodestarQuest", V1),
        (">Conditional", "$Variable.1=1", "@n2"),
        say(MAN, "The Drowned Shrine? It isn't drowned, it's frozen: the lake came up over it one bad winter and never "
                 "went down again. North-east of here, past the ridge.\\Something stands guard at it. Big. White. I "
                 "measured it once, from a long way off. I'd rather not again.", ("Thank you.", "@n1go")),
        ("@n1go",), ("Update.Attribute", "LodestarQuest", "=2"), ("End",),
        ("@n2",), (">Conditional", "$Variable.1=2", "@odd"),
        say(MAN, "The Drowned Shrine, north-east, past the ridge. Bring a coat, and something sharp.",
            ("Right.", "@end"), ("Anything else?", "@odd")),
        ("@odd",), ("Goto.Script", "Odd Jobs for Surveyor_Nils"),
        ("@end",), ("End",)])
    w("Reach In Lodestar_Altar", [
        (">Distance.From.Clicked.Entity", "40", "@far"),
        ("Get.Value", "ATTRIBUTE", "LodestarQuest", V1),
        (">Conditional", "$Variable.1>=1 and $Variable.1<=2", "@not"),
        (">Entity.State", "Rime_Warden_Boss", ALIVE, "@free"),
        ("Display.Message", "DarkRed", "The Rime Warden stands over the shrine: it won't let you near the altar.",
         "Denied"),
        ("End",),
        ("@free",),
        ("Play.Sound", "Freeze"),
        ("Give.Item", "Frozen_Lodestar", "1"),
        ("Update.Attribute", "LodestarQuest", "=3"),
        ("Display.Message", "Yellow", "You break the ice out of the altar's bowl and lift out the Lodestar. It's cold "
                                      "enough to burn, and it tugs, gently, north.", "Success"),
        ("End",),
        ("@not",), (">Conditional", "$Variable.1=0", "@empty"),
        ("Display.Message", "Cyan", "A star of ice glitters in the altar's bowl, frozen fast.", "-"),
        ("End",),
        ("@empty",), ("Display.Refusal", "The altar's bowl is empty.", "Empty"),
        ("End",)] + FAR)


def barrier():
    lights = barrier_lights()
    unbind = ("Display.Message", "Cyan", "You hold the Staff of Ashen to the barrier and speak Bert's words of "
                                         "Unbinding..", "-")
    w("Use Staff_of_Ashen With Barrier", [
        (">Distance.From.Clicked.Tile", "64", "@far"),
        ("Get.Value", "ATTRIBUTE", "GalaithQuest", V1),
        (">Conditional", "$Variable.1=0", "@broken"),
        (">Conditional", "$Attr.BarrierSpell>=1", "@words"),
        (">Conditional", "$Attr.ShardgateQuest>=5", "@anchored"),    # (its anchor in the Shardrealm: build_shardgate.py)
        (">Conditional", "$Attr.AnvilQuest>=4", "@asleep"),          # (the sword woken in its three fires)
        (">Quest.Can.Start", "GalaithQuest", "@notready"),
        unbind, ("Play.Sound", "SpellCast"), ("Wait", "2")] + lights + [
        ("Play.Sound", "Thunder"),
        ("Update.Attribute", "GalaithQuest", "=1"),
        ("Display.Message", "Yellow", "..and the barrier shatters like glass. Beyond it, on the scorched ground before "
                                      "Galaith's walls, the dragon lifts its glittering head, and the sword in your "
                                      "hand sings back at it.", "-"),
        ("End",),
        ("@words",), ("Display.Refusal", "The staff hums against the barrier, but you don't know the words."),
        ("End",),
        ("@anchored",),
        unbind, ("Play.Sound", "SpellCast"), ("Wait", "2"),
        ("Display.Message", "DarkRed", "..and the barrier flares, shudders, and holds. Something beyond the world is "
                                       "feeding it.", "Fail"),
        (">Conditional", "$Attr.ShardgateQuest=0", "@end"),
        (">Quest.Can.Start", "ShardgateQuest", "@end"),
        ("Update.Attribute", "ShardgateQuest", "=1"),
        started("The Shardgate"),
        ("End",),
        ("@asleep",),
        unbind, ("Play.Sound", "SpellCast"), ("Wait", "2"),
        (">Conditional", "$Attr.WakeQuest=0", "@thin"),
        ("Play.Sound", "Shard_Voice"),
        ("Display.Message", "Cyan", "..and the barrier thins like ice in spring. Beyond it the dragon lifts its head: "
                                    "its hide is grown over with Shards, plates of them, glittering, and more push up "
                                    "through its scales as you watch.", "-"),
        ("Wait", "3"),
        ("Display.Message", "Red", "A voice like a landslide, inside your head: 'The little heir, and the old stick "
                                   "with it. My faithful Hand has fed me Shards through this wall, crumb by crumb, "
                                   "since the day it went up, and you bring me a sword that's fast asleep.'", "-"),
        ("Play.Sound", "Thunder"),
        ("Display.Message", "DarkRed", "The barrier floods back, thicker than before.", "Fail"),
        (">Quest.Can.Start", "WakeQuest", "@end"),
        ("Update.Attribute", "WakeQuest", "=1"),
        started("The Sleeping Sword"),
        ("End",),
        ("@thin",),
        ("Display.Message", "DarkRed", "..and the barrier thins. Beyond it the dragon's Shard plate glitters, and it "
                                       "laughs at the sword in your hand till the barrier floods back.", "Fail"),
        ("End",),
        ("@notready",),
        ("Display.Refusal", "The barrier thins under the staff, and beyond it the dragon turns to watch you. You "
                            "aren't ready to face it yet.", "Denied"),
        ("End",),
        ("@broken",), ("Display.Message", "Cyan", "The barrier is broken.", "-"),
        ("@end",), ("End",)] + FAR)


def bert():
    w("Bert's Errands", [
        (">Conditional", "$Attr.WakeQuest=1", "@shardgate"),
        say(BERT, "It laughed? At the Sword of Valour? ...Oh. Oh, I should have seen it coming.\\Every Shard the Hand "
                  "slips it through the barrier, it wears. They cling to it like iron filings to a lodestone, and I "
                  "don't like to think why.\\And the sword's been asleep since the first king laid it down. It was "
                  "made in three fires, heir, and it wants waking in them, in their order.",
            ("Where are they?", "@w2")),
        ("@w2",),
        say(BERT, "The first was the Ashen Foundry, in the Ashfall, where the old smiths worked before the ash came "
                  "down. The warden at the outpost there keeps an eye on what's left of it. She'll know the rest, or "
                  "know who does.\\Don't look at me like that. I'm a wizard, not a smith.", ("I'll go.", "@w3")),
        ("@w3",),
        ("Update.Attribute", "WakeQuest", "=2"),
        complete("The Sleeping Sword"),
        ("End",),
        ("@shardgate",), ("Goto.Script", "Bert and the Shardgate")])
    path = os.path.join(K.SCRIPTS, "Talk to Bert.txt")                 # (its seventh line sends you here first)
    text = ini.read_text(path).replace("\r", "")
    new = text.replace("\t>Conditional\t$Attr.ShardgateQuest=1 or", "\t>Conditional\t$Attr.WakeQuest=1 or "
                       "$Attr.ShardgateQuest=1 or", 1) if "$Attr.WakeQuest=1" not in text else text
    new = new.replace("\tGoto.Script\tBert and the Shardgate", "\tGoto.Script\tBert's Errands")
    if new != text:
        K.write_text(path, new.rstrip("\n").split("\n"))


def sword_used_on(thing):
    w("Use Sword_of_Valour With %s" % thing, [("Goto.Script", "Temper %s" % thing)])


def foundry():
    w("Talk to Warden_Oska", [
        (">Conditional", "$Attr.CaelQuest=1", "@f0"),
        (">Got.Item", "Cael_Confession", "1", "@f0"),
        say(WOMAN, "A letter? From the Chapel?\\...Cael. My brother Cael. He went up to the Chapel when we were young, "
                   "to burn for the dragon with the rest of them. I thought he'd burnt.\\He's sorry. He's sorry, it "
                   "says, all the way down the page.", ("He's still there, praying.", "@c2")),
        ("@c2",),
        ("Take.Item", "Cael_Confession", "1"),
        ("Update.Attribute", "CaelQuest", "=2"),
        complete("The Brother in the Ash"),
        say(WOMAN, "Then I'll go and fetch him myself, when my watch is done. Thank you. I didn't know I'd been "
                   "waiting to hear that.", ("Goodbye.", "@end")),
        ("@f0",),
        ("Get.Value", "ATTRIBUTE", "FoundryQuest", V1),
        (">Conditional", "$Variable.1=0", "@f1"),
        (">Quest.Can.Start", "FoundryQuest", "@odd"),
        say(WOMAN, "Bert sent you? About the Sword of Valour? Saints and ashes.\\Then you'll want the Foundry's great "
                   "hearth lit, and that means the Forgemother out of the way: the thing that took the Foundry when "
                   "the smiths ran. Slag and spite, walking. Then the bellows. Hot, but not too hot: a fire's like a "
                   "temper, the old smiths said.", ("Leave it to me.", "@f_go"), ("Something else...", "@odd")),
        ("@f_go",), ("Update.Attribute", "FoundryQuest", "=1"), started("The Ashen Foundry"), ("End",),
        ("@f1",), (">Conditional", "$Variable.1<=2", "@f3"),
        say(WOMAN, "The Foundry's south-west of here, under the smoke. The Forgemother first, then the bellows. Hot, "
                   "mind, not too hot.", ("Right.", "@end"), ("Something else...", "@odd")),
        ("@f3",), (">Conditional", "$Variable.1=3", "@odd"),
        ("Update.Attribute", "FoundryQuest", "=4"),
        complete("The Ashen Foundry"),
        say(WOMAN, "You lit the Foundry! I haven't seen that glow since I was a girl.\\The second fire? The old smiths "
                   "said the sword was carried south and west after them, a long way, to the Sun-Forge under the "
                   "sands. The nomads at their well still sing about it, if you can get them to stop singing about "
                   "everything else.", ("Thank you.", "@end")),
        ("@odd",), ("Goto.Script", "Odd Jobs for Warden_Oska"),
        ("@end",), ("End",)])
    w("Work Foundry_Bellows", [
        (">Distance.From.Clicked.Entity", "48", "@far"),
        (">Conditional", "$Attr.FoundryQuest=2", "@idle"),
        ("Play.Sound", "Bellows"),
        (">Random", "30", "@one"),
        ("Update.Attribute", "FoundryHeat", "+2"),
        ("Goto.Line", "@show"),
        ("@one",), ("Update.Attribute", "FoundryHeat", "+1"),
        ("@show",), (">Conditional", "$Attr.FoundryHeat>=4", "@c3"),
        ("Update.Attribute", "FoundryHeat", "=0"),
        ("Display.Message", "DarkRed", "Too much! The coals roar white, then slump, choked, to black. You'll have to "
                                       "start again.", "Fail"),
        ("End",),
        ("@c3",), (">Conditional", "$Attr.FoundryHeat=3", "@c2"),
        ("Display.Message", "Yellow", "The hearth burns white-gold: as hot as it'll ever want to be."),
        ("End",),
        ("@c2",), (">Conditional", "$Attr.FoundryHeat=2", "@c1"),
        ("Display.Message", "Yellow", "The coals burn orange."),
        ("End",),
        ("@c1",), ("Display.Message", "Yellow", "The coals glow a dull red."),
        ("End",),
        ("@idle",), (">Conditional", "$Attr.FoundryQuest>=3", "@cold"),
        ("Display.Message", "Cyan", "The bellows wheeze. The Foundry's hearth glows on by itself now."),
        ("End",),
        ("@cold",), ("Display.Message", "Cyan", "The bellows wheeze, and the cold hearth doesn't answer."),
        ("End",)] + FAR)
    w("Temper Foundry_Hearth", [
        (">Distance.From.Clicked.Entity", "48", "@far"),
        ("Get.Value", "ATTRIBUTE", "FoundryQuest", V1),
        (">Conditional", "$Variable.1=2", "@not"),
        (">Conditional", SWORD, "@nosword"),
        (">Conditional", "$Attr.FoundryHeat=3", "@cool"),
        ("Toggle.User.Input", "OFF"),
        ("Display.Message", "Cyan", "You lay the Sword of Valour in the white heart of the hearth..", "-"),
        ("Play.Sound", "Sword_Wake"),
        ("Wait", "2"),
        ("Update.Attribute", "FoundryQuest", "=3"),
        ("Update.Attribute", "FoundryHeat", "=0"),
        ("Toggle.User.Input", "ON"),
        ("Display.Message", "Yellow", "..and something in the blade turns over in its sleep. A thread of red light "
                                      "runs up it and fades.", "-"),
        ("End",),
        ("@cool",), ("Display.Message", "DarkRed", "The coals aren't hot enough to touch the blade.", "Denied"),
        ("End",),
        ("@nosword",), ("Display.Refusal", "You've nothing the hearth wants.", "Denied"),
        ("End",),
        ("@not",), (">Conditional", "$Variable.1>=3", "@cold"),
        ("Display.Message", "Cyan", "The Foundry's great hearth glows on, content."),
        ("End",),
        ("@cold",), ("Display.Message", "Cyan", "The Foundry's great hearth, cold for years."),
        ("End",)] + FAR)
    sword_used_on("Foundry_Hearth")


def sunforge():
    w("Talk to Nomad_Tarek", [
        ("Get.Value", "ATTRIBUTE", "SunforgeQuest", V1),
        (">Conditional", "$Variable.1=0", "@t1"),
        (">Quest.Can.Start", "SunforgeQuest", "@odd"),
        say(MAN, "The Sun-Forge? Oska sent you, then. My grandmother's grandmother kept that forge, back when it had a "
                 "roof and a priest who wasn't dead.\\The temple's south of the well, half under the dunes. The Keeper's "
                 "still in it, wrapped in his gold and his temper. Nobody's lit the forge since he took against the "
                 "living.", ("I'll go.", "@t_go"), ("Something else...", "@odd")),
        ("@t_go",), ("Update.Attribute", "SunforgeQuest", "=1"), started("The Sun-Forge"), ("End",),
        ("@t1",), (">Conditional", "$Variable.1=1", "@t2"),
        say(MAN, "The Keeper still keeps it? South of the well, under the dunes. Take water.", ("Right.", "@end"),
            ("Something else...", "@odd")),
        ("@t2",), (">Conditional", "$Variable.1<=3", "@t4"),
        say(MAN, "The Keeper's gone? Then it's the mirrors: the forge only burns with the sun on it, and the sun comes "
                 "down to it by mirrors. My grandmother had a song for them:\\'Dawn looks where the sun is born; noon "
                 "looks down on the dead; dusk looks where the sun lies down.'\\She sang it over the pot, too, which "
                 "never helped the stew.", ("Thank you.", "@end"), ("Something else...", "@odd")),
        ("@t4",), (">Conditional", "$Variable.1=4", "@odd"),
        ("Update.Attribute", "SunforgeQuest", "=5"),
        complete("The Sun-Forge"),
        say(MAN, "You lit it! I heard it from here, like a bell rung in a kiln.\\The third fire isn't ours. The dwarves "
                 "had an anvil, deep under the mountains in the Stoneways, and the delvers' camp has been digging after "
                 "it for years. Ask for Maud. Tell her Tarek says she still owes him a goat.", ("I will.", "@end")),
        ("@odd",), ("Goto.Script", "Odd Jobs for Nomad_Tarek"),
        ("@end",), ("End",)])
    ways = ("north", "east", "south", "west")
    for m in ("Dawn", "Noon", "Dusk"):
        a = "Mirror." + m
        rows = [(">Distance.From.Clicked.Entity", "48", "@far"),
                (">Conditional", "$Attr.SunforgeQuest=2", "@stuck"),
                ("Play.Sound", "Mirror_Turn"),
                ("Update.Attribute", a, "+1"),
                (">Conditional", "$Attr.%s>=4" % a, "@d0"),
                ("Update.Attribute", a, "=0")]                     # (past west it comes round to north)
        for k, way in enumerate(ways):
            rows += [("@d%d" % k,), (">Conditional", "$Attr.%s=%d" % (a, k), "@d%d" % (k + 1) if k < 3 else "@check"),
                     ("Display.Message", "Cyan", "The %s mirror grinds round on its post: now it looks %s." %
                      (m.lower(), way)),
                     ("Goto.Line", "@check")]
        rows += [("@check",),
                 (">Conditional", "$Attr.Mirror.Dawn=1 and $Attr.Mirror.Noon=2 and $Attr.Mirror.Dusk=3", "@end"),
                 ("Update.Attribute", "SunforgeQuest", "=3"),
                 ("Play.Sound", "Stone_Wake"),
                 ("Display.Message", "Yellow", "Sunlight leaps from mirror to mirror to mirror and strikes the "
                                               "Sun-Forge's great disc. It blazes like a second noon.", "-"),
                 ("@end",), ("End",),
                 ("@stuck",), (">Conditional", "$Attr.SunforgeQuest>=3", "@old"),
                 ("Display.Message", "Cyan", "The %s mirror throws the light where it's meant to." % m.lower()),
                 ("End",),
                 ("@old",), ("Display.Message", "Cyan", "Sand's packed hard round the mirror's post. It won't turn."),
                 ("End",)] + FAR
        w("Turn %s_Mirror" % m, rows)
    w("Temper Sun_Forge", [
        (">Distance.From.Clicked.Entity", "48", "@far"),
        ("Get.Value", "ATTRIBUTE", "SunforgeQuest", V1),
        (">Conditional", "$Variable.1=3", "@not"),
        (">Conditional", SWORD, "@nosword"),
        ("Toggle.User.Input", "OFF"),
        ("Display.Message", "Cyan", "You hold the Sword of Valour in the blaze of the Sun-Forge..", "-"),
        ("Play.Sound", "Sword_Wake"),
        ("Wait", "2"),
        ("Update.Attribute", "SunforgeQuest", "=4"),
        ("Toggle.User.Input", "ON"),
        ("Display.Message", "Yellow", "..and the blade drinks the light till it's too bright to look at. When it fades, "
                                      "the sword's warm in your hand, as if it had a pulse.", "-"),
        ("End",),
        ("@nosword",), ("Display.Refusal", "You've nothing the forge wants.", "Denied"),
        ("End",),
        ("@not",), (">Conditional", "$Variable.1>=4", "@cold"),
        ("Display.Message", "Cyan", "The Sun-Forge's disc still holds a little of the light."),
        ("End",),
        ("@cold",), ("Display.Message", "Cyan", "A great disc of gold-faced bronze, dark without the sun on it."),
        ("End",)] + FAR)
    sword_used_on("Sun_Forge")


RUNES = ("Root", "Rock", "Hammer", "Crown")                         # (the work-song's order)


def anvil():
    w("Talk to Delver_Maud", [
        ("Get.Value", "ATTRIBUTE", "AnvilQuest", V1),
        (">Conditional", "$Variable.1=0", "@m1"),
        (">Quest.Can.Start", "AnvilQuest", "@odd"),
        say(WOMAN, "Tarek sent you? Then he'll want his goat. Tell him no.\\The Deep Anvil: aye, we found the old dwarf "
                   "hall, west of here under the mountains. And the Stone King found us. It sits the dwarves' throne "
                   "as if it built it. Two of mine went in to talk to it. It doesn't talk.",
            ("I'll go.", "@m_go"), ("Something else...", "@odd")),
        ("@m_go",), ("Update.Attribute", "AnvilQuest", "=1"), started("The Deep Anvil"), ("End",),
        ("@m1",), (">Conditional", "$Variable.1=1", "@m2"),
        say(WOMAN, "The Stone King's still on its throne. West of here, under the mountains. Mind your head.",
            ("Right.", "@end"), ("Something else...", "@odd")),
        ("@m2",), (">Conditional", "$Variable.1<=3", "@m4"),
        say(WOMAN, "It's dead? Then the anvil. The dwarves locked it with four rune stones, and the only key left is a "
                   "work-song we sing down here, older than any of us:\\'Root to rock, rock to hammer, hammer to "
                   "crown.'\\Mind you don't sing flat.", ("Thank you.", "@end"), ("Something else...", "@odd")),
        ("@m4",), (">Conditional", "$Variable.1=4", "@odd"),
        ("Update.Attribute", "AnvilQuest", "=5"),
        complete("The Deep Anvil"),
        say(WOMAN, "Let me see it. ...Oh. Oh, that's a sword. I can hear it from here, humming like a hive.\\Go on, "
                   "then. Go and do whatever a sword like that's for.", ("Goodbye.", "@end")),
        ("@odd",), ("Goto.Script", "Odd Jobs for Delver_Maud"),
        ("@end",), ("End",)])
    for i, rune in enumerate(RUNES, 1):
        rows = [(">Distance.From.Clicked.Entity", "48", "@far"),
                (">Conditional", "$Attr.AnvilQuest=2", "@idle"),
                ("Play.Sound", "Rune_Strike"),
                (">Conditional", "$Attr.AnvilRunes=%d" % (i - 1), "@wrong"),
                ("Update.Attribute", "AnvilRunes", "=%d" % i),
                ("Display.Message", "Cyan", "The rune of the %s rings, low and long, and the note hangs in the hall." %
                 rune.lower())]
        if i == len(RUNES):
            rows += [("Update.Attribute", "AnvilQuest", "=3"),
                     ("Play.Sound", "Stone_Wake"),
                     ("Display.Message", "Yellow", "All four notes ring together, and on its dais the Deep Anvil wakes, "
                                                   "its runes burning a cold blue.", "-")]
        rows += [("End",),
                 ("@wrong",), ("Update.Attribute", "AnvilRunes", "=0"),
                 ("Display.Message", "DarkRed", "The rune of the %s clanks, flat, and the notes die away into the "
                                                "stone." % rune.lower(), "Fail"),
                 ("End",),
                 ("@idle",), (">Conditional", "$Attr.AnvilQuest>=3", "@dull"),
                 ("Display.Message", "Cyan", "The rune of the %s hums faintly, remembering." % rune.lower()),
                 ("End",),
                 ("@dull",), ("Display.Message", "Cyan", "The rune stone answers with a dull knock."),
                 ("End",)] + FAR
        w("Strike Rune_Stone_%s" % rune, rows)
    w("Temper Deep_Anvil", [
        (">Distance.From.Clicked.Entity", "48", "@far"),
        ("Get.Value", "ATTRIBUTE", "AnvilQuest", V1),
        (">Conditional", "$Variable.1=3", "@not"),
        (">Conditional", SWORD, "@nosword"),
        ("Toggle.User.Input", "OFF"),
        ("Display.Message", "Cyan", "You lay the Sword of Valour on the Deep Anvil and strike it, once..", "-"),
        ("Play.Sound", "Anvil"),
        ("Wait", "1"),
        ("Play.Sound", "Sword_Wake"),
        ("Wait", "2"),
        ("Replace.Item", "Sword_of_Valour", "Woken_Sword_of_Valour"),
        ("Update.Attribute", "AnvilQuest", "=4"),
        ("Toggle.User.Input", "ON"),
        ("Display.Message", "Yellow", "..and the note goes down through the mountain and comes back up as a voice. The "
                                      "Sword of Valour is awake: Shard-light runs along its edge, and it pulls, gently, "
                                      "towards Galaith.", "-"),
        ("End",),
        ("@nosword",), ("Display.Refusal", "You've nothing the anvil wants.", "Denied"),
        ("End",),
        ("@not",), (">Conditional", "$Variable.1>=4", "@cold"),
        ("Display.Message", "Cyan", "The Deep Anvil's runes burn on, blue and patient."),
        ("End",),
        ("@cold",), ("Display.Message", "Cyan", "A great anvil of black iron on its dais, its runes dark and cold."),
        ("End",)] + FAR)
    sword_used_on("Deep_Anvil")


def bosses():
    kill("Orrins_Shadow", "OrrinQuest", 1, 2, 3, "Orrin's Chart",
         "The Shadow comes apart like smoke in a wind, and up in the tower somebody sighs.")
    kill("Rime_Warden", "LodestarQuest", 1, 2, 2, "The Frozen Lodestar",
         "The Rime Warden shatters across the ice, and the shrine's altar stands unguarded.")
    kill("Forgemother", "FoundryQuest", 1, 1, 2, "The Ashen Foundry",
         "The Forgemother cracks and spills across the floor, and the Foundry's great hearth stands open.")
    kill("Sun_Keeper", "SunforgeQuest", 1, 1, 2, "The Sun-Forge",
         "The Sun Keeper falls into a heap of gold leaf and dust. The temple's mirrors stand unwatched.")
    kill("Stone_King", "AnvilQuest", 1, 1, 2, "The Deep Anvil",
         "The Stone King topples off the dwarves' throne and breaks like a dropped statue.")


def side():
    pen = "Penitent"
    w("Talk to Cael", [
        ("Get.Value", "ATTRIBUTE", "CaelQuest", V1),
        (">Conditional", "$Variable.1=0", "@c1"),
        (">Quest.Can.Start", "CaelQuest", "@pray"),
        say(pen, "A man in a burnt grey robe kneels by the chapel wall, away from the others.\\'I fed it,' he says, "
                 "not looking up. 'We all fed it. Shards through the barrier, a handful a week, singing. They said it "
                 "would make the world warm again. It's only made it hungry.'\\'My sister keeps the watch at Ashfall "
                 "Outpost. Oska. I can't go to her. Would you take her this?'",
            ("I'll take it.", "@c_go"), ("No.", "@end")),
        ("@c_go",), ("Give.Item", "Cael_Confession", "1"), ("Update.Attribute", "CaelQuest", "=1"),
        started("The Brother in the Ash"), ("End",),
        ("@c1",), (">Conditional", "$Variable.1=1", "@c2"),
        say(pen, "'Oska. At the outpost. Please.'", ("I'm going.", "@end")),
        ("@c2",), say(pen, "'She's coming for me? ...Then I'd better be here when she does.'", ("Goodbye.", "@end")),
        ("@pray",), say(pen, "A man in a burnt grey robe kneels by the chapel wall, praying under his breath. He "
                             "doesn't look up.", ("...", "@end")),
        ("@end",), ("End",)])
    w("Read Cael_Confession", [
        ("Play.Sound", "Paper"),
        say("Cael_Confession", "Oska,\\I went up to the Chapel to keep the fire. That's what they said we did. We "
                               "carried Shards up the pass every week and pushed them through the barrier, and the "
                               "thing on the other side took them, and we sang.\\The Shards sing too, if you hold "
                               "them long enough. They tell you whatever you want to hear. I wanted to hear that I "
                               "was warm.\\I'm sorry. Cael.", ("Fold it up.", "@end")),
        ("@end",), ("End",)])

    echo = "Wandering_Echo"
    rows = [("Get.Value", "ATTRIBUTE", "EchoQuest", V1),
            (">Conditional", "$Variable.1=0", "@e1"),
            (">Quest.Can.Start", "EchoQuest", "@hum"),
            ("Update.Attribute", "EchoQuest", "=1"), started("The Wandering Echo"),
            ("Goto.Line", "@ask"),
            ("@e1",), (">Conditional", "$Variable.1=1", "@done"),
            ("@ask",),
            say(echo, "The glass hums, and the hum is a voice, and the voice is yours, a little late.\\'Three "
                      "questions,' it says. 'I have been asking them a long time. Nobody stays to answer.'",
                ("Ask me.", "@r1"), ("Not now.", "@end"))]
    riddles = (("I'm spent like coin and I shine like glass, and I tell you whatever you want to hear. What am I?",
                ("A mirror.", "A Shard.", "A flatterer."), 1),
               ("Where does magic go when it breaks?", ("Into the ground.", "Nowhere: it's gone.",
                                                        "Into the Shardrealm."), 2),
               ("I was cut down long ago, and every scrap of me is still hungry. What am I?",
                ("A loaf of bread.", "Something under the world.", "A forest."), 1))
    for i, (text, answers, right) in enumerate(riddles, 1):
        rows += [("@r%d" % i,), (">Conditional", "$Attr.Echo.R%d=0" % i, "@r%d" % (i + 1) if i < 3 else "@next"),
                 say(echo, "'%s'" % text, *[(a, "@r%dok" % i if k == right else "@wrong") for k, a in enumerate(answers)]),
                 ("@r%dok" % i,), ("Update.Attribute", "Echo.R%d" % i, "=1"), ("Give.Item", "Shard", "10"),
                 ("Display.Message", "Yellow", "The glass rings, pleased, and gives up 10 Shards.", "Chime_Glass"),
                 ("Goto.Line", "@next")]
    rows += [("@next",), (">Conditional", "$Attr.Echo.R1=1 and $Attr.Echo.R2=1 and $Attr.Echo.R3=1", "@more"),
             ("Update.Attribute", "EchoQuest", "=2"), complete("The Wandering Echo"),
             say(echo, "'Answered,' says the voice, and for a moment it sounds like a great many voices, relieved. "
                       "'Then I can stop asking.'", ("Goodbye.", "@end")),
             ("@more",), say(echo, "'Yes,' hums the glass. 'Again.'", ("Ask me.", "@r1"), ("Later.", "@end")),
             ("@wrong",), ("Display.Message", "DarkRed", "The glass hums, flat. 'No.'", "Fail"), ("End",),
             ("@done",), say(echo, "The glass hums to itself, content.", ("...", "@end")),
             ("@hum",), say(echo, "The glass round your feet hums, and for a moment the hum sounds like your name.",
                            ("...", "@end")),
             ("@end",), ("End",)]
    w("Talk to Wandering_Echo", rows)

    tales = (("Every winter the rivers round here freeze thick enough to drive a cart over. I've done it myself, with "
              "a cart full of cheese.", False, "Ha! Quite right. That river ice wouldn't hold a cat."),
             ("There's a man at this very lodge who measures the cracks in the ice for a living.", True,
              "True as frost. Nils. He's measured my kitchen floor twice."),
             ("Once I kissed a Rime Drake on the nose, and it said thank you, and flew me home.", False,
              "Ha! No. It bit me. Here, look."))
    rows = [("Get.Value", "ATTRIBUTE", "SkadiQuest", V1),
            (">Conditional", "$Variable.1=0", "@k1"),
            (">Quest.Can.Start", "SkadiQuest", "@plain"),
            say(OLD, "'Sit down, sit down. I'm Skadi, and I've never told a lie in my life. That's the first one.\\Here's "
                     "a game: I tell you three tales, and you tell me which are true. Get all three and I'll knit you "
                     "something.'", ("Go on, then.", "@k_go"), ("Not now.", "@end")),
            ("@k_go",), ("Update.Attribute", "SkadiQuest", "=1"), started("Old Skadi's Tall Tales"),
            ("Goto.Line", "@t1"),
            ("@k1",), (">Conditional", "$Variable.1=1", "@told")]
    for i, (tale, true, reply) in enumerate(tales, 1):
        ok, no = "@t%dok" % i, "@wrong"
        rows += [("@t%d" % i,), (">Conditional", "$Attr.Skadi.T%d=0" % i, "@t%d" % (i + 1) if i < 3 else "@next"),
                 say(OLD, "'%s'" % tale, ("True.", ok if true else no), ("A lie.", no if true else ok)),
                 (ok,), ("Update.Attribute", "Skadi.T%d" % i, "=1"),
                 ("Display.Message", "Yellow", "'%s'" % reply), ("Goto.Line", "@next")]
    rows += [("@next",), (">Conditional", "$Attr.Skadi.T1=1 and $Attr.Skadi.T2=1 and $Attr.Skadi.T3=1", "@t1"),
             ("Update.Attribute", "SkadiQuest", "=2"), complete("Old Skadi's Tall Tales"),
             say(OLD, "'Three out of three! Nobody gets three. Here: these were for my nephew, but he's got hands like "
                      "shovels.'", ("Thank you.", "@end")),
             ("@wrong",), ("Display.Message", "DarkRed", "'Ha! Got you,' says Skadi, delighted.", "Fail"), ("End",),
             ("@told",), say(OLD, "'Did I ever tell you about the time I... I did? Well, it's still true.'",
                             ("Goodbye.", "@end")),
             ("@plain",), say(OLD, "'Sit down, sit down. Did I ever tell you about the yeti that borrowed my kettle?'",
                              ("Goodbye.", "@end")),
             ("@end",), ("End",)]
    w("Talk to Old_Skadi", rows)


def curiosities():
    bets = [("Ten on Gristle.", "@bet"), ("Ten on Duchess.", "@bet"), ("Ten on Little Tom.", "@bet"),
            ("Not today.", "@end")]
    w("Talk to Lucky_Lem", [
        say(MAN, "'Rat races! Rat races! Three rats, one track, no refunds. Ten gold on a rat, and a winner pays "
                 "twenty-five.'\\Gristle's the fat one. Duchess bites. Little Tom has never once won, which means he's "
                 "due.", *bets),
        ("@bet",), (">Got.Item", "Gold_Coin(s)", "10", "@poor"),
        ("Take.Item", "Gold_Coin(s)", "10"),
        ("Toggle.User.Input", "OFF"),
        ("Play.Sound", "Squeak"),
        ("Display.Message", "Cyan", "'And they're off!' Three rats scurry down the planks..", "-"),
        ("Wait", "2"),
        ("Play.Sound", "Squeak"),
        ("Toggle.User.Input", "ON"),
        (">Random", "33", "@lose"),
        ("Give.Item", "Gold_Coin(s)", "25"),
        ("Display.Message", "Yellow", "..and yours wins by a whisker! Lem pays out, wincing.", "Coins"),
        ("Goto.Line", "@again"),
        ("@lose",), ("Display.Message", "DarkRed", "..and yours stops halfway to wash its face.", "Fail"),
        ("@again",), say(MAN, "'Again? The rats don't mind. The rats love it.'", *bets),
        ("@poor",), ("Display.Refusal", "You haven't ten gold.", "Denied"),
        ("@end",), ("End",)])
    w("Bet Rat_Race_Track", [("Goto.Script", "Talk to Lucky_Lem")])

    fortunes = ("'You'll meet a stranger. I'm counting myself.'",
                "'Fire, and a long fall, and something wearing what it ate. No, I can't make that one nice.'",
                "'You'll be rich. Not today. Today you're five gold poorer.'",
                "'There's a cat in your future. Ginger. It's sitting on something very important and it won't move.'",
                "'A crown. Heavy. You'll hate it after a week, like everyone does.'",
                "'Under the sea, a light that sings. Don't answer it.'")
    rows = [say(OLD, "'Five gold, and I'll tell you what's coming. It's mostly weather.'", ("Five gold, then.", "@pay"),
                ("No, thank you.", "@end")),
            ("@pay",), (">Got.Item", "Gold_Coin(s)", "5", "@poor"),
            ("Take.Item", "Gold_Coin(s)", "5"),
            ("Play.Sound", "Chime_Flame")]
    for k, f in enumerate(fortunes[:-1]):
        rows += [(">Random", str(round(100 / (len(fortunes) - k))), "@f%d" % (k + 1)),
                 say(OLD, "She peers into the smoke of her brazier for a long time.\\%s" % f, ("Thank you.", "@end")),
                 ("@f%d" % (k + 1),)]
    rows += [say(OLD, "She peers into the smoke of her brazier for a long time.\\%s" % fortunes[-1], ("Thank you.", "@end")),
             ("@poor",), ("Display.Refusal", "You haven't five gold.", "Denied"),
             ("@end",), ("End",)]
    w("Talk to Vesna", rows)

    w("Talk to Mirage_Trader", [
        say("Merchant", "'Water? Gems? A carpet that flies, but only on Tuesdays? Everything's for sale, friend. "
                        "Especially the things that aren't there.'", ("Show me.", "@shop"), ("Goodbye.", "@end")),
        ("@shop",), ("Display.Item.Rack", "GENERAL", "Merchant", "SHOP-Mirage", "@end"),
        ("@end",), ("End",)])
    w("Examine Mirage_Trader", [
        ("Display.Message", "Cyan", "A trader in a sun-bleached robe. Every time you look away, he's standing a little "
                                    "further off.", "-"),
        ("End",)])

    w("Listen Echo_Pool", [
        (">Distance.From.Clicked.Entity", "48", "@far"),
        (">Conditional", "$Attr.EchoPool=0", "@hum"),
        ("Play.Sound", "Geode_Song"),
        (">Random", "50", "@song2"),
        ("Display.Message", "Cyan", "The pool sings: deep, bright, bright, deep, bright.", "-"),
        ("Wait", "2"),
        say("Echo_Pool", "The water stills. It's waiting for you to sing it back.",
            ("Deep, bright, deep, bright, bright.", "@wrong"), ("Deep, bright, bright, deep, bright.", "@right"),
            ("Bright, deep, bright, bright, deep.", "@wrong")),
        ("@song2",),
        ("Display.Message", "Cyan", "The pool sings: bright, deep, deep, bright, deep.", "-"),
        ("Wait", "2"),
        say("Echo_Pool", "The water stills. It's waiting for you to sing it back.",
            ("Bright, deep, bright, deep, deep.", "@wrong"), ("Deep, deep, bright, bright, deep.", "@wrong"),
            ("Bright, deep, deep, bright, deep.", "@right")),
        ("@right",), ("Update.Attribute", "EchoPool", "=1"), ("Give.Item", "Shard", "20"),
        ("Display.Message", "Yellow", "The pool sings it back with you, note for note, and 20 Shards rise glittering "
                                      "out of the water into your hand.", "Chime_Water"),
        ("End",),
        ("@wrong",), ("Display.Message", "DarkRed", "Your song goes flat, and the pool falls silent.", "Fail"),
        ("End",),
        ("@hum",), ("Display.Message", "Cyan", "The pool hums your song to itself, very quietly.", "-"),
        ("End",)] + FAR)

    w("Talk to Fenn", [
        (">Conditional", "$Attr.Fenn.Gift=0", "@chat"),
        ("Update.Attribute", "Fenn.Gift", "=1"),
        ("Give.Item", "Cave_Mushroom", "3"),
        say("Farmer", "'Mushrooms! Cave mushrooms, the glowing kind: the only crop that likes the dark as much as I "
                      "do. Here, have a few. On the house. The house is a hole.'", ("Thank you.", "@end")),
        ("@chat",),
        (">Random", "50", "@c2"),
        say("Farmer", "'The trick is, you talk to them. Not nicely. Mushrooms don't trust nice.'", ("Goodbye.", "@end")),
        ("@c2",),
        say("Farmer", "'Maud says I can't sell them to the dwarves because there aren't any dwarves. I say that's just "
                      "what a dwarf would want you to think.'", ("Goodbye.", "@end")),
        ("@end",), ("End",)])


def takeover():
    """The four givers' own kill quests carry on as Odd Jobs for <who> (build_zones.py writes them so after)."""
    for who in ("Surveyor_Nils", "Warden_Oska", "Nomad_Tarek", "Delver_Maud"):
        old = os.path.join(K.SCRIPTS, "Talk to %s.txt" % who)
        new = os.path.join(K.SCRIPTS, "Odd Jobs for %s.txt" % who)
        if not os.path.exists(new):
            first = open(old, "rb").readline().decode("cp1252")
            assert MAKER not in first, "%s is this builder's already, with no Odd Jobs" % old
            os.replace(old, new)
            print("Moved %s's own talk to Odd Jobs for %s" % (who, who))


def scripts():
    takeover()
    rook()
    orrin()
    lodestar()
    barrier()
    bert()
    foundry()
    sunforge()
    anvil()
    bosses()
    side()
    curiosities()


def main():
    pictures()
    sounds()
    entities()
    quests()
    places()
    scripts()


if __name__ == "__main__":
    main()
