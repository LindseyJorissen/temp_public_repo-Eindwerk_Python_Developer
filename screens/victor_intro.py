"""
screens/victor_intro.py – Victor intro art screen shown before each bar duty level.

Level 1 cycles victor_intro_lvl1_1/2/3.png until tapped.
Other levels show a single static image.

Usage:
    victor = self.manager.get_screen("victor_intro")
    victor.level_num = 3          # set BEFORE navigating
    self.manager.current = "victor_intro"
"""

import os

from kivy.uix.floatlayout import FloatLayout
from kivy.graphics import Color, Rectangle
from kivy.core.image import Image as CoreImage
from kivy.clock import Clock

from game_constants import COLOR_BG
from game_utils import get_current_player
import audio_manager

_ASSETS    = os.path.join(os.path.dirname(__file__), "..", "assets")
_FRAME_DUR = 0.40
_TEX_CACHE: dict = {}   # path → texture; persists for the app lifetime


class VictorIntroScreen(FloatLayout):
    """Full-screen Victor art shown before a level starts.  Tap to begin."""

    def __init__(self, **kwargs):
        self.name     = kwargs.pop("name", "victor_intro")
        self.manager  = None
        super().__init__(**kwargs)

        self.level_num   = 1
        self._frames     = []
        self._frame_idx  = 0
        self._anim_clock = None

        with self.canvas:
            Color(1, 1, 1, 1)
            self._rect = Rectangle()

        self.bind(pos=self._draw, size=self._draw)

    # ── drawing ────────────────────────────────────────────────────────────────

    def _draw(self, *_):
        """Fill-width, crop-or-letterbox vertically — same as cafe hub."""
        tex = self._rect.texture
        if tex is None:
            return
        tw, th = tex.size
        w, h = self.size
        if w == 0 or h == 0 or tw == 0 or th == 0:
            return
        scale    = w / tw
        scaled_h = th * scale
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

    # ── texture loading ────────────────────────────────────────────────────────

    def _load_tex(self, path):
        if path not in _TEX_CACHE:
            tex = CoreImage(path).texture
            tex.mag_filter = "nearest"
            tex.min_filter = "nearest"
            _TEX_CACHE[path] = tex
        return _TEX_CACHE[path]

    # ── frame cycling ──────────────────────────────────────────────────────────

    def _set_frame(self, idx):
        self._frame_idx    = idx % len(self._frames)
        self._rect.texture = self._frames[self._frame_idx]
        self._draw()

    def _next_frame(self, dt):
        self._set_frame(self._frame_idx + 1)

    def _stop_anim(self):
        if self._anim_clock:
            self._anim_clock.cancel()
            self._anim_clock = None

    # ── lifecycle ─────────────────────────────────────────────────────────────

    def on_enter(self):
        self._stop_anim()
        self._frames    = []
        self._frame_idx = 0

        if self.level_num == 1:
            for i in range(1, 5):
                p = os.path.join(_ASSETS, "characters",
                                 f"victor_intro_lvl1_{i}.png")
                try:
                    self._frames.append(self._load_tex(p))
                except Exception:
                    pass

        if len(self._frames) > 1:
            self._set_frame(0)
            self._anim_clock = Clock.schedule_interval(self._next_frame, _FRAME_DUR)
        else:
            self._frames = []
            path = os.path.join(_ASSETS, "characters",
                                f"victor_intro_lvl{self.level_num}.png")
            try:
                self._rect.texture = self._load_tex(path)
            except Exception:
                self._rect.texture = None
            self._draw()

    def on_leave(self):
        self._stop_anim()

    # ── input ─────────────────────────────────────────────────────────────────

    def on_touch_down(self, touch):
        self._stop_anim()
        audio_manager.play_button_wood()
        self._go_to_game()
        return True

    def _go_to_game(self):
        player = get_current_player()
        game = self.manager.get_screen("game")
        game.mode      = "level"
        game.level_num = self.level_num
        if player:
            game.player_name = player["name"]
            game.player_icon = player.get("icon")
        self.manager.current = "game"
