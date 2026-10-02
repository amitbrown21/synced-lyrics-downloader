"""Exercise the crate list's rail. Run: python tests/test_widgets.py

The rail is drawn by hand, so it is easy to end up with a scrollbar that looks
right but cannot be grabbed. These are the interactions a user actually tries:
clicking the bar, dragging the knob, and clicking a row.
"""

from __future__ import annotations

import os
import sys
import tkinter as tk

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lyricsdl.ui.widgets import CrateList, Row


class Event:
    """The parts of a Tk event the rail handlers read."""

    def __init__(self, x: float, y: float, delta: int = 0, state: int = 0):
        self.x, self.y, self.delta, self.state = x, y, delta, state


def build(root: tk.Tk) -> CrateList:
    widget = CrateList(root, on_select=lambda: None)
    widget.pack(fill="both", expand=True)
    widget.set_rows([Row(key=f"k{i}", label=f"Track {i}", kind="item") for i in range(40)])
    root.update()          # realise geometry: the rail needs a real height
    return widget


def main() -> None:
    try:
        root = tk.Tk()
    except tk.TclError as exc:      # no display available
        print(f"skip — no display ({exc})")
        return
    root.geometry("300x200+3000+3000")   # off-screen, out of the way
    try:
        widget = build(root)
        geo = widget._rail_geometry()
        assert geo is not None, "a 40-row list in a 200px pane must have a rail"
        rail_x, top, knob_y, knob_h, travel, max_scroll = geo
        assert max_scroll > 0

        rail_click_x = rail_x + 3

        # 1. Clicking the bar scrolls. This is the bug being fixed: the rail was
        #    drawn but inert, and clicking it selected the row underneath.
        widget._scroll = 0.0
        widget._on_press(Event(rail_click_x, top + travel * 0.8))
        assert widget._scroll > 0, "clicking the rail must scroll"
        assert widget._sel == set(), "clicking the rail must not select a row"

        # 2. Clicking near the top returns to the top.
        widget._on_press(Event(rail_click_x, top + 1))
        assert widget._scroll == 0, f"expected the top, got {widget._scroll}"

        # 3. Dragging the knob tracks the pointer.
        widget._scroll = 0.0
        widget._on_press(Event(rail_click_x, top + knob_h / 2))    # grab the knob
        assert widget._rail_grab is not None, "pressing the knob starts a drag"
        widget._on_drag(Event(rail_click_x, top + travel * 0.5))
        mid = widget._scroll
        assert mid > 0, "dragging the knob must scroll"
        widget._on_drag(Event(rail_click_x, top + travel))
        assert widget._scroll > mid, "dragging further must scroll further"
        assert widget._scroll <= max_scroll + 0.001, "drag must respect the end"
        widget._on_release(Event(rail_click_x, top + travel))
        assert widget._rail_grab is None, "release must end the drag"

        # 4. A click on the list body still selects, and focuses.
        widget._on_press(Event(40, 30))
        assert len(widget._sel) == 1, "clicking a row must select it"

        # 5. The wheel still works, and takes the user out of follow mode.
        widget._scroll = 0.0
        widget._follow = True
        widget._on_wheel(Event(40, 30, delta=-120))
        assert widget._scroll > 0, "wheel must scroll"
        assert widget._follow is False, "scrolling by hand stops follow mode"

        # 6. A read-only list (the results sheet) can still be scrolled.
        #    Its own window: two expanded widgets in one window do not share
        #    height predictably, and a 1x1 canvas has no rail to test.
        sheet_top = tk.Toplevel(root)
        sheet_top.geometry("300x200+3000+3000")
        sheet = CrateList(sheet_top, interactive=False)
        sheet.pack(fill="both", expand=True)
        sheet.set_rows([Row(key=f"r{i}", label=f"Result {i}", kind="result") for i in range(40)])
        sheet_top.update()
        geo2 = sheet._rail_geometry()
        assert geo2 is not None, "the results sheet must have a rail too"
        sheet._on_press(Event(geo2[0] + 3, geo2[1] + geo2[4] * 0.8))
        assert sheet._scroll > 0, "a read-only sheet must still scroll by its rail"
        assert sheet._sel == set(), "a read-only sheet selects nothing"
        sheet_top.destroy()
    finally:
        root.destroy()

    print("ok")


if __name__ == "__main__":
    main()
