"""sounds\\Denied.wav: the sound of a no (a locked door, too far away, not skilled enough), like a computer's alert
rather than an instrument - two clean, glassy electronic tones falling a fourth (G5, D5), soft at the start, with a
short room-like tail. Run it again to make it again.

  python -I "dev\\migrate\\build_denied_sound.py"
"""
import math
import sys
import os
import struct
import wave

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RATE = 44100


def tone(freq, start, length, volume, n, out):
    """A glassy tone: two sines a breath apart (a slow shimmer), a little of the octave and the twelfth, a soft
    attack and a quick, smooth fade."""
    s0 = int(start * RATE)
    for i in range(int(length * RATE)):
        j = s0 + i
        if j >= n:
            break
        t = i / RATE
        env = (1 - math.exp(-t / 0.008)) * math.exp(-t * 9.0)
        v = (math.sin(2 * math.pi * freq * t) + math.sin(2 * math.pi * (freq + 2.5) * t)) * 0.5
        v += 0.18 * math.sin(4 * math.pi * freq * t) * math.exp(-t * 14)
        v += 0.06 * math.sin(6 * math.pi * freq * t) * math.exp(-t * 20)
        out[j] += volume * env * v


def room(dry):
    """A short tail: a few soft echoes, each duller and quieter, as a small room gives back."""
    out = list(dry)
    for delay, gain in ((0.023, 0.22), (0.041, 0.16), (0.067, 0.11), (0.097, 0.07)):
        d = int(delay * RATE)
        low = 0.0
        for i in range(d, len(out)):
            low += (dry[i - d] - low) * 0.35                     # (duller: its highs taken off)
            out[i] += gain * low
    return out


def main():
    sys.exit("Superseded: %s is made by build_soundscape.py now (in the old world's voice)." % "Denied")


def old_main():
    seconds = 0.62
    n = int(seconds * RATE)
    dry = [0.0] * n
    tone(784.0, 0.0, 0.30, 0.42, n, dry)                         # G5
    tone(587.3, 0.115, 0.45, 0.46, n, dry)                       # D5
    out = room(dry)
    peak = max(abs(v) for v in out) or 1
    k = 0.8 / peak
    fade = int(0.04 * RATE)
    for i in range(fade):                                        # (no click at the end)
        out[n - 1 - i] *= i / fade
    path = os.path.join(ROOT, "sounds", "Denied.wav")
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(b"".join(struct.pack("<h", int(max(-1, min(1, v * k)) * 32000)) for v in out))
    print("Made sounds\\Denied.wav")


if __name__ == "__main__":  # (superseded: see main)
    main()
