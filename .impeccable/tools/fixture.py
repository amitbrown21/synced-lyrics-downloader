"""Generate a synthetic demo library for design review only.

All artist, album and track names are invented. The audio files are tiny dummy
payloads; only the folder shape and the .lrc states matter. Never ship this.
"""

from __future__ import annotations

import os
import pathlib
import random

ROOT = pathlib.Path(__file__).resolve().parent.parent / "fixtures" / "demo-library"

LIBRARY = {
    "Vela Sound System": {
        "Harbour Lights": [
            ("Breakwater", "synced"),
            ("Tidal Drift", "synced"),
            ("Long Pier", "plain"),
            ("Night Ferry", "none"),
        ],
        "Slow Freight": [
            ("Coupling", "synced"),
            ("Siding 9", "incomplete"),
            ("Ballast", "none"),
        ],
    },
    "The Marginal Notes": {
        "Annotated": [
            ("Footnote", "synced"),
            ("Marginalia", "synced"),
            ("Erratum", "plain"),
            ("Colophon", "synced"),
            ("Appendix", "none"),
        ],
        "Second Printing": [
            ("Reprint", "synced"),
            ("Corrigenda", "none"),
        ],
    },
    "Halden & the Low Tide": {
        "Estuary": [
            ("Mudflat", "synced"),
            ("Saltmarsh", "plain"),
            ("Channel Marker", "incomplete"),
        ],
    },
    "夜間航行": {
        "Night Passage": [
            ("First Watch", "synced"),
            ("Second Watch", "none"),
        ],
    },
    "Reel to Reel Club": {
        "Quarter Inch": [
            ("Threading", "synced"),
            ("Bias", "synced"),
            ("Wow and Flutter", "plain"),
        ],
    },
    "Paper Kites": {
        "Unreleased": [
            ("Sketch One", "none"),
            ("Sketch Two", "none"),
        ],
    },
}

_LYRICS = [
    "the harbour light is swinging slow",
    "and every rope is holding on",
    "we counted buoys along the way",
    "a colder morning coming on",
    "the radio is mostly static now",
    "so sing it once and let it go",
    "the water keeps the only map",
    "and we are somewhere further out",
]


def make_lrc(state: str, seed: int) -> str | None:
    rnd = random.Random(seed)
    if state == "none":
        return None
    header = "[ar:Demo Artist]\n[ti:Demo Track]\n[al:Demo Album]\n"
    if state == "incomplete":
        return header + "[00:12.00]short one\n[00:20.00]and another\n"
    if state == "plain":
        lines = rnd.sample(_LYRICS, 6)
        return header + "\n".join(lines) + "\n"
    lines = []
    t = 8.0
    for text in _LYRICS:
        lines.append(f"[{int(t // 60):02d}:{t % 60:05.2f}]{text}")
        t += rnd.uniform(9, 15)
    return header + "\n".join(lines) + "\n"


def main() -> None:
    if ROOT.exists():
        import shutil
        shutil.rmtree(ROOT)
    seed = 0
    for artist, albums in LIBRARY.items():
        for album, tracks in albums.items():
            album_dir = ROOT / artist / album
            album_dir.mkdir(parents=True, exist_ok=True)
            for i, (title, state) in enumerate(tracks, 1):
                seed += 1
                stem = f"{i:02d} {title}"
                (album_dir / f"{stem}.mp3").write_bytes(b"ID3" + bytes(64))
                content = make_lrc(state, seed)
                if content is not None:
                    (album_dir / f"{stem}.lrc").write_text(content, encoding="utf-8")
    print(ROOT)


if __name__ == "__main__":
    main()
