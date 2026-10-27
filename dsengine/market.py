"""The marketplace: one market for the whole world. At any market board (Market_Board, placed by
dev\\migrate\\build_town_life.py: Ashford's market and by every shardstone) a player sees everything everyone has up for
sale, and puts their own things up at their own price.

  * Selling: with the board open, right-click something in your pack: Sell on the market, then the price each and how
    many. It's listed at once, for everyone, at every board. Your listings: take things back, or change the price.
  * Buying: Buy 1 / Buy 5 at the seller's price. The gold goes into the seller's market purse, which waits for them
    (they needn't be playing); they collect it at any board.
  * What can't be dropped (quest things, the Access Crystal) can't be sold. A player has at most LISTINGS listings.

World.market (Market) keeps the listings and the purses (saved with the world); MarketMixin is the player's side."""
import logging

from dragonsword.lb import val, lbstr

from .entity import ACTIONBOXITEM, INVENTORYITEM

log = logging.getLogger("dragonsword.market")

LISTINGS = 18                       # listings a player can have up at once
MAX_PRICE = 1000000
BOARD = "Market_Board"


def pretty(name):
    return name.replace("_", " ").replace("(s)", "s")


class Market:
    def __init__(self, world):
        self.w = world
        self.listings = []          # {"id", "seller", "item", "qty", "price", "wear"}
        self.purses = {}            # seller -> gold waiting for them
        self.next_id = 1

    def listing(self, lid):
        return next((it for it in self.listings if it["id"] == lid), None)

    def of(self, seller):
        return [it for it in self.listings if it["seller"] == seller]

    def add(self, seller, item, qty, price, wear=0):
        it = {"id": self.next_id, "seller": seller, "item": item, "qty": qty, "price": price, "wear": wear}
        self.next_id += 1
        self.listings.append(it)
        return it

    def remove(self, it):
        if it in self.listings:
            self.listings.remove(it)

    def changed(self, by=None):
        """Everyone with a market board open sees the market as it is now."""
        for s in self.w.sessions.values():
            if s is not by and s.ab_mode == "Market":
                s.show_market()

    # ----- saving
    def state(self):
        return {"listings": [dict(it) for it in self.listings], "purses": {k: v for k, v in self.purses.items() if v},
                "next": self.next_id}

    def load(self, saved, old_stalls=None):
        saved = saved or {}
        for it in saved.get("listings", []):
            try:
                self.listings.append({"id": int(it["id"]), "seller": str(it["seller"]), "item": str(it["item"]),
                                      "qty": max(1, int(it["qty"])), "price": max(1, min(MAX_PRICE, int(it["price"]))),
                                      "wear": int(it.get("wear", 0))})
            except (KeyError, TypeError, ValueError):
                log.error("A broken market listing was left out")
        self.purses = {str(k): max(0, int(v)) for k, v in saved.get("purses", {}).items()}
        self.next_id = max([int(saved.get("next", 1))] + [it["id"] + 1 for it in self.listings])
        for st in (old_stalls or {}).values():          # (the stalls of before: their things listed, their takings kept)
            owner = st.get("owner")
            if not owner:
                continue
            for n, q, p, wr in st.get("items", []):
                self.add(owner, str(n), max(1, int(q)), max(1, int(p)), int(wr))
            if st.get("till"):
                self.purses[owner] = self.purses.get(owner, 0) + int(st["till"])


class MarketMixin:
    """The player's side of the marketplace (on Session)."""

    def init_market(self):
        self.market_mine = False        # the board shows only this player's listings
        self.market_ids = []            # the listing ids in the box, in order (a box item's index is into this)

    @property
    def market(self):
        return self.w.market

    def board_action(self, verb, e):
        """Trade / Examine on a market board: True if it was one."""
        if e is None or e.name != BOARD or verb not in ("Trade", "Use", "Examine"):
            return False
        if verb == "Examine":
            n = len(self.market.listings)
            self.display_message("The market board: %d listing%s from everyone. Put your own things up for sale here."
                                 % (n, "" if n == 1 else "s"), "EXAMINE")
            return True
        if self.player_distance_to(e) > 56:
            self.display_message("You are too far away!", "FAIL")
            return True
        self.market_mine = False
        self.rack_page = 1
        self.show_market(full=True)
        return True

    def market_view(self):
        """The listings the box shows: everyone's (by item, cheapest first) or just this player's."""
        lst = self.market.of(self.player_name) if self.market_mine else self.market.listings
        return sorted(lst, key=lambda it: (it["item"].lower(), it["price"], it["id"]))

    def show_market(self, full=False):
        d = self.data
        view = self.market_view()
        page_size = max(1, d.ab_columns * d.ab_rows)
        self.rack_pages = max(1, (len(view) + page_size - 1) // page_size)
        self.rack_page = min(max(1, self.rack_page), self.rack_pages)
        shown = view[(self.rack_page - 1) * page_size:self.rack_page * page_size]
        self.market_ids = [it["id"] for it in shown]
        self.rack_type = "Market"
        self.rack = [{"item": it["item"], "quantity": it["qty"]} for it in shown]
        self.ab_item_defs = [(it["item"], lbstr(it["qty"]), i) for i, it in enumerate(shown)]
        self.responses, self.response_actions = [], []
        purse = self.market.purses.get(self.player_name, 0)
        if purse:
            self.responses.append("Collect %d gold" % purse)
            self.response_actions.append("MARKET_COLLECT")
        self.responses.append("Show everyone's" if self.market_mine else "Show only mine")
        self.response_actions.append("MARKET_TOGGLE")
        if self.rack_page < self.rack_pages:
            self.responses.append("Next page")
            self.response_actions.append("NEXT")
        if self.rack_page > 1:
            self.responses.append("Previous page")
            self.response_actions.append("PREV")
        self.responses.append("Close")
        self.response_actions.append("CLOSE")
        self.ab_image = BOARD
        mine = len(self.market.of(self.player_name))
        self.ab_title = "Your listings (%d of %d)" % (mine, LISTINGS) if self.market_mine else "The market"
        self.ab_text = ""
        if full or self.ab_mode != "Market":
            self.show_action_box("Market")
        else:
            self.emit(self.box_state())

    def market_box_extra(self):
        shown = [self.market.listing(i) for i in self.market_ids]
        return {"prices": [it["price"] if it else 0 for it in shown],
                "sellers": [it["seller"] if it else "" for it in shown],
                "mine": [bool(it and it["seller"] == self.player_name) for it in shown],
                "purse": self.market.purses.get(self.player_name, 0), "only_mine": self.market_mine}

    def market_response(self, action):
        if action == "MARKET_TOGGLE":
            self.market_mine = not self.market_mine
            self.rack_page = 1
            self.show_market()
        elif action == "MARKET_COLLECT":
            gold = self.market.purses.get(self.player_name, 0)
            room = self.inventory_slots_available("Gold_Coin(s)")
            if gold <= 0:
                return
            if room <= 0:
                self.display_message("You don't have room for the gold!", "FAIL")
                return
            take = min(gold, room)
            self.market.purses[self.player_name] = gold - take
            self.add_inventory_item("Gold_Coin(s)", take, quiet=True)
            self.play_sound("Coins")
            self.display_message("You collect %d gold from your sales." % take, "SUCCESS")
            self.show_market()

    # ----- verbs in the box (and on the pack while it's open)
    def box_listing(self, e):
        i = val(e.misc)
        if not isinstance(i, int) or not 0 <= i < len(self.market_ids):
            return None
        return self.market.listing(self.market_ids[i])

    def market_verbs(self, e):
        if e.type == ACTIONBOXITEM:
            it = self.box_listing(e)
            if it is None:
                return "Examine"
            if it["seller"] == self.player_name:
                return "Take back 1,Take back all,Set price,Examine"
            return "Buy 1,Buy 5,Value,Examine"
        if e.type == INVENTORYITEM:
            return "Sell on the market,Examine" if self.can_list(e.name) else "Examine"
        return ""

    def can_list(self, name):
        return name != "Gold_Coin(s)" and val(self.entity_ini(name, "Droppable", "1")) != 0

    def market_do(self, verb, e, price=0, qty=0):
        """True if it was a market verb."""
        if self.ab_mode != "Market":
            return False
        if verb == "Sell on the market" and e.type == INVENTORYITEM:
            self.market_list(e, price, qty)
            return True
        if e.type != ACTIONBOXITEM or verb not in ("Take back 1", "Take back all", "Set price", "Buy 1", "Buy 5",
                                                   "Value"):
            return False
        it = self.box_listing(e)
        if it is None:
            self.display_message("That's gone: someone else was quicker.", "FAIL")
            self.show_market()
            return True
        mine = it["seller"] == self.player_name
        if verb == "Value":
            self.display_message("%s: %d gold each, %d for sale (%s)." %
                                 (pretty(it["item"]), it["price"], it["qty"], "yours" if mine else it["seller"]),
                                 "INFO")
        elif verb in ("Take back 1", "Take back all") and mine:
            n = 1 if verb == "Take back 1" else it["qty"]
            n = min(n, self.inventory_slots_available(it["item"]))
            if n <= 0:
                self.display_message("You don't have room in your pack!", "FAIL")
                return True
            self.add_inventory_item(it["item"], n, it["wear"], quiet=True)
            it["qty"] -= n
            if it["qty"] <= 0:
                self.market.remove(it)
            self.market.changed()
        elif verb == "Set price" and mine:
            price = int(val(price))
            if not 1 <= price <= MAX_PRICE:
                self.display_message("A price is 1 gold or more.", "FAIL")
                return True
            it["price"] = price
            self.display_message("%s: now %d gold each." % (pretty(it["item"]), price), "INFO")
            self.market.changed()
        elif verb in ("Buy 1", "Buy 5") and not mine:
            self.market_buy(it, 1 if verb == "Buy 1" else 5)
        return True

    def market_list(self, e, price, qty):
        name = e.name
        if not self.can_list(name):
            self.display_message("You can't sell that.", "FAIL")
            return
        price = int(val(price))
        if not 1 <= price <= MAX_PRICE:
            self.display_message("A price is 1 gold or more.", "FAIL")
            return
        held = self.items_held(name)
        qty = held if int(val(qty)) <= 0 else min(held, int(val(qty)))
        if qty <= 0:
            return
        mine = self.market.of(self.player_name)
        worn = self.data.item_max_dur(name) > 0
        same = None if worn else next((it for it in mine if it["item"] == name and it["price"] == price), None)
        if same is None and len(mine) >= LISTINGS:
            self.display_message("You have %d things up for sale already: take something back first." % LISTINGS,
                                 "FAIL")
            return
        if worn:                                    # (worn things one at a time: each keeps its own wear)
            n = 0
            for _ in range(qty):
                ent = next((x for x in self.inv if x.name == name), None)
                if ent is None or len(self.market.of(self.player_name)) >= LISTINGS:
                    break
                self.market.add(self.player_name, name, 1, price, self.take_inventory_entity(ent))
                n += 1
            qty = n
        else:
            self.remove_inventory_item(name, qty)
            if same is not None:
                same["qty"] += qty
            else:
                self.market.add(self.player_name, name, qty, price)
        self.display_message("You put %d %s up for sale at %d gold each. Everyone can see it at any market board." %
                             (qty, pretty(name), price), "SUCCESS")
        self.market.changed()

    def market_buy(self, it, qty):
        name, price = it["item"], it["price"]
        qty = min(qty, it["qty"], int(self.items_held("Gold_Coin(s)") // price))
        if qty <= 0:
            self.display_message("You don't have enough gold!", "FAIL")
            return
        qty = min(qty, self.inventory_slots_available(name))
        if qty <= 0:
            self.display_message("You don't have enough room in your inventory!", "FAIL")
            return
        self.remove_inventory_item("Gold_Coin(s)", price * qty)
        self.add_inventory_item(name, qty, it["wear"], quiet=True)
        it["qty"] -= qty
        if it["qty"] <= 0:
            self.market.remove(it)
        seller = it["seller"]
        self.market.purses[seller] = self.market.purses.get(seller, 0) + price * qty
        self.play_sound("Coins")
        self.display_message("You buy (%d) %s from %s for %d gold." % (qty, pretty(name), seller, price * qty),
                             "SUCCESS")
        s = self.w.sessions.get(seller)
        if s is not None and s.in_world():
            s.display_message("%s bought %d %s from you on the market for %d gold (collect it at any market board)."
                              % (self.player_name, qty, pretty(name), price * qty), "ACHIEVEMENT")
            s.play_sound("Coins")
        self.market.changed()
