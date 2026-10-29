"""Brings the desktop game's characters (saves\\<Name>.ini) into the server's database.

  python tools/import_saves.py                 every save (not TEMPLATE)
  python tools/import_saves.py Kris            just that one
  --replace                                     overwrite a character the server already has

Each becomes an account with no password: set one with  python tools/admin.py password <Name>. Characters named in
Config [Admin] Players get the admin flag. What a save's [Action.Queue] has waiting (respawns, dropped things,
regrowing trees) goes into the shared world's queue; one-time items taken and NPC attitudes stay the character's."""
import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from ashen import ini  # noqa: E402
from ashen.lb import val, word, trim  # noqa: E402
from dsengine.data import GameData  # noqa: E402
from server.store import Store  # noqa: E402


def split_wear(value):
    name = trim(word(value, 1, ","))
    return name, max(0, int(val(word(value, 2, ",")))) if word(value, 2, ",") else 0


def read_save(d, path):
    r = lambda s, k, default: ini.read(s, k, default, path)
    st = {"map": r("Player", "Map", d.start_map).replace(" ", ""), "x": val(r("Player", "X", str(d.start_x))),
          "y": val(r("Player", "Y", str(d.start_y))), "hp": val(r("Player", "Hitpoints", "0")),
          "mana": val(r("Player", "Mana", "-1")), "direction": max(1, int(val(r("Player", "Direction", "4")))),
          "sprite": r("Player", "Sprite", "Player"), "skills": {}, "inventory": [], "equipped": [], "bank": [],
          "attributes": [], "quest_notes": [], "npc_attitudes": {}, "taken_once": [], "hotbar": [], "explored": {},
          "grave": None}
    for i in range(1, d.total_skills + 1):
        st["skills"][d.skill_name[i]] = val(r("Skills", d.skill_name[i], "0"))
    for i in range(1, 200):
        slot = r("Inventory", "Slot%d" % i, "")
        if slot:
            st["inventory"].append([trim(word(slot, 1, ",")), max(1, val(word(slot, 2, ","))),
                                    int(val(word(slot, 3, ","))) if word(slot, 3, ",") else 0])
    for i in range(1, d.equip_slots + 1):
        st["equipped"].append(list(split_wear(r("Equipment", d.equip_slot_names[i], ""))))
    for i in range(1, d.bank_slots + 1):
        slot = r("Bank", "Slot%d" % i, "")
        if slot:
            wears = trim(word(slot, 3, ","))
            st["bank"].append([trim(word(slot, 1, ",")), max(1, val(word(slot, 2, ","))),
                               [int(val(x)) for x in wears.split(";") if trim(x)] if wears else []])
    st["attributes"] = [[k, v] for k, v in ini.section("Attributes", path)[:500]]
    for k, v in ini.section("Quest.Notes", path)[:400]:
        parts = v.split("|", 2)
        if len(parts) == 3 and trim(parts[0]) and trim(parts[2]):
            st["quest_notes"].append([trim(parts[0]), 1 if val(parts[1]) else 0, trim(parts[2])])
    for k, v in ini.section("Taken.Once", path):
        if trim(v):
            st["taken_once"].append(trim(v))
    for k, v in ini.section("NPC.Attitudes", path):
        if trim(k) and trim(v).capitalize() in ("Good", "Bad"):
            st["npc_attitudes"][trim(k)] = trim(v).capitalize()
    hot = dict(ini.section("Hotbar", path))
    st["hotbar"] = [trim(hot.get("Slot%d" % k, "")) for k in range(1, 6)]
    explored = ini.section("Explored", path)
    grid = next((v for k, v in explored if k.upper() == "GRID"), "5x5")
    gx, gy = max(1, val(word(grid, 1, "x"))), max(1, val(word(grid, 2, "x")))
    fog = max(4, min(128, int(val(ini.read("Interface", "FogOfWar.Cell.Size", "16", d.config_path)))))
    fxt, fyt = (d.sw + fog - 1) // fog, (d.sh + fog - 1) // fog
    for m in r("Explored", "Maps", "").split():
        cells = next((v for k, v in explored if k == m), "")
        if cells == "":
            st["explored"][m] = "all"
        elif (gx, gy) == (fxt, fyt):
            st["explored"][m] = [int(val(c)) for c in cells.split() if val(c) > 0]
        else:
            st["explored"][m] = "all"            # (a save from another fog grid: the whole map counts as seen)
    g = dict(ini.section("Grave", path))
    if g.get("Map"):
        items = []
        for i in range(1, 400):
            v = g.get("Item%d" % i)
            if not v:
                break
            items.append([trim(word(v, 1, ",")), max(1, val(word(v, 2, ","))), int(val(word(v, 3, ",") or "0"))])
        if items:
            st["grave"] = {"map": g["Map"], "x": val(g.get("X", "0")), "y": val(g.get("Y", "0")),
                           "left": val(g.get("Left", "0")), "items": items}
    queue = []
    total = val(r("Action.Queue", "Total", "0"))
    for i in range(1, min(int(total), 300) + 1):
        entry = r("Action.Queue", "Entry%d" % i, "").replace("[TAB]", "\t")
        if entry:
            queue.append(entry)
    return st, queue


def main():
    p = argparse.ArgumentParser(description="Import desktop saves into the server")
    p.add_argument("names", nargs="*")
    p.add_argument("--db", default=os.environ.get("DS_DB", os.path.join(ROOT, "server-data", "ashen.db")))
    p.add_argument("--replace", action="store_true")
    args = p.parse_args()
    d = GameData(ROOT)
    store = Store(args.db)
    folder = os.path.join(ROOT, "saves")
    names = args.names or [f[:-4] for f in sorted(os.listdir(folder))
                           if f.lower().endswith(".ini") and f[:-4].upper() != "TEMPLATE"]
    world = store.load_world() or {}
    queue = list(world.get("queue", []))
    for name in names:
        path = os.path.join(folder, name + ".ini")
        if not os.path.exists(path):
            print("No save %s" % path)
            continue
        if store.load_character(name) is not None and not args.replace:
            print("%s is already on the server (--replace to overwrite)" % name)
            continue
        st, q = read_save(d, path)
        if store.account(name) is None:
            store.create_account(name, "", name.lower() in d.admin_players)
        store.save_character(name, st)
        added = [e for e in q if e not in queue]
        queue += added
        print("Imported %s (%d inventory slots, %d attributes, %d queue entries)" % (
            name, len(st["inventory"]), len(st["attributes"]), len(added)))
    world["queue"] = queue
    store.save_world(world)
    store.close()
    print("Set passwords with: python tools/admin.py password <Name>")


if __name__ == "__main__":
    main()
