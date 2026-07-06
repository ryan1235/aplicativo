from __future__ import annotations
from controllers.stockpile_controller import StockpileController
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

class ItemSearchController(QObject):
    changed = Signal()
    rowsLoaded = Signal(object, str, str)
    wikiLoaded = Signal(object, str, int)

    def __init__(self, settings: dict[str, Any], parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.settings = settings
        self._query = ""
        self._status_key = "item_search.loading"
        self._status_count = 0
        self._status_message = ""
        self._loading = False
        self._loaded = False
        self._best_match = ""
        self._selected_name = ""
        self._total = 0
        self._last_update = "-"
        self.items = DictListModel(
            ["rowType", "region", "code", "warehouse", "place", "quantity", "updatedAt", "updatedAgo", "icon", "total"],
            self,
        )
        self.suggestions = DictListModel(["name", "alias", "detail", "source"], self)
        self.wiki_fields = DictListModel(["group", "label", "value"], self)
        self.wiki_production_rows = DictListModel(["site", "input", "output", "time"], self)
        self.wiki_sections = DictListModel(["title", "body"], self)
        self.wiki_categories = DictListModel(["label"], self)
        self.wiki_tech_rows = DictListModel(["label", "value", "kind"], self)
        self.damage_ammo_suggestions = DictListModel(["name", "detail"], self)
        self.damage_duel_left_suggestions = DictListModel(["name", "detail", "faction"], self)
        self.damage_duel_right_suggestions = DictListModel(["name", "detail", "faction"], self)
        self.damage_result_rows = DictListModel(["label", "value", "kind"], self)
        self.damage_duel_rows = DictListModel(["label", "value", "kind"], self)
        self._damage_data = self._load_damage_data()
        self._damage_ammo_rows = self._build_damage_ammo_rows(self._damage_data)
        self._damage_target_rows = self._build_damage_target_rows(self._damage_data)
        self._all_rows: list[dict[str, Any]] = []
        self._cached_item_names: list[str] = []
        self._name_norm_by_name: dict[str, str] = {}
        self._slang_terms = self._load_slang_terms()
        self._slang_resolved_names: dict[int, list[str]] = {}
        self._damage_target_rows = self._merge_damage_target_rows(self._damage_target_rows, self._damage_targets_from_terms())
        self._wiki_title = ""
        self._wiki_name = ""
        self._wiki_display_title = ""
        self._wiki_description = ""
        self._wiki_image = ""
        self._wiki_source_url = ""
        self._wiki_status_key = "item_search.wiki_empty"
        self._wiki_status_message = ""
        self._wiki_loading = False
        self._wiki_data: dict[str, Any] = {}
        self._damage_duel_left_name = ""
        self._damage_duel_right_name = ""
        self._damage_duel_left_image = ""
        self._damage_duel_right_image = ""
        self._damage_duel_left_detail = ""
        self._damage_duel_right_detail = ""
        self._damage_duel_left_faction = ""
        self._damage_duel_right_faction = ""
        self._damage_target_image = ""
        self._damage_ammo_image = ""
        self._damage_duel_ammo_image = ""
        self._damage_duel_ammo_name = ""
        self._damage_duel_ammo_damage = ""
        self._damage_duel_winner_name = ""
        self._damage_duel_left_hp = ""
        self._damage_duel_right_hp = ""
        self._damage_duel_left_shots = ""
        self._damage_duel_right_shots = ""
        self._damage_duel_left_prob = -1.0
        self._damage_duel_right_prob = -1.0
        self._wiki_request_token = 0
        self._pending_wiki_title = ""
        self._wiki_timer = QTimer(self)
        self._wiki_timer.setSingleShot(True)
        self._wiki_timer.setInterval(500)
        self._wiki_timer.timeout.connect(self._run_pending_wiki_lookup)
        self.rowsLoaded.connect(self._apply_loaded_rows)
        self.wikiLoaded.connect(self._apply_wiki_result)

    @Slot()
    def ensureLoaded(self) -> None:
        if not self._loaded and not self._loading:
            self.refresh()

    @Property(str, notify=changed)
    def status(self) -> str:
        if self._status_key == "item_search.loaded":
            return f"{self._status_count} items loaded."
        if self._status_key == "item_search.error":
            return f"Error loading items: {self._status_message}"
        if self._status_key == "item_search.best_match":
            return f"Suggestion: {self._best_match}"
        return self._status_message or "Loading items from the API..."

    @Property(str, notify=changed)
    def statusKey(self) -> str:
        return self._status_key

    @Property(int, notify=changed)
    def statusCount(self) -> int:
        return self._status_count

    @Property(str, notify=changed)
    def statusMessage(self) -> str:
        return self._status_message

    @Property(str, notify=changed)
    def query(self) -> str:
        return self._query

    @Property(bool, notify=changed)
    def loading(self) -> bool:
        return self._loading

    @Property(bool, notify=changed)
    def loaded(self) -> bool:
        return self._loaded

    @Property(str, notify=changed)
    def bestMatch(self) -> str:
        return self._best_match

    @Property(str, notify=changed)
    def selectedName(self) -> str:
        return self._selected_name

    @Property(int, notify=changed)
    def total(self) -> int:
        return self._total

    @Property(str, notify=changed)
    def lastUpdate(self) -> str:
        return self._last_update

    @Property(QObject, constant=True)
    def resultRows(self) -> QObject:
        return self.items

    @Property(QObject, constant=True)
    def suggestionRows(self) -> QObject:
        return self.suggestions

    @Property(QObject, constant=True)
    def wikiFields(self) -> QObject:
        return self.wiki_fields

    @Property(QObject, constant=True)
    def wikiProduction(self) -> QObject:
        return self.wiki_production_rows

    @Property(QObject, constant=True)
    def wikiSections(self) -> QObject:
        return self.wiki_sections

    @Property(QObject, constant=True)
    def wikiCategories(self) -> QObject:
        return self.wiki_categories

    @Property(QObject, constant=True)
    def wikiTechRows(self) -> QObject:
        return self.wiki_tech_rows

    @Property(QObject, constant=True)
    def damageAmmoSuggestions(self) -> QObject:
        return self.damage_ammo_suggestions

    @Property(QObject, constant=True)
    def damageDuelLeftSuggestions(self) -> QObject:
        return self.damage_duel_left_suggestions

    @Property(QObject, constant=True)
    def damageDuelRightSuggestions(self) -> QObject:
        return self.damage_duel_right_suggestions

    @Property(QObject, constant=True)
    def damageResultRows(self) -> QObject:
        return self.damage_result_rows

    @Property(QObject, constant=True)
    def damageDuelRows(self) -> QObject:
        return self.damage_duel_rows

    @Slot(str, result="QVariantList")
    def damageDuelPresets(self, faction: str = "") -> list[dict[str, Any]]:
        return self._damage_preset_rows(faction)

    @Slot(result="QVariantList")
    def damageDuelAmmoOptions(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = [
            {
                "name": "Auto",
                "detail": "Melhor munição estimada",
                "value": "",
                "image": "",
            }
        ]
        for ammo in self._damage_ammo_rows:
            if not self._ammo_relevant_for_tank_duel(ammo, "tank armour armor vehicle"):
                continue
            name = str(ammo.get("name") or "")
            if not name:
                continue
            rows.append(
                {
                    "name": name,
                    "detail": str(ammo.get("detail") or ammo.get("damage_type") or ""),
                    "value": name,
                    "image": self._damage_ammo_image_for(ammo),
                }
            )
        return rows[:24]

    @Property(str, notify=changed)
    def damageDuelLeftName(self) -> str:
        return self._damage_duel_left_name

    @Property(str, notify=changed)
    def damageDuelRightName(self) -> str:
        return self._damage_duel_right_name

    @Property(str, notify=changed)
    def damageDuelLeftImage(self) -> str:
        return self._damage_duel_left_image

    @Property(str, notify=changed)
    def damageDuelRightImage(self) -> str:
        return self._damage_duel_right_image

    @Property(str, notify=changed)
    def damageDuelLeftDetail(self) -> str:
        return self._damage_duel_left_detail

    @Property(str, notify=changed)
    def damageDuelRightDetail(self) -> str:
        return self._damage_duel_right_detail

    @Property(str, notify=changed)
    def damageDuelLeftFaction(self) -> str:
        return self._damage_duel_left_faction

    @Property(str, notify=changed)
    def damageDuelRightFaction(self) -> str:
        return self._damage_duel_right_faction

    @Property(float, notify=changed)
    def damageDuelLeftProb(self) -> float:
        return self._damage_duel_left_prob

    @Property(float, notify=changed)
    def damageDuelRightProb(self) -> float:
        return self._damage_duel_right_prob

    @Property(str, notify=changed)
    def damageTargetImage(self) -> str:
        return self._damage_target_image

    @Property(str, notify=changed)
    def damageAmmoImage(self) -> str:
        return self._damage_ammo_image

    @Property(str, notify=changed)
    def damageDuelAmmoImage(self) -> str:
        return self._damage_duel_ammo_image

    @Property(str, notify=changed)
    def damageDuelAmmoName(self) -> str:
        return self._damage_duel_ammo_name

    @Property(str, notify=changed)
    def damageDuelAmmoDamage(self) -> str:
        return self._damage_duel_ammo_damage

    @Property(str, notify=changed)
    def damageDuelWinnerName(self) -> str:
        return self._damage_duel_winner_name

    @Property(str, notify=changed)
    def damageDuelLeftHp(self) -> str:
        return self._damage_duel_left_hp

    @Property(str, notify=changed)
    def damageDuelRightHp(self) -> str:
        return self._damage_duel_right_hp

    @Property(str, notify=changed)
    def damageDuelLeftShots(self) -> str:
        return self._damage_duel_left_shots

    @Property(str, notify=changed)
    def damageDuelRightShots(self) -> str:
        return self._damage_duel_right_shots

    @Property("QVariantList", notify=changed)
    def resultRowItems(self) -> list[dict[str, Any]]:
        return self.items.items()

    @Property("QVariantList", notify=changed)
    def suggestionRowItems(self) -> list[dict[str, Any]]:

        return self.suggestions.items()

    @Property(bool, notify=changed)
    def wikiLoading(self) -> bool:
        return self._wiki_loading

    @Property(str, notify=changed)
    def wikiStatusKey(self) -> str:
        return self._wiki_status_key

    @Property(str, notify=changed)
    def wikiStatusMessage(self) -> str:
        return self._wiki_status_message

    @Property(str, notify=changed)
    def wikiName(self) -> str:
        return self._wiki_name

    @Property(str, notify=changed)
    def wikiDisplayTitle(self) -> str:
        return self._wiki_display_title

    @Property(str, notify=changed)
    def wikiDescription(self) -> str:
        return self._wiki_description

    @Property(str, notify=changed)
    def wikiImage(self) -> str:
        return self._wiki_image

    @Property(str, notify=changed)
    def wikiSourceUrl(self) -> str:
        return self._wiki_source_url

    @Slot()
    def refreshLocalizedTimes(self) -> None:
        if self._loaded:
            self._update_search_models()
        if self._wiki_data:
            self._render_wiki_data(self._wiki_data)
        self.changed.emit()

    @Slot()
    def refresh(self) -> None:
        if self._loading:
            return
        self._loading = True
        self._status_key = "item_search.loading"
        self._status_message = ""
        self.changed.emit()

        def worker() -> None:
            try:
                stockpile = self.settings.get("stockpile", {})
                api_response = request_stockpile_debug(str(stockpile.get("api_url", DEFAULT_API_URL)))
                rows = api_item_rows(api_response)
                last_update = format_to_local_pc_time(api_last_update(api_response))
                self.rowsLoaded.emit(rows, last_update, "")
            except Exception as exc:
                self.rowsLoaded.emit([], "-", str(exc))

        threading.Thread(target=worker, daemon=True).start()

    @Slot(object, str, str)
    def _apply_loaded_rows(self, rows: object, last_update: str, error: str) -> None:
        self._loading = False
        if error:
            self._status_key = "item_search.error"
            self._status_message = error
            self.changed.emit()
            return
        raw_rows = list(rows) if isinstance(rows, list) else []
        self._all_rows = [
            item
            for item in raw_rows
            if isinstance(item, dict) and self._is_searchable_stockpile_item(item)
        ]
        self._cached_item_names = sorted(
            {str(item.get("display_name") or "-") for item in self._all_rows if item.get("display_name")},
            key=str.lower,
        )
        self._name_norm_by_name = {name: self._normalize_search_text(name) for name in self._cached_item_names}
        self._damage_target_rows = self._merge_damage_target_rows(self._damage_target_rows, self._damage_targets_from_item_names())
        self._slang_resolved_names = {}
        self._last_update = last_update or "-"
        self._loaded = True
        self._status_key = "item_search.loaded"
        self._status_count = len(self._all_rows)
        self._update_search_models()
        self.changed.emit()

    @Slot(str)
    def search(self, query: str) -> None:
        self._query = query
        self._update_search_models()
        self.changed.emit()

    @Slot(str)
    def chooseSuggestion(self, name: str) -> None:
        self._query = str(name)
        self._update_search_models()
        self.changed.emit()

    @Slot(str)
    def fetchWikiInfo(self, title: str) -> None:
        self._start_wiki_lookup(str(title or "").strip())

    @Slot()
    def openWikiPage(self) -> None:
        if self._wiki_source_url:
            QDesktopServices.openUrl(QUrl(self._wiki_source_url))

    @Slot()
    def prepareDamageCalculator(self) -> None:
        self._update_damage_ammo_suggestions("")
        target = self._current_damage_target()
        self.damage_result_rows.set_items(self._damage_target_preview_rows())
        self._damage_target_image = str(target.get("image") or "")
        self._damage_ammo_image = ""
        self._damage_duel_ammo_image = ""
        self._damage_duel_ammo_name = ""
        self._damage_duel_ammo_damage = ""
        self._damage_duel_winner_name = ""
        self._damage_duel_left_hp = ""
        self._damage_duel_right_hp = ""
        self._damage_duel_left_shots = ""
        self._damage_duel_right_shots = ""
        self.damage_duel_rows.set_items([])
        self._update_damage_duel_suggestions("", "left")
        self._update_damage_duel_suggestions("", "right")
        self._damage_duel_left_prob = -1.0
        self._damage_duel_right_prob = -1.0
        self.changed.emit()

    @Slot(str)
    def searchDamageAmmo(self, query: str) -> None:
        self._update_damage_ammo_suggestions(query)

    @Slot(str, str, str)
    def searchDamageDuelTarget(self, query: str, side: str, faction: str = "") -> None:
        self._update_damage_duel_suggestions(query, side, faction)

    @Slot(str, str)
    def calculateDamageTarget(self, ammo_name: str, penetration_percent: str = "") -> None:
        target = self._current_damage_target()
        ammo = self._find_damage_ammo(ammo_name)
        rows = self._calculate_damage_rows(target, ammo, penetration_percent)
        self.damage_result_rows.set_items(rows)
        self._damage_target_image = str(target.get("image") or "")
        self._damage_ammo_image = self._damage_ammo_image_for(ammo)
        self.changed.emit()

    @Slot(str, str, str, str)
    def calculateTankDuel(self, left_name: str, right_name: str, ammo_name: str = "", penetration_percent: str = "") -> None:
        ammo = self._find_damage_ammo(ammo_name) if ammo_name.strip() else {}
        left = self._find_damage_target(left_name)
        right = self._find_damage_target(right_name)
        self._damage_duel_left_name = clean_wiki_text(left.get("name") or left_name)
        self._damage_duel_right_name = clean_wiki_text(right.get("name") or right_name)
        self._damage_duel_left_image = self._damage_tank_image_for(left)
        self._damage_duel_right_image = self._damage_tank_image_for(right)
        self._damage_duel_left_detail = clean_wiki_text(left.get("detail") or left.get("resistance_type") or "")
        self._damage_duel_right_detail = clean_wiki_text(right.get("detail") or right.get("resistance_type") or "")
        self._damage_duel_left_faction = self._detect_faction(left)
        self._damage_duel_right_faction = self._detect_faction(right)
        self._damage_duel_left_hp = self._format_damage_stat(self._damage_number(left.get("hp")), " HP")
        self._damage_duel_right_hp = self._format_damage_stat(self._damage_number(right.get("hp")), " HP")
        rows = self._calculate_duel_rows(left, right, ammo, penetration_percent)
        # Extract win probabilities for bar display
        self._damage_duel_left_prob = -1.0
        self._damage_duel_right_prob = -1.0
        # Pick any valid ammo for the bar (specific if given, else best from all ammos)
        bar_ammo = ammo if ammo else self._best_ammo_for_duel(left, right, penetration_percent)
        self._damage_duel_ammo_image = self._damage_ammo_image_for(bar_ammo if bar_ammo else ammo)
        self._damage_duel_ammo_name = clean_wiki_text((bar_ammo or ammo).get("name") if (bar_ammo or ammo) else "")
        self._damage_duel_ammo_damage = self._format_damage_stat(self._damage_number((bar_ammo or ammo).get("damage") if (bar_ammo or ammo) else None), " dano")
        self._damage_duel_winner_name = ""
        self._damage_duel_left_shots = ""
        self._damage_duel_right_shots = ""
        if bar_ammo:
            left_attack = self._damage_estimate(right, bar_ammo, penetration_percent)
            right_attack = self._damage_estimate(left, bar_ammo, penetration_percent)
            if left_attack.get("ok") and right_attack.get("ok"):
                left_score = left_attack.get("expected_destroy") or left_attack.get("hits_destroy")
                right_score = right_attack.get("expected_destroy") or right_attack.get("hits_destroy")
                left_hits = left_attack.get("hits_destroy")
                right_hits = right_attack.get("hits_destroy")
                self._damage_duel_left_shots = self._format_duel_shots(left_score, left_hits)
                self._damage_duel_right_shots = self._format_duel_shots(right_score, right_hits)
                if left_score and right_score:
                    if left_score < right_score:
                        self._damage_duel_winner_name = self._damage_duel_left_name
                    elif right_score < left_score:
                        self._damage_duel_winner_name = self._damage_duel_right_name
                    else:
                        self._damage_duel_winner_name = "Empate tecnico"
                lp = left_attack.get("probability_destroy")
                rp = right_attack.get("probability_destroy")
                if lp is not None:
                    self._damage_duel_left_prob = float(lp)
                if rp is not None:
                    self._damage_duel_right_prob = float(rp)
                if lp is None and rp is None:
                    ls = left_attack.get("expected_destroy") or left_attack.get("hits_destroy")
                    rs = right_attack.get("expected_destroy") or right_attack.get("hits_destroy")
                    if ls and rs and (ls + rs) > 0:
                        self._damage_duel_left_prob = float(rs) / (ls + rs)
                        self._damage_duel_right_prob = float(ls) / (ls + rs)
        self.damage_duel_rows.set_items(rows)
        self.changed.emit()

    def _best_ammo_for_duel(self, left: dict[str, Any], right: dict[str, Any], penetration_percent: str = "") -> dict[str, Any]:
        """Find the ammo where the combined kill efficiency is highest (smallest total shots)."""
        best: dict[str, Any] = {}
        best_total: float | None = None
        best_damage = 0.0
        combined_resistance = self._normalize_search_text(
            " ".join(
                str(value)
                for value in (
                    left.get("resistance_type"),
                    left.get("detail"),
                    right.get("resistance_type"),
                    right.get("detail"),
                )
                if value
            )
        )
        for ammo in self._damage_ammo_rows:
            if not self._ammo_relevant_for_tank_duel(ammo, combined_resistance):
                continue
            la = self._damage_estimate(right, ammo, penetration_percent)
            ra = self._damage_estimate(left, ammo, penetration_percent)
            if not la.get("ok") or not ra.get("ok"):
                continue
            ls = self._damage_number(la.get("expected_destroy") or la.get("hits_destroy")) or 9999
            rs = self._damage_number(ra.get("expected_destroy") or ra.get("hits_destroy")) or 9999
            total = float(ls) + float(rs)
            damage = self._damage_number(ammo.get("damage")) or 0
            if best_total is None or total < best_total or (abs(total - best_total) < 0.001 and damage > best_damage):
                best = ammo
                best_total = total
                best_damage = float(damage)
        return best



    @staticmethod
    def _detect_faction(target: dict[str, Any]) -> str:
        """Detect faction from target detail/name/source. Returns 'warden', 'colonial' or ''."""
        haystack = ItemSearchController._normalize_search_text(
            " ".join(str(v) for v in [target.get("detail"), target.get("name"), target.get("faction")] if v)
        )
        if any(w in haystack for w in ("warden", "blacksteele", "callahan", "mercy", "nakki", "brigand", "loyalist", "silver", "harpa")):
            return "warden"
        if any(w in haystack for w in ("colonial", "conqueror", "titan", "poseidon", "trident", "ares", "ironship", "cullen", "predator")):
            return "colonial"
        return ""

    @Slot()
    def _run_pending_wiki_lookup(self) -> None:
        self._start_wiki_lookup(self._pending_wiki_title)

    def _clear_wiki_info(self) -> None:
        self._wiki_timer.stop()
        self._pending_wiki_title = ""
        self._wiki_title = ""
        self._wiki_name = ""
        self._wiki_display_title = ""
        self._wiki_description = ""
        self._wiki_image = ""
        self._wiki_source_url = ""
        self._wiki_status_key = "item_search.wiki_empty"
        self._wiki_status_message = ""
        self._wiki_loading = False
        self._wiki_data = {}
        self.wiki_fields.set_items([])
        self.wiki_production_rows.set_items([])
        self.wiki_sections.set_items([])
        self.wiki_categories.set_items([])
        self.wiki_tech_rows.set_items([])

    def _schedule_wiki_lookup(self) -> None:
        if not self._query.strip():
            if self._wiki_title or self._wiki_loading or self._wiki_name:
                self._clear_wiki_info()
            return
        title = (self._best_match or self._selected_name or self._query).strip()
        if not title:
            self._clear_wiki_info()
            return
        if title == self._wiki_title and (self._wiki_loading or self._wiki_name or self._wiki_status_key != "item_search.wiki_empty"):
            return
        self._pending_wiki_title = title
        self._wiki_timer.start()

    def _start_wiki_lookup(self, title: str) -> None:
        title = str(title or "").strip()
        if not title:
            self._clear_wiki_info()
            self.changed.emit()
            return
        if title == self._wiki_title and self._wiki_loading:
            return

        self._wiki_request_token += 1
        token = self._wiki_request_token
        self._wiki_title = title
        self._wiki_name = title
        self._wiki_display_title = ""
        self._wiki_description = ""
        self._wiki_image = ""
        self._wiki_source_url = f"{FOXHOLE_WIKI_BASE_URL}/wiki/{urllib.parse.quote(title.replace(' ', '_'))}"
        self._wiki_status_key = "item_search.wiki_loading"
        self._wiki_status_message = ""
        self._wiki_loading = True
        self.wiki_fields.set_items([])
        self.wiki_tech_rows.set_items([])
        self.wiki_production_rows.set_items([])
        self.wiki_sections.set_items([])
        self.wiki_categories.set_items([])
        self.changed.emit()

        def worker() -> None:
            try:
                self.wikiLoaded.emit(fetch_wiki_item_info(title), "", token)
            except Exception as exc:
                self.wikiLoaded.emit({}, str(exc), token)

        threading.Thread(target=worker, daemon=True).start()

    @Slot(object, str, int)
    def _apply_wiki_result(self, data: object, error: str, token: int) -> None:
        if token != self._wiki_request_token:
            return
        self._wiki_loading = False
        if error:
            self._wiki_status_key = "item_search.wiki_error"
            self._wiki_status_message = error
            self._wiki_data = {}
            self.wiki_fields.set_items([])
            self.wiki_production_rows.set_items([])
            self.wiki_sections.set_items([])
            self.wiki_categories.set_items([])
            self.wiki_tech_rows.set_items([])
            self.changed.emit()
            return

        item = data if isinstance(data, dict) else {}
        self._wiki_data = item
        self._render_wiki_data(item)
        self.changed.emit()

    def _render_wiki_data(self, item: dict[str, Any]) -> None:
        production = item.get("production") if isinstance(item.get("production"), list) else []
        raw_sections = item.get("sections") if isinstance(item.get("sections"), list) else []
        raw_categories = item.get("categories") if isinstance(item.get("categories"), list) else []
        raw_fields = item.get("fields") if isinstance(item.get("fields"), list) else []
        excluded = {"name", "image", "remote_image", "description", "production", "source_url", "sections", "categories", "fields"}
        language = selected_language(self.settings)
        if raw_fields:
            fields = [
                {
                    "group": wiki_section_label(row.get("group"), language),
                    "label": wiki_field_label(str(row.get("key") or normalize_wiki_key(str(row.get("label") or ""))), language),
                    "value": translate_wiki_value(row.get("value"), language),
                }
                for row in raw_fields
                if isinstance(row, dict) and translate_wiki_value(row.get("value"), language)
            ]
        else:
            fields = [
                {"group": "", "label": wiki_field_label(str(key), language), "value": translate_wiki_value(value, language)}
                for key, value in item.items()
                if key not in excluded and translate_wiki_value(value, language)
            ]
        sections = [
            {
                "title": wiki_section_label(row.get("title"), language),
                "body": translate_wiki_value(row.get("body"), language),
            }
            for row in raw_sections
            if isinstance(row, dict) and clean_wiki_text(row.get("body"))
        ]
        categories = [
            {"label": translate_wiki_value(value, language)}
            for value in raw_categories
            if translate_wiki_value(value, language)
        ]
        tech_rows = self._build_wiki_tech_rows(item, raw_fields, language)
        has_data = bool(
            item.get("display_title")
            or item.get("name")
            or item.get("description")
            or item.get("image")
            or fields
            or tech_rows
            or production
            or sections
            or categories
        )

        self._wiki_name = clean_wiki_text(item.get("name") or self._wiki_title)
        self._wiki_display_title = clean_wiki_text(item.get("display_title") or "")
        self._wiki_description = translate_wiki_value(item.get("description") or "", language)
        self._wiki_image = str(item.get("image") or "")
        self._wiki_source_url = str(item.get("source_url") or self._wiki_source_url)
        self._wiki_status_key = "item_search.wiki_loaded" if has_data else "item_search.wiki_empty"
        self._wiki_status_message = ""
        self.wiki_fields.set_items(fields[:24])
        self.wiki_tech_rows.set_items(tech_rows[:10])
        self.wiki_sections.set_items(sections[:8])
        self.wiki_categories.set_items(categories[:8])
        self.wiki_production_rows.set_items(
            [
                {
                    "site": translate_wiki_value(row.get("site"), language),
                    "input": translate_wiki_value(row.get("input"), language),
                    "output": translate_wiki_value(row.get("output"), language),
                    "time": clean_wiki_text(row.get("time")),
                }
                for row in production[:8]
                if isinstance(row, dict)
            ]
        )

    def _build_wiki_tech_rows(self, item: dict[str, Any], raw_fields: list[dict[str, Any]], language: str | None = None) -> list[dict[str, str]]:
        values: dict[str, Any] = {}
        for row in raw_fields:
            if not isinstance(row, dict):
                continue
            key = normalize_wiki_key(str(row.get("key") or row.get("label") or ""))
            if key and key not in values:
                values[key] = row.get("value")
        for key, value in item.items():
            if key not in values:
                values[str(key)] = value

        candidates = [
            ("health", ("health", "hitpoints", "hp"), "success"),
            ("armour", ("armour", "armor", "resistance", "resistance_type"), "warning"),
            ("damage", ("damage", "explosive_damage", "ap_damage"), "success"),
            ("damage_type", ("damage_type",), "info"),
            ("penetration_modifier", ("penetration_modifier",), "warning"),
            ("range", ("range",), "info"),
            ("rate_of_fire", ("rate_of_fire", "fire_rate"), "info"),
            ("reload_time", ("reload_time", "reload", "cooldown"), "warning"),
            ("magazine_size", ("magazine_size",), "info"),
            ("crew", ("crew",), "success"),
            ("fuel_capacity", ("fuel_capacity",), "info"),
            ("storage_capacity", ("storage_capacity",), "info"),
            ("disable_threshold", ("disable_threshold",), "warning"),
            ("inner_radius", ("inner_radius",), "info"),
            ("outer_radius", ("outer_radius",), "info"),
            ("faction", ("faction",), "info"),
            ("class", ("class", "super_class", "category"), "info"),
            ("production_site", ("production_site", "main_production_site"), "note"),
        ]

        rows: list[dict[str, str]] = []
        used_keys: set[str] = set()
        for label_key, keys, kind in candidates:
            for key in keys:
                if key in used_keys:
                    continue
                raw_value = values.get(key)
                text = translate_wiki_value(raw_value, language)
                if not text:
                    continue
                rows.append({"label": wiki_field_label(label_key, language), "value": text, "kind": kind})
                used_keys.add(key)
                break
        return rows

    def _damage_preset_candidate(self, row: dict[str, Any]) -> bool:
        name = self._normalize_search_text(row.get("name"))
        detail = self._normalize_search_text(row.get("detail"))
        haystack = f"{name} {detail}"
        if not haystack.strip():
            return False
        if row.get("category") == "ship":
            return False
        blocked = (
            "anti-tank", "anti tank", "rifle", "pillbox", "grenade", "flask", "ammo", "munition",
            "half-track", "half track", "armored car", "armoured car", "armouries", "armories",
            "bunker", "base", "garrison", "facility", "structure", "ship", "submarine",
        )
        if any(token in haystack for token in blocked):
            return False
        tokens = (
            "tank", "battle tank", "light tank", "medium tank", "heavy tank", "super heavy",
            "spatha", "bardiche", "silverhand", "outlaw", "devitt", "falchion", "ballista",
            "scorpion", "talos", "predator", "stygian", "ares", "chieftain", "kranesca", "mpt",
            "doru", "trident", "hatchet", "pelekys", "bonelaw", "highwayman", "thornfall",
        )
        return any(token in haystack for token in tokens)

    def _damage_preset_score(self, row: dict[str, Any], faction_norm: str) -> int:
        name = self._normalize_search_text(row.get("name"))
        detail = self._normalize_search_text(row.get("detail"))
        score = 0
        if faction_norm and self._damage_row_faction(row) == faction_norm:
            score += 40
        if any(token in name for token in ("battle tank", "light tank", "medium tank", "heavy tank", "super heavy")):
            score += 35
        if any(token in name for token in ("tank", "spatha", "bardiche", "silverhand", "outlaw", "devitt", "falchion", "ballista", "scorpion", "talos", "predator", "stygian", "ares", "chieftain", "kranesca", "mpt")):
            score += 25
        if self._damage_number(row.get("hp")):
            score += 40
        if row.get("source") == "damege.json":
            score += 15
        if row.get("source") == "wiki":
            score += 5
        if detail:
            score += 1
        return score

    def _damage_preset_rows(self, faction: str = "") -> list[dict[str, str]]:
        faction_norm = self._normalize_damage_faction(faction)
        rows: list[tuple[int, dict[str, Any]]] = []
        seen: set[str] = set()
        for row in self._damage_target_rows:
            if not self._damage_preset_candidate(row):
                continue
            row_faction = self._damage_row_faction(row)
            if faction_norm and row_faction and row_faction != faction_norm:
                continue
            key = self._normalize_search_text(row.get("name"))
            if not key or key in seen:
                continue
            seen.add(key)
            rows.append((self._damage_preset_score(row, faction_norm), row))
        seed_queries = []
        if faction_norm == "warden":
            seed_queries = ["warden tank", "warden battle tank", "warden heavy tank", "warden light tank", "warden armored vehicle"]
        elif faction_norm == "colonial":
            seed_queries = ["colonial tank", "colonial battle tank", "colonial heavy tank", "colonial light tank", "colonial armored vehicle"]
        else:
            seed_queries = ["tank", "battle tank", "light tank", "heavy tank"]
        for query in seed_queries:
            try:
                titles = search_wiki_page_titles(query, 8)
            except Exception:
                titles = []
            for title in titles:
                key = self._normalize_search_text(title)
                if not key or key in seen:
                    continue
                seen.add(key)
                rows.append((5 + (30 if faction_norm else 0), {"name": title, "detail": "Wiki | preset", "faction": faction_norm or self._damage_row_faction({"name": title, "detail": title})}))
        rows.sort(key=lambda item: (-item[0], str(item[1].get("name") or "").lower()))
        return [
            {
                "name": str(row.get("name") or ""),
                "detail": str(row.get("detail") or ""),
                "faction": str(row.get("faction") or self._damage_row_faction(row)),
                "image": self._damage_tank_image_for(row),
            }
            for _score, row in rows[:12]
        ]

    @staticmethod
    def _load_damage_data() -> dict[str, Any]:
        path = BASE_DIR / "data" / "damege.json"
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return data if isinstance(data, dict) else {}

    @staticmethod
    def _damage_number(value: Any) -> float | None:
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return float(value)
        text = clean_wiki_text(value)
        if not text:
            return None
        match = re.search(r"\d+(?:[.,]\d+)?", text.replace(" ", ""))
        if not match:
            return None
        try:
            return float(match.group(0).replace(",", "."))
        except ValueError:
            return None

    @staticmethod
    def _format_damage_stat(value: float | None, suffix: str = "") -> str:
        if value is None:
            return ""
        number = int(value) if float(value).is_integer() else round(float(value), 1)
        return f"{number:g}{suffix}"

    @classmethod
    def _format_duel_shots(cls, shots: Any, penetrations: Any = None) -> str:
        value = cls._damage_number(shots)
        if value is None:
            return ""
        text = f"{int(value) if float(value).is_integer() else value:g}"
        pen_value = cls._damage_number(penetrations)
        if pen_value is not None and int(pen_value) != int(value):
            text += f" ({int(pen_value)} pen.)"
        return text

    @staticmethod
    def _damage_percent(value: Any) -> float | None:
        number = ItemSearchController._damage_number(value)
        if number is None:
            return None
        if number > 1:
            number = number / 100.0
        if number <= 0:
            return None
        return min(1.0, number)

    @staticmethod
    def _local_damage_ammo_image_url(name: object, damage_type: object = "") -> str:
        text = ItemSearchController._normalize_search_text(f"{name} {damage_type}")
        if not text:
            return ""
        candidates: list[str] = []
        icon_map: tuple[tuple[tuple[str, ...], tuple[str, ...]], ...] = (
            (("12.7", "12 7", "machine gun", "heavy kinetic"), ("Content/Textures/UI/ItemIcons/FieldMGAmmoItemIcon.png", "Content/Textures/UI/ItemIcons/MachineGunAmmoIcon.png")),
            (("14.5", "14 5", "anti tank kinetic", "atrifle"), ("Content/Textures/UI/ItemIcons/ATRifleAmmoItemIcon.png", "Content/Textures/UI/ItemIcons/ATAmmoIcon.png")),
            (("20mm", "20 mm", "shrapnel"), ("Content/Textures/UI/VehicleIcons/LightAAAmmoIcon.png", "Content/Textures/UI/ItemIcons/ATAmmoIcon.png")),
            (("30mm", "30 mm"), ("Content/Textures/UI/ItemIcons/MiniTankAmmoItemIcon.png", "Content/Textures/UI/ItemIcons/ATAmmoIcon.png")),
            (("40mm", "40 mm"), ("Content/Textures/UI/ItemIcons/LightTankAmmoItemIcon.png", "Content/Textures/UI/ItemIcons/ATAmmoIcon.png")),
            (("68mm", "68 mm"), ("Content/Textures/UI/ATLargeAmmoIcon.png", "Content/Textures/UI/ItemIcons/ATAmmoIcon.png")),
            (("75mm", "75 mm", "94.5", "94 5"), ("Content/Textures/UI/ItemIcons/BattleTankAmmoItemIcon.png", "Content/Textures/UI/ATLargeAmmoIcon.png")),
            (("120mm", "120 mm"), ("Content/Textures/UI/ItemIcons/LightArtilleryAmmoItemIcon.png", "Content/Textures/UI/ItemIcons/LRArtilleryAmmoItemIcon.png")),
            (("150mm", "150 mm", "250mm", "250 mm"), ("Content/Textures/UI/ItemIcons/HeavyArtilleryAmmoItemIcon.png",)),
            (("high explosive rocket", "herocket", "3c high"), ("Content/Textures/UI/ItemIcons/HERocketAmmoIcon.png",)),
            (("demolition rocket", "shatter missile"), ("Content/Textures/UI/ItemIcons/DemolitionRocketAmmoIcon.png",)),
            (("ap/rpg", "arc/rpg", "atrpg"), ("Content/Textures/UI/ItemIcons/ATRpgAmmoItemIcon.png",)),
            (("rpg",), ("Content/Textures/UI/ItemIcons/RpgAmmoItemIcon.png",)),
            (("ignifist", "white ash", "sticky", "anti tank explosive"), ("Content/Textures/UI/ItemIcons/ATGrenadeWIcon.png", "Content/Textures/UI/ItemIcons/ATAmmoIcon.png")),
            (("mammon", "tremola", "grenade"), ("Content/Textures/UI/ItemIcons/HELaunchedGrenadeItemIcon.png", "Content/Textures/UI/ItemIcons/HEGrenadeItemIcon.png")),
            (("torpedo",), ("Content/Textures/UI/ItemIcons/TorpedoIcon.png", "Content/Textures/UI/ItemIcons/MiniTorpedoAmmoIcon.png")),
            (("minefield", "sea mine", "hullbreaker"), ("Content/Textures/UI/ItemIcons/SeaMineIcon.png",)),
            (("mine",), ("Content/Textures/UI/ItemIcons/AntiTankMineItemIcon.png",)),
            (("charge", "havoc", "alligator", "demolition"), ("Content/Textures/UI/ItemIcons/SatchelChargeTIcon.png", "Content/Textures/UI/StructureIcons/SatchelCharge.png")),
        )
        for tokens, paths in icon_map:
            if any(token in text for token in tokens):
                candidates.extend(paths)
        candidates.extend(
            (
                "Content/Textures/UI/ItemIcons/ATAmmoIcon.png",
                "Content/Textures/UI/ItemIcons/SubtypeAmmoIcon.png",
            )
        )
        for relative in candidates:
            path = BASE_DIR / relative
            if path.exists():
                return file_url(path)
        return ""

    def _damage_ammo_image_for(self, ammo: dict[str, Any]) -> str:
        if not ammo:
            return ""
        image = str(ammo.get("image") or "")
        if image:
            return image
        return self._local_damage_ammo_image_url(ammo.get("name"), ammo.get("damage_type"))

    @staticmethod
    def _local_damage_tank_image_url(name: object, detail: object = "") -> str:
        text = ItemSearchController._normalize_search_text(f"{name} {detail}")
        if not text:
            return ""
        icon_map: tuple[tuple[tuple[str, ...], tuple[str, ...]], ...] = (
            (("falchion", "spatha", "kranesca", "colonial medium", "medium tank c"), ("Content/Textures/UI/VehicleIcons/ColonialMediumTankIcon.png", "Content/Textures/UI/VehicleIcons/ColonialMediumTankOffensive.png")),
            (("doru", "tankette"), ("Content/Textures/UI/VehicleIcons/TanketteCVehicleIcon.png", "Content/Textures/UI/VehicleIcons/TanketteOffensiveCVehicleIcon.png")),
            (("trident", "pelekys", "light tank c", "hatchet"), ("Content/Textures/UI/VehicleIcons/LightTankColVehicleIcon.png", "Content/Textures/UI/VehicleIcons/LightTankOffensiveCVehicleIcon.png")),
            (("bardiche", "talos", "medium tank large"), ("Content/Textures/UI/VehicleIcons/MediumTankLargeCIcon.png",)),
            (("ares", "super tank c", "predator", "cullen"), ("Content/Textures/UI/VehicleIcons/SuperTankCtemIcon.png", "Content/Textures/UI/VehicleIcons/SuperTankWVehicleIcon.png")),
            (("silverhand", "outlaw", "warden medium", "highwayman", "thornfall"), ("Content/Textures/UI/VehicleIcons/WardenMediumTankIcon.png", "Content/Textures/UI/VehicleIcons/MediumTank2WIcon.png")),
            (("devitt", "light tank w", "light tank"), ("Content/Textures/UI/VehicleIcons/LightTankWarVehicleIcon.png", "Content/Textures/UI/VehicleIcons/LightTank3WVehicleIcon.png")),
            (("bonelaw", "destroyer tank"), ("Content/Textures/UI/VehicleIcons/DestroyerTankWVehicleIcon.png",)),
            (("chieftain", "ballista", "siege"), ("Content/Textures/UI/VehicleIcons/MediumTankSiegeWVehicleIcon.png", "Content/Textures/UI/VehicleIcons/MediumTank3CItemIcon.png")),
            (("scorpion", "infantry support"), ("Content/Textures/UI/VehicleIcons/LightTank2InfantryCVehicleIcon.png",)),
            (("battle tank",), ("Content/Textures/UI/VehicleIcons/BattleTank.png", "Content/Textures/UI/VehicleIcons/BattleTankWar.png")),
            (("scout tank",), ("Content/Textures/UI/VehicleIcons/ScoutTankWIcon.png",)),
            (("mortar tank",), ("Content/Textures/UI/VehicleIcons/MortarTankVehicleIcon.png",)),
        )
        candidates: list[str] = []
        for tokens, paths in icon_map:
            if any(token in text for token in tokens):
                candidates.extend(paths)
        candidates.extend(
            (
                "Content/Textures/UI/VehicleIcons/LightTankWarVehicleIcon.png",
                "Content/Textures/UI/VehicleIcons/ColonialMediumTankIcon.png",
            )
        )
        for relative in candidates:
            path = BASE_DIR / relative
            if path.exists():
                return file_url(path)
        return ""

    def _damage_tank_image_for(self, target: dict[str, Any]) -> str:
        if not target:
            return ""
        image = str(target.get("image") or "")
        if image:
            return image
        return self._local_damage_tank_image_url(target.get("name"), target.get("detail") or target.get("resistance_type"))

    @staticmethod
    def _build_damage_ammo_rows(data: dict[str, Any]) -> list[dict[str, Any]]:
        raw = data.get("municoes_importantes") if isinstance(data, dict) else {}
        if not isinstance(raw, dict):
            return []
        rows: list[dict[str, Any]] = []
        for name, payload in raw.items():
            if not isinstance(payload, dict):
                continue
            damage = ItemSearchController._damage_number(payload.get("damage"))
            if damage is None:
                continue
            damage_type = clean_wiki_text(payload.get("damage_type"))
            uses = payload.get("uso") if isinstance(payload.get("uso"), list) else []
            detail = f"{int(damage) if damage.is_integer() else damage:g} dano"
            if damage_type:
                detail += f" | {damage_type}"
            if uses:
                detail += f" | {', '.join(clean_wiki_text(use) for use in uses[:2])}"
            rows.append(
                {
                    "name": str(name),
                    "detail": detail,
                    "damage": damage,
                    "damage_type": damage_type,
                    "penetration_modifier": ItemSearchController._damage_number(payload.get("penetration_modifier")),
                    "inner_radius_m": ItemSearchController._damage_number(payload.get("inner_radius_m")),
                    "outer_radius_m": ItemSearchController._damage_number(payload.get("outer_radius_m")),
                    "uso": uses,
                    "image": ItemSearchController._local_damage_ammo_image_url(name, damage_type),
                }
            )
        return sorted(rows, key=lambda row: row["name"].lower())

    @staticmethod
    def _build_damage_target_rows(data: dict[str, Any]) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        large_ships = data.get("large_ship_hp") if isinstance(data, dict) else {}
        if isinstance(large_ships, dict):
            for name, payload in large_ships.items():
                if not isinstance(payload, dict):
                    continue
                hp = ItemSearchController._damage_number(payload.get("hp"))
                if hp is None:
                    continue
                detail = " | ".join(
                    part
                    for part in (
                        clean_wiki_text(payload.get("sigla")),
                        clean_wiki_text(payload.get("classe")),
                        clean_wiki_text(payload.get("faction")),
                        f"{int(hp)} HP",
                    )
                    if part
                )
                rows.append(
                    {
                        "name": str(name),
                        "detail": detail,
                        "hp": hp,
                        "disable_threshold": ItemSearchController._damage_percent(payload.get("disable_threshold")),
                        "resistance_type": clean_wiki_text(payload.get("resistance_type") or "Large Ship"),
                        "category": "ship",
                        "source": "damege.json",
                    }
                )
        examples = data.get("exemplos_calculados") if isinstance(data, dict) else {}
        if isinstance(examples, dict):
            for payload in examples.values():
                if not isinstance(payload, dict):
                    continue
                name = clean_wiki_text(payload.get("target"))
                hp = ItemSearchController._damage_number(payload.get("hp"))
                if not name or hp is None:
                    continue
                target_type = clean_wiki_text(payload.get("target_type"))
                rows.append(
                    {
                        "name": name,
                        "detail": " | ".join(part for part in (target_type, f"{int(hp)} HP") if part),
                        "hp": hp,
                        "disable_threshold": ItemSearchController._damage_percent(payload.get("disable_threshold")),
                        "resistance_type": target_type or "Heavy Armour",
                        "category": "tank",
                        "source": "damege.json",
                    }
                )
        unique: dict[str, dict[str, Any]] = {}
        for row in rows:
            unique.setdefault(ItemSearchController._normalize_search_text(row.get("name")), row)
        return sorted(unique.values(), key=lambda row: str(row.get("name") or "").lower())

    @staticmethod
    def _merge_damage_target_rows(*groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
        merged: dict[str, dict[str, Any]] = {}
        for rows in groups:
            for row in rows:
                name = clean_wiki_text(row.get("name"))
                if not name:
                    continue
                key = ItemSearchController._normalize_search_text(name)
                existing = merged.get(key)
                if not existing:
                    merged[key] = dict(row)
                    continue
                if not existing.get("hp") and row.get("hp"):
                    existing.update(row)
                else:
                    aliases = list(existing.get("aliases", [])) if isinstance(existing.get("aliases"), list) else []
                    aliases.extend(row.get("aliases", []) if isinstance(row.get("aliases"), list) else [])
                    existing["aliases"] = list(dict.fromkeys(str(alias) for alias in aliases if str(alias or "").strip()))
        return sorted(merged.values(), key=lambda row: str(row.get("name") or "").lower())

    def _damage_targets_from_terms(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        useful_tokens = ("tank", "vehicle", "armour", "armor", "ship", "submarine", "carrier", "destroyer", "frigate")
        for term in self._slang_terms:
            name = clean_wiki_text(term.get("name"))
            haystack = self._normalize_search_text(
                " ".join(
                    [
                        name,
                        clean_wiki_text(term.get("category")),
                        clean_wiki_text(term.get("kind")),
                        " ".join(str(alias) for alias in term.get("aliases", []) if alias),
                    ]
                )
            )
            if not name or not any(token in haystack for token in useful_tokens):
                continue
            rows.append(
                {
                    "name": name,
                    "detail": " | ".join(
                        part
                        for part in (
                            clean_wiki_text(term.get("category")),
                            clean_wiki_text(term.get("kind")),
                            clean_wiki_text(term.get("faction")),
                        )
                        if part
                    ),
                    "aliases": list(term.get("aliases", [])) if isinstance(term.get("aliases"), list) else [],
                    "hp": None,
                    "disable_threshold": None,
                    "resistance_type": clean_wiki_text(term.get("category")),
                    "category": "vehicle",
                    "source": "terms",
                }
            )
        return rows

    def _damage_targets_from_item_names(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        useful_tokens = ("tank", "armoured", "armored", "vehicle", "half track", "half-track", "gunboat", "submarine", "battleship", "destroyer")
        for name in self._cached_item_names:
            norm = self._normalize_search_text(name)
            if any(token.replace("-", " ") in norm for token in useful_tokens):
                rows.append(
                    {
                        "name": name,
                        "detail": "Item carregado | Wiki resolve HP/imagem ao calcular",
                        "aliases": [],
                        "hp": None,
                        "disable_threshold": None,
                        "resistance_type": "",
                        "category": "vehicle",
                        "source": "items",
                    }
                )
        return rows

    def _find_damage_ammo(self, name: str) -> dict[str, Any]:
        query = self._normalize_search_text(name)
        if not query and self._damage_ammo_rows:
            return dict(self._damage_ammo_rows[0])
        for row in self._damage_ammo_rows:
            if self._normalize_search_text(row.get("name")) == query:
                return dict(row)
        for row in self._damage_ammo_rows:
            haystack = self._normalize_search_text(f"{row.get('name')} {row.get('detail')}")
            if query and query in haystack:
                return dict(row)
        # Not found in local DB — try wiki
        if query:
            try:
                wiki_ammo = self._fetch_ammo_from_wiki(name)
                if wiki_ammo:
                    self._damage_ammo_rows = sorted(
                        self._damage_ammo_rows + [wiki_ammo],
                        key=lambda r: str(r.get("name") or "").lower(),
                    )
                    return wiki_ammo
            except Exception:
                pass
        return {}

    def _fetch_ammo_from_wiki(self, name: str) -> dict[str, Any] | None:
        """Try to fetch ammo damage info from the Foxhole wiki."""
        title = clean_wiki_text(name)
        if not title:
            return None
        try:
            resolved = search_wiki_page_title(title) or title
            item = fetch_wiki_item_info(resolved)
        except Exception:
            return None
        fields = item.get("fields") if isinstance(item.get("fields"), list) else []
        values: dict[str, Any] = {}
        for field in fields:
            if not isinstance(field, dict):
                continue
            key = str(field.get("key") or normalize_wiki_key(str(field.get("label") or "")))
            values[key] = field.get("value")
        damage = self._damage_number(
            values.get("damage") or values.get("explosive_damage") or values.get("ap_damage")
        )
        if damage is None:
            return None
        damage_type = clean_wiki_text(values.get("damage_type") or values.get("type") or "")
        item_name = clean_wiki_text(item.get("name") or resolved)
        detail = f"{int(damage) if float(damage).is_integer() else damage:g} dano | Wiki"
        if damage_type:
            detail = f"{int(damage) if float(damage).is_integer() else damage:g} dano | {damage_type} | Wiki"
        return {
            "name": item_name,
            "detail": detail,
            "damage": damage,
            "damage_type": damage_type,
            "penetration_modifier": self._damage_number(values.get("penetration_modifier")),
            "inner_radius_m": self._damage_number(values.get("inner_radius")),
            "outer_radius_m": self._damage_number(values.get("outer_radius")),
            "source": "wiki",
            "image": str(item.get("image") or item.get("remote_image") or "") or self._local_damage_ammo_image_url(item_name, damage_type),
        }

    def _find_damage_target(self, name: str) -> dict[str, Any]:
        query = self._normalize_search_text(name)
        for row in self._damage_target_rows:
            aliases = row.get("aliases", []) if isinstance(row.get("aliases"), list) else []
            alias_norms = [self._normalize_search_text(alias) for alias in aliases]
            if self._normalize_search_text(row.get("name")) == query or query in alias_norms:
                found = dict(row)
                if not found.get("hp") or not found.get("image"):
                    wiki_target = self._fetch_damage_target_from_wiki(str(found.get("name") or name))
                    if wiki_target:
                        found.update({key: value for key, value in wiki_target.items() if value not in (None, "")})
                        self._damage_target_rows = self._merge_damage_target_rows(self._damage_target_rows, [found])
                return found
        for row in self._damage_target_rows:
            aliases = " ".join(str(alias) for alias in row.get("aliases", []) if alias) if isinstance(row.get("aliases"), list) else ""
            haystack = self._normalize_search_text(f"{row.get('name')} {row.get('detail')} {aliases}")
            if query and query in haystack:
                found = dict(row)
                if not found.get("hp") or not found.get("image"):
                    wiki_target = self._fetch_damage_target_from_wiki(str(found.get("name") or name))
                    if wiki_target:
                        found.update({key: value for key, value in wiki_target.items() if value not in (None, "")})
                        self._damage_target_rows = self._merge_damage_target_rows(self._damage_target_rows, [found])
                return found
        if query and query == self._normalize_search_text(self._wiki_name):
            return self._wiki_damage_target()
        if query:
            wiki_target = self._fetch_damage_target_from_wiki(name)
            if wiki_target:
                self._damage_target_rows = self._merge_damage_target_rows(self._damage_target_rows, [wiki_target])
                return wiki_target
        return {}

    def _fetch_damage_target_from_wiki(self, name: str) -> dict[str, Any]:
        title = clean_wiki_text(name)
        if not title:
            return {}
        candidates = [title]
        for suffix in (" Tank", " Vehicle"):
            if suffix.strip().casefold() not in title.casefold():
                candidates.append(f"{title}{suffix}")
        seen: set[str] = set()
        best: dict[str, Any] = {}
        for candidate in candidates:
            try:
                resolved = search_wiki_page_title(candidate) or candidate
                if self._normalize_search_text(resolved) in seen:
                    continue
                seen.add(self._normalize_search_text(resolved))
                item = fetch_wiki_item_info(resolved)
            except Exception:
                continue
            target = self._wiki_damage_target_from_item(item)
            if target.get("hp") or target.get("image"):
                return target
            if target and not best:
                best = target
        return best

    def _wiki_damage_target_from_item(self, item: dict[str, Any]) -> dict[str, Any]:
        fields = item.get("fields") if isinstance(item.get("fields"), list) else []
        values: dict[str, Any] = {}
        for field in fields:
            if not isinstance(field, dict):
                continue
            key = str(field.get("key") or normalize_wiki_key(str(field.get("label") or "")))
            values[key] = field.get("value")
        for key, value in item.items():
            if key not in values:
                values[str(key)] = value
        hp = self._damage_number(values.get("health") or values.get("hp") or values.get("hitpoints"))
        disable_threshold_text = clean_wiki_text(values.get("disable_threshold"))
        disable_threshold = self._damage_percent(disable_threshold_text)
        if hp is None and disable_threshold:
            below_match = re.search(r"below\s+(\d+(?:[.,]\d+)?)\s+health", disable_threshold_text, flags=re.I)
            if below_match:
                try:
                    hp = float(below_match.group(1).replace(",", ".")) / disable_threshold
                except ValueError:
                    hp = None
        resistance_type = clean_wiki_text(
            values.get("resistance")
            or values.get("resistance_type")
            or values.get("class")
            or values.get("category")
            or values.get("super_class")
        )
        name = clean_wiki_text(item.get("name"))
        detail_parts = [part for part in (resistance_type, f"{int(hp)} HP" if hp else "", "Wiki") if part]
        return {
            "name": name,
            "detail": " | ".join(detail_parts),
            "hp": hp,
            "disable_threshold": disable_threshold,
            "resistance_type": resistance_type,
            "category": "wiki",
            "source": "wiki",
            "image": str(item.get("image") or ""),
        }

    def _wiki_damage_target(self) -> dict[str, Any]:
        item = self._wiki_data if isinstance(self._wiki_data, dict) else {}
        target = self._wiki_damage_target_from_item(item) if item else {}
        if not target.get("name"):
            target["name"] = clean_wiki_text(self._wiki_name or self._selected_name or self._query)
        if not target.get("image"):
            target["image"] = self._wiki_image
        if not target.get("detail"):
            target["detail"] = "Wiki carregada" + (f" | {int(target.get('hp'))} HP" if target.get("hp") else "")
        return target

    def _current_damage_target(self) -> dict[str, Any]:
        name = clean_wiki_text(self._wiki_name or self._selected_name or self._query)
        static_target = self._find_damage_target(name)
        if static_target:
            return static_target
        return self._wiki_damage_target()

    def _damage_target_preview_rows(self) -> list[dict[str, str]]:
        target = self._current_damage_target()
        if not target.get("name"):
            return [{"label": "Alvo", "value": "Pesquise uma estrutura, veiculo ou navio na Wiki primeiro.", "kind": "warning"}]
        rows = [{"label": "Alvo", "value": str(target.get("name") or "-"), "kind": "info"}]
        hp = self._damage_number(target.get("hp"))
        rows.append({"label": "HP conhecido", "value": str(int(hp)) if hp else "Nao encontrado no JSON/Wiki", "kind": "warning" if not hp else "info"})
        if target.get("resistance_type"):
            rows.append({"label": "Resistencia/classe", "value": str(target.get("resistance_type")), "kind": "info"})
        return rows

    def _damage_multiplier(self, target: dict[str, Any], ammo: dict[str, Any]) -> tuple[float, list[str], bool]:
        damage_type = self._normalize_search_text(ammo.get("damage_type")).replace(" ", "_")
        resistance = self._normalize_search_text(target.get("resistance_type"))
        category = self._normalize_search_text(target.get("category"))
        notes: list[str] = []
        requires_penetration = False
        multiplier = 1.0
        if "large ship" in resistance and damage_type == "armour_piercing":
            multiplier = 0.6
            notes.append("Large Ship AP: aplicado multiplicador 0.6 do damege.json.")
        is_heavy_armour = "heavy armour" in resistance or ("heavy" in resistance and "tank" in resistance)
        if is_heavy_armour and damage_type == "explosive":
            multiplier = 0.85
            requires_penetration = True
            notes.append("Heavy Armour + Explosive: usando 15% de mitigacao do exemplo do JSON.")
        if any(token in resistance for token in ("armour", "armor", "tank")) and damage_type in {"explosive", "armour_piercing"}:
            requires_penetration = True
        if "structure" in category or "structure" in resistance or "bunker" in resistance:
            if damage_type in {"light_kinetic", "anti_tank_kinetic", "anti_tank_explosive", "shrapnel"}:
                multiplier = 0.0
                notes.append("O JSON marca esse tipo de dano como ineficiente/normalmente sem dano estrutural.")
            elif damage_type in {"explosive", "high_explosive"} and "tier 2" in resistance and "bunker" in resistance:
                multiplier = 0.35
                notes.append("Tier 2 Bunker: aplicado override 0.35 para explosive/high explosive.")
        return multiplier, notes, requires_penetration

    def _damage_estimate(self, target: dict[str, Any], ammo: dict[str, Any], penetration_percent: str = "") -> dict[str, Any]:
        hp = self._damage_number(target.get("hp"))
        raw_damage = self._damage_number(ammo.get("damage"))
        if hp is None or raw_damage is None:
            return {"ok": False, "hp": hp, "raw_damage": raw_damage, "notes": []}
        multiplier, notes, requires_penetration = self._damage_multiplier(target, ammo)
        effective = raw_damage * multiplier
        if effective <= 0:
            return {"ok": False, "hp": hp, "raw_damage": raw_damage, "effective": 0, "notes": notes}
        hits_destroy = math.ceil(hp / effective)
        threshold = self._damage_percent(target.get("disable_threshold"))
        hits_disable = math.ceil((hp * threshold) / effective) if threshold else None
        chance = self._damage_percent(penetration_percent)
        chance_source = "informada"
        if requires_penetration and chance is None:
            chance = self._default_penetration_chance(target, ammo)
            chance_source = "estimada"
        expected_destroy = math.ceil(hits_destroy / chance) if chance and requires_penetration else None
        expected_disable = math.ceil(hits_disable / chance) if chance and requires_penetration and hits_disable else None
        probability_destroy = self._binomial_at_least(expected_destroy, hits_destroy, chance) if expected_destroy and chance else None
        probability_disable = self._binomial_at_least(expected_disable, hits_disable, chance) if expected_disable and chance and hits_disable else None
        return {
            "ok": True,
            "hp": hp,
            "raw_damage": raw_damage,
            "effective": effective,
            "hits_destroy": hits_destroy,
            "hits_disable": hits_disable,
            "requires_penetration": requires_penetration,
            "penetration_chance": chance,
            "penetration_source": chance_source,
            "expected_destroy": expected_destroy,
            "expected_disable": expected_disable,
            "probability_destroy": probability_destroy,
            "probability_disable": probability_disable,
            "notes": notes,
        }

    @staticmethod
    def _default_penetration_chance(target: dict[str, Any], ammo: dict[str, Any]) -> float:
        resistance = ItemSearchController._normalize_search_text(target.get("resistance_type"))
        ammo_name = ItemSearchController._normalize_search_text(ammo.get("name"))
        ammo_type = ItemSearchController._normalize_search_text(ammo.get("damage_type"))
        if "super heavy" in resistance and "40mm" in ammo_name:
            return 0.22
        if "armour piercing" in ammo_type:
            return 0.35
        if "heavy" in resistance or "tank" in resistance:
            return 0.25
        return 0.30

    @staticmethod
    def _binomial_at_least(trials: int | None, successes: int | None, chance: float | None) -> float | None:
        if not trials or not successes or chance is None or chance <= 0:
            return None
        trials = min(int(trials), 240)
        successes = int(successes)
        if successes > trials:
            return 0.0
        try:
            probability = sum(
                math.comb(trials, hit) * (chance ** hit) * ((1 - chance) ** (trials - hit))
                for hit in range(successes, trials + 1)
            )
        except (OverflowError, ValueError):
            return None
        return max(0.0, min(1.0, probability))

    def _calculate_damage_rows(self, target: dict[str, Any], ammo: dict[str, Any], penetration_percent: str = "") -> list[dict[str, str]]:
        rows = self._damage_target_preview_rows()
        if not ammo:
            rows.append({"label": "Municao", "value": "Escolha uma municao do damege.json.", "kind": "warning"})
            return rows
        rows.append({"label": "Municao", "value": str(ammo.get("name") or "-"), "kind": "info"})
        estimate = self._damage_estimate(target, ammo, penetration_percent)
        if not estimate.get("ok"):
            if estimate.get("hp") is None:
                rows.append({"label": "Calculo", "value": "HP do alvo nao encontrado. Abra um item com Health na Wiki ou use um alvo presente no damege.json.", "kind": "warning"})
            elif estimate.get("raw_damage") is None:
                rows.append({"label": "Calculo", "value": "Dano da municao nao encontrado.", "kind": "warning"})
            else:
                rows.append({"label": "Dano efetivo", "value": "0 ou ineficiente contra esse alvo pelas regras do JSON.", "kind": "warning"})
            for note in estimate.get("notes", []):
                rows.append({"label": "Nota", "value": str(note), "kind": "note"})
            return rows
        rows.append({"label": "Dano bruto", "value": f"{estimate['raw_damage']:g}", "kind": "info"})
        rows.append({"label": "Dano efetivo", "value": f"{estimate['effective']:g}", "kind": "success"})
        if estimate.get("hits_disable"):
            rows.append({"label": "Acertos penetrantes para desabilitar", "value": str(estimate["hits_disable"]), "kind": "success"})
        rows.append({"label": "Acertos penetrantes para destruir", "value": str(estimate["hits_destroy"]), "kind": "success"})
        if estimate.get("requires_penetration"):
            chance = estimate.get("penetration_chance")
            if chance:
                source = "estimada" if estimate.get("penetration_source") == "estimada" else "informada"
                rows.append({"label": f"Chance por tiro ({source})", "value": f"{chance * 100:.0f}%", "kind": "warning"})
                if estimate.get("expected_disable"):
                    rows.append({"label": "Media para desabilitar", "value": f"{estimate['expected_disable']} tiros", "kind": "warning"})
                    if estimate.get("probability_disable") is not None:
                        rows.append({"label": "Chance nessa media", "value": f"{estimate['probability_disable'] * 100:.0f}% de desabilitar", "kind": "warning"})
                rows.append({"label": "Media para destruir", "value": f"{estimate['expected_destroy']} tiros", "kind": "warning"})
                if estimate.get("probability_destroy") is not None:
                    rows.append({"label": "Chance nessa media", "value": f"{estimate['probability_destroy'] * 100:.0f}% de destruir", "kind": "warning"})
            else:
                rows.append({"label": "Penetracao", "value": "Esse alvo pode dar bounce. Informe uma chance para estimar tiros reais.", "kind": "warning"})
        else:
            rows.append({"label": "Chance por tiro", "value": "100% se o acerto aplicar dano", "kind": "success"})
            rows.append({"label": "Media para destruir", "value": f"{estimate['hits_destroy']} acertos", "kind": "success"})
        for note in estimate.get("notes", []):
            rows.append({"label": "Nota", "value": str(note), "kind": "note"})
        return rows

    def _calculate_duel_rows(self, left: dict[str, Any], right: dict[str, Any], ammo: dict[str, Any], penetration_percent: str = "") -> list[dict[str, str]]:
        if not left or not right:
            return [{"label": "Duelo", "value": "Escolha os dois tanques para simular o duelo.", "kind": "warning"}]
        if not ammo:
            # No specific ammo → test ALL ammos
            return self._calculate_duel_all_ammos(left, right, penetration_percent)
        left_name = str(left.get("name") or "Tanque A")
        right_name = str(right.get("name") or "Tanque B")
        ammo_name = str(ammo.get("name") or "-")
        # A attacks B, B attacks A
        left_attack = self._damage_estimate(right, ammo, penetration_percent)
        right_attack = self._damage_estimate(left, ammo, penetration_percent)
        if not left_attack.get("ok") or not right_attack.get("ok"):
            rows: list[dict[str, str]] = [
                {"label": "Municao", "value": ammo_name, "kind": "info"},
                {"label": "Resultado", "value": "Faltam dados de HP ou dano para simular essa luta. Verifique se os dois alvos tem HP na Wiki ou no banco de dados.", "kind": "warning"},
            ]
            return rows
        left_score = left_attack.get("expected_destroy") or left_attack.get("hits_destroy")
        right_score = right_attack.get("expected_destroy") or right_attack.get("hits_destroy")
        left_hits = left_attack.get("hits_destroy")
        right_hits = right_attack.get("hits_destroy")
        chance = left_attack.get("penetration_chance") or right_attack.get("penetration_chance")
        pen_source = "estimada" if (
            left_attack.get("penetration_source") == "estimada" or right_attack.get("penetration_source") == "estimada"
        ) else "informada"
        # Determine winner
        if left_score < right_score:
            winner = left_name
            winner_kind = "success"
        elif right_score < left_score:
            winner = right_name
            winner_kind = "warning"
        else:
            winner = "Empate tecnico"
            winner_kind = "note"
        rows = [
            # --- Overview row ---
            {"label": "Municao simulada", "value": ammo_name, "kind": "info"},
            # --- Winner ---
            {"label": "Vencedor estimado", "value": winner, "kind": winner_kind},
            # --- A attacks B ---
            {
                "label": f"{left_name} destrói {right_name} em",
                "value": f"{left_score} tiros" + (f" ({left_hits} penetrantes)" if chance and left_hits != left_score else ""),
                "kind": "success",
            },
            # --- B attacks A ---
            {
                "label": f"{right_name} destrói {left_name} em",
                "value": f"{right_score} tiros" + (f" ({right_hits} penetrantes)" if chance and right_hits != right_score else ""),
                "kind": "warning",
            },
        ]
        if chance:
            rows.append({"label": f"Chance de penetração por tiro ({pen_source})", "value": f"{chance * 100:.0f}%", "kind": "info"})
        if left_attack.get("probability_destroy") is not None:
            rows.append({"label": f"Probabilidade de {left_name} vencer na média", "value": f"{left_attack['probability_destroy'] * 100:.0f}%", "kind": "success"})
        if right_attack.get("probability_destroy") is not None:
            rows.append({"label": f"Probabilidade de {right_name} vencer na média", "value": f"{right_attack['probability_destroy'] * 100:.0f}%", "kind": "warning"})
        # Disable info if applicable
        left_dis = left_attack.get("hits_disable")
        right_dis = right_attack.get("hits_disable")
        if left_dis:
            left_dis_shots = left_attack.get("expected_disable") or left_dis
            rows.append({"label": f"{left_name} desabilita {right_name} em", "value": f"{left_dis_shots} tiros", "kind": "success"})
        if right_dis:
            right_dis_shots = right_attack.get("expected_disable") or right_dis
            rows.append({"label": f"{right_name} desabilita {left_name} em", "value": f"{right_dis_shots} tiros", "kind": "warning"})
        rows.append({"label": "Nota", "value": "Estimativa por tiros médios necessários. Não considera cadência de fogo, distância, ângulo de impacto, reparo ou tripulação.", "kind": "note"})
        return rows

    def _calculate_duel_all_ammos(self, left: dict[str, Any], right: dict[str, Any], penetration_percent: str = "") -> list[dict[str, str]]:
        """Calculate duel results for ammo types the tanks can use, ranked by combined efficiency."""
        left_name = str(left.get("name") or "Tanque A")
        right_name = str(right.get("name") or "Tanque B")

        if not self._damage_ammo_rows:
            return [{"label": "Municao", "value": "Banco de munições vazio.", "kind": "warning"}]

        left_hp = self._damage_number(left.get("hp"))
        right_hp = self._damage_number(right.get("hp"))
        if left_hp is None or right_hp is None:
            return [
                {"label": "Dados insuficientes", "value": "HP de um ou ambos os tanques é desconhecido. Abra cada tanque na Wiki primeiro.", "kind": "warning"},
            ]

        # Filter ammo to tank-mounted calibres for tank-vs-tank duels.
        left_res  = self._normalize_search_text(left.get("resistance_type") or left.get("detail") or "")
        right_res = self._normalize_search_text(right.get("resistance_type") or right.get("detail") or "")
        combined_res = left_res + " " + right_res
        relevant_ammos = [a for a in self._damage_ammo_rows if self._ammo_relevant_for_tank_duel(a, combined_res)]

        if not relevant_ammos:
            relevant_ammos = self._damage_ammo_rows  # fallback: use all if filter returns nothing

        results: list[dict[str, Any]] = []
        for ammo in relevant_ammos:
            la = self._damage_estimate(right, ammo, penetration_percent)  # A attacks B
            ra = self._damage_estimate(left,  ammo, penetration_percent)  # B attacks A
            if not la.get("ok") or not ra.get("ok"):
                continue
            ls = la.get("expected_destroy") or la.get("hits_destroy") or 9999
            rs = ra.get("expected_destroy") or ra.get("hits_destroy") or 9999
            diff = rs - ls  # positive = A wins, negative = B wins
            results.append({
                "ammo": ammo,
                "left_attack": la,
                "right_attack": ra,
                "left_score": ls,
                "right_score": rs,
                "total_score": (self._damage_number(ls) or 9999) + (self._damage_number(rs) or 9999),
                "diff": diff,
            })

        if not results:
            return [{"label": "Sem resultados", "value": "Nenhuma munição relevante causa dano útil em ambos com os dados disponíveis.", "kind": "warning"}]

        results.sort(key=lambda r: -r["diff"])

        left_wins  = [r for r in results if r["diff"] > 0]
        right_wins = [r for r in results if r["diff"] < 0]
        ties       = [r for r in results if r["diff"] == 0]

        # Determine overall advantage by comparing total "diff" sum
        total_diff = sum(r["diff"] for r in results)
        if total_diff > 0:
            winner_name  = left_name
            loser_name   = right_name
            winner_wins  = len(left_wins)
            winner_kind  = "winner"
            loser_kind   = "loser"
        elif total_diff < 0:
            winner_name  = right_name
            loser_name   = left_name
            winner_wins  = len(right_wins)
            winner_kind  = "loser"
            loser_kind   = "winner"
        else:
            winner_name  = "Empate técnico"
            loser_name   = ""
            winner_wins  = len(ties)
            winner_kind  = "note"
            loser_kind   = "note"

        # Same criterion used by Auto: fastest combined duel.
        best = min(
            results,
            key=lambda r: (
                r.get("total_score") or 9999,
                -(self._damage_number(r["ammo"].get("damage")) or 0),
            ),
        )
        best_ammo_name = str(best["ammo"].get("name") or "-")
        best_ls = best["left_score"]
        best_rs = best["right_score"]

        rows: list[dict[str, str]] = [
            # Big winner announcement
            {"label": f"{len(results)} munições testadas • {winner_wins} favorecem o vencedor",
             "value": winner_name,
             "kind": winner_kind},
        ]

        rows.append({"label": "Municao auto", "value": best_ammo_name, "kind": "note"})

        rows.append({"label": f"{left_name} destrói {right_name} com {best_ammo_name}", "value": f"{best_ls} tiros", "kind": "success"})
        rows.append({"label": f"{right_name} destrói {left_name} com {best_ammo_name}", "value": f"{best_rs} tiros", "kind": "warning"})

        # Per-ammo ranking rows
        shown: set[str] = {best_ammo_name.lower()}
        for r in results:
            aname = str(r["ammo"].get("name") or "-")
            if aname.lower() in shown:
                continue
            shown.add(aname.lower())
            ls = r["left_score"]
            rs = r["right_score"]
            if r["diff"] > 0:
                kind = "success"
                summary = f"{left_name} • {ls} tiros vs {rs}"
            elif r["diff"] < 0:
                kind = "warning"
                summary = f"{right_name} • {rs} tiros vs {ls}"
            else:
                kind = "note"
                summary = f"Empate — {ls} tiros cada"
            rows.append({"label": aname, "value": summary, "kind": kind})
            if len(rows) >= 18:
                break

        rows.append({"label": "Nota", "value": "Baseado em HP banco/wiki + dano por munição. Não considera cadência, distância, ângulo, reparo ou tripulação.", "kind": "note"})
        return rows

    @classmethod
    def _ammo_relevant_for_tank_duel(cls, ammo: dict[str, Any], combined_resistance: str) -> bool:
        if not cls._ammo_relevant_for_vehicle(ammo, combined_resistance):
            return False
        text = cls._normalize_search_text(
            " ".join(
                str(value)
                for value in (
                    ammo.get("name"),
                    ammo.get("detail"),
                    ammo.get("damage_type"),
                )
                if value
            )
        )
        blocked = (
            "mine", "torpedo", "grenade", "flask", "sticky", "rpg", "rocket",
            "satchel", "charge", "havoc", "mammon", "tremola", "ignifist",
        )
        if any(token in text for token in blocked):
            return False
        tank_calibres = ("12 7mm", "14 5mm", "20mm", "30mm", "40mm", "68mm", "75mm", "94 5mm")
        return any(calibre in text for calibre in tank_calibres)

    @staticmethod
    def _ammo_relevant_for_vehicle(ammo: dict[str, Any], combined_resistance: str) -> bool:
        """Return True if this ammo is suitable for a vehicle-vs-vehicle duel."""
        uso = [ItemSearchController._normalize_search_text(u) for u in (ammo.get("uso") or [])]
        uso_text = " ".join(uso)
        damage_type = ItemSearchController._normalize_search_text(ammo.get("damage_type") or "")

        def has_usage(tags: tuple[str, ...]) -> bool:
            return any(ItemSearchController._normalize_search_text(tag) in uso_text for tag in tags)

        if has_usage(("anti-ship", "anti-large-ship")):
            is_ship = any(t in combined_resistance for t in ("ship", "naval", "submarine"))
            return is_ship

        # Exclude pure infantry / AA / sea mine / structure demolition ammos
        EXCLUDE_TAGS = (
            "anti-infantry", "anti-air", "area denial", "anti-aircraft",
            "sabotage", "structure demolition", "concrete cracking",
            "base destruction", "heavy pve", "sea mine", "infantry demolition",
            "area bleed",
        )
        if has_usage(EXCLUDE_TAGS):
            # Exception: if it also explicitly mentions anti-tank or anti-vehicle, keep it
            if not has_usage(("anti-tank", "anti-vehicle", "anti-armor", "anti-armour", "vehicle weapon", "light vehicle", "light vehicles", "heavy vehicle")):
                return False

        # Always include if tagged as vehicle / tank relevant
        INCLUDE_TAGS = (
            "anti-tank", "anti-vehicle", "anti-armor", "anti-armour",
            "vehicle weapon", "heavy vehicle", "light vehicle",
            "armour piercing", "anti-structure medio",
        )
        if has_usage(INCLUDE_TAGS):
            return True

        # Include standard calibre ammos (no uso or pve/artillery)
        CALIBRE_TYPES = ("explosive", "armour_piercing", "armour piercing", "high_explosive", "high explosive",
                         "anti_tank", "anti-tank", "anti_tank_explosive", "anti-tank explosive",
                         "anti_tank_kinetic", "anti-tank kinetic", "heavy kinetic")
        if damage_type in CALIBRE_TYPES or not uso:
            return True

        return False

    def _normalize_damage_faction(self, value: Any) -> str:
        faction = self._normalize_search_text(value)
        if "warden" in faction:
            return "warden"
        if "colonial" in faction:
            return "colonial"
        return ""

    def _damage_row_faction(self, row: dict[str, Any]) -> str:
        for value in (row.get("faction"), row.get("detail"), row.get("name"), row.get("resistance_type")):
            faction = self._normalize_damage_faction(value)
            if faction:
                return faction
        return ""

    def _damage_suggestions(self, rows: list[dict[str, Any]], query: str, limit: int = 10, faction: str = "") -> list[dict[str, str]]:
        query_norm = self._normalize_search_text(query)
        faction_norm = self._normalize_damage_faction(faction)
        scored: list[tuple[int, dict[str, Any]]] = []
        for row in rows:
            row_faction = self._damage_row_faction(row)
            if faction_norm and row_faction and row_faction != faction_norm:
                continue
            name_norm = self._normalize_search_text(row.get("name"))
            detail_norm = self._normalize_search_text(row.get("detail"))
            aliases_norm = self._normalize_search_text(" ".join(str(alias) for alias in row.get("aliases", []) if alias)) if isinstance(row.get("aliases"), list) else ""
            score = 0
            if not query_norm:
                score = 10
            elif name_norm == query_norm:
                score = 100
            elif query_norm and query_norm in aliases_norm:
                score = 90
            elif name_norm.startswith(query_norm):
                score = 82
            elif query_norm in name_norm:
                score = 62
            elif query_norm in detail_norm:
                score = 45
            if faction_norm and row_faction == faction_norm:
                score += 8
            if score:
                scored.append((score, row))
        scored.sort(key=lambda item: (-item[0], str(item[1].get("name") or "").lower()))
        return [{"name": str(row.get("name") or ""), "detail": str(row.get("detail") or ""), "faction": self._damage_row_faction(row)} for _score, row in scored[:limit]]

    def _update_damage_ammo_suggestions(self, query: str) -> None:
        self.damage_ammo_suggestions.set_items(self._damage_suggestions(self._damage_ammo_rows, query))

    def _update_damage_duel_suggestions(self, query: str, side: str, faction: str = "") -> None:
        tank_rows = [row for row in self._damage_target_rows if self._damage_preset_candidate(row)]
        rows = self._damage_suggestions(tank_rows, query, faction=faction)
        if len(rows) < 6 and len(clean_wiki_text(query)) >= 3:
            seen = {self._normalize_search_text(row.get("name")) for row in rows}
            faction_norm = self._normalize_damage_faction(faction)
            try:
                titles = search_wiki_page_titles(query, 8)
            except Exception:
                titles = []
            for title in titles:
                key = self._normalize_search_text(title)
                if not key or key in seen:
                    continue
                wiki_row = {"name": title, "detail": "Wiki | HP e imagem resolvidos ao calcular"}
                if not self._damage_preset_candidate(wiki_row):
                    continue
                wiki_faction = self._damage_row_faction(wiki_row)
                if faction_norm and wiki_faction and wiki_faction != faction_norm:
                    continue
                rows.append({"name": title, "detail": "Wiki | HP e imagem resolvidos ao calcular", "faction": wiki_faction})
                seen.add(key)
                if len(rows) >= 8:
                    break
        if str(side).lower() == "right":
            self.damage_duel_right_suggestions.set_items(rows)
        else:
            self.damage_duel_left_suggestions.set_items(rows)

    def _item_names(self) -> list[str]:
        return self._cached_item_names

    @staticmethod
    def _row_quantity(item: dict[str, Any]) -> int:
        try:
            return int(item.get("quantity", 0) or 0)
        except (TypeError, ValueError):
            return 0

    @classmethod
    def _is_searchable_stockpile_item(cls, item: dict[str, Any]) -> bool:
        if cls._row_quantity(item) <= 0:
            return False
        return StockpileController._has_gg_stockpile_prefix(
            {
                "name": item.get("warehouse"),
                "warehouse_name": item.get("warehouse_name"),
                "stockpile_name": item.get("stockpile_name"),
                "neme": item.get("neme"),
            }
        )

    @staticmethod
    def _normalize_search_text(value: Any) -> str:
        text = str(value or "").casefold()
        text = "".join(char for char in unicodedata.normalize("NFKD", text) if not unicodedata.combining(char))
        return re.sub(r"[^a-z0-9]+", " ", text).strip()

    @staticmethod
    def _load_slang_terms() -> list[dict[str, Any]]:
        def aliases_from_name(name: str) -> list[str]:
            words = re.findall(r"[A-Za-z0-9]+", name)
            aliases: list[str] = []
            if 2 <= len(words) <= 5:
                acronym = "".join(word[0] for word in words if word and word[0].isalnum()).upper()
                if len(acronym) >= 2:
                    aliases.append(acronym)
            compact = re.sub(r"[^A-Za-z0-9]+", "", name)
            if compact and compact != name and len(compact) <= 24:
                aliases.append(compact)
            return aliases

        def add_term(
            terms: list[dict[str, Any]],
            name: str,
            aliases: list[Any] | None = None,
            category: str = "",
            kind: str = "",
            faction: str = "",
            source: str = "slang",
        ) -> None:
            clean_name = str(name or "").strip()
            clean_aliases = [str(alias).strip() for alias in (aliases or []) if str(alias or "").strip()]
            if clean_name:
                clean_aliases.extend(aliases_from_name(clean_name))
            unique_aliases = list(dict.fromkeys(alias for alias in clean_aliases if alias and alias != clean_name))
            if not clean_name and not unique_aliases:
                return
            terms.append(
                {
                    "index": len(terms),
                    "name": clean_name,
                    "aliases": unique_aliases,
                    "category": str(category or "").strip(),
                    "kind": str(kind or "").strip(),
                    "faction": str(faction or "").strip(),
                    "source": source,
                }
            )

        terms: list[dict[str, Any]] = []
        path = BASE_DIR / "data" / "slang_terms.json"
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            data = {}
        raw_terms = data.get("slang_terms", []) if isinstance(data, dict) else []
        for item in raw_terms:
            if not isinstance(item, dict):
                continue
            add_term(
                terms,
                str(item.get("nome") or "").strip(),
                item.get("apelidos", []) if isinstance(item.get("apelidos"), list) else [],
                str(item.get("categoria") or "").strip(),
                str(item.get("tipo") or "").strip(),
                str(item.get("faccao") or "").strip(),
                "slang",
            )

        structure_path = BASE_DIR / "data" / "siglestrutrure.json"
        try:
            structure_data = json.loads(structure_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            structure_data = {}

        def add_structure_value(value: Any, category: str) -> None:
            if isinstance(value, str):
                add_term(terms, value, [], category, "estrutura", "", "structure")
                return
            if not isinstance(value, dict):
                return
            name = str(value.get("name") or value.get("nome") or value.get("nome_oficial") or "").strip()
            aliases = value.get("aliases", [])
            if not isinstance(aliases, list):
                aliases = []
            aliases = list(aliases)
            for key in ("sigla_principal", "nome_pt_comunidade", "classe", "type"):
                alias = value.get(key)
                if alias:
                    aliases.append(alias)
            add_term(
                terms,
                name,
                aliases,
                category,
                str(value.get("type") or value.get("classe") or "estrutura").strip(),
                str(value.get("faction") or "").strip(),
                "structure",
            )

        if isinstance(structure_data, dict):
            structures = structure_data.get("estruturas_quebraveis")
            if isinstance(structures, dict):
                for category, values in structures.items():
                    if isinstance(values, list):
                        for value in values:
                            add_structure_value(value, str(category))
            ships = structure_data.get("navios_grande_porte")
            if isinstance(ships, list):
                for value in ships:
                    add_structure_value(value, "navios_grande_porte")
            naval_acronyms = structure_data.get("siglas_navais_resumo")
            if isinstance(naval_acronyms, dict):
                for acronym, description in naval_acronyms.items():
                    parts = [part.strip() for part in re.split(r"/|\bou\b", str(description or "")) if part.strip()]
                    if not parts:
                        continue
                    name = parts[-1]
                    aliases = [acronym, *parts[:-1]]
                    add_term(terms, name, aliases, "siglas_navais_resumo", "abreviacao", "", "structure")

        unique_terms: list[dict[str, Any]] = []
        seen_terms: set[tuple[str, tuple[str, ...], str]] = set()
        for term in terms:
            normalized_name = str(term.get("name") or "").casefold()
            normalized_aliases = tuple(str(alias).casefold() for alias in term.get("aliases", []))
            key = (
                normalized_name,
                normalized_aliases,
                str(term.get("source") or ""),
            )
            if key in seen_terms or (not normalized_name and not normalized_aliases):
                continue
            term["index"] = len(unique_terms)
            unique_terms.append(term)
            seen_terms.add(key)
        return unique_terms

    def _resolve_slang_names(self, term: dict[str, Any]) -> list[str]:
        term_index = int(term.get("index", -1))
        if term_index in self._slang_resolved_names:
            return self._slang_resolved_names[term_index]

        target_norm = self._normalize_search_text(term.get("name"))
        alias_norms = [self._normalize_search_text(alias) for alias in term.get("aliases", [])]
        target_tokens = set(target_norm.split())
        resolved: list[str] = []
        for name, norm in self._name_norm_by_name.items():
            if not norm:
                continue
            if target_norm and (norm == target_norm or target_norm in norm or norm in target_norm):
                resolved.append(name)
                continue
            if target_tokens and len(target_tokens) <= 4 and target_tokens.issubset(set(norm.split())):
                resolved.append(name)
                continue
            if any(alias_norm and (alias_norm == norm or f" {alias_norm} " in f" {norm} ") for alias_norm in alias_norms):
                resolved.append(name)

        unique = sorted(dict.fromkeys(resolved), key=str.lower)
        self._slang_resolved_names[term_index] = unique[:16]
        return self._slang_resolved_names[term_index]

    def _slang_matches_for_query(self, query_norm: str) -> list[dict[str, Any]]:
        if not query_norm:
            return []
        scored: list[tuple[int, dict[str, Any]]] = []
        for term in self._slang_terms:
            name_norm = self._normalize_search_text(term.get("name"))
            alias_norms = [self._normalize_search_text(alias) for alias in term.get("aliases", [])]
            score = 0
            if any(alias == query_norm for alias in alias_norms):
                score = 100
            elif name_norm == query_norm:
                score = 95
            elif any(alias.startswith(query_norm) for alias in alias_norms):
                score = 82
            elif name_norm.startswith(query_norm):
                score = 76
            elif len(query_norm) >= 3 and any(query_norm in alias for alias in alias_norms):
                score = 62
            elif len(query_norm) >= 3 and query_norm in name_norm:
                score = 55
            if score:
                scored.append((score, term))
        scored.sort(key=lambda item: (-item[0], str(item[1].get("name") or "").lower()))
        return [term for _score, term in scored[:12]]

    def _suggestions_for_query(self, query: str) -> list[dict[str, str]]:
        query_norm = self._normalize_search_text(query)
        if not query_norm:
            return []
        names = self._item_names()
        starts = [name for name in names if self._name_norm_by_name.get(name, "").startswith(query_norm)]
        contains = [name for name in names if query_norm in self._name_norm_by_name.get(name, "") and name not in starts]

        rows: list[dict[str, str]] = [
            {"name": name, "alias": "", "detail": "", "source": "item"}
            for name in (starts + contains)
        ]

        seen = {row["name"] for row in rows}
        for term in self._slang_matches_for_query(query_norm):
            alias = next(
                (
                    str(alias)
                    for alias in term.get("aliases", [])
                    if query_norm in self._normalize_search_text(alias)
                ),
                str((term.get("aliases") or [""])[0] or ""),
            )
            detail_parts = [
                part
                for part in (
                    alias,
                    str(term.get("name") or ""),
                    str(term.get("kind") or ""),
                    str(term.get("category") or ""),
                    str(term.get("faction") or ""),
                )
                if part
            ]
            resolved_names = self._resolve_slang_names(term)
            names_to_show = resolved_names or ([str(term.get("name") or "").strip()] if str(term.get("name") or "").strip() else [])
            for name in names_to_show:
                if name in seen:
                    continue
                rows.append(
                    {
                        "name": name,
                        "alias": alias,
                        "detail": " -> ".join(detail_parts[:4]),
                        "source": str(term.get("source") or "slang"),
                    }
                )
                seen.add(name)
                if len(rows) >= 10:
                    return rows

        return rows[:10]

    def _rows_for_name(self, name: str) -> list[dict[str, Any]]:
        target = self._normalize_search_text(name)
        return [item for item in self._all_rows if self._normalize_search_text(item.get("display_name")) == target]

    def _matching_rows(self) -> list[dict[str, Any]]:
        query_norm = self._normalize_search_text(self._query)
        if not query_norm:
            return self._all_rows
        exact = [item for item in self._all_rows if self._normalize_search_text(item.get("display_name")) == query_norm]
        if exact:
            return exact
        suggestions = self._suggestions_for_query(self._query)
        if suggestions:
            selected = suggestions[0].get("name", "")
            selected_rows = self._rows_for_name(selected)
            if selected_rows:
                return selected_rows

        slang_rows: list[dict[str, Any]] = []
        for term in self._slang_matches_for_query(query_norm):
            for name in self._resolve_slang_names(term):
                slang_rows.extend(self._rows_for_name(name))
        if slang_rows:
            return slang_rows

        return [item for item in self._all_rows if query_norm in self._normalize_search_text(item.get("display_name"))]

    @staticmethod
    def _split_location(warehouse: str) -> tuple[str, str, str]:
        parts = [part.strip() for part in str(warehouse or "-").split("/") if part.strip()]
        if len(parts) >= 3:
            return parts[0], parts[-2], parts[-1]
        if len(parts) == 2:
            return parts[0], parts[1], parts[1]
        value = parts[0] if parts else "-"
        return value, value, value

    @staticmethod
    def _location_meta_for_row(item: dict[str, Any]) -> dict[str, str]:
        return StockpileController._warehouse_meta(
            {
                "name": item.get("warehouse"),
                "map_name": item.get("map_name"),
                "town": item.get("town"),
                "warehouse_name": item.get("warehouse_name"),
            }
        )

    def _update_search_models(self) -> None:
        suggestions = self._suggestions_for_query(self._query)
        self.suggestions.set_items(suggestions)
        self._best_match = suggestions[0].get("name", "") if suggestions else ""

        rows = self._matching_rows()
        if not self._query.strip():
            self._selected_name = ""
            self._total = sum(max(0, int(item.get("quantity", 0) or 0)) for item in rows)
            self._status_key = "item_search.loaded" if self._loaded else "item_search.loading"
            self._status_count = len(self._all_rows)
        elif rows:
            self._selected_name = str(rows[0].get("display_name") or self._query)
            self._total = sum(max(0, int(item.get("quantity", 0) or 0)) for item in rows)
            self._status_key = "item_search.best_match" if self._best_match else "item_search.loaded"
        else:
            self._selected_name = self._query
            self._total = 0
            self._status_key = "item_search.best_match_empty"

        grouped: dict[str, list[tuple[dict[str, Any], dict[str, str]]]] = {}
        for item in rows:
            meta = self._location_meta_for_row(item)
            fallback_region, _name, _code = self._split_location(str(item.get("warehouse") or "-"))
            region = str(meta.get("groupLabel") or meta.get("mapName") or meta.get("region") or fallback_region)
            grouped.setdefault(region, []).append((item, meta))

        result_rows: list[dict[str, Any]] = []
        translator = Translator(selected_language(self.settings))
        for region in sorted(grouped):
            region_rows = sorted(
                grouped[region],
                key=lambda entry: (
                    str(entry[1].get("town") or "").lower(),
                    str(entry[1].get("code") or "").lower(),
                    str(entry[0].get("warehouse") or "").lower(),
                ),
            )
            region_total = sum(max(0, int(item.get("quantity", 0) or 0)) for item, _meta in region_rows)
            result_rows.append(
                {
                    "rowType": "region",
                    "region": region,
                    "code": "",
                    "warehouse": "",
                    "place": "",
                    "quantity": 0,
                    "updatedAt": "",
                    "updatedAgo": "",
                    "icon": "",
                    "total": region_total,
                }
            )
            for item, meta in region_rows:
                _region, _name, fallback_code = self._split_location(str(item.get("warehouse") or "-"))
                code = str(meta.get("code") or fallback_code or "-")
                place = str(meta.get("placePath") or item.get("warehouse") or "-")
                updated_raw = str(item.get("warehouse_last_update") or "-")
                icon_path = str(item.get("icon_path") or "")
                result_rows.append(
                    {
                        "rowType": "item",
                        "region": region,
                        "code": code,
                        "warehouse": str(item.get("warehouse") or "-"),
                        "place": place,
                        "quantity": max(0, int(item.get("quantity", 0) or 0)),
                        "updatedAt": format_to_local_pc_time(updated_raw),
                        "updatedAgo": format_relative_time(updated_raw, translator),
                        "icon": file_url(icon_path) if icon_path and Path(icon_path).exists() else "",
                        "total": 0,
                    }
                )
        self.items.set_items(result_rows)
        self._schedule_wiki_lookup()
