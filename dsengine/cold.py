"""The cold (data\\Cold.ini): out on snow or ice and not warm, it bites, a little at a time. Warm is: indoors (under a
roof), near a fire, wearing something warm (Entities.ini Warm=1: a fur cap, a wool hood, wool mittens), or a Warming
Draught drunk lately (herbs: WarmUntil, a real time). It gives a moment's grace first, says so once, and shows as Cold
by your health."""
import time

from ashen.lb import val, trim, distance

COLD = "Cold.ini"
FIRES = ("Fire", "Campfire", "Fireplace", "Brazier", "Forge", "Range", "Oven", "Stove")


class ColdMixin:
    def cold_num(self, key, default):
        v = trim(self.data.ini_read(COLD, "Cold", key, ""))
        return val(v) if v else default

    def cold_ground(self):
        """Snow or ice underfoot, out in the open."""
        p = self.player
        m, tx, ty = self.w.tile_at(p.z, p.fx, p.fy)
        if m is None or not m.inside(tx, ty) or self.w.roofed(p.z, p.fx, p.fy):
            return False
        t = m.tile[m.cell(tx, ty)]
        return any(t.startswith(k) for k in trim(self.cold_text("Tiles", "Snow,Ice")).split(","))

    def cold_text(self, key, default):
        return trim(self.data.ini_read(COLD, "Cold", key, "")) or default

    def warm(self):
        if any(it and trim(self.entity_ini(it, "Warm", "0")) == "1" for it in self.equipped[1:]):
            return True
        if val(self.get_attribute("WarmUntil")) > time.time():
            return True                                     # (a Warming Draught: herbs, inside you)
        p, w = self.player, self.w
        reach = self.cold_num("Fire.Range", 96)
        for e in w.ents:
            if e.z == p.z and e.alive and e.name.startswith(FIRES) and distance(e.cx, e.cy, p.cx, p.cy) <= reach:
                return True
        m, tx, ty = w.tile_at(p.z, p.fx, p.fy)
        if m is not None:
            r = int(reach // w.tw)
            for dy in range(-r, r + 1):
                for dx in range(-r, r + 1):
                    x, y = tx + dx, ty + dy
                    if m.inside(x, y) and (m.tile[m.cell(x, y)].startswith(FIRES) or
                                           (m.decor[m.cell(x, y)] or "").startswith(FIRES)):
                        return True
        return False

    def cold_tick(self):
        if self.god_mode or self.now < self.cold_at:
            return
        self.cold_at = self.now + 1000
        if not self.cold_ground() or self.warm():
            if self.cold_since:
                self.cold_since = 0
                self.status.pop("Cold", None)
                self.dirty_me = True
            return
        if not self.cold_since:
            self.cold_since = self.now
            return
        if self.now - self.cold_since < self.cold_num("Grace", 20) * 1000:
            return
        if "Cold" not in self.status:                      # (said once; shown by your health while it lasts)
            self.display_message("The cold bites. Find warmth: a fire, a roof, something warm to wear.", "DAMAGE",
                                 "-")
        self.status["Cold"] = {"until": self.now + 3000, "next": self.now + 3000}
        if self.now >= self.cold_next:
            self.cold_next = self.now + int(self.cold_num("Every", 8) * 1000)
            self.update_skill("Hitpoints", "-%d" % int(self.cold_num("Damage", 1)))
            self.fx_splat("Hit", int(self.cold_num("Damage", 1)), self.player)
            self.dirty_me = True
