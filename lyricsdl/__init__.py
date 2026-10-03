"""Synced Lyrics Downloader — package root.

The application is split into a headless *core* (this package's top-level
modules) and a Tk/CustomTkinter *UI* (:mod:`lyricsdl.ui`). Nothing in the core
imports tkinter, so the fetching and library logic can be tested and reused
without a display.
"""

__all__ = ["config", "library", "providers", "downloader", "ui"]

# Single source of truth for the release version (shown in About, stamped on
# the Windows executable, and used for the git tag).
__version__ = "1.0.3"
