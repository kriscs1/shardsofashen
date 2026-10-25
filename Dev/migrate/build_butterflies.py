"""Butterflies that flap their wings: an orange one (Butterfly) and a blue one (Blue_Butterfly), drawn here small,
seen from above - wings open (a), half closed (b), all but shut (c). Flap=1 in Entities.ini: the browser runs
through the frames on a timer, so they flutter even while they hover (Dev\\migrate\\small_butterflies.py made the
old ones smaller; this draws them afresh). Run it again to draw them again; the blue ones are only placed once.

  python -I "Dev\\migrate\\build_butterflies.py"

  * Sprites\\Walk\\<Kind>2a-c / 8a-c, Sprites\\Entities\\<Kind>.png.
  * Entities.ini: Flap=1 on both; [Blue_Butterfly] as the Butterfly, in blue.
  * Maps: every other butterfly on a map with two or more, and one in three of the rest, is blue.
"""
import glob
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame  # noqa: E402
from dragonsword import ini  # noqa: E402
from build_isle import DATA, Map  # noqa: E402

OUTLINE = (30, 22, 18)
BODY = (44, 32, 26)
# wing, its darker edge, its spots
KINDS = {
    "Butterfly": ((240, 140, 40), (178, 84, 22), (255, 226, 150)),
    "Blue_Butterfly": ((70, 150, 240), (30, 80, 170), (190, 230, 255)),
}
SPREAD = (6, 4, 2)               # the wings' width out from the body in frames a, b, c: open, half, all but shut
CX, CY = 16, 16                  # (where the old ones were: the middle of the tile)


def draw(wing, edge, spot, frame):
    """One side drawn, the other its mirror: the two always match."""
    w = SPREAD[frame]
    half = pygame.Surface((16, 32), pygame.SRCALPHA)              # (the right half; x 0 is the body's middle)
    pygame.draw.ellipse(half, edge, (1, CY - 5, w, 6))              # the forewing, edged darker
    pygame.draw.ellipse(half, edge, (1, CY, max(1, w - 1), 5))      # the hindwing
    if w > 2:
        pygame.draw.ellipse(half, wing, (1, CY - 4, w - 1, 4))
        pygame.draw.ellipse(half, wing, (1, CY + 1, max(1, w - 2), 3))
    if w >= 6:
        half.set_at((4, CY - 3), spot)                              # (spots, while the wings are open)
        half.set_at((3, CY + 2), spot)
    pygame.draw.line(half, BODY, (0, CY - 4), (0, CY + 3))          # the body
    half.set_at((1, CY - 6), BODY)                                  # (a feeler)
    s = pygame.Surface((32, 32), pygame.SRCALPHA)
    s.blit(half, (CX, 0))
    s.blit(pygame.transform.flip(half, True, False), (CX - 15, 0))
    out = pygame.Surface((32, 32), pygame.SRCALPHA)
    sil = pygame.mask.from_surface(s).to_surface(setcolor=OUTLINE + (255,), unsetcolor=(0, 0, 0, 0))
    for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        out.blit(sil, (dx, dy))
    out.blit(s, (0, 0))
    return out


def pictures():
    pygame.init()
    pygame.display.set_mode((1, 1))
    walk, ents = os.path.join(ROOT, "Sprites", "Walk"), os.path.join(ROOT, "Sprites", "Entities")
    for name, pal in KINDS.items():
        frames = [draw(*pal, frame=i) for i in range(3)]
        for f, img in zip("abc", frames):
            pygame.image.save(img, os.path.join(walk, "%s2%s.png" % (name, f)))
            pygame.image.save(pygame.transform.flip(img, True, False), os.path.join(walk, "%s8%s.png" % (name, f)))
        pygame.image.save(frames[0], os.path.join(ents, name + ".png"))
    print("Drew the butterflies: %s" % ", ".join(KINDS))


def data():
    ents = os.path.join(DATA, "Entities.ini")
    ini.write("Butterfly", "Flap", "1", ents)
    if not ini.section("Blue_Butterfly", ents):
        for k in ("Type", "Use.Words", "Examine.Info", "Movement.Speed", "Roam.Radius", "Chase.Radius", "Walk.Speed",
                  "Pause", "Solid", "Layer", "Attitude", "Schedule", "Flap"):
            v = ini.read("Butterfly", k, "", ents)
            if k == "Examine.Info":
                v = "A butterfly with bright blue wings."
            if v != "":
                ini.write("Blue_Butterfly", k, v, ents)


def place():
    n = 0
    for path in glob.glob(os.path.join(ROOT, "Maps", "*.txt")):
        name = os.path.splitext(os.path.basename(path))[0]
        if name.count(",") != 2:
            continue
        text = open(path, "rb").read().decode("cp1252")
        if "NPC\tButterfly\t" not in text or "NPC\tBlue_Butterfly\t" in text:
            continue
        m = Map(name)
        mine = [i for i, ln in enumerate(m.ents) if ln.startswith("NPC\tButterfly\t")]
        turn = mine[1::2] if len(mine) > 1 else (mine if sum(map(ord, name)) % 3 == 0 else [])
        for i in turn:
            m.ents[i] = m.ents[i].replace("NPC\tButterfly\t", "NPC\tBlue_Butterfly\t", 1)
            n += 1
        if turn:
            m.save()
    print("Blue butterflies placed: %d" % n)


if __name__ == "__main__":
    pictures()
    data()
    place()
