from __future__ import annotations

import ctypes
from pathlib import Path
import threading
import time
import tkinter as tk
from tkinter import ttk

try:
    import customtkinter as ctk
except ImportError:  # pragma: no cover - optional visual upgrade.
    ctk = None

from i18n import Translator
from settings_store import load_settings, save_settings


COLORS = {
    "bg": "#070b16",
    "card": "#111c31",
    "card_2": "#1d3353",
    "text": "#edf6ff",
    "muted": "#99abc4",
    "accent": "#5eead4",
    "accent_2": "#8ab4ff",
    "soft": "#0e1a2d",
    "good": "#62d7a4",
    "warn": "#ffd166",
    "line": "#2d496f",
    "hover": "#172943",
    "accent_text": "#041014",
}

BASE_DIR = Path(__file__).resolve().parent
SOUND_DIRS = (BASE_DIR / "efeitos sonoros", BASE_DIR / "audio")
SOUND_EXTENSIONS = (".wav", ".mp3", ".wma")
SQUADLOCK_SECONDS = 30 * 60
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
FOXHOLE_PROCESS_NAMES = ("war-win64-shipping.exe", "foxhole.exe")
FOXHOLE_PATH_HINTS = ("\\steamapps\\common\\foxhole\\", "/steamapps/common/foxhole/")


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


def modern_button(
    parent,
    *,
    text: str,
    command,
    color: str,
    text_color: str,
    hover: str | None = None,
    height: int = 42,
    font: tuple = ("Segoe UI", 10, "bold"),
):
    if ctk is not None:
        return ctk.CTkButton(
            parent,
            text=text,
            command=command,
            fg_color=color,
            bg_color=parent_surface_color(parent, COLORS["bg"]),
            hover_color=hover or COLORS["hover"],
            text_color=text_color,
            corner_radius=12,
            height=height,
            font=font,
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
        font=font,
        cursor="hand2",
    )


def configure_surface(widget, color: str) -> None:
    if ctk is not None:
        try:
            widget.configure(fg_color=color)
            return
        except Exception:
            pass
    widget.configure(bg=color)


def sound_path(name: str) -> Path | None:
    for directory in SOUND_DIRS:
        for extension in SOUND_EXTENSIONS:
            path = directory / f"{name}{extension}"
            if path.exists():
                return path
    return None


def play_sound(name: str) -> None:
    path = sound_path(name)
    if not path:
        return
    if path.suffix.lower() == ".wav":
        try:
            import winsound

            winsound.PlaySound(str(path), winsound.SND_FILENAME | winsound.SND_ASYNC)
            return
        except Exception:
            pass
    try:
        alias = f"gg_{name}_{int(time.time() * 1000)}"
        winmm = ctypes.windll.winmm
        winmm.mciSendStringW(f"close {alias}", None, 0, None)
        winmm.mciSendStringW(f'open "{path}" type mpegvideo alias {alias}', None, 0, None)
        winmm.mciSendStringW(f"play {alias}", None, 0, None)
        threading.Timer(10.0, lambda: winmm.mciSendStringW(f"close {alias}", None, 0, None)).start()
    except Exception:
        pass


def format_time(seconds: int) -> str:
    minutes, remainder = divmod(max(0, seconds), 60)
    return f"{minutes:02d}:{remainder:02d}"


class SquadlockOverlay:
    def __init__(self, parent: tk.Widget, on_reset, on_finish, on_moved, translator: Translator | None = None) -> None:
        self.parent = parent
        self.tr = translator or Translator()
        self.on_reset = on_reset
        self.on_finish = on_finish
        self.on_moved = on_moved
        self.position: tuple[int, int] | None = None
        self.drag_state: dict[str, int] = {}
        self.window = ctk.CTkToplevel(parent) if ctk is not None else tk.Toplevel(parent)
        self.window.withdraw()
        self.window.overrideredirect(True)
        self.window.attributes("-topmost", True)
        configure_surface(self.window, COLORS["bg"])
        try:
            self.window.attributes("-transparentcolor", COLORS["bg"])
            self.window.attributes("-toolwindow", True)
        except Exception:
            pass

        self.shell = modern_frame(self.window, "#0d1828", radius=10, border=1, border_color="#39506f")
        self.shell.pack(fill="both", expand=True, padx=3, pady=3)
        self.title_label = tk.Label(
            self.shell,
            text=self.tr.t("notifications.overlay_title"),
            bg="#0d1828",
            fg="#a8bfdc",
            font=("Segoe UI", 7, "bold"),
            padx=9,
            pady=1,
        )
        self.title_label.grid(row=0, column=0, sticky="w")
        self.time_label = tk.Label(
            self.shell,
            text="30:00",
            bg="#0d1828",
            fg=COLORS["text"],
            font=("Segoe UI", 14, "bold"),
            padx=9,
            pady=1,
        )
        self.time_label.grid(row=1, column=0, sticky="w")
        self.status_label = tk.Label(
            self.shell,
            text=self.tr.t("notifications.vehicle"),
            bg="#0d1828",
            fg="#7f93ad",
            font=("Segoe UI", 7, "bold"),
            padx=9,
            pady=1,
        )
        self.status_label.grid(row=2, column=0, sticky="w")

        self.actions = tk.Frame(self.shell, bg="#0d1828")
        self.reset_button = tk.Button(
            self.actions,
            text=self.tr.t("notifications.reset"),
            command=self.on_reset,
            bg=COLORS["card_2"],
            fg=COLORS["text"],
            activebackground=COLORS["hover"],
            activeforeground=COLORS["text"],
            relief="flat",
            font=("Segoe UI", 7, "bold"),
            cursor="hand2",
        )
        self.done_button = tk.Button(
            self.actions,
            text=self.tr.t("notifications.finish"),
            command=self.on_finish,
            bg=COLORS["accent"],
            fg=COLORS["accent_text"],
            activebackground=COLORS["accent_2"],
            activeforeground=COLORS["accent_text"],
            relief="flat",
            font=("Segoe UI", 7, "bold"),
            cursor="hand2",
        )
        self.reset_button.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        self.done_button.grid(row=0, column=1, sticky="ew", padx=(5, 0))
        self.actions.columnconfigure(0, weight=1)
        self.actions.columnconfigure(1, weight=1)

        for widget in (self.window, self.shell, self.title_label, self.time_label, self.status_label):
            widget.bind("<ButtonPress-1>", self.start_drag, add="+")
            widget.bind("<B1-Motion>", self.drag, add="+")
            widget.bind("<ButtonRelease-1>", self.end_drag, add="+")

    def show(self, seconds: int, finished: bool = False) -> None:
        self.update(seconds, finished)
        self.position_window()
        self.window.deiconify()
        self.window.lift()

    def hide(self) -> None:
        self.window.withdraw()

    def update(self, seconds: int, finished: bool = False) -> None:
        self.time_label.configure(text=format_time(seconds))
        if finished:
            self.status_label.configure(text=self.tr.t("notifications.finished"), fg=COLORS["good"])
            self.actions.grid(row=3, column=0, sticky="ew", padx=10, pady=(4, 10))
        else:
            self.status_label.configure(text=self.tr.t("notifications.vehicle"), fg="#7f93ad")
            self.actions.grid_forget()

    def set_translator(self, translator: Translator) -> None:
        self.tr = translator
        self.title_label.configure(text=self.tr.t("notifications.overlay_title"))
        self.reset_button.configure(text=self.tr.t("notifications.reset"))
        self.done_button.configure(text=self.tr.t("notifications.finish"))
        current = str(self.time_label.cget("text"))
        try:
            minutes, seconds = current.split(":", 1)
            total = int(minutes) * 60 + int(seconds)
        except Exception:
            total = 0
        self.update(total, self.actions.winfo_ismapped())

    def position_window(self) -> None:
        width = 148
        height = 118 if self.actions.winfo_ismapped() else 82
        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()
        x, y = self.position or (screen_width - width - 24, 222)
        x = max(8, min(int(x), screen_width - width - 8))
        y = max(8, min(int(y), screen_height - height - 8))
        self.position = (x, y)
        self.window.geometry(f"{width}x{height}+{x}+{y}")

    def set_position(self, x, y) -> None:
        try:
            if x is not None and y is not None:
                self.position = (int(x), int(y))
        except (TypeError, ValueError):
            self.position = None

    def start_drag(self, event) -> None:
        self.drag_state = {
            "mouse_x": event.x_root,
            "mouse_y": event.y_root,
            "start_x": self.window.winfo_x(),
            "start_y": self.window.winfo_y(),
        }

    def drag(self, event) -> None:
        if not self.drag_state:
            return
        new_x = int(self.drag_state["start_x"]) + event.x_root - int(self.drag_state["mouse_x"])
        new_y = int(self.drag_state["start_y"]) + event.y_root - int(self.drag_state["mouse_y"])
        self.position = (new_x, new_y)
        self.window.geometry(f"+{new_x}+{new_y}")

    def end_drag(self, _event) -> None:
        if self.position:
            self.on_moved(self.position)
        self.drag_state = {}

    def destroy(self) -> None:
        if self.window.winfo_exists():
            self.window.destroy()


class NotificationsCategory(ttk.Frame):
    def __init__(self, parent: ttk.Widget, translator: Translator | None = None) -> None:
        super().__init__(parent, style="Panel.TFrame")
        self.tr = translator or Translator()
        self.settings = load_settings()
        notification_settings = self.settings["notifications"]
        self.overlay_enabled_var = tk.BooleanVar(value=bool(notification_settings.get("squadlock_overlay_enabled", True)))
        self.remaining_seconds = SQUADLOCK_SECONDS
        self.running = False
        self.finished = False
        self.tick_job: str | None = None
        self.focus_job: str | None = None
        self.status_var = tk.StringVar(value=self.tr.t("notifications.waiting"))
        self.time_var = tk.StringVar(value=format_time(self.remaining_seconds))
        self.overlay = SquadlockOverlay(self, self.reset_squadlock, self.finish_squadlock, self.save_overlay_position, self.tr)
        self.overlay.set_position(notification_settings.get("squadlock_x"), notification_settings.get("squadlock_y"))
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.build()

    def build(self) -> None:
        container = modern_frame(self, COLORS["bg"], radius=0)
        container.grid(row=0, column=0, sticky="nsew")
        container.columnconfigure(0, weight=1)
        tk.Label(container, text=self.tr.t("notifications.title"), bg=COLORS["bg"], fg=COLORS["text"], font=("Segoe UI", 24, "bold")).grid(
            row=0, column=0, sticky="w", padx=22, pady=(20, 2)
        )
        tk.Label(
            container,
            text=self.tr.t("notifications.subtitle"),
            bg=COLORS["bg"],
            fg=COLORS["accent_2"],
            font=("Segoe UI", 11, "bold"),
        ).grid(row=1, column=0, sticky="w", padx=22, pady=(0, 16))

        card = modern_frame(container, COLORS["card"], radius=18, border=1, border_color=COLORS["line"])
        card.grid(row=2, column=0, sticky="ew", padx=22, pady=(0, 16))
        card.columnconfigure(0, weight=1)
        tk.Label(card, text=self.tr.t("notifications.squadlock_title"), bg=COLORS["card"], fg=COLORS["text"], font=("Segoe UI", 18, "bold")).grid(
            row=0, column=0, sticky="w", padx=20, pady=(18, 4)
        )
        tk.Label(
            card,
            text=self.tr.t("notifications.squadlock_body"),
            bg=COLORS["card"],
            fg=COLORS["muted"],
            font=("Segoe UI", 10),
            wraplength=760,
            justify="left",
        ).grid(row=1, column=0, sticky="w", padx=20, pady=(0, 12))

        timer = tk.Label(card, textvariable=self.time_var, bg=COLORS["card"], fg=COLORS["warn"], font=("Segoe UI", 38, "bold"))
        timer.grid(row=2, column=0, sticky="w", padx=20, pady=(0, 6))
        tk.Label(card, textvariable=self.status_var, bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI", 10, "bold")).grid(
            row=3, column=0, sticky="w", padx=20, pady=(0, 14)
        )

        options = modern_frame(card, COLORS["card"], radius=0)
        options.grid(row=4, column=0, sticky="ew", padx=20, pady=(0, 14))
        tk.Checkbutton(
            options,
            text=self.tr.t("notifications.show_overlay"),
            variable=self.overlay_enabled_var,
            command=self.save_settings,
            bg=COLORS["card"],
            fg=COLORS["text"],
            selectcolor=COLORS["soft"],
            activebackground=COLORS["card"],
            activeforeground=COLORS["text"],
            font=("Segoe UI", 9, "bold"),
        ).grid(row=0, column=0, sticky="w")

        actions = modern_frame(card, COLORS["card"], radius=0)
        actions.grid(row=5, column=0, sticky="ew", padx=20, pady=(0, 20))
        actions.columnconfigure(0, weight=1)
        actions.columnconfigure(1, weight=1)
        actions.columnconfigure(2, weight=1)
        modern_button(
            actions,
            text=self.tr.t("notifications.start"),
            command=self.start_squadlock,
            color=COLORS["accent"],
            text_color=COLORS["accent_text"],
            hover=COLORS["accent_2"],
        ).grid(row=0, column=0, sticky="ew", padx=(0, 8))
        modern_button(
            actions,
            text=self.tr.t("notifications.reset"),
            command=self.reset_squadlock,
            color=COLORS["card_2"],
            text_color=COLORS["text"],
        ).grid(row=0, column=1, sticky="ew", padx=8)
        modern_button(
            actions,
            text=self.tr.t("notifications.finish"),
            command=self.finish_squadlock,
            color=COLORS["soft"],
            text_color=COLORS["text"],
        ).grid(row=0, column=2, sticky="ew", padx=(8, 0))

    def save_settings(self) -> None:
        self.settings = load_settings()
        self.settings["notifications"] = {
            **self.settings.get("notifications", {}),
            "squadlock_overlay_enabled": self.overlay_enabled_var.get(),
            "squadlock_x": self.overlay.position[0] if self.overlay.position else None,
            "squadlock_y": self.overlay.position[1] if self.overlay.position else None,
        }
        save_settings(self.settings)
        if not self.overlay_enabled_var.get():
            self.overlay.hide()
        elif self.running or self.finished:
            self.overlay.show(self.remaining_seconds, self.finished)

    def save_overlay_position(self, position: tuple[int, int]) -> None:
        self.overlay.position = position
        self.save_settings()

    def start_squadlock(self) -> None:
        self.cancel_tick()
        self.cancel_focus_watch()
        self.remaining_seconds = SQUADLOCK_SECONDS
        self.running = True
        self.finished = False
        self.status_var.set(self.tr.t("notifications.active"))
        self.update_views()
        self.start_focus_watch()
        self.tick_job = self.after(1000, self.tick)

    def reset_squadlock(self) -> None:
        self.start_squadlock()

    def finish_squadlock(self) -> None:
        self.cancel_tick()
        self.cancel_focus_watch()
        self.running = False
        self.finished = False
        self.remaining_seconds = SQUADLOCK_SECONDS
        self.status_var.set(self.tr.t("notifications.waiting"))
        self.update_views()
        self.overlay.hide()

    def tick(self) -> None:
        if not self.running:
            return
        self.remaining_seconds -= 1
        if self.remaining_seconds <= 0:
            self.remaining_seconds = 0
            self.running = False
            self.finished = True
            self.status_var.set(self.tr.t("notifications.finished"))
            self.update_views()
            self.start_focus_watch()
            if load_settings().get("app", {}).get("squadlock_sound_enabled", True):
                play_sound("squad")
            return
        self.update_views()
        self.tick_job = self.after(1000, self.tick)

    def update_views(self) -> None:
        self.time_var.set(format_time(self.remaining_seconds))
        if self.overlay_enabled_var.get() and (self.running or self.finished) and self.is_foxhole_foreground():
            self.overlay.show(self.remaining_seconds, self.finished)
        else:
            self.overlay.hide()

    def start_focus_watch(self) -> None:
        self.cancel_focus_watch()
        self.focus_job = self.after(500, self.watch_overlay_focus)

    def watch_overlay_focus(self) -> None:
        self.focus_job = None
        if self.running or self.finished:
            self.update_views()
            self.start_focus_watch()

    def cancel_tick(self) -> None:
        if self.tick_job:
            try:
                self.after_cancel(self.tick_job)
            except tk.TclError:
                pass
            self.tick_job = None

    def cancel_focus_watch(self) -> None:
        if self.focus_job:
            try:
                self.after_cancel(self.focus_job)
            except tk.TclError:
                pass
            self.focus_job = None

    def is_foxhole_foreground(self) -> bool:
        try:
            user32 = ctypes.windll.user32
            foreground = user32.GetForegroundWindow()
            if not foreground:
                return False
            try:
                if self.overlay.window.winfo_exists() and foreground == self.overlay.window.winfo_id():
                    return True
            except Exception:
                pass
            return self.is_foxhole_window(foreground)
        except Exception:
            return False

    def is_foxhole_window(self, hwnd: int) -> bool:
        process_path = self.get_window_process_path(hwnd).lower()
        process_name = Path(process_path).name.lower() if process_path else ""
        return process_name in FOXHOLE_PROCESS_NAMES or any(hint in process_path for hint in FOXHOLE_PATH_HINTS)

    def get_window_process_path(self, hwnd: int) -> str:
        pid = ctypes.c_ulong()
        ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if not pid.value:
            return ""
        handle = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)
        if not handle:
            return ""
        try:
            path_buffer = ctypes.create_unicode_buffer(1024)
            size = ctypes.c_ulong(len(path_buffer))
            if ctypes.windll.kernel32.QueryFullProcessImageNameW(handle, 0, path_buffer, ctypes.byref(size)):
                return path_buffer.value
            return ""
        finally:
            ctypes.windll.kernel32.CloseHandle(handle)

    def refresh_language(self, translator: Translator) -> None:
        self.tr = translator
        self.overlay.set_translator(translator)
        overlay_enabled = self.overlay_enabled_var.get()
        overlay_position = self.overlay.position
        if not self.running and not self.finished:
            self.status_var.set(self.tr.t("notifications.waiting"))
        elif self.running:
            self.status_var.set(self.tr.t("notifications.active"))
        else:
            self.status_var.set(self.tr.t("notifications.finished"))
        for child in self.winfo_children():
            child.destroy()
        self.overlay_enabled_var.set(overlay_enabled)
        self.overlay.position = overlay_position
        self.build()
        if self.overlay_enabled_var.get() and (self.running or self.finished):
            self.overlay.show(self.remaining_seconds, self.finished)
        else:
            self.overlay.hide()

    def stop(self) -> None:
        self.cancel_tick()
        self.cancel_focus_watch()
        self.overlay.destroy()
