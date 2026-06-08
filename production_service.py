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


def input_slots(materials: dict[str, float], is_flatbed: bool = False) -> int:
    if is_flatbed:
        return sum(
            math.ceil(max(0.0, materials.get(key, 0.0)) / MATERIAL_CRATE_SIZES[key])
            for key, _label in MATERIALS
            if materials.get(key, 0.0) > 0
        )
    return sum(
        math.ceil(max(0.0, materials.get(key, 0.0)) / 100.0)
        for key, _label in MATERIALS
        if materials.get(key, 0.0) > 0
    )


def _flatbed_input_units(materials: dict[str, float]) -> list[str]:
    units: list[str] = []
    for key, _label in MATERIALS:
        value = materials.get(key, 0.0)
        if value > 0:
            units.extend([key] * math.ceil(max(0.0, value) / MATERIAL_CRATE_SIZES[key]))
    return units


def _materials_from_flatbed_units(units: list[str]) -> dict[str, float]:
    materials = {key: 0.0 for key, _label in MATERIALS}
    for key in units:
        materials[key] += MATERIAL_CRATE_SIZES[key]
    return materials


def _add_materials(left: dict[str, float], right: dict[str, float]) -> dict[str, float]:
    return {key: float(left.get(key, 0.0)) + float(right.get(key, 0.0)) for key, _label in MATERIALS}


def _flatbed_trip(
    *,
    orders: list[tuple[str, list[ProductionItem]]],
    materials: dict[str, float],
    warning: str = "",
    route_part: int = 0,
    route_parts: int = 0,
) -> dict[str, Any]:
    return {
        "orders": [(category, chunk) for category, chunk in orders if chunk],
        "materials": materials,
        "input_slots": input_slots(materials, is_flatbed=True),
        "output_crates": sum(len(chunk) for _category, chunk in orders),
        "vehicle": "Flatbed",
        "max_slots": 60,
        "warning": warning,
        "route_part": route_part,
        "route_parts": route_parts,
    }


def _flatbed_split_oversized_order(category: str, chunk: list[ProductionItem], materials: dict[str, float]) -> list[dict[str, Any]]:
    input_units = _flatbed_input_units(materials)
    output_items = list(chunk)
    trips: list[dict[str, Any]] = []
    warning_msg = "Essa fila tem mais de 60 caixas; cuidado para nao ser roubado."
    while input_units or output_items:
        trip_in_keys = input_units[:60]
        input_units = input_units[60:]
        trip_out_items = output_items[:60]
        output_items = output_items[60:]
        trips.append(
            _flatbed_trip(
                orders=[(category, trip_out_items)] if trip_out_items else [],
                materials=_materials_from_flatbed_units(trip_in_keys),
                warning=warning_msg,
            )
        )
    total_parts = len(trips)
    if total_parts > 1:
        dependency_warning = "Essa fila tem mais de 60 caixas; cuidado para nao ser roubado."
        for index, trip in enumerate(trips, 1):
            trip["route_part"] = index
            trip["route_parts"] = total_parts
            trip["warning"] = (
                f"{dependency_warning} Parte {index}/{total_parts} da mesma fila; "
                "mantenha junto com as outras partes."
            )
    return trips


def _trip_fill_score(trip: dict[str, Any]) -> int:
    return max(int(trip.get("input_slots") or 0), int(trip.get("output_crates") or 0))


def _plan_flatbed_routes(queue: dict[str, list[ProductionItem]], *, mode: str) -> list[dict[str, Any]]:
    pending: list[dict[str, Any]] = []
    grouped_trips: list[list[dict[str, Any]]] = []

    for category, chunk in route_orders(queue, mode=mode):
        if not chunk:
            continue
        materials = order_materials(chunk, mode=mode)
        order = {
            "category": category,
            "chunk": list(chunk),
            "materials": materials,
            "input_slots": input_slots(materials, is_flatbed=True),
            "output_crates": len(chunk),
        }
        if order["input_slots"] > 60 or order["output_crates"] > 60:
            grouped_trips.append(_flatbed_split_oversized_order(category, list(chunk), materials))
        else:
            pending.append(order)

    # Bigger queues first makes the remaining bins naturally stay close to 60.
    pending.sort(key=lambda order: max(int(order["input_slots"]), int(order["output_crates"])), reverse=True)

    bins: list[dict[str, Any]] = []
    for order in pending:
        best_index = -1
        best_score = -1
        for index, bin_data in enumerate(bins):
            combined_materials = _add_materials(bin_data["materials"], order["materials"])
            combined_input = input_slots(combined_materials, is_flatbed=True)
            combined_output = int(bin_data["output_crates"]) + int(order["output_crates"])
            if combined_input > 60 or combined_output > 60:
                continue
            score = max(combined_input, combined_output)
            if score > best_score:
                best_index = index
                best_score = score
        if best_index >= 0:
            target = bins[best_index]
            target["materials"] = _add_materials(target["materials"], order["materials"])
            target["orders"].append((order["category"], order["chunk"]))
            target["output_crates"] = int(target["output_crates"]) + int(order["output_crates"])
        else:
            bins.append(
                {
                    "materials": dict(order["materials"]),
                    "orders": [(order["category"], order["chunk"])],
                    "output_crates": int(order["output_crates"]),
                }
            )

    grouped_trips.extend(
        [_flatbed_trip(orders=bin_data["orders"], materials=bin_data["materials"])]
        for bin_data in bins
    )
    grouped_trips.sort(key=lambda group: max((_trip_fill_score(trip) for trip in group), default=0), reverse=True)
    return [trip for group in grouped_trips for trip in group]


def plan_transport_routes(
    queue: dict[str, list[ProductionItem]],
    *,
    mode: str,
    vehicle: str,
) -> list[dict[str, Any]]:
    is_flatbed = mode == "mpf" and vehicle.lower() == "flatbed"
    if is_flatbed:
        return _plan_flatbed_routes(queue, mode=mode)

    max_slots = 60 if is_flatbed else 15
    trips: list[dict[str, Any]] = []

    for category, chunk in route_orders(queue, mode=mode):
        if not chunk:
            continue
            
        total_materials = order_materials(chunk, mode=mode)
        
        input_units = []
        for key, _label in MATERIALS:
            val = total_materials.get(key, 0.0)
            if val > 0:
                if is_flatbed:
                    count = math.ceil(max(0.0, val) / MATERIAL_CRATE_SIZES[key])
                else:
                    count = math.ceil(max(0.0, val) / 100.0)
                input_units.extend([key] * count)
                
        output_items = list(chunk)
        
        needs_warning = is_flatbed and (len(input_units) > 60 or len(output_items) > 60)
        warning_msg = "Essa fila é mais de 60 caixas então tome cuidado para não ser roubado" if needs_warning else ""
        
        while input_units or output_items:
            trip_in_keys = input_units[:max_slots]
            input_units = input_units[max_slots:]
            
            trip_out_items = output_items[:max_slots]
            output_items = output_items[max_slots:]
            
            trip_materials = {key: 0.0 for key, _label in MATERIALS}
            for key in trip_in_keys:
                if is_flatbed:
                    trip_materials[key] += MATERIAL_CRATE_SIZES[key]
                else:
                    trip_materials[key] += 100.0
                    
            trips.append({
                "orders": [(category, trip_out_items)] if trip_out_items else [],
                "materials": trip_materials,
                "input_slots": len(trip_in_keys),
                "output_crates": len(trip_out_items),
                "vehicle": "Flatbed" if is_flatbed else "Dunne",
                "max_slots": max_slots,
                "warning": warning_msg,
            })
            
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
        counts = {}
        for item in chunk:
            counts[item.name] = counts.get(item.name, 0) + 1
        for name, count in counts.items():
            lines.append(f"{count}x {name} ({count} caixas)")
    return "\n".join(lines) if lines else "-"
