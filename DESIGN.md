---
name: Synced Lyrics Downloader
description: A record crate for your music library — browse, stamp and file synced lyrics.
colors:
  crate-ground: "#211F1D"
  crate-recess: "#191716"
  panel: "#2B2A28"
  panel-raised: "#343230"
  edge: "#3A3835"
  kraft: "#E8E2D2"
  kraft-shade: "#D9D1BC"
  kraft-edge: "#BCB29A"
  ink: "#1C1A17"
  ink-soft: "#5A5344"
  ink-faint: "#8B8474"
  silkscreen-red: "#C8452F"
  silkscreen-red-deep: "#A93622"
  silkscreen-red-soft: "#E2836C"
  filed-green: "#6F8163"
  pending-amber: "#C08A2E"
  absent-grey: "#8A8377"
  filed-green-ink: "#3F4C38"
  pending-amber-ink: "#8A5A12"
  absent-grey-ink: "#6B6355"
  text: "#EDE8DC"
  text-dim: "#A79E8C"
  text-faint: "#989081"
  focus: "#F0C46A"
typography:
  display:
    fontFamily: "Bahnschrift SemiCondensed, Bahnschrift Condensed, Arial Narrow, Segoe UI, sans-serif"
    fontSize: "17px"
    fontWeight: 700
    lineHeight: 1.05
  headline:
    fontFamily: "Bahnschrift SemiCondensed, Bahnschrift Condensed, Arial Narrow, Segoe UI, sans-serif"
    fontSize: "15px"
    fontWeight: 700
    lineHeight: 1.1
  title:
    fontFamily: "Bahnschrift SemiCondensed, Bahnschrift Condensed, Arial Narrow, Segoe UI, sans-serif"
    fontSize: "12px"
    fontWeight: 700
    lineHeight: 1.2
  body:
    fontFamily: "Bahnschrift, Segoe UI, Helvetica, sans-serif"
    fontSize: "11px"
    fontWeight: 400
    lineHeight: 1.35
  label:
    fontFamily: "Bahnschrift SemiCondensed, Bahnschrift Condensed, Arial Narrow, Segoe UI, sans-serif"
    fontSize: "10px"
    fontWeight: 700
    lineHeight: 1.2
    letterSpacing: "0.04em"
  mono:
    fontFamily: "Cascadia Mono, Consolas, DejaVu Sans Mono, Courier New, monospace"
    fontSize: "9px"
    fontWeight: 400
    lineHeight: 1.3
rounded:
  sharp: "0px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "12px"
  lg: "16px"
  xl: "24px"
components:
  silk-button-primary:
    backgroundColor: "{colors.silkscreen-red}"
    textColor: "{colors.kraft}"
    typography: "{typography.label}"
    rounded: "{rounded.sharp}"
    padding: "0 18px"
    height: "30px"
  silk-button-primary-hover:
    backgroundColor: "{colors.silkscreen-red-deep}"
    textColor: "{colors.kraft}"
    rounded: "{rounded.sharp}"
  silk-button-secondary:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.text}"
    typography: "{typography.label}"
    rounded: "{rounded.sharp}"
    padding: "0 16px"
    height: "30px"
  silk-button-disabled:
    backgroundColor: "{colors.crate-ground}"
    textColor: "{colors.text-faint}"
    rounded: "{rounded.sharp}"
  ghost-button:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.text-dim}"
    typography: "{typography.label}"
    rounded: "{rounded.sharp}"
    size: "44px"
    height: "22px"
  pane-header:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.text-dim}"
    typography: "{typography.label}"
    height: "30px"
  crate-row-divider:
    backgroundColor: "{colors.kraft-shade}"
    textColor: "{colors.ink}"
    typography: "{typography.title}"
    height: "32px"
  crate-row-divider-selected:
    backgroundColor: "{colors.kraft}"
    textColor: "{colors.ink}"
    typography: "{typography.title}"
    height: "32px"
  crate-row-spine:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.text}"
    typography: "{typography.body}"
    height: "26px"
  crate-row-spine-selected:
    backgroundColor: "{colors.kraft}"
    textColor: "{colors.ink}"
    typography: "{typography.body}"
    height: "26px"
  crate-row-track:
    backgroundColor: "{colors.crate-recess}"
    textColor: "{colors.text}"
    typography: "{typography.body}"
    height: "24px"
  crate-row-track-selected:
    backgroundColor: "{colors.kraft}"
    textColor: "{colors.ink}"
    typography: "{typography.body}"
    height: "24px"
  log-sheet:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.text-dim}"
    typography: "{typography.mono}"
    rounded: "{rounded.sharp}"
    padding: "8px 12px"
    height: "106px"
  entry:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.text}"
    typography: "{typography.body}"
    rounded: "{rounded.sharp}"
    padding: "0 10px"
    height: "34px"
---

# Design System: Synced Lyrics Downloader

## Overview

**Creative North Star: "The Record Crate"**

A music library is not a file tree; it is a crate of records you flip through.
Every surface says so. Artists are kraft board dividers with a tab at the
spine; albums are record spines stacked behind them; the selected record's
tracklist is a ruled sheet; the job that ran is a ruled log sheet pinned below.
Strip the content out and the pixels still read as a crate of tabbed records.

The world is built from two materials only: **near-black crate board** and
**kraft stock**. There is no third material, no shadow, no gradient. Depth comes
from three fixed tones of the dark board — a ground, a recess for the crate
interior, and a raised panel for toolbars and headers — plus one hairline rule.
Kraft is reserved for things you can pick up: a divider, a pulled-forward
record, a printed board in the legend. The accent is silkscreen ink, and it is
rationed hard.

State is never carried by colour alone. Each lyric state has its own drawn
geometry — a circled check for synced, a squared sheet for plain, a struck
triangle for incomplete, a struck circle for missing — stamped at the right edge
of the row. Colour reinforces the shape; it never replaces it. The same is true
of completeness on folders: a half-filled circle means partly complete.

**Key Characteristics:**
- Two materials: near-black crate board and kraft stock, no third.
- Hard edges everywhere — a single radius of 0.
- One saturated accent (silkscreen tab red) rationed to ≤3% of a screen.
- Drawn vector state marks; zero emoji, zero icon fonts, zero glyph-as-icon.
- Condensed grotesque caps for anything that names or labels; mono for counts, timings and the log.
- Legibility proven by pixel: body text clears 4.5:1, marks clear 3:1 on both materials.

## Colors

A near-monochrome world in two materials, with one rationed silkscreen accent
and a three-colour state vocabulary that exists in two inks — one for the dark
board, one for kraft.

### Primary
- **Silkscreen Tab Red** (#C8452F): the single accent. It marks the pulled-forward selection (the tab of the selected artist divider), the primary action button, the 2px printed rule under each pane header, and the 2px rule under a dialog title. Its rarity is the entire effect. **Silkscreen Red Deep** (#A93622) is its hover; **Silkscreen Red Soft** (#E2836C) is its error-text form on the dark board.

### Secondary
- **Filed Green** (#6F8163): a record has synced lyrics, or a folder is complete. Paired with the circled-check mark. Lifted from #5C6B52, which measured 2.88:1 on Crate Ground and 2.51:1 on Panel — below the 3:1 this system asks of a mark.
- **Pending Amber** (#C08A2E): lyrics exist but are incomplete, or a folder is partly filled. Paired with the struck-triangle or half-filled-circle mark.
- **Absent Grey** (#8A8377): no lyrics at all. Deliberately the quietest state — absence should not shout.

### Neutral
- **Crate Ground** (#211F1D): the application background. Everything sits on it.
- **Crate Recess** (#191716): the inside of a crate — the tracklist surface. One step darker than the ground, which is what makes the lists read as recessed slots rather than panels.
- **Panel** (#2B2A28): raised board — pane headers, the action bar, the status strip, the log sheet. One step lighter than the ground.
- **Panel Raised** (#343230): hover on a dark row.
- **Edge** (#3A3835): the hairline rule on dark. 1px, never thicker.
- **Kraft** (#E8E2D2) and **Kraft Shade** (#D9D1BC): the stock. Kraft is the selected/pulled-forward state; Kraft Shade is an unselected divider — the same board, marginally in shade. **Kraft Edge** (#BCB29A) is the printed hairline under a divider.
- **Ink** (#1C1A17), **Ink Soft** (#5A5344), **Ink Faint** (#8B8474): text on kraft. Three steps only.
- **Text** (#EDE8DC), **Text Dim** (#A79E8C), **Text Faint** (#989081): text on dark. All three clear 4.5:1 on the three surfaces text actually rests on — Crate Ground, Crate Recess and Panel (13.44 / 6.19 / 5.20 on the ground). Text Faint is reserved for metadata that is never load-bearing, and it was lifted from #867E6E, which measured 4.09:1 on the ground and 3.57:1 on Panel. One caveat, measured rather than assumed: on the *hover* step, Panel Raised, Text Faint reads 4.04:1. Closing that would need #A0998B, which is within [-7,-5,-1] of Text Dim — a third step below Dim cannot be AA on every surface without becoming Dim, so the ramp holds three steps and the hover shortfall is accepted.
- **Focus** (#F0C46A): the keyboard focus ring on the progress rail.

### Named Rules
**The Kraft Rule.** Kraft stock means *pick me up*: a divider you flip, a record pulled forward, a printed legend board. It is never a background, never a container, never a section fill.

**The Two-Inks Rule.** The three state colours exist in two inks. On the dark board use Filed Green / Pending Amber / Absent Grey; on kraft use Filed Green Ink (#3F4C38) / Pending Amber Ink (#8A5A12) / Absent Grey Ink (#6B6355). The dark-board trio fails 3:1 on kraft — using it there is a bug, not a style choice.

## Typography

**Display Font:** Bahnschrift SemiCondensed (with Bahnschrift Condensed, Arial Narrow, Segoe UI, sans-serif)
**Body Font:** Bahnschrift (with Segoe UI, Helvetica, sans-serif)
**Label/Mono Font:** Cascadia Mono (with Consolas, DejaVu Sans Mono, monospace)

**Character:** A condensed industrial grotesque — the lettering you would find
screen-printed on a crate divider — paired with a quiet mono for numbers. The
condensed caps let a 300px-wide pane hold a long artist name without truncating
it; the mono makes counts, timings and log lines align into columns.

The families are resolved at startup against what is actually installed; the
fallback chain is part of the system, not a failure. On a machine without
Bahnschrift the world degrades to Segoe UI and still holds.

### Hierarchy
- **Display** (700, 17px, 1.05): the wordmark, and nothing else.
- **Headline** (700, 15px, 1.1): dialog titles.
- **Title** (700, 12px, 1.2): artist divider labels — the largest text inside a list, because the artist is the thing you are flipping to.
- **Body** (400, 11px, 1.35): album spines, track titles, dialog copy, status text.
- **Label** (700, 10px, uppercase, 0.04em tracking): pane headers, legend captions, every button, section labels in dialogs.
- **Mono** (400, 9px, 1.3): track numbers, running-time slots, counts, the log sheet, the library path, scroll footers, dialog check-row hints.

### Named Rules
**The Caps Rule.** Anything that names a surface, a control or a category is condensed-grotesque uppercase. Anything that is data — a number, a timecode, a path, a log line — is mono. Prose stays in body case. Mixing these is the fastest way to look off-world.

**The Truncate Rule.** Long labels are cut with an ellipsis measured against the real font, never wrapped and never allowed to collide with the mark or the meta column. A row is one line, always.

## Layout

The window is a fixed 1180×800 grid with a 940×640 floor, stacked in five bands
tall and three columns wide.

Vertically: a **header strip** (54px) carrying the wordmark, the library path and
the folder/settings/about actions; a **3px progress rail** with a 1px rule beneath
it; the **crate body** (expanding, ≥420px) holding the three panes; a
**silkscreen action bar** (46px); the **legend** (one line of marks); the
**results sheet** (a fixed ~224px, deliberately not expanding); the **job log**
(collapsed by default, shown on demand); a 1px rule; and a **status strip** (30px).

The results sheet is fixed-height and the log is hidden behind a toggle. The
sheet answers "what happened to each track?" in one glance; the raw log is a
diagnostic record, not a work surface. Letting either expand would halve the
crate and invert the hierarchy.

Horizontally the crate body holds three panes: **Artists** 300px fixed,
**Albums** 330px fixed, **Tracks** fluid. Each pane is a 30px header (title,
count, an All/Clear toggle) over a 2px red rule over a recessed scroll area.
Every list reserves a 10px right rail for the scroll indicator and an 8px inner
gutter, so all three panes share one left text edge per row type.

Spacing runs on a five-step ramp (4 / 8 / 12 / 16 / 24). The rules are consistent
inside a band: 16px for window-edge gutters, 12px between bands, 8px between
sibling controls, 4px inside a control.

## Elevation & Depth

**There are no shadows.** None, anywhere, at any state — not on dialogs, not on
the pull-forward animation, not on the tooltip.

Depth is tonal and structural, and it is a fixed vocabulary of four steps, never
more: Crate Ground (#211F1D) is the world; Crate Recess (#191716) is one step
*down* and means "inside the crate" (list interiors); Panel (#2B2A28) is one step
*up* and means "raised board" (toolbars, headers, the status strip, the log);
Panel Raised (#343230) is the hover step on a dark row. Separations are made by
1px Edge (#3A3835) rules, never by shadow, never by a thicker line.

The one authored moment of depth is the **pull-forward**: a selected row is
drawn 7px further right than its neighbours, over three eased frames, so it
physically sits proud of the crate. That 7px shift is the only motion-driven
depth in the system.

### Named Rules
**The Flat-By-Default Rule.** Surfaces are flat at rest and flat when active. A shadow is always a bug; if a boundary is unclear, the answer is a 1px rule or a tonal step, never `box-shadow`.

## Shapes

**One radius: zero.** Every rectangle in the application — buttons, panes, rows,
entry fields, checkbox boxes, dialogs, the log sheet — has square corners. There
is no `corner_radius` in the codebase other than 0. Rounded corners would make
this a cards UI, and the world is a crate.

Beyond corners: dividers carry a 26px ink tab at their head; album spines carry a
5px coloured stripe at their left edge (a six-colour rotation of muted board
tones, so adjacent spines separate without competing with the state colours);
state marks are drawn geometry with a ~1.4px stroke; the log sheet is wrapped in
a 1px Edge border to read as a ruled sheet rather than a floating box.

### Named Rules
**The Hard-Edge Rule.** Radius is 0 everywhere. If a surface wants to feel soft, it has chosen the wrong world.

## Components

### Buttons
Two variants, both flat, both hard-edged, both uppercase label type.
- **Shape:** square (0px radius), 30px tall, 1px border on the secondary variant only.
- **Primary:** Silkscreen Tab Red fill, Kraft text, no border. One per surface — "Open music folder" in the header, "Download selection" in the action bar, "Save" / "Download with this query" in dialogs. **Hover:** Silkscreen Red Deep. **Disabled:** Crate Ground fill with Text Faint — a primary button that cannot act stops looking like an action.
- **Secondary:** Panel fill, Text, 1px Edge border. Hover steps to Panel Raised.
- **Ghost:** for pane-header toggles (All / Clear) — transparent, Text Dim, no border, Panel Raised on hover, 22px tall.

### Cards / Containers
There are no cards. The container vocabulary is the pane and the dialog.
- **Corner Style:** square (0px).
- **Pane:** a 30px Panel header over a 2px Silkscreen Tab Red rule over a Crate Recess interior. The red rule is the pane's identity — it is what makes three dark rectangles read as three crate bays.
- **Dialog:** a Crate Ground shell; a dialog title in Headline with a 48×2px red rule under it; content on the ground, never on a raised card; a footer of secondary-then-primary buttons right-aligned.

### Inputs / Fields
- **Style:** Panel fill, 1px Edge stroke, square corners, Body type, 34px tall in dialogs.
- **Focus:** the stroke holds; the caret is Text-coloured. No glow, no ring, no colour shift.
- **Checkboxes:** Silkscreen Tab Red fill when checked, Kraft checkmark, 1px Edge border, square box, Body-adjacent label in Text. A disabled checkbox keeps its geometry and drops to Text Faint.

### Navigation
There is no navigation bar. Movement through the library *is* the navigation, and it happens in the crate: pick a divider, pick a spine, read the tracklist. The three panes are the only structural navigation, and the legend below the action bar is the only key.

### Signature Components

**CrateList rows.** Three row types in one canvas-drawn list. *Divider*: a 32px kraft board with a 26px tab at its head — the tab is silkscreen red when selected, crate board when not — carrying the artist name in Title ink and, once scanned, a folder-state mark at its right edge. *Spine*: a 26px dark row with a 5px coloured stripe at its left edge and a state mark at its right. *Track*: a 24px row on recess, ruled by a 1px hairline, holding a mono track number, the title, a mono running-time slot, and a stamped state mark. Multi-select is native (click, Ctrl-click, Shift-range); arrow keys move, Ctrl+A selects all, and the pane header toggles All/Clear.

**State marks.** Drawn on canvas at 13px, never emoji and never a font glyph, so they render identically on every machine and can be inked for either material. Synced/complete is a circle with a check; plain is a square sheet with two rules; incomplete is a struck triangle; missing is a struck circle; partly complete is a half-filled circle. Each is a distinct silhouette, so the state survives greyscale and colour-blindness.

**Results sheet.** A read-only canvas sheet that replaces reading a scrolling log. One kraft header strip carries four column labels (TRACK / FOLDER / PROVIDER / RESULT) and does not scroll — rows pass underneath it, so the columns stay named no matter how long the job runs. Under it, one 24px ruled row per track: a drawn state mark, the title, the folder it lives in, the provider that answered (or the reason none did), and the state as a word in mono caps, right-aligned and coloured by the same token as its mark. Rows are seeded in job order before any lookup starts, so the whole worklist is visible from the first second and each row settles in place rather than appearing out of order. The sheet follows the work frontier as it descends, and stops following the moment the user takes the wheel.

**Result states.** The sheet needs states the library panes never show, so the mark family grows by exactly one silhouette. *Queued* and *skipped* reuse the struck circle, *failed* reuses it in Silkscreen Red Soft, *upgraded* reuses the synced check, and *kept* reuses the plain sheet. The state is carried by colour and the word, not by new geometry. *Working* is the one new shape: an open 285° ring, the only mark that is deliberately incomplete, because the track it describes is still in flight.

*Kept* exists because "we left your existing plain lyrics alone" is neither a write nor a failure. Counting it as a download would inflate the summary, so it is reported distinctly and excluded from both tallies.

**Silkscreen action bar.** A Panel band whose buttons are flat ink-press shapes. It holds the two flows side by side: *select → download*, and *scan missing → download missing*, with the scan button carrying a live `[n]` count once it has found something.

## Do's and Don'ts

### Do:
- **Do** keep to the two materials. Kraft for things you pick up; Crate Ground / Recess / Panel for everything structural.
- **Do** use the Two-Inks Rule when a mark lands on kraft — Filed Green Ink, Pending Amber Ink, Absent Grey Ink.
- **Do** pair every colour-coded state with its shape, so state survives greyscale.
- **Do** keep the silkscreen red under 3% of any screen. On the main window it is the two primary buttons, three 2px pane rules, the selected divider tab and its spine stripe.
- **Do** draw a hairline rather than add a shadow when two surfaces need separating.
- **Do** solve collisions by reserving the column: the mark sits at `x1 − meta_w − 6`, clear of both the meta text and the rail.
- **Do** measure condensed labels with the real font and truncate with an ellipsis.

### Don't:
- **Don't** add a shadow, glow, gradient or blur. There are none in the system, and one will make the whole crate look like a plastic admin panel.
- **Don't** round a corner. Radius is 0, including on checkbox boxes, entries and dialogs.
- **Don't** use emoji, icon fonts, or unicode glyphs as icons. State marks are drawn geometry.
- **Don't** use Crate Recess for a raised surface or Panel for a sunken one — the three dark tones have fixed meanings and swapping them flattens the depth vocabulary.
- **Don't** let the log sheet expand; it is a fixed strip and the crate owns the window.
- **Don't** use Silkscreen Tab Red for a large fill. A full-width red bar is the accent shouting over the content; kraft is the selection material, red is the tab.
