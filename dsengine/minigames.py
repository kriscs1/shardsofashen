"""Minigames on the game screen (web/js/games.js draws them; the tavern's games are tavern.py):

  * Picking a lock (a script's Play.Minigame LOCK <level> <line if lost>): the pins, one at a time, bob up and down;
    set each as it crosses the shear line (the band where the lock turns). Three slips and the pick slides out. The
    server keeps each pin's timing and judges the tap at the moment the browser says it was made, but only within
    TAP_LAG of what its own clock says (the browser can't name any moment it likes).
  * Arm wrestling at the Green Dragon's arm-wrestling table (Arm_Table): against the innkeeper, or another player
    who's sat down at it, for a stake. Push (tap) to force the arms your way; Strength makes each push count for more.
    First to pin the other's hand down wins; at the bell (ARM_SECONDS), whoever's ahead.

MinigameMixin is the player's side (Session); World.arms keeps the bouts."""
import random

from ashen.lb import val

SLIPS = 3                               # (slips of the pick before it slides out)
ARM_SECONDS = 25
ARM_STAKES = (5, 20, 50)
PUSH_MS = 70                            # (the fastest a push counts: a dozen a second)
TAP_LAG = 400                           # (ms a tap may be said to have been made before the server had it: the trip)
HOUSE = "the innkeeper"


def pin_at(pin, t):
    """Where a pin is (0 down .. 1 up) t ms after it began: it bobs, up and down, its own speed."""
    p = (t / pin["period"] + pin["phase"]) % 1.0
    return 2 * p if p < 0.5 else 2 - 2 * p


class Arms:
    """The bouts at the arm-wrestling tables: table id -> {players [a, b], stake, at (-100 a .. 100 b), ends, ...}."""

    def __init__(self, world):
        self.w = world
        self.bouts = {}
        self.waiting = {}               # table id -> (player name, stake): sat down, waiting for a challenger

    def tick(self):
        now = self.w.now
        for tid, b in list(self.bouts.items()):
            if b["house"] and now >= b["house_at"]:             # (the innkeeper leans in, steady, now and then hard)
                b["house_at"] = now + random.randint(110, 190)
                b["at"] += b["house_push"] * (2 if random.random() < 0.15 else 1)   # (its side: towards 100)
            if abs(b["at"]) >= 100 or now >= b["ends"]:
                self.finish(tid, b)
            elif now >= b["shown"] + 120:
                self.show(tid, b)

    def show(self, tid, b, **kw):
        b["shown"] = self.w.now
        for who in b["players"]:
            s = self.w.sessions.get(who)
            if s is not None and s.game is not None and s.game["game"] == "arm":
                s.game_show(bout={"players": b["players"], "at": round(b["at"], 1), "stake": b["stake"],
                                  "secs": max(0, int((b["ends"] - self.w.now) / 1000)), "me": b["players"].index(who)}, **kw)

    def finish(self, tid, b):
        del self.bouts[tid]
        a, z = b["players"]
        winner = a if b["at"] < 0 else z
        if b["at"] == 0:
            winner = random.choice(b["players"])
        pot = b["stake"] * 2
        s = self.w.sessions.get(winner)
        if s is not None and winner != HOUSE:
            s.win(pot, "arm wrestling")
        for who in b["players"]:
            s = self.w.sessions.get(who)
            if s is not None and s.game is not None and s.game["game"] == "arm":
                s.game["phase"] = "done"
                if who != winner:
                    s.play_sound("Fail")
        self.show(tid, b, winner=winner, pot=pot)


class MinigameMixin:
    """The player's side of the minigames (on Session)."""

    # ----- picking a lock
    def minigame_start(self, kind, level, lost_line):
        """Play.Minigame: the script waits (MINIGAME) till it's won (on to the next line) or lost (lost_line)."""
        kind = kind.strip().upper()
        if kind != "LOCK":
            self.log("ERROR - Script %s: Play.Minigame: no minigame %s" % (self.script_name, kind))
            return
        level = max(1, min(5, int(val(level) or 1)))
        pins = [{"period": random.randint(1300, 1800) - level * 120, "phase": random.random(),
                 "band": 0.25 + random.random() * 0.5, "width": max(0.06, 0.15 - level * 0.02)}
                for _ in range(2 + level)]
        at = self.clicked_ent if self.clicked_ent is not None and self.clicked_ent.alive else self.player
        self.game = {"game": "lock", "at": at, "phase": "pick", "pins": pins, "pin": 0, "slips": 0, "script": True,
                     "won": False, "pin_at": self.now}
        self.script_state = "MINIGAME"
        self.script_result = 0
        self.script_cancel_line = int(val(lost_line))
        self.game_show(**self.lock_view())

    def lock_view(self):
        g = self.game
        return {"pins": [{"period": p["period"], "phase": p["phase"], "band": p["band"], "width": p["width"]}
                         for p in g["pins"]], "pin": g["pin"], "slips": g["slips"], "most": SLIPS}

    def lock_input(self, do, msg):
        g = self.game
        if do != "set" or g["phase"] != "pick":
            return
        pin = g["pins"][g["pin"]]
        held = self.now - g.get("pin_at", self.now)            # (how long the pin has bobbed, by the server's clock)
        t = min(held, max(held - TAP_LAG, int(val(msg.get("ms", 0)))))
        g["pin_at"] = self.now                                  # (the page starts the next, or this one again, now)
        if abs(pin_at(pin, max(0, t)) - pin["band"]) <= pin["width"]:
            g["pin"] += 1
            self.play_sound("Lockpick")
            if g["pin"] >= len(g["pins"]):                  # (the last pin: the lock turns)
                g["phase"], g["won"] = "done", True
                self.play_sound("Unlock")
                self.game_show(opened=True, **self.lock_view())
                self.game_close()
                return
            self.game_show(set=True, **self.lock_view())
        else:
            g["slips"] += 1
            self.play_sound("Block")
            if g["slips"] >= SLIPS:
                g["phase"] = "done"
                self.game_show(**self.lock_view())
                self.game_close()
                return
            self.game_show(slipped=True, **self.lock_view())

    # ----- arm wrestling
    def arm_table(self, e):
        self.game_open("arm", e)

    def arm_view(self):
        tid = self.table_id(self.game["at"])
        w = self.w.arms.waiting.get(tid)
        return {"stakes": list(ARM_STAKES), "waiting": {"who": w[0], "stake": w[1]} if w else None}

    def arm_input(self, do, msg):
        g = self.game
        arms = self.w.arms
        tid = self.table_id(g["at"])
        bout = arms.bouts.get(tid)
        if do == "push":
            if bout is None or self.player_name not in bout["players"] or self.now - g.get("pushed", 0) < PUSH_MS:
                return
            g["pushed"] = self.now
            side = -1 if bout["players"][0] == self.player_name else 1
            strength = self.skill_level("Strength")
            bout["at"] += side * (2.2 + strength * 0.16)
            return
        if bout is not None or g["phase"] not in ("stake", "done", "wait"):
            return
        stake = int(val(msg.get("stake", 0)))
        if do == "house" and stake in ARM_STAKES:            # (the innkeeper takes you on)
            if not self.pay_stake(stake):
                return
            self.arm_begin(tid, [self.player_name, HOUSE], stake)
        elif do == "sit" and stake in ARM_STAKES and tid not in arms.waiting:   # (wait for a challenger)
            if not self.pay_stake(stake):
                return
            arms.waiting[tid] = (self.player_name, stake)
            g["phase"] = "wait"
            self.arm_show_all(tid)
        elif do == "take" and tid in arms.waiting:         # (take on whoever's sat down)
            who, stake = arms.waiting[tid]
            if who == self.player_name or not self.pay_stake(stake):
                return
            del arms.waiting[tid]
            self.arm_begin(tid, [who, self.player_name], stake)

    def arm_show_all(self, tid):
        for s in self.w.sessions.values():
            if s.in_world() and s.game is not None and s.game["game"] == "arm" and s.table_id(s.game["at"]) == tid:
                s.game_show(**s.arm_view())

    def arm_begin(self, tid, players, stake):
        arms = self.w.arms
        strength = 0
        if HOUSE in players:                                   # (the innkeeper's arm: about as strong as yours)
            strength = self.skill_level("Strength")
        arms.bouts[tid] = {"players": players, "stake": stake, "at": 0.0, "ends": self.w.now + ARM_SECONDS * 1000,
                           "house": HOUSE in players, "house_at": self.w.now + 900,
                           "house_push": 2.4 + strength * 0.12, "shown": 0}
        for who in players:
            s = self.w.sessions.get(who)
            if s is not None and s.game is not None and s.game["game"] == "arm":
                s.game["phase"] = "bout"
        self.play_sound("Drop")
        arms.show(tid, arms.bouts[tid])

    def arm_leave(self):
        """Up from the table: a stake left waiting comes back; a bout in hand is forfeit."""
        g = self.game
        if g is None or g["game"] != "arm":
            return
        tid = self.table_id(g["at"])
        arms = self.w.arms
        w = arms.waiting.get(tid)
        if w is not None and w[0] == self.player_name:
            del arms.waiting[tid]
            self.add_inventory_item("Gold_Coin(s)", w[1], quiet=True)
            self.bets = self.bets[:-1]                         # (it wasn't a bet after all)
        b = arms.bouts.get(tid)
        if b is not None and self.player_name in b["players"]:
            b["at"] = 100 if b["players"][0] == self.player_name else -100   # (you let go: they win)
