"""
screens/settings.py – Settings screen (music & SFX toggles + volume sliders).
Audio is not yet wired up in the Kivy port; these values are stored and
ready to be read by audio code once it is added.

Layout
------
Left  half  – music and SFX controls
Right half  – staff roster (2 rows × 3 cols, paginated)
"""

import os

from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.widget import Widget
from kivy.graphics import Color, Rectangle, RoundedRectangle
from kivy.core.image import Image as CoreImage
from kivy.core.audio import SoundLoader

import game_settings
import audio_manager
from game_constants import (
    COLOR_BG, COLOR_BTN, COLOR_BTN_TEXT,
    DEBUG_HITBOXES,
)
from game_utils import load_player_data, set_current_player, get_current_player, icon_path_polaroid, fsp
from screens.menu import CoverImage

_ASSETS     = os.path.join(os.path.dirname(__file__), "..", "assets")
_KB_DIR     = os.path.join(_ASSETS, "keyboard buttons")
_BG         = os.path.join(_ASSETS, "screens", "settings.png")
_SLIDER_DIR = os.path.join(_ASSETS, "settings slider")
_FONT       = os.path.join(_ASSETS, "fonts", "Pixelfont.ttf")


class _BgImage(CoverImage):
    """Always scales to full screen width; crops top/bottom symmetrically."""

    def _update(self, *_):
        tex_w, tex_h = self._texture.size
        w, h = self.size
        if w == 0 or h == 0 or tex_w == 0 or tex_h == 0:
            return
        scale    = w / tex_w
        scaled_h = tex_h * scale
        if scaled_h >= h:
            # Fill width; crop top/bottom symmetrically
            crop_v = (scaled_h - h) / (2 * scaled_h)
            self._rect.tex_coords = (0.0, 1.0 - crop_v, 1.0, 1.0 - crop_v,
                                     1.0, crop_v,        0.0, crop_v)
            self._rect.pos  = self.pos
            self._rect.size = self.size
        else:
            # Fill width; letterbox (image centred vertically)
            ry = self.y + (h - scaled_h) / 2
            self._rect.tex_coords = (0.0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0)
            self._rect.pos  = (self.x, ry)
            self._rect.size = (w, scaled_h)


_DBG_BACK    = (1.00, 0.80, 0.00, 0.40)   # amber – back button debug overlay

_BG_W        = 3915   # settings.png source width  (pixels)
_BG_H        = 1773   # settings.png source height (pixels)

_PAGE_SIZE   = 5   # player cards per page (slot 6 is always the new-player button)
_MAX_PLAYERS = 5   # hard cap on total players

# Pixel bounding boxes (left, top, right, bottom) measured in settings.png
# Open settings.png in an image editor and update these if the art moves.
_ZONE_BACK  = (69, 1506, 501, 1713)   # BACK key bottom-left

# Six individually positionable slots (left, top, right, bottom) in settings.png pixels.
# Slots 0-4 = player polaroids, slot 5 = new-player button.
# Measure each cell in your image editor and update accordingly.
_ZONE_SLOTS = [
    (2152,  315, 2593,  900),  # slot 0 – row 0, col 0
    (2680,  315, 3121,  900),  # slot 1 – row 0, col 1
    (3206,  315, 3647,  900),  # slot 2 – row 0, col 2
    (2152,  960, 2588, 1545),  # slot 3 – row 1, col 0
    (2680,  960, 3116, 1545),  # slot 4 – row 1, col 1
    (3256,  1100, 3697, 1541),  # slot 5 – row 1, col 2  (new-player button)
]

# ── Vertical volume slider zones (left, top, right, bottom) in settings.png pixels ──
# Open settings.png in your image editor and adjust these to sit over the brown bars.
_ZONE_MUSIC_SLIDER = (555,  466,  835, 1125)   # MUSIC volume slider
_ZONE_SFX_SLIDER   = (1224, 466, 1504, 1125)   # SOUND EFFECTS volume slider
_ZONE_GYRO_TOGGLE  = (1010, 1243, 1120, 1348)   # GYRO checkbox (below sliders)


# ── Pixel-perfect key button (no stretch / squish) ───────────────────────────

class _KeyButton(Widget):
    """Renders a button image with uniform scaling (no aspect-ratio distortion).
    The full widget bounds act as the touch target; the image is centred inside."""

    def __init__(self, img_normal, img_pressed, callback, **kwargs):
        super().__init__(**kwargs)
        self._callback = callback
        self._pressed  = False
        self._tex_n = None
        self._tex_d = None
        for attr, path in (("_tex_n", img_normal), ("_tex_d", img_pressed)):
            if path and os.path.isfile(path):
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
        dw    = tw * scale
        dh    = th * scale
        x     = self.x + (self.width  - dw) / 2
        y     = self.y + (self.height - dh) / 2
        with self.canvas:
            Color(1, 1, 1, 1)
            Rectangle(texture=tex, pos=(x, y), size=(dw, dh))
            if DEBUG_HITBOXES:
                Color(1.0, 0.80, 0.0, 0.40)   # amber – full touch zone
                Rectangle(pos=self.pos, size=self.size)

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


# ── Player card widget ──────────────────────────────────────────────────────────

class _PlayerCard(Widget):
    """Polaroid card: icon image fills the whole slot; player name overlaid at the bottom."""

    def __init__(self, name, icon_key, is_active, callback, **kwargs):
        super().__init__(**kwargs)
        self._is_active = is_active
        self._cb = callback

        p = icon_path_polaroid(icon_key) if icon_key else None
        tex = None
        if p:
            try:
                tex = CoreImage(p).texture
            except Exception:
                pass

        with self.canvas.before:
            if tex:
                Color(1, 1, 1, 1)
                self._bg = Rectangle(texture=tex, pos=self.pos, size=self.size)
            else:
                Color(*COLOR_BTN)
                self._bg = RoundedRectangle(pos=self.pos, size=self.size, radius=[10])
        self._lbl = Label(
            text=name.upper(),
            font_size=fsp(20),
            bold=is_active,
            color=(0, 0, 0, 1) if is_active else COLOR_BTN_TEXT,
            font_name=_FONT,
            halign="center",
            valign="middle",
        )
        self.add_widget(self._lbl)
        self.bind(pos=self._upd, size=self._upd)

    def _upd(self, *_):
        self._bg.pos  = self.pos
        self._bg.size = self.size
        # Name sits in the bottom strip of the card
        lbl_h = self.height * 0.22
        self._lbl.pos       = (self.x, self.y)
        self._lbl.size      = (self.width, lbl_h)
        self._lbl.text_size = (self.width, lbl_h)
        if DEBUG_HITBOXES:
            self.canvas.after.clear()
            with self.canvas.after:
                Color(0.0, 0.80, 1.0, 0.35)   # cyan – player card touch zone
                Rectangle(pos=self.pos, size=self.size)

    def on_touch_down(self, touch):
        if self._cb and self.collide_point(*touch.pos):
            self._cb()
            return True
        return super().on_touch_down(touch)


class _NewPlayerCard(Widget):
    """Slot 6 in the roster grid: shows new_player.png; navigates to hiring if < max players."""

    def __init__(self, enabled, callback, **kwargs):
        super().__init__(**kwargs)
        self._enabled = enabled
        self._cb = callback
        p = os.path.join(_ASSETS, "screens", "new_player.png")
        try:
            self._tex = CoreImage(p).texture
        except Exception:
            self._tex = None
        self.bind(pos=self._draw, size=self._draw)

    def _draw(self, *_):
        self.canvas.clear()
        with self.canvas:
            if self._tex:
                Color(1, 1, 1, 1 if self._enabled else 0.4)
                Rectangle(texture=self._tex, pos=self.pos, size=self.size)
            else:
                Color(*(COLOR_BTN[:3] + (1 if self._enabled else 0.4,)))
                RoundedRectangle(pos=self.pos, size=self.size, radius=[10])
            if DEBUG_HITBOXES:
                Color(0.0, 1.0, 0.50, 0.40)   # green – new-player touch zone
                Rectangle(pos=self.pos, size=self.size)

    def on_touch_down(self, touch):
        if self._enabled and self.collide_point(*touch.pos):
            self._cb()
            return True
        return super().on_touch_down(touch)


# ── Vertical sprite-based volume slider ─────────────────────────────────────────

class _VolumeSlider(Widget):
    """Vertical volume slider drawn from 11 pre-rendered sprite frames.

    Frames in ``settings slider/``: 00.png (0 %) … 100.png (100 %).
    Drag up  → louder  (handle moves toward top).
    Drag down → quieter (handle moves toward bottom).
    ``on_change(value)`` is called with a float 0.0–1.0 whenever the value
    changes to a new 10 % step.
    """

    _STEPS = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]

    def __init__(self, initial_value=1.0, on_change=None, **kwargs):
        super().__init__(**kwargs)
        self._value     = max(0.0, min(1.0, initial_value))
        self._on_change = on_change
        self._textures  = {}

        for pct in self._STEPS:
            path = os.path.join(_SLIDER_DIR, f"{pct:02d}.png")
            if os.path.isfile(path):
                try:
                    self._textures[pct] = CoreImage(path).texture
                except Exception:
                    pass

        self.bind(pos=self._redraw, size=self._redraw)

    # ── public value property ───────────────────────────────────────────────

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, v):
        self._value = max(0.0, min(1.0, v))
        self._redraw()

    # ── internal helpers ────────────────────────────────────────────────────

    def _pct(self):
        """Round internal float to the nearest displayed 10 % step."""
        return round(self._value * 10) * 10   # 0, 10, 20, …, 100

    def _redraw(self, *_):
        self.canvas.clear()
        tex = self._textures.get(self._pct())
        if tex is None:
            return
        tw, th = tex.size
        if tw == 0 or th == 0 or self.width == 0 or self.height == 0:
            return
        # Uniform scale: fit the sprite inside the zone, centred
        scale = min(self.width / tw, self.height / th)
        dw    = tw * scale
        dh    = th * scale
        px    = self.x + (self.width  - dw) / 2
        py    = self.y + (self.height - dh) / 2
        with self.canvas:
            Color(1, 1, 1, 1)
            Rectangle(texture=tex, pos=(px, py), size=(dw, dh))
            if DEBUG_HITBOXES:
                Color(1.0, 0.50, 0.0, 0.40)   # orange – slider touch zone
                Rectangle(pos=self.pos, size=self.size)

    # ── touch handling ──────────────────────────────────────────────────────

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            touch.grab(self)
            self._update_from_touch(touch)
            return True
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if touch.grab_current is self:
            self._update_from_touch(touch)
            return True
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        if touch.grab_current is self:
            touch.ungrab(self)
            return True
        return super().on_touch_up(touch)

    def _update_from_touch(self, touch):
        if self.height == 0:
            return
        # Bottom of widget = 0.0 (quiet), top = 1.0 (loud)
        rel_y   = (touch.y - self.y) / self.height
        new_val = max(0.0, min(1.0, rel_y))
        old_pct = self._pct()
        self._value = new_val
        if self._pct() != old_pct:
            self._redraw()
        if self._on_change:
            self._on_change(new_val)


# ── Screen ──────────────────────────────────────────────────────────────────────

_UI_DIR = os.path.join(_ASSETS, "ui")


class _GyroToggle(Widget):
    """Checkbox image for the gyro tilt setting. Text is baked into the bg art."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._enabled = game_settings.get("gyro_enabled")

        def _load(name):
            try:
                return CoreImage(os.path.join(_UI_DIR, name)).texture
            except Exception:
                return None

        self._tex_on  = _load("checkbox_checked.png")
        self._tex_off = _load("checkbox_unchecked.png")
        self.bind(pos=self._redraw, size=self._redraw)

    def refresh(self):
        self._enabled = game_settings.get("gyro_enabled")
        self._redraw()

    def _redraw(self, *_):
        self.canvas.clear()
        if self.width < 2 or self.height < 2:
            return
        tex = self._tex_on if self._enabled else self._tex_off
        with self.canvas:
            Color(1, 1, 1, 1)
            if tex:
                tw, th = tex.size
                scale = min(self.width / tw, self.height / th)
                dw, dh = tw * scale, th * scale
                px = self.x + (self.width  - dw) / 2
                py = self.y + (self.height - dh) / 2
                Rectangle(texture=tex, pos=(px, py), size=(dw, dh))
            else:
                # fallback: drawn checkbox
                Color(0.55, 0.40, 0.20, 1)
                box = min(self.width, self.height) * 0.8
                bx  = self.x + (self.width  - box) / 2
                by  = self.y + (self.height - box) / 2
                RoundedRectangle(pos=(bx, by), size=(box, box), radius=[4])
                if self._enabled:
                    Color(0.30, 0.75, 0.30, 1)
                    RoundedRectangle(pos=(bx + 3, by + 3),
                                     size=(box - 6, box - 6), radius=[3])

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self._enabled = not self._enabled
            game_settings.set_value("gyro_enabled", self._enabled)
            audio_manager.play_button_wood()
            self._redraw()
            return True
        return False


class SettingsScreen(FloatLayout):

    def __init__(self, **kwargs):
        self.name          = kwargs.pop("name", "settings")
        self.manager       = None
        self.in_game       = False   # set True by GameScreen before navigating here
        self._roster_page  = 0
        self._slot_widgets = [None] * 6   # one widget per roster slot
        _snd_dir = os.path.join(_ASSETS, "sounds")
        self._snd_bell = SoundLoader.load(os.path.join(_snd_dir, "typewriter_bell.mp3"))
        super().__init__(**kwargs)
        self._build_ui()

    def on_enter(self):
        game_settings.load()
        self._refresh()
        self._roster_page = 0
        if self.in_game:
            # Show polaroids as decoration but non-clickable; hide nav arrows
            self._rebuild_roster(readonly=True)
            self._prev_arrow.opacity  = 0
            self._prev_arrow.disabled = True
            self._next_arrow.opacity  = 0
            self._next_arrow.disabled = True
        else:
            self._rebuild_roster()

    # ── coordinate mapping (matches _BgImage cover-scale) ──────────────────────

    def _img_to_screen_box(self, zone):
        """Convert (left, top, right, bottom) in settings.png pixels to
        (screen_x, screen_y, width, height) in Kivy coords."""
        l, t, r, b = zone
        scr_w, scr_h = self.width, self.height
        if scr_w == 0 or scr_h == 0:
            return 0, 0, 1, 1
        scale_x  = scr_w / _BG_W
        scaled_h = scale_x * _BG_H
        if scaled_h >= scr_h:
            # fit-to-width, crop top/bottom symmetrically
            scale  = scale_x
            crop_y = (scaled_h - scr_h) / 2   # screen-space pixels cropped off top
            sx = lambda ix: ix * scale
            sy = lambda iy: scr_h - (iy * scale - crop_y)
        else:
            # fill-width; letterbox (image centred vertically)
            sx = lambda ix: ix * scale_x
            sy = lambda iy: (scr_h + scaled_h) / 2 - iy * scale_x
        x0, x1       = sx(l), sx(r)
        y_top, y_bot = sy(t), sy(b)
        return x0, y_bot, x1 - x0, y_top - y_bot

    # ── build ──────────────────────────────────────────────────────────────────

    def _build_ui(self):
        with self.canvas.before:
            Color(*COLOR_BG)
            self._bg_rect = Rectangle(pos=self.pos, size=self.size)
            Color(1, 1, 1, 1)  # reset GL colour so child textures aren't tinted
        self.bind(pos=self._update_bg, size=self._update_bg)

        self.add_widget(_BgImage(
            source=_BG,
            size_hint=(1, 1),
            pos_hint={"x": 0, "y": 0},
        ))

        self._build_audio_panel()
        self._build_roster_panel()
        self._build_bottom_bar()
        self.bind(size=self._reposition_buttons, pos=self._reposition_buttons)

    # ── left column – audio ────────────────────────────────────────────────────

    def _build_audio_panel(self):
        self._music_slider = _VolumeSlider(
            initial_value=1.0,
            on_change=self._on_music_volume,
            size_hint=(None, None),
        )
        self.add_widget(self._music_slider)

        self._sfx_slider = _VolumeSlider(
            initial_value=1.0,
            on_change=self._on_sfx_volume,
            size_hint=(None, None),
        )
        self.add_widget(self._sfx_slider)

        self._gyro_toggle = _GyroToggle(size_hint=(None, None))
        self.add_widget(self._gyro_toggle)

    # ── right column – staff roster ────────────────────────────────────────────

    def _build_roster_panel(self):
        # Slot widgets are created/destroyed in _rebuild_roster and
        # positioned individually via _ZONE_SLOTS in _reposition_buttons.

        _dbg_arrow = (1.0, 0.0, 1.0, 0.45) if DEBUG_HITBOXES else COLOR_BTN

        # Left arrow (previous page)
        self._prev_arrow = Button(
            text="<", font_size=fsp(36), bold=True,
            font_name=_FONT,
            size_hint=(0.04, 0.20),
            pos_hint={"x": 0.52, "center_y": 0.55},
            background_normal="", background_color=_dbg_arrow, color=COLOR_BTN_TEXT,
            opacity=1 if DEBUG_HITBOXES else 0, disabled=True,
        )
        self._prev_arrow.bind(on_release=self._prev_roster_page)
        self.add_widget(self._prev_arrow)

        # Right arrow (next page)
        self._next_arrow = Button(
            text=">", font_size=fsp(36), bold=True,
            font_name=_FONT,
            size_hint=(0.04, 0.20),
            pos_hint={"x": 0.92, "center_y": 0.55},
            background_normal="", background_color=_dbg_arrow, color=COLOR_BTN_TEXT,
            opacity=1 if DEBUG_HITBOXES else 0, disabled=True,
        )
        self._next_arrow.bind(on_release=self._next_roster_page)
        self.add_widget(self._next_arrow)

    # ── bottom bar ─────────────────────────────────────────────────────────────

    def _build_bottom_bar(self):
        bn = os.path.join(_KB_DIR, "BACK_button.png")
        bd = os.path.join(_KB_DIR, "BACK_button_pressed.png")
        self._back_btn = _KeyButton(
            img_normal=bn,
            img_pressed=bd,
            callback=self._on_back,
            size_hint=(None, None),
        )
        self.add_widget(self._back_btn)

    def _reposition_buttons(self, *_):
        if self.width == 0 or self.height == 0:
            return
        x, y, w, h = self._img_to_screen_box(_ZONE_BACK)
        self._back_btn.pos  = (x, y)
        self._back_btn.size = (w, h)

        x, y, w, h = self._img_to_screen_box(_ZONE_MUSIC_SLIDER)
        self._music_slider.pos  = (x, y)
        self._music_slider.size = (w, h)

        x, y, w, h = self._img_to_screen_box(_ZONE_SFX_SLIDER)
        self._sfx_slider.pos  = (x, y)
        self._sfx_slider.size = (w, h)

        x, y, w, h = self._img_to_screen_box(_ZONE_GYRO_TOGGLE)
        self._gyro_toggle.pos  = (x, y)
        self._gyro_toggle.size = (w, h)

        for i, zone in enumerate(_ZONE_SLOTS):
            widget = self._slot_widgets[i] if i < len(self._slot_widgets) else None
            if widget is not None:
                x, y, w, h = self._img_to_screen_box(zone)
                widget.pos  = (x, y)
                widget.size = (w, h)

    # ── helpers ────────────────────────────────────────────────────────────────

    def _update_bg(self, *_):
        self._bg_rect.pos  = self.pos
        self._bg_rect.size = self.size

    def _refresh(self):
        music_vol = game_settings.get("music_volume")
        sfx_vol   = game_settings.get("sfx_volume")

        # Set without firing on_change (swap callback out temporarily)
        cb = self._music_slider._on_change
        self._music_slider._on_change = None
        self._music_slider.value = music_vol
        self._music_slider._on_change = cb

        cb = self._sfx_slider._on_change
        self._sfx_slider._on_change = None
        self._sfx_slider.value = sfx_vol
        self._sfx_slider._on_change = cb

        self._gyro_toggle.refresh()

    # ── callbacks ──────────────────────────────────────────────────────────────

    def _on_music_volume(self, value):
        game_settings.set_value("music_volume", round(value, 2))
        audio_manager.set_music_volume(value)

    def _on_sfx_volume(self, value):
        game_settings.set_value("sfx_volume", round(value, 2))
        if self._snd_bell and game_settings.get("sfx_enabled"):
            self._snd_bell.volume = value
            self._snd_bell.play()

    def _rebuild_roster(self, readonly=False):
        # Remove previous slot widgets from the screen
        for w in self._slot_widgets:
            if w is not None and w.parent is self:
                self.remove_widget(w)
        self._slot_widgets = [None] * 6

        data    = load_player_data()
        players = data.get("players", [])
        current = (get_current_player() or {}).get("name")
        total   = len(players)

        start        = self._roster_page * _PAGE_SIZE
        page_players = players[start : start + _PAGE_SIZE]

        # Slots 0-4: player cards or empty placeholders
        for i in range(_PAGE_SIZE):
            if i < len(page_players):
                p        = page_players[i]
                name     = p["name"]
                icon_key = p.get("icon")
                is_me    = (name == current)
                w = _PlayerCard(
                    name=name,
                    icon_key=icon_key,
                    is_active=is_me,
                    callback=None if readonly else (lambda n=name: self._on_switch_player(n)),
                    size_hint=(None, None),
                )
            else:
                w = Widget(size_hint=(None, None))
            self._slot_widgets[i] = w
            self.add_widget(w)

        # Slot 5: new-player button — hidden when readonly (in-game)
        is_last_page = (start + _PAGE_SIZE) >= total
        if not readonly and is_last_page:
            can_add = total < _MAX_PLAYERS
            w = _NewPlayerCard(
                enabled=can_add,
                callback=self._on_add_player,
                size_hint=(None, None),
            )
        else:
            w = Widget(size_hint=(None, None))
        self._slot_widgets[5] = w
        self.add_widget(w)

        # Apply pixel-accurate positions immediately
        self._reposition_buttons()

        has_prev = self._roster_page > 0
        has_next = (start + _PAGE_SIZE) < total
        # In debug mode keep arrows always visible so their zone is obvious
        self._prev_arrow.opacity  = 1 if (has_prev or DEBUG_HITBOXES) else 0
        self._prev_arrow.disabled = not has_prev
        self._next_arrow.opacity  = 1 if (has_next or DEBUG_HITBOXES) else 0
        self._next_arrow.disabled = not has_next

    def _prev_roster_page(self, *_):
        if self._roster_page > 0:
            audio_manager.play_button_wood()
            self._roster_page -= 1
            self._rebuild_roster()

    def _next_roster_page(self, *_):
        audio_manager.play_button_wood()
        self._roster_page += 1
        self._rebuild_roster()

    def _on_switch_player(self, name):
        audio_manager.play_paper_rustling()
        set_current_player(name)
        self._rebuild_roster()

    def _on_add_player(self, *_):
        self.manager.current = "hiring_sheet"

    def _on_back(self, *_):
        audio_manager.play_button_wood()
        if self.in_game:
            self.in_game = False
            self.manager.current = "game"
        else:
            self.manager.current = "cafe_hub"
