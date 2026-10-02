#!/usr/bin/env python3
"""Synced Lyrics Downloader — runnable entry point.

Kept as a plain script so the documented command still works:

    python lyrics_downloader_ultimate.py

The application itself now lives in the ``lyricsdl`` package:

    lyricsdl/config.py       settings and constants
    lyricsdl/library.py      folder scanning and lyric-state detection
    lyricsdl/providers.py    provider fetching and quality filters
    lyricsdl/downloader.py   the download engine (thread-safe, UI-free)
    lyricsdl/ui/             the CustomTkinter crate interface

``--selftest`` proves a packaged build actually works without a human: it runs
a real lookup, builds the real window against a miniature library, and reports
JSON. A frozen ``--windowed`` build has no stdout to read, so the result is
written to a file as well.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile


def _gui_check() -> dict:
    """Build the real window off-screen and confirm the packaged GUI works.

    A frozen build can be missing customtkinter's theme assets, which no import
    check would catch — the window has to be constructed for real.
    """
    from lyricsdl import config as app_config

    result: dict = {"ok": False}
    saved = {k: app_config.config.get(k) for k in ("music_dir", "window_geometry")}
    tmp = tempfile.mkdtemp(prefix="sl-gui-")
    try:
        # A miniature library, so this exercises scanning and row rendering.
        for artist in ("Alpha", "Beta"):
            album = os.path.join(tmp, artist, "Album")
            os.makedirs(album)
            open(os.path.join(album, "01 Track.mp3"), "wb").close()

        app_config.config["music_dir"] = tmp
        app_config.config["window_geometry"] = "1000x700+4000+4000"  # off-screen

        import customtkinter as ctk
        from lyricsdl.ui.app import App

        app = App()
        app.root.update()
        result["customtkinter"] = getattr(ctk, "__version__", "?")
        result["artists_listed"] = len(app.artist_pane.list.rows)

        # Albums and tracks only fill in once something is selected, so drive
        # the same cascade a click would.
        if app.artist_pane.list.rows:
            app.artist_pane.list.select_index(0)
            app.root.update()
        result["albums_listed"] = len(app.album_pane.list.rows)
        result["tracks_listed"] = len(app.track_pane.list.rows)

        # And prove the results sheet renders, via the engine's own event.
        if app.track_pane.list.rows:
            app._seed_results([r.data["path"] for r in app.track_pane.list.rows])
            app.on_track(app.track_pane.list.rows[0].data["path"], "synced", "Lrclib")
            app.root.update()
        result["result_rows"] = len(app.result_pane.list.rows)

        result["ok"] = (result["artists_listed"] == 2 and result["albums_listed"] >= 1
                        and result["tracks_listed"] >= 1 and result["result_rows"] >= 1)
        app.root.destroy()
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        for key, value in saved.items():
            app_config.config[key] = value
        shutil.rmtree(tmp, ignore_errors=True)
    return result


def _selftest(out_path: str, query: str, provider: str) -> int:
    """Exercise the packaged engine and GUI, and report what happened."""
    from lyricsdl import config as app_config
    from lyricsdl import library, providers

    report: dict = {
        "frozen": bool(getattr(sys, "frozen", False)),
        "python": sys.version.split()[0],
        "backend": providers.backend(),
        "config_file": app_config.CONFIG_FILE,
        "config_writable": False,
        "lookup": {"query": query, "provider": provider, "found": False, "state": None},
    }

    # Settings must survive a restart: a frozen build that resolved its config
    # into the temporary bundle directory would silently lose them.
    try:
        probe = os.path.join(os.path.dirname(app_config.CONFIG_FILE), ".sl-write-probe")
        with open(probe, "w", encoding="utf-8") as f:
            f.write("ok")
        os.remove(probe)
        report["config_writable"] = True
    except Exception as exc:
        report["config_error"] = str(exc)

    if report["backend"] != "none":
        with tempfile.TemporaryDirectory() as tmp:
            target = os.path.join(tmp, "selftest.lrc")
            try:
                ok = providers.run_provider(query, provider, target,
                                            app_config.config.lang_code(), True)
                report["lookup"]["found"] = bool(ok)
                if ok:
                    report["lookup"]["state"] = library.analyze_lrc(target)
                    report["lookup"]["bytes"] = os.path.getsize(target)
            except Exception as exc:
                report["lookup"]["error"] = f"{type(exc).__name__}: {exc}"

    report["gui"] = _gui_check()

    text = json.dumps(report, indent=2)
    try:
        sys.stdout.write(text + "\n")
        sys.stdout.flush()
    except Exception:
        pass  # no console attached (windowed build) — the file is the output
    try:
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(text + "\n")
    except Exception:
        pass

    ok = (report["backend"] != "none" and report["config_writable"]
          and report["gui"]["ok"])
    return 0 if ok else 1


def _run_selftest_from_argv() -> int:
    args = sys.argv[sys.argv.index("--selftest") + 1:]
    out, query, provider = "selftest-report.json", "Bohemian Rhapsody Queen", "Lrclib"
    for i, arg in enumerate(args):
        if i + 1 >= len(args):
            continue
        if arg == "--out":
            out = args[i + 1]
        elif arg == "--query":
            query = args[i + 1]
        elif arg == "--provider":
            provider = args[i + 1]
    return _selftest(out, query, provider)


def main() -> int:
    if "--selftest" in sys.argv:
        return _run_selftest_from_argv()

    try:
        from lyricsdl.ui import run
    except ImportError as exc:  # missing customtkinter or a broken install
        try:
            sys.stderr.write(
                "Could not start Synced Lyrics Downloader.\n"
                f"  {exc}\n\n"
                "Install the requirements first:\n"
                "  pip install -r requirements.txt\n"
            )
        except Exception:
            pass  # no console attached
        return 1
    run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
