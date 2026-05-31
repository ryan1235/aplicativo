from pathlib import Path
import ctypes
from datetime import datetime, timezone
import threading
import tkinter as tk
from tkinter import ttk

try:
    import customtkinter as ctk
except ImportError:  # pragma: no cover - optional visual upgrade.
    ctk = None

from app_paths import extracted_dir, resolve_writable_path
from i18n import Translator
from settings_store import load_settings, save_settings
from stockpiler import (
    StockpileWatcher,
    api_item_rows,
    api_last_update,
    request_stockpile_debug,
    warehouse_summaries,
)

try:
    from PIL import Image, ImageTk
except ImportError:  # pragma: no cover - app still runs without icons.
    Image = None
    ImageTk = None


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
STOCKPILE_SOUND_NAMES = ("stoque", "estoque")
SOUND_EXTENSIONS = (".wav", ".mp3", ".wma")


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
        padx=16,
        pady=12,
        font=font,
        cursor="hand2",
    )


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


def stockpile_sound_path() -> Path | None:
    for directory in SOUND_DIRS:
        for name in STOCKPILE_SOUND_NAMES:
            for extension in SOUND_EXTENSIONS:
                path = directory / f"{name}{extension}"
                if path.exists():
                    return path
    return None


def play_stockpile_sound() -> None:
    path = stockpile_sound_path()
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
        alias = f"gg_stockpile_{int(threading.get_ident())}"
        winmm = ctypes.windll.winmm
        winmm.mciSendStringW(f"close {alias}", None, 0, None)
        winmm.mciSendStringW(f'open "{path}" type mpegvideo alias {alias}', None, 0, None)
        winmm.mciSendStringW(f"play {alias}", None, 0, None)
        threading.Timer(8.0, lambda: winmm.mciSendStringW(f"close {alias}", None, 0, None)).start()
    except Exception:
        pass


class StockpileCategory(ttk.Frame):
    def __init__(self, parent: ttk.Widget, translator: Translator | None = None, success_callback=None) -> None:
        super().__init__(parent, style="Panel.TFrame")
        self.tr = translator or Translator()
        self.success_callback = success_callback
        self.settings = load_settings()
        stockpile = self.settings["stockpile"]
        self.watcher: StockpileWatcher | None = None
        self.status_var = tk.StringVar(value=self.tr.t("stockpile.idle"))
        self.sent_count_var = tk.StringVar(value="0")
        self.report_count_var = tk.StringVar(value="0")
        self.item_count_var = tk.StringVar(value="0")
        self.last_stockpile_var = tk.StringVar(value="-")
        self.stockpile_list_var = tk.StringVar(value="-")
        self.warehouse_detail_var = tk.StringVar(value="-")
        self.last_response_var = tk.StringVar(value="-")
        self.api_last_update_var = tk.StringVar(value="-")
        self.selected_warehouse_var = tk.StringVar(value="")
        self.latest_warehouses: list[dict] = []
        self.latest_items: list[dict] = []
        self.icon_images: dict[str, tk.PhotoImage] = {}
        self.search_var = tk.StringVar(value="")
        self.visual_canvas: tk.Canvas | None = None
        self.warehouse_combo: ttk.Combobox | None = None
        self.refresh_job: str | None = None
        self.relative_update_job: str | None = None
        self.visual_item_hitboxes: list[tuple[int, int, int, int, str]] = []
        self.visual_tooltip: tk.Toplevel | None = None
        self.visual_tooltip_label: tk.Label | None = None
        self.visual_tooltip_text = ""
        self.api_last_update_var.trace_add("write", lambda *_args: self.draw_visual_stockpile())
        self.active = False
        self.api_loading = False
        self.file_var = tk.StringVar(value=stockpile.get("watch_file", ""))
        self.api_var = tk.StringVar(value=stockpile.get("api_url", ""))
        self.out_dir_var = tk.StringVar(value=stockpile.get("out_dir", str(extracted_dir())))
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.build()
        self.schedule_relative_update_clock()
        self.load_api_snapshot()
        self.start_watcher()

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

        tk.Label(container, text=self.tr.t("stockpile.title"), bg=COLORS["bg"], fg=COLORS["text"], font=("Segoe UI", 24, "bold")).grid(
            row=0, column=0, sticky="w", padx=22, pady=(20, 2)
        )
        tk.Label(container, text=self.tr.t("stockpile.subtitle"), bg=COLORS["bg"], fg=COLORS["accent_2"], font=("Segoe UI", 11, "bold")).grid(
            row=1, column=0, sticky="w", padx=22, pady=(0, 16)
        )

        card = modern_frame(container, COLORS["card"], radius=24, border=1, border_color=COLORS["line"])
        card.grid(row=2, column=0, sticky="ew", padx=22, pady=(0, 16))
        card.columnconfigure(0, weight=1)

        explanation = tk.Label(
            card,
            text=self.tr.t("stockpile.explain"),
            bg=COLORS["card"],
            fg=COLORS["muted"],
            font=("Segoe UI", 10),
            wraplength=780,
            justify="left",
        )
        explanation.grid(row=0, column=0, sticky="ew", padx=18, pady=(18, 12))

        auto_box = modern_frame(card, COLORS["soft"], radius=16, border=1, border_color="#213854")
        auto_box.grid(row=1, column=0, sticky="ew", padx=18, pady=(4, 18))
        auto_box.columnconfigure(0, weight=1)
        tk.Label(auto_box, text=self.tr.t("stockpile.auto_title"), bg=COLORS["soft"], fg=COLORS["accent"], font=("Segoe UI", 11, "bold")).grid(
            row=0, column=0, sticky="w", padx=14, pady=(12, 2)
        )
        tk.Label(auto_box, text=self.tr.t("stockpile.auto_body"), bg=COLORS["soft"], fg=COLORS["text"], font=("Segoe UI", 10), wraplength=760, justify="left").grid(
            row=1, column=0, sticky="ew", padx=14, pady=(0, 12)
        )

        metrics = modern_frame(container, COLORS["bg"], radius=0)
        metrics.grid(row=3, column=0, sticky="ew", padx=22, pady=(0, 16))
        for column in range(4):
            metrics.columnconfigure(column, weight=1)
        self.metric_card(metrics, self.tr.t("stockpile.metric_sent"), self.sent_count_var, 0, 0)
        self.metric_card(metrics, self.tr.t("stockpile.metric_reports"), self.report_count_var, 0, 1)
        self.metric_card(metrics, self.tr.t("stockpile.metric_items"), self.item_count_var, 0, 2)
        self.metric_card(metrics, self.tr.t("stockpile.metric_last"), self.last_stockpile_var, 0, 3)

        visual_box = modern_frame(container, COLORS["card"], radius=24, border=1, border_color=COLORS["line"])
        visual_box.grid(row=4, column=0, sticky="ew", padx=22, pady=(0, 16))
        visual_box.columnconfigure(0, weight=1)
        visual_head = modern_frame(visual_box, COLORS["card"], radius=0)
        visual_head.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 8))
        visual_head.columnconfigure(0, weight=1)
        tk.Label(visual_head, text=self.tr.t("stockpile.visual_title"), bg=COLORS["card"], fg=COLORS["text"], font=("Segoe UI", 13, "bold")).grid(
            row=0, column=0, sticky="w"
        )
        selector = modern_frame(visual_head, COLORS["card"], radius=0)
        selector.grid(row=0, column=1, sticky="e")
        tk.Label(selector, text=self.tr.t("stockpile.visual_select"), bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI", 9, "bold")).grid(
            row=0, column=0, sticky="e", padx=(0, 8)
        )
        self.warehouse_combo = ttk.Combobox(selector, textvariable=self.selected_warehouse_var, state="readonly", width=34)
        self.warehouse_combo.grid(row=0, column=1, sticky="e")
        self.warehouse_combo.bind("<<ComboboxSelected>>", lambda _event: self.draw_visual_stockpile())
        self.visual_canvas = tk.Canvas(visual_box, height=310, bg="#030303", highlightthickness=0)
        self.visual_canvas.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 14))
        self.visual_canvas.bind("<Configure>", lambda _event: self.draw_visual_stockpile())
        self.visual_canvas.bind("<Motion>", self.on_visual_item_motion)
        self.visual_canvas.bind("<Leave>", lambda _event: self.hide_visual_tooltip())

        status = modern_frame(container, COLORS["soft"], radius=18, border=1, border_color="#213854")
        status.grid(row=5, column=0, sticky="ew", padx=22, pady=(0, 22))
        status.columnconfigure(0, weight=1)
        tk.Label(status, textvariable=self.status_var, bg=COLORS["soft"], fg=COLORS["text"], font=("Segoe UI", 11, "bold"), wraplength=820, justify="left").grid(
            row=0, column=0, sticky="w", padx=16, pady=(12, 2)
        )
        tk.Label(status, textvariable=self.last_response_var, bg=COLORS["soft"], fg=COLORS["accent_2"], font=("Segoe UI", 9, "bold"), wraplength=820, justify="left").grid(
            row=1, column=0, sticky="w", padx=16, pady=(4, 2)
        )
        tk.Label(status, textvariable=self.stockpile_list_var, bg=COLORS["soft"], fg=COLORS["text"], font=("Segoe UI", 9), wraplength=820, justify="left").grid(
            row=2, column=0, sticky="w", padx=16, pady=(4, 2)
        )
        tk.Label(status, text=self.tr.t("stockpile.console_note"), bg=COLORS["soft"], fg=COLORS["muted"], font=("Segoe UI", 9)).grid(row=3, column=0, sticky="w", padx=16, pady=(0, 12))
        self.bind_mousewheel_recursive(outer, canvas)

    def add_label(self, parent: tk.Frame, text: str, row: int) -> None:
        tk.Label(parent, text=text, bg=widget_color(parent, COLORS["card"]), fg=COLORS["muted"], font=("Segoe UI", 10, "bold")).grid(
            row=row, column=0, sticky="w", padx=18, pady=8
        )

    def bind_mousewheel_recursive(self, widget: tk.Widget, canvas: tk.Canvas) -> None:
        def on_mousewheel(event) -> str:
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            return "break"

        widget.bind("<MouseWheel>", on_mousewheel, add="+")
        for child in widget.winfo_children():
            self.bind_mousewheel_recursive(child, canvas)

    def metric_card(self, parent: tk.Frame, title: str, value: tk.StringVar, row: int, column: int) -> None:
        card = modern_frame(parent, COLORS["card"], radius=18, border=1, border_color=COLORS["line"])
        card.grid(row=row, column=column, sticky="nsew", padx=(0 if column == 0 else 8, 0), pady=0)
        tk.Label(card, text=title, bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI", 9, "bold")).pack(
            anchor="w", padx=14, pady=(12, 2)
        )
        tk.Label(card, textvariable=value, bg=COLORS["card"], fg=COLORS["text"], font=("Segoe UI", 14, "bold"), wraplength=170, justify="left").pack(
            anchor="w", padx=14, pady=(0, 12)
        )

    def save_settings(self) -> None:
        self.settings = load_settings()
        self.settings["stockpile"] = {
            "enabled": True,
            "watch_file": self.file_var.get(),
            "api_url": self.api_var.get(),
            "out_dir": str(resolve_writable_path(self.out_dir_var.get())),
            "extract_initial": True,
        }
        resolve_writable_path(self.out_dir_var.get()).mkdir(parents=True, exist_ok=True)
        save_settings(self.settings)

    def refresh_language(self, translator: Translator) -> None:
        self.tr = translator
        for child in self.winfo_children():
            child.destroy()
        self.build()
        self.load_api_snapshot()

    def start_watcher(self) -> None:
        self.save_settings()
        self.stop_watcher(update_status=False)
        self.watcher = StockpileWatcher(
            Path(self.file_var.get()),
            resolve_writable_path(self.out_dir_var.get()),
            self.api_var.get(),
            extract_initial=True,
            sync_interval=300.0,
            status_callback=self.show_status,
        )
        self.watcher.start()
        self.status_var.set(self.tr.t("stockpile.running"))

    def load_api_snapshot(self) -> None:
        if self.api_loading:
            return
        self.api_loading = True
        self.status_var.set(self.tr.t("stockpile.refreshing"))

        def worker() -> None:
            try:
                api_response = request_stockpile_debug(self.api_var.get())
                summaries = warehouse_summaries(api_response)
                message = {
                    "kind": "api_snapshot",
                    "api_response": api_response.get("status_text", "-"),
                    "api_last_update": api_last_update(api_response),
                    "warehouse_summaries": summaries,
                    "items": api_item_rows(api_response),
                    "report_count": len(summaries),
                    "stockpiles": [str(item.get("name", "-")) for item in summaries],
                    "send_count": self.sent_count_var.get(),
                }
                self.show_status(message)
            except Exception as exc:
                self.after(0, self.status_var.set, self.tr.t("stockpile.error", message=str(exc)))
            finally:
                self.api_loading = False

        threading.Thread(target=worker, daemon=True).start()

    def set_active(self, active: bool) -> None:
        self.active = active
        if active:
            self.load_api_snapshot()
            self.schedule_api_refresh()
        else:
            self.cancel_api_refresh()

    def schedule_api_refresh(self) -> None:
        self.cancel_api_refresh()
        if self.active:
            self.refresh_job = self.after(30_000, self.periodic_api_refresh)

    def cancel_api_refresh(self) -> None:
        if self.refresh_job:
            self.after_cancel(self.refresh_job)
            self.refresh_job = None

    def periodic_api_refresh(self) -> None:
        self.refresh_job = None
        if not self.active:
            return
        self.load_api_snapshot()
        self.schedule_api_refresh()

    def show_status(self, message) -> None:
        if isinstance(message, dict):
            stockpiles = message.get("stockpiles") or []
            last_stockpile = stockpiles[-1] if stockpiles else "-"
            stockpile_list = ", ".join(stockpiles[:6]) if stockpiles else "-"
            if len(stockpiles) > 6:
                stockpile_list = f"{stockpile_list} +{len(stockpiles) - 6}"
            self.after(0, self.sent_count_var.set, str(message.get("send_count", 0)))
            self.after(0, self.report_count_var.set, str(message.get("report_count", 0)))
            self.after(0, self.item_count_var.set, str(len(message.get("items") or [])))
            self.after(0, self.last_stockpile_var.set, last_stockpile)
            self.after(0, self.stockpile_list_var.set, self.tr.t("stockpile.detected_list", names=stockpile_list))
            self.after(0, self.last_response_var.set, str(message.get("api_response", "-")))
            self.after(0, self.api_last_update_var.set, str(message.get("api_last_update") or "-"))
            self.latest_warehouses = message.get("warehouse_summaries") or []
            self.latest_items = message.get("items") or []
            self.after(0, self.update_warehouse_dashboard)
            if message.get("kind") == "api_snapshot":
                self.after(0, self.status_var.set, self.tr.t("stockpile.api_loaded"))
            else:
                self.after(0, self.status_var.set, self.tr.t("stockpile.last_sent", count=len(stockpiles)))
                if message.get("upload_reason") == "file_changed" or message.get("payload_changed") is True:
                    self.after(0, self.notify_upload_success, len(stockpiles))
            return

        translated = {
            "running": self.tr.t("stockpile.running"),
            "waiting for Foxhole save file": self.tr.t("stockpile.waiting_file"),
            "stockpile unchanged": self.tr.t("stockpile.unchanged"),
        }.get(message, message)
        if isinstance(message, str) and message.startswith("waiting for Foxhole save file:"):
            path = message.split(":", 1)[1].strip()
            translated = self.tr.t("stockpile.waiting_file_detail", path=path)
        elif isinstance(message, str) and message.startswith("found Foxhole save file:"):
            path = message.split(":", 1)[1].strip()
            self.after(0, lambda value=path: self.remember_discovered_file(value))
            translated = self.tr.t("stockpile.found_file", path=path)
        elif isinstance(message, str) and message.startswith("cannot read Foxhole save file:"):
            translated = self.tr.t("stockpile.read_error", message=message)
        self.after(0, self.status_var.set, translated)

    def remember_discovered_file(self, path: str) -> None:
        self.file_var.set(path)
        self.save_settings()

    def notify_upload_success(self, count: int) -> None:
        text = self.tr.t("stockpile.upload_success", count=count)
        if load_settings().get("app", {}).get("stockpile_sound_enabled", True):
            play_stockpile_sound()
        if self.success_callback:
            self.success_callback(text)

    def stop_watcher(self, update_status: bool = True) -> None:
        if self.watcher:
            self.watcher.stop()
            self.watcher = None
        if update_status:
            self.status_var.set(self.tr.t("stockpile.stopped"))

    def stop(self) -> None:
        self.cancel_api_refresh()
        self.cancel_relative_update_clock()
        if self.visual_tooltip and self.visual_tooltip.winfo_exists():
            self.visual_tooltip.destroy()
        self.stop_watcher(update_status=False)

    def update_warehouse_dashboard(self) -> None:
        self.update_warehouse_selector()
        self.draw_visual_stockpile()

    def update_warehouse_selector(self) -> None:
        if not self.warehouse_combo:
            return
        names = [str(item.get("name", "-")) for item in self.latest_warehouses if item.get("name")]
        self.warehouse_combo.configure(values=names)
        if names and self.selected_warehouse_var.get() not in names:
            self.selected_warehouse_var.set(names[0])
        if not names:
            self.selected_warehouse_var.set("")

    def load_item_icon(self, path: str) -> tk.PhotoImage | None:
        if not path:
            return None
        cached = self.icon_images.get(path)
        if cached:
            return cached
        try:
            if Image and ImageTk:
                image = Image.open(path).convert("RGBA")
                image.thumbnail((32, 32), Image.LANCZOS)
                photo = ImageTk.PhotoImage(image)
            else:
                photo = tk.PhotoImage(file=path)
        except Exception:
            return None
        self.icon_images[path] = photo
        return photo

    def schedule_relative_update_clock(self) -> None:
        self.cancel_relative_update_clock()
        self.relative_update_job = self.after(1000, self.tick_relative_update_clock)

    def cancel_relative_update_clock(self) -> None:
        if self.relative_update_job:
            try:
                self.after_cancel(self.relative_update_job)
            except tk.TclError:
                pass
            self.relative_update_job = None

    def tick_relative_update_clock(self) -> None:
        self.relative_update_job = None
        self.draw_visual_stockpile()
        self.schedule_relative_update_clock()

    def parsed_last_update(self) -> datetime | None:
        value = self.api_last_update_var.get().strip()
        if not value or value == "-":
            return None
        try:
            normalized = value.replace("Z", "+00:00")
            return datetime.fromisoformat(normalized)
        except ValueError:
            return None

    def relative_last_update(self) -> str:
        updated_at = self.parsed_last_update()
        if not updated_at:
            return self.api_last_update_var.get()
        now = datetime.now(timezone.utc) if updated_at.tzinfo else datetime.now()
        seconds = max(0, int((now - updated_at).total_seconds()))
        if seconds < 5:
            return self.tr.t("time.now")
        if seconds < 60:
            if seconds == 1:
                return self.tr.t("time.second_ago")
            return self.tr.t("time.seconds_ago", count=seconds)
        minutes = seconds // 60
        if minutes < 60:
            if minutes == 1:
                return self.tr.t("time.minute_ago")
            return self.tr.t("time.minutes_ago", count=minutes)
        hours = minutes // 60
        if hours < 24:
            if hours == 1:
                return self.tr.t("time.hour_ago")
            return self.tr.t("time.hours_ago", count=hours)
        days = hours // 24
        if days == 1:
            return self.tr.t("time.day_ago")
        return self.tr.t("time.days_ago", count=days)

    def on_visual_item_motion(self, event) -> None:
        for x1, y1, x2, y2, label in reversed(self.visual_item_hitboxes):
            if x1 <= event.x <= x2 and y1 <= event.y <= y2:
                if self.visual_canvas:
                    self.visual_canvas.configure(cursor="question_arrow")
                self.show_visual_tooltip(label, event.x_root + 12, event.y_root + 12)
                return
        if self.visual_canvas:
            self.visual_canvas.configure(cursor="")
        self.hide_visual_tooltip()

    def show_visual_tooltip(self, text: str, x: int, y: int) -> None:
        if not text:
            self.hide_visual_tooltip()
            return
        if not self.visual_tooltip or not self.visual_tooltip.winfo_exists():
            self.visual_tooltip = tk.Toplevel(self)
            self.visual_tooltip.withdraw()
            self.visual_tooltip.overrideredirect(True)
            self.visual_tooltip.attributes("-topmost", True)
            self.visual_tooltip_label = tk.Label(
                self.visual_tooltip,
                bg="#111c31",
                fg=COLORS["text"],
                font=("Segoe UI", 9, "bold"),
                padx=8,
                pady=5,
                relief="solid",
                borderwidth=1,
            )
            self.visual_tooltip_label.pack()
        if self.visual_tooltip_label and text != self.visual_tooltip_text:
            self.visual_tooltip_label.configure(text=text)
            self.visual_tooltip_text = text
        self.visual_tooltip.geometry(f"+{x}+{y}")
        self.visual_tooltip.deiconify()

    def hide_visual_tooltip(self) -> None:
        self.visual_tooltip_text = ""
        if self.visual_canvas:
            self.visual_canvas.configure(cursor="")
        if self.visual_tooltip and self.visual_tooltip.winfo_exists():
            self.visual_tooltip.withdraw()

    def clean_visual_item_name(self, item: dict) -> str:
        display_name = str(item.get("display_name") or item.get("asset_name") or "-").strip()
        suffix = " Crated"
        if display_name.endswith(suffix):
            display_name = display_name[: -len(suffix)].strip()
        return display_name or "-"

    def visual_group_key(self, item: dict) -> str:
        asset = str(item.get("asset_name") or "").lower()
        display = str(item.get("display_name") or "").lower()
        icon_name = str(item.get("icon_name") or "").lower()
        category = str(item.get("category") or "").lower()
        icon_source = str(item.get("icon_source") or "").lower()
        priority = str(item.get("priority") or "").lower()
        is_crated = "crated" in display or icon_name.endswith("-crated")
        is_shippable = category in {"shippables", "shippable", "structures"} or icon_source == "structures_shippables"

        if priority and priority not in {"-", "medium", "normal"}:
            return "priority"
        if asset in {"basicmaterials", "bmat", "bmats"} or "basic materials" in display or display in {"bmat", "bmats"}:
            return "starter"
        if asset in {"cloth", "soldiersupplies", "shirts"} or "soldier supplies" in display or "shirts" in display:
            return "starter"
        if asset in {"maintenancesupplies", "msup", "msups"} or "maintenance supplies" in display or "msup" in display:
            return "starter"
        if (
            asset in {"cloth", "soldiersupplies", "maintenancesupplies"}
            or "basic materials" in display
            or "soldier supplies" in display
            or "maintenance supplies" in display
        ):
            return "supplies"
        if category == "vehicle":
            return "vehicle_crates" if is_crated else "vehicles"
        if is_shippable:
            return "shippable_crates" if is_crated else "shippables"
        if category == "utility":
            return "common_logi"
        return "supplies"

    def visual_groups(self, rows: list[dict]) -> list[tuple[str, list[dict]]]:
        ordered_keys = [
            "starter",
            "priority",
            "supplies",
            "common_logi",
            "vehicles",
            "vehicle_crates",
            "shippables",
            "shippable_crates",
        ]
        groups = {key: [] for key in ordered_keys}
        for item in rows:
            groups.setdefault(self.visual_group_key(item), []).append(item)

        result = []
        for key in ordered_keys:
            items = groups.get(key) or []
            if not items:
                continue
            result.append(
                (
                    key,
                    sorted(
                        items,
                        key=self.visual_sort_key,
                    ),
                )
            )
        return result

    def visual_sort_key(self, item: dict) -> tuple[int, int, str]:
        display = str(item.get("display_name") or "").lower()
        asset = str(item.get("asset_name") or "").lower()
        starter_order = 99
        if asset in {"basicmaterials", "bmat", "bmats"} or "basic materials" in display:
            starter_order = 0
        elif asset in {"cloth", "soldiersupplies", "shirts"} or "soldier supplies" in display or "shirts" in display:
            starter_order = 1
        elif asset in {"maintenancesupplies", "msup", "msups"} or "maintenance supplies" in display or "msup" in display:
            starter_order = 2
        return (
            starter_order,
            -int(item.get("quantity", 0) or 0),
            str(item.get("display_name") or ""),
        )

    def draw_visual_stockpile(self) -> None:
        if not self.visual_canvas:
            return
        canvas = self.visual_canvas
        canvas.delete("all")
        self.visual_item_hitboxes = []
        width = max(1, canvas.winfo_width())
        height = max(1, canvas.winfo_height())
        warehouse = self.selected_warehouse_var.get()
        rows = [item for item in self.latest_items if item.get("warehouse") == warehouse]
        rows = [item for item in rows if int(item.get("quantity", 0) or 0) > 0] or rows
        columns = max(1, (width - 16) // 84)
        tile_w = max(78, (width - 16) // columns)
        grouped_rows = self.visual_groups(rows)

        needed_height = 82
        for _group_key, items in grouped_rows:
            needed_height += 22
            needed_height += ((len(items) + columns - 1) // columns) * 36
            needed_height += 4
        needed_height = max(310, needed_height)
        if int(float(canvas.cget("height"))) != needed_height:
            canvas.configure(height=needed_height)
            height = needed_height

        canvas.create_rectangle(0, 0, width, height, fill="#09111f", outline="#28445f")
        canvas.create_rectangle(0, 0, width, 32, fill="#15253d", outline="")
        title = warehouse or self.tr.t("stockpile.visual_empty")
        canvas.create_text(12, 16, text=title, fill=COLORS["text"], anchor="w", font=("Segoe UI", 10, "bold"))

        canvas.create_text(
            8,
            46,
            text=self.tr.t("stockpile.visual_updated", value=self.relative_last_update()),
            fill=COLORS["muted"],
            anchor="w",
            font=("Segoe UI", 8),
        )
        canvas.create_line(0, 62, width, 62, fill="#223752", width=2)

        if not rows:
            canvas.create_text(
                width // 2,
                height // 2,
                text=self.tr.t("stockpile.visual_empty"),
                fill=COLORS["muted"],
                font=("Segoe UI", 10, "bold"),
            )
            return

        x0 = 8
        y = 80

        for group_key, items in grouped_rows:
            canvas.create_line(10, y - 8, width - 10, y - 8, fill="#1f324b", width=1)
            canvas.create_text(
                12,
                y,
                text=self.tr.t(f"stockpile.group_{group_key}"),
                fill=COLORS["accent_2"] if group_key in {"bmat", "shirts", "msup"} else "#aeb7c2",
                anchor="w",
                font=("Segoe UI", 8, "bold"),
            )
            y += 16
            column = 0

            for item in items:
                x = x0 + column * tile_w

                icon = self.load_item_icon(str(item.get("icon_path") or ""))
                if icon:
                    canvas.create_image(x + 16, y + 15, image=icon)
                else:
                    canvas.create_rectangle(x + 2, y + 2, x + 32, y + 28, fill="#1e2630", outline="#375777")

                quantity = str(item.get("quantity", 0))
                canvas.create_rectangle(x + 40, y + 2, x + 82, y + 28, fill="#172943", outline="#2b4565")
                canvas.create_text(x + 61, y + 15, text=quantity, fill=COLORS["text"], anchor="center", font=("Segoe UI", 10, "bold"))
                display_name = self.clean_visual_item_name(item)
                self.visual_item_hitboxes.append((x, y, x + 82, y + 30, display_name))

                column += 1
                if column >= columns:
                    column = 0
                    y += 36
            if column:
                y += 36
            y += 4
