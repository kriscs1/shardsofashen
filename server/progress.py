"""What every character here has got to, told to the central server for its admin page (which quests get done, what
skills people have): level, skills, quests, Shards, gold, where they are. Read from the saves, so it's the same for those
playing now and those long gone, and every character on the server is told once however old it is.

Kept small: it's told only what's changed since it last heard (nothing at all when nobody's getting anywhere), every
few minutes, a few dozen characters at a time, zipped. Never a device's key, the character's look, what they carry or
what they say. DS_PROGRESS=0 keeps a server's characters to itself. A game alone or on a network has no name told
(its host's device or PC is in its name)."""
import asyncio
import hashlib
import json
import logging
import os

from ashen.lb import val
from dsengine.renames import merged_skills

log = logging.getLogger("ashen.progress")

EVERY = 300                 # (seconds between reports)
FIRST = 30                  # (seconds after it starts: catching up what a phone switched off before it could say)
BETWEEN = 10                # (seconds between reports while there's more to tell)
PAGE = 40                   # (characters in a report)
SKILLS_BEFORE = 50          # (what skills were out of in a save that doesn't say: session.py)
GOLD = "Gold_Coin(s)"


def progress_of(state, quests, skill_max):
    """What's told of one character, from its save. quests: the game's quest table [(name, {KEY: value})]."""
    scale = skill_max / max(1.0, val(state.get("skills_of", SKILLS_BEFORE)))
    told = {}
    for name, xp in (merged_skills(state.get("skills")) or {}).items():
        xp = val(xp)
        if scale < 1 and name.upper() != "HITPOINTS" and xp >= 1:
            xp = max(1.0, xp * scale)
        told[name] = [min(skill_max, max(1, int(xp))), round(min(skill_max, xp), 2)]
    attrs = {str(a[0]).lower(): a[1] for a in state.get("attributes") or [] if len(a) >= 2}
    on = {}
    for name, d in quests:
        attr = d.get("ATTRIBUTE", "").lower()
        stage = int(val(attrs.get(attr, 0))) if attr else 0
        if stage:
            done = val(d.get("DONE", "0"))
            on[name] = [stage, 1 if 0 < done <= stage else 0]
    gold = sum(int(val(i[1])) for i in state.get("inventory") or [] if len(i) >= 2 and i[0] == GOLD) + \
        sum(int(val(i[1])) for i in state.get("bank") or [] if len(i) >= 2 and i[0] == GOLD)
    return {"level": int(val(state.get("level", 1))) or 1, "shards": int(val(state.get("shards", 0))), "gold": gold,
            "map": str(state.get("map", "")), "skills": told, "quests": on}


class Reporter:
    def __init__(self, game):
        self.game = game
        self.sent = {}              # (lower name -> what was last told of them, hashed: nothing new, nothing sent)

    def on(self):
        return bool(self.game.central_url()) and os.environ.get("DS_PROGRESS", "1").strip() not in ("0", "no", "off", "false")

    def secret(self):
        """This server's own (made once, kept with the world): the central server knows its reports by the hash."""
        got = self.game.store.setting("progress_secret", "")
        if not got:
            got = os.urandom(24).hex()
            self.game.store.set_setting("progress_secret", got)
        return got

    def about(self):
        g = self.game
        public = os.environ.get("DS_PUBLIC", "").strip() in ("1", "yes", "on", "true")
        kind = "public" if public else "friends" if g.for_friends() else \
            "solo" if os.environ.get("DS_LAN", "1").strip() == "0" else "local"
        out = {"secret": self.secret(), "kind": kind, "version": g.version.get("version", ""),
               "name": g.server_name() if kind in ("public", "friends") else ""}
        if public:                  # (that it's the server listed: it says so with what it announces itself by)
            out.update(server=g.server_id(), proof=g.store.setting("central_secret", ""))
        return out

    async def report(self):
        """One report of what's changed since the last that was heard: True when there's more waiting."""
        g = self.game
        mark = val(g.store.setting("progress_mark", "0"))
        rows = g.store.characters_since(mark, PAGE)
        if not rows:
            return False
        quests, most = g.world.data.quest_table(), g.world.data.skill_max_level
        told, marks = [], {}
        for name, text, updated, owner in rows:
            try:
                state = json.loads(text)
                c = progress_of(state, quests, most)
            except (ValueError, TypeError, AttributeError):
                log.warning("%s's save couldn't be read for the central server", name)
                continue
            c["name"] = name
            c["account"] = owner[2:] if owner.startswith("a:") else ""    # (a device's own key stays here)
            seen = hashlib.md5(json.dumps(c, sort_keys=True).encode("utf-8")).hexdigest()
            if self.sent.get(name.lower()) != seen:
                c["played"] = int(val(state.get("last_seen", updated)))
                told.append(c)
                marks[name.lower()] = seen
        if told:
            got = await g.central_post("/api/game/report", {**self.about(), "characters": told}, packed=True)
            if not got or not got.get("ok"):
                return False        # (it's still all here: told next time)
            self.sent.update(marks)
        g.store.set_setting("progress_mark", repr(rows[-1][2]))
        return len(rows) >= PAGE and rows[-1][2] > mark

    async def run(self):
        await asyncio.sleep(FIRST)
        while True:
            more = False
            try:
                if self.on():
                    more = await self.report()
            except asyncio.CancelledError:
                raise
            except Exception:
                log.exception("Telling the central server how characters are getting on")
            await asyncio.sleep(BETWEEN if more else EVERY)
