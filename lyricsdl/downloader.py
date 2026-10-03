"""The download engine: turn a list of audio files into ``.lrc`` files.

The engine runs on a worker thread and never touches tkinter directly. It
reports everything through a :class:`Reporter`, which the UI implements to
marshal events onto the main thread. Cancellation is a plain callable so the
UI owns that flag.
"""

from __future__ import annotations

import os
import shutil
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Callable, Iterable

from . import config as app_config
from .library import analyze_lrc, lrc_path_for, infer_artist_from_path, normalize_title
from .providers import (backend, overruns, reject_if_mostly_non_ascii,
                        run_provider, strip_cjk_lines_in_lrc)

# States that mean "lyrics were written just now".
SUCCESS_STATES = ("synced", "plain", "upgraded")

# Some providers stop serving for good (an API change, a block, a dead domain)
# while the rest keep working. `run_provider` reports "this provider is broken"
# and "this provider does not have that song" identically, so the only way to
# tell them apart is to ask for a track every working provider has. A provider
# that cannot answer this one is not going to answer anything else either.
HEALTH_QUERY = "Bohemian Rhapsody Queen"


@dataclass
class WorkItem:
    """One track whose lyrics still have to be fetched."""

    path: str
    lrc: str
    title: str
    query: str
    upgrade: bool = False   # replacing an existing plain file, atomically


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
    """Sink for engine events. Override what you need; the rest are no-ops.

    Every method may be called from any worker thread, so implementations must
    marshal onto their own UI thread rather than touching widgets directly.
    """

    def log(self, msg: str, level: str = "info") -> None:
        """*level* is one of info, step, ok, warn, error."""

    def status(self, text: str, kind: str = "normal") -> None:
        """*kind* is one of normal, working, success, error."""

    def progress(self, done: int, total: int) -> None:
        """Fraction complete of the current job, for a progress indicator."""

    def track(self, path: str, state: str, detail: str = "") -> None:
        """One track changed state — the per-track result feed.

        *state* is one of: queued, working, synced, plain, upgraded, kept,
        skipped, failed, cancelled. *detail* is the provider that answered, or
        the reason there is none ("not found", "mostly non-ASCII", …).

        ``kept`` means existing plain lyrics were left alone: neither a write
        nor a failure, so it counts as neither in the summary.
        """

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


def _probe_providers(names: list[str], *, lang_code: str | None) -> set[str]:
    """Which of *names* actually answer a canonical query.

    Probed concurrently, so the whole check costs about one lookup. Returns the
    set that answered; an empty set means nothing answered, which the caller
    treats as "the probe failed", not "every provider is dead".
    """
    if not names:
        return set()
    tmpdir = tempfile.mkdtemp(prefix="sl-health-")
    try:
        def probe(name: str) -> tuple[str, bool]:
            out = os.path.join(tmpdir, f"{name}.lrc")
            try:
                return name, bool(run_provider(HEALTH_QUERY, name, out, lang_code, True))
            except Exception:
                return name, False

        with ThreadPoolExecutor(max_workers=len(names)) as pool:
            return {name for name, ok in pool.map(probe, names) if ok}
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def _fetch_item(item: WorkItem, *, providers_synced, providers_plain, lang_code,
                plain_ok, reporter, cancel) -> tuple[str, str]:
    """Fetch lyrics for one work item. Runs on a pool thread.

    Returns ``(state, detail)`` where *detail* is the provider that answered or
    the reason none did. Only ever writes *item.lrc* through a verified path, so
    the caller can treat a failure as "nothing changed on disk".
    """
    reporter.track(item.path, "working")

    if item.upgrade:
        if _try_synced_upgrade(item.query, item.lrc, providers_synced, lang_code, reporter, cancel):
            return "upgraded", ""
        if cancel():
            return "cancelled", ""
        reporter.log("      No synced version found, keeping plain .lrc")
        return "kept", "no synced found"

    lrc = item.lrc
    used = mode = None

    for provider in providers_synced:
        if cancel():
            return "cancelled", ""
        reporter.log(f"   trying synced: {provider}", "step")
        if run_provider(item.query, provider, lrc, lang_code, want_synced=True):
            used, mode = provider, "synced"
            break

    if (not os.path.exists(lrc)) and plain_ok and (not cancel()):
        for provider in providers_plain:
            if cancel():
                break
            reporter.log(f"   trying plain: {provider}", "step")
            if run_provider(item.query, provider, lrc, lang_code, want_synced=False):
                used, mode = provider, "plain"
                break

    if not os.path.exists(lrc):
        if cancel():
            return "cancelled", ""
        reporter.log("   Not found", "error")
        return "failed", "not found"

    if app_config.config.get("strip_cjk", True) and strip_cjk_lines_in_lrc(lrc):
        reporter.log("   Stripped CJK lines")
    if reject_if_mostly_non_ascii(lrc):
        reporter.log(f"   Rejected (mostly non-ASCII) [{used}/{mode}]", "warn")
        return "failed", "mostly non-ASCII"

    reporter.log(f"   Saved [{used}/{mode}]", "ok")
    return (mode or "plain"), (used or "")


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

    Two phases. Planning is sequential because it may raise a modal upgrade
    prompt and must settle "Yes to all" in one place. Fetching is a thread pool:
    each lookup shells out to the ``syncedlyrics`` CLI, so the tracks are
    independent processes and nothing is shared but the reporter.

    *prompt_upgrades* asks the user before replacing a plain file (the
    selection flow); the missing flow passes False and upgrades silently.
    """
    providers_synced = app_config.config.synced_provider_order()
    providers_plain = app_config.config.plain_provider_order()
    lang_code = app_config.config.lang_code()
    plain_ok = app_config.config.allow_plain_fallback()
    workers = app_config.config.workers()

    total = len(targets)
    reporter.progress(0, total)
    reporter.status(f"Downloading... ({total} tracks)", "working")
    reporter.log(f"\n{headline} {total} tracks, {workers} at a time...\n")
    how = backend()
    if how == "none":
        reporter.log("syncedlyrics is unavailable — every lookup will fail. "
                     "Install it with: pip install syncedlyrics", "error")
    else:
        reporter.log(f"Provider engine: {how}", "step")

    # -- phase 1: plan (sequential; may prompt) ----------------------------
    items: list[WorkItem] = []
    claimed: set[str] = set()
    done = 0
    upgrade_all_session = False

    for song in targets:
        if cancel():
            break
        lrc = lrc_path_for(song)
        song_name = os.path.basename(song)
        title = normalize_title(os.path.splitext(song_name)[0])
        artist = infer_artist_from_path(song, music_dir)
        query = f"{title} {artist}".strip()

        if lrc in claimed:
            # Two formats of one song (say .flac and .mp3) share a single .lrc.
            # Fetch it once; the second is not a failure, just redundant.
            reporter.track(song, "skipped", "duplicate .lrc")
            done += 1
            reporter.progress(done, total)
            continue
        claimed.add(lrc)

        if os.path.exists(lrc):
            existing_state = analyze_lrc(lrc)

            if existing_state == "plain":
                # Never fetch straight over a plain file: run_provider deletes
                # its target first, so a failed lookup would destroy lyrics the
                # user already had. Upgrade atomically instead.
                should_upgrade = (
                    (not app_config.config.get("upgrade_plain_to_synced", True))
                    or (not prompt_upgrades)
                    or app_config.config.get("auto_upgrade_plain", False)
                    or upgrade_all_session
                )
                if should_upgrade:
                    reporter.log("   Found plain lyrics — looking for a synced version")
                else:
                    reporter.track(song, "working")
                    upgrade, upgrade_all = reporter.ask_upgrade(song_name, cancel)
                    if cancel():
                        reporter.track(song, "cancelled", "stopped before lookup")
                        break
                    if upgrade_all:
                        upgrade_all_session = True
                    should_upgrade = upgrade

                if should_upgrade:
                    items.append(WorkItem(path=song, lrc=lrc, title=title,
                                          query=query, upgrade=True))
                else:
                    reporter.log("   Skipped upgrade, keeping plain .lrc")
                    reporter.track(song, "kept", "upgrade declined")
                    done += 1
                    reporter.progress(done, total)
                continue

            if existing_state in ("synced", "incomplete"):
                reporter.log("   Skip (already has .lrc)")
                reporter.track(song, "skipped", "already there")
                done += 1
                reporter.progress(done, total)
                continue

        reporter.log(f"Searching: {title}")
        items.append(WorkItem(path=song, lrc=lrc, title=title, query=query))

    # -- phase 2: fetch (concurrent) ---------------------------------------
    results: list[tuple[str, str]] = []
    if items and not cancel():
        # Before hammering one dead provider per track, find out which ones are
        # serving at all. Skipped providers are reported rather than silently
        # dropped, since a missing provider is a missing chance at lyrics.
        candidates = list(dict.fromkeys(providers_synced + providers_plain))
        healthy = _probe_providers(candidates, lang_code=lang_code)
        if not healthy:
            reporter.log("No provider answered the check — "
                         "asking them all anyway.", "warn")
        else:
            dead = [p for p in candidates if p not in healthy]
            if dead:
                reporter.log(f"Providers not answering: {', '.join(dead)}", "warn")
            providers_synced = [p for p in providers_synced if p in healthy]
            providers_plain = [p for p in providers_plain if p in healthy]
            working = list(dict.fromkeys(providers_synced + providers_plain))
            if working:
                reporter.log(f"Using: {', '.join(working)}", "step")
            else:
                reporter.log("No provider can answer — every lookup will fail.", "error")

        reporter.status(f"Downloading... 0/{total}", "working")
        with ThreadPoolExecutor(max_workers=min(workers, len(items))) as pool:
            futures = {
                pool.submit(_fetch_item, item,
                            providers_synced=providers_synced,
                            providers_plain=providers_plain,
                            lang_code=lang_code, plain_ok=plain_ok,
                            reporter=reporter, cancel=cancel): item
                for item in items
            }
            for future in as_completed(futures):
                item = futures[future]
                try:
                    state, detail = future.result()
                except Exception as exc:  # a worker must never vanish silently
                    state, detail = "failed", f"error: {exc}"
                    reporter.log(f"   {exc}", "error")
                done += 1
                reporter.progress(done, total)
                reporter.track(item.path, state, detail)
                results.append((state, detail))
                reporter.status(f"Downloading... {done}/{total}", "working")

    succeeded = sum(1 for state, _ in results if state in SUCCESS_STATES)
    failed = sum(1 for state, _ in results if state == "failed")
    cancelled = cancel()

    # A lookup that overran its timeout was abandoned, not searched. Say so
    # rather than letting it look like the lyrics simply do not exist.
    stalled = overruns()
    if stalled:
        reporter.log(f"{stalled} lookup(s) overran the provider timeout and were "
                     "abandoned — check the connection and retry those tracks.", "warn")

    reporter.log("\nDone.\n")
    reporter.progress(total, total)

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
    lrc = lrc_path_for(song_path)
    title = normalize_title(os.path.splitext(os.path.basename(song_path))[0])
    reporter.log(f"\nCustom search for: {os.path.basename(song_path)}")
    reporter.log(f"Query: {query}")

    if os.path.exists(lrc):
        reporter.log("   (Existing .lrc found — deleting and re-downloading)")
        try:
            os.remove(lrc)
        except Exception:
            pass

    # Same worker the bulk flow uses, so the two can never drift apart.
    state, detail = _fetch_item(
        WorkItem(path=song_path, lrc=lrc, title=title, query=query),
        providers_synced=app_config.config.synced_provider_order(),
        providers_plain=app_config.config.plain_provider_order(),
        lang_code=app_config.config.lang_code(),
        plain_ok=app_config.config.allow_plain_fallback(),
        reporter=reporter, cancel=cancel,
    )
    reporter.track(song_path, state, detail)

    succeeded = 1 if state in SUCCESS_STATES else 0
    failed = 1 if state == "failed" else 0
    artist = infer_artist_from_path(song_path, app_config.config.get("music_dir", ""))
    summary = Summary(
        total=1,
        succeeded=succeeded,
        failed=failed,
        cancelled=state == "cancelled",
        artists={artist} if artist else set(),
    )
    reporter.status(summary.message(), "error" if summary.cancelled or failed else "success")
    return summary
