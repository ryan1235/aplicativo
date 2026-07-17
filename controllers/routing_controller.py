from PySide6.QtCore import QObject, Slot, Signal, Property, QTimer
import threading
import json
import os
from foxmap.geo.routing import get_routing_graph

class RoutingController(QObject):
    isReadyChanged = Signal()
    
    def __init__(self, base_dir: str, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._is_ready = False
        self._base_dir = base_dir
        
        # Load roads in background
        threading.Thread(target=self._load_roads_async, daemon=True).start()

    def _load_roads_async(self):
        roads_path = os.path.join(self._base_dir, "roads.json")
        try:
            graph = get_routing_graph()
            graph.load_from_json(roads_path)
            self._is_ready = True
            
            # Use QTimer to emit signal on main thread
            QTimer.singleShot(0, self.isReadyChanged.emit)
        except Exception as e:
            print(f"[RoutingController] Failed to load roads.json: {e}")

    @Property(bool, notify=isReadyChanged)
    def isReady(self) -> bool:
        return self._is_ready

    @Slot(float, float, float, float, result=str)
    def calculateRoute(self, start_x: float, start_y: float, end_x: float, end_y: float) -> str:
        if not self._is_ready:
            return json.dumps({"error": "Routing graph not ready"})
            
        try:
            graph = get_routing_graph()
            path, total_cost, time_mins = graph.calculate_route(start_x, start_y, end_x, end_y)
            
            if not path:
                return json.dumps({"error": "No route found"})
                
            # Convert tuples back to dictionaries for QML JSON parsing
            formatted_path = [{"x": p[0], "y": p[1]} for p in path]
            
            result = {
                "points": formatted_path,
                "cost": total_cost,
                "time_mins": time_mins
            }
            return json.dumps(result)
        except Exception as e:
            print(f"[RoutingController] Error calculating route: {e}")
            return json.dumps({"error": str(e)})
