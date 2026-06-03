from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
import sqlite3
import tkinter as tk
from tkinter import ttk

try:
    import customtkinter as ctk
except ImportError:  # pragma: no cover - optional visual upgrade.
    ctk = None

from i18n import Translator
from stockpiler import DB_PATH, icon_info_for_asset

try:
    from PIL import Image, ImageTk
except ImportError:  # pragma: no cover - app still runs without icons.
    Image = None
    ImageTk = None


COLORS = {
    "bg": "#060a13",
    "card": "#111a2b",
    "card_2": "#24344d",
    "text": "#edf6ff",
    "muted": "#99abc4",
    "accent": "#5eead4",
    "accent_2": "#8ab4ff",
    "soft": "#172130",
    "line": "#294366",
    "good": "#62d7a4",
    "warn": "#ffd166",
    "danger": "#ff7a90",
}

BASE_DIR = Path(__file__).resolve().parent
CALCULATOR_ASSET_DIR = BASE_DIR / "img" / "calculator"
CALCULATOR_MENU_DIR = CALCULATOR_ASSET_DIR / "menu"

MATERIALS = (
    ("bmat", "BMats"),
    ("emat", "EMats"),
    ("rmat", "RMats"),
    ("hemat", "HEMats"),
    ("relic", "Relic"),
)

MATERIAL_CRATE_SIZES = {
    "bmat": 100,
    "emat": 40,
    "rmat": 20,
    "hemat": 30,
    "relic": 20,
}

MATERIAL_ICON_PATHS = {
    "bmat": CALCULATOR_ASSET_DIR / "BasicMaterials.png",
    "emat": CALCULATOR_ASSET_DIR / "ExplosiveMaterials.png",
    "rmat": CALCULATOR_ASSET_DIR / "RefinedMaterials.png",
    "hemat": CALCULATOR_ASSET_DIR / "HeavyExplosiveMaterials.png",
}
CRATE_ICON_PATH = CALCULATOR_ASSET_DIR / "cx.png"

CATEGORY_ORDER = (
    "Small Arms",
    "Heavy Arms",
    "Heavy Ammunition",
    "Utility",
    "Medical",
    "Resource",
    "Uniforms",
    "Vehicles",
    "Structures",
)

CATEGORY_RULES = {
    "Small Arms": {"min": 3, "max": 9, "units": None, "mark": "SA", "factory": True, "mpf": True},
    "Heavy Arms": {"min": 3, "max": 9, "units": None, "mark": "HA", "factory": True, "mpf": True},
    "Heavy Ammunition": {"min": 3, "max": 9, "units": None, "mark": "AM", "factory": True, "mpf": True},
    "Utility": {"min": 3, "max": 9, "units": None, "mark": "UT", "factory": True, "mpf": False},
    "Medical": {"min": 3, "max": 9, "units": None, "mark": "MD", "factory": True, "mpf": False},
    "Resource": {"min": 3, "max": 9, "units": None, "mark": "RS", "factory": True, "mpf": False},
    "Uniforms": {"min": 3, "max": 9, "units": None, "mark": "UN", "factory": True, "mpf": True},
    "Vehicles": {"min": 1, "max": 5, "units": 3, "mark": "VH", "factory": False, "mpf": True},
    "Structures": {"min": 1, "max": 5, "units": 3, "mark": "ST", "factory": False, "mpf": True},
}

CATEGORY_ICON_PATHS = {
    category: CALCULATOR_MENU_DIR / f"{rule['mark'].lower()}.png"
    for category, rule in CATEGORY_RULES.items()
}


@dataclass(frozen=True)
class ProductionItem:
    mode: str
    item_id: str
    name: str
    faction: str
    category: str
    bmat: float
    emat: float
    rmat: float
    hemat: float
    relic: float
    quantity_per_crate: int
    crate_production_time: float
    icon_path: str


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


def clean_enum(value: str | None) -> str:
    text = str(value or "")
    return text.split("::", 1)[-1] if "::" in text else text


def category_from_queue(value: str | None) -> str:
    queue = clean_enum(value)
    return {
        "SmallArms": "Small Arms",
        "HeavyArms": "Heavy Arms",
        "HeavyAmmo": "Heavy Ammunition",
        "Uniforms": "Uniforms",
        "Utility": "Utility",
        "Medical": "Medical",
        "Supplies": "Resource",
        "VehicleFactory": "Vehicles",
        "Shipyard": "Vehicles",
        "ConstructionYard": "Structures",
    }.get(queue, queue or "Other")


def faction_label(value: str | None) -> str:
    faction = clean_enum(value)
    return {
        "Colonials": "Colonial",
        "Wardens": "Warden",
    }.get(faction, "Neutral")


def discount_multiplier(box_index: int) -> float:
    discount = min(0.5, max(0.1, box_index * 0.1))
    return 1.0 - discount


class ProductionCalculatorCategory(ttk.Frame):
    def __init__(self, parent: ttk.Widget, translator: Translator | None = None) -> None:
        super().__init__(parent, style="Panel.TFrame")
        self.tr = translator or Translator()
        self.items: list[ProductionItem] = []
        self.queue: dict[str, list[ProductionItem]] = {category: [] for category in CATEGORY_ORDER}
        self.icon_images: dict[tuple[str, int], tk.PhotoImage] = {}
        self.category_images: dict[str, tk.PhotoImage] = {}
        self.item_hitboxes: list[tuple[int, int, int, int, ProductionItem]] = []
        self.queue_hitboxes: list[tuple[int, int, int, int, str, int]] = []
        self.last_material_totals: dict[str, float] = {key: 0.0 for key, _label in MATERIALS}
        self.selected_category = tk.StringVar(value="Small Arms")
        self.mode_var = tk.StringVar(value="mpf")
        self.factory_multiplier = tk.IntVar(value=1)
        self.mpf_vehicle_mode = tk.StringVar(value="Dunne")
        self.faction_filter = tk.StringVar(value="Neutral")
        self.search_var = tk.StringVar(value="")
        self.status_var = tk.StringVar(value=self.tr.t("production.loading"))
        self.summary_var = tk.StringVar(value="-")
        self.materials_var = tk.StringVar(value="-")
        self.orders_var = tk.StringVar(value="-")
        self.warning_var = tk.StringVar(value="")
        self.item_canvas: tk.Canvas | None = None
        self.queue_canvas: tk.Canvas | None = None
        self.material_canvas: tk.Canvas | None = None
        self.category_canvas: tk.Canvas | None = None
        self.category_hitboxes: list[tuple[int, int, int, int, str]] = []
        self.search_entry: tk.Entry | None = None
        self.search_placeholder_active = False
        self.category_buttons: dict[str, tk.Button] = {}
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.load_items()
        self.build()
        self.refresh_all()

    def load_items(self) -> None:
        self.items = []
        if not DB_PATH.exists():
            self.status_var.set(self.tr.t("production.db_missing"))
            return
        try:
            with sqlite3.connect(DB_PATH) as connection:
                rows = []
                for mode, table, relic_expr, vehicle_bonus_expr in (
                    ("factory", "items_factory", "NULL", "NULL"),
                    ("mpf", "items_mpf", "relic", "vehicles_per_crate_bonus_quantity"),
                ):
                    rows.extend(
                        (
                            mode,
                            *row,
                        )
                        for row in connection.execute(
                            f"""
                            SELECT id, name, faction_variant, type, bmat, emat, rmat, hemat, {relic_expr},
                                   quantity_per_crate, crate_production_time, {vehicle_bonus_expr}
                            FROM {table}
                            WHERE name IS NOT NULL
                            ORDER BY name COLLATE NOCASE
                            """
                        ).fetchall()
                    )
        except sqlite3.Error as exc:
            self.status_var.set(self.tr.t("production.db_error", message=str(exc)))
            return

        for row in rows:
            mode, item_id, name, faction, queue_type, bmat, emat, rmat, hemat, relic, quantity, time_value, vehicle_bonus = row
            category = category_from_queue(queue_type)
            
            if mode == "mpf" and not CATEGORY_RULES.get(category, {}).get("mpf", False):
                continue
            if mode == "factory" and not CATEGORY_RULES.get(category, {}).get("factory", False):
                continue

            rule = CATEGORY_RULES.get(category, {"units": None})
            if rule.get("units"):
                units_per_crate = int(rule["units"])
            elif vehicle_bonus:
                units_per_crate = 1 + int(vehicle_bonus)
            else:
                units_per_crate = int(quantity or 1)
            icon_info = icon_info_for_asset(str(item_id))
            self.items.append(
                ProductionItem(
                    mode=str(mode),
                    item_id=str(item_id),
                    name=str(name),
                    faction=faction_label(faction),
                    category=category,
                    bmat=float(bmat or 0),
                    emat=float(emat or 0),
                    rmat=float(rmat or 0),
                    hemat=float(hemat or 0),
                    relic=float(relic or 0),
                    quantity_per_crate=max(1, units_per_crate),
                    crate_production_time=float(time_value or 0),
                    icon_path=str(icon_info.get("icon_path", "")),
                )
            )
        self.status_var.set(self.tr.t("production.loaded", count=len(self.items)))

    def build(self) -> None:
        outer = modern_frame(self, COLORS["bg"], radius=0)
        outer.grid(row=0, column=0, sticky="nsew")
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(1, weight=1)

        header = modern_frame(outer, COLORS["bg"], radius=0)
        header.grid(row=0, column=0, sticky="ew", padx=16, pady=(10, 4))
        header.columnconfigure(0, weight=1)
        tk.Label(header, text=self.tr.t("production.title"), bg=COLORS["bg"], fg=COLORS["text"], font=("Segoe UI", 20, "bold")).grid(
            row=0, column=0, sticky="w"
        )
        tk.Label(header, textvariable=self.status_var, bg=COLORS["bg"], fg=COLORS["muted"], font=("Segoe UI", 9, "bold")).grid(
            row=0, column=1, sticky="e"
        )

        body = modern_frame(outer, COLORS["card"], radius=14, border=1, border_color=COLORS["line"])
        body.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        body.columnconfigure(0, weight=4)
        body.columnconfigure(1, weight=3)
        body.rowconfigure(0, weight=1)

        self.build_items_panel(body)
        self.build_queue_panel(body)

    def build_items_panel(self, parent) -> None:
        panel = modern_frame(parent, COLORS["card"], radius=0)
        panel.grid(row=0, column=0, sticky="nsew", padx=(8, 5), pady=8)
        panel.columnconfigure(0, weight=1)
        panel.rowconfigure(3, weight=1)

        head = modern_frame(panel, COLORS["card"], radius=0)
        head.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        head.columnconfigure(0, weight=1)
        tk.Label(head, text=self.tr.t("production.items"), bg=COLORS["card"], fg=COLORS["text"], font=("Segoe UI", 13, "bold")).grid(
            row=0, column=0, sticky="w"
        )
        tk.Label(head, text=self.tr.t("production.shift_hint"), bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI", 9, "bold")).grid(
            row=0, column=1, sticky="e", padx=(8, 0)
        )

        filters = modern_frame(panel, COLORS["card"], radius=0)
        filters.grid(row=1, column=0, sticky="ew", pady=(0, 6))
        filters.columnconfigure(4, weight=1)
        
        tk.Radiobutton(
            filters,
            text=self.tr.t("production.mode_factory"),
            variable=self.mode_var,
            value="factory",
            command=self.on_mode_changed,
            bg=COLORS["card"],
            fg=COLORS["text"],
            selectcolor=COLORS["card_2"],
            activebackground=COLORS["card"],
            activeforeground=COLORS["text"],
            font=("Segoe UI", 8, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=(0, 4))
        
        mult_frame = tk.Frame(filters, bg=COLORS["card"])
        mult_frame.grid(row=0, column=1, sticky="w", padx=(0, 16))
        
        def dec():
            if self.factory_multiplier.get() > 1:
                self.factory_multiplier.set(self.factory_multiplier.get() - 1)
                self.recalculate_queue()
                self.draw_queue()
                
        def inc():
            if self.factory_multiplier.get() < 2:
                self.factory_multiplier.set(self.factory_multiplier.get() + 1)
                self.recalculate_queue()
                self.draw_queue()
            
        tk.Button(mult_frame, text="-", command=dec, bg=COLORS["card_2"], fg=COLORS["text"], relief="flat", activebackground=COLORS["line"]).pack(side="left")
        tk.Label(mult_frame, textvariable=self.factory_multiplier, bg=COLORS["card"], fg=COLORS["accent"], font=("Segoe UI", 8, "bold"), width=3).pack(side="left")
        tk.Button(mult_frame, text="+", command=inc, bg=COLORS["card_2"], fg=COLORS["text"], relief="flat", activebackground=COLORS["line"]).pack(side="left")

        tk.Radiobutton(
            filters,
            text=self.tr.t("production.mode_mpf"),
            variable=self.mode_var,
            value="mpf",
            command=self.on_mode_changed,
            bg=COLORS["card"],
            fg=COLORS["text"],
            selectcolor=COLORS["card_2"],
            activebackground=COLORS["card"],
            activeforeground=COLORS["text"],
            font=("Segoe UI", 8, "bold"),
        ).grid(row=0, column=2, sticky="w", padx=(0, 8))

        for value, column in (("Neutral", 0), ("Colonial", 1), ("Warden", 2)):
            tk.Radiobutton(
                filters,
                text=self.tr.t(f"production.faction_{value.lower()}"),
                variable=self.faction_filter,
                value=value,
                command=self.refresh_item_grid,
                bg=COLORS["card"],
                fg=COLORS["text"],
                selectcolor=COLORS["card_2"],
                activebackground=COLORS["card"],
                activeforeground=COLORS["text"],
                font=("Segoe UI", 8, "bold"),
            ).grid(row=1, column=column, sticky="w", padx=(0, 8), pady=(4, 0))
        search_wrap = modern_frame(filters, "#050914", radius=8, border=1, border_color="#24405f")
        search_wrap.grid(row=0, column=4, rowspan=2, sticky="e", padx=(10, 0))
        search_wrap.columnconfigure(0, weight=1)
        self.search_entry = tk.Entry(
            search_wrap,
            bg="#050914",
            fg=COLORS["text"],
            insertbackground=COLORS["accent"],
            relief="flat",
            borderwidth=0,
            font=("Segoe UI", 9, "bold"),
            width=26,
        )
        self.search_entry.grid(row=0, column=0, sticky="ew", ipady=7, padx=(10, 4), pady=1)
        self.search_entry.bind("<FocusIn>", self.on_search_focus_in)
        self.search_entry.bind("<FocusOut>", self.on_search_focus_out)
        self.search_entry.bind("<KeyRelease>", self.on_search_key)
        tk.Button(
            search_wrap,
            text="x",
            command=self.clear_search,
            bg="#050914",
            fg=COLORS["muted"],
            activebackground="#0b1424",
            activeforeground=COLORS["text"],
            relief="flat",
            width=2,
            font=("Segoe UI", 11, "bold"),
            cursor="hand2",
        ).grid(row=0, column=1, sticky="e", padx=(0, 6), pady=1)
        self.apply_search_placeholder()

        self.category_canvas = tk.Canvas(panel, height=58, bg=COLORS["soft"], highlightthickness=1, highlightbackground="#2b3d58")
        self.category_canvas.grid(row=2, column=0, sticky="ew", pady=(0, 6))
        self.category_canvas.bind("<Configure>", lambda _event: self.update_category_buttons())
        self.category_canvas.bind("<Button-1>", self.on_category_canvas_click)

        self.item_canvas = tk.Canvas(panel, bg="#080c14", highlightthickness=0)
        self.item_canvas.grid(row=3, column=0, sticky="nsew")
        self.item_canvas.bind("<Configure>", lambda _event: self.refresh_item_grid())
        self.item_canvas.bind("<Button-1>", self.on_item_click)
        self.item_canvas.bind("<Button-3>", self.on_item_right_click)
        self.item_canvas.bind("<MouseWheel>", self.on_item_mousewheel, add="+")

    def build_queue_panel(self, parent) -> None:
        panel = modern_frame(parent, COLORS["soft"], radius=10, border=1, border_color="#2b3d58")
        panel.grid(row=0, column=1, sticky="nsew", padx=(5, 8), pady=8)
        panel.columnconfigure(0, weight=1)
        panel.rowconfigure(5, weight=1)

        top = modern_frame(panel, COLORS["soft"], radius=0)
        top.grid(row=0, column=0, sticky="ew", padx=10, pady=(8, 6))
        top.columnconfigure(0, weight=1)
        tk.Label(top, text=self.tr.t("production.queue"), bg=COLORS["soft"], fg=COLORS["text"], font=("Segoe UI", 13, "bold")).grid(
            row=0, column=0, sticky="w"
        )
        tk.Button(
            top,
            text="Resumo de Rotas",
            command=self.show_truck_planner,
            bg=COLORS["accent_2"],
            fg="#041014",
            activebackground=COLORS["accent"],
            activeforeground="#041014",
            relief="flat",
            padx=12,
            pady=4,
            font=("Segoe UI", 8, "bold"),
            cursor="hand2",
        ).grid(row=0, column=1, sticky="e", padx=(0, 8))

        tk.Button(
            top,
            text=self.tr.t("production.clear"),
            command=self.clear_queue,
            bg=COLORS["card_2"],
            fg=COLORS["text"],
            activebackground=COLORS["line"],
            activeforeground=COLORS["text"],
            relief="flat",
            padx=9,
            pady=4,
            font=("Segoe UI", 8, "bold"),
            cursor="hand2",
        ).grid(row=0, column=2, sticky="e")

        totals = modern_frame(panel, COLORS["soft"], radius=0)
        totals.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 6))
        totals.columnconfigure(0, weight=1)
        totals.columnconfigure(1, weight=1)
        totals.columnconfigure(2, weight=1)
        self.total_card(totals, self.tr.t("production.summary"), self.summary_var, 0)
        self.total_card(totals, self.tr.t("production.materials"), self.materials_var, 1)
        self.total_card(totals, self.tr.t("production.orders"), self.orders_var, 2)

        self.material_canvas = tk.Canvas(panel, height=70, bg=COLORS["soft"], highlightthickness=0)
        self.material_canvas.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 6))
        self.material_canvas.bind("<Configure>", lambda _event: self.draw_material_strip())

        warning = tk.Label(
            panel,
            textvariable=self.warning_var,
            bg=COLORS["soft"],
            fg=COLORS["warn"],
            font=("Segoe UI", 8, "bold"),
            wraplength=440,
            justify="left",
        )
        warning.grid(row=3, column=0, sticky="ew", padx=10, pady=(0, 4))

        tk.Label(
            panel,
            text=self.tr.t("production.queue_hint"),
            bg=COLORS["soft"],
            fg=COLORS["muted"],
            font=("Segoe UI", 7, "bold"),
        ).grid(row=4, column=0, sticky="w", padx=10, pady=(0, 4))

        self.queue_canvas = tk.Canvas(panel, bg=COLORS["soft"], highlightthickness=0)
        self.queue_canvas.grid(row=5, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.queue_canvas.bind("<Configure>", lambda _event: self.draw_queue())
        self.queue_canvas.bind("<Button-1>", self.on_queue_click)
        self.queue_canvas.bind("<MouseWheel>", self.on_queue_mousewheel, add="+")

    def total_card(self, parent, title: str, variable: tk.StringVar, column: int) -> None:
        card = modern_frame(parent, COLORS["card"], radius=6, border=1, border_color=COLORS["line"])
        card.grid(row=0, column=column, sticky="nsew", padx=(0 if column == 0 else 6, 0))
        tk.Label(card, text=title, bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI", 8, "bold")).pack(
            anchor="w", padx=9, pady=(6, 0)
        )
        tk.Label(card, textvariable=variable, bg=COLORS["card"], fg=COLORS["text"], font=("Segoe UI", 9, "bold"), wraplength=145, justify="left").pack(
            anchor="w", padx=9, pady=(0, 6)
        )

    def refresh_language(self, translator: Translator) -> None:
        self.tr = translator
        for child in self.winfo_children():
            child.destroy()
        self.category_buttons.clear()
        self.build()
        self.refresh_all()

    def apply_search_placeholder(self) -> None:
        if not self.search_entry or self.search_var.get():
            return
        self.search_placeholder_active = True
        self.search_entry.delete(0, "end")
        self.search_entry.insert(0, self.tr.t("production.search_placeholder"))
        self.search_entry.configure(fg=COLORS["muted"])

    def on_search_focus_in(self, _event=None) -> None:
        if self.search_entry and self.search_placeholder_active:
            self.search_entry.delete(0, "end")
            self.search_entry.configure(fg=COLORS["text"])
            self.search_placeholder_active = False

    def on_search_focus_out(self, _event=None) -> None:
        if self.search_entry and not self.search_entry.get().strip():
            self.search_var.set("")
            self.apply_search_placeholder()

    def on_search_key(self, _event=None) -> None:
        if not self.search_entry or self.search_placeholder_active:
            return
        self.search_var.set(self.search_entry.get().strip())
        self.refresh_item_grid()

    def clear_search(self) -> None:
        self.search_var.set("")
        if self.search_entry:
            self.search_entry.configure(fg=COLORS["text"])
            self.search_entry.delete(0, "end")
        self.apply_search_placeholder()
        self.refresh_item_grid()

    def select_category(self, category: str) -> None:
        self.selected_category.set(category)
        self.refresh_all()

    def on_mode_changed(self) -> None:
        self.clear_queue(refresh=False)
        if self.selected_category.get() not in {item.category for item in self.current_mode_items()}:
            categories = self.available_categories()
            self.selected_category.set(categories[0] if categories else "Small Arms")
        self.warning_var.set("")
        self.refresh_all()

    def current_mode_items(self) -> list[ProductionItem]:
        mode = self.mode_var.get()
        return [item for item in self.items if item.mode == mode]

    def available_categories(self) -> list[str]:
        present = {item.category for item in self.current_mode_items()}
        return [category for category in CATEGORY_ORDER if category in present]

    def filtered_items(self) -> list[ProductionItem]:
        category = self.selected_category.get()
        faction = self.faction_filter.get()
        query = self.search_var.get().strip().lower()
        rows = [item for item in self.current_mode_items() if item.category == category]
        if faction != "Neutral":
            rows = [item for item in rows if item.faction in {faction, "Neutral"}]
        if query:
            rows = [item for item in rows if query in item.name.lower()]
        return rows

    def refresh_all(self) -> None:
        self.update_category_buttons()
        self.refresh_item_grid()
        self.recalculate_queue()
        self.draw_queue()

    def update_category_buttons(self) -> None:
        canvas = self.category_canvas
        if canvas:
            canvas.delete("all")
            self.category_hitboxes = []
            width = max(1, canvas.winfo_width())
            present = self.available_categories()
            cell_w = max(1, width // max(1, len(present)))
            selected = self.selected_category.get()
            for index, category in enumerate(present):
                x1 = index * cell_w
                x2 = width if index == len(present) - 1 else (index + 1) * cell_w
                is_selected = category == selected
                fill = COLORS["accent"] if is_selected else COLORS["soft"]
                outline = "#3c587d" if is_selected else "#223650"
                text_color = "#041014" if is_selected else COLORS["text"]
                canvas.create_rectangle(x1 + 2, 4, x2 - 2, 54, fill=fill, outline=outline)
                icon = self.load_item_icon(str(CATEGORY_ICON_PATHS.get(category, "")), 24)
                if icon:
                    canvas.create_image((x1 + x2) // 2, 22, image=icon)
                    self.category_images[category] = icon
                else:
                    canvas.create_text((x1 + x2) // 2, 19, text=CATEGORY_RULES[category]["mark"], fill=text_color, font=("Segoe UI", 9, "bold"))
                count = len(self.queue.get(category, []))
                label = CATEGORY_RULES[category]["mark"] if not count else f"{CATEGORY_RULES[category]['mark']} {count}"
                canvas.create_text((x1 + x2) // 2, 43, text=label, fill=text_color, font=("Segoe UI", 7, "bold"))
                self.category_hitboxes.append((x1, 0, x2, 58, category))
            return

        selected = self.selected_category.get()
        present = set(self.available_categories())
        for category, button in self.category_buttons.items():
            count = len(self.queue.get(category, []))
            text = CATEGORY_RULES[category]["mark"]
            if count:
                text = f"{text}\n{count}"
            icon = self.load_item_icon(str(CATEGORY_ICON_PATHS.get(category, "")), 22)
            button.configure(
                text=text,
                image=icon or "",
                bg=COLORS["accent"] if category == selected else COLORS["soft"],
                fg="#041014" if category == selected else (COLORS["text"] if category in present else COLORS["muted"]),
                state="normal" if category in present else "disabled",
            )
            if icon:
                self.category_images[category] = icon

    def on_category_canvas_click(self, event) -> str:
        for x1, y1, x2, y2, category in self.category_hitboxes:
            if x1 <= event.x <= x2 and y1 <= event.y <= y2:
                self.select_category(category)
                break
        return "break"

    def load_item_icon(self, path: str, size: int) -> tk.PhotoImage | None:
        if not path:
            return None
        key = (path, size)
        if key in self.icon_images:
            return self.icon_images[key]
        try:
            if Image and ImageTk:
                image = Image.open(path).convert("RGBA")
                image.thumbnail((size, size), Image.LANCZOS)
                canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
                canvas.alpha_composite(image, ((size - image.width) // 2, (size - image.height) // 2))
                photo = ImageTk.PhotoImage(canvas)
            else:
                photo = tk.PhotoImage(file=path)
        except Exception:
            return None
        self.icon_images[key] = photo
        return photo

    def refresh_item_grid(self) -> None:
        canvas = self.item_canvas
        if not canvas:
            return
        canvas.delete("all")
        self.item_hitboxes = []
        width = max(1, canvas.winfo_width())
        tile_w = 88
        tile_h = 88
        gap = 6
        columns = max(1, (width - gap) // (tile_w + gap))
        rows = self.filtered_items()
        if not rows:
            canvas.create_text(width // 2, 120, text=self.tr.t("production.empty_items"), fill=COLORS["muted"], font=("Segoe UI", 10, "bold"))
            return
        for index, item in enumerate(rows):
            column = index % columns
            row = index // columns
            x = gap + column * (tile_w + gap)
            y = gap + row * (tile_h + gap)
            queued = self.queue.get(item.category, []).count(item)
            fill = "#202020" if queued else "#151515"
            outline = COLORS["accent"] if queued else "#303030"
            canvas.create_rectangle(x, y, x + tile_w, y + tile_h, fill=fill, outline=outline, width=2 if queued else 1)
            icon = self.load_item_icon(item.icon_path, 50)
            if icon:
                canvas.create_image(x + tile_w // 2, y + 32, image=icon)
            else:
                canvas.create_rectangle(x + 28, y + 10, x + 60, y + 42, fill=COLORS["card_2"], outline="")
                canvas.create_text(x + tile_w // 2, y + 26, text=item.name[:2].upper(), fill=COLORS["text"], font=("Segoe UI", 10, "bold"))
            name = item.name if len(item.name) <= 20 else item.name[:17] + "..."
            canvas.create_text(x + tile_w // 2, y + 64, text=name, fill=COLORS["text"], font=("Segoe UI", 7, "bold"), width=tile_w - 8)
            if queued:
                canvas.create_oval(x + tile_w - 23, y + 5, x + tile_w - 5, y + 23, fill=COLORS["accent"], outline="")
                canvas.create_text(x + tile_w - 14, y + 14, text=str(queued), fill="#041014", font=("Segoe UI", 7, "bold"))
            self.item_hitboxes.append((x, y, x + tile_w, y + tile_h, item))
        needed_height = gap + math.ceil(len(rows) / columns) * (tile_h + gap)
        canvas.configure(scrollregion=(0, 0, width, max(canvas.winfo_height(), needed_height)))

    def item_at(self, x: int, y: int) -> ProductionItem | None:
        for x1, y1, x2, y2, item in self.item_hitboxes:
            if x1 <= x <= x2 and y1 <= y <= y2:
                return item
        return None

    def on_item_click(self, event) -> str:
        item = self.item_at(event.x, self.item_canvas.canvasy(event.y) if self.item_canvas else event.y)
        if item:
            is_ctrl = bool(event.state & 0x0004)
            is_shift = bool(event.state & 0x0001)
            if is_ctrl or is_shift:
                q = self.queue.get(item.category, [])
                if q and q[0].item_id == item.item_id and len(q) >= self.category_limit(item.category):
                    self.clear_category_queue(item.category)
                else:
                    self.fill_category_queue(item)
            else:
                self.add_queue_item(item)
        return "break"

    def clear_category_queue(self, category: str) -> None:
        self.queue[category] = []
        self.refresh_all()

    def on_item_right_click(self, event) -> str:
        item = self.item_at(event.x, self.item_canvas.canvasy(event.y) if self.item_canvas else event.y)
        if item:
            self.remove_queue_item(item.category, item)
        return "break"

    def add_queue_item(self, item: ProductionItem) -> None:
        category_queue = self.queue.setdefault(item.category, [])
        if category_queue and category_queue[0].item_id != item.item_id:
            category_queue.clear()
            
        limit = self.category_limit(item.category)
        if len(category_queue) >= limit:
            self.warning_var.set(self.tr.t("production.max_warning", category=item.category, max=limit))
            return
        category_queue.append(item)
        self.warning_var.set("")
        self.refresh_all()

    def fill_category_queue(self, item: ProductionItem) -> None:
        category_queue = self.queue.setdefault(item.category, [])
        if category_queue and category_queue[0].item_id != item.item_id:
            category_queue.clear()
            
        limit = self.category_limit(item.category)
        while len(self.queue[item.category]) < limit:
            self.queue[item.category].append(item)
        self.warning_var.set("")
        self.refresh_all()

    def remove_queue_item(self, category: str, item: ProductionItem | None = None, index: int | None = None) -> None:
        rows = self.queue.setdefault(category, [])
        if index is not None and 0 <= index < len(rows):
            rows.pop(index)
        elif item in rows:
            rows.remove(item)
        self.warning_var.set("")
        self.refresh_all()

    def clear_queue(self, refresh: bool = True) -> None:
        for category in CATEGORY_ORDER:
            self.queue[category] = []
        self.warning_var.set("")
        if refresh:
            self.refresh_all()

    def category_limit(self, category: str) -> int:
        if self.mode_var.get() == "factory":
            return 4 * max(1, self.factory_multiplier.get())
        return int(CATEGORY_RULES.get(category, {}).get("max") or 9)

    def category_minimum(self, category: str) -> int:
        if self.mode_var.get() == "factory":
            return 0
        return int(CATEGORY_RULES.get(category, {}).get("min") or 1)

    def material_totals(self) -> tuple[dict[str, float], dict[str, float], int, int, int]:
        totals = {key: 0.0 for key, _label in MATERIALS}
        base_totals = {key: 0.0 for key, _label in MATERIALS}
        total_crates = 0
        total_items = 0
        active_orders = 0
        for category in CATEGORY_ORDER:
            rows = self.queue.get(category, [])
            if rows:
                active_orders += 1
            for box_index, item in enumerate(rows, 1):
                multiplier = discount_multiplier(box_index) if self.mode_var.get() == "mpf" else 1.0
                total_crates += 1
                total_items += item.quantity_per_crate
                for key, _label in MATERIALS:
                    base = getattr(item, key)
                    totals[key] += base * multiplier
                    base_totals[key] += base
        return totals, base_totals, total_crates, total_items, active_orders

    def recalculate_queue(self) -> None:
        totals, base_totals, total_crates, total_items, _active_orders = self.material_totals()
        saved_total = sum(base_totals.values()) - sum(totals.values())
        base_total = sum(base_totals.values())
        discount = (saved_total / base_total * 100.0) if base_total else 0.0
        self.summary_var.set(self.tr.t("production.queue_summary", crates=total_crates, items=total_items))
        self.last_material_totals = totals
        self.materials_var.set(self.format_materials(totals))
        
        mode = self.mode_var.get()
        if mode == "mpf":
            self.orders_var.set(self.tr.t("production.queue_orders", orders=total_crates, discount=f"{discount:.1f}"))
        else:
            # Calculate factories needed
            max_factory = 1
            for rows in self.queue.values():
                if rows:
                    max_factory = max(max_factory, math.ceil(len(rows) / 4))
            msg = f"{total_crates} caixas\n{max_factory} Fábrica(s) necessária(s)"
            self.orders_var.set(msg)
            
        self.draw_material_strip()
        min_warnings = []
        if mode == "mpf":
            for category, rows in self.queue.items():
                minimum = self.category_minimum(category)
                if rows and len(rows) < minimum:
                    min_warnings.append(self.tr.t("production.min_warning", category=category, min=minimum))
        if min_warnings:
            self.warning_var.set("  ".join(min_warnings))
            
    def show_truck_planner(self) -> None:
        totals = self.last_material_totals
        if sum(totals.values()) == 0:
            return
            
        top = tk.Toplevel(self)
        top.title("Rotas de Transporte Logístico")
        top.geometry("450x520")
        top.configure(bg=COLORS["bg"])
        top.transient(self.winfo_toplevel())
        
        if ctk is None:
            top.grab_set()
            top.overrideredirect(True)
            
        header = modern_frame(top, COLORS["card"], radius=0, border=0)
        header.pack(fill="x", pady=(0, 10))
        
        tk.Label(header, text="Logística de Transporte", bg=COLORS["card"], fg=COLORS["text"], font=("Segoe UI", 14, "bold")).pack(pady=(12, 4))
        
        if ctk is None:
            tk.Button(header, text="X", command=top.destroy, bg=COLORS["card"], fg=COLORS["danger"], activebackground=COLORS["line"], relief="flat", font=("Segoe UI", 12, "bold")).place(relx=1.0, x=-10, y=10, anchor="ne")
        
        controls = tk.Frame(header, bg=COLORS["card"])
        controls.pack(pady=(0, 12))
        
        if self.mode_var.get() == "mpf":
            tk.Radiobutton(controls, text="Dunne (Solto)", variable=self.mpf_vehicle_mode, value="Dunne", bg=COLORS["card"], fg=COLORS["text"], selectcolor=COLORS["card_2"], activebackground=COLORS["card"], activeforeground=COLORS["text"], command=lambda: refresh_routes()).pack(side="left", padx=10)
            tk.Radiobutton(controls, text="Flatbed (Caixas)", variable=self.mpf_vehicle_mode, value="Flatbed", bg=COLORS["card"], fg=COLORS["text"], selectcolor=COLORS["card_2"], activebackground=COLORS["card"], activeforeground=COLORS["text"], command=lambda: refresh_routes()).pack(side="left", padx=10)
        else:
            tk.Label(controls, text="Veículo: Dunne Transport (15 Slots)", bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI", 9)).pack()
            self.mpf_vehicle_mode.set("Dunne")

        container = modern_frame(top, COLORS["soft"], radius=14, border=1, border_color=COLORS["line"])
        container.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        
        canvas = tk.Canvas(container, bg=COLORS["soft"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=COLORS["soft"])

        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True, padx=8, pady=8)
        scrollbar.pack(side="right", fill="y")
        
        def refresh_routes():
            for child in scrollable_frame.winfo_children():
                child.destroy()
                
            is_flatbed = self.mpf_vehicle_mode.get() == "Flatbed"
            mode = self.mode_var.get()
            
            # 1. Group queues into orders
            orders = []
            for category, items in self.queue.items():
                if not items: continue
                if mode == "factory":
                    for i in range(0, len(items), 4):
                        chunk = items[i:i+4]
                        orders.append((category, chunk))
                else:
                    orders.append((category, items))
                    
            if not orders:
                return

            trips = []
            
            for category, chunk in orders:
                # Calculate cost of this order
                mats = {key: 0.0 for key, _ in MATERIALS}
                for box_index, item in enumerate(chunk, 1):
                    multiplier = discount_multiplier(box_index) if mode == "mpf" else 1.0
                    for key, _ in MATERIALS:
                        mats[key] += getattr(item, key) * multiplier
                        
                # Pack into trips
                placed = False
                for trip in trips:
                    test_mats = {k: trip["materials"].get(k, 0) + mats.get(k, 0) for k, _ in MATERIALS}
                    
                    if is_flatbed:
                        in_slots = sum(math.ceil(math.ceil(test_mats[k]) / MATERIAL_CRATE_SIZES[k]) for k, _ in MATERIALS if test_mats[k] > 0)
                    else:
                        in_slots = sum(math.ceil(test_mats[k] / MATERIAL_CRATE_SIZES[k]) for k, _ in MATERIALS if test_mats[k] > 0)
                        
                    out_crates = trip["crates"] + len(chunk)
                    max_in = 60 if is_flatbed else 15
                    max_out = 60 if is_flatbed else 15
                    
                    if in_slots <= max_in and out_crates <= max_out:
                        trip["orders"].append((category, chunk))
                        trip["materials"] = test_mats
                        trip["crates"] = out_crates
                        trip["in_slots"] = in_slots
                        placed = True
                        break
                        
                if not placed:
                    if is_flatbed:
                        in_slots = sum(math.ceil(math.ceil(mats[k]) / MATERIAL_CRATE_SIZES[k]) for k, _ in MATERIALS if mats[k] > 0)
                    else:
                        in_slots = sum(math.ceil(mats[k] / MATERIAL_CRATE_SIZES[k]) for k, _ in MATERIALS if mats[k] > 0)
                    trips.append({
                        "orders": [(category, chunk)],
                        "materials": mats,
                        "crates": len(chunk),
                        "in_slots": in_slots
                    })

            tk.Label(scrollable_frame, text=f"Total de viagens ({self.mpf_vehicle_mode.get()}): {len(trips)}", bg=COLORS["soft"], fg=COLORS["accent"], font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(8, 12))
            
            for trip_num, trip in enumerate(trips):
                trip_frame = modern_frame(scrollable_frame, COLORS["card_2"], radius=8)
                trip_frame.pack(fill="x", pady=(0, 12), padx=4)
                
                tk.Label(trip_frame, text=f"Viagem {trip_num + 1}:", bg=COLORS["card_2"], fg="#fff", font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=10, pady=(6, 2))
                
                take_frame = tk.Frame(trip_frame, bg=COLORS["card_2"])
                take_frame.pack(fill="x", padx=10, pady=2)
                tk.Label(take_frame, text="Levar (Materiais):", bg=COLORS["card_2"], fg=COLORS["accent"], font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky="w")
                
                row_idx = 1
                for key, label in MATERIALS:
                    val = trip["materials"].get(key, 0)
                    if val > 0:
                        rounded = math.ceil(val - 1e-9)
                        crate_size = MATERIAL_CRATE_SIZES.get(key) or 1
                        if is_flatbed:
                            crates_needed = math.ceil(rounded / crate_size)
                            tk.Label(take_frame, text=f"• {crates_needed}x caixas de {label}", bg=COLORS["card_2"], fg=COLORS["text"], font=("Segoe UI", 9)).grid(row=row_idx, column=0, sticky="w", padx=(10, 0))
                        else:
                            tk.Label(take_frame, text=f"• {rounded} {label} soltos", bg=COLORS["card_2"], fg=COLORS["text"], font=("Segoe UI", 9)).grid(row=row_idx, column=0, sticky="w", padx=(10, 0))
                        row_idx += 1
                        
                bring_frame = tk.Frame(trip_frame, bg=COLORS["card_2"])
                bring_frame.pack(fill="x", padx=10, pady=(4, 6))
                tk.Label(bring_frame, text="Produzir / Retirar (Caixas):", bg=COLORS["card_2"], fg=COLORS["accent"], font=("Segoe UI", 9, "bold")).grid(row=0, column=0, columnspan=2, sticky="w")
                
                row_idx = 1
                for _cat, chunk in trip["orders"]:
                    item = chunk[0]
                    icon = self.load_item_icon(item.icon_path, 20)
                    if icon:
                        lbl = tk.Label(bring_frame, image=icon, bg=COLORS["card_2"])
                        lbl.image = icon
                        lbl.grid(row=row_idx, column=0, sticky="w", padx=(10, 0), pady=1)
                        tk.Label(bring_frame, text=f"{len(chunk)}x {item.name}", bg=COLORS["card_2"], fg=COLORS["text"], font=("Segoe UI", 9)).grid(row=row_idx, column=1, sticky="w", padx=(4, 0), pady=1)
                    else:
                        tk.Label(bring_frame, text=f"• {len(chunk)}x {item.name}", bg=COLORS["card_2"], fg=COLORS["text"], font=("Segoe UI", 9)).grid(row=row_idx, column=0, columnspan=2, sticky="w", padx=(10, 0), pady=1)
                    row_idx += 1
                
        refresh_routes()

    def format_materials(self, totals: dict[str, float]) -> str:
        parts = []
        for key, label in MATERIALS:
            value = totals.get(key, 0)
            if value > 0:
                rounded = math.ceil(value - 1e-9)
                crate_size = MATERIAL_CRATE_SIZES.get(key)
                if crate_size:
                    crates = math.ceil(rounded / crate_size)
                    parts.append(f"{rounded} {label} ({crates} cx)")
                else:
                    parts.append(f"{rounded} {label}")
        return ", ".join(parts) if parts else self.tr.t("production.no_materials")

    def draw_material_strip(self) -> None:
        canvas = self.material_canvas
        if not canvas:
            return
        canvas.delete("all")
        width = max(1, canvas.winfo_width())
        active = []
        for key, label in MATERIALS:
            value = self.last_material_totals.get(key, 0)
            if value > 0:
                rounded = math.ceil(value - 1e-9)
                crate_size = MATERIAL_CRATE_SIZES.get(key) or 1
                active.append((key, label, rounded, math.ceil(rounded / crate_size)))
        if not active:
            canvas.create_rectangle(0, 0, width, 64, fill="#101827", outline="#263c5b")
            canvas.create_text(12, 32, text=self.tr.t("production.no_materials"), fill=COLORS["muted"], anchor="w", font=("Segoe UI", 9, "bold"))
            return

        gap = 6
        card_w = max(98, min(136, (width - gap * (len(active) - 1)) // max(1, len(active))))
        x = 0
        crate_icon = self.load_item_icon(str(CRATE_ICON_PATH), 18)
        for key, label, raw_amount, crate_count in active:
            canvas.create_rectangle(x, 0, x + card_w, 64, fill="#101827", outline="#263c5b")
            icon = self.load_item_icon(str(MATERIAL_ICON_PATHS.get(key, "")), 30)
            if icon:
                canvas.create_image(x + 23, 25, image=icon)
            else:
                canvas.create_oval(x + 9, 10, x + 39, 40, fill=COLORS["card_2"], outline="")
            canvas.create_text(x + 46, 16, text=label, fill=COLORS["text"], anchor="w", font=("Segoe UI", 8, "bold"))
            canvas.create_text(x + 46, 33, text=str(raw_amount), fill=COLORS["accent"], anchor="w", font=("Segoe UI", 10, "bold"))
            if crate_icon:
                canvas.create_image(x + 50, 51, image=crate_icon)
                canvas.create_text(x + 64, 51, text=f"{crate_count} cx", fill=COLORS["muted"], anchor="w", font=("Segoe UI", 7, "bold"))
            else:
                canvas.create_text(x + 46, 51, text=f"{crate_count} cx", fill=COLORS["muted"], anchor="w", font=("Segoe UI", 7, "bold"))
            x += card_w + gap

    def draw_queue(self) -> None:
        canvas = self.queue_canvas
        if not canvas:
            return
        canvas.delete("all")
        self.queue_hitboxes = []
        width = max(1, canvas.winfo_width())
        y = 8
        for category in self.available_categories():
            rows = self.queue.get(category, [])
            rule = {**CATEGORY_RULES[category], "max": self.category_limit(category)}
            
            # Calculate required height based on wrapping
            items_per_row = max(1, int((width - 58) / 45))
            num_item_rows = max(1, (len(rows) + items_per_row - 1) // items_per_row) if len(rows) > 0 else 1
            row_h = 58 + (num_item_rows - 1) * 45
            
            canvas.create_rectangle(0, y, width, y + row_h, fill="#292929", outline="#3b3b3b")
            category_icon = self.load_item_icon(str(CATEGORY_ICON_PATHS.get(category, "")), 28)
            
            if category_icon:
                canvas.create_image(24, y + 22, image=category_icon)
            else:
                canvas.create_text(10, y + 17, text=rule["mark"], fill=COLORS["text"], anchor="w", font=("Segoe UI", 12, "bold"))
                
            canvas.create_text(10, y + 49, text=f"{len(rows)}/{rule['max']}", fill=COLORS["muted"], anchor="w", font=("Segoe UI", 7, "bold"))
            
            x = 58
            item_y = y
            for index, item in enumerate(rows):
                if x + 40 > width and x > 58:
                    x = 58
                    item_y += 45
                    
                icon = self.load_item_icon(item.icon_path, 32)
                canvas.create_rectangle(x, item_y + 9, x + 40, item_y + 49, fill="#555555", outline=COLORS["line"])
                if icon:
                    canvas.create_image(x + 20, item_y + 29, image=icon)
                else:
                    canvas.create_text(x + 20, item_y + 29, text=item.name[:2].upper(), fill=COLORS["text"], font=("Segoe UI", 7, "bold"))
                    
                discount = int((1 - discount_multiplier(index + 1)) * 100) if self.mode_var.get() == "mpf" else 0
                if discount:
                    canvas.create_text(x + 37, item_y + 15, text=f"{discount}", fill=COLORS["accent"], anchor="e", font=("Segoe UI", 6, "bold"))
                    
                self.queue_hitboxes.append((x, item_y + 9, x + 40, item_y + 49, category, index))
                x += 45
                
            y += row_h + 7

        canvas.configure(scrollregion=(0, 0, width, max(canvas.winfo_height(), y + 8)))

    def on_queue_click(self, event) -> str:
        if not self.queue_canvas:
            return "break"
        y = int(self.queue_canvas.canvasy(event.y))
        for x1, y1, x2, y2, category, index in self.queue_hitboxes:
            if x1 <= event.x <= x2 and y1 <= y <= y2:
                self.remove_queue_item(category, index=index)
                break
        return "break"

    def on_item_mousewheel(self, event) -> str:
        if self.item_canvas:
            self.item_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        return "break"

    def on_queue_mousewheel(self, event) -> str:
        if self.queue_canvas:
            self.queue_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        return "break"
