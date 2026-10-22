"""Worn equipment: overlays drawn over the player so you can see what they wear (Sprites\\Worn\\*.png).

Run:  python -I "Dev\\migrate\\build_worn.py" [--preview]
Deterministic and re-runnable: only files that change are written. --preview writes Dev\\Renders\\Worn preview.png
(the player in each direction, bare and then in a few outfits).

For every item in Data\\Entities.ini with a Slot (except rings) it writes Worn_<Item><Dir><Frame>.png, the same 12
frames as the player (Dir 1 = north, 2 = east, 4 = south, 8 = west; Frame a, b, c), made from the player's own body
parts in build_player.py, so they fit exactly: body armour recolours the torso and sleeves, leg armour the legs, boots
the feet, gloves the hands; helmets, hats, weapons and shields are drawn on. The look comes from the item's name:
its material (Leather, Bronze, Iron, Steel, Mithril, Copper, Silver, Wooden, Oak, Willow, Yew) and kind (Sword,
Dagger, Staff, Shield, Helm, Cap, Hat, Tiara, Platebody/Body, Platelegs/Legs, Boots, Gloves/Gauntlets).
The game layers them over the player in the order legs, feet, body, hands, head, shield, weapon, and keeps them in step
with the walking frames. An item with no Worn_ frames is simply not shown. Re-run after adding equipment.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_player as BP
import sprite_kit as K
from common import Ini, p

OUT = "Worn"
CX = BP.CX

MATERIALS = {   # light, mid, dark
    "Leather": ((196, 142, 86), (154, 102, 56), (104, 66, 32)),
    "Copper": ((232, 154, 100), (188, 102, 58), (120, 58, 28)),
    "Bronze": ((222, 168, 92), (170, 112, 46), (106, 62, 22)),
    "Iron": ((206, 206, 214), (150, 150, 158), (94, 94, 102)),
    "Steel": ((216, 228, 244), (160, 180, 204), (98, 116, 144)),
    "Mithril": ((132, 222, 218), (50, 150, 160), (22, 84, 102)),
    "Dragonscale": ((236, 96, 72), (170, 32, 28), (92, 14, 12)),    # Wardhaven's Dragonforge (build_cinder.py)
    "Silver": ((246, 248, 255), (200, 206, 220), (130, 136, 150)),
    "Gold": ((255, 236, 130), (226, 180, 52), (150, 108, 18)),
    "Wooden": ((186, 130, 72), (150, 100, 52), (100, 64, 30)),
    "Oak": ((160, 112, 60), (126, 84, 40), (86, 54, 22)),
    "Willow": ((230, 218, 166), (180, 166, 112), (120, 108, 68)),
    "Yew": ((200, 112, 82), (152, 72, 48), (96, 36, 22)),
    "Chefs": ((255, 255, 255), (232, 232, 236), (186, 186, 196)),
    "Dragon": ((255, 130, 90), (200, 40, 30), (110, 16, 12)),     # the Dragon Sword (build_dragon.py)
}
GOLD = MATERIALS["Gold"]
ORBS = {"Willow": ((90, 140, 240), (180, 210, 255), (30, 50, 150)), "Yew": ((220, 40, 50), (255, 150, 150), (120, 10, 20))}
SHIELD_FACES = {     # (face colour, emblem colour) for metal shields; wooden ones show their planks
    "Iron_Shield": ((170, 36, 30), GOLD[1]), "Steel_Shield": ((40, 70, 170), GOLD[1]),
    "Bronze_Shield": (MATERIALS["Bronze"][1], MATERIALS["Bronze"][0]),
    "Mithril_Shield": (MATERIALS["Mithril"][1], (240, 240, 240)),
}


def material(name):
    for m in MATERIALS:
        if name.startswith(m):
            return m
    return None


def kind(name, slot):
    for k in ("Platebody", "Platelegs", "Gauntlets", "Gloves", "Boots", "Helm", "Cap", "Hat", "Tiara", "Sword", "Bow",
              "Dagger", "Staff", "Shield", "Body", "Legs"):
        if k in name:
            return k
    return None


# ------------------------------------------------------------------ the player's body parts, frame by frame
def part(direction, frame, which):
    """A code grid with only one part of the player drawn ('legs', 'torso', 'arms', 'head')."""
    g = BP.blank()
    side = direction in ("2", "8")
    if which == "legs":
        BP.legs_side(g, frame, 1) if side else BP.legs_front(g, frame)
    elif which == "torso":
        BP.torso_side(g, 1) if side else BP.torso_front(g, direction == "1")
    elif which == "arms":
        BP.arm_side(g, frame, 1) if side else BP.arms_front(g, frame)
    elif which == "head":
        if side:
            BP.head_side(g, 1)
        elif direction == "4":
            BP.head_front(g)
        else:
            BP.head_back(g)
    return BP.mirror(g) if direction == "8" else g


def blank():
    return [[None] * 32 for _ in range(32)]


def put(img, x, y, c):
    if 0 <= x < 32 and 0 <= y < 32:
        img[y][x] = c


def recolour(grid, codes, mat):
    """Pixels of grid whose code is in codes (code -> 0 light / 1 mid / 2 dark) in the material's colours."""
    img = blank()
    for y in range(32):
        for x in range(32):
            c = grid[y][x]
            if c in codes:
                img[y][x] = mat[codes[c]]
    return img


def hands(direction, frame):
    """[(x0, x1, top, bottom)] of each hand, left to right on screen."""
    g = part(direction, frame, "arms")
    pts = [(x, y) for y in range(32) for x in range(32) if g[y][x] == "S"]
    left = [(x, y) for x, y in pts if x < CX]
    right = [(x, y) for x, y in pts if x >= CX]
    out = []
    for group in (left, right):
        if group:
            out.append((min(x for x, _ in group), max(x for x, _ in group), min(y for _, y in group), max(y for _, y in group)))
    return out


def weapon_hand(direction, frame):
    hs = hands(direction, frame)
    if direction == "4":
        return hs[0]                          # facing you: the right hand is on the left of the screen
    if direction == "1":
        return hs[-1]                         # from behind: on the right
    return hs[0]                              # side on: the one visible hand


def shield_hand(direction, frame):
    hs = hands(direction, frame)
    if direction == "4":
        return hs[-1]
    if direction == "1":
        return hs[0]
    return None


# ------------------------------------------------------------------ each kind of item
def body(d, f, mat, plate):
    img = recolour(part(d, f, "torso"), {"T": 1, "t": 0, "k": 2}, mat)
    arms = recolour(part(d, f, "arms"), {"t": 0}, mat)
    for y in range(32):
        for x in range(32):
            if arms[y][x]:
                img[y][x] = arms[y][x]
    if plate:                                 # a highlight down the breastplate and a row of rivets
        x0 = CX - 1 if d in ("1", "4") else (CX if d == "2" else CX - 1)
        for y in range(13, 19):
            if img[y][x0]:
                img[y][x0] = mat[0]
        for x in range(CX - 4, CX + 4, 2):
            if img[16][x]:
                img[16][x] = mat[2]
    return img


def legs(d, f, mat):
    return recolour(part(d, f, "legs"), {"P": 1, "p": 2}, mat)


def feet(d, f, mat):
    return recolour(part(d, f, "legs"), {"B": 1, "b": 2}, mat)


def gloves(d, f, mat):
    return recolour(part(d, f, "arms"), {"S": 1}, mat)


def headgear(d, f, mat, k):
    head = part(d, f, "head")
    img = blank()
    pts = [(x, y) for y in range(32) for x in range(32) if head[y][x]]
    if not pts:
        return img
    top = min(y for _, y in pts)
    x0, x1 = min(x for x, _ in pts), max(x for x, _ in pts)
    if k == "Hat":                            # a tall white chef's hat
        for y in range(0, top + 3):
            for x in range(CX - 4, CX + 4):
                put(img, x, y, mat[1] if (x + y) % 4 else mat[2])
        for x in range(CX - 5, CX + 5):
            put(img, x, top + 3, mat[2])
        return img
    if k == "Tiara":                          # a silver band with a sapphire in front
        for x in range(x0, x1 + 1):
            if head[top + 2][x]:
                put(img, x, top + 2, mat[0] if x % 2 else mat[1])
        if d == "4":
            put(img, CX - 1, top + 1, (60, 100, 220))
            put(img, CX, top + 1, (60, 100, 220))
        return img
    bottom = top + (3 if k == "Cap" else 4)
    if d == "1":
        bottom += 1                           # from behind it covers more of the head
    for y in range(top, bottom + 1):
        for x in range(32):
            if head[y][x]:
                img[y][x] = mat[0] if y == top else mat[1]
    for x in range(x0, x1 + 1):               # the rim
        if head[bottom][x] or head[bottom - 1][x]:
            put(img, x, bottom, mat[2])
    if k == "Cap" and d in ("2", "8"):        # the peak sticks out in front
        put(img, x1 + 1 if d == "2" else x0 - 1, bottom, mat[2])
    if k == "Helm" and d == "4":              # a nose guard
        put(img, CX - 1, bottom + 1, mat[1])
        put(img, CX - 1, bottom + 2, mat[2])
    if k == "Helm" and d in ("2", "8"):
        put(img, x1 - 1 if d == "2" else x0 + 1, bottom + 1, mat[1])
    return img


def weapon(d, f, mat, k, name):
    img = blank()
    hx0, hx1, ht, hb = weapon_hand(d, f)
    if k == "Staff":
        wood = MATERIALS[material(name)]
        x = hx0 if d != "1" else hx1
        if d in ("2", "8"):
            x = hx1 + 1 if d == "2" else hx0 - 1
        for y in range(max(0, ht - 13), min(31, hb + 5) + 1):
            put(img, x, y, wood[1] if y % 3 else wood[2])
        orb = ORBS.get(material(name))
        top = max(0, ht - 14)
        if orb:
            for dx, dy, c in ((0, 0, orb[1]), (1, 0, orb[0]), (0, 1, orb[0]), (1, 1, orb[2])):
                put(img, x + dx - (1 if d == "8" else 0), top + dy, c)
        else:
            put(img, x - 1, top + 1, wood[2]); put(img, x + 1, top + 1, wood[2]); put(img, x, top, wood[0])
        return img
    if k == "Bow":                            # an arc held upright, the string straight
        wood = MATERIALS[material(name)]
        x = hx0 - 1 if d in ("4", "8") else hx1 + 1
        bulge = -1 if d in ("4", "8") else 1
        top, bottom = max(0, ht - 9), min(31, hb + 6)
        for y in range(top, bottom + 1):
            t = (y - top) / float(max(1, bottom - top))
            put(img, x + int(round(bulge * 2.5 * math.sin(math.pi * t))), y, wood[1] if y % 3 else wood[2])
            if 0 < t < 1:
                put(img, x, y, (230, 225, 210))       # the string
        return img
    length = 6 if k == "Dagger" else 10
    if d in ("1", "4"):                       # held up, by the side
        x = hx0 - 1 if d == "4" else hx1 + 1
        for x2 in (x - 1, x, x + 1):
            put(img, x2, ht - 1, GOLD[1])     # the guard
        for y in range(ht - 1 - length, ht - 1):
            put(img, x, y, mat[0])
            put(img, x + (1 if d == "4" else -1), y, mat[2] if y > ht - length else None)
        put(img, x, ht - 2 - length, mat[0])
        put(img, x, hb + 1, GOLD[2])          # the pommel under the hand
    else:                                     # side on: pointing forward and up
        step = 1 if d == "2" else -1
        x, y = (hx1 + 1 if d == "2" else hx0 - 1), ht
        put(img, x, y - 1, GOLD[1]); put(img, x, y + 1, GOLD[1])
        for i in range(1, length + 1):
            put(img, x + step * i, y - i // 2, mat[0])
            put(img, x + step * i, y - i // 2 + 1, mat[2] if i < length else None)
    return img


def shield(d, f, name):
    img = blank()
    m = material(name)
    wooden = m in ("Wooden", "Oak")
    face, emblem = SHIELD_FACES.get(name, (MATERIALS.get(m, MATERIALS["Iron"])[1], GOLD[1]))
    rim = MATERIALS["Iron"] if m == "Wooden" else GOLD if m == "Oak" else MATERIALS.get(m, MATERIALS["Iron"])
    if d in ("2", "8"):                       # side on: the edge of the shield on the far arm, behind the body
        x = CX - 6 if d == "2" else CX + 5
        for y in range(13, 22):
            put(img, x, y, rim[1] if 14 < y < 21 else rim[2])
        return img
    hx0, hx1, ht, hb = shield_hand(d, f)
    cx, cy, r = (hx0 + hx1) / 2.0 + (1 if d == "4" else -1), ht - 2, 4.6
    for y in range(32):
        for x in range(32):
            dd = ((x + 0.5 - cx) ** 2 + (y + 0.5 - cy) ** 2) ** 0.5
            if dd <= r:
                if d == "1":                  # from behind: the back of the shield
                    c = rim[2] if dd > r - 1 else (MATERIALS["Oak"][2] if wooden else (60, 50, 40))
                elif dd > r - 1:
                    c = rim[1] if x + y < cx + cy else rim[2]
                elif wooden:
                    c = MATERIALS[m][(int(x) // 2) % 3]
                else:
                    c = face
                    if abs(x + 0.5 - cx) < 1 or abs(y + 0.5 - cy) < 1:
                        c = emblem            # the cross
                img[y][x] = c
    return img


def worn_frames(name, slot):
    k = kind(name, slot)
    m = material(name)
    if slot == "Ring" or k is None:
        return None
    mat = MATERIALS.get(m, MATERIALS["Iron"])
    frames = {}
    for d in "1248":
        for f in "abc":
            if slot == "Body":
                im = body(d, f, mat, k == "Platebody")
            elif slot == "Legs":
                im = legs(d, f, mat)
            elif slot == "Feet":
                im = feet(d, f, mat)
            elif slot == "Hands":
                im = gloves(d, f, mat)
            elif slot == "Head":
                im = headgear(d, f, mat if k != "Hat" else MATERIALS["Chefs"], k)
            elif slot == "Weapon":
                im = weapon(d, f, mat, k, name)
            elif slot == "Shield":
                im = shield(d, f, name)
            else:
                return None
            frames[d + f] = im
    return frames


def items():
    ini = Ini(p("Data", "Entities.ini"))
    out = []
    for name, _ in ini.sections:
        slot = (ini.get(name, "Slot") or "").strip()
        if slot:
            out.append((name, slot))
    return out


def player_frame(d, f):
    g = BP.draw(d, f)
    return [[BP.C[c] if c else None for c in row] for row in g]


def layered(base, *overs):
    img = [list(r) for r in base]
    for o in overs:
        for y in range(32):
            for x in range(32):
                if o[y][x]:
                    img[y][x] = o[y][x]
    return img


ORDER = ["Legs", "Feet", "Body", "Hands", "Head", "Shield", "Weapon"]   # the game draws them in this order too


def main():
    os.makedirs(p("Sprites", OUT), exist_ok=True)
    made, wanted, written, skipped = {}, set(), 0, []
    for name, slot in items():
        fr = worn_frames(name, slot)
        if fr is None:
            skipped.append(name)
            continue
        made[name] = (slot, fr)
        for key, im in fr.items():
            wanted.add("Worn_%s%s" % (name, key))
            if K.save(OUT, "Worn_%s%s" % (name, key), im):
                written += 1
    stale = [f for f in os.listdir(p("Sprites", OUT)) if f.lower().endswith(".png") and f[:-4] not in wanted]
    for f in stale:
        os.remove(p("Sprites", OUT, f))
    print("%d items shown (%d frames, %d written, %d stale removed); not shown: %s"
          % (len(made), len(wanted), written, len(stale), ", ".join(skipped)))
    if "--preview" in sys.argv:
        outfits = [[], ["Leather_Cap", "Leather_Body", "Leather_Legs", "Leather_Boots", "Leather_Gloves", "Copper_Dagger"],
                   ["Bronze_Helm", "Bronze_Platebody", "Bronze_Platelegs", "Bronze_Sword", "Bronze_Shield"],
                   ["Iron_Helm", "Iron_Platebody", "Iron_Platelegs", "Iron_Boots", "Iron_Gauntlets", "Iron_Sword", "Iron_Shield"],
                   ["Steel_Helm", "Steel_Platebody", "Steel_Platelegs", "Steel_Boots", "Steel_Gauntlets", "Steel_Sword", "Steel_Shield"],
                   ["Mithril_Helm", "Mithril_Platebody", "Mithril_Platelegs", "Mithril_Boots", "Mithril_Gauntlets", "Mithril_Sword", "Mithril_Shield"],
                   ["Silver_Tiara", "Leather_Body", "Yew_Staff", "Oak_Shield"], ["Chefs_Hat", "Willow_Staff", "Wooden_Shield"]]
        sheet = []
        for outfit in outfits:
            for d in "4128":
                for f in "ab":
                    overs = [made[n][1][d + f] for slot in ORDER for n in outfit if n in made and made[n][0] == slot]
                    sheet.append(layered(player_frame(d, f), *overs))
        K.sheet(p("Dev", "Renders", "Worn preview.png"), sheet, scale=3, cols=8)
        print("preview: Dev\\Renders\\Worn preview.png (one row per outfit: S N E W, standing and stepping)")


if __name__ == "__main__":
    main()
