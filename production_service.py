from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
import sqlite3
from typing import Any

from stockpiler import DB_PATH, icon_info_for_asset


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
    "Resource": {"min": 3, "max": 9, "units": None, "mark": "RS", "factory": True, "mpf": True},
    "Uniforms": {"min": 3, "max": 9, "units": None, "mark": "UN", "factory": True, "mpf": True},
    "Vehicles": {"min": 1, "max": 5, "units": 3, "mark": "VH", "factory": False, "mpf": True},
    "Structures": {"min": 1, "max": 5, "units": 3, "mark": "ST", "factory": False, "mpf": True},
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

    @property
    def key(self) -> str:
        return f"{self.mode}:{self.item_id}"


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


def load_production_items(db_path: Path = DB_PATH) -> tuple[list[ProductionItem], str]:
    if not db_path.exists():
        return [], f"Production database missing: {db_path}"

    try:
        with sqlite3.connect(db_path) as connection:
            rows: list[tuple[Any, ...]] = []
            for mode, table, relic_expr, vehicle_bonus_expr in (
                ("factory", "items_factory", "NULL", "NULL"),
                ("mpf", "items_mpf", "relic", "vehicles_per_crate_bonus_quantity"),
            ):
                rows.extend(
                    (mode, *row)
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
        return [], f"Production database error: {exc}"

    items: list[ProductionItem] = []
    for row in rows:
        mode, item_id, name, faction, queue_type, bmat, emat, rmat, hemat, relic, quantity, time_value, vehicle_bonus = row
        category = category_from_queue(queue_type)
        rule = CATEGORY_RULES.get(category, {"units": None, "factory": False, "mpf": False})
        if mode == "mpf" and not rule.get("mpf", False):
            continue
        if mode == "factory" and not rule.get("factory", False):
            continue

        if rule.get("units"):
            units_per_crate = int(rule["units"])
        elif vehicle_bonus:
            units_per_crate = 1 + int(vehicle_bonus)
        else:
            units_per_crate = int(quantity or 1)
        icon_info = icon_info_for_asset(str(item_id))
        items.append(
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
    return items, f"Loaded {len(items)} production items"


def available_categories(items: list[ProductionItem], mode: str) -> list[str]:
    present = {item.category for item in items if item.mode == mode}
    return [category for category in CATEGORY_ORDER if category in present]


def filter_items(
    items: list[ProductionItem],
    *,
    mode: str,
    category: str,
    faction: str,
    query: str,
) -> list[ProductionItem]:
    query = query.strip().lower()
    rows = [item for item in items if item.mode == mode and item.category == category]
    if faction != "Neutral":
        rows = [item for item in rows if item.faction in {faction, "Neutral"}]
    if query:
        rows = [item for item in rows if query in item.name.lower()]
    return rows


def category_limit(category: str, mode: str, factory_multiplier: int) -> int:
    if mode == "factory":
        return 4 * max(1, factory_multiplier)
    return int(CATEGORY_RULES.get(category, {}).get("max") or 9)


def category_minimum(category: str, mode: str) -> int:
    if mode == "factory":
        return 0
    return int(CATEGORY_RULES.get(category, {}).get("min") or 1)


def calculate_queue(
    queue: dict[str, list[ProductionItem]],
    *,
    mode: str,
) -> dict[str, Any]:
    totals = {key: 0.0 for key, _label in MATERIALS}
    base_totals = {key: 0.0 for key, _label in MATERIALS}
    total_crates = 0
    total_items = 0
    active_orders = 0
    warnings = []

    for category in CATEGORY_ORDER:
        rows = queue.get(category, [])
        if rows:
            active_orders += 1
        for box_index, item in enumerate(rows, 1):
            multiplier = discount_multiplier(box_index) if mode == "mpf" else 1.0
            total_crates += 1
            total_items += item.quantity_per_crate
            for key, _label in MATERIALS:
                base = getattr(item, key)
                totals[key] += base * multiplier
                base_totals[key] += base
        minimum = category_minimum(category, mode)
        if mode == "mpf" and rows and len(rows) < minimum:
            warnings.append(f"{category} needs at least {minimum} crates for MPF.")

    saved_total = sum(base_totals.values()) - sum(totals.values())
    base_total = sum(base_totals.values())
    discount = (saved_total / base_total * 100.0) if base_total else 0.0
    max_factory = 1
    if mode == "factory":
        for rows in queue.values():
            if rows:
                max_factory = max(max_factory, math.ceil(len(rows) / 4))
    return {
        "totals": totals,
        "base_totals": base_totals,
        "total_crates": total_crates,
        "total_items": total_items,
        "active_orders": active_orders,
        "discount": discount,
        "max_factory": max_factory,
        "warnings": warnings,
    }


def route_orders(queue: dict[str, list[ProductionItem]], *, mode: str) -> list[tuple[str, list[ProductionItem]]]:
    orders: list[tuple[str, list[ProductionItem]]] = []
    for category in CATEGORY_ORDER:
        items = queue.get(category, [])
        if not items:
            continue
        if mode == "factory":
            for index in range(0, len(items), 4):
                orders.append((category, items[index : index + 4]))
        else:
            orders.append((category, list(items)))
    return orders


def order_materials(items: list[ProductionItem], *, mode: str) -> dict[str, float]:
    materials = {key: 0.0 for key, _label in MATERIALS}
    for box_index, item in enumerate(items, 1):
        multiplier = discount_multiplier(box_index) if mode == "mpf" else 1.0
        for key, _label in MATERIALS:
            materials[key] += getattr(item, key) * multiplier
    return materials


def input_slots(materials: dict[str, float]) -> int:
    return sum(
        math.ceil(max(0.0, materials.get(key, 0.0)) / MATERIAL_CRATE_SIZES[key])
        for key, _label in MATERIALS
        if materials.get(key, 0.0) > 0
    )


def plan_transport_routes(
    queue: dict[str, list[ProductionItem]],
    *,
    mode: str,
    vehicle: str,
) -> list[dict[str, Any]]:
    is_flatbed = mode == "mpf" and vehicle.lower() == "flatbed"
    max_slots = 60 if is_flatbed else 15
    trips: list[dict[str, Any]] = []

    for category, chunk in route_orders(queue, mode=mode):
        materials = order_materials(chunk, mode=mode)
        placed = False
        for trip in trips:
            test_materials = {
                key: trip["materials"].get(key, 0.0) + materials.get(key, 0.0)
                for key, _label in MATERIALS
            }
            test_input_slots = input_slots(test_materials)
            test_output_crates = int(trip["output_crates"]) + len(chunk)
            if test_input_slots <= max_slots and test_output_crates <= max_slots:
                trip["orders"].append((category, chunk))
                trip["materials"] = test_materials
                trip["input_slots"] = test_input_slots
                trip["output_crates"] = test_output_crates
                placed = True
                break
        if not placed:
            trips.append(
                {
                    "orders": [(category, chunk)],
                    "materials": materials,
                    "input_slots": input_slots(materials),
                    "output_crates": len(chunk),
                    "vehicle": "Flatbed" if is_flatbed else "Dunne",
                    "max_slots": max_slots,
                }
            )
    return trips


def format_route_materials(materials: dict[str, float], *, vehicle: str) -> str:
    is_flatbed = vehicle.lower() == "flatbed"
    lines: list[str] = []
    for key, label in MATERIALS:
        value = materials.get(key, 0.0)
        if value <= 0:
            continue
        rounded = math.ceil(value - 1e-9)
        crate_size = MATERIAL_CRATE_SIZES[key]
        if is_flatbed:
            lines.append(f"{math.ceil(rounded / crate_size)}x {label} crates")
        else:
            lines.append(f"{rounded} {label}")
    return "\n".join(lines) if lines else "-"


def format_route_orders(orders: list[tuple[str, list[ProductionItem]]]) -> str:
    lines: list[str] = []
    for _category, chunk in orders:
        if not chunk:
            continue
        lines.append(f"{len(chunk)}x {chunk[0].name}")
    return "\n".join(lines) if lines else "-"
