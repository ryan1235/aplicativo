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

class AutoClickerController(QObject):
    changed = Signal()
    statusFromWorker = Signal(str)
    menuRequested = Signal()
    orderRequested = Signal(str)
    DEFAULT_INTERVAL = 0.05
    LEGACY_DEFAULT_INTERVAL = 0.5
    MODE_KEYS = ("auto", "move", "pilot", "right_hold", "fixed", "artillery")

    def __init__(self, settings: dict[str, Any], parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.settings = settings
        self._status = "Auto Clicker initializing..."
        self._available = True
        self._activity_logger: ActivityLogger | None = None
        self.slots = DictListModel(["slotNumber", "slotX", "slotY"], self)
        self.orders = DictListModel(["name"], self)
        self.statusFromWorker.connect(self._set_status)
        self.menuRequested.connect(self._start_default_order)
        try:
            self.clicker = AutoClicker(lambda text: self.statusFromWorker.emit(str(text)))
            self.clicker.set_menu_callback(lambda: self.menuRequested.emit())
            # Propaga idioma atual do I18nController para o AutoClicker
            try:
                parent_i18n = parent.i18nController if parent is not None and hasattr(parent, "i18nController") else None
                # guarda referência para expor disponibilidade do toggle FR
                self._parent_i18n = parent_i18n
                if parent_i18n is not None:
                    # set initial language and subscribe to changes
                    self.clicker.set_language(parent_i18n.language)
                    self.changed.emit()

                    def _on_i18n_changed() -> None:
                        try:
                            self.clicker.set_language(parent_i18n.language)
                        finally:
                            self.changed.emit()

                    parent_i18n.changed.connect(_on_i18n_changed)
            except Exception:
                pass
            self._apply_settings()
        except Exception as exc:
            self.clicker = None
            self._available = False
            self._status = f"Auto Clicker unavailable: {exc}"
        self._refresh_models()
        self.changed.emit()


    def setActivityLogger(self, logger: ActivityLogger | None) -> None:
        self._activity_logger = logger

    def _log_activity(
        self,
        action: str,
        *,
        subcategory: str,
        quantity: int = 1,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        if not callable(self._activity_logger):
            return
        self._activity_logger("autoclique", action, quantity, metadata or {}, subcategory)

    def _log_mode_toggle(self, mode: str, enabled: bool, metadata: dict[str, Any] | None = None) -> None:
        details = {
            "mode": mode,
            "enabled": enabled,
            "status": self._status,
            "target": self.targetTitle,
        }
        if metadata:
            details.update(metadata)
        self._log_activity("ativar_modo" if enabled else "desativar_modo", subcategory=mode, metadata=details)

    def _clicker_settings(self) -> dict[str, Any]:
        return self.settings.setdefault("auto_clicker", {})

    def _orders_from_settings(self) -> list[str]:
        orders = [str(item).strip() for item in self._clicker_settings().get("f5_orders", []) if str(item).strip()]
        return orders or ["Diesel", "Cmats", "Bmats", "Emats"]

    def _click_interval(self) -> float:
        data = self._clicker_settings()
        try:
            value = float(data.get("interval", self.DEFAULT_INTERVAL))
        except (TypeError, ValueError):
            value = self.DEFAULT_INTERVAL
        if abs(value - self.LEGACY_DEFAULT_INTERVAL) < 0.0001:
            value = self.DEFAULT_INTERVAL
        value = round(max(0.03, min(5.0, value)), 2)
        data["interval"] = value
        return value

    def _mode_enabled_settings(self) -> dict[str, bool]:
        data = self._clicker_settings()
        raw = data.get("modes_enabled", {})
        raw = raw if isinstance(raw, dict) else {}
        modes = {key: bool(raw.get(key, True)) for key in self.MODE_KEYS}
        data["modes_enabled"] = modes
        return modes

    def _mode_enabled(self, key: str) -> bool:
        return bool(self._mode_enabled_settings().get(key, True))

    def _refresh_models(self) -> None:
        data = self._clicker_settings()
        self.slots.set_items(
            [
                {
                    "slotNumber": slot,
                    "slotX": int(data.get(f"slot_{slot}_x", 0) or 0),
                    "slotY": int(data.get(f"slot_{slot}_y", 0) or 0),
                }
                for slot in (1, 2, 3, 4)
            ]
        )
        self.orders.set_items([{"name": name} for name in self._orders_from_settings()])

    def _apply_settings(self) -> None:
        if not self.clicker:
            return
        data = self._clicker_settings()
        self.clicker.configure(
            str(data.get("hotkey", "F3")),
            str(data.get("mouse_button", "Esquerdo")),
            self._click_interval(),
        )
        self.clicker.configure_modes_enabled(self._mode_enabled_settings())
        self.clicker.configure_action_hotkeys(
            str(data.get("move_hotkey", "F2")),
            str(data.get("fixed_hotkey", "F6")),
            str(data.get("pilot_hotkey", "F4")),
            str(data.get("artillery_hotkey", "F7")),
            str(data.get("right_hold_hotkey", "F9")),
        )
        self.clicker.shift_enabled = bool(data.get("shift_enabled", False))
        self.clicker.w_doubletap_enabled = bool(data.get("w_doubletap_enabled", False))
        self.clicker.right_doubletap_enabled = bool(data.get("right_doubletap_enabled", False))
        self.clicker.set_slot_positions(
            {
                slot: (
                    int(data.get(f"slot_{slot}_x", 0)),
                    int(data.get(f"slot_{slot}_y", 0)),
                )
                for slot in (1, 2, 3, 4)
            }
        )
        self._status = self.clicker.status_text()
        # Aplica override para manter W mesmo em FR (toggle disponível apenas para idioma FR)
        try:
            self.clicker.force_w_in_fr = bool(data.get("force_w_in_fr", False))
        except Exception:
            pass

    @Slot(str)
    def _set_status(self, text: str) -> None:
        self._status = text
        debug_log("autoclicker", "status", {"text": text})
        self.changed.emit()

    @Property(bool, notify=changed)
    def available(self) -> bool:
        return self._available

    @Property(str, notify=changed)
    def status(self) -> str:
        return self._status

    @Property(bool, notify=changed)
    def running(self) -> bool:
        return bool(self.clicker and self.clicker.enabled)

    def _pilot_active(self) -> bool:
        if not self.clicker:
            return False
        return bool(getattr(self.clicker, "w_hold_enabled", False))

    @Property(bool, notify=changed)
    def active(self) -> bool:
        return bool(
            self.clicker
            and (
                bool(getattr(self.clicker, "enabled", False))
                or bool(getattr(self.clicker, "fixed_click_enabled", False))
                or bool(getattr(self.clicker, "move_click_enabled", False))
                or bool(getattr(self.clicker, "artillery_enabled", False))
                or bool(getattr(self.clicker, "right_hold_enabled", False))
                or self._pilot_active()
            )
        )

    @Property(bool, notify=changed)
    def fixedRunning(self) -> bool:
        return bool(self.clicker and self.clicker.fixed_click_enabled)

    @Property(bool, notify=changed)
    def moveRunning(self) -> bool:
        return bool(self.clicker and self.clicker.move_click_enabled)

    @Property(bool, notify=changed)
    def pilotRunning(self) -> bool:
        return self._pilot_active()

    @Property(bool, notify=changed)
    def artilleryRunning(self) -> bool:
        return bool(self.clicker and getattr(self.clicker, "artillery_enabled", False))

    @Property(bool, notify=changed)
    def rightHoldRunning(self) -> bool:
        return bool(self.clicker and getattr(self.clicker, "right_hold_enabled", False))

    @Property(bool, notify=changed)
    def wHoldRunning(self) -> bool:
        return self._pilot_active()

    @Property(bool, notify=changed)
    def wHoldPaused(self) -> bool:
        return bool(self.clicker and getattr(self.clicker, "pilot_w_paused", False))

    @Property(bool, notify=changed)
    def shiftPressed(self) -> bool:
        return bool(self.clicker and getattr(self.clicker, "shift_pressed", False))

    @Property(str, notify=changed)
    def hotkey(self) -> str:
        return str(self._clicker_settings().get("hotkey", "F3"))

    @Property(str, notify=changed)
    def moveHotkey(self) -> str:
        return str(self._clicker_settings().get("move_hotkey", "F2"))

    @Property(str, notify=changed)
    def fixedHotkey(self) -> str:
        return str(self._clicker_settings().get("fixed_hotkey", "F6"))

    @Property(str, notify=changed)
    def pilotHotkey(self) -> str:
        return str(self._clicker_settings().get("pilot_hotkey", "F4"))

    @Property(str, notify=changed)
    def artilleryHotkey(self) -> str:
        return str(self._clicker_settings().get("artillery_hotkey", "F7"))

    @Property(str, notify=changed)
    def rightHoldHotkey(self) -> str:
        return str(self._clicker_settings().get("right_hold_hotkey", "F9"))

    @Property(str, notify=changed)
    def mouseButton(self) -> str:
        return str(self._clicker_settings().get("mouse_button", "Esquerdo"))

    @Property(float, notify=changed)
    def interval(self) -> float:
        return self._click_interval()

    @Property(bool, notify=changed)
    def autoModeEnabled(self) -> bool:
        return self._mode_enabled("auto")

    @Property(bool, notify=changed)
    def moveModeEnabled(self) -> bool:
        return self._mode_enabled("move")

    @Property(bool, notify=changed)
    def pilotModeEnabled(self) -> bool:
        return self._mode_enabled("pilot")

    @Property(bool, notify=changed)
    def rightHoldModeEnabled(self) -> bool:
        return self._mode_enabled("right_hold")

    @Property(bool, notify=changed)
    def fixedModeEnabled(self) -> bool:
        return self._mode_enabled("fixed")

    @Property(bool, notify=changed)
    def artilleryModeEnabled(self) -> bool:
        return self._mode_enabled("artillery")

    @Property(bool, notify=changed)
    def allModesEnabled(self) -> bool:
        return all(self._mode_enabled(key) for key in self.MODE_KEYS)

    @Property(str, notify=changed)
    def targetTitle(self) -> str:
        return str(self.clicker.target_title if self.clicker and self.clicker.target_title else "Foxhole")

    @Property(int, notify=changed)
    def clickCount(self) -> int:
        return int(self.clicker.click_count if self.clicker else 0)

    @Property(str, notify=changed)
    def modeSummary(self) -> str:
        if not self.clicker:
            return "-"
        items: list[str] = []
        if self.clicker.enabled:
            items.append(f"AUTO {self.hotkey} ({self.interval:.2f}s)")
        if self.clicker.move_click_enabled:
            items.append(f"LEFT HOLD {self.moveHotkey}")
        if self.clicker.fixed_click_enabled:
            items.append(f"FIXED {self.fixedHotkey}")
            items.append("SLOTS 1-4")
        if self.clicker.artillery_enabled:
            items.append(f"ART {self.artilleryHotkey}")
        if self.clicker.right_hold_enabled:
            items.append(f"RMB HOLD {self.rightHoldHotkey}")
        if self._pilot_active():
            suffix = " PAUSADO" if getattr(self.clicker, "pilot_w_paused", False) else ""
            wlabel = getattr(self.clicker, "w_hold_label", lambda: "W")()
            items.append(f"{wlabel} HOLD {self.pilotHotkey}{suffix}")
        if self.clicker.shift_enabled:
            items.append("SHIFT ON" if self.clicker.shift_pressed else "SHIFT READY")
        return " | ".join(items) if items else "-"

    @Property(str, notify=changed)
    def overlayPrimaryText(self) -> str:
        if not self.clicker:
            return "Auto Clicker indisponivel"
        if getattr(self.clicker, "w_hold_enabled", False):
            wlabel = getattr(self.clicker, "w_hold_label", lambda: "W")()
            return f"{wlabel} Hold {self.pilotHotkey}: {'pausado no S' if getattr(self.clicker, 'pilot_w_paused', False) else f'segurando {wlabel}'}"
        if getattr(self.clicker, "right_hold_enabled", False):
            return f"Right Hold {self.rightHoldHotkey}: segurando direito"
        if getattr(self.clicker, "artillery_enabled", False):
            return f"Artilharia {self.artilleryHotkey}: R + clique"
        if getattr(self.clicker, "move_click_enabled", False):
            return f"Left Hold {self.moveHotkey}: segurando esquerdo"
        if getattr(self.clicker, "fixed_click_enabled", False):
            return f"Fixo {self.fixedHotkey}: clique + slots 1-4"
        if getattr(self.clicker, "enabled", False):
            shift = " + Shift" if getattr(self.clicker, "shift_pressed", False) else ""
            return f"Auto {self.hotkey}: {self.mouseButton} | {self.interval:.2f}s{shift}"
        # Use dynamic W/Z label (respecting FR override)
        wlabel = getattr(self.clicker, "w_hold_label", lambda: "W")()
        return f"{self.hotkey} auto | {self.pilotHotkey} {wlabel} | {self.rightHoldHotkey} direito"

    @Property(str, notify=changed)
    def wHoldLabel(self) -> str:
        """Rótulo dinâmico para o W-Hold (ex.: 'W Hold:' ou 'Z Hold:')."""
        if not self.clicker:
            return "W Hold:"
        wlabel = getattr(self.clicker, "w_hold_label", lambda: "W")()
        return f"{wlabel} Hold:"

    @Property(str, notify=changed)
    def wHoldLetter(self) -> str:
        """Retorna apenas a letra usada para W-hold ('W' ou 'Z')."""
        if not self.clicker:
            return "W"
        try:
            return getattr(self.clicker, "w_hold_label", lambda: "W")()
        except Exception:
            return "W"

    @Property(bool, notify=changed)
    def frWOverrideAvailable(self) -> bool:
        """Disponibilidade do toggle: somente quando o idioma normalizado for 'fr'."""
        try:
            if getattr(self, "_parent_i18n", None) is None:
                return False
            code = normalize_language(self._parent_i18n.language)
            return code == "fr"
        except Exception:
            return False

    @Property(bool, notify=changed)
    def frWOverride(self) -> bool:
        """Estado atual do override (forcar W mesmo em FR)."""
        if not self.clicker:
            return False
        return bool(getattr(self.clicker, "force_w_in_fr", False))

    @Slot(bool)
    def setFrWOverride(self, value: bool) -> None:
        """Ativa/desativa o override e persiste a configuração; re-aplica idioma."""
        if not self.clicker:
            return
        self.clicker.force_w_in_fr = bool(value)
        # persiste a config
        try:
            self._clicker_settings()["force_w_in_fr"] = bool(value)
            save_settings(self.settings)
        except Exception:
            pass
        # re-aplica idioma atual para forçar recalculo da tecla usada
        try:
            if getattr(self, "_parent_i18n", None) is not None:
                self.clicker.set_language(self._parent_i18n.language)
        except Exception:
            pass
        self.changed.emit()

    @Property(str, notify=changed)
    def overlayHintText(self) -> str:
        if not self.clicker:
            return ""
        if getattr(self.clicker, "w_hold_enabled", False):
            return f"S pausa | Esc ou {self.pilotHotkey} para parar"
        if getattr(self.clicker, "right_hold_enabled", False):
            return f"Esc ou {self.rightHoldHotkey} para soltar"
        if getattr(self.clicker, "artillery_enabled", False):
            return f"{self.artilleryHotkey} ou clique esquerdo para parar"
        if getattr(self.clicker, "move_click_enabled", False):
            return f"Esc ou {self.moveHotkey} para soltar"
        if getattr(self.clicker, "fixed_click_enabled", False):
            return "1-4 clicam slots | mouse/asd cancela"
        if getattr(self.clicker, "enabled", False) and getattr(self.clicker, "shift_enabled", False):
            return "Shift entra somente enquanto voce segura"
        return ""

    @Property(QObject, constant=True)
    def slotModel(self) -> QObject:
        return self.slots

    @Property(QObject, constant=True)
    def orderModel(self) -> QObject:
        return self.orders

    @Property("QStringList", constant=True)
    def hotkeys(self) -> list[str]:
        return list(ACTION_KEYS.keys())

    @Property("QStringList", constant=True)
    def mouseButtons(self) -> list[str]:
        return list(MOUSE_BUTTONS.keys())

    @Slot(str, result=str)
    def mouseButtonLabel(self, value: str) -> str:
        return {
            "Esquerdo": "clicker.mouse_left",
            "Direito": "clicker.mouse_right",
            "Meio": "clicker.mouse_middle",
        }.get(value, "clicker.mouse_left")

    @Slot(result=str)
    def shortcutsText(self) -> str:
        return "\n".join(
            [
                f"{self.hotkey}: default Auto Clicker toggle",
                f"{self.moveHotkey}: Left Hold",
                f"{self.fixedHotkey}: fixed double-click and slots 1-4",
                f"{self.pilotHotkey}: pilot sequence",
                f"{self.rightHoldHotkey}: right mouse hold",
                f"{self.artilleryHotkey}: artillery sequence",
                "F5: orders and stock menu",
            ]
        )

    @Slot()
    def toggle(self) -> None:
        if self.clicker:
            was_enabled = bool(self.clicker.enabled)
            self.clicker.toggle()
            self._status = self.clicker.status_text()
            is_enabled = bool(self.clicker.enabled)
            if is_enabled != was_enabled:
                self._log_mode_toggle("auto", is_enabled, {"hotkey": self.hotkey, "interval": self.interval, "mouseButton": self.mouseButton})
            self.changed.emit()

    @Slot()
    def toggleMoveClick(self) -> None:
        if self.clicker:
            was_enabled = bool(self.clicker.move_click_enabled)
            self.clicker.toggle_move_click()
            self._status = self.clicker.status_text()
            is_enabled = bool(self.clicker.move_click_enabled)
            if is_enabled != was_enabled:
                self._log_mode_toggle("move", is_enabled, {"hotkey": self.moveHotkey})
            self.changed.emit()

    @Slot()
    def togglePilot(self) -> None:
        if self.clicker:
            was_enabled = self._pilot_active()
            self.clicker.toggle_pilot()
            self._status = self.clicker.status_text()
            is_enabled = self._pilot_active()
            if is_enabled != was_enabled:
                self._log_mode_toggle("pilot", is_enabled, {"hotkey": self.pilotHotkey, "wHoldLabel": self.wHoldLetter})
            self.changed.emit()

    @Slot()
    def toggleRightHold(self) -> None:
        if self.clicker:
            was_enabled = bool(self.clicker.right_hold_enabled)
            self.clicker.toggle_right_hold()
            self._status = self.clicker.status_text()
            is_enabled = bool(self.clicker.right_hold_enabled)
            if is_enabled != was_enabled:
                self._log_mode_toggle("right_hold", is_enabled, {"hotkey": self.rightHoldHotkey})
            self.changed.emit()

    @Slot()
    def toggleFixedClick(self) -> None:
        if self.clicker:
            was_enabled = bool(self.clicker.fixed_click_enabled)
            self.clicker.toggle_fixed_click()
            self._status = self.clicker.status_text()
            is_enabled = bool(self.clicker.fixed_click_enabled)
            if is_enabled != was_enabled:
                self._log_mode_toggle("fixed", is_enabled, {"hotkey": self.fixedHotkey})
            self.changed.emit()

    @Slot()
    def toggleArtillery(self) -> None:
        if self.clicker:
            was_enabled = bool(getattr(self.clicker, "artillery_enabled", False))
            self.clicker.toggle_artillery()
            self._status = self.clicker.status_text()
            is_enabled = bool(getattr(self.clicker, "artillery_enabled", False))
            if is_enabled != was_enabled:
                self._log_mode_toggle("artillery", is_enabled, {"hotkey": self.artilleryHotkey})
            self.changed.emit()

    @Slot()
    def captureFoxhole(self) -> None:
        if self.clicker:
            self._status = self.clicker.use_foxhole_window()
            self.changed.emit()

    @Slot(str)
    def setHotkey(self, value: str) -> None:
        if value in ACTION_KEYS:
            self._clicker_settings()["hotkey"] = value
            self._save_and_apply()
            self._log_activity("configurar_hotkey", subcategory="configuracao", metadata={"mode": "auto", "hotkey": value})

    @Slot(str)
    def setMoveHotkey(self, value: str) -> None:
        if value in ACTION_KEYS:
            self._clicker_settings()["move_hotkey"] = value
            self._save_and_apply()

    @Slot(str)
    def setFixedHotkey(self, value: str) -> None:
        if value in ACTION_KEYS:
            self._clicker_settings()["fixed_hotkey"] = value
            self._save_and_apply()

    @Slot(str)
    def setPilotHotkey(self, value: str) -> None:
        if value in ACTION_KEYS:
            self._clicker_settings()["pilot_hotkey"] = value
            self._save_and_apply()

    @Slot(str)
    def setArtilleryHotkey(self, value: str) -> None:
        if value in ACTION_KEYS:
            self._clicker_settings()["artillery_hotkey"] = value
            self._save_and_apply()

    @Slot(str)
    def setRightHoldHotkey(self, value: str) -> None:
        if value in ACTION_KEYS:
            self._clicker_settings()["right_hold_hotkey"] = value
            self._save_and_apply()

    @Slot(str)
    def setMouseButton(self, value: str) -> None:
        if value in MOUSE_BUTTONS:
            self._clicker_settings()["mouse_button"] = value
            self._save_and_apply()
            self._log_activity("configurar_mouse", subcategory="configuracao", metadata={"mouseButton": value})

    @Property(bool, notify=changed)
    def shiftEnabled(self) -> bool:
        return bool(self._clicker_settings().get("shift_enabled", False))

    @Slot(bool)
    def setShiftEnabled(self, value: bool) -> None:
        self._clicker_settings()["shift_enabled"] = bool(value)
        save_settings(self.settings)
        if self.clicker:
            self.clicker.shift_enabled = bool(value)
        self._log_activity("configurar_shift", subcategory="configuracao", metadata={"enabled": bool(value)})
        self.changed.emit()

    @Property(bool, notify=changed)
    def wDoubleTapEnabled(self) -> bool:
        return bool(self._clicker_settings().get("w_doubletap_enabled", False))

    @Slot(bool)
    def setWDoubleTapEnabled(self, value: bool) -> None:
        self._clicker_settings()["w_doubletap_enabled"] = bool(value)
        save_settings(self.settings)
        if self.clicker:
            self.clicker.w_doubletap_enabled = bool(value)
        self.changed.emit()

    @Property(bool, notify=changed)
    def rightDoubleTapEnabled(self) -> bool:
        return bool(self._clicker_settings().get("right_doubletap_enabled", False))

    @Slot(bool)
    def setRightDoubleTapEnabled(self, value: bool) -> None:
        self._clicker_settings()["right_doubletap_enabled"] = bool(value)
        save_settings(self.settings)
        if self.clicker:
            self.clicker.right_doubletap_enabled = bool(value)
        self.changed.emit()

    @Slot(str, bool)
    def setModeEnabled(self, key: str, enabled: bool) -> None:
        key = str(key or "")
        if key not in self.MODE_KEYS:
            return
        modes = self._mode_enabled_settings()
        enabled = bool(enabled)
        if modes.get(key, True) == enabled:
            return
        modes[key] = enabled
        self._clicker_settings()["modes_enabled"] = modes
        save_settings(self.settings)
        self._log_activity("habilitar_modo" if enabled else "desabilitar_modo", subcategory="configuracao", metadata={"mode": key, "enabled": enabled})
        if self.clicker:
            self.clicker.configure_modes_enabled(modes)
            self._status = self.clicker.status_text()
        self.changed.emit()

    @Slot()
    def toggleAllModes(self) -> None:
        enabled = not all(self._mode_enabled(key) for key in self.MODE_KEYS)
        modes = {key: enabled for key in self.MODE_KEYS}
        self._clicker_settings()["modes_enabled"] = modes
        save_settings(self.settings)
        if self.clicker:
            self.clicker.configure_modes_enabled(modes, stop_disabled=False)
            self._status = self.clicker.status_text()
        self.changed.emit()

    @Slot(float)
    def setInterval(self, value: float) -> None:
        try:
            interval = float(value)
        except (TypeError, ValueError):
            interval = self.DEFAULT_INTERVAL
        self._clicker_settings()["interval"] = round(max(0.03, min(5.0, interval)), 2)
        self._save_and_apply()
        self._log_activity("configurar_intervalo", subcategory="configuracao", metadata={"interval": self.interval})

    @Slot(int, int, int)
    def setSlotPosition(self, slot: int, x: int, y: int) -> None:
        if slot not in (1, 2, 3, 4):
            return
        data = self._clicker_settings()
        data[f"slot_{slot}_x"] = max(0, int(x))
        data[f"slot_{slot}_y"] = max(0, int(y))
        self._save_and_apply()

    @Slot(int, str)
    def setOrderName(self, index: int, name: str) -> None:
        orders = self._orders_from_settings()
        if index < 0 or index >= len(orders):
            return
        clean = str(name).strip()
        if not clean:
            return
        orders[index] = clean
        self._clicker_settings()["f5_orders"] = orders
        self._save_and_apply()

    @Slot()
    def addOrder(self) -> None:
        orders = self._orders_from_settings()
        orders.append(f"Order {len(orders) + 1}")
        self._clicker_settings()["f5_orders"] = orders
        self._save_and_apply()

    @Slot(int)
    def removeOrder(self, index: int) -> None:
        orders = self._orders_from_settings()
        if index < 0 or index >= len(orders):
            return
        del orders[index]
        self._clicker_settings()["f5_orders"] = orders or ["Diesel"]
        self._save_and_apply()

    @Slot(int)
    def startOrder(self, index: int) -> None:
        orders = self._orders_from_settings()
        if not orders:
            return
        order_name = orders[index] if 0 <= index < len(orders) else orders[0]
        self._status = f"Order started: {order_name}"
        self._log_activity("iniciar_ordem", subcategory="ordens", metadata={"orderName": order_name})
        self.orderRequested.emit(order_name)
        self.changed.emit()

    @Slot()
    def _start_default_order(self) -> None:
        self.startOrder(0)

    def _save_and_apply(self) -> None:
        save_settings(self.settings)
        self._apply_settings()
        self._refresh_models()
        self.changed.emit()
    @Slot()
    def shutdown(self) -> None:
        if self.clicker:
            self.clicker.stop()
