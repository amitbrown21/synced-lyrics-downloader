"""Crate-styled dialogs: Options, About, Custom Search, and the plain→synced
upgrade prompt, plus replacements for the stock messagebox.

All of these run on the Tk main thread. The worker thread reaches them through
``App._ask_on_main`` (see :mod:`lyricsdl.ui.app`), which blocks until the user
answers or the job is cancelled.
"""

from __future__ import annotations

import tkinter as tk
from typing import Callable

import customtkinter as ctk

from .. import config as app_config
from . import theme as T
from .widgets import Tooltip, silk_button


def center_on(win, root, w: int, h: int) -> None:
    win.update_idletasks()
    try:
        x = root.winfo_rootx() + (root.winfo_width() - w) // 2
        y = root.winfo_rooty() + (root.winfo_height() - h) // 2
    except Exception:
        x = y = 120
    win.geometry(f"{w}x{h}+{max(x, 40)}+{max(y, 40)}")


def _toplevel(root, title: str) -> ctk.CTkToplevel:
    win = ctk.CTkToplevel(root)
    win.title(title)
    win.configure(fg_color=T.CRATE)
    win.transient(root)
    win.resizable(False, False)
    return win


def _title_block(parent, title: str, subtitle: str = "") -> None:
    tk.Label(parent, text=title.upper(), bg=T.CRATE, fg=T.TEXT,
             font=T.display(15)).pack(anchor="w")
    tk.Frame(parent, bg=T.RED, height=2, width=48).pack(anchor="w", pady=(4, 0))
    if subtitle:
        tk.Label(parent, text=subtitle, bg=T.CRATE, fg=T.TEXT_DIM, font=T.ui(10),
                 justify="left", wraplength=460).pack(anchor="w", pady=(8, 0))


def notify(root, title: str, text: str) -> None:
    win = _toplevel(root, title)
    center_on(win, root, 460, 190)
    body = tk.Frame(win, bg=T.CRATE)
    body.pack(fill="both", expand=True, padx=T.S.lg, pady=T.S.lg)
    _title_block(body, title, text)
    row = tk.Frame(body, bg=T.CRATE)
    row.pack(side="bottom", fill="x", pady=(T.S.lg, 0))
    silk_button(row, "Close", win.destroy, primary=True, width=110).pack(side="right")
    win.after(30, lambda: (win.lift(), win.focus_force()))
    win.wait_window()


def ask_confirm(root, title: str, text: str, *, confirm: str = "Confirm", cancel: str = "Cancel") -> bool:
    win = _toplevel(root, title)
    center_on(win, root, 460, 200)
    result = {"ok": False}
    body = tk.Frame(win, bg=T.CRATE)
    body.pack(fill="both", expand=True, padx=T.S.lg, pady=T.S.lg)
    _title_block(body, title, text)
    row = tk.Frame(body, bg=T.CRATE)
    row.pack(side="bottom", fill="x", pady=(T.S.lg, 0))

    def ok():
        result["ok"] = True
        win.destroy()

    silk_button(row, cancel, win.destroy, width=110).pack(side="right")
    silk_button(row, confirm, ok, primary=True, width=140).pack(side="right", padx=(0, T.S.sm))
    win.after(30, lambda: (win.lift(), win.focus_force()))
    win.wait_window()
    return result["ok"]


def ask_upgrade_synced(root, song_name: str) -> tuple[bool, bool]:
    """Ask whether to search for a synced replacement. Returns (upgrade, all)."""
    win = _toplevel(root, "Plain lyrics found")
    center_on(win, root, 480, 230)
    result = {"upgrade": False, "all": False}
    body = tk.Frame(win, bg=T.CRATE)
    body.pack(fill="both", expand=True, padx=T.S.lg, pady=T.S.lg)
    _title_block(body, "Plain lyrics found",
                 f"{song_name}\n\nA plain .lrc already exists. Search for a synced version to replace it?")
    row = tk.Frame(body, bg=T.CRATE)
    row.pack(side="bottom", fill="x", pady=(T.S.lg, 0))

    def no():
        result["upgrade"] = False
        win.destroy()

    def yes():
        result["upgrade"] = True
        win.destroy()

    def yes_all():
        result["upgrade"] = True
        result["all"] = True
        win.destroy()

    win.protocol("WM_DELETE_WINDOW", no)
    silk_button(row, "No", no, width=90).pack(side="right")
    silk_button(row, "Yes to all", yes_all, width=120).pack(side="right", padx=(0, T.S.sm))
    silk_button(row, "Yes", yes, primary=True, width=90).pack(side="right", padx=(0, T.S.sm))
    win.after(30, lambda: (win.lift(), win.focus_force()))
    win.wait_window()
    return result["upgrade"], result["all"]


def open_about(root) -> None:
    import sys
    from .. import __version__

    win = _toplevel(root, "About")
    center_on(win, root, 620, 560)
    body = tk.Frame(win, bg=T.CRATE)
    body.pack(fill="both", expand=True, padx=T.S.lg, pady=T.S.lg)
    _title_block(body, app_config.APP_NAME,
                 f"Version {__version__} \u2014 downloads synced (.lrc) lyrics next to your "
                 "music files. No browser, no account, no ads.")

    text = tk.Text(body, bg=T.PANEL, fg=T.TEXT_DIM, bd=0, highlightthickness=0,
                   font=T.ui(10), padx=T.S.md, pady=T.S.md, wrap="word", height=15,
                   insertbackground=T.TEXT)
    text.pack(fill="both", expand=True, pady=(T.S.lg, T.S.md))
    if getattr(sys, "frozen", False):
        requirements = [
            "This is the standalone build.",
            "  \u2022 Nothing else to install: Python and the lyrics engine are bundled.",
            "  \u2022 Settings are saved next to this executable.",
        ]
    else:
        requirements = [
            "Requirements",
            "  Python 3.10+  \u2022  pip install syncedlyrics customtkinter",
            "  tkinter ships with standard Python on Windows and most Linux installs.",
        ]
    for line in [
        "How it works",
        "  \u2022 Select artists, albums or tracks, then click Download Selection.",
        "  \u2022 Synced lyrics are always tried first; plain is an optional fallback.",
        "  \u2022 Scan Missing finds tracks with no .lrc, then Download Missing fills them.",
        "  \u2022 Double-click a track (or press Custom Search) for a hard-to-find track.",
        "  \u2022 Cancel stops safely after the current track. F5 rescans, Ctrl+D downloads.",
        "",
        *requirements,
        "",
        "Keyboard",
        "  Ctrl+D  download selection      Escape  cancel job      F5  rescan library",
        "  Arrow keys move the selection   Ctrl+A  select all in the focused pane",
    ]:
        text.insert("end", line + "\n")
    text.configure(state="disabled")

    row = tk.Frame(body, bg=T.CRATE)
    row.pack(fill="x")
    from ..config import DEFAULT_GITHUB_URL, SYNCEDLYRICS_URL
    import webbrowser
    gh = silk_button(row, "Open GitHub", lambda: webbrowser.open(DEFAULT_GITHUB_URL), width=140)
    gh.pack(side="left")
    Tooltip(gh, "Open the upstream project on GitHub")
    sl = silk_button(row, "syncedlyrics", lambda: webbrowser.open(SYNCEDLYRICS_URL), width=140)
    sl.pack(side="left", padx=(T.S.sm, 0))
    Tooltip(sl, "The lyrics-fetching library on PyPI")
    silk_button(row, "Close", win.destroy, primary=True, width=110).pack(side="right")
    win.after(30, lambda: (win.lift(), win.focus_force()))
    win.wait_window()


def open_custom_search(root, *, artist: str, album: str, title: str, on_submit: Callable[[str], None]) -> None:
    """Query editor for one track. Calls *on_submit(query)* then closes."""
    win = _toplevel(root, "Custom search")
    center_on(win, root, 600, 340)
    body = tk.Frame(win, bg=T.CRATE)
    body.pack(fill="both", expand=True, padx=T.S.lg, pady=T.S.lg)

    default = f"{artist}: {album} - {title}".strip() if album else f"{artist}: {title}".strip()
    _title_block(body, "Custom search", "Override the search query used for this one track.")

    tk.Label(body, text="SEARCH QUERY", bg=T.CRATE, fg=T.TEXT_DIM,
             font=T.display(9)).pack(anchor="w", pady=(T.S.lg, T.S.xs))
    qvar = tk.StringVar(value=default)
    entry = ctk.CTkEntry(body, textvariable=qvar, fg_color=T.PANEL, text_color=T.TEXT,
                         border_color=T.PANEL_EDGE, border_width=1, corner_radius=0,
                         font=T.ui(12), height=34)
    entry.pack(fill="x")
    entry.focus_set()

    dedup_var = tk.BooleanVar(value=False)
    strip_var = tk.BooleanVar(value=False)

    def strip_punctuation(s: str) -> str:
        out = ""
        for ch in s:
            if ch in "-:" or ch.isalnum() or ch.isspace():
                out += ch
        return " ".join(out.split())

    def dedupe_artist(s: str) -> str:
        parts = s.split(" - ")
        cleaned, seen = [], False
        low = artist.lower()
        for part in parts:
            if part.strip().lower().startswith(low):
                after = part.strip().lower()[len(low):]
                if after == "" or after[0] in " :,":
                    if seen:
                        continue
                    seen = True
            cleaned.append(part.strip())
        return " - ".join(cleaned)

    def recompute(*_):
        q = default
        if dedup_var.get():
            q = dedupe_artist(q)
        if strip_var.get():
            q = strip_punctuation(q)
        qvar.set(q)

    checks = tk.Frame(body, bg=T.CRATE)
    checks.pack(fill="x", pady=(T.S.sm, 0))
    ctk.CTkCheckBox(checks, text="Remove duplicate artist name", variable=dedup_var,
                    command=recompute, fg_color=T.RED, hover_color=T.RED_DEEP,
                    border_color=T.PANEL_EDGE, checkmark_color=T.STOCK, corner_radius=0,
                    text_color=T.TEXT_DIM, font=T.ui(10)).pack(anchor="w")
    ctk.CTkCheckBox(checks, text="Strip punctuation (apostrophes, commas, …)", variable=strip_var,
                    command=recompute, fg_color=T.RED, hover_color=T.RED_DEEP,
                    border_color=T.PANEL_EDGE, checkmark_color=T.STOCK, corner_radius=0,
                    text_color=T.TEXT_DIM, font=T.ui(10)).pack(anchor="w", pady=(4, 0))
    tk.Label(body, text="Tip: remove (remix), (live), feat. and similar for better matches.",
             bg=T.CRATE, fg=T.TEXT_FAINT, font=T.ui(9)).pack(anchor="w", pady=(T.S.sm, 0))

    row = tk.Frame(body, bg=T.CRATE)
    row.pack(side="bottom", fill="x", pady=(T.S.lg, 0))

    def submit():
        query = qvar.get().strip()
        win.destroy()
        if query:
            on_submit(query)

    silk_button(row, "Cancel", win.destroy, width=110).pack(side="right")
    silk_button(row, "Download with this query", submit, primary=True, width=230).pack(side="right", padx=(0, T.S.sm))
    entry.bind("<Return>", lambda e: submit())
    win.after(30, lambda: (win.lift(), win.focus_force()))


def open_options(root, on_saved: Callable[[], None]) -> None:
    win = _toplevel(root, "Options")
    center_on(win, root, 880, 620)
    body = tk.Frame(win, bg=T.CRATE)
    body.pack(fill="both", expand=True, padx=T.S.lg, pady=T.S.lg)
    _title_block(body, "Options", "Provider priority, quality filters and language.")

    cols = tk.Frame(body, bg=T.CRATE)
    cols.pack(fill="both", expand=True, pady=(T.S.lg, 0))
    left = tk.Frame(cols, bg=T.CRATE)
    left.pack(side="left", fill="y")
    right = tk.Frame(cols, bg=T.CRATE)
    right.pack(side="left", fill="both", expand=True, padx=(T.S.xl, 0))

    tk.Label(left, text="PROVIDERS", bg=T.CRATE, fg=T.TEXT_DIM, font=T.display(10)).pack(anchor="w")
    plain_var = tk.BooleanVar(value=bool(app_config.config.get("allow_plain_fallback", False)))
    provider_vars: dict[str, tk.BooleanVar] = {}
    genius_cb = None

    def on_toggle_plain():
        if not plain_var.get():
            provider_vars["Genius"].set(False)
        render_priority()
        genius_cb.configure(state=("normal" if plain_var.get() else "disabled"))

    ctk.CTkCheckBox(left, text="Allow plain lyrics fallback", variable=plain_var,
                    command=on_toggle_plain, fg_color=T.RED, hover_color=T.RED_DEEP,
                    border_color=T.PANEL_EDGE, checkmark_color=T.STOCK, corner_radius=0,
                    text_color=T.TEXT, font=T.ui(10)).pack(anchor="w", pady=(T.S.sm, T.S.sm))

    for name in app_config.ALL_PROVIDERS:
        var = tk.BooleanVar(value=bool(app_config.config.get("providers_enabled", {}).get(name, True)))
        provider_vars[name] = var

        def toggle(pname=name):
            if pname == "Genius" and provider_vars["Genius"].get() and not plain_var.get():
                plain_var.set(True)
                genius_cb.configure(state="normal")
            render_priority()

        cb = ctk.CTkCheckBox(left, text=name, variable=var, command=toggle,
                             fg_color=T.RED, hover_color=T.RED_DEEP, border_color=T.PANEL_EDGE,
                             checkmark_color=T.STOCK, corner_radius=0, text_color=T.TEXT, font=T.ui(10))
        cb.pack(anchor="w", pady=2)
        if name == "Genius":
            genius_cb = cb
    if not plain_var.get():
        provider_vars["Genius"].set(False)
    genius_cb.configure(state=("normal" if plain_var.get() else "disabled"))

    upgrade_var = tk.BooleanVar(value=bool(app_config.config.get("upgrade_plain_to_synced", True)))
    ctk.CTkCheckBox(left, text="Offer to upgrade plain → synced", variable=upgrade_var,
                    fg_color=T.RED, hover_color=T.RED_DEEP, border_color=T.PANEL_EDGE,
                    checkmark_color=T.STOCK, corner_radius=0, text_color=T.TEXT,
                    font=T.ui(10)).pack(anchor="w", pady=(T.S.md, 0))
    auto_var = tk.BooleanVar(value=bool(app_config.config.get("auto_upgrade_plain", False)))
    ctk.CTkCheckBox(left, text="Upgrade without asking", variable=auto_var,
                    fg_color=T.RED, hover_color=T.RED_DEEP, border_color=T.PANEL_EDGE,
                    checkmark_color=T.STOCK, corner_radius=0, text_color=T.TEXT,
                    font=T.ui(10)).pack(anchor="w", pady=(4, 0))

    tk.Label(right, text="PRIORITY — TOP IS TRIED FIRST", bg=T.CRATE, fg=T.TEXT_DIM,
             font=T.display(10)).pack(anchor="w")
    order = list(app_config.config.get("providers_order", app_config.ALL_PROVIDERS))

    pri_wrap = tk.Frame(right, bg=T.CRATE)
    pri_wrap.pack(fill="both", expand=True, pady=(T.S.sm, 0))
    pri = tk.Listbox(pri_wrap, exportselection=False, bg=T.PANEL, fg=T.TEXT,
                     selectbackground=T.STOCK, selectforeground=T.INK, bd=0,
                     highlightthickness=1, highlightbackground=T.PANEL_EDGE,
                     highlightcolor=T.PANEL_EDGE, font=T.ui(11), activestyle="none")
    pri.pack(side="left", fill="both", expand=True)
    sb = ctk.CTkScrollbar(pri_wrap, command=pri.yview, fg_color=T.PANEL,
                          button_color=T.mix(T.PANEL, T.STOCK, 0.22),
                          button_hover_color=T.mix(T.PANEL, T.STOCK, 0.35),
                          corner_radius=0, width=12)
    pri.configure(yscrollcommand=sb.set)
    sb.pack(side="right", fill="y")

    def render_priority(select_index=None):
        pri.delete(0, tk.END)
        for name in order:
            enabled = bool(provider_vars[name].get())
            if name == "Genius" and not plain_var.get():
                enabled = False
            pri.insert(tk.END, f"{name}" + ("" if enabled else "   (off)"))
            pri.itemconfig(tk.END, foreground=(T.TEXT if enabled else T.TEXT_FAINT))
        if select_index is not None and 0 <= select_index < pri.size():
            pri.selection_set(select_index)
            pri.activate(select_index)

    def move(delta: int):
        sel = pri.curselection()
        if not sel:
            return
        i = sel[0]
        j = i + delta
        if not (0 <= j < len(order)):
            return
        order[i], order[j] = order[j], order[i]
        render_priority(j)

    btns = tk.Frame(right, bg=T.CRATE)
    btns.pack(fill="x", pady=(T.S.sm, 0))
    silk_button(btns, "Up", lambda: move(-1), width=80).pack(side="left")
    silk_button(btns, "Down", lambda: move(1), width=80).pack(side="left", padx=(T.S.sm, 0))
    render_priority(0 if order else None)

    quality = tk.Frame(body, bg=T.CRATE)
    quality.pack(fill="x", pady=(T.S.lg, 0))
    tk.Label(quality, text="LANGUAGE", bg=T.CRATE, fg=T.TEXT_DIM, font=T.display(9)).grid(row=0, column=0, sticky="w")
    lang_var = tk.StringVar(value=app_config.config.get("lang", "en"))
    ctk.CTkEntry(quality, textvariable=lang_var, width=70, fg_color=T.PANEL, text_color=T.TEXT,
                 border_color=T.PANEL_EDGE, border_width=1, corner_radius=0,
                 font=T.mono(11), height=28).grid(row=0, column=1, sticky="w", padx=(T.S.sm, T.S.sm))
    tk.Label(quality, text="en, es, fr … or blank for auto", bg=T.CRATE, fg=T.TEXT_FAINT,
             font=T.ui(9)).grid(row=0, column=2, sticky="w")

    strip_var = tk.BooleanVar(value=bool(app_config.config.get("strip_cjk", True)))
    ctk.CTkCheckBox(quality, text="Strip CJK lines from downloaded lyrics", variable=strip_var,
                    fg_color=T.RED, hover_color=T.RED_DEEP, border_color=T.PANEL_EDGE,
                    checkmark_color=T.STOCK, corner_radius=0, text_color=T.TEXT,
                    font=T.ui(10)).grid(row=1, column=0, columnspan=3, sticky="w", pady=(T.S.sm, 0))
    rej_var = tk.BooleanVar(value=bool(app_config.config.get("reject_non_ascii", True)))
    ctk.CTkCheckBox(quality, text="Reject lyric files that are mostly non-ASCII", variable=rej_var,
                    fg_color=T.RED, hover_color=T.RED_DEEP, border_color=T.PANEL_EDGE,
                    checkmark_color=T.STOCK, corner_radius=0, text_color=T.TEXT,
                    font=T.ui(10)).grid(row=2, column=0, columnspan=3, sticky="w", pady=(4, 0))
    tk.Label(quality, text="Reject threshold (0.05–0.50)", bg=T.CRATE, fg=T.TEXT_DIM,
             font=T.ui(9)).grid(row=3, column=0, sticky="w", pady=(T.S.sm, 0))
    ratio_var = tk.StringVar(value=str(app_config.config.get("reject_non_ascii_ratio", 0.15)))
    ctk.CTkEntry(quality, textvariable=ratio_var, width=70, fg_color=T.PANEL, text_color=T.TEXT,
                 border_color=T.PANEL_EDGE, border_width=1, corner_radius=0,
                 font=T.mono(11), height=28).grid(row=3, column=1, sticky="w", padx=(T.S.sm, T.S.sm), pady=(T.S.sm, 0))

    tk.Label(quality, text="PARALLEL LOOKUPS", bg=T.CRATE, fg=T.TEXT_DIM,
             font=T.display(9)).grid(row=4, column=0, sticky="w", pady=(T.S.md, 0))
    conc_var = tk.StringVar(value=str(app_config.config.get("concurrency", 4)))
    ctk.CTkEntry(quality, textvariable=conc_var, width=70, fg_color=T.PANEL, text_color=T.TEXT,
                 border_color=T.PANEL_EDGE, border_width=1, corner_radius=0,
                 font=T.mono(11), height=28).grid(row=4, column=1, sticky="w", padx=(T.S.sm, T.S.sm),
                                                  pady=(T.S.md, 0))
    tk.Label(quality, text="tracks fetched at once (1–16) — faster, but can trip rate limits",
             bg=T.CRATE, fg=T.TEXT_FAINT, font=T.ui(9)).grid(row=4, column=2, sticky="w",
                                                             pady=(T.S.md, 0))

    def on_save():
        fixed, seen = [], set()
        for name in order:
            if name in app_config.ALL_PROVIDERS and name not in seen:
                fixed.append(name)
                seen.add(name)
        for name in app_config.ALL_PROVIDERS:
            if name not in seen:
                fixed.append(name)
        try:
            ratio = max(0.05, min(0.50, float(ratio_var.get())))
        except Exception:
            ratio = 0.15
        try:
            concurrency = max(1, min(16, int(float(conc_var.get()))))
        except Exception:
            concurrency = 4
        plain = bool(plain_var.get())
        if not plain:
            provider_vars["Genius"].set(False)
        cfg = app_config.config
        cfg["allow_plain_fallback"] = plain
        cfg["upgrade_plain_to_synced"] = bool(upgrade_var.get())
        cfg["auto_upgrade_plain"] = bool(auto_var.get())
        cfg["providers_enabled"] = {p: bool(provider_vars[p].get()) for p in app_config.ALL_PROVIDERS}
        cfg["providers_order"] = fixed
        cfg["lang"] = lang_var.get()
        cfg["strip_cjk"] = bool(strip_var.get())
        cfg["reject_non_ascii"] = bool(rej_var.get())
        cfg["reject_non_ascii_ratio"] = ratio
        cfg["concurrency"] = concurrency
        cfg.save()
        win.destroy()
        on_saved()

    footer = tk.Frame(body, bg=T.CRATE)
    footer.pack(side="bottom", fill="x", pady=(T.S.md, 0))
    silk_button(footer, "Cancel", win.destroy, width=110).pack(side="right")
    silk_button(footer, "Save", on_save, primary=True, width=110).pack(side="right", padx=(0, T.S.sm))
    win.after(30, lambda: (win.lift(), win.focus_force()))
    win.wait_window()
