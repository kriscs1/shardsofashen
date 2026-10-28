"""The Shardgate (chapter 15 of the main quest: ShardgateQuest 0-5, between The Sword of Valour and The Dragon of
Galaith), and the Shardrealm beyond it.

The story: with the Sword of Valour in hand you raise the Staff of Ashen at the barrier, and it holds: something
beyond the world feeds it (the barrier's script, estforlan/story.py). Bert knows what: the dragon anchored it in the
Shardrealm, where all broken magic goes. He gives you a Shardgate's plans; you build it in the old ring of standing
stones on the hill north of the Wizards' Court (21,4,0) from 4 silver bars, 2 sapphires, a Remnant's core and
Shards.ini Shardgate Shards. Through it, the Shardrealm (21,4,-10): its Warden guards the anchor; with the Warden down,
the staff shatters it. Bert: now the barrier will break. The gate stays, and you can go back: Shard Remnants roam the
realm (map NPCs with Level=), and its Shard clusters give Shards every Realm.Cluster.Hours hours.

  * the pictures: the ring of stones, the gate (its portal swirling: Shardgate1-4), the realm's ground and void, its
    crystals and clusters, the anchor (whole and shattered), the Warden (its walking frames); the plans;
  * the sounds: Portal, Gate_Built, Anchor_Shatter;
  * the ring and its place Id (Shardgate_Site) on 21,4,0; the realm's map; the scripts; Bert's (Talk to Bert comes
    here: build_heir_mainland.py); the quest, and the chapters after it moved on one; the world map's label, shown
    once you've built your gate (WorldMap.ini [if ...]).
The gate and the anchor are each player's own (Add.Entity: the maps' entry scripts put them back).

Safe to run again (the realm's map is made once; edit it in the editor after).

  python -I "dev\\migrate\\build_shardgate.py"
"""
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import Ini, p                      # noqa: E402
import build_remnants as BR                    # noqa: E402
import build_sounds as SND                     # noqa: E402
import sprite_kit as K                         # noqa: E402
import story_kit as SK                         # noqa: E402
from story_kit import Map, obj_line            # noqa: E402

MAKER = "build_shardgate.py"
HILL, RING = "21,4,0", (19, 7)                   # (the ring: 2 x 2 tiles from here; its site, the tile below it)
SITE = (20, 9)
REALM = "21,4,-10"
GATE_IN, ANCHOR = (3, 10), (21, 10)              # (the realm's way back, and the anchor: 2 x 2 tiles each)
REALM_GATE, ANCHOR_SITE = (5, 11), (20, 12)
SHARDS = [("Shardgate", "30", "Shardgate: the Shards that bind a Shardgate as you build it."),
          ("Realm.Cluster", "5", "Realm.Cluster: a Shard cluster in the Shardrealm's Shards, once every "
                                 "Realm.Cluster.Hours (real) hours."),
          ("Realm.Cluster.Hours", "8", None)]
VOID, GROUND = "Realm_Void001", ("Realm_Ground001", "Realm_Ground002", "Realm_Ground003")
VIOLET, PALE, DEEP = (150, 90, 220), (215, 200, 255), (40, 20, 70)


# ================================================================== pictures
def stones(img, ox, oy, lit):
    """Four old standing stones in a ring (back two taller), runes on them faint or lit."""
    for sx, top, h, w in ((10, 10, 34, 9), (45, 10, 34, 9), (4, 30, 26, 8), (52, 30, 26, 8)):
        for y in range(top, top + h):
            half = w // 2 if y > top + 2 else w // 2 - 1
            for x in range(sx - half, sx + half + 1):
                shade = (128, 124, 132) if x < sx else (96, 92, 104) if x > sx + 1 else (112, 108, 118)
                if (x * 7 + y * 5) % 17 == 0:
                    shade = K.mul(shade, 0.85)
                K.put(img, ox + x, oy + y, shade)
        for k in range(3):                                       # (a rune down each)
            K.put(img, ox + sx, oy + top + 6 + k * 5, PALE if lit else (150, 140, 170))
            K.put(img, ox + sx + 1, oy + top + 7 + k * 5, VIOLET if lit else (120, 112, 140))


def ring():
    img = K.new(64, 64)
    for x in range(6, 58):                                       # (trodden earth in the ring)
        for y in range(46, 60):
            if ((x - 32) / 26.0) ** 2 + ((y - 53) / 7.0) ** 2 <= 1 and (x + y) % 3:
                K.put(img, x, y, (96, 84, 64))
    stones(img, 0, 0, False)
    return K.outline_img(img, (34, 30, 38))


def gate(frame):
    """The stones bound by a lintel, a portal swirling between: frame turns the swirl."""
    img = K.new(64, 64)
    for x in range(6, 58):
        for y in range(46, 60):
            if ((x - 32) / 26.0) ** 2 + ((y - 53) / 7.0) ** 2 <= 1:
                K.put(img, x, y, K.mix((96, 84, 64), VIOLET, 0.35))
    cx, cy, rx, ry = 27, 30, 13, 18                              # (the portal, between the back stones)
    for y in range(cy - ry, cy + ry + 1):
        for x in range(cx - rx, cx + rx + 1):
            d = ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2
            if d <= 1:
                a = math.atan2(y - cy, x - cx) + frame * math.pi / 6 + d * 5        # (a twelfth of a turn a frame)
                t = 0.5 + 0.5 * math.sin(a * 3)
                K.put(img, x, y, K.mix(K.mix(DEEP, VIOLET, d), PALE, t * (1 - d) * 0.9))
    stones(img, 0, 0, True)
    for x in range(4, 58):                                       # (the lintel over the back stones)
        for y in range(6, 11):
            K.put(img, x, y, (118, 114, 124) if y < 8 else (90, 86, 98))
    for k in range(5):
        K.put(img, 14 + k * 8, 8, PALE)
    return K.outline_img(img, (30, 22, 44))


def ground(n):
    rng = random.Random(500 + n)
    img = K.new()
    for y in range(32):
        for x in range(32):
            img[y][x] = K.jitter(K.mix((46, 34, 72), (70, 56, 104), rng.random() * 0.5), rng, 6)
    for _ in range(3 + n):                                       # (glassy veins)
        x, y = rng.randrange(32), rng.randrange(32)
        for i in range(rng.randrange(5, 12)):
            K.put(img, x + i, y + (i * n) // 4, K.mix((90, 70, 140), VIOLET, 0.5), wrap=True)
    for _ in range(2):
        K.put(img, rng.randrange(32), rng.randrange(32), PALE)
    return img


def void():
    rng = random.Random(77)
    img = K.new()
    for y in range(32):
        for x in range(32):
            img[y][x] = K.mix((8, 4, 18), (24, 10, 44), rng.random() * 0.6)
    for _ in range(4):
        K.put(img, rng.randrange(32), rng.randrange(32), (200, 190, 255))
    return img


def crystal(tall):
    img = K.new()
    for (bx, h, lean) in ((14, 22 if tall else 14, -1), (19, 16 if tall else 10, 1), (10, 10, -1)):
        for i in range(h):
            x, y = bx + (lean * i) // 4, 29 - i
            w = 1 if i > h - 4 else 2
            for dx in range(-w + 1, w):
                K.put(img, x + dx, y, PALE if dx == 0 else VIOLET)
            K.put(img, x - w, y, (90, 50, 150))
            K.put(img, x + w, y, (70, 40, 120))
    return K.outline_img(img, (24, 14, 40))


def anchor(broken):
    """The barrier's anchor: a great dark crystal, violet light chained round it; broken, a jagged stump."""
    img = K.new(64, 64)
    top = 34 if broken else 2
    for y in range(top, 60):
        half = int(4 + (y - top) * (0.35 if not broken else 0.6))
        for x in range(32 - half, 32 + half + 1):
            jag = broken and y < top + 6 and (x * 3) % 5 < 2
            if not jag:
                K.put(img, x, y, K.mix((30, 18, 50), (80, 50, 130), (x - 32 + half) / (2.0 * half + 1)))
    if not broken:
        for k in range(4):                                        # (chains of light round it)
            y = 14 + k * 11
            for x in range(14, 51):
                K.put(img, x, y + int(2 * math.sin(x / 4.0 + k)), PALE if x % 3 else VIOLET)
    else:
        for i in range(10):                                       # (shards strewn at its foot)
            K.put(img, 12 + i * 4, 58 - (i % 3), VIOLET)
    return K.outline_img(img, (16, 8, 28))


def warden(frame, flip=False):
    """The Warden: a remnant grown huge on the realm's magic, gold where they are violet, a crown of splinters."""
    img = K.hue_shift(BR.living_remnant(frame, False), target_hue=0.12, sat_mul=1.1, val_mul=1.05)
    for k in (-4, 0, 4):
        for i in range(4):
            K.put(img, 16 + k, 3 + i + (1 if k else 0) - (1 if frame == 1 else 0), (255, 230, 140))
    return K.flip_h(img) if flip else img


def plans():
    img = K.new()
    for y in range(6, 27):
        for x in range(5, 27):
            K.put(img, x, y, (226, 214, 180) if (x + y) % 9 else (210, 196, 160))
    for k in range(4):                                            # (the ring drawn on it, and the arch)
        K.put(img, 9 + k * 4, 20, (90, 60, 140))
        K.put(img, 9 + k * 4, 19, (90, 60, 140))
    for x in range(9, 23):
        K.put(img, x, 11, (90, 60, 140))
    return K.outline_img(img, (80, 66, 44))


def art():
    out = [("Entities", "Shardgate_Ring", ring()), ("Entities", "Shardgate", gate(0)),
           ("Entities", "Realm_Crystal", crystal(True)), ("Entities", "Barrier_Anchor", anchor(False)),
           ("Entities", "Barrier_Anchor_Broken", anchor(True)), ("Entities", "Shard_Warden", warden(0)),
           ("Entities", "Shardgate_Plans", plans()), ("Tiles", VOID, void())]
    out += [("Entities", "Shardgate%d" % (f + 1), gate(f)) for f in range(4)]
    out += [("Tiles", name, ground(i)) for i, name in enumerate(GROUND)]
    for f, letter in enumerate("abc"):
        out += [("Walk", "Shard_Warden2" + letter, warden(f)), ("Walk", "Shard_Warden8" + letter, warden(f, True))]
    n = sum(1 for kind, name, img in out if K.save(kind, name, img))
    SK.copy_sprite("Entities", "Shard_Seam", "Shard_Cluster")
    print("Pictures: %d written" % n)


SOUNDS = {
    # a rising shimmer, and the air folding shut behind you
    "Portal": lambda: SND.mix((SND.arpeggio([523, 784, 1047, 1568, 2093, 3136], 0.05, 0.8, decay=3.0), 0.4),
                              (SND.shaped(SND.noise(51, SND.n(0.8), 0.4, high=0.4), 0.3, 2.5), 0.3),
                              (SND.shaped(SND.tone(110, SND.n(0.7), glide=0.6), 0.05, 4.0, delay=0.2), 0.4)),
    # stone grinding into place, then a chime as the gate wakes
    "Gate_Built": lambda: SND.mix((SND.shaped(SND.noise(52, SND.n(1.2), 0.15), 0.1, 2.5), 0.6),
                                  (SND.arpeggio([392, 523, 659, 784], 0.12, 1.2, decay=2.5), 0.4)),
    # a great crystal cracking, and shards ringing down
    "Anchor_Shatter": lambda: SND.mix((SND.shaped(SND.noise(53, SND.n(0.2), 0.95, high=0.8), 0.001, 20), 0.8),
                                      (SND.arpeggio([3136, 2637, 2349, 1976, 1568, 1319], 0.07, 0.9, decay=5),
                                       0.4),
                                      (SND.shaped(SND.tone(65, SND.n(1.0), glide=-0.4), 0.01, 3.0), 0.5)),
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
            ("Shardgate_Ring", [("Type", "StaticObject"), ("Use.Words", "Build,Examine"), ("Solid", "1"),
                                ("Examine.Info", "A ring of old standing stones, worn smooth, a faint rune on each.")]),
            ("Shardgate", [("Type", "StaticObject"), ("Use.Words", "Step Through,Examine"), ("Solid", "1"),
                           ("Light", "90"), ("Anim.Frames", "4"), ("Anim.Speed", "140"),
                           ("Examine.Info", "A Shardgate: the old stones bound with silver and sapphire, and between "
                                            "them a door of swirling violet light.")]),
            ("Shardgate_Plans", [("Type", "MapItem"), ("Use.Words", "Read,Examine"), ("Droppable", "0"),
                                 ("Value", "0"), ("Examine.Info", "Bert's plans for a Shardgate, in his spidery hand.")]),
            ("Realm_Crystal", [("Type", "StaticObject"), ("Use.Words", "Examine"), ("Solid", "1"), ("Light", "50"),
                               ("Examine.Info", "Crystal, grown out of nothing, humming.")]),
            ("Shard_Cluster", [("Type", "StaticObject"), ("Use.Words", "Mine,Examine"), ("Solid", "1"),
                               ("Light", "60"), ("Examine.Info", "A cluster of Shards, growing out of the realm's "
                                                                 "glassy ground.")]),
            ("Barrier_Anchor", [("Type", "StaticObject"), ("Use.Words", "Shatter,Examine"), ("Solid", "1"),
                                ("Light", "70"), ("Examine.Info", "The barrier's anchor: a great dark crystal, chains "
                                                                  "of violet light pulled taut round it, humming.")]),
            ("Barrier_Anchor_Broken", [("Type", "StaticObject"), ("Use.Words", "Examine"), ("Solid", "1"),
                                       ("Examine.Info", "What's left of the barrier's anchor: a jagged black stump.")]),
            ("Shard_Warden", [("Type", "NPC"), ("Attitude", "Bad"), ("Use.Words", "Attack,Examine"),
                              ("Examine.Info", "The Warden of the anchor: a remnant grown huge on the realm's "
                                               "magic, a crown of golden splinters."),
                              ("Hitpoints", "160"), ("Attack.Speed", "1"), ("Strength", "9"), ("Defence", "9"),
                              ("Aggro.Range", "200"), ("Weapon.Range", "0"), ("Movement.Speed", "2"),
                              ("Aggressive", "1"), ("Respawn", "900"), ("Chase.Radius", "10"), ("Walk.Speed", "0.6"),
                              ("Kill.Sound", "Undead"), ("Level", "16"), ("Freeze.Immune", "1"), ("Light", "50"),
                              ("Drops", "Remnant_Core,1-1,100 Shard_Remnant,8-12,100")])):
        for k, v in keys:
            ents.set(name, k, v)
    ents.save(p("data", "Entities.ini"))
    sh = Ini(p("data", "Shards.ini"))
    if sh.get("Shards", "Shardgate") is None:
        sh.section("Shards")[1].extend((None, "; " + n) for k, v, n in SHARDS if n)
    for k, v, n in SHARDS:
        sh.set("Shards", k, v, overwrite=False)
    sh.save(p("data", "Shards.ini"))
    SK.copy_tile(VOID, "Black001", Examine_Info="Nothing: a deep violet dark, stars far down in it.")
    for name in GROUND:
        SK.copy_tile(name, "Black001", Walkable_Data="1" * 49, Examine_Info="Glassy ground, faintly humming.")
    SK.minimap_colour(VOID, (14, 6, 28))
    for name in GROUND:
        SK.minimap_colour(name, (58, 44, 88))


# ================================================================== the maps
def ring_on_the_hill():
    m = Map(HILL)
    if any("\tShardgate_Ring\t" in ln for ln in m.ents):
        return
    m.ents.append(obj_line("StaticObject", "Shardgate_Ring", RING[0], RING[1], "Id=Old_Ring_Stones"))
    SK.place_id(m, "Shardgate_Site", SITE[0], SITE[1])
    m.save()
    print("The ring, on %s at %d,%d" % (HILL, RING[0], RING[1]))


def realm():
    if SK.map_exists(REALM):
        return
    rng = random.Random(21407)
    m = Map(REALM, new=True)
    land = set()
    for y in range(1, 22):
        for x in range(1, 26):
            edge = 1 + 0.12 * math.sin(x * 1.7 + y) + 0.08 * math.cos(y * 2.3)     # (ragged, not an ellipse)
            if ((x - 13) / 11.5) ** 2 + ((y - 11) / 8.6) ** 2 <= edge:
                land.add((x, y))
    for y in range(1, 22):
        for x in range(1, 26):
            m.put(x, y, rng.choice(GROUND) if (x, y) in land else VOID, {})
    m.ents = [obj_line("StaticObject", "Shardgate", GATE_IN[0], GATE_IN[1], "Id=Realm_Gate_Stones"),
              obj_line("NPC", "Shard_Warden", 18, 11, "Attitude=Bad Id=Anchor_Warden Name=Shard_Warden")]
    for x, y, lv in ((8, 6, 6), (11, 16, 8), (15, 6, 10), (16, 16, 12)):
        m.ents.append(obj_line("NPC", "Living_Remnant", x, y, "Attitude=Bad Level=%d Name=Shard_Remnant" % lv))
    for x, y in ((7, 9), (12, 4), (14, 17)):
        m.ents.append(obj_line("StaticObject", "Shard_Cluster", x, y))
    for x, y in ((4, 6), (9, 3), (19, 5), (23, 8), (22, 15), (6, 16), (17, 19), (3, 13)):
        if (x, y) in land:
            m.ents.append(obj_line("StaticObject", "Realm_Crystal", x, y))
    SK.place_id(m, "Realm_Gate", REALM_GATE[0], REALM_GATE[1])
    SK.place_id(m, "Barrier_Anchor_Site", ANCHOR_SITE[0], ANCHOR_SITE[1])
    m.save()
    print("Made maps\\%s.txt: the Shardrealm" % REALM)


# ================================================================== the scripts
def px(t, dy=0):
    return "%d,%d" % ((t[0] - 1) * 32, (t[1] - 1) * 32 + dy)


FAR = [("@far",), ("Display.Message", "DarkRed", "You are too far away!", "Denied"), ("End",)]


def scripts():
    SK.write_script(HILL, [                                       # (your own gate, once you've built it)
        ("Get.Value", "ATTRIBUTE", "ShardgateQuest", "Variable.1$"),
        (">Conditional", "$Variable.1>=3", "@end"),
        ("Add.Entity", px(RING, 1), "Shardgate", "StaticObject", "-"),
        ("@end",), ("End",)], MAKER)
    SK.write_script(REALM, [                                      # (the anchor: whole, until you've shattered it)
        ("Get.Value", "ATTRIBUTE", "ShardgateQuest", "Variable.1$"),
        (">Conditional", "$Variable.1<=3", "@broken"),
        ("Add.Entity", px(ANCHOR), "Barrier_Anchor", "StaticObject", "-"),
        ("End",),
        ("@broken",), ("Add.Entity", px(ANCHOR), "Barrier_Anchor_Broken", "StaticObject", "-"),
        ("End",)], MAKER)
    SK.write_script("Build Shardgate_Ring", [
        (">Distance.From.Clicked.Entity", "72", "@far"),
        ("Get.Value", "ATTRIBUTE", "ShardgateQuest", "Variable.1$"),
        (">Conditional", "$Variable.1=2", "@stones"),
        (">Got.Item", "Silver_Bar", "4", "@need"),
        (">Got.Item", "Sapphire", "2", "@need"),
        (">Got.Item", "Remnant_Core", "1", "@need"),
        (">Pay.Shards", "Shardgate", "Binding_the_Shardgate", "@end"),
        ("Take.Item", "Silver_Bar", "4"),
        ("Take.Item", "Sapphire", "2"),
        ("Take.Item", "Remnant_Core", "1"),
        ("Toggle.User.Input", "OFF"),
        ("Show.Skill", "Crafting"),
        ("Display.Message", "Cyan", "You bind the stones with silver, set the sapphires in their runes, and lay the "
                                    "Remnant's core at the ring's heart..", "-"),
        ("Play.Sound", "Gate_Built"),
        ("Wait", "3"),
        ("Add.Entity", px(RING, 1), "Shardgate", "StaticObject", "-"),
        ("Play.Sound", "Portal"),
        ("Update.Attribute", "ShardgateQuest", "=3"),
        ("Update.Skill", "Crafting", "+2"),
        ("Toggle.User.Input", "ON"),
        ("Display.Message", "Yellow", "..and the Shards drain out of you into the stones, and light opens between "
                                      "them: a Shardgate.", "-"),
        ("End",),
        ("@need",), ("Display.Message", "DarkRed", "A Shardgate needs 4 silver bars, 2 sapphires and a Remnant's "
                                                   "core, as Bert's plans say.", "Denied"),
        ("End",),
        ("@stones",), ("Display.Message", "Cyan", "Old standing stones, worn smooth. A faint rune on each.", "-"),
        ("@end",), ("End",)] + FAR, MAKER)
    SK.write_script("Read Shardgate_Plans", [
        ("Play.Sound", "Paper"),
        SK.say("Shardgate_Plans", "A SHARDGATE, by Bert, greatest wizard of the age.\\In the old ring of standing "
                                  "stones on the hill north of the Court: bind the stones with four bars of silver, "
                                  "set two sapphires in the runes, and at the ring's heart lay a Remnant's core.\\Then "
                                  "give it $Shards.Shardgate Shards of your own, and step through. Mind the Warden.",
               ("Fold the plans.", "@end")),
        ("@end",), ("End",)], MAKER)
    SK.write_script("Step Through Shardgate", [
        (">Distance.From.Clicked.Entity", "72", "@far"),
        (">On.Map", REALM, "@in"),
        ("Play.Sound", "Portal"),
        ("Display.Message", "Cyan", "You step back through the light, and the world settles round you.", "-"),
        ("Teleport", "Shardgate_Site", "-"),
        ("End",),
        ("@in",),
        ("Play.Sound", "Portal"),
        ("Display.Message", "Cyan", "You step into the light. Cold, then everything at once, then glass under your "
                                    "feet: the Shardrealm.", "-"),
        ("Teleport", "Realm_Gate", "-"),
        ("End",)] + FAR, MAKER)
    SK.write_script("Shatter Barrier_Anchor", [
        (">Distance.From.Clicked.Entity", "72", "@far"),
        ("Get.Value", "ATTRIBUTE", "ShardgateQuest", "Variable.1$"),
        (">Conditional", "$Variable.1=3", "@end"),
        (">Entity.State", "Anchor_Warden", "Walking,Standing,Fighting,Following", "@down"),
        ("Display.Message", "DarkRed", "The Warden stands over the anchor: it won't let you near.", "Denied"),
        ("End",),
        ("@down",), (">Got.Item", "Staff_of_Ashen", "1", "@nostaff"),
        ("Toggle.User.Input", "OFF"),
        ("Display.Message", "Cyan", "You raise the Staff of Ashen and speak Bert's words of Unbinding at the "
                                    "anchor..", "-"),
        ("Play.Sound", "SpellCast"),
        ("Wait", "2"),
        ("Remove.Entity", px(ANCHOR), "Barrier_Anchor"),
        ("Add.Entity", px(ANCHOR), "Barrier_Anchor_Broken", "StaticObject", "-"),
        ("Play.Sound", "Anchor_Shatter"),
        ("Update.Attribute", "ShardgateQuest", "=4"),
        ("Toggle.User.Input", "ON"),
        ("Display.Message", "Yellow", "..and it shatters. Far away, in the pass of Galaith, something gives. Tell "
                                      "Bert.", "-"),
        ("End",),
        ("@nostaff",), ("Display.Message", "DarkRed", "Your bare hands won't break it: it needs the Staff of "
                                                      "Ashen.", "Denied"),
        ("@end",), ("End",)] + FAR, MAKER)
    rows = [(">Distance.From.Clicked.Entity", "48", "@far")]
    for i, tool in enumerate(("Mithril_Pickaxe", "Steel_Pickaxe", "Pickaxe", "Bronze_Pickaxe")):
        rows += [("@pick%d" % i,), (">Got.Item", tool, "1", "@pick%d" % (i + 1) if i < 3 else "@nopick"),
                 ("Goto.Line", "@dig")]
    rows += [
        ("@dig",),
        ("Get.Value", "ATTRIBUTE", "RealmClusterAt", "Variable.4$"),
        ("Get.Value", "CALCULATION", "$Clock-$Variable.4", "Variable.5$"),
        ("Get.Value", "CALCULATION", "$Shards.Realm.Cluster.Hours*3600", "Variable.6$"),
        (">Conditional", "$Variable.5>=$Variable.6", "@dim"),
        ("Show.Skill", "Mining"),
        ("Play.Animation", "Rock_Chips", "3", "Mine"),
        ("Display.Message", "Cyan", "You chip at the glowing cluster.."),
        ("Wait", "2"),
        ("Update.Attribute", "RealmClusterAt", "=$Clock"),
        ("Give.Item", "Shard", "$Shards.Realm.Cluster"),
        ("Update.Skill", "Mining", "+0.3"),
        ("Play.Sound", "Absorb"),
        ("Display.Message", "Yellow", "..and $Shards.Realm.Cluster Shards come away in your hand."),
        ("End",),
        ("@dim",), ("Display.Message", "DarkRed", "The realm's clusters are dim: they haven't grown back since you "
                                                  "last dug.", "Fail"),
        ("End",),
        ("@nopick",), ("Display.Message", "DarkRed", "You need a pickaxe!", "Denied"), ("End",)] + FAR
    SK.write_script("Mine Shard_Cluster", rows, MAKER)
    SK.write_script("Bert and the Shardgate", [
        ("Get.Value", "ATTRIBUTE", "ShardgateQuest", "Variable.1$"),
        (">Conditional", "$Variable.1=4", "@s1"),
        SK.say("Bert", "Broken? You broke the anchor? In the Shardrealm? Ha! I said you were good. Did I say that? "
                       "I meant to.\\The barrier's nothing now but light and spite. Go to the pass: the staff will "
                       "break it for good this time.", ("I'm on my way.", "@done")),
        ("@done",),
        ("Update.Attribute", "ShardgateQuest", "=5"),
        ("Display.Message", "Yellow", "Quest complete: The Shardgate! The barrier's anchor is broken; the Shardgate "
                                      "stays open to you.", "Quest"),
        ("End",),
        ("@s1",), (">Conditional", "$Variable.1=1", "@late"),
        SK.say("Bert", "It held? Of course it held. Oh, don't look at me like that: I only half thought it would.\\"
                       "Listen. When the dragon drank the mountain's magic, what it couldn't hold it shattered, and "
                       "the pieces went somewhere: the Shardrealm, where all broken magic goes. The barrier draws on "
                       "it. It's anchored there, beyond the world.", ("How do I get there?", "@how")),
        ("@how",),
        SK.say("Bert", "You build a door. A Shardgate: the old ring of standing stones on the hill north of this Court "
                       "was one, once. Here are my plans. Silver, sapphires, a Remnant's core, and Shards: it drinks "
                       "them.\\Through the gate, find the anchor and break it with the staff. Something will be "
                       "guarding it. Something always is.", ("I'll build it.", "@plans")),
        ("@plans",),
        ("Give.Item", "Shardgate_Plans", "1"),
        ("Update.Attribute", "ShardgateQuest", "=2"),
        ("Display.Message", "Yellow", "Bert gave you his plans for a Shardgate (Read them).", "-"),
        ("End",),
        ("@late",), (">Quest.Can.Start", "ShardgateQuest", "@end"),
        SK.say("Bert", "The barrier's gone, yes, yes. But its anchor isn't: it still hums in the Shardrealm, beyond the "
                       "world, where all broken magic goes. I can feel it from here.\\Build a Shardgate in the old ring "
                       "of stones on the hill north of the Court: here are my plans. Go through, break the anchor with "
                       "the staff, and the realm's yours to wander.", ("I'll build it.", "@lateplans")),
        ("@lateplans",),
        ("Give.Item", "Shardgate_Plans", "1"),
        ("Update.Attribute", "ShardgateQuest", "=2"),
        ("Display.Message", "Yellow", "Quest started: The Shardgate. Bert gave you his plans (Read them).", "Quest"),
        ("@end",), ("End",)], MAKER)


# ================================================================== the quest, the chapters after it, the map's label
def quest():
    SK.quest("The Shardgate", "Bert", "ShardgateQuest", {
        0: "The barrier still stands in the pass of Galaith. Raise the Staff of Ashen against it.",
        1: "The barrier held: something beyond the world feeds it. Ask Bert, at the top of the Wizards' Court's "
           "tower.",
        2: "Build a Shardgate in the old ring of standing stones on the hill north of the Wizards' Court: 4 silver "
           "bars, 2 sapphires, a Remnant's core and Shards (Bert's plans).",
        3: "Step through the Shardgate into the Shardrealm. Get past its Warden, and shatter the barrier's anchor "
           "with the Staff of Ashen.",
        4: "The anchor is shattered. Tell Bert."}, 5,
        markers={0: "Galaith_Barrier", 1: "Court_Wizard", 2: "Shardgate_Site", 3: "Shardgate_Site", 4: "Court_Wizard"},
        chapter=15, requires="The Sword of Valour", after="The Sword of Valour")
    q = p("data", "Quests.ini")
    SK.section(q, "The Shardgate", [("Reward.Shards", "30"), ("Reward.XP", "Magic 4 Crafting 3")])
    SK.section(q, "The Dragon of Galaith", [("Chapter", "16"), ("Requires.Quests", "The Shardgate")])
    SK.section(q, "The Royal Guard", [("Chapter", "17")])
    SK.section(q, "The True Heir", [("Chapter", "18")])
    SK.place_label("Places", "The Shardgate", "Shardgate_Site [if $Attr.ShardgateQuest>=3]")


def main():
    art()
    sounds()
    data()
    ring_on_the_hill()
    realm()
    scripts()
    quest()
    print("The Shardgate: done")


if __name__ == "__main__":
    main()
