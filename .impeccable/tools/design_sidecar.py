"""Generate .impeccable/design.json from the shipped design tokens.

Dev-only. Tonal ramps are computed from the real token hexes (same hue and
saturation, lightness stepped 15% -> 95%) rather than eyeballed, so the panel
swatches always match the app. Re-run after changing lyricsdl/ui/theme.py.
"""

from __future__ import annotations

import datetime
import json
import math
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[2]
THEME = ROOT / "lyricsdl" / "ui" / "theme.py"
OUT = ROOT / ".impeccable" / "design.json"

# token slug -> (display name, role)
COLOR_META = {
    "crate-ground": ("Crate Ground", "neutral"),
    "crate-recess": ("Crate Recess", "neutral"),
    "panel": ("Crate Panel", "neutral"),
    "panel-raised": ("Panel Raised", "neutral"),
    "edge": ("Edge Hairline", "neutral"),
    "kraft": ("Kraft Stock", "secondary"),
    "kraft-shade": ("Kraft Shade", "secondary"),
    "kraft-edge": ("Kraft Rule", "neutral"),
    "ink": ("Board Ink", "neutral"),
    "ink-soft": ("Ink Soft", "neutral"),
    "ink-faint": ("Ink Faint", "neutral"),
    "silkscreen-red": ("Silkscreen Tab Red", "primary"),
    "silkscreen-red-deep": ("Silkscreen Red Deep", "primary"),
    "silkscreen-red-soft": ("Silkscreen Red Soft", "primary"),
    "filed-green": ("Filed Green", "tertiary"),
    "pending-amber": ("Pending Amber", "tertiary"),
    "absent-grey": ("Absent Grey", "tertiary"),
    "filed-green-ink": ("Filed Green Ink", "tertiary"),
    "pending-amber-ink": ("Pending Amber Ink", "tertiary"),
    "absent-grey-ink": ("Absent Grey Ink", "tertiary"),
    "text": ("Board Text", "neutral"),
    "text-dim": ("Text Dim", "neutral"),
    "text-faint": ("Text Faint", "neutral"),
    "focus": ("Focus Amber", "neutral"),
}


# token slug -> theme.py constant name. This is the real mapping; slugs are
# descriptive for the frontmatter, constants are terse in the theme module.
FRONTMATTER_KEYS = {
    "crate-ground": "CRATE", "crate-recess": "CRATE_DEEP", "panel": "PANEL",
    "panel-raised": "PANEL_HI", "edge": "PANEL_EDGE", "kraft": "STOCK",
    "kraft-shade": "STOCK_DIM", "kraft-edge": "STOCK_EDGE", "ink": "INK",
    "ink-soft": "INK_SOFT", "ink-faint": "INK_FAINT",
    "silkscreen-red": "RED", "silkscreen-red-deep": "RED_DEEP",
    "silkscreen-red-soft": "RED_SOFT", "filed-green": "GREEN",
    "pending-amber": "AMBER", "absent-grey": "VOID", "filed-green-ink": "GREEN_INK",
    "pending-amber-ink": "AMBER_INK", "absent-grey-ink": "VOID_INK",
    "text": "TEXT", "text-dim": "TEXT_DIM", "text-faint": "TEXT_FAINT",
    "focus": "FOCUS",
}


def read_colors() -> dict[str, str]:
    """Pull the token hexes straight out of theme.py so they cannot drift."""
    src = THEME.read_text(encoding="utf-8")
    found = dict(re.findall(r'^([A-Z][A-Z_0-9]*) = "(#[0-9A-Fa-f]{6})"', src, re.M))
    return found


def ramp(hex_color: str, steps: int = 8) -> list[str]:
    """Dark -> light at constant hue and chroma.

    Synthesised in OKLCH, as the DESIGN.md spec prescribes. HSL would step
    *saturation*, which over-saturates the dark end (kraft #E8E2D2 comes out
    brown). Chroma is held and reduced only where sRGB cannot hold it.
    """
    lightness, chroma, hue = to_oklch(hex_color)
    out = []
    for i in range(steps):
        step_l = 0.15 + (0.95 - 0.15) * (i / (steps - 1))
        out.append(from_oklch(step_l, chroma, hue))
    return out


def to_oklch(hex_color: str) -> tuple[float, float, float]:
    r, g, b = (_srgb_to_linear(c) for c in _rgb(hex_color))
    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    l_, m_, s_ = _cbrt(l), _cbrt(m), _cbrt(s)
    lightness = 0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_
    a = 1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_
    bb = 0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_
    return lightness, math.hypot(a, bb), math.degrees(math.atan2(bb, a)) % 360


def from_oklch(lightness: float, chroma: float, hue: float) -> str:
    while chroma > 0.0005 and not _in_gamut(lightness, chroma, hue):
        chroma *= 0.96
    a = chroma * math.cos(math.radians(hue))
    bb = chroma * math.sin(math.radians(hue))
    l_ = lightness + 0.3963377774 * a + 0.2158037573 * bb
    m_ = lightness - 0.1055613458 * a - 0.0638541728 * bb
    s_ = lightness - 0.0894841775 * a - 1.2914855480 * bb
    l, m, s = l_ ** 3, m_ ** 3, s_ ** 3
    return _hex((
        _linear_to_srgb(4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s),
        _linear_to_srgb(-1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s),
        _linear_to_srgb(-0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s),
    ))


def _in_gamut(lightness: float, chroma: float, hue: float) -> bool:
    a = chroma * math.cos(math.radians(hue))
    bb = chroma * math.sin(math.radians(hue))
    l_ = lightness + 0.3963377774 * a + 0.2158037573 * bb
    m_ = lightness - 0.1055613458 * a - 0.0638541728 * bb
    s_ = lightness - 0.0894841775 * a - 1.2914855480 * bb
    l, m, s = l_ ** 3, m_ ** 3, s_ ** 3
    for channel in (
        4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
        -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
        -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s,
    ):
        if not -1e-4 <= channel <= 1 + 1e-4:
            return False
    return True


def _cbrt(x: float) -> float:
    return math.copysign(abs(x) ** (1 / 3), x)


def _srgb_to_linear(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _linear_to_srgb(c: float) -> float:
    c = max(0.0, min(1.0, c))
    return 12.92 * c if c <= 0.0031308 else 1.055 * (c ** (1 / 2.4)) - 0.055


def _rgb(hex_color: str) -> tuple[float, float, float]:
    v = hex_color.lstrip("#")
    return tuple(int(v[i:i + 2], 16) / 255 for i in (0, 2, 4))


def _hex(rgb) -> str:
    return "#" + "".join(f"{max(0, min(255, round(c * 255))):02X}" for c in rgb)


SHELL = (
    "font-family: Bahnschrift, 'Segoe UI', Helvetica, sans-serif;"
    "background: #211F1D; color: #EDE8DC; padding: 18px;"
    "display: flex; gap: 10px; align-items: center; flex-wrap: wrap;"
)

MARK_SVG = {
    "synced": (
        '<svg width="22" height="22" viewBox="0 0 22 22" fill="none" stroke="{c}" '
        'stroke-width="2" stroke-linecap="round">'
        '<circle cx="11" cy="11" r="8.5"/><path d="M7.2 11.2l2.6 2.6 5-5.2"/></svg>'
    ),
    "plain": (
        '<svg width="22" height="22" viewBox="0 0 22 22" fill="none" stroke="{c}" '
        'stroke-width="2" stroke-linecap="round">'
        '<rect x="2.5" y="2.5" width="17" height="17"/>'
        '<path d="M7 9h9M7 14h6"/></svg>'
    ),
    "incomplete": (
        '<svg width="22" height="22" viewBox="0 0 22 22" fill="none" stroke="{c}" '
        'stroke-width="2" stroke-linecap="round" stroke-linejoin="miter">'
        '<path d="M11 2.5L20 19H2z"/><path d="M11 8.5v5"/><path d="M11 16.2v.1"/></svg>'
    ),
    "none": (
        '<svg width="22" height="22" viewBox="0 0 22 22" fill="none" stroke="{c}" '
        'stroke-width="2" stroke-linecap="round">'
        '<circle cx="11" cy="11" r="8.5"/><path d="M6.5 15.5l9-9"/></svg>'
    ),
    "some": (
        '<svg width="22" height="22" viewBox="0 0 22 22" fill="none" stroke="{c}" '
        'stroke-width="2"><circle cx="11" cy="11" r="8.5"/>'
        '<path d="M11 2.5a8.5 8.5 0 000 17z" fill="{c}" stroke="none"/></svg>'
    ),
}


def components() -> list[dict]:
    # Read green from the tokens rather than hardcoding it: the showcase pinned
    # it as a literal and went stale the moment the token moved to clear its
    # contrast floor.
    _tokens = read_colors()
    green = _tokens.get("GREEN", "#6F8163")
    btn = (
        ".ds-nav { display:flex; gap:8px; align-items:center; }"
        ".ds-btn { font-family:'Bahnschrift SemiCondensed','Arial Narrow','Segoe UI',sans-serif;"
        " font-size:11px; font-weight:700; letter-spacing:.04em; text-transform:uppercase;"
        " height:30px; padding:0 18px; border-radius:0; border:1px solid transparent;"
        " cursor:pointer; transition:background .12s linear; }"
        ".ds-btn-primary { background:#C8452F; color:#E8E2D2; }"
        ".ds-btn-primary:hover { background:#A93622; }"
        ".ds-btn-primary:focus-visible { outline:2px solid #F0C46A; outline-offset:2px; }"
        ".ds-btn-secondary { background:#2B2A28; color:#EDE8DC; border-color:#3A3835; }"
        ".ds-btn-secondary:hover { background:#343230; }"
        ".ds-btn-secondary:focus-visible { outline:2px solid #F0C46A; outline-offset:2px; }"
        ".ds-btn[disabled] { background:#211F1D; color:#867E6E; cursor:default; }"
    )
    rows = (
        ".ds-crate { font-family:'Bahnschrift','Segoe UI',sans-serif; width:320px;"
        " background:#191716; padding:0; }"
        ".ds-row { display:flex; align-items:center; height:24px; font-size:11px;"
        " color:#EDE8DC; border-bottom:1px solid #3A3835; padding:0 8px; }"
        ".ds-row--sel { background:#E8E2D2; color:#1C1A17; border-bottom:none;"
        " transform:translateX(7px); }"
        ".ds-row__num { font-family:'Cascadia Mono',Consolas,monospace; font-size:9px;"
        " color:#867E6E; width:30px; }"
        ".ds-row--sel .ds-row__num { color:#5A5344; }"
        ".ds-row__title { flex:1; }"
        ".ds-row__meta { font-family:'Cascadia Mono',Consolas,monospace; font-size:9px;"
        " color:#867E6E; margin-right:18px; }"
        ".ds-row--sel .ds-row__meta { color:#5A5344; }"
    )
    divider = (
        ".ds-divider { display:flex; align-items:center; height:32px;"
        " background:#D9D1BC; border-bottom:1px solid #BCB29A;"
        " font-family:'Bahnschrift SemiCondensed','Arial Narrow','Segoe UI',sans-serif; }"
        ".ds-divider--sel { background:#E8E2D2; }"
        ".ds-divider__tab { width:26px; height:100%; display:flex; align-items:center;"
        " justify-content:center; background:#211F1D; color:#A79E8C; font-size:10px;"
        " font-weight:700; }"
        ".ds-divider--sel .ds-divider__tab { background:#C8452F; color:#E8E2D2; }"
        ".ds-divider__name { flex:1; padding-left:10px; font-size:12px; font-weight:700;"
        " color:#1C1A17; }"
        ".ds-divider__mark { margin-right:14px; line-height:0; }"
    )
    marks = (
        ".ds-marks { display:flex; gap:22px; align-items:center; }"
        ".ds-mark { display:flex; flex-direction:column; gap:6px; align-items:center;"
        " font-family:'Bahnschrift SemiCondensed','Arial Narrow','Segoe UI',sans-serif;"
        " font-size:10px; font-weight:700; letter-spacing:.04em; text-transform:uppercase;"
        " color:#A79E8C; }"
        ".ds-mark--stock { color:#5A5344; }"
    )
    logsheet = (
        ".ds-log { width:520px; background:#2B2A28; border:1px solid #3A3835;"
        " padding:8px 12px; font-family:'Cascadia Mono',Consolas,monospace;"
        " font-size:9px; line-height:1.5; color:#CFC7B4; }"
        ".ds-log__lvl { font-weight:400; }"
        ".ds-log .ok { color:#8FBE7A; } .ds-log .warn { color:#E0B45C; }"
        ".ds-log .err { color:#E08573; } .ds-log .step { color:#9E9583; }"
    )
    field = (
        ".ds-field { width:340px; height:34px; background:#2B2A28; border:1px solid #3A3835;"
        " border-radius:0; color:#EDE8DC; padding:0 10px; font-size:12px;"
        " font-family:'Bahnschrift','Segoe UI',sans-serif; }"
        ".ds-field:focus { outline:none; border-color:#3A3835; }"
        ".ds-field::placeholder { color:#867E6E; }"
    )
    toggle = (
        ".ds-toggle { font-family:'Bahnschrift SemiCondensed','Arial Narrow','Segoe UI',sans-serif;"
        " font-size:10px; font-weight:700; letter-spacing:.04em; text-transform:uppercase;"
        " height:22px; padding:0 10px; background:transparent; color:#A79E8C; border:0;"
        " border-radius:0; cursor:pointer; }"
        ".ds-toggle:hover { background:#343230; color:#EDE8DC; }"
        ".ds-toggle:focus-visible { outline:2px solid #F0C46A; }"
    )
    header = (
        ".ds-pane { width:330px; background:#191716; }"
        ".ds-pane__head { display:flex; align-items:center; height:30px; background:#2B2A28;"
        " padding:0 12px 0 12px; gap:8px; }"
        ".ds-pane__title { font-family:'Bahnschrift SemiCondensed','Arial Narrow','Segoe UI',sans-serif;"
        " font-size:10px; font-weight:700; letter-spacing:.04em; text-transform:uppercase;"
        " color:#A79E8C; }"
        ".ds-pane__count { font-family:'Cascadia Mono',Consolas,monospace; font-size:9px;"
        " color:#867E6E; }"
        ".ds-pane__rule { height:2px; background:#C8452F; }"
    )

    return [
        {
            "name": "Silk Button",
            "kind": "button",
            "refersTo": "silk-button-primary",
            "description": "The action vocabulary: flat, hard-edged, condensed caps. Red is the one primary action per surface.",
            "html": "<div class=\"ds-nav\">"
                    "<button class=\"ds-btn ds-btn-primary\">DOWNLOAD SELECTION</button>"
                    "<button class=\"ds-btn ds-btn-secondary\">CANCEL</button>"
                    "<button class=\"ds-btn\" disabled>SILK DISABLED</button></div>",
            "css": SHELL + btn,
        },
        {
            "name": "Crate Track Rows",
            "kind": "custom",
            "refersTo": "crate-row-track",
            "description": "The tracklist: recessed rows ruled by a hairline, mono number and running-time slot, state mark at the right. The selected row is pulled 7px forward onto kraft.",
            "html": "<div class=\"ds-crate\">"
                    "<div class=\"ds-row\"><span class=\"ds-row__num\">01</span>"
                    "<span class=\"ds-row__title\">Footnote</span>"
                    "<span class=\"ds-row__meta\">04:12</span>" + MARK_SVG["synced"].format(c=green) + "</div>"
                    "<div class=\"ds-row\"><span class=\"ds-row__num\">02</span>"
                    "<span class=\"ds-row__title\">Marginalia</span>"
                    "<span class=\"ds-row__meta\">02:58</span>" + MARK_SVG["plain"].format(c="#8A8377") + "</div>"
                    "<div class=\"ds-row ds-row--sel\"><span class=\"ds-row__num\">03</span>"
                    "<span class=\"ds-row__title\">Erratum</span>"
                    "<span class=\"ds-row__meta\">03:41</span>" + MARK_SVG["incomplete"].format(c="#8A5A12") + "</div>"
                    "<div class=\"ds-row\"><span class=\"ds-row__num\">05</span>"
                    "<span class=\"ds-row__title\">Appendix</span>"
                    "<span class=\"ds-row__meta\">MP3</span>" + MARK_SVG["none"].format(c="#8A8377") + "</div>"
                    "</div>",
            "css": SHELL + rows,
        },
        {
            "name": "Artist Divider",
            "kind": "custom",
            "refersTo": "crate-row-divider-selected",
            "description": "A kraft board with a 26px tab at its head. Selecting it inverts the tab to silkscreen red and pulls the board forward; the folder-state mark sits at its right edge in kraft ink.",
            "html": "<div style=\"width:340px\">"
                    "<div class=\"ds-divider\"><span class=\"ds-divider__tab\">H</span>"
                    "<span class=\"ds-divider__name\">Halden &amp; the Low Tide</span></div>"
                    "<div class=\"ds-divider ds-divider--sel\"><span class=\"ds-divider__tab\">T</span>"
                    "<span class=\"ds-divider__name\">The Marginal Notes</span>"
                    "<span class=\"ds-divider__mark\">" + MARK_SVG["some"].format(c="#8A5A12") + "</span></div>"
                    "</div>",
            "css": SHELL + divider,
        },
        {
            "name": "State Marks",
            "kind": "custom",
            "refersTo": "crate-row-track",
            "description": "The signature: five drawn silhouettes, no emoji and no icon font. Each state is a different shape, so it survives greyscale and colour-blindness. Both inks shown.",
            "html": "<div class=\"ds-marks\">"
                    + "".join(
                        f"<span class=\"ds-mark\">{MARK_SVG[k].format(c=c)}<span>{label}</span></span>"
                        for k, label, c in (
                            ("synced", "synced", green),
                            ("plain", "plain", "#8A8377"),
                            ("incomplete", "incomplete", "#C08A2E"),
                            ("none", "missing", "#8A8377"),
                            ("some", "partial", "#C08A2E"),
                        )
                    )
                    + "</div>"
                    "<div class=\"ds-marks\" style=\"margin-top:14px\">"
                    + "".join(
                        f"<span class=\"ds-mark ds-mark--stock\">{MARK_SVG[k].format(c=c)}<span>{label}</span></span>"
                        for k, label, c in (
                            ("synced", "complete", "#3F4C38"),
                            ("incomplete", "partial", "#8A5A12"),
                            ("none", "empty", "#6B6355"),
                        )
                    )
                    + "</div>",
            "css": SHELL + marks,
        },
        {
            "name": "Pane Header",
            "kind": "nav",
            "refersTo": "pane-header",
            "description": "Each of the three bays: a raised panel header carrying the title, a mono count and an All/Clear toggle, over the 2px silkscreen rule that makes it read as a crate bay.",
            "html": "<div class=\"ds-pane\">"
                    "<div class=\"ds-pane__head\"><span class=\"ds-pane__title\">Albums</span>"
                    "<span class=\"ds-pane__count\">2</span>"
                    "<button class=\"ds-toggle\" style=\"margin-left:auto\">ALL</button></div>"
                    "<div class=\"ds-pane__rule\"></div></div>",
            "css": SHELL + header + toggle,
        },
        {
            "name": "Log Sheet",
            "kind": "card",
            "refersTo": "log-sheet",
            "description": "The ruled record of a job. Fixed-height by design — it is a receipt, not a work surface. Levels are carried by mono text colour on the raised panel.",
            "html": "<div class=\"ds-log\">"
                    "<div><span class=\"ds-log__lvl\">INFO </span>Library: D:\\MUSIC</div>"
                    "<div><span class=\"ds-log__lvl\">STEP </span>trying synced: Lrclib</div>"
                    "<div><span class=\"ds-log__lvl ok\">OK   </span>Saved [Lrclib/synced]</div>"
                    "<div><span class=\"ds-log__lvl warn\">WARN </span>Cancel requested.</div>"
                    "<div><span class=\"ds-log__lvl err\">ERR  </span>Not found</div>"
                    "</div>",
            "css": SHELL + logsheet,
        },
        {
            "name": "Entry Field",
            "kind": "input",
            "refersTo": "entry",
            "description": "Square, panel-filled, 1px edge stroke. Focus keeps the stroke and the caret; no glow, no ring, no colour shift — focus is not a colour event in this world.",
            "html": "<input class=\"ds-field\" value=\"The Marginal Notes: Annotated - Marginalia\">",
            "css": SHELL + field,
        },
    ]


def main() -> None:
    colors = read_colors()
    missing = [const for const in FRONTMATTER_KEYS.values() if const not in colors]
    if missing:
        raise SystemExit(f"theme.py is missing tokens: {missing}")

    color_meta = {}
    for slug, const in FRONTMATTER_KEYS.items():
        display, role = COLOR_META[slug]
        hex_value = colors[const]
        color_meta[slug] = {
            "role": role,
            "displayName": display,
            "canonical": hex_value,
            "tonalRamp": ramp(hex_value),
        }

    doc = {
        "schemaVersion": 2,
        "generatedAt": datetime.datetime.now(datetime.UTC).isoformat().replace("+00:00", "Z"),
        "title": "Design System: Synced Lyrics Downloader",
        "extensions": {
            "colorMeta": color_meta,
            "typographyMeta": {
                "display": {"displayName": "Display", "purpose": "The wordmark, and nothing else."},
                "headline": {"displayName": "Headline", "purpose": "Dialog titles."},
                "title": {"displayName": "Title", "purpose": "Artist divider labels — the largest text inside a list."},
                "body": {"displayName": "Body", "purpose": "Spines, track titles, dialog copy, status text."},
                "label": {"displayName": "Label", "purpose": "Pane headers, legend, every button. Condensed caps."},
                "mono": {"displayName": "Mono", "purpose": "Track numbers, timings, counts, the log sheet, paths."},
            },
            "shadows": [],
            "motion": [
                {"name": "pull-forward", "value": "7px in 16ms steps, ease-out cubic, ~96ms",
                 "purpose": "The one authored moment: a selected row slides forward onto kraft to sit proud of the crate."},
                {"name": "state-hover", "value": "background-color .12s linear",
                 "purpose": "Row and button hover. Colour only; nothing moves, nothing fades."},
                {"name": "ui-pump", "value": "50ms",
                 "purpose": "Worker-thread events are drained onto the Tk main thread on a 50ms timer."},
            ],
            "breakpoints": [
                {"name": "min-window", "value": "940x640",
                 "purpose": "Native desktop: the smallest window the three panes still hold. Above 1180x800 the crate absorbs the extra height."},
            ],
            "materials": [
                {"name": "crate-board", "value": "#211F1D / #191716 / #2B2A28 / #343230",
                 "purpose": "Four fixed tonal steps of one near-black board: ground, recess, panel, hover. Never more, never fewer."},
                {"name": "kraft-stock", "value": "#E8E2D2 / #D9D1BC / #BCB29A",
                 "purpose": "The only light material. Reserved for what the user can pick up: dividers, pulled-forward records, legend boards."},
            ],
        },
        "components": components(),
        "narrative": {
            "northStar": "The Record Crate",
            "overview": (
                "A music library is not a file tree; it is a crate of records you flip through. Every surface says so. "
                "Artists are kraft board dividers with a tab at the spine; albums are record spines stacked behind them; "
                "the selected record's tracklist is a ruled sheet; the job that ran is a ruled log sheet pinned below.\n\n"
                "The world is built from two materials only: near-black crate board and kraft stock. Depth comes from three "
                "fixed tones of the dark board plus one hairline rule. Kraft is reserved for things you can pick up. The accent "
                "is silkscreen ink, and it is rationed hard.\n\n"
                "State is never carried by colour alone. Each lyric state has its own drawn geometry, stamped at the right edge "
                "of the row. Colour reinforces the shape; it never replaces it."
            ),
            "keyCharacteristics": [
                "Two materials: near-black crate board and kraft stock, no third.",
                "Hard edges everywhere — a single radius of 0.",
                "One saturated accent (silkscreen tab red) rationed to ≤3% of a screen.",
                "Drawn vector state marks; zero emoji, zero icon fonts, zero glyph-as-icon.",
                "Condensed grotesque caps for anything that names or labels; mono for counts, timings and the log.",
                "Legibility proven by pixel: body text clears 4.5:1, marks clear 3:1 on both materials.",
            ],
            "rules": [
                {"name": "The Kraft Rule",
                 "body": "Kraft stock means pick me up: a divider you flip, a record pulled forward, a printed legend board. It is never a background, never a container, never a section fill.",
                 "section": "colors"},
                {"name": "The Two-Inks Rule",
                 "body": "The three state colours exist in two inks. On the dark board use Filed Green / Pending Amber / Absent Grey; on kraft use Filed Green Ink / Pending Amber Ink / Absent Grey Ink. The dark-board trio fails 3:1 on kraft — using it there is a bug, not a style choice.",
                 "section": "colors"},
                {"name": "The Caps Rule",
                 "body": "Anything that names a surface, a control or a category is condensed-grotesque uppercase. Anything that is data — a number, a timecode, a path, a log line — is mono. Prose stays in body case.",
                 "section": "typography"},
                {"name": "The Truncate Rule",
                 "body": "Long labels are cut with an ellipsis measured against the real font, never wrapped and never allowed to collide with the mark or the meta column. A row is one line, always.",
                 "section": "typography"},
                {"name": "The Flat-By-Default Rule",
                 "body": "Surfaces are flat at rest and flat when active. A shadow is always a bug; if a boundary is unclear, the answer is a 1px rule or a tonal step, never box-shadow.",
                 "section": "elevation"},
                {"name": "The Hard-Edge Rule",
                 "body": "Radius is 0 everywhere. If a surface wants to feel soft, it has chosen the wrong world.",
                 "section": "shapes"},
            ],
            "dos": [
                "Do keep to the two materials. Kraft for things you pick up; Crate Ground / Recess / Panel for everything structural.",
                "Do use the Two-Inks Rule when a mark lands on kraft — Filed Green Ink, Pending Amber Ink, Absent Grey Ink.",
                "Do pair every colour-coded state with its shape, so state survives greyscale.",
                "Do keep the silkscreen red under 3% of any screen.",
                "Do draw a hairline rather than add a shadow when two surfaces need separating.",
                "Do solve collisions by reserving the column: the mark sits at x1 − meta_w − 6, clear of both the meta text and the rail.",
                "Do measure condensed labels with the real font and truncate with an ellipsis.",
            ],
            "donts": [
                "Don't add a shadow, glow, gradient or blur.",
                "Don't round a corner. Radius is 0, including on checkbox boxes, entries and dialogs.",
                "Don't use emoji, icon fonts, or unicode glyphs as icons. State marks are drawn geometry.",
                "Don't use Crate Recess for a raised surface or Panel for a sunken one.",
                "Don't let the log sheet expand; it is a fixed strip and the crate owns the window.",
                "Don't use Silkscreen Tab Red for a large fill. Kraft is the selection material, red is the tab.",
            ],
        },
    }

    OUT.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}  ({len(doc['components'])} components, "
          f"{len(color_meta)} colour tokens with ramps)")


if __name__ == "__main__":
    main()
