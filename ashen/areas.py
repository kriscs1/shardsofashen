"""Areas of tiles on a map line: an NPC's Zone=, Chase= or Home= is a rectangle "x1,y1,x2,y2" (1-based tiles of its
map; past its edges, the maps round it), or several joined by / for any shape (an L, a house's rooms). The map editor
paints them tile by tile and the migrations work them out; both write them with rects_text."""


def parse(text):
    """"x1,y1,x2,y2/..." -> [(x1, y1, x2, y2)] (each with x1<=x2, y1<=y2), or None if any part isn't one."""
    out = []
    for part in (text or "").split("/"):
        try:
            r = tuple(int(float(v)) for v in part.split(","))
        except ValueError:
            return None
        if len(r) != 4:
            return None
        out.append((min(r[0], r[2]), min(r[1], r[3]), max(r[0], r[2]), max(r[1], r[3])))
    return out or None


def tiles_of(rects):
    return {(x, y) for x1, y1, x2, y2 in rects for x in range(x1, x2 + 1) for y in range(y1, y2 + 1)}


def rects_text(tiles):
    """Tiles (x, y) as few rectangles as rows allow: each row's runs, the same runs in the rows under them merged into
    one - "x1,y1,x2,y2/..."."""
    runs = {}
    for y in sorted({t[1] for t in tiles}):
        xs = sorted(x for x, yy in tiles if yy == y)
        start = prev = xs[0]
        for x in xs[1:] + [None]:
            if x is not None and x == prev + 1:
                prev = x
                continue
            runs.setdefault((start, prev), []).append(y)
            start = prev = x
    rects = []
    for (x1, x2), ys in runs.items():
        y0 = ys[0]
        for a, b in zip(ys, ys[1:] + [None]):
            if b != a + 1:
                rects.append((x1, y0, x2, a))
                y0 = b
    rects.sort(key=lambda r: (r[1], r[0]))
    return "/".join("%d,%d,%d,%d" % r for r in rects)
