"""sounds\\Fail.wav: an attempt that comes to nothing in the world (the axe gets no logs, the fish slips the hook, the
logs won't catch) - two soft notes on a lute, falling (E4, then a sighing C4), plucked strings with a wooden body:
the old world's "oh well", not a computer's no (that's Denied). Run it again to make it again.

  python -I "dev\\migrate\\build_fail_sound.py"
"""
import math
import sys
import os
import random
import struct
import wave

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RATE = 44100


def pluck(freq, seconds, rng, damp=0.996, bright=0.5):
    """A plucked string (Karplus-Strong): a burst of noise in a delay line the length of the string's wave,
    averaged on each pass, so it rings at the note and mellows as it dies, as gut strings do."""
    period = int(RATE / freq)
    buf = [rng.uniform(-1, 1) for _ in range(period)]
    soft = 0.0
    for i in range(period):                            # (plucked with a finger, not a pick: the highs softened)
        soft += (buf[i] - soft) * bright
        buf[i] = soft
    out = []
    for i in range(int(seconds * RATE)):
        j = i % period
        nxt = buf[(j + 1) % period]
        v = buf[j]
        buf[j] = damp * 0.5 * (v + nxt)
        out.append(v)
    return out


def body(samples):
    """The lute's wooden body: a low hollow resonance under the string, and the very top taken off."""
    out, lo, res, vel = [], 0.0, 0.0, 0.0
    w = 2 * math.pi * 190 / RATE                       # (a body resonance near 190 Hz)
    for v in samples:
        vel += (v - res) * w * w * 0.9 - vel * 0.02
        res += vel
        lo += (v - lo) * 0.45
        out.append(lo * 0.8 + res * 0.12)
    return out


def main():
    sys.exit("Superseded: %s is made by build_soundscape.py now (in the old world's voice)." % "Fail")


def old_main():
    rng = random.Random(11)
    seconds = 1.1
    n = int(seconds * RATE)
    mix = [0.0] * n
    for freq, start, vol, damp in ((329.6, 0.0, 0.8, 0.995), (261.6, 0.16, 1.0, 0.9965)):     # E4, then C4
        s0 = int(start * RATE)
        for i, v in enumerate(pluck(freq, seconds - start, rng, damp)):
            mix[s0 + i] += v * vol
    out = body(mix)
    peak = max(abs(v) for v in out) or 1
    fade = int(0.25 * RATE)
    for i in range(fade):                              # (dying away, no click)
        out[n - 1 - i] *= i / fade
    path = os.path.join(ROOT, "sounds", "Fail.wav")
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(b"".join(struct.pack("<h", int(max(-1, min(1, v / peak * 0.8)) * 32000)) for v in out))
    print("Made sounds\\Fail.wav")


if __name__ == "__main__":  # (superseded: see main)
    main()
