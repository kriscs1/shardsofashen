"""sounds\\Empty.wav: "duh-derr" - nothing in it. Two notes on a muted horn: a short one, then a longer one lower
down that sags at its end. Played by an empty chest (Display.Refusal's sound). Run it again to make it again.

  python -I "dev\\migrate\\build_empty_sound.py"
"""
import math
import sys
import os
import struct
import wave

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RATE = 22050


def note(freq, secs, sag=0.0, vibrato=0.0):
    """A brassy note: a handful of harmonics, a soft attack, a fall at the end (sag: how far its pitch droops)."""
    out = []
    n = int(RATE * secs)
    phase = 0.0
    for i in range(n):
        t = i / RATE
        f = freq * (1 - sag * max(0.0, (t / secs - 0.55)) / 0.45) * (1 + vibrato * math.sin(2 * math.pi * 6 * t))
        phase += 2 * math.pi * f / RATE
        v = sum(math.sin(phase * h) / h ** 1.3 for h in range(1, 8))
        env = min(1.0, t / 0.025) * min(1.0, (secs - t) / 0.08)
        out.append(v * env * 0.32)
    return out


def main():
    sys.exit("Superseded: %s is made by build_soundscape.py now (in the old world's voice)." % "Empty")


def old_main():
    gap = [0.0] * int(RATE * 0.05)
    samples = note(220.0, 0.22) + gap + note(165.0, 0.62, sag=0.12, vibrato=0.012)
    path = os.path.join(ROOT, "sounds", "Empty.wav")
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(b"".join(struct.pack("<h", int(max(-1, min(1, s)) * 30000)) for s in samples))
    print("Made sounds\\Empty.wav")


if __name__ == "__main__":  # (superseded: see main)
    main()
