"""Capture screenshots of the built app for design review.

Dev-only. Uses the synthetic fixture library; the real config file is never
written because every dialog is torn down with ``destroy()`` (which skips the
dialogs' save paths) and ``on_saved`` is a no-op.
"""

from __future__ import annotations

import os
import pathlib
import shutil
import sys
import tempfile
import threading
import time

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import customtkinter as ctk  # noqa: E402
from PIL import ImageGrab  # noqa: E402

from lyricsdl import config as app_config  # noqa: E402
from lyricsdl import downloader  # noqa: E402
from lyricsdl.ui import dialogs  # noqa: E402
from lyricsdl.ui.app import App  # noqa: E402

FIXTURE = ROOT / ".impeccable" / "fixtures" / "demo-library"
OUT = ROOT / ".impeccable" / "review"

SYNCED_LRC = "\n".join(
    f"[00:{i:02d}.00] line {i} with enough words to clear the size floor"
    for i in range(8))
PLAIN_LRC = "[ar:Demo Artist]\n" + "\n".join(f"line {i}" for i in range(8))


def settle(app, seconds: float = 1.0) -> None:
    end = time.time() + seconds
    while time.time() < end:
        app.root.update()
        time.sleep(0.02)


def shoot(win, name: str) -> None:
    # Raise just this window for the grab; a -topmost root would hide dialogs.
    win.lift()
    try:
        win.attributes("-topmost", True)
    except Exception:
        pass
    for _ in range(25):
        win.update()
        time.sleep(0.02)
    x, y = win.winfo_rootx(), win.winfo_rooty()
    w, h = win.winfo_width(), win.winfo_height()
    img = ImageGrab.grab(bbox=(x, y, x + w, y + h))
    try:
        win.attributes("-topmost", False)
    except Exception:
        pass
    OUT.mkdir(parents=True, exist_ok=True)
    img.save(OUT / name)
    print(f"saved {name} {img.size} at ({x},{y})")


def tops(app) -> list:
    return [w for w in app.root.winfo_children()
            if isinstance(w, ctk.CTkToplevel) and w.winfo_ismapped()]


def select(app, pane, label: str) -> None:
    for i, row in enumerate(pane.list.rows):
        if row.label == label:
            pane.list.select_index(i)
            settle(app, 0.45)
            return
    print(f"!! no row named {label!r}")


def shoot_dialog(app, name: str, delay: float = 0.9) -> None:
    """Tear down whatever modal is open once it has painted."""
    def go():
        found = tops(app)
        if not found:
            print(f"!! no dialog for {name}")
        else:
            shoot(found[-1], name)
            for w in found:
                w.destroy()
    app.root.after(int(delay * 1000), go)


def shoot_first_run() -> None:
    """The empty state a user sees before opening a folder."""
    saved = app_config.config.get("music_dir", "")
    app_config.config["music_dir"] = ""
    app = App()
    app.root.geometry("1180x800+30+30")
    app.root.deiconify()
    app.root.attributes("-topmost", True)
    settle(app, 1.2)
    shoot(app.root, "first-run.png")
    app.root.destroy()
    app_config.config["music_dir"] = saved


def shoot_results() -> None:
    """Capture the results sheet, driven by the real engine and an offline stub.

    Runs against a throwaway copy of the fixture so the shipped one stays
    pristine, and stubs the provider call so no capture ever hits the network.
    """
    lib = tempfile.mkdtemp(prefix="sl-results-")
    shutil.copytree(FIXTURE, os.path.join(lib, "demo-library"))
    music = os.path.join(lib, "demo-library")

    saved = {k: app_config.config.get(k) for k in
             ("music_dir", "allow_plain_fallback", "auto_upgrade_plain")}
    real_run = downloader.run_provider

    # Offline stand-in: slow enough to keep rows visibly in flight, and shaped
    # so every outcome the sheet can render actually appears.
    def fake_provider(query, provider, out_path, lang_code, want_synced):
        slow = any(n in out_path for n in ("Night Ferry", "Ballast"))
        if slow:
            time.sleep(1.1)
        if "Ballast" in out_path:
            return False                       # nothing at all -> failed
        if not want_synced:
            open(out_path, "w", encoding="utf-8").write(PLAIN_LRC)
            return True
        if "Night Ferry" in out_path:
            return False                       # synced absent -> plain fallback
        open(out_path, "w", encoding="utf-8").write(SYNCED_LRC)
        return True

    downloader.run_provider = fake_provider
    app_config.config["music_dir"] = music
    app_config.config["allow_plain_fallback"] = True
    app_config.config["auto_upgrade_plain"] = True   # upgrades the fixture's plain .lrc

    try:
        app = App()
        app.root.geometry("1180x880+30+20")
        app.root.deiconify()
        app.root.attributes("-topmost", True)
        settle(app, 1.0)
        app.load_library()
        settle(app, 0.4)
        select(app, app.artist_pane, "Vela Sound System")
        # Artist selection auto-picks the first album; take both for a fuller sheet.
        app.album_pane.list.select_keys([r.key for r in app.album_pane.list.rows])
        app.album_pane.list._changed()
        settle(app, 0.4)
        targets = app._collect_targets()
        print(f"results capture: {len(targets)} targets")

        worker = threading.Thread(
            target=lambda: app._job_download(targets, prompt_upgrades=False,
                                             headline="Processing"),
            daemon=True)
        worker.start()
        settle(app, 0.9)
        shoot(app.root, "results-live.png")      # rows still in flight
        worker.join(30)
        settle(app, 0.6)
        shoot(app.root, "results.png")           # settled
        app.root.destroy()
    finally:
        downloader.run_provider = real_run
        for key, value in saved.items():
            app_config.config[key] = value
        shutil.rmtree(lib, ignore_errors=True)


def main() -> None:
    shoot_first_run()
    shoot_results()

    app_config.config["music_dir"] = str(FIXTURE)
    app = App()
    app.root.geometry("1180x800+30+30")
    app.root.deiconify()
    app.root.attributes("-topmost", True)
    settle(app, 1.0)
    app.load_library()
    settle(app, 0.6)

    # Scan first: artist completeness only surfaces once an artist is scanned.
    select(app, app.artist_pane, "The Marginal Notes")
    app.scan_missing()
    settle(app, 1.5)
    print("after scan: artists", len(app.artist_pane.list.rows),
          "albums", len(app.album_pane.list.rows),
          "tracks", len(app.track_pane.list.rows),
          "missing", len(app.missing_targets))

    select(app, app.artist_pane, "The Marginal Notes")
    select(app, app.album_pane, "Annotated")
    select(app, app.track_pane, "Marginalia")
    settle(app, 0.6)
    shoot(app.root, "desktop.png")

    # Dialogs are transient: root must release -topmost or they paint behind it.
    app.root.attributes("-topmost", False)
    settle(app, 0.3)

    shoot_dialog(app, "dialog-options.png")
    dialogs.open_options(app.root, on_saved=lambda: None)

    dialogs.open_custom_search(
        app.root, artist="The Marginal Notes", album="Annotated",
        title="Marginalia", on_submit=lambda q: None)
    settle(app, 0.8)
    for w in tops(app):
        shoot(w, "dialog-custom-search.png")
        w.destroy()

    shoot_dialog(app, "dialog-about.png")
    dialogs.open_about(app.root)
    settle(app, 1.4)  # let the scheduled capture run; open_about does not block

    app.root.destroy()


if __name__ == "__main__":
    main()
