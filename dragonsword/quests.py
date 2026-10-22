"""Quests: the main story and the side quests, and what each needs before it can be started (Data\\Quests.ini):
  Type=Main             part of the main story (shown first in the journal, by Chapter); anything else is a side quest
  Chapter=3             its place in the main story
  Requires.Level=12     the player's level (player_level: Config [Gameplay] Level.Skills, Level.Best)
  Requires.Quests=The Wildwood Watch; Bog Lights     quests that must be finished first
  Requires.Skills=Woodcutting 10, Herblore 5         skill levels
A quest giver's script asks >Quest.Can.Start before offering it (and says what's missing); a script that starts a quest
anyway (Update.Attribute from 0 on its Attribute) is stopped while the quest still needs something."""
import os

from . import ini
from .lb import trim, val


class QuestMixin:
    def quests_path(self):
        return os.path.join(self.root, "Data", "Quests.ini")

    def quest_table(self):
        """[(name, {KEY: value})] of every quest, in file order (read again when the file changes)."""
        path = self.quests_path()
        try:
            stamp = os.path.getmtime(path)
        except OSError:
            return []
        if getattr(self, "_quest_table_stamp", None) != stamp:
            self._quest_table = [(name, {k.upper(): trim(v) for k, v in items}) for name, items in ini.sections(path)]
            self._quest_table_stamp = stamp
        return self._quest_table

    def quest_named(self, name_or_attr):
        """(name, data) of the quest called that, or with that Attribute (any case), or (None, None)."""
        want = trim(name_or_attr).lower()
        for name, d in self.quest_table():
            if name.lower() == want or d.get("ATTRIBUTE", "").lower() == want:
                return name, d
        return None, None

    def quest_of_attribute(self, attr):
        want = trim(attr).lower()
        for name, d in self.quest_table():
            if d.get("ATTRIBUTE", "").lower() == want:
                return name, d
        return None, None

    def quest_stage(self, d):
        a = d.get("ATTRIBUTE", "")
        return val(self.get_attribute(a)) if a else 0

    def quest_done(self, name_or_attr):
        name, d = self.quest_named(name_or_attr)
        if d is None:
            return False
        done = val(d.get("DONE", "0"))
        return done > 0 and self.quest_stage(d) >= done

    def quest_is_main(self, d):
        return d.get("TYPE", "").strip().lower() == "main"

    # ----- the player's level: how good a fighter they are, for the quests' Requires.Level
    def player_level(self):
        """The average of the player's best Config [Gameplay] Level.Best (2) of Level.Skills (Strength, Defence,
        Magic), rounded down: a swordsman and a mage of the same strength have the same level."""
        names = [s.strip() for s in self.config_read("Gameplay", "Level.Skills", "Strength,Defence,Magic").split(",")
                 if s.strip()]
        levels = sorted((self.skill_level(s) for s in names if self.skill_index(s) > 0), reverse=True)
        best = max(1, int(val(self.config_read("Gameplay", "Level.Best", "2")) or 2))
        top = levels[:best]
        return max(1, int(sum(top) / len(top))) if top else 1

    def quest_needs(self, name_or_attr):
        """What a quest still needs before it can be started, as words ([] = nothing: it can be)."""
        name, d = self.quest_named(name_or_attr)
        if d is None:
            return []
        out = []
        lvl = int(val(d.get("REQUIRES.LEVEL", "0")))
        if lvl > 0 and self.player_level() < lvl:
            out.append("level %d (you're %d)" % (lvl, self.player_level()))
        words = d.get("REQUIRES.SKILLS", "").replace(",", " ").split()
        for i in range(0, len(words) - 1, 2):
            skill, need = words[i], int(val(words[i + 1]))
            if self.skill_index(skill) > 0 and self.skill_level(skill) < need:
                out.append("%s %d" % (skill.replace("_", " "), need))
        for q in [trim(x) for x in d.get("REQUIRES.QUESTS", "").split(";") if trim(x)]:
            if not self.quest_done(q):
                out.append("\"%s\" done" % q)
        return out

    def quest_can_start(self, name_or_attr, say=True):
        """True if the quest can be started now; if not (and say), what it needs goes in the chat."""
        needs = self.quest_needs(name_or_attr)
        if needs and say:
            name, _ = self.quest_named(name_or_attr)
            self.display_message("Quest locked: %s needs %s." % (name or name_or_attr, ", ".join(needs)), "FAIL")
        return not needs

    def quest_start_blocked(self, attr, new_value):
        """A script setting attribute attr to new_value: True (and says why) if that would start a quest that still
        needs something."""
        name, d = self.quest_of_attribute(attr)
        if d is None or val(self.get_attribute(attr)) > 0 or val(new_value) <= 0:
            return False
        return not self.quest_can_start(name)
