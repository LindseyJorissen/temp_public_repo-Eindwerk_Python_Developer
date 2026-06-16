"""
screens/kitchen_duty_hub.py – Kitchen Duty level-selection calendar screen.

Uses kitchen_duty_hub.png (3915 × 1773) with the same pixel-perfect
coordinate system as bar_duty_hub.py.

Calendar grid zones were measured from kitchen_duty_hub.png in the same
positions as bar_duty_hub so the same artwork layout works for both.
"""

import os

from kivy.uix.floatlayout import FloatLayout
from kivy.uix.widget import Widget
from kivy.uix.label import Label
from kivy.graphics import Color, Rectangle, RoundedRectangle
from kivy.core.image import Image as CoreImage

from game_constants import (
    COLOR_BG, COLOR_BTN_TEXT, DEBUG_HITBOXES,
)
from game_utils import (
    get_current_player,
    get_kitchen_level_progress,
    is_kitchen_level_unlocked,
    is_kitchen_endless_unlocked,
    is_kitchen_level_tutorial_done,
    debug_unlock_kitchen_endless,
    fsp,
)
from kitchen_level_config import KITCHEN_LEVELS, KITCHEN_TOTAL_LEVELS
import audio_manager

_ASSETS = os.path.join(os.path.dirname(__file__), "..", "assets")
_KB_DIR = os.path.join(_ASSETS, "keyboard buttons")
_FONT   = os.path.join(_ASSETS, "fonts", "Pixelfont.ttf")

_BG_IMG         = os.path.join(_ASSETS, "screens", "kitchen_duty_hub.png")
_BG_IMG_ENDLESS = os.path.join(_ASSETS, "screens", "endless_kitchen_duty.png")
_STAMP   = os.path.join(_ASSETS, "screens", "level_complete.png")
_HINT    = os.path.join(_ASSETS, "ui", "nextlevelhint.png")

# Source image dimensions (measured; same as bar_duty_hub.png)
_BG_W = 3915
_BG_H = 1773

# Calendar cell zones (left, top, right, bottom) in source-image pixels.
# Measured from kitchen_duty_hub.png – same grid layout as bar_duty_hub.
_ZONE_LVL = [
    (1548,  432, 1926,  765),   # Level 1
    (1935,  432, 2322,  765),   # Level 2
    (2331,  432, 2709,  765),   # Level 3
    (2718,  432, 3114,  765),   # Level 4
    (3123,  432, 3501,  765),   # Level 5
    (1548,  774, 1926, 1107),   # Level 6
    (1935,  774, 2322, 1107),   # Level 7
    (2331,  774, 2709, 1107),   # Level 8
    (2718,  774, 3114, 1107),   # Level 9
    (3123,  774, 3501, 1107),   # Level 10
]
_ZONE_ENDLESS = (1548, 1170, 3501, 1494)
_ZONE_BACK    = (  69, 1506,  501, 1713)

_COLOR_LOCKED_TXT  = (0.50, 0.50, 0.50, 1.0)
_COLOR_AVAIL_TXT   = (0.95, 0.85, 0.55, 1.0)
_COLOR_ENDLESS_OFF = (0.35, 0.30, 0.20, 1.0)
_COLOR_ENDLESS_ON  = (0.95, 0.85, 0.55, 1.0)


# ── Shared helper widgets (identical to bar_duty_hub pattern) ─────────────────

class _StampWidget(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        try:
            self._texture = CoreImage(_STAMP).texture
        except Exception:
            self._texture = None
        self._visible = False
        self.bind(pos=self._redraw, size=self._redraw)

    def set_visible(self, v):
        self._visible = v
        self._redraw()

    def _redraw(self, *_):
        self.canvas.clear()
        if not self._visible or not self._texture:
            return
        tw, th = self._texture.size
        if tw == 0 or th == 0 or self.width == 0 or self.height == 0:
            return
        scale = min(self.width / tw, self.height / th)
        dw, dh = tw * scale, th * scale
        x = self.x + (self.width  - dw) / 2
        y = self.y + (self.height - dh) / 2
        with self.canvas:
            Color(1, 1, 1, 1)
            Rectangle(texture=self._texture, pos=(x, y), size=(dw, dh))

    def on_touch_down(self, touch):
        return False


class _HintWidget(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        try:
            self._texture = CoreImage(_HINT).texture
        except Exception:
            self._texture = None
        self._visible = False
        self.bind(pos=self._redraw, size=self._redraw)

    def set_visible(self, v):
        self._visible = v
        self._redraw()

    def _redraw(self, *_):
        self.canvas.clear()
        if not self._visible or not self._texture:
            return
        tw, th = self._texture.size
        if tw == 0 or th == 0 or self.width == 0 or self.height == 0:
            return
        scale = min(self.width / tw, self.height / th)
        dw, dh = tw * scale, th * scale
        x = self.x + (self.width  - dw) / 2
        y = self.y + (self.height - dh) / 2
        with self.canvas:
            Color(1, 1, 1, 1)
            Rectangle(texture=self._texture, pos=(x, y), size=(dw, dh))

    def on_touch_down(self, touch):
        return False


class _TapButton(Widget):
    def __init__(self, text, callback, bg_color, txt_color,
                 font_size=14, enabled=True, **kwargs):
        super().__init__(**kwargs)
        self._text      = text
        self._callback  = callback
        self._bg_color  = bg_color
        self._txt_color = txt_color
        self._font_size = font_size
        self._enabled   = enabled
        self._pressed   = False
        self._label = Label(
            text=text, font_name=_FONT, font_size=fsp(font_size),
            color=txt_color, size_hint=(None, None),
            halign="center", valign="middle",
        )
        self.add_widget(self._label)
        self.bind(pos=self._redraw, size=self._redraw)

    def _redraw(self, *_):
        self.canvas.clear()
        color = list(self._bg_color)
        if self._pressed and self._enabled:
            color = [min(1.0, c * 1.4) for c in color[:3]] + [color[3]]
        if color[3] > 0:
            with self.canvas:
                Color(*color)
                RoundedRectangle(pos=self.pos, size=self.size, radius=[8])
        self._label.pos       = self.pos
        self._label.size      = self.size
        self._label.text_size = self.size
        self._label.font_size = fsp(self._font_size)

    def on_touch_down(self, touch):
        if self._enabled and self.collide_point(*touch.pos):
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
            if inside and self._enabled:
                self._callback()
            return True
        return super().on_touch_up(touch)


class _FillWidthBg(Widget):
    def __init__(self, source, **kwargs):
        super().__init__(**kwargs)
        try:
            self._texture = CoreImage(source).texture
        except Exception:
            self._texture = None
        with self.canvas:
            Color(1, 1, 1, 1)
            self._rect = Rectangle()
        self.bind(pos=self._update, size=self._update)

    def set_source(self, path):
        try:
            self._texture = CoreImage(path).texture
        except Exception:
            self._texture = None
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


class _ImageButton(Widget):
    def __init__(self, normal_path, pressed_path, callback, **kwargs):
        super().__init__(**kwargs)
        self._callback = callback
        self._pressed  = False
        self._tex_n = self._tex_d = None
        for attr, path in (("_tex_n", normal_path), ("_tex_d", pressed_path)):
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
            with self.canvas:
                Color(0.30, 0.18, 0.06, 1.0)
                RoundedRectangle(pos=self.pos, size=self.size, radius=[6])
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
            inside = self.collide_point(*touch.pos)
            self._pressed = False
            self._redraw()
            if inside:
                self._callback()
            return True
        return super().on_touch_up(touch)


# ── Screen ────────────────────────────────────────────────────────────────────

class KitchenDutyHubScreen(FloatLayout):
    """Kitchen Duty calendar screen – 10 levels + endless mode."""

    def __init__(self, **kwargs):
        self.name    = kwargs.pop("name", "kitchen_duty_hub")
        self.manager = None
        super().__init__(**kwargs)
        self._level_btns    = []
        self._stamp_widgets = []
        self._endless_btn   = None
        self._back_btn      = None
        self._debug_btn     = None
        self._hint_widget   = None
        self._hint_level_idx = None
        self._build_ui()
        self.bind(size=self._reposition, pos=self._reposition)

    # ── Coordinate mapping ────────────────────────────────────────────────────

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
        x0, x1 = sx(l), sx(r)
        y_top, y_bot = sy(t), sy(b)
        return x0, y_bot, x1 - x0, y_top - y_bot

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        with self.canvas.before:
            Color(*COLOR_BG)
            self._bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(
            size=lambda *_: setattr(self._bg_rect, "size", self.size),
            pos =lambda *_: setattr(self._bg_rect, "pos",  self.pos),
        )

        self._bg_widget = _FillWidthBg(
            source=_BG_IMG,
            size_hint=(1, 1),
            pos_hint={"x": 0, "y": 0},
        )
        self.add_widget(self._bg_widget)

        for _ in range(KITCHEN_TOTAL_LEVELS):
            stamp = _StampWidget(size_hint=(None, None))
            self._stamp_widgets.append(stamp)
            self.add_widget(stamp)

        self._hint_widget = _HintWidget(size_hint=(None, None))
        self.add_widget(self._hint_widget)

        for n in range(1, KITCHEN_TOTAL_LEVELS + 1):
            cfg = KITCHEN_LEVELS[n]
            btn = _TapButton(
                text=f"{n}. {cfg['name'].upper()}",
                callback=lambda num=n: self._on_level(num),
                bg_color=(0, 0, 0, 0),
                txt_color=_COLOR_AVAIL_TXT,
                font_size=10,
                enabled=True,
                size_hint=(None, None),
            )
            self._level_btns.append(btn)
            self.add_widget(btn)

        self._endless_btn = _TapButton(
            text="ENDLESS MODE",
            callback=self._on_endless,
            bg_color=(0, 0, 0, 0),
            txt_color=_COLOR_ENDLESS_OFF,
            font_size=12,
            enabled=False,
            size_hint=(None, None),
        )
        self.add_widget(self._endless_btn)

        if DEBUG_HITBOXES:
            self._debug_btn = _TapButton(
                text="[DBG] UNLOCK KITCHEN",
                callback=self._on_debug_unlock,
                bg_color=(0.05, 0.45, 0.05, 0.85),
                txt_color=(1.0, 1.0, 0.0, 1.0),
                font_size=11,
                size_hint=(None, None),
            )
            self.add_widget(self._debug_btn)

        bn = os.path.join(_KB_DIR, "BACK_button.png")
        bd = os.path.join(_KB_DIR, "BACK_button_pressed.png")
        self._back_btn = _ImageButton(
            normal_path=bn,
            pressed_path=bd,
            callback=self._on_back,
            size_hint=(None, None),
        )
        self.add_widget(self._back_btn)

    # ── Layout ────────────────────────────────────────────────────────────────

    def _reposition(self, *_):
        if self.width < 2 or self.height < 2:
            return

        for i, btn in enumerate(self._level_btns):
            x, y, w, h = self._img_to_screen_box(_ZONE_LVL[i])
            btn.pos  = (x, y)
            btn.size = (w, h)
            btn._redraw()
            self._stamp_widgets[i].pos  = (x, y)
            self._stamp_widgets[i].size = (w, h)
            self._stamp_widgets[i]._redraw()

        if self._hint_widget and self._hint_level_idx is not None:
            x, y, w, h = self._img_to_screen_box(_ZONE_LVL[self._hint_level_idx])
            scale = 1.4
            dw, dh = w * scale, h * scale
            self._hint_widget.pos  = (x - (dw - w) / 2, y - (dh - h) / 2 + h * 0.15)
            self._hint_widget.size = (dw, dh)
            self._hint_widget._redraw()

        x, y, w, h = self._img_to_screen_box(_ZONE_ENDLESS)
        self._endless_btn.pos  = (x, y)
        self._endless_btn.size = (w, h)
        self._endless_btn._redraw()

        x, y, w, h = self._img_to_screen_box(_ZONE_BACK)
        self._back_btn.pos  = (x, y)
        self._back_btn.size = (w, h)
        self._back_btn._redraw()

        if self._debug_btn:
            dbg_w = min(self.width * 0.22, 240)
            self._debug_btn.pos  = (8, self.height - 44)
            self._debug_btn.size = (dbg_w, 36)
            self._debug_btn._redraw()

    # ── State refresh ─────────────────────────────────────────────────────────

    def on_enter(self):
        audio_manager.start_cafe_ambiance()
        player = get_current_player()
        if not player:
            return
        progress = get_kitchen_level_progress(player["name"])

        for i, btn in enumerate(self._level_btns):
            n         = i + 1
            unlocked  = is_kitchen_level_unlocked(player["name"], n)
            completed = progress.get(n, {}).get("completed", False)
            cfg       = KITCHEN_LEVELS[n]

            if completed:
                btn._bg_color  = (0, 0, 0, 0)
                btn._txt_color = (0, 0, 0, 0)
                btn._enabled   = True
                btn._text      = ""
                self._stamp_widgets[i].set_visible(True)
            elif unlocked:
                btn._bg_color  = (0, 0, 0, 0)
                btn._txt_color = _COLOR_AVAIL_TXT
                btn._enabled   = True
                btn._text      = f"{n}. {cfg['name'].upper()}"
                self._stamp_widgets[i].set_visible(False)
            else:
                btn._bg_color  = (0, 0, 0, 0)
                btn._txt_color = _COLOR_LOCKED_TXT
                btn._enabled   = False
                btn._text      = f"{n}. ???"
                self._stamp_widgets[i].set_visible(False)

            btn._label.text  = btn._text
            btn._label.color = btn._txt_color
            btn._redraw()

        next_idx = None
        for i in range(KITCHEN_TOTAL_LEVELS):
            n = i + 1
            if is_kitchen_level_unlocked(player["name"], n) and not progress.get(n, {}).get("completed", False):
                next_idx = i
                break
        self._hint_level_idx = next_idx
        if self._hint_widget:
            self._hint_widget.set_visible(next_idx is not None)

        endless_on = is_kitchen_endless_unlocked(player["name"])
        self._endless_btn._enabled   = endless_on
        self._endless_btn._txt_color = _COLOR_ENDLESS_ON if endless_on else _COLOR_ENDLESS_OFF
        self._endless_btn._label.color = self._endless_btn._txt_color
        self._endless_btn._redraw()

        # Swap background based on endless unlock state
        bg = _BG_IMG_ENDLESS if endless_on else _BG_IMG
        self._bg_widget.set_source(bg)

        self._reposition()

    # ── Navigation ────────────────────────────────────────────────────────────

    def _on_level(self, level_num):
        player = get_current_player()
        if not player or not is_kitchen_level_unlocked(player["name"], level_num):
            return
        audio_manager.play_button_wood()
        has_tutorial = os.path.isfile(
            os.path.join(_ASSETS, "tutorial", f"kitchen_tutorial_lvl{level_num}_1.png"))
        if has_tutorial and not is_kitchen_level_tutorial_done(player["name"], level_num):
            tut = self.manager.get_screen("kitchen_tutorial")
            tut.level_num = level_num
            self.manager.current = "kitchen_tutorial"
            return
        if level_num == 1:
            game = self.manager.get_screen("kitchen_gameplay")
            game.level_num = 1
            self.manager.current = "kitchen_gameplay"
        else:
            intro = self.manager.get_screen("kitchen_victor_intro")
            intro.level_num = level_num
            self.manager.current = "kitchen_victor_intro"

    def _on_endless(self):
        audio_manager.play_button_wood()
        game = self.manager.get_screen("kitchen_gameplay")
        game.level_num = 0
        self.manager.current = "kitchen_gameplay"

    def _on_debug_unlock(self):
        player = get_current_player()
        if player:
            debug_unlock_kitchen_endless(player["name"])
            self.on_enter()

    def _on_back(self):
        audio_manager.play_button_wood()
        self.manager.current = "cafe_hub"
