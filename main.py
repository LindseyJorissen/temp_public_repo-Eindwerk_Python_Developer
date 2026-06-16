"""
main.py – Entry point for Mittens: the Mischievous Cafe Destroyer (Kivy/Android).

Run on desktop:
    pip install kivy
    python main.py

Build for Android:
    pip install buildozer
    buildozer android debug deploy run
"""

import os
import sys

# ── Windows GL backend ───────────────────────────────────────────────────────
# Use plain sdl2 (OpenGL) instead of angle_sdl2 (GL→DirectX).
# ANGLE caused sRGB gamma washing out all images.  SimpleScreenManager means
# we no longer need ANGLE to avoid the RenderContext pop_state crash.
if sys.platform.startswith("win"):
    os.environ.setdefault("KIVY_GL_BACKEND", "sdl2")

# Ensure the android/ directory is on sys.path so relative imports work
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

# Window config – must happen before Window is created
from kivy.config import Config              # noqa: E402
Config.set("graphics", "multisamples", "0")

# Desktop: simulate a landscape phone screen (1280×720 ≈ 16:9).
# On Android the window always fills the device screen, so this block
# has no effect there (ANDROID_ARGUMENT is set in the Android env).
if not os.environ.get("ANDROID_ARGUMENT"):
    Config.set("graphics", "width",  "1280")
    Config.set("graphics", "height", "720")

from kivy.app import App                    # noqa: E402
from kivy.clock import Clock                # noqa: E402
from kivy.uix.floatlayout import FloatLayout  # noqa: E402
from kivy.uix.label import Label            # noqa: E402
from kivy.core.window import Window         # noqa: E402
from kivy.core.image import Image as CoreImage  # noqa: E402
from kivy.graphics import Color, Rectangle  # noqa: E402

from screens.menu                  import MenuScreen                # noqa: E402
from screens.hiring_sheet          import HiringSheetScreen         # noqa: E402
from screens.cafe_hub              import CafeHubScreen             # noqa: E402
from screens.bar_duty_hub          import BarDutyHubScreen          # noqa: E402
from screens.opponent_select       import OpponentSelectScreen      # noqa: E402
from screens.victor_intro          import VictorIntroScreen         # noqa: E402
from screens.tutorial              import TutorialScreen            # noqa: E402
from screens.gameplay              import GameScreen                # noqa: E402
from screens.level_end             import LevelEndScreen            # noqa: E402
from screens.leaderboard           import LeaderboardScreen         # noqa: E402
from screens.settings              import SettingsScreen            # noqa: E402
from screens.achievements          import AchievementsScreen        # noqa: E402
from screens.shop                  import ShopScreen                 # noqa: E402
from screens.kitchen_duty_hub      import KitchenDutyHubScreen      # noqa: E402
from screens.kitchen_victor_intro  import KitchenVictorIntroScreen  # noqa: E402
from screens.kitchen_gameplay      import KitchenGameScreen         # noqa: E402
from screens.kitchen_level_end     import KitchenLevelEndScreen     # noqa: E402
from screens.kitchen_intro_cutscene import KitchenIntroCutsceneScreen  # noqa: E402
from screens.kitchen_tutorial      import KitchenTutorialScreen        # noqa: E402


# ══════════════════════════════════════════════════════════════════
# LoadingScreen
# ══════════════════════════════════════════════════════════════════
# Shown immediately so there is no black gap between the presplash
# and the first real frame.  Advances a progress bar as each screen
# widget is constructed in the background.

_LOADING_BG_COLOR = (0.0, 0.0, 0.0, 1.0)          # pure black
_LOADING_FONT     = os.path.join(_HERE, "assets", "fonts", "Pixelfont.ttf")
_LOADING_BG_IMAGE = os.path.join(_HERE, "assets", "loading_screen.png")


class _LoadingScreen(FloatLayout):

    def __init__(self, total, **kwargs):
        self.name    = kwargs.pop("name", "_loading")
        self.manager = None
        super().__init__(**kwargs)
        self._total  = total
        self._loaded = 0

        # Optional background image (drop assets/screens/loading_screen.png to use it)
        self._bg_tex = None
        if os.path.isfile(_LOADING_BG_IMAGE):
            try:
                self._bg_tex = CoreImage(_LOADING_BG_IMAGE).texture
            except Exception:
                pass

        with self.canvas.before:
            Color(*_LOADING_BG_COLOR)
            self._bg_rect = Rectangle(pos=self.pos, size=self.size)
            if self._bg_tex:
                Color(1, 1, 1, 1)
                self._img_rect = Rectangle(texture=self._bg_tex)
            else:
                self._img_rect = None

        with self.canvas:
            Color(0.3, 0.3, 0.3, 1)            # dark grey track
            self._track = Rectangle()
            Color(1.0, 1.0, 1.0, 1)            # white fill
            self._fill  = Rectangle()

        self._lbl = Label(
            text="LOADING...",
            font_name=_LOADING_FONT,
            font_size="14sp",
            color=(1.0, 1.0, 1.0, 1),
            size_hint=(None, None),
            size=(300, 24),
        )
        self.add_widget(self._lbl)
        self.bind(pos=self._redraw, size=self._redraw)

    def advance(self):
        self._loaded += 1
        self._redraw()

    def _redraw(self, *_):
        w, h = self.size
        x, y = self.pos

        self._bg_rect.pos  = (x, y)
        self._bg_rect.size = (w, h)

        if self._img_rect is not None and self._bg_tex:
            # Fill width, crop top/bottom to maintain aspect ratio
            tw, th   = self._bg_tex.size
            scale    = w / tw if tw > 0 else 1
            scaled_h = th * scale
            if scaled_h >= h:
                crop_v = (scaled_h - h) / (2 * scaled_h)
                self._img_rect.tex_coords = (0.0, 1.0 - crop_v, 1.0, 1.0 - crop_v,
                                             1.0, crop_v,        0.0, crop_v)
                self._img_rect.pos  = (x, y)
                self._img_rect.size = (w, h)
            else:
                ry = y + (h - scaled_h) / 2
                self._img_rect.tex_coords = (0.0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0)
                self._img_rect.pos  = (x, ry)
                self._img_rect.size = (w, scaled_h)

        bar_w = max(w * 0.55, 200)
        bar_h = 12
        bx    = x + (w - bar_w) / 2
        by    = y + h * 0.10       # near the bottom so a BG image shows above it

        self._track.pos  = (bx, by)
        self._track.size = (bar_w, bar_h)

        frac = self._loaded / max(self._total, 1)
        self._fill.pos   = (bx, by)
        self._fill.size  = (bar_w * frac, bar_h)

        self._lbl.size = (bar_w, 24)
        self._lbl.pos  = (bx, by + bar_h + 10)


# ══════════════════════════════════════════════════════════════════
# SimpleScreenManager
# ══════════════════════════════════════════════════════════════════
# Kivy 2.3.1's ScreenManager creates a RenderContext for its canvas
# (required for animated transitions).  That RenderContext causes a
# pop_state IndexError on OpenGL ES 3.2 / ANGLE and on some AMD GLEW
# setups.  This plain FloatLayout switcher has NO RenderContext and
# NO transitions – it just swaps widgets in/out of the tree.
# The public API (.current, .get_screen()) matches ScreenManager so
# all existing screen code works without changes.

class SimpleScreenManager(FloatLayout):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._registry = {}   # name → screen widget
        self._current  = None

    # ── ScreenManager-compatible API ─────────────────────────────

    @property
    def current(self):
        return self._current

    @current.setter
    def current(self, name):
        if name == self._current:
            return
        # Tear down old screen
        old = self._registry.get(self._current)
        if old:
            if hasattr(old, "on_leave"):
                old.on_leave()
            super().remove_widget(old)
        # Set up new screen
        self._current = name
        new = self._registry.get(name)
        if new:
            new.manager = self
            super().add_widget(new)
            if hasattr(new, "on_enter"):
                new.on_enter()

    def get_screen(self, name):
        return self._registry[name]

    # ── Widget registration ───────────────────────────────────────

    def add_widget(self, widget, *args, **kwargs):
        """Register a named screen; only the first is shown immediately."""
        name = getattr(widget, "name", None)
        if name:
            widget.manager = self
            self._registry[name] = widget
            if self._current is None:
                # First registered screen becomes current
                self._current = name
                super().add_widget(widget, *args, **kwargs)
                if hasattr(widget, "on_enter"):
                    widget.on_enter()
            # All other screens are held off-tree until navigated to
        else:
            super().add_widget(widget, *args, **kwargs)

    def remove_widget(self, widget, *args, **kwargs):
        if widget in self.children:
            super().remove_widget(widget, *args, **kwargs)


# ══════════════════════════════════════════════════════════════════
# App
# ══════════════════════════════════════════════════════════════════

class MittensApp(App):

    def build(self):
        Window.clearcolor = (0.149, 0.078, 0.027, 1)  # #261407 – matches presplash bg
        Window.softinput_mode = "below_target"
        Window.bind(on_keyboard=self._on_keyboard)

        # Ordered list of (ScreenClass, name) to build lazily after the first frame.
        self._screen_queue = [
            (MenuScreen,                "menu"),
            (HiringSheetScreen,         "hiring_sheet"),
            (CafeHubScreen,             "cafe_hub"),
            (BarDutyHubScreen,          "bar_duty_hub"),
            (OpponentSelectScreen,      "opponent_select"),
            (VictorIntroScreen,         "victor_intro"),
            (TutorialScreen,            "tutorial"),
            (GameScreen,                "game"),
            (LevelEndScreen,            "level_end"),
            (LeaderboardScreen,         "leaderboard"),
            (SettingsScreen,            "settings"),
            (AchievementsScreen,        "achievements"),
            (ShopScreen,                "shop"),
            (KitchenDutyHubScreen,      "kitchen_duty_hub"),
            (KitchenVictorIntroScreen,  "kitchen_victor_intro"),
            (KitchenGameScreen,         "kitchen_gameplay"),
            (KitchenLevelEndScreen,     "kitchen_level_end"),
            (KitchenIntroCutsceneScreen, "kitchen_intro_cutscene"),
            (KitchenTutorialScreen,     "kitchen_tutorial"),
        ]

        sm = SimpleScreenManager()
        self._loading = _LoadingScreen(total=len(self._screen_queue), name="_loading")
        sm.add_widget(self._loading)
        Clock.schedule_once(self._load_next, 0)
        return sm

    def _load_next(self, dt):
        """Build one screen per frame so the loading bar stays visible."""
        if not self._screen_queue:
            self.root.current = "menu"
            return
        cls, name = self._screen_queue.pop(0)
        self.root.add_widget(cls(name=name))
        self._loading.advance()
        Clock.schedule_once(self._load_next, 0)

    def _on_keyboard(self, window, key, *args):
        """Android back button (27) and desktop Escape."""
        if key == 27:
            sm = self.root
            cur = sm.current
            # ── Bar Duty navigation ───────────────────────────────
            if cur in ("victor_intro", "level_end", "kitchen_intro_cutscene"):
                sm.current = "bar_duty_hub"
            elif cur == "bar_duty_hub":
                sm.current = "cafe_hub"
            elif cur in ("opponent_select", "tutorial"):
                sm.current = "bar_duty_hub"
            elif cur == "game":
                sm.current = "bar_duty_hub"
            # ── Kitchen Duty navigation ───────────────────────────
            elif cur == "kitchen_duty_hub":
                sm.current = "cafe_hub"
            elif cur in ("kitchen_victor_intro", "kitchen_level_end", "kitchen_tutorial"):
                sm.current = "kitchen_duty_hub"
            elif cur == "kitchen_gameplay":
                kg = sm.get_screen("kitchen_gameplay")
                if kg._game_widget:
                    kg._game_widget.stop()
                sm.current = "kitchen_duty_hub"
            # ── Shared hubs ───────────────────────────────────────
            elif cur in ("leaderboard", "settings", "achievements", "cafe_hub", "hiring_sheet"):
                sm.current = "menu"
            else:
                self.stop()
            return True


if __name__ == "__main__":
    MittensApp().run()
