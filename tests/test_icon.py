"""Exercise the window icon loader. Run: python tests/test_icon.py

The icon is generated art loaded from disk, so the failure that matters most is
a path that resolves in a source checkout but not inside a frozen build. That
case cannot be reproduced here without freezing the app, so the checks cover
what can be: that the mark loads now, that the exact file build_exe.py bundles
exists, and that missing or unreadable art never stops the window opening.
"""

from __future__ import annotations

import os
import sys
import tkinter as tk

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lyricsdl.ui import icon


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

    # build_exe.py --add-data points at this exact file. If it is renamed, the
    # frozen build loses its window icon and nothing else would notice.
    bundled = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "docs", "art", icon.PNG_NAME)
    assert os.path.exists(bundled), (
        f"{bundled} is what build_exe.py bundles, but it does not exist")

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
