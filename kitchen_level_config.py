"""
kitchen_level_config.py – Kitchen Duty campaign level definitions.

Each level dict contains:
  name                – display name for this shift
  duration_secs       – shift timer (seconds); level succeeds when it hits 0
  victor_lines        – list of dialogue strings shown before the level
  max_orders          – max simultaneous customer orders visible at once
  recipe_pool         – list of ingredient tuples (sorted) available this level
  cat_enabled         – whether cats appear on the counter
  cat_key             – which cat walks across ("mittens" | "hector")
  cat_speed_mult      – multiplier on KITCHEN_CAT_SPEED_BASE
  cat_frequency_mult  – multiplier on spawn interval (>1 = less frequent = easier)
  contamination_enabled – whether cat hair contaminates the sandwich
  patience_mult       – multiplier on base patience time (>1 = more patient = easier)
  order_interval_mult – multiplier on base order spawn interval (>1 = slower = easier)
  rush_mode           – whether random "rush periods" activate (Level 9+)
"""

# ── Ingredient combinations available as orders ────────────────────────────────
# Each recipe is a sorted tuple of ingredient keys.
# Display name is derived at runtime from the ingredients.

R_CHEESE    = ("bread", "cheese")
R_HAM       = ("bread", "ham")
R_SALAD     = ("bread", "lettuce", "tomato")
R_CLUB      = ("bread", "ham", "tomato")
R_GARDEN    = ("bread", "cheese", "lettuce")
R_HAM_CHSE  = ("bread", "cheese", "ham")
R_DELUXE    = ("bread", "cheese", "ham", "tomato")
R_VEGGIE    = ("bread", "cheese", "lettuce", "tomato")
# Onion recipes
R_ONION     = ("bread", "onion")
R_HAM_ONION = ("bread", "ham", "onion")
R_FULL_CLUB = ("bread", "ham", "onion", "tomato")
R_LOADED    = ("bread", "cheese", "ham", "onion", "tomato")
# Pan-cooked recipes (require bacon / eggs to be fried first)
R_BACON     = ("bacon", "bread")
R_EGGS      = ("bread", "eggs")
R_BREKKIE   = ("bacon", "bread", "eggs")

KITCHEN_LEVELS = {
    1: {
        "name":               "First Shift",
        "duration_secs":      120,
        "orders_required":    6,
        "victor_lines": [],
        "max_orders":          2,
        "recipe_pool":         [R_CHEESE, R_HAM, R_SALAD],
        "pan_enabled":         False,
        "cat_enabled":         False,
        "cat_key":             "mittens",
        "cat_speed_mult":      0.80,
        "cat_frequency_mult":  2.0,
        "contamination_enabled": False,
        "patience_mult":       1.30,
        "order_interval_mult": 1.20,
        "rush_mode":           False,
    },
    2: {
        "name":               "Lunch Rush",
        "duration_secs":      120,
        "orders_required":    7,
        "victor_lines": [],
        "max_orders":          3,
        "recipe_pool":         [R_CHEESE, R_HAM, R_SALAD, R_BACON],
        "pan_enabled":         True,
        "cat_enabled":         False,
        "cat_key":             "mittens",
        "cat_speed_mult":      0.80,
        "cat_frequency_mult":  2.0,
        "contamination_enabled": False,
        "patience_mult":       1.40,
        "order_interval_mult": 1.00,
        "rush_mode":           False,
    },
    3: {
        "name":               "Tick Tock",
        "duration_secs":      135,
        "orders_required":    6,
        "victor_lines":       [],
        "max_orders":          3,
        "recipe_pool":         [R_CHEESE, R_HAM, R_SALAD, R_GARDEN, R_BACON, R_EGGS],
        "pan_enabled":         True,
        "cat_enabled":         False,
        "cat_key":             "mittens",
        "cat_speed_mult":      0.80,
        "cat_frequency_mult":  2.0,
        "contamination_enabled": False,
        "patience_mult":       1.00,
        "order_interval_mult": 0.85,
        "rush_mode":           False,
    },
    4: {
        "name":               "Double Trouble",
        "duration_secs":      150,
        "orders_required":    7,
        "victor_lines":       [],
        "max_orders":          4,
        "recipe_pool":         [R_CHEESE, R_HAM, R_SALAD, R_CLUB, R_GARDEN, R_BACON, R_EGGS, R_BREKKIE],
        "pan_enabled":         True,
        "cat_enabled":         False,
        "cat_key":             "mittens",
        "cat_speed_mult":      0.80,
        "cat_frequency_mult":  2.0,
        "contamination_enabled": False,
        "patience_mult":       1.20,
        "order_interval_mult": 0.80,
        "rush_mode":           False,
    },
    5: {
        "name":               "Counter Cat",
        "duration_secs":      150,
        "orders_required":    8,
        "victor_lines": [],
        "max_orders":          4,
        "recipe_pool":         [R_CHEESE, R_HAM, R_SALAD, R_CLUB, R_GARDEN, R_BACON, R_EGGS],
        "pan_enabled":         True,
        "cat_enabled":         True,
        "cat_key":             "mittens",
        "cat_speed_mult":      0.75,
        "cat_frequency_mult":  1.80,
        "contamination_enabled": False,
        "patience_mult":       1.20,
        "order_interval_mult": 0.75,
        "rush_mode":           False,
    },
    6: {
        "name":               "Zoomies",
        "duration_secs":      165,
        "orders_required":    9,
        "victor_lines":       [],
        "max_orders":          5,
        "recipe_pool":         [R_CHEESE, R_HAM, R_SALAD, R_CLUB, R_GARDEN, R_HAM_CHSE, R_ONION, R_HAM_ONION, R_BACON, R_EGGS],
        "pan_enabled":         True,
        "cat_enabled":         True,
        "cat_key":             "mittens",
        "cat_speed_mult":      1.20,
        "cat_frequency_mult":  1.20,
        "contamination_enabled": False,
        "patience_mult":       1.10,
        "order_interval_mult": 0.70,
        "rush_mode":           False,
    },
    7: {
        "name":               "Hair Today, Gone Tomorrow",
        "duration_secs":      180,
        "orders_required":    10,
        "victor_lines": [],
        "max_orders":          5,
        "recipe_pool":         [R_CHEESE, R_HAM, R_SALAD, R_CLUB, R_GARDEN, R_HAM_CHSE, R_ONION, R_HAM_ONION, R_FULL_CLUB, R_BACON, R_EGGS, R_BREKKIE],
        "pan_enabled":         True,
        "cat_enabled":         True,
        "cat_key":             "mittens",
        "cat_speed_mult":      1.10,
        "cat_frequency_mult":  1.00,
        "contamination_enabled": True,
        "patience_mult":       1.00,
        "order_interval_mult": 0.65,
        "rush_mode":           False,
    },
    8: {
        "name":               "Dinner Disaster",
        "duration_secs":      180,
        "orders_required":    11,
        "victor_lines":       [],
        "max_orders":          5,
        "recipe_pool":         [R_CHEESE, R_HAM, R_SALAD, R_CLUB, R_GARDEN, R_HAM_CHSE, R_DELUXE, R_ONION, R_HAM_ONION, R_FULL_CLUB, R_BACON, R_EGGS, R_BREKKIE],
        "pan_enabled":         True,
        "cat_enabled":         True,
        "cat_key":             "mittens",
        "cat_speed_mult":      1.30,
        "cat_frequency_mult":  0.85,
        "contamination_enabled": True,
        "patience_mult":       0.90,
        "order_interval_mult": 0.55,
        "rush_mode":           False,
    },
    9: {
        "name":               "Absolute Kitchen Chaos",
        "duration_secs":      195,
        "orders_required":    12,
        "victor_lines":       [],
        "max_orders":          6,
        "recipe_pool":         [R_CHEESE, R_HAM, R_SALAD, R_CLUB, R_GARDEN, R_HAM_CHSE, R_DELUXE, R_VEGGIE, R_ONION, R_HAM_ONION, R_FULL_CLUB, R_LOADED, R_BACON, R_EGGS, R_BREKKIE],
        "pan_enabled":         True,
        "cat_enabled":         True,
        "cat_key":             "mittens",
        "cat_speed_mult":      1.50,
        "cat_frequency_mult":  0.65,
        "contamination_enabled": True,
        "patience_mult":       0.80,
        "order_interval_mult": 0.50,
        "rush_mode":           True,
    },
    10: {
        "name":               "Victor's Final Shift",
        "duration_secs":      210,
        "orders_required":    14,
        "victor_lines": [],
        "max_orders":          7,
        "recipe_pool":         [R_CHEESE, R_HAM, R_SALAD, R_CLUB, R_GARDEN, R_HAM_CHSE, R_DELUXE, R_VEGGIE, R_ONION, R_HAM_ONION, R_FULL_CLUB, R_LOADED, R_BACON, R_EGGS, R_BREKKIE],
        "pan_enabled":         True,
        "cat_enabled":         True,
        "cat_key":             "mittens",
        "cat_speed_mult":      1.70,
        "cat_frequency_mult":  0.50,
        "contamination_enabled": True,
        "patience_mult":       0.70,
        "order_interval_mult": 0.40,
        "rush_mode":           True,
    },

    # ── Endless mode (level_num = 0) ──────────────────────────────────────────
    # No time limit, no order quota — play until 3 complaints.
    0: {
        "name":               "Endless",
        "duration_secs":      99999,
        "orders_required":    0,
        "victor_lines": [],
        "max_orders":          7,
        "recipe_pool":         [R_CHEESE, R_HAM, R_SALAD, R_CLUB, R_GARDEN, R_HAM_CHSE, R_DELUXE, R_VEGGIE, R_ONION, R_HAM_ONION, R_FULL_CLUB, R_LOADED, R_BACON, R_EGGS, R_BREKKIE],
        "pan_enabled":         True,
        "cat_enabled":         True,
        "cat_key":             "mittens",
        "cat_speed_mult":      1.70,
        "cat_frequency_mult":  0.50,
        "contamination_enabled": True,
        "patience_mult":       0.70,
        "order_interval_mult": 0.40,
        "rush_mode":           True,
    },
}

KITCHEN_TOTAL_LEVELS = 10

# ── Display name for a recipe tuple ───────────────────────────────────────────

_RECIPE_NAMES = {
    R_CHEESE:   "Cheese Sandwich",
    R_HAM:      "Ham Sandwich",
    R_SALAD:    "Salad Sandwich",
    R_CLUB:     "Club Sandwich",
    R_GARDEN:   "Garden Sandwich",
    R_HAM_CHSE: "Ham & Cheese",
    R_DELUXE:   "Deluxe Stack",
    R_VEGGIE:   "Veggie Deluxe",
    R_BACON:    "Bacon Bap",
    R_EGGS:     "Egg Sandwich",
    R_BREKKIE:  "Full Breakfast",
    R_ONION:    "Onion Sandwich",
    R_HAM_ONION: "Ham & Onion",
    R_FULL_CLUB: "Full Club",
    R_LOADED:   "Loaded Stack",
}


def recipe_display_name(recipe):
    """Return a short human-readable name for a recipe tuple."""
    key = tuple(sorted(recipe))
    return _RECIPE_NAMES.get(key, " + ".join(i.capitalize() for i in key))
