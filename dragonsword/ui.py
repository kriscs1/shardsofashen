"""The interface: the chat bar and the hover box beside it, the info box, the ActionBox (conversations, shops, the bank,
crafting) and its response box, the right-click menu, the Stats / Gear / Quests tabs, and drawing each frame."""
import math

import pygame

from .assets import colour
from .entity import (Entity, PLAYER, TILE, MAPITEM, STATICOBJECT, NPC, MISSILE, TEMPORARY, INFRONTTILE,
                     ACTIONBOXITEM, INVENTORYITEM)
from .lb import val, word, field, trim, lbstr, word_count, pretty
from .sharp import Sharp

TAB_TEXT = (243, 232, 136)


class UIMixin:
    # =================================================================================================================
    # Text helpers
    # =================================================================================================================
    def font(self, size, bold=False):
        return self.assets.font(size, bold)

    def text_width(self, text, size, bold=False):
        return self.assets.text_width(text, size, bold)

    def draw_text(self, surf, text, x, y, size, bold, col):
        """Text with its top-left at x,y (gx "textat")."""
        if not text:
            return 0
        if isinstance(surf, Sharp):                  # drawn at the screen's resolution: the font k times bigger
            img = self.font(size * surf.k, bold).render(text, True, colour(col))
            surf.surf.blit(img, surf.at(int(x), int(y)))
            surf.dirty = True
            return round(img.get_width() / surf.k)
        img = self.font(size, bold).render(text, True, colour(col))
        surf.blit(img, (int(x), int(y)))
        return img.get_width()

    def draw_text_baseline(self, surf, text, x, y, size, bold, col):
        """Text with its baseline at y (LB "place x y; \\text")."""
        f = self.font(size, bold)
        if text and isinstance(surf, Sharp):
            big = self.font(size * surf.k, bold)
            bx, by = surf.at(int(x), int(y))
            surf.surf.blit(big.render(text, True, colour(col)), (bx, by - big.get_ascent()))
            surf.dirty = True
        elif text:
            surf.blit(f.render(text, True, colour(col)), (int(x), int(y) - f.get_ascent()))
        return f.get_linesize()

    def cap_metrics(self, size, bold=False):
        """(top, height) of capital letters and digits in a rendered line of this font: where the letters really
        are, so text can be centred in a box by its letters rather than by the font's taller line box."""
        key = ("cap", self.assets.font_name, size, bold)
        m = self.icon_cache.get(key)
        if m is None:
            r = self.font(size, bold).render("H08", True, (255, 255, 255)).get_bounding_rect()
            m = (r.y, max(1, r.h))
            self.icon_cache[key] = m
        return m

    def draw_text_mid(self, surf, text, x, top, height, size, bold, col):
        """Text whose capitals are centred between top and top+height."""
        cap_top, cap_h = self.cap_metrics(size, bold)
        return self.draw_text(surf, text, x, top + round((height - cap_h) / 2) - cap_top, size, bold, col)

    def centred_mid(self, surf, xm, top, height, text, size, bold, col):
        """Text centred on xm, its capitals centred between top and top+height, with a dark shadow."""
        x = xm - int(self.text_width(text, size, bold) / 2)
        self.draw_text_mid(surf, text, x + 1, top + 1, height, size, bold, (0, 0, 0))
        self.draw_text_mid(surf, text, x, top, height, size, bold, col)

    def crisp_label(self, scr, text, x, top, w, h, size, bold, col):
        """Text centred (by its letters) in the box x,top,w,h of the frame. On a big screen it is drawn on a small
        Sharp laid over the frame, so it is as crisp as the screen allows; the Sharps are kept and reused."""
        k = self.presenter.k if self.presenter is not None and self.presenter.active else 1.0
        lw = self.text_width(text, size, bold)
        if k <= 1.01:
            self.draw_text_mid(scr, text, x + int((w - lw) / 2), top, h, size, bold, col)
            return
        key = (text, w, h, size, bold, tuple(col), k, self.assets.font_name)
        cache = self.__dict__.setdefault("crisp_cache", {})
        sharp = cache.get(key)
        if sharp is None:
            if len(cache) > 300:
                cache.clear()
            sharp = cache[key] = Sharp(w, h, k)
            self.draw_text_mid(sharp, text, int((w - lw) / 2), 0, h, size, bold, col)
        self.sharp_layers.append((sharp, (x, top)))

    def fit_text(self, text, max_width, size, bold=False):
        """text cut short (with ...) to fit max_width pixels (Help.Fit$)."""
        if max_width <= 0 or not text:
            return ""
        f = self.font(size, bold)
        full = f.size(text)[0]
        if full <= max_width:
            return text
        n = min(len(text), int(len(text) * max_width / max(1, full)) + 2)
        while n > 0 and f.size(text[:n].strip() + "...")[0] > max_width:
            n -= 1
        return text[:n].strip() + "..." if n > 0 else ""

    def centre_text(self, surf, xm, y, text, size, bold, col):
        """Help.Centre: text centred on xm, its top at y."""
        text = self.fit_text(text, 900, size, bold)
        self.draw_text(surf, text, xm - int(self.text_width(text, size, bold) / 2), y, size, bold, col)

    @staticmethod
    def round_box(surf, rect, fill, border=None, width=1, radius=10):
        """gx roundbox: radius is the corner ellipse's size, as in GDI RoundRect."""
        r = pygame.Rect(rect)
        rad = max(0, int(radius / 2))
        if isinstance(surf, Sharp):
            r, rad, width = surf.rect(r), round(rad * surf.k), surf.line_width(width)
            surf.dirty = True
            surf = surf.surf
        if fill is not None:
            pygame.draw.rect(surf, colour(fill), r, 0, border_radius=rad)
        if border is not None and width > 0:
            pygame.draw.rect(surf, colour(border), r, width, border_radius=rad)

    @staticmethod
    def silhouette(img, col):
        """img's shape engraved in colour col: its edge in col, the inside faintly (the Gear tab's empty slots)."""
        import numpy as np
        a = pygame.surfarray.array_alpha(img) >= 128
        inner = a.copy()
        inner[1:, :] &= a[:-1, :]
        inner[:-1, :] &= a[1:, :]
        inner[:, 1:] &= a[:, :-1]
        inner[:, :-1] &= a[:, 1:]
        s = pygame.Surface(img.get_size(), pygame.SRCALPHA)
        rgb = pygame.surfarray.pixels3d(s)
        rgb[:] = col
        del rgb
        alpha = pygame.surfarray.pixels_alpha(s)
        alpha[:] = np.where(a & ~inner, 255, np.where(inner, 60, 0)).astype(np.uint8)
        del alpha
        return s

    def draw_icon(self, surf, name, x, y, size, tint=None):
        """Help.Icon: a sprite's picture scaled to fit size x size (tint: its silhouette in that colour)."""
        if not name or not self.assets.loaded(name):
            return
        if isinstance(surf, Sharp):                  # the sprite scaled straight to its size on the screen
            big = round(size * surf.k)
            key = (name, big, tint)
            img = self.icon_cache.get(key)
            if img is None:
                sp = self.assets.get(name)
                if sp.w < 1 or sp.h < 1:
                    return
                scale = min(big / sp.w, big / sp.h)
                img = pygame.transform.scale(sp.masked, (max(1, int(sp.w * scale)), max(1, int(sp.h * scale))))
                if tint:
                    img = self.silhouette(img, tint)
                self.icon_cache[key] = img
            px, py = surf.at(x, y)
            surf.surf.blit(img, (px + int((big - img.get_width()) / 2), py + int((big - img.get_height()) / 2)))
            surf.dirty = True
            return
        key = (name, size, tint)
        img = self.icon_cache.get(key)
        if img is None:
            sp = self.assets.get(name)
            w, h = sp.w, sp.h
            if w < 1 or h < 1:
                return
            scale = min(size / w, size / h)
            dw, dh = max(1, int(w * scale)), max(1, int(h * scale))
            img = pygame.transform.scale(sp.masked, (dw, dh))
            if tint:
                img = self.silhouette(img, tint)
            self.icon_cache[key] = img
        surf.blit(img, (x + int((size - img.get_width()) / 2), y + int((size - img.get_height()) / 2)))

    # =================================================================================================================
    # Chat and the hover box
    # =================================================================================================================
    def scroll_message_display(self, increment):
        if increment == 0:
            self.chat_line = 1
        else:
            self.chat_line = min(46, max(1, self.chat_line + increment))
        self.chat_dirty = True

    @staticmethod
    def valid_colour(c):
        c = trim(c).lower()
        if c in ("white", "black", "lightgray", "darkgray", "red", "darkred", "pink", "darkpink", "blue", "darkblue",
                 "green", "darkgreen", "darkcyan", "brown"):
            return c
        if c == "cyan":
            return "darkblue"
        if c == "yellow":
            return "darkgreen"
        if val(word(c, 1)) > 0 or word(c, 3) != "":
            return c
        return "darkgray"

    def display_message(self, message, mtype):
        if self.message_log and message == self.message_log[0][0] and self.clock() - self.message_log[0][2] < 500:
            return
        if message[:14].upper() == "QUEST COMPLETE":
            self.play_sound("Quest")
        t = str(mtype).upper()
        if t in ("ERROR", "WARNING", "FAIL"):
            c = "darkred"
        elif t in ("INFORMATION", "SUCCESS"):
            c = "darkblue"
        elif t == "ACHIEVEMENT":
            c = "darkgreen"
        elif t == "LOG":
            c = "darkcyan"
        elif t in ("INFO", "EXAMINE"):
            c = "black"
        elif t == "COMBAT":
            c = "brown"
        elif t == "DAMAGE":                 # you're hurt: bright red, not the dark red of "you can't do that"
            c = "205 18 18"
        elif t == "LEVELUP":                # a new level: gold
            c = "140 82 0"
        else:
            c = self.valid_colour(mtype)
        self.message_log.insert(0, (message, c, self.clock()))
        del self.message_log[50:]
        self.scroll_message_display(0)

    def display_quick_message(self, message, mtype):
        if message == self.qm_message:
            return
        self.qm_message = message
        self.qm_lines = []
        self.chat_dirty = True
        if message == "":
            return
        c = {"ERROR": "150 20 20", "WARNING": "150 20 20", "INFORMATION": "120 70 0", "ENTITY": "60 30 20",
             "INTERFACE": "30 50 120"}.get(mtype, "70 50 40")
        parts = message.split("|")
        size = 10
        while True:
            size -= 1
            lines = []
            for part in parts:
                seg = trim(part)
                line = ""
                for w in seg.split():
                    attempt = trim(line + " " + w)
                    if self.text_width(attempt, size) > 150 and line != "":
                        if len(lines) < 10:
                            lines.append(line)
                        line = w
                    else:
                        line = attempt
                if len(lines) < 10:
                    lines.append(line)
            line_h = int(size * 1.35) + 1
            if len(lines) * line_h <= 70 or size <= 6:
                break
        self.qm_lines = lines
        self.qm_size = size
        self.qm_colour = colour(c)
        self.qm_line_h = line_h
        self.qm_y = max(line_h - 2, int(31 - len(lines) * line_h / 2 + line_h * 0.8))

    def redraw_chat_bar(self):
        surf = self.chat_surface
        surf.blit(self.chat_bg, (0, 0))
        y = 20
        for i in range(self.chat_line + 4, self.chat_line - 1, -1):
            if 1 <= i <= len(self.message_log):
                msg, c, _ = self.message_log[i - 1]
                self.draw_text_baseline(surf, msg, 10, y, 9, False, c)
            y += self.font(9).get_linesize()
        if self.qm_lines:
            y = self.qm_y
            for i, line in enumerate(self.qm_lines):
                self.draw_text_baseline(surf, line, self.view_w + 35, y, self.qm_size, i == 0, self.qm_colour)
                y += self.qm_line_h
        self.chat_dirty = False

    # =================================================================================================================
    # Info box, ActionBox, response box
    # =================================================================================================================
    def hide_infobox(self):
        self.infobox_open = False

    def show_infobox(self, title, title_colour, info, info_colour):
        self.infobox_open = True
        sp = self.assets.get("InfoBox")
        w = sp.w if sp else 144
        h = self.assets.picture_height("InfoBox", 166)
        surf = pygame.Surface((w, h)).convert()
        surf.fill((212, 191, 126))
        if sp:
            surf.blit(sp.full, (0, 0))
        self.draw_text_baseline(surf, title, 15, 30, 12, True, title_colour)
        self.draw_text_baseline(surf, info, 15, 60, 11, False, info_colour)
        self.infobox_surface = surf

    def action_box_background(self, mode):
        bg = "AB_" + mode
        if not self.assets.loaded(bg):
            bg = "AB_Bank" if self.assets.loaded("AB_Bank") else self.interface_sprite("AB_Conversation")
        return bg

    def hide_action_box(self):
        if self.ab_mode == "":
            return
        self.ab_mode = ""
        self.ab_surface = None
        self.ab_items = []
        self.hide_response_box()
        self.force_layer_update = True

    def close_action_box(self, result):
        """Closes the ActionBox; a script waiting on it carries on (result -1 = cancelled)."""
        self.hide_action_box()
        if self.script_state in ("CONVERSATION", "RACK"):
            self.script_result = result

    def show_action_box(self, mode):
        """Shop Craft Bank Armour Conversation. While it is open the world is paused (game_loop)."""
        self.stop_player_walk()
        self.hide_action_box()
        self.show_response_box(-1)
        self.ab_mode = mode
        if not self.ab_image:
            self.ab_image = "Placeholder"
        self.ab_image = self.interface_sprite(self.ab_image)
        if not self.ab_title:
            self.ab_title = "?"
        self.build_action_box(self.action_box_background(mode))
        self.refresh_action_box_items()
        self.force_layer_update = True

    def refresh_action_box_items(self):
        self.ab_items = []
        if self.ab_mode != "Conversation":
            gap = self.tw + 5
            for n, (name, qty, misc) in enumerate(self.ab_item_defs):
                if n >= self.ab_columns * self.ab_rows:
                    break
                e = Entity(ACTIONBOXITEM, name)
                self.init_entity(e, 0, 0)
                e.x = self.ab_x + 66 + gap * (n % self.ab_columns)
                e.y = self.ab_y + 45 + gap * int(n / self.ab_columns)
                e.qty_text = qty
                e.misc = misc
                self.ab_items.append(e)
        self.show_response_box(-1)
        self.force_layer_update = True

    def build_action_box(self, background):
        """The box: the background with the NPC portrait, title and (for conversations) the wrapped text."""
        bg = self.assets.get(background)
        if bg is None:
            self.ab_surface = None
            return
        w, h = bg.w, bg.h
        surf = bg.masked.copy()
        portrait = self.assets.get(self.ab_image)
        pw = portrait.w if portrait else 32
        ph = portrait.h if portrait else 32
        if self.ab_mode == "Conversation":
            zoom, px, py = 2, 24, 20
            title_x, title_y = 24 + max(32, pw) * zoom + 16, 18
        else:
            zoom, px, py = 1, 37 - int(pw / 2), 52
            title_x, title_y = 22, 14
        if portrait:
            pic = portrait.image.copy()
            pic.set_colorkey((0, 0, 0))
            if zoom != 1:
                pic = pygame.transform.scale(pic, (pw * zoom, ph * zoom))
            surf.blit(pic, (px, py))
        if self.ab_mode == "Conversation":
            self.draw_text(surf, self.ab_title, title_x, title_y, 12, True, TAB_TEXT)
        else:                                       # on the racks: centred (by its letters) in the plank band, 18-43
            cap_top, cap_h = self.cap_metrics(12, True)
            title_y = 18 + round((26 - cap_h) / 2) - cap_top
            self.draw_text(surf, self.ab_title, title_x, title_y, 12, True, TAB_TEXT)
        title_w = self.text_width(self.ab_title, 12, True)
        kind = {"Shop": "Shop", "Bank": "Bank", "Craft": "Crafting"}.get(self.ab_mode, "")
        if kind:                                    # sharing the title's baseline
            base = title_y + self.font(12, True).get_ascent()
            self.draw_text_baseline(surf, "- " + kind, title_x + title_w + 10, base, 9, False, (212, 191, 126))
        if self.ab_mode == "Conversation":
            max_w = w - title_x - 28
            size = 9
            line_h = 14
            for size in (11, 10, 9):
                line_h = max(14, self.font(size, True).get_height() + 2)
                if self.conversation_lines(self.ab_text, max_w, size) * line_h <= h - 58:
                    break
            y = 48
            for part in self.ab_text.split("|"):
                if part == "" or y + line_h > h - 10:
                    continue
                line = ""
                for wd in trim(part).split():
                    if y + line_h > h - 10:
                        break
                    attempt = trim(line + " " + wd)
                    if self.text_width(attempt, size, True) > max_w and line != "":
                        self.draw_text(surf, line, title_x, y, size, True, (250, 240, 210))
                        y += line_h
                        line = wd
                    else:
                        line = attempt
                if line and y + line_h <= h - 10:
                    self.draw_text(surf, line, title_x, y, size, True, (250, 240, 210))
                    y += line_h
        self.ab_surface = surf

    def conversation_lines(self, text, max_w, size):
        n = 0
        for part in text.split("|"):
            if part == "":
                continue
            line = ""
            for wd in trim(part).split():
                attempt = trim(line + " " + wd)
                if self.text_width(attempt, size, True) > max_w and line != "":
                    n += 1
                    line = wd
                else:
                    line = attempt
            if line:
                n += 1
        return n

    def hide_response_box(self):
        self.rb_surface = None
        self.rb_highlight = -2

    def show_response_box(self, selected):
        """-1 = initialise"""
        if selected == self.rb_highlight and selected != -1:
            return
        self.rb_highlight = selected
        sp = self.assets.get("ResponseBox")
        w = sp.w if sp else 459
        base_h = self.assets.picture_height("ResponseBox", 112)
        h = max(base_h, 8 + len(self.responses) * 16 + 22)  # Grows for long lists (clear of the frame's bottom edge)
        surf = pygame.Surface((w, h)).convert()
        surf.fill((0, 0, 0))
        if sp:
            img = sp.full
            ih = img.get_height()
            if h <= ih:
                surf.blit(img, (0, 0))
            else:
                # The frame's top and bottom as they are, the parchment in between stretched
                top, bottom = 30, 20
                surf.blit(img, (0, 0), (0, 0, w, top))
                middle = img.subsurface((0, top, w, ih - top - bottom))
                surf.blit(pygame.transform.scale(middle, (w, h - top - bottom)), (0, top))
                surf.blit(img, (0, h - bottom), (0, ih - bottom, w, bottom))
        for i, r in enumerate(self.responses, 1):
            c = (200, 30, 20) if selected == i else (0, 0, 0)
            self.draw_text_mid(surf, "%d. %s" % (i, r), 40, 7 + (i - 1) * 16, 16, 10, True, c)
        self.rb_surface = surf

    # =================================================================================================================
    # Right-click menu
    # =================================================================================================================
    def open_right_click_menu(self, e):
        e = self.pick_tile(e)
        self.rcm_world_x, self.rcm_world_y = self.screen_to_world(self.cursor_x, self.cursor_y)
        verbs = self.get_verbs(e)
        if verbs == "":
            if self.cursor_x < 0 or self.cursor_y < 0 or self.cursor_x >= self.view_w or self.cursor_y >= self.view_h:
                return
            verbs = "Walk here"
        self.rcm_verbs = []
        self.rcm_labels = []
        for i in range(1, 21):
            v = word(verbs, i, ",")
            if v == "":
                break
            self.rcm_verbs.append(v)
            self.rcm_labels.append(self.verb_label(v, e))
        self.rcm_verbs.append("Cancel")
        self.rcm_labels.append("Cancel")
        longest = max(self.text_width(lb, 9, True) for lb in self.rcm_labels)
        self.rcm_target = e
        self.rcm_highlight = 0
        self.rcm_row_top = 6
        self.rcm_row_height = 18
        self.rcm_w = max(110, longest + 28)
        self.rcm_h = self.rcm_row_top * 2 + len(self.rcm_verbs) * self.rcm_row_height
        self.rcm_x = min(max(0, self.cursor_x - 10), self.win_w - self.rcm_w)
        self.rcm_y = min(max(0, self.cursor_y - 8), self.view_h - self.rcm_h)
        self.rcm_open = True

    def close_right_click_menu(self):
        self.rcm_open = False
        self.rcm_highlight = 0

    def draw_right_click_menu(self, scr):
        w, h = self.rcm_w, self.rcm_h
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        self.round_box(surf, (0, 0, w, h), (51, 34, 27), (126, 77, 63), 2, 12)
        for i in range(len(self.rcm_verbs)):
            ry = self.rcm_row_top + i * self.rcm_row_height
            c = TAB_TEXT
            if self.rcm_verbs[i] == "Cancel":
                c = (190, 160, 110)
                pygame.draw.line(surf, (92, 60, 46), (10, ry), (w - 10, ry))
            if i + 1 == self.rcm_highlight:
                self.round_box(surf, (5, ry + 1, w - 10, self.rcm_row_height - 1), (126, 77, 63), (160, 104, 80), 1, 8)
                c = (255, 255, 255)
            self.draw_text_mid(surf, self.rcm_labels[i], 14, ry + 1, self.rcm_row_height - 1, 9, True, c)
        scr.blit(surf, (self.rcm_x, self.rcm_y))

    # =================================================================================================================
    # The Stats box: tabs Stats (skills), Gear (equipment), Quests
    # =================================================================================================================
    def set_stats_view(self, view):
        self.stats_view = view
        self.equip_mouseover = 0
        self.quest_mouseover = 0
        if view == 2:
            self.draw_quests(True)
        self.stats_dirty = True

    def draw_skills(self):
        self.stats_dirty = True

    def draw_quests(self, reload):
        if reload or not self.help_quests:
            self.help_load_quests()
        self.stats_dirty = True

    def draw_stats_panel(self):
        surf = self.stats_surface
        sp = self.assets.get("StatBox")
        if sp:
            surf.blit(sp.full, (0, 0))
        else:
            surf.fill((51, 34, 27))
        if self.stats_view == 1:
            self.draw_equipment_tab(surf)
        elif self.stats_view == 2:
            self.draw_quests_tab(surf)
        else:
            self.draw_skills_tab(surf)
        self.draw_stats_tabs(surf)
        self.stats_dirty = False

    def draw_stats_tabs(self, surf):
        pygame.draw.rect(surf, (51, 31, 25), (28, 13, 170, 27))
        for t, (x1, x2, label) in enumerate(((31, 81, "Stats"), (84, 135, "Gear"), (138, 194, "Quests"))):
            if t == self.stats_view:
                fill, text = (126, 77, 63), TAB_TEXT
            else:
                fill, text = (61, 40, 31), (190, 160, 110)
            pygame.draw.rect(surf, fill, (x1, 15, x2 - x1 + 1, 22))
            pygame.draw.rect(surf, (126, 77, 63), (x1, 15, x2 - x1 + 1, 22), 1)

    def draw_stats_tab_labels(self, scr):
        """The tabs' names, over the stats panel (crisp: see crisp_label)."""
        for t, (x1, x2, label) in enumerate(((31, 81, "Stats"), (84, 135, "Gear"), (138, 194, "Quests"))):
            text = TAB_TEXT if t == self.stats_view else (190, 160, 110)
            self.crisp_label(scr, label, self.view_w + x1, self.statbar_y + 15, x2 - x1 + 1, 22, 9, True, text)

    def draw_skills_tab(self, surf):
        skills = sum(1 for i in range(1, self.total_skills + 1) if self.skill_shown(i))
        self.stat_rows = 1 + int((skills + 2) / 3)          # hitpoints and mana share the first row, two wide boxes
        self.stat_row_top = 41
        self.stat_row_height = min(33, int(130 / self.stat_rows))
        hp = self.player.hp
        hp_c = (21, 171, 75)
        if hp < self.player_max_hp * 0.66:
            hp_c = (230, 150, 40)
        if hp < self.player_max_hp * 0.33:
            hp_c = (230, 60, 40)
        hp_progress = 100 * hp / max(1, self.player_max_hp)
        self.draw_skill_tile(surf, 0, self.config_skill_icon("Hitpoints"), "%d/%d" % (hp, self.player_max_hp), hp_c,
                             hp_progress)
        self.draw_skill_tile(surf, 1, "Mana", "%d/%d" % (int(self.player_mana), self.player_max_mana), (140, 180, 255),
                             100 * self.player_mana / max(1, self.player_max_mana))
        k = 1
        for i in range(1, self.total_skills + 1):
            if self.skill_shown(i):
                k += 1
                level = self.level_of_xp(self.skill_xp[i])
                c = (255, 215, 60) if level >= self.skill_max_level else TAB_TEXT
                self.draw_skill_tile(surf, k, self.config_skill_icon(self.skill_name[i]), str(level), c,
                                     self.level_progress(self.skill_xp[i]))

    def stat_tile_rect(self, k):
        """(x, y, w) of stat box k in the stats panel: 0 hitpoints and 1 mana, side by side on the first row; then
        the skills, three to a row."""
        if k < 2:
            return 29 + k * 84, self.stat_row_top, 82
        j = k - 2
        return 29 + (j % 3) * 56, self.stat_row_top + (1 + int(j / 3)) * self.stat_row_height, 54

    def stat_tile_at(self, px, py):
        """The stat box under panel pixel px,py (-1 = none)."""
        if self.stat_row_height <= 0:
            return -1
        for k in range(2 + 3 * max(0, self.stat_rows - 1)):
            x, y, w = self.stat_tile_rect(k)
            if x <= px < x + w and y <= py < y + self.stat_row_height:
                return k
        return -1

    def draw_skill_tile(self, surf, k, icon, value, value_colour, progress):
        x, y, w = self.stat_tile_rect(k)
        h = self.stat_row_height - 2
        icon_size = min(24, h - 4)
        self.round_box(surf, (x, y, w, h), (40, 26, 20), (126, 77, 63), 1, 6)
        if self.assets.loaded(icon):
            self.draw_icon(surf, icon, x + 3, y + int((h - icon_size) / 2), icon_size)
        main, small = value, ""
        if "/" in value:
            main, small = value.split("/", 1)
            small = "/" + small
        bar_y = y + h - 4
        # The numbers go between the box's top edge and the progress bar, beside the icon, laid out by where their
        # digits really are (so "38" over "/38" stays inside however short the rows are)
        top, bottom = y + 3, bar_y - 1
        left, right = x + icon_size + 4, x + w - 2
        xm = (left + right) / 2
        if small == "":
            size = 10
            while size > 7 and self.text_width(main, size, True) > right - left:
                size -= 1
            self.centred_mid(surf, xm, top, bottom - top, main, size, True, value_colour)
        else:
            big, little = (10, 8) if w > 60 else (9, 7)
            while big > 6 and (self.cap_metrics(big, True)[1] + self.cap_metrics(little, True)[1] + 2 > bottom - top or
                               max(self.text_width(main, big, True), self.text_width(small, little, True)) > right - left):
                big -= 1
                little = max(6, little - 1) if big < 8 else little
            main_h = self.cap_metrics(big, True)[1]
            small_h = self.cap_metrics(little, True)[1]
            gap = max(1, min(3, (bottom - top) - main_h - small_h))
            y0 = top + int(((bottom - top) - (main_h + gap + small_h)) / 2)
            self.centred_mid(surf, xm, y0, main_h, main, big, True, value_colour)
            self.centred_mid(surf, xm, y0 + main_h + gap, small_h, small, little, True, (212, 191, 126))
        bar_x, bar_len = x + icon_size + 5, w - icon_size - 8
        bar_w = int(bar_len * min(100, max(0, progress)) / 100)
        pygame.draw.rect(surf, (25, 16, 12), (bar_x, bar_y, bar_len, 2))
        if bar_w > 0:
            c = (255, 215, 60) if progress >= 100 else (21, 171, 75)
            if icon == "Mana":
                c = (80, 140, 255)
            pygame.draw.rect(surf, c, (bar_x, bar_y, bar_w, 2))

    # What each empty Gear slot shows, engraved (as on the old armour window): a typical item's outline
    SLOT_OUTLINES = {"Weapon": "Iron_Sword", "Shield": "Iron_Shield", "Head": "Iron_Helm", "Body": "Iron_Platebody",
                     "Legs": "Iron_Platelegs", "Feet": "Iron_Boots", "Hands": "Iron_Gauntlets", "Ring": "Gold_Ring"}

    def draw_equipment_tab(self, surf):
        box = self.EQUIP_BOX
        link = (30, 19, 15)
        for a, b in ((3, 4), (4, 5), (5, 6), (1, 4), (4, 2), (7, 5), (5, 8)):     # the joints between the slots
            ax, ay, bx, by = self.equip_slot_x(a), self.equip_slot_y(a), self.equip_slot_x(b), self.equip_slot_y(b)
            if ax == bx:
                self.round_box(surf, (ax + box // 2 - 3, ay + box, 6, by - ay - box), link, None, 0, 0)
            else:
                self.round_box(surf, (ax + box, ay + box // 2 - 3, bx - ax - box, 6), link, None, 0, 0)
        for s in range(1, self.equip_slots + 1):
            x, y = self.equip_slot_x(s), self.equip_slot_y(s)
            item = self.equipped[s]
            hot = s == self.equip_mouseover
            border = (250, 220, 140) if hot else (176, 120, 80) if item else (110, 74, 58)
            self.round_box(surf, (x, y, box, box), (58, 38, 30) if hot else (40, 26, 20), border, 1, 8)
            if item:
                if self.assets.loaded(item):
                    self.draw_icon(surf, item, x + 1, y + 1, box - 2)
                else:
                    self.centre_text(surf, x + box // 2, y + 10, self.fit_text(pretty(item), box - 2, 6), 6, False,
                                     (200, 180, 140))
                self.draw_wear_bar(surf, item, self.equip_wear[s], x + 1, y + 1, box - 2)
            else:                                   # engraved: a light edge under a dark outline
                outline = self.SLOT_OUTLINES.get(self.equip_slot_names[s])
                self.draw_icon(surf, outline, x + 3, y + 4, box - 6, (18, 11, 8))
                self.draw_icon(surf, outline, x + 3, y + 3, box - 6, (150, 112, 82))
        # the bonuses, in the corners beside the head (and the magic one beside the feet)
        totals = [(63, 44, "Attack", self.equip_attack_total), (163, 44, "Defence", self.equip_defence_total)]
        if self.equip_magic_total > 0:
            totals.append((63, 139, "Magic", self.equip_magic_total))
        for xm, y, label, value in totals:
            self.centre_text(surf, xm, y, label, 7, True, (190, 160, 110))
            self.centre_text(surf, xm, y + 10, "+" + lbstr(value), 11, True, TAB_TEXT)

    def draw_quests_tab(self, surf):
        total = len(self.help_quests)
        self.quests_pages = max(1, int((total + self.quests_per_page - 1) / self.quests_per_page))
        self.quests_page = min(self.quests_pages, max(1, self.quests_page))
        first = (self.quests_page - 1) * self.quests_per_page
        if total == 0:
            self.centre_text(surf, 112, 90, "No quests yet.", 7, True, (212, 191, 126))
            self.centre_text(surf, 112, 104, "Talk to people: some will need your help.", 7, True, (170, 150, 120))
            return
        summary = "Level %d  -  %d/%d done" % (self.player_level(), self.help_quest_done, total)
        self.draw_text(surf, self.fit_text(summary, 108, 7, True), 34, 43, 7, True, (212, 191, 126))
        if self.quests_pages > 1:
            on, off = TAB_TEXT, (96, 70, 56)
            self.round_box(surf, (147, 43, 12, 12), on if self.quests_page > 1 else off, None, 0, 4)
            self.round_box(surf, (183, 43, 12, 12), on if self.quests_page < self.quests_pages else off, None, 0, 4)
            self.centre_text(surf, 153, 42, "<", 7, True, (51, 31, 25))
            self.centre_text(surf, 189, 42, ">", 7, True, (51, 31, 25))
            self.centre_text(surf, 171, 43, "%d/%d" % (self.quests_page, self.quests_pages), 7, True, (212, 191, 126))
        for row in range(1, self.quests_per_page + 1):
            k = first + row
            if k > total:
                break
            q = self.help_quests[self.help_quest_order[k - 1]]
            y = self.quest_row_top + (row - 1) * self.quest_row_height
            # gold = in progress, green (crossed out) = complete, blue = you can start it, a padlock = locked
            # (screens.quest_look)
            c, _ = self.quest_look(q)
            dot = {0: (240, 190, 50), 2: (70, 170, 80)}.get(q["status"], (70, 160, 205))
            if row == self.quest_mouseover:
                self.round_box(surf, (30, y, 165, self.quest_row_height - 1), (74, 48, 38), c, 1, 6)
            if q.get("needs"):                      # locked: a padlock (gold for the main story)
                self.draw_padlock(surf, 39, y + 8, (210, 170, 80) if q.get("main") else c)
            elif q.get("main"):                     # the main story: a diamond, not a dot
                pts = [(39, y + 3), (44, y + 8), (39, y + 13), (34, y + 8)]
                pygame.draw.polygon(surf, dot, pts)
                pygame.draw.polygon(surf, (255, 220, 110), pts, 1)
            else:
                pygame.draw.circle(surf, dot, (39, y + 8), 4)
                pygame.draw.circle(surf, (30, 20, 16), (39, y + 8), 5, 1)
            if q["status"] == 2:                    # a tick in the green dot
                pygame.draw.lines(surf, (230, 250, 220), False, [(37, y + 8), (38, y + 9), (41, y + 6)], 1)
            title = self.fit_text(q["title"], 142, 8, True)
            tw = self.draw_text(surf, title, 49, y + 1, 8, True, c)
            if q["status"] == 2:
                cap_top, cap_h = self.cap_metrics(8, True)
                my = y + 1 + cap_top + int(cap_h / 2) + 1
                pygame.draw.line(surf, (100, 150, 90), (48, my), (50 + tw, my), 1)

    def quest_hover(self, q):
        status = {0: "In progress", 2: "Complete"}.get(q["status"], "You can start this now")
        if q.get("needs"):
            status = self.quest_needs_text(q)
        text = q["title"] + ("  (main story)" if q.get("main") else "") + "|" + status
        if q["giver"]:
            text += " - " + pretty(q["giver"])
        from .lb import wrap_text
        return text + "|" + wrap_text(q["text"], 44) + "|(click: open the journal)"

    # ----- Going up a level: a banner across the view ("LEVEL UP!", the skill's icon and its new level) and rings of
    # light bursting out round the player. Several at once share the banner.
    LEVEL_BANNER_MS = 3400

    def level_up_show(self, skill, level):
        now = self.loop_start
        b = getattr(self, "level_banner", None)
        if b and now - b["start"] < self.LEVEL_BANNER_MS - 800:
            b["skills"] = [s for s in b["skills"] if s[0] != skill] + [(skill, level)]
            b["start"] = max(b["start"], now - 300)
        else:
            self.level_banner = {"start": now, "skills": [(skill, level)]}
        self.level_burst_start = now

    def draw_level_burst(self, surf, cam_x, cam_y):
        start = getattr(self, "level_burst_start", None)
        if start is None:
            return
        t = self.loop_start - start
        if not 0 <= t < 1400:
            self.level_burst_start = None
            return
        p = self.player
        cx, cy = int(p.cx - cam_x), int(p.cy - cam_y)
        glow = pygame.Surface((180, 180), pygame.SRCALPHA)
        for k in range(3):                              # three rings, one after another, fading as they grow
            tt = t - k * 220
            if not 0 <= tt < 900:
                continue
            f = tt / 900.0
            r = int(14 + 70 * f)
            a = int(230 * (1 - f))
            pygame.draw.circle(glow, (255, 214, 92, a), (90, 90), r, max(2, int(6 * (1 - f))))
        if t < 700:                                     # a soft gold light on the player
            pygame.draw.circle(glow, (255, 236, 160, int(110 * (1 - t / 700.0))), (90, 90), 26)
        for k in range(10):                             # sparks rising
            f = ((t + k * 97) % 1100) / 1100.0
            if t + k * 97 > 1400:
                continue
            sx = 90 + int(30 * math.sin(k * 2.4)) + int(6 * math.sin(f * 9 + k))
            sy = 100 - int(80 * f)
            pygame.draw.circle(glow, (255, 240, 170, int(220 * (1 - f))), (sx, sy), 2)
        surf.blit(glow, (cx - 90, cy - 90))

    def draw_level_banner(self, surf, sw, sh):
        b = getattr(self, "level_banner", None)
        if not b:
            return
        t = self.loop_start - b["start"]
        if not 0 <= t < self.LEVEL_BANNER_MS:
            self.level_banner = None
            return
        alpha = min(1.0, t / 220.0, (self.LEVEL_BANNER_MS - t) / 650.0)
        drop = int(18 * max(0.0, 1 - t / 260.0))       # it drops in a little
        skills = b["skills"]
        lines = ["%s %d" % (s, lv) for s, lv in skills]
        sub_text = ("Your %s level is now %d!" % skills[0]) if len(skills) == 1 else "   ·   ".join(lines)
        w = max(360, self.text_width(sub_text, 16, True) + 120)
        h = 96
        x0, y0 = (sw - w) // 2, int(sh * 0.2) - drop
        band = pygame.Surface((w, h), pygame.SRCALPHA)
        band.fill((24, 14, 8, 200))
        pygame.draw.rect(band, (214, 170, 70, 255), (0, 0, w, h), 2)
        pygame.draw.rect(band, (120, 84, 30, 255), (4, 4, w - 8, h - 8), 1)
        shine = int(w * ((t % 1600) / 1600.0))          # a glint running along the top edge
        pygame.draw.line(band, (255, 240, 180, 255), (max(2, shine - 40), 2), (min(w - 3, shine), 2), 2)
        title = "LEVEL UP!"
        tw = self.text_width(title, 30, True)
        for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2), (2, 2)):
            self.draw_text(band, title, (w - tw) // 2 + dx, 10 + dy, 30, True, "40 22 8")
        self.draw_text(band, title, (w - tw) // 2, 10, 30, True, "255 214 92")
        icon = self.config_skill_icon(skills[-1][0])
        if icon:
            self.draw_icon(band, icon, 16, (h - 40) // 2, 40)
            self.draw_icon(band, icon, w - 56, (h - 40) // 2, 40)
        stw = self.text_width(sub_text, 16, True)
        self.draw_text(band, sub_text, (w - stw) // 2 + 1, 58 + 1, 16, True, "20 10 4")
        self.draw_text(band, sub_text, (w - stw) // 2, 58, 16, True, "246 232 196")
        band.set_alpha(int(255 * alpha))
        surf.blit(band, (x0, y0))

    def config_skill_icon(self, skill):
        return trim(self.config_read("Skills", "Icon." + skill, ""))

    # =================================================================================================================
    # Drawing a frame
    # =================================================================================================================
    def sprite_of(self, name):
        sp = self.assets.get(name)
        if sp is None:
            sp = self.assets.get(self.fallback_sprite())
        return sp

    def render(self):
        scr = self.screen
        scr.fill((0, 0, 0))
        sw, sh = self.view_w, self.view_h
        cam_x, cam_y = int(self.cam_x), int(self.cam_y)
        pick = []
        # ----- The world, drawn at 1:1 on the world canvas, then scaled to the playfield (the zoom)
        screen = scr
        scr = self.world_surf
        scr.fill((0, 0, 0))
        sw, sh = self.world_w, self.world_h
        if self.ground_ready:
            src = pygame.Rect(cam_x - self.ground_ox, cam_y - self.ground_oy, sw, sh)
            part = src.clip(self.ground.get_rect())
            if part.w > 0 and part.h > 0:
                scr.blit(self.ground, (part.x - src.x, part.y - src.y), part)
        world = self.world
        for e in world:
            if e.active and e.ai is not None and e.ai.under:
                self.draw_entity(scr, e, cam_x, cam_y, pick)
        for e in world:
            if e.type == MAPITEM and e.active:
                self.draw_entity(scr, e, cam_x, cam_y, pick)
        # Objects, the player and the people and monsters are drawn by how far down the screen their feet are, so
        # whoever stands in front is drawn in front
        p = self.player
        standing = [e for e in world if e.active and (e.type == STATICOBJECT or (
            e.type == NPC and not (e.ai is not None and e.ai.under)))]
        if self.player_visible:
            standing.append(p)
        standing.sort(key=lambda e: e.y + e.h)
        for e in standing:
            if e is p:
                self.draw_player(scr, cam_x, cam_y)
            else:
                self.draw_entity(scr, e, cam_x, cam_y, pick)
        for e in world:
            if e.type in (MISSILE, TEMPORARY) and e.active:
                self.draw_entity(scr, e, cam_x, cam_y, pick)
        self.draw_infront_tiles(scr, cam_x, cam_y, pick)
        self.draw_weather(scr, cam_x, cam_y)            # rain, snow, fog, lightning (weather.py)
        self.draw_sky(scr, cam_x, cam_y)                # dawn, evening, night and the lights (daynight.py)
        if self.fog_enabled and self.ground_ready:
            self.draw_fog(scr, cam_x, cam_y)
        for f in self.fx:
            if f.kind in (1, 2, 3, 6):
                sp = self.assets.get(f.image)
                if sp:
                    y = f.draw_y if f.kind == 1 else f.y
                    scr.blit(sp.flipped if f.mirror else sp.masked, (int(f.x) - cam_x, int(y) - cam_y))
        self.draw_status_icons(scr, cam_x, cam_y)
        if self.healthbars_available:
            for e in [p] + world:
                if e.show_bar:
                    img = self.assets.get(self.healthbar_image(e.hp, e.max_hp))
                    if img:
                        bx = int(e.x + (e.w - 26) / 2) - cam_x
                        by = int(e.y - 12) - cam_y
                        scr.blit(img.masked, (bx, by))
        self.draw_level_burst(scr, cam_x, cam_y)
        scr = screen
        sw, sh = self.view_w, self.view_h
        if self.zoom == 1:
            scr.blit(self.world_surf, (0, 0))
        elif self.zoom == int(self.zoom):
            scr.blit(pygame.transform.scale(self.world_surf, (sw, sh)), (0, 0))
        else:
            scr.blit(pygame.transform.smoothscale(self.world_surf, (sw, sh)), (0, 0))
        self.pick_world = pick
        pick = []
        scr.set_clip((0, 0, sw, sh))
        for f in self.fx:
            if f.kind == 5:
                img = self.hurt_strip(f.image)
                if img is not None:
                    scr.blit(img, (f.x, f.y))
        self.draw_hotbar(scr)
        self.draw_level_banner(scr, sw, sh)
        scr.set_clip(None)
        # ----- The sidebar: the minimap shows through its circle
        if self.minimap_available:
            scr.blit(self.minimap_view, self.minimap_view_pos)
        sb = self.assets.get("SideBar")
        if sb:
            scr.blit(sb.masked, (sw, 0))
        mm = self.assets.get("MinimapMarker")
        if self.minimap_available:
            if mm:
                scr.blit(mm.masked, (self.minimap_centre_x - 4, self.minimap_centre_y - 4))
            else:
                pygame.draw.circle(scr, (255, 255, 255), (self.minimap_centre_x, self.minimap_centre_y), 4)
                pygame.draw.circle(scr, (220, 30, 30), (self.minimap_centre_x, self.minimap_centre_y), 2)
        self.draw_clock(scr)
        self.draw_sidebar_button(scr, self.help_button_x(), self.help_button_y(), "? Help", self.help_button_hot,
                                 ((126, 77, 63), (160, 104, 80)), ((243, 232, 136), (255, 255, 255)), (77, 43, 33))
        if self.admin_enabled:
            self.draw_sidebar_button(scr, self.help_button_x(), self.help_button_y() + 26, "Admin",
                                     self.admin_button_hot, ((48, 76, 104), (70, 110, 150)),
                                     ((210, 230, 250), (255, 255, 255)), (30, 40, 60))
        border = self.assets.get("SideBarBorder")
        if border:
            scr.blit(border.full, (sw, 0), (0, 0, border.w, sh))
        if self.stats_dirty:
            self.draw_stats_panel()
        scr.blit(self.stats_surface, (sw, self.statbar_y))
        self.draw_stats_tab_labels(scr)
        # ----- The ActionBox, its items and the inventory
        if self.ab_mode and self.ab_surface is not None:
            scr.blit(self.ab_surface, (self.ab_x, self.ab_y))
            pick.append((pygame.Rect(self.ab_x, self.ab_y, self.ab_surface.get_width(), self.ab_surface.get_height()),
                         None))
            for e in self.ab_items:
                short = self.rack_level_short(e)            # a recipe above the player's level: greyed, its level
                lacking = self.rack_missing(e) if self.ab_mode == "Craft" else ""    # or without the materials
                self.draw_slot_item(scr, e, int(e.x), int(e.y), e.qty_text, pick, dim=short > 0,
                                    badge="Lv%d" % short if short else "", cross=bool(short or lacking))
        shop = self.ab_mode == "Shop"
        for n, e in enumerate(self.inv):
            x, y = self.inventory_slot_pos(n)
            e.x, e.y = x, y
            self.draw_slot_item(scr, e, x, y, lbstr(e.quantity), pick,
                                dim=shop and not self.can_sell_here(e.name))   # what this shop won't buy: greyed
        if self.ab_mode and self.rb_surface is not None:
            scr.blit(self.rb_surface, (self.rb_x - 1, self.rb_y))
        self.pick_list = pick
        # ----- The chat bar and the hover box
        if self.chat_dirty:
            self.redraw_chat_bar()
        scr.blit(self.chat_surface, (0, sh))
        self.draw_scroll_thumb(scr, self.chat_thumb(), self.scroll_drag == "chat")
        if self.rack_track() is not None and self.ab_surface is not None:
            self.draw_scroll_thumb(scr, self.rack_thumb(), self.scroll_drag == "rack")
        if self.infobox_open and self.infobox_surface is not None:
            scr.blit(self.infobox_surface, (self.infobox_x, self.infobox_y))
        if self.item_in_use is not None and self.item_in_use in self.inv:
            n = self.inv.index(self.item_in_use)
            x, y = self.inventory_slot_pos(n)
            pygame.draw.rect(scr, (243, 232, 136), (x - 1, y - 1, self.tw + 2, self.th + 2), 1)
        self.draw_sidebar_quest_popup(scr)
        if self.rcm_open:
            self.draw_right_click_menu(scr)
        if self.admin_open:
            self.draw_admin(scr)
        if self.quit_dialog_open:
            self.draw_quit_dialog(scr)
        if self.options_open:
            self.draw_options_dialog(scr)

    def draw_night(self, scr, cam_x, cam_y):
        """Night: dark blue over the world, with a soft circle of light round the player (Config [Gameplay]
        Night.Light.Radius, 0 = none)."""
        night = self.night_layer
        night.fill((10, 12, 40, self.night_alpha))
        if self.light_mask is not None:
            r = self.light_mask.get_width() // 2
            night.blit(self.light_mask, (int(self.player.cx) - cam_x - r, int(self.player.cy) - cam_y - r),
                       special_flags=pygame.BLEND_RGBA_MULT)
        scr.blit(night, (0, 0))

    def draw_player(self, scr, cam_x, cam_y):
        """The player and what they wear (Sprites\\Worn), which takes the same walking step."""
        p = self.player
        sp = self.sprite_of(p.image)
        if not sp:
            return
        px = int(p.x) - cam_x + p.nudge_x
        py = int(p.y) - cam_y + p.nudge_y
        scr.blit(sp.masked, (px, py))
        suffix = p.image[-2:] if len(p.image) >= 2 else "4a"
        if suffix[:1] not in "1248" or len(suffix) != 2:
            suffix = "4a"
        for item in self.worn_items():
            g = self.assets.get("Worn_" + item + suffix)
            if g:
                scr.blit(g.masked, (px, py))

    def hurt_strip(self, name):
        """The red hurt flash strips, stretched to the playfield (the pictures were made for an 800 x 672 one)."""
        key = ("hurt", name, self.view_w, self.view_h)
        img = self.icon_cache.get(key)
        if img is None:
            sp = self.assets.get(name)
            if sp is None:
                return None
            if name in ("Hurt_Top", "Hurt_Bottom"):
                img = pygame.transform.scale(sp.masked, (self.view_w, sp.h))
            else:
                img = pygame.transform.scale(sp.masked, (sp.w, self.view_h))
            self.icon_cache[key] = img
        return img

    # ----- Scroll bars on the chat bar and the item racks (shops, bank, crafting): a thumb in the dark track between
    # the arrows shows where you are; click the track to jump there or drag the thumb
    def chat_track(self):
        return pygame.Rect(780 + self.ui_dx, self.view_h + 19, 15, 60)

    def rack_track(self):
        if self.ab_mode in ("", "Conversation"):
            return None
        return pygame.Rect(self.ab_x + 409, self.ab_y + 60, 15, 89)

    def chat_scroll_range(self):
        """(lines scrolled back, the most it can be)"""
        most = max(0, len(self.message_log) - 5)
        return min(self.chat_line - 1, most), most

    def rack_page_range(self):
        return self.rack_page, max(1, getattr(self, "rack_pages", 1))

    @staticmethod
    def thumb_rect(track, shown, total, pos, last):
        """The thumb in track: shown of total visible, at pos of 0..last (0 = top)."""
        h = track.h if total <= shown or last <= 0 else max(10, int(track.h * shown / total))
        frac = 0 if last <= 0 else pos / last
        return pygame.Rect(track.x + 2, track.y + int((track.h - h) * frac), track.w - 4, h)

    def chat_thumb(self):
        back, most = self.chat_scroll_range()
        return self.thumb_rect(self.chat_track(), 5, len(self.message_log), most - back, most)

    def rack_thumb(self):
        page, pages = self.rack_page_range()
        return self.thumb_rect(self.rack_track(), 1, pages, page - 1, pages - 1)

    def draw_scroll_thumb(self, scr, rect, hot):
        self.round_box(scr, rect, (190, 132, 88) if hot else (174, 118, 79), (102, 30, 21), 1, 6)
        cx = rect.centerx
        for dy in (-3, 0, 3):  # Grip lines
            y = rect.centery + dy
            if rect.top + 3 < y < rect.bottom - 3:
                pygame.draw.line(scr, (102, 30, 21), (cx - 3, y), (cx + 3, y))

    def scroll_to(self, which, y):
        """Moves the chat or the rack so its thumb is centred at screen y."""
        if which == "chat":
            track, thumb = self.chat_track(), self.chat_thumb()
            back, most = self.chat_scroll_range()
            if most <= 0:
                return
            frac = min(1, max(0, (y - track.y - thumb.h / 2) / max(1, track.h - thumb.h)))
            self.chat_line = 1 + int(round((1 - frac) * most))
            self.chat_dirty = True
        elif which == "rack" and self.rack_track() is not None:
            track, thumb = self.rack_track(), self.rack_thumb()
            page, pages = self.rack_page_range()
            if pages <= 1:
                return
            frac = min(1, max(0, (y - track.y - thumb.h / 2) / max(1, track.h - thumb.h)))
            new = 1 + int(round(frac * (pages - 1)))
            if new != page:
                self.rack_page = new
                self.show_rack_page(False)

    def scroll_bar_click(self):
        """A left click on a scroll bar's track starts dragging it. True if it was one."""
        pos = (self.cursor_x, self.cursor_y)
        if self.chat_track().collidepoint(pos):
            self.scroll_drag = "chat"
        elif self.rack_track() is not None and self.rack_track().collidepoint(pos):
            self.scroll_drag = "rack"
        else:
            return False
        self.scroll_to(self.scroll_drag, self.cursor_y)
        return True

    def update_scroll_drag(self):
        if not self.scroll_drag:
            return
        if not pygame.mouse.get_pressed()[0]:
            self.scroll_drag = ""
            return
        self.scroll_to(self.scroll_drag, self.cursor_y)

    def scroll_wheel(self):
        """The mouse wheel over the chat or a rack scrolls it. True if it did."""
        if not self.mouse_wheel:
            return False
        pos = (self.cursor_x, self.cursor_y)
        if self.cursor_y >= self.view_h and self.cursor_x < self.view_w + 4:
            self.scroll_message_display(1 if self.mouse_wheel > 0 else -1)
            return True
        if self.ab_mode not in ("", "Conversation") and self.ab_surface is not None:
            box = pygame.Rect(self.ab_x, self.ab_y, self.ab_surface.get_width(), self.ab_surface.get_height())
            if box.collidepoint(pos):
                page, pages = self.rack_page_range()
                new = min(pages, max(1, page + (-1 if self.mouse_wheel > 0 else 1)))
                if new != page:
                    self.rack_page = new
                    self.show_rack_page(False)
                return True
        return False

    def make_chat_background(self):
        """The ChatBar picture as wide as the window: the parchment is stretched, the scroll arrows and the hover box
        stay at its right-hand end (under the sidebar)."""
        sp = self.assets.get("ChatBar")
        surf = pygame.Surface((self.win_w, 96)).convert()
        surf.fill((212, 191, 126))
        if sp is None:
            return surf
        img = sp.full
        dx = max(0, self.ui_dx)
        if dx == 0:
            surf.blit(img, (0, 0))
        else:
            surf.blit(img, (0, 0), (0, 0, 10, 96))
            middle = img.subsurface((10, 0, 760, 96))
            surf.blit(pygame.transform.scale(middle, (760 + dx, 96)), (10, 0))
            surf.blit(img, (770 + dx, 0), (770, 0, 254, 96))
        # The hover box's parchment has its gold edge on the sides and bottom but not along the top, where it met
        # the sidebar's planks with no seam: a dark line and the gold edge there too
        if img.get_width() >= 1000:
            x1, x2 = 827 + dx, 997 + dx
            pygame.draw.line(surf, (49, 28, 18), (x1 - 1, 0), (x2 + 1, 0))
            pygame.draw.line(surf, (243, 210, 129), (x1, 1), (x2 - 1, 1))
            pygame.draw.line(surf, (183, 139, 60), (x2, 1), (x2, 1))
        return surf

    def idle_frames(self, name):
        """(frames, ms per frame) of an object that animates where it stands: Entities.ini Anim.Frames=N (sprites
        <Name>1..<Name>N in Sprites\\Entities) and Anim.Speed (ms, default 200). (1, 0) = it doesn't."""
        cache = self.__dict__.setdefault("idle_cache", {})
        if name not in cache:
            n = val(self.entity_ini(name, "Anim.Frames", "0"))
            ms = max(30, val(self.entity_ini(name, "Anim.Speed", "200")))
            if n > 1 and all(self.assets.loaded("%s%d" % (name, k)) or self.assets.load_if_exists("Entities", "%s%d" % (name, k))
                             for k in range(1, n + 1)):
                cache[name] = (n, ms)
            else:
                cache[name] = (1, 0)
        return cache[name]

    def draw_entity(self, scr, e, cam_x, cam_y, pick):
        image = e.image or e.name
        if e.type == STATICOBJECT:
            n, ms = self.idle_frames(e.name)
            if n > 1:                                   # each one a little out of step with its neighbours
                image = "%s%d" % (e.name, (int(self.loop_start // ms) + e.uid * 3) % n + 1)
        sp = self.sprite_of(image)
        if sp is None:
            return
        x = int(e.x) - cam_x + e.nudge_x
        y = int(e.y) - cam_y + e.nudge_y
        pic = sp.masked
        if e.type == STATICOBJECT and self.is_decor_object(e.name):  # a decor tile placed as an object: it sways or
            kind = self.decor_anim_kind(e.name)                      # flickers as it does on the decor layer
            if kind == "sway":
                frames = self.decor_sway_frames(e.name)
                if frames:
                    pic = frames[self.anim_frame("sway", int(e.x // self.tw))]
            elif kind == "flame":
                pic = self.flame_frame(e.name, self.anim_frame("flame"), see_through=True) or pic
        scr.blit(pic, (x, y))
        pick.append((pygame.Rect(x, y, sp.w, sp.h), e))

    def draw_infront_tiles(self, scr, cam_x, cam_y, pick):
        """Tree tops (Infront overlays) go over the entities (the fog, drawn over them, dims them); only the current
        map's, out of the fog, can be clicked."""
        tw, th = self.tw, self.th
        wx1 = int((cam_x - self.ground_ox) // tw) + 1
        wy1 = int((cam_y - self.ground_oy) // th) + 1
        wx2 = int((cam_x + self.world_w - 1 - self.ground_ox) // tw) + 1
        wy2 = int((cam_y + self.world_h - 1 - self.ground_oy) // th) + 1
        for wy in range(max(1, wy1), min(3 * self.yt, wy2) + 1):
            for wx in range(max(1, wx1), min(3 * self.xt, wx2) + 1):
                f = self.w_find(wx, wy)
                if f is None:
                    continue
                st, c = f
                name = st.infront[c]
                if not name:
                    continue
                x = (wx - 1) * tw + self.ground_ox
                y = (wy - 1) * th + self.ground_oy
                sp = self.assets.get(name)
                if sp is None:
                    continue
                scr.blit(sp.masked, (x - cam_x, y - cam_y))
                if st is self.store[5] and not self.fog_covers(x + tw / 2, y + th / 2):
                    e = self.infront_ents.get((wx - self.xt, wy - self.yt))
                    if e is not None:
                        pick.append((pygame.Rect(x - cam_x, y - cam_y, tw, th), e))

    def greyed(self, sp):
        """A sprite washed out to grey and darkened (cached): an item you can't use here."""
        cache = self.__dict__.setdefault("grey_cache", {})
        key = id(sp)
        if key not in cache:
            img = sp.masked.copy()
            try:
                import pygame.surfarray as sa
                rgb = sa.pixels3d(img)
                lum = (rgb[:, :, 0] * 0.3 + rgb[:, :, 1] * 0.59 + rgb[:, :, 2] * 0.11) * 0.55 + 20
                for c in range(3):
                    rgb[:, :, c] = lum.astype(rgb.dtype)
                del rgb
            except Exception:
                img.fill((90, 90, 90), special_flags=pygame.BLEND_RGB_MULT)
            cache[key] = img
        return cache[key]

    def draw_wear_bar(self, scr, name, wear, x, y, w):
        """A thin bar along the bottom of a worn weapon or armour: green to red as it wears, empty when broken."""
        m = self.item_max_dur(name)
        if m <= 0 or wear <= 0:
            return
        k = max(0.0, (m - wear) / float(m))
        col = (int(220 - 160 * k), int(60 + 150 * k), 40) if k > 0 else (200, 30, 30)
        pygame.draw.rect(scr, (24, 14, 10), (x + 3, y + w - 5, w - 6, 3))
        if k > 0:
            pygame.draw.rect(scr, col, (x + 3, y + w - 5, max(1, int((w - 6) * k)), 3))
        else:
            pygame.draw.rect(scr, col, (x + 3, y + w - 5, w - 6, 1))

    def draw_slot_item(self, scr, e, x, y, qty, pick, dim=False, badge="", cross=False):
        sp = self.sprite_of(e.image or e.name)
        broken = e.type == INVENTORYITEM and self.is_broken(e.name, getattr(e, "wear", 0))
        if sp:
            scr.blit(self.greyed(sp) if (dim or broken) else sp.masked, (x, y))
            pick.append((pygame.Rect(x, y, sp.w, sp.h), e))
        if e.type == INVENTORYITEM:
            self.draw_wear_bar(scr, e.name, getattr(e, "wear", 0), x, y, self.tw)
        if cross:                                           # can't make it (level or materials): a small red cross in
            x0, y0, s = x + self.tw - 11, y + 1, 8          # the top right corner, the picture still showing
            for col, w in (((40, 8, 6), 4), ((214, 40, 32), 2)):
                pygame.draw.line(scr, col, (x0, y0), (x0 + s, y0 + s), w)
                pygame.draw.line(scr, col, (x0 + s, y0), (x0, y0 + s), w)
        if badge:                                           # e.g. the level a recipe needs, along the bottom
            w = self.text_width(badge, 7, True) + 4
            bx, by = x + self.tw - w, y + self.th - 10
            pygame.draw.rect(scr, (60, 18, 14), (bx, by, w, 10))
            self.draw_text(scr, badge, bx + 2, by, 7, True, (255, 150, 120))
        if qty not in ("1", ""):
            text = qty
            if qty != "+":
                q = val(qty)
                if q >= 100000:
                    text = "%dK" % int(q / 1000)
                if q >= 10000000:
                    text = "%dM" % int(q / 1000000)
            dx = x
            for ch in text:
                if ch in "KM":
                    ch = "+"
                d = self.assets.get("InterfaceNumber" + ch)
                if d:
                    scr.blit(d.masked, (dx, y + 2))
                    dx += d.w + 1

    def draw_sidebar_button(self, scr, x, y, label, hot, fills, inks, edge):
        w, h = 52, 22
        self.round_box(scr, (x, y, w, h), fills[1 if hot else 0], edge, 2, 10)
        self.crisp_label(scr, label, x, y, w, h, 9, True, inks[1 if hot else 0])

    def help_button_x(self):
        return self.view_w + 18

    def help_button_y(self):
        return 18

    def help_button_under_cursor(self):
        x, y = self.help_button_x(), self.help_button_y()
        return x <= self.cursor_x <= x + 52 and y <= self.cursor_y <= y + 22

    def admin_button_under_cursor(self):
        x, y = self.help_button_x(), self.help_button_y()
        return x <= self.cursor_x <= x + 52 and y + 26 <= self.cursor_y <= y + 48
