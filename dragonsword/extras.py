"""Status effects (poison, burning, bleeding, chill), the gravestone you leave when you die, and the hotbar.

Status effects: a monster's Entities.ini On.Hit=<Effect> <chance %> gives it to you when its blow (or its missile)
lands. They wear off by themselves; an item with Cures=<Effect> <Effect>... (the Antidote) ends them at once. Dying
ends them too. Each shows as a little icon over your head.

The gravestone: when you die, everything in your inventory (not what you're wearing) is left in a grave where you
fell, for Config [Gameplay] Grave.Minutes (10) of play. Search it to take it all back. Die again first and the old
grave is gone. Kept in the save ([Grave]).

The hotbar: five slots along the bottom of the view for things you use often (food, potions, scrolls). Right-click
an item in your inventory to put it there (or take it off); click a slot, or press 1-5, to use it (its first verb:
Eat, Drink, Cast...). Kept in the save ([Hotbar])."""
import math

import pygame

from .entity import ACTIONBOXITEM, INVENTORYITEM, STATICOBJECT
from .lb import val, word, trim, lbstr, pretty, random_number, rnd

EFFECTS = {
    # name: how long (ms), how often it hurts (ms, 0 = never), damage (min, max), icon colour, messages
    "Poison": dict(ms=14000, every=2000, dmg=(1, 1), colour=(90, 200, 60), start="You've been poisoned!",
                   end="The poison wears off."),
    "Burn": dict(ms=5000, every=1000, dmg=(1, 2), colour=(255, 128, 30), start="You're on fire!",
                 end="The flames go out."),
    "Bleed": dict(ms=7000, every=1500, dmg=(1, 1), colour=(200, 24, 24), start="You're bleeding!",
                  end="The bleeding stops."),
    "Chill": dict(ms=7000, every=0, dmg=(0, 0), colour=(120, 196, 255), start="You're chilled to the bone: slowed!",
                  end="You warm up again."),
}
CHILL_MOVE, CHILL_ATTACK = 0.6, 1.4         # chilled: you move at 60%, swing 40% slower
HOTBAR_SLOTS = 5
HOTBAR_SIZE = 38


class ExtrasMixin:
    # =================================================================================================================
    # Status effects
    # =================================================================================================================
    def status_reset(self):
        for name in list(getattr(self, "status", {})):
            self.status_end(name, quiet=True)
        self.status = {}

    def status_start(self, name):
        fx = EFFECTS.get(name)
        if fx is None or self.god_mode:
            return
        if self.resists(name):                          # (a worn charm: Entities.ini Resists=Burn)
            return
        now = self.clock()
        st = self.__dict__.setdefault("status", {})
        if name not in st:
            self.display_message(fx["start"], "DAMAGE")
            if name == "Chill":
                self.player.move_speed *= CHILL_MOVE
        st[name] = {"until": now + fx["ms"], "next": now + fx["every"]}

    def status_end(self, name, quiet=False):
        st = getattr(self, "status", {})
        if name not in st:
            return
        del st[name]
        if name == "Chill":
            self.player.move_speed /= CHILL_MOVE
        if not quiet:
            self.display_message(EFFECTS[name]["end"], "INFO")

    def status_tick(self):
        """Every frame: what the effects do, and their ending."""
        st = getattr(self, "status", None)
        if not st:
            return
        now = self.clock()
        for name in list(st):
            s, fx = st[name], EFFECTS[name]
            if now >= s["until"] or now < s["until"] - fx["ms"] - 1000:
                self.status_end(name)
                continue
            if fx["every"] and now >= s["next"]:
                s["next"] = now + fx["every"]
                dmg = random_number(*fx["dmg"])
                if dmg > 0 and self.player.hp > 0:
                    self.fx_splat("Hit", dmg, self.player)
                    self.player_last_combat = now
                    self.update_skill("Hitpoints", "-%d" % dmg)
                    if self.player.hp <= 0:
                        return

    def status_on_hit(self, e):
        """A monster's blow landed: its On.Hit effect, maybe ("Poison 40")."""
        on = trim(self.entity_ini(e.name, "On.Hit", ""))
        if not on:
            return
        name, chance = word(on, 1), val(word(on, 2)) or 100
        if name in EFFECTS and rnd() * 100 < chance:
            self.status_start(name)

    def resists(self, effect):
        """Something worn (Entities.ini Resists=<Effect> ...) wards off that effect."""
        for s in range(1, self.equip_slots + 1):
            it = self.equipped[s]
            if it and effect in trim(self.entity_ini(it, "Resists", "")).split():
                return True
        return False

    def resist_damage(self, e, damage):
        """A monster whose blows carry an effect you resist (the dragon's fire, a Fire Ward) hits a third softer."""
        on = word(trim(self.entity_ini(e.name, "On.Hit", "")), 1)
        if on and self.resists(on):
            return damage - max(1, damage // 3) if damage > 1 else damage
        return damage

    def attack_slowdown(self):
        return CHILL_ATTACK if "Chill" in getattr(self, "status", {}) else 1.0

    def drink_cure(self, e):
        """An item with Cures= (the Antidote): ends those effects, used up."""
        cures = trim(self.entity_ini(e.name, "Cures", "")).split()
        self.remove_inventory_item(e.name, 1)
        self.play_sound("EatFood")
        ended = [c for c in cures if c in getattr(self, "status", {})]
        for c in ended:
            self.status_end(c, quiet=True)
        self.display_message("You drink the %s.%s" % (pretty(e.name), " You feel much better!" if ended else ""),
                             "SUCCESS")
        food = val(self.entity_ini(e.name, "Food.Value", "0"))
        if food > 0:
            self.update_skill("Hitpoints", "+" + lbstr(food))

    def status_icon(self, name):
        """A 12 x 12 picture of an effect (drawn once)."""
        cache = self.__dict__.setdefault("status_icons", {})
        if name in cache:
            return cache[name]
        s = pygame.Surface((12, 12), pygame.SRCALPHA)
        col = EFFECTS[name]["colour"]
        pygame.draw.circle(s, (20, 14, 10, 220), (6, 6), 6)
        if name in ("Poison", "Bleed"):                         # a drop
            pygame.draw.circle(s, col, (6, 7), 3)
            pygame.draw.polygon(s, col, [(6, 2), (3, 6), (9, 6)])
            pygame.draw.circle(s, (255, 255, 255, 160), (5, 7), 1)
        elif name == "Burn":                                    # a flame
            pygame.draw.polygon(s, col, [(6, 1), (9, 6), (8, 10), (4, 10), (3, 6)])
            pygame.draw.polygon(s, (255, 230, 120), [(6, 5), (7, 8), (5, 8)])
        else:                                                   # a snowflake
            for a in range(3):
                ang = a * math.pi / 3
                dx, dy = int(round(4 * math.cos(ang))), int(round(4 * math.sin(ang)))
                pygame.draw.line(s, col, (6 - dx, 6 - dy), (6 + dx, 6 + dy), 1)
        cache[name] = s
        return s

    def draw_status_icons(self, surf, cam_x, cam_y):
        st = getattr(self, "status", None)
        if not st:
            return
        p = self.player
        names = [n for n in EFFECTS if n in st]
        x0 = int(p.cx - cam_x - len(names) * 7)
        y = int(p.y - cam_y) - 26
        for i, n in enumerate(names):
            surf.blit(self.status_icon(n), (x0 + i * 14, y))

    # =================================================================================================================
    # The gravestone
    # =================================================================================================================
    def grave_reset(self):
        self.grave = None                   # {"map", "x", "y", "left" (ms of play), "items": [(name, qty)]}
        self.grave_ent = None

    def grave_minutes(self):
        return max(0.5, val(self.config_read("Gameplay", "Grave.Minutes", "10")))

    def grave_leave(self):
        """Dying: the inventory goes into a grave where the player fell."""
        old = getattr(self, "grave", None)
        if old and old.get("items"):
            self.display_message("Your old grave crumbles away, and what was in it with it.", "DAMAGE")
        self.grave_remove_entity()
        items = [(e.name, e.quantity, getattr(e, "wear", 0)) for e in self.inv]
        for e in list(self.inv):                        # (each with its wear: durability.py)
            e.alive = False
        self.inv[:] = []
        self.check_locks(True)
        if not items:
            self.grave = None
            return
        p = self.player
        self.grave = {"map": self.screen_name, "x": int(p.fx) - 16, "y": int(p.fy) - 28, "items": items,
                      "left": self.grave_minutes() * 60000}
        self.display_message("Everything you carried lies in a grave where you fell (map %s). Get back to it within "
                             "%s minutes!" % (self.screen_name, lbstr(self.grave_minutes())), "DAMAGE")

    def grave_place(self):
        """On arriving on a map: the grave, if it's on this one."""
        g = getattr(self, "grave", None)
        if not g or g["map"] != self.screen_name:
            return
        if self.grave_ent is not None and self.grave_ent in self.world and self.grave_ent.alive:
            return
        self.grave_ent = self.add_static_object("Gravestone", g["x"], g["y"])

    def grave_remove_entity(self):
        e = getattr(self, "grave_ent", None)
        if e is not None and e in self.world:
            e.alive = False
            self.world.remove(e)
        self.grave_ent = None

    def grave_tick(self, delta_ms):
        g = getattr(self, "grave", None)
        if not g:
            return
        g["left"] -= delta_ms
        if g["left"] <= 0:
            self.grave_remove_entity()
            self.grave = None
            self.display_message("Your grave has crumbled away: what you left in it is lost.", "DAMAGE")

    def grave_search(self):
        g = getattr(self, "grave", None)
        if not g:
            self.display_message("The grave is empty.", "INFO")
            return
        left = []
        for name, qty, wear in g["items"]:
            room = self.inventory_slots_available(name)
            take = min(qty, room)
            if take > 0:
                self.add_inventory_item(name, take, wear)
            if qty - take > 0:
                left.append((name, qty - take, wear))
        if left:
            g["items"] = left
            self.display_message("You take what you can carry; the rest is still in the grave.", "INFO")
            return
        self.grave_remove_entity()
        self.grave = None
        self.play_sound("Pickup")
        self.display_message("You take back everything from your grave.", "SUCCESS")

    def grave_load(self, section):
        """[Grave] Map=, X=, Y=, Left= (ms), Item1=name,qty..."""
        d = dict(section)
        self.grave_reset()
        if not d.get("Map"):
            return
        items = []
        for i in range(1, 400):
            v = d.get("Item%d" % i)
            if not v:
                break
            items.append((trim(word(v, 1, ",")), max(1, val(word(v, 2, ","))), int(val(word(v, 3, ",") or "0"))))
        if items:
            self.grave = {"map": d["Map"], "x": val(d.get("X", "0")), "y": val(d.get("Y", "0")),
                          "left": val(d.get("Left", "0")), "items": items}

    def grave_save_lines(self):
        g = getattr(self, "grave", None)
        out = ["", "[Grave]"]
        if g:
            out += ["Map=" + g["map"], "X=%d" % int(g["x"]), "Y=%d" % int(g["y"]), "Left=%d" % int(g["left"])]
            out += ["Item%d=%s,%d,%d" % (i, n, q, w) for i, (n, q, w) in enumerate(g["items"], 1)]
        return out

    # =================================================================================================================
    # The hotbar
    # =================================================================================================================
    def hotbar_reset(self):
        self.hotbar = [""] * HOTBAR_SLOTS

    def hotbar_rect(self, k):
        total = HOTBAR_SLOTS * HOTBAR_SIZE + (HOTBAR_SLOTS - 1) * 4
        x0 = (self.view_w - total) // 2
        return pygame.Rect(x0 + k * (HOTBAR_SIZE + 4), self.view_h - HOTBAR_SIZE - 8, HOTBAR_SIZE, HOTBAR_SIZE)

    def hotbar_slot_at(self, x, y):
        if self.ab_mode or getattr(self, "help_open", False):
            return -1
        for k in range(HOTBAR_SLOTS):
            if self.hotbar_rect(k).collidepoint(x, y):
                return k
        return -1

    def hotbar_add(self, name):
        if name in self.hotbar:
            return
        free = [k for k, n in enumerate(self.hotbar) if not n]
        k = free[0] if free else HOTBAR_SLOTS - 1
        self.hotbar[k] = name
        self.display_message("%s is on your hotbar: press %d to use it." % (pretty(name), k + 1), "INFO")

    def hotbar_remove(self, k):
        if 0 <= k < HOTBAR_SLOTS and self.hotbar[k]:
            self.display_message("%s is off your hotbar." % pretty(self.hotbar[k]), "INFO")
            self.hotbar[k] = ""

    def hotbar_use(self, k):
        if not (0 <= k < HOTBAR_SLOTS) or not self.hotbar[k]:
            return
        name = self.hotbar[k]
        e = next((i for i in self.inv if i.name == name), None)
        if e is None:
            self.display_message("You have no %s left." % pretty(name), "FAIL")
            return
        verbs = [v for v in self.get_verbs(e).split(",") if v and v not in ("Hotbar", "Off hotbar")]
        if verbs:
            self.do_action(verbs[0], e)

    def hotbar_label(self, k):
        name = self.hotbar[k]
        if not name:
            return "Hotbar slot %d|right-click an item in your inventory to put it here" % (k + 1)
        n = self.items_held(name)
        return "%s (%d)|%d or click: use it · right-click: take it off" % (pretty(name), n, k + 1)

    def draw_hotbar(self, scr):
        if self.ab_mode:
            return
        for k in range(HOTBAR_SLOTS):
            r = self.hotbar_rect(k)
            box = pygame.Surface(r.size, pygame.SRCALPHA)
            box.fill((24, 14, 8, 170))
            pygame.draw.rect(box, (214, 170, 70, 230), box.get_rect(), 1)
            scr.blit(box, r.topleft)
            name = self.hotbar[k]
            if name:
                sp = self.sprite_of(name)
                held = self.items_held(name)
                if sp:
                    img = sp.masked if held else self.greyed(sp)
                    scr.blit(img, (r.x + (r.w - sp.w) // 2, r.y + (r.h - sp.h) // 2))
                if held != 1:
                    self.draw_text(scr, str(held), r.right - 3 - self.text_width(str(held), 8, True), r.bottom - 11,
                                   8, True, (255, 240, 200) if held else (200, 90, 80))
            self.draw_text(scr, str(k + 1), r.x + 3, r.y + 1, 8, True, (214, 170, 70))

    def hotbar_load(self, section):
        self.hotbar_reset()
        d = dict(section)
        for k in range(HOTBAR_SLOTS):
            self.hotbar[k] = self.renamed(trim(d.get("Slot%d" % (k + 1), "")))

    def hotbar_save_lines(self):
        return ["", "[Hotbar]"] + ["Slot%d=%s" % (k + 1, n) for k, n in enumerate(self.hotbar) if n]
