# ─────────────────────────────────────────────────────────────
# game_constants.py
# All tunable values for Mittens – Kivy/Android port.
# Physics values converted from the original pygame (60 fps, frame-based)
# to time-based (px / second) so Kivy's dt loop stays frame-rate-independent.
# ─────────────────────────────────────────────────────────────

# ── Debug ──────────────────────────────────────────────────────
# Set to True to show coloured overlays on all invisible hitbox buttons.
# Each zone gets its own colour so you can tell them apart.
# Flip back to False before release.
DEBUG_HITBOXES = False

# Reference height used for scaling (matches original pygame: scale = height / 700)
REF_SCALE_HEIGHT = 700.0

# ── Cat ──────────────────────────────────────────────────────
CAT_W_REF        = 130      # hitbox width  at reference scale
CAT_H_REF        = 110      # hitbox height at reference scale
CAT_SPRITE_W_REF    = 205   # ← adjust mittens sprite width
CAT_SPRITE_H_REF    = 225   # ← adjust mittens sprite height
HECTOR_SPRITE_W_REF        = 310   # ← adjust hector sprite width
HECTOR_SPRITE_H_REF        = 250   # ← adjust hector sprite height
HECTOR_SPRITE_Y_NUDGE_REF  = 8    # ← px to shift hector upward (positive = up)
OSCAR_SPRITE_W_REF  = 310   # ← adjust oscar sprite width
OSCAR_SPRITE_H_REF  = 250   # ← adjust oscar sprite height
OSCAR_SPRITE_Y_NUDGE_REF = 8   # ← px to shift oscar upward (positive = up)
CHILI_SPRITE_W_REF  = 205   # ← adjust chili sprite width
CHILI_SPRITE_H_REF  = 225   # ← adjust chili sprite height
CAT_SPEED_BASE  = 84.0      # 1.4 px/frame × 60 fps
CAT_SPEED_MAX   = 420.0     # 7.0 px/frame × 60 fps
CAT_ANIM_FPS        = 6         # animation frames per second
OSCAR_ANIM_FPS      = 9         # slightly faster than other cats
CAT_ANIM_COUNT  = 4
CAT_LEFT_MARGIN_F  = 0.02   # fraction of screen width (left boundary)
CAT_RIGHT_MARGIN_F = 0.12   # fraction of screen width (right boundary)
CAT_Y_FROM_TOP_F   = 0.14   # fraction of screen height from top

# ── Bar prop (decorative; drawn in front of cat) ─────────────
BEER_PROP_W_REF        = 80    # ← adjust beer_prop.png width
BEER_PROP_H_REF        = 110    # ← adjust beer_prop.png height
BEER_PROP_X_F           = 0.08   # ← first beer prop horizontal position (fraction of screen width)
BEER_PROP_Y_FROM_BOT_F  = 0.57  # ← first beer prop vertical position (fraction of art height from bottom)
BEER_PROP2_X_F          = 0.00   # ← second beer prop horizontal position
BEER_PROP2_Y_FROM_BOT_F = 0.61  # ← second beer prop vertical position

# ── Disco flyer prop (only visible in disco mode) ─────────────
DISCO_FLYER_W_REF        = 90    # ← adjust disco_mode_flyer.png width
DISCO_FLYER_H_REF        = 128   # ← adjust disco_mode_flyer.png height
DISCO_FLYER_X_F          = 0.15  # ← horizontal position (fraction of screen width)
DISCO_FLYER_Y_FROM_BOT_F = 0.60  # ← vertical position (fraction of art height from bottom)

# ── Tray ─────────────────────────────────────────────────────
TRAY_W_REF           = 380   # sprite width
TRAY_H_REF           = 170   # sprite height
TRAY_HB_W_REF        = 240   # ← catch-zone width  (independent of sprite)
TRAY_HB_H_REF        = 40    # ← catch-zone height (independent of sprite)
TRAY_Y_FROM_BOTTOM_F = 0.0   # fraction of art height from bottom  ← adjust tray height
TRAY_EDGE_MARGIN_F   = 0.01

# ── Beer cups ────────────────────────────────────────────────
BEER_W_REF          = 90   # hitbox width  at reference scale
BEER_H_REF          = 90   # hitbox height at reference scale
BEER_SPRITE_W_REF        = 84   # ← adjust to resize beer.png (width)
BEER_SPRITE_H_REF        = 111  # ← adjust to resize beer.png (height)
BEER_BROKEN_SPRITE_W_REF = 116   # ← adjust to resize beer_broken.png (width)
BEER_BROKEN_SPRITE_H_REF = 111  # ← adjust to resize beer_broken.png (height)
BEER_SPEED_BASE     = 180.0   # 3.0 px/frame × 60
BEER_SPEED_BONUS    = 0.9     # per score point  (0.015 × 60)
BEER_SPEED_BONUS_MAX= 180.0   # cap               (3.0  × 60)
BEER_SPEED_RAND     = 180.0   # extra random range (3.0  × 60)
BEER_GRAVITY        = 380.0   # px/s² acceleration while falling
BEER_ANGLE_MAX      = 15      # degrees
BEER_BROKEN_SECS         = 8.0 / 60.0   # broken-cup display time
BEER_BROKEN_Y_OFFSET_REF = 20           # ← px above the floor the broken sprite rests (increase = higher)

# ── Mice ─────────────────────────────────────────────────────
MOUSE_W_REF        = 50
MOUSE_H_REF        = 160
MOUSE_SPRITE_W_REF = 60    # ← adjust mouse.png sprite width
MOUSE_SPRITE_H_REF = 150   # ← adjust mouse.png sprite height
MOUSE_SPEED_MIN  = 360.0    # 6.0 × 60
MOUSE_SPEED_MAX  = 540.0    # 9.0 × 60
MOUSE_WIGGLE     = 60.0     # horizontal jitter px/sec

# ── Spawn intervals (seconds; 1 frame = 1/60 s) ──────────────
DROP_MIN       = 60.0  / 60.0   # 1.00 s
DROP_MAX_BASE  = 160.0 / 60.0   # 2.67 s
DROP_SCORE_DEC = 0.3   / 60.0   # per score point

MOUSE_MIN        = 900.0  / 60.0   # 15.00 s
MOUSE_MAX_BASE   = 1600.0 / 60.0   # 26.67 s
MOUSE_SCORE_DEC  = 3.0    / 60.0   # per score point
MOUSE_MAX_FLOOR  = 1100.0 / 60.0   # 18.33 s

# ── Lives HUD sprite ─────────────────────────────────────────
LIVES_SPRITE_W_REF     = 180   # ← adjust lives sprite width
LIVES_SPRITE_H_REF     = 69    # ← adjust lives sprite height
LIVES_SPRITE_MARGIN_REF = 10   # ← gap from top-right art edge

# ── Bar Duty HUD zones in source-image pixels (left, top, right, bottom) ──
# Same 3915 × 1773 coordinate space as kitchen.png.
BAR_HUD_ZONE_SCORE    = (  80,  30,  620, 220)
BAR_HUD_ZONE_TIMER    = (1790,  30, 2350, 220)
BAR_HUD_ZONE_LIVES    = (3300,  30, 3840, 220)
BAR_HUD_ZONE_SETTINGS = (3090,  30, 3280, 220)  # square button just left of lives, same height as HUD

# ── Game rules ───────────────────────────────────────────────
LIVES_START         = 3
SCORE_CUP           = 1
SCORE_MOUSE_PENALTY = 2

# ── Difficulty thresholds ────────────────────────────────────
SCORE_DISCO   = 50
SCORE_REVERSE = 80   # controls reverse
SCORE_DRUNK   = 80   # screen wobble

# ── Colours (R, G, B, A) all 0.0–1.0 ────────────────────────
COLOR_BG           = (0.094, 0.043, 0.059, 1.0)   # #180b0f
COLOR_BG_DISCO1    = (0.55, 0.05, 0.55, 1.0)
COLOR_BG_DISCO2    = (0.05, 0.50, 0.50, 1.0)
COLOR_BG_DRUNK     = (0.22, 0.05, 0.22, 1.0)
COLOR_FLOOR        = (0.25, 0.14, 0.04, 1.0)

COLOR_CAT_BODY     = (1.00, 0.60, 0.10, 1.0)
COLOR_CAT_EAR      = (0.85, 0.45, 0.00, 1.0)
COLOR_CAT_EYE      = (0.00, 0.00, 0.00, 1.0)

COLOR_TRAY         = (0.55, 0.35, 0.12, 1.0)
COLOR_TRAY_RIM     = (0.72, 0.52, 0.22, 1.0)
COLOR_HANDS        = (0.92, 0.72, 0.56, 1.0)

COLOR_BEER         = (1.00, 0.85, 0.10, 1.0)
COLOR_BEER_FOAM    = (0.98, 0.98, 0.92, 1.0)
COLOR_BROKEN       = (0.65, 0.35, 0.05, 1.0)

COLOR_MOUSE_BODY   = (0.50, 0.50, 0.50, 1.0)
COLOR_MOUSE_NOSE   = (0.90, 0.50, 0.55, 1.0)

COLOR_WHITE        = (1.00, 1.00, 1.00, 1.0)
COLOR_RED          = (0.78, 0.20, 0.20, 1.0)
COLOR_GOLD         = (0.77, 0.69, 0.42, 1.0)
COLOR_YELLOW       = (1.00, 0.75, 0.00, 1.0)
COLOR_BLACK        = (0.00, 0.00, 0.00, 1.0)

COLOR_BTN          = (0.30, 0.18, 0.06, 1.0)
COLOR_BTN_PRESSED  = (0.50, 0.30, 0.10, 1.0)
COLOR_BTN_TEXT     = (0.92, 0.82, 0.52, 1.0)
COLOR_OVERLAY      = (0.00, 0.00, 0.00, 0.75)

# ── Opponents ─────────────────────────────────────────────────
# Each entry defines display info and difficulty multipliers.
# *_mult values scale the corresponding base constants:
#   >1 = harder/faster,  <1 = easier/slower  (for cat/cup speed)
#   >1 = easier (drop_mult, mouse_mult – longer spawn intervals)
OPPONENTS = {
    "oscar": {
        "display_name":   "Oscar",
        "difficulty":     "EASY",
        "tagline":        "Lazy & sleepy",
        "stars":          "\u2605",
        "card_color":     (0.10, 0.12, 0.20, 1.0),
        "body_color":     (0.10, 0.10, 0.12, 1.0),
        "ear_color":      (0.22, 0.06, 0.10, 1.0),
        "eye_color":      (0.90, 0.85, 0.20, 1.0),
        "cat_speed_mult": 0.70,
        "cup_speed_mult": 0.75,
        "drop_mult":      1.35,
        "mouse_mult":     1.40,
    },
    "mittens": {
        "display_name":   "Mittens",
        "difficulty":     "NORMAL",
        "tagline":        "The original menace",
        "stars":          "\u2605\u2605",
        "card_color":     (0.50, 0.26, 0.05, 1.0),
        "body_color":     (1.00, 0.60, 0.10, 1.0),
        "ear_color":      (0.85, 0.45, 0.00, 1.0),
        "eye_color":      (0.10, 0.55, 0.10, 1.0),
        "cat_speed_mult": 1.00,
        "cup_speed_mult": 1.00,
        "drop_mult":      1.00,
        "mouse_mult":     1.00,
    },
    "hector": {
        "display_name":   "Hector",
        "difficulty":     "HARD",
        "tagline":        "Fast & relentless",
        "stars":          "\u2605\u2605\u2605",
        "card_color":     (0.22, 0.26, 0.32, 1.0),
        "body_color":     (0.55, 0.55, 0.62, 1.0),
        "ear_color":      (0.38, 0.40, 0.46, 1.0),
        "eye_color":      (0.20, 0.55, 0.88, 1.0),
        "cat_speed_mult": 1.35,
        "cup_speed_mult": 1.40,
        "drop_mult":      0.75,
        "mouse_mult":     0.80,
    },
    "chili": {
        "display_name":   "Chili",
        "difficulty":     "CHAOS",
        "tagline":        "Pure madness",
        "stars":          "\u2605\u2605\u2605\u2605",
        "card_color":     (0.45, 0.08, 0.05, 1.0),
        "body_color":     (0.88, 0.42, 0.10, 1.0),
        "ear_color":      (0.68, 0.24, 0.05, 1.0),
        "eye_color":      (0.95, 0.18, 0.10, 1.0),
        "cat_speed_mult": 1.70,
        "cup_speed_mult": 1.80,
        "drop_mult":      0.55,
        "mouse_mult":     0.60,
    },
}

OPPONENT_ORDER = ["oscar", "mittens", "hector", "chili"]


# ══════════════════════════════════════════════════════════════════
# Kitchen Duty constants
# ══════════════════════════════════════════════════════════════════

# ── Kitchen background aspect ratio ─────────────────────────────
# kitchen.png source dimensions: 3915 × 1773  (same as bar_duty assets)
KITCHEN_BG_W      = 3915
KITCHEN_BG_H      = 1773
KITCHEN_BG_ASPECT = 3915.0 / 1773.0   # ≈ 2.21 — used for fill-width letterbox

# HUD element zones in source-image pixels (left, top, right, bottom).
# Adjust these to move/resize the timer, score, and complaints labels.
KITCHEN_HUD_ZONE_TIMER      = (1790,  30, 2350, 220)
KITCHEN_HUD_ZONE_SCORE      = (  80,  30,  620, 220)
KITCHEN_HUD_ZONE_COMPLAINTS = (3300,  30, 3840, 220)

# ── Image-fraction layout zones ────────────────────────────────
# All x/y values are fractions of the SOURCE IMAGE (3915 × 1773).
# x:  0.0 = left edge,    1.0 = right edge
# y:  0.0 = TOP of image, 1.0 = BOTTOM of image
#
# Conversion helpers (computed at runtime in KitchenGameWidget):
#   screen_x = img_x + fx * img_w
#   screen_y = img_y + (1.0 - fy) * img_h   ← Kivy y=0 is at bottom

# String / fairy lights (where order tickets hang from)
KITCHEN_STRING_Y_F       = 0.175


#X left, X right, Y top, Y bot
KITCHEN_TICKET_SLOTS = [
    (0.204, 0.316, 0.125, 0.482),   # slot 1
    (0.389, 0.501, 0.163, 0.520),   # slot 2
    (0.563, 0.675, 0.160, 0.517),   # slot 3
    (0.743, 0.855, 0.107, 0.462),   # slot 4
    (0.893, 1.005, 0.017, 0.372),   # slot 5
]

# Counter surface top edge
KITCHEN_COUNTER_TOP_Y_F  = 0.560

# Plate drop zone – circular plate on the far-left serving station
KITCHEN_PLATE_X1_F       = 0.000  # left edge of plate zone
KITCHEN_PLATE_X2_F       = 0.159   # right edge of plate zone
KITCHEN_PLATE_Y1_F       = 0.320   # top of plate zone (image frac from top)
KITCHEN_PLATE_Y2_F       = 0.772   # bottom of plate zone

# Bell tap zone – orange dome below the plate
KITCHEN_SERVE_X1_F       = 0.037   # left bell
KITCHEN_SERVE_X2_F       = 0.127  # right bell
KITCHEN_SERVE_Y1_F       = 0.770   # top bell
KITCHEN_SERVE_Y2_F       = 0.980   # bottom bell

# Left area – 6 ingredients in 2 rows × 3 columns (extended for bigger buttons)
KITCHEN_LEFT_X1_F        = 0.073
KITCHEN_LEFT_X2_F        = 0.455
KITCHEN_LEFT_Y1_F        = 0.560
KITCHEN_LEFT_Y2_F        = 0.920

# Center prep zone – sandwich display + cat contamination zone
KITCHEN_CENTER_X1_F      = 0.496
KITCHEN_CENTER_X2_F      = 0.640
KITCHEN_CENTER_Y1_F      = 0.560
KITCHEN_CENTER_Y2_F      = 0.870

# Right area – 2 stove ingredients (bacon, eggs) + pan slots
KITCHEN_RIGHT_X1_F       = 0.601
KITCHEN_RIGHT_X2_F       = 0.991
KITCHEN_RIGHT_Y1_F       = 0.560
KITCHEN_RIGHT_Y2_F       = 0.870

# Pans overlay image – position/size as fractions of kitchen.png dimensions.
# Tweak these to shift or resize pans.png over the stove area.
# x/y = top-left corner (image-top = 0, image-left = 0); w/h = size fractions.
KITCHEN_PANS_X_F         = 0.850
KITCHEN_PANS_Y_F         = 0.576
KITCHEN_PANS_W_F         = 0.150
KITCHEN_PANS_H_F         = 0.380

# Cat walking y (image fraction from top; just below counter edge)
KITCHEN_CAT_Y_F          = 0.575

# Cat sprite reference sizes (at 1280-wide screen)
KITCHEN_CAT_W_REF        = 110   # px wide at reference screen width
KITCHEN_CAT_H_REF        = 130   # px tall

# ── Kitchen cat speeds (px/s at 1280-wide reference screen) ─────
KITCHEN_CAT_SPEED_BASE   = 200.0  # base speed
KITCHEN_CAT_SPEED_MAX    = 550.0  # hard cap

# ── Cat spawn timing ────────────────────────────────────────────
KITCHEN_CAT_SPAWN_BASE   = 18.0   # seconds between cat spawns (× level mult)

# ── Cat peek timing ─────────────────────────────────────────────
KITCHEN_CAT_PEEK_TIME    = 2.5    # seconds cat is visible before it steals
KITCHEN_CAT_RISE_TIME    = 0.40   # seconds to rise up / duck back down
KITCHEN_CAT_PEEK_ANIM_FPS = 2     # animation speed for peek/steal frames (lower = slower)
KITCHEN_CAT_PEEK_SCALE    = 2.5   # size multiplier for peek sprite (1.0 = base cat size)
KITCHEN_CAT_PEEK_Y_F      = 0.76  # image-fraction from top where cat base sits (higher = lower on screen)
KITCHEN_CAT_PEEK_PAUSE    = 1.0   # seconds to pause at top and bottom of peek cycle

# ── Order patience time ─────────────────────────────────────────
KITCHEN_ORDER_PATIENCE_BASE = 38.0   # seconds (× level patience_mult)

# ── Order spawn interval ────────────────────────────────────────
KITCHEN_ORDER_INTERVAL_BASE = 12.0   # seconds (× level order_interval_mult)

# ── Scoring ─────────────────────────────────────────────────────
KITCHEN_SCORE_PER_ORDER  = 10    # base score per completed order
KITCHEN_COINS_BASE       =  5    # base coins per completed order (+ patience bonus)

# ── Failure threshold ───────────────────────────────────────────
KITCHEN_MAX_COMPLAINTS   = 3     # complaints before level fail

# ── Rush mode ───────────────────────────────────────────────────
KITCHEN_RUSH_PERIOD      = 35.0  # seconds between rush periods
KITCHEN_RUSH_DURATION    = 12.0  # seconds each rush lasts

# ── Per-ingredient scale factors ────────────────────────────────
# Each value is (scale_x, scale_y) relative to the button slot size.
# 1.0 = fill slot.  Only affects the visual; the touch hitbox stays the same.
KITCHEN_INGR_SCALES = {
    "lettuce": (1.07, 0.63),
    "tomato":  (0.95, 0.79),   # ← adjust (width, height) to resize tomatoes
    "onion":   (1.04, 0.73),
    "bread":   (0.99, 0.92),
    "ham":     (1.0, 1.0),
    "cheese":  (1.1, 0.92),
    "bacon":   (0.95, 0.7),
    "eggs":    (1.1, 0.9),
}

# ── Per-ingredient pixel offsets (dx, dy) ───────────────────────
# Nudge individual ingredient tray buttons from their grid position.
# Positive dx = right, negative dx = left.
# Positive dy = up,    negative dy = down.
# Offsets as fractions of (img_w, img_h) so they scale with any screen size.
# Tuned at 1920-px-wide reference (img_h ≈ 869). Applied via sw(ox)/sh(oy).
KITCHEN_INGR_OFFSETS = {
    "lettuce": (-0.0052, -0.0265),
    "tomato":  ( 0.0016, -0.0150),
    "onion":   (-0.0125, -0.0196),
    "bread":   (-0.0063, -0.0104),
    "ham":     (-0.0026, -0.0069),
    "cheese":  (-0.0031, -0.0115),
    "bacon":   (-0.0042, -0.0219),
    "eggs":    ( 0.0005, -0.0115),
}

# ── Ingredient display colours (RGBA) ───────────────────────────
KITCHEN_COLOR_BREAD      = (0.85, 0.68, 0.38, 1.0)
KITCHEN_COLOR_LETTUCE    = (0.22, 0.62, 0.22, 1.0)
KITCHEN_COLOR_TOMATO     = (0.82, 0.18, 0.18, 1.0)
KITCHEN_COLOR_CHEESE     = (0.95, 0.82, 0.08, 1.0)
KITCHEN_COLOR_HAM        = (0.88, 0.42, 0.48, 1.0)
KITCHEN_COLOR_ONION      = (0.70, 0.50, 0.75, 1.0)
KITCHEN_COLOR_BACON      = (0.55, 0.18, 0.10, 1.0)
KITCHEN_COLOR_EGGS       = (0.98, 0.95, 0.70, 1.0)

KITCHEN_INGREDIENT_COLORS = {
    "bread":   KITCHEN_COLOR_BREAD,
    "lettuce": KITCHEN_COLOR_LETTUCE,
    "tomato":  KITCHEN_COLOR_TOMATO,
    "cheese":  KITCHEN_COLOR_CHEESE,
    "ham":     KITCHEN_COLOR_HAM,
    "onion":   KITCHEN_COLOR_ONION,
    "bacon":   KITCHEN_COLOR_BACON,
    "eggs":    KITCHEN_COLOR_EGGS,
}

# Short labels used on ingredient buttons and order tickets
KITCHEN_INGREDIENT_LABELS = {
    "bread":   "BREAD",
    "lettuce": "LETTUCE",
    "tomato":  "TOMATO",
    "cheese":  "CHEESE",
    "ham":     "HAM",
    "onion":   "ONION",
    "bacon":   "BACON",
    "eggs":    "EGGS",
}

# ── Victor serving animation ────────────────────────────────────
KITCHEN_VICTOR_W_REF    = 360    # Victor sprite width at 1280 px reference screen
KITCHEN_VICTOR_H_REF    = 690    # Victor sprite height
KITCHEN_VICTOR_Y_F      = 0.548   # image fraction from top — bottom edge of Victor sprite
KITCHEN_VICTOR_SPEED_F  = 0.30   # image widths per second
KITCHEN_VICTOR_WALK_FPS = 6      # walking animation frames per second

# ── End-screen delay ────────────────────────────────────────────
KITCHEN_END_DELAY        = 1.8   # seconds before navigating to level-end screen
