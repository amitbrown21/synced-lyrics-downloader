"""Self-check for the lyric-file classifiers. Run: python tests/test_library.py

No framework: these are the assertions that fail if the parsing breaks.
"""

from __future__ import annotations

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lyricsdl import library  # noqa: E402


def write(path: str, text: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def main() -> None:
    with tempfile.TemporaryDirectory() as root:
        album = os.path.join(root, "Artist", "Album")
        os.makedirs(album)
        song = os.path.join(album, "01 Track.mp3")
        open(song, "wb").close()
        lrc = library.lrc_path_for(song)

        # No lyric file at all.
        assert library.track_state(song) == "none"
        assert library.find_missing([album]) == [song]

        # Metadata headers sit above the timestamps; they must not hide them.
        write(lrc, "[ar:A]\n[ti:T]\n[al:L]\n"
                   + "\n".join(f"[00:{i:02d}.00] line {i}" for i in range(8)))
        assert library.track_state(song) == "synced", library.track_state(song)
        assert library.last_timestamp(lrc) == "00:07", library.last_timestamp(lrc)
        assert library.find_missing([album]) == []

        # Timestamped but too short to trust.
        write(lrc, "[ar:A]\n[00:01.00] one\n[00:02.00] two\n")
        assert library.track_state(song) == "incomplete", library.track_state(song)

        # Enough lines, no timing.
        write(lrc, "\n".join(f"line {i}" for i in range(8)))
        assert library.track_state(song) == "plain", library.track_state(song)
        assert library.last_timestamp(lrc) == ""

        # Folder completeness.
        assert library.completeness_state(0, 0) == "none"
        assert library.completeness_state(0, 3) == "none"
        assert library.completeness_state(3, 3) == "all"
        assert library.completeness_state(1, 3) == "some"
        assert library.scan_folder_completeness(album) == {"total": 1, "have": 1}

        # Track labels.
        assert library.normalize_title("03 Grey Garden") == "Grey Garden"
        assert library.normalize_title("Grey Garden") == "Grey Garden"

    print("ok")


if __name__ == "__main__":
    main()
