"""Shardcraft: the making and working of Shard magic (Channeling is its use: casting). What it governs:

  * Shardstones (data\\Shardstones.ini: each stone's key and name; its place is its map's Id Waystone_<Key>, and a
    player's attunement to it the attribute Waystone.<Key>, as they always were). A stone stays dormant to you, its
    rune dark and still, until you activate it (Shards.ini [Shards] Shardstone.<Key>, else Shardstone). Travelling
    from an active one opens a copy of the world map with every stone you've activated on it: pick one, and go
    (Shardstone.Travel Shards). Your homestead is a stone's journey too, with the anchor that holds it (homes.py).
  * Dismantling (shards.py dismantle): its Shardcraft xp, and now and then a rare shard as well (Shards.ini
    [Shardcraft] Rare.*): an Ember Shard from a blade, a Storm Shard from a staff, a Ward Shard from armour.
  * Enchanting: a rare shard bound into a piece of gear in the pack (the shard's Enchant): the gear becomes its
    enchanted kind (Emberbound_Iron_Sword: Entities.ini Base= and Enchant=, made by dev\\migrate\\build_shardcraft.py),
    for Shards.ini [Enchant] Shards and a Shardcraft level.
  * The Shardgate (its script, build_shardgate.py): Shards.ini [Shardcraft] Shardgate.Level and Shardgate.Stones
    activated shardstones ($Shardstones.Active) before the ring will hold.
  * Writing scrolls and spells (ItemRacks.ini CRAFT-Scrolls, ownspell.py), absorbing remnants (remnants.py) and
    shaping your pocket of the Shardrealm (homes.py terraforming) train it too."""
from ashen import ini
from ashen.lb import val, lbstr, trim, pretty, random_number

from .entity import INVENTORYITEM, STATICOBJECT
from .shards import shard_words

STONE = "Shardstone"
STONE_REACH = 64                    # (how near a stone you must stand for it to answer)


def shardstone_table(w):
    """[{"key", "title", "map", "px", "py", "uid"}] of every shardstone, in Shardstones.ini's order: where its place Id
    is, and the stone (a StaticObject) nearest that on its map. Worked out once, the first time it's asked for."""
    t = getattr(w, "_shardstones", None)
    if t is not None:
        return t
    d = w.data
    out = []
    for key, items in ini.sections(d.data_file("Shardstones.ini")):
        kv = {k.upper(): v for k, v in items}
        pl = d.place("Waystone_" + key)
        m = w.map_named(pl.map) if pl is not None else None
        if m is None:
            continue
        gx, gy = m.ox + pl.px, m.oy + pl.py
        best, uid = 1e9, 0
        for e in w.ents:
            if e.type == STATICOBJECT and e.name == STONE and e.z == m.mz:
                dd = abs(e.x - gx) + abs(e.y - gy)
                if dd < best and dd < 6 * w.tw:
                    best, uid = dd, e.uid
        out.append({"key": key, "title": trim(kv.get("TITLE", "")) or pretty(key), "map": m.name, "px": pl.px,
                    "py": pl.py, "gx": gx, "gy": gy, "z": m.mz, "uid": uid})
    w._shardstones = out
    return out


class ShardcraftMixin:
    def craft_num(self, key, default, section="Shardcraft"):
        v = trim(self.data.shards_ini(section, key, ""))
        return val(v) if v != "" else default

    def shardcraft_do(self, verb, e):
        """The engine's own Shardcraft things (True: done): a shardstone, enchanting."""
        if e.type == STATICOBJECT and e.name == STONE and verb in ("Travel", "Touch", "Activate"):
            self.shardstone_touched(e)
            return True
        if e.type == INVENTORYITEM and verb == "Enchant" and self.entity_ini(e.name, "Enchant", ""):
            self.enchant_menu(e)
            return True
        return False

    # ----- shardstones
    def stones(self):
        return shardstone_table(self.w)

    def stone_of(self, e):
        return next((s for s in self.stones() if s["uid"] == e.uid), None)

    def stone_active(self, key):
        return val(self.get_attribute("Waystone." + key)) >= 1

    def stones_active(self):
        return [s for s in self.stones() if self.stone_active(s["key"])]

    def stones_lit(self):
        """The stones this player has activated, by their uid (the page draws the others dormant)."""
        return [s["uid"] for s in self.stones_active() if s["uid"]]

    def stone_cost(self, key):
        return int(self.shard_setting("Shardstone." + key, 5))

    def shardstone_touched(self, e):
        if self.player_distance_to(e) > STONE_REACH:
            self.refuse("You are too far away!")
            return
        s = self.stone_of(e)
        if s is None:
            self.display_message("The stone is silent.", "FAIL")
            return
        if not self.stone_active(s["key"]):
            n = self.stone_cost(s["key"])
            self.play_sound("Stone_Dormant")
            self.show_menu("Shardstone", "Shardstone_Dormant",
                           "The %s shardstone stands dormant: its rune is dark and cold under your hand. Once it's "
                           "active it knows you, and you can travel to it from any shardstone you've activated."
                           % s["title"], [("Activate it (%s)" % shard_words(n), lambda: self.stone_activate(e)),
                                          ("Leave it.", None)])
            return
        self.stone_map(s)

    def stone_activate(self, e):
        s = self.stone_of(e)
        if s is None or self.stone_active(s["key"]) or self.player_distance_to(e) > STONE_REACH:
            return
        if not self.spend_shards(self.stone_cost(s["key"]), "Activating the shardstone"):
            return
        self.update_attribute("Waystone." + s["key"], "=1")
        self.play_sound("Stone_Wake", (e.cx, e.cy))
        self.fx_anim("Teleport_Glow", e.cx, e.cy, 700)
        self.update_skill("Shardcraft", "+" + lbstr(self.craft_num("Shardstone.XP", 0.3)))
        self.display_message("The rune drinks the Shards and flares blue: the %s shardstone is active to you."
                             % s["title"], "SUCCESS")
        self.dirty_me = True
        self.stone_map(s)

    def stone_map(self, here):
        """The world map, to travel from the stone here: every stone you've activated on it."""
        self.stone_here = (here["key"], self.now)
        rows = [{"k": s["key"], "t": s["title"], "x": s["gx"] + 16, "y": s["gy"] + 16, "z": s["z"], "here":
                 s["key"] == here["key"]} for s in self.stones_active()]
        self.play_sound("SpellCast")
        self.emit({"t": "stones", "here": here["key"], "title": here["title"], "cost": int(self.shard_setting(
            "Shardstone.Travel", 2)), "stones": rows, "home": self.has_home_access() and self.homes.available,
                   "visit": bool(self.homes.visitable_by(self.player_name))})

    def stone_near(self):
        """The active stone the player opened the map at, if they're still by it (and it was lately): its row."""
        here = getattr(self, "stone_here", None)
        if not here or self.now - here[1] > 10 * 60 * 1000:
            return None
        s = next((s for s in self.stones() if s["key"] == here[0]), None)
        e = self.w.by_uid.get(s["uid"]) if s else None
        if e is None or self.player_distance_to(e) > STONE_REACH * 1.5 or not self.stone_active(s["key"]):
            return None
        return s

    def stone_travel(self, key):
        """A stone picked on the travel map."""
        here = self.stone_near()
        if here is None:
            self.refuse("You need to stand by an active shardstone to travel.")
            return
        to = next((s for s in self.stones_active() if s["key"] == key), None)
        if to is None or to["key"] == here["key"]:
            return
        if not self.spend_shards(int(self.shard_setting("Shardstone.Travel", 2)), "Travelling"):
            return
        self.stone_here = None
        self.player_attack_target = None
        self.play_sound("Teleporter")
        self.display_message("The world blurs... and you step out by the %s shardstone." % to["title"], "INFO")
        self.teleport(to["map"], to["px"], to["py"])

    def stone_home(self, visit=False):
        """Home (or someone's home) from the travel map: a stone's journey to an anchored pocket (homes.py)."""
        if self.stone_near() is None:
            self.refuse("You need to stand by an active shardstone to travel.")
            return
        self.stone_here = None
        if visit:
            self.visit_menu()
        else:
            self.go_home()

    # ----- dismantling's rare shards
    def rare_shard_for(self, name):
        """Which rare shard breaking this down might give: a staff's (it has Magic=) Storm, a blade's Ember,
        armour's Ward; "" if none (not gear, or worth too little, or enchanted already)."""
        verb = self.equip_verb(name)
        if not verb or self.entity_ini(name, "Base", "") or \
                val(self.entity_ini(name, "Value", "0")) < self.craft_num("Rare.Min.Value", 30):
            return ""
        if verb == "Wield" and self.item_equip_slot(name) == 1:
            return "Storm_Shard" if val(self.entity_ini(name, "Magic", "0")) > 0 else "Ember_Shard"
        return "Ward_Shard"

    def dismantled(self, name, n):
        """After a dismantling: its Shardcraft xp, and the roll for a rare shard."""
        xp = max(self.craft_num("Dismantle.XP.Min", 0.05), self.craft_num("Dismantle.XP", 0.04) * n)
        self.update_skill("Shardcraft", "+" + lbstr(round(xp, 3)))
        rare = self.rare_shard_for(name)
        if not rare:
            return
        chance = self.craft_num("Rare.Chance", 4) + self.craft_num("Rare.Chance.Per.Level", 0.4) * \
            self.skill_level("Shardcraft")
        if random_number(1, 1000) <= int(chance * 10):
            self.add_inventory_item(rare, 1)
            self.play_sound("Rare_Shard")
            self.display_message("Something bright is left in the dust: %s!" % pretty(rare).replace("Shard", "shard"),
                                 "ACHIEVEMENT")

    # ----- enchanting
    def enchanted_name(self, shard, gear):
        """The enchanted kind of gear that shard makes (Emberbound_Iron_Sword), or "" if it can't take it."""
        word = trim(self.entity_ini(shard, "Enchant", ""))
        name = "%s_%s" % (word, gear)
        if not word or self.entity_ini(gear, "Base", "") or not self.entity_ini(name, "Type", ""):
            return ""
        return name if trim(self.entity_ini(name, "Base", "")) == gear else ""

    def enchant_fee(self, gear):
        return int(self.craft_num("Shards", 8, "Enchant") +
                   self.craft_num("Shards.Per.Value", 0.05, "Enchant") * val(self.entity_ini(gear, "Value", "0")))

    def enchant_menu(self, shard_item):
        shard = shard_item.name
        seen, opts = set(), []
        for it in self.inv:
            if it.name in seen or not self.enchanted_name(shard, it.name):
                continue
            seen.add(it.name)
            opts.append(("%s (%s)" % (pretty(it.name), shard_words(self.enchant_fee(it.name))),
                         (lambda uid=it.uid: self.enchant(shard, uid))))
        if not opts:
            self.refuse("There's nothing in your pack the %s will bind to." % pretty(shard).lower())
            return
        need = int(self.craft_num("Level", 4, "Enchant"))
        self.show_menu("Enchant", shard, "Bind the %s into which? It's gone into the gear for good. (Shardcraft %d)"
                       % (pretty(shard).lower(), need), opts[:9] + [("Not now.", None)])

    def enchant(self, shard, uid):
        it = self.inv_item(uid)
        if it is None or self.items_held(shard) < 1:
            return
        new = self.enchanted_name(shard, it.name)
        if not new:
            return
        need = int(self.craft_num("Level", 4, "Enchant"))
        if self.skill_level("Shardcraft") < need:
            self.refuse("You need level %d Shardcraft to enchant (you have %d)." % (need, self.skill_level("Shardcraft")))
            return
        if not self.spend_shards(self.enchant_fee(it.name), "Enchanting it"):
            return
        old, wear = it.name, it.wear
        self.remove_inventory_item(shard, 1)
        it.name = new                                  # (the same piece, worn as it was: only what it is changes)
        it.wear = wear
        self.dirty_me = True
        self.play_sound("Enchant")
        self.fx_anim("Teleport_Glow", self.player.cx, self.player.cy, 600)
        self.update_skill("Shardcraft", "+" + lbstr(self.craft_num("XP", 0.8, "Enchant")))
        self.display_message("The shard melts into the %s: it's %s now." % (pretty(old).lower(), pretty(new)),
                             "ACHIEVEMENT")
