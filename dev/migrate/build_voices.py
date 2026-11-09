"""People's voices: sounds\\Voice_<Kind>.wav, _2, _3 ..., a murmured syllable each, played by the browser as a
speaker's words appear in a conversation (web/js/voice.js), at the speaker's own pitch.

Real people mumbling nonsense, not words: CC0 recordings from freesound.org (SOURCES; in CREDITS.md), cut here into
syllables (at the dips between them), their rumble taken off, made as loud as each other and faded in and out. The
old, the ghostly and the beasts are made from them: a little slower and lower with a tremble, an echo, a growl.
(A voice built up from tones, this builder's first way, sounded like a machine.)

The recordings are fetched the first time (the previews: ffmpeg makes them WAVs) and kept in dev\\Voices (not in git).

Also gives each speaking NPC in data\\Entities.ini its Voice= (one of KINDS), unless it has one already: the owner's
choice stands. A notice, a sign or a letter has none, and is silent.

  python -I "dev\\migrate\\build_voices.py"

Safe to run again: the same cuts, made the same way, and only missing Voice= lines are added.
"""
import os
import re
import shutil
import subprocess
import urllib.request
import wave

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CACHE = os.path.join(ROOT, "dev", "Voices")
RATE = 22050

# the recordings (all CC0): freesound id -> its preview, and who made it
SOURCES = {
    165539: ("https://cdn.freesound.org/previews/165/165539_1038806-hq.mp3", "unfa", '15 seconds of "blah blah blah"'),
    536967: ("https://cdn.freesound.org/previews/536/536967_456862-hq.mp3", "dynamique", "Indistinct deep male mumble"),
    800349: ("https://cdn.freesound.org/previews/800/800349_17223158-hq.mp3", "cloyen", "Female Gibberish"),
    377743: ("https://cdn.freesound.org/previews/377/377743_6769439-hq.mp3", "BlueSiren", "indistinctwhispering.wav"),
    389642: ("https://cdn.freesound.org/previews/389/389642_4103633-hq.mp3", "SilentStrikeZ", "Human_Male_Crazy Mumbles_1.wav"),
    677407: ("https://cdn.freesound.org/previews/677/677407_12064174-hq.mp3", "SnowFightStudios",
             "Monster or Creature Mutterings and Gibberish"),
}

# kind: which recording, how many takes, its speed (below 1: slower and lower), a tremble (an old voice's: depth),
# an echo (a ghost's), a rattle (a frog's: times a second)
KINDS = {
    "Man":       dict(src=165539, takes=8),
    "Deep":      dict(src=536967, takes=8),
    "Woman":     dict(src=800349, takes=8),
    "Old_Man":   dict(src=165539, takes=8, speed=0.9, tremble=0.18, skip=1),
    "Old_Woman": dict(src=800349, takes=8, speed=0.9, tremble=0.2, skip=1),
    "Gruff":     dict(src=389642, takes=8, speed=0.92),
    "Ghost":     dict(src=377743, takes=8, echo=0.4),
    "Croak":     dict(src=677407, takes=6, speed=0.72, rattle=22),
    "Beast":     dict(src=677407, takes=8, speed=0.82, skip=1),
}

# who speaks how (Entities.ini sections); anyone who speaks and isn't here gets none until it's given one
VOICES = {
    "Man": "Villager Trader Greengrocer Fishmonger Carter Clerk Cobbler Hotelier Beekeeper Courier Constable Druid "
           "Ranger Chancellor Mayor Merchant Man Barkeep Baker Doctor Edwin Banker Shopkeeper Farmer Shepherd Scholar "
           "Sheriff Quartermaster Jester Travelling_Salesman Night_Smuggler Ashen_Acolyte Penitent Collier "
           "Mending_Wayfarer Ferryman Bert Pip",
    "Deep": "Guard Port_Guard Guard_Captain Royal_Guard Captain Butcher Armourer Frank Dwarf Forgemaster Sea_Captain "
            "King_Rupert King_Tyron",
    "Woman": "Woman Settler Painter Mourner Barmaid Blacksmith Herbalist Maren Milkmaid Nurse Tailor Scout Warden "
             "Wyrmsmith Ice_Fisher Mending_Sister Mending_Cantor Duchess",
    "Old_Man": "Beggar Elder Eldest_of_the_Mending Fisherman Gravekeeper Hermit Manor_Steward Miner Tobias Wizard "
               "Steward Speaker Archivist",
    "Old_Woman": "Old_Woman Beachcomber Marsh_Witch Witch Stone_Ringer",
    "Gruff": "Hob Bandit Talking_Scarecrow",
    "Ghost": "Delver_Ghost Ghost_Warden Orrin_Ghost Toll_Keeper Valour_Guardian Wandering_Echo Ysolde Singing_Remnant "
             "The_Voice Great_Shard Echo_Pool",
    "Croak": "Frog_King",
    "Beast": "Galaith_Dragon",
}


def recording(sid):
    """The recording as mono 22050 Hz, fetched and kept the first time."""
    wav = os.path.join(CACHE, "%d.wav" % sid)
    if not os.path.exists(wav):
        os.makedirs(CACHE, exist_ok=True)
        mp3 = os.path.join(CACHE, "%d.mp3" % sid)
        if not os.path.exists(mp3):
            req = urllib.request.Request(SOURCES[sid][0], headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=60) as r, open(mp3, "wb") as f:
                f.write(r.read())
        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            raise SystemExit("ffmpeg isn't on the PATH: it's needed once, to make %s a WAV" % mp3)
        subprocess.run([ffmpeg, "-loglevel", "error", "-y", "-i", mp3, "-ac", "1", "-ar", str(RATE), wav], check=True)
    with wave.open(wav, "rb") as w:
        return np.frombuffer(w.readframes(w.getnframes()), "<i2").astype(float) / 32768


def clarity(s):
    """How much a piece is a voice (its pitch repeating), 0..1, rather than breath or a knock."""
    s = s[:1500] - s[:1500].mean()
    if np.sum(s * s) < 1e-6:
        return 0.0
    ac = np.correlate(s, s, "full")[len(s) - 1:]
    lo, hi = RATE // 450, min(len(ac) - 1, RATE // 60)
    return float(np.max(ac[lo:hi]) / ac[0]) if hi > lo else 0.0


def syllables(x, shortest=0.09, longest=0.38):
    """Where the syllables are: (start, end) in samples. Loud stretches, split where the sound dips between two."""
    hop = 110
    n = len(x) // hop
    e = np.sqrt(np.mean(x[:n * hop].reshape(n, hop) ** 2, axis=1))
    e = np.convolve(e, np.ones(4) / 4, "same")                    # (20 ms smoothing)
    floor, peak = np.percentile(e, 10), np.percentile(e, 98)
    on = e > floor + (peak - floor) * 0.18
    runs, i = [], 0
    while i < n:
        if on[i]:
            j = i
            while j < n and on[j]:
                j += 1
            if runs and i - runs[-1][1] < int(0.025 * RATE / hop):  # (a gap under 25 ms is inside a syllable)
                runs[-1][1] = j
            else:
                runs.append([i, j])
            i = j
        else:
            i += 1
    out = []
    w = int(0.06 * RATE / hop)
    for a, b in runs:
        cuts = [a]
        for k in range(a + 4, b - 4):
            if e[k] <= e[k - 1] and e[k] <= e[k + 1]:
                if e[k] < 0.55 * min(e[max(a, k - w):k].max(), e[k + 1:min(b, k + w)].max()) and \
                        (k - cuts[-1]) * hop / RATE >= shortest:
                    cuts.append(k)
        cuts.append(b)
        out += [(s * hop, t * hop) for s, t in zip(cuts, cuts[1:]) if shortest <= (t - s) * hop / RATE <= longest]
    return out


def pick(x, takes, skip=0):
    """The clearest, loudest syllables, spread through the recording (every other one from skip, if there are
    enough: a voice made from another's takes its own)."""
    found = [(s, t) for s, t in syllables(x) if clarity(x[s:t]) > 0.5]
    found.sort(key=lambda st: -np.sqrt(np.mean(x[st[0]:st[1]] ** 2)) * clarity(x[st[0]:st[1]]))
    best = found[:takes * 2]
    best.sort()
    chosen = best[skip::2] if len(best) >= takes * 2 else best
    return chosen[:takes]


def highpass(y, hz=90):
    a = np.exp(-2 * np.pi * hz / RATE)
    out = np.empty_like(y)
    prev_x = prev_y = 0.0
    for i, v in enumerate(y):
        prev_y = a * (prev_y + v - prev_x)
        prev_x = v
        out[i] = prev_y
    return out


def make(x, span, k):
    pad = int(0.015 * RATE)
    y = x[max(0, span[0] - pad):min(len(x), span[1] + pad)].copy()
    speed = k.get("speed", 1.0)
    if speed != 1.0:                                              # (slower and lower, as a tape would)
        y = np.interp(np.arange(0, len(y) - 1, speed), np.arange(len(y)), y)
    y = highpass(y)
    t = np.arange(len(y)) / RATE
    if k.get("tremble"):
        y *= 1 - k["tremble"] * (0.5 + 0.5 * np.sin(2 * np.pi * 6.5 * t))
    if k.get("rattle"):
        y *= 0.45 + 0.55 * (0.5 + 0.5 * np.sin(2 * np.pi * k["rattle"] * t))
    if k.get("echo"):
        tail = int(0.3 * RATE)
        y = np.concatenate([y, np.zeros(tail)])
        for d, g in ((0.083, k["echo"]), (0.131, k["echo"] * 0.6), (0.197, k["echo"] * 0.35)):
            n = int(d * RATE)
            y[n:] += y[:-n] * g
    fade_in, fade_out = int(0.006 * RATE), int(0.03 * RATE)
    y[:fade_in] *= np.linspace(0, 1, fade_in)
    y[-fade_out:] *= np.linspace(1, 0, fade_out)
    rms = np.sqrt(np.mean(y ** 2))                                # (all as loud as each other)
    y *= 0.12 / max(rms, 1e-6)
    peak = np.max(np.abs(y))
    if peak > 0.9:
        y *= 0.9 / peak
    return (y * 32767).astype("<i2").tobytes()


def write(name, data):
    path = os.path.join(ROOT, "sounds", name + ".wav")
    if os.path.exists(path):
        with wave.open(path, "rb") as w:
            if w.readframes(w.getnframes()) == data:
                return False
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(data)
    return True


def give_voices():
    """Voice= for each speaker in VOICES that has a section and no Voice= yet (written cp1252, CRLF, in place)."""
    path = os.path.join(ROOT, "data", "Entities.ini")
    with open(path, "rb") as f:
        lines = f.read().decode("cp1252").split("\r\n")
    who = {name: kind for kind, names in VOICES.items() for name in names.split()}
    sections = {}
    sec = None
    for i, ln in enumerate(lines):
        m = re.match(r"\[(.+)\]\s*$", ln)
        if m:
            sec = m.group(1)
            sections[sec] = [i, i, False]
        elif sec:
            if ln.strip():
                sections[sec][1] = i
            if ln.lower().startswith("voice="):
                sections[sec][2] = True
    added = []
    for name, (first, last, has) in sorted(sections.items(), key=lambda kv: -kv[1][1]):   # (from the end up)
        if name in who and not has:
            lines.insert(last + 1, "Voice=" + who[name])
            added.append(name)
    if added:
        with open(path, "wb") as f:
            f.write("\r\n".join(lines).encode("cp1252"))
    missing = sorted(n for n in who if n not in sections)
    return added, missing


def take_name(kind, n):
    return "Voice_" + kind + ("" if n == 1 else "_%d" % n)


def main():
    made = total = 0
    for kind, k in KINDS.items():
        x = recording(k["src"])
        spans = pick(x, k["takes"], k.get("skip", 0))
        for n, span in enumerate(spans, 1):
            made += write(take_name(kind, n), make(x, span, k))
        total += len(spans)
        n = len(spans) + 1                                        # (fewer takes than before: the rest go)
        while os.path.exists(os.path.join(ROOT, "sounds", take_name(kind, n) + ".wav")):
            os.remove(os.path.join(ROOT, "sounds", take_name(kind, n) + ".wav"))
            n += 1
        if len(spans) < k["takes"]:
            print("(%s: only %d syllables clear enough in %d)" % (kind, len(spans), k["src"]))
    print("Voices: %d of %d sounds made or redrawn" % (made, total))
    added, missing = give_voices()
    print("Voice= given to %d: %s" % (len(added), ", ".join(sorted(added)) or "-"))
    if missing:
        print("(no section for %s: left be)" % ", ".join(missing))


if __name__ == "__main__":
    main()
