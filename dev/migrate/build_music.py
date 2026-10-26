"""The background music: original pieces, one theme for each kind of place, written as General MIDI files.

Run:  python -I "dev\\migrate\\build_music.py"      (writes sounds\\Music_<Theme><n>.mid; deterministic)

Each theme (THEMES) has its key and mode, tempo and metre, two chord progressions (A and B sections), its instruments
and a percussion style. A piece is: intro (pad and arpeggio), A, A' (the A motifs on, a second voice joins), B (the
second lead takes the tune), B', A, and an outro that settles on the home chord, about two minutes. The melody is made
of two-bar motifs that come back (so it has a tune, not a wander): strong beats land on chord tones, the notes between
step through the scale, and each section ends on the tonic. Two variations of each theme (different melodies, leads
swapped) so a place doesn't play the same thing over and over: the game alternates them (data\\Music.ini).

Which theme plays where: data\\Music.ini [Maps], written by extend() below as part of build_world.py.
"""
import os
import random
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import p, read_lines  # noqa: E402

TPB = 480                       # ticks per beat
MAJOR = [0, 2, 4, 5, 7, 9, 11]
MINOR = [0, 2, 3, 5, 7, 8, 10]
HARMONIC = [0, 2, 3, 5, 7, 8, 11]
DORIAN = [0, 2, 3, 5, 7, 9, 10]
PHRYGIAN_DOM = [0, 1, 4, 5, 7, 8, 10]
PHRYGIAN = [0, 1, 3, 5, 7, 8, 10]

# GM programs (0-based)
FLUTE, RECORDER, PAN_FLUTE, OBOE, ENGLISH_HORN, CLARINET, BASSOON = 73, 74, 75, 68, 69, 71, 70
TRUMPET, HORN, BRASS, TUBA = 56, 60, 61, 58
STRINGS, SLOW_STRINGS, TREMOLO, PIZZ, CELLO, CONTRABASS, VIOLIN, FIDDLE = 48, 49, 44, 45, 42, 43, 40, 110
HARP, NYLON, DULCIMER, SITAR, CELESTA, MUSIC_BOX, GLOCK, VIBES, ACCORDION = 46, 24, 15, 104, 8, 10, 9, 11, 21
ACOUSTIC_BASS, FRETLESS, TIMPANI, CHOIR, OOHS, WARM_PAD, HALO_PAD, SHANAI = 32, 35, 47, 52, 53, 89, 94, 111

# name: settings. tonic = the MIDI note of the home key (the bass plays an octave or two under it)
THEMES = {
    "Town": dict(tonic=62, scale=MAJOR, bpm=108, beats=3, A=[0, 4, 5, 3, 0, 4, 3, 4], B=[5, 3, 0, 4, 1, 4, 0, 0],
                 leads=(FLUTE, VIOLIN), pad=STRINGS, arp=NYLON, bass=ACOUSTIC_BASS, perc="town", arp_style="waltz"),
    "Palace": dict(tonic=58, scale=MAJOR, bpm=84, beats=4, A=[0, 3, 4, 0, 0, 5, 3, 4], B=[3, 4, 2, 5, 1, 4, 0, 0],
                   leads=(TRUMPET, HORN), pad=STRINGS, arp=HARP, bass=TUBA, perc="timpani", arp_style="broad"),
    "Fields": dict(tonic=55, scale=MAJOR, bpm=96, beats=4, A=[0, 3, 5, 4, 0, 3, 4, 0], B=[5, 3, 0, 4, 5, 3, 1, 4],
                   leads=(OBOE, FLUTE), pad=SLOW_STRINGS, arp=HARP, bass=CELLO, perc="", arp_style="flow"),
    "Forest": dict(tonic=52, scale=DORIAN, bpm=80, beats=4, A=[0, 3, 0, 6, 0, 3, 6, 0], B=[2, 6, 3, 0, 2, 6, 3, 0],
                   leads=(PAN_FLUTE, RECORDER), pad=WARM_PAD, arp=NYLON, bass=FRETLESS, perc="", arp_style="flow"),
    "Desert": dict(tonic=50, scale=PHRYGIAN_DOM, bpm=92, beats=4, A=[0, 1, 0, 6, 0, 1, 3, 0], B=[3, 1, 0, 6, 3, 1, 6, 0],
                   leads=(SHANAI, OBOE), pad=SLOW_STRINGS, arp=SITAR, bass=FRETLESS, perc="desert", arp_style="pulse"),
    "Snow": dict(tonic=57, scale=MINOR, bpm=72, beats=4, A=[0, 5, 2, 6, 0, 3, 5, 4], B=[5, 2, 6, 0, 3, 5, 4, 0],
                 leads=(CELESTA, FLUTE), pad=HALO_PAD, arp=GLOCK, bass=CONTRABASS, perc="", arp_style="sparse"),
    "Marsh": dict(tonic=47, scale=HARMONIC, bpm=66, beats=4, A=[0, 5, 3, 4, 0, 3, 1, 4], B=[3, 0, 5, 4, 3, 1, 4, 0],
                  leads=(CLARINET, ENGLISH_HORN), pad=OOHS, arp=VIBES, bass=BASSOON, perc="", arp_style="sparse"),
    "Sea": dict(tonic=53, scale=MAJOR, bpm=100, beats=3, A=[0, 3, 0, 4, 0, 3, 4, 0], B=[5, 3, 0, 4, 0, 3, 4, 0],
                leads=(FIDDLE, ACCORDION), pad=ACCORDION, arp=NYLON, bass=ACOUSTIC_BASS, perc="", arp_style="waltz"),
    "Cave": dict(tonic=50, scale=HARMONIC, bpm=70, beats=4, A=[0, 0, 5, 4, 0, 3, 4, 0], B=[3, 0, 5, 4, 3, 5, 4, 0],
                 leads=(HORN, CELLO), pad=TREMOLO, arp=PIZZ, bass=CONTRABASS, perc="deep", arp_style="pulse"),
    "Lair": dict(tonic=52, scale=HARMONIC, bpm=132, beats=4, A=[0, 5, 3, 4, 0, 5, 4, 0], B=[3, 4, 0, 5, 3, 1, 4, 4],
                 leads=(BRASS, HORN), pad=TREMOLO, arp=PIZZ, bass=CONTRABASS, perc="battle", arp_style="drive"),
    # where the monsters are: urgent and driving (Danger), or slow and eerie (Dread: the undead and the spiders)
    "Danger": dict(tonic=48, scale=HARMONIC, bpm=116, beats=4, A=[0, 5, 0, 4, 0, 1, 5, 4], B=[3, 3, 0, 0, 5, 1, 4, 4],
                   leads=(BRASS, HORN), pad=TREMOLO, arp=PIZZ, bass=CONTRABASS, perc="battle", arp_style="drive"),
    "Dread": dict(tonic=47, scale=PHRYGIAN, bpm=58, beats=4, A=[0, 1, 0, 6, 0, 1, 3, 0], B=[5, 1, 3, 0, 5, 6, 1, 0],
                  leads=(BASSOON, ENGLISH_HORN), pad=CHOIR, arp=VIBES, bass=CONTRABASS, perc="deep", arp_style="sparse"),
    # the title: the login and loading screens. Broad and heroic: horns over a choir, harp sweeps, timpani
    "Title": dict(tonic=50, scale=MINOR, bpm=80, beats=4, A=[0, 5, 2, 6, 0, 5, 3, 4], B=[5, 6, 2, 2, 5, 3, 4, 4],
                  leads=(HORN, VIOLIN), pad=CHOIR, arp=HARP, bass=CELLO, perc="timpani", arp_style="broad"),
    # indoors: slow and soft, nothing like the towns' waltzes outside (a music box and a clarinet over a warm pad,
    # a harp rippling, no drums)
    "Hearth": dict(tonic=60, scale=MAJOR, bpm=63, beats=4, A=[0, 5, 3, 4, 0, 3, 4, 0], B=[3, 4, 2, 5, 1, 4, 0, 0],
                   leads=(MUSIC_BOX, CLARINET), pad=WARM_PAD, arp=HARP, bass=FRETLESS, perc="", arp_style="flow"),
}
VARIANTS = 2
CH_LEAD, CH_LEAD2, CH_PAD, CH_ARP, CH_BASS, CH_TIMP, CH_DRUMS = 0, 1, 2, 3, 4, 5, 9


# ------------------------------------------------------------------------------------------- the MIDI file
def vlq(n):
    out = [n & 0x7F]
    n >>= 7
    while n:
        out.append(0x80 | (n & 0x7F))
        n >>= 7
    return bytes(reversed(out))


class Song:
    def __init__(self):
        self.events = []        # (tick, order, bytes): note offs sort before note ons at the same tick

    def add(self, tick, data, order=1):
        self.events.append((max(0, int(tick)), order, bytes(data)))

    def note(self, ch, tick, length, pitch, vel):
        if not 0 <= pitch <= 127 or length <= 0:
            return
        vel = max(1, min(127, int(vel)))
        self.add(tick, (0x90 | ch, pitch, vel), 2)
        self.add(tick + length, (0x80 | ch, pitch, 0), 0)

    def write(self, path):
        data = b""
        last = 0
        for tick, _, ev in sorted(self.events, key=lambda e: (e[0], e[1])):
            data += vlq(tick - last) + ev
            last = tick
        data += vlq(0) + b"\xff\x2f\x00"
        blob = b"MThd" + struct.pack(">IHHH", 6, 0, 1, TPB) + b"MTrk" + struct.pack(">I", len(data)) + data
        if os.path.exists(path):
            with open(path, "rb") as f:
                if f.read() == blob:
                    return False
        with open(path, "wb") as f:
            f.write(blob)
        return True


# ------------------------------------------------------------------------------------------- harmony
class Key:
    def __init__(self, tonic, scale):
        self.tonic, self.scale = tonic, scale

    def pitch(self, i, base=0):
        """Scale step i (0 = the tonic, 7 = an octave up, may be negative) as a MIDI note, plus base semitones."""
        return self.tonic + base + 12 * (i // 7) + self.scale[i % 7]

    @staticmethod
    def chord(degree):
        return [degree % 7, (degree + 2) % 7, (degree + 4) % 7]


# ------------------------------------------------------------------------------------------- the tune
RHYTHMS = {   # one bar's note lengths in beats
    4: [[1, 1, 1, 1], [1.5, 0.5, 1, 1], [2, 1, 1], [1, 0.5, 0.5, 2], [0.5, 0.5, 1, 2], [1, 1, 2], [1.5, 0.5, 2],
        [1, 0.5, 0.5, 1, 1]],
    3: [[1, 1, 1], [2, 1], [1.5, 0.5, 1], [1, 0.5, 0.5, 1], [1, 2], [0.5, 0.5, 1, 1]],
}
CADENCE = {4: [[1, 1, 2], [2, 2], [4]], 3: [[1, 2], [3]]}


def nearest_chord_tone(i, tones, direction, rng):
    """The scale step nearest i (preferring the direction the tune is heading) whose note is in the chord."""
    best = None
    for d in range(0, 5):
        for s in ((d, -d) if direction >= 0 else (-d, d)):
            if (i + s) % 7 in tones:
                return i + s
    return best if best is not None else i


def phrase(rng, beats, chords, rhythm_bars, start, low, high, end_on_tonic):
    """Notes [(beat offset, length in beats, scale step)] for len(chords) bars over those chords."""
    notes = []
    i = start
    direction = rng.choice((-1, 1))
    for b, (deg, rhythm) in enumerate(zip(chords, rhythm_bars)):
        tones = Key.chord(deg)
        t = 0.0
        last_bar = b == len(chords) - 1
        for k, length in enumerate(rhythm):
            strong = t == 0 or (beats == 4 and t == 2)
            if rng.random() < 0.25:
                direction = -direction
            if i >= high:
                direction = -1
            if i <= low:
                direction = 1
            if last_bar and k == len(rhythm) - 1 and end_on_tonic:
                i = min((x for x in range(low - 7, high + 8) if x % 7 == 0), key=lambda x: abs(x - i))
            elif strong:
                i = nearest_chord_tone(i + direction, tones, direction, rng)
            else:
                i += direction * rng.choice((1, 1, 1, 2))
            i = max(low, min(high, i))
            notes.append((b * beats + t, length, i))
            t += length
    return notes, i


class Composer:
    def __init__(self, name, spec, variant):
        self.name, self.spec, self.variant = name, spec, variant
        self.rng = random.Random("%s/%d" % (name, variant))
        self.key = Key(spec["tonic"], spec["scale"])
        self.beats = spec["beats"]
        self.bar = self.beats * TPB
        self.song = Song()
        lead, lead2 = spec["leads"]
        if variant % 2:
            lead, lead2 = lead2, lead
        self.programs = {CH_LEAD: lead, CH_LEAD2: lead2, CH_PAD: spec["pad"], CH_ARP: spec["arp"],
                         CH_BASS: spec["bass"], CH_TIMP: TIMPANI}

    def setup(self):
        s = self.song
        s.add(0, b"\xff\x51\x03" + struct.pack(">I", int(60000000 / self.spec["bpm"]))[1:])
        s.add(0, b"\xff\x58\x04" + bytes((self.beats, 2, 24, 8)))
        volumes = {CH_LEAD: 100, CH_LEAD2: 88, CH_PAD: 62, CH_ARP: 72, CH_BASS: 92, CH_TIMP: 84, CH_DRUMS: 70}
        pans = {CH_LEAD: 64, CH_LEAD2: 50, CH_PAD: 64, CH_ARP: 84, CH_BASS: 58, CH_TIMP: 64, CH_DRUMS: 70}
        for ch, prog in self.programs.items():
            s.add(0, (0xC0 | ch, prog))
        for ch in volumes:
            s.add(0, (0xB0 | ch, 7, volumes[ch]))
            s.add(0, (0xB0 | ch, 10, pans[ch]))
            s.add(0, (0xB0 | ch, 91, 70))                     # reverb

    def human(self, tick):
        return tick + self.rng.randint(-6, 6)

    # --- the parts, bar by bar
    def bass(self, bar, deg, vel):
        root = self.key.pitch(deg % 7, -24)
        if root > self.key.tonic - 7:
            root -= 12
        t0 = bar * self.bar
        if self.beats == 3:
            self.song.note(CH_BASS, t0, TPB * 2 - 20, root, vel)
            self.song.note(CH_BASS, t0 + TPB * 2, TPB - 20, root + 7, vel - 15)
        else:
            self.song.note(CH_BASS, t0, TPB * 2 - 20, root, vel)
            self.song.note(CH_BASS, t0 + TPB * 2, TPB * 2 - 20, root + (7 if self.rng.random() < 0.6 else 0), vel - 12)

    def pad(self, bar, deg, vel):
        t0 = bar * self.bar
        for k, step in enumerate(Key.chord(deg)):
            pitch = self.key.pitch(step, -12)
            while pitch < self.key.tonic - 7:
                pitch += 12
            while pitch > self.key.tonic + 7:
                pitch -= 12
            self.song.note(CH_PAD, t0 + k * 8, self.bar - 30, pitch, vel - k * 4)

    def arp(self, bar, deg, vel):
        style = self.spec["arp_style"]
        tones = sorted(self.key.pitch(s) for s in Key.chord(deg))
        tones = [t - 12 if t > self.key.tonic + 7 else t for t in tones]
        tones = sorted(tones)
        seq = tones + [t + 12 for t in tones]
        t0 = bar * self.bar
        if style == "waltz":                          # oom-pah-pah: low note, then the chord twice
            self.song.note(CH_ARP, self.human(t0), TPB - 40, tones[0], vel)
            for b in (1, 2):
                for k, t in enumerate(tones[1:] + [tones[0] + 12]):
                    self.song.note(CH_ARP, self.human(t0 + b * TPB) + k * 6, TPB - 60, t, vel - 18)
        elif style == "broad":                        # a harp sweep up on the downbeat, a chord mid-bar
            for k, t in enumerate(seq):
                self.song.note(CH_ARP, t0 + k * 40, self.bar // 2, t, vel - k * 3)
            for k, t in enumerate(tones):
                self.song.note(CH_ARP, t0 + self.bar // 2 + k * 10, self.bar // 2 - 40, t + 12, vel - 20)
        elif style == "sparse":                       # a few bell notes
            for b in range(self.beats):
                if b == 0 or self.rng.random() < 0.45:
                    self.song.note(CH_ARP, self.human(t0 + b * TPB), TPB * 2, self.rng.choice(seq[2:]), vel - 10)
        elif style in ("pulse", "drive"):             # repeated eighths (sixteenths when driving) on the chord
            step = TPB // 4 if style == "drive" else TPB // 2
            n = self.bar // step
            pattern = [0, 2, 1, 2] if style == "drive" else [0, 1, 2, 1]
            for k in range(n):
                acc = 14 if k % (4 if style == "drive" else 2) == 0 else 0
                self.song.note(CH_ARP, t0 + k * step, step - 30, seq[pattern[k % 4]], vel - 16 + acc)
        else:                                         # flow: eighths up and down the chord
            order = [0, 1, 2, 3, 4, 3, 2, 1]
            for k in range(self.beats * 2):
                self.song.note(CH_ARP, self.human(t0 + k * TPB // 2), TPB // 2 + 60, seq[order[k % 8]], vel - (0 if k % 2 == 0 else 14))

    def drums(self, bar, vel, fill=False):
        style, t0, b = self.spec["perc"], bar * self.bar, TPB
        if style == "town":
            for k in range(1, self.beats):
                self.song.note(CH_DRUMS, t0 + k * b, 60, 54, vel - 40)                  # tambourine
        elif style == "desert":
            self.song.note(CH_DRUMS, t0, 120, 64, vel)                                   # low conga
            self.song.note(CH_DRUMS, t0 + int(1.5 * b), 60, 63, vel - 20)
            self.song.note(CH_DRUMS, t0 + 2 * b, 120, 64, vel - 10)
            for k in (1, 3):
                self.song.note(CH_DRUMS, t0 + k * b, 60, 62, vel - 25)                   # high conga
            self.song.note(CH_DRUMS, t0 + int(3.5 * b), 60, 54, vel - 40)
        elif style == "battle":
            self.song.note(CH_DRUMS, t0, 120, 36, vel)                                    # kick
            self.song.note(CH_DRUMS, t0 + 2 * b, 120, 36, vel - 10)
            for k in (1, 3):
                self.song.note(CH_DRUMS, t0 + k * b, 120, 38, vel - 15)                  # snare
            if fill:
                for k in range(8):
                    self.song.note(CH_DRUMS, t0 + 2 * b + k * b // 4, 60, 45 - (k // 2) * 2, vel - 10 + k * 2)
        if style in ("timpani", "deep", "battle"):
            root = self.key.pitch(0, -24)
            while root < 40:
                root += 12
            if style == "battle" or bar % 2 == 0 or fill:
                self.song.note(CH_TIMP, t0, b, root, vel - (10 if style == "deep" else 0))
            if fill and style != "battle":
                for k in range(6):                       # a roll into the next section
                    self.song.note(CH_TIMP, t0 + 2 * b + k * b // 3, b // 3, root, vel - 30 + k * 6)

    def melody(self, ch, start_bar, notes, vel, octave=12):
        for beat, length, step in notes:
            tick = self.human(start_bar * self.bar + int(beat * TPB))
            accent = 10 if beat % self.beats == 0 else 0
            self.song.note(ch, tick, int(length * TPB) - 25, self.key.pitch(step, octave), vel + accent)

    # --- the piece
    def section(self, chords, motifs, cadence, start):
        """A section's tune: four two-bar phrases (1, 1 again, 2, the cadence) over its eight chords."""
        notes, i = [], start
        for k, rh in enumerate((motifs[0], motifs[0], motifs[1], cadence)):
            ns, i = phrase(self.rng, self.beats, chords[2 * k:2 * k + 2], rh, i, 2, 12, k == 3)
            notes += [(2 * k * self.beats + b, length, s) for b, length, s in ns]
        return notes, i

    def compose(self):
        self.setup()
        sp, rng, beats = self.spec, self.rng, self.beats
        A, B = list(sp["A"]), list(sp["B"])
        if self.variant % 2:
            A = A[4:] + A[:4] if A[3] in (0, 4) else A
        rh = RHYTHMS[beats]
        motif = lambda: [rng.choice(rh), rng.choice(rh)]
        cad = lambda: [rng.choice(rh), rng.choice(CADENCE[beats])]
        motifs_a, motifs_b, cad_a, cad_b = (motif(), motif()), (motif(), motif()), cad(), cad()
        tune_a, i = self.section(A, motifs_a, cad_a, 7)
        tune_a2, i = self.section(A, motifs_a, cad_a, i)
        tune_b, i = self.section(B, motifs_b, cad_b, i + 2)
        tune_b2, _ = self.section(B, motifs_b, cad_b, i)
        plan = [("intro", A[:2]), ("A", A), ("A2", A), ("B", B), ("B2", B), ("A", A), ("outro", [A[0], A[0]])]
        bar = 0
        for name, chords in plan:
            full = name not in ("intro", "outro")
            for k, deg in enumerate(chords):
                b = bar + k
                self.pad(b, deg, 70 if full else 60)
                self.arp(b, deg, 76 if full else 64)
                if name != "intro":
                    self.bass(b, deg, 92)
                if sp["perc"] and full:
                    self.drums(b, 96, fill=(k == len(chords) - 1))
            if name in ("A", "A2"):
                self.melody(CH_LEAD, bar, tune_a if name == "A" else tune_a2, 92)
                if name == "A2":                       # a second voice, a third under the tune, softly
                    self.melody(CH_LEAD2, bar, [(t, n, s - 2) for t, n, s in tune_a2], 62, octave=0)
            elif name in ("B", "B2"):
                self.melody(CH_LEAD2, bar, tune_b if name == "B" else tune_b2, 90)
                if name == "B2":
                    self.melody(CH_LEAD, bar, [(t, n, s + 2) for t, n, s in tune_b2], 58)
            elif name == "outro":
                self.song.note(CH_LEAD, bar * self.bar, self.bar * 2 - 60, self.key.pitch(7, 12), 70)
                self.song.note(CH_BASS, bar * self.bar, self.bar * 2 - 60, self.key.pitch(0, -24), 80)
            bar += len(chords)
        return self.song


def track_file(theme, variant):
    return "Music_%s%d.mid" % (theme, variant + 1)


def main():
    for name, spec in THEMES.items():
        for v in range(VARIANTS):
            path = p("sounds", track_file(name, v))
            print(("wrote " if Composer(name, spec, v).compose().write(path) else "unchanged ") + os.path.basename(path))


# ------------------------------------------------------------------------------------------- where each plays
W = R = None
PALACE_MAPS = {"4,4,0", "4,4,1", "2,4,0"}
TOWN_MAPS = {"1,3,0", "2,3,0", "1,1,0", "3,4,0"}   # (3,4,0: Ashford's market square, once the goblin camp)


BOSSES = {"Bog_Troll", "Cave_Troll", "Frost_Troll", "Alpha_Wolf", "Hob", "Barrow_King"}
DREADFUL = {"Skeleton", "Barrow_King", "Giant_Spider"}
DANGER_HP = 100             # the hitpoints of the aggressive monsters on a map that make it dangerous
DANGER_MAPS = {"2,4,-2"}   # and always: the hobgoblin warren


def danger_of(name):
    """'Dread', 'Danger' or '' for a map, from the monsters in its file: the undead or a spiders' nest is dread;
    a boss, or aggressive monsters with DANGER_HP hitpoints between them, is danger."""
    from common import Ini
    ents = Ini(p("data", "Entities.ini"))
    path = p("maps", name + ".txt")
    if name in DANGER_MAPS:
        return "Danger"
    if not os.path.exists(path):
        return ""
    lines = read_lines(path)[21:]
    names = [l.split("	")[1] for l in lines if l.startswith("NPC	") and "Attitude=Bad" in l]
    foes = [n for n in names if (ents.get(n, "Aggressive") or "0").strip() == "1"]
    if sum(1 for n in foes if n in DREADFUL) >= 3 or "Barrow_King" in foes:
        return "Dread"
    hp = sum(float(ents.get(n, "Hitpoints") or 0) for n in foes)
    if hp >= DANGER_HP or any(n in BOSSES for n in foes):
        return "Danger"
    return ""


def theme_for(name, ambient):
    x, y, z = (int(v) for v in name.split(","))
    if name in PALACE_MAPS:
        return "Palace"
    if name == "0,0,-9":
        return "Lair"
    if name not in TOWN_MAPS and name not in town_maps():
        danger = danger_of(name)
        if danger:
            return danger
    if z < 0:
        return "Cave"
    if z > 0:
        return "Hearth"
    if name in TOWN_MAPS or name in town_maps():
        return "Town"
    return {"Forest": "Forest", "Wind": "Fields", "Desert": "Desert", "Snow": "Snow", "Marsh": "Marsh",
            "Cave": "Cave", "": "Sea"}.get(ambient, "Fields")


def town_maps():
    import build_eastreach as E
    import build_walled as WL
    import build_cinder as CI
    out = set()
    for mod in (R, E, WL, CI):
        for town in mod.TOWNS:
            m, _, _ = mod.local(*mod.town_centre(town))
            out.add(m)
    for m in ("4,2,0", "5,2,0", "4,3,0", "5,3,0"):        # Wardhaven, inside its walls
        out.add(m)
    return out


def write_music_ini():
    from common import write_lines
    import build_travel
    lines = ["; The music for each map: sounds\\Music_<Theme><n>.mid, the theme's variations taking turns (Config",
             "; [Sounds] Music.On=0 turns it off). Generated by dev\\migrate\\build_music.py: edit it there.", "",
             "[Themes]"]
    for name in THEMES:
        lines.append("%s=%s" % (name, ",".join(track_file(name, v) for v in range(VARIANTS))))
    lines += ["", "[Maps]"]
    for name in W.all_maps():
        lines.append("%s=%s" % (name, theme_for(name, build_travel.ambient_for(name))))
    return ["data\\Music.ini"] if write_lines(p("data", "Music.ini"), lines) else []


def extend(world, regions):
    global W, R
    W, R = world, regions
    W.EXTRA_STEPS.append(write_music_ini)


if __name__ == "__main__":
    main()
