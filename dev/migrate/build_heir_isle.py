"""The heir's story on the Isle: the first four chapters of the main quest line (it replaces build_isle_quest.py's
Passage to the Mainland, the ticket book and the goblin's cage). Run it again: it draws and writes the same again.

  python -I "dev\\migrate\\build_heir_isle.py"

The story: your mother Mary, the Queen of Ashen in hiding, ran from the capital, Galaith, with you as a baby, to
save you from the dragon that takes the firstborn heir of every generation. You were raised on the Isle in poverty.
  1  The Last Will (LastWill 0-2; the letter tells you who you are, and little else: the rest you find). A new
     character stands at her grave in the chapel's graveyard (3,1,0's entry script runs The Funeral): the mourners
     go, Edwin the lawyer walks you home and leaves her letter on the table.
     The cottage door (a Lock) stays shut until it's read: the letter (Last_Will, Read) tells you who you are.
  2  Dinner at Edwin's (DinnerQuest 0-4). Maren, Edwin's wife and the Isle's doctor, at their brick house by the
     chapel (2,1,0: her surgery and his desk downstairs; their rooms upstairs, 2,1,1; it was the bank): three logs
     for her range (with an axe she lends you), an egg from Bess's coop fried on her range, the egg to Edwin.
     Maren gives you the key to the chapel's trapdoor (Chapel_Cellar_Key).
  3  The Amulet of Succession (AmuletQuest 0-6). Bess sends you to her husband Frank, the blacksmith (his hut by the
     dairy, 2,0,0): a wooden sword and shield at his workbench, then wield them. Brother Aldous opens the trapdoor
     to you when you're armed and Strength and Defence are level 2. The amulet is at the back of the caves (1,1,-2)
     behind bars; Aldous follows you down with a scroll of Grasp. He gives you the key of the hobgoblins' lair door.
  4  Passage to the Mainland (Passage 0-4, done at 5; a save from before, at 12, has it done too). Bess won't sail without her father
     Tobias's compass. His house (the old brick house, 1,1,0) is locked and the hobgoblins have the key. Their lair
     (2,2,-2), behind a locked door in the caves (2,1,-2): four hobgoblins (the entry script puts back the ones
     killed, when someone comes in again), the key in the corner barrel, Tobias in a cage you pick the lock of. A
     ladder up to their camp (2,2,0), in a tent: only a tent until you've climbed it from below. In the house, a
     floorboard squeaks: stand on it, search it, the compass. Bess sails you to Northport.
Characters made before this story keep what they had done (session.heir_story_from_old_save).

The Isle teaches the world as you go, in what people say and give you: Edwin hands over Mary's jar of Shards (the
world's magic: the count under your health); Maren gives healing draughts (herbs mend a body, Shards can't); Frank
gives his old dagger to break down for its Shard (Dismantle); Brother Aldous, in the caves, shows you a dead beast's
Shard Remnants (Absorb) and the scroll of Grasp (learnt for good, cast for Shards); Bess, at Northport, the shardstone.
"""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import story_kit as K  # noqa: E402
from story_kit import Map, obj_line, TW, say, ini  # noqa: E402

MAKER = "build_heir_isle.py"
GRAVE = (15, 4)                                  # Mary's grave, 3,1,0 (you stand below it)
COTTAGE = (5, 9, 12, 13)                         # the cottage, 4,0,0 (made wider: two beds)
COTTAGE_DOOR = 8
HOME = (12, 1, 21, 7)                            # Edwin and Maren's house, 2,1,0, their rooms upstairs on 2,1,1
HOME_DOOR = 16
SMITHY = (8, 3, 12, 7)                           # Frank's smithy, 2,0,0
FATHERS = (18, 3, 22, 7)                         # Tobias's house, 1,1,0 (the old brick house)
SQUEAK = (21, 6)                                 # its loose floorboard
NICHE = (5, 12)                                  # the amulet's niche, 1,1,-2 (where the goblin's cage was)
CAMP = (7, 3, 19, 13)                            # the hobgoblins' camp, 2,2,0
GATE = (13, 3)
TENT = (17, 10)                                  # the tent with the ladder; the ladder below it on 2,2,-2
CAGE = (19, 11)                                  # Tobias's cage in the lair
DOOR = (14, 19)                                  # the lair's door, 2,1,-2
KEY_BARREL = (5, 15)                             # the corner barrel with the house key, 2,2,-2
LAIR_HOBS = ((10, 8), (15, 13), (8, 12), (18, 7))


# ================================================================== pictures
def P(x, y):
    return int(x), int(y)


def letter():
    pg = K.pg()
    s = K.surface()
    paper, shade, line = (238, 228, 198), (204, 188, 150), (150, 130, 96)
    pg.draw.polygon(s, paper, [(5, 9), (27, 7), (28, 24), (6, 26)])
    pg.draw.polygon(s, shade, [(5, 9), (27, 7), (17, 17)])                 # the folded flap
    pg.draw.line(s, line, (5, 9), (17, 17))
    pg.draw.line(s, line, (27, 7), (17, 17))
    for y in (20, 22):
        pg.draw.line(s, line, (9, y + 1), (24, y))
    pg.draw.circle(s, (170, 26, 30), (17, 17), 4)                           # the wax seal
    pg.draw.circle(s, (210, 60, 60), (16, 16), 2)
    s.set_at((15, 15), (240, 140, 140))
    return K.outlined(s)


def amulet():
    pg = K.pg()
    s = K.surface()
    gold, dark, light = (214, 170, 54), (150, 110, 30), (250, 220, 120)
    for i in range(14):                                                      # the chain, in links
        t = i / 13.0
        x = 9 + 14 * t
        y = 4 + 9 * (1 - (2 * t - 1) ** 2)
        s.set_at(P(x, y + 1), gold if i % 2 else dark)
    pg.draw.line(s, dark, (9, 5), (13, 15))
    pg.draw.line(s, dark, (23, 5), (19, 15))
    pg.draw.circle(s, dark, (16, 21), 8)
    pg.draw.circle(s, gold, (16, 21), 7)
    pg.draw.circle(s, light, (15, 20), 5)
    pg.draw.circle(s, gold, (16, 21), 4)
    pg.draw.circle(s, (30, 70, 190), (16, 21), 3)                            # the sapphire
    pg.draw.circle(s, (90, 150, 250), (15, 20), 1)
    for x in (13, 16, 19):                                                   # a crown over it
        s.set_at((x, 15), light)
    pg.draw.line(s, light, (13, 16), (19, 16))
    return K.outlined(s)


def key(metal, light, ring_r=5):
    pg = K.pg()
    s = K.surface()
    pg.draw.circle(s, metal, (10, 16), ring_r, 2)
    pg.draw.line(s, metal, (14, 16), (27, 16), 2)
    pg.draw.line(s, light, (14, 15), (27, 15))
    pg.draw.rect(s, metal, (22, 17, 2, 4))
    pg.draw.rect(s, metal, (25, 17, 2, 3))
    s.set_at((8, 13), light)
    return K.outlined(s)


def compass():
    pg = K.pg()
    s = K.surface()
    brass, dark = (196, 152, 60), (130, 96, 32)
    pg.draw.circle(s, dark, (16, 17), 11)
    pg.draw.circle(s, brass, (16, 17), 10)
    pg.draw.circle(s, (238, 232, 214), (16, 17), 8)
    pg.draw.rect(s, brass, (14, 4, 5, 3))                                     # the ring at the top
    pg.draw.polygon(s, (200, 30, 30), [(16, 10), (18, 17), (14, 17)])        # north, red
    pg.draw.polygon(s, (50, 50, 60), [(16, 24), (18, 17), (14, 17)])
    s.set_at((16, 17), brass)
    for x, y in ((16, 9), (24, 17), (16, 25), (8, 17)):
        s.set_at((x, y), dark)
    return K.outlined(s)


def niche(with_amulet):
    pg = K.pg()
    s = K.surface()
    stone, dark, deep = (126, 122, 114), (86, 82, 76), (34, 30, 30)
    pg.draw.rect(s, stone, (2, 3, 28, 27))
    for y in (8, 15, 22):
        pg.draw.line(s, dark, (2, y), (29, y))
    pg.draw.rect(s, deep, (7, 7, 18, 21))
    pg.draw.ellipse(s, deep, (7, 3, 18, 10))                                 # (an arched alcove)
    if with_amulet:
        pg.draw.circle(s, (214, 170, 54), (16, 22), 3)
        pg.draw.circle(s, (60, 110, 230), (16, 22), 1)
        s.set_at((14, 20), (255, 240, 170))
        pg.draw.line(s, (150, 110, 30), (14, 19), (16, 16))
        pg.draw.line(s, (150, 110, 30), (18, 19), (16, 16))
    iron, lit = (64, 64, 72), (128, 128, 140)
    for x in (9, 13, 17, 21):
        pg.draw.line(s, iron, (x, 5), (x, 28), 2)
        pg.draw.line(s, lit, (x, 5), (x, 28))
    for y in (11, 24):
        pg.draw.line(s, iron, (7, y), (24, y), 2)
    return K.outlined(s)


def cage(person):
    pg = K.pg()
    s = K.surface()
    pg.draw.rect(s, (0, 0, 0, 80), (3, 28, 27, 3))
    pg.draw.rect(s, (56, 50, 46), (3, 25, 26, 4))
    if person is not None:
        s.blit(person, (0, -2))
    iron, lit = (58, 58, 64), (122, 122, 132)
    pg.draw.rect(s, iron, (3, 2, 26, 3))
    pg.draw.line(s, lit, (3, 2), (28, 2))
    xs = range(4, 29, 4) if person is not None else (4, 8, 24, 28)          # (open: the front bars swung away)
    for x in xs:
        pg.draw.line(s, iron, (x, 5), (x, 26), 2)
        pg.draw.line(s, lit, (x, 5), (x, 26))
    pg.draw.rect(s, iron, (3, 24, 26, 2))
    if person is not None:
        pg.draw.rect(s, (170, 140, 60), (15, 14, 4, 4))                       # the padlock
        pg.draw.arc(s, (170, 140, 60), (15, 11, 4, 6), 0, 3.14, 1)
    else:
        pg.draw.line(s, iron, (9, 6), (13, 25), 2)                           # the door, hanging open
    return K.outlined(s)


def smoke(k):
    """Frame k (0-3) of a chimney's smoke: puffs rising and spreading, 32 x 48."""
    pg = K.pg()
    s = K.surface(32, 48)
    for i in range(5):
        h = (k * 6 + i * 11) % 44                                            # (how far up this puff has risen)
        r = 3 + h // 9
        a = max(40, 190 - h * 3)
        x = 14 + int(4 * ((i * 7 + k * 3) % 5 - 2) * h / 44.0)
        y = 44 - h
        g = 150 + (i * 17) % 40
        pg.draw.circle(s, (g, g, g + 6, a), (x, y), r)
        pg.draw.circle(s, (g + 30, g + 30, g + 34, a), (x - 1, y - 1), max(1, r - 2))
    return s


def sleeping_cat():
    """Jimmy curled up asleep on the spare bed: his own Curl pose (build_cats.py), so he's the same cat, the same size."""
    return K.load("Entities", "Strawberry_Cat_Curl8")


def fresh_grave():
    pg = K.pg()
    s = K.surface()
    pg.draw.rect(s, (150, 150, 146), (10, 2, 12, 15), border_top_left_radius=6, border_top_right_radius=6)
    pg.draw.rect(s, (190, 190, 186), (11, 3, 10, 13), border_top_left_radius=5, border_top_right_radius=5)
    pg.draw.line(s, (120, 120, 116), (13, 8), (18, 8))                       # (her name, worn in)
    pg.draw.line(s, (120, 120, 116), (14, 11), (17, 11))
    pg.draw.ellipse(s, (82, 56, 34), (4, 15, 24, 14))                        # the fresh earth
    pg.draw.ellipse(s, (110, 76, 46), (6, 16, 20, 10))
    for x, y, c in ((9, 20, (240, 240, 240)), (13, 19, (220, 60, 70)), (17, 21, (250, 220, 90)),
                    (21, 19, (240, 240, 240)), (15, 23, (220, 60, 70)), (11, 23, (190, 120, 220))):
        pg.draw.circle(s, c, (x, y), 1)
        s.set_at((x, y + 2), (60, 120, 50))
    return K.outlined(s)


def loose_board():
    """A floorboard sticking up out of the planks: drawn over Plank001, the board one row up from its neighbours."""
    pg = K.pg()
    s = K.surface()
    plank = K.load("Tiles", "Plank001")
    for y in range(8, 16):
        for x in range(32):
            r, g, b, a = plank.get_at((x, y))
            s.set_at((x, y - 1), (min(255, r + 22), min(255, g + 16), min(255, b + 10), 255))
    pg.draw.line(s, (36, 22, 12), (0, 15), (31, 15))                         # the gap it left
    pg.draw.line(s, (36, 22, 12), (0, 16), (31, 16))
    for x in (5, 26):
        s.set_at((x, 9), (200, 200, 206))                                    # nails, popped
        s.set_at((x, 8), (150, 150, 160))
    return s


def double_bed():
    """Double_Bed001/002 (the head, left and right halves) and 003/004 (the foot): Bed001/002 widened."""
    out = []
    for src in ("Bed001", "Bed002"):
        b = K.load("Tiles", src)
        left, right = K.surface(), K.surface()
        for y in range(32):
            for x in range(32):
                left.set_at((x, y), b.get_at((x if x < 16 else x - 8, y)))
                right.set_at((x, y), b.get_at((8 + x if x < 16 else x, y)))
        out += [left, right]
    return out[0], out[1], out[2], out[3]


def desk():
    pg = K.pg()
    s = K.surface()
    wood, dark, light = (120, 76, 40), (78, 48, 24), (156, 104, 60)
    pg.draw.rect(s, dark, (2, 12, 28, 18))
    pg.draw.rect(s, wood, (2, 10, 28, 12))
    pg.draw.line(s, light, (2, 10), (29, 10))
    for x in (4, 26):
        pg.draw.rect(s, dark, (x, 22, 3, 8))
    pg.draw.rect(s, (60, 36, 18), (12, 23, 9, 5))                            # a drawer
    s.set_at((16, 25), (220, 190, 90))
    pg.draw.rect(s, (238, 230, 206), (6, 11, 9, 7))                          # papers
    pg.draw.line(s, (150, 140, 120), (7, 13), (13, 13))
    pg.draw.line(s, (150, 140, 120), (7, 15), (12, 15))
    pg.draw.rect(s, (30, 30, 40), (20, 12, 4, 4))                            # the inkwell and its quill
    pg.draw.line(s, (240, 240, 240), (23, 13), (27, 6))
    return K.outlined(s)


def dining_table():
    """Dining_Table001 (west half) and 002 (east half): one long table, plates and a candle on it."""
    pg = K.pg()
    halves = []
    for side in (0, 1):
        s = K.surface()
        wood, dark, light = (128, 82, 42), (82, 50, 24), (164, 112, 64)
        x0, x1 = (3, 32) if side == 0 else (0, 29)
        pg.draw.rect(s, dark, (x0, 12, x1 - x0, 16))
        pg.draw.rect(s, wood, (x0, 10, x1 - x0, 13))
        pg.draw.line(s, light, (x0, 10), (x1 - 1, 10))
        leg = 5 if side == 0 else 25
        pg.draw.rect(s, dark, (leg, 23, 3, 7))
        pg.draw.circle(s, (236, 236, 230), (16, 16), 4)                       # a plate
        pg.draw.circle(s, (200, 200, 196), (16, 16), 2)
        if side == 1:
            pg.draw.rect(s, (240, 230, 200), (4, 6, 2, 6))                    # a candle at the join
            s.set_at((4, 5), (255, 200, 60))
        halves.append(K.outlined(s))
    return halves


def draw_pictures():
    made = []
    for name, img in (("Last_Will", letter()), ("Amulet_of_Succession", amulet()),
                      ("Lair_Key", key((70, 70, 78), (140, 140, 150))),
                      ("Fathers_House_Key", key((184, 140, 52), (240, 206, 110))),
                      ("Fathers_Compass", compass()), ("Barred_Niche", niche(True)),
                      ("Barred_Niche_Empty", niche(False)),
                      ("Caged_Tobias", cage(K.load("Entities", "Tobias"))), ("Hob_Cage_Open", cage(None)),
                      ("Sleeping_Jimmy", sleeping_cat())):
        made += [name] if K.save("Entities", name, img) else []
    frames = [smoke(k) for k in range(4)]
    made += ["Chimney_Smoke"] if K.save("Entities", "Chimney_Smoke", frames[0]) else []
    for k, f in enumerate(frames, 1):
        K.save("Entities", "Chimney_Smoke%d" % k, f)
    beds = double_bed()
    tables = dining_table()
    for name, img in (("Fresh_Grave001", fresh_grave()), ("Loose_Floorboard001", loose_board()),
                      ("Double_Bed001", beds[0]), ("Double_Bed002", beds[1]), ("Double_Bed003", beds[2]),
                      ("Double_Bed004", beds[3]), ("Desk001", desk()), ("Dining_Table001", tables[0]),
                      ("Dining_Table002", tables[1])):
        made += [name] if K.save("Tiles", name, img) else []
    for new, old in (("Hidden_Ladder001", "Cave_Ladder001"), ("Hob_Tent001", "Tent002"),
                     ("Lair_Barrel001", "Barrel001")):
        K.copy_sprite("Tiles", old, new)
    print("Pictures: " + (", ".join(made) if made else "all as they were"))


# ================================================================== sounds
def make_sounds():
    import math
    rnd = random.Random(7)
    # a floorboard's squeak: a creaking glide up and down, rough
    creak = []
    n = int(K.RATE * 0.55)
    phase = 0.0
    for i in range(n):
        t = i / K.RATE
        f = 520 + 260 * math.sin(math.pi * t / 0.55) + 30 * math.sin(2 * math.pi * 23 * t)
        phase += 2 * math.pi * f / K.RATE
        saw = (phase / math.pi) % 2 - 1
        env = min(1.0, t / 0.03) * min(1.0, (0.55 - t) / 0.12) * (0.7 + 0.3 * math.sin(2 * math.pi * 31 * t))
        creak.append((0.6 * saw + 0.4 * math.sin(phase)) * env * 0.5 + rnd.uniform(-0.04, 0.04) * env)
    K.wav("Squeak", creak)
    # a lockpick: small metal clicks, unevenly spaced
    picks = []
    for gap in (0.12, 0.2, 0.09, 0.26, 0.14):
        click = [math.sin(2 * math.pi * 3200 * i / K.RATE) * math.exp(-i / 90.0) * 0.7 for i in range(int(K.RATE * 0.03))]
        picks += K.silence(gap) + click
    K.wav("Lockpick", picks)
    # a cage door: a hinge's long squeal, then the clang of it swinging open
    hinge = K.tone(780, 0.5, (0.6, 0.3, 0.2), attack=0.05, release=0.1, glide=-0.35, vibrato=0.04)
    clang = [sum(math.sin(2 * math.pi * f * i / K.RATE) for f in (310, 470, 900)) / 3 * math.exp(-i / 2600.0)
             for i in range(int(K.RATE * 0.7))]
    K.wav("Cage_Open", [v * 0.5 for v in hinge] + clang)
    # paper: a letter unfolded, a rustle of noise in two crinkles
    rustle = []
    for part in (0.18, 0.26):
        m = int(K.RATE * part)
        last = 0.0
        for i in range(m):
            last = 0.6 * last + 0.4 * rnd.uniform(-1, 1)
            rustle.append(last * math.sin(math.pi * i / m) * 0.6)
        rustle += K.silence(0.06)
    K.wav("Paper", rustle)
    print("Sounds: Squeak, Lockpick, Cage_Open, Paper")


# ================================================================== data
def data():
    E, T = K.ENTS, K.TILES
    items = [
        ("Last_Will", "Your mother's last will and testament, sealed with her wax.", "Read,Examine"),
        ("Amulet_of_Succession", "The Amulet of Ashen Succession: gold, a sapphire, the royal crown. Your mother "
         "hid it for you.", "Examine"),
        ("Lair_Key", "A heavy iron key: it opens the door the hobgoblins hold in the caves.", "Examine"),
        ("Fathers_House_Key", "Tobias's house key, brass and well worn.", "Examine"),
        ("Fathers_Compass", "Tobias's compass: brass, its needle always true. Bess won't sail without it.", "Examine"),
    ]
    for name, info, words in items:
        K.section(E, name, [("Type", "MapItem"), ("Use.Words", words), ("Examine.Info", info), ("Stackable", "1"),
                            ("Droppable", "0"), ("Value", "0")])
    objects = [
        ("Barred_Niche", "Reach In,Examine", "An alcove in the rock behind iron bars. Something gold glints inside."),
        ("Barred_Niche_Empty", "Examine", "An alcove in the rock behind iron bars. It's empty now."),
        ("Caged_Tobias", "Talk to,Pick Lock,Examine", "An old man, locked in the hobgoblins' cage."),
        ("Hob_Cage_Open", "Examine", "The hobgoblins' cage, its door hanging open."),
        ("Sleeping_Jimmy", "Stroke,Examine", "Jimmy, curled up asleep on the spare bed."),
    ]
    for name, words, info in objects:
        K.section(E, name, [("Type", "StaticObject"), ("Use.Words", words), ("Examine.Info", info), ("Solid", "1")])
    K.section(E, "Sleeping_Jimmy", [("Solid", "0"), ("Schedule", "Night")])
    K.section(E, "Chimney_Smoke", [("Type", "StaticObject"), ("Use.Words", ""), ("Examine.Info", "Smoke from the forge."),
                                   ("Solid", "0"), ("Layer", "Over"), ("Anim.Frames", "4"), ("Anim.Speed", "260"),
                                   ("Schedule", "Day")])
    K.people_sections()
    K.section(E, "Woman", [("Examine.Info", "A woman of the town.")])
    # the tiles
    K.copy_tile("Fresh_Grave001", "Grave001", Examine_Info="A fresh grave, the earth still dark. Flowers lie on it.",
                Use_Words="Examine", Layer="Decor")
    K.copy_tile("Loose_Floorboard001", "Plank001", Use_Words="Search,Examine", Show_Name="1", Layer="Decor",
                Examine_Info="A floorboard, loose and sticking up.")
    for n, src, half in (("Double_Bed001", "Bed001", "left"), ("Double_Bed002", "Bed001", "right"),
                         ("Double_Bed003", "Bed002", "left"), ("Double_Bed004", "Bed002", "right")):
        K.copy_tile(n, src, Examine_Info="A big double bed.", Piece="a double bed: the %s of its %s" % (
            half, "head" if src == "Bed001" else "foot"))
    K.copy_tile("Desk001", "Table001", Examine_Info="A writing desk: papers, an inkwell and a quill.", Use_Words="Examine")
    for n in ("Dining_Table001", "Dining_Table002"):
        K.copy_tile(n, "Table001", Examine_Info="A long dining table, laid for supper.", Use_Words="Examine")
    K.copy_tile("Hidden_Ladder001", "Cave_Ladder001", Use_Words="Climb Up,Examine",
                Examine_Info="A rope ladder, hidden in a cleft, going up into the dark.")
    K.copy_tile("Hob_Tent001", "Tent002", Use_Words="Enter,Examine", Examine_Info="A grubby hide tent.")
    K.copy_tile("Lair_Barrel001", "Barrel001", Use_Words="Search,Examine", Examine_Info="A hobgoblin's barrel.")
    for t, rgb in (("Fresh_Grave001", (110, 76, 46)), ("Loose_Floorboard001", (176, 124, 76)),
                   ("Double_Bed001", (200, 50, 50)), ("Double_Bed002", (200, 50, 50)),
                   ("Double_Bed003", (200, 50, 50)), ("Double_Bed004", (200, 50, 50)), ("Desk001", (120, 76, 40)),
                   ("Dining_Table001", (128, 82, 42)), ("Dining_Table002", (128, 82, 42)),
                   ("Hidden_Ladder001", (255, 0, 0)), ("Hob_Tent001", (150, 120, 80)),
                   ("Lair_Barrel001", (120, 80, 40))):
        K.minimap_colour(t, rgb)
    # the quests
    K.remove_section(K.QUESTS, "The Beggar's Lost Key")
    K.quest("The Last Will", "Edwin", "LastWill", {
        0: "",
        1: "Read the letter your mother left you, on the table in your cottage.",
    }, 2, markers={1: "Cottage"}, chapter=1, marker0="Cottage", after=None)
    K.remove_section(K.QUESTS, "Dinner at the Bank")              # (the house was the bank: renames.py QUEST_NAMES)
    K.quest("Dinner at Edwin's", "Maren", "DinnerQuest", {
        0: "Edwin the lawyer asked you to dinner. He and his wife Maren, the Isle's doctor, live in the brick house "
           "by the chapel.",
        1: "Chop 3 logs for Maren's range with the axe she lent you (Chop a tree), and bring them to her.",
        2: "Take an egg from the hen coop on Bess's farm, in the north, and fry it on Maren's range, upstairs in their "
           "house (use the egg on the range).",
        3: "Give the fried egg to Edwin, at his house.",
    }, 4, markers={0: "Isle_Bank", 1: "Isle_Bank", 2: "Hen_Coop", 3: "Isle_Bank"}, chapter=2,
        requires="The Last Will", marker0="Isle_Bank")
    K.quest("The Amulet of Succession", "Milkmaid", "AmuletQuest", {
        0: "Bess the milkmaid, on the farm in the north, knew your mother well.",
        1: "Bess's husband Frank, the blacksmith, will help you make a sword and a shield. His smithy is by the dairy.",
        2: "Make a wooden sword and a wooden shield at Frank's workbench, then show them to him.",
        3: "Wield your sword and shield, and train until your Strength and Defence are level 2. Then ask Brother "
           "Aldous, at the chapel, about the trapdoor in its cellar.",
        4: "Something of your mother's lies in the caves under the chapel.",
        5: "Something gold glints behind iron bars, out of reach of any hand.",
    }, 6, markers={0: "Milkmaid_Farm", 1: "Franks_Smithy", 2: "Franks_Smithy", 3: "Chapel_Door",
                   4: "Amulet_Niche", 5: "Amulet_Niche"}, chapter=3, requires="The Last Will")
    K.quest("Passage to the Mainland", "Milkmaid", "Passage", {
        0: "Bess the milkmaid, on the farm in the north, has the only boat that crosses to the mainland.",
        1: "Find Bess's father's compass. His house in the village is locked, and the hobgoblins have its key: their "
           "lair is in the caves under the chapel.",
        2: "Bess's father, Tobias, is locked in a cage in the hobgoblins' lair. Pick its lock to free him. His house "
           "key is hidden in one of the lair's barrels.",
        3: "Tobias has given you his house. Unlock it with his key and find the compass he hid there.",
        4: "Give Tobias's compass to Bess, on the farm.",
    }, 5, markers={0: "Milkmaid_Farm", 1: "Hobgoblin_Lair", 2: "Hobgoblin_Lair", 3: "Fathers_House",
                    4: "Milkmaid_Farm"}, chapter=4, requires="The Last Will")
    # a new character begins at the graveyard (dying still wakes you in the cottage: Config's Start.Map)
    tpl = os.path.join(K.ROOT, "saves", "TEMPLATE.ini")
    for k, v in (("Map", "3,1,0"), ("X", str((GRAVE[0] - 1) * TW)), ("Y", str(GRAVE[1] * TW - 4)), ("Direction", "1")):
        if ini.read("Player", k, "<unset>", tpl) != v:
            ini.write("Player", k, v, tpl)
    K.drop_label("Places", "The Isle Bank")
    K.place_label("Places", "Edwin & Maren's House", "Isle_Bank")
    K.place_label("Places", "Frank's Smithy", "Franks_Smithy")
    K.place_label("Places", "Maren & Bess's Father's Home", "Fathers_House")
    K.place_label("Places", "Hobgoblin Camp", "Hobgoblin_Camp")
    print("Data: the Isle's items, people and tiles; its four quests; a new character starts at the graveyard")


# ================================================================== maps
def px(x, y, dy=0):
    """A tile's top-left in pixels (1-based tiles), for map lines and scripts."""
    return (x - 1) * TW, (y - 1) * TW + dy


def at(x, y, dy=0):
    return "%d,%d" % px(x, y, dy)


def grave():
    m = Map("3,1,0")
    if K.has_id(m, "Mothers_Grave"):
        return
    gx, gy = GRAVE
    m.set(gx, gy, decor="Fresh_Grave001")
    m.set(gx, gy + 1, decor="")
    K.place_id(m, "Mothers_Grave", gx, gy)
    K.place_id(m, "Funeral_Spot", gx, gy + 1)
    m.save()
    print("3,1,0: Mary's grave, fresh, in the chapel's graveyard")


def cottage():
    m = Map("4,0,0")
    x1, y1, x2, y2 = COTTAGE
    if m.tile(x2, y1) == "Timber_Thin_Plank005":
        return
    K.building(m, x1, y1, x2, y2, COTTAGE_DOOR, wall="Timber001", roof="Thatch")
    for (x, y), d in {(6, 9): "Bed001", (6, 10): "Bed002", (7, 9): "Bed001", (7, 10): "Bed002",      # yours; Jimmy's
                      (9, 9): "Bookshelf001", (9, 11): "Table001", (8, 11): "Chair003", (10, 11): "Chair004",
                      (11, 12): "Potted_Plant001"}.items():
        m.set(x, y, decor=d)
    for x, rugpiece in ((8, "Rug011"), (9, "Rug012"), (10, "Rug013")):
        t, over = m.parts(x, 11)
        over["Under"] = rugpiece
        m.put(x, 11, t, over)
    for x, y in ((8, 14), (8, 15)):
        m.set(x, y, tile="Dirt001", decor="")
    keep = []
    for ln in m.ents:
        f = ln.split("\t")
        if f[:2] == ["StaticObject", "Range"]:
            ln = obj_line("StaticObject", "Range", 11, 9)
        elif f[:2] == ["StaticObject", "Notice"]:
            ln = "StaticObject\tNotice\t%d\t418\tId=Cottage_Notice" % px(9, 1)[0]
        elif f[:2] == ["Id", "Cottage"]:
            ln = "Id\tCottage\t9\t12"
        elif f[:2] == ["Id", "Cottage_Door"]:
            ln = "Id\tCottage_Door\t%d\t14" % COTTAGE_DOOR
        elif f[:2] == ["NPC", "Strawberry_Cat"]:
            ln = "NPC\tStrawberry_Cat\t%d\t%d\tAttitude=Good Zone=6,10,11,12 Pause=6-15 Schedule=Day Id=Jimmy Name=Jimmy" % \
                 px(10, 12, -8)
        elif f[0] == "Lock":
            continue
        keep.append(ln)
    keep.append("StaticObject\tSleeping_Jimmy\t%d\t%d" % px(7, 10, -14))
    keep.append("Lock\t%d\t%d\t$Attr.LastWill<>1\tYou should read your mother's letter before you go out." %
                (COTTAGE_DOOR, y2))
    m.ents = keep
    m.save()
    print("4,0,0: the cottage, wider: your bed and a spare one (Jimmy's, at night), the table, the range")


def rug(m, x0, y0, w, h, kind):
    """A rug (interior_tiles' pieces: <kind>001-017) under whatever stands there."""
    import villages as V
    for j in range(h):
        for i in range(w):
            t, over = m.parts(x0 + i, y0 + j)
            over["Under"] = "%s%03d" % (kind, 1 + V.rug_piece(i, j, w, h))
            m.put(x0 + i, y0 + j, t, over)


def front_room(m):
    """Downstairs: Maren's surgery (a bed for the sick, her bottles and drying herbs) and Edwin's desk and law books.
    (It was the bank: a house built then has its counter and plaque taken away.)"""
    for (x, y), d in {(13, 1): "Potion_Shelf001", (14, 1): "Bed001", (14, 2): "Bed002", (15, 1): "Bookshelf001",
                      (16, 1): "Herb_Rack001", (17, 1): "Potted_Plant002", (13, 4): "", (14, 4): "", (15, 4): "",
                      (18, 3): "Desk001", (18, 2): "Chair001", (18, 4): "Chair002", (13, 6): "Potted_Plant001",
                      (20, 6): "Potted_Plant003", (18, HOME[3]): ""}.items():
        m.set(x, y, decor=d)


def home():
    m, up = Map("2,1,0"), K.black_map("2,1,1")
    x1, y1, x2, y2 = HOME
    if K.has_id(m, "Isle_Bank"):
        if m.parts(14, 1)[1].get("Decor") != "Bed001":
            front_room(m)
            m.save()
            print("2,1,0: the bank is Edwin and Maren's house now")
        return
    K.building(m, x1, y1, x2, y2, HOME_DOOR, wall="Brick001", roof="Slate", chimney=19, upper=up)
    front_room(m)
    m.set(20, 2, tile="Stairs001")
    rug(m, 15, 5, 4, 2, "Rug")
    for y in range(y2 + 1, y2 + 4):                             # a path down to the Isle's path
        m.set(HOME_DOOR, y, tile="Dirt001", decor="")
    m.ents += [
        obj_line("NPC", "Maren", 14, 3, "Attitude=Good Stand=1 Face=S Schedule=Day Id=Maren_At_Counter", -8),
        obj_line("NPC", "Edwin", 18, 2, "Attitude=Good Stand=1 Face=S Schedule=Day Id=Edwin_At_Desk", -8),
        "StaticObject\tNotice\t%d\t%d\tId=Isle_Bank_Notice" % px(15, 8, 2),
    ]
    K.place_id(m, "Isle_Bank", HOME_DOOR, y2 + 1)
    m.save()
    # upstairs, their home: the bedroom (west) and the kitchen and dining room (east), a wall between with a doorway
    K.partition(up, 16, 2, 5, gaps=(4,))
    for (x, y), d in {(13, 1): "Double_Bed001", (14, 1): "Double_Bed002", (13, 2): "Double_Bed003",
                      (14, 2): "Double_Bed004", (15, 1): "Bookshelf001", (13, 5): "Potted_Plant004",
                      (17, 1): "Shelf_Goods001", (18, 4): "Dining_Table001", (19, 4): "Dining_Table002",
                      (17, 4): "Chair003", (20, 4): "Chair004", (18, 5): "Chair002", (19, 5): "Chair002"}.items():
        up.set(x, y, decor=d)
    up.set(20, 2, tile="Stairs002")
    rug(up, 14, 3, 2, 2, "Rug")
    up.ents = [ln for ln in up.ents if "Marens_Range" not in ln and "_At_Home" not in ln]
    up.ents += [
        obj_line("StaticObject", "Range", 18, 1, "Id=Marens_Range"),
        obj_line("NPC", "Maren", 14, 3, "Attitude=Good Stand=1 Face=S Schedule=Night Id=Maren_At_Home", -8),
        obj_line("NPC", "Edwin", 15, 4, "Attitude=Good Stand=1 Face=S Schedule=Night Id=Edwin_At_Home", -8),
    ]
    up.save()
    print("2,1,0 and 2,1,1: Edwin and Maren's house, two storeys of brick: her surgery and his desk, their rooms "
          "upstairs")


def smithy():
    m = Map("2,0,0")
    if K.has_id(m, "Franks_Smithy"):
        return
    x1, y1, x2, y2 = SMITHY
    K.building(m, x1, y1, x2, y2, 10, wall="Stone_Wall001", roof="Slate", windows=(9, 11), chimney=11)
    m.set(10, y2 + 1, tile="Dirt001", decor="")
    ents = []
    for ln in m.ents:
        if ln.split("\t")[:2] == ["StaticObject", "Sign_Dairy"]:
            ln = "StaticObject\tSign_Dairy\t%d\t208" % px(7, 1)[0]          # (beside Bess's hut, not the smithy's wall)
        ents.append(ln)
    ents += [
        obj_line("StaticObject", "Furnace", 9, 3),
        obj_line("StaticObject", "Workbench", 11, 3, "Id=Franks_Workbench"),
        obj_line("StaticObject", "Anvil", 11, 5),
        obj_line("NPC", "Frank", 10, 4, "Attitude=Good Stand=1 Face=S Schedule=Day Id=Frank_At_Forge", -8),
        "StaticObject\tChimney_Smoke\t%d\t56" % px(11, 1)[0],                # (over the chimney on the ridge)
        "StaticObject\tSign_Smithy\t%d\t208" % px(13, 1)[0],
    ]
    m.ents = ents
    K.place_id(m, "Franks_Smithy", 10, y2 + 1)
    m.save()
    print("2,0,0: Frank's smithy by the dairy: furnace, anvil, workbench; smoke from its chimney by day")


def fathers_house():
    m = Map("1,1,0")
    x1, y1, x2, y2 = FATHERS
    before = list(m.ents), list(map(list, m.rows))
    if not K.has_id(m, "Fathers_House"):
        for y in range(y1, y2 + 1):                              # the old brick house, brick again
            for x in range(x1, x2 + 1):
                t, over = m.parts(x, y)
                t = t.replace("Timber_Thin_Plank", "Brick_Thin_Plank").replace("Timber001", "Brick001")
                if over.get("Decor", "").startswith("Timber_Window"):
                    over["Decor"] = over["Decor"].replace("Timber", "Brick")
                if over.get("Roof"):
                    over["Roof"] = over["Roof"].replace("Thatch_Roof", "Slate_Roof")
                m.put(x, y, t, over)
        for x in (19, 21):
            m.set(x, y2, decor="Brick_Window001")
        K.place_id(m, "Fathers_House", x1 + 2, y2 + 1)
    ents = []                                                    # (its notice, lock and floorboard: made so each run)
    for ln in m.ents:
        f = ln.split("\t")
        if f[0] == "Trigger" and f[1] in ("Beggar House", "Squeaky Floorboard"):
            continue
        if f[0] == "Lock" and f[1:3] == [str(x1 + 2), str(y2)]:
            continue
        if f[:2] == ["StaticObject", "Notice"] and "Id=The_Old_Brick_House" in ln:
            ln = ln.replace("Id=The_Old_Brick_House", "Id=Fathers_Home")
        ents.append(ln)
    ents += ["Trigger\tSqueaky Floorboard\t%d\t%d" % SQUEAK,
             "Lock\t%d\t%d\t$Item.Fathers_House_Key>=1 or $Item.Beggars_House_Key>=1\tThe door is locked." % (x1 + 2, y2)]
    m.ents = ents
    if (m.ents, m.rows) != before:
        m.save()
        print("1,1,0: Maren and Bess's father's home, the old brick house: brick again, locked, a squeaky floorboard")


def camp():
    m = Map("2,2,0")
    if K.has_id(m, "Hobgoblin_Camp"):
        return
    x1, y1, x2, y2 = CAMP
    for y in range(y1, y2 + 1):                                  # (Palisade001 all round: build_palisades.py joins it)
        for x in range(x1, x2 + 1):
            if (x in (x1, x2) or y in (y1, y2)) and (x, y) != GATE:
                m.set(x, y, tile="Grass001", decor="Palisade001")
            elif m.decor(x, y) and not m.decor(x, y).startswith(("Flowers", "Pebbles", "Tall_Grass", "Grass_Tuft")):
                m.set(x, y, decor="")
    for x, y in ((GATE[0], GATE[1] - 1), GATE, (GATE[0], GATE[1] + 1)):
        m.set(x, y, tile="Dirt001", decor="")
    for (x, y), d in {(9, 5): "Tent002", (12, 5): "Tent001", (16, 5): "Tent002", (9, 10): "Tent002",
                      TENT: "Hob_Tent001", (10, 7): "Sacks001", (15, 11): "Sacks001", (18, 4): "Crate001",
                      (18, 12): "Barrel001", (8, 12): "Crate001"}.items():
        m.set(x, y, decor=d)
    m.ents = [ln for ln in m.ents if ln.split("\t")[:2] != ["NPC", "Goblin"]]
    m.ents += [obj_line("NPC", "Hobgoblin", 12, 9, "Attitude=Bad Zone=8,4,18,12", -8),
               obj_line("NPC", "Hobgoblin", 15, 8, "Attitude=Bad Zone=8,4,18,12", -8)]
    K.place_id(m, "Hobgoblin_Camp", 13, 8)
    K.place_id(m, "Hob_Camp_Tent", *TENT)
    m.save()
    print("2,2,0: the hobgoblins' camp, a palisade of sharpened logs round it; one tent hides a ladder")


def lair():
    """The lair (2,2,-2): a cavern down a tunnel from the caves' door, its ladder under the camp's tent."""
    import math
    tunnel = Map("2,1,-2")
    dx, dy = DOOR
    if tunnel.tile(dx, dy) != "Door002":
        for y in range(dy - 1, 22):
            for x in (dx - 1, dx, dx + 1):
                if x == dx:
                    tunnel.set(x, y, tile="Door002" if y == dy else "Cave_Floor001", decor="")
                elif tunnel.tile(x, y) == "Black001":
                    tunnel.set(x, y, tile="Cave_Wall001", decor="")
        tunnel.ents = [ln for ln in tunnel.ents if not ln.startswith("Lock\t%d\t%d\t" % DOOR)]
        tunnel.ents.append("Lock\t%d\t%d\t$Item.Lair_Key>=1\tThe door is locked." % DOOR)
        K.place_id(tunnel, "Lair_Door", dx, dy - 1)
        tunnel.save()
        print("2,1,-2: a door in the caves' south wall, and a tunnel beyond it")
    if K.map_exists("2,2,-2"):
        return
    rnd = random.Random(2226)
    m = Map("2,2,-2", new=True)
    floor = set()
    ph = [rnd.uniform(0, 6.3) for _ in range(3)]
    for y in range(1, 22):
        for x in range(1, 26):
            a = math.atan2(y - 11, x - 12.5)
            edge = 1 + 0.1 * math.sin(3 * a + ph[0]) + 0.07 * math.sin(5 * a + ph[1]) + 0.05 * math.sin(7 * a + ph[2])
            if ((x - 12.5) / 9.8) ** 2 + ((y - 11) / 7.2) ** 2 <= edge * edge:
                floor.add((x, y))
    floor |= {(dx, y) for y in range(1, 6)} | {(dx + i, y) for y in (4, 5) for i in (-1, 1)}
    for need in (TENT, CAGE, KEY_BARREL) + LAIR_HOBS:
        assert need in floor, need
    for y in range(1, 22):
        for x in range(1, 26):
            if (x, y) in floor:
                m.set(x, y, tile=rnd.choice(["Cave_Floor001"] * 6 + ["Cave_Floor003"] * 3 + ["Cave_Floor002"] * 2))
            elif any((x + i, y + j) in floor for i in (-1, 0, 1) for j in (-1, 0, 1)):
                m.set(x, y, tile=rnd.choice(("Cave_Wall001", "Cave_Wall001", "Cave_Wall002")))
    for (x, y), d in {TENT: "Hidden_Ladder001", KEY_BARREL: "Lair_Barrel001", (6, 16): "Lair_Barrel001",
                      (4, 13): "Lair_Barrel001", (7, 17): "Crate001", (20, 15): "Crate001", (21, 13): "Lair_Barrel001",
                      (9, 6): "Sacks001", (11, 5): "Sacks001", (16, 15): "Sacks001", (8, 9): "Crate001"}.items():
        if (x, y) in floor:
            m.set(x, y, decor=d)
    for x, y in ((8, 4), (17, 4), (4, 9)):                       # torches on the walls, where the floor meets them
        if (x, y) not in floor and m.tile(x, y).startswith("Cave_Wall"):
            m.set(x, y, decor="Wall_Torch001")
    m.ents = ["StaticObject\tFire\t%d\t%d" % px(12, 11),
              "MapItem\tBones\t%d\t%d\t1" % px(6, 8), "MapItem\tBones\t%d\t%d\t1" % px(17, 16)]
    K.place_id(m, "Hobgoblin_Lair", 13, 10)
    K.place_id(m, "Lair_Corner_Barrel", *KEY_BARREL)
    K.place_id(m, "Lair_Ladder", *TENT)
    m.save()
    print("Made maps\\2,2,-2.txt: the hobgoblins' lair")


def niche_and_pier():
    c = Map("1,1,-2")
    if not K.has_id(c, "Amulet_Niche"):
        ents = []
        for ln in c.ents:
            f = ln.split("\t")
            if f[:2] == ["StaticObject", "Goblin_Cage"] or f[:2] == ["Id", "Thief_Cage"]:
                continue
            ents.append(ln.replace(" Name=Goblin_Thief", ""))
        c.ents = ents
        K.place_id(c, "Amulet_Niche", NICHE[0] + 1, NICHE[1])
        c.save()
        print("1,1,-2: the goblin's cage gone; the amulet's niche at the back of the caves (its entry script puts it)")
    s = Map("1,3,0")
    if any(ln.startswith("NPC\tWoman\t") and "Name=Maren" in ln for ln in s.ents):
        s.ents = [ln.replace("NPC\tWoman\t", "NPC\tFerryman\t").replace("Name=Maren", "Name=Wim")
                  if ln.startswith("NPC\tWoman\t") and "Name=Maren" in ln else ln for ln in s.ents]
        s.save()
        print("1,3,0: Wim the ferryman on Northport's pier")
    k = Map("2,4,-2")
    if K.ents_without(k, lambda f: f[:2] == ["MapItem", "Beggars_House_Key"]):
        k.save()
        print("2,4,-2: the beggar's key is gone (his quest with it)")


def maps():
    grave()
    cottage()
    home()
    smithy()
    fathers_house()
    camp()
    lair()
    niche_and_pier()
    amb = os.path.join(K.DATA, "Ambient.ini")
    for name, sound in (("2,2,-2", "Cave"), ("2,1,1", "Indoors")):
        if ini.read("Maps", name, "<unset>", amb) != sound:
            ini.write("Maps", name, sound, amb)


# ================================================================== scripts
V1, V2, V3 = "Variable.1$", "Variable.2$", "Variable.3$"
FAR = [("@far",), ("Display.Message", "DarkRed", "You are too far away!", "Denied"), ("End",)]


def w(name, rows):
    K.write_script(name, rows, MAKER)


def notice(pid, title, text, cond=None, alt=None):
    """A notice's Read script (64 pixels to read it); cond: a condition under which alt is read instead."""
    rows = [(">Distance.From.Clicked.Entity", "64", "@far")]
    if cond:
        rows.append((">Conditional", cond, "@alt"))
    rows += [say("Notice", "%s\\%s" % (title, text), ("Okay", "@end")), ("End",)]
    if cond:
        rows += [("@alt",), say("Notice", "%s\\%s" % (title, alt), ("Okay", "@end")), ("End",)]
    w("Read " + pid, rows + [("@end",), ("End",)] + FAR)


def opening():
    """The funeral (3,1,0's entry script, for a character who's never been: LastWill 0), the walk home, the letter."""
    gx, gy = GRAVE
    w("3,1,0", [
        ("Get.Value", "ATTRIBUTE", "LastWill", V1),
        (">Conditional", "$Variable.1=0", "@end"),
        ("Goto.Script", "The Funeral"),
        ("@end",), ("End",),
    ])
    mourners = [("Mourner", gx - 1, gy + 1, "N"), ("Villager", gx + 1, gy + 2, "N"), ("Farmer", gx - 1, gy + 2, "N")]
    rows = [
        ("Toggle.User.Input", "OFF"),
        ("Get.Value", "ATTRIBUTE", "LastWill", V1),                  # (what's added from here is this player's alone)
        ("Teleport", at(gx, gy + 1, -4), "3,1,0"),
        ("Add.Entity", at(gx + 1, gy + 1, -8), "Edwin", "NPC", "Attitude=Good Stand=1 Face=W"),
    ]
    rows += [("Add.Entity", at(x, y, -8), who, "NPC", "Attitude=Good Stand=1 Face=%s" % f) for who, x, y, f in mourners]
    rows += [
        ("Play.Sound", "Bell"),
        ("Display.Message", "Cyan", "The chapel bell tolls for Mary. The last of the mourners lay their flowers on her "
                                    "grave.", "-"),
        ("Wait", "3"),
        say("Mourner", "She was a good woman, your mother. Kind to all of us, and never a word about herself.",
            ("Thank you.", "@go")),
        ("@go",),
    ]
    for who, x, y, f in mourners:                                # (they go home, out of the graveyard's gate)
        rows += [("Move.Entity", at(x, y, -8), who, at(22, 3, -8), "3"), ("Remove.Entity", at(x, y, -8), who)]
    rows += [
        say("Edwin", "I'm so sorry. Mary was a friend to all of us here.\\Come: I'll walk you home. She left something "
                     "for you, and it's to be given to you alone.", ("Lead the way.", "@walk")),
        ("@walk",),
        ("Remove.Entity", at(gx + 1, gy + 1, -8), "Edwin"),
        ("Display.Message", "Cyan", "You walk home together across the Isle, neither of you saying much.", "-"),
        ("Teleport", at(8, 11, -8), "4,0,0"),
        ("Wait", "1"),
        ("Add.Entity", at(10, 11, -8), "Edwin", "NPC", "Attitude=Good Stand=1 Face=W"),
        ("Wait", "1"),
        say("Edwin", "Your mother entrusted me with her last will and testament. She told me never to open this letter, "
                     "and said you should not read it to anyone. It's her last words to you, and only you.",
            ("...", "@letter")),
        ("@letter",),
        ("Add.Entity", at(9, 11, -6), "Last_Will", "MapItem", "1"),
        ("Play.Sound", "Paper"),
        ("Display.Message", "Cyan", "He lays a letter on the table, sealed with your mother's wax.", "-"),
        say("Player", "Thank you. If you don't mind, I would like to be left alone to read the letter.",
            ("Continue", "@leave")),
        ("@leave",),
        ("Move.Entity", at(10, 11, -8), "Edwin", at(COTTAGE_DOOR, 12, -8), "2"),
        say("Edwin", "Of course. If you need anything, you can find my wife, Maren, and me at our house, by the chapel. "
                     "Come for dinner.", ("Thank you, Edwin.", "@jar")),
        ("@jar",),
        say("Edwin", "Oh, and this. Mary kept a little jar of Shards on the mantel: she'd want you to have them.\\Shards "
                     "are splinters of the world's old magic. Spells drink them, and so do the old standing stones on "
                     "the mainland. Don't spend them all at once.", ("I won't.", "@out")),
        ("@out",),
        ("Play.Sound", "Absorb"),
        ("Display.Message", "Cyan", "Mary's Shards are yours: their count is under your health.", "-"),
        ("Remove.Entity", at(10, 11, -8), "Edwin"),
        ("Play.Sound", "Door"),
        ("Display.Message", "Cyan", "He lets himself out, and the door shuts behind him.", "-"),
        ("Update.Attribute", "LastWill", "=1"),
        ("Display.Message", "Yellow", "Quest started: The Last Will. (H: your journal)", "Quest"),
        ("Toggle.User.Input", "ON"),
        ("End",),
    ]
    w("The Funeral", rows)
    w("4,0,0", [                                                  # (the letter is on the table until it's read:
        ("Get.Value", "ATTRIBUTE", "LastWill", V1),                 # their own things go when they leave the game)
        (">Conditional", "$Variable.1<=1", "@end"),
        (">Not.Got.Item", "Last_Will", "1", "@end"),
        (">Conditional", "$Variable.1=0", "@letter"),
        ("Update.Attribute", "LastWill", "=1"),                    # (gone in the middle of the funeral: it's over)
        ("@letter",),
        ("Add.Entity", at(9, 11, -6), "Last_Will", "MapItem", "1"),
        ("@end",), ("End",),
    ])
    w("Examine Mothers_Grave", [
        ("Display.Message", "Black", "'Mary. Beloved mother.' The earth is still fresh, and the flowers on it."),
        ("End",),
    ])
    w("Pickup Last_Will", [
        (">Distance.From.Clicked.Entity", "48", "@far"),
        ("Remove.Entity", "$Object.under.Cursor.X,$Object.under.Cursor.Y", "Last_Will"),
        ("Give.Item", "Last_Will", "1"),
        ("Play.Sound", "Paper"),
        say("Last_Will", "Your mother's letter, sealed with her wax. Read it now?", ("Read it.", "@read"),
            ("Later.", "@end")),
        ("@read",), ("Goto.Script", "Read Last_Will"),
        ("@end",), ("End",),
    ] + FAR)
    w("Read Last_Will", [
        ("Play.Sound", "Paper"),
        say("Last_Will", "THE LAST WILL AND TESTAMENT OF MARY\\My beloved $Player.Son,\\We have lived in poverty on this island "
                         "since you were six months old; this is not what your life should have been like. You are the "
                         "true heir of Ashen, and its riches, lands and people are yours to protect.",
            ("Read on.", "@p2")),
        ("@p2",),
        say("Last_Will", "I could never tell you who we were while I lived: it was safer that you didn't know. I "
                         "didn't leave Galaith with nothing. What I carried away, I hid, and the people of this island "
                         "have kept my secrets for you. When you are ready, they will see that you find it.",
            ("Read on.", "@p3")),
        ("@p3",),
        say("Last_Will", "Your father, the king, still waits behind the walls of Galaith, and he doesn't know that I am "
                         "gone. Go to him. The city has been shut since the day you were born, and I am the reason "
                         "why. One day you will understand.\\Be careful, and tell your father I never stopped loving "
                         "him.\\Mary",
            ("Fold the letter.", "@done")),
        ("@done",),
        ("Get.Value", "ATTRIBUTE", "LastWill", V1),
        (">Conditional", "$Variable.1<2", "@end"),
        ("Update.Attribute", "LastWill", "=2"),
        ("Display.Message", "Yellow", "Quest complete: The Last Will.", "Quest"),
        ("Display.Message", "Cyan", "The door to your house is unlocked now, and the Isle lies before you.", "-"),
        ("@end",), ("End",),
    ])
    w("Stroke Sleeping_Jimmy", [
        ("Play.Sound", "Purr"),
        ("Display.Message", "Cyan", "Jimmy stretches, purrs without waking, and curls up tighter on the spare bed."),
        ("End",),
    ])


def home_scripts():
    w("Talk to Maren", [
        ("Get.Value", "ATTRIBUTE", "DinnerQuest", V1),
        (">Conditional", "$Variable.1=0 and $Attr.LastWill>=2", "@s1"),
        say("Maren", "Oh, you poor dear. Edwin said he'd be taking Mary's letter to you. We were so fond of her.\\Dinner? "
                     "Of course! Only the range is stone cold, and I've not a stick of firewood left. Would you chop me "
                     "three logs? Here, take Edwin's old axe.", ("I'll chop some logs.", "@axe"), ("Not just now.", "@end")),
        ("@axe",), (">Quest.Can.Start", "DinnerQuest", "@end"),
        ("Give.Item", "Bronze_Axe", "1"),
        ("Update.Attribute", "DinnerQuest", "=1"),
        ("Display.Message", "Yellow", "Quest started: Dinner at Edwin's. (H: your journal)", "Quest"),
        ("End",),
        ("@s1",), (">Conditional", "$Variable.1=1", "@s2"),
        (">Got.Item", "Logs", "3", "@nologs"),
        ("Take.Item", "Logs", "3"),
        ("Update.Attribute", "DinnerQuest", "=2"),
        say("Maren", "Lovely dry logs: that'll get the range going. Now, supper! Edwin's partial to an egg, fried crisp. "
                     "Would you fetch one from my sister Bess's hen coop, up on the farm, and fry it on the range? It's "
                     "upstairs, in our kitchen.", ("I'll fetch an egg.", "@end")),
        ("End",),
        ("@nologs",), say("Maren", "Three logs, dear. Chop a tree with the axe I gave you.", ("I'll keep chopping.", "@menu")),
        ("@s2",), (">Conditional", "$Variable.1>=2 and $Variable.1<=3", "@menu"),
        say("Maren", "An egg from Bess's coop, fried on my range upstairs, and then it's for Edwin. He'll be so pleased.",
            ("I'll see to it.", "@menu")),
        ("@menu",),
        say("Maren", "Come in, dear. Anyone on the Isle who's poorly ends up on that bed, and I do what I can for "
                     "them. Edwin has his desk by the window: wills and deeds and the like.",
            ("How is your father? [if $Attr.FatherFreed>=1]", "@father"), ("Goodbye.", "@end")),
        ("@father",), say("Maren", "Home, and safe, and eating us out of house and home! I can't ever thank you enough.",
                          ("I'm glad.", "@end")),
        ("@end",), ("End",),
    ])
    w("Talk to Edwin", [
        ("Get.Value", "ATTRIBUTE", "DinnerQuest", V1),
        (">Conditional", "$Variable.1>=2 and $Variable.1<=3", "@chat"),   # (an egg fried on any range will do)
        (">Got.Item", "Fried_Egg", "1", "@chat"),
        ("Take.Item", "Fried_Egg", "1"),
        ("Update.Attribute", "DinnerQuest", "=4"),
        say("Edwin", "A fried egg, crisp at the edges, just as I like it! You have your mother's kindness. Thank you.",
            ("Enjoy it.", "@key")),
        ("@key",),
        say("Maren", "Thank you, dear. Now, Brother Aldous left this with us for safekeeping: the key to the trapdoor in "
                     "the chapel cellar. Mary said that one day you would need it.\\Only promise me you won't go down "
                     "there without a sword and a shield.", ("I promise.", "@give")),
        ("@give",),
        ("Give.Item", "Chapel_Cellar_Key", "1"),
        say("Maren", "And take these with you: two healing draughts, brewed from Bess's herbs. Drink one when you're "
                     "hurt: doctor's orders.\\Herbs, mind, not magic. Shards can do a great deal, but they can't mend a body: only a "
                     "brewer's herbs can.", ("Thank you, Maren.", "@draughts")),
        ("@draughts",),
        ("Give.Item", "Healing_Draught", "2"),
        ("Display.Message", "Yellow", "Quest complete: Dinner at Edwin's! Maren gave you the key to the chapel's "
                                      "trapdoor, and two healing draughts.", "Quest"),
        ("End",),
        ("@chat",), (">Conditional", "$Attr.LastWill>=2", "@letter"),
        say("Edwin", "If you need anything drawn up, a will or a deed, I'm your man.",
            ("What was my mother like?", "@mary"), ("Goodbye.", "@end")),
        ("@mary",),
        say("Edwin", "She came to the Isle with you in her arms and never said from where. Kind, proud, and far cleverer "
                     "than she let on. I always thought there was more to her than a cottage and a cat.",
            ("Thank you.", "@end")),
        ("End",),
        ("@letter",), say("Edwin", "Take your time with the letter. It's yours alone.", ("Goodbye.", "@end")),
        ("@end",), ("End",),
    ])
    w("Use Egg With Marens_Range", [
        (">Distance.From.Clicked.Entity", "48", "@far"),
        (">Got.Item", "Egg", "1", "@none"),
        ("Take.Item", "Egg", "1"),
        ("Show.Skill", "Cooking"),
        ("Display.Message", "Cyan", "You crack the egg onto Maren's hot range..", "-"),
        ("Play.Sound", "CookingFood"),
        ("Wait", "2"),
        ("Display.Message", "Yellow", "..and fry it to a turn!", "-"),
        ("Update.Skill", "Cooking", "+0.05"),
        ("Give.Item", "Fried_Egg", "1"),
        ("Get.Value", "ATTRIBUTE", "DinnerQuest", V1),
        (">Conditional", "$Variable.1=2", "@end"),
        ("Update.Attribute", "DinnerQuest", "=3"),
        ("@end",), ("End",),
        ("@none",), ("Display.Message", "DarkRed", "You don't have an egg.", "Denied"),
        ("End",),
    ] + FAR)
    w("2,1,1", [                                                  # (upstairs at Edwin's: Tobias, once he's free)
        ("Get.Value", "ATTRIBUTE", "FatherFreed", V1),
        (">Conditional", "$Variable.1>=1", "@end"),
        ("Add.Entity", at(19, 3, -8), "Tobias", "NPC", "Attitude=Good Stand=1 Face=S"),
        ("@end",), ("End",),
    ])
    w("Talk to Tobias", [
        say("Tobias", "There's my rescuer! Maren's feeding me up like a Midsummer goose.\\The house is yours, mind: "
                      "I'll not go back, not with those brutes so near it. Keep it well.", ("I will.", "@end")),
        ("@end",), ("End",),
    ])
    notice("Isle_Bank_Notice", "EDWIN, LAWYER. MAREN, DOCTOR.", "A brass plate by the door of a red brick house, "
           "built the year the great storm took the pier.")


def bess_and_frank():
    w("Talk to Milkmaid", [
        say("Milkmaid", "Morning! Mind the cows, they're friendly but they tread on toes.\\Use a bucket on a cow for milk, "
                        "shears on a sheep for wool. The hens lay in their coop, by the barn.",
            ("What do you sell?", "@shop"), ("What's wool for?", "@wool"),
            ("Will you take me to the mainland? [if $Attr.Passage<=4 and $Attr.LastWill>=2]", "@ask"),
            ("Goodbye.", "@end")),
        ("@shop",), ("Display.Item.Rack", "SPECIFIC", "Milkmaid", "SHOP-Dairy", "@end"),
        ("End",),
        ("@wool",), say("Milkmaid", "Spin it into balls of wool on a workbench, there's one in the barn. Cowhide can be "
                                    "tanned into leather there too.", ("Thanks!", "@end")),
        ("End",),
        ("@ask",), (">Conditional", "$Attr.Passage=0", "@compass"),
        (">Quest.Can.Start", "Passage", "@end"),
        say("Milkmaid", "To the mainland? Love, nobody's crossed the strait since Father went missing. The fog out there "
                        "would swallow you whole. Father was the only one who could find the way through it, with his "
                        "compass, and the compass went with him.\\Find Father's compass and I'll sail you over myself. "
                        "His house is the old brick one in the village, locked up, and the hobgoblins took his keys when "
                        "they took him. They've a lair in the caves under the chapel, they say.",
            ("I'll find it.", "@start")),
        ("@start",),
        ("Update.Attribute", "Passage", "=1"),
        ("Display.Message", "Yellow", "Quest started: Passage to the Mainland.", "Quest"),
        (">Conditional", "$Attr.AmuletQuest=0", "@end"),
        say("Milkmaid", "And you'll not go near hobgoblins with your bare hands! My Frank's the blacksmith: his smithy's "
                        "right by my hut. He'll help you make a sword and a shield.", ("Thank you, Bess.", "@amulet")),
        ("@amulet",), (">Quest.Can.Start", "AmuletQuest", "@end"),
        ("Update.Attribute", "AmuletQuest", "=1"),
        ("Display.Message", "Yellow", "Quest started: The Amulet of Succession.", "Quest"),
        ("End",),
        ("@compass",), ("Get.Value", "ATTRIBUTE", "Passage", V1),
        (">Conditional", "$Variable.1=4", "@hunting"),
        (">Got.Item", "Fathers_Compass", "1", "@hunting"),
        (">Conditional", "$Attr.FatherFreed>=1", "@nofather"),
        ("Take.Item", "Fathers_Compass", "1"),
        ("Update.Attribute", "Passage", "=5"),
        ("Display.Message", "Yellow", "Quest complete: Passage to the Mainland!", "Quest"),
        say("Milkmaid", "Father's compass! And Father home safe, all thanks to you. Oh, come here, love.\\I'll take you "
                        "across to Northport myself, right now. After that Wim can ferry you back and forth: he'll steer "
                        "by Father's compass now.", ("Take me to Northport.", "@sail"), ("Not yet.", "@later")),
        ("@sail",), ("Goto.Script", "Bess Sails to Northport"),
        ("@later",), say("Milkmaid", "Whenever you're ready, Wim's on the pier.", ("Thank you, Bess.", "@end")),
        ("End",),
        ("@nofather",),
        say("Milkmaid", "You found his compass! But where's Father? You didn't leave him with those brutes? Bring him "
                        "home, love, please.", ("I'll find him.", "@end")),
        ("End",),
        ("@hunting",),
        say("Milkmaid", "Any sign of Father's compass? It'll be in his house, the old brick one in the village. The "
                        "hobgoblins have his keys, down in their lair under the chapel.", ("I'm on it.", "@end")),
        ("@end",), ("End",),
    ])
    w("Bess Sails to Northport", [
        ("Display.Message", "Cyan", "Bess takes the tiller, her father's compass in her hand, and the Isle slips away "
                                    "into the fog..", "-"),
        ("Play.Sound", "Boat"),
        ("Toggle.User.Input", "OFF"),
        ("Wait", "3"),
        ("Toggle.User.Input", "ON"),
        ("Teleport", "Northport_Pier", "-"),
        ("Display.Message", "Yellow", "..and the fog lifts over Northport harbour.", "-"),
        say("Milkmaid", "There's Northport. Its shardstone stands by the market: feed it a few Shards and it wakes, and "
                        "after that it'll carry you to any other shardstone you've woken. Mind your Shards, love, and "
                        "come home sometimes.", ("Goodbye, Bess.", "@off")),
        ("@off",),
        ("Display.Message", "Cyan", "Bess waves you off from the boat.", "-"),
        ("End",),
    ])
    w("Talk to Frank", [
        ("Get.Value", "ATTRIBUTE", "AmuletQuest", V1),
        (">Conditional", "$Variable.1=1", "@s2"),
        say("Frank", "Bess sent you? Then you'll want a sword and a shield, and I'll show you how. Wood first: you'll "
                     "learn to swing a blade before anyone trusts you with steel.\\Use my workbench there (Craft): a "
                     "wooden sword takes 2 logs, a wooden shield 3. Here, have some of my seasoned wood.",
            ("Thank you, Frank.", "@logs")),
        ("@logs",),
        ("Give.Item", "Logs", "5"),
        ("Update.Attribute", "AmuletQuest", "=2"),
        ("End",),
        ("@s2",), (">Conditional", "$Variable.1=2", "@s3"),
        (">Conditional", "$Item.Wooden_Sword>=1 and $Item.Wooden_Shield>=1", "@notyet"),
        ("Update.Attribute", "AmuletQuest", "=3"),
        say("Frank", "Not bad at all! Now wield them: sword in your hand, shield on your arm, and get used to the weight. "
                     "Practise on the rats and wolves till your arm's strong (Strength 2) and you can take a knock "
                     "(Defence 2).\\Then go and see Brother Aldous at the chapel. He keeps the way down.",
            ("I will.", "@dagger")),
        ("@dagger",),
        say("Frank", "And here: my first dagger. It's past mending, but don't throw it away. Everything that's forged "
                     "keeps a little of the world's magic in it: break it down (Dismantle, in your pack) and you'll "
                     "have a Shard out of it. Do the same with any gear you've outgrown.", ("I'll try it.", "@give")),
        ("@give",),
        ("Give.Item", "Copper_Dagger", "1"),
        ("End",),
        ("@notyet",),
        say("Frank", "A wooden sword and a wooden shield, at my workbench (Craft). Bring them to show me when they're "
                     "made.", ("Right.", "@end")),
        ("End",),
        ("@s3",),
        say("Frank", "Hot work, smithing. If your gear's knocked about, I'll mend it for a fair price (Repair).",
            ("Goodbye.", "@end")),
        ("@end",), ("End",),
    ])


def chapel_and_caves():
    w("Talk to Chapel_Verger", [
        ("Get.Value", "ATTRIBUTE", "AmuletQuest", V1),
        (">Conditional", "$Variable.1=3", "@not3"),
        (">Conditional", "$Equipped.Weapon<>none and $Equipped.Shield<>none", "@unarmed"),
        (">Conditional", "$Skill.Strength>=2 and $Skill.Defence>=2", "@untrained"),
        (">Conditional", "$Item.Chapel_Cellar_Key>=1", "@nokey"),
        ("Update.Attribute", "AmuletQuest", "=4"),
        say("Gravekeeper", "Mary's $Player.Boy. So the time has come.\\She came to me years ago with something to hide: an amulet. "
                           "We put it at the back of the caves under this chapel, behind bars no hand could reach "
                           "through.\\You have the trapdoor's key from Maren, and a sword and a shield, and you look as "
                           "if you can use them now. Go down. I'll not be far behind you.",
            ("Thank you, Brother.", "@end")),
        ("End",),
        ("@nokey",),
        say("Gravekeeper", "You're ready, I'd say. But the trapdoor's locked, and I gave its key to Maren, the doctor, "
                           "for safekeeping.", ("I'll ask her.", "@end")),
        ("End",),
        ("@untrained",),
        say("Gravekeeper", "Wooden swords and good intentions. Practise first: a few rats and wolves, until your Strength "
                           "and Defence are level 2. Then come back.", ("I will.", "@end")),
        ("End",),
        ("@unarmed",),
        say("Gravekeeper", "Down there, with your sword and shield in your pack? Wield them both, then we'll talk.",
            ("Right.", "@end")),
        ("End",),
        ("@not3",), (">Conditional", "$Variable.1<3", "@after"),
        say("Gravekeeper", "Peace be with you. I'm Brother Aldous: I keep the chapel, and the graves out there. I buried "
                           "your mother this morning. She was a good woman.",
            ("What's down in the cellar?", "@cellar"), ("Goodbye.", "@end")),
        ("@cellar",),
        say("Gravekeeper", "Barrels and dust, and a trapdoor down to the caves, where no one should go unarmed.",
            ("I see.", "@end")),
        ("End",),
        ("@after",), (">Conditional", "$Variable.1=4", "@s5"),
        say("Gravekeeper", "The trapdoor is in the cellar, down the steps behind the altar. The amulet is at the very back "
                           "of the caves.", ("I'll find it.", "@end")),
        ("End",),
        ("@s5",), (">Conditional", "$Variable.1=5", "@done"),
        say("Gravekeeper", "Cast the Grasp at the bars, and the amulet will come to you.", ("I will.", "@end")),
        ("End",),
        ("@done",),
        say("Gravekeeper", "Keep the amulet close, and show it to no one but your father. Go with God.",
            ("Goodbye.", "@end")),
        ("@end",), ("End",),
    ])
    w("Climb Down Trapdoor", [
        (">Got.Item", "Chapel_Cellar_Key", "1", "@locked"),
        ("Get.Value", "ATTRIBUTE", "AmuletQuest", V1),
        (">Conditional", "$Variable.1>=4", "@wait"),
        ("Play.Sound", "Ladder"),
        ("Display.Message", "Cyan", "You climb down the ladder, into the caves under the Isle."),
        ("Teleport", "416,280", "3,1,-2"),
        ("End",),
        ("@wait",), ("Display.Refusal", "You promised Maren: not until Brother Aldous says you're ready."),
        ("End",),
        ("@locked",), ("Display.Refusal", "The trapdoor is locked."),
        ("End",),
    ])
    for kind, nothing in (("Cellar_Barrel", "Only old candle ends and dust."),
                          ("Cellar_Crate", "Mouldy hymn books, and a mouse.")):
        w("Search " + kind, [
            (">Distance.From.Clicked.Tile", "40", "@far"),
            ("Display.Message", "Cyan", "You rummage through the %s.." % kind.split("_")[1].lower()),
            ("Play.Sound", "Pickup"),
            ("Wait", "1"),
            ("Display.Message", "Cyan", ".." + nothing[0].lower() + nothing[1:]),
            ("End",),
        ] + FAR)
    nx, ny = NICHE
    aldous = at(nx + 3, ny + 1, -8)                              # (where Aldous stands when he's followed you down)
    w("1,1,-2", [
        ("Get.Value", "ATTRIBUTE", "AmuletQuest", V1),
        (">Conditional", "$Variable.1<6", "@empty"),
        ("Add.Entity", at(nx, ny), "Barred_Niche", "StaticObject", "-"),
        ("End",),
        ("@empty",), ("Add.Entity", at(nx, ny), "Barred_Niche_Empty", "StaticObject", "-"),
        ("End",),
    ])
    w("Reach In Barred_Niche", [
        (">Distance.From.Clicked.Entity", "64", "@far"),
        ("Get.Value", "ATTRIBUTE", "AmuletQuest", V1),
        (">Conditional", "$Variable.1=4", "@not4"),
        ("Display.Refusal", "Iron bars, set deep in the rock, too close for your hand. Behind them: a gold amulet!"),
        ("Wait", "1"),
        ("Display.Message", "Cyan", "Footsteps echo behind you: Brother Aldous, a lantern in his hand.", "-"),
        ("Add.Entity", aldous, "Gravekeeper", "NPC", "Attitude=Good Stand=1 Face=W Name=Brother_Aldous"),
        say("Gravekeeper", "I said I'd not be far behind. Look here first.\\He stoops, and picks dull grey splinters "
                           "from the floor.\\Something died here, a rat or a bat, and left its magic behind: Shard "
                           "Remnants. Hold them and draw the magic out (Absorb, in your pack), and they're Shards. "
                           "Every beast leaves its magic somewhere when it dies. And now and then, the magic won't lie "
                           "still.", ("I'll remember.", "@remnants")),
        ("@remnants",),
        ("Give.Item", "Shard_Remnant", "3"),
        say("Gravekeeper", "Now, the amulet. Your mother put it there, and the bars after it, so that no "
                           "thief could ever take it. But a hand that isn't a hand can.\\Here: a scroll of Grasp. Read it, "
                           "and the spell is yours for good; each casting drinks a couple of Shards. Cast it at the "
                           "bars, and an unseen hand will bring the amulet to you.", ("Thank you, Brother.", "@give")),
        ("@give",),
        ("Give.Item", "Grasp_Scroll", "1"),
        ("Update.Attribute", "AmuletQuest", "=5"),
        ("Display.Message", "Yellow", "Learn Grasp from the scroll, then cast it from Channeling at what you want "
                                      "brought to you.", "-"),
        ("End",),
        ("@not4",), (">Conditional", "$Variable.1=5", "@end"),
        ("Display.Refusal", "The bars are too close for your hand."),
        ("@end",), ("End",),
    ] + FAR)
    w("Grasp Barred_Niche", [
        ("Get.Value", "ATTRIBUTE", "AmuletQuest", V1),
        (">Conditional", "$Variable.1=5", "@end"),
        ("Remove.Entity", "$Object.under.Cursor.X,$Object.under.Cursor.Y", "Barred_Niche"),
        ("Add.Entity", at(nx, ny), "Barred_Niche_Empty", "StaticObject", "-"),
        ("Give.Item", "Amulet_of_Succession", "1"),
        ("Display.Message", "Yellow", "An unseen hand closes on the amulet and draws it out between the bars, into your "
                                      "palm.", "-"),
        ("Update.Attribute", "AmuletQuest", "=6"),
        say("Gravekeeper", "The Amulet of Ashen Succession. So it's true, then. Keep it close, and show it to no one "
                           "but your father.\\And take this. The hobgoblins have made a lair beyond an old iron door in "
                           "these caves, south of the great cavern. I keep the caves' old keys: this is that door's. "
                           "Bess's father went missing when they came. If you go after them, go carefully.",
            ("I will.", "@key")),
        ("@key",),
        ("Give.Item", "Lair_Key", "1"),
        ("Display.Message", "Yellow", "Quest complete: The Amulet of Succession! Brother Aldous gave you the key of the "
                                      "hobgoblins' door.", "Quest"),
        ("Remove.Entity", aldous, "Gravekeeper"),
        ("@end",), ("End",),
    ])


def lair_scripts():
    tx, ty = TENT
    cx, cy = CAGE
    rows = [("Display.Message", "Red", "Torchlight, bones and the stink of hobgoblin: their lair!", "-")]
    zones = ("6,6,14,12", "12,11,19,16", "4,10,11,16", "15,5,21,10")
    for (x, y), z in zip(LAIR_HOBS, zones):                       # (the ones killed come back when someone comes in)
        rows.append(("Add.Entity", at(x, y, -8), "Hobgoblin", "NPC", "Attitude=Bad Zone=" + z))
    rows += [
        ("Get.Value", "ATTRIBUTE", "FatherFreed", V1),
        (">Conditional", "$Variable.1=0", "@freed"),
        ("Add.Entity", at(cx, cy), "Caged_Tobias", "StaticObject", "-"),
        ("End",),
        ("@freed",), ("Add.Entity", at(cx, cy), "Hob_Cage_Open", "StaticObject", "-"),
        ("End",),
    ]
    w("2,2,-2", rows)
    w("Enter Hob_Camp_Tent", [
        (">Distance.From.Clicked.Tile", "48", "@far"),
        ("Get.Value", "ATTRIBUTE", "LairLadder", V1),
        (">Conditional", "$Variable.1>=1", "@empty"),
        ("Play.Sound", "Ladder"),
        ("Display.Message", "Cyan", "You lift the bedroll aside and climb down the hidden ladder, into the hobgoblins' "
                                    "lair.", "-"),
        ("Teleport", at(tx, ty + 1, -8), "2,2,-2"),
        ("End",),
        ("@empty",),
        ("Display.Message", "Cyan", "Bedrolls, bones and the stink of hobgoblin. It's just an empty tent.", "-"),
        ("End",),
    ] + FAR)
    w("Climb Up Hidden_Ladder", [
        (">Distance.From.Clicked.Tile", "48", "@far"),
        ("Play.Sound", "Ladder"),
        ("Update.Attribute", "LairLadder", "=1"),
        ("Display.Message", "Cyan", "You climb the ladder and come up under a bedroll, inside a tent in the hobgoblins' "
                                    "camp.", "-"),
        ("Teleport", at(tx, ty + 1, -8), "2,2,0"),
        ("End",),
    ] + FAR)
    w("Talk to Caged_Tobias", [
        ("Get.Value", "ATTRIBUTE", "Passage", V1),
        (">Conditional", "$Variable.1=1", "@talk"),
        ("Update.Attribute", "Passage", "=2"),
        ("@talk",),
        say("Tobias", "Who's there? You're not one of them, thank the stars!\\I'm Tobias, Bess and Maren's father. The "
                      "brutes caught me in my own house, and they've kept me in this cage ever since. They took my keys "
                      "too: my house key's hidden in one of their barrels, the one in the corner. I watched them do "
                      "it.\\Can you get this lock open? It's a poor old lock.",
            ("I'll try.", "@try"), ("Hold on.", "@end")),
        ("@try",), ("Goto.Script", "Pick Lock Caged_Tobias"),
        ("@end",), ("End",),
    ])
    w("Pick Lock Caged_Tobias", [
        (">Distance.From.Clicked.Entity", "48", "@far"),
        ("Display.Message", "Cyan", "You work at the cage's lock with a bent nail..", "-"),
        ("Play.Minigame", "LOCK", "1", "@fail"),                # (set the pins: minigames.py)
        ("Get.Value", "ATTRIBUTE", "Passage", V1),
        ("Play.Sound", "Cage_Open"),
        ("Remove.Entity", "$Object.under.Cursor.X,$Object.under.Cursor.Y", "Caged_Tobias"),
        ("Add.Entity", at(cx, cy), "Hob_Cage_Open", "StaticObject", "-"),
        ("Add.Entity", at(cx - 1, cy + 1, -8), "Tobias", "NPC", "Attitude=Good Stand=1 Face=N"),
        ("Update.Attribute", "FatherFreed", "=1"),
        ("Display.Message", "Yellow", "..and the lock springs open!", "-"),
        say("Tobias", "Free! Bless you, child.\\Listen: the house is yours. I'll not go back, not with those brutes so "
                      "near it: I'll go and live with Maren and Edwin. Find my key in that corner barrel and keep "
                      "it.\\And Bess's compass? I hid it under the floor at home before they took me. You'll hear the "
                      "board.", ("Get home safe.", "@go")),
        ("@go",),
        ("Remove.Entity", at(cx - 1, cy + 1, -8), "Tobias"),
        ("Display.Message", "Cyan", "Tobias hobbles to the ladder and climbs up out of the lair, towards home.", "-"),
        (">Conditional", "$Variable.1<3", "@end"),
        ("Update.Attribute", "Passage", "=3"),
        ("@end",), ("End",),
        ("@fail",), ("Display.Message", "DarkRed", "..but the lock won't give. Try again.", "Fail"),
        ("End",),
    ] + FAR)
    w("Search Lair_Corner_Barrel", [
        (">Distance.From.Clicked.Tile", "48", "@far"),
        ("Display.Message", "Cyan", "You rummage through the barrel..", "-"),
        ("Play.Sound", "Pickup"),
        ("Wait", "1"),
        (">Got.Item", "Fathers_House_Key", "1", "@find"),
        ("Display.Message", "Cyan", "..rags and bones, nothing more.", "-"),
        ("End",),
        ("@find",), ("Give.Item", "Fathers_House_Key", "1"),
        ("Display.Message", "Yellow", "..and there, under the rags: a brass house key. Tobias's!", "-"),
        ("End",),
    ] + FAR)
    w("Search Lair_Barrel", [
        (">Distance.From.Clicked.Tile", "48", "@far"),
        ("Display.Message", "Cyan", "You rummage through the barrel..", "-"),
        ("Play.Sound", "Pickup"),
        ("Wait", "1"),
        ("Display.Message", "Cyan", "..rotten cabbages and hobgoblin junk.", "-"),
        ("End",),
    ] + FAR)


def fathers_house_scripts():
    sx, sy = SQUEAK
    w("Squeaky Floorboard", [
        ("Get.Value", "ATTRIBUTE", "CompassFound", V1),
        (">Conditional", "$Variable.1=0", "@end"),
        ("Play.Sound", "Squeak"),
        ("Display.Message", "Cyan", "Someone should fix that floorboard; it sounds like it's about to fall through.", "-"),
        ("Update.Attribute", "Squeaked", "=1"),
        ("Change.Tile", "%d,%d" % (sx, sy), "Loose_Floorboard001", "0", "0"),
        ("@end",), ("End",),
    ])
    w("1,1,0", [                                                  # (a loose board they've stood on stays loose;
        ("Get.Value", "ATTRIBUTE", "Squeaked", V1),                 # and Jimmy, in this house of yours too, once
        ("Get.Value", "ATTRIBUTE", "CompassFound", V2),             # you're king: build_heir_mainland.py)
        (">Conditional", "$Variable.1>=1 and $Variable.2=0", "@jimmy"),
        ("Change.Tile", "%d,%d" % (sx, sy), "Loose_Floorboard001", "0", "0"),
        ("@jimmy",), (">Conditional", "$Attr.KingQuest>=1", "@end"),
        ("Add.Entity", at(20, 5, -8), "Strawberry_Cat", "NPC", "Attitude=Good Zone=19,4,21,6 Pause=6-15 Name=Jimmy"),
        ("@end",), ("End",),
    ])
    w("Search Loose_Floorboard", [
        (">Distance.From.Clicked.Tile", "48", "@far"),
        ("Get.Value", "ATTRIBUTE", "CompassFound", V1),
        (">Conditional", "$Variable.1=0", "@done"),
        ("Display.Message", "Cyan", "You prise up the loose board..", "-"),
        ("Play.Sound", "Squeak"),
        ("Wait", "1"),
        ("Give.Item", "Fathers_Compass", "1"),
        ("Update.Attribute", "CompassFound", "=1"),
        ("Display.Message", "Yellow", "..and underneath, wrapped in oilcloth: a brass compass. Tobias's!", "-"),
        ("Change.Tile", "%d,%d" % (sx, sy), "Plank001", "0", "0"),
        ("Get.Value", "ATTRIBUTE", "Passage", V2),
        (">Conditional", "$Variable.2>=1 and $Variable.2<4", "@end"),
        ("Update.Attribute", "Passage", "=4"),
        ("@end",), ("End",),
        ("@done",), ("Display.Message", "Cyan", "Just a floorboard, nailed down firm.", "-"),
        ("End",),
    ] + FAR)
    notice("Fathers_Home", "MAREN & BESS'S FATHER'S HOME",
           "Maren & Bess's Father's Home is locked; he has been missing ever since the hobgoblins set up camp just south "
           "of here.", cond="$Attr.FatherFreed<1", alt="Tobias gave it to you when you freed him: it's yours now.")
    w("Talk to Beggar", [
        say("Beggar", "Spare a coin for a poor old man?", ("Here's a coin.", "@coin"), ("Sorry, no.", "@end")),
        ("@coin",), (">Got.Item", "Gold_Coin(s)", "1", "@none"),
        ("Take.Item", "Gold_Coin(s)", "1"),
        say("Beggar", "Bless you! I wasn't always like this, you know. Had a house once, with a garden. Ah well.",
            ("Good luck to you.", "@end")),
        ("End",),
        ("@none",), ("Display.Message", "DarkRed", "You don't have any gold!", "Denied"),
        ("@end",), ("End",),
    ])


def ferry_scripts():
    K.remove_script("1,2,0")                                      # (the pier was on 1,2,0: it's on 3,2,0 now)
    w("3,2,0", [                                    # (the pier map's own file is unchanged: its notice is its own)
        ("Add.Entity", "Isle_Ferry_Pier", "Ferryman", "NPC", "Attitude=Good Stand=1 Name=Wim Schedule=Always"),
        ("End",),
    ])
    w("Talk to Ferryman", [
        (">On.Map", "3,2,0", "@southport"),
        ("Get.Value", "ATTRIBUTE", "Passage", V1),
        (">Conditional", "$Variable.1>=5", "@fog"),
        say("Ferryman", "Northport, is it? A gold coin a crossing.", ("Yes, take me (1 gold).", "@pay"),
            ("Not today.", "@end")),
        ("@pay",), (">Got.Item", "Gold_Coin(s)", "1", "@nogold"),
        ("Take.Item", "Gold_Coin(s)", "1"),
        ("Goto.Script", "Ferry to Northport"),
        ("@fog",),
        say("Ferryman", "Cross the strait? Not in this fog, friend. Old Tobias was the only one who could find the way, "
                        "with that compass of his, and nobody's seen him since the hobgoblins came. Bess would tell you "
                        "the same: it's her boat.", ("I see.", "@end")),
        ("End",),
        ("@southport",), (">On.Map", "1,3,0", "@end"),
        say("Ferryman", "Back to the Isle? A gold coin, then climb aboard.", ("Yes, back to the Isle (1 gold).", "@back"),
            ("Not yet.", "@end")),
        ("@back",), (">Got.Item", "Gold_Coin(s)", "1", "@nogold"),
        ("Take.Item", "Gold_Coin(s)", "1"),
        ("Goto.Script", "Ferry to the Isle"),
        ("@nogold",), ("Display.Refusal", "You need 1 gold coin for the fare."),
        ("@end",), ("End",),
    ])


def old_scripts():
    """What the old Passage to the Mainland and The Beggar's Lost Key had, and nothing does now."""
    for name in ("Open Barred_Niche", "Talk to Woman", "Open Goblin_Cage", "Grasp Goblin_Cage", "Beggar House", "Unlock Door001",
                 "Read The_Old_Brick_House", "Use Beggars_House_Key With Door", "Use Beggars_House_Key With Door001"):
        K.remove_script(name)


def scripts():
    opening()
    home_scripts()
    bess_and_frank()
    chapel_and_caves()
    lair_scripts()
    fathers_house_scripts()
    ferry_scripts()
    old_scripts()
    print("Scripts: the funeral and the letter, Edwin and Maren's house, Bess and Frank, Brother Aldous and the amulet, the lair, "
          "the floorboard, the ferry")


def main():
    draw_pictures()
    make_sounds()
    data()
    maps()
    scripts()


if __name__ == "__main__":
    main()
