"""sounds\\Thunder.wav: thunder, made from noise. A sharp crack (bright noise, quickly gone), then a deep rumble (noise
filtered down to the low end) that rolls - swelling and dying in waves - for a few seconds, and fades.

  python -I "dev\\migrate\\build_thunder.py"          (it overwrites Thunder.wav)
"""
import os
import wave

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RATE = 22050
SECONDS = 5.5


def lowpass(x, cutoff):
    """A one-pole low-pass, run twice (a gentle slope): keeps what's below cutoff Hz."""
    a = np.exp(-2 * np.pi * cutoff / RATE)
    for _ in range(2):
        y = np.empty_like(x)
        acc = 0.0
        for i, v in enumerate(x):
            acc = (1 - a) * v + a * acc
            y[i] = acc
        x = y
    return x


def main():
    rng = np.random.default_rng(7)
    n = int(SECONDS * RATE)
    t = np.arange(n) / RATE
    # the crack: bright noise, there and gone in a fifth of a second, a little after the start
    crack = rng.standard_normal(n) - lowpass(rng.standard_normal(n), 900)
    crack *= np.exp(-np.maximum(0, t - 0.05) * 18) * (t > 0.05)
    # the rumble: deep noise rolling in waves (each a swell that dies away), the whole thing fading
    rumble = lowpass(rng.standard_normal(n), 140)
    rumble += 0.5 * lowpass(rng.standard_normal(n), 60)
    rolls = np.zeros(n)
    for start, size, length in ((0.08, 1.0, 1.6), (0.7, 0.8, 1.4), (1.5, 0.65, 1.6), (2.4, 0.45, 1.8),
                                (3.3, 0.3, 1.8)):
        k = np.clip((t - start) / 0.12, 0, 1) * np.exp(-np.maximum(0, t - start) / (length / 2.5))
        rolls += size * k
    rumble *= rolls * np.exp(-t / 3.2)
    mix = 0.55 * crack / (np.abs(crack).max() or 1) + rumble / (np.abs(rumble).max() or 1)
    mix *= np.clip((SECONDS - t) / 0.6, 0, 1)                  # (no click at the end)
    mix = np.tanh(1.6 * mix)                                    # (a little warmth, and no clipping)
    mix = (mix / np.abs(mix).max() * 0.9 * 32767).astype("<i2")
    path = os.path.join(ROOT, "sounds", "Thunder.wav")
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(mix.tobytes())
    print("Made sounds\\Thunder.wav (%.1f s)" % SECONDS)


if __name__ == "__main__":
    main()
