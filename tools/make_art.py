#!/usr/bin/env python3
"""Generate the project's art from the shipped design tokens.

    python tools/make_art.py            # everything
    python tools/make_art.py --icon     # just build/icon.ico

The mark is **The Record**: a kraft disc with a silkscreen-red label. The disc
is ringed in the same red, because kraft alone disappears on a light taskbar
while the rim holds the silhouette on both. Detail is thinned as the size
drops — the groove and the spindle hole are the first to go, and at 16px the
mark is just rim, disc and label — so the small version is the same idea drawn
with fewer marks rather than a shrunken picture.

It was previously **The Divider**, a kraft board with a tab. At 16px its
recess, rules and stamp all collapsed, leaving a beige ticket that read as a
document rather than a music app, so the board gave way to the record.

Every raster is generated from ``lyricsdl/ui/theme.py`` and carries its
provenance as PNG text chunks, so no image can drift from the palette and none
is a mystery blob. Contrast is asserted before writing, not eyeballed after.
"""

from __future__ import annotations

import argparse
import datetime
import json
import pathlib
import struct
import sys

from PIL import Image, ImageDraw, ImageFont

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lyricsdl.ui import theme as T  # noqa: E402
from lyricsdl import __version__  # noqa: E402

BUILD = ROOT / "build"
ART = ROOT / "docs" / "art"
FONTS = pathlib.Path(r"C:\Windows\Fonts")
SS = 8  # supersample factor; draw large then reduce, as the crate already does

ICON_SIZES = (16, 20, 24, 32, 40, 48, 64, 128, 256)


def rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


CRATE, RECESS, PANEL, PANEL_HI, EDGE = (rgb(T.CRATE), rgb(T.CRATE_DEEP),
                                        rgb(T.PANEL), rgb(T.PANEL_HI),
                                        rgb(T.PANEL_EDGE))
STOCK, STOCK_DIM, STOCK_EDGE = rgb(T.STOCK), rgb(T.STOCK_DIM), rgb(T.STOCK_EDGE)
INK, INK_SOFT, INK_FAINT = rgb(T.INK), rgb(T.INK_SOFT), rgb(T.INK_FAINT)
RED, RED_DEEP, RED_SOFT = rgb(T.RED), rgb(T.RED_DEEP), rgb(T.RED_SOFT)
GREEN, AMBER, VOID = rgb(T.GREEN), rgb(T.AMBER), rgb(T.VOID)
GREEN_INK, AMBER_INK, VOID_INK = rgb(T.GREEN_INK), rgb(T.AMBER_INK), rgb(T.VOID_INK)
TEXT, TEXT_DIM, TEXT_FAINT = rgb(T.TEXT), rgb(T.TEXT_DIM), rgb(T.TEXT_FAINT)
FOCUS = rgb(T.FOCUS)
CLEAR = (0, 0, 0, 0)

# The mark is the one asset that lands on a ground the palette does not own:
# whatever the user's desktop happens to be. These are the two Windows 11
# taskbar greys, and the rim's whole job is measured against them.
LIGHT_TASKBAR = (243, 243, 243)
DARK_TASKBAR = (32, 32, 32)


# --------------------------------------------------------------------------
# Type — the real display face, resolved against what is installed
# --------------------------------------------------------------------------

_FONT_CACHE: dict = {}


def display_font(size: int) -> ImageFont.FreeTypeFont:
    """Bold SemiCondensed Bahnschrift, falling back down the token chain."""
    key = ("display", size)
    if key not in _FONT_CACHE:
        for name in ("bahnschrift.ttf", "arialn.ttf", "segoeui.ttf"):
            path = FONTS / name
            if not path.exists():
                continue
            font = ImageFont.truetype(str(path), size)
            for variation in ("Bold SemiCondensed", "SemiCondensed",
                             "Bold Condensed", "Condensed"):
                try:
                    font.set_variation_by_name(variation)
                    break
                except Exception:
                    continue
            _FONT_CACHE[key] = font
            break
        else:
            _FONT_CACHE[key] = ImageFont.load_default()
    return _FONT_CACHE[key]


def mono_font(size: int) -> ImageFont.FreeTypeFont:
    key = ("mono", size)
    if key not in _FONT_CACHE:
        for name in ("CascadiaMono.ttf", "consola.ttf", "lucon.ttf"):
            path = FONTS / name
            if path.exists():
                _FONT_CACHE[key] = ImageFont.truetype(str(path), size)
                break
        else:
            _FONT_CACHE[key] = ImageFont.load_default()
    return _FONT_CACHE[key]


def typeset(draw, xy, text, font, fill, tracking=0.0):
    """Draw letter-spaced caps — the Label style's 0.04em tracking.

    PIL has no tracking, so glyphs are placed one at a time and the advance is
    measured from the real font, never estimated.
    """
    x, y = xy
    gap = font.size * tracking
    for i, ch in enumerate(text):
        draw.text((x, y), ch, font=font, fill=fill)
        x += draw.textlength(ch, font=font) + (gap if i < len(text) - 1 else 0)
    return x


def tracked_width(draw, text, font, tracking=0.0):
    gap = font.size * tracking
    return sum(draw.textlength(c, font=font) for c in text) + gap * (len(text) - 1)


# --------------------------------------------------------------------------
# Contrast — proven, not eyeballed
# --------------------------------------------------------------------------

def _luminance(rgbc) -> float:
    def channel(c):
        c /= 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (channel(c) for c in rgbc[:3])
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b) -> float:
    la, lb = _luminance(a), _luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def assert_contrast() -> None:
    """Every pair the art actually paints, against the design system's floor."""
    checks = [
        ("stamp on kraft", GREEN_INK, STOCK, 3.0),
        ("partial on kraft", AMBER_INK, STOCK, 3.0),
        ("missing on kraft", VOID_INK, STOCK, 3.0),
        ("ink on kraft", INK, STOCK, 4.5),
        ("ink soft on kraft", INK_SOFT, STOCK, 4.5),
        ("text on crate", TEXT, CRATE, 4.5),
        ("text dim on crate", TEXT_DIM, CRATE, 4.5),
        ("tab red on crate", RED, CRATE, 3.0),
        ("kraft on crate", STOCK, CRATE, 3.0),
        # The mark ships to desktops the palette does not control, so its rim
        # is checked against both taskbar greys rather than against the crate.
        ("rim on light taskbar", RED, LIGHT_TASKBAR, 3.0),
        ("rim on dark taskbar", RED, DARK_TASKBAR, 3.0),
    ]
    failures = []
    for name, fg, bg, floor in checks:
        got = contrast(fg, bg)
        if got < floor:
            failures.append(f"{name}: {got:.2f}:1 < {floor}:1")
    if failures:
        raise SystemExit("contrast floor not met:\n  " + "\n  ".join(failures))
    print(f"contrast: {len(checks)} pairs clear their floor")


def _minimal_lift(token: str, floor: float, surfaces) -> tuple[str, int] | None:
    """The smallest lightness lift that clears *floor* on every surface."""
    import colorsys

    def lighten(h, t):
        r, g, b = [c / 255 for c in rgb(h)]
        hh, ll, ss = colorsys.rgb_to_hls(r, g, b)
        ll = min(1.0, ll + (1.0 - ll) * t)
        r, g, b = colorsys.hls_to_rgb(hh, ll, ss)
        return "#%02X%02X%02X" % (round(r * 255), round(g * 255), round(b * 255))

    for pct in range(1, 60):
        cand = lighten(token, pct / 100)
        if all(contrast(rgb(cand), s) >= floor for _, s in surfaces):
            return cand, pct
    return None


def report_palette_gaps() -> None:
    """Measure the app's own tokens and say so if the docs overclaim.

    DESIGN.md asks marks to clear 3:1 and both Text Dim and Text Faint to clear
    4.5:1 on the dark board. A mark is checked against every dark surface it
    lands on — checking the crate ground alone is how the previous green passed
    review at 2.88:1 while measuring 2.51:1 on the panel, where the status
    strip and the results sheet actually draw it.
    """
    surfaces = (("crate ground", CRATE), ("crate recess", RECESS),
                ("panel", PANEL), ("panel raised", PANEL_HI))
    text_surfaces = (("crate ground", CRATE), ("crate recess", RECESS),
                     ("panel", PANEL))
    gaps = []

    if min(contrast(GREEN, s) for _, s in surfaces) < 3.0:
        for name, s in surfaces:
            got = contrast(GREEN, s)
            if got < 3.0:
                gaps.append((f"filed green {T.GREEN} on {name} {got:.2f}:1 < 3:1",
                             T.GREEN, 3.0, surfaces))
    for label, token in (("text dim", T.TEXT_DIM), ("text faint", T.TEXT_FAINT)):
        name, s = min(text_surfaces, key=lambda pair: contrast(rgb(token), pair[1]))
        got = contrast(rgb(token), s)
        if got < 4.5:
            gaps.append((f"{label} {token} on {name} {got:.2f}:1 < 4.5:1",
                         token, 4.5, text_surfaces))

    if gaps:
        print("WARNING — DESIGN.md claims a floor these tokens do not meet:")
        for message, token, floor, on in gaps:
            print(f"  {message}")
            lift = _minimal_lift(token, floor, on)
            if lift:
                print(f"    smallest fix: +{lift[1]}% lightness -> {lift[0]}")
        print("  (the art avoids these pairs; the app does not)")


# --------------------------------------------------------------------------
# State marks — the same drawn geometry the lists stamp
# --------------------------------------------------------------------------

def draw_state_mark(d, kind, cx, cy, r, colour, width):
    """One of the five silhouettes, at 13px-equivalent proportions."""
    if kind == "synced":
        d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=colour, width=width)
        d.line([cx - r * 0.46, cy + r * 0.04, cx - r * 0.10, cy + r * 0.40,
                cx + r * 0.50, cy - r * 0.42], fill=colour, width=width,
               joint="curve")
    elif kind == "plain":
        d.rectangle([cx - r, cy - r, cx + r, cy + r], outline=colour, width=width)
        d.line([cx - r * 0.5, cy - r * 0.3, cx + r * 0.5, cy - r * 0.3],
               fill=colour, width=width)
        d.line([cx - r * 0.5, cy + r * 0.28, cx + r * 0.1, cy + r * 0.28],
               fill=colour, width=width)
    elif kind == "incomplete":
        d.polygon([(cx, cy - r), (cx + r, cy + r), (cx - r, cy + r)],
                  outline=colour, width=width)
        d.line([cx, cy - r * 0.1, cx, cy + r * 0.35], fill=colour, width=width)
    elif kind == "none":
        d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=colour, width=width)
        d.line([cx - r * 0.62, cy + r * 0.62, cx + r * 0.62, cy - r * 0.62],
               fill=colour, width=width)
    elif kind == "some":
        d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=colour, width=width)
        d.pieslice([cx - r, cy - r, cx + r, cy + r], -90, 90, fill=colour)
    else:
        raise ValueError(kind)


# --------------------------------------------------------------------------
# The mark: The Record
# --------------------------------------------------------------------------

def mark(size: int, ground=CLEAR, detail: str | None = None) -> Image.Image:
    """Render the mark at *size*, thinning detail as the size drops.

    The rim is not decoration. A kraft disc measures 1.17:1 against a Windows
    light taskbar — invisible — and 12.6:1 against a dark one. Ringing it in
    silkscreen red gives the silhouette 4.35:1 on light and 3.37:1 on dark, so
    the mark holds on whichever ground the user runs.
    """
    if detail is None:
        detail = "tiny" if size <= 20 else "small" if size <= 40 else "full"
    px = size * SS
    img = Image.new("RGBA", (px, px), ground)
    d = ImageDraw.Draw(img)

    cx = cy = px / 2
    R = px * 0.455
    # The rim thickens as the size drops: below ~24px a proportionally scaled
    # rim rounds away to a grey smear instead of a ring.
    rim = px * {"tiny": 0.105, "small": 0.080, "full": 0.058}[detail]
    r_disc = R - rim

    # The rim, then the disc it holds.
    d.ellipse([cx - R, cy - R, cx + R, cy + R], fill=RED)
    d.ellipse([cx - r_disc, cy - r_disc, cx + r_disc, cy + r_disc], fill=STOCK)

    # One groove, once there is room for it to read as a groove.
    if detail == "full":
        gr = px * 0.355
        d.ellipse([cx - gr, cy - gr, cx + gr, cy + gr], outline=STOCK_EDGE,
                  width=max(SS, int(px * 0.010)))

    # The label, and the spindle the record turns on.
    r_label = px * {"tiny": 0.235, "small": 0.215, "full": 0.200}[detail]
    d.ellipse([cx - r_label, cy - r_label, cx + r_label, cy + r_label], fill=RED)
    if detail != "tiny":
        r_hole = px * 0.048
        d.ellipse([cx - r_hole, cy - r_hole, cx + r_hole, cy + r_hole],
                  fill=RECESS)

    return _settle(img, ground, size)


def _settle(img: Image.Image, ground, size: int) -> Image.Image:
    """Resize down, and flatten an opaque-ground asset back to full opacity.

    Pasting a masked glyph onto an RGBA destination writes the glyph's partial
    alpha into the result, so a dark-ground asset ends up with semi-transparent
    pixels along the mark's antialiased edge — which fringes on a light page.
    The colour blend is already correct, so only the alpha needs restoring.

    Bicubic, not Lanczos. Lanczos overshoots at the hard red-to-kraft edge and
    lands pixels *past* both colours — measured at 8 to 80 off-colour pixels
    per render depending on size, which reads as a warm halo round the label.
    Bicubic measures zero on every size and keeps the edge shape.
    """
    if ground != CLEAR:
        img.putalpha(255)
    return img.resize((size, size), Image.BICUBIC)


def mark_mono(size: int, ink=INK, ground=CLEAR) -> Image.Image:
    """A one-ink version for stamping where colour is not available.

    The record with its colours stripped to a single ink: the rim becomes the
    outline, the label becomes a filled disc, and the spindle is punched back
    out of it. ``ImageDraw`` writes raw values in RGBA rather than compositing,
    so filling with a zero alpha is what cuts the hole.
    """
    px = size * SS
    img = Image.new("RGBA", (px, px), ground)
    d = ImageDraw.Draw(img)
    detail = "tiny" if size <= 20 else "small" if size <= 40 else "full"

    cx = cy = px / 2
    r_outer = px * 0.455 - px * 0.030
    d.ellipse([cx - r_outer, cy - r_outer, cx + r_outer, cy + r_outer],
              outline=ink, width=max(SS * 2, int(px * 0.055)))
    r_label = px * 0.200
    d.ellipse([cx - r_label, cy - r_label, cx + r_label, cy + r_label], fill=ink)
    if detail == "full":
        r_hole = px * 0.048
        d.ellipse([cx - r_hole, cy - r_hole, cx + r_hole, cy + r_hole],
                  fill=(0, 0, 0, 0))
    return _settle(img, ground, size)


# --------------------------------------------------------------------------
# Writing rasters, with provenance
# --------------------------------------------------------------------------

def provenance(what: str) -> str:
    return json.dumps({
        "generator": "tools/make_art.py",
        "generated": datetime.datetime.now(datetime.UTC).isoformat(
            timespec="seconds").replace("+00:00", "Z"),
        "app_version": __version__,
        "tokens": "lyricsdl/ui/theme.py",
        "mark": "The Record",
        "asset": what,
        "colours": {
            "ground": T.CRATE, "disc": T.STOCK, "rim": T.RED,
            "label": T.RED, "spindle": T.CRATE_DEEP, "groove": T.STOCK_EDGE,
        },
    }, separators=(",", ":"))


def _rel(path: pathlib.Path) -> str:
    """A readable path for logging, even one outside the repo."""
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def save(img: Image.Image, path: pathlib.Path, what: str,
         check_edges: bool = True) -> None:
    """Write a PNG with its provenance, after proving nothing is clipped."""
    if check_edges:
        clipped = _bleeding(img)
        if clipped:
            raise SystemExit(
                f"{path.name}: ink runs off the {clipped} edge — content does "
                f"not fit its canvas ({img.size[0]}x{img.size[1]})")
    from PIL.PngImagePlugin import PngInfo
    path.parent.mkdir(parents=True, exist_ok=True)
    meta = PngInfo()
    meta.add_text("Software", f"Synced Lyrics Downloader {__version__} art generator")
    meta.add_text("Comment", "The Record Crate — the record, kraft disc in silkscreen red")
    meta.add_text("Description", provenance(what))
    img.save(path, "PNG", pnginfo=meta)
    print(f"  {_rel(path)}  {img.size[0]}x{img.size[1]}")


def _bleeding(img: Image.Image, band: int = 2) -> str:
    """Name the edge that content touches, or '' when the canvas has margin.

    Only transparent assets can be clipped against an edge, so a wholly opaque
    image (a composition with a painted ground) is not checked here.
    """
    if img.mode != "RGBA":
        return ""
    alpha_img = img.split()[3]
    if alpha_img.getextrema()[0] == 255:
        return ""
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


def write_ico(path: pathlib.Path, base: int = 256) -> None:
    """Write a multi-size .ico with a separate, adaptive render per size.

    Pillow's ``sizes=`` downsamples one image for every entry, which would throw
    away the per-size detail. Vista and later accept PNG-compressed entries, so
    each size is rendered on its own terms and embedded directly.
    """
    entries = []
    for size in ICON_SIZES:
        img = mark(size)
        import io
        buf = io.BytesIO()
        img.save(buf, "PNG")
        entries.append((size, buf.getvalue()))

    header = struct.pack("<HHH", 0, 1, len(entries))
    offset = len(header) + 16 * len(entries)
    directory, payload = b"", b""
    for size, data in entries:
        dim = 0 if size >= 256 else size
        directory += struct.pack("<BBBBHHII", dim, dim, 0, 0, 1, 32,
                                 len(data), offset)
        payload += data
        offset += len(data)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(header + directory + payload)
    print(f"  {_rel(path)}  multi-size "
          f"({', '.join(str(s) for s in ICON_SIZES)})")


# --------------------------------------------------------------------------
# Compositions
# --------------------------------------------------------------------------

def legend_board(d, box, *, label_size=13) -> None:
    """The five drawn silhouettes on a printed kraft board.

    DESIGN.md sanctions kraft for "a printed board in the legend", and printing
    the key on stock sidesteps the dark-ground trio entirely — which matters,
    because Filed Green only measures 2.88:1 on the dark ground.
    """
    x0, y0, x1, y1 = box
    d.rectangle([x0, y0, x1, y1], fill=STOCK)
    d.rectangle([x0, y0, x1, y1], outline=STOCK_EDGE, width=1)
    inks = {"synced": GREEN_INK, "plain": VOID_INK, "incomplete": AMBER_INK,
            "none": VOID_INK, "some": AMBER_INK}
    order = [("synced", "SYNCED"), ("plain", "PLAIN"), ("incomplete", "PARTIAL"),
             ("none", "MISSING"), ("some", "SCANNING")]
    font = mono_font(label_size)
    cy = (y0 + y1) / 2
    r = max(6, (y1 - y0) * 0.26)
    x = x0 + (y1 - y0) * 0.42
    for kind, label in order:
        draw_state_mark(d, kind, x, cy, r, inks[kind], max(2, int(r * 0.22)))
        x += r * 2.4
        d.text((x, cy - label_size * 0.60), label, font=font, fill=INK_SOFT)
        x += tracked_width(d, label, font) + (y1 - y0) * 0.34


def wordmark(size_px: int, *, on_dark=True) -> Image.Image:
    """The lockup: mark, name in condensed caps, and the 2px red rule.

    The canvas is measured from the real glyphs rather than assumed, so the
    sub-line can never run off the edge of a shipped asset.
    """
    name = "SYNCED LYRICS DOWNLOADER"
    sub_line = "SYNCED FIRST  ·  PLAIN AS FALLBACK  ·  NO ACCOUNT  ·  LOCAL-FIRST"
    f_name = display_font(size_px)
    sub = mono_font(max(9, int(size_px * 0.42)))
    probe = ImageDraw.Draw(Image.new("RGB", (8, 8)))

    name_w = tracked_width(probe, name, f_name, 0.04)
    sub_w = probe.textlength(sub_line, font=sub)
    rule_h = max(2, size_px // 9)

    mark_sz = int(size_px * 2.1)
    pad = int(size_px * 0.7)
    text_x = mark_sz + int(pad * 0.85)
    text_w = max(name_w, sub_w)
    W = int(pad + text_x + text_w + pad)

    block_h = size_px * 1.28 + size_px * 0.42 + sub.size * 1.45
    H = int(max(mark_sz, block_h) + pad * 2)

    img = Image.new("RGBA", (W, H), rgb(T.CRATE) if on_dark else CLEAR)
    d = ImageDraw.Draw(img)
    glyph = mark(mark_sz)
    img.paste(glyph, (pad, int(H / 2 - mark_sz / 2)), glyph)

    tx = pad + text_x
    ty = int(H / 2 - block_h / 2)
    typeset(d, (tx, ty), name, f_name, TEXT if on_dark else INK, tracking=0.04)
    rule_y = ty + int(size_px * 1.28)
    d.rectangle([tx, rule_y, tx + name_w, rule_y + rule_h], fill=RED)
    d.text((tx, rule_y + size_px * 0.42), sub_line, font=sub,
           fill=TEXT_DIM if on_dark else INK_SOFT)
    if on_dark:
        img.putalpha(255)   # the ground is opaque; do not leave edge fringe
    return img


def crate_motif(d, box, ground_dark=True) -> None:
    """An abstract crate: kraft boards tabbed into a recess, front one forward."""
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    d.rectangle([x0, y0, x1, y1], fill=RECESS)
    for i in range(4):
        inset = 0.06 + i * 0.055
        band_y0 = y0 + h * (0.08 + i * 0.235)
        band_y1 = band_y0 + h * 0.20
        bx = x0 + w * inset
        shade = STOCK if i == 3 else STOCK_DIM
        d.rectangle([bx, band_y0, x1 - w * 0.04, band_y1], fill=shade)
        d.line([x1 - w * 0.04, band_y0, x1 - w * 0.04, band_y1],
               fill=STOCK_EDGE, width=2)
        if i == 3:
            d.rectangle([bx, band_y0 - h * 0.055, bx + w * 0.26, band_y0 + h * 0.03],
                        fill=RED)
            draw_state_mark(d, "synced", bx + (x1 - w * 0.04 - bx) * 0.72,
                            (band_y0 + band_y1) / 2, h * 0.055, GREEN_INK,
                            max(2, int(h * 0.011)))


def hero() -> Image.Image:
    """README hero: the crate, the lockup, the provider line, the key."""
    W, H = 1600, 420
    img = Image.new("RGBA", (W, H), rgb(T.CRATE))
    d = ImageDraw.Draw(img)

    crate_motif(d, (int(W * 0.58), int(H * 0.10), int(W * 0.95), int(H * 0.90)))

    pad = int(W * 0.045)
    name = "SYNCED LYRICS"
    f_name = display_font(74)
    typeset(d, (pad, int(H * 0.235)), name, f_name, TEXT, tracking=0.035)
    f_name2 = display_font(74)
    typeset(d, (pad, int(H * 0.415)), "DOWNLOADER", f_name2, TEXT, tracking=0.035)
    d.rectangle([pad, int(H * 0.60), pad + int(W * 0.20), int(H * 0.60) + 3],
                fill=RED)

    sub = mono_font(17)
    d.text((pad, int(H * 0.655)),
           "SYNCED FIRST  ·  PLAIN AS FALLBACK  ·  NO ACCOUNT  ·  LOCAL-FIRST",
           font=sub, fill=TEXT_DIM)
    d.text((pad, int(H * 0.715)),
           "Lrclib · Musixmatch · Megalobiz · NetEase · Genius",
           font=sub, fill=TEXT_DIM)
    legend_board(d, (pad, int(H * 0.80), int(W * 0.53), int(H * 0.93)))
    img.putalpha(255)   # the ground is opaque; do not leave edge fringe
    return img


def social() -> Image.Image:
    """GitHub social preview, 1280x640."""
    W, H = 1280, 640
    img = Image.new("RGBA", (W, H), rgb(T.CRATE))
    d = ImageDraw.Draw(img)

    m = mark(150)
    img.paste(m, (int(W * 0.5 - 75), int(H * 0.15)), m)

    f_name = display_font(58)
    name = "SYNCED LYRICS DOWNLOADER"
    tw = tracked_width(d, name, f_name, 0.04)
    typeset(d, (W / 2 - tw / 2, int(H * 0.435)), name, f_name, TEXT, tracking=0.04)
    d.rectangle([W / 2 - tw / 2, int(H * 0.545), W / 2 + tw / 2, int(H * 0.545) + 3],
                fill=RED)
    sub = mono_font(17)
    line = "SYNCED FIRST  ·  PLAIN AS FALLBACK  ·  NO ACCOUNT  ·  LOCAL-FIRST"
    stw = d.textlength(line, font=sub)
    d.text((W / 2 - stw / 2, int(H * 0.605)), line, font=sub, fill=TEXT_DIM)

    legend_board(d, (W * 0.5 - 340, int(H * 0.72), W * 0.5 + 340, int(H * 0.83)))

    crate_motif(d, (-40, int(H * 0.62), 250, H + 40))
    crate_motif(d, (W - 250, int(H * 0.62), W + 40, H + 40))
    img.putalpha(255)   # the ground is opaque; do not leave edge fringe
    return img


# --------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--icon", action="store_true", help="only build/icon.ico")
    args = ap.parse_args()

    assert_contrast()
    report_palette_gaps()
    BUILD.mkdir(exist_ok=True)

    if args.icon:
        print("icon:")
        write_ico(BUILD / "icon.ico")
        return

    print("icon:")
    write_ico(BUILD / "icon.ico")
    # The shipped copy. Tk's iconbitmap needs a real .ico to set the window
    # icons Windows actually reads for the taskbar, and build/ is gitignored,
    # so a source checkout would otherwise have no .ico to point at.
    write_ico(ART / "icon.ico")

    print("mark:")
    for size, name in ((1024, "icon-1024.png"), (512, "icon-512.png"),
                       (256, "icon-256.png"), (128, "icon-128.png")):
        save(mark(size), ART / name, f"app mark at {size}px, transparent")
    save(mark(512, ground=rgb(T.CRATE)),
         ART / "icon-on-dark.png", "app mark on crate ground")
    save(mark_mono(512), ART / "mark-mono.png", "app mark, single ink, transparent")

    print("lockup:")
    save(wordmark(46), ART / "wordmark-on-dark.png", "wordmark on crate ground")
    save(wordmark(46, on_dark=False), ART / "wordmark.png",
         "wordmark, transparent")

    print("compositions:")
    save(hero(), ART / "readme-hero.png", "README hero banner")
    save(social(), ART / "social-preview.png", "GitHub social preview 1280x640")

    manifest = {
        "mark": "The Record",
        "source_of_truth": "lyricsdl/ui/theme.py",
        "generator": "tools/make_art.py",
        "app_version": __version__,
        "generated": datetime.datetime.now(datetime.UTC).isoformat(
            timespec="seconds").replace("+00:00", "Z"),
        "assets": (sorted(p.name for p in ART.glob("*.png"))
                   + ["icon.ico", "../build/icon.ico"]),
    }
    (ART / "provenance.json").write_text(json.dumps(manifest, indent=2) + "\n",
                                         encoding="utf-8")
    print(f"  {ART.relative_to(ROOT) / 'provenance.json'}")


if __name__ == "__main__":
    main()
