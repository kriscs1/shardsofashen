"""Stance forms: ways of holding the Shards in you, each of one stance (Fighting, Channelling, Sneaking), taught by
people round the world. Every number is data\\Stances.ini: a form is a section [<Stance>.<Form>] and its numbers
multiply the stance's own (what it doesn't say is the stance's); [Limits] holds every number within reach, so a stack
can't run away. Only the bound forms of the stance you're in count: six on one stance is a specialist, two on each
all-round.

A form learnt is yours for good (Learn.Stance, or its teacher: Taught.By= and Taught.If= on its section, when you talk
to them); learnt with a place free it's bound at once, for nothing. Binding another is done at a shardstone you've
activated (Bind forms, on its travel map), for Shards (Shards.ini [Forms]); unbinding is free. Most=6 at once.

The four with code of their own: Shieldwall (Draw: monsters near come for you before your friends - npcs.py),
Listening (Hear.Shards: remnants, clusters and Shard secrets near you show), Drinking (Drink.*: remnants on the
ground near you drunk straight off, healing you; the Shards whisper), Ranger's Tread (Woods.Noise: quieter on grass
and in woods; Calm.Animals: prey doesn't run from you). Reckless's rush, Duellist's parry and Dirty Fighting's daze
are numbers read where the blow is (player_combat.py)."""
from ashen import ini
from ashen.lb import val, trim, lbstr, pretty, random_number

from .entity import MAPITEM, STATICOBJECT
from .remnants import REMNANT, LIVING
from .shards import shard_words

STANCES_INI = "Stances.ini"
FORM_STANCES = ("Fighting", "Channelling", "Sneaking")
TEXT_KEYS = {"TITLE", "WHAT", "COLOUR", "TAUGHT.BY", "TAUGHT.IF", "TAUGHT.WORDS", "WOODS.GROUNDS"}


def forms_of(data):
    """{"FIGHTING.SHIELDWALL": form} from Stances.ini, in the file's order: each form a dict of key ("Fighting.
    Shieldwall"), stance, form, title, what, colour [r,g,b], by, cond, words, nums {KEY: number} (data's cache)."""
    c = data.cache("forms")
    got = c.get("defs")
    if got is None:
        got = {}
        for sec, items in ini.sections(data.data_file(STANCES_INI)):
            stance, _, form = sec.partition(".")
            stance = stance.capitalize()
            if stance not in FORM_STANCES or not form:
                continue
            d = {k.upper(): trim(v) for k, v in items}
            colour = [int(val(x)) for x in d.get("COLOUR", "").split(",")][:3]
            got[sec.upper()] = {
                "key": "%s.%s" % (stance, form), "stance": stance, "form": form,
                "title": d.get("TITLE", "") or pretty(form), "what": d.get("WHAT", ""),
                "colour": colour if len(colour) == 3 else [200, 200, 200], "by": d.get("TAUGHT.BY", "").upper(),
                "cond": d.get("TAUGHT.IF", ""), "words": d.get("TAUGHT.WORDS", ""),
                "grounds": [g.strip().upper() for g in d.get("WOODS.GROUNDS", "").split(",") if g.strip()],
                "nums": {k: val(v) for k, v in d.items() if k not in TEXT_KEYS and not k.startswith("WHISPER.")
                         and v != ""}}
        c["defs"] = got
    return got


def form_limits(data):
    """{KEY: (least, most)} from Stances.ini [Limits] (Key=least,most)."""
    c = data.cache("forms")
    got = c.get("limits")
    if got is None:
        got = {}
        for k, v in ini.section("Limits", data.data_file(STANCES_INI)) or ():
            parts = [p.strip() for p in str(v).split(",")]
            if len(parts) == 2 and all(parts):
                got[k.upper()] = (val(parts[0]), val(parts[1]))
        c["limits"] = got
    return got


class FormMixin:
    # ----- the forms, and which of yours count now
    def form_defs(self):
        return forms_of(self.data)

    def form_def(self, key):
        """A form by its key (Fighting.Shieldwall, any case, or Stance Form): its dict, or None."""
        key = trim(str(key)).replace(" ", ".").upper()
        return self.form_defs().get(key)

    def forms_setting(self, key, default):
        return val(trim(self.data.shards_ini("Forms", key, "")) or default)

    def forms_most(self):
        return int(self.forms_setting("Most", 6))

    def forms_on(self, stance=None):
        """The bound forms of a stance (the one you're in): their dicts."""
        st = self.stance if stance is None else stance
        if not st or not self.forms_bound:
            return []
        defs = self.form_defs()
        return [f for f in (defs.get(k.upper()) for k in self.forms_bound) if f is not None and f["stance"] == st]

    def form_product(self, key):
        """Every bound form of the stance you're in, its key times the others' (1 if none says it)."""
        v = 1.0
        key = key.upper()
        for f in self.forms_on():
            v *= f["nums"].get(key, 1.0)
        return v

    def form_sum(self, key):
        """The bound forms of the stance you're in, their key added up (a chance in 100, a reach): 0 if none says it,
        held within its [Limits]."""
        key = key.upper()
        return self.form_limit(key, sum(f["nums"].get(key, 0.0) for f in self.forms_on()))

    def form_limit(self, key, v):
        lim = form_limits(self.data).get(key.upper())
        return v if lim is None else max(lim[0], min(lim[1], v))

    def rush_factor(self, key):
        """Reckless's rush after a kill: Damage and Walk times its Rush.Damage and Rush.Walk, for Rush.Seconds."""
        if key.upper() not in ("DAMAGE", "WALK") or self.now >= self.rush_until:
            return 1.0
        return self.form_product("Rush." + key)

    def draw_reach(self):
        """Shieldwall: how near a monster must be to come for you first (0: it doesn't)."""
        return self.form_sum("Draw") if self.stance == "Fighting" and self.forms_bound else 0

    # ----- learning, binding
    def learn_form(self, stance, form="", quiet=False):
        """A form taught (Learn.Stance Fighting Shieldwall): yours for good; bound at once, for nothing, if there's a
        place free. True if it was new."""
        f = self.form_def("%s.%s" % (stance, form) if form else stance)
        if f is None or f["key"] in self.forms_learnt:
            return False
        self.forms_learnt.append(f["key"])
        bound = len(self.forms_bound) < self.forms_most()
        if bound:
            self.forms_bound.append(f["key"])
        self.dirty_me = True
        if not quiet:
            self.play_sound("Stance_" + f["stance"])
            self.display_message("You learn a form of %s: %s. %s" % (f["stance"], f["title"], (
                "It's bound in you already." if bound else "Bind it at any shardstone you've woken (you have %d bound "
                                                           "already)." % len(self.forms_bound))), "ACHIEVEMENT")
        return True

    def bind_cost(self, f):
        return int(self.forms_setting("Bind." + f["form"], self.forms_setting("Bind", 8)))

    def bind_form(self, key):
        f = self.form_def(key)
        if f is None or f["key"] not in self.forms_learnt or f["key"] in self.forms_bound:
            return
        if self.stone_near() is None:
            self.refuse("A form is bound where the Shards run: at a shardstone you've woken.")
            return
        if len(self.forms_bound) >= self.forms_most():
            self.refuse("You hold %d forms already: unbind one first." % self.forms_most())
            return
        if not self.spend_shards(self.bind_cost(f), "Binding a form"):
            return
        self.forms_bound.append(f["key"])
        self.play_sound("Stone_Wake")
        self.fx_anim("Teleport_Glow", self.player.cx, self.player.cy, 600)
        self.update_skill("Shardcraft", "+" + lbstr(self.forms_setting("Bind.XP", 0.4)))
        self.display_message("The Shards settle in you in a new way: %s is bound." % f["title"], "SUCCESS")
        self.dirty_me = True

    def unbind_form(self, key):
        f = self.form_def(key)
        if f is None or f["key"] not in self.forms_bound:
            return
        self.forms_bound.remove(f["key"])
        self.play_sound("Stance_None")
        self.display_message("You let %s go. It's still yours, to bind again." % f["title"], "INFO")
        self.dirty_me = True

    # ----- the Bind forms window (a shardstone's travel map): a page of stances, then a stance's forms
    def forms_menu(self):
        if self.stone_near() is None:
            self.refuse("A form is bound where the Shards run: at a shardstone you've woken.")
            return
        known = self.forms_known()
        if not known:
            self.display_message("You know no forms yet. People round the world teach them.", "FAIL", "Denied")
            return
        lines = []
        for st in FORM_STANCES:
            mine = [f for f in known if f["stance"] == st]
            if mine:
                lines.append("%s: %s." % (st, ", ".join(f["title"] + (" (bound)" if f["key"] in self.forms_bound
                                                                      else "") for f in mine)))
        opts = [("%s forms..." % st, (lambda st=st: self.forms_stance_menu(st))) for st in FORM_STANCES
                if any(f["stance"] == st for f in known)]
        self.show_menu("Bind forms", "Shardstone", "%d of %d bound. A form counts while you're in its stance; binding "
                       "one costs Shards, letting one go costs nothing.\\%s" % (
                           len(self.forms_bound), self.forms_most(), "\\".join(lines)), opts + [("Done.", None)])

    def forms_stance_menu(self, stance):
        mine = [f for f in self.forms_known() if f["stance"] == stance]
        lines, opts = [], []
        for f in mine:
            on = f["key"] in self.forms_bound
            lines.append("%s%s: %s" % (f["title"], " (bound)" if on else "", f["what"]))
            if on:
                opts.append(("Let %s go." % f["title"], (lambda k=f["key"]: (self.unbind_form(k),
                                                                             self.forms_stance_menu(stance)))))
            else:
                opts.append(("Bind %s (%s)." % (f["title"], shard_words(self.bind_cost(f))),
                             (lambda k=f["key"]: (self.bind_form(k), self.forms_stance_menu(stance)))))
        self.show_menu("%s forms" % stance, "Shardstone", "%d of %d bound.\\%s" % (
            len(self.forms_bound), self.forms_most(), "\\".join(lines)), opts + [("Back.", self.forms_menu)])

    def forms_known(self):
        defs = self.form_defs()
        return [f for f in (defs.get(k.upper()) for k in self.forms_learnt) if f is not None]

    # ----- teachers: talking to one who teaches a form you've earned
    def form_teach(self, e, then=None):
        """Talked to NPC e: any form it teaches (Taught.By its Id, or its kind if it has none) whose Taught.If is
        true for you, and you don't know, it shows you. True if it did (their words, then, on Thank you, their talk
        as ever: then)."""
        who = (e.npc_id or e.name).upper()
        due = [f for f in self.form_defs().values() if f["by"] == who and f["key"] not in self.forms_learnt and
               (not f["cond"] or self.condition_met(f["cond"]))]
        if not due:
            return False
        text = "\\".join(f["words"] or "%s shows you a way of holding yourself: %s." % (self.display_name(e),
                                                                                          f["title"]) for f in due)
        for f in due:
            self.learn_form(f["stance"], f["form"])
        self.show_menu(self.display_name(e), e.name, self.parse_script_variables(text),     # ($Player.Brother...)
                       [("Thank you.", then)])
        return True

    # ----- the forms with code of their own, each half second (session.py's tick, after senses)
    def forms_tick(self):
        if not self.forms_bound or self.stance != "Channelling" or self.now < self.forms_at:
            return
        self.forms_at = self.now + 500
        hear, drink = self.form_sum("Hear.Shards"), self.form_sum("Drink.Reach")
        if hear > 0:
            self.hear_shards(hear)
        if drink > 0:
            self.drink_remnants(drink)
            if self.now >= self.whisper_at:
                if self.whisper_at:
                    self.shards_whisper()
                self.whisper_at = self.now + random_number(int(self.forms_setting("Whisper.Least", 90)),
                                                           int(self.forms_setting("Whisper.Most", 240))) * 1000

    def hear_shards(self, reach):
        """Listening: remnants, Shard clusters and Shard secrets within reach show (a blue mark), every few seconds
        while you're near."""
        p, w = self.player, self.w
        heard = self.__dict__.setdefault("shards_heard", {})
        for e in w.ents_near(p.z, p.cx, p.cy, reach):
            if not e.alive or self.now < heard.get(e.uid, 0) or not (
                    e.name in (REMNANT, LIVING) or e.name.startswith("Shard_Cluster") or
                    (e.type == STATICOBJECT and (e.npc_id or "").startswith("Secret_") and
                     val(self.get_attribute(e.npc_id)) <= 0)) or not w.visible_to(e, self):
                continue
            heard[e.uid] = self.now + 3000
            w.fx({"t": "mark", "kind": "shard", "u": e.uid}, e.z, e.cx, e.cy, self)
        if len(heard) > 200:
            self.shards_heard = {k: v for k, v in heard.items() if v > self.now}

    def drink_remnants(self, reach):
        """Drinking: Shard Remnants on the ground within reach, drunk straight off (as absorbed, and healing you)."""
        p, w = self.player, self.w
        got = 0
        for e in w.ents_near(p.z, p.cx, p.cy, reach):
            if e.type != MAPITEM or e.name != REMNANT or not e.alive or getattr(e, "once", False) or \
                    getattr(e, "source", "") == "MAP" or not w.visible_to(e, self):
                continue
            got += max(1, e.quantity)
            m = w.maps.get(e.map)
            if e.owner is None and m is not None:
                w.remove_action_from_queue("\t".join(["REMOVE", e.name, "MapItem", "*", m.name,
                                                      w.local_coords(m, e.x, e.y), "*"]))
            w.fx_anim("Teleport_Glow", e.z, e.cx, e.cy, 400)
            w.remove_entity(e)
        if not got:
            return
        self.play_sound("Absorb")
        self.give_shards(int(got * self.remnant_num("Absorb", 1)), "You drink %d Shard Remnant%s" % (
            got, "" if got == 1 else "s"))
        self.update_attribute("RemnantsAbsorbed", "+%d" % got)
        xp = self.remnant_num("Absorb.XP", self.remnant_num("Absorb.Magic.XP", 0.05)) * got
        if xp > 0:
            self.update_skill("Shardcraft", "+%s" % round(xp, 3), pop=False)
        heal = int(got * self.form_sum("Drink.Heal"))
        if heal > 0 and self.player.hp < self.player_max_hp:
            self.update_skill("Hitpoints", "+%d" % heal)

    def shards_whisper(self):
        lines = [f for f in (trim(self.data.ini_read(STANCES_INI, "Channelling.Drinking", "Whisper.%d" % n, ""))
                             for n in range(1, 13)) if f]
        if lines:
            self.display_message(lines[random_number(1, len(lines)) - 1], "INFO", "-")

    def woods_quiet(self):
        """Ranger's Tread: how much quieter you are on grass and in woods (Woods.Noise; 1 elsewhere)."""
        q = self.form_product("Woods.Noise")
        if q == 1:
            return 1.0
        grounds = next((f["grounds"] for f in self.forms_on() if f["grounds"]), ())
        m, tx, ty = self.w.tile_at(self.player.z, self.player.fx, self.player.fy)
        if m is None or not m.inside(tx, ty):
            return 1.0
        tile = m.tile[m.cell(tx, ty)].upper()
        return q if any(g in tile for g in grounds) else 1.0

    def calms_animals(self):
        return self.forms_bound and self.form_sum("Calm.Animals") > 0

    # ----- what the page shows: your forms (the stance buttons, the journal), the ring's colours
    def forms_state(self):
        return [[f["stance"], f["title"], 1 if f["key"] in self.forms_bound else 0, f["what"], f["colour"]]
                for f in self.forms_known()]

    def form_colours(self):
        return [f["colour"] for f in self.forms_on()]

    # ----- the admin panel's Stance forms
    def admin_forms(self):
        return [[f["key"], f["title"], 1 if f["key"] in self.forms_learnt else 0, 1 if f["key"] in self.forms_bound
                 else 0] for f in self.form_defs().values()]

    def admin_set_form(self, key, learnt, bound):
        """Learnt or forgotten, bound or not: for nothing, and past the six if wanted."""
        f = self.form_def(key)
        if f is None:
            return "No such form."
        k = f["key"]
        if learnt and k not in self.forms_learnt:
            self.forms_learnt.append(k)
        if not learnt or not bound:
            if k in self.forms_bound:
                self.forms_bound.remove(k)
        if not learnt and k in self.forms_learnt:
            self.forms_learnt.remove(k)
        if learnt and bound and k not in self.forms_bound:
            self.forms_bound.append(k)
        self.dirty_me = True
        return "%s: %s." % (f["title"], "bound" if k in self.forms_bound else "learnt, not bound"
                            if k in self.forms_learnt else "not known")
