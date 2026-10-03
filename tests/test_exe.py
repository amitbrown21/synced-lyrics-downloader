"""Verify a built executable. Run: python tests/test_exe.py

Checks the packaged app the way a user would meet it: launch it and make it
exercise its own engine and window, then assert on the JSON it reports.

A frozen ``--windowed`` build has no stdout, so ``--selftest`` writes a report
file; that report is the assertion surface here. Skips (successfully) when no
executable has been built, so this can sit in the normal suite.

Build first with:  python build_exe.py
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXE = os.path.join(ROOT, "dist", "SyncedLyricsDownloader.exe")
PROCESS = "SyncedLyricsDownloader.exe"


def _kill() -> None:
    """A onefile build runs as a launcher plus a child; kill both by name."""
    subprocess.run(["taskkill", "/F", "/IM", PROCESS],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _run(backend: str | None, timeout: int = 240) -> tuple[int, dict]:
    out = os.path.join(tempfile.mkdtemp(prefix="sl-exe-"), "report.json")
    env = dict(os.environ)
    if backend:
        env["LYRICSDL_BACKEND"] = backend
    else:
        env.pop("LYRICSDL_BACKEND", None)

    proc = subprocess.Popen([EXE, "--selftest", "--out", out],
                            env=env, cwd=os.path.join(ROOT, "dist"))
    try:
        code = proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        _kill()
        raise AssertionError(f"exe did not finish within {timeout}s")
    finally:
        _kill()

    if not os.path.exists(out):
        raise AssertionError(f"exe produced no report (exit {code})")
    with open(out, encoding="utf-8") as f:
        return code, json.load(f)


def main() -> None:
    if not os.path.exists(EXE):
        print("skip — no executable built (run python build_exe.py)")
        return

    size_mb = os.path.getsize(EXE) / 1_048_576
    print(f"exe: {EXE} ({size_mb:.1f} MB)")
    assert size_mb > 5, f"suspiciously small executable: {size_mb:.1f} MB"

    for backend in ("inproc", None):
        label = backend or "auto"
        code, report = _run(backend)
        print(f"  [{label}] exit={code} {json.dumps(report, sort_keys=True)}")

        assert report["frozen"] is True, "report did not come from the frozen build"
        assert code == 0, f"[{label}] selftest reported failure"

        # The engine must be usable with nothing installed, which is what the
        # bundled backend is for.
        if backend == "inproc":
            assert report["backend"] == "inproc", report["backend"]
        assert report["backend"] != "none", "no provider engine resolved"

        # Settings must survive a restart beside the executable.
        assert report["config_writable"] is True, report.get("config_error")
        assert os.path.dirname(report["config_file"]) == os.path.join(ROOT, "dist"), (
            f"config would not persist beside the exe: {report['config_file']}")

        # The window must build and fill, which a missing customtkinter asset
        # would break while every import still succeeded.
        gui = report["gui"]
        assert gui["ok"] is True, gui.get("error", gui)
        assert gui["artists_listed"] == 2, gui
        assert gui["albums_listed"] >= 1, gui
        assert gui["tracks_listed"] >= 1, gui
        assert gui["result_rows"] >= 1, gui

        # The window icon comes from art bundled with --add-data. build_exe.py
        # would still produce a working exe without it, so assert it explicitly.
        assert gui.get("window_icon") is True, (
            "the window icon did not load inside the frozen build — the bundled "
            "mark PNG is missing from the bundle")

        # The lookup itself needs the network, so it is reported but not
        # asserted: a release must still verify offline.
        if report["lookup"]["found"]:
            assert report["lookup"]["state"] == "synced", report["lookup"]
            print(f"  [{label}] live lookup: synced, {report['lookup']['bytes']} bytes")
        else:
            print(f"  [{label}] live lookup unavailable (network?) — not asserted")

    print("ok")


if __name__ == "__main__":
    main()
