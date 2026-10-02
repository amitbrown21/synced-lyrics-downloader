"""The download engine: turn a list of audio files into ``.lrc`` files.

The engine runs on a worker thread and never touches tkinter directly. It
reports everything through a :class:`Reporter`, which the UI implements to
marshal events onto the main thread. Cancellation is a plain callable so the
UI owns that flag.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Callable, Iterable

from . import config as app_config
from .library import analyze_lrc, lrc_path_for, infer_artist_from_path, normalize_title
from .providers import run_provider, strip_cjk_lines_in_lrc, reject_if_mostly_non_ascii


@dataclass
class Summary:
    total: int = 0
    succeeded: int = 0
    failed: int = 0
    cancelled: bool = False
    artists: set[str] = field(default_factory=set)

    def message(self) -> str:
        verb = "Cancelled" if self.cancelled else "Done"
        return f"{verb}. Downloaded: {self.succeeded}/{self.total} ({self.failed} failed)"


class Reporter:
    """Sink for engine events. Override what you need; the rest are no-ops."""

    def log(self, msg: str, level: str = "info") -> None:
        """*level* is one of info, step, ok, warn, error."""

    def status(self, text: str, kind: str = "normal") -> None:
        """*kind* is one of normal, working, success, error."""

    def progress(self, done: int, total: int) -> None:
        """Fraction complete of the current job, for a progress indicator."""

    def ask_upgrade(self, song_name: str, should_cancel: Callable[[], bool]) -> tuple[bool, bool]:
        """Ask whether to search for a synced version of *song_name*.

        Returns ``(upgrade, upgrade_all)``. Default: do not upgrade.
        """
        return False, False


def _try_synced_upgrade(query, lrc, providers_synced, lang_code, reporter, cancel) -> bool:
    """Search providers for a synced version of an existing plain file.

    Replaces *lrc* in place when a genuinely synced result is found.
    """
    for provider in providers_synced:
        if cancel():
            return False
        reporter.log(f"      trying synced: {provider}", "step")
        temp_lrc = lrc + ".temp"
        if run_provider(query, provider, temp_lrc, lang_code, want_synced=True):
            if analyze_lrc(temp_lrc) == "synced":
                try:
                    # Atomic: never leaves the plain file deleted if the move fails.
                    os.replace(temp_lrc, lrc)
                    reporter.log(f"      Upgraded plain to synced [{provider}]", "ok")
                    return True
                except Exception:
                    pass
            else:
                try:
                    os.remove(temp_lrc)
                except Exception:
                    pass
    return False


def download_targets(
    targets: list[str],
    *,
    music_dir: str,
    reporter: Reporter,
    cancel: Callable[[], bool],
    prompt_upgrades: bool = True,
    headline: str = "Processing",
) -> Summary:
    """Fetch lyrics for every path in *targets*.

    *prompt_upgrades* asks the user before replacing a plain file (the
    selection flow); the missing flow passes False and upgrades silently.
    """
    providers_synced = app_config.config.synced_provider_order()
    providers_plain = app_config.config.plain_provider_order()
    lang_code = app_config.config.lang_code()
    plain_ok = app_config.config.allow_plain_fallback()

    total = len(targets)
    reporter.progress(0, total)
    reporter.status(f"Downloading... ({total} tracks)", "working")
    reporter.log(f"\n{headline} {total} tracks...\n")

    succeeded = failed = 0
    upgrade_all_session = False

    for idx, song in enumerate(targets, 1):
        if cancel():
            reporter.log("Cancelled by user.", "warn")
            break
        reporter.progress(idx - 1, total)

        lrc = lrc_path_for(song)
        song_name = os.path.basename(song)
        title = normalize_title(os.path.splitext(song_name)[0])

        reporter.status(f"[{idx}/{total}] {song_name}", "working")
        reporter.log(f"[{idx}/{total}] Searching: {title}")

        existing_state = None
        if os.path.exists(lrc):
            existing_state = analyze_lrc(lrc)

            if existing_state == "plain" and app_config.config.get("upgrade_plain_to_synced", True):
                reporter.log("   Found plain lyrics (.lrc file)")

                should_upgrade = (
                    (not prompt_upgrades)
                    or app_config.config.get("auto_upgrade_plain", False)
                    or upgrade_all_session
                )
                if should_upgrade:
                    reporter.log("   Auto-upgrading (setting enabled or 'Yes to All' selected)")
                else:
                    upgrade, upgrade_all = reporter.ask_upgrade(song_name, cancel)
                    if cancel():
                        break
                    if upgrade_all:
                        upgrade_all_session = True
                    should_upgrade = upgrade

                if should_upgrade:
                    reporter.log("   Searching for synced version...")
                    artist = infer_artist_from_path(song, music_dir)
                    query = f"{title} {artist}".strip()
                    if _try_synced_upgrade(query, lrc, providers_synced, lang_code, reporter, cancel):
                        succeeded += 1
                    else:
                        reporter.log("      No synced version found, keeping plain .lrc")
                else:
                    reporter.log("   Skipped upgrade, keeping plain .lrc")
                continue

            if existing_state in ("synced", "incomplete"):
                reporter.log("   Skip (already has .lrc)")
                continue

        artist = infer_artist_from_path(song, music_dir)
        query = f"{title} {artist}".strip()

        used = mode = None
        for provider in providers_synced:
            if cancel():
                break
            reporter.log(f"   trying synced: {provider}", "step")
            if run_provider(query, provider, lrc, lang_code, want_synced=True):
                used, mode = provider, "synced"
                break

        if (not os.path.exists(lrc)) and plain_ok and (not cancel()):
            for provider in providers_plain:
                if cancel():
                    break
                reporter.log(f"   trying plain: {provider}", "step")
                if run_provider(query, provider, lrc, lang_code, want_synced=False):
                    used, mode = provider, "plain"
                    break

        if os.path.exists(lrc):
            if app_config.config.get("strip_cjk", True) and strip_cjk_lines_in_lrc(lrc):
                reporter.log("   Stripped CJK lines")
            if reject_if_mostly_non_ascii(lrc):
                reporter.log(f"   Rejected (mostly non-ASCII) [{used}/{mode}]", "warn")
                failed += 1
                continue
            reporter.log(f"   Saved [{used}/{mode}]", "ok")
            succeeded += 1
        else:
            reporter.log("   Not found", "error")
            failed += 1

    reporter.log("\nDone.\n")
    reporter.progress(total, total)

    cancelled = cancel()
    summary = Summary(total=total, succeeded=succeeded, failed=failed, cancelled=cancelled)
    for song in targets:
        artist = infer_artist_from_path(song, music_dir)
        if artist:
            summary.artists.add(artist)

    reporter.status(summary.message(), "error" if cancelled else "success")
    return summary


def run_custom_query(
    song_path: str,
    query: str,
    *,
    reporter: Reporter,
    cancel: Callable[[], bool],
) -> Summary:
    """Fetch lyrics for a single file using a user-supplied query."""
    providers_synced = app_config.config.synced_provider_order()
    providers_plain = app_config.config.plain_provider_order()
    lang_code = app_config.config.lang_code()
    plain_ok = app_config.config.allow_plain_fallback()

    lrc = lrc_path_for(song_path)
    reporter.log(f"\nCustom search for: {os.path.basename(song_path)}")
    reporter.log(f"Query: {query}")

    if os.path.exists(lrc):
        reporter.log("   (Existing .lrc found — deleting and re-downloading)")
        try:
            os.remove(lrc)
        except Exception:
            pass

    used = mode = None
    for provider in providers_synced:
        if cancel():
            break
        reporter.log(f"   trying synced: {provider}", "step")
        if run_provider(query, provider, lrc, lang_code, want_synced=True):
            used, mode = provider, "synced"
            break

    if (not os.path.exists(lrc)) and plain_ok and (not cancel()):
        for provider in providers_plain:
            if cancel():
                break
            reporter.log(f"   trying plain: {provider}", "step")
            if run_provider(query, provider, lrc, lang_code, want_synced=False):
                used, mode = provider, "plain"
                break

    succeeded = failed = 0
    if os.path.exists(lrc):
        if app_config.config.get("strip_cjk", True) and strip_cjk_lines_in_lrc(lrc):
            reporter.log("   Stripped CJK lines")
        if reject_if_mostly_non_ascii(lrc):
            reporter.log(f"   Rejected (mostly non-ASCII) [{used}/{mode}]", "warn")
            failed = 1
        else:
            reporter.log(f"   Saved [{used}/{mode}]", "ok")
            succeeded = 1
    else:
        reporter.log("   Not found", "error")
        failed = 1

    artist = infer_artist_from_path(song_path, app_config.config.get("music_dir", ""))
    summary = Summary(
        total=1,
        succeeded=succeeded,
        failed=failed,
        cancelled=cancel(),
        artists={artist} if artist else set(),
    )
    reporter.status(summary.message(), "error" if summary.cancelled or failed else "success")
    return summary
