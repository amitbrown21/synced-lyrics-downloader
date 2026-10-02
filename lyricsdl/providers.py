"""Provider fetching and lyric post-processing.

Wraps the ``syncedlyrics`` command-line tool and applies the quality filters
(CJK stripping, mostly-non-ASCII rejection). No UI here.
"""

from __future__ import annotations

import os
import re
import subprocess

from . import config as app_config

CJK_RE = re.compile(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uac00-\ud7af]")

_LRC_META_PREFIXES = ("[ar:", "[ti:", "[al:", "[by:", "[offset:", "[re:", "[ve:")

# A provider that never returns must not pin a worker thread forever: with a
# pool, one hung child would stall the whole job and Cancel could not end it.
PROVIDER_TIMEOUT = 120


def cli_available() -> bool:
    """Is the ``syncedlyrics`` console script on this machine?"""
    from shutil import which
    return which("syncedlyrics") is not None


def run_provider(query: str, provider: str, out_path: str, lang_code: str, want_synced: bool) -> bool:
    """Run one provider into *out_path*; return True if a usable file landed."""
    if os.path.exists(out_path):
        try:
            os.remove(out_path)
        except Exception:
            pass

    cmd = ["syncedlyrics", query, "-p", provider, "-o", out_path]
    cmd.append("--synced-only" if want_synced else "--plain-only")
    if lang_code:
        cmd.extend(["--lang", lang_code])

    # One provider failing (timeout, missing CLI, crash) must not kill the run.
    try:
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       timeout=PROVIDER_TIMEOUT)
    except Exception:
        return False
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
