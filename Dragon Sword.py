"""Dragon Sword: run this file to play (python "Dragon Sword.py"). Needs Python 3 and pygame (pip install pygame numpy).
The game reads and writes the same Data, Maps, Saves, Sounds and Sprites folders as the Liberty BASIC version."""
import os
import sys
import warnings

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
warnings.filterwarnings("ignore", message=".*pkg_resources.*")  # pygame's own start-up notice on newer Pythons
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")


def missing(module):
    """Says what to install (in a message box, since a double-clicked game has no console to read)."""
    text = ("Dragon Sword needs %s, which isn't installed for this Python:\n\n%s\n\nInstall it by running this in a "
            "command prompt:\n\n\"%s\" -m pip install pygame numpy" % (module, sys.executable, sys.executable))
    print(text, file=sys.stderr)
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, text, "Dragon Sword", 0x10)
    except Exception:
        pass
    sys.exit(1)


try:
    import pygame  # noqa: F401
except ImportError:
    missing("pygame")
try:
    import numpy  # noqa: F401
except ImportError:
    missing("numpy")

from dragonsword.game import main  # noqa: E402

if __name__ == "__main__":
    main()
