"""The seasons (data\\Seasons.ini, the owner's wish): one year for everyone, on the world's clock, Year.Days real days long, so a
player sees them all (Spring, Summer, Autumn, Winter from the first day of the clock).

  * Days are longer in summer and nights longer in winter ([<Season>] Night.From, Night.To: world.night_bounds).
  * Winter: snow instead of rain (Weather.ini kinds, Becomes), and every river and lake freezes hard enough to walk on
    (Water cells of a body of water smaller than River.Most, turned to Ice with the tile changes everyone shares, and back in
    spring). What says Season.Absent=Winter in Entities.ini (mosquitoes) isn't about: gone till it isn't.
  * Crops grow by [<Season>] Crop.Growth; a script can ask $World.Season; a script's Give.Item is swapped by [Swap.<Season>]
    (what's in season: the catch changes through the year).
  * The page draws what's only to be seen (ground.js seasonal: snow patches, autumn leaves, spring's flowers).
Never saved: it comes from the clock."""
import logging

from ashen import ini
from ashen.lb import val, trim

from .entity import NPC

log = logging.getLogger("ashen.seasons")
ORDER = ("Spring", "Summer", "Autumn", "Winter")
EVERY = 5000            # (ms between looks at the clock)
FREEZE_PER_TICK = 400   # (cells of ice a tick: a thaw spread out over a moment, not a stall)


class Seasons:
    def __init__(self, world):
        self.w = world
        self.path = world.data.data_file("Seasons.ini")
        self.now_is = None
        self.pinned = None                  # (a season that stays, whatever the clock says: the tests')
        self.checked = -10 ** 12
        self.rivers = None
        self.todo = []
        self.frozen = False

    def setting(self, section, key, default=""):
        return ini.read(section, key, str(default), self.path)

    def number(self, section, key, default):
        return val(self.setting(section, key, default))

    def year_ms(self):
        return max(1.0, self.number("Seasons", "Year.Days", 16)) * 86400000

    def season(self, now=None):
        now = self.w.now if now is None else now
        at = (now % self.year_ms()) / self.year_ms()
        return ORDER[min(3, int(at * 4))]

    def current(self):
        return self.now_is or self.season()

    # ----- the rivers: every little body of water on the world's level (once)
    def find_rivers(self):
        most = int(self.number("Seasons", "River.Most", 900))
        seen, out = set(), []
        grid = {}
        for m in self.w.maps.values():
            if m.mz != 0:
                continue
            for y in range(1, self.w.yt + 1):
                for x in range(1, self.w.xt + 1):
                    c = m.cell(x, y)
                    if m.tile[c].startswith("Water0") and not m.decor[c]:
                        grid[(m.mx * self.w.xt + x - 1, m.my * self.w.yt + y - 1)] = (m, x, y)
        for start in grid:
            if start in seen:
                continue
            body, todo = [], [start]
            seen.add(start)
            while todo:
                gx, gy = todo.pop()
                body.append(grid[(gx, gy)])
                for n in ((gx + 1, gy), (gx - 1, gy), (gx, gy + 1), (gx, gy - 1)):
                    if n in grid and n not in seen:
                        seen.add(n)
                        todo.append(n)
            if len(body) <= most:
                out += body
        self.rivers = out
        log.info("%d cells of river and lake", len(out))

    def tick(self):
        w = self.w
        if self.todo:
            for m, x, y, spec in self.todo[:FREEZE_PER_TICK]:
                w.change_tile(m, x, y, spec)
            del self.todo[:FREEZE_PER_TICK]
        if 0 <= w.now - self.checked < EVERY:
            return
        self.checked = w.now
        now = self.pinned or self.season()
        if now != self.now_is:
            self.now_is = now
            self.changed()
        self.keep_absent()

    def changed(self):
        w = self.w
        winter = self.now_is == "Winter"
        if winter != self.frozen:
            self.frozen = winter
            if self.rivers is None:
                self.find_rivers()
            ice, water = trim(self.setting("Seasons", "Ice", "Ice001")), "Water001"
            self.todo = [(m, x, y, ice if winter else water) for m, x, y in self.rivers]
        for s in w.sessions.values():
            s.emit(w.clock_event())
            s.weather_dirty = True

    def absent(self, name):
        """Is this kind out of season? (Entities.ini Season.Absent=Winter,Autumn)"""
        said = trim(self.w.data.entity_ini(name, "Season.Absent", ""))
        return bool(said) and self.current() in [v.strip() for v in said.split(",")]

    def keep_absent(self):
        """What's out of season keeps out: gone as it would die, without its death; it comes back when it respawns in season."""
        w = self.w
        if self.current() != getattr(self, "absent_for", None):
            self.absent_for = self.current()
            names = {e.name for e in w.ents if e.type == NPC}
            self.absent_now = {n for n in names if self.absent(n)}
        if not self.absent_now:
            return
        for e in list(w.ents):
            if e.type == NPC and e.name in self.absent_now and e.alive and not e.in_combat:
                w.season_hide(e)

    # ----- what scripts and the world ask
    def night(self):
        s = self.current()
        return self.number(s, "Night.From", 0.83), self.number(s, "Night.To", 0.21)

    def crop_growth(self):
        return max(0.0, self.number(self.current(), "Crop.Growth", 1))

    def swapped(self, item):
        """What a script's giving is, this season (the catch changes through the year)."""
        return trim(self.setting("Swap." + self.current(), item, item)) or item

    def rain_is(self, kind):
        """What a sky's kind falls as, this season."""
        return trim(self.setting("Winter.Sky", kind, kind)) if self.current() == "Winter" else kind
