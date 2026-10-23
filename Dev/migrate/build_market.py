"""The market and the shop signs. Run it again after rebuilding the world: it makes what's missing.

  python -I "Dev\\migrate\\build_market.py"

  * Market stalls (the server's dsengine/market.py): a row of them by the south road in Ashford (Id=Stall_1...). A
    player claims one, stocks it from their pack at their own prices, and other players buy from it, even while the
    owner is away; the takings wait in the stall for its owner. Sprites\\Entities\\Market_Stall (empty) and
    Market_Stall_Open (with goods out), and a Market sign.
  * Shop signs: every shop gets a signboard on a post outside its door, with a picture of what it sells (the bread
    for the bakery, the anvil for the smithy...). Sprites\\Entities\\Sign_<Kind>.
"""
import glob
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame  # noqa: E402

from dragonsword import ini  # noqa: E402

DATA = os.path.join(ROOT, "Data")
ENTS = os.path.join(ROOT, "Sprites", "Entities")
XT, YT = 25, 21
MARKET_MAP, MARKET_ROW, STALLS = "2,3,0", 20, 6

# shopkeeper (or Id) -> sign: (sprite name, what the shop is, the item on the board, what the examine text adds)
SIGNS = {
    "Baker": ("Sign_Bakery", "The Bakery", "Bread", "bread, pies and flour"),
    "Blacksmith": ("Sign_Smithy", "The Smithy", "Anvil", "tools, weapons and armour; repairs"),
    "Dwarf": ("Sign_Dwarf", "Dwarven Wares", "Pickaxe", "picks and fine metalwork"),
    "Farmer": ("Sign_Farm", "Farm Shop", "Cabbage", "seeds, vegetables, eggs and wheat"),
    "Fisherman": ("Sign_Fishing", "Fishing Supplies", "Fishing_Rod", "rods, bait and fish"),
    "Herbalist": ("Sign_Herbalist", "The Herbalist", "Basic_Potion", "potions and herbs"),
    "Milkmaid": ("Sign_Dairy", "The Dairy", "Bucket_of_Milk", "milk, cheese and eggs"),
    "Quartermaster": ("Sign_Armoury", "Quartermaster", "Iron_Shield", "the King's arms and armour"),
    "Shopkeeper": ("Sign_General", "General Store", "Gold_Coin(s)", "a bit of everything"),
    "Trader": ("Sign_General", "General Store", "Gold_Coin(s)", "a bit of everything"),
    "Wizard": ("Sign_Magic", "Magic Shop", "Fire_Bolt_Scroll", "scrolls and staves"),
    "Homestead_Settler": ("Sign_Builder", "Homestead Supplies", "Plank", "building materials and homestead scrolls"),
}
MARKET_SIGN = ("Sign_Market", "The Market", "Market_Stall_Open", "players' stalls: claim an empty one to sell your things")


# ---------------------------------------------------------------- sprites
def save(img, name):
    path = os.path.join(ENTS, name + ".png")
    if os.path.exists(path):
        return False
    pygame.image.save(img, path)
    print("Made Sprites\\Entities\\%s.png" % name)
    return True


def stall(goods):
    """A market stall, 32 x 48: two posts, a striped awning, a counter (with goods out on it, or bare)."""
    s = pygame.Surface((32, 48), pygame.SRCALPHA)
    wood, dark = (138, 94, 54), (84, 56, 32)
    for x in (3, 27):
        pygame.draw.rect(s, wood, (x, 12, 3, 34))
        pygame.draw.rect(s, dark, (x, 12, 3, 34), 1)
    for i in range(6):                                          # the awning: red and cream stripes
        col = (196, 52, 44) if i % 2 == 0 else (238, 226, 196)
        pygame.draw.polygon(s, col, [(1 + i * 5, 4), (6 + i * 5, 4), (7 + i * 5, 14), (1 + i * 5, 14)])
    pygame.draw.rect(s, (120, 30, 26), (0, 3, 32, 2))
    for i in range(6):                                          # its scalloped edge
        pygame.draw.circle(s, (196, 52, 44) if i % 2 == 0 else (238, 226, 196), (3 + i * 5, 14), 3)
    pygame.draw.rect(s, (160, 112, 66), (1, 30, 30, 8))         # the counter
    pygame.draw.rect(s, dark, (1, 30, 30, 8), 1)
    pygame.draw.rect(s, (120, 82, 48), (2, 38, 28, 8))
    pygame.draw.line(s, dark, (2, 42), (29, 42))
    if goods:
        for x, col in ((5, (214, 60, 50)), (11, (240, 190, 60)), (17, (110, 170, 70)), (23, (200, 140, 80))):
            pygame.draw.circle(s, col, (x + 2, 28), 3)
            pygame.draw.circle(s, (60, 40, 30), (x + 2, 28), 3, 1)
        pygame.draw.rect(s, (226, 200, 140), (13, 22, 6, 6))       # a little parcel on top
        pygame.draw.rect(s, dark, (13, 22, 6, 6), 1)
    return s


def sign(icon_name):
    """A signboard, 32 x 48: a post, an arm, and a board hanging from it with the shop's picture."""
    s = pygame.Surface((32, 48), pygame.SRCALPHA)
    wood, dark = (122, 84, 50), (70, 46, 28)
    pygame.draw.rect(s, wood, (3, 4, 4, 44))                     # the post
    pygame.draw.rect(s, dark, (3, 4, 4, 44), 1)
    pygame.draw.rect(s, wood, (3, 4, 28, 3))                     # the arm
    pygame.draw.rect(s, dark, (3, 4, 28, 3), 1)
    for x in (12, 26):                                          # the chains
        pygame.draw.line(s, (60, 60, 64), (x, 7), (x, 10))
    board = pygame.Rect(8, 10, 23, 24)
    pygame.draw.rect(s, (236, 216, 168), board)
    pygame.draw.rect(s, (150, 104, 56), board, 2)
    pygame.draw.rect(s, dark, board.inflate(2, 2), 1)
    path = os.path.join(ENTS, icon_name + ".png")
    if os.path.exists(path):
        icon = pygame.image.load(path).convert_alpha() if pygame.display.get_init() and pygame.display.get_surface() \
            else pygame.image.load(path)
        w, h = icon.get_size()
        k = min(19 / w, 19 / h)
        icon = pygame.transform.smoothscale(icon, (max(1, int(w * k)), max(1, int(h * k))))
        s.blit(icon, (board.centerx - icon.get_width() // 2, board.centery - icon.get_height() // 2))
    return s


def make_sprites():
    pygame.init()
    save(stall(False), "Market_Stall")
    save(stall(True), "Market_Stall_Open")
    for name, title, icon, _ in list(SIGNS.values()) + [MARKET_SIGN]:
        save(sign(icon), name)


# ---------------------------------------------------------------- data
def write_section(path, name, values):
    if ini.section(name, path):
        return False
    for k, v in values.items():
        ini.write(name, k, v, path)
    print("Entities.ini [%s]" % name)
    return True


def write_entities():
    path = os.path.join(DATA, "Entities.ini")
    write_section(path, "Market_Stall", {"Type": "StaticObject", "Use.Words": "Browse,Examine",
                                         "Examine.Info": "A market stall. Claim an empty one and sell your things "
                                                         "from it, at your own prices."})
    write_section(path, "Market_Stall_Open", {"Type": "StaticObject", "Use.Words": "Browse,Examine",
                                              "Examine.Info": "A market stall with things for sale."})
    for name, title, icon, sells in list(SIGNS.values()) + [MARKET_SIGN]:
        write_section(path, name, {"Type": "StaticObject", "Use.Words": "Examine",
                                   "Examine.Info": "A sign: %s - %s." % (title, sells)})


# ---------------------------------------------------------------- placing them
TILES_INI = os.path.join(DATA, "Tiles.ini")


def map_lines(name):
    return ini.read_text(os.path.join(ROOT, "Maps", name + ".txt")).replace("\r", "").split("\n")


def write_map(name, lines):
    while lines and lines[-1] == "":
        lines.pop()
    with open(os.path.join(ROOT, "Maps", name + ".txt"), "w", encoding="cp1252", newline="\r\n") as f:
        f.write("\n".join(lines) + "\n")


def cell(lines, x, y):
    return lines[y - 1].split(":")[x - 1].strip() if 1 <= x <= XT and 1 <= y <= YT else ""


def walkable(c):
    t = c.split("+")[0]
    return bool(t) and "0" not in ini.read(t, "Walkable.Data", "1" * 49, TILES_INI)


def clear(lines, x, y, taken):
    """Free ground outdoors: walkable, nothing on it (no decor, no roof), not a door, nothing standing near."""
    if not (2 <= x <= XT - 1 and 2 <= y <= YT - 1):
        return False
    c = cell(lines, x, y)
    if "+" in c or not walkable(c) or c.startswith("Door"):
        return False
    px, py = (x - 1) * 32, (y - 1) * 32
    return all(math.hypot(px - ax, py - ay) > 30 for ax, ay in taken)


def taken_spots(lines):
    out = []
    for ln in lines[YT:]:
        p = ln.split("\t")
        if len(p) >= 4 and p[0] not in ("Lock", "Trigger", "Id"):
            try:
                out.append((float(p[2]), float(p[3]) + (16 if p[1].startswith(("Sign_", "Market_Stall")) else 0)))
            except ValueError:
                pass
    return out


def outside_of(lines, dx, dy):
    """The tile in front of a door: walkable, not under a roof."""
    for x, y in ((dx, dy + 1), (dx, dy - 1), (dx - 1, dy), (dx + 1, dy)):
        c = cell(lines, x, y)
        if c and "Roof(" not in c and walkable(c):
            return x, y
    return None


def sign_spot(lines, npc_x, npc_y, taken):
    """Beside the shop's door (outside it), or near the shopkeeper if there's no door close by."""
    tx, ty = int(npc_x // 32) + 1, int((npc_y + 8) // 32) + 1
    indoors = "Roof(" in cell(lines, tx, ty)               # (a shopkeeper out in the open: the sign goes by them)
    doors = [] if not indoors else sorted((abs(x - tx) + abs(y - ty), x, y) for y in range(1, YT + 1) for x in range(1, XT + 1)
                   if cell(lines, x, y).split("+")[0].startswith("Door") and abs(x - tx) <= 8 and abs(y - ty) <= 8)
    for _, dx, dy in doors[:2]:
        out = outside_of(lines, dx, dy)
        if out is None:
            continue
        ox, oy = out
        side = [(ox - 1, oy), (ox + 1, oy)] if ox == dx else [(ox, oy - 1), (ox, oy + 1)]
        for x, y in side + [(ox - 2, oy), (ox + 2, oy), (ox - 1, oy + 1), (ox + 1, oy + 1)]:
            if clear(lines, x, y, taken):
                return x, y
    best = None
    for y in range(ty - 3, ty + 4):
        for x in range(tx - 3, tx + 4):
            if (x, y) != (tx, ty) and clear(lines, x, y, taken) and "Roof(" not in cell(lines, x, y):
                d = math.hypot(x - tx, y - ty)
                if best is None or d < best[0]:
                    best = (d, x, y)
    return best[1:] if best else None


def place_signs():
    for path in sorted(glob.glob(os.path.join(ROOT, "Maps", "*.txt"))):
        name = os.path.basename(path)[:-4]
        if len(name.split(",")) != 3:
            continue
        lines = map_lines(name)
        changed = False
        for ln in list(lines[YT:]):
            p = ln.split("\t")
            if len(p) < 4 or p[0] != "NPC":
                continue
            key = "Homestead_Settler" if "Id=Homestead_Settler" in (p[4] if len(p) > 4 else "") else p[1]
            if key not in SIGNS:
                continue
            sprite = SIGNS[key][0]
            if any(l.split("\t")[:2] == ["StaticObject", sprite] for l in lines[YT:]):
                continue                                        # (this map has its sign already)
            spot = sign_spot(lines, float(p[2]), float(p[3]), taken_spots(lines))
            if spot is None:
                print("WARNING - no room for the %s sign on %s" % (SIGNS[key][1], name))
                continue
            x, y = spot
            lines.append("StaticObject\t%s\t%d\t%d" % (sprite, (x - 1) * 32, (y - 1) * 32 - 16))
            print("%s: %s sign at tile %d,%d" % (name, SIGNS[key][1], x, y))
            changed = True
        if changed:
            write_map(name, lines)


def place_market():
    lines = map_lines(MARKET_MAP)
    if any(l.split("\t")[:2] == ["StaticObject", "Market_Stall"] for l in lines[YT:]):
        print("Ashford has its market already")
        return
    taken = taken_spots(lines)
    xs = [x for x in range(3, XT - 1) if clear(lines, x, MARKET_ROW, taken)]
    spots = []
    for x in xs:                                                # (a gap between stalls, to walk round them)
        if all(abs(x - s) >= 2 for s in spots) and len(spots) < STALLS + 1:
            spots.append(x)
    if len(spots) < 3:
        print("WARNING - no room for a market in Ashford")
        return
    sign_x, stalls = spots[0], spots[1:]
    lines.append("StaticObject\t%s\t%d\t%d" % (MARKET_SIGN[0], (sign_x - 1) * 32, (MARKET_ROW - 1) * 32 - 16))
    for n, x in enumerate(stalls, 1):
        lines.append("StaticObject\tMarket_Stall\t%d\t%d\tId=Stall_%d" % ((x - 1) * 32, (MARKET_ROW - 1) * 32 - 16, n))
    lines.append("Id\tAshford_Market\t%d\t%d" % (stalls[len(stalls) // 2], MARKET_ROW - 1))
    write_map(MARKET_MAP, lines)
    print("Ashford's market: %d stalls on row %d (tiles %s)" % (len(stalls), MARKET_ROW, ", ".join(map(str, stalls))))


def main():
    make_sprites()
    write_entities()
    place_market()
    place_signs()


if __name__ == "__main__":
    main()
