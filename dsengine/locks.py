"""Locks on chests (data\\Locks.ini). Each chest has a lock of a level (0: none): a map line's Lock= (and Key=: the
item that opens it), else its kind's (Entities.ini Lock=), else by where it is: the easiest on the Isle (where you
learn to pick one), low on the mainland, harder underground, a little different chest to chest. A chest a quest needs
(its script gives a quest's own item or says quest news) is never locked.

Open it with its key; or Pick Lock (Stealth: the lockpicking game, harder the higher the lock); or Break Open
(Strength: loud, and it may take a few goes), unless it's sturdy (iron-bound: the high locks and some others, a map
line's or kind's Sturdy=): those are picked or opened with their key, never forced. Unlocked is yours alone (chests
are per player), and saved."""
import zlib

from ashen.lb import val, trim, lbstr, rnd, pretty

from .entity import STATICOBJECT

LOCKS = "Locks.ini"


class LockMixin:
    def lock_num(self, key, default):
        v = trim(self.data.ini_read(LOCKS, "Locks", key, ""))
        return val(v) if v else default

    def is_chest(self, e):
        return e is not None and e.type == STATICOBJECT and "Chest" in e.name and \
            any(v.strip() in ("Open", "Search") for v in (e.use_words or "").split(","))

    def chest_lock(self, e):
        """(level, key item) of chest e's lock (level 0: none)."""
        if not self.is_chest(e):
            return 0, ""
        key = getattr(e, "lock_key", "") or trim(self.data.entity_ini(e.name, "Key", ""))
        own = getattr(e, "lock_level", "")
        if own != "":
            return int(val(own)), key
        kind = trim(self.data.entity_ini(e.name, "Lock", ""))
        if kind != "":
            return int(val(kind)), key
        if e.owner is not None or self.chest_for_a_quest(e):
            return 0, key
        m = self.w.maps.get(e.map)
        if m is None or e.map in self.lock_text("Unlocked.Maps", "").split():
            return 0, key
        if e.map in self.lock_text("Isle.Maps", "").split():
            return int(self.lock_num("Isle.Level", 1)), key       # (the Isle's: easy, to learn on)
        base = self.lock_num("Dungeon.Level", 8) if m.mz < 0 else self.lock_num("Level", 3)
        spread = int(self.lock_num("Variance", 3))
        return int(base + zlib.crc32(self.chest_key(e).encode()) % (spread + 1)), key

    def chest_sturdy(self, e):
        """Iron-bound: it can't be broken open (a map line's or its kind's Sturdy=, else the high locks and, chest to
        chest, Sturdy.Chance in 100 of the rest; never on the Isle, where you learn both ways in)."""
        own = getattr(e, "sturdy", "") or trim(self.data.entity_ini(e.name, "Sturdy", ""))
        if own != "":
            return val(own) > 0
        if e.map in self.lock_text("Isle.Maps", "").split():
            return False
        level, _ = self.chest_lock(e)
        if level >= self.lock_num("Sturdy.Level", 9):
            return True
        return zlib.crc32(("sturdy" + self.chest_key(e)).encode()) % 100 < self.lock_num("Sturdy.Chance", 25)

    def lock_text(self, key, default):
        return trim(self.data.ini_read(LOCKS, "Locks", key, "")) or default

    def chest_for_a_quest(self, e):
        """Does its script give a quest's own item (one that can't be dropped) or say quest news?"""
        script = self.find_action_script("Open", e.name, e.type, getattr(e, "npc_id", "")) or \
            self.find_action_script("Search", e.name, e.type, getattr(e, "npc_id", ""))
        if not script:
            return False
        cache = self.data.cache("quest_chest")
        if script not in cache:
            quest = False
            for ln in self.data.read_lines(self.script_path(script)):
                parts = ln.split("\t")
                if len(parts) > 2 and parts[1] in ("Quest.Note", "Reward.Shards", "Reward.Items", "Reward.XP"):
                    quest = True
                elif len(parts) > 2 and parts[1] == "Give.Item" and \
                        trim(self.data.entity_ini(parts[2], "Droppable", "1")) == "0" and \
                        not trim(self.data.entity_ini(parts[2], "Spell", "")) and parts[2] != "Gold_Coin(s)":
                    quest = True                                   # (a quest's own thing: not a scroll, not gold)
            cache[script] = quest
        return cache[script]

    def chest_locked(self, e):
        level, _ = self.chest_lock(e)
        return level > 0 and self.chest_key(e) not in self.unlocked_chests

    def unlock_chest(self, e, how):
        self.unlocked_chests.add(self.chest_key(e))
        self.play_sound("Unlock")
        self.display_message(how, "SUCCESS")

    def lock_verbs(self, e, verbs):
        if self.chest_locked(e):
            verbs = self.add_verb(verbs, "Pick Lock")
            if not self.chest_sturdy(e):
                verbs = self.add_verb(verbs, "Break Open")
        return verbs

    def lock_do(self, verb, e):
        """Open/Search on a locked chest, Pick Lock, Break Open: True if it was one of those (and dealt with)."""
        if not self.is_chest(e) or verb not in ("Open", "Search", "Pick Lock", "Break Open"):
            return False
        level, key = self.chest_lock(e)
        if not self.chest_locked(e):
            return verb in ("Pick Lock", "Break Open")
        if verb in ("Open", "Search"):
            if key and self.items_held(key) > 0:
                self.unlock_chest(e, "You unlock it with the %s." % pretty(key))
                return False                                       # (on: it opens)
            self.display_message("It's locked.", "FAIL", "Locked")
            self.act_done(False)
            return True
        if verb == "Pick Lock":
            self.pick_chest_lock(e, level)
        elif self.chest_sturdy(e):
            self.refuse("It's bound in iron. No forcing this one.")
            self.act_done(False)
        else:
            self.break_chest_open(e, level)
        return True

    def pick_chest_lock(self, e, level):
        if self.stealth_level() < level - self.lock_num("Reach", 4):
            self.refuse("This lock is beyond your picks (Stealth %d)." % level)
            self.act_done(False)
            return
        import random
        hard = max(1, min(5, 1 + level // 5))
        pins = [{"period": random.randint(1300, 1800) - hard * 120, "phase": random.random(),
                 "band": 0.25 + random.random() * 0.5, "width": max(0.06, 0.15 - hard * 0.02)}
                for _ in range(2 + hard)]

        def done(won):
            if won and e.alive:
                self.unlock_chest(e, "The lock gives with a click.")
                self.update_skill("Stealth", "+" + lbstr(self.lock_num("Pick.XP", 0.2) + level * 0.03))
                self.act_done(True)
            elif not won:
                self.display_message("Your pick slips out of the lock.", "FAIL", "Fail")
                self.act_done(False)
        self.game = {"game": "lock", "at": e, "phase": "pick", "pins": pins, "pin": 0, "slips": 0, "script": False,
                     "won": False, "then": done}
        self.game_show(**self.lock_view())

    def break_chest_open(self, e, level):
        if self.now < self.break_at:
            return
        self.break_at = self.now + 1500
        self.player_last_combat = self.now                         # (loud: anything near hears it)
        self.play_sound("Block", (e.cx, e.cy))
        self.fx_nudge(e, 0, 2, 120)
        chance = max(5, min(90, self.lock_num("Break.Chance", 40) + (self.skill_level("Strength") - level) * 4))
        self.update_skill("Strength", "+0.02", pop=False)
        if rnd() * 100 < chance:
            self.unlock_chest(e, "The lock bursts with a crack of wood.")
            self.act_done(True)
        else:
            self.display_message("You heave at the lid. It holds.", "FAIL", "Fail")
            self.act_done(False)
