"""A Portrait of Mo (PortraitQuest, a side quest once you're on the mainland): Ottilie (Painter, Id=Ashford_Painter)
paints at her easel in Ashford's market square (3,4,0), and the painting wants a cat: Mo, who never keeps still.
Stroke Mo while Mo is sitting (>Entity.State CLICKED Sit) and Mo settles (Set.NPC.State: held sitting) for the
painting; any other time it comes to nothing, each its own way (mid-stretch; showing you its back end; on the move).
Ottilie paints, Mo is let go, and you get a little painting of Mo (Portrait_of_Mo) and some gold.
Run it again to draw the easel and the painting again; the rest is only done once (the scripts are written again).

  python -I "dev\\migrate\\build_portrait.py"
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame  # noqa: E402
from dragonsword import ini  # noqa: E402
from build_isle import Map, DATA, obj_line  # noqa: E402

QUEST = "A Portrait of Mo"
PAINTER = (3, 14)                   # (3,4,0: on the paving at the edge of Mo's wandering ground)
EASEL = (4, 14)
OUTLINE = (34, 30, 30)
WOOD = ((176, 128, 78), (138, 96, 54), (96, 64, 34))
CAT_BLACK, CAT_WHITE = (40, 36, 42), (240, 240, 244)


def outlined(s):
    shape = pygame.mask.from_surface(s, 100)
    out = pygame.Surface(s.get_size(), pygame.SRCALPHA)
    sil = shape.to_surface(setcolor=OUTLINE + (255,), unsetcolor=(0, 0, 0, 0))
    for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        out.blit(sil, (dx, dy))
    out.blit(s, (0, 0))
    return out


def mo(s, x, y):
    """Mo's face, small: black, ears up, a white muzzle and gold eyes."""
    pygame.draw.polygon(s, CAT_BLACK, [(x - 4, y - 1), (x - 3, y - 5), (x - 1, y - 2)])
    pygame.draw.polygon(s, CAT_BLACK, [(x + 1, y - 2), (x + 3, y - 5), (x + 4, y - 1)])
    pygame.draw.circle(s, CAT_BLACK, (x, y), 4)
    pygame.draw.ellipse(s, CAT_WHITE, (x - 2, y + 1, 5, 3))
    s.set_at((x - 2, y - 1), (230, 190, 60))
    s.set_at((x + 2, y - 1), (230, 190, 60))
    s.set_at((x, y + 1), (236, 128, 146))


def draw_easel():
    """A wooden easel on three legs, a canvas on it with the market and a cat roughed in."""
    s = pygame.Surface((32, 32), pygame.SRCALPHA)
    pygame.draw.line(s, WOOD[2], (16, 4), (16, 29), 2)                         # (the back leg)
    pygame.draw.line(s, WOOD[1], (16, 4), (8, 30), 2)
    pygame.draw.line(s, WOOD[1], (16, 4), (24, 30), 2)
    pygame.draw.line(s, WOOD[0], (9, 22), (23, 22), 2)                         # (the ledge)
    pygame.draw.rect(s, (238, 232, 214), (8, 6, 16, 15))                       # the canvas
    pygame.draw.rect(s, (150, 180, 210), (9, 7, 14, 6))                        # (a sky)
    pygame.draw.rect(s, (170, 150, 120), (9, 13, 14, 7))                       # (the square)
    mo(s, 16, 15)
    return outlined(s)


def draw_portrait():
    """The finished painting, small enough to carry: Mo, sitting like a loaf, in a gilt frame."""
    s = pygame.Surface((32, 32), pygame.SRCALPHA)
    pygame.draw.rect(s, (200, 160, 50), (5, 6, 22, 20))                        # the frame
    pygame.draw.rect(s, (150, 112, 30), (5, 6, 22, 20), 1)
    pygame.draw.rect(s, (70, 90, 120), (8, 9, 16, 14))                         # (a dusk sky)
    pygame.draw.rect(s, (110, 90, 70), (8, 18, 16, 5))
    pygame.draw.ellipse(s, CAT_BLACK, (11, 15, 10, 7))                         # (the loaf)
    pygame.draw.ellipse(s, CAT_WHITE, (14, 18, 4, 3))
    mo(s, 16, 14)
    return outlined(s)


def pictures():
    pygame.init()
    pygame.display.set_mode((1, 1))
    pygame.image.save(draw_easel(), os.path.join(ROOT, "sprites", "Entities", "Easel.png"))
    pygame.image.save(draw_portrait(), os.path.join(ROOT, "sprites", "Entities", "Portrait_of_Mo.png"))
    print("Drew the easel and the portrait")


def data():
    ents = os.path.join(DATA, "Entities.ini")
    for name, keys in (
            ("Painter", (("Type", "NPC"), ("Use.Words", "Talk to"), ("Examine.Info", "A painter with paint on "
                         "everything but the canvas."), ("Roam.Radius", "0"), ("Chase.Radius", "0"),
                         ("Attitude", "Good"), ("Respawn", "300"))),
            ("Easel", (("Type", "StaticObject"), ("Use.Words", "Examine"), ("Examine.Info", "Ashford's market, "
                       "painted in quick strokes. There's a cat-shaped gap in the middle."),
                       ("Walkable.Data", "1111111" * 2 + "1100011" * 5))),
            ("Portrait_of_Mo", (("Type", "MapItem"), ("Use.Words", "Examine"), ("Examine.Info", "A little oil "
                                "painting of Mo, sitting like a loaf in Ashford's market."), ("Value", "40")))):
        if not ini.section(name, ents):
            for k, v in keys:
                ini.write(name, k, v, ents)
    quests = os.path.join(DATA, "Quests.ini")
    if not ini.section(QUEST, quests):
        for k, v in (("Giver", "Painter"), ("Attribute", "PortraitQuest"),
                     ("Stage0", "A painter at an easel in Ashford's market square looks fed up."),
                     ("Stage1", "Get Mo, the black-and-white cat in Ashford's market square, to keep still for "
                                "Ottilie's painting: stroke Mo while Mo is sitting down."),
                     ("Stage2", "Mo is sitting still at last. Tell Ottilie."),
                     ("Done", "3"), ("Marker0", "Ashford_Painter"), ("Marker1", "Mo"), ("Marker2", "Ashford_Painter"),
                     ("Type", "Side"), ("Requires.Quests", "Passage to the Mainland")):
            ini.write(QUEST, k, v, quests)
    m = Map("3,4,0")
    if not m.has_line("Id=Ashford_Painter"):
        m.ents.append(obj_line("NPC", "Painter", PAINTER[0], PAINTER[1],
                               "Attitude=Good Stand=1 Face=E Id=Ashford_Painter Name=Ottilie", -8))
        m.ents.append(obj_line("StaticObject", "Easel", EASEL[0], EASEL[1]))
        m.save()
    print("Ottilie and her easel in Ashford's market square; the quest; the painting")


def write(name, lines):
    with open(os.path.join(DATA, "Scripts", name + ".txt"), "w", encoding="cp1252", newline="\r\n") as f:
        f.write("// Generated by dev\\migrate\\build_portrait.py\n" + "\n".join(lines) + "\n")


def scripts():
    write("Talk to Ashford_Painter", [
        "01\tGet.Value\tATTRIBUTE\tPortraitQuest\tVariable.1$",
        "02\t>Conditional\t$Variable.1=0\t08",
        "03\tDisplay.Conversation\tPainter\tI'm painting the market, and it wants a cat: that black one with the white "
        "socks, Mo. But Mo won't keep still for a moment!\\Stroke Mo while Mo's sitting down, and Mo will settle for "
        "me. Any other time and Mo's off. Will you try?\tI'll try.\t04\tNot now.\t07",
        "04\tUpdate.Attribute\tPortraitQuest\t=1",
        "05\tDisplay.Message\tYellow\tQuest started: %s. (H: your journal)\tQuest" % QUEST,
        "06\tEnd",
        "07\tEnd",
        "08\t>Conditional\t$Variable.1=1\t11",
        "09\tDisplay.Conversation\tPainter\tNo luck yet? Wait till Mo sits, then stroke Mo. Not mid-stretch. And "
        "not... well. Not that end.\tI'll keep at it.\t10",
        "10\tEnd",
        "11\t>Conditional\t$Variable.1=2\t19",
        "12\tDisplay.Conversation\tPainter\tLook at that: sitting like a loaf! Don't move, puss...\\(The brush flicks "
        "and dabs. The market comes and goes around you.)\\There! Have this one. I'll paint another for myself.\t"
        "Thank you!\t13",
        "13\tSet.NPC.State\tMo\t-",
        "14\tGive.Item\tPortrait_of_Mo\t1",
        "15\tGive.Item\tGold_Coin(s)\t25",
        "16\tUpdate.Attribute\tPortraitQuest\t=3",
        "17\tDisplay.Message\tYellow\tQuest done: %s.\tQuest" % QUEST,
        "18\tEnd",
        "19\tDisplay.Conversation\tPainter\tFolk keep asking who the cat in my painting is. I tell them: the "
        "market's real owner.\tGoodbye.\t20",
        "20\tEnd"])
    write("Stroke Mo", [
        "01\tGet.Value\tATTRIBUTE\tPortraitQuest\tVariable.1$",
        "02\t>Conditional\t$Variable.1=1\t18",
        "03\t>Distance.From.Clicked.Entity\t40\t21",
        "04\t>Entity.State\tCLICKED\tSit\t10",
        "05\tSet.NPC.State\tCLICKED\tSit",
        "06\tPlay.Sound\tPurr",
        "07\tUpdate.Attribute\tPortraitQuest\t=2",
        "08\tDisplay.Message\tCyan\tMo settles under your hand, purring, and stays put. Ottilie reaches for a brush.",
        "09\tEnd",
        "10\t>Entity.State\tCLICKED\tButt\t13",
        "11\tDisplay.Message\tDarkRed\tYou reach for Mo and get a close view of Mo's back end. At the easel, Ottilie "
        "snorts with laughter.\tFail",
        "12\tEnd",
        "13\t>Entity.State\tCLICKED\tStretch\t16",
        "14\tDisplay.Message\tDarkRed\tMo is mid-stretch, long as a draught excluder, and won't be hurried.\tFail",
        "15\tEnd",
        "16\tDisplay.Message\tDarkRed\tMo slips out from under your hand and trots off.\tFail",
        "17\tEnd",
        "18\tPlay.Sound\tPurr",
        "19\tDisplay.Message\tCyan\tMo kneads the air with a white paw and purrs.",
        "20\tEnd",
        "21\tDisplay.Message\tDarkRed\tYou are too far away!\tDenied",
        "22\tEnd"])
    print("Scripts: Talk to Ashford_Painter, Stroke Mo")


def main():
    pictures()
    data()
    scripts()


if __name__ == "__main__":
    main()
