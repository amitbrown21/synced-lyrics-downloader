"""Give the window the project mark as its icon.

The mark is generated art (``tools/make_art.py``), so it is loaded from disk
rather than redrawn here, and the same file feeds the executable's icon
resource. Both a source checkout and a frozen build are handled: the frozen
case looks inside the PyInstaller bundle, which ``build_exe.py`` populates.

Why this module exists: without it a source run showed Python's own icon in the
title bar and taskbar, so the app presented two different icons depending on
how it was launched.
"""

from __future__ import annotations

import sys
import tkinter as tk
from pathlib import Path

PNG_NAME = "icon-256.png"
ICO_NAME = "icon.ico"


def _candidates(name: str) -> list[Path]:
    """Every place the asset may live, most specific first."""
    found: list[Path] = []
    if getattr(sys, "frozen", False):
        # Onefile builds unpack beside the executable; onedir builds land in
        # the bundle root. Both are worth trying.
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
        found += [base / "art" / name, base / name]
    repo = Path(__file__).resolve().parents[2]
    found += [repo / "docs" / "art" / name, repo / "build" / name]
    return found


def _find(name: str) -> Path | None:
    return next((path for path in _candidates(name) if path.exists()), None)


def apply(root: tk.Misc) -> tk.PhotoImage | None:
    """Set *root*'s window icon, returning the image the caller must keep.

    Tk holds only a weak reference to a PhotoImage, so a caller that drops it
    gets a window with no icon. Art that is missing or unreadable is not fatal:
    the window still opens, it just keeps the default icon.
    """
    png = _find(PNG_NAME)
    if png is not None:
        try:
            image = tk.PhotoImage(file=str(png))
        except tk.TclError:
            image = None      # this Tk has no PNG support; try the .ico instead
        if image is not None:
            try:
                root.iconphoto(True, image)
                return image
            except tk.TclError:
                pass

    if sys.platform == "win32":
        ico = _find(ICO_NAME)
        if ico is not None:
            try:
                # -default also covers every dialog opened later.
                root.iconbitmap(default=str(ico))
            except tk.TclError:
                pass
    return None
