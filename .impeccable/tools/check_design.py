"""Drift check: DESIGN.md + .impeccable/design.json vs the shipped tokens.

Dev-only. Run: python .impeccable/tools/check_design.py

The design system is generated from lyricsdl/ui/theme.py, so the three can
silently disagree. This is the assertion that catches it.
"""

from __future__ import annotations

import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from design_sidecar import FRONTMATTER_KEYS, read_colors  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
CANONICAL = ["Overview", "Colors", "Typography", "Layout", "Elevation & Depth",
             "Shapes", "Components", "Do's and Don'ts"]
ALLOWED_TOP = {"colors", "typography", "rounded", "spacing", "components"}


def main() -> None:
    md = (ROOT / "DESIGN.md").read_text(encoding="utf-8")
    assert md.startswith("---\n"), "DESIGN.md must open with YAML frontmatter"
    body, frontmatter, rest = md.split("---\n", 2)
    theme = read_colors()

    # 1. Frontmatter hexes must equal the shipped theme tokens.
    declared = dict(re.findall(r'^  ([a-z0-9-]+): "(#[0-9A-Fa-f]{6})"', frontmatter, re.M))
    assert declared, "no colour tokens found in the frontmatter"
    unknown = [s for s in declared if s not in FRONTMATTER_KEYS]
    assert not unknown, f"frontmatter colours with no theme mapping: {unknown}"
    drift = [
        (slug, value, theme[FRONTMATTER_KEYS[slug]])
        for slug, value in declared.items()
        if value.upper() != theme[FRONTMATTER_KEYS[slug]].upper()
    ]
    assert not drift, f"DESIGN.md drifted from theme.py: {drift}"

    # 2. Canonical section order, exactly.
    heads = re.findall(r"^## (.+)$", rest, re.M)
    assert heads == CANONICAL, f"sections out of order or renamed: {heads}"

    # 3. Frontmatter must stay inside Stitch's schema.
    try:
        import yaml
        data = yaml.safe_load(frontmatter)
    except ImportError:
        data = None
    if data:
        extra = set(data) - ALLOWED_TOP - {"name", "description"}
        assert not extra, f"frontmatter token groups outside the schema: {extra}"
        for group in ("colors", "typography", "rounded", "spacing", "components"):
            assert group in data, f"frontmatter is missing '{group}'"

    # 4. The sidecar must cover every colour token and carry real ramps.
    sidecar = json.loads((ROOT / ".impeccable" / "design.json").read_text(encoding="utf-8"))
    assert sidecar["schemaVersion"] == 2, sidecar["schemaVersion"]
    color_meta = sidecar["extensions"]["colorMeta"]
    assert set(color_meta) == set(FRONTMATTER_KEYS), "sidecar colours out of sync"
    for slug, meta in color_meta.items():
        assert meta["canonical"] == theme[FRONTMATTER_KEYS[slug]], f"{slug} canonical drifted"
        assert len(meta["tonalRamp"]) == 8, f"{slug} ramp is not 8 steps"
        assert len(set(meta["tonalRamp"])) == 8, f"{slug} ramp has duplicate steps"
    assert sidecar["extensions"]["shadows"] == [], "this world has no shadows"
    assert not (ALLOWED_TOP & set(sidecar["extensions"])), "extensions duplicated the frontmatter"

    # 5. Every component must be a drop-in snippet, scoped and non-empty.
    assert 5 <= len(sidecar["components"]) <= 10, len(sidecar["components"])
    for comp in sidecar["components"]:
        assert comp.get("css"), f"{comp['name']} has no css"
        assert "ds-" in comp["css"], f"{comp['name']} css is not ds- scoped"

    print(f"ok — {len(declared)} colours, {len(sidecar['components'])} components, "
          f"{len(sidecar['narrative']['rules'])} named rules")


if __name__ == "__main__":
    main()
