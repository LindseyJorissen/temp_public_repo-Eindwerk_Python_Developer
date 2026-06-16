"""
screens/tutorial.py – How-to-play art slideshow before the game starts.

Displays tutorial_barduty_1.png … tutorial_barduty_N.png fullscreen.
Each tap/click advances to the next frame; tapping after the last frame
goes to gameplay.
"""

import os

import audio_manager
from kivy.uix.widget import Widget
from kivy.uix.label import Label
from kivy.graphics import Color, Rectangle
from kivy.core.image import Image as CoreImage

from game_constants import COLOR_BG
from game_utils import fsp

_ASSETS     = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets")
_FONT       = os.path.join(_ASSETS, "fonts", "Pixelfont.ttf")
_FRAME_BASE = "tutorial/tutorial_barduty_"
_CACHED_FRAMES: list = []   # loaded once, reused on every visit


def _load_frames():
    if _CACHED_FRAMES:
        return _CACHED_FRAMES
    i = 1
    while True:
        path = os.path.join(_ASSETS, f"{_FRAME_BASE}{i}.png")
        if not os.path.isfile(path):
            break
        try:
            _CACHED_FRAMES.append(CoreImage(path).texture)
        except Exception:
            break
        i += 1
    return _CACHED_FRAMES


class TutorialScreen(Widget):

    def __init__(self, **kwargs):
        self.name    = kwargs.pop("name", "tutorial")
        self.manager = None
        super().__init__(**kwargs)
        self.player_name = ""
        self._frames  = None   # loaded lazily on first on_enter
        self._index   = 0
        with self.canvas:
            Color(*COLOR_BG)
            self._bg_rect    = Rectangle(pos=self.pos, size=self.size)
            Color(1, 1, 1, 1)
            self._frame_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update, size=self._update)

        self._lbl = Label(
            text="TAP TO CONTINUE",
            font_name=_FONT,
            font_size=fsp(18),
            color=(1.0, 1.0, 1.0, 0.85),
            halign="center",
            valign="middle",
            size_hint=(None, None),
        )
        self.add_widget(self._lbl)
        self.bind(pos=self._reposition_lbl, size=self._reposition_lbl)

    # ── drawing ────────────────────────────────────────────────────

    def _reposition_lbl(self, *_):
        lbl_h = fsp(30)
        self._lbl.size      = (self.width, lbl_h)
        self._lbl.text_size = (self.width, lbl_h)
        self._lbl.pos       = (self.x, self.y + fsp(10))

    def _update(self, *_):
        self._bg_rect.pos  = self.pos
        self._bg_rect.size = self.size
        self._draw_frame()

    def _draw_frame(self):
        if not self._frames:
            return
        tex   = self._frames[self._index]
        tw, th = tex.size
        w, h   = self.size
        if tw == 0 or th == 0 or w == 0 or h == 0:
            return
        # Fill width, crop/letterbox vertically (same logic as other screens)
        scale    = w / tw
        scaled_h = th * scale
        if scaled_h >= h:
            crop_v = (scaled_h - h) / (2 * scaled_h)
            self._frame_rect.tex_coords = (
                0.0, 1.0 - crop_v, 1.0, 1.0 - crop_v,
                1.0, crop_v,       0.0, crop_v,
            )
            self._frame_rect.pos  = self.pos
            self._frame_rect.size = self.size
        else:
            ry = self.y + (h - scaled_h) / 2
            self._frame_rect.tex_coords = (0.0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0)
            self._frame_rect.pos  = (self.x, ry)
            self._frame_rect.size = (w, scaled_h)
        self._frame_rect.texture = tex

    # ── lifecycle ──────────────────────────────────────────────────

    def on_enter(self):
        if self._frames is None:
            self._frames = _load_frames()
        audio_manager.start_tutorial_music()
        self._index = 0
        self._draw_frame()

    # ── input ──────────────────────────────────────────────────────

    def on_touch_down(self, touch):
        if not self._frames or self._index >= len(self._frames) - 1:  # type: ignore[arg-type]
            self._go_to_game()
        else:
            self._index += 1
            self._draw_frame()
        return True

    def _go_to_game(self):
        audio_manager.stop_music()
        from game_utils import get_current_player, mark_tutorial_done
        player = get_current_player()
        if player:
            mark_tutorial_done(player["name"])
        # After tutorial always flow into Level 1 via Victor intro
        victor = self.manager.get_screen("victor_intro")
        victor.level_num = 1
        game = self.manager.get_screen("game")
        game.mode      = "level"
        game.level_num = 1
        if player:
            game.player_name = player["name"]
            game.player_icon = player.get("icon")
        self.manager.current = "victor_intro"
