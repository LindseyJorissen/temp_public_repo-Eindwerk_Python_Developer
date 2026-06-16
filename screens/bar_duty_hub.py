"""
screens/bar_duty_hub.py – Bar Duty level-selection calendar screen.

Shows all 10 Bar Duty shift levels.  Completed levels are bright; locked
levels are dimmed.  The Endless Shift button only enables after all 10
levels are complete.

Background: bar_duty_hub.png (falls back to a solid colour until the art
is drawn).  Level buttons are drawn in code and will be replaceable with
pixel-perfect zones once the calendar art exists.
"""

import os

from kivy.uix.floatlayout import FloatLayout
from kivy.uix.widget import Widget
from kivy.uix.label import Label
from kivy.graphics import Color, Rectangle, RoundedRectangle
from kivy.core.image import Image as CoreImage

from game_constants import (
    COLOR_BG, COLOR_BTN, COLOR_BTN_PRESSED, COLOR_BTN_TEXT,
    COLOR_GOLD, COLOR_WHITE, COLOR_BLACK, DEBUG_HITBOXES,
)
from game_utils import (
    get_current_player, get_level_progress,
    is_level_unlocked, is_endless_unlocked, debug_unlock_endless, fsp,
)
from level_config import LEVELS, TOTAL_LEVELS
import audio_manager

_ASSETS = os.path.join(os.path.dirname(__file__), "..", "assets")
_KB_DIR = os.path.join(_ASSETS, "keyboard buttons")
_FONT   = os.path.join(_ASSETS, "fonts", "Pixelfont.ttf")

# Placeholder background – replace with real calendar art path when available
_BG_IMG        = os.path.join(_ASSETS, "screens", "bar_duty_hub.png")
_BG_IMG_ENDLESS = os.path.join(_ASSETS, "screens", "endless_bar_duty.png")

# Source image dimensions (used for pixel-perfect coordinate mapping)
_BG_W = 3915
_BG_H = 1773

# Calendar cell pixel zones (left, top, right, bottom) in source image coords
_ZONE_LVL = [
    (1548,  432, 1926,  765),   # Level 1  – row 1, col 1
    (1935,  432, 2322,  765),   # Level 2  – row 1, col 2
    (2331,  432, 2709,  765),   # Level 3  – row 1, col 3
    (2718,  432, 3114,  765),   # Level 4  – row 1, col 4
    (3123,  432, 3501,  765),   # Level 5  – row 1, col 5
    (1548,  774, 1926, 1107),   # Level 6  – row 2, col 1
    (1935,  774, 2322, 1107),   # Level 7  – row 2, col 2
    (2331,  774, 2709, 1107),   # Level 8  – row 2, col 3
    (2718,  774, 3114, 1107),   # Level 9  – row 2, col 4
    (3123,  774, 3501, 1107),   # Level 10 – row 2, col 5
]
_ZONE_ENDLESS = (1548, 1170, 3501, 1494)  # Wide banner row
_ZONE_BACK    = (  69, 1506,  501, 1713)  # Back button – bottom-left brick area

_STAMP_IMG = os.path.join(_ASSETS, "screens", "level_complete.png")
_HINT_IMG  = os.path.join(_ASSETS, "ui", "nextlevelhint.png")


# ── Colour helpers ────────────────────────────────────────────────────────────

_COLOR_LOCKED_TXT= (0.55, 0.55, 0.55, 1.0)   # dim grey for locked
_COLOR_DONE_TXT  = (1.00, 1.00, 1.00, 1.0)   # white for completed
_COLOR_AVAIL_TXT = (1.00, 1.00, 1.00, 1.0)   # white for available
_COLOR_ENDLESS_OFF = (0.18, 0.18, 0.18, 1.0)
_COLOR_ENDLESS_TXT_OFF = (0.40, 0.40, 0.40, 1.0)
_COLOR_ENDLESS_ON  = (0.50, 0.12, 0.50, 1.0)
_COLOR_ENDLESS_TXT = (1.00, 0.80, 1.00, 1.0)


# ── Level-complete stamp overlay ─────────────────────────────────────────────

class _StampWidget(Widget):
    """Draws level_complete.png fitted inside its bounds; hidden by default."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        try:
            self._texture = CoreImage(_STAMP_IMG).texture
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
        dw = tw * scale
        dh = th * scale
        x  = self.x + (self.width  - dw) / 2
        y  = self.y + (self.height - dh) / 2
        with self.canvas:
            Color(1, 1, 1, 1)
            Rectangle(texture=self._texture, pos=(x, y), size=(dw, dh))

    def on_touch_down(self, touch):
        return False   # let touches fall through to the button beneath


# ── Next-level hint overlay ───────────────────────────────────────────────────

class _HintWidget(Widget):
    """Draws nextlevelhint.png fitted inside its bounds; hidden by default.
    Passes all touches through so the level button underneath still works."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        try:
            self._texture = CoreImage(_HINT_IMG).texture
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
        dw = tw * scale
        dh = th * scale
        x  = self.x + (self.width  - dw) / 2
        y  = self.y + (self.height - dh) / 2
        with self.canvas:
            Color(1, 1, 1, 1)
            Rectangle(texture=self._texture, pos=(x, y), size=(dw, dh))

    def on_touch_down(self, touch):
        return False   # let touches fall through to the button beneath


# ── Generic tap button ────────────────────────────────────────────────────────

class _TapButton(Widget):
    """Simple rounded-rect button drawn on canvas."""

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
            text=text,
            font_name=_FONT,
            font_size=fsp(font_size),
            color=txt_color,
            size_hint=(None, None),
            halign="center",
            valign="middle",
        )
        self.add_widget(self._label)
        self.bind(pos=self._redraw, size=self._redraw)

    def _redraw(self, *_):
        self.canvas.clear()
        color = list(self._bg_color)
        if self._pressed and self._enabled:
            color = [min(1.0, c * 1.4) for c in color[:3]] + [color[3]]
        # Only draw the rect when there is an actual background colour;
        # drawing Color(0,0,0,0)+RoundedRectangle punches holes in Kivy's canvas.
        if color[3] > 0:
            with self.canvas:
                Color(*color)
                RoundedRectangle(pos=self.pos, size=self.size, radius=[8])
                if DEBUG_HITBOXES:
                    Color(1.0, 0.0, 0.0, 0.3)
                    Rectangle(pos=self.pos, size=self.size)
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


# ── Fill-width background (same pattern as other screens) ────────────────────

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


# ── Screen ────────────────────────────────────────────────────────────────────

class BarDutyHubScreen(FloatLayout):
    """Bar Duty calendar screen showing all 10 levels and the Endless Shift."""

    def __init__(self, **kwargs):
        self.name    = kwargs.pop("name", "bar_duty_hub")
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

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        # Solid colour background (always)
        with self.canvas.before:
            Color(*COLOR_BG)
            self._bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(
            size=lambda *_: setattr(self._bg_rect, "size", self.size),
            pos =lambda *_: setattr(self._bg_rect, "pos",  self.pos),
        )

        # Art background (optional – replaces solid colour when image exists)
        self._bg_widget = _FillWidthBg(
            source=_BG_IMG,
            size_hint=(1, 1),
            pos_hint={"x": 0, "y": 0},
        )
        self.add_widget(self._bg_widget)

        # Stamp overlays – added before buttons so buttons stay on top for touches
        for _ in range(TOTAL_LEVELS):
            stamp = _StampWidget(size_hint=(None, None))
            self._stamp_widgets.append(stamp)
            self.add_widget(stamp)

        # Next-level hint overlay (single widget, repositioned to the right cell)
        self._hint_widget = _HintWidget(size_hint=(None, None))
        self.add_widget(self._hint_widget)

        # 10 level buttons (2 rows × 5 columns)
        for n in range(1, TOTAL_LEVELS + 1):
            cfg  = LEVELS[n]
            btn  = _TapButton(
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

        # Endless Shift button
        self._endless_btn = _TapButton(
            text="ENDLESS SHIFT",
            callback=self._on_endless,
            bg_color=(0, 0, 0, 0),
            txt_color=_COLOR_ENDLESS_TXT_OFF,
            font_size=12,
            enabled=False,
            size_hint=(None, None),
        )
        self.add_widget(self._endless_btn)

        # Debug: unlock endless mode instantly (only when DEBUG_HITBOXES = True)
        if DEBUG_HITBOXES:
            self._debug_btn = _TapButton(
                text="[DBG] UNLOCK ENDLESS",
                callback=self._on_debug_unlock,
                bg_color=(0.60, 0.05, 0.60, 0.85),
                txt_color=(1.0, 1.0, 0.0, 1.0),
                font_size=11,
                size_hint=(None, None),
            )
            self.add_widget(self._debug_btn)

        # Back button (image-based, falls back to text button)
        bn = os.path.join(_KB_DIR, "BACK_button.png")
        bd = os.path.join(_KB_DIR, "BACK_button_pressed.png")
        self._back_btn = _ImageButton(
            normal_path=bn,
            pressed_path=bd,
            callback=self._on_back,
            size_hint=(None, None),
        )
        self.add_widget(self._back_btn)

    # ── Coordinate mapping (same pattern as cafe_hub / leaderboard) ──────────

    def _img_to_screen_box(self, zone):
        """Convert (left, top, right, bottom) in image pixels to
        (screen_x, screen_y, width, height) in Kivy coords.
        Matches _FillWidthBg: always fill-width, crop or letterbox vertically."""
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
            scale  = 1.4
            dw = w * scale
            dh = h * scale
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
            dbg_h = 36
            self._debug_btn.pos  = (8, self.height - dbg_h - 8)
            self._debug_btn.size = (dbg_w, dbg_h)
            self._debug_btn._redraw()

    # ── State refresh on enter ────────────────────────────────────────────────

    def on_enter(self):
        audio_manager.start_cafe_ambiance()
        player = get_current_player()
        if not player:
            return
        progress = get_level_progress(player["name"])

        for i, btn in enumerate(self._level_btns):
            n         = i + 1
            unlocked  = is_level_unlocked(player["name"], n)
            completed = progress.get(n, {}).get("completed", False)
            cfg       = LEVELS[n]

            if completed:
                # Transparent, no text — stamp image says it all
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

        # Show hint circle on the first unlocked-but-not-completed level
        next_idx = None
        for i in range(TOTAL_LEVELS):
            n = i + 1
            if is_level_unlocked(player["name"], n) and not progress.get(n, {}).get("completed", False):
                next_idx = i
                break
        self._hint_level_idx = next_idx
        if self._hint_widget:
            self._hint_widget.set_visible(next_idx is not None)

        endless_on = is_endless_unlocked(player["name"])
        bg = _BG_IMG_ENDLESS if endless_on else _BG_IMG
        self._bg_widget.set_source(bg)

        self._endless_btn._enabled   = endless_on
        self._endless_btn._bg_color  = (0, 0, 0, 0)
        self._endless_btn._txt_color = _COLOR_ENDLESS_TXT if endless_on else _COLOR_ENDLESS_TXT_OFF
        self._endless_btn._label.color = self._endless_btn._txt_color
        self._endless_btn._redraw()

        self._reposition()

    # ── Navigation ────────────────────────────────────────────────────────────

    def _on_level(self, level_num):
        player = get_current_player()
        if not player or not is_level_unlocked(player["name"], level_num):
            return
        victor = self.manager.get_screen("victor_intro")
        victor.level_num = level_num
        self.manager.current = "victor_intro"

    def _on_endless(self):
        self.manager.current = "opponent_select"

    def _on_debug_unlock(self):
        player = get_current_player()
        if player:
            debug_unlock_endless(player["name"])
            self.on_enter()   # refresh UI immediately

    def _on_back(self):
        audio_manager.play_button_wood()
        self.manager.current = "cafe_hub"


# ── Image-based button (same as leaderboard _BackButton pattern) ─────────────

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
                Color(*(_COLOR_LOCKED if not self._pressed else _COLOR_AVAILABLE))
                RoundedRectangle(pos=self.pos, size=self.size, radius=[6])
            return
        tw, th = tex.size
        if tw == 0 or th == 0 or self.width == 0 or self.height == 0:
            return
        scale = min(self.width / tw, self.height / th)
        dw = tw * scale
        dh = th * scale
        x  = self.x + (self.width  - dw) / 2
        y  = self.y + (self.height - dh) / 2
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
