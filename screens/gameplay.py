"""
screens/gameplay.py – Core game loop and rendering for the Kivy port.

Coordinate system note
──────────────────────
Pygame  → Y=0 at TOP,    increases DOWNWARD
Kivy    → Y=0 at BOTTOM, increases UPWARD

So everything that "falls" has a DECREASING y in Kivy.
The cat lives near the TOP  → high y
The tray lives near BOTTOM  → low y

Canvas pattern
──────────────
We use self.canvas.clear() + with self.canvas: each frame.
Do NOT use InstructionGroup with PushMatrix/PopMatrix – it
causes RenderContext pop_state IndexError when cleared mid-cycle.
Wobble offset is applied manually to each x coordinate.
"""

import math
import os
import random

from kivy.uix.floatlayout import FloatLayout
from kivy.uix.widget import Widget
from kivy.uix.label import Label
from kivy.graphics import (
    Color, Rectangle, Ellipse, Line,
    RoundedRectangle,
)
from kivy.clock import Clock
from kivy.core.image import Image as CoreImage
from kivy.core.audio import SoundLoader

from game_constants import *   # includes OPPONENTS
from game_utils import update_player_score, update_player_stats, is_achievement_unlocked, unlock_achievement, is_endless_unlocked, fsp
from achievements import ACHIEVEMENTS
import game_settings
import audio_manager
from level_config import LEVELS

try:
    from plyer import accelerometer as _accelerometer
    _ACCEL_AVAILABLE = True
except Exception:
    _accelerometer   = None
    _ACCEL_AVAILABLE = False

_TILT_MAX  = 4.5   # m/s²  — full tilt = full tray travel
_TILT_DEAD = 0.4   # m/s²  — dead zone at centre

_FONT = os.path.join(os.path.dirname(__file__), "..", "assets", "fonts", "Pixelfont.ttf")


def _bar_zone_rect(zone, screen_w, screen_h):
    """Convert a BAR_HUD_ZONE_* tuple (left, top, right, bottom in source px)
    to (x, y, width, height) in Kivy screen coordinates.
    Uses the same fill-width letterbox logic as the bar art rendering."""
    l, t, r, b = zone
    if screen_w < 2:
        return 0, 0, 1, 1
    scale    = screen_w / KITCHEN_BG_W   # bar art is same 3915×1773 as kitchen
    scaled_h = scale * KITCHEN_BG_H
    if scaled_h >= screen_h:
        crop_y = (scaled_h - screen_h) / 2
        def sy(iy): return screen_h - (iy * scale - crop_y)
    else:
        def sy(iy): return (screen_h + scaled_h) / 2 - iy * scale
    return l * scale, sy(b), (r - l) * scale, sy(t) - sy(b)


# ══════════════════════════════════════════════════════════════════
# GameWidget – draws and updates all game entities
# ══════════════════════════════════════════════════════════════════

class GameWidget(Widget):
    """Handles all game logic and renders everything via canvas."""

    def __init__(self, player_name, on_game_over, on_achievement=None, opponent="mittens",
                 player_icon=None, mode="endless", level_cfg=None,
                 on_level_complete=None, on_level_fail=None, **kwargs):
        super().__init__(**kwargs)
        self.player_name      = player_name
        self._on_game_over    = on_game_over
        self._on_achievement  = on_achievement
        self._on_level_complete = on_level_complete
        self._on_level_fail   = on_level_fail
        self._mode            = mode       # "endless" | "level"
        self._player_icon     = player_icon

        # ── Difficulty multipliers (level config overrides opponent table) ─
        if mode == "level" and level_cfg is not None:
            self._opponent       = level_cfg.get("primary_cat", "mittens")
            self._cat_speed_base = CAT_SPEED_BASE * level_cfg["cat_speed_mult"]
            self._cat_speed_max  = CAT_SPEED_MAX  * level_cfg["cat_speed_mult"]
            self._cup_speed_mult = level_cfg["cup_speed_mult"]
            self._drop_mult      = level_cfg["drop_mult"]
            self._mouse_mult     = level_cfg["mouse_mult"]
        else:
            op = OPPONENTS.get(opponent, OPPONENTS["mittens"])
            self._opponent       = opponent
            self._cat_speed_base = CAT_SPEED_BASE * op['cat_speed_mult']
            self._cat_speed_max  = CAT_SPEED_MAX  * op['cat_speed_mult']
            self._cup_speed_mult = op['cup_speed_mult']
            self._drop_mult      = op['drop_mult']
            self._mouse_mult     = op['mouse_mult']

        # ── Level-mode settings ────────────────────────────────
        if mode == "level" and level_cfg is not None:
            self._mice_enabled      = level_cfg.get("mice_enabled", True)
            self._disco_threshold   = level_cfg.get("disco_threshold")   # None = never
            self._drunk_threshold   = level_cfg.get("drunk_threshold")   # None = never
            self._reverse_threshold = level_cfg.get("reverse_threshold") # None = never
            self._shift_timer       = float(level_cfg.get("duration_secs", 0))
            self._secondary_cat     = level_cfg.get("secondary_cat")     # cat key or None
        else:
            self._mice_enabled      = True
            self._disco_threshold   = SCORE_DISCO
            self._drunk_threshold   = SCORE_DRUNK
            self._reverse_threshold = SCORE_REVERSE
            self._shift_timer       = None   # no timer in endless mode
            self._secondary_cat     = None
        self._alarm_played = False

        # ── Game state ─────────────────────────────────────────
        self.score          = 0
        self.lives          = LIVES_START
        self.game_over      = False
        self.paused         = False
        self._show_game_over = False   # True only when lives hit 0 (not on level success)

        # ── Per-game achievement tracking ──────────────────────
        self._cups_caught_this_game  = 0
        self._cup_streak             = 0   # consecutive catches without a miss
        self._mouse_hits_this_game   = 0
        self._triggered_achievements = set()  # avoid double-firing this game

        # ── Cat state ──────────────────────────────────────────
        self.cat_x     = 0.0
        self.cat_y     = 0.0
        self.cat_dir   = 1            # 1 = right, -1 = left
        self.cat_speed = self._cat_speed_base
        self.cat_anim  = 0.0          # accumulates seconds
        self._cat_dart_acc  = 0.0
        self._cat_dart_next = random.uniform(2.0, 5.0)  # first random dash

        # ── Secondary cat state (level mode only) ──────────────
        self._cat2_x        = 0.0
        self._cat2_y        = 0.0
        self._cat2_dir      = -1      # starts moving left
        self._cat2_anim     = 0.0
        self._cat2_speed    = self._cat_speed_base * 0.65
        self._cat2_drop_acc  = 0.0
        self._cat2_drop_next = random.uniform(
            DROP_MIN * self._drop_mult * 1.8,
            DROP_MAX_BASE * self._drop_mult * 1.8,
        )
        self._cat2_dart_acc  = 0.0
        self._cat2_dart_next = random.uniform(2.0, 5.0)

        # ── Tray state ─────────────────────────────────────────
        self.tray_x      = -1.0          # -1 = uninitialised
        self.tray_y      = 0.0
        self._touch_x    = None          # current finger X
        self._accel_ay   = 0.0           # low-pass filtered accelerometer Y

        # ── Game objects ──────────────────────────────────────
        self.cups = []   # {cx, cy, speed, angle, state, timer}
        self.mice = []   # {x, y, speed}

        # ── Spawn timers ──────────────────────────────────────
        self._drop_acc   = 0.0
        self._drop_next  = 3.0   # extra breathing room before the first glass drops
        self._mouse_acc  = 0.0
        self._mouse_next = random.uniform(MOUSE_MIN * self._mouse_mult, MOUSE_MAX_BASE * self._mouse_mult)

        # ── Visual effects ────────────────────────────────────
        self.disco_mode    = (mode == "level" and self._disco_threshold is not None)
        self._disco_toggle = False
        self._disco_acc    = 0.0
        self._go_alpha     = 0.0      # game-over overlay alpha

        # ── Background texture ────────────────────────────────
        _assets  = os.path.join(os.path.dirname(__file__), "..", "assets")
        _bg_path = os.path.join(_assets, "screens", "bar_duty.png")
        try:
            self._bg_texture = CoreImage(_bg_path).texture
        except Exception:
            self._bg_texture = None

        # ── Disco overlay textures ────────────────────────────
        try:
            self._disco1_texture = CoreImage(os.path.join(_assets, "disco", "disco_overlay1.png")).texture
        except Exception:
            self._disco1_texture = None
        try:
            self._disco2_texture = CoreImage(os.path.join(_assets, "disco", "disco_overlay2.png")).texture
        except Exception:
            self._disco2_texture = None
        try:
            self._disco_flyer_texture = CoreImage(os.path.join(_assets, "disco", "disco_mode_flyer.png")).texture
        except Exception:
            self._disco_flyer_texture = None

        # ── Bar overlay (drawn over cats to put them behind the counter) ──
        try:
            self._bar_overlay_texture = CoreImage(os.path.join(_assets, "ui", "bar_overlay.png")).texture
        except Exception:
            self._bar_overlay_texture = None

        # ── Beer sprite textures ──────────────────────────────
        try:
            self._beer_texture = CoreImage(os.path.join(_assets, "ui", "beer.png")).texture
        except Exception:
            self._beer_texture = None
        try:
            self._beer_broken_texture = CoreImage(os.path.join(_assets, "ui", "beer_broken.png")).texture
        except Exception:
            self._beer_broken_texture = None

        # ── Tray textures (light for all icons except icon2 = dark) ─
        _tray_file = "tray_dark.png" if player_icon == "icon2" else "tray_light.png"
        try:
            self._tray_texture = CoreImage(os.path.join(_assets, "food", _tray_file)).texture
        except Exception:
            self._tray_texture = None

        # ── Bar prop texture ──────────────────────────────────────
        try:
            self._beer_prop_texture = CoreImage(os.path.join(_assets, "ui", "beer_prop.png")).texture
        except Exception:
            self._beer_prop_texture = None

        # ── Mouse sprite texture ──────────────────────────────────
        try:
            self._mouse_texture = CoreImage(os.path.join(_assets, "ui", "mouse.png")).texture
        except Exception:
            self._mouse_texture = None

        # ── Lives HUD textures (0–3 lives) ────────────────────────
        self._lives_textures = []
        for n in range(4):
            try:
                self._lives_textures.append(
                    CoreImage(os.path.join(_assets, "ui", f"{n}_lives.png")).texture
                )
            except Exception:
                self._lives_textures.append(None)

        # ── Cat sprite textures (mittens running animation) ───────
        self._mittens_textures = []
        for i in range(1, 6):
            try:
                self._mittens_textures.append(
                    CoreImage(os.path.join(_assets, "characters", f"mittens_running{i}.png")).texture
                )
            except Exception:
                pass

        # ── Cat sprite textures (hector running animation) ───────
        self._hector_textures = []
        for i in range(1, 14):
            try:
                self._hector_textures.append(
                    CoreImage(os.path.join(_assets, "characters", f"hector_running{i}.png")).texture
                )
            except Exception:
                pass

        # ── Cat sprite textures (oscar running animation) ────────
        self._oscar_textures = []
        for i in range(1, 14):
            try:
                self._oscar_textures.append(
                    CoreImage(os.path.join(_assets, "characters", f"oscar_running{i}.png")).texture
                )
            except Exception:
                pass

        # ── Cat sprite textures (chili running animation) ────────
        self._chili_textures = []
        for i in range(1, 6):
            try:
                self._chili_textures.append(
                    CoreImage(os.path.join(_assets, "characters", f"chili_running{i}.png")).texture
                )
            except Exception:
                pass

        # ── Sound effects ─────────────────────────────────────────
        _snd_dir = os.path.join(_assets, "sounds")
        self._snd_catch   = [
            SoundLoader.load(os.path.join(_snd_dir, "metal_knock.mp3")),
            SoundLoader.load(os.path.join(_snd_dir, "metal_knock2.mp3")),
        ]
        self._snd_shatter = SoundLoader.load(os.path.join(_snd_dir, "glass_shatter.mp3"))
        self._snd_mouse   = SoundLoader.load(os.path.join(_snd_dir, "mouse_squeek.mp3"))

        # ── Art bounds (the region the background image occupies) ─
        # When the screen is wider than the art's aspect ratio, brown
        # letterbox bars appear at top & bottom.  All game elements
        # should stay inside [_art_y, _art_y + _art_h].
        self._art_y = 0.0
        self._art_h = 0.0

        self.bind(size=self._on_resize, pos=self._on_resize)
        Clock.schedule_interval(self._update, 1.0 / 60.0)

        if _ACCEL_AVAILABLE:
            try:
                _accelerometer.enable()
            except Exception:
                pass

    # ─────────────────────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────────────────────

    def _compute_art_bounds(self, W, H):
        """Return (art_y, art_h): the vertical region the background image occupies.
        Mirrors the letterbox logic in _draw() so game elements stay inside the art."""
        if self._bg_texture and W > 0:
            tex_w, tex_h = self._bg_texture.size
            scaled_h = (W / tex_w) * tex_h
            if scaled_h >= H:
                return self.y, H
            else:
                return self.y + (H - scaled_h) / 2.0, scaled_h
        return self.y, H

    def _scale(self):
        # Scale relative to art height so sprites fit inside the art area,
        # not the full screen (which may include brown letterbox bars).
        art_h = self._art_h if self._art_h > 1 else self.height
        return (art_h / REF_SCALE_HEIGHT) if art_h > 1 else 1.0

    def _sizes(self):
        s = self._scale()
        return dict(
            s=s,
            cat_w=CAT_W_REF * s,
            cat_h=CAT_H_REF * s,
            tray_w=TRAY_W_REF * s,
            tray_h=TRAY_H_REF * s,
            tray_hb_w=TRAY_HB_W_REF * s,
            tray_hb_h=TRAY_HB_H_REF * s,
            beer_w=BEER_W_REF * s,
            beer_h=BEER_H_REF * s,
            mouse_w=MOUSE_W_REF * s,
            mouse_h=MOUSE_H_REF * s,
        )

    def _fire_achievement(self, key):
        """Fire an achievement callback once per game session."""
        if key in self._triggered_achievements:
            return
        self._triggered_achievements.add(key)
        if self._on_achievement:
            self._on_achievement(key)

    def _on_resize(self, *_):
        if self.width < 2 or self.height < 2:
            return
        W, H = self.width, self.height
        # Compute art bounds BEFORE _sizes() so _scale() uses the correct height.
        self._art_y, self._art_h = self._compute_art_bounds(W, H)
        z = self._sizes()
        self.cat_x = W * CAT_LEFT_MARGIN_F
        self.cat_y = self._art_y + self._art_h * (1.0 - CAT_Y_FROM_TOP_F) - z['cat_h']
        if self.tray_x < 0:
            self.tray_x = W / 2.0 - z['tray_w'] / 2.0
        self.tray_y = self._art_y + self._art_h * TRAY_Y_FROM_BOTTOM_F

        # Secondary cat starts from the right edge
        if self._secondary_cat:
            self._cat2_x = W * (1.0 - CAT_RIGHT_MARGIN_F) - z['cat_w']
            self._cat2_y = self._art_y + self._art_h * (1.0 - CAT_Y_FROM_TOP_F) - z['cat_h']

    # ─────────────────────────────────────────────────────────────
    # Touch input
    # ─────────────────────────────────────────────────────────────

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self._touch_x = touch.x
            return True

    def on_touch_move(self, touch):
        if self.collide_point(*touch.pos):
            self._touch_x = touch.x
            return True

    def on_touch_up(self, touch):
        self._touch_x = None
        return False

    # ─────────────────────────────────────────────────────────────
    # Main update
    # ─────────────────────────────────────────────────────────────

    def _update(self, dt):
        if self.game_over or self.paused or self.width < 2:
            return

        W, H = self.width, self.height
        z    = self._sizes()
        s    = z['s']

        # ── Shift timer (level mode only) ─────────────────────
        if self._shift_timer is not None:
            self._shift_timer = max(0.0, self._shift_timer - dt)
            if not self._alarm_played and 0 < self._shift_timer <= 4.0:
                self._alarm_played = True
                audio_manager.play_tiktok_alarm()
            if self._shift_timer <= 0 and not self.game_over:
                self.game_over = True
                if self._on_level_complete:
                    Clock.schedule_once(lambda _: self._on_level_complete(self.score), 1.0)
                return

        # ── Cat animation ─────────────────────────────────────
        self.cat_anim += dt

        # ── Cat movement ──────────────────────────────────────
        self.cat_x += self.cat_speed * s * self.cat_dir * dt

        l_bound = W * CAT_LEFT_MARGIN_F
        r_bound = W * (1.0 - CAT_RIGHT_MARGIN_F) - z['cat_w']
        if self.cat_x <= l_bound:
            self.cat_x = l_bound
            self.cat_dir = 1
        elif self.cat_x >= r_bound:
            self.cat_x = r_bound
            self.cat_dir = -1

        # Random dart: pick a new target anywhere on the track
        self._cat_dart_acc += dt
        if self._cat_dart_acc >= self._cat_dart_next:
            self._cat_dart_acc  = 0.0
            self._cat_dart_next = random.uniform(1.5, 4.0)
            target_x = random.uniform(l_bound, r_bound)
            self.cat_dir = 1 if target_x > self.cat_x else -1

        # ── Secondary cat movement ────────────────────────────
        if self._secondary_cat:
            self._cat2_anim += dt
            self._cat2_x += self._cat2_speed * s * self._cat2_dir * dt
            if self._cat2_x <= l_bound:
                self._cat2_x = l_bound
                self._cat2_dir = 1
            elif self._cat2_x >= r_bound:
                self._cat2_x = r_bound
                self._cat2_dir = -1

            self._cat2_dart_acc += dt
            if self._cat2_dart_acc >= self._cat2_dart_next:
                self._cat2_dart_acc  = 0.0
                self._cat2_dart_next = random.uniform(1.5, 4.0)
                target_x = random.uniform(l_bound, r_bound)
                self._cat2_dir = 1 if target_x > self._cat2_x else -1

        # ── Tray movement (finger or gyro tilt) ───────────────
        l_edge = W * TRAY_EDGE_MARGIN_F
        r_edge = W * (1.0 - TRAY_EDGE_MARGIN_F) - z['tray_w']
        reverse_active = (self._reverse_threshold is not None
                          and self.score >= self._reverse_threshold)

        if self._touch_x is not None:
            # Touch takes priority
            if reverse_active:
                target_x = (W - self._touch_x) - z['tray_w'] / 2.0
            else:
                target_x = self._touch_x - z['tray_w'] / 2.0
            self.tray_x = max(l_edge, min(r_edge, target_x))

        elif (_ACCEL_AVAILABLE and game_settings.get("gyro_enabled")
              and _accelerometer is not None):
            try:
                ax, ay, az = _accelerometer.acceleration[:3]
                if ay is not None:
                    # Stronger low-pass filter — keeps sensor stable
                    self._accel_ay = 0.12 * ay + 0.88 * self._accel_ay
                    smooth = self._accel_ay
                    # In landscape mode the long axis (ay) is horizontal.
                    # Tilt left → ay negative, tilt right → ay positive.
                    sign = 1 if smooth > 0 else -1
                    clamped = min(abs(smooth), _TILT_MAX)
                    if clamped < _TILT_DEAD:
                        frac = 0.0
                    else:
                        frac = (clamped - _TILT_DEAD) / (_TILT_MAX - _TILT_DEAD)
                    frac *= sign
                    if reverse_active:
                        frac = -frac
                    # Lerp tray toward target — prevents choppy snapping
                    target_x = l_edge + (frac + 1.0) / 2.0 * (r_edge - l_edge)
                    target_x = max(l_edge, min(r_edge, target_x))
                    self.tray_x += 0.25 * (target_x - self.tray_x)
            except Exception:
                pass

        self.tray_y = self._art_y + self._art_h * TRAY_Y_FROM_BOTTOM_F

        # ── Tray hitbox (sized by TRAY_HB_W_REF / TRAY_HB_H_REF) ─
        # Centred on the sprite horizontally; sits at the top of the sprite.
        hb_w   = z['tray_hb_w']
        hb_h   = z['tray_hb_h']
        hb_x   = self.tray_x + (z['tray_w'] - hb_w) / 2.0
        hb_top = self.tray_y + z['tray_h']
        hb_bot = hb_top - hb_h

        # ── Cup spawning ──────────────────────────────────────
        self._drop_acc += dt
        if self._drop_acc >= self._drop_next:
            self._drop_acc = 0.0
            drop_min = DROP_MIN * self._drop_mult
            max_iv = max(drop_min, (DROP_MAX_BASE - self.score * DROP_SCORE_DEC) * self._drop_mult)
            self._drop_next = random.uniform(drop_min, max_iv)

            bonus = min(self.score * BEER_SPEED_BONUS, BEER_SPEED_BONUS_MAX)
            spd   = random.uniform(
                BEER_SPEED_BASE + bonus,
                BEER_SPEED_BASE + BEER_SPEED_RAND + bonus / 2.0
            ) * s * self._cup_speed_mult

            self.cups.append({
                'cx':     self.cat_x + z['cat_w'] / 2.0,
                'cy':     self.cat_y,
                'speed':  spd,
                'angle':  random.uniform(-BEER_ANGLE_MAX, BEER_ANGLE_MAX),
                'state':  'falling',
                'timer':  0.0,
                'flip_h': random.choice((True, False)),
                'cat':    1,
            })

        # ── Secondary cat cup spawning ────────────────────────
        if self._secondary_cat:
            self._cat2_drop_acc += dt
            if self._cat2_drop_acc >= self._cat2_drop_next:
                self._cat2_drop_acc = 0.0
                drop_min = DROP_MIN * self._drop_mult * 1.8
                max_iv   = max(drop_min,
                               (DROP_MAX_BASE - self.score * DROP_SCORE_DEC) * self._drop_mult * 1.8)
                self._cat2_drop_next = random.uniform(drop_min, max_iv)

                bonus = min(self.score * BEER_SPEED_BONUS, BEER_SPEED_BONUS_MAX)
                spd   = random.uniform(
                    BEER_SPEED_BASE + bonus,
                    BEER_SPEED_BASE + BEER_SPEED_RAND + bonus / 2.0
                ) * s * self._cup_speed_mult
                self.cups.append({
                    'cx':     self._cat2_x + z['cat_w'] / 2.0,
                    'cy':     self._cat2_y,
                    'speed':  spd,
                    'angle':  random.uniform(-BEER_ANGLE_MAX, BEER_ANGLE_MAX),
                    'state':  'falling',
                    'timer':  0.0,
                    'flip_h': random.choice((True, False)),
                    'cat':    2,
                })

        # ── Mouse spawning ────────────────────────────────────
        if self._mice_enabled:
            self._mouse_acc += dt
        if self._mice_enabled and self._mouse_acc >= self._mouse_next:
            self._mouse_acc = 0.0
            mouse_min = MOUSE_MIN * self._mouse_mult
            max_iv = max(MOUSE_MAX_FLOOR * self._mouse_mult, (MOUSE_MAX_BASE - self.score * MOUSE_SCORE_DEC) * self._mouse_mult)
            self._mouse_next = random.uniform(mouse_min, max_iv)

            cat_cx = self.cat_x + z['cat_w'] / 2.0
            side   = random.choice((-1, 1))
            mx     = cat_cx + side * 200 * s
            mx     = max(W * 0.05, min(W * 0.95 - z['mouse_w'], mx))
            my     = self.cat_y - z['mouse_h']

            self.mice.append({
                'x':     mx,
                'y':     my,
                'speed': random.uniform(MOUSE_SPEED_MIN, MOUSE_SPEED_MAX) * s,
            })

        # ── Update cups ───────────────────────────────────────
        bw, bh = z['beer_w'], z['beer_h']
        for cup in self.cups[:]:
            if cup['state'] == 'falling':
                cup['speed'] += BEER_GRAVITY * s * dt
                cup['cy'] -= cup['speed'] * dt

                # Drift cx toward the cat that dropped this cup
                cat_id = cup.get('cat', 0)
                if cat_id == 1:
                    target_cx = self.cat_x + z['cat_w'] / 2.0
                    cup['cx'] += (target_cx - cup['cx']) * 2.5 * dt
                elif cat_id == 2 and self._secondary_cat:
                    target_cx = self._cat2_x + z['cat_w'] / 2.0
                    cup['cx'] += (target_cx - cup['cx']) * 2.5 * dt

                c_left  = cup['cx'] - bw / 2.0
                c_right = cup['cx'] + bw / 2.0
                c_bot   = cup['cy'] - bh / 2.0
                c_top   = cup['cy'] + bh / 2.0

                # Caught by tray
                if (c_right > hb_x and c_left < hb_x + hb_w and
                        c_top > hb_bot and c_bot < hb_top):
                    self.score += SCORE_CUP
                    self.cups.remove(cup)
                    if self._snd_catch and game_settings.get("sfx_enabled"):
                        snd = random.choice(self._snd_catch)
                        if snd:
                            snd.volume = game_settings.get("sfx_volume")
                            snd.play()

                    # ── Per-game catch tracking ────────────────
                    self._cups_caught_this_game += 1
                    self._cup_streak            += 1

                    if self._cups_caught_this_game >= 10:
                        self._fire_achievement("first_round")
                    if self._cups_caught_this_game >= 100 and self._mode == "endless":
                        self._fire_achievement("shaky_hands")
                    if self._cup_streak >= 20:
                        self._fire_achievement("no_spills")

                    if (self._disco_threshold is not None
                            and self.score >= self._disco_threshold):
                        self.disco_mode = True
                        audio_manager.start_disco_music()
                        if self._mode == "endless":
                            self._fire_achievement("disco_fever")
                    if (self._drunk_threshold is not None
                            and self.score >= self._drunk_threshold):
                        self._fire_achievement("drunk_on_the_job")

                    self.cat_speed = min(
                        self._cat_speed_base + (self.score // 10),
                        self._cat_speed_max,
                    )
                    continue

                # Hit the floor: break when the bottom edge reaches the tray level.
                # Broken sprite rests with its bottom at the tray top.
                if c_bot < self.tray_y:
                    self.lives -= 1
                    self._cup_streak = 0   # reset catch streak on miss
                    cup['state'] = 'broken'
                    cup['timer'] = BEER_BROKEN_SECS
                    cup['cy']    = self.tray_y + (BEER_BROKEN_SPRITE_H_REF * 0.5 + BEER_BROKEN_Y_OFFSET_REF) * s
                    cup['speed'] = 0.0
                    if self._snd_shatter and game_settings.get("sfx_enabled"):
                        self._snd_shatter.volume = game_settings.get("sfx_volume")
                        self._snd_shatter.play()

            elif cup['state'] == 'broken':
                cup['timer'] -= dt
                if cup['timer'] <= 0:
                    self.cups.remove(cup)

        # ── Update mice ───────────────────────────────────────
        mw, mh = z['mouse_w'], z['mouse_h']
        for m in self.mice[:]:
            m['x'] += random.choice((-1, 0, 1)) * MOUSE_WIGGLE * s * dt
            m['y'] -= m['speed'] * dt

            m_right = m['x'] + mw
            m_top   = m['y'] + mh

            if (m_right > hb_x and m['x'] < hb_x + hb_w and
                    m_top > hb_bot and m['y'] < hb_top):
                if self._snd_mouse and game_settings.get("sfx_enabled"):
                    self._snd_mouse.volume = game_settings.get("sfx_volume")
                    self._snd_mouse.play()
                self.score = max(0, self.score - SCORE_MOUSE_PENALTY)
                self.lives -= 1
                self._mouse_hits_this_game += 1
                self._cup_streak = 0   # mouse hit also breaks catch streak
                if self._mouse_hits_this_game >= 3:
                    self._fire_achievement("catastrophic")
                self.mice.remove(m)
                continue

            if m['y'] < self._art_y:
                self.mice.remove(m)

        # ── Disco toggle ──────────────────────────────────────
        if self.disco_mode:
            self._disco_acc += dt
            if self._disco_acc >= 0.2:
                self._disco_acc    = 0.0
                self._disco_toggle = not self._disco_toggle

        # ── Game over ─────────────────────────────────────────
        if self.lives <= 0 and not self.game_over:
            self.game_over       = True
            self._show_game_over = True
            update_player_score(self.player_name, self._opponent, self.score)
            # Pest control: survived the whole game without a single mouse hit
            if self._mouse_hits_this_game == 0:
                self._fire_achievement("pest_control")
            if self._mode == "level" and self._on_level_fail:
                Clock.schedule_once(lambda _: self._on_level_fail(self.score), 2.5)
            else:
                Clock.schedule_once(lambda _: self._on_game_over(self.score), 2.5)

        # ── Redraw ────────────────────────────────────────────
        self._draw(z, W, H)

    # ─────────────────────────────────────────────────────────────
    # Drawing  (canvas.clear + with self.canvas each frame)
    # NOTE: No PushMatrix/PopMatrix here – they cause pop_state
    # IndexError when used inside a cleared group.
    # Wobble is applied as a plain x offset passed to sub-draws.
    # ─────────────────────────────────────────────────────────────

    def _draw(self, z, W, H):
        s = z['s']

        # Drunk wobble: offset every x coordinate by this amount
        wx = 0.0
        drunk_active = (self._drunk_threshold is not None
                        and self.score >= self._drunk_threshold)
        if drunk_active and not self.game_over:
            wx = math.sin(self.cat_anim * 3.5) * 9.0 * s

        self.canvas.clear()
        with self.canvas:

            # ── Background ────────────────────────────────────
            # Bar colour always fills the screen first
            Color(*COLOR_BG)
            Rectangle(pos=(self.x, self.y), size=(W, H))

            if self._bg_texture:
                tex = self._bg_texture

                tex_w, tex_h = tex.size
                # Drunk wobble: shift UV horizontally so the image itself slides.
                # du is the fraction of texture width that wx pixels represent.
                du = (wx / W) if W > 0 else 0.0
                scaled_h = (W / tex_w) * tex_h
                if scaled_h >= H:
                    # Fill width; crop top/bottom symmetrically
                    crop_v = (scaled_h - H) / (2 * scaled_h)
                    img_pos  = (self.x, self.y)
                    img_size = (W, H)
                    tc = (du,       1.0 - crop_v,
                          1.0 + du, 1.0 - crop_v,
                          1.0 + du, crop_v,
                          du,       crop_v)
                else:
                    # Fill width; letterbox (centred vertically)
                    ry = self.y + (H - scaled_h) / 2
                    img_pos  = (self.x, ry)
                    img_size = (W, scaled_h)
                    tc = (du, 1.0, 1.0 + du, 1.0, 1.0 + du, 0.0, du, 0.0)
                Color(1, 1, 1, 1)
                Rectangle(texture=tex, pos=img_pos, size=img_size, tex_coords=tc)
            else:
                # Fallback: solid colour (override the bar colour drawn above)
                Color(*COLOR_BG)
                Rectangle(pos=(self.x, self.y), size=(W, H))

            # ── Cat ───────────────────────────────────────────
            self._draw_cat(z, s, wx)

            # ── Secondary cat (level mode, drawn at 75% scale) ─
            if self._secondary_cat:
                self._draw_secondary_cat(z, s, wx)

            # ── Bar overlay (drawn over cats so they appear behind the counter) ─
            self._draw_bar_overlay(W, H)

            # ── Disco flyer prop (only in disco mode) ─────────
            if self.disco_mode:
                self._draw_disco_flyer(s, wx)

            # ── Tray (under cups so beer lands on it) ─────────
            self._draw_tray(z, wx)

            # ── Cups ──────────────────────────────────────────
            for cup in self.cups:
                self._draw_cup(cup, z, s, wx)

            # ── Mice ──────────────────────────────────────────
            for m in self.mice:
                self._draw_mouse(m, z, s, wx)

            # ── Disco overlay (over cats & bar, under HUD) ────
            if self.disco_mode and self._bg_texture:
                overlay_tex = self._disco1_texture if self._disco_toggle else self._disco2_texture
                if overlay_tex:
                    Color(1, 1, 1, 1)
                    Rectangle(texture=overlay_tex, pos=img_pos, size=img_size, tex_coords=tc)

            # ── Lives HUD sprite ──────────────────────────────
            lives_idx = max(0, min(3, self.lives))
            lives_tex = self._lives_textures[lives_idx] if self._lives_textures else None
            if lives_tex:
                lx, ly, lw, lh = _bar_zone_rect(BAR_HUD_ZONE_LIVES, W, H)
                Color(1, 1, 1, 1)
                Rectangle(
                    texture=lives_tex,
                    pos=(lx, ly),
                    size=(lw, lh),
                    tex_coords=(0, 1, 1, 1, 1, 0, 0, 0),  # V-flip
                )

            # ── Game-over fade ────────────────────────────────────
            if self.game_over:
                self._go_alpha = min(1.0, self._go_alpha + 0.025)
                Color(0, 0, 0, self._go_alpha * 0.82)
                Rectangle(pos=(self.x, self.y), size=(W, H))

    # ── Cat ───────────────────────────────────────────────────────

    def _draw_cat(self, z, s, wx):
        cw, ch = z['cat_w'], z['cat_h']
        cx = self.cat_x + wx
        cy = self.cat_y

        if self._opponent == "mittens" and self._mittens_textures:
            textures = self._mittens_textures
            sw, sh = CAT_SPRITE_W_REF * s, CAT_SPRITE_H_REF * s
        elif self._opponent == "hector" and self._hector_textures:
            textures = self._hector_textures
            sw, sh = HECTOR_SPRITE_W_REF * s, HECTOR_SPRITE_H_REF * s
        elif self._opponent == "oscar" and self._oscar_textures:
            textures = self._oscar_textures
            sw, sh = OSCAR_SPRITE_W_REF * s, OSCAR_SPRITE_H_REF * s
        elif self._opponent == "chili" and self._chili_textures:
            textures = self._chili_textures
            sw, sh = CHILI_SPRITE_W_REF * s, CHILI_SPRITE_H_REF * s
        else:
            textures = None

        if textures:
            fps = OSCAR_ANIM_FPS if self._opponent == "oscar" else CAT_ANIM_FPS
            frame_idx = int(self.cat_anim * fps) % len(textures)
            tex = textures[frame_idx]
            draw_sw, draw_sh = sw, sh
            sx = cx + (cw - draw_sw) / 2.0
            sy = cy + (ch - draw_sh) / 2.0
            if self._opponent == "oscar":
                sy += OSCAR_SPRITE_Y_NUDGE_REF * s
            elif self._opponent == "hector":
                sy += HECTOR_SPRITE_Y_NUDGE_REF * s
            # V-flip to correct Kivy's inverted Y; H-flip when moving left
            tc = (1, 1, 0, 1, 0, 0, 1, 0) if self.cat_dir == -1 else (0, 1, 1, 1, 1, 0, 0, 0)
            Color(1, 1, 1, 1)
            Rectangle(texture=tex, pos=(sx, sy), size=(draw_sw, draw_sh), tex_coords=tc)
        else:
            # Placeholder square – art to be added for remaining opponents
            Color(*COLOR_CAT_BODY)
            Rectangle(pos=(cx, cy), size=(cw, ch))

    # ── Secondary cat ─────────────────────────────────────────

    def _draw_secondary_cat(self, z, s, wx):
        """Draw the secondary cat at the same scale as the primary cat."""
        cw = z['cat_w']
        ch = z['cat_h']
        cx = self._cat2_x + wx
        cy = self._cat2_y

        cat_type = self._secondary_cat
        if cat_type == "mittens" and self._mittens_textures:
            textures = self._mittens_textures
            sw = CAT_SPRITE_W_REF * s
            sh = CAT_SPRITE_H_REF * s
        elif cat_type == "hector" and self._hector_textures:
            textures = self._hector_textures
            sw = HECTOR_SPRITE_W_REF * s
            sh = HECTOR_SPRITE_H_REF * s
        elif cat_type == "oscar" and self._oscar_textures:
            textures = self._oscar_textures
            sw = OSCAR_SPRITE_W_REF * s
            sh = OSCAR_SPRITE_H_REF * s
        elif cat_type == "chili" and self._chili_textures:
            textures = self._chili_textures
            sw = CHILI_SPRITE_W_REF * s
            sh = CHILI_SPRITE_H_REF * s
        else:
            textures = None

        if textures:
            sx = cx + (cw - sw) / 2.0
            sy = cy + (ch - sh) / 2.0
            if cat_type == "oscar":
                sy += OSCAR_SPRITE_Y_NUDGE_REF * s
            elif cat_type == "hector":
                sy += HECTOR_SPRITE_Y_NUDGE_REF * s
            fps = OSCAR_ANIM_FPS if cat_type == "oscar" else CAT_ANIM_FPS
            frame_idx = int(self._cat2_anim * fps) % len(textures)
            tex = textures[frame_idx]
            tc = (1, 1, 0, 1, 0, 0, 1, 0) if self._cat2_dir == -1 else (0, 1, 1, 1, 1, 0, 0, 0)
            Color(1, 1, 1, 1.0)
            Rectangle(texture=tex, pos=(sx, sy), size=(sw, sh), tex_coords=tc)
        else:
            Color(*COLOR_CAT_BODY[:3], 0.75)
            Rectangle(pos=(cx, cy), size=(cw, ch))

    # ── Bar overlay ───────────────────────────────────────────────

    def _draw_bar_overlay(self, W, H):
        """Render bar_overlay.png using the same crop/letterbox logic as the background.
        Drawn after the cats so they appear to stand behind the bar counter."""
        if not self._bar_overlay_texture:
            return
        tex = self._bar_overlay_texture
        tex_w, tex_h = tex.size
        scaled_h = (W / tex_w) * tex_h if tex_w > 0 else H
        if scaled_h >= H:
            # Narrow screen: fill width, crop top/bottom symmetrically (same as bg)
            crop_v   = (scaled_h - H) / (2 * scaled_h)
            img_pos  = (self.x, self.y)
            img_size = (W, H)
            tc = (0.0, 1.0 - crop_v, 1.0, 1.0 - crop_v, 1.0, crop_v, 0.0, crop_v)
        else:
            # Wide screen: letterbox, centred vertically (same as bg)
            ry       = self.y + (H - scaled_h) / 2
            img_pos  = (self.x, ry)
            img_size = (W, scaled_h)
            tc = (0.0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0)
        Color(1, 1, 1, 1)
        Rectangle(texture=tex, pos=img_pos, size=img_size, tex_coords=tc)

    # ── Disco flyer prop ──────────────────────────────────────────

    def _draw_disco_flyer(self, s, wx):
        if not self._disco_flyer_texture:
            return
        fw = DISCO_FLYER_W_REF * s
        fh = DISCO_FLYER_H_REF * s
        fx = self.width * DISCO_FLYER_X_F + wx
        fy = self._art_y + self._art_h * DISCO_FLYER_Y_FROM_BOT_F
        Color(1, 1, 1, 1)
        Rectangle(
            texture=self._disco_flyer_texture,
            pos=(fx, fy),
            size=(fw, fh),
            tex_coords=(0, 1, 1, 1, 1, 0, 0, 0),  # V-flip
        )

    # ── Cup ───────────────────────────────────────────────────────

    def _draw_cup(self, cup, z, s, wx):
        broken = cup['state'] == 'broken'
        if broken:
            sw = BEER_BROKEN_SPRITE_W_REF * s
            sh = BEER_BROKEN_SPRITE_H_REF * s
        else:
            sw = BEER_SPRITE_W_REF * s
            sh = BEER_SPRITE_H_REF * s
        x  = cup['cx'] - sw / 2.0 + wx
        y  = cup['cy'] - sh / 2.0

        # tex_coords order: bottom-left, bottom-right, top-right, top-left (u,v pairs)
        # V is inverted vs PNG storage, so use v=1 at bottom and v=0 at top to flip right-side-up.
        # H flip additionally swaps the U coords left↔right.
        tc = (1, 1, 0, 1, 0, 0, 1, 0) if cup.get('flip_h') else (0, 1, 1, 1, 1, 0, 0, 0)

        tex = self._beer_broken_texture if broken else self._beer_texture
        Color(1, 1, 1, 1)
        Rectangle(texture=tex, pos=(x, y), size=(sw, sh), tex_coords=tc)

    # ── Mouse ─────────────────────────────────────────────────────

    def _draw_mouse(self, m, z, s, wx):
        mx = m['x'] + wx
        my = m['y']

        if self._mouse_texture:
            sw = MOUSE_SPRITE_W_REF * s
            sh = MOUSE_SPRITE_H_REF * s
            Color(1, 1, 1, 1)
            Rectangle(
                texture=self._mouse_texture,
                pos=(mx, my),
                size=(sw, sh),
                tex_coords=(0, 1, 1, 1, 1, 0, 0, 0),  # V-flip
            )
        else:
            mw, mh = z['mouse_w'], z['mouse_h']

            # Tail
            Color(0.38, 0.38, 0.38, 1)
            Line(
                points=[mx + mw / 2, my + mh * 0.85,
                         mx + mw / 2, my + mh * 1.15],
                width=max(1.5, s),
            )

            # Body
            Color(*COLOR_MOUSE_BODY)
            Ellipse(pos=(mx, my + mh * 0.28), size=(mw, mh * 0.62))

            # Head
            head_r = mw * 0.55
            Ellipse(
                pos=(mx + mw / 2 - head_r, my + mh * 0.02),
                size=(head_r * 2, mh * 0.38),
            )

            # Ears
            ear_r = mw * 0.28
            Color(0.70, 0.55, 0.55, 1)
            Ellipse(pos=(mx + mw * 0.05, my + mh * 0.30), size=(ear_r, ear_r))
            Ellipse(pos=(mx + mw * 0.60, my + mh * 0.30), size=(ear_r, ear_r))

            # Eye
            Color(0.10, 0.10, 0.10, 1)
            er = mw * 0.12
            Ellipse(pos=(mx + mw * 0.35, my + mh * 0.10), size=(er, er))

            # Nose
            Color(*COLOR_MOUSE_NOSE)
            nr = mw * 0.09
            Ellipse(pos=(mx + mw * 0.44, my + mh * 0.03), size=(nr, nr))

    # ── Tray ──────────────────────────────────────────────────────

    def _draw_tray(self, z, wx):
        tw, th = z['tray_w'], z['tray_h']
        tx = self.tray_x + wx
        ty = self.tray_y

        if self._tray_texture:
            Color(1, 1, 1, 1)
            Rectangle(
                texture=self._tray_texture,
                pos=(tx, ty),
                size=(tw, th),
                tex_coords=(0, 1, 1, 1, 1, 0, 0, 0),  # V-flip
            )
        else:
            Color(*COLOR_TRAY)
            Rectangle(pos=(tx, ty), size=(tw, th * 0.52))

        if DEBUG_HITBOXES:
            s = z['s']
            hb_w = TRAY_HB_W_REF * s
            hb_h = TRAY_HB_H_REF * s
            hb_x = tx + (tw - hb_w) / 2.0
            hb_y = ty + th - hb_h
            # Sprite bounds – orange
            Color(1.0, 0.5, 0.0, 0.35)
            Rectangle(pos=(tx, ty), size=(tw, th))
            # Catch hitbox – bright yellow
            Color(1.0, 1.0, 0.0, 0.55)
            Rectangle(pos=(hb_x, hb_y), size=(hb_w, hb_h))

    # ─────────────────────────────────────────────────────────────
    # Cleanup
    # ─────────────────────────────────────────────────────────────

    def stop(self):
        Clock.unschedule(self._update)
        if _ACCEL_AVAILABLE:
            try:
                _accelerometer.disable()
            except Exception:
                pass


# ══════════════════════════════════════════════════════════════════
# _AchievementToast – animated popup shown when an achievement unlocks
# ══════════════════════════════════════════════════════════════════

_TOAST_ART_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "achievements_art")
_TOAST_ASPECT  = 1989 / 459   # width / height of all toast images
_TOAST_IMGS = {
    "first_round":            "firstroundsonme_toast.png",
    "on_the_clock":           "ontheclock_toast.png",
    "disco_fever":            "discofever_toast.png",
    "drunk_on_the_job":       "drunkonthejob_toast.png",
    "no_spills":              "nospills_toast.png",
    "pest_control":           "pestcontrol_toast.png",
    "shaky_hands":            "shakyhands_toast.png",
    "rookie_waiter":          "rookiewaiter_toast.png",
    "veteran_bartender":      "veteranbartender_toast.png",
    "whole_damn_menu":        "thewholedamnmenu_toast.png",
    "chili_survivor":         "chilisurvivor_toast.png",
    "hector_tamer":           "hectortamer_toast.png",
    "glutton_for_punishment": "gluttonforpunishment_toast.png",
    "catastrophic":           "catastrophic_toast.png",
    "bar_survivor":           "barsurvivor_toast.png",
    "kitchen_mise_en_place":  "miseenplace_toast.png",
    "kitchen_head_chef":      "headchef_toast.png",
    "kitchen_iron_chef":      "ironchef_toast.png",
    "kitchen_long_shift":     "thelongshift_toast.png",
    "kitchen_closing_time":   "closingtime_toast.png",
    "kitchen_mittens_buffet": "mittensbuffet_toast.png",
}


class _AchievementToast(Widget):
    """Slides in from the right with achievement art, holds, then slides back out."""

    _SLIDEIN  = 0.40
    _SHOW     = 2.5
    _SLIDEOUT = 0.35

    def __init__(self, key, rest_x, rest_y, screen_right, on_done, **kwargs):
        super().__init__(**kwargs)
        self._on_done      = on_done
        self._phase        = 'slidein'
        self._elapsed      = 0.0
        self._rest_x       = rest_x
        self._rest_y       = rest_y
        self._screen_right = screen_right
        self._tex          = None

        fname = _TOAST_IMGS.get(key)
        if fname:
            try:
                self._tex = CoreImage(os.path.join(_TOAST_ART_DIR, fname)).texture
            except Exception:
                self._tex = None

        self.bind(pos=self._redraw, size=self._redraw)
        Clock.schedule_interval(self._tick, 1.0 / 60.0)

    def _redraw(self, *_):
        self.canvas.clear()
        if self.width == 0 or self.height == 0:
            return
        with self.canvas:
            if self._tex:
                Color(1, 1, 1, 1)
                Rectangle(texture=self._tex, pos=self.pos, size=self.size)
            else:
                Color(0.12, 0.06, 0.02, 0.95)
                RoundedRectangle(pos=self.pos, size=self.size, radius=[14])

    @staticmethod
    def _ease_out(t):
        return 1.0 - (1.0 - t) ** 3

    @staticmethod
    def _ease_in(t):
        return t ** 3

    def _tick(self, dt):
        self._elapsed += dt
        if self._phase == 'slidein':
            t = min(1.0, self._elapsed / self._SLIDEIN)
            self.x = self._screen_right + (self._rest_x - self._screen_right) * self._ease_out(t)
            if self._elapsed >= self._SLIDEIN:
                self.x    = self._rest_x
                self._phase   = 'show'
                self._elapsed = 0.0
        elif self._phase == 'show':
            if self._elapsed >= self._SHOW:
                self._phase   = 'slideout'
                self._elapsed = 0.0
        elif self._phase == 'slideout':
            t = min(1.0, self._elapsed / self._SLIDEOUT)
            self.x = self._rest_x + (self._screen_right - self._rest_x) * self._ease_in(t)
            if self._elapsed >= self._SLIDEOUT:
                Clock.unschedule(self._tick)
                self._on_done()

    def stop(self):
        Clock.unschedule(self._tick)


# ══════════════════════════════════════════════════════════════════
# _SettingsButton – small pause/settings button drawn on the HUD
# ══════════════════════════════════════════════════════════════════

class _SettingsButton(Widget):
    """Image-based settings button rendered in the HUD."""

    _IMG = os.path.join(os.path.dirname(__file__), "..", "assets", "ui", "settings_button.png")

    def __init__(self, callback, **kwargs):
        super().__init__(**kwargs)
        self._callback = callback
        self._pressed  = False
        try:
            self._tex = CoreImage(self._IMG).texture
        except Exception:
            self._tex = None
        self.bind(pos=self._redraw, size=self._redraw)

    def _redraw(self, *_):
        self.canvas.clear()
        if not self._tex or self.width < 2 or self.height < 2:
            return
        with self.canvas:
            Color(1, 1, 1, 1)
            Rectangle(texture=self._tex, pos=self.pos, size=self.size)

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self._pressed = True
            self._redraw()
            return True
        return False

    def on_touch_up(self, touch):
        if self._pressed:
            self._pressed = False
            self._redraw()
            if self.collide_point(*touch.pos) and self._callback:
                self._callback()
            return True
        return False


# ══════════════════════════════════════════════════════════════════
# GameScreen – Screen wrapper with HUD labels
# ══════════════════════════════════════════════════════════════════

class GameScreen(FloatLayout):
    def __init__(self, **kwargs):
        self.name    = kwargs.pop("name", "game")
        self.manager = None
        super().__init__(**kwargs)
        self.player_name  = ""
        self.opponent     = "mittens"
        self.player_icon  = None
        self.mode         = "endless"  # "endless" | "level"
        self.level_num    = None       # int when mode == "level"
        self._game        = None
        self._layout      = FloatLayout()
        self._score_lbl   = None
        self._timer_lbl   = None
        self._clock_ui    = None
        self._go_lbl      = None
        self._settings_btn = None
        self._final_score   = 0
        self._elapsed_secs  = 0.0
        self._resuming      = False   # True when returning from in-game settings
        # ── Achievement toast queue ─────────────────────────────
        self._toast_queue   = []   # [(name, coins), ...]
        self._active_toast  = None
        self._pending_nav   = False
        self._level_success = True
        self.add_widget(self._layout)

    # ─────────────────────────────────────────────────────────────
    # Screen lifecycle
    # ─────────────────────────────────────────────────────────────

    def on_enter(self):
        # ── Returning from in-game settings: just unpause ──────
        if self._resuming:
            self._resuming = False
            if self._game:
                self._game.paused = False
            if self._game and self._game.disco_mode:
                audio_manager.start_disco_music()
            else:
                audio_manager.start_game_music(volume_scale=0.25)
            Clock.schedule_interval(self._hud_tick, 1.0 / 15.0)
            return

        # Destroy previous game instance cleanly
        if self._game:
            self._game.stop()
            self._layout.remove_widget(self._game)
        for w in (self._score_lbl, self._clock_ui, self._timer_lbl,
                  self._go_lbl, self._settings_btn):
            if w and w.parent:
                self._layout.remove_widget(w)

        self._toast_queue  = []
        self._active_toast = None
        self._pending_nav  = False

        level_cfg = LEVELS.get(self.level_num) if self.mode == "level" and self.level_num else None

        self._game = GameWidget(
            player_name=self.player_name,
            opponent=self.opponent,
            player_icon=self.player_icon,
            on_game_over=self._on_game_over,
            on_achievement=self._trigger_achievement,
            mode=self.mode,
            level_cfg=level_cfg,
            on_level_complete=self._on_level_complete,
            on_level_fail=self._on_level_fail,
            size_hint=(1, 1),
            pos_hint={'x': 0, 'y': 0},
        )
        self._layout.add_widget(self._game)

        # HUD – positions set by _update_hud_positions()
        self._score_lbl = Label(
            text="SCORE: 0",
            font_size=fsp(30),
            bold=True,
            color=COLOR_WHITE,
            font_name=_FONT,
            halign="center",
            valign="middle",
            size_hint=(None, None),
            size=(250, 60),
        )
        # Shared helper – build a background panel widget from an asset file
        _assets_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets")

        def _make_panel(filename, opacity=1):
            widget = Widget(size_hint=(None, None), size=(1, 1), opacity=opacity)
            try:
                tex = CoreImage(os.path.join(_assets_dir, filename)).texture
                with widget.canvas:
                    Color(1, 1, 1, 1)
                    widget._rect = Rectangle(texture=tex, pos=widget.pos, size=widget.size)
                def _upd(*_):
                    widget._rect.pos  = widget.pos
                    widget._rect.size = widget.size
                widget.bind(pos=_upd, size=_upd)
            except Exception:
                pass
            return widget

        # Score background panel (ui_empty.png)
        self._score_ui = _make_panel("ui/ui_empty.png")

        # Clock UI image – background panel behind the timer (level mode only)
        self._clock_ui = _make_panel("ui/clock_ui.png",
                                     opacity=1 if self.mode == "level" else 0)

        self._timer_lbl = Label(
            text="",
            font_size=fsp(30),
            bold=True,
            color=COLOR_WHITE,
            font_name=_FONT,
            halign="center",
            valign="middle",
            opacity=1 if self.mode == "level" else 0,
            size_hint=(None, None),
            size=(250, 60),
        )
        self._go_lbl = Label(
            text="GAME OVER",
            font_size=fsp(64),
            bold=True,
            color=COLOR_RED,
            font_name=_FONT,
            opacity=0,
            size_hint=(None, None),
            size=(600, 100),
        )
        # Settings button – small button to the left of the lives widget
        self._settings_btn = _SettingsButton(
            callback=self._on_settings,
            size_hint=(None, None),
        )

        self._layout.add_widget(self._score_ui)
        self._layout.add_widget(self._score_lbl)
        self._layout.add_widget(self._clock_ui)
        self._layout.add_widget(self._timer_lbl)
        self._layout.add_widget(self._go_lbl)
        self._layout.add_widget(self._settings_btn)

        self._update_hud_positions()
        self._game.bind(size=self._update_hud_positions)

        if self._game.disco_mode:
            audio_manager.start_disco_music()
        else:
            audio_manager.start_game_music(volume_scale=0.25)

        Clock.schedule_interval(self._hud_tick, 1.0 / 15.0)

    def on_leave(self):
        audio_manager.stop_music()
        Clock.unschedule(self._hud_tick)
        if not self._resuming:
            # Full teardown — not just pausing for settings
            Clock.unschedule(self._maybe_navigate)
            self._pending_nav = False
            if self._active_toast:
                self._active_toast.stop()
                self._layout.remove_widget(self._active_toast)
                self._active_toast = None
            self._toast_queue.clear()
            if self._game:
                self._game.stop()

    # ─────────────────────────────────────────────────────────────
    # HUD positioning – kept inside art bounds, not in the bars
    # ─────────────────────────────────────────────────────────────

    def _update_hud_positions(self, *_):
        if not self._game:
            return
        g = self._game
        W, H = g.width, g.height
        if W < 2 or H < 2:
            return

        sx, sy, sw, sh = _bar_zone_rect(BAR_HUD_ZONE_SCORE, W, H)
        tx, ty, tw, th = _bar_zone_rect(BAR_HUD_ZONE_TIMER, W, H)

        if self._score_ui:
            self._score_ui.pos  = (sx, sy)
            self._score_ui.size = (sw, sh)
        if self._score_lbl:
            self._score_lbl.pos       = (sx, sy)
            self._score_lbl.size      = (sw, sh)
            self._score_lbl.text_size = (sw, None)
        if self._clock_ui:
            self._clock_ui.pos  = (tx, ty)
            self._clock_ui.size = (tw, th)
        if self._timer_lbl:
            self._timer_lbl.pos       = (tx, ty)
            self._timer_lbl.size      = (tw, th)
            self._timer_lbl.text_size = (tw, None)
        if self._go_lbl:
            art_y = g._art_y if g._art_h > 1 else 0.0
            art_h = g._art_h if g._art_h > 1 else H
            self._go_lbl.pos = (
                W / 2 - self._go_lbl.width / 2,
                art_y + art_h / 2 - self._go_lbl.height / 2,
            )
        if self._settings_btn:
            bx, by, bw, bh = _bar_zone_rect(BAR_HUD_ZONE_SETTINGS, W, H)
            self._settings_btn.pos  = (bx, by)
            self._settings_btn.size = (bw, bh)

    # ─────────────────────────────────────────────────────────────
    # Settings button callback
    # ─────────────────────────────────────────────────────────────

    def _on_settings(self):
        if not self._game or self._game.game_over:
            return
        self._resuming = True
        self._game.paused = True
        settings_screen = self.manager.get_screen("settings")
        settings_screen.in_game = True
        self.manager.current = "settings"

    # ─────────────────────────────────────────────────────────────
    # HUD updates
    # ─────────────────────────────────────────────────────────────

    def _hud_tick(self, dt):
        if not self._game:
            return
        g = self._game
        if self._score_lbl:
            self._score_lbl.text = f"SCORE: {g.score}"
        if self._timer_lbl and self.mode == "level" and g._shift_timer is not None:
            secs  = max(0, int(g._shift_timer))
            mins  = secs // 60
            secs  = secs % 60
            self._timer_lbl.text = f"{mins}:{secs:02d}"
        if self._go_lbl and g.game_over and g._show_game_over:
            self._go_lbl.opacity = min(1.0, self._go_lbl.opacity + 0.05)

    # ─────────────────────────────────────────────────────────────
    # Achievement helpers
    # ─────────────────────────────────────────────────────────────

    def _trigger_achievement(self, key):
        """Called by GameWidget (real-time) or end-of-game checks."""
        if not self.player_name:
            return
        if key not in ACHIEVEMENTS:
            return
        if self.mode != "endless":
            return
        if not is_endless_unlocked(self.player_name):
            return
        if is_achievement_unlocked(self.player_name, key):
            return
        coins = ACHIEVEMENTS[key]["coins"]
        if unlock_achievement(self.player_name, key, coins):
            self._enqueue_toast(key, ACHIEVEMENTS[key]["name"], coins)

    def _enqueue_toast(self, key, name, coins):
        self._toast_queue.append((key, name, coins))
        if self._active_toast is None:
            self._show_next_toast()

    def _show_next_toast(self):
        if not self._toast_queue:
            self._active_toast = None
            self._maybe_navigate()
            return
        key, _, _ = self._toast_queue.pop(0)
        audio_manager.play_achievement_unlocked()
        W  = self._layout.width
        sr = self._layout.right   # screen right edge
        if key in _TOAST_IMGS:
            toast_w = min(W * 0.72, 680)
            toast_h = toast_w / _TOAST_ASPECT
        else:
            toast_w = min(380, W * 0.80)
            toast_h = 90
        g = self._game
        art_top = (g._art_y + g._art_h) if (g and g._art_h > 1) else self._layout.top
        rest_x = sr - toast_w - 16
        rest_y = art_top - toast_h - 16
        toast = _AchievementToast(
            key=key,
            rest_x=rest_x,
            rest_y=rest_y,
            screen_right=sr,
            on_done=self._on_toast_done,
            size_hint=(None, None),
            size=(toast_w, toast_h),
        )
        toast.x = sr        # start off-screen right
        toast.y = rest_y
        self._layout.add_widget(toast)
        self._active_toast = toast

    def _on_toast_done(self):
        if self._active_toast:
            self._layout.remove_widget(self._active_toast)
            self._active_toast = None
        self._show_next_toast()

    # ─────────────────────────────────────────────────────────────
    # Game-over callback
    # ─────────────────────────────────────────────────────────────

    def _on_level_complete(self, final_score):
        """Called when the shift timer expires in level mode (success)."""
        Clock.unschedule(self._hud_tick)
        self._final_score = final_score
        g = self._game
        # Elapsed = full level duration (timer ran to 0)
        cfg = LEVELS.get(self.level_num, {})
        self._elapsed_secs = float(cfg.get("duration_secs", 0))
        cups_this_game = g._cups_caught_this_game if g else 0
        update_player_stats(self.player_name, cups_caught=cups_this_game, games_played=1)
        # Fire cumulative achievements
        from game_utils import get_player_stats
        stats = get_player_stats(self.player_name)
        total = stats.get("total_cups_caught", 0)
        if total >= 500:
            self._trigger_achievement("rookie_waiter")
        if total >= 5000:
            self._trigger_achievement("veteran_bartender")
        if total >= 25000:
            self._trigger_achievement("whole_damn_menu")
        if stats.get("total_games_played", 0) >= 50:
            self._trigger_achievement("glutton_for_punishment")
        # Navigate to level_end
        self._pending_nav = True
        self._level_success = True
        self._maybe_navigate()

    def _on_level_fail(self, final_score):
        """Called when the player runs out of lives in level mode (fail)."""
        Clock.unschedule(self._hud_tick)
        self._final_score = final_score
        g = self._game
        # Elapsed = how much of the shift had passed before failure
        cfg = LEVELS.get(self.level_num, {})
        duration = float(cfg.get("duration_secs", 0))
        remaining = g._shift_timer if (g and g._shift_timer is not None) else 0.0
        self._elapsed_secs = duration - remaining
        cups_this_game = g._cups_caught_this_game if g else 0
        update_player_stats(self.player_name, cups_caught=cups_this_game, games_played=1)
        self._pending_nav = True
        self._level_success = False
        self._maybe_navigate()

    def _on_game_over(self, final_score):
        Clock.unschedule(self._hud_tick)
        self._final_score = final_score
        g = self._game

        # ── Update cumulative stats ──────────────────────────────
        cups_this_game = g._cups_caught_this_game if g else 0
        update_player_stats(
            self.player_name,
            cups_caught=cups_this_game,
            games_played=1,
            opponent=self.opponent,
        )

        # ── Check end-of-game and cumulative achievements ────────
        from game_utils import get_player_stats
        stats = get_player_stats(self.player_name)

        # Opponent-specific score milestones
        if self.opponent == "chili" and final_score >= 50:
            self._trigger_achievement("chili_survivor")
        if self.opponent == "hector" and final_score >= 75:
            self._trigger_achievement("hector_tamer")

        # All 4 opponents played
        if set(stats.get("opponents_played", [])) >= {"oscar", "mittens", "hector", "chili"}:
            self._trigger_achievement("on_the_clock")

        # Cumulative cups
        total = stats.get("total_cups_caught", 0)
        if total >= 500:
            self._trigger_achievement("rookie_waiter")
        if total >= 5000:
            self._trigger_achievement("veteran_bartender")
        if total >= 25000:
            self._trigger_achievement("whole_damn_menu")

        # Total games
        if stats.get("total_games_played", 0) >= 50:
            self._trigger_achievement("glutton_for_punishment")

        # Navigate after toasts finish (or immediately if none)
        self._pending_nav = True
        self._maybe_navigate()

    def _maybe_navigate(self, *_):
        if not self._pending_nav:
            return
        if self._active_toast or self._toast_queue:
            Clock.schedule_once(self._maybe_navigate, 0.5)
            return
        self._pending_nav = False
        if self.mode == "level":
            # ── First-time level 3 completion → kitchen intro cutscene ──────
            if self.level_num == 3 and self._level_success:
                from game_utils import get_level_progress, mark_level_complete
                prog = get_level_progress(self.player_name)
                if not prog.get(3, {}).get("completed", False):
                    mark_level_complete(self.player_name, 3, self._final_score)
                    self.manager.current = "kitchen_intro_cutscene"
                    return
            # ── Normal flow ─────────────────────────────────────────────────
            le = self.manager.get_screen("level_end")
            le.level_num    = self.level_num
            le.score        = self._final_score
            le.success      = self._level_success
            le.elapsed_secs = self._elapsed_secs
            self.manager.current = "level_end"
        else:
            lb = self.manager.get_screen("leaderboard")
            lb.current_player   = self.player_name
            lb.current_score    = self._final_score
            lb.current_opponent = self.opponent
            self.manager.current = "leaderboard"
