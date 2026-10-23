"""Market stalls: players sell to each other (the stalls are StaticObjects Market_Stall with Id=Stall_<n>, placed by
Dev\\migrate\\build_market.py in Ashford).

  * Browse an empty stall to claim it (one each). Its owner puts things from their pack on it at a price each
    (right-click an item in the pack: Sell here), changes prices, takes things back, and collects the takings.
  * Anyone else browses it like a shop: Buy 1 / Buy 5 at the owner's price. The gold waits in the stall for the
    owner, who needn't be playing: a stall sells while its owner is away.
  * Giving the stall up hands back what's on it (and the takings) and frees it for someone else.

World.market (Market) keeps the stalls (saved with the world); MarketMixin is the player's side (Session)."""
import logging

from dragonsword.lb import val, lbstr

from .entity import Entity, ACTIONBOXITEM, INVENTORYITEM

log = logging.getLogger("dragonsword.market")

SLOTS = 18                          # things a stall can have out at once
MAX_PRICE = 1000000
STALL, STALL_OPEN = "Market_Stall", "Market_Stall_Open"


def pretty(name):
    return name.replace("_", " ").replace("(s)", "s")


class Market:
    def __init__(self, world):
        self.w = world
        self.stalls = {}            # stall id -> {"owner": name or None, "items": [[name, qty, price, wear]], "till": gold}

    def stall(self, sid):
        return self.stalls.setdefault(sid, {"owner": None, "items": [], "till": 0})

    def stall_of(self, owner):
        return next((sid for sid, st in self.stalls.items() if st["owner"] == owner), None)

    def entity(self, sid):
        return self.w.placed_entity(sid.upper())

    def show(self, sid):
        """The stall's picture: goods out on it, or bare."""
        e = self.entity(sid)
        st = self.stalls.get(sid)
        if e is None:
            return
        want = STALL_OPEN if st and st["items"] else STALL
        if e.name != want:
            self.w.replace_sprite(e, want)
            e.use_words = self.w.data.entity_ini(want, "Use.Words", "")

    def changed(self, sid, by=None):
        """Everyone with this stall open sees it as it is now."""
        self.show(sid)
        for s in self.w.sessions.values():
            if s is not by and s.ab_mode == "Stall" and s.stall_open == sid:
                s.show_stall()

    # ----- saving
    def state(self):
        return {sid: {"owner": st["owner"], "items": [list(i) for i in st["items"]], "till": st["till"]}
                for sid, st in self.stalls.items() if st["owner"] or st["items"] or st["till"]}

    def load(self, saved):
        for sid, st in (saved or {}).items():
            try:
                items = [[str(n), max(1, int(q)), max(1, min(MAX_PRICE, int(p))), int(wr)]
                         for n, q, p, wr in st.get("items", [])][:SLOTS]
                self.stalls[str(sid)] = {"owner": st.get("owner") or None, "items": items,
                                         "till": max(0, int(st.get("till", 0)))}
            except (TypeError, ValueError):
                log.error("A broken market stall %s was left out", sid)
                continue
            self.show(str(sid))


class MarketMixin:
    """The player's side of the market (on Session)."""

    def init_market(self):
        self.stall_open = None          # the stall id this player has open (ab_mode "Stall")
        self.stall_owner = False        # ...and whether it's theirs

    @property
    def market(self):
        return self.w.market

    @staticmethod
    def is_stall(e):
        return e is not None and e.name in (STALL, STALL_OPEN)

    def stall_id(self, e):
        return e.npc_id or "Stall_%d" % e.uid

    # ----- at the stall
    def stall_action(self, verb, e):
        """Browse / Examine on a stall: True if it was one."""
        if not self.is_stall(e) or verb not in ("Browse", "Use", "Examine"):
            return False
        sid = self.stall_id(e)
        st = self.market.stall(sid)
        if verb == "Examine":
            if st["owner"] is None:
                self.display_message("An empty market stall: browse it to claim it, and sell your things from it.",
                                     "EXAMINE")
            else:
                n = sum(i[1] for i in st["items"])
                self.display_message("%s's stall: %s." % (st["owner"], "%d thing%s for sale" % (n, "" if n == 1 else "s")
                                                          if n else "nothing for sale just now"), "EXAMINE")
            return True
        if self.player_distance_to(e) > 56:
            self.display_message("You are too far away!", "FAIL")
            return True
        if st["owner"] is None:
            mine = self.market.stall_of(self.player_name)
            if mine is not None:
                self.display_message("You have a stall already. Give that one up first.", "FAIL")
                return True
            self.show_menu("Market stall", STALL, "An empty stall, free to whoever wants it. Claim it, put things "
                           "from your pack on it at your own prices, and other players can buy them - even while "
                           "you're away. The gold waits here for you.",
                           [("Claim this stall.", lambda: self.claim_stall(sid)), ("Never mind.", None)])
            return True
        self.open_stall(sid)
        return True

    def claim_stall(self, sid):
        st = self.market.stall(sid)
        if st["owner"] is not None or self.market.stall_of(self.player_name) is not None:
            self.display_message("Someone got there first.", "FAIL")
            return
        st["owner"] = self.player_name
        self.display_message("The stall is yours. Right-click things in your pack: Sell here, and set a price.",
                             "SUCCESS")
        self.market.changed(sid)
        self.open_stall(sid)

    def open_stall(self, sid):
        self.stall_open = sid
        self.stall_owner = self.market.stall(sid)["owner"] == self.player_name
        self.rack_page = 1
        self.show_stall(full=True)

    def show_stall(self, full=False):
        """The stall in the ActionBox: its things (each with its price) and, for its owner, the takings."""
        sid = self.stall_open
        st = self.market.stall(sid)
        if st["owner"] is None or (self.stall_owner and st["owner"] != self.player_name):
            self.close_action_box(-1)
            return
        self.rack_type = "Stall"
        self.rack = [{"item": n, "quantity": q, "price": p} for n, q, p, wr in st["items"]]
        self.rack_name = sid
        self.ab_item_defs = [(n, lbstr(q), i) for i, (n, q, p, wr) in enumerate(st["items"])]
        self.rack_pages = 1
        self.responses, self.response_actions = [], []
        if self.stall_owner:
            if st["till"]:
                self.responses.append("Collect %d gold" % st["till"])
                self.response_actions.append("STALL_COLLECT")
            self.responses.append("Give up the stall")
            self.response_actions.append("STALL_GIVE_UP")
        self.responses.append("Close")
        self.response_actions.append("CLOSE")
        self.ab_image = STALL_OPEN
        self.ab_title = "Your stall" if self.stall_owner else "%s's stall" % st["owner"]
        self.ab_text = ""
        if full or self.ab_mode != "Stall":
            self.show_action_box("Stall")
        else:
            self.emit(self.box_state())

    def stall_box_extra(self):
        """What box_state adds for a stall: each thing's price, and whether it's this player's."""
        st = self.market.stall(self.stall_open)
        return {"prices": [p for n, q, p, wr in st["items"]], "owner": self.stall_owner,
                "till": st["till"] if self.stall_owner else 0}

    def stall_response(self, action):
        sid = self.stall_open
        st = self.market.stall(sid)
        if action == "STALL_COLLECT" and self.stall_owner:
            gold = st["till"]
            room = self.inventory_slots_available("Gold_Coin(s)")
            if gold <= 0:
                return
            if room <= 0:
                self.display_message("You don't have room for the gold!", "FAIL")
                return
            take = min(gold, room)
            st["till"] -= take
            self.add_inventory_item("Gold_Coin(s)", take, quiet=True)
            self.play_sound("Coins")
            self.display_message("You collect %d gold from your stall." % take, "SUCCESS")
            self.show_stall()
        elif action == "STALL_GIVE_UP" and self.stall_owner:
            for n, q, p, wr in list(st["items"]):
                if self.inventory_slots_available(n) < q:
                    self.display_message("You don't have room in your pack for what's on the stall.", "FAIL")
                    return
            for n, q, p, wr in st["items"]:
                self.add_inventory_item(n, q, wr, quiet=True)
            if st["till"]:
                self.add_inventory_item("Gold_Coin(s)", st["till"], quiet=True)
            self.market.stalls[sid] = {"owner": None, "items": [], "till": 0}
            self.close_action_box(-1)
            self.display_message("You give the stall up and pack your things away.", "INFO")
            self.market.changed(sid)

    # ----- the verbs in the stall's box (and on the pack while it's open)
    def stall_verbs(self, e):
        if e.type == ACTIONBOXITEM:
            if self.stall_owner:
                return "Take back 1,Take back all,Set price,Examine"
            return "Buy 1,Buy 5,Value,Examine"
        if e.type == INVENTORYITEM:
            return "Sell here,Examine" if self.stall_owner and self.can_stock(e.name) else "Examine"
        return ""

    def can_stock(self, name):
        return name != "Gold_Coin(s)" and val(self.entity_ini(name, "Droppable", "1")) != 0

    def stall_item(self, e):
        i = val(e.misc)
        st = self.market.stall(self.stall_open)
        return (i, st["items"][i]) if isinstance(i, int) and 0 <= i < len(st["items"]) else (None, None)

    def stall_do(self, verb, e, price=0, qty=0):
        """True if it was a stall verb."""
        if self.ab_mode != "Stall" or self.stall_open is None:
            return False
        sid = self.stall_open
        st = self.market.stall(sid)
        if verb == "Sell here" and e.type == INVENTORYITEM:
            self.stall_stock(e, price, qty)
        elif verb in ("Take back 1", "Take back all") and e.type == ACTIONBOXITEM and self.stall_owner:
            i, it = self.stall_item(e)
            if it is None:
                return True
            n = 1 if verb == "Take back 1" else it[1]
            n = min(n, self.inventory_slots_available(it[0]))
            if n <= 0:
                self.display_message("You don't have room in your pack!", "FAIL")
                return True
            self.add_inventory_item(it[0], n, it[3], quiet=True)
            it[1] -= n
            if it[1] <= 0:
                st["items"].pop(i)
            self.market.changed(sid)
            self.show_stall()
        elif verb == "Set price" and e.type == ACTIONBOXITEM and self.stall_owner:
            i, it = self.stall_item(e)
            if it is None:
                return True
            price = int(val(price))
            if not 1 <= price <= MAX_PRICE:
                self.display_message("A price is 1 gold or more.", "FAIL")
                return True
            it[2] = price
            self.display_message("%s: now %d gold each." % (pretty(it[0]), price), "INFO")
            self.market.changed(sid)
            self.show_stall()
        elif verb in ("Buy 1", "Buy 5") and e.type == ACTIONBOXITEM and not self.stall_owner:
            self.stall_buy(e, 1 if verb == "Buy 1" else 5)
        elif verb == "Value" and e.type == ACTIONBOXITEM:
            i, it = self.stall_item(e)
            if it is not None:
                self.display_message("%s: %d gold each (%d for sale)." % (pretty(it[0]), it[2], it[1]), "INFO")
        else:
            return False
        return True

    def stall_stock(self, e, price, qty):
        sid = self.stall_open
        st = self.market.stall(sid)
        name = e.name
        if not self.stall_owner or not self.can_stock(name):
            self.display_message("You can't sell that here.", "FAIL")
            return
        price = int(val(price))
        if not 1 <= price <= MAX_PRICE:
            self.display_message("A price is 1 gold or more.", "FAIL")
            return
        held = self.items_held(name)
        qty = held if int(val(qty)) <= 0 else min(held, int(val(qty)))
        if qty <= 0:
            return
        worn = self.data.item_max_dur(name) > 0
        same = next((it for it in st["items"] if it[0] == name and it[2] == price and not worn), None)
        if same is None and len(st["items"]) >= SLOTS:
            self.display_message("Your stall is full (%d things at most)." % SLOTS, "FAIL")
            return
        if worn:                                    # (worn things one at a time: each keeps its own wear)
            for _ in range(qty):
                if len(st["items"]) >= SLOTS:
                    break
                ent = next((x for x in self.inv if x.name == name), None)
                if ent is None:
                    break
                wear = self.take_inventory_entity(ent)
                st["items"].append([name, 1, price, wear])
        else:
            self.remove_inventory_item(name, qty)
            if same is not None:
                same[1] += qty
            else:
                st["items"].append([name, qty, price, 0])
        self.display_message("You put %s out at %d gold each." % (pretty(name), price), "SUCCESS")
        self.market.changed(sid)
        self.show_stall()

    def stall_buy(self, e, qty):
        sid = self.stall_open
        st = self.market.stall(sid)
        i, it = self.stall_item(e)
        if it is None:
            return
        name, have, price, wear = it
        qty = min(qty, have, int(self.items_held("Gold_Coin(s)") // price))
        if qty <= 0:
            self.display_message("You don't have enough gold!", "FAIL")
            return
        qty = min(qty, self.inventory_slots_available(name))
        if qty <= 0:
            self.display_message("You don't have enough room in your inventory!", "FAIL")
            return
        self.remove_inventory_item("Gold_Coin(s)", price * qty)
        self.add_inventory_item(name, qty, wear, quiet=True)
        it[1] -= qty
        if it[1] <= 0:
            st["items"].pop(i)
        st["till"] += price * qty
        self.play_sound("Coins")
        self.display_message("You buy (%d) %s for %d gold." % (qty, pretty(name), price * qty), "SUCCESS")
        owner = self.w.sessions.get(st["owner"])
        if owner is not None and owner.in_world():
            owner.display_message("%s bought %d %s from your stall for %d gold." %
                                  (self.player_name, qty, pretty(name), price * qty), "ACHIEVEMENT")
            owner.play_sound("Coins")
        self.market.changed(sid, by=self)
        self.show_stall()
