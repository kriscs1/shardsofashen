"""Creatures of the water's edge: they swim (Swims=1: the water is theirs as well as the land), and now and then come
out onto the bank, a beach or a rock for a while, then slip back in.

  * Otter (the river by Ashford, the Saltmarsh): sits up on the bank. Drops Otter_Pelt (two make a Fur_Cap: Crafting),
    and now and then the trout it was eating.
  * Seal (Northport's harbour): hauls out to lie on the beach, and barks (Calls=Seal_Bark). Drops Seal_Pelt (two make
    Sealskin_Boots: Crafting) and Seal_Blubber: oily bait the salmon and the swordfish like better than worms.
  * Frog (Ashford's lily pond, the Isle's pond, the Saltmarsh): hops, croaks (Calls=Croak). Drops Frog_Legs: cook them
    on a fire, a fireplace or a range (Cooked_Frog_Legs).
Sprites: <Name>.png, the walk frames <Name>2a-c / 8a-c, <Name>_Swim2 / 8 (in the water: head and back above it),
the resting pose (Otter_Sit, Seal_Lie); the items; sounds\\Croak.wav and Seal_Bark.wav.
Run it again to draw and make them again; the animals are only placed once.

  python -I "dev\\migrate\\build_water_animals.py"
"""
import math
import os
import random
import struct
import sys
import wave

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame  # noqa: E402
from ashen import ini  # noqa: E402
from build_isle import Map, DATA, obj_line  # noqa: E402

OUTLINE = (34, 30, 30)
WATER_LINE = (200, 232, 248)
RATE = 22050


def outlined(s):
    shape = pygame.mask.from_surface(s, 100)
    out = pygame.Surface(s.get_size(), pygame.SRCALPHA)
    sil = shape.to_surface(setcolor=OUTLINE + (255,), unsetcolor=(0, 0, 0, 0))
    for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        out.blit(sil, (dx, dy))
    out.blit(s, (0, 0))
    return out


def ripples(s, cx, y, w):
    """The water round what's swimming: a light ring, broken, and a wake behind it."""
    pygame.draw.arc(s, WATER_LINE, (cx - w // 2, y - 3, w, 6), math.pi * 1.05, math.pi * 1.95, 1)
    pygame.draw.arc(s, WATER_LINE, (cx - w // 2, y - 3, w, 6), 0.1, math.pi * 0.9, 1)
    for k in range(3):
        s.set_at((cx - w // 2 - 3 - k * 3, y - 1 + k % 2), WATER_LINE)


# ---------------------------------------------------------------- the otter
OT = ((128, 86, 52), (92, 60, 34), (172, 128, 88), (214, 186, 150))   # fur, shade, light, its pale throat


def otter(frame):
    s = pygame.Surface((32, 32), pygame.SRCALPHA)
    bob = (0, -1, 0)[frame]
    fur, dark, light, pale = OT
    pygame.draw.polygon(s, fur, [(3, 23), (9, 20 + bob), (10, 23 + bob)])                  # the tail, thick, tapering
    for x, off in ((11, (0, 1, -1)[frame]), (20, (0, -1, 1)[frame])):                        # the far legs
        pygame.draw.line(s, dark, (x, 23 + bob), (x + off, 26), 2)
    pygame.draw.ellipse(s, fur, (8, 18 + bob, 18, 8))                                         # the long body
    pygame.draw.line(s, light, (11, 19 + bob), (21, 19 + bob))
    pygame.draw.ellipse(s, pale, (20, 21 + bob, 6, 4))
    for x, off in ((13, (0, -1, 1)[frame]), (22, (0, 1, -1)[frame])):                        # the near legs
        pygame.draw.line(s, fur, (x, 23 + bob), (x + off, 26), 2)
        s.set_at((x + off + 1, 26), dark)
    hx, hy = 26, 18 + bob                                                                     # the head, small, round
    pygame.draw.circle(s, fur, (hx, hy), 4)
    pygame.draw.ellipse(s, pale, (hx - 1, hy, 6, 3))
    s.set_at((hx - 2, hy - 4), dark)                                                          # (little ears)
    s.set_at((hx + 1, hy - 4), dark)
    s.set_at((hx + 1, hy - 1), (20, 16, 16))
    s.set_at((hx + 4, hy), (40, 26, 20))                                                      # (its nose)
    out = outlined(s)
    for wy in (hy + 1, hy + 2):                                                               # (whiskers)
        out.set_at((hx + 6, wy), (230, 226, 216))
    return out


def otter_sit():
    """Up on its hind legs, looking about, its paws together."""
    s = pygame.Surface((32, 32), pygame.SRCALPHA)
    fur, dark, light, pale = OT
    pygame.draw.polygon(s, fur, [(10, 28), (15, 25), (16, 28)])                               # the tail along the ground
    pygame.draw.ellipse(s, fur, (13, 13, 9, 15))                                              # the body, upright
    pygame.draw.ellipse(s, pale, (16, 15, 5, 9))
    pygame.draw.line(s, dark, (17, 19), (20, 19))                                             # (its paws)
    pygame.draw.circle(s, fur, (18, 10), 4)
    pygame.draw.ellipse(s, pale, (17, 11, 5, 3))
    s.set_at((16, 6), dark)
    s.set_at((19, 6), dark)
    s.set_at((19, 9), (20, 16, 16))
    s.set_at((21, 11), (40, 26, 20))
    return outlined(s)


def otter_swim():
    s = pygame.Surface((32, 32), pygame.SRCALPHA)
    fur, dark, light, pale = OT
    pygame.draw.ellipse(s, dark, (8, 21, 14, 4))                                              # (its back, just under)
    pygame.draw.circle(s, fur, (24, 20), 4)
    pygame.draw.ellipse(s, pale, (23, 21, 5, 3))
    s.set_at((22, 16), dark)
    s.set_at((25, 16), dark)
    s.set_at((25, 19), (20, 16, 16))
    out = outlined(s)
    ripples(out, 18, 24, 20)
    return out


# ---------------------------------------------------------------- the seal
SE = ((128, 132, 140), (88, 92, 102), (172, 176, 184), (196, 196, 196))   # coat, shade, light, belly


def seal(frame):
    """Plump and grey, humping along on its belly: the body bunches and stretches."""
    s = pygame.Surface((32, 32), pygame.SRCALPHA)
    coat, dark, light, belly = SE
    squash = (0, 1, 0)[frame]
    pygame.draw.polygon(s, dark, [(2, 22), (6, 24), (2, 27)])                                 # the hind flippers
    pygame.draw.ellipse(s, coat, (4, 17 - squash, 22 - squash * 2, 10 + squash))              # the body
    pygame.draw.ellipse(s, belly, (8, 23, 15, 4))
    pygame.draw.line(s, light, (8, 18 - squash), (19, 18 - squash))
    for x, y in ((9, 20), (14, 19), (18, 21)):                                                # (its spots)
        s.set_at((x, y - squash), dark)
    pygame.draw.polygon(s, dark, [(17, 24), (21, 27), (15, 27)])                              # the front flipper
    hx, hy = 25, 17 - squash                                                                  # the head, round
    pygame.draw.circle(s, coat, (hx, hy), 5)
    pygame.draw.ellipse(s, light, (hx, hy, 6, 4))
    pygame.draw.rect(s, (16, 14, 18), (hx + 1, hy - 2, 2, 2))                                 # (big dark eyes)
    s.set_at((hx + 5, hy + 1), (40, 36, 40))
    out = outlined(s)
    for wy in (hy + 2, hy + 3):
        out.set_at((hx + 7, wy), (236, 236, 236))
    return out


def seal_lie():
    """Flat out on the sand, basking: long and low, its tail flippers curled up, head resting, eyes shut."""
    s = pygame.Surface((32, 32), pygame.SRCALPHA)
    coat, dark, light, belly = SE
    pygame.draw.polygon(s, dark, [(2, 21), (6, 25), (1, 27)])                                 # (the tail flippers)
    pygame.draw.ellipse(s, coat, (4, 21, 23, 8))                                              # the body, long and low
    pygame.draw.line(s, light, (8, 22), (21, 22))
    for x, y in ((9, 24), (14, 23), (19, 25)):                                                # (its spots)
        s.set_at((x, y), dark)
    pygame.draw.ellipse(s, dark, (15, 27, 6, 2))                                              # (a flipper, tucked)
    pygame.draw.circle(s, coat, (26, 24), 4)                                                  # the head, down
    pygame.draw.ellipse(s, light, (26, 24, 5, 3))
    pygame.draw.line(s, (16, 14, 18), (26, 22), (28, 22))                                     # (eyes shut)
    return outlined(s)


def seal_swim():
    s = pygame.Surface((32, 32), pygame.SRCALPHA)
    coat, dark, light, belly = SE
    pygame.draw.ellipse(s, dark, (8, 22, 12, 3))
    pygame.draw.circle(s, coat, (22, 20), 5)
    pygame.draw.ellipse(s, light, (22, 20, 6, 4))
    pygame.draw.rect(s, (16, 14, 18), (23, 17, 2, 2))
    out = outlined(s)
    ripples(out, 18, 24, 22)
    return out


# ---------------------------------------------------------------- the frog
FR = ((92, 168, 70), (52, 116, 44), (150, 206, 110), (220, 220, 150))   # green, dark, light, its belly


def frog(frame):
    """Crouched, big-eyed; frame b is the hop (stretched out, off the ground)."""
    s = pygame.Surface((32, 32), pygame.SRCALPHA)
    green, dark, light, belly = FR
    if frame == 1:
        pygame.draw.line(s, dark, (10, 22), (6, 25), 2)                                       # (legs out behind)
        pygame.draw.ellipse(s, green, (10, 17, 13, 7))
        pygame.draw.ellipse(s, belly, (13, 21, 8, 3))
        pygame.draw.line(s, green, (21, 22), (24, 25), 1)
        ex, ey = 20, 17
    else:
        pygame.draw.ellipse(s, dark, (8, 22, 8, 5))                                           # (the folded back legs)
        pygame.draw.ellipse(s, green, (10, 20, 13, 8))
        pygame.draw.ellipse(s, belly, (14, 24, 8, 4))
        pygame.draw.line(s, green, (20, 25), (22, 28), 1)                                     # (a front leg)
        ex, ey = 20, 20
    for x in (ex - 3, ex):                                                                    # the big eyes, on top
        pygame.draw.circle(s, light, (x, ey), 2)
        s.set_at((x, ey), (20, 20, 16))
    pygame.draw.line(s, dark, (ex - 4, ey + 3), (ex + 2, ey + 3))                             # (its wide mouth)
    return outlined(s)


def frog_swim():
    s = pygame.Surface((32, 32), pygame.SRCALPHA)
    green, dark, light, belly = FR
    pygame.draw.ellipse(s, green, (11, 21, 10, 4))
    for x in (14, 18):
        pygame.draw.circle(s, light, (x, 21), 2)
        s.set_at((x, 21), (20, 20, 16))
    out = outlined(s)
    ripples(out, 16, 24, 16)
    return out


# ---------------------------------------------------------------- the things they leave
def item(draw):
    s = pygame.Surface((32, 32), pygame.SRCALPHA)
    draw(s)
    return outlined(s)


def pelt(s, coat, dark, spots=False):
    pygame.draw.polygon(s, coat, [(6, 12), (12, 9), (21, 9), (27, 12), (25, 22), (20, 25), (12, 25), (7, 22)])
    pygame.draw.line(s, dark, (8, 17), (25, 17))                                              # (folded over)
    for x, y in ((10, 12), (26, 13), (9, 23), (24, 23)):
        s.set_at((x, y), dark)
    if spots:
        for x, y in ((13, 13), (18, 21), (22, 12), (11, 20)):
            s.set_at((x, y), dark)


ITEMS = {
    "Otter_Pelt": lambda s: pelt(s, OT[0], OT[1]),
    "Seal_Pelt": lambda s: pelt(s, SE[0], SE[1], spots=True),
    "Seal_Blubber": lambda s: (pygame.draw.ellipse(s, (238, 226, 176), (8, 12, 17, 11)),
                               pygame.draw.ellipse(s, (210, 196, 146), (10, 18, 13, 5)),
                               pygame.draw.line(s, (130, 132, 140), (9, 14), (21, 12), 2)),
    "Frog_Legs": lambda s: [(pygame.draw.line(s, FR[0], (12 + k * 6, 10), (10 + k * 6, 20), 3),
                             pygame.draw.line(s, (232, 196, 180), (10 + k * 6, 20), (13 + k * 6, 26), 2))
                            for k in (0, 1)],
    "Cooked_Frog_Legs": lambda s: [(pygame.draw.line(s, (176, 112, 52), (12 + k * 6, 10), (10 + k * 6, 20), 3),
                                    pygame.draw.line(s, (214, 160, 96), (10 + k * 6, 20), (13 + k * 6, 26), 2))
                                   for k in (0, 1)],
    "Fur_Cap": lambda s: (pygame.draw.ellipse(s, OT[0], (7, 10, 18, 14)), pygame.draw.rect(s, OT[2], (6, 19, 20, 5)),
                          pygame.draw.line(s, OT[1], (8, 21), (24, 21))),
    "Sealskin_Boots": lambda s: [(pygame.draw.rect(s, SE[0], (7 + k * 9, 9, 6, 14)),
                                  pygame.draw.rect(s, SE[1], (7 + k * 9, 22, 9, 4)),
                                  pygame.draw.line(s, SE[2], (8 + k * 9, 11), (8 + k * 9, 20))) for k in (0, 1)],
}


def pictures():
    pygame.init()
    pygame.display.set_mode((1, 1))
    ents, walk = os.path.join(ROOT, "sprites", "Entities"), os.path.join(ROOT, "sprites", "Walk")
    flip = lambda im: pygame.transform.flip(im, True, False)                                  # noqa: E731
    for name, draw, swim, poses in (("Otter", otter, otter_swim, {"Sit": otter_sit}),
                                    ("Seal", seal, seal_swim, {"Lie": seal_lie}),
                                    ("Frog", frog, frog_swim, {})):
        frames = [draw(f) for f in range(3)]
        for f, im in zip("abc", frames):
            pygame.image.save(im, os.path.join(walk, "%s2%s.png" % (name, f)))
            pygame.image.save(flip(im), os.path.join(walk, "%s8%s.png" % (name, f)))
        pygame.image.save(frames[0], os.path.join(ents, name + ".png"))
        for pose, pic in list(poses.items()) + [("Swim", swim)]:
            im = pic()
            pygame.image.save(im, os.path.join(ents, "%s_%s2.png" % (name, pose)))
            pygame.image.save(flip(im), os.path.join(ents, "%s_%s8.png" % (name, pose)))
    for name, draw in ITEMS.items():
        pygame.image.save(item(draw), os.path.join(ents, name + ".png"))
    print("Drew the otter, the seal and the frog (walking, swimming, resting) and what they leave")


# ---------------------------------------------------------------- their calls
def write_wav(name, samples):
    with wave.open(os.path.join(ROOT, "sounds", name + ".wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(b"".join(struct.pack("<h", int(max(-1, min(1, v)) * 30000)) for v in samples))


def croak():
    """Ribbit: two quick throaty buzzes, the second a little higher."""
    out = []
    for k, (f, length) in enumerate(((150, 0.13), (185, 0.11))):
        n = int(RATE * length)
        for i in range(n):
            t = i / RATE
            env = math.sin(math.pi * i / n) ** 0.6
            buzz = 1 if math.sin(2 * math.pi * f * t) > 0 else -1                             # (a reedy square)
            pulse = 0.55 + 0.45 * math.sin(2 * math.pi * 38 * t)                              # (its throat's rattle)
            out.append(buzz * pulse * env * 0.38)
        out += [0.0] * int(RATE * 0.06)
    return out


def bark():
    """A seal's bark: two short honks, falling, rough."""
    rng = random.Random(9)
    out = []
    for f0 in (420, 380):
        n = int(RATE * 0.18)
        phase = 0.0
        for i in range(n):
            t = i / n
            f = f0 * (1 - 0.3 * t)
            phase += f / RATE
            saw = 2 * (phase % 1) - 1
            env = (min(1, t * 12)) * (1 - t) ** 1.5
            out.append((saw * 0.7 + (rng.random() * 2 - 1) * 0.3) * env * 0.5)
        out += [0.0] * int(RATE * 0.09)
    return out


def sounds():
    write_wav("Croak", croak())
    write_wav("Seal_Bark", bark())
    print("Made sounds\\Croak.wav and Seal_Bark.wav")


# ---------------------------------------------------------------- the data
ANIMALS = {
    "Otter": [("Type", "NPC"), ("Attitude", "Passive"), ("Examine.Info", "An otter, sleek and wet, never still for long."),
              ("Hitpoints", "8"), ("Attack.Speed", "1"), ("Strength", "1"), ("Defence", "2"), ("Aggro.Range", "0"),
              ("Aggressive", "0"), ("Movement.Speed", "2.4"), ("Walk.Speed", "0.5"), ("Roam.Radius", "4"),
              ("Chase.Radius", "0"), ("Pause", "2-7"), ("Respawn", "180"), ("Flees", "1"), ("Swims", "1"),
              ("States", "Sit"), ("Solid", "0"), ("Kill.Sound", "Small"),
              ("Drops", "Otter_Pelt,1-1,100 Raw_Trout,1-1,25")],
    "Seal": [("Type", "NPC"), ("Attitude", "Passive"), ("Examine.Info", "A grey seal with big dark eyes, spotted like "
              "wet slate."), ("Hitpoints", "20"), ("Attack.Speed", "1.4"), ("Strength", "1"), ("Defence", "3"),
             ("Aggro.Range", "0"), ("Aggressive", "0"), ("Movement.Speed", "1.8"), ("Walk.Speed", "0.4"),
             ("Roam.Radius", "4"), ("Chase.Radius", "0"), ("Pause", "4-14"), ("Respawn", "300"), ("Flees", "1"),
             ("Swims", "1"), ("States", "Lie"), ("Calls", "Seal_Bark"), ("Kill.Sound", "Beast"),
             ("Drops", "Seal_Pelt,1-1,100 Seal_Blubber,1-2,100")],
    "Frog": [("Type", "NPC"), ("Attitude", "Passive"), ("Examine.Info", "A fat green frog, all eyes and mouth."),
             ("Hitpoints", "2"), ("Attack.Speed", "1"), ("Strength", "0"), ("Defence", "1"), ("Aggro.Range", "0"),
             ("Aggressive", "0"), ("Movement.Speed", "2"), ("Walk.Speed", "0.6"), ("Roam.Radius", "3"),
             ("Chase.Radius", "0"), ("Pause", "2-9"), ("Respawn", "90"), ("Flees", "1"), ("Swims", "1"),
             ("Calls", "Croak"), ("Solid", "0"), ("Layer", "Under"), ("Kill.Sound", "Small"),
             ("Drops", "Frog_Legs,1-1,100")],
}
THINGS = {
    "Otter_Pelt": [("Type", "MapItem"), ("Examine.Info", "A thick, soft otter pelt. Two would make a warm cap "
                    "(Crafting)."), ("Stackable", "1"), ("Value", "24")],
    "Seal_Pelt": [("Type", "MapItem"), ("Examine.Info", "A spotted sealskin: it keeps the wet out. Two would make "
                   "boots (Crafting)."), ("Stackable", "1"), ("Value", "28")],
    "Seal_Blubber": [("Type", "MapItem"), ("Examine.Info", "A slab of seal blubber, oily and rank. The big fish love "
                      "it on a hook."), ("Stackable", "50"), ("Value", "3")],
    "Frog_Legs": [("Type", "MapItem"), ("Examine.Info", "A pair of frog's legs. Cook them on a fire or a range."),
                  ("Stackable", "1"), ("Value", "3")],
    "Cooked_Frog_Legs": [("Type", "MapItem"), ("Use.Words", "Eat"), ("Examine.Info", "Frog's legs, crisp and golden. "
                          "They taste like chicken. Mostly."), ("Stackable", "1"), ("Value", "7"), ("Food.Value", "4")],
    "Fur_Cap": [("Type", "MapItem"), ("Examine.Info", "A cap of otter fur, warm as toast."), ("Stackable", "1"),
                ("Value", "40"), ("Slot", "Head"), ("Attack", "0"), ("Defence", "2"), ("Durability", "140")],
    "Sealskin_Boots": [("Type", "MapItem"), ("Examine.Info", "Sealskin boots: dry feet, whatever the weather."),
                       ("Stackable", "1"), ("Value", "45"), ("Slot", "Feet"), ("Attack", "0"), ("Defence", "2"),
                       ("Durability", "160")],
}
RECIPES = [("Fur_Cap", "Otter_Pelt 2", "0.4", "8"), ("Sealskin_Boots", "Seal_Pelt 2", "0.5", "10")]


def data():
    ents = os.path.join(DATA, "Entities.ini")
    for name, keys in list(ANIMALS.items()) + list(THINGS.items()):
        if not ini.section(name, ents):
            for k, v in keys:
                ini.write(name, k, v, ents)
    racks = os.path.join(DATA, "ItemRacks.ini")
    craft = dict(ini.section("CRAFT-Crafting", racks) or [])
    for product, needs, xp, level in RECIPES:
        if not any(v.split(",")[0] == product for k, v in craft.items() if k.startswith("Item")):
            n = sum(1 for k in craft if k.startswith("Item")) + 1
            ini.write("CRAFT-Crafting", "Item%d" % n, "%s,%s,%s,%s" % (product, needs, xp, level), racks)
            craft["Item%d" % n] = product
    print("Entities.ini: the otter, the seal, the frog and their things; Fur_Cap and Sealskin_Boots to craft")


def write(name, lines, why):
    with open(os.path.join(DATA, "Scripts", name + ".txt"), "w", encoding="cp1252", newline="\r\n") as f:
        f.write("// %s Generated by dev\\migrate\\build_water_animals.py\n" % why + "\n".join(lines) + "\n")


def cook_script(where):
    return [
        "01\t>Distance.From.Clicked.Entity\t40\t18",
        "02\t>Got.Item\tFrog_Legs\t1\t16",
        "03\tTake.Item\tFrog_Legs\t1",
        "04\tDisplay.Message\tCyan\tYou put the frog's legs on the %s..." % where,
        "05\tPlay.Sound\tCookingFood",
        "06\tWait\t3",
        "07\tGet.Value\tSKILL\tCooking\tVariable.1$",
        "08\t>Conditional\t($Variable.1+50)>$Random.Percent\t13",
        "09\tDisplay.Message\tYellow\t..and cook them crisp and golden!",
        "10\tUpdate.Skill\tCooking\t+0.15",
        "11\tGive.Item\tCooked_Frog_Legs\t1",
        "12\tEnd",
        "13\tDisplay.Message\tDarkRed\t..but burn them to a crisp!\tFail",
        "14\tGive.Item\tBurnt_Meat\t1",
        "15\tEnd",
        "16\tDisplay.Message\tDarkRed\tYou don't have any frog's legs.\tDenied",
        "17\tEnd",
        "18\tDisplay.Message\tDarkRed\tYou are too far away!\tDenied",
        "19\tEnd"]


# the two big fish: worms, or the seal blubber they like better (a better chance)
BIG_FISH = {"Salmon_Spot": ("Raw_Salmon", "salmon", 20, "0.4", "cast your line across the current"),
            "Swordfish_Spot": ("Raw_Swordfish", "swordfish", 35, "0.6", "heave your line out towards the fin")}


def fish_script(spot):
    fish, name, level, xp, doing = BIG_FISH[spot]
    return [
        "01\t>Distance.From.Clicked.Entity\t64\t33",
        "02\t>Got.Item\tFishing_Rod\t1\t29",
        "03\tGet.Value\tSKILL\tFishing\tVariable.1$",
        "04\t>Conditional\t$Variable.1>=%d\t31" % level,
        "05\t>Got.Item\tSeal_Blubber\t1\t09",
        "06\tGet.Value\tCALCULATION\t15\tVariable.2$",
        "07\tDisplay.Message\tCyan\tYou bait the hook with seal blubber and %s..." % doing,
        "08\tGoto.Line\t13",
        "09\t>Got.Item\tBait\t1\t27",
        "10\tGet.Value\tCALCULATION\t0\tVariable.2$",
        "11\tDisplay.Message\tCyan\tYou bait the hook and %s..." % doing,
        "12\tGoto.Line\t13",
        "13\tShow.Skill\tFishing",
        "14\tPlay.Animation\tSplash\t1\tSplash",
        "15\tWait\t4",
        "16\t>Conditional\t($Variable.1-%d+40+$Variable.2)>$Random.Percent\t25" % level,
        "17\t>Conditional\t$Variable.2>0\t20",
        "18\tTake.Item\tSeal_Blubber\t1",
        "19\tGoto.Line\t21",
        "20\tTake.Item\tBait\t1",
        "21\tDisplay.Message\tYellow\t...and land a %s!" % name,
        "22\tGive.Item\t%s\t1" % fish,
        "23\tUpdate.Skill\tFishing\t+%s" % xp,
        "24\tEnd",
        "25\tDisplay.Message\tDarkRed\t...but it slips the hook. Your bait's still on.\tFail",
        "26\tEnd",
        "27\tDisplay.Message\tDarkRed\tYou need bait on the hook: worms, or seal blubber for the big ones.\tDenied",
        "28\tEnd",
        "29\tDisplay.Message\tDarkRed\tYou need a fishing rod.\tDenied",
        "30\tEnd",
        "31\tDisplay.Message\tDarkRed\tYou need level %d Fishing to catch the %s here.\tDenied" % (level, name),
        "32\tEnd",
        "33\tDisplay.Message\tDarkRed\tYou need to stand at the water's edge, by the spot!\tDenied",
        "34\tEnd"]


def scripts():
    for where, word in (("Fire", "fire"), ("Fireplace", "fire"), ("Range", "range")):
        write("Use Frog_Legs With " + where, cook_script(word), "Cooking frog's legs (anyone can).")
    for spot in BIG_FISH:
        write("Fish " + spot, fish_script(spot), "Fishing at a %s: worms, or seal blubber (a better chance)."
              % spot.replace("_", " ").lower())
    print("Scripts: cooking frog's legs; the salmon and swordfish spots take seal blubber too")


# ---------------------------------------------------------------- where they live
PLACES = [   # map, the zone (tiles: water and the bank by it), how many of what
    ("1,3,0", (14, 2, 24, 8), "Seal", 2),          # (Northport's harbour and its beach)
    ("3,3,0", (14, 11, 21, 19), "Otter", 2),       # (the river past Ashford)
    ("3,4,0", (9, 15, 14, 20), "Frog", 2),         # (Ashford's lily pond)
    ("1,7,0", (6, 4, 18, 12), "Otter", 1),         # (the Saltmarsh)
    ("1,7,0", (6, 4, 18, 12), "Frog", 2),
]


def isle_pond():
    """The Isle's pond (Id=Isle_Pond on 2,1,0), round it."""
    m = Map("2,1,0")
    for ln in m.ents:
        p = ln.split("\t")
        if p[:2] == ["Id", "Isle_Pond"]:
            x, y = int(p[2]), int(p[3])
            return ("2,1,0", (max(1, x - 3), max(1, y - 3), min(25, x + 3), min(21, y + 3)), "Frog", 2)
    return None


def place():
    from dsengine.data import GameData
    d = GameData(ROOT)
    n = 0
    places = PLACES + [p for p in (isle_pond(),) if p]
    for name, (x1, y1, x2, y2), kind, count in places:
        m = Map(name)
        if any(ln.startswith("NPC\t%s\t" % kind) for ln in m.ents):
            continue
        water = [(x, y) for y in range(y1, y2 + 1) for x in range(x1, x2 + 1)
                 if d.tile_water(m.tile(x, y)) and not m.ent_near(x, y, 10)]
        if not water:
            print("WARNING - no water for the %s on %s" % (kind, name))
            continue
        rng = random.Random(name + kind)
        for k in range(count):
            x, y = water[rng.randrange(len(water))]
            m.ents.append(obj_line("NPC", kind, x, y, "Attitude=Bad Zone=%d,%d,%d,%d" % (x1, y1, x2, y2), -8))
            n += 1
        m.save()
    print("Placed %d otters, seals and frogs" % n)


def main():
    pictures()
    sounds()
    data()
    scripts()
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import story_kit as K
    if not K.new_mainland():                 # (build_estforlan.py places these in the new mainland)
        place()


if __name__ == "__main__":
    main()
