"""The demo (dev/Roadmap-7.md): a player without the full game plays the Isle, and no skill goes past Config.ini [Demo]
Level for them. Each player's own, like a quest door: nothing in the shared world changes for them.

A session has the full game (full: the central server's word, with their ticket; an app's own game, its device's) or a
Friend Pass (friend_pass: in a game where someone who owns it is playing: server/game.py); without either it's the
demo. The engine's own sessions (tests, a game with no central server) have the full game: server/game.py says
otherwise.

  * Every way off the Isle stops at its edge: a ferry's far stop (carts.py), a teleport of any kind (scrolls, spells,
    shardstones, portals: do_pending_map_change), walking (check_map). The game says so itself, never a character,
    and the page shows what's held back once (demo event).
  * The ferry, with the papers: the demo's end (demo_end), a card of what the Isle gave you and what's left to
    ask, not a refusal; once each time in, then the line alone.
  * Past the level, the XP still comes: it's kept, and counts as soon as they have the full game (level_of_xp).
  * One found outside the Isle as they come in (a pass run out, a friend's game left) is put on the Isle's pier
    ([Demo] Return); nothing of theirs is taken."""
from ashen.lb import val

BORDER_WORDS = "That's as far as the demo goes: the full game goes on from here."
LEVEL_WORDS = "That's as far as the demo goes: level %d. What you learn from here is kept for the full game."
END_WORDS = "The Isle's story is told, as far as the demo goes: the crossing to Northport is the full game's."
END_FOUND = (   # (the end card: what the Isle gave you, each once it's yours: its picture, its words, attribute, value)
    ("Marys_Papers", "Your mother's papers, under a crowned seal", "PapersFound", 1),
    ("Ashen_Order", "An order for her papers and her child's name, signed with a hand pressed in ash", "AshenOrder", 1),
    ("Royal_Miniature", "A miniature from where only a cat could go: a crowned man, a baby in his arms", "JimmyQuest", 3),
)
END_ASK = (     # (and what's left to ask, the same way; the first that applies of the hobgoblins' two)
    ("Who signs in ash, and what do they want with Mary's child?", "AshenOrder", 1),
    ("Who is the crowned man, and whose is the baby?", "JimmyQuest", 3),
)
END_ASK_RAID = "Why would hobgoblins raid the Isle for your mother's papers?"       # (the order not found)
END_AHEAD = ("Across the strait: Northport, the mainland's towns and roads, the Wizards' Court, and the rest of the "
             "story.")
PASS_WORDS = "A Friend Pass: someone here has the full game, so it's yours too while they're in the game."
GRACE_WORDS = "Nobody here has the full game now: back to the Isle in %d seconds."
PASS_GONE_WORDS = "Nobody here has the full game now: you're back in the demo, the Isle and level %d."


class DemoMixin:
    full = True             # (the full game: server/game.py says otherwise)
    friend_pass = False     # (someone who owns it is playing here: server/game.py)
    demo_told = ()          # (what's been said this time in: "border", "level")
    demo_said = -10 ** 9    # (when the border was last said: not every step against it)
    pass_ends = 0           # (a Friend Pass ending, for one outside the Isle: when they're taken back, ms)
    pass_from = ""          # (whose it is: the host, or the friend who owns it)

    def demo(self):
        """Playing the demo: neither the full game nor a Friend Pass, and the game has a demo ([Demo] Area)."""
        return not (self.full or self.friend_pass) and bool(self.data.demo["area"])

    def demo_map(self, name):
        """Whether a map (its X,Y,Z name) is in the demo."""
        area = self.data.demo["area"]
        try:
            x, y, z = (int(v) for v in str(name).split(","))
        except ValueError:
            return False
        return any(a[0] <= x <= b[0] and a[1] <= y <= b[1] and a[2] <= z <= b[2] for a, b in area)

    def demo_cap(self):
        """The most a skill's level can be just now (the demo's, or the game's)."""
        top = self.data.skill_max_level
        return min(top, self.data.demo["level"]) if self.demo() else top

    def demo_say(self, why):
        """The game says what's held back (never a character), with Denied; the page's box once each time in."""
        if why != "border" or self.now - self.demo_said >= 5000:
            self.demo_said = self.now if why == "border" else self.demo_said
            self.display_message(BORDER_WORDS if why == "border" else LEVEL_WORDS % self.data.demo["level"], "FAIL",
                                 "Denied")
        if why not in self.demo_told:
            self.demo_told = tuple(self.demo_told) + (why,)
            self.emit({"t": "demo", "why": why, "level": self.data.demo["level"]})

    def demo_end(self):
        """The ferry, papers in hand: the Isle's story is done, as far as the demo goes. A line (its own sound, not a
        refusal's), and the end card once each time in: what the Isle gave you, what's left to ask, what's ahead."""
        if self.now - self.demo_said < 5000:
            return
        self.demo_said = self.now
        self.display_message(END_WORDS, "ACHIEVEMENT", "Quest")
        if "end" in self.demo_told:
            return
        self.demo_told = tuple(self.demo_told) + ("end",)
        has = lambda attr, at_least: val(self.get_attribute(attr)) >= at_least
        ask = [words for words, attr, n in END_ASK if has(attr, n)]
        if not has("AshenOrder", 1):
            ask.insert(0, END_ASK_RAID)
        self.emit({"t": "demo", "why": "end", "found": [[icon, words] for icon, words, attr, n in END_FOUND
                                                           if has(attr, n)], "ask": ask, "ahead": END_AHEAD})

    def demo_dock(self):
        """Put on the Isle's pier ([Demo] Return): found outside the demo. Its map."""
        name, x, y = self.data.demo["back"]
        m = self.w.map_named(name) or self.w.map_named(self.data.start_map)
        p = self.player
        self.stop_player_walk()
        self.w.carts.leaving(self)
        p.x, p.y, p.z = m.ox + x, m.oy + y, m.mz
        self.player_tile = None
        self.emit({"t": "teleport", "fade": True})
        return m

    def set_full(self, full, friend_pass=None):
        """The full game, or a Friend Pass, come or gone (bought, a pass run out, an owner come or gone): skills as they
        are now, and one outside the Isle in the demo is put back on its pier (server/game.py gives them a while
        first: [Demo] FriendGrace)."""
        before = (self.demo(), self.demo_cap())
        self.full = bool(full)
        if friend_pass is not None:
            self.friend_pass = bool(friend_pass)
        if (self.demo(), self.demo_cap()) == before:
            return
        self.update_max_hp()
        self.player.hp = min(self.player.hp, self.player_max_hp)
        self.dirty_me = self.dirty_quests = True
        self.check_locks(False)
        if self.demo() and self.cur_map is not None and not self.demo_map(self.cur_map.name):
            self.cur_map = None
            self.check_map()

    def demo_state(self):
        """What the page shows (its badge under the Online line, the levels it works out): None, the full game."""
        if not self.data.demo["area"] or self.full:
            return None
        return {"on": self.demo(), "level": self.data.demo["level"], "pass": self.friend_pass, "from": self.pass_from,
                "ends": max(0, int(self.pass_ends - self.now)) if self.pass_ends else 0}

    def want_friend_pass(self, on, who=""):
        """The Friend Pass, as server/game.py finds it each second: someone who owns the game is here (on), or not.
        Gone, one on the Isle is in the demo at once; one outside it has [Demo] FriendGrace to get back, and is then
        taken to its pier (an owner come back in the while: it goes on as before)."""
        if self.full:
            self.pass_ends = 0
            return
        if on:
            if who != self.pass_from:
                self.pass_from, self.dirty_me = who, True
            if self.pass_ends:
                self.dirty_me = True
                self.pass_ends = 0
            elif not self.friend_pass:
                self.set_full(False, True)
                if self.data.demo["area"]:
                    self.display_message(PASS_WORDS, "INFO")
                    self.emit({"t": "demo", "why": "friend", "on": True})
            return
        if not self.friend_pass:
            return
        outside = self.cur_map is not None and not self.demo_map(self.cur_map.name)
        grace = self.data.demo["grace"]
        if outside and grace and not self.pass_ends:
            self.pass_ends = self.now + grace * 1000
            self.dirty_me = True
            self.display_message(GRACE_WORDS % grace, "FAIL", "Denied")
            return
        if outside and self.now < self.pass_ends:
            return
        self.pass_ends = 0
        self.set_full(False, False)
        self.display_message(PASS_GONE_WORDS % self.data.demo["level"], "FAIL", "Denied")
        self.emit({"t": "demo", "why": "friend", "on": False})


def read_demo(c):
    """Config.ini [Demo]: (area: [((x, y, z), (x, y, z))], level, back: (map, x, y)). No Area: no demo."""
    area = []
    for part in c("Demo", "Area", "").split(";"):
        ends = part.split()
        try:
            if len(ends) == 2:
                a, b = (tuple(int(v) for v in e.split(",")) for e in ends)
                if len(a) == len(b) == 3:
                    area.append((tuple(map(min, a, b)), tuple(map(max, a, b))))
        except ValueError:
            continue
    back = c("Demo", "Return", "").split()
    return {"area": area, "level": max(1, int(val(c("Demo", "Level", "5")) or 5)),
            "back": (back[0], val(back[1]), val(back[2])) if len(back) == 3 else (c("Gameplay", "Start.Map", ""), 0, 0),
            "grace": max(0, int(val(c("Demo", "FriendGrace", "60"))))}
