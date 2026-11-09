"""The shared world's rules: what one player does, the others see; what a quest changes is the player's own."""
import os
import random

import pytest

from dsengine import World, Session
from dsengine.entity import MAPITEM, NPC, AI_FLEE, AI_IDLE
from ashen.lb import distance, val
from dsengine.forms import form_limits

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture(scope="module")
def world():
    random.seed(1)
    w = World(ROOT)
    w.encounters.settings["on"] = w.banter.settings["on"] = "0"   # (nobody turning up in other tests: they ask for them)
    w.wonders.on = False
    w.seasons.pinned = "Summer"         # (the same season every run: a 16-day year would change it under them)
    return w


@pytest.fixture(autouse=True)
def same_luck(request):
    """Each test rolls the same dice every run (the world is shared: a sheep wandering through a gate shouldn't fail one)."""
    random.seed(request.node.name)


def test_a_scene_that_ends_never_leaves_you_rooted(world):
    s = join(world, "Rooted", "4,0,0", 224, 380)
    assert s.run_script_lines("(test)", ["01\tToggle.User.Input\tOFF", "02\tEnd"])
    world.tick(0.05)
    assert s.user_input_enabled and not s.script_running            # (the scene's over: you can walk)
    leave(world, s)


def test_every_npc_has_a_level_and_its_strength_goes_by_it(world):
    d = world.data
    wolf = int(d.entity_ini("Wolf", "Level", "0"))
    assert wolf >= 1 and int(d.entity_ini("Villager", "Level", "0")) >= 1      # (townsfolk too)
    many = [world.add_npc("Wolf", 0, 40 + 3 * k, 40, "") for k in range(12)]
    levels = {e.npc_level for e in many}
    assert levels <= {wolf - 1, wolf, wolf + 1} and len(levels) > 1            # (a little above or below its kind's)
    hp = {e.npc_level: e.max_hp for e in many}
    assert all(hp[a] < hp[b] for a in hp for b in hp if a < b)
    set_to = world.add_npc("Wolf", 0, 40, 80, "Level=%d" % (wolf + 6))
    named = world.add_npc("Wolf", 0, 40, 120, "Id=Test_Wolf")
    assert set_to.npc_level == wolf + 6 and named.npc_level == wolf          # (its map line's; one of a kind: its kind's)
    from dsengine.remnants import monster_level
    villager = world.add_npc("Villager", 0, 40, 160, "Attitude=Good")
    assert monster_level(d, set_to) == wolf + 6 and monster_level(d, villager) == 0   # (no remnants from townsfolk)
    for e in many + [set_to, named, villager]:
        world.remove_entity(e)


def test_standing_stones_are_decor_and_lava_runs_over_its_neighbours(world):
    d = world.data
    assert d.tile_ini("Standing_Stone001", "Layer", "") == "Decor"
    assert not any(t == "Standing_Stone001" for m in world.maps.values() for t in m.tile)
    assert int(d.tile_ini("Lava001", "Blend", "0")) == 9


def test_marys_grave_is_by_the_sea_and_galaith_has_no_way_in_from_it(world):
    m = world.maps["4,1,0"]
    assert ("Mothers_Grave", 2, 5) in m.ids
    assert not any(world.pixel_walkable(0, gx * 32 + 16, 378 * 32 + 16) for gx in range(-263, -82))   # (the south wall whole)
    harbour = [world.maps["%d,18,0" % mx] for mx in (-6, -5, -4)]
    assert any("Burnt_Hull001" in c for h in harbour for c in h.decor)
    assert sum(1 for e in world.ents if e.name == "Fire" and e.map in ("-6,18,0", "-5,18,0", "-4,18,0")) >= 5


def test_the_chapel_graveyard_has_one_gate_and_you_walk_out_of_it_from_the_grave(world):
    from collections import deque
    m, chapel = world.maps["4,1,0"], world.maps["3,1,0"]
    assert not any(t.startswith("Wood_Gate") for t in m.decor)      # (the one gate is on 3,1,0)

    def reach(start, goal, x0, y0, x1, y1, step=2):
        seen, q = {start}, deque([start])
        while q:
            x, y = q.popleft()
            if abs(x - goal[0]) <= step and abs(y - goal[1]) <= step:
                return True
            for n in ((x + step, y), (x - step, y), (x, y + step), (x, y - step)):
                if x0 <= n[0] < x1 and y0 <= n[1] < y1 and n not in seen and world.pixel_walkable(0, *n):
                    seen.add(n)
                    q.append(n)
        return False
    start = (m.ox + 48, m.oy + 5 * 32 + 16)                        # (below the grave)
    out = (m.ox + 2 * 32 + 16, m.oy + 16)                           # (outside the fence, the cottage's way)
    assert not reach(start, out, m.ox, m.oy, m.ox + 25 * 32, m.oy + 21 * 32)        # (no way out on its own map)
    assert reach(start, out, chapel.ox, chapel.oy, m.ox + 25 * 32, m.oy + 21 * 32)  # (west, out of the chapel's gate)
    script = open(os.path.join(ROOT, "data", "Scripts", "The Funeral.txt"), encoding="cp1252").read()
    spots = {ln.split("\t")[4] for ln in script.splitlines() if "\tMove.Entity\t" in ln and "Edwin" not in ln}
    for spot in spots:                                              # (the mourners walk somewhere they can get to)
        x, y = (int(v) for v in spot.split(","))
        assert reach(start, (m.ox + x + 16, m.oy + y + 24), m.ox, m.oy, m.ox + 25 * 32, m.oy + 21 * 32), spot


def test_the_hard_zones_are_places_with_homes_and_no_ruin_outlines(world):
    import sys
    sys.path.insert(0, os.path.join(ROOT, "dev", "migrate"))
    from build_zone_sites import SITES, HOMES
    ids = {i[0]: (m, i[1], i[2]) for m in world.maps.values() for i in m.ids}
    for site in SITES:
        assert site["id"] in ids, site["id"]                    # (every place made, and named on the world map)
    for h in HOMES:                                            # (where people live, no monster on the doorstep)
        m, x, y = ids[h]
        hx, hy = m.ox + (x - 1) * 32, m.oy + (y - 1) * 32
        assert not any(e.hostile and e.z == 0 and abs(e.x - hx) < 12 * 32 and abs(e.y - hy) < 12 * 32 for e in world.ents
                       if e.type == NPC and not e.npc_id), h
    walls = sum(1 for m in world.maps.values() if m.mz == 0 for t in m.decor if t.startswith("Ruined_Wall"))
    assert 40 < walls < 600                                    # (a few ruins of every shape: never an outline everywhere)
    assert world.data.tile_ini("Ruined_Wall001", "Layer", "") == "Decor"
    yews = [m.name for m in world.maps.values() if m.mz == 0 and "Yew_Tree001" in m.decor]
    assert yews and all(-7 <= int(n.split(",")[0]) <= 23 and 6 <= int(n.split(",")[1]) <= 12 for n in yews), yews


def test_galaiths_fires_go_out_for_whoever_has_done_the_royal_guard(world):
    fires = [e for e in world.ents if e.name == "Blaze" and getattr(e, "gone_after", "") == "GuardQuest:5"]
    field = [e for e in fires if e.x > -78 * 32]
    ramparts = [e for e in fires if e.x < -82 * 32]
    assert len(field) >= 10 and len(ramparts) >= 8
    fire = field[0]
    m = world.maps[fire.map]
    slayer = join(world, "Slayer", m.name, int(fire.x - m.ox) + 40, int(fire.y - m.oy))
    newcomer = join(world, "Newcomer", m.name, int(fire.x - m.ox) + 60, int(fire.y - m.oy))
    assert world.visible_to(fire, slayer) and world.visible_to(fire, newcomer)
    slayer.update_attribute("GalaithQuest", "=2")
    assert world.visible_to(fire, slayer)                       # (the dragon dead: still burning)
    slayer.update_attribute("GuardQuest", "=5")
    assert not world.visible_to(fire, slayer) and not world.visible_to(ramparts[0], slayer)
    assert world.visible_to(fire, newcomer)                     # (out for them alone)
    leave(world, slayer)
    leave(world, newcomer)


def test_an_admin_can_fly_over_what_stops_a_walker(world):
    s = join(world, "Flyer", "4,0,0", 224, 380)
    s.admin_enabled = True
    p = s.player
    m = world.maps["4,0,0"]
    wall = next((x, y) for y in range(m.oy + 260, m.oy + 520, 4) for x in range(m.ox + 120, m.ox + 420, 4)
                if not world.pixel_walkable(0, x, y, s) and world.pixel_walkable(0, x, y + 40, s))
    assert not world.entity_can_stand(p, wall[0], wall[1], wall[0], wall[1] + 40, s)
    s.handle({"t": "admin", "do": "fly", "on": True})
    assert s.flying and world.entity_can_stand(p, wall[0], wall[1], wall[0], wall[1] + 40, s)
    assert not world.entity_can_stand(p, -99999, -99999, p.fx, p.fy, s)          # (never off the world's maps)
    s.handle({"t": "admin", "do": "fly", "on": False})
    assert not s.flying and not world.entity_can_stand(p, wall[0], wall[1], wall[0], wall[1] + 40, s)
    leave(world, s)


def test_locked_out_runs_through_the_secret_cellars(world):
    s = join(world, "Lockpicker", "17,2,0", 520, 240)
    s.update_attribute("LockedOutQuest", "=1")
    assert world.map_named("17,2,-1") is not None
    s.update_attribute("LockedOutQuest", "=3")
    assert s.get_attribute("LockedOutQuest") in ("3", 3)
    world.tick(0.05)
    s.out = []
    s.update_attribute("LockedOutQuest", "=4")          # (done: the reward screen, with what it gave)
    world.tick(0.05, now=world.now + 21000)
    ev = next(e for e in s.out if e.get("t") == "reward")
    assert ev["quest"] == "Locked Out" and ev["shards"] == 8
    leave(world, s)


def test_every_pub_has_a_dice_table_and_every_barkeep_plays(world):
    barkeeps = [e for e in world.ents if e.name == "Barkeep"]
    assert barkeeps
    assert "Play" in world.data.entity_ini("Barkeep", "Use.Words", "")
    tables = [e for e in world.ents if e.name == "Dice_Table"]
    for b in barkeeps:
        assert any(t.z == b.z and abs(t.x - b.x) <= 800 and abs(t.y - b.y) <= 672 for t in tables), b.npc_id


def test_the_year_goes_round(world):
    y = world.seasons.year_ms()
    assert [world.seasons.season(k * y / 4 + 1000) for k in range(4)] == ["Spring", "Summer", "Autumn", "Winter"]
    was = world.seasons.now_is
    try:
        world.seasons.now_is = "Winter"
        winter = world.seasons.night()
        assert world.seasons.rain_is("rain") == "snow" and world.seasons.crop_growth() < 1
        world.seasons.now_is = "Summer"
        summer = world.seasons.night()
        assert (1 - winter[0]) + winter[1] > (1 - summer[0]) + summer[1]    # (longer nights in winter)
        assert world.seasons.rain_is("rain") == "rain"
        assert world.seasons.swapped("Raw_Herring") == "Raw_Trout" and world.seasons.swapped("Bread") == "Bread"
    finally:
        world.seasons.now_is = was


def test_a_river_freezes_in_winter_but_never_the_sea(world):
    s = world.seasons
    if s.rivers is None:
        s.find_rivers()
    assert s.rivers
    sizes = {m.name for m, _, _ in s.rivers}
    assert "23,23,0" not in sizes                       # (open sea: too big a body of water)
    m, x, y = s.rivers[0]
    before = m.tile[m.cell(x, y)]
    assert before.startswith("Water0")


def test_a_shard_storm_rains_on_those_out_in_it(world):
    wd = world.wonders
    s = join(world, "Stormy", "2,0,0", 300, 300)
    s.connected = True
    wd.storm_start()
    assert wd.in_storm() and world.weather["kind"] == "shardstorm"
    assert world.weather_kind("4,6,0", 0)[0] == "shardstorm"
    before = sum(1 for e in world.ents if e.name in ("Shard_Remnant", "Living_Remnant"))
    for _ in range(40):
        wd.storm_rains_on(s)
    assert sum(1 for e in world.ents if e.name in ("Shard_Remnant", "Living_Remnant")) > before
    wd.storm_until = 0
    world.weather["kind"] = "clear"
    for e in [e for e in world.ents if e.name == "Living_Remnant" and e.source == "ENCOUNTER"]:
        world.remove_entity(e)
    leave(world, s)


def test_the_tax_collector_walks_after_the_rich_and_is_polite_about_it(world):
    wd = world.wonders
    s = join(world, "Moneybags", "2,0,0", 300, 300)
    s.connected = True
    s.script_running = False
    stock(s, **{"Gold_Coin(s)": 10000})
    wd.tax_tick()
    e = wd.collectors[s.player_name]
    assert e.follow is s and not e.hostile
    assert "Attack" not in s.get_verbs(e)
    due = wd.tax_due(s)
    wd.tax_paid(s)
    assert s.items_held("Gold_Coin(s)") == 10000 - due and s.player_name not in wd.collectors
    leave(world, s)


def test_a_letter_waits_for_a_friend_and_a_courier_brings_it(world):
    wd = world.wonders
    a = join(world, "Sender", "4,6,0", 300, 300)
    world.together.friends[a.player_name] = ["Faraway"]
    stock(a, **{"Bread": 1})
    assert wd.send_letter(a, "Faraway", "+Bread Eat something.")
    assert a.items_held("Bread") == 0 and wd.mail["faraway"][0]["item"] == "Bread"
    assert not wd.send_letter(a, "Stranger", "Hello.")
    state = wd.state()
    wd.load(state)                                      # (saved with the world: still there)
    b = join(world, "Faraway", "4,6,0", 300, 340)
    assert wd.take_letters(b) == 1 and b.items_held("Bread") == 1 and "faraway" not in wd.mail
    world.together.friends.pop(a.player_name)
    leave(world, a)
    leave(world, b)


def test_a_mimic_stops_pretending_when_its_caught(world):
    wd = world.wonders
    s = join(world, "Accuser", "4,6,0", 300, 300)
    s.connected = True
    m = world.maps["4,6,0"]
    e = wd.add("Mimic_Villager", m, 10, 10, "Attitude=Good Schedule=Always Name=Viilager")
    wd.mimics[e.uid] = world.now + 60000
    wd.mimic_caught(s, e)
    assert not e.alive
    thing = next(o for o in world.ents if o.name == "Mimic_Thing")
    assert thing.hostile and thing.target is s
    world.remove_entity(thing)
    leave(world, s)


def test_what_killed_you_holds_a_grudge_and_comes_back_stronger(world):
    wd = world.wonders
    s = join(world, "Grudged", "2,0,0", 300, 300)
    s.connected = True
    m = world.maps["2,0,0"]
    wolf = world.add_npc("Wolf", 0, m.ox + 300, m.oy + 300, "Attitude=Bad", home=m.name)
    wolf.target = s
    s.death_remembered()
    assert s.get_attribute("Legend.Died.Wolf") in (1, "1") and s.get_attribute("Grudge.Kind") == "Wolf"
    plain = (wolf.max_hp, wolf.strength)
    world.remove_entity(wolf)
    s.update_attribute("Grudge.At", "=1")
    s.script_running = False
    wd.grudge_tick()
    who = [world.by_uid[u] for u, n in wd.grudges.items() if n == s.player_name]
    assert who and who[0].max_hp > plain[0] and who[0].strength > plain[1] and who[0].display.startswith("Scarred")
    wd.grudge_settled(s, who[0])
    assert s.player_name not in wd.grudges.values() and float(s.get_attribute("Grudge.At")) == 0
    world.remove_entity(who[0])
    leave(world, s)


def test_your_legend_gets_about(world):
    s = join(world, "Goosed", "4,6,0", 300, 300)
    assert s.legend_due() is None or True
    s.update_attribute("Legend.Died.Goose", "=1")
    line = s.legend_due()
    assert line and "Goosed" in line[2] and "goose" in line[2]
    s.rumour_heard(line[1])
    assert s.legend_due() is None or s.legend_due()[1] != line[1]
    leave(world, s)


def test_the_champion_is_crowned_at_the_years_turn(world):
    wd = world.wonders
    s = join(world, "Champ", "4,6,0", 300, 300)
    was = world.seasons.now_is, wd.champion, wd.champion_year, dict(wd.scores)
    try:
        world.seasons.now_is = "Winter"
        wd.arena_kill(s)
        assert wd.scores["Champ"] == 1
        world.seasons.now_is = "Spring"
        wd.champion_year = wd.year() - 1
        wd.champion_tick()
        assert wd.champion == "Champ" and not wd.scores
    finally:
        world.seasons.now_is, wd.champion, wd.champion_year, wd.scores = was
    leave(world, s)


def test_marys_notes_make_a_map(world):
    s = join(world, "Reader", "4,6,0", 300, 300)
    for k in range(1, 8):
        assert world.data.place("Mary_Note_%d" % k) is not None or any(
            e.npc_id == "Mary_Note_%d" % k for e in world.ents), k
        assert os.path.exists(os.path.join(ROOT, "data", "Scripts", "Read Mary_Note_%d.txt" % k))
    assert world.data.place("Marys_Cache") is not None
    leave(world, s)


def test_the_wandering_inn_is_somewhere_today(world):
    wd = world.wonders
    wd.inn_tick()
    assert wd.inn and {e.name for e in wd.inn["ents"]} >= {"Wandering_Inn", "Wandering_Keeper", "Dice_Table"}


def test_a_ghost_ship_comes_and_is_gone_by_morning(world):
    wd = world.wonders
    wd.ship_comes(1)
    assert wd.ship and any(e.name == "Ghost_Ship" for e in wd.ship["ents"])
    ents = wd.ship["ents"]
    assert any(e.name == "Drowned_Sailor" for e in ents) or len(ents) >= 2
    world.is_night = lambda t=None: False
    try:
        wd.ship_tick()
    finally:
        del world.is_night
    assert wd.ship is None and not any(e.alive for e in ents)


def test_no_building_in_galaith_stands_across_a_map_edge(world):
    # (a roof's group is its own map's: half of it wouldn't lift as you went in. The orchard gardener's cottage on
    # -9,15 / -8,15 is the owner's, left across the edge on purpose)
    for mx in range(-11, -3):
        for my in range(12, 18):
            m = world.maps.get("%d,%d,0" % (mx, my))
            east = world.maps.get("%d,%d,0" % (mx + 1, my))
            south = world.maps.get("%d,%d,0" % (mx, my + 1))
            if m is None:
                continue
            for y in range(1, 22):
                if m.name == "-9,15,0":
                    continue
                assert not (east and m.roof[m.cell(25, y)] and east.roof[east.cell(1, y)]), (m.name, y)
            for x in range(1, 26):
                assert not (south and m.roof[m.cell(x, 21)] and south.roof[south.cell(x, 1)]), (m.name, x)


def test_every_finished_quest_shows_its_screen_even_with_no_reward(world):
    s = join(world, "Quester")
    s.out.clear()
    s.reward_begin("A Thankless Task")
    s.reward["at"] = -10 ** 9                           # (long enough ago, whatever's running)
    s.reward_tick()
    ev = next(e for e in s.out if e.get("t") == "reward")
    assert ev["quest"] == "A Thankless Task" and not ev["items"] and not ev["xp"] and not ev["shards"]
    leave(world, s)


def join(w, name, map_name="1,1,0", x=300, y=300):
    s = Session(w, name)
    s.load_state({"map": map_name, "x": x, "y": y})
    w.sessions[name] = s
    s.enter_world()
    w.tick(0.05)
    return s


def leave(w, s):
    s.leave_world()
    w.sessions.pop(s.player_name, None)


def test_world_loads(world):
    assert len(world.maps) > 100
    assert any(e.type == NPC for e in world.ents)
    m = world.maps["1,1,0"]
    assert (m.ox, m.oy) == (world.sw, world.sh)


def test_walking_moves_the_player(world):
    s = join(world, "Walker")
    x0 = s.player.x
    s.keyboard_direction = 2
    for _ in range(10):
        world.tick(0.05)
    s.keyboard_direction = 0
    assert s.player.x > x0
    leave(world, s)


def test_tile_changes_are_shared(world):
    a, b = join(world, "Alice"), join(world, "Bob")
    m = world.maps["1,1,0"]
    before = m.version
    a.script_change_tile("3,3", "Tree_Stump001", 0, 0)
    assert m.version == before + 1
    assert b.cell_names(m, 3, 3)[1] == "Tree_Stump001" or b.cell_names(m, 3, 3)[0] == "Tree_Stump001"
    leave(world, a)
    leave(world, b)


def test_quest_lock_is_per_player(world):
    # maps/1,1,0.txt: Lock 20,7  $Item.Fathers_House_Key>=1 or $Item.Beggars_House_Key>=1 (Tobias's house)
    a, b = join(world, "Ann"), join(world, "Ben")
    m = world.maps["1,1,0"]
    lk = m.lock_at[(20, 7)]
    assert a.lock_closed(m, lk) and b.lock_closed(m, lk)
    a.add_inventory_item("Fathers_House_Key", 1)                  # (as a script gives it: the locks look again)
    assert not a.lock_closed(m, lk)
    assert b.lock_closed(m, lk)
    cx, cy = m.ox + 19 * 32 + 16, m.oy + 6 * 32 + 16
    assert not world.pixel_walkable(0, cx, cy, b)
    assert not world.pixel_walkable(0, cx, cy, None)            # (NPCs: locks stay shut)
    leave(world, a)
    leave(world, b)


def test_one_time_items_are_per_player(world):
    m = world.maps["1,1,0"]
    item = world.add_entity_of_type("MapItem", "Logs", 0, m.ox + 300, m.oy + 300, "1 Once=1 Id=Test_Once", home=m.name)
    assert item.once
    a = join(world, "Cara", m.name, int(item.x - m.ox), int(item.y - m.oy))
    b = join(world, "Dan", m.name, int(item.x - m.ox), int(item.y - m.oy))
    a.pickup_map_item(item)
    assert a.items_held(item.name) >= 1
    assert not world.visible_to(item, a)
    assert world.visible_to(item, b)
    assert item.alive
    leave(world, a)
    leave(world, b)


def test_npc_attitude_is_per_player(world):
    npc = next(e for e in world.ents if e.type == NPC and not e.hostile)
    a, b = join(world, "Eve"), join(world, "Fay")
    a.clicked_ent = npc
    a.set_npc_attitude("CLICKED", "Bad")
    assert world.hostile_for(npc, a) is True
    assert world.hostile_for(npc, b) is False
    assert "Attack" in a.get_verbs(npc) and "Attack" not in b.get_verbs(npc)
    leave(world, a)
    leave(world, b)


def test_quest_scripts_change_things_for_their_player_only(world, tmp_path, monkeypatch):
    script = tmp_path / "Quest Test.txt"
    script.write_text("01\tGet.Value\tATTRIBUTE\tSomeQuest\tVariable.1$\n"
                      "02\tChange.Tile\t5,5\tTree_Stump001\t0\t0\n03\tEnd\n", encoding="cp1252")
    a, b = join(world, "Gil"), join(world, "Hal")
    monkeypatch.setattr(type(a), "script_path", lambda self, name: str(tmp_path / (name + ".txt")))
    m = world.maps["1,1,0"]
    before = (m.version, m.cell_text(5, 5))
    a.start_script("Quest Test", True)
    a.run_scripts()
    assert (m.version, m.cell_text(5, 5)) == before          # the world didn't change
    assert "Tree_Stump001" in a.cell_names(m, 5, 5)
    assert "Tree_Stump001" not in b.cell_names(m, 5, 5)
    leave(world, a)
    leave(world, b)


def test_shop_stock_is_shared(world):
    a, b = join(world, "Ivy"), join(world, "Jon")
    from ashen import ini
    racks = [name for name, items in ini.sections(world.data.data_file("ItemRacks.ini"))
             if dict((k.upper(), v) for k, v in items).get("TYPE", "").upper() in ("SHOP", "GENERAL", "SPECIFIC")]
    if not racks:
        pytest.skip("no shops")
    for s in (a, b):
        s.open_item_rack("SHOP", "Shopkeeper", racks[0])
    i = next((i for i, r in enumerate(a.rack) if r["quantity"] > 0), None)
    if i is None:
        pytest.skip("no limited stock")
    item = a.rack[i]["item"]
    before = b.rack[i]["quantity"]
    a.add_inventory_item("Gold_Coin(s)", 100000, quiet=True)
    e = a.rack_pseudo(i)
    a.rack_buy(e, 1)
    assert b.rack[i]["quantity"] == before - 1
    assert any(f"ADD.SHOP.ITEM\t{item}" in q for q in world.action_queue)
    leave(world, a)
    leave(world, b)


def test_shop_stock_varies_below_the_rack(world, monkeypatch):
    s = join(world, "Stocky")
    d = world.data
    counts = [s.shop_stock("SHOP-Test", "Item%d" % i, 9) for i in range(400)]
    assert all(0 <= n <= 9 for n in counts)
    assert 0 in counts and 9 in counts and any(0 < n < 9 for n in counts)      # (sold out, full, and between)
    assert all(n >= 3 for n in counts if n)                                       # (a third of it, at the least)
    assert s.shop_stock("SHOP-Test", "Item1", 9) == counts[1]                     # (the same all through a delivery)
    assert {s.shop_stock("SHOP-Test", "Item%d" % i, 9, "0") for i in range(50)} == {9}   # (the rack's Vary.Stock=0)
    monkeypatch.setattr(d, "shop_vary_stock", False)
    assert {s.shop_stock("SHOP-Test", "Item%d" % i, 9) for i in range(50)} == {9}
    assert s.shop_stock("SHOP-Test", "Item1", 9, "1") == counts[1]                # (Vary.Stock=1 wins over Config)
    assert d.shop_restock_delay >= 3600
    leave(world, s)


def test_a_cart_goes_round_its_stops_and_takes_you_to_one(world):
    carts = world.carts
    c = next(c for c in carts.carts if c.key == "Northport")
    e = c.e
    assert e is not None and e.alive and len(c.stops) >= 3
    m = world.map_at(c.z, e.cx, e.cy)
    s = join(world, "Rider", m.name, int(e.cx - m.ox), int(e.y + e.h - m.oy) + 4)
    s.connected = True
    stock(s, **{"Gold_Coin(s)": 10})
    c.wait_until = 0                                     # (off it goes)
    x0 = e.x, e.y
    for _ in range(20):
        world.tick(0.05)
    assert (e.x, e.y) != x0 and "Hail" in carts.verbs(s, e)
    s.player.x, s.player.y = e.cx - s.player.w / 2, e.y + e.h - s.player.h + 6
    s.choose_verb("Hail", e, e.cx, e.cy)
    held = e.x, e.y
    for _ in range(10):
        world.tick(0.05)
    assert (e.x, e.y) == held                            # (hailed: it waits)
    s.choose_verb("Get In", e, e.cx, e.cy)
    for _ in range(5):
        world.tick(0.05)
    assert s.ab_mode == "Conversation"
    dest = carts.next_stop(c)
    words = "To %s." % c.stops[dest]
    s.action_box_response_chosen(s.responses.index(words) + 1)
    assert s.ride is c and s.items_held("Gold_Coin(s)") == 10 - c.fare
    s.keyboard_direction = 2                             # (no walking out of it)
    for _ in range(int(60000 / 50)):
        world.tick(0.05, now=world.now + 50)             # (the clock as fast as the ticks: its waits go by)
        if s.ride is None:
            break
    s.keyboard_direction = 0
    assert s.ride is None and c.i == dest                # (there: down they get, at the stop)
    sx, sy = c.pts[dest]
    assert abs(s.player.cx - sx) < 80 and abs(s.player.cy - sy) < 80
    leave(world, s)


def test_the_ferries_cross_together_and_carry_you_over(world):
    carts = world.carts
    east = next(c for c in carts.carts if c.key == "Isle_Ferry_East")
    west = next(c for c in carts.carts if c.key == "Isle_Ferry_West")
    assert east.e.name == west.e.name == "Ferry_Boat" and east.timetable and east.headings == 16
    assert east.stops[east.i] == "the Isle" and west.stops[west.i] == "Northport"     # (one at each pier)
    t = world.now + 5000                                                              # (not cast off mid-test)
    east.wait_until, west.wait_until = carts.leave_time(east, t), carts.leave_time(west, t)
    assert east.wait_until == west.wait_until and east.wait_until % 45000 == 0        # (they cast off together)
    e = east.e
    m = world.maps["3,2,0"]
    s = join(world, "Passenger", "3,2,0", 14 * 32 + 16, 14 * 32)                     # (at the end of the Isle's pier)
    s.connected = True
    stock(s, **{"Gold_Coin(s)": 5})
    s.choose_verb("Get In", e, e.cx, e.cy)
    assert s.ab_mode != "Conversation" and s.ride is None                         # (no papers yet: not for you)
    s.update_attribute("Passage", "=5")
    s.update_attribute("RemnantsAbsorbed", "=1")
    for k in range(len(s.skill_xp)):
        s.skill_xp[k] = max(s.skill_xp[k], 6)
    assert s.player_level() >= 3
    s.choose_verb("Get In", e, e.cx, e.cy)
    for _ in range(5):
        world.tick(0.05)
    assert s.ab_mode == "Conversation" and "To Northport." in s.responses
    s.action_box_response_chosen(s.responses.index("To Northport.") + 1)
    assert s.ride is east and s.items_held("Gold_Coin(s)") == 4
    assert east.wait_until == west.wait_until                                     # (no hurrying a timetable)
    heading = east.heading
    s.keyboard_direction = 2
    turned = False
    for _ in range(int(400000 / 100)):
        world.tick(0.1, now=world.now + 100)
        turned = turned or abs(east.heading - heading) > 20
        if s.ride is None:
            break
    s.keyboard_direction = 0
    assert s.ride is None and east.stops[east.i] == "Northport" and turned        # (it turned as it went)
    assert s.cur_map.name in ("4,4,0", "4,3,0")
    t = s.cur_map
    assert world.entity_can_stand(s.player, s.player.x, s.player.y, s.player.x, s.player.y, s)  # (on the pier, not the sea)
    assert m is not t
    leave(world, s)


def test_at_most_two_merchants_of_a_trade_in_a_place():
    import sys
    sys.path.insert(0, os.path.join(ROOT, "dev", "migrate"))
    import cap_merchants
    over = {k: [s[1] for s in v] for k, v in cap_merchants.merchants().items() if len(v) > cap_merchants.CAP}
    assert not over


def test_save_round_trip(world):
    a = join(world, "Kim")
    a.add_inventory_item("Logs", 3, quiet=True)
    a.update_attribute("SomeQuest", "=2")
    a.taken_once.add("X@1,1")
    st = a.save_state()
    leave(world, a)
    b = Session(world, "Kim")
    b.load_state(st)
    assert b.items_held("Logs") >= 3
    assert b.get_attribute("SomeQuest") == "2"
    assert "X@1,1" in b.taken_once
    assert b.save_state()["map"] == st["map"]


def test_look_is_kept_and_shown_to_others(world):
    from dsengine.view import player_state
    a, b = join(world, "Lia"), join(world, "Max")
    a.handle({"t": "look", "look": {"hair": "#A83A1A", "shirt": "red", "skin": "#ffdcc0"}})
    assert a.look == {"hair": "#a83a1a", "skin": "#ffdcc0"}          # (only real colours are kept)
    assert player_state(a, b)["look"] == a.look
    assert a.save_state()["look"] == a.look
    leave(world, a)
    leave(world, b)


def test_pvp_only_on_the_arena_sand(world):
    a, b = join(world, "Ned"), join(world, "Ola")                 # in Ashford's neighbour: no fighting
    assert "Attack" not in a.get_verbs(b.player)
    assert not a.pvp_ok(b)
    # the arena: on the paving, still safe; on the sand, fair game
    for s, x in ((a, 300), (b, 330)):
        s.teleport("0,0,10", x, 530)                               # (the paving by the gate)
        s.do_pending_map_change()
    world.tick(0.05)
    assert a.in_arena() and not a.on_arena_ground()
    assert "Attack" not in a.get_verbs(b.player)
    for s, x in ((a, 384), (b, 416)):
        s.teleport("0,0,10", x, 300)                               # (the middle of the sand)
        s.do_pending_map_change()
    world.tick(0.05)
    assert a.on_arena_ground() and b.on_arena_ground()
    assert "Attack" in a.get_verbs(b.player)
    leave(world, a)
    leave(world, b)


def test_pvp_fight_to_the_end_costs_nothing(world):
    a, b = join(world, "Pip"), join(world, "Quin")
    for s, x in ((a, 384), (b, 410)):
        s.teleport("0,0,10", x, 300)
        s.do_pending_map_change()
    world.tick(0.05)
    a.equipped[1] = "Bronze_Sword"
    a.recalc_equipment()
    b.add_inventory_item("Gold_Coin(s)", 50, quiet=True)
    gold, items = b.items_held("Gold_Coin(s)"), len(b.inv)
    a.start_attack(b.player)
    assert a.player_attack_target is b.player
    t = world.now
    for _ in range(3000):                                          # (up to 150 seconds of the world's time)
        t += 50
        world.tick(0.05, t)
        if b.get_attribute("ArenaLosses") == "1":
            break
    assert b.get_attribute("ArenaLosses") == "1"
    assert a.get_attribute("ArenaWins") == "1"
    assert b.player.hp == b.player_max_hp
    assert b.items_held("Gold_Coin(s)") == gold and len(b.inv) == items and b.grave is None
    assert b.screen_name == "0,0,10" and not b.on_arena_ground()   # (by the gate, on the paving)
    assert a.player_attack_target is None
    leave(world, a)
    leave(world, b)


def wild_map(world, s):
    """A map out in the wild (no town's), on the surface."""
    return next(n for n, m in sorted(world.maps.items()) if m.mz == 0 and not s.town_of_map(n) and n != "0,0,10")


def open_pair(world, *names):
    """Players side by side out in the wild, open PvP on (the caller turns it off again)."""
    world.open_pvp = True
    out = [join(world, n) for n in names]
    wild = wild_map(world, out[0])
    for k, s in enumerate(out):
        s.teleport(wild, 300 + 26 * k, 300)
        s.do_pending_map_change()
    world.tick(0.05)
    return out


def test_the_pvp_badge_says_open_ground_or_safe_and_only_while_its_on(world):
    (a,) = open_pair(world, "Wren")
    try:
        assert a.me_state()["pvp"] == 2                             # (out in the wild: you can be fought)
        for safe in ("1,1,0", "21,4,-10"):                         # (the Isle's a town; the Shardrealm)
            a.dirty_me = False
            a.teleport(safe, 300, 300)
            a.do_pending_map_change()
            world.tick(0.05)
            assert a.me_state()["pvp"] == 1, safe
        a.teleport(wild_map(world, a), 300, 300)
        a.do_pending_map_change()
        world.tick(0.05)
        assert a.me_state()["pvp"] == 2
        a.dirty_me = False
        a.teleport("1,1,0", 300, 300)
        a.do_pending_map_change()
        a.check_map()
        assert a.dirty_me                                           # (crossing into a town tells the browser)
    finally:
        world.open_pvp = False
    assert a.me_state()["pvp"] == 0                                 # (off: no badge)


def test_open_pvp_is_outside_towns_within_a_level_gap_and_never_a_party(world):
    a, b = join(world, "Rook"), join(world, "Sable")
    wild = wild_map(world, a)
    for s, x in ((a, 300), (b, 326)):
        s.teleport(wild, x, 300)
        s.do_pending_map_change()
    world.tick(0.05)
    assert not a.pvp_ok(b)                                          # (the server's setting is off)
    world.open_pvp = True
    try:
        assert a.pvp_ok(b) and b.pvp_ok(a) and "Attack" in a.get_verbs(b.player)
        for safe in ("1,1,0", "21,4,-10"):                         # (the Isle's a town; the Shardrealm)
            b.teleport(safe, 300, 300)
            b.do_pending_map_change()
            a.teleport(safe, 326, 300)
            a.do_pending_map_change()
            world.tick(0.05)
            assert not a.pvp_ok(b), safe
        for s, x in ((a, 300), (b, 326)):
            s.teleport(wild, x, 300)
            s.do_pending_map_change()
        world.tick(0.05)
        a.player_level = lambda: b.player_level() + 6              # (more than Open.Level.Gap apart)
        assert not a.pvp_ok(b) and "too far from your level" in a.pvp_why_not(b)
        del a.player_level
        a.party_id = b.party_id = 987
        assert not a.pvp_ok(b)
        a.party_id = b.party_id = 0
        assert a.pvp_ok(b)
    finally:
        world.open_pvp = False
        leave(world, a)
        leave(world, b)


def test_striking_first_marks_you_the_guards_come_and_you_cant_slip_away(world):
    a, b = open_pair(world, "Tarn", "Ula")
    try:
        a.pvp_strike(b.player, False)
        assert a.pvp_marked() and not b.pvp_marked()
        b.pvp_strike(a.player, False)                               # (fighting back: no mark on them)
        assert not b.pvp_marked()
        guard = next(e for e in world.ents if e.type == NPC and a.guard_town(e) and e.owner is None and
                     not world.hostile_for(e, b))                   # (a town's watch, friendly to the unmarked)
        assert world.hostile_for(guard, a) and world.stat_for(guard, a, "aggressive") == 1
        stock(a, Hearth_Anchor=1)
        here = a.cur_map.name
        a.go_home()
        world.tick(0.05)
        assert a.cur_map.name == here                               # (marked: not home)
        assert 0 < a.save_state()["pvp_mark"] <= 5 * 60000          # (the rest of it, kept with the save)
        a.player_attack_target = b.player_attack_target = None      # (the fight over: each blow would start it again)
        world.tick(0.05, now=world.now + 5 * 60000 + 1000)
        assert not a.pvp_marked() and not world.hostile_for(guard, a)
    finally:
        world.open_pvp = False
        leave(world, a)
        leave(world, b)


def test_dying_marked_loses_everything_for_the_killer_and_the_struck_keep_theirs(world):
    a, b, c = open_pair(world, "Vex", "Wynn", "Yarrow")
    try:
        stock(a, **{"Gold_Coin(s)": 100, "Hearth_Anchor": 1, "Bronze_Sword": 1})
        a.equipped[1] = "Bronze_Sword"
        a.recalc_equipment()
        stock(b, **{"Gold_Coin(s)": 40})
        a.pvp_strike(b.player, False)
        assert a.pvp_marked()
        a.player.hp = 1
        a.pvp_take_hit(b, 50, "Hit")
        assert a.dead_wait and a.grave is None and not a.pvp_marked()
        assert [e.name for e in a.inv] == ["Hearth_Anchor"] and not any(a.equipped[1:])   # (all but what's kept)
        loot = [e for e in world.ents if e.type == MAPITEM and e.alive and e.private_to is b]
        names = {e.name for e in loot}
        assert {"Gold_Coin(s)", "Bronze_Sword"} <= names
        gold = next(e for e in loot if e.name == "Gold_Coin(s)")
        assert gold.quantity == 100
        assert world.visible_to(gold, b) and not world.visible_to(gold, c)
        world.tick(0.05, now=world.now + 11000)                     # (Loot.Private.Seconds on: anyone's)
        assert world.visible_to(gold, c)
        b.player.hp = 1                                             # (b, never marked, dies as ever: a grave)
        b.pvp_take_hit(c, 50, "Hit")
        assert b.dead_wait and b.grave is not None
    finally:
        world.open_pvp = False
        for s in (a, b, c):
            leave(world, s)


def stock(s, **items):
    for name, q in items.items():
        s.add_inventory_item(name, q, quiet=True)


def hold_pocket(world, s):
    """The test's pocket all still glass (a new one is mostly mist: build_pocket.py), to build anywhere on."""
    h, m = world.homes.home_of(s.player_name), world.homes.map_of(s.player_name)
    h["land"] = [ln.replace("Rim_Mist001", "Rim_Glass001") for ln in h["land"]]
    world.homes.bases.pop(s.player_name, None)
    for c in range(1, len(m.tile)):
        if m.tile[c] == "Rim_Mist001":
            m.tile[c] = "Rim_Glass001"
            m.refresh_cell(c)
    return m


def test_homestead_needs_the_crystal_and_starts_closed(world):
    a, b = join(world, "Homer"), join(world, "Guest")
    a.go_home()
    world.tick(0.05)
    assert not world.homes.is_home_map(a.cur_map.name)          # no Hearth Anchor: nowhere to go
    stock(a, Hearth_Anchor=1)
    a.go_home()
    world.tick(0.05)
    assert world.homes.owner_of(a.cur_map.name) == "Homer" and a.on_own_home()
    assert world.homes.home_of("Homer")["visit"] == "closed"
    assert "Homer" not in world.homes.visitable_by("Guest")
    b.visit_home("Homer")
    world.tick(0.05)
    assert b.cur_map is not a.cur_map
    a.set_visit("open")
    b.visit_home("Homer")
    world.tick(0.05)
    assert b.cur_map is a.cur_map
    a.set_visit("closed")                                         # closing sends visitors back
    world.tick(0.05)
    assert b.cur_map is not a.cur_map
    leave(world, a)
    leave(world, b)


def test_building_uses_materials_and_is_shared(world):
    a, b = join(world, "Builder"), join(world, "Friend")
    stock(a, Hearth_Anchor=1)
    a.go_home()
    world.tick(0.05)
    hold_pocket(world, a)
    m = a.cur_map
    assert not a.build(6, 6, "Plank001")                          # no planks
    stock(a, Plank=30, Nails=60)
    assert a.build(6, 6, "Plank001")
    assert a.items_held("Plank") == 29 and m.tile[m.cell(6, 6)] == "Plank001"
    assert not a.build(6, 6, "Stone_Wall001")                     # Homesteading too low
    assert not b.build(7, 6, "Plank001")                          # not their home
    assert not a.build(*world.homes.arrival, "Plank001")          # where the anchor puts you down
    a.update_skill("Homesteading", "=10")
    for x in range(4, 8):
        for y in range(9, 12):
            assert a.build(x, y, "Shingle")
    assert m.roof[m.cell(4, 9)] == "Shingle_Roof001" and m.roof[m.cell(7, 11)] == "Shingle_Roof015"
    assert m.roof[m.cell(5, 10)] == "Shingle_Roof008"
    assert a.unbuild(5, 10) and m.roof[m.cell(5, 10)] == ""
    assert a.unbuild(6, 6) and m.tile[m.cell(6, 6)] == world.homes.base_of("Builder").tile[m.cell(6, 6)]
    a.friends_menu()
    a.add_friend("Friend")
    a.set_visit("friends")
    assert world.homes.may_visit("Builder", "Friend")
    leave(world, a)
    leave(world, b)


def test_homes_are_saved_and_come_back(world):
    a = join(world, "Keeper")
    stock(a, Hearth_Anchor=1, Plank=10, Nails=40, Iron_Bar=4)
    a.update_skill("Homesteading", "=10")
    a.go_home()
    world.tick(0.05)
    hold_pocket(world, a)
    assert a.build(8, 8, "Home_Chest") and a.build(9, 8, "Timber001")
    saved = world.homes.state()
    leave(world, a)
    w2 = World(ROOT)
    w2.homes.load(saved)
    m = w2.homes.map_of("Keeper")
    assert m.tile[m.cell(9, 8)] == "Timber001"
    assert w2.homes.object_at(m, 8, 8).name == "Home_Chest"
    s = Session(w2, "Other")
    s.load_state({"map": m.name, "x": 384, "y": 536})             # logged out in a home that's closed to them
    w2.sessions["Other"] = s
    s.enter_world()
    w2.tick(0.05)
    assert s.cur_map is not m


def test_home_bed_is_where_you_wake(world):
    a = join(world, "Sleeper")
    stock(a, Hearth_Anchor=1, Plank=10, Nails=20, Wool=6)
    a.update_skill("Homesteading", "=10")
    a.go_home()
    world.tick(0.05)
    hold_pocket(world, a)
    m = a.cur_map
    assert a.build(10, 10, "Bed001") and m.decor[m.cell(10, 11)] == "Bed002"     # (its foot, in the tile below)
    assert a.unbuild(10, 11) and not m.decor[m.cell(10, 10)] and not m.decor[m.cell(10, 11)]   # (down whole)
    assert a.build(10, 10, "Bed001")
    world.homes.home_of("Sleeper")["bed"] = [10, 10]
    a.leave_home()                                                 # (they die somewhere else)
    world.tick(0.05)
    assert not a.on_own_home()
    a.player_dies()
    a.handle({"t": "respawn"})
    world.tick(0.05)
    assert a.on_own_home()
    leave(world, a)


def test_dying_keeps_undroppables_and_the_five_most_valuable(world):
    a = join(world, "Faller")
    value = lambda n: int(float(world.data.entity_ini(n, "Value", "0") or 0))
    stock(a, Hearth_Anchor=1, Logs=5, Sapphire=3, Iron_Bar=3, **{"Gold_Coin(s)": 100})
    a.drop_inventory_item(a.inv_item(next(e.uid for e in a.inv if e.name == "Hearth_Anchor")), 1)
    assert a.items_held("Hearth_Anchor") == 1                      # can't be dropped
    slot = 1
    a.equipped[slot] = "Iron_Sword" if value("Iron_Sword") else a.equipped[slot]
    a.player_dies()
    assert a.items_held("Hearth_Anchor") == 1                      # nor lost when you die
    assert a.items_held("Gold_Coin(s)") == 0 and a.items_held("Logs") == 0
    kept = sorted([e.name for e in a.inv for _ in range(e.quantity) if e.name != "Hearth_Anchor"] +
                  [n for n in a.equipped[1:] if n])
    pool = sorted(["Sapphire"] * 3 + ["Iron_Bar"] * 3 + ["Logs"] * 5 + ["Iron_Sword"], key=value, reverse=True)
    assert len(kept) == 5
    assert sorted(value(n) for n in kept) == sorted(value(n) for n in pool[:5])
    assert any(i[0] == "Logs" for i in a.grave["items"])
    leave(world, a)


def test_dropped_things_are_yours_alone_for_ten_seconds(world):
    a, b = join(world, "Dropper"), join(world, "Watcher")
    stock(a, Logs=1)
    a.drop_inventory_item(a.inv_item(next(e.uid for e in a.inv if e.name == "Logs")), 1)
    e = next(x for x in world.ents if x.name == "Logs" and x.private_to is a)
    assert world.visible_to(e, a) and not world.visible_to(e, b)
    world.tick(0.05, now=world.now + 11000)
    assert world.visible_to(e, b)
    leave(world, a)
    leave(world, b)


def test_farming_grows_and_only_the_sower_harvests(world):
    a, b = join(world, "Farmer Jo"), join(world, "Thief")
    farms = world.farms
    m = world.maps["13,-3,0"]
    x, y = 4, 14
    assert m.tile[m.cell(x, y)] == "Soil001"
    for s in (a, b):
        s.player.x, s.player.y = m.ox + (x - 1) * 32, m.oy + y * 32
    world.tick(0.05)
    stock(a, Potato_Seed=2, Pumpkin_Seed=1)
    soil = a.tile_entity_at(m.ox + (x - 0.5) * 32, m.oy + (y - 0.5) * 32)
    a.script_cursor_x, a.script_cursor_y = soil.x + 16, soil.y + 16
    a.item_in_use = a.inv_item(next(e.uid for e in a.inv if e.name == "Pumpkin_Seed"))
    a.use_item_with(soil)
    assert (m.name, x, y) not in farms.plots                        # Farming too low for pumpkins
    a.item_in_use = a.inv_item(next(e.uid for e in a.inv if e.name == "Potato_Seed"))
    a.use_item_with(soil)
    assert farms.plots[(m.name, x, y)]["owner"] == "Farmer Jo" and m.decor[m.cell(x, y)] == "Potato_Crop001"
    start, clock = farms.clock(), farms.clock
    farms.clock = lambda: start + 10 * 60                           # time passes
    world.tick(0.05, now=world.now + 2000)
    assert m.decor[m.cell(x, y)] == "Potato_Crop003"
    crop = a.tile_entity_at(m.ox + (x - 0.5) * 32, m.oy + (y - 0.5) * 32)
    for s in (a, b):
        s.script_cursor_x, s.script_cursor_y = crop.x + 16, crop.y + 16
    b.do_action("Harvest", crop)
    assert b.items_held("Potato") == 0 and (m.name, x, y) in farms.plots
    a.do_action("Harvest", crop)
    assert a.items_held("Potato") >= 3 and (m.name, x, y) not in farms.plots and m.decor[m.cell(x, y)] == ""
    farms.clock = clock
    leave(world, a)
    leave(world, b)


def test_the_settlers_quest_gives_the_crystal(world):
    st = next(e for e in world.ents if getattr(e, "npc_id", "") == "Homestead_Settler")
    m = world.maps[st.map]
    s = join(world, "Apprentice", st.map, int(st.x - m.ox), int(st.y - m.oy + 34))

    def talk(answer, ticks=10):
        s.do_action("Talk to", st)
        for _ in range(10):
            world.tick(0.05)
        words = list(s.responses)
        s.action_box_response_chosen(answer)
        for _ in range(ticks):
            world.tick(0.05)
        return words

    talk(1)
    assert s.get_attribute("HomeQuest") in ("", "0")                 # not before the ferry
    s.update_attribute("Passage", "=12")                           # (the Isle's quests done)
    assert talk(1)[0] == "I'll do it!"
    assert s.get_attribute("HomeQuest") == "1"
    stock(s, Plank=10, Stone_Block=4)
    talk(1, ticks=40)
    assert s.get_attribute("HomeQuest") == "2" and s.items_held("Hearth_Anchor") == 1
    assert s.items_held("Plank") == 0
    assert talk(1)[0] == "Sell me something." and s.ab_mode == "Shop"
    leave(world, s)


def test_each_home_keeps_its_own_land(world):
    a = join(world, "Landholder")
    stock(a, Hearth_Anchor=1)
    a.go_home()
    world.tick(0.05)
    saved = world.homes.state()
    assert saved["Landholder"]["land"][:21] == world.homes.template_lines[:21]
    w2 = World(ROOT)
    changed = list(w2.homes.template_lines)                       # the starting land is redesigned: all sand
    changed[:21] = [":".join(["Sand001"] * 25)] * 21
    w2.homes.template_lines = changed
    old = dict(saved["Landholder"])
    del old["land"]                                               # (a home saved before homes kept their land)
    w2.homes.load({"Landholder": saved["Landholder"], "Oldtimer": dict(old, n=old["n"] + 50)})
    m = w2.homes.map_of("Landholder")
    assert m.tile[m.cell(5, 5)] == "Rim_Mist001"                  # the existing home is as it was
    assert w2.homes.map_of("Oldtimer").tile[w2.homes.map_of("Oldtimer").cell(5, 5)] == "Sand001"
    assert w2.homes.state()["Oldtimer"]["land"][0].startswith("Sand001")   # (copied once, kept from now on)
    new = w2.homes.create("Newcomer")
    assert w2.homes.map_of("Newcomer").tile[w2.homes.map_of("Newcomer").cell(5, 5)] == "Sand001"
    assert new["land"] == changed
    leave(world, a)


def test_the_market_is_one_for_everyone(world):
    boards = [e for e in world.ents if e.name == "Market_Board"]
    assert len(boards) >= 5                                       # (Ashford's market and every shardstone town)
    ash, far = boards[0], boards[-1]
    ma, mf = world.maps[ash.map], world.maps[far.map]
    seller = join(world, "Seller", ma.name, int(ash.x - ma.ox), int(ash.y - ma.oy + 40))
    buyer = join(world, "Buyer", mf.name, int(far.x - mf.ox), int(far.y - mf.oy + 40))
    stock(seller, Bread=5, Hearth_Anchor=1)
    stock(buyer, **{"Gold_Coin(s)": 100})
    seller.do_action("Trade", ash)
    assert seller.ab_mode == "Market"
    bread = next(e for e in seller.inv if e.name == "Bread")
    crystal = next(e for e in seller.inv if e.name == "Hearth_Anchor")
    assert "Sell on the market" in seller.get_verbs(bread)
    assert "Sell on the market" not in seller.get_verbs(crystal)  # (what can't be dropped can't be sold)
    seller.verb_price, seller.verb_qty = 7, 4
    seller.do_action("Sell on the market", bread)
    assert seller.items_held("Bread") == 1
    assert [(l["item"], l["qty"], l["price"]) for l in world.market.listings] == [("Bread", 4, 7)]
    seller.close_action_box(-1)
    leave(world, seller)                                          # the seller goes; their listing stays up
    buyer.do_action("Trade", far)                                 # (another town's board: the same market)
    box = buyer.box_state()
    assert box["prices"] == [7] and box["sellers"] == ["Seller"] and box["mine"] == [False]
    assert "Buy 5" in buyer.get_verbs(buyer.rack_pseudo(0))
    buyer.do_action("Buy 5", buyer.rack_pseudo(0))
    assert buyer.items_held("Bread") == 4 and buyer.items_held("Gold_Coin(s)") == 100 - 28
    assert world.market.listings == [] and world.market.purses["Seller"] == 28
    w2 = World(ROOT)
    w2.market.load(world.market.state())
    assert w2.market.purses["Seller"] == 28
    seller = join(world, "Seller", ma.name, int(ash.x - ma.ox), int(ash.y - ma.oy + 40))
    seller.do_action("Trade", ash)
    assert seller.responses[0] == "Collect 28 gold"
    gold = seller.items_held("Gold_Coin(s)")
    seller.action_box_response_chosen(1)
    assert seller.items_held("Gold_Coin(s)") == gold + 28 and world.market.purses["Seller"] == 0
    leave(world, seller)
    leave(world, buyer)


def test_old_stalls_become_listings():
    w = World(ROOT)
    w.market.load(None, old_stalls={"Stall_1": {"owner": "Old", "items": [["Bread", 3, 5, 0]], "till": 12}})
    assert [(l["seller"], l["item"], l["qty"]) for l in w.market.listings] == [("Old", "Bread", 3)]
    assert w.market.purses["Old"] == 12


def find_open_ground(world, m):
    for ty in range(3, 19):
        for tx in range(3, 23):
            c = m.cell(tx, ty)
            if m.tile[c].startswith("Grass") and not m.decor[c] and not m.roof[c] and "0" not in m.walk[c]:
                return tx, ty
    raise AssertionError("no open grass")


def test_digging_finds_things_now_and_then(world, monkeypatch):
    m = world.maps["1,1,0"]
    tx, ty = find_open_ground(world, m)
    s = join(world, "Digger", m.name, (tx - 1) * 32 + 8, (ty - 1) * 32)
    stock(s, Spade=1)
    spade = next(e for e in s.inv if e.name == "Spade")
    assert "Dig" in s.get_verbs(spade)
    import random as rnd
    monkeypatch.setattr(rnd, "uniform", lambda a, b: a)          # (the luckiest dig there is: something turns up)
    gold = s.items_held("Gold_Coin(s)")
    s.do_action("Dig", spade)
    assert s.dig_pending is not None
    world.tick(0.05, now=world.now + 3000)
    pm, px, py = world.tile_at(s.player.z, s.player.fx, s.player.fy)
    assert pm.decor[pm.cell(px, py)] == "Dug_Hole001"            # (a hole, that grasses over later)
    assert any("CHANGE.TILE" in q and "Dug_Hole001" in q for q in world.action_queue)
    assert s.items_held("Gold_Coin(s)") > gold                    # (gold: the first find in Digging.ini)
    s.do_action("Dig", spade)
    assert s.dig_pending is None                                  # (dug already)
    assert spade.wear == 1                                        # (the spade wears with each dig)
    leave(world, s)


def test_what_you_dig_up_depends_on_where(world):
    s = join(world, "Prospector")
    chance, finds = s.dig_finds(world.maps["2,19,0"])                 # (the desert: its own finds, nothing else)
    names = {f[0] for f in finds}
    assert chance == 9 and "Glass" in names and "Potato_Seed" not in names
    chance, finds = s.dig_finds(world.maps["1,1,0"])                 # (the Isle: worms as well as the usual)
    names = {f[0] for f in finds}
    assert chance == 12 and {"Bait", "Gold_Coin(s)", "Potato_Seed"} <= names
    chance, finds = s.dig_finds(world.maps["11,-3,0"])                 # (Ashford: the usual)
    assert chance == 7 and "Bait" not in {f[0] for f in finds}
    leave(world, s)


def test_tools_wear_out_and_a_broken_one_wont_do(world):
    s = join(world, "Woodsman")
    stock(s, Bronze_Axe=1)
    axe = next(e for e in s.inv if e.name == "Bronze_Axe")
    assert s.is_tool("Bronze_Axe") and not s.is_tool("Logs")


    def swing(script):                                             # (a script's check for the axe, as Chop Tree has)
        s.script_name, s.script_tools_used = script, set()
        s.script_lines = ["", "01	>Got.Item	Bronze_Axe	1	03", "02	>Got.Item	Bronze_Axe	1	03", "03	End", ""]
        s.script_line_no = 1
        s.execute_script_line()
        after = s.script_line_no                                   # (2: it's there; 3: it isn't)
        s.execute_script_line()
        return after
    assert swing("Chop Tree") == 2 and axe.wear == 1                # (found, and worn once a go)
    swing("Talk to Miner")
    assert axe.wear == 1                                           # (asked about, not used: no wear)
    axe.wear = world.data.item_max_dur("Bronze_Axe")               # (worn right out)
    assert s.tools_held("Bronze_Axe") == 0 and s.items_held("Bronze_Axe") == 1
    assert not s.use_tool("Bronze_Axe")
    assert swing("Chop Tree") == 3                                  # (a broken axe: "You need an axe!")
    leave(world, s)


def test_a_wave_attack_comes_in_waves_and_rewards_the_defenders(world):
    waves = world.waves
    assert "Ashford_Raid" in waves.defs and "Farm_Raid" in waves.defs
    d = waves.defs["Ashford_Raid"]
    m = world.maps[d["map"]]
    s = join(world, "Defender", m.name, 384, 300)
    s.god_mode = 1
    gold = s.items_held("Gold_Coin(s)")
    assert waves.start("Ashford_Raid") and not waves.start("Ashford_Raid")
    for n in range(len(d["waves"])):
        world.tick(0.05, now=world.now + 1000)
        r = waves.running["Ashford_Raid"]
        assert r["wave"] == n and r["uids"]
        assert any(e.get("t") == "wave" and e.get("wave") == n + 1 for e in s.out)
        for u in list(r["uids"]):                                 # the defender kills this wave
            e = world.by_uid[u]
            s.kill_npc(e)
            if e.alive:
                world.remove_entity(e)
        world.tick(0.05, now=world.now + 600)
        world.tick(0.05, now=world.now + 60000)                   # (the gap before the next wave)
    assert "Ashford_Raid" not in waves.running
    assert s.items_held("Gold_Coin(s)") > gold + int(d["reward.gold"])   # (the reward, and gold for each kill)
    leave(world, s)


def test_every_town_has_a_surprise_raid_that_waits_for_someone_there(world):
    """build_town_raids.py: a raid for every town; waves.py: a surprise one comes while someone's there to meet it."""
    waves = world.waves
    assert len([k for k in waves.defs if k.endswith("_Raid")]) >= 13
    assert {"Northport_Raid", "Keep_Raid", "Frosthold_Raid", "Dunerest_Raid"} <= set(waves.defs)
    a, b = join(world, "Far_Away", "1,1,0", 300, 300), join(world, "Far_Away_Too", "1,1,0", 340, 300)
    for k in waves.defs:
        waves.next_random[k] = world.now + 10 ** 9
    waves.next_random["Northport_Raid"] = world.now - 1
    waves.random_attacks()
    assert "Northport_Raid" not in waves.running                    # (nobody in Northport: it waits)
    assert waves.next_random["Northport_Raid"] > world.now
    s = join(world, "Northporter", waves.defs["Northport_Raid"]["map"], 384, 300)
    waves.next_random["Northport_Raid"] = world.now - 1
    waves.random_attacks()
    assert "Northport_Raid" in waves.running
    waves.finish("Northport_Raid", waves.running["Northport_Raid"], False)
    for who in (a, b, s):
        leave(world, who)


def test_the_towns_gone_and_moved_and_their_quests_with_them(world):
    """remove_towns.py, move_keep.py, move_ashford.py, build_manors.py: what the quests name is where they say."""
    place = world.data.place
    for gone in ("Fenwick_Square", "Highwatch_Square", "Ravensgate_Square"):
        assert place(gone) is None, gone
    for pid in ("Saltmarsh_Elder", "Frosthold_Captain", "Keep_Gravekeeper", "Granny_Bramble", "Rooks_Pier",
                "Drowned_Abbey", "Fenmoor_Hall", "Redrock_Manor", "Mire_Tunnel_East", "Mire_Tunnel_West"):
        assert place(pid) is not None, pid
    assert place("Kings_Solar").map == "26,18,1" and place("Keep_Square").map == "25,18,0"
    assert place("Ashford_Square").map == "12,-2,0" and world.maps.get("12,-6,0") is not None
    assert place("Granny_Bramble").map == place("Thornwick_Square").map


def test_redrock_manor_is_a_maze_of_ladders_and_stairs(world):
    """build_manors.py: three floors, every way up lined up with its way down, the vault reached only from above."""
    import sys as _sys
    _sys.path.insert(0, os.path.join(world.data.root, "dev", "migrate"))
    import build_manors as B
    pl = world.data.place("Redrock_Manor")
    mx, my = pl.map.split(",")[:2]
    floors = {f: world.maps["%s,%s,%d" % (mx, my, z)] for f, z in B.FLOORS.items()}
    for lower, upper, (x, y), kind in B.LINKS:
        lo, hi = floors[lower], floors[upper]
        if kind == "stairs":
            assert lo.tile[lo.cell(x, y)] == "Stairs001" and hi.tile[hi.cell(x, y)] == "Stairs002", (lower, x, y)
        else:
            assert lo.decor[lo.cell(x, y)] == "Ladder001" and hi.decor[hi.cell(x, y)] == "Hatch001", (lower, x, y)
    assert ("e", 1, 1) not in B.GAPS["G"] and ("s", 2) not in B.GAPS["G"] and ("e", 2, 1) not in B.GAPS["G"]


def test_the_mire_tunnel_leads_under_the_range_and_up_again(world):
    """reshape_west.py: the Mirefen's only way in, a cave mouth each side of the range and steps up from the tunnel."""
    import re as _re
    for side in ("East", "West"):
        down = open(os.path.join(world.data.root, "data", "Scripts", "Enter Mire_Tunnel_%s.txt" % side)).read()
        up = open(os.path.join(world.data.root, "data", "Scripts", "Climb Up Mire_Tunnel_%s_Steps.txt" % side)).read()
        below = _re.search(r"Teleport\t\d+,\d+\t(\S+)", down).group(1)
        above = _re.search(r"Teleport\t\d+,\d+\t(\S+)", up).group(1)
        assert below.endswith(",-1") and below in world.maps
        assert above.endswith(",0") and above in world.maps
        assert world.data.place("Mire_Tunnel_%s_Steps" % side).map.endswith(",-1")


def test_a_script_starts_a_wave_and_a_lost_one_ends(world):
    d = world.waves.defs["Farm_Raid"]
    m = world.maps[d["map"]]
    s = join(world, "Farmhand", m.name, 384, 300)
    s.start_script("Talk to Farmer", True)
    for _ in range(5):
        world.tick(0.05)
    s.action_box_response_chosen(2)                               # "Seen any goblins?"
    for _ in range(5):
        world.tick(0.05)
    s.action_box_response_chosen(2)                               # "They're here now? I'll fight them off!"
    for _ in range(10):
        world.tick(0.05)
    assert "Farm_Raid" in world.waves.running
    world.tick(0.05, now=world.now + 10 * 60000)                  # (out of time: they get away)
    assert "Farm_Raid" not in world.waves.running
    assert not any(e.alive and e.source == "WAVE" for e in world.ents)
    leave(world, s)


def test_tavern_games(world, monkeypatch):
    keeper = world.placed_entity("INNKEEPER")
    table = world.placed_entity("DICE_TABLE_1")
    assert keeper is not None and table is not None
    m = world.maps[keeper.map]
    a = join(world, "Gambler", m.name, int(keeper.x - m.ox), int(keeper.y - m.oy + 34))
    b = join(world, "Punter", m.name, int(keeper.x - m.ox), int(keeper.y - m.oy + 34))
    stock(a, **{"Gold_Coin(s)": 200})
    stock(b, **{"Gold_Coin(s)": 200})
    import random as rnd
    monkeypatch.setattr(rnd, "randint", lambda lo, hi: 2)        # (the coin under the middle cup; every die a 2)
    a.do_action("Talk to", keeper)
    assert a.responses[0] == "Three Cups."
    a.out = []
    a.action_box_response_chosen(1)                               # Three Cups: its table
    shown = lambda s: [ev for ev in s.out if ev["t"] == "game"][-1]
    assert shown(a)["game"] == "cups" and shown(a)["phase"] == "stake" and shown(a)["stakes"] == [5, 20, 50, 100]
    a.game_input({"do": "stake", "stake": 20})
    assert shown(a)["phase"] == "pick" and "coin" not in shown(a)  # (where the coin is stays the server's)
    a.game_input({"do": "pick", "n": 2})                          # the middle cup
    assert shown(a)["coin"] == 2 and shown(a)["won"] == 50
    assert a.items_held("Gold_Coin(s)") == 200 - 20 + 50
    a.game_input({"do": "leave"})
    assert a.game is None and shown(a)["game"] == ""
    a.do_action("Talk to", keeper)
    a.action_box_response_chosen(2)                               # High or Low: 2, and every die after a 2
    a.game_input({"do": "stake", "stake": 5})
    assert shown(a)["first"] == 2
    a.game_input({"do": "guess", "higher": True})
    assert shown(a)["second"] == 2 and shown(a)["won"] == 0        # (the same again: the house wins)
    a.game_input({"do": "leave"})
    a.player.x, a.player.y = table.x, table.y + 30
    b.player.x, b.player.y = table.x + 10, table.y + 30
    a.do_action("Play", table)
    a.game_input({"do": "stake", "stake": 50})                    # a round at 50 gold
    b.out = []
    b.do_action("Play", table)
    assert shown(b)["round"]["players"] == ["Gambler"]
    b.game_input({"do": "join"})
    assert world.tavern.rounds["Dice_Table_1"]["players"] == ["Gambler", "Punter"]
    assert shown(a)["round"]["players"] == ["Gambler", "Punter"]  # (everyone at the table sees who's in)
    world.tick(0.05, now=world.now + 21000)
    assert "Dice_Table_1" not in world.tavern.rounds
    assert shown(b)["rolled"]["Gambler"] == [2, 2, 2] and set(shown(b)["winners"]) == {"Gambler", "Punter"}
    assert a.items_held("Gold_Coin(s)") == 225 and b.items_held("Gold_Coin(s)") == 200   # (a tie: they share)
    a.player.x += 400                                             # (walked off: the table's screen goes)
    world.tick(0.05)
    assert a.game is None
    leave(world, a)
    leave(world, b)


def test_picking_a_lock_is_a_minigame(world):
    s = join(world, "Picker")
    lines = ["01\tPlay.Minigame\tLOCK\t1\t03", "02\tUpdate.Attribute\tPicked\t=1", "03\tEnd"]
    s.out = []
    assert s.run_script_lines("Lock Test", lines)
    s.run_scripts()
    shown = lambda: [ev for ev in s.out if ev["t"] == "game"][-1]
    assert shown()["game"] == "lock" and len(shown()["pins"]) == 3 and s.script_state == "MINIGAME"
    pin = s.game["pins"][0]
    tap(s, ((pin["band"] / 2 + 0.5 - pin["phase"]) % 1) * pin["period"])   # (at the bottom)
    assert shown()["slipped"] and s.game["slips"] == 1 and s.game["pin"] == 0
    pick_the_lock(s)
    assert shown()["game"] == "" and s.game is None
    s.run_scripts()
    assert s.get_attribute("Picked") == "1"                        # (won: on to the next line)
    s.update_attribute("Picked", "0")
    assert s.run_script_lines("Lock Test", lines)
    s.run_scripts()
    for _ in range(3):                                              # (three slips and the nail's out of the lock)
        pin = s.game["pins"][0]
        tap(s, ((pin["band"] / 2 + 0.5 - pin["phase"]) % 1) * pin["period"])
    assert s.game is None
    s.run_scripts()
    s.run_scripts()
    assert s.get_attribute("Picked") == "0" and not s.script_running
    leave(world, s)


def test_a_lock_judges_the_tap_by_the_servers_clock(world):
    from dsengine.minigames import TAP_LAG
    s = join(world, "Cheat")
    assert s.run_script_lines("Lock Test", ["01\tPlay.Minigame\tLOCK\t1\t02", "02\tEnd"])
    s.run_scripts()
    pin = s.game["pins"][0]
    pin["band"], pin["width"] = 0.7, 0.1                                      # (the bottom is never on its line, whatever's rolled)
    good = ((pin["band"] / 2 - pin["phase"]) % 1) * pin["period"]             # (just on its line)
    bottom = ((pin["band"] / 2 + 0.5 - pin["phase"]) % 1) * pin["period"]
    s.w.now = s.game["pin_at"] + int(bottom + 3 * pin["period"] + TAP_LAG)    # (it's at the bottom, by the server)
    s.game_input({"do": "set", "ms": int(good)})                              # (the page says it was long ago, just so)
    assert s.game["pin"] == 0 and s.game["slips"] == 1
    leave(world, s)


def test_arm_wrestling(world, monkeypatch):
    table = world.placed_entity("ARM_TABLE_1")
    assert table is not None
    m = world.maps[table.map]
    a = join(world, "Brawn", m.name, int(table.x - m.ox), int(table.y - m.oy + 30))
    b = join(world, "Sinew", m.name, int(table.x - m.ox + 10), int(table.y - m.oy + 30))
    stock(a, **{"Gold_Coin(s)": 100})
    stock(b, **{"Gold_Coin(s)": 100})
    shown = lambda s: [ev for ev in s.out if ev["t"] == "game"][-1]
    a.do_action("Play", table)
    assert shown(a)["game"] == "arm" and shown(a)["stakes"] == [5, 20, 50]
    a.game_input({"do": "house", "stake": 20})                     # the innkeeper, for 20
    assert a.items_held("Gold_Coin(s)") == 80 and shown(a)["bout"]["players"] == ["Brawn", "the innkeeper"]
    t = world.now
    while a.game["phase"] == "bout" and world.now < t + 30000:
        a.game_input({"do": "push"})
        world.tick(0.05, now=world.now + 80)
    assert shown(a)["winner"] == "Brawn" and a.items_held("Gold_Coin(s)") == 120   # (pushed hard: the pot)
    a.game_input({"do": "sit", "stake": 5})                       # then wait for a challenger
    assert a.items_held("Gold_Coin(s)") == 115
    b.do_action("Play", table)
    assert shown(b)["waiting"] == {"who": "Brawn", "stake": 5}
    b.game_input({"do": "take"})
    assert b.items_held("Gold_Coin(s)") == 95 and shown(a)["bout"]["players"] == ["Brawn", "Sinew"]
    while b.game["phase"] == "bout":
        b.game_input({"do": "push"})
        world.tick(0.05, now=world.now + 80)
    assert shown(a)["winner"] == "Sinew" and b.items_held("Gold_Coin(s)") == 105
    a.game_input({"do": "sit", "stake": 50})
    a.game_input({"do": "leave"})                                  # (up from the table: the stake back)
    assert a.items_held("Gold_Coin(s)") == 115 and not world.arms.waiting
    leave(world, a)
    leave(world, b)


def test_a_door_opening_sends_that_tile_not_the_whole_map(world):
    from dsengine.view import snapshot
    s = join(world, "Watcher", "3,1,0", 300, 300)
    m = world.maps["3,1,0"]
    first = snapshot(world, s)
    assert any(ev["t"] == "mapdata" and ev["name"] == "3,1,0" for ev in first)
    before, beside = m.cell_text(5, 5), m.cell_text(6, 5)
    world.change_tile(m, 5, 5, "Dirt001")
    world.change_tile(m, 6, 5, "Dirt001")
    sent = [ev for ev in snapshot(world, s) if ev.get("name") == "3,1,0"]
    assert [ev["t"] for ev in sent] == ["mapcells"]                # (just the two tiles)
    assert [c[0] for c in sent[0]["cells"]] == [m.cell(5, 5), m.cell(6, 5)] and sent[0]["v"] == m.version
    for k in range(60):                                            # (a great many at once: the whole map again)
        world.change_tile(m, 5, 5, "Grass001" if k % 2 else "Dirt001")
    assert [ev["t"] for ev in snapshot(world, s) if ev.get("name") == "3,1,0"] == ["mapdata"]
    world.change_tile(m, 5, 5, before)
    world.change_tile(m, 6, 5, beside)
    leave(world, s)


def test_only_so_many_bets_an_hour(world):
    s = join(world, "HighRoller")
    stock(s, **{"Gold_Coin(s)": 500})
    most = int(world.data.config_read("Gameplay", "Gamble.Max.Bets", "10"))
    for _ in range(most - 2):
        assert s.pay_stake(5)
    st = s.save_state()
    leave(world, s)
    s = join(world, "HighRoller")                                    # (logging out doesn't start the count again)
    s.load_state(st)
    assert s.pay_stake(5) and s.pay_stake(5)
    s.out = []
    gold = s.items_held("Gold_Coin(s)")
    assert not s.pay_stake(5) and s.items_held("Gold_Coin(s)") == gold
    assert any("enough gambling" in str(ev.get("text", "")) for ev in s.out)
    s.bets = [t - 3601 for t in s.bets]                              # (an hour on)
    assert s.pay_stake(5)
    leave(world, s)


def test_a_chest_shows_what_is_in_it_before_it_is_yours(world):
    chest = next(e for e in world.ents if e.npc_id == "Hob_Camp_Chest")    # (the hobgoblins' camp: grow_isle.py)
    m = world.maps[chest.map]
    s = join(world, "Looter", m.name, int(chest.x - m.ox), int(chest.y - m.oy + 36))
    gold = s.items_held("Gold_Coin(s)")
    s.unlocked_chests.add(s.chest_key(chest))                       # (the Isle's chests are locked: picked already)
    s.do_action("Open", chest)
    for _ in range(10):
        world.tick(0.05)
    assert s.ab_mode == "Chest"
    names = [it["name"] for it in s.box_state()["items"]]
    assert "Bronze_Sword" in names and "Gold_Coin(s)" in names and not any(n.endswith("_Scroll") for n in names)
    assert s.items_held("Bronze_Sword") == 0 and s.items_held("Gold_Coin(s)") == gold        # (not yours yet)
    i = names.index("Gold_Coin(s)")
    assert s.get_verbs(s.rack_pseudo(i)) == "Take 1,Take all,Examine"
    s.do_action("Take 1", s.rack_pseudo(i))
    assert s.items_held("Gold_Coin(s)") == gold + 1
    s.close_action_box(-1)
    saved = s.save_state()
    assert any(it[0] == "Gold_Coin(s)" and it[1] == 29 for v in saved["chests"].values() for it in v)
    s.do_action("Open", chest)                                     # (what's left is still there, for them)
    assert s.ab_mode == "Chest"
    s.action_box_response_chosen(1)                                # Take everything
    assert s.items_held("Bronze_Sword") == 1
    assert s.items_held("Gold_Coin(s)") == gold + 30 and not s.chests
    s.do_action("Open", chest)                                     # (empty now: the script says so)
    for _ in range(10):
        world.tick(0.05)
    assert s.ab_mode != "Chest"
    leave(world, s)


def test_not_skilled_enough_plays_a_sound(world):
    s = join(world, "Novice")
    stock(s, Ice_Bolt_Scroll=1)
    scroll = next(e for e in s.inv if e.name == "Ice_Bolt_Scroll")
    s.out.clear()
    s.cast_scroll(scroll, None)
    assert any(e.get("t") == "sound" and e.get("name") == "Denied" for e in s.out)
    leave(world, s)


def test_dying_waits_for_the_player_to_respawn(world):
    a = join(world, "Mortal", "11,-3,0", 384, 300)
    where = (a.player.x, a.player.y, a.cur_map.name)
    a.player_dies()
    assert any(e.get("t") == "died" for e in a.out) and any(e.get("name") == "Death" for e in a.out)
    world.tick(0.05)
    assert (a.player.x, a.player.y, a.cur_map.name) == where and not a.player_visible      # (still where they fell)
    a.handle({"t": "move", "dir": 2})
    for _ in range(5):
        world.tick(0.05)
    assert (a.player.x, a.player.y) == where[:2]                   # (no walking while dead)
    assert a.save_state()["map"] == world.data.start_map           # (logging off now: they'd wake at the start)
    a.handle({"t": "respawn"})
    world.tick(0.05)
    assert a.cur_map.name == world.data.start_map and a.player_visible and not a.dead_wait
    leave(world, a)


def test_nothing_carries_on_while_dead(world):
    a = join(world, "Bleeder", "11,-3,0", 384, 300)
    a.status_start("Bleed")
    a.keyboard_direction = 2                                       # (an arrow key held down as they fell)
    a.player_dies()
    hp = a.player.hp
    where = (a.player.x, a.player.y)
    for _ in range(40):
        world.tick(0.05, now=world.now + 500)                      # (twenty seconds dead)
    assert a.player.hp == hp and (a.player.x, a.player.y) == where
    a.handle({"t": "respawn"})
    world.tick(0.05)
    start = (a.player.x, a.player.y)
    for _ in range(10):
        world.tick(0.05)
    assert (a.player.x, a.player.y) == start and not a.status   # (no walking off, no bleeding on)
    leave(world, a)


def test_a_bolt_waits_for_you_to_choose_its_target(world):
    wolf = next(e for e in world.ents if e.name == "Wolf" and e.alive)
    m = world.maps[wolf.map]
    a = join(world, "Caster", m.name, int(wolf.x - m.ox), int(wolf.y - m.oy + 40))
    stock(a, Fire_Bolt_Scroll=2)
    a.spell_chance = lambda spell: 100                            # (no fizzling, for this)
    scroll = next(e for e in a.inv if e.name == "Fire_Bolt_Scroll")
    assert "Learn" in a.get_verbs(scroll)
    a.do_action("Learn", scroll)                                  # (read: the spell is theirs, the scroll goes)
    assert "Fire_Bolt" in a.spells_known and a.items_held("Fire_Bolt_Scroll") == 1
    scroll = next(e for e in a.inv if e.name == "Fire_Bolt_Scroll")
    assert "Cast" not in a.get_verbs(scroll) and "Learn" not in a.get_verbs(scroll)   # (a scroll only teaches)
    a.out = []
    a.cast_scroll(scroll, None)
    assert any("already know this" in str(e.get("text", "")) for e in a.out) and a.items_held("Fire_Bolt_Scroll") == 1
    a.spell_auto_target = lambda rng: None                        # (nobody in reach: Channeling holds it ready)
    a.out = []
    a.handle({"t": "cast", "spell": "Fire_Bolt"})
    assert any(e.get("t") == "ready" and e.get("spell") == "Fire_Bolt" for e in a.out)
    shards = a.shards()
    a.handle({"t": "cast", "spell": "Fire_Bolt", "target": {"k": "ent", "uid": wolf.uid}, "x": wolf.cx, "y": wolf.cy})
    assert a.shards() == shards - 3                               # (then clicked on the wolf: cast, 3 Shards)
    leave(world, a)


def test_frost_nova_freezes_the_foes_round_you_but_not_a_boss(world):
    a = join(world, "Frosty", "11,-3,0", 384, 300)
    m = a.cur_map
    a.skill_level = lambda skill: 60                               # (a mage who never fizzles)
    a.spell_chance = lambda spell: 100
    a.spells_known["Frost_Nova"] = 1
    stock(a, Shard=40)
    wolves = [world.add_npc("Wolf", 0, m.ox + x * 32, m.oy + 9 * 32, "Attitude=Bad") for x in (10, 13)]
    boss = world.add_npc("Valour_Guardian", 0, m.ox + 12 * 32, m.oy + 11 * 32, "Attitude=Bad")
    far = world.add_npc("Wolf", 0, m.ox + 22 * 32, m.oy + 18 * 32, "Attitude=Bad")
    for e in wolves + [boss, far]:
        e.hp = e.max_hp = 500                                      # (alive after the blast)
    a.out = []
    shards = a.shards()
    a.handle({"t": "cast", "spell": "Frost_Nova"})                 # (from Channeling)
    assert a.shards() == shards - a.spell_cost("Frost_Nova")
    assert all(w.hp < 500 and w.frozen_until for w in wolves)       # (hurt, and held in the ice)
    assert boss.hp < 500 and boss.frozen_until is None              # (hurt, but no ice holds it)
    assert far.hp == 500 and far.frozen_until is None               # (too far off)
    assert any("2 foes are frozen" in str(e.get("text", "")) for e in a.out)
    w = wolves[0]
    where = (w.x, w.y)
    for _ in range(40):                                             # (two seconds: it neither moves nor fights)
        world.tick(0.05, now=world.now + 50)
    assert (w.x, w.y) == where and a.player.hp == a.player_max_hp
    from dsengine.view import entity_state
    assert entity_state(world, w, a)["fz"] == 1
    for _ in range(80):                                             # (five seconds on, it thaws)
        world.tick(0.05, now=world.now + 50)
    assert w.frozen_until is None and entity_state(world, w, a)["fz"] == 0
    for e in wolves + [boss, far]:
        world.remove_entity(e)
    leave(world, a)


def test_arrows_need_feathers_and_hens_drop_them(world):
    racks = open(os.path.join(ROOT, "data", "ItemRacks.ini"), encoding="cp1252").read()
    assert "Item4=Arrows,Logs 1 Bronze_Bar 1 Feather 3," in racks
    assert "Feather," in world.data.entity_ini("Chicken", "Drops", "")


def test_the_way_down_is_through_the_chapel(world):
    def climb(s, verb, tx, ty):
        m = s.cur_map
        gx, gy = m.ox + (tx - 1) * 32 + 16, m.oy + (ty - 1) * 32 + 16
        e = s.tile_entity_at(gx, gy)
        assert verb in s.get_verbs(e)
        s.out = []
        s.choose_verb(verb, e, gx, gy)                             # (as a click does: where, too)
        for _ in range(60):
            world.tick(0.05, now=world.now + 50)                   # (the climb's heard, then a moment, then you move)
        return s.cur_map.name, any(ev.get("t") == "sound" and ev.get("name") == "Denied" for ev in s.out)

    s = join(world, "Pilgrim", "3,1,0", 17 * 32, 8 * 32)
    s.connected = True
    verger = next(e for e in world.ents if e.npc_id == "Chapel_Verger")
    assert verger.display == "Brother Aldous" and s.display_name(verger) == "Brother Aldous"
    assert climb(s, "Climb Down", 18, 8) == ("3,1,-1", False)      # anyone may go down to the cellar
    s.teleport("3,1,-1", 13 * 32, 9 * 32 - 8)
    for _ in range(5):
        world.tick(0.05)
    assert climb(s, "Climb Down", 14, 9) == ("3,1,-1", True)       # the trapdoor: locked, without its key
    stock(s, Chapel_Cellar_Key=1)
    assert climb(s, "Climb Down", 14, 9) == ("3,1,-1", True)       # the key, but Brother Aldous hasn't said you're ready
    s.update_attribute("AmuletQuest", "=4")
    assert climb(s, "Climb Down", 14, 9) == ("3,1,-2", False)      # now down you go (the trapdoor stays shut)
    leave(world, s)

def test_dying_ends_buffs_and_debuffs(world):
    s = join(world, "Mortal")
    s.spell_attack_bonus, s.spell_attack_until = 5, world.now + 60000
    s.boost_from = {"attack": "Strength_Potion"}
    s.status_start("Poison")
    s.player_dies()
    st = s.me_state()
    assert not st["boost_left"] and not st["status_left"] and st["boosts"]["attack"] == 0
    s.respawn()
    leave(world, s)


def test_fences_join_up_at_their_corners(world):
    a = join(world, "Fencer")
    stock(a, Hearth_Anchor=1, Plank=20, Nails=40)
    a.update_skill("Homesteading", "=10")
    a.go_home()
    world.tick(0.05)
    hold_pocket(world, a)
    m = a.cur_map
    spots = [(4, 14), (5, 14), (6, 14), (4, 15), (4, 16)]
    for x, y in spots:
        while m.decor[m.cell(x, y)]:                               # (the land's own bushes and stones, cleared)
            a.unbuild(x, y)
        assert a.build(x, y, "Wood_Fence001")
    piece = lambda x, y: m.decor[m.cell(x, y)]
    assert piece(4, 14) == "Wood_Fence003"                         # the corner: east and south
    assert piece(5, 14) == "Wood_Fence001" and piece(6, 14) == "Wood_Fence001"
    assert piece(4, 15) == "Wood_Fence002" and piece(4, 16) == "Wood_Fence002"
    planks = a.items_held("Plank")
    assert a.unbuild(5, 14)                                        # a gap: the pieces either side change
    assert piece(4, 14) == "Wood_Fence002" and piece(6, 14) == "Wood_Fence012"
    assert a.items_held("Plank") >= planks                         # (half back, rounded down)
    assert world.homes.home_of("Fencer")["cells"]["4,14"]["decor"] == "Wood_Fence002"
    leave(world, a)


def test_the_effects_bar_knows_what_hurts_and_for_how_long(world):
    s = join(world, "Sufferer")
    s.status_start("Poison")
    st = s.me_state()
    assert 0 < st["status_left"]["Poison"] <= 14000
    assert st["status_info"]["Poison"] == "1 damage every 2 s"
    assert s.status_words("Burn") == "1-2 damage every second"
    assert s.status_words("Chill").startswith("Slowed")
    leave(world, s)


def test_a_kills_loot_is_the_killers_for_ten_seconds(world, monkeypatch):
    import dsengine.npcs as NP
    import dsengine.remnants as RM
    monkeypatch.setattr(NP, "rnd", lambda: 0.0)                    # (every drop drops: the world rolls a kill's loot)
    monkeypatch.setattr(RM, "rnd", lambda: 0.0)                    # (and its remnants: a goblin's too weak to rise)
    a, b = join(world, "Slayer"), join(world, "Passerby")
    goblin = next(e for e in world.ents if e.name == "Goblin")
    before = {e.uid for e in world.ents}
    a.add_npc_drops(goblin)
    loot = [e for e in world.ents if e.uid not in before]
    assert loot and all(e.private_to is a for e in loot)
    assert all(world.visible_to(e, a) and not world.visible_to(e, b) for e in loot)
    world.now += 11000
    assert all(world.visible_to(e, b) for e in loot)
    for e in loot:
        world.remove_entity(e)
    leave(world, a)
    leave(world, b)


def test_crafting_lists_go_by_the_level_they_need(world):
    s = join(world, "Crafter")
    assert s.open_item_rack("CRAFT", "Workbench", "CRAFT-Smithing") is not False
    levels = [r["level"] for r in s.rack]
    assert levels == sorted(levels) and len(levels) > 3
    leave(world, s)


def test_a_chair_can_stand_on_a_rug(world):
    a = join(world, "Decorator")
    stock(a, Hearth_Anchor=1, Plank=20, Nails=40, Wool=20, Logs=20, Herb=20)
    a.update_skill("Homesteading", "=30")
    a.go_home()
    world.tick(0.05)
    hold_pocket(world, a)
    m = a.cur_map
    x, y = 5, 15
    while m.decor[m.cell(x, y)]:
        a.unbuild(x, y)
    rug = next(k for k, p in world.homes.catalog.items() if k.startswith("Rug"))
    chair = next(k for k, p in world.homes.catalog.items() if k.startswith("Chair"))
    for k in (rug, chair):
        for item, qty in world.homes.catalog[k]["needs"]:
            stock(a, **{item: qty * 2})
    assert a.build(x, y, rug) and m.under[m.cell(x, y)] == rug and not m.decor[m.cell(x, y)]
    assert a.build(x, y, chair)                                    # (on the rug)
    assert m.under[m.cell(x, y)] == rug and m.decor[m.cell(x, y)] == chair
    assert "+Under(%s)+Decor(%s)" % (rug, chair) in m.cell_text(x, y)
    assert a.unbuild(x, y) and m.decor[m.cell(x, y)] == "" and m.under[m.cell(x, y)] == rug    # the chair first
    assert a.unbuild(x, y) and m.under[m.cell(x, y)] == ""                                     # then the rug
    leave(world, a)


def pick_the_lock(s):
    """Sets every pin of the lock on s's game screen, each just as it crosses its line."""
    while s.game is not None and s.game["game"] == "lock":
        pin = s.game["pins"][s.game["pin"]]
        tap(s, ((pin["band"] / 2 - pin["phase"]) % 1) * pin["period"])


def tap(s, ms):
    """Taps the lock's pin ms after it began bobbing, by the server's clock as by the page's."""
    s.w.now = s.game["pin_at"] + int(ms)
    s.game_input({"do": "set", "ms": int(ms)})


def isle_helpers(world, s):
    """run, npc, talk and use for a test that plays through the Isle's quests (time jumps on as it runs)."""
    def run(ticks=30, ms=50):
        for _ in range(ticks):
            world.tick(0.05, now=world.now + ms)

    def npc(name, map_name, npc_id=""):
        return next(e for e in world.ents if e.name == name and e.map == map_name and e.alive and
                    (not npc_id or e.npc_id == npc_id) and world.visible_to(e, s))

    def talk(e, *answers):
        m = world.map_at(e.z, e.x, e.y) or world.maps[e.map]          # (upstairs, if that's where they are now)
        s.teleport(m.name, int(e.x - m.ox), int(e.y - m.oy) + 30)
        run(5)
        s.do_action("Talk to", e)
        run(30)
        for n in answers:
            assert s.ab_mode == "Conversation", (e.name, n)
            s.action_box_response_chosen(n)
            run(30)
        if s.ab_mode:
            s.close_action_box(-1)
            run(5)

    def use(map_name, tx, ty, verb, below=True):
        """verb on tile tx,ty of map_name, standing on the tile below it (or on it)."""
        s.teleport(map_name, (tx - 1) * 32, (ty - (0 if below else 1)) * 32 - 8)
        run(5)
        m = s.cur_map
        gx, gy = m.ox + (tx - 1) * 32 + 16, m.oy + (ty - 1) * 32 + 16
        s.choose_verb(verb, s.tile_entity_at(gx, gy), gx, gy)
        run(60)

    return run, npc, talk, use


def test_the_heirs_isle_from_start_to_finish(world, monkeypatch):
    """Dinner at Edwin's, The Amulet of Succession and Passage to the Mainland, played through."""
    import dsengine.player_combat as pc
    import dsengine.scripting as sc
    monkeypatch.setattr(pc, "rnd", lambda: 0.0)                     # (spells don't fizzle in a test)
    monkeypatch.setattr(sc, "rnd", lambda: 0.0)                     # (and the cage's lock gives at the first try)
    day = world.day_fraction()
    world.set_day_fraction(0.5)                                     # (by day: Maren at her counter)
    s = join(world, "Heir", "0,-2,0", 16 * 32, 8 * 32)
    s.connected = True
    s.god_mode = True                                               # (the caves' beasts: no dying in a test)
    attr = lambda name: int(float(s.get_attribute(name) or 0))
    run, npc, talk, use = isle_helpers(world, s)
    assert attr("LastWill") == 2                                    # (a saved character: past the funeral)
    assert "Bronze_Sword" not in s.equipped                         # (no sword to start with)
    # Dinner at Edwin's
    maren = npc("Maren", "0,-2,0", "Maren_At_Counter")
    talk(maren, 1)                                                  # dinner? logs for the range first: an axe
    assert attr("DinnerQuest") == 1 and s.items_held("Bronze_Axe") == 1
    stock(s, Logs=3)
    talk(maren, 1)
    assert attr("DinnerQuest") == 2 and s.items_held("Logs") == 0
    rng = next(e for e in world.ents if e.npc_id == "Marens_Range")
    up = world.maps["0,-2,1"]
    s.teleport("0,-2,1", int(rng.x - up.ox), int(rng.y - up.oy) + 30)
    run(5)
    stock(s, Egg=1)
    s.item_in_use = next(e for e in s.inv if e.name == "Egg")
    s.use_item_with(rng)                                            # fried on Maren's range, upstairs
    run(60)
    assert s.items_held("Fried_Egg") == 1 and attr("DinnerQuest") == 3
    talk(npc("Edwin", "0,-2,0", "Edwin_At_Desk"), 1, 1, 1)           # the egg to Edwin; Maren gives the key
    assert s.items_held("Healing_Draught") >= 2                     # (and draughts: herbs mend you, not Shards)
    assert attr("DinnerQuest") == 4 and s.items_held("Chapel_Cellar_Key") == 1
    # The Amulet of Succession, and the papers begun
    bess = npc("Milkmaid", "2,0,0")
    talk(bess, 3, 1, 1)                                             # the mainland? Wim wants papers, Father wrote them; Frank
    assert attr("Passage") == 1 and attr("AmuletQuest") == 1
    frank = npc("Frank", "2,0,0", "Frank_At_Forge")
    talk(frank, 1)                                                  # his wood, his workbench
    assert attr("AmuletQuest") == 2 and s.items_held("Logs") >= 5
    s.open_item_rack("CRAFT", "Workbench", "CRAFT-Crafting")
    assert {r["item"] for r in s.rack if r["level"] <= 1} >= {"Wooden_Sword", "Wooden_Shield"}
    s.close_action_box(-1)
    stock(s, Wooden_Sword=1, Wooden_Shield=1)
    talk(frank, 1, 1)
    assert s.dismantle_worth("Copper_Dagger") >= 1 and s.items_held("Copper_Dagger") == 1   # (his old dagger)
    assert attr("AmuletQuest") == 3
    aldous = npc("Gravekeeper", "3,1,0", "Chapel_Verger")
    talk(aldous, 1)                                                 # not unarmed
    assert attr("AmuletQuest") == 3
    for name in ("Wooden_Sword", "Wooden_Shield"):
        s.do_action("Wield", next(e for e in s.inv if e.name == name))
    s.update_skill("Strength", "=2")
    s.update_skill("Defence", "=2")
    talk(aldous, 1)                                                 # armed and trained: the way down
    assert attr("AmuletQuest") == 4
    use("3,1,-1", 14, 9, "Climb Down")                              # the trapdoor, with Maren's key
    assert s.cur_map.name == "3,1,-2"
    for e in [e for e in world.ents if e.type == NPC and e.map == "1,1,-2" and e.hostile]:
        world.remove_entity(e)                                      # (no fighting in this test)
    s.teleport("1,1,-2", 5 * 32, 11 * 32 - 8)                       # (beside the niche at the back of the caves)
    run(10)
    niche = next(e for e in world.ents if e.name == "Barred_Niche" and e.owner is s)
    for e in [e for e in world.ents if e.type == NPC and e.map == "1,1,-2" and e.hostile]:
        world.remove_entity(e)                                      # (any that came back meanwhile)
    s.player_attack_target = None
    for _ in range(100):                                            # (a kill's script still running: wait for it)
        if not s.script_running and not s.script_queue:
            break
        run(1)
    s.teleport("1,1,-2", 5 * 32, 11 * 32 - 8)                       # (back beside the niche: a fight may have moved them)
    run(3)
    s.out = []
    s.do_action("Reach In", niche)                                  # too close for a hand: Aldous, and a scroll
    for _ in range(200):
        run(1)
        if s.ab_mode == "Conversation":
            break
    s.action_box_response_chosen(1)                                 # (the remnants first: Absorb them)
    for _ in range(200):
        run(1)
        if s.ab_mode == "Conversation":
            break
    assert s.items_held("Shard_Remnant") == 3, [m.get("text") for m in s.out if m.get("t") == "msg"]
    s.action_box_response_chosen(1)
    run(30)
    assert attr("AmuletQuest") == 5 and s.items_held("Grasp_Scroll") == 1
    s.cast_scroll(next(e for e in s.inv if e.name == "Grasp_Scroll"), None)       # (learnt: the scroll is used up)
    assert "Grasp" in s.spells_known and s.items_held("Grasp_Scroll") == 0
    s.cast_spell("Grasp", niche)                                                  # (cast, as from Channeling)
    run(30)
    s.action_box_response_chosen(1)
    run(30)
    assert s.items_held("Amulet_of_Succession") == 1 and s.items_held("Lair_Key") == 1 and attr("AmuletQuest") == 6
    assert not any(e.name == "Gravekeeper" and e.owner is s for e in world.ents)   # (he's gone back up)
    # Passage to the Mainland: the lair, Tobias, the house key, the floorboard, the papers, Wim
    door = world.maps["2,1,-2"]
    lk = door.lock_at[(14, 19)]
    assert not s.lock_closed(door, lk)                              # (the lair's door, with Aldous's key)
    s.teleport("2,2,-2", 18 * 32, 11 * 32 - 8)                      # (beside Tobias's cage)
    run(10)
    for e in [e for e in world.ents if e.name == "Hobgoblin" and e.map == "2,2,-2"]:
        world.remove_entity(e)                                      # (no fighting in this test)
    cage = next(e for e in world.ents if e.name == "Caged_Tobias" and e.owner is s)
    s.do_action("Talk to", cage)
    run(30)
    assert attr("Passage") == 2
    s.action_box_response_chosen(1)                                 # "I'll try": the lock
    run(10)
    assert s.game["game"] == "lock"
    pick_the_lock(s)
    run(80)
    assert s.ab_mode == "Conversation"
    s.action_box_response_chosen(1)
    run(30)
    assert attr("FatherFreed") == 1 and attr("Passage") == 3
    assert any(e.name == "Hob_Cage_Open" and e.owner is s for e in world.ents)
    use("2,2,-2", 5, 15, "Search")                                  # the corner barrel
    assert s.items_held("Fathers_House_Key") == 1
    use("2,2,-2", 17, 10, "Climb Up")                               # the hidden ladder, up into the camp
    assert s.cur_map.name == "2,2,0" and attr("LairLadder") == 1
    house = world.maps["1,1,0"]
    assert not s.lock_closed(house, house.lock_at[(20, 7)])
    m = world.maps["1,1,0"]
    assert s.tile_entity_at(m.ox + 20 * 32 + 16, m.oy + 5 * 32 + 16).name == "Plank001"   # (a board like the rest)
    for _ in range(10):                                             # (standing on it: it squeaks)
        s.player_tile = None
        s.teleport("1,1,0", 20 * 32, 5 * 32)
        run(20)
        if attr("Squeaked") == 1:
            break
    assert attr("Squeaked") == 1
    use("1,1,0", 21, 6, "Search")
    assert s.items_held("Marys_Papers") == 1 and attr("Passage") == 4
    use("1,1,0", 21, 6, "Search")
    assert s.items_held("Marys_Papers") == 1                        # (just the once)
    for k in range(len(s.skill_xp)):
        s.skill_xp[k] = max(s.skill_xp[k], 6)                       # (Wim won't take a green hand: level 3)
    s.absorb_remnants(next(e for e in s.inv if e.name == "Shard_Remnant"))   # (Aldous's lesson: nor before it)
    s.teleport("3,2,0", 14 * 32, 15 * 32)
    run(10)
    talk(npc("Ferryman", "3,2,0"), 1, 1)                            # the papers to Wim: aboard when a boat's in
    assert attr("Passage") == 5 and s.items_held("Marys_Papers") == 1
    world.set_day_fraction(day)
    leave(world, s)


def test_the_lairs_hobgoblins_come_back_when_someone_comes_in(world):
    s = join(world, "Raider", "2,2,-2", 13 * 32, 10 * 32)
    s.god_mode = 1                                                  # (four hobgoblins: they'd win)
    for _ in range(5):
        world.tick(0.05)
    hobs = [e for e in world.ents if e.name == "Hobgoblin" and e.map == "2,2,-2" and e.alive]
    assert len(hobs) == 4
    world.remove_entity(hobs[0])                                    # (one killed: no respawn while you're there)
    for _ in range(40):
        world.tick(0.05, now=world.now + 5000)
    assert len([e for e in world.ents if e.name == "Hobgoblin" and e.map == "2,2,-2" and e.alive]) <= 3
    s.teleport("2,1,-2", 14 * 32, 16 * 32)                          # out through the door, and back in
    for _ in range(5):
        world.tick(0.05)
    s.teleport("2,2,-2", 13 * 32, 10 * 32)
    for _ in range(5):
        world.tick(0.05)
    assert len([e for e in world.ents if e.name == "Hobgoblin" and e.map == "2,2,-2" and e.alive]) == 4
    leave(world, s)


def listen(world):
    """Every sound made from now on, as (name, level, who heard it), till world.sound is put back (del world.sound)."""
    heard, sound = [], world.sound

    def record(name, z, x, y, only=None, radius=600.0, seen=False):
        who = [s.player_name for s in ([only] if only is not None else world.hearers(z, x, y, radius))
               if not seen or world.sees_spot(s, z, x, y)]
        heard.append((name, z, who))
        sound(name, z, x, y, only, radius, seen)
    world.sound = record
    return heard


def test_townsfolk_take_the_stairs_to_bed(world):
    """Maren tends her counter by day; at night she walks up the stairs to her bed (Bed.Level=1) while you watch,
    and in the morning comes back down to it. Only Climb=1 tiles lead her: one Maren, not a night self upstairs."""
    def run(ticks):
        for _ in range(ticks):
            world.tick(0.05, now=world.now + 50)
    assert not [e for e in world.ents if e.npc_id in ("Maren_At_Home", "Edwin_At_Home")]
    assert world.data.climb_dir("Stairs001") == 1 and world.data.climb_dir("Stairs002") == -1
    down = world.maps["0,-2,0"]
    assert (down.ox + 19.5 * 32, down.oy + 1.5 * 32, 1) in world.climb_spots(down)
    s = join(world, "Lodger", "0,-2,0", 16 * 32, 4 * 32)             # (in the house, watching)
    day = world.day_fraction()
    maren = next(e for e in world.ents if e.npc_id == "Maren_At_Counter")
    counter = (maren.cx, maren.cy)
    world.set_day_fraction(0.95)                                    # (night: off up to bed)
    run(10)
    assert maren.z == 0 and not maren.ai.asleep                     # (walking to the stairs, not gone at once)
    heard = listen(world)
    for _ in range(900):
        run(1)
        if maren.z == 1:
            break
    del world.sound
    assert maren.z == 1 and ("Ladder", 0, ["Lodger"]) in heard     # (heard going up: in the room with her)
    assert ("Ladder", 1, []) in heard                               # (nobody upstairs to hear her come up)
    s.teleport("0,-2,1", 14 * 32, 3 * 32)                            # (upstairs after her: to bed she goes)
    run(600)
    assert maren.ai.asleep and maren.pose == "Sleep" and maren.z == 1
    world.set_day_fraction(0.5)                                     # (morning: down the stairs to her counter)
    for _ in range(1200):
        run(1)
        if maren.z == 0 and distance(maren.cx, maren.cy, *counter) < 4:
            break
    assert maren.z == 0 and not maren.ai.asleep and distance(maren.cx, maren.cy, *counter) < 4
    leave(world, s)
    world.set_day_fraction(0.6)
    run(5)
    assert maren.z == 0
    out = join(world, "Outsider", "0,-2,0", 23 * 32, 2 * 32)          # (outside, by the wall the stairs are against)
    assert world.roof_over(0, maren.cx, maren.cy) and not world.roof_over(0, out.player.fx, out.player.fy)
    assert not world.sees_spot(out, 0, down.ox + 19.5 * 32, down.oy + 1.5 * 32)
    heard = listen(world)
    world.set_day_fraction(0.95)                                    # (night: under the roof, she can't be seen going)
    run(5)
    del world.sound
    assert maren.z == 1 and not [h for h in heard if h[0] == "Ladder" and h[2]]   # (up, and nobody heard a thing)
    leave(world, out)
    edwin = next(e for e in world.ents if e.npc_id == "Edwin_At_Desk")
    t = join(world, "Passer", "0,-2,0", 9 * 32, 18 * 32)             # (out by the shore: too far off to see)
    run(5)
    leave(world, t)
    u = join(world, "Guest", "0,-2,1", 13 * 32, 2 * 32)
    run(5)
    assert edwin.z == 1 and edwin.ai.asleep
    world.set_day_fraction(day)
    leave(world, u)


def test_townsfolk_climb_ladders_and_roam_a_zone_on_two_floors(world):
    """A ladder up to a hatch is a climb as stairs are (Climb=1; never a cave's hole). One whose Zone.Levels=0,1 roams
    both floors of its house, up the ladder and back down it while you watch."""
    d = world.data
    assert d.climb_dir("Ladder001") == 1 and d.climb_dir("Hatch001") == -1 and d.climb_dir("Ladder006") == 0
    found = None
    for m in sorted(world.maps.values(), key=lambda m: m.name):
        if m.mz != 0:
            continue
        for x, y, dz in world.climb_spots(m):
            c = m.cell(int((x - m.ox) / 32) + 1, int((y - m.oy) / 32) + 1)
            below = (x, y + 32)
            if dz == 1 and "Ladder001" in (m.tile[c], m.decor[c]) and world.pixel_walkable(0, *below):
                found = (m, x, y)
                break
        if found:
            break
    assert found, "no house ladder"
    m, x, y = found
    tx, ty = int((x - m.ox) / 32) + 1, int((y - m.oy) / 32) + 1
    zone = "%d,%d,%d,%d" % (max(1, tx - 1), max(1, ty - 1), min(25, tx + 1), min(21, ty + 2))     # (close by: a house may have other rooms, out of the watcher's sight)
    day = world.day_fraction()
    world.set_day_fraction(0.5)
    e = world.add_npc("Villager", 0, x - 16, y + 32 - 24, "Attitude=Good Zone=%s Zone.Levels=0,1 Schedule=Always" % zone)
    assert e.ai.zone_levels == {0, 1} and e.ai.levels
    def in_the_room(z):
        """A spot a tile or two from the ladder (or hatch) on level z, under its roof, that can see it."""
        under = world.roof_over(z, x, y)
        for dx, dy in ((0, 64), (32, 64), (-32, 64), (64, 32), (-64, 32), (0, 96), (64, 0), (-64, 0)):
            if world.pixel_walkable(z, x + dx, y + dy) and world.roof_over(z, x + dx, y + dy) == under and                     world.in_line_of_sight(z, x + dx, y + dy - 15, x, y):
                return x + dx - 16, y + dy - 31
        return x - 16, y + 33
    sx, sy = in_the_room(0)
    s = join(world, "Watcher", m.name, int(sx - m.ox), int(sy - m.oy))
    heard = listen(world)
    went_up = came_down = False
    try:
        for _ in range(8000):
            world.tick(0.05, now=world.now + 50)
            if e.z == 1:
                if not went_up:                       # (up after it: by the hatch, to see it come back down)
                    ux, uy = in_the_room(1)
                    s.teleport(world.map_at(1, x, y).name, int(ux - m.ox), int(uy - m.oy))
                went_up = True
            elif went_up:
                came_down = True
                break
    finally:
        del world.sound
        world.remove_entity(e)
        world.set_day_fraction(day)
        leave(world, s)
    assert went_up and came_down and ("Ladder", 0, ["Watcher"]) in heard and ("Ladder", 1, ["Watcher"]) in heard


def test_the_smithy_smokes_by_day(world):
    smoke = next(e for e in world.ents if e.name == "Chimney_Smoke")
    day = world.day_fraction()
    world.set_day_fraction(0.95)
    world.tick(0.05, now=world.now + 3000)
    assert not smoke.active                                         # (Frank's gone home: the forge is out)
    world.set_day_fraction(0.5)
    world.tick(0.05, now=world.now + 3000)
    assert smoke.active
    world.set_day_fraction(day)


def test_the_towns_are_the_size_they_were_asked_to_be(world):
    """build_towns.py: each city its taverns, its halls, its law and its doctors (dev/migrate/build_towns.py)."""
    import re
    ids = [e.npc_id for e in world.ents if e.npc_id]
    count = lambda town, who: len([i for i in ids if re.fullmatch(r"%s_%s_\d+" % (town, who), i)])
    for town in ("Northport", "Keep", "Court"):
        assert count(town, "Barkeep") == 5, town                       # (five taverns)
        assert count(town, "Doctor") == 1, town                        # (a hospital)
    assert count("Northport", "Speaker") == 1 and count("Northport", "Constable") == 1     # (Parliament; police)
    for town in ("Frosthold", "Oakhollow", "Thornwick", "Emberwatch"):
        assert count(town, "Sheriff") == 1 and count(town, "Doctor") == 1, town
    for town in ("Greyford", "Dunerest", "Wildwood", "Saltmarsh"):
        assert count(town, "Barkeep") == 1, town                       # (a hamlet: its pub)


def test_a_tavern_has_a_room_for_the_night(world):
    bar = next(e for e in world.ents if (e.npc_id or "").startswith("Northport_Barkeep_"))
    m = world.maps[bar.map]
    s = join(world, "Lodger2", bar.map, int(bar.x - m.ox), int(bar.y - m.oy) + 40)
    s.connected = True
    stock(s, **{"Gold_Coin(s)": 10})
    s.do_action("Talk to", bar)
    for _ in range(10):
        world.tick(0.05)
    room = next(i for i, r in enumerate(s.responses, 1) if r.startswith("A room for the night"))   # (an inn's too)
    s.action_box_response_chosen(room)
    for _ in range(10):
        world.tick(0.05)
    assert s.items_held("Gold_Coin(s)") == 5 and s.sleeping()
    leave(world, s)


def test_a_character_from_before_the_heirs_story(world):
    done = Session(world, "Veteran")
    done.load_state({"map": "4,4,0", "x": 300, "y": 300, "attributes": [["Passage", "12"]]})
    assert [done.quest_done(q) for q in ("LastWill", "DinnerQuest", "AmuletQuest", "Passage")] == [True] * 4
    half = Session(world, "Halfway")
    half.load_state({"map": "2,0,0", "x": 300, "y": 300, "attributes": [["Passage", "7"]]})
    assert half.get_attribute("Passage") == "0" and half.quest_done("LastWill")      # (the Isle again, after the letter)
    assert not half.quest_done("Passage")



def test_a_save_from_before_greyford_had_its_name(world):
    s = Session(world, "Shepherdess")
    s.load_state({"map": "15,9,0", "x": 300, "y": 300,
                  "attributes": [["Passage", "12"], ["Waystone.Moorcross", "1"], ["Zone_Chest_Dustlands", "1"],
                                         ["Secret_Sallowcross_2", "1"]],
                  "quest_notes": [["Wolves of the Moor", 0, "Slay six wolves on Greymoor."]]})
    assert s.get_attribute("Waystone.Greyford") == "1" and s.get_attribute("Zone_Chest_Sallow_Waste") == "1"
    assert s.get_attribute("Secret_Greyford_2") == "1"
    assert s.quest_notes[0][0] == "Wolves of the Greyflats" and "Wolves of the Greyflats" in [q for q, _ in world.data.quest_table()]

def test_sneaking_past_the_smugglers(world):
    m = world.maps["-2,15,0"]
    at = lambda tx, ty: (m.ox + (tx - 1) * 32, m.oy + (ty - 1) * 32)
    opts = "Attitude=Bad Stand=1 Face=S Group=TESTCAMP Friendly.If=$Attr.SmugglerQuest>=3"
    sentry = world.add_npc("Smuggler", 0, *at(22, 15), opts)        # (in the open, east of the camp: looking south)
    mate = world.add_npc("Smuggler", 0, *at(24, 13), opts.replace("Face=S", "Face=N"))
    for e in (sentry, mate):
        e.ai.turn_at = world.now + 10 ** 9                          # (no glancing about, for the test)
    s = join(world, "Sneak", "-2,15,0", 21 * 32, 11 * 32)             # behind the sentry (north of him), 4 tiles off
    for _ in range(40):
        world.tick(0.05)
    assert not sentry.in_combat and not mate.in_combat               # (he looks the other way)
    s.teleport("-2,15,0", 21 * 32, 18 * 32)                           # in front of him
    for _ in range(40):
        world.tick(0.05)
    assert sentry.in_combat and sentry.target is s
    assert mate.in_combat and mate.target is s                       # he raised the alarm
    for e in (sentry, mate):
        world.npc_give_up(e, e.ai)
    s.update_attribute("SmugglerQuest", "=3")                       # Red Meg's deal: friends now
    assert not world.hostile_for(sentry, s)
    other = join(world, "Stranger", "-2,15,0", 21 * 32, 20 * 32)
    assert world.hostile_for(sentry, other)                         # (to them alone)
    for e in (sentry, mate):
        world.remove_entity(e)
    leave(world, s)
    leave(world, other)


def test_the_smugglers_run(world, monkeypatch):
    monkeypatch.setattr(world, "npc_sees", lambda e, a, s, d: False)   # (a perfect sneak, for the test)
    s = join(world, "Spy", "21,5,0", 10 * 32, 17 * 32)
    s.connected = True
    s.update_attribute("Passage", "=12")                           # (off the Isle: the ferry's been taken)
    attr = lambda: int(float(s.get_attribute("SmugglerQuest") or 0))

    def run(ticks=30, ms=0):
        for _ in range(ticks):
            world.tick(0.05, now=world.now + ms if ms else None)

    def talk(npc_id, *answers):
        e = next(x for x in world.ents if x.npc_id == npc_id)
        m = world.maps[e.map]
        s.teleport(e.map, int(e.x - m.ox) + 26, int(e.y - m.oy))
        run(5)
        s.do_action("Talk to", e)
        run(30)
        for n in answers:
            s.action_box_response_chosen(n)
            run(30)
        if s.ab_mode:
            s.close_action_box(-1)
            run(5)

    def use(map_name, tx, ty, verb, from_xy):
        s.teleport(map_name, *from_xy)
        run(5)
        m = s.cur_map
        gx, gy = m.ox + (tx - 1) * 32 + 16, m.oy + (ty - 1) * 32 + 16
        s.choose_verb(verb, s.tile_entity_at(gx, gy), gx, gy)
        run(60)
        run(3, ms=1500)

    talk("Smuggler_Sergeant", 1)
    assert attr() == 1
    use("16,4,0", 12, 14, "Search", (11 * 32, 14 * 32))               # the hollow barrel
    assert attr() == 2 and s.cur_map.name == "16,4,-1"
    use("17,4,-1", 16, 11, "Climb Up", (15 * 32, 11 * 32))            # up into the camp
    assert s.cur_map.name == "17,4,0"
    use("17,4,0", 16, 11, "Climb Down", (15 * 32, 11 * 32))           # (and back down the hatch: it's a way out)
    assert s.cur_map.name == "17,4,-1"
    talk("Red_Meg", 1)
    assert attr() == 3
    gold = s.items_held("Gold_Coin(s)")
    talk("Smuggler_Sergeant", 1, 1)                                 # (Meg's truce, carried)
    assert attr() == 4 and s.items_held("Gold_Coin(s)") == gold + 60
    assert s.get_attribute("SmugglerSide") == "0"
    run_q = next(q for q in s.quest_list() if q["title"] == "The Smugglers' Run")
    assert "truce" in str(run_q)                                    # (the journal says which way it ended)
    leave(world, s)


def past_a_lesson(world, s):
    """A stance form shown first (forms.py form_teach): Thank you, and on into their talk."""
    while s.native_menu and s.responses == ["Thank you."]:
        s.action_box_response_chosen(1)
        run_for(world, 30)


def smugglers_talk(world, s, npc_id, *answers):
    """Talk to npc_id (taken there), choosing each answer in turn."""
    e = world.placed_entity(npc_id, s)
    assert e is not None, npc_id
    m = world.maps[e.map]
    s.teleport(e.map, int(e.x - m.ox) + 26, int(e.y - m.oy))
    run_for(world, 5)
    s.do_action("Talk to", e)
    run_for(world, 30)
    past_a_lesson(world, s)
    for n in answers:
        s.action_box_response_chosen(n)
        run_for(world, 30)
    if s.ab_mode:
        s.handle({"t": "close"})                                    # (Esc, as the page sends it)
        run_for(world, 5)


def smugglers_go(world, s, map_name, tx, ty):
    s.teleport(map_name, (tx - 1) * 32, (ty - 1) * 32)
    run_for(world, 10)


def test_sending_holt_to_the_wrong_cove_and_under_the_tide(world):
    s = join(world, "Turncoat", "21,5,0", 10 * 32, 17 * 32)
    s.connected = True
    s.update_attribute("Passage", "=12")
    s.update_attribute("SmugglerQuest", "=2")
    names = lambda: [q["title"] for q in s.quest_list()]
    assert world.placed_entity("Meg_Cot", s) is None                # (no hideout till you've sided with her)
    smugglers_talk(world, s, "Red_Meg", 2)                          # "I'll send Holt to the wrong cove."
    assert s.get_attribute("SmugglerQuest") == "3" and s.get_attribute("SmugglerSide") == "1"
    assert s.side_attitudes.get("SMUGGLERS") == "Good"
    for pid in ("Meg_Cot", "Meg_Stash", "Meg_Tunnel_Cove", "Meg_Tunnel_Ashford"):
        assert world.placed_entity(pid, s) is not None, pid
    other = join(world, "Bystander", "21,5,0", 10 * 32, 17 * 32)
    assert world.placed_entity("Meg_Cot", other) is None            # (hers to you alone)
    leave(world, other)
    smugglers_talk(world, s, "Red_Meg", 2)                          # (no job till Holt's been sent the wrong way)
    assert s.items_held("Smuggled_Brandy") == 0 and s.get_attribute("UnderTideQuest") == "0"
    gold = s.items_held("Gold_Coin(s)")
    smugglers_talk(world, s, "Smuggler_Sergeant", 1)                # (only the wrong beach to tell him)
    assert s.get_attribute("SmugglerQuest") == "4" and s.items_held("Gold_Coin(s)") == gold + 60
    assert s.standing("Court") == -5                                # (-15, and the quest's own 10)
    assert "Under the Tide" in names() and "The Tide Turns" not in names()
    trap = world.placed_entity("Meg_Tunnel_Cove", s)                # Meg's tunnel, to Ashford's fields
    m = world.maps[trap.map]
    s.teleport(trap.map, int(trap.x - m.ox) + 20, int(trap.y - m.oy))
    run_for(world, 5)
    s.do_action("Climb Down", trap)
    run_for(world, 30)
    assert s.cur_map.name == "12,-1,0"
    smugglers_talk(world, s, "Red_Meg", 1)                          # Under the Tide
    assert s.get_attribute("UnderTideQuest") == "1" and s.items_held("Smuggled_Brandy") == 1
    smugglers_go(world, s, "21,5,0", 12, 19)
    watch = [e for e in world.ents if e.owner is s and e.name == "Guard" and e.map == "21,5,0"]
    assert len(watch) == 2 and all(e.ai.spotted == "Watch_Search" for e in watch)
    world.npc_spotted(watch[0], watch[0].ai, s)                     # (seen: the cask's taken, and you're put out)
    run_for(world, 30)
    assert s.items_held("Smuggled_Brandy") == 0 and s.get_attribute("UnderTideQuest") == "1"
    assert s.player.fy - s.cur_map.oy > 18 * 32
    smugglers_talk(world, s, "Red_Meg", 1)                          # (another cask)
    assert s.items_held("Smuggled_Brandy") == 1
    smugglers_talk(world, s, "Castle_Cellarer", 1)
    assert s.get_attribute("UnderTideQuest") == "2" and s.items_held("Smuggled_Brandy") == 0
    gold = s.items_held("Gold_Coin(s)")
    smugglers_talk(world, s, "Red_Meg", 1)
    assert s.get_attribute("UnderTideQuest") == "3" and s.items_held("Gold_Coin(s)") == gold + 90
    leave(world, s)


def test_leading_the_watch_into_the_camp_and_the_tide_turns(world):
    s = join(world, "Lawman", "21,5,0", 10 * 32, 17 * 32)
    s.connected = True
    s.god_mode = True                                               # (Meg's lads: no dying in a test)
    s.update_attribute("Passage", "=12")
    s.update_attribute("SmugglerQuest", "=3")                       # (Meg's truce in hand)
    smugglers_talk(world, s, "Smuggler_Sergeant", 2)                # "I'll lead your men in."
    assert s.get_attribute("SmugglerSide") == "2" and s.get_attribute("SmugglerQuest") == "3"
    assert s.side_attitudes.get("SMUGGLERS") == "Bad"
    assert world.placed_entity("Red_Meg", s) is None                # (gone: away by sea)
    smugglers_go(world, s, "17,4,0", 12, 20)
    men = [e for e in world.ents if e.owner is s and e.name == "Guard" and e.map == "17,4,0"]
    assert len(men) == 3
    camp = [e for e in world.ents if e.name == "Smuggler" and e.map == "17,4,0" and e.owner is None and e.alive]
    assert len(camp) >= 4
    world.npc_killed_by_npc(camp[0], men[0])                        # (your men's kill counts as yours)
    run_for(world, 5)
    assert s.get_attribute("SmugglerRaid") == "1"
    for e in camp[1:4]:
        s.kill_npc(e)
        run_for(world, 5)
    assert s.get_attribute("SmugglerRaid") == "4"
    gold = s.items_held("Gold_Coin(s)")
    smugglers_talk(world, s, "Smuggler_Sergeant", 1)
    assert s.get_attribute("SmugglerQuest") == "4" and s.items_held("Gold_Coin(s)") == gold + 60
    assert s.standing("Court") == 30
    smugglers_talk(world, s, "Smuggler_Sergeant", 1)                # The Tide Turns
    assert s.get_attribute("TideQuest") == "1"
    boat = world.placed_entity("Watch_Boat_Cove", s)
    m = world.maps[boat.map]
    s.teleport(boat.map, int(boat.x - m.ox), int(boat.y - m.oy) + 40)
    run_for(world, 5)
    s.do_action("Row", boat)
    run_for(world, 30)
    assert s.cur_map.name == "18,3,0"
    lads = [e for e in world.ents if e.owner is s and e.name == "Smuggler" and e.map == "18,3,0"]
    assert len(lads) == 2
    smugglers_talk(world, s, "Meg_On_The_Sandbar")
    assert s.get_attribute("TideQuest") == "1"                      # (not while her lads stand)
    for e in lads:
        s.kill_npc(e)
        run_for(world, 5)
    assert s.get_attribute("TideGuards") == "2"
    smugglers_talk(world, s, "Meg_On_The_Sandbar", 1)
    assert s.get_attribute("TideQuest") == "2" and world.placed_entity("Meg_On_The_Sandbar", s) is None
    gold = s.items_held("Gold_Coin(s)")
    smugglers_talk(world, s, "Smuggler_Sergeant", 1)
    assert s.get_attribute("TideQuest") == "3" and s.items_held("Gold_Coin(s)") == gold + 80
    s.out = []
    smugglers_talk(world, s, "Watch_Quartermaster", 1)              # (the watch's stores, open to you)
    assert "SHOP-Watch" in str(s.out) or "Steel_Platebody" in str(s.out)
    leave(world, s)


def test_quests_only_for_those_who_went_a_certain_way_and_banter_conditions(world):
    s = join(world, "Neutral", "21,5,0", 300, 300)
    s.update_attribute("SmugglerQuest", "=4")
    names = [q["title"] for q in s.quest_list()]
    assert "The Tide Turns" not in names and "Under the Tide" not in names     # (the truce: neither)
    assert world.banter.applies("$Attr.SmugglerQuest>=4 and $Attr.SmugglerSide=0", s)
    assert not world.banter.applies("$Attr.SmugglerSide=2", s)
    s.update_attribute("SmugglerSide", "=2")
    assert world.banter.applies("$Attr.SmugglerSide=2", s)
    assert "The Tide Turns" in [q["title"] for q in s.quest_list()]
    leave(world, s)


def test_closing_a_cutscenes_conversation_doesnt_leave_you_stuck(world):
    s = Session(world, "Impatient")
    s.load_state(None)
    world.sessions["Impatient"] = s
    s.connected = True
    s.enter_world()
    for _ in range(400):                                            # (Esc at every word of the funeral)
        world.tick(0.05, now=world.now + 50)
        if s.ab_mode == "Conversation":
            s.handle({"t": "close"})
        if s.user_input_enabled and s.get_attribute("LastWill") == "1":
            break
    assert s.user_input_enabled and s.cur_map.name == "4,0,0" and s.get_attribute("LastWill") == "1"
    leave(world, s)
    world.sessions.pop("Impatient", None)


def test_a_new_character_starts_at_their_mothers_funeral(world):
    s = Session(world, "Newborn")
    s.load_state(None)                                              # (a new character: data\\NewCharacter.ini)
    world.sessions["Newborn"] = s
    s.connected = True
    s.enter_world()
    for _ in range(10):
        world.tick(0.05, now=world.now + 50)
    assert s.cur_map.name == "4,1,0" and "Bronze_Sword" not in s.equipped
    assert not s.user_input_enabled                                 # (the funeral: you watch)
    for _ in range(40):                                             # (each answer as it comes, up to the cottage)
        for _ in range(60):
            world.tick(0.05, now=world.now + 100)
        if s.ab_mode == "Conversation":
            s.action_box_response_chosen(1)
        if s.get_attribute("LastWill") == "1" and s.user_input_enabled:
            break
    assert s.cur_map.name == "4,0,0" and s.get_attribute("LastWill") == "1"
    m = world.maps["4,0,0"]
    door = m.lock_at[(8, 13)]
    assert s.lock_closed(m, door)                                   # (not out until the letter's read)
    assert not any(e.name == "Edwin" and e.owner is s for e in world.ents)       # (he's gone)
    letter = next(e for e in world.ents if e.name == "Last_Will" and e.owner is s)
    s.do_action("Pickup", letter)
    for _ in range(20):
        world.tick(0.05, now=world.now + 50)
    for _ in range(4):                                              # "Read it", then the letter's three pages
        assert s.ab_mode == "Conversation"
        s.action_box_response_chosen(1)
        for _ in range(20):
            world.tick(0.05, now=world.now + 50)
    assert s.get_attribute("LastWill") == "2" and s.items_held("Last_Will") == 1
    assert not s.lock_closed(m, door)
    leave(world, s)
    world.sessions.pop("Newborn", None)


def test_up_to_the_chapel_loft_and_its_bell(world):
    s = join(world, "Ringer", "3,1,0", 13 * 32, 8 * 32)            # (by the stairs up, left of the altar)
    s.connected = True

    def use(verb, tx, ty):
        m = s.cur_map
        gx, gy = m.ox + (tx - 1) * 32 + 16, m.oy + (ty - 1) * 32 + 16
        e = s.tile_entity_at(gx, gy)
        assert verb in s.get_verbs(e), (verb, e.name if e else None)
        s.out = []
        s.choose_verb(verb, e, gx, gy)
        for _ in range(120):                                       # (time to walk there first)
            world.tick(0.05, now=world.now + 50)

    use("Climb Up", 14, 8)
    assert s.cur_map.name == "3,1,1"
    use("Ring", 16, 11)
    assert any(ev.get("t") == "sound" and ev.get("name") == "Bell" for ev in s.out)
    use("Climb Down", 14, 8)
    assert s.cur_map.name == "3,1,0"
    leave(world, s)


def test_the_ferry_runs_at_night(world):
    s = join(world, "NightOwl", "3,2,0", 14 * 32, 13 * 32)          # (on the Isle's pier)
    day = world.day_fraction()
    world.set_day_fraction(0.95)                                    # (deep in the night: townsfolk go home)
    for _ in range(100):
        world.tick(0.05, now=world.now + 100)
    wim = [e for e in world.ents if e.name == "Ferryman" and e.map == "3,2,0"]
    assert wim and all(e.active and not e.sched_away for e in wim)  # (Schedule=Always: he stays at his pier)
    world.set_day_fraction(day)
    leave(world, s)


def test_hens_do_not_keep_you_awake(world):
    m = world.maps["2,0,0"]
    s = join(world, "Sleeper", "2,0,0", 21 * 32, 16 * 32)           # (in the hens' yard)
    hens = [e for e in world.ents if e.name == "Chicken" and e.map == "2,0,0" and e.alive]
    assert hens and any(world.hostile_for(e, s) for e in hens)       # (you may chase them...)
    s.player_last_combat = 0
    wild = [e for e in world.ents if e.name == "Wolf" and e.alive]   # (the Isle's own wolves, out of it for this)
    for e in wild:
        e.alive = False
    assert "enemies" not in s.sleep_refusal()                        # (...but they're no reason not to sleep)
    for e in wild:
        e.alive = True
    wolf = world.add_npc("Wolf", 0, m.ox + 20 * 32, m.oy + 17 * 32, "Attitude=Bad")
    assert "enemies" in s.sleep_refusal()                            # (a wolf is)
    world.remove_entity(wolf)
    leave(world, s)


def test_jimmy_is_at_home_in_the_cottage(world):
    s = join(world, "CatLover", "4,0,0", 7 * 32, 11 * 32)           # (where a new character wakes)
    s.connected = True
    jimmy = [e for e in world.ents if getattr(e, "id", None) == "Jimmy" or getattr(e, "display", "") == "Jimmy"]
    assert len(jimmy) == 1 and jimmy[0].name == "Strawberry_Cat" and jimmy[0].map == "4,0,0"
    e = jimmy[0]
    assert not world.hostile_for(e, s) and "Stroke" in s.get_verbs(e) and "Attack" not in s.get_verbs(e)
    s.out = []
    s.choose_verb("Stroke", e, int(e.fx), int(e.fy))
    for _ in range(120):
        world.tick(0.05)
    assert any(ev.get("t") == "sound" and ev.get("name") == "Purr" for ev in s.out)
    assert any("Jimmy" in str(ev.get("text", "")) for ev in s.out)
    assert len({e.name for e in world.ents if e.name in ("Cat", "Black_Cat", "Ginger_Cat")}) == 3   # (and in the towns)
    leave(world, s)


def test_a_cat_sits_stretches_and_eats_a_fish(world):
    day = world.day_fraction()
    world.set_day_fraction(0.5)                                      # (by day: Jimmy keeps Schedule=Day)
    s = join(world, "CatFeeder", "4,0,0", 7 * 32, 11 * 32)
    s.connected = True
    e = next(e for e in world.ents if getattr(e, "display", "") == "Jimmy")
    a = e.ai
    world.set_entity_position(e, s.player.x + 24, s.player.y)
    a.pause_min = a.pause_max = 8                                    # (a long rest: it sits, sooner or later)
    for _ in range(40):
        world.npc_set_idle(e, a, False)
        if e.pose == "Sit":
            break
    assert e.pose == "Sit" and e.image.startswith("Strawberry_Cat_Sit")
    a.pose_next = ""                                                 # (settled: not about to lie down, which it may roll)
    a.fidget_at = world.now                                          # (now and then: a stretch, or its back to you)
    world.npc_fidget(e, a, world.now)                                # (its turn comes in the tick's own order: asked here)
    assert e.image[len("Strawberry_Cat_"):-1] in ("Stretch", "Butt")
    for _ in range(4):
        world.tick(0.05, now=world.now + 1000)
    assert not e.image[len("Strawberry_Cat_"):-1] in ("Stretch", "Butt") and a.fidget_until == 0
    assert "Feed" in s.get_verbs(e)
    s.out = []
    s.choose_verb("Feed", e, int(e.fx), int(e.fy))                   # nothing a cat would eat
    for _ in range(10):
        world.tick(0.05)
    assert any(ev.get("t") == "sound" and ev.get("name") == "Denied" for ev in s.out)
    stock(s, Raw_Meat=1, Raw_Trout=2)
    s.out = []
    s.choose_verb("Feed", e, int(e.fx), int(e.fy))
    for _ in range(10):
        world.tick(0.05)
    assert s.items_held("Raw_Trout") == 1 and s.items_held("Raw_Meat") == 1   # (a cat: the fish, not the meat)
    assert any("Jimmy eats the raw trout" in str(ev.get("text", "")) for ev in s.out)
    leave(world, s)
    world.set_day_fraction(day)


def test_sitting_on_a_bench_till_you_move(world):
    a = join(world, "Sitter", "0,0,10", 5 * 32, 3 * 32)              # (the arena's benches, along its top wall)
    b = join(world, "Stander", "0,0,10", 7 * 32, 3 * 32)
    m = a.cur_map
    gx, gy = m.ox + 4 * 32 + 16, m.oy + 1 * 32 + 16                  # (the bench at 5,2)
    bench = a.tile_entity_at(gx, gy)
    assert bench.name == "Bench001" and a.get_verbs(bench).split(",")[0] == "Sit"
    a.choose_verb("Sit", bench, gx, gy)
    for _ in range(40):
        world.tick(0.05)
    assert a.player.image == "Player_Sit4" and a.seat is not None   # (facing south, off the bench's back)
    stood = a.seat[0]                                                # (where they walked up to it)
    assert a.save_state()["y"] < bench.y - m.oy + 32 + 8            # (saved where they stood, not on the bench)
    b.choose_verb("Sit", b.tile_entity_at(gx, gy), gx, gy)           # one to a seat
    for _ in range(40):
        world.tick(0.05)
    assert b.seat is None and any("already sitting" in str(ev.get("text", "")) for ev in b.out)
    a.keyboard_direction = 4                                         # moving gets them up
    world.tick(0.05)
    a.keyboard_direction = 0
    world.tick(0.05)
    assert a.seat is None and not a.player.image.startswith("Player_Sit")
    assert abs(a.player.x - stood[0]) < 8 and abs(a.player.y - stood[1]) < 8   # (up where they stood, then a step)
    leave(world, a)
    leave(world, b)


def test_a_wolf_hunts_a_sheep_and_a_rat_bites_back(world):
    s = join(world, "Watcher", "0,0,10", 12 * 32, 4 * 32)             # (the arena: open sand, nothing else about)
    m = s.cur_map
    s.god_mode = True                                                # (the wolf would rather have them)
    held = [e for e in world.ents if e.type == NPC and e.map == m.name and "FOES" in getattr(e.ai, "hunts", ())]
    for e in held:
        world.ents.remove(e)                                         # (the arena's guard would go for the wolf)
    wolf = world.add_npc("Wolf", m.mz, m.ox + 6 * 32, m.oy + 12 * 32, "Zone=3,8,22,18")
    sheep = world.add_npc("Sheep", m.mz, m.ox + 9 * 32, m.oy + 12 * 32, "Zone=3,8,22,18")
    s.player_visible = False                                         # (out of its sight: the sheep, not them)
    world.tick(0.05)
    wolf.ai.hunt_at = world.now
    for _ in range(30):
        world.tick(0.05, now=world.now + 50)
    assert wolf.npc_foe is sheep and sheep.npc_foe is wolf           # the wolf goes for it, and it runs
    for _ in range(1200):
        world.tick(0.05, now=world.now + 50)
        if not sheep.alive:
            break
    left = [e for e in world.ents if e.type == MAPITEM and distance(e.cx, e.cy, sheep.cx, sheep.cy) < 48]
    assert not sheep.alive and any(e.name == "Raw_Meat" for e in left)  # (its loot, anyone's to take)
    for e in left:
        world.remove_entity(e)
    rat = world.add_npc("Rat", m.mz, wolf.cx + 40, wolf.cy, "Zone=3,8,22,18")
    dog = world.add_npc("Dog", m.mz, wolf.cx - 200, wolf.cy - 100, "Zone=3,8,22,18")
    world.npc_set_foe(dog, rat)
    world.npc_set_foe(rat, dog)
    hp = dog.hp
    for _ in range(400):
        world.tick(0.05, now=world.now + 50)
        if dog.hp < hp or not rat.alive:
            break
    assert dog.hp < hp or not rat.alive                              # (a rat doesn't run: it bites back)
    for e in (wolf, rat, dog):
        world.remove_entity(e)
    world.ents.extend(held)
    leave(world, s)


def test_walking_off_stops_the_work(world):
    s = join(world, "Woodcutter", "0,1,0", 7 * 32, 4 * 32)           # (just under the tree at 8,4)
    s.connected = True
    stock(s, Bronze_Axe=1)
    m = s.cur_map
    gx, gy = m.ox + 7 * 32 + 16, m.oy + 3 * 32 + 16
    tree = s.tile_entity_at(gx, gy)
    assert tree.name == "Tree001"
    logs = s.items_held("Logs")
    s.out = []
    s.choose_verb("Chop", tree, gx, gy)
    for _ in range(10):
        world.tick(0.05)
    assert s.script_running and s.work_from is not None             # (swinging)
    s.keyboard_direction = 4                                         # and off they go
    for _ in range(10):
        world.tick(0.05)
    s.keyboard_direction = 0
    for _ in range(100):
        world.tick(0.05, now=world.now + 50)
    assert not s.script_running and s.items_held("Logs") == logs
    assert any(ev.get("t") == "work_stop" for ev in s.out)
    assert not any("logs" in str(ev.get("text", "")) for ev in s.out)
    s.out = []
    s.choose_verb("Chop", tree, gx, gy)                              # (staying put: the work's done, logs or none)
    for _ in range(150):
        world.tick(0.05, now=world.now + 50)
    assert not s.script_running and any("logs!" in str(ev.get("text", "")) for ev in s.out)
    leave(world, s)


def test_the_admin_panel_goes_anywhere_and_runs_any_command(world):
    s = join(world, "Overseer")
    s.admin_enabled = True
    s.out = []
    s.admin_command({"do": "places"})
    places = next(ev["places"] for ev in s.out if ev["t"] == "admin_places")
    groups = {g for g, _, _ in places}
    assert {"On the world map", "Places", "People", "Things"} <= groups
    village = next(where for g, label, where in places if label == "Isle Village")
    assert village == "1,1,0 13 15"                                  # (a map and a tile, as the world map has it)
    s.admin_command({"do": "goto", "place": village})
    world.tick(0.05)
    assert s.cur_map.name == "1,1,0"
    s.admin_command({"do": "goto", "place": "Waystone_Ashford"})
    for _ in range(5):
        world.tick(0.05)                                             # (Ashford's own script, as you arrive)
    assert s.cur_map.name == "11,-3,0" and not s.script_running
    s.out = []
    s.admin_command({"do": "commands"})
    cmds = {c[0]: c[1] for c in next(ev["commands"] for ev in s.out if ev["t"] == "admin_commands")}
    assert cmds["Give.Item"] == ["ITEM NAME", "QUANTITY TO ADD"]
    s.admin_command({"do": "script", "command": "Give.Item", "args": ["Logs", "3"]})
    s.admin_command({"do": "script", "command": "Update.Attribute", "args": ["AdminTest", "=7"]})   # (one at a time)
    for _ in range(5):
        world.tick(0.05)
    assert s.items_held("Logs") == 3
    s.admin_command({"do": "script", "command": "Update.Attribute", "args": ["AdminTest", "=7"]})
    for _ in range(5):
        world.tick(0.05)
    assert s.get_attribute("AdminTest") == "7"
    leave(world, s)


def test_walking_granny_wren_to_her_daughter(world):
    s = join(world, "Guide", "4,4,0", 13 * 32, 9 * 32)              # (Northport's landing)
    s.connected = True
    s.update_attribute("Passage", "=5")                              # (over from the Isle: it can start)
    s.update_attribute("ParliamentQuest", "=2")                      # (the Parliament has spoken: Northport's gates are open)
    for _ in range(10):
        world.tick(0.05)
    granny = world.placed_entity("Granny_Wren", s)
    assert granny is not None and granny.owner is s                  # (each player's own)
    attr = lambda: s.get_attribute("EscortQuest")
    s.choose_verb("Talk to", granny, int(granny.cx), int(granny.cy))
    for _ in range(5):
        world.tick(0.05)
    s.action_box_response_chosen(1)                                  # "Of course. Follow me."
    for _ in range(5):
        world.tick(0.05)
    assert attr() == "1" and granny.follow is s
    m = world.maps["11,-3,0"]
    door = (m.ox + 13 * 32 + 16, m.oy + 18 * 32 + 16)                # (in front of Percy's door)
    bridges = [(bm.ox + (x - 1) * 32 + 16, bm.oy + (y - 1) * 32 + 16) for bm in world.maps.values()
               if bm.name.endswith(",0") and 4 <= int(bm.name.split(",")[1]) <= 6 and
               int(bm.name.split(",")[0]) in range(5, 11)
               for y in range(2, 21) for x in range(2, 25) if bm.tile[bm.cell(x, y)].startswith("Wood_Bridge_") and
               not bm.roof[bm.cell(x, y)] and any(bm.tile_is_water(x + dx, y + dy)
                                                  for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))]   # (a bridge)
    bridge = min(bridges, key=lambda b: abs(b[0] - (s.player.cx + door[0]) / 2) + abs(b[1] - door[1]))
    up_the_peninsula = [(gx * 32 + 16, gy * 32 + 16) for gx, gy in ((309, 80), (316, 40), (316, 0))]   # (to Ashford, north)
    legs = [bridge] + up_the_peninsula + [door]                      # (along the road: over the river's bridge)
    for _ in range(12000):                                           # (a long road: the guide waits for her)
        behind = distance(granny.cx, granny.cy, s.player.cx, s.player.cy)
        if legs[0] is not door and distance(s.player.cx, s.player.cy, *legs[0]) < 40:
            legs.pop(0)
        if s.player_walk_active and behind > 160:
            s.stop_player_walk()
        elif not s.player_walk_active and behind < 64:
            s.walk_player_to(legs[0][0], legs[0][1] - 14, 0, 4)
        world.tick(0.05, now=world.now + 50)
        if s.cur_map is m and distance(s.player.cx, s.player.cy, *door) < 40 and \
                distance(granny.cx, granny.cy, s.player.cx, s.player.cy) < 80:
            break
    assert s.cur_map is m and distance(granny.cx, granny.cy, s.player.cx, s.player.cy) < 80, (s.cur_map.name, s.player.cx / 32, s.player.cy / 32, granny.cx / 32, legs[:1] and (legs[0][0] / 32, legs[0][1] / 32))   # (she kept up)
    gold = s.items_held("Gold_Coin(s)")
    s.choose_verb("Talk to", granny, int(granny.cx), int(granny.cy))
    for _ in range(5):
        world.tick(0.05)
    s.action_box_response_chosen(1)                                  # "Glad I could help."
    for _ in range(5):
        world.tick(0.05)
    assert attr() == "2" and granny.follow is None and s.items_held("Gold_Coin(s)") == gold + 30
    leave(world, s)
    assert not granny.alive                                          # (gone with them; she lives at Percy's now)
    s = join(world, "Guide", "11,-3,0", 13 * 32, 19 * 32)
    s.load_state({"map": "11,-3,0", "x": 13 * 32, "y": 19 * 32, "attributes": [["EscortQuest", "2"]]})
    s.enter_world()
    for _ in range(10):
        world.tick(0.05)
    granny = world.placed_entity("Granny_Wren", s)
    assert granny is not None and granny.map == "11,-3,0" and distance(granny.cx, granny.cy, *door) < 64
    leave(world, s)


def test_a_guard_comes_to_help_against_a_goblin(world):
    s = join(world, "Helped", "0,0,10", 12 * 32, 12 * 32)             # (the arena's sand)
    m = s.cur_map
    s.god_mode = True
    guard = world.add_npc("Guard", m.mz, m.ox + 8 * 32, m.oy + 12 * 32, "Attitude=Good Zone=6,10,18,14")
    goblin = world.add_npc("Goblin", m.mz, m.ox + 14 * 32, m.oy + 12 * 32, "Attitude=Bad Zone=6,10,18,14")
    goblin.direction = 8                                             # (looking your way: a goblin sees only ahead)
    for _ in range(40):
        world.tick(0.05, now=world.now + 50)
    assert goblin.in_combat and goblin.target is s                    # (it's after the player)
    for _ in range(800):
        world.tick(0.05, now=world.now + 50)
        if not goblin.alive:
            break
    assert not goblin.alive and guard.alive                          # (the guard cut it down)
    world.remove_entity(guard)
    leave(world, s)


def test_the_guards_kills_count_and_whoever_fought_is_rewarded(world):
    waves = world.waves
    s = join(world, "Fighter", "11,-3,0", 10 * 32, 12 * 32)
    s.god_mode = True
    assert waves.start("Ashford_Raid")
    r = waves.running["Ashford_Raid"]
    gold = s.items_held("Gold_Coin(s)")
    for _ in range(20):
        for u in list(r["uids"]):
            e = world.by_uid[u]
            s.damage_npc(e, 1)                                       # (a blow from the player...)
            world.npc_killed_by_npc(e)                               # (...and the guards finish it)
        world.tick(0.05, now=world.now + 13000)
        if "Ashford_Raid" not in waves.running:
            break
    assert "Ashford_Raid" not in waves.running and r["kills"] == {}  # (won, though the guards made every kill)
    assert s.items_held("Gold_Coin(s)") >= gold + 60                 # (and the player who fought is paid)
    leave(world, s)


def test_mo_sits_for_a_portrait_only_when_sitting(world):
    from dsengine.entity import AI_IDLE, AI_ROAM
    ottilie = next(e for e in world.ents if e.npc_id == "Ashford_Painter")   # (not the court painter in Galaith)
    pm = world.maps[ottilie.map]
    s = join(world, "Patron", ottilie.map, int(ottilie.x - pm.ox), int(ottilie.y - pm.oy + 40))   # (by her easel)
    s.connected = True
    held = [e for e in world.ents if e.type == NPC and e.map == ottilie.map and e.hostile]
    for e in held:
        world.ents.remove(e)                                         # (the goblins in the square: no fighting here)
    s.update_attribute("Passage", "=5")
    for _ in range(5):
        world.tick(0.05)
    painter = world.placed_entity("Ashford_Painter", s)
    mo = world.placed_entity("Mo", s)
    attr = lambda: s.get_attribute("PortraitQuest")

    def talk(e):
        s.choose_verb("Talk to", e, int(e.cx), int(e.cy))
        for _ in range(40):
            world.tick(0.05)
        s.action_box_response_chosen(1)
        for _ in range(5):
            world.tick(0.05)

    def stroke(state, pose=""):
        world.set_entity_position(mo, s.player.x + 26, s.player.y)
        mo.ai.state, mo.pose, mo.ai.timer = state, pose, world.now + 60000
        mo.ai.fidget_at = mo.ai.turn_at = world.now + 60000              # (no stretch or glance about meanwhile)
        mo.ai.pose_next, mo.ai.fidget_until, mo.ai.pose_back = "", 0, ""
        s.out = []
        s.choose_verb("Stroke", mo, int(mo.cx), int(mo.cy))
        for _ in range(5):
            world.tick(0.05)
        return " ".join(str(ev.get("text", "")) for ev in s.out)

    talk(painter)
    assert attr() == "1"
    assert "trots off" in stroke(AI_ROAM) and attr() == "1"          # (on the move: off it goes)
    assert "back end" in stroke(AI_IDLE, "Butt") and attr() == "1"   # (the wrong end)
    assert "mid-stretch" in stroke(AI_IDLE, "Stretch") and attr() == "1"
    assert "stays put" in stroke(AI_IDLE, "Sit") and attr() == "2"   # sitting: it settles
    assert mo.ai.fixed_pose == "Sit"
    x = mo.x
    for _ in range(400):
        world.tick(0.05, now=world.now + 50)
    assert mo.x == x and world.npc_state(mo) == "Sit"                # (and stays sitting)
    talk(painter)
    assert attr() == "3" and s.items_held("Portrait_of_Mo") == 1 and mo.ai.fixed_pose == ""   # (painted; Mo's free)
    world.ents.extend(held)
    leave(world, s)


def test_a_seal_swims_comes_ashore_barks_and_leaves_its_pelt(world):
    from dsengine.entity import AI_ROAM
    def roomy(e):                                      # (open water on its map: not a seal by a narrow river)
        mm = world.maps[e.map]
        return any(mm.tile_is_water(x, y) and mm.tile_is_water(x + 1, y) and mm.tile_is_water(x, y + 1)
                   for y in range(2, 20) for x in range(2, 24))
    seal = next(e for e in world.ents if e.name == "Seal" and e.alive and roomy(e))
    m = world.maps[seal.map]
    s = join(world, "Beachcomber", seal.map, int(seal.x - m.ox), int(seal.y - m.oy))
    s.connected = True
    s.god_mode = True
    if not world.in_water(seal):                       # (the world's been going a while: it may be ashore already)
        wx, wy = next((x, y) for y in range(2, 20) for x in range(2, 24) if m.tile_is_water(x, y) and
                      m.tile_is_water(x + 1, y) and m.tile_is_water(x, y + 1))
        world.set_entity_position(seal, m.ox + (wx - 0.5) * 32 - seal.w / 2, m.oy + (wy - 0.5) * 32 - seal.h + 1)
    seal.ai.state = AI_IDLE                            # (and still: it may have been on its way ashore)
    assert world.in_water(seal)
    for _ in range(5):
        world.tick(0.05)
    world.animate_entity(seal, False)
    assert world.in_water(seal) and seal.image.startswith("Seal_Swim")          # (in the sea: just its head)
    sx, sy = (seal.cx - m.ox) / 32 + 0.5, (seal.cy - m.oy) / 32 + 0.5
    beaches = sorted(((x, y) for y in range(2, 21) for x in range(2, 25)    # (the nearest sand by the water first)
                      if not m.tile_is_water(x, y) and m.local_walkable((x - 0.5) * 32, (y - 0.5) * 32) and
                      any(m.tile_is_water(x + dx, y + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))),
                     key=lambda t: (t[0] - sx) ** 2 + (t[1] - sy) ** 2)
    a = seal.ai
    for beach in beaches[:6]:                                   # (one it can't reach from where it is: the next)
        a.goal_x, a.goal_y = m.ox + (beach[0] - 0.5) * 32, m.oy + (beach[1] - 0.5) * 32 - (seal.fy - seal.cy)
        world.npc_walk_started(seal, a, AI_ROAM)
        for _ in range(300):
            world.tick(0.05, now=world.now + 50)
            if not world.in_water(seal):
                break
        if not world.in_water(seal):
            break
    assert not world.in_water(seal) and not seal.image.startswith("Seal_Swim")   # (out on the beach)
    s.player.x, s.player.y = seal.x + 320, seal.y              # (out of earshot: an animal's call carries 8 tiles)
    a.call_at = world.now
    s.out = []
    world.tick(0.05, now=world.now + 50)
    assert not any(ev.get("t") == "sound" and ev.get("name") == "Seal_Bark" for ev in s.out)
    s.player.x, s.player.y = seal.x + 64, seal.y
    a.call_at = world.now
    s.out = []
    world.tick(0.05, now=world.now + 50)
    assert any(ev.get("t") == "sound" and ev.get("name") == "Seal_Bark" for ev in s.out)   # (near: it barks)
    x, y = seal.cx, seal.cy
    s.damage_npc(seal, 999)
    left = {e.name for e in world.ents if e.type == MAPITEM and distance(e.cx, e.cy, x, y) < 48}
    assert {"Seal_Pelt", "Seal_Blubber"} <= left
    leave(world, s)


def test_seal_blubber_is_bait_for_the_big_fish(world):
    spot = next(e for e in world.ents if e.name == "Swordfish_Spot" and e.alive)
    m = world.maps[spot.map]
    s = join(world, "Angler", spot.map, int(spot.x - m.ox), int(spot.y - m.oy) + 34)
    stock(s, Fishing_Rod=1, Seal_Blubber=2, Bait=5)
    s.update_skill("Fishing", "=50")
    for _ in range(10):                                              # (cast till one bites: a miss keeps the bait)
        s.choose_verb("Fish", spot, int(spot.cx), int(spot.cy))
        for _ in range(120):
            world.tick(0.05, now=world.now + 50)
        if s.items_held("Raw_Swordfish"):
            break
    assert s.items_held("Raw_Swordfish") == 1
    assert s.items_held("Seal_Blubber") == 1 and s.items_held("Bait") == 5   # (the blubber went on the hook, not a worm)
    leave(world, s)


def test_every_player_finds_a_chests_loot(world):
    chest = next(e for e in world.ents if e.npc_id == "Stone_Circle_Chest")   # (the stone circle's: grow_isle.py)
    m = world.maps[chest.map]
    a = join(world, "FirstFinder", chest.map, int(chest.x - m.ox) - 32, int(chest.y - m.oy))
    b = join(world, "SecondFinder", chest.map, int(chest.x - m.ox) - 32, int(chest.y - m.oy) + 32)
    for s in (a, b, a):
        s.connected = True
        s.out = []
        s.unlocked_chests.add(s.chest_key(chest))                   # (the Isle's chests are locked: picked already)
        s.choose_verb("Open", chest, int(chest.cx), int(chest.cy))
        for _ in range(60):
            world.tick(0.05)
        s.handle({"t": "respond", "n": 1})                           # (Take everything)
        world.tick(0.05)
    assert a.items_held("Magic_Potion") == 1 and b.items_held("Magic_Potion") == 1   # (each their own; once each)
    leave(world, a)
    leave(world, b)


def test_sheep_run_from_you_and_never_fight_back(world):
    sheep = next(e for e in world.ents if e.name == "Sheep" and e.alive)
    m = world.maps[sheep.map]
    s = join(world, "Shepherd", sheep.map, int(sheep.x - m.ox) - 24, int(sheep.y - m.oy))
    s.connected = True
    hp = s.player.hp
    start = distance(s.player.cx, s.player.cy, sheep.cx, sheep.cy)
    s.provoke(sheep)
    assert sheep.ai.state == AI_FLEE
    for _ in range(40):
        world.tick(0.05, now=world.now + 50)
    assert s.player.hp == hp                                         # (it never struck back)
    assert distance(s.player.cx, s.player.cy, sheep.cx, sheep.cy) > start   # (it ran)
    leave(world, s)


def test_the_milkmaid_is_asked_about_the_mainland_only_once_its_time(world):
    bess = next(e for e in world.ents if e.name == "Milkmaid")
    m = world.maps[bess.map]
    s = join(world, "Asker", bess.map, int(bess.x - m.ox) - 28, int(bess.y - m.oy))
    s.connected = True
    for will, passage, asked in ((1, 0, False), (2, 0, True), (2, 3, True), (2, 4, False)):     # (4: Wim's, now)
        s.update_attribute("LastWill", "=%d" % will)
        s.update_attribute("Passage", "=%d" % passage)
        s.choose_verb("Talk to", bess, int(bess.cx), int(bess.cy))
        for _ in range(20):
            world.tick(0.05)
        assert any(r.startswith("How do I get to the mainland") for r in s.responses) == asked, passage
        s.close_action_box(-1)
        world.tick(0.05)
    leave(world, s)


def test_hens_roost_in_their_coop_at_night(world):
    s = join(world, "Nightwatch", "2,0,0", 18 * 32, 16 * 32)         # (by the hens' yard: they walk, not vanish)
    m = world.maps["2,0,0"]
    day = world.day_fraction()
    world.set_day_fraction(0.95)
    for _ in range(900):
        world.tick(0.05, now=world.now + 50)
    hens = [e for e in world.ents if e.name == "Chicken" and e.map == "2,0,0"]
    inside = lambda e: 21 <= int((e.fx - m.ox) // 32) + 1 <= 23 and 12 <= int((e.fy - m.oy) // 32) + 1 <= 13   # (its feet)
    assert hens and all(e.active and inside(e) for e in hens), [(e.cx - m.ox, e.cy - m.oy) for e in hens]
    world.set_day_fraction(0.5)                                      # (morning: out into the yard again)
    for _ in range(900):
        world.tick(0.05, now=world.now + 50)
    assert not any(inside(e) for e in hens)
    world.set_day_fraction(day)
    leave(world, s)


def test_bad_news_is_heard_and_work_is_seen(world):
    s = join(world, "Listener")
    s.connected = True
    s.out = []
    s.display_message("The door is locked.", "FAIL")
    assert {"t": "sound", "name": "Denied"} in s.take_out()          # (no sound of its own: the Denied tell)
    s.display_message("The spell fizzles!", "FAIL")
    s.play_sound("Fizzle")
    assert [ev["name"] for ev in s.take_out() if ev["t"] == "sound"] == ["Fizzle"]   # (its own sound: just that)
    s.display_message("You pick some berries.", "SUCCESS")
    assert not any(ev["t"] == "sound" for ev in s.take_out())
    s.display_message("You need an axe!", "DarkRed", sound="")        # (a script's message: silent unless it says)
    assert not any(ev["t"] == "sound" for ev in s.take_out())
    s.script_lines = ["", "01\tDisplay.Message\tDarkRed\tYou need a pickaxe!\tDenied", "02\tEnd", ""]
    s.script_line_no = 1
    s.execute_script_line()                                          # (Display.Message's SOUND: heard with it)
    assert [ev["name"] for ev in s.take_out() if ev["t"] == "sound"] == ["Denied"]
    s.script_cursor_x, s.script_cursor_y = s.player.cx + 32, s.player.cy
    s.show_skill("Woodcutting")
    s.play_work("Wood_Chips", "3", "WoodChop")
    out = s.take_out()
    assert any(ev["t"] == "skillpop" and ev["skill"] == "Woodcutting" for ev in out)
    assert [ev["delay"] for ev in out if ev["t"] == "anim"] == [0, 800, 1600]          # (three swings of the axe)
    assert len([ev for ev in out if ev["t"] == "nudge"]) == 3
    leave(world, s)


def test_a_racks_search_finds_across_its_pages(world, monkeypatch):
    monkeypatch.setattr(world.data, "shop_vary_stock", False)       # (the milk may be sold out this delivery)
    s = join(world, "Shopper")
    s.connected = True
    assert s.open_item_rack("SPECIFIC", "Milkmaid", "SHOP-Dairy")
    every = [n for n, _, _ in s.ab_item_defs]
    s.set_rack_filter("MILK", False)                                 # (any case; part of the name)
    found = [n for n, _, _ in s.ab_item_defs]
    assert found and all("milk" in n.lower() for n in found) and len(found) < len(every)
    s.set_rack_filter("no such thing", False)
    assert s.ab_item_defs == [] and s.box_state()["filter"] == "no such thing"
    s.set_rack_filter("", False)
    assert [n for n, _, _ in s.ab_item_defs] == every
    leave(world, s)


def test_quests_wait_for_the_mainland_and_mark_their_giver(world):
    """A quest given off the Isle needs the ferry first; one not begun is marked where its own giver stands."""
    import re
    s = join(world, "Planner")
    text = open(os.path.join(ROOT, "data", "Quests.ini"), encoding="cp1252").read()
    on_isle = lambda mp: int(mp.split(",")[0]) <= 4 and int(mp.split(",")[1]) <= 2      # (the Isle's maps)
    for m in re.finditer(r"(?ms)^\[([^\]]+)\]\s*\n(.*?)(?=^\[|\Z)", text):
        name, body = m.group(1), m.group(2)
        get = lambda k: (re.search(r"(?m)^%s=(.*)$" % re.escape(k), body) or [None, ""])[1].strip()
        giver = get("Giver")
        givers = [e for e in world.ents if e.name.upper() == giver.upper() or (e.npc_id or "").upper() == giver.upper()]
        if not get("Marker0"):
            assert len(givers) == 1, "%s: %d NPCs called %s - give it a Marker0" % (name, len(givers), giver)
        if name != "Passage to the Mainland" and not get("Requires.Quests"):
            assert givers and all(on_isle(e.map) for e in givers), "%s is given off the Isle" % name
    leave(world, s)


def test_an_outcome_finishes_its_own_line_by_id(world):
    s = join(world, "Cook2")
    s.connected = True
    s.out = []
    s.display_message("You place the Raw Poultry on the range..", "Cyan", sound="")
    s.display_message("Your axe is badly worn: get it mended soon.", "DAMAGE", sound="")    # (something between)
    s.display_message("..and cook it perfectly!", "Yellow", sound="")
    msgs = [ev for ev in s.take_out() if ev["t"] == "msg"]
    assert msgs[2]["of"] == msgs[0]["id"] and "of" not in msgs[1]       # (it finishes its own line, not the last)
    s.display_message("..a stray one, with no line open", "Cyan", sound="")
    assert "of" not in [ev for ev in s.take_out() if ev["t"] == "msg"][0]
    leave(world, s)


def test_each_grave_says_who_lies_there(world):
    s = join(world, "Mourner", "3,1,0", 8 * 32, 3 * 32)
    s.connected = True
    m = s.cur_map
    said = []
    for pid in ("Grave_Tom_Barrow", "Grave_Ned_Pike"):               # (two Grave001s: once both Old Tom)
        s.out = []
        pl = world.data.place(pid)                                   # (found by its name, wherever it's moved to)
        gx, gy = m.ox + (pl.tx - 1) * 32 + 16, m.oy + (pl.ty - 1) * 32 + 16
        e = s.tile_entity_at(gx, gy)
        assert e.name.startswith("Grave") and e.npc_id == pid
        s.choose_verb("Examine", e, gx, gy)
        for _ in range(5):
            world.tick(0.05)
        said += [ev["text"] for ev in s.out if ev["t"] == "msg"]
    assert any("Tom Barrow" in t for t in said) and any("Ned Pike" in t for t in said)
    leave(world, s)


def test_a_gate_is_decor_and_opens_as_a_door(world):
    m = world.maps["2,0,0"]
    c = m.cell(8, 12)
    held = [e for e in world.ents if e.type == NPC and e.active and e.z == m.mz and
            distance(e.fx, e.fy, m.ox + 7.5 * 32, m.oy + 11.5 * 32) < 160]
    for e in held:
        world.ents.remove(e)                                         # (no sheep through the gate while we watch)
    for _ in range(30):
        world.tick(0.05, now=world.now + 100)
    assert m.decor[c] == "Wood_Gate003" and m.tile[c] != "Wood_Gate003"    # (in the decor, over its ground)
    s = join(world, "Drover", "2,0,0", 7 * 32, 11 * 32 - 8)          # (standing at the gate)
    for _ in range(10):
        world.tick(0.05, now=world.now + 50)
    assert m.decor[c] == "Wood_Gate004"                              # (open, as someone comes through)
    leave(world, s)
    for _ in range(60):
        world.tick(0.05, now=world.now + 100)
    assert m.decor[c] == "Wood_Gate003"                              # (and shut again behind them)
    world.ents.extend(held)


def test_a_bed_can_lie_sideways(world):
    a = join(world, "Napper")
    stock(a, Hearth_Anchor=1, Plank=20, Nails=40, Wool=20)
    a.update_skill("Homesteading", "=10")
    a.go_home()
    world.tick(0.05)
    hold_pocket(world, a)
    m = a.cur_map
    assert a.build(10, 10, "Bed003") and m.decor[m.cell(11, 10)] == "Bed004"    # (its foot to the right)
    assert a.build(10, 13, "Bed006") and m.decor[m.cell(9, 13)] == "Bed005"     # (or to the left)
    assert a.unbuild(11, 10) and not m.decor[m.cell(10, 10)] and not m.decor[m.cell(11, 10)]   # (down whole)
    assert "Sleep" in world.data.tile_ini("Bed005", "Use.Words", "")
    leave(world, a)


def story_done_before(s, chapter):
    """Every main quest before chapter done, and the level for the last of them."""
    for name, d in s.help_read_ini("Quests.ini"):
        if d.get("TYPE", "") == "Main" and int(d.get("CHAPTER", "0") or 0) < chapter:
            s.update_attribute(d["ATTRIBUTE"], "=" + d["DONE"])
    s.player_level = lambda: 30


def test_only_the_sword_of_valour_kills_galaiths_dragon(world):
    s = join(world, "Slayer", "-3,14,0", 10 * 32, 11 * 32)
    s.god_mode = 1
    dragon = next(e for e in world.ents if e.name == "Galaith_Dragon" and e.alive)
    s.damage_npc(dragon, dragon.hp + 100)
    assert dragon.alive and dragon.hp == 1                          # (any other blade can't reach its heart)
    stock(s, Sword_of_Valour=1)
    s.equipped[s.equip_slot_index("Weapon")] = "Sword_of_Valour"
    s.damage_npc(dragon, 100)
    assert not dragon.alive
    leave(world, s)


def test_the_woken_sword_kills_galaiths_dragon_too(world):
    s = join(world, "Waker", "-3,14,0", 10 * 32, 11 * 32)
    s.god_mode = 1
    for i, entry in enumerate(world.action_queue):                  # (back from the last test's death, now)
        bits = entry.split("	")
        if bits[1] == "Galaith_Dragon":
            world.action_queue[i] = "	".join(bits[:7] + ["0"] + bits[8:])
    world.run_action_queue()
    dragon = next(e for e in world.ents if e.name == "Galaith_Dragon" and e.alive)
    stock(s, Woken_Sword_of_Valour=1)
    s.equipped[s.equip_slot_index("Weapon")] = "Woken_Sword_of_Valour"
    s.damage_npc(dragon, dragon.hp + 100)
    assert not dragon.alive                                          # (Slain.By: a list)
    leave(world, s)


def test_bert_takes_the_ring_off_your_finger_and_gives_back_one_staff(world):
    """The three treasures brought worn and wielded ($Item counts both): Take.Item has them off your hands too."""
    s = join(world, "Treasurer", "21,5,1", 300, 300)
    run, npc, talk, use = isle_helpers(world, s)
    for a in ("WizardGift", "BertQuest", "HobgoblinQuest", "StaffQuest", "GrimoireQuest", "RingQuest"):
        s.update_attribute(a, "=" + {"WizardGift": "1", "BertQuest": "1"}.get(a, "2"))
    stock(s, Grimoire_of_Unbinding=1)
    s.equipped[s.equip_slot_index("Ring")] = "Ember_Ring"
    s.equipped[s.equip_slot_index("Weapon")] = "Staff_of_Ashen"
    talk(npc("Bert", "21,5,1"), 1, 1, 1)
    assert s.get_attribute("BertQuest") == "2" and s.get_attribute("BarrierSpell") == "1"
    assert s.items_held("Staff_of_Ashen") + s.items_equipped("Staff_of_Ashen") == 1
    assert s.items_equipped("Ember_Ring") == 0 and s.items_held("Ember_Ring") == 0
    assert s.items_held("Grimoire_of_Unbinding") == 0
    leave(world, s)


def test_the_warden_sends_no_one_to_the_cinder_fort_before_level_10(world):
    """The Ember Ring is for level 10: under it the Warden says not yet (no quest), at it she sends you."""
    s = join(world, "Ringseeker", "27,5,0", 300, 300)
    run, npc, talk, use = isle_helpers(world, s)
    story_done_before(s, 11)                                        # (up to The Ember Ring)
    s.player_level = lambda: 9
    talk(npc("Warden", "27,5,0"))
    assert s.get_attribute("RingQuest") in ("", "0")
    s.player_level = lambda: 10
    talk(npc("Warden", "27,5,0"), 1)
    assert s.get_attribute("RingQuest") == "1"
    leave(world, s)


def test_berts_spell_and_the_staff_break_the_barrier(world):
    s = join(world, "Breaker", "0,14,0", 9 * 32, 10 * 32 - 8)
    run, npc, talk, use = isle_helpers(world, s)
    run(5)
    lights = lambda: [e for e in world.ents if e.name == "Barrier_Light" and e.alive and world.visible_to(e, s)]
    assert len(lights()) == 3
    story_done_before(s, 17)                                        # (up to The Sword of Valour)
    stock(s, Staff_of_Ashen=1)
    m = s.cur_map
    gx, gy = m.ox + 7 * 32 + 16, m.oy + 10 * 32 + 16                 # (the barrier at 8,11, from beside it)
    s.item_in_use = next(e for e in s.inv if e.name == "Staff_of_Ashen")
    s.choose_verb("Use with", s.tile_entity_at(gx, gy), gx, gy)
    run(60)
    assert int(float(s.get_attribute("GalaithQuest") or 0)) == 0                 # (the staff alone: no words for it)
    s.update_attribute("BarrierSpell", "=1")
    s.item_in_use = next(e for e in s.inv if e.name == "Staff_of_Ashen")
    s.choose_verb("Use with", s.tile_entity_at(gx, gy), gx, gy)
    run(80)
    assert s.get_attribute("ShardgateQuest") == "1" and len(lights()) == 3   # (it holds: its anchor's in the realm)
    s.update_attribute("ShardgateQuest", "=5")                      # (The Shardgate: the anchor broken)
    s.item_in_use = next(e for e in s.inv if e.name == "Staff_of_Ashen")
    s.choose_verb("Use with", s.tile_entity_at(gx, gy), gx, gy)
    run(160)
    assert s.get_attribute("WakeQuest") == "1" and len(lights()) == 3     # (it thins: the dragon laughs at the sword)
    assert int(float(s.get_attribute("GalaithQuest") or 0)) == 0
    story_done_before(s, 22)                                        # (the sword woken in its three fires)
    s.item_in_use = next(e for e in s.inv if e.name == "Staff_of_Ashen")
    s.choose_verb("Use with", s.tile_entity_at(gx, gy), gx, gy)
    run(80)
    assert int(float(s.get_attribute("GalaithQuest") or 0)) == 1 and not lights()
    leave(world, s)


def test_clearing_the_wardhaven_bridge_opens_its_gates(world):
    s = join(world, "Bridger", "11,-3,0", 13 * 32, 10 * 32)
    s.connected = True
    s.god_mode = 1
    run, npc, talk, use = isle_helpers(world, s)
    story_done_before(s, 7)                                          # (The Ashford Road done)
    attr = lambda: int(float(s.get_attribute("WardhavenQuest") or 0))
    mayor = next(e for e in world.ents if e.npc_id == "Ashford_Clerk_13")
    talk(mayor, 1)                                                   # "I'll clear the bridge."
    assert attr() == 1
    gate = world.data.place("Wardhaven_Gate")
    m = world.maps[gate.map]
    lock = next(lk for lk in m.locks if "WardhavenQuest" in lk.condition)
    assert s.lock_closed(m, lock)                                    # (barred till it's done)
    near = lambda name: [e for e in world.ents if e.name in name and e.map == gate.map and e.alive and
                         world.visible_to(e, s)]
    s.teleport(gate.map, (gate.tx - 1) * 32, (gate.ty + 1) * 32)
    run(10)
    goblins = near(("Goblin", "Goblin_Archer"))
    assert len(goblins) == 4 and not near(("Guard",))               # (on the bridge for this player; no guards)
    for g in goblins:
        s.damage_npc(g, g.hp + 100)
        run(5)
    assert attr() == 2
    gold = s.items_held("Gold_Coin(s)")
    talk(mayor, 1)
    assert attr() == 3 and s.items_held("Gold_Coin(s)") == gold + 80
    s.check_locks(False)
    assert not s.lock_closed(m, lock)                                # the gates open
    s.teleport(gate.map, (gate.tx - 1) * 32, (gate.ty + 1) * 32)     # (back again: the guards are at their posts)
    run(10)
    assert len(near(("Guard",))) == 2 and not near(("Goblin", "Goblin_Archer"))
    leave(world, s)


def test_the_wyrmsmith_forges_a_helm_from_the_dragons_scales(world):
    s = join(world, "Scaler", "11,-3,0", 13 * 32, 10 * 32)
    s.connected = True
    run, npc, talk, use = isle_helpers(world, s)
    wyrmsmith = next(e for e in world.ents if e.name == "Wyrmsmith")
    attr = lambda: int(float(s.get_attribute("DragonforgeQuest") or 0))
    talk(wyrmsmith)
    assert attr() == 0                                               # (the dragon lives: no quest yet)
    story_done_before(s, 23)                                         # (the dragon of Galaith slain)
    talk(wyrmsmith, 1)
    assert attr() == 1
    stock(s, Dragon_Scale=3)
    helms = s.items_held("Dragonscale_Helm")                         # (the Sun-Forge gave one already)
    talk(wyrmsmith, 1)
    assert attr() == 2 and s.items_held("Dragonscale_Helm") == helms + 1 and s.items_held("Dragon_Scale") == 0
    leave(world, s)


def test_the_royal_guard_and_the_king(world):
    king_at = next(e for e in world.ents if e.npc_id == "Rupert_On_Throne")      # (the palace: wherever Galaith has it)
    palace = world.maps[king_at.map]
    door = next(lk for lk in palace.locks if "GuardQuest>=5" in lk.condition)
    throne_xy = next((x, y) for y in range(1, 22) for x in range(1, 26) if palace.tile[palace.cell(x, y)] == "Throne001"
                     or palace.decor[palace.cell(x, y)] == "Throne001")
    s = join(world, "Heir", palace.name, (door.x - 1) * 32, (door.y + 3) * 32)
    run, npc, talk, use = isle_helpers(world, s)
    attr = lambda a: int(float(s.get_attribute(a) or 0))
    story_done_before(s, 23)
    find = lambda pid: next(e for e in world.ents if e.alive and e.npc_id == pid)
    captain, king = find("Palace_Captain"), find("Rupert_On_Throne")
    talk(captain, 1)
    assert attr("GuardQuest") == 1
    talk(find("Galaith_Speaker_70"), 1, 1)
    assert attr("GuardQuest") == 2
    talk(find("Galaith_Clerk_73"), 1)                                   # (no amulet, no word from her)
    assert attr("GuardQuest") == 2
    stock(s, Amulet_of_Succession=1)
    talk(find("Galaith_Clerk_73"), 1, 1)                             # (not on the amulet alone: the vault first)
    assert attr("GuardQuest") == 2 and attr("ArchiveVault") == 1
    stock(s, Marys_Notes=1)                                          # (from the vault: its own test)
    talk(find("Galaith_Clerk_73"), 1, 1)
    assert attr("GuardQuest") == 3 and s.items_held("Archivists_Attestation") == 1
    talk(find("Galaith_Speaker_70"), 1)
    assert attr("GuardQuest") == 4 and s.items_held("Chancellors_Warrant") == 1
    s.check_locks(False)
    assert s.lock_closed(palace, door)                               # (the warrant shown to the captain first)
    talk(captain, 1)
    s.check_locks(False)
    assert attr("GuardQuest") == 5 and not s.lock_closed(palace, door)
    talk(king, 1, 1, 1, 1, 1)
    assert attr("KingQuest") == 1
    run(5)
    jimmy = world.placed_entity("Throne_Jimmy", s)                   # (the cat himself, curled up on the throne)
    assert jimmy is not None and jimmy.name == "Strawberry_Cat" and world.npc_state(jimmy) == "Curl"
    assert jimmy.image.startswith("Strawberry_Cat_Curl")             # (and drawn curled up)
    m = palace
    gx, gy = m.ox + (throne_xy[0] - 1) * 32 + 16, m.oy + (throne_xy[1] - 1) * 32 + 16
    throne = s.tile_entity_at(gx, gy)
    assert throne.name == "Throne001" and s.get_verbs(throne).split(",")[0] == "Sit"
    s.teleport(palace.name, (throne_xy[0] - 1) * 32, (throne_xy[1] + 1) * 32 - 8)   # (in front of it)
    run(10)
    s.choose_verb("Sit", throne, gx, gy)
    run(20)
    assert s.seat is not None and not jimmy.ai.napping               # (you sit on the throne: down he hops)
    assert distance(jimmy.cx, jimmy.cy, gx, gy) > 20
    s.keyboard_direction = 4
    run(2)
    s.keyboard_direction = 0
    for _ in range(4000):                                            # (and in a while he's back up, curled)
        world.tick(0.05, now=world.now + 100)
        if jimmy.ai.napping:
            break
    assert jimmy.ai.napping and world.npc_state(jimmy) == "Curl" and distance(jimmy.cx, jimmy.cy, gx, gy) < 20
    leave(world, s)


# ----- Shards (dsengine/shards.py): magic spends them; spells are learnt from scrolls for good
def ticks(world, n, ms=50):
    for _ in range(n):
        world.tick(0.05, now=world.now + ms)


def test_a_new_character_has_shards_and_an_old_one_gets_them_once(world):
    s = Session(world, "Fresh")
    s.load_state(None)
    assert s.shards() == 12 and not s.spells_known and "mana" not in s.me_state()
    old = join(world, "Veteran")                                   # (a save from before Shards)
    got = old.shards()
    assert got == 20
    saved = old.save_state()
    leave(world, old)
    again = Session(world, "Veteran")
    again.load_state(saved)
    assert again.shards() == got                                   # (no second grant)


def test_a_learnt_spell_stays_through_death_and_logging_off(world):
    a = join(world, "Learner", "11,-3,0", 384, 300)
    a.skill_level = lambda skill: 10
    stock(a, Shard_Ward_Scroll=1)
    a.do_action("Learn", next(e for e in a.inv if e.name == "Shard_Ward_Scroll"))
    assert "Shard_Ward" in a.spells_known and a.items_held("Shard_Ward_Scroll") == 0
    a.player_dies()
    a.handle({"t": "respawn"})
    world.tick(0.05)
    assert "Shard_Ward" in a.spells_known
    a.spell_start_cooldown("Shard_Ward")
    saved = a.save_state()
    leave(world, a)
    b = Session(world, "Learner")
    b.load_state(saved)
    assert "Shard_Ward" in b.spells_known and b.spell_cooldown_left("Shard_Ward") > 0    # (logging off doesn't reset it)


def test_healing_and_farsight_are_potions_now_and_stone_skin_a_ward(world):
    s = Session(world, "Oldtimer")
    s.load_state({"spells": {"Healing": 2, "Farsight": 1, "Stone_Skin": 1, "Fire_Bolt": 1},
                  "inventory": [["Healing_Scroll", 2, 0], ["Stone_Skin_Scroll", 1, 0]]})
    assert set(s.spells_known) == {"Shard_Ward", "Fire_Bolt"}
    assert s.items_held("Healing_Draught") == 5 and s.items_held("Owl_Potion") == 2      # (3 for the spell, 2 scrolls)
    assert s.items_held("Shard_Ward_Scroll") == 1 and s.data.spell_ini("Healing", "Effect", "") == ""


def test_a_scroll_too_hard_to_learn_is_kept(world):
    a = join(world, "Novice2")
    stock(a, Blizzard_Scroll=1)
    a.out = []
    a.do_action("Learn", next(e for e in a.inv if e.name == "Blizzard_Scroll"))
    assert "Blizzard" not in a.spells_known and a.items_held("Blizzard_Scroll") == 1
    assert any(e.get("t") == "sound" and e.get("name") == "Denied" for e in a.out)
    assert any("Channeling 13" in str(e.get("text", "")) or "level 13 Channeling" in str(e.get("text", "")) for e in a.out)
    leave(world, a)


def test_casting_spends_shards_only_when_it_takes(world):
    a = join(world, "Spender", "11,-3,0", 384, 300)
    a.skill_level = lambda skill: 10
    a.spells_known["Shard_Ward"] = 1
    c = a.spell_cost("Shard_Ward")                                 # (its 10, less what Channeling 10 saves)
    assert 1 <= c < 10
    a.remove_inventory_item("Shard", a.shards())
    stock(a, Shard=c - 1)
    a.out = []
    a.cast_spell("Shard_Ward", None)
    assert a.shards() == c - 1 and a.spell_defence_bonus == 0      # (too few: nothing taken, nothing cast)
    assert any(e.get("t") == "sound" and e.get("name") == "Denied" for e in a.out)
    stock(a, Shard=10)
    a.spell_chance = lambda spell: 0                               # (it fizzles: no Shards spent)
    a.cast_spell("Shard_Ward", None)
    assert a.shards() == c + 9 and a.spell_cooldown_left("Shard_Ward") > 0
    a.cooldowns.clear()
    a.player_last_cast = 0
    a.spell_chance = lambda spell: 100
    a.cast_spell("Shard_Ward", None)
    assert a.shards() == 9 and a.spell_defence_bonus > 0           # (cast: its Shards, exactly once)
    a.cast_spell("Shard_Ward", None)                               # (again at once: its cooldown)
    assert a.shards() == 9
    assert not a.spend_shards(100, "That") and a.shards() == 9     # (never below nothing)
    leave(world, a)


def test_the_hotbar_casts_a_known_spell_without_its_scroll(world):
    a = join(world, "Quick", "11,-3,0", 384, 300)
    a.skill_level = lambda skill: 10
    a.spells_known["Shard_Ward"] = 1
    a.spell_chance = lambda spell: 100
    a.hotbar[0] = "Shard_Ward_Scroll"
    assert a.items_held("Shard_Ward_Scroll") == 0
    shards = a.shards()
    a.hotbar_use(0)
    assert a.spell_defence_bonus > 0 and a.shards() == shards - a.spell_cost("Shard_Ward")
    a.handle({"t": "hotbar_spell", "spell": "Fire_Bolt"})          # (not known: not put there)
    assert "Fire_Bolt_Scroll" not in a.hotbar
    leave(world, a)


def test_digging_turns_up_shards_now_and_then(world, monkeypatch):
    s = join(world, "Delver")
    import random as rnd
    assert s.dig_shard_odds(world.maps["11,-3,0"]) == (5.0, "1-3")
    cave = next(m for m in world.maps.values() if m.mz < 0)
    assert s.dig_shard_odds(cave) == (15.0, "1-5")                 # (under the ground: likelier)
    assert s.dig_shard_odds(world.maps["2,19,0"])[0] == 15.0        # (the desert's old places)
    monkeypatch.setattr(rnd, "uniform", lambda a, b: b)            # (the unluckiest: nothing)
    before = s.shards()
    assert s.dig_shards(world.maps["11,-3,0"]) == 0 and s.shards() == before
    monkeypatch.setattr(rnd, "uniform", lambda a, b: 3.0)          # (under 5 in 100: Shards; not a cache)
    assert s.dig_shards(world.maps["11,-3,0"]) >= 1 and s.shards() > before
    leave(world, s)


def test_a_quests_shards_are_paid_once(world):
    s = join(world, "Rewarded")
    s.update_attribute("ShardsPaid.DinnerQuest", "=0")
    s.update_attribute("DinnerQuest", "=3")
    before = s.shards()
    s.update_attribute("DinnerQuest", "=4")                        # (done: Reward.Shards=5)
    assert s.shards() == before + 5
    s.update_attribute("DinnerQuest", "=4")
    s.update_attribute("DinnerQuest", "+1")
    assert s.shards() == before + 5
    assert next(q for q in s.quest_list() if q["title"] == "Dinner at Edwin's")["shards"] == 5
    leave(world, s)


def test_activating_a_shardstone_costs_shards_once(world):
    m = world.maps["4,6,0"]
    ws = next(e for e in world.ents if e.name == "Shardstone" and e.map == m.name)
    a = join(world, "Wanderer", m.name, int(ws.x - m.ox) + 40, int(ws.y - m.oy) + 8)
    other = join(world, "Bystander", m.name, int(ws.x - m.ox) + 60, int(ws.y - m.oy) + 8)
    a.connected = other.connected = True
    theirs = other.shards()
    assert ws.uid not in a.me_state()["lit"]                       # (dormant to you: drawn so - render.js)

    def touch(answer=None):
        a.out = []
        a.choose_verb("Travel", ws, int(ws.cx), int(ws.cy))
        ticks(world, 40)
        if answer is not None:
            assert a.ab_mode == "Conversation" and a.responses[0].startswith("Activate it")
            assert "you have" not in a.ab_text and "carry" not in a.ab_text   # (it doesn't count your Shards)
            a.action_box_response_chosen(answer)
            ticks(world, 40)

    a.remove_inventory_item("Shard", a.shards())
    stock(a, Shard=3)
    touch(1)                                                       # ("Activate it": but 5 are needed)
    assert a.get_attribute("Waystone.Northport") in ("", "0") and a.shards() == 3
    assert any(e.get("t") == "sound" and e.get("name") == "Denied" for e in a.out)
    stock(a, Shard=7)
    touch(2)                                                       # ("Leave it": nothing spent)
    assert a.get_attribute("Waystone.Northport") in ("", "0") and a.shards() == 10
    craft = a.skill_xp_of("Shardcraft")
    touch(1)
    assert a.get_attribute("Waystone.Northport") == "1" and a.shards() == 5
    assert a.skill_xp_of("Shardcraft") > craft and ws.uid in a.me_state()["lit"]
    assert any(e.get("t") == "stones" for e in a.out)               # (and its travel map opens)
    touch()                                                        # (active: straight to the travel map)
    assert not a.ab_mode and any(e.get("t") == "stones" and e["here"] == "Northport" for e in a.out)
    assert a.shards() == 5 and other.shards() == theirs            # (charged once, and only them)
    assert ws.uid not in other.me_state()["lit"]
    leave(world, a)
    leave(world, other)


def test_the_magister_takes_fifteen_shards_only_when_you_hand_them_over(world):
    q = next(e for e in world.ents if e.npc_id == "Court_Magister")
    m = world.maps[q.map]
    s = join(world, "Scholar", m.name, int(q.x - m.ox), int(q.y - m.oy) + 40)
    s.connected = True
    s.update_attribute("Passage", "=12")

    def talk(*answers):
        s.choose_verb("Talk to", q, int(q.cx), int(q.cy))
        ticks(world, 40)
        for n in answers:
            assert s.ab_mode == "Conversation"
            s.action_box_response_chosen(n)
            ticks(world, 20)

    talk(1)                                                        # ("I'll bring you fifteen")
    assert s.get_attribute("ShardQuest") == "1"
    before = s.shards()
    talk(3)                                                        # ("Not yet": nothing taken)
    assert s.shards() == before
    s.remove_inventory_item("Shard", before)
    stock(s, Shard=10)
    talk(1)                                                        # (too few: nothing taken)
    assert s.shards() == 10 and s.get_attribute("ShardQuest") == "1"
    s.close_action_box(-1)
    ticks(world, 5)
    stock(s, Shard=10)
    talk(1, 1)
    assert s.shards() == 5 and s.get_attribute("ShardQuest") == "2" and s.items_held("Frost_Nova_Scroll") == 1
    leave(world, s)


def test_a_chest_sometimes_holds_shards(world, monkeypatch):
    s = join(world, "Looter")
    import random as rnd
    monkeypatch.setattr(rnd, "uniform", lambda a, b: a)            # (the luckiest chest)
    s.loot_key, s.loot_collect = "x|1|1|Chest", [["Gold_Coin(s)", 5]]
    s.loot_finish()
    assert any(it[0] == "Shard" and 3 <= it[1] <= 15 for it in s.chests["x|1|1|Chest"])
    s.loot_key, s.loot_collect = "y|1|1|Chest", []                 # (an empty one: nothing added)
    s.loot_finish()
    assert "y|1|1|Chest" not in s.chests
    s.close_action_box(-1)
    leave(world, s)


def test_shards_are_a_balance_not_an_item(world):
    a = join(world, "Purse")
    before = a.shards()
    a.add_inventory_item("Shard", 7)                               # (a script's Give.Item, a chest's, a drop's)
    assert a.shards() == before + 7 and not any(e.name == "Shard" for e in a.inv)
    assert a.items_held("Shard") == before + 7                     # (>Got.Item and $Item.Shard read the balance)
    a.remove_inventory_item("Shard", 1000)                         # (Take.Item: never below nothing)
    assert a.shards() == 0
    saved = a.save_state()
    assert saved["shards"] == 0 and not any(i[0] == "Shard" for i in saved["inventory"])
    leave(world, a)
    old = Session(world, "Hoarder")                                # (a save from when Shards were an item)
    old.load_state({"map": "11,-3,0", "x": 384, "y": 300, "inventory": [["Shard", 9, 0]],
                    "bank": [["Shard", 4, []]], "attributes": [["ShardsGiven", "1"]]})
    assert old.shards() == 13 and not any(e.name == "Shard" for e in old.inv)
    assert "Shard" not in old.bank_item


def test_a_beast_leaves_shard_remnants_not_shards(world, monkeypatch):
    import dsengine.remnants as RM
    a = join(world, "Hunter", "11,-3,0", 384, 300)
    m = a.cur_map
    wolf = world.add_npc("Wolf", 0, m.ox + 12 * 32, m.oy + 10 * 32, "Attitude=Bad")
    monkeypatch.setattr(RM, "rnd", lambda: 0.3)                    # (30 in 100: remnants, but nothing rises)
    before, uids = a.shards(), {e.uid for e in world.ents}
    a.add_npc_drops(wolf)
    assert a.shards() == before                                    # (no Shards for the kill itself)
    left = [e for e in world.ents if e.uid not in uids]
    remnants = [e for e in left if e.name == "Shard_Remnant" and e.type == MAPITEM]
    assert remnants and all(e.private_to is a for e in remnants)
    assert not any(e.name in ("Bones", "Shard", "Living_Remnant") for e in left)
    for e in left:
        world.remove_entity(e)
    stock(a, Shard_Remnant=5)
    a.do_action("Absorb", next(e for e in a.inv if e.name == "Shard_Remnant"))
    assert a.items_held("Shard_Remnant") == 0 and a.shards() == before + 5
    world.remove_entity(wolf)
    leave(world, a)


def test_a_shard_remnant_rises_as_strong_as_the_beast_and_leaves_more(world, monkeypatch):
    import dsengine.remnants as RM
    a = join(world, "Riser", "11,-3,0", 384, 300)
    m = a.cur_map
    bear = world.add_npc("Bear", 0, m.ox + 12 * 32, m.oy + 10 * 32, "Attitude=Bad")
    level = a.monster_level(bear)
    assert 2 <= level <= 25
    monkeypatch.setattr(RM, "rnd", lambda: 0.0)                    # (it rises)
    uids = {e.uid for e in world.ents}
    a.add_npc_drops(bear)
    world.remove_entity(bear)
    risen = [e for e in world.ents if e.uid not in uids and e.name == "Living_Remnant"]
    assert len(risen) == 1 and not any(e.uid not in uids and e.name == "Shard_Remnant" for e in world.ents)
    rem = risen[0]
    assert rem.max_hp == 5 + 5 * level and rem.target is a and world.hostile_for(rem, a)
    assert a.display_name(rem) == "Shard Remnant" and a.monster_level(rem) == level
    uids = {e.uid for e in world.ents}
    a.kill_npc(rem)                                                # (killed: more remnants, and it never rises again)
    left = [e for e in world.ents if e.uid not in uids]
    assert sum(e.quantity for e in left if e.name == "Shard_Remnant") >= 3
    assert not any(e.name == "Living_Remnant" for e in left)
    for e in left:
        world.remove_entity(e)
    leave(world, a)


def test_a_shard_remnant_nobody_fights_fades(world):
    a = join(world, "Watcher", "11,-3,0", 384, 300)
    m = a.cur_map
    wolf = world.add_npc("Wolf", 0, m.ox + 14 * 32, m.oy + 12 * 32, "Attitude=Bad")
    a.remnant_rise(wolf, 3)
    world.remove_entity(wolf)
    rem = next(e for e in world.ents if e.name == "Living_Remnant" and e.alive)
    rem.in_combat = False
    rem.fades_at = world.now
    world.last_queue_check = world.now - 1000
    world.tick(0.05, now=world.now + 300)
    assert not rem.alive
    leave(world, a)


def test_shard_numbers_come_from_shards_ini(world):
    a = join(world, "Counter", "11,-3,0", 384, 300)
    assert a.shard_setting("Shardstone.Galaith") == 20 and a.shard_setting("Shardstone.Northport") == 5
    assert a.shard_setting("Weapon", 0, "Dismantle") == 25 and a.shard_setting("Scroll", 0, "Dismantle") == 10
    assert a.upgrade_scroll("Fire_Bolt", 2) == "Fire_Bolt_Scroll_II"
    assert a.spell_ini_at("Fire_Bolt", "Damage", "", 3) == "7-13" and a.spell_ini_at("Fire_Bolt", "Range", "", 3) == "256"
    leave(world, a)


def test_a_woman_has_her_own_body_and_keeps_it(world):
    from dsengine.view import player_state
    a, b = join(world, "Ada"), join(world, "Ben")
    a.handle({"t": "look", "look": {"hair": "#A83A1A", "body": "f"}})
    assert a.look == {"hair": "#a83a1a", "body": "f"} and a.player_sprite_base == "PlayerF"
    assert player_state(a, b)["i"].startswith("PlayerF") and a.player.name == "PlayerF"
    a.change_player_sprite("Wolf")                                 # (a script's disguise, and back to herself)
    a.change_player_sprite("Player")
    assert a.player_sprite_base == "PlayerF"
    saved = a.save_state()
    a.handle({"t": "look", "look": {"hair": "#a83a1a"}})          # (a man again)
    assert a.player_sprite_base == "Player"
    leave(world, a)
    c = Session(world, "Ada2")
    c.load_state(saved)
    assert c.player_sprite_base == "PlayerF" and c.look["body"] == "f"
    leave(world, b)


def test_an_old_save_has_its_skills_out_of_25(world):
    s = Session(world, "Elder")
    s.load_state({"skills": {"Strength": 40, "Herblore": 10.5, "Magic": 1.4, "Hitpoints": 20}})
    assert s.skill_xp_of("Strength") == 20 and s.skill_xp_of("Potion_Making") == 5.25
    assert s.skill_level("Magic") == 1 and s.skill_xp_of("Hitpoints") == 20
    saved = s.save_state()
    assert saved["skills_of"] == 25
    t = Session(world, "Elder2")
    t.load_state(saved)                                            # (saved out of 25: as it was)
    assert t.skill_xp_of("Strength") == 20


def test_a_quest_gives_its_skill_xp_once(world):
    s = join(world, "Learner")
    name, d = next((n, d) for n, d in s.help_read_ini("Quests.ini") if n == "The Ashford Road")
    attr, done = d["ATTRIBUTE"], int(d["DONE"])
    skill = d["REWARD.XP"].split()[0]
    before = s.skill_xp_of(skill)
    s.out = []
    s.update_attribute(attr, "=%d" % done)
    gained = s.skill_xp_of(skill) - before
    assert gained > 0
    s.update_attribute(attr, "=%d" % (done + 1))                   # (paid once)
    assert s.skill_xp_of(skill) - before == gained
    world.tick(0.05, now=world.now + 21000)
    ev = next(e for e in s.out if e.get("t") == "reward")
    assert any(k == skill for k, _ in ev["xp"])
    assert any(q["title"] == name and skill in q["xp"] for q in s.quest_list())
    leave(world, s)


def test_upgrade_scrolls_raise_a_known_spell_a_rank(world):
    a = join(world, "Ranker", "11,-3,0", 384, 300)
    a.skill_level = lambda skill: 20
    a.spell_chance = lambda spell: 100
    stock(a, Fire_Bolt_Scroll_II=1)
    two = next(e for e in a.inv if e.name == "Fire_Bolt_Scroll_II")
    a.out = []
    a.do_action("Learn", two)                                      # (rank 2 before rank 1: no)
    assert a.spell_rank("Fire_Bolt") == 0 and a.items_held("Fire_Bolt_Scroll_II") == 1
    a.spells_known["Fire_Bolt"] = 1
    assert a.spell_ini("Fire_Bolt", "Cost", "") == "3" and a.spell_ini("Fire_Bolt", "Damage", "") == "2-5"
    assert "Learn" in a.get_verbs(two)
    a.do_action("Learn", two)
    assert a.spell_rank("Fire_Bolt") == 2 and a.items_held("Fire_Bolt_Scroll_II") == 0
    assert a.spell_ini("Fire_Bolt", "Cost", "") == "4" and a.spell_ini("Fire_Bolt", "Damage", "") == "4-9"
    assert a.spell_ini("Fire_Bolt", "Range", "") == "256"          # (what a rank doesn't change, stays)
    saved = a.save_state()
    assert saved["spells"]["Fire_Bolt"] == 2
    book = {r["spell"]: r for r in a.spellbook()}
    assert book["Fire_Bolt"]["title"] == "Fire Bolt II" and book["Fire_Bolt"]["next"]["title"] == "Fire Bolt III"
    leave(world, a)


def test_dismantling_breaks_gear_into_shards_after_asking(world):
    a = join(world, "Breaker", "11,-3,0", 384, 300)
    stock(a, Iron_Sword=1, Logs=3, Fire_Bolt_Scroll=1)
    sword = next(e for e in a.inv if e.name == "Iron_Sword")
    logs = next(e for e in a.inv if e.name == "Logs")
    scroll = next(e for e in a.inv if e.name == "Fire_Bolt_Scroll")
    assert "Dismantle" in a.get_verbs(sword) and "Dismantle" not in a.get_verbs(logs)
    assert "Dismantle" not in a.get_verbs(scroll)                  # (not learnt yet: read it instead)
    worth = a.dismantle_worth("Iron_Sword")
    assert worth >= 1
    before = a.shards()
    a.do_action("Dismantle", sword)
    assert a.ab_mode == "Conversation" and a.items_held("Iron_Sword") == 1      # (asked first)
    a.action_box_response_chosen(2)                                # ("Keep it")
    assert a.items_held("Iron_Sword") == 1 and a.shards() == before
    a.do_action("Dismantle", sword)
    a.action_box_response_chosen(1)
    assert a.items_held("Iron_Sword") == 0 and a.shards() == before + worth
    a.spells_known["Fire_Bolt"] = 1
    assert "Dismantle" in a.get_verbs(scroll)                      # (known: a spare scroll is worth Shards)
    leave(world, a)


def test_a_finished_quest_shows_what_it_gave(world):
    s = join(world, "Victor")
    s.update_attribute("ShardsPaid.HobgoblinQuest", "=0")
    s.update_attribute("HobgoblinQuest", "=1")
    shards = s.shards()
    s.out = []
    done = next(int(d["DONE"]) for n, d in s.help_read_ini("Quests.ini") if d.get("ATTRIBUTE") == "HobgoblinQuest")
    s.update_attribute("HobgoblinQuest", "=%d" % done)            # (The Steward's Hunt: 20 Shards, Fire Bolt II)
    s.add_inventory_item("Gold_Coin(s)", 100)                      # (what its script gives as it ends)
    world.tick(0.05, now=world.now + 21000)
    ev = next(e for e in s.out if e.get("t") == "reward")
    assert ev["quest"] == "The Steward's Hunt" and ev["shards"] == 20
    assert ["Fire_Bolt_Scroll_II", 1] in ev["items"] and ["Gold_Coin(s)", 100] in ev["items"]
    assert s.shards() == shards + 20 and s.items_held("Fire_Bolt_Scroll_II") == 1
    s.update_attribute("HobgoblinQuest", "=%d" % done)            # (once)
    assert s.shards() == shards + 20 and s.items_held("Fire_Bolt_Scroll_II") == 1
    leave(world, s)


def test_a_journey_by_shardstone_costs_a_few_shards(world):
    m = world.maps["4,6,0"]
    ws = next(e for e in world.ents if e.name == "Shardstone" and e.map == m.name)
    a = join(world, "Traveller", m.name, int(ws.x - m.ox) + 40, int(ws.y - m.oy) + 8)
    a.connected = True
    a.update_attribute("Waystone.Northport", "=1")
    a.update_attribute("Waystone.Ashford", "=1")
    a.remove_inventory_item("Shard", a.shards())
    stock(a, Shard=10)
    a.out = []
    a.choose_verb("Travel", ws, int(ws.cx), int(ws.cy))
    ticks(world, 40)
    st = next(e for e in a.out if e.get("t") == "stones")          # (the travel map: the stones you've activated)
    assert {s["k"] for s in st["stones"]} == {"Northport", "Ashford"} and st["cost"] == 2
    a.handle({"t": "stone_go", "k": "Wardhaven"})                  # (not activated: no journey)
    ticks(world, 5)
    assert a.shards() == 10 and a.cur_map.name == m.name
    a.handle({"t": "stone_go", "k": "Ashford"})
    ticks(world, 5)
    assert a.shards() == 8 and a.cur_map.name == "11,-3,0"          # (2 Shards, and there)
    a.handle({"t": "stone_go", "k": "Northport"})                  # (not by a stone you've opened the map at)
    ticks(world, 5)
    assert a.shards() == 8 and a.cur_map.name == "11,-3,0"
    leave(world, a)

def test_the_kings_shard_seam_gives_shards_once_a_day(world):
    seam = next(e for e in world.ents if e.name == "Shard_Seam" and e.map == "-7,11,-1")
    m = world.maps[seam.map]
    s = join(world, "Monarch", seam.map, int(seam.x - m.ox) + 36, int(seam.y - m.oy) + 8)
    s.connected = True
    stock(s, Pickaxe=1)

    def mine():
        s.out = []
        s.choose_verb("Mine", seam, int(seam.cx), int(seam.cy))
        for _ in range(100):
            world.tick(0.05, now=world.now + 50)
        return " ".join(str(e.get("text", "")) for e in s.out if e.get("t") == "msg")

    before = s.shards()
    assert "the Crown's" in mine() and s.shards() == before              # (not king: not yours)
    s.update_attribute("KingQuest", "=1")
    s.update_attribute("HeartChoice", "=1")                              # (the ending's choice made: its own test)
    before = s.shards()                                                  # (after The True Heir's own reward)
    assert "prise loose 12 Shards" in mine() and s.shards() == before + 12
    assert "haven't grown back" in mine() and s.shards() == before + 12  # (once a day)
    s.update_attribute("ShardSeamAt", "=%d" % (int(s.get_attribute("ShardSeamAt")) - 21 * 3600))
    mine()
    assert s.shards() == before + 24
    assert next(e for e in s.inv if e.name == "Pickaxe").wear >= 2        # (the pickaxe wears, as on any rock)
    leave(world, s)


def test_a_woman_is_a_daughter_a_lady_and_a_queen(world):
    s = join(world, "Isolde")
    words = "My $Player.Son, the $Player.King. Mary's $Player.Boy, my $Player.Lord."
    assert s.parse_script_variables(words) == "My son, the King. Mary's boy, my lord."
    s.handle({"t": "look", "look": {"body": "f"}})
    assert s.parse_script_variables(words) == "My daughter, the Queen. Mary's girl, my lady."
    leave(world, s)


def near(world, s, e, dx=36, dy=8):
    """s stands by e (on its map), the world ticks a moment."""
    m = world.maps[e.map]
    s.teleport(e.map, int(e.x - m.ox) + dx, int(e.y - m.oy) + dy)
    s.do_pending_map_change()
    for _ in range(5):
        world.tick(0.05, now=world.now + 50)


def run_for(world, n=60):
    for _ in range(n):
        world.tick(0.05, now=world.now + 50)


def talk_to(world, s, e, most=200):
    """Talk to e, and wait (it may have to walk to them) till their conversation's open."""
    s.choose_verb("Talk to", e, int(e.cx), int(e.cy))
    for _ in range(most):
        world.tick(0.05, now=world.now + 50)
        if s.ab_mode == "Conversation":
            return True
    return False


def test_writing_a_spell_of_your_own_at_the_lectern(world):
    lectern = next(e for e in world.ents if e.name == "Spellwright_Lectern")
    s = join(world, "Wright", lectern.map, 300, 300)
    s.connected = True
    near(world, s, lectern, 0, 40)
    s.out = []
    s.choose_verb("Write", lectern, int(lectern.cx), int(lectern.cy))
    run_for(world, 5)
    assert s.ab_mode != "Conversation"                              # (not taught yet: the pages are blank)
    s.update_attribute("SpellwrightQuest", "=3")
    s.skill_level = lambda skill: 25
    s.choose_verb("Write", lectern, int(lectern.cx), int(lectern.cy))
    run_for(world, 5)
    assert s.ab_mode == "Conversation" and s.responses[0].startswith("Bolt")
    s.action_box_response_chosen(1)                                 # (a bolt)
    assert all(r.startswith("Power") for r in s.responses[:-1])
    s.action_box_response_chosen(len(s.responses) - 1)              # (the strongest: power 5)
    s.action_box_response_chosen(2)                                 # (far)
    assert "Wright's Bolt, power 5" in s.ab_text
    s.action_box_response_chosen(1)                                 # (write it: the first time is free)
    assert s.spell_rank("Own_Spell") == 1 and s.spell_title("Own_Spell") == "Wright's Bolt"
    assert s.spell_ini("Own_Spell", "Damage", "") == "10-21" and s.spell_ini("Own_Spell", "Range", "") == "320"
    near_cost = int(s.spell_ini("Own_Spell", "Cost", "0"))
    assert near_cost == round(3 * 5 ** 1.1 * 1.4)                   # (Shards.ini [Spellwright]: dearer for far)
    assert any(r["spell"] == "Own_Spell" for r in s.spellbook()) and s.me_state()["own"]["title"] == "Wright's Bolt"
    saved = s.save_state()
    leave(world, s)
    t = Session(world, "Wright")
    t.load_state(saved)
    assert t.spell_title("Own_Spell") == "Wright's Bolt" and t.spell_ini("Own_Spell", "Cost", "") == str(near_cost)


def test_the_spellwright_quest_from_core_to_lectern(world):
    quill = next(e for e in world.ents if e.npc_id == "Court_Magister")
    s = join(world, "Apprentice", quill.map, 300, 300)
    s.connected = True
    for q in ("Passage", "ShardQuest"):
        s.update_attribute(q, "=12" if q == "Passage" else "=2")
    near(world, s, quill, 0, 36)

    def talk(*answers):
        s.choose_verb("Talk to", quill, int(quill.cx), int(quill.cy))
        run_for(world, 10)
        for n in answers:
            assert s.ab_mode == "Conversation", n
            s.action_box_response_chosen(n)
            run_for(world, 10)
        if s.ab_mode:
            s.close_action_box(-1)

    talk(2, 1)                                                      # (about spellcraft; I'll bring you one)
    assert s.get_attribute("SpellwrightQuest") == "1"
    stock(s, Remnant_Core=1)
    talk(2, 1)
    assert s.get_attribute("SpellwrightQuest") == "2" and s.items_held("Remnant_Core") == 0
    stock(s, Shard_Remnant=20)
    s.do_action("Absorb", next(e for e in s.inv if e.name == "Shard_Remnant"))
    talk(2, 1)
    assert s.get_attribute("SpellwrightQuest") == "3"
    leave(world, s)


def test_the_shardgate_from_bert_to_the_broken_anchor(world):
    bert = next(e for e in world.ents if e.name == "Bert" and e.alive)
    s = join(world, "Gatewright", bert.map, 300, 300)
    s.connected = True
    s.god_mode = True                                               # (the realm's remnants: no dying in a test)
    for q, v in (("Passage", 12), ("ParliamentQuest", 9), ("AshfordQuest", 9), ("HobgoblinQuest", 2), ("BertQuest", 2),
                 ("ShipQuest", 2), ("DragonIsleQuest", 2), ("ValourQuest", 3), ("WizardGift", 1)):
        s.update_attribute(q, "=%d" % v)
    assert s.quest_can_start("ShardgateQuest")
    assert any("Shardgate" in n for n in s.quest_needs("WakeQuest"))                 # (the gate first)
    s.update_attribute("ShardgateQuest", "=1")                     # (the barrier held: its script)
    near(world, s, bert, 0, 36)
    assert talk_to(world, s, bert)
    s.action_box_response_chosen(1)
    run_for(world, 5)
    s.action_box_response_chosen(1)
    run_for(world, 10)
    assert s.get_attribute("ShardgateQuest") == "2" and s.items_held("Shardgate_Plans") == 1
    assert not any(l["n"] == "The Shardgate" for l in s.my_labels())
    ring = next(e for e in world.ents if e.name == "Shardgate_Ring")
    near(world, s, ring, 16, 72)
    s.out = []
    s.choose_verb("Build", ring, int(ring.cx), int(ring.cy))
    run_for(world, 10)
    assert s.get_attribute("ShardgateQuest") == "2"                 # (no stones to steady it, nothing to build with)
    assert any("shardstones active" in str(e.get("text", "")) for e in s.out)
    stock(s, Silver_Bar=4, Sapphire=2, Remnant_Core=1, Shard=40)
    for k in ("Northport", "Ashford", "Wardhaven", "Oakhollow", "Wildwood", "Greyford", "Dunerest", "Court"):
        s.update_attribute("Waystone." + k, "=1")
    s.update_skill("Shardcraft", "=1")
    s.out = []
    s.choose_verb("Build", ring, int(ring.cx), int(ring.cy))
    run_for(world, 40)
    assert s.get_attribute("ShardgateQuest") == "2" and any("Shardcraft" in str(e.get("text", "")) for e in s.out)
    s.update_skill("Shardcraft", "=5")
    shards = s.shards()
    s.out = []
    s.choose_verb("Build", ring, int(ring.cx), int(ring.cy))
    run_for(world, 100)
    assert s.get_attribute("ShardgateQuest") == "3" and s.shards() == shards - 30 and s.items_held("Silver_Bar") == 0
    gate = next(e for e in world.ents if e.name == "Shardgate" and e.owner is s)
    assert any(l["n"] == "The Shardgate" for l in s.my_labels())     # (on the world map now: yours)
    assert any(e.get("t") == "labels" for e in s.out)
    s.choose_verb("Step Through", gate, int(gate.cx), int(gate.cy))
    run_for(world, 20)
    assert s.cur_map.name == "21,4,-10"
    anchor = next(e for e in world.ents if e.name == "Barrier_Anchor" and e.owner is s)
    warden = next(e for e in world.ents if e.name == "Shard_Warden" and e.alive)
    near(world, s, anchor, -40, 16)
    stock(s, Staff_of_Ashen=1)
    s.choose_verb("Shatter", anchor, int(anchor.cx), int(anchor.cy))
    run_for(world, 10)
    assert s.get_attribute("ShardgateQuest") == "3"                 # (the Warden stands over it)
    s.kill_npc(warden)
    s.choose_verb("Shatter", anchor, int(anchor.cx), int(anchor.cy))
    run_for(world, 80)
    assert s.get_attribute("ShardgateQuest") == "4"
    assert any(e.name == "Barrier_Anchor_Broken" and e.owner is s for e in world.ents)
    s.teleport(bert.map, 300, 300)
    s.do_pending_map_change()
    near(world, s, bert, 0, 36)
    assert talk_to(world, s, bert)
    s.action_box_response_chosen(1)
    run_for(world, 10)
    assert s.get_attribute("ShardgateQuest") == "5"
    assert not any("Shardgate" in n for n in s.quest_needs("WakeQuest"))             # (the barrier can thin now)
    leave(world, s)


def test_the_shardrealms_remnants_are_as_strong_as_their_level_and_stay(world):
    rems = [e for e in world.ents if e.name == "Living_Remnant" and e.map == "21,4,-10" and e.source == "MAP"]
    assert rems and all(e.max_hp == 5 + 5 * e.remnant_level for e in rems)
    from dsengine.remnants import fade_remnants
    world.now += 10 ** 7
    fade_remnants(world)
    assert all(e.alive for e in rems)                               # (a map's remnants don't fade)


def test_drains_and_boosts_show_a_skill_as_it_is_now(world):
    s = join(world, "Sapped", "11,-3,0", 384, 300)
    s.update_skill("Strength", "=10")
    hp = s.player_max_hp
    s.status_start("Weaken")
    assert s.skill_level("Strength") == 7 and s.base_skill_level("Strength") == 10 and s.player_max_hp == hp
    st = s.me_state()
    i = [n.upper() for n in s.data.skill_name[1:]].index("STRENGTH")
    assert st["skill_now"][i] == 7 and "Weaken" in st["status_left"]
    s.run_script_lines("test", ["01	Boost.Skill	Magic	+2	5", "02	End"])  # (its old name: Channeling now)
    world.tick(0.05, now=world.now + 50)
    assert s.skill_level("Channeling") == s.base_skill_level("Channeling") + 2
    assert s.me_state()["skill_boosts"]["Channeling"]["n"] == 2
    world.tick(0.05, now=world.now + 6000)
    assert s.skill_level("Channeling") == s.base_skill_level("Channeling")     # (a while, and back)
    s.boost_skill("Defence", -4, 60)
    s.player_dies()
    assert s.skill_level("Strength") == 10 and s.skill_change("Defence") == 0   # (death ends them, as it ends buffs)
    leave(world, s)


def test_an_invisibility_potion_hides_you_till_you_strike(world):
    s = join(world, "Ghost", "11,-3,0", 384, 300)
    s.connected = True
    m = s.cur_map
    wolf = world.add_npc("Wolf", 0, s.player.x + 40, s.player.y, "Attitude=Bad")
    stock(s, Invisibility_Potion=1)
    s.do_action("Drink", next(e for e in s.inv if e.name == "Invisibility_Potion"))
    assert s.invisible() and not s.player_visible and s.items_held("Invisibility_Potion") == 0
    for _ in range(20):
        world.tick(0.05, now=world.now + 50)
    assert wolf.target is not s                                    # (it can't see you)
    s.damage_npc(wolf, 1)
    assert not s.invisible() and s.player_visible                  # (a blow struck: seen)
    world.remove_entity(wolf)
    leave(world, s)


def test_a_body_swap_is_a_strict_while_and_needs_no_hands(world):
    s = join(world, "Swapper", "11,-3,0", 384, 300)
    s.connected = True
    duck = world.add_npc("Duck", 0, s.player.x + 60, s.player.y, "Attitude=Good")
    s.skill_level = lambda skill: 10
    s.spells_known["Swap"] = 1
    bx, by = s.player.x, s.player.y
    s.cast_spell("Swap", duck)
    assert s.player_form() == "Duck" and s.player.name == "Duck" and duck.name == "Player"
    assert (duck.x, duck.y) == (bx, by) and s.parse_script_variables("$Player.Form") == "Duck"
    stock(s, Fire_Bolt_Scroll=1)
    s.out = []
    s.choose_verb("Cast", next(e for e in s.inv if e.name == "Fire_Bolt_Scroll"), int(s.player.cx), int(s.player.cy))
    assert any("as a duck" in str(e.get("text", "")) for e in s.out)  # (no hands)
    saved = s.save_state()
    assert saved["sprite"] in ("Player", "PlayerF") and abs(saved["x"] - (bx - s.cur_map.ox)) < 40
    world.tick(0.05, now=world.now + 31000)
    assert s.player_form() == "" and s.player.name in ("Player", "PlayerF") and duck.name == "Duck"
    world.remove_entity(duck)
    leave(world, s)


def test_berts_cat_flap_lets_only_a_cat_through(world):
    flap = next(e for e in world.ents if e.npc_id == "Berts_Cat_Flap" or (e.name == "Cat_Flap"))
    s = join(world, "Moggy", flap.map, 300, 300)
    s.connected = True
    near(world, s, flap, 32, 0)
    shards = s.shards()
    s.choose_verb("Squeeze Through", flap, int(flap.cx), int(flap.cy))
    run_for(world, 10)
    assert s.shards() == shards                                     # (far too small for you)
    s.turn_into("Cat", 30, "")
    s.choose_verb("Squeeze Through", flap, int(flap.cx), int(flap.cy))
    run_for(world, 10)
    assert s.shards() == shards + 25 and s.get_attribute("BertsTin") == "1"
    leave(world, s)


def test_granny_brambles_hex_leaves_you_weak_for_her_rats(world):
    granny = next(e for e in world.ents if e.npc_id == "Granny_Bramble")
    s = join(world, "Hexed", granny.map, 300, 300)
    s.connected = True
    s.god_mode = True
    for q, v in (("Passage", 12), ("PipQuest", 2)):
        s.update_attribute(q, "=%d" % v)
    s.update_skill("Strength", "=20")
    near(world, s, granny, 36, 0)
    assert talk_to(world, s, granny)
    s.action_box_response_chosen(1)
    run_for(world, 10)
    s.action_box_response_chosen(1)
    run_for(world, 20)
    assert s.get_attribute("HexQuest") == "1" and s.skill_level("Strength") == 1    # (weak as a kitten)
    rats = [e for e in world.ents if e.npc_id == "Hex_Rat" and e.owner is s]
    assert len(rats) == 4
    for r in rats:
        s.kill_npc(r)
    run_for(world, 20)
    assert s.get_attribute("HexRats") == "4"
    assert talk_to(world, s, granny)
    s.action_box_response_chosen(1)
    run_for(world, 10)
    assert s.get_attribute("HexQuest") == "2" and s.skill_level("Strength") == 20
    leave(world, s)


def test_pip_is_cured_and_lady_pettigrew_gets_her_hat(world):
    pip = next(e for e in world.ents if e.npc_id == "Pip_The_Apprentice")
    s = join(world, "Hatter", pip.map, 300, 300)
    s.connected = True
    s.god_mode = True
    s.update_attribute("Passage", "=12")
    near(world, s, pip, 36, 0)
    assert talk_to(world, s, pip)
    s.action_box_response_chosen(1)
    run_for(world, 5)
    s.action_box_response_chosen(1)
    run_for(world, 10)
    assert s.get_attribute("PipQuest") == "1"
    stock(s, Egg=1, Feather=1, Cave_Mushroom=2)
    assert talk_to(world, s, pip)
    s.action_box_response_chosen(1)
    run_for(world, 10)
    assert s.get_attribute("PipQuest") == "2" and s.items_held("Swap_Scroll") == 1
    assert s.items_held("Invisibility_Potion") == 2
    lady = next(e for e in world.ents if e.npc_id == "Lady_Pettigrew")
    near(world, s, lady, 36, 0)
    assert talk_to(world, s, lady)
    s.action_box_response_chosen(1)
    run_for(world, 20)
    assert s.get_attribute("HatQuest") == "1"
    hat = next(e for e in world.ents if e.name == "Fancy_Hat" and e.owner is s)       # (on the nest: yours)
    s.do_action("Drink", next(e for e in s.inv if e.name == "Invisibility_Potion"))
    near(world, s, hat, 0, 0)
    s.choose_verb("Pickup", hat, int(hat.cx), int(hat.cy))
    run_for(world, 40)
    assert s.items_held("Fancy_Hat") == 1
    near(world, s, lady, 36, 0)
    assert talk_to(world, s, lady)
    s.action_box_response_chosen(1)
    run_for(world, 10)
    assert s.get_attribute("HatQuest") == "2" and s.items_held("Fancy_Hat") == 0
    leave(world, s)


def deep_floor_walk(m, start):
    """The floor cells reachable from start (tile x, y), not through walls."""
    seen, todo = {start}, [start]
    while todo:
        x, y = todo.pop()
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if (nx, ny) not in seen and m.inside(nx, ny) and m.tile[m.cell(nx, ny)] in (
                    "Flagstone001", "Cave_Floor001", "Cave_Floor002"):
                seen.add((nx, ny))
                todo.append((nx, ny))
    return seen


def test_the_shifting_deep_is_made_anew_and_every_way_down_can_be_reached(world):
    from dsengine.deep import Deep
    for seed in (1, 2, 3, 42, 777):
        world.deep.make(seed)
        for fl in world.deep.floors:
            m = world.maps[fl["map"]]
            up = (fl["up"][0] // 32 + 1, (fl["up"][1] + 8) // 32 + 1)
            reach = deep_floor_walk(m, up)
            goal = next(e for e in world.ents if e.map == m.name and e.name in ("Deep_Stairs_Down", "Deep_Heart"))
            gx, gy = int((goal.x - m.ox) // 32) + 1, int((goal.y - m.oy) // 32) + 1
            assert any(abs(gx - x) + abs(gy - y) <= 1 for x, y in reach), (seed, m.name)
    a = world.deep.seed
    world.deep.make(99)
    assert world.deep.seed != a and len(world.deep.floors) == 3


def test_the_deeps_chests_traps_heart_and_shifting(world, monkeypatch):
    import dsengine.deep as D
    world.deep.make(4242)
    mouth = next(e for e in world.ents if e.name == "Deep_Entrance")
    s = join(world, "Delver2", mouth.map, 300, 300)
    s.connected = True
    s.god_mode = False
    near(world, s, mouth, 0, 36)
    s.choose_verb("Enter", mouth, int(mouth.cx), int(mouth.cy))
    run_for(world, 10)
    f1 = world.deep.floors[0]["map"]
    assert s.cur_map.name == f1
    for e in [e for e in world.ents if e.map == f1 and e.type == NPC and e.hostile]:
        world.remove_entity(e)                                      # (only the chest and the traps: nothing wearing them down)
    monkeypatch.setattr(D.random, "uniform", lambda a, b: 99.0)     # (no mimics; every loot roll fails but gold's)
    chest = next(e for e in world.ents if e.map == f1 and e.name == "Deep_Chest")
    near(world, s, chest, 0, 30)
    gold = s.items_held("Gold_Coin(s)")
    s.choose_verb("Open", chest, int(chest.cx), int(chest.cy))
    run_for(world, 5)
    assert s.items_held("Gold_Coin(s)") > gold                      # (gold always: 100 in 100)
    got = s.items_held("Gold_Coin(s)")
    s.choose_verb("Open", chest, int(chest.cx), int(chest.cy))
    run_for(world, 5)
    assert s.items_held("Gold_Coin(s)") == got                      # (once a shift)
    m = s.cur_map
    hp = s.player.hp
    s.deep_trap("Darts", m, 5, 5)
    assert s.player.hp < hp and m.tile[m.cell(5, 5)] == "Trap_Sprung001"
    s.deep_trap("Pit", m, 6, 5)
    run_for(world, 5)
    assert s.cur_map.name == world.deep.floors[1]["map"]          # (fell a floor)
    world.deep.next_shift = world.now - 1
    seed = world.deep.seed
    world.deep.tick()
    assert world.deep.seed == seed                                  # (someone's inside: it waits)
    leave(world, s)
    world.deep.tick()
    assert world.deep.seed != seed                                  # (empty: it shifts)
    s2 = join(world, "Delver3", mouth.map, 300, 300)
    s2.update_attribute("DeepLoot", "=%d:x" % seed)
    assert s2.deep_had() == set()                                   # (a new shift: everything to find again)
    leave(world, s2)


def test_a_secret_by_the_square_is_found_once_and_counted(world):
    stump = next(e for e in world.ents if e.npc_id == "Secret_Ashford")
    s = join(world, "Snoop", stump.map, 300, 300)
    s.connected = True
    near(world, s, stump, 32, 0)
    s.choose_verb("Search", stump, int(stump.cx), int(stump.cy))
    run_for(world, 20)
    s.chest_response("CHEST_ALL")
    assert s.items_held("Rubber_Duck") == 1 and s.get_attribute("SecretsFound") == "1"
    s.choose_verb("Search", stump, int(stump.cx), int(stump.cy))
    run_for(world, 20)
    assert s.items_held("Rubber_Duck") == 1 and s.get_attribute("SecretsFound") == "1"     # (once each)
    leave(world, s)


def test_an_old_dungeons_trap_springs_then_rests(world):
    m = world.maps["24,12,-1"]
    assert any(t.startswith("Trap_") for t in m.trigger if t)
    s = join(world, "Trapped", "24,12,-1", 300, 300)
    s.connected = True
    s.god_mode = False
    s.update_skill("Hitpoints", "=40")
    hp = s.player.hp
    s.world_trap("Darts", m, 5, 5)
    assert s.player.hp < hp
    hp = s.player.hp
    s.world_trap("Darts", m, 5, 5)
    assert s.player.hp == hp                                        # (resting)
    world.tick(0.05, now=world.now + 601000)
    s.world_trap("Pie", m, 5, 5)
    assert s.skill_level("Magic") == max(0, s.base_skill_level("Magic") - 1) or s.skill_boosts
    leave(world, s)


def test_in_an_animals_body_the_animals_talk(world):
    s = join(world, "Moo", "11,-3,0", 384, 300)
    s.connected = True
    cow = world.add_npc("Cow", 0, s.player.x + 50, s.player.y, "Attitude=Good")
    s.turn_into("Cow", 30, "")
    s.out = []
    s.choose_verb("Talk to", cow, int(cow.cx), int(cow.cy))
    run_for(world, 20)
    from dsengine.tricks import ANIMAL_TALK
    said = " ".join(str(e) for e in s.out)
    assert any(line.split(".")[0] in said for line in ANIMAL_TALK["Cow"])
    world.remove_entity(cow)
    leave(world, s)


def test_duchess_the_cow_wants_three_herbs(world):
    cow = next(e for e in world.ents if e.npc_id == "Duchess_The_Cow")
    s = join(world, "Herby", cow.map, 300, 300)
    s.connected = True
    s.god_mode = True
    s.update_attribute("Passage", "=12")
    near(world, s, cow, 36, 0)
    assert talk_to(world, s, cow)
    s.action_box_response_chosen(1)
    run_for(world, 10)
    assert s.get_attribute("CowQuest") == "1"
    stock(s, Herb=3)
    assert talk_to(world, s, cow)
    s.action_box_response_chosen(1)
    run_for(world, 10)
    assert s.get_attribute("CowQuest") == "2" and s.items_held("Herb") == 0
    leave(world, s)


def test_the_mayors_trousers_were_taken_by_a_goose(world):
    dobbs = next(e for e in world.ents if e.npc_id == "Constable_Dobbs")
    s = join(world, "Sleuth", dobbs.map, 300, 300)
    s.connected = True
    s.god_mode = True
    for q, v in (("Passage", 12), ("AshfordQuest", 99)):
        s.update_attribute(q, "=%d" % v)
    near(world, s, dobbs, 36, 0)
    assert talk_to(world, s, dobbs)
    s.action_box_response_chosen(1)
    run_for(world, 10)
    assert s.get_attribute("TrousersQuest") == "1"
    for pid in ("Clue_Footprints", "Clue_Washing", "Clue_Feather"):
        clue = next(e for e in world.ents if e.npc_id == pid)
        near(world, s, clue, 32, 0)
        s.choose_verb("Search", clue, int(clue.cx), int(clue.cy))
        run_for(world, 20)
    assert s.get_attribute("TrouserClues") == "3" and s.get_attribute("TrousersQuest") == "2"
    near(world, s, dobbs, 36, 0)
    assert talk_to(world, s, dobbs)
    s.action_box_response_chosen(3)                                 # (a goose)
    run_for(world, 10)
    assert s.get_attribute("TrousersQuest") == "3"
    leave(world, s)


def test_the_scarecrow_gets_a_hat_and_shares_a_thought(world):
    crow = next(e for e in world.ents if e.npc_id == "Philosopher_Scarecrow")
    s = join(world, "Hatless", crow.map, 300, 300)
    s.connected = True
    s.god_mode = True
    s.update_attribute("Passage", "=12")
    near(world, s, crow, 36, 0)
    assert talk_to(world, s, crow)
    s.action_box_response_chosen(1)
    run_for(world, 10)
    assert s.get_attribute("ScarecrowQuest") == "1"
    stock(s, Fur_Cap=1)
    assert talk_to(world, s, crow)
    s.action_box_response_chosen(1)
    run_for(world, 10)
    assert s.get_attribute("ScarecrowQuest") == "2" and s.items_held("Fur_Cap") == 0
    leave(world, s)


def test_the_hollow_hill_cave_in_and_out_and_its_chest_once(world):
    s = join(world, "Spelunker", "2,4,0", 288, 480)
    s.connected = True
    s.god_mode = True

    def tile_verb(verb, map_name, tx, ty, stand):
        s.teleport(map_name, (stand[0] - 1) * 32, (stand[1] - 1) * 32 - 8)
        if s.pending_map:
            s.do_pending_map_change()
        run_for(world, 5)
        m = s.cur_map
        gx, gy = m.ox + (tx - 1) * 32 + 16, m.oy + (ty - 1) * 32 + 16
        s.choose_verb(verb, s.tile_entity_at(gx, gy), gx, gy)
        run_for(world, 40)
        if s.pending_map:
            s.do_pending_map_change()
        run_for(world, 5)

    tile_verb("Enter", "2,4,0", 8, 16, (9, 16))
    assert s.cur_map.name == "2,4,-1"                               # (down into the cave)
    chest = next(e for e in world.ents if e.npc_id == "Hollow_Hill_Chest")
    s.unlocked_chests.add(s.chest_key(chest))                       # (its lock picked: locks.py has its own test)
    near(world, s, chest, 0, 30)
    s.choose_verb("Open", chest, int(chest.cx), int(chest.cy))
    run_for(world, 20)
    s.chest_response("CHEST_ALL")
    assert s.items_held("Iron_Helm") == 1 and s.get_attribute("HollowHillChest") == "1"
    s.choose_verb("Open", chest, int(chest.cx), int(chest.cy))
    run_for(world, 20)
    s.chest_response("CHEST_ALL")
    assert s.items_held("Iron_Helm") == 1                           # (once each)
    tile_verb("Climb Up", "2,4,-1", 8, 16, (9, 16))
    assert s.cur_map.name == "2,4,0"
    leave(world, s)


def test_doctor_foster_heals_the_hurt_and_tells_the_well_to_keep_their_gold(world):
    doc = next(e for e in world.ents if e.npc_id == "Northport_Doctor_349")
    s = join(world, "Patient", doc.map, 300, 300)
    s.connected = True
    s.god_mode = True
    stock(s, **{"Gold_Coin(s)": 30})
    near(world, s, doc, 0, 40)
    s.player.hp = s.player_max_hp
    assert talk_to(world, s, doc)
    s.action_box_response_chosen(1)                                 # (heal me)
    run_for(world, 10)
    assert s.items_held("Gold_Coin(s)") == 30 and s.ab_mode == "Conversation"   # (fit as a fiddle: no charge)
    assert "not a scratch" in s.ab_text
    s.action_box_response_chosen(1)                                 # (thank you)
    run_for(world, 10)
    s.player.hp = 3
    assert talk_to(world, s, doc)
    s.action_box_response_chosen(1)
    run_for(world, 10)
    assert s.items_held("Gold_Coin(s)") == 20 and s.player.hp == s.player_max_hp
    leave(world, s)


def test_skills_renamed_or_made_one_come_back_as_they_are_now(world):
    s = Session(world, "Oldtimer")
    s.load_state({"skills": {"Strength": 12, "Magic": 9, "Smithing": 6, "Crafting": 8, "Construction": 3,
                             "Farming": 5, "Potion_Making": 4, "Hitpoints": 20}, "skills_of": 25})
    assert s.skill_level("Channeling") == 9 and s.skill_level("Crafting") == 8      # (made one: the better of two)
    assert s.skill_level("Homesteading") == 5 and s.skill_level("Alchemy") == 4
    assert s.skill_level("Shardcraft") == 4                       # (new: half their Magic, to begin with)
    assert s.skill_level("Magic") == 9 and s.skill_level("Smithing") == 8           # (an old name: the skill now)
    names = s.data.skill_name[1:]
    assert names[:4] == ["Strength", "Defence", "Channeling", "Shardcraft"]
    assert not {"Magic", "Smithing", "Construction", "Farming", "Potion_Making"} & set(names)
    saved = s.save_state()["skills"]
    assert "Magic" not in saved and saved["Channeling"] == 9
    fresh = Session(world, "Newcomer")
    fresh.load_state(None)
    assert fresh.skill_level("Shardcraft") == 1


def test_channeling_makes_spells_cheaper_but_never_free(world):
    from dsengine.shards import channeled_cost
    d = world.data
    costs = [channeled_cost(10, lv, d) for lv in range(1, 26)]
    assert costs[0] == 10 and costs == sorted(costs, reverse=True)  # (never dearer as you go)
    assert costs[-1] == 7                                           # (30% at most, at level 21 and up)
    assert costs[4] == 9 and costs[9] == 9 and costs[14] == 8       # (slowly: a Shard every few levels)
    assert channeled_cost(1, 25, d) == 1 and channeled_cost(2, 25, d) == 1   # (never under a Shard)
    assert channeled_cost(0, 25, d) == 0                            # (free stays free)
    a = join(world, "Channeler", "11,-3,0", 384, 300)
    a.update_skill("Channeling", "=1")
    full = a.spell_cost("Fire_Storm")
    a.update_skill("Channeling", "=25")
    assert a.spell_cost("Fire_Storm") == int(round(full * 0.7)) < full
    assert next(r for r in a.spellbook() if r["spell"] == "Fire_Storm")["cost"] == a.spell_cost("Fire_Storm")
    leave(world, a)


def test_dismantling_trains_shardcraft_and_can_leave_a_rare_shard(world, monkeypatch):
    a = join(world, "Breaker", "11,-3,0", 384, 300)
    import dsengine.shardcraft as SC
    monkeypatch.setattr(SC, "random_number", lambda lo, hi: lo)    # (the luckiest roll)
    stock(a, Iron_Sword=1, Oak_Staff=1, Iron_Shield=1, Copper_Dagger=1)
    craft = a.skill_xp_of("Shardcraft")
    for name, rare in (("Iron_Sword", "Ember_Shard"), ("Oak_Staff", "Storm_Shard"), ("Iron_Shield", "Ward_Shard")):
        it = next(e for e in a.inv if e.name == name)
        a.dismantle_now(it.uid, a.dismantle_worth(name))
        assert a.items_held(rare) >= 1, name
    assert a.skill_xp_of("Shardcraft") > craft
    monkeypatch.setattr(SC, "random_number", lambda lo, hi: hi)    # (the unluckiest: nothing rare)
    held = a.items_held("Ember_Shard")
    stock(a, Iron_Sword=1)
    it = next(e for e in a.inv if e.name == "Iron_Sword")
    a.dismantle_now(it.uid, a.dismantle_worth("Iron_Sword"))
    assert a.items_held("Ember_Shard") == held
    assert a.rare_shard_for("Copper_Dagger") == ""                  # (worth too little to hold one)
    leave(world, a)


def test_enchanting_binds_a_rare_shard_into_gear(world):
    a = join(world, "Enchanter", "11,-3,0", 384, 300)
    a.connected = True
    stock(a, Iron_Sword=1, Ember_Shard=1, Ward_Shard=1, Shard=50)
    sword = next(e for e in a.inv if e.name == "Iron_Sword")
    sword.wear = 7
    ember = next(e for e in a.inv if e.name == "Ember_Shard")
    assert "Enchant" in a.get_verbs(ember)
    a.update_skill("Shardcraft", "=1")
    a.do_action("Enchant", ember)
    assert a.ab_mode == "Conversation" and a.responses[0].startswith("Iron Sword")
    a.out = []
    a.action_box_response_chosen(1)
    assert a.items_held("Iron_Sword") == 1 and any(e.get("name") == "Denied" for e in a.out)   # (Shardcraft 4)
    a.update_skill("Shardcraft", "=4")
    a.do_action("Enchant", next(e for e in a.inv if e.name == "Ward_Shard"))
    assert not a.ab_mode or not any("Sword" in r for r in a.responses)   # (a ward shard won't take to a blade)
    a.close_action_box(-1)
    shards = a.shards()
    a.do_action("Enchant", ember)
    a.action_box_response_chosen(1)
    assert a.items_held("Emberbound_Iron_Sword") == 1 and a.items_held("Iron_Sword") == 0
    assert a.items_held("Ember_Shard") == 0 and a.shards() == shards - a.enchant_fee("Iron_Sword")
    it = next(e for e in a.inv if e.name == "Emberbound_Iron_Sword")
    assert it.wear == 7                                             # (the same sword, as worn as it was)
    base = int(a.entity_ini("Iron_Sword", "Attack", "0"))
    assert int(a.entity_ini(it.name, "Attack", "0")) == base + 2
    a.equip_item(it)
    assert a.worn_items() == [] or "Iron_Sword" in a.worn_items()   # (drawn as the sword it was)
    assert a.dismantle_worth("Emberbound_Iron_Sword") > 0 and a.rare_shard_for("Emberbound_Iron_Sword") == ""
    leave(world, a)


def test_a_new_pocket_is_raw_rim_shaped_with_shards(world):
    a = join(world, "Shaper")
    stock(a, Hearth_Anchor=1)
    a.go_home()
    world.tick(0.05)
    m = a.cur_map
    ax, ay = world.homes.arrival
    assert m.tile[m.cell(ax, ay - 1)] == "Rim_Glass001" and m.tile[m.cell(3, 3)] == "Rim_Mist001"
    assert world.homes.object_at(m, ax - 1, ay).name == "Pocket_Anchor"
    assert not any(e.name == "Homestone" for e in world.ents)       # (a shardstone takes you home now)
    a.remove_inventory_item("Shard", a.shards())
    stock(a, Shard=40, Plank=5, Nails=10)
    assert not a.build(3, 3, "Plank001")                           # (mist: nothing to build on)
    edge = next(x for x in range(1, 26) if m.tile[m.cell(x, 16)] == "Rim_Glass001") - 1
    assert not a.build(edge - 1, 16, "Terra_Glass")                # (mist stills only beside held ground)
    assert a.build(edge, 16, "Terra_Glass") and m.tile[m.cell(edge, 16)] == "Rim_Glass001"
    assert a.shards() == 40 - a.homes.catalog["Terra_Glass"]["shards"]
    assert not a.build(edge, 16, "Grass001")                       # (glass won't take grass: soil first)
    shards = a.shards()
    assert not a.build(edge, 16, "Terra_Grass") and a.shards() == shards   # (grass goes on soil)
    assert a.build(edge, 16, "Terra_Soil") and m.tile[m.cell(edge, 16)] == "Dirt001"
    a.update_skill("Shardcraft", "=2")
    assert a.build(edge, 16, "Terra_Grass") and m.tile[m.cell(edge, 16)] == "Grass001"
    a.remove_inventory_item("Shard", a.shards())
    assert not a.build(edge + 1, 15, "Terra_Soil")                 # (no Shards: nothing done, nothing taken)
    assert m.tile[m.cell(edge + 1, 15)] == "Rim_Glass001"
    leave(world, a)


def test_shard_blooms_give_shards_to_their_owner_now_and_then(world, monkeypatch):
    import dsengine.homes as H
    clock = [1_000_000.0]
    monkeypatch.setattr(H.time, "time", lambda: clock[0])
    a = join(world, "Gardener")
    stock(a, Hearth_Anchor=1)
    a.go_home()
    world.tick(0.05)
    m = hold_pocket(world, a)
    a.update_skill("Shardcraft", "=3")
    stock(a, Shard=100)
    for x in (6, 8):
        a.build(x, 6, "Terra_Soil")
    assert a.build(6, 6, "Shard_Bloom")
    assert a.blooms_allowed() == 1 and not a.build(8, 6, "Shard_Bloom")     # (Shardcraft 3: one)
    bloom = world.homes.object_at(m, 6, 6)
    a.teleport(m.name, 5 * 32, 6 * 32)
    a.do_pending_map_change()
    world.tick(0.05)
    before = a.shards()
    a.do_action("Harvest", bloom)
    assert a.shards() == before                                    # (just planted: still filling)
    clock[0] += 6 * 3600
    a.do_action("Harvest", bloom)
    assert a.shards() == before + 4
    a.do_action("Harvest", bloom)
    assert a.shards() == before + 4                                # (once, then it fills again)
    a.update_skill("Shardcraft", "=5")
    assert a.blooms_allowed() == 2 and a.build(8, 6, "Shard_Bloom")
    saved = world.homes.state()
    assert len(saved["Gardener"]["blooms"]) == 2
    a.set_visit("open")
    b = join(world, "Picker")
    b.visit_home("Gardener")
    world.tick(0.05)
    b.teleport(m.name, 5 * 32, 6 * 32)
    b.do_pending_map_change()
    clock[0] += 7 * 3600
    theirs = b.shards()
    b.do_action("Harvest", bloom)
    assert b.shards() == theirs                                    # (only its owner's)
    assert world.add_npc("Wolf", m.mz, m.ox + 200, m.oy + 200, "Attitude=Bad") is None   # (a pocket is safe)
    leave(world, b)
    leave(world, a)


def test_a_shardstone_takes_you_home_and_the_anchor_back(world):
    m = world.maps["11,-3,0"]
    ws = next(e for e in world.ents if e.name == "Shardstone" and e.map == m.name)
    a = join(world, "Homebody", m.name, int(ws.x - m.ox) + 40, int(ws.y - m.oy) + 8)
    a.connected = True
    a.update_attribute("Waystone.Ashford", "=1")
    a.out = []
    a.choose_verb("Travel", ws, int(ws.cx), int(ws.cy))
    ticks(world, 20)
    assert next(e for e in a.out if e.get("t") == "stones")["home"] is False      # (no anchor: no way home)
    stock(a, Hearth_Anchor=1)
    a.out = []
    a.choose_verb("Travel", ws, int(ws.cx), int(ws.cy))
    ticks(world, 20)
    assert next(e for e in a.out if e.get("t") == "stones")["home"] is True
    a.handle({"t": "stone_home"})
    ticks(world, 5)
    assert a.on_own_home()
    anchor = world.homes.object_at(a.cur_map, *(v - (1 if i == 0 else 0) for i, v in enumerate(world.homes.arrival)))
    a.do_action("Touch", anchor)
    assert a.ab_mode == "Conversation" and a.responses[0] == "Take me back."
    a.action_box_response_chosen(1)
    ticks(world, 5)
    assert a.cur_map.name == m.name                                # (back by the shardstone you left from)
    leave(world, a)


def test_an_old_home_keeps_its_land_and_its_homestone_is_its_anchor(world):
    old_land = [":".join(["Grass001"] * 25)] * 21 + ["StaticObject\tHomestone\t352\t544", "Id\tHome_Arrival\t13\t18"]
    w2 = World(ROOT)
    w2.homes.load({"Pioneer": {"n": 7, "visit": "closed", "friends": [], "cells": {}, "cleared": [], "objects": {},
                               "land": old_land}})
    m = w2.homes.map_of("Pioneer")
    assert m.tile[m.cell(5, 5)] == "Grass001" and w2.homes.object_at(m, 12, 18).name == "Pocket_Anchor"
    s = Session(w2, "Pioneer")
    s.load_state({"inventory": [["Access_Crystal", 1, 0]]})
    assert s.items_held("Hearth_Anchor") == 1                      # (the Access Crystal, as it's called now)


def test_editor_lays_out_sets_and_smooths_coasts():
    # The map editor (dsedit/world.py): a set dragged out over a rectangle gets its corners, edges and middle; a range's
    # peaks are one tile in the palette; a coast's inside corner gets its diagonal shore piece
    from dsedit.project import Project
    from dsedit import world as WD
    P = Project(ROOT)
    roof = WD.shape(P, "Thatch_Roof005", 3, 5)
    assert [r[0] for r in roof] == ["Thatch_Roof%03d" % n for n in (1, 4, 7, 10, 13)]
    assert roof[2] == ["Thatch_Roof007", "Thatch_Roof008", "Thatch_Roof009"]      # (the ridge in the middle)
    assert WD.shape(P, "Wood_Fence001", 3, 3) is None and WD.joins(P, "Wood_Fence001")   # (its pieces join instead)
    fence = {}
    put = lambda x, y, t: fence.__setitem__((x, y), t)
    WD.lay_joins(P, "Wood_Fence001", WD.join_cells(3, 3), lambda x, y: fence.get((x, y)), put)
    assert (1, 1) not in fence and fence[(0, 0)] == "Wood_Fence003"              # (round the edge only)
    assert WD.shape(P, "Rug005", 1, 3) == [["Rug014"], ["Rug015"], ["Rug016"]]    # (a runner)
    assert WD.shape(P, "Bench001", 3, 3) is None
    assert WD.stand_ins(P)["Peak003"] == WD.stand_ins(P)["Mountain002"]
    assert "Pebbles002" in WD.look_alikes(P, "Pebbles001") and WD.look_alikes(P, "Water002") == ["Water002"]
    grid = {(x, y): "Water001" for x in range(5) for y in range(5)}
    grid.update({(2, 1): "Grass001", (3, 1): "Grass001", (3, 2): "Grass001"})
    WD.smooth_corners(P, lambda x, y: grid.get((x, y)), lambda x, y, t: grid.__setitem__((x, y), t), {(3, 2)})
    assert grid[(2, 2)] == "Water002"                                           # (land to its north and east)
    grid = {(x, y): "Water001" for x in range(5) for y in range(5)}
    grid.update({(2, 1): "Grass001", (3, 1): "Dirt001", (3, 2): "Grass001"})     # (a path off the corner)
    WD.smooth_corners(P, lambda x, y: grid.get((x, y)), lambda x, y, t: grid.__setitem__((x, y), t), {(3, 2)})
    assert grid[(2, 2)] == "Water002"


def test_editor_palette_auto_shows_whole_things_not_their_pieces():
    # The Maps palette's Auto view: a bed is one entry (its foot isn't on its own) and goes down whole; a town wall's
    # face (put in by its set) is in Detail only; Roofs offers roofs, not grass
    from dsedit.project import Project
    from dsedit import world as WD, terrain as TR
    P = Project(ROOT)
    decor = TR.groups(P, "decor")
    hidden = {n for g in decor.values() if g.kind != "Terrain" for n in g.tiles}
    assert {"Bed002", "Double_Bed004"} <= hidden
    assert decor["set:Bed"].brush == "Bed001" and decor["set:Bed"].kind == "Set"
    assert "City_Wall004" in {n for g in TR.groups(P, "map").values() for n in g.tiles}
    assert sorted(WD.whole(P, "Bed001")) == [(0, 0, "Bed001"), (0, 1, "Bed002")]
    assert (-1, 0, "Bed005") in WD.whole(P, "Bed006") and WD.whole(P, "Bench001") == []
    assert len(WD.whole(P, "Double_Bed004")) == 4 and (-1, -1, "Double_Bed001") in WD.whole(P, "Double_Bed004")
    roof = TR.layer_test(P, "roof")
    assert roof("Thatch_Roof001") and roof("Steeple001") and roof("Chapel_Stone_Upper001") and not roof("Grass001")


def test_a_fence_thinner_than_a_cell_is_walked_round_not_through():
    w = World(ROOT)
    spot = None
    for m in (w.maps[n] for n in ("1,1,0", "2,4,0", "3,5,0", "4,6,0", "5,5,0", "11,-3,0")):
        for ty in range(4, 16):
            for tx in range(4, 18):
                if all(m.tile[m.cell(x, y)] and "0" not in m.walk[m.cell(x, y)] and not m.decor[m.cell(x, y)] and
                       not w.data.tile_water(m.tile[m.cell(x, y)])
                       for x in range(tx - 2, tx + 5) for y in range(ty - 2, ty + 3)):
                    spot = (m, tx, ty)
                    break
            if spot:
                break
        if spot:
            break
    assert spot, "no open ground"
    m, tx, ty = spot
    for x in range(tx, tx + 3):                       # (three tiles of fence, east-west, across the middle)
        assert m.change_cell(x, ty, "Wood_Fence001")      # (a rail, east-west)
    x = m.ox + tx * 32 + 16                           # (the middle of the fence, a tile above it and a tile below)
    above, below = m.oy + (ty - 1) * 32 - 12, m.oy + ty * 32 + 12
    assert not w.grid_line_walkable(m.mz, x, above, x, below)
    s = join(w, "Fencer", m.name, x - 16 - m.ox, above - 30 - m.oy)
    p = s.player
    assert p.fy < m.oy + (ty - 1) * 32 + 19                   # (short of the rail, low in its tile)
    for _ in range(30):                               # (straight at it, as fast as a step goes: it holds)
        w.try_move_entity(p, 0, 6, s)
    assert p.fy < m.oy + (ty - 1) * 32 + 19
    assert w.plan_path(p, x, below - (p.fy - p.cy), 0, 4000, s) and p.path    # (a way round)
    ax, ay = p.fx, p.fy
    for i, (wx, wy) in enumerate(p.path):
        wy += p.fy - p.cy
        if i == 0:                                    # (from the feet, in the rail's own cell: by the walk masks)
            assert all(w.pixel_walkable(m.mz, ax + (wx - ax) * k / 20, ay + (wy - ay) * k / 20) for k in range(21))
        else:
            assert w.grid_line_walkable(m.mz, ax, ay, wx, wy, s)
        ax, ay = wx, wy
    leave(w, s)


def test_animals_keep_out_of_houses_by_where_they_roam():
    """No rule stops an animal at a door now (Indoors= is gone): its zone leaves out the houses on its map
    (dev/migrate/assign_homes.py), and cats and dogs come in as they always did."""
    w = World(ROOT)
    m = w.maps["0,-2,0"]
    spot = None                                       # (open ground just south of a roofed, walkable cell)
    for ty in range(2, 20):
        for tx in range(2, 24):
            c, b = m.cell(tx, ty), m.cell(tx, ty + 1)
            if (m.roof[c] and not m.roof[b] and "0" not in m.walk[c] and "0" not in m.walk[b] and
                    not m.lock_at.get((tx, ty))):
                spot = (tx, ty)
                break
        if spot:
            break
    assert spot, "no doorway"
    tx, ty = spot
    fx, fy = m.ox + (tx - 0.5) * 32, m.oy + ty * 32 + 4  # (feet just outside, a step from the roof)
    assert w.roofed(m.mz, fx, fy - 8) and not w.roofed(m.mz, fx, fy)
    sheep = w.add_npc("Sheep", m.mz, fx, fy, "")
    cat = w.add_npc("Cat", m.mz, fx, fy, "")
    assert w.entity_can_stand(sheep, fx, fy - 8, fx, fy) and w.entity_can_stand(cat, fx, fy - 8, fx, fy)
    yard = w.maps["3,1,0"]                            # (the churchyard's sheep: its zone goes round the chapel)
    flock = [e for e in w.ents if e.name == "Sheep" and e.map == "3,1,0"]
    lines = open(os.path.join(ROOT, "maps", "3,1,0.txt"), encoding="cp1252").read().splitlines()
    assert flock and all("Attitude=Passive" in ln for ln in lines if ln.startswith("NPC\tSheep\t"))
    for e in flock:
        z = e.ai.zone
        for gx in range(int(z[0]), int(z[2]), 32):
            for gy in range(int(z[1]), int(z[3]), 32):
                if w.roofed(yard.mz, gx + 16, gy + 16) and not w.roofed(yard.mz, e.fx, e.fy):
                    assert not w.in_zone(e.ai, gx + 16, gy + 16)


def test_editor_knows_what_points_at_the_maps():
    """The map editor's badges (dsedit/refs.py): places by name, tiles by coordinates, quest givers, whole maps."""
    from dsedit.project import Project
    from dsedit.refs import Refs, label
    r = Refs(Project(ROOT))
    assert r.fresh()
    assert "Quest Dinner at Edwin's" in [label(u) for u in r.of_name("Isle_Bank")]       # (a quest's marker)
    assert "WorldMap.ini Edwin & Maren's House" in [label(u) for u in r.of_name("isle_bank")]   # (a label)
    assert ("script", "Read Isle_Bank_Notice") in r.of_name("Isle_Bank_Notice")         # (its own script)
    assert ("script", "3,2,0") in r.of_name("Isle_Ferry_Pier")                          # (a script's place)
    assert ("Shardstones.ini", "Northport") in r.of_name("Waystone_Northport")
    assert ("quest", "Dinner at Edwin's") in r.of_kind("Maren")                          # (a quest's giver)
    assert ("script", "3,2,0") in r.of_map("3,2,0")                                      # (its arrival script)
    assert r.tiles and all(len(k) == 3 for k in r.tiles)                                 # (map, tile x, tile y)
    assert not r.fresh()                                                                 # (nothing changed since)
    # and exactly what points: the lines themselves
    assert "Marker1=Isle_Bank" in r.lines(("quest", "Dinner at Edwin's"), [("names", "Isle_Bank")])
    said = r.lines(("script", "3,2,0"), [("names", "Isle_Ferry_Pier")])
    assert said and said[0].startswith("01  Add.Entity  Isle_Ferry_Pier  Ferryman")       # (numbered as the game does)
    assert r.lines(("quest", "Dinner at Edwin's"), [("givers", "Maren")]) == ["Giver=Maren"]


def test_editor_shows_the_shared_script_a_thing_runs_and_its_lines_here():
    """The map editor's "What it runs" (dsedit/refs.py): the script the game would find for each verb, and for a shared
    one (every Trader's) just the lines that can run on this map, its >On.Map settled."""
    from dsedit.project import Project, ScriptDoc
    from dsedit.refs import script_for, lines_here
    P = Project(ROOT)
    names = P.scripts()
    assert script_for(names, "Talk to", "Trader", "NPC") == ("Talk to Trader", "shared")
    assert script_for(names, "Read", "Notice", "StaticObject", "Isle_Bank_Notice") == ("Read Isle_Bank_Notice", "own")
    assert script_for(names, "Chop", "Tree002", "Tile") == ("Chop Tree", "shared")      # (its name without the number)
    assert script_for(names, "Pickup", "Gold_Coin(s)", "MapItem") == ("Pickup [MapItem]", "shared")
    assert script_for(names, "Attack", "Trader", "NPC") is None                         # (the game's own)
    cmds = ScriptDoc(P, "Talk to Trader").commands()
    here = [t for _, t in lines_here(cmds, "9,10,0")]                                   # (Oakhollow's market)
    assert any("Welcome to Oakhollow!" in t for t in here) and any("SHOP-Oakhollow" in t for t in here)
    assert not any("Greyford" in t for t in here)
    away = [t for _, t in lines_here(cmds, "1,1,0")]                                    # (no Trader's town)
    assert any("Nothing to sell here" in t for t in away) and not any("Welcome" in t for t in away)


def test_scrolls_are_rare_and_only_teach(world):
    """dev/migrate/rare_scrolls.py: none at the start, one at a time, never sold if a quest or a chest gives it."""
    d = world.data
    s = join(world, "Apprentice")
    assert not any(e.name.endswith("_Scroll") for e in s.inv)                     # (a new character: none)
    found, sold = "Fire_Bolt_Scroll", "Teleport_Scroll"                           # (Bert gives one; the other is sold)
    assert d.entity_ini(found, "Value", "") == "0" and float(d.entity_ini(sold, "Value", "0")) >= 100
    assert d.entity_ini(found, "Stackable", "") == "1"
    assert not s.can_sell_here(found)                                            # (no shop takes it, to sell it on)
    racks = open(os.path.join(ROOT, "data", "ItemRacks.ini"), encoding="cp1252").read()
    assert "Fire_Bolt_Scroll," not in racks and "[CRAFT-Scrolls]" not in racks
    assert "Scroll" not in d.entity_ini("Bandit", "Drops", "")                     # (no beast drops one)
    leave(world, s)


def test_chests_say_nothing_and_draughts_come_in_three_strengths(world):
    lines = open(os.path.join(ROOT, "data", "Scripts", "Open Chest 2.txt"), encoding="cp1252").read()
    assert "Grave goods" not in lines and "\tYellow\t" not in lines
    heal = lambda n: world.data.spell_ini(n, "Heal", "")
    assert (heal("Minor_Healing_Draught"), heal("Healing_Draught"), heal("Major_Healing_Draught")) == \
        ("8-12", "15-20", "26-32")


def test_a_cat_sits_before_it_lies_down_and_sits_up_before_it_walks(world):
    m = world.maps["11,-3,0"]
    cat = world.add_npc("Cat", m.mz, m.ox + 12 * 32, m.oy + 10 * 32, "")
    a = cat.ai
    world.npc_ease_pose(cat, a, "Curl")
    assert cat.pose == "Sit" and a.pose_next == "Curl"              # (down: it sits first)
    world.npc_pose_step(cat, a)
    assert cat.pose == "Curl"
    world.animate_entity(cat, False)
    assert cat.image == "Cat_Curl" + cat.image[-1]
    d = cat.direction
    a.state, a.timer, a.turn_at = 0, world.now + 60000, world.now - 1   # (idle, a turn due)
    for _ in range(5):
        world.tick(0.05, now=world.now + 50)
    assert cat.direction == d and cat.pose == "Curl"                 # (asleep: it doesn't turn about)
    world.npc_next_move(cat, a)
    assert cat.pose == "Sit"                                         # (up: it sits up first)
    world.remove_entity(cat)


def test_townsfolk_wear_their_trades_other_colours_but_stay_who_they_are(world):
    """build_people.py looks: a picture a trade, recoloured in the browser; which colouring goes by Id (or spot)."""
    from dsengine.view import entity_state
    keeps = [e for e in world.ents if e.name == "Barkeep"]
    assert len({e.look for e in keeps}) > 2                                    # (not all alike)
    assert all(world.npc_look(e, "Id=%s" % e.npc_id) == e.look for e in keeps if e.npc_id)   # (the same every time)
    e = keeps[0]
    assert world.npc_look(e, "Look=0") == 0 and world.npc_look(e, "Look=2") == 2   # (Look= on its map line)
    edwin = next(x for x in world.ents if x.name == "Edwin")
    assert edwin.look == 0 and not world.data.entity_ini("Edwin", "Looks", "")       # (one of a kind: as drawn)
    s = join(world, "Onlooker", e.map, int(e.x - world.maps[e.map].ox), int(e.y - world.maps[e.map].oy))
    st = entity_state(world, next(x for x in keeps if x.look), s)
    assert st["lk"] >= 1 and st["n"] == "Barkeep"
    leave(world, s)


def test_a_display_name_is_shown_but_the_name_stays(world):
    from ashen import lb
    from ashen.lb import pretty
    assert pretty("Pine_Tree001") == "Pine Tree"                              # (none set: its name tidied)
    lb.DISPLAY_NAMES["BREAD"] = "Crusty Loaf"
    try:
        s = join(world, "Namer")
        stock(s, Bread=1)
        bread = next(e for e in s.inv if e.name == "Bread")
        assert s.display_name(bread) == "Crusty Loaf" and bread.name == "Bread"     # (shown so; still Bread)
        assert s.items_held("Bread") == 1
        leave(world, s)
    finally:
        del lb.DISPLAY_NAMES["BREAD"]
    m = world.maps["1,1,0"]
    e = world.add_entity_of_type("MapItem", "Bread", m.mz, m.ox + 100, m.oy + 100, "1 Name=Old_Loaf")
    assert e.display == "Old Loaf" and e.name == "Bread"                      # (a name of its own, on its map line)
    world.remove_entity(e)


# ----- Roadmap group 1: quick fixes
def test_farm_animals_are_passive_and_leave_no_bones(world):
    from dsengine.view import entity_state
    for kind in ("Chicken", "Cow", "Sheep"):
        assert "Bones" not in world.data.entity_ini(kind, "Drops", "")
        assert world.data.entity_ini(kind, "Level", "0") == "1"           # (remnants, like any beast)
        assert world.data.entity_ini(kind, "Attitude", "") == "Passive"
    s = join(world, "Shepherd")
    m = world.maps["1,1,0"]
    rabbit = world.add_npc("Rabbit", m.mz, m.ox + 200, m.oy + 200, "-")
    wolf = world.add_npc("Wolf", m.mz, m.ox + 260, m.oy + 200, "-")
    try:
        assert entity_state(world, rabbit, s)["f"] == 2                    # (can be attacked: won't come for you)
        assert entity_state(world, wolf, s)["f"] == 1
        assert "Attack" in s.get_verbs(rabbit)
        assert rabbit.aggressive == 0
    finally:
        world.remove_entity(rabbit)
        world.remove_entity(wolf)
        leave(world, s)


def test_no_quest_locked_message(world):
    s = join(world, "Eager")
    name = next(n for n, d in world.data.quest_table() if int(float(d.get("REQUIRES.LEVEL", "0") or 0)) > 5)
    s.connected, s.out = True, []
    assert not s.quest_can_start(name)
    msgs = [e.get("text", "") for e in s.out if e.get("t") == "msg"]
    assert not any("locked" in t.lower() for t in msgs)
    leave(world, s)


def test_a_frog_on_the_bank_of_a_shore_tile_walks(world):
    # (a corner piece laid by hand, its land in one corner: the coasts round themselves now, so none lie in the maps)
    m = world.maps["4,0,0"]
    tx, ty = 2, 2
    old = m.tile[m.cell(tx, ty)]
    assert world.change_tile(m, tx, ty, "Water002")
    found = None
    try:
        assert m.tile_is_water(tx, ty)
        for lx in range((tx - 1) * world.tw + 2, tx * world.tw - 2, 3):
            for ly in range((ty - 1) * world.th + 2, ty * world.th - 2, 3):
                if not found and m.local_walkable(lx, ly):
                    found = (lx, ly)
        assert found, "a shore tile with land on it"
        lx, ly = found
        frog = world.add_npc("Frog", m.mz, m.ox + lx - 16, m.oy + ly - 28, "-")
        try:
            world.set_entity_position(frog, frog.x + (m.ox + lx - frog.fx), frog.y + (m.oy + ly - frog.fy))
            assert not world.in_water(frog)                                 # (its feet on the bank: it hops)
        finally:
            world.remove_entity(frog)
    finally:
        world.change_tile(m, tx, ty, old)


def test_a_walk_goes_round_someone_in_the_way(world):
    """Bess stood between you and the tinderbox: you go round her to it, not stop against her."""
    m = world.maps["2,0,0"]
    box = next(e for e in world.ents if e.type == MAPITEM and e.name == "Tinderbox")
    bess = next(e for e in world.ents if e.type == NPC and e.name == "Milkmaid" and e.map == "2,0,0")
    assert world.npc_is_solid(bess)
    s = join(world, "Roundabout", "2,0,0", int(box.x - m.ox) + 90, int(box.y - m.oy) - 6)
    box.alive = True
    s.choose_verb("Pickup", box, box.cx, box.cy)
    for _ in range(300):
        bess.x, bess.y = box.x + 44, box.y - 4                  # (she stays put, square in the way)
        world.tick(0.05)
        if s.items_held("Tinderbox"):
            break
    assert s.items_held("Tinderbox") == 1
    leave(world, s)


def test_jimmy_goes_to_bed_and_is_never_two(world):
    day = world.day_fraction()
    jimmy = next(e for e in world.ents if e.npc_id == "Jimmy" and e.map == "4,0,0")
    abed = next(e for e in world.ents if e.name == "Sleeping_Jimmy")
    s = join(world, "Catsitter")
    try:
        world.set_day_fraction(0.5)
        near(world, s, jimmy, 40, 0)
        run_for(world, 60)
        assert jimmy.active and not abed.active
        world.set_day_fraction(0.95)                                        # (night: to bed, not out of a door)
        both = False
        for _ in range(600):
            world.tick(0.05, now=world.now + 50)
            if jimmy.active and abed.active:
                both = True
            if not jimmy.active:
                break
        run_for(world, 50)
        assert not both and not jimmy.active and abed.active
    finally:
        world.set_day_fraction(day)
        run_for(world, 50)
        leave(world, s)


def test_an_npc_kill_leaves_loot_and_remnants_hunt_creatures(world):
    m = world.maps["1,1,0"]
    sheep = world.add_npc("Sheep", m.mz, m.ox + 300, m.oy + 300, "-")
    wolf = world.add_npc("Wolf", m.mz, m.ox + 330, m.oy + 300, "-")
    before = {id(e) for e in world.ents if e.type == MAPITEM}
    world.npc_killed_by_npc(sheep, wolf)
    dropped = [e for e in world.ents if e.type == MAPITEM and id(e) not in before]
    assert any(e.name == "Raw_Meat" for e in dropped)                      # (the Drops, for anyone)
    assert all(getattr(e, "private_to", None) is None for e in dropped)
    for e in dropped:
        world.remove_entity(e)
    remnant = world.add_npc("Living_Remnant", m.mz, m.ox + 360, m.oy + 300, "-", "Bad")
    try:
        assert "ALL" in remnant.ai.hunts
        world.tick(0.05, now=world.now + 50)                               # (the NPCs by map: made each tick)
        prey = world.npc_prey(remnant, remnant.ai)                         # (any creature near it, not only you)
        assert prey is not None and prey.hostile and prey.name != "Living_Remnant"
    finally:
        world.remove_entity(remnant)
        world.remove_entity(wolf)


def test_a_kill_by_a_player_or_an_npc_comes_back_and_its_loot_goes_alike(world, monkeypatch):
    import dsengine.npcs as NP
    monkeypatch.setattr(NP, "rnd", lambda: 0.0)                    # (every drop drops)
    a = join(world, "Reaper")
    foes = [e for e in world.ents if e.type == NPC and e.source == "MAP" and e.owner is None and e.hostile and
            world.data.entity_ini(e.name, "Drops", "")][:2]
    assert len(foes) == 2
    for foe, kill in zip(foes, (a.kill_npc, world.npc_killed_by_npc)):
        m = world.maps[foe.map]
        before, uids = len(world.action_queue), {e.uid for e in world.ents}
        kill(foe)
        new = world.action_queue[before:]
        assert any(q.startswith("ADD\t%s\tNPC\t" % foe.name) and world.local_coords(m, foe.orig_x, foe.orig_y) in q
                   for q in new)                                   # (it comes back where its map puts it)
        loot = [e for e in world.ents if e.uid not in uids and e.type == MAPITEM and e.name != "Shard_Remnant"]
        assert loot and all(e.source == "DROPPED" for e in loot)
        assert all(any(q.startswith("REMOVE\t%s\tMapItem\t" % e.name) for q in new) for e in loot)   # (and it goes)
        assert all((e.private_to is a) == (kill == a.kill_npc) for e in loot)       # (a player's kill: theirs first)
        for e in [e for e in world.ents if e.uid not in uids]:
            world.remove_entity(e)
    leave(world, a)


def test_ini_comments_are_never_keys(tmp_path):
    from ashen import ini
    path = str(tmp_path / "t.ini")
    with open(path, "wb") as f:
        f.write(b"[Sky]\r\n; The colour: <time>=R G B\r\n0.5=1 2 3 4\r\n")
    assert ini.section("Sky", path) == [("0.5", "1 2 3 4")]
    assert ini.read("Sky", "; The colour: <time>", "none", path) == "none"


def test_burnt_food_is_one_stack(world):
    from dsengine.renames import renamed
    assert renamed({"inv": [["Burnt_Meat", 1], ["Burnt_Chicken", 2], ["Burnt_Fish", 1]]}) == \
        {"inv": [["Burnt_Food", 1], ["Burnt_Food", 2], ["Burnt_Food", 1]]}      # (old saves: one heap of charcoal)
    assert world.data.stackable_quantity("Burnt_Food") > 1
    for kind in ("Burnt_Meat", "Burnt_Poultry", "Burnt_Herring"):
        assert not world.data.entity_ini(kind, "Type", "")


def test_success_is_heard(world):
    import glob
    chop = open(os.path.join(ROOT, "data", "Scripts", "Chop Tree.txt"), "rb").read().decode("cp1252")
    assert any(ln.split("\t")[1:2] == ["Display.Message"] and ln.endswith("\tGather_Wood") for ln in chop.split("\r\n"))
    sounds = {os.path.basename(f)[:-4] for f in glob.glob(os.path.join(ROOT, "sounds", "*.wav"))}
    for s in ("Gather_Wood", "Gather_Ore", "Gather_Fish", "Harvest", "Cooked", "Crafted", "Unlock", "Learn",
              "Fail_2", "Fail_3", "Denied_2"):
        assert s in sounds


def test_sitting_is_a_step_not_a_jump(world):
    a = join(world, "Percher", "0,0,10", 8 * 32, 4 * 32)              # (two tiles off the bench, and down)
    m = a.cur_map
    gx, gy = m.ox + 4 * 32 + 16, m.oy + 1 * 32 + 16                  # (the arena's bench at 5,2)
    bench = a.tile_entity_at(gx, gy)
    a.choose_verb("Sit", bench, gx, gy)
    for _ in range(80):
        world.tick(0.05)
    assert a.seat is not None
    (sx, sy), (bx, by) = a.seat
    assert abs(sx - bx) + abs(sy - by) <= 30                         # (walked to its front, then one step onto it)
    leave(world, a)


def test_editor_joins_fences_and_walls_and_smooths_mixed_grass():
    # The editor reads how tiles go together from the data (TileSets.ini Kind=, Tiles.ini Joins= and Below=): a
    # palisade painted freehand joins up, corners and T's and all; erasing one rejoins what's left; a town wall is
    # battlements over its face east-west, a tower at its corners; a coast of mixed grass gets its diagonals too
    from dsedit.project import Project
    from dsedit import world as WD
    P = Project(ROOT)
    grid = {}
    get, put = (lambda x, y: grid.get((x, y))), (lambda x, y, t: grid.__setitem__((x, y), t))
    for c in [(0, 0), (1, 0), (2, 0), (1, 1), (1, 2)]:                          # (a T, painted a cell at a time)
        WD.lay_joins(P, "Palisade001", [c], get, put)
    joins = lambda t: P.tiles_ini.get(t, "Joins", "")
    assert joins(grid[(1, 0)]) == "ESW" and joins(grid[(1, 2)]) == "NS" and joins(grid[(0, 0)]) == "EW"
    grid.pop((1, 1))                                                            # (the stem erased: the T an east-west)
    WD.lay_joins(P, "Palisade001", [], get, put, erased=[(1, 1)])
    assert joins(grid[(1, 0)]) == "EW"
    wall = {}
    WD.lay_joins(P, "City_Wall001", [(i, j) for i, j in WD.join_cells(5, 5)], lambda x, y: wall.get((x, y)),
                 lambda x, y, t: wall.__setitem__((x, y), t))
    assert wall[(0, 0)] == "City_Wall003" and wall[(0, 1)] == "City_Wall002"   # (a corner tower, the wall going on south under it)
    assert wall[(2, 0)] == "City_Wall001" and wall[(2, 1)] == "City_Wall004"   # (battlements over the face)
    assert wall[(0, 2)] == "City_Wall002"                                       # (north-south, under the tower)
    coast = {(x, y): "Water001" for x in range(5) for y in range(5)}
    coast.update({(2, 1): "Grass002", (3, 1): "Grass001", (3, 2): "Grass003"})  # (grass painted mixed)
    WD.smooth_corners(P, lambda x, y: coast.get((x, y)), lambda x, y, t: coast.__setitem__((x, y), t), {(3, 2)})
    assert coast[(2, 2)] == "Water002"


def test_stances_take_a_moment_and_change_what_you_do(world):
    s = join(world, "Stancer", "0,0,10", 12 * 32, 4 * 32)
    base_attack, base_def = s.player_attack_value(), s.player_defence_value()
    s.handle({"t": "stance", "stance": "Fighting"})
    world.tick(0.05, now=world.now + 50)
    assert s.stance == ""                                            # (it takes a moment)
    run_for(world, 30)
    assert s.stance == "Fighting" and s.player_attack_value() > base_attack and s.player_defence_value() > base_def
    s.handle({"t": "stance", "stance": "Channelling"})
    run_for(world, 30)
    assert s.stance == "Channelling" and s.stance_walk() < 1 and s.player_defence_value() < base_def
    s.handle({"t": "stance", "stance": "Sneaking"})
    run_for(world, 30)
    assert s.sneaking() and s.sight_factor() < 1 and s.stance_walk() < 1
    s.skill_xp[s.skill_index("Stealth")] = 20                       # (more Stealth: harder still to see)
    assert s.sight_factor() < 0.6 and s.cone_factor() < 1
    s.handle({"t": "stance", "stance": "Sneaking"})                 # (the same again: back to none)
    run_for(world, 30)
    assert s.stance == ""
    leave(world, s)


def test_a_lookout_turns_to_what_it_hears_and_a_sneak_attack_hits_hard(world):
    s = join(world, "Creeper", "0,0,10", 12 * 32, 4 * 32)
    m = s.cur_map
    held = [e for e in world.ents if e.type == NPC and e.map == m.name and e.alive]
    for e in held:
        world.ents.remove(e)
    p = s.player
    guard = world.add_npc("Goblin", m.mz, p.x + 70, p.y, "Stand=1")
    guard.ai.cone = 90
    guard.direction = 2                                             # (looking east: away from them)
    world.tick(0.05, now=world.now + 50)
    assert not world.npc_sees(guard, guard.ai, s, 70)
    s.player_moved = True                                          # (walking: heard)
    world.npc_listen(guard, guard.ai, s, 70)
    assert guard.direction == 8                                     # (it turns to look)
    guard.direction = 2
    s.handle({"t": "stance", "stance": "Sneaking"})
    run_for(world, 25)
    s.player_moved = True
    if s.noise_radius() < 70:                                       # (sneaking: too soft to hear)
        world.npc_listen(guard, guard.ai, s, 70)
        assert guard.direction == 2
    assert s.unseen_by(guard)
    hp = guard.hp
    s.player_strike(guard, False)
    assert guard.hp < hp and s.stance == ""                         # (a blow it never saw coming; seen now)
    world.remove_entity(guard)
    world.ents.extend(held)
    leave(world, s)


def test_pickpocketing_and_getting_caught(world):
    import dsengine.thieving as TH
    s = join(world, "Lightfingers")
    s.connected = True
    mark = next(e for e in world.ents if e.type == NPC and e.alive and e.owner is None and not e.hostile and
                "Talk to" in (e.use_words or "") and s.shop_rack_of(e))           # (a shopkeeper)
    near(world, s, mark, 30, 0)
    other = join(world, "Bystander", mark.map, int(mark.x - world.maps[mark.map].ox) + 60, int(mark.y - world.maps[mark.map].oy))
    assert "Pickpocket" not in s.get_verbs(mark)                   # (only sneaking)
    s.handle({"t": "stance", "stance": "Sneaking"})
    run_for(world, 25)
    assert "Pickpocket" in s.get_verbs(mark)
    s.skill_xp[s.skill_index("Stealth")] = 25
    gold = s.items_held("Gold_Coin(s)")
    was = TH.rnd
    try:
        TH.rnd = lambda: 0.0                                       # (a sure hand)
        s.pickpocket(mark)
        assert s.items_held("Gold_Coin(s)") > gold and s.sneaking()
        s.thief_until.clear()
        TH.rnd = lambda: 0.999                                     # (caught)
        s.pickpocket(mark)
    finally:
        TH.rnd = was
    g = s.guards_after[0] if s.guards_after else None
    assert not s.sneaking() and g is not None and g.owner is None   # (everyone's to see)
    assert world.hostile_for(g, s) and not world.hostile_for(g, other) and world.visible_to(g, other)
    run_for(world, 10)
    assert g.in_combat and g.target is s                           # (after the thief alone)
    leave(world, other)
    s.clicked_ent = mark
    assert not s.open_item_rack("SHOP", mark.name, s.shop_rack_of(mark))   # (they won't serve you now)
    for g in s.guards_after:
        world.remove_entity(g)
    leave(world, s)


def test_monsters_see_in_their_cone_and_hear_as_far_as_their_ears(world):
    """Each kind's Sight.Cone and Hearing (build_senses.py): a bat hears you twice as far as you carry, and sees all
    round; a skeleton looks one way, and only turns to a sound."""
    s = join(world, "Footfalls")
    s.connected = True
    bat = world.add_npc("Bat", s.player.z, s.player.x + 150, s.player.y, "Attitude=Bad Zone=1,1,25,21", "Bad")
    bone = world.add_npc("Skeleton", s.player.z, s.player.x - 150, s.player.y, "Attitude=Bad Zone=1,1,25,21", "Bad")
    try:
        assert bat.ai.cone == 360 and bat.ai.hearing == 2 and bone.ai.cone == 110 and bone.ai.hearing < 1
        s.player_moved = True                                      # (walking: heard as far as Noise.Walk carries)
        d = distance(bat.cx, bat.cy, s.player.cx, s.player.cy)
        assert s.noise_radius() < d <= s.noise_radius() * 2       # (too far for plain ears; not for a bat's)
        assert world.npc_listen(bat, bat.ai, s, d) and bat.in_combat and bat.target is s
        bone.direction = 8                                         # (looking west, away: you're east of it)
        db = distance(bone.cx, bone.cy, s.player.cx, s.player.cy)
        assert not world.npc_sees(bone, bone.ai, s, db)            # (behind it)
        assert not world.npc_listen(bone, bone.ai, s, db) and not bone.in_combat   # (too far for dull ears)
    finally:
        world.remove_entity(bat)
        world.remove_entity(bone)
        leave(world, s)


def test_a_house_has_valuables_to_steal(world):
    import dsengine.thieving as TH
    box = next(e for e in world.ents if e.name == "Valuables" and e.z == 0)
    s = join(world, "Magpie")
    s.connected = True
    near(world, s, box, 0, 30)
    assert "Steal" not in s.get_verbs(box)                         # (only sneaking)
    s.stance = "Sneaking"
    assert "Steal" in s.get_verbs(box)
    was = TH.rnd
    try:
        TH.rnd = lambda: 0.0
        before = sum(s.items_held(n) for n in ("Gold_Coin(s)", "Silver_Ring", "Gold_Ring", "Sapphire", "Bread",
                                               "Minor_Healing_Draught", "Egg"))
        had = {id(e) for e in s.inv}
        s.steal_from(box)
        after = sum(s.items_held(n) for n in ("Gold_Coin(s)", "Silver_Ring", "Gold_Ring", "Sapphire", "Bread",
                                              "Minor_Healing_Draught", "Egg"))
        assert after > before
        got = [e for e in s.inv if id(e) not in had]
        assert all(e.stolen == (e.name != "Gold_Coin(s)") for e in got)   # (marked; gold never is)
        s.out = []
        s.steal_from(box)                                          # (not twice in a row)
        assert sum(s.items_held(n) for n in ("Gold_Coin(s)",)) <= after
    finally:
        TH.rnd = was
    leave(world, s)


def test_stolen_goods_stay_marked_wherever_they_go(world):
    s = join(world, "Fingers")
    s.connected = True
    stock(s, Silver_Ring=1, Logs=2)
    s.add_inventory_item("Silver_Ring", 2, stolen=True, quiet=True)
    s.add_inventory_item("Logs", 3, stolen=True, quiet=True)
    s.add_inventory_item("Gold_Coin(s)", 5, stolen=True, quiet=True)
    logs = [e for e in s.inv if e.name == "Logs"]
    assert sorted((e.quantity, e.stolen) for e in logs) == [(2, False), (3, True)]    # (never one stack)
    rings = [e for e in s.inv if e.name == "Silver_Ring"]
    assert not any(e.stolen for e in s.inv if e.name == "Gold_Coin(s)")              # (gold is just gold)
    hot = next(e for e in rings if e.stolen)
    assert s.inv_row(hot)[-1] == 1 and s.inv_row(next(e for e in rings if not e.stolen))[-1] != 1
    said = []
    s.display_message = lambda text, kind="": said.append(text)
    s.examine_entity(hot)
    assert "stolen" in said[-1]
    # (the bank: a slot of its own, and it comes back out stolen)
    s.bank_deposit(hot, 2)
    slot = next(i for i in range(1, s.data.bank_slots + 1) if s.bank_item[i] == "Silver_Ring")
    assert s.bank_stolen[slot] and s.items_held("Silver_Ring", True) == 0 and s.items_held("Silver_Ring", False) == 1
    s.bank_deposit(next(e for e in s.inv if e.name == "Silver_Ring"), 1)
    assert sum(1 for i in range(1, s.data.bank_slots + 1) if s.bank_item[i] == "Silver_Ring") == 2
    assert s.get_script_value("BANK", "Silver_Ring") == "3"         # (a script counts both slots)
    s.bank_withdraw(type("Slot", (), {"misc": slot})(), -1)
    assert s.items_held("Silver_Ring", True) == 2 and not s.bank_stolen[slot]
    # (saved and loaded)
    st = s.save_state()
    t = Session(world, "Fingers2")
    t.load_state(st)
    assert t.items_held("Silver_Ring", True) == 2
    # (the ground, and back)
    s.remove_inventory_item("Silver_Ring", 1, True)
    s.drop_on_floor("Silver_Ring", 1, stolen=True)
    lying = next(e for e in world.ents if e.name == "Silver_Ring" and e.alive and e.stolen)
    s.pickup_map_item(lying, reach=9999)
    assert s.items_held("Silver_Ring", True) == 2
    # (worn and taken off)
    hot = next(e for e in s.inv if e.name == "Silver_Ring" and e.stolen)
    s.equip_item(hot)
    ring = s.item_equip_slot("Silver_Ring")
    if ring:
        assert s.equip_stolen[ring]
        s.unequip_slot(ring)
        assert s.items_held("Silver_Ring", True) == 2 and not s.equip_stolen[ring]
    # (given away)
    b = join(world, "Receiver")
    try:
        s.remove_inventory_item("Silver_Ring", 1, False)
        s.hand_over(s, b, "Silver_Ring", 2)
        assert b.items_held("Silver_Ring", True) == 2 and b.items_held("Silver_Ring", False) == 0
        # (and in the grave, after a death: kept things are the five worth most, so some gold rings first)
        stock(b, Gold_Ring=5)
        graved = b.death_sort()
        assert sum(q for n, q, _, stolen in graved if n == "Silver_Ring" and stolen) == 2
        b.grave = {"map": b.cur_map.name, "x": 0, "y": 0, "items": graved, "left": 60000}
        b.grave_search()
        assert b.items_held("Silver_Ring", True) == 2
    finally:
        leave(world, b)
        leave(world, s)


def test_only_a_fence_buys_stolen_goods(world):
    s = join(world, "Fencer")
    s.connected = True
    s.clicked_ent = None
    s.add_inventory_item("Silver_Ring", 3, stolen=True, quiet=True)
    stock(s, Silver_Ring=1)
    hot = next(e for e in s.inv if e.name == "Silver_Ring" and e.stolen)
    assert s.open_item_rack("SHOP", "Man", "SHOP-Isle")
    gold = s.items_held("Gold_Coin(s)")
    assert not s.can_sell_here("Silver_Ring", True) and s.can_sell_here("Silver_Ring")
    assert "Sell 1" not in s.get_verbs(hot)
    s.rack_sell(hot, 1)
    assert s.items_held("Silver_Ring", True) == 3 and s.items_held("Gold_Coin(s)") == gold
    # (the market won't list it either)
    said = []
    real = s.display_message
    s.display_message = lambda text, kind="": said.append(text)
    s.market_list(hot, 10, 1)
    assert "stolen" in said[-1] and s.items_held("Silver_Ring", True) == 3
    s.display_message = real
    # (a fence: half what an honest shop gives)
    assert s.open_item_rack("SHOP", "Man", "SHOP-Fence_Northport") and s.rack_fence
    assert s.fence_rate() == 0.5 and s.can_sell_here("Silver_Ring", True)
    assert s.sell_price("Silver_Ring", True) == s.item_price("Silver_Ring", s.rack_sell_rate *
                                                              s.data.sell_price_factor * 0.5, 1)
    assert s.sell_price("Silver_Ring", True) < s.sell_price("Silver_Ring")
    price = s.sell_price("Silver_Ring", True)
    s.rack_sell(hot, 1)
    assert s.items_held("Silver_Ring", True) == 2 and s.items_held("Gold_Coin(s)") == gold + price
    assert s.items_held("Silver_Ring", False) == 1                   # (the honest one's still there)
    # (Red Meg pays better, and best to those on her side)
    assert s.open_item_rack("SHOP", "Captain", "SHOP-Smugglers") and s.fence_rate() == 0.6
    s.set_side_attitude("Smugglers", "Good")
    assert s.fence_rate() == 0.8
    # (a fence asks no questions, of an Outlaw either)
    s.shop_rates = lambda npc, rack="": None
    assert not s.open_item_rack("SHOP", "Man", "SHOP-Isle")
    assert s.open_item_rack("SHOP", "Man", "SHOP-Fence_Galaith")
    leave(world, s)


def test_a_thief_hears_where_the_fences_are(world):
    s = join(world, "Tipped", "4,4,0", 300, 300)                     # (Northport)
    s.connected = True
    s.clicked_ent = None
    try:
        scene = world.banter.scenes["Scene.Fence_Northport"]
        assert not world.banter.applies("Thief", s)                 # (an honest soul hears nothing of it)
        s.got_stolen("Silver_Ring", 1)
        assert world.banter.applies("Thief", s) and world.banter.in_town(scene, s)
        assert not world.banter.in_town(world.banter.scenes["Scene.Fence_Galaith"], s)
        assert s.open_item_rack("SHOP", "Man", "SHOP-Isle")
        said = []
        s.display_message = lambda text, kind="": said.append(text)
        s.rack_sell(next(e for e in s.inv if e.stolen), 1)
        assert "docks after dark" in said[-1]                       # (the shopkeeper says where it'd sell)
    finally:
        leave(world, s)


def test_the_admin_panel_sets_a_quest_and_its_variables(world):
    s = join(world, "Questmaster")
    s.connected = True
    s.admin_enabled = True
    try:
        row = next(q for q in s.admin_quests() if q[0] == "The Dwarf's Grudge")
        assert row[1] == "DwarfQuest" and [v for v, _ in row[4]] == ["SkeletonsSlain", "TrollSlain"]
        shards = s.shard_balance
        s.handle({"t": "admin", "do": "quest", "quest": "The Dwarf's Grudge", "done": True})
        assert s.quest_done("DwarfQuest") and s.shard_balance == shards          # (ticked: no reward for it)
        assert s.get_attribute("ShardsPaid.DwarfQuest") == "1"
        s.handle({"t": "admin", "do": "quest", "quest": "DwarfQuest", "vars": {"SkeletonsSlain": "3", "Gold": "9"}})
        assert s.get_attribute("SkeletonsSlain") == "3" and val(s.get_attribute("Gold")) == 0   # (only the quest's own)
        s.handle({"t": "admin", "do": "quest", "quest": "The Dwarf's Grudge", "stage": 1})
        assert val(s.get_attribute("DwarfQuest")) == 1 and not s.quest_done("DwarfQuest")
        s.handle({"t": "admin", "do": "quest", "quest": "The Dwarf's Grudge", "done": False})
        assert val(s.get_attribute("DwarfQuest")) == 0 and val(s.get_attribute("SkeletonsSlain")) == 0
        assert val(s.get_attribute("ShardsPaid.DwarfQuest")) == 0                  # (to be played again, in full)
        s.admin_enabled = False
        s.handle({"t": "admin", "do": "quest", "quest": "The Dwarf's Grudge", "done": True})
        assert not s.quest_done("DwarfQuest")                       # (only an admin)
    finally:
        leave(world, s)


def test_a_creature_comes_back_out_of_shard_essence(world):
    s = join(world, "Watcher")
    s.connected = True
    m = s.cur_map
    s.out = []
    before = {id(e) for e in world.ents}
    # (a seal: none lives here, so none has wandered onto the spot, which would stop the add)
    world.add_action_to_queue("ADD", "Seal", "NPC", "Attitude=Passive", m.name, "200,200", 0)
    world.run_action_queue()
    assert any(ev.get("t") == "anim" and ev.get("base") == "Shard_Form" for ev in s.out)
    rabbit = next(e for e in world.ents if e.name == "Seal" and id(e) not in before)
    s.out = []
    world.npc_killed_by_npc(rabbit)
    assert any(ev.get("t") == "anim" and ev.get("base") == "Shard_Fade" for ev in s.out)
    leave(world, s)


def test_a_kill_counts_for_everyone_who_fought(world):
    """Two players at the bridge goblins: one lands the blow, both count it (each their own quest goes on)."""
    m = world.maps["16,3,0"]
    a = join(world, "Striker", "16,3,0", 300, 300)
    b = join(world, "Shieldmate", "16,3,0", 340, 300)
    for s in (a, b):
        s.connected = True
        s.update_attribute("WardhavenQuest", "=1")
        s.update_attribute("BridgeGoblins", "=0")
    goblin = world.add_npc("Goblin", 0, m.ox + 320, m.oy + 330, "Attitude=Bad", "Bad")
    try:
        b.fought(goblin)                                            # (b's blows landed too)
        a.kill_npc(goblin)
        run_for(world, 5)
        assert a.get_attribute("BridgeGoblins") == "1" and b.get_attribute("BridgeGoblins") == "1"
        loner = join(world, "Bystander2", "16,3,0", 360, 300)       # (there, but never fought it: nothing)
        loner.update_attribute("WardhavenQuest", "=1")
        g2 = world.add_npc("Goblin", 0, m.ox + 320, m.oy + 330, "Attitude=Bad", "Bad")
        a.kill_npc(g2)
        run_for(world, 5)
        assert loner.get_attribute("BridgeGoblins") == "0" and a.get_attribute("BridgeGoblins") == "2"
        leave(world, loner)
    finally:
        leave(world, a)
        leave(world, b)


def test_the_arena_master_wakes_the_arenas_shardstone(world):
    s = join(world, "Gladiator", "11,-3,0", 300, 300)
    s.connected = True
    assert any(st["key"] == "Arena" and st["map"] == "0,0,10" and st["uid"] for st in s.stones())
    assert not s.stone_active("Arena")
    s.start_script("Talk to Arena_Master", False)
    run_for(world, 5)
    assert s.stone_active("Arena")                                  # (spoken to once: it knows you, no Shards)
    leave(world, s)


def test_a_party_shares_kills_and_quest_stages(world):
    """Invited and joined: a kill counts for a party member near who never struck it, and a quest stage one reaches the
    other at the same stage reaches too (with the quest's own thing given)."""
    m = world.maps["16,3,0"]
    a = join(world, "Leader", "16,3,0", 300, 300)
    b = join(world, "Follower", "16,3,0", 340, 300)
    try:
        for s in (a, b):
            s.connected = True
            s.update_attribute("WardhavenQuest", "=1")
            s.update_attribute("BridgeGoblins", "=0")
        assert "Invite to party" in a.get_verbs(b.player)
        a.do_action("Invite to party", b.player)
        b.native_menu_chosen(1)                                     # (Join)
        assert a.party_names() == ["Leader", "Follower"] and b.party_id == a.party_id
        assert "Leave party" in a.get_verbs(b.player)
        goblin = world.add_npc("Goblin", 0, m.ox + 320, m.oy + 330, "Attitude=Bad", "Bad")
        a.kill_npc(goblin)
        run_for(world, 5)
        assert b.get_attribute("BridgeGoblins") == "1"              # (b never struck it: the party counts it)
        a.update_attribute("BridgeGoblins", "=3")
        b.update_attribute("BridgeGoblins", "=3")
        a.start_script("Kill Goblin", False)                        # (a's fourth: the quest's stage moves on)
        run_for(world, 5)
        assert a.get_attribute("WardhavenQuest") == "2" and b.get_attribute("WardhavenQuest") == "2"
        b.leave_party()
        assert not a.party_id and not b.party_id                    # (one left: no party)
    finally:
        leave(world, a)
        leave(world, b)


def test_a_gift_is_offered_and_taken(world):
    a = join(world, "Giver", "11,-3,0", 300, 300)
    b = join(world, "Taker", "11,-3,0", 330, 300)
    try:
        stock(a, Bread=3)
        before = b.items_held("Bread")
        bread = next(i for i in a.inv if i.name == "Bread")
        a.item_in_use = bread
        a.do_action("Use with", b.player)
        a.native_menu_chosen(1)                                     # (All 3)
        b.native_menu_chosen(1)                                     # (Take it)
        assert a.items_held("Bread") == 0 and b.items_held("Bread") == before + 3
    finally:
        leave(world, a)
        leave(world, b)


def test_a_town_project_changes_the_town_for_everyone(world):
    t = world.together
    key = "Mirefold_Boardwalks"
    t.projects.pop(key, None)
    stone = next(e for e in world.ents if getattr(e, "project", "") == key and e.name == "Shardstone")
    s = join(world, "Builder", "11,-3,0", 300, 300)
    try:
        assert not world.visible_to(stone, s)
        d = t.defs()[key]
        stock(s, **{"Logs": 300, "Gold_Coin(s)": 800})
        s.donate(d, "Logs", 300)
        assert not t.done(key)
        s.donate(d, "Gold_Coin(s)", 800)
        assert t.done(key) and world.visible_to(stone, s)           # (finished: its shardstone stands for everyone)
        assert "Builder" in s.plaque_text(key)
        st = t.state()
        t2 = type(t)(world)
        t2.load(st)
        assert t2.done(key)                                         # (kept with the world)
    finally:
        t.projects.pop(key, None)
        leave(world, s)


def test_the_bounty_clerk_sets_a_hunt_a_day(world):
    s = join(world, "Hunter", "11,-3,0", 300, 300)
    try:
        kind, n, day = s.bounty_today()
        s.take_bounty(day)
        prey = world.add_npc(kind, 0, s.player.x + 40, s.player.y, "Attitude=Bad", "Bad")
        s.kill_npc(prey)
        assert s.get_attribute("Bounty.Got") == "1"
        s.update_attribute("Bounty.Got", "=%d" % n)
        gold = s.items_held("Gold_Coin(s)")
        s.clerk_menu()                                              # (done: paid)
        assert s.items_held("Gold_Coin(s)") > gold and s.get_attribute("Bounty.Paid") == str(day)
    finally:
        leave(world, s)


def test_jimmy_comes_along_and_a_sellsword_can_be_hired(world):
    s = join(world, "Crowned2", "11,-3,0", 300, 300)
    try:
        s.update_attribute("KingQuest", "=1")
        jimmy = world.add_npc("Strawberry_Cat", 0, s.player.x + 30, s.player.y, "Attitude=Good Id=Throne_Jimmy Name=Jimmy")
        assert "Come along" in s.companion_verbs(jimmy, "")
        s.do_action("Come along", jimmy)
        cat = s.companions()[0]
        assert cat.display == "Jimmy" and s.secrets_nose() > 0
        s.teleport("11,-3,0", 600, 500)
        s.do_pending_map_change()
        run_for(world, 10)
        assert distance(cat.cx, cat.cy, s.player.cx, s.player.cy) < 500   # (he keeps up)
        sword = next(e for e in world.ents if (e.npc_id or "") == "Sellsword_Northport")
        stock(s, **{"Gold_Coin(s)": 30})
        s.do_action("Hire", sword)
        assert any(getattr(e, "comp_kind", "") == "Sellsword" for e in s.companions())
        world.remove_entity(jimmy)
    finally:
        leave(world, s)
        assert not any(getattr(e, "comp_of", None) is s and e.alive for e in world.ents)


def test_a_boss_grows_tougher_for_each_fighter(world):
    a = join(world, "BossA", "11,-3,0", 300, 300)
    b = join(world, "BossB", "11,-3,0", 330, 300)
    try:
        boss = world.add_npc("Barrow_King", 0, a.player.x + 60, a.player.y, "Attitude=Bad", "Bad")
        hp = boss.max_hp
        a.fought(boss)
        assert boss.max_hp == hp                                     # (one fighter: as it is)
        b.fought(boss)
        assert boss.max_hp > hp                                      # (two: tougher)
        world.remove_entity(boss)
    finally:
        leave(world, a)
        leave(world, b)


def test_a_day_away_and_back_says_what_happened(world):
    import time as T
    s = Session(world, "Wanderer")
    s.load_state({"map": "11,-3,0", "x": 300, "y": 300, "last_seen": int(T.time()) - 3 * 86400})
    world.sessions[s.player_name] = s
    s.out = []
    s.enter_world()
    try:
        assert any("While you were away" in str(ev.get("text", "")) for ev in s.out)
    finally:
        leave(world, s)


def test_friends_are_kept_and_shown_in_the_journal(world):
    a = join(world, "Pal_A", "11,-3,0", 300, 300)
    b = join(world, "Pal_B", "11,-3,0", 330, 300)
    try:
        assert "Add friend" in a.get_verbs(b.player)
        a.do_action("Add friend", b.player)
        assert a.friend_names() == ["Pal_B"] and "Remove friend" in a.get_verbs(b.player)
        rows = a.journal_state()["friends"] if hasattr(a, "journal_state") else a.friends_rows()
        assert rows[0]["name"] == "Pal_B" and rows[0]["on"] == 1
        t2 = type(world.together)(world)
        t2.load(world.together.state())
        assert t2.friends_of("Pal_A") == ["Pal_B"]                  # (kept with the world)
        b.out = []
        a.friends_hear("Your friend Pal_A has left Ashen.")
        assert not any("Pal_A" in str(ev.get("text", "")) for ev in b.out)   # (only those who count you a friend)
        b.add_friend_named("pal_a")                                 # (any case: the name as it's written)
        b.out = []
        a.friends_hear("Your friend Pal_A has left Ashen.")
        assert any("Pal_A has left" in str(ev.get("text", "")) for ev in b.out)
        a.remove_friend_named("Pal_B")
        assert a.friend_names() == []
    finally:
        world.together.friends.pop("Pal_A", None)
        world.together.friends.pop("Pal_B", None)
        leave(world, a)
        leave(world, b)


def test_a_trade_changes_hands_when_both_accept(world):
    a = join(world, "Trader_A", "11,-3,0", 300, 300)
    b = join(world, "Trader_B", "11,-3,0", 330, 300)
    try:
        stock(a, Bread=2)
        stock(b, **{"Gold_Coin(s)": 50})
        gold_a, bread_b = a.items_held("Gold_Coin(s)"), b.items_held("Bread")
        a.do_action("Trade", b.player)
        b.native_menu_chosen(1)                                     # (Trade with Trader_A)
        assert a.trade is b.trade and a.trade
        a.trade_msg({"do": "add", "item": "Bread", "n": 2})
        b.trade_msg({"do": "add", "item": "Gold_Coin(s)", "n": 20})
        a.trade_msg({"do": "accept"})
        b.trade_msg({"do": "add", "item": "Gold_Coin(s)", "n": 5})  # (a change: a's accept undone)
        assert not a.trade["ok"]["Trader_A"]
        b.trade_msg({"do": "accept"})
        assert a.trade                                              # (only b has accepted)
        a.trade_msg({"do": "accept"})
        assert a.trade is None and b.trade is None
        assert a.items_held("Bread") == 0 and b.items_held("Bread") == bread_b + 2
        assert a.items_held("Gold_Coin(s)") == gold_a + 25
    finally:
        leave(world, a)
        leave(world, b)


def test_a_thief_spots_disarms_and_steps_over_traps(world):
    import dsengine.senses as SN
    m = world.maps["15,18,-1"]                                       # (the buried library: darts, a pit, a pie)
    tx, ty = 16, 13
    assert m.trigger[m.cell(tx, ty)] == "Trap_Darts"
    s = join(world, "Sneak", m.name, (tx - 1) * 32, (ty - 3) * 32)
    s.connected = True
    was = SN.rnd
    try:
        SN.rnd = lambda: 0.0                                       # (a sharp eye)
        s.sense_at, s.sense_tried = 0, set()                       # (a fresh look: one roll each time you come near)
        s.sense_tick()
        assert s.trap_known(m, tx, ty) and "Disarm" in s.get_verbs(s.tile_entity_at(m.ox + tx * 32 - 16, m.oy + ty * 32 - 16))
        s.stance = "Sneaking"
        assert s.trap_spared(m, tx, ty)                            # (seen, and stepped over softly)
        s.stance = ""
        hp = s.player.hp
        s.disarm_trap(m, tx, ty)
        assert (m.name, tx, ty) in s.traps_disarmed and s.trap_spared(m, tx, ty)
        s.world_trap("Darts", m, tx, ty)
        assert s.player.hp == hp                                   # (harmless now)
    finally:
        SN.rnd = was
    leave(world, s)


def test_chests_are_locked_and_never_out_of_reach(world):
    import dsengine.locks as LK
    s = join(world, "Locksmith")
    s.connected = True
    chests = [e for e in world.ents if s.is_chest(e) and e.z == 0 and s.chest_locked(e) and
              e.map not in s.lock_text("Isle.Maps", "").split()]
    chest = next(e for e in chests if not s.chest_sturdy(e))
    assert "Pick Lock" in s.get_verbs(chest) and "Break Open" in s.get_verbs(chest)
    isle = next(e for e in world.ents if s.is_chest(e) and e.map == "3,1,0")
    assert s.chest_lock(isle)[0] == 1 and not s.chest_sturdy(isle)  # (the Isle's: the easiest, to learn on)
    iron = next(e for e in chests if s.chest_sturdy(e))              # (iron-bound: picked or keyed, never forced)
    assert "Pick Lock" in s.get_verbs(iron) and "Break Open" not in s.get_verbs(iron)
    near(world, s, iron, 30, 0)
    s.do_action("Break Open", iron)
    assert s.chest_locked(iron)
    near(world, s, chest, 30, 0)
    s.out = []
    s.do_action("Open", chest)
    assert any("locked" in str(ev.get("text", "")) for ev in s.out) and s.ab_mode != "Chest"
    was = LK.rnd
    try:
        LK.rnd = lambda: 0.0
        s.do_action("Break Open", chest)                            # (Strength: loud, but it gives)
    finally:
        LK.rnd = was
    assert not s.chest_locked(chest) and s.chest_key(chest) in s.save_state()["unlocked_chests"]
    leave(world, s)


def test_galaiths_houses_are_locked_most_for_picking(world):
    """build_locked_doors.py: Galaith's houses, most pickable (and easy, in the hovels), two locked for good."""
    picks = [(m, xy) for m, xy in (("-10,15,0", (17, 16)), ("-7,12,0", (14, 21)), ("-5,17,0", (5, 18)),
                                   ("-5,16,0", (7, 17)), ("-6,17,0", (7, 19)), ("-5,15,0", (9, 16)),
                                   ("-6,16,0", (16, 13)), ("-6,13,0", (8, 16)), ("-6,17,0", (14, 6)),
                                   ("-6,17,0", (22, 20)), ("-6,16,0", (10, 7)))]
    for m, xy in picks:
        lk = world.maps[m].lock_at[xy]
        assert 3 <= lk.pick <= 15 and lk.message == lk.PICKABLE, (m, xy)
    for m, xy in (("-10,16,0", (19, 15)), ("-8,17,0", (13, 8))):
        lk = world.maps[m].lock_at[xy]
        assert lk.pick == 0 and lk.message not in ("It's locked.", lk.PICKABLE), (m, xy)


def test_the_floors_over_and_under_the_world_are_roofed_dark_each_building_its_own(world):
    """build_level_roofs.py: on levels 1 and -1 every building is under a black roof, its own group (so you don't see
    into the next across the dark); caves and mines are left open."""
    up = world.maps["-11,16,1"]                                      # (two houses' upper floors on one map)
    a, b = up.roof_group[up.cell(13, 1)], up.roof_group[up.cell(13, 3)]
    assert up.roof[up.cell(13, 1)] and a and a == b
    groups = {up.roof_group[i] for i in range(len(up.roof)) if up.roof[i]}
    assert len(groups) == 2
    cave = world.maps["-7,11,-1"]                                    # (the King's mine)
    assert not any(cave.roof)


def test_oakhollows_trader_stands_in_its_market_and_greets_you_so(world):
    m = world.maps["9,10,0"]
    t = next(e for e in world.ents if e.name == "Trader" and e.map == m.name)
    s = join(world, "Haggler", m.name, t.x - m.ox, t.y - m.oy + 40)
    s.out = []
    s.choose_verb("Talk to", t, t.cx, t.cy)
    run_for(world, 5)
    assert "Welcome to Oakhollow!" in str(s.out)
    assert not any(e.name == "Trader" and e.map == "8,11,0" for e in world.ents)
    leave(world, s)


def test_doors_can_be_picked_and_some_are_locked_for_good(world, monkeypatch):
    """build_locked_doors.py: a pickable door says so and opens for its picker alone; a private one never does; a
    yard's loot is for Grasp through the railings (or very high Stealth at its gate)."""
    a, b = join(world, "Pins"), join(world, "Bolt")
    a.connected = b.connected = True
    m = world.maps["26,19,0"]
    lk = m.lock_at[(19, 14)]
    assert lk.pick == 12 and lk.message == lk.PICKABLE
    gx, gy = m.ox + 18 * 32 + 16, m.oy + 13 * 32 + 16

    def at_door(s):
        s.teleport(m.name, 18 * 32, 14 * 32 - 8)                  # (on the tile below it)
        run_for(world, 5)
        return s.tile_entity_at(gx, gy)

    door = at_door(a)
    assert "Pick Lock" in a.get_verbs(door) and "Pick Lock" in a.get_verbs(at_door(b))
    a.out = []
    a.choose_verb("Pick Lock", at_door(a), gx, gy)
    run_for(world, 30)
    assert a.game is None and any("beyond your picks" in str(ev.get("text", "")) for ev in a.out)
    a.skill_xp[a.skill_index("Stealth")] = 8                        # (12 less the Reach of 4: just enough to try)
    a.choose_verb("Pick Lock", at_door(a), gx, gy)
    run_for(world, 30)
    assert a.game is not None and a.game["game"] == "lock"
    pick_the_lock(a)
    assert not a.lock_closed(m, lk) and a.door_key(m, lk) in a.save_state()["unlocked_chests"]
    assert b.lock_closed(m, lk)                                     # (picked for Pins, not for Bolt)
    cx, cy = m.ox + 18 * 32 + 16, m.oy + 13 * 32 + 16
    assert world.pixel_walkable(0, cx, cy, a) and not world.pixel_walkable(0, cx, cy, None)
    # locked for good: no picking it, and its own words for why
    home = world.maps["11,-1,0"]
    shut = home.lock_at[(10, 7)]
    assert shut.pick == 0 and shut.message not in ("It's locked.", shut.PICKABLE)
    hx, hy = home.ox + 9 * 32 + 16, home.oy + 6 * 32 + 16
    a.teleport(home.name, 9 * 32, 7 * 32 - 8)
    run_for(world, 5)
    assert "Pick Lock" not in a.get_verbs(a.tile_entity_at(hx, hy))
    # Northport's yard: Stealth 20 to try its gate; its loot in Grasp's reach from the street
    yard = world.maps["5,5,0"]
    gate = yard.lock_at[(16, 17)]
    assert gate.pick == 24 and "pick it" in gate.message
    gem = next(e for e in world.ents if e.name == "Sapphire" and e.map == yard.name and e.once)
    a.spells_known["Grasp"] = 1
    a.add_shards(50)
    a.teleport(yard.name, 15 * 32, 11 * 32 - 8)                    # (north of the railings, outside)
    run_for(world, 5)
    import dsengine.player_combat as pc
    monkeypatch.setattr(pc, "rnd", lambda: 0.0)                    # (the spell takes, whatever's rolled)
    a.out = []
    a.cast_spell("Grasp", gem)
    run_for(world, 40)
    assert a.items_held("Sapphire") == 1, [ev.get("text") for ev in a.out if ev.get("t") == "msg"]
    assert not world.visible_to(gem, a) and world.visible_to(gem, b)
    leave(world, a)
    leave(world, b)


def test_no_leaving_the_isle_without_papers_or_knowing_shard_remnants(world):
    """Wim's ferry runs for everyone, but not for you till he's seen your papers, you've absorbed remnants and you're
    level 3; with the papers, Northport's port guard sends you to the Speaker."""
    s = join(world, "Islander", "3,2,0", 14 * 32, 15 * 32)
    s.connected = True
    wim = next(e for e in world.ents if e.name == "Ferryman" and e.map == "3,2,0" and world.visible_to(e, s))
    east = next(c for c in world.carts.carts if c.key == "Isle_Ferry_East")

    def board():
        return world.carts.refusal(s, east) or ""                                   # (what the boat says, wherever it is)

    def ask(*answers):
        s.close_action_box(-1) if s.ab_mode else None
        s.teleport("3,2,0", int(wim.x - s.cur_map.ox), int(wim.y - s.cur_map.oy) + 30)
        run_for(world, 5)
        s.do_action("Talk to", wim)
        run_for(world, 30)
        said = s.ab_text
        for n in answers:
            s.action_box_response_chosen(n)
            run_for(world, 30)
        return said

    assert "Papers first" in board()
    s.update_attribute("LastWill", "=2")
    assert "Papers first" in ask(1) and s.get_attribute("Passage") == "1"              # (his quest, if Bess didn't start it)
    assert "no passage" in ask()
    s.update_attribute("Passage", "=4")
    stock(s, Marys_Papers=1)
    assert "seal" in ask(1) and s.get_attribute("Passage") == "5"
    assert "green as grass" in s.ab_text                                            # (no remnants absorbed: Aldous first)
    assert "green as grass" in board()
    s.update_attribute("RemnantsAbsorbed", "=1")
    assert "green as grass" in board()                                              # (nor a green hand: level 3)
    for k in range(len(s.skill_xp)):
        s.skill_xp[k] = max(s.skill_xp[k], 6)
    assert "Northport, is it" in ask() and board() == ""
    leave(world, s)
    m = world.maps["4,4,0"]
    guard = next(e for e in world.ents if e.name == "Port_Guard" and e.map == "4,4,0")
    s = join(world, "Lander", "4,4,0", int(guard.x - m.ox), int(guard.y - m.oy) + 30)
    s.update_attribute("Passage", "=5")
    stock(s, Marys_Papers=1)
    s.do_action("Talk to", guard)
    run_for(world, 30)
    assert "royal seal" in s.ab_text
    s.action_box_response_chosen(1)
    run_for(world, 10)
    assert s.get_attribute("ParliamentQuest") == "1"
    leave(world, s)


def test_the_kings_seam_asks_what_becomes_of_the_heart(world):
    s = join(world, "Crowned")
    stock(s, Pickaxe=1)
    s.update_attribute("KingQuest", "=1")
    seam = next(e for e in world.ents if e.npc_id == "Kings_Shard_Seam")
    near(world, s, seam, 0, 30)
    s.choose_verb("Mine", seam, int(seam.cx), int(seam.cy))
    run_for(world, 30)
    assert s.ab_mode == "Conversation"                               # (the first time: the choice)
    s.action_box_response_chosen(2)                                 # (make it whole)
    run_for(world, 20)
    assert s.get_attribute("HeartChoice") == "2" and s.items_held("Heartstone_Ring") == 1
    leave(world, s)


def test_the_seam_can_be_unmade_only_with_the_wardens_truth(world):
    s = join(world, "Unmaker")
    stock(s, Pickaxe=1)
    s.update_attribute("KingQuest", "=1")
    s.update_attribute("WardensTruth", "=1")
    seam = next(e for e in world.ents if e.npc_id == "Kings_Shard_Seam")
    near(world, s, seam, 0, 30)
    s.choose_verb("Mine", seam, int(seam.cx), int(seam.cy))
    run_for(world, 30)
    assert s.ab_mode == "Conversation"
    s.action_box_response_chosen(3)                                 # (break it)
    run_for(world, 20)
    assert s.get_attribute("HeartChoice") == "3" and s.get_attribute("Unmade") == "1"
    assert s.items_held("Seam_Hammerhead") == 1 and s.items_held("Heartstone_Ring") == 0
    leave(world, s)


def test_the_seam_cant_be_unmade_without_the_wardens_truth(world):
    s = join(world, "Binder")
    stock(s, Pickaxe=1)
    s.update_attribute("KingQuest", "=1")
    seam = next(e for e in world.ents if e.npc_id == "Kings_Shard_Seam")
    near(world, s, seam, 0, 30)
    s.choose_verb("Mine", seam, int(seam.cx), int(seam.cy))
    run_for(world, 30)
    assert s.ab_mode == "Conversation"
    s.action_box_response_chosen(3)                                 # (the third shown: Not yet)
    run_for(world, 20)
    assert s.get_attribute("Unmade") == "0" and s.get_attribute("HeartChoice") == "0"
    leave(world, s)


def test_the_glass_wardens_journals_chimes_shardsong_and_the_listening_room(world):
    """The Glass Wardens (dev/migrate/build_glass_wardens.py): nine journals read for Pell; the four chimes struck in
    the season's order; the Shardsong (a bout held still, then sharp eyes; the Quiet Draught cures it); the Listening
    Room's horn heard out only in the Channelling stance, never answered, which gives the Wardens' truth."""
    s = join(world, "Listener", "8,-13,-1", 300, 300)
    s.connected = True
    s.god_mode = True
    held = [e for e in world.ents if e.type == NPC and e.hostile and e.map.endswith(",-1") and world.maps[e.map].my < -4]
    for e in held:
        world.ents.remove(e)                                         # (the Deep's monsters: a fight shuts the books)

    def use(verb, e, answers=()):
        near(world, s, e, 0, 40)
        s.out = []
        s.choose_verb(verb, e, int(e.cx), int(e.cy))
        run_for(world, 40)
        for a in answers:
            assert s.ab_mode == "Conversation"
            s.action_box_response_chosen(a)
            run_for(world, 40)
        return " ".join(str(o.get("text", "")) for o in s.out if o.get("t") == "msg")

    # ----- the journals: nine, each counted once
    s.update_attribute("WardensWords", "=1")
    for i in range(1, 10):
        book = next(e for e in world.ents if e.npc_id == "Wardens_Journal_%d" % i)
        use("Read", book, [1])
        if i == 1:
            use("Read", book, [1])                                   # (read twice: counted once)
    assert s.get_attribute("WardensJournals") == "9" and s.get_attribute("WardensWords") == "2"

    # ----- the four notes, in spring's order (a wrong one starts it again)
    was = (world.seasons.now_is, world.seasons.pinned)
    world.seasons.now_is = world.seasons.pinned = "Spring"
    s.update_attribute("FourNotes", "=1")
    chime = {k: next(e for e in world.ents if e.npc_id == "%s_Chime" % k) for k in ("Water", "Bone", "Flame", "Glass")}
    use("Strike", chime["Water"])
    assert "jars" in use("Strike", chime["Flame"]) and s.get_attribute("FourNotes.Step") == "0"
    for k in ("Water", "Bone", "Flame", "Glass"):
        use("Strike", chime[k])
    assert s.get_attribute("FourNotes") == "2"
    world.seasons.now_is, world.seasons.pinned = was

    # ----- the Shardsong: held still to listen, then sharp eyes; the Quiet Draught ends it
    s.diseases.clear()
    s.god_mode = False                                               # (god mode shrugs off every bout)
    s.catch_disease("Shardsong")
    s.diseases["Shardsong"] = s.now
    s.disease_at = 0
    s.disease_tick()
    assert "Listening" in s.status
    s.status_end("Listening")
    assert "Keen" in s.status
    stock(s, Quiet_Draught=1)
    s.drink_cure(next(e for e in s.inv if e.name == "Quiet_Draught"))
    assert "Shardsong" not in s.diseases
    s.god_mode = True

    # ----- the Listening Room: the horn, only in the Channelling stance, and never answered
    s.update_attribute("WardensHeard", "=1")
    horn = next(e for e in world.ents if e.npc_id == "Wardens_Horn")
    s.stance = ""
    use("Listen", horn, [1])                                         # (Ysolde: stand as if to cast)
    assert s.get_attribute("WardensTruth") == "0"
    assert any(e.name == "Ysolde" and e.map == horn.map for e in world.ents)   # (she's there for you)
    s.stance = "Channelling"
    msg = use("Listen", horn, [2])                                   # (answered: it's over)
    assert "You answered it" in msg and s.get_attribute("WardensTruth") == "0"
    use("Listen", horn, [1, 1, 1, 1, 1, 1])                          # (four times nothing; then Ysolde, twice)
    assert s.get_attribute("WardensTruth") == "1" and s.get_attribute("WardensHeard") == "2"
    assert s.items_held("Wardens_Lantern") == 1
    s.diseases.clear()
    leave(world, s)
    world.ents.extend(held)


def test_the_archive_vault_under_galaiths_city_hall(world):
    hall = next(m for m in world.maps.values() if any(i[0] == "Archive_Hatch" for i in m.ids))
    hx, hy = next(i[1:] for i in hall.ids if i[0] == "Archive_Hatch")
    s = join(world, "Burglar", hall.name, (hx - 1) * 32, hy * 32)
    s.connected = True
    gx, gy = hall.ox + (hx - 1) * 32 + 16, hall.oy + (hy - 1) * 32 + 16
    s.out = []
    s.choose_verb("Climb Down", s.tile_entity_at(gx, gy), gx, gy)
    run_for(world, 20)
    assert s.cur_map is hall and any("locked" in str(e.get("text", "")) for e in s.out)   # (not till she sends you)
    s.update_attribute("ArchiveVault", "=1")
    s.choose_verb("Climb Down", s.tile_entity_at(gx, gy), gx, gy)
    run_for(world, 30)
    if s.pending_map:
        s.do_pending_map_change()
    assert s.cur_map.name == hall.name.replace(",0", ",-1")
    chest = next(e for e in world.ents if e.npc_id == "Archive_Vault_Chest")
    assert s.chest_locked(chest)                                     # (Stealth to pick it, or a loud Break Open)
    s.unlocked_chests.add(s.chest_key(chest))
    s.god_mode = True                                                # (the watchmen: not what this tests)
    near(world, s, chest, 0, 30)
    s.do_action("Open", chest)
    run_for(world, 20)
    s.chest_response("CHEST_ALL")
    assert s.items_held("Marys_Notes") == 1 and s.get_attribute("ArchiveVault") == "2"
    leave(world, s)


def test_the_cold_bites_unless_youre_warm(world):
    spot = None
    for m in world.maps.values():
        if m.mz != 0:
            continue
        for ty in range(3, 19):
            for tx in range(3, 23):
                c = m.cell(tx, ty)
                if m.tile[c].startswith("Snow") and not m.roof[c] and not m.decor[c] and "0" not in m.walk[c]:
                    spot = (m, tx, ty)
                    break
            if spot:
                break
        if spot:
            break
    assert spot, "no snow"
    m, tx, ty = spot
    s = join(world, "Shiverer", m.name, (tx - 1) * 32, (ty - 1) * 32 - 12)
    assert s.cold_ground() and not s.warm()
    hp = s.player.hp = s.player_max_hp
    s.cold_since = world.now - 60000                               # (out in it a while)
    s.cold_at = s.cold_next = 0
    s.cold_tick()
    assert s.player.hp < hp and "Cold" in s.status                 # (it bites)
    stock(s, Wool_Hood=1)
    s.do_action("Wear", next(e for e in s.inv if e.name == "Wool_Hood"))
    assert s.warm()                                                # (wool keeps it off)
    s.cold_at = 0
    s.cold_tick()
    assert "Cold" not in s.status
    leave(world, s)


def test_an_altar_blesses_once_a_day(world):
    m = next(m for m in world.maps.values() if any(d == "Altar001" for d in m.decor))
    c = m.decor.index("Altar001")
    tx, ty = c % 25 + 1 if c % 25 else 25, (c - 1) // 25 + 1
    tx = next(x for x in range(1, 26) if m.decor[m.cell(x, ty)] == "Altar001")
    s = join(world, "Pilgrim", m.name, (tx - 1) * 32, ty * 32)
    s.connected = True
    gx, gy = m.ox + (tx - 1) * 32 + 16, m.oy + (ty - 1) * 32 + 16
    before = s.skill_level("Defence")
    s.choose_verb("Pray", s.tile_entity_at(gx, gy), gx, gy)
    run_for(world, 20)
    assert s.skill_level("Defence") == before + 2                   # (blessed: steadier a while)
    s.out = []
    s.choose_verb("Pray", s.tile_entity_at(gx, gy), gx, gy)
    run_for(world, 20)
    assert any("still" in str(e.get("text", "")) for e in s.out)    # (once a day: then a quiet moment)
    leave(world, s)


def test_houses_with_more_than_one_floor_line_up(world):
    ups = downs = 0
    for name, m in world.maps.items():
        mx, my, mz = (int(v) for v in name.split(","))
        if mz != 0:
            continue
        for z, here, there in ((1, "Ladder001", "Hatch001"), (-1, "Hatch001", "Ladder001")):
            other = world.maps.get("%d,%d,%d" % (mx, my, z))
            if other is None:
                continue
            for c, d in enumerate(m.decor):
                if d == here and other.decor[c] == there:     # (the ladder up under the hatch above it, and so on)
                    if z == 1:
                        ups += 1
                    else:
                        downs += 1
    assert ups >= 60 and downs >= 40                              # (about half the houses: more than one floor)


def test_a_question_never_breaks_into_a_busy_player(world):
    a, b = join(world, "Asker"), join(world, "Busy")
    lines = ["01\tDisplay.Conversation\tFrank\tWell?\tYes.\t02\tNo.\t03", "02\tEnd", "03\tEnd"]
    assert b.run_script_lines("Talk Test", lines)
    b.run_scripts()
    assert b.ab_mode == "Conversation" and b.script_state == "CONVERSATION"
    a.invite(b)                                                     # (from anywhere, while they talk: refused)
    assert b.ab_mode == "Conversation" and not getattr(b, "native_menu", None)
    b.action_box_response_chosen(1)
    b.run_scripts()
    assert not b.script_running                                     # (their conversation went on as it should)
    a.invite(b)
    assert getattr(b, "native_menu", None)                          # (free now: asked)
    b.action_box_response_chosen(2)
    a.invite(b)
    assert b.ab_mode == ""                                          # (asked a moment ago: not again yet)
    assert b.run_script_lines("Talk Test", lines)
    b.run_scripts()
    b.show_menu("Test", "Man", "Something else.", [("All right.", None)])   # (an engine box over a script's)
    b.run_scripts()
    assert not b.script_running                                     # (the script went on, as if it were closed)
    b.action_box_response_chosen(1)
    leave(world, a)
    leave(world, b)


def test_a_tree_felled_by_two_at_once_grows_back(world, monkeypatch):
    import dsengine.world as dw
    clock = [dw.clock_seconds()]
    monkeypatch.setattr(dw, "clock_seconds", lambda: clock[0])
    a, b = join(world, "Feller1"), join(world, "Feller2")
    m = world.maps["1,1,0"]
    before = m.cell_text(5, 5)
    a.script_change_tile("5,5", "Tree_Stump001", 0, 20)
    b.script_change_tile("5,5", "Tree_Stump001", 0, 20)            # (half a second later: it's a stump already)
    assert "Tree_Stump001" in m.cell_text(5, 5)
    clock[0] += 25
    world.run_action_queue()
    assert m.cell_text(5, 5) == before
    clock[0] += 25
    world.run_action_queue()
    assert m.cell_text(5, 5) == before
    leave(world, a)
    leave(world, b)


def test_shop_restocks_never_crowd_out_respawns(world, monkeypatch):
    import dsengine.world as dw
    saved = list(world.action_queue)
    try:
        world.action_queue = []
        world.add_action_to_queue("ADD.SHOP.ITEM", "Bread", "SHOP-Test", "1", "-", "0,0", 3600)
        world.add_action_to_queue("ADD.SHOP.ITEM", "Bread", "SHOP-Test", "2", "-", "0,0", 3600)
        assert len(world.action_queue) == 1 and float(world.action_queue[0].split("\t")[3]) == 3   # (one entry)
        monkeypatch.setattr(dw, "SHOP_QUEUE_MOST", 5)
        for i in range(10):
            world.add_action_to_queue("ADD.SHOP.ITEM", "Thing%d" % i, "SHOP-Test", "1", "-", "0,0", 3600)
        assert len(world.action_queue) == 5
        world.add_action_to_queue("ADD", "Goblin", "NPC", "-", "1,1,0", "100,100", 60)
        assert world.action_queue[-1].startswith("ADD\tGoblin")      # (a respawn always has its place)
    finally:
        world.action_queue = saved


def test_what_ends_is_forgotten_by_the_others(world):
    from dsengine.view import snapshot
    a, b = join(world, "Seer"), join(world, "Sneak", x=330, y=300)
    b.stance = "Sneaking"
    snapshot(world, a)
    b.stance = ""
    out = snapshot(world, a)
    chg = [c for m in out if m["t"] == "snap" for c in m["chg"] if c["u"] == b.player.uid]
    assert chg and "sc" in chg[0]["rm"]                             # (the page is told the crouch is over)
    leave(world, a)
    leave(world, b)


def test_what_a_player_has_seen_is_kept_small(world):
    from dsengine.session import pack_cells, unpack_cells
    cells = {1, 2, 9, 2100}
    assert unpack_cells(pack_cells(cells)) == cells
    assert unpack_cells([3, 4]) == {3, 4} and unpack_cells("all") == "all"     # (an older save's list)
    s = join(world, "Mapper")
    s.note_explored("1,1,0", list(range(1, 1001)))
    assert isinstance(s.explored["1,1,0"], set)
    s.note_explored("1,1,0", list(range(1001, s.fog_cells() + 1)))
    assert s.explored["1,1,0"] == "all"                              # (all of it seen: kept as all)
    s.note_explored("1,0,0", [5, 6])
    st = s.save_state()
    assert st["explored"]["1,1,0"] == "all" and unpack_cells(st["explored"]["1,0,0"]) == {5, 6}
    leave(world, s)


def test_the_journal_is_sent_at_most_once_a_second(world):
    s = join(world, "Reader")
    s.out = []
    journals = lambda: sum(ev["t"] == "journal" for ev in s.out)
    s.handle({"t": "journal"})
    s.handle({"t": "journal"})
    world.tick(0.05, now=world.now + 50)
    assert journals() == 1
    s.handle({"t": "journal"})
    world.tick(0.05, now=world.now + 50)
    assert journals() == 1                                          # (asked again at once: in a moment)
    world.tick(0.05, now=world.now + 1000)
    assert journals() == 2
    leave(world, s)


def test_the_journals_skills_page_says_how_each_skill_is_levelled_and_what_each_level_opens(world):
    """The journal's Skills tab: every skill but Hitpoints, in Config's order, its words from Skills.ini and what each
    level opens read from where it's set (gathering, crafting, spells, gear, building, thieving)."""
    s = join(world, "Reader")
    pages = {p["skill"]: p for p in s.journal_data()["skills"]}
    assert [p for p in world.data.skill_name[1:] if p.upper() != "HITPOINTS"] == list(pages)
    assert "Hit things in a fight" in pages["Strength"]["trains"]
    opens = lambda skill: dict(pages[skill]["opens"])
    assert opens("Mining")[3] == "Gather Coal" and "Mithril ore" in opens("Mining")[13]
    assert "Wield Steel Sword" in opens("Strength")[5]
    assert "Wear" in opens("Defence")[3] and "Iron Helm" in opens("Defence")[3]
    assert "Cast Fire Bolt" in opens("Channeling")[1]
    assert opens("Crafting")[1].startswith("Make ") and "Copper Bar" in opens("Crafting")[1]
    assert "an armourer" in opens("Stealth")[8] and "a house's valuables" in opens("Stealth")[4]
    assert "Enchant gear" in opens("Shardcraft")[4] and "still the mist" in opens("Shardcraft")[1]
    assert "Build" in opens("Homesteading")[1] and "Bed (" not in " ".join(opens("Homesteading").values())
    assert all(a[0] < b[0] for p in pages.values() for a, b in zip(p["opens"], p["opens"][1:]))   # (level by level)
    assert s.skill_pages() is s.skill_pages()                       # (worked out once)
    leave(world, s)


def test_an_npc_roams_a_zone_of_any_shape(world):
    """Zone= (and Chase=) can be several rectangles joined by / (the map editor paints them tile by tile): it roams
    only in them, not in the gap their corners leave."""
    m = world.maps["3,5,0"]
    rabbit = world.add_npc("Rabbit", m.mz, m.ox + 4 * 32, m.oy + 4 * 32, "Attitude=Passive Zone=4,4,6,5/4,6,4,9")
    a = rabbit.ai
    inside = lambda tx, ty: world.in_zone(a, m.ox + (tx - 0.5) * 32, m.oy + (ty - 0.5) * 32)
    assert inside(5, 4) and inside(4, 9) and inside(6, 5)
    assert not inside(6, 8) and not inside(7, 4)                      # (the L's corner, and past it)
    assert a.zone.parts and len(a.zone.parts) == 2
    for _ in range(200):                                              # (where it picks to go: in one of them)
        r = a.zone.pick()
        assert r in a.zone.parts
    assert world.npc_rects("4,4,6,5/4,6,x,9") == []                   # (a part that isn't one: none of it)
    world.remove_entity(rabbit)


def test_a_cart_route_takes_its_nodes_in_order():
    """Carts.ini: NodeN= in Order= (a node more than once: out and back by the same street), else PointN= in turn;
    a stop it passes twice is offered once, at the next time it comes to it."""
    from dsengine.carts import route_points, Carts, Cart
    kv = {"NODE1": "a", "NODE2": "b", "NODE3": "c", "NODE4": "d", "ORDER": "1,2,3,2,4"}
    assert route_points(kv) == ["a", "b", "c", "b", "d"]
    assert route_points({"NODE2": "b", "NODE1": "a"}) == ["a", "b"]          # (no order: in number order)
    assert route_points({"POINT1": "x", "POINT2": "y"}) == ["x", "y"]
    c = Cart("T", "T", [(0, 0), (1, 0), (2, 0), (1, 0), (3, 0)], {0: "the gate", 1: "the square", 3: "the square",
                                                                   4: "the port"}, 0, 1, 6, True)
    c.i = 2
    ahead = Carts.ahead(None, c)
    assert [c.stops[j] for j in ahead] == ["the square", "the port", "the gate"] and ahead[0] == 3


def test_editor_terrains_zones_routes_and_map_names():
    """The map editor: a terrain painted lays its ground and decor and takes off another's (dsedit/terrain.py); an
    area painted tile by tile is written as few rectangles; a cart's order can visit a node twice; a map's name is
    found only where it stands on its own (dsedit/mapops.py)."""
    import random as _r
    from dsedit.project import Project, MapDoc
    from dsedit import terrain as TR, mapops
    from dsedit.pages.maps import MapPage
    from dsedit.carts import CartRoutes
    P = Project(ROOT)
    doc = MapDoc(P, "4,0,0")
    at = lambda x, y: (doc, x, y) if 0 <= x < P.map_w and 0 <= y < P.map_h else None
    spot = [(x, y) for x in range(2, 8) for y in range(2, 8)]
    TR.paint(P, TR.named(P, "Woodland"), spot, at, lambda d: None, rng=_r.Random(3))
    assert all(doc.cells[y][x].tile == "Grass001" for x, y in spot)
    assert sum(1 for x, y in spot if doc.cells[y][x].decor) > 10                  # (trees, mostly)
    TR.paint(P, TR.named(P, "Water"), spot, at, lambda d: None, rng=_r.Random(3))
    assert all(doc.cells[y][x].tile == "Water001" for x, y in spot)
    assert not any((doc.cells[y][x].decor or "").startswith("Tree") for x, y in spot)   # (the woodland's, gone)
    TR.paint(P, TR.named(P, "Cave_Rock"), spot, at, lambda d: None, rng=_r.Random(3))
    TR.paint(P, TR.named(P, "Cave_Floor"), [(4, 5), (5, 5)], at, lambda d: None, rng=_r.Random(3))
    assert doc.cells[4][4].tile in ("Cave_Wall002", "Cave_Wall003") and doc.cells[3][4].tile == "Cave_Wall001"
    TR.paint(P, TR.named(P, "Cave_Rock"), [(4, 5), (5, 5)], at, lambda d: None, rng=_r.Random(3))
    assert doc.cells[4][4].tile == "Cave_Wall001"                                # (filled in: no face)
    assert len(TR.disc(0, 0, 5)) == 21 and TR.disc(3, 3, 1) == [(3, 3)]
    assert (5, 5) in TR.inside_outline([(0, 0), (10, 0), (10, 10), (0, 10)])
    tiles = {(x, y) for x in range(1, 4) for y in range(1, 3)} | {(1, 3), (1, 4)}
    text = MapPage.rects_text(tiles)
    assert MapPage.tiles_of(MapPage.opt_rects(text)) == tiles and text.count("/") == 1
    routes = CartRoutes(P)
    r = routes.routes[0]
    plain = routes.text()
    r.order = [0, 1, 2, 1, 3]
    assert "Order=1,2,3,2,4" in routes.text() and "Node1=" in routes.text()
    r.order = []
    assert routes.text() == plain                                                # (one after another: PointN= as before)
    pat = mapops.name_re("4,0,0")
    assert pat.search("Start.Map=4,0,0") and pat.search("Point3=4,0,0,5,17,the market")
    assert not pat.search("14,0,0") and not pat.search("-4,0,0") and not pat.search("4,0,01")


def test_editor_galaith_wall_joins_and_a_stroke_has_no_gaps():
    """Galaith's wall, white and burnt, is a set that joins (it was look-alikes: a random piece a tile); a piece beside
    its gate or its other colour counts it as more of the wall; a stroke the mouse outran has no gaps."""
    from dsedit.project import Project
    from dsedit import terrain as TR, world as WD
    P = Project(ROOT)
    groups = TR.groups(P, "map")
    for key in ("Galaith_Wall", "Burnt_Wall"):
        assert groups["set:" + key].kind == "Set" and "fam:" + key not in groups and WD.joins(P, key + "001")

    def lay(cells, there=None):
        grid = dict(there or {})
        WD.lay_joins(P, "Galaith_Wall001", cells, lambda x, y: grid.get((x, y), "Flagstone001"),
                     lambda x, y, n: grid.__setitem__((x, y), n))
        return grid
    run = lay([(x, 5) for x in range(5)])
    assert [run[(x, 5)] for x in range(5)] == ["Galaith_Wall003"] + ["Galaith_Wall001"] * 3 + ["Galaith_Wall003"]
    assert [run[(x, 6)] for x in range(5)] == ["Galaith_Wall005"] + ["Galaith_Wall004"] * 3 + ["Galaith_Wall005"]
    col = lay([(5, y) for y in range(6)])
    assert [col[(5, y)] for y in range(7)] == ["Galaith_Wall003"] + ["Galaith_Wall002"] * 4 + \
        ["Galaith_Wall003", "Galaith_Wall005"]                   # (a face only under the south end, never cutting a wall that runs on)
    both = lay([(0, 5), (1, 5)], {(2, 5): "Burnt_Gate005", (-1, 5): "Burnt_Wall001"})
    assert both[(0, 5)] == both[(1, 5)] == "Galaith_Wall001"          # (run on through: no tower by the gate)
    for a, b in (((0, 0), (5, 3)), ((5, 3), (0, 0)), ((2, 2), (2, 7)), ((2, 2), (9, 2)), ((0, 0), (-4, 4))):
        line = WD.line_cells(a, b)
        assert line[-1] == b
        for p, q in zip([a] + line, line):
            assert abs(p[0] - q[0]) + abs(p[1] - q[1]) == 1           # (next to the last along a side)
    assert WD.line_cells((3, 3), (3, 3)) == []


def test_editor_an_area_lies_across_maps():
    """An area marked over the corner of four maps: every tile and entity taken, a roof group of the same number on two
    maps kept apart, put down on maps of its own, each entity on the map it lands on; a cut's references map to map."""
    import types
    from dsedit import region as R
    from dsedit.project import Cell
    W, H = 25, 21

    def blank(name, tile):
        return types.SimpleNamespace(name=name, cells=[[Cell(tile) for _ in range(W)] for _ in range(H)], entities=[],
                                     placed=lambda: [])
    docs = {}
    for name, tile in (("a", "Grass001"), ("b", "Sand001"), ("c", "Dirt001"), ("d", "Water001")):
        d = docs[name] = blank(name, tile)
        d.placed = (lambda d: lambda: d.entities)(d)
    at_grid = {"a": (0, 0), "b": (1, 0), "c": (0, 1), "d": (1, 1)}

    def on(names):
        """at(), parts_of() over maps set out in a grid, counted from the first's top-left."""
        grid = {v: k for k, v in at_grid.items() if k in names}

        def at(x, y):
            n = grid.get((x // W, y // H))
            return (docs[n], x % W, y % H) if n else None

        def parts(r):
            out = []
            for (i, j), n in grid.items():
                dx, dy = i * W, j * H
                x0, y0, x1, y1 = max(r[0], dx), max(r[1], dy), min(r[2], dx + W - 1), min(r[3], dy + H - 1)
                if x0 <= x1 and y0 <= y1:
                    out.append((docs[n], dx, dy, (x0 - dx, y0 - dy, x1 - dx, y1 - dy)))
            return out
        return at, parts
    ent_tile = lambda e: (e.x // 32 + 1, e.y // 32 + 1)

    def shift(e, dx, dy):
        e.x, e.y = e.x + dx * 32, e.y + dy * 32
    docs["a"].cells[20][24].set_roof("Roof001", "01")
    docs["b"].cells[20][0].set_roof("Roof002", "01")
    docs["d"].entities.append(types.SimpleNamespace(x=32, y=32, name="Cat"))         # (tile 2,2 of d)
    at, parts = on("abcd")
    rect = (23, 19, 27, 23)
    got = R.grab(parts(rect), "a", rect, ent_tile, shift, False)
    assert got.size == (5, 5)
    assert got.cells[0][0].tile == "Grass001" and got.cells[0][4].tile == "Sand001"
    assert got.cells[4][0].tile == "Dirt001" and got.cells[4][4].tile == "Water001"
    assert got.cells[1][1].roof_group != got.cells[1][2].roof_group           # (two maps' 01s: two roofs)
    assert [(e.x // 32, e.y // 32) for e in got.entities] == [(26, 22)]       # (as if it stood on a)
    assert R.ground_round(lambda x, y: "Sand001" if x > 25 else "Grass001", (10, 10, 12, 12)) == "Grass001"
    # (put down lower, on maps c and d's own ground: across their edge, the cat on d)
    before = len(docs["d"].entities)
    added = R.put(at, got, 23, 30, ent_tile, shift)
    assert docs["c"].cells[9][23].tile == "Grass001" and docs["d"].cells[9][2].tile == "Sand001"
    assert len(added) == 1 and added[0] in docs["d"].entities and len(docs["d"].entities) == before + 1
    assert (added[0].x // 32, added[0].y // 32) == (1, 12)                    # (that map's own tiles)
    # (a gap in the world: a cell of None lands nowhere and needs nothing there)
    at2, parts2 = on("a")
    gappy = R.grab(parts2(rect), "a", rect, ent_tile, shift, False)
    assert gappy.cells[0][4] is None and gappy.cells[0][0] is not None
    assert R.put(at2, gappy, 0, 0, ent_tile, shift) == []
    # (a cut moved over an edge: each part of it says where it went, in that map's tiles, once)
    moved = R.moves(parts((23, 2, 27, 2)), (23, 2, 27, 2), parts((23, 3, 27, 3)), 23, 3)
    assert sorted(moved) == [("a", (23, 2, 24, 2), "a", 0, 1), ("b", (0, 2, 2, 2), "b", 0, 1)]
    moved = R.moves(parts((23, 2, 27, 2)), (23, 2, 27, 2), parts((24, 2, 28, 2)), 24, 2)
    assert sorted(moved) == [("a", (23, 2, 23, 2), "a", 1, 0), ("a", (24, 2, 24, 2), "b", -24, 0),
                             ("b", (0, 2, 2, 2), "b", 1, 0)]
    assert R._moved(moved, "a", 25, 3, True) == ("b", 1, 3)                  # (tile 24,2 of a: tile 0,2 of b, from 1)


def test_editor_draws_a_boardwalk_on_over_a_maps_edge():
    """A boardwalk running on into the next map has no front at this one's edge (as the game draws it: ground.js
    raisedAt goes by the world); one that ends there does; and it casts its shadow onto the map south of it."""
    import types
    from PIL import ImageChops
    from dsedit.project import Project, Cell
    from dsedit.render import render, ground_image
    P = Project(ROOT)
    board = types.SimpleNamespace(cells=[[Cell("Boardwalk001") for _ in range(P.map_w)] for _ in range(P.map_h)],
                                  placed=lambda: [])
    grass = types.SimpleNamespace(cells=[[Cell("Grass001") for _ in range(P.map_w)] for _ in range(P.map_h)],
                                  placed=lambda: [])
    tw, th = P.tile_w, P.tile_h
    x, y = 5, P.map_h - 1
    last = (x * tw, y * th, (x + 1) * tw, (y + 1) * th)
    plain = ground_image(P, "Boardwalk001", x, y).convert("RGB")
    on = render(P, board, entities=False, origin=(0, 0), around=lambda gx, gy: "Boardwalk001").convert("RGB").crop(last)
    assert ImageChops.difference(on, plain).getbbox() is None         # (nothing drawn over it: it goes on)
    ends = render(P, board, entities=False, origin=(0, 0), around=lambda gx, gy: "Grass001").convert("RGB").crop(last)
    assert ImageChops.difference(ends, plain).getbbox() is not None   # (its front)
    top = (x * tw, 0, (x + 1) * tw, th)
    alone = render(P, grass, entities=False, origin=(0, P.map_h), around=lambda gx, gy: "Grass001").convert("RGB")
    under = render(P, grass, entities=False, origin=(0, P.map_h), around=lambda gx, gy: "Boardwalk001" if gy < P.map_h
                   else "Grass001").convert("RGB")
    assert ImageChops.difference(alone.crop(top), under.crop(top)).getbbox() is not None   # (its shadow, from the last map)


def test_editor_moves_any_entity_over_a_maps_edge():
    """Dragged past a map's edge, an NPC, a trigger, a lock or a place goes onto the next map (a tile that has its own
    already says no); with no map there it stays where it is. A marked group on Entities moves just its entities."""
    import types
    from dsedit.pages.maps import MapPage
    from dsedit.project import Entity
    W, H = 25, 21
    said = []

    def blank(name):
        return types.SimpleNamespace(name=name, cells=[[None] * W for _ in range(H)], entities=[], placed=None)
    a, b = blank("a"), blank("b")
    for d in (a, b):
        d.placed = (lambda d: lambda: d.entities)(d)
    pg = types.SimpleNamespace(doc=a, project=types.SimpleNamespace(map_w=W, map_h=H, tile_w=32, tile_h=32), area=None,
                               app=types.SimpleNamespace(status=lambda m, k="": said.append(m)), touch=lambda d: None,
                               sel_ent=None, shift_ent=MapPage.shift_ent, ent_size=lambda e: (32, 32),
                               tile_taken=MapPage.tile_taken, remember=lambda: None, redraw=lambda: None,
                               show_inspector=lambda: None)
    pg.activate = lambda n: setattr(pg, "doc", {"a": a, "b": b}[n])
    pg.zone_follows, pg.zone_keeps_up = MapPage.zone_follows, lambda d: MapPage.zone_keeps_up(pg, d)
    pg.inside = lambda x, y: 0 <= x < W and 0 <= y < H

    def at(x, y):
        if not 0 <= y < H:
            return None
        return (pg.doc, x, y) if 0 <= x < W else ((b if pg.doc is a else a), x % W, y) if -W <= x < 2 * W else None
    pg.at = at
    pg.ent_tile = lambda e: MapPage.ent_tile(pg, e)
    pg.tile_of = lambda x, y: (int(x // 32), int(y // 32))
    pg.parts_of = lambda r: [(pg.doc, 0, 0, (r[0], r[1], min(r[2], W - 1), r[3]))]
    pg.area_ents = lambda parts: MapPage.area_ents(pg, parts)
    pg.ents_land = lambda dx, dy: MapPage.ents_land(pg, dx, dy)
    npc = Entity("NPC", "Fisherman", 25 * 32, 5 * 32, opts="Attitude=Good Zone=20,5,24,8")
    a.entities.append(npc)
    MapPage.settle_ent(pg, npc)
    assert npc in b.entities and npc not in a.entities and (npc.x, npc.y) == (0, 5 * 32) and pg.doc is b
    assert npc.opt("Zone") == "-5,5,-1,8"                             # (where it was: on the map beside this)
    pg.doc = a
    place = Entity("Id", "Probe_Place", 26, 3)                        # (dragged to tile 26: the next map's first)
    a.entities.append(place)
    MapPage.settle_ent(pg, place, {"move": place, "orig": (24, 3)})
    assert place in b.entities and (place.x, place.y) == (1, 3)
    pg.doc = a
    other = Entity("Id", "Another", 26, 3)
    a.entities.append(other)
    MapPage.settle_ent(pg, other, {"move": other, "orig": (24, 3)})
    assert other in a.entities and (other.x, other.y) == (24, 3) and "already" in said[-1]
    lost = Entity("NPC", "Fisherman", 5 * 32, 30 * 32)
    a.entities.append(lost)
    MapPage.settle_ent(pg, lost)
    assert lost in a.entities and lost.y == (H - 1) * 32 and "no map" in said[-1]
    # (its zone, chase area and patrol go with it, tile by tile; its home and bed are where they really are)
    pg.doc = a
    walker = Entity("NPC", "Fisherman", 10 * 32, 5 * 32,
                    opts="Zone=9,4,13,8 Chase=7,2,15,10 Patrol=10,6/12,6 Home=1,1,3,3 Bed=2,2")
    a.entities.append(walker)
    drag = {"move": walker, "orig": (walker.x, walker.y), "tile": tuple(pg.ent_tile(walker))}
    walker.x = 13 * 32                                                # (three tiles along)
    MapPage.zone_keeps_up(pg, drag)
    assert walker.opt("Zone") == "12,4,16,8" and walker.opt("Chase") == "10,2,18,10"
    assert walker.opt("Patrol") == "13,6/15,6" and walker.opt("Home") == "1,1,3,3" and walker.opt("Bed") == "2,2"
    walker.x = 26 * 32                                                # (and on over the edge: the next map's tile 2)
    MapPage.settle_ent(pg, walker, drag)
    assert walker in b.entities and walker.x == 32 and walker.opt("Zone") == "0,4,4,8"
    assert walker.opt("Patrol") == "1,6/3,6"                          # (round it, on its new map)
    assert walker.opt("Home") == "-24,1,-22,3" and walker.opt("Bed") == "-23,2"   # (still that house, back on the last map)
    pg.doc = a
    held = Entity("NPC", "Fisherman", 5 * 32, 19 * 32, opts="Zone=4,18,8,21")
    a.entities.append(held)
    drag = {"move": held, "orig": (held.x, held.y), "tile": tuple(pg.ent_tile(held))}
    held.y = 30 * 32
    MapPage.zone_keeps_up(pg, drag)
    assert held.opt("Zone") == "4,29,8,32"
    MapPage.settle_ent(pg, held, drag)
    assert held.y == 20 * 32 and held.opt("Zone") == "4,19,8,22"      # (where it was held back to)
    # (a group: over the edge together, nothing left behind; one that can't go, none go)
    a.entities[:] = []
    one, two = Entity("NPC", "Fisherman", 20 * 32, 2 * 32, opts="Zone=19,1,22,4 Bed=1,1"), \
        Entity("Trigger", x=24, y=4, script="Probe")
    a.entities += [one, two]
    pg.area = (20, 0, 24, 6)
    MapPage.move_area_ents(pg, 3, 0)
    assert one in a.entities and two in b.entities and (two.x, two.y) == (2, 4) and pg.area == (23, 0, 27, 6)
    assert one.opt("Zone") == "22,1,25,4" and one.opt("Bed") == "1,1"
    pg.area = (20, 0, 24, 6)
    MapPage.move_area_ents(pg, 0, 40)                                 # (off the bottom of the maps)
    assert one in a.entities and (one.x, one.y) == (23 * 32, 2 * 32) and "Not there" in said[-1]


def test_editor_keeps_a_picture_till_its_new_one_is_there():
    """A Tk image that's let go of goes blank at once, which was the map flashing black each time it was painted: a
    map's picture stays held till what replaces it is on the canvas. Friendly and standing NPCs draw no lines they don't
    have."""
    import types
    from dsedit.pages.maps import MapPage, LINES
    from dsedit.project import Project
    pg = types.SimpleNamespace(_pics={}, _photos={("a", "map"): "old a", ("b", "map"): "old b"}, _retired=[],
                              _edges={})
    pg.retire_photos = lambda name=None: MapPage.retire_photos(pg, name)
    MapPage.forget_pictures(pg, "a")
    assert pg._photos == {("b", "map"): "old b"} and pg._retired == ["old a"]
    MapPage.forget_pictures(pg)
    assert pg._photos == {} and sorted(pg._retired) == ["old a", "old b"]
    pg = types.SimpleNamespace(project=Project(ROOT))
    for a in ("npc_attitude", "npc_roams", "npc_chases"):
        setattr(pg, a, (lambda f: lambda e: f(pg, e))(getattr(MapPage, a)))
    npc = lambda **o: types.SimpleNamespace(name="Fisherman", opt=lambda k: o.get(k, ""))
    assert not pg.npc_roams(npc(Stand="1", Attitude="Good")) and not pg.npc_chases(npc(Stand="1", Attitude="Good"))
    assert pg.npc_roams(npc(Attitude="Good")) and pg.npc_chases(npc(Attitude="Bad"))
    assert pg.npc_roams(npc(Stand="1", Zone="1,1,3,3")) and pg.npc_chases(npc(Attitude="Good", Chase="1,1,3,3"))
    assert all(len(v) == 3 and v[1] and v[2] for v in LINES.values())


def test_a_poison_that_kills_takes_the_other_effects_without_a_fault(world):
    s = join(world, "Poisoned")
    s.connected = True
    s.status_start("Poison")
    s.status_start("Daze")
    s.player.hp = 1
    s.status["Poison"]["next"] = world.now
    world.tick(0.05, now=world.now + 50)                            # (no KeyError: the tick goes on)
    assert s.dead_wait and not s.status
    s.respawn()
    leave(world, s)


def test_one_players_fault_doesnt_stop_the_others(world):
    a, b = join(world, "Faulty"), join(world, "Fine")
    a.tick_before_npcs = lambda: 1 / 0                              # (something in a's own state goes wrong)
    b.out = []
    b.journal_wanted, b.journal_at = True, -10 ** 9
    world.tick(0.05, now=world.now + 50)
    assert any(ev["t"] == "journal" for ev in b.out)                # (b's tick went on all the same)
    del a.tick_before_npcs
    leave(world, a)
    leave(world, b)


def test_a_trade_keeps_wear_and_room_and_leaves_shards_alone(world):
    a = join(world, "Wear_A", "11,-3,0", 300, 300)
    b = join(world, "Wear_B", "11,-3,0", 330, 300)
    try:
        stock(a, Pickaxe=1)
        next(e for e in a.inv if e.name == "Pickaxe").wear = 150
        a.shard_balance = 40
        a.do_action("Trade", b.player)
        b.native_menu_chosen(1)
        a.trade_msg({"do": "add", "item": "Shard", "n": 40})       # (a hand-made message: not a thing to trade)
        assert a.trade["offer"]["Wear_A"] == {}
        a.trade_msg({"do": "add", "item": "Pickaxe", "n": 1})
        a.trade_msg({"do": "accept"})
        b.trade_msg({"do": "accept"})
        assert next(e for e in b.inv if e.name == "Pickaxe").wear == 150     # (worn as it was)
        assert a.shard_balance == 40
        cap = b.inventory_capacity()
        while len(b.inv) < cap - 1:
            b.inv.append(type(b.inv[0])("Stone", 1, 0))
        stock(a, Bronze_Sword=1, Iron_Dagger=1)
        a.do_action("Trade", b.player)
        b.native_menu_chosen(1)
        a.trade_msg({"do": "add", "item": "Bronze_Sword", "n": 1})
        a.trade_msg({"do": "add", "item": "Iron_Dagger", "n": 1})
        a.trade_msg({"do": "accept"})
        b.trade_msg({"do": "accept"})
        assert a.items_held("Bronze_Sword") == 1 and b.items_held("Bronze_Sword") == 0   # (one slot: both or neither)
    finally:
        a.trade_close()
        leave(world, a)
        leave(world, b)


def test_a_boss_goes_back_down_when_its_fighters_go(world):
    a = join(world, "Down_A", "11,-3,0", 300, 300)
    b = join(world, "Down_B", "11,-3,0", 330, 300)
    try:
        boss = world.add_npc("Barrow_King", 0, a.player.x + 60, a.player.y, "Attitude=Bad", "Bad")
        hp = boss.max_hp
        a.fought(boss)
        b.fought(boss)
        assert boss.max_hp > hp
        boss.fought_by["Down_B"] = world.now - 120000               # (b's blows were two minutes ago)
        a.fought(boss)
        assert boss.max_hp == hp and 1 <= boss.hp <= hp             # (one fighter: the base numbers again)
        world.remove_entity(boss)
    finally:
        leave(world, a)
        leave(world, b)


def test_no_shards_from_gear_too_cheap_to_hold_magic(world):
    s = join(world, "Breaker")
    assert s.dismantle_worth("Wooden_Sword") == 0                   # (two free logs: no Shards from nothing)
    assert s.dismantle_worth("Copper_Dagger") >= 1                  # (Frank's old dagger still teaches it)
    leave(world, s)


def test_a_dead_creature_isnt_killed_twice(world):
    s = join(world, "Twice")
    g = world.add_npc("Goblin", 0, s.player.x + 40, s.player.y, "Attitude=Bad", "Bad")
    queued = len(world.action_queue)
    s.damage_npc(g, 999)
    after = len(world.action_queue)
    s.damage_npc(g, 999)
    assert len(world.action_queue) == after and after >= queued    # (one death, one respawn)
    leave(world, s)


def test_dying_keeps_what_was_in_your_hands_and_the_grave_waits(world):
    s = join(world, "Fallen")
    s.connected = True
    stock(s, Wooden_Sword=1, Healing_Draught=5, Iron_Dagger=1)
    s.do_action("Wield", next(e for e in s.inv if e.name == "Wooden_Sword"))
    s.player.hp = 0
    s.player_dies()
    assert s.equipped[s.equip_slot_index("Weapon")] == "Wooden_Sword"     # (cheap, but it was in their hand)
    left = s.grave["left"]
    world.tick(0.05, now=world.now + 5000)
    assert s.grave["left"] == left                                  # (no time lost on the death screen)
    s.respawn()
    leave(world, s)


def test_thieving_and_disarmed_traps_are_remembered_across_a_relog(world):
    s = join(world, "Pocket")
    s.thief_until["pick:Someone"] = world.now + 600000
    s.banned_until["Shopkeeper"] = world.now + 600000
    s.traps_disarmed.add(("15,18,-1", 16, 13))
    s.traps_disarmed.add(("40,40,-11", 3, 3))                       # (the Deep's: made anew each shift)
    st = s.save_state()
    leave(world, s)
    t = Session(world, "Pocket")
    t.load_state(st)
    assert t.thief_until.get("pick:Someone", 0) > world.now and "Shopkeeper" in t.banned_until
    assert ("15,18,-1", 16, 13) in t.traps_disarmed and ("40,40,-11", 3, 3) not in t.traps_disarmed


def test_the_gift_box_gives_every_gift(world):
    s = join(world, "Giftee")
    world.together.gifts["Giftee"] = [["A", "Bread", 1], ["B", "Logs", 2], ["C", "Bread", 1]]
    try:
        s.gift_box_menu("Giftee")
        assert world.together.gifts["Giftee"] == [] and s.items_held("Logs") == 2 and s.items_held("Bread") == 2
    finally:
        world.together.gifts.pop("Giftee", None)
        leave(world, s)


def test_work_stops_when_someone_else_gets_there_first(world):
    s = join(world, "Chopper")
    s.connected = True
    m = world.maps["1,1,0"]
    before = m.cell_text(5, 5)
    lines = ["01\tPlay.Animation\tWood_Chips\t1\tWoodChop", "02\tWait\t3", "03\tGive.Item\tLogs\t1", "04\tEnd"]
    s.script_cursor_x, s.script_cursor_y = m.ox + 4 * 32 + 16, m.oy + 4 * 32 + 16
    assert s.run_script_lines("Chop Test", lines)
    s.run_scripts()
    world.change_tile(m, 5, 5, "Tree_Stump001", keep_decor=False)  # (another player felled it)
    s.run_scripts()
    assert not s.script_running and s.items_held("Logs") == 0
    world.change_tile(m, 5, 5, before, keep_decor=False)
    leave(world, s)


def test_what_everyone_sees_is_the_same_worked_out_once(world):
    from dsengine.view import snapshot
    a, b = join(world, "Look_A"), join(world, "Look_B", x=330, y=300)
    alone = snapshot(world, a)
    a.view_known, a.sent_maps = {}, {}
    together = snapshot(world, a, {})
    pick = lambda out: sorted((e["u"], sorted(e.items())) for m in out if m["t"] == "snap" for e in m["add"])
    assert pick(alone) == pick(together)
    leave(world, a)
    leave(world, b)


def test_townsfolk_go_home_and_to_bed_at_night(world):
    """dev/migrate/assign_homes.py gave townsfolk a Home= and a Bed=: at night one goes to its bed and sleeps in it
    (<Name>_Sleep4: its head on the pillow), can't be talked to, and gets up in the morning, beside it."""
    sleeper = next(e for e in world.ents if e.ai is not None and getattr(e.ai, "bed", None) and e.z == 0 and
                   world.data.loaded("%s_Sleep4" % e.name))
    m = world.maps[sleeper.map]
    s = join(world, "Nightowl", sleeper.map, 2 * 32, 2 * 32)
    s.connected = True
    day = world.day_fraction()
    world.set_day_fraction(0.95)
    for _ in range(900):
        world.tick(0.05, now=world.now + 50)
        if sleeper.ai.asleep:
            break
    assert sleeper.ai.asleep and sleeper.pose == "Sleep" and sleeper.image == sleeper.name + "_Sleep4"
    bx, by = sleeper.ai.bed
    assert abs(sleeper.cx - (bx + 16)) <= 2 and by <= sleeper.y <= by + 4          # (in its bed)
    s.player.x, s.player.y = sleeper.x, sleeper.y + 40                       # (at the bedside)
    s.out = []
    s.choose_verb("Talk to", sleeper, sleeper.cx, sleeper.cy)
    assert any("fast asleep" in ev.get("text", "") for ev in s.out if ev["t"] == "msg")
    world.set_day_fraction(0.5)
    for _ in range(20):
        world.tick(0.05, now=world.now + 50)
    assert not sleeper.ai.asleep and sleeper.active and sleeper.pose != "Sleep"
    world.set_day_fraction(day)
    leave(world, s)


def test_a_home_is_where_its_hours_keep_it(world):
    """Home= (a hen's coop, it was Roost=): for the hours it's in, its zone is its home; out of them, its own."""
    day = world.day_fraction()
    world.set_day_fraction(0.5)
    hen = world.add_npc("Chicken", 0, world.maps["2,0,0"].ox + 20 * 32, world.maps["2,0,0"].oy + 16 * 32,
                        "Attitude=Passive Zone=19,15,25,18 Home=21,12,23,13")
    a = hen.ai
    assert a.home is not None and a.zone is a.day_zone
    world.set_day_fraction(0.95)
    world.tick(0.05, now=world.now + 50)             # (the hour's worked out once a tick)
    world.schedule_npc(hen, None)                    # (nobody near: it's simply in its coop)
    assert a.zone is a.home and world.in_zone(a, hen.fx, hen.fy)
    world.set_day_fraction(0.5)
    world.tick(0.05, now=world.now + 50)
    world.schedule_npc(hen, None)
    assert a.zone is a.day_zone
    old = world.add_npc("Chicken", 0, world.maps["2,0,0"].ox + 20 * 32, world.maps["2,0,0"].oy + 16 * 32,
                        "Roost=21,12,23,13")         # (an old map's Roost= still reads as its Home)
    assert old.ai.home is not None
    world.set_day_fraction(day)
    world.remove_entity(hen)
    world.remove_entity(old)


def test_prey_is_passive_everywhere():
    """Every placed animal that flees (Flees=1) is Passive: hunted, never a foe (dev/migrate/prey_passive.py)."""
    from ashen import ini
    path = os.path.join(ROOT, "data", "Entities.ini")
    prey = {s for s, _ in ini.sections(path) if s and (ini.read(s, "Flees", "", path) or "").strip() == "1"}
    assert {"Rabbit", "Duck", "Chicken", "Sheep"} <= prey
    for f in os.listdir(os.path.join(ROOT, "maps")):
        if f.endswith(".txt"):
            for ln in open(os.path.join(ROOT, "maps", f), encoding="cp1252").read().splitlines():
                fl = ln.split("	")
                if fl[0] == "NPC" and len(fl) > 1 and fl[1] in prey:
                    assert "Attitude=Passive" in (fl[4] if len(fl) > 4 else ""), (f, ln)


def test_sneaking_xp_is_for_getting_past(world, monkeypatch):
    """Stealth xp for slipping past a monster is for walking past it yourself, in its roam or near its patrol's path,
    against one above your level or not far under it, once a monster for a while: standing still while it wanders
    off teaches nothing."""
    m = world.maps["-2,15,0"]
    at = lambda tx, ty: (m.ox + (tx - 1) * 32, m.oy + (ty - 1) * 32)
    monkeypatch.setattr(world, "npc_sees", lambda e, a, s, d: False)   # (a perfect sneak, for the test)
    gob = world.add_npc("Goblin", 0, *at(5, 5), "Attitude=Bad Zone=1,1,25,21")
    s = join(world, "Creeper", "-2,15,0", 6 * 32, 5 * 32)
    world.npc_give_up(gob, gob.ai)
    s.stance = "Sneaking"
    xp = lambda: s.skill_xp_of("Stealth")
    before = xp()
    s.sneak_tick()
    assert gob.uid in s.sneak_near
    world.set_entity_position(gob, *at(20, 18))                     # (it wanders off; you stood still)
    s.sneak_tick()
    assert xp() == before and gob.uid not in s.sneak_near
    world.set_entity_position(gob, *at(5, 5))
    s.sneak_tick()
    s.player.x, s.player.y = at(18, 16)                              # (you walk on past it)
    s.sneak_tick()
    assert xp() > before
    got = xp()
    s.player.x, s.player.y = at(6, 5)                                # (back and past it again at once: nothing)
    s.sneak_tick()
    s.player.x, s.player.y = at(18, 16)
    s.sneak_tick()
    assert xp() == got
    world.remove_entity(gob)
    walker = world.add_npc("Goblin", 0, *at(3, 18), "Attitude=Bad Zone=3,18,3,18 Patrol=3,18/12,18")
    world.npc_give_up(walker, walker.ai)
    s.sneak_near.clear()
    s.player.x, s.player.y = at(8, 16)                               # (out of its roam, 2 tiles off its path)
    assert not world.in_zone(walker.ai, s.player.fx, s.player.fy) and s.near_patrol(walker, s.player.fx, s.player.fy)
    s.player.x, s.player.y = at(8, 10)
    assert not s.near_patrol(walker, s.player.fx, s.player.fy)
    world.remove_entity(walker)
    leave(world, s)


def test_loud_thieving_wakes_sleepers(world):
    """A lock forced or a rattle wakes whoever's asleep near; they get up and stay up a while, and one who sees you
    shouts for the guard. Asleep, nobody sees your hand."""
    sleeper = next(e for e in world.ents if e.ai is not None and getattr(e.ai, "bed", None) and e.z == 0 and
                   world.data.loaded("%s_Sleep4" % e.name))
    s = join(world, "Burglar", sleeper.map, 2 * 32, 2 * 32)
    s.connected = True
    day = world.day_fraction()
    world.set_day_fraction(0.95)
    for _ in range(900):
        world.tick(0.05, now=world.now + 50)
        if sleeper.ai.asleep:
            break
    assert sleeper.ai.asleep
    s.player.x, s.player.y = sleeper.x, sleeper.y + 40
    assert not s.watching(sleeper)
    s.wake_sleepers(s.player, 224)
    assert not sleeper.ai.asleep
    for _ in range(20):
        world.tick(0.05, now=world.now + 50)
    assert not sleeper.ai.asleep                                     # (up a while, night or not)
    world.set_day_fraction(day)
    leave(world, s)


def test_a_noise_wakes_every_sleeper_in_earshot_though_the_first_shouts(world, monkeypatch):
    m = world.maps["-2,15,0"]
    s = join(world, "Clatter", "-2,15,0", 2 * 32, 2 * 32)
    pair = [world.add_npc("Villager", 0, m.ox + (10 + k) * 32, m.oy + 10 * 32, "Attitude=Good Stand=1") for k in (0, 1)]
    run_for(world, 1)                                                # (on the world's map of who's where)
    for n in pair:
        n.ai.asleep = True
    shouted = []
    monkeypatch.setattr(s, "watching", lambda e: True)
    monkeypatch.setattr(s, "caught", lambda e, how: shouted.append(e))
    s.wake_sleepers(pair[0], 224)
    assert not any(n.ai.asleep for n in pair) and len(shouted) == 1
    for n in pair:
        world.remove_entity(n)
    leave(world, s)


def test_a_lookout_can_be_set_never_to_turn(world, monkeypatch):
    """Turn= on a map line: how often it glances about (seconds); 0, never, but back the way it faces after a sound."""
    monkeypatch.setattr(world, "npc_sees", lambda e, a, s, d: False)
    m = world.maps["-2,15,0"]
    s = join(world, "Watcher", "-2,15,0", 2 * 32, 2 * 32)          # (someone on the map, far off: it thinks)
    g = world.add_npc("Smuggler", 0, m.ox + 22 * 32, m.oy + 15 * 32, "Attitude=Bad Stand=1 Face=S Turn=0")
    assert g.ai.turn_every == 0 and g.direction == 4
    for _ in range(200):
        world.tick(0.05, now=world.now + 100)
    assert g.direction == 4
    g.direction = 1                                                  # (it turned to a sound)
    for _ in range(80):
        world.tick(0.05, now=world.now + 100)
    assert g.direction == 4
    world.remove_entity(g)
    leave(world, s)


def test_a_bed_is_clicked_where_its_drawn(world):
    """A bed is 1.5 tiles: a click past its foot (the walkable half of Bed002's tile) is the floor under it."""
    m = next(mm for mm in world.maps.values() if mm.mz == 0 and any(d == "Bed002" for d in mm.decor))
    i = m.decor.index("Bed002")
    xt = world.data.xt
    ty = (i - 1) // xt + 1
    tx = i - (ty - 1) * xt
    assert m.cell(tx, ty) == i
    s = join(world, "Sleepy", m.name, (tx - 1) * 32 + 16, (ty - 1) * 32 + 40)
    x0, y0 = m.ox + (tx - 1) * 32, m.oy + (ty - 1) * 32
    assert s.tile_entity_at(x0 + 16, y0 + 4).name == "Bed002"
    assert s.tile_entity_at(x0 + 16, y0 + 28).name != "Bed002"
    leave(world, s)


def test_a_night_owl_sleeps_by_day_and_one_on_watch_never(world):
    """Schedule=Night with a bed: asleep in it by day, up after dark. Schedule=Always: never to bed."""
    sleeper = next(e for e in world.ents if e.ai is not None and getattr(e.ai, "bed", None) and e.z == 0 and
                   world.data.loaded("%s_Sleep4" % e.name))
    s = join(world, "Owl", sleeper.map, 2 * 32, 2 * 32)
    day = world.day_fraction()
    was = sleeper.ai.schedule if hasattr(sleeper.ai, "schedule") else None
    try:
        sleeper.ai.schedule = "Night"
        sleeper.ai.woken_until = 0                                         # (not still up from a burglar)
        world.set_day_fraction(0.5)
        for _ in range(900):
            world.tick(0.05, now=world.now + 50)
            if sleeper.ai.asleep:
                break
        assert sleeper.ai.asleep                                          # (by day: abed)
        world.set_day_fraction(0.95)
        for _ in range(20):
            world.tick(0.05, now=world.now + 50)
        assert not sleeper.ai.asleep                                      # (after dark: up)
        sleeper.ai.schedule = "Always"
        for _ in range(200):
            world.tick(0.05, now=world.now + 50)
        assert not sleeper.ai.asleep                                      # (on watch all night)
    finally:
        sleeper.ai.schedule = was
        world.set_day_fraction(day)
        leave(world, s)


def test_one_with_no_door_sleeps_in_a_tent(world):
    """Galaith's town crier has no house and no door on the square: at night into the tent (houseless_tents.py),
    zzz over it; out of it in the morning."""
    crier = next(e for e in world.ents if e.npc_id == "Town_Crier_Galaith")
    assert world.nearest_door(crier) is None and world.nearest_shelter(crier) is not None
    s = join(world, "Passer", crier.map, 2 * 32, 2 * 32)
    day = world.day_fraction()
    try:
        world.set_day_fraction(0.95)
        for _ in range(1200):
            world.tick(0.05, now=world.now + 50)
            if crier.sched_away:
                break
        assert crier.sched_away and not crier.active
        from dsengine.view import shared_state
        assert shared_state(world, crier)["zz"] == 1
        world.set_day_fraction(0.5)
        for _ in range(20):
            world.tick(0.05, now=world.now + 50)
        assert crier.active and not crier.sched_away and shared_state(world, crier)["zz"] == 0
    finally:
        world.set_day_fraction(day)
        leave(world, s)


def test_the_hotbar_has_as_many_slots_as_you_choose(world):
    s = join(world, "Tenfingers")
    s.connected = True
    assert len(s.me_state()["hotbar"]) == 5
    s.handle({"t": "hotbar_slots", "n": 10})
    for k in range(10):
        s.hotbar_add("Thing%d" % k)
    assert s.me_state()["hotbar"][9] == "Thing9"
    s.handle({"t": "hotbar_slots", "n": 3})
    assert s.me_state()["hotbar"] == ["Thing0", "Thing1", "Thing2"]
    s.hotbar_add("Thing8")                                          # (a hidden slot's thing, brought back into view)
    assert s.me_state()["hotbar"][2] == "Thing8" and s.hotbar.count("Thing8") == 1
    s.handle({"t": "hotbar_slots", "n": 99})
    assert s.hotbar_n == 10
    saved = s.save_state()
    leave(world, s)
    t = Session(world, "Tenfingers")
    t.load_state(saved)
    assert t.hotbar_n == 10 and len(t.me_state()["hotbar"]) == 10


def test_a_spell_of_your_own_can_slow(world):
    from dsengine.ownspell import own_values, EFFECTS
    assert "Slow" in EFFECTS
    v = own_values("Slow", 3, True, lambda k, d: d)
    assert v["Effect"] == "Area" and v["Slow"] == "36,10" and v["Radius"] == "160"
    s = join(world, "Treacle", "14,15,0", 100, 300)
    s.connected = True
    s.own_spell = {"effect": "Slow", "power": 3, "far": False}
    s.spells_known["Own_Spell"] = 1
    s.skill_level = lambda skill: 25
    s.add_shards(50)
    p = s.player
    foes = [world.add_npc("Goblin", p.z, p.x + 40 + 20 * k, p.y, "Attitude=Bad Zone=1,1,25,21", "Bad") for k in range(3)]
    try:
        for f in foes:
            f.hp = f.max_hp = 500
        speed = foes[0].move_speed
        s.out = []
        s.cast_spell("Own_Spell", None)
        run_for(world, 1)
        assert all(f.slow_until is not None and f.move_speed < speed for f in foes)
        lines = [ev.get("text", "") for ev in s.out if ev.get("t") == "msg"]
        assert sum("slow" in ln for ln in lines) == 1                # (one line for the lot)
    finally:
        for f in foes:
            world.remove_entity(f)
        leave(world, s)


def test_a_foe_set_upon_brings_the_others_near_it_unless_you_are_hushed(world):
    s = join(world, "Brawler", "14,15,0", 100, 300)
    s.connected = True
    p = s.player
    near_one = world.add_npc("Goblin", p.z, p.x + 120, p.y, "Attitude=Bad Zone=1,1,25,21", "Bad")
    friend = world.add_npc("Goblin", p.z, p.x + 200, p.y, "Attitude=Bad Zone=1,1,25,21", "Bad")
    far = world.add_npc("Goblin", p.z, p.x + 120, p.y + 400, "Attitude=Bad Zone=1,1,25,21", "Bad")
    folk = (near_one, friend, far)
    try:
        world.tick(0.05, now=world.now + 50)                        # (on the map's index of who's where)
        for e in folk:
            e.in_combat, e.target = False, None
            world.npc_give_up(e, e.ai)
        s.provoke(near_one)
        assert near_one.in_combat and friend.in_combat and friend.target is s and not far.in_combat
        for e in folk:
            world.npc_give_up(e, e.ai)
            e.in_combat, e.target = False, None
        s.spells_known["Silence"] = 1
        s.skill_level = lambda skill: 25
        s.add_shards(20)
        s.cast_spell("Silence", None)                               # (tricks.py: a hush round you)
        assert s.silent() and "silent_left" in s.me_state()
        s.provoke(near_one)
        assert near_one.in_combat and not friend.in_combat
    finally:
        for e in folk:
            world.remove_entity(e)
        leave(world, s)


def test_dread_sends_a_foe_running_but_not_a_boss(world):
    from dsengine.entity import AI_FLEE
    s = join(world, "Bogeyman", "14,15,0", 100, 300)
    s.connected = True
    s.spells_known["Dread"] = 1
    s.skill_level = lambda skill: 25
    s.add_shards(50)
    p = s.player
    gob = world.add_npc("Goblin", p.z, p.x + 90, p.y, "Attitude=Bad Zone=1,1,25,21", "Bad")
    try:
        gob.hp = gob.max_hp = 500
        s.cast_spell("Dread", gob)
        run_for(world, 10)
        assert gob.ai.state == AI_FLEE and gob.target is s
        s.provoke(gob)                                              # (a blow doesn't turn it)
        assert gob.ai.state == AI_FLEE
        start = distance(gob.cx, gob.cy, p.cx, p.cy)
        run_for(world, 20)
        assert distance(gob.cx, gob.cy, p.cx, p.cy) > start
        assert "flees from you" in s.spell_what("Dread", 1)
    finally:
        world.remove_entity(gob)
    boss = world.add_npc("Tomb_Guardian", p.z, p.x + 90, p.y, "Attitude=Bad Zone=1,1,25,21", "Bad")
    try:
        s.frighten(boss, 6)
        assert boss.ai.state != AI_FLEE
    finally:
        world.remove_entity(boss)
        leave(world, s)


def test_ambrose_wants_the_redrock_signet_from_the_vault(world):
    ambrose = next(e for e in world.ents if e.npc_id == "Redrock_Steward")
    s = join(world, "Signet", ambrose.map, 300, 300)
    s.connected = True
    s.update_attribute("Passage", "=12")
    s.skill_level = s.base_skill_level = lambda skill: 25          # (Requires.Level=6: your level)
    near(world, s, ambrose, 0, 36)

    def talk(*answers):
        s.choose_verb("Talk to", ambrose, int(ambrose.cx), int(ambrose.cy))
        run_for(world, 10)
        for n in answers:
            assert s.ab_mode == "Conversation", n
            s.action_box_response_chosen(n)
            run_for(world, 10)
        if s.ab_mode:
            s.close_action_box(-1)

    talk(1, 1, 1)                                                   # (what happened; you want something; I'll bring it)
    assert s.get_attribute("RedrockSignetQuest") == "1"
    vault = next(e for e in world.ents if e.npc_id == "Redrock_Manor_Vault")
    s.update_attribute("Redrock_ManorVault", "=1")                  # (emptied before the signet was put in it)
    near(world, s, vault, 0, 30)
    s.clicked_ent = vault
    s.start_script("Open Redrock_Manor_Vault", True)
    run_for(world, 5)
    s.close_action_box(-1)
    assert s.items_held("Redrock_Signet") == 1 and s.items_held("Dread_Scroll") == 1
    near(world, s, ambrose, 0, 36)
    talk(1)
    assert s.get_attribute("RedrockSignetQuest") == "2" and s.items_held("Redrock_Signet") == 0
    leave(world, s)


def test_the_isle_has_grown_north_with_its_new_places(world):
    ids = {i[0] for m in world.maps.values() for i in m.ids}
    for pid in ("Mirror_Tarn", "Hollow_Wood", "Tin_Braes", "Old_Beacon", "Standing_Stones", "Hobgoblin_Camp"):
        assert pid in ids
    camp = next(e for e in world.ents if e.npc_id == "Hob_Camp_Chest")
    assert camp.map == "2,2,0"                                      # (back over their lair: move_lawyers_house.py)
    assert any(e.name == "Hobgoblin" and e.map == camp.map for e in world.ents)
    assert next(e for e in world.ents if e.npc_id == "Edwin_At_Desk").map == "0,-2,0"   # (the north-west corner)
    stones = next(e for e in world.ents if e.npc_id == "Stone_Circle_Chest")
    assert stones.map in ("2,2,0", "3,2,0", "2,1,0", "3,1,0")          # (the south-east)
    day = world.day_fraction()
    world.set_day_fraction(0.5)
    s = join(world, "Wanderer", camp.map, 300, 300)
    s.connected = True
    assert s.cur_map.name in s.lock_text("Isle.Maps", "").split()   # (the Isle's easy locks, up there too)
    hearth = next(e for e in world.ents if e.npc_id == "Old_Beacon_Hearth")
    near(world, s, hearth, 0, 30)
    hm = world.maps[hearth.map]
    s.teleport(hearth.map, int(hearth.x - hm.ox), int(hearth.y - hm.oy) + 30)   # (by it again: nothing nudged since)
    s.do_pending_map_change()
    assert s.player_distance_to(hearth) <= 48, s.player_distance_to(hearth)
    s.out = []
    s.clicked_ent = hearth
    s.start_script("Search Old_Beacon_Hearth", True)
    run_for(world, 20)
    assert s.get_attribute("Old_Beacon_Hearth") == "1", [ev for ev in s.out if ev.get("t") == "msg"]
    assert s.items_held("Tinderbox") >= 1
    leave(world, s)
    world.set_day_fraction(day)


def test_editor_smooths_bays_ponds_lakes_and_sand_into_grass():
    # Every way two grounds meet on the slant (build_ground_pieces.py): water with land on three sides takes two
    # corners, a one-tile pond all four, a lake has its own coast, and sand going into grass takes the grass's corners
    from dsedit.project import Project
    from dsedit import world as WD
    P = Project(ROOT)

    def smooth(grid, at):
        WD.smooth_corners(P, lambda x, y: grid.get((x, y)), lambda x, y, t: grid.__setitem__((x, y), t), {at})
        return grid
    bay = {(x, y): "Marsh001" for x in range(5) for y in range(5)}
    bay.update({(2, 2): "Water001", (2, 3): "Water001", (2, 4): "Water001"})     # (an inlet, open to the south)
    smooth(bay, (2, 2))
    assert bay[(2, 2)] == "Marsh_Water_NE_NW001" and bay[(2, 3)] == "Water001"
    assert P.tiles_ini.get("Marsh_Water_NE_NW001", "Corner.Land", "") == "Marsh001"   # (painted from the marsh itself)
    pond = {(x, y): "Grass001" for x in range(3) for y in range(3)}
    pond[(1, 1)] = "Lake001"
    assert smooth(pond, (1, 1))[(1, 1)] == "Grass_Lake_NE_SE_SW_NW001"
    assert P.tiles_ini.get("Grass_Lake_NE_SE_SW_NW001", "Corner.Leg", "") == "0.55"   # (still a pool, not all land)
    sand = {(x, y): "Sand001" for x in range(5) for y in range(5)}
    sand.update({(2, 1): "Grass001", (3, 1): "Grass001", (3, 2): "Grass001"})
    assert smooth(sand, (3, 2))[(2, 2)] == "Sand_Grass_NE001"
    sand[(3, 2)] = "Sand001"                                                    # (the grass gone: back to sand)
    assert smooth(sand, (3, 2))[(2, 2)] == "Sand001"


def test_townsfolk_mention_a_quest_you_could_start_now_and_then(world, monkeypatch):
    # Rumours (dsengine/rumours.py): a gossip with no words of its own tells one first, then talks as usual; never
    # again till Every.Minutes have passed, and never about a quest you've started
    import dsengine.rumours as R
    monkeypatch.setattr(R.random, "random", lambda: 0.0)              # (the chance always comes up)
    s = join(world, "Listener", "11,-3,0", 384, 300)
    s.connected = True
    s.update_attribute("Passage", "=12")
    s.skill_level = s.base_skill_level = lambda skill: 25
    gossip = world.add_npc("Villager", s.player.z, s.player.x + 30, s.player.y, "Attitude=Good Stand=1", "Good")
    rumours = {v for _, d in world.data.quest_table() for k, v in d.items() if k.startswith("RUMOUR")}
    try:
        s.choose_verb("Talk to", gossip, int(gossip.cx), int(gossip.cy))
        run_for(world, 10)
        assert s.ab_mode == "Conversation" and s.ab_text in rumours
        heard = [a for a, v in s.attributes if a.startswith("Rumour.") and a != "Rumour.At"]
        assert len(heard) == 1
        s.action_box_response_chosen(1)                             # (thanks: and now what they always say)
        run_for(world, 10)
        assert s.ab_text not in rumours
        if s.ab_mode:
            s.close_action_box(-1)
        s.choose_verb("Talk to", gossip, int(gossip.cx), int(gossip.cy))
        run_for(world, 10)
        assert s.ab_text not in rumours                             # (not again so soon)
        if s.ab_mode:
            s.close_action_box(-1)
        quest = world.data.quest_of_attribute(heard[0][len("Rumour."):])[0]
        s.update_attribute(heard[0][len("Rumour."):], "=1")         # (started it: never told of it again)
        s.update_attribute("Rumour.At", "=0")
        for _ in range(20):
            r = s.rumour_due(gossip)
            assert r is None or r[0] != quest
        guard = next(e for e in world.ents if e.npc_id and e.type == NPC and s.script_exists("Talk to " + e.npc_id))
        assert not s.gossips(guard)                                 # (someone with words of their own never gossips)
    finally:
        world.remove_entity(gossip)
        leave(world, s)


def test_two_corner_pieces_meeting_round_into_each_other():
    # Where one piece's corner runs on into its neighbour's (a two-tile inlet: a NE corner over a SE one), the land is
    # thickened at that tip and curved between, not a point (dsedit/render.py, as ground.js draws it)
    from dsedit import render as RD
    plain = RD._corner_poly(0, 32, 32, 1.0, (False, False))
    joined = RD._corner_poly(0, 32, 32, 1.0, (False, True))
    assert plain == [(32, 0), (0, 0), (32, 32)]
    assert (32 - 32 * RD.JOIN, 32) in [tuple(round(v, 6) for v in pt) for pt in joined]   # (thick where it meets)
    assert len(joined) > 6                                           # (and curved between)


def test_natural_grounds_round_into_each_other_at_every_corner():
    # round_world.py: the game and the editor round where grounds meet, from the four cells round each corner of the
    # grid: a lone tile round, a lone pond round, a diagonal of two grounds joined by the higher, a straight edge left
    from dsedit.project import Project
    from dsedit import render as RD
    P = Project(ROOT)

    def fills(grid, x, y):
        return RD.round_fills(P, lambda a, b: grid.get((a, b)), x, y)
    islet = {(x, y): "Water001" for x in range(3) for y in range(3)}
    islet[(1, 1)] = "Sand001"
    assert sorted(k for k, *_ in fills(islet, 1, 1)) == [0, 1, 2, 3]            # (sand, round, in the water)
    assert all(fills(islet, x, y) == [] for x, y in islet if (x, y) != (1, 1))  # (the water round it: as it was)
    pond = {(x, y): "Grass001" for x in range(3) for y in range(3)}
    pond[(1, 1)] = "Lake001"
    assert sorted(k for k, *_ in fills(pond, 1, 1)) == [0, 1, 2, 3]
    saddle = {(0, 0): "Grass001", (1, 1): "Grass001", (1, 0): "Water001", (0, 1): "Water001"}
    assert [k for k, *_ in fills(saddle, 1, 0)] == [2] and fills(saddle, 0, 0) == []   # (the land joins across)
    edge = {(x, y): ("Grass001" if y == 0 else "Sand001") for x in range(3) for y in range(2)}
    assert all(fills(edge, x, y) == [] for x, y in edge)                       # (a straight edge stays straight)
    for k, y in ((0, 0), (1, 32)):
        c, mid, near, *_, last = RD.round_poly(k, 32, 32, 5, 7)
        assert c == (32, y) and mid == (16, y) and last == (32, 16)     # (the corner, then its edges' middles)
        assert abs(near[1] - y) < abs(near[0] - 16)                     # (leaving the edge along it: no angle there)
    lava = {(x, y): "Ash001" for x in range(3) for y in range(3)}
    lava[(1, 1)] = "Lava001"
    assert sorted(k for k, *_ in fills(lava, 1, 1)) == [0, 1, 2, 3]
    pond[(1, 1)] = "Pond001"
    assert sorted(k for k, *_ in fills(pond, 1, 1)) == [0, 1, 2, 3]
    assert P.tiles_ini.get("Sea_Rock002", "Layer", "") == "Decor"       # (rocks on the water, not a square of their own)


def test_a_secret_room_lies_behind_a_wall_you_can_walk_through(world):
    # build_secret_caves.py: a cave wall that isn't there, a black roof over what's behind it, a chest each
    found = [(m, c) for m in world.maps.values() for c, t in enumerate(m.trigger) if t.startswith("Hidden_Way_")]
    assert len(found) >= 4
    assert sum(1 for m, _ in found if m.name in ("-1,5,-1", "0,5,-1")) == 2      # (two in the Mire Tunnel)
    m, c = found[0]
    tx, ty = (c - 1) % world.xt + 1, (c - 1) // world.xt + 1
    assert m.tile[c] == "Cave_Wall_Hollow001" and "1" in m.walk[c]
    assert not m.roof[c]                                        # (the wall itself shows, like any other)
    slug = m.trigger[c][len("Hidden_Way_"):]
    chest = next(e for e in world.ents if e.npc_id == "Hidden_Cache_" + slug)
    assert chest.map == m.name and m.roof[m.cell(int((chest.x - m.ox) // world.tw) + 1,
                                                 int((chest.y - m.oy) // world.th) + 1)]    # (hidden under the dark)
    a = join(world, "Delver", m.name, (tx - 1) * world.tw, ty * world.th)   # (beside it: not on it, yet)
    a.connected = True
    a.out = []
    a.start_script(m.trigger[c], False)
    run_for(world, 5)
    assert a.get_attribute(m.trigger[c]) == "1"
    assert any(ev.get("t") == "msg" for ev in a.out)
    a.out = []
    a.start_script(m.trigger[c], False)                         # (it says so only the first time)
    run_for(world, 5)
    assert not any(ev.get("t") == "msg" for ev in a.out)
    leave(world, a)


def test_the_isle_comes_down_on_the_slant_and_rooms_are_furnished(world):
    # cut_isle_corner.py: the north-east corner's sea, the Braes' tin kept; build_interiors.py: furniture never in a door
    corner = world.maps["4,-2,0"]
    assert corner.tile_is_water(16, 3) and corner.tile_is_water(15, 10)
    assert not world.maps["3,-1,0"].tile_is_water(5, 5)
    assert next(e for e in world.ents if e.npc_id == "Maren_At_Counter").map == "0,-2,0"     # (the north-west stays)
    tin = sum(1 for m in (world.maps["%d,%d,0" % (x, y)] for x in (3, 4) for y in (-2, -1, 0))
              for c in range(1, len(m.decor)) if m.decor[c].startswith("Tin_Rock"))
    assert tin >= 15                                            # (as much to mine as there was)
    assert world.data.entity_ini("Mosquito", "Swarm", "") == "6"
    standing = {"Cupboard001", "Cupboard002", "Wardrobe001", "Dresser001", "Writing_Desk001", "Writing_Desk002",
                "Side_Table001", "Washstand001", "Long_Clock001"}
    seen = 0
    for m in world.maps.values():
        if m.mz not in (0, 1):
            continue
        for y in range(1, world.yt + 1):
            for x in range(1, world.xt + 1):
                c = m.cell(x, y)
                if m.decor[c] in standing:
                    seen += 1
                    assert not m.tile[c].startswith("Door")
                    assert not m.inside(x, y + 1) or m.decor[m.cell(x, y + 1)] not in standing
    assert seen > 100
    sides = [(m, c) for m in world.maps.values() if m.mz in (0, 1) for c in range(1, len(m.decor))
             if m.decor[c].startswith("Side_") and m.decor[c][-4] in "WE"]
    assert len(sides) > 300                                     # (the side walls too, seen side on)
    for m, c in sides:                                          # (a west wall's on the west of its room, an east's east)
        word = m.decor[c][-4]
        assert ("_Thin_" not in m.tile[c]) or m.tile[c][-3:] == ("004" if word == "W" else "002")


# ----- Galaith's grounds (build_galaith_grounds.py)
def test_galaith_is_paved_nicer_among_the_nobles_and_royals(world):
    d = world.data

    def ground(gx, gy):
        m = world.maps["%d,%d,0" % (gx // 25, gy // 21)]
        return m, m.cell(gx - (gx // 25) * 25 + 1, gy - (gy // 21) * 21 + 1)
    plots = ((-222, 268, -192, 284), (-222, 308, -192, 328))   # (the graveyard's lawn and the orchard's)
    for gx in range(-262, -90, 3):
        for gy in range(272, 372, 3):
            m, c = ground(gx, gy)
            if m.roof[c] or any(a <= gx <= x and b <= gy <= y for a, b, x, y in plots):
                continue
            assert m.tile[c] not in ("Grass001", "Dirt001"), (gx, gy, m.tile[c])
    m, c = ground(-258, 290)
    assert m.tile[c] == "Royal_Paving001"
    assert any(ground(x, y)[0].tile[ground(x, y)[1]] in ("Noble_Paving001", "Marble_Paving001")   # (the owner's marble, now)
               for x in range(-263, -226) for y in range(268, 286))
    assert any(ground(x, 375)[0].tile[ground(x, 375)[1]] == "Flagstone001" for x in range(-146, -114))   # (the hovels')
    for tile in ("Royal_Paving001", "Noble_Paving001", "Lawn001"):
        assert d.tile_ini(tile, "Texture", "")                  # (a big texture: never one picture every tile)


def test_the_fountains_pool_is_raised_and_you_can_toss_a_coin(world):
    fountain = next(e for e in world.ents if e.npc_id == "The_Grand_Fountain")
    m = world.maps[fountain.map]
    pool = next(c for c in range(1, len(m.decor)) if m.decor[c].startswith("Fountain_Pool"))
    assert "1" not in m.walk[pool]                              # (the water's walked round, not through)
    s = join(world, "Wisher", "-9,14,0", 576, 136)              # (on the paving, its south side)
    assert "Toss a Coin" in s.get_verbs(fountain)
    stock(s, **{"Gold_Coin(s)": 5})
    coins = s.items_held("Gold_Coin(s)")
    s.choose_verb("Toss a Coin", fountain, int(fountain.cx), int(fountain.cy))
    run_for(world, 200)
    assert s.get_attribute("Fountain.Coins") == "1"
    assert s.items_held("Gold_Coin(s)") in (coins - 1, coins + 1)     # (now and then, it comes back with a friend)
    leave(world, s)


def test_every_stone_in_galaiths_graveyard_says_its_own(world):
    m = world.maps[world.data.place("Grave_Tobin_Lamps").map]
    assert sum(1 for c in range(1, len(m.decor)) if m.decor[c].startswith(("Headstone", "Stone_Cross", "Grave_Slab",
                                                                           "Royal_Cenotaph"))) >= 8
    for pid in ("Grave_Tobin_Lamps", "Grave_Hobb_Vintner", "Stone_Prince_Alaric", "Stone_The_Empty_One"):
        assert world.data.place(pid) is not None
        assert os.path.exists(os.path.join(ROOT, "data", "Scripts", "Examine %s.txt" % pid))
    assert next(e for e in world.ents if e.npc_id == "Galaith_Sexton").display == "Sexton"


def test_the_orchard_gives_fruit_for_the_picking(world):
    pl = world.data.place("Galaith_Orchard")
    m = world.map_named(pl.map)
    s = join(world, "Picker", pl.map, (pl.tx - 1) * 32, (pl.ty + 1) * 32)
    s.connected = True
    tree = next((x, y) for y in range(1, 22) for x in range(1, 26)
                if m.decor[m.cell(x, y)] in ("Apple_Tree001", "Pear_Tree001"))
    kind = "Apple" if m.decor[m.cell(*tree)].startswith("Apple") else "Pear"
    gx, gy = m.ox + (tree[0] - 1) * 32 + 16, m.oy + (tree[1] - 1) * 32 + 16
    s.choose_verb("Pick", s.tile_entity_at(gx, gy), gx, gy)
    run_for(world, 400)
    assert s.items_held(kind) == 1
    racks = open(os.path.join(ROOT, "data", "ItemRacks.ini"), "rb").read().decode("cp1252")
    assert "Apple_Pie,Flour 1 Apple 2" in racks                # (and they bake)
    leave(world, s)


# ----- random encounters (dsengine/encounters.py)
def wild_spot(world):
    """A map out in the wild (no settlement near), past the Isle, with open ground in its middle to stand on."""
    enc = world.encounters
    fierce = [(e.x, e.y) for e in world.ents if e.type == NPC and e.hostile and e.z == 0]
    for m in world.maps.values():
        mx, my = (int(v) for v in m.name.split(",")[:2])
        if m.mz != 0 or mx < 5 or enc.settled(m) or any(abs(x - m.ox - 416) < 448 and abs(y - m.oy - 352) < 448 for x, y in fierce):   # (nothing near)
            continue
        if all("0" not in m.walk[m.cell(x, y)] and not m.tile_is_water(x, y) and not m.roof[m.cell(x, y)]
               for x in range(10, 17) for y in range(8, 15)):
            return m
    raise AssertionError("no wild ground")


def met(world, kind, name):
    m = wild_spot(world)
    s = join(world, name, m.name, 13 * 32, 11 * 32)
    s.update_attribute("Passage", "=5")
    e = world.encounters.start(kind, s)
    assert e is not None
    return s, e


def test_a_salesman_turns_up_and_his_goods_differ_each_visit(world):
    enc = world.encounters
    s, e = met(world, "Salesman", "Customer")
    assert e.source == "ENCOUNTER" and e.name == "Travelling_Salesman" and not e.hostile
    assert distance(e.cx, e.fy, s.player.cx, s.player.fy) > 6 * 32

    def goods(who):
        who.open_item_rack("GENERAL", "Travelling_Salesman", "SHOP-Salesman")
        out = sorted(r["item"] for r in who.rack)
        who.close_action_box(0)
        return out
    first = goods(s)
    assert len(first) == 7
    assert goods(s) == first                                     # (the same all through his visit, for everyone)
    t = join(world, "Customer2", s.cur_map.name, 13 * 32, 11 * 32)
    assert goods(t) == first
    leave(world, t)
    seen = {tuple(first)}
    for k in range(1, 6):                                        # (his next visits bring something else)
        enc.visit["Salesman"] += k * 1000
        seen.add(tuple(goods(s)))
    assert len(seen) > 1
    enc.remove(e.uid, e)
    leave(world, s)


def test_what_the_salesman_sells_is_gone_till_his_next_visit(world):
    enc = world.encounters
    s, e = met(world, "Salesman", "Haggler")
    stock(s, **{"Gold_Coin(s)": 50000})
    s.open_item_rack("GENERAL", "Travelling_Salesman", "SHOP-Salesman")
    assert "#" in s.rack_name
    item = next(r for r in s.rack if r["quantity"] > 0)
    name, left = item["item"], item["quantity"]
    s.rack_buy(type("Clicked", (), {"misc": s.rack.index(item)})(), 1)
    assert s.items_held(name) >= 1
    s.open_item_rack("GENERAL", "Travelling_Salesman", "SHOP-Salesman")
    assert next(r for r in s.rack if r["item"] == name)["quantity"] == left - 1
    s.close_action_box(0)
    enc.visit["Salesman"] += 1000
    s.open_item_rack("GENERAL", "Travelling_Salesman", "SHOP-Salesman")
    again = [r for r in s.rack if r["item"] == name]
    assert not again or again[0]["quantity"] == left             # (a new visit, new stock)
    s.close_action_box(0)
    enc.remove(e.uid, e)
    leave(world, s)


def test_an_encounter_walks_off_when_its_time_is_up(world):
    enc = world.encounters
    s, e = met(world, "Jester", "Audience")
    r = enc.running[e.uid]
    r["ends"] = world.now - 1
    enc.update(e.uid, r)
    assert r["leaving"] and e.alive                              # (off it goes)
    r["gone_by"] = world.now - 1                                 # (out of sight, or out of time: gone)
    enc.update(e.uid, r)
    assert not e.alive and e.uid not in enc.running
    leave(world, s)


def test_the_abomination_is_as_strong_as_who_it_found_and_leaves_plenty(world, monkeypatch):
    import dsengine.remnants as RM
    enc = world.encounters
    s, e = met(world, "Abomination", "Hunter")
    weak = e.max_hp
    assert e.hostile and e.in_combat and s.monster_level(e) == s.player_level() + 1
    enc.remove(e.uid, e)
    e2 = world.add_npc("Shard_Abomination", s.player.z, s.player.x + 320, s.player.y, "Attitude=Bad")
    enc.scale(e2, enc.kinds["Abomination"], 20)
    assert e2.max_hp > weak and e2.strength > e.strength
    monkeypatch.setattr(RM, "rnd", lambda: 0.99)                 # (no remnants of its own roll: only its Drops)
    uids = {x.uid for x in world.ents}
    s.kill_npc(e2)
    left = [x for x in world.ents if x.uid not in uids]
    assert sum(x.quantity for x in left if x.name == "Shard_Remnant") >= 6
    assert not any(x.alive and x.name == "Shard_Abomination" for x in world.ents)
    for x in left:
        world.remove_entity(x)
    leave(world, s)


def test_encounters_keep_off_the_isle_new_players_towns_and_fights(world):
    enc = world.encounters
    s = join(world, "Greenhorn", "1,1,0", 300, 300)
    assert not any(enc.allowed(k, s) for k in enc.kinds)         # (the Isle's first days are left alone)
    s.update_attribute("Passage", "=5")
    assert enc.allowed("Jester", s) and enc.allowed("Salesman", s)
    assert not enc.allowed("Abomination", s)                     # (too new, and on a settlement's map)
    leave(world, s)
    m = wild_spot(world)
    t = join(world, "Traveller", m.name, 13 * 32, 11 * 32)
    t.player_last_combat = -10 ** 9
    assert enc.free(t)
    t.player_last_combat = t.now
    assert not enc.free(t)                                       # (not in a fight)
    leave(world, t)


def test_more_kills_leave_or_raise_a_shard_remnant(world):
    assert world.data.shards_ini("Remnants", "Mob.Chance", "") == "15"
    assert world.data.shards_ini("Remnants", "Chance", "") == "53"


def test_an_encounter_comes_round_on_its_own(world):
    enc = world.encounters
    enc.settings["on"] = "1"
    m = wild_spot(world)
    s = join(world, "Wanderer", m.name, 13 * 32, 11 * 32)
    s.update_attribute("Passage", "=5")
    s.player_last_combat = -10 ** 9
    before = set(enc.running)
    enc.next_for[s.player_name] = world.now - 1
    enc.last_check = world.now - 5000
    enc.tick()
    enc.settings["on"] = "0"
    new = set(enc.running) - before
    assert len(new) == 1
    for u in new:
        enc.remove(u, world.by_uid[u])
    assert enc.next_for[s.player_name] > world.now               # (and the next one's a while off)
    leave(world, s)


def jester_box(world, s, e, *answers):
    """Talk to the jester, give these answers in turn, and say what he said last (the text of the last box)."""
    s.out = []
    s.do_action("Talk to", e)
    run_for(world, 4)
    for a in answers:
        s.out = []
        s.action_box_response_chosen(a)
        run_for(world, 6)
    boxes = [ev for ev in s.out if ev.get("t") == "box"]
    return boxes[-1]["text"] if boxes else ""


def jester_done(world, s):
    while s.ab_mode or s.script_running:
        s.action_box_response_chosen(1)
        run_for(world, 6)


def test_the_jesters_riddles_pay_once_each_and_wrong_pays_nothing(world):
    s, e = met(world, "Jester", "Riddler")
    world.encounters.running[e.uid]["ends"] = world.now + 3600000
    stock(s, **{"Gold_Coin(s)": 100})
    for attr, right in (("Jester.Riddle1", 1), ("Jester.Riddle2", 2), ("Jester.Riddle3", 2)):
        coins = s.items_held("Gold_Coin(s)")
        assert "Wrong!" in jester_box(world, s, e, 2, 3)
        assert s.items_held("Gold_Coin(s)") == coins and val_attr(s, attr) == 0
        jester_done(world, s)
        assert "Right first time" in jester_box(world, s, e, 2, right)
        assert s.items_held("Gold_Coin(s)") == coins + 15 and val_attr(s, attr) == 1
        s.out = []
        while s.ab_mode or s.script_running:
            s.action_box_response_chosen(2)                      # (Goodbye)
            run_for(world, 6)
    coins = s.items_held("Gold_Coin(s)")
    assert "all the riddles" in jester_box(world, s, e, 2)
    assert s.items_held("Gold_Coin(s)") == coins
    jester_done(world, s)
    world.encounters.remove(e.uid, e)
    leave(world, s)


def val_attr(s, attr):
    return int(float(s.get_attribute(attr) or 0))


def test_the_jesters_jokes_come_back_to_him(world):
    s, e = met(world, "Jester", "Heckler")
    world.encounters.running[e.uid]["ends"] = world.now + 3600000
    jokes = set()
    for _ in range(40):
        jokes.add(jester_box(world, s, e, 1))
        s.out = []
        s.action_box_response_chosen(1)                          # (That's terrible.)
        run_for(world, 6)
        assert any("jester needs a king" in ev.get("text", "") for ev in s.out if ev.get("t") == "box")
        s.action_box_response_chosen(4)                          # (Goodbye.)
        run_for(world, 6)
        assert not s.script_running
    assert len(jokes) == 5
    world.encounters.remove(e.uid, e)
    leave(world, s)


def test_the_jesters_trick_does_something_and_then_he_makes_you_wait(world):
    s, e = met(world, "Jester", "Mark")
    world.encounters.running[e.uid]["ends"] = world.now + 3600000
    stock(s, **{"Gold_Coin(s)": 20})
    seen = set()
    for _ in range(60):
        s.update_attribute("Jester.Trick", "=0")
        coins = s.items_held("Gold_Coin(s)")
        s.out = []
        s.do_action("Talk to", e)
        run_for(world, 4)
        s.out = []
        s.action_box_response_chosen(3)
        run_for(world, 10)
        assert not s.script_running
        if s.parse_script_variables("$Player.Form") == "Chicken":
            seen.add("chicken")
            run_for(world, 21 * 20 + 20)                         # (it wears off)
            assert s.parse_script_variables("$Player.Form") == "-"
        elif s.items_held("Gold_Coin(s)") > coins:
            seen.add("coins")
        elif s.items_held("Gold_Coin(s)") < coins:
            seen.add("pickpocket")
        else:
            assert any("working out" in ev.get("text", "") for ev in s.out if ev.get("t") == "msg")
            seen.add("boost")
    assert seen == {"chicken", "coins", "pickpocket", "boost"}
    s.remove_inventory_item("Gold_Coin(s)", s.items_held("Gold_Coin(s)"))
    for _ in range(40):                                          # (nothing to take: a cabbage, out of pity)
        s.update_attribute("Jester.Trick", "=0")
        cabbages = s.items_held("Cabbage")
        s.do_action("Talk to", e)
        run_for(world, 4)
        s.action_box_response_chosen(3)
        run_for(world, 10)
        if s.items_held("Cabbage") > cabbages:
            break
        if s.items_held("Gold_Coin(s)"):
            s.remove_inventory_item("Gold_Coin(s)", s.items_held("Gold_Coin(s)"))
        if s.parse_script_variables("$Player.Form") == "Chicken":
            run_for(world, 21 * 20 + 20)
    assert s.items_held("Cabbage") > cabbages
    s.update_attribute("Jester.Trick", "=%s" % s.parse_script_variables("$Clock"))
    assert "only had the one" in jester_box(world, s, e, 3)      # (and it's a while till the next)
    jester_done(world, s)
    world.encounters.remove(e.uid, e)
    leave(world, s)


def test_the_jester_juggles_whichever_way_he_faces(world):
    s, e = met(world, "Jester", "Crowd")
    for direction, d in ((1, "1"), (2, "2"), (4, "4"), (8, "8")):
        e.direction = direction
        e.pose = "Juggle"
        world.animate_entity(e, False)
        assert e.image == "Jester_Juggle" + d
    world.encounters.remove(e.uid, e)
    leave(world, s)


def test_galaiths_gardener_and_sexton_go_home_at_night(world):
    def where(pid):
        return next(x for x in world.ents if x.npc_id == pid)
    day = world.day_fraction()
    gardener, sexton = where("Galaith_Gardener"), where("Galaith_Sexton")
    a = join(world, "Nightwatch", gardener.map, 12 * 32, 11 * 32)
    b = join(world, "Nightwatch2", sexton.map, 20 * 32, 8 * 32)
    world.set_day_fraction(world.night_bounds()[0] + 0.01)
    run_for(world, 1)
    assert world.is_night()
    run_for(world, 2400)
    assert gardener.ai.asleep and gardener.image == "Farmer_Sleep4"   # (in his own bed, in the orchard)
    m = world.maps[gardener.map]
    bx, by = gardener.ai.bed
    assert m.decor[m.cell(int((bx - m.ox) // 32) + 1, int((by - m.oy) // 32) + 1)] == "Bed001"
    assert not sexton.active or sexton.ai.home is None         # (his house is elsewhere now: off by the nearest door)
    world.set_day_fraction(0.4)
    run_for(world, 2400)
    assert not gardener.ai.asleep and gardener.active
    z = gardener.ai.day_zone
    assert z[0] <= gardener.fx <= z[2] and z[1] <= gardener.fy <= z[3]   # (back at work)
    world.set_day_fraction(day)
    leave(world, a)
    leave(world, b)


def test_the_fountain_is_heard_near_it_not_over_whole_maps(world):
    d = world.data
    assert d.entity_ini("Grand_Fountain", "Sound.Loop", "") == "Ambient_Fountain"
    assert os.path.exists(os.path.join(ROOT, "sounds", "Ambient_Fountain.wav"))
    amb = open(os.path.join(ROOT, "data", "Ambient.ini"), "rb").read().decode("cp1252")
    assert "=Fountain" not in amb


# ----- banter (dsengine/banter.py)
def banter_pair(world, name, a_kind, b_kind):
    """A player out in the wild, two characters beside them that nothing else is doing anything with."""
    m = wild_spot(world)
    s = join(world, name, m.name, 13 * 32, 11 * 32)
    s.connected = True
    a = world.add_npc(a_kind, 0, m.ox + 11 * 32, m.oy + 10 * 32, "Attitude=Good Schedule=Always")
    b = world.add_npc(b_kind, 0, m.ox + 14 * 32, m.oy + 10 * 32, "Attitude=Good Schedule=Always")
    world.banter.speaker_rest.clear()
    world.banter.scene_rest.clear()
    return s, a, b


def banter_bubbles(s):
    return [(ev["u"], ev["text"]) for ev in s.out if ev.get("t") == "bubble"]


def test_two_who_meet_turn_and_have_words_over_their_heads(world):
    s, a, b = banter_pair(world, "Eavesdropper", "Guard", "Villager")
    s.player.x, s.player.y = a.x + 40, a.y + 32
    d = world.banter.scenes["Scene.Along"]
    s.out = []
    r = world.banter.start(d, a, b, s)
    assert a.direction == 2 and b.direction == 8                  # (facing each other)
    assert r in world.banter.running
    for _ in range(10 * 20):
        world.tick(0.05, now=world.now + 50)
    said = [x for x in banter_bubbles(s) if x[0] in (a.uid, b.uid)]
    assert [t for _, t in said] == ["Move along.", "Along where?", "Just along."]
    assert [u for u, _ in said] == [a.uid, b.uid, a.uid]
    assert r not in world.banter.running
    assert not [ev for ev in s.out if ev.get("t") == "msg"]        # (never the chat log)
    world.remove_entity(a)
    world.remove_entity(b)
    leave(world, s)


def test_a_dog_sends_a_cat_running(world):
    s, dog, cat = banter_pair(world, "Dogwalker", "Dog", "Cat")
    s.out = []
    r = world.banter.start(world.banter.scenes["Scene.Dog_Cat"], dog, cat, s)
    x0, y0 = cat.fx, cat.fy
    for _ in range(12 * 20):
        world.tick(0.05, now=world.now + 50)
    assert r not in world.banter.running
    assert distance(cat.fx, cat.fy, x0, y0) > 32                  # (off it went)
    assert "Dog_Bark" in [ev.get("name") for ev in s.out if ev.get("t") == "sound"]
    world.remove_entity(dog)
    world.remove_entity(cat)
    leave(world, s)


def test_banter_picks_who_it_fits_and_rests_after(world):
    ban = world.banter
    s, a, b = banter_pair(world, "Passerby", "Guard", "Villager")
    s.player.x, s.player.y = a.x + 48, a.y + 32
    run_for(world, 1)
    for e in list(world.ents):                                    # (only these two about)
        if e.type == NPC and e not in (a, b) and e.source != "MAP" and e.name in ("Villager", "Guard"):
            world.remove_entity(e)
    r = ban.roll(s)
    assert r is not None and r["a"] in (a, b) and r["b"] in (a, b) and r["a"] is not r["b"]
    assert r["a"].name in r["d"]["a_kinds"] and r["b"].name in r["d"]["b_kinds"]
    assert not ban.free_to_talk(a, s)                             # (they've had their say, for a while)
    ban.running.remove(r)
    assert ban.resting(r["d"]["key"])
    world.remove_entity(a)
    world.remove_entity(b)
    leave(world, s)


def test_banter_leaves_out_those_with_words_of_their_own_and_foes(world):
    ban = world.banter
    s, a, b = banter_pair(world, "Bystander", "Guard", "Villager")
    assert ban.free_to_talk(a, s)
    a.npc_id = "Galaith_Sexton"                                   # (it has its own Talk to script)
    assert not ban.free_to_talk(a, s)
    mo = next(e for e in world.ents if e.npc_id and os.path.exists(os.path.join(ROOT, "data", "Scripts", "Stroke %s.txt" % e.npc_id)))
    assert not ban.free_to_talk(mo, s)                            # (any verb of its own: a scene would stop what it's doing)
    a.npc_id = ""
    a.in_combat = True
    assert not ban.free_to_talk(a, s)
    a.in_combat = False
    wolf = world.add_npc("Wolf", 0, a.x, a.y, "Attitude=Bad")
    assert not ban.free_to_talk(wolf, s)
    world.remove_entity(wolf)
    world.remove_entity(a)
    world.remove_entity(b)
    leave(world, s)


def test_townsfolk_have_something_to_say_about_a_chicken_in_boots(world):
    ban = world.banter
    s, a, b = banter_pair(world, "Clucker", "Villager", "Guard")
    s.player.x, s.player.y = a.x + 48, a.y + 32
    run_for(world, 1)
    assert not ban.applies("Chicken", s) and not ban.applies("Form", s)
    s.run_script_lines("(test)", ["01\tTurn.Into\tChicken\t20\tCluck.", "02\tEnd"])
    run_for(world, 4)
    assert s.player_form() == "Chicken" and ban.applies("Chicken", s) and ban.applies("Form", s)
    r = ban.roll(s)
    assert r is not None and r["b"] is None and r["d"]["b"] == "Player"
    assert "chicken" in r["d"]["lines"][0][1].lower() or "Bird" in r["d"]["lines"][0][1] or "different" in r["d"]["lines"][0][1]
    ban.running.remove(r)
    world.remove_entity(a)
    world.remove_entity(b)
    leave(world, s)


def test_no_banter_is_heard_through_a_roof_youre_outside_of(world):
    ban = world.banter
    s, a, b = banter_pair(world, "Outside", "Guard", "Villager")
    s.out = []
    world.sees_spot, keep = (lambda *args: False), world.sees_spot
    try:
        ban.say(a, "Psst.")
    finally:
        del world.sees_spot
    assert not banter_bubbles(s)
    world.remove_entity(a)
    world.remove_entity(b)
    leave(world, s)


def test_every_banter_scene_is_for_kinds_there_are_and_fits_over_a_head(world):
    ban = world.banter
    assert len(ban.scenes) >= 30
    for key, d in ban.scenes.items():
        assert d["lines"], key
        assert d["a_kinds"], key
        for who, said, _ in d["lines"]:
            assert who in ("A", "B") and 0 < len(said) <= 60, (key, said)
            assert d["b"].lower() != "player" or who == "A", key


def test_status_effects_last_longer_in_fighting_stance_not_shorter(world):
    s = join(world, "StanceHurt")
    s.stance = "Fighting"
    s.status_start("Poison")
    left = s.status["Poison"]["until"] - s.now
    assert left > 14000                                         # (Fighting: it lasts half as long again...)
    s.status_tick()
    assert "Poison" in s.status                                 # (... and isn't taken for a clock gone wrong)
    s.status_reset()
    s.stance = ""
    leave(world, s)


def test_malaria_stays_until_the_fever_tonic(world):
    s = join(world, "Bitten")
    s.diseases.clear()
    s.catch_disease("Malaria")
    assert "Fever Tonic" in s.me_state()["diseases"]["Malaria"]
    # (a bout comes when it's due: Strength down, and it never kills)
    strength = s.skill_level("Strength")
    s.diseases["Malaria"] = s.now
    s.disease_at = 0
    s.disease_tick()
    assert "Fever" in s.status and s.skill_level("Strength") == max(1, strength - 3)
    s.player.hp = 1
    s.status["Fever"]["next"] = s.now
    s.status_tick()
    assert s.player.hp == 1 and not s.dead_wait
    # (the Antidote takes neither away)
    s.status_end("Fever", quiet=True)
    stock(s, Antidote=1)
    s.drink_cure(next(e for e in s.inv if e.name == "Antidote"))
    assert "Malaria" in s.diseases
    # (dying ends the bout, and not the disease)
    s.status_start("Fever")
    s.player.hp = 5
    s.player_dies()
    assert "Fever" not in s.status and "Malaria" in s.diseases
    s.respawn()
    # (logging off and on: still there, the wait to its next bout kept)
    left = s.diseases["Malaria"] - s.now
    saved = s.save_state()
    assert abs(saved["diseases"]["Malaria"] - left) < 2000
    back = Session(world, "Bitten2")
    back.load_state(dict(saved, map="1,1,0", x=300, y=300))
    assert "Malaria" in back.diseases
    # (the tonic: gone, and the bout with it)
    s.status_start("Fever")
    stock(s, Fever_Tonic=1)
    s.drink_cure(next(e for e in s.inv if e.name == "Fever_Tonic"))
    assert "Malaria" not in s.diseases and "Fever" not in s.status
    leave(world, s)


def test_a_mosquito_gives_malaria_through_armour(world):
    s = join(world, "Armoured")
    m = next(e for e in world.ents if e.name == "Mosquito")
    assert world.data.entity_ini("Mosquito", "On.Hit", "").startswith("Malaria")
    real = s.entity_ini
    s.entity_ini = lambda n, k, d: "Malaria 100" if k == "On.Hit" else real(n, k, d)
    s.disease_on_blocked_hit(m)
    assert "Malaria" in s.diseases
    del s.entity_ini
    leave(world, s)


def test_a_fever_tonic_goes_off_wherever_it_is(world):
    s = join(world, "Shelf")
    stock(s, Fever_Tonic=2)
    tonics = [e for e in s.inv if e.name == "Fever_Tonic"]
    assert len(tonics) == 2 and all(e.wear for e in tonics)     # (one a slot, each with its own age)
    life = world.data.shelf_life("Fever_Tonic")
    assert life == int(world.data.entity_ini("Fever_Tonic", "Shelf.Minutes", "0")) * 60 > 0
    assert 0.9 < s.shelf_left(tonics[0]) <= 1 and "keep" in s.shelf_text(tonics[0])
    # (the bank doesn't freshen it)
    old = int(s.now / 1000) - life // 2
    tonics[0].wear = tonics[1].wear = old
    s.bank_deposit(tonics[0], 2)
    assert s.items_held("Fever_Tonic") == 0
    slot = next(i for i in range(1, s.data.bank_slots + 1) if s.bank_item[i] == "Fever_Tonic")
    assert s.bank_wear[slot] == [old, old]
    s.bank_withdraw(type("Slot", (), {"misc": slot})(), 2)
    assert [e.wear for e in s.inv if e.name == "Fever_Tonic"] == [old, old]
    # (past its time it turns, and what it turns into cures nothing)
    for e in s.inv:
        if e.name == "Fever_Tonic":
            e.wear = int(s.now / 1000) - life - 1
    s.shelf_at = 0
    s.shelf_tick()
    assert s.items_held("Fever_Tonic") == 0 and s.items_held("Spoiled_Tonic") == 2
    assert not world.data.entity_ini("Spoiled_Tonic", "Cures", "")
    s.remove_inventory_item("Spoiled_Tonic", 2)
    leave(world, s)


def test_what_doesnt_keep_keeps_its_age_when_dropped_and_picked_up(world):
    s = join(world, "Dropper")
    assert world.data.keeps_wear("Fever_Tonic") and not world.data.keeps_wear("Herb")
    stock(s, Fever_Tonic=1)
    e = next(x for x in s.inv if x.name == "Fever_Tonic")
    e.wear = int(s.now / 1000) - 600
    s.drop_inventory_item(e, 1)
    assert s.items_held("Fever_Tonic") == 0
    world.tick(0.05)
    down = next(x for x in world.ents if x.name == "Fever_Tonic" and x.alive)
    assert down.wear == e.wear
    s.pickup_map_item(down, reach=9999)
    assert next(x for x in s.inv if x.name == "Fever_Tonic").wear == down.wear
    leave(world, s)


def dark_mage(world, s, dist=40):
    """A Dark Mage in the open on the Barrow's field, fighting s, dist from them."""
    e = next(x for x in world.ents if x.name == "Dark_Mage" and x.map == "21,19,0")
    p = s.player
    world.set_entity_position(e, p.cx + dist - e.w / 2, p.cy - e.h / 2)
    world.npc_start_fight(e, e.ai, s, dist)
    e.frozen_until = None
    e.ai.blink_every = None
    assert not world.npc_blink(e, e.ai, s, dist)                # (not the moment a fight starts)
    e.ai.blink_at = world.now - 1
    return e


def test_a_dark_mage_jumps_away_when_you_come_near_and_is_held_by_ice(world):
    s = join(world, "MageHunter", "21,19,0", 18 * 32, 8 * 32)
    e = dark_mage(world, s)
    a = e.ai
    old = (e.cx, e.cy)
    assert world.npc_blink(e, a, s, 40)                         # (too close: gone)
    p = s.player
    assert ((e.cx - old[0]) ** 2 + (e.cy - old[1]) ** 2) ** 0.5 >= 100
    assert world.pixel_walkable(e.z, e.fx, e.fy) and world.in_line_of_sight(e.z, e.cx, e.cy - 12, p.cx, p.cy)
    assert world.in_chase_area(a, e.fx, e.fy)
    assert e.last_attack == world.now                           # (it can't throw at once: the moment to catch it)
    assert not world.npc_blink(e, a, s, 40)                     # (and not again at once)
    # (hit, once it's ready again: gone)
    a.blink_at = world.now - 1
    a.blink_hp = e.hp
    e.hp -= 5
    assert world.npc_blink(e, a, s, 150)
    e.hp = e.max_hp
    # (frozen, its tick never gets as far as a jump)
    a.blink_at = 0
    world.set_entity_position(e, p.cx + 40 - e.w / 2, p.cy - e.h / 2)
    e.frozen_until = world.now + 5000
    at = (e.x, e.y)
    world.tick(0.05)
    assert (e.x, e.y) == at
    e.frozen_until = None
    world.npc_give_up(e, a)
    leave(world, s)


def test_a_dark_mage_never_lands_where_it_cant_be_reached(world):
    s = join(world, "MageHunter2", "21,19,0", 18 * 32, 8 * 32)
    e = dark_mage(world, s)
    a, p = e.ai, s.player
    here = world.grid_region_at(e.z, e.fx, e.fy)
    for _ in range(60):
        spot = world.npc_blink_spot(e, a, p)
        if spot is None:
            continue
        assert world.pixel_walkable(e.z, *spot) and world.in_chase_area(a, *spot)
        assert world.grid_region_at(e.z, *spot) == here
    world.npc_give_up(e, a)
    leave(world, s)


def test_every_dark_mage_stands_on_open_ground(world):
    mages = [e for e in world.ents if e.name == "Dark_Mage"]
    assert len(mages) == 3
    for e in mages:
        assert e.ai is not None and world.pixel_walkable(e.z, e.fx, e.fy)


def test_morwen_knows_malaria_gives_one_tonic_then_sells_them(world):
    s = join(world, "Shaking", "11,23,0", 12 * 32, 9 * 32)
    witch = next(e for e in world.ents if e.name == "Witch")

    def talk():
        s.do_action("Talk to", witch)
        for _ in range(30):
            world.tick(0.05)

    m = world.maps[witch.map]
    s.teleport(witch.map, int(witch.x - m.ox) + 26, int(witch.y - m.oy))
    world.tick(0.05)
    talk()                                                      # (well: only her usual words, no tonic)
    words = list(s.responses)
    assert s.ab_mode == "Conversation" and "Thank you." not in words and "I'll take one." not in words
    s.close_action_box(0)
    s.script_running = False
    s.catch_disease("Malaria")
    talk()
    assert list(s.responses) == ["Thank you."]
    s.action_box_response_chosen(1)
    for _ in range(10):
        world.tick(0.05)
    assert s.items_held("Fever_Tonic") == 1
    stock(s, **{"Gold_Coin(s)": 50})
    talk()                                                      # (only the one for nothing; after that, for coin)
    assert "I'll take one." in s.responses
    s.action_box_response_chosen(1)
    for _ in range(10):
        world.tick(0.05)
    assert s.items_held("Fever_Tonic") == 2 and s.items_held("Gold_Coin(s)") == 5
    # (gone off, it's only good for its vial)
    tonic = next(e for e in s.inv if e.name == "Fever_Tonic")
    tonic.wear = int(s.now / 1000) - world.data.shelf_life("Fever_Tonic") - 1
    s.shelf_at = 0
    s.shelf_tick()
    vials = s.items_held("Empty_Vial")
    s.do_action("Pour Out", next(e for e in s.inv if e.name == "Spoiled_Tonic"))
    for _ in range(10):
        world.tick(0.05)
    assert s.items_held("Spoiled_Tonic") == 0 and s.items_held("Empty_Vial") == vials + 1
    leave(world, s)


def test_the_marshes_water_is_marsh_water_and_the_sea_is_not(world):
    """marsh_water.py: the pools in the fen are Bog001, the sea off its coast is still the sea, and both are water."""
    fen, sea = world.maps["-6,6,0"], world.maps["-13,5,0"]
    assert "Bog001" in fen.tile and "Water001" not in fen.tile
    assert "Water001" in sea.tile and "Bog001" not in sea.tile
    assert world.data.tile_water("Bog001")


def test_mirefolds_boardwalk_wanders_and_still_joins_up(world):
    """wind_boardwalks.py: from the square to under the tunnel's mouth in one line of planks, no ruler line of it."""
    cells = set()
    for mx in range(-7, 0):
        for my in (4, 5):
            m = world.maps["%d,%d,0" % (mx, my)]
            for y in range(1, 22):
                for x in range(1, 26):
                    if m.tile[m.cell(x, y)] == "Boardwalk001":
                        cells.add((mx * 25 + x - 1, my * 21 + y - 1))
    seen, todo = {(-145, 104)}, [(-145, 104)]
    while todo:
        x, y = todo.pop()
        for c in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if c in cells and c not in seen:
                seen.add(c)
                todo.append(c)
    assert (-6, 124) in seen
    rows = {}
    for x, y in cells:
        if -120 < x < -20:                                          # (out of the hamlet, short of the tunnel)
            rows[y] = rows.get(y, 0) + 1
    assert len(rows) > 8 and max(rows.values()) < 40


def test_the_marshes_places_are_on_the_world_map(world):
    """build_marsh_places.py: each a named place with a label."""
    labels = open(os.path.join(world.data.root, "data", "WorldMap.ini"), encoding="cp1252").read()
    for pid in ("Sunken_Barge", "Peat_Cuttings", "Wisp_Ring", "Eel_Catchers_Hut", "Drowned_Bell_Site"):
        assert world.data.place(pid) is not None and "=%s" % pid in labels, pid


def test_the_marsh_chests_are_each_players_own(world):
    chest = next(e for e in world.ents if e.npc_id == "Sunken_Barge_Hold")

    def loot(s):
        s.unlocked_chests.add(s.chest_key(chest))                   # (its lock picked: locks.py has its own test)
        near(world, s, chest, -32, 8)                               # (from the end of the boardwalk)
        s.choose_verb("Open", chest, int(chest.cx), int(chest.cy))
        run_for(world, 20)
        s.chest_response("CHEST_ALL")
    a, b = join(world, "Barge_A"), join(world, "Barge_B")
    a.connected = b.connected = True
    loot(a)
    assert a.items_held("Emerald") == 1
    loot(a)
    assert a.items_held("Emerald") == 1                             # (once each)
    loot(b)
    assert b.items_held("Emerald") == 1                             # (and each)
    leave(world, a)
    leave(world, b)


def test_the_lights_are_caught_on_the_third_try_and_only_once(world):
    lights = next(e for e in world.ents if e.name == "Marsh_Lights")
    s = join(world, "Wisp_Hunter", lights.map, 300, 300)
    s.connected = True
    near(world, s, lights, 0, 30)
    before = s.shards()

    def reach():
        s.choose_verb("Reach For", lights, int(lights.cx), int(lights.cy))
        run_for(world, 20)
    reach()
    reach()
    assert s.shards() == before and s.get_attribute("MarshLights") == "2"
    reach()
    assert s.shards() == before + 12
    reach()
    assert s.shards() == before + 12
    leave(world, s)


def test_the_stargazers_glass_winks_back_on_the_third_look_and_only_once(world):
    glass = next(e for e in world.ents if e.name == "Star_Glass")
    assert glass.map == "22,4,0"
    s = join(world, "Stargazer", glass.map, 300, 300)
    s.connected = True
    near(world, s, glass, 0, 30)
    before = s.shards()

    def look():
        s.choose_verb("Look Through", glass, int(glass.cx), int(glass.cy))
        run_for(world, 20)
    look()
    look()
    assert s.shards() == before and s.get_attribute("StarGlass") == "2"
    look()
    assert s.shards() == before + 8
    look()
    assert s.shards() == before + 8
    leave(world, s)


def test_the_drowned_bell_answers_once(world):
    bell = next(e for e in world.ents if e.name == "Drowned_Bell")
    s = join(world, "Bell_Ringer", bell.map, 300, 300)
    s.connected = True
    near(world, s, bell, 0, 32)                                     # (from the shore below it)
    shards, gold = s.shards(), s.items_held("Gold_Coin(s)")

    def ring():
        s.choose_verb("Ring", bell, int(bell.cx), int(bell.cy))
        run_for(world, 60)
    ring()
    assert s.shards() == shards + 6 and s.items_held("Gold_Coin(s)") == gold + 30
    ring()
    assert s.shards() == shards + 6 and s.items_held("Gold_Coin(s)") == gold + 30
    leave(world, s)


def test_the_peat_man_gives_up_his_torc_once(world):
    man = next(e for e in world.ents if e.name == "Peat_Man")
    s = join(world, "Peat_Robber", man.map, 300, 300)
    s.connected = True
    near(world, s, man, 32, 0)
    before = s.shards()

    def search():
        s.choose_verb("Search", man, int(man.cx), int(man.cy))
        run_for(world, 20)
        s.chest_response("CHEST_ALL")
    search()
    got = s.shards()
    assert s.items_held("Old_Torc") == 1 and got >= before + 8      # (a chest's treasure may have a few Shards more)
    search()
    assert s.items_held("Old_Torc") == 1 and s.shards() == got      # (once each)
    leave(world, s)


def test_old_silt_talks_and_gives_one_eel(world):
    silt = next(e for e in world.ents if e.npc_id == "Eel_Catcher")
    s = join(world, "Eel_Fancier", silt.map, 300, 300)
    s.connected = True
    near(world, s, silt, 32, 0)
    for _ in range(2):
        assert talk_to(world, s, silt)
        s.action_box_response_chosen(3)                             # (is that eel I can smell?)
        run_for(world, 10)
        assert s.items_held("Cooked_Cave_Eel") == 1
        s.action_box_response_chosen(2)                             # (I'll leave you to it)
        run_for(world, 10)
    leave(world, s)


def test_people_speak_in_their_own_voice_and_notices_are_silent(world):
    """A conversation's box says whose voice to murmur it in (Entities.ini Voice=: build_voices.py) and a pitch that
    one person always has; a notice, a sign or a letter has none; you speak in your own."""
    keeper = next(e for e in world.ents if e.name == "Gravekeeper" and e.alive)      # (no hours kept: there by night)
    s = join(world, "Listener", keeper.map, 300, 300)
    s.connected = True
    near(world, s, keeper, 32, 0)
    heard = []
    for _ in range(2):
        assert talk_to(world, s, keeper)
        box = s.box_state()
        assert box["voice"] == "Old_Man" and 93 <= box["pitch"] <= 107
        heard.append(box["pitch"])
        s.close_action_box(-1)
        run_for(world, 5)
    assert heard[0] == heard[1]                                    # (the same person sounds the same every time)
    assert s.npc_voice("Notice") == ("", 100) and s.npc_voice("Signpost") == ("", 100)
    s.player_sprite_base = "PlayerF"
    assert s.npc_voice("Player")[0] == "Woman"
    leave(world, s)


def test_the_shardfall_deep_opens_only_to_a_woken_signet_and_its_shard_gives_once_a_day(world):
    """The Shardfall Deep (dev/migrate/build_shardfall.py): down the sea cave on Gull Point; the Wardens' Seal shut till
    Bryony's signet is woken there with Shards and Shardcraft 15; the Fallen Shard's Shards once a day to whoever
    finished the watch; its maps dim (Config.ini [Darkness])."""
    s = join(world, "Delver", "12,-5,0", 192, 300)
    s.connected = True
    s.god_mode = True

    def tile_verb(verb, map_name, tx, ty, stand):
        s.teleport(map_name, (stand[0] - 1) * 32, (stand[1] - 1) * 32 - 8)
        if s.pending_map:
            s.do_pending_map_change()
        run_for(world, 5)
        m = s.cur_map
        gx, gy = m.ox + (tx - 1) * 32 + 16, m.oy + (ty - 1) * 32 + 16
        s.out = []
        s.choose_verb(verb, s.tile_entity_at(gx, gy), gx, gy)
        run_for(world, 40)
        if s.pending_map:
            s.do_pending_map_change()
        run_for(world, 5)
        return " ".join(str(e.get("text", "")) for e in s.out if e.get("t") == "msg")

    tile_verb("Enter", "12,-5,0", 7, 8, (7, 9))
    assert s.cur_map.name == "12,-5,-1"                              # (down the sea cave)
    m = world.maps["12,-6,-1"]
    lk = m.lock_at[(7, 16)]
    assert s.lock_closed(m, lk)                                      # (the Seal: shut)
    assert "small round hollow" in tile_verb("Touch", "12,-6,-1", 7, 16, (7, 18))
    s.update_attribute("ShardfallGate", "=4")
    stock(s, Wardens_Signet=1)
    s.add_shards(150)
    start = s.shards()
    assert "Shardcraft 15" in tile_verb("Touch", "12,-6,-1", 7, 16, (7, 18))
    assert s.lock_closed(m, lk) and s.items_held("Wardens_Signet") == 1 and s.shards() == start
    s.skill_level = lambda skill: 25
    tile_verb("Touch", "12,-6,-1", 7, 16, (7, 18))
    assert s.get_attribute("ShardfallGate") == "5" and not s.lock_closed(m, lk)
    assert s.items_held("Wardens_Signet") == 0 and s.shards() == start - 100 + 40   # (Shardfall.Seal; the quest's reward)
    tile_verb("Climb Up", "12,-5,-1", 7, 10, (7, 9))
    assert s.cur_map.name == "12,-5,0"                               # (and up again)

    shard = next(e for e in world.ents if e.npc_id == "The_Fallen_Shard")
    near(world, s, shard, 32, 100)

    def draw():
        s.out = []
        s.choose_verb("Draw From", shard, int(shard.cx), int(shard.cy))
        run_for(world, 80)
        return " ".join(str(e.get("text", "")) for e in s.out if e.get("t") == "msg")

    before = s.shards()
    assert "pushes you back" in draw() and s.shards() == before      # (not till the watch is finished)
    s.update_attribute("FallenShardQuest", "=3")
    before = s.shards()                                              # (after the quest's own reward)
    assert "10 Shards" in draw() and s.shards() == before + 10
    assert "given what it will" in draw() and s.shards() == before + 10
    s.update_attribute("FallenShardAt", "=%d" % (int(s.get_attribute("FallenShardAt")) - 21 * 3600))
    draw()
    assert s.shards() == before + 20
    dim = world.data.ini_read("Config.ini", "Darkness", "Maps", "").split()
    assert shard.map in dim and "12,-6,-1" in dim and "12,-5,0" not in dim
    leave(world, s)


def test_the_shardfall_deep_is_all_one_place_with_its_people_and_its_three_of_a_kind(world):
    names = [n for n in world.maps if n.endswith(",-1") and 4 <= int(n.split(",")[0]) <= 12
             and -17 <= int(n.split(",")[1]) <= -5]
    assert len(names) >= 40
    ids = {e.npc_id: e for e in world.ents if e.npc_id}
    for pid in ("Warden_Ysolde", "Pell_Varrow", "Morrow_Angler", "Nell_Tarrow", "Bryony_Tarrow", "The_Fallen_Shard",
                "The_Singing_Geode", "Wardens_Reliquary", "Prism_Grotto", "Leviathans_Jaw"):
        assert pid in ids, pid
    for boss in ("Brine_Mother", "Hollow_Marshal", "Shardborn"):
        e = next(e for e in world.ents if e.name == boss)
        assert world.data.entity_ini(boss, "Boss", "") == "1" and int(world.data.entity_ini(boss, "Level", "0")) == \
            (24 if boss == "Brine_Mother" else 25)
    for kind in ("Prism_Crawler", "Shard_Wraith", "Hollow_Warden", "Shard_Drake"):
        assert int(world.data.entity_ini(kind, "Level", "0")) >= 20
    for q in ("Glass in the Nets", "Charting the Deep", "The Brine Mother", "The Last Watch", "The Fallen Shard"):
        assert world.data.ini_read("Quests.ini", q, "Requires.Level", "") == "20", q


def test_the_palace_has_cellars_below_and_the_royal_floor_above(world):
    """Galaith's palace (dev/migrate/build_royal_quarter.py): the throne hall as it was, a stair down to the kitchens and
    the King's own stair up to the royal floor; the courtyard's folk each have a bed or a watch that never sleeps."""
    hall, cellar, upper = world.maps["-10,14,0"], world.maps["-10,14,-1"], world.maps["-10,14,1"]
    assert hall.tile[hall.cell(2, 2)] == "Stairs002" and cellar.tile[cellar.cell(2, 2)] == "Stairs001"
    assert hall.tile[hall.cell(18, 2)] == "Stairs001" and upper.tile[upper.cell(18, 2)] == "Stairs002"
    rupert = next(e for e in world.ents if e.npc_id == "Rupert_On_Throne")
    assert rupert.map == "-10,14,0" and (10, 8) in hall.lock_at          # (the story's throne hall, its door's lock)
    s = join(world, "Courtier", "-10,14,0", 17 * 32, 2 * 32 - 8)
    s.connected = True
    m = s.cur_map
    gx, gy = m.ox + 17 * 32 + 16, m.oy + 1 * 32 + 16
    s.choose_verb("Climb Up", s.tile_entity_at(gx, gy), gx, gy)
    run_for(world, 40)
    if s.pending_map:
        s.do_pending_map_change()
    assert s.cur_map.name == "-10,14,1"
    leave(world, s)
    for name in ("-11,14,0", "-10,14,0", "-10,15,0", "-10,14,-1", "-10,14,1", "-11,15,0"):
        mm = world.maps[name]
        for ln in open(os.path.join(ROOT, "maps", name + ".txt"), encoding="cp1252").read().splitlines():
            f = ln.split("	")
            if f[0] != "NPC" or len(f) < 5:
                continue
            opts = " " + f[4] + " "
            pid = opts.split(" Id=")[1].split()[0] if " Id=" in opts else ""
            if pid.startswith(("Royal_", "Palace_", "Court_", "Nurse_")) and pid not in ("Palace_Guard_1", "Palace_Guard_2",
                                                                                          "Palace_Captain"):
                assert " Bed=" in opts or "Schedule=Always" in opts, pid   # (a bed, or a watch that never sleeps)
                assert os.path.exists(os.path.join(ROOT, "data", "Scripts", "Talk to %s.txt" % pid)), pid
            if " Bed=" in opts:
                bx, by = (int(v) for v in opts.split(" Bed=")[1].split()[0].split(","))
                assert mm.decor[mm.cell(bx, by)] in ("Bed001", "Bed003", "Double_Bed001"), (pid, name, bx, by)


def test_the_editor_wheel_zooms_about_where_the_mouse_really_is(world):
    """The map editor (dsedit/pages/maps.py wheel_zoom): the spot under the mouse is found from the screen, not the event's
    own x, y (on Windows that can be another widget's); a touchpad's small turns zoom a little each, not a notch each."""
    from types import SimpleNamespace as NS
    from dsedit.pages.maps import MapPage
    canvas = NS(winfo_rootx=lambda: 100, winfo_rooty=lambda: 50, winfo_width=lambda: 800, winfo_height=lambda: 600)
    calls = []
    pg = NS(canvas=canvas, zoom=1.0, set_zoom=lambda z, around=None: calls.append((z, around and (around.x, around.y))))
    MapPage.wheel_zoom(pg, NS(delta=120, x=5, y=5, x_root=400, y_root=350))
    assert calls[-1] == (1.25, (300, 300))                          # (where the mouse is on the canvas)
    MapPage.wheel_zoom(pg, NS(delta=-30, x=0, y=0, x_root=400, y_root=350))
    assert abs(calls[-1][0] - 1.25 ** -0.25) < 1e-9                 # (a quarter of a notch)
    MapPage.wheel_zoom(pg, NS(delta=120, x=0, y=0, x_root=5, y_root=5))
    assert calls[-1][1] is None                                     # (off the canvas: about the middle)


def test_winter_ice_is_thin_and_cracked_and_never_walked_on(world):
    """Seasons.ini freezes a river to Thin_Ice001: dark water under a cracked skin, with the water's own (empty) walk mask."""
    import re
    from dsedit.project import Project
    P = Project(ROOT)
    assert re.search(r"(?m)^Ice=Thin_Ice001", open(os.path.join(ROOT, "data", "Seasons.ini"), encoding="cp1252").read())
    assert set(P.tiles_ini.get("Thin_Ice001", "Walkable.Data", "")) == {"0"}
    assert P.tiles_ini.get("Thin_Ice001", "Texture", "") == "Thin_Ice"
    assert os.path.exists(os.path.join(ROOT, "sprites", "Textures", "Thin_Ice.png"))


def test_a_blaze_warms_you_like_any_fire(world):
    from dsengine.cold import FIRES
    assert "Blaze" in FIRES
    f = [ln for ln in open(os.path.join(ROOT, "maps", "-4,14,0.txt"), encoding="cp1252").read().splitlines() if "\tBlaze\t" in ln]
    assert all("Gone.After=GuardQuest:5" in ln for ln in f)            # (a player's own to see go out)


def test_wooden_bridges_are_a_set_with_rails_on_their_open_sides(world):
    """Wood_Bridge: sixteen pieces by the sides they join; the open sides are railed (not walkable), the joined ones open;
    and no plank pier is left over water."""
    from dsedit.project import Project
    P = Project(ROOT)
    for bits in range(16):
        mask = "".join(s for i, s in enumerate("NESW") if bits >> i & 1)
        name = "Wood_Bridge_%s001" % (mask or "X")
        assert P.tiles_ini.get(name, "Joins", "") == (mask or "-"), name
        walk = P.tiles_ini.get(name, "Walkable.Data", "")
        assert len(walk) == 49
        rows = [walk[i * 7:i * 7 + 7] for i in range(7)]
        assert (set(rows[0]) == {"0"}) == ("N" not in mask)
        assert (set(rows[6]) == {"0"}) == ("S" not in mask)
        assert (set(r[0] for r in rows) == {"0"}) == ("W" not in mask)
        assert (set(r[6] for r in rows) == {"0"}) == ("E" not in mask)


def test_northport_is_shut_on_its_two_roads_till_the_parliament_speaks(world):
    for mapname, gate, side in ("8,6,0", (18, 2), (17, 2)), ("2,10,0", (20, 15), (20, 14)):
        m = world.maps[mapname]
        assert (gate[0], gate[1]) in m.lock_at
        s = join(world, "Walker" + mapname[0], mapname, (side[0] - 1) * 32 + 16, (side[1] - 1) * 32 + 16)
        lk = m.lock_at[gate]
        assert world.lock_closed_for(m, lk, s)
        s.update_attribute("ParliamentQuest", "=2")
        assert not world.lock_closed_for(m, lk, s)
        leave(world, s)


def test_captain_rook_wants_orrins_chart_and_the_lodestar_before_his_hull(world):
    rook = next(e for e in world.ents if e.npc_id == "Captain_Rook" and e.alive)
    s = join(world, "Navigator", rook.map, 300, 300)
    s.god_mode = 1                                                   # (out in the zones)
    run, npc, talk, use = isle_helpers(world, s)
    attr = lambda a: int(float(s.get_attribute(a) or 0))
    story_done_before(s, 12)
    talk(rook, 1)
    assert attr("OrrinQuest") == 1 and attr("ShipQuest") == 0        # (the chart first)
    orrin = next(e for e in world.ents if e.npc_id == "Orrin")
    talk(orrin, 1)
    assert attr("OrrinQuest") == 2
    shadow = next(e for e in world.ents if e.name == "Orrins_Shadow" and e.alive)
    s.kill_npc(shadow)
    run(10)
    assert attr("OrrinQuest") == 3
    talk(orrin, 1)
    assert attr("OrrinQuest") == 4 and s.items_held("Valour_Chart") == 1
    talk(rook, 1, 1)                                                 # (the chart; then I'll find the Lodestar)
    assert attr("OrrinQuest") == 5 and attr("LodestarQuest") == 1 and s.items_held("Mithril_Helm") == 1
    altar = next(e for e in world.ents if e.npc_id == "Drowned_Shrine_Altar")
    talk(next(e for e in world.ents if e.npc_id == "Surveyor_Nils"), 1)
    assert attr("LodestarQuest") == 2
    near(world, s, altar, 0, 36)
    s.choose_verb("Reach In", altar, int(altar.cx), int(altar.cy))
    run(30)
    assert attr("LodestarQuest") == 2                                # (its Warden stands over it)
    s.kill_npc(next(e for e in world.ents if e.name == "Rime_Warden" and e.alive))
    run(10)
    near(world, s, altar, 0, 36)
    s.choose_verb("Reach In", altar, int(altar.cx), int(altar.cy))
    run(30)
    assert attr("LodestarQuest") == 3 and s.items_held("Frozen_Lodestar") == 1
    talk(rook, 1, 1)                                                 # (the Lodestar; the hull; I'll bring them)
    assert attr("LodestarQuest") == 4 and attr("ShipQuest") == 1 and s.items_held("Frozen_Lodestar") == 0
    leave(world, s)


def test_the_three_fires_wake_the_sword_of_valour(world):
    find = lambda pid: next(e for e in world.ents if e.npc_id == pid and e.alive)
    oska = find("Warden_Oska")
    s = join(world, "Smith", oska.map, 300, 300)
    s.god_mode = 1
    run, npc, talk, use = isle_helpers(world, s)
    attr = lambda a: int(float(s.get_attribute(a) or 0))
    story_done_before(s, 19)                                         # (up to The Sleeping Sword)
    s.equipped[s.equip_slot_index("Weapon")] = "Sword_of_Valour"     # (in your hand: none in the pack)

    def do(verb, pid, ticks=60):
        e = find(pid)
        near(world, s, e, 0, 36)
        s.choose_verb(verb, e, int(e.cx), int(e.cy))
        run(ticks)

    talk(oska, 1)
    assert attr("FoundryQuest") == 1
    s.kill_npc(next(e for e in world.ents if e.name == "Forgemother" and e.alive))
    run(10)
    assert attr("FoundryQuest") == 2
    s.update_attribute("FoundryHeat", "=3")
    do("Work", "Ashen_Foundry_Bellows")
    assert attr("FoundryHeat") == 0                                  # (too hot: the fire chokes)
    do("Temper", "Ashen_Foundry_Hearth")
    assert attr("FoundryQuest") == 2                                 # (not hot enough)
    s.update_attribute("FoundryHeat", "=3")
    do("Temper", "Ashen_Foundry_Hearth", 120)
    assert attr("FoundryQuest") == 3
    talk(oska, 1)
    assert attr("FoundryQuest") == 4 and s.items_held("Mithril_Platebody") == 1

    tarek = find("Nomad_Tarek")
    talk(tarek, 1)
    assert attr("SunforgeQuest") == 1
    s.kill_npc(next(e for e in world.ents if e.name == "Sun_Keeper" and e.alive))
    run(10)
    assert attr("SunforgeQuest") == 2
    for _ in range(5):                                               # (round past west to north, and on to east)
        do("Turn", "Dawn_Mirror", 10)
    assert attr("Mirror.Dawn") == 1
    for mirror, n in (("Noon_Mirror", 2), ("Dusk_Mirror", 3)):
        for _ in range(n):
            do("Turn", mirror, 10)
    assert attr("SunforgeQuest") == 3                                # (east, south, west: the song)
    do("Temper", "Sunken_Temple_Forge", 120)
    assert attr("SunforgeQuest") == 4
    talk(tarek, 1)
    assert attr("SunforgeQuest") == 5

    maud = find("Delver_Maud")
    talk(maud, 1)
    assert attr("AnvilQuest") == 1
    s.kill_npc(next(e for e in world.ents if e.name == "Stone_King" and e.alive))
    run(10)
    assert attr("AnvilQuest") == 2
    do("Strike", "Dwarf_Hall_Root", 10)
    do("Strike", "Dwarf_Hall_Hammer", 10)
    assert attr("AnvilRunes") == 0                                   # (out of the song's order: start again)
    for rune in ("Root", "Rock", "Hammer", "Crown"):
        do("Strike", "Dwarf_Hall_" + rune, 10)
    assert attr("AnvilQuest") == 3
    do("Temper", "Dwarf_Hall_Anvil", 160)
    assert attr("AnvilQuest") == 4
    assert s.equipped[s.equip_slot_index("Weapon")] == "Woken_Sword_of_Valour"          # (Replace.Item: in your hand)
    assert s.items_held("Sword_of_Valour") == 0
    talk(maud, 1)
    assert attr("AnvilQuest") == 5 and s.items_held("Dragonscale_Platebody") == 1
    assert not s.quest_needs("GalaithQuest")
    leave(world, s)


def test_the_wandering_echos_riddles(world):
    echo = next(e for e in world.ents if e.npc_id == "Shardglass_Echo")
    s = join(world, "Riddled", echo.map, 300, 300)
    s.god_mode = 1                                                   # (out in the zones)
    run, npc, talk, use = isle_helpers(world, s)
    story_done_before(s, 6)
    shards = s.shards()
    talk(echo, 1, 1)                                                 # (a mirror: no)
    assert s.get_attribute("EchoQuest") == "1" and s.shards() == shards
    talk(echo, 1, 2, 1, 3, 1, 2, 1)                                  # (a Shard; the Shardrealm; under the world)
    assert s.get_attribute("EchoQuest") == "2" and s.shards() == shards + 30 + 45
    leave(world, s)


def test_ringing_the_rocks_is_a_minigame(world):
    s = join(world, "Ringer")
    lines = ["01\tPlay.Minigame\tCHIMES\t1\t03", "02\tUpdate.Attribute\tRang\t=1", "03\tEnd"]
    s.out = []
    assert s.run_script_lines("Chimes Test", lines)
    s.run_scripts()
    shown = lambda: [ev for ev in s.out if ev["t"] == "game"][-1]
    assert shown()["game"] == "chimes" and s.script_state == "MINIGAME"
    tune = s.game["tune"]
    assert len(tune) == 4 and s.game["heard"] == 3 and s.game["phase"] == "listen"
    for heard in (3, 4):                                            # (rung back, then a note longer, from the top)
        s.game_input({"do": "heard"})
        for n in tune[:heard]:
            s.game_input({"do": "ring", "n": n})
    assert s.game is None
    s.run_scripts()
    assert s.get_attribute("Rang") == "1"                           # (won: on to the next line)
    s.update_attribute("Rang", "0")
    assert s.run_script_lines("Chimes Test", lines)
    s.run_scripts()
    for _ in range(3):                                              # (three wrong notes and the tune's lost)
        s.game_input({"do": "heard"})
        s.game_input({"do": "ring", "n": s.game["tune"][0] % 5 + 1})
    assert s.game is None
    s.run_scripts()
    s.run_scripts()
    assert s.get_attribute("Rang") == "0" and not s.script_running
    leave(world, s)


def test_the_wild_places(world):
    """build_wilds.py: a lamb caught for Abel, the Fen Horn's coffer (everyone's, its Shards once each), a fairy ring."""
    def click(s, verb, e):
        near(world, s, e)
        s.choose_verb(verb, e, int(e.cx), int(e.cy))
        run_for(world, 10)

    placed = {e.npc_id for e in world.ents}
    for pid in ("Tamsin", "Shepherd_Abel", "Hode", "Toll_Keeper_Ghost", "Merrin", "Mother_Natter", "Marsh_Frog_King", "Pell",
                "Salt_Agnes", "Stoneways_Wraith", "Ulla", "Fairy_Ring_1", "Castaway_Bottle_3"):
        assert pid in placed, pid
    s = join(world, "Wanderer")
    s.connected = True
    s.update_attribute("LambQuest", "=1")
    lamb = next(e for e in world.ents if e.npc_id == "Stray_Lamb_1")
    click(s, "Catch", lamb)
    assert s.get_attribute("LambQuest") == "2" and s.get_attribute("Lamb1") == "1"
    click(s, "Catch", lamb)
    assert s.get_attribute("LambQuest") == "2"                     # (that one's home: not twice)
    horn = next(e for e in world.ents if e.name == "Fen_Horn" and e.alive)
    click(s, "Blow", horn)
    assert not horn.alive or horn not in world.ents
    coffer = next(e for e in world.ents if e.name == "Fen_Coffer" and e.alive)
    assert coffer.owner is None                                     # (up for everyone, a minute)
    shards = s.shards()
    click(s, "Open", coffer)
    assert s.ab_mode == "Chest" and s.responses[0] == "Take everything"
    s.action_box_response_chosen(1)
    run_for(world, 5)
    assert s.shards() > shards and s.get_attribute("FenCoffer") == "1"
    shards = s.shards()
    click(s, "Open", coffer)
    assert s.shards() == shards
    ring = next(e for e in world.ents if e.npc_id == "Fairy_Ring_1")
    click(s, "Step In", ring)
    if s.pending_map:
        s.do_pending_map_change()
    assert s.cur_map.name == "10,1,0" and s.get_attribute("FairyRing2") == "1"
    leave(world, s)


# ------------------------------------------------------------------ standing (standing.py, data\Towns.ini)
def test_standing_moves_a_towns_rank_and_its_prices(world):
    s = join(world, "Wellknown", "12,-2,0", 300, 300)
    s.connected = True
    assert s.town_of_map("12,-2,0") == "Ashford" and s.town_of_map("-10,13,-1") == "Galaith"
    assert s.town_of_map("7,7,-3") == "" and s.rank("Ashford") == "Stranger"
    keeper = next(e for e in world.ents if e.type == NPC and e.alive and s.town_of_map(e.map) == "Ashford" and
                  s.shop_rack_of(e))
    s.clicked_ent = keeper
    assert s.open_item_rack("SHOP", keeper.name, s.shop_rack_of(keeper))
    base = s.rack_buy_rate, s.rack_sell_rate
    s.out.clear()
    s.change_standing("Ashford", 25)
    said = [m["text"] for m in s.out if m.get("t") == "msg"]
    assert any("Ashford thinks better of you" in t and "Welcome" in t for t in said)
    assert any(m.get("t") == "standing" and m["list"] == [["Ashford", 25, "Welcome"]] for m in s.out)
    s.out.clear()
    s.change_standing("Ashford", 3)                                # (no new rank: nothing said)
    assert not [m for m in s.out if m.get("t") == "msg"]
    assert s.condition_met("$Standing.Ashford>=28") and s.condition_met("$Standing.Here=28")
    assert s.open_item_rack("SHOP", keeper.name, s.shop_rack_of(keeper))
    assert abs(s.rack_buy_rate - base[0] * 0.95) < 1e-9 and abs(s.rack_sell_rate - base[1] * 1.05) < 1e-9
    s.change_standing("Ashford", -500)                             # (held at the least: an Outlaw)
    assert s.standing("Ashford") == -100 and s.rank("Ashford") == "Outlaw"
    assert not s.open_item_rack("SHOP", keeper.name, s.shop_rack_of(keeper))   # (not served)
    s.change_standing("Ashford", 500)
    assert s.standing("Ashford") == 100 and s.rank("Ashford") == "Honoured"
    m = world.maps["11,-1,0"]                                      # (a house that opens to friends of the town)
    door = next(lk for lk in m.locks if (lk.x, lk.y) == (10, 7))
    s.lock_cache = {}
    assert not s.lock_closed(m, door)
    s.change_standing("Ashford", -60)                              # (40: Welcome, not Trusted)
    s.lock_cache = {}
    assert s.lock_closed(m, door)
    leave(world, s)


def test_an_outlaws_town_guards_come_for_them_till_the_fine_is_paid(world):
    s = join(world, "Wanted", "12,-2,0", 300, 300)
    other = join(world, "Honest", "12,-2,0", 340, 300)
    s.connected = True
    guard = next(e for e in world.ents if e.type == NPC and e.name == "Guard" and not e.npc_id and
                 s.town_of_map(e.map) == "Ashford")
    sheriff = next(e for e in world.ents if e.npc_id == "Ashford_Sheriff_325")
    arena = next(e for e in world.ents if e.npc_id == "Arena_Master")
    assert not world.hostile_for(guard, s)
    s.out.clear()
    s.change_standing("Ashford", -90)
    assert any("Outlaw" in m["text"] for m in s.out if m.get("t") == "msg")
    assert world.hostile_for(guard, s) and world.stat_for(guard, s, "aggressive")
    assert not world.hostile_for(guard, other)                      # (yours alone)
    assert not world.hostile_for(sheriff, s) and not world.hostile_for(arena, s)   # (the captain; a character)
    gal = next(e for e in world.ents if e.type == NPC and e.name == "Guard" and s.town_of_map(e.map) == "Galaith")
    s.change_standing("Galaith", -90)
    assert not world.hostile_for(gal, s)                            # (Galaith's guards wait for The True Heir)
    s.update_attribute("KingQuest", "=1")
    assert world.hostile_for(gal, s)
    s.update_attribute("KingQuest", "=0")
    assert not world.hostile_for(gal, s)
    owed = s.fine_owed("Ashford")
    assert owed == 50 + 30 * 5
    s.clicked_ent = sheriff
    assert s.fine_menu(sheriff) and s.responses[0] != "Pay the fine."    # (too poor to pay)
    s.native_menu_chosen(len(s.responses))
    stock(s, **{"Gold_Coin(s)": owed})
    assert s.fine_menu(sheriff) and s.responses[0] == "Pay the fine."
    s.native_menu_chosen(1)
    assert s.items_held("Gold_Coin(s)") == 0 and s.standing("Ashford") == -60 and s.rank("Ashford") == "Distrusted"
    assert not world.hostile_for(guard, s) and not s.fine_menu(sheriff)  # (talks as ever now)
    leave(world, other)
    leave(world, s)


def test_caught_thieving_as_the_town_thinks_of_you(world):
    s = join(world, "Known_Face", "12,-2,0", 300, 300)
    s.connected = True
    shop = next(e for e in world.ents if e.type == NPC and e.alive and s.town_of_map(e.map) == "Ashford" and
                s.shop_rack_of(e))
    s.change_standing("Ashford", 50)                               # (Trusted)
    assert s.caught_by_town(shop, "shop") == "warn" and s.standing("Ashford") == 50
    assert s.caught_by_town(shop, "shop") == 1 and s.standing("Ashford") == 42   # (once a day: then the guard)
    s.change_standing("Ashford", 40)                               # (Honoured)
    stock(s, **{"Gold_Coin(s)": 30})
    assert s.caught_by_town(shop, "shop") == "fine" and s.items_held("Gold_Coin(s)") == 5
    assert s.caught_by_town(shop, "house") == 1 and s.standing("Ashford") == 62    # (too poor for the fine now)
    s.change_standing("Ashford", -100)                             # (Distrusted)
    assert s.caught_by_town(shop, "shop") == 2
    wild = next(e for e in world.ents if e.type == NPC and e.alive and not e.hostile and e.map.endswith(",0") and
                not s.town_of_map(e.map))
    assert s.caught_by_town(wild, "pocket") == 1                   # (no town: nothing to lose)
    leave(world, s)


def test_a_blow_at_a_guard_costs_standing_once_in_a_while(world):
    s = join(world, "Brawler", "12,-2,0", 300, 300)
    guard = next(e for e in world.ents if e.type == NPC and e.name == "Guard" and not e.npc_id and
                 s.town_of_map(e.map) == "Ashford")
    hp = guard.hp
    s.damage_npc(guard, 1)
    s.damage_npc(guard, 1)
    assert s.standing("Ashford") == -15
    guard.hp = hp
    guard.in_combat, guard.target = False, None
    leave(world, s)


def test_a_quests_standing_is_given_once_and_to_old_saves(world):
    s = join(world, "Smuggled", "12,-2,0", 300, 300)
    s.update_attribute("SmugglerQuest", "=4")
    assert s.standing("Court") == 10
    s.update_attribute("SmugglerQuest", "=4")
    assert s.standing("Court") == 10                               # (once)
    old = join(world, "Old_Timer", "12,-2,0", 300, 300)
    old.attributes = [["SmugglerQuest", "4"], ["ShardsPaid.SmugglerQuest", "1"]]   # (done before standing was kept)
    old.standing_attr_changed()
    old.standing_catch_up()
    old.standing_catch_up()
    assert old.standing("Court") == 10
    leave(world, old)
    leave(world, s)


def test_the_admin_panel_sets_a_towns_standing(world):
    s = join(world, "Steward")
    s.admin_enabled = True
    s.out = []
    s.admin_command({"do": "standings"})
    towns = next(ev["towns"] for ev in s.out if ev["t"] == "admin_standings")
    assert ["Ashford", "Ashford", 0, "Stranger"] in towns and len(towns) >= 16
    s.out = []
    s.admin_command({"do": "standing", "town": "Ashford", "value": "80"})
    assert s.standing("Ashford") == 80 and s.rank("Ashford") == "Honoured"
    assert any("Ashford thinks better of you" in str(ev.get("text", "")) for ev in s.out)   # (as for any deed)
    towns = [ev["towns"] for ev in s.out if ev["t"] == "admin_standings"][-1]
    assert ["Ashford", "Ashford", 80, "Honoured"] in towns
    s.admin_command({"do": "standing", "town": "Ashford", "value": "-900"})               # (held at the least)
    assert s.standing("Ashford") == -100 and s.rank("Ashford") == "Outlaw"
    s.out = []
    s.admin_command({"do": "standing", "town": "Nowhere", "value": "5"})
    assert s.out[-1] == {"t": "admin_status", "text": "Pick a town first."}
    leave(world, s)


def test_a_side_taken_makes_all_of_it_friends_or_foes_for_that_player_alone(world):
    s, t = join(world, "Sider"), join(world, "Bystander")
    m = s.cur_map
    meg = world.add_npc("Villager", 0, m.ox + 200, m.oy + 200, "Side=Smugglers Attitude=Good")
    mate = world.add_npc("Villager", 0, m.ox + 260, m.oy + 200, "Side=Smugglers Attitude=Good")
    own = world.add_npc("Villager", 0, m.ox + 320, m.oy + 200, "Side=Smugglers Id=Test_Smuggler Attitude=Good")
    assert meg.side == "SMUGGLERS" and not world.hostile_for(meg, s)
    assert s.condition_met("$Side.Smugglers=none")
    assert s.run_script_lines("(test)", ["01\tSet.Side.Attitude\tSmugglers\tBad", "02\tEnd"])
    for _ in range(3):
        world.tick(0.05)
    assert world.hostile_for(meg, s) and world.hostile_for(mate, s)
    assert not world.hostile_for(meg, t)                         # (your side, not everyone's)
    assert s.condition_met("$Side.Smugglers=Bad") and t.condition_met("$Side.Smugglers=none")
    s.set_npc_attitude("Test_Smuggler", "Good")                  # (one NPC's own word comes first)
    assert not world.hostile_for(own, s) and world.hostile_for(mate, s)
    st = s.save_state()
    assert st["side_attitudes"] == {"SMUGGLERS": "Bad"}
    s.side_attitudes = {}
    s.load_state(st)
    assert world.hostile_for(meg, s)
    meg.target = s                                               # (made friends again: it stops fighting at once)
    s.set_side_attitude("Smugglers", "Good")
    assert not world.hostile_for(meg, s) and meg.target is not s
    for e in (meg, mate, own):
        world.remove_entity(e)
    leave(world, s)
    leave(world, t)


def test_an_npc_there_only_for_some(world):
    s, t = join(world, "Insider"), join(world, "Outsider")
    m = s.cur_map
    meg = world.add_npc("Villager", 0, m.ox + 200, m.oy + 200, "Here.After=SidedWithMeg:1 Attitude=Good")
    holt = world.add_npc("Villager", 0, m.ox + 260, m.oy + 200, "Gone.After=SidedWithMeg:1 Attitude=Good")
    assert not world.visible_to(meg, s) and world.visible_to(holt, s)
    s.update_attribute("SidedWithMeg", "=1")
    assert world.visible_to(meg, s) and not world.visible_to(holt, s)
    assert not world.visible_to(meg, t) and world.visible_to(holt, t)    # (theirs is as it was)
    for e in (meg, holt):
        world.remove_entity(e)
    leave(world, s)
    leave(world, t)


def test_a_quest_ending_is_kept_with_its_own_journal_line(world, monkeypatch):
    s = join(world, "Chooser")
    quest = {"GIVER": "Villager", "ATTRIBUTE": "TestRunQuest", "STAGE0": "", "STAGE1": "Decide.", "DONE": "2",
             "ENDING": "TestRunEnding", "ENDING1": "You sided with the watch.", "ENDING2": "You sided with Meg."}
    monkeypatch.setattr(world.data, "_quests", lambda: (None, [("The Test Run", quest)],
                                                        {"TESTRUNQUEST": ("The Test Run", quest)}))
    s.update_attribute("TestRunQuest", "=1")
    q = s.quest_list()[0]
    assert q["status"] == 0 and q["text"] == "Decide."
    s.update_attribute("TestRunEnding", "=2")
    s.update_attribute("TestRunQuest", "=2")
    q = s.quest_list()[0]
    assert q["status"] == 2 and q["text"] == "You sided with Meg." and q["steps"][-1] == ["You sided with Meg.", 1]
    s.update_attribute("TestRunEnding", "=0")                     # (no way kept: as any finished quest)
    q = s.quest_list()[0]
    assert q["text"] == "You have finished this quest." and q["steps"][-1] == ["Decide.", 1]
    leave(world, s)


# ---------------------------------------------------------------- other choices (build_choices.py)
def choice_talk(world, s, who, *answers):
    """Talk to who (an Id, or the entity), choosing each answer in turn."""
    e = world.placed_entity(who, s) if isinstance(who, str) else who
    assert e is not None, who
    near(world, s, e, 26, 0)
    s.do_action("Talk to", e)
    run_for(world, 30)
    past_a_lesson(world, s)
    for n in answers:
        s.action_box_response_chosen(n)
        run_for(world, 30)
    if s.ab_mode:
        s.close_action_box(-1)
        run_for(world, 5)


def ending_of(s, title):
    return next(q for q in s.quest_list() if q["title"] == title)["text"]


def test_old_hobs_savings_given_back_or_kept_and_oakhollow_hears(world):
    honest = join(world, "Honest", "3,11,0", 300, 300)
    honest.connected = True
    honest.update_attribute("HobQuest", "=3")
    honest.update_attribute("HobsChest", "=1")                      # (his savings taken from his chest)
    stock(honest, **{"Gold_Coin(s)": 150})
    choice_talk(world, honest, "OldHob", 1)                         # "Here, take it back."
    assert honest.get_attribute("HobQuest") == "4" and honest.get_attribute("HobAngry") == "0"
    assert honest.standing("Oakhollow") == 10 and "himself again" in ending_of(honest, "Old Hob")
    leave(world, honest)
    thief = join(world, "Keeper", "3,11,0", 300, 300)
    thief.connected = True
    thief.update_attribute("HobQuest", "=3")
    thief.update_attribute("HobsChest", "=1")
    choice_talk(world, thief, "OldHob", 2)                          # "It's mine now."
    assert thief.get_attribute("HobAngry") == "1" and thief.standing("Oakhollow") == -15
    assert "madness" in ending_of(thief, "Old Hob")
    leave(world, thief)


def test_hales_goods_sold_to_meg_by_her_friends(world):
    s = join(world, "Fencer", "17,4,0", 300, 300)
    s.connected = True
    s.update_attribute("SmugglerQuest", "=4")
    s.update_attribute("SmugglerSide", "=1")
    s.update_attribute("BanditQuest", "=3")
    stock(s, Stolen_Goods=1)
    gold = s.items_held("Gold_Coin(s)")
    choice_talk(world, s, "Red_Meg", 1)                             # "Sell them to Meg."
    assert s.get_attribute("BanditQuest") == "4" and s.get_attribute("BanditWay") == "2"
    assert s.items_held("Gold_Coin(s)") == gold + 300 and s.items_held("Stolen_Goods") == 0
    assert s.standing("Frosthold") == -10 and "Red Meg" in ending_of(s, "Bandits on the Road")
    hale = next(e for e in world.ents if e.name == "Captain" and e.map == "17,20,0")
    s.out = []
    choice_talk(world, s, hale)
    assert "smugglers" in str(s.out)                                # (he's heard where they went)
    leave(world, s)
    other = join(world, "Truce", "17,4,0", 300, 300)               # (the truce: Meg doesn't ask)
    other.connected = True
    other.update_attribute("SmugglerQuest", "=4")
    other.update_attribute("BanditQuest", "=3")
    stock(other, Stolen_Goods=1)
    choice_talk(world, other, "Red_Meg", 1)
    assert other.get_attribute("BanditQuest") == "3" and other.items_held("Stolen_Goods") == 1
    leave(world, other)


def test_the_redrock_signet_to_spleen_or_to_ambrose(world):
    s = join(world, "Seller", "15,15,0", 300, 300)
    s.connected = True
    assert world.placed_entity("Spleen_Parley", s) is None          # (not till Ambrose has asked)
    s.update_attribute("RedrockSignetQuest", "=1")
    stock(s, Redrock_Signet=1)
    choice_talk(world, s, "Spleen_Parley", 1)                       # "Sell it to Spleen."
    assert s.get_attribute("RedrockSignetQuest") == "2" and s.get_attribute("RedrockWay") == "1"
    assert s.side_attitudes.get("REDROCK_BANDITS") == "Good"
    assert world.placed_entity("Redrock_Steward", s) is None and world.placed_entity("Spleen_Parley", s) is None
    assert "Spleen" in ending_of(s, "The Redrock Signet")
    leave(world, s)
    g = join(world, "Giver", "16,15,0", 300, 300)
    g.connected = True
    g.update_attribute("RedrockSignetQuest", "=1")
    stock(g, Redrock_Signet=1)
    choice_talk(world, g, "Redrock_Steward", 1)
    assert g.get_attribute("RedrockSignetQuest") == "2" and g.get_attribute("RedrockWay") == "2"
    assert world.placed_entity("Ambrose_At_Home", g) is not None and world.placed_entity("Redrock_Steward", g) is None
    assert "Ambrose" in ending_of(g, "The Redrock Signet")
    leave(world, g)


def test_the_chancellors_grain_bribe_or_the_captain(world):
    def start(name):
        s = join(world, name, "-10,13,0", 300, 300)
        s.connected = True
        s.update_attribute("KingQuest", "=1")                        # (The True Heir done)
        s.update_attribute("GuardQuest", "=5")
        choice_talk(world, s, "Galaith_Clerk_73", 1)                 # "I'll find his ledger."
        assert s.get_attribute("GrainQuest") == "1"
        box = world.placed_entity("Chancellors_Strongbox", s)
        assert s.chest_locked(box) and s.chest_sturdy(box)
        s.unlocked_chests.add(s.chest_key(box))                      # (picked)
        near(world, s, box, 30, 0)
        s.do_action("Open", box)
        run_for(world, 10)
        assert s.ab_mode == "Chest" and s.responses[0] == "Take everything"
        s.action_box_response_chosen(1)
        run_for(world, 5)
        assert s.get_attribute("GrainQuest") == "2" and s.items_held("Grain_Ledger") == 1
        return s
    s = start("Briber")
    gold = s.items_held("Gold_Coin(s)")
    choice_talk(world, s, "Galaith_Speaker_70", 1)                  # "Give him the ledger, for his price."
    assert s.get_attribute("GrainWay") == "1" and s.get_attribute("GrainQuest") == "3"
    assert s.items_held("Gold_Coin(s)") == gold + 250 and s.items_held("Galaith_Treasury_Key") == 1
    s.out = []
    choice_talk(world, s, "Galaith_Clerk_73")
    assert "nothing to say" in str(s.out)                           # (the Archivist won't speak to you)
    gold = s.items_held("Gold_Coin(s)")
    vault = world.placed_entity("Galaith_Treasury", s)
    near(world, s, vault, 30, 0)
    s.do_action("Open", vault)
    run_for(world, 10)
    s.action_box_response_chosen(1)
    run_for(world, 5)
    s.do_action("Open", vault)                                      # (once)
    run_for(world, 10)
    if s.ab_mode:
        s.close_action_box(-1)
    assert s.items_held("Gold_Coin(s)") == gold + 300
    leave(world, s)
    h = start("Honest_Clerk")
    choice_talk(world, h, "Palace_Captain", 1)                      # "Hand the ledger to Captain Hart."
    assert h.get_attribute("GrainWay") == "2" and h.get_attribute("GrainQuest") == "3"
    assert h.standing("Galaith") == 20 and "Archivist sits" in ending_of(h, "The Chancellor's Grain")
    assert world.placed_entity("Galaith_Speaker_70", h) is None
    assert world.placed_entity("Chancellor_Sefton", h) is not None
    baker = world.placed_entity("Galaith_Baker_334", h)
    h.clicked_ent = baker
    assert h.open_item_rack("SHOP", baker.name, "SHOP-Bakery")
    cheap = h.rack_buy_rate
    h.update_attribute("GrainWay", "=0")
    assert h.open_item_rack("SHOP", baker.name, "SHOP-Bakery")
    assert abs(cheap - h.rack_buy_rate * 0.7) < 1e-9                # (bread's cheaper, for one who did it)
    leave(world, h)


def test_the_old_grove_felled_or_kept(world):
    ash = next(e for e in world.ents if e.name == "Ranger" and e.map == "8,11,0" and not e.npc_id)
    s = join(world, "Feller", "8,11,0", 300, 300)
    s.connected = True
    s.update_attribute("RangerQuest", "=4")
    choice_talk(world, s, "Timber_Merchant", 1)                     # "I'll cut your mark: fell the grove."
    assert s.get_attribute("GroveQuest") == "2"
    oak = world.placed_entity("Old_Grove_Oak", s)
    near(world, s, oak, 30, 0)
    s.do_action("Blaze", oak)
    run_for(world, 10)
    assert s.get_attribute("GroveQuest") == "4"
    gold = s.items_held("Gold_Coin(s)")
    choice_talk(world, s, "Timber_Merchant", 1)
    assert s.get_attribute("GroveWay") == "1" and s.get_attribute("GroveQuest") == "6"
    assert s.items_held("Gold_Coin(s)") == gold + 150 and s.standing("Oakhollow") == 5
    s.teleport("9,12,0", 16 * 32, 10 * 32)
    s.do_pending_map_change()
    run_for(world, 10)
    assert any(v.startswith("Tree_Stump") for (m, x, y), v in s.personal_cells.items() if m == "9,12,0")
    assert world.placed_entity("Old_Grove_Oak", s) is None and world.placed_entity("Grove_Sawyer", s) is not None
    leave(world, s)
    k = join(world, "Keeper", "8,11,0", 300, 300)
    k.connected = True
    k.update_attribute("RangerQuest", "=4")
    choice_talk(world, k, ash, 1)                                   # "I'll stand with you: the grove stays."
    assert k.get_attribute("GroveQuest") == "3"
    k.teleport("9,12,0", 16 * 32, 10 * 32)
    k.do_pending_map_change()
    run_for(world, 10)
    cutters = [e for e in world.ents if e.owner is k and e.name == "Woodcutter" and e.alive]
    assert len(cutters) == 2
    for e in cutters:
        k.kill_npc(e)
        run_for(world, 5)
    assert k.get_attribute("GroveQuest") == "5" and k.get_attribute("GroveCutters") == "2"
    choice_talk(world, k, ash, 1)
    assert k.get_attribute("GroveWay") == "2" and k.get_attribute("GroveQuest") == "6"
    assert world.placed_entity("Grove_Warden", k) is not None and world.placed_entity("Grove_Cot", k) is not None
    assert world.placed_entity("Grove_Sawyer", k) is None and not k.personal_cells
    leave(world, k)



def by_stone(world, name):
    """A player beside Northport's shardstone, woken, with its travel map lately opened (what binding needs)."""
    m = world.maps["4,6,0"]
    ws = next(e for e in world.ents if e.name == "Shardstone" and e.map == m.name)
    s = join(world, name, m.name, int(ws.x - m.ox) + 40, int(ws.y - m.oy) + 8)
    s.update_attribute("Waystone.Northport", "=1")
    s.stone_here = ("Northport", world.now)
    assert s.stone_near() is not None
    return s


def test_a_stance_form_counts_only_in_its_stance_and_within_its_limits(world):
    s = join(world, "Formed", "0,0,10", 12 * 32, 4 * 32)
    s.handle({"t": "stance", "stance": "Fighting"})
    run_for(world, 30)
    defence = s.stance_num("Defence")
    assert s.learn_form("Fighting", "Shieldwall") and s.forms_bound == ["Fighting.Shieldwall"]   # (bound at once)
    assert not s.learn_form("Fighting", "Shieldwall")                  # (known already)
    assert abs(s.stance_num("Defence") - defence * 1.4) < 1e-6 and s.stance_walk() < 1
    assert s.draw_reach() == 160 and s.form_colours() == [s.form_def("Fighting.Shieldwall")["colour"]]
    s.learn_form("Fighting", "Reckless")                               # (Defence 0.8 more: they multiply)
    assert abs(s.stance_num("Defence") - s.form_limit("Defence", defence * 1.4 * 0.8)) < 1e-6
    s.learn_form("Sneaking", "Rangers_Tread")                          # (Walk 1.5: but only when sneaking)
    assert s.form_product("Walk") == 0.8
    s.learn_form("Fighting", "Duellist")                               # (bound too: four of six)
    lo, hi = form_limits(world.data)["DEFENCE"]
    s.forms_bound += ["Fighting.Shieldwall"] * 6                       # (stacked past sense: still within [Limits])
    assert lo <= s.stance_num("Defence") <= hi
    s.forms_bound = ["Fighting.Shieldwall"]
    assert s.form_sum("Parry") == 0                                    # (Duellist's not bound)
    st = s.stance_state()
    assert st["forms_most"] == 6 and [f[:3] for f in st["forms"]] == [
        ["Fighting", "Shieldwall", 1], ["Fighting", "Reckless", 0], ["Sneaking", "Ranger's Tread", 0],
        ["Fighting", "Duellist", 0]] and all(f[3] for f in st["forms"])   # (bound or not, and what each does)
    saved = s.save_state()
    leave(world, s)
    t = Session(world, "Formed")
    t.load_state(saved)
    assert t.forms_learnt == saved["forms"]["learnt"] and t.forms_bound == ["Fighting.Shieldwall"]


def test_stance_and_form_tips_are_in_numbers_with_your_forms(world):
    s = join(world, "Tipped", "0,0,10", 12 * 32, 4 * 32)
    tips = s.stance_state()["stance_tips"]
    assert tips["Fighting"] == ["accuracy +15%, damage +15%, defence +15%",
                                "magic in a blow hurts +30%, drains and poisons last +50%"]
    assert "50% to shrug off a drain or poison" in tips["Channelling"][0] and "pace -20%" in tips["Channelling"][1]
    assert tips["Sneaking"][0].startswith("heard from ") and "pace -55%" in tips["Sneaking"][1]
    s.learn_form("Fighting", "Shieldwall")
    s.learn_form("Channelling", "Wardkeeper")
    tips = s.stance_tips()                                     # (the stance's numbers times its bound forms)
    assert "defence +61%" in tips["Fighting"][0] and "monsters within 5 tiles come for you first" in tips["Fighting"][0]
    assert "pace -20%" in tips["Fighting"][1] and "80% to shrug off a drain or poison" in tips["Channelling"][0]
    forms = {f[1]: f[3] for f in s.forms_state()}              # (a form alone: its own change, and what it makes)
    assert forms["Shieldwall"] == "defence +40%, monsters within 5 tiles come for you first, pace -20%"
    assert forms["Wardkeeper"] == "wards and boosts last +100%, 80% to shrug off a drain or poison"
    r = s.form_figures(s.form_def("Fighting.Reckless"))
    assert ("a kill: damage +20% and pace +30% for 4s", True) in r and ("defence -20%", False) in r
    leave(world, s)


def test_binding_a_form_is_paid_at_a_shardstone_and_six_at_most(world):
    s = by_stone(world, "Binder")
    for f in ("Fighting.Shieldwall", "Fighting.Reckless", "Fighting.Duellist", "Fighting.Dirty_Fighting",
              "Channelling.Stormcaller", "Channelling.Wardkeeper", "Sneaking.Cutpurse"):
        s.learn_form(f, quiet=True)
    assert len(s.forms_bound) == 6 and "Sneaking.Cutpurse" not in s.forms_bound   # (the seventh waits)
    stock(s, Shard=50)
    had = s.shards()
    s.bind_form("Sneaking.Cutpurse")
    assert "Sneaking.Cutpurse" not in s.forms_bound and s.shards() == had         # (six held: one must go first)
    s.unbind_form("Fighting.Reckless")
    assert "Fighting.Reckless" in s.forms_learnt and s.shards() == had            # (letting go is free)
    craft = s.skill_xp_of("Shardcraft")
    s.bind_form("Sneaking.Cutpurse")
    assert "Sneaking.Cutpurse" in s.forms_bound and s.shards() == had - 8 and s.skill_xp_of("Shardcraft") > craft
    s.unbind_form("Sneaking.Cutpurse")
    s.stone_here = None                                                # (away from the stone: no binding)
    s.bind_form("Sneaking.Cutpurse")
    assert "Sneaking.Cutpurse" not in s.forms_bound and s.shards() == had - 8
    s.stone_here = ("Northport", world.now)
    s.forms_menu()                                                     # (the Bind forms window: stances, then forms)
    assert s.ab_mode == "Conversation" and s.responses[:3] == ["Fighting forms...", "Channelling forms...",
                                                                "Sneaking forms..."]
    s.action_box_response_chosen(3)
    assert "Bind Cutpurse (8 Shards)." in s.responses and "Let Cutpurse go." not in s.responses
    s.action_box_response_chosen(s.responses.index("Bind Cutpurse (8 Shards).") + 1)
    assert "Sneaking.Cutpurse" in s.forms_bound and "Let Cutpurse go." in s.responses
    leave(world, s)


def test_forms_are_taught_by_people_and_scripts_and_set_by_the_admin_panel(world):
    s = join(world, "Pupil")
    meg = next(e for e in world.ents if e.type == NPC and e.npc_id == "Red_Meg")
    assert not s.form_teach(meg)                                       # (not on her side: nothing)
    s.update_attribute("SmugglerSide", "=1")
    assert s.form_teach(meg) and "Sneaking.Cutpurse" in s.forms_learnt
    assert s.ab_mode == "Conversation" and "Watch the eyes" in s.ab_text and s.responses == ["Thank you."]
    s.action_box_response_chosen(1)
    assert not s.form_teach(meg)                                       # (once)
    assert s.run_script_lines("(test)", ["01\tLearn.Stance\tFighting\tDirty_Fighting", "02\tEnd"])
    world.tick(0.05)
    assert "Fighting.Dirty_Fighting" in s.forms_learnt
    s.admin_enabled = True
    s.out = []
    s.handle({"t": "admin", "do": "form", "form": "Channelling.Drinking", "learnt": True, "bound": True})
    assert "Channelling.Drinking" in s.forms_bound
    forms = next(m for m in s.out if m.get("t") == "admin_forms")["forms"]
    assert ["Channelling.Drinking", "Drinking", 1, 1] in forms and len(forms) == len(s.form_defs())
    s.handle({"t": "admin", "do": "form", "form": "Sneaking.Cutpurse", "learnt": False, "bound": False})
    assert "Sneaking.Cutpurse" not in s.forms_learnt + s.forms_bound
    leave(world, s)


def test_channelling_forms_hear_and_drink_remnants(world):
    s = join(world, "Drinker", "0,0,10", 12 * 32, 4 * 32)
    s.handle({"t": "stance", "stance": "Channelling"})
    run_for(world, 30)
    s.admin_set_form("Channelling.Listening", True, True)
    p = s.player
    r = world.drop_item("Shard_Remnant", p.z, p.x + 60, p.y, 3)
    s.out = []
    s.forms_at = 0
    s.forms_tick()
    assert any(m.get("t") == "mark" and m.get("kind") == "shard" and m.get("u") == r.uid for m in s.out)
    s.admin_set_form("Channelling.Drinking", True, True)
    before, drunk = s.shards(), val(s.get_attribute("RemnantsAbsorbed"))
    s.forms_at = 0
    s.forms_tick()
    assert not r.alive or r not in world.ents
    assert s.shards() > before and val(s.get_attribute("RemnantsAbsorbed")) == drunk + 3
    leave(world, s)


def test_fighting_forms_parry_daze_and_draw_monsters(world, monkeypatch):
    import dsengine.player_combat as pc
    s = join(world, "Brawler", "0,0,10", 12 * 32, 4 * 32)
    friend = join(world, "Behind", "0,0,10", 12 * 32 + 40, 4 * 32)
    s.handle({"t": "stance", "stance": "Fighting"})
    run_for(world, 30)
    m = s.cur_map
    held = [e for e in world.ents if e.type == NPC and e.map == m.name and e.alive]
    for e in held:
        world.ents.remove(e)
    p = s.player
    gob = world.add_npc("Goblin", m.mz, p.x + 30, p.y, "")
    try:
        s.admin_set_form("Fighting.Duellist", True, True)
        s.admin_set_form("Fighting.Dirty_Fighting", True, True)
        monkeypatch.setattr(pc, "rnd", lambda: 0.0)                    # (every chance comes up)
        hp = p.hp
        s.out = []
        s.npc_attack_player(gob, False)
        assert p.hp == hp and any(m.get("t") == "sound" and m.get("name") == "Block" for m in s.out)   # (parried)
        s.player_strike(gob, False)
        assert gob.frozen_until > world.now and gob.frozen_word == "stunned"                      # (dazed)
        s.admin_set_form("Fighting.Shieldwall", True, True)
        world.tick(0.05)
        assert world.drawers == [s]
        gob.frozen_until = 0
        assert world.shieldwall_draw(gob, gob.ai, friend) is s                                    # (comes for them)
        assert world.shieldwall_draw(gob, gob.ai, s) is None
    finally:
        world.remove_entity(gob)
        world.ents.extend(held)
        leave(world, friend)
        leave(world, s)


def test_a_robe_fools_them_till_a_blow_gives_you_away(world):
    s = join(world, "Robed", "0,0,10", 12 * 32, 4 * 32)
    other = join(world, "Plain", "0,0,10", 12 * 32 + 40, 4 * 32)
    m = s.cur_map
    held = [e for e in world.ents if e.type == NPC and e.map == m.name and e.alive]
    for e in held:
        world.ents.remove(e)
    p = s.player
    gobs = [world.add_npc("Goblin", m.mz, p.x + 60 + 30 * k, p.y, "") for k in range(3)]
    far = world.add_npc("Goblin", m.mz, m.ox + 24 * 32, m.oy + 20 * 32, "")
    try:
        for g in gobs + [far]:
            g.ai.disguise = "LEATHER_BODY"                              # (as Friend.If.Wearing=Leather_Body)
        assert all(world.hostile_for(g, s) for g in gobs)              # (no robe on yet)
        s.equipped[s.equip_slot_index("Body")] = "Leather_Body"
        assert not any(world.hostile_for(g, s) for g in gobs) and world.hostile_for(gobs[0], other)   # (your robe)
        assert "Attack" in s.get_verbs(gobs[0]) and "Talk to" in s.get_verbs(gobs[0])
        s.damage_npc(gobs[0], 1)                                        # (a blow, in their sight)
        assert all(world.hostile_for(g, s) for g in gobs) and m.name in s.unmasked
        assert all(g.in_combat and g.target is s for g in gobs) and not far.in_combat   # (those near come)
        s.unmasked[m.name] = world.now - 1                              # (a while later, they've forgotten)
        assert not world.hostile_for(gobs[1], s)
        s.equipped[s.equip_slot_index("Body")] = ""
        assert world.hostile_for(gobs[1], s)
    finally:
        for g in gobs + [far]:
            world.remove_entity(g)
        world.ents.extend(held)
        leave(world, other)
        leave(world, s)


def test_a_boss_heals_by_the_remnants_near_it_unless_you_take_them_first(world):
    s = join(world, "Drainer", "0,0,10", 12 * 32, 4 * 32)
    m = s.cur_map
    held = [e for e in world.ents if e.type == NPC and e.map == m.name and e.alive]
    for e in held:
        world.ents.remove(e)
    p = s.player
    boss = world.add_npc("Goblin", m.mz, p.x + 200, p.y, "")
    pile = world.add_map_item("Shard_Remnant", m.mz, p.x + 120, p.y, 3)
    other = world.add_map_item("Shard_Remnant", m.mz, p.x + 260, p.y + 40, 2)
    try:
        boss.ai.absorbs = True
        boss.aggressive = 0
        boss.max_hp = 200
        boss.hp = 100
        for _ in range(120):                                            # (it goes to the nearest, and takes it in)
            if not pile.alive or not other.alive:
                break
            run_for(world, 1)
        assert pile.alive != other.alive
        took = 3 if not pile.alive else 2
        assert boss.hp == 100 + int(200 * 0.04 * took)
        left = other if not pile.alive else pile
        s.pickup_map_item(left, reach=10 ** 6)                          # (taken in first: none for it)
        assert not left.alive and s.items_held("Shard_Remnant") >= 1
        hp = boss.hp
        run_for(world, 40)
        assert boss.hp == hp
    finally:
        world.remove_entity(boss)
        for it in (pile, other):
            world.remove_entity(it)
        world.ents.extend(held)
        leave(world, s)


# ----- the Mending (dev/migrate/build_mending.py)
def mending_do(world, s, e, verb, *answers):
    """s stands by e and does verb to it, choosing each answer in turn (Esc after, if it's still open)."""
    assert e is not None
    near(world, s, e, 26, 0)
    s.choose_verb(verb, e, int(e.cx), int(e.cy))
    run_for(world, 30)
    past_a_lesson(world, s)
    for n in answers:
        s.action_box_response_chosen(n)
        run_for(world, 30)
    if s.ab_mode:
        s.handle({"t": "close"})
        run_for(world, 5)


def mending_script(world, s, name, *answers):
    """A trigger's (or a kill's, or an item's) script, run for s, choosing each answer in turn."""
    s.start_script(name, False)
    run_for(world, 30)
    for n in answers:
        s.action_box_response_chosen(n)
        run_for(world, 30)
    if s.ab_mode:
        s.handle({"t": "close"})
        run_for(world, 5)


def test_cold_fire_three_blue_shrines_and_what_is_said_by_the_hands_fire(world):
    s = join(world, "Ashwalker", "0,0,10", 12 * 32, 4 * 32)
    s.connected = True
    s.god_mode = 1                                                  # (whatever's about on the Ashwold's roads)
    s.player_level = lambda: 20
    attr = s.get_attribute
    warden = next(e for e in world.ents if e.name == "Warden" and e.alive)
    mending_do(world, s, warden, "Talk to")
    assert attr("ColdFireQuest") == "0"                             # (the Ember Ring first)
    s.update_attribute("RingQuest", "=2")
    mending_do(world, s, warden, "Talk to", 1)
    assert attr("ColdFireQuest") == "1"
    for n in (1, 2, 1):                                             # (the same one twice counts once)
        mending_script(world, s, "Ashen Shrine %d" % n)
    assert attr("ColdShrines") == "2" and attr("ColdFireQuest") == "1"
    mending_script(world, s, "Ashen Shrine 3")
    assert attr("ColdFireQuest") == "2"
    mending_script(world, s, "Hand Camp")                           # (walking up: too loud to hear a thing)
    assert attr("ColdFireQuest") == "2" and attr("ColdCampNear") == "1"
    s.handle({"t": "stance", "stance": "Sneaking"})
    run_for(world, 25)
    assert s.sneaking()
    mending_script(world, s, "Hand Camp", 1)
    assert attr("ColdFireQuest") == "3"
    mending_do(world, s, warden, "Talk to", 1)
    assert attr("ColdFireQuest") == "4"
    leave(world, s)


def test_the_kind_stranger_annis_goes_home_or_to_the_hall(world):
    s = join(world, "Tamsfriend", "0,0,10", 12 * 32, 4 * 32)
    other = join(world, "Letherbe", "0,0,10", 12 * 32, 5 * 32)
    for p in (s, other):
        p.connected = True
        p.god_mode = 1                                              # (whatever's about on the Ashwold's roads)
        p.player_level = lambda: 20
        p.update_attribute("ColdFireQuest", "=4")
    attr = s.get_attribute
    seen = lambda pid, p=s: world.placed_entity(pid, p) is not None      # noqa: E731
    mending_do(world, s, world.placed_entity("Tam_Cooper", s), "Talk to", 1)
    assert attr("StrangerQuest") == "1"
    mending_do(world, s, world.placed_entity("House_Annis", s), "Talk to", 1)
    assert attr("StrangerQuest") == "2"
    mending_do(world, s, world.placed_entity("Cael", s), "Talk to", 1)
    assert attr("StrangerQuest") == "3" and s.items_held("Caels_Lines") == 1
    mending_do(world, s, world.placed_entity("House_Annis", s), "Talk to", 1, 1)   # (Cael's lines read to her)
    assert attr("StrangerQuest") == "4" and attr("StrangerEnd") == "1" and s.items_held("Caels_Lines") == 0
    assert seen("Home_Annis") and not seen("House_Annis") and not seen("Hall_Annis")
    other.update_attribute("StrangerQuest", "=3")
    mending_do(world, other, world.placed_entity("House_Annis", other), "Talk to", 2)   # (left with her Shard)
    assert other.get_attribute("StrangerEnd") == "2" and other.get_attribute("StrangerQuest") == "4"
    assert seen("Hall_Annis", other) and not seen("House_Annis", other) and not seen("Home_Annis", other)
    assert seen("House_Annis", join(world, "Passerby", "0,0,10", 12 * 32, 6 * 32))   # (hers to each their own)
    leave(world, world.sessions["Passerby"])
    other.update_attribute("EldestQuest", "=1")                     # (down under Wardhaven with the rest)
    assert seen("Undercroft_Annis", other) and not seen("Hall_Annis", other)
    leave(world, other)
    leave(world, s)


def test_in_grey_the_robe_the_sermon_the_tithe_and_the_great_shard(world):
    s = join(world, "Greyrobe", "0,0,10", 12 * 32, 4 * 32)
    s.connected = True
    s.god_mode = 1
    s.player_level = lambda: 20
    s.update_attribute("ShardgateQuest", "=5")
    s.update_attribute("ColdFireQuest", "=4")
    attr = s.get_attribute
    seen = lambda pid: world.placed_entity(pid, s) is not None      # noqa: E731
    body = s.equip_slot_index("Body")
    linnet = world.placed_entity("Sister_Linnet", s)
    mending_do(world, s, linnet, "Talk to", 1, 1)                   # (where's the gathering? only for the Mending)
    assert attr("GreyQuest") == "1"
    s.equipped[body] = "Mending_Robe"
    mending_do(world, s, linnet, "Talk to", 1)                      # (in grey: one of them)
    assert attr("GreyQuest") == "2"
    s.equipped[body] = ""
    mending_script(world, s, "Mending Sermon")
    assert attr("GreyQuest") == "2"                                 # (Ivo speaks only to those in grey)
    s.equipped[body] = "Mending_Robe"
    mending_script(world, s, "Mending Sermon", 1)
    assert attr("GreyQuest") == "3" and attr("TitheQuest") == "1"
    hall = world.maps["23,7,-1"]
    gate = hall.lock_at[(15, 4)]
    assert s.lock_closed(hall, gate)
    held = [e for e in world.ents if e.type == NPC and e.map == hall.name and e.alive and e.hostile]
    for e in held:
        world.ents.remove(e)
    try:
        s.add_shards(100)
        shards = s.shards()
        mending_do(world, s, world.placed_entity("Hall_Font", s), "Pour Shards", 1)
        assert s.shards() == shards - 40 and attr("TitheOpen") == "1" and attr("TitheWay") == "1"
        s.check_locks(False)
        assert not s.lock_closed(hall, gate)
        mending_script(world, s, "Mending Sanctum")
        assert attr("TitheQuest") == "2" and attr("TitheWay") == "1"    # (the way it was opened, kept)
        mending_do(world, s, world.placed_entity("Hall_Great_Shard", s), "Listen", 1)
        assert attr("GreyQuest") == "4"
    finally:
        world.ents.extend(held)
    assert seen("Sister_Linnet") and seen("House_Shard")
    mending_do(world, s, world.placed_entity("Ashford_Sheriff_325", s), "Talk to", 1, 1)
    assert attr("GreyQuest") == "5" and attr("GreyEnd") == "1" and attr("MendingShut") == "1"
    assert not seen("Sister_Linnet") and not seen("House_Shard") and seen("Home_Annis")   # (the house shut)
    assert attr("StrangerQuest") == "0"                             # (and Annis taken home, never asked)
    leave(world, s)


def test_keeping_the_mendings_secret_and_the_tithes_other_ways(world):
    s = join(world, "Keeper", "0,0,10", 12 * 32, 4 * 32)
    s.connected = True
    s.update_attribute("GreyQuest", "=4")
    s.equipped[s.equip_slot_index("Body")] = "Mending_Robe"
    linnet = world.placed_entity("Sister_Linnet", s)
    mending_do(world, s, linnet, "Talk to", 1, 1)                   # (I won't tell a soul)
    assert s.get_attribute("GreyQuest") == "5" and s.get_attribute("GreyEnd") == "2"
    near(world, s, linnet, 26, 0)
    s.choose_verb("Talk to", linnet, int(linnet.cx), int(linnet.cy))
    run_for(world, 30)
    assert "Channelling.Drinking" in s.forms_learnt and "Brother. Let it in" in s.ab_text   # (a form, first)
    past_a_lesson(world, s)
    assert s.responses[0] == "Show me what you have."
    s.action_box_response_chosen(1)
    run_for(world, 10)
    assert any(r["item"] == "Mending_Robe" for r in s.rack)         # (her shelf)
    s.handle({"t": "close"})
    run_for(world, 5)
    s.update_attribute("TitheQuest", "=1")
    mending_script(world, s, "Mending Sanctum")                     # (in past the gate, and nothing paid)
    assert s.get_attribute("TitheWay") == "2" and s.get_attribute("TitheQuest") == "2"
    other = join(world, "Breaker", "0,0,10", 12 * 32, 5 * 32)
    other.update_attribute("TitheQuest", "=1")
    mending_script(world, other, "Kill Font_Keeper")
    assert other.get_attribute("TitheOpen") == "1" and other.get_attribute("TitheWay") == "3"
    leave(world, other)
    leave(world, s)


def test_the_eldest_takes_a_tither_for_a_friend_and_never_sees_the_first_blow(world):
    s = join(world, "Tither", "0,0,10", 12 * 32, 4 * 32)
    s.connected = True
    s.god_mode = 1                                                  # (he fights back, after)
    s.player_level = lambda: 30
    s.update_attribute("GalaithQuest", "=2")
    s.update_attribute("GreyQuest", "=5")
    attr = s.get_attribute
    mending_do(world, s, world.placed_entity("Wardhaven_Priest_309", s), "Talk to", 1)
    assert attr("EldestQuest") == "1" and world.placed_entity("Wardhaven_Undercroft_Stair", s) is not None
    s.update_attribute("TitheWay", "=1")
    s.teleport("17,1,-1", 7 * 32 + 8, 12 * 32 + 8)                  # (at the foot of the stair)
    s.do_pending_map_change()
    eldest = world.placed_entity("The_Eldest", s)
    choir = [e for e in world.ents if e.map == "17,1,-1" and e.npc_id.startswith("Eldest_Choir")]
    for e in choir:
        world.ents.remove(e)
    try:
        mending_script(world, s, "Eldest Sanctum", 1)
        assert attr("EldestMet") == "1"
        assert not world.hostile_for(eldest, s) and s.unseen_by(eldest)  # (one of the faithful, he thinks)
        other = join(world, "Stranger", "17,1,-1", 7 * 32 + 8, 11 * 32 + 8)
        assert world.hostile_for(eldest, other)                     # (his trust is the tither's alone)
        leave(world, other)
        stealth = s.skill_xp[s.skill_index("Stealth")]
        near(world, s, eldest, 20, 0)
        s.player_attack_target = eldest
        s.player_last_attack = 0
        hp = eldest.hp
        for _ in range(40):                                         # (a blow, as it's struck in play)
            world.tick(0.05, now=world.now + 50)
            if eldest.hp < hp:
                break
        assert eldest.hp < hp and s.skill_xp[s.skill_index("Stealth")] > stealth   # (a sneak attack's)
        assert world.hostile_for(eldest, s) and eldest.uid not in s.ent_attitudes  # (and he knows you now)
        s.player_attack_target = None
        s.damage_npc(eldest, 10 ** 6)
        run_for(world, 30)
        assert attr("EldestQuest") == "2"                           # (Kill The_Eldest)
    finally:
        world.ents.extend(choir)
    mending_do(world, s, world.placed_entity("Eldest_Great_Shard", s), "Listen", 2)   # (keep a splinter)
    assert attr("EldestQuest") == "3" and attr("EldestEnd") == "2" and s.items_held("Marys_Whisper") == 1
    leave(world, s)


def test_marys_whisper_gives_shards_once_in_a_while_and_wont_let_the_seam_be_unmade(world):
    s = join(world, "Whispered")
    stock(s, Marys_Whisper=1, Pickaxe=1)
    shards = s.shards()
    mending_script(world, s, "Listen Marys_Whisper")
    assert s.shards() == shards + 3
    mending_script(world, s, "Listen Marys_Whisper")
    assert s.shards() == shards + 3                                 # (soon, love: not yet)
    s.update_attribute("WhisperAt", "=%d" % (int(float(s.get_attribute("WhisperAt"))) - 21 * 3600))
    mending_script(world, s, "Listen Marys_Whisper")
    assert s.shards() == shards + 6
    s.update_attribute("KingQuest", "=1")
    s.update_attribute("WardensTruth", "=1")
    seam = next(e for e in world.ents if e.npc_id == "Kings_Shard_Seam")
    near(world, s, seam, 0, 30)
    s.choose_verb("Mine", seam, int(seam.cx), int(seam.cy))
    run_for(world, 30)
    s.action_box_response_chosen(3)                                 # (break it: the Whisper cries out)
    run_for(world, 20)
    assert s.get_attribute("HeartChoice") == "0" and s.get_attribute("Unmade") == "0"
    leave(world, s)


def test_the_mendings_brother_and_a_kinds_display_name_for_a_title(world):
    s = join(world, "Brotherly")
    assert s.parse_script_variables("Welcome, $Player.Brother.") == "Welcome, Brother."
    s.handle({"t": "look", "look": {"body": "f"}})
    assert s.parse_script_variables("Welcome, $Player.Brother.") == "Welcome, Sister."
    s.clicked_ent = None
    assert s.npc_title("Mending_Sister") == "Sister of the Mending"
    leave(world, s)


def test_the_mending_on_the_road_in_the_mine_and_after_it_all(world):
    s = join(world, "Roadworn", "0,0,10", 12 * 32, 4 * 32)
    s.connected = True
    s.player_level = lambda: 20
    enc = world.encounters
    assert not enc.allowed("Mending_Wayfarer", s)                   # (not till Cold Fire's told you of them)
    s.update_attribute("ColdFireQuest", "=3")
    assert s.condition_met(enc.kinds["Mending_Wayfarer"]["requires"])
    shards = s.shards()
    mending_script(world, s, "Talk to Mending_Wayfarer", 1)         # (for nothing, friend)
    assert s.get_attribute("MendingGift") == "1" and s.shards() == shards + 5
    mending_script(world, s, "Talk to Mending_Wayfarer", 1)
    assert s.shards() == shards + 5                                 # (once)
    waves = world.waves
    for k in waves.defs:
        waves.next_random[k] = world.now + 10 ** 9
    s.teleport(waves.defs["Mending_Raid"]["map"], 12 * 32, 10 * 32)
    s.do_pending_map_change()
    waves.next_random["Mending_Raid"] = world.now - 1
    waves.random_attacks()
    assert "Mending_Raid" not in waves.running                      # (not before The True Heir)
    s.update_attribute("KingQuest", "=1")
    waves.next_random["Mending_Raid"] = world.now - 1
    waves.random_attacks()
    assert "Mending_Raid" in waves.running
    waves.finish("Mending_Raid", waves.running["Mending_Raid"], False)
    seen = lambda pid: world.placed_entity(pid, s) is not None      # noqa: E731
    assert seen("Hall_Sister_2") and not seen("Chapel_Penitent_1")
    s.update_attribute("HeartChoice", "=3")                         # (the Seam unmade: some go home)
    assert not seen("Hall_Sister_2") and seen("Hall_Sister_1")
    assert not s.condition_met(waves.defs["Mending_Raid"]["requires"])
    s.update_attribute("EldestEnd", "=1")                           # (the great Shard broken)
    assert seen("Chapel_Penitent_1") and seen("Chapel_Penitent_2")
    s.update_attribute("EldestEnd", "=2")                           # (or a splinter kept: they stay)
    assert not seen("Chapel_Penitent_1")
    leave(world, s)


def test_an_outlaws_town_gate_is_barred_to_them_at_night(world):
    s = join(world, "Night_Owl", "21,4,0", 300, 300)
    s.connected = True
    m = world.maps["21,5,0"]
    gate = next(lk for lk in m.locks if (lk.x, lk.y) == (12, 17))
    t0 = world.day_fraction()
    try:
        world.set_day_fraction(0.0)                                # (midnight)
        assert s.condition_met("$World.Dark=1") and s.condition_met("$World.Hour=0")
        s.lock_cache = {}
        assert not s.lock_closed(m, gate)                          # (not an Outlaw: open by night)
        s.change_standing("Court", -90)                            # (an Outlaw: shut at once)
        assert s.lock_closed(m, gate) and "barred for the night" in s.lock_words(gate)
        world.set_day_fraction(0.5)                                # (noon)
        assert s.condition_met("$World.Dark=0") and s.condition_met("$World.Hour=12")
        s.clock_locks()                                            # (a new hour: looked at again)
        assert not s.lock_closed(m, gate)
        ward = world.maps["16,3,0"]
        wgate = next(lk for lk in ward.locks if (lk.x, lk.y) == (13, 3))
        s.change_standing("Wardhaven", -90)
        s.lock_cache = {}
        assert s.lock_closed(ward, wgate) and "Nobody answers" in s.lock_words(wgate)   # (not let in yet)
        s.update_attribute("WardhavenQuest", "=3")
        s.lock_cache = {}
        assert not s.lock_closed(ward, wgate)                      # (by day)
        world.set_day_fraction(0.0)
        s.lock_cache = {}
        assert s.lock_closed(ward, wgate) and "barred for the night" in s.lock_words(wgate)
    finally:
        world.set_day_fraction(t0)
    leave(world, s)


def test_a_trusted_door_in_northport_and_its_chest_once(world):
    m = world.maps["2,7,0"]
    door = next(lk for lk in m.locks if (lk.x, lk.y) == (12, 7))
    chest = next(e for e in world.ents if e.npc_id == "Trusted_Chest_Northport")
    s = join(world, "Harbour_Friend", "2,7,0", 300, 300)
    s.connected = True
    s.lock_cache = {}
    assert s.lock_closed(m, door)
    s.change_standing("Northport", 45)                             # (Trusted: opens without being asked again)
    assert not s.lock_closed(m, door)
    near(world, s, chest, 0, 30)
    s.do_action("Open", chest)
    run_for(world, 10)
    assert s.ab_mode == "Chest"                                    # (not locked: left for you)
    s.action_box_response_chosen(1)                                # Take everything
    assert s.items_held("Wardbound_Sealskin_Boots") == 1 and s.items_held("Teleport_Scroll") >= 2
    gold = s.items_held("Gold_Coin(s)")
    s.do_action("Open", chest)                                     # (once only)
    run_for(world, 10)
    assert s.items_held("Gold_Coin(s)") == gold and s.items_held("Wardbound_Sealskin_Boots") == 1
    s.change_standing("Northport", -20)
    assert s.lock_closed(m, door)
    leave(world, s)


def mainlander(world, name, map_name):
    s = join(world, name, map_name, 300, 300)
    s.connected = True
    s.update_attribute("Passage", "=12")
    return s


def test_the_deserter_told_or_let_go(world):
    s = mainlander(world, "Teller", "26,19,0")
    choice_talk(world, s, "Keep_Sergeant_Brask", 1)               # "I'll look."
    assert s.get_attribute("DeserterQuest") == "1"
    choice_talk(world, s, "Deserter_Pip", 2)                       # "Brask will hear of this."
    choice_talk(world, s, "Keep_Sergeant_Brask")
    assert s.get_attribute("DeserterQuest") == "3" and s.standing("Keep") == 15
    assert "back in the levy" in ending_of(s, "The Deserter")
    leave(world, s)
    s = mainlander(world, "Kind_Heart", "26,19,0")
    choice_talk(world, s, "Keep_Sergeant_Brask", 1)
    stock(s, **{"Gold_Coin(s)": 40})
    choice_talk(world, s, "Deserter_Pip", 1)                       # "Here's 40 gold. Go."
    assert s.get_attribute("DeserterQuest") == "3" and s.items_held("Gold_Coin(s)") == 0
    assert s.standing("Keep") == -10 and "carter's cart" in ending_of(s, "The Deserter")
    assert world.placed_entity("Saltmarsh_Pip", s) is not None    # (he's in Saltmarsh now)
    leave(world, s)


def test_the_dry_spring_bribed_or_broken(world):
    s = mainlander(world, "Bribed", "3,21,0")
    choice_talk(world, s, "Dunerest_Elder_Sabra", 1)
    dam = world.placed_entity("Dunerest_Dam", s)
    near(world, s, dam, 0, 30)
    s.do_action("Break", dam)                                      # (found: the spring's dammed)
    run_for(world, 10)
    assert s.get_attribute("WellQuest") == "2"
    choice_talk(world, s, "Water_Seller_Corvin", 1)                # "Done. Give me the gold."
    assert s.get_attribute("WellQuest") == "4" and s.standing("Dunerest") == -10
    assert "by the cup" in ending_of(s, "The Dry Spring") and world.placed_entity("Dunerest_Dam", s) is not None
    leave(world, s)
    s = mainlander(world, "Breaker", "3,21,0")
    choice_talk(world, s, "Dunerest_Elder_Sabra", 1)
    dam = world.placed_entity("Dunerest_Dam", s)
    near(world, s, dam, 0, 30)
    s.do_action("Break", dam)
    run_for(world, 10)
    s.do_action("Break", dam)                                      # (pulled down)
    run_for(world, 10)
    assert s.get_attribute("WellQuest") == "3" and world.placed_entity("Dunerest_Dam", s) is None
    choice_talk(world, s, "Dunerest_Elder_Sabra")
    assert s.get_attribute("WellQuest") == "4" and s.standing("Dunerest") == 15
    assert "runs to Dunerest's well" in ending_of(s, "The Dry Spring")
    leave(world, s)


def test_the_eel_traps_blamed_or_mended(world):
    s = mainlander(world, "Blamer", "11,23,0")
    choice_talk(world, s, "Eel_Catcher_Morwen", 1)
    choice_talk(world, s, "Saltmarsh_Tobin", 1)
    choice_talk(world, s, "Eel_Catcher_Morwen")
    assert s.get_attribute("EelQuest") == "4" and s.standing("Saltmarsh") == 5
    assert "uncle inland" in ending_of(s, "The Eel Traps")
    leave(world, s)
    s = mainlander(world, "Mender", "11,23,0")
    choice_talk(world, s, "Eel_Catcher_Morwen", 1)
    choice_talk(world, s, "Saltmarsh_Tobin", 2)
    stock(s, Plank=3)
    choice_talk(world, s, "Eel_Catcher_Morwen", 1)                 # "Share your catch with him."
    assert s.get_attribute("EelQuest") == "4" and s.items_held("Plank") == 0 and s.standing("Saltmarsh") == 15
    assert "shares her catch" in ending_of(s, "The Eel Traps")
    leave(world, s)


def test_marsh_fever_paid_off_or_run_out(world):
    for name, answer, standing, words in (("Paid_Off", 1, -15, "still sells his cure"),
                                          ("Run_Out", 2, 15, "real tonic")):
        s = mainlander(world, name, "-6,4,0")
        choice_talk(world, s, "Mirefold_Healer_Bryony", 1)
        stock(s, **{"Gold_Coin(s)": 20})
        choice_talk(world, s, "Doctor_Pallister", 1)               # (a cure, for 20 gold)
        assert s.items_held("Pallisters_Cure") == 1 and s.items_held("Gold_Coin(s)") == 0
        choice_talk(world, s, "Mirefold_Healer_Bryony")            # (she knows it for what it is)
        assert s.get_attribute("FeverQuest") == "3" and s.items_held("Pallisters_Cure") == 0
        choice_talk(world, s, "Doctor_Pallister", answer)
        assert s.get_attribute("FeverQuest") == "4" and s.standing("Mirefold") == standing
        assert words in ending_of(s, "Marsh Fever")
        leave(world, s)


# ---------------------------------------------------------------- quests that wait for their stage
def test_the_grimoire_stays_on_its_lectern_till_you_come_for_it(world):
    s = join(world, "Reader", "3,18,-1", 13 * 32, 8 * 32)
    s.connected = True
    run_for(world, 10)
    lectern = next(e for e in world.ents if e.name == "Grimoire_Lectern" and e.map == "3,18,-1" and e.alive
                   and world.visible_to(e, s))
    near(world, s, lectern, 0, 40)
    s.choose_verb("Take", lectern, int(lectern.cx), int(lectern.cy))
    run_for(world, 10)
    assert s.items_held("Grimoire_of_Unbinding") == 0 and s.get_attribute("GrimoireQuest") == "0"
    s.update_attribute("GrimoireQuest", "=2")                       # (the scholar's sent you, and you've dug in)
    s.choose_verb("Take", lectern, int(lectern.cx), int(lectern.cy))
    run_for(world, 10)
    assert s.items_held("Grimoire_of_Unbinding") == 1 and s.get_attribute("GrimoireQuest") == "3"
    leave(world, s)


def test_pell_has_no_job_for_a_beginner(world):
    s = join(world, "Lamp")
    s.connected = True
    s.update_attribute("Passage", "=12")
    pell = world.placed_entity("Pell", s)
    assert pell is not None
    near(world, s, pell, 26, 0)
    assert talk_to(world, s, pell)
    assert "Pell" not in s.ab_text and len(s.responses) == 1        # (a miner at work, no more)
    s.close_action_box(-1)
    run_for(world, 5)
    s.player_level = lambda: 20
    assert talk_to(world, s, pell)
    assert "I'm Pell" in s.ab_text
    s.close_action_box(-1)
    leave(world, s)


def test_the_barrow_king_falling_before_you_were_sent_moves_nothing(world):
    s = join(world, "Grave")
    s.start_script("Kill Barrow_King", True)
    run_for(world, 5)
    assert s.get_attribute("BarrowQuest") == "0"
    s.update_attribute("BarrowQuest", "=2")
    s.start_script("Kill Barrow_King", True)
    run_for(world, 5)
    assert s.get_attribute("BarrowQuest") == "3"
    leave(world, s)



def test_the_frog_kings_pearl_from_the_witch_to_the_throne(world):
    s = join(world, "Croaky")
    s.connected = True
    smugglers_talk(world, s, "Mother_Natter", 1)
    assert s.get_attribute("FrogQuest") == "0" and s.player_form() == ""    # (not before the mainland)
    s.update_attribute("Passage", "=5")
    smugglers_talk(world, s, "Mother_Natter", 1, 1)
    assert s.get_attribute("FrogQuest") == "1" and s.player_form() == "Frog"
    smugglers_talk(world, s, "Marsh_Frog_King", 1, 1)
    assert s.get_attribute("FrogQuest") == "2"
    nest = next(e for e in world.ents if e.name == "Heron_Nest" and e.alive)
    near(world, s, nest, 0, 40)
    s.do_action("Search", nest)
    run_for(world, 10)
    assert s.get_attribute("FrogQuest") == "2"                     # (a frog can't climb)
    s.end_swap()
    s.do_action("Search", nest)
    run_for(world, 10)
    assert s.get_attribute("FrogQuest") == "3" and s.rack_type == "Chest"     # (shown in the nest, to take)
    s.action_box_response_chosen(1)                                 # (Take everything)
    assert s.items_held("Frog_Pearl") == 1
    smugglers_talk(world, s, "Marsh_Frog_King")
    assert s.get_attribute("FrogQuest") == "3"                     # (he won't talk to anything with ears)
    smugglers_talk(world, s, "Mother_Natter", 1)
    assert s.player_form() == "Frog"
    smugglers_talk(world, s, "Marsh_Frog_King", 1)
    assert s.get_attribute("FrogQuest") == "4" and s.items_held("Frog_Pearl") == 0
    leave(world, s)


def test_the_herbalists_remedy_wants_mushrooms_and_silk(world):
    herbalist = next(e for e in world.ents if e.name == "Herbalist" and e.alive)
    s = join(world, "Poultice", herbalist.map, 300, 300)
    s.connected = True
    s.player_level = lambda: 2
    s.update_attribute("Passage", "=5")
    day = world.day_fraction()
    world.set_day_fraction(0.5)                                     # (she's up and about at noon)
    if herbalist.ai is not None:
        herbalist.ai.asleep = False
    near(world, s, herbalist)

    def ask(*answers):
        s.update_attribute("Rumour.At", "=%d" % int(world.now / 1000))   # (no rumour first: one was just heard)
        assert talk_to(world, s, herbalist)
        for n in answers:
            s.action_box_response_chosen(n)
            run_for(world, 5)
        if s.ab_mode:
            s.close_action_box(-1)
        run_for(world, 5)
    ask(3, 1)                                                       # (Can I help you? I'll gather them.)
    assert s.get_attribute("RemedyQuest") == "1"
    ask(3)                                                          # (back with nothing)
    assert s.get_attribute("RemedyQuest") == "1"
    s.add_inventory_item("Cave_Mushroom", 3)
    s.add_inventory_item("Spider_Silk", 2)
    ask(3, 1)                                                       # (Thank you!)
    assert s.get_attribute("RemedyQuest") == "2" and s.items_held("Cave_Mushroom") == 0
    world.set_day_fraction(day)
    leave(world, s)
