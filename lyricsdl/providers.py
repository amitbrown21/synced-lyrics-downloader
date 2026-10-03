"""Provider fetching and lyric post-processing.

Wraps the ``syncedlyrics`` command-line tool and applies the quality filters
(CJK stripping, mostly-non-ASCII rejection). No UI here.
"""

from __future__ import annotations

import logging
import os
import re
import subprocess
import threading

from . import config as app_config

CJK_RE = re.compile(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uac00-\ud7af]")

_LRC_META_PREFIXES = ("[ar:", "[ti:", "[al:", "[by:", "[offset:", "[re:", "[ve:")

# A provider that never returns must not pin a worker thread forever: with a
# pool, one hung child would stall the whole job and Cancel could not end it.
PROVIDER_TIMEOUT = 120

# Providers attach a log handler in their constructor and send their logs to
# stderr, which a frozen --windowed build does not have. Silence them; the app
# reports outcomes itself, on the results sheet.
_PROVIDER_LOGGERS = ("Musixmatch", "Lrclib", "NetEase", "Megalobiz", "Genius",
                     "Deezer", "Lyricsify")
_logging_lock = threading.Lock()

# Lookups that overran the timeout. Python threads cannot be killed, so an
# overrun is abandoned rather than stopped. Counting is all this does — it must
# never gate a lookup, because refusing to start one is indistinguishable from
# "the lyrics do not exist", and a track reported missing when it was never
# searched is worse than any leak.
_abandoned_lock = threading.Lock()
_abandoned_total = 0


def overruns() -> int:
    """How many lookups overran :data:`PROVIDER_TIMEOUT` and were abandoned."""
    with _abandoned_lock:
        return _abandoned_total


def _silence_provider_loggers() -> None:
    """Stop syncedlyrics from leaking a log handler per lookup.

    Every provider instance adds a StreamHandler in its constructor, so a bulk
    job piles up thousands of them, each writing to a stream that does not
    exist in a windowed build. One NullHandler each, above the effective level,
    keeps it both quiet and bounded.
    """
    with _logging_lock:
        for name in _PROVIDER_LOGGERS:
            logger = logging.getLogger(name)
            logger.handlers = [logging.NullHandler()]
            logger.setLevel(logging.CRITICAL + 1)


def backend() -> str:
    """Which engine will service lookups: ``cli``, ``inproc``, or ``none``.

    ``cli`` shells out to the ``syncedlyrics`` command (process isolation and a
    hard timeout). ``inproc`` calls the library in this process, which is how
    the frozen executable works on a machine with nothing installed. The
    ``LYRICSDL_BACKEND`` environment variable forces one, for testing.
    """
    forced = os.environ.get("LYRICSDL_BACKEND", "").strip().lower()
    if forced in ("cli", "inproc", "none"):
        return forced
    from shutil import which
    if which("syncedlyrics"):
        return "cli"
    try:
        import syncedlyrics  # noqa: F401
    except Exception:
        return "none"
    return "inproc"


def cli_available() -> bool:
    """Is the ``syncedlyrics`` console script on this machine?"""
    return backend() == "cli"


def _run_in_process(query: str, provider: str, out_path: str,
                    lang_code: str, want_synced: bool) -> None:
    """Look up *out_path* via the syncedlyrics library, in this process.

    The call runs on a daemon thread so a hung request cannot pin the calling
    worker forever. If it overruns, the thread is abandoned rather than stopped
    and this returns having written nothing — but every lookup is attempted, no
    matter how many have already overrun. Refusing to start one would be
    indistinguishable from "the lyrics do not exist", and reporting a track as
    missing when it was never actually searched is worse than any leak.
    """
    import syncedlyrics

    _silence_provider_loggers()
    state: dict = {}

    def call() -> None:
        try:
            # Same arguments the official CLI passes, minus save_path: that
            # runs str.format() on the path, which a brace in a folder name
            # would turn into a crash. Writing the returned string here is
            # byte-identical, since save_lrc_file just writes to_str().
            state["text"] = syncedlyrics.search(
                query,
                plain_only=not want_synced,
                synced_only=want_synced,
                providers=[provider],
                lang=lang_code or None,
            )
        except Exception:
            state["text"] = None
        finally:
            _silence_provider_loggers()
            # "done" is set under the same lock the caller checks, so a lookup
            # that finishes just after the timeout is not miscounted as
            # abandoned.
            with _abandoned_lock:
                state["done"] = True

    worker = threading.Thread(target=call, daemon=True)
    worker.start()
    worker.join(PROVIDER_TIMEOUT)
    with _abandoned_lock:
        abandoned = not state.get("done")
        if abandoned:
            global _abandoned_total
            _abandoned_total += 1
    if abandoned:
        return

    text = state.get("text")
    if text:
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(text)


def run_provider(query: str, provider: str, out_path: str, lang_code: str, want_synced: bool) -> bool:
    """Run one provider into *out_path*; return True if a usable file landed."""
    if os.path.exists(out_path):
        try:
            os.remove(out_path)
        except Exception:
            pass

    how = backend()
    if how == "cli":
        cmd = ["syncedlyrics", query, "-p", provider, "-o", out_path]
        cmd.append("--synced-only" if want_synced else "--plain-only")
        if lang_code:
            cmd.extend(["--lang", lang_code])
        # CREATE_NO_WINDOW: a windowed GUI build must not flash a console for
        # every lookup. One provider failing must also not kill the run.
        flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        try:
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           timeout=PROVIDER_TIMEOUT, creationflags=flags)
        except Exception:
            return False
    elif how == "inproc":
        _run_in_process(query, provider, out_path, lang_code, want_synced)

    return os.path.exists(out_path) and os.path.getsize(out_path) > 50


def strip_cjk_lines_in_lrc(path: str) -> bool:
    """Remove lyric lines containing CJK characters. Returns True if changed."""
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.read().splitlines()
    except Exception:
        return False

    kept: list[str] = []
    changed = False
    for line in lines:
        if line.startswith(_LRC_META_PREFIXES):
            kept.append(line)
            continue
        if "]" in line:
            text = line.rsplit("]", 1)[-1].strip()
            if text and CJK_RE.search(text):
                changed = True
                continue
        kept.append(line)

    try:
        with open(path, "w", encoding="utf-8", errors="ignore") as f:
            f.write("\n".join(kept).strip() + "\n")
    except Exception:
        return False
    return changed


def reject_if_mostly_non_ascii(path: str, *, enabled: bool | None = None, ratio_limit: float | None = None) -> bool:
    """Delete *path* and return True when it is mostly non-ASCII."""
    if enabled is None:
        enabled = app_config.config.get("reject_non_ascii", True)
    if not enabled:
        return False
    if ratio_limit is None:
        ratio_limit = float(app_config.config.get("reject_non_ascii_ratio", 0.15))

    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except Exception:
        return False

    non_ascii = sum(1 for c in content if ord(c) > 127)
    ratio = non_ascii / max(len(content), 1)
    if ratio > ratio_limit:
        try:
            os.remove(path)
        except Exception:
            pass
        return True
    return False


def handle_plain_lyrics(lrc_path: str) -> str:
    """If a ``.lrc`` file holds plain lyrics, rename it to ``.txt``.

    Returns the final path (``.lrc`` or ``.txt``).
    """
    from .library import analyze_lrc  # local import avoids a cycle

    if not os.path.exists(lrc_path) or analyze_lrc(lrc_path) != "plain":
        return lrc_path

    txt_path = os.path.splitext(lrc_path)[0] + ".txt"
    try:
        if os.path.exists(txt_path):
            os.remove(txt_path)
        os.rename(lrc_path, txt_path)
        return txt_path
    except Exception:
        return lrc_path
