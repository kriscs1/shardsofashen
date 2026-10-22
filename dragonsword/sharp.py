"""Crisp menus on big screens.

The game is drawn 768 pixels high and scaled up to fill the screen, which softens text. The character select, the
loading screen, the journal and the quit and options boxes are drawn instead on a Sharp: a surface as many times finer
as the screen is bigger, laid over the scaled game one screen pixel to one pixel (Presenter). Code draws on a Sharp in
the game's 768-high coordinates, through the UI helpers (draw_text, round_box, box, draw_icon...), which scale it.
Without a GPU renderer (the dummy video driver) a Sharp isn't used: the plain surfaces are drawn as before.
"""
import pygame

from .assets import colour


class Sharp:
    """w x h (game pixels) drawn k times finer."""

    def __init__(self, w, h, k):
        self.w, self.h, self.k = w, h, k
        self.surf = pygame.Surface((max(1, round(w * k)), max(1, round(h * k))), pygame.SRCALPHA)
        self.tex = None             # the Presenter's texture of it, made again after drawing (dirty)
        self.dirty = True

    def get_width(self):
        return self.w

    def get_height(self):
        return self.h

    def get_size(self):
        return self.w, self.h

    def at(self, x, y):
        return round(x * self.k), round(y * self.k)

    def rect(self, r):
        """A game-pixel rectangle -> this surface's, edges rounded so boxes side by side still meet."""
        r = pygame.Rect(r)
        x1, y1 = self.at(r.x, r.y)
        x2, y2 = self.at(r.right, r.bottom)
        return pygame.Rect(x1, y1, max(1, x2 - x1), max(1, y2 - y1))

    def line_width(self, width):
        return max(1, round(width * self.k))

    def fill(self, col, rect=None):
        self.dirty = True
        self.surf.fill(colour(col), None if rect is None else self.rect(rect))

    def blit(self, img, pos):
        """A picture drawn at game size (scaled up smoothly). A Sharp's own pictures are drawn by the helpers."""
        self.dirty = True
        if isinstance(img, Sharp):
            self.surf.blit(img.surf, self.at(*pos))
            return
        w, h = img.get_size()
        big = pygame.transform.smoothscale(img.convert_alpha(), (max(1, round(w * self.k)), max(1, round(h * self.k))))
        self.surf.blit(big, self.at(*pos))


class Presenter:
    """Shows each frame: the game scaled to the window (pygame.SCALED does that), with any Sharp layers over it at the
    window's own resolution. Uses the SDL renderer behind the SCALED window."""

    def __init__(self, screen):
        self.screen = screen
        self.renderer = None
        self.screen_tex = None
        self.k = 1.0
        self.origin = (0, 0)
        try:
            from pygame._sdl2 import video
            self.video = video
            self.window = video.Window.from_display_module()
            self.renderer = video.Renderer.from_window(self.window)
            self.measure()
        except Exception:
            self.renderer = None

    @property
    def active(self):
        return self.renderer is not None and self.k > 1.01

    def measure(self):
        """The window's size in pixels -> k (screen pixels per game pixel) and where the game's top left is."""
        r = self.renderer
        logical = r.logical_size
        r.logical_size = (0, 0)
        out = r.get_viewport()
        r.logical_size = logical
        gw, gh = self.screen.get_size()
        self.k = min(out.w / gw, out.h / gh)
        self.origin = ((out.w - gw * self.k) / 2, (out.h - gh * self.k) / 2)

    def present(self, layers):
        """layers: [(Sharp, (x, y) in game pixels)]."""
        if not layers or self.renderer is None:
            pygame.display.flip()
            return
        r, v = self.renderer, self.video
        self.measure()
        if self.screen_tex is None or self.screen_tex.width != self.screen.get_width() or self.screen_tex.height != self.screen.get_height():
            self.screen_tex = v.Texture(r, self.screen.get_size(), streaming=True)
        self.screen_tex.update(self.screen)
        r.draw_color = (0, 0, 0, 255)
        r.clear()
        r.blit(self.screen_tex)
        logical = r.logical_size
        r.logical_size = (0, 0)                      # draw the layers in screen pixels, one to one
        for sharp, (x, y) in layers:
            if sharp.tex is None or sharp.dirty:
                sharp.tex = v.Texture.from_surface(r, sharp.surf)
                sharp.tex.blend_mode = 1             # SDL_BLENDMODE_BLEND
                sharp.dirty = False
            sx = round(self.origin[0] + x * self.k)
            sy = round(self.origin[1] + y * self.k)
            r.blit(sharp.tex, pygame.Rect(sx, sy, sharp.tex.width, sharp.tex.height))
        r.present()
        r.logical_size = logical
