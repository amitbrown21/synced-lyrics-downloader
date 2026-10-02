"""The Crate widget kit.

Everything the crate world needs that stock widgets cannot give us: kraft
divider tabs, record spines, ruled tracklists, drawn state marks, and
silkscreen buttons. Lists are drawn on a :class:`tkinter.Canvas` so the
material, the hairline rules and the pull-forward selection are ours to
control.
"""

from __future__ import annotations

import tkinter as tk
import tkinter.font as tkfont
from dataclasses import dataclass, field
from typing import Callable

import customtkinter as ctk

from . import theme as T

PULL = 7            # px a selected row is pulled forward
RAIL = 10           # px reserved for the custom scroll rail

ROW_HEIGHT = {"divider": 32, "spine": 26, "track": 24, "item": 26, "result": 24}

# Spine colours cycle through the crate palette so albums stay distinguishable.
SPINE_COLORS = ["#8C6A4A", "#6E7A62", "#8A5B4E", "#5E6B72", "#7A6A86", "#9A7B4A"]


@dataclass
class Row:
    key: str
    label: str
    kind: str = "item"          # divider | spine | track | item | result
    state: str | None = None    # all|some|none (folders) / synced|plain|incomplete|none (tracks) / job states (results)
    meta: str = ""              # trailing text (track count, running time, …)
    index: str = ""             # divider tab label
    spine: str = ""             # spine stripe colour
    mark: bool = True           # draw the leading state mark
    provider: str = ""          # result rows: who answered, or why nobody did
    data: dict = field(default_factory=dict)


def result_columns(x0: float, x1: float, sf: float = 1.0) -> dict:
    """Column geometry for result rows.

    One source of truth, so the header strip and the rows can never disagree.
    The state column is right-aligned, so its width has to be reserved up front
    — otherwise long provider text runs underneath it.
    """
    gap = 10.0 * sf
    mark_w = 26.0 * sf
    state_w = 92.0 * sf
    provider_w = 104.0 * sf
    right = x1 - 12.0 * sf
    title_x = x0 + mark_w
    provider_x = right - state_w - gap - provider_w
    span = max(60.0, provider_x - gap - title_x)
    meta_w = span * 0.5
    return {
        "mark_x": x0 + mark_w / 2,
        "title": (title_x, span - meta_w),
        "meta": (title_x + (span - meta_w) + gap, meta_w),
        "provider": (provider_x, provider_w),
        "state_x": right,
    }



# --------------------------------------------------------------------------
# Drawn iconography — no emoji, no unicode glyphs
# --------------------------------------------------------------------------

MARK_COLORS = {
    "synced": T.GREEN,
    "plain": T.VOID,
    "incomplete": T.AMBER,
    "none": T.VOID,
    "all": T.GREEN,
    "some": T.AMBER,
    # Job-result states, shown on the results sheet.
    "queued": T.mix(T.VOID, T.CRATE, 0.55),
    "working": T.FOCUS,
    "upgraded": T.GREEN,
    "kept": T.VOID,
    "skipped": T.VOID,
    "failed": T.RED_SOFT,
    "cancelled": T.mix(T.VOID, T.CRATE, 0.3),
}

MARK_LABELS = {
    "synced": "synced lyrics",
    "plain": "plain lyrics",
    "incomplete": "incomplete lyrics",
    "none": "no lyrics",
    "all": "complete",
    "some": "partly complete",
    "queued": "queued",
    "working": "looking up…",
    "upgraded": "upgraded to synced",
    "kept": "kept plain lyrics",
    "skipped": "skipped",
    "failed": "no lyrics found",
    "cancelled": "cancelled",
}

# On kraft board the state colours are inked down to stay legible.
MARK_COLORS_STOCK = {
    "synced": T.GREEN_INK,
    "all": T.GREEN_INK,
    "plain": T.VOID_INK,
    "none": T.VOID_INK,
    "incomplete": T.AMBER_INK,
    "some": T.AMBER_INK,
    "queued": T.INK_FAINT,
    "working": T.AMBER_INK,
    "upgraded": T.GREEN_INK,
    "kept": T.VOID_INK,
    "skipped": T.VOID_INK,
    "failed": T.RED_DEEP,
    "cancelled": T.INK_FAINT,
}

# States that borrow another state's silhouette so the family stays small.
MARK_SHAPES = {
    "upgraded": "synced",
    "kept": "plain",
    "failed": "none",
    "skipped": "none",
    "cancelled": "none",
    "queued": "none",
}


def mark_color(state: str | None, on_stock: bool = False) -> str:
    """Mark colour for *state*. Kraft boards need the inked-down palette."""
    palette = MARK_COLORS_STOCK if on_stock else MARK_COLORS
    return palette.get(state or "", T.INK_SOFT if on_stock else T.VOID)


def draw_mark(canvas: tk.Canvas, x: float, y: float, size: float, state: str | None, color: str) -> None:
    """Draw a state mark centred on (x, y). *size* is the mark's box."""
    if not state:
        return
    shape = MARK_SHAPES.get(state, state)
    h = size / 2.0
    left, top, right, bottom = x - h, y - h, x + h, y + h
    lw = max(1.0, size / 9.0)
    if shape == "working":
        # An open ring: the mark for "in flight", distinct from a settled state.
        canvas.create_arc(left, top, right, bottom, start=55, extent=285, style="arc",
                          outline=color, width=lw * 1.4)
    elif shape in ("synced", "all"):
        canvas.create_oval(left, top, right, bottom, outline=color, width=lw, fill="")
        canvas.create_line(x - h * 0.45, y, x - h * 0.08, y + h * 0.42, fill=color, width=lw,
                           capstyle="round", joinstyle="round")
        canvas.create_line(x - h * 0.08, y + h * 0.42, x + h * 0.5, y - h * 0.4, fill=color, width=lw,
                           capstyle="round", joinstyle="round")
    elif shape == "plain":
        canvas.create_rectangle(left, top, right, bottom, outline=color, width=lw, fill="")
        canvas.create_line(left + h * 0.5, y - h * 0.25, right - h * 0.4, y - h * 0.25, fill=color, width=lw)
        canvas.create_line(left + h * 0.5, y + h * 0.35, right - h * 0.7, y + h * 0.35, fill=color, width=lw)
    elif shape == "incomplete":
        canvas.create_polygon(x, top, right, bottom, left, bottom, outline=color, width=lw,
                              fill="", joinstyle="miter")
        canvas.create_line(x, y - h * 0.35, x, y + h * 0.15, fill=color, width=lw, capstyle="round")
        canvas.create_line(x, y + h * 0.5, x, y + h * 0.5, fill=color, width=lw * 2, capstyle="round")
    elif shape == "some":
        canvas.create_oval(left, top, right, bottom, outline=color, width=lw, fill="")
        canvas.create_arc(left, top, right, bottom, start=90, extent=180, style="pieslice",
                          outline="", fill=color)
    else:  # none
        canvas.create_oval(left, top, right, bottom, outline=color, width=lw, fill="")
        canvas.create_line(x - h * 0.55, y + h * 0.55, x + h * 0.55, y - h * 0.55,
                           fill=color, width=lw, capstyle="round")


class StateMark(tk.Canvas):
    """A small standalone mark, used in the legend and status strip."""

    def __init__(self, parent, size: int = 14, state: str = "none", color: str | None = None, **kw):
        super().__init__(parent, width=size, height=size, highlightthickness=0,
                         bd=0, bg=kw.pop("bg", T.CRATE), **kw)
        draw_mark(self, size / 2, size / 2, size * 0.86, state, color or mark_color(state))


# --------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------

_FONT_CACHE: dict[tuple, tkfont.Font] = {}


def reset_font_cache() -> None:
    """Drop cached Font objects.

    A ``tkfont.Font`` is bound to the Tk root that was current when it was
    created, so every cached entry dies with that root — which then fails with
    "application has been destroyed" rather than a useful message.
    """
    _FONT_CACHE.clear()


def _font(spec: tuple) -> tkfont.Font:
    key = tuple(spec)
    if key not in _FONT_CACHE:
        _FONT_CACHE[key] = tkfont.Font(family=spec[0], size=spec[1],
                                       weight=(spec[2] if len(spec) > 2 else "normal"))
    return _FONT_CACHE[key]


def fit_text(text: str, spec: tuple, max_w: float) -> str:
    if max_w <= 0:
        return ""
    font = _font(spec)
    if font.measure(text) <= max_w:
        return text
    ell = "\u2026"
    lo, hi = 0, len(text)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if font.measure(text[:mid] + ell) <= max_w:
            lo = mid
        else:
            hi = mid - 1
    return (text[:lo] + ell) if lo else ell


def rule(parent, color: str = T.PANEL_EDGE, **pack_kw) -> tk.Frame:
    """A hairline separator."""
    f = tk.Frame(parent, bg=color, height=1)
    f.pack(fill="x", **pack_kw)
    return f


def silk_button(parent, text: str, command: Callable[[], None], *, primary: bool = False,
                width: int = 0, height: int = 30, state: str = "normal") -> ctk.CTkButton:
    """A silkscreen button: flat, hard-edged, condensed caps."""
    if primary:
        fg, hover, tc = T.RED, T.RED_DEEP, T.STOCK
        border, bc = 0, T.RED
    else:
        fg, hover, tc = T.PANEL, T.PANEL_HI, T.TEXT
        border, bc = 1, T.PANEL_EDGE
    btn = ctk.CTkButton(
        parent, text=text.upper(), command=command,
        fg_color=fg, hover_color=hover, text_color=tc,
        text_color_disabled=T.TEXT_FAINT,
        corner_radius=T.RADIUS, border_width=border, border_color=bc,
        font=T.display(11), height=height,
        **({"width": width} if width else {}),
    )
    if state == "disabled":
        btn.configure(state="disabled", fg_color=T.mix(T.PANEL, T.CRATE, 0.4),
                      text_color=T.TEXT_FAINT, border_color=T.PANEL_EDGE)
    return btn


def ghost_button(parent, text: str, command: Callable[[], None], *, width: int = 0,
                 height: int = 24) -> ctk.CTkButton:
    """A quiet text button for pane headers."""
    return ctk.CTkButton(
        parent, text=text.upper(), command=command,
        fg_color="transparent", hover_color=T.PANEL_HI, text_color=T.TEXT_DIM,
        corner_radius=0, border_width=0, font=T.display(10, "normal"),
        height=height, **({"width": width} if width else {}),
    )


class Tooltip:
    def __init__(self, widget, text: str):
        self.widget, self.text, self.win = widget, text, None
        widget.bind("<Enter>", self._show, add="+")
        widget.bind("<Leave>", self._hide, add="+")
        widget.bind("<ButtonPress>", self._hide, add="+")

    def _show(self, _e=None):
        if self.win or not self.text:
            return
        x = self.widget.winfo_rootx() + 14
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
        self.win = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        tw.configure(bg=T.STOCK_EDGE)
        tk.Label(tw, text=self.text, justify="left", bg=T.STOCK, fg=T.INK,
                 font=T.ui(9), padx=8, pady=5).pack(padx=1, pady=1)

    def _hide(self, _e=None):
        if self.win:
            self.win.destroy()
            self.win = None


# --------------------------------------------------------------------------
# The crate list
# --------------------------------------------------------------------------

class CrateList(tk.Frame):
    """A Canvas list of crate rows with multi-select and a pull-forward state.

    ``interactive=False`` turns it into a read-only sheet (no selection, no
    hover, no keyboard). ``header`` adds a non-scrolling kraft column strip.
    """

    def __init__(self, parent, *, on_select: Callable | None = None,
                 on_activate: Callable | None = None, empty_text: str = "",
                 row_height: int | None = None, footer_text: str = "",
                 interactive: bool = True, follow: bool = False,
                 header: tuple[str, ...] | None = None):
        super().__init__(parent, bg=T.CRATE_DEEP, highlightthickness=0, bd=0)
        self.canvas = tk.Canvas(self, bg=T.CRATE_DEEP, highlightthickness=0, bd=0,
                                takefocus=1)
        self.canvas.pack(fill="both", expand=True)
        try:
            self._sf = float(ctk.ScalingTracker.get_widget_scaling(self.canvas))
        except Exception:
            self._sf = 1.0

        self.rows: list[Row] = []
        self._sel: set[str] = set()
        self._anchor: int | None = None
        self._scroll = 0.0
        self._hover: int = -1
        self._height_override = row_height
        self._total_h = 0.0
        self._pull = 1.0          # pull-forward animation progress (0..1)
        self._anim_job = None
        self._interactive = interactive
        self._follow = follow     # keep the newest row in view
        self._header = header
        self._rail_grab: float | None = None   # cursor offset while dragging the rail

        self._on_select = on_select
        self._on_activate = on_activate
        self._empty_text = empty_text
        self._footer_text = footer_text

        self.canvas.bind("<Configure>", lambda e: self._redraw())
        self.canvas.bind("<MouseWheel>", self._on_wheel)
        self.canvas.bind("<Button-4>", lambda e: self._wheel(-1))
        self.canvas.bind("<Button-5>", lambda e: self._wheel(1))
        # The rail is a real scrollbar, so these are bound whether or not the
        # list is interactive — a read-only sheet still has to be scrollable.
        self.canvas.bind("<Button-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.canvas.bind("<Motion>", self._on_motion)
        self.canvas.bind("<Leave>", self._on_leave)
        if interactive:
            self.canvas.bind("<Double-Button-1>", self._on_double)
            self.canvas.bind("<Up>", lambda e: self._move(-1))
            self.canvas.bind("<Down>", lambda e: self._move(1))
            self.canvas.bind("<Home>", lambda e: self._move_to(0))
            self.canvas.bind("<End>", lambda e: self._move_to(len(self.rows) - 1))
            self.canvas.bind("<Prior>", lambda e: self._move(-8))
            self.canvas.bind("<Next>", lambda e: self._move(8))
            self.canvas.bind("<Control-a>", lambda e: (self.select_all(), "break"))
            self.canvas.bind("<Control-A>", lambda e: (self.select_all(), "break"))

    # -- data -------------------------------------------------------------

    def set_rows(self, rows: list[Row]) -> None:
        self.rows = list(rows)
        keys = {r.key for r in self.rows}
        self._sel &= keys
        if self._anchor is not None and self._anchor >= len(self.rows):
            self._anchor = None
        self._clamp_scroll()
        self._redraw()

    def add_row(self, row: Row) -> None:
        """Append one row and keep it in view while following."""
        self.rows.append(row)
        self._clamp_scroll()
        if self._follow:
            self.see(len(self.rows) - 1)

    def see_key(self, key: str) -> None:
        """Scroll *key* into view, unless the user has taken over scrolling."""
        if not self._follow:
            return
        i = self.index_of(key)
        if i is not None:
            self.see(i)

    def scroll_to_top(self) -> None:
        self._scroll = 0.0
        self._redraw()

    def resume_follow(self) -> None:
        """Re-engage auto-scroll, e.g. when a new job starts."""
        self._follow = True


    def row_height(self, row: Row) -> int:
        if self._height_override:
            return int(self._height_override * self._sf)
        return int(ROW_HEIGHT.get(row.kind, 26) * self._sf)

    def size(self) -> int:
        return len(self.rows)

    def get(self, i: int) -> Row:
        return self.rows[i]

    def index_of(self, key: str) -> int | None:
        for i, r in enumerate(self.rows):
            if r.key == key:
                return i
        return None

    def update_row(self, key: str, **changes) -> None:
        i = self.index_of(key)
        if i is None:
            return
        for k, v in changes.items():
            setattr(self.rows[i], k, v)
        self._redraw()

    # -- selection --------------------------------------------------------

    def selected_indices(self) -> list[int]:
        return [i for i, r in enumerate(self.rows) if r.key in self._sel]

    def selected_keys(self) -> list[str]:
        return [r.key for r in self.rows if r.key in self._sel]

    def selected_rows(self) -> list[Row]:
        return [r for r in self.rows if r.key in self._sel]

    def select_keys(self, keys) -> None:
        self._sel = {k for k in keys if self.index_of(k) is not None}

    def select_all(self) -> None:
        if not self.rows:
            return
        self._sel = {r.key for r in self.rows}
        self._anchor = 0
        self._changed()

    def clear_selection(self) -> None:
        self._sel.clear()
        self._anchor = None
        self._changed()

    def select_index(self, i: int, *, scroll: bool = True) -> None:
        if self.rows and 0 <= i < len(self.rows):
            self._sel = {self.rows[i].key}
            self._anchor = i
            if scroll:
                self.see(i)
            self._changed()

    def see(self, i: int) -> None:
        if not (0 <= i < len(self.rows)):
            return
        top = self._row_top(i)
        h = self._viewport_h()
        if top < self._scroll:
            self._scroll = top
        elif top + self.row_height(self.rows[i]) > self._scroll + h:
            self._scroll = top + self.row_height(self.rows[i]) - h
        self._clamp_scroll()
        self._redraw()

    # -- geometry ---------------------------------------------------------

    def _row_top(self, i: int) -> float:
        y = 0.0
        for r in self.rows[:i]:
            y += self.row_height(r) + 1
        return y

    def _viewport_h(self) -> float:
        """Usable content height: the header strip, if any, is not scrollable."""
        return max(self.canvas.winfo_height() - self._header_h(), 1)

    def _header_h(self) -> float:
        return (24.0 * self._sf) if self._header else 0.0

    def _clamp_scroll(self) -> None:
        total = self._row_top(len(self.rows)) + (self._footer_h())
        self._total_h = total
        self._scroll = max(0.0, min(self._scroll, max(0.0, total - self._viewport_h())))

    def _footer_h(self) -> float:
        return 26 if self._footer_text else 0

    # -- interaction ------------------------------------------------------

    def _row_at(self, cy: float) -> int:
        y = -self._scroll
        for i, r in enumerate(self.rows):
            h = self.row_height(r) + 1
            if y <= cy < y + h:
                return i
            y += h
        return -1

    def _set_hover(self, i: int) -> None:
        if i != self._hover:
            self._hover = i
            self.canvas.configure(cursor="hand2" if i >= 0 else "")
            self._redraw()

    def _on_motion(self, event):
        if self._rail_grab is not None:
            self._rail_drag(event)
            return
        geo = self._rail_geometry()
        if geo and event.x >= geo[0]:
            # Over the rail: never highlight a row, and show it can be dragged.
            if self._hover != -1:
                self._hover = -1
                self._redraw()
            self.canvas.configure(cursor="sb_v_double_arrow")
            return
        if self._interactive:
            self._set_hover(self._row_at(event.y))

    def _on_leave(self, event):
        self._rail_grab = None
        self._set_hover(-1)
        self.canvas.configure(cursor="")

    def _on_press(self, event):
        """Left click: on the rail it scrolls, anywhere else it selects a row."""
        if self._rail_press(event):
            return "break"
        if self._interactive:
            self._on_click(event)

    def _on_drag(self, event):
        self._rail_drag(event)

    def _on_release(self, event):
        self._rail_grab = None

    def _rail_geometry(self) -> tuple | None:
        """``(rail_x, top, knob_y, knob_h, travel, max_scroll)``, or None.

        None means nothing scrolls, which is also how the rail's hit area is
        defined — the strip only responds when a rail is actually drawn there.
        """
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        top = self._header_h()
        track = self._row_top(len(self.rows)) + self._footer_h()
        view = self._viewport_h()
        if track <= view or h <= top:
            return None
        span = h - top
        knob_h = max(24.0, span * (view / track))
        travel = span - knob_h
        max_scroll = track - view
        knob_y = top + (self._scroll / max_scroll) * travel
        return w - RAIL, top, knob_y, knob_h, travel, max_scroll

    @staticmethod
    def _scroll_for_knob(knob_y: float, top: float, travel: float,
                         max_scroll: float) -> float:
        if travel <= 0:
            return 0.0
        return max(0.0, min(1.0, (knob_y - top) / travel)) * max_scroll

    def _rail_press(self, event) -> bool:
        """Handle a press on the rail; True if it was the rail's."""
        geo = self._rail_geometry()
        if not geo or event.x < geo[0]:
            return False
        rail_x, top, knob_y, knob_h, travel, max_scroll = geo
        self.canvas.focus_set()
        self._follow = False        # the user took over; stop chasing rows
        if not (knob_y <= event.y <= knob_y + knob_h):
            # The trough behaves like a page: jump the knob to the pointer.
            self._scroll = self._scroll_for_knob(event.y - knob_h / 2, top, travel, max_scroll)
            self._clamp_scroll()
            self._redraw()
            knob_y = self._rail_geometry()[2]
        self._rail_grab = event.y - knob_y
        return True

    def _rail_drag(self, event) -> None:
        if self._rail_grab is None:
            return
        geo = self._rail_geometry()
        if not geo:
            return
        rail_x, top, knob_y, knob_h, travel, max_scroll = geo
        self._scroll = self._scroll_for_knob(event.y - self._rail_grab, top, travel, max_scroll)
        self._clamp_scroll()
        self._redraw()

    def _on_wheel(self, event):
        self._wheel(-1 if event.delta > 0 else 1)

    def _wheel(self, direction: int):
        self._follow = False      # the user took the wheel; stop chasing rows
        self._scroll += direction * 60
        self._clamp_scroll()
        self._redraw()

    def _on_click(self, event):
        self.canvas.focus_set()
        i = self._row_at(event.y)
        if i < 0:
            return
        ctrl = bool(event.state & 0x0004)
        shift = bool(event.state & 0x0001)
        key = self.rows[i].key
        if ctrl:
            self._sel.symmetric_difference_update({key})
            self._anchor = i
        elif shift and self._anchor is not None:
            lo, hi = sorted((self._anchor, i))
            self._sel = {r.key for r in self.rows[lo:hi + 1]}
        else:
            self._sel = {key}
            self._anchor = i
        self._changed(pull=True)

    def _on_double(self, event):
        geo = self._rail_geometry()
        if geo and event.x >= geo[0]:
            return                      # a double-click on the rail scrolls, not selects
        i = self._row_at(event.y)
        if i >= 0 and self._on_activate:
            self._on_activate(i)

    def _move(self, delta: int):
        cur = self.selected_indices()
        base = cur[0] if cur else (self._anchor or 0)
        self.select_index(max(0, min(len(self.rows) - 1, base + delta)))

    def _move_to(self, i: int):
        self.select_index(i)

    def _changed(self, *, pull: bool = False):
        self._redraw()
        if self._on_select:
            self._on_select()
        if pull:
            self._animate_pull()

    # -- the authored moment: a pulled-forward record ---------------------

    def _animate_pull(self):
        if self._anim_job is not None:
            try:
                self.after_cancel(self._anim_job)
            except Exception:
                pass
        self._pull = 0.0

        def step():
            self._pull = min(1.0, self._pull + 0.16)
            self._redraw()
            if self._pull < 1.0:
                self._anim_job = self.after(16, step)
            else:
                self._anim_job = None

        step()

    def _ease(self) -> float:
        t = self._pull
        return 1 - (1 - t) ** 3

    # -- drawing ----------------------------------------------------------

    def _redraw(self):
        c = self.canvas
        c.delete("all")
        w = c.winfo_width()
        h = c.winfo_height()
        if w <= 1 or h <= 1:
            return
        self._clamp_scroll()

        top = self._header_h()
        y = top - self._scroll
        rail_x = w - RAIL
        c.create_rectangle(0, 0, rail_x, h, outline="", fill=T.CRATE_DEEP)

        if not self.rows:
            if self._empty_text:
                c.create_text(T.S.md + 2, top + T.S.sm, anchor="nw", text=self._empty_text,
                              font=T.ui(10), fill=T.TEXT_FAINT, width=max(40, rail_x - 2 * T.S.md))
        else:
            for i, row in enumerate(self.rows):
                rh = self.row_height(row)
                if y + rh >= top and y <= h:   # cull above the header, not just the canvas
                    selected = row.key in self._sel
                    self._draw_row(c, i, row, y, rh, rail_x, selected, i == self._hover)
                y += rh + 1

            if self._footer_text:
                self._draw_footer(c, rail_x, y)

        self._draw_rail(rail_x, w, h)
        if self._header:
            self._draw_header(c, rail_x)   # last: rows scroll under the strip

    def _draw_header(self, c: tk.Canvas, rail_x: float):
        hh = self._header_h()
        c.create_rectangle(0, 0, rail_x, hh, outline="", fill=T.STOCK_DIM)
        c.create_line(0, hh, rail_x, hh, fill=T.STOCK_EDGE)
        cols = result_columns(T.S.sm, rail_x - T.S.sm, self._sf)
        cy = hh / 2
        labels = self._header
        for i, (x, anchor) in enumerate((
            (cols["title"][0], "w"),
            (cols["meta"][0], "w"),
            (cols["provider"][0], "w"),
            (cols["state_x"], "e"),
        )):
            if i < len(labels):
                c.create_text(x, cy, anchor=anchor, text=labels[i],
                              font=T.display(9), fill=T.INK_SOFT)

    def _draw_rail(self, rail_x: float, w: float, h: float):
        c = self.canvas
        top = self._header_h()
        track = max(0.0, self._total_h)
        view = self._viewport_h()
        if track <= view or h <= top:
            return
        c.create_rectangle(rail_x, top, w, h, outline="", fill=T.CRATE)
        span = h - top
        knob_h = max(24.0, span * (view / track))
        knob_y = top + (self._scroll / (track - view)) * (span - knob_h)
        # 6px rather than 3px: a scrollbar you cannot see is one you cannot grab.
        c.create_rectangle(rail_x + 2, knob_y, rail_x + 8, knob_y + knob_h,
                           outline="", fill=T.mix(T.PANEL, T.STOCK, 0.35))

    def _draw_footer(self, c: tk.Canvas, rail_x: float, y: float):
        c.create_line(T.S.sm, y + 0.5, rail_x - T.S.sm, y + 0.5, fill=T.PANEL_EDGE)
        c.create_text(rail_x - T.S.sm, y + 13, anchor="e", text=self._footer_text,
                      font=T.mono(9), fill=T.TEXT_FAINT)

    def _draw_row(self, c: tk.Canvas, i: int, row: Row, y: float, rh: float,
                  rail_x: float, selected: bool, hover: bool):
        kind = row.kind
        pull = self._ease() * PULL * self._sf if selected else 0.0
        x0 = T.S.sm + pull
        x1 = rail_x - T.S.sm
        cy = y + rh / 2
        layout = x1 - x0

        if kind == "divider":
            fill = T.STOCK if selected else (T.mix(T.STOCK_DIM, T.STOCK, 0.5) if hover else T.STOCK_DIM)
            c.create_rectangle(x0, y + 1, x1, y + rh, outline="", fill=fill)
            # printed edge under the board
            c.create_line(x0, y + rh, x1, y + rh, fill=T.STOCK_EDGE)
            tab_w = 26
            tab_fill = T.RED if selected else T.CRATE
            c.create_rectangle(x0, y + 1, x0 + tab_w, y + rh, outline="", fill=tab_fill)
            c.create_text(x0 + tab_w / 2, cy, text=row.index or "\u2013",
                          font=T.display(10), fill=T.STOCK if selected else T.TEXT_DIM)
            tx = x0 + tab_w + 10
            avail = x1 - tx - (34 if row.mark else 8)
            c.create_text(tx, cy, anchor="w", text=fit_text(row.label, T.display(12), avail),
                          font=T.display(12), fill=T.INK)
            if row.mark:
                draw_mark(c, x1 - 20, cy, 13, row.state, mark_color(row.state, on_stock=True))
        elif kind == "spine":
            fill = T.STOCK if selected else (T.PANEL_HI if hover else T.PANEL)
            c.create_rectangle(x0, y + 1, x1, y + rh, outline="", fill=fill)
            stripe = T.RED if selected else (row.spine or SPINE_COLORS[i % len(SPINE_COLORS)])
            c.create_rectangle(x0, y + 1, x0 + 5, y + rh, outline="", fill=stripe)
            tx = x0 + 14
            meta_w = 44 if row.meta else 8
            avail = x1 - tx - meta_w - (18 if row.mark else 4)
            c.create_text(tx, cy, anchor="w", text=fit_text(row.label, T.ui(11), avail),
                          font=T.ui(11), fill=T.INK if selected else T.TEXT)
            if row.meta:
                c.create_text(x1 - 10, cy, anchor="e", text=row.meta, font=T.mono(9),
                              fill=T.INK_SOFT if selected else T.TEXT_FAINT)
            if row.mark:
                # Keep clear of the reserved meta column, or the two collide.
                draw_mark(c, x1 - meta_w - 6, cy, 13, row.state,
                          mark_color(row.state, on_stock=selected))
        elif kind == "result":
            cols = result_columns(x0, x1, self._sf)
            if hover:
                c.create_rectangle(x0, y + 1, x1, y + rh, outline="", fill=T.PANEL)
            else:
                c.create_line(x0, y + rh, x1, y + rh, fill=T.PANEL_EDGE)
            color = mark_color(row.state)
            draw_mark(c, cols["mark_x"], cy, 13 * self._sf, row.state, color)
            tx, tw = cols["title"]
            c.create_text(tx, cy, anchor="w", text=fit_text(row.label, T.ui(11), tw),
                          font=T.ui(11), fill=T.TEXT)
            mx, mw = cols["meta"]
            c.create_text(mx, cy, anchor="w", text=fit_text(row.meta, T.ui(9), mw),
                          font=T.ui(9), fill=T.TEXT_FAINT)
            px, pw = cols["provider"]
            c.create_text(px, cy, anchor="w", text=fit_text(row.provider, T.mono(9), pw),
                          font=T.mono(9), fill=T.TEXT_DIM)
            c.create_text(cols["state_x"], cy, anchor="e", text=(row.state or "").upper(),
                          font=T.display(9), fill=color)
        else:  # track / item
            if selected:
                c.create_rectangle(x0, y + 1, x1, y + rh, outline="", fill=T.STOCK)
            elif hover:
                c.create_rectangle(x0, y + 1, x1, y + rh, outline="", fill=T.PANEL)
            else:
                c.create_line(x0, y + rh, x1, y + rh, fill=T.PANEL_EDGE)
            fg = T.INK if selected else T.TEXT
            # track index (from row.index, e.g. "03")
            ix = x0 + T.S.sm
            if row.index:
                c.create_text(ix, cy, anchor="w", text=row.index, font=T.mono(9),
                              fill=T.INK_SOFT if selected else T.TEXT_FAINT)
            tx = ix + 30
            meta_w = 52 if row.meta else 8
            avail = x1 - tx - meta_w - (18 if row.mark else 4)
            c.create_text(tx, cy, anchor="w", text=fit_text(row.label, T.ui(11), avail),
                          font=T.ui(11), fill=fg)
            if row.meta:
                c.create_text(x1 - 10, cy, anchor="e", text=row.meta, font=T.mono(9),
                              fill=T.INK_SOFT if selected else T.TEXT_FAINT)
            if row.mark:
                draw_mark(c, x1 - meta_w - 6, cy, 13, row.state,
                          mark_color(row.state, on_stock=selected))


# --------------------------------------------------------------------------
# A titled crate pane: header + list
# --------------------------------------------------------------------------

class CratePane(tk.Frame):
    def __init__(self, parent, *, title: str, on_select=None, on_activate=None,
                 on_toggle_all=None, empty_text: str = "", footer_text: str = ""):
        super().__init__(parent, bg=T.CRATE, highlightthickness=0, bd=0)
        self._on_toggle_all = on_toggle_all

        header = tk.Frame(self, bg=T.PANEL, height=30)
        header.pack(fill="x")
        header.pack_propagate(False)
        self.title_lbl = tk.Label(header, text=title.upper(), bg=T.PANEL, fg=T.TEXT_DIM,
                                  font=T.display(10))
        self.title_lbl.pack(side="left", padx=(T.S.md, T.S.sm))
        self.count_lbl = tk.Label(header, text="0", bg=T.PANEL, fg=T.TEXT_FAINT, font=T.mono(9))
        self.count_lbl.pack(side="left")
        self.toggle_btn = ghost_button(header, "All", self._toggle, width=44, height=22)
        self.toggle_btn.pack(side="right", padx=(0, 2))
        tk.Frame(self, bg=T.RED, height=2).pack(fill="x")

        self.list = CrateList(self, on_select=on_select, on_activate=on_activate,
                              empty_text=empty_text, footer_text=footer_text)
        self.list.pack(fill="both", expand=True)

    def _toggle(self):
        if self._on_toggle_all:
            self._on_toggle_all()

    def set_toggle_label(self, label: str) -> None:
        self.toggle_btn.configure(text=label.upper())

    def set_count(self, n: int) -> None:
        self.count_lbl.configure(text=str(n))

    def set_rows(self, rows: list[Row]) -> None:
        self.list.set_rows(rows)
        self.set_count(len(rows))

    def set_title(self, title: str) -> None:
        self.title_lbl.configure(text=title.upper())


# --------------------------------------------------------------------------
# The results sheet: what the job actually did, track by track
# --------------------------------------------------------------------------

RESULT_HEADER = ("TRACK", "FOLDER", "PROVIDER", "RESULT")


class ResultPane(tk.Frame):
    """A read-only sheet of per-track outcomes, newest job on top.

    Replaces squinting at a scrolling log: one ruled row per track, a drawn
    state mark, and the state spelled out in words — SYNCED, PLAIN, UPGRADED,
    FAILED, SKIPPED. Rows are seeded in job order so the whole worklist is
    visible from the first second, then they settle as lookups return.
    """

    def __init__(self, parent, *, on_toggle_log: Callable[[], None] | None = None,
                 empty_text: str = "", height: int = 196):
        super().__init__(parent, bg=T.CRATE, highlightthickness=0, bd=0)
        self._on_toggle_log = on_toggle_log
        self._show_log = False

        head = tk.Frame(self, bg=T.PANEL, height=28)
        head.pack(fill="x")
        head.pack_propagate(False)
        tk.Label(head, text="RESULTS", bg=T.PANEL, fg=T.TEXT_DIM,
                 font=T.display(10)).pack(side="left", padx=(T.S.md, T.S.sm))
        self.summary_lbl = tk.Label(head, text="", bg=T.PANEL, fg=T.TEXT_FAINT, font=T.mono(9))
        self.summary_lbl.pack(side="left")
        self.log_btn = ghost_button(head, "Log", self._toggle, width=58, height=22)
        self.log_btn.pack(side="right", padx=(0, 2))
        tk.Frame(self, bg=T.RED, height=2).pack(fill="x")

        wrap = tk.Frame(self, bg=T.PANEL_EDGE, height=height)
        wrap.pack(fill="x")
        wrap.pack_propagate(False)
        self.list = CrateList(wrap, interactive=False, follow=True,
                              empty_text=empty_text, header=RESULT_HEADER)
        self.list.pack(fill="both", expand=True, padx=1, pady=1)

    def _toggle(self):
        if self._on_toggle_log:
            self._on_toggle_log()

    def set_log_visible(self, visible: bool) -> None:
        self._show_log = visible
        self.log_btn.configure(text=("HIDE LOG" if visible else "LOG").upper())

    def set_rows(self, rows: list[Row]) -> None:
        self.list.set_rows(rows)
        self.list.scroll_to_top()

    def reset(self, rows: list[Row]) -> None:
        """Start a fresh job: new rows, back to the top, follow re-engaged."""
        self.set_rows(rows)
        self.list.resume_follow()

    def add_row(self, row: Row) -> None:
        self.list.add_row(row)

    def update_row(self, key: str, **changes) -> None:
        self.list.update_row(key, **changes)
        self.list.see_key(key)

    def has_row(self, key: str) -> bool:
        return self.list.index_of(key) is not None

    def set_summary(self, text: str) -> None:
        self.summary_lbl.configure(text=text)
