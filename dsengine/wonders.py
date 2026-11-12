"""What happens in the world on its own, for those about in it (data\\Wonders.ini, dev/migrate/build_wonders.py; the owner's list):

  * Shard storms: a rare sky of wild magic. Remnants rise round whoever's out in it and Shard Remnants lie on the ground.
  * Ghost ships: a wreck at a port on a foggy night, its dead on the quay, its chest once a night each; gone by morning.
  * The Wandering Inn: somewhere else in the wild each day (the Inn_Spot_<n> places), its keeper knows too much.
  * Mimics: a villager who's slightly wrong (a misspelt name, never sleeps, a glint now and then). Accuse them and see.
  * Grudges: what survives a fight with you remembers. It comes looking, stronger; kill it and you've settled it.
  * The Tax Collector: an unkillable, polite man walking after anyone carrying too much gold.
  * The Champion: the arena's kills through each year's winter (seasons.py) crown one heir; a statue of them till the next.
  * Letters by carrier: /letter to a friend who's away, a courier finds them when they come in.

Who's here and what's owed is its own (saved with each character as attributes, or with the world: state()); what turns up is
for all to see, and never saved, as encounters.py's aren't."""
import logging
import random
import time

from ashen import ini
from ashen.lb import val, trim, distance

from .entity import NPC

log = logging.getLogger("ashen.wonders")
LOOK_EVERY = 1000
MOST_MAIL = 20
STORM_SKY = "shardstorm"


class Wonders:
    def __init__(self, world):
        self.w = world
        self.path = world.data.data_file("Wonders.ini")
        self.rng = random.Random()
        self.on = True                  # (off in the tests: nothing turning up in the middle of another's)
        self.looked = -10 ** 12
        self.storm_until = 0
        self.storm_next = None
        self.storm_drop = 0
        self.ship = None                # {"map", "ents": [...], "night": n}
        self.ship_night = None
        self.inn = None                 # {"day", "ents": [...]}
        self.mimic_next = None
        self.mimics = {}                # uid -> when it goes
        self.collectors = {}            # player name -> the entity
        self.couriers = {}              # player name -> the entity
        self.grudges = {}               # uid -> the player it's after
        self.mail = {}                  # lower name -> [{from, text, item, n}]
        self.champion = ""
        self.champion_year = -1
        self.scores = {}                # player name -> kills this tournament

    def setting(self, section, key, default=""):
        return ini.read(section, key, str(default), self.path)

    def num(self, section, key, default):
        return val(self.setting(section, key, default))

    # ----- saved with the world
    def state(self):
        return {"mail": self.mail, "champion": self.champion, "champion_year": self.champion_year, "scores": self.scores}

    def load(self, st):
        st = st or {}
        self.mail = {str(k): [dict(m) for m in v][:MOST_MAIL] for k, v in (st.get("mail") or {}).items() if isinstance(v, list)}
        self.champion = str(st.get("champion", ""))
        self.champion_year = int(val(st.get("champion_year", -1)))
        self.scores = {str(k): int(val(v)) for k, v in (st.get("scores") or {}).items()}

    def tick(self):
        w = self.w
        if 0 <= w.now - self.looked < LOOK_EVERY:
            return
        self.looked = w.now
        if not self.on or self.num("Wonders", "On", 1) != 1:
            return
        for job in (self.storm_tick, self.ship_tick, self.inn_tick, self.mimic_tick, self.tax_tick, self.grudge_tick,
                    self.courier_tick, self.champion_tick):
            job()

    def about(self):
        return [s for s in self.w.sessions.values() if s.in_world() and s.player.alive]

    def add(self, name, m, tx, ty, opts):
        w = self.w
        e = w.add_npc(name, m.mz, m.ox + (tx - 1) * w.tw, m.oy + (ty - 1) * w.th - 8, opts, home=m.name)
        if e is not None:
            e.source = "ENCOUNTER"
        return e

    def spot_for(self, s):
        return self.w.encounters.spot_near(s)

    def go(self, e):
        w = self.w
        if e is not None and e.alive:
            w.shard_fade(e)
            w.remove_entity(e)

    # ----- shard storms
    def in_storm(self):
        return self.w.now < self.storm_until

    def storm_tick(self):
        w = self.w
        if self.storm_next is None or w.now < self.storm_next - 86400000:
            self.storm_next = w.now + self.num("Storm", "Every.Minutes", 150) * 60000 * self.rng.uniform(0.6, 1.4)
        if not self.in_storm():
            if w.now >= self.storm_next and self.about():
                self.storm_next = None
                self.storm_start()
            return
        if w.now < self.storm_drop:
            return
        self.storm_drop = w.now + self.num("Storm", "Drop.Seconds", 12) * 1000
        for s in self.about():
            if s.player.z == 0 and w.encounters.free(s):
                self.storm_rains_on(s)

    def storm_start(self):
        w = self.w
        minutes = self.num("Storm", "Minutes", 6)
        self.storm_until = w.now + minutes * 60000
        if w.weather:
            w.weather.update(kind=STORM_SKY, next=self.storm_until, fading=False)
            w.weather_changed()
        for s in self.about():
            s.display_message(self.setting("Storm", "Message", "The air tastes of metal. Wild magic is coming down."), "WARNING")
            s.play_sound("Remnant_Rise")
        log.info("A shard storm")

    def storm_rains_on(self, s):
        w, p = self.w, s.player
        spot = self.spot_for(s)
        if spot is None:
            return
        m, tx, ty = spot
        x, y = m.ox + (tx - 1) * w.tw, m.oy + (ty - 1) * w.th
        w.drop_item("Shard", p.z, x, y, max(1, s.player_level() // 3))
        w.fx_anim("Shard_Form", p.z, x + 16, y + 16, 700)
        if s.get_attribute("Unmade") != "1" and self.rng.random() * 100 < self.num("Storm", "Rise.Chance", 35):   # (calmer once the Seam is unmade)
            e = self.add("Living_Remnant", m, tx, ty, "Attitude=Bad")
            if e is not None:
                from .remnants import make_remnant
                make_remnant(w.data, e, max(2, s.player_level()))
                e.fades_at = w.now + int(self.num("Storm", "Remnant.Seconds", 120) * 1000)
                w.shard_form(e)
                if e.ai is not None:
                    w.npc_start_fight(e, e.ai, s, 0)

    # ----- ghost ships
    def night_number(self):
        return int(self.w.now // (self.w.data.day_seconds * 1000 or 1))

    def ship_tick(self):
        w = self.w
        night = w.is_night()
        if self.ship is not None:
            if not night:
                for e in self.ship["ents"]:
                    if e.alive:
                        w.shard_fade(e) if e.type == NPC else None
                        w.remove_entity(e)
                self.ship = None
            return
        n = self.night_number()
        if not night or self.ship_night == n or not self.about():
            return
        self.ship_night = n
        foggy = bool(w.weather) and w.weather.get("kind") == "fog"
        if self.rng.random() * 100 < self.num("Ghost_Ship", "Foggy.Chance" if foggy else "Clear.Chance", 60 if foggy else 3):
            self.ship_comes(n)

    def ship_comes(self, n):
        w = self.w
        ports = [trim(v) for v in self.setting("Ghost_Ship", "Ports", "Northport_Port").split(",") if trim(v)]
        self.rng.shuffle(ports)
        for name in ports:
            pl = w.data.place(name)
            m = w.maps.get(pl.map) if pl else None
            if m is None:
                continue
            water = next(((x, y) for r in range(1, 14) for y in range(max(1, pl.ty - r), min(self.w.yt, pl.ty + r) + 1)
                          for x in range(max(1, pl.tx - r), min(self.w.xt, pl.tx + r) + 1)
                          if m.tile[m.cell(x, y)].startswith("Water")), None)
            if water is None:
                continue
            ship = w.add_static_object("Ghost_Ship", m.mz, m.ox + (water[0] - 1) * w.tw, m.oy + (water[1] - 1) * w.th, home=m.name)
            chest = w.add_static_object("Ghost_Chest", m.mz, m.ox + (pl.tx - 1) * w.tw, m.oy + (pl.ty - 1) * w.th, home=m.name)
            ents = [e for e in (ship, chest) if e is not None]
            for k in range(int(self.num("Ghost_Ship", "Dead", 4))):
                tx, ty = max(1, min(self.w.xt, pl.tx + self.rng.randint(-3, 3))), max(1, min(self.w.yt, pl.ty + self.rng.randint(-3, 3)))
                if not w.pixel_walkable(m.mz, m.ox + (tx - 0.5) * w.tw, m.oy + (ty - 0.5) * w.th):
                    continue
                d = self.add("Drowned_Sailor", m, tx, ty, "Attitude=Bad Zone=%d,%d,%d,%d" % (
                    max(1, tx - 3), max(1, ty - 3), min(self.w.xt, tx + 3), min(self.w.yt, ty + 3)))
                if d is not None:
                    w.shard_form(d)
                    ents.append(d)
            self.ship = {"map": m.name, "ents": ents, "night": n}
            log.info("A ghost ship at %s", name)
            for s in self.about():
                if s.player.z == 0 and distance(s.player.cx, s.player.cy, m.ox + pl.tx * w.tw, m.oy + pl.ty * w.th) < w.sw * 2:
                    s.display_message("A ship with no lights has come in out of the fog.", "INFO")
            return

    # ----- the Wandering Inn
    def inn_tick(self):
        w = self.w
        day = int(time.time() // 86400)
        if self.inn is not None and self.inn["day"] == day:
            return
        if self.inn is not None:
            for e in self.inn["ents"]:
                if e.alive:
                    w.remove_entity(e)
        spots = []
        n = 1
        while w.data.place("Inn_Spot_%d" % n):
            spots.append(w.data.place("Inn_Spot_%d" % n))
            n += 1
        self.inn = {"day": day, "ents": []}
        if not spots:
            return
        pl = spots[day % len(spots)]
        m = w.maps.get(pl.map)
        if m is None:
            return
        px, py = m.ox + (pl.tx - 1) * w.tw, m.oy + (pl.ty - 1) * w.th
        inn = w.add_static_object("Wandering_Inn", m.mz, px, py, home=m.name)
        table = w.add_static_object("Dice_Table", m.mz, px + 3 * w.tw, py + w.th, home=m.name)
        keeper = self.add("Wandering_Keeper", m, min(self.w.xt, pl.tx + 1), min(self.w.yt, pl.ty + 2), "Attitude=Good Stand=1 Face=S Schedule=Always Name=Hob")
        self.inn["ents"] = [e for e in (inn, table, keeper) if e is not None]

    # ----- mimics
    def mimic_tick(self):
        w = self.w
        for uid, ends in list(self.mimics.items()):
            e = w.by_uid.get(uid)
            if e is None or not e.alive:
                del self.mimics[uid]
            elif w.now >= ends:
                self.go(e)
                del self.mimics[uid]
        if self.mimic_next is None or w.now < self.mimic_next - 86400000:
            self.mimic_next = w.now + self.num("Mimic", "Every.Minutes", 25) * 60000 * self.rng.uniform(0.5, 1.5)
        if w.now < self.mimic_next:
            return
        self.mimic_next = None
        people = [s for s in self.about() if s.player.z == 0 and w.encounters.free(s) and w.encounters.settled(s.cur_map)]
        if not people or len(self.mimics) >= self.num("Mimic", "Most", 2):
            return
        s = self.rng.choice(people)
        spot = self.spot_for(s)
        if spot is None:
            return
        m, tx, ty = spot
        names = [v.strip() for v in self.setting("Mimic", "Names", "Viilager").split(",") if v.strip()]
        e = self.add("Mimic_Villager", m, tx, ty, "Attitude=Good Schedule=Always Pause=4-10 Name=%s Zone=%d,%d,%d,%d" % (
            self.rng.choice(names), max(1, tx - 6), max(1, ty - 5), min(self.w.xt, tx + 6), min(self.w.yt, ty + 5)))
        if e is not None:
            self.mimics[e.uid] = w.now + self.num("Mimic", "Minutes", 15) * 60000

    def mimic_caught(self, s, e):
        """They've called it what it is: it stops pretending."""
        w = self.w
        if e is None or not e.alive or e.name != "Mimic_Villager":
            return
        self.mimics.pop(e.uid, None)
        m = w.map_at(e.z, e.fx, e.fy)
        tx, ty = int((e.fx - m.ox) // w.tw) + 1, int((e.fy - m.oy) // w.th) + 1
        w.remove_entity(e)
        t = self.add("Mimic_Thing", m, tx, ty, "Attitude=Bad Chase=%d,%d,%d,%d" % (tx - 20, ty - 20, tx + 20, ty + 20))
        if t is None:
            return
        level = max(3, s.player_level())
        t.hp = t.max_hp = int(12 + level * 7)
        t.strength, t.defence = max(1, int(level * 0.7)), max(1, int(level * 0.7))
        w.shard_form(t)
        w.fx({"t": "bubble", "u": t.uid, "text": self.setting("Mimic", "Caught", "Oh. You noticed.")}, t.z, t.cx, t.cy)
        if t.ai is not None:
            w.npc_start_fight(t, t.ai, s, 0)

    # ----- grudges
    def grudge_noted(self, s, e):
        """e got away from s, or killed them: it remembers."""
        if e is None or e.type != NPC or getattr(e, "source", "") == "ENCOUNTER" or not getattr(e, "hostile", False):
            return
        if val(self.w.data.entity_ini(e.name, "Boss", "0")) >= 1 or trim(self.w.data.entity_ini(e.name, "Slain.By", "")):
            return
        s.update_attribute("Grudge.Kind", "=" + e.name)
        s.update_attribute("Grudge.Level", "=%d" % max(1, int(getattr(e, "npc_level", 0) or
                                                           val(self.w.data.entity_ini(e.name, "Level", "1")))))
        s.update_attribute("Grudge.At", "=%d" % int(time.time() + self.num("Grudge", "After.Minutes", 30) * 60))

    def grudge_tick(self):
        w = self.w
        for uid, name in list(self.grudges.items()):
            e = w.by_uid.get(uid)
            if e is None or not e.alive:
                del self.grudges[uid]
        now = time.time()
        for s in self.about():
            at = val(s.get_attribute("Grudge.At"))
            if at <= 0 or now < at or s.player_name in self.grudges.values() or not w.encounters.free(s):
                continue
            kind = str(s.get_attribute("Grudge.Kind") or "")
            spot = self.spot_for(s)
            if not kind or spot is None:
                continue
            s.update_attribute("Grudge.At", "=%d" % int(now + self.num("Grudge", "Again.Minutes", 15) * 60))
            m, tx, ty = spot
            times = int(val(s.get_attribute("Grudge.Times"))) + 1
            level = max(1, int(val(s.get_attribute("Grudge.Level")))) + times     # (a level up on the one that got you)
            e = self.add(kind, m, tx, ty, "Attitude=Bad Chase=%d,%d,%d,%d Name=Scarred_%s Level=%d" % (
                tx - 24, ty - 21, tx + 24, ty + 21, kind, min(25, level)))
            if e is None:
                continue
            s.update_attribute("Grudge.Times", "=%d" % times)
            grow = 1 + self.num("Grudge", "Stronger", 0.25) * times
            e.hp = e.max_hp = int(e.max_hp * grow)
            e.strength, e.defence = int(e.strength * grow) + 1, int(e.defence * grow) + 1
            self.grudges[e.uid] = s.player_name
            w.fx({"t": "bubble", "u": e.uid, "text": self.setting("Grudge", "Says", "You. I remember you.")}, e.z, e.cx, e.cy)
            s.display_message("Something's been following your trail.", "WARNING")
            if e.ai is not None:
                w.npc_start_fight(e, e.ai, s, 0)

    def grudge_settled(self, s, e):
        if self.grudges.pop(e.uid, None) is None:
            return
        s.update_attribute("Grudge.At", "=0")
        s.update_attribute("Grudge.Times", "=0")
        s.give_shards(int(self.num("Grudge", "Reward.Shards", 15)), "That's settled")

    # ----- the Tax Collector
    def tax_due(self, s):
        return max(1, int(s.items_held("Gold_Coin(s)") * self.num("Tax", "Percent", 5) / 100))

    def tax_tick(self):
        w = self.w
        most = self.num("Tax", "Gold", 5000)
        for name, e in list(self.collectors.items()):
            s = w.sessions.get(name)
            if s is None or not s.in_world() or not e.alive or s.items_held("Gold_Coin(s)") < most:
                self.collectors.pop(name, None)
                self.go(e)
            elif self.rng.random() < 0.015:
                said = [v.strip() for v in self.setting("Tax", "Says", "A moment of your time?").split("|")]
                w.fx({"t": "bubble", "u": e.uid, "text": self.rng.choice(said)}, e.z, e.cx, e.cy)
        for s in self.about():
            if s.player_name in self.collectors or s.items_held("Gold_Coin(s)") < most or not w.encounters.free(s):
                continue
            if time.time() < val(s.get_attribute("Tax.Paid")) + self.num("Tax", "Rest.Minutes", 60) * 60:
                continue
            spot = self.spot_for(s)
            if spot is None:
                continue
            m, tx, ty = spot
            e = self.add("Tax_Collector", m, tx, ty, "Attitude=Good Schedule=Always Name=Mr._Pennyworth")
            if e is not None:
                e.follow = s
                self.collectors[s.player_name] = e

    def tax_paid(self, s):
        due = self.tax_due(s)
        s.remove_inventory_item("Gold_Coin(s)", due)
        s.update_attribute("Tax.Paid", "=%d" % int(time.time()))
        e = self.collectors.pop(s.player_name, None)
        if e is not None:
            self.w.fx({"t": "bubble", "u": e.uid, "text": "Most obliged. Good day to you."}, e.z, e.cx, e.cy)
            self.go(e)

    # ----- letters
    def send_letter(self, s, to, text):
        """A letter from s to their friend: at most one thing in it (+Item_Name first). True if it's on its way."""
        w = self.w
        who = next((n for n in (s.w.together.friends.get(s.player_name) or []) if n.lower() == to.lower()), None)
        if who is None:
            s.refuse("You can only send a letter to a friend.")
            return False
        box = self.mail.setdefault(who.lower(), [])
        if len(box) >= MOST_MAIL:
            s.refuse("%s's letters are piling up as it is." % who)
            return False
        item, n, went, words = "", 0, [], text.strip()
        if words.startswith("+"):
            first, _, words = words.partition(" ")
            item = first[1:]
            # (only something in the pack: Shards are a balance, never sent)
            if not any(e.name == item for e in s.inv) or val(s.entity_ini(item, "Droppable", "1")) == 0:
                s.refuse("You haven't got that to send.")
                return False
            n = 1
            went = s.remove_inventory_item(item, 1)     # (as it was: its wear, stolen or not)
        box.append({"from": s.player_name, "text": words[:300], "item": item, "n": n, "went": went})
        s.display_message("Your letter to %s is on its way." % who, "SUCCESS")
        return True

    def courier_tick(self):
        w = self.w
        for name, e in list(self.couriers.items()):
            s = w.sessions.get(name)
            if s is None or not s.in_world() or not e.alive or not self.mail.get(name.lower()):
                self.couriers.pop(name, None)
                self.go(e)
        for s in self.about():
            if s.player_name in self.couriers or not self.mail.get(s.player_name.lower()) or not w.encounters.free(s):
                continue
            spot = self.spot_for(s)
            if spot is None:
                continue
            m, tx, ty = spot
            e = self.add("Courier", m, tx, ty, "Attitude=Good Schedule=Always Name=Courier")
            if e is not None:
                e.follow = s
                self.couriers[s.player_name] = e
                w.fx({"t": "bubble", "u": e.uid, "text": "Letter for %s!" % s.player_name}, e.z, e.cx, e.cy)

    def take_letters(self, s):
        """The courier hands over everything for s."""
        box = self.mail.pop(s.player_name.lower(), [])
        for m in box:
            s.display_message("A letter from %s: %s" % (m.get("from", "someone"), m.get("text", "")), "INFO")
            if m.get("item"):
                s.put_items(m["item"], [tuple(p) for p in m.get("went") or [(int(val(m.get("n", 1))) or 1, 0, False)]])
        return len(box)

    # ----- the Champion
    def tourney_on(self):
        return self.w.seasons.current() == "Winter"

    def year(self):
        return int(self.w.now // self.w.seasons.year_ms())

    def arena_kill(self, s):
        if self.tourney_on():
            self.scores[s.player_name] = self.scores.get(s.player_name, 0) + 1

    def champion_tick(self):
        y = self.year()
        if self.champion_year == y or self.w.seasons.current() != "Spring":
            return
        self.champion_year = y
        if not self.scores:
            return
        best = max(self.scores, key=lambda k: self.scores[k])
        self.champion = best
        self.scores = {}
        log.info("%s is the year's champion", best)
        for s in self.about():
            s.display_message("%s has won the year's crown in the arena! Their statue stands in Galaith." % best, "ACHIEVEMENT")
