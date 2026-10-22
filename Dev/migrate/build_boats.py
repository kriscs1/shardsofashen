"""The ferry's boats, tied up at the two piers (the Isle's, 1,2,0, and Southport's, 1,3,0): a little sailing boat with
a planked hull, two thwarts and a mast with its sail furled, bobbing on the water (Anim.Frames: <Name>1 and 2).

  * Boat001: lying east-west (64 x 48: the hull in the bottom 32, the mast above), along Southport's pier.
  * Boat002: lying north-south (32 x 80), along the stem of the Isle's pier.

Run:  python -I "Dev\\migrate\\build_boats.py"   (draws the sprites; build_content puts them on the maps)
"""
import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

HULL, HULL_DK, RIM, RIM_LT = (104, 66, 38), (70, 42, 24), (158, 112, 66), (196, 150, 96)
INSIDE, SEAT, MAST, SAIL, SAIL_DK = (128, 86, 50), (176, 128, 78), (66, 44, 28), (232, 222, 196), (186, 172, 140)
FOAM, ROPE = (226, 240, 250), (204, 182, 128)

# where they go: map -> (sprite, pixel x, pixel y)
PLACES = {"1,3,0": ("Boat001", 12 * 32, 2 * 32 - 16), "1,2,0": ("Boat002", 19 * 32, 11 * 32 - 16)}
EXAMINE = "The ferry's boat, tied up at the pier. Its sail is furled and it rocks gently on the swell."


def hull_layer(bob):
    """The boat lying east-west, bow to the east, on a 64 x 32 layer (RGBA)."""
    im = Image.new("RGBA", (64, 32), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    y = 4 + bob
    outline = [(4, y + 10), (10, y + 3), (44, y + 2), (56, y + 6), (62, y + 12), (56, y + 18), (44, y + 22),
               (10, y + 21), (4, y + 14)]
    d.polygon(outline, fill=HULL_DK)                              # the hull's side (in shade below)
    d.polygon([(p[0], p[1] - 2) for p in outline], fill=HULL)
    inner = [(8, y + 9), (12, y + 5), (43, y + 4), (53, y + 8), (57, y + 11), (52, y + 15), (43, y + 18),
             (12, y + 17), (8, y + 13)]
    d.polygon(inner, fill=INSIDE)
    for k in range(3):                                            # the planks inside
        d.line([(12, y + 8 + k * 3), (50, y + 8 + k * 3)], fill=(112, 74, 42))
    d.line([(10, y + 3), (44, y + 2), (56, y + 6)], fill=RIM_LT)  # the gunwale, lit along the top
    d.line([(10, y + 19), (44, y + 20), (56, y + 16)], fill=RIM)
    for sx in (20, 36):                                           # two thwarts (seats)
        d.rectangle([sx, y + 5, sx + 3, y + 17], fill=SEAT)
        d.line([(sx + 3, y + 5), (sx + 3, y + 17)], fill=HULL_DK)
    d.rectangle([4, y + 9, 6, y + 15], fill=HULL_DK)              # the transom
    for x in range(6, 60, 4):                                     # foam where it meets the water
        d.point((x + bob % 2, y + 23), fill=FOAM)
    for x in range(8, 56, 7):
        d.point((x + 2 - bob, y + 25), fill=FOAM)
    return im


def mast(d, x, top, bottom):
    d.rectangle([x, top, x + 1, bottom], fill=MAST)
    d.rectangle([x - 2, top + 3, x + 3, top + 13], fill=SAIL)      # the furled sail, lashed to the mast
    for yy in range(top + 4, top + 13, 3):
        d.line([(x - 2, yy), (x + 3, yy)], fill=SAIL_DK)
    d.point((x, top - 1), fill=RIM_LT)


def boat_east(bob):
    im = Image.new("RGBA", (64, 48), (0, 0, 0, 0))
    im.alpha_composite(hull_layer(bob), (0, 16))
    d = ImageDraw.Draw(im)
    mast(d, 30, 1 + bob, 28 + bob)
    d.line([(58, 30 + bob), (63, 34)], fill=ROPE)                  # the mooring line to the pier
    return im


def boat_south(bob):
    hull = hull_layer(bob).rotate(-90, expand=True)              # bow to the south
    im = Image.new("RGBA", (32, 80), (0, 0, 0, 0))
    im.alpha_composite(hull, (0, 16))
    d = ImageDraw.Draw(im)
    mast(d, 15, 9 + bob, 46 + bob)
    d.line([(26, 48 + bob), (31, 52)], fill=ROPE)
    return im


def to_rows(im):
    w, h = im.size
    px = im.load()
    return [[px[x, y][:3] if px[x, y][3] > 127 else None for x in range(w)] for y in range(h)]


SPRITES = {"Boat001": boat_east, "Boat002": boat_south}


def draw_sprites():
    import sprite_kit as K
    made = []
    for name, make in SPRITES.items():
        frames = [make(0), make(1)]
        for i, f in enumerate(frames, 1):
            if K.save("Entities", "%s%d" % (name, i), to_rows(f)):
                made.append("%s%d" % (name, i))
        if K.save("Entities", name, to_rows(frames[0])):
            made.append(name)
    return made


def extend(world, content):
    """Entities.ini, the boats on 1,3,0 (a built map); the Isle's (protected) goes in through patches()."""
    for name in SPRITES:
        content.ENTITIES[name] = [("Type", "StaticObject"), ("Use.Words", "Examine"), ("Examine.Info", EXAMINE),
                                  ("Solid", "0"), ("Anim.Frames", "2"), ("Anim.Speed", "900")]
    world.WATER_ENTITIES = set(getattr(world, "WATER_ENTITIES", ())) | set(SPRITES)
    for m, (name, x, y) in PLACES.items():
        if m in world.MAPS and m not in world.PROTECTED_MAPS:
            world.MAPS[m]["entities"].append(("StaticObject", name, x, y))


def protected_places(world):
    return {m: [("StaticObject", name, x, y)] for m, (name, x, y) in PLACES.items() if m in world.PROTECTED_MAPS}


if __name__ == "__main__":
    print("\n".join("wrote " + n for n in draw_sprites()))
