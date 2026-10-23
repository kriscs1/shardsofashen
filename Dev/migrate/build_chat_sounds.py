"""The chat's sounds: Sounds\\Chat.wav (a bright two-note chime when another player says something) and
Sounds\\Whisper.wav (a softer, lower one when someone whispers to you). Makes them if they aren't there.

  python -I "Dev\\migrate\\build_chat_sounds.py"
"""
import math
import os
import struct
import wave

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RATE = 22050


def bell(freq, start, length, volume, n):
    """A bell-ish note: a sine with a little of its octave, a quick attack and a long fade."""
    out = [0.0] * n
    s0 = int(start * RATE)
    for i in range(int(length * RATE)):
        j = s0 + i
        if j >= n:
            break
        t = i / RATE
        env = min(1.0, t / 0.006) * math.exp(-t * 7.0)
        out[j] = volume * env * (math.sin(2 * math.pi * freq * t) + 0.3 * math.sin(4 * math.pi * freq * t))
    return out


def write(name, notes, seconds, breath=0.0):
    path = os.path.join(ROOT, "Sounds", name + ".wav")
    if os.path.exists(path):
        print("Sounds\\%s.wav is there already" % name)
        return
    n = int(seconds * RATE)
    mix = [0.0] * n
    for freq, start, length, volume in notes:
        for i, v in enumerate(bell(freq, start, length, volume, n)):
            mix[i] += v
    if breath:                                  # (a whisper: a little soft noise under it)
        seed = 12345
        for i in range(n):
            seed = (seed * 1103515245 + 12345) & 0x7fffffff
            t = i / RATE
            mix[i] += breath * ((seed / 0x7fffffff) - 0.5) * math.exp(-t * 9) * min(1, t / 0.02)
    peak = max(1e-6, max(abs(v) for v in mix))
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(b"".join(struct.pack("<h", int(v / peak * 0.7 * 32767)) for v in mix))
    print("Made Sounds\\%s.wav" % name)


def main():
    write("Chat", [(988, 0.0, 0.5, 1.0), (1319, 0.09, 0.6, 0.9)], 0.7)          # B5, E6: "ding-ding"
    write("Whisper", [(659, 0.0, 0.5, 0.8), (523, 0.12, 0.6, 0.6)], 0.75, 0.25)   # E5, C5, falling, with breath


if __name__ == "__main__":
    main()
