#!/usr/bin/env python3
"""Synced Lyrics Downloader — runnable entry point.

Kept as a plain script so the documented command still works:

    python lyrics_downloader_ultimate.py

The application itself now lives in the ``lyricsdl`` package:

    lyricsdl/config.py       settings and constants
    lyricsdl/library.py      folder scanning and lyric-state detection
    lyricsdl/providers.py    provider fetching and quality filters
    lyricsdl/downloader.py   the download engine (thread-safe, UI-free)
    lyricsdl/ui/             the CustomTkinter crate interface
"""

from __future__ import annotations

import sys


def main() -> int:
    try:
        from lyricsdl.ui import run
    except ImportError as exc:  # missing customtkinter or a broken install
        sys.stderr.write(
            "Could not start Synced Lyrics Downloader.\n"
            f"  {exc}\n\n"
            "Install the requirements first:\n"
            "  pip install -r requirements.txt\n"
        )
        return 1
    run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
