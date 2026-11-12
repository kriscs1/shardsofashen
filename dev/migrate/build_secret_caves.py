"""Secret rooms in the caves (the owner's wish): a chamber in the solid rock behind a cave's wall, under a black roof so
it can't be seen from outside, reached by walking through a stretch of wall that isn't really there.

  * Cave_Wall_Hollow001: a wall face you can walk through; a hairline seam is all that gives it away. Stepping into it
    runs its Trigger, Hidden_Way_<map> (a word and a sound, once, and a little Stealth). A thief's eye may catch the
    draught coming through it first (senses.py).
  * Hidden_Dark001: the black roof over the chamber and its walls (a roof group of its own: gone when you're under it,
    as a house's is).
  * In the chamber: a chest, each player's own (Hidden_Cache_<map>, by what lives on that map), and what was left there:
    a smugglers' stash, a hermit's bolt-hole, a shrine, a dead adventurer, a miners' store (Bones, Cobweb, Bedroll: drawn
    here).
  * Where: a map under the world with cave walls and rock enough behind them, MOST of them, two of them in the Mire
    Tunnel; never the Isle's caves or a place the story's in (SKIP).

Safe to run again (the pictures and scripts redrawn; once any room is there, no more are dug).

  python -I "dev\\migrate\\build_secret_caves.py"
"""
import math
import os
import random
import struct
import sys
import wave

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "estforlan"))
from common import Ini, p, read_lines, write_image, write_lines, sound_file          # noqa: E402
import world_edit as W                           # noqa: E402
from world_edit import XT, YT, h01               # noqa: E402

from PIL import Image, ImageDraw                 # noqa: E402

MOST = 12
GROUP = "97"                                     # (the roof group: no house on a cave's map to clash with)
ROOF = "Hidden_Dark001.%s" % GROUP
SKIP = {"1,1,-1", "1,1,-2", "2,1,-2", "2,2,-2", "3,1,-1", "3,1,-2",   # (the Isle's)
        "-7,11,-1", "21,4,-10", "3,18,-1"}       # (the King's mine, the Shardrealm, the Sunken Grimoire's library)
MIRE = {"-6,5,-1", "-7,5,-1", "-1,5,-1", "-1,6,-1", "0,5,-1", "0,6,-1", "1,5,-1", "1,6,-1", "2,6,-1", "2,4,-1"}
TIERS = [   # (the most a map's monsters' level, what its cache holds)
    (6, [("Shard", 10), ("Gold_Coin(s)", 40), ("Minor_Healing_Draught", 2)]),
    (14, [("Shard", 18), ("Gold_Coin(s)", 90), ("Healing_Draught", 2), ("Ruby", 1)]),
    (99, [("Shard", 28), ("Gold_Coin(s)", 160), ("Major_Healing_Draught", 2), ("Ember_Shard", 1)]),
]
THEMES = [  # (what stands against its back wall, what lies on its floor)
    ("smugglers", ["Cellar_Crate001", "Cellar_Barrel001", "Sacks001"], []),
    ("hermit", ["Candles001", "Bookshelf001"], ["Bedroll001"]),
    ("shrine", ["Altar001", "Candles001"], ["Bones002"]),
    ("adventurer", ["Cobweb001"], ["Bones001", "Bones002"]),
    ("miners", ["Cellar_Barrel001", "Crate001", "Cobweb001"], ["Bones001"]),
]
WORDS = ["The rock gives under your hand. It isn't rock at all, only shadow, and you're through it.",
         "You lean on the wall and it isn't there. Cold air, and a dark that goes on.",
         "A wall, you'd have sworn. You walk straight through it into the dark beyond."]


# ================================================================== pictures
def art():
    made = write_image(p("sprites", "Tiles", "Hidden_Dark001.png"), Image.new("RGBA", (32, 32), (0, 0, 0, 255)))
    wall = Image.open(p("sprites", "Tiles", "Cave_Wall002.png")).convert("RGBA")
    d = ImageDraw.Draw(wall)
    for y, x in ((9, 15), (11, 16), (14, 16), (16, 15), (19, 15), (22, 16)):        # (a hairline seam)
        px = wall.getpixel((x, y))
        d.point((x, y), fill=tuple(int(v * 0.72) for v in px[:3]) + (255,))
    made += write_image(p("sprites", "Tiles", "Cave_Wall_Hollow001.png"), wall)
    for n, seed in ((1, 11), (2, 23)):
        made += write_image(p("sprites", "Tiles", "Bones%03d.png" % n), bones(seed))
    made += write_image(p("sprites", "Tiles", "Cobweb001.png"), cobweb())
    made += write_image(p("sprites", "Tiles", "Bedroll001.png"), bedroll())
    return made


def outlined(im):
    a = im.getchannel("A").point(lambda v: 255 if v > 0 else 0)
    out = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ring = Image.new("RGBA", im.size, (30, 24, 20, 255))
    for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        out.paste(ring, (dx, dy), a)
    out.alpha_composite(im)
    return out


def bones(seed):
    rng = random.Random(seed)
    im = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    pale = (214, 206, 186, 255)
    for _ in range(4):
        x, y = rng.randint(7, 24), rng.randint(15, 26)
        dx, dy = rng.randint(-6, 6), rng.randint(-3, 3)
        d.line((x, y, x + dx, y + dy), fill=pale, width=1)
        d.point([(x, y - 1), (x + dx, y + dy + 1)], fill=pale)
    x, y = rng.randint(11, 19), rng.randint(14, 20)              # (the skull)
    d.ellipse((x, y, x + 6, y + 5), fill=pale)
    d.point([(x + 2, y + 2), (x + 4, y + 2)], fill=(50, 44, 40, 255))
    return outlined(im)


def cobweb():
    """In the corner it's put against (the top left): threads out from it, and across."""
    im = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    thread = (220, 224, 228, 130)
    ends = [(24, 0), (22, 8), (16, 15), (8, 21), (0, 24)]
    for e in ends:
        d.line((0, 0, e[0], e[1]), fill=thread)
    for t in (0.35, 0.65, 0.9):
        pts = [(e[0] * t, e[1] * t) for e in ends]
        d.line(pts, fill=thread)
    return im


def bedroll():
    im = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((5, 13, 27, 26), 3, fill=(106, 86, 62, 255))
    d.rounded_rectangle((5, 13, 12, 26), 3, fill=(146, 128, 96, 255))     # (its folded end, a pillow of sorts)
    for x in (16, 20, 24):
        d.line((x, 14, x, 25), fill=(84, 66, 48, 255))
    return outlined(im)


def sound():
    """Stone that isn't there: a low breath of cold air and a soft scrape."""
    path = sound_file("Hidden_Way")
    rate = 22050
    rng = random.Random("hidden way")
    n = int(rate * 0.7)
    low = 0.0
    out = []
    for i in range(n):
        t = i / rate
        low += (rng.uniform(-1, 1) - low) * 0.06                  # (a breath: noise, kept low)
        env = min(1.0, t / 0.12) * math.exp(-t * 3.2)
        v = low * 2.4 * env + 0.14 * math.sin(2 * math.pi * 74 * t) * env
        out.append(max(-1.0, min(1.0, v)))
    data = b"".join(struct.pack("<h", int(v * 30000)) for v in out)
    if os.path.exists(path):
        with wave.open(path, "rb") as f:
            if f.readframes(f.getnframes()) == data:
                return
    with wave.open(path, "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(rate)
        f.writeframes(data)


def data():
    tiles = Ini(p("data", "Tiles.ini"))
    open_mask, shut = "1" * 49, "0" * 49
    for name, keys in (
            ("Hidden_Dark001", (("Walkable.Data", open_mask), ("Show.Name", "0"), ("Use.Words", ""),
                                ("Examine.Info", ""), ("Line.of.Sight", "1"), ("Layer", "Roof"))),
            ("Cave_Wall_Hollow001", (("Walkable.Data", open_mask), ("Show.Name", "1"), ("Use.Words", ""),
                                     ("Examine.Info", "A wall of rough rock."), ("Line.of.Sight", "0"), ("Blend", "4"),
                                     ("Blend.Texture", "Cave_Wall001"))),
            ("Bones001", (("Walkable.Data", open_mask), ("Show.Name", "0"), ("Use.Words", ""),
                          ("Examine.Info", "Old bones. Whoever it was, they got this far."), ("Line.of.Sight", "1"),
                          ("Layer", "Decor"))),
            ("Bones002", (("Walkable.Data", open_mask), ("Show.Name", "0"), ("Use.Words", ""),
                          ("Examine.Info", "Bones, picked clean a long time ago."), ("Line.of.Sight", "1"),
                          ("Layer", "Decor"))),
            ("Cobweb001", (("Walkable.Data", open_mask), ("Show.Name", "0"), ("Use.Words", ""),
                           ("Examine.Info", "Cobwebs, thick with dust."), ("Line.of.Sight", "1"), ("Layer", "Decor"))),
            ("Bedroll001", (("Walkable.Data", open_mask), ("Show.Name", "0"), ("Use.Words", ""),
                            ("Examine.Info", "A bedroll, long since gone to mould."), ("Line.of.Sight", "1"),
                            ("Layer", "Decor")))):
        for k, v in keys:
            tiles.set(name, k, v)
    tiles.save(p("data", "Tiles.ini"))
    path = p("dev", "Minimap Colours.txt")
    lines = read_lines(path)
    while lines and not lines[-1]:
        lines.pop()
    have = {ln.split("\t")[0]: ln.split("\t")[1] for ln in lines if "\t" in ln}
    for name, like in (("Hidden_Dark001", None), ("Cave_Wall_Hollow001", "Cave_Wall002"), ("Bones001", "Cave_Floor001"),
                       ("Bones002", "Cave_Floor001"), ("Cobweb001", "Cave_Floor001"), ("Bedroll001", "Cave_Floor001")):
        if name not in have:
            lines.append("%s\t%s" % (name, have[like] if like else "0 0 0"))
    write_lines(path, lines)


# ================================================================== a room
def floorish(t):
    return t.startswith(("Cave_Floor", "Cave_Puddle", "Cave_Steps"))


def tile_at(m, x, y):
    return W.parts(m.rows[y - 1][x - 1])[0] if 1 <= x <= XT and 1 <= y <= YT else None


def seen_side(c, door, d):
    """Is c on the cave's side of the wall the way in is in (what you see from the cave stays as it was)?"""
    return c[1] >= door[1] if d[1] else (c[0] <= door[0] if d[0] > 0 else c[0] >= door[0])


def room_rects(x, y, d):
    """Rooms that could lie beyond the wall at x, y, the way d (north, east or west), biggest first: (x1, y1, x2, y2)."""
    for w, h in ((7, 4), (6, 4), (7, 3), (6, 3), (5, 4), (5, 3), (4, 4), (4, 3)):
        if d[1]:                                         # (north: the way in along its south side, not at its edge)
            for x1 in range(x - w + 2, x):
                yield (x1, y - h, x1 + w - 1, y - 1)
        else:                                            # (east or west: along its side)
            x1 = x + 1 if d[0] > 0 else x - w
            for y1 in range(y - h + 2, y):
                yield (x1, y1, x1 + w - 1, y1 + h - 1)


def room_at(m, x, y, used):
    """The biggest room behind the wall at x, y (rows and columns from 1): (room, the way in), or None."""
    if not (tile_at(m, x, y) or "").startswith(("Cave_Wall001", "Cave_Wall002", "Cave_Wall003")):
        return None
    for d in ((0, -1), (1, 0), (-1, 0)):
        here = tile_at(m, x - d[0], y - d[1]) or ""      # (the floor you come from)
        if not floorish(here) or here.startswith("Cave_Steps"):
            continue
        for x1, y1, x2, y2 in room_rects(x, y, d):
            if x1 - 1 < 2 or x2 + 1 > XT - 1 or y1 - 1 < 2 or y2 + 1 > YT - 1:
                continue
            ring = [(i, j) for i in range(x1 - 1, x2 + 2) for j in range(y1 - 1, y2 + 2)]
            ok = True
            for c in ring:
                t = tile_at(m, *c)
                if seen_side(c, (x, y), d):
                    ok = not floorish(t)                 # (its own wall: wall it must be)
                else:
                    ok = t == "Black001" and not W.parts(m.rows[c[1] - 1][c[0] - 1])[1]
                if not ok:
                    break
            if ok and not any(x1 - 2 <= c[0] <= x2 + 2 and y1 - 2 <= c[1] <= y2 + 2 for c in used):
                return (x1, y1, x2, y2), d
    return None


def things_cells(m):
    """Where its map lines are (rows and columns from 1)."""
    mx, my, _ = W.mxyz(m.name)
    out = []
    for ln in m.ents:
        c = W.line_cell(ln, mx, my)
        if c is not None:
            out.append((c[0] - mx * XT + 1, c[1] - my * YT + 1))
    return out


def best_room(m):
    used = things_cells(m)
    opts = []
    for y in range(2, YT):
        for x in range(2, XT):
            if (x, y) in used:
                continue
            found = room_at(m, x, y, used)
            if found:
                r, d = found
                opts.append((-(r[2] - r[0] + 1) * (r[3] - r[1] + 1), h01("hidden door", x, y, len(m.name)), x, y, r, d))
    return min(opts)[2:] if opts else None


def tier_of(m, ents):
    top = 0
    for ln in m.ents:
        q = ln.split("\t")
        if q[0] == "NPC":
            try:
                top = max(top, int(ents.get(q[1], "Level", "0") or 0))
            except ValueError:
                pass
    return next(g for lim, g in TIERS if top <= lim)


def dig(m, door, room, d, slug, theme, rng):
    x, y = door
    x1, y1, x2, y2 = room
    inside = (x + d[0], y + d[1])                        # (the floor just through the wall: kept clear)
    floor = {(i, j) for i in range(x1, x2 + 1) for j in range(y1, y2 + 1)}
    for c in ((x1, y1), (x2, y1), (x1, y2), (x2, y2)):   # (its corners knocked off: it's a cave, not a room)
        if rng.random() < 0.6 and abs(c[0] - inside[0]) + abs(c[1] - inside[1]) > 1:
            floor.discard(c)
    clear = {inside} | {(inside[0] + i, inside[1] + j) for i, j in ((1, 0), (-1, 0), (0, 1), (0, -1))}
    decor = {}
    backs = sorted((c for c in floor if (c[0], c[1] - 1) not in floor and c not in clear), key=lambda c: rng.random())
    for name, c in zip(THEMES[theme][1], backs[1:]):      # (backs[0]: the chest's)
        decor[c] = name
    opens = sorted((c for c in floor if c not in decor and c not in clear and c not in backs[:1] and
                    (c[0], c[1] + 1) in floor), key=lambda c: rng.random())
    for name, c in zip(THEMES[theme][2], opens):
        decor[c] = name
    for c in floor:
        r = rng.random()
        t = "Cave_Floor001" if r < 0.6 else "Cave_Floor002" if r < 0.85 else "Cave_Floor003"
        over = {"Roof": ROOF}
        if c in decor:
            over["Decor"] = decor[c]
        m.rows[c[1] - 1][c[0] - 1] = W.join(t, over)
    near = {(c[0] + i, c[1] + j) for c in floor for i in (-1, 0, 1) for j in (-1, 0, 1)} - floor
    for c in near:
        if not seen_side(c, door, d):                    # (the wall you see from the cave: as it was)
            t = "Cave_Wall002" if (c[0], c[1] + 1) in floor else "Cave_Wall001"
            m.rows[c[1] - 1][c[0] - 1] = W.join(t, {"Roof": ROOF})
    for i in range(x1, x2 + 1):                          # (the rock left in its knocked-off corners: dark too)
        for j in range(y1, y2 + 1):
            if (i, j) not in floor and (i, j) not in near:
                m.rows[j - 1][i - 1] = W.join("Black001", {"Roof": ROOF})
    m.rows[y - 1][x - 1] = "Cave_Wall_Hollow001"
    m.ents.append("Trigger\tHidden_Way_%s\t%d\t%d" % (slug, x, y))
    c = backs[0]
    m.ents.append("StaticObject\tChest\t%d\t%d\tId=Hidden_Cache_%s" % ((c[0] - 1) * 32, (c[1] - 1) * 32, slug))


def scripts(slug, name, finds, rng):
    head = "// Generated by dev\\migrate\\build_secret_caves.py (%s)" % name
    way = [head,
           "01\t>Conditional\t$Attr.Hidden_Way_%s=0\t06" % slug,
           "02\tUpdate.Attribute\tHidden_Way_%s\t=1" % slug,
           "03\tDisplay.Message\tCyan\t%s\tHidden_Way" % rng.choice(WORDS),
           "04\tUpdate.Skill\tStealth\t+0.5",
           "05\tEnd",
           "06\tEnd"]
    W.write(os.path.join(W.ROOT, "data", "Scripts", "Hidden_Way_%s.script" % slug), "\r\n".join(way) + "\r\n")
    n = len(finds) + 5                                   # (the line after what it gives)
    rows = [head,
            "01\t>Distance.From.Clicked.Entity\t48\t%02d" % (n + 3),
            "02\t>Conditional\t$Attr.Hidden_Cache_%s=0\t%02d" % (slug, n + 1),
            "03\tUpdate.Attribute\tHidden_Cache_%s\t=1" % slug,
            "04\tPlay.Sound\tChest"]
    for i, (item, q) in enumerate(finds):
        rows.append("%02d\tGive.Item\t%s\t%d" % (i + 5, item, q))
    rows += ["%02d\tEnd" % n,
             "%02d\tDisplay.Message\tCyan\tThe chest is empty.\tEmpty" % (n + 1), "%02d\tEnd" % (n + 2),
             "%02d\tDisplay.Message\tDarkRed\tYou are too far away!\tDenied" % (n + 3), "%02d\tEnd" % (n + 4)]
    W.write(os.path.join(W.ROOT, "data", "Scripts", "Open Hidden_Cache_%s.script" % slug), "\r\n".join(rows) + "\r\n")


def slug_of(name):
    return name.replace("-", "n").replace(",", "_")


def place():
    ents = Ini(p("data", "Entities.ini"))
    worlds = {}
    for z in (-1, -2, -3):
        worlds[z] = W.World(z)
    every = [m for w in worlds.values() for m in w.maps.values()]
    if any(ln.startswith("Trigger\tHidden_Way_") for m in every for ln in m.ents):
        return 0, 0
    opts = []
    for m in every:
        if m.name in SKIP:
            continue
        found = best_room(m)
        if found:
            opts.append((m.name not in MIRE, h01("hidden room", len(m.name), sum(map(ord, m.name))), m, found))
    opts.sort(key=lambda o: o[:2])
    print("  %d maps have room for one" % len(opts))
    mire = [o for o in opts if not o[0]][:2]
    rest = [o for o in opts if o[0]]
    chosen = mire + rest[:MOST - len(mire)]
    done = 0
    for i, (_, _, m, (x, y, room, d)) in enumerate(chosen):
        slug = slug_of(m.name)
        rng = random.Random("hidden " + m.name)
        dig(m, (x, y), room, d, slug, i % len(THEMES), rng)
        scripts(slug, m.name, tier_of(m, ents), rng)
        w = worlds[W.mxyz(m.name)[2]]
        w.touch(m)
        done += 1
        print("  %s: the way in at %d,%d, room %s (%s)" % (m.name, x, y, room, THEMES[i % len(THEMES)][0]))
    n = sum(w.save() for w in worlds.values())
    return done, n


def main():
    made = art()
    sound()
    data()
    done, n = place()
    print("Secret caves: %d pictures written; %d rooms dug, on %d maps" % (made, done, n))


if __name__ == "__main__":
    main()
