"""The disguise: some folk take you for one of their own while you wear their robe (Entities.ini
Friend.If.Wearing=Mending_Robe, each player's own gear: nobody else's robe fools them for you). A blow struck, or a
spell cast, where one of them can see it ends it on that map for a while (data\\Thieving.ini [Disguise]), and those
of them near come for you."""
from ashen.lb import trim, distance
from .entity import NPC

THIEVES = "Thieving.ini"


def disguise_of(data, name):
    """The thing one of this kind takes you for a friend in (upper case), or ""."""
    return trim(data.entity_ini(name, "Friend.If.Wearing", "")).upper()


class DisguiseMixin:
    def disguise_num(self, key, default):
        return self.data.ini_num(THIEVES, "Disguise", key, default)

    def wearing(self, item):
        """Is item (upper case) on you, worn or held?"""
        return any(it and it.upper() == item for it in self.equipped[1:])

    def disguised_from(self, e):
        """Does NPC e take you for one of its own just now (its robe on you, and not seen through on its map)?"""
        a = e.ai
        dis = getattr(a, "disguise", "") if a is not None else ""
        if not dis or not self.wearing(dis):
            return False
        until = self.unmasked.get(e.map)
        return until is None or not (self.now < until <= self.now + 3600000)

    def unmask(self):
        """A blow or a spell: anyone fooled by your robe who sees it knows you now, on this map, and those near
        come for you."""
        w, p = self.w, self.player
        sight = self.disguise_num("Sight", 256)
        fooled = [e for e in w.ents if e.type == NPC and e.alive and e.z == p.z and e.ai is not None and
                  getattr(e.ai, "disguise", "") and self.disguised_from(e)]
        seen = [e for e in fooled if distance(e.cx, e.cy, p.cx, p.cy) <= sight and
                w.in_line_of_sight(e.z, e.cx, e.cy, p.cx, p.cy)]
        if not seen:
            return
        until = self.now + int(self.disguise_num("Forget", 300) * 1000)
        for m in {e.map for e in seen}:
            self.unmasked[m] = until
        come = self.disguise_num("Come", 384)
        self.display_message("They know you now: the robe won't hide you here.", "DAMAGE", "Spotted")
        for e in fooled:
            if e.map in self.unmasked and distance(e.cx, e.cy, p.cx, p.cy) <= come and w.hostile_for(e, self):
                e.in_combat = True
                e.last_combat = self.now
                if e.target is None or not e.target.in_world():
                    e.target = self
                    w.npc_start_fight(e, e.ai, self, distance(e.cx, e.cy, p.cx, p.cy))
