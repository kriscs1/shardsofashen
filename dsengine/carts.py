"""Horse-drawn carts, and the Isle's ferries (data/Carts.ini): each route has a vehicle that keeps to its points, stop to
stop (to its end and back again, or round and round with Loop=1), waiting Wait seconds at each stop. A route's points are
its NodeN= taken in its Order= (1,2,3,2,4: a node can come up more than once), or its PointN= one after another. Hail a
cart as it goes by and it pulls up for you; Get In, pick a stop and pay the fare, and it takes you there along its way,
stopping at the stops between. It goes at a walk with nobody aboard and three times that with anyone in it.

A route can name its own vehicle (Vehicle=, an Entities.ini NPC with Vehicle=1: the ferry's Ferry_Boat), and keep to a
timetable (Timetable=1: never hailed, never hurried, always at its Speed=, leaving a stop only on the clock's marks of
its Every= seconds, so two boats that leave opposite piers together always leave together), start at a stop of its own (Start=), and ask something of whoever boards (Requires=, a
condition as a Lock's; Refused= what's said, or Refused.Script= a talk that says it: Wim's). A vehicle with Headings=N turns as it goes, through N headings
(<Name>_H<n><frame>: n from 0, north, clockwise), and comes about at a stop before it leaves. The vehicle is
everyone's (they all see it go by); who rides it, and where to, is each rider's own."""
import math

from ashen import ini
from ashen.lb import val, trim, distance

CART = "Horse_Cart"
HAIL_RANGE = 288            # (how far off a cart hears you hail it)
BOARD_RANGE = 80            # (close enough to climb in)
HAIL_WAIT = 20000           # (how long a hailed cart waits for you, ms)
HAIL_REST = 30000           # (after a hail's wait, it can't be waved down again so soon, ms)
CART_BACK = 30000           # (a cart or a ferry somehow gone is back at its last stop this soon, ms)
BOARDED_WAIT = 2500         # (once someone's in: off it goes, this soon)
RIDE_SPEED = 3              # (with anyone aboard: this many times a walk)
TURN_RATE = 150.0           # (a vehicle with headings turns this many degrees a second)
COME_ABOUT = 3500           # (it turns for its way out this long before it leaves a stop, ms)
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
        self.kind = CART                                     # (the vehicle: an Entities.ini NPC with Vehicle=1)
        self.timetable = False                               # (keeps its own time: no hailing, no hurrying)
        self.every = 0                                       # (a timetable's: it leaves only on these marks of the clock, ms)
        self.speed = 0.0                                     # (times a walk; 0: a walk empty, RIDE_SPEED with riders)
        self.requires = []                                   # [(condition, what's said if it isn't met)]
        self.refused_script = ""                             # (a talk instead, if it isn't: the ferry's Wim)
        self.headings = 0                                    # (how many ways its picture turns; 0: the four of a walk)
        self.heading = 0.0                                   # (where it points, degrees clockwise from north)
        self.noun = "cart"


def route_points(kv):
    """A route's way, as written in Carts.ini (its keys upper case): [the PointN text, in order]. NodeN= in Order=
    (a comma list of node numbers; a node more than once goes by it again), else PointN= in number order."""
    nodes = {int(k[4:]): v for k, v in kv.items() if k.startswith("NODE") and k[4:].isdigit()}
    if nodes:
        order = [int(t) for t in str(kv.get("ORDER", "")).replace(" ", "").split(",") if t.isdigit()]
        return [nodes[n] for n in (order or sorted(nodes)) if n in nodes]
    out = []
    for n in range(1, 500):
        if "POINT%d" % n not in kv:
            break
        out.append(kv["POINT%d" % n])
    return out


def parse_point(text):
    """"MAP,X,Y[,Stop name]" (a 1-based tile of map MAP) -> (map, x, y, name) or None."""
    p = [trim(v) for v in str(text).split(",", 5)]
    if len(p) < 5 or not all(v.lstrip("-").isdigit() for v in p[:5]):
        return None
    return ",".join(p[:3]), int(p[3]), int(p[4]), p[5] if len(p) > 5 else ""


def bearing(dx, dy):
    """Degrees clockwise from north (screen up) of the way dx, dy."""
    return math.degrees(math.atan2(dx, -dy)) % 360.0


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
            for text in route_points(kv):
                pt = parse_point(text)
                if pt is None:
                    continue
                m = w.map_named(pt[0])
                if m is None or (z is not None and m.mz != z):
                    continue                                 # (no such map, or off its level: left out)
                z = m.mz
                if pt[3]:
                    stops[len(points)] = pt[3]
                points.append((m.ox + (pt[1] - 0.5) * w.tw, m.oy + (pt[2] - 0.5) * w.th))
            if len(points) < 2 or len(set(stops.values())) < 2:
                continue
            c = Cart(key, trim(kv.get("TITLE", "")) or key.replace("_", " "), points, stops, z,
                     max(0, int(val(kv.get("FARE", "1")))), max(1.0, val(kv.get("WAIT", "6"))),
                     trim(kv.get("LOOP", "0")) == "1")
            c.kind = trim(kv.get("VEHICLE", "")) or CART
            if w.data.entity_ini(c.kind, "Vehicle", "0") != "1":
                c.kind = CART                                # (not a vehicle: the cart, as before)
            c.timetable = trim(kv.get("TIMETABLE", "0")) == "1"
            c.speed = max(0.0, val(kv.get("SPEED", "0")))
            c.every = int(max(0.0, val(kv.get("EVERY", "0"))) * 1000) if c.timetable else 0
            c.headings = int(val(w.data.entity_ini(c.kind, "Headings", "0")))
            c.noun = w.data.entity_ini(c.kind, "Vehicle.Noun", "") or "cart"
            for n in [""] + [".%d" % k for k in range(1, 10)]:
                cond = trim(kv.get("REQUIRES" + n, ""))
                if cond:
                    c.requires.append((cond, trim(kv.get("REFUSED" + n, "")) or "You can't go aboard yet."))
            c.refused_script = trim(kv.get("REFUSED.SCRIPT", ""))
            c.i = min(stops)
            start = trim(kv.get("START", "")).lower()
            for j, name in sorted(stops.items()):
                if start and name.lower() == start:
                    c.i = j                                  # (it starts at that stop)
            if not c.loop and c.i == len(points) - 1:
                c.step = -1                                  # (at its far end: it sets off back)
            self.spawn(c)
            self.carts.append(c)

    def spawn(self, c):
        w = self.w
        x, y = c.pts[c.i]
        e = w.add_npc(c.kind, c.z, x, y, "Attitude=Good Id=Cart_%s" % c.key)
        if e is None:
            return
        e.ai = None                                         # (it thinks nothing: this module drives it)
        e.cart = c
        e.source = "CART"
        c.e = e
        if c.headings:
            (ax, ay), (bx, by) = c.pts[c.i], c.pts[self.next_point(c)]
            c.heading = bearing(bx - ax, by - ay)
        self.place(c, x, y, 2)
        c.wait_until = self.leave_time(c, w.now + c.wait * 1000)
        self.by_uid[e.uid] = c

    @staticmethod
    def leave_time(c, at):
        """When it may set off, staying till at: a timetable with Every= leaves on the next mark of the clock after it
        (so every boat with the same Every leaves together, however long its way)."""
        if not c.every:
            return at
        return -(-int(at) // c.every) * c.every

    def of(self, e):
        return getattr(e, "cart", None) if e is not None else None

    def seat(self, c, d):
        """(x, feet y) of the place a rider stands in the vehicle, facing d: from its Seat.<d>= (x, feet, panel top),
        or its Seat= (one for every way: a boat, seen from above)."""
        ent = self.w.data.entity_ini
        s = (ent(c.kind, "Seat.%d" % d, "") or ent(c.kind, "Seat", "")).split(",")
        if len(s) >= 2:
            return val(s[0]), val(s[1])
        return c.e.w / 2, c.e.h - 12

    def anchor(self, e):
        """Where on its picture the vehicle's point on its way is (a cart: the middle of its wheels' line; a boat: its
        middle)."""
        c = self.of(e)
        if c is not None and c.headings:
            return e.w / 2, e.h / 2
        return e.w / 2, e.h - 8

    def place(self, c, x, y, d):
        e = c.e
        ax, ay = self.anchor(e)
        e.x, e.y = x - ax, y - ay
        e.direction = d

    def word(self, c, text):
        """A line about a cart said of this vehicle ("the cart" -> "the ferry")."""
        return text if c.noun == "cart" else text.replace("cart", c.noun)

    # ----- every tick
    def tick(self):
        for c in self.carts:
            if c.e is not None and c.e.alive:
                self.move(c)
            elif not getattr(c, "back_at", 0):          # (gone some other way: its riders set down, back in a while)
                c.back_at = self.w.now + CART_BACK
                for name in list(c.riders):
                    s = self.w.sessions.get(name)
                    if s is not None and s.ride is c and c.e is not None:
                        self.get_out(s, True)
                c.riders = {}
            elif self.w.now >= c.back_at:
                c.back_at = 0
                if c.e is not None:
                    self.by_uid.pop(c.e.uid, None)
                    if c.e in self.w.ents:
                        self.w.remove_entity(c.e)
                c.t = 0.0
                self.spawn(c)

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
            if c.headings and c.wait_until - w.now < COME_ABOUT:
                (ax, ay), (bx, by) = c.pts[c.i], c.pts[self.next_point(c)]
                self.turn(c, bearing(bx - ax, by - ay))     # (coming about for its way out)
            self.animate(e, 0)
            self.pin_riders(c)
            return
        e.use_words = "Examine" if c.timetable else "Hail,Get In,Examine"
        go = w.data.player_move_speed * (c.speed or (RIDE_SPEED if c.riders else 1)) * w.dt
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
        docked = c.t == 0 and w.now < c.wait_until
        if docked:
            d = e.direction                                 # (pulled up: it faces the way it came)
        elif c.headings:
            self.turn(c, bearing(dx, dy))
        self.place(c, ax + dx * k, ay + dy * k, d)
        self.animate(e, moved)
        self.pin_riders(c)

    def turn(self, c, want):
        """A vehicle with headings swings round toward want, at TURN_RATE."""
        diff = (want - c.heading + 540.0) % 360.0 - 180.0
        step = TURN_RATE * self.w.dt
        c.heading = want % 360.0 if abs(diff) <= step else (c.heading + math.copysign(step, diff)) % 360.0

    def next_point(self, c):
        n = len(c.pts)
        if c.loop:
            return (c.i + 1) % n
        j = c.i + c.step
        return j if 0 <= j < n else c.i - c.step

    def animate(self, e, moved):
        w = self.w
        c = self.of(e)
        if c is not None and c.headings:
            h = int(round(c.heading / (360.0 / c.headings))) % c.headings
            if moved:
                e.anim_dist += moved
                if e.anim_dist >= w.WALK_STEP * 2:
                    e.frame = (e.frame + 1) % 2              # (its wake, and the oars or the pole, as it goes)
                    e.anim_dist = 0.0
            else:
                e.frame, e.anim_dist = 0, 0.0
            # (a: tied up, still; b and c, under way)
            e.image = "%s_H%02d%s" % (e.name, h, ("bc"[e.frame % 2]) if moved else "a")
            return
        if moved:
            e.anim_dist += moved
        w.animate_entity(e, bool(moved))

    def arrive(self, c, j):
        """At stop j: who's going there gets down; it waits a while."""
        w = self.w
        c.wait_until = self.leave_time(c, w.now + int(c.wait * 1000))
        x, y = c.pts[j]
        w.sound(w.data.entity_ini(c.kind, "Arrive.Sound", "") or "Hooves", c.z, x, y, radius=256.0)
        for name, dest in list(c.riders.items()):
            s = w.sessions.get(name)
            if s is not None and c.stops.get(dest) == c.stops.get(j):       # (that stop, here or where it's again)
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
        if s.ride is c or c.timetable:
            return                                           # (a ferry keeps its time: it isn't waved down)
        if distance(s.player.cx, s.player.cy, e.cx, e.cy) > HAIL_RANGE:
            s.display_message("The cart is too far off to hear you.", "FAIL", "Denied")
            return
        s.play_sound("Hail", at=(s.player.cx, s.player.cy))
        if w.now < c.wait_until:
            s.act_done(True)                                 # (stopped already: it waits as long as it would)
            return
        if w.now < getattr(c, "hail_rest", 0):               # (once a while: never held at one spot for ever)
            s.display_message(self.word(c, "The cart rolls on: it stopped for a wave only just now."), "FAIL", "Denied")
            return
        c.wait_until = w.now + HAIL_WAIT                     # (it pulls up where it is, and waits for you)
        c.hail_rest = c.wait_until + HAIL_REST
        s.display_message("You wave the cart down. The horse snorts and stops.", "INFO")
        s.act_done(True)

    def refusal(self, s, c):
        """What stops this player going aboard (a route's Requires=), or None."""
        for cond, words in c.requires:
            if not s.condition_met(cond):
                return words
        return None

    def get_in(self, s, e):
        c = self.of(e)
        w = self.w
        if s.ride is c:
            return
        if distance(s.player.cx, s.player.cy, e.cx, e.cy) > BOARD_RANGE:
            s.display_message(self.word(c, "You can't reach the cart from here!"), "FAIL", "Denied")
            return
        no = self.refusal(s, c)
        if no and c.refused_script:                         # (not yet: the ferryman says why, himself, in a talk)
            s.start_script(c.refused_script, True)
            return
        if c.timetable and not self.waiting(c):
            s.display_message("The %s has cast off." % c.noun, "FAIL", "Denied")
            return
        if no:
            s.display_message(no, "FAIL", "Denied")
            return
        if s.ride is not None:
            self.get_out(s)
        if w.now >= c.wait_until:
            c.wait_until = w.now + HAIL_WAIT                 # (beside it as it goes: it stops for you)
        here = self.stop_at(c)
        options = [("To %s." % c.stops[j], (lambda j=j: self.choose(s, c, j))) for j in self.ahead(c)
                   if here is None or c.stops[j] != c.stops[here]][:5]
        fare = ("%d gold" % c.fare) if c.fare else "nothing"
        about = w.data.entity_ini(c.kind, "Board.Words", "") or "The cart goes round %s. A ride to any stop is %s."
        s.show_menu(c.title, w.data.entity_ini(c.kind, "Menu.Image", "") or "Horse_Cart2a",
                    about.replace("%s", "\0", 1).replace("%s", fare).replace("\0", c.title)
                    + ("" if here is None else " You're at %s." % c.stops[here]), options + [("Not now.", None)])

    def ahead(self, c):
        """Each stop once, by name, at the point it next comes to it (a route that goes by a node twice)."""
        seen, out = set(), []
        i, step, n = c.i, c.step, len(c.pts)
        for _ in range(2 * n + 2):
            if i in c.stops and c.stops[i] not in seen:
                seen.add(c.stops[i])
                out.append(i)
            i = (i + 1) % n if c.loop else i + step
            if not 0 <= i < n:
                step = -step
                i += 2 * step
        return out

    def stop_at(self, c):
        """The stop the cart is standing at, or None (between stops: pulled up for someone)."""
        return c.i if c.t == 0 and c.i in c.stops else None

    def choose(self, s, c, j):
        w, e = self.w, c.e
        if e is None or not e.alive or distance(s.player.cx, s.player.cy, e.cx, e.cy) > BOARD_RANGE * 1.5 or \
                (c.timetable and not self.waiting(c)):
            s.display_message(self.word(c, "The cart has gone without you."), "FAIL", "Fail")
            return
        no = self.refusal(s, c)
        if no:
            s.display_message(no, "FAIL", "Denied")
            return
        if s.demo():                    # (a stop outside the demo: the ferry's far side, dsengine/demo.py)
            m = w.map_at(c.z, *c.pts[j])
            if m is None or not s.demo_map(m.name):
                if val(s.get_attribute("PapersFound")) >= 1:
                    s.demo_end()            # (the Isle done: its end card, not a refusal)
                else:
                    s.demo_say("border")
                return
        if c.fare and s.items_held("Gold_Coin(s)") < c.fare:
            s.display_message(self.word(c, "You need %d gold for the cart.") % c.fare, "FAIL", "Denied")
            return
        if c.fare:
            s.remove_inventory_item("Gold_Coin(s)", c.fare)
            s.play_sound("Coins")
        s.stop_player_walk()
        s.stand_up()
        s.ride = c
        s.dirty_me = True
        if not c.riders and not c.loop and not c.timetable:   # (the first aboard: it heads their way)
            nxt = self.next_point(c)
            want = 1 if j > c.i else -1
            if c.t > 0:
                want = 1 if j >= max(c.i, nxt) else -1
                if (nxt > c.i) != (want > 0):                 # (going the other way: it turns about where it is)
                    c.i, c.t = nxt, self.seg_len(c) - c.t
            c.step = want
        c.riders[s.player_name] = j
        if not c.timetable:
            c.wait_until = min(c.wait_until, w.now + BOARDED_WAIT)
        self.pin_riders(c)
        if c.noun == "cart":
            s.display_message("You climb into the cart. Next stop: %s." % c.stops[j] if self.next_stop(c) == j else
                              "You climb into the cart, for %s." % c.stops[j], "INFO")
        else:
            s.display_message("You step aboard the %s, for %s. It leaves when it leaves." % (c.noun, c.stops[j])
                              if c.timetable else "You step aboard the %s, for %s." % (c.noun, c.stops[j]), "INFO")
        w.sound(w.data.entity_ini(c.kind, "Board.Sound", "") or "Hooves", c.z, e.cx, e.cy, radius=256.0)
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

    # (where to step down, nearest the vehicle first: the old cart's spots, then round it a tile at a time)
    OUT_SPOTS = [(0, 30), (0, -30), (-48, 0), (48, 0), (0, 52), (0, -52), (-64, 24), (64, 24)]
    OUT_SPOTS += sorted(((dx * 16, dy * 16) for dx in range(-6, 7) for dy in range(-6, 7) if dx or dy),
                        key=lambda d: math.hypot(*d))

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
        if c.headings:
            x, y = e.x + self.anchor(e)[0], e.y + self.anchor(e)[1]
        nx, ny = x - p.w / 2, y - p.h + 4
        for dx, dy in self.OUT_SPOTS:
            tx, ty = x + dx - p.w / 2, y + dy - p.h + 4
            if w.entity_can_stand(p, tx, ty, tx, ty, s):
                nx, ny = tx, ty
                break
        p.x, p.y = nx, ny
        s.player_tile = None
        if arrived:
            s.display_message(self.word(c, "..and the cart pulls up at %s.") % c.stops.get(c.i, "the stop")
                              if c.noun == "cart" else "..and the %s ties up at %s." % (c.noun, c.stops.get(c.i, "the pier")),
                              "INFO")
        else:
            s.display_message(self.word(c, "You climb down from the cart.") if c.noun == "cart" else
                              "You step off the %s." % c.noun, "INFO")
        s.act_done(True)

    def leaving(self, s):
        if s.ride is not None:
            s.ride.riders.pop(s.player_name, None)
            s.ride = None
