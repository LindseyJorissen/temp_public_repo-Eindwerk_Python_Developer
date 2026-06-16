"""
screens/level_end.py – Shown after a Bar Duty level completes or fails.

SHIFT COMPLETE: timer reached 0, player survived with lives remaining.
SHIFT FAILED  : player lost all lives before the timer ended.

Background images are displayed fit-to-width (no cropping) so the baked-in
art text is always fully visible.  Overlay labels are positioned using
image-fraction coordinates so they sit exactly on the board's data areas.

Attributes set by the calling screen BEFORE navigating here:
    level_end.level_num    (int)
    level_end.score        (int)
    level_end.success      (bool)
    level_end.elapsed_secs (float)  seconds the player actually played
"""

import os

import audio_manager
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.widget import Widget
from kivy.uix.label import Label
from kivy.graphics import Color, Rectangle
from kivy.core.image import Image as CoreImage

from game_constants import COLOR_BG, COLOR_GOLD
from game_utils import (
    get_current_player, mark_level_complete,
    is_endless_unlocked, unlock_achievement, is_achievement_unlocked,
)
from level_config import LEVELS, TOTAL_LEVELS

_ASSETS = os.path.join(os.path.dirname(__file__), "..", "assets")
_FONT   = os.path.join(_ASSETS, "fonts", "Pixelfont.ttf")

_BG_IMG_COMPLETE  = os.path.join(_ASSETS, "screens", "shift_complete.png")
_BG_IMG_FAIL      = os.path.join(_ASSETS, "screens", "shift_failed.png")
_BTN_CONTINUE_N   = os.path.join(_ASSETS, "ui", "continue_button.png")
_BTN_CONTINUE_P   = os.path.join(_ASSETS, "ui", "continue_button_clicked.png")
_BTN_RETRY_N      = os.path.join(_ASSETS, "ui", "retry_button.png")
_BTN_RETRY_P      = os.path.join(_ASSETS, "ui", "retry_button_clicked.png")
_BTN_BACK_N       = os.path.join(_ASSETS, "ui", "back_button_level_end.png")
_BTN_BACK_P       = os.path.join(_ASSETS, "ui", "back_button_level_end_clicked.png")

_COLOR_SCORE_TXT = (1.00, 0.90, 0.55, 1.0)
_COLOR_COINS_TXT = (1.00, 0.80, 0.10, 1.0)

_BTN_ASPECT = 918 / 306   # 3.0 – width : height of the button art

# ── Image-fraction label positions ────────────────────────────────────────────
# (ux, uy) : ux=0 left … 1 right;  uy=0 top … 1 bottom of the displayed image

_UX_SCORE_COMPLETE  = 0.22
_UX_COINS_COMPLETE  = 0.48
_UX_TIME_COMPLETE   = 0.74
_UY_VALUE_COMPLETE  = 0.67

_UX_SCORE_FAILED    = 0.48
_UY_VALUE_FAILED    = 0.67

_UX_LEVEL_NAME             = 0.50
_UY_LEVEL_NAME_COMPLETE    = 0.41
_UY_LEVEL_NAME_FAILED      = 0.43


def _fmt_time(secs):
    """Format elapsed seconds as  M:SS."""
    s = int(max(0.0, secs))
    return f"{s // 60}:{s % 60:02d}"


# ── Image-based tap button ────────────────────────────────────────────────────

class _ImgButton(Widget):
    """A button rendered as a sprite image (normal / pressed state)."""

    def __init__(self, tex_normal, tex_pressed, callback, **kwargs):
        super().__init__(**kwargs)
        self._tex_normal  = tex_normal
        self._tex_pressed = tex_pressed
        self._callback    = callback
        self._pressed     = False
        with self.canvas:
            Color(1, 1, 1, 1)
            self._rect = Rectangle(
                texture=tex_normal,
                pos=self.pos,
                size=self.size,
            )
        self.bind(pos=self._redraw, size=self._redraw)

    def _redraw(self, *_):
        tex = self._tex_pressed if (self._pressed and self._tex_pressed) else self._tex_normal
        if tex:
            self._rect.texture = tex
        self._rect.pos  = self.pos
        self._rect.size = self.size

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
            inside = self.collide_point(*touch.pos)
            self._pressed = False
            self._redraw()
            if inside:
                self._callback()
            return True
        return super().on_touch_up(touch)


# ── Background widget (fit-to-width, no cropping) ─────────────────────────────

class _FillWidthBg(Widget):
    def __init__(self, source, **kwargs):
        super().__init__(**kwargs)
        self.img_x = 0.0
        self.img_y = 0.0
        self.img_w = 0.0
        self.img_h = 0.0
        try:
            self._texture = CoreImage(source).texture
        except Exception:
            self._texture = None
        with self.canvas:
            Color(1, 1, 1, 1)
            self._rect = Rectangle()
        self.bind(pos=self._update, size=self._update)

    def set_texture(self, texture):
        self._texture = texture
        self._update()

    def _update(self, *_):
        if not self._texture:
            return
        tw, th = self._texture.size
        w, h   = self.size
        if w == 0 or h == 0 or tw == 0 or th == 0:
            return
        dw = w
        dh = w * th / tw
        self.img_x = self.x
        self.img_y = self.y + (h - dh) / 2
        self.img_w = dw
        self.img_h = dh
        self._rect.texture    = self._texture
        self._rect.tex_coords = (0, 1, 1, 1, 1, 0, 0, 0)
        self._rect.pos        = (self.img_x, self.img_y)
        self._rect.size       = (dw, dh)


# ── Screen ────────────────────────────────────────────────────────────────────

class LevelEndScreen(FloatLayout):
    """Post-level result screen (complete or failed)."""

    def __init__(self, **kwargs):
        self.name    = kwargs.pop("name", "level_end")
        self.manager = None
        super().__init__(**kwargs)

        self.level_num    = 1
        self.score        = 0
        self.success      = True
        self.elapsed_secs = 0.0

        self._coins_earned = 0
        self._first_time   = False

        self._build_ui()
        self.bind(size=self._reposition, pos=self._reposition)

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        with self.canvas.before:
            Color(*COLOR_BG)
            self._bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(
            size=lambda *_: setattr(self._bg_rect, "size", self.size),
            pos =lambda *_: setattr(self._bg_rect, "pos",  self.pos),
        )

        def _lt(path):
            try:
                return CoreImage(path).texture
            except Exception:
                return None

        self._tex_complete  = _lt(_BG_IMG_COMPLETE)
        self._tex_fail      = _lt(_BG_IMG_FAIL)
        self._tex_cont_n    = _lt(_BTN_CONTINUE_N)
        self._tex_cont_p    = _lt(_BTN_CONTINUE_P)
        self._tex_retry_n   = _lt(_BTN_RETRY_N)
        self._tex_retry_p   = _lt(_BTN_RETRY_P)
        self._tex_back_n    = _lt(_BTN_BACK_N)
        self._tex_back_p    = _lt(_BTN_BACK_P)

        self._bg_widget = _FillWidthBg(
            source=_BG_IMG_FAIL,
            size_hint=(1, 1),
            pos_hint={"x": 0, "y": 0},
        )
        self.add_widget(self._bg_widget)

        # Level / shift name
        self._level_lbl = Label(
            text="",
            font_name=_FONT,
            font_size=12,
            color=COLOR_GOLD,
            size_hint=(None, None),
            halign="center",
            valign="middle",
        )
        self.add_widget(self._level_lbl)

        # Score number
        self._score_lbl = Label(
            text="",
            font_name=_FONT,
            font_size=12,
            color=_COLOR_SCORE_TXT,
            size_hint=(None, None),
            halign="center",
            valign="middle",
        )
        self.add_widget(self._score_lbl)

        # Coins number (complete only)
        self._coins_lbl = Label(
            text="",
            font_name=_FONT,
            font_size=12,
            color=_COLOR_COINS_TXT,
            size_hint=(None, None),
            halign="center",
            valign="middle",
        )
        self.add_widget(self._coins_lbl)

        # Time value (complete only)
        self._time_lbl = Label(
            text="",
            font_name=_FONT,
            font_size=12,
            color=_COLOR_SCORE_TXT,
            size_hint=(None, None),
            halign="center",
            valign="middle",
        )
        self.add_widget(self._time_lbl)

        # Primary action button (CONTINUE image or RETRY image)
        self._action_btn = _ImgButton(
            tex_normal=self._tex_retry_n,
            tex_pressed=self._tex_retry_p,
            callback=self._on_retry,
            size_hint=(None, None),
        )
        self.add_widget(self._action_btn)

        # Back button (image)
        self._back_btn = _ImgButton(
            tex_normal=self._tex_back_n,
            tex_pressed=self._tex_back_p,
            callback=self._on_back,
            size_hint=(None, None),
        )
        self.add_widget(self._back_btn)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _img_at(self, ux, uy, img_x, img_y, img_w, img_h):
        """Screen coords for a fractional point in the image.
        ux=0..1 left..right; uy=0..1 top..bottom of the displayed image."""
        return (
            img_x + ux * img_w,
            img_y + (1.0 - uy) * img_h,
        )

    # ── Layout ────────────────────────────────────────────────────────────────

    def _reposition(self, *_):
        W, H = self.width, self.height
        if W < 2 or H < 2:
            return

        # Compute image rect directly from screen size + texture aspect.
        # This avoids the Kivy layout-timing race where _bg_widget.size may
        # not have been resolved yet when on_enter fires.
        bg  = self._bg_widget
        tex = bg._texture
        if tex is None:
            return
        tw, th = tex.size
        if tw == 0 or th == 0:
            return

        img_w = W
        img_h = W * th / tw
        img_x = 0.0
        img_y = (H - img_h) / 2.0

        # Keep the bg widget's cached values and drawn rect in sync
        bg.img_x = img_x
        bg.img_y = img_y
        bg.img_w = img_w
        bg.img_h = img_h
        bg._rect.texture    = tex
        bg._rect.tex_coords = (0, 1, 1, 1, 1, 0, 0, 0)
        bg._rect.pos        = (img_x, img_y)
        bg._rect.size       = (img_w, img_h)

        val_w  = img_w * 0.28
        val_h  = img_h * 0.22
        name_w = img_w * 0.65
        name_h = img_h * 0.18

        def at(ux, uy):
            return self._img_at(ux, uy, img_x, img_y, img_w, img_h)

        # Level name
        uy_name = _UY_LEVEL_NAME_COMPLETE if self.success else _UY_LEVEL_NAME_FAILED
        nx, ny = at(_UX_LEVEL_NAME, uy_name)
        self._level_lbl.pos       = (nx - name_w / 2, ny - name_h / 2)
        self._level_lbl.size      = (name_w, name_h)
        self._level_lbl.text_size = (name_w, name_h)
        self._level_lbl.font_size = max(8, int(img_h * 0.045))

        # Value labels
        if self.success:
            sx, sy = at(_UX_SCORE_COMPLETE, _UY_VALUE_COMPLETE)
            cx, cy = at(_UX_COINS_COMPLETE, _UY_VALUE_COMPLETE)
            tx, ty = at(_UX_TIME_COMPLETE,  _UY_VALUE_COMPLETE)
        else:
            sx, sy = at(_UX_SCORE_FAILED, _UY_VALUE_FAILED)
            cx, cy = sx, sy   # hidden on failed screen
            tx, ty = sx, sy

        for lbl, x, y in (
            (self._score_lbl, sx, sy),
            (self._coins_lbl, cx, cy),
            (self._time_lbl,  tx, ty),
        ):
            lbl.pos       = (x - val_w / 2, y - val_h / 2)
            lbl.size      = (val_w, val_h)
            lbl.text_size = (val_w, val_h)

        val_font = max(8, int(img_h * 0.07))
        self._score_lbl.font_size = val_font
        self._coins_lbl.font_size = val_font
        self._time_lbl.font_size  = val_font

        # Buttons – anchored inside the image (brick strip below the chalkboard)
        btn_w  = img_w * 0.18
        btn_h  = btn_w / _BTN_ASPECT
        gap    = img_w * 0.04
        total  = btn_w * 2 + gap
        bx     = img_x + img_w / 2 - total / 2
        _, btn_cy = at(0.5, 0.87)
        btn_y  = btn_cy - btn_h / 2

        self._action_btn.pos  = (bx, btn_y)
        self._action_btn.size = (btn_w, btn_h)
        self._action_btn._redraw()

        self._back_btn.pos  = (bx + btn_w + gap, btn_y)
        self._back_btn.size = (btn_w, btn_h)
        self._back_btn._redraw()

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def on_enter(self):
        tex = self._tex_complete if self.success else self._tex_fail
        if tex:
            self._bg_widget.set_texture(tex)

        player     = get_current_player()
        cfg        = LEVELS.get(self.level_num, {})
        level_name = cfg.get("name", f"Level {self.level_num}")

        self._first_time   = False
        self._coins_earned = 0

        if self.success:
            if player:
                self._first_time, self._coins_earned = mark_level_complete(
                    player["name"], self.level_num, self.score
                )
                if (is_endless_unlocked(player["name"])
                        and not is_achievement_unlocked(player["name"], "bar_survivor")):
                    unlock_achievement(player["name"], "bar_survivor", 500)

            coins_txt = f"+{self._coins_earned}" if self._coins_earned > 0 else "0"
            self._coins_lbl.text    = coins_txt
            self._coins_lbl.opacity = 1
            self._time_lbl.text     = _fmt_time(self.elapsed_secs)
            self._time_lbl.opacity  = 1

            # Action button → CONTINUE image
            self._action_btn._tex_normal  = self._tex_cont_n
            self._action_btn._tex_pressed = self._tex_cont_p
            if self.level_num < TOTAL_LEVELS:
                self._action_btn._callback = self._on_next_level
            else:
                self._action_btn._callback = self._on_back

        else:
            self._coins_lbl.text    = ""
            self._coins_lbl.opacity = 0
            self._time_lbl.text     = ""
            self._time_lbl.opacity  = 0

            # Action button → RETRY image
            self._action_btn._tex_normal  = self._tex_retry_n
            self._action_btn._tex_pressed = self._tex_retry_p
            self._action_btn._callback    = self._on_retry

        self._action_btn._pressed = False
        self._action_btn._redraw()

        self._level_lbl.text = f"SHIFT {self.level_num} — {level_name.upper()}"
        self._score_lbl.text = str(self.score)

        self._reposition()

    # ── Navigation ────────────────────────────────────────────────────────────

    def _on_next_level(self):
        audio_manager.play_button_wood()
        next_num = self.level_num + 1
        victor = self.manager.get_screen("victor_intro")
        victor.level_num = next_num
        self.manager.current = "victor_intro"

    def _on_retry(self):
        audio_manager.play_button_wood()
        victor = self.manager.get_screen("victor_intro")
        victor.level_num = self.level_num
        self.manager.current = "victor_intro"

    def _on_back(self):
        audio_manager.play_button_wood()
        self.manager.current = "bar_duty_hub"
