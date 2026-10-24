"""Makes web/assets: everything the browser needs to draw and play the game, from the game's own folders.

  python tools/export_web_assets.py            (needs pygame and numpy; ffmpeg on the PATH turns the music into OGG)

  web/assets/sprites/<name>.png     every sprite (the old Liberty BASIC BMPs with their mask made into transparency)
  web/assets/masks/<name>.png       the edge-blend masks (Blend_*) as transparency
  web/assets/anim/<name>~s<k>.png   plants swaying (ground tiles), ~d<k> (decor), flames ~f<k> (ground), ~F<k> (decor)
  web/assets/textures/<name>.png    big textures (Tiles.ini Texture=)
  web/assets/cursors/<kind>_<n>@<px>.png the mouse cursors (and their click animation), at each pointer size the
                                    Options offer (18 22 28 32), and twice that for sharp high-DPI screens
  web/assets/sounds/<name>.wav      the sound effects; the music as .ogg (or .wav without ffmpeg)
  web/assets/manifest.json          sprite sizes, the data files the browser reads, what was made

Run it again whenever sprites, sounds or data change (the editor). Only what changed is made again."""
import hashlib
import json
import os
import shutil
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import numpy as np  # noqa: E402
import pygame  # noqa: E402

from dragonsword import ini  # noqa: E402
from dragonsword.anim import AnimMixin  # noqa: E402
from dragonsword.assets import Assets  # noqa: E402
from dragonsword import cursor as cursors  # noqa: E402
from dsengine.data import GameData, SPRITE_FOLDERS  # noqa: E402

OUT = os.path.join(ROOT, "web", "assets")


def newer(src, dst):
    try:
        return os.path.getmtime(src) > os.path.getmtime(dst)
    except OSError:
        return True


def ini_dict(path):
    """{section: {key: value}} (keys as written; the first of each wins, like the game)."""
    out = {}
    for name, items in ini.sections(path):
        d = {}
        for k, v in items:
            d.setdefault(k, v)
        out[name] = d
    return out


def ini_list(path):
    """{section: [[key, value]...]} in file order (tables like DayNight.ini [Sky])."""
    return {name: [[k, v] for k, v in items] for name, items in ini.sections(path)}


class Baker(AnimMixin):
    """Enough of the desktop game for its animation code (anim.py) to make the frames."""

    def __init__(self, root):
        self.root = root
        self.config_path = os.path.join(root, "Data", "Config.ini")
        self.assets = Assets(root, lambda *a: None)
        self.loop_start = 0
        self.w_origin_tx = self.w_origin_ty = 0

    def tile_ini(self, section, key, default):
        return ini.read(section, key, default, os.path.join(self.root, "Data", "Tiles.ini"))

    def is_decor_tile(self, name):
        return bool(name) and self.tile_ini(name, "Layer", "").strip().lower() == "decor"

    def ground_bmp(self, name):
        if not name:
            name = "Black001"
        if not self.assets.loaded(name):
            for folder in ("Tiles", "Entities", "Interface"):
                if self.assets.load_if_exists(folder, name):
                    break
        return self.assets.get(name)


def export_sprites(d, manifest):
    out = os.path.join(OUT, "sprites")
    os.makedirs(out, exist_ok=True)
    sizes = {}
    made = 0
    for name, (folder, path) in d.sprites.items():
        dst = os.path.join(out, name + ".png")
        sizes[name] = list(d.size_of(name))
        if not newer(path, dst):
            continue
        made += 1
        if path.lower().endswith(".png"):
            shutil.copyfile(path, dst)
            continue
        a = Assets(ROOT, lambda *x: None)
        a.load_path(name, path)
        sp = a.get(name)
        if sp is not None:
            pygame.image.save(sp.masked, dst)
    manifest["sprites"] = sizes
    print("sprites: %d (%d made)" % (len(sizes), made))


def export_masks(d):
    out = os.path.join(OUT, "masks")
    os.makedirs(out, exist_ok=True)
    n = 0
    for name, (folder, path) in d.sprites.items():
        if not name.startswith("Blend_"):
            continue
        dst = os.path.join(out, name + ".png")
        if not newer(path, dst):
            continue
        img = pygame.image.load(path)
        if path.lower().endswith(".bmp"):
            img = img.subsurface((0, img.get_height() // 2, img.get_width(), img.get_height() // 2)).copy()
        rgb = pygame.surfarray.array3d(img).astype(np.int32)
        mask = pygame.Surface(img.get_size(), pygame.SRCALPHA)
        mask.fill((255, 255, 255, 255))
        alpha = pygame.surfarray.pixels_alpha(mask)
        alpha[:, :] = np.where(rgb.sum(axis=2) >= 384, 255, 0).astype(np.uint8)
        del alpha
        pygame.image.save(mask, dst)
        n += 1
    print("blend masks: %d made" % n)


def export_textures(d, manifest):
    src = os.path.join(ROOT, "Sprites", "Textures")
    out = os.path.join(OUT, "textures")
    os.makedirs(out, exist_ok=True)
    names = []
    if os.path.isdir(src):
        for f in os.listdir(src):
            n, ext = os.path.splitext(f)
            if ext.lower() == ".png":
                names.append(n)
                if newer(os.path.join(src, f), os.path.join(out, f)):
                    shutil.copyfile(os.path.join(src, f), os.path.join(out, f))
    manifest["textures"] = names


def export_anim(d, manifest):
    """Swaying plants and flickering flames, made by the desktop game's own code (anim.py)."""
    out = os.path.join(OUT, "anim")
    os.makedirs(out, exist_ok=True)
    b = Baker(ROOT)
    tiles = ini_dict(d.data_file("Tiles.ini"))
    info = {}
    land = []
    stamp = max(os.path.getmtime(d.data_file("Tiles.ini")), os.path.getmtime(d.config_path))
    made = 0
    for name in tiles:
        if not d.loaded(name):
            continue
        entry = {}
        decor = b.is_decor_tile(name)
        kind = b.decor_anim_kind(name) if decor else b.anim_kind(name)
        frames = []
        prefix = None
        if kind == "sway":
            frames = (b.decor_sway_frames(name) if decor else b.sway_frames(name)) or []
            prefix = "d" if decor else "s"
        elif kind == "flame":
            count = b.anim_setting("Flame.Frames")
            frames = [b.flame_frame(name, k, see_through=decor) for k in range(count)]
            if any(f is None for f in frames):
                frames = []
            prefix = "F" if decor else "f"
        elif kind == "water" and b.tile_has_land(name):
            land.append(name)
        if frames:
            for k, f in enumerate(frames):
                dst = os.path.join(out, "%s~%s%d.png" % (name, prefix, k))
                if not os.path.exists(dst) or os.path.getmtime(dst) < stamp:
                    pygame.image.save(f, dst)
                    made += 1
            entry[prefix] = len(frames)
        if entry:
            info[name] = entry
    manifest["anim"] = info
    manifest["land"] = land
    print("animated tiles: %d (%d frames made)" % (len(info), made))


def export_cursors(manifest):
    out = os.path.join(OUT, "cursors")
    os.makedirs(out, exist_ok=True)
    c = cursors.Cursors()
    info = {}
    sizes = (18, 22, 28, 32)
    # (drawn again whenever the cursors' code changes: its fingerprint is in the manifest, so browsers fetch them anew)
    import hashlib
    src = open(cursors.__file__, "rb").read()
    stamp = hashlib.sha1(src).hexdigest()[:10]
    stamp_file = os.path.join(out, ".drawn")
    fresh = not os.path.exists(stamp_file) or open(stamp_file).read().strip() != stamp
    for kind, (_, hot) in cursors.KINDS.items():
        for step in range(-1, 7):
            for px in sorted({s for s in sizes} | {2 * s for s in sizes}):
                dst = os.path.join(out, "%s_%d@%d.png" % (kind, step + 1, px))
                if fresh or not os.path.exists(dst):
                    pygame.image.save(c._frame(kind, step, px), dst)
        info[kind] = list(hot)
    with open(stamp_file, "w") as f:
        f.write(stamp)
    manifest["cursors"] = {"hot": info, "verbs": cursors.VERBS, "swings": sorted(cursors.SWINGS),
                           "click_ms": cursors.CLICK_MS, "frames": 8, "sizes": list(sizes), "unit": cursors.SIZE,
                           "drawn": stamp}


def export_sounds(manifest):
    from tools import midisynth
    src = os.path.join(ROOT, "Sounds")
    out = os.path.join(OUT, "sounds")
    os.makedirs(out, exist_ok=True)
    ffmpeg = shutil.which("ffmpeg")
    sounds = {}
    for f in sorted(os.listdir(src)):
        n, ext = os.path.splitext(f)
        path = os.path.join(src, f)
        if ext.lower() == ".wav":
            if newer(path, os.path.join(out, f)):
                shutil.copyfile(path, os.path.join(out, f))
            sounds[f] = f
        elif ext.lower() == ".mid":
            target = n + (".ogg" if ffmpeg else ".wav")
            dst = os.path.join(out, target)
            if newer(path, dst):
                t0 = time.time()
                audio, secs = midisynth.render(path)
                wav = os.path.join(out, n + ".wav")
                midisynth.write_wav(wav, audio)
                if ffmpeg:
                    if midisynth.to_ogg(wav, dst, ffmpeg):
                        os.remove(wav)
                    else:
                        target = n + ".wav"
                print("  music %s: %.0f s (%.1fs)" % (f, secs, time.time() - t0))
            sounds[f] = target
    manifest["sounds"] = sounds
    print("sounds: %d" % len(sounds))


def export_data(d, manifest):
    df = d.data_file
    manifest["tiles"] = ini_dict(df("Tiles.ini"))
    manifest["entities"] = ini_dict(df("Entities.ini"))
    manifest["config"] = ini_dict(d.config_path)
    manifest["daynight"] = ini_list(df("DayNight.ini"))
    manifest["weather"] = ini_list(df("Weather.ini"))
    manifest["ambient"] = ini_dict(df("Ambient.ini"))
    manifest["music"] = ini_dict(df("Music.ini"))
    manifest["spells"] = ini_dict(df("Spells.ini"))
    manifest["maps"] = d.map_names()
    manifest["skills"] = d.skill_name[1:]
    manifest["geometry"] = {"tw": d.tw, "th": d.th, "xt": d.xt, "yt": d.yt, "walk_res": d.walk_res}


def main():
    t0 = time.time()
    pygame.init()
    pygame.display.set_mode((1, 1))
    os.makedirs(OUT, exist_ok=True)
    d = GameData(ROOT)
    manifest = {}
    export_data(d, manifest)
    export_sprites(d, manifest)
    export_masks(d)
    export_textures(d, manifest)
    export_anim(d, manifest)
    export_cursors(manifest)
    export_sounds(manifest)
    body = json.dumps(manifest, separators=(",", ":"), sort_keys=True)
    manifest["version"] = hashlib.sha1(body.encode()).hexdigest()[:12]
    with open(os.path.join(OUT, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, separators=(",", ":"))
    print("manifest: %d KB, version %s (%.1fs)" % (len(body) // 1024, manifest["version"], time.time() - t0))


if __name__ == "__main__":
    main()
