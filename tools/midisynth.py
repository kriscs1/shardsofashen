"""A small General MIDI synthesizer, good enough for the game's tunes: browsers can't play MIDI, so the music is turned
into audio once (tools/export_web_assets.py). Each instrument family gets a waveform made of a few harmonics and an
envelope; channel 10 is drums (noise and thumps). Reads the files with the desktop game's own MIDI reader."""
import math
import os
import subprocess
import sys
import wave

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ashen.midi import Midi  # noqa: E402

RATE = 32000

# family (program // 8) -> (harmonic weights, attack s, decay s, sustain level, release s, vibrato)
FAMILIES = {
    0: ((1, .5, .25, .12, .06), .004, .9, .0, .25, 0),          # piano: struck, dies away
    1: ((1, .2, .4, .1), .002, .5, .0, .2, 0),                   # chromatic percussion (bells, celesta)
    2: ((1, .6, .45, .3, .2, .1), .03, .2, .8, .08, .004),       # organ
    3: ((1, .45, .3, .15, .08), .003, 1.2, .0, .2, 0),           # guitar: plucked
    4: ((1, .55, .2, .1), .01, .4, .5, .12, 0),                  # bass
    5: ((1, .5, .33, .25, .2, .16, .14), .09, .3, .85, .3, .006),  # strings: bowed (a sawtooth)
    6: ((1, .5, .33, .25, .2, .16), .07, .3, .8, .35, .004),     # ensemble, choir
    7: ((1, .7, .5, .35, .22), .03, .2, .8, .15, .005),          # brass
    8: ((1, .3, .5, .15, .3), .04, .2, .8, .15, .005),           # reed
    9: ((1, .12, .05, .02), .05, .2, .85, .2, .006),             # pipe (flute, recorder)
    10: ((1, 0, .33, 0, .2, 0, .14), .01, .2, .75, .15, .003),   # synth lead (square-ish)
    11: ((1, .4, .25, .15, .1), .25, .5, .8, .6, .004),          # synth pad
    12: ((1, .3, .2, .1), .01, .5, .4, .3, 0),
    13: ((1, .4, .2, .1), .003, .8, .0, .2, 0),                  # ethnic plucked (harp-like)
    14: ((1, .2, .3, .05), .002, .4, .0, .2, 0),                 # percussive
    15: ((1, .2), .05, .3, .5, .3, 0),
}
_wave_cache = {}


def family_wave(fam):
    """One cycle (4096 samples) of a family's waveform."""
    if fam not in _wave_cache:
        weights = FAMILIES.get(fam, FAMILIES[0])[0]
        t = np.linspace(0, 2 * np.pi, 4096, endpoint=False)
        w = sum(a * np.sin((k + 1) * t) for k, a in enumerate(weights))
        _wave_cache[fam] = (w / np.max(np.abs(w))).astype(np.float32)
    return _wave_cache[fam]


def envelope(n, attack, decay, sustain, release, held):
    """Attack, decay to sustain while held (held samples), then release."""
    env = np.empty(n, dtype=np.float32)
    a = max(1, int(attack * RATE))
    d = max(1, int(decay * RATE))
    i = np.arange(n, dtype=np.float32)
    env[:] = sustain
    env[:min(a, n)] = i[:min(a, n)] / a
    if a < n:
        dd = i[a:min(a + d, n)] - a
        if sustain > 0:
            env[a:min(a + d, n)] = 1 - (1 - sustain) * (dd / d)
        else:                                       # a struck or plucked note: dies away, exponentially
            env[a:n] = np.exp(-(i[a:n] - a) / max(1.0, d * 0.45))
    if held < n:
        level = env[held - 1] if held > 0 else 0
        r = np.arange(n - held, dtype=np.float32)
        env[held:] = np.minimum(env[held:], level * np.exp(-r / max(1.0, release * RATE * 0.3)))
    return env


def note_audio(fam, freq, velocity, seconds):
    attack, decay, sustain, release, vib = FAMILIES.get(fam, FAMILIES[0])[1:]
    held = int(seconds * RATE)
    n = held + int(release * RATE)
    if sustain == 0:
        n = min(n, int((attack + decay * 3) * RATE)) if held < (attack + decay * 3) * RATE else held + int(release * RATE)
    n = max(n, 64)
    t = np.arange(n, dtype=np.float32) / RATE
    phase = freq * t
    if vib:
        phase = phase + vib * freq * np.sin(2 * np.pi * 5.5 * t) / (2 * np.pi * 5.5) * np.minimum(1, t * 3)
    wav = family_wave(fam)
    out = wav[((phase % 1.0) * 4096).astype(np.int32) & 4095]
    if freq > 1200:                                 # high notes: softer upper harmonics
        out = out * 0.8
    return out * envelope(n, attack, decay, sustain, release, held) * (velocity / 127.0) ** 1.5


def drum_audio(note, velocity):
    rng = np.random.default_rng(note)
    v = (velocity / 127.0) ** 1.4
    if note in (35, 36):                            # kick: a falling thump
        n = int(0.25 * RATE)
        t = np.arange(n) / RATE
        f = 120 * np.exp(-t * 18) + 45
        return (np.sin(2 * np.pi * np.cumsum(f) / RATE) * np.exp(-t * 14) * v * 1.1).astype(np.float32)
    if note in (38, 40, 37, 39):                    # snare, clap
        n = int(0.18 * RATE)
        t = np.arange(n) / RATE
        noise = rng.uniform(-1, 1, n)
        tone = np.sin(2 * np.pi * 190 * t)
        return ((noise * 0.7 + tone * 0.4) * np.exp(-t * 22) * v * 0.7).astype(np.float32)
    if note in (42, 44, 46, 51, 53, 59):            # hats and rides: short bright noise
        n = int((0.3 if note in (46, 51, 59) else 0.06) * RATE)
        t = np.arange(n) / RATE
        noise = rng.uniform(-1, 1, n)
        noise = noise - np.concatenate(([0], noise[:-1]))       # (brighter)
        return (noise * np.exp(-t * (10 if note in (46, 51, 59) else 60)) * v * 0.25).astype(np.float32)
    if note in (49, 57, 52, 55):                    # crash
        n = int(1.0 * RATE)
        t = np.arange(n) / RATE
        noise = rng.uniform(-1, 1, n)
        noise = noise - np.concatenate(([0], noise[:-1]))
        return (noise * np.exp(-t * 3.5) * v * 0.22).astype(np.float32)
    n = int(0.3 * RATE)                             # toms and the rest: a pitched thump
    t = np.arange(n) / RATE
    f = 80 + (note - 41) * 12
    return (np.sin(2 * np.pi * f * t) * np.exp(-t * 10) * v * 0.6).astype(np.float32)


def render(path):
    """The MIDI file's audio: (stereo float32 array, seconds)."""
    m = Midi(path)
    events = []
    for tr in m.tracks:
        for tick, msg in tr:
            events.append((tick, msg))
    events.sort(key=lambda e: e[0])
    program = [0] * 16
    volume = [100] * 16
    pan = [64] * 16
    active = {}                                     # (channel, note) -> (start s, velocity, program)
    notes = []                                      # (start, end, channel, note, velocity, program, volume, pan)
    for tick, msg in events:
        s = msg[0]
        if s == 0xFF or s in (0xF0, 0xF7):
            continue
        ch = s & 0x0F
        kind = s & 0xF0
        at = m.ms_at(tick) / 1000.0
        if kind == 0xC0:
            program[ch] = msg[1]
        elif kind == 0xB0 and msg[1] == 7:
            volume[ch] = msg[2]
        elif kind == 0xB0 and msg[1] == 10:
            pan[ch] = msg[2]
        elif kind == 0x90 and msg[2] > 0:
            key = (ch, msg[1])
            if key in active:
                st, vel, prog = active.pop(key)
                notes.append((st, at, ch, msg[1], vel, prog, volume[ch], pan[ch]))
            active[key] = (at, msg[2], program[ch])
        elif kind == 0x80 or (kind == 0x90 and msg[2] == 0):
            key = (ch, msg[1])
            if key in active:
                st, vel, prog = active.pop(key)
                notes.append((st, at, ch, msg[1], vel, prog, volume[ch], pan[ch]))
    end = m.length_ms / 1000.0
    for (ch, note), (st, vel, prog) in active.items():
        notes.append((st, end, ch, note, vel, prog, volume[ch], pan[ch]))
    total = int((end + 2.0) * RATE)
    out = np.zeros((2, total), dtype=np.float32)
    for st, en, ch, note, vel, prog, vol, pn in notes:
        if ch == 9:
            a = drum_audio(note, vel)
        else:
            freq = 440.0 * 2 ** ((note - 69) / 12.0)
            a = note_audio(prog // 8, freq, vel, max(0.03, en - st))
        a = a * (vol / 127.0)
        i = int(st * RATE)
        j = min(total, i + len(a))
        if j <= i:
            continue
        p = (pn / 127.0) * math.pi / 2
        out[0, i:j] += a[:j - i] * math.cos(p) * 1.2
        out[1, i:j] += a[:j - i] * math.sin(p) * 1.2
    # a little room: a short echo, so it isn't so dry
    d = int(0.11 * RATE)
    echo = np.zeros_like(out)
    echo[:, d:] = out[:, :-d] * 0.18
    out += echo
    peak = float(np.max(np.abs(out))) or 1.0
    out *= 0.85 / peak
    last = np.nonzero(np.max(np.abs(out), axis=0) > 0.002)[0]
    if last.size:
        out = out[:, :last[-1] + int(0.3 * RATE)]
    return out, out.shape[1] / RATE


def write_wav(path, audio):
    pcm = (np.clip(audio.T, -1, 1) * 32767).astype("<i2")
    with wave.open(path, "wb") as f:
        f.setnchannels(2)
        f.setsampwidth(2)
        f.setframerate(RATE)
        f.writeframes(pcm.tobytes())


def to_ogg(wav_path, ogg_path, ffmpeg="ffmpeg"):
    """True if ffmpeg made the OGG."""
    try:
        r = subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-i", wav_path, "-c:a", "libvorbis", "-q:a", "4",
                            ogg_path], capture_output=True)
        return r.returncode == 0 and os.path.exists(ogg_path)
    except OSError:
        return False


if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    audio, secs = render(src)
    write_wav(dst, audio)
    print("%s: %.1f s" % (dst, secs))
