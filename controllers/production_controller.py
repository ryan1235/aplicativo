from __future__ import annotations
from controllers.i18n_controller import I18nController
from .dict_list_model import DictListModel
from .api_http_error import ApiHttpError
from .auth_ui_error import AuthUiError
import base64
import colorsys
import csv
import ctypes
from datetime import datetime, timezone
import hashlib
import html
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import math
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys
import threading
import time
from typing import Any, Callable
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from debug_logging import debug_log, debug_logger
from PySide6.QtNetwork import QNetworkAccessManager
from PySide6.QtCore import (
    QAbstractListModel,
    QMetaObject,
    QModelIndex,
    QObject,
    Property,
    QTimer,
    Qt,
    QUrl,
    Signal,
    Slot,
)
from PySide6.QtGui import QDesktopServices, QGuiApplication, QIcon
from PySide6.QtWidgets import QApplication, QFileDialog, QMenu, QMessageBox, QSystemTrayIcon
from app_metadata import APP_TITLE, APP_USER_AGENT, APP_VERSION
from app_paths import extracted_dir, resolve_writable_path, resource_dir, settings_path, user_data_dir
from app_update import UpdateInfo, check_latest_release, download_update, launch_updater
from auto_clicker import ACTION_KEYS, HOTKEYS, MOUSE_BUTTONS, POINT, RECT, AutoClicker
import identify_service
from identify_service import (
    dependencies_status as identify_dependencies_status,
    detect_stockpile_item_regions,
    prepare_detection_template,
    prepare_detection_template_path,
    grab_clipboard_image,
)
from i18n import SUPPORTED_LANGUAGES, Translator, normalize_language
from production_service import (
    CALCULATOR_MENU_DIR,
    CATEGORY_ORDER,
    CATEGORY_RULES,
    MATERIAL_CRATE_SIZES,
    MATERIAL_ICON_PATHS,
    MATERIALS,
    ProductionItem,
    available_categories,
    calculate_queue,
    category_limit,
    discount_multiplier,
    filter_items,
    format_route_materials,
    format_route_orders,
    load_production_items,
    plan_transport_routes,
)
from personalization_store import DEFAULT_THEME_CUSTOM, load_personalization_settings, save_personalization_settings
from settings_store import load_settings, save_settings, selected_language
from secure_store import secure_clear_credentials, secure_load_credentials, secure_save_credentials
from steam_profile import SteamProfile, get_local_steam_profile
from msupp_controller import MSuppController
from stockpiler import (
    DEFAULT_API_URL,
    STOCKPILE_DEBUG_LOG,
    StockpileWatcher,
    api_item_rows,
    api_last_update,
    default_output_path,
    discover_map_data_file,
    extract_and_post,
    format_to_local_pc_time,
    foxhole_savegames_dir,
    last_sent_output_path,
    request_stockpile_debug,
    warehouse_summaries,
)

from .common import *
from .common import _compact_location_key, _location_index, _warehouse_nested, _stockpile_town_code, _first_mapping_text, _location_from_stockpile_code, _location_code_index, _town_code_candidates, _warehouse_text, _strip_hex_suffix

class ProductionController(QObject):
    changed = Signal()

    def __init__(self, i18n: I18nController | None = None, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.i18n = i18n
        self.availableItems = DictListModel(
            ["key", "name", "category", "faction", "mode", "icon", "quantityPerCrate", "bmat", "emat", "rmat", "hemat", "relic"],
            self,
        )
        self.categories = DictListModel(["name", "mark", "count", "active", "icon"], self)
        self.queue = DictListModel(["key", "name", "category", "faction", "quantity", "icon", "line"], self)
        self.queueCategories = DictListModel(["name", "mark", "count", "limit", "active", "icon", "slots"], self)
        self.materials = DictListModel(["key", "label", "quantity", "crates", "icon"], self)
        self.routeTrips = DictListModel(["title", "vehicle", "materials", "orders", "inputSlots", "outputCrates", "capacity"], self)
        self._status = "Production database not loaded."
        self._loaded = False
        self._items_by_key: dict[str, ProductionItem] = {}
        self._queue: dict[str, list[ProductionItem]] = {category: [] for category in CATEGORY_ORDER}
        self._mode = "mpf"
        self._faction = "Neutral"
        self._category = ""
        self._query = ""
        self._factory_multiplier = 1
        self._route_vehicle_mode = "Dunne"
        self._summary = "-"
        self._orders = "-"
        self._material_summary = "-"
        self._material_detail = "-"
        self._route_summary = "-"
        self._warning = ""
        self._activity_logger: ActivityLogger | None = None
        if self.i18n:
            self.i18n.changed.connect(self.refresh)

    def setActivityLogger(self, logger: ActivityLogger | None) -> None:
        self._activity_logger = logger

    def _log_activity(self, action: str, *, subcategory: str, quantity: int = 1, metadata: dict[str, Any] | None = None) -> None:
        if callable(self._activity_logger):
            self._activity_logger("producao", action, quantity, metadata or {}, subcategory)

    @Slot()
    def ensureLoaded(self) -> None:
        if self._loaded:
            return
        all_items, self._status = load_production_items()
        self._items_by_key = {item.key: item for item in all_items}
        self._category = self._first_available_category()
        self._loaded = True
        self.refresh()

    @Property(str, notify=changed)
    def status(self) -> str:
        return self._status

    @Property(str, notify=changed)
    def mode(self) -> str:
        return self._mode

    @Property(str, notify=changed)
    def faction(self) -> str:
        return self._faction

    @Property(str, notify=changed)
    def category(self) -> str:
        return self._category

    @Property(str, notify=changed)
    def query(self) -> str:
        return self._query

    @Property(int, notify=changed)
    def factoryMultiplier(self) -> int:
        return self._factory_multiplier

    @Property(str, notify=changed)
    def routeVehicleMode(self) -> str:
        return self._route_vehicle_mode

    @Property(str, notify=changed)
    def summary(self) -> str:
        return self._summary

    @Property(str, notify=changed)
    def orders(self) -> str:
        return self._orders

    @Property(str, notify=changed)
    def materialSummary(self) -> str:
        return self._material_summary

    @Property(str, notify=changed)
    def materialDetail(self) -> str:
        return self._material_detail

    @Property(str, notify=changed)
    def routeSummary(self) -> str:
        return self._route_summary

    categoriesChanged = Signal()
    itemsChanged = Signal()
    queueChanged = Signal()
    queueCategoriesChanged = Signal()
    materialsChanged = Signal()
    routesChanged = Signal()

    @Property(str, notify=changed)
    def warning(self) -> str:
        return self._warning

    @Property("QStringList", constant=True)
    def modes(self) -> list[str]:
        return ["mpf", "factory"]

    @Property("QStringList", constant=True)
    def factions(self) -> list[str]:
        return ["Neutral", "Colonial", "Warden"]

    @Property("QStringList", notify=changed)
    def routeVehicleOptions(self) -> list[str]:
        return ["Dunne", "Flatbed"] if self._mode == "mpf" else ["Dunne"]

    @Property("QVariantList", notify=itemsChanged)
    def availableItemRows(self) -> list[dict[str, Any]]:
        return getattr(self, "_cached_available_items", self.availableItems.items())

    @Property("QVariantList", notify=categoriesChanged)
    def categoryRows(self) -> list[dict[str, Any]]:
        return getattr(self, "_cached_categories", self.categories.items())

    @Property("QVariantList", notify=queueChanged)
    def queueRows(self) -> list[dict[str, Any]]:
        return getattr(self, "_cached_queue", self.queue.items())

    @Property("QVariantList", notify=queueCategoriesChanged)
    def queueCategoryRows(self) -> list[dict[str, Any]]:
        return getattr(self, "_cached_queue_categories", self.queueCategories.items())

    @Property("QVariantList", notify=materialsChanged)
    def materialRows(self) -> list[dict[str, Any]]:
        return getattr(self, "_cached_materials", self.materials.items())

    @Property("QVariantList", notify=routesChanged)
    def routeTripRows(self) -> list[dict[str, Any]]:
        return getattr(self, "_cached_routes", self.routeTrips.items())

    @Property(QObject, constant=True)
    def availableItemsModel(self) -> QObject:
        return self.availableItems

    @Property(QObject, constant=True)
    def categoriesModel(self) -> QObject:
        return self.categories

    @Property(QObject, constant=True)
    def queueModel(self) -> QObject:
        return self.queue

    @Property(QObject, constant=True)
    def queueCategoriesModel(self) -> QObject:
        return self.queueCategories

    @Property(QObject, constant=True)
    def materialsModel(self) -> QObject:
        return self.materials

    @Property(QObject, constant=True)
    def routeTripsModel(self) -> QObject:
        return self.routeTrips

    @Slot()
    def reload(self) -> None:
        self._loaded = False
        self._items_by_key = {}
        self.clear()
        self.ensureLoaded()

    @Slot(str)
    def setMode(self, mode: str) -> None:
        self.ensureLoaded()
        if mode not in {"mpf", "factory"} or mode == self._mode:
            return
        self._mode = mode
        if self._mode != "mpf":
            self._route_vehicle_mode = "Dunne"
        self._queue = {category: [] for category in CATEGORY_ORDER}
        self._category = self._first_available_category()
        self._log_activity("alterar_modo", subcategory="calculadora", metadata={"mode": mode})
        self.refresh()

    @Slot(str)
    def setFaction(self, faction: str) -> None:
        self.ensureLoaded()
        if faction not in {"Neutral", "Colonial", "Warden"}:
            return
        self._faction = faction
        self._log_activity("alterar_faccao", subcategory="calculadora", metadata={"faction": faction})
        self.refresh()

    @Slot(str)
    def setCategory(self, category: str) -> None:
        self.ensureLoaded()
        if category not in CATEGORY_ORDER:
            return
        self._category = category
        self._log_activity("alterar_categoria", subcategory="calculadora", metadata={"category": category})
        self.refresh()

    @Slot(str)
    def search(self, query: str) -> None:
        self.ensureLoaded()
        self._query = query
        self.refresh()

    @Slot(int)
    def setFactoryMultiplier(self, value: int) -> None:
        self.ensureLoaded()
        self._factory_multiplier = min(2, max(1, int(value)))
        self._log_activity("alterar_multiplicador", subcategory="calculadora", metadata={"factoryMultiplier": self._factory_multiplier})
        self.refresh()

    @Slot(str)
    def setRouteVehicleMode(self, value: str) -> None:
        self.ensureLoaded()
        if value not in {"Dunne", "Flatbed"}:
            return
        if self._mode != "mpf":
            value = "Dunne"
        if value == self._route_vehicle_mode:
            return
        self._route_vehicle_mode = value
        self._log_activity("alterar_veiculo_rota", subcategory="rota", metadata={"vehicle": value})
        self.refresh()

    @Slot(str)
    def addItemByKey(self, key: str) -> None:
        self.ensureLoaded()
        item = self._items_by_key.get(key)
        if not item:
            self._warning = "Item not found."
            self.changed.emit()
            return
        self._add_item(item, fill=False)
        self._log_activity("adicionar_item", subcategory="fila", metadata={"itemKey": key, "category": item.category})

    @Slot(str)
    def fillCategoryWithItem(self, key: str) -> None:
        self.ensureLoaded()
        item = self._items_by_key.get(key)
        if item:
            category_queue = self._queue.setdefault(item.category, [])
            limit = category_limit(item.category, self._mode, self._factory_multiplier)
            if category_queue and category_queue[0].item_id == item.item_id and len(category_queue) >= limit:
                category_queue.clear()
                self.refresh()
            else:
                self._add_item(item, fill=True)
                self._log_activity("preencher_categoria", subcategory="fila", quantity=max(1, len(self._queue.get(item.category, []))), metadata={"itemKey": key, "category": item.category})

    @Slot(str)
    def removeItemByKey(self, key: str) -> None:
        self.ensureLoaded()
        item = self._items_by_key.get(key)
        if not item:
            return
        rows = self._queue.get(item.category, [])
        for index, queued in enumerate(rows):
            if queued.item_id == item.item_id:
                rows.pop(index)
                self._log_activity("remover_item", subcategory="fila", metadata={"itemKey": key, "category": item.category})
                self.refresh()
                return

    @Slot(str, int)
    def addItem(self, name: str, quantity: int) -> None:
        self.ensureLoaded()
        match = next((item for item in self._items_by_key.values() if item.name.lower() == name.strip().lower() and item.mode == self._mode), None)
        if not match:
            self._warning = f"Item not found: {name}"
            self.changed.emit()
            return
        quantity_value = max(1, int(quantity))
        for _ in range(quantity_value):
            self._add_item(match, fill=False, emit=False)
        self._log_activity("adicionar_item", subcategory="fila", quantity=quantity_value, metadata={"itemName": name, "category": match.category})
        self.refresh()

    @Slot(str, int)
    def removeQueueRow(self, category: str, index: int) -> None:
        self.ensureLoaded()
        rows = self._queue.get(category, [])
        if 0 <= index < len(rows):
            removed = rows.pop(index)
            self._log_activity("remover_item", subcategory="fila", metadata={"category": category, "itemName": getattr(removed, "name", "")})
        self.refresh()

    @Slot(str, int)
    def removeQueueSlot(self, category: str, index: int) -> None:
        self.removeQueueRow(category, index)

    @Slot(str)
    def clearCategory(self, category: str) -> None:
        self.ensureLoaded()
        if category in self._queue:
            quantity = len(self._queue.get(category, []))
            self._queue[category] = []
            self._log_activity("limpar_categoria", subcategory="fila", quantity=max(1, quantity), metadata={"category": category})
        self.refresh()

    @Slot()
    def clear(self) -> None:
        quantity = sum(len(rows) for rows in self._queue.values())
        self._queue = {category: [] for category in CATEGORY_ORDER}
        self._log_activity("limpar_fila", subcategory="fila", quantity=max(1, quantity))
        self.refresh()

    @Slot()
    def refresh(self) -> None:
        if not self._loaded:
            self.availableItems.set_items([])
            self.categories.set_items([])
            self.queue.set_items([])
            self.queueCategories.set_items([])
            self.materials.set_items([])
            self.routeTrips.set_items([])
            self.changed.emit()
            return
        _all_items = list(self._items_by_key.values())
        categories = available_categories(_all_items, self._mode)
        if self._category not in categories:
            self._category = categories[0] if categories else ""

        filtered = filter_items(
            _all_items,
            mode=self._mode,
            category=self._category,
            faction=self._faction,
            query=self._query,
        )
        self._cached_available_items = [self._item_to_model(item) for item in filtered]
        self.availableItems.set_items(self._cached_available_items)
        self.itemsChanged.emit()

        self._cached_categories = [
            {
                "name": category,
                "mark": str(CATEGORY_RULES.get(category, {}).get("mark") or category[:2].upper()),
                "count": len(self._queue.get(category, [])),
                "active": category == self._category,
                "icon": self._category_icon_url(category),
            }
            for category in categories
        ]
        self.categories.set_items(self._cached_categories)
        self.categoriesChanged.emit()

        totals = calculate_queue(self._queue, mode=self._mode)
        material_rows = self._material_rows(totals["totals"])

        self._cached_queue = self._queue_rows()
        self.queue.set_items(self._cached_queue)
        self.queueChanged.emit()

        self._cached_queue_categories = self._queue_category_rows(categories)
        self.queueCategories.set_items(self._cached_queue_categories)
        self.queueCategoriesChanged.emit()

        self._cached_materials = material_rows
        self.materials.set_items(self._cached_materials)
        self.materialsChanged.emit()

        self._cached_routes = self._route_rows()
        self.routeTrips.set_items(self._cached_routes)
        self.routesChanged.emit()

        material_crates = sum(int(row.get("crates", 0) or 0) for row in material_rows)
        self._summary = self._t("production.total_value", items=totals["total_items"])
        if self._mode == "mpf":
            self._orders = self._t(
                "production.total_detail_mpf",
                crates=totals["total_crates"],
                orders=totals["active_orders"],
                discount=f"{totals['discount']:.1f}",
            )
        else:
            self._orders = self._t(
                "production.total_detail_factory",
                crates=totals["total_crates"],
                factories=totals["max_factory"],
            )
        self._material_summary = self._t("production.material_total_value", crates=material_crates)
        self._material_detail = self._format_material_detail(material_rows)
        self._route_summary = f"{self.routeTrips.count()} trips | {self._route_vehicle_mode}"
        self._warning = "  ".join(totals["warnings"])
        if self._items_by_key:
            self._status = f"{len(filtered)} visible / {len(self._items_by_key)} loaded"
        self.changed.emit()

    def _first_available_category(self) -> str:
        categories = available_categories(list(self._items_by_key.values()), self._mode)
        return categories[0] if categories else ""

    def _add_item(self, item: ProductionItem, *, fill: bool, emit: bool = True) -> None:
        category_queue = self._queue.setdefault(item.category, [])
        if category_queue and category_queue[0].item_id != item.item_id:
            category_queue.clear()
        limit = category_limit(item.category, self._mode, self._factory_multiplier)
        if fill:
            while len(category_queue) < limit:
                category_queue.append(item)
        elif len(category_queue) < limit:
            category_queue.append(item)
        else:
            self._warning = f"{item.category} is already at its {limit} crate limit."
        if emit:
            self.refresh()

    def _item_to_model(self, item: ProductionItem) -> dict[str, Any]:
        return {
            "key": item.key,
            "name": item.name,
            "category": item.category,
            "faction": item.faction,
            "mode": item.mode,
            "icon": file_url(item.icon_path) if item.icon_path and Path(item.icon_path).exists() else "",
            "quantityPerCrate": item.quantity_per_crate,
            "bmat": int(item.bmat),
            "emat": int(item.emat),
            "rmat": int(item.rmat),
            "hemat": int(item.hemat),
            "relic": int(item.relic),
        }

    def _queue_rows(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for category in CATEGORY_ORDER:
            for index, item in enumerate(self._queue.get(category, [])):
                rows.append(
                    {
                        "key": item.key,
                        "name": item.name,
                        "category": category,
                        "faction": item.faction,
                        "quantity": item.quantity_per_crate,
                        "icon": file_url(item.icon_path) if item.icon_path and Path(item.icon_path).exists() else "",
                        "line": index,
                    }
                )
        return rows

    def _category_icon_url(self, category: str) -> str:
        mark = str(CATEGORY_RULES.get(category, {}).get("mark") or category[:2].upper()).lower()
        path = CALCULATOR_MENU_DIR / f"{mark}.png"
        return file_url(path) if path.exists() else ""

    def _queue_category_rows(self, categories: list[str]) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for category in categories:
            queued = self._queue.get(category, [])
            limit = category_limit(category, self._mode, self._factory_multiplier)
            slots: list[dict[str, Any]] = []
            for index in range(limit):
                if index < len(queued):
                    item = queued[index]
                    discount = int((1 - discount_multiplier(index + 1)) * 100) if self._mode == "mpf" else 0
                    price_parts = []
                    multiplier = discount_multiplier(index + 1) if self._mode == "mpf" else 1.0
                    for key, label in MATERIALS:
                        val = getattr(item, key, 0.0)
                        if val > 0:
                            price_parts.append(f"{int(math.ceil(val * multiplier - 1e-9))} {label}")
                    price_tooltip = " | ".join(price_parts)

                    slots.append(
                        {
                            "filled": True,
                            "line": index,
                            "name": item.name,
                            "icon": file_url(item.icon_path) if item.icon_path and Path(item.icon_path).exists() else "",
                            "discount": discount,
                            "priceTooltip": price_tooltip,
                        }
                    )
                else:
                    slots.append({"filled": False, "line": index, "name": "", "icon": "", "discount": 0, "priceTooltip": ""})
            rows.append(
                {
                    "name": category,
                    "mark": str(CATEGORY_RULES.get(category, {}).get("mark") or category[:2].upper()),
                    "count": len(queued),
                    "limit": limit,
                    "active": category == self._category,
                    "icon": self._category_icon_url(category),
                    "slots": slots,
                }
            )
        return rows

    def _material_rows(self, totals: dict[str, float]) -> list[dict[str, Any]]:
        rows = []
        for key, label in MATERIALS:
            quantity = int(math.ceil(max(0, totals.get(key, 0.0)) - 1e-9))
            if quantity <= 0:
                continue
            crate_size = MATERIAL_CRATE_SIZES.get(key, 1)
            rows.append(
                {
                    "key": key,
                    "label": label,
                    "quantity": quantity,
                    "crates": int(math.ceil(quantity / crate_size)),
                    "icon": file_url(MATERIAL_ICON_PATHS[key]) if key in MATERIAL_ICON_PATHS and MATERIAL_ICON_PATHS[key].exists() else "",
                }
            )
        return rows

    def _format_material_detail(self, rows: list[dict[str, Any]]) -> str:
        if not rows:
            return self._t("production.material_empty")
        parts = [
            self._t(
                "production.material_line",
                quantity=row.get("quantity", 0),
                label=row.get("label", ""),
                crates=row.get("crates", 0),
            )
            for row in rows
        ]
        if len(parts) <= 2:
            return " | ".join(parts)
        return " | ".join(parts[:2]) + "\n" + " | ".join(parts[2:])

    def _t(self, key: str, **kwargs: Any) -> str:
        if self.i18n:
            return self.i18n.translator.t(key, **kwargs)
        if kwargs:
            try:
                return key.format(**kwargs)
            except Exception:
                return key
        return key

    def _route_order_rows(self, orders: list[tuple[str, list[ProductionItem]]]) -> list[dict[str, Any]]:
        rows = []
        for _category, chunk in orders:
            if not chunk:
                continue
            counts = {}
            icons = {}
            for item in chunk:
                counts[item.name] = counts.get(item.name, 0) + 1
                if item.name not in icons:
                    icons[item.name] = file_url(item.icon_path) if item.icon_path and Path(item.icon_path).exists() else ""
            for name, count in counts.items():
                rows.append({"name": name, "count": count, "icon": icons[name]})
        return rows

    def _route_rows(self) -> list[dict[str, Any]]:
        trips = plan_transport_routes(self._queue, mode=self._mode, vehicle=self._route_vehicle_mode)
        rows: list[dict[str, Any]] = []
        for index, trip in enumerate(trips, 1):
            vehicle = str(trip.get("vehicle") or self._route_vehicle_mode)
            title = f"Trip {index}"
            route_part = int(trip.get("route_part") or 0)
            route_parts = int(trip.get("route_parts") or 0)
            if route_part and route_parts:
                title = f"{title} ({route_part}/{route_parts})"
            rows.append(
                {
                    "title": title,
                    "vehicle": vehicle,
                    "materials": format_route_materials(trip.get("materials", {}), vehicle=vehicle),
                    "orders": format_route_orders(trip.get("orders", [])),
                    "materialsList": self._material_rows(trip.get("materials", {})),
                    "ordersList": self._route_order_rows(trip.get("orders", [])),
                    "inputSlots": int(trip.get("input_slots") or 0),
                    "outputCrates": int(trip.get("output_crates") or 0),
                    "capacity": int(trip.get("max_slots") or 15),
                    "warning": str(trip.get("warning") or ""),
                }
            )
        return rows
