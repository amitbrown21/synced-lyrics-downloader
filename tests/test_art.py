"""The art is generated, so its defects are preventable — so they are tested.

Covers the three real bugs found while building the asset set:
  * a transparent asset with ink running off its canvas (the wordmark clipped
    its sub-line by 140px);
  * an opaque asset left with semi-transparent fringe pixels, because pasting a
    masked glyph onto RGBA writes the glyph's partial alpha into the result;
  * a mark that stops being legible once it is actually 16px.
Also asserts the design system's contrast floor, which the art must not break.
"""

from __future__ import annotations

import io
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import make_art as A  # noqa: E402
from PIL import Image  # noqa: E402


def bleeding(img: Image.Image, band: int = 2) -> str:
    """The edge that content touches, or '' when the canvas has margin."""
    if img.mode != "RGBA":
        return ""
    alpha_img = img.split()[3]
    if alpha_img.getextrema()[0] == 255:
        return ""          # wholly opaque: nothing can be clipped against it
    alpha = alpha_img.load()
    w, h = img.size
    for name, coords in (
        ("right", ((x, y) for x in range(w - band, w) for y in range(h))),
        ("left", ((x, y) for x in range(band) for y in range(h))),
        ("bottom", ((x, y) for y in range(h - band, h) for x in range(w))),
        ("top", ((x, y) for y in range(band) for x in range(w))),
    ):
        if any(alpha[x, y] > 8 for x, y in coords):
            return name
    return ""


def main() -> None:
    A.assert_contrast()

    # -- a transparent asset must keep a margin ---------------------------
    for name, img in (("mark", A.mark(512)), ("mark mono", A.mark_mono(512)),
                      ("wordmark", A.wordmark(46, on_dark=False))):
        edge = bleeding(img)
        assert not edge, f"{name}: ink runs off the {edge} edge {img.size}"

    # The wordmark's sub-line is the thing that overflowed; measure it.
    img = A.wordmark(46, on_dark=False)
    d = A.ImageDraw.Draw(img)
    sub = A.mono_font(max(9, int(46 * 0.42)))
    line = "SYNCED FIRST  ·  PLAIN AS FALLBACK  ·  NO ACCOUNT  ·  LOCAL-FIRST"
    assert d.textlength(line, font=sub) + 4 < img.size[0], (
        "the wordmark sub-line is wider than the canvas it is drawn on")

    # -- an opaque asset must be fully opaque -----------------------------
    for name, img in (("hero", A.hero()), ("social", A.social()),
                      ("wordmark on dark", A.wordmark(46)),
                      ("mark on dark", A.mark(512, ground=A.rgb(A.T.CRATE)))):
        low, _ = img.convert("RGBA").split()[3].getextrema()
        assert low == 255, (
            f"{name} has semi-transparent pixels (min alpha {low}) — a masked "
            "paste left edge fringe on an opaque ground")

    # -- the 16px mark must keep all three parts: rim, disc, label --------
    small = A.mark(16).convert("RGB")
    w, h = small.size
    px = small.load()

    def reddish(c):
        return c[0] > 150 and c[1] < 110 and c[2] < 100

    def lightish(c):
        return sum(c[:3]) > 450

    red = light = 0
    rim_at_edge = label_at_centre = False
    for y in range(h):
        for x in range(w):
            c = px[x, y]
            radius = max(abs(x - w / 2 + 0.5), abs(y - h / 2 + 0.5))
            if reddish(c):
                red += 1
                rim_at_edge |= radius > w * 0.30
                label_at_centre |= radius < w * 0.18
            if lightish(c):
                light += 1
    assert light >= 35, f"16px kraft disc is barely there ({light}px)"
    assert red >= 70, f"16px rim and label have only {red}px between them"

    # Rim and label are both red, so counting red proves nothing on its own:
    # the rim has to reach the edge and the label has to reach the middle. A
    # disc that lost its rim vanishes on a light taskbar, which is the whole
    # reason the rim exists.
    assert rim_at_edge, "16px rim is gone — the mark loses its silhouette on light"
    assert label_at_centre, "16px label is gone — the disc reads as a blank ring"

    # The rim is load-bearing, and this is the measurement that says so: the
    # kraft disc alone all but vanishes on a light taskbar, so if someone ever
    # darkens kraft or lightens red past these numbers, the mark loses the
    # ground it was drawn for and this test says why.
    bare_disc = A.contrast(A.STOCK, A.LIGHT_TASKBAR)
    rim = A.contrast(A.RED, A.LIGHT_TASKBAR)
    assert bare_disc < 1.5, (
        f"kraft alone now measures {bare_disc:.2f}:1 on a light taskbar — the "
        "rim's rationale no longer holds, so re-check the mark's structure")
    assert rim >= 3.0, (
        f"the rim measures {rim:.2f}:1 on a light taskbar and must hold the "
        "silhouette there")

    # -- the .ico must be a valid directory of the sizes Windows asks for --
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        ico = Path(tmp) / "icon.ico"
        A.write_ico(ico)
        raw = ico.read_bytes()
        reserved, kind, count = struct.unpack("<HHH", raw[:6])
        assert (reserved, kind) == (0, 1), "not an icon directory"
        assert count == len(A.ICON_SIZES), f"{count} entries, expected {len(A.ICON_SIZES)}"
        found = set()
        off = 6
        for _ in range(count):
            w, h, _, _, planes, bpp, size, offset = struct.unpack(
                "<BBBBHHII", raw[off:off + 16])
            decoded = Image.open(io.BytesIO(raw[offset:offset + size]))
            assert planes == 1 and bpp == 32, "icon entry is not 32-bit RGBA"
            assert decoded.size == (w or 256, h or 256), "entry size mismatch"
            found.add(w or 256)
            off += 16
        assert found == set(A.ICON_SIZES), f"missing sizes: {set(A.ICON_SIZES) - found}"
        # Windows needs 16 and 256 present; both are in the set above.

    # -- every shipped raster carries its provenance ----------------------
    import json
    for name in ("icon-512.png", "readme-hero.png", "wordmark-on-dark.png"):
        with Image.open(ROOT / "docs" / "art" / name) as im:
            raw = im.info.get("Description")
        assert raw, f"{name} carries no provenance"
        assert json.loads(raw)["generator"] == "tools/make_art.py"

    print("ok")


if __name__ == "__main__":
    main()
