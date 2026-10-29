"""Some creatures go after others (Hunts= in Entities.ini): wolves and bears after the rabbits, sheep, hens and ducks,
dogs after the rabbits and the rats, cats after the rats. What they go for runs (Flees=1) or fights back; what they
kill leaves nothing behind and comes back as it would after a player killed it. The guards (and the town's law)
hunt foes (Hunts=Foes: any monster that attacks on sight, even one that's fighting you), with the arms to do it.
Safe to run again.

  python -I "dev\\migrate\\hunters.py"
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_isle import DATA  # noqa: E402
from build_cats import CATS  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from ashen import ini  # noqa: E402

HUNTS = {"Wolf": "Rabbit,Sheep,Chicken,Duck", "Snow_Wolf": "Rabbit,Sheep,Chicken,Duck",
         "Alpha_Wolf": "Rabbit,Sheep,Chicken,Duck", "Bear": "Rabbit,Sheep", "Dog": "Rabbit,Rat"}
HUNTS.update({cat: "Rat" for cat in CATS})
# a guard's fighting stats: Hitpoints, Strength, Defence, Attack.Speed, Aggro.Range (how far it sees a foe), and
# Chase.Radius (tiles past its post or beat it will go after one)
GUARDS = {"Guard": (30, 4, 4, 1, 200, 6), "Port_Guard": (30, 4, 4, 1, 200, 6), "Constable": (25, 3, 3, 1, 180, 6),
          "Sheriff": (35, 5, 4, 1, 200, 6), "Royal_Guard": (45, 6, 6, 1, 220, 6), "Guard_Captain": (55, 7, 6, 1, 220, 6)}


def main():
    ents = os.path.join(DATA, "Entities.ini")
    n = 0
    for who, prey in HUNTS.items():
        if ini.section(who, ents) and ini.read(who, "Hunts", "", ents) != prey:
            ini.write(who, "Hunts", prey, ents)
            n += 1
    keys = ("Hitpoints", "Strength", "Defence", "Attack.Speed", "Aggro.Range", "Chase.Radius")
    for who, stats in GUARDS.items():
        if not ini.section(who, ents):
            continue
        for k, v in list(zip(keys, (str(x) for x in stats))) + [("Hunts", "Foes")]:
            if ini.read(who, k, "", ents) != v:
                ini.write(who, k, v, ents)
                n += 1
    print("Hunters: %d set (%s; the guards: %s)" % (n, ", ".join(HUNTS), ", ".join(GUARDS)))


if __name__ == "__main__":
    main()
