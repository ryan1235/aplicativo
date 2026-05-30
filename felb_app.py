import ctypes
import base64
from datetime import datetime, timezone
import os
from pathlib import Path
import sys
import threading
import tkinter as tk
from tkinter import messagebox, ttk
import urllib.request
import math

PACKAGE_PATHS = [
    Path(__file__).resolve().parent / "deps",
    Path.home() / "AppData" / "Roaming" / "Python" / "Python314" / "site-packages",
    Path.home() / "AppData" / "Local" / "Python" / "pythoncore-3.14-64" / "Lib" / "site-packages",
]
for package_path in PACKAGE_PATHS:
    if package_path.exists():
        sys.path.insert(0, str(package_path))

try:
    import customtkinter as ctk
    if not hasattr(ctk, "set_appearance_mode"):
        ctk = None
except Exception:  # pragma: no cover - optional visual upgrade.
    ctk = None

try:
    import pystray
    from PIL import Image, ImageDraw
except Exception:  # pragma: no cover - tray is optional until dependencies are installed.
    pystray = None
    Image = None
    ImageDraw = None

from app_update import check_latest_release, download_update, launch_updater
from functions_category import FunctionsCategory, OverlayCategory
from i18n import SUPPORTED_LANGUAGES, Translator
from settings_store import load_settings, save_settings, selected_language
from steam_profile import SteamProfile, get_local_steam_profile
from stockpile_category import StockpileCategory


APP_TITLE = "GG Coalition"
APP_VERSION = "0.1.0"
UPDATE_REPO = ""  # Exemplo: "seu-usuario/gg-coalition"
FOXHOLE_APP_ID = "505460"
SIDEBAR_WIDTH = 302
BASE_DIR = Path(__file__).resolve().parent
ICON_PATH = BASE_DIR / "img" / "ggimege.gif"
WALLPAPER_PATH = BASE_DIR / "img" / "wallpeper.png"
FOXHOLE_PROCESS_NAMES = ("war-win64-shipping.exe", "foxhole.exe")
FOXHOLE_PATH_HINTS = ("\\steamapps\\common\\foxhole\\", "/steamapps/common/foxhole/")
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
MAX_SPLASH_FRAMES = 36

if ctk is not None:
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

AppBase = ctk.CTk if ctk is not None else tk.Tk


def tk_image_path(path: Path) -> str:
    return path.resolve().as_posix()


def tk_photo_from_path(path: Path, *, format: str | None = None) -> tk.PhotoImage:
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    if format:
        return tk.PhotoImage(data=encoded, format=format)
    return tk.PhotoImage(data=encoded)


class FILETIME(ctypes.Structure):
    _fields_ = [("dwLowDateTime", ctypes.c_ulong), ("dwHighDateTime", ctypes.c_ulong)]

COLORS = {
    "bg": "#070b16",
    "sidebar": "#0a1020",
    "panel": "#0d1729",
    "card": "#111c31",
    "card_2": "#1d3353",
    "text": "#edf6ff",
    "muted": "#99abc4",
    "accent": "#5eead4",
    "accent_2": "#8ab4ff",
    "line": "#2d496f",
    "soft": "#0e1a2d",
    "hover": "#172943",
    "glass": "#0c1628",
    "glass_2": "#15253d",
    "danger": "#ff7a90",
    "accent_text": "#041014",
}


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
    width: int = 120,
    height: int = 38,
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
            width=width,
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


class FelbApp(AppBase):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"{APP_TITLE} - {self.tr.t('app.subtitle') if hasattr(self, 'tr') else 'Warden Command'}")
        self.geometry("1100x680")
        self.minsize(900, 580)
        configure_surface(self, COLORS["bg"])

        self.settings = load_settings()
        self.tr = Translator(selected_language(self.settings))
        self.title(f"{APP_TITLE} - {self.tr.t('app.subtitle')}")
        self.profile = SteamProfile()
        self.user_active = False
        self.user_status_var = tk.StringVar(value=self.tr.t("status.checking_user"))
        self.foxhole_running = False
        self.foxhole_status_var = tk.StringVar(value=self.tr.t("status.checking_foxhole"))
        self.avatar_image: tk.PhotoImage | None = None
        self.app_icon_image: tk.PhotoImage | None = None
        self.splash_logo_image: tk.PhotoImage | None = None
        self.splash_logo_frames: list[tuple[tk.PhotoImage, int]] = []
        self.sidebar_logo_frames: list[tuple[tk.PhotoImage, int]] = []
        self.splash_frame_index = 0
        self.sidebar_logo_frame_index = 0
        self.splash_animation_job: str | None = None
        self.sidebar_logo_animation_job: str | None = None
        self.flag_images: dict[str, tk.PhotoImage] = {}
        self.wallpaper_source = None
        self.wallpaper_photo: tk.PhotoImage | None = None
        self.wallpaper_resize_job: str | None = None
        self.functions_page: FunctionsCategory | None = None
        self.overlay_page: OverlayCategory | None = None
        self.stockpile_page: StockpileCategory | None = None
        self.sidebar: tk.Frame | None = None
        self.sidebar_canvas: tk.Canvas | None = None
        self.sidebar_inner: tk.Frame | None = None
        self.menu_button: tk.Button | None = None
        self.sidebar_visible = False
        self.pages: dict[str, tk.Widget] = {}
        self.nav_buttons: dict[str, tk.Button] = {}
        self.language_buttons: dict[str, tk.Button] = {}
        self.ui_text: dict[str, tk.Widget] = {}
        self.tray_icon = None
        self.tray_running = False
        self.hidden_to_tray = False

        self.style = ttk.Style(self)
        self.style.theme_use("clam")
        self.configure_styles()
        self.load_app_icon()
        self.show_loading_screen()
        self.build_ui()
        self.update_loading(self.tr.t("loading.steam"))
        self.refresh_steam_profile()
        self.update_loading(self.tr.t("loading.foxhole"))
        self.refresh_foxhole_status()
        self.update_user_status()
        self.update_loading(self.tr.t("loading.ready"))
        self.show_page("inicio")
        self.after(650, self.finish_loading)
        self.after(1800, self.check_for_updates)
        self.protocol("WM_DELETE_WINDOW", self.request_close)
        self.bind("<Unmap>", self.on_unmap, add="+")

    def load_app_icon(self) -> None:
        if not ICON_PATH.exists():
            return
        try:
            self.app_icon_image = tk_photo_from_path(ICON_PATH)
            self.iconphoto(True, self.app_icon_image)
        except tk.TclError:
            self.app_icon_image = None

    def show_loading_screen(self) -> None:
        self.withdraw()
        splash = ctk.CTkToplevel(self) if ctk is not None else tk.Toplevel(self)
        splash.overrideredirect(True)
        configure_surface(splash, COLORS["bg"])
        splash.geometry("460x330")
        splash.update_idletasks()
        x = (splash.winfo_screenwidth() - 460) // 2
        y = (splash.winfo_screenheight() - 330) // 2
        splash.geometry(f"460x330+{x}+{y}")

        panel = modern_frame(splash, COLORS["card"], radius=24, border=1, border_color=COLORS["line"])
        panel.pack(fill="both", expand=True, padx=18, pady=18)
        self.splash_logo_frames = self.load_splash_frames()
        self.splash_logo_image = self.splash_logo_frames[0][0] if self.splash_logo_frames else self.load_splash_logo()
        if self.splash_logo_image:
            self.splash_logo_label = tk.Label(panel, image=self.splash_logo_image, bg=COLORS["card"])
            self.splash_logo_label.pack(pady=(24, 10))
            self.animate_splash_logo()
        tk.Label(panel, text=APP_TITLE, bg=COLORS["card"], fg=COLORS["text"], font=("Segoe UI", 28, "bold")).pack()
        tk.Label(panel, text=self.tr.t("loading.prepare"), bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI", 11)).pack(pady=(2, 22))
        self.loading_label = tk.Label(panel, text=self.tr.t("loading.starting"), bg=COLORS["card"], fg=COLORS["accent_2"], font=("Segoe UI", 10, "bold"))
        self.loading_label.pack()
        progress = ttk.Progressbar(panel, mode="indeterminate", length=260)
        progress.pack(pady=(14, 0))
        progress.start(12)
        self.loading_screen = splash
        self.update()

    def load_splash_frames(self, size: int = 108) -> list[tuple[tk.PhotoImage, int]]:
        if not ICON_PATH.exists():
            return []
        frames: list[tuple[tk.PhotoImage, int]] = []
        try:
            from PIL import Image, ImageTk, ImageSequence

            with Image.open(ICON_PATH) as image:
                for index, frame in enumerate(ImageSequence.Iterator(image)):
                    if index >= MAX_SPLASH_FRAMES:
                        break
                    frame = frame.convert("RGBA")
                    frame.thumbnail((size, size))
                    frames.append((ImageTk.PhotoImage(frame), max(45, int(frame.info.get("duration", 85)))))
        except Exception:
            encoded = base64.b64encode(ICON_PATH.read_bytes()).decode("ascii")
            index = 0
            while index < MAX_SPLASH_FRAMES:
                try:
                    frame = tk.PhotoImage(data=encoded, format=f"gif -index {index}")
                except tk.TclError:
                    break
                scale = max(1, math.ceil(max(frame.width() / size, frame.height() / size)))
                if scale > 1:
                    frame = frame.subsample(scale, scale)
                frames.append((frame, 85))
                index += 1
        return frames

    def load_splash_logo(self) -> tk.PhotoImage | None:
        if not ICON_PATH.exists():
            return None
        try:
            from PIL import Image, ImageTk

            image = Image.open(ICON_PATH).convert("RGBA")
            image.thumbnail((92, 92))
            return ImageTk.PhotoImage(image)
        except Exception:
            try:
                return tk_photo_from_path(ICON_PATH).subsample(5, 5)
            except tk.TclError:
                return None

    def animate_splash_logo(self) -> None:
        if not self.splash_logo_frames or not hasattr(self, "splash_logo_label"):
            return
        frame, delay = self.splash_logo_frames[self.splash_frame_index]
        self.splash_logo_label.configure(image=frame)
        self.splash_logo_image = frame
        self.splash_frame_index = (self.splash_frame_index + 1) % len(self.splash_logo_frames)
        self.splash_animation_job = self.after(delay, self.animate_splash_logo)

    def update_loading(self, text: str) -> None:
        if hasattr(self, "loading_label"):
            self.loading_label.configure(text=text)
            self.update()

    def finish_loading(self) -> None:
        if self.splash_animation_job:
            self.after_cancel(self.splash_animation_job)
            self.splash_animation_job = None
        if hasattr(self, "loading_screen") and self.loading_screen.winfo_exists():
            self.loading_screen.destroy()
        self.deiconify()

    def configure_styles(self) -> None:
        self.style.configure(
            "Vertical.TScrollbar",
            background=COLORS["card_2"],
            troughcolor=COLORS["bg"],
            bordercolor=COLORS["bg"],
            arrowcolor=COLORS["accent_2"],
            relief="flat",
            width=12,
        )
        self.style.map("Vertical.TScrollbar", background=[("active", COLORS["accent"])])
        self.style.configure("Panel.TFrame", background=COLORS["bg"])
        self.style.configure("Inset.TFrame", background=COLORS["card"])
        self.style.configure("Title.TLabel", background=COLORS["bg"], foreground=COLORS["text"], font=("Segoe UI", 24, "bold"))
        self.style.configure("Accent.TButton", font=("Segoe UI", 10, "bold"), padding=(14, 9))
        self.style.map("Accent.TButton", background=[("active", COLORS["accent"])])

    def build_ui(self) -> None:
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        sidebar = modern_frame(self, COLORS["sidebar"], radius=0)
        sidebar.grid(row=0, column=0, sticky="ns")
        sidebar.grid_propagate(False)
        sidebar.configure(width=0)
        sidebar.columnconfigure(0, weight=1)
        sidebar.rowconfigure(0, weight=1)
        self.sidebar = sidebar

        self.build_sidebar_shell(sidebar)

        content = modern_frame(self, COLORS["bg"], radius=0)
        content.grid(row=0, column=1, sticky="nsew")
        content.columnconfigure(0, weight=1)
        content.rowconfigure(1, weight=1)

        self.build_header(content)

        page_host = modern_frame(content, COLORS["bg"], radius=0)
        page_host.grid(row=1, column=0, sticky="nsew", padx=24, pady=(0, 24))
        page_host.columnconfigure(0, weight=1)
        page_host.rowconfigure(0, weight=1)

        command_page = self.build_home_page(page_host)
        self.functions_page = FunctionsCategory(page_host, self.tr)
        self.overlay_page = OverlayCategory(page_host, self.functions_page, self.tr)
        self.stockpile_page = StockpileCategory(page_host, self.tr)

        self.pages["inicio"] = command_page
        self.pages["ferramentas"] = self.functions_page
        self.pages["overlay"] = self.overlay_page
        self.pages["stockpile"] = self.stockpile_page

        command_page.grid(row=0, column=0, sticky="nsew")
        self.functions_page.grid(row=0, column=0, sticky="nsew")
        self.overlay_page.grid(row=0, column=0, sticky="nsew")
        self.stockpile_page.grid(row=0, column=0, sticky="nsew")
        sidebar.configure(width=0)
        sidebar.grid_remove()

    def build_sidebar_shell(self, sidebar: tk.Frame) -> None:
        canvas = tk.Canvas(sidebar, bg=COLORS["sidebar"], highlightthickness=0, bd=0)
        canvas.grid(row=0, column=0, sticky="nsew")
        if ctk is not None:
            scrollbar = ctk.CTkScrollbar(
                sidebar,
                orientation="vertical",
                command=canvas.yview,
                width=10,
                fg_color=COLORS["sidebar"],
                button_color=COLORS["card_2"],
                button_hover_color=COLORS["accent"],
            )
        else:
            scrollbar = ttk.Scrollbar(sidebar, orient="vertical", command=canvas.yview, style="Vertical.TScrollbar")
        scrollbar.grid(row=0, column=1, sticky="ns")
        canvas.configure(yscrollcommand=scrollbar.set)

        inner = tk.Frame(canvas, bg=COLORS["sidebar"])
        window_id = canvas.create_window((0, 0), window=inner, anchor="nw", width=SIDEBAR_WIDTH - 18)
        inner.bind("<Configure>", lambda _event: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda event: canvas.itemconfigure(window_id, width=max(1, event.width)))

        self.sidebar_canvas = canvas
        self.sidebar_inner = inner
        self.build_sidebar(inner)
        self.bind_mousewheel_recursive(sidebar, canvas)

    def bind_mousewheel_recursive(self, widget: tk.Widget, canvas: tk.Canvas) -> None:
        def on_mousewheel(event) -> str:
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            return "break"

        widget.bind("<MouseWheel>", on_mousewheel, add="+")
        for child in widget.winfo_children():
            self.bind_mousewheel_recursive(child, canvas)

    def build_sidebar(self, sidebar: tk.Frame) -> None:
        brand = modern_frame(sidebar, COLORS["sidebar"], radius=0)
        brand.grid(row=0, column=0, sticky="ew", padx=18, pady=(18, 14))
        brand.columnconfigure(1, weight=1)
        self.sidebar_logo_frames = self.load_logo_frames(size=44)
        if self.sidebar_logo_frames:
            self.sidebar_logo_image = self.sidebar_logo_frames[0][0]
            self.sidebar_logo_label = tk.Label(brand, image=self.sidebar_logo_image, bg=COLORS["sidebar"])
            self.sidebar_logo_label.grid(row=0, column=0, rowspan=2, sticky="w", padx=(0, 10))
            self.animate_sidebar_logo()
        else:
            mark = tk.Label(brand, text="GG", bg=COLORS["accent"], fg="#06101d", font=("Segoe UI", 13, "bold"), width=3, height=2)
            mark.grid(row=0, column=0, rowspan=2, sticky="w", padx=(0, 10))
        self.ui_text["brand_title"] = tk.Label(brand, text=APP_TITLE, bg=COLORS["sidebar"], fg=COLORS["text"], font=("Segoe UI", 17, "bold"))
        self.ui_text["brand_title"].grid(
            row=0, column=1, sticky="w"
        )
        self.ui_text["brand_subtitle"] = tk.Label(brand, text=self.tr.t("app.subtitle"), bg=COLORS["sidebar"], fg=COLORS["muted"], font=("Segoe UI", 9))
        self.ui_text["brand_subtitle"].grid(
            row=1, column=1, sticky="w"
        )

        profile_card = modern_frame(sidebar, COLORS["soft"], radius=18, border=1, border_color="#1e3554")
        profile_card.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 18))
        profile_card.columnconfigure(1, weight=1)

        tk.Canvas(profile_card, width=72, height=72, bg=COLORS["card_2"], highlightthickness=0).grid(
            row=0, column=0, rowspan=2, sticky="nw", padx=14, pady=14
        )
        self.avatar_canvas = profile_card.winfo_children()[0]
        self.draw_avatar_placeholder()

        self.nick_label = tk.Label(
            profile_card,
            text=self.tr.t("sidebar.searching_steam"),
            bg=COLORS["soft"],
            fg=COLORS["text"],
            font=("Segoe UI", 13, "bold"),
            anchor="w",
        )
        self.nick_label.grid(row=0, column=1, sticky="ew", padx=(0, 14), pady=(16, 0))
        self.steam_label = tk.Label(profile_card, text="", bg=COLORS["soft"], fg=COLORS["muted"], font=("Segoe UI", 9), anchor="w")
        self.steam_label.grid(row=1, column=1, sticky="ew", padx=(0, 14), pady=(2, 12))

        self.section_label(sidebar, self.tr.t("sidebar.navigation"), 2, key="section_navigation")
        self.nav_buttons["inicio"] = self.nav_button(sidebar, "HOME", self.tr.t("nav.home"), lambda: self.show_page("inicio"), row=3)

        self.section_label(sidebar, self.tr.t("sidebar.tools"), 4, pady=(20, 6), key="section_tools")
        self.nav_buttons["ferramentas"] = self.nav_button(sidebar, "AUTO", self.tr.t("nav.auto_clicker"), lambda: self.show_page("ferramentas"), row=5)
        self.nav_buttons["overlay"] = self.nav_button(sidebar, "HUD", self.tr.t("nav.overlay"), lambda: self.show_page("overlay"), row=6)
        self.nav_buttons["stockpile"] = self.nav_button(sidebar, "STK", self.tr.t("stockpile.nav"), lambda: self.show_page("stockpile"), row=7)
        tk.Label(sidebar, text="", bg=COLORS["sidebar"]).grid(row=8, column=0, pady=80)

        tk.Label(
            sidebar,
            text=f"{APP_TITLE} Command",
            bg=COLORS["sidebar"],
            fg="#517499",
            font=("Segoe UI", 8, "bold"),
        ).grid(row=99, column=0, sticky="s", padx=18, pady=20)
        sidebar.rowconfigure(98, weight=1)

    def load_logo_frames(self, size: int = 44) -> list[tuple[tk.PhotoImage, int]]:
        return self.load_splash_frames(size=size)

    def animate_sidebar_logo(self) -> None:
        if not self.sidebar_logo_frames or not hasattr(self, "sidebar_logo_label"):
            return
        frame, delay = self.sidebar_logo_frames[self.sidebar_logo_frame_index]
        self.sidebar_logo_label.configure(image=frame)
        self.sidebar_logo_image = frame
        self.sidebar_logo_frame_index = (self.sidebar_logo_frame_index + 1) % len(self.sidebar_logo_frames)
        self.sidebar_logo_animation_job = self.after(max(80, delay), self.animate_sidebar_logo)

    def section_label(self, parent: tk.Frame, text: str, row: int, pady: tuple[int, int] = (0, 6), key: str | None = None) -> None:
        label = tk.Label(parent, text=text, bg=COLORS["sidebar"], fg="#6385aa", font=("Segoe UI", 8, "bold"))
        label.grid(
            row=row, column=0, sticky="w", padx=22, pady=pady
        )
        if key:
            self.ui_text[key] = label

    def nav_button(self, parent: tk.Frame, icon: str, text: str, command, row: int):
        button = modern_button(
            parent,
            text=f"{icon}   {text}",
            command=command,
            color=COLORS["sidebar"],
            text_color=COLORS["muted"],
            hover=COLORS["hover"],
            height=46,
            font=("Segoe UI", 11, "bold"),
        )
        button.grid(row=row, column=0, sticky="ew", padx=12, pady=3)
        if ctk is None:
            button.configure(anchor="w", padx=18)
            button.bind("<Enter>", lambda _event: button.configure(bg=COLORS["hover"], fg=COLORS["text"]))
        else:
            button.configure(anchor="w")
        button.bind("<Leave>", lambda _event: self.restore_nav_button(button))
        return button

    def restore_nav_button(self, button) -> None:
        if ctk is not None:
            if button.cget("fg_color") != COLORS["card_2"]:
                button.configure(fg_color=COLORS["sidebar"], text_color=COLORS["muted"])
        elif button.cget("bg") != COLORS["card_2"]:
            button.configure(bg=COLORS["sidebar"], fg=COLORS["muted"])

    def build_header(self, parent: tk.Frame) -> None:
        header = modern_frame(parent, COLORS["bg"], radius=0)
        header.grid(row=0, column=0, sticky="ew", padx=24, pady=(24, 18))
        header.columnconfigure(1, weight=1)

        self.menu_button = modern_button(
            header,
            text="â˜°",
            command=self.toggle_sidebar,
            color=COLORS["card"],
            text_color=COLORS["text"],
            hover=COLORS["card_2"],
            width=48,
            height=44,
            font=("Segoe UI", 16, "bold"),
        )
        self.menu_button.configure(text="\u2630")
        self.menu_button.grid(row=0, column=0, rowspan=2, sticky="nw", padx=(0, 14), pady=(2, 0))

        self.ui_text["header_title"] = tk.Label(header, text=self.tr.t("header.title"), bg=COLORS["bg"], fg=COLORS["text"], font=("Segoe UI", 26, "bold"))
        self.ui_text["header_title"].grid(
            row=0, column=1, sticky="w"
        )
        self.ui_text["header_subtitle"] = tk.Label(
            header,
            text=self.tr.t("header.subtitle"),
            bg=COLORS["bg"],
            fg=COLORS["muted"],
            font=("Segoe UI", 11),
        )
        self.ui_text["header_subtitle"].grid(row=1, column=1, sticky="w")
        tk.Label(
            header,
            textvariable=self.user_status_var,
            bg=COLORS["bg"],
            fg=COLORS["accent_2"],
            font=("Segoe UI", 10, "bold"),
        ).grid(row=0, column=2, rowspan=2, sticky="e", padx=(16, 14))

        language_box = modern_frame(header, COLORS["bg"], radius=0)
        language_box.grid(row=0, column=3, rowspan=2, sticky="e")
        for index, language in enumerate(SUPPORTED_LANGUAGES):
            flag_image = self.load_flag_image(language)
            button = tk.Button(
                language_box,
                text=language.upper(),
                image=flag_image,
                compound="left",
                command=lambda code=language: self.change_language(code),
                bg=COLORS["card_2"] if language == self.tr.language else COLORS["card"],
                fg=COLORS["text"],
                activebackground=COLORS["accent"],
                activeforeground=COLORS["accent_text"],
                relief="flat",
                padx=7,
                pady=5,
                font=("Segoe UI", 9, "bold"),
                cursor="hand2",
            )
            button.grid(row=0, column=index, padx=2)
            self.language_buttons[language] = button
        modern_button(
            language_box,
            text="STOCK",
            command=lambda: self.show_page("stockpile"),
            color=COLORS["card"],
            text_color=COLORS["accent_2"],
            hover=COLORS["card_2"],
            height=30,
            font=("Segoe UI", 9, "bold"),
        ).grid(row=1, column=0, columnspan=4, sticky="ew", pady=(6, 0))

    def load_flag_image(self, language: str) -> tk.PhotoImage | None:
        if language in self.flag_images:
            return self.flag_images[language]
        info = SUPPORTED_LANGUAGES[language]
        url = self.tr.flag_url(language)
        try:
            cache_dir = BASE_DIR / "img" / "flags"
            cache_dir.mkdir(parents=True, exist_ok=True)
            cache_path = cache_dir / f"{info['flag']}.png"
            if not cache_path.exists():
                with urllib.request.urlopen(url, timeout=4) as response:
                    cache_path.write_bytes(response.read())
            try:
                from PIL import Image, ImageTk

                source = Image.open(cache_path).convert("RGBA")
                source.thumbnail((24, 16))
                image = ImageTk.PhotoImage(source)
            except Exception:
                encoded = base64.b64encode(cache_path.read_bytes()).decode("ascii")
                image = tk.PhotoImage(data=encoded)
                if image.width() > 32:
                    image = image.subsample(max(1, image.width() // 24), max(1, image.height() // 16))
        except Exception:
            return None
        self.flag_images[language] = image
        return image

    def toggle_sidebar(self) -> None:
        if not self.sidebar:
            return
        if self.sidebar_visible:
            self.sidebar.configure(width=0)
            self.sidebar.grid_remove()
            self.sidebar_visible = False
            if self.menu_button:
                self.configure_button_color(self.menu_button, COLORS["card"])
                self.menu_button.configure(text="\u2630")
                self.pulse_menu_button(COLORS["card_2"], COLORS["card"])
        else:
            self.sidebar.configure(width=SIDEBAR_WIDTH)
            self.sidebar.grid(row=0, column=0, sticky="ns")
            self.sidebar_visible = True
            if self.menu_button:
                self.configure_button_color(self.menu_button, COLORS["card_2"])
                self.menu_button.configure(text="X")
                self.pulse_menu_button(COLORS["accent"], COLORS["card_2"])

    def pulse_menu_button(self, first_color: str, final_color: str) -> None:
        if not self.menu_button:
            return
        self.configure_button_color(self.menu_button, first_color)
        self.after(90, lambda: self.menu_button and self.configure_button_color(self.menu_button, final_color))

    def configure_button_color(self, button, color: str, text_color: str | None = None) -> None:
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

    def change_language(self, language: str) -> None:
        self.settings = load_settings()
        self.settings["language"] = language
        save_settings(self.settings)
        self.tr.set_language(language)
        self.title(f"{APP_TITLE} - {self.tr.t('app.subtitle')}")
        self.refresh_language_texts()
        self.refresh_steam_profile()
        self.refresh_foxhole_status()

    def refresh_language_texts(self) -> None:
        text_updates = {
            "brand_subtitle": self.tr.t("app.subtitle"),
            "section_navigation": self.tr.t("sidebar.navigation"),
            "section_tools": self.tr.t("sidebar.tools"),
            "header_title": self.tr.t("header.title"),
            "header_subtitle": self.tr.t("header.subtitle"),
            "home_eyebrow": self.tr.t("home.eyebrow"),
            "home_title": self.tr.t("home.title"),
            "home_body": self.tr.t("home.body"),
            "home_card_tools_title": self.tr.t("home.card_tools_title"),
            "home_card_tools_body": self.tr.t("home.card_tools_body"),
            "home_card_profile_title": self.tr.t("home.card_profile_title"),
            "home_card_profile_body": self.tr.t("home.card_profile_body"),
            "home_card_stockpile_title": self.tr.t("home.card_stockpile_title"),
            "home_card_stockpile_body": self.tr.t("home.card_stockpile_body"),
            "home_card_foxhole_title": self.tr.t("home.card_foxhole_title"),
            "home_card_foxhole_body": self.tr.t("home.card_foxhole_body"),
        }
        for key, text in text_updates.items():
            widget = self.ui_text.get(key)
            if widget:
                widget.configure(text=text)
        nav_texts = {
            "inicio": ("HOME", self.tr.t("nav.home")),
            "ferramentas": ("AUTO", self.tr.t("nav.auto_clicker")),
            "overlay": ("HUD", self.tr.t("nav.overlay")),
            "stockpile": ("STK", self.tr.t("stockpile.nav")),
        }
        for key, (icon, text) in nav_texts.items():
            button = self.nav_buttons.get(key)
            if button:
                button.configure(text=f"{icon}   {text}")
        for language, button in self.language_buttons.items():
            button.configure(bg=COLORS["card_2"] if language == self.tr.language else COLORS["card"])
        if self.functions_page and hasattr(self.functions_page, "refresh_language"):
            self.functions_page.refresh_language(self.tr)
        if self.overlay_page and hasattr(self.overlay_page, "refresh_language"):
            self.overlay_page.refresh_language(self.tr)
        if self.stockpile_page and hasattr(self.stockpile_page, "refresh_language"):
            self.stockpile_page.refresh_language(self.tr)

    def build_home_page(self, parent: tk.Frame) -> tk.Frame:
        page = modern_frame(parent, COLORS["bg"], radius=0)
        page.columnconfigure(0, weight=1)
        page.rowconfigure(0, weight=1)

        canvas = tk.Canvas(page, bg=COLORS["bg"], highlightthickness=0, bd=0)
        canvas.grid(row=0, column=0, sticky="nsew")

        hero = modern_frame(canvas, COLORS["glass"], radius=24, border=1, border_color="#315b86")
        hero_window = canvas.create_window(32, 32, window=hero, anchor="nw", width=760)
        self.ui_text["home_eyebrow"] = tk.Label(hero, text=self.tr.t("home.eyebrow"), bg=COLORS["glass"], fg=COLORS["accent_2"], font=("Segoe UI", 10, "bold"))
        self.ui_text["home_eyebrow"].pack(
            anchor="w", padx=26, pady=(24, 4)
        )
        self.ui_text["home_title"] = tk.Label(hero, text=self.tr.t("home.title"), bg=COLORS["glass"], fg=COLORS["text"], font=("Segoe UI", 30, "bold"))
        self.ui_text["home_title"].pack(
            anchor="w", padx=26
        )
        status_row = tk.Frame(hero, bg=COLORS["glass"])
        status_row.pack(fill="x", padx=26, pady=(14, 4))
        status_pill = tk.Label(
            status_row,
            textvariable=self.user_status_var,
            bg=COLORS["glass_2"],
            fg=COLORS["accent_2"],
            font=("Segoe UI", 10, "bold"),
            padx=12,
            pady=6,
        )
        status_pill.pack(side="left", padx=(0, 8))
        tk.Label(
            status_row,
            text="STEAM ONLY",
            bg="#102b2a",
            fg=COLORS["accent"],
            font=("Segoe UI", 10, "bold"),
            padx=12,
            pady=6,
        ).pack(side="left")
        self.ui_text["home_body"] = tk.Label(
            hero,
            text=self.tr.t("home.body"),
            bg=COLORS["glass"],
            fg=COLORS["muted"],
            font=("Segoe UI", 11),
            wraplength=560,
            justify="left",
        )
        self.ui_text["home_body"].pack(anchor="w", padx=26, pady=(8, 20))

        foxhole_panel = modern_frame(hero, COLORS["glass_2"], radius=18, border=1, border_color="#254469")
        foxhole_panel.pack(fill="x", padx=26, pady=(0, 26))
        tk.Label(foxhole_panel, text="Foxhole", bg=COLORS["glass_2"], fg=COLORS["text"], font=("Segoe UI", 13, "bold")).grid(
            row=0, column=0, sticky="w", padx=16, pady=(14, 0)
        )
        tk.Label(foxhole_panel, textvariable=self.foxhole_status_var, bg=COLORS["glass_2"], fg=COLORS["muted"], font=("Segoe UI", 10)).grid(
            row=1, column=0, sticky="w", padx=16, pady=(2, 14)
        )
        self.foxhole_button = modern_button(
            foxhole_panel,
            text=self.tr.t("home.open_foxhole"),
            command=self.open_foxhole,
            color=COLORS["accent"],
            text_color=COLORS["accent_text"],
            hover=COLORS["accent_2"],
            width=150,
            height=42,
            font=("Segoe UI", 10, "bold"),
        )
        self.foxhole_button.grid(row=0, column=1, rowspan=2, sticky="e", padx=16, pady=14)
        foxhole_panel.columnconfigure(0, weight=1)

        grid = modern_frame(canvas, COLORS["bg"], radius=0)
        grid_window = canvas.create_window(32, 348, window=grid, anchor="nw", width=840)
        for column in range(2):
            grid.columnconfigure(column, weight=1)

        self.add_card(grid, self.tr.t("home.card_tools_title"), self.tr.t("home.card_tools_body"), 0, 0, "home_card_tools")
        self.add_card(grid, self.tr.t("home.card_profile_title"), self.tr.t("home.card_profile_body"), 0, 1, "home_card_profile")
        self.add_card(grid, self.tr.t("home.card_stockpile_title"), self.tr.t("home.card_stockpile_body"), 1, 0, "home_card_stockpile")
        self.add_card(grid, self.tr.t("home.card_foxhole_title"), self.tr.t("home.card_foxhole_body"), 1, 1, "home_card_foxhole")

        canvas.bind("<Configure>", lambda event: self.redraw_home_background(event, hero_window, grid_window))
        return page

    def redraw_home_background(self, event, hero_window: int, grid_window: int) -> None:
        canvas: tk.Canvas = event.widget
        canvas.delete("wallpaper")
        width = max(1, event.width)
        height = max(1, event.height)
        self.wallpaper_photo = self.load_wallpaper(width, height)
        if self.wallpaper_photo:
            canvas.create_image(0, 0, image=self.wallpaper_photo, anchor="nw", tags="wallpaper")
        else:
            canvas.create_rectangle(0, 0, width, height, fill=COLORS["bg"], outline="", tags="wallpaper")
        canvas.create_rectangle(0, 0, width, height, fill="#030914", stipple="gray25", outline="", tags="wallpaper")
        canvas.create_rectangle(0, int(height * 0.55), width, height, fill="#030914", stipple="gray50", outline="", tags="wallpaper")
        canvas.tag_lower("wallpaper")
        canvas.itemconfigure(hero_window, width=min(780, max(320, width - 64)))
        canvas.itemconfigure(grid_window, width=max(320, width - 64))

    def load_wallpaper(self, width: int, height: int) -> tk.PhotoImage | None:
        if not WALLPAPER_PATH.exists():
            return None
        try:
            from PIL import Image, ImageFilter, ImageTk

            if self.wallpaper_source is None:
                self.wallpaper_source = Image.open(WALLPAPER_PATH).convert("RGB")
            source_w, source_h = self.wallpaper_source.size
            scale = max(width / source_w, height / source_h)
            target_size = (max(1, int(source_w * scale)), max(1, int(source_h * scale)))
            image = self.wallpaper_source.resize(target_size)
            left = max(0, (target_size[0] - width) // 2)
            top = max(0, (target_size[1] - height) // 2)
            image = image.crop((left, top, left + width, top + height))
            image = image.filter(ImageFilter.GaussianBlur(radius=8))
            return ImageTk.PhotoImage(image)
        except Exception:
            try:
                return tk_photo_from_path(WALLPAPER_PATH)
            except tk.TclError:
                return None

    def build_command_page(self, parent: tk.Frame) -> tk.Frame:
        page = modern_frame(parent, COLORS["bg"], radius=0)
        page.columnconfigure(0, weight=1)

        hero = modern_frame(page, COLORS["card"], radius=24, border=1, border_color=COLORS["line"])
        hero.grid(row=0, column=0, sticky="ew", pady=(0, 16))
        hero.columnconfigure(0, weight=1)
        tk.Label(hero, text="INICIO", bg=COLORS["card"], fg=COLORS["accent_2"], font=("Segoe UI", 12, "bold")).grid(
            row=0, column=0, sticky="w", padx=20, pady=(18, 4)
        )
        tk.Label(hero, text="Painel de comando", bg=COLORS["card"], fg=COLORS["text"], font=("Segoe UI", 24, "bold")).grid(
            row=1, column=0, sticky="w", padx=20
        )
        tk.Label(
            hero,
            text="Abra o menu para ver seu perfil da Steam e entrar nas ferramentas.",
            bg=COLORS["card"],
            fg=COLORS["muted"],
            font=("Segoe UI", 11),
            wraplength=720,
            justify="left",
        ).grid(row=2, column=0, sticky="w", padx=20, pady=(8, 20))

        grid = modern_frame(page, COLORS["bg"], radius=0)
        grid.grid(row=1, column=0, sticky="ew")
        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)

        self.add_card(grid, "ðŸ§° Ferramentas", "Auto Clicker fica dentro da categoria Ferramentas.", 0, 0)
        self.add_card(grid, "Perfil", "Nick e foto da Steam ficam organizados no menu.", 0, 1)
        self.add_card(grid, "Stockpile", "Envio e visual do estoque ficam em uma tela dedicada.", 1, 0)
        self.add_card(grid, "ðŸŽ® Foxhole", "Abra o jogo e capture a janela antes de ligar o autoclicker.", 1, 1)

        return page

    def add_card(self, parent: tk.Frame, title: str, body: str, row: int, column: int, key: str | None = None) -> None:
        card = modern_frame(parent, COLORS["glass"], radius=18, border=1, border_color="#24486d")
        card.grid(row=row, column=column, sticky="nsew", padx=(0 if column == 0 else 10, 0), pady=(0, 16))
        accent = tk.Frame(card, bg=COLORS["accent"], width=4)
        accent.pack(side="left", fill="y")
        content = tk.Frame(card, bg=COLORS["glass"])
        content.pack(side="left", fill="both", expand=True)
        title_label = tk.Label(content, text=title, bg=COLORS["glass"], fg=COLORS["accent_2"], font=("Segoe UI", 11, "bold"))
        title_label.pack(
            anchor="w", padx=16, pady=(14, 4)
        )
        body_label = tk.Label(content, text=body, bg=COLORS["glass"], fg=COLORS["text"], font=("Segoe UI", 10), wraplength=320, justify="left")
        body_label.pack(
            anchor="w", padx=16, pady=(0, 16)
        )
        if key:
            self.ui_text[f"{key}_title"] = title_label
            self.ui_text[f"{key}_body"] = body_label

    def show_page(self, page_name: str) -> None:
        for name, page in self.pages.items():
            if name == page_name:
                page.tkraise()
                self.configure_button_color(self.nav_buttons[name], COLORS["card_2"], COLORS["text"])
            else:
                self.configure_button_color(self.nav_buttons[name], COLORS["sidebar"], COLORS["muted"])

    def draw_avatar_placeholder(self) -> None:
        canvas: tk.Canvas = self.avatar_canvas
        canvas.delete("all")
        canvas.create_rectangle(0, 0, 72, 72, fill=COLORS["card_2"], outline=COLORS["accent"])
        canvas.create_oval(23, 13, 49, 39, fill=COLORS["accent_2"], outline="")
        canvas.create_rectangle(18, 47, 54, 61, fill=COLORS["accent_2"], outline="")

    def load_avatar_if_possible(self) -> None:
        self.draw_avatar_placeholder()
        if not self.profile.avatar_path:
            return
        try:
            if self.profile.avatar_path.suffix.lower() == ".png":
                self.avatar_image = tk_photo_from_path(self.profile.avatar_path)
            else:
                from PIL import Image, ImageTk

                image = Image.open(self.profile.avatar_path).resize((72, 72))
                self.avatar_image = ImageTk.PhotoImage(image)
            self.avatar_canvas.create_image(36, 36, image=self.avatar_image)
        except Exception:
            self.avatar_image = None

    def refresh_steam_profile(self) -> None:
        self.profile = get_local_steam_profile()
        self.load_avatar_if_possible()

        if self.profile.persona_name:
            self.nick_label.configure(text=self.profile.persona_name)
        elif self.profile.account_name:
            self.nick_label.configure(text=self.profile.account_name)
        else:
            self.nick_label.configure(text=self.tr.t("steam.not_found"))

        details = [self.tr.t("steam.connected") if self.profile.steam_id else self.tr.t("steam.open_to_detect")]
        self.steam_label.configure(text="\n".join(details))
        self.update_user_status()

    def refresh_foxhole_status(self) -> None:
        running, started_at = self.get_foxhole_process_state()
        self.foxhole_running = running
        if running:
            duration = self.format_duration(datetime.now(timezone.utc) - started_at) if started_at else self.tr.t("duration.unknown")
            self.foxhole_status_var.set(self.tr.t("home.foxhole_running", duration=duration))
            if hasattr(self, "foxhole_button"):
                self.foxhole_button.configure(text=self.tr.t("home.refresh"), command=self.refresh_foxhole_status)
                self.configure_button_color(self.foxhole_button, COLORS["soft"], COLORS["text"])
        else:
            self.foxhole_status_var.set(self.tr.t("home.foxhole_closed"))
            if hasattr(self, "foxhole_button"):
                self.foxhole_button.configure(text=self.tr.t("home.open_foxhole"), command=self.open_foxhole)
                self.configure_button_color(self.foxhole_button, COLORS["accent"], COLORS["accent_text"])

    def get_foxhole_process_state(self) -> tuple[bool, datetime | None]:
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        matches: list[datetime | None] = []
        enum_proc_type = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

        def enum_proc(hwnd, _lparam):
            if not user32.IsWindowVisible(hwnd):
                return True
            pid = ctypes.c_ulong()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if not pid.value:
                return True
            process_path = self.get_process_path(kernel32, pid.value)
            process_name = Path(process_path).name.lower() if process_path else ""
            if self.is_foxhole_process(process_name, process_path.lower()):
                matches.append(self.get_process_started_at(kernel32, pid.value))
            return True

        user32.EnumWindows(enum_proc_type(enum_proc), 0)
        if not matches:
            return False, None
        known_times = [item for item in matches if item is not None]
        return True, min(known_times) if known_times else None

    def get_process_name(self, kernel32, pid: int) -> str:
        process_path = self.get_process_path(kernel32, pid)
        return Path(process_path).name if process_path else ""

    def get_process_path(self, kernel32, pid: int) -> str:
        process_handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not process_handle:
            return ""
        try:
            path_buffer = ctypes.create_unicode_buffer(1024)
            size = ctypes.c_ulong(len(path_buffer))
            if kernel32.QueryFullProcessImageNameW(process_handle, 0, path_buffer, ctypes.byref(size)):
                return path_buffer.value
            return ""
        finally:
            kernel32.CloseHandle(process_handle)

    @staticmethod
    def is_foxhole_process(process_name: str, process_path: str) -> bool:
        return process_name in FOXHOLE_PROCESS_NAMES or any(hint in process_path for hint in FOXHOLE_PATH_HINTS)

    def get_process_started_at(self, kernel32, pid: int) -> datetime | None:
        process_handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not process_handle:
            return None
        try:
            creation = FILETIME()
            exit_time = FILETIME()
            kernel = FILETIME()
            user = FILETIME()
            if not kernel32.GetProcessTimes(process_handle, ctypes.byref(creation), ctypes.byref(exit_time), ctypes.byref(kernel), ctypes.byref(user)):
                return None
            value = (creation.dwHighDateTime << 32) + creation.dwLowDateTime
            unix_seconds = (value - 116444736000000000) / 10000000
            return datetime.fromtimestamp(unix_seconds, tz=timezone.utc)
        finally:
            kernel32.CloseHandle(process_handle)

    @staticmethod
    def get_window_title(user32, hwnd: int) -> str:
        length = user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return ""
        buffer = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buffer, length + 1)
        return buffer.value

    def format_duration(self, delta) -> str:
        seconds = max(0, int(delta.total_seconds()))
        hours, remainder = divmod(seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        if hours:
            return self.tr.t("duration.hours", hours=hours, minutes=minutes)
        if minutes:
            return self.tr.t("duration.minutes", minutes=minutes)
        return self.tr.t("duration.less_minute")

    def update_user_status(self) -> None:
        self.user_active = bool(self.profile.steam_id)
        if self.profile.steam_id:
            self.user_status_var.set(self.tr.t("user.active_steam"))
        else:
            self.user_status_var.set(self.tr.t("user.unknown"))

    def open_foxhole(self) -> None:
        os.startfile(f"steam://run/{FOXHOLE_APP_ID}")
        self.foxhole_status_var.set(self.tr.t("home.foxhole_opening"))
        self.after(5000, self.refresh_foxhole_status)

    def check_for_updates(self) -> None:
        if not UPDATE_REPO:
            return

        def worker() -> None:
            try:
                update = check_latest_release(UPDATE_REPO, APP_VERSION)
            except Exception as exc:
                print(f"[Updater] check failed: {exc}", flush=True)
                return
            if update:
                self.after(0, lambda: self.offer_update(update))

        threading.Thread(target=worker, daemon=True).start()

    def offer_update(self, update) -> None:
        wants_update = messagebox.askyesno(
            "Atualizacao disponivel",
            f"Existe uma nova versao do GG Coalition: {update.version}\n\n"
            "Deseja baixar e instalar agora?",
            parent=self,
        )
        if not wants_update:
            return

        def worker() -> None:
            try:
                zip_path = download_update(update)
                launch_updater(zip_path, self.runtime_dir(), self.launch_target())
                self.after(0, self.exit_app)
            except Exception as exc:
                self.after(0, lambda: messagebox.showerror("Erro ao atualizar", str(exc), parent=self))

        threading.Thread(target=worker, daemon=True).start()

    def runtime_dir(self) -> Path:
        if getattr(sys, "frozen", False):
            return Path(sys.executable).resolve().parent
        return BASE_DIR

    def launch_target(self) -> Path:
        if getattr(sys, "frozen", False):
            return Path(sys.executable).resolve()
        return BASE_DIR / "felb_app.py"

    def on_unmap(self, event) -> None:
        if event.widget is not self:
            return
        if self.hidden_to_tray:
            return
        self.after(80, self.hide_if_minimized)

    def hide_if_minimized(self) -> None:
        if self.state() == "iconic":
            self.hide_to_tray()

    def request_close(self) -> None:
        action = str(self.settings.get("app", {}).get("close_action", "ask"))
        if action == "tray":
            self.hide_to_tray()
            return
        if action == "exit":
            self.exit_app()
            return
        self.show_close_dialog()

    def show_close_dialog(self) -> None:
        dialog = ctk.CTkToplevel(self) if ctk is not None else tk.Toplevel(self)
        dialog.title("Fechar GG Coalition")
        dialog.geometry("430x230")
        dialog.resizable(False, False)
        configure_surface(dialog, COLORS["bg"])
        dialog.transient(self)
        dialog.grab_set()
        dialog.update_idletasks()
        x = self.winfo_rootx() + max(0, (self.winfo_width() - 430) // 2)
        y = self.winfo_rooty() + max(0, (self.winfo_height() - 230) // 2)
        dialog.geometry(f"430x230+{x}+{y}")

        panel = modern_frame(dialog, COLORS["card"], radius=22, border=1, border_color=COLORS["line"])
        panel.pack(fill="both", expand=True, padx=16, pady=16)
        tk.Label(panel, text="O que deseja fazer?", bg=COLORS["card"], fg=COLORS["text"], font=("Segoe UI", 18, "bold")).pack(
            anchor="w", padx=20, pady=(18, 4)
        )
        tk.Label(
            panel,
            text="Voce pode fechar de verdade ou deixar o app rodando em segundo plano na bandeja do Windows.",
            bg=COLORS["card"],
            fg=COLORS["muted"],
            font=("Segoe UI", 10),
            wraplength=360,
            justify="left",
        ).pack(anchor="w", padx=20, pady=(0, 12))

        remember_var = tk.BooleanVar(value=False)
        if ctk is not None:
            checkbox = ctk.CTkCheckBox(
                panel,
                text="Nao perguntar novamente",
                variable=remember_var,
                fg_color=COLORS["accent"],
                hover_color=COLORS["accent_2"],
                text_color=COLORS["text"],
                corner_radius=6,
            )
        else:
            checkbox = tk.Checkbutton(
                panel,
                text="Nao perguntar novamente",
                variable=remember_var,
                bg=COLORS["card"],
                fg=COLORS["text"],
                selectcolor=COLORS["soft"],
                activebackground=COLORS["card"],
                activeforeground=COLORS["text"],
                font=("Segoe UI", 10),
            )
        checkbox.pack(anchor="w", padx=20, pady=(0, 14))

        actions = modern_frame(panel, COLORS["card"], radius=0)
        actions.pack(fill="x", padx=20, pady=(0, 18))

        def choose(action: str) -> None:
            if remember_var.get():
                self.settings = load_settings()
                self.settings.setdefault("app", {})["close_action"] = action
                save_settings(self.settings)
            dialog.grab_release()
            dialog.destroy()
            if action == "tray":
                self.hide_to_tray()
            else:
                self.exit_app()

        modern_button(
            actions,
            text="Segundo plano",
            command=lambda: choose("tray"),
            color=COLORS["accent"],
            text_color=COLORS["accent_text"],
            hover=COLORS["accent_2"],
            height=40,
        ).pack(side="left", fill="x", expand=True, padx=(0, 8))
        modern_button(
            actions,
            text="Fechar",
            command=lambda: choose("exit"),
            color=COLORS["soft"],
            text_color=COLORS["text"],
            hover=COLORS["hover"],
            height=40,
        ).pack(side="left", fill="x", expand=True, padx=(8, 0))

    def hide_to_tray(self) -> None:
        if self.ensure_tray_icon():
            self.hidden_to_tray = True
            self.withdraw()
            return
        self.iconify()
        messagebox.showwarning(
            "Bandeja indisponivel",
            "Instale a dependencia pystray para esconder no canto do Windows.",
            parent=self,
        )

    def ensure_tray_icon(self) -> bool:
        if pystray is None:
            return False
        if self.tray_running:
            return True
        image = self.create_tray_image()
        menu = pystray.Menu(
            pystray.MenuItem("Abrir GG Coalition", lambda _icon, _item: self.after(0, self.show_from_tray), default=True),
            pystray.MenuItem("Fechar", lambda _icon, _item: self.after(0, self.exit_app)),
        )
        self.tray_icon = pystray.Icon("GG Coalition", image, "GG Coalition", menu)
        threading.Thread(target=self.tray_icon.run, daemon=True).start()
        self.tray_running = True
        return True

    def create_tray_image(self):
        if Image is None:
            return None
        try:
            image = Image.open(ICON_PATH).convert("RGBA")
            image.thumbnail((64, 64))
            canvas = Image.new("RGBA", (64, 64), (7, 11, 22, 255))
            x = (64 - image.width) // 2
            y = (64 - image.height) // 2
            canvas.alpha_composite(image, (x, y))
            return canvas
        except Exception:
            image = Image.new("RGBA", (64, 64), (17, 28, 49, 255))
            draw = ImageDraw.Draw(image)
            draw.rounded_rectangle((6, 6, 58, 58), radius=14, fill=(94, 234, 212, 255))
            draw.text((19, 22), "GG", fill=(4, 16, 20, 255))
            return image

    def show_from_tray(self) -> None:
        self.hidden_to_tray = False
        self.deiconify()
        self.state("normal")
        self.lift()
        self.focus_force()

    def on_close(self) -> None:
        self.exit_app()

    def exit_app(self) -> None:
        if self.tray_icon:
            try:
                self.tray_icon.stop()
            except Exception:
                pass
            self.tray_icon = None
            self.tray_running = False
        if self.sidebar_logo_animation_job:
            self.after_cancel(self.sidebar_logo_animation_job)
            self.sidebar_logo_animation_job = None
        if self.functions_page:
            self.functions_page.stop()
        if self.stockpile_page:
            self.stockpile_page.stop()
        self.destroy()


if __name__ == "__main__":
    FelbApp().mainloop()
