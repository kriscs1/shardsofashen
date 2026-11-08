"""Standing: what each town thinks of you (data\\Towns.ini has every number), each player's own, kept as the attribute
Standing.<Town> (from Least to Most; everyone starts at 0, a Stranger).

  Ranks       Outlaw, Distrusted, Stranger, Welcome, Trusted, Honoured ([Ranks]): each sets what a shop there charges
              you and pays you; an Outlaw isn't served at all.
  Guards      Trusted: caught thieving, the first time in a day, a guard only warns you. Honoured: a fine, not a
              chase. Distrusted or worse: more guards come. An Outlaw is the town's guards' foe on sight (never its
              captain, nor a guard with a script of their own: a character, not the watch).
  The fine    an Outlaw talks to the town's captain ([<Town>] Captain=: an Id or a kind) and pays to be Distrusted.
  What moves  a quest (Quests.ini Reward.Standing=<Town> N, once), a raid fought off, gifts to a project, the day's
  it          bounty; caught thieving or in a house, a blow at a guard, a guard killed. A theft nobody sees costs
              nothing. Scripts: Change.Standing <Town> <amount>, and $Standing.<Town> (or $Standing.Here) in a
              condition: a lock's condition is how a door opens at a rank.
A line and a sound when a rank changes, never on every point."""
import time

from ashen import ini
from ashen.lb import val, trim, lbstr

from .entity import NPC

TOWNS = "Towns.ini"


class StandingMixin:
    def standing_num(self, key, default):
        return self.data.ini_num(TOWNS, "Standing", key, default)

    # ----- the towns (worked out once, from the file)
    def standing_towns(self):
        """{TOWN KEY: {"key", "name", "boxes", "captain", "guards_if", "cheaper_if", "cheaper_racks",
        "cheaper_rate"}} from Towns.ini."""
        c = self.data.cache("standing")
        got = c.get("towns")
        if got is None:
            got = {}
            for sec, items in ini.sections(self.data.data_file(TOWNS)):
                if sec.upper() in ("STANDING", "RANKS"):
                    continue
                d = {k.upper(): trim(v) for k, v in items}
                boxes = []
                for part in d.get("MAPS", "").split():
                    b = [int(val(x)) for x in part.split(",")]
                    if len(b) == 4:
                        boxes.append((min(b[0], b[2]), min(b[1], b[3]), max(b[0], b[2]), max(b[1], b[3])))
                got[sec.upper()] = {"key": sec, "name": d.get("NAME", sec), "boxes": boxes,
                                    "captain": d.get("CAPTAIN", ""), "guards_if": d.get("GUARDS.IF", ""),
                                    "cheaper_if": d.get("CHEAPER.IF", ""),
                                    "cheaper_racks": {r.strip().upper() for r in d.get("CHEAPER.RACKS", "").split(",")
                                                      if r.strip()},
                                    "cheaper_rate": val(d.get("CHEAPER.RATE", "1")) or 1.0}
            c["towns"] = got
        return got

    def standing_ranks(self):
        """[(least, name, buy rate, sell rate)] from the lowest up."""
        c = self.data.cache("standing")
        got = c.get("ranks")
        if got is None:
            got = []
            for name, v in ini.section("Ranks", self.data.data_file(TOWNS)):
                bits = v.split()
                if bits:
                    got.append((val(bits[0]), name, val(bits[1]) if len(bits) > 1 else 1.0,
                                val(bits[2]) if len(bits) > 2 else 1.0))
            got.sort()
            c["ranks"] = got
        return got

    def town_of_map(self, map_name):
        """The town key whose maps take in map_name ("" if none): its own maps, and Depth below them."""
        c = self.data.cache("standing_maps")
        if map_name in c:
            return c[map_name]
        town = ""
        bits = (map_name or "").split(",")
        if len(bits) == 3:
            x, y, z = (int(val(b)) for b in bits)
            if z >= -int(self.standing_num("Depth", 1)):
                for t in self.standing_towns().values():
                    if any(a <= x <= c_ and b <= y <= d for a, b, c_, d in t["boxes"]):
                        town = t["key"]
                        break
        c[map_name] = town
        return town

    def town_named(self, name):
        """A town's key from what a script or data says (its key or its name; Here: where you are)."""
        name = trim(name).replace("_", " ")
        if name.upper() == "HERE":
            return self.town_of_map(self.cur_map.name) if self.cur_map is not None else ""
        towns = self.standing_towns()
        t = towns.get(name.upper().replace(" ", "_")) or towns.get(name.upper())
        if t is None:
            t = next((t for t in towns.values() if t["name"].upper() == name.upper()), None)
        return t["key"] if t is not None else ""

    def town_title(self, town):
        t = self.standing_towns().get(town.upper())
        return t["name"] if t is not None else town

    # ----- yours
    def standings(self):
        """{TOWN KEY: standing} of this player's (only the towns that aren't 0), read from the attributes once."""
        got = self.standing_cache
        if got is None:
            got = {}
            for k, v in self.attributes:
                if k.upper().startswith("STANDING."):
                    got[k[9:].upper()] = val(v)
            self.standing_cache = got
            self.outlaw_towns = self.outlaw_set(got)
            self.outlaw_any = any(self.rank_of(n)[0] == "Outlaw" for n in got.values())
        return got

    def standing(self, town):
        return self.standings().get(trim(town).upper(), 0)

    def rank_of(self, n):
        """(name, buy rate, sell rate) of standing n."""
        ranks = self.standing_ranks()
        got = ranks[0] if ranks else (0, "Stranger", 1.0, 1.0)
        for r in ranks:
            if n >= r[0]:
                got = r
        return got[1], got[2], got[3]

    def rank(self, town):
        return self.rank_of(self.standing(town))[0] if town else "Stranger"

    def standing_attr_changed(self):
        """Some Standing.<Town> (or a condition a town's guards wait for) may have changed: worked out again."""
        self.standing_cache = None
        self.standings()

    def outlaw_set(self, got):
        """The towns whose guards are this player's foes on sight (an Outlaw there, and its Guards.If met)."""
        out = set()
        towns = self.standing_towns()
        for key, n in got.items():
            t = towns.get(key)
            if t is None or self.rank_of(n)[0] != "Outlaw":
                continue
            if t["guards_if"] and not self.condition_met(t["guards_if"]):
                continue
            out.add(t["key"])
        return out

    def change_standing(self, town, amount, why=""):
        """A deed moves town's standing by amount (held between Least and Most): a line and a sound if the rank
        changes."""
        town = self.town_named(town)
        if not town or not amount:
            return
        old = self.standing(town)
        new = max(self.standing_num("Least", -100), min(self.standing_num("Most", 100), old + amount))
        if new == old:
            return
        was, now = self.rank_of(old)[0], self.rank_of(new)[0]
        self.update_attribute("Standing." + town, "=" + lbstr(round(new, 2)))
        self.emit({"t": "standing", "list": self.standing_list()})
        self.check_locks(True)                          # (a Trusted door, an Outlaw's gate)
        if was == now:
            return
        name = self.town_title(town)
        if now == "Outlaw":
            self.display_message("%s has had enough of you: you're an Outlaw there now, and its guards will come for "
                                 "you." % name, "DAMAGE", "Spotted")
        elif new > old:
            self.display_message("%s thinks better of you: you're %s there now." % (name, rank_words(now)),
                                 "ACHIEVEMENT", "Success")
        else:
            self.display_message("%s thinks worse of you: you're %s there now." % (name, rank_words(now)), "FAIL",
                                 "Fail")

    def standing_list(self):
        """For the journal: [[town's name, standing, rank]] of every town you've a standing in, the best first."""
        towns = self.standing_towns()
        out = []
        for key, n in self.standings().items():
            t = towns.get(key)
            if t is not None and n:
                out.append([t["name"], round(n), self.rank_of(n)[0]])
        out.sort(key=lambda r: (-r[1], r[0]))
        return out

    def admin_standings(self):
        """For the admin panel: [[town key, name, standing, rank]] of every town, as Towns.ini has them."""
        return [[t["key"], t["name"], round(self.standing(t["key"]), 2), self.rank(t["key"])]
                for t in self.standing_towns().values()]

    # ----- what a town's people make of you
    def shop_rates(self, npc, rack=""):
        """(buy times, sell times) at a shop in npc's town (or yours), or None: an Outlaw there isn't served (and is
        told). Towns.ini Cheaper.If=<condition>: its Cheaper.Racks sell at Cheaper.Rate times the price, to those
        it's true for."""
        where = npc.map if npc is not None and npc.type == NPC else (self.cur_map.name if self.cur_map else "")
        town = self.town_of_map(where)
        if not town:
            return 1.0, 1.0
        rank, buy, sell = self.rank_of(self.standing(town))
        t = self.standing_towns().get(town.upper(), {})
        if rack and rack.upper() in t.get("cheaper_racks", ()) and t["cheaper_if"] and \
                self.condition_met(t["cheaper_if"]):
            buy *= t["cheaper_rate"]                       # (a quest's way made the town's bread cheaper, for you)
        if rank == "Outlaw":
            who = self.display_name(npc) if npc is not None and npc.type == NPC else "shopkeeper"
            self.display_message("The %s won't serve you: you're an Outlaw in %s." % (who, self.town_title(town)),
                                 "FAIL", "Denied")
            return None
        return buy, sell

    def guard_town(self, e):
        """The town NPC e keeps the watch in ("" if it's no town's guard): a guard kind, on a town's maps, not its
        captain, not anyone's companion, and not a character (a guard with a Talk script of their own)."""
        nid = getattr(e, "npc_id", "") or ""
        key = (e.name, e.map, nid)
        c = self.data.cache("guard_town")
        if key in c:
            return c[key]
        town = ""
        kinds = {k.strip() for k in str(self.data.ini_read(TOWNS, "Standing", "Guards", "")).split(",")}
        if e.name in kinds:
            town = self.town_of_map(e.map)
            t = self.standing_towns().get(town.upper())
            if t is not None and (t["captain"] in (nid, e.name) or (nid and self.script_exists("Talk to " + nid))):
                town = ""
        c[key] = town
        return town

    def outlaw_foe(self, e):
        """Is NPC e one of the guards of a town you're an Outlaw in? (session.attitude_of asks, ~1000 times a tick:
        nothing to do for anyone who isn't.)"""
        if e.owner is not None or getattr(e, "comp_of", None) is not None or getattr(e, "summoned_until", 0):
            return False
        return self.guard_town(e) in self.outlaw_towns

    def caught_by_town(self, e, how):
        """Caught thieving by e (how: shop, pocket or house): the town thinks worse of you, and says what comes:
        "warn" (a guard looks the other way), "fine" (paid, no chase), or how many guards come (1 or more)."""
        town = self.town_of_map(e.map)
        if not town:
            return 1
        rank = self.rank(town)
        flag = "StandingWarned." + town
        hour = int(time.time() // 3600)
        if rank == "Trusted" and hour - int(val(self.get_attribute(flag))) >= self.standing_num("Warn.Hours", 24):
            self.update_attribute(flag, "=%d" % hour)
            self.display_message("A guard steps up beside you: \"Put it back. I didn't see that.\"", "INFO", "Hush")
            return "warn"
        self.change_standing(town, self.standing_num("Caught.House" if how == "house" else "Caught", -8))
        fine = int(self.standing_num("Caught.Fine", 25))
        if rank == "Honoured" and self.items_held("Gold_Coin(s)") >= fine:
            self.remove_inventory_item("Gold_Coin(s)", fine)
            self.display_message("A guard takes %d gold off you for it, and that's an end of it. This time." % fine,
                                 "FAIL", "Coins")
            return "fine"
        if rank in ("Distrusted", "Outlaw"):
            return max(1, int(self.standing_num("Distrusted.Guards", 2)))
        return 1

    def guard_struck(self, e, killed=False):
        """A blow at (or the death of) a town's guard: its town thinks worse of you (a blow once in a while for each
        guard, not every swing)."""
        if e.type != NPC or e.owner is not None:
            return
        kinds = {k.strip() for k in str(self.data.ini_read(TOWNS, "Standing", "Guards", "")).split(",")}
        if e.name not in kinds:
            return
        town = self.town_of_map(e.map)
        if not town:
            return
        if killed:
            self.change_standing(town, self.standing_num("Guard.Killed", -40))
            return
        hit = getattr(self, "guards_hit", None)
        if hit is None:
            hit = self.guards_hit = {}
        if self.now - hit.get(e.uid, -10 ** 9) < self.standing_num("Guard.Hit.Minutes", 5) * 60000:
            return
        hit[e.uid] = self.now
        self.change_standing(town, self.standing_num("Guard.Hit", -15))

    # ----- the fine (an Outlaw talks to the captain)
    def captain_of(self, e):
        """The town NPC e is the captain of (Towns.ini Captain=: its Id, or its kind on the town's maps), or ""."""
        if e.type != NPC:
            return ""
        town = self.town_of_map(e.map)
        t = self.standing_towns().get(town.upper())
        nid = getattr(e, "npc_id", "") or ""
        if t is None or not t["captain"] or t["captain"] not in (nid, e.name):
            return ""
        return t["key"]

    def fine_owed(self, town):
        clear = self.standing_num("Clear.To", -60)
        return int(self.standing_num("Fine", 50) + max(0, clear - self.standing(town)) *
                   self.standing_num("Fine.Per.Point", 5))

    def fine_menu(self, e):
        """Talk to a town's captain as its Outlaw: the fine, paid or not (True: shown). Anyone else talks as ever."""
        town = self.captain_of(e)
        if not town or self.rank(town) != "Outlaw":
            return False
        gold = self.fine_owed(town)
        name = self.town_title(town)
        script = self.find_action_script("Talk to", e.name, NPC, getattr(e, "npc_id", "") or "")
        opts = []
        if self.items_held("Gold_Coin(s)") >= gold:
            opts.append(("Pay the fine.", lambda: self.pay_fine(town, gold)))
        if script:
            opts.append(("Something else.", lambda: self.start_script(script, True)))
        opts.append(("Not now.", None))
        self.show_menu("The fine", e.name, "You've a nerve, walking in here. %s wants %d gold for your name, and "
                       "then you're only distrusted. Every guard in the town knows your face till then." %
                       (name, gold), opts)
        return True

    def pay_fine(self, town, gold):
        if self.rank(town) != "Outlaw" or self.items_held("Gold_Coin(s)") < gold:
            return
        self.remove_inventory_item("Gold_Coin(s)", gold)
        self.play_sound("Coins")
        clear = self.standing_num("Clear.To", -60)
        self.change_standing(town, clear - self.standing(town))
        self.act_done(True)

    # ----- old saves
    def standing_catch_up(self):
        """Quests finished before standing was kept: what they'd have given, given once now, quietly."""
        for name, d in self.help_read_ini("Quests.ini"):
            attr = trim(d.get("ATTRIBUTE", ""))
            if not attr or not any(k.startswith("REWARD.STANDING") and trim(v) for k, v in d.items()):
                continue
            if val(self.get_attribute("ShardsPaid." + attr)) >= 1 and val(self.get_attribute("StandingPaid." + attr)) < 1:
                self.quest_standing(d, attr)

    def quest_standing(self, d, attr):
        """A quest done: its Reward.Standing (<Town> N ...), once (StandingPaid.<attribute> says it's given); or
        Reward.Standing<N>, for a quest that ended way N (its Ending= attribute's value), where it has one."""
        key, ending = "REWARD.STANDING", trim(d.get("ENDING", ""))
        if ending and trim(d.get("REWARD.STANDING%d" % int(val(self.get_attribute(ending))), "")):
            key = "REWARD.STANDING%d" % int(val(self.get_attribute(ending)))
        bits = trim(d.get(key, "")).split()
        if not bits or val(self.get_attribute("StandingPaid." + attr)) >= 1:
            return
        self.update_attribute("StandingPaid." + attr, "=1")
        for k in range(0, len(bits) - 1, 2):
            self.change_standing(bits[k], val(bits[k + 1]))


def rank_words(rank):
    """"Welcome", "Trusted"... as said in a sentence ("you're a Stranger there now")."""
    return "a Stranger" if rank == "Stranger" else rank
