 Kivy / Android port – dev notes

## GL backend: use `sdl2`, NOT `angle_sdl2`

**Problem:** ANGLE (`angle_sdl2`) applies sRGB gamma correction to all texture output on Windows,
making every image render washed-out / too bright ("white haze").

**Fix:** Force the plain SDL2 OpenGL backend in `main.py` before any Kivy import:

```python
if sys.platform.startswith("win"):
    os.environ.setdefault("KIVY_GL_BACKEND", "sdl2")
```

ANGLE was originally used to avoid a `RenderContext.pop_state IndexError` crash.
That crash no longer happens because we replaced `ScreenManager` with `SimpleScreenManager`
(see below), so ANGLE is no longer needed.

---

## Replace `ScreenManager` with `SimpleScreenManager`

**Problem:** Kivy 2.3.x `ScreenManager` always creates a `RenderContext` in its `__init__`,
which causes an `IndexError: list index out of range` crash in `pop_state` on:
- OpenGL ES 3.2 / ANGLE backend
- Some AMD/Intel GLEW drivers on Windows

The crash happens regardless of which `Transition` is used (including `NoTransition`).

**Fix:** Replace `ScreenManager` with a plain `FloatLayout` that swaps screens manually.
See `SimpleScreenManager` in `main.py`. It has the same `.current` / `.get_screen()` API
so all screen code works unchanged.

All screen classes must be `FloatLayout` subclasses (NOT `Screen`), with:
```python
self.name    = kwargs.pop("name", "default_name")
self.manager = None
```

---

## Canvas drawing in game loop

**DO:**
```python
self.canvas.clear()
with self.canvas:
    Color(...)
    Rectangle(...)
```

**DON'T** use `InstructionGroup` with `PushMatrix` / `PopMatrix` — this causes the same
`pop_state IndexError` when the group is cleared mid-cycle.

Wobble effects: apply as a plain `wx` float offset added to each x coordinate.
Do NOT use `PushMatrix` / `Translate` / `PopMatrix` for this.

---

## Image backgrounds in screens

Use `kivy.uix.image.Image` widget added as the **first** child (so it renders behind everything):

```python
from kivy.uix.image import Image
import os

_ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets")

self.add_widget(Image(
    source=os.path.join(_ASSETS, "my_image.png"),
    allow_stretch=True,
    keep_ratio=False,
    size_hint=(1, 1),
    pos_hint={"x": 0, "y": 0},
))
```

Use **absolute paths** via `os.path.abspath(__file__)` — relative paths break depending
on which directory you launch from.

File extensions must be **lowercase** (`.png` not `.PNG`) — Android's filesystem is
case-sensitive, so `.PNG` would silently fail on device.

---

## Pixel art sizes (4× scale, reference height = 700 px)

| Sprite     | Draw at (native) | Export at 4× | Game constant      |
|------------|------------------|--------------|--------------------|
| Cat        | 32 × 28          | 128 × 112    | CAT_W/H_REF        |
| Beer cup   | 24 × 24          | 96 × 96      | BEER_W/H_REF       |
| Mouse      | 13 × 40          | 52 × 160     | MOUSE_W/H_REF      |
| Tray       | 68 × 28          | 272 × 112    | TRAY_W/H_REF       |
| Background | 320 × 180        | 1280 × 720   | full screen        |
| App icon   | 128 × 128        | 512 × 512    | icon.filename      |

After exporting, update the corresponding `*_REF` constants in `game_constants.py`.
Keep a 14 px dead zone on each side of the background for aspect ratio stretch on tall phones.

---

## Buildozer / Android

- Orientation: `landscape` (set in `buildozer.spec`)
- Presplash: `assets/presplash.png` — background colour set via `presplash.color`
- Icon: `assets/icon.png` (512×512) — uncomment `icon.filename` line when ready
- Score storage: uses `App.user_data_dir` (works on both desktop and Android)



The pattern to remember for any screen with a background image + overlay buttons/widgets:

Image-anchored overlay pattern

Measure once — open the background PNG in any image editor, note the pixel box (left, top, right, bottom) for each clickable/display zone.

Store as constants at the top of the file:


_BG_W, _BG_H = 3645, 1773          # source image size
_ZONE_ICON   = (441, 153, 530, 251) # (l, t, r, b) in image pixels
Add the converter — mirrors CoverImage's own math:


def _img_to_screen_box(self, zone):
    l, t, r, b = zone
    scr_w, scr_h = self.width, self.height
    img_ratio = _BG_W / _BG_H
    scr_ratio = scr_w / scr_h
    if img_ratio > scr_ratio:          # wider image → scale to height
        scale = scr_h / _BG_H
        off_x = (_BG_W - scr_w / scale) / 2
        sx = lambda ix: (ix - off_x) * scale
        sy = lambda iy: scr_h - iy * scale
    else:                              # taller image → scale to width
        scale = scr_w / _BG_W
        off_y = (_BG_H - scr_h / scale) / 2
        sx = lambda ix: ix * scale
        sy = lambda iy: scr_h - (iy - off_y) * scale
    return sx(l), sy(b), sx(r)-sx(l), sy(t)-sy(b)
Create widgets without pos_hint, add a _reposition_overlays method that calls _img_to_screen_box and sets .pos / .size directly.

Bind to window size:


self.bind(size=self._reposition_overlays, pos=self._reposition_overlays)
And call it in on_enter() too.

This works because it runs the exact same crop/scale logic as CoverImage, so the overlay always lands on the right art pixels regardless of screen resolution or aspect ratio.