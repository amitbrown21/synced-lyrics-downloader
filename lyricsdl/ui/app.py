"""The main window — the crate.

Three panes (artist dividers, album spines, the selected record's tracklist)
over a silkscreen action bar, a ruled job log and a status strip. All fetching
happens on a worker thread; everything it reports is marshalled onto the Tk
main thread through a queue, never touched directly.
"""

from __future__ import annotations

import os
import queue
import re
import threading
import tkinter as tk
import traceback

import customtkinter as ctk

from .. import config as app_config
from .. import library
from ..downloader import Reporter, download_targets, run_custom_query
from . import dialogs
from . import theme as T
from .widgets import (CratePane, ResultPane, Row, SPINE_COLORS, Tooltip,
                      reset_font_cache, silk_button)

LEVEL_WORD = {"info": "INFO", "step": "STEP", "ok": "OK", "warn": "WARN", "error": "ERR"}
STATUS_KIND = {"normal": T.TEXT, "working": T.FOCUS, "success": T.GREEN, "error": T.RED_SOFT}

_TRACK_NUM_RE = re.compile(r"^\s*(\d{1,3})\s*[\.\-_ ]\s*(.*)$")


def _index_letter(name: str) -> str:
    for ch in name:
        if ch.isalnum():
            return ch.upper()
    return "\u00b7"


def _split_track(base: str) -> tuple[str, str]:
    m = _TRACK_NUM_RE.match(base)
    if m:
        return m.group(1).zfill(2), (m.group(2) or base)
    return "", base


class _UiReporter(Reporter):
    """Marshals engine events onto the Tk main thread."""

    def __init__(self, app: "App"):
        self.app = app

    def log(self, msg: str, level: str = "info") -> None:
        self.app._post(self.app.append_log, msg, level)

    def status(self, text: str, kind: str = "normal") -> None:
        self.app._post(self.app.set_status, text, kind)

    def progress(self, done: int, total: int) -> None:
        self.app._post(self.app.set_progress, done, total)

    def track(self, path: str, state: str, detail: str = "") -> None:
        self.app._post(self.app.on_track, path, state, detail)

    def ask_upgrade(self, song_name: str, should_cancel) -> tuple[bool, bool]:
        return self.app._ask_upgrade_blocking(song_name, should_cancel)


class App:
    def __init__(self) -> None:
        ctk.set_appearance_mode("dark")
        self.root = ctk.CTk(fg_color=T.CRATE)
        self.root.title(app_config.APP_NAME)
        self.root.minsize(940, 640)
        T.init_fonts(self.root)
        reset_font_cache()   # a fresh root invalidates every cached Font

        self.music_dir: str = app_config.config.get("music_dir", "")
        self.missing_targets: list[str] = []
        self._downloading = False
        self._cancel = False
        self._ui_q: queue.Queue = queue.Queue()
        self._legend_marks: list[tk.Canvas] = []

        self._build()
        self._bind_keys()

        geo = app_config.config.get("window_geometry", "1180x800")
        try:
            self.root.geometry(geo)
        except Exception:
            self.root.geometry("1180x800")
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self.root.after(50, self._pump)
        if self.music_dir and os.path.isdir(self.music_dir):
            self.load_library()
        else:
            self.set_status("Ready. Open a music folder to begin.")

    # ------------------------------------------------------------------ build

    def _build(self) -> None:
        header = tk.Frame(self.root, bg=T.CRATE)
        header.pack(fill="x", padx=T.S.lg, pady=(T.S.md, T.S.sm))

        brand = tk.Frame(header, bg=T.CRATE)
        brand.pack(side="left")
        tk.Label(brand, text="SYNCED LYRICS", bg=T.CRATE, fg=T.TEXT,
                 font=T.display(17)).pack(side="left")
        tk.Frame(brand, bg=T.RED, width=9, height=9).pack(side="left", padx=T.S.sm, pady=(7, 0))
        tk.Label(brand, text="DOWNLOADER", bg=T.CRATE, fg=T.TEXT_DIM,
                 font=T.display(11)).pack(side="left", pady=(3, 0))

        self.path_lbl = tk.Label(header, text="NO FOLDER OPEN", bg=T.CRATE, fg=T.TEXT_FAINT,
                                 font=T.mono(9))
        self.path_lbl.pack(side="left", padx=(T.S.xl, 0))

        open_btn = silk_button(header, "Open music folder", self.choose_folder, primary=True, width=190)
        open_btn.pack(side="right")
        Tooltip(open_btn, "Choose the folder your Artist/Album/Track library lives in (F5 to rescan)")
        settings_btn = silk_button(header, "Settings", self.open_settings, width=110)
        settings_btn.pack(side="right", padx=(0, T.S.sm))
        Tooltip(settings_btn, "Provider priority, quality filters and language")
        about_btn = silk_button(header, "About", self.open_about, width=90)
        about_btn.pack(side="right", padx=(0, T.S.sm))
        Tooltip(about_btn, "How it works, requirements and keyboard shortcuts")

        self.rail = tk.Canvas(self.root, height=3, bg=T.CRATE, highlightthickness=0, bd=0)
        self.rail.pack(fill="x")
        self.rail.bind("<Configure>", lambda e: self._draw_progress())
        self._progress = 0.0

        tk.Frame(self.root, bg=T.PANEL_EDGE, height=1).pack(fill="x")

        body = tk.Frame(self.root, bg=T.CRATE)
        body.pack(fill="both", expand=True, padx=T.S.lg, pady=T.S.md)

        self.artist_pane = CratePane(body, title="Artists", on_select=self._on_artist_select,
                                     on_toggle_all=self._toggle_artists,
                                     empty_text="Open a music folder to load your crate.",
                                     footer_text="Completeness appears after scanning")
        self.artist_pane.configure(width=300)
        self.artist_pane.pack(side="left", fill="y")
        self.artist_pane.pack_propagate(False)

        self.album_pane = CratePane(body, title="Albums", on_select=self._on_album_select,
                                    on_toggle_all=self._toggle_albums,
                                    empty_text="Select an artist to see its albums.")
        self.album_pane.configure(width=330)
        self.album_pane.pack(side="left", fill="y", padx=(T.S.sm, 0))
        self.album_pane.pack_propagate(False)

        self.track_pane = CratePane(body, title="Tracks", on_select=self._on_track_select,
                                    on_activate=self._on_track_activate,
                                    on_toggle_all=self._toggle_tracks,
                                    empty_text="Select an album to see its tracklist.",
                                    footer_text="Double-click a track for custom search")
        self.track_pane.pack(side="left", fill="both", expand=True, padx=(T.S.sm, 0))

        # -- action bar ----------------------------------------------------
        bar = tk.Frame(self.root, bg=T.PANEL)
        bar.pack(fill="x")
        inner = tk.Frame(bar, bg=T.PANEL)
        inner.pack(fill="x", padx=T.S.lg, pady=T.S.sm)

        self.dl_btn = silk_button(inner, "Download selection", self.start_download, primary=True, width=200)
        self.dl_btn.pack(side="left")
        Tooltip(self.dl_btn, "Download lyrics for the current selection (Ctrl+D)")
        self.cancel_btn = silk_button(inner, "Cancel", self.request_cancel, width=100)
        self.cancel_btn.pack(side="left", padx=(T.S.sm, 0))
        self.cancel_btn.configure(state="disabled")
        Tooltip(self.cancel_btn, "Stop after the current track (Escape)")
        self.scan_btn = silk_button(inner, "Scan missing", self.scan_missing, width=170)
        self.scan_btn.pack(side="left", padx=(T.S.lg, 0))
        Tooltip(self.scan_btn, "Find tracks in the selection that have no lyrics at all")
        self.missing_btn = silk_button(inner, "Download missing", self.download_missing, width=180)
        self.missing_btn.pack(side="left", padx=(T.S.sm, 0))
        Tooltip(self.missing_btn, "Download only the tracks found by the missing scan")
        self.custom_btn = silk_button(inner, "Custom search", self.open_custom_search, width=150)
        self.custom_btn.pack(side="left", padx=(T.S.sm, 0))
        Tooltip(self.custom_btn, "Override the search query for one track")
        self.clear_btn = silk_button(inner, "Clear selection", self.clear_all_selections, width=160)
        self.clear_btn.pack(side="right")

        self._set_missing_buttons()

        # -- legend --------------------------------------------------------
        legend = tk.Frame(self.root, bg=T.CRATE)
        legend.pack(fill="x", padx=T.S.lg, pady=(0, T.S.sm))
        tk.Label(legend, text="TRACK", bg=T.CRATE, fg=T.TEXT_FAINT,
                 font=T.display(9)).pack(side="left", padx=(0, T.S.sm))
        for state, label in (("synced", "synced"), ("plain", "plain"),
                             ("incomplete", "incomplete"), ("none", "missing")):
            self._legend_mark(legend, state, label)
        tk.Label(legend, text="FOLDER", bg=T.CRATE, fg=T.TEXT_FAINT,
                 font=T.display(9)).pack(side="left", padx=(T.S.lg, T.S.sm))
        for state, label in (("all", "complete"), ("some", "partial"), ("none", "empty")):
            self._legend_mark(legend, state, label)

        # -- results sheet -------------------------------------------------
        # The clear answer to "what happened?": one row per track. The raw log
        # is still there, one click away, for when something goes wrong.
        self.result_pane = ResultPane(self.root, on_toggle_log=self.toggle_log,
                                      empty_text="Download a selection to see what "
                                                 "each track got.",
                                      height=196)
        self.result_pane.pack(fill="x", padx=T.S.lg, pady=(0, T.S.sm))

        self.log_wrap = tk.Frame(self.root, bg=T.CRATE)   # packed by toggle_log
        log_head = tk.Frame(self.log_wrap, bg=T.CRATE)
        log_head.pack(fill="x")
        tk.Label(log_head, text="JOB LOG", bg=T.CRATE, fg=T.TEXT_DIM,
                 font=T.display(10)).pack(side="left")
        self.log_meta = tk.Label(log_head, text="", bg=T.CRATE, fg=T.TEXT_FAINT, font=T.mono(9))
        self.log_meta.pack(side="right")

        log_body = tk.Frame(self.log_wrap, bg=T.PANEL_EDGE)
        log_body.pack(fill="both", expand=True, pady=(T.S.xs, 0))
        self.log_text = tk.Text(log_body, bg=T.PANEL, fg=T.TEXT_DIM, bd=0, highlightthickness=0,
                                font=T.mono(9), padx=T.S.md, pady=T.S.sm, wrap="word",
                                insertbackground=T.TEXT, height=6, state="disabled")
        self.log_text.pack(side="left", fill="both", expand=True, padx=1, pady=1)
        log_sb = ctk.CTkScrollbar(log_body, command=self.log_text.yview,
                                  fg_color=T.PANEL, button_color=T.mix(T.PANEL, T.STOCK, 0.22),
                                  button_hover_color=T.mix(T.PANEL, T.STOCK, 0.35),
                                  corner_radius=0, width=12)
        log_sb.pack(side="right", fill="y")
        self.log_text.configure(yscrollcommand=log_sb.set)
        for level, color in T.LOG_COLORS.items():
            self.log_text.tag_configure(level, foreground=color)
        self.log_text.tag_configure("body", foreground=T.TEXT_DIM)

        # -- status strip --------------------------------------------------
        tk.Frame(self.root, bg=T.PANEL_EDGE, height=1).pack(fill="x")
        status = tk.Frame(self.root, bg=T.PANEL)
        status.pack(fill="x")
        self.status_lbl = tk.Label(status, text="Ready.", bg=T.PANEL, fg=T.TEXT_DIM,
                                   anchor="w", font=T.ui(10), padx=T.S.md, pady=5)
        self.status_lbl.pack(side="left", fill="x", expand=True)
        self.counter_lbl = tk.Label(status, text="", bg=T.PANEL, fg=T.TEXT_FAINT,
                                    font=T.mono(9), padx=T.S.md)
        self.counter_lbl.pack(side="right")

    def _legend_mark(self, parent, state: str, label: str) -> None:
        from .widgets import StateMark, mark_color
        box = tk.Frame(parent, bg=T.CRATE)
        box.pack(side="left", padx=(0, T.S.md))
        StateMark(box, size=13, state=state).pack(side="left")
        tk.Label(box, text=label, bg=T.CRATE, fg=T.TEXT_DIM, font=T.ui(9)).pack(side="left", padx=(4, 0))

    def _bind_keys(self) -> None:
        self.root.bind("<F5>", lambda e: self.load_library() if self.music_dir else None)
        self.root.bind("<Escape>", lambda e: self.request_cancel() if self._downloading else None)
        self.root.bind("<Control-d>", lambda e: self.start_download())
        self.root.bind("<Control-D>", lambda e: self.start_download())

    # ------------------------------------------------------- ui-safe plumbing

    def _post(self, fn, *args) -> None:
        self._ui_q.put((fn, args))

    def _pump(self) -> None:
        while True:
            try:
                fn, args = self._ui_q.get_nowait()
            except queue.Empty:
                break
            try:
                fn(*args)
            except Exception as exc:  # never fail silently: the log is the only witness
                traceback.print_exc()
                self.append_log(f"UI error: {exc}", "error")
        self.root.after(50, self._pump)

    def _ask_upgrade_blocking(self, song_name: str, should_cancel) -> tuple[bool, bool]:
        done = threading.Event()
        box = {"upgrade": False, "all": False}

        def on_main():
            up, all_ = dialogs.ask_upgrade_synced(self.root, song_name)
            box["upgrade"], box["all"] = up, all_
            done.set()

        self._post(on_main)
        while not done.wait(0.1):
            if should_cancel():
                return False, False
        return box["upgrade"], box["all"]

    # ------------------------------------------------------------ status/log

    def set_status(self, text: str, kind: str = "normal") -> None:
        self.status_lbl.configure(text=text, fg=STATUS_KIND.get(kind, T.TEXT_DIM))

    def set_progress(self, done: int, total: int) -> None:
        self._progress = (done / total) if total else 0.0
        self.counter_lbl.configure(text=f"{done} / {total}" if total else "")
        self._draw_progress()

    def _draw_progress(self) -> None:
        c = self.rail
        c.delete("all")
        w = c.winfo_width()
        if w <= 1:
            return
        c.create_rectangle(0, 0, w, 3, outline="", fill=T.PANEL)
        if self._progress > 0:
            c.create_rectangle(0, 0, max(2, w * self._progress), 3, outline="", fill=T.RED)
        self.rail.update_idletasks()

    def append_log(self, msg: str, level: str = "info") -> None:
        text = self.log_text
        text.configure(state="normal")
        if int(text.index("end-1c").split(".")[0]) > 4000:
            text.delete("1.0", "500.0")
        text.insert("end", f"{LEVEL_WORD.get(level, 'INFO'):<5} ", (level,))
        text.insert("end", msg + "\n", ("body",))
        text.configure(state="disabled")
        text.see("end")
        self.log_meta.configure(text=f"{int(text.index('end-1c').split('.')[0])} lines")

    def clear_log(self) -> None:
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

    def toggle_log(self) -> None:
        show = not self.log_wrap.winfo_ismapped()
        if show:
            self.log_wrap.pack(fill="x", padx=T.S.lg, pady=(0, T.S.sm))
        else:
            self.log_wrap.pack_forget()
        self.result_pane.set_log_visible(show)

    # ------------------------------------------------------------- results

    def _seed_results(self, paths: list[str]) -> None:
        """Lay out every queued track up front, in job order.

        Seeding beats appending on completion: the whole worklist is visible
        from the first second, and rows settle in place instead of arriving in
        whatever order the pool happened to finish them.
        """
        rows = []
        for path in paths:
            base = os.path.splitext(os.path.basename(path))[0]
            index, title = _split_track(base)
            rows.append(Row(key=path, label=title, kind="result", state="queued",
                            index=index, meta=self._relative_folder(path)))
        self.result_pane.reset(rows)
        self.result_pane.set_summary("")

    def _relative_folder(self, path: str) -> str:
        try:
            rel = os.path.relpath(os.path.dirname(path), self.music_dir or "")
        except Exception:
            return ""
        return "" if rel == "." else rel

    def on_track(self, path: str, state: str, detail: str = "") -> None:
        """Apply one engine track event to the results sheet."""
        if not self.result_pane.has_row(path):
            base = os.path.splitext(os.path.basename(path))[0]
            index, title = _split_track(base)
            self.result_pane.add_row(Row(key=path, label=title, kind="result",
                                         index=index, meta=self._relative_folder(path)))
        self.result_pane.update_row(path, state=state, provider=detail)
        self._refresh_result_summary()

    def _refresh_result_summary(self) -> None:
        counts: dict[str, int] = {}
        for row in self.result_pane.list.rows:
            counts[row.state or "queued"] = counts.get(row.state or "queued", 0) + 1
        order = ("working", "queued", "synced", "upgraded", "plain",
                 "kept", "skipped", "failed", "cancelled")
        self.result_pane.set_summary(" · ".join(
            f"{counts[s]} {s}" for s in order if counts.get(s)))

    # -------------------------------------------------------------- library

    def choose_folder(self) -> None:
        from tkinter import filedialog
        folder = filedialog.askdirectory(title="Select Music Folder", initialdir=self.music_dir or None)
        if not folder:
            return
        self.music_dir = folder
        app_config.config["music_dir"] = folder
        app_config.config.save()
        self.load_library()

    def load_library(self) -> None:
        if not self.music_dir or not os.path.isdir(self.music_dir):
            return
        self.missing_targets = []
        self.missing_scan_artists = []
        self.clear_log()
        self._reload_artists()
        self.album_pane.set_rows([])
        self.track_pane.set_rows([])
        self.path_lbl.configure(text=self.music_dir.upper(), fg=T.TEXT_DIM)
        self.append_log(f"Library: {self.music_dir}")
        self.append_log(f"Config: {app_config.CONFIG_FILE}", "step")
        self.set_status(f"Loaded {len(self.artist_pane.list.rows)} artists")
        self._set_missing_buttons()

    def _reload_artists(self) -> None:
        rows = []
        for name in library.list_artists(self.music_dir):
            state = library.artist_completeness_state(os.path.join(self.music_dir, name), name)
            rows.append(Row(key=name, label=name, kind="divider", state=state,
                            index=_index_letter(name), mark=state is not None))
        self.artist_pane.set_rows(rows)

    def _selected_artists(self) -> list[str]:
        return self.artist_pane.list.selected_keys()

    def _on_artist_select(self) -> None:
        sel = self._selected_artists()
        self._update_toggle_labels()
        if len(sel) == 1:
            artist = sel[0]
            path = os.path.join(self.music_dir, artist)
            state = library.artist_completeness_state(path, artist)
            self.artist_pane.list.update_row(artist, state=state, mark=state is not None)
            self._reload_albums(artist)
        else:
            self.album_pane.set_rows([])
            self.track_pane.set_rows([])
            self.set_status(f"{len(sel)} artists selected" if sel else "No artist selected")
        self._set_missing_buttons()

    def _reload_albums(self, artist: str) -> None:
        artist_path = os.path.join(self.music_dir, artist)
        rows = []
        for name in library.list_albums(artist_path):
            album_path = os.path.join(artist_path, name)
            result = library.cached_completeness(album_path, "album")
            rows.append(Row(key=f"{artist}\x1f{name}", label=name, kind="spine",
                            state=library.completeness_state(result["have"], result["total"]),
                            mark=True, data={"artist": artist, "album": name, "path": album_path}))
        self.album_pane.set_rows(rows)
        if rows and not self.album_pane.list.selected_keys():
            self.album_pane.list.select_keys([rows[0].key])
        self._on_album_select()

    def _on_album_select(self) -> None:
        self._update_toggle_labels()
        self._rebuild_tracks()
        self._set_missing_buttons()

    def _rebuild_tracks(self) -> None:
        artists = self._selected_artists()
        if len(artists) != 1:
            self.track_pane.set_rows([])
            return
        artist = artists[0]
        albums = self.album_pane.list.selected_rows()
        if not albums:
            self.track_pane.set_rows([])
            return
        rows: list[Row] = []
        for album in albums:
            album_path = album.data["path"]
            multi = len(albums) > 1
            for path in library.find_audio_files(album_path):
                name = os.path.basename(path)
                base = os.path.splitext(name)[0]
                num, title = _split_track(base)
                state = library.track_state(path)
                lrc = library.lrc_path_for(path)
                if state in ("synced", "plain"):
                    meta = library.last_timestamp(lrc)
                else:
                    meta = os.path.splitext(name)[1].lstrip(".").upper()
                if multi:
                    rel = os.path.relpath(path, album_path)
                    title = os.path.splitext(rel)[0]
                    prefix = album.data["album"]
                    title = f"{prefix} / {title}"
                rows.append(Row(key=path, label=title, kind="track", state=state,
                                index=num, meta=meta, data={"artist": artist, "path": path}))
        self.track_pane.set_rows(rows)
        if rows:
            self.set_status(f"{artist} — {len(rows)} tracks")
        else:
            self.set_status(f"{artist} — album has no audio files")

    def _on_track_select(self) -> None:
        self._update_toggle_labels()
        self._set_missing_buttons()

    def _on_track_activate(self, index: int) -> None:
        self.open_custom_search()

    # ------------------------------------------------------------- selection

    def _update_toggle_labels(self) -> None:
        for pane in (self.artist_pane, self.album_pane, self.track_pane):
            lst = pane.list
            all_sel = bool(lst.rows) and len(lst.selected_keys()) == len(lst.rows)
            pane.set_toggle_label("Clear" if all_sel else "All")

    def _toggle_artists(self) -> None:
        lst = self.artist_pane.list
        if lst.rows and len(lst.selected_keys()) == len(lst.rows):
            lst.clear_selection()
        else:
            lst.select_all()
        self._on_artist_select()

    def _toggle_albums(self) -> None:
        lst = self.album_pane.list
        if lst.rows and len(lst.selected_keys()) == len(lst.rows):
            lst.clear_selection()
        else:
            lst.select_all()
        self._on_album_select()

    def _toggle_tracks(self) -> None:
        lst = self.track_pane.list
        if lst.rows and len(lst.selected_keys()) == len(lst.rows):
            lst.clear_selection()
        else:
            lst.select_all()
        self._update_toggle_labels()

    def clear_all_selections(self) -> None:
        self.artist_pane.list.clear_selection()
        self.album_pane.list.clear_selection()
        self.track_pane.list.clear_selection()
        self.missing_targets = []
        self._update_toggle_labels()
        self._set_missing_buttons()
        self.set_status("Selection cleared")

    def _set_missing_buttons(self) -> None:
        n = len(self.missing_targets)
        self.scan_btn.configure(text=f"SCAN MISSING [{n}]" if n else "SCAN MISSING")
        self.missing_btn.configure(state="normal" if n else "disabled")
        self.dl_btn.configure(state="normal")
        self.custom_btn.configure(state="normal")

    # ------------------------------------------------------------- collection

    def _collect_roots(self) -> list[str]:
        """Filesystem roots for the current selection (used by the missing scan)."""
        artists = self._selected_artists()
        roots: list[str] = []
        if len(artists) > 1:
            return [os.path.join(self.music_dir, a) for a in artists]
        if len(artists) == 1:
            artist = artists[0]
            tracks = [r.data["path"] for r in self.track_pane.list.selected_rows() if "path" in r.data]
            if tracks:
                return tracks
            albums = self.album_pane.list.selected_rows()
            if albums:
                return [a.data["path"] for a in albums]
            return [os.path.join(self.music_dir, artist)]
        return roots

    def _collect_targets(self) -> list[str]:
        artists = self._selected_artists()
        targets: list[str] = []
        if len(artists) > 1:
            for artist in artists:
                targets += library.find_audio_files(os.path.join(self.music_dir, artist))
        elif len(artists) == 1:
            artist = artists[0]
            tracks = [r.data["path"] for r in self.track_pane.list.selected_rows() if "path" in r.data]
            if tracks:
                targets = tracks
            else:
                albums = self.album_pane.list.selected_rows()
                if albums:
                    for album in albums:
                        targets += library.find_audio_files(album.data["path"])
                else:
                    targets = library.find_audio_files(os.path.join(self.music_dir, artist))
        return library.dedupe(targets)

    # ------------------------------------------------------------------- jobs

    def _start_job(self, worker) -> None:
        if self._downloading:
            return
        self._cancel = False
        self._set_busy(True)
        threading.Thread(target=worker, daemon=True).start()

    def _set_busy(self, busy: bool) -> None:
        self._downloading = busy
        for btn in (self.dl_btn, self.scan_btn, self.missing_btn, self.custom_btn):
            btn.configure(state="disabled" if busy else "normal")
        self.cancel_btn.configure(state="normal" if busy else "disabled")
        if not busy:
            self.missing_btn.configure(state="normal" if self.missing_targets else "disabled")
            self._update_toggle_labels()
        self._draw_progress()

    def request_cancel(self) -> None:
        if not self._downloading:
            return
        self._cancel = True
        self.set_status("Cancel requested — stopping after the current track", "working")
        self.append_log("Cancel requested.", "warn")

    # -- download selection ------------------------------------------------

    def start_download(self) -> None:
        if self._downloading:
            return
        targets = self._collect_targets()
        if not targets:
            dialogs.notify(self.root, "Nothing selected",
                           "Select an artist, album or track first.")
            return
        app_config.config["music_dir"] = self.music_dir
        app_config.config.save()
        self._start_job(lambda: self._job_download(targets, prompt_upgrades=True,
                                                   headline="Processing"))

    def _job_download(self, targets, *, prompt_upgrades: bool, headline: str) -> None:
        self._post(self._seed_results, list(targets))
        reporter = _UiReporter(self)
        summary = download_targets(targets, music_dir=self.music_dir, reporter=reporter,
                                   cancel=lambda: self._cancel, prompt_upgrades=prompt_upgrades,
                                   headline=headline)
        self._post(self._after_job, summary)

    def _after_job(self, summary) -> None:
        for artist in summary.artists:
            library.scanned_artists.add(artist)
            library.invalidate_artist_cache(os.path.join(self.music_dir, artist))
        self.missing_targets = []
        self._reload_artists()
        self._on_artist_select()
        self._set_busy(False)
        self._set_missing_buttons()
        self.set_progress(0, 0)

    # -- missing scan ------------------------------------------------------

    def scan_missing(self) -> None:
        if self._downloading:
            return
        roots = self._collect_roots()
        if not roots:
            dialogs.notify(self.root, "Scan missing", "Select an artist, album or track first.")
            return
        artists = self._selected_artists()

        def worker():
            found = library.find_missing(roots)
            self._post(self._after_scan, found, artists)

        self._start_job(worker)

    def _after_scan(self, found: list[str], artists: list[str]) -> None:
        self.missing_targets = found
        for artist in artists:
            library.scanned_artists.add(artist)
            library.invalidate_artist_cache(os.path.join(self.music_dir, artist))
        level = "ok" if found else "info"
        self.append_log(f"Missing scan: {len(found)} track(s) without lyrics", level)
        self.set_status(f"Missing: {len(found)} tracks without lyrics", "success" if found else "normal")
        self._reload_artists()
        self._on_artist_select()
        self._set_busy(False)
        self._set_missing_buttons()

    def download_missing(self) -> None:
        if self._downloading:
            return
        if not self.missing_targets:
            dialogs.notify(self.root, "Download missing",
                           "Run Scan missing first — nothing is queued.")
            return
        targets = list(self.missing_targets)
        self._start_job(lambda: self._job_download(targets, prompt_upgrades=False,
                                                   headline="Processing missing"))

    # -- custom search -----------------------------------------------------

    def open_custom_search(self) -> None:
        if self._downloading:
            return
        artists = self._selected_artists()
        tracks = self.track_pane.list.selected_rows()
        if len(artists) != 1 or len(tracks) != 1:
            dialogs.notify(self.root, "Custom search",
                           "Select exactly one artist and one track first.")
            return
        row = tracks[0]
        path = row.data.get("path", "")
        if not os.path.isfile(path):
            dialogs.notify(self.root, "Custom search", f"Could not find the track file:\n{path}")
            return
        album = ""
        albums = self.album_pane.list.selected_rows()
        if len(albums) == 1:
            album = albums[0].data["album"]
        title = library.normalize_title(os.path.splitext(os.path.basename(path))[0])
        dialogs.open_custom_search(
            self.root, artist=artists[0], album=album, title=title,
            on_submit=lambda query: self._job_custom(path, query),
        )

    def _job_custom(self, path: str, query: str) -> None:
        self._post(self._seed_results, [path])
        def worker():
            reporter = _UiReporter(self)
            summary = run_custom_query(path, query, reporter=reporter, cancel=lambda: self._cancel)
            self._post(self._after_job, summary)
        self._start_job(worker)

    # ---------------------------------------------------------------- extras

    def open_settings(self) -> None:
        if self._downloading:
            dialogs.notify(self.root, "Busy", "Wait for the current download to finish first.")
            return
        dialogs.open_options(self.root, on_saved=self.load_library)

    def open_about(self) -> None:
        dialogs.open_about(self.root)

    def _on_close(self) -> None:
        self._cancel = True
        try:
            app_config.config["window_geometry"] = self.root.geometry()
            app_config.config.save()
        except Exception:
            pass
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()
