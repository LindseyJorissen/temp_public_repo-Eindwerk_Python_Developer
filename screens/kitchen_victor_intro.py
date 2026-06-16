"""
screens/kitchen_victor_intro.py – Pre-level intro screen for Kitchen Duty.

Shows kitchen_intro_lvlN.png full-screen; tap to continue.

Attributes set by the calling screen before navigating here:
    kitchen_victor_intro.level_num  (int)
"""

import os

from kivy.uix.floatlayout import FloatLayout
from kivy.graphics import Color, Rectangle
from kivy.core.image import Image as CoreImage

from game_constants import COLOR_BG
import audio_manager

_ASSETS    = os.path.join(os.path.dirname(__file__), "..", "assets")
_TEX_CACHE: dict = {}   # path → texture; persists for the app lifetime


class KitchenVictorIntroScreen(FloatLayout):

    def __init__(self, **kwargs):
        self.name    = kwargs.pop("name", "kitchen_victor_intro")
        self.manager = None
        super().__init__(**kwargs)

        self.level_num = 1

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

    # ── screen lifecycle ───────────────────────────────────────────────────────

    def on_enter(self):
        path = os.path.join(_ASSETS, "screens",
                            f"kitchen_intro_lvl{self.level_num}.png")
        try:
            self._rect.texture = self._load_tex(path)
        except Exception:
            self._rect.texture = None
        self._draw()

    def on_leave(self):
        pass

    def on_touch_down(self, touch):
        audio_manager.play_button_wood()
        game = self.manager.get_screen("kitchen_gameplay")
        game.level_num = self.level_num
        self.manager.current = "kitchen_gameplay"
        return True
