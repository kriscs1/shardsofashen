"""Houses furnished for who lives there (interior_props.py draws the things): a trader's shop has shelves of goods
along the back wall, sacks, barrels and crates, and a counter beside them; a bank its counter and chests of coin;
an herbalist or a witch drying herbs, potions and a cauldron on the boil; the elder a bed and candles; the
fisherman nets and barrels of fish. The usual furniture (villages.py, build_content.furnish_old_houses) gives way.
Every placement keeps the doorway, the person and their neighbours clear, and every bit of floor reachable from
the door, or it isn't made. Run by build_content.extend on the maps' rows (before they're written)."""
import random

THEMES = {"Trader": "shop", "Shopkeeper": "shop", "Banker": "bank", "Herbalist": "herbal", "Witch": "herbal",
          "Elder": "elder", "Fisherman": "fisher"}
LAYOUTS = {   # theme: [(where, tiles to choose from in turn)]
    "shop": [("back", ["Shelf_Goods001", "Shelf_Goods001", "Sacks001"]), ("front_corner", ["Barrel002", "Crate002"]),
             ("beside", ["Counter001"]), ("side", ["Crate002", "Sacks001"])],
    "bank": [("back_corner", ["Coin_Chest001"]), ("beside", ["Counter001"]), ("front_corner", ["Potted_Plant001",
             "Candles001"]), ("back", ["Bookshelf001"])],
    "herbal": [("back", ["Herb_Rack001", "Potion_Shelf001"]), ("middle", ["Cauldron001"]),
               ("front_corner", ["Candles001", "Barrel002"]), ("side", ["Herb_Rack001"])],
    "elder": [("bed", ["Bed001"]), ("back", ["Bookshelf001", "Candles001"]), ("front_corner", ["Potted_Plant001"])],
    "fisher": [("back", ["Nets001", "Nets001", "Fish_Barrel001"]), ("front_corner", ["Fish_Barrel001", "Barrel002"]),
               ("side", ["Crate002"])],
}
FURNITURE = {"Table001", "Chair001", "Chair002", "Chair003", "Chair004", "Bookshelf001", "Potted_Plant001"}
FLOORS = {"Plank001", "Tile001", "Marble001"}


def theme_interiors(W, R, C):
    new = {t for lay in LAYOUTS.values() for _, ts in lay for t in ts} | {"Bed002"} | FLOORS
    chars = R.legend_chars(new)
    done = 0
    for name, spec in sorted(W.MAPS.items()):
        if name in W.PROTECTED_MAPS or not spec.get("roofs"):
            continue
        rows = spec["rows"]
        h, w = len(rows), len(rows[0])
        grid = {(x, y): W.LEGEND[rows[y - 1][x - 1]].split("+")[0] for y in range(1, h + 1) for x in range(1, w + 1)}
        people = {}
        for e in spec["entities"]:
            if e[0] in W.NPC_KINDS:
                try:
                    people[(int(float(e[2]) + 16) // 32 + 1, int(float(e[3]) + 28) // 32 + 1)] = e[1]
                except (ValueError, IndexError):
                    pass
        changes = {}
        for roof in spec["roofs"]:
            x1, y1, x2, y2 = roof[:4]
            who = [(xy, n) for xy, n in people.items() if x1 <= xy[0] <= x2 and y1 <= xy[1] <= y2 and n in THEMES]
            if not who:
                continue
            (nx, ny), person = who[0]
            inside = {(x, y) for y in range(y1, y2 + 1) for x in range(x1, x2 + 1)
                      if grid[(x, y)] in FLOORS or grid[(x, y)] in FURNITURE or grid[(x, y)].startswith("Rug")}
            if len(inside) < 6:
                continue
            doors = [x for x in range(x1, x2 + 1) if grid.get((x, y2 + 1), "").startswith("Door")]
            entry = (doors[0], y2) if doors else None
            if entry not in inside:
                continue
            floor = next((grid[c] for c in inside if grid[c] in FLOORS), "Plank001")
            cells = dict((c, grid[c]) for c in inside)
            theme = THEMES[person]
            for c, t in list(cells.items()):
                if t in FURNITURE or (t.startswith("Rug") and theme != "elder"):
                    cells[c] = floor                    # (the usual furniture, and a shop's rug, give way)
            keep = {entry, (entry[0] - 1, entry[1]), (entry[0] + 1, entry[1]), (entry[0], entry[1] - 1),
                    (nx, ny), (nx, ny + 1), (nx, ny - 1)}
            for (sx, sy), t in grid.items():           # (round stairs and ladders nothing changes: the floor
                if t.startswith(("Stairs", "Ladder")) and x1 <= sx <= x2 and y1 <= sy <= y2:     # above must match)
                    keep |= {(sx + dx, sy + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)}
            for c in list(cells):
                if c in keep and grid[c] in FURNITURE:
                    cells[c] = grid[c]
            xs = [c[0] for c in inside]
            ys = [c[1] for c in inside]
            bx0, bx1, by0, by1 = min(xs), max(xs), min(ys), max(ys)

            def open_cell(c):
                return c in cells and (cells[c] in FLOORS or cells[c].startswith("Rug"))

            def reachable():
                todo, seen = [entry], {entry}
                while todo:
                    x, y = todo.pop()
                    for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                        if n not in seen and open_cell(n):
                            seen.add(n)
                            todo.append(n)
                spots = [c for c in cells if open_cell(c)]
                return all(c in seen for c in spots) and (nx, ny) in seen

            def place(c, tile):
                if c not in cells or c in keep or not open_cell(c) or cells[c].startswith("Rug"):
                    return False
                old = cells[c]
                cells[c] = tile
                if reachable():
                    return True
                cells[c] = old
                return False
            rng = random.Random("%s:%d:%d" % (name, x1, y1))
            spots = {
                "back": [(x, by0) for x in range(bx0, bx1 + 1)],
                "back_corner": [(bx0, by0), (bx1, by0)],
                "front_corner": [(bx0, by1), (bx1, by1)],
                "side": [(bx0, y) for y in range(by0 + 1, by1)] + [(bx1, y) for y in range(by0 + 1, by1)],
                "beside": [(nx - 1, ny), (nx + 1, ny)],
                "middle": sorted(inside, key=lambda c: abs(c[0] - (bx0 + bx1) / 2.0) + abs(c[1] - (by0 + by1) / 2.0)),
                "bed": [(x, by0) for x in (bx1, bx0)],
            }
            for where, tiles in LAYOUTS[theme]:
                k = 0
                for c in spots[where]:
                    if where == "bed":                  # (a bed: its head on the back row, its foot below)
                        foot = (c[0], c[1] + 1)
                        if open_cell(foot) and foot not in keep and place(c, "Bed001"):
                            if not place(foot, "Bed002"):
                                cells[c] = floor
                            else:
                                break
                        continue
                    if place(c, tiles[k % len(tiles)]):
                        k += 1
                        if where in ("middle",):
                            break
                    if where == "side" and k >= 2:
                        break
            for c, t in cells.items():
                if t != grid[c]:
                    changes[c] = t
            done += 1
        if changes:
            spec["rows"] = C.set_cells(rows, [(x, y, chars[t]) for (x, y), t in changes.items()])
    return done
