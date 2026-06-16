"""
screens/kitchen_intro_cutscene.py – One-time cutscene shown after a new player
completes Bar Duty level 1 for the first time.

Flow:
  1. Pan: cutscene_to_kitchen.png scrolls left→right (non-skippable).
     Overlay 1 appears immediately on top.
     Tap → Overlay 2 → Tap → Overlay 3 → Tap → overlays gone.
  2. Pan finishes (waits if overlays still showing, starts anim once both done).
  3. Anim: cutscene_to_kitchen1-6.png plays once, stops on last frame.
  4. Tap → Cafe Hub.
"""

import os

from kivy.uix.floatlayout import FloatLayout
from kivy.uix.widget import Widget
from kivy.graphics import Color, Rectangle
from kivy.core.image import Image as CoreImage
from kivy.animation import Animation
from kivy.clock import Clock
from kivy.properties import NumericProperty

import audio_manager

_ASSETS       = os.path.join(os.path.dirname(__file__), "..", "assets")
_PAN_DURATION = 12.0   # seconds for full left → right pan
_FRAME_DUR    = 0.14   # seconds per animation frame


def _load_tex(path):
    """Load a texture with nearest-neighbor filtering so pixel art stays crisp."""
    tex = CoreImage(path).texture
    tex.mag_filter = "nearest"
    tex.min_filter = "nearest"
    return tex


# ── Horizontal pan widget ──────────────────────────────────────────────────────

class _HorizontalScrollBG(Widget):
    """Wide image scaled to screen height, panned left → right."""

    scroll_offset = NumericProperty(0.0)

    def __init__(self, source, **kwargs):
        super().__init__(**kwargs)
        self._texture = _load_tex(source)
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
        displayed_w = tex_w * (h / tex_h)
        if displayed_w <= w:
            u_left, u_right = 0.0, 1.0
        else:
            visible_u = w / displayed_w
            u_left    = self.scroll_offset * (1.0 - visible_u)
            u_right   = u_left + visible_u
        v_top, v_bot = 0.0, 1.0
        self._rect.tex_coords = (u_left, v_bot, u_right, v_bot,
                                  u_right, v_top, u_left,  v_top)
        self._rect.pos  = self.pos
        self._rect.size = self.size


# ── Frame animation widget ─────────────────────────────────────────────────────

class _FrameAnim(Widget):
    """Plays cutscene_to_kitchen1-6.png once, stops on last frame."""

    def __init__(self, textures, **kwargs):
        super().__init__(**kwargs)
        self._textures   = textures
        self._idx        = 0
        self._clock      = None
        self.on_complete = None   # callable fired when last frame is reached
        with self.canvas:
            Color(1, 1, 1, 1)
            self._rect = Rectangle()
        self.bind(pos=self._draw, size=self._draw)

    def _draw(self, *_):
        if not self._textures:
            return
        tex = self._textures[self._idx]
        tw, th = tex.size
        w, h = self.size
        if w == 0 or h == 0 or tw == 0 or th == 0:
            return
        scale    = w / tw
        scaled_h = th * scale
        self._rect.texture = tex
        if scaled_h >= h:
            crop_v = (scaled_h - h) / (2 * scaled_h)
            self._rect.tex_coords = (0, 1 - crop_v, 1, 1 - crop_v,
                                      1, crop_v,     0, crop_v)
            self._rect.pos  = self.pos
            self._rect.size = self.size
        else:
            ry = self.y + (h - scaled_h) / 2
            self._rect.tex_coords = (0, 1, 1, 1, 1, 0, 0, 0)
            self._rect.pos  = (self.x, ry)
            self._rect.size = (w, scaled_h)

    def start(self):
        self._idx = 0
        self._draw()
        if self._clock:
            self._clock.cancel()
        self._clock = Clock.schedule_interval(self._step, _FRAME_DUR)

    def stop(self):
        if self._clock:
            self._clock.cancel()
            self._clock = None

    def _step(self, *_):
        next_idx = self._idx + 1
        if next_idx >= len(self._textures):
            self.stop()
            if self.on_complete:
                self.on_complete()
            return
        self._idx = next_idx
        self._draw()


# ── Overlay widget ─────────────────────────────────────────────────────────────

class _OverlayWidget(Widget):
    """Shows one overlay PNG at a time fullscreen; hidden when idx == -1."""

    def __init__(self, textures, **kwargs):
        super().__init__(**kwargs)
        self._textures = textures
        self._idx      = -1
        with self.canvas:
            Color(1, 1, 1, 1)
            self._rect = Rectangle()
        self.bind(pos=self._draw, size=self._draw)

    def _draw(self, *_):
        if self._idx < 0 or not self._textures:
            self._rect.size = (0, 0)
            return
        tex = self._textures[self._idx]
        tw, th = tex.size
        w, h = self.size
        if w == 0 or h == 0 or tw == 0 or th == 0:
            return
        # Render at 62% of screen width, centred
        rw       = w * 0.62
        rh       = th * (rw / tw)
        rx       = self.x + (w - rw) / 2
        ry       = self.y + (h - rh) / 2
        self._rect.texture    = tex
        self._rect.tex_coords = (0, 1, 1, 1, 1, 0, 0, 0)
        self._rect.pos        = (rx, ry)
        self._rect.size       = (rw, rh)

    def show(self, idx):
        self._idx = idx
        self._draw()

    def hide(self):
        self._idx = -1
        self._draw()

    @property
    def visible(self):
        return self._idx >= 0


# ── Screen ─────────────────────────────────────────────────────────────────────

class KitchenIntroCutsceneScreen(FloatLayout):
    """Pan + overlay dialogue + frame-animation cutscene."""

    def __init__(self, **kwargs):
        self.name    = kwargs.pop("name", "kitchen_intro_cutscene")
        self.manager = None
        super().__init__(**kwargs)

        self._anim     = None
        self._phase    = "pan"   # "pan" | "anim"
        self._pan_done = False   # pan finished before overlays were tapped away

        # ── Phase 1: wide pan image ──────────────────────────────────────────
        pan_path = os.path.join(_ASSETS, "screens", "cutscene_to_kitchen.png")
        self._pan_bg = _HorizontalScrollBG(
            source=pan_path,
            size_hint=(1, 1),
            pos_hint={"x": 0, "y": 0},
        )
        self.add_widget(self._pan_bg)

        # ── Phase 2: 6-frame animation ───────────────────────────────────────
        frame_texes = []
        for i in range(1, 7):
            p = os.path.join(_ASSETS, "screens", f"cutscene_to_kitchen{i}.png")
            if os.path.isfile(p):
                try:
                    frame_texes.append(_load_tex(p))
                except Exception:
                    pass

        self._frame_anim = _FrameAnim(
            textures=frame_texes,
            size_hint=(1, 1),
            pos_hint={"x": 0, "y": 0},
            opacity=0,
        )
        self.add_widget(self._frame_anim)

        # ── Overlays (on top of pan, tapped away before animation) ───────────
        overlay_texes = []
        for i in range(1, 4):
            p = os.path.join(_ASSETS, "screens", f"cutscene_overlay{i}.png")
            if os.path.isfile(p):
                try:
                    overlay_texes.append(_load_tex(p))
                except Exception:
                    pass

        self._overlay = _OverlayWidget(
            textures=overlay_texes,
            size_hint=(1, 1),
            pos_hint={"x": 0, "y": 0},
        )
        self.add_widget(self._overlay)

        # ── Fade-to-black overlay (topmost) ──────────────────────────────────
        self._fade = Widget(
            size_hint=(1, 1),
            pos_hint={"x": 0, "y": 0},
            opacity=0,
        )
        with self._fade.canvas:
            Color(0, 0, 0, 1)
            self._fade_rect = Rectangle()
        self._fade.bind(pos=self._update_fade, size=self._update_fade)
        self.add_widget(self._fade)

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def _update_fade(self, *_):
        self._fade_rect.pos  = self._fade.pos
        self._fade_rect.size = self._fade.size

    def on_enter(self):
        audio_manager.stop_music()
        audio_manager.play_mittens_nogood()
        self._phase    = "pan"
        self._pan_done = False
        self._fade.opacity   = 0
        self._pan_bg.opacity     = 1
        self._frame_anim.opacity = 0
        self._frame_anim.stop()
        self._pan_bg.scroll_offset = 0.0
        # Show overlay 1 immediately as pan starts
        if self._overlay._textures:
            self._overlay.show(0)
        else:
            self._overlay.hide()
        self._anim = Animation(scroll_offset=1.0,
                               duration=_PAN_DURATION, t="linear")
        self._anim.bind(on_complete=self._on_pan_done)
        self._anim.start(self._pan_bg)

    def on_leave(self):
        audio_manager.stop_mittens_nogood()
        if self._anim:
            self._anim.cancel(self._pan_bg)
            self._anim = None
        self._frame_anim.stop()
        self._frame_anim.on_complete = None
        Animation.cancel_all(self._fade)
        self._overlay.hide()

    # ── Phase transitions ─────────────────────────────────────────────────────

    def _on_pan_done(self, *_):
        self._anim = None
        if not self._overlay.visible:
            # Overlays already all tapped – go straight to animation
            self._start_anim_phase()
        else:
            # Wait for the player to finish tapping overlays
            self._pan_done = True

    def _start_anim_phase(self):
        self._pan_bg.opacity     = 0
        self._frame_anim.opacity = 1
        self._phase = "anim"
        self._frame_anim.on_complete = self._on_anim_done
        self._frame_anim.start()

    def _on_anim_done(self):
        Clock.schedule_once(self._begin_fade, 1.0)

    def _begin_fade(self, *_):
        self._phase = "fading"
        fade_anim = Animation(opacity=1.0, duration=0.8, t="linear")
        fade_anim.bind(on_complete=lambda *_: self._go_to_hub())
        fade_anim.start(self._fade)

    # ── Input ─────────────────────────────────────────────────────────────────

    def on_touch_down(self, touch):
        if self._overlay.visible:
            # Advance through overlays 1 → 2 → 3 → gone
            next_idx = self._overlay._idx + 1
            if next_idx < len(self._overlay._textures):
                self._overlay.show(next_idx)
            else:
                self._overlay.hide()
                # If pan already finished while we were reading, start anim now
                if self._pan_done:
                    self._start_anim_phase()
        return True

    def _go_to_hub(self):
        hub = self.manager.get_screen("cafe_hub")
        hub._after_cutscene = True
        self.manager.current = "cafe_hub"
