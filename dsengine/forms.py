"""Stance forms: ways of holding the Shards in you, each of one stance (Cautious, Fighting, Channelling, Sneaking), taught by
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
and in woods; Calm.Animals: prey doesn't run from you). Reckless's rush, Duellist's parry, Dirty Fighting's daze and
Riposte's answer are numbers read where the blow is (player_combat.py); Sure Step's Calm, how long a fight lasts after
a blow (calm_ms)."""
from ashen import ini
from ashen.lb import val, trim, lbstr, pretty, random_number

from .entity import MAPITEM, STATICOBJECT
from .remnants import REMNANT, LIVING
from .shards import shard_words

STANCES_INI = "Stances.ini"
FORM_STANCES = ("Cautious", "Fighting", "Channelling", "Sneaking")
TEXT_KEYS = {"TITLE", "WHAT", "COLOUR", "TAUGHT.BY", "TAUGHT.IF", "TAUGHT.WORDS", "WOODS.GROUNDS"}
# The numbers in words, for the tips (the stance buttons, the journal, Bind forms), in the order they're shown: the key,
# its words ({v}: the number), how it's shown (x: a change, +15%; %: a chance, +12%; n: as it is; tiles: a reach in
# pixels, in tiles; flag: on or not; rush: Reckless's) and 1 if more is better (-1 if less is). A key added up over the
# forms (not multiplied) is in SUM_KEYS. Each is short, its number first (dev/Rules.md, Writing: a hover line).
FIGURES = (
    ("ATTACK", "{v} Accuracy", "x", 1), ("DAMAGE", "{v} Damage", "x", 1), ("DEFENCE", "{v} Defence", "x", 1),
    ("SPELL.POWER", "{v} Spell Power", "x", 1), ("SPELL.DURATION", "{v} Ward and Boost Time", "x", 1),
    ("RESIST.STATUS", "{v} Debuff Resistance", "%", 1),
    ("PARRY", "{v} Parry", "%", 1), ("DAZE", "{v} Daze", "%", 1), ("RIPOSTE", "{v} Riposte", "%", 1),
    ("RUSH.SECONDS", "{v} s", "rush", 1), ("SNEAK.ATTACK", "x{v} Unseen Damage", "n", 1),
    ("NOISE", "{v} Noise", "x", -1), ("SIGHT", "{v} Seen", "x", -1),
    ("WOODS.NOISE", "{v} Noise in Woods", "x", -1),
    ("THIEVING", "+{v} Thieving", "n", 1), ("WATCHED", "{v} Noticed When Watched", "x", -1),
    ("DRAW", "Draws Foes within {v}", "tiles", 1),
    ("HEAR.SHARDS", "Hears Shards within {v}", "tiles", 1),
    ("DRINK.REACH", "Drinks Remnants within {v}", "tiles", 1), ("DRINK.HEAL", "+{v} HP a Shard Drunk", "n", 1),
    ("CALM.ANIMALS", "Animals Stay Calm", "flag", 1),
    ("WALK", "{v} Speed", "x", 1), ("CALM", "{v} Time to Leave a Fight", "x", -1),
    ("SPELL.COST", "{v} Spell Cost", "x", -1),
    ("SPELL.HURT", "{v} Magic Damage Taken", "x", -1), ("STATUS.HURT", "{v} Debuff Time", "x", -1))
SUM_KEYS = {"PARRY", "DAZE", "RIPOSTE", "DAZE.SECONDS", "THIEVING", "DRAW", "HEAR.SHARDS", "DRINK.REACH", "DRINK.HEAL",
            "CALM.ANIMALS", "RUSH.SECONDS"}


def num_words(v):
    return ("%.2f" % v).rstrip("0").rstrip(".")


def pct_words(m):
    return "%+d%%" % round((m - 1) * 100)


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

    def calm_ms(self, ms):
        """How long after a blow you're still in a fight (hp waits to mend, sleep and encounters wait): Sure Step's
        Calm cuts it."""
        return ms * self.form_limit("Calm", self.form_product("Calm")) if self.forms_bound else ms

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
            lines.append("%s%s: %s." % (f["title"], " (bound)" if on else "",
                                        ", ".join(t for t, _ in self.form_figures(f)) or f["what"]))
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
        """Drinking: Shards on the ground within reach, drunk straight off (as picked up, and healing you)."""
        p, w = self.player, self.w
        got = 0
        flown = []
        for e in w.ents_near(p.z, p.cx, p.cy, reach):
            if e.type != MAPITEM or e.name != REMNANT or not e.alive or getattr(e, "once", False) or \
                    getattr(e, "source", "") == "MAP" or not w.visible_to(e, self):
                continue
            got += max(1, e.quantity)
            flown.append((max(1, e.quantity), e.cx, e.cy))
            m = w.maps.get(e.map)
            if e.owner is None and m is not None:
                w.remove_action_from_queue("REMOVE", e.name, "MapItem", "*", m.name, w.local_coords(m, e.x, e.y))
            w.fx_anim("Teleport_Glow", e.z, e.cx, e.cy, 400)
            w.remove_entity(e)
        if not got:
            return
        for n, x, y in flown:
            self.gather_shards(n, x, y)
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

    # ----- the numbers, in words (FIGURES): a form's, and a stance's with your bound forms
    def figure_words(self, num):
        """[(words, good)] for each number num(KEY) gives (None: not said), in FIGURES' order."""
        out = []
        for key, words, how, better in FIGURES:
            v = num(key)
            if v is None or (how == "x" and round(v, 2) == 1) or (how != "x" and v <= 0):
                continue
            good = better > 0
            if how == "x":
                s, good = pct_words(v), (v > 1) == (better > 0)
            elif how == "%":
                s = "+%d%%" % round(v)
            elif how == "tiles":
                t = round(v / (self.w.tw or 32), 1)
                s = "%s tile%s" % (num_words(t), "" if t == 1 else "s")
            else:
                s = num_words(v)
            text = words.format(v=s)
            if key == "DAZE":
                text += " (%s s)" % num_words(num("DAZE.SECONDS") or 1.5)
            elif key == "RUSH.SECONDS":
                text = "On a Kill: " + ", ".join(w.format(v=pct_words(num(k) or 1)) for k, w in (
                    ("RUSH.DAMAGE", "{v} Damage"), ("RUSH.WALK", "{v} Speed")) if round(num(k) or 1, 2) != 1) + \
                    " for " + text
            out.append((text, good))
        return out

    def stance_base(self, st, key, default=1.0):
        """A stance's own number before its forms (a blow never seen coming is every stance's, [Stances])."""
        if key == "SNEAK.ATTACK":
            return self.stance_setting("Sneak.Attack", 2.0) if st == "Sneaking" else None
        got = trim(self.data.ini_read(STANCES_INI, st, key, ""))
        return val(got) if got else default

    def form_figures(self, f):
        """What a form does, in numbers: its own changes (+40%), its chances and reaches, and what it makes of the
        stance's own chance (Wardkeeper: the 50 in 100 to shrug off a drain becomes 80)."""
        nums = f["nums"]

        def num(key):
            if key not in nums or key in SUM_KEYS:
                return nums.get(key)
            if key in ("RESIST.STATUS", "SNEAK.ATTACK"):
                b = self.stance_base(f["stance"], key, 0.0)
                return None if not b else self.form_limit(key, b * nums[key])
            return nums[key]
        return self.figure_words(num)

    def stance_figures(self, st):
        """What a stance does for you, in numbers: its own, times your bound forms of it, within [Limits]; sneaking,
        how far you're heard and seen with your Stealth. [good words, bad words]."""
        forms = self.forms_on(st)
        said = {k for f in forms for k in f["nums"]}
        sneak = st == "Sneaking"

        def num(key):
            if key in SUM_KEYS:
                return self.form_limit(key, sum(f["nums"].get(key, 0.0) for f in forms)) if key in said else None
            if sneak and key in ("NOISE", "SIGHT"):
                return None                                 # (said below, with Stealth)
            if key == "RUSH.DAMAGE" or key == "RUSH.WALK":
                v = 1.0
                for f in forms:
                    v *= f["nums"].get(key, 1.0)
                return v
            base = self.stance_base(st, key, 0.0 if key == "RESIST.STATUS" else 1.0)
            if base is None or (key not in said and not trim(self.data.ini_read(STANCES_INI, st, key, "")) and
                                key != "SNEAK.ATTACK"):
                return None
            for f in forms:
                base *= f["nums"].get(key, 1.0)
            return self.form_limit(key, base)
        lines = self.figure_words(num)
        if sneak:
            noise = self.form_limit("Noise", self.stance_base(st, "NOISE") * self.form_product_of(forms, "NOISE"))
            least = self.stance_base(st, "SIGHT.LEAST", 0.3)
            sight = self.form_limit("Sight", self.stance_base(st, "SIGHT") * self.form_product_of(forms, "SIGHT"))
            lv = self.stealth_level()
            lines[:0] = [("Heard at %d%% | Seen at %d%%%s" % (
                round(noise * self.stealth_cut("Noise", 0.3) * 100),
                round(max(least, sight * self.stealth_cut("Sight", least)) * 100),
                " (Stealth %d)" % lv if lv else ""), True)]
            lines.append(("Ends When You Attack or Cast", False))
        good = " | ".join(t for t, g in lines if g)
        bad = " | ".join(t for t, g in lines if not g)
        return [good, bad]

    @staticmethod
    def form_product_of(forms, key):
        v = 1.0
        for f in forms:
            v *= f["nums"].get(key, 1.0)
        return v

    # ----- what the page shows: your forms (the stance buttons, the journal), the ring's colours
    def forms_state(self):
        return [[f["stance"], f["title"], 1 if f["key"] in self.forms_bound else 0,
                 " | ".join(t for t, _ in self.form_figures(f)) or f["what"], f["colour"]] for f in self.forms_known()]

    def stance_tips(self):
        return {st: self.stance_figures(st) for st in FORM_STANCES}

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
