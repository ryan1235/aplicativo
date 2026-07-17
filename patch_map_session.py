import re
import sys

with open('c:/Users/ryanl/OneDrive/Desktop/aplicativo/controllers/map_session_controller.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Imports
content = content.replace("from .dict_list_model import DictListModel", "from .dict_list_model import DictListModel\nfrom .sync_manager import SyncManager")

# 2. Init
old_init = """        self.resultFromWorker.connect(self._apply_result)
        self._client_version = 0
        self._server_version = 0
        self._pending_events = []
        self._debug_sync = True"""
new_init = """        self.resultFromWorker.connect(self._apply_result)
        self.sync_manager = SyncManager()
        self._debug_sync = True"""
content = content.replace(old_init, new_init)

# 3. Log event
old_log = """        log_entry = {
            "timestamp": now,
            "eventId": f"evt_{uuid.uuid4().hex[:8]}",
            "serverVersion": self._server_version,
            "clientVersion": self._client_version,"""
new_log = """        log_entry = {
            "timestamp": now,
            "eventId": f"evt_{uuid.uuid4().hex[:8]}",
            "serverVersion": self.sync_manager.server_version,
            "clientVersion": getattr(self.sync_manager, "sequence_counter", 0),"""
content = content.replace(old_log, new_log)

# 4. _on_ws_text_received
old_ws_rx = """            elif event == "map_update":
                # Check versions for event sourcing if supported
                payload_data = data.get("data", {})
                server_ver = payload_data.get("serverVersion")
                
                if server_ver is not None:
                    if self._client_version < server_ver:
                        self.fetchLatestState()
                        self.replayPendingEvents()
                    self._server_version = server_ver
                
                # Expose specific events
                self.mapUpdated.emit(json.dumps(payload_data))
                
                # Log receive
                action = payload_data.get("type", "map_update")
                self._log_event("SINCRONIZAÇÃO", "receive", {"event": action})"""

new_ws_rx = """            elif event == "map_update":
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
                    self.mapUpdated.emit(json.dumps({"type": "full_state", "payload": {"drawings": render_list}}))
                elif action == "version_conflict":
                    self._log_event("ERROS", "version_conflict", {"serverVersion": server_ver})
                    self.fetchLatestState()
                else:
                    if action != "cursor_move":
                        self.sync_manager.process_incoming_event(action, payload_data.get("objectId"), payload_data.get("payload"), server_ver)
                        render_list = self.sync_manager.build_render_drawings()
                        self.mapUpdated.emit(json.dumps({"type": "full_state", "payload": {"drawings": render_list}}))
                        self._log_event("EVENTOS", "event_received", {"event": action, "serverVersion": server_ver})
                    else:
                        self.mapUpdated.emit(json.dumps(payload_data))"""
content = content.replace(old_ws_rx, new_ws_rx)

# 5. pushEvent
old_push = """    @Slot(str, str, str)
    def pushEvent(self, event_type: str, object_id: str, payload_json: str):
        try:
            payload = json.loads(payload_json) if payload_json else {}
            user_id = self._chatController._current_user_id if self._chatController else ""
            
            evt = {
                "eventId": f"evt_{uuid.uuid4().hex[:8]}",
                "type": event_type,
                "userId": user_id,
                "objectId": object_id,
                "version": self._client_version + 1,
                "timestamp": int(time.time()),
                "payload": payload
            }
            
            self._client_version += 1
            
            if self._ws.isValid() and self._current_room:
                msg = json.dumps({
                    "event": "map_event",
                    "room_id": self._current_room,
                    "data": evt
                })
                self.send_ws_message(msg)
                self._log_event("FERRAMENTAS", event_type, evt)
            else:
                self._pending_events.append(evt)
                self._log_event("SINCRONIZAÇÃO", "queue_event", evt)
        except Exception as e:
            self._log_event("ERROS", "invalid payload", {"error": str(e)})"""

new_push = """    @Slot(str, str, str)
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
            self.mapUpdated.emit(json.dumps({"type": "full_state", "payload": {"drawings": render_list}}))
            
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
            self._log_event("ERROS", "invalid payload", {"error": str(e)})"""
content = content.replace(old_push, new_push)

# 6. replayPendingEvents
old_replay = """    @Slot()
    def replayPendingEvents(self):
        if not self._pending_events or not self._ws.isValid() or not self._current_room:
            return
            
        self._log_event("SINCRONIZAÇÃO", "replay_pending", {"count": len(self._pending_events)})
        
        for evt in self._pending_events:
            msg = json.dumps({
                "event": "map_event",
                "room_id": self._current_room,
                "data": evt
            })
            self.send_ws_message(msg)
            
        self._pending_events.clear()"""

new_replay = """    @Slot()
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
            self.send_ws_message(msg)"""
content = content.replace(old_replay, new_replay)

# 7. update jsonDebugWindow connection string
content = content.replace("jsonDebugWindow.jsonOutput = JSON.stringify(debugLog, null, 2);", "")

with open('c:/Users/ryanl/OneDrive/Desktop/aplicativo/controllers/map_session_controller.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Patch applied.")
