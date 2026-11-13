"""The small things the page draws on the ground (web/js/effects.js), as data: which grounds keep footprints and how
long (Tiles.ini Prints=R G B A Seconds: the print's colour, how dark, how long it lasts), what casts no shadow
(Entities.ini Shadow=0: a ghost, a wisp, the ferry, whose shadow is in its picture), what flies (Shadow.Lift=N: its
shadow N pixels under it, smaller and fainter) and what gives off sparks (Embers=N, on a thing or a tile: N at once).
Safe to run again.

  python -I "dev\\migrate\\build_ground_fx.py"
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from ashen import ini  # noqa: E402

ENTITIES = os.path.join(ROOT, "data", "Entities.ini")
TILES = os.path.join(ROOT, "data", "Tiles.ini")

PRINTS = {                       # (soft ground: snow keeps them longest, a crust of salt or chalk a while)
    "Snow001": "112 132 170 120 14",
    "Sand001": "132 96 52 125 8",
    "Marsh001": "40 36 20 120 8",
    "Ash001": "38 34 32 110 10",
    "Dust001": "106 82 54 90 8",
    "Salt_Flat001": "136 136 124 90 10",
    "Spore_Loam001": "26 20 16 110 8",
    "Chalk_Floor001": "136 130 114 80 8",
}

NO_SHADOW = ["Chalk_Wraith", "Dust_Wraith", "Ice_Wraith", "Shard_Wraith", "Tunnel_Wraith", "Delver_Ghost",
             "Orrin_Ghost", "Ghost_Warden", "Archmage_Shade", "Wandering_Echo", "Orrins_Shadow", "Arcane_Wisp",
             "Ferry_Boat", "Fairy_Ring", "Mosquito"]

LIFT = {"Bat": 12, "Glass_Bat": 12, "Lantern_Moth": 14, "Butterfly": 10, "Blue_Butterfly": 10}

EMBERS = {"Fire": 3, "Blaze": 5, "Signal_Pyre_Lit": 4, "Furnace": 2, "Foundry_Hearth": 3, "Sun_Forge": 3,
          "Dragonforge": 3}
TILE_EMBERS = {"Fireplace001": 2, "Fireplace002": 2, "Fireplace003": 2, "Campfire001": 3, "Ember_Vent001": 3,
               "Lava001": 1, "Wall_Torch001": 1}


def main():
    ents = {s for s, _ in ini.sections(ENTITIES) if s}
    tiles = {s for s, _ in ini.sections(TILES) if s}
    n = 0
    for name, v in PRINTS.items():
        assert name in tiles, name
        ini.write(name, "Prints", v, TILES); n += 1
    for name, v in TILE_EMBERS.items():
        assert name in tiles, name
        ini.write(name, "Embers", str(v), TILES); n += 1
    for name in NO_SHADOW:
        assert name in ents, name
        ini.write(name, "Shadow", "0", ENTITIES); n += 1
    for name, v in LIFT.items():
        assert name in ents, name
        ini.write(name, "Shadow.Lift", str(v), ENTITIES); n += 1
    for name, v in EMBERS.items():
        assert name in ents, name
        ini.write(name, "Embers", str(v), ENTITIES); n += 1
    print("ground effects: %d keys set" % n)


if __name__ == "__main__":
    main()
