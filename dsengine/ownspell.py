"""A spell of your own (The Spellwright, Magister Quill's quest): at the Spellwright's Lectern in the Wizards' Court you
write it, choosing its effect (a bolt at one foe, a burst round you, a frost that holds them, a ward of Shards round
you), its power (1-5, as far as your Magic goes) and its reach. What it costs and how long it rests are worked out so
that no choice is better than another for its price: Shards.ini [Spellwright].

It's the spell Own_Spell (Spells.ini has its section, a bolt, for what nothing here says), known like any other; its
page, Spellwrights_Page, is what goes on the hotbar. Write it again whenever you like, for a few Shards."""
from dragonsword.lb import val, trim, lbstr

OWN = "Own_Spell"
PAGE = "Spellwrights_Page"
QUEST = "SpellwrightQuest"
EFFECTS = {   # effect: (what it is, near and far reach words)
    "Bolt": ("a bolt of Shard light at one foe", ("near: 6 tiles", "far: 10 tiles")),
    "Burst": ("a burst of Shards at every foe round you", ("close: 3 tiles round", "wide: 5 tiles round")),
    "Frost": ("a frost that holds every foe round you still", ("close: 3 tiles round", "wide: 4 tiles round")),
    "Ward": ("a ward of Shards round you, for Defence", ("short: a minute or so", "long: two minutes or so")),
}


def own_values(effect, power, far, cost_of):
    """Spells.ini keys for a written spell. cost_of(key, default): a Shards.ini [Spellwright] number."""
    p, f = max(1, min(5, int(power))), bool(far)
    scale = p ** cost_of("Power.Exponent", 1.1) * (cost_of("Far", 1.4) if f else 1.0)
    v = {"Kind": "Scroll", "Scroll": PAGE, "Skill": "Magic", "XP": lbstr(round(0.2 + 0.1 * p, 2))}
    if effect == "Bolt":
        v.update(Effect="Bolt", Damage="%d-%d" % (2 * p, 4 * p + 1), Range=str(320 if f else 192),
                 Cooldown=lbstr(round(0.6 + 0.8 * p, 1)), Level=str(max(1, 3 * p - 2)),
                 Missile="Ice_Bolt_Missile", Impact="Ice_Burst", Sound="SpellIce")
    elif effect == "Burst":
        v.update(Effect="Area", Damage="%d-%d" % (p, 2 * p + 2), Radius=str(160 if f else 96),
                 Cooldown=lbstr(3 + 2 * p), Level=str(max(1, 3 * p - 1)), Impact="Spark", Sound="Thunderclap")
    elif effect == "Frost":
        v.update(Effect="Area", Damage="%d-%d" % (max(1, p // 2), p + 1), Radius=str(128 if f else 96),
                 Freeze=str(1 + p), **{"Freeze.Word": "frozen"}, Cooldown=lbstr(6 + 3 * p), Level=str(max(2, 3 * p)),
                 Impact="Ice_Burst", Sound="Freeze")
    else:
        effect = "Ward"
        v.update(Effect="Shield", Defence=str(2 * p), Duration=str((60 + 20 * p) if f else (30 + 10 * p)),
                 Cooldown="60", Level=str(max(1, 3 * p - 2)), Impact="Stone_Glow", Sound="SpellShield")
    v["Cost"] = str(max(1, int(round(cost_of(effect + ".Cost", 3) * scale))))
    return v


class OwnSpellMixin:
    def spellwright_num(self, key, default):
        v = trim(self.data.shards_ini("Spellwright", key, ""))
        return val(v) if v != "" else default

    def own_spell_values(self):
        o = getattr(self, "own_spell", None)
        if not o:
            return None
        return own_values(o["effect"], o["power"], o["far"], self.spellwright_num)

    def own_spell_title(self):
        o = getattr(self, "own_spell", None)
        return "%s's %s" % (self.player_name.split()[0], o["effect"]) if o else "Your Own Spell"

    def own_spell_state(self):
        """For the page (verbs.js: its title and values, as Spells.ini would have them)."""
        v = self.own_spell_values()
        return {"title": self.own_spell_title(), "v": v} if v else None

    # ----- the Spellwright's Lectern
    def lectern_write(self, e):
        if self.player_distance_to(e) > 56:
            self.refuse("You are too far away!")
            return
        if val(self.get_attribute(QUEST)) < 3:
            self.refuse("The lectern's pages are blank to you.")
            return
        self.play_sound("Paper")
        self.choose_effect()

    def choose_effect(self):
        self.show_menu("Spellwright's Lectern", "Spellwright_Lectern",
                       "A blank page, and Shard-ink. What will your spell do?",
                       [("%s: %s" % (k, d[0]), (lambda k=k: self.choose_power(k))) for k, d in EFFECTS.items()] +
                       [("Leave the page.", None)])

    def choose_power(self, effect):
        magic = self.skill_level("Magic")
        rows = []
        for p in range(1, 6):
            need = int(val(own_values(effect, p, False, self.spellwright_num)["Level"]))
            if need <= magic:
                rows.append(("Power %d (Magic %d)" % (p, need), (lambda p=p: self.choose_reach(effect, p))))
        rows = rows[-4:] or [("Power 1", lambda: self.choose_reach(effect, 1))]   # (the strongest four you can)
        self.show_menu("Spellwright's Lectern", "Spellwright_Lectern",
                       "How strong? The stronger, the more Shards it drinks, and the longer it rests. (Your Magic: %d)"
                       % magic, rows + [("Back.", self.choose_effect)])

    def choose_reach(self, effect, power):
        near, far = EFFECTS[effect][1]
        self.show_menu("Spellwright's Lectern", "Spellwright_Lectern", "And its reach?",
                       [(near[0].upper() + near[1:], lambda: self.confirm_spell(effect, power, False)),
                        (far[0].upper() + far[1:] + " (dearer)", lambda: self.confirm_spell(effect, power, True)),
                        ("Back.", lambda: self.choose_power(effect))])

    def confirm_spell(self, effect, power, far):
        v = own_values(effect, power, far, self.spellwright_num)
        fee = 0 if OWN not in self.spells_known else int(self.spellwright_num("Write", 10))
        what = self.spell_what_values(v)
        text = ("%s's %s, power %d: %s.\\It drinks %s Shards a cast and rests %s s. It needs Magic %s.%s" %
                (self.player_name.split()[0], effect, power, what, v["Cost"], v["Cooldown"], v["Level"],
                 ("\\Writing it over your old one costs %d Shards." % fee) if fee else ""))
        self.show_menu("Spellwright's Lectern", "Spellwright_Lectern", text,
                       [("Write it.", lambda: self.write_spell(effect, power, far, fee)),
                        ("Start again.", self.choose_effect), ("Leave the page.", None)])

    def spell_what_values(self, v):
        if v["Effect"] == "Shield":
            return "+%s Defence for %s s" % (v["Defence"], v["Duration"])
        words = "%s damage" % v["Damage"]
        if v["Effect"] == "Bolt":
            return words + " at one foe up to %d tiles away" % (int(v["Range"]) // 32)
        words += " to every foe within %d tiles" % (int(v["Radius"]) // 32)
        if "Freeze" in v:
            words += ", frozen for %s s" % v["Freeze"]
        return words

    def write_spell(self, effect, power, far, fee):
        if fee and not self.spend_shards(fee, "Writing it again"):
            return
        self.own_spell = {"effect": effect, "power": int(power), "far": bool(far)}
        self.spells_known[OWN] = 1
        self.cooldowns.pop(OWN, None)
        self.dirty_me = True
        self.play_sound("SpellCast")
        self.fx_anim("Teleport_Glow", self.player.cx, self.player.cy, 600)
        self.display_message("The Shard-ink settles into the page: %s is yours. (H: the journal's Spells, or put it on "
                             "the hotbar.)" % self.own_spell_title(), "ACHIEVEMENT")
