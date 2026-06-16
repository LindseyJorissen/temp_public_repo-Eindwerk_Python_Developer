"""
screens/kitchen_tutorial.py – Kitchen Duty per-level tutorial slideshow.

Displays kitchen_tutorial_lvl{N}_1.png … kitchen_tutorial_lvl{N}_M.png fullscreen.
Each tap advances to the next frame; tapping after the last frame goes to
kitchen_victor_intro for that level and marks the tutorial as done.

Set `screen.level_num` before navigating here.
"""

import os

import audio_manager
from kivy.uix.widget import Widget
from kivy.uix.label import Label
from kivy.graphics import Color, Rectangle
from kivy.core.image import Image as CoreImage

from game_constants import COLOR_BG
from game_utils import fsp

_ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets")
_FONT   = os.path.join(_ASSETS, "fonts", "Pixelfont.ttf")


def _load_frames_for_level(level_num):
    frames = []
    i = 1
    while True:
        path = os.path.join(_ASSETS, "tutorial", f"kitchen_tutorial_lvl{level_num}_{i}.png")
        if not os.path.isfile(path):
            break
        try:
            frames.append(CoreImage(path).texture)
        except Exception:
            break
        i += 1
    return frames


class KitchenTutorialScreen(Widget):

    def __init__(self, **kwargs):
        self.name      = kwargs.pop("name", "kitchen_tutorial")
        self.manager   = None
        super().__init__(**kwargs)

        self.level_num = 1
        self._frames   = []
        self._index    = 0

        with self.canvas:
            Color(*COLOR_BG)
            self._bg_rect    = Rectangle(pos=self.pos, size=self.size)
            Color(1, 1, 1, 1)
            self._frame_rect = Rectangle(pos=self.pos, size=self.size)

        self.bind(pos=self._update, size=self._update)

        # "TAP TO CONTINUE" label — sits at the very bottom of the screen
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

    # ── drawing ────────────────────────────────────────────────────────────────

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
        tex    = self._frames[self._index]
        tw, th = tex.size
        w, h   = self.size
        if tw == 0 or th == 0 or w == 0 or h == 0:
            return
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

    # ── lifecycle ──────────────────────────────────────────────────────────────

    def on_enter(self):
        self._frames = _load_frames_for_level(self.level_num)
        self._index  = 0
        self._draw_frame()
        self._reposition_lbl()

    # ── input ──────────────────────────────────────────────────────────────────

    def on_touch_down(self, touch):
        audio_manager.play_button_wood()
        if not self._frames or self._index >= len(self._frames) - 1:
            self._go_to_game()
        else:
            self._index += 1
            self._draw_frame()
        return True

    def _go_to_game(self):
        from game_utils import get_current_player, mark_kitchen_level_tutorial_done
        player = get_current_player()
        if player:
            mark_kitchen_level_tutorial_done(player["name"], self.level_num)
        if self.level_num == 1:
            # Level 1 has a tutorial instead of a separate intro — go straight to gameplay
            game = self.manager.get_screen("kitchen_gameplay")
            game.level_num = 1
            self.manager.current = "kitchen_gameplay"
        else:
            intro = self.manager.get_screen("kitchen_victor_intro")
            intro.level_num = self.level_num
            self.manager.current = "kitchen_victor_intro"
