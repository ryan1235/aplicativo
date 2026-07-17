import json
import uuid
import time

class SyncManager:
    def __init__(self):
        self.reset_state()
        self.server_version = 0
        self.sequence_counter = 0
        self.pending_events = []

    def reset_state(self):
        self.state = {
            "users": {},
            "cursors": {},
            "markers": {},
            "polygons": {},
            "lines": {},
            "circles": {},
            "texts": {},
            "artillery": {},
            "tactical_symbols": {}
        }

    def process_incoming_snapshot(self, snapshot_data: dict, server_version: int):
        """Replaces the entire local state with a server snapshot."""
        # Update server version
        self.server_version = server_version
        
        # Load snapshot keys into state
        for key in self.state.keys():
            if key in snapshot_data and isinstance(snapshot_data[key], dict):
                self.state[key] = snapshot_data[key]
            else:
                self.state[key] = {}
                
        # Support legacy / combined "drawings" array in snapshot
        if "drawings" in snapshot_data and isinstance(snapshot_data["drawings"], list):
            for d in snapshot_data["drawings"]:
                d_id = d.get("id") or d.get("_id") or d.get("eventId")
                if d_id:
                    self.state["lines"][d_id] = d
                    
        # We should replay pending_events on top of the snapshot.
        self.replay_pending_events()

    def process_incoming_event(self, event_type: str, object_id: str, payload: dict, server_version: int):
        """Processes a single event from the server and updates local state."""
        self.server_version = server_version
        
        # Simple routing based on event_type prefix
        # This is basic logic; real logic would depend on your backend's exact event schemas.
        # But for this compatibility adapter, we just try to infer the dictionary.
        
        target_dict = None
        if event_type == "add_marker" or event_type == "update_marker": target_dict = "markers"
        elif event_type == "add_polygon" or event_type == "update_polygon": target_dict = "polygons"
        elif event_type == "add_line" or event_type == "update_line": target_dict = "lines"
        elif event_type == "add_circle" or event_type == "update_circle": target_dict = "circles"
        elif event_type == "add_text" or event_type == "update_text": target_dict = "texts"
        elif event_type == "add_artillery" or event_type == "update_artillery": target_dict = "artillery"
        elif event_type == "add_tactical_symbol" or event_type == "update_tactical_symbol" or event_type == "remove_tactical_symbol": target_dict = "tactical_symbols"
        elif event_type == "add_drawing" or event_type == "update_drawing":
            # Compatibility fallback for generic drawing additions/updates
            dtype = payload.get("type", "unknown")
            if dtype == "marker": target_dict = "markers"
            elif dtype == "polygon" or dtype == "route": target_dict = "polygons"
            elif dtype == "line": target_dict = "lines"
            elif dtype == "circle": target_dict = "circles"
            elif dtype == "text": target_dict = "texts"
            elif dtype == "artillery": target_dict = "artillery"
            else: target_dict = "lines" # fallback
        
        if event_type.startswith("add_") or event_type.startswith("update_"):
            if target_dict:
                payload["id"] = object_id
                self.state[target_dict][object_id] = payload
        elif event_type.startswith("delete_") or event_type.startswith("remove_"):
            if target_dict and object_id in self.state[target_dict]:
                del self.state[target_dict][object_id]
            elif not target_dict:
                for key in self.state:
                    if object_id in self.state[key]:
                        del self.state[key][object_id]
                        break
        elif event_type == "clear_all":
            self.reset_state()
            
    def receive_ack(self, sequence: int, server_version: int):
        """Server acknowledged our event. Remove from pending and update version."""
        self.server_version = server_version
        self.pending_events = [e for e in self.pending_events if e.get("sequence") != sequence]

    def add_pending_event(self, event_type: str, object_id: str, payload: dict) -> dict:
        """Create a new local event, add to pending, and apply optimistically."""
        self.sequence_counter += 1
        event = {
            "eventId": f"evt_{uuid.uuid4().hex[:8]}",
            "sequence": self.sequence_counter,
            "type": event_type,
            "objectId": object_id,
            "payload": payload,
            "timestamp": int(time.time())
        }
        self.pending_events.append(event)
        
        # Apply optimistically so the user sees it immediately
        self.process_incoming_event(event_type, object_id, payload, self.server_version)
        
        return event

    def replay_pending_events(self):
        """Re-applies pending events on top of the current state."""
        # For simplicity, we just process them through the incoming event logic
        # without incrementing the server version.
        for evt in self.pending_events:
            self.process_incoming_event(evt["type"], evt["objectId"], evt["payload"], self.server_version)

    def build_render_drawings(self) -> list:
        """
        Compatibility adapter for QML.
        Merges all separated drawing dictionaries into a single array.
        """
        render_list = []
        for key in ["markers", "polygons", "lines", "circles", "texts", "artillery"]:
            for obj_id, obj_data in self.state[key].items():
                render_list.append(obj_data)
        return render_list

    def build_tactical_symbols(self) -> list:
        render_list = []
        for obj_id, obj_data in self.state["tactical_symbols"].items():
            render_list.append(obj_data)
        return render_list

    def get_debug_state(self) -> dict:
        """Returns metadata for the QML JSON debug window."""
        return {
            "serverVersion": self.server_version,
            "pendingEventsCount": len(self.pending_events),
            "pendingEvents": self.pending_events
        }
