"""Application constants and the persisted settings dict.

This module owns the single mutable :data:`config` object that the rest of the
app reads and writes. It is deliberately a thin, behaviour-preserving port of
the settings block from the original single-file script.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

APP_NAME = "Synced Lyrics Downloader"


def _data_dir() -> Path:
    """The durable directory for user settings.

    When frozen (PyInstaller), ``__file__`` resolves inside the temporary
    bundle directory, which is deleted on exit — anything written there would
    silently vanish between runs. Beside the executable is the only durable
    choice. From source this is still the repo root, so existing users keep
    their saved settings.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


PROJECT_ROOT = _data_dir()
CONFIG_FILE = str(PROJECT_ROOT / "lyrics_gui_config.json")

DEFAULT_GITHUB_URL = "https://github.com/amitbrown21/synced-lyrics-downloader"
SYNCEDLYRICS_URL = "https://pypi.org/project/syncedlyrics/"

ALL_PROVIDERS = ["Lrclib", "Musixmatch", "Megalobiz", "NetEase", "Genius"]


class Config(dict):
    """A settings dict with persistence and provider-order helpers."""

    def save(self) -> None:
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self, f, indent=2)
        except Exception:
            pass

    # -- provider / quality accessors -------------------------------------

    def lang_code(self) -> str:
        return self.get("lang", "en")

    def allow_plain_fallback(self) -> bool:
        return bool(self.get("allow_plain_fallback", False))

    def enabled_providers_in_order(self) -> list[str]:
        enabled = self.get("providers_enabled", {})
        order = self.get("providers_order", [])
        out = [p for p in order if enabled.get(p, False)]
        return out if out else ["Lrclib"]

    def synced_provider_order(self) -> list[str]:
        return [p for p in self.enabled_providers_in_order() if p != "Genius"]

    def plain_provider_order(self) -> list[str]:
        return self.enabled_providers_in_order()

    def workers(self) -> int:
        """How many tracks to look up at once. Clamped to a sane range."""
        try:
            return max(1, min(16, int(self.get("concurrency", 4))))
        except Exception:
            return 4


def load() -> Config:
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return Config(data)
        except Exception:
            pass
    return Config()


def _with_defaults(cfg: Config) -> Config:
    cfg.setdefault("music_dir", "")
    cfg.setdefault("theme", "dark")
    cfg.setdefault("providers_order", list(ALL_PROVIDERS))
    default_enabled = {p: True for p in ALL_PROVIDERS}
    default_enabled["Genius"] = False
    cfg.setdefault("providers_enabled", default_enabled)
    cfg.setdefault("lang", "en")
    cfg.setdefault("allow_plain_fallback", False)
    cfg.setdefault("upgrade_plain_to_synced", True)
    cfg.setdefault("auto_upgrade_plain", False)
    cfg.setdefault("strip_cjk", True)
    cfg.setdefault("reject_non_ascii", True)
    cfg.setdefault("reject_non_ascii_ratio", 0.15)
    cfg.setdefault("concurrency", 4)
    return cfg


config = _with_defaults(load())
config.save()
