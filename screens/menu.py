"""
screens/menu.py – Main menu screen.
"""

import os

from kivy.uix.floatlayout import FloatLayout
from kivy.uix.button import Button
from kivy.uix.widget import Widget
from kivy.uix.label import Label
from kivy.graphics import Color, Rectangle
from kivy.core.image import Image as CoreImage
from kivy.clock import Clock

from game_constants import COLOR_BG, DEBUG_HITBOXES
import audio_manager
from game_utils import fsp

_ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets")


class CoverImage(Widget):
    """Fills its bounds with an image while keeping aspect ratio.
    Crops left/right (or top/bottom) as needed – never squishes."""

    def __init__(self, source, **kwargs):
        super().__init__(**kwargs)
        self._texture = CoreImage(source).texture
        self._texture.mag_filter = 'nearest'
        self._texture.min_filter = 'nearest'
        with self.canvas:
            self._rect = Rectangle(texture=self._texture)
        self.bind(pos=self._update, size=self._update)

    def set_texture(self, texture):
        self._texture = texture
        self._rect.texture = texture
        self._update()

    def _update(self, *_):
        tex_w, tex_h = self._texture.size
        w, h = self.size
        if w == 0 or h == 0 or tex_w == 0 or tex_h == 0:
            return

        img_ratio    = tex_w / tex_h
        widget_ratio = w / h

        if img_ratio > widget_ratio:
            # Image is wider than the screen – scale to height, crop left/right
            scale    = h / tex_h
            scaled_w = tex_w * scale
            crop_u   = (scaled_w - w) / (2 * scaled_w)
            u0, u1   = crop_u, 1.0 - crop_u
            v0, v1   = 0.0, 1.0
        else:
            # Image is taller than the screen – scale to width, crop top/bottom
            scale    = w / tex_w
            scaled_h = tex_h * scale
            crop_v   = (scaled_h - h) / (2 * scaled_h)
            u0, u1   = 0.0, 1.0
            v0, v1   = crop_v, 1.0 - crop_v

        # tex_coords order: BL, BR, TR, TL  (v is flipped – PNG origin is top-left)
        self._rect.tex_coords = (u0, v1, u1, v1, u1, v0, u0, v0)
        self._rect.pos  = self.pos
        self._rect.size = self.size


class _FillWidthBg(Widget):
    """Fill-width background that supports animated texture swaps via set_texture.
    Crops top/bottom symmetrically when image is taller than screen; letterboxes
    (centres vertically) when image is shorter."""

    def __init__(self, source, **kwargs):
        super().__init__(**kwargs)
        try:
            self._texture = CoreImage(source).texture
            self._texture.mag_filter = 'nearest'
            self._texture.min_filter = 'nearest'
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
        tex_w, tex_h = self._texture.size
        w, h = self.size
        if w == 0 or h == 0 or tex_w == 0 or tex_h == 0:
            return
        scale    = w / tex_w
        scaled_h = tex_h * scale
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


_FRAME_INTERVAL = 0.45  # seconds between frames
_CLICK_HINT_FRAME_DUR = 0.45  # seconds per frame for the click hint sprite

# ── Source image dimensions & door zone ───────────────────────────────────────
_BG_W = 3645
_BG_H = 1773
# (left, top, right, bottom) in source image pixels.
# Open menu_screen_1.png in an image editor to verify / adjust.
_ZONE_DOOR      = (1120, 420, 1475, 1350)   # the cafe door
_ZONE_DOOR_HINT = (1247, 1020, 1407, 1265)   # click hint centred on door
_ZONE_TAP_LBL   = (1060, 1310, 1615, 1430)  # "TAP DOOR TO ENTER" label below hint
_FONT           = os.path.join(_ASSETS, "fonts", "Pixelfont.ttf")


class _ClickHint(Widget):
    """Loops between click1.png and click2.png as a tap hint."""
    def __init__(self, assets_dir, **kwargs):
        super().__init__(**kwargs)
        self._texes = []
        self._idx   = 0
        self._event = None
        for name in ("ui/click1.png", "ui/click2.png"):
            p = os.path.join(assets_dir, name)
            try:
                t = CoreImage(p).texture if os.path.isfile(p) else None
            except Exception:
                t = None
            if t:
                self._texes.append(t)
        with self.canvas:
            self._ci_color = Color(1, 1, 1, 0)
            self._ci_rect  = Rectangle()
        self.bind(pos=self._place, size=self._place)

    def _place(self, *_):
        self._ci_rect.pos  = self.pos
        self._ci_rect.size = self.size
        if self._texes:
            self._ci_rect.texture = self._texes[self._idx]

    def show(self):
        if not self._texes:
            return
        self._idx = 0
        self._ci_rect.texture = self._texes[0]
        self._ci_rect.pos     = self.pos
        self._ci_rect.size    = self.size
        self._ci_color.rgba   = (1, 1, 1, 1)
        if self._event:
            self._event.cancel()
        self._event = Clock.schedule_once(self._step, _CLICK_HINT_FRAME_DUR)

    def hide(self):
        if self._event:
            self._event.cancel()
            self._event = None
        self._ci_color.rgba = (1, 1, 1, 0)

    def _step(self, *_):
        if not self._texes:
            return
        self._idx = (self._idx + 1) % len(self._texes)
        self._ci_rect.texture = self._texes[self._idx]
        self._event = Clock.schedule_once(self._step, _CLICK_HINT_FRAME_DUR)


class MenuScreen(FloatLayout):
    def __init__(self, **kwargs):
        self.name    = kwargs.pop("name", "menu")
        self.manager = None
        super().__init__(**kwargs)
        self._play_btn    = None
        self._click_hint  = None
        self._tap_lbl     = None
        self._build_ui()
        self._anim_event = Clock.schedule_interval(self._next_frame, _FRAME_INTERVAL)
        self.bind(size=self._reposition_overlays, pos=self._reposition_overlays)

    # ── Coordinate mapping (same logic as CoverImage) ─────────────────────────

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

    def _reposition_overlays(self, *_):
        if self._play_btn is None or self.width == 0:
            return
        x, y, w, h = self._img_to_screen_box(_ZONE_DOOR)
        self._play_btn.pos  = (x, y)
        self._play_btn.size = (w, h)

        x, y, w, h = self._img_to_screen_box(_ZONE_DOOR_HINT)
        self._click_hint.pos  = (x, y)
        self._click_hint.size = (w, h)

        x, y, w, h = self._img_to_screen_box(_ZONE_TAP_LBL)
        self._tap_lbl.pos       = (x, y)
        self._tap_lbl.size      = (w, h)
        self._tap_lbl.text_size = (w, h)

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        with self.canvas.before:
            Color(*COLOR_BG)
            self._bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=lambda *_: setattr(self._bg_rect, 'pos',  self.pos),
                  size=lambda *_: setattr(self._bg_rect, 'size', self.size))

        def _load(name):
            tex = CoreImage(os.path.join(_ASSETS, name)).texture
            tex.mag_filter = 'nearest'
            tex.min_filter = 'nearest'
            return tex

        self._frame_textures = [_load(f"screens/menu_screen_{i}.png") for i in range(1, 4)]
        self._frame_index = 0

        self._cover = _FillWidthBg(
            source=os.path.join(_ASSETS, "screens", "menu_screen_1.png"),
            size_hint=(1, 1),
            pos_hint={"x": 0, "y": 0},
        )
        self.add_widget(self._cover)

        self._play_btn = Button(
            text="DOOR" if DEBUG_HITBOXES else "",
            size_hint=(None, None),
            background_normal="",
            background_color=(1.00, 0.85, 0.00, 0.35) if DEBUG_HITBOXES else (0, 0, 0, 0),
            color=(1, 1, 1, 1),
            font_size="12sp",
            bold=True,
        )
        self._play_btn.bind(on_release=self._on_play)
        self.add_widget(self._play_btn)

        self._click_hint = _ClickHint(_ASSETS, size_hint=(None, None))
        self.add_widget(self._click_hint)

        self._tap_lbl = Label(
            text="TAP DOOR TO ENTER",
            font_name=_FONT,
            font_size=fsp(16),
            color=(1.0, 1.0, 1.0, 0.85),
            halign="center",
            valign="middle",
            size_hint=(None, None),
        )
        self.add_widget(self._tap_lbl)

    def on_enter(self):
        audio_manager.start_menu_music()
        self._reposition_overlays()

    def on_leave(self):
        self._click_hint.hide()

    def _next_frame(self, *_):
        self._frame_index = (self._frame_index + 1) % len(self._frame_textures)
        self._cover.set_texture(self._frame_textures[self._frame_index])

    def _on_play(self, *_):
        audio_manager.play_open_door()
        from game_utils import get_current_player, migrate_scores_if_needed
        migrate_scores_if_needed()
        if get_current_player() is None:
            self.manager.current = "hiring_sheet"
        else:
            self.manager.current = "cafe_hub"

