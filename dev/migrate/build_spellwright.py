"""The Spellwright: Magister Quill's second quest, and a spell of your own (dsengine/ownspell.py).

  * The quest (SpellwrightQuest 0-3, after The Shard Scholar): how does a Shard hold a spell's shape? Bring Quill the
    core of a risen Shard Remnant (Remnant_Core: every risen one leaves one), then absorb twenty more remnants and tell
    him how it felt. He teaches you to write a spell of your own.
  * The Spellwright's Lectern in the Court's great hall (21,5,0, on the back wall right of the throne): Write, and
    choose your spell's effect, power and reach; its Shards and rest are worked out (Shards.ini [Spellwright]).
  * Spells.ini [Own_Spell] (only defaults: ownspell.py works out the rest), its page Spellwrights_Page (what goes on
    the hotbar), Remnant_Core; their pictures.
  * Quill's script "Quill the Spellwright" (Talk to Court_Magister comes here: build_shards.py).

Safe to run again.

  python -I "dev\\migrate\\build_spellwright.py"
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import Ini, p                      # noqa: E402
import build_sprites as BS                     # noqa: E402
import sprite_kit as K                         # noqa: E402
import story_kit as SK                         # noqa: E402
from story_kit import Map, obj_line            # noqa: E402

MAKER = "build_spellwright.py"
WIZARD = "Wizard"
COURT, LECTERN = "21,5,0", (15, 5)
SPELLWRIGHT = [   # Shards.ini [Spellwright] (key, value, note)
    ("Bolt.Cost", "3", "A written spell's Shards a cast: its effect's .Cost, times its power to Power.Exponent,"),
    ("Burst.Cost", "3.5", "times Far for the far reach. Write: Shards to write it again over your old one."),
    ("Frost.Cost", "3.5", None), ("Ward.Cost", "3", None), ("Power.Exponent", "1.1", None), ("Far", "1.4", None),
    ("Write", "10", None),
]
OWN_DEFAULTS = [("Kind", "Scroll"), ("Scroll", "Spellwrights_Page"), ("Skill", "Channeling"), ("Effect", "Bolt"),
                ("Damage", "2-5"), ("Range", "192"), ("Level", "1"), ("Cost", "3"), ("Cooldown", "1.4"),
                ("Missile", "Ice_Bolt_Missile"), ("Impact", "Ice_Burst"), ("Sound", "SpellIce"), ("XP", "0.3")]


def core():
    """A Remnant's core: a dark violet orb, splinters bound round it, a cold light at its heart."""
    img = K.new()
    cx, cy = 16, 17
    for r in range(8, 0, -1):
        c = K.mix((230, 220, 255), (70, 30, 120), r / 8.0)
        for y in range(cy - r, cy + r + 1):
            for x in range(cx - r, cx + r + 1):
                if (x - cx) ** 2 + (y - cy) ** 2 <= r * r:
                    K.put(img, x, y, c)
    for i in range(5):                                     # (splinters round it)
        a = i * 2 * math.pi / 5 + 0.3
        for k in range(8, 12):
            K.put(img, int(round(cx + math.cos(a) * k)), int(round(cy + math.sin(a) * k)), (150, 120, 245))
    K.put(img, cx - 2, cy - 3, (255, 255, 255))
    return K.outline_img(img, (30, 18, 46))


def art():
    print(("wrote " if K.save("Entities", "Remnant_Core", core()) else "unchanged ") + "Remnant_Core")
    page = BS.scroll((120, 60, 200), ((210, 190, 255), (120, 60, 200)))     # (a scroll sealed in Shard-violet)
    print(("wrote " if K.save("Entities", "Spellwrights_Page", page) else "unchanged ") + "Spellwrights_Page")
    SK.copy_sprite("Entities", "Grimoire_Lectern", "Spellwright_Lectern")


def data():
    ents = Ini(p("data", "Entities.ini"))
    for name, keys in (
            ("Spellwright_Lectern", [("Type", "StaticObject"), ("Use.Words", "Write,Examine"), ("Solid", "1"),
                                     ("Light", "30"), ("Examine.Info", "The Spellwright's Lectern: a stone lectern, a "
                                                                       "blank page on it and a pot of Shard-ink.")]),
            ("Spellwrights_Page", [("Type", "MapItem"), ("Use.Words", "Learn"), ("Spell", "Own_Spell"),
                                   ("Droppable", "0"), ("Value", "0"),
                                   ("Examine.Info", "A page in your own hand, written at the Spellwright's Lectern: "
                                                    "your own spell.")]),
            ("Remnant_Core", [("Type", "MapItem"), ("Stackable", "99"), ("Value", "15"), ("Light", "20"),
                              ("Examine.Info", "A Shard Remnant's core: splinters bound round a cold violet light, "
                                               "all that's left when one is killed.")])):
        for k, v in keys:
            ents.set(name, k, v)
    drops = ents.get("Living_Remnant", "Drops") or ""
    if "Remnant_Core" not in drops:
        ents.set("Living_Remnant", "Drops", (drops + " Remnant_Core,1-1,100").strip())
    ents.save(p("data", "Entities.ini"))
    spells = Ini(p("data", "Spells.ini"))
    if spells.section("Own_Spell") is None:
        spells.replace_section("Own_Spell", OWN_DEFAULTS)
        spells.section("Own_Spell")[1].insert(0, (None, "; (your own spell, written at the Spellwright's Lectern: "
                                                        "dsengine/ownspell.py works out its values; these are only "
                                                        "what's read before)"))
    spells.save(p("data", "Spells.ini"))
    sh = Ini(p("data", "Shards.ini"))
    if sh.section("Spellwright") is None:
        sh.section("Spellwright", create=True)[1].extend((None, "; " + n) for k, v, n in SPELLWRIGHT if n)
    for k, v, n in SPELLWRIGHT:
        sh.set("Spellwright", k, v, overwrite=False)
    sh.save(p("data", "Shards.ini"))


def place():
    m = Map(COURT)
    if any("\tSpellwright_Lectern\t" in ln for ln in m.ents):
        return
    m.ents.append(obj_line("StaticObject", "Spellwright_Lectern", LECTERN[0], LECTERN[1], "Id=Quill_Lectern"))
    m.save()
    print("The lectern, on %s at %d,%d" % (COURT, LECTERN[0], LECTERN[1]))


def quest():
    SK.quest("The Spellwright", WIZARD, "SpellwrightQuest", {
        0: "Magister Quill wonders how a Shard holds the shape of a spell.",
        1: "Bring Magister Quill the core of a Shard Remnant. They rise, now and then, from a beast's magic when it "
           "dies; killed, one leaves its core.",
        2: "Absorb twenty more Shard Remnants (in your pack), then tell Magister Quill how it felt."}, 3,
        markers={0: "Court_Magister", 1: "Court_Magister", 2: "Court_Magister"}, kind="Side",
        requires="The Shard Scholar")
    SK.section(p("data", "Quests.ini"), "The Spellwright", [("Reward.Shards", "20"), ("Reward.XP", "Magic 4")])
    rows = [
        ("Get.Value", "ATTRIBUTE", "SpellwrightQuest", "Variable.1$"),
        (">Conditional", "$Variable.1=0", "@s1"),
        (">Quest.Can.Start", "SpellwrightQuest", "@busy"),
        SK.say(WIZARD, "Here's what keeps me up at night. A scroll is ink and vellum: how does a Shard know to become a "
                       "bolt of fire because some words told it to? The Shards remember shapes, I think. Bring me "
                       "something that remembers its own: the core of a Shard Remnant, one that rose.",
               ("I'll bring you one.", "@start"), ("Not now.", "@end")),
        ("@start",), ("Update.Attribute", "SpellwrightQuest", "=1"),
        ("Display.Message", "Yellow", "Quest started: The Spellwright.", "Quest"),
        ("End",),
        ("@s1",), (">Conditional", "$Variable.1=1", "@s2"),
        (">Got.Item", "Remnant_Core", "1", "@nocore"),
        ("Take.Item", "Remnant_Core", "1"),
        ("Update.Attribute", "RemnantsAtStart", "=$Attr.RemnantsAbsorbed"),
        ("Update.Attribute", "SpellwrightQuest", "=2"),
        ("Play.Sound", "SpellCast"),
        SK.say(WIZARD, "Look at it: it's still holding the shape of the beast it was. Shape is the whole secret.\\Now "
                       "you. Absorb twenty more remnants, and pay attention as you do: what the magic feels like as it "
                       "comes into you. Then tell me.", ("I will.", "@end")),
        ("End",),
        ("@nocore",), SK.say(WIZARD, "A Remnant's core: they rise from a beast's magic, now and then, when it dies. "
                                     "Kill one and it leaves its core behind.", ("I'll find one.", "@end")),
        ("End",),
        ("@s2",), (">Conditional", "$Variable.1=2", "@done"),
        (">Conditional", "$Attr.RemnantsAbsorbed-$Attr.RemnantsAtStart>=20", "@notyet"),   # (no brackets: a name may end in one)
        ("Update.Attribute", "SpellwrightQuest", "=3"),
        ("Play.Sound", "Quest"),
        SK.say(WIZARD, "Cold, then warm, then a sort of... leaning? Yes! That's the shape, wanting to be something.\\"
                       "You've felt it, so you can write it. The lectern by the throne: a page and Shard-ink. Choose "
                       "what your spell does, how hard, how far, and the Shards will remember. Yours, no one else's.",
               ("Thank you, Magister.", "@taught")),
        ("@taught",),
        ("Display.Message", "Yellow", "Quest complete: The Spellwright! Write a spell of your own at the Spellwright's "
                                      "Lectern.", "Quest"),
        ("End",),
        ("@notyet",), SK.say(WIZARD, "Twenty remnants, absorbed, and mind how they feel. You've absorbed "
                                     "$Attr.RemnantsAbsorbed in all.", ("I'll keep at it.", "@end")),
        ("End",),
        ("@done",), SK.say(WIZARD, "The lectern's there whenever you want to write your spell again. Change it as "
                                   "you grow: a spell's a living thing.", ("Thank you.", "@end")),
        ("End",),
        ("@busy",), SK.say(WIZARD, "Ask me again when you've seen more of the world.", ("Goodbye.", "@end")),
        ("@end",), ("End",),
    ]
    SK.write_script("Quill the Spellwright", rows, MAKER)


def main():
    art()
    data()
    place()
    quest()
    print("The Spellwright: done")


if __name__ == "__main__":
    main()
