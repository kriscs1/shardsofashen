"""Horse-drawn carts (data/Carts.ini): each route has a horse and cart that keep to its points, stop to stop (to its
end and back again, or round and round with Loop=1), waiting Wait seconds at each stop. Hail one as it goes by and it
pulls up for you; Get In, pick a stop and pay the fare, and it takes you there along its way, stopping at the stops
between. It goes at a walk with nobody aboard and three times that with anyone in it. The cart is everyone's (they all
see it go by); who rides it, and where to, is each rider's own."""
import math

from ashen import ini
from ashen.lb import val, trim, distance

CART = "Horse_Cart"
HAIL_RANGE = 288            # (how far off a cart hears you hail it)
BOARD_RANGE = 80            # (close enough to climb in)
HAIL_WAIT = 20000           # (how long a hailed cart waits for you, ms)
BOARDED_WAIT = 2500         # (once someone's in: off it goes, this soon)
RIDE_SPEED = 3              # (with anyone aboard: this many times a walk)
DIRS = {1: "1", 2: "2", 4: "4", 8: "8"}


class Cart:
    def __init__(self, key, title, points, stops, z, fare, wait, loop):
        self.key, self.title = key, title
        self.pts, self.stops, self.z = points, stops, z      # ([(gx, gy)], {point index: stop name}, its level)
        self.fare, self.wait, self.loop = fare, wait, loop
        self.i, self.step, self.t = 0, 1, 0.0               # (the point last passed, which way, how far past it)
        self.wait_until = 0
        self.riders = {}                                     # player name -> the stop (its point) they're going to
        self.e = None


def parse_point(text):
    """"MAP,X,Y[,Stop name]" (a 1-based tile of map MAP) -> (map, x, y, name) or None."""
    p = [trim(v) for v in str(text).split(",", 5)]
    if len(p) < 5 or not all(v.lstrip("-").isdigit() for v in p[:5]):
        return None
    return ",".join(p[:3]), int(p[3]), int(p[4]), p[5] if len(p) > 5 else ""


class Carts:
    def __init__(self, w):
        self.w = w
        self.carts = []
        self.by_uid = {}
        self.load()

    def load(self):
        w = self.w
        for key, items in ini.sections(w.data.data_file("Carts.ini")):
            kv = {k.upper(): v for k, v in items if k}
            points, stops, z = [], {}, None
            for n in range(1, 500):
                pt = parse_point(kv.get("POINT%d" % n, ""))
                if pt is None:
                    if "POINT%d" % n not in kv:
                        break
                    continue
                m = w.map_named(pt[0])
                if m is None or (z is not None and m.mz != z):
                    continue                                 # (no such map, or off its level: left out)
                z = m.mz
                if pt[3]:
                    stops[len(points)] = pt[3]
                points.append((m.ox + (pt[1] - 0.5) * w.tw, m.oy + (pt[2] - 0.5) * w.th))
            if len(points) < 2 or len(stops) < 2:
                continue
            c = Cart(key, trim(kv.get("TITLE", "")) or key.replace("_", " "), points, stops, z,
                     max(0, int(val(kv.get("FARE", "2")))), max(1.0, val(kv.get("WAIT", "6"))),
                     trim(kv.get("LOOP", "0")) == "1")
            c.i = min(stops)
            self.spawn(c)
            self.carts.append(c)

    def spawn(self, c):
        w = self.w
        x, y = c.pts[c.i]
        e = w.add_npc(CART, c.z, x, y, "Attitude=Good Id=Cart_%s" % c.key)
        if e is None:
            return
        e.ai = None                                         # (it thinks nothing: this module drives it)
        e.cart = c
        e.source = "CART"
        c.e = e
        self.place(c, x, y, 2)
        c.wait_until = w.now + c.wait * 1000
        self.by_uid[e.uid] = c

    def of(self, e):
        return getattr(e, "cart", None) if e is not None else None

    def seat(self, c, d):
        """(x, feet y) of the place a rider stands in the cart, facing d: from its Seat.<d>= (x, feet, panel top)."""
        s = self.w.data.entity_ini(CART, "Seat.%d" % d, "").split(",")
        if len(s) >= 2:
            return val(s[0]), val(s[1])
        return c.e.w / 2, c.e.h - 12

    @staticmethod
    def anchor(e):
        """Where on its picture the cart's point on the road is (the middle of its wheels' line)."""
        return e.w / 2, e.h - 8

    def place(self, c, x, y, d):
        e = c.e
        ax, ay = self.anchor(e)
        e.x, e.y = x - ax, y - ay
        e.direction = d

    # ----- every tick
    def tick(self):
        for c in self.carts:
            if c.e is not None and c.e.alive:
                self.move(c)

    def move(self, c):
        w, e = self.w, c.e
        for name in list(c.riders):
            s = w.sessions.get(name)
            if s is None or not s.in_world() or s.dead_wait or s.ride is not c or s.player.z != c.z:
                c.riders.pop(name, None)
                if s is not None and s.ride is c:
                    s.ride = None
                    s.dirty_me = True
        if w.now < c.wait_until and not (c.wait_until - w.now > 600000):
            e.use_words = "Get In,Examine"
            self.animate(e, 0)
            self.pin_riders(c)
            return
        e.use_words = "Hail,Get In,Examine"
        go = w.data.player_move_speed * (RIDE_SPEED if c.riders else 1) * w.dt
        moved = 0.0
        n = len(c.pts)
        while go > 0:
            j = self.next_point(c)
            (ax, ay), (bx, by) = c.pts[c.i], c.pts[j]
            seg = max(0.01, math.hypot(bx - ax, by - ay))
            if c.t + go < seg:
                c.t += go
                moved += go
                go = 0
            else:
                moved += seg - c.t
                go -= seg - c.t
                c.i, c.t = j, 0.0
                if c.loop:
                    c.step = 1
                elif c.i == n - 1 or c.i == 0:
                    c.step = -1 if c.i == n - 1 else 1         # (at an end: it turns about)
                if j in c.stops:
                    self.arrive(c, j)
                    break
        j = self.next_point(c)
        (ax, ay), (bx, by) = c.pts[c.i], c.pts[j]
        seg = max(0.01, math.hypot(bx - ax, by - ay))
        k = min(1.0, c.t / seg)
        dx, dy = bx - ax, by - ay
        d = (2 if dx > 0 else 8) if abs(dx) >= abs(dy) else (4 if dy > 0 else 1)
        if c.t == 0 and w.now < c.wait_until:
            d = e.direction                                 # (pulled up: it faces the way it came)
        self.place(c, ax + dx * k, ay + dy * k, d)
        self.animate(e, moved)
        self.pin_riders(c)

    def next_point(self, c):
        n = len(c.pts)
        if c.loop:
            return (c.i + 1) % n
        j = c.i + c.step
        return j if 0 <= j < n else c.i - c.step

    def animate(self, e, moved):
        w = self.w
        if moved:
            e.anim_dist += moved
        w.animate_entity(e, bool(moved))

    def arrive(self, c, j):
        """At stop j: who's going there gets down; it waits a while."""
        w = self.w
        c.wait_until = w.now + int(c.wait * 1000)
        x, y = c.pts[j]
        w.sound("Hooves", c.z, x, y, radius=256.0)
        for name, dest in list(c.riders.items()):
            s = w.sessions.get(name)
            if s is not None and dest == j:
                self.get_out(s, arrived=True)

    def pin_riders(self, c):
        e = c.e
        for name in c.riders:
            s = self.w.sessions.get(name)
            if s is None:
                continue
            p = s.player
            sx, sy = self.seat(c, e.direction)
            p.x, p.y = e.x + sx - p.w / 2, e.y + sy - p.h
            p.direction = e.direction
            p.pose = ""

    # ----- what the players do to it (Session calls these)
    def verbs(self, s, e):
        c = self.of(e)
        if c is None:
            return "Examine"
        if s.ride is c:
            return "Get Out,Examine" if self.waiting(c) else "Examine"
        return e.use_words or "Examine"

    def waiting(self, c):
        return self.w.now < c.wait_until

    def hail(self, s, e):
        c = self.of(e)
        w = self.w
        if s.ride is c:
            return
        if distance(s.player.cx, s.player.cy, e.cx, e.cy) > HAIL_RANGE:
            s.display_message("The cart is too far off to hear you.", "FAIL", "Denied")
            return
        s.play_sound("Hail", at=(s.player.cx, s.player.cy))
        if w.now < c.wait_until:
            c.wait_until = max(c.wait_until, w.now + HAIL_WAIT)
            s.act_done(True)
            return
        c.wait_until = w.now + HAIL_WAIT                     # (it pulls up where it is, and waits for you)
        s.display_message("You wave the cart down. The horse snorts and stops.", "INFO")
        s.act_done(True)

    def get_in(self, s, e):
        c = self.of(e)
        w = self.w
        if s.ride is c:
            return
        if s.ride is not None:
            self.get_out(s)
        if distance(s.player.cx, s.player.cy, e.cx, e.cy) > BOARD_RANGE:
            s.display_message("You can't reach the cart from here!", "FAIL", "Denied")
            return
        if w.now >= c.wait_until:
            c.wait_until = w.now + HAIL_WAIT                 # (beside it as it goes: it stops for you)
        here = self.stop_at(c)
        options = [("To %s." % name, (lambda j=j: self.choose(s, c, j))) for j, name in sorted(c.stops.items())
                   if j != here][:5]
        fare = ("%d gold" % c.fare) if c.fare else "nothing"
        s.show_menu(c.title, "Horse_Cart2a", "The cart goes round %s. A ride to any stop is %s." % (c.title, fare)
                    + ("" if here is None else " You're at %s." % c.stops[here]), options + [("Not now.", None)])

    def stop_at(self, c):
        """The stop the cart is standing at, or None (between stops: pulled up for someone)."""
        return c.i if c.t == 0 and c.i in c.stops else None

    def choose(self, s, c, j):
        w, e = self.w, c.e
        if e is None or not e.alive or distance(s.player.cx, s.player.cy, e.cx, e.cy) > BOARD_RANGE * 1.5:
            s.display_message("The cart has gone without you.", "FAIL", "Fail")
            return
        if c.fare and s.items_held("Gold_Coin(s)") < c.fare:
            s.display_message("You need %d gold for the cart." % c.fare, "FAIL", "Denied")
            return
        if c.fare:
            s.remove_inventory_item("Gold_Coin(s)", c.fare)
            s.play_sound("Coins")
        s.stop_player_walk()
        s.stand_up()
        s.ride = c
        s.dirty_me = True
        if not c.riders and not c.loop:                       # (the first aboard: it heads their way)
            nxt = self.next_point(c)
            want = 1 if j > c.i else -1
            if c.t > 0:
                want = 1 if j >= max(c.i, nxt) else -1
                if (nxt > c.i) != (want > 0):                 # (going the other way: it turns about where it is)
                    c.i, c.t = nxt, self.seg_len(c) - c.t
            c.step = want
        c.riders[s.player_name] = j
        c.wait_until = min(c.wait_until, w.now + BOARDED_WAIT)
        self.pin_riders(c)
        s.display_message("You climb into the cart. Next stop: %s." % c.stops[j] if self.next_stop(c) == j else
                          "You climb into the cart, for %s." % c.stops[j], "INFO")
        w.sound("Hooves", c.z, e.cx, e.cy, radius=256.0)
        s.act_done(True)

    def seg_len(self, c):
        (ax, ay), (bx, by) = c.pts[c.i], c.pts[self.next_point(c)]
        return math.hypot(bx - ax, by - ay)

    def next_stop(self, c):
        n, i, step = len(c.pts), c.i, c.step
        for _ in range(2 * n):
            i = (i + 1) % n if c.loop else i + step
            if not 0 <= i < n:
                step = -step
                i += 2 * step
            if i in c.stops:
                return i
        return None

    def get_out(self, s, arrived=False):
        c = s.ride
        if c is None:
            return
        w, e = self.w, c.e
        if not arrived and not self.waiting(c):
            s.display_message("Not while it's moving!", "FAIL")
            return
        c.riders.pop(s.player_name, None)
        s.ride = None
        s.dirty_me = True
        p = s.player
        x, y = c.pts[c.i] if c.t == 0 else (e.x + self.anchor(e)[0], e.y + self.anchor(e)[1])
        for dx, dy in ((0, 30), (0, -30), (-48, 0), (48, 0), (0, 52), (0, -52), (-64, 24), (64, 24), (0, 0)):
            nx, ny = x + dx - p.w / 2, y + dy - p.h + 4
            if w.entity_can_stand(p, nx, ny, nx, ny, s):
                break
        p.x, p.y = nx, ny
        s.player_tile = None
        if arrived:
            s.display_message("..and the cart pulls up at %s." % c.stops.get(c.i, "the stop"), "INFO")
        else:
            s.display_message("You climb down from the cart.", "INFO")
        s.act_done(True)

    def leaving(self, s):
        if s.ride is not None:
            s.ride.riders.pop(s.player_name, None)
            s.ride = None
