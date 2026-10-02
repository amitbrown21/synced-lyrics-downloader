#!/usr/bin/env python3
"""Build the distributable Windows executable.

    python build_exe.py

Generates the application icon from the shipped design tokens (so the icon can
never drift from the palette), then freezes the app into a single ``.exe`` with
PyInstaller.

The result is one self-contained program. It does not need Python, tkinter or
``syncedlyrics`` installed: the lyrics engine is bundled, and
:func:`lyricsdl.providers.backend` falls back to calling it in-process when the
``syncedlyrics`` command is not on PATH.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BUILD = ROOT / "build"
DIST = ROOT / "dist"
ENTRY = "lyrics_downloader_ultimate.py"
APP_NAME = "SyncedLyricsDownloader"

sys.path.insert(0, str(ROOT))


def make_icon() -> Path:
    """Draw the app icon from the design palette and return the .ico path."""
    from PIL import Image, ImageDraw

    from lyricsdl.ui import theme as T

    def hexc(value: str) -> tuple[int, int, int]:
        return tuple(int(value[i:i + 2], 16) for i in (1, 3, 5))

    def render(size: int) -> Image.Image:
        # Draw large, then downsample: keeps the strokes even at 16px.
        ss = 8
        px = size * ss
        img = Image.new("RGB", (px, px), hexc(T.STOCK))
        d = ImageDraw.Draw(img)

        # The crate's signature element: a silkscreen tab down the left edge.
        tab = int(px * 0.22)
        d.rectangle([0, 0, tab, px], fill=hexc(T.RED))

        # The synced state mark — the same circled check the lists stamp.
        cx = tab + (px - tab) / 2
        cy = px / 2
        r = (px - tab) * 0.34
        w = max(ss, int(px * 0.055))
        d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=hexc(T.GREEN_INK), width=w)
        d.line(
            [cx - r * 0.45, cy, cx - r * 0.08, cy + r * 0.42, cx + r * 0.5, cy - r * 0.4],
            fill=hexc(T.GREEN_INK), width=w, joint="curve",
        )
        return img.resize((size, size), Image.LANCZOS)

    sizes = [16, 24, 32, 48, 64, 128, 256]
    base = render(256)
    BUILD.mkdir(exist_ok=True)
    icon = BUILD / "icon.ico"
    base.save(icon, format="ICO", sizes=[(s, s) for s in sizes])
    print(f"icon: {icon} ({', '.join(str(s) for s in sizes)})")
    return icon


def make_version_file(version: str) -> Path:
    """Windows version metadata, so the exe is not an anonymous blob."""
    parts = (version.split("+")[0].split("-")[0]).split(".")
    while len(parts) < 4:
        parts.append("0")
    quad = ", ".join(str(int(p)) for p in parts[:4])
    text = f"""VSVersionInfo(
  ffi=FixedFileInfo(filevers=({quad}), prodvers=({quad}), mask=0x3f, flags=0x0,
    OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('040904B0', [
      StringStruct('CompanyName', 'Amit Brounstine'),
      StringStruct('FileDescription', 'Synced Lyrics Downloader'),
      StringStruct('FileVersion', '{version}'),
      StringStruct('InternalName', '{APP_NAME}'),
      StringStruct('OriginalFilename', '{APP_NAME}.exe'),
      StringStruct('ProductName', 'Synced Lyrics Downloader'),
      StringStruct('ProductVersion', '{version}')])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"""
    path = BUILD / "version_info.txt"
    path.write_text(text, encoding="utf-8")
    return path


def build() -> Path:
    from lyricsdl import __version__

    if BUILD.exists():
        shutil.rmtree(BUILD)
    BUILD.mkdir(parents=True)

    icon = make_icon()
    version_file = make_version_file(__version__)

    args = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm", "--clean",
        "--onefile",
        "--windowed",
        "--name", APP_NAME,
        "--icon", str(icon),
        "--version-file", str(version_file),
        "--distpath", str(DIST),
        "--workpath", str(BUILD / "work"),
        "--specpath", str(BUILD),
        # customtkinter ships theme JSON and font assets that must travel along.
        "--collect-all", "customtkinter",
        # The whole lyrics engine, so the frozen app never needs pip.
        "--collect-submodules", "syncedlyrics",
        # requests needs its CA bundle or TLS fails inside the bundle.
        "--collect-data", "certifi",
        "--hidden-import", "tkinter.filedialog",
        ENTRY,
    ]
    print("pyinstaller:", " ".join(args[2:]))
    result = subprocess.run(args, cwd=str(ROOT))
    if result.returncode != 0:
        raise SystemExit(f"PyInstaller failed with code {result.returncode}")

    exe = DIST / f"{APP_NAME}.exe"
    if not exe.exists():
        raise SystemExit(f"expected {exe}, but it was not produced")
    print(f"\nbuilt {exe}  ({exe.stat().st_size / 1_048_576:.1f} MB)")
    return exe


if __name__ == "__main__":
    os.environ.setdefault("PYTHONUTF8", "1")
    build()
