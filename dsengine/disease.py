"""Diseases (data\\Diseases.ini): what gets into the blood and stays there. A monster's On.Hit can give one, as it gives
a poison; unlike a status effect it has no end of its own. It stays through death and logging off, and only what names
it in its Cures= takes it away. Malaria (a mosquito's bite; the Fever Tonic): nothing at first, then a bout of Fever
now and again, until it's cured. Numbers are in the ini; the bout itself is EFFECTS' Fever (player_combat.py)."""
from ashen.lb import pretty, random_number, trim, val

DISEASES = "Diseases.ini"


class DiseaseMixin:
    def disease_num(self, name, key, default):
        return self.data.ini_num(DISEASES, name, key, default)

    def disease_known(self, name):
        return bool(trim(self.data.ini_read(DISEASES, name, "Effect", "")))

    def disease_words(self, name):
        return trim(self.data.ini_read(DISEASES, name, "Words", ""))

    def catch_disease(self, name):
        """Bitten: it's in the blood, whatever comes of it later. A stance's shrug or something worn can stop it."""
        if name in self.diseases or self.god_mode or self.resists(name):
            return
        if random_number(1, 100) <= self.stance_num("Resist.Status", 0):
            return
        self.diseases[name] = self.now + int(self.disease_num(name, "Incubation.Seconds", 120) * 1000)
        self.display_message(trim(self.data.ini_read(DISEASES, name, "Caught", "")) or "You feel unwell.", "DAMAGE",
                             trim(self.data.ini_read(DISEASES, name, "Caught.Sound", "")) or "-")
        self.dirty_me = True

    def cure_disease(self, name):
        """A cure that names it: it's gone, and the bout it was in the middle of."""
        if self.diseases.pop(name, None) is None:
            return False
        effect = trim(self.data.ini_read(DISEASES, name, "Effect", ""))
        self.status_end(effect, quiet=True)
        self.dirty_me = True
        return True

    def disease_next_bout(self, name):
        lo = self.disease_num(name, "Every.Min.Minutes", 5)
        hi = max(lo, self.disease_num(name, "Every.Max.Minutes", 9))
        return self.now + int((lo + (hi - lo) * random_number(0, 100) / 100.0) * 60000)

    def disease_tick(self):
        if not self.diseases or self.dead_wait or self.now < self.disease_at:
            return
        self.disease_at = self.now + 1000
        for name, at in list(self.diseases.items()):
            longest = (self.disease_num(name, "Every.Max.Minutes", 9) + 5) * 60000
            if self.now >= at or at - self.now > longest:     # (when, or the clock has gone back past all reason)
                self.diseases[name] = self.disease_next_bout(name)
                self.status_start(trim(self.data.ini_read(DISEASES, name, "Effect", "")))
                self.play_sound(trim(self.data.ini_read(DISEASES, name, "Bout.Sound", "")) or "Hurt",
                                (self.player.cx, self.player.cy))

    def diseases_save(self):
        """What's left till each next bout: a bout waits for you, as a cooldown does."""
        return {k: max(0, int(v - self.now)) for k, v in self.diseases.items()}

    def diseases_load(self, saved):
        if isinstance(saved, dict):
            for name, left in saved.items():
                name = str(name)
                if self.disease_known(name):
                    self.diseases[name] = self.now + max(0, int(val(left)))

    def diseases_state(self):
        return {k: self.disease_words(k) or pretty(k) for k in self.diseases}
