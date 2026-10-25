"""People and humanoid monsters drawn on the player's body (build_player.py), so they match the player's style and
walk properly in all four directions.

Run:  python -I "Dev\\migrate\\build_people.py" [--preview]
Writes Sprites\\Entities\\<Name>.png (the standing, facing-you frame). build_walk.py writes their 12 walking frames
(Sprites\\Walk\\<Name><Dir><Frame>.png) from frames() here. Then re-run build_walk.py.
--preview writes Dev\\Renders\\People preview.png (each person: S N E W, standing and stepping).
The hand-drawn originals they replace are in Dev\\Archive\\Original NPC sprites.

Each person in PEOPLE is the player's body (head, torso, arms, legs, the same frames) in their own colours, with
extras: a hairstyle, beard, hat, apron, dress or robe, cape, worn armour (the Worn_ overlays of build_worn.py), and
something held in the hand. Monsters too: goblins (green, pointed ears), hobgoblins (horns), skeletons (bones).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_player as BP
import build_worn as BW
import sprite_kit as K
from common import p

CX = BP.CX
SKIN = ((244, 184, 160), (206, 146, 124))
SKIN_DARK = ((150, 100, 70), (112, 72, 48))


def shade(c, f):
    return tuple(max(0, min(255, int(v * f))) for v in c)


def P(**kw):
    d = dict(skin=SKIN, hair=((102, 55, 10), (72, 38, 6)), shirt=((40, 110, 50),), trousers=((96, 70, 40),),
             shoes=((70, 46, 24),), eyes=(40, 20, 30), mouth=(170, 70, 70), hair_style="short", beard=None,
             hat=None, apron=None, dress=None, cape=None, worn=(), held=None, ears=None, bones=False, bare_arms=False,
             bare_legs=False)
    d.update(kw)
    return d


BROWN, DARK, GREY = (96, 70, 40), (40, 40, 48), (120, 120, 128)
WHITE = (236, 236, 228)
PEOPLE = {
    "Guard": P(shirt=((150, 30, 30),), trousers=((70, 70, 84),), worn=("Iron_Helm", "Iron_Platebody"),
               apron=(170, 30, 30), held="spear"),
    "Villager": P(shirt=((60, 130, 60),), trousers=((110, 80, 46),)),
    "Man": P(hair=((30, 26, 24), (14, 12, 12)), shirt=(DARK,), trousers=((30, 30, 36),), shoes=((20, 20, 24),),
             apron=(220, 220, 224)),
    "Woman": P(hair=((70, 36, 30), (44, 20, 18)), hair_style="long", shirt=((150, 20, 24),), dress=(150, 20, 24)),
    "Farmer": P(shirt=((226, 214, 190),), trousers=((70, 90, 150),), apron=(70, 90, 150), hat="straw", held="pitchfork",
                hair=((150, 100, 40), (110, 70, 20))),
    "Miner": P(skin=SKIN_DARK, hair=((24, 20, 18), (10, 8, 8)), shirt=((96, 60, 160),), apron=(120, 76, 36),
               hat="cap:110 76 36", held="pickaxe"),
    "Dwarf": P(hair=((210, 110, 40), (160, 70, 20)), beard="big", shirt=((140, 70, 30),), trousers=((80, 60, 40),),
               worn=("Iron_Helm",), hat="horns", held="axe"),
    "Wizard": P(hair=((210, 210, 214), (160, 160, 166)), hair_style="long", beard="white", shirt=((30, 40, 160),),
                dress=(30, 40, 160), hat="wizard", held="staff", stars=True),
    "Beggar": P(hair=((120, 90, 50), (90, 62, 30)), hair_style="messy", beard="stubble", shirt=((110, 104, 90),),
                trousers=((90, 80, 66),), shoes=((60, 50, 40),), patches=True),
    "Baker": P(shirt=((110, 140, 220),), apron=WHITE, hat="chef", trousers=((80, 80, 90),)),
    "Shopkeeper": P(hair=((170, 170, 176), (130, 130, 136)), shirt=(WHITE,), apron=(120, 76, 36), trousers=((60, 60, 70),)),
    "Milkmaid": P(hair=((200, 80, 40), (150, 50, 20)), hair_style="long", shirt=((70, 110, 200),), dress=(70, 110, 200),
                  apron=WHITE, hat="kerchief:240 240 240", held="bucket"),
    "Banker": P(hair=((90, 90, 96), (60, 60, 66)), hair_style="rim", shirt=(DARK,), trousers=((30, 30, 36),),
                shoes=((20, 20, 24),), apron=WHITE, held="book"),
    "King_Tyron": P(hair=((230, 190, 80), (190, 150, 40)), beard="gold", shirt=((30, 70, 190),), trousers=(WHITE,),
                    cape=(180, 20, 30), hat="crown"),
    "Herbalist": P(hair=((40, 30, 24), (20, 14, 12)), hair_style="long", shirt=((40, 110, 60),), dress=(40, 110, 60),
                   held="herbs"),
    "Blacksmith": P(hair_style="bald", shirt=((110, 110, 118),), apron=(90, 56, 26), trousers=((60, 60, 70),),
                    held="hammer", bare_arms=True),
    "Fisherman": P(hair=((150, 150, 150), (110, 110, 110)), beard="grey", shirt=((236, 200, 40),),
                   trousers=((50, 70, 130),), hat="sou'wester", held="rod"),
    "Quartermaster": P(shirt=((40, 50, 100),), trousers=((40, 50, 100),), hat="cap:40 50 100", beard="moustache",
                       held="book"),
    "Hermit": P(hair=((200, 200, 200), (160, 160, 160)), hair_style="long", beard="white", shirt=((110, 80, 50),),
                dress=(110, 80, 50), hat="hood:110 80 50", held="staff"),
    "Goblin": P(skin=((110, 170, 60), (76, 126, 40)), hair_style="bald", ears="pointy", eyes=(230, 200, 40),
                mouth=(60, 30, 20), shirt=((120, 84, 40),), trousers=((120, 84, 40),), bare_arms=True, bare_legs=True,
                held="spear"),
    "Hobgoblin": P(skin=((176, 110, 60), (136, 80, 40)), hair_style="bald", ears="pointy", eyes=(240, 60, 30),
                   mouth=(60, 20, 10), hat="horns", worn=("Leather_Body",), trousers=((70, 50, 30),), held="club",
                   bare_legs=True),
    "Skeleton": P(bones=True, held="rusty_sword"),
    # the Wildlands (build_regions.py): quest givers, traders and the bandits on the roads
    "Ranger": P(hair=((90, 60, 30), (60, 40, 18)), shirt=((70, 96, 50),), trousers=((80, 64, 40),),
                cape=(46, 84, 40), hat="hood:46 84 40", held="spear"),
    "Shepherd": P(hair=((170, 130, 80), (130, 96, 50)), beard="stubble", shirt=((200, 186, 150),),
                  trousers=((110, 90, 60),), hat="straw", held="staff"),
    "Witch": P(hair=((24, 20, 26), (10, 8, 12)), hair_style="long", shirt=((90, 40, 110),), dress=(90, 40, 110),
               hat="wizard", held="herbs"),
    "Elder": P(hair=((220, 220, 220), (180, 180, 180)), hair_style="long", beard="white", shirt=((110, 110, 96),),
               dress=(110, 110, 96), held="staff"),
    "Captain": P(shirt=((40, 60, 120),), trousers=((60, 60, 70),), worn=("Iron_Helm", "Iron_Platebody"),
                 cape=(30, 50, 130), beard="moustache", held="spear"),
    "Merchant": P(skin=SKIN_DARK, hair=((24, 20, 18), (10, 8, 8)), beard="stubble", shirt=((220, 140, 40),),
                  dress=(220, 140, 40), hat="cap:240 230 210", held="book"),
    "Forgemaster": P(hair=((150, 60, 30), (110, 40, 20)), hair_style="bald", beard="big", shirt=((100, 100, 108),),
                     apron=(80, 50, 24), trousers=((60, 60, 70),), held="hammer", bare_arms=True),
    "Trader": P(hair=((120, 80, 40), (90, 56, 26)), shirt=((140, 40, 50),), apron=(230, 220, 200),
                trousers=((70, 60, 50),), held="book"),
    "Settler": P(hair=((150, 100, 50), (110, 70, 30)), hair_style="long", shirt=((150, 120, 70),),
                 dress=(96, 110, 70), held="herbs"),
    "Bandit": P(hair=((40, 30, 24), (20, 14, 12)), beard="stubble", shirt=((70, 60, 50),), trousers=((60, 50, 40),),
                cape=(60, 46, 34), hat="hood:50 40 32", worn=("Leather_Body",), held="rusty_sword"),
    # the monsters that fight from afar (build_status.py): archers and casters
    "Goblin_Archer": P(skin=((110, 170, 60), (76, 126, 40)), hair_style="bald", ears="pointy", eyes=(230, 200, 40),
                       mouth=(60, 30, 20), shirt=((70, 90, 40),), trousers=((90, 70, 36),), cape=(56, 76, 32),
                       hat="hood:56 76 32", bare_legs=True, held="bow"),
    "Goblin_Shaman": P(skin=((110, 170, 60), (76, 126, 40)), hair_style="bald", ears="pointy", eyes=(255, 140, 40),
                       mouth=(60, 30, 20), shirt=((120, 40, 40),), dress=(120, 40, 40), hat="hood:90 30 30",
                       held="orb_staff:255 140 40"),
    "Skeleton_Archer": P(bones=True, held="bow"),
    "Frost_Witch": P(skin=((214, 226, 240), (170, 186, 206)), hair=((236, 244, 255), (190, 206, 230)),
                     hair_style="long", eyes=(90, 180, 255), shirt=((70, 120, 190),), dress=(70, 120, 190),
                     cape=(200, 226, 250), hat="wizard", held="orb_staff:150 220 255"),
    # The Ashen Omens (build_omens.py): the dragon cult's acolyte
    "Ashen_Acolyte": P(skin=((214, 196, 186), (176, 156, 146)), hair=((40, 36, 34), (24, 22, 20)), eyes=(230, 90, 30),
                       shirt=((96, 92, 90),), dress=(96, 92, 90), cape=(60, 56, 54), hat="hood:70 66 64",
                       held="orb_staff:255 110 30"),
    # the heir's story (build_heir_isle.py, build_heir_mainland.py, build_galaith.py): its people by their own names
    "Edwin": P(hair=((58, 40, 28), (38, 26, 18)), beard="moustache", shirt=((34, 32, 40),), trousers=((30, 30, 36),),
               shoes=((20, 20, 24),), apron=WHITE, held="book"),
    "Maren": P(hair=((140, 60, 34), (100, 40, 22)), hair_style="long", shirt=((44, 98, 74),), dress=(44, 98, 74)),
    "Frank": P(hair=((110, 64, 30), (80, 44, 18)), beard="big", shirt=((120, 116, 110),), apron=(96, 60, 28),
               trousers=((60, 60, 70),), held="hammer", bare_arms=True),
    "Tobias": P(hair=((226, 226, 222), (186, 186, 182)), hair_style="messy", beard="white", shirt=((116, 108, 92),),
                trousers=((96, 80, 60),), patches=True),
    "Ferryman": P(hair=((130, 130, 128), (96, 96, 94)), beard="grey", shirt=((56, 76, 130),),
                  trousers=((70, 64, 56),), hat="cap:30 34 50"),
    "Mourner": P(hair=((52, 36, 28), (34, 22, 16)), hair_style="long", shirt=((44, 42, 48),), dress=(44, 42, 48)),
    "Port_Guard": P(shirt=((40, 70, 150),), trousers=((60, 60, 72),), worn=("Iron_Helm", "Iron_Platebody"),
                    apron=(40, 70, 150), held="spear"),
    "Speaker": P(hair=((176, 176, 180), (136, 136, 140)), hair_style="long", shirt=((130, 24, 40),),
                 dress=(130, 24, 40), cape=(200, 170, 70), held="book"),
    "Mayor": P(hair=((90, 70, 50), (62, 46, 30)), beard="moustache", shirt=((96, 50, 120),), cape=(96, 50, 120),
               trousers=((50, 44, 56),), held="book"),
    "Steward": P(hair=((150, 150, 150), (110, 110, 110)), beard="grey", shirt=((40, 60, 130),), cape=(200, 160, 50),
                 trousers=((60, 56, 70),), held="book"),
    "Bert": P(hair=((230, 230, 234), (180, 180, 186)), hair_style="long", beard="white", shirt=((112, 40, 150),),
              dress=(112, 40, 150), hat="wizard", held="orb_staff:200 120 255", stars=True),
    "Scholar": P(skin=SKIN_DARK, hair=((24, 20, 18), (10, 8, 8)), beard="stubble", shirt=((210, 190, 140),),
                 dress=(210, 190, 140), hat="cap:240 236 220", held="book"),
    "Sea_Captain": P(hair=((90, 90, 92), (60, 60, 62)), beard="big", shirt=((30, 40, 80),), cape=(30, 40, 80),
                     trousers=((40, 40, 50),), hat="cap:26 26 30"),
    "Valour_Guardian": P(skin=((180, 210, 240), (140, 170, 210)), hair=((200, 225, 255), (160, 190, 230)),
                         eyes=(255, 255, 255), shirt=((150, 180, 230),), trousers=((130, 160, 210),),
                         worn=("Mithril_Helm", "Mithril_Platebody"), cape=(110, 150, 220), held="rusty_sword"),
    "King_Rupert": P(hair=((176, 168, 140), (136, 128, 100)), beard="grey", shirt=((236, 232, 220),),
                     trousers=((40, 50, 120),), cape=(110, 20, 60), hat="crown"),
    "Royal_Guard": P(shirt=((236, 232, 220),), trousers=((70, 70, 84),), worn=("Steel_Helm", "Steel_Platebody"),
                     apron=(200, 160, 40), cape=(120, 20, 40), held="spear"),
    "Guard_Captain": P(beard="moustache", shirt=((236, 232, 220),), trousers=((70, 70, 84),),
                       worn=("Steel_Helm", "Steel_Platebody"), cape=(200, 160, 40), held="spear"),
    "Chancellor": P(hair=((70, 60, 54), (46, 38, 34)), hair_style="rim", shirt=((30, 28, 34),), dress=(30, 28, 34),
                    cape=(200, 160, 50), held="book"),
    "Archivist": P(hair=((190, 190, 196), (150, 150, 156)), hair_style="long", shirt=((120, 90, 60),),
                   dress=(120, 90, 60), held="book"),
    # the towns' and cities' people (build_towns.py)
    "Barkeep": P(hair=((60, 40, 26), (40, 26, 16)), beard="moustache", shirt=((150, 100, 60),), apron=WHITE,
                 trousers=((60, 50, 40),)),
    "Barmaid": P(hair=((226, 196, 110), (186, 156, 70)), hair_style="long", shirt=((60, 120, 70),),
                 dress=(60, 120, 70), apron=WHITE),
    "Butcher": P(hair_style="bald", shirt=((200, 70, 70),), apron=WHITE, trousers=((60, 60, 70),), held="axe",
                 bare_arms=True),
    "Fishmonger": P(hair=((70, 50, 30), (50, 34, 20)), beard="stubble", shirt=((60, 100, 160),), apron=WHITE,
                    hat="cap:60 100 160"),
    "Greengrocer": P(hair=((120, 80, 40), (90, 56, 26)), shirt=((70, 140, 60),), apron=(110, 76, 40), hat="straw",
                     held="herbs"),
    "Tailor": P(hair=((40, 30, 24), (20, 14, 12)), hair_style="long", shirt=((150, 60, 130),), dress=(150, 60, 130),
                held="book"),
    "Cobbler": P(hair=((100, 70, 40), (70, 46, 24)), beard="stubble", shirt=((190, 170, 130),), apron=(110, 70, 34),
                 held="hammer"),
    "Armourer": P(hair_style="bald", beard="big", shirt=((90, 90, 96),), apron=(70, 46, 24), worn=("Iron_Helm",),
                  held="hammer", bare_arms=True),
    "Hotelier": P(hair=((160, 160, 166), (120, 120, 126)), hair_style="rim", shirt=((60, 20, 30),), apron=WHITE,
                  trousers=((30, 30, 36),), shoes=((20, 20, 24),)),
    "Doctor": P(hair=((130, 130, 130), (96, 96, 96)), beard="moustache", shirt=(WHITE,), trousers=((40, 40, 50),),
                held="book"),
    "Nurse": P(hair=((90, 60, 40), (60, 40, 24)), hair_style="long", shirt=((90, 130, 200),), dress=(90, 130, 200),
               apron=WHITE, hat="kerchief:250 250 250"),
    "Constable": P(shirt=((30, 40, 90),), trousers=((30, 40, 90),), hat="cap:30 40 90", beard="moustache",
                   held="club"),
    "Sheriff": P(hair=((110, 80, 50), (80, 56, 30)), beard="stubble", shirt=((140, 100, 60),), cape=(90, 64, 40),
                 trousers=((70, 60, 50),), hat="cap:110 76 40", held="spear"),
    "Clerk": P(hair=((70, 50, 34), (46, 32, 20)), shirt=((120, 120, 130),), trousers=((60, 60, 70),), held="book"),
    "Carter": P(hair=((140, 100, 50), (100, 70, 30)), beard="stubble", shirt=((190, 160, 110),), hat="straw",
                trousers=((90, 70, 46),)),
}


# ------------------------------------------------------------------ drawing
def blank():
    return [[None] * 32 for _ in range(32)]


def put(img, x, y, c, under=False):
    if 0 <= x < 32 and 0 <= y < 32 and (not under or img[y][x] is None):
        img[y][x] = c


def rect(img, x0, y0, x1, y1, c, under=False):
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            put(img, x, y, c, under)


def colour_body(g, sp):
    """The player's code grid in this person's colours."""
    skin, hair = sp["skin"], sp["hair"]
    shirt = sp["shirt"][0]
    trousers = sp["trousers"][0]
    shoes = sp["shoes"][0]
    if sp["bones"]:
        bone, bone_d = (226, 222, 204), (170, 164, 140)
        skin, hair, shirt, trousers, shoes = (bone, bone_d), None, bone, bone, bone
    pal = {"S": skin[0], "s": skin[1], "E": sp["eyes"], "M": sp["mouth"],
           "T": shirt, "t": shade(shirt, 1.18) if not sp["bare_arms"] else skin[0], "k": shade(shirt, 0.62),
           "P": trousers if not sp["bare_legs"] else skin[0], "p": shade(trousers, 0.7) if not sp["bare_legs"] else skin[1],
           "B": shoes if not sp["bare_legs"] else skin[1], "b": shade(shoes, 0.6) if not sp["bare_legs"] else skin[1]}
    if hair is None or sp["hair_style"] == "bald":
        pal["H"], pal["h"] = skin[0], skin[1]
    else:
        pal["H"], pal["h"] = hair
    img = blank()
    for y in range(32):
        for x in range(32):
            c = g[y][x]
            if c:
                img[y][x] = pal[c]
    return img


def head_box(g):
    pts = [(x, y) for y in range(0, 12) for x in range(32) if g[y][x]]
    return min(x for x, _ in pts), max(x for x, _ in pts), min(y for _, y in pts)


def hand_box(d, f):
    """(x0, x1, top, bottom) of the hand that holds things: d in 1, 2, 4 (west is drawn as east, then mirrored)."""
    return BW.weapon_hand(d, f)


def draw_person(name, d, f):
    sp = PEOPLE[name]
    dd = "2" if d == "8" else d                       # west = east mirrored
    g = BP.draw(dd, f)
    img = colour_body(g, sp)
    x0, x1, top = head_box(g)
    hair = sp["hair"]
    # --- skeleton details
    if sp["bones"]:
        dark = (60, 56, 50)
        if dd == "4":
            for x in (CX - 3, CX - 2, CX + 1, CX + 2):
                put(img, x, 7, dark)
                put(img, x, 6, dark)
            for x in range(CX - 2, CX + 2):
                put(img, x, 10, dark if x % 2 else (226, 222, 204))
        elif dd == "2":
            put(img, CX + 2, 7, dark); put(img, CX + 2, 6, dark); put(img, CX + 1, 7, dark)
        for y in (13, 15, 17, 19):                    # ribs
            for x in range(CX - 4, CX + 4):
                if img[y][x] == (226, 222, 204) and x not in (CX - 1, CX):
                    img[y][x] = (110, 104, 92)
        for y in range(21, 29):                       # thin legs: shade the inner columns
            for x in range(32):
                if img[y][x] == (226, 222, 204) and (x in (CX - 2, CX + 1)):
                    img[y][x] = (170, 164, 140)
    # --- hair styles
    if hair and sp["hair_style"] == "long":
        if dd in ("1", "4"):
            for y in range(4, 14):
                put(img, x0 - 1, y, hair[1], under=True)
                put(img, x1 + 1, y, hair[1], under=True)
                put(img, x0, y, hair[0] if dd == "1" or y < 6 or y > 11 else img[y][x0])
                put(img, x1, y, hair[0] if dd == "1" or y < 6 or y > 11 else img[y][x1])
            if dd == "1":
                rect(img, x0, 10, x1, 14, hair[0])
                rect(img, x0, 14, x1, 14, hair[1])
        else:
            rect(img, x0, 4, x0 + 2, 14, hair[0])
            rect(img, x0, 14, x0 + 2, 14, hair[1])
    if hair and sp["hair_style"] == "messy":
        for x in range(x0, x1 + 1, 2):
            put(img, x, top - 1, hair[1])
    if hair and sp["hair_style"] == "rim":            # bald on top, hair round the sides
        for y in range(top, top + 2):
            for x in range(32):
                if img[y][x] in hair:
                    img[y][x] = sp["skin"][0]
    # --- beard
    b = sp["beard"]
    if b and dd != "1":
        col = {"big": hair, "white": ((240, 240, 240), (200, 200, 206)), "grey": ((170, 170, 170), (130, 130, 130)),
               "gold": hair, "stubble": None, "moustache": ((60, 40, 20), (40, 26, 10))}[b]
        if b == "stubble":
            for x in range(CX - 3, CX + 3, 2):
                put(img, x, 10, shade(sp["skin"][1], 0.8))
        elif b == "moustache":
            xs = range(CX - 2, CX + 2) if dd == "4" else range(CX + 1, CX + 4)
            for x in xs:
                put(img, x, 9, col[1])
        else:
            bottom = 16 if b in ("big", "white") else 12
            xs = (CX - 4, CX + 3) if dd == "4" else (CX, CX + 4)
            for y in range(9, bottom + 1):
                w = 0 if y < 13 else (y - 12)
                for x in range(xs[0] + w, xs[1] - w + 1):
                    if not (dd == "4" and y == 9 and x in (CX - 1, CX)):
                        put(img, x, y, col[0] if (x + y) % 3 else col[1])
    # --- clothes
    if sp["dress"]:
        c = sp["dress"]
        for y in range(19, 28):
            grow = (y - 19) // 3
            if dd in ("1", "4"):
                xa, xb = CX - 5 - grow, CX + 4 + grow
            else:
                xa, xb = CX - 4 - grow, CX + 3 + grow
            for x in range(xa, xb + 1):
                put(img, x, y, shade(c, 0.75) if x in (xa, xb) else c)
        if sp.get("stars"):
            for x, y in ((CX - 3, 14), (CX + 2, 17), (CX - 2, 22), (CX + 3, 25), (CX - 5, 26), (CX + 1, 20)):
                if img[y][x] == c or img[y][x] == shade(c, 1.0):
                    put(img, x, y, (250, 230, 90))
    if sp["apron"] and dd != "1" and not sp["worn"]:
        c = sp["apron"]
        xs = (CX - 3, CX + 2) if dd == "4" else (CX + 1, CX + 3)
        for y in range(14, 25):
            for x in range(xs[0], xs[1] + 1):
                if img[y][x] is not None:
                    put(img, x, y, shade(c, 0.85) if x == xs[1] else c)
    if sp["apron"] and dd == "1":
        put(img, CX - 1, 19, sp["apron"]); put(img, CX, 19, sp["apron"])
    if sp.get("patches"):
        for x, y in ((CX - 3, 15), (CX + 2, 18), (CX - 2, 24)):
            put(img, x, y, (140, 120, 80)) if img[y][x] else None
    if sp["cape"]:
        c = sp["cape"]
        if dd == "1":
            rect(img, CX - 6, 12, CX + 5, 26, c)
            rect(img, CX - 6, 26, CX + 5, 26, shade(c, 0.7))
        elif dd == "4":
            rect(img, CX - 8, 12, CX + 7, 26, c, under=True)
        else:
            rect(img, CX - 7, 12, CX - 3, 26, c, under=True)
    # --- ears
    if sp["ears"] and dd in ("1", "4"):
        for x, y in ((x0 - 1, 6), (x0 - 2, 5), (x1 + 1, 6), (x1 + 2, 5)):
            put(img, x, y, sp["skin"][1])
    if sp["ears"] and dd == "2":
        put(img, CX - 2, 6, sp["skin"][1]); put(img, CX - 3, 5, sp["skin"][1])
    # --- hats
    hat = sp["hat"] or ""
    kind, _, arg = hat.partition(":")
    col = tuple(int(v) for v in arg.split()) if arg else None
    if kind == "straw":
        straw, dark = (230, 200, 110), (180, 140, 60)
        rect(img, x0 - 2, top + 1, x1 + 2, top + 1, straw)
        rect(img, x0 + 1, top - 2, x1 - 1, top, straw)
        rect(img, x0 + 1, top, x1 - 1, top, dark)
    elif kind == "wizard":
        hc = sp["shirt"][0]
        rect(img, x0 - 1, top + 2, x1 + 1, top + 2, shade(hc, 0.8))
        for i, y in enumerate(range(top + 1, -1, -1)):
            rect(img, x0 + i, y, x1 - i, y, hc)
        put(img, CX, 0, (250, 230, 90)); put(img, CX - 2, top, (250, 230, 90))
    elif kind == "crown":
        gold, gd = (250, 210, 60), (190, 140, 20)
        rect(img, x0 + 1, top, x1 - 1, top + 1, gold)
        for x in (x0 + 1, CX - 1, x1 - 1):
            put(img, x, top - 1, gold)
        put(img, CX - 1, top + 1, (200, 30, 40)) if dd == "4" else None
        rect(img, x0 + 1, top + 1, x1 - 1, top + 1, gd)
    elif kind == "chef":
        rect(img, x0 + 1, 0, x1 - 1, top + 1, WHITE)
        rect(img, x0 + 1, top + 2, x1 - 1, top + 2, (200, 200, 206))
    elif kind == "cap":
        rect(img, x0, top, x1, top + 2, col)
        rect(img, x0, top + 2, x1, top + 2, shade(col, 0.7))
        if dd == "2":
            rect(img, x1 + 1, top + 2, x1 + 2, top + 2, shade(col, 0.7))
        if dd == "4":
            rect(img, x0 + 2, top + 3, x1 - 2, top + 3, shade(col, 0.7))
    elif kind == "kerchief":
        rect(img, x0, top, x1, top + 2, col)
        if dd == "1":
            put(img, CX - 1, top + 3, col); put(img, CX, top + 4, col)
    elif kind == "sou'wester":
        yel = (236, 200, 40)
        rect(img, x0 - 1, top + 2, x1 + 1, top + 2, shade(yel, 0.8))
        rect(img, x0 + 1, top, x1 - 1, top + 1, yel)
    elif kind == "hood":
        for y in range(top, 12):
            for x in range(x0 - 1, x1 + 2):
                if dd == "1" and img[y][x] is not None:
                    img[y][x] = col if y < 11 else img[y][x]
                elif dd == "4" and (x <= x0 or x >= x1 or y <= top + 2):
                    put(img, x, y, col if (x, y) != (x0 - 1, y) else shade(col, 0.8))
                elif dd == "2" and x <= x0 + 3 and img[y][x] is not None:
                    img[y][x] = col
            if dd == "4":
                put(img, x0 - 1, y, shade(col, 0.8), under=True)
                put(img, x1 + 1, y, shade(col, 0.8), under=True)
    elif kind == "horns":
        horn = (236, 226, 200)
        for x, y in ((x0 + 1, top - 1), (x0, top - 2), (x1 - 1, top - 1), (x1, top - 2)):
            put(img, x, y, horn)
    # --- held things
    held = sp["held"]
    if held:
        draw_held(img, held, dd, f)
    if d == "8":
        img = [list(reversed(r)) for r in img]
    # --- worn armour (already made for every direction), then a tabard over it
    for item in sp["worn"]:
        slot = "Head" if item.endswith("_Helm") else "Body"          # (any metal: Mithril_Helm, Steel_Platebody...)
        over = BW.worn_frames(item, slot)[d + f]
        for y in range(32):
            for x in range(32):
                if over[y][x]:
                    img[y][x] = over[y][x]
    if sp["apron"] and sp["worn"] and d != "1":
        c = sp["apron"]
        xs = (CX - 2, CX + 1) if d == "4" else ((CX + 1, CX + 3) if d == "2" else (CX - 4, CX - 2))
        for y in range(14, 24):
            for x in range(xs[0], xs[1] + 1):
                if img[y][x] is not None:
                    img[y][x] = shade(c, 0.8) if y in (14, 23) else c
        if d == "4":
            put(img, CX - 1, 17, (240, 200, 60)); put(img, CX, 17, (240, 200, 60))
    return img


WOOD = ((176, 120, 64), (130, 84, 40), (84, 52, 22))
METAL = ((220, 220, 228), (160, 160, 168), (100, 100, 108))


def draw_held(img, held, d, f):
    hx0, hx1, ht, hb = hand_box(d, f)
    if d == "4":
        x = hx0 - 1
    elif d == "1":
        x = hx1 + 1
    else:                                         # side on: held out in front, clear of the face and body
        x = CX + 6 if held in ("spear", "pitchfork", "staff", "rod") else CX + 5
    if held in ("spear", "pitchfork", "staff"):
        top = 0 if held != "staff" else 3
        for y in range(top + 2, min(31, hb + 7)):
            put(img, x, y, WOOD[1] if y % 4 else WOOD[2])
        if held == "spear":
            put(img, x, top, METAL[0]); put(img, x, top + 1, METAL[0])
            put(img, x - 1, top + 2, METAL[1]); put(img, x + 1, top + 2, METAL[1]); put(img, x, top + 2, METAL[1])
        elif held == "pitchfork":
            for dx in (-2, 0, 2):
                put(img, x + dx, top, METAL[1]); put(img, x + dx, top + 1, METAL[1])
            rect(img, x - 2, top + 2, x + 2, top + 2, METAL[2])
        else:
            put(img, x, top + 1, WOOD[0]); put(img, x - 1, top + 2, WOOD[2]); put(img, x + 1, top + 2, WOOD[2])
    elif held in ("pickaxe", "axe", "hammer", "club"):
        for y in range(ht - 7, hb + 2):
            put(img, x, y, WOOD[1] if held != "club" else WOOD[0])
            if held == "club" and y < ht - 2:
                put(img, x + 1, y, WOOD[1])
        y = ht - 8
        if held == "pickaxe":
            rect(img, x - 3, y, x + 3, y, METAL[1]); put(img, x - 4, y + 1, METAL[2]); put(img, x + 4, y + 1, METAL[2])
        elif held == "axe":
            rect(img, x + 1, y, x + 3, y + 3, METAL[1]); rect(img, x + 3, y, x + 3, y + 3, METAL[0])
        elif held == "hammer":
            rect(img, x - 2, y, x + 2, y + 2, METAL[2]); rect(img, x - 2, y, x + 2, y, METAL[1])
        else:
            rect(img, x - 1, y, x + 2, y + 2, WOOD[2])
    elif held == "rusty_sword":
        rust = ((170, 150, 120), (130, 104, 80))
        for y in range(ht - 10, ht - 1):
            put(img, x, y, rust[0]); put(img, x + 1, y, rust[1])
        rect(img, x - 1, ht - 1, x + 2, ht - 1, (90, 70, 40))
    elif held == "rod":
        for i in range(14):
            put(img, x + (i // 3 if d == "2" else -(i // 3) if d == "4" else i // 3), hb - i, WOOD[0] if i % 2 else WOOD[1])
        tipx = x + (4 if d != "4" else -4)
        for y in range(hb - 13, hb - 6):
            put(img, tipx + (1 if d != "4" else -1), y, (230, 230, 230))
    elif held == "bucket":
        rect(img, x - 1, hb + 1, x + 2, hb + 4, (150, 110, 60))
        rect(img, x - 1, hb + 1, x + 2, hb + 1, (110, 76, 36))
        rect(img, x, hb + 2, x + 1, hb + 2, (240, 240, 240))
    elif held == "book":
        rect(img, x - 1, ht - 2, x + 2, hb, (120, 30, 30))
        rect(img, x - 1, ht - 2, x - 1, hb, (240, 230, 200))
    elif held == "bow":                           # a bow held upright: a curved stave and its string
        top, bot = ht - 9, hb + 5
        mid = (top + bot) // 2
        for y in range(top, bot + 1):
            bend = 2 - min(2, abs(y - mid) // 3)
            put(img, x + bend if d != "8" else x - bend, y, WOOD[1] if (y - top) % 5 else WOOD[2])
        for y in range(top + 1, bot):
            put(img, x - 1 if d != "8" else x + 1, y, (220, 214, 200))
    elif held.startswith("orb_staff"):            # a staff with a glowing orb on top
        glow = tuple(int(v) for v in held.split(":")[1].split()) if ":" in held else (255, 160, 60)
        top = 3
        for y in range(top + 3, min(31, hb + 7)):
            put(img, x, y, WOOD[1] if y % 4 else WOOD[2])
        for dx, dy in ((0, 0), (-1, 1), (1, 1), (0, 2), (0, 1)):
            put(img, x + dx, top + dy, glow)
        put(img, x, top + 1, (255, 255, 240))
    elif held == "herbs":
        for dx, dy in ((0, 0), (-1, -1), (1, -2), (0, -3), (-1, -4)):
            put(img, x + dx, ht + dy, (70, 160, 60))
        put(img, x, hb, (90, 60, 30))


def frames(name):
    return {d + f: draw_person(name, d, f) for d in "1248" for f in "abc"}


def main():
    made = {}
    for name in PEOPLE:
        fr = frames(name)
        made[name] = fr
        changed = K.save("Entities", name, fr["4a"])
        print(("wrote " if changed else "unchanged ") + name)
    if "--preview" in sys.argv:
        sheet = []
        for name in PEOPLE:
            for d in "4128":
                for f in "ab":
                    sheet.append(made[name][d + f])
        K.sheet(p("Dev", "Renders", "People preview.png"), sheet, scale=3, cols=16)
        print("preview: Dev\\Renders\\People preview.png (two people per row: S N E W, standing and stepping)")


if __name__ == "__main__":
    main()
