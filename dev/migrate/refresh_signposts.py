"""The signposts' words worked out again from where the towns are now (Fenwick, Highwatch and Ravensgate gone; the
Keep and Ashford moved): each says which way the nearest four lie (no more), as build_estforlan.py's ways.signposts
first wrote them.

Safe to run again (the words are worked out afresh each time).

  python -I "dev\\migrate\\refresh_signposts.py"
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "estforlan"))
import world_edit as W                                   # noqa: E402
import story_kit as SK                                   # noqa: E402

MAKER = "refresh_signposts.py"
REACH = 260
SKIP = ("Isle Village",)


def compass(dx, dy):
    ns = "north" if dy < -abs(dx) * 0.4 else "south" if dy > abs(dx) * 0.4 else ""
    ew = "west" if dx < -abs(dy) * 0.4 else "east" if dx > abs(dy) * 0.4 else ""
    return (ns + ("-" if ns and ew else "") + ew) or "here"


def towns(w):
    out, sec = [], None
    for ln in W.read(os.path.join(W.ROOT, "data", "WorldMap.ini")).splitlines():
        if ln.startswith("["):
            sec = ln.strip("[]")
        elif sec == "Towns" and "=" in ln and not ln.startswith(";"):
            name, place = (v.strip() for v in ln.split("=", 1))
            if name in SKIP:
                continue
            _, c = w.find_id(place)
            if c is not None:
                out.append((name, c))
    return out


def main():
    w = W.World(0)
    places = towns(w)
    n = 0
    for m, ln, c in w.lines():
        p = ln.split("\t")
        if p[0] != "StaticObject" or p[1] != "Signpost":
            continue
        pid = W.line_id(ln)
        if not pid:
            continue
        ways = sorted((abs(tc[0] - c[0]) + abs(tc[1] - c[1]), name, compass(tc[0] - c[0], tc[1] - c[1]))
                      for name, tc in places if abs(tc[0] - c[0]) + abs(tc[1] - c[1]) < REACH)
        text = "\\".join("%s: %s" % (t, d) for _, t, d in ways[:4]) or "The road goes on."
        SK.write_script("Read " + pid, [
            (">Distance.From.Clicked.Entity", "64", "@far"),
            ("Display.Conversation", "Signpost", text, "Okay", "@end"),
            ("@end",), ("End",),
            ("@far",), ("Display.Message", "DarkRed", "You can't read that from here!", "Denied"), ("End",)], MAKER)
        n += 1
    print("Signposts: %d read again" % n)


if __name__ == "__main__":
    main()
