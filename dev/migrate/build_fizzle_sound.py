"""sounds\\Fizzle.wav: a spell that fails - a hiss that sputters and gutters out, crackling, with a thin whine of
magic sinking away under it. Played when a spell slips from your grasp. Run it again to make it again.

  python -I "dev\\migrate\\build_fizzle_sound.py"
"""
import math
import sys
import os
import random
import struct
import wave

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RATE = 22050


def main():
    sys.exit("Superseded: %s is made by build_soundscape.py now (in the old world's voice)." % "Fizzle")


def old_main():
    rng = random.Random(7)
    secs = 0.75
    out, low, phase, crackle = [], 0.0, 0.0, 0.0
    for i in range(int(RATE * secs)):
        t = i / RATE
        u = t / secs
        n = rng.uniform(-1, 1)
        low += (n - low) * (0.6 - 0.45 * u)                         # (the hiss: duller as it dies)
        sputter = 0.35 + 0.65 * (0.5 + 0.5 * math.sin(2 * math.pi * (18 + 10 * rng.random()) * t)) ** 3
        if rng.random() < 0.004 * (1 - u):                          # (crackles, fewer as it goes)
            crackle = rng.choice((-1, 1)) * rng.uniform(0.5, 1.0)
        crackle *= 0.86
        f = 900 * (1 - 0.75 * u)                                    # (the magic: a whine sinking away)
        phase += 2 * math.pi * f / RATE
        whine = 0.18 * math.sin(phase) * (1 - u)
        env = min(1.0, t / 0.01) * (1 - u) ** 1.6
        out.append((low * 0.55 * sputter + crackle * 0.6 + whine) * env)
    path = os.path.join(ROOT, "sounds", "Fizzle.wav")
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(b"".join(struct.pack("<h", int(max(-1, min(1, s)) * 30000)) for s in out))
    print("Made sounds\\Fizzle.wav")


if __name__ == "__main__":  # (superseded: see main)
    main()
