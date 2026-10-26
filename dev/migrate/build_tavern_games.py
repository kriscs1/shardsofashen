"""The tavern games' table (web/js/games.js draws it): the pictures and the sounds.

  * sprites\\Interface\\Game_Table.png: the green baize with its wooden rim, 200 x 100 (shown twice as big);
    Game_Cup.png (a wooden cup, upside down), Game_Coin.png, Game_Die1-6.png (ivory dice, 16 x 16).
  * sounds\\Dice_Roll.wav (dice clattering to a stop), Cup_Shuffle.wav (three cups slid over the baize).
Run it again to draw and make them again (the same).

  python -I "dev\\migrate\\build_tavern_games.py"
"""
import math
import os
import random
import struct
import wave

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame  # noqa: E402

OUT = os.path.join(ROOT, "sprites", "Interface")
OUTLINE = (34, 30, 30)
RATE = 22050
PIPS = {1: [(1, 1)], 2: [(0, 0), (2, 2)], 3: [(0, 0), (1, 1), (2, 2)], 4: [(0, 0), (2, 0), (0, 2), (2, 2)],
        5: [(0, 0), (2, 0), (1, 1), (0, 2), (2, 2)], 6: [(0, 0), (2, 0), (0, 1), (2, 1), (0, 2), (2, 2)]}


def outlined(s):
    shape = pygame.mask.from_surface(s, 100)
    out = pygame.Surface(s.get_size(), pygame.SRCALPHA)
    sil = shape.to_surface(setcolor=OUTLINE + (255,), unsetcolor=(0, 0, 0, 0))
    for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        out.blit(sil, (dx, dy))
    out.blit(s, (0, 0))
    return out


def table():
    """The baize, a little mottled, inside a wooden rim with a lighter top edge."""
    rng = random.Random(7)
    w, h = 200, 100
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    s.fill((92, 58, 30))
    pygame.draw.rect(s, (130, 86, 46), (0, 0, w, h), 3)
    pygame.draw.line(s, (164, 116, 66), (3, 3), (w - 4, 3))
    felt = pygame.Rect(7, 7, w - 14, h - 14)
    s.fill((38, 104, 58), felt)
    for _ in range(900):
        x, y = rng.randrange(felt.left, felt.right), rng.randrange(felt.top, felt.bottom)
        s.set_at((x, y), (32, 94, 50) if rng.random() < 0.5 else (44, 114, 64))
    pygame.draw.rect(s, (24, 70, 38), felt, 1)                                 # (the baize's edge, in shadow)
    return s


def cup():
    """A wooden cup upside down: wider at its mouth, on the baize, its rim and a band of darker wood."""
    s = pygame.Surface((24, 28), pygame.SRCALPHA)
    pygame.draw.polygon(s, (150, 98, 52), [(6, 2), (17, 2), (21, 25), (2, 25)])
    pygame.draw.polygon(s, (182, 128, 74), [(7, 3), (10, 3), (7, 24), (4, 24)])   # (light down one side)
    pygame.draw.line(s, (104, 66, 32), (4, 12), (19, 12), 2)                    # (the band)
    pygame.draw.ellipse(s, (124, 80, 40), (1, 22, 22, 5))                       # (the rim)
    pygame.draw.ellipse(s, (150, 98, 52), (6, 0, 12, 4))
    return outlined(s)


def coin():
    s = pygame.Surface((10, 10), pygame.SRCALPHA)
    pygame.draw.circle(s, (168, 128, 30), (5, 5), 4)
    pygame.draw.circle(s, (230, 190, 60), (5, 5), 3)
    s.set_at((4, 3), (255, 236, 150))
    return outlined(s)


def die(n):
    """An ivory die, its corners worn round, n dark pips."""
    s = pygame.Surface((16, 16), pygame.SRCALPHA)
    pygame.draw.rect(s, (236, 228, 206), (1, 1, 14, 14), border_radius=3)
    pygame.draw.line(s, (204, 194, 168), (3, 14), (13, 14))                     # (its shadowed edge)
    pygame.draw.line(s, (204, 194, 168), (14, 3), (14, 13))
    for px, py in PIPS[n]:
        x, y = 4 + px * 4, 4 + py * 4
        pygame.draw.rect(s, (40, 30, 30), (x - 1, y - 1, 2, 2))
    return outlined(s)


def pictures():
    pygame.init()
    pygame.display.set_mode((1, 1))
    pygame.image.save(table(), os.path.join(OUT, "Game_Table.png"))
    pygame.image.save(cup(), os.path.join(OUT, "Game_Cup.png"))
    pygame.image.save(coin(), os.path.join(OUT, "Game_Coin.png"))
    for n in range(1, 7):
        pygame.image.save(die(n), os.path.join(OUT, "Game_Die%d.png" % n))
    print("Drew the table, the cup, the coin and the dice")


# ---------------------------------------------------------------- the sounds
def write_wav(name, samples):
    with wave.open(os.path.join(ROOT, "sounds", name + ".wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(b"".join(struct.pack("<h", int(max(-1, min(1, v)) * 30000)) for v in samples))


def clack(out, at, loud, rng, pitch):
    """A die hitting wood: a sharp knock, a ringing tone and a burst of noise, dying fast."""
    for i in range(int(RATE * 0.05)):
        t = i / RATE
        env = math.exp(-t * 90)
        v = (0.6 * math.sin(2 * math.pi * pitch * t) + 0.5 * (rng.random() * 2 - 1)) * env * loud
        if at + i < len(out):
            out[at + i] += v


def dice_roll():
    """Dice rattled in the hand, thrown, bouncing to a stop: the knocks come closer and quieter."""
    rng = random.Random(3)
    out = [0.0] * int(RATE * 0.9)
    t = 0.0
    for k in range(5):                                                         # (the rattle in the hand)
        clack(out, int(t * RATE), 0.35, rng, 1800 + rng.random() * 400)
        t += 0.045
    t += 0.08
    gap, loud = 0.12, 0.9
    while gap > 0.012 and t < 0.85:                                            # (and the bounces)
        clack(out, int(t * RATE), loud, rng, 1300 + rng.random() * 500)
        clack(out, int((t + 0.008) * RATE), loud * 0.6, rng, 1500 + rng.random() * 500)
        t += gap
        gap *= 0.72
        loud *= 0.8
    return out


def cup_shuffle():
    """Three wooden cups slid over the baize: soft swishes, each ending in a light knock."""
    rng = random.Random(5)
    out = [0.0] * int(RATE * 1.3)
    prev = 0.0
    for k in range(4):
        start, length = 0.05 + k * 0.3, 0.22
        for i in range(int(RATE * length)):
            t = i / RATE
            env = math.sin(math.pi * t / length) * 0.35
            prev = prev * 0.85 + (rng.random() * 2 - 1) * 0.15                 # (low-passed noise: the slide)
            out[int((start + t) * RATE)] += prev * env * 3
        clack(out, int((start + length) * RATE), 0.35, rng, 700)
    return out


def sounds():
    write_wav("Dice_Roll", dice_roll())
    write_wav("Cup_Shuffle", cup_shuffle())
    print("Made sounds\\Dice_Roll.wav and Cup_Shuffle.wav")


def main():
    pictures()
    sounds()


if __name__ == "__main__":
    main()
