"""The Android app's pictures (android/), all from the game's own icon (web/img/icon.png):

  * android\\app\\src\\main\\res\\mipmap-*\\ic_launcher.png: the launcher icon at each screen density (48 to 192).
  * android\\app\\src\\main\\res\\drawable\\splash.png: shown while the game's page loads (on the game's dark brown).
  * android\\store\\icon-512.png: the Play Store listing's icon; web\\img\\icon-512.png: the web page's (its manifest).
Run it again to make them again (the same).

  python -I "dev\\migrate\\build_android.py"
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame  # noqa: E402

RES = os.path.join(ROOT, "android", "app", "src", "main", "res")
DENSITIES = {"mdpi": 48, "hdpi": 72, "xhdpi": 96, "xxhdpi": 144, "xxxhdpi": 192}
BG = (24, 14, 10)


def scaled(icon, n):
    # (pixel art: doubled up sharp first, then smoothed down to the size, so it isn't blurred nor jagged)
    big = pygame.transform.scale(icon, (icon.get_width() * 2, icon.get_height() * 2))
    return pygame.transform.smoothscale(big, (n, n))


def save(surface, *parts):
    path = os.path.join(*parts)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    pygame.image.save(surface, path)


def main():
    pygame.init()
    pygame.display.set_mode((1, 1))
    icon = pygame.image.load(os.path.join(ROOT, "web", "img", "icon.png")).convert_alpha()
    for name, n in DENSITIES.items():
        save(scaled(icon, n), RES, "mipmap-" + name, "ic_launcher.png")
    splash = pygame.Surface((384, 384), pygame.SRCALPHA)
    splash.blit(scaled(icon, 384), (0, 0))
    save(splash, RES, "drawable", "splash.png")
    store = pygame.Surface((512, 512))
    store.fill(BG)                                                   # (the store wants it square and solid)
    store.blit(scaled(icon, 512), (0, 0))
    save(store, ROOT, "android", "store", "icon-512.png")
    save(scaled(icon, 512), ROOT, "web", "img", "icon-512.png")
    print("Made the Android app's icons and splash")


if __name__ == "__main__":
    main()
