"""What each player's browser is told every tick: the maps round them (once, and again when one changes), the things
and people on them (in full when first seen, then only what changed), their own tiles, themselves, the weather."""
import math

from .entity import PLAYER, NPC, MAPITEM, STATICOBJECT

VIEW_MAPS = 1           # the maps this far round the player's are sent (1 = the 3 x 3 the desktop game kept)


def shared_state(w, e):
    """What everyone is told of e (the same whoever's looking: worked out once a tick, entity_state adds theirs)."""
    st = {"k": e.type, "n": e.name, "i": e.image, "x": int(e.x), "y": int(e.y), "w": e.w, "h": e.h,
          "a": 1 if e.active else 0}
    if e.type == NPC:
        st["hp"] = e.hp
        st["mh"] = e.max_hp
        st["b"] = 1 if e.show_bar else 0
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
    if getattr(e, "look", 0) and e.name == e.look_of:            # (one of its kind's other colourings; not in a swap)
        st["lk"] = e.look
    if e.npc_id:
        st["id"] = e.npc_id
    if e.display:
        st["dn"] = e.display
    return st


def entity_state(w, e, viewer, shared=None):
    """shared: {uid: shared_state} for this tick's views (each thing worked out once, not once a viewer)."""
    if shared is None:
        base = shared_state(w, e)
    else:
        base = shared.get(e.uid)
        if base is None:
            base = shared[e.uid] = shared_state(w, e)
    st = dict(base)
    if e.type == STATICOBJECT and viewer.is_chest(e):
        lock = viewer.chest_lock(e)[0] if viewer.chest_locked(e) else 0     # (locked for you: its level)
        if "lk" not in base:
            st["lk"] = lock
        if lock and viewer.chest_sturdy(e):
            st["ib"] = 1                                # (iron-bound: no Break Open)
    if e.type == NPC:
        # (1: a foe; 2: can be attacked but won't come for you, a rabbit or a hen)
        st["f"] = (1 if w.stat_for(e, viewer, "aggressive") == 1 else 2) if w.hostile_for(e, viewer) else 0
        st["uw"] = viewer.companion_verbs(e, e.use_words)    # (Come along, Hire, Send away: together.py)
        if e.ai is not None and st["f"] == 1:
            # (sneaking: a foe's sight shown, as it is for you - how wide, how far, the way it looks; and how far
            # it hears you as you move now)
            cone = getattr(e.ai, "cone", 0)
            cone = 360 if cone <= 0 or cone >= 360 else round(cone * viewer.cone_factor())
            st["cone"] = [cone, round(w.stat_for(e, viewer, "aggro_range") * viewer.sight_factor()), e.direction or 4,
                          round(viewer.noise_radius() * getattr(e.ai, "hearing", 1.0))] if viewer.sneaking() else 0
    return st


def player_state(s, viewer, shared=None):
    if shared is None:
        st = own_state(s)
    else:
        base = shared.get(s.player.uid)
        if base is None:
            base = shared[s.player.uid] = own_state(s)
        st = dict(base)
    if viewer.pvp_ok(s):
        st["pvp"] = 1
    return st


def own_state(s):
    """What everyone is told of player s (pvp, the one thing that's the viewer's own, is player_state's)."""
    p = s.player
    st = {"k": PLAYER, "n": s.player_name, "i": p.image, "x": int(p.x), "y": int(p.y), "w": p.w, "h": p.h,
          "a": 1 if (s.player_visible or s.swap or s.invisible()) else 0, "hp": p.hp, "mh": s.player_max_hp,
          "b": 1 if (p.hp < s.player_max_hp or 0 <= s.now - s.player_last_combat < 5000) else 0,
          "worn": s.worn_items()}
    if s.look:
        st["look"] = s.look
    if s.sleeping():
        st["zz"] = 1
    if s.ride is not None and s.ride.e is not None:
        st["rd"] = s.ride.e.uid                         # (in a cart: drawn standing in it, carts.py)
    if s.invisible():
        st["gh"] = 1                                    # (a shimmer: faint to you, all but nothing to others)
    if s.stance and not s.swap:
        st["sc"] = s.stance                             # (its look: a ring, motes, a crouch - render.js drawStance)
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


def ents_by_map(w):
    """Everything in the world by the map it's on, (mx, my, z): made once a tick (or when things come and go) for
    every player's snapshot, not every thing looked at for each of them."""
    ents = w.ents
    key = (w.now, len(ents), id(ents[-1]) if ents else 0)
    got = getattr(w, "_ents_by_map", None)
    if got is None or got[0] != key:
        sw, sh = w.sw, w.sh
        idx = {}
        for e in ents:
            idx.setdefault((math.floor(e.x / sw), math.floor(e.y / sh), e.z), []).append(e)
        got = w._ents_by_map = (key, idx)
    return got[1]


def snapshot(w, s, shared=None):
    """The messages for player s this tick (a list). shared: one dict for all of this tick's snapshots (what's the
    same for every viewer is worked out once)."""
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
        idx = ents_by_map(w)
        mxs, mys = [m.mx for m in maps], [m.my for m in maps]
        for mx in range(min(mxs) - 1, max(mxs) + 2):           # (the maps in view, and the edge just past them)
            for my in range(min(mys) - 1, max(mys) + 2):
                for e in idx.get((mx, my, z), ()):
                    if not (x0 <= e.x <= x1 and y0 <= e.y <= y1) or not w.visible_to(e, s):
                        continue
                    seen[e.uid] = entity_state(w, e, s, shared)
        for o in w.sessions.values():
            if o is s or not o.in_world() or o.player.z != z:
                continue
            p = o.player
            if x0 <= p.x <= x1 and y0 <= p.y <= y1:
                seen[p.uid] = player_state(o, s, shared)
    known = s.view_known
    add, change = [], []
    for uid, st in seen.items():
        old = known.get(uid)
        if old is None:
            add.append(dict(st, u=uid))
        elif old != st:
            diff = {k: v for k, v in st.items() if old.get(k) != v}
            rm = [k for k in old if k not in st]
            if rm:                                      # (a stance, a spell, a sleep over: the page forgets it)
                diff["rm"] = rm
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
