"""Library scanning over the standard ``Artist / Album / Track`` folder tree.

Pure filesystem logic: no tkinter, no display. Callers (the UI) ask this module
for the *state* of a folder or file and render their own iconography; the core
never returns emoji or display strings.

States
------
Album/artist completeness: ``"all"`` | ``"some"`` | ``"none"``
Track lyric state:         ``"synced"`` | ``"plain"`` | ``"incomplete"`` | ``"none"``
"""

from __future__ import annotations

import os
import re

AUDIO_EXTS = (".mp3", ".flac")
_LRC_META_PREFIXES = ("[ar:", "[ti:", "[al:", "[by:", "[offset:", "[re:", "[ve:")

TS_RE = re.compile(r"^\s*\[\d{1,2}:\d{2}(?:\.\d{1,3})?\]", re.MULTILINE)

# Folder-scan cache, keyed by (path, mtime, kind). Shared process-wide.
lyrics_cache: dict = {}
# Artists the user has explicitly scanned this session (drives icon display).
scanned_artists: set[str] = set()


# --------------------------------------------------------------------------
# Path helpers
# --------------------------------------------------------------------------

def is_audio(path: str) -> bool:
    return path.lower().endswith(AUDIO_EXTS)


def lrc_path_for(song_path: str) -> str:
    return os.path.splitext(song_path)[0] + ".lrc"


def strip_leading_glyph(s: str) -> str:
    """Drop a leading icon/whitespace run from a display string.

    Retained for parity with the original UI, which prefixed list rows with an
    emoji; the redesigned UI keeps icons out of the string, but the helper is
    still used when parsing any legacy text.
    """
    return re.sub(r"^[\U00000080-\U0010ffff\ufe0f]+\s*", "", s).strip()


def dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


# --------------------------------------------------------------------------
# Enumeration
# --------------------------------------------------------------------------

def list_artists(music_dir: str) -> list[str]:
    try:
        return sorted(
            name for name in os.listdir(music_dir)
            if os.path.isdir(os.path.join(music_dir, name))
        )
    except Exception:
        return []


def list_albums(artist_path: str) -> list[str]:
    try:
        return sorted(
            name for name in os.listdir(artist_path)
            if os.path.isdir(os.path.join(artist_path, name))
        )
    except Exception:
        return []


def find_audio_files(root: str) -> list[str]:
    """Every ``.mp3``/``.flac`` at or under *root*, sorted."""
    if os.path.isfile(root):
        return [root] if is_audio(root) else []
    out: list[str] = []
    for root_dir, _dirs, files in os.walk(root):
        for name in sorted(files):
            if name.lower().endswith(AUDIO_EXTS):
                out.append(os.path.join(root_dir, name))
    return out


def find_missing(paths: list[str]) -> list[str]:
    """Audio files under the given roots that have no sibling ``.lrc``."""
    missing: list[str] = []
    seen: set[str] = set()
    for root in paths:
        for song in find_audio_files(root):
            if song in seen:
                continue
            seen.add(song)
            if not os.path.exists(lrc_path_for(song)):
                missing.append(song)
    return missing


# --------------------------------------------------------------------------
# Lyric-file inspection
# --------------------------------------------------------------------------

def analyze_lrc(lrc_path: str) -> str:
    """Classify an ``.lrc`` file: synced / plain / incomplete / none."""
    if not os.path.exists(lrc_path):
        return "none"
    try:
        with open(lrc_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = [ln.strip() for ln in f.read().splitlines()]
    except Exception:
        return "none"

    lyric_lines = [ln for ln in lines if ln and not ln.startswith(_LRC_META_PREFIXES)]
    if len(lyric_lines) < 6:
        return "incomplete"
    ts_lines = sum(1 for ln in lyric_lines if TS_RE.match(ln))
    return "synced" if ts_lines >= 3 else "plain"


def track_state(song_path: str) -> str:
    """Lyric state for an audio file (``"none"`` when no ``.lrc`` exists)."""
    return analyze_lrc(lrc_path_for(song_path))


def last_timestamp(lrc_path: str) -> str:
    """The final ``[mm:ss]`` in a lyric file, as ``"mm:ss"`` (or ``""``).

    A useful, honest stand-in for a track's length in the tracklist: it is the
    timestamp of the last synced line.
    """
    try:
        with open(lrc_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except Exception:
        return ""
    last = None
    for last in TS_RE.finditer(content):
        pass
    if last is None:
        return ""
    mm, ss = last.group(0).strip("[]").split(":")[:2]
    try:
        return f"{int(mm):02d}:{int(float(ss)):02d}"
    except Exception:
        return ""


# --------------------------------------------------------------------------
# Folder completeness (with mtime-keyed cache)
# --------------------------------------------------------------------------

def quick_mtime(folder: str) -> int:
    """Cheap change signal: newest mtime of *folder* and its immediate children.

    Enough to notice new albums/tracks without walking the whole tree.
    """
    newest = 0
    try:
        newest = max(newest, int(os.path.getmtime(folder)))
        for entry in os.scandir(folder):
            if entry.is_dir():
                newest = max(newest, int(entry.stat().st_mtime))
    except Exception:
        pass
    return newest


def scan_folder_completeness(folder: str) -> dict:
    total = have = 0
    try:
        for root_dir, _dirs, files in os.walk(folder):
            for name in files:
                if name.lower().endswith(AUDIO_EXTS):
                    total += 1
                    if os.path.exists(lrc_path_for(os.path.join(root_dir, name))):
                        have += 1
    except Exception:
        pass
    return {"total": total, "have": have}


def completeness_state(have: int, total: int) -> str:
    if total <= 0 or have == 0:
        return "none"
    if have >= total:
        return "all"
    return "some"


def cached_completeness(path: str, kind: str, *, scan: bool = True) -> dict | None:
    """Return cached completeness for *path*.

    *kind* is ``"artist"`` or ``"album"``. When *scan* is false and nothing is
    cached, returns ``None`` instead of walking the tree.
    """
    key = (path, quick_mtime(path), kind)
    cached = lyrics_cache.get(key)
    if cached is not None:
        return cached
    if not scan:
        return None
    result = scan_folder_completeness(path)
    lyrics_cache[key] = result
    return result


def artist_completeness_state(artist_path: str, artist_name: str) -> str | None:
    """State for an artist row, or ``None`` if it has never been scanned."""
    cached = next(
        (v for k, v in lyrics_cache.items()
         if isinstance(k, tuple) and k[0] == artist_path and k[2] == "artist"),
        None,
    )
    if cached is None and artist_name in scanned_artists:
        cached = cached_completeness(artist_path, "artist")
    if cached is None:
        return None
    return completeness_state(cached["have"], cached["total"])


def album_completeness_state(artist_path: str, album_name: str, artist_name: str) -> str | None:
    """State for an album row, or ``None`` when its artist has not been scanned."""
    if artist_name not in scanned_artists:
        return None
    result = cached_completeness(os.path.join(artist_path, album_name), "album")
    if result is None:
        return None
    return completeness_state(result["have"], result["total"])


def invalidate_artist_cache(artist_path: str) -> None:
    keys = [k for k in lyrics_cache if isinstance(k, tuple) and k[0].startswith(artist_path)]
    for key in keys:
        lyrics_cache.pop(key, None)


# --------------------------------------------------------------------------
# Query building
# --------------------------------------------------------------------------

def infer_artist_from_path(song_path: str, music_dir: str) -> str:
    try:
        rel = os.path.relpath(song_path, music_dir)
        return rel.split(os.sep, 1)[0]
    except Exception:
        return ""


def normalize_title(title: str) -> str:
    if " " in title:
        first, rest = title.split(" ", 1)
        if first.isdigit():
            title = rest
    title = title.replace("_", " ").replace("'", "'")
    for ch in ["!", "?", ":", ";"]:
        title = title.replace(ch, "")
    return " ".join(title.split())
