"""Digging: a spade (its Use.Words Dig) digs where you stand, on open ground (data\\Digging.ini Ground). Now and then
(Chance in 100) something turns up: a weighted pick from [Finds], or from the [Finds.<Place>] that covers the map
(its Maps=), added to them or instead (Replace=1). It leaves a hole (Dug_Hole001) that grasses over after Regrow
seconds; until then nobody can dig there again. On sand you always get a sack of sand as well."""
import random

from dragonsword import ini
from dragonsword.lb import val, word, strip_digits, lbstr

HOLE = "Dug_Hole001"


def parse_finds(items):
    """[(item, how many, weight)] from item=how many,weight lines."""
    out = []
    for k, v in items:
        q, w = word(v, 1, ","), val(word(v, 2, ","))
        if w > 0:
            out.append((k.strip(), q.strip() or "1", w))
    return out


def parse_maps(text):
    """{(x, y, z)} from "x,y,z x1-x2,y1-y2,z ...": maps, and blocks of them (a negative one alone: -1)."""
    out = set()
    for part in text.split():
        bits = part.split(",")
        if len(bits) != 3:
            continue
        spans = []
        for b in bits:
            b = b.strip()
            lo, _, hi = b[1:].partition("-") if b.startswith("-") else b.partition("-")
            lo = -int(val(lo)) if b.startswith("-") else int(val(lo))
            hi = int(val(hi)) if hi else lo
            spans.append(range(min(lo, hi), max(lo, hi) + 1))
        out |= {(x, y, z) for x in spans[0] for y in spans[1] for z in spans[2]}
    return out


class DigMixin:
    def init_digging(self):
        self.dig_pending = None             # (due ms, map, tile x, tile y, where the player stood)

    def dig_rules(self):
        d = self.data
        cache = d.cache("digging")
        if "rules" not in cache:
            path = d.data_file("Digging.ini")
            r = lambda k, default: ini.read("Digging", k, default, path)
            chance = float(val(r("Chance", "7")))
            places = []
            for sec, items in ini.sections(path):
                if not sec.lower().startswith("finds."):
                    continue
                keys = {k.strip().lower(): v for k, v in items}
                places.append({"name": sec[6:], "maps": parse_maps(keys.get("maps", "")),
                               "replace": val(keys.get("replace", "0")) == 1,
                               "chance": float(val(keys["chance"])) if "chance" in keys else chance,
                               "finds": parse_finds([(k, v) for k, v in items
                                                     if k.strip().lower() not in ("maps", "replace", "chance")])})
            cache["rules"] = {"chance": chance, "regrow": max(10, int(val(r("Regrow", "600")))),
                              "seconds": max(0.0, float(val(r("Seconds", "2")))),
                              "ground": [g.strip().lower() for g in r("Ground", "Grass,Dirt,Sand").split(",") if g.strip()],
                              "finds": parse_finds(ini.section("Finds", path) or []), "places": places}
        return cache["rules"]

    def dig_finds(self, m):
        """(chance in 100, [(item, how many, weight)]) for digging on map m: its place's, or the general ones."""
        rules = self.dig_rules()
        for pl in rules["places"]:
            if (m.mx, m.my, m.mz) in pl["maps"]:
                return pl["chance"], pl["finds"] if pl["replace"] else rules["finds"] + pl["finds"]
        return rules["chance"], rules["finds"]

    def diggable(self, tile):
        base = strip_digits(tile or "").rstrip("_").lower()
        return any(base == g or base.startswith(g + "_") or base.endswith("_" + g) for g in self.dig_rules()["ground"])

    def dig(self):
        """The spade: dig where you stand."""
        if self.dig_pending is not None:
            return
        p = self.player
        m, tx, ty = self.w.tile_at(p.z, p.fx, p.fy)
        if m is None:
            return
        tile, decor = self.cell_names(m, tx, ty)
        if decor == HOLE:
            self.display_message("Someone has dug here already.", "FAIL")
            return
        if decor or not self.diggable(tile):
            self.display_message("You can't dig here. Try open ground: grass, earth or sand.", "FAIL")
            return
        owner = self.w.homes.owner_of(m.name)
        if owner is not None and owner != self.player_name:
            self.display_message("Not in someone else's garden!", "FAIL")
            return
        if not self.tools_held("Spade"):
            self.display_message("Your spade is broken: get it mended (a blacksmith, or an anvil).", "FAIL")
            return
        rules = self.dig_rules()
        self.use_tool("Spade")
        self.stop_player_walk()
        self.display_message("You dig into the ground...", "INFO")
        self.play_work("Dirt_Clods", int(rules["seconds"] / 0.8) or 1, "DigHole", at=(p.cx, p.fy))
        self.dig_pending = (self.now + rules["seconds"] * 1000, m, tx, ty, (p.fx, p.fy))

    def dig_tick(self):
        if self.dig_pending is None:
            return
        due, m, tx, ty, (sx, sy) = self.dig_pending
        p = self.player
        if abs(p.fx - sx) > 12 or abs(p.fy - sy) > 12:
            self.dig_pending = None
            self.display_message("You stop digging.", "INFO")
            return
        if self.now < due:
            return
        self.dig_pending = None
        w = self.w
        tile, decor = self.cell_names(m, tx, ty)
        if decor:                       # (someone else's hole got there first)
            self.display_message("...but someone has dug here already.", "FAIL")
            return
        rules = self.dig_rules()
        w.change_tile(m, tx, ty, HOLE)
        w.add_action_to_queue("CHANGE.TILE", tile, "Tile", HOLE, m.name, "%d,%d" % (tx, ty), rules["regrow"])
        if strip_digits(tile).lower() == "sand" and self.inventory_slots_available("Sand") > 0:
            self.add_inventory_item("Sand", 1, quiet=True)
            extra = " and a sack of sand"
        else:
            extra = ""
        self.update_skill("Mining", "+0.01", pop=False)
        chance, finds = self.dig_finds(m)
        if finds and random.uniform(0, 100) < chance:
            total = sum(f[2] for f in finds)
            pick = random.uniform(0, total)
            for name, q, weight in finds:
                pick -= weight
                if pick <= 0:
                    break
            lo = int(val(word(q, 1, "-"))) or 1
            hi = int(val(word(q, 2, "-"))) or lo
            n = random.randint(min(lo, hi), max(lo, hi))
            room = self.inventory_slots_available(name)
            if room >= n:
                self.add_inventory_item(name, n, quiet=True)
            else:
                if room > 0:
                    self.add_inventory_item(name, room, quiet=True)
                self.drop_on_floor(name, n - room)
            what = self.data.entity_ini(name, "Value", "0")
            self.play_sound("Coins" if name == "Gold_Coin(s)" else "Pickup")
            self.display_message("...and turn up %s %s%s!" % (lbstr(n), name.replace("_", " ").replace("(s)", "s").lower(),
                                                              extra),
                                 "ACHIEVEMENT" if val(what) >= 30 else "SUCCESS")
        else:
            self.display_message("...but find nothing but earth%s." % extra, "INFO")
