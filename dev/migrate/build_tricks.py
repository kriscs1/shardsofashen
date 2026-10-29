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
  * Secrets in Bert's tower: a cat flap to his secret biscuit tin (only a cat fits), and a big red button.
  * Pictures (the potion, the scroll, Pip, the goose - the duck's frames, whitened - its nest, the hat, the button,
    the flap) and sounds (Vanish, Appear, Swap, Honk, Splosh).

Safe to run again.

  python -I "dev\\migrate\\build_tricks.py"
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import Ini, p                      # noqa: E402
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
MARKET, GRANNY = "8,16,0", (6, 18)
RATS = [(3, 14), (23, 14), (2, 5), (20, 5)]
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
           ("Entities", "Goose", whiten(K.load("Entities", "Duck")))]
    for f in "abc":
        for d in "28":
            out.append(("Walk", "Goose%s%s" % (d, f), whiten(K.load("Walk", "Duck%s%s" % (d, f)))))
    print("Pictures: %d written" % sum(1 for kind, name, img in out if K.save(kind, name, img)))


SOUNDS = {
    # (Vanish, Appear, Swap and Click: build_soundscape.py)
    # HONK
    "Honk": lambda: SND.mix((SND.shaped(SND.tone(330, SND.n(0.25), glide=-0.15, shape="square"), 0.01, 6), 0.45),
                            (SND.shaped(SND.noise(62, SND.n(0.25), 0.5, high=0.3), 0.01, 6), 0.15)),
    # a bucket of water, all at once
    "Splosh": lambda: SND.mix((SND.shaped(SND.noise(63, SND.n(0.7), 0.6, high=0.5), 0.005, 4), 0.7),),
}


def sounds():
    for name, fn in SOUNDS.items():
        blob = SND.wav_bytes(fn())
        path = p("sounds", name + ".wav")
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
            ("Cat_Flap", [("Type", "StaticObject"), ("Use.Words", "Squeeze Through,Examine"), ("Solid", "1"),
                          ("Examine.Info", "A little flap, low in the wall. It smells faintly of shortbread.")])):
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
    m = Map(map_name)
    added = [ln for ln in lines if ln not in m.ents]
    if added:
        m.ents += added
        m.save()
        print("%s: %d added" % (map_name, len(added)))


def places():
    place(COURT, [obj_line("NPC", "Pip", PIP[0], PIP[1], "Attitude=Good Stand=1 Id=Pip_The_Apprentice Name=Pip")])
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
def at(t, dy=-8):
    return "%d,%d" % ((t[0] - 1) * 32, (t[1] - 1) * 32 + dy)


FAR = [("@far",), ("Display.Message", "DarkRed", "You are too far away!", "Denied"), ("End",)]


def pip():
    SK.quest("The Invisible Apprentice", "Pip", "PipQuest", {
        0: "Someone in the Wizards' Court's great hall keeps saying hello. There's no one there.",
        1: "Bring Pip what he needs to be seen again: an egg, a feather and two cave mushrooms."}, 2,
        markers={0: "Pip_The_Apprentice", 1: "Pip_The_Apprentice"}, kind="Side", requires="Passage to the Mainland")
    SK.section(p("data", "Quests.ini"), "The Invisible Apprentice",
               [("Reward.Items", "Invisibility_Potion 2 Swap_Scroll 1"), ("Reward.Shards", "10"),
                ("Reward.XP", "Alchemy 2")])
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
        ("@chat",), SK.say("Pip", "Still mostly invisible. The Magister says it suits me. I think that was rude.",
                           ("Goodbye, Pip.", "@end")),
        ("@end",), ("End",)], MAKER)


def lady():
    SK.quest("Lady Pettigrew's Hat", "Woman", "HatQuest", {
        0: "A lady on Goose Green, east of Northport, is shouting at some geese.",
        1: "Get Lady Pettigrew's hat back from the geese's nest on Goose Green. They are not reasonable geese: go "
           "unseen, or go as a goose."}, 2,
        markers={0: "Goose_Green", 1: "Goose_Green"}, kind="Side", requires="The Invisible Apprentice")
    SK.section(p("data", "Quests.ini"), "Lady Pettigrew's Hat",
               [("Reward.Items", "Gold_Coin(s) 60"), ("Reward.Shards", "12"), ("Reward.XP", "Defence 1 Magic 1")])
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
    SK.quest("Granny Bramble's Practice Hex", "Old_Woman", "HexQuest", {
        0: "An old woman at Fenwick's market is looking for someone to practise a hex on.",
        1: "Granny Bramble has hexed you weak as a kitten. Clear the rats round Fenwick's market anyway ($HexRats of "
           "4): your sword arm's no use. A spell, a potion, or someone else's body."}, 2,
        markers={0: "Granny_Bramble", 1: "Granny_Bramble"}, kind="Side", requires="The Invisible Apprentice")
    SK.section(p("data", "Quests.ini"), "Granny Bramble's Practice Hex",
               [("Reward.Items", "Antidote 2"), ("Reward.Shards", "15"), ("Reward.XP", "Magic 3")])
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
    lady()
    granny()
    tower()
    print("Tricks: done")


if __name__ == "__main__":
    main()
