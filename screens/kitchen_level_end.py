"""
screens/kitchen_level_end.py – Shown after a Kitchen Duty level completes or fails.

Reuses the same shift_complete.png / shift_failed.png background art as the
Bar Duty level-end screen, with Kitchen Duty-specific nav and data calls.

Attributes set by the calling screen BEFORE navigating here:
    kitchen_level_end.level_num    (int)
    kitchen_level_end.score        (int)
    kitchen_level_end.success      (bool)
    kitchen_level_end.elapsed_secs (float)
"""

import os

import audio_manager
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.widget import Widget
from kivy.uix.label import Label
from kivy.graphics import Color, Rectangle, RoundedRectangle
from kivy.core.image import Image as CoreImage
from kivy.clock import Clock

from game_constants import COLOR_BG, COLOR_GOLD
from game_utils import (
    get_current_player,
    mark_kitchen_level_complete,
    update_player_score,
    is_kitchen_endless_unlocked,
    is_kitchen_level_unlocked,
    is_kitchen_level_tutorial_done,
    fsp,
)
from kitchen_level_config import KITCHEN_LEVELS, KITCHEN_TOTAL_LEVELS

_ASSETS = os.path.join(os.path.dirname(__file__), "..", "assets")
_FONT   = os.path.join(_ASSETS, "fonts", "Pixelfont.ttf")

# Reuse the same result screen art as Bar Duty
_BG_COMPLETE = os.path.join(_ASSETS, "screens", "shift_complete.png")
_BG_FAIL     = os.path.join(_ASSETS, "screens", "shift_failed.png")
_BTN_CONT_N  = os.path.join(_ASSETS, "ui", "continue_button.png")
_BTN_CONT_P  = os.path.join(_ASSETS, "ui", "continue_button_clicked.png")
_BTN_RETRY_N = os.path.join(_ASSETS, "ui", "retry_button.png")
_BTN_RETRY_P = os.path.join(_ASSETS, "ui", "retry_button_clicked.png")
_BTN_BACK_N  = os.path.join(_ASSETS, "ui", "back_button_level_end.png")
_BTN_BACK_P  = os.path.join(_ASSETS, "ui", "back_button_level_end_clicked.png")

_COLOR_SCORE = (1.00, 0.90, 0.55, 1.0)
_COLOR_COINS = (1.00, 0.80, 0.10, 1.0)
_BTN_ASPECT  = 918.0 / 306.0   # width : height of button art

# ── Achievement toast ─────────────────────────────────────────────────────────

_TOAST_ART_DIR = os.path.join(_ASSETS, "achievements_art")
_TOAST_ASPECT  = 1989 / 459   # width / height of all toast images
_TOAST_IMGS = {
    "kitchen_mise_en_place":  "miseenplace_toast.png",
    "kitchen_head_chef":      "headchef_toast.png",
    "kitchen_iron_chef":      "ironchef_toast.png",
    "kitchen_long_shift":     "thelongshift_toast.png",
    "kitchen_closing_time":   "closingtime_toast.png",
    "kitchen_mittens_buffet": "mittensbuffet_toast.png",
}


class _AchievementToast(Widget):
    """Slides in from the right, holds, slides back out."""
    _SLIDEIN  = 0.40
    _SHOW     = 2.5
    _SLIDEOUT = 0.35

    def __init__(self, key, rest_x, rest_y, screen_right, on_done, **kwargs):
        super().__init__(**kwargs)
        self._on_done      = on_done
        self._phase        = 'slidein'
        self._elapsed      = 0.0
        self._rest_x       = rest_x
        self._rest_y       = rest_y
        self._screen_right = screen_right
        self._tex          = None
        fname = _TOAST_IMGS.get(key)
        if fname:
            try:
                self._tex = CoreImage(os.path.join(_TOAST_ART_DIR, fname)).texture
            except Exception:
                pass
        self.bind(pos=self._redraw, size=self._redraw)
        Clock.schedule_interval(self._tick, 1.0 / 60.0)

    def _redraw(self, *_):
        self.canvas.clear()
        if self.width == 0 or self.height == 0:
            return
        with self.canvas:
            if self._tex:
                Color(1, 1, 1, 1)
                Rectangle(texture=self._tex, pos=self.pos, size=self.size)
            else:
                Color(0.12, 0.06, 0.02, 0.95)
                RoundedRectangle(pos=self.pos, size=self.size, radius=[14])

    @staticmethod
    def _ease_out(t): return 1.0 - (1.0 - t) ** 3
    @staticmethod
    def _ease_in(t):  return t ** 3

    def _tick(self, dt):
        self._elapsed += dt
        if self._phase == 'slidein':
            t = min(1.0, self._elapsed / self._SLIDEIN)
            self.x = self._screen_right + (self._rest_x - self._screen_right) * self._ease_out(t)
            if self._elapsed >= self._SLIDEIN:
                self.x        = self._rest_x
                self._phase   = 'show'
                self._elapsed = 0.0
        elif self._phase == 'show':
            if self._elapsed >= self._SHOW:
                self._phase   = 'slideout'
                self._elapsed = 0.0
        elif self._phase == 'slideout':
            t = min(1.0, self._elapsed / self._SLIDEOUT)
            self.x = self._rest_x + (self._screen_right - self._rest_x) * self._ease_in(t)
            if self._elapsed >= self._SLIDEOUT:
                Clock.unschedule(self._tick)
                self._on_done()

    def stop(self):
        Clock.unschedule(self._tick)


# Image-fraction positions (same layout as level_end.py)
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
    s = int(max(0.0, secs))
    return f"{s // 60}:{s % 60:02d}"


# ── Image button ─────────────────────────────────────────────────────────────

class _ImgButton(Widget):
    def __init__(self, tex_normal, tex_pressed, callback, **kwargs):
        super().__init__(**kwargs)
        self._tex_n   = tex_normal
        self._tex_p   = tex_pressed
        self._callback = callback
        self._pressed  = False
        with self.canvas:
            Color(1, 1, 1, 1)
            self._rect = Rectangle(texture=tex_normal, pos=self.pos, size=self.size)
        self.bind(pos=self._redraw, size=self._redraw)

    def _redraw(self, *_):
        tex = self._tex_p if (self._pressed and self._tex_p) else self._tex_n
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


# ── Background widget ─────────────────────────────────────────────────────────

class _FillWidthBg(Widget):
    def __init__(self, source, **kwargs):
        super().__init__(**kwargs)
        self.img_x = self.img_y = self.img_w = self.img_h = 0.0
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

class KitchenLevelEndScreen(FloatLayout):

    def __init__(self, **kwargs):
        self.name    = kwargs.pop("name", "kitchen_level_end")
        self.manager = None
        super().__init__(**kwargs)

        self.level_num    = 1
        self.score        = 0
        self.success      = True
        self.elapsed_secs = 0.0
        self.pending_achievement_toasts = []

        self._coins_earned  = 0
        self._first_time    = False
        self._toast_queue   = []
        self._active_toast  = None

        self._build_ui()
        self.bind(size=self._reposition, pos=self._reposition)

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

        self._tex_complete = _lt(_BG_COMPLETE)
        self._tex_fail     = _lt(_BG_FAIL)
        self._tex_cont_n   = _lt(_BTN_CONT_N)
        self._tex_cont_p   = _lt(_BTN_CONT_P)
        self._tex_retry_n  = _lt(_BTN_RETRY_N)
        self._tex_retry_p  = _lt(_BTN_RETRY_P)
        self._tex_back_n   = _lt(_BTN_BACK_N)
        self._tex_back_p   = _lt(_BTN_BACK_P)

        self._bg_widget = _FillWidthBg(
            source=_BG_FAIL,
            size_hint=(1, 1),
            pos_hint={"x": 0, "y": 0},
        )
        self.add_widget(self._bg_widget)

        self._level_lbl = Label(text="", font_name=_FONT, font_size=12, color=COLOR_GOLD,
                                size_hint=(None, None), halign="center", valign="middle")
        self._score_lbl = Label(text="", font_name=_FONT, font_size=12, color=_COLOR_SCORE,
                                size_hint=(None, None), halign="center", valign="middle")
        self._coins_lbl = Label(text="", font_name=_FONT, font_size=12, color=_COLOR_COINS,
                                size_hint=(None, None), halign="center", valign="middle")
        self._time_lbl  = Label(text="", font_name=_FONT, font_size=12, color=_COLOR_SCORE,
                                size_hint=(None, None), halign="center", valign="middle")
        for lbl in (self._level_lbl, self._score_lbl, self._coins_lbl, self._time_lbl):
            self.add_widget(lbl)

        self._action_btn = _ImgButton(
            tex_normal=self._tex_retry_n, tex_pressed=self._tex_retry_p,
            callback=self._on_retry, size_hint=(None, None),
        )
        self._back_btn = _ImgButton(
            tex_normal=self._tex_back_n, tex_pressed=self._tex_back_p,
            callback=self._on_back, size_hint=(None, None),
        )
        self.add_widget(self._action_btn)
        self.add_widget(self._back_btn)

    def _img_at(self, ux, uy, img_x, img_y, img_w, img_h):
        return (img_x + ux * img_w, img_y + (1.0 - uy) * img_h)

    def _reposition(self, *_):
        W, H = self.width, self.height
        if W < 2 or H < 2:
            return

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

        bg.img_x = img_x; bg.img_y = img_y; bg.img_w = img_w; bg.img_h = img_h
        bg._rect.texture    = tex
        bg._rect.tex_coords = (0, 1, 1, 1, 1, 0, 0, 0)
        bg._rect.pos        = (img_x, img_y)
        bg._rect.size       = (img_w, img_h)

        val_w  = img_w * 0.28; val_h  = img_h * 0.22
        name_w = img_w * 0.65; name_h = img_h * 0.18

        def at(ux, uy):
            return self._img_at(ux, uy, img_x, img_y, img_w, img_h)

        uy_name = _UY_LEVEL_NAME_COMPLETE if self.success else _UY_LEVEL_NAME_FAILED
        nx, ny = at(_UX_LEVEL_NAME, uy_name)
        self._level_lbl.pos       = (nx - name_w / 2, ny - name_h / 2)
        self._level_lbl.size      = (name_w, name_h)
        self._level_lbl.text_size = (name_w, name_h)
        self._level_lbl.font_size = max(8, int(img_h * 0.045))

        if self.success:
            sx, sy = at(_UX_SCORE_COMPLETE, _UY_VALUE_COMPLETE)
            cx, cy = at(_UX_COINS_COMPLETE, _UY_VALUE_COMPLETE)
            tx, ty = at(_UX_TIME_COMPLETE,  _UY_VALUE_COMPLETE)
        else:
            sx, sy = at(_UX_SCORE_FAILED, _UY_VALUE_FAILED)
            cx, cy = sx, sy
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

    def on_enter(self):
        tex = self._tex_complete if self.success else self._tex_fail
        if tex:
            self._bg_widget.set_texture(tex)

        player     = get_current_player()
        cfg        = KITCHEN_LEVELS.get(self.level_num, {})
        level_name = cfg.get("name", f"Level {self.level_num}")

        self._first_time   = False
        self._coins_earned = 0

        is_endless = (self.level_num == 0)

        if is_endless and player:
            update_player_score(player["name"], "kitchen_endless", self.score)
        elif self.success and player:
            self._first_time, self._coins_earned = mark_kitchen_level_complete(
                player["name"], self.level_num, self.score
            )

        if self.success and not is_endless:
            coins_txt = f"+{self._coins_earned}" if self._coins_earned > 0 else "0"
            self._coins_lbl.text    = coins_txt
            self._coins_lbl.opacity = 1
            self._time_lbl.text     = _fmt_time(self.elapsed_secs)
            self._time_lbl.opacity  = 1
            self._action_btn._tex_n = self._tex_cont_n
            self._action_btn._tex_p = self._tex_cont_p
            if self.level_num < KITCHEN_TOTAL_LEVELS:
                self._action_btn._callback = self._on_next_level
            else:
                self._action_btn._callback = self._on_back
        else:
            self._coins_lbl.text    = ""
            self._coins_lbl.opacity = 0
            self._time_lbl.text     = _fmt_time(self.elapsed_secs) if is_endless else ""
            self._time_lbl.opacity  = 1 if is_endless else 0
            self._action_btn._tex_n = self._tex_retry_n
            self._action_btn._tex_p = self._tex_retry_p
            self._action_btn._callback = self._on_retry

        self._action_btn._pressed = False
        self._action_btn._redraw()
        self._level_lbl.text = ("KITCHEN ENDLESS" if is_endless
                                else f"KITCHEN {self.level_num} — {level_name.upper()}")
        self._score_lbl.text = str(self.score)
        self._reposition()

        # Show achievement toasts if any were newly unlocked this run
        self._toast_queue  = list(self.pending_achievement_toasts)
        self._active_toast = None
        self.pending_achievement_toasts = []
        if self._toast_queue:
            Clock.schedule_once(lambda *_: self._show_next_toast(), 0.6)

    def _show_next_toast(self):
        if not self._toast_queue:
            self._active_toast = None
            return
        key = self._toast_queue.pop(0)
        audio_manager.play_achievement_unlocked()
        W  = self.width
        sr = self.right
        toast_w = min(W * 0.72, 680)
        toast_h = toast_w / _TOAST_ASPECT
        rest_x  = sr - toast_w - 16
        rest_y  = self.top - toast_h - 60
        toast = _AchievementToast(
            key=key,
            rest_x=rest_x,
            rest_y=rest_y,
            screen_right=sr,
            on_done=self._on_toast_done,
            size_hint=(None, None),
            size=(toast_w, toast_h),
        )
        toast.x = sr
        toast.y = rest_y
        self.add_widget(toast)
        self._active_toast = toast

    def _on_toast_done(self):
        if self._active_toast:
            self.remove_widget(self._active_toast)
            self._active_toast = None
        self._show_next_toast()

    def on_leave(self):
        if self._active_toast:
            self._active_toast.stop()
            self.remove_widget(self._active_toast)
            self._active_toast = None
        self._toast_queue.clear()

    def _on_next_level(self):
        audio_manager.play_button_wood()
        next_num = self.level_num + 1
        player = get_current_player()
        has_tutorial = os.path.isfile(
            os.path.join(_ASSETS, "tutorial", f"kitchen_tutorial_lvl{next_num}_1.png"))
        if has_tutorial and player and not is_kitchen_level_tutorial_done(player["name"], next_num):
            tut = self.manager.get_screen("kitchen_tutorial")
            tut.level_num = next_num
            self.manager.current = "kitchen_tutorial"
        else:
            intro = self.manager.get_screen("kitchen_victor_intro")
            intro.level_num = next_num
            self.manager.current = "kitchen_victor_intro"

    def _on_retry(self):
        audio_manager.play_button_wood()
        if self.level_num in (0, 1):
            game = self.manager.get_screen("kitchen_gameplay")
            game.level_num = self.level_num
            self.manager.current = "kitchen_gameplay"
        else:
            intro = self.manager.get_screen("kitchen_victor_intro")
            intro.level_num = self.level_num
            self.manager.current = "kitchen_victor_intro"

    def _on_back(self):
        audio_manager.play_button_wood()
        self.manager.current = "kitchen_duty_hub"
