"""
screens/opponent_select.py – Choose which cat to play against.

Background: choose_opponent.png (3915 × 1773 px) shows all four cat cards.
Invisible _CardZone widgets sit over each card; tapping one selects it.
BACK and READY key-buttons handle navigation.

To adjust hit-zones:
  1. Open choose_opponent.png in an image editor.
  2. Measure each card's bounding box in pixels (left, top, right, bottom).
  3. Update _ZONE_CATS below.
  4. Set DEBUG_HITBOXES = True in game_constants.py to see coloured overlays.
"""

import os

from kivy.uix.floatlayout import FloatLayout
from kivy.uix.widget import Widget
from kivy.graphics import Color, Rectangle
from kivy.core.image import Image as CoreImage
from kivy.core.audio import SoundLoader
from kivy.clock import Clock

_TEX_CACHE: dict = {}   # path → texture; avoids re-decoding cat frames between visits

from game_constants import (
    OPPONENT_ORDER,
    COLOR_BG,
    DEBUG_HITBOXES,
)
from screens.settings import _KeyButton
import game_settings
import audio_manager

_ASSETS = os.path.join(os.path.dirname(__file__), "..", "assets")
_KB_DIR = os.path.join(_ASSETS, "keyboard buttons")
_BG     = os.path.join(_ASSETS, "screens", "choose_opponent.png")

# choose_opponent.png source dimensions
_BG_W = 3915
_BG_H = 1773

# ── Cat-card hit-zones (left, top, right, bottom) in choose_opponent.png pixels ──
# These define the TOUCH AREA for each card – the entire card should be clickable.
# Open the image in an editor, measure each card boundary, and update these values.
_ZONE_CATS = [
    (320,   304, 1069,  1398),  # slot 0 – oscar   (full card touch area)
    (1088, 304, 1948, 1398),  # slot 1 – mittens
    (2000, 304, 2780, 1398),  # slot 2 – hector
    (2846, 304, 3626, 1398),  # slot 3 – chili
]

# ── Oscar image position (left, top, right, bottom) in choose_opponent.png pixels ──
# Controls where choose_opp_oscar.png and the animation frames are drawn.
# Adjust this independently from _ZONE_CATS[0] to place the cat art precisely.
_ZONE_OSCAR_IMAGE = (469, 734, 984, 1163)

# ── Mittens image position (left, top, right, bottom) in choose_opponent.png pixels ──
# Controls where choose_opp_mittens.png and the animation frames are drawn.
# Adjust this independently from _ZONE_CATS[1] to place the cat art precisely.
_ZONE_MITTENS_IMAGE = (1280, 551, 1888, 1163)

# ── Hector image position (left, top, right, bottom) in choose_opponent.png pixels ──
# Controls where choose_opp_hector.png and the animation frames are drawn.
# Adjust this independently from _ZONE_CATS[2] to place the cat art precisely.
_ZONE_HECTOR_IMAGE = (2068, 551, 2672, 1163)

# ── Chili image position (left, top, right, bottom) in choose_opponent.png pixels ──
# Controls where choose_opp_chili.png and the animation frames are drawn.
# Adjust this independently from _ZONE_CATS[3] to place the cat art precisely.
_ZONE_CHILI_IMAGE = (3026, 551, 3431, 1163)

# Back / Ready buttons (same reference coord space as settings.png)
_ZONE_BACK  = (69,   1506, 501,  1713)
_ZONE_READY = (3414, 1506, 3846, 1713)

# Fine-tune button positions in screen pixels (dx, dy)
_BACK_OFFSET  = (0, 0)
_READY_OFFSET = (0, 0)

# Debug overlay colours per card slot (shown when DEBUG_HITBOXES = True)
_DBG_COLORS = [
    (0.00, 0.80, 1.00, 0.45),  # cyan   – oscar
    (0.00, 1.00, 0.40, 0.45),  # green  – mittens
    (1.00, 0.60, 0.00, 0.45),  # orange – hector
    (0.80, 0.00, 1.00, 0.45),  # purple – chili
]


# ══════════════════════════════════════════════════════════════════
# _FillWidthBg – background image that always fills screen width
# ══════════════════════════════════════════════════════════════════

class _FillWidthBg(Widget):
    """Always scales the image to fill the full screen width.
    Crops top/bottom symmetrically if the scaled image overflows;
    centres (letterboxes) it vertically if it is shorter than the screen."""

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

    def set_texture(self, texture):
        """Swap to a different texture and refresh the display."""
        if texture is not None:
            self._texture = texture
        self._update()

    def _update(self, *_):
        if not self._texture:
            return
        tex_w, tex_h = self._texture.size
        w, h = self.size
        if w == 0 or h == 0 or tex_w == 0 or tex_h == 0:
            return
        scale    = w / tex_w
        scaled_h = scale * tex_h
        if scaled_h >= h:
            # Fill width; crop top/bottom symmetrically
            crop_v = (scaled_h - h) / (2 * scaled_h)
            rx, ry, rw, rh = self.x, self.y, w, h
            tc = (0.0, 1.0 - crop_v, 1.0, 1.0 - crop_v,
                  1.0, crop_v,       0.0, crop_v)
        else:
            # Fill width; letterbox (centre) vertically
            ry = self.y + (h - scaled_h) / 2
            rx, rw, rh = self.x, w, scaled_h
            tc = (0.0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0)
        self._rect.texture    = self._texture
        self._rect.pos        = (rx, ry)
        self._rect.size       = (rw, rh)
        self._rect.tex_coords = tc


# ══════════════════════════════════════════════════════════════════
# _AnimatedCardZone – image overlay with idle/animated states
# ══════════════════════════════════════════════════════════════════

class _AnimatedCardZone(Widget):
    """Card zone that draws a static image when idle and plays a looping
    frame animation while selected.  Touch handling works identically to
    _CardZone; the debug overlay is drawn on top of the image."""

    ANIM_FPS = 4   # frames per second for the selection animation

    def __init__(self, cat_key, static_path, anim_paths, dbg_color, on_select_cb, **kwargs):
        super().__init__(**kwargs)
        self._cat_key      = cat_key
        self._dbg_color    = dbg_color
        self._on_select_cb = on_select_cb
        self._selected     = False
        self._anim_frame   = 0
        self._clock_event  = None

        self._tex_static = self._load(static_path)
        self._tex_frames = [self._load(p) for p in anim_paths]

        # Image draw area – set via set_img_bounds(); falls back to widget bounds
        self._img_pos  = None
        self._img_size = None

        self.bind(pos=self._redraw, size=self._redraw)

    @staticmethod
    def _load(path):
        if path not in _TEX_CACHE:
            try:
                _TEX_CACHE[path] = CoreImage(path).texture
            except Exception:
                _TEX_CACHE[path] = None
        return _TEX_CACHE[path]

    def set_img_bounds(self, pos, size):
        """Set where the image is drawn, independent of the touch hit-zone."""
        self._img_pos  = pos
        self._img_size = size
        self._redraw()

    def set_selected(self, val):
        self._selected = val
        if val:
            self._anim_frame = 0
            if self._clock_event is None:
                self._clock_event = Clock.schedule_interval(
                    self._tick, 1.0 / self.ANIM_FPS
                )
        else:
            if self._clock_event is not None:
                self._clock_event.cancel()
                self._clock_event = None
        self._redraw()

    def _tick(self, _dt):
        frames = [f for f in self._tex_frames if f is not None]
        if frames:
            self._anim_frame = (self._anim_frame + 1) % len(frames)
        self._redraw()

    def _redraw(self, *_):
        self.canvas.clear()
        if self.width == 0 or self.height == 0:
            return
        frames = [f for f in self._tex_frames if f is not None]
        if self._selected and frames:
            tex = frames[self._anim_frame % len(frames)]
        else:
            tex = self._tex_static
        ipos  = self._img_pos  if self._img_pos  is not None else self.pos
        isize = self._img_size if self._img_size is not None else self.size
        with self.canvas:
            if tex:
                Color(1, 1, 1, 1)
                Rectangle(texture=tex, pos=ipos, size=isize)
            if DEBUG_HITBOXES:
                # Cyan tint over the IMAGE area
                Color(0.00, 0.80, 1.00, 0.30)
                Rectangle(pos=ipos, size=isize)
                # Full card touch zone outline
                Color(*self._dbg_color)
                Rectangle(pos=self.pos, size=self.size)

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self._on_select_cb(self._cat_key)
            return True
        return super().on_touch_down(touch)


# ══════════════════════════════════════════════════════════════════
# OpponentSelectScreen
# ══════════════════════════════════════════════════════════════════

class OpponentSelectScreen(FloatLayout):
    def __init__(self, **kwargs):
        self.name    = kwargs.pop('name', 'opponent_select')
        self.manager = None
        super().__init__(**kwargs)
        self.player_name = ''
        self.player_icon = None
        self._selected   = 'mittens'
        self._zones      = {}
        _snd_dir = os.path.join(_ASSETS, "sounds")
        self._snd_spotlight = SoundLoader.load(os.path.join(_snd_dir, "spotlight.mp3"))
        self._ui_built = False   # _build_ui() deferred to first on_enter

    # ── Coordinate mapping ────────────────────────────────────────

    def _img_to_screen_box(self, zone):
        """Convert (left, top, right, bottom) in choose_opponent.png pixels to
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
            # Crop top/bottom
            crop_y = (scaled_h - scr_h) / 2
            sy = lambda iy: scr_h - (iy * scale - crop_y)
        else:
            # Letterbox: image centred vertically
            sy = lambda iy: (scr_h + scaled_h) / 2 - iy * scale
        x0, x1       = sx(l), sx(r)
        y_top, y_bot = sy(t), sy(b)
        return x0, y_bot, x1 - x0, y_top - y_bot

    def _reposition_widgets(self, *_):
        if self.width == 0 or self.height == 0:
            return
        for key, zone in zip(OPPONENT_ORDER, _ZONE_CATS):
            widget = self._zones.get(key)
            if widget:
                x, y, w, h = self._img_to_screen_box(zone)
                widget.pos  = (x, y)
                widget.size = (w, h)

        # Each cat's image drawn at its own zone, separate from the card touch area
        _img_zones = {
            'oscar':   _ZONE_OSCAR_IMAGE,
            'mittens': _ZONE_MITTENS_IMAGE,
            'hector':  _ZONE_HECTOR_IMAGE,
            'chili':   _ZONE_CHILI_IMAGE,
        }
        for key, img_zone in _img_zones.items():
            widget = self._zones.get(key)
            if isinstance(widget, _AnimatedCardZone):
                ix, iy, iw, ih = self._img_to_screen_box(img_zone)
                widget.set_img_bounds((ix, iy), (iw, ih))

        x, y, w, h = self._img_to_screen_box(_ZONE_BACK)
        dx, dy = _BACK_OFFSET
        self._back_btn.pos  = (x + dx, y + dy)
        self._back_btn.size = (w, h)

        x, y, w, h = self._img_to_screen_box(_ZONE_READY)
        dx, dy = _READY_OFFSET
        self._ready_btn.pos  = (x + dx, y + dy)
        self._ready_btn.size = (w, h)

    # ── UI ────────────────────────────────────────────────────────

    def _build_ui(self):
        # Solid fallback background colour
        with self.canvas.before:
            Color(*COLOR_BG)
            self._bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(
            pos=lambda *_: setattr(self._bg_rect, 'pos',  self.pos),
            size=lambda *_: setattr(self._bg_rect, 'size', self.size),
        )

        # Background image (always fills width)
        self._bg_widget = _FillWidthBg(
            source=_BG,
            size_hint=(1, 1),
            pos_hint={'x': 0, 'y': 0},
        )
        self.add_widget(self._bg_widget)

        # Load spotlight textures for each cat
        def _load_tex(name):
            try:
                return CoreImage(os.path.join(_ASSETS, name)).texture
            except Exception:
                return None

        self._spotlight_textures = {
            'oscar':   _load_tex('disco/spotlight_oscar.png'),
            'mittens': _load_tex('disco/spotlight_mittens.png'),
            'hector':  _load_tex('disco/spotlight_hector.png'),
            'chili':   _load_tex('disco/spotlight_chili.png'),
        }

        # Card zones – all cats get animated image overlays
        _anim_configs = {
            'oscar':   ("screens/choose_opp_oscar.png",   [f"characters/oscar_animation_{i}.png"   for i in range(1, 6)]),
            'mittens': ("screens/choose_opp_mittens.png", [f"characters/mittens_animation_{i}.png" for i in range(1, 6)]),
            'hector':  ("screens/choose_opp_hector.png",  [f"characters/hector_animation_{i}.png"  for i in range(1, 5)]),
            'chili':   ("screens/choose_opp_chili.png",   [f"characters/chili_animation_{i}.png"   for i in range(1, 5)]),
        }
        for key, dbg_col in zip(OPPONENT_ORDER, _DBG_COLORS):
            static, frames = _anim_configs[key]
            zone_widget = _AnimatedCardZone(
                cat_key=key,
                static_path=os.path.join(_ASSETS, static),
                anim_paths=[os.path.join(_ASSETS, f) for f in frames],
                dbg_color=dbg_col,
                on_select_cb=self._on_card_select,
                size_hint=(None, None),
            )
            self._zones[key] = zone_widget
            self.add_widget(zone_widget)

        # Pre-select Mittens
        self._zones['mittens'].set_selected(True)

        # READY button (right side)
        rn = os.path.join(_KB_DIR, "READY_button.png")
        rd = os.path.join(_KB_DIR, "READY_button_pressed.png")
        self._ready_btn = _KeyButton(
            img_normal=rn,
            img_pressed=rd,
            callback=self._on_play,
            size_hint=(None, None),
        )
        self.add_widget(self._ready_btn)

        # BACK button (left side)
        bn = os.path.join(_KB_DIR, "BACK_button.png")
        bd = os.path.join(_KB_DIR, "BACK_button_pressed.png")
        self._back_btn = _KeyButton(
            img_normal=bn,
            img_pressed=bd,
            callback=lambda: (audio_manager.play_button_wood(), setattr(self.manager, 'current', 'cafe_hub')),
            size_hint=(None, None),
        )
        self.add_widget(self._back_btn)
        self.bind(size=self._reposition_widgets, pos=self._reposition_widgets)

    # ── Card selection ────────────────────────────────────────────

    def _play_spotlight(self):
        if self._snd_spotlight and game_settings.get("sfx_enabled"):
            self._snd_spotlight.volume = game_settings.get("sfx_volume")
            self._snd_spotlight.play()

    def _on_card_select(self, cat_key):
        if cat_key == self._selected:
            return
        self._zones[self._selected].set_selected(False)
        self._selected = cat_key
        self._zones[cat_key].set_selected(True)
        tex = self._spotlight_textures.get(cat_key)
        if tex:
            self._bg_widget.set_texture(tex)
        self._play_spotlight()

    # ── Navigation ────────────────────────────────────────────────

    def _on_play(self, *_):
        # Opponent select is only used for Endless mode
        game_screen = self.manager.get_screen('game')
        game_screen.player_name  = self.player_name
        game_screen.opponent     = self._selected
        game_screen.player_icon  = self.player_icon
        game_screen.mode         = "endless"
        game_screen.level_num    = None
        self.manager.current = 'game'

    # ── Screen lifecycle ──────────────────────────────────────────

    def on_leave(self):
        # Stop animation clocks if running when we navigate away
        for key in OPPONENT_ORDER:
            zone = self._zones.get(key)
            if isinstance(zone, _AnimatedCardZone) and zone._clock_event:
                zone._clock_event.cancel()
                zone._clock_event = None

    def on_enter(self):
        if not self._ui_built:
            self._build_ui()
            self._ui_built = True
            self._reposition_widgets()
        from game_utils import get_current_player
        player = get_current_player()
        if player:
            self.player_name = player["name"]
            self.player_icon = player.get("icon")
        if self._selected != 'mittens':
            self._zones[self._selected].set_selected(False)
            self._selected = 'mittens'
            self._zones['mittens'].set_selected(True)
        tex = self._spotlight_textures.get('mittens')
        if tex:
            self._bg_widget.set_texture(tex)
        self._play_spotlight()
