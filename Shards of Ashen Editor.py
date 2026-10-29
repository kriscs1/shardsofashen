"""Shards of Ashen Editor: every editor in one window (maps, scripts, tiles, entities, item racks, spells, quests,
minimaps). Run:  python "Shards of Ashen Editor.py"   (or double-click it)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dsedit.app import main  # noqa: E402

if __name__ == "__main__":
    main()
