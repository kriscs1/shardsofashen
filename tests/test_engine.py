"""The shared world's rules: what one player does, the others see; what a quest changes is the player's own."""
import os

import pytest

from dsengine import World, Session
from dsengine.entity import MAPITEM, NPC

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture(scope="module")
def world():
    return World(ROOT)


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
    # Maps/1,1,0.txt: Lock 20,7  $Attr.Door1Open>=1 or $Item.Beggars_House_Key>=1
    a, b = join(world, "Ann"), join(world, "Ben")
    m = world.maps["1,1,0"]
    lk = m.lock_at[(20, 7)]
    assert a.lock_closed(m, lk) and b.lock_closed(m, lk)
    a.update_attribute("Door1Open", "=1")
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
    from dragonsword import ini
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
        s.teleport("0,0,5", x, 530)                               # (the paving by the gate)
        s.do_pending_map_change()
    world.tick(0.05)
    assert a.in_arena() and not a.on_arena_ground()
    assert "Attack" not in a.get_verbs(b.player)
    for s, x in ((a, 384), (b, 416)):
        s.teleport("0,0,5", x, 300)                               # (the middle of the sand)
        s.do_pending_map_change()
    world.tick(0.05)
    assert a.on_arena_ground() and b.on_arena_ground()
    assert "Attack" in a.get_verbs(b.player)
    leave(world, a)
    leave(world, b)


def test_pvp_fight_to_the_end_costs_nothing(world):
    a, b = join(world, "Pip"), join(world, "Quin")
    for s, x in ((a, 384), (b, 410)):
        s.teleport("0,0,5", x, 300)
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
    assert b.screen_name == "0,0,5" and not b.on_arena_ground()   # (by the gate, on the paving)
    assert a.player_attack_target is None
    leave(world, a)
    leave(world, b)
