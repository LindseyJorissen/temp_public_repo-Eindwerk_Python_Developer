"""
game_utils.py – Player profile and score persistence helpers.
Uses Kivy's App.user_data_dir so it works on both desktop and Android.
"""

import json
import os

# ── Font scaling helper ────────────────────────────────────────────────────────
# sp units in Kivy scale with device DPI, which makes fonts huge on high-DPI
# phones even though the screen may be small.  fsp() converts a size that looks
# correct on the 720 px-tall desktop window into the equivalent pixel count for
# whatever screen the game is actually running on.

def fsp(sp_value, ref_height=720):
    """Return a font size in screen pixels proportional to Window.height.

    sp_value   – the size (in 'sp' or px) that looks right at 720 px tall.
    ref_height – the reference window height the game was designed for (720).
    """
    try:
        from kivy.core.window import Window
        h = Window.height if Window.height > 1 else ref_height
    except Exception:
        h = ref_height
    return max(8, int(sp_value * h / ref_height))


# ── Path helpers ──────────────────────────────────────────────────────────────

def _data_dir():
    try:
        from kivy.app import App
        app = App.get_running_app()
        if app:
            return app.user_data_dir
    except Exception:
        pass
    d = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
    os.makedirs(d, exist_ok=True)
    return d

def _players_path():
    return os.path.join(_data_dir(), "players.json")

def _scores_path():
    """Legacy scores.json path – used only for one-time migration."""
    return os.path.join(_data_dir(), "scores.json")


# ── Low-level load / save ─────────────────────────────────────────────────────

def _empty():
    return {"current_player": None, "players": []}

def load_player_data():
    path = _players_path()
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return _empty()

def _save(data):
    try:
        with open(_players_path(), "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"[players] Could not write: {e}")


# ── Migration ─────────────────────────────────────────────────────────────────

def migrate_scores_if_needed():
    """One-time import from legacy scores.json → players.json."""
    if os.path.exists(_players_path()):
        return
    old_path = _scores_path()
    if not os.path.exists(old_path):
        return
    try:
        with open(old_path, "r") as f:
            old = json.load(f)
    except Exception:
        return
    data = _empty()
    for p in old.get("players", []):
        name = p.get("name", "").strip()
        if name:
            data["players"].append({
                "name":   name,
                "icon":   None,
                "scores": {"bar_duty": p.get("score", 0)},
            })
    _save(data)


# ── Player profile API ────────────────────────────────────────────────────────

def get_current_player():
    """Return the active player dict, or None if nobody is logged in."""
    data = load_player_data()
    name = data.get("current_player")
    if not name:
        return None
    for p in data["players"]:
        if p["name"] == name:
            return p
    return None

def set_current_player(name):
    data = load_player_data()
    data["current_player"] = name
    _save(data)

def save_player_profile(name, icon):
    """Create or update a player; make them the current player."""
    data = load_player_data()
    for p in data["players"]:
        if p["name"] == name:
            p["icon"] = icon
            break
    else:
        data["players"].append({
            "name": name,
            "icon": icon,
            "scores": {},
            "coins": 0,
            "stats": {"total_cups_caught": 0, "total_games_played": 0, "opponents_played": []},
            "achievements": {},
        })
    data["current_player"] = name
    _save(data)

def mark_tutorial_done(player_name):
    """Flag that this player has completed the tutorial."""
    data = load_player_data()
    for p in data["players"]:
        if p["name"] == player_name:
            p["tutorial_done"] = True
            break
    _save(data)

def update_player_score(player_name, game_mode, new_score):
    """Save a high score for a game mode (keeps existing if higher)."""
    data = load_player_data()
    for p in data["players"]:
        if p["name"].strip().upper() == player_name.strip().upper():
            current = p.setdefault("scores", {}).get(game_mode, 0)
            p["scores"][game_mode] = max(current, new_score)
            break
    _save(data)


# ── Icon helpers ──────────────────────────────────────────────────────────────

def _icons_dir():
    return os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "assets", "icons"
    )

def list_icon_keys():
    """Return sorted list of base icon keys found in assets/icons/.

    Naming convention:
      icon1.png        – large version (48×48 px), shown in hiring screen
      icon1_small.png  – small version, shown in cafe hub widget

    Keys are the base names without the _small suffix and without extension,
    de-duplicated so each icon appears once.
    """
    d = _icons_dir()
    if not os.path.isdir(d):
        return []
    keys = set()
    for f in os.listdir(d):
        if f.lower().endswith(".png"):
            stem = os.path.splitext(f)[0]
            for suffix in ("_small", "_polaroid"):
                if stem.endswith(suffix):
                    stem = stem[: -len(suffix)]
                    break
            keys.add(stem)
    return sorted(keys)

def icon_path(key):
    """Large icon path: tries <key>.png first, falls back to <key>_small.png."""
    d = _icons_dir()
    for name in (f"{key}.png", f"{key}_small.png"):
        p = os.path.join(d, name)
        if os.path.isfile(p):
            return p
    return None

def icon_path_small(key):
    """Small icon path: tries <key>_small.png first, falls back to <key>.png."""
    d = _icons_dir()
    for name in (f"{key}_small.png", f"{key}.png"):
        p = os.path.join(d, name)
        if os.path.isfile(p):
            return p
    return None

def icon_path_polaroid(key):
    """Polaroid icon path: tries <key>_polaroid.png first, falls back to <key>.png."""
    d = _icons_dir()
    for name in (f"{key}_polaroid.png", f"{key}.png"):
        p = os.path.join(d, name)
        if os.path.isfile(p):
            return p
    return None


# ── Achievement & stats API ──────────────────────────────────────────────────

def _get_player_record(data, player_name):
    """Return the player dict from data whose name matches (case-insensitive)."""
    name_upper = player_name.strip().upper()
    for p in data["players"]:
        if p["name"].strip().upper() == name_upper:
            return p
    return None


def get_player_stats(player_name):
    """Return the stats dict for a player (empty defaults if missing)."""
    data = load_player_data()
    p = _get_player_record(data, player_name)
    if not p:
        return {"total_cups_caught": 0, "total_games_played": 0, "opponents_played": []}
    return p.get("stats", {"total_cups_caught": 0, "total_games_played": 0, "opponents_played": []})


def update_player_stats(player_name, cups_caught=0, games_played=0, opponent=None):
    """Increment cumulative stats for a player."""
    data = load_player_data()
    p = _get_player_record(data, player_name)
    if not p:
        return
    stats = p.setdefault("stats", {
        "total_cups_caught": 0, "total_games_played": 0, "opponents_played": []
    })
    stats["total_cups_caught"]  = stats.get("total_cups_caught",  0) + cups_caught
    stats["total_games_played"] = stats.get("total_games_played", 0) + games_played
    if opponent and opponent not in stats.get("opponents_played", []):
        stats.setdefault("opponents_played", []).append(opponent)
    _save(data)


def is_achievement_unlocked(player_name, key):
    """Return True if the player has already unlocked this achievement."""
    data = load_player_data()
    p = _get_player_record(data, player_name)
    if not p:
        return False
    return bool(p.get("achievements", {}).get(key))


def unlock_achievement(player_name, key, coins):
    """Unlock an achievement and award coins.  Returns True if newly unlocked."""
    data = load_player_data()
    p = _get_player_record(data, player_name)
    if not p:
        return False
    ach = p.setdefault("achievements", {})
    if ach.get(key):
        return False          # already unlocked
    ach[key] = True
    p["coins"] = p.get("coins", 0) + coins
    _save(data)
    return True


def get_player_coins(player_name):
    """Return the player's current coin balance."""
    data = load_player_data()
    p = _get_player_record(data, player_name)
    if not p:
        return 0
    return p.get("coins", 0)


def get_player_purchases(player_name):
    """Return dict of {item_key: True} for all purchased shop items."""
    data = load_player_data()
    p = _get_player_record(data, player_name)
    if not p:
        return {}
    return p.get("purchases", {})


def purchase_shop_item(player_name, item_key, cost):
    """Spend coins to buy a shop item. Returns True on success, False if already owned or insufficient coins."""
    data = load_player_data()
    p = _get_player_record(data, player_name)
    if not p:
        return False
    purchases = p.setdefault("purchases", {})
    if purchases.get(item_key):
        return False
    if p.get("coins", 0) < cost:
        return False
    p["coins"] = p["coins"] - cost
    purchases[item_key] = True
    _save(data)
    return True


# ── Legacy wrapper (kept so existing gameplay.py still compiles) ──────────────

def load_scores():
    """Return list of {name, score} dicts for bar_duty, sorted high→low."""
    data = load_player_data()
    entries = [
        {"name": p["name"], "score": p.get("scores", {}).get("bar_duty", 0)}
        for p in data.get("players", [])
    ]
    return sorted(entries, key=lambda x: x["score"], reverse=True)

def update_score(player_name, new_score):
    """Legacy wrapper – saves to bar_duty mode."""
    update_player_score(player_name, "bar_duty", new_score)

def load_scores_for_opponent(opponent):
    """Return list of {name, score} dicts for a specific opponent, sorted high→low."""
    data = load_player_data()
    entries = [
        {"name": p["name"], "score": p.get("scores", {}).get(opponent, 0)}
        for p in data.get("players", [])
        if p.get("scores", {}).get(opponent, 0) > 0
    ]
    return sorted(entries, key=lambda x: x["score"], reverse=True)


# ── Bar Duty level progress API ───────────────────────────────────────────────

def get_level_progress(player_name):
    """Return dict of {level_num: {"completed": bool, "best_score": int}} for all 10 levels."""
    from level_config import TOTAL_LEVELS
    data = load_player_data()
    p = _get_player_record(data, player_name)
    raw = p.get("bar_duty_progress", {}) if p else {}
    result = {}
    for n in range(1, TOTAL_LEVELS + 1):
        key = str(n)
        result[n] = {
            "completed":  bool(raw.get(key, {}).get("completed", False)),
            "best_score": int(raw.get(key, {}).get("best_score", 0)),
        }
    return result


def is_level_unlocked(player_name, level_num):
    """Level 1 is always unlocked; level N requires level N-1 to be completed."""
    if level_num <= 1:
        return True
    progress = get_level_progress(player_name)
    return progress.get(level_num - 1, {}).get("completed", False)


def is_endless_unlocked(player_name):
    """Endless Shift unlocks when all 10 Bar Duty levels are completed."""
    from level_config import TOTAL_LEVELS
    progress = get_level_progress(player_name)
    return all(progress.get(n, {}).get("completed", False) for n in range(1, TOTAL_LEVELS + 1))


def debug_unlock_endless(player_name):
    """DEBUG ONLY – mark all Bar Duty levels complete so endless mode unlocks."""
    from level_config import TOTAL_LEVELS
    data = load_player_data()
    p = _get_player_record(data, player_name)
    if not p:
        return
    progress = p.setdefault("bar_duty_progress", {})
    for n in range(1, TOTAL_LEVELS + 1):
        entry = progress.setdefault(str(n), {"completed": False, "best_score": 0})
        entry["completed"] = True
    _save(data)


# ── Kitchen Duty level progress API ──────────────────────────────────────────

def get_kitchen_level_progress(player_name):
    """Return dict of {level_num: {"completed": bool, "best_score": int}} for all 10 KD levels."""
    from kitchen_level_config import KITCHEN_TOTAL_LEVELS
    data = load_player_data()
    p = _get_player_record(data, player_name)
    raw = p.get("kitchen_duty_progress", {}) if p else {}
    result = {}
    for n in range(1, KITCHEN_TOTAL_LEVELS + 1):
        key = str(n)
        result[n] = {
            "completed":  bool(raw.get(key, {}).get("completed", False)),
            "best_score": int(raw.get(key, {}).get("best_score", 0)),
        }
    return result


def is_kitchen_level_unlocked(player_name, level_num):
    """KD Level 1 always unlocked; level N requires level N-1 completed."""
    if level_num <= 1:
        return True
    progress = get_kitchen_level_progress(player_name)
    return progress.get(level_num - 1, {}).get("completed", False)


def is_kitchen_endless_unlocked(player_name):
    """Kitchen Endless unlocks when all 10 Kitchen Duty levels are completed."""
    from kitchen_level_config import KITCHEN_TOTAL_LEVELS
    progress = get_kitchen_level_progress(player_name)
    return all(progress.get(n, {}).get("completed", False) for n in range(1, KITCHEN_TOTAL_LEVELS + 1))


def mark_kitchen_level_complete(player_name, level_num, score):
    """Mark a Kitchen Duty level as completed and update best score.

    Returns (first_time, coins_earned):
      first_time   – True if this is the first successful completion
      coins_earned – coins awarded (only on first completion)
    """
    data = load_player_data()
    p = _get_player_record(data, player_name)
    if not p:
        return False, 0
    progress = p.setdefault("kitchen_duty_progress", {})
    key = str(level_num)
    entry = progress.setdefault(key, {"completed": False, "best_score": 0})
    first_time = not entry.get("completed", False)
    entry["completed"] = True
    entry["best_score"] = max(entry.get("best_score", 0), score)
    coins = (score * 2 + level_num * 10) if first_time else 0
    if first_time and coins > 0:
        p["coins"] = p.get("coins", 0) + coins
    _save(data)
    return first_time, coins


def debug_unlock_kitchen_endless(player_name):
    """DEBUG ONLY – mark all Kitchen Duty levels complete."""
    from kitchen_level_config import KITCHEN_TOTAL_LEVELS
    data = load_player_data()
    p = _get_player_record(data, player_name)
    if not p:
        return
    progress = p.setdefault("kitchen_duty_progress", {})
    for n in range(1, KITCHEN_TOTAL_LEVELS + 1):
        entry = progress.setdefault(str(n), {"completed": False, "best_score": 0})
        entry["completed"] = True
    _save(data)


def mark_kitchen_tutorial_done(player_name):
    """Flag that this player has completed the Kitchen Duty level-1 tutorial (legacy)."""
    mark_kitchen_level_tutorial_done(player_name, 1)


def is_kitchen_tutorial_done(player_name):
    """Return True if the player has done the Kitchen Duty level-1 tutorial (legacy)."""
    return is_kitchen_level_tutorial_done(player_name, 1)


def mark_kitchen_level_tutorial_done(player_name, level_num):
    """Flag that this player has seen the tutorial for the given kitchen level."""
    data = load_player_data()
    for p in data["players"]:
        if p["name"] == player_name:
            seen = p.get("kitchen_tutorials_done", [])
            # migrate old boolean flag
            if p.get("kitchen_tutorial_done"):
                if 1 not in seen:
                    seen.append(1)
            if level_num not in seen:
                seen.append(level_num)
            p["kitchen_tutorials_done"] = seen
            break
    _save(data)


def is_kitchen_level_tutorial_done(player_name, level_num):
    """Return True if the player has seen the tutorial for the given kitchen level."""
    data = load_player_data()
    p = _get_player_record(data, player_name)
    if not p:
        return False
    seen = p.get("kitchen_tutorials_done", [])
    # migrate old boolean flag for level 1
    if level_num == 1 and p.get("kitchen_tutorial_done"):
        return True
    return level_num in seen


def mark_level_complete(player_name, level_num, score):
    """Mark a level as completed and update best score.

    Returns (first_time, coins_earned):
      first_time   – True if this is the first successful completion
      coins_earned – coins awarded (only on first completion)
    """
    data = load_player_data()
    p = _get_player_record(data, player_name)
    if not p:
        return False, 0
    progress = p.setdefault("bar_duty_progress", {})
    key = str(level_num)
    entry = progress.setdefault(key, {"completed": False, "best_score": 0})
    first_time = not entry.get("completed", False)
    entry["completed"] = True
    entry["best_score"] = max(entry.get("best_score", 0), score)
    coins = (score * 2 + level_num * 10) if first_time else 0
    if first_time and coins > 0:
        p["coins"] = p.get("coins", 0) + coins
    _save(data)
    return first_time, coins


# ── Cafe equipped ──────────────────────────────────────────────────────────────

_DEFAULT_CAFE_EQUIPPED = {
    "floor":           "floor_cherry_wood",
    "kitchen_overlay": None,
    "walls":           "walls_bricks",
    "rugs":            None,
    "tables":          "tables_standardwood",
    "seats":           "seats_standardwood",   # chairs (wood, fabric, stools…)
    "couch":           "seats_orangecouch",    # couch (separate physical spot)
    "barstools":       "seats_barstool_standardwood",  # barstools (separate physical spot)
    "decor":           None,
}

# Item keys that every player owns for free (the standard/default options)
_DEFAULT_OWNED_KEYS = {"floor_cherry_wood", "walls_bricks", "tables_standardwood", "seats_standardwood", "seats_orangecouch", "seats_barstool_standardwood", "decor_rugs", "floor_kitchen_redbeigetiles"}


def get_cafe_equipped(player_name):
    """Return {slot: item_key} for the player's equipped cafe items."""
    data = load_player_data()
    p = _get_player_record(data, player_name)
    if not p:
        return dict(_DEFAULT_CAFE_EQUIPPED)
    return {**_DEFAULT_CAFE_EQUIPPED, **p.get("cafe_equipped", {})}


def set_cafe_equipped(player_name, slot, item_key):
    """Set the equipped item for a slot. Pass item_key=None to unequip (overlay slots only)."""
    data = load_player_data()
    p = _get_player_record(data, player_name)
    if not p:
        return
    p.setdefault("cafe_equipped", {})[slot] = item_key
    _save(data)


def ensure_defaults_owned(player_name):
    """Pre-own all default cafe items so they show as OWNED in the shop."""
    data = load_player_data()
    p = _get_player_record(data, player_name)
    if not p:
        return
    changed = False

    # ── Data migration ────────────────────────────────────────────────────────
    eqp = p.setdefault("cafe_equipped", {})

    # Old saves stored decor_rugs in the generic "decor" slot before the dedicated
    # "rugs" layer was added. Move it to the correct slot so it renders below tables.
    if eqp.get("decor") == "decor_rugs":
        eqp["rugs"]  = "decor_rugs"
        eqp["decor"] = None
        changed = True

    # Old saves had seats_orangecouch in the "seats" slot (before the dedicated
    # "couch" layer slot was added). Move it and restore chairs to "seats".
    if eqp.get("seats") == "seats_orangecouch":
        eqp["couch"] = "seats_orangecouch"
        eqp["seats"] = "seats_standardwood"
        changed = True

    # Ensure every player has a "couch" slot (may be missing on pre-couch saves).
    if "couch" not in eqp:
        eqp["couch"] = "seats_orangecouch"
        changed = True

    # Ensure every player has a "barstools" slot (may be missing on pre-barstool saves).
    if "barstools" not in eqp:
        eqp["barstools"] = "seats_barstool_standardwood"
        changed = True

    # Equip rugs by default for players who never had them set.
    if "rugs" not in eqp:
        eqp["rugs"] = "decor_rugs"
        changed = True

    # Equip kitchen tiles by default for players who never had them set.
    if not eqp.get("kitchen_overlay"):
        eqp["kitchen_overlay"] = "floor_kitchen_redbeigetiles"
        changed = True

    purchases = p.setdefault("purchases", {})
    for key in _DEFAULT_OWNED_KEYS:
        if not purchases.get(key):
            purchases[key] = True
            changed = True
    if changed:
        _save(data)
