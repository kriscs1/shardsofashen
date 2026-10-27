"""The shared world's rules: what one player does, the others see; what a quest changes is the player's own."""
import os
import random

import pytest

from dsengine import World, Session
from dsengine.entity import MAPITEM, NPC, AI_FLEE, AI_IDLE
from dragonsword.lb import distance

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture(scope="module")
def world():
    random.seed(1)
    return World(ROOT)


@pytest.fixture(autouse=True)
def same_luck(request):
    """Each test rolls the same dice every run (the world is shared: a sheep wandering through a gate shouldn't fail one)."""
    random.seed(request.node.name)


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


def stock(s, **items):
    for name, q in items.items():
        s.add_inventory_item(name, q, quiet=True)


def test_homestead_needs_the_crystal_and_starts_closed(world):
    a, b = join(world, "Homer"), join(world, "Guest")
    a.go_home()
    world.tick(0.05)
    assert not world.homes.is_home_map(a.cur_map.name)          # no Access Crystal: nowhere to go
    stock(a, Access_Crystal=1)
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
    stock(a, Access_Crystal=1)
    a.go_home()
    world.tick(0.05)
    m = a.cur_map
    assert not a.build(6, 6, "Plank001")                          # no planks
    stock(a, Plank=30, Nails=60)
    assert a.build(6, 6, "Plank001")
    assert a.items_held("Plank") == 29 and m.tile[m.cell(6, 6)] == "Plank001"
    assert not a.build(6, 6, "Stone_Wall001")                     # Construction too low
    assert not b.build(7, 6, "Plank001")                          # not their home
    assert not a.build(*world.homes.arrival, "Plank001")          # where the homestone puts you down
    a.update_skill("Construction", "=10")
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
    stock(a, Access_Crystal=1, Plank=10, Nails=40, Iron_Bar=4)
    a.update_skill("Construction", "=10")
    a.go_home()
    world.tick(0.05)
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
    stock(a, Access_Crystal=1, Plank=10, Nails=20, Wool=6)
    a.update_skill("Construction", "=10")
    a.go_home()
    world.tick(0.05)
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
    stock(a, Access_Crystal=1, Logs=5, Sapphire=3, Iron_Bar=3, **{"Gold_Coin(s)": 100})
    a.drop_inventory_item(a.inv_item(next(e.uid for e in a.inv if e.name == "Access_Crystal")), 1)
    assert a.items_held("Access_Crystal") == 1                      # can't be dropped
    slot = 1
    a.equipped[slot] = "Iron_Sword" if value("Iron_Sword") else a.equipped[slot]
    a.player_dies()
    assert a.items_held("Access_Crystal") == 1                      # nor lost when you die
    assert a.items_held("Gold_Coin(s)") == 0 and a.items_held("Logs") == 0
    kept = sorted([e.name for e in a.inv for _ in range(e.quantity) if e.name != "Access_Crystal"] +
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
    m = world.maps["13,4,0"]
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
    assert s.get_attribute("HomeQuest") == "2" and s.items_held("Access_Crystal") == 1
    assert s.items_held("Plank") == 0
    assert talk(1)[0] == "Sell me something." and s.ab_mode == "Shop"
    leave(world, s)


def test_each_home_keeps_its_own_land(world):
    a = join(world, "Landholder")
    stock(a, Access_Crystal=1)
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
    assert m.tile[m.cell(5, 5)] == "Grass001"                     # the existing home is as it was
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
    stock(seller, Bread=5, Access_Crystal=1)
    stock(buyer, **{"Gold_Coin(s)": 100})
    seller.do_action("Trade", ash)
    assert seller.ab_mode == "Market"
    bread = next(e for e in seller.inv if e.name == "Bread")
    crystal = next(e for e in seller.inv if e.name == "Access_Crystal")
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
    chance, finds = s.dig_finds(world.maps["11,4,0"])                 # (Ashford: the usual)
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
    s.game_input({"do": "set", "t": ((pin["band"] / 2 + 0.5 - pin["phase"]) % 1) * pin["period"]})   # (at the bottom)
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
        s.game_input({"do": "set", "t": ((pin["band"] / 2 + 0.5 - pin["phase"]) % 1) * pin["period"]})
    assert s.game is None
    s.run_scripts()
    s.run_scripts()
    assert s.get_attribute("Picked") == "0" and not s.script_running
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
    m = world.maps["2,2,0"]
    chest = next(e for e in world.ents if e.name == "Chest" and e.map == m.name)
    s = join(world, "Looter", m.name, int(chest.x - m.ox), int(chest.y - m.oy + 36))
    gold = s.items_held("Gold_Coin(s)")
    s.do_action("Open", chest)
    for _ in range(10):
        world.tick(0.05)
    assert s.ab_mode == "Chest"
    names = [it["name"] for it in s.box_state()["items"]]
    assert "Fire_Bolt_Scroll" in names and "Bronze_Sword" in names and "Gold_Coin(s)" in names
    assert s.items_held("Fire_Bolt_Scroll") == 0 and s.items_held("Gold_Coin(s)") == gold    # (not yours yet)
    i = names.index("Fire_Bolt_Scroll")
    assert s.get_verbs(s.rack_pseudo(i)) == "Take 1,Take all,Examine"
    s.do_action("Take 1", s.rack_pseudo(i))
    assert s.items_held("Fire_Bolt_Scroll") == 1
    s.close_action_box(-1)
    saved = s.save_state()
    assert any(it[0] == "Fire_Bolt_Scroll" and it[1] == 2 for v in saved["chests"].values() for it in v)
    s.do_action("Open", chest)                                     # (what's left is still there, for them)
    assert s.ab_mode == "Chest"
    s.action_box_response_chosen(1)                                # Take everything
    assert s.items_held("Fire_Bolt_Scroll") == 3 and s.items_held("Bronze_Sword") == 1
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
    a = join(world, "Mortal", "11,4,0", 384, 300)
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
    a = join(world, "Bleeder", "11,4,0", 384, 300)
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
    assert "Cast" in a.get_verbs(scroll) and "Learn" not in a.get_verbs(scroll)
    a.do_action("Cast", scroll)
    assert a.item_in_use is scroll                                # (held ready, not cast)
    assert any(e.get("t") == "use" and e.get("uid") == scroll.uid for e in a.out)
    shards = a.shards()
    a.script_cursor_x, a.script_cursor_y = wolf.cx, wolf.cy
    a.use_item_with(wolf)                                         # (then clicked on the wolf)
    assert a.items_held("Fire_Bolt_Scroll") == 1 and a.shards() == shards - 3     # (the scroll stays; 3 Shards go)
    leave(world, a)


def test_frost_nova_freezes_the_foes_round_you_but_not_a_boss(world):
    a = join(world, "Frosty", "11,4,0", 384, 300)
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
    stock(a, Frost_Nova_Scroll=1)
    a.out = []
    shards = a.shards()
    a.cast_scroll(next(e for e in a.inv if e.name == "Frost_Nova_Scroll"), None)
    assert a.items_held("Frost_Nova_Scroll") == 1 and a.shards() == shards - 15      # (known: the scroll stays)
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
            world.tick(0.05)
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
    stock(a, Access_Crystal=1, Plank=20, Nails=40)
    a.update_skill("Construction", "=10")
    a.go_home()
    world.tick(0.05)
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
    import dsengine.player_combat as PC
    import dsengine.remnants as RM
    monkeypatch.setattr(PC, "rnd", lambda: 0.0)                    # (every drop drops)
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
    stock(a, Access_Crystal=1, Plank=20, Nails=40, Wool=20, Logs=20, Herb=20)
    a.update_skill("Construction", "=30")
    a.go_home()
    world.tick(0.05)
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
        s.game_input({"do": "set", "t": ((pin["band"] / 2 - pin["phase"]) % 1) * pin["period"]})


def isle_helpers(world, s):
    """run, npc, talk and use for a test that plays through the Isle's quests (time jumps on as it runs)."""
    def run(ticks=30, ms=50):
        for _ in range(ticks):
            world.tick(0.05, now=world.now + ms)

    def npc(name, map_name, npc_id=""):
        return next(e for e in world.ents if e.name == name and e.map == map_name and e.alive and
                    (not npc_id or e.npc_id == npc_id) and world.visible_to(e, s))

    def talk(e, *answers):
        m = world.maps[e.map]
        s.teleport(e.map, int(e.x - m.ox), int(e.y - m.oy) + 30)
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
    """Dinner at the Bank, The Amulet of Succession and Passage to the Mainland, played through."""
    import dsengine.player_combat as pc
    import dsengine.scripting as sc
    monkeypatch.setattr(pc, "rnd", lambda: 0.0)                     # (spells don't fizzle in a test)
    monkeypatch.setattr(sc, "rnd", lambda: 0.0)                     # (and the cage's lock gives at the first try)
    day = world.day_fraction()
    world.set_day_fraction(0.5)                                     # (by day: Maren at her counter)
    s = join(world, "Heir", "2,1,0", 16 * 32, 8 * 32)
    s.connected = True
    attr = lambda name: int(float(s.get_attribute(name) or 0))
    run, npc, talk, use = isle_helpers(world, s)
    assert attr("LastWill") == 2                                    # (a saved character: past the funeral)
    assert "Bronze_Sword" not in s.equipped                         # (no sword to start with)
    # Dinner at the Bank
    maren = npc("Maren", "2,1,0", "Maren_At_Counter")
    talk(maren, 1)                                                  # dinner? logs for the range first: an axe
    assert attr("DinnerQuest") == 1 and s.items_held("Bronze_Axe") == 1
    stock(s, Logs=3)
    talk(maren, 1)
    assert attr("DinnerQuest") == 2 and s.items_held("Logs") == 0
    rng = next(e for e in world.ents if e.npc_id == "Marens_Range")
    up = world.maps["2,1,1"]
    s.teleport("2,1,1", int(rng.x - up.ox), int(rng.y - up.oy) + 30)
    run(5)
    stock(s, Egg=1)
    s.item_in_use = next(e for e in s.inv if e.name == "Egg")
    s.use_item_with(rng)                                            # fried on Maren's range, upstairs
    run(60)
    assert s.items_held("Fried_Egg") == 1 and attr("DinnerQuest") == 3
    talk(npc("Edwin", "2,1,0", "Edwin_At_Desk"), 1, 1)              # the egg to Edwin; Maren gives the key
    assert attr("DinnerQuest") == 4 and s.items_held("Chapel_Cellar_Key") == 1
    # The Amulet of Succession, and Bess's compass begun
    bess = npc("Milkmaid", "2,0,0")
    talk(bess, 3, 1, 1)                                             # the mainland? Father's compass first; and Frank
    assert attr("Passage") == 1 and attr("AmuletQuest") == 1
    frank = npc("Frank", "2,0,0", "Frank_At_Forge")
    talk(frank, 1)                                                  # his wood, his workbench
    assert attr("AmuletQuest") == 2 and s.items_held("Logs") >= 5
    s.open_item_rack("CRAFT", "Workbench", "CRAFT-Crafting")
    assert {r["item"] for r in s.rack if r["level"] <= 1} >= {"Wooden_Sword", "Wooden_Shield"}
    s.close_action_box(-1)
    stock(s, Wooden_Sword=1, Wooden_Shield=1)
    talk(frank, 1)
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
    s.do_action("Reach In", niche)                                  # too close for a hand: Aldous, and a scroll
    run(60)
    s.action_box_response_chosen(1)
    run(30)
    assert attr("AmuletQuest") == 5 and s.items_held("Grasp_Scroll") == 1
    s.cast_scroll(next(e for e in s.inv if e.name == "Grasp_Scroll"), niche)      # (read at it: learnt, and cast)
    run(30)
    s.action_box_response_chosen(1)
    run(30)
    assert s.items_held("Amulet_of_Succession") == 1 and s.items_held("Lair_Key") == 1 and attr("AmuletQuest") == 6
    assert not any(e.name == "Gravekeeper" and e.owner is s for e in world.ents)   # (he's gone back up)
    # Passage to the Mainland: the lair, Tobias, the house key, the floorboard, the compass
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
    assert s.items_held("Fathers_Compass") == 1 and attr("Passage") == 4
    talk(bess, 3, 1)                                                # the compass to Bess: she sails you over
    run(60, ms=200)
    assert attr("Passage") == 5 and s.cur_map.name == "4,4,0"
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


def test_the_bank_keeps_its_hours_upstairs_and_down(world):
    """Maren tends the counter by day; at night she's upstairs at home (her own Schedule=, on an upper floor too)."""
    s = join(world, "Lodger", "2,1,0", 16 * 32, 9 * 32)
    day = world.day_fraction()
    counter = next(e for e in world.ents if e.npc_id == "Maren_At_Counter")
    home = next(e for e in world.ents if e.npc_id == "Maren_At_Home")
    world.set_day_fraction(0.95)                                    # (night: she shuts the bank and goes up)
    for _ in range(900):
        world.tick(0.05, now=world.now + 50)
    assert counter.sched_away and not counter.active
    s.teleport("2,1,1", 19 * 32, 2 * 32)                            # (upstairs: there she is)
    for _ in range(20):
        world.tick(0.05, now=world.now + 50)
    assert home.active and not home.sched_away
    world.set_day_fraction(0.5)                                     # (morning: off downstairs, not in front of you)
    for _ in range(20):
        world.tick(0.05, now=world.now + 50)
    assert home.sched_away and not home.active
    s.teleport("2,1,0", 16 * 32, 9 * 32)
    for _ in range(20):
        world.tick(0.05, now=world.now + 50)
    assert counter.active and not counter.sched_away
    world.set_day_fraction(day)
    leave(world, s)


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
    for town in ("Southport", "Keep", "Court", "Fenwick", "Ravensgate"):
        assert count(town, "Barkeep") == 5, town                       # (five taverns)
        assert count(town, "Doctor") == 1, town                        # (a hospital)
    assert count("Southport", "Speaker") == 1 and count("Southport", "Constable") == 1     # (Parliament; police)
    for town in ("Highwatch", "Frosthold", "Oakhollow", "Thornwick", "Emberwatch"):
        assert count(town, "Sheriff") == 1 and count(town, "Doctor") == 1, town
    for town in ("Moorcross", "Dunerest", "Wildwood", "Saltmarsh"):
        assert count(town, "Barkeep") == 1, town                       # (a hamlet: its pub)


def test_a_tavern_has_a_room_for_the_night(world):
    bar = next(e for e in world.ents if (e.npc_id or "").startswith("Southport_Barkeep_"))
    m = world.maps[bar.map]
    s = join(world, "Lodger2", bar.map, int(bar.x - m.ox), int(bar.y - m.oy) + 40)
    s.connected = True
    stock(s, **{"Gold_Coin(s)": 10})
    s.do_action("Talk to", bar)
    for _ in range(10):
        world.tick(0.05)
    assert s.responses[1].startswith("A room for the night")
    s.action_box_response_chosen(2)
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
    talk("Smuggler_Sergeant", 1)
    assert attr() == 4 and s.items_held("Gold_Coin(s)") == gold + 60
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
    s.load_state(None)                                              # (a new character: saves\\TEMPLATE.ini)
    world.sessions["Newborn"] = s
    s.connected = True
    s.enter_world()
    for _ in range(10):
        world.tick(0.05, now=world.now + 50)
    assert s.cur_map.name == "3,1,0" and "Bronze_Sword" not in s.equipped
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
            world.tick(0.05)

    use("Climb Up", 14, 8)
    assert s.cur_map.name == "3,1,1"
    use("Ring", 16, 11)
    assert any(ev.get("t") == "sound" and ev.get("name") == "Bell" for ev in s.out)
    use("Climb Down", 14, 8)
    assert s.cur_map.name == "3,1,0"
    leave(world, s)


def test_the_ferry_runs_at_night(world):
    s = join(world, "NightOwl", "1,2,0", 20 * 32, 12 * 32)
    day = world.day_fraction()
    world.set_day_fraction(0.95)                                    # (deep in the night: townsfolk go home)
    for _ in range(100):
        world.tick(0.05, now=world.now + 100)
    wim = [e for e in world.ents if e.name == "Ferryman" and e.map == "1,2,0"]
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
    a.fidget_at = world.now                                          # (now and then: a stretch, or its back to you)
    world.tick(0.05)
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


def test_sitting_on_a_bench_till_you_move(world):
    a = join(world, "Sitter", "0,0,5", 5 * 32, 3 * 32)              # (the arena's benches, along its top wall)
    b = join(world, "Stander", "0,0,5", 7 * 32, 3 * 32)
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
    s = join(world, "Watcher", "0,0,5", 12 * 32, 4 * 32)             # (the arena: open sand, nothing else about)
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
    assert not sheep.alive and not any(e.type == MAPITEM and distance(e.cx, e.cy, sheep.cx, sheep.cy) < 48
                                       for e in world.ents)         # (eaten: nothing left behind)
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
    assert s.cur_map.name == "11,4,0" and not s.script_running
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
    s = join(world, "Guide", "4,4,0", 13 * 32, 9 * 32)              # (Southport's landing)
    s.connected = True
    s.update_attribute("Passage", "=5")                              # (over from the Isle: it can start)
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
    m = world.maps["11,4,0"]
    door = (m.ox + 13 * 32 + 16, m.oy + 18 * 32 + 16)                # (in front of Percy's door)
    bridges = [(bm.ox + (x - 1) * 32 + 16, bm.oy + (y - 1) * 32 + 16) for bm in world.maps.values()
               if bm.name.endswith(",0") and 4 <= int(bm.name.split(",")[1]) <= 6 and
               int(bm.name.split(",")[0]) in range(5, 11)
               for y in range(2, 21) for x in range(2, 25) if bm.tile[bm.cell(x, y)] == "Plank001" and
               not bm.roof[bm.cell(x, y)] and any(bm.tile_is_water(x + dx, y + dy)
                                                  for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))]   # (a bridge)
    bridge = min(bridges, key=lambda b: abs(b[0] - (s.player.cx + door[0]) / 2) + abs(b[1] - door[1]))
    legs = [bridge, door]                                            # (along the road: over the river's bridge)
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
    assert s.cur_map is m and distance(granny.cx, granny.cy, s.player.cx, s.player.cy) < 80   # (she kept up)
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
    s = join(world, "Guide", "11,4,0", 13 * 32, 19 * 32)
    s.load_state({"map": "11,4,0", "x": 13 * 32, "y": 19 * 32, "attributes": [["EscortQuest", "2"]]})
    s.enter_world()
    for _ in range(10):
        world.tick(0.05)
    granny = world.placed_entity("Granny_Wren", s)
    assert granny is not None and granny.map == "11,4,0" and distance(granny.cx, granny.cy, *door) < 64
    leave(world, s)


def test_a_guard_comes_to_help_against_a_goblin(world):
    s = join(world, "Helped", "0,0,5", 12 * 32, 12 * 32)             # (the arena's sand)
    m = s.cur_map
    s.god_mode = True
    guard = world.add_npc("Guard", m.mz, m.ox + 8 * 32, m.oy + 12 * 32, "Attitude=Good Zone=6,10,18,14")
    goblin = world.add_npc("Goblin", m.mz, m.ox + 14 * 32, m.oy + 12 * 32, "Attitude=Bad Zone=6,10,18,14")
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
    s = join(world, "Fighter", "11,4,0", 10 * 32, 12 * 32)
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
    ottilie = next(e for e in world.ents if e.name == "Painter")
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
    seal = next(e for e in world.ents if e.name == "Seal" and e.alive)
    m = world.maps[seal.map]
    s = join(world, "Beachcomber", seal.map, int(seal.x - m.ox), int(seal.y - m.oy))
    s.connected = True
    s.god_mode = True
    if not world.in_water(seal):                       # (the world's been going a while: it may be ashore already)
        wx, wy = next((x, y) for y in range(2, 20) for x in range(2, 24) if m.tile_is_water(x, y) and
                      m.tile_is_water(x + 1, y) and m.tile_is_water(x, y + 1))
        world.set_entity_position(seal, m.ox + (wx - 0.5) * 32 - seal.w / 2, m.oy + (wy - 0.5) * 32 - seal.h + 1)
        seal.ai.state = AI_IDLE
    assert world.in_water(seal)
    for _ in range(5):
        world.tick(0.05)
    world.animate_entity(seal, False)
    assert world.in_water(seal) and seal.image.startswith("Seal_Swim")          # (in the sea: just its head)
    sx, sy = (seal.cx - m.ox) / 32 + 0.5, (seal.cy - m.oy) / 32 + 0.5
    beach = min(((x, y) for y in range(2, 21) for x in range(2, 25)      # (the nearest sand by the water)
                 if not m.tile_is_water(x, y) and m.local_walkable((x - 0.5) * 32, (y - 0.5) * 32) and
                 any(m.tile_is_water(x + dx, y + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))),
                key=lambda t: (t[0] - sx) ** 2 + (t[1] - sy) ** 2)
    a = seal.ai
    a.goal_x, a.goal_y = m.ox + (beach[0] - 0.5) * 32, m.oy + (beach[1] - 0.5) * 32 - (seal.fy - seal.cy)
    world.npc_walk_started(seal, a, AI_ROAM)
    for _ in range(600):
        world.tick(0.05, now=world.now + 50)
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
    a = join(world, "FirstFinder", "0,0,0", 15 * 32, 11 * 32)        # (beside the stone circle's chest)
    b = join(world, "SecondFinder", "0,0,0", 15 * 32, 12 * 32)
    chest = next(e for e in world.ents if e.name == "Chest" and e.map == "0,0,0")
    for s in (a, b, a):
        s.connected = True
        s.out = []
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
    for will, passage, asked in ((1, 0, False), (2, 0, True), (2, 3, True), (2, 5, False)):
        s.update_attribute("LastWill", "=%d" % will)
        s.update_attribute("Passage", "=%d" % passage)
        s.choose_verb("Talk to", bess, int(bess.cx), int(bess.cy))
        for _ in range(20):
            world.tick(0.05)
        assert any(r.startswith("Will you take me to the mainland") for r in s.responses) == asked, passage
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


def test_a_racks_search_finds_across_its_pages(world):
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
    c = m.cell(8, 11)
    held = [e for e in world.ents if e.type == NPC and e.active and e.z == m.mz and
            distance(e.fx, e.fy, m.ox + 7.5 * 32, m.oy + 10.5 * 32) < 160]
    for e in held:
        world.ents.remove(e)                                         # (no sheep through the gate while we watch)
    for _ in range(30):
        world.tick(0.05, now=world.now + 100)
    assert m.decor[c] == "Wood_Gate003" and m.tile[c] != "Wood_Gate003"    # (in the decor, over its ground)
    s = join(world, "Drover", "2,0,0", 7 * 32, 10 * 32 - 8)          # (standing at the gate)
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
    stock(a, Access_Crystal=1, Plank=20, Nails=40, Wool=20)
    a.update_skill("Construction", "=10")
    a.go_home()
    world.tick(0.05)
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


def test_berts_spell_and_the_staff_break_the_barrier(world):
    s = join(world, "Breaker", "0,14,0", 9 * 32, 10 * 32 - 8)
    run, npc, talk, use = isle_helpers(world, s)
    run(5)
    lights = lambda: [e for e in world.ents if e.name == "Barrier_Light" and e.alive and world.visible_to(e, s)]
    assert len(lights()) == 3
    story_done_before(s, 15)
    stock(s, Staff_of_Estforlan=1)
    m = s.cur_map
    gx, gy = m.ox + 7 * 32 + 16, m.oy + 10 * 32 + 16                 # (the barrier at 8,11, from beside it)
    s.item_in_use = next(e for e in s.inv if e.name == "Staff_of_Estforlan")
    s.choose_verb("Use with", s.tile_entity_at(gx, gy), gx, gy)
    run(60)
    assert int(float(s.get_attribute("GalaithQuest") or 0)) == 0                 # (the staff alone: no words for it)
    s.update_attribute("BarrierSpell", "=1")
    s.item_in_use = next(e for e in s.inv if e.name == "Staff_of_Estforlan")
    s.choose_verb("Use with", s.tile_entity_at(gx, gy), gx, gy)
    run(80)
    assert int(float(s.get_attribute("GalaithQuest") or 0)) == 1 and not lights()
    leave(world, s)


def test_clearing_the_wardhaven_bridge_opens_its_gates(world):
    s = join(world, "Bridger", "11,4,0", 13 * 32, 10 * 32)
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
    s = join(world, "Scaler", "11,4,0", 13 * 32, 10 * 32)
    s.connected = True
    run, npc, talk, use = isle_helpers(world, s)
    wyrmsmith = next(e for e in world.ents if e.name == "Wyrmsmith")
    attr = lambda: int(float(s.get_attribute("DragonforgeQuest") or 0))
    talk(wyrmsmith)
    assert attr() == 0                                               # (the dragon lives: no quest yet)
    story_done_before(s, 16)                                         # (the dragon of Galaith slain)
    talk(wyrmsmith, 1)
    assert attr() == 1
    stock(s, Dragon_Scale=3)
    talk(wyrmsmith, 1)
    assert attr() == 2 and s.items_held("Dragonscale_Helm") == 1 and s.items_held("Dragon_Scale") == 0
    leave(world, s)


def test_the_royal_guard_and_the_king(world):
    s = join(world, "Heir", "-9,14,0", 13 * 32, 17 * 32)
    run, npc, talk, use = isle_helpers(world, s)
    attr = lambda a: int(float(s.get_attribute(a) or 0))
    palace = world.maps["-9,14,0"]
    door = palace.lock_at[(13, 13)]
    story_done_before(s, 16)
    find = lambda pid: next(e for e in world.ents if e.alive and e.npc_id == pid)
    captain, king = find("Palace_Captain"), find("Rupert_On_Throne")
    talk(captain, 1)
    assert attr("GuardQuest") == 1
    talk(find("Galaith_Speaker_70"), 1, 1)
    assert attr("GuardQuest") == 2
    talk(find("Galaith_Clerk_73"), 1)                                   # (no amulet, no word from her)
    assert attr("GuardQuest") == 2
    stock(s, Amulet_of_Succession=1)
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
    m = world.maps["-9,14,0"]
    gx, gy = m.ox + 12 * 32 + 16, m.oy + 6 * 32 + 16
    throne = s.tile_entity_at(gx, gy)
    assert throne.name == "Throne001" and s.get_verbs(throne).split(",")[0] == "Sit"
    s.teleport("-9,14,0", 12 * 32, 8 * 32 - 8)                       # (in front of it)
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
    a = join(world, "Learner", "11,4,0", 384, 300)
    a.skill_level = lambda skill: 10
    stock(a, Healing_Scroll=1)
    a.do_action("Learn", next(e for e in a.inv if e.name == "Healing_Scroll"))
    assert "Healing" in a.spells_known and a.items_held("Healing_Scroll") == 0
    a.player_dies()
    a.handle({"t": "respawn"})
    world.tick(0.05)
    assert "Healing" in a.spells_known
    a.spell_start_cooldown("Healing")
    saved = a.save_state()
    leave(world, a)
    b = Session(world, "Learner")
    b.load_state(saved)
    assert "Healing" in b.spells_known and b.spell_cooldown_left("Healing") > 0    # (logging off doesn't reset it)


def test_a_scroll_too_hard_to_learn_is_kept(world):
    a = join(world, "Novice2")
    stock(a, Blizzard_Scroll=1)
    a.out = []
    a.do_action("Learn", next(e for e in a.inv if e.name == "Blizzard_Scroll"))
    assert "Blizzard" not in a.spells_known and a.items_held("Blizzard_Scroll") == 1
    assert any(e.get("t") == "sound" and e.get("name") == "Denied" for e in a.out)
    assert any("Magic 13" in str(e.get("text", "")) or "level 13 Magic" in str(e.get("text", "")) for e in a.out)
    leave(world, a)


def test_casting_spends_shards_only_when_it_takes(world):
    a = join(world, "Spender", "11,4,0", 384, 300)
    a.skill_level = lambda skill: 10
    a.spells_known["Healing"] = 1
    a.player.hp = 5
    a.remove_inventory_item("Shard", a.shards())
    stock(a, Shard=5)                                              # (Healing takes 6)
    a.out = []
    a.cast_spell("Healing", None)
    assert a.shards() == 5 and a.player.hp == 5                    # (too few: nothing taken, nothing cast)
    assert any(e.get("t") == "sound" and e.get("name") == "Denied" for e in a.out)
    stock(a, Shard=10)
    a.spell_chance = lambda spell: 0                               # (it fizzles: no Shards spent)
    a.cast_spell("Healing", None)
    assert a.shards() == 15 and a.spell_cooldown_left("Healing") > 0
    a.cooldowns.clear()
    a.player_last_cast = 0
    a.spell_chance = lambda spell: 100
    a.cast_spell("Healing", None)
    assert a.shards() == 9 and a.player.hp > 5                     # (cast: 6 Shards, exactly once)
    a.player.hp = 5
    a.cast_spell("Healing", None)                                  # (again at once: its cooldown)
    a.cast_spell("Healing", None)
    assert a.shards() == 9 and a.player.hp == 5
    assert not a.spend_shards(100, "That") and a.shards() == 9     # (never below nothing)
    leave(world, a)


def test_the_hotbar_casts_a_known_spell_without_its_scroll(world):
    a = join(world, "Quick", "11,4,0", 384, 300)
    a.skill_level = lambda skill: 10
    a.spells_known["Healing"] = 1
    a.spell_chance = lambda spell: 100
    a.player.hp = 3
    a.hotbar[0] = "Healing_Scroll"
    assert a.items_held("Healing_Scroll") == 0
    shards = a.shards()
    a.hotbar_use(0)
    assert a.player.hp > 3 and a.shards() == shards - 6
    a.handle({"t": "hotbar_spell", "spell": "Fire_Bolt"})          # (not known: not put there)
    assert "Fire_Bolt_Scroll" not in a.hotbar
    leave(world, a)


def test_digging_turns_up_shards_now_and_then(world, monkeypatch):
    s = join(world, "Delver")
    import random as rnd
    assert s.dig_shard_odds(world.maps["11,4,0"]) == (5.0, "1-3")
    cave = next(m for m in world.maps.values() if m.mz < 0)
    assert s.dig_shard_odds(cave) == (15.0, "1-5")                 # (under the ground: likelier)
    assert s.dig_shard_odds(world.maps["2,19,0"])[0] == 15.0        # (the desert's old places)
    monkeypatch.setattr(rnd, "uniform", lambda a, b: b)            # (the unluckiest: nothing)
    before = s.shards()
    assert s.dig_shards(world.maps["11,4,0"]) == 0 and s.shards() == before
    monkeypatch.setattr(rnd, "uniform", lambda a, b: 3.0)          # (under 5 in 100: Shards; not a cache)
    assert s.dig_shards(world.maps["11,4,0"]) >= 1 and s.shards() > before
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
    assert next(q for q in s.quest_list() if q["title"] == "Dinner at the Bank")["shards"] == 5
    leave(world, s)


def test_waking_a_shardstone_costs_shards_once(world):
    m = world.maps["4,6,0"]
    ws = next(e for e in world.ents if e.name == "Shardstone" and e.map == m.name)
    a = join(world, "Wanderer", m.name, int(ws.x - m.ox) + 40, int(ws.y - m.oy) + 8)
    other = join(world, "Bystander", m.name, int(ws.x - m.ox) + 60, int(ws.y - m.oy) + 8)
    a.connected = other.connected = True
    theirs = other.shards()

    def touch(answer):
        a.out = []
        a.choose_verb("Travel", ws, int(ws.cx), int(ws.cy))
        ticks(world, 40)
        assert a.ab_mode == "Conversation"
        a.action_box_response_chosen(answer)
        ticks(world, 40)

    a.remove_inventory_item("Shard", a.shards())
    stock(a, Shard=3)
    touch(1)                                                       # ("Wake it": but 5 are needed)
    assert a.get_attribute("Waystone.Southport") in ("", "0") and a.shards() == 3
    assert any(e.get("t") == "sound" and e.get("name") == "Denied" for e in a.out)
    a.close_action_box(-1)
    ticks(world, 5)
    stock(a, Shard=7)
    touch(2)                                                       # ("Not now": nothing spent)
    assert a.get_attribute("Waystone.Southport") in ("", "0") and a.shards() == 10
    touch(1)
    assert a.get_attribute("Waystone.Southport") == "1" and a.shards() == 5
    a.close_action_box(-1)
    ticks(world, 5)
    touch(len(a.responses))                                        # (awake: straight to its menu, "Stay here")
    assert a.shards() == 5 and other.shards() == theirs            # (charged once, and only them)
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
    old.load_state({"map": "11,4,0", "x": 384, "y": 300, "inventory": [["Shard", 9, 0]],
                    "bank": [["Shard", 4, []]], "attributes": [["ShardsGiven", "1"]]})
    assert old.shards() == 13 and not any(e.name == "Shard" for e in old.inv)
    assert "Shard" not in old.bank_item


def test_a_beast_leaves_shard_remnants_not_shards(world, monkeypatch):
    import dsengine.remnants as RM
    a = join(world, "Hunter", "11,4,0", 384, 300)
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
    a = join(world, "Riser", "11,4,0", 384, 300)
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
    a = join(world, "Watcher", "11,4,0", 384, 300)
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
    a = join(world, "Counter", "11,4,0", 384, 300)
    assert a.shard_setting("Shardstone.Galaith") == 20 and a.shard_setting("Shardstone.Highwatch") == 5
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
    a = join(world, "Ranker", "11,4,0", 384, 300)
    a.skill_level = lambda skill: 20
    a.spell_chance = lambda spell: 100
    stock(a, Fire_Bolt_Scroll_II=1)
    two = next(e for e in a.inv if e.name == "Fire_Bolt_Scroll_II")
    a.out = []
    a.do_action("Learn", two)                                      # (rank 2 before rank 1: no)
    assert a.spell_rank("Fire_Bolt") == 0 and a.items_held("Fire_Bolt_Scroll_II") == 1
    a.spells_known["Fire_Bolt"] = 1
    assert a.spell_cost("Fire_Bolt") == 3 and a.spell_ini("Fire_Bolt", "Damage", "") == "2-5"
    assert "Learn" in a.get_verbs(two)
    a.do_action("Learn", two)
    assert a.spell_rank("Fire_Bolt") == 2 and a.items_held("Fire_Bolt_Scroll_II") == 0
    assert a.spell_cost("Fire_Bolt") == 4 and a.spell_ini("Fire_Bolt", "Damage", "") == "4-9"
    assert a.spell_ini("Fire_Bolt", "Range", "") == "256"          # (what a rank doesn't change, stays)
    saved = a.save_state()
    assert saved["spells"]["Fire_Bolt"] == 2
    book = {r["spell"]: r for r in a.spellbook()}
    assert book["Fire_Bolt"]["title"] == "Fire Bolt II" and book["Fire_Bolt"]["next"]["title"] == "Fire Bolt III"
    leave(world, a)


def test_dismantling_breaks_gear_into_shards_after_asking(world):
    a = join(world, "Breaker", "11,4,0", 384, 300)
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
    a.update_attribute("Waystone.Southport", "=1")
    a.update_attribute("Waystone.Ashford", "=1")
    a.remove_inventory_item("Shard", a.shards())
    stock(a, Shard=10)
    a.choose_verb("Travel", ws, int(ws.cx), int(ws.cy))
    ticks(world, 40)
    assert a.ab_mode == "Conversation" and any("Ashford" in r for r in a.responses)
    a.action_box_response_chosen(next(i for i, r in enumerate(a.responses, 1) if "Ashford" in r))
    ticks(world, 40)
    assert a.shards() == 8 and a.cur_map.name == "11,4,0"          # (2 Shards, and there)
    leave(world, a)

def test_the_kings_shard_seam_gives_shards_once_a_day(world):
    seam = next(e for e in world.ents if e.name == "Shard_Seam" and e.map == "-11,14,-1")
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
