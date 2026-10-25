"""The tavern's games (the Green Dragon in Ashford: dev\\migrate\\build_town_life.py).

  * The innkeeper (Id=Innkeeper) plays two games against you, for a stake you choose:
      - Three Cups: a coin under one of three cups; find it and get 2.5 times your stake back.
      - High or Low: they roll a die; say whether the next roll is higher or lower; right, and you get 1.4 times
        your stake back (the same number again: the house wins).
    and sells food and drink (SHOP-Tavern).
  * Dragon Dice at a dice table (Dice_Table), for everyone: someone starts a round with a stake, and for ROUND_SECONDS
    anyone at the tavern can join by putting the same stake in. Then everyone rolls three dice; the highest takes the
    whole pot (a tie shares it). Alone at the table? The innkeeper plays you for the house.

World.tavern (Tavern) keeps the dice rounds; TavernMixin is the player's side (Session)."""
import random
import time

from dragonsword.lb import val

ROUND_SECONDS = 20
MAX_PLAYERS = 6
STAKES = (5, 20, 50, 100)
HOUSE = "the innkeeper"


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

    def roll(self, r):
        players = list(r["players"])
        stake = r["stake"]
        if len(players) == 1:
            players.append(HOUSE)
            self.say(r, "Nobody else joined: %s puts %s in for the house." % (HOUSE, gold_word(stake)))
        pot = stake * len(players)
        rolls = {}
        for who in players:
            dice = [random.randint(1, 6) for _ in range(3)]
            rolls[who] = sum(dice)
            self.say(r, "%s rolls %s = %d." % (who, " + ".join(str(d) for d in dice), sum(dice)), sound="Drop")
        best = max(rolls.values())
        winners = [who for who in players if rolls[who] == best]
        share, spare = divmod(pot, len(winners))
        for i, who in enumerate(winners):
            s = self.w.sessions.get(who)
            won = share + (spare if i == 0 else 0)
            if s is not None and who != HOUSE:
                if s.inventory_slots_available("Gold_Coin(s)") > 0:
                    s.add_inventory_item("Gold_Coin(s)", won, quiet=True)
                else:
                    s.drop_on_floor("Gold_Coin(s)", won)
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
        if e.name == "Dice_Table" and verb in ("Play", "Use"):
            if self.player_distance_to(e) > 64:
                self.display_message("You are too far away!", "FAIL")
                return True
            self.dice_menu(e)
            return True
        return False

    def pay_stake(self, stake):
        wait = self.gamble_wait()
        if wait:
            self.display_message("That's enough gambling for now. You can play again in %s." % (
                "a minute" if wait <= 60 else "%d minutes" % ((wait + 59) // 60)), "FAIL")
            return False
        if self.items_held("Gold_Coin(s)") < stake:
            self.display_message("You haven't got %s to stake." % gold_word(stake), "FAIL")
            return False
        self.remove_inventory_item("Gold_Coin(s)", stake)
        self.bets.append(time.time())
        self.play_sound("Coins")
        return True

    def gamble_wait(self):
        """Seconds till they may bet again (Config [Gameplay] Gamble.Max.Bets in Gamble.Window.Minutes), 0 = now."""
        most = int(val(self.data.config_read("Gameplay", "Gamble.Max.Bets", "10")))
        window = val(self.data.config_read("Gameplay", "Gamble.Window.Minutes", "60")) * 60
        now = time.time()
        self.bets = [t for t in self.bets if abs(now - t) < window]
        if most <= 0 or window <= 0 or len(self.bets) < most:
            return 0
        return max(1, int(min(self.bets) + window - now))

    def win(self, amount):
        if self.inventory_slots_available("Gold_Coin(s)") > 0:
            self.add_inventory_item("Gold_Coin(s)", amount, quiet=True)
        else:
            self.drop_on_floor("Gold_Coin(s)", amount)
        self.play_sound("Coins")

    # ----- the innkeeper
    def innkeeper_menu(self, e):
        self.innkeeper = e
        self.show_menu("Innkeeper", "Man", "Welcome to the Green Dragon! Something to drink? Or do you fancy your "
                       "luck at a game?",
                       [("Three Cups.", lambda: self.stake_menu("Three Cups", self.three_cups)),
                        ("High or Low.", lambda: self.stake_menu("High or Low", self.high_low)),
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

    def stake_menu(self, game, then):
        opts = [("%d gold." % s, (lambda s=s: then(s))) for s in STAKES]
        opts.append(("Never mind.", None))
        self.show_menu(game, "Man", "How much will you stake?", opts)

    def three_cups(self, stake):
        if not self.pay_stake(stake):
            return
        coin = random.randint(1, 3)
        pick = lambda n: (lambda: self.three_cups_reveal(stake, coin, n))
        self.show_menu("Three Cups", "Man", "The innkeeper hides a coin under one of three cups and shuffles them "
                       "round and round... Which one?",
                       [("The left one.", pick(1)), ("The middle one.", pick(2)), ("The right one.", pick(3))])

    def three_cups_reveal(self, stake, coin, n):
        where = ("left", "middle", "right")
        if n == coin:
            won = int(stake * 2.5)
            self.win(won)
            text = "The %s cup - and there's the coin! You win %s." % (where[n - 1], gold_word(won))
            self.display_message(text, "ACHIEVEMENT")
        else:
            text = "Empty! The coin was under the %s cup. The innkeeper pockets your %s." % (where[coin - 1],
                                                                                            gold_word(stake))
            self.display_message(text, "FAIL")
        self.show_menu("Three Cups", "Man", text, [("Again!", lambda: self.stake_menu("Three Cups", self.three_cups)),
                                                   ("That's enough.", None)])

    def high_low(self, stake):
        if not self.pay_stake(stake):
            return
        first = random.randint(1, 6)
        guess = lambda higher: (lambda: self.high_low_reveal(stake, first, higher))
        self.show_menu("High or Low", "Man", "The innkeeper rolls... a %d. Will the next roll be higher, or lower? "
                       "(The same again, and the house wins.)" % first,
                       [("Higher!", guess(True)), ("Lower!", guess(False))])

    def high_low_reveal(self, stake, first, higher):
        second = random.randint(1, 6)
        right = second > first if higher else second < first
        if right:
            won = int(stake * 1.4)
            self.win(won)
            text = "A %d! You called it, and win %s." % (second, gold_word(won))
            self.display_message(text, "ACHIEVEMENT")
        else:
            text = "A %d... %s. Better luck next time." % (second, "the same again: the house wins" if second == first
                                                            else "not this time")
            self.display_message(text, "FAIL")
        self.show_menu("High or Low", "Man", text, [("Again!", lambda: self.stake_menu("High or Low", self.high_low)),
                                                    ("That's enough.", None)])

    # ----- Dragon Dice
    def table_id(self, e):
        return e.npc_id or "Dice_Table_%d" % e.uid

    def dice_menu(self, e):
        tid = self.table_id(e)
        r = self.tavern.rounds.get(tid)
        if r is None:
            opts = [("Start a round at %d gold." % s, (lambda s=s: self.dice_start(e, s))) for s in STAKES]
            opts.append(("Never mind.", None))
            self.show_menu("Dragon Dice", "Dice_Table", "Put a stake down and start a round: everyone at the tavern "
                           "has %d seconds to join. Highest roll of three dice takes the pot." % ROUND_SECONDS, opts)
            return
        left = max(0, int((r["ends"] - self.now) / 1000))
        if self.player_name in r["players"]:
            self.display_message("You're in this round: the dice roll in %d seconds." % left, "INFO")
            return
        if len(r["players"]) >= MAX_PLAYERS:
            self.display_message("The table is full this round.", "FAIL")
            return
        self.show_menu("Dragon Dice", "Dice_Table", "%s %s playing for %s each; the dice roll in %d seconds." %
                       (", ".join(r["players"]), "is" if len(r["players"]) == 1 else "are", gold_word(r["stake"]), left),
                       [("Join in (%s)." % gold_word(r["stake"]), lambda: self.dice_join(tid)), ("Never mind.", None)])

    def dice_start(self, e, stake):
        tid = self.table_id(e)
        if tid in self.tavern.rounds:
            return self.dice_join(tid)
        if not self.pay_stake(stake):
            return
        r = {"stake": stake, "players": [self.player_name], "ends": self.now + ROUND_SECONDS * 1000, "map": e.map,
             "table": tid}
        self.tavern.rounds[tid] = r
        self.tavern.say(r, "%s starts a round of Dragon Dice at %s! Join at the dice table within %d seconds." %
                        (self.player_name, gold_word(stake), ROUND_SECONDS), "ACHIEVEMENT", sound="Drop")

    def dice_join(self, tid):
        r = self.tavern.rounds.get(tid)
        if r is None:
            self.display_message("That round has been rolled already.", "FAIL")
            return
        if self.player_name in r["players"] or len(r["players"]) >= MAX_PLAYERS:
            return
        if not self.pay_stake(r["stake"]):
            return
        r["players"].append(self.player_name)
        self.tavern.say(r, "%s joins the Dragon Dice: the pot is %s." % (self.player_name,
                                                                         gold_word(r["stake"] * len(r["players"]))))
