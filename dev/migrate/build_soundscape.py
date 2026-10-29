"""The game's sounds of yes and no, of magic and of small creatures, in one voice that fits the old world: plucked
strings (a lute, a harp: Karplus-Strong), wood knocking, low soft bells, breath. No clean electronic tones and
nothing shrill. Each is written at its own loudness (a menu's tick is soft; a level gained is not). Sounds with a
few takes (Fail, Fail_2, Fail_3) are picked among at random as they play (audio.js), so a repeat doesn't grate.

  Saying no:      Denied (a knock on a shut shutter, low), Fail (a lute's sigh: three takes), Empty ("duh-derr" on
                  a low string), Fizzle (a spell's breath going out)
  The interface:  Click (a soft tick of parchment), Chat (a soft harp pluck), Hail (a carter's "hoy!")
  Doing well:     Gather_Wood, Gather_Ore, Gather_Fish, Harvest, Cooked, Crafted, Unlock, Learn, Success
  Magic:          Rare_Shard, Appear, Vanish, Swap, SpellHeal, LevelUp, Quest, Remnant_Rise, Absorb, Bloom_Harvest,
                  Freeze, Stone_Wake, Enchant, Portal, Gate_Built, Anchor_Shatter (harps for the old sine chimes)
  Creatures:      Croak (a frog's ribbit: a pulsed call, as a real frog makes it), Kill_Small (a rat's squeal)
  Traps:          Darts (a soft hiss of darts)

These were made by build_denied_sound, build_fail_sound, build_empty_sound, build_fizzle_sound, build_sounds,
build_tricks, build_shardcraft, build_shardgate, build_remnants, build_pocket, build_feathers_and_frost, build_carts,
build_water_animals and build_deep (and build_sounds.arpeggio plucks a harp now):
they're made only here now. Safe to run again (only changed files are written).

  python -I "dev\\migrate\\build_soundscape.py"
"""
import math
import os
import random
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import p                                                    # noqa: E402
from build_sounds import RATE, n, noise, tone, mix, shaped, delay, lowpass, voice, crackle  # noqa: E402


# ---------------------------------------------------------------------------------------------------- the palette
def pluck(freq, length, damp=0.996, bright=0.55, seed=1):
    """A plucked string (Karplus-Strong): noise in a delay line, softened each pass, so it rings and fades like gut."""
    rng = random.Random(seed)
    period = max(2, int(RATE / freq))
    buf = [rng.uniform(-1, 1) for _ in range(period)]
    lp = 0.0
    for i in range(period):                                             # (a softer pluck: the noise rounded first)
        lp += bright * (buf[i] - lp)
        buf[i] = lp
    out = []
    for i in range(n(length)):
        j = i % period
        nxt = buf[(i + 1) % period]
        v = buf[j]
        buf[j] = damp * 0.5 * (v + nxt)
        out.append(v)
    return out


def lute(freq, length, seed=1, damp=0.995):
    """A lute note: the string and its wooden body (a low, rounded copy under it)."""
    s = pluck(freq, length, damp, 0.5, seed)
    return mix((s, 0.8), (lowpass(s, 0.12), 0.6), (shaped(noise(seed + 50, n(0.03), 0.3), 0.001, 80), 0.15))


def harp(freq, length, seed=1):
    return pluck(freq, length, 0.998, 0.65, seed)


def knock(f, length=0.18, seed=1, soft=0.25):
    """Knuckles on wood: a muffled thump and the hollow ring of the board."""
    return mix((shaped(tone(f, n(length), glide=-0.25), 0.001, 26), 0.7),
               (shaped(tone(f * 2.3, n(length), glide=-0.2), 0.001, 40), 0.2),
               (shaped(noise(seed, n(length), soft), 0.001, 55), 0.55))


def bell(f, length, decay=3.0):
    """A small, low bell: inharmonic partials, the high ones dying first."""
    parts = [(1.0, 1.0), (2.0, 0.5), (2.76, 0.35), (4.07, 0.18), (5.4, 0.1)]
    return mix(*[(shaped(tone(f * k, n(length)), 0.004, decay * (1 + j * 0.9)), g) for j, (k, g) in enumerate(parts)])


def breath(seed, length, cutoff=0.06, rise=0.5):
    """Air: soft noise that swells (to rise of the way through) and fades."""
    sig = noise(seed, n(length), cutoff)
    total = len(sig)
    out = []
    for i, v in enumerate(sig):
        t = i / float(total)
        a = (t / rise) if t < rise else (1 - t) / (1 - rise)
        out.append(v * max(0.0, a) ** 1.3 * 3.0)
    return out


def room(sig, wet=0.25, seconds=0.35):
    """A little stone room round it: a few soft echoes, darker each time."""
    out = list(sig) + [0.0] * n(seconds)
    for k, (d, g) in enumerate(((0.043, 0.5), (0.071, 0.38), (0.113, 0.27), (0.167, 0.18))):
        echo = lowpass(sig, 0.35 - k * 0.06)
        o = n(d)
        for i, v in enumerate(echo):
            out[i + o] += v * g * wet
    return out


def harp_run(freqs, step, length):
    """Notes one after another on a harp; anything above C6 an octave down (nothing shrill)."""
    parts = []
    for k, f in enumerate(freqs):
        while f > 1050:
            f /= 2.0
        parts.append((delay(harp(f, length, seed=k + 1), k * step), 0.45))
    return mix(*parts)


def seq(*notes):
    """Notes one after another: (signal, start seconds, gain)."""
    return mix(*[(delay(sig, at), g) for sig, at, g in notes])


# ---------------------------------------------------------------------------------------------------- the sounds
NOTE = {"D3": 146.83, "E3": 164.81, "F3": 174.61, "G3": 196.0, "A3": 220.0, "Bb3": 233.08, "B3": 246.94, "C4": 261.63,
        "D4": 293.66, "E4": 329.63, "F4": 349.23, "G4": 392.0, "A4": 440.0, "B4": 493.88, "C5": 523.25, "D5": 587.33,
        "E5": 659.25, "G5": 783.99}


def falling(a, b, seed, at=0.16):
    return room(seq((lute(NOTE[a], 0.45, seed), 0, 0.8), (lute(NOTE[b], 0.9, seed + 1, 0.993), at, 0.9)), 0.3)


def ribbit(seed=1, f0=None, pulses=(9, 6)):
    """A frog's call: two bursts of quick pulses (rib-bit), each pulse a little throaty ring, as real frogs call."""
    rng = random.Random(seed)
    f0 = f0 or rng.uniform(380, 520)
    out = []
    t0 = 0.0
    for b, count in enumerate(pulses):
        rate = rng.uniform(52, 64)
        for k in range(count):
            env_amp = math.sin(math.pi * (k + 0.5) / count)
            f = f0 * (1.0 + 0.08 * b) * (1 + rng.uniform(-0.02, 0.02))
            ring = mix((shaped(tone(f, n(0.03)), 0.0008, 140), 0.8), (shaped(tone(f * 2.6, n(0.02)), 0.0008, 200), 0.3),
                       (shaped(noise(seed * 31 + k, n(0.015), 0.4), 0.0005, 300), 0.25))
            out.append((delay(ring, t0 + k / rate), env_amp))
        t0 += count / rate + rng.uniform(0.05, 0.08)
    return lowpass(mix(*out), 0.5)


def sparkle(seed, f, count, length):
    """A few soft, low glints (bells) scattered through length seconds."""
    rng = random.Random(seed)
    return mix(*[(delay(bell(f * rng.choice((1.0, 1.25, 1.5)), 0.6, 6), rng.uniform(0, length)), 0.25)
                 for _ in range(count)])


SOUNDS = {
    # ----- no
    "Denied": (lambda: room(seq((knock(150, 0.2, 1), 0, 0.9), (knock(118, 0.26, 2), 0.15, 1.0)), 0.3), 0.55),
    "Denied_2": (lambda: room(seq((knock(140, 0.2, 3), 0, 0.9), (knock(110, 0.26, 4), 0.17, 1.0)), 0.3), 0.55),
    "Fail": (lambda: falling("E4", "C4", 11), 0.6),
    "Fail_2": (lambda: falling("D4", "Bb3", 13), 0.6),
    "Fail_3": (lambda: falling("G4", "E4", 15, 0.13), 0.6),
    "Empty": (lambda: room(seq((lute(NOTE["G3"], 0.3, 21), 0, 0.9),
                               (lute(NOTE["D3"], 1.0, 22, 0.99), 0.2, 1.0)), 0.3), 0.6),
    "Fizzle": (lambda: room(mix((breath(31, 0.7, 0.05, 0.15), 0.9), (shaped(crackle(32, 0.5, 0.004), 0.002, 7), 0.25),
                                (shaped(tone(220, n(0.6), glide=-0.45, shape="tri"), 0.01, 5), 0.18)), 0.2), 0.55),
    # ----- the interface
    "Click": (lambda: mix((shaped(noise(41, n(0.04), 0.18), 0.0008, 90), 0.8), (knock(420, 0.04, 42, 0.1), 0.3)), 0.3),
    "Chat": (lambda: room(seq((harp(NOTE["D4"], 0.5, 43), 0, 0.7), (harp(NOTE["A4"], 0.7, 44), 0.09, 0.6)), 0.2), 0.45),
    "Hail": (lambda: room(seq((lowpass(voice(190, 0.18, glide=0.15, vibrato=0.01, rough=0.02, seed=45), 0.2), 0, 0.9),
                              (lowpass(voice(230, 0.32, glide=-0.3, vibrato=0.02, rough=0.02, seed=46), 0.2), 0.16, 1.0)),
                          0.25), 0.6),
    # ----- doing well
    "Success": (lambda: room(seq((harp(NOTE["C4"], 0.5, 51), 0, 0.7), (harp(NOTE["G4"], 0.8, 52), 0.1, 0.7)), 0.2), 0.5),
    "Gather_Wood": (lambda: room(seq((knock(170, 0.2, 53), 0, 0.9), (knock(210, 0.14, 54), 0.11, 0.6),
                                     (harp(NOTE["G4"], 0.5, 55), 0.12, 0.25)), 0.2), 0.55),
    "Gather_Ore": (lambda: room(mix((knock(120, 0.22, 56, 0.4), 0.9),
                                    *[(delay(knock(random.Random(57 + k).uniform(500, 900), 0.06, 58 + k, 0.5),
                                             0.05 + k * 0.045), 0.3) for k in range(5)],
                                    (delay(harp(NOTE["A4"], 0.5, 59), 0.14), 0.22)), 0.2), 0.55),
    "Gather_Fish": (lambda: room(mix((shaped(noise(61, n(0.3), 0.3), 0.003, 12), 0.6),
                                     (delay(knock(180, 0.1, 62, 0.35), 0.18), 0.6), (delay(knock(160, 0.1, 63, 0.35), 0.3), 0.45),
                                     (delay(harp(NOTE["E4"], 0.5, 64), 0.2), 0.25)), 0.2), 0.55),
    "Harvest": (lambda: room(mix((breath(65, 0.35, 0.35, 0.3), 0.35),
                                 (delay(harp(NOTE["E4"], 0.5, 66), 0.06), 0.55), (delay(harp(NOTE["A4"], 0.7, 67), 0.15), 0.5)),
                             0.2), 0.5),
    "Cooked": (lambda: room(mix((shaped(crackle(68, 0.6, 0.02), 0.01, 5), 0.4),
                                (delay(harp(NOTE["G4"], 0.5, 69), 0.1), 0.5), (delay(harp(NOTE["C5"], 0.6, 70), 0.2), 0.4)),
                            0.2), 0.5),
    "Crafted": (lambda: room(mix((knock(260, 0.12, 71, 0.3), 0.5), (delay(bell(392, 0.8, 5), 0.06), 0.3),
                                 (delay(harp(NOTE["C5"], 0.6, 72), 0.12), 0.45)), 0.25), 0.55),
    "Unlock": (lambda: room(seq((knock(620, 0.05, 73, 0.6), 0, 0.5), (shaped(noise(74, n(0.12), 0.2), 0.02, 18), 0.05, 0.4),
                                (knock(240, 0.15, 75, 0.35), 0.16, 0.9)), 0.3), 0.55),
    "Learn": (lambda: room(mix((breath(76, 0.9, 0.05, 0.4), 0.5),
                               *[(delay(harp(NOTE[nt], 0.8, 77 + k), k * 0.07), 0.45)
                                 for k, nt in enumerate(("C4", "E4", "G4", "C5", "E5"))]), 0.3), 0.6),
    # ----- magic
    "Rare_Shard": (lambda: room(mix((bell(523.25, 1.0, 3.5), 0.5), (delay(bell(659.25, 0.9, 4), 0.09), 0.4),
                                    (sparkle(81, 784, 4, 0.5), 1.0)), 0.35), 0.6),
    "Appear": (lambda: room(mix((breath(82, 0.6, 0.08, 0.7), 0.7), (delay(bell(392, 0.6, 5), 0.38), 0.35)), 0.3), 0.55),
    "Vanish": (lambda: room(mix((breath(83, 0.7, 0.08, 0.2), 0.7), (bell(330, 0.6, 6), 0.3)), 0.3), 0.55),
    "Swap": (lambda: room(mix((breath(84, 0.6, 0.06, 0.5), 0.6), (shaped(tone(196, n(0.6), glide=0.5, shape="tri"), 0.05, 4), 0.25),
                              (shaped(tone(392, n(0.6), glide=-0.33, shape="tri"), 0.05, 4), 0.2)), 0.3), 0.55),
    "SpellHeal": (lambda: room(mix(*[(delay(harp(NOTE[nt], 0.9, 85 + k), k * 0.09), 0.45)
                                     for k, nt in enumerate(("C4", "E4", "G4", "C5"))]), 0.3), 0.6),
    "LevelUp": (lambda: room(mix(*[(delay(harp(NOTE[nt], 1.2, 90 + k), k * 0.085), 0.42)
                                   for k, nt in enumerate(("G3", "C4", "E4", "G4", "C5", "E5"))],
                                 (delay(bell(261.63, 1.4, 2.0), 0.45), 0.35)), 0.35), 0.75),
    "Quest": (lambda: room(mix(*[(delay(lute(NOTE[nt], 1.0, 100 + k, 0.996), k * 0.13), 0.5)
                                 for k, nt in enumerate(("G3", "C4", "E4", "G4"))],
                               (delay(bell(196, 1.5, 1.8), 0.5), 0.3)), 0.35), 0.7),
    "Remnant_Rise": (lambda: room(mix((lowpass(voice(70, 0.9, glide=0.4, vibrato=0.04, rate=5, rough=0.08, seed=110,
                                                     shape="square"), 0.12), 1.0),
                                      (sparkle(111, 659, 5, 0.6), 0.8), (breath(112, 0.9, 0.04, 0.4), 0.4)), 0.3), 0.7),
    "Absorb": (lambda: room(mix((breath(140, 0.7, 0.05, 0.8), 0.6), (harp_run((330, 392, 523), 0.06, 0.6), 0.8)), 0.25), 0.55),
    "Bloom_Harvest": (lambda: room(mix((harp_run((659, 880, 1109, 1319), 0.07, 0.8), 0.9),
                                       (breath(141, 0.6, 0.12, 0.3), 0.3)), 0.3), 0.6),
    "Freeze": (lambda: room(mix((harp_run((784, 1047, 1319, 1568), 0.06, 0.9), 0.7), (breath(142, 0.9, 0.2, 0.3), 0.3),
                                (delay(knock(700, 0.06, 143, 0.6), 0.35), 0.6)), 0.3), 0.6),
    "Stone_Wake": (lambda: room(mix((shaped(tone(98, n(1.1), glide=0.5, shape="tri"), 0.3, 2.5), 0.5),
                                    (harp_run((440, 660, 880, 1320), 0.09, 1.0), 0.6), (breath(144, 0.9, 0.08, 0.5), 0.3)),
                                0.35), 0.65),
    "Enchant": (lambda: room(mix((breath(145, 0.7, 0.15, 0.2), 0.4), (harp_run((784, 988, 1175, 1568), 0.06, 0.9), 0.7),
                                 (delay(bell(392, 0.9, 3), 0.3), 0.3)), 0.3), 0.6),
    "Portal": (lambda: room(mix((harp_run((523, 784, 1047, 1568), 0.05, 0.8), 0.6), (breath(146, 0.8, 0.08, 0.5), 0.5),
                                (shaped(tone(110, n(0.7), glide=0.6, shape="tri"), 0.05, 4.0, 0.2), 0.4)), 0.35), 0.65),
    "Gate_Built": (lambda: room(mix((shaped(noise(147, n(1.2), 0.15), 0.1, 2.5), 0.6), (harp_run((392, 523, 659, 784), 0.12, 1.2), 0.6),
                                    (delay(bell(196, 1.4, 1.8), 0.5), 0.3)), 0.35), 0.7),
    "Anchor_Shatter": (lambda: room(mix((shaped(noise(148, n(0.25), 0.4), 0.001, 16), 0.8),
                                        (harp_run((3136, 2637, 2349, 1976, 1568, 1319), 0.07, 0.9), 0.6),
                                        (shaped(tone(65, n(1.0), glide=-0.4), 0.01, 3.0), 0.5)), 0.35), 0.75),
    # ----- stances and stealth (stances.py)
    "Stance_None": (lambda: room(breath(150, 0.4, 0.03, 0.3), 0.2), 0.35),
    "Stance_Fighting": (lambda: room(mix((breath(151, 0.3, 0.25, 0.6), 0.6), (delay(bell(330, 0.6, 7), 0.2), 0.3),
                                         (delay(knock(220, 0.08, 152, 0.4), 0.22), 0.4)), 0.25), 0.5),
    "Stance_Channelling": (lambda: room(mix((breath(153, 0.6, 0.06, 0.5), 0.6), (delay(harp_run((392, 523, 659), 0.08, 0.7), 0.15), 0.5)),
                                        0.3), 0.5),
    "Stance_Sneaking": (lambda: room(mix((breath(154, 0.35, 0.12, 0.4), 0.7), (delay(breath(155, 0.25, 0.1, 0.4), 0.18), 0.4)), 0.15),
                        0.35),
    "Spotted": (lambda: room(mix((lute(NOTE["E3"], 0.5, 156), 0.7), (lute(NOTE["F3"], 0.5, 157), 0.6),
                                 (knock(160, 0.15, 158, 0.4), 0.6)), 0.25), 0.6),
    "Sneak_Past": (lambda: room(mix((breath(159, 0.6, 0.04, 0.3), 0.6), (delay(harp(NOTE["D4"], 0.7, 160), 0.2), 0.35)), 0.25), 0.4),
    # ----- footsteps (the page: by the ground underfoot, softer sneaking)
    "Step_Grass": (lambda: shaped(noise(170, n(0.09), 0.12), 0.006, 30), 0.3),
    "Step_Grass_2": (lambda: shaped(noise(171, n(0.08), 0.1), 0.006, 32), 0.3),
    "Step_Stone": (lambda: mix((knock(260, 0.07, 172, 0.35), 0.6), (shaped(noise(173, n(0.04), 0.4), 0.001, 70), 0.3)), 0.3),
    "Step_Stone_2": (lambda: mix((knock(240, 0.07, 174, 0.35), 0.6), (shaped(noise(175, n(0.04), 0.4), 0.001, 70), 0.3)), 0.3),
    "Step_Wood": (lambda: knock(170, 0.1, 176, 0.25), 0.32),
    "Step_Wood_2": (lambda: knock(155, 0.1, 177, 0.25), 0.32),
    "Step_Sand": (lambda: shaped(crackle(178, 0.1, 0.03), 0.004, 25), 0.28),
    "Step_Snow": (lambda: mix((shaped(crackle(179, 0.14, 0.06), 0.01, 18), 0.6), (shaped(noise(180, n(0.12), 0.08), 0.01, 18), 0.5)), 0.3),
    "Step_Snow_2": (lambda: mix((shaped(crackle(181, 0.14, 0.06), 0.01, 18), 0.6), (shaped(noise(182, n(0.12), 0.08), 0.01, 18), 0.5)), 0.3),
    # ----- creatures and traps
    "Croak": (lambda: ribbit(121), 0.6),
    "Kill_Small": (lambda: lowpass(mix((voice(1150, 0.2, glide=-0.4, vibrato=0.06, rate=28, rough=0.05, seed=122,
                                              shape="sine"), 0.8),
                                       (delay(voice(950, 0.16, glide=-0.5, vibrato=0.05, rate=26, seed=123, shape="sine"), 0.08),
                                        0.5)), 0.35), 0.6),
    "Darts": (lambda: room(mix(*[(delay(shaped(noise(130 + k, n(0.09), 0.3), 0.003, 30), k * 0.05), 0.5) for k in range(3)],
                               (delay(knock(300, 0.08, 135, 0.3), 0.2), 0.5)), 0.2), 0.55),
}


def wav_bytes(sig, level):
    peak = max(1e-6, max(abs(s) for s in sig))
    gain = level / peak
    frames = b"".join(struct.pack("<h", int(max(-1, min(1, s * gain)) * 32767)) for s in sig)
    header = b"RIFF" + struct.pack("<I", 36 + len(frames)) + b"WAVE"
    header += b"fmt " + struct.pack("<IHHIIHH", 16, 1, 1, RATE, RATE * 2, 2, 16)
    header += b"data" + struct.pack("<I", len(frames))
    return header + frames


def make(name):
    fn, level = SOUNDS[name]
    return wav_bytes(fn(), level)


def main():
    written = 0
    for name in SOUNDS:
        blob = make(name)
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
