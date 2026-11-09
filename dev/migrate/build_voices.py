"""People's greetings, monsters' growls and the quest jingles, all cut from CC0 recordings (freesound.org; each is
in SOURCES and CREDITS.md):

  sounds\\Voice_<Kind>.wav, _2 ...   what someone says as you start talking to them ("Hello", "Well met", "How can
                                     I help?"): one of their kind's, at the speaker's own pitch (web/js/voice.js)
  sounds\\Growl_<Kind>.wav, _2 ...   a monster that's seen you and comes for you (npcs.py npc_growl)
  sounds\\Quest_Start.wav             a quest taken on (a harp's run up)
  sounds\\Quest_Done.wav              a quest finished (a harpsichord's flourish)

Real people's words, never made up from tones (that sounded like a machine) or mumbled (that sounded awful). The
deeper and older voices are the same recordings made lower (the pitch moved, the pace kept: stretch) with a tremble;
a ghost's echo; the beasts are a creature's mutterings slowed, with a rattle for a troll's or a frog's throat.

The recordings are fetched the first time (the previews: ffmpeg makes them WAVs) and kept in dev\\Voices (not in git).

Also gives each speaker in data\\Entities.ini its Voice= (one of GREETINGS) and each monster its Growl= (one of
GROWLS), unless it has one already: the owner's choice stands. A notice, a sign or a letter has no voice: it's silent.

  python -I "dev\\migrate\\build_voices.py"

Safe to run again: the same cuts, made the same way, and only missing Voice=/Growl= lines are added.
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

# the recordings (all CC0): freesound id -> its preview (cdn.freesound.org/previews/...), who made it, its title
SOURCES = {
    431176: ("431176_3082984", "envirOmaniac2", "Thirty-Eight Greetings."),
    351611: ("351611_6325950", "bectec", "Female greetings.wav"),
    429038: ("429038_6492957", "theuncertainman", "Greetings (NPC, British Male)"),
    429037: ("429037_6492957", "theuncertainman", "How can I help? (NPC, British Male)"),
    458074: ("458074_6492957", "theuncertainman", "What can I do for you? (NPC, British Male)"),
    501882: ("501882_7076647", "Nchamp13", "Welcome Traveler.mp3"),
    449481: ("449481_9288538", "12125065", "hello"),
    447392: ("447392_6253486", "florianreichelt", "man saying hello"),
    711358: ("711358_14604432", "sickfin", "Nervous Old Man or Middle-aged Man"),
    546058: ("546058_12187251", "FunnyVoices", "hello, can I help you - Australian female voice.wav"),
    546061: ("546061_12187251", "FunnyVoices", "good morning - Australian female voice.wav"),
    123346: ("123346_495253", "MatteusNova", "hello.wav"),
    213282: ("213282_1118942", "AderuMoro", "Hello-female friendly professional.wav"),
    50940: ("50940_71257", "qubodup", "Fearing Hello"),
    677407: ("677407_12064174", "SnowFightStudios", "Monster or Creature Mutterings and Gibberish"),
    669913: ("669913_12064174", "SnowFightStudios", "Creature Gibberish Language\\Dialogue - Monster\\Alien"),
    490831: ("490831_10350281", "PhonosUPF", "harp glissando"),
    521642: ("521642_7724198", "Fupicat", "WinHarpsichord.wav"),
}

# what each kind of speaker says: (recording, from s, to s) each, what it says in the comment; then how it's made:
# pitch (below 1: lower), pace (below 1: slower), a tremble (an old voice's), an echo (a ghost's), a rattle (times a
# second: a frog's throat)
MAN = 431176
GREETINGS = {
    "Man": dict(clips=[(MAN, 5.71, 6.06),          # Hello!
                       (MAN, 8.13, 8.67),          # How are you?
                       (MAN, 20.44, 21.02),        # Welcome!
                       (MAN, 21.91, 22.79),        # How may I help you?
                       (MAN, 23.54, 24.01),        # Hey there!
                       (MAN, 25.02, 25.80),        # Why hello there.
                       (MAN, 36.12, 36.71),        # It's a pleasure.
                       (MAN, 39.44, 40.14),        # Nice to meet you.
                       (MAN, 41.19, 41.92),        # How are you today?
                       (MAN, 42.83, 43.79)]),      # How are things with you?
    "Deep": dict(clips=[(429038, 0.15, 0.77),      # Greetings.
                        (429037, 0.16, 0.88),      # How can I help?
                        (458074, 0.31, 1.15),      # What can I do for you?
                        (501882, 0.22, 1.19),      # Welcome, traveller.
                        (449481, 0.11, 1.48)],     # Hello.
                 pitch=0.88),
    "Woman": dict(clips=[(351611, 0.26, 1.09),     # Hello!
                         (351611, 1.65, 2.24),     # Hello.
                         (351611, 2.59, 2.88),     # Hey!
                         (351611, 5.94, 6.56),     # Oh, hi!
                         (351611, 7.07, 7.58),     # Good morning.
                         (351611, 9.80, 10.55),    # Hey, how are you?
                         (351611, 18.68, 19.48)]), # Hey, how are you?
    "Old_Man": dict(clips=[(MAN, 0.77, 1.64),      # Well met.
                           (MAN, 2.43, 3.20),      # How do you do?
                           (MAN, 4.13, 4.95),      # Greetings!
                           (MAN, 17.02, 17.96),    # Salutations.
                           (MAN, 33.11, 34.02),    # Friend!
                           (711358, 1.08, 2.05)],  # Oh, hi.
                    pitch=0.84, pace=0.9, tremble=0.16),
    "Old_Woman": dict(clips=[(546058, 0.41, 2.03),  # Hello, can I help you?
                             (546058, 0.41, 0.92),  # Hello.
                             (546061, 0.29, 0.99),  # Good morning.
                             (123346, 0.37, 0.86),  # Hello.
                             (213282, 0.13, 0.62)],  # Hello!
                      pitch=0.88, pace=0.9, tremble=0.2),
    "Gruff": dict(clips=[(449481, 0.11, 1.48),      # Hello.
                         (447392, 1.05, 1.48),      # Hello.
                         (MAN, 23.54, 24.01),       # Hey there.
                         (MAN, 0.77, 1.64)],        # Well met.
                  pitch=0.78),
    "Ghost": dict(clips=[(50940, 5.82, 6.12),       # Hello?
                         (50940, 11.24, 11.71),     # Hello?
                         (50940, 12.54, 13.18),     # Hello...
                         (351611, 0.26, 1.09)],     # Hello...
                  pace=0.85, echo=0.45),
    # (the Frog King and the dragon don't say "hello": they mutter, as their monsters growl)
    "Croak": dict(clips=[(677407, a, b) for a, b in ((95.80, 97.07), (98.54, 99.37), (100.85, 102.15),
                                                     (104.54, 105.23), (110.60, 111.56))],
                  speed=0.72, rattle=22),
    "Beast": dict(clips=[(669913, a, b) for a, b in ((24.43, 25.23), (31.05, 32.35), (33.18, 34.78),
                                                     (40.12, 41.17))],
                  speed=0.8),
}

# a monster's growl as it comes for you: a creature's mutterings (its parts: a goblin's, a troll's, a wraith's)
GROWLS = {
    "Goblin": dict(clips=[(677407, a, b) for a, b in ((2.90, 3.51), (5.47, 6.20), (7.01, 7.88), (8.86, 9.47),
                                                      (10.39, 11.15), (12.13, 12.91))],
                   speed=1.1),
    "Troll": dict(clips=[(677407, a, b) for a, b in ((95.80, 97.07), (98.54, 99.37), (100.85, 102.15),
                                                     (106.14, 106.81), (107.74, 108.37), (112.38, 113.43),
                                                     (114.26, 115.42))],
                  speed=0.72, rattle=22),
    "Wraith": dict(clips=[(677407, a, b) for a, b in ((123.96, 125.10), (131.41, 132.15), (137.10, 137.83),
                                                      (138.70, 139.51), (141.83, 142.48), (143.43, 144.54))],
                   speed=0.8, echo=0.45),
    "Dragon": dict(clips=[(669913, a, b) for a, b in ((22.95, 23.52), (24.43, 25.23), (26.12, 26.75),
                                                      (31.05, 32.35), (40.12, 41.17), (45.93, 47.19))],
                   speed=0.75),
}

JINGLES = {
    "Quest_Start": (490831, 0.0, None),
    "Quest_Done": (521642, 0.0, None),
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

# which monsters growl how (people, animals and things of stone or glass have none)
GROWLERS = {
    "Goblin": "Goblin Hobgoblin Goblin_Archer Goblin_Shaman Cinder_Imp",
    "Troll": "Cave_Troll Bog_Troll Frost_Troll Deep_Troll Yeti Magma_Brute Spore_Shambler Mire_Horror Cave_Horror "
             "Fossil_Horror Mimic_Thing",
    "Wraith": "Shard_Wraith Chalk_Wraith Dust_Wraith Ice_Wraith Tunnel_Wraith Archmage_Shade Orrins_Shadow "
              "Drowned_Sailor Sun_Mummy Barrow_King Hollow_Warden Hollow_Marshal Drowned_Warden",
    "Dragon": "Dragon Drake Shard_Drake Rime_Drake Sand_Drake Slag_Wyrm Galaith_Dragon",
}


def preview_url(sid):
    key = SOURCES[sid][0]
    return "https://cdn.freesound.org/previews/%s/%s-hq.mp3" % (key.split("_")[0][:-3], key)


def recording(sid):
    """The recording as mono 22050 Hz, fetched and kept the first time."""
    wav = os.path.join(CACHE, "%d.wav" % sid)
    if not os.path.exists(wav):
        os.makedirs(CACHE, exist_ok=True)
        mp3 = os.path.join(CACHE, "%d.mp3" % sid)
        if not os.path.exists(mp3):
            req = urllib.request.Request(preview_url(sid), headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=60) as r, open(mp3, "wb") as f:
                f.write(r.read())
        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            raise SystemExit("ffmpeg isn't on the PATH: it's needed once, to make %s a WAV" % mp3)
        subprocess.run([ffmpeg, "-loglevel", "error", "-y", "-i", mp3, "-ac", "1", "-ar", str(RATE), wav], check=True)
    with wave.open(wav, "rb") as w:
        return np.frombuffer(w.readframes(w.getnframes()), "<i2").astype(float) / 32768


def resample(y, speed):
    """Faster and higher (speed above 1) or slower and lower, as a tape would."""
    return np.interp(np.arange(0, len(y) - 1, speed), np.arange(len(y)), y) if speed != 1.0 else y


def stretch(y, by, win=882, tol=220):
    """Longer (by above 1) at the same pitch: overlapping pieces, each nudged to match the last (WSOLA)."""
    if abs(by - 1.0) < 1e-3 or len(y) < win * 2:
        return y
    hop = win // 2
    w = np.hanning(win + 1)[:win]
    n_out = int(len(y) * by)
    x = np.concatenate([np.zeros(tol), y, np.zeros(win + tol * 2)])
    out = np.zeros(n_out + win)
    norm = np.zeros(n_out + win)
    prev = tol
    for k in range(0, n_out, hop):
        want = tol + int(k / by)
        if k == 0:
            pos = want
        else:
            target = x[prev + hop:prev + hop + win]                  # (what would come next, left as it was)
            lo, hi = max(0, want - tol), min(len(x) - win, want + tol)
            best, pos = -1e18, want
            for p in range(lo, hi, 4):
                c = float(np.dot(x[p:p + win], target))
                if c > best:
                    best, pos = c, p
        out[k:k + win] += x[pos:pos + win] * w
        norm[k:k + win] += w
        prev = pos
    return out[:n_out] / np.maximum(norm[:n_out], 1e-3)


def highpass(y, hz=80):
    a = np.exp(-2 * np.pi * hz / RATE)
    out = np.empty_like(y)
    px = py = 0.0
    for i, v in enumerate(y):
        py = a * (py + v - px)
        px = v
        out[i] = py
    return out


def lowpass(y, hz):
    a = np.exp(-2 * np.pi * hz / RATE)
    out = np.empty_like(y)
    p = 0.0
    for i, v in enumerate(y):
        p = (1 - a) * v + a * p
        out[i] = p
    return out


def make(x, a, b, k, rms_to=0.1):
    pre, post = int(0.04 * RATE), int(0.09 * RATE)                 # (the breath before, the word's tail after)
    y = x[max(0, int(a * RATE) - pre):min(len(x), int(b * RATE) + post)].copy()
    pitch, pace = k.get("pitch", 1.0), k.get("pace", 1.0)
    if pitch != 1.0 or pace != 1.0:                               # (lower, at its own pace or slower)
        y = resample(stretch(y, pitch / pace), pitch)
    y = resample(y, k.get("speed", 1.0))
    y = highpass(y)
    t = np.arange(len(y)) / RATE
    if k.get("tremble"):
        y *= 1 - k["tremble"] * (0.5 + 0.5 * np.sin(2 * np.pi * 6.0 * t))
    if k.get("rattle"):
        y *= 0.45 + 0.55 * (0.5 + 0.5 * np.sin(2 * np.pi * k["rattle"] * t))
    if k.get("echo"):
        y = np.concatenate([y, np.zeros(int(0.45 * RATE))])
        wet = np.zeros_like(y)
        for d, g in ((0.071, 1.0), (0.113, 0.75), (0.167, 0.55), (0.241, 0.38), (0.337, 0.24)):
            n = int(d * RATE)
            wet[n:] += y[:-n] * g
        y = y + lowpass(wet, 2500) * k["echo"]
    fade_in, fade_out = int(0.008 * RATE), int(0.06 * RATE)
    y[:fade_in] *= np.linspace(0, 1, fade_in)
    y[-fade_out:] *= np.linspace(1, 0, fade_out)
    if rms_to:
        loud = y[np.abs(y) > 0.02 * np.max(np.abs(y))]            # (as loud as each other, by the words, not the gaps)
        y *= rms_to / max(np.sqrt(np.mean(loud ** 2)) if len(loud) else 1e-6, 1e-6)
    peak = np.max(np.abs(y))
    if peak > 0.9 or not rms_to:
        y *= (0.9 if rms_to else 0.7) / peak                      # (a jingle: as loud as the game's own, LevelUp's)
    return (y * 32767).astype("<i2").tobytes()


def write(name, data):
    path = os.path.join(ROOT, "sounds", name + ".wav")
    if os.path.exists(path):
        with wave.open(path, "rb") as w:
            if w.getframerate() == RATE and w.readframes(w.getnframes()) == data:
                return False
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(data)
    return True


def give(key, table):
    """key= (Voice or Growl) for each in table that has a section and none yet (written cp1252, CRLF, in place)."""
    path = os.path.join(ROOT, "data", "Entities.ini")
    with open(path, "rb") as f:
        lines = f.read().decode("cp1252").split("\r\n")
    who = {name: kind for kind, names in table.items() for name in names.split()}
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
            if ln.lower().startswith(key.lower() + "="):
                sections[sec][2] = True
    added = []
    for name, (first, last, has) in sorted(sections.items(), key=lambda kv: -kv[1][1]):   # (from the end up)
        if name in who and not has:
            lines.insert(last + 1, "%s=%s" % (key, who[name]))
            added.append(name)
    if added:
        with open(path, "wb") as f:
            f.write("\r\n".join(lines).encode("cp1252"))
    missing = sorted(n for n in who if n not in sections)
    return added, missing


def take_name(prefix, kind, n):
    return prefix + kind + ("" if n == 1 else "_%d" % n)


def build(prefix, table):
    made = total = 0
    for kind, k in table.items():
        for n, (sid, a, b) in enumerate(k["clips"], 1):
            made += write(take_name(prefix, kind, n), make(recording(sid), a, b, k))
        total += len(k["clips"])
        n = len(k["clips"]) + 1                                   # (fewer takes than before: the rest go)
        while os.path.exists(os.path.join(ROOT, "sounds", take_name(prefix, kind, n) + ".wav")):
            os.remove(os.path.join(ROOT, "sounds", take_name(prefix, kind, n) + ".wav"))
            n += 1
    return made, total


def main():
    made, total = build("Voice_", GREETINGS)
    print("Greetings: %d of %d sounds made or redrawn" % (made, total))
    made, total = build("Growl_", GROWLS)
    print("Growls: %d of %d sounds made or redrawn" % (made, total))
    made = 0
    for name, (sid, a, b) in JINGLES.items():
        x = recording(sid)
        k = {}
        made += write(name, make(x, a, (b or len(x) / RATE) - 0.09, k, rms_to=0))
    print("Jingles: %d of %d made or redrawn" % (made, len(JINGLES)))
    for key, table in (("Voice", VOICES), ("Growl", GROWLERS)):
        added, missing = give(key, table)
        print("%s= given to %d: %s" % (key, len(added), ", ".join(sorted(added)) or "-"))
        if missing:
            print("(no section for %s: left be)" % ", ".join(missing))


if __name__ == "__main__":
    main()
