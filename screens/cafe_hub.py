"""
screens/cafe_hub.py – Main hub after logging in.

Overlay widgets (player icon, name label, settings button) are positioned by
converting SOURCE IMAGE pixel coordinates → screen coordinates at runtime, so
they stay glued to the correct art pixels on every phone/resolution.

To move an overlay element, open cafe_hub.png in an image editor and read the
pixel coordinates, then update the _ZONE_* tuples below (left, top, right, bottom).

DEBUG_HITBOXES (in game_constants.py) – set True to see coloured overlays on
every invisible hit zone so you can verify placement without guessing.
"""

import os

from kivy.uix.floatlayout import FloatLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.graphics import Color, Rectangle, Ellipse
from kivy.core.image import Image as CoreImage
from kivy.clock import Clock

from game_constants import COLOR_BG, COLOR_GOLD, DEBUG_HITBOXES
from game_utils import get_current_player, icon_path_small, fsp, is_endless_unlocked, get_level_progress, get_cafe_equipped, ensure_defaults_owned
import audio_manager

# ── Debug colours ─────────────────────────────────────────────────────────────
_DBG_KITCHEN = (0.10, 0.80, 0.10, 0.35)

_ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets")
_FONT   = os.path.join(_ASSETS, "fonts", "Pixelfont.ttf")

_CLICK_HINT_FRAME_DUR  = 0.45   # seconds per frame for the click hint sprite
_BG_FRAME_DUR          = 0.45   # seconds per frame for the background animation
_FIRE_FRAME_DUR        = 0.40   # seconds per frame for the fireplace animation
_CAT_FRAME_DUR         = 0.40   # seconds per frame for the cafe cat animation
_COUPLE_FRAME_DUR      = 0.30   # seconds per frame for the cafe couple animation
_COUPLE_PAUSE_DUR      = 2.0    # hold on frame 0 before the couple cycle starts
_SCRATCH_FRAME_DUR     = 0.12   # seconds per frame for the cat scratching animation
_SCRATCH_PAUSE_DUR     = 1.0    # hold on frame 0 before the scratch cycle starts

# ── Victor-at-bar animation ────────────────────────────────────────────────────
# Open cafe_hub.png in an image editor and read pixel coordinates to tune these.
_VIC_BAR_ANCHOR_X = 1924    # image-pixel x: horizontal centre of the sprite
_VIC_BAR_FEET_Y   = 808   # image-pixel y (from top of image): where his feet sit
_VIC_BAR_HEIGHT   = 210    # sprite height in image pixels – increase to make bigger
_VIC_BAR_FRAME    = 0.20   # seconds per animation frame – decrease to speed up

# ── Source image dimensions ────────────────────────────────────────────────────
_BG_W = 3645
_BG_H = 1773

# Bounding boxes of UI zones in source image pixels (left, top, right, bottom).
# Open cafe_hub.png in an image editor to verify / adjust these.
_ZONE_ICON         = (525,   194,  632,  304)   # photo square
_ZONE_NAME         = (565,   173, 1105,  341)   # name tag strip
# Achievements button: user will add art to the LEFT of the highscores trophy.
# Update these coords once the new button is placed in cafe_hub.png.
_ZONE_SHOP         = (1355,  135, 1550,  325)   # shop button (left of achievements)
_ZONE_ACHIEVEMENTS = (1585,  135, 1775,  325)   # achievements button
_ZONE_HIGHSCORES   = (1808,  110, 2042,  350)   # trophy / highscores button
_ZONE_GEAR         = (2056,  110, 2290,  350)   # settings gear (+50 px padding)
_ZONE_CLICK_HINT   = (1726,  980, 1918, 1280)   # click hint sprite – centre of art, slightly below mid

# Debug colours per zone (RGBA, semi-transparent) – only shown when DEBUG_HITBOXES=True
_DBG = {
    "glass":        (0.00, 0.80, 1.00, 0.35),
    "shop":         (1.00, 0.80, 0.00, 0.35),
    "achievements": (0.20, 0.80, 0.20, 0.35),
    "highscores":   (0.70, 0.00, 1.00, 0.35),
    "settings":     (1.00, 0.30, 0.00, 0.35),
}


def _zone_btn(zone_name, on_release):
    """Return an invisible hit-zone Button (or a coloured debug one)."""
    col  = _DBG[zone_name] if DEBUG_HITBOXES else (0, 0, 0, 0)
    text = zone_name.upper() if DEBUG_HITBOXES else ""
    btn = Button(
        text=text,
        size_hint=(None, None),
        background_normal="",
        background_color=col,
        color=(1, 1, 1, 1),
        font_size=fsp(12),
        font_name=_FONT,
        bold=True,
    )
    btn.bind(on_release=on_release)
    return btn



_CAFE_HUB_DIR = os.path.join(_ASSETS, "cafe_hub")

# Texture cache so layer PNGs are decoded once and reused on every on_enter.
_TEX_CACHE: dict = {}

def _load_cached(path):
    if path not in _TEX_CACHE:
        try:
            _TEX_CACHE[path] = CoreImage(path).texture if os.path.isfile(path) else None
        except Exception:
            _TEX_CACHE[path] = None
    return _TEX_CACHE[path]

# ── Modular cafe background layers ────────────────────────────────────────────

class _CafeLayerBg(Widget):
    """Stacks full-screen PNGs:
    floor → kitchen overlay → walls → wall_overlay → rugs → tables → seats → couch → barstools
    → solid_standard → fireplace (animated) → cafe_cat (animated) → cafe_couple (animated) → decor → background_and_ui
    """

    _SLOTS = 16  # +1 for wall_overlay, +1 for fireplace, +1 for cafe_cat, +1 for cafe_couple, +1 for cat_scratching

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._texes         = []
        self._fire_texes    = []
        self._fire_idx      = 0
        self._fire_event    = None
        self._cat_texes     = []
        self._cat_idx       = 0
        self._cat_event     = None
        self._couple_texes   = []
        self._couple_idx     = 0
        self._couple_event   = None
        self._scratch_texes  = []
        self._scratch_idx    = 0
        self._scratch_event  = None
        self.bind(pos=self._draw, size=self._draw)

    def _load(self, filename):
        return _load_cached(os.path.join(_CAFE_HUB_DIR, filename))

    def refresh(self, player_name=None):
        equipped = get_cafe_equipped(player_name) if player_name else {}
        floor_key     = equipped.get("floor",           "floor_cherry_wood")
        kitchen_key   = equipped.get("kitchen_overlay")
        walls_key     = equipped.get("walls",           "walls_bricks")
        rugs_key      = equipped.get("rugs")
        tables_key    = equipped.get("tables")
        seats_key     = equipped.get("seats")
        couch_key     = equipped.get("couch")
        barstools_key     = equipped.get("barstools")
        wall_overlay_key  = equipped.get("wall_overlay")
        decor_key         = equipped.get("decor")

        from screens.shop import SHOP_CATALOGUE
        def find_asset(cat, key):
            for item in SHOP_CATALOGUE.get(cat, []):
                if item["key"] == key:
                    return item.get("asset")
            return None

        # Load fireplace frames and (re)start animation
        self._fire_texes = [t for name in ("fireplace1.png", "fireplace2.png")
                            if (t := self._load(name)) is not None]
        self._fire_idx = 0
        if self._fire_event:
            self._fire_event.cancel()
            self._fire_event = None
        if len(self._fire_texes) > 1:
            self._fire_event = Clock.schedule_interval(self._step_fire, _FIRE_FRAME_DUR)

        # Load cafe cat frames and (re)start animation
        self._cat_texes = [t for name in ("cafe_cat1.png", "cafe_cat2.png")
                           if (t := self._load(name)) is not None]
        self._cat_idx = 0
        if self._cat_event:
            self._cat_event.cancel()
            self._cat_event = None
        if len(self._cat_texes) > 1:
            self._cat_event = Clock.schedule_interval(self._step_cat, _CAT_FRAME_DUR)

        # Load cafe couple frames and (re)start animation
        self._couple_texes = [t for i in range(1, 10)
                              if (t := self._load(f"cafe_couple_drinking{i}.png")) is not None]
        self._couple_idx = 0
        if self._couple_event:
            self._couple_event.cancel()
            self._couple_event = None
        if len(self._couple_texes) > 1:
            self._couple_event = Clock.schedule_once(self._step_couple, _COUPLE_PAUSE_DUR)

        # Load cat scratching frames and (re)start animation
        self._scratch_texes = [t for i in range(1, 7)
                               if (t := self._load(f"cat_scratching{i}.png")) is not None]
        self._scratch_idx = 0
        if self._scratch_event:
            self._scratch_event.cancel()
            self._scratch_event = None
        if len(self._scratch_texes) > 1:
            self._scratch_event = Clock.schedule_once(self._step_scratch, _SCRATCH_PAUSE_DUR)

        self._texes = [
            self._load(find_asset("floors",  floor_key)          or "") if floor_key          else None,  # 0
            self._load(find_asset("floors",  kitchen_key)        or "") if kitchen_key        else None,  # 1
            self._load(find_asset("walls",   walls_key)          or "") if walls_key          else None,  # 2
            self._load(find_asset("walls",   wall_overlay_key)   or "") if wall_overlay_key   else None,  # 3 wall overlay
            self._load(find_asset("decor",   rugs_key)           or "") if rugs_key           else None,  # 4
            self._load(find_asset("tables",  tables_key)         or "") if tables_key         else None,  # 5
            self._load(find_asset("seats",   seats_key)          or "") if seats_key          else None,  # 6
            self._load(find_asset("seats",   couch_key)          or "") if couch_key          else None,  # 7
            self._load(find_asset("seats",   barstools_key)      or "") if barstools_key      else None,  # 8
            self._load("cafe_solid_standard.png"),                # 9  permanent furniture
            self._fire_texes[0]   if self._fire_texes   else None, # 10 fireplace frame 0
            self._cat_texes[0]    if self._cat_texes    else None, # 11 cafe cat frame 0
            self._couple_texes[0]  if self._couple_texes  else None, # 12 cafe couple frame 0
            self._scratch_texes[0] if self._scratch_texes else None, # 13 cat scratching frame 0
            self._load(find_asset("decor",   decor_key)          or "") if decor_key          else None,  # 14
            self._load("background_and_ui.png"),                # 15
        ]
        self._draw()

    def _step_fire(self, *_):
        if not self._fire_texes or len(self._texes) <= 10:
            return
        self._fire_idx = (self._fire_idx + 1) % len(self._fire_texes)
        self._texes[10] = self._fire_texes[self._fire_idx]
        self._draw()

    def _step_cat(self, *_):
        if not self._cat_texes or len(self._texes) <= 11:
            return
        self._cat_idx = (self._cat_idx + 1) % len(self._cat_texes)
        self._texes[11] = self._cat_texes[self._cat_idx]
        self._draw()

    def _step_couple(self, *_):
        if not self._couple_texes or len(self._texes) <= 12:
            return
        self._couple_idx = (self._couple_idx + 1) % len(self._couple_texes)
        self._texes[12] = self._couple_texes[self._couple_idx]
        self._draw()
        delay = _COUPLE_PAUSE_DUR if self._couple_idx == 0 else _COUPLE_FRAME_DUR
        self._couple_event = Clock.schedule_once(self._step_couple, delay)

    def _step_scratch(self, *_):
        if not self._scratch_texes or len(self._texes) <= 13:
            return
        self._scratch_idx = (self._scratch_idx + 1) % len(self._scratch_texes)
        self._texes[13] = self._scratch_texes[self._scratch_idx]
        self._draw()
        delay = _SCRATCH_PAUSE_DUR if self._scratch_idx == 0 else _SCRATCH_FRAME_DUR
        self._scratch_event = Clock.schedule_once(self._step_scratch, delay)

    def stop(self):
        if self._fire_event:
            self._fire_event.cancel()
            self._fire_event = None
        if self._cat_event:
            self._cat_event.cancel()
            self._cat_event = None
        if self._couple_event:
            self._couple_event.cancel()
            self._couple_event = None
        if self._scratch_event:
            self._scratch_event.cancel()
            self._scratch_event = None

    def _draw(self, *_):
        self.canvas.clear()
        w, h = self.size
        if w == 0 or h == 0:
            return
        with self.canvas:
            for tex in self._texes:
                if tex is None:
                    continue
                tw, th   = tex.size
                scale    = w / tw
                scaled_h = th * scale
                Color(1, 1, 1, 1)
                if scaled_h >= h:
                    crop_v = (scaled_h - h) / (2 * scaled_h)
                    r = Rectangle(texture=tex, pos=self.pos, size=self.size)
                    r.tex_coords = (0.0, 1.0 - crop_v, 1.0, 1.0 - crop_v,
                                    1.0, crop_v,        0.0, crop_v)
                else:
                    ry = self.y + (h - scaled_h) / 2
                    r = Rectangle(texture=tex, pos=(self.x, ry), size=(w, scaled_h))
                    r.tex_coords = (0.0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0)


# ── Static background ─────────────────────────────────────────────────────────

class _AnimatedHintBg(Widget):
    """Animated background.

    First entry: cycles cafe_hub_first_entry1-4.png
    Regular:     cycles cafe_hub1-4.png
    Falls back to static cafe_hub.png if frames are missing.
    """

    def __init__(self, assets_dir, **kwargs):
        super().__init__(**kwargs)
        self._idx   = 0
        self._event = None

        self._regular_texes        = self._load_frames(assets_dir, "cafe_hub{}.png")
        self._first_entry_texes    = self._load_frames(assets_dir, "cafe_hub_first_entry{}.png")
        self._after_cutscene_texes = self._load_frames(assets_dir, "cafe_hub_after_cutscene{}.png")

        # Fallback to static cafe_hub.png if regular frames are missing
        if not self._regular_texes:
            p = os.path.join(assets_dir, "screens", "cafe_hub.png")
            try:
                t = CoreImage(p).texture if os.path.isfile(p) else None
            except Exception:
                t = None
            if t:
                self._regular_texes = [t]

        self._texes = self._regular_texes

        with self.canvas:
            Color(1, 1, 1, 1)
            self._rect = Rectangle()
        self.bind(pos=self._draw, size=self._draw)

    def _load_frames(self, assets_dir, pattern):
        texes = []
        for i in range(1, 5):
            p = os.path.join(assets_dir, "screens", pattern.format(i))
            try:
                t = CoreImage(p).texture if os.path.isfile(p) else None
            except Exception:
                t = None
            if t:
                texes.append(t)
        return texes

    def _draw(self, *_):
        if not self._texes:
            return
        tex = self._texes[self._idx]
        tw, th = tex.size
        w, h = self.size
        if w == 0 or h == 0 or tw == 0 or th == 0:
            return
        scale    = w / tw
        scaled_h = th * scale
        self._rect.texture = tex
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

    def _step(self, *_):
        if not self._texes:
            return
        self._idx = (self._idx + 1) % len(self._texes)
        self._draw()

    def set_first_entry(self, first_entry):
        if first_entry and self._first_entry_texes:
            self._texes = self._first_entry_texes
        else:
            self._texes = self._regular_texes
        self._idx = 0

    def set_after_cutscene(self):
        """Switch to after-cutscene frames (falls back to first-entry frames)."""
        if self._after_cutscene_texes:
            self._texes = self._after_cutscene_texes
        elif self._first_entry_texes:
            self._texes = self._first_entry_texes
        else:
            self._texes = self._regular_texes
        self._idx = 0

    def start(self):
        if not self._texes:
            self._rect.size = (0, 0)   # hide any stale first-entry / after-cutscene frame
            return
        self._idx = 0
        self._draw()
        if self._event:
            self._event.cancel()
        self._event = Clock.schedule_interval(self._step, _BG_FRAME_DUR)

    def stop(self):
        if self._event:
            self._event.cancel()
            self._event = None


# ── Click hint overlay ────────────────────────────────────────────────────────

class _ClickHint(Widget):
    """Loops between click1.png and click2.png as a first-entry tap hint.
    Call show() to start animating, hide() to stop and make invisible."""

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


# ── Victor-at-bar animation ───────────────────────────────────────────────────

class _VictorAtBar(Widget):
    """Loops victor_at_bar1-4.png at a fixed position on the bar counter.

    Tune the position and size with the _VIC_BAR_* constants at the top of
    this file – no need to touch this class.
    """

    def __init__(self, assets_dir, **kwargs):
        super().__init__(**kwargs)
        self._texes = []
        self._idx   = 0
        self._event = None

        for i in range(1, 5):
            p = os.path.join(assets_dir, "characters", f"victor_at_bar{i}.png")
            try:
                t = CoreImage(p).texture if os.path.isfile(p) else None
            except Exception:
                t = None
            if t:
                self._texes.append(t)

        with self.canvas:
            self._color = Color(1, 1, 1, 0)
            self._rect  = Rectangle()
        self.bind(pos=self._place, size=self._place)

    def _screen_rect(self):
        """Return (x, y, w, h) in screen pixels using the same fill-width
        letterbox maths as the background image."""
        W, H = self.width, self.height
        if W < 2 or not self._texes:
            return 0, 0, 0, 0

        scale    = W / _BG_W
        scaled_h = scale * _BG_H

        if scaled_h >= H:
            crop_y = (scaled_h - H) / 2
            def sy(iy): return H - (iy * scale - crop_y)
        else:
            def sy(iy): return (H + scaled_h) / 2 - iy * scale

        # height in screen pixels, width preserves sprite aspect ratio
        vh = _VIC_BAR_HEIGHT * scale
        tw, th = self._texes[0].size
        vw = vh * (tw / th) if th > 0 else vh

        vx = self.x + _VIC_BAR_ANCHOR_X * scale - vw / 2
        vy = sy(_VIC_BAR_FEET_Y)   # Kivy y = bottom of sprite

        return vx, vy, vw, vh

    def _place(self, *_):
        if not self._texes:
            return
        x, y, w, h = self._screen_rect()
        self._rect.texture = self._texes[self._idx % len(self._texes)]
        self._rect.pos     = (x, y)
        self._rect.size    = (w, h)

    def start(self):
        if not self._texes:
            return
        self._color.a = 1
        self._place()
        if self._event:
            self._event.cancel()
        self._event = Clock.schedule_interval(self._step, _VIC_BAR_FRAME)

    def stop(self):
        if self._event:
            self._event.cancel()
            self._event = None
        self._color.a = 0

    def _step(self, *_):
        if not self._texes:
            return
        self._idx = (self._idx + 1) % len(self._texes)
        self._rect.texture = self._texes[self._idx]


# ── Small icon widget ──────────────────────────────────────────────────────────

class _IconWidget(Widget):
    def __init__(self, key, **kwargs):
        super().__init__(**kwargs)
        self._tex = None
        self._load(key)
        self.bind(pos=self._draw, size=self._draw)

    def _load(self, key):
        p = icon_path_small(key) if key else None
        if p:
            try:
                self._tex = CoreImage(p).texture
            except Exception:
                self._tex = None
        else:
            self._tex = None

    def _draw(self, *_):
        self.canvas.clear()
        x, y, w, h = self.x, self.y, self.width, self.height
        with self.canvas:
            if self._tex:
                Color(1, 1, 1, 1)
                Rectangle(texture=self._tex, pos=(x, y), size=(w, h))
            else:
                Color(*COLOR_GOLD)
                Ellipse(pos=(x + 4, y + 4), size=(w - 8, h - 8))


# ── Screen ─────────────────────────────────────────────────────────────────────

class CafeHubScreen(FloatLayout):

    def __init__(self, **kwargs):
        self.name    = kwargs.pop("name", "cafe_hub")
        self.manager = None
        super().__init__(**kwargs)
        self._player_label     = None
        self._icon_widget      = None
        self._settings_btn     = None
        self._achievements_btn = None
        self._highscores_btn   = None
        self._shop_btn         = None
        self._bg_anim          = None
        self._victor_at_bar    = None
        self._click_hint       = None
        self._kitchen_btn      = None
        self._next_screen      = None
        self._after_cutscene   = False   # set True by cutscene before navigating here
        self._build_ui()
        self.bind(size=self._reposition_overlays, pos=self._reposition_overlays)

    # ── Coordinate mapping ────────────────────────────────────────────────────

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
        self._icon_widget.pos  = (x, y)
        self._icon_widget.size = (w, h)

        x, y, w, h = self._img_to_screen_box(_ZONE_NAME)
        self._player_label.pos  = (x, y)
        self._player_label.size = (w, h)

        x, y, w, h = self._img_to_screen_box(_ZONE_SHOP)
        self._shop_btn.pos  = (x, y)
        self._shop_btn.size = (w, h)

        x, y, w, h = self._img_to_screen_box(_ZONE_ACHIEVEMENTS)
        self._achievements_btn.pos  = (x, y)
        self._achievements_btn.size = (w, h)

        x, y, w, h = self._img_to_screen_box(_ZONE_HIGHSCORES)
        self._highscores_btn.pos  = (x, y)
        self._highscores_btn.size = (w, h)

        x, y, w, h = self._img_to_screen_box(_ZONE_GEAR)
        self._settings_btn.pos  = (x, y)
        self._settings_btn.size = (w, h)

        x, y, w, h = self._img_to_screen_box(_ZONE_CLICK_HINT)
        self._click_hint.pos  = (x, y)
        self._click_hint.size = (w, h)

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        # Solid bar colour behind the image (shows as letterbox bars)
        with self.canvas.before:
            Color(*COLOR_BG)
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(size=lambda *_: setattr(self._bg, "size", self.size),
                  pos=lambda *_: setattr(self._bg, "pos",  self.pos))

        self._cafe_layers = _CafeLayerBg(
            size_hint=(1, 1),
            pos_hint={"x": 0, "y": 0},
        )
        self.add_widget(self._cafe_layers)

        self._bg_anim = _AnimatedHintBg(
            assets_dir=_ASSETS,
            size_hint=(1, 1),
            pos_hint={"x": 0, "y": 0},
        )
        # Regular frames handled by the layer system; keep anim only for cutscenes
        self._bg_anim._regular_texes = []
        self._bg_anim._texes = []
        self._bg_anim._rect.size = (0, 0)   # hide default 100×100 white rect
        self.add_widget(self._bg_anim)

        # Victor at bar – above background, below all UI buttons/overlays
        self._victor_at_bar = _VictorAtBar(
            assets_dir=_ASSETS,
            size_hint=(1, 1),
            pos_hint={"x": 0, "y": 0},
        )
        self.add_widget(self._victor_at_bar)

        # ── Game mode hit zones (pos_hint – tune to your art) ─────────────────
        glass_col  = _DBG["glass"]        if DEBUG_HITBOXES else (0, 0, 0, 0)
        glass_text = "GLASS DROP"         if DEBUG_HITBOXES else ""
        glass_btn = Button(
            text=glass_text,
            size_hint=(0.33, 0.40),
            pos_hint={"center_x": 0.52, "center_y": 0.57},
            background_normal="",
            background_color=glass_col,
            color=(1, 1, 1, 1),
            font_size=fsp(12),
            font_name=_FONT,
            bold=True,
        )
        glass_btn.bind(on_release=self._on_bar_duty)
        self.add_widget(glass_btn)

        # Kitchen Duty hit zone – top-right kitchen room (checkered floor area)
        kitchen_col  = _DBG_KITCHEN if DEBUG_HITBOXES else (0, 0, 0, 0)
        kitchen_text = "KITCHEN" if DEBUG_HITBOXES else ""
        self._kitchen_btn = Button(
            text=kitchen_text,
            size_hint=(0.30, 0.35),
            pos_hint={"center_x": 0.815, "center_y": 0.65},
            background_normal="",
            background_color=kitchen_col,
            color=(1, 1, 1, 1),
            font_size=fsp(12),
            font_name=_FONT,
            bold=True,
        )
        self._kitchen_btn.bind(on_release=self._on_kitchen_duty)
        self.add_widget(self._kitchen_btn)

        # ── Overlays anchored to image pixels ─────────────────────────────────
        self._icon_widget = _IconWidget(key=None, size_hint=(None, None))
        self.add_widget(self._icon_widget)

        self._player_label = Label(
            text="",
            font_size=fsp(26),
            bold=True,
            color=(0.15, 0.08, 0.02, 1),
            font_name=_FONT,
            size_hint=(None, None),
            halign="left",
            valign="middle",
        )
        self.add_widget(self._player_label)

        self._shop_btn = _zone_btn("shop", self._on_shop)
        self.add_widget(self._shop_btn)

        self._achievements_btn = _zone_btn("achievements", self._on_achievements)
        self.add_widget(self._achievements_btn)

        self._highscores_btn = _zone_btn("highscores", self._on_highscores)
        self.add_widget(self._highscores_btn)

        self._settings_btn = _zone_btn("settings", self._on_settings)
        self.add_widget(self._settings_btn)

        # Click hint – added last so it renders on top
        self._click_hint = _ClickHint(assets_dir=_ASSETS, size_hint=(None, None))
        self.add_widget(self._click_hint)

    # ── Navigation ─────────────────────────────────────────────────────────────

    def _on_bar_duty(self, *_):
        player = get_current_player()
        if not player:
            self._next_screen = "menu"
            self.manager.current = "menu"
            return
        if not player.get("tutorial_done", False):
            # First time: show tutorial, which auto-flows into Level 1
            tutorial = self.manager.get_screen("tutorial")
            tutorial.player_name = player["name"]
            self._next_screen = "tutorial"
            self.manager.current = "tutorial"
        else:
            self._next_screen = "bar_duty_hub"
            self.manager.current = "bar_duty_hub"

    def _on_kitchen_duty(self, *_):
        player = get_current_player()
        if not player:
            self.manager.current = "menu"
            return
        prog = get_level_progress(player["name"])
        if not prog.get(3, {}).get("completed", False):
            return  # locked until bar duty level 3 is completed
        self._next_screen = "kitchen_duty_hub"
        self.manager.current = "kitchen_duty_hub"

    def _on_shop(self, *_):
        self._next_screen = "shop"
        self.manager.current = "shop"

    def _on_achievements(self, *_):
        self._next_screen = "achievements"
        self.manager.current = "achievements"

    def _on_highscores(self, *_):
        lb = self.manager.get_screen("leaderboard")
        lb.current_player   = None
        lb.current_score    = None
        lb.current_opponent = None
        self._next_screen = "leaderboard"
        self.manager.current = "leaderboard"

    def _on_settings(self, *_):
        self._next_screen = "settings"
        self.manager.current = "settings"

    # ── Lifecycle ──────────────────────────────────────────────────────────────

    def on_enter(self):
        audio_manager.start_menu_music()
        self._reposition_overlays()
        player = get_current_player()
        if player:
            ensure_defaults_owned(player["name"])
        self._cafe_layers.refresh(player["name"] if player else None)
        if player:
            self._player_label.text = player["name"].upper()
            key = player.get("icon")
            self._icon_widget._load(key)
            self._icon_widget._draw()
            self._highscores_btn.disabled = not is_endless_unlocked(player["name"])
            first_entry = not player.get("tutorial_done", False)
        else:
            self._player_label.text = ""
            self._highscores_btn.disabled = True
            first_entry = False
        if player:
            prog = get_level_progress(player["name"])
            kitchen_unlocked = prog.get(3, {}).get("completed", False)
        else:
            kitchen_unlocked = False
        self._kitchen_btn.disabled = not kitchen_unlocked

        after_cutscene = self._after_cutscene
        self._after_cutscene = False   # consume flag

        if after_cutscene:
            # Return from kitchen intro cutscene: play after-cutscene art, no overlays
            self._bg_anim.set_after_cutscene()
            self._icon_widget.opacity  = 0
            self._player_label.opacity = 0
            self._bg_anim.start()
            self._click_hint.hide()
        elif first_entry:
            # Very first cafe visit: play first-entry art (pointer baked into art)
            self._bg_anim.set_first_entry(True)
            self._icon_widget.opacity  = 0
            self._player_label.opacity = 0
            self._bg_anim.start()
            self._click_hint.hide()
        else:
            # Regular visit
            self._bg_anim.set_first_entry(False)
            self._icon_widget.opacity  = 1
            self._player_label.opacity = 1
            self._bg_anim.start()
            audio_manager.start_fire_crackling()
            self._click_hint.hide()
            self._victor_at_bar.start()

    def on_leave(self):
        self._click_hint.hide()
        self._victor_at_bar.stop()
        self._bg_anim.stop()
        self._cafe_layers.stop()
        audio_manager.stop_fire_crackling()
        if self._next_screen not in ("settings", "leaderboard", "achievements", "shop", "bar_duty_hub", "kitchen_duty_hub"):
            audio_manager.stop_music()
        self._next_screen = None
