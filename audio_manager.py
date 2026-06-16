"""
audio_manager.py – Background music manager for the cafe.

Tracks:
  menu    → assets/sounds/mainmenu_cafehub.mp3   (menu + cafe hub + bar duty hub)
  tutorial → assets/sounds/tutorial.mp3          (bar duty tutorial slideshow)
  disco   → assets/sounds/disco.mp3              (Disco Night level, triggered on disco_mode)

Only one track plays at a time.  Calling start_* for the track that is already
playing is a no-op (no restart), so navigating between screens that share the
same music is seamless.
"""

import os
from kivy.core.audio import SoundLoader
import game_settings

_current      = None   # currently loaded SoundLoader instance
_current_path = None   # path of the loaded instance
_btn_wood     = None   # lazily loaded wood button SFX
_typewriter_bell = None   # lazily loaded typewriter bell SFX
_bacon_frying = None   # looping kitchen frying SFX
_bread_sfx    = None   # one-shot bread-placed SFX
_lettuce_sfx       = None
_cloche_sfx        = None
_ding_sfx          = None
_burnt_sfx         = None
_trash_sfx         = None
_stealing_sfx      = None
_victor_running_sfx = None
_tiktok_alarm_sfx       = None
_achievement_unlocked_sfx  = None
_purchase_successful_sfx   = None
_fire_crackling    = None   # looping ambient for cafe hub
_mittens_nogood    = None   # cutscene sfx
_tomato_sfx        = None
_open_door_sfx     = None
_paper_rustling_sfx = None
_onion_sfx         = None
_cheese_sfx        = None


def _sounds_dir():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "sounds")


def _assets_dir():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")


# ── internal ───────────────────────────────────────────────────────────────────

def _play(path, loop=True, volume_scale=1.0):
    """Load and play *path*.  If the same path is already playing, do nothing."""
    global _current, _current_path
    vol = game_settings.get("music_volume") * volume_scale
    if _current_path == path and _current and _current.state == 'play':
        _current.volume = vol
        return  # already playing the right track – just update volume
    if _current and _current.state == 'play':
        _current.stop()
    if _current_path != path or _current is None:
        _current = SoundLoader.load(path)
        _current_path = path
    if _current:
        _current.loop   = loop
        _current.volume = vol
        if _current.state != 'play':
            _current.play()


# ── public API ─────────────────────────────────────────────────────────────────

def start_menu_music():
    """Play the main-menu / cafe-hub track (mainmenu_cafehub.mp3)."""
    if not game_settings.get("music_enabled"):
        return
    _play(os.path.join(_sounds_dir(), "mainmenu_cafehub.mp3"))


def start_game_music(volume_scale=1.0):
    """Play the in-game track (game_music.mp3)."""
    if not game_settings.get("music_enabled"):
        return
    _play(os.path.join(_sounds_dir(), "game_music.mp3"), volume_scale=volume_scale)


def start_tutorial_music():
    """Play the bar-duty tutorial track (tutorial.mp3)."""
    if not game_settings.get("music_enabled"):
        return
    _play(os.path.join(_sounds_dir(), "tutorial.mp3"))


def start_disco_music():
    """Play the disco level track (disco.mp3)."""
    if not game_settings.get("music_enabled"):
        return
    _play(os.path.join(_sounds_dir(), "disco.mp3"))


def play_button_wood():
    """Play the wood button click SFX (one-shot, respects sfx settings)."""
    global _btn_wood
    if not game_settings.get("sfx_enabled"):
        return
    if _btn_wood is None:
        _btn_wood = SoundLoader.load(os.path.join(_sounds_dir(), "button_wood.mp3"))
    if _btn_wood:
        _btn_wood.volume = game_settings.get("sfx_volume")
        _btn_wood.play()


def play_typewriter_bell():
    """Play the typewriter bell SFX (one-shot, respects sfx settings)."""
    global _typewriter_bell
    if not game_settings.get("sfx_enabled"):
        return
    if _typewriter_bell is None:
        _typewriter_bell = SoundLoader.load(os.path.join(_sounds_dir(), "typewriter_bell.mp3"))
    if _typewriter_bell:
        _typewriter_bell.volume = game_settings.get("sfx_volume")
        _typewriter_bell.play()


def play_bread():
    """Play the bread-placed SFX (one-shot, respects sfx settings)."""
    global _bread_sfx
    if not game_settings.get("sfx_enabled"):
        return
    if _bread_sfx is None:
        _bread_sfx = SoundLoader.load(os.path.join(_sounds_dir(), "bread.mp3"))
    if _bread_sfx:
        _bread_sfx.volume = min(1.0, game_settings.get("sfx_volume") * 3.0)
        _bread_sfx.play()


def start_bacon_frying():
    """Start looping the bacon/egg frying SFX. No-op if already playing."""
    global _bacon_frying
    if not game_settings.get("sfx_enabled"):
        return
    if _bacon_frying is None:
        _bacon_frying = SoundLoader.load(os.path.join(_sounds_dir(), "bacon_frying.mp3"))
    if _bacon_frying and _bacon_frying.state != 'play':
        _bacon_frying.loop   = True
        _bacon_frying.volume = game_settings.get("sfx_volume") * 0.40
        _bacon_frying.play()


def stop_bacon_frying():
    """Stop the bacon/egg frying SFX loop."""
    global _bacon_frying
    if _bacon_frying and _bacon_frying.state == 'play':
        _bacon_frying.stop()


def stop_music():
    """Stop whatever track is currently playing."""
    global _current
    if _current and _current.state == 'play':
        _current.stop()


def set_music_volume(volume):
    """Update the volume of the currently playing track immediately."""
    if _current:
        _current.volume = max(0.0, min(1.0, volume))


def play_lettuce():
    """Play the ingredient-added SFX (one-shot, respects sfx settings)."""
    global _lettuce_sfx
    if not game_settings.get("sfx_enabled"):
        return
    if _lettuce_sfx is None:
        _lettuce_sfx = SoundLoader.load(os.path.join(_sounds_dir(), "lettuce.mp3"))
    if _lettuce_sfx:
        _lettuce_sfx.volume = game_settings.get("sfx_volume")
        _lettuce_sfx.play()


def play_cloche():
    """Play the cloche/presentation SFX (one-shot, respects sfx settings)."""
    global _cloche_sfx
    if not game_settings.get("sfx_enabled"):
        return
    if _cloche_sfx is None:
        _cloche_sfx = SoundLoader.load(os.path.join(_sounds_dir(), "cloche.mp3"))
    if _cloche_sfx:
        _cloche_sfx.volume = game_settings.get("sfx_volume")
        _cloche_sfx.play()


def play_ding(loud=False):
    """Play the pan-ready ding SFX (one-shot, respects sfx settings).

    loud=True plays at full volume (used for bacon/eggs).
    """
    global _ding_sfx
    if not game_settings.get("sfx_enabled"):
        return
    if _ding_sfx is None:
        _ding_sfx = SoundLoader.load(os.path.join(_sounds_dir(), "ding.mp3"))
    if _ding_sfx:
        mult = 3.0 if loud else 1.5
        _ding_sfx.volume = min(1.0, game_settings.get("sfx_volume") * mult)
        _ding_sfx.play()


def play_trash():
    """Play the trash-chute SFX (one-shot, respects sfx settings)."""
    global _trash_sfx
    if not game_settings.get("sfx_enabled"):
        return
    if _trash_sfx is None:
        _trash_sfx = SoundLoader.load(os.path.join(_sounds_dir(), "trash.mp3"))
    if _trash_sfx:
        _trash_sfx.volume = game_settings.get("sfx_volume")
        _trash_sfx.play()


def play_burnt():
    """Play the burnt food SFX (one-shot, respects sfx settings)."""
    global _burnt_sfx
    if not game_settings.get("sfx_enabled"):
        return
    if _burnt_sfx is None:
        _burnt_sfx = SoundLoader.load(os.path.join(_sounds_dir(), "burnt.mp3"))
    if _burnt_sfx:
        _burnt_sfx.volume = game_settings.get("sfx_volume")
        _burnt_sfx.play()


def play_stealing():
    """Play the cat-stealing SFX (one-shot, respects sfx settings)."""
    global _stealing_sfx
    if not game_settings.get("sfx_enabled"):
        return
    if _stealing_sfx is None:
        _stealing_sfx = SoundLoader.load(os.path.join(_sounds_dir(), "stealing.mp3"))
    if _stealing_sfx:
        _stealing_sfx.volume = game_settings.get("sfx_volume")
        _stealing_sfx.play()


def play_victor_running():
    """Play the Victor-running SFX (one-shot, respects sfx settings)."""
    global _victor_running_sfx
    if not game_settings.get("sfx_enabled"):
        return
    if _victor_running_sfx is None:
        _victor_running_sfx = SoundLoader.load(os.path.join(_sounds_dir(), "victor_running.mp3"))
    if _victor_running_sfx:
        _victor_running_sfx.volume = game_settings.get("sfx_volume")
        _victor_running_sfx.play()


def stop_victor_running():
    """Stop the Victor-running SFX."""
    global _victor_running_sfx
    if _victor_running_sfx and _victor_running_sfx.state == 'play':
        _victor_running_sfx.stop()


def play_tiktok_alarm():
    """Play the end-of-shift ticking alarm (one-shot, respects sfx settings)."""
    global _tiktok_alarm_sfx
    if not game_settings.get("sfx_enabled"):
        return
    if _tiktok_alarm_sfx is None:
        _tiktok_alarm_sfx = SoundLoader.load(os.path.join(_sounds_dir(), "tiktok_alarm.mp3"))
    if _tiktok_alarm_sfx:
        _tiktok_alarm_sfx.volume = game_settings.get("sfx_volume")
        _tiktok_alarm_sfx.play()


def play_achievement_unlocked():
    """Play the achievement-unlocked fanfare (one-shot, respects sfx settings)."""
    global _achievement_unlocked_sfx
    if not game_settings.get("sfx_enabled"):
        return
    if _achievement_unlocked_sfx is None:
        _achievement_unlocked_sfx = SoundLoader.load(
            os.path.join(_sounds_dir(), "achievement_unlocked.mp3")
        )
    if _achievement_unlocked_sfx:
        _achievement_unlocked_sfx.volume = game_settings.get("sfx_volume")
        _achievement_unlocked_sfx.play()


def play_purchase_successful():
    """Play the purchase-successful SFX (one-shot, respects sfx settings)."""
    global _purchase_successful_sfx
    if not game_settings.get("sfx_enabled"):
        return
    if _purchase_successful_sfx is None:
        _purchase_successful_sfx = SoundLoader.load(
            os.path.join(_sounds_dir(), "purchase_succesfull.mp3")
        )
    if _purchase_successful_sfx:
        _purchase_successful_sfx.volume = game_settings.get("sfx_volume")
        _purchase_successful_sfx.play()


def start_fire_crackling():
    """Start looping the fire crackling ambient. No-op if already playing."""
    global _fire_crackling
    if not game_settings.get("sfx_enabled"):
        return
    if _fire_crackling is None:
        _fire_crackling = SoundLoader.load(os.path.join(_sounds_dir(), "fire_crackeling.mp3"))
    if _fire_crackling and _fire_crackling.state != 'play':
        _fire_crackling.loop   = True
        _fire_crackling.volume = game_settings.get("sfx_volume") * 0.30
        _fire_crackling.play()


def stop_fire_crackling():
    """Stop the fire crackling ambient loop."""
    global _fire_crackling
    if _fire_crackling and _fire_crackling.state == 'play':
        _fire_crackling.stop()


def play_mittens_nogood():
    """Play the mittensuptonogood cutscene sound."""
    global _mittens_nogood
    if not _mittens_nogood:
        p = os.path.join(_sounds_dir(), "mittensuptonogood.mp3")
        _mittens_nogood = SoundLoader.load(p)
    if _mittens_nogood and game_settings.get("sfx_enabled"):
        _mittens_nogood.volume = game_settings.get("sfx_volume")
        _mittens_nogood.play()


def stop_mittens_nogood():
    """Stop the mittensuptonogood cutscene sound if playing."""
    global _mittens_nogood
    if _mittens_nogood and _mittens_nogood.state == 'play':
        _mittens_nogood.stop()


def play_tomato():
    """Play the tomato-placed SFX (one-shot, respects sfx settings)."""
    global _tomato_sfx
    if not game_settings.get("sfx_enabled"):
        return
    if _tomato_sfx is None:
        _tomato_sfx = SoundLoader.load(os.path.join(_sounds_dir(), "tomato.mp3"))
    if _tomato_sfx:
        _tomato_sfx.volume = min(1.0, game_settings.get("sfx_volume") * 3.0)
        _tomato_sfx.play()


def play_paper_rustling():
    """Play the paper rustling SFX (one-shot, respects sfx settings)."""
    global _paper_rustling_sfx
    if not game_settings.get("sfx_enabled"):
        return
    if _paper_rustling_sfx is None:
        _paper_rustling_sfx = SoundLoader.load(os.path.join(_sounds_dir(), "paper_rustling.mp3"))
    if _paper_rustling_sfx:
        _paper_rustling_sfx.volume = game_settings.get("sfx_volume")
        _paper_rustling_sfx.play()


def play_onion():
    """Play the onion-placed SFX (one-shot, respects sfx settings)."""
    global _onion_sfx
    if not game_settings.get("sfx_enabled"):
        return
    if _onion_sfx is None:
        _onion_sfx = SoundLoader.load(os.path.join(_sounds_dir(), "onion.mp3"))
    if _onion_sfx:
        _onion_sfx.volume = game_settings.get("sfx_volume")
        _onion_sfx.play()


def play_cheese():
    """Play the cheese-placed SFX (one-shot, respects sfx settings)."""
    global _cheese_sfx
    if not game_settings.get("sfx_enabled"):
        return
    if _cheese_sfx is None:
        _cheese_sfx = SoundLoader.load(os.path.join(_sounds_dir(), "cheese.mp3"))
    if _cheese_sfx:
        _cheese_sfx.volume = game_settings.get("sfx_volume")
        _cheese_sfx.play()


def play_open_door():
    """Play the door-open SFX on the main menu (one-shot, respects sfx settings)."""
    global _open_door_sfx
    if not game_settings.get("sfx_enabled"):
        return
    if _open_door_sfx is None:
        _open_door_sfx = SoundLoader.load(os.path.join(_sounds_dir(), "open_door.mp3"))
    if _open_door_sfx:
        _open_door_sfx.volume = game_settings.get("sfx_volume")
        _open_door_sfx.play()


# ── backward-compat aliases (used by hiring_sheet, settings, etc.) ─────────────

def start_cafe_ambiance():
    start_menu_music()


def stop_cafe_ambiance():
    stop_music()
