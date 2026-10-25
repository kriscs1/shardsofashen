"""A player's quests (Data\\Quests.ini, their attributes and journal notes), the journal's lists of what they can
make and gather (as the desktop game's quests.py and screens.py worked them out) and the quest markers on the minimap."""
from dragonsword import ini
from dragonsword.lb import val, word, trim, lbstr, pretty


def help_clean(value):
    p = value.find(";")
    if p >= 0:
        value = value[:p]
    value = trim(value)
    if value.lower() == "none" or value == "-":
        value = ""
    return value


def help_text(value):
    p = value.find("  ;")
    if p >= 0:
        value = value[:p]
    return trim(value)


class QuestMixin:
    def help_read_ini(self, file):
        out = []
        for name, items in ini.sections(self.data.data_file(file)):
            d = {}
            for k, v in items:
                d.setdefault(k.upper(), v.replace("\t", " "))
            out.append((name, d))
        return out

    # ----- what a quest needs
    def quest_stage(self, d):
        a = d.get("ATTRIBUTE", "")
        return val(self.get_attribute(a)) if a else 0

    def quest_done(self, name_or_attr):
        name, d = self.data.quest_named(name_or_attr)
        if d is None:
            return False
        done = val(d.get("DONE", "0"))
        return done > 0 and self.quest_stage(d) >= done

    def quest_needs(self, name_or_attr):
        name, d = self.data.quest_named(name_or_attr)
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
        needs = self.quest_needs(name_or_attr)
        if needs and say:
            name, _ = self.data.quest_named(name_or_attr)
            self.display_message("Quest locked: %s needs %s." % (name or name_or_attr, ", ".join(needs)), "FAIL")
        return not needs

    def quest_start_blocked(self, attr, new_value):
        name, d = self.data.quest_of_attribute(attr)
        if d is None or val(self.get_attribute(attr)) > 0 or val(new_value) <= 0:
            return False
        return not self.quest_can_start(name)

    # ----- the journal's notes
    def quest_title(self, quest):
        q = trim(quest)
        for name, d in self.help_read_ini("Quests.ini"):
            if name.lower() == q.lower() or help_clean(d.get("ATTRIBUTE", "")).lower() == q.lower():
                return name
        return q

    def quest_note(self, quest, text, done):
        quest, text = self.quest_title(quest), trim(text)
        if not quest or not text:
            return
        found = False
        for n in self.quest_notes:
            if n[0] == quest and (text == "*" or n[2].lower() == text.lower()):
                found = True
                if done:
                    n[1] = 1
        if not found and text != "*":
            if len(self.quest_notes) >= 400:
                return
            self.quest_notes.append([quest, 1 if done else 0, text])
            if not done:
                self.display_message("Journal (%s): %s" % (quest, text), "darkgreen")
        self.dirty_quests = True

    def help_attributes(self, text):
        ok = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_."
        out = []
        i = 0
        while i < len(text):
            c = text[i]
            if c == "$":
                j = i + 1
                while j < len(text) and text[j] in ok:
                    j += 1
                nm = text[i + 1:j]
                while nm.endswith("."):
                    nm = nm[:-1]
                    j -= 1
                if nm == "":
                    out.append("$")
                    i += 1
                else:
                    out.append(self.get_attribute(nm))
                    i = j
            else:
                out.append(c)
                i += 1
        return "".join(out)

    # ----- the quest list (the sidebar's Quests tab and the journal)
    def quest_list(self):
        quests = []
        for name, d in self.help_read_ini("Quests.ini"):
            attribute = help_clean(d.get("ATTRIBUTE", ""))
            done = val(help_clean(d.get("DONE", "")))
            value = val(self.get_attribute(attribute)) if attribute else 0
            status = -1
            text = ""
            if done > 0 and value >= done:
                status, text = 2, "You have finished this quest."
            elif value <= 0:
                text = help_text(d.get("STAGE0", ""))
                if text:
                    status = 1
            else:
                text = help_text(d.get("STAGE" + lbstr(int(value)), "")) or "In progress."
                status = 0
            notes = [(t, dn) for q, dn, t in self.quest_notes if q == name]
            if status < 0 and notes:
                status, text = 0, next((t for t, dn in reversed(notes) if not dn), "In progress.")
            steps = []
            last = int(done) if status == 2 else max(0, int(value))
            for n in range(0, last + 1):
                t = help_text(d.get("STAGE%d" % n, ""))
                if t:
                    steps.append([self.help_attributes(t), 1 if status == 2 or n < value else 0])
            if status >= 0 and len(quests) < 300:
                quests.append({"title": name, "giver": help_clean(d.get("GIVER", "")), "status": status,
                               "text": self.help_attributes(text), "steps": steps,
                               "notes": [[self.help_attributes(t), x] for t, x in notes],
                               "main": help_clean(d.get("TYPE", "")).lower() == "main",
                               "chapter": val(help_clean(d.get("CHAPTER", "0"))),
                               "needs": self.quest_needs(name) if status == 1 else []})

        def order(q):
            return (bool(q["needs"]), not q["main"], q["chapter"] if q["main"] else 0)
        return [q for s in (0, 1, 2) for q in sorted((q for q in quests if q["status"] == s), key=order)]

    def quest_markers(self):
        marks = []
        for name, d in self.help_read_ini("Quests.ini"):
            attribute = help_clean(d.get("ATTRIBUTE", ""))
            done = val(help_clean(d.get("DONE", "")))
            value = val(self.get_attribute(attribute)) if attribute else 0
            if done == 0 or value < done:
                where = help_text(d.get("MARKER" + lbstr(int(max(0, value))), ""))
                if value <= 0 and not where:                       # (not begun: where its giver is)
                    where = self.quest_giver_at(help_clean(d.get("GIVER", "")))
                for part in where.split(";"):
                    part = trim(part)
                    if not part:
                        continue
                    if " " in part:
                        mark = (word(part, 1), val(word(part, 2)), val(word(part, 3)))
                    else:
                        pl = self.data.place(part)
                        mark = (pl.map, pl.tx, pl.ty) if pl else None
                    if mark and len(marks) < 80:
                        marks.append(list(mark) + [name])          # (whose it is: one quest is tracked at a time)
        return marks

    def quest_giver_at(self, giver):
        """ "map tx ty" of the NPC that gives a quest (by its Id, else its name), or "" if there's none."""
        if not giver:
            return ""
        e = self.w.placed_entity(giver) or next(
            (e for e in self.w.ents if e.name.upper() == giver.upper() and e.alive and e.map), None)
        m = self.w.maps.get(e.map) if e is not None else None
        if m is None:
            return ""
        return "%s %d %d" % (m.name, int((e.cx - m.ox) // self.tw) + 1, int((e.cy - m.oy) // self.th) + 1)

    # ----- the journal's other tabs
    def help_level_short(self, skill, level):
        return bool(skill) and level > 0 and self.skill_level(skill) < level

    def help_has_ingredients(self, ingredients):
        j = 1
        while word(ingredients, j) != "":
            if self.items_held(word(ingredients, j)) < max(1, val(word(ingredients, j + 1))):
                return False
            j += 2
        return True

    def help_tool_held(self, alts):
        items = [a for a in alts.split("/") if a][:20]
        for it in reversed(items):
            if self.items_held(it) > 0:
                return it
        return ""

    def journal_data(self):
        crafts = []
        for rack, d in self.help_read_ini("ItemRacks.ini"):
            rtype = help_clean(d.get("TYPE", "")).upper()
            is_craft = rack.upper().startswith("CRAFT-") or rtype in ("CRAFT", "CRAFTING", "CREATABLES")
            if rtype in ("SHOP", "GENERAL", "SPECIFIC", "BANK"):
                is_craft = False
            if not is_craft:
                continue
            skill = help_clean(d.get("SKILL", ""))
            name = trim((rack[6:] if rack.upper().startswith("CRAFT-") else rack).replace("_", " "))
            for n in range(1, 201):
                item = help_clean(d.get("ITEM%d" % n, ""))
                if item == "":
                    break
                product = trim(word(item, 1, ","))
                if product and len(crafts) < 300:
                    ingredients = trim(word(item, 2, ","))
                    level = val(word(item, 4, ","))
                    status = 0
                    if not self.help_has_ingredients(ingredients):
                        status = 1
                    if self.help_level_short(skill, level):
                        status = 2
                    crafts.append({"product": product, "ingredients": ingredients, "xp": trim(word(item, 3, ",")),
                                   "level": level, "skill": skill, "rack": name, "status": status,
                                   "skill_xp": self.skill_xp_of(skill) if skill else 0})
        crafts = [c for s in (0, 1, 2) for c in crafts if c["status"] == s]
        gathers = []
        for name, d in self.help_read_ini("Gathering.ini"):
            gives = help_clean(d.get("GIVES", ""))
            source = help_clean(d.get("SOURCE", ""))
            verb = help_clean(d.get("VERB", ""))
            if (gives or source or verb) and len(gathers) < 300:
                tool = help_clean(d.get("TOOL", ""))
                skill = help_clean(d.get("SKILL", ""))
                level = val(help_clean(d.get("LEVEL", "")))
                missing = ""
                for t in tool.split():
                    if missing == "" and self.help_tool_held(t) == "":
                        missing = word(t, 1, "/")
                status = 2 if self.help_level_short(skill, level) else (1 if missing else 0)
                gathers.append({"title": name, "gives": gives, "source": source, "verb": verb, "tool": tool,
                                "skill": skill, "level": level, "xp": help_clean(d.get("XP", "")),
                                "where": help_text(d.get("WHERE", "")), "status": status, "missing": missing,
                                "skill_xp": self.skill_xp_of(skill) if skill else 0})
        gathers = [g for s in (0, 1, 2) for g in gathers if g["status"] == s]
        return {"t": "journal", "crafts": crafts, "gathers": gathers, "quests": self.quest_list(),
                "level": self.player_level()}
