"""People's voices: sounds\\Voice_<Kind>.wav, _2 ... _6, a murmured syllable each, played by the browser as a
speaker's words appear in a conversation (web/js/voice.js), at the speaker's own pitch. Not words: breath through a
throat's shape (a buzz at the voice's pitch through three vowel resonances, Klatt's way), soft-started like m, n, l,
b, d or h, so a run of them sounds like someone talking just out of earshot.

Also gives each speaking NPC in data\\Entities.ini its Voice= (one of KINDS), unless it has one already: the owner's
choice stands. A notice, a sign or a letter has none, and is silent.

  python -I "dev\\migrate\\build_voices.py"

Safe to run again: the same sounds, drawn the same (seeded), and only missing Voice= lines are added.
"""
import math
import os
import random
import re
import struct
import wave

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RATE = 22050
TAKES = 6

# (a vowel's first three resonances, for a man's throat: a, e, i, o, u, and the "uh" between)
VOWELS = {"a": (730, 1090, 2440), "e": (530, 1840, 2480), "i": (400, 1900, 2550), "o": (570, 840, 2410),
          "u": (440, 1020, 2240), "@": (500, 1400, 2450)}
# (how each take starts, and what it says: every voice the same six, so they differ only by throat)
SYLLABLES = [("m", "a"), ("h", "e"), ("n", "o"), ("l", "@"), ("b", "u"), ("d", "i")]

# kind: pitch (Hz), throat (resonances times), breath (0 none, 1 a whisper), roughness, wobble (an old voice's
# tremble), length (s), echo (a ghost's), a low lift (the beasts' growl under it)
KINDS = {
    "Man":       dict(f0=118, throat=1.00, breath=0.10, rough=0.02, wobble=0.0, length=0.13),
    "Deep":      dict(f0=88, throat=0.92, breath=0.08, rough=0.05, wobble=0.0, length=0.14),
    "Woman":     dict(f0=205, throat=1.16, breath=0.16, rough=0.01, wobble=0.0, length=0.12),
    "Old_Man":   dict(f0=108, throat=0.98, breath=0.30, rough=0.08, wobble=0.05, length=0.15),
    "Old_Woman": dict(f0=185, throat=1.10, breath=0.32, rough=0.06, wobble=0.06, length=0.14),
    "Gruff":     dict(f0=95, throat=1.05, breath=0.18, rough=0.30, wobble=0.0, length=0.12),
    "Ghost":     dict(f0=140, throat=1.04, breath=0.92, rough=0.0, wobble=0.03, length=0.22, echo=0.45),
    "Croak":     dict(f0=52, throat=0.72, breath=0.10, rough=0.45, wobble=0.0, length=0.16, pulse=9.0),
    "Beast":     dict(f0=48, throat=0.62, breath=0.35, rough=0.35, wobble=0.0, length=0.26, growl=0.5),
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


def resonator(freq, bw):
    """A two-pole resonance (Klatt): its three coefficients."""
    c = -math.exp(-2 * math.pi * bw / RATE)
    b = 2 * math.exp(-math.pi * bw / RATE) * math.cos(2 * math.pi * freq / RATE)
    return 1 - b - c, b, c


def glottal(phase):
    """One push of air through the throat (Rosenberg's pulse), phase 0..1."""
    if phase < 0.42:
        return 0.5 * (1 - math.cos(math.pi * phase / 0.42))
    if phase < 0.62:
        return math.cos(math.pi * (phase - 0.42) / 0.4)
    return 0.0


def syllable(kind, take):
    v = KINDS[kind]
    rnd = random.Random("%s/%d" % (kind, take))            # (the same every run)
    onset, vowel = SYLLABLES[take]
    length = v["length"] * rnd.uniform(0.9, 1.15)
    lead = 0.04 if onset in "mnl" else 0.025               # (the consonant before the vowel)
    tail = 0.06 + v.get("echo", 0) * 0.5
    n = int((lead + length + tail) * RATE)
    target = [f * v["throat"] for f in VOWELS[vowel]]
    # (a nasal or an l starts closed - low first resonance, the second near 1200 - and opens into the vowel)
    start = [260 * v["throat"], 1200 * v["throat"], target[2]] if onset in "mnlbd" else list(target)
    contour = rnd.choice([(1.04, 0.95), (0.98, 1.03), (1.02, 0.97), (1.0, 0.96)])   # (falling, rising...)
    out = [0.0] * n
    y = [[0.0, 0.0] for _ in range(3)]
    coefs = None
    phase = 0.0
    prev = 0.0
    jit = 1.0
    seed = rnd.random()
    for i in range(n):
        t = i / RATE
        if i % 32 == 0:                                    # (the throat changes shape a little at a time)
            k = min(1.0, max(0.0, (t - lead * 0.4) / (lead + 0.035)))
            k = k * k * (3 - 2 * k)
            fs = [s + (g - s) * k for s, g in zip(start, target)]
            coefs = [resonator(fs[0], 70), resonator(fs[1], 100), resonator(fs[2], 160)]
        # loudness: the consonant's soft start, the vowel, its fall
        if t < lead:
            amp = (0.25 if onset in "mnl" else 0.05) * (t / lead)
        elif t < lead + 0.02:
            amp = 0.25 + 0.75 * (t - lead) / 0.02 if onset in "mnl" else 0.05 + 0.95 * (t - lead) / 0.02
        else:
            amp = math.exp(-max(0.0, t - lead - length * 0.55) * 22)
        if "growl" in v:                                   # (a dragon: the voice shakes, low in its chest)
            amp *= 1 - v["growl"] * (0.5 + 0.5 * math.sin(2 * math.pi * 23 * t + 6 * seed))
        if "pulse" in v:                                   # (a frog: the croak's rattle)
            amp *= 0.35 + 0.65 * (0.5 + 0.5 * math.sin(2 * math.pi * v["pulse"] * t))
        u = t / (lead + length)
        f0 = v["f0"] * (contour[0] + (contour[1] - contour[0]) * u) * (1 + v["wobble"] * math.sin(2 * math.pi * 6.5 * t))
        phase += f0 * jit / RATE
        if phase >= 1.0:
            phase -= 1.0
            jit = 1 + rnd.uniform(-1, 1) * v["rough"] * 0.25            # (a rough voice: each push a little off)
        g = glottal(phase)
        if v["rough"] > 0.2 and int(t * f0) % 2:                         # (a growl: every other push weaker)
            g *= 1 - v["rough"]
        src = g - prev                                                    # (the mouth's opening: the change in the push)
        prev = g
        noise = rnd.uniform(-1, 1) * 0.35
        voiced = 1 - v["breath"]
        x = (src * voiced + noise * v["breath"] * (0.6 + 0.4 * g)) * amp
        if onset == "h" and t < lead + 0.015:                             # (h: breath alone first)
            x = noise * 0.5 * min(1.0, t / 0.01)
        for j in range(3):
            a, b, c = coefs[j]
            s = a * x + b * y[j][0] + c * y[j][1]
            y[j][1] = y[j][0]
            y[j][0] = s
            x = s
        out[i] = x
    # (warm, never shrill: a gentle low-pass, then a ghost's echo)
    lp, acc = 0.75, 0.0
    for i in range(n):
        acc += lp * (out[i] - acc)
        out[i] = acc
    if v.get("echo"):
        for d, g in ((int(0.071 * RATE), v["echo"]), (int(0.113 * RATE), v["echo"] * 0.6)):
            for i in range(d, n):
                out[i] += out[i - d] * g
    fade = int(0.01 * RATE)                                # (no click at either end)
    for i in range(min(fade, n)):
        out[i] *= i / fade
        out[n - 1 - i] *= i / fade
    return out


def write(name, samples):
    peak = max(1e-6, max(abs(s) for s in samples))
    data = b"".join(struct.pack("<h", int(s / peak * 0.6 * 32767)) for s in samples)
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


def main():
    made = 0
    for kind in KINDS:
        for take in range(TAKES):
            name = "Voice_" + kind + ("" if take == 0 else "_%d" % (take + 1))
            made += write(name, syllable(kind, take))
    print("Voices: %d of %d sounds made or redrawn" % (made, len(KINDS) * TAKES))
    added, missing = give_voices()
    print("Voice= given to %d: %s" % (len(added), ", ".join(sorted(added)) or "-"))
    if missing:
        print("(no section for %s: left be)" % ", ".join(missing))


if __name__ == "__main__":
    main()
