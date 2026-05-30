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

GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
WS_EX_TOOLWINDOW = 0x00000080


def modern_frame(parent, color: str, radius: int = 18, border: int = 0, border_color: str | None = None):
    if ctk is not None:
        return ctk.CTkFrame(
            parent,
            fg_color=color,
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
        self.enabled_by_hotkey = True
        self.show_profile = True
        self.show_clicker = True
        self.show_target = True
        self.palette = OVERLAY_COLORS["Azul"]
        self.window = ctk.CTkToplevel(parent) if ctk is not None else tk.Toplevel(parent)
        self.window.withdraw()
        self.window.overrideredirect(True)
        self.window.attributes("-topmost", True)
        self.window.attributes("-alpha", 0.84)
        configure_surface(self.window, self.palette["bg"])

        self.shell = modern_frame(self.window, self.palette["panel"], radius=18, border=1, border_color=self.palette["accent"])
        self.shell.pack(fill="both", expand=True, padx=6, pady=6)

        self.status_label = tk.Label(
            self.shell,
            text="AUTO CLICKER",
            bg=self.palette["panel"],
            fg=self.palette["accent"],
            font=("Segoe UI", 9, "bold"),
            padx=14,
            pady=4,
        )
        self.status_label.pack(fill="x")
        self.profile_label = tk.Label(
            self.shell,
            text="Perfil",
            bg=self.palette["panel"],
            fg=COLORS["muted"],
            font=("Segoe UI", 9, "bold"),
            padx=14,
            pady=2,
        )
        self.profile_label.pack(fill="x")
        self.detail_label = tk.Label(
            self.shell,
            text="Pausado",
            bg=self.palette["panel"],
            fg=COLORS["text"],
            font=("Segoe UI", 10, "bold"),
            padx=14,
            pady=4,
        )
        self.detail_label.pack(fill="x")
        self.target_label = tk.Label(
            self.shell,
            text="Foxhole",
            bg=self.palette["panel"],
            fg=COLORS["muted"],
            font=("Segoe UI", 9),
            padx=14,
            pady=4,
        )
        self.target_label.pack(fill="x")

        self.position()
        self.window.deiconify()
        self.window.after(150, self.make_click_through)

    def position(self) -> None:
        self.window.update_idletasks()
        width = 240
        height = 96
        screen_width = self.window.winfo_screenwidth()
        self.window.geometry(f"{width}x{height}+{screen_width - width - 24}+24")

    def make_click_through(self) -> None:
        try:
            hwnd = self.window.winfo_id()
            user32 = ctypes.windll.user32
            current_style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            user32.SetWindowLongW(hwnd, GWL_EXSTYLE, current_style | WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOOLWINDOW)
        except Exception:
            pass

    def configure(self, enabled_by_hotkey: bool, color_name: str, show_profile: bool, show_clicker: bool, show_target: bool) -> None:
        self.enabled_by_hotkey = enabled_by_hotkey
        self.show_profile = show_profile
        self.show_clicker = show_clicker
        self.show_target = show_target
        self.palette = OVERLAY_COLORS.get(color_name, OVERLAY_COLORS["Azul"])
        configure_surface(self.window, self.palette["bg"])
        if ctk is not None:
            self.shell.configure(fg_color=self.palette["panel"], border_color=self.palette["accent"])
        else:
            self.shell.configure(bg=self.palette["panel"], highlightbackground=self.palette["accent"])
        for label in (self.status_label, self.profile_label, self.detail_label, self.target_label):
            label.configure(bg=self.palette["panel"])
        self.status_label.configure(fg=self.palette["accent"])

    def set_visible(self, visible: bool) -> None:
        if not self.window.winfo_exists():
            return
        if visible:
            self.window.attributes("-topmost", True)
            self.position()
            self.window.deiconify()
        else:
            self.window.withdraw()

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
        if self.window.winfo_exists():
            self.window.destroy()


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
        self.overlay_hotkey_was_down = False
        self.last_overlay_reason = ""
        self.last_overlay_find_attempt = 0.0

        self.hotkey_var = tk.StringVar(value=clicker_settings.get("hotkey", "F3"))
        self.mouse_button_var = tk.StringVar(value=clicker_settings.get("mouse_button", "Esquerdo"))
        self.speed_var = tk.StringVar(value=saved_speed)
        self.overlay_enabled_var = tk.BooleanVar(value=bool(clicker_settings.get("overlay_enabled", True)))
        self.overlay_hotkey_var = tk.StringVar(value=clicker_settings.get("overlay_hotkey", "F8"))
        self.overlay_color_var = tk.StringVar(value=clicker_settings.get("overlay_color", "Azul"))
        self.overlay_profile_var = tk.BooleanVar(value=bool(clicker_settings.get("overlay_show_profile", True)))
        self.overlay_clicker_var = tk.BooleanVar(value=bool(clicker_settings.get("overlay_show_clicker", True)))
        self.overlay_target_var = tk.BooleanVar(value=bool(clicker_settings.get("overlay_show_target", True)))

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
        overlay_color_combo = ttk.Combobox(overlay_card, textvariable=self.overlay_color_var, values=list(OVERLAY_COLORS.keys()), state="readonly", width=12)
        overlay_color_combo.grid(row=3, column=1, sticky="w", padx=14, pady=8)
        overlay_color_combo.bind("<<ComboboxSelected>>", lambda _event: self.save_clicker_settings())
        checks = modern_frame(overlay_card, COLORS["card"], radius=0)
        checks.grid(row=4, column=0, columnspan=2, sticky="ew", padx=20, pady=(4, 18))
        for index, (label, variable) in enumerate(
            (
                (self.tr.t("overlay.profile"), self.overlay_profile_var),
                ("Auto Clicker", self.overlay_clicker_var),
                (self.tr.t("overlay.target"), self.overlay_target_var),
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
        }
        save_settings(self.settings)

    def apply_overlay_settings(self) -> None:
        self.overlay.configure(
            enabled_by_hotkey=self.overlay_enabled_var.get(),
            color_name=self.overlay_color_var.get(),
            show_profile=self.overlay_profile_var.get(),
            show_clicker=self.overlay_clicker_var.get(),
            show_target=self.overlay_target_var.get(),
        )

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
        self.ui_text = {}
        for child in self.winfo_children():
            child.destroy()
        self.build()
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
