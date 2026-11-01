"""Redrock Manor's three floors drawn again as build_manors.py lays them out now (the owner's wish: the rooms all the
same size and shape, and bare, looked wrong): rooms of their own sizes, each furnished for what it is - a kitchen, a
library, a vault, bedrooms, a wine cellar - its bandits and rats roaming their own rooms. The chests, the traps, the
stash and the ways up and down stay where they are (the way through is the same).

Safe to run again (the same each time).

  python -I "dev\migrate\refurnish_redrock.py"
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_manors as BM                       # noqa: E402
import world_edit as W                           # noqa: E402


def main():
    w = W.World(0)
    BM.maze(w, BM.MAZE, again=True)
    print("Redrock Manor: its floors laid out and furnished; %d maps of the world changed" % w.save())


if __name__ == "__main__":
    main()
