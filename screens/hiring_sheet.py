"""
screens/hiring_sheet.py – "Now Hiring!" first-time player registration.

Background image: assets/hiring_screen.png (3645×1773).
All keyboard buttons and the icon display are placed by converting
SOURCE IMAGE pixel coordinates → screen coordinates at runtime,
using the same _img_to_screen_box pattern as cafe_hub.py and menu.py.
This keeps every button pixel-perfect on any phone / tablet / aspect ratio.

To tweak a button position: open hiring_screen.png in an image editor,
read the pixel bounds, and update the corresponding entry in _KEY_ZONES.
"""

import os

from kivy.uix.floatlayout import FloatLayout
from kivy.core.audio import SoundLoader
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.graphics import Color, Rectangle
from kivy.core.image import Image as CoreImage
from kivy.animation import Animation
from kivy.properties import NumericProperty

from game_constants import COLOR_BG
from game_utils import save_player_profile, list_icon_keys, icon_path, fsp
import game_settings
import audio_manager

_ASSETS    = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets")
_KB_ASSETS = os.path.join(_ASSETS, "keyboard buttons")
_FONT      = os.path.join(_ASSETS, "fonts", "Pixelfont.ttf")

# ── Intro pan settings ────────────────────────────────────────────────────────
_PAN_IMAGE    = "screens/hiring_scroll.png"   # tall image to pan; skipped if missing
_PAN_DURATION = 20.0                  # seconds for top → bottom scroll

# ── Source image dimensions ────────────────────────────────────────────────────
_BG_W = 3645
_BG_H = 1773

# ── Overlay zones in source image pixels (left, top, right, bottom) ───────────
_ZONE_ICON       = ( 187,  635,  641, 1095)   # dark inner square of polaroid
_ZONE_NAME_TEXT  = ( 100, 1098,  740, 1185)   # name text area below polaroid photo
_ZONE_MAX_CHARS  = ( 100, 1185,  740, 1255)   # "(MAX 8 CHARACTERS)" hint
_ZONE_ARROW_L    = (  70, 1421,  399, 1640)   # left arrow  (270 px wide)
_ZONE_ARROW_R    = ( 559, 1421,  861, 1640)   # right arrow (270 px wide, shifted left)
_ZONE_BACK       = (  36,  218,  583,  413)   # back button – top-left corner of art

# Keyboard rows — left to right as drawn in the art.
# UNDO = wide key end of row 1; READY = wide key end of row 4.
_ROWS = [
    ["A", "B", "C", "D", "E", "F", "UNDO"],
    ["G", "H", "I", "J", "K", "L", "M", "N"],
    ["O", "P", "Q", "R", "S", "T", "U", "V"],
    ["W", "X", "Y", "Z", "SPACE", "READY"],
]
_MAX_LEN = 8

# Pixel-accurate bounding boxes measured from hiring_screen.png.
# Key width = 219 , key height = 209 (except SPACE and READY which are wider).
_KEY_ZONES = {
    # Row 1 
    "A":     (1194,  592, 1413,  801),
    "B":     (1436,  592, 1673,  801),
    "C":     (1691,  592, 1928,  801),
    "D":     (1941,  592, 2178,  801),
    "E":     (2191,  592, 2428,  801),
    "F":     (2441,  592, 2678,  801),
    "UNDO":  (2681,  592, 3143,  801),
    # Row 2  
    "G":     (1318,  819, 1537, 1023),
    "H":     (1571,  819, 1790, 1023),
    "I":     (1822,  819, 2041, 1023),
    "J":     (2072,  819, 2291, 1023),
    "K":     (2325,  819, 2544, 1023),
    "L":     (2575,  819, 2794, 1023),
    "M":     (2825,  819, 3044, 1023),
    "N":     (3072,  819, 3301, 1023),
    # Row 3  
    "O":     (1194, 1052, 1413, 1261),
    "P":     (1436, 1052, 1673, 1261),
    "Q":     (1691, 1052, 1928, 1261),
    "R":     (1941, 1052, 2178, 1261),
    "S":     (2191, 1052, 2428, 1261),
    "T":     (2441, 1052, 2678, 1261),
    "U":     (2694, 1052, 2933, 1261),
    "V":     (2946, 1052, 3183, 1261),
    # Row 4  
    "W":     (1318, 1275, 1537, 1484),
    "X":     (1571, 1275, 1790, 1484),
    "Y":     (1822, 1275, 2041, 1484),
    "Z":     (2072, 1275, 2291, 1484),
    "SPACE": (2315, 1275, 2777, 1484),
    "READY": (2778, 1275, 3240, 1484),
}

# Placeholder colours used when no icon PNGs are found
_PLACEHOLDER_COLOURS = [
    (0.85, 0.30, 0.30, 1),
    (0.30, 0.60, 0.85, 1),
    (0.30, 0.78, 0.46, 1),
    (0.85, 0.70, 0.20, 1),
    (0.68, 0.30, 0.85, 1),
    (0.85, 0.54, 0.22, 1),
]


# ── Intro scroll widget ────────────────────────────────────────────────────────

class _FitWidthBG(Widget):
    """Scales image to full screen width.
    If the image is shorter than the screen after that scale, it is letterboxed
    (centred with empty space above/below).  If it is taller it is cropped
    symmetrically top/bottom."""

    def __init__(self, source, **kwargs):
        super().__init__(**kwargs)
        self._texture = CoreImage(source).texture
        with self.canvas:
            Color(1, 1, 1, 1)
            self._rect = Rectangle(texture=self._texture)
        self.bind(pos=self._update, size=self._update)

    def _update(self, *_):
        tex_w, tex_h = self._texture.size
        w, h = self.size
        if w == 0 or h == 0 or tex_w == 0 or tex_h == 0:
            return
        scale  = w / tex_w
        img_h  = tex_h * scale
        if img_h >= h:
            # Image taller than screen – crop top/bottom symmetrically
            visible_v = h / img_h
            v_top     = (1.0 - visible_v) / 2
            v_bot     = v_top + visible_v
            self._rect.tex_coords = (0.0, v_bot, 1.0, v_bot, 1.0, v_top, 0.0, v_top)
            self._rect.pos  = self.pos
            self._rect.size = self.size
        else:
            # Image shorter than screen – centred vertically (bars top and bottom)
            ry = self.y + (h - img_h) / 2
            self._rect.tex_coords = (0.0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0)
            self._rect.pos  = (self.x, ry)
            self._rect.size = (w, img_h)


class _ScrollingBG(Widget):
    """Tall image that pans from top → bottom then disappears.
    Sits on top of everything and swallows all touches while visible."""

    scroll_offset = NumericProperty(0.0)   # 0 = image top, 1 = image bottom

    def __init__(self, source, **kwargs):
        super().__init__(**kwargs)
        self._texture = CoreImage(source).texture
        with self.canvas:
            Color(1, 1, 1, 1)
            self._rect = Rectangle(texture=self._texture)
        self.bind(pos=self._update, size=self._update,
                  scroll_offset=self._update)

    def _update(self, *_):
        tex_w, tex_h = self._texture.size
        w, h = self.size
        if w == 0 or h == 0 or tex_w == 0 or tex_h == 0:
            return
        u0, u1 = 0.0, 1.0
        displayed_h = tex_h * (w / tex_w)   # image height if scaled to screen width
        if displayed_h <= h:
            v_top, v_bot = 0.0, 1.0          # image fits entirely – show all
        else:
            visible_v = h / displayed_h       # fraction of image that fits on screen
            # v=0 → PNG top,  v=1 → PNG bottom  (matches CoverImage convention)
            v_top = self.scroll_offset * (1.0 - visible_v)
            v_bot = v_top + visible_v
        # tex_coords order: BL, BR, TR, TL
        self._rect.tex_coords = (u0, v_bot, u1, v_bot, u1, v_top, u0, v_top)
        self._rect.pos  = self.pos
        self._rect.size = self.size

    def on_touch_down(self, touch):
        return self.collide_point(*touch.pos)   # swallow all touches during pan


# ── Icon display widget ────────────────────────────────────────────────────────

class IconDisplay(Widget):
    """Draws the selected icon (or a coloured rectangle placeholder) inside the
    polaroid zone. No border — the art provides the frame."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._tex    = None
        self._colour = _PLACEHOLDER_COLOURS[0]
        with self.canvas:
            self._ci_color = Color(1, 1, 1, 1)
            self._ci_rect  = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._draw, size=self._draw)

    def set_icon(self, tex, colour):
        self._tex    = tex
        self._colour = colour
        self._draw()

    def _draw(self, *_):
        x, y, w, h = self.x, self.y, self.width, self.height
        if self._tex:
            self._ci_color.rgba   = (1, 1, 1, 1)
            self._ci_rect.texture = self._tex
        else:
            r, g, bv, a           = self._colour
            self._ci_color.rgba   = (r, g, bv, a)
            self._ci_rect.texture = None
        self._ci_rect.pos  = (x, y)
        self._ci_rect.size = (w, h)


# ── Keyboard key widget ────────────────────────────────────────────────────────

class _KeyButton(Widget):
    """Renders a button image with uniform scaling (no aspect-ratio distortion).
    The full widget bounds act as the touch target; the image is centred inside."""

    def __init__(self, label, img_normal, img_pressed, callback, **kwargs):
        super().__init__(**kwargs)
        self._label    = label
        self._callback = callback
        self._pressed  = False
        self._tex_n = None
        self._tex_d = None
        if os.path.isfile(img_normal):
            try:
                self._tex_n = CoreImage(img_normal).texture
            except Exception:
                pass
        if os.path.isfile(img_pressed):
            try:
                self._tex_d = CoreImage(img_pressed).texture
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
        # Uniform scale: largest factor that still fits inside the zone bounds
        scale = min(self.width / tw, self.height / th)
        dw    = tw * scale
        dh    = th * scale
        x     = self.x + (self.width  - dw) / 2
        y     = self.y + (self.height - dh) / 2
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
            was_inside = self.collide_point(*touch.pos)
            self._pressed = False
            self._redraw()
            if was_inside:
                self._callback()
            return True
        return super().on_touch_up(touch)


# ── Screen ─────────────────────────────────────────────────────────────────────

class HiringSheetScreen(FloatLayout):

    def __init__(self, **kwargs):
        self.name    = kwargs.pop("name", "hiring_sheet")
        self.manager = None
        super().__init__(**kwargs)
        self.player_name    = ""
        self._name_label    = None
        self._icon_display  = None
        self._icon_keys     = []
        self._icon_textures = []
        self._selected_idx  = 0
        self._max_chars_label = None
        self._key_widgets   = {}   # label → Button for all image-anchored keys
        self._left_btn      = None
        self._right_btn     = None
        self._back_btn      = None
        self._scroll_bg     = None   # intro pan overlay; None if image missing

        # ── Sound effects ─────────────────────────────────────────────────────
        _snd_dir = os.path.join(_ASSETS, "sounds")
        self._snd_typing  = SoundLoader.load(os.path.join(_snd_dir, "typewriter_typing.mp3"))
        self._snd_key     = SoundLoader.load(os.path.join(_snd_dir, "typewriter_key.mp3"))
        self._snd_bell    = SoundLoader.load(os.path.join(_snd_dir, "typewriter_bell.mp3"))
        self._snd_rustle  = SoundLoader.load(os.path.join(_snd_dir, "paper_rustling.mp3"))
        if self._snd_typing:
            self._snd_typing.loop = True

        self._build_ui()
        self.bind(size=self._reposition_overlays, pos=self._reposition_overlays)

    # ── Coordinate mapping (mirrors CoverImage maths) ─────────────────────────

    def _img_to_screen_box(self, zone):
        """Convert (left,top,right,bottom) in image pixels to
        (screen_x, screen_y, width, height) in Kivy coords.
        Matches _FitWidthBG: always fill-width, crop or letterbox vertically."""
        l, t, r, b = zone
        scr_w, scr_h = self.width, self.height
        if scr_w == 0 or scr_h == 0:
            return 0, 0, 1, 1
        scale    = scr_w / _BG_W
        scaled_h = scale * _BG_H
        sx = lambda ix: ix * scale
        if scaled_h >= scr_h:
            # Fill width; crop top/bottom symmetrically
            crop_y = (scaled_h - scr_h) / 2
            sy = lambda iy: scr_h - (iy * scale - crop_y)
        else:
            # Fill width; letterbox (image centred vertically)
            sy = lambda iy: (scr_h + scaled_h) / 2 - iy * scale
        x0, x1 = sx(l), sx(r)
        y_top, y_bot = sy(t), sy(b)
        return x0, y_bot, x1 - x0, y_top - y_bot

    def _reposition_overlays(self, *_):
        if self.width == 0 or self.height == 0:
            return

        x, y, w, h = self._img_to_screen_box(_ZONE_ICON)
        self._icon_display.pos  = (x, y)
        self._icon_display.size = (w, h)

        x, y, w, h = self._img_to_screen_box(_ZONE_NAME_TEXT)
        self._name_label.pos       = (x, y)
        self._name_label.size      = (w, h)
        self._name_label.text_size = (w, h)

        x, y, w, h = self._img_to_screen_box(_ZONE_MAX_CHARS)
        self._max_chars_label.pos       = (x, y)
        self._max_chars_label.size      = (w, h)
        self._max_chars_label.text_size = (w, h)

        x, y, w, h = self._img_to_screen_box(_ZONE_ARROW_L)
        self._left_btn.pos  = (x, y)
        self._left_btn.size = (w, h)

        x, y, w, h = self._img_to_screen_box(_ZONE_ARROW_R)
        self._right_btn.pos  = (x, y)
        self._right_btn.size = (w, h)

        x, y, w, h = self._img_to_screen_box(_ZONE_BACK)
        self._back_btn.pos  = (x, y)
        self._back_btn.size = (w, h)

        for label, btn in self._key_widgets.items():
            x, y, w, h = self._img_to_screen_box(_KEY_ZONES[label])
            btn.pos  = (x, y)
            btn.size = (w, h)

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        # Solid bar colour behind the image (shows as letterbox bars)
        with self.canvas.before:
            Color(*COLOR_BG)
            self._bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(size=lambda *_: setattr(self._bg_rect, "size", self.size),
                  pos=lambda *_: setattr(self._bg_rect, "pos",  self.pos))

        bg_path = os.path.join(_ASSETS, "screens", "hiring_screen.png")
        if os.path.isfile(bg_path):
            self.add_widget(_FitWidthBG(
                source=bg_path,
                size_hint=(1, 1),
                pos_hint={"x": 0, "y": 0},
            ))

        # ── Name display – anchored to polaroid image coords ──────────────────
        self._name_label = Label(
            text="",
            font_size=fsp(36),
            bold=True,
            color=(0, 0, 0, 1),
            font_name=_FONT,
            size_hint=(None, None),
            halign="center",
            valign="middle",
        )
        self.add_widget(self._name_label)

        self._max_chars_label = Label(
            text="(MAX 8 CHARACTERS)",
            font_size=fsp(16),
            font_name=_FONT,
            color=(0, 0, 0, 0.65),
            size_hint=(None, None),
            halign="center",
            valign="middle",
        )
        self.add_widget(self._max_chars_label)

        # ── Arrow buttons – image-based ───────────────────────────────────────
        self._left_btn = _KeyButton(
            label="left_arrow",
            img_normal=os.path.join(_ASSETS, "ui", "left_arrow.png"),
            img_pressed=os.path.join(_ASSETS, "ui", "left_arrow_clicked.png"),
            callback=lambda: self._cycle(-1),
            size_hint=(None, None),
        )
        self.add_widget(self._left_btn)

        self._right_btn = _KeyButton(
            label="right_arrow",
            img_normal=os.path.join(_ASSETS, "ui", "right_arrow.png"),
            img_pressed=os.path.join(_ASSETS, "ui", "right_arrow_clicked.png"),
            callback=lambda: self._cycle(+1),
            size_hint=(None, None),
        )
        self.add_widget(self._right_btn)

        # ── Keyboard keys – image-anchored ────────────────────────────────────
        for row in _ROWS:
            for label in row:
                img_n = os.path.join(_KB_ASSETS, f"{label}_button.png")
                img_d = os.path.join(_KB_ASSETS, f"{label}_button_pressed.png")
                if label == "READY":
                    cb = self._on_ready
                else:
                    cb = lambda l=label: self._on_key(l)
                btn = _KeyButton(
                    label=label,
                    img_normal=img_n,
                    img_pressed=img_d,
                    callback=cb,
                    size_hint=(None, None),
                )
                self._key_widgets[label] = btn
                self.add_widget(btn)

        # ── BACK button – top-left, uniform-scaled like character keys ───────
        bn = os.path.join(_KB_ASSETS, "BACK_button.png")
        bd = os.path.join(_KB_ASSETS, "BACK_button_pressed.png")
        self._back_btn = _KeyButton(
            label="BACK",
            img_normal=bn,
            img_pressed=bd,
            callback=self._on_back,
            size_hint=(None, None),
        )
        self.add_widget(self._back_btn)

        # ── Icon display – added last so it renders on top of everything ──────
        self._icon_display = IconDisplay(size_hint=(None, None))
        self.add_widget(self._icon_display)

        # ── Intro pan overlay – created here, added to tree in on_enter ───────
        scroll_path = os.path.join(_ASSETS, _PAN_IMAGE)
        if os.path.isfile(scroll_path):
            self._scroll_bg = _ScrollingBG(
                source=scroll_path,
                size_hint=(1, 1),
                pos_hint={"x": 0, "y": 0},
            )

    # ── Icon data ─────────────────────────────────────────────────────────────

    def _load_icons(self):
        self._icon_keys     = list_icon_keys()
        self._icon_textures = []
        if self._icon_keys:
            for k in self._icon_keys:
                p = icon_path(k)
                try:
                    self._icon_textures.append(CoreImage(p).texture)
                except Exception:
                    self._icon_textures.append(None)
        else:
            for i, c in enumerate(_PLACEHOLDER_COLOURS):
                self._icon_keys.append(f"placeholder_{i}")
                self._icon_textures.append(None)
        self._selected_idx = 0

    def _refresh_icon(self):
        if not self._icon_keys:
            return
        idx    = self._selected_idx
        tex    = self._icon_textures[idx]
        colour = _PLACEHOLDER_COLOURS[idx % len(_PLACEHOLDER_COLOURS)]
        self._icon_display.set_icon(tex, colour)

    # ── Callbacks ─────────────────────────────────────────────────────────────

    def _cycle(self, direction):
        if not self._icon_keys:
            return
        self._selected_idx = (self._selected_idx + direction) % len(self._icon_keys)
        self._refresh_icon()
        if self._snd_rustle and game_settings.get("sfx_enabled"):
            self._snd_rustle.volume = game_settings.get("sfx_volume")
            self._snd_rustle.play()

    def _on_key(self, label):
        if label == "SPACE":
            if len(self.player_name) < _MAX_LEN:
                self.player_name += " "
        elif label == "UNDO":
            self.player_name = self.player_name[:-1]
        else:
            if len(self.player_name) < _MAX_LEN:
                self.player_name += label
        self._name_label.text = self.player_name or "..."
        self._refresh_icon()
        if self._snd_key and game_settings.get("sfx_enabled"):
            self._snd_key.volume = game_settings.get("sfx_volume")
            self._snd_key.play()

    def _on_back(self, *_):
        audio_manager.play_button_wood()
        from game_utils import get_current_player
        dest = "cafe_hub" if get_current_player() else "menu"
        self.manager.current = dest

    def _on_ready(self, *_):
        name = self.player_name.strip()
        if not name:
            return
        if self._snd_bell and game_settings.get("sfx_enabled"):
            self._snd_bell.volume = game_settings.get("sfx_volume") * 0.5
            self._snd_bell.play()
        icon = self._icon_keys[self._selected_idx] if self._icon_keys else None
        save_player_profile(name, icon)
        self.manager.current = "cafe_hub"

    def _on_pan_complete(self, *_):
        """Called when the intro scroll finishes – remove the overlay."""
        if self._scroll_bg and self._scroll_bg.parent:
            self.remove_widget(self._scroll_bg)
        if self._snd_typing:
            self._snd_typing.stop()

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def on_enter(self):
        audio_manager.stop_cafe_ambiance()
        self.player_name = ""
        if self._name_label:
            self._name_label.text = "..."
        self._load_icons()
        self._reposition_overlays()
        self._refresh_icon()

        if self._scroll_bg is not None:
            # Reset and place the pan overlay on top of everything
            if self._scroll_bg.parent:
                self.remove_widget(self._scroll_bg)
            self._scroll_bg.scroll_offset = 0.0
            self.add_widget(self._scroll_bg)
            anim = Animation(scroll_offset=1.0,
                             duration=_PAN_DURATION, t="linear")
            anim.bind(on_complete=self._on_pan_complete)
            anim.start(self._scroll_bg)
            if self._snd_typing and game_settings.get("sfx_enabled"):
                self._snd_typing.volume = game_settings.get("sfx_volume")
                self._snd_typing.play()
