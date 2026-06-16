"""
screens/shop.py – Visual upgrade shop.
Players spend earned coins on cosmetic cafe upgrades.

Tab button zones (_TAB_ZONES) are in shop_background.png source pixels.
Open the image in an editor and update these coordinates to match the art.
"""

import os

import audio_manager
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout  import GridLayout
from kivy.uix.label       import Label
from kivy.uix.widget      import Widget
from kivy.graphics        import Color, Rectangle, RoundedRectangle
from kivy.core.image      import Image as CoreImage
from kivy.core.text       import Label as CoreLabel
from kivy.clock           import Clock

from game_constants import COLOR_BG, COLOR_GOLD, DEBUG_HITBOXES
from game_utils     import (
    get_current_player, get_player_coins,
    get_player_purchases, purchase_shop_item, fsp,
    get_cafe_equipped, set_cafe_equipped, ensure_defaults_owned,
)
_ASSETS       = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets")
_FONT         = os.path.join(_ASSETS, "fonts", "Pixelfont.ttf")
_BG_IMG       = os.path.join(_ASSETS, "screens", "shop_background.png")
_SCREENS_DIR  = os.path.join(_ASSETS, "screens")
_CAFE_HUB_DIR = os.path.join(_ASSETS, "cafe_hub")
_UI_DIR       = os.path.join(_ASSETS, "ui")

_BG_W = 3915
_BG_H = 1773

# ── Colours ───────────────────────────────────────────────────────────────────
_C_BG    = COLOR_BG
_C_GOLD  = COLOR_GOLD
_C_WHITE = (1.0, 1.0, 1.0, 1)
_C_DIM   = (0.45, 0.35, 0.25, 1)
_C_PANEL = (0.16, 0.09, 0.04, 1)
_C_PANEL_LOCKED = (0.10, 0.06, 0.03, 1)
_C_BUY      = (0.18, 0.52, 0.18, 1)
_C_OWNED    = (0.28, 0.18, 0.08, 1)
_C_BROKE    = (0.48, 0.14, 0.10, 1)
_C_USE      = (0.12, 0.35, 0.55, 1)
_C_EQUIPPED = (0.50, 0.35, 0.05, 1)
_C_UNEQUIP  = (0.45, 0.20, 0.10, 1)

# Slots where equipping None is valid (player can remove the item entirely)
_UNEQUIPPABLE_SLOTS = {"rugs", "decor", "kitchen_overlay", "wall_overlay"}

# ── Category tabs ─────────────────────────────────────────────────────────────
_CATEGORIES = ["seats", "tables", "decor", "walls", "floors"]

_TAB_IMGS = {
    "seats":  ("shop_seats.png",          "shop_seats_activated.png"),
    "tables": ("shop_tables.png",         "shop_tables_activate.png"),
    "decor":  ("shop_decor.png",          "shop_decor_activate.png"),
    "walls":  ("shop_walls.png",          "shop_walls_activated.png"),
    "floors": ("shop_floors.png",         "shop_floors_activated.png"),
}

# Tab zones in shop_background.png source image pixels (left, top, right, bottom).
# Tune these once you can see the background art.
_TAB_ZONES = {
    "seats":  (199,  417,  658,  651),
    "tables": (199,  661,  658,  895),
    "decor":  (199,  905,  658, 1139),
    "walls":  (199, 1149,  658, 1383),
    "floors": (199, 1393,  658, 1627),
}

# Back button zone (mirrors achievements / leaderboard placement)
_ZONE_BACK = (69, 1506, 501, 1713)

# Content layout zones in shop_background.png source image pixels (left, top, right, bottom).
# Open shop_background.png in an image editor to tune these.
_ZONE_COINS_LBL  = ( 400, 112,  800,  197)   # coin counter top-left
_ZONE_CARDS_AREA = ( 680, 430, 2700, 1810)   # scrollable card grid
_ZONE_X_BTN      = (3500,  40, 3720,  260)   # close X button top-right (220×220 square)
_ZONE_PREVIEW    = (2314, 311, 3635, 1591)   # live cafe preview panel (right side)
_ZONE_ARROW_L    = (2274, 851, 2424, 1051)   # left  arrow over preview left  edge
_ZONE_ARROW_R    = (3525, 851, 3675, 1051)   # right arrow over preview right edge
_ZONE_ACTION_BTN = (2564, 1480, 3435, 1675)  # action button below preview

# Card column width in background source pixels (3915-px coordinate space).
# At the 1920-px reference screen this produces col_default_width ≈ 175 px.
# Increase to make cards bigger on all screens, decrease to shrink them.
_CARD_W_REF = 440   # card column width in background source pixels; tune to adjust card size on all screens

# Two crop windows inside the cafe_hub source image (3645×1773).
# View 0 = seating area (centre-left), View 1 = kitchen area (right side).
_PREVIEW_CROPS = [
    ( 800,  50, 2150, 1350),   # seating
    (1800,  50, 3150, 1350),   # kitchen
]
_CAFE_HUB_IMG_W    = 3645
_CAFE_HUB_IMG_H    = 1773

_PAGE_SIZE = 6  # items per page (2 rows × 3 cols)

# ── Shop catalogue ─────────────────────────────────────────────────────────────
# Add an "art" key (filename in assets/shop_items/) when per-item images exist.
SHOP_CATALOGUE = {
    "seats": [
        {"key": "seats_orangecouch",            "name": "ORANGE COUCH",      "cost": 0,   "default": True, "asset": "cafe_seats_orangecouch.png"},
        {"key": "seats_velvetgreencouch",        "name": "VELVET GREEN COUCH","cost": 300,                  "asset": "cafe_seats_velvetgreencouch.png"},
        {"key": "seats_standardwood",           "name": "WOOD",              "cost": 0,   "default": True, "asset": "cafe_seats_standardwood.png"},
        {"key": "seats_orangefabric",           "name": "ORANGE FABRIC",     "cost": 200,                  "asset": "cafe_seats_orangefabric.png"},
        {"key": "seats_velvetgreen",            "name": "VELVET GREEN",      "cost": 200,                  "asset": "cafe_seats_velvetgreen.png"},
        {"key": "seats_barstool_standardwood",  "name": "WOOD",              "cost": 0,   "default": True, "asset": "cafe_seats_barstool_standardwood.png"},
        {"key": "seats_barstool_orangefluffy",  "name": "ORANGE FLUFFY",     "cost": 250,                  "asset": "cafe_seats_barstool_orangefluffy.png"},
        {"key": "seats_barstool_woodluxe",      "name": "WOOD LUXE",         "cost": 300,                  "asset": "cafe_seats_barstool_woodluxe.png"},
        {"key": "seats_barstool_velvetgreen",   "name": "VELVET GREEN",      "cost": 250,                  "asset": "cafe_seats_barstool_velvetgreen.png"},
    ],
    "tables": [
        {"key": "tables_standardwood", "name": "WOOD",           "cost": 0,   "default": True, "asset": "cafe_tables_standardwood.png"},
        {"key": "tables_marble",       "name": "MARBLE",         "cost": 300,                  "asset": "cafe_tables_marble.png"},
    ],
    "decor": [
        {"key": "decor_rugs",          "name": "RUGS",           "cost": 0,   "default": True, "asset": "cafe_decor_rugs.png"},
        {"key": "decor_plantset",      "name": "PLANT SET",      "cost": 200,                  "asset": "cafe_decor_plantset.png"},
    ],
    "walls": [
        {"key": "walls_bricks",           "name": "BRICK",          "cost": 0,   "default": True, "asset": "cafe_walls_bricks.png"},
        {"key": "walls_beige",            "name": "PLASTER",        "cost": 200,                  "asset": "cafe_walls_beige.png"},
        {"key": "walls_woodpannel",       "name": "WOOD",           "cost": 350,                  "asset": "cafe_walls_woodpannel.png"},
        {"key": "walls_bartablet_marble", "name": "MARBLE BAR",     "cost": 300,                  "asset": "cafe_walls_bartablet_marble.png"},
    ],
    "floors": [
        {"key": "floor_cherry_wood",           "name": "CHERRY WOOD",   "cost": 0,   "default": True, "asset": "cafe_floor_cherry_wood.png"},
        {"key": "floor_oak_wood",              "name": "OAK WOOD",      "cost": 280,                  "asset": "cafe_floor_oak_wood.png"},
        {"key": "floor_fishbone",              "name": "FISHBONE",      "cost": 350,                  "asset": "cafe_floor_fishbone.png"},
        {"key": "floor_beigetiles",            "name": "BEIGE TILES",   "cost": 250,                  "asset": "cafe_floor_beigetiles.png"},
        {"key": "floor_kitchen_redbeigetiles", "name": "KITCHEN TILES", "cost": 0,   "default": True, "overlay": True, "asset": "cafe_floor_kitchenonly_redbeigetiles.png"},
    ],
}


def _item_slot(item):
    """Return the cafe_equipped slot for an item, or None if not equippable."""
    key = item.get("key", "")
    if key.startswith("floor_"):
        return "kitchen_overlay" if item.get("overlay") else "floor"
    if key.startswith("walls_bartablet"):
        return "wall_overlay"
    if key.startswith("walls_"):
        return "walls"
    if key.startswith("tables_"):
        return "tables"
    # Couch items live in the separate "couch" slot (different cafe spot to chairs)
    if key.endswith("couch") or key.startswith("couch_"):
        return "couch"
    # Barstool items live in their own slot too
    if key.startswith("seats_barstool_") or key.startswith("barstools_"):
        return "barstools"
    if key.startswith("seats_"):
        return "seats"
    if key == "decor_rugs":
        return "rugs"
    if key.startswith("decor_"):
        return "decor"
    return None


# ── _CafePreview ──────────────────────────────────────────────────────────────

class _CafePreview(Widget):
    """Live cropped preview of the cafe layers, updated when the player equips items."""

    # Same slot order as _CafeLayerBg
    _SLOTS = [
        ("floors",  "floor"),
        ("floors",  "kitchen_overlay"),
        ("walls",   "walls"),
        ("walls",   "wall_overlay"),              # bar tablet etc. above walls
        ("decor",   "rugs"),                      # rugs below tables
        ("tables",  "tables"),
        ("seats",   "seats"),                     # chairs
        ("seats",   "couch"),                     # couch (separate cafe spot)
        ("seats",   "barstools"),                 # barstools (separate cafe spot)
        (None,      "cafe_solid_standard.png"),   # permanent
        (None,      "fireplace1.png"),            # fireplace (static frame in preview)
        (None,      "cafe_cat1.png"),                    # cafe cat (static frame in preview)
        (None,      "cafe_couple_drinking1.png"),      # cafe couple (static frame in preview)
        (None,      "cat_scratching1.png"),           # cat scratching (static frame in preview)
        ("decor",   "decor"),
        (None,      "background_and_ui.png"),     # permanent
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._texes    = []
        self._crop_idx = 0
        self.bind(pos=self._draw, size=self._draw)

    def _load(self, filename):
        if not filename:
            return None
        p = os.path.join(_CAFE_HUB_DIR, filename)
        try:
            return CoreImage(p).texture if os.path.isfile(p) else None
        except Exception:
            return None

    def _crop_coords(self):
        l, t, r, b = _PREVIEW_CROPS[self._crop_idx]
        u0    = l / _CAFE_HUB_IMG_W
        u1    = r / _CAFE_HUB_IMG_W
        v_top = 1.0 - t / _CAFE_HUB_IMG_H
        v_bot = 1.0 - b / _CAFE_HUB_IMG_H
        return (u0, v_top, u1, v_top, u1, v_bot, u0, v_bot)

    def set_crop(self, idx):
        self._crop_idx = idx % len(_PREVIEW_CROPS)
        self._draw()

    def refresh(self, player_name=None, preview_item=None):
        """Reload textures from equipped items.

        If *preview_item* is given its slot is temporarily overridden so the
        player can see what an unowned item looks like before buying it.
        """
        equipped = get_cafe_equipped(player_name) if player_name else {}
        if preview_item is not None:
            slot = _item_slot(preview_item)
            if slot:
                equipped = dict(equipped)
                equipped[slot] = preview_item["key"]

        def find_asset(cat, key):
            for item in SHOP_CATALOGUE.get(cat, []):
                if item["key"] == key:
                    return item.get("asset")
            return None

        self._texes = []
        for cat, slot in self._SLOTS:
            if cat is None:
                self._texes.append(self._load(slot))
            else:
                key = equipped.get(slot)
                self._texes.append(self._load(find_asset(cat, key) or "") if key else None)
        self._draw()

    def _draw(self, *_):
        self.canvas.clear()
        if self.width == 0 or self.height == 0:
            return
        coords = self._crop_coords()
        with self.canvas:
            for tex in self._texes:
                if tex is not None:
                    Color(1, 1, 1, 1)
                    r = Rectangle(texture=tex, pos=self.pos, size=self.size)
                    r.tex_coords = coords


# ── _XButton ──────────────────────────────────────────────────────────────────

class _XButton(Widget):
    """Top-right close button using X_button.png assets."""

    def __init__(self, callback, **kwargs):
        super().__init__(**kwargs)
        self._callback = callback
        self._pressed  = False
        self._tex_n = self._tex_d = None
        _kb = os.path.join(_ASSETS, "keyboard buttons")
        for attr, name in (
            ("_tex_n", "X_button.png"),
            ("_tex_d", "X_button_pressed.png"),
        ):
            path = os.path.join(_kb, name)
            if os.path.isfile(path):
                try:
                    setattr(self, attr, CoreImage(path).texture)
                except Exception:
                    pass
        self.bind(pos=self._redraw, size=self._redraw)

    def _redraw(self, *_):
        self.canvas.clear()
        if not DEBUG_HITBOXES:
            return
        with self.canvas:
            Color(1.0, 0.2, 0.8, 0.4)
            Rectangle(pos=self.pos, size=self.size)

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            touch.grab(self)
            self._pressed = True
            self._redraw()
            return True
        return super().on_touch_down(touch)

    def on_touch_up(self, touch):
        if touch.grab_current is self:
            touch.ungrab(self)
            was_inside = self.collide_point(*touch.pos)
            self._pressed = False
            self._redraw()
            if was_inside:
                self._callback()
            return True
        return super().on_touch_up(touch)


# ── _PreviewArrow ─────────────────────────────────────────────────────────────

class _PreviewArrow(Widget):
    """Left/right arrow button using arrow images from assets/ui/."""

    def __init__(self, direction, callback, **kwargs):
        super().__init__(**kwargs)
        self._callback = callback
        self._pressed  = False
        name_n = "left_arrow.png"         if direction == "left" else "right_arrow.png"
        name_p = "left_arrow_clicked.png" if direction == "left" else "right_arrow_clicked.png"
        self._tex_n = self._load(name_n)
        self._tex_p = self._load(name_p)
        self.bind(pos=self._draw, size=self._draw)

    def _load(self, name):
        p = os.path.join(_UI_DIR, name)
        try:
            return CoreImage(p).texture if os.path.isfile(p) else None
        except Exception:
            return None

    def _draw(self, *_):
        self.canvas.clear()
        if self.width == 0 or self.height == 0:
            return
        tex = self._tex_p if self._pressed else self._tex_n
        if tex:
            with self.canvas:
                Color(1, 1, 1, 1)
                Rectangle(texture=tex, pos=self.pos, size=self.size)

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            touch.grab(self)
            self._pressed = True
            self._draw()
            return True
        return super().on_touch_down(touch)

    def on_touch_up(self, touch):
        if touch.grab_current is self:
            touch.ungrab(self)
            was_inside = self.collide_point(*touch.pos)
            self._pressed = False
            self._draw()
            if was_inside:
                self._callback()
            return True
        return super().on_touch_up(touch)


# ── _TabButton ────────────────────────────────────────────────────────────────

class _TabButton(Widget):
    """Renders a category tab button, switching between normal and activated art."""

    def __init__(self, category, callback, **kwargs):
        super().__init__(**kwargs)
        self._category = category
        self._callback = callback
        self._active   = False
        self._tex_n = self._tex_a = None

        normal_file, active_file = _TAB_IMGS[category]
        for attr, fname in (("_tex_n", normal_file), ("_tex_a", active_file)):
            path = os.path.join(_SCREENS_DIR, fname)
            if os.path.isfile(path):
                try:
                    setattr(self, attr, CoreImage(path).texture)
                except Exception:
                    pass

        # Pre-render text as a texture so it draws reliably on canvas
        cl = CoreLabel(text=category.upper(), font_name=_FONT, font_size=36, bold=True)
        cl.refresh()
        self._lbl_tex = cl.texture

        self.bind(pos=self._draw, size=self._draw)

    def set_active(self, active):
        self._active = active
        self._draw()

    def _draw(self, *_):
        if self.width == 0 or self.height == 0:
            return
        tex = self._tex_a if self._active else self._tex_n
        self.canvas.clear()
        with self.canvas:
            Color(1, 1, 1, 1)
            if tex:
                Rectangle(texture=tex, pos=self.pos, size=self.size)
            if self._lbl_tex:
                col = _C_GOLD if self._active else _C_WHITE
                Color(*col)
                tw, th = self._lbl_tex.size
                tx = self.x + (self.width  - tw) / 2 + 18
                ty = self.y + (self.height - th) / 2
                Rectangle(texture=self._lbl_tex, pos=(tx, ty), size=(tw, th))

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self._callback(self._category)
            return True
        return super().on_touch_down(touch)


# ── _ItemCard ─────────────────────────────────────────────────────────────────

class _ItemCard(Widget):
    """A single shop item card. Tapping the card selects/previews it."""

    _HEIGHT = 235

    def __init__(self, item, owned, equipped=False, selected=False, can_afford=True, on_select=None, **kwargs):
        kwargs.setdefault("size_hint", (1, None))
        kwargs.setdefault("height", self._HEIGHT)
        super().__init__(**kwargs)
        self._item        = item
        self._owned       = owned
        self._equipped    = equipped
        self._selected    = selected
        self._can_afford  = can_afford
        self._on_select   = on_select
        self._card_tex, self._card_tex_grey = self._load_card_texes()
        self._owned_overlay_tex = self._try_load_tex("owned_overlay.png")
        self.bind(pos=self._redraw, size=self._redraw)

    def _load_card_texes(self):
        asset = self._item.get("asset")
        if not asset:
            return None, None
        stem, ext = os.path.splitext(asset)
        tex_n = self._try_load_tex("card_" + asset)
        tex_g = self._try_load_tex("card_" + stem + "_grey" + ext)
        return tex_n, tex_g

    def _try_load_tex(self, filename):
        path = os.path.join(_CAFE_HUB_DIR, filename)
        try:
            return CoreImage(path).texture if os.path.isfile(path) else None
        except Exception:
            return None

    def set_selected(self, selected):
        self._selected = selected
        self._redraw()

    def _redraw(self, *_):
        self.canvas.clear()
        x, y, w, h = self.x, self.y, self.width, self.height
        use_grey = (self._card_tex_grey is not None
                    and not self._owned and not self._can_afford)
        use_tex  = self._card_tex_grey if use_grey else self._card_tex
        # dim unowned-but-affordable cards; grey cards and owned/equipped are full opacity
        card_alpha = 1.0 if (self._owned or not self._can_afford) else 0.5
        with self.canvas:
            if use_tex:
                Color(1, 1, 1, card_alpha)
                Rectangle(texture=use_tex, pos=(x + 4, y + 4), size=(w - 8, h - 8))
            else:
                Color(*(_C_PANEL if self._owned else _C_PANEL_LOCKED))
                RoundedRectangle(pos=(x + 4, y + 4), size=(w - 8, h - 8), radius=[10])

            # Owned overlay on top of card art
            if self._owned and self._owned_overlay_tex:
                Color(1, 1, 1, 1)
                Rectangle(texture=self._owned_overlay_tex, pos=(x + 4, y + 4), size=(w - 8, h - 8))

            # Selection border
            if self._selected:
                Color(*_C_GOLD)
                Rectangle(pos=(x,         y + h - 4), size=(w, 4))   # top
                Rectangle(pos=(x,         y),         size=(w, 4))   # bottom
                Rectangle(pos=(x,         y),         size=(4, h))   # left
                Rectangle(pos=(x + w - 4, y),         size=(4, h))   # right

        for child in list(self.children):
            self.remove_widget(child)

        # Scale all internal dimensions relative to the base design height (235)
        s       = h / 235
        pad     = max(4, int(10 * s))
        inner_w = max(1, w - pad * 2)

        # Name label at top
        name_h      = max(20, int(56 * s))
        name_offset = max(name_h + 4, int(68 * s))
        name_w      = max(1, w - 8)
        self.add_widget(Label(
            text=self._item["name"],
            font_name=_FONT, font_size=max(8, int(26 * s)), bold=True,
            color=_C_GOLD if self._owned else _C_WHITE,
            size_hint=(None, None), size=(name_w, name_h),
            pos=(x + 4, y + h - name_offset),
            halign="center", valign="top",
            text_size=(name_w, name_h),
        ))

        # Status label at bottom: price (unowned) or OWNED / EQUIPPED
        if self._equipped:
            status_text  = "EQUIPPED"
            status_color = _C_GOLD
        elif self._owned:
            status_text  = "OWNED"
            status_color = _C_WHITE
        elif self._item.get("default"):
            status_text  = "FREE"
            status_color = _C_GOLD
        else:
            status_text  = f"{self._item['cost']:,} COINS"
            status_color = _C_WHITE

        status_h = max(16, int(30 * s))
        self.add_widget(Label(
            text=status_text,
            font_name=_FONT, font_size=max(6, int(20 * s)),
            color=status_color,
            size_hint=(None, None), size=(inner_w, status_h),
            pos=(x + pad, y + pad + 2),
            halign="center", valign="middle",
            text_size=(inner_w, status_h),
        ))

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            if self._on_select:
                self._on_select(self._item)
            return True
        return super().on_touch_down(touch)


# ── _ActionButton ─────────────────────────────────────────────────────────────

class _ActionButton(Widget):
    """Single action button shown below the preview (BUY / USE / EQUIPPED / UNEQUIP)."""

    def __init__(self, callback, **kwargs):
        super().__init__(**kwargs)
        self._callback = callback
        self._text    = ""
        self._enabled = False
        self._pressed = False
        self._lbl_tex = None
        self._tex_n   = self._load_tex("multifunctional_button.png")
        self._tex_p   = self._load_tex("multifunctional_button_activated.png")
        self.bind(pos=self._draw, size=self._draw)

    def _load_tex(self, name):
        p = os.path.join(_CAFE_HUB_DIR, name)
        try:
            return CoreImage(p).texture if os.path.isfile(p) else None
        except Exception:
            return None

    def update(self, text, color, enabled):
        self._text    = text
        self._enabled = enabled
        cl = CoreLabel(text=text, font_name=_FONT, font_size=22, bold=True)
        cl.refresh()
        self._lbl_tex = cl.texture
        self._draw()

    def _draw(self, *_):
        self.canvas.clear()
        if self.width == 0 or self.height == 0:
            return
        with self.canvas:
            tex = self._tex_p if self._pressed else self._tex_n
            alpha = 1.0 if self._enabled else 0.45
            if tex:
                Color(1, 1, 1, alpha)
                Rectangle(texture=tex, pos=self.pos, size=self.size)
            else:
                Color(*_C_PANEL_LOCKED, alpha)
                RoundedRectangle(pos=(self.x + 4, self.y + 4),
                                 size=(self.width - 8, self.height - 8),
                                 radius=[12])
            if self._lbl_tex:
                Color(1, 1, 1, alpha)
                tw, th = self._lbl_tex.size
                tx = self.x + (self.width  - tw) / 2
                ty = self.y + (self.height - th) / 2 - 6
                Rectangle(texture=self._lbl_tex, pos=(tx, ty), size=(tw, th))

    def on_touch_down(self, touch):
        if self._enabled and self.collide_point(*touch.pos):
            touch.grab(self)
            self._pressed = True
            self._draw()
            return True
        return super().on_touch_down(touch)

    def on_touch_up(self, touch):
        if touch.grab_current is self:
            touch.ungrab(self)
            was_inside = self.collide_point(*touch.pos)
            self._pressed = False
            self._draw()
            if was_inside:
                self._callback()
            return True
        return super().on_touch_up(touch)


# ── ShopScreen ────────────────────────────────────────────────────────────────

class ShopScreen(FloatLayout):

    def __init__(self, **kwargs):
        self.name    = kwargs.pop("name", "shop")
        self.manager = None
        super().__init__(**kwargs)
        self._active_cat    = "seats"
        self._coins_lbl     = None
        self._card_grid     = None
        self._preview       = None
        self._preview_view  = 0
        self._tab_btns      = {}
        self._bg_tex        = None
        self._selected_item = None   # currently selected/previewed item dict
        self._card_widgets  = []     # list of _ItemCard widgets (same order as grid)
        self._action_btn    = None
        self._card_col_width = 175   # updated in _reposition to match screen scale
        self._card_height    = 235   # updated in _reposition to match screen scale
        self._page           = 0
        self._total_pages    = 1
        self._build_ui()
        self.bind(size=self._reposition, pos=self._reposition)

    # ── Coordinate mapping ────────────────────────────────────────────────────

    def _img_to_screen_box(self, zone):
        """Convert (left, top, right, bottom) in source image pixels to
        (screen_x, screen_y, width, height) in Kivy coords."""
        l, t, r, b = zone
        scr_w, scr_h = self.width, self.height
        if scr_w == 0 or scr_h == 0:
            return 0, 0, 1, 1
        scale    = scr_w / _BG_W
        scaled_h = scale * _BG_H
        sx = lambda ix: ix * scale
        if scaled_h >= scr_h:
            crop_y = (scaled_h - scr_h) / 2
            sy = lambda iy: scr_h - (iy * scale - crop_y)
        else:
            sy = lambda iy: (scr_h + scaled_h) / 2 - iy * scale
        x0, x1       = sx(l), sx(r)
        y_top, y_bot = sy(t), sy(b)
        return x0, y_bot, x1 - x0, y_top - y_bot

    # ── Build ─────────────────────────────────────────────────────────────────

    def _update_bg_img(self):
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

        # Category tab buttons (left column)
        for cat in _CATEGORIES:
            btn = _TabButton(category=cat, callback=self._on_tab, size_hint=(None, None))
            self._tab_btns[cat] = btn
            self.add_widget(btn)

        # Coins display
        self._coins_lbl = Label(
            text="0",
            font_name=_FONT, font_size=44, bold=True,
            color=_C_WHITE,
            size_hint=(None, None), size=(400, 40),
            halign="left",
        )
        self.add_widget(self._coins_lbl)

        # Paged item grid – shows exactly _PAGE_SIZE items (2 rows × 3 cols)
        self._card_grid = GridLayout(
            cols=3, spacing=[14, 8], padding=[10, 2, 10, 6],
            size_hint=(None, None),
            col_force_default=True,
            col_default_width=175,
        )
        self.add_widget(self._card_grid)

        # Page navigation arrows below the card grid
        self._page_prev = _PreviewArrow("left",  self._on_page_prev, size_hint=(None, None))
        self._page_next = _PreviewArrow("right", self._on_page_next, size_hint=(None, None))
        self.add_widget(self._page_prev)
        self.add_widget(self._page_next)

        # Live cafe preview panel
        self._preview = _CafePreview(size_hint=(None, None))
        self.add_widget(self._preview)

        # Preview navigation arrows
        self._arrow_l = _PreviewArrow("left",  self._on_preview_prev, size_hint=(None, None))
        self._arrow_r = _PreviewArrow("right", self._on_preview_next, size_hint=(None, None))
        self.add_widget(self._arrow_l)
        self.add_widget(self._arrow_r)

        # Action button below preview (BUY / USE / EQUIPPED / UNEQUIP)
        self._action_btn = _ActionButton(callback=self._on_action_btn, size_hint=(None, None))
        self.add_widget(self._action_btn)

        # X (close) button – top-right
        self._back_btn = _XButton(callback=self._on_back, size_hint=(None, None))
        self.add_widget(self._back_btn)

    # ── Layout ────────────────────────────────────────────────────────────────

    def _reposition(self, *_):
        W, H = self.width, self.height
        if W < 2 or H < 2:
            return

        self._update_bg_img()

        for cat in _CATEGORIES:
            x, y, w, h = self._img_to_screen_box(_TAB_ZONES[cat])
            self._tab_btns[cat].pos  = (x, y)
            self._tab_btns[cat].size = (w, h)

        bx, by, bw, bh = self._img_to_screen_box(_ZONE_X_BTN)
        self._back_btn.pos  = (bx, by)
        self._back_btn.size = (bw, bh)

        lx, ly, lw, lh = self._img_to_screen_box(_ZONE_COINS_LBL)
        self._coins_lbl.pos       = (lx, ly)
        self._coins_lbl.size      = (lw, lh)
        self._coins_lbl.text_size = (lw, lh)

        cx, cy, cw, ch = self._img_to_screen_box(_ZONE_CARDS_AREA)

        # Scale card dimensions proportionally with the background.
        scale  = W / _BG_W
        col_w  = max(60, int(_CARD_W_REF * scale))
        card_h = max(80, int(col_w * 549 / 414))   # card art is 414 × 549

        # Grid is exactly 3 cols × 2 rows; no scroll wrapper needed.
        grid_w = 3 * col_w + 2 * 14 + 10 + 10       # cols + x-gaps + L/R padding
        grid_h = 2 * card_h + 8 + 2 + 6             # rows + y-gap + T/B padding
        self._card_grid.size = (grid_w, grid_h)
        self._card_grid.pos  = (cx, cy + ch - grid_h)  # top-aligned in the zone

        # Page nav arrows — same size as the preview arrows (_ZONE_ARROW_L = 150×200 src px)
        arr_w  = max(16, int(110 * scale))
        arr_h  = max(16, int(145 * scale))
        arr_y  = cy + ch - grid_h - arr_h + 12
        nav_cx = cx + grid_w / 2
        self._page_prev.size = (arr_w, arr_h)
        self._page_prev.pos  = (nav_cx - arr_w - 8, arr_y)
        self._page_next.size = (arr_w, arr_h)
        self._page_next.pos  = (nav_cx + 8, arr_y)

        if col_w != self._card_col_width or card_h != self._card_height:
            self._card_col_width = col_w
            self._card_height    = card_h
            self._card_grid.col_default_width = col_w
            for card in self._card_widgets:
                card.height = card_h
            Clock.schedule_once(lambda *_: self._card_grid.do_layout(), 0)

        px, py, pw, ph = self._img_to_screen_box(_ZONE_PREVIEW)
        self._preview.pos  = (px, py)
        self._preview.size = (pw, ph)

        lx, ly, lw, lh = self._img_to_screen_box(_ZONE_ARROW_L)
        self._arrow_l.pos  = (lx, ly)
        self._arrow_l.size = (lw, lh)

        rx, ry, rw, rh = self._img_to_screen_box(_ZONE_ARROW_R)
        self._arrow_r.pos  = (rx, ry)
        self._arrow_r.size = (rw, rh)

        ax, ay, aw, ah = self._img_to_screen_box(_ZONE_ACTION_BTN)
        self._action_btn.pos  = (ax, ay)
        self._action_btn.size = (aw, ah)

    # ── Data ──────────────────────────────────────────────────────────────────

    def _populate_cards(self):
        self._card_grid.clear_widgets()
        self._card_widgets = []
        player = get_current_player()
        if not player:
            return

        purchases  = get_player_purchases(player["name"])
        equipped   = get_cafe_equipped(player["name"])
        coins      = get_player_coins(player["name"])
        all_items  = SHOP_CATALOGUE.get(self._active_cat, [])

        self._total_pages = max(1, (len(all_items) + _PAGE_SIZE - 1) // _PAGE_SIZE)
        self._page = min(self._page, self._total_pages - 1)
        page_items = all_items[self._page * _PAGE_SIZE : (self._page + 1) * _PAGE_SIZE]

        for item in page_items:
            owned       = bool(purchases.get(item["key"]))
            slot        = _item_slot(item)
            is_equipped = slot is not None and equipped.get(slot) == item["key"]
            is_selected = (self._selected_item is not None and
                           self._selected_item["key"] == item["key"])
            can_afford  = bool(item.get("default")) or item.get("cost", 0) == 0 or coins >= item.get("cost", 0)
            card = _ItemCard(
                item=item,
                owned=owned,
                equipped=is_equipped,
                selected=is_selected,
                can_afford=can_afford,
                on_select=self._on_card_select,
                height=self._card_height,
            )
            self._card_grid.add_widget(card)
            self._card_widgets.append(card)

        self._page_prev.opacity = 1.0 if self._page > 0 else 0.25
        self._page_next.opacity = 1.0 if self._page < self._total_pages - 1 else 0.25
        Clock.schedule_once(lambda *_: self._card_grid.do_layout(), 0)

    # ── Events ────────────────────────────────────────────────────────────────

    def _update_preview_arrows(self):
        last = len(_PREVIEW_CROPS) - 1
        self._arrow_l.opacity = 0.0 if self._preview_view == 0    else 1.0
        self._arrow_r.opacity = 0.0 if self._preview_view == last else 1.0

    def _on_preview_prev(self):
        audio_manager.play_button_wood()
        self._preview_view = (self._preview_view - 1) % len(_PREVIEW_CROPS)
        self._preview.set_crop(self._preview_view)
        self._update_preview_arrows()

    def _on_preview_next(self):
        audio_manager.play_button_wood()
        self._preview_view = (self._preview_view + 1) % len(_PREVIEW_CROPS)
        self._preview.set_crop(self._preview_view)
        self._update_preview_arrows()

    def _on_page_prev(self):
        if self._page > 0:
            audio_manager.play_button_wood()
            self._page -= 1
            self._populate_cards()

    def _on_page_next(self):
        if self._page < self._total_pages - 1:
            audio_manager.play_button_wood()
            self._page += 1
            self._populate_cards()

    def _on_tab(self, category):
        audio_manager.play_button_wood()
        self._active_cat    = category
        self._selected_item = None
        self._page          = 0
        for cat, btn in self._tab_btns.items():
            btn.set_active(cat == category)
        self._populate_cards()
        self._refresh_preview()
        self._update_action_btn()

    def _on_card_select(self, item):
        """Called when a card is tapped — preview the item and update the action button."""
        audio_manager.play_button_wood()
        self._selected_item = item
        # Update selection highlight on all cards
        for card in self._card_widgets:
            card.set_selected(card._item["key"] == item["key"])
        self._refresh_preview()
        self._update_action_btn()

    def _refresh_preview(self):
        player = get_current_player()
        self._preview.refresh(
            player_name=player["name"] if player else None,
            preview_item=self._selected_item,
        )

    def _update_action_btn(self):
        """Recalculate which action (BUY / USE / EQUIPPED / UNEQUIP) to show."""
        item = self._selected_item
        if item is None:
            self._action_btn.update("SELECT AN ITEM", _C_PANEL_LOCKED, False)
            return

        player = get_current_player()
        if not player:
            self._action_btn.update("BUY", _C_PANEL_LOCKED, False)
            return

        purchases = get_player_purchases(player["name"])
        owned     = bool(purchases.get(item["key"]))
        slot      = _item_slot(item)
        equipped  = get_cafe_equipped(player["name"])
        is_eqp    = slot is not None and equipped.get(slot) == item["key"]

        if owned:
            if is_eqp:
                if slot in _UNEQUIPPABLE_SLOTS:
                    self._action_btn.update("UNEQUIP", _C_UNEQUIP, True)
                else:
                    self._action_btn.update("EQUIPPED", _C_EQUIPPED, False)
            else:
                self._action_btn.update("USE", _C_USE, True)
        else:
            coins      = get_player_coins(player["name"])
            can_afford = coins >= item["cost"]
            if can_afford:
                self._action_btn.update("BUY", _C_BUY, True)
            else:
                self._action_btn.update("BUY", _C_BROKE, False)

    def _on_action_btn(self):
        """Perform BUY / USE / UNEQUIP for the currently selected item."""
        item = self._selected_item
        if item is None:
            return
        player = get_current_player()
        if not player:
            return

        purchases = get_player_purchases(player["name"])
        owned     = bool(purchases.get(item["key"]))
        slot      = _item_slot(item)
        equipped  = get_cafe_equipped(player["name"])
        is_eqp    = slot is not None and equipped.get(slot) == item["key"]

        if owned:
            if is_eqp and slot in _UNEQUIPPABLE_SLOTS:
                # Unequip — clear selection so preview shows real state (no item)
                audio_manager.play_button_wood()
                set_cafe_equipped(player["name"], slot, None)
                self._selected_item = None
            elif not is_eqp:
                # Equip / USE
                audio_manager.play_button_wood()
                set_cafe_equipped(player["name"], slot, item["key"])
        else:
            # Buy — and immediately equip
            if purchase_shop_item(player["name"], item["key"], item["cost"]):
                audio_manager.play_purchase_successful()
                coins = get_player_coins(player["name"])
                self._coins_lbl.text = f"{coins:,}"
                if slot is not None:
                    set_cafe_equipped(player["name"], slot, item["key"])

        self._populate_cards()
        self._refresh_preview()
        self._update_action_btn()

    def _on_back(self, *_):
        audio_manager.play_button_wood()
        self.manager.current = "cafe_hub"

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def on_enter(self):
        player = get_current_player()
        if player:
            ensure_defaults_owned(player["name"])
        coins  = get_player_coins(player["name"]) if player else 0
        self._coins_lbl.text = f"{coins:,}"
        self._active_cat    = "seats"
        self._selected_item = None
        self._page          = 0
        for cat, btn in self._tab_btns.items():
            btn.set_active(cat == "seats")
        self._populate_cards()
        self._preview_view = 0
        self._preview.refresh(player["name"] if player else None)
        self._update_action_btn()
        self._update_preview_arrows()
        Clock.schedule_once(lambda *_: self._reposition(), 0)

    def on_leave(self):
        pass
