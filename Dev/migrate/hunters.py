"""Some creatures go after others (Hunts= in Entities.ini): wolves and bears after the rabbits, sheep, hens and ducks,
dogs after the rabbits and the rats, cats after the rats. What they go for runs (Flees=1) or fights back; what they
kill leaves nothing behind and comes back as it would after a player killed it. Safe to run again.

  python -I "Dev\\migrate\\hunters.py"
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_isle import DATA  # noqa: E402
from build_cats import CATS  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from dragonsword import ini  # noqa: E402

HUNTS = {"Wolf": "Rabbit,Sheep,Chicken,Duck", "Snow_Wolf": "Rabbit,Sheep,Chicken,Duck",
         "Alpha_Wolf": "Rabbit,Sheep,Chicken,Duck", "Bear": "Rabbit,Sheep", "Dog": "Rabbit,Rat"}
HUNTS.update({cat: "Rat" for cat in CATS})


def main():
    ents = os.path.join(DATA, "Entities.ini")
    n = 0
    for who, prey in HUNTS.items():
        if ini.section(who, ents) and ini.read(who, "Hunts", "", ents) != prey:
            ini.write(who, "Hunts", prey, ents)
            n += 1
    print("Hunters: %d set (%s)" % (n, ", ".join(HUNTS)))


if __name__ == "__main__":
    main()
