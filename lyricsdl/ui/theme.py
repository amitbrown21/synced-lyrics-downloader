"""Design tokens for The Crate — the committed visual world.

Kraft board on a near-black crate ground, silkscreen tab ink, condensed
grotesque caps, hairline rules. Every colour and metric the UI uses lives here
so the world stays consistent across panes and dialogs.
"""

from __future__ import annotations

import tkinter.font as tkfont
from types import SimpleNamespace

# --------------------------------------------------------------------------
# Palette
# --------------------------------------------------------------------------

CRATE = "#211F1D"        # app ground
CRATE_DEEP = "#191716"   # recessed crate
PANEL = "#2B2A28"        # raised crate panel / toolbar
PANEL_HI = "#343230"     # hover
PANEL_EDGE = "#3A3835"   # hairline on dark

STOCK = "#E8E2D2"        # kraft board stock
STOCK_DIM = "#D9D1BC"    # stock in shade
STOCK_EDGE = "#BCB29A"   # hairline rule on stock
INK = "#1C1A17"          # ink on stock
INK_SOFT = "#5A5344"     # secondary ink (≥4.5:1 on stock)
INK_FAINT = "#8B8474"    # tertiary ink (meta only)

RED = "#C8452F"          # silkscreen accent — the pulled-forward tab
RED_DEEP = "#A93622"
RED_SOFT = "#E2836C"

GREEN = "#6F8163"        # filed / complete
AMBER = "#C08A2E"        # warning
VOID = "#8A8377"         # missing / none

# The same three states inked for kraft board. The dark-ground trio is too
# light to clear 3:1 on stock, so marks drawn on a board use these.
GREEN_INK = "#3F4C38"
AMBER_INK = "#8A5A12"
VOID_INK = "#6B6355"

TEXT = "#EDE8DC"         # primary text on dark
TEXT_DIM = "#A79E8C"     # secondary text on dark (≥4.5:1)
TEXT_FAINT = "#989081"   # tertiary text on dark

FOCUS = "#F0C46A"

# Log level colours, tuned to read on the dark ground.
LOG_COLORS = {
    "info": "#CFC7B4",
    "step": "#9E9583",
    "ok": "#8FBE7A",
    "warn": "#E0B45C",
    "error": "#E08573",
}

# --------------------------------------------------------------------------
# Metrics
# --------------------------------------------------------------------------

S = SimpleNamespace(xs=4, sm=8, md=12, lg=16, xl=24)
RADIUS = 0          # the crate is hard-edged
RULE = 1            # hairline thickness in px


def mix(a: str, b: str, t: float) -> str:
    """Blend two ``#rrggbb`` colours; ``t`` 0 → a, 1 → b."""
    ar, ag, ab = int(a[1:3], 16), int(a[3:5], 16), int(a[5:7], 16)
    br, bg, bb = int(b[1:3], 16), int(b[3:5], 16), int(b[5:7], 16)
    r = round(ar + (br - ar) * t)
    g = round(ag + (bg - ag) * t)
    bl = round(ab + (bb - ab) * t)
    return f"#{r:02x}{g:02x}{bl:02x}"


# --------------------------------------------------------------------------
# Type — resolved against what is actually installed
# --------------------------------------------------------------------------

_FAMILIES: set[str] = set()

DISPLAY = "Bahnschrift SemiCondensed"
UI = "Bahnschrift"
MONO = "Consolas"


def _first_available(candidates: tuple[str, ...], fallback: str) -> str:
    for name in candidates:
        if name in _FAMILIES:
            return name
    return fallback


def init_fonts(root) -> None:
    """Resolve font families once a Tk root exists."""
    global DISPLAY, UI, MONO, _FAMILIES
    _FAMILIES = set(tkfont.families(root))
    DISPLAY = _first_available(
        ("Bahnschrift SemiCondensed", "Bahnschrift Condensed", "Bahnschrift",
         "Arial Narrow", "Segoe UI", "Helvetica"),
        "Segoe UI",
    )
    UI = _first_available(
        ("Bahnschrift", "Segoe UI", "Helvetica", "DejaVu Sans"),
        "Segoe UI",
    )
    MONO = _first_available(
        ("Cascadia Mono", "Consolas", "DejaVu Sans Mono", "Courier New"),
        "Courier New",
    )


def display(size: int, weight: str = "bold") -> tuple:
    return (DISPLAY, size, weight)


def ui(size: int, weight: str = "normal") -> tuple:
    return (UI, size, weight)


def mono(size: int, weight: str = "normal") -> tuple:
    return (MONO, size, weight)
