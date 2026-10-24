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
    m = world.maps["3,3,0"]
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
    s.attributes.append(["FerryQuest", "4"])
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
    assert len(boards) >= 5                                       # (Ashford's market and every waystone town)
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
    a.action_box_response_chosen(1)                               # Three Cups
    a.action_box_response_chosen(2)                               # 20 gold
    a.action_box_response_chosen(2)                               # the middle cup
    assert a.items_held("Gold_Coin(s)") == 200 - 20 + 50
    a.player.x, a.player.y = table.x, table.y + 30
    b.player.x, b.player.y = table.x + 10, table.y + 30
    a.do_action("Play", table)
    a.action_box_response_chosen(3)                               # a round at 50 gold
    b.do_action("Play", table)
    b.action_box_response_chosen(1)                               # join in
    assert world.tavern.rounds["Dice_Table_1"]["players"] == ["Gambler", "Punter"]
    world.tick(0.05, now=world.now + 21000)
    assert "Dice_Table_1" not in world.tavern.rounds
    assert a.items_held("Gold_Coin(s)") == 230 and b.items_held("Gold_Coin(s)") == 200   # (a tie: they share)
    leave(world, a)
    leave(world, b)


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
    a = join(world, "Mortal", "2,3,0", 384, 300)
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
    a = join(world, "Bleeder", "2,3,0", 384, 300)
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
    a.player_mana = 50
    scroll = next(e for e in a.inv if e.name == "Fire_Bolt_Scroll")
    a.do_action("Cast", scroll)
    assert a.item_in_use is scroll and a.items_held("Fire_Bolt_Scroll") == 2     # (held ready, not cast)
    assert any(e.get("t") == "use" and e.get("uid") == scroll.uid for e in a.out)
    a.script_cursor_x, a.script_cursor_y = wolf.cx, wolf.cy
    a.use_item_with(wolf)                                         # (then clicked on the wolf)
    assert a.items_held("Fire_Bolt_Scroll") == 1
    leave(world, a)


def test_the_way_down_is_through_the_chapel(world):
    def climb(s, verb, tx, ty):
        m = s.cur_map
        gx, gy = m.ox + (tx - 1) * 32 + 16, m.oy + (ty - 1) * 32 + 16
        e = s.tile_entity_at(gx, gy)
        assert verb in s.get_verbs(e)
        s.choose_verb(verb, e, gx, gy)                             # (as a click does: where, too)
        for _ in range(60):
            world.tick(0.05)
        return s.cur_map.name

    s = join(world, "Pilgrim", "3,1,0", 17 * 32, 8 * 32)
    s.connected = True
    verger = next(e for e in world.ents if e.npc_id == "Chapel_Verger")
    assert verger.display == "Brother Aldous" and s.display_name(verger) == "Brother Aldous"
    assert climb(s, "Climb Down", 18, 8) == "3,1,-1"               # the chapel's steps, down to the cellar
    s.out = []
    assert climb(s, "Climb Down", 14, 9) == "3,1,-1"               # the trapdoor: locked, without its key
    assert any(ev.get("t") == "sound" and ev.get("name") == "Denied" for ev in s.out)
    s.teleport("3,1,0", 15 * 32, 8 * 32)                           # ask Brother Aldous about it
    for _ in range(5):
        world.tick(0.05)
    s.do_action("Talk to", verger)
    for _ in range(40):
        world.tick(0.05)
    assert s.ab_mode == "Conversation" and s.ab_title == "Brother Aldous"
    assert "cellar" not in s.ab_text.lower()                       # (he doesn't bring it up himself)
    s.action_box_response_chosen(1)                                # "What's down in the cellar?"
    for _ in range(20):
        world.tick(0.05)
    assert "lost the key" in s.ab_text and s.items_held("Chapel_Cellar_Key") == 0
    s.close_action_box(-1)
    s.teleport("3,1,-1", 16 * 32, 11 * 32 - 8)                     # search the cellar's crates
    for _ in range(5):
        world.tick(0.05)
    for x in (19, 17):                                             # (the wrong crate, then the right one)
        climb(s, "Search", x, 12)
        for _ in range(3):
            world.tick(0.05, now=world.now + 1500)                 # (the rummaging takes a moment)
    assert s.items_held("Chapel_Cellar_Key") == 1
    cell = (s.cur_map.name, 14, 9)
    assert s.lock_cells.get(cell) == "Trapdoor002"                 # (it stands open for them now)
    s.teleport("3,1,-1", 13 * 32, 9 * 32 - 8)                      # (in the cellar, by the trapdoor)
    for _ in range(5):
        world.tick(0.05)
    assert climb(s, "Climb Down", 14, 9) == "3,1,-2"               # it opens: straight down to the caves
    assert climb(s, "Climb Up", 14, 9) == "3,1,-1"                 # and the ladder under it back up
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


def test_a_kills_loot_is_the_killers_for_ten_seconds(world):
    a, b = join(world, "Slayer"), join(world, "Passerby")
    goblin = next(e for e in world.ents if e.name == "Goblin")
    before = {e.uid for e in world.ents}
    a.add_npc_drops(goblin)                                        # (bones: always)
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
