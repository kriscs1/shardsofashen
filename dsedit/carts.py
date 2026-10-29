"""data\\Carts.ini for the Maps page: each cart's route, its settings and its points (a map's tile at a time; a point
with a name is a stop), read, changed and written back (cp1252, CRLF), its comments kept."""
import os

from .project import parse_map_name


class Route:
    def __init__(self, key):
        self.key = key
        self.keys = []                  # [(key, value)]: Title, Fare, Wait, Loop (and anything else, kept)
        self.points = []                # [[map, x, y, stop name]] (x, y 1-based)

    def get(self, key, default=""):
        return next((v for k, v in self.keys if k.lower() == key.lower()), default)

    def set(self, key, value):
        for i, (k, _) in enumerate(self.keys):
            if k.lower() == key.lower():
                self.keys[i] = (k, value)
                return
        self.keys.append((key, value))

    def level(self):
        return parse_map_name(self.points[0][0])[2] if self.points else None


class CartRoutes:
    def __init__(self, project):
        self.path = project.p("data", "Carts.ini")
        self.load()

    def load(self):
        self.load_text(open(self.path, "rb").read().decode("cp1252") if os.path.exists(self.path) else None)
        self.dirty = False

    def load_text(self, text):
        """From Carts.ini's text (None: there's no file yet). Changed, unless it's the file as it is."""
        self.head, self.routes, self.dirty = [], [], True
        if text is None:
            self.head = ["; Horses and carts (dsengine/carts.py). PointN=MAP,X,Y[,Stop name]; a point with a name is a "
                         "stop. Title=, Fare=, Wait= (seconds at a stop), Loop=1 (round and round).", ""]
            return
        r = None
        for line in text.split("\r\n"):
            s = line.strip()
            if s.startswith("[") and s.endswith("]"):
                r = Route(s[1:-1])
                self.routes.append(r)
            elif r is None:
                self.head.append(line)
            elif "=" in s and not s.startswith(";"):
                k, v = (t.strip() for t in s.split("=", 1))
                if k.lower().startswith("point") and k[5:].isdigit():
                    p = [t.strip() for t in v.split(",", 5)]
                    if len(p) >= 5 and all(t.lstrip("-").isdigit() for t in p[:5]):
                        r.points.append([",".join(p[:3]), int(p[3]), int(p[4]), p[5] if len(p) > 5 else ""])
                else:
                    r.keys.append((k, v))
        while self.head and not self.head[-1].strip():
            self.head.pop()
        self.head.append("")

    def text(self):
        out = list(self.head)
        for r in self.routes:
            out.append("[%s]" % r.key)
            out += ["%s=%s" % kv for kv in r.keys]
            out += ["Point%d=%s,%d,%d%s" % (n, m, x, y, "," + name if name else "")
                    for n, (m, x, y, name) in enumerate(r.points, 1)]
            out.append("")
        return "\r\n".join(out)

    def save(self):
        if self.dirty:
            open(self.path, "wb").write(self.text().encode("cp1252"))
            self.dirty = False

    def snapshot(self):
        return self.text()

    def named(self, key):
        return next((r for r in self.routes if r.key == key), None)

    def new(self, key, first):
        r = Route(key)
        r.keys = [("Title", key.replace("_", " ")), ("Fare", "2"), ("Wait", "6"), ("Loop", "0")]
        r.points = [first]
        self.routes.append(r)
        self.dirty = True
        return r
