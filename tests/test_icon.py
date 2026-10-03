"""Exercise the window icon loader. Run: python tests/test_icon.py

The icon is generated art loaded from disk, so the failure that matters most is
a path that resolves in a source checkout but not inside a frozen build. That
case cannot be reproduced here without freezing the app, so the checks cover
what can be: that the mark loads now, that the exact files build_exe.py bundles
exist, that Windows gets both the PNG and the .ico, that the process claims its
own taskbar identity, and that missing or unreadable art never stops the window
opening.
"""

from __future__ import annotations

import ctypes
import os
import sys
import tkinter as tk

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lyricsdl.ui import icon

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main() -> None:
    root = tk.Tk()
    root.withdraw()
    try:
        image = icon.apply(root)
        assert image is not None, (
            "the window icon did not load; the mark PNG is missing or unreadable")
        assert (image.width(), image.height()) == (256, 256), (
            f"expected the 256px mark, got {image.width()}x{image.height()}")
    finally:
        root.destroy()

    # build_exe.py --add-data points at these exact files. If either is
    # renamed, the frozen build loses its window icon and nothing else notices.
    # The .ico is not redundant: on Windows it is the one that reaches the
    # taskbar, so losing it is what made the taskbar show the launcher's icon.
    for name in (icon.PNG_NAME, icon.ICO_NAME):
        bundled = os.path.join(ROOT, "docs", "art", name)
        assert os.path.exists(bundled), (
            f"{bundled} is what build_exe.py bundles, but it does not exist")

    # The identity must actually take. A process that declares none inherits
    # its launcher's, and then Windows draws the launcher's icon on our
    # taskbar button — the exact bug this guards.
    if sys.platform == "win32":
        icon.claim_taskbar_identity()
        declared = ctypes.c_wchar_p()
        hr = ctypes.windll.shell32.GetCurrentProcessExplicitAppUserModelID(
            ctypes.byref(declared))
        assert hr == 0, f"could not read back the taskbar identity (hr={hr})"
        assert declared.value == icon.APP_USER_MODEL_ID, (
            f"the process claims identity {declared.value!r}, expected "
            f"{icon.APP_USER_MODEL_ID!r}")

    # Missing art must degrade, not raise: a build without the PNG still opens.
    real_find = icon._find
    icon._find = lambda name: None
    root = tk.Tk()
    root.withdraw()
    try:
        assert icon.apply(root) is None, "missing art should yield no image"
    finally:
        root.destroy()
        icon._find = real_find

    print("ok")


if __name__ == "__main__":
    main()
