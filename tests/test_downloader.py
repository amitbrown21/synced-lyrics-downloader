"""Self-check for the download engine's failure paths. Run: python tests/test_downloader.py

``run_provider`` is stubbed so these never touch the network.
"""

from __future__ import annotations

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lyricsdl import config as app_config  # noqa: E402
from lyricsdl import downloader, library  # noqa: E402

PLAIN = "[ar:A]\n" + "\n".join(f"line {i}" for i in range(8))


class Recorder(downloader.Reporter):
    def __init__(self, upgrade=(False, False)):
        self.lines: list[tuple[str, str]] = []
        self.progress_calls: list[tuple[int, int]] = []
        self._upgrade = upgrade

    def log(self, msg, level="info"):
        self.lines.append((level, msg))

    def progress(self, done, total):
        self.progress_calls.append((done, total))

    def ask_upgrade(self, song_name, should_cancel):
        return self._upgrade

    def text(self) -> str:
        return "\n".join(m for _, m in self.lines)


def main() -> None:
    # Pin the settings this test depends on; never saved to disk.
    for key, value in {
        "upgrade_plain_to_synced": True,
        "auto_upgrade_plain": False,
        "allow_plain_fallback": False,
        "strip_cjk": False,
        "reject_non_ascii": False,
    }.items():
        app_config.config[key] = value

    downloader.run_provider = lambda *a, **k: False  # always "not found"

    with tempfile.TemporaryDirectory() as root:
        artist = os.path.join(root, "Artist", "Album")
        os.makedirs(artist)
        song = os.path.join(artist, "01 Track.mp3")
        open(song, "wb").close()
        lrc = library.lrc_path_for(song)

        # Nothing found: counted as a failure, and it does not raise.
        rec = Recorder()
        summary = downloader.download_targets(
            [song], music_dir=root, reporter=rec, cancel=lambda: False)
        assert summary.total == 1 and summary.failed == 1 and summary.succeeded == 0, summary
        assert "Not found" in rec.text(), rec.text()
        assert rec.progress_calls[-1] == (1, 1), rec.progress_calls
        assert "Artist" in summary.artists, summary.artists

        # Cancelled before any work: no fetch, flagged as cancelled.
        rec = Recorder()
        summary = downloader.download_targets(
            [song], music_dir=root, reporter=rec, cancel=lambda: True)
        assert summary.cancelled and summary.succeeded == 0, summary

        # A plain file the user declined to upgrade must survive untouched.
        with open(lrc, "w", encoding="utf-8") as f:
            f.write(PLAIN)
        rec = Recorder(upgrade=(False, False))
        downloader.download_targets([song], music_dir=root, reporter=rec,
                                    cancel=lambda: False, prompt_upgrades=True)
        with open(lrc, encoding="utf-8") as f:
            assert f.read() == PLAIN, "declined upgrade discarded the plain .lrc"
        assert "Skipped upgrade" in rec.text(), rec.text()

        # An accepted upgrade that finds nothing must also leave the file intact.
        rec = Recorder(upgrade=(True, False))
        downloader.download_targets([song], music_dir=root, reporter=rec,
                                    cancel=lambda: False, prompt_upgrades=True)
        assert os.path.exists(lrc), "failed upgrade deleted the plain .lrc"
        with open(lrc, encoding="utf-8") as f:
            assert f.read() == PLAIN
        assert "No synced version found" in rec.text(), rec.text()
        assert not os.path.exists(lrc + ".temp"), "temp file leaked"

        # Already-synced files are skipped, not re-fetched.
        with open(lrc, "w", encoding="utf-8") as f:
            f.write("\n".join(f"[00:{i:02d}.00] line {i}" for i in range(8)))
        rec = Recorder()
        downloader.download_targets([song], music_dir=root, reporter=rec,
                                    cancel=lambda: False)
        assert "Skip (already has .lrc)" in rec.text(), rec.text()

    print("ok")


if __name__ == "__main__":
    main()
