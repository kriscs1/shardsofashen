"""Combat and spell sounds (sounds\\*.wav), synthesised: 22050 Hz, 16-bit mono.

Run:  python -I "dev\\migrate\\build_sounds.py"
Deterministic and re-runnable: only files that change are written. Sounds that are already there and aren't in SOUNDS
(Miss, Pickup, Teleporter...) are left alone.

  Fight1-3      the player's blows landing (a thud, a slash, a heavy thump)
  Crit          a critical hit           Block    a blow turned by armour (a clang)
  Hurt          the player is hit        Death    the player dies
  SpellCast     a scroll is read (a rising whoosh)
  SpellFire, SpellIce, SpellLightning, SpellHeal, SpellShield    the spells' effects
  Kill_Beast, _Small, _Bird, _Livestock, _Humanoid, _Troll, _Undead, _Bug, _Dragon    a creature dies (its Kill.Sound)
"""
import math
import os
import random
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import p

RATE = 22050


def n(seconds):
    return int(RATE * seconds)


def env(i, total, attack=0.005, decay=6.0):
    t = i / float(RATE)
    a = min(1.0, t / attack) if attack > 0 else 1.0
    return a * math.exp(-decay * t)


def noise(seed, count, cutoff=0.25, high=0.0):
    """White noise through a one-pole low-pass (cutoff 0..1) and optional high-pass."""
    rng = random.Random(seed)
    out, lp, hp_prev, hp = [], 0.0, 0.0, 0.0
    for _ in range(count):
        x = rng.uniform(-1, 1)
        lp += cutoff * (x - lp)
        if high:
            hp = (1 - high) * (hp + lp - hp_prev)
            hp_prev = lp
            out.append(hp)
        else:
            out.append(lp)
    return out


def tone(freq, count, phase=0.0, glide=0.0, shape="sine"):
    out, ph = [], phase
    for i in range(count):
        f = freq * (1 + glide * i / max(1, count))
        ph += 2 * math.pi * f / RATE
        s = math.sin(ph)
        if shape == "square":
            s = 1.0 if s >= 0 else -1.0
        elif shape == "tri":
            s = 2 / math.pi * math.asin(math.sin(ph))
        out.append(s)
    return out


def mix(*parts):
    length = max(len(p_) for p_, _ in parts)
    out = [0.0] * length
    for sig, gain in parts:
        for i, s in enumerate(sig):
            out[i] += s * gain
    return out


def shaped(sig, attack=0.005, decay=6.0, delay=0.0):
    d = n(delay)
    return [0.0] * d + [s * env(i, len(sig), attack, decay) for i, s in enumerate(sig)]


def fight(seed, body_f, crack, decay):
    return mix((shaped(noise(seed, n(0.25), 0.18), 0.002, decay), 0.9),
               (shaped(tone(body_f, n(0.25), glide=-0.5), 0.002, decay * 1.3), 0.7),
               (shaped(noise(seed + 1, n(0.08), 0.9, high=0.5), 0.001, 40), crack))


def clang(base, partials=(1.0, 2.76, 5.4, 8.9), decay=7.0, length=0.5):
    parts = [(shaped(tone(base * k, n(length)), 0.001, decay * (1 + j * 0.6)), 0.5 / (1 + j)) for j, k in enumerate(partials)]
    parts.append((shaped(noise(77, n(0.05), 0.9, high=0.6), 0.001, 60), 0.6))
    return mix(*parts)


def arpeggio(freqs, step, length, decay=5.0):
    """Notes one after another, plucked on a harp (never a clean electronic tone; above C6 an octave down, so
    nothing's shrill: build_soundscape.harp_run)."""
    from build_soundscape import harp_run
    return harp_run(freqs, step, length)


def whoosh(seed, length, rise=True):
    out = []
    lp, rng = 0.0, random.Random(seed)
    total = n(length)
    for i in range(total):
        t = i / float(total)
        c = 0.03 + 0.5 * (t if rise else 1 - t)
        lp += c * (rng.uniform(-1, 1) - lp)
        out.append(lp * math.sin(math.pi * t) ** 1.5 * 2.2)
    return out


def crackle(seed, length, density=0.02):
    rng = random.Random(seed)
    out = noise(seed, n(length), 0.35)
    for i in range(len(out)):
        if rng.random() < density:
            out[i] += rng.uniform(-1.6, 1.6)
        out[i] *= math.exp(-3.0 * i / RATE)
    return out


SOUNDS = {
    "Fight1": lambda: fight(1, 150, 0.5, 18),
    "Fight2": lambda: mix((shaped(noise(2, n(0.22), 0.6, high=0.3), 0.01, 14), 0.8),
                          (shaped(tone(110, n(0.2), glide=-0.4), 0.002, 22), 0.6)),
    "Fight3": lambda: fight(3, 90, 0.35, 12),
    "Crit": lambda: mix((fight(4, 120, 0.8, 14), 1.0), (clang(880, decay=10, length=0.4), 0.5)),
    "Block": lambda: clang(520, decay=9, length=0.45),
    "Hurt": lambda: mix((shaped(noise(5, n(0.3), 0.12), 0.002, 12), 0.8),
                        (shaped(tone(180, n(0.3), glide=-0.45, shape="tri"), 0.01, 9), 0.6)),
    "Death": lambda: mix((shaped(tone(330, n(1.2), glide=-0.7, shape="tri"), 0.02, 2.2), 0.5),
                         (shaped(tone(220, n(1.2), glide=-0.7), 0.02, 2.0, delay=0.15), 0.4),
                         (shaped(noise(6, n(0.5), 0.1), 0.01, 5), 0.4)),
    "SpellCast": lambda: mix((whoosh(7, 0.45, True), 0.8), (shaped(tone(440, n(0.45), glide=1.0), 0.05, 5), 0.15)),
    "SpellFire": lambda: mix((crackle(8, 0.7), 0.8), (shaped(noise(9, n(0.7), 0.08), 0.01, 4), 0.6)),
    "SpellIce": lambda: mix(*[(shaped(tone(f, n(0.7), glide=-0.1), 0.002, 6 + k), 0.18)
                             for k, f in enumerate((1568, 2093, 2637, 3136, 1760))] +
                           [(shaped(noise(10, n(0.2), 0.95, high=0.7), 0.001, 25), 0.5)]),
    "SpellLightning": lambda: mix((shaped(noise(11, n(0.12), 0.98, high=0.2), 0.0005, 30), 1.0),
                                  (shaped(noise(12, n(0.9), 0.04), 0.03, 3), 1.0)),
    # (SpellHeal: build_soundscape.py)
    "SpellShield": lambda: mix((shaped(tone(98, n(0.8), glide=0.2, shape="tri"), 0.1, 2.5), 0.5),
                               (shaped(tone(147, n(0.8), glide=0.2), 0.1, 2.5), 0.4),
                               (whoosh(13, 0.8, False), 0.4)),
}


# ------------------------------------------------------------------ work, places and rewards
def knock(seed, f, length=0.16):
    """A hollow wooden knock: a short falling tone and a soft thump of noise."""
    return mix((shaped(tone(f, n(length), glide=-0.35, shape="tri"), 0.001, 32), 0.8),
               (shaped(noise(seed, n(length), 0.25), 0.001, 45), 0.6))


def creak(seed, f, length, glide=0.35):
    """Wood bending: a scratchy, wobbling low tone."""
    rng = random.Random(seed)
    out, ph = [], 0.0
    total = n(length)
    for i in range(total):
        t = i / float(total)
        fr = f * (1 + glide * t) * (1 + 0.04 * math.sin(2 * math.pi * 23 * i / RATE)) + rng.uniform(-6, 6)
        ph += 2 * math.pi * fr / RATE
        s = 2 / math.pi * math.asin(math.sin(ph))
        out.append(s * math.sin(math.pi * t) * (0.6 + 0.4 * rng.random()))
    return out


def delay(sig, seconds):
    return [0.0] * n(seconds) + sig


def ladder():
    """Climbing: three rungs (knock, knock, knock) with a creak of the wood between."""
    return mix((knock(40, 210), 0.9), (delay(knock(41, 190), 0.26), 0.85), (delay(knock(42, 225), 0.52), 0.8),
               (delay(creak(43, 160, 0.3), 0.08), 0.18), (delay(creak(44, 150, 0.3), 0.34), 0.15))


def pick_strike(seed, f):
    return mix((clang(f, partials=(1.0, 2.3, 3.9, 6.1), decay=16, length=0.22), 0.7),
               (shaped(crackle(seed, 0.3, 0.012), 0.002, 9, delay=0.02), 0.7))


def bubbles(seed, length, count):
    rng = random.Random(seed)
    parts = []
    for k in range(count):
        f = rng.uniform(260, 720)
        parts.append((shaped(tone(f, n(0.07), glide=0.9), 0.003, 40, delay=rng.uniform(0, length - 0.1)), 0.5))
    return mix(*parts)


def coins(seed, count=6):
    rng = random.Random(seed)
    parts = []
    for k in range(count):
        f = rng.uniform(2600, 4200)
        at = k * 0.06 + rng.uniform(0, 0.03)
        parts.append((shaped(mix((tone(f, n(0.25)), 0.6), (tone(f * 1.48, n(0.25)), 0.3)), 0.001, 22, delay=at), 0.5))
    return mix(*parts)


SOUNDS.update({
    "Ladder": ladder,
    "Mine": lambda: mix((pick_strike(50, 1350), 1.0), (delay(pick_strike(51, 1200), 0.42), 0.9)),
    "Splash": lambda: mix((shaped(noise(52, n(0.55), 0.55, high=0.25), 0.004, 7), 0.9), (bubbles(53, 0.5, 5), 0.5)),
    "Anvil": lambda: mix((clang(660, decay=6, length=0.7), 1.0), (delay(clang(700, decay=6, length=0.6), 0.36), 0.85)),
    "Smelt": lambda: mix((whoosh(54, 1.0, True), 0.9), (crackle(55, 1.0, 0.01), 0.4),
                         (shaped(tone(55, n(1.0), shape="tri"), 0.2, 2.5), 0.4)),
    "Brew": lambda: mix((bubbles(56, 1.0, 14), 0.9), (shaped(noise(57, n(1.0), 0.05), 0.1, 2), 0.25)),
    "Craft": lambda: mix((knock(58, 320, 0.1), 0.6), (delay(knock(59, 300, 0.1), 0.18), 0.5),
                         (delay(shaped(noise(60, n(0.35), 0.4, high=0.4), 0.05, 8), 0.3), 0.5)),
    # (LevelUp and Quest: build_soundscape.py)
    "Coins": lambda: coins(61),
    "Door": lambda: mix((creak(62, 220, 0.55, glide=0.6), 0.45), (delay(knock(63, 120, 0.2), 0.5), 0.9)),
    "Locked": lambda: mix((clang(1300, decay=26, length=0.15), 0.5), (knock(64, 110, 0.2), 0.8)),   # (one clunk: it holds)
    "Chest": lambda: mix((creak(65, 180, 0.5, glide=0.5), 0.4), (delay(knock(66, 140, 0.22), 0.45), 0.9), (delay(coins(67, 3), 0.55), 0.35)),
    "Drop": lambda: knock(68, 150, 0.15),
})


# ------------------------------------------------------------------ deaths: sounds\Kill_<kind>.wav
# Played where a creature dies: Entities.ini Kill.Sound=<kind> (set for each monster by build_content.py).
def voice(f, length, glide=-0.5, vibrato=0.0, rate=6.0, shape="tri", rough=0.0, seed=0):
    """A creature's cry: a falling tone with vibrato, a little growl (rough) and a soft rise and fall."""
    rng = random.Random(seed)
    out, ph, total = [], 0.0, n(length)
    for i in range(total):
        t = i / float(total)
        fr = f * (1 + glide * t) * (1 + vibrato * math.sin(2 * math.pi * rate * i / RATE)) * (1 + rough * rng.uniform(-1, 1))
        ph += 2 * math.pi * fr / RATE
        x = math.sin(ph)
        if shape == "tri":
            x = 2 / math.pi * math.asin(x)
        elif shape == "square":
            x = math.copysign(abs(x) ** 0.3, x)
        out.append(x * min(1.0, t * 25) * (1 - t) ** 1.2)
    return out


def lowpass(sig, cutoff):
    out, lp = [], 0.0
    for x in sig:
        lp += cutoff * (x - lp)
        out.append(lp)
    return out


def clatter(seed, count, length):
    """Bones falling: dry knocks scattered over length seconds, thinning out."""
    rng = random.Random(seed)
    parts = []
    for k in range(count):
        at = length * (k / float(count)) ** 1.6 + rng.uniform(0, 0.03)
        parts.append((delay(knock(seed + k, rng.uniform(500, 1100), 0.08), at), 0.6 * (1 - 0.6 * k / count)))
    return mix(*parts)


def chitter(seed, length, rate=38.0):
    """Insect clicks: a hiss chopped into fast pulses."""
    sig = noise(seed, n(length), 0.9, high=0.55)
    total = len(sig)
    return [x * (1.0 if math.sin(2 * math.pi * rate * i / RATE) > 0.6 else 0.15) * (1 - i / float(total)) for i, x in enumerate(sig)]


KILLS = {
    "Beast": lambda: mix((voice(520, 0.55, glide=-0.6, vibrato=0.03, rate=9, rough=0.04, seed=601), 0.7),           # a yelp
                         (shaped(lowpass(noise(602, n(0.6), 0.5), 0.15), 0.01, 5), 0.6)),
    # (Small, a rat's squeal: build_soundscape.py)
    "Bird": lambda: mix((voice(760, 0.16, glide=0.3, vibrato=0.12, rate=45, shape="square", seed=611), 0.6),         # squawk
                        (delay(voice(690, 0.3, glide=-0.5, vibrato=0.1, rate=40, shape="square", seed=612), 0.15), 0.7),
                        (shaped(noise(613, n(0.4), 0.6, high=0.3), 0.01, 7, delay=0.05), 0.25)),
    "Livestock": lambda: mix((voice(150, 0.9, glide=-0.35, vibrato=0.05, rate=5.5, rough=0.01, seed=621), 0.8),     # a low moan
                             (voice(300, 0.9, glide=-0.35, vibrato=0.05, rate=5.5, shape="sine"), 0.25)),
    "Humanoid": lambda: mix((lowpass(voice(190, 0.75, glide=-0.45, vibrato=0.02, rate=7, rough=0.02, seed=631, shape="square"), 0.25), 0.9),
                            (shaped(noise(632, n(0.5), 0.12), 0.05, 5), 0.3),                                        # a groan
                            (delay(fight(633, 80, 0.2, 10), 0.55), 0.6)),                                            # and a fall
    "Troll": lambda: mix((lowpass(voice(85, 1.1, glide=-0.4, vibrato=0.04, rate=4, rough=0.06, seed=641, shape="square"), 0.12), 1.0),
                         (shaped(lowpass(noise(642, n(1.1), 0.4), 0.06), 0.05, 2.8), 0.8),                          # a roar
                         (delay(fight(643, 55, 0.1, 7), 0.9), 0.9)),                                                 # and a thud
    "Undead": lambda: mix((clatter(651, 11, 0.6), 1.0),                                                              # bones fall
                          (shaped(voice(330, 0.7, glide=-0.6, vibrato=0.08, rate=3, shape="sine"), 0.1, 3), 0.25)),
    "Bug": lambda: mix((chitter(661, 0.45), 0.8),                                                                    # click, hiss
                       (shaped(noise(662, n(0.5), 0.95, high=0.7), 0.01, 6, delay=0.1), 0.4)),
    "Dragon": lambda: mix((lowpass(voice(110, 2.0, glide=-0.55, vibrato=0.05, rate=3.5, rough=0.08, seed=671, shape="square"), 0.15), 1.0),
                          (lowpass(voice(220, 1.6, glide=-0.6, vibrato=0.06, rate=5, rough=0.05, seed=672, shape="square"), 0.2), 0.4),
                          (shaped(lowpass(noise(673, n(2.0), 0.5), 0.08), 0.15, 1.6), 0.8),                          # a roar
                          (delay(fight(674, 45, 0.15, 4), 1.7), 1.0)),                                               # and the crash
}
SOUNDS.update({"Kill_" + k: fn for k, fn in KILLS.items()})


# ------------------------------------------------------------------ ambience: sounds\Ambient_<name>.wav, 10 s loops
# Played on repeat by the game for each map (data\Ambient.ini, made by build_travel.py), quietly, under the sounds.
# Every slow change repeats a whole number of times in the loop, and the last half second is faded into the first,
# so there is no click where it starts again.
LOOP = 10.0


def loop_of(make):
    """make(count) -> a signal; returns LOOP seconds that join up end to start."""
    total, fade = n(LOOP), n(0.5)
    sig = make(total + fade)
    out = sig[:total]
    for i in range(fade):
        k = i / float(fade)
        out[i] = out[i] * k + sig[total + i] * (1 - k)
    return out


def swell(count, cycles, depth, base):
    return [base + depth * (0.5 + 0.5 * math.sin(2 * math.pi * cycles * i / n(LOOP))) for i in range(count)]


def scaled(sig, gains):
    return [s * g for s, g in zip(sig, gains)]


def events(seed, count, every, make, gain=1.0):
    """Short sounds (make(rng) -> signal) dropped in at random times, never across the loop's end."""
    rng = random.Random(seed)
    out = [0.0] * count
    t = rng.uniform(0.2, every)
    while t < LOOP - 1.2:
        s = make(rng)
        start = n(t)
        for i, v in enumerate(s):
            if start + i < count:
                out[start + i] += v * gain
        t += rng.uniform(every * 0.5, every * 1.5)
    return out


def chirp(rng):
    f = rng.uniform(2300, 3600)
    parts = []
    for k in range(rng.randint(2, 4)):
        parts.append((shaped(tone(f, n(0.09), glide=rng.uniform(0.15, 0.4)), 0.004, 30, delay=k * 0.13), 0.5))
    return mix(*parts)


def croak(rng):
    """A frog in the marsh: the same pulsed ribbit as Croak.wav (build_soundscape.ribbit), each one its own."""
    from build_soundscape import ribbit
    return [v * 0.6 for v in ribbit(rng.randint(1, 10 ** 6))]


def drip(rng):
    return shaped(tone(rng.uniform(900, 1500), n(0.25), glide=-0.35), 0.001, 22)


def patter(rng):
    """One raindrop: a tiny tick of bright noise."""
    sig = noise(rng.randint(0, 1 << 30), n(rng.uniform(0.006, 0.018)), rng.uniform(0.35, 0.8), high=0.35)
    return [s * rng.uniform(0.25, 1.0) for s in shaped(sig, 0.0005, rng.uniform(180, 320))]


def rainfall(seed, count, every):
    """Drops (patter) all through count samples, evenly thick (loop_of joins the end to the start)."""
    rng = random.Random(seed)
    out = [0.0] * count
    t = 0
    while t < count:
        for i, v in enumerate(patter(rng)):
            if t + i < count:
                out[t + i] += v
        t += max(1, n(rng.uniform(every * 0.3, every * 1.7)))
    return out


def wind(count, seed, cutoff, cycles=(2, 3)):
    gains = [a * b for a, b in zip(swell(count, cycles[0], 0.6, 0.3), swell(count, cycles[1], 0.4, 0.6))]
    return scaled(noise(seed, count, cutoff), gains)


AMBIENT = {
    "Forest": lambda: loop_of(lambda c: mix((wind(c, 501, 0.03), 0.6), (events(502, c, 1.6, chirp), 0.18))),
    "Wind": lambda: loop_of(lambda c: wind(c, 521, 0.045, (2, 5))),
    "Marsh": lambda: loop_of(lambda c: mix((wind(c, 531, 0.025), 0.4), (events(532, c, 1.3, croak), 0.5))),
    "Desert": lambda: loop_of(lambda c: mix((wind(c, 541, 0.08, (1, 4)), 0.8), (noise(542, c, 0.5, high=0.7), 0.05))),
    "Snow": lambda: loop_of(lambda c: mix((wind(c, 551, 0.06, (2, 3)), 0.8),
                                          (scaled(tone(420, c, glide=0.0), swell(c, 2, 0.12, 0.0)), 0.25))),
    "Cave": lambda: loop_of(lambda c: mix((noise(561, c, 0.008), 1.2), (events(562, c, 1.4, drip), 0.35))),
    "Lair": lambda: loop_of(lambda c: mix((noise(571, c, 0.006), 1.4),
                                          (scaled(noise(572, c, 0.03), swell(c, 2, 0.9, 0.0)), 0.6))),
    "Indoors": lambda: loop_of(lambda c: mix((noise(581, c, 0.01), 0.3), (crackle(582, LOOP + 0.5, 0.004)[:c], 0.5))),
    # the weather (ashen\weather.py plays these instead of a place's own while it rains)
    # rain: a patter of drops over a soft, steady hiss (no low rushing or swelling: that sounded like wind), now
    # and then a drip from the eaves; a storm: heavier, with a low steady rumble under it
    "Rain": lambda: loop_of(lambda c: mix((noise(591, c, 0.4, high=0.5), 0.12), (rainfall(592, c, 0.006), 0.5),
                                          (events(593, c, 0.7, drip), 0.05))),
    "Storm": lambda: loop_of(lambda c: mix((noise(601, c, 0.45, high=0.45), 0.2), (rainfall(602, c, 0.003), 0.55),
                                           (noise(603, c, 0.008), 0.5), (events(604, c, 0.5, drip), 0.05))),
}
SOUNDS.update({"Ambient_" + k: fn for k, fn in AMBIENT.items()})


def thunder():
    """A crack, then a long rolling rumble."""
    crack = shaped(noise(611, n(0.3), 0.6), 0.001, 14)
    roll = scaled(noise(612, n(3.2), 0.012), [math.exp(-1.1 * i / n(1.0)) * (0.7 + 0.3 * math.sin(i / n(0.21)))
                                               for i in range(n(3.2))])
    return mix((crack, 0.35), (roll, 1.0))


# (Thunder.wav itself is build_thunder.py's: not written here)


def wav_bytes(sig):
    peak = max(1e-6, max(abs(s) for s in sig))
    gain = 0.85 / peak
    frames = b"".join(struct.pack("<h", int(max(-1, min(1, s * gain)) * 32767)) for s in sig)
    header = b"RIFF" + struct.pack("<I", 36 + len(frames)) + b"WAVE"
    header += b"fmt " + struct.pack("<IHHIIHH", 16, 1, 1, RATE, RATE * 2, 2, 16)
    header += b"data" + struct.pack("<I", len(frames))
    return header + frames


def main():
    written = 0
    for name, fn in SOUNDS.items():
        blob = wav_bytes(fn())
        path = p("sounds", name + ".wav")
        if os.path.exists(path):
            with open(path, "rb") as f:
                if f.read() == blob:
                    continue
        with open(path, "wb") as f:
            f.write(blob)
        written += 1
    print("%d sounds, %d written" % (len(SOUNDS), written))


if __name__ == "__main__":
    main()
