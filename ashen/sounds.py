"""The sounds' folders: sounds\\<kind>\\<Name>.wav (ui, creatures, voices, ambient, skills, combat, magic, world, music).

A sound is found by its name wherever it is, so Entities.ini and the scripts name it bare (Play.Sound Door), and no two
sounds share a name (validate.py checks). A builder writing a sound asks where it goes (place): where it is today, else
the folder for its kind (kind_of). The page gets them all in one folder (web/assets/sounds, tools/export_web_assets.py).
"""
import os

KINDS = ("ui", "creatures", "voices", "ambient", "skills", "combat", "magic", "world", "music")
EXTS = (".wav", ".mid", ".ogg", ".mp3")

# (a name's kind: its first word, or the whole name; anything else is the world's: doors, bells, boats, steps...)
_PREFIX = {
    "ui": ("Chat", "Click", "Coins", "Denied", "Empty", "Fail", "LevelUp", "Learn", "Pickup", "Drop", "Quest",
           "Success", "Swap", "Paper", "EatFood"),
    "creatures": ("Abomination", "Baa", "Bleat", "Buzz", "Cat", "Cluck", "Croak", "Dog", "Growl", "Honk", "Meow",
                  "Moo", "Otter", "Purr", "Quack", "Rabbit", "Seal_Bark", "Snort", "Squeak", "Kill", "Remnant_Rise",
                  "Hooves"),
    "voices": ("Voice", "Whisper"),
    "ambient": ("Ambient", "Thunder", "Thunderclap", "Hail", "Rumble"),
    "skills": ("Anvil", "Bellows", "Brew", "Cooked", "CookingFood", "Craft", "Crafted", "DigHole", "EmptyBucket", "FillBucket",
               "Gather", "Harvest", "Bloom_Harvest", "MakeFire", "Mine", "PutFireOut", "Rock_Chime", "Smelt",
               "StrikeFlint", "WoodChop", "Geode_Song", "Lockpick", "Sneak_Past"),
    "combat": ("Fight", "Block", "Crit", "Miss", "Hurt", "Death", "Stance", "Spotted"),
    "magic": ("Spell", "Absorb", "Shard", "Rare_Shard", "Enchant", "Fizzle", "Appear", "Vanish", "Mage_Blink",
              "Anchor_Shatter", "Chime", "Rune_Strike", "Seal_Break", "Terraform", "Cutting_Vision", "Dread", "Hush",
              "Mending", "Stone_Dormant", "Stone_Wake", "Sword_Wake", "Freeze", "Ysolde_Rest", "Portal", "Teleporter",
              "Fever"),
    "music": ("Music", "TownTheme"),
}


def kind_of(name):
    """The folder a new sound goes in, from its name (Growl_Troll_3: creatures; a tune: music)."""
    stem, ext = os.path.splitext(name)
    if ext.lower() not in EXTS:
        stem, ext = name, ""
    if ext.lower() in (".mid", ".ogg", ".mp3"):
        return "music"
    for kind, words in _PREFIX.items():
        for w in words:
            rest = stem[len(w):] if stem.startswith(w) else None
            if rest is not None and (not rest or rest[0] in "_0123456789" or rest[0].isupper()):
                return kind
    return "world"


_INDEX = {}


def index(root):
    """{file name: its path} of every sound under root\\sounds (looked at once; place() adds to it)."""
    if root not in _INDEX:
        found = {}
        top = os.path.join(root, "sounds")
        for d, _dirs, files in os.walk(top):
            for f in files:
                if os.path.splitext(f)[1].lower() in EXTS:
                    found.setdefault(f, os.path.join(d, f))
        _INDEX[root] = found
    return _INDEX[root]


def file_name(name):
    """Door -> Door.wav; Music_Town1.mid stays as it is."""
    return name if os.path.splitext(name)[1].lower() in EXTS else name + ".wav"


def find(root, name):
    """The path of the sound called name (bare means .wav), wherever it is, or None."""
    path = index(root).get(file_name(name))
    if path and not os.path.exists(path):
        path = None
    return path


def place(root, name):
    """Where a builder writes the sound called name: where it is now, else its kind's folder (made if need be)."""
    f = file_name(name)
    path = find(root, f)
    if not path:
        d = os.path.join(root, "sounds", kind_of(f))
        os.makedirs(d, exist_ok=True)
        path = os.path.join(d, f)
        index(root)[f] = path
    return path


def duplicates(root):
    """The names two sounds share (Door.wav in two folders, or Door.wav and Door.mid): [(name, [paths])]."""
    by = {}
    for d, _dirs, files in os.walk(os.path.join(root, "sounds")):
        for f in files:
            stem, ext = os.path.splitext(f)
            if ext.lower() in EXTS:
                by.setdefault(stem.lower(), []).append(os.path.relpath(os.path.join(d, f), root))
    return sorted((k, v) for k, v in by.items() if len(v) > 1)
