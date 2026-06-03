from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

try:
    import customtkinter as ctk
except Exception:  # pragma: no cover - optional visual upgrade.
    ctk = None

from i18n import Translator
from macro_recorder import MACRO_DIR, MacroRecorder, MacroSummary
from settings_store import load_settings, save_settings


COLORS = {
    "bg": "#070b16",
    "card": "#111c31",
    "card_2": "#1d3353",
    "text": "#edf6ff",
    "muted": "#99abc4",
    "accent": "#5eead4",
    "accent_2": "#8ab4ff",
    "good": "#62d7a4",
    "warn": "#ffd166",
    "danger": "#ff7a90",
    "soft": "#0e1a2d",
    "line": "#2d496f",
    "hover": "#172943",
    "accent_text": "#041014",
}


def parent_surface_color(parent, fallback: str) -> str:
    for option in ("fg_color", "bg"):
        try:
            value = parent.cget(option)
            if isinstance(value, tuple):
                return value[-1]
            if value:
                return str(value)
        except Exception:
            pass
    return fallback


def modern_frame(parent, color: str, radius: int = 18, border: int = 0, border_color: str | None = None):
    if ctk is not None:
        return ctk.CTkFrame(
            parent,
            fg_color=color,
            bg_color=parent_surface_color(parent, COLORS["bg"]),
            corner_radius=radius,
            border_width=border,
            border_color=border_color or color,
        )
    return tk.Frame(parent, bg=color, highlightthickness=border, highlightbackground=border_color or color)


def modern_button(parent, *, text: str, command, color: str, text_color: str, hover: str | None = None, height: int = 40):
    if ctk is not None:
        return ctk.CTkButton(
            parent,
            text=text,
            command=command,
            fg_color=color,
            bg_color=parent_surface_color(parent, COLORS["bg"]),
            hover_color=hover or COLORS["hover"],
            text_color=text_color,
            corner_radius=14,
            height=height,
            font=("Segoe UI", 10, "bold"),
        )
    return tk.Button(
        parent,
        text=text,
        command=command,
        bg=color,
        fg=text_color,
        activebackground=hover or COLORS["hover"],
        activeforeground=text_color,
        relief="flat",
        padx=16,
        pady=10,
        font=("Segoe UI", 10, "bold"),
        cursor="hand2",
    )


def modern_option_menu(parent, variable, values: list[str], width: int = 80):
    if ctk is not None:
        return ctk.CTkOptionMenu(
            parent,
            variable=variable,
            values=values,
            width=width,
            height=28,
            fg_color=COLORS["card_2"],
            button_color=COLORS["card_2"],
            button_hover_color=COLORS["hover"],
            dropdown_fg_color=COLORS["card"],
            dropdown_hover_color=COLORS["hover"],
            dropdown_text_color=COLORS["text"],
            text_color=COLORS["text"],
            font=("Segoe UI", 11, "bold"),
            dropdown_font=("Segoe UI", 11)
        )
    return ttk.Combobox(parent, textvariable=variable, values=values, state="readonly", width=width//10)


def modern_entry(parent, variable, width: int = 50):
    if ctk is not None:
        return ctk.CTkEntry(
            parent,
            textvariable=variable,
            width=width,
            height=28,
            fg_color=COLORS["soft"],
            border_color=COLORS["line"],
            text_color=COLORS["text"],
            font=("Segoe UI", 11, "bold"),
            justify="center"
        )
    return ttk.Entry(parent, textvariable=variable, width=width//10)


class TimeTaskOverlay:
    def __init__(self, parent: tk.Widget, translator: Translator, settings: dict | None = None) -> None:
        self.parent = parent
        self.tr = translator
        self.settings = settings or load_settings()
        self.start_callback = lambda: None
        self.pause_callback = lambda: None
        self.stop_callback = lambda: None
        self.save_callback = lambda: None
        self.window = ctk.CTkToplevel(parent) if ctk is not None else tk.Toplevel(parent)
        self.window.withdraw()
        self.window.overrideredirect(True)
        self.window.attributes("-topmost", True)
        try:
            self.window.attributes("-toolwindow", True)
        except tk.TclError:
            pass
        if ctk is not None:
            self.window.configure(fg_color="#060b14")
        else:
            self.window.configure(bg="#060b14")
        self.panel = modern_frame(self.window, "#111c31", radius=12, border=1, border_color=COLORS["accent"])
        self.panel.pack(fill="both", expand=True, padx=4, pady=4)
        self.title = tk.Label(self.panel, text="", bg="#111c31", fg=COLORS["accent"], font=("Segoe UI", 9, "bold"), padx=12, pady=4)
        self.title.pack(fill="x")
        self.detail = tk.Label(self.panel, text="", bg="#111c31", fg=COLORS["text"], font=("Segoe UI", 9, "bold"), padx=12, pady=2)
        self.detail.pack(fill="x")
        self.hint = tk.Label(self.panel, text="", bg="#111c31", fg=COLORS["muted"], font=("Segoe UI", 8), padx=12, pady=3)
        self.hint.pack(fill="x")
        actions = tk.Frame(self.panel, bg="#111c31")
        actions.pack(fill="x", padx=8, pady=(4, 8))
        self.start_button = tk.Button(actions, text=self.tr.t("timetask.start"), command=lambda: self.start_callback(), bg=COLORS["accent"], fg=COLORS["accent_text"], activebackground=COLORS["accent_2"], activeforeground=COLORS["accent_text"], relief="flat", font=("Segoe UI", 8, "bold"), cursor="hand2")
        self.start_button.grid(row=0, column=0, sticky="ew", padx=3)
        self.pause_button = tk.Button(actions, text=self.tr.t("timetask.pause"), command=lambda: self.pause_callback(), bg=COLORS["card_2"], fg=COLORS["text"], activebackground=COLORS["hover"], activeforeground=COLORS["text"], relief="flat", font=("Segoe UI", 8, "bold"), cursor="hand2")
        self.pause_button.grid(row=0, column=1, sticky="ew", padx=3)
        self.stop_button = tk.Button(actions, text=self.tr.t("timetask.stop"), command=lambda: self.stop_callback(), bg=COLORS["danger"], fg=COLORS["text"], activebackground="#b94a5d", activeforeground=COLORS["text"], relief="flat", font=("Segoe UI", 8, "bold"), cursor="hand2")
        self.stop_button.grid(row=0, column=2, sticky="ew", padx=3)
        self.save_button = tk.Button(actions, text=self.tr.t("timetask.save"), command=lambda: self.save_callback(), bg=COLORS["good"], fg=COLORS["accent_text"], activebackground=COLORS["accent"], activeforeground=COLORS["accent_text"], relief="flat", font=("Segoe UI", 8, "bold"), cursor="hand2")
        self.save_button.grid(row=0, column=3, sticky="ew", padx=3)
        self.close_button = tk.Button(actions, text="X", command=self.hide, bg=COLORS["card_2"], fg=COLORS["text"], activebackground=COLORS["hover"], activeforeground=COLORS["text"], relief="flat", font=("Segoe UI", 8, "bold"), cursor="hand2")
        self.close_button.grid(row=0, column=4, sticky="ew", padx=3)
        for column in range(5):
            actions.columnconfigure(column, weight=1)

        self._drag_x = 0
        self._drag_y = 0
        for widget in (self.panel, self.title, self.detail, self.hint, actions):
            widget.bind("<ButtonPress-1>", self.start_move)
            widget.bind("<B1-Motion>", self.on_move)
            widget.bind("<ButtonRelease-1>", self.stop_move)

        self.position()

    def start_move(self, event) -> None:
        self._drag_x = event.x_root - self.window.winfo_x()
        self._drag_y = event.y_root - self.window.winfo_y()

    def on_move(self, event) -> None:
        x = event.x_root - self._drag_x
        y = event.y_root - self._drag_y
        self.window.geometry(f"+{x}+{y}")

    def stop_move(self, event) -> None:
        if "time_task" not in self.settings:
            self.settings["time_task"] = {}
        self.settings["time_task"]["overlay_record_x"] = self.window.winfo_x()
        self.settings["time_task"]["overlay_record_y"] = self.window.winfo_y()
        save_settings(self.settings)

    def set_actions(self, start, pause, stop, save) -> None:
        self.start_callback = start
        self.pause_callback = pause
        self.stop_callback = stop
        self.save_callback = save

    def position(self) -> None:
        self.window.update_idletasks()
        width = 420
        height = 126
        time_task_config = self.settings.get("time_task", {})
        x = time_task_config.get("overlay_record_x")
        y = time_task_config.get("overlay_record_y")
        if x is None or y is None:
            x = max(12, self.window.winfo_screenwidth() - width - 24)
            y = 28
        self.window.geometry(f"{width}x{height}+{x}+{y}")

    def show(self, title: str, detail: str, hint: str, accent: str | None = None) -> None:
        was_hidden = self.window.state() == "withdrawn"
        self.title.configure(text=title, fg=accent or COLORS["accent"])
        self.detail.configure(text=detail)
        self.hint.configure(text=hint)
        if ctk is not None:
            self.panel.configure(border_color=accent or COLORS["accent"])
        else:
            self.panel.configure(highlightbackground=accent or COLORS["accent"])
        self.position()
        self.window.deiconify()
        if was_hidden:
            self.window.lift()

    def hide(self) -> None:
        self.window.withdraw()

    def refresh_language(self, translator: Translator) -> None:
        self.tr = translator
        self.start_button.configure(text=self.tr.t("timetask.start"))
        self.pause_button.configure(text=self.tr.t("timetask.pause"))
        self.stop_button.configure(text=self.tr.t("timetask.stop"))
        self.save_button.configure(text=self.tr.t("timetask.save"))

    def destroy(self) -> None:
        if self.window.winfo_exists():
            self.window.destroy()


class TimeTaskReplayOverlay:
    def __init__(self, parent: tk.Widget, translator: Translator, settings: dict | None = None) -> None:
        self.parent = parent
        self.tr = translator
        self.settings = settings or load_settings()
        self.play_callback = lambda: None
        self.pause_callback = lambda: None
        self.stop_callback = lambda: None
        self.window = ctk.CTkToplevel(parent) if ctk is not None else tk.Toplevel(parent)
        self.window.withdraw()
        self.window.overrideredirect(True)
        self.window.attributes("-topmost", True)
        try:
            self.window.attributes("-toolwindow", True)
        except tk.TclError:
            pass
        if ctk is not None:
            self.window.configure(fg_color="#060b14")
        else:
            self.window.configure(bg="#060b14")
        self.panel = modern_frame(self.window, "#111c31", radius=12, border=1, border_color=COLORS["good"])
        self.panel.pack(fill="both", expand=True, padx=4, pady=4)
        self.title = tk.Label(self.panel, text="", bg="#111c31", fg=COLORS["good"], font=("Segoe UI", 9, "bold"), padx=12, pady=4)
        self.title.pack(fill="x")
        self.detail = tk.Label(self.panel, text="", bg="#111c31", fg=COLORS["text"], font=("Segoe UI", 9, "bold"), padx=12, pady=2)
        self.detail.pack(fill="x")

        actions = tk.Frame(self.panel, bg="#111c31")
        actions.pack(fill="x", padx=8, pady=(6, 8))
        self.play_button = tk.Button(actions, text=self.tr.t("timetask.play"), command=lambda: self.play_callback(), bg=COLORS["good"], fg=COLORS["accent_text"], activebackground=COLORS["accent"], activeforeground=COLORS["accent_text"], relief="flat", font=("Segoe UI", 8, "bold"), cursor="hand2")
        self.play_button.grid(row=0, column=0, sticky="ew", padx=3)
        self.pause_button = tk.Button(actions, text=self.tr.t("timetask.pause"), command=lambda: self.pause_callback(), bg=COLORS["card_2"], fg=COLORS["text"], activebackground=COLORS["hover"], activeforeground=COLORS["text"], relief="flat", font=("Segoe UI", 8, "bold"), cursor="hand2")
        self.pause_button.grid(row=0, column=1, sticky="ew", padx=3)
        self.stop_button = tk.Button(actions, text=self.tr.t("timetask.stop"), command=lambda: self.stop_callback(), bg=COLORS["danger"], fg=COLORS["text"], activebackground="#b94a5d", activeforeground=COLORS["text"], relief="flat", font=("Segoe UI", 8, "bold"), cursor="hand2")
        self.stop_button.grid(row=0, column=2, sticky="ew", padx=3)
        self.close_button = tk.Button(actions, text="X", command=self.hide, bg=COLORS["card_2"], fg=COLORS["text"], activebackground=COLORS["hover"], activeforeground=COLORS["text"], relief="flat", font=("Segoe UI", 8, "bold"), cursor="hand2")
        self.close_button.grid(row=0, column=3, sticky="ew", padx=3)
        for column in range(4):
            actions.columnconfigure(column, weight=1)

        self._drag_x = 0
        self._drag_y = 0
        for widget in (self.panel, self.title, self.detail, actions):
            widget.bind("<ButtonPress-1>", self.start_move)
            widget.bind("<B1-Motion>", self.on_move)
            widget.bind("<ButtonRelease-1>", self.stop_move)

        self.position()

    def start_move(self, event) -> None:
        self._drag_x = event.x_root - self.window.winfo_x()
        self._drag_y = event.y_root - self.window.winfo_y()

    def on_move(self, event) -> None:
        x = event.x_root - self._drag_x
        y = event.y_root - self._drag_y
        self.window.geometry(f"+{x}+{y}")

    def stop_move(self, event) -> None:
        if "time_task" not in self.settings:
            self.settings["time_task"] = {}
        self.settings["time_task"]["overlay_replay_x"] = self.window.winfo_x()
        self.settings["time_task"]["overlay_replay_y"] = self.window.winfo_y()
        save_settings(self.settings)

    def set_actions(self, play, pause, stop) -> None:
        self.play_callback = play
        self.pause_callback = pause
        self.stop_callback = stop

    def position(self) -> None:
        self.window.update_idletasks()
        width = 360
        height = 104
        time_task_config = self.settings.get("time_task", {})
        x = time_task_config.get("overlay_replay_x")
        y = time_task_config.get("overlay_replay_y")
        if x is None or y is None:
            x = max(12, self.window.winfo_screenwidth() - width - 24)
            y = 170
        self.window.geometry(f"{width}x{height}+{x}+{y}")

    def show(self, title: str, detail: str, accent: str | None = None) -> None:
        was_hidden = self.window.state() == "withdrawn"
        self.title.configure(text=title, fg=accent or COLORS["good"])
        self.detail.configure(text=detail)
        if ctk is not None:
            self.panel.configure(border_color=accent or COLORS["good"])
        else:
            self.panel.configure(highlightbackground=accent or COLORS["good"])
        self.position()
        self.window.deiconify()
        if was_hidden:
            self.window.lift()

    def hide(self) -> None:
        self.window.withdraw()

    def refresh_language(self, translator: Translator) -> None:
        self.tr = translator
        self.play_button.configure(text=self.tr.t("timetask.play"))
        self.pause_button.configure(text=self.tr.t("timetask.pause"))
        self.stop_button.configure(text=self.tr.t("timetask.stop"))

    def destroy(self) -> None:
        if self.window.winfo_exists():
            self.window.destroy()


class TimeTaskCategory(ttk.Frame):
    def __init__(self, parent: ttk.Widget, translator: Translator | None = None) -> None:
        super().__init__(parent, style="Panel.TFrame")
        self.tr = translator or Translator()
        self.settings = load_settings()
        self.recorder = MacroRecorder(self.on_recorder_status)
        self.overlay = TimeTaskOverlay(self, self.tr, self.settings)
        self.overlay.set_actions(self.begin_countdown_recording, self.pause_toggle, self.stop_only, self.save_current)
        self.replay_overlay = TimeTaskReplayOverlay(self, self.tr, self.settings)
        self.replay_overlay.set_actions(self.play_selected, self.pause_toggle, self.stop_replay)
        self.status_var = tk.StringVar(value=self.tr.t("timetask.status_idle"))
        self.metric_var = tk.StringVar(value=self.tr.t("timetask.metric_empty"))
        self.macro_name_var = tk.StringVar(value="macro")
        self.speed_var = tk.StringVar(value="1.0")
        self.repeat_var = tk.StringVar(value="1")
        self.delay_var = tk.StringVar(value="0s")
        self.stock_macro_var = tk.StringVar(value=self.tr.t("timetask.none"))
        self.stock_interval_var = tk.StringVar(value="1")
        self.selected_path: Path | None = None
        self.summaries: list[MacroSummary] = []
        self.ui_text: dict[str, tk.Widget] = {}
        self.active = False
        self.countdown_job: str | None = None
        self.countdown_value = 0
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.build()
        self.refresh_macro_list()
        self.poll_state()

    def build(self) -> None:
        outer = modern_frame(self, COLORS["bg"], radius=0)
        outer.grid(row=0, column=0, sticky="nsew")
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(0, weight=1)

        canvas = tk.Canvas(outer, bg=COLORS["bg"], highlightthickness=0)
        canvas.grid(row=0, column=0, sticky="nsew")
        if ctk is not None:
            scrollbar = ctk.CTkScrollbar(outer, orientation="vertical", command=canvas.yview, width=10, fg_color=COLORS["bg"], button_color=COLORS["card_2"], button_hover_color=COLORS["accent"])
        else:
            scrollbar = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview, style="Vertical.TScrollbar")
        scrollbar.grid(row=0, column=1, sticky="ns")
        canvas.configure(yscrollcommand=scrollbar.set)

        container = modern_frame(canvas, COLORS["bg"], radius=0)
        window_id = canvas.create_window((0, 0), window=container, anchor="nw")
        container.bind("<Configure>", lambda _event: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda event: canvas.itemconfigure(window_id, width=event.width))
        container.columnconfigure(0, weight=1)

        self.ui_text["title"] = tk.Label(container, text=self.tr.t("timetask.title"), bg=COLORS["bg"], fg=COLORS["text"], font=("Segoe UI", 24, "bold"))
        self.ui_text["title"].grid(row=0, column=0, sticky="w", padx=22, pady=(20, 2))
        self.ui_text["subtitle"] = tk.Label(container, text=self.tr.t("timetask.subtitle"), bg=COLORS["bg"], fg=COLORS["accent_2"], font=("Segoe UI", 11, "bold"))
        self.ui_text["subtitle"].grid(row=1, column=0, sticky="w", padx=22, pady=(0, 16))

        record_card = modern_frame(container, COLORS["card"], radius=20, border=1, border_color=COLORS["line"])
        record_card.grid(row=2, column=0, sticky="ew", padx=22, pady=(0, 14))
        record_card.columnconfigure(0, weight=1)
        self.ui_text["record_title"] = tk.Label(record_card, text=self.tr.t("timetask.record_title"), bg=COLORS["card"], fg=COLORS["text"], font=("Segoe UI", 18, "bold"))
        self.ui_text["record_title"].grid(row=0, column=0, columnspan=6, sticky="w", padx=20, pady=(18, 4))
        self.ui_text["warning"] = tk.Label(record_card, text=self.tr.t("timetask.warning"), bg=COLORS["card"], fg=COLORS["warn"], font=("Segoe UI", 10, "bold"), wraplength=840, justify="left")
        self.ui_text["warning"].grid(row=1, column=0, columnspan=6, sticky="w", padx=20, pady=(0, 14))

        self.ui_text["status_label"] = tk.Label(record_card, text=self.tr.t("timetask.status"), bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI", 9, "bold"))
        self.ui_text["status_label"].grid(row=2, column=0, sticky="w", padx=20, pady=(0, 4))
        tk.Label(record_card, textvariable=self.status_var, bg=COLORS["card"], fg=COLORS["text"], font=("Segoe UI", 13, "bold")).grid(row=3, column=0, columnspan=6, sticky="w", padx=20, pady=(0, 14))

        modern_button(record_card, text=self.tr.t("timetask.open_record_overlay"), command=self.show_record_overlay, color=COLORS["accent"], text_color=COLORS["accent_text"], height=46).grid(row=4, column=0, columnspan=6, sticky="ew", padx=20, pady=(0, 8))
        tk.Label(record_card, textvariable=self.metric_var, bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI", 9)).grid(row=5, column=0, columnspan=6, sticky="w", padx=20, pady=(0, 18))

        replay_card = modern_frame(container, COLORS["card"], radius=20, border=1, border_color=COLORS["line"])
        replay_card.grid(row=3, column=0, sticky="ew", padx=22, pady=(0, 16))
        replay_card.columnconfigure(0, weight=1)
        self.ui_text["replay_title"] = tk.Label(replay_card, text=self.tr.t("timetask.replay_title"), bg=COLORS["card"], fg=COLORS["text"], font=("Segoe UI", 18, "bold"))
        self.ui_text["replay_title"].grid(row=0, column=0, columnspan=6, sticky="w", padx=20, pady=(18, 10))

        self.macro_list = tk.Listbox(replay_card, bg=COLORS["soft"], fg=COLORS["text"], selectbackground=COLORS["card_2"], selectforeground=COLORS["text"], highlightthickness=1, highlightbackground=COLORS["line"], relief="flat", height=8, font=("Segoe UI", 10))
        self.macro_list.grid(row=1, column=0, columnspan=7, sticky="ew", padx=20, pady=(0, 12))
        self.macro_list.bind("<<ListboxSelect>>", self.on_select_macro)

        self.ui_text["speed_label"] = tk.Label(replay_card, text=self.tr.t("timetask.speed"), bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI", 9, "bold"))
        self.ui_text["speed_label"].grid(row=2, column=0, sticky="w", padx=20, pady=(0, 8))
        modern_option_menu(replay_card, variable=self.speed_var, values=["0.5", "1.0", "1.5", "2.0"], width=70).grid(row=2, column=1, sticky="w", padx=(0, 16), pady=(0, 8))
        
        self.ui_text["repeat_label"] = tk.Label(replay_card, text=self.tr.t("timetask.repeat"), bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI", 9, "bold"))
        self.ui_text["repeat_label"].grid(row=2, column=2, sticky="w", padx=(0, 8), pady=(0, 8))
        modern_entry(replay_card, variable=self.repeat_var, width=50).grid(row=2, column=3, sticky="w", padx=(0, 16), pady=(0, 8))
        
        modern_button(replay_card, text=self.tr.t("timetask.play"), command=self.play_selected, color=COLORS["good"], text_color=COLORS["accent_text"]).grid(row=2, column=4, sticky="ew", padx=(0, 8), pady=(0, 8))
        modern_button(replay_card, text=self.tr.t("timetask.cancel"), command=self.stop_replay, color=COLORS["danger"], text_color=COLORS["text"]).grid(row=2, column=5, sticky="ew", padx=(0, 8), pady=(0, 8))
        modern_button(replay_card, text=self.tr.t("timetask.delete"), command=self.delete_selected_macro, color=COLORS["card_2"], text_color=COLORS["text"]).grid(row=2, column=6, sticky="ew", padx=(0, 20), pady=(0, 8))

        self.ui_text["delay_label"] = tk.Label(replay_card, text=self.tr.t("timetask.delay"), bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI", 9, "bold"))
        self.ui_text["delay_label"].grid(row=3, column=0, sticky="w", padx=20, pady=(0, 12))
        modern_option_menu(replay_card, variable=self.delay_var, values=["0s", "0.5s", "1s", "2s", "5s", "10s", "1 min", "2 min", "5 min"], width=70).grid(row=3, column=1, sticky="w", padx=(0, 16), pady=(0, 12))
        
        self.ui_text["repeat_hint"] = tk.Label(replay_card, text=self.tr.t("timetask.repeat_hint"), bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI", 8))
        self.ui_text["repeat_hint"].grid(row=3, column=2, columnspan=2, sticky="w", padx=8, pady=(0, 12))

        self.ui_text["stock_macro_label"] = tk.Label(replay_card, text=self.tr.t("timetask.stock_macro"), bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI", 9, "bold"))
        self.ui_text["stock_macro_label"].grid(row=4, column=0, sticky="w", padx=20, pady=(0, 12))
        self.stock_macro_combobox = modern_option_menu(replay_card, variable=self.stock_macro_var, values=[self.tr.t("timetask.none")], width=100)
        self.stock_macro_combobox.grid(row=4, column=1, columnspan=2, sticky="w", padx=(0, 16), pady=(0, 12))

        self.ui_text["stock_interval_label"] = tk.Label(replay_card, text=self.tr.t("timetask.stock_interval"), bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI", 8, "bold"))
        self.ui_text["stock_interval_label"].grid(row=4, column=3, sticky="w", padx=(0, 8), pady=(0, 12))
        modern_entry(replay_card, variable=self.stock_interval_var, width=50).grid(row=4, column=4, sticky="w", padx=(0, 16), pady=(0, 12))

        self.ui_text["folder"] = tk.Label(replay_card, text=self.tr.t("timetask.folder", path=str(MACRO_DIR)), bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI", 8), wraplength=860, justify="left")
        self.ui_text["folder"].grid(row=5, column=0, columnspan=7, sticky="w", padx=20, pady=(0, 18))
        self.bind_mousewheel_recursive(outer, canvas)

    def bind_mousewheel_recursive(self, widget: tk.Widget, canvas: tk.Canvas) -> None:
        def on_mousewheel(event) -> str:
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            return "break"
        widget.bind("<MouseWheel>", on_mousewheel, add="+")
        for child in widget.winfo_children():
            self.bind_mousewheel_recursive(child, canvas)

    def show_record_overlay(self) -> None:
        self.cancel_countdown()
        self.replay_overlay.hide()
        self.overlay.show(self.tr.t("timetask.overlay_ready"), self.tr.t("timetask.overlay_record_options"), self.tr.t("timetask.overlay_focus_hint"), COLORS["accent"])

    def begin_countdown_recording(self) -> None:
        if self.recorder.recording:
            self.recorder.resume_recording()
            return
        self.replay_overlay.hide()
        self.countdown_value = 3
        self.run_countdown_tick()

    def run_countdown_tick(self) -> None:
        if self.countdown_value <= 0:
            self.countdown_job = None
            self.recorder.start_recording()
            self.overlay.show(self.tr.t("timetask.overlay_recording"), self.tr.t("timetask.overlay_armed"), self.tr.t("timetask.overlay_focus_hint"), COLORS["warn"])
            return
        self.overlay.show(self.tr.t("timetask.overlay_countdown_title"), str(self.countdown_value), self.tr.t("timetask.overlay_countdown_hint"), COLORS["warn"])
        self.countdown_value -= 1
        self.countdown_job = self.after(1000, self.run_countdown_tick)

    def cancel_countdown(self) -> None:
        if self.countdown_job:
            try:
                self.after_cancel(self.countdown_job)
            except tk.TclError:
                pass
        self.countdown_job = None
        self.countdown_value = 0

    def stop_and_save(self) -> None:
        self.cancel_countdown()
        events = self.recorder.stop_recording()
        if not events:
            self.status_var.set(self.tr.t("timetask.no_events"))
            self.overlay.hide()
            return
        path = self.recorder.save_macro(self.macro_name_var.get())
        self.status_var.set(self.tr.t("timetask.saved", path=str(path)))
        self.refresh_macro_list(select_path=path)
        self.overlay.hide()
        self.show_replay_overlay()

    def pause_toggle(self) -> None:
        if self.recorder.recording:
            if self.recorder.paused:
                self.recorder.resume_recording()
            else:
                self.recorder.pause_recording()
        elif self.recorder.replaying:
            if self.recorder.replay_paused:
                self.recorder.resume_replay()
            else:
                self.recorder.pause_replay()

    def stop_only(self) -> None:
        self.cancel_countdown()
        if self.recorder.recording:
            events = self.recorder.stop_recording()
            self.overlay.hide()
            self.ask_save_after_stop(events)
            self.show_replay_overlay()
            return
        self.recorder.stop_replay()
        self.status_var.set(self.tr.t("timetask.stopped"))
        self.overlay.hide()
        self.show_replay_overlay()

    def save_current(self) -> None:
        self.cancel_countdown()
        if self.recorder.recording:
            self.recorder.stop_recording()
        events = self.recorder.snapshot_events()
        if not events:
            self.status_var.set(self.tr.t("timetask.no_events"))
            self.overlay.hide()
            return
        path = self.recorder.save_macro(self.macro_name_var.get())
        self.status_var.set(self.tr.t("timetask.saved", path=str(path)))
        self.refresh_macro_list(select_path=path)
        self.overlay.hide()
        self.show_replay_overlay()

    def ask_save_after_stop(self, events: list[dict]) -> None:
        if not events:
            self.status_var.set(self.tr.t("timetask.no_events"))
            return
        should_save = messagebox.askyesno(self.tr.t("timetask.save_question_title"), self.tr.t("timetask.save_question_body"), parent=self.winfo_toplevel())
        if not should_save:
            self.status_var.set(self.tr.t("timetask.stopped"))
            return
        default_name = self.macro_name_var.get() or "macro"
        name = simpledialog.askstring(self.tr.t("timetask.name"), self.tr.t("timetask.name_prompt"), initialvalue=default_name, parent=self.winfo_toplevel())
        if name:
            self.macro_name_var.set(name)
        path = self.recorder.save_macro(self.macro_name_var.get())
        self.status_var.set(self.tr.t("timetask.saved", path=str(path)))
        self.refresh_macro_list(select_path=path)

    def play_selected(self) -> None:
        if not self.selected_path:
            self.refresh_macro_list()
            if self.summaries:
                self.selected_path = self.summaries[0].path
            else:
                messagebox.showinfo(self.tr.t("timetask.title"), self.tr.t("timetask.pick_macro"), parent=self.winfo_toplevel())
                self.show_replay_overlay(self.tr.t("timetask.pick_macro"))
                return
        try:
            speed = float(self.speed_var.get())
            repeat = int(self.repeat_var.get())
            
            delay_str = self.delay_var.get().strip().lower()
            if "min" in delay_str:
                delay = float(delay_str.replace("min", "").replace("s", "").strip()) * 60
            else:
                delay = float(delay_str.replace("s", "").strip())
                
            stock_macro_name = self.stock_macro_var.get()
            stock_path = None
            if stock_macro_name != self.tr.t("timetask.none"):
                for summary in self.summaries:
                    if summary.name == stock_macro_name:
                        stock_path = summary.path
                        break
            stock_interval = int(self.stock_interval_var.get())
            
        except ValueError:
            speed = 1.0
            repeat = 1
            delay = 0.0
            stock_path = None
            stock_interval = 1
            
        self.overlay.hide()
        self.replay_overlay.show(self.tr.t("timetask.overlay_playing"), self.selected_path.stem, COLORS["good"])
        started = self.recorder.replay_macro(self.selected_path, speed=speed, repeat=repeat, delay_between=delay, stock_path=stock_path, stock_interval=stock_interval)
        if started:
            self.status_var.set(self.tr.t("timetask.overlay_playing"))
        else:
            self.show_replay_overlay(self.tr.t("timetask.replay_need_foxhole"))

    def stop_replay(self) -> None:
        self.recorder.stop_replay()
        self.show_replay_overlay()

    def delete_selected_macro(self) -> None:
        if not self.selected_path:
            messagebox.showinfo(self.tr.t("timetask.title"), self.tr.t("timetask.pick_macro"), parent=self.winfo_toplevel())
            return
        if not messagebox.askyesno(self.tr.t("timetask.delete"), self.tr.t("timetask.delete_confirm", name=self.selected_path.stem), parent=self.winfo_toplevel()):
            return
        try:
            self.selected_path.unlink()
        except OSError as exc:
            messagebox.showerror(self.tr.t("timetask.delete"), str(exc), parent=self.winfo_toplevel())
            return
        self.selected_path = None
        self.refresh_macro_list()
        self.show_replay_overlay(self.tr.t("timetask.deleted"))

    def refresh_macro_list(self, select_path: Path | None = None) -> None:
        self.summaries = self.recorder.list_macros()
        self.macro_list.delete(0, tk.END)
        for summary in self.summaries:
            self.macro_list.insert(tk.END, self.format_summary(summary))
            
        if hasattr(self, "stock_macro_combobox"):
            macro_names = [self.tr.t("timetask.none")] + [summary.name for summary in self.summaries]
            self.stock_macro_combobox.configure(values=macro_names)
            if self.stock_macro_var.get() not in macro_names:
                self.stock_macro_var.set(self.tr.t("timetask.none"))
                
        if select_path:
            for index, summary in enumerate(self.summaries):
                if summary.path == select_path:
                    self.macro_list.selection_set(index)
                    self.macro_list.activate(index)
                    self.selected_path = summary.path
                    break
        elif not self.selected_path and self.summaries:
            self.selected_path = self.summaries[0].path

    def format_summary(self, summary: MacroSummary) -> str:
        return self.tr.t("timetask.list_item", name=summary.name, duration=f"{summary.duration:.1f}s", events=summary.events, created=summary.created_at)

    def on_select_macro(self, _event=None) -> None:
        selection = self.macro_list.curselection()
        if not selection:
            return
        index = int(selection[0])
        if 0 <= index < len(self.summaries):
            self.selected_path = self.summaries[index].path
            self.show_replay_overlay()

    def on_recorder_status(self, message: str) -> None:
        self.after(0, self.status_var.set, message)
        if "finalizada" in message.lower() or "cancelada" in message.lower() or "parada" in message.lower():
            self.after(0, self.show_replay_overlay)

    def poll_state(self) -> None:
        events = self.recorder.snapshot_events()
        duration = events[-1]["t"] if events else 0.0
        self.metric_var.set(self.tr.t("timetask.metric", events=len(events), duration=f"{duration:.1f}s"))
        if self.recorder.recording:
            detail = self.tr.t("timetask.overlay_paused") if self.recorder.paused else self.tr.t("timetask.overlay_events_live", events=len(events), live=self.recorder.live_status())
            self.overlay.show(self.tr.t("timetask.overlay_recording"), detail, self.tr.t("timetask.overlay_focus_hint"), COLORS["warn"])
        elif self.recorder.replaying:
            detail = self.tr.t("timetask.overlay_paused") if self.recorder.replay_paused else self.tr.t("timetask.overlay_replay_live", live=self.recorder.replay_status())
            self.replay_overlay.show(self.tr.t("timetask.overlay_playing"), detail, COLORS["good"])
        self.after(300, self.poll_state)

    def show_idle_overlay(self) -> None:
        self.overlay.hide()

    def show_replay_overlay(self, detail: str | None = None) -> None:
        if not self.active:
            return
        if detail is None:
            if self.selected_path:
                detail = self.selected_path.stem
            elif self.summaries:
                detail = self.summaries[0].name
            else:
                detail = self.tr.t("timetask.replay_empty")
        
        self.replay_overlay.show(self.tr.t("timetask.replay_overlay_title"), detail, COLORS["good"])

    def set_active(self, active: bool) -> None:
        self.active = active
        if active:
            if self.recorder.recording or self.recorder.replaying:
                return
            self.show_replay_overlay()
        elif not self.recorder.recording and not self.recorder.replaying:
            self.overlay.hide()
            self.replay_overlay.hide()

    def refresh_language(self, translator: Translator) -> None:
        self.tr = translator
        self.overlay.refresh_language(translator)
        self.replay_overlay.refresh_language(translator)
        for child in self.winfo_children():
            child.destroy()
        self.build()
        self.refresh_macro_list(select_path=self.selected_path)

    def stop(self) -> None:
        self.cancel_countdown()
        self.recorder.stop()
        self.overlay.destroy()
        self.replay_overlay.destroy()
