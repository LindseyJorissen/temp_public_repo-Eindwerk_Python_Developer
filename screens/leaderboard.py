"""
screens/leaderboard.py – Top scores display.

Page 0 – Bar Duty   (top_score_barduty.png)
Page 1 – Kitchen Duty (top_score_kitchenduty.png)

Left/right arrows switch pages; they only appear when BOTH Bar Duty and
Kitchen Duty endless modes are unlocked.  If only one duty has endless
unlocked the matching page is shown directly with no arrows.
"""

import os

from kivy.uix.floatlayout import FloatLayout
from kivy.uix.widget import Widget
from kivy.uix.label import Label
from kivy.graphics import Color, Rectangle, InstructionGroup
from kivy.core.image import Image as CoreImage

from game_constants import COLOR_BG, COLOR_BLACK, COLOR_YELLOW, OPPONENT_ORDER, DEBUG_HITBOXES
from game_utils import (
    get_current_player,
    load_scores_for_opponent,
    is_endless_unlocked,
    is_kitchen_endless_unlocked,
    fsp,
)
import audio_manager

_MAX_ENTRIES = 5   # rows per column

# ── Bar Duty column positions in source image pixels ──────────────────────────
_COL_PX         = [(452, 965), (1253, 880), (2043, 924), (2832, 1003)]
_COL_TITLE_PX   = [(452, 788), (1253, 703), (2043, 747), (2832, 826)]
_SCORES_STEP_PX = 142
_COL_TITLES     = ["EASY", "NORMAL", "HARD", "CHAOS"]
_BD_TITLE_PX    = (1300, 420)
_BD_TITLE_TEXT  = "BAR DUTY : CATCH THE GLASSES"

# ── Kitchen Duty score column in source image pixels ─────────────────────────
# Single centred column – tune these to fit top_score_kitchenduty.png
_KD_COL_PX      = (1957, 750)   # ← tune to art
_KD_TITLE_PX    = (1957, 560)   # ← tune to art
_KD_STEP_PX     = 150           # ← tune to art
_KD_TITLE_TEXT  = "KITCHEN DUTY : ENDLESS"
_KD_SCREEN_TITLE_PX = (1300, 420)  # ← tune to art

# ── Arrow button zones in source image pixels (left, top, right, bottom) ─────
_ZONE_LEFT_ARROW  = (60,  800, 310, 1020)   # ← tune to art
_ZONE_RIGHT_ARROW = (3605, 800, 3855, 1020) # ← tune to art

_ASSETS  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets")
_KB_DIR  = os.path.join(_ASSETS, "keyboard buttons")
_BD_BG   = os.path.join(_ASSETS, "screens", "top_score_barduty.png")
_KD_BG   = os.path.join(_ASSETS, "screens", "top_score_kitchenduty.png")
_FONT    = os.path.join(_ASSETS, "fonts", "Pixelfont.ttf")

_BG_W = 3915
_BG_H = 1773

_ZONE_BACK = (69, 1506, 501, 1713)

_KITCHEN_SCORE_PER_ORDER = 10   # keep in sync with game_constants


# ── Fill-width background ─────────────────────────────────────────────────────

class _FillWidthBg(Widget):
    def __init__(self, source, **kwargs):
        super().__init__(**kwargs)
        self._texture = None
        self._load(source)
        with self.canvas:
            Color(1, 1, 1, 1)
            self._rect = Rectangle()
        self.bind(pos=self._update, size=self._update)

    def _load(self, source):
        try:
            self._texture = CoreImage(source).texture
        except Exception:
            self._texture = None

    def set_source(self, source):
        self._load(source)
        self._update()

    def _update(self, *_):
        if not self._texture:
            return
        tw, th = self._texture.size
        w, h   = self.size
        if w == 0 or h == 0 or tw == 0 or th == 0:
            return
        scale    = w / tw
        scaled_h = th * scale
        self._rect.texture = self._texture
        if scaled_h >= h:
            crop_v = (scaled_h - h) / (2 * scaled_h)
            self._rect.tex_coords = (0.0, 1.0 - crop_v, 1.0, 1.0 - crop_v,
                                     1.0, crop_v,        0.0, crop_v)
            self._rect.pos  = self.pos
            self._rect.size = self.size
        else:
            ry = self.y + (h - scaled_h) / 2
            self._rect.tex_coords = (0.0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0)
            self._rect.pos  = (self.x, ry)
            self._rect.size = (w, scaled_h)


# ── Back button ───────────────────────────────────────────────────────────────

class _BackButton(Widget):
    def __init__(self, callback, **kwargs):
        super().__init__(**kwargs)
        self._callback = callback
        self._pressed  = False
        self._tex_n = self._tex_d = None
        for attr, path in (
            ("_tex_n", os.path.join(_KB_DIR, "BACK_button.png")),
            ("_tex_d", os.path.join(_KB_DIR, "BACK_button_pressed.png")),
        ):
            if os.path.isfile(path):
                try:
                    setattr(self, attr, CoreImage(path).texture)
                except Exception:
                    pass
        self.bind(pos=self._redraw, size=self._redraw)

    def _redraw(self, *_):
        self.canvas.clear()
        tex = self._tex_d if self._pressed else self._tex_n
        if tex is None:
            return
        tw, th = tex.size
        if tw == 0 or th == 0 or self.width == 0 or self.height == 0:
            return
        scale = min(self.width / tw, self.height / th)
        dw, dh = tw * scale, th * scale
        x = self.x + (self.width  - dw) / 2
        y = self.y + (self.height - dh) / 2
        with self.canvas:
            Color(1, 1, 1, 1)
            Rectangle(texture=tex, pos=(x, y), size=(dw, dh))

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            touch.grab(self)
            self._pressed = True
            self._redraw()
            return True
        return super().on_touch_down(touch)

    def on_touch_up(self, touch):
        if touch.grab_current is self:
            touch.ungrab(self)
            was_inside = self.collide_point(*touch.pos)
            self._pressed = False
            self._redraw()
            if was_inside:
                self._callback()
            return True
        return super().on_touch_up(touch)


# ── Arrow button ──────────────────────────────────────────────────────────────

class _ArrowButton(Widget):
    def __init__(self, direction, callback, **kwargs):
        super().__init__(**kwargs)
        self._callback = callback
        self._pressed  = False
        prefix = "left_arrow" if direction == "left" else "right_arrow"
        self._tex_n = self._tex_d = None
        for attr, name in (
            ("_tex_n", f"{prefix}.png"),
            ("_tex_d", f"{prefix}_clicked.png"),
        ):
            path = os.path.join(_ASSETS, "ui", name)
            if os.path.isfile(path):
                try:
                    setattr(self, attr, CoreImage(path).texture)
                except Exception:
                    pass
        self.bind(pos=self._redraw, size=self._redraw)

    def _redraw(self, *_):
        self.canvas.clear()
        tex = self._tex_d if self._pressed else self._tex_n
        if tex is None:
            return
        tw, th = tex.size
        if tw == 0 or th == 0 or self.width == 0 or self.height == 0:
            return
        scale = min(self.width / tw, self.height / th)
        dw, dh = tw * scale, th * scale
        x = self.x + (self.width  - dw) / 2
        y = self.y + (self.height - dh) / 2
        with self.canvas:
            Color(1, 1, 1, 1)
            Rectangle(texture=tex, pos=(x, y), size=(dw, dh))

    def on_touch_down(self, touch):
        if self.opacity == 0:
            return False
        if self.collide_point(*touch.pos):
            touch.grab(self)
            self._pressed = True
            self._redraw()
            return True
        return super().on_touch_down(touch)

    def on_touch_up(self, touch):
        if touch.grab_current is self:
            touch.ungrab(self)
            was_inside = self.collide_point(*touch.pos)
            self._pressed = False
            self._redraw()
            if was_inside:
                self._callback()
            return True
        return super().on_touch_up(touch)


# ── Screen ────────────────────────────────────────────────────────────────────

class LeaderboardScreen(FloatLayout):
    def __init__(self, **kwargs):
        self.name    = kwargs.pop("name", "leaderboard")
        self.manager = None
        super().__init__(**kwargs)
        self.current_player   = None
        self.current_score    = None
        self.current_opponent = None

        self._page              = 0     # 0 = bar duty, 1 = kitchen duty
        self._bar_available     = True
        self._kitchen_available = False

        self._score_labels   = [[] for _ in OPPONENT_ORDER]   # bar duty
        self._kitchen_labels = []                              # kitchen duty
        self._title_labels   = []
        self._build_ui()
        self.bind(size=self._reposition, pos=self._reposition)

    # ── Coordinate helpers ────────────────────────────────────────────────────

    def _img_to_screen_box(self, zone):
        l, t, r, b = zone
        scr_w, scr_h = self.width, self.height
        if scr_w == 0 or scr_h == 0:
            return 0, 0, 1, 1
        scale    = scr_w / _BG_W
        scaled_h = scale * _BG_H
        sx = lambda ix: ix * scale
        if scaled_h >= scr_h:
            crop_y = (scaled_h - scr_h) / 2
            sy = lambda iy: scr_h - (iy * scale - crop_y)
        else:
            sy = lambda iy: (scr_h + scaled_h) / 2 - iy * scale
        x0, x1       = sx(l), sx(r)
        y_top, y_bot = sy(t), sy(b)
        return x0, y_bot, x1 - x0, y_top - y_bot

    def _img_to_screen_pt(self, ix, iy):
        scr_w, scr_h = self.width, self.height
        if scr_w == 0 or scr_h == 0:
            return 0, 0
        scale    = scr_w / _BG_W
        scaled_h = scale * _BG_H
        sx = ix * scale
        if scaled_h >= scr_h:
            crop_y = (scaled_h - scr_h) / 2
            sy = scr_h - (iy * scale - crop_y)
        else:
            sy = (scr_h + scaled_h) / 2 - iy * scale
        return sx, sy

    # ── UI build ──────────────────────────────────────────────────────────────

    def _build_ui(self):
        with self.canvas.before:
            Color(*COLOR_BG)
            self._bg_color_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(
            size=lambda *_: setattr(self._bg_color_rect, "size", self.size),
            pos=lambda *_: setattr(self._bg_color_rect, "pos",  self.pos),
        )

        self._bg = _FillWidthBg(
            source=_BD_BG,
            size_hint=(1, 1),
            pos_hint={"x": 0, "y": 0},
        )
        self.add_widget(self._bg)

        self._back_btn = _BackButton(callback=self._go_menu, size_hint=(None, None))
        self.add_widget(self._back_btn)

        self._left_arrow = _ArrowButton(
            direction="left", callback=self._prev_page, size_hint=(None, None))
        self._right_arrow = _ArrowButton(
            direction="right", callback=self._next_page, size_hint=(None, None))
        self.add_widget(self._left_arrow)
        self.add_widget(self._right_arrow)

        self._screen_title = Label(
            text=_BD_TITLE_TEXT,
            font_size=fsp(28), font_name=_FONT,
            color=COLOR_BLACK,
            size_hint=(None, None), size=(2000, 50),
            text_size=(2000, 50), halign="left", valign="middle",
        )
        self.add_widget(self._screen_title)

        self._debug_layer = InstructionGroup()
        self.canvas.after.add(self._debug_layer)

        self._title_labels = []
        for title in _COL_TITLES:
            lbl = Label(
                text=title,
                font_size=fsp(26), font_name=_FONT,
                color=COLOR_BLACK,
                size_hint=(None, None), size=(400, 36),
                text_size=(400, 36), halign="left", valign="middle",
            )
            self._title_labels.append(lbl)
            self.add_widget(lbl)

        self._kd_title_lbl = Label(
            text=_KD_TITLE_TEXT,
            font_size=fsp(26), font_name=_FONT,
            color=COLOR_BLACK,
            size_hint=(None, None), size=(800, 36),
            text_size=(800, 36), halign="center", valign="middle",
        )
        self.add_widget(self._kd_title_lbl)

    # ── Page logic ────────────────────────────────────────────────────────────

    def _apply_page(self):
        """Show/hide labels and swap background for the current page."""
        on_kitchen = self._page == 1
        show_arrows = self._bar_available and self._kitchen_available

        # Background
        self._bg.set_source(_KD_BG if on_kitchen else _BD_BG)

        # Arrows
        for arrow in (self._left_arrow, self._right_arrow):
            arrow.opacity = 1 if show_arrows else 0

        # Bar duty labels
        bar_opacity = 0 if on_kitchen else 1
        self._screen_title.text = _KD_SCREEN_TITLE_PX and (_BD_TITLE_TEXT if not on_kitchen else _KD_TITLE_TEXT)
        for lbl in self._title_labels:
            lbl.opacity = bar_opacity
        for col_labels in self._score_labels:
            for lbl in col_labels:
                lbl.opacity = bar_opacity

        # Kitchen labels
        kd_opacity = 1 if on_kitchen else 0
        self._kd_title_lbl.opacity = 0   # screen title already shows the page name
        for lbl in self._kitchen_labels:
            lbl.opacity = kd_opacity

        self._reposition()

    def _prev_page(self):
        if not self._bar_available and not self._kitchen_available:
            return
        audio_manager.play_button_wood()
        pages = self._available_pages()
        idx = pages.index(self._page) if self._page in pages else 0
        self._page = pages[(idx - 1) % len(pages)]
        self._apply_page()

    def _next_page(self):
        if not self._bar_available and not self._kitchen_available:
            return
        audio_manager.play_button_wood()
        pages = self._available_pages()
        idx = pages.index(self._page) if self._page in pages else 0
        self._page = pages[(idx + 1) % len(pages)]
        self._apply_page()

    def _available_pages(self):
        pages = []
        if self._bar_available:
            pages.append(0)
        if self._kitchen_available:
            pages.append(1)
        return pages

    # ── Reposition ────────────────────────────────────────────────────────────

    def _reposition(self, *_):
        if self.width == 0 or self.height == 0:
            return
        x, y, w, h = self._img_to_screen_box(_ZONE_BACK)
        self._back_btn.pos  = (x, y)
        self._back_btn.size = (w, h)

        x, y, w, h = self._img_to_screen_box(_ZONE_LEFT_ARROW)
        self._left_arrow.pos  = (x, y)
        self._left_arrow.size = (w, h)

        x, y, w, h = self._img_to_screen_box(_ZONE_RIGHT_ARROW)
        self._right_arrow.pos  = (x, y)
        self._right_arrow.size = (w, h)

        sx, sy = self._img_to_screen_pt(
            _BD_TITLE_PX[0] if self._page == 0 else _KD_SCREEN_TITLE_PX[0],
            _BD_TITLE_PX[1] if self._page == 0 else _KD_SCREEN_TITLE_PX[1],
        )
        self._screen_title.pos = (sx, sy)

        self._reposition_scores()

    def _reposition_scores(self):
        if self.width == 0 or self.height == 0:
            return
        scale = self.width / _BG_W

        # Bar duty columns
        step = _SCORES_STEP_PX * scale
        for col_idx, lbl in enumerate(self._title_labels):
            lbl.pos = self._img_to_screen_pt(*_COL_TITLE_PX[col_idx])
        for col_idx, col_labels in enumerate(self._score_labels):
            ax, ay = self._img_to_screen_pt(*_COL_PX[col_idx])
            for row, lbl in enumerate(col_labels):
                lbl.pos = (ax, ay - row * step)

        # Kitchen duty column
        kd_step = _KD_STEP_PX * scale
        self._kd_title_lbl.pos = self._img_to_screen_pt(*_KD_TITLE_PX)
        ax, ay = self._img_to_screen_pt(*_KD_COL_PX)
        for row, lbl in enumerate(self._kitchen_labels):
            lbl.pos = (ax - 400, ay - row * kd_step)   # centre-offset

        self._debug_layer.clear()

    # ── Score population ──────────────────────────────────────────────────────

    def on_enter(self):
        player = get_current_player()
        player_name = player["name"] if player else None

        self._bar_available     = player_name is not None and is_endless_unlocked(player_name)
        self._kitchen_available = player_name is not None and is_kitchen_endless_unlocked(player_name)

        # Pick starting page: show the one that's available; prefer bar duty
        pages = self._available_pages()
        if pages:
            self._page = pages[0]

        self._populate_scores()
        self._apply_page()

    def _populate_scores(self):
        # ── Clear old labels ─────────────────────────────────────────────────
        for col_labels in self._score_labels:
            for lbl in col_labels:
                self.remove_widget(lbl)
        self._score_labels = [[] for _ in OPPONENT_ORDER]

        for lbl in self._kitchen_labels:
            self.remove_widget(lbl)
        self._kitchen_labels = []

        current     = get_current_player()
        current_name = current["name"].strip().upper() if current else ""

        # ── Bar Duty ─────────────────────────────────────────────────────────
        for col_idx, opponent in enumerate(OPPONENT_ORDER):
            if self.current_opponent and opponent != self.current_opponent:
                continue
            entries = load_scores_for_opponent(opponent)[:_MAX_ENTRIES]
            for entry in entries:
                name  = entry["name"].strip().upper()
                score = entry["score"]
                is_highlight = (
                    name == current_name
                    and score == self.current_score
                    and opponent == self.current_opponent
                )
                lbl = Label(
                    text=f"{name} : {score}",
                    font_size=fsp(28), font_name=_FONT,
                    bold=is_highlight,
                    color=COLOR_YELLOW if is_highlight else COLOR_BLACK,
                    size_hint=(None, None), size=(400, 32),
                    text_size=(400, 32), halign="left", valign="middle",
                )
                lbl.bind(size=lbl.setter("text_size"))
                self._score_labels[col_idx].append(lbl)
                self.add_widget(lbl)

        # ── Kitchen Duty ─────────────────────────────────────────────────────
        entries = load_scores_for_opponent("kitchen_endless")[:_MAX_ENTRIES]
        for entry in entries:
            name     = entry["name"].strip().upper()
            score    = entry["score"]
            orders   = score // _KITCHEN_SCORE_PER_ORDER
            is_hl    = name == current_name and score == self.current_score
            lbl = Label(
                text=f"{name} : {orders} ORDERS",
                font_size=fsp(26), font_name=_FONT,
                bold=is_hl,
                color=COLOR_YELLOW if is_hl else COLOR_BLACK,
                size_hint=(None, None), size=(800, 32),
                text_size=(800, 32), halign="center", valign="middle",
            )
            lbl.bind(size=lbl.setter("text_size"))
            self._kitchen_labels.append(lbl)
            self.add_widget(lbl)

        self._reposition_scores()

    # ── Navigation ────────────────────────────────────────────────────────────

    def _go_menu(self, *_):
        audio_manager.play_button_wood()
        if get_current_player() is not None:
            self.manager.current = "cafe_hub"
        else:
            audio_manager.stop_cafe_ambiance()
            self.manager.current = "menu"
