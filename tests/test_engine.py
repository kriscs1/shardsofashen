"""The shared world's rules: what one player does, the others see; what a quest changes is the player's own."""
import os

import pytest

from dsengine import World, Session
from dsengine.entity import MAPITEM, NPC, AI_FLEE
from dragonsword.lb import distance

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
    s.attributes.append(["Passage", "12"])                          # (the first quest done)
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
    assert spade.wear == 1                                        # (the spade wears with each dig)
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
    assert climb(s, "Climb Down", 14, 9) == ("3,1,-2", False)      # the key: down you go (the trapdoor stays shut)
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


def test_passage_to_the_mainland_from_start_to_finish(world, monkeypatch):
    import dsengine.player_combat as pc
    monkeypatch.setattr(pc, "rnd", lambda: 0.0)                     # (spells don't fizzle in a test)
    s = join(world, "Newcomer", "1,2,0", 20 * 32, 12 * 32)
    s.connected = True
    attr = lambda: int(float(s.get_attribute("Passage") or 0))

    def run(ticks=30, ms=0):
        for _ in range(ticks):
            world.tick(0.05, now=world.now + ms if ms else None)

    def npc(name, map_name, npc_id=""):
        return next(e for e in world.ents if e.name == name and e.map == map_name and e.alive and
                    (not npc_id or e.npc_id == npc_id) and world.visible_to(e, s))

    def talk(e, *answers):
        m = world.maps[e.map]
        s.teleport(e.map, int(e.x - m.ox) + 26, int(e.y - m.oy))
        run(5)
        s.do_action("Talk to", e)
        run(30)
        for n in answers:
            assert s.ab_mode == "Conversation", (e.name, n, attr())
            assert e.display in ("", s.ab_title) or s.ab_title == s.display_name(e), (s.ab_title, e.name)
            s.action_box_response_chosen(n)
            run(30)
        if s.ab_mode:
            s.close_action_box(-1)
            run(5)

    def at(map_name, tx, ty, verb):
        s.teleport(map_name, (tx - 1) * 32, ty * 32)
        run(5)
        m = s.cur_map
        gx, gy = m.ox + (tx - 1) * 32 + 16, m.oy + (ty - 2) * 32 + 16
        e = s.tile_entity_at(gx, gy)
        s.choose_verb(verb, e, gx, gy)
        run(60)
        run(3, ms=1500)

    assert "Bronze_Sword" not in s.equipped                         # (no sword to start with)
    maren = npc("Woman", "1,2,0")
    assert maren.display == "Maren"
    talk(maren, 1)
    assert attr() == 1
    bess = npc("Milkmaid", "2,0,0")
    talk(bess, 3, 1)                                                # the ticket book's stolen: here's an axe
    assert attr() == 2 and s.items_held("Bronze_Axe") == 1
    stock(s, Logs=3)
    talk(bess, 3)                                                   # three logs for the range
    assert attr() == 3 and s.items_held("Logs") == 0
    stock(s, Egg=1)                                                 # an egg, fried on the range
    rng = next(e for e in world.ents if e.name == "Range" and e.map == "2,0,0")
    s.teleport("2,0,0", int(rng.x - world.maps["2,0,0"].ox), int(rng.y - world.maps["2,0,0"].oy) + 30)
    run(5)
    s.item_in_use = next(e for e in s.inv if e.name == "Egg")
    s.use_item_with(rng)
    run(30)
    run(3, ms=1500)
    assert s.items_held("Fried_Egg") == 1
    talk(bess, 3)
    assert attr() == 4
    s.open_item_rack("CRAFT", "Workbench", "CRAFT-Crafting")       # (a wooden sword and shield, at Crafting 1)
    assert {r["item"] for r in s.rack if r["level"] <= 1} >= {"Wooden_Sword", "Wooden_Shield"}
    s.close_action_box(-1)
    talk(bess, 3)                                                   # not yet: unarmed
    assert attr() == 4
    stock(s, Wooden_Sword=1, Wooden_Shield=1)
    for name in ("Wooden_Sword", "Wooden_Shield"):
        s.do_action("Wield", next(e for e in s.inv if e.name == name))
    talk(bess, 3)
    assert attr() == 5
    aldous = npc("Gravekeeper", "3,1,0", "Chapel_Verger")
    talk(aldous, 1)                                                 # "What's down in the cellar?" - the key's lost
    assert attr() == 6
    at("3,1,0", 18, 9, "Climb Down")                                # the chapel's steps, armed
    assert s.cur_map.name == "3,1,-1"
    at("3,1,-1", 17, 13, "Search")                                  # the crate with the key in it
    assert s.items_held("Chapel_Cellar_Key") == 1 and attr() == 7
    at("3,1,-1", 14, 10, "Climb Down")                              # the trapdoor opens for the key
    assert s.cur_map.name == "3,1,-2"
    cage = next(e for e in world.ents if e.name == "Goblin_Cage")
    m = world.maps["1,1,-2"]
    s.teleport("1,1,-2", int(cage.x - m.ox) + 40, int(cage.y - m.oy))
    run(5)
    s.do_action("Open", cage)
    run(30)
    assert attr() == 8
    talk(aldous, 1)                                                 # a scroll of Grasp
    assert attr() == 9 and s.items_held("Grasp_Scroll") == 1
    s.teleport("1,1,-2", int(cage.x - m.ox) + 96, int(cage.y - m.oy))
    run(5, ms=2000)
    s.player_mana = s.player_max_mana
    s.cast_scroll(next(e for e in s.inv if e.name == "Grasp_Scroll"), cage)
    run(30)
    assert s.items_held("Ticket_Book") == 1 and attr() == 10
    assert s.items_held("Grasp_Scroll") == 1                        # (it keeps)
    talk(bess, 3)
    assert attr() == 11 and s.items_held("Ferry_Ticket") == 1
    talk(npc("Woman", "1,2,0"), 1)                                  # across to Southport
    run(3, ms=1500)
    assert attr() == 12
    leave(world, s)


def test_sneaking_past_the_smugglers(world):
    m = world.maps["4,5,0"]
    at = lambda tx, ty: (m.ox + (tx - 1) * 32, m.oy + (ty - 1) * 32)
    opts = "Attitude=Bad Stand=1 Face=S Group=TESTCAMP Friendly.If=$Attr.SmugglerQuest>=3"
    sentry = world.add_npc("Smuggler", 0, *at(22, 15), opts)        # (in the open, east of the camp: looking south)
    mate = world.add_npc("Smuggler", 0, *at(24, 13), opts.replace("Face=S", "Face=N"))
    for e in (sentry, mate):
        e.ai.turn_at = world.now + 10 ** 9                          # (no glancing about, for the test)
    s = join(world, "Sneak", "4,5,0", 21 * 32, 11 * 32)             # behind the sentry (north of him), 4 tiles off
    for _ in range(40):
        world.tick(0.05)
    assert not sentry.in_combat and not mate.in_combat               # (he looks the other way)
    s.teleport("4,5,0", 21 * 32, 18 * 32)                           # in front of him
    for _ in range(40):
        world.tick(0.05)
    assert sentry.in_combat and sentry.target is s
    assert mate.in_combat and mate.target is s                       # he raised the alarm
    for e in (sentry, mate):
        world.npc_give_up(e, e.ai)
    s.update_attribute("SmugglerQuest", "=3")                       # Red Meg's deal: friends now
    assert not world.hostile_for(sentry, s)
    other = join(world, "Stranger", "4,5,0", 21 * 32, 22 * 32)
    assert world.hostile_for(sentry, other)                         # (to them alone)
    for e in (sentry, mate):
        world.remove_entity(e)
    leave(world, s)
    leave(world, other)


def test_the_smugglers_run(world, monkeypatch):
    monkeypatch.setattr(world, "npc_sees", lambda e, a, s, d: False)   # (a perfect sneak, for the test)
    s = join(world, "Spy", "4,4,0", 10 * 32, 17 * 32)
    s.connected = True
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
    use("3,5,0", 12, 14, "Search", (11 * 32, 14 * 32))               # the hollow barrel
    assert attr() == 2 and s.cur_map.name == "3,5,-1"
    use("4,5,-1", 16, 11, "Climb Up", (15 * 32, 11 * 32))            # up into the camp
    assert s.cur_map.name == "4,5,0"
    use("4,5,0", 16, 11, "Climb Down", (15 * 32, 11 * 32))           # (and back down the hatch: it's a way out)
    assert s.cur_map.name == "4,5,-1"
    talk("Red_Meg", 1)
    assert attr() == 3
    gold = s.items_held("Gold_Coin(s)")
    talk("Smuggler_Sergeant", 1)
    assert attr() == 4 and s.items_held("Gold_Coin(s)") == gold + 60
    leave(world, s)


def test_a_new_character_wakes_in_the_cottage(world):
    s = Session(world, "Newborn")
    s.load_state(None)                                              # (a new character: Saves\TEMPLATE.ini)
    world.sessions["Newborn"] = s
    s.enter_world()
    world.tick(0.05)
    assert s.cur_map.name == "4,0,0" and "Bronze_Sword" not in s.equipped
    m, tx, ty = world.tile_at(s.player.z, s.player.fx, s.player.fy)
    assert m.name == "4,0,0" and m.roof[m.cell(tx, ty)]             # (indoors, under the cottage's roof)
    assert "0" not in m.walk[m.cell(tx, ty)]                        # (on open floor)
    leave(world, s)


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
    maren = [e for e in world.ents if e.name == "Woman" and e.map == "1,2,0"]
    assert maren and all(e.active and not e.sched_away for e in maren)   # (Schedule=Always: she stays at her pier)
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


def test_the_milkmaid_is_asked_about_tickets_only_once_its_time(world):
    bess = next(e for e in world.ents if e.name == "Milkmaid")
    m = world.maps[bess.map]
    s = join(world, "Asker", bess.map, int(bess.x - m.ox) - 28, int(bess.y - m.oy))
    s.connected = True
    for passage, asked in ((0, False), (1, True), (11, False)):
        s.update_attribute("Passage", "=%d" % passage)
        s.choose_verb("Talk to", bess, int(bess.cx), int(bess.cy))
        for _ in range(20):
            world.tick(0.05)
        assert any(r.startswith("About a ferry ticket") for r in s.responses) == asked, passage
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
    s.script_lines = ["", "01	Display.Message	DarkRed	You need a pickaxe!	Denied", "02	End", ""]
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
