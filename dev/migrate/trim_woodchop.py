"""sounds\\WoodChop.wav held three chops (2.9 s): Play.Animation plays it on every beat of the axe (800 ms apart), so
the chops ran over each other and each swing seemed to sound twice. This keeps only the first chop (a short fade at
its end). A second run does nothing.

  python -I "dev\\migrate\\trim_woodchop.py"
"""
import array
import os
import wave

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PATH = os.path.join(ROOT, "sounds", "WoodChop.wav")
KEEP = 0.6          # seconds from the chop
FADE = 0.15


def main():
    with wave.open(PATH, "rb") as w:
        rate, ch, width, n = w.getframerate(), w.getnchannels(), w.getsampwidth(), w.getnframes()
        a = array.array("h", w.readframes(n))
    if n / float(rate) <= KEEP + 0.1:
        print("WoodChop.wav is one chop already")
        return
    mono = a[::ch]
    start = next(i for i, x in enumerate(mono) if abs(x) > 3000)          # (the first blow)
    start = max(0, start - int(rate * 0.01))
    cut = mono[start:start + int(rate * KEEP)]
    fade = int(rate * FADE)
    for i in range(fade):
        cut[len(cut) - fade + i] = int(cut[len(cut) - fade + i] * (1 - i / float(fade)))
    with wave.open(PATH, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(width)
        w.setframerate(rate)
        w.writeframes(cut.tobytes())
    print("WoodChop.wav: one chop (%.2f s)" % (len(cut) / float(rate)))


if __name__ == "__main__":
    main()
