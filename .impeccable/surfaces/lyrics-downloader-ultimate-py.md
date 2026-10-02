---
version: 1
slug: "lyrics-downloader-ultimate-py"
primary_target: "lyrics_downloader_ultimate.py"
related_targets: []
---

# Surface: Synced Lyrics Downloader — main application window

<!-- impeccable:surface-brief -->

## Scope and mode

The whole application window and its dialogs (Options, About, Custom Search, Plain-lyrics upgrade prompt). Mode: **Operate** — the visitor is completing a task (finding and filing lyrics for a local music library) and expression must never obscure the task, state, or familiar affordance.

## Audience, job, action, constraints

- Owner of a large local library, usually on Windows, frequently on a network drive.
- Job: point at a library, see what is missing, download lyrics in bulk, spot-check hard tracks.
- Action: select an artist → album → track, then download; or scan-then-download only what is missing.
- Content to preserve: provider priority, synced/plain/incomplete/missing states, the visible log, provider attribution, quality filters, keyboard shortcuts, window geometry.
- Constraints: stays responsive during background work; cancel is safe; no emoji-as-icon system; state must not be carried by colour alone; keyboard-operable.

## Chosen direction and memorable moment

**The Crate** (record-shop crate dividers), chosen from the direction round (seed `a6fdedb9`, candidate 1). Memorable moment: selecting an artist physically pulls its divider forward out of the crate and the albums behind it fan into record spines.

## Unresolved decisions

- Final font family depends on what is installed; a resolver picks the first available condensed grotesque and falls back to the platform sans.
- Whether the log sheet also becomes the queue view is parked; v1 keeps the log as a ruled record of the job.

## Direction contract

**THESIS.** A music library is a record crate; you flip dividers, pull a record forward, and read its tracklist. It refuses the category's sidebar-plus-dark-data-table arrangement.

**OWN-WORLD.** Kraft board (#E8E2D2) on a near-black crate ground (#2B2A28); tabbed dividers with silkscreen ink; exactly one saturated tab red (#C8452F) marks the pulled-forward selection, and a muted crate green (#5C6B52) marks filed/complete. Labels are condensed grotesque caps; tracklists are ruled rows. Strip all content and it still reads as a crate of tabbed records.

**STORY.** The user sees the library as a crate — artist dividers, album spines, the selected record's tracklist — each track stamped with its lyric state, and a ruled log sheet recording the job.

**FIRST VIEWPORT.** ~1180×800, three panes: a header strip with the wordmark, the library path and the folder/settings actions; left, a stack of artist dividers; middle, album spines behind the pulled-forward divider; right, the selected record's tracklist ruled with track number, title, running-time slot and a stamped state. Below, a silkscreen action bar, a ruled log sheet, and a one-line status strip.

**FORM.** Candidate 1 of my grounded list (record-shop crate dividers); seed key `a6fdedb9`.

**FINISH.** unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance.
