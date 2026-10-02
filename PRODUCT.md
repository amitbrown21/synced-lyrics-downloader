<!-- impeccable:product-schema 1 -->
# Product

## Platform

desktop

<!-- Native, cross-platform desktop application (Windows and Linux), built in Python on a Tk-derived GUI toolkit. It is not web, iOS, or Android; the enumerated platform values do not cover a native desktop GUI, so `desktop` is recorded explicitly so future work treats this as a native app rather than a browser surface. -->

## Stack

Existing codebase: Python 3.10+ on Tk 8.6/9.0. Lyrics are fetched through the `syncedlyrics` CLI/library. The redesign adds exactly one runtime dependency, `customtkinter`, as the modern widget layer; the entry point stays a runnable Python file (`python lyrics_downloader_ultimate.py`). Distribution is source-run; no packaged installer was confirmed.

## Users

Owners of local music libraries, primarily on Windows (also Linux), whose files are already organized in the standard three-level `Artist / Album / Track` layout produced by MusicBrainz Picard, beets, Mp3tag, and similar tools. They are comfortable enough to run a Python script and manage files, but they are not developers by trade. They often point the app at a large library on a network drive (NAS, mapped drive) and want lyrics fetched in bulk without a browser, an account, or an ad-supported web service.

<!-- Audience confirmed by the fork owner. Remaining details derived from README and code; treat as hypothesis until corrected. -->

## Product Purpose

Find and save synced (`.lrc`, timestamped) lyrics next to local music files, falling back to plain lyrics when synced versions do not exist. It exists so a person can fix a whole library's missing lyrics in a few clicks instead of visiting a lyrics website per track. Success means: point at a folder, scan what is missing, download, and trust the result is filed correctly beside each track.

## Positioning

A local-first, accountless desktop tool that is *library-aware*: it understands the `Artist/Album/Track` folder structure, can scan which tracks are missing lyrics, and resolves a track's artist from its path to build better search queries. The synced-first, multi-provider fallback chain (Lrclib, Musixmatch, Megalobiz, NetEase, Genius) with quality filtering is the mechanism a generic "paste a song name" service cannot copy.

## Operating Context

- Libraries are large (hundreds to thousands of tracks) and frequently on slow or network storage, so scanning must be cheap and results cached.
- The standard folder shape is fixed and load-bearing: `Music/Artist/Album/NN Track.ext` plus a sibling `.lrc`.
- Users already selected this library structure with another tool; the app must not fight it.
- Runs as a long-lived window beside a file manager; downloads happen in the background while the user keeps selecting work.

## Capabilities and Constraints

- Providers: Lrclib, Musixmatch, Megalobiz, NetEase, Genius; user-ordered priority, individually toggleable, Genius gated behind the plain-lyrics fallback.
- Synced-first: try timestamped lyrics first, then optional plain fallback; everything is saved as `.lrc` for maximum player compatibility.
- Selection model: artist → album → track, with multi-select and Select-All/Clear-All; scan for missing lyrics in a selection, then download only what is missing.
- Custom Search overrides the query for hard-to-find tracks (dedupe artist, strip punctuation).
- Quality filters: strip CJK lines, reject mostly-non-ASCII results, configurable language code.
- Auto-upgrade: detect plain `.lrc` files and offer to find a synced version (with "Yes to All").
- Remembers window geometry, theme, and all settings in `lyrics_gui_config.json` next to the script.
- Keyboard shortcuts: `Ctrl+D` download, `Escape` cancel, `F5` refresh, double-click a track for Custom Search.
- Constraint: results depend on third-party, sometimes-rate-limited providers; the app must stay responsive while working and cancel safely after the current track.
- Terminology to preserve in the UI: "synced", "plain", "incomplete", "missing", "provider priority", "auto-upgrade".

## Brand Commitments

- Name: "Synced Lyrics Downloader".
- Explicitly no accounts, no ads, no browser required. Local-only by default.
- License: MIT.
- Upstream project is `type0dev/synced-lyrics-downloader`; the fork lives at `amitbrown21/synced-lyrics-downloader`.

## Evidence on Hand

- `README.md` — full feature list, install, quick start, provider table, library-structure spec.
- `lyrics download screenshot.png` — the incumbent (pre-redesign) UI, useful only as an anti-reference.
- No testimonial, benchmark, pricing, or press material exists; none may be invented.

## Product Principles

1. **The library is the source of truth.** Read the folder structure; never ask the user to re-describe their own files.
2. **Synced beats plain, always.** Prefer timestamps; when only plain exists, be honest that it is plain and offer the upgrade.
3. **Bulk over one-at-a-time.** Optimize for fixing a whole selection, but keep single hard tracks tractable via Custom Search.
4. **Never block the window.** Scanning and downloading run in the background; cancel is always available and safe.
5. **Trust through transparency.** Show what provider produced what, keep a visible log, and make quality filters visible and reversible.

## Accessibility & Inclusion

- Fully keyboard-operable: every core action has a shortcut or a focusable control; selection and list navigation must not require a mouse.
- Visible focus states on interactive controls (a gap in the incumbent UI).
- Status, success, warning, and error must be conveyed by text/label, not color alone.
- Incumbent uses emoji as iconography; the redesign must not rely on emoji or color alone to carry meaning.
