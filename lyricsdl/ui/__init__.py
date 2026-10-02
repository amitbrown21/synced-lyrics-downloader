"""Tk/CustomTkinter UI for Synced Lyrics Downloader."""

from __future__ import annotations


def run() -> None:
    from .app import App

    App().run()


__all__ = ["run"]
