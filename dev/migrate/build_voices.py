"""People's greetings, monsters' growls and the quest-taken jingle, all cut from CC0 recordings (freesound.org; each is
in SOURCES and CREDITS.md):

  sounds\\Voice_<Kind>.wav, _2 ...   what someone says as you start talking to them ("Hello", "Well met", "How can
                                     I help?"): one of their kind's, at the speaker's own pitch (web/js/voice.js)
  sounds\Bye_<Kind>.wav, _2 ...     what they say as the talk ends ("Goodbye", "Thank you"), in the same voice as
                                     their greeting: only a kind whose speaker recorded one has any (FAREWELLS)
  sounds\\Growl_<Kind>.wav, _2 ...   a monster that's seen you and comes for you (npcs.py npc_growl)
  sounds\\Quest_Start.wav             a quest taken on (a harp's run up; a quest finished, Quest_Done, is
                                     build_soundscape's: quieter)
  sounds\\Moo.wav, Baa, Cluck ...     an animal's noise (CALLS): now and then on its own, and as you do something
                                     with it (stroke it, feed it, milk it, talk to it in an animal's body)

Real people's words, never made up from tones (that sounded like a machine) or mumbled (that sounded awful). The
deeper voices are the same recordings made lower (the pitch moved, the pace kept: stretch); the old are real old
people (Common Voice), never a younger voice made old; a mourner only sighs; a ghost's echo; the beasts are a
creature's mutterings slowed, with a rattle for a troll's or a frog's throat.

The recordings are fetched the first time (freesound's previews; a Common Voice clip out of its parquet file, which
needs pyarrow just then; ffmpeg makes them WAVs) and kept in dev\\Voices (not in git).

Also gives each speaker in data\\Entities.ini its Voice= (one of GREETINGS), each monster its Growl= (one of
GROWLS) and each animal its Calls= (CALLERS), unless it has one already: the owner's choice stands. A notice, a
sign or a letter has no voice: it's silent.

  python -I "dev\\migrate\\build_voices.py"

Safe to run again: the same cuts, made the same way, and only missing Voice=/Growl=/Calls= lines are added.
"""
import os
import re
import shutil
import subprocess
import sys
import urllib.request
import wave

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import sound_file  # noqa: E402
CACHE = os.path.join(ROOT, "dev", "Voices")
RATE = 22050

# the recordings (all CC0): freesound id -> its preview (cdn.freesound.org/previews/...), who made it, its title
SOURCES = {
    431176: ("431176_3082984", "envirOmaniac2", "Thirty-Eight Greetings."),
    351611: ("351611_6325950", "bectec", "Female greetings.wav"),
    352220: ("352220_6325950", "bectec", "female alto goodby.wav"),
    429038: ("429038_6492957", "theuncertainman", "Greetings (NPC, British Male)"),
    429037: ("429037_6492957", "theuncertainman", "How can I help? (NPC, British Male)"),
    458074: ("458074_6492957", "theuncertainman", "What can I do for you? (NPC, British Male)"),
    429036: ("429036_6492957", "theuncertainman", "Thank you (NPC, British Male)"),
    501882: ("501882_7076647", "Nchamp13", "Welcome Traveler.mp3"),
    449481: ("449481_9288538", "12125065", "hello"),
    447392: ("447392_6253486", "florianreichelt", "man saying hello"),
    50940: ("50940_71257", "qubodup", "Fearing Hello"),
    677407: ("677407_12064174", "SnowFightStudios", "Monster or Creature Mutterings and Gibberish"),
    669913: ("669913_12064174", "SnowFightStudios", "Creature Gibberish Language\\Dialogue - Monster\\Alien"),
    490831: ("490831_10350281", "PhonosUPF", "harp glissando"),
    242625: ("242625_950925", "Reitanna", "heavy sigh.wav"),
    242690: ("242690_950925", "Reitanna", "long sigh.wav"),
    427722: ("427722_8295394", "lemigoga", "05. Suspiro madre.wav"),
    429321: ("429321_8649084", "Tomycatts", "49-suspiro mujer.wav"),
    # the animals (CALLS)
    354132: ("354132_5462031", "betterchinese", "Frog croaking sound effect"),
    397236: ("397236_4889106", "black_trillium", "Horse Snort.wav"),
    538697: ("538697_11519060", "bruno.auzet", "horse snort.wav"),
    424076: ("424076_7388661", "chanyatenn", "chicken sound - clucking.wav"),
    437960: ("437960_2524442", "craigsmith", "G12-28-Seal Bark.wav"),
    558858: ("558858_7414526", "DigPro120", "Duck quacking.mp3"),
    656500: ("656500_6497685", "druulian", "Cat purr"),
    414541: ("414541_6694545", "emilyws", "Sheep Baa"),
    832435: ("832435_1661766", "felix.blume", "Dog barking"),
    149024: ("149024_2581089", "foxen10", "Horse_Whinny.wav"),
    528949: ("528949_3302313", "fthgurdy", "Cat's short purr"),
    805297: ("805297_17326459", "jahjahjahjah", "goose honk"),
    187261: ("187261_3165570", "Jonnyhoff91", "duck.wav"),
    177253: ("177253_276010", "JosephSardin", "Cow moos"),
    372075: ("372075_4521595", "kessir", "Rabbit oinks and squeaks"),
    277058: ("277058_4486188", "kwahmah_02", "Single Dog Bark"),
    333916: ("333916_4930786", "lextrack", "Cat Meowing"),
    436541: ("436541_1196472", "Mafon2", "Cat Meow"),
    418509: ("418509_5632532", "Mikes-MultiMedia", "single quack from a duck"),
    583856: ("583856_3902754", "mycompasstv", "geese honking honk"),
    475483: ("475483_7009965", "o_ciz", "Horse(snort)_3.wav"),
    692898: ("692898_14166079", "satoristudios3", "Twin Lambs Baa-ing"),
    692899: ("692899_14166079", "satoristudios3", "Lambs bleating"),
    692900: ("692900_14166079", "satoristudios3", "Ewe Shetland Sheep Baa"),
    412017: ("412017_3652520", "skymary", "cat meow short"),
    188195: ("188195_1480854", "SpliceSound", "Green frog, croaking.wav"),
    23142: ("23142_92534", "stackpool", "river otter or weasel 2006-09-17.mp3"),
    53258: ("53258_177850", "stomachache", "duck.wav"),
    362652: ("362652_5966858", "TRNGLE", "Cat meow"),
}

# real old people's voices, never a younger one's made old: Mozilla Common Voice 17.0 (CC0), its clip -> the parquet
# file of the en "validated" split it's in (fixie-ai/common_voice_17_0 on Hugging Face), the row group and the row,
# the speaker (each kind is one person's every take) and what they read out
CV_BASE = "https://huggingface.co/datasets/fixie-ai/common_voice_17_0/resolve/main/en/validated-%s-of-00138.parquet"
CV_SOURCES = {
    "common_voice_en_18078830": ("00004", 2, 7, "a man in his seventies",
                                 "Good afternoon sir, how may I be of service?"),
    "common_voice_en_18139265": ("00016", 31, 43, "a man in his seventies", "Hello, my name is Brenda."),
    "common_voice_en_18105147": ("00058", 85, 58, "a man in his seventies", "Hello! It is great to see you!"),
    "common_voice_en_18105271": ("00087", 3, 4, "a man in his seventies", "Good evening."),
    "common_voice_en_18090744": ("00126", 33, 70, "a man in his seventies", "Good morning."),
    "common_voice_en_21913523": ("00019", 30, 2, "a woman in her sixties",
                                 "\"Good Morning, Mister Echo\" was a popular song."),
    "common_voice_en_21901890": ("00045", 102, 25, "a woman in her sixties", "Hey"),
    "common_voice_en_147943": ("00055", 119, 8, "a woman in her sixties", "Good evening"),
}

# what each kind of speaker says: (recording, from s, to s) each, what it says in the comment; then how it's made:
# pitch (below 1: lower), pace (below 1: slower), an echo (a ghost's), a rattle (times a
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
    "Old_Man": dict(clips=[("common_voice_en_18078830", 0.33, 0.88),   # Good afternoon.   (one man in his seventies,
                           ("common_voice_en_18139265", 0.33, 0.81),   # Hello.             as he is: Common Voice)
                           ("common_voice_en_18105147", 0.24, 1.65),   # Hello! It's great to see you!
                           ("common_voice_en_18105271", 0.57, 1.23),   # Good evening.
                           ("common_voice_en_18090744", 0.60, 1.23)]), # Good morning.
    "Old_Woman": dict(clips=[("common_voice_en_21913523", 0.84, 1.43),  # Good morning.   (one woman in her sixties)
                             ("common_voice_en_21901890", 0.60, 0.99),  # Hey.
                             ("common_voice_en_147943", 1.23, 1.89)]),  # Good evening.
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
    # (a mourner doesn't say hello at a funeral: she sighs, softly)
    "Sigh": dict(clips=[(242625, 0.08, 1.40), (242690, 0.08, 1.25), (427722, 0.30, 1.95), (429321, 1.08, 2.50)],
                 rms=0.06),
}

# what each kind says as you part (Bye_: voice.js), the same speaker as its greeting and made the same way: the
# woman's goodbyes, the deep voice's thank-you; the mourner sighs again and the beasts mutter. The man's, the old
# people's, the gruff's and the ghost's speakers recorded no goodbye, so they say none (another's voice would jar)
BYE = 352220
FAREWELLS = {
    "Woman": dict(clips=[(BYE, a, b) for a, b in ((1.02, 1.42), (1.87, 2.31), (2.67, 3.19), (3.47, 4.25),
                                                  (4.62, 5.37), (6.74, 7.26), (10.02, 10.53), (12.45, 12.89),
                                                  (13.53, 14.08), (14.42, 14.99))]),
    "Deep": dict(clips=[(429036, 0.37, 0.81)],      # Thank you.
                 pitch=0.88),
    "Sigh": GREETINGS["Sigh"],
    "Croak": GREETINGS["Croak"],
    "Beast": GREETINGS["Beast"],
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
}

# who speaks how (Entities.ini sections); anyone who speaks and isn't here gets none until it's given one
VOICES = {
    "Man": "Villager Trader Greengrocer Fishmonger Carter Clerk Cobbler Hotelier Beekeeper Courier Constable Druid "
           "Ranger Chancellor Mayor Merchant Man Barkeep Baker Doctor Edwin Banker Shopkeeper Farmer Shepherd Scholar "
           "Sheriff Quartermaster Jester Travelling_Salesman Night_Smuggler Ashen_Acolyte Penitent Collier "
           "Mending_Wayfarer Ferryman Bert Pip",
    "Deep": "Guard Port_Guard Guard_Captain Royal_Guard Captain Butcher Armourer Frank Dwarf Forgemaster Sea_Captain "
            "King_Rupert King_Tyron",
    "Woman": "Woman Settler Painter Barmaid Blacksmith Herbalist Maren Milkmaid Nurse Tailor Scout Warden "
             "Wyrmsmith Ice_Fisher Mending_Sister Mending_Cantor Duchess",
    "Old_Man": "Beggar Elder Eldest_of_the_Mending Fisherman Gravekeeper Hermit Manor_Steward Miner Tobias Wizard "
               "Steward Speaker Archivist",
    "Old_Woman": "Old_Woman Beachcomber Marsh_Witch Witch Stone_Ringer",
    "Gruff": "Hob Bandit Talking_Scarecrow",
    "Sigh": "Mourner",
    "Ghost": "Delver_Ghost Ghost_Warden Orrin_Ghost Toll_Keeper Valour_Guardian Wandering_Echo Ysolde Singing_Remnant "
             "The_Voice Great_Shard Echo_Pool",
    "Croak": "Frog_King",
    "Beast": "Galaith_Dragon",
}

# an animal's noise, the same as it makes now and then and as you do something with it (its Calls=: npcs.py,
# player_actions.py animal_noise); a field recording's background hushed between its sounds (gate)
CALLS = {
    "Moo": dict(clips=[(177253, 0.67, 2.30), (177253, 3.29, 5.15), (177253, 6.02, 7.85), (177253, 9.54, 11.37),
                       (177253, 12.44, 13.90)], gate=True),
    "Baa": dict(clips=[(414541, 0.01, 0.97), (414541, 1.37, 2.84), (414541, 3.28, 4.39), (692900, 0.11, 1.84),
                       (692900, 2.45, 3.52)], gate=True),
    "Bleat": dict(clips=[(692899, 0.03, 1.16), (692899, 1.32, 2.07), (692898, 0.04, 1.76),
                         (692898, 2.37, 3.44)], gate=True),
    "Cluck": dict(clips=[(424076, 0.08, 1.18), (424076, 1.47, 1.67), (424076, 1.92, 2.74),
                         (424076, 3.16, 3.97)], gate=True),
    "Quack": dict(clips=[(418509, 0.00, 0.20), (53258, 0.13, 0.73), (53258, 3.95, 4.52), (558858, 0.69, 1.16),
                         (187261, 2.68, 3.47)], gate=True),
    "Honk": dict(clips=[(805297, 0.03, 0.52), (583856, 1.94, 2.13), (583856, 5.05, 5.62), (583856, 11.48, 11.86),
                        (583856, 30.52, 30.72)], gate=True),
    "Snort": dict(clips=[(475483, 0.00, 0.51), (397236, 0.44, 0.86), (397236, 1.96, 2.33), (538697, 0.17, 0.92),
                         (149024, 3.40, 5.29)], gate=True),
    "Dog_Bark": dict(clips=[(832435, 2.18, 2.35), (832435, 3.28, 3.48), (832435, 5.53, 5.78), (832435, 8.15, 8.37),
                            (277058, 0.00, 0.30)], gate=True),
    "Meow": dict(clips=[(362652, 0.09, 1.08), (412017, 0.09, 1.58), (333916, 0.15, 1.30),
                        (436541, 0.05, 0.46)], gate=True),
    "Purr": dict(clips=[(656500, 2.60, 4.60), (656500, 5.20, 7.20), (528949, 0.42, 1.57)], gate=True, rms=0.06),
    "Croak": dict(clips=[(188195, 2.32, 3.36), (188195, 6.87, 7.60), (188195, 4.09, 4.35), (188195, 11.33, 11.51),
                         (354132, 0.65, 0.89)], gate=True),
    "Seal_Bark": dict(clips=[(437960, 3.19, 4.26), (437960, 11.02, 12.09), (437960, 19.35, 20.95),
                             (437960, 0.10, 2.62)], gate=True),
    "Rabbit_Grunt": dict(clips=[(372075, 6.50, 6.87), (372075, 9.33, 9.89), (372075, 11.83, 12.03),
                                (372075, 20.40, 20.65)], gate=True, rms=0.06),
    "Otter_Chirp": dict(clips=[(23142, 7.30, 7.99), (23142, 11.58, 12.27), (23142, 16.89, 17.45),
                               (23142, 4.73, 5.28)], gate=True),
}

# who makes which noise (Calls=; a sleeping cat, a toy duck or a wax seal has none)
CALLERS = {
    "Moo": "Cow",
    "Baa": "Sheep",
    "Bleat": "Stray_Lamb",
    "Cluck": "Chicken",
    "Quack": "Duck",
    "Honk": "Goose",
    "Snort": "Horse Royal_Horse",
    "Dog_Bark": "Dog",
    "Meow": "Cat Black_Cat Ginger_Cat Strawberry_Cat Fat_Grey_Cat Tuxedo_Cat",
    "Croak": "Frog",
    "Seal_Bark": "Seal",
    "Rabbit_Grunt": "Rabbit",
    "Otter_Chirp": "Otter",
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


class Ranged:
    """A file on the web read in pieces (HTTP ranges), as pyarrow reads a parquet file: only what it needs."""
    def __init__(self, url):
        self.pos, self.closed = 0, False
        with urllib.request.urlopen(urllib.request.Request(url, method="HEAD"), timeout=60) as r:
            self.url, self.size = r.geturl(), int(r.headers["Content-Length"])

    def seekable(self):
        return True

    def readable(self):
        return True

    def tell(self):
        return self.pos

    def seek(self, off, whence=0):
        self.pos = off if whence == 0 else self.pos + off if whence == 1 else self.size + off
        return self.pos

    def read(self, n=-1):
        n = self.size - self.pos if n is None or n < 0 else min(n, self.size - self.pos)
        if n <= 0:
            return b""
        req = urllib.request.Request(self.url, headers={"Range": "bytes=%d-%d" % (self.pos, self.pos + n - 1)})
        with urllib.request.urlopen(req, timeout=120) as r:
            got = r.read()
        self.pos += len(got)
        return got

    def close(self):
        self.closed = True


def common_voice(clip, mp3):
    """A Common Voice clip, out of the parquet file it's in (pyarrow: needed only the first time, to fetch it)."""
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
    except ImportError:
        raise SystemExit("pyarrow is needed once, to fetch %s from Common Voice (pip install pyarrow)" % clip)
    part, group, row = CV_SOURCES[clip][:3]
    f = pq.ParquetFile(pa.PythonFile(Ranged(CV_BASE % part), mode="r"))
    audio = f.read_row_group(group, columns=["audio"]).slice(row, 1).to_pylist()[0]["audio"]
    if not os.path.basename(audio.get("path") or "").startswith(clip):
        raise SystemExit("%s isn't where it was (%s, row group %d, row %d)" % (clip, part, group, row))
    with open(mp3, "wb") as out:
        out.write(audio["bytes"])


def recording(sid):
    """The recording as mono 22050 Hz, fetched and kept the first time."""
    wav = os.path.join(CACHE, "%s.wav" % sid)
    if not os.path.exists(wav):
        os.makedirs(CACHE, exist_ok=True)
        mp3 = os.path.join(CACHE, "%s.mp3" % sid)
        if not os.path.exists(mp3) and sid in CV_SOURCES:
            common_voice(sid, mp3)
        elif not os.path.exists(mp3):
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
    if k.get("gate"):                                             # (between a field recording's calls: hushed)
        hop = 220
        n = len(y) // hop + 1
        env = np.array([np.sqrt(np.mean(y[i * hop:(i + 1) * hop] ** 2)) if i * hop < len(y) else 0.0 for i in range(n)])
        g = np.clip(env / max(env.max() * 0.08, 1e-6), 0, 1) ** 2
        g = np.convolve(g, np.ones(5) / 5, "same")
        y = y * np.interp(np.arange(len(y)), np.arange(n) * hop + hop / 2, g)
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
    rms_to = k.get("rms", rms_to)                                 # (a sigh is quieter than a hello)
    if rms_to:
        loud = y[np.abs(y) > 0.02 * np.max(np.abs(y))]            # (as loud as each other, by the words, not the gaps)
        y *= rms_to / max(np.sqrt(np.mean(loud ** 2)) if len(loud) else 1e-6, 1e-6)
    peak = np.max(np.abs(y))
    if peak > 0.9 or not rms_to:
        y *= (0.9 if rms_to else 0.7) / peak                      # (a jingle: as loud as the game's own, LevelUp's)
    return (y * 32767).astype("<i2").tobytes()


def write(name, data):
    path = sound_file(name)
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


SPOKEN = ("Man", "Deep", "Woman", "Old_Man", "Old_Woman", "Gruff")
SPOKEN_PACE = 0.9                       # (people's greetings a little slower than recorded: they sounded hurried)


def build(prefix, table):
    made = total = 0
    for kind, k in table.items():
        if prefix in ("Voice_", "Bye_") and kind in SPOKEN:
            k = dict(k, pace=k.get("pace", SPOKEN_PACE))
        for n, (sid, a, b) in enumerate(k["clips"], 1):
            made += write(take_name(prefix, kind, n), make(recording(sid), a, b, k))
        total += len(k["clips"])
        n = len(k["clips"]) + 1                                   # (fewer takes than before: the rest go)
        while os.path.exists(sound_file(take_name(prefix, kind, n))):
            os.remove(sound_file(take_name(prefix, kind, n)))
            n += 1
    return made, total


def main():
    made, total = build("Voice_", GREETINGS)
    print("Greetings: %d of %d sounds made or redrawn" % (made, total))
    made, total = build("Bye_", FAREWELLS)
    print("Goodbyes: %d of %d sounds made or redrawn" % (made, total))
    made, total = build("Growl_", GROWLS)
    print("Growls: %d of %d sounds made or redrawn" % (made, total))
    made = 0
    for name, (sid, a, b) in JINGLES.items():
        x = recording(sid)
        k = {}
        made += write(name, make(x, a, (b or len(x) / RATE) - 0.09, k, rms_to=0))
    print("Jingles: %d of %d made or redrawn" % (made, len(JINGLES)))
    made, total = build("", CALLS)
    print("Animals' noises: %d of %d sounds made or redrawn" % (made, total))
    for key, table in (("Voice", VOICES), ("Growl", GROWLERS), ("Calls", CALLERS)):
        added, missing = give(key, table)
        print("%s= given to %d: %s" % (key, len(added), ", ".join(sorted(added)) or "-"))
        if missing:
            print("(no section for %s: left be)" % ", ".join(missing))


if __name__ == "__main__":
    main()
