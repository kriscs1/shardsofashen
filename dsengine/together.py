"""Playing alone or together (dev\\Roadmap.md group 15). Every story moment is yours; the world round it is everyone's.

  Parties     Invite a player (right-click them); in a party, a kill counts for every member near, a quest stage
              one of you reaches is reached by the others near at that same stage (and the quest's own things they're
              given come to them too), and /p talks to the party. Up to Party.Size (Config [Together]).
  Scaling     A boss (Entities.ini Boss=1) grows tougher for each player fighting it; a raid sends more for each
              player there (waves.py). One player alone still wins at the base numbers.
  Gifts       Use an item on another player: they're offered it, and take it or not.
  Projects    data\\Projects.ini: a town's foreman takes donations (materials and gold) from anyone; when it's full
              the town changes for everyone (what has Project=<Key> on its map line appears; a perk). The plaque names
              who gave most.
  The crier   tells what's going on (raids, projects, the arena's champion); the bounty clerk sets a hunt a day; the
              record keeper keeps the records (kills, secrets, arena wins); a homestead's Pocket Anchor keeps a
              guestbook and a gift box; and on a return after a day away, what happened while you were gone.
  Friends     Add a player as a friend (right-click them, or /friend Name): the journal's Friends page shows who's
              about and where, with Whisper and Invite; you're told when a friend comes or goes; and your homestead's
              "friends" are yours (kept with the world, so it knows them while you're away).
  Trading     Trade with a player (right-click them): each puts in things and gold, both accept, and they change
              hands at once. A change undoes both accepts.
  Companions  Jimmy follows the crowned heir about (a cat: he finds secrets); a sellsword can be hired for a while.
              They step aside when a real player in your party is near.
  Greetings   Townsfolk greet the crowned heir, and a town you saved from a raid thanks you, now and then."""
import random
import time

from ashen.lb import val, trim, lbstr, distance, pretty
from ashen import ini

from .entity import NPC, PLAYER, STATICOBJECT, INVENTORYITEM

PROJECTS = "Projects.ini"
BOUNTIES = ["Wolf", "Goblin", "Bandit", "Skeleton", "Giant_Spider", "Bear", "Hobgoblin", "Scorpion", "Rat", "Bat"]


def today():
    return int(time.strftime("%Y%m%d"))


class Together:
    """The shared side, kept with the world: the towns' projects, everyone's records, homesteads' guests and gifts."""

    def __init__(self, w):
        self.w = w
        self.projects = {}          # key -> {"have": {item: n}, "givers": {name: worth}, "done_at": seconds or 0}
        self.records = {}           # name -> {"Kills": n, "SecretsFound": n, "ArenaWins": n, "Deep": n}
        self.guests = {}            # owner -> [[name, seconds]] (the newest last)
        self.gifts = {}             # owner -> [[from, item, n]]
        self.friends = {}           # name -> [names] (kept with the world: a homestead knows them while you're away)
        self.parties = {}           # id -> [names] (not saved: a party lasts while its people play)
        self.next_party = 1

    def defs(self):
        out = {}
        for key, items in ini.sections(self.w.data.data_file(PROJECTS)):
            kv = {k.upper(): trim(v) for k, v in items}
            needs = {}
            for part in kv.get("NEEDS", "").split(","):
                bits = part.split()
                if len(bits) == 2:
                    needs[bits[0]] = int(val(bits[1]))
            maps = [int(val(v)) for v in kv.get("MAPS", "").split(",") if v.strip()]
            out[key] = {"key": key, "title": kv.get("TITLE", pretty(key)), "town": kv.get("TOWN", ""),
                        "needs": needs, "perk": kv.get("PERK", "").upper(), "maps": maps if len(maps) == 4 else None}
        return out

    def project(self, key):
        return self.projects.setdefault(key, {"have": {}, "givers": {}, "done_at": 0})

    def done(self, key):
        return bool(self.projects.get(key, {}).get("done_at"))

    def perk(self, kind, map_name):
        """Is a project with this perk done for this map (its Maps=x1,y1,x2,y2)? FREETRAVEL: a shardstone there is
        free to come to; RESTOCK: its shops restock twice as fast."""
        try:
            mx, my = (int(v) for v in map_name.split(",")[:2])
        except ValueError:
            return False
        for k, d in self.defs().items():
            r = d["maps"]
            if d["perk"] == kind and r and r[0] <= mx <= r[2] and r[1] <= my <= r[3] and self.done(k):
                return True
        return False

    def state(self):
        return {"projects": self.projects, "records": self.records, "guests": self.guests, "gifts": self.gifts,
                "friends": self.friends}

    def load(self, st):
        st = st or {}
        self.projects = dict(st.get("projects", {}))
        self.records = dict(st.get("records", {}))
        self.guests = dict(st.get("guests", {}))
        self.gifts = dict(st.get("gifts", {}))
        self.friends = {k: list(v) for k, v in st.get("friends", {}).items()}

    def friends_of(self, name):
        return self.friends.get(name, [])


class TogetherMixin:
    def tg_num(self, key, default):
        v = trim(self.data.config_read("Together", key, "")) if hasattr(self.data, "config_read") else ""
        return val(v) if v else default

    # ================================================================================================= parties
    def party_names(self):
        pid = getattr(self, "party_id", 0)
        return list(self.w.together.parties.get(pid, [])) if pid else []

    def party_members(self, near=False):
        """The others in your party who are playing (near: on your level, within a map of you)."""
        out = []
        p = self.player
        for n in self.party_names():
            o = self.w.sessions.get(n)
            if o is None or o is self or not o.in_world():
                continue
            if near and (o.player.z != p.z or abs(o.player.cx - p.cx) > self.w.sw or abs(o.player.cy - p.cy) > self.w.sh):
                continue
            out.append(o)
        return out

    def party_near(self, e):
        """The names of your party near e (a kill counts for them too: player_combat.helpers_of)."""
        return [o.player_name for o in self.party_members() if o.player.z == e.z and
                abs(o.player.cx - e.cx) < self.w.sw and abs(o.player.cy - e.cy) < self.w.sh]

    def party_say(self, text, kind="INFO"):
        for o in [self] + self.party_members():
            o.display_message(text, kind)

    def invite(self, other):
        if other is None or other is self or not other.in_world():
            return
        if other.player_name in self.party_names():
            self.refuse("%s is in your party already." % other.player_name)
            return
        if getattr(other, "party_id", 0):
            self.refuse("%s is in a party already." % other.player_name)
            return
        if len(self.party_names()) >= self.tg_num("Party.Size", 5):
            self.refuse("Your party is full.")
            return
        me = self
        other.show_menu("Party", self.player.image, "%s asks you to join their party: kills and quest stages shared "
                        "with those of you near each other, and /p to talk to the party." % self.player_name,
                        [("Join %s." % self.player_name, lambda: other.join_party(me)), ("No, thank you.", None)])
        self.display_message("You ask %s to join your party." % other.player_name, "INFO")
        self.act_done(True)

    def join_party(self, leader):
        t = self.w.together
        if not leader.in_world() or getattr(self, "party_id", 0):
            return
        pid = getattr(leader, "party_id", 0)
        if not pid:
            pid = t.next_party
            t.next_party += 1
            t.parties[pid] = [leader.player_name]
            leader.party_id = pid
        if len(t.parties[pid]) >= self.tg_num("Party.Size", 5):
            self.refuse("That party is full now.")
            return
        t.parties[pid].append(self.player_name)
        self.party_id = pid
        self.play_sound("Quest")
        self.party_say("%s has joined the party (%s)." % (self.player_name, ", ".join(t.parties[pid])), "SUCCESS")
        for o in [self] + self.party_members():
            o.dirty_me = True
            o.companions_step_aside()

    def leave_party(self, quiet=False):
        t = self.w.together
        pid = getattr(self, "party_id", 0)
        if not pid:
            return
        names = t.parties.get(pid, [])
        if self.player_name in names:
            names.remove(self.player_name)
        self.party_id = 0
        self.dirty_me = True
        if not quiet:
            self.display_message("You have left the party.", "INFO")
        for n in list(names):
            o = self.w.sessions.get(n)
            if o is not None:
                o.display_message("%s has left the party." % self.player_name, "INFO")
                o.dirty_me = True
        if len(names) <= 1:
            for n in names:
                o = self.w.sessions.get(n)
                if o is not None:
                    o.party_id = 0
                    o.display_message("The party has broken up.", "INFO")
            t.parties.pop(pid, None)

    def party_state(self):
        return {"party": self.party_names(), "party_id": getattr(self, "party_id", 0), "friends": self.friend_names()}

    # ----- quest sync: a stage you reach, reached by your party near you at that same stage
    def quest_attribute(self, name):
        cache = self.data.cache("quest_attrs")
        if not cache:
            for key, items in ini.sections(self.data.data_file("Quests.ini")):
                a = trim(dict((k.upper(), v) for k, v in items).get("ATTRIBUTE", ""))
                if a:
                    cache[a.upper()] = True
            cache["_"] = True
        return name.upper() in cache

    def quest_sync(self, name, change, old):
        """After this player's script changed a quest's attribute from old: the same for each party member near who
        stood at old too. Returns who (the script's quest things go to them as well: sync_give)."""
        if not self.party_names() or not self.quest_attribute(name):
            return []
        moved = []
        for o in self.party_members(near=True):
            if o.get_attribute(name) == old and not o.script_running:
                o.update_attribute(name, change)
                o.display_message("Your party moves on together: %s." % self.quest_title_of(name), "SUCCESS")
                moved.append(o)
        if moved:
            synced = getattr(self, "synced_now", None)
            if synced is None:
                synced = self.synced_now = []
            synced += [o for o in moved if o not in synced]
        return moved

    def quest_title_of(self, attr):
        for key, items in ini.sections(self.data.data_file("Quests.ini")):
            d = {k.upper(): v for k, v in items}
            if trim(d.get("ATTRIBUTE", "")).upper() == attr.upper():
                return trim(d.get("TITLE", "")) or pretty(key)
        return pretty(attr)

    def sync_give(self, item, n):
        """A quest's own thing given in this script (one that can't be dropped): to the party who moved on with you."""
        if trim(self.data.entity_ini(item, "Droppable", "1")) != "0":
            return
        for o in getattr(self, "synced_now", None) or []:
            if o.in_world() and o.items_held(item) <= 0:
                o.add_inventory_item(item, n)

    # ================================================================================================= friends
    def friend_names(self):
        return self.w.together.friends_of(self.player_name)

    def add_friend_named(self, name):
        name = trim(name)
        known = self.known_player(name)
        if not known or known == self.player_name:
            self.refuse("There's nobody called %s." % name if not known else "You're your own friend already.")
            return
        mine = self.w.together.friends.setdefault(self.player_name, [])
        if known in mine:
            self.display_message("%s is your friend already." % known, "INFO")
            return
        if len(mine) >= 100:
            self.refuse("Your friends list is full.")
            return
        mine.append(known)
        h = self.homes.home_of(self.player_name)
        if h is not None and known not in h["friends"]:
            h["friends"].append(known)                 # (your homestead's friends are your friends)
        self.display_message("%s is your friend now." % known, "SUCCESS")
        o = self.w.sessions.get(known)
        if o is not None:
            o.display_message("%s has made you a friend." % self.player_name, "INFO")
        self.dirty_me = True

    def remove_friend_named(self, name):
        mine = self.w.together.friends.get(self.player_name, [])
        known = next((n for n in mine if n.lower() == trim(name).lower()), None)
        if known is None:
            return
        mine.remove(known)
        h = self.homes.home_of(self.player_name)
        if h is not None and known in h["friends"]:
            h["friends"].remove(known)
        self.display_message("%s is no longer on your friends list." % known, "INFO")
        self.dirty_me = True

    def known_player(self, name):
        """A player's name as it's written (someone playing, or anyone the world has records of), or ""."""
        low = trim(name).lower()
        for n in list(self.w.sessions) + list(self.w.together.records):
            if n.lower() == low:
                return n
        return ""

    def friends_rows(self):
        """For the journal's Friends page: each friend, whether they're about, where, their level."""
        out = []
        for n in self.friend_names():
            o = self.w.sessions.get(n)
            on = o is not None and o.in_world()
            out.append({"name": n, "on": 1 if on else 0, "where": self.where_words(o) if on else "",
                        "level": o.player_level() if on else self.w.together.records.get(n, {}).get("Level", 0),
                        "party": 1 if n in self.party_names() else 0})
        return sorted(out, key=lambda r: (-r["on"], r["name"].lower()))

    def towns_at(self):
        """[(title, global x, global y)] of the world map's towns (WorldMap.ini [Towns]), worked out once."""
        got = getattr(self.w, "_towns_at", None)
        if got is None:
            got = []
            for title, pid in ini.section("Towns", self.data.data_file("WorldMap.ini")):
                pl = self.data.place(trim(pid))
                m = self.w.map_named(pl.map) if pl is not None else None
                if m is not None and m.mz == 0:
                    got.append((title, m.ox + pl.px, m.oy + pl.py))
            self.w._towns_at = got
        return got

    def where_words(self, o):
        """Where another player is, in words: in or near a town, out in the wilds, underground, at a homestead."""
        p = o.player
        m = o.cur_map
        if m is not None and self.homes.is_home_map(m.name):
            return "at a homestead"
        if p.z < 0:
            return "underground"
        if p.z > 0:
            return "indoors"
        best = min(((abs(x - p.cx) + abs(y - p.cy), t) for t, x, y in self.towns_at()), default=None)
        if best is None:
            return "in Ashen"
        d, title = best
        if d < self.w.sw * 1.2:
            return "in " + title
        if d < self.w.sw * 3:
            return "near " + title
        return "in the wilds"

    def friends_hear(self, words):
        """Your friends who are playing are told (you've come, you've gone)."""
        for o in self.w.sessions.values():
            if o is not self and o.in_world() and self.player_name in o.friend_names():
                o.display_message(words, "INFO")

    def records_rows(self):
        """For the journal's Records page: the top three of each record, and yours."""
        self.note_records()
        recs = self.w.together.records
        rows = []
        for key, words in self.RECORDS:
            top = sorted(((r.get(key, 0), n) for n, r in recs.items() if r.get(key, 0)), reverse=True)[:3]
            rows.append({"key": key, "words": words, "top": [[n, v] for v, n in top],
                         "mine": recs.get(self.player_name, {}).get(key, 0)})
        return rows

    # ================================================================================================= trading
    TRADE_REACH = 192

    def tradeable(self, name):
        """Gold, and anything that can be dropped (not a quest's own thing)."""
        return name == "Gold_Coin(s)" or trim(self.data.entity_ini(name, "Droppable", "1")) != "0"

    def trade_other(self):
        tr = getattr(self, "trade", None)
        if not tr:
            return None
        return tr["b"] if tr["a"] is self else tr["a"]

    def trade_ask(self, o):
        if getattr(self, "trade", None) or getattr(o, "trade", None):
            self.refuse("One of you is trading already.")
            return
        if distance(self.player.cx, self.player.cy, o.player.cx, o.player.cy) > self.TRADE_REACH:
            self.refuse("You need to be nearer to trade.")
            return
        me = self
        o.show_menu("Trade", self.player.image, "%s would like to trade with you." % self.player_name,
                    [("Trade with %s." % self.player_name, lambda: o.trade_open(me)), ("No, thank you.", None)])
        self.display_message("You ask %s to trade." % o.player_name, "INFO")
        self.act_done(True)

    def trade_open(self, asker):
        if not asker.in_world() or getattr(self, "trade", None) or getattr(asker, "trade", None):
            return
        tr = {"a": asker, "b": self, "offer": {asker.player_name: {}, self.player_name: {}},
              "ok": {asker.player_name: False, self.player_name: False}}
        self.trade = asker.trade = tr
        self.trade_send()

    def trade_send(self):
        tr = getattr(self, "trade", None)
        if not tr:
            return
        for s in (tr["a"], tr["b"]):
            o = tr["b"] if tr["a"] is s else tr["a"]
            mine, theirs = tr["offer"][s.player_name], tr["offer"][o.player_name]
            stock = {}
            for it in s.inv:
                if self.tradeable(it.name):
                    stock[it.name] = stock.get(it.name, 0) + max(1, it.quantity)
            s.emit({"t": "trade", "open": True, "with": o.player_name,
                    "mine": sorted(mine.items()), "theirs": sorted(theirs.items()),
                    "ok": tr["ok"][s.player_name], "their_ok": tr["ok"][o.player_name],
                    "stock": sorted([n, q - mine.get(n, 0)] for n, q in stock.items() if q - mine.get(n, 0) > 0)})

    def trade_close(self, words=""):
        tr = getattr(self, "trade", None)
        if not tr:
            return
        for s in (tr["a"], tr["b"]):
            s.trade = None
            s.emit({"t": "trade", "open": False})
            if words:
                s.display_message(words, "INFO")

    def trade_msg(self, msg):
        """The trade window: add (item, n), take back (item), accept, cancel. Any change undoes both accepts."""
        tr = getattr(self, "trade", None)
        if not tr:
            return
        do = str(msg.get("do", ""))
        mine = tr["offer"][self.player_name]
        if do == "cancel":
            self.trade_close("The trade is off.")
            return
        if do == "add":
            name = str(msg.get("item", ""))
            n = int(val(msg.get("n", 1)))
            left = self.items_held(name) - mine.get(name, 0)
            if n <= 0 or left <= 0 or not self.tradeable(name):
                return
            mine[name] = mine.get(name, 0) + min(n, left)
        elif do == "back":
            mine.pop(str(msg.get("item", "")), None)
        elif do == "accept":
            tr["ok"][self.player_name] = True
            if all(tr["ok"].values()):
                self.trade_finish()
                return
            self.trade_send()
            return
        else:
            return
        for k in tr["ok"]:
            tr["ok"][k] = False                         # (changed: both look again)
        self.trade_send()

    def trade_finish(self):
        tr = self.trade
        a, b = tr["a"], tr["b"]
        oa, ob = tr["offer"][a.player_name], tr["offer"][b.player_name]
        for s, give in ((a, oa), (b, ob)):
            if any(s.items_held(n) < q for n, q in give.items()):
                self.trade_close("The trade is off: something offered isn't there now.")
                return
        for s, get in ((a, ob), (b, oa)):
            if any(s.inventory_slots_available(n) < q and n != "Gold_Coin(s)" for n, q in get.items()):
                self.trade_close("The trade is off: %s hasn't the room." % s.player_name)
                return
        for n, q in oa.items():
            a.remove_inventory_item(n, q)
        for n, q in ob.items():
            b.remove_inventory_item(n, q)
        for n, q in ob.items():
            a.add_inventory_item(n, q)
        for n, q in oa.items():
            b.add_inventory_item(n, q)
        for s in (a, b):
            s.play_sound("Coins")
        self.trade_close("The trade is done.")

    def trade_tick(self):
        o = self.trade_other()
        if o is not None and (not o.in_world() or o.player.z != self.player.z or
                              distance(self.player.cx, self.player.cy, o.player.cx, o.player.cy) > self.TRADE_REACH * 1.5):
            self.trade_close("The trade is off: you've moved apart.")

    # ================================================================================================= scaling
    def boss_scale(self, e):
        """A boss grows tougher for each player fighting it (Entities.ini Boss=1): Boss.Per.Player more health each."""
        if trim(self.data.entity_ini(e.name, "Boss", "0")) != "1":
            return
        fighters = sum(1 for t in (getattr(e, "fought_by", None) or {}).values() if self.now - t <= 60000)
        per = self.tg_num("Boss.Per.Player", 0.6)
        want = 1 + per * max(0, fighters - 1)
        have = getattr(e, "scaled", 1.0)
        if want > have:
            base = getattr(e, "base_hp", e.max_hp)
            e.base_hp = base
            new = int(base * want)
            e.hp = min(new, e.hp + (new - e.max_hp))
            e.max_hp = new
            e.scaled = want

    # ================================================================================================= gifts
    def offer_gift(self, item, other):
        if other is None or other is self or not other.in_world() or item is None:
            return
        if distance(self.player.cx, self.player.cy, other.player.cx, other.player.cy) > 96:
            self.refuse("You need to be beside them to hand something over.")
            return
        if not self.tradeable(item.name):
            self.refuse("That's not something you can give away.")
            return
        n = max(1, self.items_held(item.name))           # (all you carry of it, stacked or not)
        if n > 1:
            opts = [("All %d." % n, lambda: self.offer_gift_n(item.name, n, other)),
                    ("Half (%d)." % max(1, n // 2), lambda: self.offer_gift_n(item.name, max(1, n // 2), other)),
                    ("One.", lambda: self.offer_gift_n(item.name, 1, other)), ("Never mind.", None)]
            self.show_menu("A gift", item.name, "How many %s for %s?" % (pretty(item.name), other.player_name), opts)
            return
        self.offer_gift_n(item.name, 1, other)

    def offer_gift_n(self, name, n, other):
        me = self
        what = "%d gold" % n if name == "Gold_Coin(s)" else "%s%s" % ("%d " % n if n > 1 else "", pretty(name))
        other.show_menu("A gift", name, "%s offers you %s." % (self.player_name, what),
                        [("Take it, with thanks.", lambda: other.take_gift(me, name, n)), ("No, thank you.", None)])
        self.display_message("You offer %s %s." % (other.player_name, what), "INFO")

    def take_gift(self, giver, name, n):
        if not giver.in_world() or giver.items_held(name) < n:
            self.refuse("It isn't theirs to give now.")
            return
        if distance(self.player.cx, self.player.cy, giver.player.cx, giver.player.cy) > 128:
            self.refuse("They've walked off.")
            return
        if self.inventory_slots_available(name) <= 0:
            self.refuse("You don't have enough room in your inventory!")
            return
        giver.remove_inventory_item(name, n)
        self.add_inventory_item(name, n)
        self.play_sound("Coins" if name == "Gold_Coin(s)" else "Pickup")
        giver.display_message("%s takes your gift." % self.player_name, "SUCCESS")

    # ================================================================================================= projects
    def project_of_foreman(self, e):
        pid = (getattr(e, "npc_id", "") or "")
        if not pid.startswith("Foreman_"):
            return None
        return self.w.together.defs().get(pid[len("Foreman_"):])

    def foreman_menu(self, d):
        t = self.w.together
        pr = t.project(d["key"])
        if t.done(d["key"]):
            top = sorted(pr["givers"].items(), key=lambda kv: -kv[1])[:3]
            self.show_menu(d["title"], "Clerk", "%s is finished, thanks to everyone who gave. Most of all: %s." %
                           (d["title"], ", ".join(n for n, _ in top) or "the town"), [("Good.", None)])
            return
        lines = []
        for item, need in d["needs"].items():
            have = pr["have"].get(item, 0)
            lines.append("%s %d of %d" % ("gold" if item == "Gold_Coin(s)" else pretty(item), min(have, need), need))
        opts = []
        for item, need in d["needs"].items():
            left = need - pr["have"].get(item, 0)
            mine = self.items_held(item)
            if left > 0 and mine > 0:
                if item == "Gold_Coin(s)":
                    for amt in (10, 100):
                        if mine >= amt and left >= amt:
                            opts.append(("Give %d gold." % amt, lambda a=amt: self.donate(d, "Gold_Coin(s)", a)))
                    opts.append(("Give all the gold I can (%d)." % min(mine, left),
                                 lambda a=min(mine, left): self.donate(d, "Gold_Coin(s)", a)))
                else:
                    opts.append(("Give my %s (%d)." % (pretty(item), min(mine, left)),
                                 lambda i=item, a=min(mine, left): self.donate(d, i, a)))
        opts.append(("Not now.", None))
        self.show_menu(d["title"], "Clerk", "We're putting %s right, for everyone, with whatever folk can spare. So "
                       "far: %s." % (d["title"], "; ".join(lines)), opts[:9])

    def donate(self, d, item, n):
        t = self.w.together
        pr = t.project(d["key"])
        left = d["needs"].get(item, 0) - pr["have"].get(item, 0)
        n = min(n, left, self.items_held(item))
        if n <= 0 or t.done(d["key"]):
            return
        self.remove_inventory_item(item, n)
        pr["have"][item] = pr["have"].get(item, 0) + n
        worth = n if item == "Gold_Coin(s)" else n * max(1, int(val(self.data.entity_ini(item, "Value", "1"))))
        pr["givers"][self.player_name] = pr["givers"].get(self.player_name, 0) + worth
        self.play_sound("Coins" if item == "Gold_Coin(s)" else "Build" if self.data.loaded("Build") else "Pickup")
        self.display_message("You give %s to %s. Thank you!" % ("%d gold" % n if item == "Gold_Coin(s)" else
                                                                 "%d %s" % (n, pretty(item)), d["title"]), "SUCCESS")
        if all(pr["have"].get(i, 0) >= need for i, need in d["needs"].items()):
            pr["done_at"] = int(time.time())
            for s in self.w.sessions.values():
                if s.in_world():
                    s.display_message("%s is finished! The town has changed." % d["title"], "QUEST")
                    s.play_sound("Quest")
                    s.dirty_me = True
            for e in self.w.ents:                         # (what it built: shown to everyone now)
                if getattr(e, "project", "") == d["key"]:
                    e.active = True
            self.w._shardstones = None                    # (a new shardstone among them: worked out again)

    def plaque_text(self, key):
        t = self.w.together
        d = t.defs().get(key)
        if d is None:
            return ""
        top = sorted(t.project(key)["givers"].items(), key=lambda kv: -kv[1])[:5]
        return "%s, raised by the people of Ashen. Most given by: %s." % (d["title"], ", ".join(n for n, _ in top) or
                                                                          "many hands")

    # ================================================================================================= the crier
    def crier_news(self):
        w, t = self.w, self.w.together
        news = []
        for name, r in list(getattr(w.waves, "running", {}).items())[:2]:
            news.append("Raiders at %s! Every blade is wanted." % pretty(r.get("def", {}).get("title", name)))
        for key, d in t.defs().items():
            pr = t.project(key)
            if t.done(key):
                if time.time() - pr["done_at"] < 7 * 86400:
                    news.append("%s is finished, thanks to the town's good folk." % d["title"])
            else:
                total = sum(d["needs"].values()) or 1
                have = sum(min(pr["have"].get(i, 0), n) for i, n in d["needs"].items())
                if have:
                    news.append("%s is %d parts in a hundred done. The foreman wants more hands." %
                                (d["title"], have * 100 // total))
        best = max(t.records.items(), key=lambda kv: kv[1].get("ArenaWins", 0), default=None)
        if best and best[1].get("ArenaWins", 0):
            news.append("%s is the arena's champion, with %d wins." % (best[0], best[1]["ArenaWins"]))
        others = [n for n, s in w.sessions.items() if s is not self and s.in_world()]
        if others:
            news.append("Other heirs abroad today: %s." % ", ".join(sorted(others)[:4]))
        return news or ["All quiet in Ashen today. Quiet as a mouse in a cat's dream."]

    def crier_menu(self):
        news = self.crier_news()
        self.show_menu("The town crier", "Villager", "Hear ye! " + " ".join(news[:4]), [("Thank you.", None)])

    # ================================================================================================= bounties
    def bounty_today(self):
        d = today()
        rng = random.Random(d)
        return rng.choice(BOUNTIES), rng.randint(5, 9), d

    def clerk_menu(self):
        kind, n, day = self.bounty_today()
        got_day = int(val(self.get_attribute("Bounty.Day")))
        got = int(val(self.get_attribute("Bounty.Got")))
        if int(val(self.get_attribute("Bounty.Paid"))) == day:
            self.show_menu("Bounties", "Clerk", "You've had today's bounty. Come back tomorrow: there's always "
                           "something with too many teeth.", [("Goodbye.", None)])
        elif got_day == day and got >= n:
            gold, shards = 40 + n * 6, 3 + n // 2
            self.update_attribute("Bounty.Paid", "=%d" % day)
            self.add_inventory_item("Gold_Coin(s)", gold)
            self.give_shards(shards, "the bounty")
            self.play_sound("Coins")
            self.show_menu("Bounties", "Clerk", "%d %s, as asked. Here's your bounty: %d gold and %d Shards." %
                           (n, pretty(kind).lower() + "s", gold, shards), [("Thank you.", None)])
        elif got_day == day:
            self.show_menu("Bounties", "Clerk", "%s: %d of %d so far. Keep at it." % (pretty(kind) + "s", got, n),
                           [("I will.", None)])
        else:
            self.show_menu("Bounties", "Clerk", "Today's bounty: %d %s, anywhere in Ashen. Gold and Shards when "
                           "it's done. One a day." % (n, pretty(kind).lower() + "s"),
                           [("I'll take it.", lambda: self.take_bounty(day)), ("Not today.", None)])

    def take_bounty(self, day):
        self.update_attribute("Bounty.Day", "=%d" % day)
        self.update_attribute("Bounty.Got", "=0")
        self.display_message("Bounty taken.", "SUCCESS")

    def bounty_kill(self, e):
        kind, n, day = self.bounty_today()
        if int(val(self.get_attribute("Bounty.Day"))) != day or e.name != kind:
            return
        got = int(val(self.get_attribute("Bounty.Got")))
        if got >= n:
            return
        self.update_attribute("Bounty.Got", "=%d" % (got + 1))
        self.display_message("Bounty: %d of %d %s." % (got + 1, n, pretty(kind).lower() + "s"),
                             "QUEST" if got + 1 >= n else "INFO")

    # ================================================================================================= records
    RECORDS = (("Kills", "creatures slain"), ("SecretsFound", "secrets found"), ("ArenaWins", "arena wins"),
               ("Deep.Floor", "floors of the Shifting Deep"))

    def note_records(self):
        rec = self.w.together.records.setdefault(self.player_name, {})
        for key, _ in self.RECORDS:
            rec[key] = int(val(self.get_attribute(key)))
        rec["Level"] = self.player_level()

    def records_menu(self):
        self.note_records()
        recs = self.w.together.records
        lines = []
        for key, words in self.RECORDS:
            top = sorted(((r.get(key, 0), n) for n, r in recs.items() if r.get(key, 0)), reverse=True)[:3]
            if top:
                lines.append("Most %s: %s." % (words, ", ".join("%s (%d)" % (n, v) for v, n in top)))
        mine = recs.get(self.player_name, {})
        lines.append("Yours: %s." % ", ".join("%d %s" % (mine.get(k, 0), words) for k, words in self.RECORDS))
        self.show_menu("The hall of records", "Clerk", " ".join(lines), [("Thank you.", None)])

    # ================================================================================================= homesteads
    def guestbook_sign(self, owner):
        if owner == self.player_name:
            return
        book = self.w.together.guests.setdefault(owner, [])
        book.append([self.player_name, int(time.time())])
        del book[:-30]

    def guestbook_menu(self, owner):
        book = self.w.together.guests.get(owner, [])
        names = []
        for n, _ in reversed(book):
            if n not in names:
                names.append(n)
        self.show_menu("Guestbook", "Pocket_Anchor", "Who has visited: %s." % (", ".join(names[:12]) or "nobody yet"),
                       [("Close the book.", None)])

    def gift_box_menu(self, owner):
        t = self.w.together
        if owner == self.player_name:
            gifts = t.gifts.get(owner, [])
            if not gifts:
                self.show_menu("Gift box", "Pocket_Anchor", "Nothing in the gift box.", [("Close it.", None)])
                return
            for frm, item, n in gifts:
                if self.inventory_slots_available(item) > 0:
                    self.add_inventory_item(item, n)
                    self.display_message("A gift from %s: %s." % (frm, ("%d gold" % n) if item == "Gold_Coin(s)" else
                                                                   "%d %s" % (n, pretty(item))), "SUCCESS")
                    gifts.remove([frm, item, n]) if [frm, item, n] in gifts else None
            self.play_sound("Pickup")
            return
        opts = []
        for it in self.inv[:7]:
            if trim(self.data.entity_ini(it.name, "Droppable", "1")) != "0":
                opts.append(("Leave %s." % pretty(it.name), lambda i=it: self.leave_gift(owner, i.name,
                                                                                        max(1, i.quantity))))
        opts.append(("Never mind.", None))
        self.show_menu("Gift box", "Pocket_Anchor", "Leave something for %s?" % owner, opts)

    def leave_gift(self, owner, item, n):
        if self.items_held(item) < n:
            return
        box = self.w.together.gifts.setdefault(owner, [])
        if len(box) >= 20:
            self.refuse("The gift box is full.")
            return
        self.remove_inventory_item(item, n)
        box.append([self.player_name, item, n])
        self.display_message("You leave it in %s's gift box." % owner, "SUCCESS")
        o = self.w.sessions.get(owner)
        if o is not None:
            o.display_message("%s has left you a gift at your homestead." % self.player_name, "INFO")

    # ================================================================================================= welcome back
    def welcome_back(self, last_seen):
        if not last_seen or time.time() - last_seen < self.tg_num("Away.Hours", 20) * 3600:
            return
        t = self.w.together
        lines = []
        for key, d in t.defs().items():
            done_at = t.project(key)["done_at"]
            if done_at and done_at > last_seen:
                lines.append("%s was finished." % d["title"])
        gifts = len(t.gifts.get(self.player_name, []))
        if gifts:
            lines.append("%d gift%s wait%s at your homestead." % (gifts, "" if gifts == 1 else "s",
                                                                 "s" if gifts == 1 else ""))
        guests = [n for n, at in t.guests.get(self.player_name, []) if at > last_seen]
        if guests:
            lines.append("%s visited your homestead." % ", ".join(sorted(set(guests))[:4]))
        lines.append("The shops have had their deliveries, and the Shard Blooms have grown.")
        self.display_message("While you were away: " + " ".join(lines), "INFO")

    # ================================================================================================= companions
    def companions(self):
        return [e for e in getattr(self, "followers", []) if e.alive]

    def companion_call(self, kind, name, minutes, fights):
        if any(getattr(e, "comp_kind", "") == name for e in self.companions()):
            return
        p = self.player
        e = self.w.add_npc(kind, p.z, p.x + 24, p.y, "Attitude=Good Name=%s Pause=0-2" % name.replace(" ", "_"), "Good")
        if e is None:
            return
        e.comp_kind, e.comp_of = name, self
        e.comp_until = self.now + int(minutes * 60000) if minutes else 0
        if not fights and e.ai is not None:
            e.ai.hunts = set()
        elif e.ai is not None:
            e.ai.hunts = {"FOES"}
        self.followers = self.companions() + [e]
        self.w.shard_form(e) if kind != "Strawberry_Cat" else None

    def companion_dismiss(self, e):
        self.followers = [f for f in self.companions() if f is not e]
        self.w.fx_anim("Puff", e.z, e.cx, e.cy, 400)
        self.w.remove_entity(e)

    def companions_step_aside(self):
        """A real player in your party is near: your companions go (they'd only be in the way)."""
        if self.party_members(near=True):
            for e in self.companions():
                self.display_message("%s steps aside: you've company now." % e.display, "INFO")
                self.companion_dismiss(e)

    def companion_tick(self):
        """Your companions keep by you (their roaming ground goes where you go); a hired one's time runs out."""
        comps = self.companions()
        if not comps:
            return
        p = self.player
        for e in comps:
            if e.comp_until and self.now >= e.comp_until:
                self.display_message("%s's time is up: they nod and go their way." % e.display, "INFO")
                self.companion_dismiss(e)
                continue
            a = e.ai
            if a is None:
                continue
            if e.z != p.z or distance(e.cx, e.cy, p.cx, p.cy) > 480:
                self.w.set_entity_position(e, p.x + 20, p.y + 4)       # (lost you: they catch up)
                e.z = p.z
            a.zone = [p.fx - 40, p.fy - 40, p.fx + 40, p.fy + 40]
            a.chase = [p.fx - 320, p.fy - 320, p.fx + 320, p.fy + 320]
            a.stand = 0

    def companion_verbs(self, e, verbs):
        if getattr(e, "comp_of", None) is self:
            return self.add_verb(verbs, "Send away")
        nid = getattr(e, "npc_id", "") or ""
        if nid in ("Jimmy", "Throne_Jimmy") and val(self.get_attribute("KingQuest")) >= 1:
            return self.add_verb(verbs, "Come along")
        if nid.startswith("Sellsword"):
            return self.add_verb(verbs, "Hire")
        return verbs

    def secrets_nose(self):
        """Jimmy along: the thief's eye finds more (senses.py adds this to its chance)."""
        return 15 if any(getattr(e, "comp_kind", "") == "Jimmy" for e in self.companions()) else 0

    # ================================================================================================= greetings
    def greet_tick(self):
        """Now and then a townsperson near the crowned heir (or the saviour of their town) says so over their head."""
        if self.now < getattr(self, "greet_at", 0):
            return
        self.greet_at = self.now + 4000
        crowned = val(self.get_attribute("KingQuest")) >= 1
        saved = [k for k, v in self.attributes if k.upper().startswith("SAVED.") and val(v) >= 1]
        if not crowned and not saved:
            return
        p = self.player
        heard = getattr(self, "greeted", None)
        if heard is None:
            heard = self.greeted = {}
        for e in self.w.npcs_near(p.z, p.cx, p.cy):
            if not e.alive or "Talk to" not in (e.use_words or "") or self.w.hostile_for(e, self) or \
                    getattr(e, "comp_of", None) is not None or distance(e.cx, e.cy, p.cx, p.cy) > 96:
                continue
            if self.now - heard.get(e.uid, -10 ** 9) < 600000 or random.random() > 0.35:
                continue
            heard[e.uid] = self.now
            if saved and (not crowned or random.random() < 0.5):
                line = "You saved us from the raiders! Thank you!"
            else:
                king = self.data_word("King")
                line = random.choice(("Long live the %s!" % king, "Your Majesty!", "Ashen's own %s!" % king,
                                      "Bless you, Majesty."))
            self.w.fx({"t": "bubble", "u": e.uid, "text": line}, e.z, e.cx, e.cy, self)
            break

    def data_word(self, word):
        return self.parse_script_variables("$Player.%s" % word)

    # ================================================================================================= the hooks
    def together_verbs(self, e, verbs):
        """Verbs for a player (Invite, Leave party) and the companions'."""
        if e.type == PLAYER:
            o = self.session_of(e)
            if o is not None and o is not self:
                verbs = self.add_verb(verbs, "Trade")
                if o.player_name in self.party_names():
                    verbs = self.add_verb(verbs, "Leave party")
                elif not getattr(o, "party_id", 0):
                    verbs = self.add_verb(verbs, "Invite to party")
                verbs = self.add_verb(verbs, "Remove friend" if o.player_name in self.friend_names() else "Add friend")
            return verbs
        if e.type == NPC:
            return self.companion_verbs(e, verbs)
        return verbs

    def together_do(self, verb, e):
        """The engine's own things for playing together (True: done)."""
        if e is None:
            return False
        if e.type == PLAYER:
            o = self.session_of(e)
            if verb == "Invite to party":
                self.invite(o)
                return True
            if verb == "Leave party":
                self.leave_party()
                return True
            if verb == "Add friend" and o is not None:
                self.add_friend_named(o.player_name)
                return True
            if verb == "Remove friend" and o is not None:
                self.remove_friend_named(o.player_name)
                return True
            if verb == "Trade" and o is not None:
                self.trade_ask(o)
                return True
            if verb == "Use with" and self.item_in_use is not None and o is not None:
                self.offer_gift(self.item_in_use, o)
                self.item_in_use = None
                return True
            return False
        nid = getattr(e, "npc_id", "") or ""
        if e.type == NPC and verb == "Talk to":
            d = self.project_of_foreman(e)
            if d is not None:
                self.foreman_menu(d)
                return True
            if nid.startswith("Town_Crier"):
                self.crier_menu()
                return True
            if nid == "Bounty_Clerk":
                self.clerk_menu()
                return True
            if nid == "Record_Keeper":
                self.records_menu()
                return True
            if nid.startswith("Sellsword"):
                self.show_menu("Sellsword", "Guard", "A sword for hire. %d gold and I'm yours for %d minutes." %
                               (self.tg_num("Hire.Gold", 25), self.tg_num("Hire.Minutes", 10)),
                               [("Hire them.", lambda: self.do_action("Hire", e)), ("Not now.", None)])
                return True
        if e.type == NPC and verb == "Come along" and nid in ("Jimmy", "Throne_Jimmy"):
            self.companion_call("Strawberry_Cat", "Jimmy", 0, False)
            self.display_message("Jimmy stretches, considers it, and pads after you.", "INFO")
            return True
        if e.type == NPC and verb == "Hire" and nid.startswith("Sellsword"):
            cost = int(self.tg_num("Hire.Gold", 25))
            if self.items_held("Gold_Coin(s)") < cost:
                self.refuse("You need %d gold for that." % cost)
                return True
            self.remove_inventory_item("Gold_Coin(s)", cost)
            self.companion_call("Guard", "Sellsword", self.tg_num("Hire.Minutes", 10), True)
            self.display_message("The sellsword pockets the gold and falls in beside you.", "SUCCESS")
            return True
        if e.type == NPC and verb == "Send away" and getattr(e, "comp_of", None) is self:
            self.companion_dismiss(e)
            return True
        if e.type == STATICOBJECT and e.name == "Project_Plaque" and verb in ("Read", "Examine"):
            self.display_message(self.plaque_text(nid.replace("Plaque_", "")), "EXAMINE")
            return True
        return False

    def together_tick(self):
        self.trade_tick()
        self.companion_tick()
        self.greet_tick()
