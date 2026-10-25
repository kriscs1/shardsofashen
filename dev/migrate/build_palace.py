"""King Tyron's palace on the Royal Isle (4,4,0), and the wizard's study at the top of its tower (4,4,1).

Not run on its own: build_content.extend() calls extend() here after the Wildlands, Eastreach and Wardhaven (it needs
build_regions.legend_chars) and before the waystones and the scenery pass.

  * The isle lies in the sea east of the goblin camp (3,4,0). The camp's north road, along the top of that map above its
    cliff ridge, runs on east to a stone causeway over the water and onto the isle at row 3.
  * A royal road lined with statues and clipped hedges goes down the west of the isle and along its south front to the
    gatehouse in the curtain wall (City_Wall / City_Gate, the gates always open). The gate, the fountain in the
    courtyard, the throne hall's door, its red carpet and the throne are all on one line (column 12).
  * The throne hall: marble floor, columns, banners and torches on the walls, the throne on its dais, King Tyron before
    it. The wizard's tower (stairs up to his study, 4,4,1) and the royal treasury (a Lock: open once King Tyron's hunt
    is done; its chest is in build_scenery's Open Chest script) are in the courtyard.
  * Tyron's Keep (2,4,0) stays: the King's garrison by the crossroads (guards, the quartermaster and the roads
    south). The throne hall there is now the guards' barracks; the treasury and the tower's ladder are gone.
"""
W = C = R = None        # build_world, build_content, build_regions

PALACE, STUDY, KEEP, CAMP = "4,4,0", "4,4,1", "2,4,0", "3,4,0"

KEY = {
    "~": "Water001", "s": "Sand001", ".": "Grass001", "=": "Paving001",
    "N": "City_Wall001", "F": "City_Wall004", "|": "City_Wall002", "T": "City_Wall003", "t": "City_Wall005",
    "A": "City_Gate004", "G": "City_Gate002",
    "W": "Stone_Wall001", "w": "Stone_Wall_Window001", "D": "Door002",
    "m": "Marble001", "c": "Carpet001", "r": "Carpet002", "h": "Throne001", "P": "Pillar001",
    "B": "Banner001", "L": "Wall_Torch001", "p": "Plank001", "U": "Stairs001", "d": "Stairs002", "K": "Black001",
    "f": "Fountain001", "S": "Statue001", "Z": "Statue002", "H": "Hedge001",
    "1": "Flowers001", "2": "Flowers002", "3": "Flowers003", "b": "Bush001", "k": "Oak_Tree001", "o": "Pond001",
}

#        x: 1   5    10   15   20   25
ISLE = [
    "~~~~~~~~~~~~~~~~~~~~~~~~~",
    "~~~~~~~~~~~~~~~~~~~~~~~~~",
    "====.TNNNNNNNNNNNNNNNNNTs",     # 3: the causeway comes in from the west; the north curtain wall
    "~~s=.tFFFFFFFFFFFFFFFFFts",
    "~~s=.|WLWBWBWBWLW=WWLWW|s",     # 5: the throne hall (7-17) and the wizard's tower (19-23)
    "~~s=S|WmmmrhrmmmW=WpppW|s",
    "~~s=.|WmPmmcmmPmW=WpUpW|s",
    "~~s=H|WmmmmcmmmmW=WpppW|s",
    "~~s=.|WmPmmcmmPmW=WpppW|s",
    "~~s=S|WWWwWDWwWWW=WwDwW|s",     # 10: the hall's door (12,10) and the tower's (21,10)
    "~~s=.|H1=Z===Z=2H======|s",
    "~~s=H|H3=======3==WWWWW|s",     # 12-14: the treasury (its door 21,14 on its south side, like every house)
    "~~s=.|H====f======WmmmW|s",
    "~~s=S|H2=======1==WWDWW|s",
    "~~s=.|b1=======2b======|s",
    "~~s=.TNNNNTATNNNNNNNNNNTs",     # 16: the south curtain wall, the gatehouse at 12
    "~~s=.tFFFFtGtFFFFFFFFFFts",
    "~~s=.HHSHH.=.HHSHH.1o2k.s",
    "~~s=========...1.b.321.ks",     # 19: the royal road along the front
    "~~ssssssssssssssssssssss~",
    "~~~~~~~~~~~~~~~~~~~~~~~~~",
]
TOWER_ROWS = {5: "WWWWW", 6: "WpppW", 7: "WpdpW", 8: "WpppW", 9: "WpppW", 10: "WWWWW"}   # x 19-23 in the study
TOWER = (STUDY, 21, 9)              # (build_dragon: back beside the wizard)
TREASURY_DOOR = (21, 14)
TREASURY_NOTICE = (22, 15)


def rows_of(grid):
    chars = R.legend_chars({KEY[ch] for row in grid for ch in row})
    out = []
    for row in grid:
        assert len(row) == 25, row
        out.append("".join(chars[KEY[ch]] for ch in row))
    assert len(out) == 21
    return out


def study_grid():
    grid = []
    for y in range(1, 22):
        t = TOWER_ROWS.get(y)
        grid.append("K" * 18 + t + "KK" if t else "K" * 25)
    return grid


def palace_maps():
    npc, item, obj = W.npc, W.item, W.obj
    W.MAPS[PALACE] = dict(
        rows=rows_of(ISLE),
        roofs=[(7, 5, 17, 9, 1, "Slate"), (19, 5, 23, 9, 2, "Slate"), (19, 12, 23, 13, 3, "Slate")],
        entities=[
            npc("GoodNPC", "King_Tyron", 12, 7),
            npc("GoodNPC", "Guard", 9, 8), npc("GoodNPC", "Guard", 15, 8),         # in the hall, by the carpet
            npc("GoodNPC", "Guard", 11, 15), npc("GoodNPC", "Guard", 13, 15),      # inside the gate
            npc("GoodNPC", "Guard", 20, 11),                                        # by the treasury
            npc("GoodNPC", "Guard", 4, 6),                                          # on the royal road
            npc("GoodNPC", "Villager", 16, 13),
            obj("Notice", 5, 4), obj("Notice", *TREASURY_NOTICE),
            obj("Chest", 21, 13),
        ],
        locks=[(TREASURY_DOOR[0], TREASURY_DOOR[1], "$Attr.HobgoblinQuest>=2",
                "The royal treasury is locked. Only a hero of King Tyron may enter.")],
    )
    old = W.MAPS.pop("2,4,1")                                  # the study moves up the palace's tower
    W.MAPS[STUDY] = dict(
        rows=rows_of(study_grid()),
        roofs=[],
        entities=[npc("GoodNPC", "Wizard", 20, 8), obj("Alchemy_Table", 22, 6),
                  item("Basic_Potion", 20, 6), item("Empty_Vial", 20, 9, 2), item("Full_Vial", 22, 9)],
    )
    assert any(e[1] == "Wizard" for e in old["entities"])
    W.NEW_MAPS[:] = [m for m in W.NEW_MAPS if m != "2,4,1"] + [PALACE, STUDY]
    W.NO_SCENERY = set(getattr(W, "NO_SCENERY", ())) | {PALACE}
    C.LOCK_NOTICES[(PALACE,) + TREASURY_NOTICE] = C.LOCK_NOTICES.pop((KEEP, 14, 13))
    C.NPC_OPTIONS.pop("2,4,1", None)
    C.NPC_OPTIONS[STUDY] = {("Wizard", 20, 8): "Zone=20,8,22,9 Pause=5-12"}
    keep = C.NPC_OPTIONS[KEEP]
    C.NPC_OPTIONS[PALACE] = {
        ("King_Tyron", 12, 7): keep.pop(("King_Tyron", 15, 7)),
        ("Guard", 9, 8): "Stand=1", ("Guard", 15, 8): "Stand=1",
        ("Guard", 11, 15): "Stand=1", ("Guard", 13, 15): "Stand=1", ("Guard", 20, 11): "Stand=1",
        ("Guard", 4, 6): "Patrol=4,4/4,19/12,19 PatrolMode=PingPong Pause=2-5",
        ("Villager", 16, 13): "Zone=14,11,18,15 Pause=2-6",
    }
    keep[("Guard", 13, 9)] = "Zone=12,9,18,9 Pause=3-8"


def garrison():
    """Tyron's Keep (2,4,0) without the King: the hall is the guards' barracks, the treasury an empty storeroom, and
    the tower's ladder (to the study, now on the Royal Isle) is gone."""
    npc = W.npc
    m = W.MAPS[KEEP]
    chars = R.legend_chars({"Bed001", "Bed002", "Tile001"})
    rows = m["rows"]
    assert W.LEGEND[rows[14][17]] == "Ladder001", W.LEGEND[rows[14][17]]
    changes = [(18, 15, chars["Tile001"])]
    for x in (12, 14, 16, 18):                                   # four beds along the hall's back wall
        assert W.LEGEND[rows[6][x - 1]] == "Plank001"
        changes += [(x, 7, chars["Bed001"]), (x, 8, chars["Bed002"])]
    m["rows"] = C.set_cells(rows, changes)
    ents = []
    for e in m["entities"]:
        if e[:2] == ("GoodNPC", "King_Tyron") or e[:2] == ("StaticObject", "Chest") or \
                (e[:2] == ("StaticObject", "Notice") and e[2:4] == W.obj("Notice", 14, 13)[2:4]):
            continue
        ents.append(e)
    assert len(ents) == len(m["entities"]) - 3
    m["entities"] = ents + [npc("GoodNPC", "Guard", 13, 9)]
    m["locks"] = [lk for lk in m.get("locks", []) if (lk[0], lk[1]) != (12, 14)]


def causeway():
    """The goblin camp's north road (row 3 of 3,4,0) on east to the shore, and a stone causeway over the water."""
    m = W.MAPS[CAMP]
    chars = R.legend_chars({"Paving001"})
    rows = m["rows"]
    road = next(ch for ch, t in W.LEGEND.items() if t == "Dirt001" and ch == "=")
    changes = []
    for x in range(14, 26):
        t = W.LEGEND[rows[2][x - 1]]
        assert t in ("Grass001", "Water001"), (x, t)
        changes.append((x, 3, road if t == "Grass001" else chars["Paving001"]))
    m["rows"] = C.set_cells(rows, changes)


def notice(m, tx, ty, text):
    W.S[W.notice_script_name(m, tx, ty)] = [("Display.Conversation", "Notice", text, "Okay", "@end"), "end:", ("End",)]


def finish():
    """After build_content's scripts(): the notices, what each map says as you arrive, and the palace guards' words."""
    notice(PALACE, 5, 4, "THE ROYAL ISLE\\King Tyron's palace. The gate is open to all\\honest folk: follow the "
                         "royal road round\\to the south front.")
    notice(KEEP, 7, 12, "TYRON'S KEEP\\The King's garrison. Honest folk welcome.\\East: the goblin camp road, "
                        "and the causeway\\to the Royal Isle and King Tyron's palace.")
    W.S.pop(W.notice_script_name(KEEP, 14, 13), None)
    W.S.pop("2,4,1", None)
    W.S[KEEP] = [("Display.Message", "Cyan", "Tyron's Keep, the King's garrison."), ("End",)]
    W.S[PALACE] = [("Display.Message", "Cyan", "The Royal Isle: King Tyron's palace."), ("End",)]
    W.S[STUDY] = [("Display.Message", "Cyan", "The wizard's study. Strange smells drift from the bubbling vials."),
                  ("End",)]
    guard = W.S["Talk to Guard"]
    assert "bye:" in guard
    W.S["Talk to Guard"] = [
        (">On.Map", PALACE, "@notpalace"),
        ("Display.Conversation", "Guard", "Welcome to the Royal Isle. King Tyron holds court in the throne hall.\\"
         "Mind your manners before the throne, and keep your blade sheathed.", "Goodbye.", "@bye"),
        ("End",),
        "notpalace:"] + guard


def extend(world, content, regions):
    global W, C, R
    W, C, R = world, content, regions
    palace_maps()
    garrison()
    causeway()
