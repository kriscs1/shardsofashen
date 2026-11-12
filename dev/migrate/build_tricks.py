"""Tricks, and the silly quests that use them (dsengine/tricks.py: invisibility, body swaps).

  * The Invisibility Potion (Spells.ini Effect=Invisible: no monster sees you for 45 s) and the Swap scroll (Effect=Swap:
    you and a creature or a townsperson swap bodies for 30 s; Entities.ini Swap=1 says who can be swapped with).
  * The Invisible Apprentice (PipQuest 0-2): Pip, in the Wizards' Court's great hall, drank his own potion and can't
    be seen; only his hat and spectacles. An egg, a feather and two cave mushrooms for the cure. He gives you
    invisibility potions and the Swap scroll ("I spent last Tuesday as a cat"), and the potion's recipe is brewed.
  * Lady Pettigrew's Hat (HatQuest 0-2): the geese of Goose Green, east of Northport (5,5,0), have her hat on their
    nest, and they are not reasonable geese. Go unseen, or swap with her own tame goose, and fetch it.
  * Granny Bramble's Practice Hex (HexQuest 0-2): a hedge witch at Fenwick's market practises a hex on you (your
    Strength drained to nothing: Boost.Skill) and then wants the rats round the market cleared. Your sword's no use:
    a spell, a potion, or someone else's body.
  * Pip's Spectacles (SpectaclesQuest 0-8): Pip's good spectacles went missing the afternoon a cat had his body.
    Only the animals know, and they only talk to another animal: swap, and ask Inkwell, the Court's cat (a fish
    first), who sends you to Biscuit the dog outside the gate, who gave them to Henrietta the hen, who has been
    sitting on them in her nest by the pond, hoping they'd hatch.
  * Secrets in Bert's tower: a cat flap to his secret biscuit tin (only a cat fits), and a big red button.
  * Pictures (the potion, the scroll, Pip, the goose - the duck's frames, whitened - its nest, the hat, the button,
    the flap, Pip's spectacles, the hen's nest) and sounds (Vanish, Appear, Swap, Splosh).

Safe to run again.

  python -I "dev\\migrate\\build_tricks.py"
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import Ini, p, sound_file                      # noqa: E402
import build_sounds as SND                     # noqa: E402
import build_sprites as BS                     # noqa: E402
import sprite_kit as K                         # noqa: E402
import story_kit as SK                         # noqa: E402
from story_kit import Map, obj_line            # noqa: E402

MAKER = "build_tricks.py"
COURT, PIP = "21,5,0", (11, 9)
TOWER, BUTTON, FLAP = "21,5,1", (19, 6), (18, 8)
GREEN, LADY, TAME, NEST = "5,5,0", (12, 7), (13, 6), (16, 3)
GEESE = [(15, 2), (17, 4), (15, 4), (17, 2)]   # (round the nest: they mind it, not the road)
CAT, DOG, HEN, HEN_NEST = (10, 13), (15, 19), (19, 20), (19, 19)   # (on COURT: Pip's Spectacles)
HENS = [(22, 20), (17, 21)]
MARKET, GRANNY = "21,12,0", (3, 17)
RATS = [(4, 14), (2, 13), (4, 12), (2, 11)]
SWAPPABLE = ("Cat", "Strawberry_Cat", "Chicken", "Duck", "Goose", "Sheep", "Cow", "Rabbit", "Dog", "Villager",
             "Farmer", "Merchant", "Guard")


# ================================================================== pictures
def whiten(img):
    """The duck as a goose: white, its beak and feet orange still."""
    def keep(c):
        r, g, b = c
        return r > 180 and 70 < g < 190 and b < 90                # (orange: beak and feet)
    return K.hue_shift(img, sat=0.05, val_mul=1.45, pred=lambda c: not keep(c))


def potion():
    img = K.hue_shift(K.load("Entities", "Owl_Potion"), sat_mul=0.25, val_mul=1.35)
    for x, y in ((10, 6), (22, 9), (8, 20), (24, 22)):            # (sparkles round a bottle you can barely see)
        K.put(img, x, y, (255, 255, 255))
    return img


def pip_sprite():
    """Pip, as much as anyone can see of him: a floating pointed hat and a pair of round spectacles."""
    img = K.new()
    for y in range(3, 16):                                        # (the hat)
        half = 1 + (y - 3) * 7 // 12
        for x in range(16 - half, 17 + half):
            K.put(img, x, y, (70, 60, 150) if x > 16 - half + 1 else (100, 90, 190))
    for x in range(6, 27):
        K.put(img, x, 16, (60, 50, 130))
        K.put(img, x, 17, (40, 34, 90))
    for cx in (12, 20):                                           # (the spectacles)
        for a in range(0, 360, 30):
            K.put(img, int(round(cx + 3 * math.cos(math.radians(a)))), int(round(22 + 3 * math.sin(math.radians(a)))),
                  (200, 170, 70))
    for x in range(15, 18):
        K.put(img, x, 22, (200, 170, 70))
    K.put(img, 11, 21, (255, 255, 255))
    K.put(img, 19, 21, (255, 255, 255))
    return K.outline_img(img, (30, 26, 60))


def hat():
    img = K.new()
    for x in range(4, 28):                                        # (a brim as wide as a cartwheel)
        for y in range(20, 24):
            if ((x - 16) / 12.0) ** 2 + ((y - 22) / 2.2) ** 2 <= 1:
                K.put(img, x, y, (150, 60, 160))
    for y in range(12, 21):
        for x in range(10, 23):
            K.put(img, x, y, (170, 70, 180) if x < 20 else (130, 50, 140))
    for x in range(10, 23):
        K.put(img, x, 18, (255, 220, 90))                         # (its band)
    for i in range(12):                                           # (and a great curling feather)
        K.put(img, 21 + i // 2, 12 - i, (255, 240, 200))
        K.put(img, 22 + i // 2, 12 - i, (240, 200, 120))
    return K.outline_img(img, (50, 20, 50))


def nest():
    img = K.new()
    for y in range(18, 29):
        for x in range(4, 29):
            if ((x - 16) / 12.0) ** 2 + ((y - 24) / 5.0) ** 2 <= 1:
                K.put(img, x, y, (170, 140, 80) if (x * 3 + y) % 4 else (130, 100, 50))
    for cx in (12, 17, 21):
        for y in range(19, 25):
            for x in range(cx - 2, cx + 3):
                if ((x - cx) / 2.5) ** 2 + ((y - 22) / 3.0) ** 2 <= 1:
                    K.put(img, x, y, (245, 240, 225))
    return K.outline_img(img, (60, 44, 20))


def spectacles():
    """Pip's good spectacles: round, gold, a little straw on them."""
    img = K.new()
    for cx in (11, 21):
        for a in range(0, 360, 15):
            for r in (4.5, 5.0):
                K.put(img, int(round(cx + r * math.cos(math.radians(a)))), int(round(18 + r * math.sin(math.radians(a)))),
                      (220, 180, 70))
        K.put(img, cx - 2, 16, (255, 255, 255))
    for x in range(15, 18):
        K.put(img, x, 17, (220, 180, 70))
    for x, y in ((6, 17), (5, 16), (26, 17), (27, 16)):           # (the arms)
        K.put(img, x, y, (190, 150, 60))
    K.put(img, 14, 23, (230, 200, 110))                           # (and a bit of straw)
    K.put(img, 15, 24, (230, 200, 110))
    return K.outline_img(img, (70, 50, 20))


def hen_nest():
    """A hen's nest, an egg in it, and something round and gold glinting under the straw."""
    img = K.new()
    for y in range(20, 29):
        for x in range(6, 27):
            if ((x - 16) / 10.0) ** 2 + ((y - 25) / 4.0) ** 2 <= 1:
                K.put(img, x, y, (190, 160, 90) if (x * 5 + y) % 3 else (140, 110, 55))
    for y in range(20, 25):
        for x in range(12, 17):
            if ((x - 14) / 2.4) ** 2 + ((y - 22) / 2.8) ** 2 <= 1:
                K.put(img, x, y, (240, 225, 200))
    for a in range(0, 360, 40):
        K.put(img, int(round(20 + 2 * math.cos(math.radians(a)))), int(round(24 + 2 * math.sin(math.radians(a)))),
              (230, 190, 70))
    K.put(img, 21, 23, (255, 255, 230))
    return K.outline_img(img, (60, 44, 20))


def button():
    img = K.new()
    for y in range(18, 30):                                       # (a stone pedestal)
        for x in range(10, 23):
            K.put(img, x, y, (140, 136, 130) if x < 18 else (110, 106, 100))
    for y in range(11, 18):                                       # (and the great red button on it)
        for x in range(8, 25):
            if ((x - 16) / 8.0) ** 2 + ((y - 17) / 6.0) ** 2 <= 1:
                K.put(img, x, y, (235, 40, 30) if y > 13 else (255, 120, 100))
    return K.outline_img(img, (40, 20, 20))


def flap():
    img = K.new()
    for y in range(20, 30):                                       # (a small square flap, low in the wall)
        for x in range(11, 22):
            K.put(img, x, y, (120, 80, 40) if (x + y) % 5 else (90, 60, 30))
    for x in range(11, 22):
        K.put(img, x, 20, (70, 50, 30))
    K.put(img, 16, 26, (200, 180, 90))
    return K.outline_img(img, (40, 26, 14))


def art():
    out = [("Entities", "Invisibility_Potion", potion()),
           ("Entities", "Swap_Scroll", BS.scroll((200, 120, 40), ((255, 210, 120), (200, 120, 40)))),
           ("Entities", "Pip", pip_sprite()), ("Entities", "Fancy_Hat", hat()), ("Entities", "Goose_Nest", nest()),
           ("Entities", "Big_Red_Button", button()), ("Entities", "Cat_Flap", flap()),
           ("Entities", "Pips_Spectacles", spectacles()), ("Entities", "Hen_Nest", hen_nest()),
           ("Entities", "Goose", whiten(K.load("Entities", "Duck")))]
    for f in "abc":
        for d in "28":
            out.append(("Walk", "Goose%s%s" % (d, f), whiten(K.load("Walk", "Duck%s%s" % (d, f)))))
    print("Pictures: %d written" % sum(1 for kind, name, img in out if K.save(kind, name, img)))


SOUNDS = {
    # (Vanish, Appear, Swap and Click: build_soundscape.py)
    # (Honk is a goose's recorded honk: build_voices.py CALLS)
    # a bucket of water, all at once
    "Splosh": lambda: SND.mix((SND.shaped(SND.noise(63, SND.n(0.7), 0.6, high=0.5), 0.005, 4), 0.7),),
}


def sounds():
    for name, fn in SOUNDS.items():
        blob = SND.wav_bytes(fn())
        path = sound_file(name)
        if not (os.path.exists(path) and open(path, "rb").read() == blob):
            with open(path, "wb") as fh:
                fh.write(blob)
            print("wrote sounds\\%s.wav" % name)


# ================================================================== data
def data():
    ents = Ini(p("data", "Entities.ini"))
    for name, keys in (
            ("Invisibility_Potion", [("Type", "MapItem"), ("Use.Words", "Drink"), ("Spell", "Invisibility_Potion"),
                                     ("Stackable", "10"), ("Value", "45"),
                                     ("Examine.Info", "An Invisibility Potion: you can see the bottle if you squint. "
                                                      "No monster sees you for 45 seconds; strike or cast and it's "
                                                      "over.")]),
            ("Swap_Scroll", [("Type", "MapItem"), ("Use.Words", "Cast"), ("Spell", "Swap"), ("Stackable", "10"),
                             ("Value", "90"), ("Examine.Info", "A scroll of Swap: you and a creature (or a person) "
                                                               "trade bodies for 30 seconds. Channeling 5. Read it to "
                                                               "learn the spell for good.")]),
            ("Pip", [("Type", "NPC"), ("Attitude", "Good"), ("Use.Words", "Talk to,Examine"), ("Respawn", "60"),
                     ("Examine.Info", "A hat and a pair of spectacles, hanging in the air, looking at you.")]),
            ("Fancy_Hat", [("Type", "MapItem"), ("Droppable", "0"), ("Value", "0"),
                           ("Examine.Info", "Lady Pettigrew's hat: purple, a brim like a cartwheel, a feather like a "
                                            "small tree. Slightly pecked.")]),
            ("Goose_Nest", [("Type", "StaticObject"), ("Use.Words", "Examine"), ("Solid", "0"),
                            ("Examine.Info", "A nest of straw, three eggs, and an air of menace.")]),
            ("Goose", [("Type", "NPC"), ("Attitude", "Bad"), ("Use.Words", "Attack,Examine"), ("Hitpoints", "6"),
                       ("Attack.Speed", "0.9"), ("Strength", "1"), ("Defence", "1"), ("Aggro.Range", "48"),
                       ("Weapon.Range", "0"), ("Movement.Speed", "2.6"), ("Aggressive", "1"), ("Respawn", "40"),
                       ("Roam.Radius", "2"), ("Chase.Radius", "2"), ("Walk.Speed", "0.7"), ("Kill.Sound", "Bird"),
                       ("Calls", "Honk"), ("Drops", "Feather,1-3,100"), ("Swap", "1"),
                       ("Examine.Info", "A goose. It knows what it did, and it would do it again.")]),
            ("Big_Red_Button", [("Type", "StaticObject"), ("Use.Words", "Press,Examine"), ("Solid", "1"),
                                ("Examine.Info", "A big red button on a stone pedestal. Someone has scratched DO NOT "
                                                 "PRESS on it, crossed it out, and scratched it again.")]),
            ("Pips_Spectacles", [("Type", "MapItem"), ("Droppable", "0"), ("Value", "0"),
                                 ("Display.Name", "Pip's Spectacles"),
                                 ("Examine.Info", "Pip's good spectacles: round, gold, still warm, and a little bit of "
                                                  "straw on them.")]),
            ("Hen_Nest", [("Type", "StaticObject"), ("Use.Words", "Rummage,Examine"), ("Solid", "0"),
                          ("Examine.Info", "A hen's nest of straw by the pond. One egg in it, and something round "
                                           "that glints.")]),
            ("Cat_Flap", [("Type", "StaticObject"), ("Use.Words", "Squeeze Through,Examine"), ("Solid", "1"),
                          ("Examine.Info", "A little flap, low in the wall. It smells faintly of shortbread.")])):
        if ents.section(name) is None:                            # (made here once: tuned since, kept so)
            for k, v in keys:
                ents.set(name, k, v)
    for name in SWAPPABLE:
        if ents.section(name) is not None:
            ents.set(name, "Swap", "1")
    ents.save(p("data", "Entities.ini"))
    spells = Ini(p("data", "Spells.ini"))
    for name, keys in (
            ("Invisibility_Potion", [("Kind", "Potion"), ("Scroll", "Invisibility_Potion"), ("Effect", "Invisible"),
                                     ("Skill", "Alchemy"), ("Level", "1"), ("Duration", "45"),
                                     ("Leaves", "Empty_Vial")]),
            ("Swap", [("Cost", "8"), ("Cooldown", "90"), ("Scroll", "Swap_Scroll"), ("Effect", "Swap"), ("Level", "5"),
                      ("Duration", "30"), ("Range", "160"), ("Sound", "Swap"), ("XP", "0.5")])):
        if spells.section(name) is None:
            spells.replace_section(name, keys)
    spells.save(p("data", "Spells.ini"))
    racks = Ini(p("data", "ItemRacks.ini"))
    s = racks.section("CRAFT-Potion_Making")
    if s is not None and not any(v.startswith("Invisibility_Potion,") for k, v in s[1] if k):
        n = sum(1 for k, v in s[1] if k and k.startswith("Item"))
        racks.set("CRAFT-Potion_Making", "Item%d" % (n + 1), "Invisibility_Potion,Cave_Mushroom 2 Feather 1,0.5,6")
        racks.save(p("data", "ItemRacks.ini"))


# ================================================================== places
def place(map_name, lines):
    """Each line, unless it's there already: the one with its Id, or (with none) its kind on its spot. (Moved since,
    or given a Chase=: left as it is.)"""
    m = Map(map_name)

    def there(ln):
        f = ln.split("\t")
        pid = next((o[3:] for o in f[-1].split() if o.startswith("Id=")), "")
        if pid:
            return any(("Id=%s" % pid) in e.split("\t")[-1].split() for e in m.ents)
        return any(e.split("\t")[:4] == f[:4] for e in m.ents)
    added = [ln for ln in lines if not there(ln)]
    if added:
        m.ents += added
        m.save()
        print("%s: %d added" % (map_name, len(added)))


def places():
    place(COURT, [obj_line("NPC", "Pip", PIP[0], PIP[1], "Attitude=Good Stand=1 Id=Pip_The_Apprentice Name=Pip"),
                  obj_line("NPC", "Cat", CAT[0], CAT[1], "Attitude=Good Zone=8,11,15,15 Pause=4-12 Id=Court_Cat "
                                                         "Name=Inkwell"),
                  obj_line("NPC", "Dog", DOG[0], DOG[1], "Attitude=Good Zone=13,18,18,21 Pause=3-8 Id=Court_Dog "
                                                         "Name=Biscuit"),
                  obj_line("NPC", "Chicken", HEN[0], HEN[1], "Attitude=Passive Zone=18,19,21,21 Pause=4-10 Id=Court_Hen "
                                                             "Name=Henrietta"),
                  obj_line("StaticObject", "Hen_Nest", HEN_NEST[0], HEN_NEST[1], "Id=Court_Hen_Nest")] +
          [obj_line("NPC", "Chicken", x, y, "Attitude=Passive Zone=17,19,23,21 Pause=3-8") for x, y in HENS])
    place(TOWER, [obj_line("StaticObject", "Big_Red_Button", BUTTON[0], BUTTON[1], "Id=Berts_Button"),
                  obj_line("StaticObject", "Cat_Flap", FLAP[0], FLAP[1], "Id=Berts_Cat_Flap")])
    zone = "Zone=%d,%d,%d,%d" % (15, 2, 17, 4)
    place(GREEN, [obj_line("NPC", "Woman", LADY[0], LADY[1], "Attitude=Good Stand=1 Face=E Id=Lady_Pettigrew "
                                                            "Name=Lady_Pettigrew"),
                  obj_line("NPC", "Goose", TAME[0], TAME[1], "Attitude=Good Zone=12,6,14,7 Pause=3-8 Id=Tame_Goose "
                                                             "Name=Lady_Pettigrew's_Goose"),
                  obj_line("StaticObject", "Goose_Nest", NEST[0], NEST[1], "Id=Goose_Green_Nest")] +
          [obj_line("NPC", "Goose", x, y, "Attitude=Bad %s Pause=2-6" % zone) for x, y in GEESE])
    m = Map(GREEN)
    if not SK.has_id(m, "Goose_Green"):
        SK.place_id(m, "Goose_Green", NEST[0], NEST[1] + 2)
        m.save()
    place(MARKET, [obj_line("NPC", "Old_Woman", GRANNY[0], GRANNY[1], "Attitude=Good Stand=1 Face=E "
                                                                      "Id=Granny_Bramble Name=Granny_Bramble")])
    SK.place_label("Places", "Goose Green", "Goose_Green")


# ================================================================== the quests
NEW = set()


def quest(name, *a, **k):
    """A quest, the first time only (its rumours and standing were added since: kept)."""
    if Ini(p("data", "Quests.ini")).section(name) is None:
        NEW.add(name)
        SK.quest(name, *a, **k)


def section(path, name, keys):
    if name in NEW:
        SK.section(path, name, keys)


def at(t, dy=-8):
    return "%d,%d" % ((t[0] - 1) * 32, (t[1] - 1) * 32 + dy)


FAR = [("@far",), ("Display.Message", "DarkRed", "You are too far away!", "Denied"), ("End",)]


def pip():
    quest("The Invisible Apprentice", "Pip", "PipQuest", {
        0: "Someone in the Wizards' Court's great hall keeps saying hello. There's no one there.",
        1: "Bring Pip what he needs to be seen again: an egg, a feather and two cave mushrooms."}, 2,
        markers={0: "Pip_The_Apprentice", 1: "Pip_The_Apprentice"}, kind="Side", requires="Passage to the Mainland")
    section(p("data", "Quests.ini"), "The Invisible Apprentice",
               [("Reward.Items", "Invisibility_Potion 2 Swap_Scroll 1"), ("Reward.Shards", "10"),
                ("Reward.XP", "Alchemy 2"),
                ("Reward.Standing", "Court 10")])
    SK.write_script("Talk to Pip_The_Apprentice", [
        ("Get.Value", "ATTRIBUTE", "PipQuest", "Variable.1$"),
        (">Conditional", "$Variable.1=0", "@s1"),
        (">Quest.Can.Start", "PipQuest", "@chat"),
        SK.say("Pip", "Hello! No, here. HERE. You're looking at a hat stand.\\I'm Pip, apprentice to the Court, and I "
                      "may have drunk my own invisibility potion. All of it. Three days ago. I keep getting sat on.",
               ("Can I help?", "@help"), ("Good luck with that.", "@end")),
        ("@help",),
        SK.say("Pip", "Would you? The cure's simple: an egg (for the shell: it's the seeing kind of thing), a feather "
                      "(to tickle the potion out of me, don't ask), and two cave mushrooms. The Magister says I'm not "
                      "to leave the hall in case someone steps on me.", ("I'll fetch them.", "@start")),
        ("@start",), ("Update.Attribute", "PipQuest", "=1"),
        ("Display.Message", "Yellow", "Quest started: The Invisible Apprentice.", "Quest"),
        ("End",),
        ("@s1",), (">Conditional", "$Variable.1=1", "@chat"),
        (">Got.Item", "Egg", "1", "@missing"),
        (">Got.Item", "Feather", "1", "@missing"),
        (">Got.Item", "Cave_Mushroom", "2", "@missing"),
        ("Take.Item", "Egg", "1"), ("Take.Item", "Feather", "1"), ("Take.Item", "Cave_Mushroom", "2"),
        ("Play.Sound", "Appear"),
        ("Display.Message", "Cyan", "Pip mixes it all in his hat, drinks it, sneezes three times..", "-"),
        ("Update.Attribute", "PipQuest", "=2"),
        SK.say("Pip", "..and? Can you see me? You can see my SPECTACLES? Oh, that's the spectacles. Well. Progress!\\"
                      "Take the rest of my potions, I'm off them. And this: a scroll of Swap. I spent last Tuesday as "
                      "a cat by mistake. Honestly, best day of the week.", ("Thank you, Pip. I think.", "@end")),
        ("Display.Message", "Yellow", "Quest complete: The Invisible Apprentice!", "Quest"),
        ("End",),
        ("@missing",), SK.say("Pip", "An egg, a feather and two cave mushrooms. I'd fetch them myself, but people keep "
                                     "walking into me.", ("I'll keep looking.", "@end")),
        ("End",),
        ("@chat",),                                   # (Pip's Spectacles: Variable.1 is that quest's from here)
        ("Get.Value", "ATTRIBUTE", "SpectaclesQuest", "Variable.1$"),
        (">Conditional", "$Variable.1=0", "@g1"),
        (">Quest.Can.Start", "SpectaclesQuest", "@plain"),
        SK.say("Pip", "Is that you? Or another hat stand? These aren't my spectacles: they're the Magister's spare "
                      "pair, and everything past my nose is soup.\\My good ones went missing last Tuesday. The day I was "
                      "a cat. Well: the day the cat was me. It had my body all afternoon, and when I got it back, no "
                      "spectacles.", ("What did the cat do with them?", "@what"), ("Good luck, Pip.", "@end")),
        ("@what",),
        SK.say("Pip", "Ask her! Oh. You can't: Inkwell won't talk to people, only to other animals. She's the Court's "
                      "cat, she's in the courtyard, and she was me.\\You've had a Swap scroll from me. Here's another, "
                      "in case you've used it. Be something with whiskers and ask nicely.",
               ("I'll ask her.", "@begin")),
        ("@begin",), ("Update.Attribute", "SpectaclesQuest", "=1"),
        ("Give.Item", "Swap_Scroll", "1"),
        ("Display.Message", "Yellow", "Quest started: Pip's Spectacles.", "Quest"),
        ("End",),
        ("@g1",), (">Conditional", "$Variable.1=7", "@g2"),
        (">Got.Item", "Pips_Spectacles", "1", "@lost"),
        ("Take.Item", "Pips_Spectacles", "1"),
        ("Update.Attribute", "SpectaclesQuest", "=8"),
        ("Play.Sound", "Appear"),
        SK.say("Pip", "My SPECTACLES! In a hen's nest? They're warm. ...Oh. Oh, I can see. You've got a face! "
                      "Everyone's got faces! I'd quite forgotten.", ("Glad to help, Pip.", "@done")),
        ("@done",),
        ("Display.Message", "Yellow", "Quest complete: Pip's Spectacles!", "Quest"),
        ("End",),
        ("@lost",), SK.say("Pip", "You found them and you've lost them again? Have another look in that nest.",
                           ("I will.", "@end")),
        ("End",),
        ("@g2",), (">Conditional", "$Variable.1=8", "@asking"),
        SK.say("Pip", "Everything's so SHARP. I keep looking at things. The Magister says I can stop now.",
               ("Goodbye, Pip.", "@end")),
        ("End",),
        ("@asking",), SK.say("Pip", "Any luck? Remember: the animals only talk to another animal. Inkwell's in the "
                                    "courtyard, usually asleep on something important.", ("I'm on it.", "@end")),
        ("End",),
        ("@plain",), SK.say("Pip", "Still mostly invisible. The Magister says it suits me. I think that was rude.",
                            ("Goodbye, Pip.", "@end")),
        ("@end",), ("End",)], MAKER)


def spectacles_quest():
    quest("Pip's Spectacles", "Pip", "SpectaclesQuest", {
        0: "Pip, in the Wizards' Court's great hall, is squinting at everyone through somebody else's spectacles.",
        1: "Pip's good spectacles went missing the afternoon a cat had his body. Ask Inkwell, the Court's cat, what she "
           "did with them. She won't talk to people: ask her as an animal.",
        2: "Inkwell remembers better with a fish inside her. Feed her one, then ask her again as an animal.",
        3: "Inkwell has had her fish. Ask her again, as an animal.",
        4: "Inkwell dropped Pip's spectacles in the courtyard, and Biscuit, the dog outside the Court's gate, ran off "
           "with them. Ask Biscuit, as an animal.",
        5: "Biscuit gave the 'shiny stick' to his friend Henrietta, a hen by the pond outside the Court's gate. Ask "
           "her, as an animal.",
        6: "Henrietta has been sitting on Pip's spectacles in her nest by the pond, hoping they'd hatch. Have a "
           "rummage in the nest.",
        7: "Take Pip's spectacles back to him in the Wizards' Court's great hall."}, 8,
        markers={0: "Pip_The_Apprentice", 1: "Court_Cat", 2: "Court_Cat", 3: "Court_Cat", 4: "Court_Dog",
                 5: "Court_Hen", 6: "Court_Hen_Nest", 7: "Pip_The_Apprentice"},
        kind="Side", requires="The Invisible Apprentice")
    section(p("data", "Quests.ini"), "Pip's Spectacles",
               [("Reward.Items", "Gold_Coin(s) 40"), ("Reward.Shards", "15"), ("Reward.XP", "Channeling 2"),
                ("Reward.Standing", "Court 5")])
    q = "$Attr.SpectaclesQuest"
    SK.write_script("Talk to Court_Cat", [                 # (as yourself, a cat; as an animal, Inkwell)
        (">Conditional", "$Player.Form=-", "@animal"),
        ("Play.Sound", "Meow"),
        ("Display.Message", "Cyan", "Inkwell looks at you, slowly blinks, and goes back to sleep.", "-"),
        ("End",),
        ("@animal",), (">Conditional", q + "=1", "@a2"),
        SK.say("Cat", "Spectacles? Round ones, gold, smelled of Pip? I might know. I might not. My memory's much "
                      "better with a fish inside it.", ("A fish?", "@fish")),
        ("@fish",), ("Update.Attribute", "SpectaclesQuest", "=2"),
        SK.say("Cat", "A fish. From a person, mind: you've no hands at the moment. I'll wait.", ("...", "@end")),
        ("End",),
        ("@a2",), (">Conditional", q + "=2", "@a3"),
        SK.say("Cat", "Fish first. I don't make the rules. I do, actually, but these are very good rules.",
               ("...", "@end")),
        ("End",),
        ("@a3",), (">Conditional", q + "=3", "@chat"),
        ("Update.Attribute", "SpectaclesQuest", "=4"),
        SK.say("Cat", "That was a lovely fish. Right. Last Tuesday I woke up as Pip, and those spectacles made "
                      "everything go wobbly, so I took them off and dropped them in the courtyard. Then Biscuit ran "
                      "off with them. He's the dog outside the gate. Everything's a stick to a dog.",
               ("Thank you, Inkwell.", "@end")),
        ("End",),
        ("@chat",), SK.say("Cat", "Being Pip was dreadful. Nobody stroked me once, and I had to read.",
                           ("...", "@end")),
        ("@end",), ("End",)], MAKER)
    fish = ("Raw_Herring", "Raw_Trout", "Raw_Salmon", "Cooked_Herring", "Cooked_Trout", "Cooked_Salmon")
    rows = [(">Distance.From.Clicked.Entity", "40", "@far")]
    for i, f in enumerate(fish):
        rows += [(">Got.Item", f, "1", "@f%d" % (i + 1)),
                 ("Take.Item", f, "1"),
                 ("Display.Message", "Cyan", "Inkwell eats the %s in neat little bites, then washes her whiskers."
                  % f.lower().replace("_", " "), "EatFood"),
                 ("Goto.Line", "@fed"),
                 ("@f%d" % (i + 1),)]
    for f in ("Raw_Poultry", "Cooked_Poultry"):
        rows += [(">Got.Item", f, "1", "@n" + f),
                 ("Take.Item", f, "1"),
                 ("Display.Message", "Cyan", "Inkwell eats the %s, and looks at you as if to say: that was not a fish."
                  % f.lower().replace("_", " "), "EatFood"),
                 ("End",),
                 ("@n" + f,)]
    rows += [("Display.Message", "DarkRed", "You have nothing a cat would eat.", "Denied"),
             ("End",),
             ("@fed",), (">Conditional", q + "=2", "@end"),
             ("Update.Attribute", "SpectaclesQuest", "=3"),
             ("Display.Message", "Yellow", "Inkwell looks at you as if she might, after all, remember something. If "
                                           "only she could tell you.", "-"),
             ("@end",), ("End",)] + FAR
    SK.write_script("Feed Court_Cat", rows, MAKER)
    SK.write_script("Talk to Court_Dog", [
        (">Conditional", "$Player.Form=-", "@animal"),
        SK.say("Dog", "Woof! Woof!\\(The dog wags its tail hopefully.)", ("Good dog.", "@end")),
        ("End",),
        ("@animal",), (">Conditional", q + "=4", "@a5"),
        ("Update.Attribute", "SpectaclesQuest", "=5"),
        SK.say("Dog", "The shiny stick! I found the shiny stick! Best stick ever. I gave it to Henrietta, by the pond. "
                      "She's my friend. She didn't say thank you, but she sat on it, so I think she liked it.",
               ("Good dog.", "@end")),
        ("End",),
        ("@a5",), (">Conditional", q + "=5", "@chat"),
        SK.say("Dog", "Henrietta! By the pond! She sits on everything! Are you going to throw something? Throw "
                      "something!", ("Good dog.", "@end")),
        ("End",),
        ("@chat",), SK.say("Dog", "Friend? FRIEND! You smell like a cat. That's fine. I'm fine with it. Ball?",
                           ("Good dog.", "@end")),
        ("@end",), ("End",)], MAKER)
    SK.write_script("Talk to Court_Hen", [
        (">Conditional", "$Player.Form=-", "@animal"),
        ("Play.Sound", "Cluck"),
        ("Display.Message", "Cyan", "Bok?", "-"),
        ("End",),
        ("@animal",), (">Conditional", q + "=5", "@a6"),
        ("Update.Attribute", "SpectaclesQuest", "=6"),
        SK.say("Chicken", "The shiny things? Mine. They're warm. I've sat on them for a week and they haven't hatched "
                          "yet, but I have hopes.\\...Oh, have them. They're not hatching, are they. My nest, by the "
                          "pond. The one that glints.", ("Thank you, Henrietta.", "@end")),
        ("End",),
        ("@a6",), (">Conditional", q + "=6", "@chat"),
        SK.say("Chicken", "In the nest. Go on, before I change my mind.", ("...", "@end")),
        ("End",),
        ("@chat",), SK.say("Chicken", "Bok. The dog brings me presents. A stick, a boot, half a rat. He means well.",
                           ("...", "@end")),
        ("@end",), ("End",)], MAKER)
    SK.write_script("Rummage Court_Hen_Nest", [
        (">Distance.From.Clicked.Entity", "48", "@far"),
        (">Conditional", q + "=6", "@s7"),
        ("@give",),
        ("Update.Attribute", "SpectaclesQuest", "=7"),
        ("Play.Sound", "Pickup"),
        ("Give.Item", "Pips_Spectacles", "1"),
        ("Display.Message", "Yellow", "Under the straw, still warm: a pair of round gold spectacles. Pip's!", "-"),
        ("End",),
        ("@s7",), (">Conditional", q + "=7", "@straw"),
        (">Got.Item", "Pips_Spectacles", "1", "@give"),
        ("@straw",), ("Display.Message", "Cyan", "Straw, feathers and one warm egg. The hen watches you closely.", "-"),
        ("End",)] + FAR, MAKER)


def lady():
    quest("Lady Pettigrew's Hat", "Woman", "HatQuest", {
        0: "A lady on Goose Green, east of Northport, is shouting at some geese.",
        1: "Get Lady Pettigrew's hat back from the geese's nest on Goose Green. They are not reasonable geese: go "
           "unseen, or go as a goose."}, 2,
        markers={0: "Goose_Green", 1: "Goose_Green"}, kind="Side", requires="The Invisible Apprentice")
    section(p("data", "Quests.ini"), "Lady Pettigrew's Hat",
               [("Reward.Items", "Gold_Coin(s) 60"), ("Reward.Shards", "12"), ("Reward.XP", "Defence 1 Channeling 1"),
                ("Reward.Standing", "Northport 10")])
    SK.write_script("Talk to Lady_Pettigrew", [
        ("Get.Value", "ATTRIBUTE", "HatQuest", "Variable.1$"),
        (">Conditional", "$Variable.1=0", "@s1"),
        (">Quest.Can.Start", "HatQuest", "@chat"),
        SK.say("Woman", "Those GEESE. I lay my hat down for one moment to admire the view, and they take it to their "
                        "nest like it's an egg. I've tried reasoning with them. I've tried bribery. Gerald, my own "
                        "goose, won't go near them; he's a coward.", ("I'll get your hat.", "@start"),
               ("Have you tried shouting?", "@shout")),
        ("@shout",), SK.say("Woman", "For two hours. They shouted back.", ("I'll get your hat.", "@start")),
        ("@start",), ("Update.Attribute", "HatQuest", "=1"),
        ("Display.Message", "Yellow", "Quest started: Lady Pettigrew's Hat.", "Quest"),
        ("Goto.Line", "@hat"),
        ("@s1",), (">Conditional", "$Variable.1=1", "@chat"),
        (">Got.Item", "Fancy_Hat", "1", "@hat"),
        ("Take.Item", "Fancy_Hat", "1"),
        ("Update.Attribute", "HatQuest", "=2"),
        SK.say("Woman", "My HAT! A little pecked, but it was a little pecked before. How ever did you get past them?\\"
                        "Never mind. I don't want to know. Gerald, apologise to the hero.",
               ("You're welcome.", "@done")),
        ("@done",),
        ("Play.Sound", "Honk"),
        ("Display.Message", "Cyan", "Gerald the goose looks at you, and does not apologise.", "-"),
        ("Display.Message", "Yellow", "Quest complete: Lady Pettigrew's Hat!", "Quest"),
        ("End",),
        ("@hat",),                                            # (the hat on the nest: each player's own, put back)
        ("Remove.Entity", at(NEST, -4), "Fancy_Hat"),
        ("Add.Entity", at(NEST, -4), "Fancy_Hat", "MapItem", "1"),
        ("End",),
        ("@chat",), SK.say("Woman", "Gerald and I are going home. Gerald? GERALD.", ("Goodbye.", "@end")),
        ("@end",), ("End",)], MAKER)


def granny():
    quest("Granny Bramble's Practice Hex", "Old_Woman", "HexQuest", {
        0: "An old woman on Thornwick's green is looking for someone to practise a hex on.",
        1: "Granny Bramble has hexed you weak as a kitten. Clear the rats round Thornwick's green anyway ($HexRats of "
           "4): your sword arm's no use. A spell, a potion, or someone else's body."}, 2,
        markers={0: "Granny_Bramble", 1: "Granny_Bramble"}, kind="Side", requires="The Invisible Apprentice")
    section(p("data", "Quests.ini"), "Granny Bramble's Practice Hex",
               [("Reward.Items", "Antidote 2"), ("Reward.Shards", "15"), ("Reward.XP", "Channeling 3"),
                ("Reward.Standing", "Thornwick 10")])
    rats = [("Add.Entity", at(xy), "Rat", "NPC", "Attitude=Bad Id=Hex_Rat Name=Market_Rat") for xy in RATS]
    SK.write_script("Talk to Granny_Bramble", [
        ("Get.Value", "ATTRIBUTE", "HexQuest", "Variable.1$"),
        (">Conditional", "$Variable.1=0", "@s1"),
        (">Quest.Can.Start", "HexQuest", "@chat"),
        SK.say("Old_Woman", "You've a strong arm, dearie. Lovely. Hold still: I'm practising a hex, and I need "
                            "someone with an arm worth hexing.", ("What does it do?", "@what"), ("No thank you.", "@end")),
        ("@what",), SK.say("Old_Woman", "Takes the strength right out of you. Only for ten minutes! Probably. And while "
                                        "you're hexed, the market's rats want clearing. Fair's fair.",
                           ("Oh, go on then.", "@hex")),
        ("@hex",),
        ("Update.Attribute", "HexQuest", "=1"),
        ("Update.Attribute", "HexRats", "=0"),
        ("Play.Sound", "Fizzle"),
        ("Boost.Skill", "Strength", "-24", "600"),
        ("Display.Message", "DarkRed", "Granny Bramble waggles her fingers at you. Your arms go like wet string: your "
                                       "Strength drains to nothing!", "Denied"),
        ("Display.Message", "Yellow", "Quest started: Granny Bramble's Practice Hex.", "Quest"),
        ("Goto.Line", "@rats"),
        ("@s1",), (">Conditional", "$Variable.1=1", "@chat"),
        (">Conditional", "$Attr.HexRats>=4", "@more"),
        ("Update.Attribute", "HexQuest", "=2"),
        ("Boost.Skill", "Strength", "0", "1"),
        SK.say("Old_Woman", "All four, and you couldn't lift a teaspoon! Clever. Here, I'll take the hex off. "
                            "It was ten minutes, wasn't it? Close enough.", ("Thank you. I think.", "@done")),
        ("@done",),
        ("Display.Message", "Yellow", "Quest complete: Granny Bramble's Practice Hex!", "Quest"),
        ("End",),
        ("@more",), SK.say("Old_Woman", "Four rats, dearie, and you've seen to $Attr.HexRats. Ran off, did they? Here "
                                        "they come again.", ("I'm on it.", "@rats")),
        ("@rats",)] + [("Remove.Entity", at(xy), "Rat") for xy in RATS] + rats + [
        ("End",),
        ("@chat",), SK.say("Old_Woman", "Mind how you go, dearie. Mind the rats.", ("Goodbye.", "@end")),
        ("@end",), ("End",)], MAKER)
    SK.write_script("Kill Hex_Rat", [
        ("Get.Value", "ATTRIBUTE", "HexQuest", "Variable.1$"),
        (">Conditional", "$Variable.1=1", "@end"),
        ("Update.Attribute", "HexRats", "+1"),
        ("Display.Message", "Yellow", "A market rat seen to: $Attr.HexRats of 4.", "-"),
        ("@end",), ("End",)], MAKER)


def tower():
    SK.write_script("Squeeze Through Berts_Cat_Flap", [
        (">Distance.From.Clicked.Entity", "48", "@far"),
        (">Conditional", "$Player.Form=Cat or $Player.Form=Strawberry_Cat", "@big"),
        (">Conditional", "$Attr.BertsTin=0", "@empty"),
        ("Update.Attribute", "BertsTin", "=1"),
        ("Play.Sound", "Pickup"),
        ("Display.Message", "Yellow", "You squeeze through the flap into Bert's secret pantry, and there it is: the "
                                      "biscuit tin. Inside, 25 Shards and a pie with BERT'S on it in icing. You take "
                                      "both. You are a cat. Cats do that.", "-"),
        ("Give.Item", "Shard", "25"),
        ("Give.Item", "Berry_Pie", "1"),
        ("End",),
        ("@empty",), ("Display.Message", "Cyan", "The biscuit tin is empty. Somebody ate the pie.", "-"),
        ("End",),
        ("@big",), ("Display.Message", "DarkRed", "The flap is far too small for you. Something small and furry might "
                                                  "fit.", "Denied"),
        ("End",)] + FAR, MAKER)
    SK.write_script("Press Berts_Button", [
        (">Distance.From.Clicked.Entity", "48", "@far"),
        ("Play.Sound", "Click"),
        ("Display.Message", "Cyan", "Click.", "-"),
        ("Wait", "1"),
        (">Random", "25", "@water"),
        ("Turn.Into", "Chicken", "20", "With a pop, you are a chicken. From somewhere upstairs Bert shouts: 'Did "
                                       "somebody press the button?'"),
        ("End",),
        ("@water",), (">Random", "33", "@confetti"),
        ("Play.Sound", "Splosh"),
        ("Display.Message", "DarkRed", "A bucket of icy water falls on your head from nowhere at all.", "-"),
        ("Boost.Skill", "Defence", "-2", "30"),
        ("End",),
        ("@confetti",), (">Random", "50", "@goose"),
        ("Play.Sound", "Quest"),
        ("Display.Message", "Yellow", "Confetti! A voice booms: 'CONGRATULATIONS: you are the one thousandth person to "
                                      "press the button!' A Shard drops into your hand.", "-"),
        ("Give.Item", "Shard", "1"),
        ("End",),
        ("@goose",),
        ("Play.Sound", "Honk"),
        ("Display.Message", "DarkRed", "A goose appears. It looks at you. You look at it. It honks.", "-"),
        ("Add.Entity", "$Player.X,$Player.Y", "Goose", "NPC", "Attitude=Bad"),
        ("End",)] + FAR, MAKER)


def main():
    art()
    sounds()
    data()
    places()
    pip()
    spectacles_quest()
    lady()
    granny()
    tower()
    print("Tricks: done")


if __name__ == "__main__":
    main()
