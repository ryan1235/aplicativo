import ctypes
import time
import tkinter as tk
from tkinter import ttk

try:
    import customtkinter as ctk
except ImportError:  # pragma: no cover - optional visual upgrade.
    ctk = None

from auto_clicker import HOTKEYS, MOUSE_BUTTONS, POINT, AutoClicker
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
    "good": "#62d7a4",
    "warn": "#ffd166",
    "soft": "#0e1a2d",
    "line": "#2d496f",
    "hover": "#172943",
    "accent_text": "#041014",
}

SPEEDS = {
    "Devagar": 0.50,
    "Normal": 0.10,
    "Rapido": 0.05,
}

OVERLAY_COLORS = {
    "Azul": {"bg": "#071426", "panel": "#12233d", "accent": "#8ab4ff"},
    "Verde": {"bg": "#071a18", "panel": "#10342e", "accent": "#5eead4"},
    "Roxo": {"bg": "#141125", "panel": "#2a214b", "accent": "#c4b5fd"},
    "Vermelho": {"bg": "#211016", "panel": "#431926", "accent": "#ff8aa0"},
}

OVERLAY_COLOR_LABEL_KEYS = {
    "Azul": "overlay.color_blue",
    "Verde": "overlay.color_green",
    "Roxo": "overlay.color_purple",
    "Vermelho": "overlay.color_red",
}

GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_APPWINDOW = 0x00040000
HWND_TOPMOST = -1
HWND_NOTOPMOST = -2
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOACTIVATE = 0x0010
SWP_SHOWWINDOW = 0x0040
LWA_ALPHA = 0x00000002


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
            corner_radius=14,
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
        padx=18,
        pady=12,
        font=font,
        cursor="hand2",
    )


def configure_button_color(button, color: str, text_color: str | None = None) -> None:
    if ctk is not None:
        kwargs = {"fg_color": color}
        if text_color:
            kwargs["text_color"] = text_color
        button.configure(**kwargs)
    else:
        kwargs = {"bg": color}
        if text_color:
            kwargs["fg"] = text_color
        button.configure(**kwargs)


def widget_color(widget, fallback: str) -> str:
    if ctk is not None:
        try:
            color = widget.cget("fg_color")
            if isinstance(color, tuple):
                return color[-1]
            return color
        except Exception:
            return fallback
    return widget.cget("bg")


def configure_surface(widget, color: str) -> None:
    if ctk is not None:
        try:
            widget.configure(fg_color=color)
            return
        except Exception:
            pass
    widget.configure(bg=color)


class AutoClickerOverlay:
    def __init__(self, parent: tk.Widget) -> None:
        self.parent = parent
        self.focus_check = lambda: False
        self.enabled_by_hotkey = True
        self.show_profile = True
        self.show_clicker = True
        self.show_target = True
        self.panel_position: tuple[int, int] | None = None
        self.notification_position: tuple[int, int] | None = None
        self.adjusting = False
        self.panel_hidden_for_adjust = False
        self.notification_hidden_for_adjust = False
        self.drag_state: dict[str, int | tk.Toplevel] = {}
        self.pin_job: str | None = None
        self.panel_alpha = 1.0
        self.notification_alpha = 1.0
        self.palette = OVERLAY_COLORS["Azul"]
        self.window = ctk.CTkToplevel(parent) if ctk is not None else tk.Toplevel(parent)
        self.window.withdraw()
        self.window.overrideredirect(True)
        self.window.attributes("-topmost", True)
        self.window.attributes("-alpha", 1.0)
        self.configure_overlay_shell(self.window)
        configure_surface(self.window, self.palette["bg"])

        self.shell = modern_frame(self.window, self.palette["panel"], radius=12, border=1, border_color=self.palette["accent"])
        self.shell.pack(fill="both", expand=True, padx=4, pady=4)

        self.status_label = tk.Label(
            self.shell,
            text="AUTO CLICKER",
            bg=self.palette["panel"],
            fg=self.palette["accent"],
            font=("Segoe UI", 8, "bold"),
            padx=10,
            pady=3,
        )
        self.status_label.pack(fill="x")
        self.profile_label = tk.Label(
            self.shell,
            text="Perfil",
            bg=self.palette["panel"],
            fg=COLORS["muted"],
            font=("Segoe UI", 8, "bold"),
            padx=10,
            pady=1,
        )
        self.profile_label.pack(fill="x")
        self.detail_label = tk.Label(
            self.shell,
            text="Pausado",
            bg=self.palette["panel"],
            fg=COLORS["text"],
            font=("Segoe UI", 9, "bold"),
            padx=10,
            pady=2,
        )
        self.detail_label.pack(fill="x")
        self.target_label = tk.Label(
            self.shell,
            text="Foxhole",
            bg=self.palette["panel"],
            fg=COLORS["muted"],
            font=("Segoe UI", 8),
            padx=10,
            pady=2,
        )
        self.target_label.pack(fill="x")

        self.adjust_label = tk.Label(
            self.shell,
            text="Arraste para mover",
            bg=self.palette["panel"],
            fg=COLORS["accent"],
            font=("Segoe UI", 8, "bold"),
            padx=10,
            pady=3,
        )
        self.panel_close_button = tk.Button(
            self.shell,
            text="X",
            command=lambda: self.hide_adjust_overlay("panel"),
            bg="#431926",
            fg=COLORS["text"],
            activebackground="#5f2034",
            activeforeground=COLORS["text"],
            relief="flat",
            font=("Segoe UI", 8, "bold"),
            cursor="hand2",
        )

        self.notification = ctk.CTkToplevel(parent) if ctk is not None else tk.Toplevel(parent)
        self.notification.withdraw()
        self.notification.overrideredirect(True)
        self.notification.attributes("-topmost", True)
        self.notification.attributes("-alpha", 1.0)
        self.configure_overlay_shell(self.notification)
        configure_surface(self.notification, self.palette["bg"])
        self.notification_shell = modern_frame(self.notification, self.palette["panel"], radius=12, border=1, border_color=COLORS["good"])
        self.notification_shell.pack(fill="both", expand=True, padx=4, pady=4)
        self.notification_icon = tk.Label(
            self.notification_shell,
            text="OK",
            bg=COLORS["good"],
            fg=COLORS["accent_text"],
            font=("Segoe UI", 11, "bold"),
            padx=8,
            pady=3,
        )
        self.notification_icon.grid(row=0, column=0, sticky="ns", padx=(12, 8), pady=12)
        self.notification_text = tk.Label(
            self.notification_shell,
            text="Upload enviado com sucesso",
            bg=self.palette["panel"],
            fg=COLORS["text"],
            font=("Segoe UI", 9, "bold"),
            anchor="w",
            padx=6,
            pady=8,
        )
        self.notification_text.grid(row=0, column=1, sticky="ew", padx=(0, 12), pady=8)
        self.notification_shell.columnconfigure(1, weight=1)
        self.notification_close_button = tk.Button(
            self.notification_shell,
            text="X",
            command=lambda: self.hide_adjust_overlay("notification"),
            bg="#431926",
            fg=COLORS["text"],
            activebackground="#5f2034",
            activeforeground=COLORS["text"],
            relief="flat",
            font=("Segoe UI", 8, "bold"),
            cursor="hand2",
        )

        self.adjust_controls = ctk.CTkToplevel(parent) if ctk is not None else tk.Toplevel(parent)
        self.adjust_controls.withdraw()
        self.adjust_controls.overrideredirect(True)
        self.adjust_controls.attributes("-topmost", True)
        self.adjust_controls.attributes("-alpha", 1.0)
        self.configure_overlay_shell(self.adjust_controls)
        configure_surface(self.adjust_controls, self.palette["bg"])
        self.adjust_controls_shell = modern_frame(
            self.adjust_controls,
            COLORS["card"],
            radius=12,
            border=1,
            border_color=self.palette["accent"],
        )
        self.adjust_controls_shell.pack(fill="both", expand=True, padx=4, pady=4)
        self.adjust_controls_label = tk.Label(
            self.adjust_controls_shell,
            text="Ajuste os overlays",
            bg=COLORS["card"],
            fg=COLORS["text"],
            font=("Segoe UI", 9, "bold"),
            padx=10,
            pady=7,
        )
        self.adjust_controls_label.grid(row=0, column=0, sticky="ew", padx=(8, 4), pady=8)
        self.adjust_confirm_button = tk.Button(
            self.adjust_controls_shell,
            text="Salvar posicoes",
            command=self.finish_adjust_positions,
            bg=COLORS["accent"],
            fg=COLORS["accent_text"],
            activebackground=COLORS["accent_2"],
            activeforeground=COLORS["accent_text"],
            relief="flat",
            font=("Segoe UI", 9, "bold"),
            cursor="hand2",
        )
        self.adjust_confirm_button.grid(row=0, column=1, sticky="ew", padx=(4, 8), pady=8)
        self.adjust_controls_shell.columnconfigure(0, weight=1)

        self.bind_drag(self.window)
        self.bind_drag(self.notification)
        self.position()
        self.position_notification()
        self.position_adjust_controls()
        self.apply_transparent_surfaces()
        self.window.after(150, self.make_click_through)
        self.window.after(200, self.pin_visible_windows)

    def configure_overlay_shell(self, window) -> None:
        try:
            window.attributes("-toolwindow", True)
        except tk.TclError:
            pass

    def set_focus_checker(self, callback) -> None:
        self.focus_check = callback

    def parse_position(self, x, y) -> tuple[int, int] | None:
        try:
            if x is None or y is None:
                return None
            return int(x), int(y)
        except (TypeError, ValueError):
            return None

    def position(self) -> None:
        self.window.update_idletasks()
        width = 190
        height = 104 if self.adjusting else 68
        screen_width = self.window.winfo_screenwidth()
        x, y = self.panel_position or (screen_width - width - 24, 24)
        self.window.geometry(f"{width}x{height}+{x}+{y}")

    def position_notification(self) -> None:
        self.notification.update_idletasks()
        width = 380
        height = 58
        screen_width = self.notification.winfo_screenwidth()
        screen_height = self.notification.winfo_screenheight()
        x, y = self.notification_position or (screen_width - width - 24, 136)
        x = max(8, min(int(x), screen_width - width - 8))
        y = max(8, min(int(y), screen_height - height - 8))
        self.notification_position = (x, y)
        self.notification.geometry(f"{width}x{height}+{x}+{y}")

    def position_adjust_controls(self) -> None:
        self.adjust_controls.update_idletasks()
        width = 320
        height = 58
        screen_width = self.adjust_controls.winfo_screenwidth()
        screen_height = self.adjust_controls.winfo_screenheight()
        x = max(12, (screen_width - width) // 2)
        y = max(12, screen_height - height - 96)
        self.adjust_controls.geometry(f"{width}x{height}+{x}+{y}")

    def apply_transparent_surfaces(self) -> None:
        transparent_targets = (
            (self.window, self.palette["bg"]),
            (self.notification, self.palette["bg"]),
            (self.adjust_controls, self.palette["bg"]),
        )
        for window, transparent in transparent_targets:
            try:
                window.configure(bg=transparent)
                window.attributes("-transparentcolor", transparent)
            except Exception:
                pass

    def make_click_through(self) -> None:
        self.set_click_through(True)

    def get_window_ex_style(self, user32, hwnd: int) -> int:
        getter = getattr(user32, "GetWindowLongPtrW", None) or user32.GetWindowLongW
        return int(getter(hwnd, GWL_EXSTYLE))

    def set_window_ex_style(self, user32, hwnd: int, style: int) -> None:
        setter = getattr(user32, "SetWindowLongPtrW", None) or user32.SetWindowLongW
        setter(hwnd, GWL_EXSTYLE, style)

    def set_click_through(self, enabled: bool) -> None:
        try:
            user32 = ctypes.windll.user32
            for window in (self.window, self.notification, self.adjust_controls):
                window.update_idletasks()
                hwnd = window.winfo_id()
                current_style = self.get_window_ex_style(user32, hwnd)
                current_style |= WS_EX_TOOLWINDOW
                current_style &= ~WS_EX_APPWINDOW
                current_style &= ~WS_EX_TRANSPARENT
                if enabled:
                    current_style |= WS_EX_TRANSPARENT
                self.set_window_ex_style(user32, hwnd, current_style)
                self.apply_window_alpha(window)
                self.pin_window(window, show=window.state() != "withdrawn")
        except Exception:
            pass

    def apply_window_alpha(self, window) -> None:
        try:
            window.attributes("-alpha", 1.0)
        except Exception:
            pass

    def pin_window(self, window, *, show: bool = True) -> None:
        if not window.winfo_exists():
            return
        try:
            window.attributes("-topmost", True)
            self.apply_window_alpha(window)
            window.lift()
            hwnd = window.winfo_id()
            flags = SWP_NOMOVE | SWP_NOSIZE
            if not self.adjusting:
                flags |= SWP_NOACTIVATE
            if show:
                flags |= SWP_SHOWWINDOW
            ctypes.windll.user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, flags)
        except Exception:
            pass

    def force_adjust_windows_front(self) -> None:
        if not self.adjusting:
            return
        for window in (self.window, self.notification, self.adjust_controls):
            if not window.winfo_exists() or window.state() == "withdrawn":
                continue
            try:
                window.attributes("-topmost", False)
                window.attributes("-topmost", True)
                window.deiconify()
                window.lift()
                self.pin_window(window)
            except Exception:
                pass
        self.set_click_through(False)

    def pin_visible_windows(self) -> None:
        if self.window.winfo_exists() and self.window.state() != "withdrawn":
            self.pin_window(self.window)
        if self.notification.winfo_exists() and self.notification.state() != "withdrawn":
            self.pin_window(self.notification)
        if self.adjust_controls.winfo_exists() and self.adjust_controls.state() != "withdrawn":
            self.pin_window(self.adjust_controls)

    def start_topmost_watch(self) -> None:
        self.stop_topmost_watch()
        self.keep_topmost()

    def keep_topmost(self) -> None:
        self.pin_visible_windows()
        if (
            self.adjusting
            or self.window.state() != "withdrawn"
            or self.notification.state() != "withdrawn"
            or self.adjust_controls.state() != "withdrawn"
        ):
            self.pin_job = self.window.after(250, self.keep_topmost)

    def stop_topmost_watch(self) -> None:
        if self.pin_job:
            try:
                self.window.after_cancel(self.pin_job)
            except tk.TclError:
                pass
            self.pin_job = None

    def configure(
        self,
        enabled_by_hotkey: bool,
        color_name: str,
        show_profile: bool,
        show_clicker: bool,
        show_target: bool,
        panel_x=None,
        panel_y=None,
        notification_x=None,
        notification_y=None,
    ) -> None:
        self.enabled_by_hotkey = enabled_by_hotkey
        self.show_profile = show_profile
        self.show_clicker = show_clicker
        self.show_target = show_target
        self.panel_position = self.parse_position(panel_x, panel_y)
        self.notification_position = self.parse_position(notification_x, notification_y)
        self.palette = OVERLAY_COLORS.get(color_name, OVERLAY_COLORS["Azul"])
        configure_surface(self.window, self.palette["bg"])
        configure_surface(self.notification, self.palette["bg"])
        configure_surface(self.adjust_controls, self.palette["bg"])
        if ctk is not None:
            self.shell.configure(fg_color=self.palette["panel"], border_color=self.palette["accent"])
            self.notification_shell.configure(fg_color=self.palette["panel"], border_color=COLORS["good"])
            self.adjust_controls_shell.configure(border_color=self.palette["accent"])
        else:
            self.shell.configure(bg=self.palette["panel"], highlightbackground=self.palette["accent"])
            self.notification_shell.configure(bg=self.palette["panel"], highlightbackground=COLORS["good"])
            self.adjust_controls_shell.configure(highlightbackground=self.palette["accent"])
        for label in (self.status_label, self.profile_label, self.detail_label, self.target_label, self.adjust_label):
            label.configure(bg=self.palette["panel"])
        self.notification_text.configure(bg=self.palette["panel"])
        self.status_label.configure(fg=self.palette["accent"])
        self.adjust_label.configure(fg=self.palette["accent"])
        self.position()
        self.position_notification()
        self.position_adjust_controls()
        self.apply_transparent_surfaces()

    def set_visible(self, visible: bool) -> None:
        if not self.window.winfo_exists():
            return
        if visible:
            self.window.attributes("-topmost", True)
            if not self.adjusting:
                self.position()
            self.window.deiconify()
            self.set_click_through(not self.adjusting)
            self.start_topmost_watch()
        else:
            if not self.adjusting:
                self.window.withdraw()

    def show_success_notification(self, text: str = "Upload enviado com sucesso") -> None:
        if not self.notification.winfo_exists():
            return
        if not self.focus_check():
            return
        self.notification_text.configure(text=text)
        self.position_notification()
        self.notification.attributes("-topmost", True)
        self.notification.deiconify()
        self.set_click_through(True)
        self.start_topmost_watch()
        self.notification.after(4500, self.hide_notification_if_needed)

    def hide_notification_if_needed(self) -> None:
        if not self.adjusting and self.notification.winfo_exists():
            self.notification.withdraw()

    def begin_adjust_positions(self, on_done=None, on_remove=None) -> None:
        self.adjusting = True
        self.on_adjust_done = on_done
        self.on_adjust_remove = on_remove
        self.panel_hidden_for_adjust = False
        self.notification_hidden_for_adjust = False
        self.position()
        self.position_notification()
        self.position_adjust_controls()
        self.adjust_label.pack(fill="x")
        self.panel_close_button.pack(anchor="ne", padx=8, pady=(2, 6))
        self.window.deiconify()
        self.notification_text.configure(text="Upload enviado com sucesso")
        self.notification_close_button.grid(row=0, column=2, sticky="ne", padx=(0, 8), pady=8)
        self.notification.deiconify()
        self.adjust_controls.deiconify()
        self.apply_transparent_surfaces()
        self.set_click_through(False)
        self.apply_window_alpha(self.window)
        self.apply_window_alpha(self.notification)
        self.apply_window_alpha(self.adjust_controls)
        self.start_topmost_watch()
        self.window.after(80, self.force_adjust_windows_front)
        self.window.after(300, self.force_adjust_windows_front)
        self.window.after(900, self.force_adjust_windows_front)
        self.window.after(1600, self.force_adjust_windows_front)

    def finish_adjust_positions(self) -> None:
        if not self.adjusting:
            return
        panel_position = self.current_panel_position()
        notification_position = self.current_notification_position()
        self.panel_position = panel_position
        self.notification_position = notification_position
        self.adjusting = False
        self.adjust_label.pack_forget()
        self.panel_close_button.pack_forget()
        self.notification_close_button.grid_forget()
        self.adjust_controls.withdraw()
        self.set_click_through(True)
        callback = getattr(self, "on_adjust_done", None)
        if callback:
            callback(panel_position, notification_position)
        self.position()
        self.notification.withdraw()
        self.stop_topmost_watch()

    def hide_adjust_overlay(self, overlay_name: str) -> None:
        if not self.adjusting:
            return
        if overlay_name == "panel":
            self.panel_hidden_for_adjust = True
            self.window.withdraw()
        elif overlay_name == "notification":
            self.notification_hidden_for_adjust = True
            self.notification.withdraw()
        callback = getattr(self, "on_adjust_remove", None)
        if callback:
            callback(overlay_name)
        self.force_adjust_windows_front()

    def current_panel_position(self) -> tuple[int, int]:
        return self.window.winfo_x(), self.window.winfo_y()

    def current_notification_position(self) -> tuple[int, int]:
        return self.notification.winfo_x(), self.notification.winfo_y()

    def bind_drag(self, window) -> None:
        for widget in self.iter_widgets(window):
            widget.bind("<ButtonPress-1>", lambda event, win=window: self.start_drag(event, win), add="+")
            widget.bind("<B1-Motion>", self.drag_window, add="+")
            widget.bind("<ButtonRelease-1>", self.end_drag, add="+")

    def iter_widgets(self, widget):
        yield widget
        for child in widget.winfo_children():
            yield from self.iter_widgets(child)

    def start_drag(self, event, window) -> None:
        if not self.adjusting:
            return
        self.drag_state = {
            "window": window,
            "mouse_x": event.x_root,
            "mouse_y": event.y_root,
            "start_x": window.winfo_x(),
            "start_y": window.winfo_y(),
        }

    def drag_window(self, event) -> None:
        if not self.adjusting or not self.drag_state:
            return
        window = self.drag_state["window"]
        dx = event.x_root - int(self.drag_state["mouse_x"])
        dy = event.y_root - int(self.drag_state["mouse_y"])
        new_x = int(self.drag_state["start_x"]) + dx
        new_y = int(self.drag_state["start_y"]) + dy
        window.geometry(f"+{new_x}+{new_y}")
        if window == self.window:
            self.panel_position = (new_x, new_y)
        elif window == self.notification:
            self.notification_position = (new_x, new_y)

    def end_drag(self, _event) -> None:
        if not self.adjusting:
            return
        self.drag_state = {}

    def update(self, enabled: bool, hotkey: str, interval: float, profile_name: str, target_title: str) -> None:
        if not self.window.winfo_exists():
            return
        self.profile_label.configure(text=profile_name if self.show_profile else "")
        self.profile_label.pack_forget()
        if self.show_profile:
            self.profile_label.pack(fill="x", after=self.status_label)

        if enabled:
            self.status_label.configure(text="AUTO CLICKER ATIVO", fg=COLORS["good"])
            self.detail_label.configure(text=f"{hotkey} | {interval:.2f}s", fg=COLORS["text"])
        else:
            self.status_label.configure(text="AUTO CLICKER PAUSADO", fg=COLORS["warn"])
            self.detail_label.configure(text=f"{hotkey} para ligar", fg=COLORS["muted"])
        self.detail_label.pack_forget()
        if self.show_clicker:
            self.detail_label.pack(fill="x", after=self.profile_label if self.show_profile else self.status_label)

        self.target_label.configure(text=target_title if target_title else "Foxhole")
        self.target_label.pack_forget()
        if self.show_target:
            self.target_label.pack(fill="x")

    def destroy(self) -> None:
        self.stop_topmost_watch()
        if self.window.winfo_exists():
            self.window.destroy()
        if self.notification.winfo_exists():
            self.notification.destroy()
        if self.adjust_controls.winfo_exists():
            self.adjust_controls.destroy()


class FunctionsCategory(ttk.Frame):
    def __init__(self, parent: ttk.Widget, translator: Translator | None = None) -> None:
        super().__init__(parent, style="Panel.TFrame")
        self.tr = translator or Translator()
        self.ui_text: dict[str, tk.Widget] = {}
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self.settings = load_settings()
        clicker_settings = self.settings["auto_clicker"]

        saved_interval = float(clicker_settings.get("interval", 0.10))
        saved_speed = min(SPEEDS, key=lambda name: abs(SPEEDS[name] - saved_interval))

        self.clicker_status_var = tk.StringVar(value=self.tr.t("clicker.off"))
        self.foxhole_status_var = tk.StringVar(value=self.tr.t("clicker.find_hint"))
        self.clicker = AutoClicker(self.set_clicker_status)
        self.overlay = AutoClickerOverlay(self)
        self.overlay.set_focus_checker(self.is_foxhole_overlay_context)
        self.overlay_hotkey_was_down = False
        self.last_overlay_reason = ""
        self.last_overlay_find_attempt = 0.0

        self.hotkey_var = tk.StringVar(value=clicker_settings.get("hotkey", "F3"))
        self.mouse_button_var = tk.StringVar(value=clicker_settings.get("mouse_button", "Esquerdo"))
        self.speed_var = tk.StringVar(value=saved_speed)
        self.overlay_enabled_var = tk.BooleanVar(value=bool(clicker_settings.get("overlay_enabled", True)))
        self.overlay_hotkey_var = tk.StringVar(value=clicker_settings.get("overlay_hotkey", "F8"))
        self.overlay_color_var = tk.StringVar(value=clicker_settings.get("overlay_color", "Azul"))
        self.overlay_color_display_var = tk.StringVar(value=self.overlay_color_label(self.overlay_color_var.get()))
        self.overlay_profile_var = tk.BooleanVar(value=bool(clicker_settings.get("overlay_show_profile", True)))
        self.overlay_clicker_var = tk.BooleanVar(value=bool(clicker_settings.get("overlay_show_clicker", True)))
        self.overlay_target_var = tk.BooleanVar(value=bool(clicker_settings.get("overlay_show_target", True)))
        self.overlay_notification_var = tk.BooleanVar(value=bool(clicker_settings.get("overlay_notification_enabled", True)))
        self.overlay_panel_x = clicker_settings.get("overlay_panel_x")
        self.overlay_panel_y = clicker_settings.get("overlay_panel_y")
        self.overlay_notification_x = clicker_settings.get("overlay_notification_x")
        self.overlay_notification_y = clicker_settings.get("overlay_notification_y")

        self.build()
        self.apply_clicker_settings(save=False)
        self.prepare_clicker()
        self.refresh_overlay()
        self.monitor_overlay()

    def build(self) -> None:
        container = modern_frame(self, COLORS["bg"], radius=0)
        container.grid(row=0, column=0, sticky="nsew")
        container.columnconfigure(0, weight=1)

        self.ui_text["tools_title"] = tk.Label(container, text=self.tr.t("tools.title"), bg=COLORS["bg"], fg=COLORS["text"], font=("Segoe UI", 24, "bold"))
        self.ui_text["tools_title"].grid(
            row=0, column=0, sticky="w", padx=22, pady=(20, 2)
        )
        tk.Label(container, text="🖱️ Auto Clicker", bg=COLORS["bg"], fg=COLORS["accent_2"], font=("Segoe UI", 11, "bold")).grid(
            row=1, column=0, sticky="w", padx=22, pady=(0, 16)
        )

        card = modern_frame(container, COLORS["card"], radius=24, border=1, border_color=COLORS["line"])
        card.grid(row=2, column=0, sticky="ew", padx=22, pady=(0, 14))
        card.columnconfigure(0, weight=1)

        top = modern_frame(card, COLORS["card"], radius=0)
        top.grid(row=0, column=0, sticky="ew", padx=20, pady=(18, 8))
        top.columnconfigure(0, weight=1)
        self.ui_text["clicker_title"] = tk.Label(top, text=self.tr.t("clicker.title"), bg=COLORS["card"], fg=COLORS["text"], font=("Segoe UI", 20, "bold"))
        self.ui_text["clicker_title"].grid(
            row=0, column=0, sticky="w"
        )
        self.state_badge = tk.Label(top, text=self.tr.t("clicker.off").upper(), bg="#263a55", fg=COLORS["text"], font=("Segoe UI", 10, "bold"), padx=14, pady=6)
        self.state_badge.grid(row=0, column=1, sticky="e")

        status_panel = modern_frame(card, COLORS["soft"], radius=18, border=1, border_color="#213854")
        status_panel.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 18))
        status_panel.columnconfigure(0, weight=1)
        self.ui_text["clicker_status_label"] = tk.Label(status_panel, text=self.tr.t("clicker.status"), bg="#0b1f38", fg=COLORS["accent_2"], font=("Segoe UI", 9, "bold"))
        self.ui_text["clicker_status_label"].grid(
            row=0, column=0, sticky="w", padx=14, pady=(10, 0)
        )
        tk.Label(status_panel, textvariable=self.clicker_status_var, bg="#0b1f38", fg=COLORS["text"], font=("Segoe UI", 13, "bold")).grid(
            row=1, column=0, sticky="w", padx=14, pady=(2, 12)
        )

        controls = modern_frame(card, COLORS["soft"], radius=18, border=1, border_color="#213854")
        controls.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 16))
        controls.columnconfigure(1, weight=1)

        self.add_label(controls, self.tr.t("clicker.key"), 0)
        ttk.Combobox(controls, textvariable=self.hotkey_var, values=list(HOTKEYS.keys()), state="readonly", width=12).grid(
            row=0, column=1, sticky="w", padx=14, pady=10
        )

        self.add_label(controls, self.tr.t("clicker.speed"), 1)
        ttk.Combobox(controls, textvariable=self.speed_var, values=list(SPEEDS.keys()), state="readonly", width=12).grid(
            row=1, column=1, sticky="w", padx=14, pady=10
        )

        self.add_label(controls, self.tr.t("clicker.button"), 2)
        ttk.Combobox(controls, textvariable=self.mouse_button_var, values=list(MOUSE_BUTTONS.keys()), state="readonly", width=12).grid(
            row=2, column=1, sticky="w", padx=14, pady=10
        )

        target_box = modern_frame(card, COLORS["card"], radius=0)
        target_box.grid(row=3, column=0, sticky="ew", padx=20, pady=(0, 16))
        target_box.columnconfigure(0, weight=1)

        self.capture_button = modern_button(
            target_box,
            text=self.tr.t("clicker.capture"),
            command=self.use_foxhole_mode,
            color=COLORS["soft"],
            text_color=COLORS["text"],
            hover="#23486f",
            font=("Segoe UI", 10, "bold"),
        )
        self.capture_button.grid(row=0, column=0, sticky="ew")

        tk.Label(card, textvariable=self.foxhole_status_var, bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI", 9)).grid(
            row=4, column=0, sticky="w", padx=20, pady=(0, 16)
        )

        action_row = modern_frame(card, COLORS["card"], radius=0)
        action_row.grid(row=5, column=0, sticky="ew", padx=20, pady=(0, 20))
        action_row.columnconfigure(0, weight=1)
        action_row.columnconfigure(1, weight=1)

        self.toggle_button = modern_button(
            action_row,
            text=self.tr.t("clicker.pause"),
            command=self.toggle_clicker,
            color=COLORS["accent"],
            text_color=COLORS["accent_text"],
            hover=COLORS["accent_2"],
            height=48,
            font=("Segoe UI", 12, "bold"),
        )
        self.toggle_button.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.save_button = modern_button(
            action_row,
            text=self.tr.t("clicker.save"),
            command=self.save_clicker_settings,
            color=COLORS["soft"],
            text_color=COLORS["text"],
            hover="#23486f",
            height=48,
            font=("Segoe UI", 12, "bold"),
        )
        self.save_button.grid(row=0, column=1, sticky="ew", padx=(8, 0))

    def build_overlay_controls(self, parent: tk.Frame, row: int = 0) -> None:
        overlay_card = modern_frame(parent, COLORS["card"], radius=24, border=1, border_color=COLORS["line"])
        overlay_card.grid(row=row, column=0, sticky="ew", padx=22, pady=(0, 16))
        overlay_card.columnconfigure(1, weight=1)
        tk.Label(overlay_card, text="Overlay", bg=COLORS["card"], fg=COLORS["text"], font=("Segoe UI", 18, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", padx=20, pady=(18, 8)
        )
        tk.Checkbutton(
            overlay_card,
            text=self.tr.t("overlay.show"),
            variable=self.overlay_enabled_var,
            command=self.save_clicker_settings,
            bg=COLORS["card"],
            fg=COLORS["text"],
            selectcolor=COLORS["soft"],
            activebackground=COLORS["card"],
            activeforeground=COLORS["text"],
            font=("Segoe UI", 10, "bold"),
        ).grid(row=1, column=0, columnspan=2, sticky="w", padx=20, pady=(0, 8))
        self.add_label(overlay_card, self.tr.t("overlay.hotkey"), 2)
        overlay_hotkey_combo = ttk.Combobox(overlay_card, textvariable=self.overlay_hotkey_var, values=list(HOTKEYS.keys()), state="readonly", width=12)
        overlay_hotkey_combo.grid(row=2, column=1, sticky="w", padx=14, pady=8)
        overlay_hotkey_combo.bind("<<ComboboxSelected>>", lambda _event: self.save_clicker_settings())
        self.add_label(overlay_card, self.tr.t("overlay.color"), 3)
        self.overlay_color_display_var.set(self.overlay_color_label(self.overlay_color_var.get()))
        overlay_color_combo = ttk.Combobox(
            overlay_card,
            textvariable=self.overlay_color_display_var,
            values=self.overlay_color_labels(),
            state="readonly",
            width=12,
        )
        overlay_color_combo.grid(row=3, column=1, sticky="w", padx=14, pady=8)
        overlay_color_combo.bind("<<ComboboxSelected>>", lambda _event: self.save_overlay_color_selection())
        checks = modern_frame(overlay_card, COLORS["card"], radius=0)
        checks.grid(row=4, column=0, columnspan=2, sticky="ew", padx=20, pady=(4, 18))
        for index, (label, variable) in enumerate(
            (
                (self.tr.t("overlay.profile"), self.overlay_profile_var),
                ("Auto Clicker", self.overlay_clicker_var),
                (self.tr.t("overlay.target"), self.overlay_target_var),
                (self.tr.t("overlay.upload_notification"), self.overlay_notification_var),
            )
        ):
            tk.Checkbutton(
                checks,
                text=label,
                variable=variable,
                command=self.save_clicker_settings,
                bg=COLORS["card"],
                fg=COLORS["text"],
                selectcolor=COLORS["soft"],
                activebackground=COLORS["card"],
                activeforeground=COLORS["text"],
                font=("Segoe UI", 9),
            ).grid(row=0, column=index, sticky="w", padx=(0, 16))
        action_row = modern_frame(overlay_card, COLORS["card"], radius=0)
        action_row.grid(row=5, column=0, columnspan=2, sticky="ew", padx=20, pady=(0, 20))
        action_row.columnconfigure(0, weight=1)
        modern_button(
            action_row,
            text=self.tr.t("overlay.adjust"),
            command=self.open_overlay_adjuster,
            color=COLORS["soft"],
            text_color=COLORS["text"],
            hover="#23486f",
            height=42,
        ).grid(row=0, column=0, sticky="ew")

    def overlay_color_label(self, color_name: str) -> str:
        return self.tr.t(OVERLAY_COLOR_LABEL_KEYS.get(color_name, "overlay.color_blue"))

    def overlay_color_labels(self) -> list[str]:
        return [self.overlay_color_label(name) for name in OVERLAY_COLORS]

    def overlay_color_from_label(self, label: str) -> str:
        for color_name in OVERLAY_COLORS:
            if self.overlay_color_label(color_name) == label:
                return color_name
        return self.overlay_color_var.get() if self.overlay_color_var.get() in OVERLAY_COLORS else "Azul"

    def save_overlay_color_selection(self) -> None:
        self.overlay_color_var.set(self.overlay_color_from_label(self.overlay_color_display_var.get()))
        self.overlay_color_display_var.set(self.overlay_color_label(self.overlay_color_var.get()))
        self.save_clicker_settings()

    def add_label(self, parent: tk.Frame, text: str, row: int) -> None:
        label = tk.Label(parent, text=text, bg=widget_color(parent, COLORS["card"]), fg=COLORS["muted"], font=("Segoe UI", 10, "bold"))
        label.grid(
            row=row, column=0, sticky="w", padx=14, pady=10
        )
        label_keys = {
            self.tr.t("clicker.key"): "clicker_key",
            self.tr.t("clicker.speed"): "clicker_speed",
            self.tr.t("clicker.button"): "clicker_button",
            self.tr.t("overlay.hotkey"): "overlay_hotkey",
            self.tr.t("overlay.color"): "overlay_color",
        }
        key = label_keys.get(text)
        if key:
            self.ui_text[key] = label

    def selected_interval(self) -> float:
        return SPEEDS.get(self.speed_var.get(), 0.10)

    def apply_clicker_settings(self, save: bool = True) -> None:
        interval = self.selected_interval()
        self.clicker.configure(self.hotkey_var.get(), self.mouse_button_var.get(), interval)
        self.apply_overlay_settings()
        if save:
            self.write_settings(interval)

    def save_clicker_settings(self) -> None:
        self.apply_clicker_settings(save=True)
        self.flash_status(self.tr.t("clicker.saved"))

    def write_settings(self, interval: float) -> None:
        self.settings = load_settings()
        self.settings["auto_clicker"] = {
            "hotkey": self.hotkey_var.get(),
            "mouse_button": self.mouse_button_var.get(),
            "interval": interval,
            "mode": "Foxhole",
            "overlay_enabled": self.overlay_enabled_var.get(),
            "overlay_hotkey": self.overlay_hotkey_var.get(),
            "overlay_color": self.overlay_color_var.get(),
            "overlay_show_profile": self.overlay_profile_var.get(),
            "overlay_show_clicker": self.overlay_clicker_var.get(),
            "overlay_show_target": self.overlay_target_var.get(),
            "overlay_notification_enabled": self.overlay_notification_var.get(),
            "overlay_panel_x": self.overlay_panel_x,
            "overlay_panel_y": self.overlay_panel_y,
            "overlay_notification_x": self.overlay_notification_x,
            "overlay_notification_y": self.overlay_notification_y,
        }
        save_settings(self.settings)

    def apply_overlay_settings(self) -> None:
        self.overlay.configure(
            enabled_by_hotkey=self.overlay_enabled_var.get(),
            color_name=self.overlay_color_var.get(),
            show_profile=self.overlay_profile_var.get(),
            show_clicker=self.overlay_clicker_var.get(),
            show_target=self.overlay_target_var.get(),
            panel_x=self.overlay_panel_x,
            panel_y=self.overlay_panel_y,
            notification_x=self.overlay_notification_x,
            notification_y=self.overlay_notification_y,
        )

    def open_overlay_adjuster(self) -> None:
        self.apply_overlay_settings()
        self.clicker.use_foxhole_window(quiet=True)
        self.overlay.begin_adjust_positions(self.save_overlay_positions, self.remove_adjust_overlay)
        self.flash_status(self.tr.t("overlay.adjust_hint"))

    def save_overlay_positions(self, panel_position: tuple[int, int], notification_position: tuple[int, int]) -> None:
        self.overlay_panel_x, self.overlay_panel_y = panel_position
        self.overlay_notification_x, self.overlay_notification_y = notification_position
        self.write_settings(self.selected_interval())
        self.flash_status(self.tr.t("overlay.positions_saved"))

    def remove_adjust_overlay(self, overlay_name: str) -> None:
        if overlay_name == "panel":
            self.overlay_enabled_var.set(False)
        elif overlay_name == "notification":
            self.overlay_notification_var.set(False)
        self.write_settings(self.selected_interval())
        self.flash_status(self.tr.t("overlay.removed"))

    def notify_stockpile_success(self, text: str) -> None:
        if not self.overlay_notification_var.get():
            return
        self.overlay.show_success_notification(text)

    def is_foxhole_overlay_context(self) -> bool:
        if not self.clicker.target_hwnd or not self.clicker.user32.IsWindow(self.clicker.target_hwnd):
            self.clicker.use_foxhole_window(quiet=True)
        if not self.clicker.target_hwnd or not self.clicker.user32.IsWindow(self.clicker.target_hwnd):
            return False
        foreground = self.clicker.user32.GetForegroundWindow()
        if foreground and (
            foreground == self.clicker.target_hwnd
            or self.clicker.is_same_process_window(foreground, self.clicker.target_hwnd)
            or self.clicker.is_foxhole_window(foreground)
        ):
            return True
        return False

    def use_foxhole_mode(self) -> None:
        title = self.clicker.use_foxhole_window()
        self.foxhole_status_var.set(title)
        self.apply_clicker_settings(save=True)

    def prepare_clicker(self) -> None:
        self.apply_clicker_settings(save=True)
        title = self.clicker.use_foxhole_window()
        self.foxhole_status_var.set(title)
        self.clicker.pause()
        self.update_state()

    def toggle_clicker(self) -> None:
        self.apply_clicker_settings(save=True)
        self.clicker.toggle()
        self.update_state()

    def update_state(self) -> None:
        if self.clicker.enabled:
            self.state_badge.configure(text=self.tr.t("clicker.on_badge"), bg="#145f46", fg=COLORS["text"])
            self.toggle_button.configure(text=self.tr.t("clicker.pause"))
            configure_button_color(self.toggle_button, COLORS["accent"], COLORS["accent_text"])
        else:
            self.state_badge.configure(text=self.tr.t("clicker.paused_badge"), bg="#263a55", fg=COLORS["text"])
            self.toggle_button.configure(text=self.tr.t("clicker.resume"))
            configure_button_color(self.toggle_button, COLORS["card_2"], COLORS["text"])
        self.refresh_overlay()

    def refresh_language(self, translator: Translator) -> None:
        self.tr = translator
        overlay_was_enabled = self.overlay_enabled_var.get()
        notification_was_enabled = self.overlay_notification_var.get()
        panel_position = (self.overlay_panel_x, self.overlay_panel_y)
        notification_position = (self.overlay_notification_x, self.overlay_notification_y)
        self.ui_text = {}
        for child in self.winfo_children():
            child.destroy()
        self.overlay_enabled_var.set(overlay_was_enabled)
        self.overlay_notification_var.set(notification_was_enabled)
        self.overlay_panel_x, self.overlay_panel_y = panel_position
        self.overlay_notification_x, self.overlay_notification_y = notification_position
        self.overlay_color_display_var.set(self.overlay_color_label(self.overlay_color_var.get()))
        self.build()
        self.apply_clicker_settings(save=False)
        self.update_state()

    def refresh_overlay(self) -> None:
        profile_name = self.overlay_profile_name()
        self.overlay.update(
            self.clicker.enabled,
            self.hotkey_var.get(),
            self.selected_interval(),
            profile_name,
            self.clicker.target_title or "Foxhole",
        )
        self.overlay.set_visible(self.should_show_overlay())

    def overlay_profile_name(self) -> str:
        app = self.winfo_toplevel()
        profile = getattr(app, "profile", None)
        if profile and getattr(profile, "persona_name", None):
            return profile.persona_name
        if profile and getattr(profile, "account_name", None):
            return profile.account_name
        return self.tr.t("user.unknown")

    def should_show_overlay(self) -> bool:
        if not self.overlay_enabled_var.get():
            self.log_overlay_reason("desativado nas configuracoes")
            return False
        if not self.clicker.target_hwnd or not self.clicker.user32.IsWindow(self.clicker.target_hwnd):
            now = time.monotonic()
            if now - self.last_overlay_find_attempt >= 5:
                self.last_overlay_find_attempt = now
                self.clicker.use_foxhole_window(quiet=True)
        if not self.clicker.target_hwnd or not self.clicker.user32.IsWindow(self.clicker.target_hwnd):
            self.log_overlay_reason("Foxhole nao capturado/encontrado")
            return False

        foreground = self.clicker.user32.GetForegroundWindow()
        if foreground and (
            foreground == self.clicker.target_hwnd
            or self.clicker.is_same_process_window(foreground, self.clicker.target_hwnd)
            or self.clicker.is_foxhole_window(foreground)
        ):
            self.last_overlay_reason = ""
            return True

        point = POINT()
        if self.clicker.user32.GetCursorPos(ctypes.byref(point)):
            cursor_hwnd = self.clicker.user32.WindowFromPoint(point)
            if cursor_hwnd and (
                cursor_hwnd == self.clicker.target_hwnd
                or self.clicker.is_same_process_window(cursor_hwnd, self.clicker.target_hwnd)
                or self.clicker.is_foxhole_window(cursor_hwnd)
            ):
                self.last_overlay_reason = ""
                return True

        self.log_overlay_reason("Foxhole nao esta em foco")
        return False

    def log_overlay_reason(self, reason: str) -> None:
        if reason == self.last_overlay_reason:
            return
        self.last_overlay_reason = reason
        print(f"[Overlay] escondido: {reason}", flush=True)

    def monitor_overlay(self) -> None:
        hotkey = self.overlay_hotkey_var.get()
        vk = HOTKEYS.get(hotkey, HOTKEYS["F8"])
        is_down = bool(self.clicker.user32.GetAsyncKeyState(vk) & 0x8000)
        if is_down and not self.overlay_hotkey_was_down:
            self.overlay_enabled_var.set(not self.overlay_enabled_var.get())
            self.save_clicker_settings()
        self.overlay_hotkey_was_down = is_down
        self.refresh_overlay()
        self.after(250, self.monitor_overlay)

    def flash_status(self, text: str) -> None:
        self.clicker_status_var.set(text)
        self.after(1500, lambda: self.set_clicker_status(self.clicker.status_text()))

    def set_clicker_status(self, text: str) -> None:
        self.after(0, self.clicker_status_var.set, text)
        self.after(0, self.update_state)

    def stop(self) -> None:
        self.clicker.stop()
        self.overlay.destroy()


class OverlayCategory(ttk.Frame):
    def __init__(self, parent: ttk.Widget, controller: FunctionsCategory, translator: Translator | None = None) -> None:
        super().__init__(parent, style="Panel.TFrame")
        self.controller = controller
        self.tr = translator or Translator()
        self.ui_text: dict[str, tk.Widget] = {}
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.build()

    def build(self) -> None:
        container = modern_frame(self, COLORS["bg"], radius=0)
        container.grid(row=0, column=0, sticky="nsew")
        container.columnconfigure(0, weight=1)

        self.ui_text["title"] = tk.Label(container, text="Overlay", bg=COLORS["bg"], fg=COLORS["text"], font=("Segoe UI", 24, "bold"))
        self.ui_text["title"].grid(
            row=0, column=0, sticky="w", padx=22, pady=(20, 2)
        )
        self.ui_text["subtitle"] = tk.Label(
            container,
            text=self.tr.t("overlay.subtitle"),
            bg=COLORS["bg"],
            fg=COLORS["accent_2"],
            font=("Segoe UI", 11, "bold"),
        )
        self.ui_text["subtitle"].grid(row=1, column=0, sticky="w", padx=22, pady=(0, 16))

        self.controller.build_overlay_controls(container, row=2)

    def refresh_language(self, translator: Translator) -> None:
        self.tr = translator
        self.ui_text = {}
        for child in self.winfo_children():
            child.destroy()
        self.build()


class SettingsCategory(ttk.Frame):
    def __init__(self, parent: ttk.Widget, controller: FunctionsCategory, translator: Translator | None = None) -> None:
        super().__init__(parent, style="Panel.TFrame")
        self.controller = controller
        self.tr = translator or Translator()
        settings = load_settings()
        app_settings = settings.get("app", {})
        self.start_with_windows_var = tk.BooleanVar(value=bool(app_settings.get("start_with_windows", False)))
        self.close_action_var = tk.StringVar(value=str(app_settings.get("close_action", "ask")))
        self.stockpile_sound_enabled_var = tk.BooleanVar(value=bool(app_settings.get("stockpile_sound_enabled", True)))
        self.squadlock_sound_enabled_var = tk.BooleanVar(value=bool(app_settings.get("squadlock_sound_enabled", True)))
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.build()

    def build(self) -> None:
        outer = modern_frame(self, COLORS["bg"], radius=0)
        outer.grid(row=0, column=0, sticky="nsew")
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(0, weight=1)

        canvas = tk.Canvas(outer, bg=COLORS["bg"], highlightthickness=0)
        canvas.grid(row=0, column=0, sticky="nsew")
        if ctk is not None:
            scrollbar = ctk.CTkScrollbar(
                outer,
                orientation="vertical",
                command=canvas.yview,
                width=10,
                fg_color=COLORS["bg"],
                button_color=COLORS["card_2"],
                button_hover_color=COLORS["accent"],
            )
        else:
            scrollbar = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview, style="Vertical.TScrollbar")
        scrollbar.grid(row=0, column=1, sticky="ns")
        canvas.configure(yscrollcommand=scrollbar.set)

        container = modern_frame(canvas, COLORS["bg"], radius=0)
        window_id = canvas.create_window((0, 0), window=container, anchor="nw")
        container.bind("<Configure>", lambda _event: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda event: canvas.itemconfigure(window_id, width=event.width))
        container.columnconfigure(0, weight=1)

        tk.Label(container, text=self.tr.t("settings.title"), bg=COLORS["bg"], fg=COLORS["text"], font=("Segoe UI", 24, "bold")).grid(
            row=0, column=0, sticky="w", padx=22, pady=(20, 2)
        )
        tk.Label(
            container,
            text=self.tr.t("settings.subtitle"),
            bg=COLORS["bg"],
            fg=COLORS["accent_2"],
            font=("Segoe UI", 11, "bold"),
        ).grid(row=1, column=0, sticky="w", padx=22, pady=(0, 16))

        app_card = modern_frame(container, COLORS["card"], radius=18, border=1, border_color=COLORS["line"])
        app_card.grid(row=2, column=0, sticky="ew", padx=22, pady=(0, 16))
        app_card.columnconfigure(0, weight=1)
        tk.Label(app_card, text=self.tr.t("settings.app_title"), bg=COLORS["card"], fg=COLORS["text"], font=("Segoe UI", 18, "bold")).grid(
            row=0, column=0, sticky="w", padx=20, pady=(18, 4)
        )
        tk.Checkbutton(
            app_card,
            text=self.tr.t("settings.start_windows"),
            variable=self.start_with_windows_var,
            command=self.save_app_settings,
            bg=COLORS["card"],
            fg=COLORS["text"],
            selectcolor=COLORS["soft"],
            activebackground=COLORS["card"],
            activeforeground=COLORS["text"],
            font=("Segoe UI", 10, "bold"),
        ).grid(row=1, column=0, sticky="w", padx=20, pady=(8, 4))

        close_row = modern_frame(app_card, COLORS["card"], radius=0)
        close_row.grid(row=2, column=0, sticky="ew", padx=20, pady=(10, 18))
        tk.Label(close_row, text=self.tr.t("settings.close_action"), bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI", 10, "bold")).grid(
            row=0, column=0, sticky="w", padx=(0, 16)
        )
        for index, (value, label_key) in enumerate(
            (
                ("ask", "settings.close_ask"),
                ("tray", "settings.close_tray"),
                ("exit", "settings.close_exit"),
            ),
            start=1,
        ):
            tk.Radiobutton(
                close_row,
                text=self.tr.t(label_key),
                value=value,
                variable=self.close_action_var,
                command=self.save_app_settings,
                bg=COLORS["card"],
                fg=COLORS["text"],
                selectcolor=COLORS["soft"],
                activebackground=COLORS["card"],
                activeforeground=COLORS["text"],
                font=("Segoe UI", 9, "bold"),
            ).grid(row=0, column=index, sticky="w", padx=(0, 14))

        self.controller.build_overlay_controls(container, row=3)

        sound_card = modern_frame(container, COLORS["card"], radius=24, border=1, border_color=COLORS["line"])
        sound_card.grid(row=4, column=0, sticky="ew", padx=22, pady=(0, 16))
        tk.Label(sound_card, text=self.tr.t("settings.sound_title"), bg=COLORS["card"], fg=COLORS["text"], font=("Segoe UI", 18, "bold")).grid(
            row=0, column=0, sticky="w", padx=20, pady=(18, 4)
        )
        tk.Label(
            sound_card,
            text=self.tr.t("settings.sound_body"),
            bg=COLORS["card"],
            fg=COLORS["muted"],
            font=("Segoe UI", 10),
            wraplength=760,
            justify="left",
        ).grid(row=1, column=0, sticky="w", padx=20, pady=(0, 18))
        tk.Checkbutton(
            sound_card,
            text=self.tr.t("settings.sound_stockpile"),
            variable=self.stockpile_sound_enabled_var,
            command=self.save_app_settings,
            bg=COLORS["card"],
            fg=COLORS["text"],
            selectcolor=COLORS["soft"],
            activebackground=COLORS["card"],
            activeforeground=COLORS["text"],
            font=("Segoe UI", 10, "bold"),
        ).grid(row=2, column=0, sticky="w", padx=20, pady=(0, 8))
        tk.Checkbutton(
            sound_card,
            text=self.tr.t("settings.sound_squadlock"),
            variable=self.squadlock_sound_enabled_var,
            command=self.save_app_settings,
            bg=COLORS["card"],
            fg=COLORS["text"],
            selectcolor=COLORS["soft"],
            activebackground=COLORS["card"],
            activeforeground=COLORS["text"],
            font=("Segoe UI", 10, "bold"),
        ).grid(row=3, column=0, sticky="w", padx=20, pady=(0, 18))
        self.bind_mousewheel_recursive(outer, canvas)

    def bind_mousewheel_recursive(self, widget: tk.Widget, canvas: tk.Canvas) -> None:
        def on_mousewheel(event) -> str:
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            return "break"

        widget.bind("<MouseWheel>", on_mousewheel, add="+")
        for child in widget.winfo_children():
            self.bind_mousewheel_recursive(child, canvas)

    def save_app_settings(self) -> None:
        settings = load_settings()
        app_settings = settings.setdefault("app", {})
        app_settings["start_with_windows"] = self.start_with_windows_var.get()
        app_settings["startup_prompted"] = True
        app_settings["close_action"] = self.close_action_var.get()
        app_settings["stockpile_sound_enabled"] = self.stockpile_sound_enabled_var.get()
        app_settings["squadlock_sound_enabled"] = self.squadlock_sound_enabled_var.get()
        save_settings(settings)
        app = self.winfo_toplevel()
        if hasattr(app, "set_start_with_windows"):
            try:
                app.set_start_with_windows(self.start_with_windows_var.get())
            except Exception as exc:
                print(f"[Settings] startup update failed: {exc}", flush=True)

    def refresh_language(self, translator: Translator) -> None:
        self.tr = translator
        for child in self.winfo_children():
            child.destroy()
        self.build()
