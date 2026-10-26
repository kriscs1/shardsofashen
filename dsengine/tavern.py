"""The tavern's games (the Green Dragon in Ashford: dev\\migrate\\build_town_life.py).

  * The innkeeper (Id=Innkeeper) plays two games against you, for a stake you choose:
      - Three Cups: a coin under one of three cups; find it and get 2.5 times your stake back.
      - High or Low: they roll a die; say whether the next roll is higher or lower; right, and you get 1.4 times
        your stake back (the same number again: the house wins).
    and sells food and drink (SHOP-Tavern).
  * Dragon Dice at a dice table (Dice_Table), for everyone: someone starts a round with a stake, and for ROUND_SECONDS
    anyone at the tavern can join by putting the same stake in. Then everyone rolls three dice; the highest takes the
    whole pot (a tie shares it). Alone at the table? The innkeeper plays you for the house.

Each game is played at a table of its own in the browser (web/js/games.js: the cups, the coin, the dice): the server
sends {"t": "game"} with what's on the table, the browser sends back the stake, the cup picked, the guess. The coin
and the dice are the server's: the browser only ever sees them once they're down.
World.tavern (Tavern) keeps the dice rounds; TavernMixin is the player's side (Session)."""
import random
import time

from dragonsword.lb import val

ROUND_SECONDS = 20
MAX_PLAYERS = 6
STAKES = (5, 20, 50, 100)
HOUSE = "the innkeeper"
GAMES = {"cups": "Three Cups", "highlow": "High or Low", "dice": "Dragon Dice", "lock": "Picking the Lock",
         "arm": "Arm Wrestling"}                 # (the last two: minigames.py)
REACH = 96                              # (how far from the innkeeper or the table you can play)


def gold_word(n):
    return "%d gold" % n


class Tavern:
    def __init__(self, world):
        self.w = world
        self.rounds = {}                # table id -> {"stake", "players": [names], "ends", "map", "table"}

    def tick(self):
        for tid, r in list(self.rounds.items()):
            if self.w.now >= r["ends"]:
                del self.rounds[tid]
                self.roll(r)

    def near(self, r):
        """Who's about (to hear the dice): everyone on the table's map and the maps round it."""
        m = self.w.maps.get(r["map"])
        near = self.w.neighbours(m) if m is not None else []
        return [s for s in self.w.sessions.values() if s.in_world() and s.cur_map in near]

    def say(self, r, text, kind="INFO", sound=None):
        hearers = {s.player_name: s for s in self.near(r)}
        for who in r["players"]:
            s = self.w.sessions.get(who)
            if s is not None and s.in_world():
                hearers[who] = s
        for s in hearers.values():
            s.display_message(text, kind)
            if sound:
                s.play_sound(sound)

    def round_view(self, tid):
        """The round at a table, for its screen: {stake, players, secs}, or None."""
        r = self.rounds.get(tid)
        if r is None:
            return None
        return {"stake": r["stake"], "players": list(r["players"]), "secs": max(0, int((r["ends"] - self.w.now) / 1000))}

    def watchers(self, tid):
        """Who has this table's screen open."""
        return [s for s in self.w.sessions.values()
                if s.in_world() and s.game is not None and s.game["game"] == "dice" and s.table_id(s.game["at"]) == tid]

    def show_table(self, tid, **kw):
        for s in self.watchers(tid):
            s.game_show(**kw)

    def roll(self, r):
        players = list(r["players"])
        stake = r["stake"]
        if len(players) == 1:
            players.append(HOUSE)
        pot = stake * len(players)
        rolls = {who: [random.randint(1, 6) for _ in range(3)] for who in players}
        best = max(sum(d) for d in rolls.values())
        winners = [who for who in players if sum(rolls[who]) == best]
        share, spare = divmod(pot, len(winners))
        paid = {}
        for i, who in enumerate(winners):
            s = self.w.sessions.get(who)
            won = share + (spare if i == 0 else 0)
            paid[who] = won
            if s is not None and who != HOUSE:
                if s.inventory_slots_available("Gold_Coin(s)") > 0:
                    s.add_inventory_item("Gold_Coin(s)", won, quiet=True)
                else:
                    s.drop_on_floor("Gold_Coin(s)", won)
        for s in self.watchers(r["table"]):
            s.game["phase"] = "done"
            s.play_sound("Dice_Roll")
            s.game_show(rolled=rolls, winners=winners, pot=pot, won=paid.get(s.player_name, 0))
            if paid.get(s.player_name):
                s.play_sound("Coins")
        if len(winners) == 1:
            self.say(r, "Dragon Dice: %s wins the pot of %s!" % (winners[0], gold_word(pot)), "ACHIEVEMENT")
        else:
            self.say(r, "Dragon Dice: a tie! %s share the pot of %s." % (" and ".join(winners), gold_word(pot)),
                     "ACHIEVEMENT")


class TavernMixin:
    """The player's side of the tavern (on Session)."""

    @property
    def tavern(self):
        return self.w.tavern

    def tavern_action(self, verb, e):
        """Talk to the innkeeper, or Play at a dice table: True if it was one of them."""
        if e is None:
            return False
        if verb == "Talk to" and getattr(e, "npc_id", "") == "Innkeeper":
            self.innkeeper_menu(e)
            return True
        if e.name == "Arm_Table" and verb in ("Play", "Use"):
            if self.player_distance_to(e) > 64:
                self.display_message("You are too far away!", "FAIL")
                return True
            self.arm_table(e)
            return True
        if e.name == "Dice_Table" and verb in ("Play", "Use"):
            if self.player_distance_to(e) > 64:
                self.display_message("You are too far away!", "FAIL")
                return True
            self.game_open("dice", e)
            return True
        return False

    def pay_stake(self, stake):
        wait = self.gamble_wait()
        if wait:
            no = "That's enough gambling for now. You can play again in %s." % (
                "a minute" if wait <= 60 else "%d minutes" % ((wait + 59) // 60))
        elif self.items_held("Gold_Coin(s)") < stake:
            no = "You haven't got %s to stake." % gold_word(stake)
        else:
            self.remove_inventory_item("Gold_Coin(s)", stake)
            self.bets.append(time.time())
            self.play_sound("Coins")
            return True
        if self.game is not None:                   # (said at the table, not in the chat)
            self.play_sound("Denied")
            self.game_show(note=no)
        else:
            self.display_message(no, "FAIL")
        return False

    def gamble_wait(self):
        """Seconds till they may bet again (Config [Gameplay] Gamble.Max.Bets in Gamble.Window.Minutes), 0 = now."""
        most = int(val(self.data.config_read("Gameplay", "Gamble.Max.Bets", "10")))
        window = val(self.data.config_read("Gameplay", "Gamble.Window.Minutes", "60")) * 60
        now = time.time()
        self.bets = [t for t in self.bets if abs(now - t) < window]
        if most <= 0 or window <= 0 or len(self.bets) < most:
            return 0
        return max(1, int(min(self.bets) + window - now))

    def win(self, amount, game):
        if self.inventory_slots_available("Gold_Coin(s)") > 0:
            self.add_inventory_item("Gold_Coin(s)", amount, quiet=True)
        else:
            self.drop_on_floor("Gold_Coin(s)", amount)
        self.play_sound("Coins")
        self.display_message("You win %s at %s!" % (gold_word(amount), game), "ACHIEVEMENT")

    # ----- the innkeeper
    def innkeeper_menu(self, e):
        self.innkeeper = e
        self.show_menu("Innkeeper", "Man", "Welcome to the Green Dragon! Something to drink? Or do you fancy your "
                       "luck at a game?",
                       [("Three Cups.", lambda: self.game_open("cups", e)),
                        ("High or Low.", lambda: self.game_open("highlow", e)),
                        ("Something to eat or drink.", self.tavern_shop),
                        ("How does Dragon Dice work?", self.dice_rules),
                        ("Goodbye.", None)])

    def tavern_shop(self):
        self.open_item_rack("SPECIFIC", "Man", "SHOP-Tavern")

    def dice_rules(self):
        self.show_menu("Innkeeper", "Man", "Dragon Dice is played at the tables, against each other. Someone puts a "
                       "stake down and everyone at the tavern has %d seconds to match it. Then you all roll three "
                       "dice, and the highest takes the lot! Nobody to play? I'll match you myself." % ROUND_SECONDS,
                       [("Thanks.", None)])

    # ----- the game table (the browser draws it; here the coin is hidden, the dice rolled and the stakes paid)
    def game_open(self, game, at):
        self.game = {"game": game, "at": at, "phase": "stake"}
        self.game_show()

    def game_show(self, **kw):
        g = self.game
        if g is None:
            return
        ev = {"t": "game", "game": g["game"], "title": GAMES[g["game"]], "phase": g["phase"], "stakes": list(STAKES),
              "gold": self.items_held("Gold_Coin(s)"), "me": self.player_name}
        if g["game"] == "dice":
            ev["round"] = self.tavern.round_view(self.table_id(g["at"]))
        elif g["game"] == "arm":
            ev.update(self.arm_view())
        ev.update(kw)
        self.emit(ev)

    def game_close(self):
        g = self.game
        if g is not None:
            if g["game"] == "arm":
                self.arm_leave()
            self.game = None
            if g.get("script"):                     # (a script's minigame: on if it was won, else to its lost line)
                self.script_result = 1 if g.get("won") else -1
            self.emit({"t": "game", "game": ""})

    def game_tick(self):
        """Walked off from the table: its screen goes."""
        g = self.game
        if g is not None and (not g["at"].alive or g["at"].z != self.player.z or
                              self.player_distance_to(g["at"]) > REACH):
            self.game_close()

    def game_input(self, msg):
        """The browser: {do: stake (stake), pick (n: 1-3), guess (higher), join, leave}."""
        g = self.game
        if g is None:
            return
        do = str(msg.get("do", ""))
        if do == "leave":
            self.game_close()
            return
        self.game_tick()
        if self.game is None:
            return
        game, phase = g["game"], g["phase"]
        if game == "lock":
            self.lock_input(do, msg)
            return
        if game == "arm":
            self.arm_input(do, msg)
            return
        if do == "stake" and phase in ("stake", "done"):
            stake = int(val(msg.get("stake", 0)))
            if stake not in STAKES:
                return
            if game == "dice":
                self.dice_start(g["at"], stake)
            elif self.pay_stake(stake):
                g["stake"] = stake
                if game == "cups":
                    g["coin"], g["phase"] = random.randint(1, 3), "pick"
                    self.play_sound("Cup_Shuffle")
                    self.game_show(stake=stake)
                else:
                    g["first"], g["phase"] = random.randint(1, 6), "guess"
                    self.play_sound("Dice_Roll")
                    self.game_show(stake=stake, first=g["first"])
        elif do == "pick" and game == "cups" and phase == "pick":
            n = int(val(msg.get("n", 0)))
            if n not in (1, 2, 3):
                return
            won = int(g["stake"] * 2.5) if n == g["coin"] else 0
            g["phase"] = "done"
            if won:
                self.win(won, GAMES[game])
            else:
                self.play_sound("Fail")
            self.game_show(stake=g["stake"], coin=g["coin"], pick=n, won=won)
        elif do == "guess" and game == "highlow" and phase == "guess":
            higher = bool(msg.get("higher"))
            second = random.randint(1, 6)
            right = second > g["first"] if higher else second < g["first"]
            won = int(g["stake"] * 1.4) if right else 0
            g["phase"] = "done"
            self.play_sound("Dice_Roll")
            if won:
                self.win(won, GAMES[game])
            self.game_show(stake=g["stake"], first=g["first"], second=second, higher=higher, won=won)
        elif do == "join" and game == "dice":
            self.dice_join(self.table_id(g["at"]))

    # ----- Dragon Dice
    def table_id(self, e):
        return e.npc_id or "Dice_Table_%d" % e.uid

    def dice_start(self, e, stake):
        tid = self.table_id(e)
        if tid in self.tavern.rounds:
            return self.dice_join(tid)
        if not self.pay_stake(stake):
            return
        r = {"stake": stake, "players": [self.player_name], "ends": self.now + ROUND_SECONDS * 1000, "map": e.map,
             "table": tid}
        self.tavern.rounds[tid] = r
        if self.game is not None:
            self.game["phase"] = "round"
        self.tavern.say(r, "%s starts a round of Dragon Dice at %s! Join at the dice table within %d seconds." %
                        (self.player_name, gold_word(stake), ROUND_SECONDS), "ACHIEVEMENT", sound="Drop")
        self.tavern.show_table(tid)

    def dice_join(self, tid):
        r = self.tavern.rounds.get(tid)
        if r is None:
            self.game_show(note="That round has been rolled already.")
            return
        if self.player_name in r["players"]:
            return
        if len(r["players"]) >= MAX_PLAYERS:
            self.game_show(note="The table is full this round.")
            return
        if not self.pay_stake(r["stake"]):
            return
        r["players"].append(self.player_name)
        if self.game is not None:
            self.game["phase"] = "round"
        self.tavern.show_table(tid)
