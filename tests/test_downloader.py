"""Self-check for the download engine's failure paths. Run: python tests/test_downloader.py

``run_provider`` is stubbed so these never touch the network.
"""

from __future__ import annotations

import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lyricsdl import config as app_config  # noqa: E402
from lyricsdl import downloader, library  # noqa: E402

PLAIN = "[ar:A]\n" + "\n".join(f"line {i}" for i in range(8))
SYNCED = "\n".join(f"[00:{i:02d}.00] line {i} with enough words to clear the size floor"
                   for i in range(8))


class Recorder(downloader.Reporter):
    def __init__(self, upgrade=(False, False)):
        self.lines: list[tuple[str, str]] = []
        self.progress_calls: list[tuple[int, int]] = []
        self.tracks: list[tuple[str, str]] = []
        self._upgrade = upgrade

    def log(self, msg, level="info"):
        self.lines.append((level, msg))

    def progress(self, done, total):
        self.progress_calls.append((done, total))

    def track(self, path, state, detail=""):
        self.tracks.append((state, os.path.basename(path)))

    def ask_upgrade(self, song_name, should_cancel):
        return self._upgrade

    def text(self) -> str:
        return "\n".join(m for _, m in self.lines)

    def states(self) -> dict[str, str]:
        """Last recorded state per file name."""
        out = {}
        for state, name in self.tracks:
            out[name] = state
        return out


def main() -> None:
    # Pin the settings this test depends on; never saved to disk.
    for key, value in {
        "upgrade_plain_to_synced": True,
        "auto_upgrade_plain": False,
        "allow_plain_fallback": False,
        "strip_cjk": False,
        "reject_non_ascii": False,
        "providers_order": list(app_config.ALL_PROVIDERS),
        "providers_enabled": {p: True for p in app_config.ALL_PROVIDERS},
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
        assert rec.states() == {"01 Track.mp3": "failed"}, rec.tracks

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
        # "kept" is neither a write nor a failure, so it counts as neither.
        assert rec.states() == {"01 Track.mp3": "kept"}, rec.tracks

        # An accepted upgrade that finds nothing must also leave the file intact.
        rec = Recorder(upgrade=(True, False))
        summary = downloader.download_targets([song], music_dir=root, reporter=rec,
                                              cancel=lambda: False, prompt_upgrades=True)
        assert os.path.exists(lrc), "failed upgrade deleted the plain .lrc"
        with open(lrc, encoding="utf-8") as f:
            assert f.read() == PLAIN
        assert "No synced version found" in rec.text(), rec.text()
        assert not os.path.exists(lrc + ".temp"), "temp file leaked"
        assert rec.states() == {"01 Track.mp3": "kept"}, rec.tracks
        assert (summary.succeeded, summary.failed) == (0, 0), summary

        # Regression: with the upgrade feature switched off entirely, the old
        # code fell through to a plain fetch — which deletes its target before
        # searching, destroying lyrics the user already had when nothing was
        # found. It must upgrade atomically instead.
        app_config.config["upgrade_plain_to_synced"] = False
        rec = Recorder()
        downloader.download_targets([song], music_dir=root, reporter=rec,
                                    cancel=lambda: False)
        assert os.path.exists(lrc), "disabled upgrade destroyed the plain .lrc"
        with open(lrc, encoding="utf-8") as f:
            assert f.read() == PLAIN
        app_config.config["upgrade_plain_to_synced"] = True

        # Already-synced files are skipped, not re-fetched.
        with open(lrc, "w", encoding="utf-8") as f:
            f.write(SYNCED)
        rec = Recorder()
        downloader.download_targets([song], music_dir=root, reporter=rec,
                                    cancel=lambda: False)
        assert "Skip (already has .lrc)" in rec.text(), rec.text()
        assert rec.states() == {"01 Track.mp3": "skipped"}, rec.tracks

        # -- parallel lookups -------------------------------------------------
        # Each stubbed lookup blocks; the pool must overlap them.
        for i in range(2, 6):
            open(os.path.join(artist, f"{i:02d} Track.mp3"), "wb").close()
        four = [os.path.join(artist, f"{i:02d} Track.mp3") for i in range(2, 6)]

        def slow_provider(query, provider, out_path, lang_code, want_synced):
            time.sleep(0.25)
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(SYNCED)
            return True

        downloader.run_provider = slow_provider

        app_config.config["concurrency"] = 1
        rec = Recorder()
        started = time.monotonic()
        sequential = downloader.download_targets(
            four, music_dir=root, reporter=rec, cancel=lambda: False)
        serial_time = time.monotonic() - started
        assert sequential.succeeded == 4, sequential
        assert all(rec.states()[f"{i:02d} Track.mp3"] == "synced" for i in range(2, 6)), rec.tracks

        for i in range(2, 6):
            os.remove(library.lrc_path_for(os.path.join(artist, f"{i:02d} Track.mp3")))

        app_config.config["concurrency"] = 4
        rec = Recorder()
        started = time.monotonic()
        parallel = downloader.download_targets(
            four, music_dir=root, reporter=rec, cancel=lambda: False)
        pool_time = time.monotonic() - started
        assert parallel.succeeded == 4, parallel
        assert pool_time < serial_time * 0.6, (
            f"pool did not overlap lookups: {pool_time:.2f}s vs serial {serial_time:.2f}s")
        assert "4 at a time" in rec.text(), rec.text

        # Every track reports "working" before it settles.
        assert ("working", "02 Track.mp3") in rec.tracks, rec.tracks

        # Upgraded files are reported as upgraded, not merely synced.
        app_config.config["auto_upgrade_plain"] = True
        with open(library.lrc_path_for(four[0]), "w", encoding="utf-8") as f:
            f.write(PLAIN)
        rec = Recorder()
        downloader.download_targets(four, music_dir=root, reporter=rec,
                                    cancel=lambda: False)
        assert rec.states()["02 Track.mp3"] == "upgraded", rec.tracks
        app_config.config["auto_upgrade_plain"] = False

        # -- provider health --------------------------------------------------
        # A provider that has gone dark (an API change, a block, a dead domain)
        # must not be asked about every track: run_provider reports "broken" and
        # "no such song" identically, so a canonical probe decides it once per
        # job. Otherwise every track either wastes a timeout or fails outright.
        app_config.config["providers_order"] = ["Lrclib", "Megalobiz"]
        app_config.config["providers_enabled"] = {"Lrclib": True, "Megalobiz": True}
        asked: list[tuple[str, str]] = []

        def health_aware(query, provider, out_path, lang_code, want_synced):
            asked.append((provider, query))
            if provider == "Megalobiz":
                return False        # dark: will not answer, not even the probe
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(SYNCED)
            return True

        downloader.run_provider = health_aware
        two = []
        for name in ("07 Track.mp3", "08 Track.mp3"):
            path = os.path.join(artist, name)
            open(path, "wb").close()
            two.append(path)

        rec = Recorder()
        summary = downloader.download_targets(two, music_dir=root, reporter=rec,
                                             cancel=lambda: False)
        assert summary.succeeded == 2, summary
        assert "Providers not answering: Megalobiz" in rec.text(), rec.text()
        assert "Using: Lrclib" in rec.text(), rec.text()

        track_asks = [(p, q) for p, q in asked if q != downloader.HEALTH_QUERY]
        assert all(p != "Megalobiz" for p, _ in track_asks), (
            f"a dark provider was still asked about tracks: {asked}")
        assert any(p == "Lrclib" for p, _ in track_asks), asked

        # If nothing answers the probe at all, that is a network problem rather
        # than every provider being dead, so the configured list is kept. A blip
        # must not turn one bad moment into a whole job of failures.
        asked.clear()
        dark = []
        for name in ("09 Track.mp3", "10 Track.mp3"):
            path = os.path.join(artist, name)
            open(path, "wb").close()
            dark.append(path)

        def all_dark(query, provider, out_path, lang_code, want_synced):
            asked.append((provider, query))
            return False

        downloader.run_provider = all_dark
        rec = Recorder()
        summary = downloader.download_targets(dark, music_dir=root, reporter=rec,
                                              cancel=lambda: False)
        assert summary.failed == 2, summary
        assert "asking them all anyway" in rec.text(), rec.text()
        # Both providers must still have been offered the tracks.
        track_providers = {p for p, q in asked if q != downloader.HEALTH_QUERY}
        assert track_providers == {"Lrclib", "Megalobiz"}, (
            f"an all-dark probe must not permanently drop providers: {track_providers}")

    print("ok")


if __name__ == "__main__":
    main()
