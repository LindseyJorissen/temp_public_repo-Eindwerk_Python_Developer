"""
screens/achievements.py – Achievements & coins display screen.

Shows all 14 achievements in a scrollable list.
Unlocked achievements are highlighted; locked ones are dimmed.
Progress bars shown for cumulative grind goals.
"""

import os

import audio_manager
from kivy.uix.floatlayout  import FloatLayout
from kivy.uix.scrollview   import ScrollView
from kivy.uix.gridlayout   import GridLayout
from kivy.uix.label        import Label
from kivy.uix.widget       import Widget
from kivy.graphics         import Color, Rectangle, RoundedRectangle, Line
from kivy.core.image       import Image as CoreImage
from kivy.clock            import Clock

from game_constants        import COLOR_BG, COLOR_GOLD, COLOR_WHITE, DEBUG_HITBOXES
from game_utils            import get_current_player, get_player_stats, get_player_coins, fsp
from achievements          import ACHIEVEMENTS, ACHIEVEMENT_ORDER
from screens.leaderboard   import _BackButton

_ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets")
_FONT   = os.path.join(_ASSETS, "fonts", "Pixelfont.ttf")
_BG_IMG = os.path.join(_ASSETS, "screens", "achievements_background.png")

# ── Colour palette ─────────────────────────────────────────────────────────────
_C_BG        = COLOR_BG                    # dark bar background
_C_PANEL     = (0.16, 0.09, 0.04, 1)      # card background (unlocked)
_C_PANEL_LK  = (0.10, 0.06, 0.03, 1)      # card background (locked)
_C_GOLD      = COLOR_GOLD                  # gold accent
_C_DIM       = (0.45, 0.35, 0.25, 1)      # dimmed text / locked tint
_C_WHITE     = (1.0,  1.0,  1.0,  1)
_C_BAR_FILL  = (0.85, 0.65, 0.10, 1)      # progress bar fill
_C_BAR_BG    = (0.22, 0.14, 0.06, 1)      # progress bar track


# ── Art-card achievements (key → (done_img, locked_img)) ──────────────────────
_ART_DIR = os.path.join(_ASSETS, "achievements_art")
_ART_CARDS = {
    "first_round":            ("firstroundsonme_done.png",       "firstroundsonme_locked.png"),
    "on_the_clock":           ("ontheclock_done.png",            "ontheclock_locked.png"),
    "disco_fever":            ("discofever_done.png",            "discofever_locked.png"),
    "drunk_on_the_job":       ("drunkonthejob_done.png",         "drunkonthejob_locked.png"),
    "no_spills":              ("nospills_done.png",              "nospills_locked.png"),
    "pest_control":           ("pestcontrol_done.png",           "pestcontrol_locked.png"),
    "shaky_hands":            ("shakyhands_done.png",            "shakyhands_locked.png"),
    "rookie_waiter":          ("rookiewaiter_done.png",          "rookiewaiter_locked.png"),
    "veteran_bartender":      ("veteranbartender_done.png",      "veteranbartender_locked.png"),
    "whole_damn_menu":        ("thewholedamnmenu_done.png",      "thewholedamnmenu_locked.png"),
    "chili_survivor":         ("chilisurvivor_done.png",         "chilisurvivor_locked.png"),
    "hector_tamer":           ("hectortamer_done.png",           "hectortamer_locked.png"),
    "glutton_for_punishment": ("gluttonforpunishment_done.png",  "gluttonforpunishment_locked.png"),
    "catastrophic":           ("catastrophic_done.png",          "catastrophic_locked.png"),
    "bar_survivor":           ("barsurvivor_done.png",           "barsurvivor_locked.png"),
    "kitchen_mise_en_place":  ("miseenplace_done.png",           "miseenplace_locked.png"),
    "kitchen_head_chef":      ("headchef_done.png",              "headchef_locked.png"),
    "kitchen_iron_chef":      ("ironchef_done.png",              "ironchef_locked.png"),
    "kitchen_long_shift":     ("thelongshift_done.png",          "thelongshift_locked.png"),
    "kitchen_closing_time":   ("closingtime_done.png",           "closingtime_locked.png"),
    "kitchen_mittens_buffet": ("mittensbuffet_done.png",         "mittensbuffet_locked.png"),
}
_ART_ASPECT = 3915 / 495    # width / height of the card art


# ══════════════════════════════════════════════════════════════════
# _ArtAchievementCard – full-image card for hand-drawn achievements
# ══════════════════════════════════════════════════════════════════

class _ArtAchievementCard(Widget):
    """Displays a hand-drawn achievement card image (done or locked variant).
    Height auto-adjusts to preserve the image aspect ratio."""

    def __init__(self, key, unlocked, **kwargs):
        kwargs.setdefault("size_hint", (1, None))
        kwargs.setdefault("height", 200)
        super().__init__(**kwargs)
        done_file, locked_file = _ART_CARDS[key]
        img_file = done_file if unlocked else locked_file
        path = os.path.join(_ART_DIR, img_file)
        try:
            self._tex = CoreImage(path).texture
        except Exception:
            self._tex = None
        self.bind(pos=self._redraw, size=self._on_size)

    def _on_size(self, *_):
        if self.width > 0:
            self.height = self.width / _ART_ASPECT
        self._redraw()

    def _redraw(self, *_):
        self.canvas.clear()
        if not self._tex or self.width == 0 or self.height == 0:
            return
        with self.canvas:
            Color(1, 1, 1, 1)
            Rectangle(texture=self._tex, pos=self.pos, size=self.size)


# ══════════════════════════════════════════════════════════════════
# _AchievementCard – one row in the scroll list
# ══════════════════════════════════════════════════════════════════

class _AchievementCard(Widget):
    """Draws a single achievement card onto its canvas."""

    _HEIGHT = 130   # px

    def __init__(self, key, unlocked, progress=None, target=None, **kwargs):
        kwargs.setdefault("size_hint", (1, None))
        kwargs.setdefault("height", self._HEIGHT)
        super().__init__(**kwargs)

        self._key      = key
        self._unlocked = unlocked
        self._progress = progress   # current value (int) or None
        self._target   = target     # target value (int) or None

        info  = ACHIEVEMENTS[key]
        self._name  = info["name"].upper()
        self._desc  = info["desc"]
        self._coins = info["coins"]

        self.bind(pos=self._redraw, size=self._redraw)

    def _redraw(self, *_):
        self.canvas.clear()
        x, y, w, h = self.x, self.y, self.width, self.height
        pad      = 14
        unlocked = self._unlocked

        with self.canvas:
            # ── Card background ────────────────────────────────
            Color(*(_C_PANEL if unlocked else _C_PANEL_LK))
            RoundedRectangle(pos=(x + 4, y + 4), size=(w - 8, h - 8), radius=[12])

            # ── Border ─────────────────────────────────────────
            if unlocked:
                Color(*_C_GOLD[:3], 0.9)
            else:
                Color(*_C_DIM[:3], 0.4)
            Line(rounded_rectangle=(x + 4, y + 4, w - 8, h - 8, 12), width=2)

            # ── Progress bar (cumulative achievements only) ─────
            if self._target is not None and not unlocked:
                prog  = min(self._progress or 0, self._target)
                frac  = prog / self._target
                bar_x = x + pad
                bar_y = y + 14
                bar_w = w - pad * 2
                bar_h = 11
                Color(*_C_BAR_BG)
                RoundedRectangle(pos=(bar_x, bar_y), size=(bar_w, bar_h), radius=[5])
                if frac > 0:
                    Color(*_C_BAR_FILL)
                    RoundedRectangle(
                        pos=(bar_x, bar_y),
                        size=(max(bar_h, bar_w * frac), bar_h),
                        radius=[5],
                    )

        self._refresh_labels()

    def _refresh_labels(self):
        for child in list(self.children):
            self.remove_widget(child)

        x, y, w, h = self.x, self.y, self.width, self.height
        pad      = 18
        right_w  = 100          # width of the right-hand info column
        left_w   = w - pad * 2 - right_w - 8
        unlocked = self._unlocked
        name_col = _C_GOLD  if unlocked else _C_DIM
        desc_col = _C_WHITE if unlocked else _C_DIM
        has_bar  = self._target is not None and not unlocked

        # ── Achievement name (pixel font, larger) ──
        self.add_widget(Label(
            text=self._name,
            font_name=_FONT, font_size=fsp(18), bold=True,
            color=name_col,
            size_hint=(None, None), size=(left_w, 34),
            pos=(x + pad, y + h - 46),
            halign="left", valign="middle",
            text_size=(left_w, 34),
        ))

        # ── Description ──
        self.add_widget(Label(
            text=self._desc.upper(),
            font_name=_FONT, font_size=fsp(14),
            color=desc_col,
            size_hint=(None, None), size=(left_w, 28),
            pos=(x + pad, y + h - 82),
            halign="left", valign="middle",
            text_size=(left_w, 28),
        ))

        # ── Progress text (cumulative, locked) ──
        if has_bar and self._progress is not None:
            self.add_widget(Label(
                text=f"{self._progress:,} / {self._target:,}",
                font_name=_FONT, font_size=fsp(13),
                color=_C_DIM,
                size_hint=(None, None), size=(left_w, 22),
                pos=(x + pad, y + 32),
                halign="left", valign="middle",
                text_size=(left_w, 22),
            ))

        # ── Status badge (right side, upper) ──
        badge_text = "DONE"  if unlocked else "LOCKED"
        badge_col  = _C_GOLD if unlocked else _C_DIM
        self.add_widget(Label(
            text=badge_text,
            font_name=_FONT, font_size=fsp(14), bold=True,
            color=badge_col,
            size_hint=(None, None), size=(right_w, 28),
            pos=(x + w - right_w - 10, y + h - 46),
            halign="center", valign="middle",
            text_size=(right_w, 28),
        ))

        # ── Coin reward (right side, lower) ──
        self.add_widget(Label(
            text=f"+{self._coins} COINS",
            font_name=_FONT, font_size=fsp(14),
            color=_C_GOLD if unlocked else _C_DIM,
            size_hint=(None, None), size=(right_w, 28),
            pos=(x + w - right_w - 10, y + h - 80),
            halign="center", valign="middle",
            text_size=(right_w, 28),
        ))


# ══════════════════════════════════════════════════════════════════
# AchievementsScreen
# ══════════════════════════════════════════════════════════════════

class AchievementsScreen(FloatLayout):

    def __init__(self, **kwargs):
        self.name    = kwargs.pop("name", "achievements")
        self.manager = None
        super().__init__(**kwargs)
        self._coins_lbl  = None
        self._scroll     = None
        self._card_grid  = None
        self._build_ui()
        self.bind(size=self._reposition, pos=self._reposition)

    # ── Build ──────────────────────────────────────────────────────

    def _update_bg_img(self):
        """Recompute the background image rect: fit-to-width, centred vertically."""
        if not self._bg_tex:
            return
        W, H = self.width, self.height
        if W < 1 or H < 1:
            return
        tw, th = self._bg_tex.size
        dw = W
        dh = W * th / tw
        self._bg_img_rect.texture    = self._bg_tex
        self._bg_img_rect.tex_coords = (0, 1, 1, 1, 1, 0, 0, 0)
        self._bg_img_rect.pos        = (self.x, self.y + (H - dh) / 2)
        self._bg_img_rect.size       = (dw, dh)

    def _build_ui(self):
        # Solid fallback + fit-to-width image (no stretching)
        try:
            self._bg_tex = CoreImage(_BG_IMG).texture
        except Exception:
            self._bg_tex = None
        with self.canvas.before:
            Color(*_C_BG)
            self._bg_rect = Rectangle(pos=self.pos, size=self.size)
            Color(1, 1, 1, 1)
            self._bg_img_rect = Rectangle()
        self.bind(
            size=lambda *_: (
                setattr(self._bg_rect, "size", self.size),
                setattr(self._bg_rect, "pos",  self.pos),
                self._update_bg_img(),
            ),
            pos=lambda *_: (
                setattr(self._bg_rect, "pos", self.pos),
                self._update_bg_img(),
            ),
        )

        # Title
        self._title_lbl = Label(
            text="ACHIEVEMENTS",
            font_name=_FONT, font_size=fsp(32), bold=True,
            color=_C_WHITE,
            size_hint=(None, None), size=(600, 50),
            halign="center",
        )
        self.add_widget(self._title_lbl)

        self._coins_lbl = Label(
            text="COINS: 0",
            font_name=_FONT, font_size=fsp(20), bold=True,
            color=_C_WHITE,
            size_hint=(None, None), size=(300, 36),
            halign="center",
        )
        self.add_widget(self._coins_lbl)

        # Scroll area
        self._card_grid = GridLayout(
            cols=1,
            spacing=6,
            padding=[10, 6, 10, 6],
            size_hint=(1, None),
        )
        self._card_grid.bind(
            minimum_height=self._card_grid.setter("height")
        )

        self._scroll = ScrollView(
            do_scroll_x=False,
            do_scroll_y=True,
            size_hint=(None, None),
            bar_width=6,
            bar_color=list(_C_GOLD[:3]) + [0.7],
            bar_inactive_color=list(_C_GOLD[:3]) + [0.3],
        )
        self._scroll.add_widget(self._card_grid)
        self.add_widget(self._scroll)

        # Back button – same image-based widget used by the leaderboard screen
        self._back_btn = _BackButton(
            callback=self._on_back,
            size_hint=(None, None),
        )
        self.add_widget(self._back_btn)

    # ── Layout ─────────────────────────────────────────────────────

    def _back_zone_to_screen(self):
        """Replicate settings/leaderboard _img_to_screen_box for the BACK button zone."""
        W, H = self.width, self.height
        BG_W, BG_H = 3915, 1773
        l, t, r, b = 69, 1506, 501, 1713
        scale = W / BG_W
        scaled_h = BG_H * scale
        if scaled_h >= H:
            crop_y = (scaled_h - H) / 2
            sy = lambda iy: H - (iy * scale - crop_y)
        else:
            sy = lambda iy: (H + scaled_h) / 2 - iy * scale
        x0 = l * scale
        y_top, y_bot = sy(t), sy(b)
        return x0 + self.x, y_bot + self.y, (r - l) * scale, y_top - y_bot

    def _reposition(self, *_):
        W, H = self.width, self.height
        if W < 2 or H < 2:
            return

        self._update_bg_img()

        # Image rect (fit-to-width, centred vertically) – all content stays inside
        if self._bg_tex:
            tw, th = self._bg_tex.size
            img_h   = W * th / tw
            img_bot = (H - img_h) / 2          # screen y of image bottom edge
            img_top = img_bot + img_h           # screen y of image top edge
        else:
            img_bot = 0
            img_top = H

        x, y, w, h = self._back_zone_to_screen()
        self._back_btn.pos  = (x, y)
        self._back_btn.size = (w, h)

        # Title – pinned to top of image
        self._title_lbl.center_x = self.center_x
        self._title_lbl.top      = img_top - 50

        # Coins – just below title
        self._coins_lbl.center_x = self.center_x
        self._coins_lbl.top      = self._title_lbl.y - 4

        # Scroll area fills the space between coins label and back button
        scroll_top = self._coins_lbl.y - 6
        scroll_bot = self._back_btn.top + 6
        scroll_h   = max(10, scroll_top - scroll_bot)
        scroll_w   = W - 20

        self._scroll.size     = (scroll_w, scroll_h)
        self._scroll.center_x = self.center_x
        self._scroll.y        = scroll_bot

    # ── Data loading ───────────────────────────────────────────────

    def _populate_cards(self):
        self._card_grid.clear_widgets()

        player = get_current_player()
        if not player:
            return

        player_name = player["name"]
        ach_map     = player.get("achievements", {})
        stats       = get_player_stats(player_name)

        for key in ACHIEVEMENT_ORDER:
            info     = ACHIEVEMENTS[key]
            unlocked = bool(ach_map.get(key))

            if key in _ART_CARDS:
                card = _ArtAchievementCard(key=key, unlocked=unlocked)
            else:
                progress = None
                target   = info.get("target")
                if target is not None:
                    stat_key = info.get("stat")
                    progress = stats.get(stat_key, 0) if stat_key else 0
                card = _AchievementCard(
                    key=key,
                    unlocked=unlocked,
                    progress=progress,
                    target=target,
                )
            self._card_grid.add_widget(card)

        # Trigger a layout pass so card heights are correct
        Clock.schedule_once(lambda *_: self._card_grid.do_layout(), 0)

    # ── Navigation ─────────────────────────────────────────────────

    def _on_back(self, *_):
        audio_manager.play_button_wood()
        self.manager.current = "cafe_hub"

    # ── Lifecycle ──────────────────────────────────────────────────

    def on_enter(self):
        player = get_current_player()
        coins  = get_player_coins(player["name"]) if player else 0
        self._coins_lbl.text = f"COINS: {coins:,}"
        self._populate_cards()
        Clock.schedule_once(lambda *_: self._reposition(), 0)

    def on_leave(self):
        pass
