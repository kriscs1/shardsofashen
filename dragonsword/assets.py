"""Sprites, fonts and sounds.

Sprites are PNGs: the picture, with transparency where it is see-through (a plain picture for the interface panels and
textures). The old Liberty BASIC BMPs still load too: twice as high as the picture, the top half the mask (black =
drawn, white = see-through), the bottom half the picture. Either way each one is a Sprite with
  * image  - the picture, opaque (tiles painted into the ground, plain blits),
  * masked - the picture with its transparency (how sprites are drawn),
  * full   - the whole file as loaded (the interface panels are plain pictures)."""
import os

import numpy as np
import pygame

EXTS = (".png", ".bmp")        # a PNG first; an old BMP if that's what there is


class Sprite:
    __slots__ = ("name", "w", "h", "full", "_image", "_masked", "_flipped", "single")

    def __init__(self, name, full, single=False):
        """single: a PNG (the whole file is the picture); otherwise a BMP with its mask half on top."""
        self.name = name
        self.full = full
        self.single = single
        fw, fh = full.get_size()
        self.w = fw
        self.h = fh if single else fh // 2
        self._image = None
        self._masked = None
        self._flipped = None

    @property
    def image(self):
        if self._image is None:
            h = max(1, self.h)
            if self.single:                         # (the colours under see-through pixels kept, as a BMP's are)
                img = pygame.Surface(self.full.get_size())
                if pygame.display.get_surface() is not None:
                    img = img.convert()
                pygame.surfarray.blit_array(img, pygame.surfarray.array3d(self.full))
                self._image = img
            elif self.full.get_height() >= 2 * h:
                self._image = self.full.subsurface((0, h, self.w, h)).copy()
            else:
                self._image = self.full.copy()
        return self._image

    @property
    def masked(self):
        if self._masked is None:
            h = self.h
            if self.single or h < 1 or self.full.get_height() < 2 * h:
                self._masked = self.full.convert_alpha() if pygame.display.get_surface() is not None else self.full
                return self._masked
            pic = self.full.subsurface((0, h, self.w, h)).copy().convert_alpha()
            mask = pygame.surfarray.array3d(self.full.subsurface((0, 0, self.w, h)))
            drawn = mask.astype(np.int32).sum(axis=2) < 384
            alpha = pygame.surfarray.pixels_alpha(pic)
            alpha[:] = np.where(drawn, 255, 0).astype(np.uint8)
            del alpha
            self._masked = pic
        return self._masked

    @property
    def flipped(self):
        if self._flipped is None:
            self._flipped = pygame.transform.flip(self.masked, True, False)
        return self._flipped


def sprite_file(root, folder, name):
    """sprites\\<folder>\\<name>.png (or .bmp): the path, or None if there is neither."""
    for ext in EXTS:
        path = os.path.join(root, "sprites", folder, name + ext)
        if os.path.exists(path):
            return path
    return None


class Assets:
    def __init__(self, root, log_missing):
        self.root = root
        self.sprites = {}
        self.log_missing = log_missing
        self.fonts = {}
        self.sounds = {}
        self.font_name = "Palatino Linotype"

    # ----- sprites
    def loaded(self, name):
        return bool(name) and name in self.sprites

    def load_file(self, folder, name):
        """Load.Sprite.File: sprites\\<folder>\\<name>.png (logs it once if it is missing). True if loaded."""
        if not name or name == "Thumb":
            return False
        if name in self.sprites:
            return True
        path = sprite_file(self.root, folder, name)
        if path is None:
            self.log_missing("Sprite", name)
            return False
        return self.load_path(name, path)

    def load_path(self, name, path):
        single = not path.lower().endswith(".bmp")
        try:
            surf = pygame.image.load(path)
            if pygame.display.get_surface() is not None:
                surf = surf.convert_alpha() if surf.get_flags() & pygame.SRCALPHA else surf.convert()
        except Exception:
            self.log_missing("Sprite", name)
            return False
        self.sprites[name] = Sprite(name, surf, single)
        return True

    def load_if_exists(self, folder, name):
        """Loads sprites\\<folder>\\<name>.png if it is there (no log). True if it is loaded."""
        if name in self.sprites:
            return True
        path = sprite_file(self.root, folder, name)
        if path is None:
            return False
        return self.load_path(name, path)

    def folder_names(self, folder):
        path = os.path.join(self.root, "sprites", folder)
        try:
            files = sorted(os.listdir(path), key=str.lower)
        except OSError:
            return []
        names = []
        for f in files:
            n, ext = os.path.splitext(f)
            if ext.lower() in EXTS and n not in names:
                names.append(n)
        return names

    def register(self, name, surface, masked=None):
        """A picture made while the game runs (no mask half): stored as a sprite."""
        sp = Sprite(name, surface)
        sp.h = surface.get_height()
        sp._image = surface
        sp._masked = masked if masked is not None else surface
        self.sprites[name] = sp
        return sp

    def get(self, name):
        return self.sprites.get(name)

    def width(self, name):
        sp = self.sprites.get(name)
        return sp.w if sp else 32

    def height(self, name):
        sp = self.sprites.get(name)
        return sp.h if sp else 32

    def picture_height(self, name, default=32):
        """A plain picture's height (the interface panels: the whole file, whichever format)."""
        sp = self.sprites.get(name)
        return sp.full.get_height() if sp else default

    # ----- fonts
    def font(self, size, bold=False, name=None):
        """A font like LB's "font <name> <size> [bold]" (size in points)."""
        name = (name or self.font_name).replace("_", " ")
        key = (name, size, bold)
        f = self.fonts.get(key)
        if f is None:
            px = max(6, int(round(size * 4 / 3)))
            try:
                f = pygame.font.SysFont(name, px, bold=bold)
            except Exception:
                f = pygame.font.Font(None, px + 2)
                f.set_bold(bold)
            self.fonts[key] = f
        return f

    def text_width(self, text, size, bold=False):
        if not text:
            return 0
        return self.font(size, bold).size(text)[0]

    # ----- sounds
    def sound(self, path):
        s = self.sounds.get(path)
        if s is None:
            try:
                s = pygame.mixer.Sound(path)
            except Exception:
                s = False
            self.sounds[path] = s
        return s or None


def colour(text, default=(0, 0, 0)):
    """An LB colour name or "r g b" -> (r, g, b)."""
    if isinstance(text, tuple):
        return text
    t = str(text).strip().lower()
    parts = t.split()
    if len(parts) >= 3:
        try:
            return tuple(max(0, min(255, int(float(p)))) for p in parts[:3])
        except ValueError:
            return default
    return NAMED.get(t, default)


NAMED = {
    "buttonface": (240, 240, 240),
    "yellow": (255, 255, 0),
    "brown": (128, 128, 0),
    "red": (255, 0, 0),
    "darkred": (128, 0, 0),
    "pink": (255, 0, 255),
    "darkpink": (128, 0, 128),
    "blue": (0, 0, 255),
    "darkblue": (0, 0, 128),
    "green": (0, 255, 0),
    "darkgreen": (0, 128, 0),
    "cyan": (0, 255, 255),
    "darkcyan": (0, 128, 128),
    "white": (255, 255, 255),
    "black": (0, 0, 0),
    "lightgray": (192, 192, 192),
    "lightgrey": (192, 192, 192),
    "darkgray": (128, 128, 128),
    "darkgrey": (128, 128, 128),
}
