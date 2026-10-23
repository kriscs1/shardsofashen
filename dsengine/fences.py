"""Wooden fences that join up: each fence square shows the piece that meets its neighbours (a corner, a T, a crossing,
a straight run, a post on its own) from the twelve Wood_Fence pieces (Tiles.ini says what each one is)."""

FENCE = "Wood_Fence"
OLD = ("Fence001", "Fence002")            # (the plain rails and posts fences were once built of: they join up too)
N, E, S, W = (0, -1), (1, 0), (0, 1), (-1, 0)
PIECES = {
    frozenset(): "012",
    frozenset("EW"): "001", frozenset("E"): "001", frozenset("W"): "001",
    frozenset("NS"): "002", frozenset("N"): "002", frozenset("S"): "002",
    frozenset("ES"): "003", frozenset("WS"): "004", frozenset("NE"): "005", frozenset("NW"): "006",
    frozenset("ESW"): "007", frozenset("NEW"): "008", frozenset("NES"): "009", frozenset("NSW"): "010",
    frozenset("NESW"): "011",
}


def is_fence(name):
    return bool(name) and (name.startswith(FENCE) or name in OLD)


def fence_piece(fence_at, x, y):
    """The Wood_Fence piece for x,y, from which of its four neighbours are fences (fence_at(x, y) -> bool)."""
    joins = frozenset(k for k, (dx, dy) in zip("NESW", (N, E, S, W)) if fence_at(x + dx, y + dy))
    return FENCE + PIECES[joins]


def join_around(fence_at, x, y):
    """[(x, y, piece)] for x,y and its neighbours that are fences, each as it should be now."""
    out = []
    for dx, dy in ((0, 0), N, E, S, W):
        if fence_at(x + dx, y + dy):
            out.append((x + dx, y + dy, fence_piece(fence_at, x + dx, y + dy)))
    return out
