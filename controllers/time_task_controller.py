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

class TimeTaskController(QObject):
    changed = Signal()
    statusFromWorker = Signal(str)
    restoreAppRequested = Signal()

    def __init__(self, i18n: I18nController | None = None, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.i18n = i18n
        self._status = self._t("timetask.status_idle")
        self._metric = self._t("timetask.metric_empty")
        self._macro_name = "macro"
        self._speed = "1.0"
        self._repeat = "1"
        self._delay = "0s"
        self._stock_macro_name = self._t("timetask.none")
        self._stock_interval = "1"
        self._selected_path: Path | None = None
        self._summaries = []
        self._record_overlay_visible = False
        self._replay_overlay_visible = False
        self._record_overlay_title = self._t("timetask.overlay_ready")
        self._record_overlay_detail = self._t("timetask.overlay_record_options")
        self._record_overlay_hint = self._t("timetask.overlay_focus_hint")
        self._record_overlay_accent = "#5eead4"
        self._replay_overlay_title = self._t("timetask.replay_overlay_title")
        self._replay_overlay_detail = self._t("timetask.replay_empty")
        self._replay_overlay_accent = "#62d7a4"
        self._countdown_value = 0
        self._settings = load_settings()
        time_task_settings = self._settings.get("time_task", {})
        self._record_overlay_x = self._int_or_default(time_task_settings.get("overlay_record_x"), -1)
        self._record_overlay_y = self._int_or_default(time_task_settings.get("overlay_record_y"), -1)
        self._replay_overlay_x = self._int_or_default(time_task_settings.get("overlay_replay_x"), -1)
        self._replay_overlay_y = self._int_or_default(time_task_settings.get("overlay_replay_y"), -1)
        self._macros = DictListModel(["name", "duration", "events", "createdAt", "path", "selected"], self)
        self.statusFromWorker.connect(self._set_status_from_worker)
        self._countdown_timer = QTimer(self)
        self._countdown_timer.setInterval(1000)
        self._countdown_timer.timeout.connect(self._run_countdown_tick)
        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(300)
        self._poll_timer.timeout.connect(self._poll_state)
        self._recorder = None
        self._recorder_checked = False
        self._available = True
        self._activity_logger: ActivityLogger | None = None

    def setActivityLogger(self, logger: ActivityLogger | None) -> None:
        self._activity_logger = logger

    def _log_activity(self, action: str, *, subcategory: str, quantity: int = 1, metadata: dict[str, Any] | None = None) -> None:
        if callable(self._activity_logger):
            self._activity_logger("macros", action, quantity, metadata or {}, subcategory)

    @Slot()
    def ensureLoaded(self) -> None:
        self._ensure_recorder()
        self.refreshMacros()

    def _ensure_recorder(self) -> bool:
        if self._recorder is not None:
            return True
        if self._recorder_checked:
            return False
        self._recorder_checked = True
        try:
            from macro_recorder import MacroRecorder

            self._recorder = MacroRecorder(lambda message: self.statusFromWorker.emit(str(message)))
            self._available = True
        except Exception as exc:
            self._recorder = None
            self._available = False
            self._status = f"TimeTask unavailable: {exc}"
            self.changed.emit()
            return False
        self.changed.emit()
        return True

    @staticmethod
    def _int_or_default(value: Any, default: int) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def _t(self, key: str, **kwargs: Any) -> str:
        translator = self.i18n.translator if self.i18n is not None else Translator()
        return translator.t(key, **kwargs)

    @Property(QObject, constant=True)
    def macros(self) -> DictListModel:
        return self._macros

    @Property(str, notify=changed)
    def status(self) -> str:
        return self._status

    @Property(str, notify=changed)
    def metric(self) -> str:
        return self._metric

    @Property(bool, notify=changed)
    def available(self) -> bool:
        return self._available

    @Property(bool, notify=changed)
    def recording(self) -> bool:
        return bool(self._recorder and self._recorder.recording)

    @Property(bool, notify=changed)
    def paused(self) -> bool:
        return bool(self._recorder and (self._recorder.paused or self._recorder.replay_paused))

    @Property(bool, notify=changed)
    def replaying(self) -> bool:
        return bool(self._recorder and self._recorder.replaying)

    @Property(str, notify=changed)
    def macroName(self) -> str:
        return self._macro_name

    @Property(str, notify=changed)
    def speed(self) -> str:
        return self._speed

    @Property(str, notify=changed)
    def repeat(self) -> str:
        return self._repeat

    @Property(str, notify=changed)
    def delay(self) -> str:
        return self._delay

    @Property(str, notify=changed)
    def stockMacroName(self) -> str:
        return self._stock_macro_name

    @Property(str, notify=changed)
    def stockInterval(self) -> str:
        return self._stock_interval

    @Property(str, notify=changed)
    def selectedMacroName(self) -> str:
        return self._selected_path.stem if self._selected_path else ""

    @Property(bool, notify=changed)
    def recordOverlayVisible(self) -> bool:
        return self._record_overlay_visible

    @Property(str, notify=changed)
    def recordOverlayTitle(self) -> str:
        return self._record_overlay_title

    @Property(str, notify=changed)
    def recordOverlayDetail(self) -> str:
        return self._record_overlay_detail

    @Property(str, notify=changed)
    def recordOverlayHint(self) -> str:
        return self._record_overlay_hint

    @Property(str, notify=changed)
    def recordOverlayAccent(self) -> str:
        return self._record_overlay_accent

    @Property(int, notify=changed)
    def recordOverlayX(self) -> int:
        return self._record_overlay_x

    @Property(int, notify=changed)
    def recordOverlayY(self) -> int:
        return self._record_overlay_y

    @Property(bool, notify=changed)
    def replayOverlayVisible(self) -> bool:
        return self._replay_overlay_visible

    @Property(str, notify=changed)
    def replayOverlayTitle(self) -> str:
        return self._replay_overlay_title

    @Property(str, notify=changed)
    def replayOverlayDetail(self) -> str:
        return self._replay_overlay_detail

    @Property(str, notify=changed)
    def replayOverlayAccent(self) -> str:
        return self._replay_overlay_accent

    @Property(int, notify=changed)
    def replayOverlayX(self) -> int:
        return self._replay_overlay_x

    @Property(int, notify=changed)
    def replayOverlayY(self) -> int:
        return self._replay_overlay_y

    @Property("QStringList", constant=True)
    def speedOptions(self) -> list[str]:
        return ["0.5", "1.0", "1.5", "2.0"]

    @Property("QStringList", constant=True)
    def delayOptions(self) -> list[str]:
        return ["0s", "0.5s", "1s", "2s", "5s", "10s", "1 min", "2 min", "5 min"]

    @Property("QStringList", notify=changed)
    def stockMacroOptions(self) -> list[str]:
        return [self._t("timetask.none")] + [summary.name for summary in self._summaries]

    @Property(str, constant=True)
    def macroFolder(self) -> str:
        return str(user_data_dir() / "macros")

    @Slot(str)
    def setMacroName(self, value: str) -> None:
        self._macro_name = str(value or "macro")
        self.changed.emit()

    @Slot(str)
    def setSpeed(self, value: str) -> None:
        self._speed = str(value or "1.0")
        self.changed.emit()

    @Slot(str)
    def setRepeat(self, value: str) -> None:
        self._repeat = str(value or "1")
        self.changed.emit()

    @Slot(str)
    def setDelay(self, value: str) -> None:
        self._delay = str(value or "0s")
        self.changed.emit()

    @Slot(str)
    def setStockMacroName(self, value: str) -> None:
        self._stock_macro_name = str(value or self._t("timetask.none"))
        self.changed.emit()

    @Slot(str)
    def setStockInterval(self, value: str) -> None:
        self._stock_interval = str(value or "1")
        self.changed.emit()

    @Slot(int)
    def selectMacro(self, row: int) -> None:
        if row < 0 or row >= len(self._summaries):
            return
        self._selected_path = self._summaries[row].path
        self._show_replay_overlay(self._selected_path.stem)
        self.refreshMacros()

    @Slot()
    def showRecordOverlay(self) -> None:
        self._countdown_timer.stop()
        self._replay_overlay_visible = False
        self._record_overlay_visible = True
        self._record_overlay_title = self._t("timetask.overlay_ready")
        self._record_overlay_detail = self._t("timetask.overlay_record_options")
        self._record_overlay_hint = self._t("timetask.overlay_focus_hint")
        self._record_overlay_accent = "#5eead4"
        self.changed.emit()

    @Slot()
    def hideRecordOverlay(self) -> None:
        if self.recording:
            return
        self._record_overlay_visible = False
        self.changed.emit()

    @Slot()
    def hideReplayOverlay(self) -> None:
        if self.replaying:
            return
        self._replay_overlay_visible = False
        self.changed.emit()

    @Slot()
    def startRecording(self) -> None:
        if not self._ensure_recorder():
            self._status = "TimeTask unavailable"
            self.changed.emit()
            return
        if self._recorder.start_recording():
            self._log_activity("iniciar_gravacao", subcategory="gravacao", metadata={"macroName": self._macro_name})
            self._record_overlay_visible = True
            self._record_overlay_title = self._t("timetask.overlay_recording")
            self._record_overlay_detail = self._t("timetask.overlay_armed")
            self._record_overlay_hint = self._t("timetask.overlay_focus_hint")
            self._record_overlay_accent = "#ffd166"
        else:
            self._status = "Could not start recording"
        self._sync_poll_timer()
        self.changed.emit()

    @Slot()
    def beginCountdownRecording(self) -> None:
        if not self._ensure_recorder():
            self._status = "TimeTask unavailable"
            self.changed.emit()
            return
        if self._recorder.recording:
            self._recorder.resume_recording()
            return
        self._replay_overlay_visible = False
        self._record_overlay_visible = True
        self._countdown_value = 3
        self._run_countdown_tick()

    def _run_countdown_tick(self) -> None:
        if self._countdown_value <= 0:
            self._countdown_timer.stop()
            self.startRecording()
            return
        self._record_overlay_title = self._t("timetask.overlay_countdown_title")
        self._record_overlay_detail = str(self._countdown_value)
        self._record_overlay_hint = self._t("timetask.overlay_countdown_hint")
        self._record_overlay_accent = "#ffd166"
        self._record_overlay_visible = True
        self._countdown_value -= 1
        self._countdown_timer.start()
        self.changed.emit()

    @Slot()
    def stopRecording(self) -> None:
        if not self._ensure_recorder():
            self._status = "No active recording"
        else:
            self._countdown_timer.stop()
            events = self._recorder.stop_recording()
            self._status = self._t("timetask.overlay_events", events=len(events))
            
            if events:
                import time
                name_to_save = self._macro_name
                if name_to_save == "macro" or not name_to_save.strip():
                    name_to_save = f"Macro_{time.strftime('%H%M%S')}"
                path = self._recorder.save_macro(name_to_save)
                self._log_activity("salvar_macro", subcategory="arquivos", quantity=max(1, len(events)), metadata={"macroName": path.stem, "events": len(events)})
                self._selected_path = path
                self._show_replay_overlay(path.stem)
            else:
                self._show_replay_overlay()
                
            self._record_overlay_visible = False
            
        self.refreshMacros()
        self._sync_poll_timer()
        self.restoreAppRequested.emit()
        self.changed.emit()

    @Slot()
    def saveCurrent(self) -> None:
        if not self._ensure_recorder():
            self._status = "TimeTask unavailable"
            self.changed.emit()
            return
        self._countdown_timer.stop()
        if self._recorder.recording:
            self._recorder.stop_recording()
        events = self._recorder.snapshot_events()
        if not events:
            self._status = self._t("timetask.no_events")
            self.changed.emit()
            return
        path = self._recorder.save_macro(self._macro_name)
        self._status = self._t("timetask.saved", path=str(path))
        self._selected_path = path
        self._record_overlay_visible = False
        self.refreshMacros()
        self._show_replay_overlay(path.stem)
        self.restoreAppRequested.emit()
        self.changed.emit()

    @Slot()
    def pauseResume(self) -> None:
        if not self._ensure_recorder():
            return
        if self._recorder.recording:
            if self._recorder.paused:
                self._recorder.resume_recording()
            else:
                self._recorder.pause_recording()
        elif self._recorder.replaying:
            if self._recorder.replay_paused:
                self._recorder.resume_replay()
            else:
                self._recorder.pause_replay()
        self.changed.emit()

    @Slot()
    def playSelected(self) -> None:
        if not self._ensure_recorder():
            self._status = "TimeTask unavailable"
            self.changed.emit()
            return
        if not self._selected_path:
            self.refreshMacros()
            if self._summaries:
                self._selected_path = self._summaries[0].path
            else:
                self._status = self._t("timetask.pick_macro")
                self._show_replay_overlay(self._status)
                return
        speed = self._parse_float(self._speed, 1.0)
        repeat = self._parse_int(self._repeat, 1)
        delay = self._delay_seconds(self._delay)
        stock_path = self._stock_macro_path()
        stock_interval = self._parse_int(self._stock_interval, 1)
        self._record_overlay_visible = False
        self._show_replay_overlay(self._selected_path.stem, visible=True)
        started = self._recorder.replay_macro(
            self._selected_path,
            speed=speed,
            repeat=repeat,
            delay_between=delay,
            stock_path=stock_path,
            stock_interval=stock_interval,
        )
        if started:
            self._log_activity("reproduzir_macro", subcategory="replay", metadata={"macroName": self._selected_path.stem if self._selected_path else "", "speed": speed, "repeat": repeat, "delay": delay})
            self._status = self._t("timetask.overlay_playing")
        else:
            self._status = self._t("timetask.replay_need_foxhole")
            self._show_replay_overlay(self._status)
        self._sync_poll_timer()
        self.changed.emit()

    @Slot()
    def stopReplay(self) -> None:
        if self._recorder:
            self._recorder.stop_replay()
        self._log_activity("parar_replay", subcategory="replay", metadata={"macroName": self._selected_path.stem if self._selected_path else ""})
        self._replay_overlay_visible = False
        self._status = self._t("timetask.stopped")
        self._sync_poll_timer()
        self.changed.emit()

    @Slot()
    def deleteSelectedMacro(self) -> None:
        if not self._selected_path:
            self._status = self._t("timetask.pick_macro")
            self.changed.emit()
            return
        parent = QApplication.activeWindow()
        answer = QMessageBox.question(parent, self._t("timetask.delete"), self._t("timetask.delete_confirm", name=self._selected_path.stem))
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self._selected_path.unlink()
        except OSError as exc:
            self._status = str(exc)
        else:
            self._status = self._t("timetask.deleted")
            self._selected_path = None
            self._replay_overlay_visible = False
        self.refreshMacros()
        self.changed.emit()

    @Slot(int, int)
    def setRecordOverlayPosition(self, x: int, y: int) -> None:
        self._record_overlay_x = max(0, int(x))
        self._record_overlay_y = max(0, int(y))
        self._settings.setdefault("time_task", {})["overlay_record_x"] = self._record_overlay_x
        self._settings.setdefault("time_task", {})["overlay_record_y"] = self._record_overlay_y
        save_settings(self._settings)
        self.changed.emit()

    @Slot(int, int)
    def setReplayOverlayPosition(self, x: int, y: int) -> None:
        self._replay_overlay_x = max(0, int(x))
        self._replay_overlay_y = max(0, int(y))
        self._settings.setdefault("time_task", {})["overlay_replay_x"] = self._replay_overlay_x
        self._settings.setdefault("time_task", {})["overlay_replay_y"] = self._replay_overlay_y
        save_settings(self._settings)
        self.changed.emit()

    @Slot()
    def refreshMacros(self) -> None:
        if not self._ensure_recorder():
            self._summaries = []
        else:
            try:
                self._summaries = self._recorder.list_macros()
            except Exception as exc:
                self._status = f"Macro list unavailable: {exc}"
                self._summaries = []
        if self._selected_path is None and self._summaries:
            self._selected_path = self._summaries[0].path
        if self._selected_path and not any(summary.path == self._selected_path for summary in self._summaries):
            self._selected_path = self._summaries[0].path if self._summaries else None
        if self._stock_macro_name not in self.stockMacroOptions:
            self._stock_macro_name = self._t("timetask.none")
        self._macros.set_items(
            [
                {
                    "name": summary.name,
                    "duration": f"{summary.duration:.1f}s",
                    "events": summary.events,
                    "createdAt": summary.created_at,
                    "path": str(summary.path),
                    "selected": self._selected_path == summary.path,
                }
                for summary in self._summaries
            ]
        )
        self.changed.emit()

    def _set_status_from_worker(self, message: str) -> None:
        self._status = message
        if any(token in message.lower() for token in ("finalizada", "cancelada", "parada", "finished", "cancelled", "stopped")):
            self.refreshMacros()
            if not self.replaying:
                self._show_replay_overlay()
        self._sync_poll_timer()
        self.changed.emit()

    def _poll_state(self) -> None:
        if not self._recorder:
            self._sync_poll_timer()
            return
        if not (self._recorder.recording or self._recorder.replaying):
            self._sync_poll_timer()
            return
        events = self._recorder.snapshot_events()
        duration = events[-1]["t"] if events else 0.0
        self._metric = self._t("timetask.metric", events=len(events), duration=f"{duration:.1f}s")
        if self._recorder.recording:
            self._record_overlay_visible = True
            self._record_overlay_title = self._t("timetask.overlay_recording")
            self._record_overlay_detail = (
                self._t("timetask.overlay_paused")
                if self._recorder.paused
                else self._t("timetask.overlay_events_live", events=len(events), live=self._recorder.live_status())
            )
            self._record_overlay_hint = self._t("timetask.overlay_focus_hint")
            self._record_overlay_accent = "#ffd166"
        if self._recorder.replaying:
            self._replay_overlay_visible = True
            self._replay_overlay_title = self._t("timetask.overlay_playing")
            self._replay_overlay_detail = (
                self._t("timetask.overlay_paused")
                if self._recorder.replay_paused
                else self._t("timetask.overlay_replay_live", live=self._recorder.replay_status())
            )
            self._replay_overlay_accent = "#62d7a4"
        self.changed.emit()

    def _sync_poll_timer(self) -> None:
        active = bool(self._recorder and (self._recorder.recording or self._recorder.replaying))
        if active and not self._poll_timer.isActive():
            self._poll_timer.start()
        elif not active and self._poll_timer.isActive():
            self._poll_timer.stop()

    def _show_replay_overlay(self, detail: str | None = None, *, visible: bool = True) -> None:
        if detail is None:
            if self._selected_path:
                detail = self._selected_path.stem
            elif self._summaries:
                detail = self._summaries[0].name
            else:
                detail = self._t("timetask.replay_empty")
        self._replay_overlay_title = self._t("timetask.replay_overlay_title")
        self._replay_overlay_detail = detail
        self._replay_overlay_accent = "#62d7a4"
        self._replay_overlay_visible = visible
        self.changed.emit()

    @staticmethod
    def _parse_float(value: str, fallback: float) -> float:
        try:
            return float(str(value).strip())
        except (TypeError, ValueError):
            return fallback

    @staticmethod
    def _parse_int(value: str, fallback: int) -> int:
        try:
            return int(str(value).strip())
        except (TypeError, ValueError):
            return fallback

    def _delay_seconds(self, value: str) -> float:
        text = str(value or "0s").strip().lower()
        try:
            if "min" in text:
                return float(text.replace("min", "").replace("s", "").strip()) * 60
            return float(text.replace("s", "").strip() or 0)
        except ValueError:
            return 0.0

    def _stock_macro_path(self) -> Path | None:
        none_label = self._t("timetask.none")
        if self._stock_macro_name == none_label:
            return None
        for summary in self._summaries:
            if summary.name == self._stock_macro_name:
                return summary.path
        return None

    @Slot()
    def shutdown(self) -> None:
        self._countdown_timer.stop()
        self._poll_timer.stop()
        if self._recorder:
            self._recorder.stop()
