"""
screens/kitchen_gameplay.py – Kitchen Duty game loop.

Coordinate system
──────────────────
Kivy: y=0 at BOTTOM, increases UPWARD.
All image-fraction positions use y=0 at the IMAGE TOP, 1 at the IMAGE BOTTOM.
Conversion: screen_y = img_y + (1.0 - fy) * img_h

Layout zones (fraction of kitchen.png source 3915 × 1773)
──────────────────────────────────────────────────────────
• Order tickets   – upper 35 % of image, 5 clothespin slots
• Counter surface – y_frac ≈ 0.379 from image top
• Serving station – far left  (cloche + bell tap zone)
• Left grey area  – x 0.073–0.290  (ingredients: bread, lettuce, tomato)
• Centre area     – x 0.291–0.590  (sandwich display + cat contamination zone)
• Right grey area – x 0.591–0.991  (ingredients: cheese, ham)
• Cat walking y   – image frac 0.395 from top

Canvas is cleared and redrawn every frame; no PushMatrix/PopMatrix used.
"""

import math
import os
import random

from kivy.uix.floatlayout import FloatLayout
from kivy.uix.widget import Widget
from kivy.uix.label import Label
from kivy.graphics import Color, Rectangle, RoundedRectangle, Ellipse, Line
from kivy.clock import Clock
from kivy.core.image import Image as CoreImage

from game_constants import (
    COLOR_BG,
    KITCHEN_BG_ASPECT, KITCHEN_BG_W, KITCHEN_BG_H,
    KITCHEN_HUD_ZONE_TIMER, KITCHEN_HUD_ZONE_SCORE, KITCHEN_HUD_ZONE_COMPLAINTS,
    KITCHEN_TICKET_SLOTS,
    KITCHEN_COUNTER_TOP_Y_F,
    KITCHEN_PLATE_X1_F, KITCHEN_PLATE_X2_F, KITCHEN_PLATE_Y1_F, KITCHEN_PLATE_Y2_F,
    KITCHEN_SERVE_X1_F, KITCHEN_SERVE_X2_F, KITCHEN_SERVE_Y1_F, KITCHEN_SERVE_Y2_F,
    KITCHEN_LEFT_X1_F, KITCHEN_LEFT_X2_F, KITCHEN_LEFT_Y1_F, KITCHEN_LEFT_Y2_F,
    KITCHEN_CENTER_X1_F, KITCHEN_CENTER_X2_F, KITCHEN_CENTER_Y1_F, KITCHEN_CENTER_Y2_F,
    KITCHEN_RIGHT_X1_F, KITCHEN_RIGHT_X2_F, KITCHEN_RIGHT_Y1_F, KITCHEN_RIGHT_Y2_F,
    KITCHEN_PANS_X_F, KITCHEN_PANS_Y_F, KITCHEN_PANS_W_F, KITCHEN_PANS_H_F,
    KITCHEN_CAT_Y_F,
    KITCHEN_CAT_W_REF, KITCHEN_CAT_H_REF,
    KITCHEN_CAT_SPAWN_BASE,
    KITCHEN_CAT_PEEK_TIME, KITCHEN_CAT_RISE_TIME,
    KITCHEN_CAT_PEEK_ANIM_FPS, KITCHEN_CAT_PEEK_SCALE, KITCHEN_CAT_PEEK_Y_F,
    KITCHEN_CAT_PEEK_PAUSE,
    KITCHEN_ORDER_PATIENCE_BASE,
    KITCHEN_ORDER_INTERVAL_BASE,
    KITCHEN_SCORE_PER_ORDER, KITCHEN_COINS_BASE,
    KITCHEN_MAX_COMPLAINTS,
    KITCHEN_RUSH_PERIOD, KITCHEN_RUSH_DURATION,
    KITCHEN_END_DELAY,
    KITCHEN_VICTOR_W_REF, KITCHEN_VICTOR_H_REF, KITCHEN_VICTOR_Y_F,
    KITCHEN_VICTOR_SPEED_F, KITCHEN_VICTOR_WALK_FPS,
    KITCHEN_INGREDIENT_COLORS, KITCHEN_INGREDIENT_LABELS, KITCHEN_INGR_OFFSETS, KITCHEN_INGR_SCALES,
    COLOR_GOLD, COLOR_WHITE,
    CAT_ANIM_FPS,
    DEBUG_HITBOXES,
)
from game_utils import fsp, get_current_player, mark_kitchen_level_complete, is_kitchen_endless_unlocked, unlock_achievement
from kitchen_level_config import KITCHEN_LEVELS, recipe_display_name
import audio_manager
import game_settings

_ASSETS = os.path.join(os.path.dirname(__file__), "..", "assets")
_FONT   = os.path.join(_ASSETS, "fonts", "Pixelfont.ttf")

# Ingredient order for display (bottom → top in sandwich stack)
_INGREDIENTS = ["bread", "ham", "cheese", "lettuce", "tomato", "onion", "bacon", "eggs"]

# Left grey area  – 2 rows × 3 columns
# Row 0 (top):    onion, lettuce, tomato  (hidden in early levels)
# Row 1 (bottom): bread, ham, cheese      (always visible)
_LEFT_INGR  = ["onion", "lettuce", "tomato", "bread", "ham", "cheese"]

# Right stove area – 2 items in a single column (next to the stove)
_RIGHT_INGR = ["bacon", "eggs"]

# How many cat animation frames to cycle through
_CAT_ANIM_FRAMES = 5

# Patience bar colour thresholds
_PATIENCE_RED    = 0.30   # fraction remaining → red
_PATIENCE_ORANGE = 0.55   # fraction remaining → orange

# Seconds to cook a right-area ingredient in the pan
_PAN_COOK_TIME  = 3.0
# Seconds after ready before the food burns (timer keeps running after ready)
_PAN_BURN_TIME  = _PAN_COOK_TIME + 5.0

# Pan ingredient display: scale (sx, sy), horizontal pixel offset,
# and independent vertical offsets: top = pixels down from slot top,
# bottom = pixels up from slot bottom (positive = push inward).
# Tweak these to resize / reposition the egg/bacon art inside the pan zone.
_PAN_INGR_SCALES        = {"eggs": (0.62, 0.62), "bacon": (0.62, 0.62)}
_PAN_INGR_OFFSET_X      = {"eggs": 10,           "bacon": 22}
_PAN_INGR_OFFSET_TOP    = {"eggs": 28,            "bacon": 28}   # pixels down from slot top
_PAN_INGR_OFFSET_BOTTOM = {"eggs": 52,            "bacon": 52}   # pixels up from slot bottom

# Per-slot overrides: key is (slot_index, ingr). Slot 0 = top pan, 1 = bottom pan.
# Falls back to the per-ingredient dict when not set.
_PAN_SLOT_OFFSET_X      = {(0, "bacon"): 5,  (1, "bacon"): 25, (1, "eggs"): 16}
_PAN_SLOT_OFFSET_TOP    = {(1, "bacon"): 26}
_PAN_SLOT_OFFSET_BOTTOM = {(1, "bacon"): 54}

# Scale applied to the drag float size (relative to btn_w * 0.80 base size).
# 1.0 = default, < 1.0 = smaller ghost image while dragging from tray.
_DRAG_FLOAT_SCALES      = {"eggs": 0.65}

# Mapping from sorted recipe tuple → ticket image filename (no extension).
_RECIPE_TICKET_FILES = {
    ("bread", "cheese"):                            "r_cheese_ticket",
    ("bread", "ham"):                               "r_ham_ticket",
    ("bread", "lettuce", "tomato"):                 "r_salad_ticket",
    ("bread", "ham", "tomato"):                     "r_club_ticket",
    ("bread", "cheese", "lettuce"):                 "r_garden_ticket",
    ("bread", "cheese", "ham"):                     "r_ham_chse_ticket",
    ("bread", "cheese", "ham", "tomato"):           "r_deluxe_ticket",
    ("bread", "cheese", "lettuce", "tomato"):       "r_veggie_ticket",
    ("bread", "onion"):                             "r_onion_ticket",
    ("bread", "ham", "onion"):                      "r_ham_onion_ticket",
    ("bread", "ham", "onion", "tomato"):            "r_full_club_ticket",
    ("bread", "cheese", "ham", "onion", "tomato"):  "r_loaded_ticket",
    ("bacon", "bread"):                             "r_bacon_ticket",
    ("bread", "eggs"):                              "r_eggs_ticket",
    ("bacon", "bread", "eggs"):                     "r_brekkie_ticket",
}


# ══════════════════════════════════════════════════════════════════
# KitchenGameWidget
# ══════════════════════════════════════════════════════════════════

class KitchenGameWidget(Widget):
    """All game logic and canvas rendering for Kitchen Duty."""

    def __init__(self, player_name, level_num, level_cfg, on_success, on_fail, **kwargs):
        super().__init__(**kwargs)
        self.player_name = player_name
        self._level_num  = level_num
        self._level_cfg  = level_cfg
        self._on_success = on_success
        self._on_fail    = on_fail

        # ── Game state ──────────────────────────────────────────
        self._shift_timer  = float(level_cfg.get("duration_secs", 120))
        self._alarm_played = False
        self._complaints   = 0
        self._max_complaints = KITCHEN_MAX_COMPLAINTS
        self.score  = 0
        self.coins  = 0
        self._state = "playing"   # "playing" | "end_pending"
        self._end_acc     = 0.0
        self._end_success = False

        # ── Order system ────────────────────────────────────────
        self._orders         = []    # list of order dicts
        self._order_id_seq   = 0
        self._max_orders     = level_cfg.get("max_orders", 1)
        self._recipe_pool    = list(level_cfg.get("recipe_pool", [("bread", "cheese")]))
        self._patience_mult  = float(level_cfg.get("patience_mult", 1.0))
        raw_interval         = KITCHEN_ORDER_INTERVAL_BASE * float(level_cfg.get("order_interval_mult", 1.0))
        self._order_interval = raw_interval
        # Start accumulator so the first order appears ~3 s after the shift begins
        self._order_spawn_acc = max(0.0, raw_interval - 3.0)

        # ── Sandwich assembly ───────────────────────────────────
        self._sandwich            = []     # ingredient keys in tap order
        self._sandwich_contaminated = False

        # ── Plate / serving state ────────────────────────────────
        self._plate_dish         = []     # dish sitting on the plate (ready to serve)
        self._plate_contaminated = False
        self._dragging_dish      = False  # True while player drags sandwich to plate
        self._drag_x             = 0.0
        self._drag_y             = 0.0

        # ── Dish lid animation ───────────────────────────────────
        # 0.0 = closed (dish_top1), 3.0 = fully open (dish_top4)
        self._dish_lid_f      = 0.0
        self._dish_lid_target = 0.0   # set to 3.0 while hovering over plate

        # ── Victor serving animation ────────────────────────────────
        # phase: None | 'walking_in' | 'walking_out'
        self._victor_phase      = None
        self._victor_x          = 0.0
        self._victor_anim_acc   = 0.0
        self._victor_lid_visible = True   # False while Victor carries the plate out

        # ── Order quota ──────────────────────────────────────────
        self._orders_completed = 0
        self._orders_required  = int(level_cfg.get("orders_required", 5))
        self._cat_steals_this_run = 0

        # ── Bell press animation ─────────────────────────────────
        self._bell_pressed = 0.0      # countdown; shows bell_down frame while > 0

        # ── Full-cloche bell animation ────────────────────────────
        self._bell_fullcloche_anim_t = 0.0   # accumulator for cycling frames
        self._bell_rang_for_plate    = False  # True after bell rung; resets when plate clears

        # ── Trash chute animation ─────────────────────────────────
        self._trash_anim_t    = 0.0   # countdown while animation is playing
        self._trash_animating = False

        # ── Ingredient drag (tray → prep area or pan slot) ───────
        self._dragging_ingr  = None   # ingredient key being dragged from tray
        self._ingr_drag_x    = 0.0
        self._ingr_drag_y    = 0.0

        # ── Pan drag (cooked pan slot → sandwich) ────────────────
        self._dragging_pan_ingr = None
        self._dragging_pan_slot = None   # slot index being dragged from
        self._pan_drag_x        = 0.0
        self._pan_drag_y        = 0.0

        # ── Active ingredients for this level ────────────────────
        # Flattened set of every ingredient that appears in any recipe this level.
        self._active_ingr = set()
        for recipe in level_cfg.get("recipe_pool", []):
            self._active_ingr.update(recipe)

        # ── Pan / cooking state ──────────────────────────────────
        # Each right-area ingredient must be cooked in its pan first.
        self._pan_enabled = bool(level_cfg.get("pan_enabled", False))
        self._pans = {
            i: {"ingr": None, "timer": 0.0, "ready": False, "burned": False}
            for i in range(len(_RIGHT_INGR))
        }

        # ── Cat system ──────────────────────────────────────────
        self._cat_enabled   = bool(level_cfg.get("cat_enabled", False))
        self._cat_key       = level_cfg.get("cat_key", "mittens")
        self._cat_speed_mult = float(level_cfg.get("cat_speed_mult", 1.0))
        self._cat_spawn_mult = float(level_cfg.get("cat_frequency_mult", 1.0))
        self._contamination_enabled = bool(level_cfg.get("contamination_enabled", False))
        self._cats          = []
        self._cat_spawn_acc = 0.0

        # ── Rush mode ───────────────────────────────────────────
        self._rush_mode = bool(level_cfg.get("rush_mode", False))
        self._in_rush   = False
        self._rush_acc  = 0.0

        # ── Visual feedback timers ──────────────────────────────
        self._serve_flash       = 0.0
        self._wrong_flash       = 0.0
        self._complaint_flash   = 0.0
        self._contamination_flash = 0.0

        # ── Layout cache (populated in _compute_layout) ─────────
        self._L   = {}
        self._img_y = 0.0   # bottom-y of kitchen image in Kivy coords
        self._img_h = 0.0

        # ── Touch tracking ──────────────────────────────────────
        self._pressed_ingr = None   # ingredient key being pressed

        # ── Load assets ─────────────────────────────────────────
        self._load_textures()

        self.bind(size=self._on_resize, pos=self._on_resize)
        self._clock = Clock.schedule_interval(self._update, 1.0 / 60.0)

        # ── Ingredient button label overlays ────────────────────────
        # Labels are child widgets; they render on top of the canvas.
        self._ingr_labels = {}
        for ingr in (_LEFT_INGR + _RIGHT_INGR):
            lbl = Label(
                text=KITCHEN_INGREDIENT_LABELS.get(ingr, ingr.upper()),
                font_name=_FONT,
                font_size=fsp(18),
                color=(0.10, 0.05, 0.02, 1.0),
                halign="center",
                valign="middle",
                size_hint=(None, None),
            )
            self._ingr_labels[ingr] = lbl
            self.add_widget(lbl)

        # ── Ticket slot recipe-name label overlays (one per slot) ───
        self._ticket_labels = []
        for _ in range(5):
            lbl = Label(
                text="",
                font_name=_FONT,
                font_size=fsp(18),
                color=(0.10, 0.05, 0.02, 1.0),
                halign="center",
                valign="middle",
                size_hint=(None, None),
                opacity=0,
            )
            self._ticket_labels.append(lbl)
            self.add_widget(lbl)

    # ─────────────────────────────────────────────────────────────
    # Asset loading
    # ─────────────────────────────────────────────────────────────

    def _load_textures(self):
        def _lt(path):
            if not os.path.isfile(path):
                return None
            try:
                return CoreImage(path).texture
            except Exception:
                return None

        self._bg_tex          = _lt(os.path.join(_ASSETS, "screens", "kitchen.png"))
        self._pans_tex        = _lt(os.path.join(_ASSETS, "food", "pans.png"))
        self._order_ticket_tex = _lt(os.path.join(_ASSETS, "tickets", "order_ticket.png"))

        # Per-recipe ticket textures (r_*_ticket.png); fallback to order_ticket.png
        self._recipe_ticket_texes = {
            recipe: _lt(os.path.join(_ASSETS, "tickets", f"{fname}.png"))
            for recipe, fname in _RECIPE_TICKET_FILES.items()
        }

        # Dish presentation cloche
        self._dish_bottom_tex  = _lt(os.path.join(_ASSETS, "food", "dish_bottom.png"))
        self._dish_top_texes   = [
            _lt(os.path.join(_ASSETS, "food", f"dish_top{i}.png")) for i in range(1, 5)
        ]  # [0]=closed … [3]=fully open

        # Victor serving animation
        self._victor_noplate_tex = _lt(os.path.join(_ASSETS, "characters", "victor_noplate.png"))
        self._victor_plate_tex   = _lt(os.path.join(_ASSETS, "characters", "victor_plate.png"))
        self._victor_walk_texes  = [t for t in
            (_lt(os.path.join(_ASSETS, "characters", f"walking_victor{i}.png")) for i in range(1, 5))
            if t is not None]

        # Ingredient tray images (optional – falls back to coloured box)
        # Explicit filename overrides for irregular plurals / custom names.
        _tray_filenames = {
            "tomato": "tomatoes_tray.png",
        }
        self._ingr_tray_texes = {}
        for ingr in _LEFT_INGR:
            filename = _tray_filenames.get(ingr, f"{ingr}_tray.png")
            self._ingr_tray_texes[ingr] = _lt(os.path.join(_ASSETS, "food", filename))
        # Right-area ingredient tray images (bacon_tray.png, eggs_tray.png, etc.)
        for ingr in _RIGHT_INGR:
            self._ingr_tray_texes[ingr] = _lt(os.path.join(_ASSETS, "food", f"{ingr}_tray.png"))

        # Float (drag ghost) images – shown while dragging an ingredient.
        # Falls back to the tray image if no float variant exists.
        _float_filenames = {
            "tomato": "tomatoes_float.png",
        }
        self._ingr_float_texes = {}
        for ingr in _LEFT_INGR:
            filename = _float_filenames.get(ingr, f"{ingr}_float.png")
            tex = _lt(os.path.join(_ASSETS, "food", filename))
            self._ingr_float_texes[ingr] = tex if tex else self._ingr_tray_texes.get(ingr)
        # Right-area ingredients: prefer {ingr}_float.png, fall back to {base}_raw.png
        _right_pan_base = {"eggs": "egg"}
        for ingr in _RIGHT_INGR:
            base = _right_pan_base.get(ingr, ingr)
            tex = (_lt(os.path.join(_ASSETS, "food", f"{ingr}_float.png")) or
                   _lt(os.path.join(_ASSETS, "food", f"{base}_float.png")) or
                   _lt(os.path.join(_ASSETS, "food", f"{base}_raw.png")))
            self._ingr_float_texes[ingr] = tex

        # Combo prepare texture cache – lazy-loaded keyed by frozenset of ingredients.
        # Naming convention: sorted ingredients joined by "_" + "_prepare.png"
        # e.g. bread alone → bread_prepare.png
        #      bread + cheese → bread_cheese_prepare.png
        # If the file doesn't exist the ingredient cannot be added to the sandwich.
        self._combo_tex_cache = {}

        # Combo plate texture cache – same naming but "_plate.png"
        # Shown on the dish_bottom area when a dish is sitting on the plate.
        self._plate_tex_cache = {}

        # Pan ingredient art: {ingr: {'raw': tex, 'cooked': tex, 'burnt': tex}}
        # Files: {base}_raw.png / {base}_cooked.png / {base}_burnt.png (all optional)
        # Override base name for ingredients whose key differs from file prefix.
        _pan_base = {"eggs": "egg"}
        self._pan_ingr_texes = {}
        for ingr in _RIGHT_INGR:
            base = _pan_base.get(ingr, ingr)
            self._pan_ingr_texes[ingr] = {
                'raw':          _lt(os.path.join(_ASSETS, "food", f"{base}_raw.png")),
                'cooked':       _lt(os.path.join(_ASSETS, "food", f"{base}_cooked.png")),
                'burnt':        _lt(os.path.join(_ASSETS, "food", f"{base}_burnt.png")),
                # Float used as drag ghost when moving cooked ingredient to sandwich
                'cooked_float': (_lt(os.path.join(_ASSETS, "food", f"{ingr}_float_cooked.png")) or
                                 _lt(os.path.join(_ASSETS, "food", f"{base}_float_cooked.png"))),
            }

        # Bell
        self._bell_tex      = _lt(os.path.join(_ASSETS, "ui", "bell.png"))
        self._bell_down_tex = _lt(os.path.join(_ASSETS, "ui", "bell_down.png"))
        self._bell_fullcloche_texes = [
            _lt(os.path.join(_ASSETS, "ui", f"bell_fullcloche{i}.png")) for i in range(1, 5)
        ]  # [0..3] looping animation played when cloche has a dish

        # Trash chute
        self._trash_texes = [
            _lt(os.path.join(_ASSETS, f"trash_shute{i}.png")) for i in range(1, 5)
        ]  # [0]=idle, [1..3]=animation frames

        # Cat running frames kept for potential future use
        self._cat_texes = {}
        for cat_key, prefix in (("mittens", "mittens_running"), ("hector", "hector_running")):
            frames = [_lt(os.path.join(_ASSETS, "characters", f"{prefix}{i}.png")) for i in range(1, 6)]
            self._cat_texes[cat_key] = [t for t in frames if t is not None]

        # Cat peek animation frames (mittens_peeking1–5.png)
        self._cat_peek_texes = [t for t in
            (_lt(os.path.join(_ASSETS, "characters", f"mittens_peeking{i}.png")) for i in range(1, 6))
            if t is not None]
        # Cat steal animation frames (mittens_stealing_1–7.png)
        self._cat_steal_texes = [t for t in
            (_lt(os.path.join(_ASSETS, "characters", f"mittens_stealing_{i}.png")) for i in range(1, 8))
            if t is not None]

    # ─────────────────────────────────────────────────────────────
    # Layout helpers
    # ─────────────────────────────────────────────────────────────

    def _on_resize(self, *_):
        self._compute_layout()

    def _compute_layout(self):
        W, H = self.width, self.height
        if W < 2 or H < 2:
            return

        # Fill-width letterbox (same logic as all other screens)
        if self._bg_tex:
            tex_w, tex_h = self._bg_tex.size
            img_w = W
            img_h = W * tex_h / tex_w
        else:
            img_w = W
            img_h = H

        img_x = self.x
        img_y = self.y + (H - img_h) / 2.0

        self._img_y = img_y
        self._img_h = img_h

        # Helper closures bound to this frame's img dimensions
        def ix(fx):  return img_x + fx * img_w
        def iy(fy):  return img_y + (1.0 - fy) * img_h  # y from image top → Kivy y
        def sw(fw):  return fw * img_w
        def sh(fh):  return fh * img_h

        L = self._L
        L['ix'] = ix;  L['iy'] = iy
        L['sw'] = sw;  L['sh'] = sh
        L['img_x'] = img_x;  L['img_y'] = img_y
        L['img_w'] = img_w;  L['img_h'] = img_h

        # ── Order ticket slots ──────────────────────────────────
        L['ticket_slots'] = [
            {
                'cx': (ix(x1_f) + ix(x2_f)) / 2,
                'y':  iy(y_bot_f),
                'w':  ix(x2_f) - ix(x1_f),
                'h':  iy(y_top_f) - iy(y_bot_f),
            }
            for x1_f, x2_f, y_top_f, y_bot_f in KITCHEN_TICKET_SLOTS
        ]

        # ── Plate drop zone (above bell) ─────────────────────────
        L['plate_x'] = ix(KITCHEN_PLATE_X1_F)
        L['plate_y'] = iy(KITCHEN_PLATE_Y2_F)
        L['plate_w'] = sw(KITCHEN_PLATE_X2_F - KITCHEN_PLATE_X1_F)
        L['plate_h'] = sh(KITCHEN_PLATE_Y2_F - KITCHEN_PLATE_Y1_F)

        # ── Bell tap zone (below plate) ───────────────────────────
        L['bell_x'] = ix(KITCHEN_SERVE_X1_F)
        L['bell_y'] = iy(KITCHEN_SERVE_Y2_F)
        L['bell_w'] = sw(KITCHEN_SERVE_X2_F - KITCHEN_SERVE_X1_F)
        L['bell_h'] = sh(KITCHEN_SERVE_Y2_F - KITCHEN_SERVE_Y1_F)

        # ── Left ingredient area – 2 rows × 3 columns (square buttons) ─
        # Right edge is fixed; button size is derived from available height
        # so each button is square, and the left edge is trimmed accordingly.
        lx2    = ix(KITCHEN_LEFT_X2_F)   # right edge stays put
        ly_top = iy(KITCHEN_LEFT_Y1_F)
        ly_bot = iy(KITCHEN_LEFT_Y2_F)
        lh     = ly_top - ly_bot
        pad    = sh(0.010)
        n_cols = 3
        n_rows = 2
        btn_h  = (lh - pad * (n_rows + 1)) / n_rows
        btn_w  = btn_h   # square
        lw_needed = n_cols * btn_w + pad * (n_cols + 1)
        lx1    = lx2 - lw_needed   # left edge shrinks inward
        L['ingr_btn_h'] = btn_h   # shared with right area so sizes match
        L['ingr_btn_w'] = btn_w
        L['ingr_btns'] = {}
        extra_row_gap = sh(0.028)  # extra vertical gap between row 0 and row 1
        extra_col_gap = sh(0.015)  # extra horizontal gap between each column
        for i, ingr in enumerate(_LEFT_INGR):
            if ingr not in self._active_ingr:
                continue   # not used in any recipe this level — skip
            col = i % n_cols
            row = i // n_cols
            if row == 1 and col == 0:
                left_shift = sw(0.022)
            elif row == 1 and col == 1:
                left_shift = sw(0.010)
            else:
                left_shift = 0.0
            ox_f, oy_f = KITCHEN_INGR_OFFSETS.get(ingr, (0.0, 0.0))
            ox = sw(ox_f); oy = sh(oy_f)
            bx  = lx1 + pad + col * (btn_w + pad) + col * extra_col_gap - left_shift + ox
            by  = ly_top - pad - row * (btn_h + pad) - btn_h - (extra_row_gap if row > 0 else 0) + oy
            L['ingr_btns'][ingr] = {
                'x': bx,
                'y': by,
                'w': btn_w,
                'h': btn_h,
            }

        # ── Right stove area – ingredient buttons + pan slots ────
        # Only shown when pan_enabled is True for this level.
        # Layout per row:  [ingredient btn]  [pan slot]
        L['pan_slots'] = {}
        if self._pan_enabled:
            rx_shift = sw(0.17)   # nudge the whole right stove area to the right
            rx1     = ix(KITCHEN_RIGHT_X1_F) + rx_shift
            ry_top  = ly_top   # align with left ingredient area top
            btn_h_r = L['ingr_btn_h']
            btn_w_r = L['ingr_btn_w']
            for i, ingr in enumerate(_RIGHT_INGR):
                ox_f, oy_f = KITCHEN_INGR_OFFSETS.get(ingr, (0.0, 0.0))
                ox = sw(ox_f); oy = sh(oy_f)
                by = ry_top - pad - i * (btn_h_r + pad) - btn_h_r - (extra_row_gap if i > 0 else 0) + oy
                L['ingr_btns'][ingr] = {
                    'x': rx1 + pad + ox,
                    'y': by,
                    'w': btn_w_r,
                    'h': btn_h_r,
                }
                # Pan slot sits immediately to the right of the ingredient button.
                # Keyed by slot index (not ingredient) so either ingredient can go in either pan.
                L['pan_slots'][i] = {
                    'x': rx1 + pad + btn_w_r + pad * 2 + sw(0.04),
                    'y': by,
                    'w': btn_w_r,
                    'h': btn_h_r,
                }

        # ── Sandwich display (centre area) ──────────────────────
        cx1  = ix(KITCHEN_CENTER_X1_F)
        cy_top = iy(KITCHEN_CENTER_Y1_F)
        cy_bot = iy(KITCHEN_CENTER_Y2_F)
        L['sandwich_x'] = cx1 + sw(0.060) - 3
        L['sandwich_y'] = cy_bot + sh(0.000)
        L['sandwich_w'] = sw(KITCHEN_CENTER_X2_F - KITCHEN_CENTER_X1_F) - sw(0.015)
        L['sandwich_h'] = cy_top - cy_bot - sh(0.110)

        # ── Trash chute (below prep area, in the strip between cy_bot and image bottom) ──
        trash_w = sw(0.07)
        trash_h = sh(0.07)
        L['trash_x'] = cx1 + (sw(KITCHEN_CENTER_X2_F - KITCHEN_CENTER_X1_F) - trash_w) / 2 + sw(0.05) + 2
        L['trash_y'] = cy_bot - trash_h - sh(0.07) + 20
        L['trash_w'] = trash_w
        L['trash_h'] = trash_h

        # ── Cat dimensions (scale with image width) ─────────────
        ref_scale = img_w / 1280.0
        L['cat_w'] = KITCHEN_CAT_W_REF * ref_scale
        L['cat_h'] = KITCHEN_CAT_H_REF * ref_scale
        L['cat_y'] = iy(KITCHEN_CAT_Y_F)  # Kivy y of cat centre (kept for compat)
        L['counter_top_y'] = iy(KITCHEN_CAT_PEEK_Y_F)  # Kivy y where cat peek sprite sits

        # ── Contamination zone (where cat contaminates) ─────────
        L['contam_x1'] = ix(KITCHEN_CENTER_X1_F)
        L['contam_x2'] = ix(KITCHEN_CENTER_X2_F)

        # ── HUD positions (inside image bounds, top strip) ──────
        L['hud_timer_x']      = ix(0.74)
        L['hud_timer_y']      = iy(0.04)
        L['hud_score_x']      = ix(0.31)
        L['hud_score_y']      = iy(0.04)
        L['hud_complaints_x'] = ix(0.08)
        L['hud_complaints_y'] = iy(0.04)


        # ── Position ingredient button label overlays ────────────
        if hasattr(self, '_ingr_labels'):
            for ingr, lbl in self._ingr_labels.items():
                zone = L['ingr_btns'].get(ingr)
                if zone:
                    lbl.pos       = (zone['x'], zone['y'])
                    lbl.size      = (zone['w'], zone['h'])
                    lbl.text_size = (zone['w'] - 4, None)
                    lbl.font_size = fsp(18)
                    lbl.opacity   = 1
                else:
                    lbl.opacity   = 0   # hidden when pan not enabled for this level

        # ── Position ticket slot label overlays ──────────────────
        if hasattr(self, '_ticket_labels'):
            slots = L.get('ticket_slots', [])
            for i, lbl in enumerate(self._ticket_labels):
                if i < len(slots):
                    slot = slots[i]
                    tw = slot['w']
                    th = slot['h']
                    # Upper portion of ticket (above colour squares + patience bar)
                    lbl.pos       = (slot['cx'] - tw / 2, slot['y'] + th * 0.58)
                    lbl.size      = (tw, th * 0.38)
                    lbl.text_size = (tw - 4, None)
                    lbl.font_size = fsp(18)

    # ─────────────────────────────────────────────────────────────
    # Game loop
    # ─────────────────────────────────────────────────────────────

    def stop(self):
        if self._clock:
            self._clock.cancel()
            self._clock = None

    def _update(self, dt):
        if self._state == "end_pending":
            self._end_acc += dt
            if self._end_acc >= KITCHEN_END_DELAY:
                self._navigate_to_level_end()
            self._redraw()
            return

        if self._state != "playing":
            return

        # ── Shift timer ─────────────────────────────────────────
        self._shift_timer -= dt
        if not self._alarm_played and 0 < self._shift_timer <= 4.0:
            self._alarm_played = True
            audio_manager.play_tiktok_alarm()
        if self._shift_timer <= 0:
            self._shift_timer = 0.0
            success = self._orders_completed >= self._orders_required
            self._trigger_end(success=success)
            return

        # ── Orders ──────────────────────────────────────────────
        self._update_orders(dt)
        if self._state != "playing":
            return

        # ── Cats ────────────────────────────────────────────────
        if self._cat_enabled:
            self._update_cats(dt)

        # ── Victor serving animation ─────────────────────────────
        if self._victor_phase:
            self._update_victor(dt)

        # ── Rush mode ───────────────────────────────────────────
        if self._rush_mode:
            self._update_rush(dt)

        # ── Pan cooking timers ───────────────────────────────────
        self._update_pans(dt)

        # ── Dish lid animation ───────────────────────────────────
        _LID_SPEED = 12.0   # frames per second
        diff = self._dish_lid_target - self._dish_lid_f
        step = _LID_SPEED * dt
        if abs(diff) <= step:
            self._dish_lid_f = self._dish_lid_target
        else:
            self._dish_lid_f += step if diff > 0 else -step
        self._dish_lid_f = max(0.0, min(3.0, self._dish_lid_f))

        # ── Full-cloche bell animation timer ────────────────────
        if self._plate_dish:
            self._bell_fullcloche_anim_t += dt
        else:
            self._bell_fullcloche_anim_t = 0.0
            self._bell_rang_for_plate = False

        # ── Trash chute animation timer ──────────────────────────
        if self._trash_animating:
            self._trash_anim_t += dt
            if self._trash_anim_t >= 4 / 10.0:   # 4 frames at 10 fps
                self._trash_anim_t    = 0.0
                self._trash_animating = False

        # ── Visual flash timers ─────────────────────────────────
        for attr in ('_serve_flash', '_wrong_flash', '_complaint_flash', '_contamination_flash', '_bell_pressed'):
            v = getattr(self, attr)
            if v > 0:
                setattr(self, attr, max(0.0, v - dt))

        # ── Sync overlay labels with current game state ──────────
        self._update_overlay_labels()

        self._redraw()

    # ── Orders ────────────────────────────────────────────────────

    def _update_orders(self, dt):
        expired = [o for o in self._orders if o['patience'] - dt <= 0]
        for o in expired:
            self._orders.remove(o)
            self._complaints += 1
            self._complaint_flash = 1.2
            if self._complaints >= self._max_complaints:
                self._trigger_end(success=False)
                return

        for o in self._orders:
            o['patience'] -= dt

        # Spawn new orders
        self._order_spawn_acc += dt
        interval = self._order_interval * (0.5 if self._in_rush else 1.0)
        while (self._order_spawn_acc >= interval
               and len(self._orders) < self._max_orders):
            self._order_spawn_acc -= interval
            self._spawn_order()

    def _spawn_order(self):
        recipe   = random.choice(self._recipe_pool)
        patience = KITCHEN_ORDER_PATIENCE_BASE * self._patience_mult
        self._order_id_seq += 1
        self._orders.append({
            'id':           self._order_id_seq,
            'recipe':       tuple(sorted(recipe)),
            'patience':     patience,
            'patience_max': patience,
        })

    # ── Cats ──────────────────────────────────────────────────────

    def _update_cats(self, dt):
        L = self._L
        if not L:
            return

        spawn_interval = KITCHEN_CAT_SPAWN_BASE * self._cat_spawn_mult * (0.6 if self._in_rush else 1.0)
        self._cat_spawn_acc += dt
        if self._cat_spawn_acc >= spawn_interval and len(self._cats) < 1:
            self._cat_spawn_acc = 0.0
            self._spawn_cat()

        fps    = KITCHEN_CAT_PEEK_ANIM_FPS
        pause  = KITCHEN_CAT_PEEK_PAUSE
        np     = max(1, len(self._cat_peek_texes))   # number of peek frames
        ns     = max(1, len(self._cat_steal_texes))  # number of steal frames

        def _next(cat, phase):
            cat['phase']    = phase
            cat['anim_acc'] = 0.0

        done = []
        for cat in self._cats:
            cat['anim_acc'] += dt
            phase = cat['phase']
            acc   = cat['anim_acc']

            # ── peek 1→5 ──────────────────────────────────────────
            if phase == 'peek_up':
                if int(acc * fps) >= np:
                    _next(cat, 'peek_top')

            # ── pause at top ──────────────────────────────────────
            elif phase == 'peek_top':
                if acc >= pause:
                    _next(cat, 'peek_down')

            # ── peek 4→1 ──────────────────────────────────────────
            elif phase == 'peek_down':
                if int(acc * fps) >= (np - 1):   # np-1 reverse steps
                    _next(cat, 'peek_pause')

            # ── pause at bottom ───────────────────────────────────
            elif phase == 'peek_pause':
                if acc >= pause:
                    _next(cat, 'steal_up')

            # ── steal 1→7 ─────────────────────────────────────────
            elif phase == 'steal_up':
                if int(acc * fps) >= ns:
                    self._do_cat_steal(cat['n_steal'])
                    _next(cat, 'steal_down')

            # ── steal 6→1 then gone ───────────────────────────────
            elif phase == 'steal_down':
                if int(acc * fps) >= (ns - 1):
                    done.append(cat)

        for c in done:
            if c in self._cats:
                self._cats.remove(c)

    def _spawn_cat(self):
        L = self._L
        if not L:
            return
        cx1   = L.get('contam_x1', 0)
        cx2   = L.get('contam_x2', 100)
        cat_w = L.get('cat_w', 80) * KITCHEN_CAT_PEEK_SCALE
        x = random.uniform(cx1 + cat_w * 0.5, cx2 - cat_w * 0.5)
        self._cats.append({
            'x':        float(x),
            'phase':    'peek_up',
            'n_steal':  random.randint(1, 2),
            'anim_acc': 0.0,
        })

    def _do_cat_steal(self, n):
        """Remove up to n random non-bread ingredients from the sandwich."""
        stealable = [i for i, ingr in enumerate(self._sandwich) if ingr != 'bread']
        if not stealable:
            return
        n = min(n, len(stealable))
        for idx in sorted(random.sample(stealable, n), reverse=True):
            self._sandwich.pop(idx)
        self._cat_steals_this_run += 1
        audio_manager.play_stealing()

    # ── Victor serving animation ───────────────────────────────────

    def _update_victor(self, dt):
        L = self._L
        if not L:
            return
        img_x  = L['img_x']
        img_w  = L['img_w']
        vw     = KITCHEN_VICTOR_W_REF * (img_w / 1280.0)
        speed  = KITCHEN_VICTOR_SPEED_F * img_w        # px / s
        target_x = img_x + img_w * 0.10

        self._victor_anim_acc += dt

        if self._victor_phase == 'walking_in':
            self._victor_x += speed * dt
            if self._victor_x >= target_x:
                self._victor_x           = target_x
                self._victor_phase       = 'walking_out'
                self._victor_anim_acc    = 0.0
                # Victor picks up the plate — clear it and hide the lid
                self._plate_dish         = []
                self._plate_contaminated = False
                self._dish_lid_f         = 0.0
                self._dish_lid_target    = 0.0
                self._victor_lid_visible = False

        elif self._victor_phase == 'walking_out':
            self._victor_x -= speed * dt
            if self._victor_x + vw < img_x:
                # Victor has fully exited left — restore lid
                self._victor_phase       = None
                self._victor_lid_visible = True
                audio_manager.stop_victor_running()

    # ── Pans ──────────────────────────────────────────────────────

    def _update_pans(self, dt):
        for pan in self._pans.values():
            if pan['ingr'] is not None and not pan['burned']:
                pan['timer'] += dt
                if not pan['ready'] and pan['timer'] >= _PAN_COOK_TIME:
                    pan['ready'] = True
                    audio_manager.play_ding(loud=pan['ingr'] in ('bacon', 'eggs'))
                if pan['ready'] and pan['timer'] >= _PAN_BURN_TIME:
                    pan['burned'] = True
                    audio_manager.play_burnt()
        # Keep frying SFX in sync with pan state
        if any(p['ingr'] is not None and not p['burned'] for p in self._pans.values()):
            audio_manager.start_bacon_frying()
        else:
            audio_manager.stop_bacon_frying()

    # ── Rush mode ─────────────────────────────────────────────────

    def _update_rush(self, dt):
        self._rush_acc += dt
        if self._in_rush:
            if self._rush_acc >= KITCHEN_RUSH_DURATION:
                self._in_rush = False
                self._rush_acc = 0.0
        else:
            if self._rush_acc >= KITCHEN_RUSH_PERIOD:
                self._in_rush = True
                self._rush_acc = 0.0

    # ── Actions ───────────────────────────────────────────────────

    def _try_serve(self):
        """Serve the dish that is currently on the plate."""
        if not self._plate_dish:
            return

        if self._plate_contaminated:
            self._complaints += 1
            self._complaint_flash = 1.2
            self._plate_dish = []
            self._plate_contaminated = False
            if self._complaints >= self._max_complaints:
                self._trigger_end(success=False)
            return

        sandwich_key = tuple(sorted(self._plate_dish))
        # Find oldest matching order
        best = None
        best_consumed = -1.0
        for o in self._orders:
            if o['recipe'] == sandwich_key:
                consumed = o['patience_max'] - o['patience']
                if consumed > best_consumed:
                    best_consumed = consumed
                    best = o

        if best is not None:
            self._orders.remove(best)
            self.score += KITCHEN_SCORE_PER_ORDER
            self._orders_completed += 1
            patience_frac = best['patience'] / best['patience_max']
            self.coins += KITCHEN_COINS_BASE + int(10 * patience_frac)
            self._serve_flash = 0.9
            audio_manager.play_button_wood()
            # Start Victor walk-in (he'll clear the plate when he picks it up)
            L = self._L
            img_x = L.get('img_x', 0) if L else 0
            img_w = L.get('img_w', 1280) if L else 1280
            vw = KITCHEN_VICTOR_W_REF * (img_w / 1280.0)
            self._victor_phase    = 'walking_in'
            self._victor_x        = img_x - vw          # start off-screen left
            self._victor_anim_acc = 0.0
            self._victor_lid_visible = True
            audio_manager.play_victor_running()
        else:
            # No matching order — still clear the plate
            self._wrong_flash = 0.7
            self._plate_dish = []
            self._plate_contaminated = False

    def _trash_sandwich(self):
        """Clear the sandwich assembly area, plate, and any active drag."""
        self._sandwich = []
        self._sandwich_contaminated = False
        self._plate_dish = []
        self._plate_contaminated = False
        self._dragging_dish = False

    def _shoo_cat(self, cat):
        _scareable = ('peek_up', 'peek_top', 'peek_down', 'peek_pause')
        if cat in self._cats and cat['phase'] in _scareable:
            self._cats.remove(cat)

    # ── End game ──────────────────────────────────────────────────

    def _trigger_end(self, success):
        self._state       = "end_pending"
        self._end_success = success
        self._end_acc     = 0.0
        audio_manager.stop_bacon_frying()
        audio_manager.stop_victor_running()
        self._victor_phase = None

    def _fire_kitchen_achievements(self, elapsed_secs):
        """Fire endless-mode achievements. Returns list of newly unlocked keys."""
        if self._level_num != 0:
            return []
        orders  = self._orders_completed
        steals  = self._cat_steals_this_run
        name    = self.player_name
        unlocked = []

        checks = [
            (orders >= 10,        "kitchen_mise_en_place",  75),
            (orders >= 25,        "kitchen_head_chef",      150),
            (orders >= 50,        "kitchen_iron_chef",      300),
            (elapsed_secs >= 300, "kitchen_long_shift",     100),
            (elapsed_secs >= 600, "kitchen_closing_time",   250),
            (steals >= 5,         "kitchen_mittens_buffet",  50),
        ]
        for condition, key, coins in checks:
            if condition and unlock_achievement(name, key, coins):
                unlocked.append(key)
        return unlocked

    def _navigate_to_level_end(self):
        parent = self.parent
        if parent and hasattr(parent, 'manager'):
            elapsed  = (float(self._level_cfg.get("duration_secs", 120))
                        - self._shift_timer)
            new_keys = self._fire_kitchen_achievements(elapsed)
            end = parent.manager.get_screen("kitchen_level_end")
            end.level_num                  = self._level_num
            end.score                      = self.score
            end.success                    = self._end_success
            end.elapsed_secs               = elapsed
            end.pending_achievement_toasts = new_keys
            parent.manager.current = "kitchen_level_end"

    # ─────────────────────────────────────────────────────────────
    # Overlay label sync
    # ─────────────────────────────────────────────────────────────

    def _update_overlay_labels(self):
        """Sync text/color/opacity of child Label widgets with live game state."""
        # Ticket recipe labels
        for i, lbl in enumerate(self._ticket_labels):
            if i < len(self._orders):
                order = self._orders[i]
                lbl.text = recipe_display_name(order['recipe'])
                patience_frac = order['patience'] / order['patience_max']
                if patience_frac < _PATIENCE_RED:
                    lbl.color = (1.0, 0.96, 0.90, 1.0)
                else:
                    lbl.color = (0.15, 0.08, 0.02, 1.0)
                lbl.opacity = 1
            else:
                lbl.text    = ""
                lbl.opacity = 0

    # ─────────────────────────────────────────────────────────────
    # Rendering
    # ─────────────────────────────────────────────────────────────

    def _redraw(self):
        W, H = self.width, self.height
        if W < 2 or H < 2:
            return
        if not self._L or 'img_x' not in self._L:
            self._compute_layout()
        L = self._L
        if not L or 'img_x' not in L:
            return

        ix   = L['ix'];   iy   = L['iy']
        sw   = L['sw'];   sh   = L['sh']
        img_x = L['img_x']; img_y = L['img_y']
        img_w = L['img_w']; img_h = L['img_h']

        self.canvas.clear()
        with self.canvas:
            # ── Letterbox fill ──────────────────────────────────
            Color(*COLOR_BG)
            Rectangle(pos=(self.x, self.y), size=(W, H))

            # ── Kitchen background ──────────────────────────────
            if self._bg_tex:
                Color(1, 1, 1, 1)
                if img_h > H:
                    # Narrow screen: crop top/bottom symmetrically so nothing renders
                    # outside the screen bounds (avoids GPU clipping precision loss).
                    # Uses the same V-flip convention as bar_duty (v=1 at screen bottom).
                    crop_v = (img_h - H) / (2 * img_h)
                    Rectangle(texture=self._bg_tex,
                              pos=(img_x, self.y),
                              size=(img_w, H),
                              tex_coords=(0.0, 1.0 - crop_v, 1.0, 1.0 - crop_v,
                                          1.0, crop_v, 0.0, crop_v))
                else:
                    Rectangle(texture=self._bg_tex,
                              pos=(img_x, img_y),
                              size=(img_w, img_h))

            # ── Pans overlay (art covers both pan slots in stove area) ─
            if self._pans_tex and self._pan_enabled:
                px = ix(KITCHEN_PANS_X_F)
                py = iy(KITCHEN_PANS_Y_F + KITCHEN_PANS_H_F)
                pw = sw(KITCHEN_PANS_W_F)
                ph = sh(KITCHEN_PANS_H_F)
                Color(1, 1, 1, 1)
                Rectangle(texture=self._pans_tex, pos=(px, py), size=(pw, ph))

            # ── Order tickets ───────────────────────────────────
            self._draw_tickets(L)

            # ── Cats on counter ─────────────────────────────────
            if self._cat_enabled:
                self._draw_cats(L)

            # ── Sandwich display (hidden while dragging to plate) ──
            if not self._dragging_dish:
                self._draw_sandwich(L)

            # ── Ingredient buttons ──────────────────────────────
            self._draw_ingredient_buttons(L)

            # ── Victor serving animation (behind dish) ───────────
            if self._victor_phase:
                self._draw_victor(L)

            # ── Plate drop zone (in front of Victor) ─────────────
            self._draw_plate(L)

            # ── Pans (cooking station) ──────────────────────────
            self._draw_pans(L)

            # ── Bell (serving station) ──────────────────────────
            self._draw_bell(L)

            # ── Drag dish visual (follows finger) ───────────────
            if self._dragging_dish:
                self._draw_drag_dish(L)

            # ── Drag ingredient visual (follows finger) ──────────
            if self._dragging_ingr:
                self._draw_drag_ingr(L)

            # ── Drag pan ingredient visual (follows finger) ──────
            if self._dragging_pan_ingr:
                self._draw_drag_pan_ingr(L)

            # ── Trash button ────────────────────────────────────
            self._draw_trash(L)

            # ── HUD ─────────────────────────────────────────────
            self._draw_hud(L, W, H)

            # ── Visual flash overlays ───────────────────────────
            self._draw_flashes(L, W, H)

            # End screen overlay removed – level-end screen handles this

    # ── Draw helpers ──────────────────────────────────────────────

    def _draw_tickets(self, L):
        slots = L.get('ticket_slots', [])
        if not slots:
            return
        ix = L['ix']; sw = L['sw']; sh = L['sh']

        # Draw order tickets for active orders (fill slots from left)
        for i, order in enumerate(self._orders[:len(slots)]):
            slot = slots[i]
            cx, ty, tw, th = slot['cx'], slot['y'], slot['w'], slot['h']
            tx = cx - tw / 2

            # Ticket paper background
            patience_frac = order['patience'] / order['patience_max']
            ticket_tex = (self._recipe_ticket_texes.get(order['recipe'])
                          or self._order_ticket_tex)

            if ticket_tex:
                Color(1, 1, 1, 1)
                Rectangle(texture=ticket_tex, pos=(tx, ty), size=(tw, th))
            else:
                Color(0.90, 0.84, 0.64, 0.92)
                RoundedRectangle(pos=(tx, ty), size=(tw, th), radius=[4])
                Color(0.50, 0.38, 0.15, 1.0)
                RoundedRectangle(pos=(tx - 1, ty - 1), size=(tw + 2, th + 2), radius=[5])
                Color(0.90, 0.84, 0.64, 0.92)
                RoundedRectangle(pos=(tx, ty), size=(tw, th), radius=[4])

            # Patience bar — vertical strip on the left edge of the ticket
            bar_w   = tw * 0.13
            bar_x   = tx + sw(0.010)
            bar_top = ty + sh(0.012) + th * 0.75   # fixed top
            bar_y   = ty + sh(0.040)               # raised bottom
            bar_h   = bar_top - bar_y
            # background
            Color(0.25, 0.10, 0.05, 0.80)
            RoundedRectangle(pos=(bar_x, bar_y), size=(bar_w, bar_h), radius=[2])
            # fill — grows upward from bottom
            if patience_frac < _PATIENCE_RED:
                fill_col = (0.90, 0.15, 0.10, 1.0)
            elif patience_frac < _PATIENCE_ORANGE:
                fill_col = (0.95, 0.60, 0.05, 1.0)
            else:
                fill_col = (0.20, 0.75, 0.20, 1.0)
            fill_h = bar_h * patience_frac
            Color(*fill_col)
            if fill_h > 1:
                RoundedRectangle(pos=(bar_x, bar_y), size=(bar_w, fill_h), radius=[2])


    def _draw_cats(self, L):
        cat_w_base  = L['cat_w']
        cat_h_base  = L['cat_h']
        counter_top = L.get('counter_top_y', L['cat_y'])

        # Scale up the peek sprite relative to the base cat size
        cat_w  = cat_w_base * KITCHEN_CAT_PEEK_SCALE
        peek_h = cat_h_base * 0.70 * KITCHEN_CAT_PEEK_SCALE

        peek_texes  = self._cat_peek_texes
        steal_texes = self._cat_steal_texes

        fps = KITCHEN_CAT_PEEK_ANIM_FPS
        np  = max(1, len(peek_texes))
        ns  = max(1, len(steal_texes))

        for cat in self._cats:
            phase = cat['phase']
            acc   = cat['anim_acc']
            x     = cat['x'] - cat_w / 2

            # ── Pick texture set and frame index ──────────────────
            if phase == 'peek_up':
                texes = peek_texes
                frame = min(int(acc * fps), np - 1)

            elif phase == 'peek_top':
                texes = peek_texes
                frame = np - 1                          # hold last peek frame

            elif phase == 'peek_down':
                texes = peek_texes
                # reverse: np-2 → np-3 → … → 0
                frame = max(0, (np - 2) - int(acc * fps))

            elif phase == 'peek_pause':
                texes = peek_texes
                frame = 0                               # hold first peek frame

            elif phase == 'steal_up':
                texes = steal_texes if steal_texes else peek_texes
                frame = min(int(acc * fps), (ns if steal_texes else np) - 1)

            elif phase == 'steal_down':
                texes = steal_texes if steal_texes else peek_texes
                n     = ns if steal_texes else np
                # reverse: n-2 → n-3 → … → 0
                frame = max(0, (n - 2) - int(acc * fps))

            else:
                continue   # unknown phase, skip

            if texes:
                Color(1, 1, 1, 1)
                Rectangle(texture=texes[frame], pos=(x, counter_top), size=(cat_w, peek_h))
            else:
                # ── Placeholder: head + ears + eyes + paws ───────
                head_y = counter_top + peek_h * 0.22
                head_h = peek_h * 0.78
                Color(1.0, 0.60, 0.10, 0.95)
                RoundedRectangle(pos=(x, head_y), size=(cat_w, head_h),
                                 radius=[cat_w * 0.35])
                ear_w = cat_w * 0.20
                ear_h = peek_h * 0.28
                Rectangle(pos=(x + cat_w * 0.10, head_y + head_h * 0.76),
                          size=(ear_w, ear_h))
                Rectangle(pos=(x + cat_w * 0.70, head_y + head_h * 0.76),
                          size=(ear_w, ear_h))
                eye_r = cat_w * 0.09
                Color(0.10, 0.55, 0.10, 1.0)
                Ellipse(pos=(x + cat_w * 0.22 - eye_r, head_y + head_h * 0.44),
                        size=(eye_r * 2, eye_r * 2))
                Ellipse(pos=(x + cat_w * 0.68 - eye_r, head_y + head_h * 0.44),
                        size=(eye_r * 2, eye_r * 2))
                paw_w = cat_w * 0.32
                paw_h = peek_h * 0.18
                Color(1.0, 0.55, 0.08, 1.0)
                RoundedRectangle(pos=(x + cat_w * 0.04, counter_top),
                                 size=(paw_w, paw_h), radius=[4])
                RoundedRectangle(pos=(x + cat_w * 0.64, counter_top),
                                 size=(paw_w, paw_h), radius=[4])

            if DEBUG_HITBOXES:
                Color(1, 0, 0, 0.35)
                Rectangle(pos=(x, counter_top), size=(cat_w, peek_h))

    def _draw_victor(self, L):
        img_x  = L['img_x']
        img_w  = L['img_w']
        img_h  = L['img_h']
        iy     = L['iy']

        vw = KITCHEN_VICTOR_W_REF * (img_w / 1280.0)
        vh = KITCHEN_VICTOR_H_REF * (img_h / 1773.0)
        vx = self._victor_x
        vy = iy(KITCHEN_VICTOR_Y_F)   # Kivy y = bottom edge of sprite

        walk_texes = self._victor_walk_texes
        n_walk     = len(walk_texes)

        if self._victor_phase == 'walking_in':
            if walk_texes:
                frame = int(self._victor_anim_acc * KITCHEN_VICTOR_WALK_FPS) % n_walk
                tex = walk_texes[frame]
            else:
                tex = self._victor_noplate_tex
            if tex:
                Color(1, 1, 1, 1)
                Rectangle(texture=tex, pos=(vx, vy), size=(vw, vh))

        elif self._victor_phase == 'walking_out':
            tex = self._victor_plate_tex
            if tex:
                Color(1, 1, 1, 1)
                # Upside-down AND mirrored (faces left) when walking out
                Rectangle(texture=tex, pos=(vx, vy), size=(vw, vh),
                          tex_coords=(1, 1, 0, 1, 0, 0, 1, 0))

    def _get_combo_tex(self, ingredients):
        """Return the prepare texture for this ingredient combination, or None if no art exists.
        Files are named: sorted-ingredients joined by '_' + '_prepare.png'
        e.g. ['bread','cheese'] → bread_cheese_prepare.png
        """
        key = frozenset(ingredients)
        if key in self._combo_tex_cache:
            return self._combo_tex_cache[key]
        filename = "_".join(sorted(ingredients)) + "_prepare.png"
        path = os.path.join(_ASSETS, "food", filename)
        try:
            from kivy.core.image import Image as CoreImage
            tex = CoreImage(path).texture
        except Exception:
            tex = None
        self._combo_tex_cache[key] = tex
        return tex

    def _get_plate_tex(self, ingredients):
        """Return the plate texture for this ingredient combination, or None.
        Files are named: sorted ingredients joined by '_' + '_plate.png'
        e.g. ['bread','cheese'] → bread_cheese_plate.png
        """
        key = frozenset(ingredients)
        if key in self._plate_tex_cache:
            return self._plate_tex_cache[key]
        filename = "_".join(sorted(ingredients)) + "_plate.png"
        path = os.path.join(_ASSETS, "food", filename)
        try:
            tex = CoreImage(path).texture
        except Exception:
            tex = None
        self._plate_tex_cache[key] = tex
        return tex

    def _draw_sandwich(self, L):
        sx = L['sandwich_x']
        sy = L['sandwich_y']
        sw_v = L['sandwich_w']
        sh_v = L['sandwich_h']

        if not self._sandwich:
            return

        # Draw the single combo image for the current ingredient set
        tex = self._get_combo_tex(self._sandwich)
        if tex:
            img_scale_h = 1.40   # ← increase to make prepare image taller
            draw_h = sh_v * img_scale_h
            Color(1, 1, 1, 1)
            Rectangle(texture=tex, pos=(sx, sy), size=(sw_v, draw_h))

        # Contamination "!" badge
        if self._sandwich_contaminated:
            bx = sx + sw_v - sw_v * 0.20
            by = sy + sh_v * 0.60
            bs = min(sw_v * 0.20, sh_v * 0.25)
            Color(0.85, 0.08, 0.08, 1.0)
            Ellipse(pos=(bx - bs / 2, by - bs / 2), size=(bs, bs))
            Color(1, 1, 1, 1)
            # "!" drawn as two rectangles (no font needed)
            dot_w = bs * 0.20
            Color(1, 1, 1, 1)
            Rectangle(pos=(bx - dot_w / 2, by + bs * 0.12),
                      size=(dot_w, bs * 0.40))
            Rectangle(pos=(bx - dot_w / 2, by - bs * 0.30),
                      size=(dot_w, dot_w))

    def _draw_ingredient_buttons(self, L):
        btns = L.get('ingr_btns', {})
        if not btns:
            return

        for ingr, zone in btns.items():
            bx, by, bw, bh = zone['x'], zone['y'], zone['w'], zone['h']
            being_dragged = (self._dragging_ingr == ingr)
            tex = self._ingr_tray_texes.get(ingr)
            if tex:
                # Draw tray image; slightly faded while being dragged
                sx_s, sy_s = KITCHEN_INGR_SCALES.get(ingr, (1.0, 1.0))
                sw_s  = bw * sx_s
                sh_s  = bh * sy_s
                sx    = bx + (bw - sw_s) / 2
                sy    = by + (bh - sh_s) / 2
                Color(1, 1, 1, 0.55 if being_dragged else 1.0)
                Rectangle(texture=tex, pos=(sx, sy), size=(sw_s, sh_s))
            else:
                # Fallback: coloured box
                base_col = KITCHEN_INGREDIENT_COLORS.get(ingr, (0.60, 0.60, 0.60, 1.0))
                r, g, b, a = base_col
                if being_dragged:
                    col = (r * 0.55, g * 0.55, b * 0.55, 0.70)
                else:
                    col = (r * 0.85, g * 0.85, b * 0.85, 0.92)
                Color(*col)
                RoundedRectangle(pos=(bx, by), size=(bw, bh), radius=[5])
                Color(min(1, r * 1.5), min(1, g * 1.5), min(1, b * 1.5), 0.80)
                Line(rounded_rectangle=(bx, by, bw, bh, 5), width=1.2)

            if DEBUG_HITBOXES:
                Color(0, 0.8, 1, 0.35)
                Rectangle(pos=(bx, by), size=(bw, bh))

    def _draw_plate(self, L):
        px = L.get('plate_x', 0); py = L.get('plate_y', 0)
        pw = L.get('plate_w', 0); ph = L.get('plate_h', 0)
        if pw < 2 or ph < 2:
            return

        # ── Dish bottom ──────────────────────────────────────────
        # When a dish is sitting on the plate, show the matching *_plate.png
        # so the player can see there's already a sandwich waiting.
        Color(1, 1, 1, 1)
        bottom_tex = self._dish_bottom_tex
        if self._plate_dish:
            combo_plate = self._get_plate_tex(self._plate_dish)
            if combo_plate:
                bottom_tex = combo_plate
        if bottom_tex:
            Rectangle(texture=bottom_tex,
                      pos=(px, py), size=(pw, ph))
        else:
            # Fallback: cream ellipse base
            cx = px + pw / 2
            cy = py + ph * 0.28
            r  = min(pw, ph) * 0.40
            Color(0.92, 0.90, 0.84, 1.0)
            Ellipse(pos=(cx - r, cy - r * 0.45), size=(r * 2, r * 0.90))

        # ── Contamination tint on base ───────────────────────────
        if self._plate_contaminated and self._plate_dish:
            Color(0.80, 0.10, 0.10, 0.35)
            Rectangle(pos=(px, py), size=(pw, ph))

        # ── Dish lid (animated) — hidden while Victor carries the plate ──
        if self._victor_lid_visible:
            frame_idx = min(int(self._dish_lid_f + 0.5), 3)   # round to nearest frame
            lid_tex = self._dish_top_texes[frame_idx] if self._dish_top_texes else None
            Color(1, 1, 1, 1)
            if lid_tex:
                Rectangle(texture=lid_tex, pos=(px, py), size=(pw, ph))
            else:
                # Fallback: grey dome
                cx = px + pw / 2
                cy = py + ph * 0.55
                r  = min(pw * 0.45, ph * 0.50)
                lift = ph * 0.08 * (self._dish_lid_f / 3.0)  # rises as it opens
                Color(0.70, 0.68, 0.62, 0.95)
                Ellipse(pos=(cx - r, cy - r * 0.55 + lift), size=(r * 2, r * 1.10))

        if DEBUG_HITBOXES:
            Color(0, 1, 0, 0.35)
            Rectangle(pos=(px, py), size=(pw, ph))

    def _draw_drag_dish(self, L):
        if not self._sandwich:
            return
        dx, dy = self._drag_x, self._drag_y
        dw = min(L.get('sandwich_w', 80) * 0.90, 160.0)
        tex = self._get_combo_tex(self._sandwich)
        if tex:
            alpha = 0.75 if self._sandwich_contaminated else 1.0
            Color(1, 1, 1, alpha)
            Rectangle(texture=tex, pos=(dx - dw / 2, dy - dw / 2), size=(dw, dw))
            if self._sandwich_contaminated:
                Color(0.80, 0.10, 0.10, 0.35)
                Rectangle(pos=(dx - dw / 2, dy - dw / 2), size=(dw, dw))
        else:
            # Fallback: coloured slabs
            n      = len(self._sandwich)
            slab_h = dw / max(n, 1)
            slab_x = dx - dw / 2
            base_y = dy - (n * slab_h) / 2
            for i, ingr in enumerate(self._sandwich):
                col = KITCHEN_INGREDIENT_COLORS.get(ingr, (0.7, 0.7, 0.7, 1.0))
                Color(*col)
                RoundedRectangle(pos=(slab_x, base_y + i * slab_h),
                                 size=(dw, slab_h * 0.86), radius=[3])
            if self._sandwich_contaminated:
                Color(0.80, 0.10, 0.10, 0.45)
                RoundedRectangle(pos=(slab_x, base_y), size=(dw, n * slab_h), radius=[3])

    def _draw_drag_pan_ingr(self, L):
        """Ghost image of cooked ingredient being dragged from pan to sandwich."""
        ingr = self._dragging_pan_ingr
        if not ingr:
            return
        dx, dy = self._pan_drag_x, self._pan_drag_y
        size = L.get('ingr_btn_w', 60) * 0.80
        ingr_art = self._pan_ingr_texes.get(ingr, {})
        tex = ingr_art.get('cooked_float') or ingr_art.get('cooked')
        if tex:
            Color(1, 1, 1, 0.90)
            Rectangle(texture=tex, pos=(dx - size / 2, dy - size / 2), size=(size, size))
        else:
            col = KITCHEN_INGREDIENT_COLORS.get(ingr, (0.7, 0.7, 0.7, 1.0))
            Color(col[0], col[1], col[2], 0.90)
            RoundedRectangle(pos=(dx - size / 2, dy - size / 2), size=(size, size), radius=[5])

    def _draw_drag_ingr(self, L):
        """Ghost image of ingredient being dragged from tray to prep area."""
        ingr = self._dragging_ingr
        if not ingr:
            return
        dx, dy = self._ingr_drag_x, self._ingr_drag_y
        btn_w = L.get('ingr_btn_w', 60)
        size  = btn_w * 0.80 * _DRAG_FLOAT_SCALES.get(ingr, 1.0)
        bx    = dx - size / 2
        by    = dy - size / 2
        tex   = self._ingr_float_texes.get(ingr) or self._ingr_tray_texes.get(ingr)
        if tex:
            Color(1, 1, 1, 0.90)
            Rectangle(texture=tex, pos=(bx, by), size=(size, size))
        else:
            col = KITCHEN_INGREDIENT_COLORS.get(ingr, (0.7, 0.7, 0.7, 1.0))
            Color(col[0], col[1], col[2], 0.90)
            RoundedRectangle(pos=(bx, by), size=(size, size), radius=[5])

    def _draw_pans(self, L):
        slots = L.get('pan_slots', {})
        if not slots:
            return

        for slot_key, zone in slots.items():
            bx, by, bw, bh = zone['x'], zone['y'], zone['w'], zone['h']
            pan    = self._pans.get(slot_key, {})
            ingr   = pan.get('ingr')
            has    = ingr is not None
            ready  = pan.get('ready', False)
            burned = pan.get('burned', False)
            frac   = min(pan.get('timer', 0.0) / _PAN_COOK_TIME, 1.0) if has else 0.0

            # Cooking surface
            ingr_art = self._pan_ingr_texes.get(ingr, {}) if ingr else {}
            cx = bx + bw / 2
            cy = by + bh * 0.50
            r  = min(bw, bh) * 0.34

            # Scale / offset for this ingredient's art within the slot.
            # off_top/off_bottom crop pixels from the top/bottom of the slot.
            isx        = _PAN_INGR_SCALES.get(ingr, (1.0, 1.0))[0]
            iox        = _PAN_SLOT_OFFSET_X.get((slot_key, ingr), _PAN_INGR_OFFSET_X.get(ingr, 0))
            off_top    = _PAN_SLOT_OFFSET_TOP.get((slot_key, ingr), _PAN_INGR_OFFSET_TOP.get(ingr, 0))
            off_bottom = _PAN_SLOT_OFFSET_BOTTOM.get((slot_key, ingr), _PAN_INGR_OFFSET_BOTTOM.get(ingr, 0))
            art_w  = bw * isx
            art_h  = bh - off_top - off_bottom
            art_x  = bx + (bw - art_w) / 2 + iox
            art_y  = by + off_bottom

            if burned:
                tex = ingr_art.get('burnt')
                if tex:
                    Color(1, 1, 1, 1)
                    Rectangle(texture=tex, pos=(art_x, art_y), size=(art_w, art_h))
                else:
                    Color(0.10, 0.08, 0.06, 0.95)
                    Ellipse(pos=(cx - r, cy - r), size=(r * 2, r * 2))
                    Color(0.85, 0.10, 0.05, 0.90)
                    Line(circle=(cx, cy, r * 1.18), width=2.2)
            elif ready:
                tex = ingr_art.get('cooked')
                if tex:
                    Color(1, 1, 1, 1)
                    Rectangle(texture=tex, pos=(art_x, art_y), size=(art_w, art_h))
                else:
                    col = KITCHEN_INGREDIENT_COLORS.get(ingr, (0.7, 0.7, 0.7, 1.0))
                    Color(*col)
                    Ellipse(pos=(cx - r, cy - r), size=(r * 2, r * 2))
                    Color(1.0, 0.88, 0.18, 0.75)
                    Line(circle=(cx, cy, r * 1.18), width=2.2)
            elif has:
                tex = ingr_art.get('raw')
                if tex:
                    Color(1, 1, 1, 1)
                    Rectangle(texture=tex, pos=(art_x, art_y), size=(art_w, art_h))
                else:
                    Color(0.50, 0.28, 0.06, 0.85)
                    Ellipse(pos=(cx - r, cy - r), size=(r * 2, r * 2))
                    Color(0.95, 0.58, 0.08, 0.95)
                    Line(circle=(cx, cy, r * 1.18, 0, 360 * frac), width=2.2)
            else:
                # Empty pan — nothing drawn (kitchen background shows through)
                pass

            if DEBUG_HITBOXES:
                Color(0, 0.5, 1, 0.35)
                Rectangle(pos=(bx, by), size=(bw, bh))

    def _draw_bell(self, L):
        bx = L['bell_x']
        by = L['bell_y']
        bw = L['bell_w']
        bh = L['bell_h']
        if self._plate_dish and not self._bell_rang_for_plate and self._bell_fullcloche_texes:
            _FPS = 6.0   # animation speed (frames per second)
            frame_idx = int(self._bell_fullcloche_anim_t * _FPS) % 4
            tex = self._bell_fullcloche_texes[frame_idx]
        else:
            tex = self._bell_down_tex if self._bell_pressed > 0 else self._bell_tex
        if tex:
            Color(1, 1, 1, 1)
            Rectangle(texture=tex, pos=(bx, by), size=(bw, bh))
        else:
            # Fallback: drawn bell
            cx = bx + bw / 2
            cy = by + bh * 0.55
            r  = min(bw, bh) * 0.25
            Color(0.95, 0.75, 0.10, 1)
            Ellipse(pos=(cx - r, cy - r), size=(r * 2, r * 2))
            Color(0.80, 0.60, 0.10, 1)
            Line(circle=(cx, cy, r * 1.3, 0, 180), width=max(1.2, r * 0.14))

        if DEBUG_HITBOXES:
            Color(1, 0.5, 0, 0.35)
            Rectangle(pos=(bx, by), size=(bw, bh))

    def _draw_trash(self, L):
        tx = L['trash_x']
        ty = L['trash_y']
        tw = L['trash_w']
        th = L['trash_h']

        if self._trash_texes:
            _TRASH_FPS = 10.0
            if self._trash_animating:
                frame_idx = min(int(self._trash_anim_t * _TRASH_FPS), 3)
            else:
                frame_idx = 0
            tex = self._trash_texes[frame_idx]
            if tex:
                Color(1, 1, 1, 1)
                Rectangle(texture=tex, pos=(tx, ty), size=(tw, th))
        else:
            # Fallback: drawn trash button
            Color(0.50, 0.15, 0.10, 0.85)
            RoundedRectangle(pos=(tx, ty), size=(tw, th), radius=[5])
            margin = tw * 0.22
            Color(1.0, 0.85, 0.70, 1.0)
            Line(points=[tx + margin, ty + margin, tx + tw - margin, ty + th - margin], width=1.8)
            Line(points=[tx + tw - margin, ty + margin, tx + margin, ty + th - margin], width=1.8)

        if DEBUG_HITBOXES:
            Color(1, 0, 1, 0.35)
            Rectangle(pos=(tx, ty), size=(tw, th))

    def _draw_hud(self, L, W, H):
        # Build text strings
        mins   = int(self._shift_timer) // 60
        secs   = int(self._shift_timer) % 60
        timer_str  = f"{mins}:{secs:02d}"
        score_str  = f"SCORE: {self.score}"
        comp_str   = f"COMPLAINTS: {self._complaints}/{self._max_complaints}"

        rush_str   = "RUSH!" if self._in_rush else ""

        ix = L['ix']; iy = L['iy']; sw = L['sw']; sh = L['sh']

        # Small dark panels per HUD element
        hud_items = [
            (L['hud_timer_x'],      L['hud_timer_y'],      timer_str,  (0.95, 0.90, 0.40, 1.0)),
            (L['hud_score_x'],      L['hud_score_y'],      score_str,  (0.80, 0.95, 0.55, 1.0)),
            (L['hud_complaints_x'], L['hud_complaints_y'], comp_str,   (0.95, 0.55, 0.40, 1.0)),
        ]
        if rush_str:
            hud_items.append((ix(0.55), iy(0.04), rush_str, (1.0, 0.30, 0.10, 1.0)))

        for hx, hy, text, col in hud_items:
            Color(*col)
            # Draw each character as a thin rectangle band (pixel-font fallback via Label)
            # We rely on Kivy Labels added as child widgets for text – but since we can't
            # add Labels inside a canvas block, we use the external label overlay approach.

        # Render HUD via overlaid Label children added once in on_enter
        # (updated via self._hud_* references – see KitchenGameScreen.on_enter)

    def _draw_flashes(self, L, W, H):
        img_x = L['img_x']; img_y = L['img_y']
        img_w = L['img_w']; img_h = L['img_h']

        if self._serve_flash > 0:
            alpha = self._serve_flash * 0.45
            Color(0.20, 0.90, 0.30, alpha)
            Rectangle(pos=(img_x, img_y), size=(img_w, img_h))

        if self._wrong_flash > 0:
            alpha = self._wrong_flash * 0.40
            Color(0.90, 0.90, 0.10, alpha)
            Rectangle(pos=(img_x, img_y), size=(img_w, img_h))

        if self._complaint_flash > 0:
            alpha = self._complaint_flash * 0.50
            Color(0.90, 0.10, 0.10, alpha)
            Rectangle(pos=(img_x, img_y), size=(img_w, img_h))

        if self._contamination_flash > 0:
            alpha = min(self._contamination_flash, 1.0) * 0.35
            Color(0.50, 0.30, 0.05, alpha)
            Rectangle(pos=(img_x, img_y), size=(img_w, img_h))

    def _draw_end_overlay(self, W, H):
        # Semi-transparent blackout with status text rendered via Label widget
        Color(0.0, 0.0, 0.0, 0.70)
        Rectangle(pos=(self.x, self.y), size=(W, H))

    # ─────────────────────────────────────────────────────────────
    # Touch input
    # ─────────────────────────────────────────────────────────────

    def on_touch_down(self, touch):
        if self._state != "playing":
            return True
        if not self.collide_point(*touch.pos):
            return False

        L = self._L
        if not L:
            return True

        tx, ty = touch.pos
        touch.grab(self)

        # Priority 1: Shoo a peeking cat
        cat_w       = L.get('cat_w', 80)  * KITCHEN_CAT_PEEK_SCALE
        cat_h       = L.get('cat_h', 120)
        counter_top = L.get('counter_top_y', L.get('cat_y', 0))
        peek_h      = cat_h * 0.70 * KITCHEN_CAT_PEEK_SCALE
        _scareable = ('peek_up', 'peek_top', 'peek_down', 'peek_pause')
        for cat in list(self._cats):
            if cat['phase'] not in _scareable:
                continue
            cx = cat['x'] - cat_w / 2
            if cx <= tx <= cx + cat_w and counter_top <= ty <= counter_top + peek_h:
                self._shoo_cat(cat)
                return True

        # Priority 2: Start dragging sandwich to plate
        if self._sandwich and not self._dragging_dish:
            sx = L['sandwich_x']; sy = L['sandwich_y']
            sw_v = L['sandwich_w']; sh_v = L['sandwich_h']
            if sx <= tx <= sx + sw_v and sy <= ty <= sy + sh_v:
                self._dragging_dish = True
                self._drag_x, self._drag_y = tx, ty
                return True

        # Priority 3: Bell / serve (only active when a dish is on the plate)
        bx = L['bell_x']; by = L['bell_y']
        bw = L['bell_w']; bh = L['bell_h']
        if bx <= tx <= bx + bw and by <= ty <= by + bh:
            self._bell_pressed = 0.18
            audio_manager.play_typewriter_bell()
            if self._plate_dish:
                self._bell_rang_for_plate = True
                self._try_serve()
            return True

        # Priority 4: Trash (clears sandwich, plate, and any active drag)
        ttx = L['trash_x']; tty = L['trash_y']
        ttw = L['trash_w']; tth = L['trash_h']
        if ttx <= tx <= ttx + ttw and tty <= ty <= tty + tth:
            if self._sandwich:
                self._sandwich            = []
                self._sandwich_contaminated = False
                self._dragging_ingr       = None
                self._trash_animating     = True
                self._trash_anim_t        = 0.0
                audio_manager.play_trash()
            return True

        # Priority 5: Ingredient buttons
        for ingr, zone in L.get('ingr_btns', {}).items():
            zx, zy, zw, zh = zone['x'], zone['y'], zone['w'], zone['h']
            if zx <= tx <= zx + zw and zy <= ty <= zy + zh:
                self._dragging_ingr = ingr
                self._ingr_drag_x   = tx
                self._ingr_drag_y   = ty
                touch.grab(self)
                return True

        # Priority 6: Pan slots — burned: tap to discard; ready: drag to sandwich
        for slot_key, zone in L.get('pan_slots', {}).items():
            zx, zy, zw, zh = zone['x'], zone['y'], zone['w'], zone['h']
            if zx <= tx <= zx + zw and zy <= ty <= zy + zh:
                pan = self._pans.get(slot_key)
                if pan and pan.get('burned'):
                    # Tap burned pan to discard and reset
                    pan['ingr']   = None
                    pan['timer']  = 0.0
                    pan['ready']  = False
                    pan['burned'] = False
                    self._wrong_flash = 0.5
                elif pan and pan.get('ready'):
                    # Drag cooked ingredient to sandwich area
                    self._dragging_pan_ingr = pan['ingr']
                    self._dragging_pan_slot = slot_key
                    self._pan_drag_x = tx
                    self._pan_drag_y = ty
                    touch.grab(self)
                return True

        return True

    def on_touch_move(self, touch):
        if touch.grab_current is self:
            if self._dragging_dish:
                self._drag_x, self._drag_y = touch.pos
                # Open lid when hovering over the plate zone, close it otherwise
                L = self._L
                if L:
                    px = L.get('plate_x', 0); py = L.get('plate_y', 0)
                    pw = L.get('plate_w', 0); ph = L.get('plate_h', 0)
                    tx, ty = touch.pos
                    self._dish_lid_target = 3.0 if (px <= tx <= px + pw and py <= ty <= py + ph) else 0.0
                return True
            if self._dragging_ingr:
                self._ingr_drag_x, self._ingr_drag_y = touch.pos
                return True
            if self._dragging_pan_ingr:
                self._pan_drag_x, self._pan_drag_y = touch.pos
                return True
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        if touch.grab_current is self:
            touch.ungrab(self)

        if self._dragging_dish:
            self._dragging_dish = False
            self._dish_lid_target = 0.0   # close lid whether dropped on plate or not
            L = self._L
            if L and self._sandwich:
                px = L.get('plate_x', 0); py = L.get('plate_y', 0)
                pw = L.get('plate_w', 0); ph = L.get('plate_h', 0)
                tx, ty = touch.pos
                if px <= tx <= px + pw and py <= ty <= py + ph:
                    # Drop dish onto plate
                    self._plate_dish = list(self._sandwich)
                    self._plate_contaminated = self._sandwich_contaminated
                    self._sandwich = []
                    self._sandwich_contaminated = False
                    audio_manager.play_cloche()

        if self._dragging_ingr:
            ingr = self._dragging_ingr
            self._dragging_ingr = None
            L = self._L
            if L:
                tx, ty = touch.pos
                if ingr in _RIGHT_INGR:
                    # Right-area ingredient: drop onto any empty pan slot
                    for slot_key, pan_zone in L.get('pan_slots', {}).items():
                        zx, zy, zw, zh = pan_zone['x'], pan_zone['y'], pan_zone['w'], pan_zone['h']
                        if zx <= tx <= zx + zw and zy <= ty <= zy + zh:
                            pan = self._pans[slot_key]
                            if pan['ingr'] is None:
                                pan['ingr']   = ingr
                                pan['timer']  = 0.0
                                pan['ready']  = False
                                pan['burned'] = False
                                audio_manager.play_button_wood()
                            break
                else:
                    # Left-area ingredient: drop onto sandwich area
                    sx = L['sandwich_x']; sy = L['sandwich_y']
                    sw_v = L['sandwich_w']; sh_v = L['sandwich_h']
                    if sx <= tx <= sx + sw_v and sy <= ty <= sy + sh_v:
                        if self._sandwich.count(ingr) == 0:
                            new_combo = self._sandwich + [ingr]
                            if self._get_combo_tex(new_combo):
                                self._sandwich.append(ingr)
                                if ingr == 'bread':
                                    audio_manager.play_bread()
                                elif ingr == 'tomato':
                                    audio_manager.play_tomato()
                                elif ingr == 'onion':
                                    audio_manager.play_onion()
                                elif ingr in ('cheese', 'ham'):
                                    audio_manager.play_cheese()
                                else:
                                    audio_manager.play_lettuce()

        if self._dragging_pan_ingr:
            ingr      = self._dragging_pan_ingr
            slot_key  = self._dragging_pan_slot
            self._dragging_pan_ingr = None
            self._dragging_pan_slot = None
            L = self._L
            if L:
                tx, ty = touch.pos
                sx = L['sandwich_x']; sy = L['sandwich_y']
                sw_v = L['sandwich_w']; sh_v = L['sandwich_h']
                if sx <= tx <= sx + sw_v and sy <= ty <= sy + sh_v:
                    if self._sandwich.count(ingr) == 0:
                        new_combo = self._sandwich + [ingr]
                        if self._get_combo_tex(new_combo):
                            self._sandwich.append(ingr)
                            pan = self._pans[slot_key]
                            pan['ingr']  = None
                            pan['timer'] = 0.0
                            pan['ready'] = False
                            audio_manager.play_button_wood()

        self._pressed_ingr = None
        return False


# ══════════════════════════════════════════════════════════════════
# KitchenGameScreen – wrapper FloatLayout holding the game widget
# and HUD labels.
# ══════════════════════════════════════════════════════════════════

class KitchenGameScreen(FloatLayout):

    def __init__(self, **kwargs):
        self.name    = kwargs.pop("name", "kitchen_gameplay")
        self.manager = None
        super().__init__(**kwargs)

        self.level_num   = 1
        self._game_widget = None

        # HUD labels drawn on top of the canvas widget
        self._lbl_timer      = Label(font_name=_FONT, font_size=fsp(30), bold=True,
                                     color=(1.0, 1.0, 1.0, 1.0),
                                     size_hint=(None, None), halign="center", valign="middle")
        self._lbl_score      = Label(font_name=_FONT, font_size=fsp(30),
                                     color=(1.0, 1.0, 1.0, 1.0),
                                     size_hint=(None, None), halign="center", valign="middle")
        self._lbl_complaints = Label(font_name=_FONT, font_size=fsp(18),
                                     color=(0.95, 0.55, 0.40, 1.0),
                                     size_hint=(None, None), halign="center", valign="middle",
                                     opacity=0)  # hidden – replaced by lives widget

        # Lives widget (0–3_lives.png, mirrors bar duty)
        self._lives_textures = []
        for n in range(4):
            try:
                self._lives_textures.append(
                    CoreImage(os.path.join(_ASSETS, "ui", f"{n}_lives.png")).texture)
            except Exception:
                self._lives_textures.append(None)
        self._lives_widget = Widget(size_hint=(None, None))
        with self._lives_widget.canvas:
            Color(1, 1, 1, 1)
            self._lives_rect = Rectangle(pos=self._lives_widget.pos,
                                         size=self._lives_widget.size)
        def _upd_lives(*_):
            self._lives_rect.pos  = self._lives_widget.pos
            self._lives_rect.size = self._lives_widget.size
        self._lives_widget.bind(pos=_upd_lives, size=_upd_lives)
        self._lbl_end        = Label(font_name=_FONT, font_size=fsp(32), bold=True,
                                     color=(1.0, 0.92, 0.40, 1.0),
                                     size_hint=(None, None), halign="center", valign="middle",
                                     opacity=0)

        # Clock UI panel behind the timer, score, and complaints labels
        _clock_aspect = 603 / 198
        _clock_w      = 210
        _clock_h      = _clock_w / _clock_aspect

        def _make_hud_panel(w, h, filename):
            widget = Widget(size_hint=(None, None), size=(w, h))
            try:
                tex = CoreImage(os.path.join(_ASSETS, filename)).texture
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

        self._clock_ui       = _make_hud_panel(_clock_w, _clock_h, "ui/clock_ui.png")
        self._clock_ui_score = _make_hud_panel(_clock_w, _clock_h, "ui/ui_empty.png")

        self.bind(size=self._reposition_labels, pos=self._reposition_labels)

    def _img_to_screen_box(self, zone):
        """Convert (left, top, right, bottom) in source image pixels to
        (screen_x, screen_y, width, height) in Kivy coords.
        Matches fill-width letterbox: always fill-width, crop/letterbox vertically."""
        l, t, r, b = zone
        scr_w, scr_h = self.width, self.height
        if scr_w == 0 or scr_h == 0:
            return 0, 0, 1, 1
        scale    = scr_w / KITCHEN_BG_W
        scaled_h = scale * KITCHEN_BG_H
        sx = lambda ix: ix * scale
        if scaled_h >= scr_h:
            crop_y = (scaled_h - scr_h) / 2
            sy = lambda iy: scr_h - (iy * scale - crop_y)
        else:
            sy = lambda iy: (scr_h + scaled_h) / 2 - iy * scale
        x0, x1   = sx(l), sx(r)
        y_top, y_bot = sy(t), sy(b)
        return x0, y_bot, x1 - x0, y_top - y_bot

    def _reposition_labels(self, *_):
        W, H = self.width, self.height
        if W < 2 or H < 2:
            return

        # Timer
        tx, ty, tw, th = self._img_to_screen_box(KITCHEN_HUD_ZONE_TIMER)
        self._lbl_timer.pos       = (tx, ty)
        self._lbl_timer.size      = (tw, th)
        self._lbl_timer.text_size = (tw, None)
        self._clock_ui.pos        = (tx, ty)
        self._clock_ui.size       = (tw, th)

        # Score
        sx, sy, sw, sh = self._img_to_screen_box(KITCHEN_HUD_ZONE_SCORE)
        self._lbl_score.pos       = (sx, sy)
        self._lbl_score.size      = (sw, sh)
        self._lbl_score.text_size = (sw, None)
        self._clock_ui_score.pos  = (sx, sy)
        self._clock_ui_score.size = (sw, sh)

        # Lives widget
        cx, cy, cw, ch = self._img_to_screen_box(KITCHEN_HUD_ZONE_COMPLAINTS)
        self._lives_widget.pos  = (cx, cy)
        self._lives_widget.size = (cw, ch)

        # End overlay
        self._lbl_end.pos      = (W * 0.20, H * 0.44)
        self._lbl_end.size     = (W * 0.60, fsp(40))
        self._lbl_end.text_size = (W * 0.60, None)

    def _tick_labels(self, dt):
        gw = self._game_widget
        if gw is None:
            return

        rush = "  RUSH!" if gw._in_rush else ""
        if gw._orders_required == 0:
            # Endless mode — no meaningful timer or quota
            self._lbl_timer.text = f"∞{rush}"
            self._lbl_score.text = str(gw._orders_completed)
        else:
            mins = int(gw._shift_timer) // 60
            secs = int(gw._shift_timer) % 60
            self._lbl_timer.text = f"{mins}:{secs:02d}{rush}"
            self._lbl_score.text = f"{gw._orders_completed}/{gw._orders_required}"
        lives_left = max(0, min(3, gw._max_complaints - gw._complaints))
        tex = self._lives_textures[lives_left]
        if tex:
            self._lives_rect.texture = tex

        self._lbl_end.opacity = 0

    def on_enter(self):
        audio_manager.start_game_music(volume_scale=0.25)
        player = get_current_player()
        player_name = player["name"] if player else "Player"

        cfg = KITCHEN_LEVELS.get(self.level_num, KITCHEN_LEVELS[1])

        # Remove old game widget and labels
        if self._game_widget:
            self._game_widget.stop()
            self.remove_widget(self._game_widget)
            self._game_widget = None
        for w in (self._clock_ui, self._clock_ui_score, self._lives_widget,
                  self._lbl_timer, self._lbl_score, self._lbl_complaints, self._lbl_end):
            if w.parent:
                self.remove_widget(w)

        self._lbl_end.opacity = 0

        # Create fresh game widget
        self._game_widget = KitchenGameWidget(
            player_name=player_name,
            level_num=self.level_num,
            level_cfg=cfg,
            on_success=self._on_success,
            on_fail=self._on_fail,
            size_hint=(1, 1),
            pos_hint={"x": 0, "y": 0},
        )
        self.add_widget(self._game_widget)

        # HUD labels on top (clock_ui panels behind labels, so added first)
        for bg in (self._clock_ui, self._clock_ui_score, self._lives_widget):
            self.add_widget(bg)
        for lbl in (self._lbl_timer, self._lbl_score, self._lbl_end):
            self.add_widget(lbl)

        self._reposition_labels()
        self._label_clock = Clock.schedule_interval(self._tick_labels, 1.0 / 30.0)

    def on_leave(self):
        if hasattr(self, '_label_clock') and self._label_clock:
            self._label_clock.cancel()
            self._label_clock = None
        if self._game_widget:
            self._game_widget.stop()

    def _on_success(self):
        pass   # handled by KitchenGameWidget navigating to kitchen_level_end

    def _on_fail(self):
        pass
