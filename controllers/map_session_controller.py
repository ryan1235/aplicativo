from __future__ import annotations
from .dict_list_model import DictListModel
from .sync_manager import SyncManager
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
import uuid
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

class MapSessionController(QObject):
    roomsFetched = Signal(str)
    myRoomsFetched = Signal(str)
    roomJoined = Signal(str, str)
    mapUpdated = Signal(str)
    userKicked = Signal()
    resultFromWorker = Signal(str, str)
    currentRoomChanged = Signal()
    currentRoomCreatorChanged = Signal()
    logAppended = Signal(str)

    def __init__(self, chatController, parent=None):
        super().__init__(parent)
        from PySide6.QtWebSockets import QWebSocket, QWebSocketProtocol
        self._chatController = chatController
        self._ws = QWebSocket()
        self._ws.setParent(self)
        self._ws.errorOccurred.connect(self._on_ws_error)
        self._ws.sslErrors.connect(self._on_ws_ssl_errors)
        self._ws.connected.connect(self._on_ws_connected)
        self._ws.disconnected.connect(self._on_ws_disconnected)
        self._ws.textMessageReceived.connect(self._on_ws_text_received)
        self._current_room = ""
        self._current_room_creator = ""
        self.resultFromWorker.connect(self._apply_result)
        self.sync_manager = SyncManager()
        self._debug_sync = True
        
    @Property(str, notify=currentRoomChanged)
    def currentRoom(self):
        return self._current_room
        
    @currentRoom.setter
    def currentRoom(self, value):
        if self._current_room != value:
            self._current_room = value
            self.currentRoomChanged.emit()

    @Property(str, notify=currentRoomCreatorChanged)
    def currentRoomCreator(self):
        return self._current_room_creator
        
    @currentRoomCreator.setter
    def currentRoomCreator(self, value):
        if self._current_room_creator != value:
            self._current_room_creator = value
            self.currentRoomCreatorChanged.emit()

    @Property(bool)
    def debugSync(self):
        return self._debug_sync
        
    @debugSync.setter
    def debugSync(self, value):
        self._debug_sync = value

    def _get_token(self):
        return self._chatController._token if self._chatController else ""

    @Slot(str, str)
    def _apply_result(self, kind: str, data: str):
        if kind == "rooms-fetched":
            self.roomsFetched.emit(data)
        elif kind == "my-rooms-fetched":
            self.myRoomsFetched.emit(data)
        elif kind == "room-deleted":
            self.fetchRooms()
            self.fetchMyRooms()
        elif kind == "room-created":
            self.fetchRooms()
            try:
                res = json.loads(data)
                if "id" in res:
                    pwd = getattr(self, "_last_created_password", "")
                    creator = ""
                    if "creator" in res and isinstance(res["creator"], dict):
                        creator = res["creator"].get("personaname", "")
                    if not creator and self._chatController:
                        val = self._chatController.property("currentUserName")
                        creator = str(val) if val else ""
                    self.joinRoom(res["id"], pwd, creator)
            except Exception:
                pass
        elif kind == "room-joined-auth":
            try:
                res = json.loads(data)
                if res.get("success"):
                    self.connectWs(res.get("roomId", ""))
            except Exception:
                pass

    @Slot()
    def fetchRooms(self):
        token = self._get_token()
        if not token: return
        def run():
            try:
                res = http_json("GET", "/map-rooms", token=token)
                self.resultFromWorker.emit("rooms-fetched", json.dumps(res))
            except Exception as e:
                print("Error fetching map rooms:", e)
        threading.Thread(target=run, daemon=True).start()

    @Slot()
    def fetchMyRooms(self):
        token = self._get_token()
        if not token: return
        def run():
            try:
                res = http_json("GET", "/map-rooms/my-rooms", token=token)
                self.resultFromWorker.emit("my-rooms-fetched", json.dumps(res))
            except Exception as e:
                print("Error fetching my map rooms:", e)
        threading.Thread(target=run, daemon=True).start()

    @Slot(str, bool, str)
    def createRoom(self, name: str, isPrivate: bool, password: str):
        token = self._get_token()
        if not token: return
        self._last_created_password = password
        payload = {"name": name, "isPrivate": isPrivate}
        if isPrivate and password:
            payload["password"] = password
        def run():
            try:
                res = http_json("POST", "/map-rooms", token=token, payload=payload)
                self.resultFromWorker.emit("room-created", json.dumps(res))
            except Exception as e:
                print("Error creating map room:", e)
        threading.Thread(target=run, daemon=True).start()

    @Slot(str, str, str)
    def joinRoom(self, roomId: str, password: str, creator: str = ""):
        token = self._get_token()
        if not token: return
        self.currentRoomCreator = creator
        payload = {"password": password} if password else {}
        def run():
            try:
                res = http_json("POST", f"/map-rooms/{roomId}/join", token=token, payload=payload)
                # Inject roomId into the response so _apply_result can use it
                if isinstance(res, dict):
                    res["roomId"] = roomId
                self.resultFromWorker.emit("room-joined-auth", json.dumps(res))
            except Exception as e:
                print(f"Error joining map room: {e}")
        threading.Thread(target=run, daemon=True).start()

    @Slot(str)
    def deleteRoom(self, roomId: str):
        token = self._get_token()
        if not token: return
        def run():
            try:
                res = http_json("DELETE", f"/map-rooms/{roomId}", token=token)
                self.resultFromWorker.emit("room-deleted", json.dumps(res))
            except Exception as e:
                print("Error deleting map room:", e)
        threading.Thread(target=run, daemon=True).start()

    @Slot(str, str, str)
    def editRoom(self, roomId: str, newName: str, newPassword: str):
        token = self._get_token()
        if not token: return
        payload = {"name": newName, "password": newPassword}
        def run():
            try:
                res = http_json("PUT", f"/map-rooms/{roomId}", token=token, payload=payload)
                self.resultFromWorker.emit("room-edited", json.dumps(res))
            except Exception as e:
                print("Error editing room:", e)
        threading.Thread(target=run, daemon=True).start()

    @Slot(str, str)
    def kickUser(self, roomId: str, userIdToKick: str):
        token = self._get_token()
        if not token: return
        payload = {"userIdToKick": userIdToKick}
        def run():
            try:
                res = http_json("POST", f"/map-rooms/{roomId}/kick", token=token, payload=payload)
                print(f"User {userIdToKick} kicked successfully")
            except Exception as e:
                print("Error kicking user:", e)
        threading.Thread(target=run, daemon=True).start()

    @Slot(str)
    def connectWs(self, roomId: str):
        if self._current_room != roomId:
            self.sync_manager.reset_state()
            self.sync_manager.pending_events.clear()
            self.sync_manager.sequence_counter = 0
            # Notify QML to clear visual state immediately
            self.mapUpdated.emit(json.dumps({"type": "full_state", "payload": {"drawings": [], "tacticalSymbols": []}}))
            
        self.currentRoom = roomId
        token = self._get_token()
        if not token: return
        self._ws.close()
        from PySide6.QtNetwork import QNetworkRequest
        ws_url = f"{CHAT_WS_BASE}/ws/map?token={token}"
        req = QNetworkRequest(QUrl(ws_url))
        req.setRawHeader(b"User-Agent", b"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        self._ws.open(req)

    @Slot(list)
    def _on_ws_ssl_errors(self, errors):
        self._ws.ignoreSslErrors()

    @Slot()
    def _on_ws_error(self, error):
        pass

    @Slot()
    def _on_ws_connected(self):
        payload = {"event": "join_room", "room_id": self._current_room}
        msg = json.dumps(payload)
        self.send_ws_message(msg)
        self._log_event("CONEXÃO", "connect", {})
        self.replayPendingEvents()

    @Slot()
    def _on_ws_disconnected(self):
        self._log_event("CONEXÃO", "disconnect", {})

    @Slot(str)
    def _on_ws_text_received(self, message: str):
        try:
            data = json.loads(message)
            event = data.get("event")
            if event == "joined_room":
                map_data = data.get("mapData", {})
                self.sync_manager.process_incoming_snapshot(map_data, 0)
                self.roomJoined.emit(data.get("room_id", ""), json.dumps(map_data))
            elif event == "map_update":
                payload_data = data.get("data", {})
                server_ver = payload_data.get("serverVersion", self.sync_manager.server_version)
                action = payload_data.get("type", "map_update")
                
                if action == "ack":
                    seq = payload_data.get("sequence")
                    self.sync_manager.receive_ack(seq, server_ver)
                    self._log_event("SINCRONIZAÇÃO", "event_ack", {"sequence": seq, "serverVersion": server_ver})
                elif action == "snapshot":
                    self.sync_manager.process_incoming_snapshot(payload_data.get("payload", {}), server_ver)
                    self._log_event("SINCRONIZAÇÃO", "snapshot_download", {"serverVersion": server_ver})
                    render_list = self.sync_manager.build_render_drawings()
                    tactical_list = self.sync_manager.build_tactical_symbols()
                    self.mapUpdated.emit(json.dumps({"type": "full_state", "payload": {"drawings": render_list, "tacticalSymbols": tactical_list}}))
                elif action == "version_conflict":
                    self._log_event("ERROS", "version_conflict", {"serverVersion": server_ver})
                    self.fetchLatestState()
                else:
                    if action != "cursor_move":
                        self.sync_manager.process_incoming_event(action, payload_data.get("objectId"), payload_data.get("payload"), server_ver)
                        render_list = self.sync_manager.build_render_drawings()
                        tactical_list = self.sync_manager.build_tactical_symbols()
                        self.mapUpdated.emit(json.dumps({"type": "full_state", "payload": {"drawings": render_list, "tacticalSymbols": tactical_list}}))
                        self._log_event("EVENTOS", "event_received", {"event": action, "serverVersion": server_ver})
                    else:
                        self.mapUpdated.emit(json.dumps(payload_data))
            elif event == "kicked":
                self._ws.close()
                self.userKicked.emit()
        except Exception as e:
            self._log_event("ERROS", "exception", {"error": str(e)})

    def send_ws_message(self, msg: str):
        if self._ws.isValid():
            self._ws.sendTextMessage(msg)
            
    def _log_event(self, category: str, action: str, payload: dict):
        if not self._debug_sync:
            return
            
        now = datetime.now(timezone.utc).isoformat()
        user_id = self._chatController._current_user_id if self._chatController else ""
        nick = self._chatController._current_user_name if self._chatController else "Unknown"
        
        log_entry = {
            "timestamp": now,
            "eventId": f"evt_{uuid.uuid4().hex[:8]}",
            "serverVersion": self.sync_manager.server_version,
            "clientVersion": getattr(self.sync_manager, "sequence_counter", 0),
            "userId": user_id,
            "nick": nick,
            "category": category,
            "action": action,
            "payload": payload,
        }
        
        # print structured JSON to stdout for debugging
        log_str = json.dumps(log_entry, ensure_ascii=False)
        self.logAppended.emit(log_str)

    @Slot(str, str, str)
    def pushEvent(self, event_type: str, object_id: str, payload_json: str):
        try:
            payload = json.loads(payload_json) if payload_json else {}
            user_id = self._chatController._current_user_id if self._chatController else ""
            
            if event_type == "cursor_move":
                evt = {
                    "eventId": f"evt_{uuid.uuid4().hex[:8]}",
                    "type": event_type,
                    "userId": user_id,
                    "objectId": object_id,
                    "timestamp": int(time.time()),
                    "payload": payload
                }
                if self._ws.isValid() and self._current_room:
                    self.send_ws_message(json.dumps({"event": "map_event", "room_id": self._current_room, "data": evt}))
                return
                
            evt = self.sync_manager.add_pending_event(event_type, object_id, payload)
            evt["userId"] = user_id
            
            render_list = self.sync_manager.build_render_drawings()
            tactical_list = self.sync_manager.build_tactical_symbols()
            self.mapUpdated.emit(json.dumps({"type": "full_state", "payload": {"drawings": render_list, "tacticalSymbols": tactical_list}}))
            
            if self._ws.isValid() and self._current_room:
                msg = json.dumps({
                    "event": "map_event",
                    "room_id": self._current_room,
                    "data": evt
                })
                self.send_ws_message(msg)
                self._log_event("EVENTOS", "event_sent", evt)
            else:
                self._log_event("SINCRONIZAÇÃO", "queue_event", evt)
        except Exception as e:
            self._log_event("ERROS", "invalid payload", {"error": str(e)})

    @Slot()
    def fetchLatestState(self):
        if self._ws.isValid() and self._current_room:
            self.send_ws_message(json.dumps({
                "event": "fetch_state",
                "room_id": self._current_room
            }))
            self._log_event("SINCRONIZAÇÃO", "fetch_state", {})

    @Slot()
    def replayPendingEvents(self):
        if not self.sync_manager.pending_events or not self._ws.isValid() or not self._current_room:
            return
            
        self._log_event("SINCRONIZAÇÃO", "replay_pending", {"count": len(self.sync_manager.pending_events)})
        
        for evt in self.sync_manager.pending_events:
            msg = json.dumps({
                "event": "map_event",
                "room_id": self._current_room,
                "data": evt
            })
            self.send_ws_message(msg)

    @Slot(str)
    def sendMapUpdate(self, dataJson: str):
        # Kept for backward compatibility, but routes to the new schema
        if self._ws.isValid() and self._current_room:
            try:
                data = json.loads(dataJson)
                payload = {
                    "event": "map_update",
                    "room_id": self._current_room,
                    "data": data
                }
                msg = json.dumps(payload)
                self.send_ws_message(msg)
            except Exception as e:
                self._log_event("ERROS", "exception", {"error": str(e)})

    @Slot()
    def leaveWsRoom(self):
        if self._ws.isValid() and self._current_room:
            try:
                payload = {
                    "event": "leave_room",
                    "room_id": self._current_room
                }
                self._ws.sendTextMessage(json.dumps(payload))
                self.currentRoom = ""
            except Exception:
                pass
