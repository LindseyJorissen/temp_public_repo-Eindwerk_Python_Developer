"""
game_settings.py – Persistent settings (music / SFX toggles and volumes).
Stored alongside scores.json in the app data directory.
"""
import json
import os

_DEFAULTS = {
    "music_enabled": True,
    "sfx_enabled":   True,
    "music_volume":  1.0,
    "sfx_volume":    1.0,
    "gyro_enabled":  True,
}

_settings = dict(_DEFAULTS)


def _path():
    try:
        from kivy.app import App
        app = App.get_running_app()
        if app and hasattr(app, "user_data_dir"):
            return os.path.join(app.user_data_dir, "settings.json")
    except Exception:
        pass
    _dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
    os.makedirs(_dir, exist_ok=True)
    return os.path.join(_dir, "settings.json")


def load():
    """Load settings from disk; falls back to defaults on any error."""
    global _settings
    try:
        with open(_path(), "r") as f:
            saved = json.load(f)
        _settings = {**_DEFAULTS, **saved}
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        _settings = dict(_DEFAULTS)
    return _settings


def save():
    """Persist current settings to disk."""
    try:
        with open(_path(), "w") as f:
            json.dump(_settings, f, indent=2)
    except OSError:
        pass


def get(key):
    """Return the current value of a setting (falls back to default)."""
    return _settings.get(key, _DEFAULTS.get(key))


def set_value(key, value):
    """Update a setting and save immediately."""
    _settings[key] = value
    save()
