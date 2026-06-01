import ctypes
import base64
from datetime import datetime, timezone
import os
from pathlib import Path
import subprocess
import sys
import tempfile
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
except Exception:  # pragma: no cover - tray is optional until dependencies are installed.
    pystray = None

try:
    from PIL import Image, ImageDraw, ImageTk
except Exception:  # pragma: no cover - visual assets degrade to text-only fallbacks.
    Image = None
    ImageDraw = None
    ImageTk = None

from app_update import check_latest_release, download_update, fetch_release_description, launch_updater
from functions_category import FunctionsCategory, SettingsCategory
from i18n import SUPPORTED_LANGUAGES, Translator
from item_search_category import ItemSearchCategory
from chat_category import HomeChatPanel
from notifications_category import NotificationsCategory
from settings_store import load_settings, save_settings, selected_language
from steam_profile import SteamProfile, get_local_steam_profile
from stockpile_category import StockpileCategory


APP_TITLE = "GG Coalition"
APP_EXE_NAME = f"{APP_TITLE}.exe"
UPDATER_EXE_NAME = "GG Updater.exe"
APP_VERSION = "1.5.1"
UPDATE_REPO = "ryan1235/aplicativo"  # Exemplo: "seu-usuario/gg-coalition"
FOXHOLE_APP_ID = "505460"
SIDEBAR_WIDTH = 302
BASE_DIR = Path(__file__).resolve().parent
ICON_PATH = BASE_DIR / "img" / "ggimege.gif"
ICON_ICO_PATH = BASE_DIR / "img" / "app_icon.ico"
WALLPAPER_PATH = BASE_DIR / "img" / "wallpeper.png"
ICON_MENU_DIR = BASE_DIR / "img" / "iconmenu"
FOXHOLE_PROCESS_NAMES = ("war-win64-shipping.exe", "foxhole.exe")
FOXHOLE_PATH_HINTS = ("\\steamapps\\common\\foxhole\\", "/steamapps/common/foxhole/")
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
MAX_SPLASH_FRAMES = 5000

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
            bg_color=parent_surface_color(parent, COLORS["bg"]),
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
        self.home_online_users_var = tk.StringVar(value=self.tr.t("home.chat.online_empty"))
        self.foxhole_running = False
        self.foxhole_started_at: datetime | None = None
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
        self.nav_icon_images: dict[str, object] = {}
        self.wallpaper_source = None
        self.wallpaper_photo: tk.PhotoImage | None = None
        self.wallpaper_resize_job: str | None = None
        self.functions_page: FunctionsCategory | None = None
        self.settings_page: SettingsCategory | None = None
        self.stockpile_page: StockpileCategory | None = None
        self.notifications_page: NotificationsCategory | None = None
        self.item_search_page: ItemSearchCategory | None = None
        self.home_chat_panel: HomeChatPanel | None = None
        self.home_online_frame: tk.Frame | None = None
        self.home_online_avatar_cache: dict[str, tk.PhotoImage] = {}
        self.home_online_avatar_labels: dict[str, list[tk.Label]] = {}
        self.home_online_pending_avatars: set[str] = set()
        self.home_online_tooltip: tk.Toplevel | None = None
        self.sidebar: tk.Frame | None = None
        self.sidebar_canvas: tk.Canvas | None = None
        self.sidebar_inner: tk.Frame | None = None
        self.menu_button: tk.Button | None = None
        self.sidebar_visible = False
        self.pages: dict[str, tk.Widget] = {}
        self.nav_buttons: dict[str, tk.Button] = {}
        self.language_buttons: dict[str, tk.Button] = {}
        self.quick_stock_button: tk.Widget | None = None
        self.ui_text: dict[str, tk.Widget] = {}
        self.current_page = ""
        self.tray_icon = None
        self.tray_running = False
        self.hidden_to_tray = False

        self.apply_pending_updater_update()
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
        self.protocol("WM_DELETE_WINDOW", self.request_close)
        self.bind("<Unmap>", self.on_unmap, add="+")

    def load_app_icon(self) -> None:
        if ICON_ICO_PATH.exists():
            try:
                self.iconbitmap(default=str(ICON_ICO_PATH))
            except tk.TclError:
                pass
        if not ICON_PATH.exists():
            return
        try:
            self.app_icon_image = tk_photo_from_path(ICON_PATH)
            self.iconphoto(True, self.app_icon_image)
        except tk.TclError:
            self.app_icon_image = None

    def apply_pending_updater_update(self) -> None:
        pending_files = sorted(BASE_DIR.rglob("*.new"), key=lambda path: len(path.parts))
        if not pending_files:
            return
        for pending_path in pending_files:
            target_name = pending_path.name[:-4]
            if not target_name:
                continue
            target_path = pending_path.with_name(target_name)
            backup_path = target_path.with_name(f"{target_path.name}.old")
            try:
                if backup_path.exists():
                    backup_path.unlink()
                if target_path.exists():
                    target_path.replace(backup_path)
                try:
                    pending_path.replace(target_path)
                except OSError:
                    if backup_path.exists() and not target_path.exists():
                        backup_path.replace(target_path)
                    raise
                if backup_path.exists():
                    try:
                        backup_path.unlink()
                    except OSError:
                        pass
                print(f"[Updater] pending file applied: {target_path}", flush=True)
            except Exception as exc:
                print(f"[Updater] pending file apply failed ({pending_path}): {exc}", flush=True)

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
                    delay = max(45, int(frame.info.get("duration", image.info.get("duration", 85))))
                    frame = self.prepare_icon_frame(frame.copy(), size, crop=False)
                    frames.append((ImageTk.PhotoImage(frame), delay))
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

            image = self.prepare_icon_frame(Image.open(ICON_PATH), 92, crop=False)
            return ImageTk.PhotoImage(image)
        except Exception:
            try:
                return tk_photo_from_path(ICON_PATH).subsample(5, 5)
            except tk.TclError:
                return None

    @staticmethod
    def prepare_icon_frame(frame, size: int, *, crop: bool = True):
        from PIL import Image

        image = frame.convert("RGBA")
        bbox = image.getbbox() if crop else None
        if crop and bbox:
            image = image.crop(bbox)
        image.thumbnail((size, size), Image.LANCZOS)
        canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        x = (size - image.width) // 2
        y = (size - image.height) // 2
        canvas.alpha_composite(image, (x, y))
        return canvas

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
        self.maximize_main_window()
        self.after(650, self.run_startup_prompt_sequence)

    def maximize_main_window(self) -> None:
        try:
            self.state("zoomed")
            return
        except tk.TclError:
            pass
        try:
            width = self.winfo_screenwidth()
            height = self.winfo_screenheight()
            self.geometry(f"{width}x{height}+0+0")
        except tk.TclError:
            pass

    def configure_styles(self) -> None:
        self.style.configure(
            "Vertical.TScrollbar",
            background=COLORS["hover"],
            troughcolor=COLORS["glass"],
            bordercolor=COLORS["glass"],
            lightcolor=COLORS["hover"],
            darkcolor=COLORS["hover"],
            arrowcolor=COLORS["accent_2"],
            relief="flat",
            width=10,
        )
        self.style.map("Vertical.TScrollbar", background=[("active", COLORS["accent_2"])])
        self.style.configure(
            "Horizontal.TScrollbar",
            background=COLORS["hover"],
            troughcolor=COLORS["glass"],
            bordercolor=COLORS["glass"],
            lightcolor=COLORS["hover"],
            darkcolor=COLORS["hover"],
            arrowcolor=COLORS["accent_2"],
            relief="flat",
            width=10,
        )
        self.style.map("Horizontal.TScrollbar", background=[("active", COLORS["accent_2"])])
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
        self.settings_page = SettingsCategory(page_host, self.functions_page, self.tr)
        self.stockpile_page = StockpileCategory(page_host, self.tr, self.functions_page.notify_stockpile_success)
        self.notifications_page = NotificationsCategory(page_host, self.tr)
        self.item_search_page = ItemSearchCategory(page_host, self.tr)

        self.pages["inicio"] = command_page
        self.pages["ferramentas"] = self.functions_page
        self.pages["configuracoes"] = self.settings_page
        self.pages["stockpile"] = self.stockpile_page
        self.pages["notificacoes"] = self.notifications_page
        self.pages["item_search"] = self.item_search_page

        command_page.grid(row=0, column=0, sticky="nsew")
        self.functions_page.grid(row=0, column=0, sticky="nsew")
        self.settings_page.grid(row=0, column=0, sticky="nsew")
        self.stockpile_page.grid(row=0, column=0, sticky="nsew")
        self.notifications_page.grid(row=0, column=0, sticky="nsew")
        self.item_search_page.grid(row=0, column=0, sticky="nsew")
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
        self.nav_buttons["inicio"] = self.nav_button(sidebar, "home", self.tr.t("nav.home"), lambda: self.show_page("inicio"), row=3)

        self.section_label(sidebar, self.tr.t("sidebar.tools"), 4, pady=(20, 6), key="section_tools")
        self.nav_buttons["ferramentas"] = self.nav_button(sidebar, "autoclicker", self.tr.t("nav.auto_clicker"), lambda: self.show_page("ferramentas"), row=5)
        self.nav_buttons["stockpile"] = self.nav_button(sidebar, "estoque", self.tr.t("stockpile.nav"), lambda: self.show_page("stockpile"), row=6)
        self.nav_buttons["notificacoes"] = self.nav_button(sidebar, "noti", self.tr.t("notifications.nav"), lambda: self.show_page("notificacoes"), row=7)
        self.nav_buttons["item_search"] = self.nav_button(sidebar, "buscar", self.tr.t("item_search.nav"), lambda: self.show_page("item_search"), row=8)

        self.section_label(sidebar, self.tr.t("sidebar.settings"), 9, pady=(20, 6), key="section_settings")
        self.nav_buttons["configuracoes"] = self.nav_button(sidebar, "overlay", self.tr.t("nav.settings"), lambda: self.show_page("configuracoes"), row=10)
        tk.Label(sidebar, text="", bg=COLORS["sidebar"]).grid(row=11, column=0, pady=80)

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

    def load_nav_icon(self, name: str, size: int = 24):
        key = f"{name}:{size}"
        if key in self.nav_icon_images:
            return self.nav_icon_images[key]
        path = ICON_MENU_DIR / f"{name}.png"
        if not path.exists():
            return None
        if Image is None:
            try:
                icon = tk.PhotoImage(file=str(path))
                factor = max(1, math.ceil(max(icon.width(), icon.height()) / size))
                if factor > 1:
                    icon = icon.subsample(factor, factor)
                self.nav_icon_images[key] = icon
                return icon
            except tk.TclError:
                return None
        image = Image.open(path).convert("RGBA")
        image.thumbnail((size, size), Image.LANCZOS)
        canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        canvas.alpha_composite(image, ((size - image.width) // 2, (size - image.height) // 2))
        if ctk is not None and hasattr(ctk, "CTkImage"):
            icon = ctk.CTkImage(light_image=canvas, dark_image=canvas, size=(size, size))
        elif ImageTk is not None:
            icon = ImageTk.PhotoImage(canvas)
        else:
            return None
        self.nav_icon_images[key] = icon
        return icon

    def nav_button(self, parent: tk.Frame, icon: str, text: str, command, row: int):
        image = self.load_nav_icon(icon)
        button = modern_button(
            parent,
            text=text,
            command=command,
            color=COLORS["sidebar"],
            text_color=COLORS["muted"],
            hover=COLORS["hover"],
            height=46,
            font=("Segoe UI", 11, "bold"),
        )
        if image is not None:
            button.configure(image=image, compound="left")
        else:
            button.configure(text=f"{icon.upper()}   {text}")
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
        self.quick_stock_button = modern_button(
            language_box,
            text=self.tr.t("stockpile.nav"),
            command=lambda: self.show_page("stockpile"),
            color=COLORS["card"],
            text_color=COLORS["accent_2"],
            hover=COLORS["card_2"],
            height=30,
            font=("Segoe UI", 9, "bold"),
        )
        self.quick_stock_button.grid(row=1, column=0, columnspan=4, sticky="ew", pady=(6, 0))

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
        self.render_steam_profile(authenticate_chat=False)
        self.render_foxhole_status()
        if self.stockpile_page:
            self.stockpile_page.load_api_snapshot()
        if self.item_search_page:
            self.item_search_page.load_items()

    def refresh_language_texts(self) -> None:
        text_updates = {
            "brand_subtitle": self.tr.t("app.subtitle"),
            "section_navigation": self.tr.t("sidebar.navigation"),
            "section_tools": self.tr.t("sidebar.tools"),
            "section_settings": self.tr.t("sidebar.settings"),
            "header_title": self.tr.t("header.title"),
            "header_subtitle": self.tr.t("header.subtitle"),
            "home_eyebrow": self.tr.t("home.eyebrow"),
            "home_title": self.tr.t("home.title"),
            "home_body": self.tr.t("home.body"),
            "home_online_title": self.tr.t("home.online_title"),
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
        self.update_home_online_users(getattr(self.home_chat_panel, "online_users", []))
        nav_texts = {
            "inicio": self.tr.t("nav.home"),
            "ferramentas": self.tr.t("nav.auto_clicker"),
            "configuracoes": self.tr.t("nav.settings"),
            "stockpile": self.tr.t("stockpile.nav"),
            "notificacoes": self.tr.t("notifications.nav"),
            "item_search": self.tr.t("item_search.nav"),
        }
        for key, text in nav_texts.items():
            button = self.nav_buttons.get(key)
            if button:
                button.configure(text=text)
        for language, button in self.language_buttons.items():
            button.configure(bg=COLORS["card_2"] if language == self.tr.language else COLORS["card"])
        if self.quick_stock_button:
            self.quick_stock_button.configure(text=self.tr.t("stockpile.nav"))
        if self.functions_page and hasattr(self.functions_page, "refresh_language"):
            self.functions_page.refresh_language(self.tr)
        if self.settings_page and hasattr(self.settings_page, "refresh_language"):
            self.settings_page.refresh_language(self.tr)
        if self.stockpile_page and hasattr(self.stockpile_page, "refresh_language"):
            self.stockpile_page.refresh_language(self.tr)
        if self.notifications_page and hasattr(self.notifications_page, "refresh_language"):
            self.notifications_page.refresh_language(self.tr)
        if self.item_search_page and hasattr(self.item_search_page, "refresh_language"):
            self.item_search_page.refresh_language(self.tr)
        if self.home_chat_panel and hasattr(self.home_chat_panel, "refresh_language"):
            self.home_chat_panel.refresh_language(self.tr)

    def update_home_online_users(self, users: list[dict[str, object]] | None = None) -> None:
        users = users or []
        self.render_home_online_avatars(users)
        if not users:
            self.home_online_users_var.set(self.tr.t("home.chat.online_empty"))
            return
        local_steam_id = str(getattr(self.profile, "steam_id", "") or "")
        names: list[str] = []
        for user in users:
            steam_id = str(user.get("steamId") or user.get("steam_id") or "")
            if local_steam_id and steam_id == local_steam_id:
                continue
            name = str(user.get("mention") or user.get("personaname") or user.get("nickname") or user.get("name") or steam_id or "user").lstrip("@")
            names.append(f"@{name}")
            if len(names) >= 8:
                break
        count = len(users)
        suffix = ", ".join(names) if names else self.tr.t("home.chat.only_you_online")
        self.home_online_users_var.set(f"{self.tr.t('home.chat.online_count', count=count)} - {suffix}")

    def render_home_online_avatars(self, users: list[dict[str, object]]) -> None:
        if not self.home_online_frame:
            return
        for child in self.home_online_frame.winfo_children():
            child.destroy()
        self.home_online_avatar_labels = {}
        if not users:
            return
        for index, user in enumerate(users[:12]):
            name = self.online_user_name(user)
            avatar_url = self.online_user_avatar_url(user)
            avatar = self.get_home_online_avatar(avatar_url)
            label = tk.Label(
                self.home_online_frame,
                image=avatar,
                bg=COLORS["glass"],
                bd=0,
                cursor="hand2",
            )
            label.image = avatar
            label.grid(row=0, column=index, sticky="w", padx=(0, 7))
            if avatar_url:
                self.home_online_avatar_labels.setdefault(avatar_url, []).append(label)
            label.bind("<Enter>", lambda event, item=user: self.show_home_online_tooltip(event, item))
            label.bind("<Leave>", lambda _event: self.hide_home_online_tooltip())
        remaining = len(users) - 12
        if remaining > 0:
            tk.Label(
                self.home_online_frame,
                text=f"+{remaining}",
                bg="#10233a",
                fg=COLORS["accent"],
                font=("Segoe UI", 9, "bold"),
                padx=9,
                pady=7,
            ).grid(row=0, column=12, sticky="w")

    def online_user_name(self, user: dict[str, object]) -> str:
        return str(user.get("mention") or user.get("personaname") or user.get("nickname") or user.get("name") or user.get("steamId") or user.get("steam_id") or "user").lstrip("@")

    def online_user_avatar_url(self, user: dict[str, object]) -> str:
        return str(user.get("avatarmedium") or user.get("avatarfull") or user.get("avatar") or "")

    def get_home_online_avatar(self, url: str, size: int = 34) -> tk.PhotoImage:
        if not url:
            return self.home_online_placeholder_avatar(size)
        cached = self.home_online_avatar_cache.get(url)
        if cached:
            return cached
        if url not in self.home_online_pending_avatars:
            self.home_online_pending_avatars.add(url)
            threading.Thread(target=self.load_home_online_avatar_async, args=(url, size), daemon=True).start()
        return self.home_online_placeholder_avatar(size)

    def home_online_placeholder_avatar(self, size: int = 34) -> tk.PhotoImage:
        key = f"placeholder:{size}"
        cached = self.home_online_avatar_cache.get(key)
        if cached:
            return cached
        if Image is not None and ImageDraw is not None and ImageTk is not None:
            image = Image.new("RGBA", (size, size), "#1d3353")
            draw = ImageDraw.Draw(image)
            draw.rectangle((0, 0, size - 1, size - 1), outline="#5eead4")
            draw.ellipse((size * 0.30, size * 0.16, size * 0.70, size * 0.52), fill="#8ab4ff")
            draw.rectangle((size * 0.22, size * 0.58, size * 0.78, size * 0.82), fill="#8ab4ff")
            photo = ImageTk.PhotoImage(image)
        else:
            photo = tk.PhotoImage(width=size, height=size)
            photo.put("#1d3353", to=(0, 0, size, size))
        self.home_online_avatar_cache[key] = photo
        return photo

    def load_home_online_avatar_async(self, url: str, size: int) -> None:
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "GG Coalition/1.0", "Accept": "image/*,*/*;q=0.8"})
            with urllib.request.urlopen(request, timeout=10) as response:
                data = response.read(2 * 1024 * 1024)
            if Image is not None and ImageTk is not None:
                import io

                image = Image.open(io.BytesIO(data)).convert("RGBA").resize((size, size))
                photo = ImageTk.PhotoImage(image)
            else:
                photo = tk.PhotoImage(data=base64.b64encode(data).decode("ascii"))
            self.after(0, self.store_home_online_avatar, url, photo)
        except Exception:
            self.home_online_pending_avatars.discard(url)

    def store_home_online_avatar(self, url: str, photo: tk.PhotoImage) -> None:
        self.home_online_avatar_cache[url] = photo
        self.home_online_pending_avatars.discard(url)
        for label in self.home_online_avatar_labels.get(url, []):
            try:
                label.configure(image=photo)
                label.image = photo
            except tk.TclError:
                pass

    def show_home_online_tooltip(self, event, user: dict[str, object]) -> None:
        self.hide_home_online_tooltip()
        name = self.online_user_name(user)
        duration = self.format_online_duration(user)
        tooltip = tk.Toplevel(self)
        self.home_online_tooltip = tooltip
        tooltip.overrideredirect(True)
        tooltip.attributes("-topmost", True)
        frame = tk.Frame(tooltip, bg="#07111f", highlightthickness=1, highlightbackground="#5eead4")
        frame.pack(fill="both", expand=True)
        tk.Label(frame, text=f"@{name}", bg="#07111f", fg=COLORS["text"], font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=10, pady=(8, 1))
        tk.Label(frame, text=duration, bg="#07111f", fg=COLORS["accent"], font=("Segoe UI", 8)).pack(anchor="w", padx=10, pady=(0, 8))
        tooltip.update_idletasks()
        tooltip.geometry(f"+{event.x_root + 12}+{event.y_root + 12}")

    def hide_home_online_tooltip(self) -> None:
        try:
            if self.home_online_tooltip and self.home_online_tooltip.winfo_exists():
                self.home_online_tooltip.destroy()
        except tk.TclError:
            pass
        self.home_online_tooltip = None

    def format_online_duration(self, user: dict[str, object]) -> str:
        value = (
            user.get("onlineSince")
            or user.get("online_since")
            or user.get("connectedAt")
            or user.get("connected_at")
            or user.get("lastSeenAt")
            or user.get("last_seen_at")
            or user.get("updatedAt")
            or user.get("updated_at")
            or user.get("createdAt")
            or user.get("created_at")
        )
        if not value:
            return self.tr.t("home.online_duration_unknown")
        try:
            text = str(value).strip()
            if text.endswith("Z"):
                text = f"{text[:-1]}+00:00"
            moment = datetime.fromisoformat(text)
            if moment.tzinfo is None:
                moment = moment.replace(tzinfo=timezone.utc)
            seconds = max(0, int((datetime.now(timezone.utc) - moment.astimezone(timezone.utc)).total_seconds()))
            return self.tr.t("home.online_duration", duration=self.format_short_duration(seconds))
        except Exception:
            return self.tr.t("home.online_duration_unknown")

    def format_short_duration(self, seconds: int) -> str:
        minutes = seconds // 60
        if minutes < 1:
            return self.tr.t("duration.less_minute")
        if minutes < 60:
            return self.tr.t("duration.minutes", minutes=minutes)
        hours = minutes // 60
        remaining_minutes = minutes % 60
        if hours < 24:
            return self.tr.t("duration.hours", hours=hours, minutes=remaining_minutes)
        days = hours // 24
        return self.tr.t("duration.days", days=days)

    def build_home_page(self, parent: tk.Frame) -> tk.Frame:
        page = modern_frame(parent, COLORS["bg"], radius=0)
        page.columnconfigure(0, weight=1)
        page.columnconfigure(1, weight=0)
        page.rowconfigure(0, weight=1)

        canvas = tk.Canvas(page, bg=COLORS["bg"], highlightthickness=0, bd=0)
        canvas.grid(row=0, column=0, sticky="nsew")
        if ctk is not None:
            scrollbar = ctk.CTkScrollbar(
                page,
                orientation="vertical",
                command=canvas.yview,
                width=10,
                fg_color=COLORS["bg"],
                button_color=COLORS["card_2"],
                button_hover_color=COLORS["accent"],
            )
        else:
            scrollbar = ttk.Scrollbar(page, orient="vertical", command=canvas.yview, style="Vertical.TScrollbar")
        scrollbar.grid(row=0, column=1, sticky="ns")
        canvas.configure(yscrollcommand=scrollbar.set)

        hero = modern_frame(canvas, COLORS["glass"], radius=6, border=1, border_color="#203857")
        hero_window = canvas.create_window(24, 24, window=hero, anchor="nw", width=760)
        self.ui_text["home_eyebrow"] = tk.Label(hero, text="", bg=COLORS["glass"], fg=COLORS["accent_2"], font=("Segoe UI", 1))
        self.ui_text["home_title"] = tk.Label(hero, text=self.tr.t("home.title"), bg=COLORS["glass"], fg=COLORS["text"], font=("Segoe UI", 22, "bold"))
        self.ui_text["home_title"].pack(
            anchor="w", padx=20, pady=(16, 0)
        )
        status_row = tk.Frame(hero, bg=COLORS["glass"])
        status_pill = tk.Label(
            status_row,
            textvariable=self.user_status_var,
            bg="#10233a",
            fg=COLORS["accent_2"],
            font=("Segoe UI", 9, "bold"),
            padx=8,
            pady=4,
        )
        status_pill.pack(side="left", padx=(0, 8))
        self.ui_text["home_body"] = tk.Label(
            hero,
            text=self.tr.t("home.body"),
            bg=COLORS["glass"],
            fg=COLORS["muted"],
            font=("Segoe UI", 10),
            wraplength=660,
            justify="left",
        )
        self.ui_text["home_body"].pack(anchor="w", padx=20, pady=(6, 12))

        online_panel = tk.Frame(hero, bg=COLORS["glass"])
        online_panel.pack(fill="x", padx=20, pady=(0, 10))
        online_panel.columnconfigure(1, weight=1)
        self.ui_text["home_online_title"] = tk.Label(
            online_panel,
            text=self.tr.t("home.online_title"),
            bg=COLORS["glass"],
            fg=COLORS["accent"],
            font=("Segoe UI", 10, "bold"),
        )
        self.ui_text["home_online_title"].grid(row=0, column=0, sticky="w")
        tk.Label(
            online_panel,
            textvariable=self.home_online_users_var,
            bg=COLORS["glass"],
            fg=COLORS["muted"],
            font=("Segoe UI", 9),
            wraplength=650,
            justify="left",
            anchor="w",
        ).grid(row=0, column=1, sticky="w", padx=(12, 0))
        self.home_online_frame = tk.Frame(online_panel, bg=COLORS["glass"])
        self.home_online_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(7, 0))

        foxhole_panel = tk.Frame(hero, bg=COLORS["glass"], highlightthickness=1, highlightbackground="#203857")
        foxhole_panel.pack(fill="x", padx=20, pady=(0, 16))
        tk.Label(foxhole_panel, text=self.tr.t("home.foxhole_title"), bg=COLORS["glass"], fg=COLORS["text"], font=("Segoe UI", 11, "bold")).grid(
            row=0, column=0, sticky="w", padx=12, pady=(9, 2)
        )
        tk.Label(foxhole_panel, textvariable=self.foxhole_status_var, bg=COLORS["glass"], fg=COLORS["muted"], font=("Segoe UI", 9)).grid(
            row=1, column=0, sticky="w", padx=12, pady=(0, 9)
        )
        self.foxhole_button = modern_button(
            foxhole_panel,
            text=self.tr.t("home.open_foxhole"),
            command=self.open_foxhole,
            color=COLORS["accent"],
            text_color=COLORS["accent_text"],
            hover=COLORS["accent_2"],
            width=128,
            height=34,
            font=("Segoe UI", 9, "bold"),
        )
        self.foxhole_button.grid(row=0, column=1, rowspan=2, sticky="e", padx=12, pady=9)
        foxhole_panel.columnconfigure(0, weight=1)

        grid = modern_frame(canvas, COLORS["bg"], radius=0)
        grid_window = canvas.create_window(24, 24, window=grid, anchor="nw", width=840)
        grid.columnconfigure(0, weight=1)
        grid.rowconfigure(0, weight=1)
        self.home_chat_panel = HomeChatPanel(grid, self)
        self.home_chat_panel.grid(row=0, column=0, sticky="nsew")

        hero.bind("<Configure>", lambda _event: self.layout_home_sections(canvas, hero_window, grid_window, hero))
        grid.bind("<Configure>", lambda _event: self.layout_home_sections(canvas, hero_window, grid_window, hero))
        canvas.bind("<Configure>", lambda event: self.redraw_home_background(event, hero_window, grid_window, hero))
        self.bind_mousewheel_recursive(page, canvas)
        return page

    def redraw_home_background(self, event, hero_window: int, grid_window: int, hero: tk.Widget) -> None:
        canvas: tk.Canvas = event.widget
        canvas.delete("wallpaper")
        width = max(1, event.width)
        height = max(1, event.height)
        canvas.create_rectangle(0, 0, width, height, fill=COLORS["bg"], outline="", tags="wallpaper")
        canvas.tag_lower("wallpaper")
        canvas.itemconfigure(hero_window, width=min(860, max(320, width - 48)))
        canvas.itemconfigure(grid_window, width=max(320, width - 48))
        self.layout_home_sections(canvas, hero_window, grid_window, hero)

    def layout_home_sections(self, canvas: tk.Canvas, hero_window: int, grid_window: int, hero: tk.Widget) -> None:
        hero_height = max(hero.winfo_reqheight(), hero.winfo_height(), 220)
        canvas.coords(hero_window, 24, 24)
        canvas.coords(grid_window, 24, hero_height + 48)
        canvas.configure(scrollregion=canvas.bbox("all"))

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
        tk.Label(hero, text=self.tr.t("home.eyebrow"), bg=COLORS["card"], fg=COLORS["accent_2"], font=("Segoe UI", 12, "bold")).grid(
            row=0, column=0, sticky="w", padx=20, pady=(18, 4)
        )
        tk.Label(hero, text=self.tr.t("home.title"), bg=COLORS["card"], fg=COLORS["text"], font=("Segoe UI", 24, "bold")).grid(
            row=1, column=0, sticky="w", padx=20
        )
        tk.Label(
            hero,
            text=self.tr.t("home.command_hint"),
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

        self.add_card(grid, self.tr.t("home.card_tools_title"), self.tr.t("home.card_tools_body"), 0, 0)
        self.add_card(grid, self.tr.t("home.card_profile_title"), self.tr.t("home.card_profile_body"), 0, 1)
        self.add_card(grid, self.tr.t("home.card_stockpile_title"), self.tr.t("home.card_stockpile_body"), 1, 0)
        self.add_card(grid, self.tr.t("home.card_foxhole_title"), self.tr.t("home.card_foxhole_body"), 1, 1)

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
        self.current_page = page_name
        for name, page in self.pages.items():
            if name == page_name:
                page.tkraise()
                self.configure_button_color(self.nav_buttons[name], COLORS["card_2"], COLORS["text"])
            else:
                self.configure_button_color(self.nav_buttons[name], COLORS["sidebar"], COLORS["muted"])
        if self.stockpile_page and hasattr(self.stockpile_page, "set_active"):
            self.stockpile_page.set_active(page_name == "stockpile")
        if self.item_search_page and hasattr(self.item_search_page, "set_active"):
            self.item_search_page.set_active(page_name == "item_search")
        if self.home_chat_panel and hasattr(self.home_chat_panel, "set_active"):
            self.home_chat_panel.set_active(page_name == "inicio")

    def open_chat_from_overlay(self) -> None:
        try:
            self.deiconify()
            self.state("normal")
        except tk.TclError:
            pass
        self.hidden_to_tray = False
        self.show_page("inicio")
        self.after(80, self.focus_home_chat)
        try:
            self.lift()
            self.focus_force()
        except tk.TclError:
            pass

    def focus_home_chat(self) -> None:
        if not self.home_chat_panel:
            return
        try:
            self.home_chat_panel.scroll_messages_to_bottom()
            self.home_chat_panel.message_entry.focus_set()
        except tk.TclError:
            pass

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
        print(
            "[SteamProfile] refreshed steam_id=%r persona=%r account=%r avatar=%r"
            % (
                getattr(self.profile, "steam_id", None),
                getattr(self.profile, "persona_name", None),
                getattr(self.profile, "account_name", None),
                str(getattr(self.profile, "avatar_path", None)) if getattr(self.profile, "avatar_path", None) else None,
            ),
            flush=True,
        )
        self.render_steam_profile(authenticate_chat=True)

    def render_steam_profile(self, *, authenticate_chat: bool) -> None:
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
        if authenticate_chat and self.home_chat_panel and hasattr(self.home_chat_panel, "authenticate"):
            self.home_chat_panel.authenticate()

    def refresh_foxhole_status(self) -> None:
        running, started_at = self.get_foxhole_process_state()
        self.foxhole_running = running
        self.foxhole_started_at = started_at
        self.render_foxhole_status()

    def render_foxhole_status(self) -> None:
        running = self.foxhole_running
        started_at = getattr(self, "foxhole_started_at", None)
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

    def run_startup_prompt_sequence(self) -> None:
        self.check_for_updates(on_done=self.run_post_update_prompts)

    def run_post_update_prompts(self) -> None:
        self.configure_windows_startup()
        self.show_release_notes_if_needed()

    def show_release_notes_if_needed(self) -> None:
        self.settings = load_settings()
        app_settings = self.settings.setdefault("app", {})
        if app_settings.get("last_release_notes_version") == APP_VERSION:
            return
        self.show_release_notes_dialog()

    def show_release_notes_dialog(self) -> None:
        dialog = ctk.CTkToplevel(self) if ctk is not None else tk.Toplevel(self)
        dialog.title(self.tr.t("release.title", version=APP_VERSION))
        dialog.geometry("520x390")
        dialog.resizable(False, False)
        configure_surface(dialog, COLORS["bg"])
        dialog.transient(self)
        dialog.grab_set()
        dialog.update_idletasks()
        x = self.winfo_rootx() + max(0, (self.winfo_width() - 520) // 2)
        y = self.winfo_rooty() + max(0, (self.winfo_height() - 390) // 2)
        dialog.geometry(f"520x390+{x}+{y}")

        panel = modern_frame(dialog, COLORS["card"], radius=22, border=1, border_color=COLORS["line"])
        panel.pack(fill="both", expand=True, padx=16, pady=16)
        tk.Label(
            panel,
            text=self.tr.t("release.heading", version=APP_VERSION),
            bg=COLORS["card"],
            fg=COLORS["text"],
            font=("Segoe UI", 18, "bold"),
        ).pack(anchor="w", padx=22, pady=(20, 4))
        tk.Label(
            panel,
            text=self.tr.t("release.subtitle"),
            bg=COLORS["card"],
            fg=COLORS["muted"],
            font=("Segoe UI", 10),
            wraplength=450,
            justify="left",
        ).pack(anchor="w", padx=22, pady=(0, 14))

        notes = tk.Text(
            panel,
            height=9,
            bg=COLORS["soft"],
            fg=COLORS["text"],
            insertbackground=COLORS["accent"],
            relief="flat",
            padx=14,
            pady=12,
            font=("Segoe UI", 10),
            wrap="word",
        )
        notes.pack(fill="both", expand=True, padx=22, pady=(0, 16))
        fallback_notes = self.tr.t("release.body")
        notes.insert("1.0", fallback_notes)
        notes.configure(state="disabled")
        self.load_release_notes_from_github(notes, fallback_notes)

        actions = modern_frame(panel, COLORS["card"], radius=0)
        actions.pack(fill="x", padx=22, pady=(0, 18))
        def close_release_notes() -> None:
            self.settings = load_settings()
            app_settings = self.settings.setdefault("app", {})
            app_settings["last_release_notes_version"] = APP_VERSION
            save_settings(self.settings)
            dialog.grab_release()
            dialog.destroy()

        modern_button(
            actions,
            text=self.tr.t("release.ok"),
            command=close_release_notes,
            color=COLORS["accent"],
            text_color=COLORS["accent_text"],
            hover=COLORS["accent_2"],
            height=40,
        ).pack(side="right")
        dialog.protocol("WM_DELETE_WINDOW", close_release_notes)

    def load_release_notes_from_github(self, notes: tk.Text, fallback_notes: str) -> None:
        def worker() -> None:
            try:
                release_text = fetch_release_description(UPDATE_REPO, APP_VERSION)
            except Exception as exc:
                print(f"[ReleaseNotes] fetch failed: {exc}", flush=True)
                return
            if not release_text or release_text.strip() == fallback_notes.strip():
                return
            self.after(0, self.apply_release_notes_text, notes, release_text)

        threading.Thread(target=worker, daemon=True).start()

    def apply_release_notes_text(self, notes: tk.Text, release_text: str) -> None:
        try:
            if not notes.winfo_exists():
                return
            notes.configure(state="normal")
            notes.delete("1.0", "end")
            notes.insert("1.0", release_text)
            notes.configure(state="disabled")
        except tk.TclError:
            pass

    def configure_windows_startup(self) -> None:
        self.settings = load_settings()
        app_settings = self.settings.setdefault("app", {})
        if app_settings.get("start_with_windows"):
            try:
                self.set_start_with_windows(True)
            except Exception as exc:
                print(f"[Startup] failed: {exc}", flush=True)
            return

        if not app_settings.get("startup_prompted"):
            app_settings["startup_prompted"] = True
            app_settings["start_with_windows"] = False
            save_settings(self.settings)

    def startup_target_and_args(self) -> tuple[Path, str]:
        if getattr(sys, "frozen", False):
            return Path(sys.executable).resolve(), ""

        python_exe = Path(sys.executable).resolve()
        pythonw = python_exe.with_name("pythonw.exe")
        if pythonw.exists():
            python_exe = pythonw
        return python_exe, f'"{(BASE_DIR / "felb_app.py").resolve()}"'

    def startup_command(self) -> str:
        target, arguments = self.startup_target_and_args()
        return f'"{target}" {arguments}'.strip()

    def startup_dir(self) -> Path:
        return Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"

    def startup_shortcut_path(self) -> Path:
        return self.startup_dir() / f"{APP_TITLE}.lnk"

    def create_startup_shortcut(self) -> None:
        target, arguments = self.startup_target_and_args()
        shortcut_path = self.startup_shortcut_path()
        shortcut_path.parent.mkdir(parents=True, exist_ok=True)
        icon_path = ICON_ICO_PATH if ICON_ICO_PATH.exists() else target
        powershell_script = (
            "param($shortcutPath,$targetPath,$arguments,$workingDirectory,$iconLocation,$description);"
            "$shell=New-Object -ComObject WScript.Shell;"
            "$shortcut=$shell.CreateShortcut($shortcutPath);"
            "$shortcut.TargetPath=$targetPath;"
            "$shortcut.Arguments=$arguments;"
            "$shortcut.WorkingDirectory=$workingDirectory;"
            "$shortcut.IconLocation=$iconLocation;"
            "$shortcut.Description=$description;"
            "$shortcut.Save();"
        )
        subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                powershell_script,
                str(shortcut_path),
                str(target),
                arguments,
                str(BASE_DIR),
                str(icon_path),
                APP_TITLE,
            ],
            check=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )

    def create_startup_entry(self) -> None:
        self.create_startup_shortcut()

    def remove_startup_shortcut(self) -> None:
        shortcut_path = self.startup_shortcut_path()
        if shortcut_path.exists():
            shortcut_path.unlink()

    def set_start_with_windows(self, enabled: bool) -> None:
        import winreg

        run_key = r"Software\Microsoft\Windows\CurrentVersion\Run"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, run_key, 0, winreg.KEY_SET_VALUE) as key:
            if enabled:
                self.create_startup_entry()
                if getattr(sys, "frozen", False):
                    winreg.SetValueEx(key, APP_TITLE, 0, winreg.REG_SZ, self.startup_command())
                else:
                    try:
                        winreg.DeleteValue(key, APP_TITLE)
                    except FileNotFoundError:
                        pass
            else:
                try:
                    winreg.DeleteValue(key, APP_TITLE)
                except FileNotFoundError:
                    pass
                self.remove_startup_shortcut()

    def check_for_updates(self, on_done=None) -> None:
        if not UPDATE_REPO:
            if on_done:
                self.after(0, on_done)
            return

        def worker() -> None:
            try:
                update = check_latest_release(UPDATE_REPO, APP_VERSION)
            except Exception as exc:
                print(f"[Updater] check failed: {exc}", flush=True)
                if on_done:
                    self.after(0, on_done)
                return
            if update:
                self.after(0, lambda: self.offer_update(update, on_done=on_done))
            elif on_done:
                self.after(0, on_done)

        threading.Thread(target=worker, daemon=True).start()

    def offer_update(self, update, on_done=None) -> None:
        wants_update = self.ask_update_dialog(update)
        if not wants_update:
            if on_done:
                on_done()
            return

        progress_dialog, progress_text, progress_bar = self.show_update_progress(update.version)

        def worker() -> None:
            try:
                self.after(0, progress_text.set, self.tr.t("update.downloading"))

                def on_download_progress(downloaded: int, total: int) -> None:
                    if total > 0:
                        percent = int((downloaded / total) * 100)
                        mb_done = downloaded / (1024 * 1024)
                        mb_total = total / (1024 * 1024)
                        text = f"{self.tr.t('update.downloading')} {percent}% ({mb_done:.1f}/{mb_total:.1f} MB)"
                        self.after(0, lambda value=percent: progress_bar.configure(mode="determinate", value=value))
                    else:
                        mb_done = downloaded / (1024 * 1024)
                        text = f"{self.tr.t('update.downloading')} {mb_done:.1f} MB"
                    self.after(0, progress_text.set, text)

                zip_path = download_update(update, progress_callback=on_download_progress)
                self.after(0, progress_text.set, self.tr.t("update.launching"))
                launch_updater(zip_path, self.runtime_dir(), self.launch_target())
                self.after(0, self.exit_app)
            except Exception as exc:
                self.after(0, progress_dialog.destroy)
                self.after(0, lambda: messagebox.showerror(self.tr.t("update.error_title"), str(exc), parent=self))
                if on_done:
                    self.after(0, on_done)

        threading.Thread(target=worker, daemon=True).start()

    def ask_update_dialog(self, update) -> bool:
        dialog = ctk.CTkToplevel(self) if ctk is not None else tk.Toplevel(self)
        dialog.title(self.tr.t("update.available_title"))
        dialog.geometry("560x430")
        dialog.resizable(False, False)
        configure_surface(dialog, COLORS["bg"])
        dialog.transient(self)
        dialog.grab_set()
        result = {"value": False}
        dialog.update_idletasks()
        x = self.winfo_rootx() + max(0, (self.winfo_width() - 560) // 2)
        y = self.winfo_rooty() + max(0, (self.winfo_height() - 430) // 2)
        dialog.geometry(f"560x430+{x}+{y}")

        panel = modern_frame(dialog, COLORS["card"], radius=22, border=1, border_color=COLORS["accent"])
        panel.pack(fill="both", expand=True, padx=16, pady=16)
        tk.Label(
            panel,
            text=self.tr.t("update.available_title"),
            bg=COLORS["card"],
            fg=COLORS["text"],
            font=("Segoe UI", 19, "bold"),
        ).pack(anchor="w", padx=22, pady=(20, 4))
        tk.Label(
            panel,
            text=self.tr.t("update.available_body", version=update.version),
            bg=COLORS["card"],
            fg=COLORS["accent_2"],
            font=("Segoe UI", 10, "bold"),
            wraplength=500,
            justify="left",
        ).pack(anchor="w", padx=22, pady=(0, 12))

        release_text = str(getattr(update, "body", "") or "").strip() or str(getattr(update, "name", "") or update.version)
        notes = tk.Text(
            panel,
            height=9,
            bg=COLORS["soft"],
            fg=COLORS["text"],
            insertbackground=COLORS["accent"],
            relief="flat",
            padx=14,
            pady=12,
            font=("Segoe UI", 10),
            wrap="word",
        )
        notes.pack(fill="both", expand=True, padx=22, pady=(0, 16))
        notes.insert("1.0", release_text)
        notes.configure(state="disabled")

        actions = modern_frame(panel, COLORS["card"], radius=0)
        actions.pack(fill="x", padx=22, pady=(0, 18))

        def close(value: bool) -> None:
            result["value"] = value
            dialog.grab_release()
            dialog.destroy()

        modern_button(
            actions,
            text=self.tr.t("update.later"),
            command=lambda: close(False),
            color=COLORS["soft"],
            text_color=COLORS["text"],
            height=40,
        ).pack(side="right", padx=(10, 0))
        modern_button(
            actions,
            text=self.tr.t("update.install_now"),
            command=lambda: close(True),
            color=COLORS["accent"],
            text_color=COLORS["accent_text"],
            hover=COLORS["accent_2"],
            height=40,
        ).pack(side="right")
        dialog.protocol("WM_DELETE_WINDOW", lambda: close(False))
        self.wait_window(dialog)
        return bool(result["value"])

    def show_update_progress(self, version: str):
        dialog = ctk.CTkToplevel(self) if ctk is not None else tk.Toplevel(self)
        dialog.title(self.tr.t("update.progress_title"))
        dialog.geometry("430x180")
        dialog.resizable(False, False)
        configure_surface(dialog, COLORS["bg"])
        dialog.transient(self)
        dialog.grab_set()
        dialog.update_idletasks()
        x = self.winfo_rootx() + max(0, (self.winfo_width() - 430) // 2)
        y = self.winfo_rooty() + max(0, (self.winfo_height() - 180) // 2)
        dialog.geometry(f"430x180+{x}+{y}")

        panel = modern_frame(dialog, COLORS["card"], radius=22, border=1, border_color=COLORS["line"])
        panel.pack(fill="both", expand=True, padx=16, pady=16)
        tk.Label(panel, text=self.tr.t("update.progress_title"), bg=COLORS["card"], fg=COLORS["text"], font=("Segoe UI", 16, "bold")).pack(
            anchor="w", padx=20, pady=(18, 4)
        )
        progress_text = tk.StringVar(value=self.tr.t("update.download_prepare", version=version))
        tk.Label(panel, textvariable=progress_text, bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI", 10)).pack(
            anchor="w", padx=20, pady=(0, 14)
        )
        bar = ttk.Progressbar(panel, mode="indeterminate", length=340, maximum=100)
        bar.pack(fill="x", padx=20)
        bar.start(12)
        return dialog, progress_text, bar

    def runtime_dir(self) -> Path:
        if getattr(sys, "frozen", False):
            return self.launch_target().parent
        return BASE_DIR

    def launch_target(self) -> Path:
        if getattr(sys, "frozen", False):
            candidates: list[Path] = []
            for value in (sys.argv[0], sys.executable, self.module_file_name()):
                if not value:
                    continue
                try:
                    candidates.append(Path(value).resolve())
                except OSError:
                    continue
            try:
                candidates.append((Path.cwd() / APP_EXE_NAME).resolve())
            except OSError:
                pass
            saved = self.settings.get("app", {}).get("install_exe")
            if saved:
                try:
                    candidates.append(Path(str(saved)).resolve())
                except OSError:
                    pass

            valid = [
                candidate
                for candidate in candidates
                if candidate.exists()
                and candidate.is_file()
                and candidate.suffix.lower() == ".exe"
                and not self.is_temp_runtime_path(candidate)
            ]
            if not valid:
                details = "\n".join(str(candidate) for candidate in candidates)
                raise RuntimeError("Nao consegui identificar o executavel instalado fora da pasta temporaria:\n" + details)
            named = [candidate for candidate in valid if candidate.name.lower() == APP_EXE_NAME.lower()]
            chosen = (named or valid)[0]
            if chosen.exists() and not self.is_temp_runtime_path(chosen):
                self.remember_install_exe(chosen)
            return chosen
        return BASE_DIR / "felb_app.py"

    def module_file_name(self) -> str:
        try:
            buffer = ctypes.create_unicode_buffer(32768)
            ctypes.windll.kernel32.GetModuleFileNameW(None, buffer, len(buffer))
            return buffer.value
        except Exception:
            return ""

    def is_temp_runtime_path(self, path: Path) -> bool:
        try:
            resolved = path.resolve()
            temp_root = Path(tempfile.gettempdir()).resolve()
            if resolved == temp_root or temp_root in resolved.parents:
                return True
            lowered = str(resolved).lower()
            return "onefile" in lowered and ("temp" in lowered or "tmp" in lowered)
        except OSError:
            return False

    def remember_install_exe(self, path: Path) -> None:
        try:
            self.settings = load_settings()
            self.settings.setdefault("app", {})["install_exe"] = str(path)
            save_settings(self.settings)
        except Exception as exc:
            print(f"[Updater] nao consegui salvar install_exe: {exc}", flush=True)

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
        dialog.title(self.tr.t("close.title"))
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
        tk.Label(panel, text=self.tr.t("close.heading"), bg=COLORS["card"], fg=COLORS["text"], font=("Segoe UI", 18, "bold")).pack(
            anchor="w", padx=20, pady=(18, 4)
        )
        tk.Label(
            panel,
            text=self.tr.t("close.body"),
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
                text=self.tr.t("close.remember"),
                variable=remember_var,
                fg_color=COLORS["accent"],
                hover_color=COLORS["accent_2"],
                text_color=COLORS["text"],
                corner_radius=6,
            )
        else:
            checkbox = tk.Checkbutton(
                panel,
                text=self.tr.t("close.remember"),
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
            text=self.tr.t("close.tray"),
            command=lambda: choose("tray"),
            color=COLORS["accent"],
            text_color=COLORS["accent_text"],
            hover=COLORS["accent_2"],
            height=40,
        ).pack(side="left", fill="x", expand=True, padx=(0, 8))
        modern_button(
            actions,
            text=self.tr.t("close.exit"),
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
            self.tr.t("tray.unavailable_title"),
            self.tr.t("tray.unavailable_body"),
            parent=self,
        )

    def ensure_tray_icon(self) -> bool:
        if pystray is None:
            return False
        if self.tray_running:
            return True
        image = self.create_tray_image()
        menu = pystray.Menu(
            pystray.MenuItem(self.tr.t("tray.open"), lambda _icon, _item: self.after(0, self.show_from_tray), default=True),
            pystray.MenuItem(self.tr.t("tray.exit"), lambda _icon, _item: self.after(0, self.exit_app)),
        )
        self.tray_icon = pystray.Icon("GG Coalition", image, "GG Coalition", menu)
        threading.Thread(target=self.tray_icon.run, daemon=True).start()
        self.tray_running = True
        return True

    def create_tray_image(self):
        if Image is None:
            return None
        try:
            image = self.prepare_icon_frame(Image.open(ICON_PATH), 64)
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
        if self.notifications_page:
            self.notifications_page.stop()
        if self.item_search_page:
            self.item_search_page.stop()
        if self.home_chat_panel:
            self.home_chat_panel.stop()
        self.destroy()


if __name__ == "__main__":
    FelbApp().mainloop()
