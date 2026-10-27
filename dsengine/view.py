"""What each player's browser is told every tick: the maps round them (once, and again when one changes), the things
and people on them (in full when first seen, then only what changed), their own tiles, themselves, the weather."""
from .entity import PLAYER, NPC, MAPITEM

VIEW_MAPS = 1           # the maps this far round the player's are sent (1 = the 3 x 3 the desktop game kept)


def entity_state(w, e, viewer):
    st = {"k": e.type, "n": e.name, "i": e.image, "x": int(e.x), "y": int(e.y), "w": e.w, "h": e.h,
          "a": 1 if e.active else 0}
    if e.type == NPC:
        st["hp"] = e.hp
        st["mh"] = e.max_hp
        st["b"] = 1 if e.show_bar else 0
        st["f"] = 1 if w.hostile_for(e, viewer) else 0
        st["uw"] = e.use_words
        st["wr"] = e.weapon_range
        if e.ai is not None:
            st["un"] = e.ai.under
            st["fly"] = e.ai.flying
        held = e.frozen_until is not None and e.frozen_until > w.now
        st["fz"] = (2 if e.frozen_word == "stunned" else 1) if held else 0      # (iced over, or dazed)
    elif e.type == MAPITEM:
        st["q"] = e.quantity
    else:
        st["uw"] = e.use_words
    if e.npc_id:
        st["id"] = e.npc_id
    if e.display:
        st["dn"] = e.display
    return st


def player_state(s, viewer):
    p = s.player
    st = {"k": PLAYER, "n": s.player_name, "i": p.image, "x": int(p.x), "y": int(p.y), "w": p.w, "h": p.h,
          "a": 1 if s.player_visible else 0, "hp": p.hp, "mh": s.player_max_hp,
          "b": 1 if (p.hp < s.player_max_hp or 0 <= s.now - s.player_last_combat < 5000) else 0,
          "worn": s.worn_items()}
    if s.look:
        st["look"] = s.look
    if viewer.pvp_ok(s):
        st["pvp"] = 1
    if s.sleeping():
        st["zz"] = 1
    return st


def view_maps(w, s):
    m = s.cur_map
    if m is None:
        return []
    out = []
    for j in range(-VIEW_MAPS, VIEW_MAPS + 1):
        for i in range(-VIEW_MAPS, VIEW_MAPS + 1):
            n = w.by_pos.get((m.mx + i, m.my + j, m.mz))
            if n is not None:
                out.append(n)
    return out


def snapshot(w, s):
    """The messages for player s this tick (a list)."""
    out = []
    maps = view_maps(w, s)
    names = {m.name for m in maps}
    for m in maps:
        sent = s.sent_maps.get(m.name)
        if sent != m.version:
            s.sent_maps[m.name] = m.version
            cells = m.changes_since(sent)
            if cells:                                   # (a door opened, a tree chopped: only those tiles)
                out.append(dict(m.cells_to_client(cells), t="mapcells"))
            else:
                out.append(dict(m.to_client(), t="mapdata"))
    if s.cells_dirty:
        s.cells_dirty = False
        out.append({"t": "cells", "cells": s.cells_for_view(), "locks": s.locks_for_view()})
    if s.dirty_me:
        s.dirty_me = False
        out.append(s.me_state())
    if s.dirty_quests:
        s.dirty_quests = False
        out.append(s.quests_state())
    if s.weather_dirty:
        s.weather_dirty = False
        out.append(w.weather_state_for(s))
    # ----- things and people
    z = s.player.z
    seen = {}
    if maps:
        x0 = min(m.ox for m in maps) - 64
        y0 = min(m.oy for m in maps) - 64
        x1 = max(m.ox for m in maps) + w.sw + 64
        y1 = max(m.oy for m in maps) + w.sh + 64
        for e in w.ents:
            if e.z != z or not (x0 <= e.x <= x1 and y0 <= e.y <= y1) or not w.visible_to(e, s):
                continue
            seen[e.uid] = entity_state(w, e, s)
        for o in w.sessions.values():
            if o is s or not o.in_world() or o.player.z != z:
                continue
            p = o.player
            if x0 <= p.x <= x1 and y0 <= p.y <= y1:
                seen[p.uid] = player_state(o, s)
    known = s.view_known
    add, change = [], []
    for uid, st in seen.items():
        old = known.get(uid)
        if old is None:
            add.append(dict(st, u=uid))
        elif old != st:
            diff = {k: v for k, v in st.items() if old.get(k) != v}
            diff["u"] = uid
            change.append(diff)
    gone = [uid for uid in known if uid not in seen]
    s.view_known = seen
    p = s.player
    me = {"x": round(p.x, 1), "y": round(p.y, 1), "z": p.z, "i": p.image, "d": p.direction}
    if add or change or gone or me != getattr(s, "last_me_pos", None):
        s.last_me_pos = me
        out.append({"t": "snap", "add": add, "chg": change, "del": gone, "me": me, "maps": sorted(names),
                    "st": int(w.now)})
    return out
