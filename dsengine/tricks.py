"""Tricks: going unseen, and changing bodies.

  * Invisibility (the Invisibility Potion: Spells.ini Effect=Invisible): for a while no monster sees you, and those
    after you lose you. Strike or cast and it's over. You're a shimmer to yourself, all but nothing to others.
  * A body swap (the Swap spell: Effect=Swap, at a creature or a townsperson whose Entities.ini has Swap=1): for its
    Duration you are them - their shape and their place - and they, very confused, are in yours. You can walk, look,
    pick things up, talk and climb, but nothing that wants hands; monsters pay you no mind. When the time's up you
    snap back into your own body, wherever it has wandered. $Player.Form is the shape you're in (a cat flap's Lock:
    $Player.Form=Cat).
  * A forced change (Turn.Into, a script's: the big red button): the same, with no one to swap with."""
from dragonsword.lb import val, pretty
from .entity import NPC

SWAP_VERBS = {"Walk here", "Examine", "Pickup", "Talk to", "Climb Up", "Climb Down", "Enter", "Step Through", "Search",
              "Squeeze Through", "Peck", "Cancel", ""}


class TrickMixin:
    # ----- invisibility
    def invisible(self):
        return getattr(self, "invisible_until", 0) > self.now

    def go_invisible(self, seconds, what):
        self.invisible_until = self.now + int(seconds * 1000)
        self.player_visible = False
        for e in self.w.ents:                                   # (those after you lose you)
            if e.type == NPC and e.target is self and e.ai is not None:
                self.w.npc_give_up(e, e.ai)
        self.play_sound("Vanish")
        self.display_message("You fade away to a shimmer. No monster will see you for %d seconds, unless you strike "
                             "or cast." % seconds, "ACHIEVEMENT")          # (what: said already, as it's drunk)
        self.dirty_me = True

    def end_invisible(self, why=""):
        if not getattr(self, "invisible_until", 0):
            return
        self.invisible_until = 0
        if not self.swap:
            self.player_visible = True
        self.play_sound("Appear")
        self.display_message(why or "You flicker back into sight.", "INFO")
        self.dirty_me = True

    def break_invisibility(self):
        """A blow struck or a spell cast: seen again."""
        if self.invisible():
            self.end_invisible("You give yourself away, and flicker back into sight!")

    # ----- body swaps
    def player_form(self):
        return self.swap["form"] if self.swap else ""

    def swap_ok(self, target):
        return (target is not None and target.type == NPC and target.alive and target.ai is not None and
                val(self.entity_ini(target.name, "Swap", "0")) >= 1 and not getattr(target, "swapped_with", None))

    def swap_with(self, target, seconds, what):
        """You into target's body, it into yours, for seconds."""
        w, p = self.w, self.player
        body = self.player_sprite_base
        bx, by, bz, bmap = p.x, p.y, p.z, self.cur_map.name if self.cur_map else ""
        tx, ty, form = target.x, target.y, target.name
        self.swap = {"form": form, "body": body, "until": self.now + int(seconds * 1000), "npc": target,
                     "display": target.display, "warned": False}
        target.swapped_with = self
        w.set_entity_position(target, bx, by)                    # (it wakes up in your boots, where you stood)
        w.replace_sprite(target, body)
        target.display = "%s?" % self.player_name
        self.change_player_sprite(form)
        w.set_entity_position(p, tx, ty)
        self.player_visible = False
        self.play_sound("Swap")
        self.fx_anim("Teleport_Glow", p.cx, p.cy, 600)
        self.display_message("%s: you're a %s! For %d seconds. Your own body is over there, looking very puzzled."
                             % (what, pretty(form).lower(), seconds), "ACHIEVEMENT")
        self.check_locks(True)
        self.dirty_me = True

    def turn_into(self, form, seconds, why):
        """Into form for a while, with no one to swap with (a script's Turn.Into)."""
        if self.swap or not (self.data.loaded(form) or self.data.animation_available(form)):
            return
        self.swap = {"form": form, "body": self.player_sprite_base, "until": self.now + int(seconds * 1000),
                     "npc": None, "display": "", "warned": False}
        self.change_player_sprite(form)
        self.player_visible = False
        self.play_sound("Swap")
        self.fx_anim("Puff", self.player.cx, self.player.cy, 500)
        if why:
            self.display_message(why, "INFO")
        self.check_locks(True)
        self.dirty_me = True

    def end_swap(self, why="Time's up! You snap back into your own body."):
        sw = self.swap
        if not sw:
            return
        self.swap = None
        w, p = self.w, self.player
        e = sw["npc"]
        if e is not None:
            ex, ey = e.x, e.y
            e.swapped_with = None
            if e.alive:
                w.set_entity_position(e, p.x, p.y)               # (back in its own shape, where you left it)
                w.replace_sprite(e, sw["form"])
                e.display = sw["display"]
                w.set_entity_position(p, ex, ey)                 # (and you, where your body wandered to)
        self.change_player_sprite(sw["body"])
        self.player_visible = not self.invisible()
        self.play_sound("Swap")
        self.fx_anim("Teleport_Glow", p.cx, p.cy, 600)
        self.display_message(why, "INFO")
        self.check_locks(True)
        self.dirty_me = True

    def swap_allows(self, verb):
        """Paws, hooves and wings: only the verbs that don't need hands."""
        if not self.swap or verb in SWAP_VERBS:
            return True
        self.refuse("You can't do that as a %s." % pretty(self.swap["form"]).lower())
        return False

    def tricks_tick(self):
        if getattr(self, "invisible_until", 0) and self.now >= self.invisible_until:
            self.end_invisible()
        sw = self.swap
        if sw:
            left = sw["until"] - self.now
            if left <= 0:
                self.end_swap()
            elif left <= 5000 and not sw["warned"]:
                sw["warned"] = True
                self.display_message("Your own body is calling you back: 5 seconds!", "DAMAGE", "Denied")

    def tricks_state(self):
        st = {}
        if self.invisible():
            st["invisible_left"] = self.invisible_until - self.now
        if self.swap:
            st["swap"] = {"form": self.swap["form"], "left": max(0, self.swap["until"] - self.now)}
        return st
