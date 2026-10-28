"""The notice (sprites\\Entities\\Notice.png): a wooden board on two posts with a cream sheet pinned to it, NOTICE
across the top in letters you can read (3 x 5, dark ink) and a few lines of writing under it.
Safe to run again.

  python -I "dev\\migrate\\build_notice.py"
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sprite_kit as K                       # noqa: E402

FONT = {   # capitals 5 tall (an N needs 4 across, or it's an M)
    "N": ["X..X", "XX.X", "X.XX", "X..X", "X..X"],
    "O": ["XXX", "X.X", "X.X", "X.X", "XXX"],
    "T": ["XXX", ".X.", ".X.", ".X.", ".X."],
    "I": ["XXX", ".X.", ".X.", ".X.", "XXX"],
    "C": ["XXX", "X..", "X..", "X..", "XXX"],
    "E": ["XXX", "X..", "XX.", "X..", "XXX"],
}
WOOD, WOOD_DARK, WOOD_LIGHT = (128, 86, 48), (88, 58, 32), (156, 110, 64)
PAPER, PAPER_SHADE, INK, PIN = (238, 226, 192), (214, 198, 158), (54, 36, 24), (186, 48, 40)


def notice():
    img = K.new()
    for x in (5, 25):                                             # (the posts)
        for y in range(18, 31):
            K.put(img, x, y, WOOD_DARK)
            K.put(img, x + 1, y, WOOD)
    for y in range(4, 21):                                        # (the board)
        for x in range(2, 30):
            edge = y in (4, 20) or x in (2, 29)
            K.put(img, x, y, WOOD_DARK if edge else WOOD_LIGHT if (y - 4) % 6 == 1 else WOOD)
    for y in range(6, 19):                                        # (the sheet pinned to it)
        for x in range(3, 29):
            K.put(img, x, y, PAPER_SHADE if (y == 18 or x == 28) else PAPER)
    x = 4
    for ch in "NOTICE":
        for j, row in enumerate(FONT[ch]):
            for i, c in enumerate(row):
                if c == "X":
                    K.put(img, x + i, 8 + j, INK)
        x += len(FONT[ch][0]) + 1
    for y, (a, b) in ((14, (7, 24)), (16, (7, 20))):              # (lines of writing)
        for xx in range(a, b + 1):
            if (xx * 7 + y) % 5:
                K.put(img, xx, y, (120, 100, 78))
    for px in (3, 27):                                            # (pins)
        K.put(img, px, 6, PIN)
    return K.outline_img(img, (40, 26, 16))


def main():
    print("Notice: %s" % ("written" if K.save("Entities", "Notice", notice()) else "unchanged"))


if __name__ == "__main__":
    main()
