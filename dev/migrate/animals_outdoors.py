"""Animals stay out of houses: Indoors=0 in Entities.ini for every animal but the cats and the dog (they're welcome in).
An NPC with Indoors=0 never steps from open ground under a roof (world.py entity_can_stand); one that starts under one
(a rat in a barn) may walk out, and a creature with a Roost goes into its own (hens to their coop).
Safe to run again (a creature that has its Indoors already is left as it is).
Usage: python -I dev/migrate/animals_outdoors.py

Superseded (2026-10-31) by assign_homes.py: there's no Indoors rule now - an animal's Zone and Chase leave out the
houses on its map instead, and one with a Home= goes into it."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import Ini, p                      # noqa: E402

ANIMALS = ("Chicken", "Cow", "Sheep", "Rabbit", "Duck", "Goose", "Horse", "Duchess", "Otter", "Seal", "Frog",
           "Wolf", "Snow_Wolf", "Alpha_Wolf", "Bear", "Scorpion", "Ember_Hound", "Rat", "Bat", "Giant_Spider",
           "Butterfly", "Blue_Butterfly", "Drake", "Dragon", "Galaith_Dragon")


def main():
    sys.exit("Superseded: animals keep out of houses by their zones now (assign_homes.py); Indoors= is gone.")


def old_main():
    ini = Ini(p("data", "Entities.ini"))
    done = 0
    for name in ANIMALS:
        if ini.section(name) and not ini.has(name, "Indoors"):
            ini.set(name, "Indoors", "0")
            done += 1
    ini.save(p("data", "Entities.ini"))
    print("Indoors=0 for %d animals." % done)


if __name__ == "__main__":  # (superseded: see main)
    main()
