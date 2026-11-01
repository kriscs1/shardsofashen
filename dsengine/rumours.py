"""Rumours: townsfolk mention a quest you could start and haven't (the owner's wish: "I heard such and such in Ashford is
looking for help"). Each quest says what's said of it (Quests.ini Rumour=, and Rumour.2=, Rumour.3= for other ways of
putting it); the kinds who gossip say so (Entities.ini Gossip=1: build_rumours.py); how often is Config.ini [Rumours].

  * Talking to one who gossips and has no words of its own (no Talk to <its Id> script), now and then you hear a rumour
    first, then they talk as they always do. Never more than one every Every.Minutes; Chance in 100 when one's due;
    each quest's rumour Times at most; only about a quest you can start now (its needs met) and haven't.
  * A script can tell one too: Tell.Rumour [who] (nothing due: it goes straight on).
  * What you've heard is your own (attributes Rumour.At, Rumour.<quest's attribute>)."""
import random

from ashen.lb import val, trim

from .entity import NPC


class RumourMixin:
    def rumour_setting(self, key, default):
        return val(self.data.config_read("Rumours", key, default))

    def rumour_due(self, about=None):
        """(quest, its attribute, what's said) of a rumour due now, about a quest this player could start and hasn't,
        not one about (the NPC telling it, whose own quest it is); None when none is."""
        if self.rumour_setting("On", "1") != 1:
            return None
        now = self.now / 1000.0
        last = val(self.get_attribute("Rumour.At"))
        if last and 0 <= now - last < self.rumour_setting("Every.Minutes", "8") * 60:
            return None
        if random.random() * 100 >= self.rumour_setting("Chance", "35"):
            return None
        times = self.rumour_setting("Times", "2")
        own = (getattr(about, "npc_id", "") or "").lower()
        out = []
        for name, d in self.data.quest_table():
            said = [trim(v) for k, v in sorted(d.items()) if (k == "RUMOUR" or k.startswith("RUMOUR.")) and trim(v)]
            attr = d.get("ATTRIBUTE", "")
            if not said or not attr or val(self.get_attribute(attr)) > 0 or self.quest_done(name):
                continue
            if own and own in (d.get("MARKER0", "") or "").lower():
                continue                                # (not its own quest: it'd tell you itself)
            if val(self.get_attribute("Rumour." + attr)) >= times or not self.quest_can_start(name):
                continue
            out.append((name, attr, said))
        if not out:
            return None
        name, attr, said = random.choice(out)
        return name, attr, random.choice(said)

    def rumour_heard(self, attr):
        self.update_attribute("Rumour.At", "=%d" % int(self.now / 1000.0))
        self.update_attribute("Rumour." + attr, "+1")

    def gossips(self, e):
        """Does NPC e pass on what it's heard? Its kind does (Gossip=1), and it has no words of its own."""
        if e is None or e.type != NPC or trim(self.data.entity_ini(e.name, "Gossip", "0")) != "1":
            return False
        return not (e.npc_id and self.script_exists("Talk to " + e.npc_id))

    def rumour_first(self, e):
        """Talking to e: a rumour first, if one's due (True: shown, and their usual talk follows when it's answered)."""
        if getattr(self, "rumour_pass", None) == e.uid:
            self.rumour_pass = None                     # (the rumour told: now what they always say)
            return False
        if not self.gossips(e):
            return False
        r = self.rumour_due(e)
        if r is None:
            return False
        self.rumour_heard(r[1])

        def go_on():
            self.rumour_pass = e.uid
            self.do_action("Talk to", e)
        self.show_menu(self.display_name(e), self.npc_image(e.name), r[2], [("Thanks. I'll look into it.", go_on)])
        return True

    def tell_rumour(self, who):
        """The script command Tell.Rumour [who]: a rumour, if one's due (a conversation box, its script waiting on it);
        False when none is (it goes straight on)."""
        e = getattr(self, "clicked_ent", None)
        r = self.rumour_due(e)
        if r is None:
            return False
        self.rumour_heard(r[1])
        args = [""] * 34
        args[1] = who or (e.name if e is not None and e.type == NPC else "")
        args[2] = r[2]
        args[3], args[4] = "Thanks. I'll look into it.", "0"
        self.script_args = args
        self.script_conversation()
        return True
