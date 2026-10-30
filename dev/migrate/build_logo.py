"""The game's logo in its own look: pixel art like everything else, drawn here (no font from anywhere else).
"SHARDS" in gold over "ASHEN" in ember, "of" between them on a rule, a violet Shard crystal either side, a dark
outline and a drop shadow, all on the game's 1 px grid and scaled up square (crisp at any size the page shows it).

Writes web/img/logo.png (the game's login screen) and web/home/logo.png (the start screen, every version).

  python -I "dev\\migrate\\build_logo.py" [--preview]
"""
import os
import sys

import pygame

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCALE = 4                       # (each logo pixel is 4 x 4 on the picture)

# The letters, 7 wide and 8 tall, bold enough to read small ("#" is ink)
BIG = {
    "S": [".#####.", "##...##", "##.....", ".#####.", ".....##", ".....##", "##...##", ".#####."],
    "H": ["##...##", "##...##", "##...##", "#######", "##...##", "##...##", "##...##", "##...##"],
    "A": ["..###..", ".##.##.", "##...##", "##...##", "#######", "##...##", "##...##", "##...##"],
    "R": ["######.", "##...##", "##...##", "######.", "##.##..", "##..##.", "##...##", "##...##"],
    "D": ["#####..", "##..##.", "##...##", "##...##", "##...##", "##...##", "##..##.", "#####.."],
    "E": ["#######", "##.....", "##.....", "#####..", "##.....", "##.....", "##.....", "#######"],
    "N": ["##...##", "###..##", "####.##", "##.####", "##..###", "##...##", "##...##", "##...##"],
}
SMALL = {"o": ["....", ".##.", "#..#", "#..#", ".##."], "f": [".##", "#..", "###", "#..", "#.."]}

GOLD = [(255, 247, 205), (255, 232, 150), (243, 205, 96), (222, 170, 62), (184, 118, 38), (214, 150, 52),
        (240, 192, 96), (246, 208, 118)]
EMBER = [(255, 236, 160), (255, 196, 92), (255, 146, 48), (240, 104, 32), (200, 64, 26), (170, 40, 22),
         (196, 58, 26), (226, 86, 34)]
OUTLINE = (34, 16, 10)
SHADOW = (12, 6, 4)
SHARD = [(244, 234, 255), (196, 160, 255), (150, 104, 240), (98, 58, 186), (64, 34, 128)]


def word(text, glyphs, gap=1, zoom=2):
    """A word's pixels: [(x, y, row-of-its-letter)] at zoom (2: each letter pixel 2 x 2, so the shading has room)."""
    out, x = [], 0
    for ch in text:
        rows = glyphs[ch]
        for gy, row in enumerate(rows):
            for gx, c in enumerate(row):
                if c == "#":
                    for dy in range(zoom):
                        for dx in range(zoom):
                            out.append((x + gx * zoom + dx, gy * zoom + dy, gy * zoom + dy))
        x += (len(rows[0]) + gap) * zoom
    return out, x - gap * zoom, len(glyphs[text[0]]) * zoom


def shard(surface, cx, top, h):
    """A Shard crystal: a long six-sided gem, lit from the top left, a bright line down it."""
    w = max(3, h // 3)
    for y in range(h):
        t = y / max(1, h - 1)
        half = int(w * (t * 2 if t < 0.25 else 1 - (t - 0.25) / 0.75 * 0.6) + 0.5) if t < 1 else 1
        half = max(1, half if t >= 0.25 else int(w * t * 4 + 0.5))
        for x in range(-half, half + 1):
            k = min(len(SHARD) - 1, int((x + half) / (2 * half + 1) * 3 + t * 2))
            surface.set_at((cx + x, top + y), SHARD[k])
        surface.set_at((cx - half // 2, top + y), SHARD[0] if y % 3 else SHARD[1])


def outlined(base):
    """base with a 1 px dark outline round everything drawn, and a drop shadow one down and one right."""
    w, h = base.get_size()
    out = pygame.Surface((w + 4, h + 4), pygame.SRCALPHA)
    mask = pygame.mask.from_surface(base)
    for dx, dy in ((2, 2), (3, 3), (3, 2), (2, 3)):            # (the shadow)
        for x, y in mask.outline() + [(x, y) for x in range(w) for y in range(h) if mask.get_at((x, y))]:
            out.set_at((x + dx + 1, y + dy + 1), SHADOW)
    for x in range(w):
        for y in range(h):
            if mask.get_at((x, y)):
                for ox in (-1, 0, 1):
                    for oy in (-1, 0, 1):
                        out.set_at((x + 2 + ox, y + 2 + oy), OUTLINE)
    out.blit(base, (2, 2))
    return out


def logo():
    top, tw, th = word("SHARDS", BIG)
    bottom, bw, bh = word("ASHEN", BIG)
    small, sw, sh = word("of", SMALL, gap=1, zoom=1)
    width = max(tw, bw) + 2
    rule_y = th + 3
    height = th + 6 + sh + 6 + bh
    base = pygame.Surface((width, height), pygame.SRCALPHA)
    ox = (width - tw) // 2
    for x, y, r in top:
        base.set_at((ox + x, y), GOLD[min(len(GOLD) - 1, r * len(GOLD) // th)])
    oy, ox = th + 6 + sh + 6, (width - bw) // 2
    for x, y, r in bottom:
        base.set_at((ox + x, oy + y), EMBER[min(len(EMBER) - 1, r * len(EMBER) // bh)])
    # "of" on a gold rule between the words
    sx, sy = (width - sw) // 2, th + 6 + 1
    for x, y, r in small:
        base.set_at((sx + x, sy + y), GOLD[2])
    for x in range(6, width - 6):
        if not (sx - 3 <= x <= sx + sw + 2):
            base.set_at((x, sy + sh // 2), GOLD[3] if x % 4 else GOLD[1])
    out = outlined(base)
    full = pygame.Surface((out.get_width() + 24, out.get_height()), pygame.SRCALPHA)
    full.blit(out, (12, 0))
    mid = sy + sh // 2 + 2
    shard(full, 6, mid - 9, 18)                                  # (a Shard either side, as the rule's ends)
    shard(full, full.get_width() - 7, mid - 9, 18)
    return pygame.transform.scale(full, (full.get_width() * SCALE, full.get_height() * SCALE))


def main():
    pygame.init()
    img = logo()
    for path in (os.path.join(ROOT, "web", "img", "logo.png"), os.path.join(ROOT, "web", "home", "logo.png")):
        pygame.image.save(img, path)
        print("wrote %s (%d x %d)" % (os.path.relpath(path, ROOT), img.get_width(), img.get_height()))
    if "--preview" in sys.argv:
        bg = pygame.Surface((img.get_width() + 40, img.get_height() + 40))
        bg.fill((51, 34, 27))
        bg.blit(img, (20, 20))
        pygame.image.save(bg, os.path.join(ROOT, "dev", "Renders", "Logo preview.png"))


if __name__ == "__main__":
    main()
