from __future__ import annotations

from collections import defaultdict
import threading
import tkinter as tk
from tkinter import ttk

try:
    import customtkinter as ctk
except ImportError:  # pragma: no cover - optional visual upgrade.
    ctk = None

from i18n import Translator
from settings_store import load_settings
from stockpiler import api_item_rows, api_last_update, request_stockpile_debug

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
    "line": "#2d496f",
    "good": "#62d7a4",
    "panel": "#09111f",
    "panel_2": "#13233a",
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


class ItemSearchCategory(ttk.Frame):
    def __init__(self, parent: ttk.Widget, translator: Translator | None = None) -> None:
        super().__init__(parent, style="Panel.TFrame")
        self.tr = translator or Translator()
        self.settings = load_settings()
        self.items: list[dict] = []
        self.filtered_names: list[str] = []
        self.icon_images: dict[str, tk.PhotoImage] = {}
        self.search_var = tk.StringVar(value="")
        self.status_var = tk.StringVar(value=self.tr.t("item_search.loading"))
        self.best_match_var = tk.StringVar(value="")
        self.last_update_var = tk.StringVar(value="-")
        self.total_var = tk.StringVar(value="0")
        self.result_canvas: tk.Canvas | None = None
        self.result_scrollbar = None
        self.match_bar = None
        self.match_label: tk.Label | None = None
        self.entry: tk.Entry | None = None
        self.active = False
        self.loading = False
        self.refresh_job: str | None = None
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.build()
        self.load_items()

    def build(self) -> None:
        outer = modern_frame(self, COLORS["bg"], radius=0)
        outer.grid(row=0, column=0, sticky="nsew")
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(1, weight=1)

        body = modern_frame(outer, COLORS["card"], radius=24, border=1, border_color=COLORS["line"])
        body.grid(row=1, column=0, sticky="nsew", padx=22, pady=22)
        body.columnconfigure(0, weight=1)
        body.rowconfigure(3, weight=1)

        head = modern_frame(body, COLORS["card"], radius=0)
        head.grid(row=0, column=0, sticky="ew", padx=18, pady=(18, 4))
        head.columnconfigure(0, weight=1)
        tk.Label(head, text=self.tr.t("item_search.title"), bg=COLORS["card"], fg=COLORS["text"], font=("Segoe UI", 20, "bold")).grid(
            row=0, column=0, sticky="w"
        )
        tk.Label(head, textvariable=self.status_var, bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI", 9, "bold")).grid(
            row=0, column=1, sticky="e"
        )

        search_row = modern_frame(body, COLORS["card"], radius=0)
        search_row.grid(row=1, column=0, sticky="ew", padx=18, pady=(8, 8))
        search_row.columnconfigure(0, weight=1)

        if ctk is not None:
            self.entry = ctk.CTkEntry(
                search_row,
                textvariable=self.search_var,
                fg_color=COLORS["soft"],
                bg_color=COLORS["card"],
                border_color=COLORS["line"],
                border_width=1,
                text_color=COLORS["text"],
                placeholder_text=self.tr.t("item_search.placeholder"),
                corner_radius=14,
                height=46,
                font=("Segoe UI", 13, "bold"),
            )
        else:
            self.entry = tk.Entry(
                search_row,
                textvariable=self.search_var,
                bg=COLORS["soft"],
                fg=COLORS["text"],
                insertbackground=COLORS["accent"],
                relief="flat",
                font=("Segoe UI", 13, "bold"),
            )
        self.entry.grid(row=0, column=0, sticky="ew", ipady=12)
        self.entry.bind("<KeyRelease>", self.on_search_change)
        self.entry.bind("<Return>", lambda _event: self.select_first_suggestion())
        self.entry.bind("<Down>", lambda _event: self.focus_suggestions())

        match_bar = modern_frame(body, COLORS["soft"], radius=14, border=1, border_color="#1f3857")
        match_bar.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 8))
        match_bar.columnconfigure(0, weight=1)
        self.match_bar = match_bar
        self.match_label = tk.Label(match_bar, textvariable=self.best_match_var, bg=COLORS["soft"], fg=COLORS["accent"], font=("Segoe UI", 10, "bold"), cursor="hand2")
        self.match_label.grid(
            row=0, column=0, sticky="w", padx=12, pady=8
        )
        self.match_label.bind("<Button-1>", lambda _event: self.select_first_suggestion())
        match_bar.bind("<Button-1>", lambda _event: self.select_first_suggestion())
        match_bar.grid_remove()

        result_host = modern_frame(body, COLORS["card"], radius=0)
        result_host.grid(row=3, column=0, sticky="nsew", padx=18, pady=(4, 18))
        result_host.columnconfigure(0, weight=1)
        result_host.rowconfigure(0, weight=1)
        self.result_canvas = tk.Canvas(result_host, bg=COLORS["card"], highlightthickness=0)
        self.result_canvas.grid(row=0, column=0, sticky="nsew")
        if ctk is not None:
            self.result_scrollbar = ctk.CTkScrollbar(
                result_host,
                orientation="vertical",
                command=self.result_canvas.yview,
                width=10,
                fg_color=COLORS["card"],
                button_color=COLORS["card_2"],
                button_hover_color=COLORS["accent"],
            )
        else:
            self.result_scrollbar = ttk.Scrollbar(result_host, orient="vertical", command=self.result_canvas.yview, style="Vertical.TScrollbar")
        self.result_scrollbar.grid(row=0, column=1, sticky="ns")
        self.result_canvas.configure(yscrollcommand=self.result_scrollbar.set)
        self.result_canvas.bind("<Configure>", lambda _event: self.draw_result())
        self.result_canvas.bind("<MouseWheel>", self.on_result_mousewheel, add="+")

    def refresh_language(self, translator: Translator) -> None:
        self.tr = translator
        for child in self.winfo_children():
            child.destroy()
        self.build()
        self.update_suggestions()
        self.draw_result()

    def set_active(self, active: bool) -> None:
        self.active = active
        if active:
            self.load_items()
            self.schedule_refresh()
        else:
            self.cancel_refresh()

    def schedule_refresh(self) -> None:
        self.cancel_refresh()
        if self.active:
            self.refresh_job = self.after(30_000, self.periodic_refresh)

    def cancel_refresh(self) -> None:
        if self.refresh_job:
            self.after_cancel(self.refresh_job)
            self.refresh_job = None

    def periodic_refresh(self) -> None:
        self.refresh_job = None
        if self.active:
            self.load_items()
            self.schedule_refresh()

    def load_items(self) -> None:
        if self.loading:
            return
        self.loading = True
        self.status_var.set(self.tr.t("item_search.loading"))

        def worker() -> None:
            try:
                stockpile = load_settings()["stockpile"]
                api_response = request_stockpile_debug(str(stockpile.get("api_url", "")))
                items = api_item_rows(api_response)
                last_update = api_last_update(api_response) or "-"
                self.after(0, lambda: self.apply_items(items, last_update))
            except Exception as exc:
                self.after(0, self.status_var.set, self.tr.t("item_search.error", message=str(exc)))
            finally:
                self.loading = False

        threading.Thread(target=worker, daemon=True).start()

    def on_result_mousewheel(self, event) -> str:
        if self.result_canvas:
            self.result_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        return "break"

    def apply_items(self, items: list[dict], last_update: str) -> None:
        self.items = items
        self.last_update_var.set(last_update)
        self.status_var.set(self.tr.t("item_search.loaded", count=len(items)))
        self.update_suggestions()
        self.draw_result()

    def item_names(self) -> list[str]:
        names = {str(item.get("display_name") or "-") for item in self.items if item.get("display_name")}
        return sorted(names, key=str.lower)

    def on_search_change(self, _event=None) -> None:
        self.update_suggestions()
        self.draw_result()

    def update_suggestions(self) -> None:
        query = self.search_var.get().strip().lower()
        names = self.item_names()
        if query:
            starts = [name for name in names if name.lower().startswith(query)]
            contains = [name for name in names if query in name.lower() and name not in starts]
            self.filtered_names = (starts + contains)[:8]
        else:
            self.filtered_names = []
        if query and self.filtered_names:
            self.best_match_var.set(self.tr.t("item_search.best_match", item=self.filtered_names[0]))
            if self.match_bar:
                self.match_bar.grid()
        else:
            self.best_match_var.set(self.tr.t("item_search.best_match_empty"))
            if self.match_bar:
                self.match_bar.grid_remove()

    def focus_suggestions(self):
        return self.select_first_suggestion()

    def select_first_suggestion(self):
        if self.filtered_names:
            self.search_var.set(self.filtered_names[0])
            self.update_suggestions()
            self.draw_result()
        return "break"

    def apply_selected_suggestion(self):
        return self.select_first_suggestion()

    def matching_rows(self) -> list[dict]:
        query = self.search_var.get().strip().lower()
        if not query:
            return []
        exact = [item for item in self.items if str(item.get("display_name") or "").lower() == query]
        if exact:
            return exact
        if self.filtered_names:
            selected = self.filtered_names[0].lower()
            return [item for item in self.items if str(item.get("display_name") or "").lower() == selected]
        return [item for item in self.items if query in str(item.get("display_name") or "").lower()]

    def load_item_icon(self, path: str) -> tk.PhotoImage | None:
        if not path:
            return None
        if path in self.icon_images:
            return self.icon_images[path]
        try:
            if Image and ImageTk:
                image = Image.open(path).convert("RGBA")
                image.thumbnail((26, 26), Image.LANCZOS)
                photo = ImageTk.PhotoImage(image)
            else:
                photo = tk.PhotoImage(file=path)
        except Exception:
            return None
        self.icon_images[path] = photo
        return photo

    def split_location(self, warehouse: str) -> tuple[str, str, str]:
        parts = [part.strip() for part in warehouse.split("/") if part.strip()]
        if len(parts) >= 2:
            region = parts[-2]
            name = parts[-1]
        else:
            region = warehouse or "-"
            name = warehouse or "-"
        code = name
        return region, name, code

    def draw_result(self) -> None:
        if not self.result_canvas:
            return
        canvas = self.result_canvas
        canvas.delete("all")
        width = max(1, canvas.winfo_width())
        rows = self.matching_rows()
        grouped_preview: dict[str, list[dict]] = defaultdict(list)
        for item in rows:
            region, _name, _code = self.split_location(str(item.get("warehouse") or "-"))
            grouped_preview[region].append(item)
        height = max(440, 172 + len(rows) * 54 + len(grouped_preview) * 18)
        canvas.configure(scrollregion=(0, 0, width, height))
        canvas.create_rectangle(0, 0, width, height, fill=COLORS["card"], outline="")

        if not rows:
            canvas.create_rectangle(10, 10, width - 10, height - 10, fill=COLORS["panel"], outline=COLORS["line"])
            canvas.create_text(
                width // 2,
                height // 2,
                text=self.tr.t("item_search.empty"),
                fill=COLORS["muted"],
                font=("Segoe UI", 12, "bold"),
                anchor="center",
            )
            return

        item_name = str(rows[0].get("display_name") or self.search_var.get())
        icon_path = str(rows[0].get("icon_path") or "")
        total = sum(max(0, int(item.get("quantity", 0) or 0)) for item in rows)
        self.total_var.set(str(total))

        card_x = 12
        card_y = 10
        card_w = max(420, width - 24)
        card_h = max(390, 170 + len(rows) * 52 + len(grouped_preview) * 18)
        canvas.create_rectangle(card_x, card_y, card_x + card_w, card_y + card_h, fill=COLORS["panel"], outline=COLORS["line"])
        canvas.create_rectangle(card_x, card_y, card_x + 6, card_y + card_h, fill=COLORS["accent"], outline="")
        canvas.create_rectangle(card_x + 6, card_y, card_x + card_w, card_y + 72, fill=COLORS["panel_2"], outline="")

        icon = self.load_item_icon(icon_path)
        title_x = card_x + 26
        if icon:
            canvas.create_image(title_x + 18, card_y + 36, image=icon)
            title_x += 46
        canvas.create_text(title_x, card_y + 29, text=self.tr.t("item_search.result_title", item=item_name), fill=COLORS["text"], anchor="w", font=("Segoe UI", 16, "bold"))
        canvas.create_text(title_x, card_y + 52, text=self.tr.t("item_search.last_update", value=self.last_update_var.get()), fill=COLORS["muted"], anchor="w", font=("Segoe UI", 9, "bold"))

        canvas.create_rectangle(card_x + card_w - 178, card_y + 18, card_x + card_w - 24, card_y + 58, fill="#0d1d34", outline="#234365")
        canvas.create_text(card_x + card_w - 101, card_y + 38, text=self.tr.t("item_search.total", total=total), fill=COLORS["accent"], anchor="center", font=("Segoe UI", 12, "bold"))

        grouped: dict[str, list[dict]] = defaultdict(list)
        for item in rows:
            region, _name, _code = self.split_location(str(item.get("warehouse") or "-"))
            grouped[region].append(item)

        y = card_y + 98
        for region in sorted(grouped):
            region_rows = sorted(grouped[region], key=lambda item: str(item.get("warehouse") or ""))
            region_total = sum(max(0, int(item.get("quantity", 0) or 0)) for item in region_rows)
            canvas.create_rectangle(card_x + 22, y - 13, card_x + card_w - 22, y + 20, fill="#102039", outline="#203a5c")
            canvas.create_text(card_x + 36, y + 2, text=self.tr.t("item_search.region_total", region=region, total=region_total), fill=COLORS["text"], anchor="w", font=("Segoe UI", 12, "bold"))
            y += 38
            for item in region_rows:
                _region, _name, code = self.split_location(str(item.get("warehouse") or "-"))
                quantity = int(item.get("quantity", 0) or 0)
                row_x1 = card_x + 34
                row_x2 = card_x + card_w - 34
                canvas.create_rectangle(row_x1, y - 14, row_x2, y + 22, fill="#0c192b", outline="#162b45")
                canvas.create_text(row_x1 + 14, y + 4, text=str(code), fill=COLORS["text"], anchor="w", font=("Segoe UI", 11, "bold"))
                canvas.create_text(row_x2 - 18, y + 4, text=str(quantity), fill=COLORS["accent"], anchor="e", font=("Segoe UI", 12, "bold"))
                small_icon = self.load_item_icon(str(item.get("icon_path") or ""))
                if small_icon:
                    canvas.create_image(row_x2 - 8, y + 4, image=small_icon, anchor="w")
                y += 44
            y += 10

    def stop(self) -> None:
        self.cancel_refresh()
