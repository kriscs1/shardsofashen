"""The loading screen, character select, the quit and options dialogs, the journal (H / F1 / ? Help) and the admin
panel."""
import datetime
import os

import pygame

from . import ini
from .assets import colour
from .lb import val, word, trim, lbstr, pretty
from .sharp import Sharp

PARCHMENT = (212, 191, 126)
DARK = (77, 43, 33)
INK = (243, 232, 136)


class ScreensMixin:
    # =================================================================================================================
    # Loading screen and character select
    # =================================================================================================================
    def box(self, surf, x1, y1, x2, y2, fill, border, size):
        r = pygame.Rect(x1, y1, x2 - x1 + 1, y2 - y1 + 1)
        if isinstance(surf, Sharp):
            r, size = surf.rect(r), surf.line_width(size) if size > 0 else 0
            surf.dirty = True
            surf = surf.surf
        pygame.draw.rect(surf, colour(fill), r)
        if size > 0:
            pygame.draw.rect(surf, colour(border), r, size)

    def centre_baseline(self, surf, text, y, size, bold, col):
        w = self.text_width(text, size, bold)
        self.draw_text_baseline(surf, text, int((1024 - w) / 2), y, size, bold, col)

    def draw_loading_panel(self, surf, title_y):
        surf.fill((24, 14, 10))
        self.box(surf, 232, 174, 792, 594, (126, 77, 63), DARK, 3)
        self.box(surf, 247, 189, 777, 579, PARCHMENT, DARK, 2)
        self.centre_baseline(surf, "Dragon Sword", title_y, 30, True, DARK)

    def draw_loading_screen(self, status):
        self.loading_active = True
        self.loading_last_percent = -1
        self.loading_status = status
        self.loading_progress(0, status)

    def loading_progress(self, fraction, status):
        """Moves the loading bar (0 to 1) and shows it at once."""
        if not self.loading_active:
            return
        percent = int(min(1, max(0, fraction)) * 100)
        if percent == self.loading_last_percent and status == self.loading_status:
            return
        self.loading_last_percent = percent
        self.loading_status = status
        self.page = surf = self.make_sharp(1024, 768, self.page)
        self.draw_loading_panel(surf, 270)
        self.centre_baseline(surf, "A tale of goblins, gold and a very lost key", 305, 11, False, (126, 77, 63))
        self.box(surf, 312, 430, 712, 452, (51, 34, 27), DARK, 1)
        if percent > 0:
            self.box(surf, 314, 432, 314 + int(396 * percent / 100), 450, (21, 171, 75), (21, 171, 75), 0)
        self.centre_baseline(surf, "%s  (%d%%)" % (status, percent), 485, 10, False, DARK)
        self.present_page()
        pygame.event.pump()

    def hide_loading_screen(self):
        self.loading_active = False

    # Saved characters: six to a page (two columns of three), most recently played first
    LOGIN_PER_PAGE = 6

    # The panel: the chosen character's portrait on the left, the saved characters (cards) on the right
    LOGIN_CARD_W = 210
    LOGIN_CARD_H = 36

    def login_button_x(self, i):
        return 392 + ((i - 1) % 2) * 230

    def login_button_y(self, i):
        return 258 + int((i - 1) / 2) * 42

    def login_pages(self):
        return max(1, int((len(self.login_saves) + self.LOGIN_PER_PAGE - 1) / self.LOGIN_PER_PAGE))

    def login_page_saves(self):
        first = self.login_page * self.LOGIN_PER_PAGE
        return self.login_saves[first:first + self.LOGIN_PER_PAGE]

    def login_button_at(self, x, y):
        """1-6 = a character on this page, 97 / 98 = previous / next page, 99 = Start, 0 = nothing."""
        for i in range(1, len(self.login_page_saves()) + 1):
            bx, by = self.login_button_x(i), self.login_button_y(i)
            if bx <= x <= bx + self.LOGIN_CARD_W and by <= y <= by + self.LOGIN_CARD_H:
                return i
        if self.login_pages() > 1 and 386 <= y <= 404:
            if 392 <= x <= 472 and self.login_page > 0:
                return 97
            if 752 <= x <= 832 and self.login_page < self.login_pages() - 1:
                return 98
        if 552 <= x <= 672 and 462 <= y <= 496:
            return 99
        return 0

    def save_summary(self, name):
        """The line under a saved character's name: its level (the average of its Strength and Defence levels,
        rounded down) and when it was last played."""
        path = os.path.join(self.root, "Saves", name + ".ini")
        levels = {k.upper(): max(1, min(self.skill_max_level, int(val(v)))) for k, v in ini.section("Skills", path)}
        level = (levels.get("STRENGTH", 1) + levels.get("DEFENCE", 1)) // 2
        try:
            days = (datetime.date.today() - datetime.date.fromtimestamp(os.path.getmtime(path))).days
        except OSError:
            days = -1
        when = {0: "today", 1: "yesterday"}.get(days, "%d days ago" % days if days > 1 else "")
        text = "Level %d" % level
        return text + ("  -  played " + when if when else "")

    # ----- The character select's look: a blurred picture of where the character last stood behind the panel
    # (Saves\<Name>.png, taken each time the game saves; a meadow for a new character) and their portrait
    def save_snapshot(self):
        """Saves\\<Name>.png: the playfield as it is now, at half size, for the character select's backdrop."""
        try:
            shot = self.screen.subsurface((0, 0, self.view_w, self.view_h))
            small = pygame.transform.smoothscale(shot, (self.view_w // 2, self.view_h // 2))
            pygame.image.save(small, os.path.join(self.root, "Saves", self.player_name + ".png"))
        except (pygame.error, ValueError, OSError):
            pass

    def login_backdrop(self):
        name = self.login_name if self.login_name in self.login_saves else ""
        img = self.login_backdrops.get(name)
        if img is None:
            img = self.login_backdrops[name] = self.make_backdrop(name)
        return img

    def make_backdrop(self, name):
        """The window-sized backdrop: the character's picture (or a meadow) blurred, darker toward the edges."""
        w, h = self.win_w, 768
        pic = None
        path = os.path.join(self.root, "Saves", name + ".png")
        if name and os.path.isfile(path):
            try:
                pic = pygame.image.load(path).convert()
            except pygame.error:
                pic = None
        if pic is None:
            pic = self.meadow()
        pw, ph = pic.get_size()
        s = max(w / pw, h / ph)                      # cover the window, keeping the picture's shape
        pic = pygame.transform.smoothscale(pic, (max(w, round(pw * s)), max(h, round(ph * s))))
        pic = pic.subsurface(((pic.get_width() - w) // 2, (pic.get_height() - h) // 2, w, h)).copy()
        for f in (12, 6):                            # blurred: shrunk a long way and grown back, twice
            pic = pygame.transform.smoothscale(pygame.transform.smoothscale(pic, (w // f, h // f)), (w, h))
        pic.blit(self.vignette(w, h), (0, 0))
        return pic

    @staticmethod
    def vignette(w, h):
        import numpy as np
        xs = (np.arange(w) - w / 2) / (w / 2)
        ys = (np.arange(h) - h / 2) / (h / 2)
        d = np.clip(np.sqrt(xs[:, None] ** 2 + ys[None, :] ** 2) / 1.42, 0, 1)
        v = pygame.Surface((w, h), pygame.SRCALPHA)
        v.fill((14, 8, 6, 255))
        alpha = pygame.surfarray.pixels_alpha(v)
        alpha[:] = (40 + 190 * d ** 1.8).astype(np.uint8)
        del alpha
        return v

    def meadow(self):
        """A little scene of grass, flowers and trees from the tiles, for a character with no picture yet."""
        import random
        rnd = random.Random(7)
        cols, rows = 24, 16
        pic = pygame.Surface((cols * 32, rows * 32)).convert()
        pic.fill((70, 120, 52))
        grass = self.assets.get("Grass001")
        dots = [g for g in (self.assets.get(n) for n in ("Tall_Grass001", "Flowers001", "Flowers002", "Flowers003"))
                if g]
        trees = [g for g in (self.assets.get(n) for n in ("Oak_Tree001", "Pine_Tree001", "Tree001", "Willow_Tree001"))
                 if g]
        for ty in range(rows):
            for tx in range(cols):
                if grass:
                    pic.blit(grass.masked, (tx * 32, ty * 32))
                if dots and rnd.random() < 0.18:
                    pic.blit(rnd.choice(dots).masked, (tx * 32, ty * 32))
        for _ in range(26):
            if trees:
                pic.blit(rnd.choice(trees).masked, (rnd.randrange(cols) * 32, rnd.randrange(rows) * 32))
        return pic

    def login_portrait(self, name):
        """The character as they look, facing you: their sprite with what they wear (from their save)."""
        img = self.login_portraits.get(name)
        if img is not None:
            return img
        base, worn = "Player", []
        if name in self.login_saves:
            path = os.path.join(self.root, "Saves", name + ".ini")
            base = trim(ini.read("Player", "Sprite", "Player", path)) or "Player"
            slots = {s.upper(): i for i, s in enumerate(self.equip_slot_names) if s}
            for key, v in ini.section("Equipment", path):
                i = slots.get(key.strip().upper())
                item = self.renamed(trim(word(v, 1, ",")))
                if i and base == "Player" and self.gear_has_art(item):
                    worn.append((self.gear_rank[i], item))
        sp = self.assets.get(base + "4a") or self.assets.get("Player4a")
        if sp is None:
            return None
        img = sp.masked.copy()
        for _, item in sorted(worn):
            g = self.assets.get("Worn_" + item + "4a")
            if g:
                img.blit(g.masked, (0, 0))
        self.login_portraits[name] = img
        return img

    @staticmethod
    def blit_pixels(surf, img, x, y, scale):
        """A sprite drawn scale times bigger with its pixels kept square (no smoothing), crisp on a Sharp too."""
        k = surf.k if isinstance(surf, Sharp) else 1
        w, h = img.get_size()
        big = pygame.transform.scale(img, (max(1, round(w * scale * k)), max(1, round(h * scale * k))))
        if isinstance(surf, Sharp):
            surf.surf.blit(big, surf.at(x, y))
            surf.dirty = True
        else:
            surf.blit(big, (x, y))

    def present_page(self):
        """Shows the 1024 x 768 page (loading, character select) in the middle of the window."""
        if self.page_backdrop is not None:
            self.screen.blit(self.page_backdrop, (0, 0))
        else:
            self.screen.fill((24, 14, 10))
        if isinstance(self.page, Sharp):
            self.sharp_layers.append((self.page, (self.page_x, 0)))
        else:
            self.screen.blit(self.page, (self.page_x, 0))
        self.present_frame()

    def make_sharp(self, w, h, old=None):
        """A surface for a menu: a Sharp at the screen's resolution when the window is bigger than the game, or a
        plain one. old: the one used last time, kept if it is still the right kind and size."""
        k = self.presenter.k if self.presenter is not None and self.presenter.active else 1.0
        if k > 1.01:
            if isinstance(old, Sharp) and abs(old.k - k) < 1e-6 and old.get_size() == (w, h):
                return old
            return Sharp(w, h, k)
        if (old is not None and not isinstance(old, Sharp) and old.get_size() == (w, h) and
                old.get_flags() & pygame.SRCALPHA):
            return old
        return pygame.Surface((w, h), pygame.SRCALPHA)

    def present_frame(self):
        """The frame on the screen, with the menus drawn on Sharps over it."""
        layers, self.sharp_layers = self.sharp_layers, []
        self.cursors.update(self.cursor_kind, self.frame_clock())
        if self.presenter is not None:
            self.presenter.present(layers)
        else:
            pygame.display.flip()

    def show_layer(self, scr, surf, pos):
        """Puts a menu box on the frame: a Sharp over it (when presented), a plain surface onto it."""
        if isinstance(surf, Sharp):
            self.sharp_layers.append((surf, pos))
        else:
            scr.blit(surf, pos)

    def login_summary(self, name):
        summary = self.login_summaries.get(name)
        if summary is None:
            summary = self.login_summaries[name] = self.save_summary(name)
        return summary

    def draw_login_screen(self):
        self.page = surf = self.make_sharp(1024, 768, self.page)
        self.page_backdrop = self.login_backdrop()
        surf.fill((0, 0, 0, 0))                      # the backdrop shows round the panel
        brown, light, green = (126, 77, 63), (236, 222, 170), (21, 171, 75)
        # The panel, rounded, with a soft shadow under it
        self.round_box(surf, (152, 136, 720, 476), (0, 0, 0, 50), None, 0, 64)
        self.round_box(surf, (158, 144, 708, 462), (0, 0, 0, 90), None, 0, 52)
        self.round_box(surf, (162, 140, 700, 448), brown, DARK, 3, 44)
        self.round_box(surf, (174, 152, 676, 424), PARCHMENT, DARK, 2, 30)
        self.centre_baseline(surf, "Dragon Sword", 202, 30, True, DARK)
        if self.login_saves:
            self.centre_baseline(surf, "Choose your character, or type a new name", 234, 11, True, brown)
        else:
            self.centre_baseline(surf, "Type a name for your new character", 234, 11, True, brown)
        # The chosen character's portrait
        self.round_box(surf, (202, 258, 160, 238), (198, 174, 108), brown, 2, 24)
        self.round_box(surf, (212, 268, 140, 150), (226, 210, 152), None, 0, 20)
        self.round_box(surf, (250, 398, 64, 14), (184, 160, 98), None, 0, 14)      # a shadow at their feet
        known = self.login_name in self.login_saves
        pic = self.login_portrait(self.login_name if known else "")
        if pic is not None:
            self.blit_pixels(surf, pic, 218, 278, 4)
        shown = self.clean_player_name(self.login_name) or "Your hero"
        tw = self.text_width(self.fit_text(shown, 144, 12, True), 12, True)
        self.draw_text_baseline(surf, self.fit_text(shown, 144, 12, True), 282 - int(tw / 2), 442, 12, True, DARK)
        lines = self.login_summary(self.login_name).split("  -  ") if known else ["New character"]
        for n, line in enumerate(lines):
            self.draw_text_baseline(surf, line, 282 - int(self.text_width(line, 8) / 2), 462 + n * 16, 8, False,
                                    (90, 60, 45))
        # The saved characters, each on a rounded card with a little picture of them
        for i, name in enumerate(self.login_page_saves(), 1):
            bx, by = self.login_button_x(i), self.login_button_y(i)
            fill, border = light, brown
            if self.login_hover == i:
                fill = INK
            if self.login_name == name:
                fill, border = (150, 214, 140), green
            self.round_box(surf, (bx, by, self.LOGIN_CARD_W, self.LOGIN_CARD_H), fill, border, 2, 16)
            self.round_box(surf, (bx + 4, by + 2, 32, 32), (212, 196, 140), None, 0, 10)
            pic = self.login_portrait(name)
            if pic is not None:
                self.blit_pixels(surf, pic, bx + 4, by + 2, 1)
            tw = self.LOGIN_CARD_W - 48
            self.draw_text_mid(surf, self.fit_text(name, tw, 10, True), bx + 42, by + 4, 13, 10, True, (51, 34, 27))
            self.draw_text_mid(surf, self.fit_text(self.login_summary(name), tw, 8), bx + 42, by + 20, 10, 8, False,
                               (90, 60, 45))
        if self.login_pages() > 1:
            for hit, x, label, on in ((97, 392, "< Previous", self.login_page > 0),
                                      (98, 752, "Next >", self.login_page < self.login_pages() - 1)):
                fill = INK if self.login_hover == hit else (light if on else PARCHMENT)
                self.round_box(surf, (x, 386, 80, 18), fill, brown, 1, 12)
                lw = self.text_width(label, 8, True)
                self.draw_text_mid(surf, label, x + int((80 - lw) / 2), 386, 18, 8, True, DARK if on else (170, 150, 110))
            text = "Page %d of %d  (%d)" % (self.login_page + 1, self.login_pages(), len(self.login_saves))
            self.draw_text_mid(surf, text, 612 - int(self.text_width(text, 8) / 2), 386, 18, 8, False, DARK)
        # The name and Start
        self.draw_text_baseline(surf, "Name:", 392, 437, 11, True, DARK)
        self.round_box(surf, (450, 416, 382, 30), (250, 244, 220), brown, 2, 14)
        self.draw_text_mid(surf, self.login_name + "_", 460, 416, 30, 12, False, (51, 34, 27))
        fill = green if self.login_hover == 99 else brown
        self.round_box(surf, (552, 462, 120, 34), fill, DARK, 2, 20)
        self.draw_text_mid(surf, "Start", 612 - int(self.text_width("Start", 12, True) / 2), 462, 34, 12, True, INK)
        self.centre_baseline(surf, "Enter = start      Esc = quit      PgUp / PgDn = more characters", 528, 9, False,
                             brown)
        if self.login_note:
            self.centre_baseline(surf, self.login_note, 552, 10, True, (180, 40, 30))

    def login_turn_page(self, step):
        page = min(self.login_pages() - 1, max(0, self.login_page + step))
        if page == self.login_page:
            return False
        self.login_page = page
        return True

    def select_player(self):
        """Character select: click a saved character or type a new name, then Enter (or click Start)."""
        folder = os.path.join(self.root, "Saves")

        def played(name):
            try:
                return os.path.getmtime(os.path.join(folder, name + ".ini"))
            except OSError:
                return 0

        self.login_saves = sorted(self.list_saves(), key=played, reverse=True)
        self.login_summaries = {}
        self.login_portraits = {}
        self.login_backdrops = {}
        self.login_page = 0
        self.login_name = self.login_saves[0] if self.login_saves else ""
        self.login_hover = 0
        self.login_note = ""
        clock = pygame.time.Clock()
        done = False
        changed = True
        pygame.key.start_text_input()
        while not done:
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    self.quit_game(save=False)
                elif ev.type == pygame.KEYDOWN:
                    if ev.key == pygame.K_ESCAPE:
                        self.quit_game(save=False)
                    elif ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        done = True
                    elif ev.key == pygame.K_BACKSPACE and self.login_name:
                        self.login_name = self.login_name[:-1]
                        changed = True
                    elif ev.key == pygame.K_PAGEUP:
                        changed = self.login_turn_page(-1) or changed
                    elif ev.key == pygame.K_PAGEDOWN:
                        changed = self.login_turn_page(1) or changed
                    elif ev.key == pygame.K_F11:
                        pygame.display.toggle_fullscreen()
                elif ev.type == pygame.MOUSEWHEEL:
                    changed = self.login_turn_page(-1 if ev.y > 0 else 1) or changed
                elif ev.type == pygame.TEXTINPUT:
                    for ch in ev.text:
                        if len(self.login_name) >= 20:
                            break
                        if ch.isalnum() and ch.isascii():
                            self.login_name += ch.upper() if self.login_name == "" else ch
                        elif ch == " " and self.login_name:
                            self.login_name += " "
                        elif ch in "-_":
                            self.login_name += ch
                        changed = True
                elif ev.type == pygame.MOUSEMOTION:
                    hover = self.login_button_at(ev.pos[0] - self.page_x, ev.pos[1])
                    if hover != self.login_hover:
                        self.login_hover = hover
                        changed = True
                elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                    self.cursors.click(self.frame_clock())
                    hover = self.login_button_at(ev.pos[0] - self.page_x, ev.pos[1])
                    page = self.login_page_saves()
                    if 1 <= hover <= len(page):
                        if self.login_name == page[hover - 1]:
                            done = True
                        else:
                            self.login_name = page[hover - 1]
                            changed = True
                    if hover == 97:
                        changed = self.login_turn_page(-1) or changed
                    if hover == 98:
                        changed = self.login_turn_page(1) or changed
                    if hover == 99:
                        done = True
            if done and self.clean_player_name(self.login_name) == "":
                done = False
                self.login_note = "Please type a name for your character."
                changed = True
            if changed:
                self.draw_login_screen()
                self.present_page()
                changed = False
            self.cursors.update("pointer", self.frame_clock())
            self.title_music_tick()
            clock.tick(60)
        pygame.key.stop_text_input()
        self.page_backdrop = None
        self.login_backdrops = {}
        self.player_name = self.clean_player_name(self.login_name) or "Player"
        self.log("Player selected: " + self.player_name)

    # =================================================================================================================
    # The quit dialog ("Save and quit?")
    # =================================================================================================================
    def open_quit_dialog(self):
        if self.quit_dialog_open:
            return
        if self.rcm_open:
            self.close_right_click_menu()
        self.stop_player_walk()
        self.quit_dialog_open = True
        self.quit_hover = 0
        self.display_quick_message("", "")
        w, h = 360, 160
        self.quit_x = int((self.view_w - w) / 2)
        self.quit_y = int((self.view_h - h) / 2)

    def close_quit_dialog(self):
        self.quit_dialog_open = False

    def draw_quit_dialog(self, scr):
        w, h = 360, 160
        surf = self.make_sharp(w, h)
        self.round_box(surf, (0, 0, w, h), (51, 34, 27), (126, 77, 63), 3, 16)
        self.draw_text(surf, "Quit Dragon Sword?", 24, 16, 14, True, INK)
        self.draw_text(surf, "Your game will be saved first.", 24, 50, 10, False, PARCHMENT)
        for b, label in enumerate(("Save and Quit", "Options", "Keep Playing"), 1):
            bx, by = 18 + (b - 1) * 112, 86
            fill = (21, 171, 75) if self.quit_hover == b else (126, 77, 63)
            self.round_box(surf, (bx, by, 104, 34), fill, (160, 104, 80), 2, 10)
            self.draw_text_mid(surf, label, bx + int((104 - self.text_width(label, 10, True)) / 2), by, 34, 10, True, INK)
        self.draw_text(surf, "Enter or Y = save and quit    O = options    Esc or N = keep playing", 20, 132, 8, False,
                       (190, 160, 110))
        self.show_layer(scr, surf, (self.quit_x, self.quit_y))

    def update_quit_dialog(self):
        if self.key_hit(pygame.K_ESCAPE) or self.key_hit(pygame.K_n):
            self.close_quit_dialog()
            return
        if self.key_hit(pygame.K_RETURN) or self.key_hit(pygame.K_KP_ENTER) or self.key_hit(pygame.K_y):
            self.quit_confirmed = True
            return
        if self.key_hit(pygame.K_o):
            self.close_quit_dialog()
            self.open_options_dialog()
            return
        hover = 0
        for b in range(1, 4):
            bx = self.quit_x + 18 + (b - 1) * 112
            by = self.quit_y + 86
            if bx <= self.cursor_x <= bx + 104 and by <= self.cursor_y <= by + 34:
                hover = b
        self.quit_hover = hover
        if self.mouse_left_click:
            if hover == 1:
                self.quit_confirmed = True
            elif hover == 2:
                self.close_quit_dialog()
                self.open_options_dialog()
            elif hover == 3:
                self.close_quit_dialog()

    # =================================================================================================================
    # Options: sound, music, ambience, day and night, quest markers, auto-save, font. Saved in Data\Config.ini
    # =================================================================================================================
    OPTIONS_W, OPTIONS_ROW = 420, 34
    # (label, kind): a toggle / cycle row, or a slider (0-100) under the row it belongs to
    OPTION_ROWS = (("Sound effects", "toggle"), ("Volume", "slider"), ("Music", "toggle"), ("Music volume", "slider"),
                   ("Background sounds", "toggle"), ("Background volume", "slider"), ("Day and night", "toggle"),
                   ("Quest markers on the minimap", "toggle"), ("Auto-save", "toggle"), ("Font", "toggle"))
    SLIDERS = {2: "sound_volume", 4: "music_volume", 6: "ambient_volume"}

    def options_h(self):
        return 52 + len(self.OPTION_ROWS) * self.OPTIONS_ROW + 52

    def open_options_dialog(self):
        self.options_open = True
        self.options_hover = 0
        self.options_drag = 0
        self.options_x = int((self.view_w - self.OPTIONS_W) / 2)
        self.options_y = int((self.view_h - self.options_h()) / 2)

    def close_options_dialog(self):
        self.options_open = False

    def option_text(self, i):
        on = lambda v: "On" if v else "Off"
        if i in self.SLIDERS:
            return "%d%%" % getattr(self, self.SLIDERS[i])
        return {1: lambda: on(self.sounds_enabled), 3: lambda: on(self.music_enabled),
                5: lambda: on(self.ambient_enabled), 7: lambda: on(self.day_night_enabled),
                8: lambda: on(self.quest_markers_enabled),
                9: lambda: "Off" if self.autosave_ms <= 0 else "Every %d min" % int(self.autosave_ms / 60000),
                10: lambda: self.ui_font.replace("_", " ")}[i]()

    def slider_track(self):
        """(x1, x2) of the sliders' track, inside the dialog."""
        return 200, self.OPTIONS_W - 80

    def draw_options_dialog(self, scr):
        w, h = self.OPTIONS_W, self.options_h()
        surf = self.make_sharp(w, h)
        self.round_box(surf, (0, 0, w, h), (51, 34, 27), (126, 77, 63), 3, 16)
        self.draw_text(surf, "Options", 24, 14, 14, True, INK)
        self.draw_text(surf, "Click a row to change it; drag a slider. Esc closes.", 112, 22, 8, False, (190, 160, 110))
        for i, (label, kind) in enumerate(self.OPTION_ROWS, 1):
            ry = 52 + (i - 1) * self.OPTIONS_ROW
            fill = (96, 62, 50) if self.options_hover == i else (61, 40, 31)
            indent = 14 if kind == "slider" else 0
            self.round_box(surf, (20 + indent, ry, w - 40 - indent, 30), fill, (126, 77, 63), 1, 8)
            self.draw_text_mid(surf, label, 34 + indent, ry, 30, 10, False, INK)
            value = self.option_text(i)
            if kind == "slider":
                x1, x2 = self.slider_track()
                v = getattr(self, self.SLIDERS[i]) / 100
                ty = ry + 15
                self.round_box(surf, (x1, ty - 3, x2 - x1, 6), (30, 20, 16), None, 0, 3)
                if v > 0:
                    self.round_box(surf, (x1, ty - 3, max(6, int((x2 - x1) * v)), 6), (226, 176, 74), None, 0, 3)
                kx = x1 + int((x2 - x1) * v)
                self.round_box(surf, (kx - 7, ty - 8, 14, 16), (250, 226, 160), (120, 82, 30), 1, 7)
                self.draw_text_mid(surf, value, x2 + 12, ry, 30, 9, True, INK)
                continue
            pill = self.text_width(value, 10, True) + 20
            pc = (110, 60, 50) if value == "Off" else (21, 140, 65)
            self.round_box(surf, (w - 30 - pill, ry + 4, pill, 22), pc, None, 0, 10)
            self.draw_text_mid(surf, value, w - 20 - pill, ry + 4, 22, 10, True, INK)
        by = h - 44
        fill = (21, 171, 75) if self.options_hover == 99 else (126, 77, 63)
        self.round_box(surf, (int(w / 2) - 55, by, 110, 32), fill, (160, 104, 80), 2, 10)
        self.draw_text_mid(surf, "Done", int(w / 2 - self.text_width("Done", 10, True) / 2), by, 32, 10, True, INK)
        self.show_layer(scr, surf, (self.options_x, self.options_y))

    def set_slider(self, i, value):
        value = int(round(max(0, min(100, value)) / 5) * 5)
        attr = self.SLIDERS[i]
        if getattr(self, attr) == value:
            return
        setattr(self, attr, value)
        key = {"sound_volume": "Volume", "music_volume": "Music.Volume", "ambient_volume": "Ambient.Volume"}[attr]
        ini.write("Sounds", key, lbstr(value), self.config_path)
        self.apply_volume()

    def update_options_dialog(self):
        if self.key_hit(pygame.K_ESCAPE) or self.key_hit(pygame.K_RETURN) or self.key_hit(pygame.K_KP_ENTER):
            self.close_options_dialog()
            return
        w, h = self.OPTIONS_W, self.options_h()
        lx, ly = self.cursor_x - self.options_x, self.cursor_y - self.options_y
        hover = 0
        for i in range(1, len(self.OPTION_ROWS) + 1):
            ry = 52 + (i - 1) * self.OPTIONS_ROW
            if 20 <= lx <= w - 20 and ry <= ly <= ry + 30:
                hover = i
        if w / 2 - 55 <= lx <= w / 2 + 55 and h - 44 <= ly <= h - 12:
            hover = 99
        self.options_hover = hover
        x1, x2 = self.slider_track()
        held = pygame.mouse.get_pressed()[0]
        if self.options_drag and held:             # dragging a slider
            self.set_slider(self.options_drag, (lx - x1) * 100 / (x2 - x1))
            return
        if self.options_drag and not held:
            self.options_drag = 0
            if self.sounds_enabled:
                self.play_sound("Coins")           # (how loud the effects are now)
        if hover in self.SLIDERS:
            for k, d in ((pygame.K_LEFT, -5), (pygame.K_RIGHT, 5)):
                if self.key_hit(k):
                    self.set_slider(hover, getattr(self, self.SLIDERS[hover]) + d)
        if self.mouse_left_click:
            if hover == 99:
                self.close_options_dialog()
                return
            if hover in self.SLIDERS:
                self.options_drag = hover
                self.set_slider(hover, (lx - x1) * 100 / (x2 - x1))
            elif hover >= 1:
                self.change_option(hover)

    def change_option(self, i):
        cfg = self.config_path
        if i == 1:
            self.sounds_enabled = 0 if self.sounds_enabled else 1
            ini.write("Sounds", "Enabled", lbstr(self.sounds_enabled), cfg)
            if self.sounds_enabled:
                self.start_music()
            else:
                self.stop_music()
            self.ambient_update()
        elif i == 3:
            self.music_enabled = 0 if self.music_enabled else 1
            ini.write("Sounds", "Music.On", lbstr(self.music_enabled), cfg)
            if self.music_enabled:
                self.start_music()
            else:
                self.stop_music()
        elif i == 5:
            self.ambient_enabled = 0 if self.ambient_enabled else 1
            ini.write("Sounds", "Ambient", lbstr(self.ambient_enabled), cfg)
            self.ambient_update()
        elif i == 7:
            self.day_night_enabled = 0 if self.day_night_enabled else 1
            ini.write("Gameplay", "DayNight", lbstr(self.day_night_enabled), cfg)
            self.day_night_update()
        elif i == 8:
            self.quest_markers_enabled = 0 if self.quest_markers_enabled else 1
            ini.write("Gameplay", "QuestMarkers", lbstr(self.quest_markers_enabled), cfg)
            self.minimap_last = ""
        elif i == 9:
            minutes = {0: 1, 1: 3, 3: 5, 5: 10}.get(int(self.autosave_ms / 60000), 0)
            self.autosave_ms = 60000 * minutes
            ini.write("Gameplay", "AutoSave.Minutes", lbstr(minutes), cfg)
        elif i == 10:
            fonts = ["Palatino_Linotype", "Georgia", "Book_Antiqua", "Constantia", "Segoe_UI", "Lucida_Sans_Unicode"]
            k = next((n for n, f in enumerate(fonts) if f.lower() == self.ui_font.lower()), -1)
            self.ui_font = fonts[(k + 1) % len(fonts)]
            self.assets.font_name = self.ui_font.replace("_", " ")
            self.icon_cache = {}
            ini.write("Interface", "Font", self.ui_font.replace("_", " "), cfg)
            self.chat_dirty = True
            self.stats_dirty = True
            self.qm_message = None

    # =================================================================================================================
    # Quest markers on the minimap (Quests.ini Marker<N>=<place ID> or <map> <tile x> <tile y>, several split by ;)
    # =================================================================================================================
    @staticmethod
    def help_clean(value):
        """Names and numbers: anything after a ; is a comment."""
        p = value.find(";")
        if p >= 0:
            value = value[:p]
        value = trim(value)
        if value.lower() == "none" or value == "-":
            value = ""
        return value

    @staticmethod
    def help_text(value):
        """Free text may contain ; so only a ; after two spaces counts as a comment."""
        p = value.find("  ;")
        if p >= 0:
            value = value[:p]
        return trim(value)

    def help_read_ini(self, file):
        """[(section, {UPPER key: value})] for a whole data file (first of each key)."""
        out = []
        for name, items in ini.sections(os.path.join(self.root, file)):
            d = {}
            for k, v in items:
                d.setdefault(k.upper(), v.replace("\t", " "))
            out.append((name, d))
        return out

    def quest_markers_refresh(self):
        self.qmarks = []
        for name, d in self.help_read_ini(os.path.join("Data", "Quests.ini")):
            attribute = self.help_clean(d.get("ATTRIBUTE", ""))
            done = val(self.help_clean(d.get("DONE", "")))
            value = val(self.get_attribute(attribute)) if attribute else 0
            if value > 0 and (done == 0 or value < done):
                marks = self.help_text(d.get("MARKER" + lbstr(int(value)), ""))     # (; separates markers)
                for part in marks.split(";"):
                    mark = self.place_marker(part) if trim(part) else None    # "<map> <x> <y>" or a place ID
                    if mark and len(self.qmarks) < 40:
                        self.qmarks.append(mark)
        self.minimap_last = ""

    # =================================================================================================================
    # The journal (H, F1 or the ? Help button). Tabs: Crafting, Gathering, Quests, Controls. The game is paused
    # =================================================================================================================
    def open_help(self):
        if self.help_open or self.loading_active:
            return
        if self.rcm_open:
            self.close_right_click_menu()
        self.help_load_data()
        if self.help_tab < 1 or self.help_tab > 4:
            self.help_tab = 1
        self.help_page = 1
        self.help_focus_quest = ""
        self.help_hover = 0
        self.help_open = True
        self.help_dirty = True

    def close_help(self):
        self.help_open = False

    def help_update(self):
        if self.key_hit(pygame.K_ESCAPE) or self.key_hit(pygame.K_h) or self.key_hit(pygame.K_F1):
            self.close_help()
            return
        new_tab, new_page = self.help_tab, self.help_page
        for k in range(1, 5):
            if self.key_hit(getattr(pygame, "K_%d" % k)) or self.key_hit(getattr(pygame, "K_KP%d" % k)):
                new_tab = k
        if self.key_hit(pygame.K_LEFT):
            new_tab = self.help_tab - 1
        if self.key_hit(pygame.K_RIGHT):
            new_tab = self.help_tab + 1
        if new_tab < 1:
            new_tab = 4
        if new_tab > 4:
            new_tab = 1
        if self.key_hit(pygame.K_UP) or self.key_hit(pygame.K_PAGEUP):
            new_page = self.help_page - 1
        if self.key_hit(pygame.K_DOWN) or self.key_hit(pygame.K_PAGEDOWN):
            new_page = self.help_page + 1
        hover = self.help_hit(self.cursor_x - self.page_x, self.cursor_y)
        if self.mouse_left_click:
            if hover == 10:
                self.close_help()
                return
            if 1 <= hover <= 4:
                new_tab = hover
            if hover == 11:
                new_page = self.help_page - 1
            if hover == 12:
                new_page = self.help_page + 1
        if new_tab != self.help_tab:
            self.help_tab = new_tab
            self.help_focus_quest = ""
            new_page = 1
            self.help_dirty = True
        new_page = min(max(1, new_page), self.help_pages())
        if new_page != self.help_page:
            self.help_page = new_page
            self.help_dirty = True
        if hover != self.help_hover:
            self.help_hover = hover
            self.help_dirty = True

    def help_hit(self, x, y):
        for t in range(1, 5):
            tx = self.help_tab_x(t)
            if tx <= x <= tx + 152 and 60 <= y <= 92:
                return t
        if 942 <= x <= 982 and 20 <= y <= 48:
            return 10
        if 40 <= x <= 160 and 696 <= y <= 724:
            return 11
        if 864 <= x <= 984 and 696 <= y <= 724:
            return 12
        if self.help_tab == 3 and 48 <= x <= 976:     # a quest card: 100 + its place on the page
            n = int((y - 108) / 82)
            if 0 <= n < 7 and y - 108 - n * 82 <= 76 and (self.help_page - 1) * 7 + n < len(self.help_quests):
                return 100 + n
        return 0

    @staticmethod
    def help_tab_x(t):
        return 40 + (t - 1) * 160

    def help_page_size(self):
        return {1: 14, 2: 7, 3: 7}.get(self.help_tab, 1)

    def help_tab_count(self):
        return {1: len(self.help_crafts), 2: len(self.help_gathers), 3: len(self.help_quests)}.get(self.help_tab, 1)

    def help_pages(self):
        per = self.help_page_size()
        return max(1, int((self.help_tab_count() + per - 1) / per))

    def help_load_data(self):
        self.help_load_crafting()
        self.help_load_gathering()
        self.help_load_quests()

    def help_level_short(self, skill, level):
        return bool(skill) and level > 0 and self.skill_level(skill) < level

    def help_has_ingredients(self, ingredients):
        j = 1
        ok = True
        while word(ingredients, j) != "":
            if self.items_held(word(ingredients, j)) < max(1, val(word(ingredients, j + 1))):
                ok = False
            j += 2
        return ok

    def help_load_crafting(self):
        """Every recipe of every crafting rack (status 0 = can make, 1 = missing items, 2 = level too low)."""
        self.help_crafts = []
        for rack, d in self.help_read_ini(os.path.join("Data", "ItemRacks.ini")):
            rtype = self.help_clean(d.get("TYPE", "")).upper()
            is_craft = rack.upper().startswith("CRAFT-") or rtype in ("CRAFT", "CRAFTING", "CREATABLES")
            if rtype in ("SHOP", "GENERAL", "SPECIFIC", "BANK"):
                is_craft = False
            if not is_craft:
                continue
            skill = self.help_clean(d.get("SKILL", ""))
            name = rack[6:] if rack.upper().startswith("CRAFT-") else rack
            name = trim(name.replace("_", " "))
            for n in range(1, 201):
                item = self.help_clean(d.get("ITEM%d" % n, ""))
                if item == "":
                    break
                product = trim(word(item, 1, ","))
                if product and len(self.help_crafts) < 300:
                    ingredients = trim(word(item, 2, ","))
                    level = val(word(item, 4, ","))
                    status = 0
                    if not self.help_has_ingredients(ingredients):
                        status = 1
                    if self.help_level_short(skill, level):
                        status = 2
                    self.help_crafts.append({"product": product, "ingredients": ingredients,
                                             "xp": trim(word(item, 3, ",")), "level": level, "skill": skill,
                                             "rack": name, "status": status})
        self.help_craft_order = [i for s in (0, 1, 2) for i, c in enumerate(self.help_crafts) if c["status"] == s]
        self.help_craft_ready = sum(1 for c in self.help_crafts if c["status"] == 0)

    def help_tool_held(self, alts):
        """A Tool= word: one item, or alternatives "Bronze_Pickaxe/Pickaxe/Steel_Pickaxe". The best one held, or ""."""
        items = [a for a in alts.split("/") if a][:20]
        for it in reversed(items):
            if self.items_held(it) > 0:
                return it
        return ""

    def help_load_gathering(self):
        self.help_gathers = []
        for name, d in self.help_read_ini(os.path.join("Data", "Gathering.ini")):
            gives = self.help_clean(d.get("GIVES", ""))
            source = self.help_clean(d.get("SOURCE", ""))
            verb = self.help_clean(d.get("VERB", ""))
            if (gives or source or verb) and len(self.help_gathers) < 300:
                tool = self.help_clean(d.get("TOOL", ""))
                skill = self.help_clean(d.get("SKILL", ""))
                level = val(self.help_clean(d.get("LEVEL", "")))
                missing = ""
                for t in tool.split():
                    if missing == "" and self.help_tool_held(t) == "":
                        missing = word(t, 1, "/")
                status = 0
                if missing:
                    status = 1
                if self.help_level_short(skill, level):
                    status = 2
                self.help_gathers.append({"title": name, "gives": gives, "source": source, "verb": verb, "tool": tool,
                                          "skill": skill, "level": level, "xp": self.help_clean(d.get("XP", "")),
                                          "where": self.help_text(d.get("WHERE", "")), "status": status,
                                          "missing": missing})
        self.help_gather_order = [i for s in (0, 1, 2) for i, g in enumerate(self.help_gathers) if g["status"] == s]
        self.help_gather_ready = sum(1 for g in self.help_gathers if g["status"] == 0)

    def help_load_quests(self):
        """Every quest in Data\\Quests.ini (status 0 = in progress, 1 = not started, 2 = complete)."""
        self.help_quests = []
        self.help_quest_active = self.help_quest_done = 0
        for name, d in self.help_read_ini(os.path.join("Data", "Quests.ini")):
            attribute = self.help_clean(d.get("ATTRIBUTE", ""))
            done = val(self.help_clean(d.get("DONE", "")))
            value = val(self.get_attribute(attribute)) if attribute else 0
            status = -1
            text = ""
            if done > 0 and value >= done:
                status = 2
                text = "You have finished this quest."
            elif value <= 0:
                text = self.help_text(d.get("STAGE0", ""))
                if text:
                    status = 1
            else:
                text = self.help_text(d.get("STAGE" + lbstr(int(value)), "")) or "In progress."
                status = 0
            notes = [(t, done_) for q, done_, t in getattr(self, "quest_notes", []) if q == name]
            if status < 0 and notes:            # not listed until started, but a script has written about it
                status, text = 0, next((t for t, done_ in reversed(notes) if not done_), "In progress.")
            # the steps so far: each StageN it has passed crossed out, the one it is at not (none beyond: no spoilers)
            steps = []
            last = int(done) if status == 2 else max(0, int(value))
            for n in range(0, last + 1):
                t = self.help_text(d.get("STAGE%d" % n, ""))
                if t:
                    steps.append((self.help_attributes(t), 1 if status == 2 or n < value else 0))
            if status >= 0 and len(self.help_quests) < 300:
                if status == 0:
                    self.help_quest_active += 1
                if status == 2:
                    self.help_quest_done += 1
                main = self.help_clean(d.get("TYPE", "")).lower() == "main"
                needs = self.quest_needs(name) if status == 1 else []      # (quests.py: what it needs to start)
                self.help_quests.append({"title": name, "giver": self.help_clean(d.get("GIVER", "")),
                                         "status": status, "text": self.help_attributes(text),
                                         "steps": steps, "notes": [(self.help_attributes(t), x) for t, x in notes],
                                         "main": main, "chapter": val(self.help_clean(d.get("CHAPTER", "0"))),
                                         "needs": needs})
        self.quest_popup = None
        # in progress, then not started (all the ones you can start before any locked one), then done; the main
        # story first in each, in chapter order
        order = lambda i: (bool(self.help_quests[i]["needs"]), not self.help_quests[i]["main"],
                           self.help_quests[i]["chapter"] if self.help_quests[i]["main"] else 0)
        self.help_quest_order = [i for s in (0, 1, 2) for i in sorted(
            (i for i, q in enumerate(self.help_quests) if q["status"] == s), key=order)]

    def help_attributes(self, text):
        """$Name in quest text -> the value of the attribute Name."""
        ok = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_."
        out = []
        i = 0
        while i < len(text):
            c = text[i]
            if c == "$":
                j = i + 1
                while j < len(text) and text[j] in ok:
                    j += 1
                nm = text[i + 1:j]
                while nm.endswith("."):
                    nm = nm[:-1]
                    j -= 1
                if nm == "":
                    out.append("$")
                    i += 1
                else:
                    out.append(self.get_attribute(nm))
                    i = j
            else:
                out.append(c)
                i += 1
        return "".join(out)

    @staticmethod
    def help_name_list(names):
        out = []
        for n in names.split():
            p = pretty(n)
            if p not in out:
                out.append(p)
        return ", ".join(out)

    # ----- Drawing the journal
    def help_draw(self):
        self.help_surface = surf = self.make_sharp(1024, 768, self.help_surface)
        pages = self.help_pages()
        self.help_page = min(max(1, self.help_page), pages)
        surf.fill((24, 14, 10))
        self.round_box(surf, (20, 12, 984, 744), (51, 34, 27), (126, 77, 63), 3, 18)
        self.draw_text(surf, "Journal", 44, 18, 16, True, INK)
        tw = self.text_width("Journal", 16, True)
        self.draw_text(surf, self.fit_text(self.player_name + "  -  what you can make, gather and do", 860 - tw, 9),
                       58 + tw, 30, 9, False, PARCHMENT)
        self.help_button(surf, 942, 20, 40, 28, "X", 2 if self.help_hover == 10 else 1)
        for t in range(1, 5):
            label = {1: "Crafting (%d)" % len(self.help_crafts), 2: "Gathering (%d)" % len(self.help_gathers),
                     3: "Quests (%d)" % len(self.help_quests)}.get(t, "Controls")
            state = 1
            if self.help_hover == t:
                state = 2
            if self.help_tab == t:
                state = 3
            self.help_button(surf, self.help_tab_x(t), 60, 152, 32, label, state)
        self.round_box(surf, (36, 98, 952, 590), (40, 26, 20), (126, 77, 63), 2, 12)
        if self.help_tab == 1:
            self.help_draw_crafting(surf)
        elif self.help_tab == 2:
            self.help_draw_gathering(surf)
        elif self.help_tab == 3:
            self.help_draw_quests(surf)
        else:
            self.help_draw_controls(surf)
        state = 1 if self.help_page > 1 else 0
        if state == 1 and self.help_hover == 11:
            state = 2
        self.help_button(surf, 40, 696, 120, 28, "< Previous", state)
        state = 1 if self.help_page < pages else 0
        if state == 1 and self.help_hover == 12:
            state = 2
        self.help_button(surf, 864, 696, 120, 28, "Next >", state)
        if self.help_tab == 1:
            info = "%d of %d recipes ready to make" % (self.help_craft_ready, len(self.help_crafts))
        elif self.help_tab == 2:
            info = "%d of %d you can gather now" % (self.help_gather_ready, len(self.help_gathers))
        elif self.help_tab == 3:
            info = "%d/%d complete" % (self.help_quest_done, len(self.help_quests))
        else:
            info = "The game is paused while the journal is open"
        if pages > 1:
            info = "Page %d of %d     %s" % (self.help_page, pages, info)
        self.centre_text(surf, 512, 700, info, 10, True, INK)
        self.centre_text(surf, 512, 730, "H, F1 or Esc: close      1-4 or Left/Right: tabs      Up/Down or PgUp/PgDn: "
                                         "pages", 9, False, (190, 160, 110))
        self.help_dirty = False

    def help_button(self, surf, x, y, w, h, label, state):
        """state 0 = disabled, 1 = normal, 2 = under the mouse, 3 = selected tab"""
        fill, border, ink = {0: ((51, 34, 27), (77, 43, 33), (110, 90, 70)),
                             2: ((92, 60, 46), (160, 104, 80), INK),
                             3: ((126, 77, 63), (190, 140, 100), (255, 255, 255))}.get(
            state, ((64, 42, 33), (126, 77, 63), PARCHMENT))
        self.round_box(surf, (x, y, w, h), fill, border, 2, 10)
        label = self.fit_text(label, w - 12, 10, True)
        lw = self.text_width(label, 10, True)
        fh = self.font(10, True).get_height()
        self.draw_text(surf, label, x + int((w - lw) / 2), y + int((h - fh) / 2), 10, True, ink)

    def help_wrap(self, surf, x, y, w, text, col, line_h, max_lines, size=9, bold=False):
        """Word-wrapped text, at most max_lines lines. Returns the lines used."""
        words = text.split()
        line = ""
        lines = 0
        k = 0
        while k < len(words) and lines < max_lines:
            attempt = trim(line + " " + words[k])
            if self.text_width(attempt, size, bold) > w and line != "":
                if lines == max_lines - 1:
                    line = trim(" ".join([line] + words[k:]))
                    k = len(words)
                    break
                self.draw_text(surf, line, x, y + lines * line_h, size, bold, col)
                lines += 1
                line = words[k]
            else:
                line = attempt
            k += 1
        if line and lines < max_lines:
            self.draw_text(surf, self.fit_text(line, w, size, bold), x, y + lines * line_h, size, bold, col)
            lines += 1
        return lines

    def help_line_start(self, x, edge):
        self.help_pen_x = x
        self.help_line_right = edge
        self.help_line_full = False

    def help_run(self, surf, text, col, y, size=9, bold=False):
        if self.help_line_full or not text:
            return
        if self.help_pen_x + self.text_width(text, size, bold) > self.help_line_right:
            text = self.fit_text(text, self.help_line_right - self.help_pen_x, size, bold)
            self.help_line_full = True
            if not text:
                return
        self.draw_text(surf, text, self.help_pen_x, y, size, bold, col)
        self.help_pen_x += self.text_width(text, size, bold)

    def help_icon_run(self, surf, item, y, size):
        if self.help_line_full or not self.assets.loaded(item):
            return
        if self.help_pen_x + size > self.help_line_right:
            self.help_line_full = True
            return
        self.draw_icon(surf, item, self.help_pen_x, y, size)
        self.help_pen_x += size + 3

    def help_card(self, surf, x, y, w, h, border):
        if border is None:
            self.round_box(surf, (x, y, w, h), (61, 40, 31), (92, 60, 46), 1, 10)
        else:
            self.round_box(surf, (x, y, w, h), (61, 40, 31), border, 2, 10)

    def help_icon_well(self, surf, x, y, item):
        self.round_box(surf, (x + 10, y + 10, 36, 36), (40, 26, 20), (92, 60, 46), 1, 8)
        if self.assets.loaded(item) or (item and self.assets.load_if_exists("Entities", item)):
            self.draw_icon(surf, item, x + 12, y + 12, 32)
        else:
            self.centre_text(surf, x + 28, y + 18, "?", 12, True, (110, 90, 70))

    def help_badge(self, surf, edge, y, text, col, lock=False):
        pad = 13 if lock else 0
        w = self.text_width(text, 9, True) + 16 + pad
        self.round_box(surf, (edge - w, y, w, 18), (40, 26, 20), col, 1, 9)
        fh = self.font(9, True).get_height()
        if lock:
            self.draw_padlock(surf, edge - w + 12, y + 8, col)
        self.draw_text(surf, text, edge - w + 8 + pad, y + int((18 - fh) / 2), 9, True, col)
        return w

    def help_empty(self, surf, heading, text):
        self.centre_text(surf, 512, 330, heading, 14, True, INK)
        self.centre_text(surf, 512, 366, text, 9, False, (190, 160, 110))

    def help_draw_crafting(self, surf):
        if not self.help_crafts:
            self.help_empty(surf, "Nothing to make yet.",
                            "Recipes show up here when there are crafting lists (the CRAFT- sections of "
                            "Data\\ItemRacks.ini).")
            return
        first = (self.help_page - 1) * 14
        for slot, k in enumerate(range(first, min(len(self.help_crafts), first + 14))):
            self.help_draw_recipe(surf, self.help_crafts[self.help_craft_order[k]], 48 + (slot % 2) * 466,
                                  108 + int(slot / 2) * 82, 462)

    def help_draw_recipe(self, surf, c, x, y, w):
        status = c["status"]
        if status == 0:
            border, badge, bc = (21, 171, 75), "Can make now", (120, 210, 110)
        elif status == 1:
            border, badge, bc = None, "Missing items", (235, 160, 80)
        else:
            border, badge, bc = None, "Need level " + lbstr(c["level"]), (235, 105, 85)
        self.help_card(surf, x, y, w, 76, border)
        self.help_icon_well(surf, x, y, c["product"])
        bw = self.help_badge(surf, x + w - 10, y + 8, badge, bc)
        self.draw_text(surf, self.fit_text(pretty(c["product"]), w - 76 - bw, 10, True), x + 56, y + 6, 10, True, INK)
        self.help_line_start(x + 56, x + w - 10)
        self.help_run(surf, "Needs: ", (190, 160, 110), y + 26)
        ingredients = c["ingredients"]
        if word(ingredients, 1) == "":
            self.help_run(surf, "nothing", PARCHMENT, y + 26)
        j = 1
        while word(ingredients, j) != "":
            nm = word(ingredients, j)
            need = max(1, val(word(ingredients, j + 1)))
            have = self.items_held(nm)
            col = (120, 210, 110) if have >= need else (235, 105, 85)
            if j > 1:
                self.help_run(surf, ",  ", (190, 160, 110), y + 26)
            self.help_icon_run(surf, nm, y + 25, 16)
            self.help_run(surf, "%s %d/%s" % (pretty(nm), have, lbstr(need)), col, y + 26)
            j += 2
        self.help_line_start(x + 56, x + w - 10)
        self.help_draw_skill_need(surf, c["skill"], c["level"], c["xp"], y + 42)
        self.help_line_start(x + 56, x + w - 10)
        self.help_run(surf, "Made at: ", (190, 160, 110), y + 58)
        self.help_run(surf, c["rack"] + " (crafting list)", PARCHMENT, y + 58)

    def help_draw_skill_need(self, surf, skill, level, xp, y):
        self.help_run(surf, "Skill: ", (190, 160, 110), y)
        if skill == "":
            self.help_run(surf, "none", PARCHMENT, y)
        else:
            if level > 0:
                col = (235, 105, 85) if self.help_level_short(skill, level) else (120, 210, 110)
                self.help_run(surf, "%s level %s" % (skill, lbstr(level)), col, y)
            else:
                self.help_run(surf, skill + " (any level)", PARCHMENT, y)
            if self.skill_index(skill) > 0:
                self.help_run(surf, "  (yours: %d)" % self.skill_level(skill), (190, 160, 110), y)
        if val(xp) != 0:
            self.help_run(surf, "     +%s XP" % xp, PARCHMENT, y)

    def help_draw_gathering(self, surf):
        if not self.help_gathers:
            self.help_empty(surf, "Nothing to gather yet.", "Things you can gather show up here (Data\\Gathering.ini).")
            return
        first = (self.help_page - 1) * 7
        for n, k in enumerate(range(first, min(len(self.help_gathers), first + 7))):
            self.help_draw_gather_card(surf, self.help_gathers[self.help_gather_order[k]], 48, 108 + n * 82, 928)

    def help_draw_gather_card(self, surf, g, x, y, w):
        status = g["status"]
        if status == 0:
            border, badge, bc = (21, 171, 75), "Can gather now", (120, 210, 110)
        elif status == 1:
            border, badge, bc = None, "Need " + pretty(g["missing"]), (235, 160, 80)
        else:
            border, badge, bc = None, "Need level " + lbstr(g["level"]), (235, 105, 85)
        self.help_card(surf, x, y, w, 76, border)
        self.help_icon_well(surf, x, y, word(g["gives"], 1))
        bw = self.help_badge(surf, x + w - 10, y + 8, badge, bc)
        self.draw_text(surf, self.fit_text(g["title"], w - 76 - bw, 10, True), x + 56, y + 6, 10, True, INK)
        self.help_line_start(x + 56, x + w - 10)
        self.help_run(surf, "Gives: ", (190, 160, 110), y + 26)
        if g["gives"] == "":
            self.help_run(surf, "-", PARCHMENT, y + 26)
        for k, it in enumerate(g["gives"].split()):
            if k > 0:
                self.help_run(surf, ",  ", (190, 160, 110), y + 26)
            self.help_icon_run(surf, it, y + 25, 16)
            self.help_run(surf, pretty(it), (250, 240, 210), y + 26)
        if g["source"] or g["verb"]:
            verb = g["verb"] or "From"
            self.help_run(surf, "          " + verb + ": ", (190, 160, 110), y + 26)
            self.help_run(surf, self.help_name_list(g["source"]) or "-", PARCHMENT, y + 26)
        self.help_line_start(x + 56, x + w - 10)
        self.help_run(surf, "Tool: ", (190, 160, 110), y + 42)
        if g["tool"] == "":
            self.help_run(surf, "none", PARCHMENT, y + 42)
        for k, alts in enumerate(g["tool"].split()):
            if k > 0:
                self.help_run(surf, " and ", (190, 160, 110), y + 42)
            held = self.help_tool_held(alts)
            first = word(alts, 1, "/")
            if held:
                self.help_icon_run(surf, held, y + 41, 16)
                self.help_run(surf, pretty(held) + " (you have one)", (120, 210, 110), y + 42)
            else:
                self.help_icon_run(surf, first, y + 41, 16)
                if "/" in alts:
                    first += " or better"
                self.help_run(surf, pretty(first) + " (you need one)", (235, 105, 85), y + 42)
        self.help_run(surf, "          ", (190, 160, 110), y + 42)
        self.help_draw_skill_need(surf, g["skill"], g["level"], g["xp"], y + 42)
        self.help_line_start(x + 56, x + w - 10)
        self.help_run(surf, "Where: ", (190, 160, 110), y + 58)
        self.help_run(surf, g["where"] or "-", PARCHMENT, y + 58)

    def help_draw_quests(self, surf):
        if not self.help_quests:
            self.help_empty(surf, "No quests yet.", "Talk to the people you meet: quests you hear about are listed here.")
            return
        first = (self.help_page - 1) * 7
        for n, k in enumerate(range(first, min(len(self.help_quests), first + 7))):
            self.help_draw_quest_card(surf, self.help_quests[self.help_quest_order[k]], 48, 108 + n * 82, 928)
        n = self.help_hover - 100
        if 0 <= n < 7 and first + n < len(self.help_quests):   # the card pointed at: its checklist, under it (or over)
            q = self.help_quests[self.help_quest_order[first + n]]
            w, h = self.quest_popup_size(q, 380)
            top = 108 + n * 82
            y = top + 70 if top + 70 + h <= 740 else max(20, top + 6 - h)
            self.draw_quest_popup(surf, q, 976 - 380 - 16, y, 380)

    def help_draw_quest_card(self, surf, q, x, y, w):
        status = q["status"]
        sc, badge = self.quest_look(q)                    # the title, badge and border in the status's colour
        if status == 0:
            border, bc, tc = (200, 150, 60), sc, (250, 240, 210)
        elif status == 1 and q.get("needs"):
            border, bc, tc = None, sc, (150, 132, 114)
        elif status == 1:
            border, bc, tc = sc, sc, (220, 210, 180)
        else:
            border, bc, tc = (21, 171, 75), sc, (150, 140, 120)
        if q["title"] == getattr(self, "help_focus_quest", ""):      # the quest clicked in the sidebar
            self.round_box(surf, (x - 4, y - 4, w + 8, 84), None, (255, 214, 90), 2, 13)
            self.round_box(surf, (x, y, w, 76), (92, 66, 40), (255, 214, 90), 2, 10)
        else:
            self.help_card(surf, x, y, w, 76, border)
        bw = self.help_badge(surf, x + w - 10, y + 8, badge, bc, lock=bool(q.get("needs")))
        if q.get("main"):                               # the main story: a gold badge beside the status
            label = "Main story" + (" %d" % q["chapter"] if q.get("chapter") else "")
            bw += 8 + self.help_badge(surf, x + w - 18 - bw, y + 8, label, (240, 200, 90))
        tw = self.draw_text(surf, self.fit_text(q["title"], w - 36 - bw, 10, True), x + 16, y + 6, 10, True, sc)
        if status == 2:                                  # done: crossed out
            cap_top, cap_h = self.cap_metrics(10, True)
            my = y + 6 + cap_top + int(cap_h / 2) + 1
            self.sharp_line(surf, (x + 15, my), (x + 17 + tw, my), (90, 150, 80))
        ty = y + 26
        if q["giver"]:
            self.help_line_start(x + 16, x + w - 16)
            self.help_run(surf, "Given by: ", (190, 160, 110), y + 26)
            self.help_run(surf, pretty(q["giver"]), PARCHMENT, y + 26)
            ty = y + 42
        text = q["text"]
        if q.get("needs"):                              # locked: what it needs, on a line of its own
            ty += 15 * self.help_wrap(surf, x + 16, ty, w - 32, self.quest_needs_text(q), self.QUEST_LOCKED_NEEDS, 15,
                                      1, 9, True)
        elif status == 1:
            text = "You can start this now. " + text
        if y + 74 - ty >= 15:
            self.help_wrap(surf, x + 16, ty, w - 32, text, tc, 15, int((y + 74 - ty) / 15))
        todo = sum(1 for _, done in q.get("notes", []) if not done)
        if todo and status != 2:                     # the notes still to do, beside the status badge
            self.help_badge(surf, x + w - 18 - bw, y + 8, "%d to do" % todo, (255, 214, 90))

    # ----- The quest checklist: shown while a quest is pointed at (the sidebar's Quests tab, the journal's cards)
    QUEST_COLOURS = {0: (255, 214, 90), 1: (160, 140, 118), 2: (120, 205, 105)}    # in progress, not started, done
    QUEST_STATUS = {0: "In progress", 1: "Not started", 2: "Complete"}
    QUEST_READY = (110, 200, 235)           # not started, and nothing stops you: blue
    QUEST_LOCKED = (150, 110, 100)          # not started, and it needs something first (a level, a quest): dull red
    QUEST_LOCKED_NEEDS = (225, 140, 115)

    def quest_look(self, q):
        """(colour, label) for a quest's status: In progress, Can start, Locked or Complete."""
        if q["status"] == 1:
            return (self.QUEST_LOCKED, "Locked") if q.get("needs") else (self.QUEST_READY, "Can start")
        return self.QUEST_COLOURS.get(q["status"], PARCHMENT), self.QUEST_STATUS.get(q["status"], "")

    def quest_needs_text(self, q):
        return "Locked until you have: " + ", ".join(q["needs"]) + "."

    def draw_padlock(self, surf, cx, cy, col):
        """A small padlock centred on cx,cy (a locked quest)."""
        self.sharp_line(surf, (cx - 2, cy - 1), (cx - 2, cy - 4), col)
        self.sharp_line(surf, (cx + 2, cy - 1), (cx + 2, cy - 4), col)
        self.sharp_line(surf, (cx - 2, cy - 5), (cx + 2, cy - 5), col)
        self.round_box(surf, (cx - 4, cy - 1, 9, 7), col, None, 0, 2)

    def wrap_lines(self, text, w, size, bold=False):
        lines, line = [], ""
        for word_ in text.split():
            attempt = trim(line + " " + word_)
            if self.text_width(attempt, size, bold) > w and line:
                lines.append(line)
                line = word_
            else:
                line = attempt
        if line:
            lines.append(line)
        return [self.fit_text(ln, w, size, bold) for ln in lines] or [""]

    def quest_popup_rows(self, q, w, footer):
        """The checklist's rows: (kind, text, done, current). kind: title, giver, heading, item, item+ (a wrapped
        item's next line), footer."""
        rows = [("title", q["title"], 0, 0)]
        if q["giver"]:
            rows.append(("giver", "Given by " + pretty(q["giver"]), 0, 0))
        tw = w - 40
        steps = q.get("steps", [])
        open_steps = [i for i, (_, done) in enumerate(steps) if not done]
        for heading, items, current in (("Steps", steps, open_steps[-1] if open_steps else -1),
                                        ("Notes", q.get("notes", []), -1)):
            if not items:
                continue
            rows.append(("heading", heading, 0, 0))
            for i, (text, done) in enumerate(items):
                for j, ln in enumerate(self.wrap_lines(text, tw, 9, i == current)):
                    rows.append(("item" if j == 0 else "item+", ln, done, i == current))
        if q["status"] == 2:
            rows.append(("heading", "Quest complete!", 0, 0))
        if footer:
            rows.append(("footer", footer, 0, 0))
        heights = {"title": 22, "giver": 16, "heading": 20, "item": 15, "item+": 15, "footer": 18}
        while len(rows) > 6 and sum(heights[r[0]] for r in rows) + 20 > 600:     # too long: the oldest go first
            k = next((i for i, r in enumerate(rows) if r[0] == "item" and r[2]), None)
            if k is None:
                break
            del rows[k]
            while k < len(rows) and rows[k][0] == "item+":
                del rows[k]
        return rows, heights

    def quest_popup_size(self, q, w, footer=""):
        rows, heights = self.quest_popup_rows(q, w, footer)
        return w, 16 + sum(heights[r[0]] for r in rows)

    def sharp_line(self, surf, p1, p2, col, width=1):
        if isinstance(surf, Sharp):
            pygame.draw.line(surf.surf, colour(col), surf.at(*p1), surf.at(*p2), surf.line_width(width))
            surf.dirty = True
        else:
            pygame.draw.line(surf, colour(col), p1, p2, width)

    def draw_quest_popup(self, surf, q, x, y, w, footer=""):
        """The quest's checklist in a box at x,y, w wide: its title in its status colour, who gives it, the steps so
        far (the ones passed crossed out, the one it is at in gold) and the scripts' notes (crossed out when done)."""
        rows, heights = self.quest_popup_rows(q, w, footer)
        h = 16 + sum(heights[r[0]] for r in rows)
        sc, label = self.quest_look(q)
        self.round_box(surf, (x + 4, y + 4, w, h), (0, 0, 0), None, 0, 14)          # a shadow
        self.round_box(surf, (x, y, w, h), (46, 30, 23), sc, 2, 14)
        cy = y + 8
        cap_top, cap_h = self.cap_metrics(9, False)
        for kind, text, done, current in rows:
            if kind == "title":
                bw = self.help_badge(surf, x + w - 10, cy + 1, label, sc, lock=bool(q.get("needs")))
                self.draw_text(surf, self.fit_text(text, w - 34 - bw, 11, True), x + 12, cy, 11, True, sc)
            elif kind == "giver":
                self.draw_text(surf, self.fit_text(text, w - 24, 8), x + 12, cy, 8, False, (190, 160, 110))
            elif kind == "heading":
                self.draw_text(surf, text, x + 12, cy + 4, 8, True, (190, 160, 110) if text != "Quest complete!" else sc)
                self.sharp_line(surf, (x + 18 + self.text_width(text, 8, True), cy + 10), (x + w - 12, cy + 10),
                                (92, 60, 46))
            elif kind in ("item", "item+"):
                col = (128, 112, 96) if done else ((255, 214, 90) if current else PARCHMENT)
                if kind == "item":                 # a tick box
                    bx, by = x + 14, cy + 3
                    if done:
                        self.round_box(surf, (bx, by, 10, 10), (60, 120, 60), (90, 160, 90), 1, 4)
                        self.sharp_line(surf, (bx + 2, by + 5), (bx + 4, by + 7), (230, 250, 220), 2)
                        self.sharp_line(surf, (bx + 4, by + 7), (bx + 8, by + 2), (230, 250, 220), 2)
                    else:
                        self.round_box(surf, (bx, by, 10, 10), (30, 20, 16), col, 1, 4)
                tw = self.draw_text(surf, text, x + 30, cy, 9, current and not done, col)
                if done:                           # crossed out
                    my = cy + cap_top + int(cap_h / 2) + 1
                    self.sharp_line(surf, (x + 29, my), (x + 31 + tw, my), (150, 130, 110))
            elif kind == "footer":
                self.draw_text(surf, text, x + 12, cy + 4, 8, False, (150, 125, 95))
            cy += heights[kind]
        return h

    def quest_popup_layer(self, q, footer=""):
        """The checklist drawn on its own surface (crisp on a big screen), kept until the quest changes."""
        w = 300
        k = self.presenter.k if self.presenter is not None and self.presenter.active else 1.0
        key = (q["title"], q["status"], q["text"], tuple(q.get("steps", [])), tuple(q.get("notes", [])), footer, k)
        if self.quest_popup is None or self.quest_popup[0] != key:
            pw, ph = self.quest_popup_size(q, w, footer)
            surf = self.make_sharp(pw + 6, ph + 6)          # (new, so see-through)
            self.draw_quest_popup(surf, q, 0, 0, w, footer)
            self.quest_popup = (key, surf)
        return self.quest_popup[1]

    def draw_sidebar_quest_popup(self, scr):
        """While a quest in the sidebar's Quests tab is pointed at: its checklist, to the left of the sidebar."""
        if self.stats_view != 2 or self.quest_mouseover <= 0:
            return
        k = (self.quests_page - 1) * self.quests_per_page + self.quest_mouseover
        if k > len(self.help_quests):
            return
        q = self.help_quests[self.help_quest_order[k - 1]]
        surf = self.quest_popup_layer(q, "Click: open the journal.  Right-click: in the chat.")
        w, h = surf.get_size()
        row_y = self.statbar_y + self.quest_row_top + (self.quest_mouseover - 1) * self.quest_row_height
        y = min(max(6, row_y - 12), self.view_h - h - 6)
        self.show_layer(scr, surf, (self.view_w - w - 6, y))

    CONTROLS = (
        ("M", "Left-click ground", "Walk there."),
        ("M", "Left-click a thing", "Do its main action: Talk to a person, Pick up an item, Attack an enemy, Use an object..."),
        ("M", "Right-click", "A menu of everything you can do with it: Examine, Eat, Use, Drop All, Drop 1..."),
        ("M", "Use, then click", "Pick Use on an item you carry, then click what to use it with. Right-click to stop."),
        ("M", "Shops, bank, crafting", "Left-click buys, sells, banks or makes one. Right-click for more (Buy 5, Sell All, "
                                       "Value, Inspect...)."),
        ("M", "Box arrows, bar, wheel", "Next or previous page of a shop, bank or crafting list (or drag the bar, or turn the mouse wheel over it)."),
        ("M", "Skills (Stats)", "Point at a skill for its level. Right-click: progress to the next level. Left-click: "
                                "the skill's guide, if it has one."),
        ("M", "Stats / Equipment", "The tabs at the top of the Stats box: your skills, or your 8 labelled slots (Head, "
                                   "Body, Legs, Feet, Weapon, Shield, Hands, Ring) with your Attack and Defence bonuses."),
        ("M", "Wield, Wear", "Left-click a weapon, shield or armour in your inventory to put it on. Click it in the "
                             "Equipment tab to take it off."),
        ("M", "Quests", "Gold: in progress, green: done, grey: not started. Point at one (in the Quests tab or "
                        "here) for its checklist: the steps so far and your notes."),
        ("M", "Hotbar", "The five slots at the bottom of the view. Right-click an item in your inventory: Put it on the "
                        "hotbar. Click a slot (or press 1-5) to use it; right-click a slot to take it off."),
        ("M", "Status effects", "Icons over your head: poison (green), burning (orange), bleeding (red) hurt you for a "
                                "while; chill (blue) slows you. They wear off, or drink an Antidote."),
        ("M", "Dying", "You wake at the start, a quarter of your gold gone. Everything else you carried is in a grave "
                       "where you fell: Search it within 10 minutes to get it back."),
        ("M", "Sun and moon", "Above the minimap: point at it for the time of day. A day lasts 24 minutes; at night "
                              "townsfolk go home, lamps and windows are lit, and some creatures come out."),
        ("M", "Sleep", "Click a bed: you sleep through the night to the morning, or through the day to the evening, "
                       "and wake healed. Not with enemies near or straight after a fight."),
        ("M", "Weather", "Rain, storms, snow, blizzards and fog come and go, as suits the place."),
        ("M", "Wear and repair", "Weapons and armour wear as you fight (the bar under them); worn out they break and "
                                 "do nothing. Right-click a blacksmith: Repair (for gold), or use the item on an "
                                 "anvil with a bar of its metal."),
        ("M", "Minimap - and +", "Zoom the minimap out and in."),
        ("M", "Mouse wheel", "Over the map: zoom in and out (75% to 300%)."),
        ("M", "Chat arrows, bar, wheel", "Scroll back through older messages (or drag the bar, or turn the mouse wheel over the chat)."),
        ("M", "Pointing", "The box at the bottom right names whatever is under the mouse."),
        ("M", "? Help button", "Opens this journal (top left of the sidebar)."),
        ("M", "X (top right)", "Save and quit."),
        ("K", "Arrows or W A S D", "Walk (two at once walks diagonally)."),
        ("K", "H or F1", "Open or close this journal."),
        ("K", "Esc", "Close a menu, box or this journal, or stop using an item. With nothing open: save and quit."),
        ("K", "1 - 5", "Use what's in that hotbar slot."),
        ("K", "1 - 4", "Journal: pick a tab (Left and Right also work)."),
        ("K", "Up / Down", "Journal: previous or next page (PgUp and PgDn too)."),
        ("K", "F11", "Full screen or a window."),
        ("K", "+ / -", "Zoom the map in and out."),
        ("K", "Saving", "Automatic: when you change map and when you quit."),
        ("K", "Running away", "Monsters only chase you so far from where they live, then give up and walk back."),
    )

    def help_draw_controls(self, surf):
        """Mouse on the left, keyboard on the right; mouse rows that don't fit carry on under the keyboard ones."""
        def heading(x, y, text):
            self.draw_text(surf, text, x, y, 12, True, INK)
            self.box(surf, x, y + 24, x + 420, y + 24, (126, 77, 63), None, 0)
            return y + 32

        def row(x, y, control, what):
            self.draw_text(surf, self.fit_text(control, 140, 9, True), x, y, 9, True, INK)
            lines = self.help_wrap(surf, x + 148, y, 272, what, (250, 240, 210), 15, 3)
            return y + max(1, lines) * 15 + 8

        def height(what):
            return len(self.wrap_lines(what, 272, 9)[:3]) * 15 + 8

        mouse = [(c, w) for k, c, w in self.CONTROLS if k == "M"]
        y = heading(60, 110, "Mouse")
        while mouse and y + height(mouse[0][1]) <= 680:
            y = row(60, y, *mouse.pop(0))
        y = heading(528, 110, "Keyboard")
        for k, control, what in self.CONTROLS:
            if k == "K":
                y = row(528, y, control, what)
        if mouse:
            y = heading(528, y + 10, "Mouse (more)")
            for control, what in mouse:
                if y + height(what) <= 680:
                    y = row(528, y, control, what)

    # =================================================================================================================
    # Admin panel (Config.ini [Admin] Enabled=1): give yourself items, set skill levels, switch skills off, god mode.
    # A panel over the game (the game carries on while it is open)
    # =================================================================================================================
    def read_disabled_skills(self):
        off = "," + self.config_read("Skills", "Disabled", "").replace(" ", "").upper() + ","
        for i in range(1, self.total_skills + 1):
            self.skill_off[i] = 0
            if ("," + self.skill_name[i].upper() + ",") in off and self.skill_name[i].upper() != "HITPOINTS":
                self.skill_off[i] = 1

    def open_admin(self):
        if self.admin_open:
            return
        self.admin_load_items()
        self.admin_rows = min(16, self.total_skills)
        self.admin_ticks = [self.skill_off[i] == 0 for i in range(1, self.admin_rows + 1)]
        self.admin_levels = [lbstr(self.level_of_xp(self.skill_xp[i])) for i in range(1, self.admin_rows + 1)]
        self.admin_qty = "1"
        self.admin_filter = ""
        self.admin_pick = 0
        self.admin_scroll = 0
        self.admin_focus = ""
        self.admin_status = "%d items to give" % len(self.admin_items)
        self.admin_open = True
        bottom = 76 + int((self.admin_rows + 1) / 2) * 26 + 10
        self.admin_w = 470
        self.admin_h = bottom + 108 + 150
        self.admin_x = int((self.view_w - self.admin_w) / 2)
        self.admin_y = 20

    def admin_load_items(self):
        self.admin_items = []
        path = os.path.join(self.root, "Data", "Entities.ini")
        if not os.path.exists(path):
            return
        section = ""
        for line in self.read_lines(path):
            ln = trim(line.replace("\t", " ")).strip()
            if ln.startswith("["):
                section = ln[1:-1] if ln.endswith("]") else ln[1:]
            if ln.upper().replace(" ", "") == "TYPE=MAPITEM" and section and len(self.admin_items) < 1000:
                self.admin_items.append(section)
        self.admin_items.sort(key=str.lower)

    def admin_filtered(self):
        f = self.admin_filter.lower()
        return [it for it in self.admin_items if f in it.lower().replace("_", " ") or f in it.lower()]

    def admin_layout(self):
        """Every clickable part of the panel: name -> Rect (screen pixels)."""
        x, y = self.admin_x, self.admin_y
        r = {"panel": pygame.Rect(x, y, self.admin_w, self.admin_h),
             "filter": pygame.Rect(x + 105, y + 34, 200, 22),
             "list": pygame.Rect(x + 105, y + 60, 200, 128),
             "qty": pygame.Rect(x + 312, y + 34, 50, 22),
             "give": pygame.Rect(x + 370, y + 34, 80, 24)}
        top = y + 230
        for k in range(1, self.admin_rows + 1):
            col = (k - 1) % 2
            row = int((k - 1) / 2)
            bx = x + 12 + col * 225
            by = top + row * 26
            r["tick%d" % k] = pygame.Rect(bx, by + 2, 140, 18)
            r["level%d" % k] = pygame.Rect(bx + 145, by, 45, 22)
        bottom = top + int((self.admin_rows + 1) / 2) * 26 + 10
        r["god"] = pygame.Rect(x + 12, bottom, 420, 20)
        r["save"] = pygame.Rect(x + 12, bottom + 28, 100, 28)
        r["close"] = pygame.Rect(x + 120, bottom + 28, 100, 28)
        r["status"] = pygame.Rect(x + 230, bottom + 34, 230, 20)
        self.admin_h = bottom + 70 - y
        r["panel"].height = self.admin_h
        return r

    def admin_handle(self):
        """The panel's share of the mouse and keyboard this loop. True if it used the click."""
        if not self.admin_open:
            return False
        r = self.admin_layout()
        used = False
        if self.mouse_wheel and r["list"].collidepoint(self.cursor_x, self.cursor_y):
            n = len(self.admin_filtered())
            self.admin_scroll = max(0, min(max(0, n - 8), self.admin_scroll - self.mouse_wheel * 2))
        if self.mouse_left_click and r["panel"].collidepoint(self.cursor_x, self.cursor_y):
            used = True
            pos = (self.cursor_x, self.cursor_y)
            self.admin_focus = ""
            if r["filter"].collidepoint(pos):
                self.admin_focus = "filter"
            elif r["qty"].collidepoint(pos):
                self.admin_focus = "qty"
            elif r["list"].collidepoint(pos):
                row = int((pos[1] - r["list"].y) / 16) + self.admin_scroll
                items = self.admin_filtered()
                if 0 <= row < len(items):
                    self.admin_pick = self.admin_items.index(items[row])
            elif r["give"].collidepoint(pos):
                self.admin_give()
            elif r["god"].collidepoint(pos):
                self.admin_god(not self.god_mode)
            elif r["save"].collidepoint(pos):
                self.admin_save()
            elif r["close"].collidepoint(pos):
                self.admin_open = False
                self.admin_focus = ""
            else:
                for k in range(1, self.admin_rows + 1):
                    if r["tick%d" % k].collidepoint(pos):
                        if self.skill_name[k].upper() != "HITPOINTS":
                            self.admin_ticks[k - 1] = not self.admin_ticks[k - 1]
                    if r["level%d" % k].collidepoint(pos):
                        self.admin_focus = "level%d" % k
        elif self.mouse_left_click:
            self.admin_focus = ""
        if self.admin_focus:
            for ev in self.text_events:
                for ch in ev:
                    if self.admin_focus == "filter":
                        if len(self.admin_filter) < 24:
                            self.admin_filter += ch
                            self.admin_scroll = 0
                    elif ch.isdigit():
                        if self.admin_focus == "qty" and len(self.admin_qty) < 6:
                            self.admin_qty += ch
                        elif self.admin_focus.startswith("level"):
                            k = int(self.admin_focus[5:])
                            if len(self.admin_levels[k - 1]) < 3:
                                self.admin_levels[k - 1] += ch
            if self.key_hit(pygame.K_BACKSPACE):
                if self.admin_focus == "filter":
                    self.admin_filter = self.admin_filter[:-1]
                elif self.admin_focus == "qty":
                    self.admin_qty = self.admin_qty[:-1]
                else:
                    k = int(self.admin_focus[5:])
                    self.admin_levels[k - 1] = self.admin_levels[k - 1][:-1]
            if self.key_hit(pygame.K_RETURN) or self.key_hit(pygame.K_KP_ENTER):
                if self.admin_focus in ("filter", "qty"):
                    self.admin_give()
                else:
                    self.admin_save()
            if self.key_hit(pygame.K_ESCAPE):
                self.admin_focus = ""
                self.keys_hit.discard(pygame.K_ESCAPE)
        return used

    def admin_give(self):
        items = self.admin_filtered()
        item = ""
        if 0 <= self.admin_pick < len(self.admin_items) and self.admin_items[self.admin_pick] in items:
            item = self.admin_items[self.admin_pick]
        elif len(items) == 1:
            item = items[0]
        qty = max(1, int(val(self.admin_qty)))
        if item == "":
            self.admin_status = "Pick an item first."
            return
        room = self.inventory_slots_available(item)
        if room <= 0:
            self.admin_status = "No room in the inventory for that."
            return
        qty = min(qty, room)
        self.add_inventory_item(item, qty)
        self.play_sound("Pickup")
        self.admin_status = "Gave you %d %s." % (qty, pretty(item))

    def admin_save(self):
        off = []
        for k in range(1, self.admin_rows + 1):
            if not self.admin_ticks[k - 1] and self.skill_name[k].upper() != "HITPOINTS":
                self.skill_off[k] = 1
                off.append(self.skill_name[k])
            else:
                self.skill_off[k] = 0
            level = int(val(self.admin_levels[k - 1]))
            if level >= 1 and level != self.level_of_xp(self.skill_xp[k]):
                self.skill_xp[k] = min(self.skill_max_level, level)
        ini.write("Skills", "Disabled", ",".join(off), self.config_path)
        self.update_max_hp()
        self.draw_skills()
        self.check_locks(True)
        if self.main_setup_complete:
            self.save_player()
        self.admin_status = "Saved." if not off else "Saved. Off: " + ",".join(off)

    def admin_god(self, on):
        self.god_mode = 1 if on else 0
        ini.write("Admin", "GodMode", lbstr(self.god_mode), self.config_path)
        if self.god_mode:
            self.player.hp = self.player_max_hp
            self.draw_skills()
            self.display_message("God mode is on: nothing can hurt you.", "INFO")
            self.admin_status = "God mode on."
        else:
            self.display_message("God mode is off.", "INFO")
            self.admin_status = "God mode off."

    def draw_admin(self, scr):
        r = self.admin_layout()
        x, y = self.admin_x, self.admin_y
        panel = r["panel"]
        pygame.draw.rect(scr, (236, 233, 216), panel)
        pygame.draw.rect(scr, (48, 76, 104), panel, 2)
        pygame.draw.rect(scr, (48, 76, 104), (panel.x, panel.y, panel.w, 22))
        self.draw_text(scr, "Dragon Sword - Admin", x + 8, y + 3, 9, True, (255, 255, 255))
        ink = (20, 20, 20)
        self.draw_text(scr, "Give yourself:", x + 12, y + 37, 9, False, ink)

        def field_box(rect, text, focused):
            pygame.draw.rect(scr, (255, 255, 255), rect)
            pygame.draw.rect(scr, (0, 120, 215) if focused else (122, 122, 122), rect, 1)
            self.draw_text(scr, text + ("|" if focused else ""), rect.x + 4, rect.y + 3, 9, False, ink)

        field_box(r["filter"], self.admin_filter or ("" if self.admin_focus == "filter" else "type to search..."),
                  self.admin_focus == "filter")
        field_box(r["qty"], self.admin_qty, self.admin_focus == "qty")
        lst = r["list"]
        pygame.draw.rect(scr, (255, 255, 255), lst)
        pygame.draw.rect(scr, (122, 122, 122), lst, 1)
        items = self.admin_filtered()
        for n, it in enumerate(items[self.admin_scroll:self.admin_scroll + 8]):
            ry = lst.y + n * 16
            picked = 0 <= self.admin_pick < len(self.admin_items) and self.admin_items[self.admin_pick] == it
            if picked:
                pygame.draw.rect(scr, (0, 120, 215), (lst.x + 1, ry, lst.w - 2, 16))
            self.draw_text(scr, self.fit_text(pretty(it), lst.w - 8, 9), lst.x + 4, ry + 1, 9, False,
                           (255, 255, 255) if picked else ink)
        self.admin_button(scr, r["give"], "Give")
        self.draw_text(scr, "Skills: untick to switch one off; type a level (1 to %d) to set it" % self.skill_max_level,
                       x + 12, y + 206, 9, False, ink)
        for k in range(1, self.admin_rows + 1):
            t = r["tick%d" % k]
            pygame.draw.rect(scr, (255, 255, 255), (t.x, t.y + 2, 13, 13))
            pygame.draw.rect(scr, (90, 90, 90), (t.x, t.y + 2, 13, 13), 1)
            if self.admin_ticks[k - 1]:
                pygame.draw.lines(scr, (20, 20, 20), False, [(t.x + 3, t.y + 8), (t.x + 6, t.y + 12),
                                                             (t.x + 11, t.y + 4)], 2)
            grey = self.skill_name[k].upper() == "HITPOINTS"
            self.draw_text(scr, self.skill_name[k], t.x + 18, t.y + 1, 9, False, (120, 120, 120) if grey else ink)
            field_box(r["level%d" % k], self.admin_levels[k - 1], self.admin_focus == "level%d" % k)
        g = r["god"]
        pygame.draw.rect(scr, (255, 255, 255), (g.x, g.y + 2, 13, 13))
        pygame.draw.rect(scr, (90, 90, 90), (g.x, g.y + 2, 13, 13), 1)
        if self.god_mode:
            pygame.draw.lines(scr, (20, 20, 20), False, [(g.x + 3, g.y + 8), (g.x + 6, g.y + 12), (g.x + 11, g.y + 4)], 2)
        self.draw_text(scr, "God mode (nothing can hurt you; on at once, and remembered)", g.x + 18, g.y + 1, 9, False, ink)
        self.admin_button(scr, r["save"], "Save")
        self.admin_button(scr, r["close"], "Close")
        self.draw_text(scr, self.fit_text(self.admin_status, 230, 9), r["status"].x, r["status"].y, 9, False, ink)

    def admin_button(self, scr, rect, label):
        hot = rect.collidepoint(self.cursor_x, self.cursor_y)
        pygame.draw.rect(scr, (229, 241, 251) if hot else (225, 225, 225), rect)
        pygame.draw.rect(scr, (0, 120, 215) if hot else (173, 173, 173), rect, 1)
        w = self.text_width(label, 9)
        self.draw_text_mid(scr, label, rect.x + int((rect.w - w) / 2), rect.y, rect.h, 9, False, (20, 20, 20))
